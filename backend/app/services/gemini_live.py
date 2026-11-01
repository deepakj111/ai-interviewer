"""Fast Loop: Gemini Multimodal Live WebSocket Multiplexer."""

import asyncio
import base64
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.config import get_settings
from app.database import AsyncSessionLocal, InterviewSessionModel, TranscriptTurnModel
from app.prompts.interviewer_system import build_interviewer_session_prompt
from app.schemas import CandidateClaimGraph, InterviewMode, InterviewStage
from app.services.fsm_orchestrator import InterviewFSM
from app.services.question_bank import get_question_by_id
from app.services.shadow_supervisor import evaluate_turn_in_shadow

logger = logging.getLogger(__name__)


class LiveInterviewSessionHandler:
    """Handles bidirectional audio streaming, code state diffs, and FSM coordination."""

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        api_key: str | None = None,
    ):
        self.websocket = websocket
        self.session_id = session_id
        self.api_key = api_key or get_settings().GEMINI_API_KEY
        self.settings = get_settings()
        self.fsm: InterviewFSM | None = None
        self.session_record: InterviewSessionModel | None = None
        self.claim_graph: CandidateClaimGraph | None = None
        self.gemini_session = None

    async def initialize(self) -> None:
        """Load session metadata from SQLite and initialize FSM."""
        async with AsyncSessionLocal() as db:
            session = await db.get(InterviewSessionModel, self.session_id)
            if not session:
                raise ValueError(f"Session {self.session_id} not found")
            self.session_record = session

            mode = InterviewMode(session.interview_mode)
            initial_stage = InterviewStage(session.fsm_state)
            self.fsm = InterviewFSM(
                mode=mode,
                initial_stage=initial_stage,
                active_question_id=session.active_question_id,
            )

            if session.claim_graph:
                try:
                    self.claim_graph = CandidateClaimGraph.model_validate_json(session.claim_graph)
                except Exception as exc:
                    logger.warning("Could not parse claim graph: %s", exc)

    async def _save_transcript_turn(
        self, speaker: str, text: str, code_snapshot: str | None = None
    ) -> None:
        """Persist transcript turn to local SQLite."""
        async with AsyncSessionLocal() as db:
            stage_val = self.fsm.current_stage.value if self.fsm else "INTRO"
            turn = TranscriptTurnModel(
                session_id=self.session_id,
                stage=stage_val,
                speaker=speaker,
                text=text,
                code_snapshot=code_snapshot,
            )
            db.add(turn)
            await db.commit()

    async def handle_client(self) -> None:
        """Main loop multiplexing client WebSocket messages with Gemini Live or mock engine."""
        await self.websocket.accept()
        await self.initialize()

        # Send initial FSM snapshot
        active_q = (
            get_question_by_id(self.fsm.active_question_id)
            if self.fsm and self.fsm.active_question_id
            else None
        )
        snapshot = self.fsm.get_snapshot(active_q)
        await self.websocket.send_json({"type": "fsm_snapshot", "data": snapshot.model_dump()})

        # Run Live connection or local simulated engine
        if self.api_key and self.settings.ENVIRONMENT != "test":
            await self._run_gemini_live_loop()
        else:
            await self._run_local_simulated_loop()

    async def _run_gemini_live_loop(self) -> None:
        """Connect to google-genai Multimodal Live API."""
        client = genai.Client(api_key=self.api_key)
        claims_summary = (
            self.claim_graph.model_dump_json() if self.claim_graph else "Standard Senior Profile"
        )
        system_instruction = build_interviewer_session_prompt(
            target_role=self.session_record.target_role or "Senior ML Engineer",
            target_company=self.session_record.target_company or "Top Tech",
            claim_graph_summary=claims_summary,
            active_stage=self.fsm.current_stage.value,
        )

        config = types.LiveConnectConfig(
            response_modalities=[types.LiveServerContentModality.AUDIO],
            system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                )
            ),
        )

        try:
            async with client.aio.live.connect(
                model=self.settings.LIVE_MODEL, config=config
            ) as session:
                self.gemini_session = session

                # Start concurrent sender and receiver tasks
                client_to_gemini = asyncio.create_task(self._client_to_gemini_stream(session))
                gemini_to_client = asyncio.create_task(self._gemini_to_client_stream(session))

                done, pending = await asyncio.wait(
                    [client_to_gemini, gemini_to_client],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()

        except Exception as exc:
            logger.error("Gemini Live connection error: %s; falling back to local loop", exc)
            await self._run_local_simulated_loop()

    async def _client_to_gemini_stream(self, session: Any) -> None:
        """Forward audio and visual inputs from client to Gemini Live."""
        try:
            while True:
                message = await self.websocket.receive_json()
                msg_type = message.get("type")

                if msg_type == "audio":
                    pcm_base64 = message.get("data")
                    if pcm_base64:
                        pcm_bytes = base64.b64decode(pcm_base64)
                        await session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[
                                    types.Blob(
                                        data=pcm_bytes,
                                        mime_type=f"audio/pcm;rate={self.settings.AUDIO_INPUT_SAMPLE_RATE}",
                                    )
                                ]
                            )
                        )

                elif msg_type == "canvas_update":
                    img_data = message.get("image_base64", "")
                    if "," in img_data:
                        img_data = img_data.split(",")[1]
                    if img_data:
                        jpg_bytes = base64.b64decode(img_data)
                        await session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[types.Blob(data=jpg_bytes, mime_type="image/jpeg")]
                            )
                        )

                elif msg_type == "code_update":
                    code = message.get("code", "")
                    lang = message.get("language", "python")
                    stdout = message.get("stdout", "")
                    prompt_txt = (
                        f"[Candidate updated {lang} code]:\n{code}\nExecution stdout: {stdout}"
                    )
                    await session.send(input=prompt_txt, end_of_turn=True)
                    # Trigger async shadow supervisor evaluation
                    asyncio.create_task(self._trigger_shadow_supervisor(code, prompt_txt))

                elif msg_type == "working_state":
                    is_active = message.get("is_active", False)
                    if self.fsm:
                        self.fsm.set_working_state(is_active)

        except WebSocketDisconnect:
            logger.info("Client disconnected from WebSocket")
        except asyncio.CancelledError:
            pass

    async def _gemini_to_client_stream(self, session: Any) -> None:
        """Stream synthesized 24kHz audio and text back from Gemini Live to client."""
        try:
            async for response in session.receive():
                server_content = response.server_content
                if server_content is None:
                    continue

                model_turn = server_content.model_turn
                if model_turn:
                    for part in model_turn.parts:
                        # Forward audio chunk
                        if part.inline_data:
                            audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                            await self.websocket.send_json(
                                {
                                    "type": "audio_chunk",
                                    "data": audio_b64,
                                    "sample_rate": self.settings.AUDIO_OUTPUT_SAMPLE_RATE,
                                }
                            )
                        # Forward text caption
                        if part.text:
                            await self.websocket.send_json(
                                {
                                    "type": "transcript_caption",
                                    "speaker": "interviewer",
                                    "text": part.text,
                                }
                            )
                            await self._save_transcript_turn("interviewer", part.text)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Error receiving from Gemini Live: %s", exc)

    async def _trigger_shadow_supervisor(
        self, code_snippet: str | None, transcript_turn: str
    ) -> None:
        """Slow Loop: Run async shadow evaluator and inject probes if needed."""
        assessment = await evaluate_turn_in_shadow(
            transcript_turn=transcript_turn,
            code_snippet=code_snippet,
            api_key=self.api_key,
        )
        if assessment.has_technical_gap and assessment.injected_directive:
            logger.info("Shadow supervisor injected directive: %s", assessment.injected_directive)
            if self.gemini_session:
                try:
                    await self.gemini_session.send(
                        input=f"[SYSTEM DIRECTIVE FOR INTERVIEWER]: {assessment.injected_directive}",
                        end_of_turn=True,
                    )
                except Exception as exc:
                    logger.warning("Could not inject directive to Gemini Live: %s", exc)

    async def _run_local_simulated_loop(self) -> None:
        """Local-first fallback loop for testing, zero-cost development, or offline mode."""
        try:
            # Send initial greeting caption
            greeting = (
                f"Hello. Welcome to the technical interview for {self.session_record.target_role}. "
                "Let's begin with a 60-second summary of your background and production ML experience."
            )
            await self.websocket.send_json(
                {
                    "type": "transcript_caption",
                    "speaker": "interviewer",
                    "text": greeting,
                }
            )
            await self._save_transcript_turn("interviewer", greeting)

            while True:
                msg = await self.websocket.receive_json()
                msg_type = msg.get("type")

                if msg_type == "close":
                    break

                elif msg_type == "text_turn":
                    user_text = msg.get("text", "")
                    await self._save_transcript_turn("candidate", user_text)

                    # Trigger shadow assessment
                    asyncio.create_task(self._trigger_shadow_supervisor(None, user_text))

                    # Generate stage-aware response
                    current_stage = self.fsm.current_stage.value if self.fsm else "INTRO"
                    if current_stage == "INTRO":
                        reply = (
                            f"Thank you for that background summary. Let's move directly into our technical challenge for {self.session_record.target_role}. "
                            "Please review the problem statement in your technical workbench and walk me through your initial approach before writing code."
                        )
                    elif current_stage == "LIVE_CODING_SQL_PYTHON":
                        reply = (
                            "Good framing. What are the key edge cases (e.g. empty inputs, duplicate keys) and how does your approach achieve optimal Big-O time and space complexity?"
                        )
                    elif current_stage == "ML_SYSTEM_DESIGN":
                        reply = (
                            "Understood. How would your architecture handle downstream feature store degradation if p99 latency spikes during peak 50,000 QPS load?"
                        )
                    elif current_stage == "RESUME_DEEP_DIVE":
                        reply = (
                            "How did you prevent temporal data leakage between your training features and inference pipeline, and what was your label delay window?"
                        )
                    else:
                        reply = (
                            "Understood. Let's discuss the production trade-offs and monitoring metrics for this implementation."
                        )

                    await self.websocket.send_json(
                        {
                            "type": "transcript_caption",
                            "speaker": "interviewer",
                            "text": reply,
                        }
                    )
                    await self._save_transcript_turn("interviewer", reply)

                elif msg_type == "code_update":
                    code = msg.get("code", "")
                    stdout = msg.get("stdout", "")
                    error = msg.get("error")
                    await self._save_transcript_turn(
                        "candidate",
                        f"[Code Update]:\n{code}\n[Stdout]: {stdout}" + (f"\n[Error]: {error}" if error else ""),
                        code_snapshot=code,
                    )
                    asyncio.create_task(
                        self._trigger_shadow_supervisor(code, f"Code execution stdout: {stdout}; Error: {error}")
                    )

                    # Provide immediate technical feedback on code execution
                    if error:
                        code_reply = (
                            f"I noticed a runtime error during execution: '{error[:120]}'. "
                            "Check your boundary conditions and explain how you would resolve that exception."
                        )
                    elif stdout and "PASS" in stdout:
                        code_reply = (
                            "Tests passed. Now walk me through the asymptotic Big-O runtime and memory space complexity of your implementation."
                        )
                    else:
                        code_reply = (
                            "Code update received. Walk me through your design and how this solution handles scale."
                        )

                    await self.websocket.send_json(
                        {
                            "type": "transcript_caption",
                            "speaker": "interviewer",
                            "text": code_reply,
                        }
                    )
                    await self._save_transcript_turn("interviewer", code_reply)

                elif msg_type == "working_state":
                    is_active = msg.get("is_active", False)
                    if self.fsm:
                        self.fsm.set_working_state(is_active)

                elif msg_type == "advance_stage":
                    if self.fsm:
                        new_stage, announcement = self.fsm.transition_next()
                        active_q = (
                            get_question_by_id(self.fsm.active_question_id)
                            if self.fsm.active_question_id
                            else None
                        )
                        snapshot = self.fsm.get_snapshot(active_q)
                        await self.websocket.send_json(
                            {"type": "fsm_snapshot", "data": snapshot.model_dump()}
                        )
                        await self.websocket.send_json(
                            {
                                "type": "transcript_caption",
                                "speaker": "interviewer",
                                "text": announcement,
                            }
                        )
                        await self._save_transcript_turn("interviewer", announcement)

        except WebSocketDisconnect:
            logger.info("Local session WebSocket disconnected")
