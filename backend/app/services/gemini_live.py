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
from app.services.agentic_interviewer import AgenticInterviewer
from app.services.fsm_orchestrator import InterviewFSM
from app.services.interviewer_engine import InterviewerEngine
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
        self.engine: InterviewerEngine | None = None
        self.conversation_history: list[dict[str, str]] = []

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

            if getattr(session, "api_key", None) and not self.api_key:
                self.api_key = session.api_key

            archetype = getattr(session, "company_archetype", "FAANG_GLOBAL") or "FAANG_GLOBAL"
            enable_search = getattr(session, "enable_live_web_search", False) or False

            self.engine = InterviewerEngine(
                session_id=self.session_id,
                target_role=session.target_role or "Senior ML Engineer",
                target_company=session.target_company or "Top Tech",
                company_archetype=archetype,
                interview_mode=mode,
                claim_graph=self.claim_graph,
                api_key=self.api_key,
            )

            self.agent = AgenticInterviewer(
                session_id=self.session_id,
                target_role=session.target_role or "Senior ML Engineer",
                target_company=session.target_company or "Top Tech",
                company_archetype=archetype,
                interview_mode=mode,
                claim_graph=self.claim_graph,
                enable_live_web_search=enable_search,
                api_key=self.api_key,
            )
            await self.agent.initialize()

    async def _save_transcript_turn(
        self, speaker: str, text: str, code_snapshot: str | None = None
    ) -> None:
        """Persist transcript turn to local SQLite and memory history."""
        stage_val = self.fsm.current_stage.value if self.fsm else "INTRO"
        self.conversation_history.append({"speaker": speaker, "text": text, "stage": stage_val})
        async with AsyncSessionLocal() as db:
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

                # Kick off initial interviewer self-introduction turn
                active_q = (
                    get_question_by_id(self.fsm.active_question_id)
                    if self.fsm and self.fsm.active_question_id
                    else None
                )
                intro_prompt = await self.agent.generate_self_introduction(active_q)
                try:
                    await session.send(
                        input=f"[SYSTEM DIRECTIVE: Welcome the candidate and give your self-introduction now]: {intro_prompt}",
                        end_of_turn=True,
                    )
                except Exception as exc:
                    logger.warning("Could not send initial intro directive to Gemini Live: %s", exc)

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

                elif msg_type == "text_turn":
                    user_text = message.get("text", "")
                    await self._save_transcript_turn("candidate", user_text)
                    await session.send(input=f"[Candidate]: {user_text}", end_of_turn=True)

                elif msg_type == "interrupt":
                    logger.info("Candidate barge-in interruption received in live stream")

                elif msg_type == "silence_ping":
                    sec = message.get("seconds_silent", 30)
                    logger.info("Silence ping (%ds) received in live stream, prompting AI", sec)
                    directive = (
                        f"[SYSTEM DIRECTIVE: The candidate has been silent for {sec} seconds. "
                        f"Check in warmly and supportively. Remind them they can think out loud, ask clarifying questions, or request a hint. "
                        f"Keep your response concise and conversational (1 to 2 sentences).]"
                    )
                    try:
                        await session.send(input=directive, end_of_turn=True)
                    except Exception as exc:
                        logger.warning("Could not send silence directive to Gemini Live: %s", exc)

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
        """Smart conversational loop delivering dynamic AI responses, question explanations, and code feedback."""
        try:
            active_q = (
                get_question_by_id(self.fsm.active_question_id)
                if self.fsm and self.fsm.active_question_id
                else None
            )
            # Send dynamic self-introduction
            current_stg = self.fsm.current_stage if self.fsm else InterviewStage.INTRO
            greeting = await self.agent.generate_self_introduction(active_q)
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

                elif msg_type == "interrupt":
                    logger.info("Local candidate barge-in interrupt received")
                    continue

                elif msg_type == "silence_ping":
                    secs = msg.get("seconds_silent", 18)
                    active_q = (
                        get_question_by_id(self.fsm.active_question_id)
                        if self.fsm and self.fsm.active_question_id
                        else None
                    )
                    current_stg = self.fsm.current_stage if self.fsm else InterviewStage.INTRO
                    nudge = await self.agent.handle_silence(
                        seconds_silent=secs,
                        stage=current_stg,
                        active_question=active_q,
                    )
                    await self.websocket.send_json(
                        {
                            "type": "transcript_caption",
                            "speaker": "interviewer",
                            "text": nudge,
                        }
                    )
                    await self._save_transcript_turn("interviewer", nudge)

                elif msg_type == "text_turn":
                    user_text = msg.get("text", "")
                    await self._save_transcript_turn("candidate", user_text)

                    # Trigger shadow assessment in background
                    asyncio.create_task(self._trigger_shadow_supervisor(None, user_text))

                    active_q = (
                        get_question_by_id(self.fsm.active_question_id)
                        if self.fsm and self.fsm.active_question_id
                        else None
                    )
                    current_stg = self.fsm.current_stage if self.fsm else InterviewStage.INTRO

                    try:
                        reply = await self.agent.generate_turn_response(
                            user_text=user_text,
                            stage=current_stg,
                            active_question=active_q,
                        )
                    except Exception as turn_exc:
                        logger.error("Error generating turn response: %s", turn_exc)
                        reply = "That makes sense. Can you walk me through your engineering design choices and the trade-offs you considered?"

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
                    lang = msg.get("language", "python")
                    stdout = msg.get("stdout", "")
                    error = msg.get("error")
                    await self._save_transcript_turn(
                        "candidate",
                        f"[Code Update ({lang})]:\n{code}\n[Stdout]: {stdout}"
                        + (f"\n[Error]: {error}" if error else ""),
                        code_snapshot=code,
                    )
                    asyncio.create_task(
                        self._trigger_shadow_supervisor(
                            code, f"Code execution stdout: {stdout}; Error: {error}"
                        )
                    )

                    active_q = (
                        get_question_by_id(self.fsm.active_question_id)
                        if self.fsm and self.fsm.active_question_id
                        else None
                    )
                    try:
                        # Use the agent's LLM-powered code feedback (persistent chat context)
                        code_reply = await self.agent.generate_code_feedback(
                            code=code,
                            language=lang,
                            stdout=stdout,
                            error=error,
                            active_question=active_q,
                        )
                    except Exception as code_exc:
                        logger.error("Error generating code feedback: %s", code_exc)
                        code_reply = "I see your code execution update. Walk me through the mechanics of your solution and the edge cases you've accounted for."

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
