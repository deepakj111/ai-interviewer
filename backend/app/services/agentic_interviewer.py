"""Agentic Technical Interview Orchestrator — Persistent Multi-Turn Chat Architecture.

Implements a 2026 production-grade agentic interview framework using the
Google GenAI SDK's native multi-turn chat session (`client.aio.chats.create`).
This gives the interviewer true conversational memory: the model natively
tracks everything discussed, never repeats questions, and naturally
acknowledges the candidate's answers before asking follow-ups.

Key capabilities:
- Persistent multi-turn Gemini chat session (no manual history serialization)
- Dynamic self-introduction with persona + company adaptation
- LLM-powered silence handling (context-aware, not static strings)
- LLM-powered code feedback (understands what the code does)
- LLM-powered question explanation and hint generation
- Cultural & technical adaptation: FAANG, Indian Product, AI Startup archetypes
- Native Gemini Google Search grounding for recent company questions
"""

import asyncio
import logging

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import (
    CandidateClaimGraph,
    CompanyArchetype,
    InterviewMode,
    InterviewStage,
    QuestionItem,
)
from app.services.gemini_search_grounding import fetch_recent_company_interview_questions

logger = logging.getLogger(__name__)


PERSONA_PROFILES: dict[str, dict[str, str]] = {
    "elena": {
        "name": "Dr. Elena Vance",
        "title": "Principal Bar-Raiser & Machine Learning Scientist",
        "background": "over a decade building production distributed ranking engines and statistical foundations",
        "style": "rigorous, calm, analytical, and deeply interested in mathematical clarity and edge cases",
    },
    "alex": {
        "name": "Alex Chen",
        "title": "Staff ML Infrastructure Architect",
        "background": "building high-throughput low-latency feature stores, vLLM inference clusters, and streaming Kafka pipelines",
        "style": "practical, systems-focused, obsessed with p99 latency SLAs, memory bounds, and failure modes",
    },
    "sarah": {
        "name": "Sarah Jenkins",
        "title": "Senior Staff Applied Scientist",
        "background": "designing multi-modal generative models, two-tower neural retrieval, and continuous offline/online experimentation",
        "style": "encouraging yet uncompromising on statistical rigor, data leakage, and metric alignment",
    },
}


def _build_interviewer_system_instruction(
    persona: dict[str, str],
    target_role: str,
    target_company: str,
    company_archetype: str,
    interview_mode: str,
    claim_graph_summary: str,
    recent_company_questions: list[str],
) -> str:
    """Build a comprehensive system instruction for the persistent chat session."""
    company_qs = ""
    if recent_company_questions:
        company_qs = (
            f"\nRecently Reported Interview Questions at {target_company}:\n"
            + "\n".join(f"- {q}" for q in recent_company_questions[:5])
            + "\n"
        )

    return f"""You are {persona["name"]}, {persona["title"]} at {target_company}.
Your background: {persona["background"]}.
Your style: {persona["style"]}.

You are conducting a live technical interview for the position of {target_role}.
Interview Track: {interview_mode}. Company Archetype: {company_archetype}.
Candidate Profile Summary: {claim_graph_summary}
{company_qs}

=== CORE BEHAVIORAL RULES (NON-NEGOTIABLE) ===

1. YOU ARE A HUMAN INTERVIEWER, NOT A CHATBOT.
   - Speak naturally, conversationally, warmly. Use filler words occasionally ("So...", "Right...", "Let's see...").
   - Your responses are spoken aloud via text-to-speech, so write for the ear, not the eye.
   - Keep responses SHORT: 1 to 4 sentences maximum per turn. An interviewer who talks too much is failing.
   - Use natural transitions: "That makes sense. Building on that...", "Okay so...", "Interesting — so what about..."

2. ALWAYS ACKNOWLEDGE WHAT THE CANDIDATE JUST SAID.
   - Before asking your next question, briefly reference or paraphrase what the candidate said.
   - Examples: "Right, so you're thinking of using a two-tower architecture...", "Okay, you mentioned using L2 regularization..."
   - If the candidate's answer is wrong or vague, address it directly: "Hmm, I think there's a subtlety you might be missing there..."
   - NEVER ignore the candidate's answer and jump to an unrelated question.

3. ZERO SYCOPHANCY (ABSOLUTE RULE).
   - NEVER say: "Great answer!", "Awesome!", "Spot on!", "Brilliant!", "That's exactly right!", "I love that!", "Good job!"
   - Neutral acknowledgments only: "Right.", "Got it.", "Makes sense.", "Noted.", "Okay."
   - If the answer is strong, demonstrate that by asking a harder follow-up, not by praising.

4. NEVER REPEAT A QUESTION.
   - You have full memory of everything discussed. Never ask the same question or same topic twice.
   - Naturally progress through different topics and increasing difficulty.
   - Track what areas you've covered and what remains.

5. ADAPTIVE QUESTION FLOW.
   - Start with warm, accessible questions and gradually increase difficulty.
   - If the candidate struggles, simplify and give scaffolding. Don't push harder on a dead end.
   - If the candidate is strong, accelerate and go deeper into edge cases and production trade-offs.
   - Ask follow-up probing questions based on their specific answer, not generic follow-ups.

6. RESPECT SILENCE AND THINKING TIME.
   - When the candidate is thinking or coding, don't rush them.
   - When prompted that the candidate has been silent, check in warmly and supportively.
   - Never barrel ahead with new questions while the candidate is formulating their thoughts.

7. INTERVIEW STAGE AWARENESS.
   - You will receive [SYSTEM] messages indicating the current interview stage.
   - Adapt your questions to the stage (intro, breadth, depth, coding, design, wrap-up).
   - Naturally transition between stages with conversational bridges.

8. WHEN THE CANDIDATE SAYS SOMETHING YOU DISAGREE WITH:
   - Challenge them constructively: "Hmm, I'm not sure that's quite right. Think about what happens when..."
   - Guide them toward the right answer with Socratic probing, don't just correct them.

=== TRACK-SPECIFIC GUIDANCE ===

ML BREADTH: Quick-fire conceptual questions across fundamentals — metrics, bias-variance, regularization, tree vs. neural, optimization, data preprocessing, feature engineering.

ML DEPTH: Deep mathematical probing — loss function derivations, gradient flows, attention mechanics, normalization layers, position encoding, knowledge distillation, LoRA/QLoRA.

GENERATIVE AI / LLM: RAG pipelines, chunking strategies, vector indexing (HNSW/IVF), fine-tuning vs. in-context learning, KV cache management, speculative decoding, guardrails, agent architectures.

LIVE CODING: Guide to the active problem, assess algorithmic thinking, time/space complexity, edge case handling. Let them code — don't over-talk.

ML SYSTEM DESIGN: Data pipelines, feature stores, model serving, A/B testing, monitoring, feedback loops. Probe latency budgets and failure modes.

BEHAVIORAL/WRAP-UP: Engineering ownership, cross-functional collaboration, production incident handling. End professionally.
"""


class AgenticInterviewer:
    """Production-grade Agentic Interviewer with persistent Gemini multi-turn chat memory."""

    def __init__(
        self,
        session_id: str,
        target_role: str = "Senior Machine Learning Engineer",
        target_company: str = "Top Tech",
        company_archetype: str = "FAANG_GLOBAL",
        interview_mode: InterviewMode = InterviewMode.FULL_LOOP,
        persona_id: str = "elena",
        claim_graph: CandidateClaimGraph | None = None,
        enable_live_web_search: bool = False,
        api_key: str | None = None,
    ):
        self.session_id = session_id
        self.target_role = target_role
        self.target_company = target_company
        self.company_archetype = company_archetype
        self.interview_mode = interview_mode
        self.persona_id = persona_id
        self.persona = PERSONA_PROFILES.get(persona_id, PERSONA_PROFILES["elena"])
        self.claim_graph = claim_graph
        self.enable_live_web_search = enable_live_web_search
        self.api_key = api_key or get_settings().GEMINI_API_KEY
        self.settings = get_settings()

        # Dynamic State Tracking
        self.conversation_history: list[dict[str, str]] = []
        self.topics_covered: list[str] = []
        self.hints_given: list[str] = []
        self.recent_company_questions: list[str] = []
        self.silence_count: int = 0
        self.turns_in_current_stage: int = 0
        self.used_question_keys: set[str] = set()
        self.candidate_name: str | None = None
        self.fallback_turn_index: int = 0

        # Persistent Gemini Chat Session (lazily initialized)
        self._chat_session = None
        self._client = None

    async def initialize(self) -> None:
        """Fetch company-specific search questions if enabled or relevant."""
        try:
            self.recent_company_questions = await fetch_recent_company_interview_questions(
                company=self.target_company,
                role=self.target_role,
                track=self.interview_mode.value,
                api_key=self.api_key,
            )
        except Exception as exc:
            logger.warning("Could not pre-fetch company search questions: %s", exc)

    async def _get_chat_session(self):
        """Lazily create the persistent multi-turn Gemini chat session."""
        if self._chat_session is not None:
            return self._chat_session

        if not self.api_key or self.settings.ENVIRONMENT == "test":
            return None

        try:
            self._client = genai.Client(api_key=self.api_key)
            claims_summary = (
                self.claim_graph.model_dump_json()
                if self.claim_graph
                else "Standard Senior ML Profile"
            )
            system_instruction = _build_interviewer_system_instruction(
                persona=self.persona,
                target_role=self.target_role,
                target_company=self.target_company,
                company_archetype=self.company_archetype,
                interview_mode=self.interview_mode.value,
                claim_graph_summary=claims_summary,
                recent_company_questions=self.recent_company_questions,
            )

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.55,
                max_output_tokens=350,
            )

            self._chat_session = self._client.aio.chats.create(
                model=self.settings.INTERVIEWER_MODEL,
                config=config,
            )
            logger.info("Persistent Gemini chat session created for session %s", self.session_id)
            return self._chat_session
        except Exception as exc:
            logger.error("Failed to create Gemini chat session: %s", exc)
            return None

    async def generate_self_introduction(self, active_question: QuestionItem | None = None) -> str:
        """Dynamically generate the interviewer's natural self-introduction via the chat session."""
        chat = await self._get_chat_session()
        if chat:
            try:
                q_context = ""
                if active_question:
                    q_context = (
                        f"\n[SYSTEM: The first technical problem prepared is: '{active_question.title}' "
                        f"({active_question.category.value}). You'll introduce it naturally after the candidate "
                        f"introduces themselves. Don't mention it yet in your greeting.]"
                    )

                prompt = (
                    f"[SYSTEM: The interview is starting now. Current stage: INTRO. "
                    f"Generate your natural, spoken self-introduction (3-4 sentences). "
                    f"Introduce yourself warmly by name and role. Explain the interview structure briefly. "
                    f"Then invite the candidate to give a 60-second background overview. "
                    f"Sound genuine and human — this will be spoken aloud.]{q_context}"
                )

                response = await asyncio.wait_for(chat.send_message(prompt), timeout=10.0)
                if response.text and len(response.text.strip()) > 30:
                    intro = response.text.strip()
                    self.conversation_history.append(
                        {"speaker": "interviewer", "text": intro, "stage": "INTRO"}
                    )
                    return intro
            except Exception as exc:
                logger.warning("Chat session intro generation failed: %s; using template", exc)

        # Fallback template introduction
        return self._generate_fallback_introduction()

    def _generate_fallback_introduction(self) -> str:
        """Archetype-aware fallback introduction when LLM is unavailable."""
        if self.company_archetype == CompanyArchetype.INDIAN_PRODUCT:
            return (
                f"I'm {self.persona['name']}, {self.persona['title']} here at {self.target_company}. "
                f"My team focuses on solving high-throughput hyperlocal challenges and real-time ML systems at Indian scale. "
                "Today's session is designed to be an open, collaborative technical dialogue rather than a formal test. "
                "To get us started, please walk me through your engineering journey, your key ML specializations, "
                "and a production system you've delivered."
            )
        elif self.company_archetype == CompanyArchetype.AI_STARTUP:
            return (
                f"Hi there! I'm {self.persona['name']}, {self.persona['title']} at {self.target_company}. "
                "We move extremely fast and focus on shipping pragmatic, high-impact AI systems and low-latency inference. "
                "I'm excited to speak with you today. Feel free to think out loud and challenge assumptions throughout our discussion. "
                "To kick things off, tell me a bit about yourself and the most interesting technical challenge you've tackled recently."
            )
        else:
            return (
                f"Hello and welcome! I'm {self.persona['name']}, {self.persona['title']} at {self.target_company}. "
                f"I've spent {self.persona['background']}, and I'll be your interviewer today for the {self.target_role} position. "
                "Our goal today is to dive into deep engineering problems collaboratively. "
                "To begin, give me a concise 60-second summary of your technical background, core focus areas, and production experience."
            )

    async def generate_turn_response(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Generate a natural, adaptive interviewer response using the persistent chat session."""
        self.silence_count = 0
        self.turns_in_current_stage += 1

        # Record candidate utterance
        self.conversation_history.append(
            {"speaker": "candidate", "text": user_text.strip(), "stage": stage.value}
        )

        chat = await self._get_chat_session()
        if chat:
            try:
                # Build contextual system message for this turn
                q_context = ""
                if active_question:
                    q_context = (
                        f"\n[SYSTEM: Active problem: '{active_question.title}' ({active_question.category.value}). "
                        f"Problem statement: {active_question.prompt[:300]}. "
                        f"Rubric focus: {', '.join(active_question.rubric_criteria[:4])}.]"
                    )

                stage_context = f"[SYSTEM: Current interview stage: {stage.value}. Turn #{self.turns_in_current_stage} in this stage.]{q_context}"

                # The candidate's message + stage context
                message = f"{stage_context}\n\nCandidate: {user_text.strip()}"

                response = await asyncio.wait_for(chat.send_message(message), timeout=10.0)
                if response.text and len(response.text.strip()) > 5:
                    reply = response.text.strip()
                    self.conversation_history.append(
                        {"speaker": "interviewer", "text": reply, "stage": stage.value}
                    )
                    return reply
            except Exception as exc:
                logger.warning("Chat session turn failed: %s; using fallback", exc)

        # Fallback: generate a context-aware but non-LLM response
        reply = self._generate_fallback_turn(user_text, stage, active_question)
        self.conversation_history.append(
            {"speaker": "interviewer", "text": reply, "stage": stage.value}
        )
        return reply

    async def handle_silence(
        self,
        seconds_silent: int,
        stage: InterviewStage,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Generate a context-aware, empathetic prompt when candidate has been quiet.

        Uses the persistent chat session to generate contextually appropriate nudges
        rather than cycling through static strings.
        """
        self.silence_count += 1

        chat = await self._get_chat_session()
        if chat:
            try:
                q_hint = ""
                if active_question:
                    q_hint = f" The active problem is '{active_question.title}'."

                prompt = (
                    f"[SYSTEM: The candidate has been silent for {seconds_silent} seconds. "
                    f"This is silence occurrence #{self.silence_count} in this segment.{q_hint} "
                    f"Current stage: {stage.value}. "
                    f"Check in warmly and supportively. Be brief (1-2 sentences). "
                    f"If this is the 3rd+ silence, offer a concrete hint or suggest breaking down the problem. "
                    f"Never repeat a previous nudge. Sound human, not robotic.]"
                )

                response = await asyncio.wait_for(chat.send_message(prompt), timeout=8.0)
                if response.text and len(response.text.strip()) > 10:
                    nudge = response.text.strip()
                    self.conversation_history.append(
                        {"speaker": "interviewer", "text": nudge, "stage": stage.value}
                    )
                    return nudge
            except Exception as exc:
                logger.warning("Chat session silence handling failed: %s", exc)

        # Fallback static responses
        if self.silence_count == 1:
            return (
                "Take your time to think through the problem. "
                "Feel free to think out loud as you reason through it, or let me know if you want to clarify any assumptions."
            )
        elif self.silence_count == 2:
            return (
                "Whenever you're ready, walk me through what's on your mind. "
                "We can also discuss potential directions or trade-offs together if that helps."
            )
        return "I'm here whenever you're ready to proceed. Would you like a targeted hint to help kick off your solution?"

    async def generate_code_feedback(
        self,
        code: str,
        language: str,
        stdout: str,
        error: str | None = None,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Generate intelligent, context-aware feedback on code execution via the chat session."""
        chat = await self._get_chat_session()
        if chat:
            try:
                q_context = ""
                if active_question:
                    q_context = f" Problem: '{active_question.title}'."

                error_info = f"\nExecution Error: {error}" if error else ""

                prompt = (
                    f"[SYSTEM: The candidate just submitted/executed {language} code.{q_context}]\n"
                    f"```{language}\n{code[:1500]}\n```\n"
                    f"Execution stdout: {stdout[:500]}{error_info}\n\n"
                    f"[SYSTEM: Give brief, specific spoken feedback (2-3 sentences). "
                    f"If there's an error, help them identify the root cause without giving the answer. "
                    f"If it works, probe complexity or edge cases. Sound conversational.]"
                )

                response = await asyncio.wait_for(chat.send_message(prompt), timeout=10.0)
                if response.text and len(response.text.strip()) > 10:
                    feedback = response.text.strip()
                    self.conversation_history.append(
                        {
                            "speaker": "interviewer",
                            "text": feedback,
                            "stage": "LIVE_CODING_SQL_PYTHON",
                        }
                    )
                    return feedback
            except Exception as exc:
                logger.warning("Chat session code feedback failed: %s", exc)

        # Fallback: basic keyword-based code feedback
        return self._generate_fallback_code_feedback(code, language, stdout, error, active_question)

    def _generate_fallback_turn(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None,
    ) -> str:
        """Context-aware, non-repetitive conversational engine for offline and simulated modes.
        Understands candidate greetings, requests for constraints, hint inquiries, and domain answers."""
        u_lower = user_text.lower().strip()
        self.fallback_turn_index += 1

        # 1. Candidate Introductions & Greetings
        if any(w in u_lower for w in ["hi ", "hello", "hey", "my name is", "i am ", "i'm ", "years of experience", "background in"]):
            if "my name is" in u_lower:
                parts = u_lower.split("my name is")
                if len(parts) > 1 and parts[1].strip():
                    self.candidate_name = parts[1].strip().split()[0].strip(".,!?:;").capitalize()
            elif "i am " in u_lower:
                parts = u_lower.split("i am ")
                if len(parts) > 1 and parts[1].strip():
                    first_word = parts[1].strip().split()[0].strip(".,!?:;")
                    if len(first_word) > 2 and first_word not in ["a", "an", "the", "currently", "working"]:
                        self.candidate_name = first_word.capitalize()

            name_salutation = f" {self.candidate_name}" if self.candidate_name else ""
            q_lead = f" For our first problem today, '{active_question.title}', " if active_question else " To start our technical evaluation, "
            return (
                f"Nice to meet you{name_salutation}! Thank you for walking me through your background. "
                f"{q_lead}how do you typically structure your initial solution and validate your architectural assumptions?"
            )

        # 2. Clarification & Constraint Requests
        if any(w in u_lower for w in ["constraint", "constraints", "requirement", "requirements", "sla", "qps", "latency", "explain the question", "explain the problem", "detail"]):
            if active_question:
                return (
                    f"Good instinct to clarify requirements upfront. For '{active_question.title}': "
                    f"Assume target p99 latency SLA is under 25ms, traffic volume is around 15,000 QPS, and the system needs to gracefully handle missing features. "
                    "How would you formulate your baseline approach to meet that latency budget?"
                )
            return (
                "Good question on constraints. Assume standard production SLA: p99 under 30ms, roughly 10k QPS peak, "
                "with distributed sharding. Walk me through your design choices given those boundaries."
            )

        # 3. Hint Requests
        if any(w in u_lower for w in ["hint", "stuck", "suggest", "unsure", "not sure", "help", "nudge"]):
            if active_question:
                criteria = ", ".join(active_question.rubric_criteria[:2]) if active_question.rubric_criteria else "decoupling ranking from retrieval"
                return (
                    f"Here is a targeted hint: Think about {criteria}. "
                    "Consider separating the problem into an efficient high-recall candidate generator followed by a precision ranker. "
                    "What data structure or algorithmic formulation would you use for that first pass?"
                )
            return (
                "Here is a helpful hint: Start by establishing a simple baseline that solves the core problem correctly. "
                "Then we can optimize the Big-O time and space complexity together. How would you sketch the initial logic?"
            )

        # 4. TRACK 1: ML BREADTH ROUND
        if stage == InterviewStage.ML_BREADTH or self.interview_mode == InterviewMode.ML_BREADTH:
            if any(w in u_lower for w in ["regularization", "l1", "l2", "lasso", "ridge"]):
                return (
                    "You highlighted the geometric sparsity of L1 regularization. "
                    "In high-dimensional feature spaces where many features are correlated, "
                    "why does Lasso arbitrarily pick one feature over another, and how does Elastic Net mitigate that instability?"
                )
            if any(w in u_lower for w in ["bias", "variance", "overfitting", "underfitting"]):
                return (
                    "Good distinction on the bias-variance trade-off. "
                    "If you notice that your training error is 2% while cross-validation error is 18%, "
                    "walk me through your systematic checklist of the first 3 actions you take to diagnose and remediate."
                )
            if any(w in u_lower for w in ["roc", "pr-auc", "precision", "recall", "f1"]):
                return (
                    "Understanding metric trade-offs is critical. In a high-imbalance setting like fraud detection where only 0.05% of transactions are fraudulent, "
                    "why can ROC-AUC present an overly optimistic assessment of model quality compared to PR-AUC?"
                )
            if any(w in u_lower for w in ["tree", "xgboost", "random forest", "gradient boost"]):
                return (
                    "Tree-based models excel on tabular data. What is the fundamental difference in how Random Forests reduce variance via bagging "
                    "versus how Gradient Boosted Trees reduce bias via sequential residual fitting?"
                )
            if any(w in u_lower for w in ["gradient descent", "sgd", "adam", "learning rate", "optimizer"]):
                return (
                    "Adam computes adaptive moments for each parameter. "
                    "In what scenarios can Adam's second-moment estimation cause convergence instability, and why is weight decay decoupled in AdamW?"
                )

        # 5. TRACK 2: ML DEPTH ROUND
        if stage == InterviewStage.ML_DEPTH or self.interview_mode == InterviewMode.ML_DEPTH:
            if any(w in u_lower for w in ["loss", "gradient", "cross-entropy", "sigmoid", "softmax"]):
                return (
                    "When computing the loss gradient for sigmoid activations, explain how saturation can cause "
                    "gradients to vanish during backpropagation, and how modern initialization or normalization stabilizes this."
                )
            if any(w in u_lower for w in ["attention", "transformer", "flashattention"]):
                return (
                    "Multi-Head Attention computes softmax(QK^T / sqrt(d_k)) * V. "
                    "Walk me through the memory bottleneck of materializing the N x N attention matrix, "
                    "and explain how FlashAttention's online softmax recomputation allows computation entirely in fast GPU SRAM."
                )
            if any(w in u_lower for w in ["lora", "qlora", "low-rank", "rank", "svd"]):
                return (
                    "In Low-Rank Adaptation (LoRA), we decompose weight updates into W + B * A where B is d x r and A is r x k. "
                    "How do you initialize matrices A and B at the start of training so that the initial forward pass is an exact identity with the base model?"
                )

        # 6. TRACK 3: GENERATIVE AI & LLM
        if stage == InterviewStage.GENERATIVE_AI or self.interview_mode == InterviewMode.GENERATIVE_AI_LLM:
            if any(w in u_lower for w in ["rag", "chunk", "chunking", "retrieval", "hybrid"]):
                return (
                    "A hybrid dense-sparse retrieval pipeline with BM25 and vector embeddings is solid. "
                    "How do you handle late-chunking or parent-document retrieval so that the LLM has sufficient context without blowing through prompt token limits?"
                )
            if any(w in u_lower for w in ["dpo", "rlhf", "preference", "kto"]):
                return (
                    "Direct Preference Optimization (DPO) bypasses training a separate reward model. "
                    "Mathematically, how does DPO express the reward function directly in terms of the policy model and reference model ratio?"
                )
            if any(w in u_lower for w in ["kv cache", "speculative", "pagedattention", "vllm"]):
                return (
                    "KV cache memory management is the primary bottleneck for concurrent LLM serving. "
                    "How does PagedAttention eliminate internal and external memory fragmentation, and what is the latency benefit of Speculative Decoding with a small draft model?"
                )

        # 7. TRACK 4: CODING & SYSTEM DESIGN
        if stage == InterviewStage.LIVE_CODING_SQL_PYTHON:
            if any(w in u_lower for w in ["window", "partition", "row_number", "dense_rank"]):
                return (
                    "Using window functions with partitioning is a clean strategy. "
                    "How do you plan to handle partitions with null or missing timestamps?"
                )
            if any(w in u_lower for w in ["dict", "hash", "map", "set", "o(1)"]):
                return (
                    "Using a hash map gives O(1) expected lookup. "
                    "What is your memory footprint if the input cardinality reaches 50 million unique keys?"
                )
            return (
                "Understood. Before you start coding, can you walk me through the key invariants "
                "of your approach and the expected Big-O time and space complexity?"
            )

        if stage == InterviewStage.ML_SYSTEM_DESIGN:
            if any(w in u_lower for w in ["feature store", "feast", "redis"]):
                return (
                    "A dual-tier feature store with Redis for online inference and Parquet for training works well. "
                    f"At {self.target_company}'s scale, how do you handle feature freshness when network latency causes out-of-order writes?"
                )
            if any(w in u_lower for w in ["kafka", "flink", "streaming", "event"]):
                return (
                    "Streaming event architectures handle real-time ingestion cleanly. "
                    "How do you guarantee exactly-once processing semantics during sudden consumer node crashes?"
                )

        # 8. Dynamic Non-Repetitive Progressive Follow-Ups
        follow_up_pool = [
            f"That gives us a solid direction. Looking at {self.target_company}'s production requirements, what is the single largest bottleneck in this design under peak load?",
            "Makes sense. How would you detect and mitigate data drift or concept drift once this model runs in production for 6 months?",
            "Let's look at failure modes. If the primary caching layer experiences a cold-start restart, how does your system prevent a cascading database outage?",
            "Good analysis. Walk me through the offline evaluation metrics versus the online business KPIs you would track in an A/B test.",
            f"Understood. How would you structure cross-functional ownership between data engineering, ML modeling, and platform teams for this system at {self.target_company}?",
        ]

        # Rotate through pool non-repetitively
        chosen = follow_up_pool[self.fallback_turn_index % len(follow_up_pool)]
        return chosen

    def _generate_fallback_code_feedback(
        self,
        code: str,
        language: str,
        stdout: str,
        error: str | None = None,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Fallback code feedback when LLM is unavailable."""
        if error:
            err_msg = error.strip()
            if "Traceback" in err_msg:
                lines = err_msg.split("\n")
                last_line = lines[-1] if lines else err_msg
                return (
                    f"I see an unhandled exception: '{last_line[:120]}'. "
                    "Take a close look at your variable bindings and edge cases. "
                    "What do you think is causing this?"
                )
            return (
                f"There's an execution error: '{err_msg[:120]}'. "
                "Check your syntax and references. What do you think caused this?"
            )

        if stdout and ("PASS" in stdout.upper() or "PASSED" in stdout.upper()):
            return (
                "All test assertions passed. Now walk me through the Big-O runtime and "
                "space complexity, and how this scales to large inputs."
            )

        return (
            "Code execution completed. Walk me through the mechanics of your solution "
            "and what edge cases you've accounted for."
        )
