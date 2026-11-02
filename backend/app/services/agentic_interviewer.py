"""Agentic Technical Interview Orchestrator.

Implements a modern 2026 production-grade agentic interview framework:
- Dynamic self-introduction (Interviewer introduces themselves, their team, and sets the agenda)
- Conversational tracking & multi-turn memory (no pre-decided static arrays)
- Track-specific intelligence: ML Breadth, ML Depth, Generative AI / LLM, Coding, System Design
- Cultural & technical adaptation: FAANG scale, Indian Product Giants (Swiggy/CRED/Razorpay/Zomato), AI Startups
- Empathetic silence handling (waits for candidate; never blabbers ahead)
- Live interruption & barge-in support
- Native Gemini Google Search grounding for recent company questions
"""

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
from app.services.interviewer_engine import (
    answer_clarification_question,
    explain_question_in_detail,
    provide_hint,
)

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


class AgenticInterviewer:
    """Production-grade Agentic Interviewer orchestrating human-like technical dialogue."""

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

    async def generate_self_introduction(self, active_question: QuestionItem | None = None) -> str:
        """Dynamically generate the interviewer's natural self-introduction.

        The interviewer introduces themselves, their team, their engineering focus,
        sets the interview agenda, and warmly asks the candidate to introduce themselves.
        """
        # If API key available, generate dynamic, unique greeting via Gemini
        if self.api_key and self.settings.ENVIRONMENT != "test":
            try:
                client = genai.Client(api_key=self.api_key)
                prompt = (
                    f"You are {self.persona['name']}, {self.persona['title']} at {self.target_company}. "
                    f"Your background: {self.persona['background']}. Your style: {self.persona['style']}. "
                    f"You are conducting a technical interview for the position of {self.target_role} in the {self.interview_mode.value} track. "
                    f"Company Archetype: {self.company_archetype}. "
                    "Write your natural, spoken self-introduction (3 to 4 sentences):\n"
                    "1. Introduce yourself warmly by name and your role/team at the company.\n"
                    "2. Explain the purpose and collaborative structure of today's interview.\n"
                    "3. Open the floor to the candidate with an inviting prompt for a 60-second background overview.\n"
                    "Guidelines: Sound genuine, human, professional, calm. Avoid sycophancy. Suitable for text-to-speech."
                )

                response = await client.aio.models.generate_content(
                    model=self.settings.EXTRACTOR_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=250),
                )
                if response.text and len(response.text.strip()) > 30:
                    return response.text.strip()
            except Exception as exc:
                logger.warning("Dynamic intro LLM generation failed: %s; using smart template", exc)

        # Smart Archetype-Aware Fallback Introduction
        if self.company_archetype == CompanyArchetype.INDIAN_PRODUCT:
            context_note = (
                f"I'm {self.persona['name']}, {self.persona['title']} here at {self.target_company}. "
                f"My team focuses on solving high-throughput hyperlocal challenges and real-time ML systems at Indian scale. "
                "Today's session is designed to be an open, collaborative technical dialogue rather than a formal test. "
                "To get us started, please walk me through your engineering journey, your key ML specializations, "
                "and a production system you've delivered."
            )
        elif self.company_archetype == CompanyArchetype.AI_STARTUP:
            context_note = (
                f"Hi there! I'm {self.persona['name']}, {self.persona['title']} at {self.target_company}. "
                "We move extremely fast and focus on shipping pragmatic, high-impact AI systems and low-latency inference. "
                "I'm excited to speak with you today. Feel free to think out loud and challenge assumptions throughout our discussion. "
                "To kick things off, tell me a bit about yourself and the most interesting technical challenge you've tackled recently."
            )
        else:
            context_note = (
                f"Hello and welcome! I'm {self.persona['name']}, {self.persona['title']} at {self.target_company}. "
                f"I've spent {self.persona['background']}, and I'll be your interviewer today for the {self.target_role} position. "
                "Our goal today is to dive into deep engineering problems collaboratively. "
                "To begin, give me a concise 60-second summary of your technical background, core focus areas, and production experience."
            )

        return context_note

    async def generate_turn_response(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Generate a natural, adaptive interviewer response with full context awareness."""
        self.silence_count = 0
        self.turns_in_current_stage += 1
        u_clean = user_text.strip()
        u_lower = u_clean.lower()

        # Record candidate utterance into memory
        self.conversation_history.append(
            {"speaker": "candidate", "text": u_clean, "stage": stage.value}
        )

        # 1. Candidate explicitly asks to explain the problem
        if active_question and any(
            p in u_lower
            for p in [
                "explain the question",
                "can you explain",
                "what is the problem",
                "walk me through",
                "clarify the problem",
                "what should i do",
                "repeat the prompt",
            ]
        ):
            return explain_question_in_detail(active_question)

        # 2. Candidate asks for a hint
        if any(
            p in u_lower
            for p in [
                "give me a hint",
                "can i get a hint",
                "i am stuck",
                "i'm stuck",
                "confused on how",
                "need a hint",
            ]
        ):
            return provide_hint(active_question, self.hints_given)

        # 3. Candidate asks clarifying questions on schemas, constraints, SLAs
        if any(
            w in u_lower
            for w in [
                "can we assume",
                "what is the schema",
                "what are the columns",
                "null values",
                "duplicates",
                "what is the latency",
                "how many rows",
            ]
        ):
            return answer_clarification_question(active_question, u_clean)

        # 4. If API key is available, use Gemini Agent with complete conversation context
        if self.api_key and self.settings.ENVIRONMENT != "test":
            try:
                llm_reply = await self._generate_gemini_agent_turn(
                    user_text=u_clean,
                    stage=stage,
                    active_question=active_question,
                )
                if llm_reply and len(llm_reply.strip()) > 10:
                    self.conversation_history.append(
                        {"speaker": "interviewer", "text": llm_reply.strip(), "stage": stage.value}
                    )
                    return llm_reply.strip()
            except Exception as exc:
                logger.warning(
                    "Gemini Agent turn generation failed: %s; using local cognitive engine", exc
                )

        # 5. High-Fidelity Local Cognitive Engine (Offline & Fallback)
        reply = self._generate_local_cognitive_turn(
            user_text=u_clean,
            stage=stage,
            active_question=active_question,
        )
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
        """Generate an empathetic, patient prompt when candidate has been quiet.

        Never interrupts with new questions or advances stages unprompted.
        """
        self.silence_count += 1
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

    async def _generate_gemini_agent_turn(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None,
    ) -> str:
        """Call Gemini to formulate a context-grounded, human interviewer turn."""
        client = genai.Client(api_key=self.api_key)

        claims_summary = (
            self.claim_graph.model_dump_json() if self.claim_graph else "Senior ML Profile"
        )
        q_context = ""
        if active_question:
            q_context = (
                f"ACTIVE PROBLEM: {active_question.title} ({active_question.category.value})\n"
                f"STATEMENT: {active_question.prompt}\n"
                f"RUBRIC: {', '.join(active_question.rubric_criteria)}\n"
            )

        company_context = f"Company: {self.target_company} (Archetype: {self.company_archetype}). Role: {self.target_role}.\n"
        if self.recent_company_questions:
            company_context += (
                f"Recently Reported Questions at {self.target_company}:\n"
                + "\n".join(f"- {q}" for q in self.recent_company_questions[:3])
            )

        system_instruction = (
            f"You are {self.persona['name']}, {self.persona['title']} at {self.target_company}.\n"
            f"Persona Style: {self.persona['style']}.\n"
            f"{company_context}\n"
            f"Track: {self.interview_mode.value}. Current Stage: {stage.value}.\n"
            f"Candidate Profile: {claims_summary}\n"
            f"{q_context}\n\n"
            "CRITICAL BEHAVIORAL INSTRUCTIONS:\n"
            "1. Speak naturally as an attentive, experienced human interviewer.\n"
            "2. First directly reference and acknowledge the candidate's exact technical statements.\n"
            "3. If in ML BREADTH: Ask targeted, quick-fire conceptual questions across ML fundamentals (metrics, bias-variance, regularizations, tree vs net, optimization).\n"
            "4. If in ML DEPTH: Probe deeply into mathematical equations, analytical derivations, loss gradients, and attention mechanics.\n"
            "5. If in GENERATIVE AI: Probe into RAG chunking/retrieval/reranking, vector indexing (HNSW/IVF), LoRA/QLoRA fine-tuning, KV cache optimization, and guardrails.\n"
            "6. Keep spoken output concise (2 to 4 sentences maximum) so it feels like natural dialogue.\n"
            "7. Zero sycophancy ('Awesome!', 'Great answer!'). Stay grounded, warm, intellectually rigorous, and professional.\n"
        )

        recent_history = self.conversation_history[-8:]
        history_str = ""
        for turn in recent_history:
            spk = turn.get("speaker", "interviewer").capitalize()
            txt = turn.get("text", "")
            history_str += f"{spk}: {txt}\n"

        prompt = f"{history_str}Candidate: {user_text}\nInterviewer (spoken reply):"

        response = await client.aio.models.generate_content(
            model=self.settings.EXTRACTOR_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.35,
                max_output_tokens=300,
            ),
        )

        return response.text or ""

    def _generate_local_cognitive_turn(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None,
    ) -> str:
        """High-fidelity local cognitive dialogue manager for offline or zero-key operation."""
        u_lower = user_text.lower()
        t_count = self.turns_in_current_stage

        # --- TRACK 1: ML BREADTH ROUND ---
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

            breadth_questions = [
                "Let's test foundational ML breadth: compare Batch Gradient Descent, Mini-Batch SGD, and Adam. What problem does Adam's second-moment estimation solve?",
                "How do you handle high-cardinality categorical features (like user IDs or postal codes) in a model without causing extreme memory explosion?",
                "When scaling a binary classifier to production, how do you verify whether predicted probabilities are well-calibrated using Platt scaling or isotonic regression?",
            ]
            return breadth_questions[(t_count - 1) % len(breadth_questions)]

        # --- TRACK 2: ML DEPTH ROUND ---
        if stage == InterviewStage.ML_DEPTH or self.interview_mode == InterviewMode.ML_DEPTH:
            if any(
                w in u_lower
                for w in ["gradient", "derivative", "sigmoid", "cross-entropy", "cross entropy"]
            ):
                return (
                    "Good derivation. Notice that the derivative simplifies cleanly to (p - y). "
                    "When the model is heavily confident and wrong (p ≈ 1 when y = 0), what happens to the gradient magnitude, "
                    "and why does mean squared error fail to penalize that as sharply?"
                )
            if any(
                w in u_lower for w in ["attention", "transformer", "flashattention", "sram", "qk"]
            ):
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

            depth_questions = [
                "Let's dive into deep optimization mechanics: walk me through the mathematical equations of LayerNorm versus RMSNorm. What computational advantage does RMSNorm provide during inference?",
                "In transformer position encoding, compare Rotary Position Embedding (RoPE) with sinusoidal absolute position embeddings in terms of extrapolation beyond the context window.",
                "Explain the exact mechanics of Knowledge Distillation: how does the temperature parameter soften probability distributions, and what does the loss gradient look like?",
            ]
            return depth_questions[(t_count - 1) % len(depth_questions)]

        # --- TRACK 3: GENERATIVE AI & LLM TRACK ---
        if (
            stage == InterviewStage.GENERATIVE_AI
            or self.interview_mode == InterviewMode.GENERATIVE_AI_LLM
        ):
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

            genai_questions = [
                "When building an enterprise LLM agent with autonomous tool-calling, how do you structure fallback recovery when an API tool returns a malformed response or times out?",
                "Compare the pros and cons of fine-tuning with QLoRA on a 4-bit quantized base model versus using in-context learning with dynamic semantic few-shot selection.",
                "How would you build an automated evaluation framework to benchmark hallucination rates and faithfulness in a production RAG application?",
            ]
            return genai_questions[(t_count - 1) % len(genai_questions)]

        # --- TRACK 4: LIVE CODING & SYSTEM DESIGN ---
        if stage == InterviewStage.LIVE_CODING_SQL_PYTHON:
            if any(w in u_lower for w in ["window", "partition", "row_number", "dense_rank"]):
                return (
                    "Using window functions with partitioning is a clean strategy. "
                    "Pay close attention to how ties are ranked and whether your window frame includes unbounded preceding rows. "
                    "How do you plan to handle partitions with null or missing timestamps?"
                )
            if any(w in u_lower for w in ["dict", "hash", "map", "set", "o(1)"]):
                return (
                    "Using a hash map gives O(1) expected lookup. "
                    "What is your memory footprint if the input cardinality reaches 50 million unique keys? "
                    "Could we prune keys in-place or use a generator to preserve linear space?"
                )
            return (
                f"That's a sound initial direction for '{active_question.title if active_question else 'this problem'}'. "
                "Before you begin typing in the code editor, walk me through the key invariants of your loop or query, and its asymptotic Big-O runtime."
            )

        if stage == InterviewStage.ML_SYSTEM_DESIGN:
            if any(w in u_lower for w in ["feature store", "feast", "redis"]):
                return (
                    "A dual-tier feature store with Redis for online inference and Parquet for training works well. "
                    f"At {self.target_company}'s scale, how do you handle feature freshness when network latency causes out-of-order writes?"
                )
            return (
                f"Understood. When designing this architecture for {self.target_company}, what are your p99 latency budgets per microservice, "
                "and where are the potential single points of failure under peak traffic?"
            )

        # Default Stage & Wrap-up
        if stage == InterviewStage.WRAP_UP:
            return (
                f"At {self.target_company}, we value strong engineering ownership and empirical statistical rigor. "
                "It was a pleasure working through these technical problems with you today. "
                "Do you have any questions for me about our architecture, team dynamics, or technology stack?"
            )

        return (
            f"Understood. Looking at how this applies to {self.target_role} at {self.target_company}, "
            "walk me through your next technical step."
        )

    def generate_code_feedback(
        self,
        code: str,
        language: str,
        stdout: str,
        error: str | None = None,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Provide intelligent, constructive spoken feedback on code execution."""
        if error:
            err_msg = error.strip()
            if "Traceback" in err_msg:
                lines = err_msg.split("\n")
                last_line = lines[-1] if lines else err_msg
                return (
                    f"I see an unhandled exception during execution: '{last_line[:120]}'. "
                    "Take a close look at your variable bindings, array bounds, or empty collection cases. "
                    "How would you refactor your code to handle that edge case?"
                )
            return (
                f"There is a syntax or query execution error: '{err_msg[:120]}'. "
                "Check your table aliases, commas, and column references. What do you think caused this?"
            )

        if stdout and ("PASS" in stdout.upper() or "PASSED" in stdout.upper()):
            return (
                "All test assertions passed successfully! Now, walk me through the asymptotic Big-O runtime and "
                "space complexity of your solution, and explain how this implementation scales to 50 million records."
            )

        if language == "sql" and "rows returned" in stdout.lower():
            return (
                f"Your query executed cleanly ({stdout}). Take a look at the resulting table in your console. "
                "Do the cohort percentages and column outputs match what you expected? Walk me through your query logic."
            )

        return (
            "Code execution completed. Walk me through the mechanics of your solution, "
            "and what edge cases you've accounted for in this implementation."
        )
