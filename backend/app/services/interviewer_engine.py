"""Intelligent Interviewer Conversational Engine.

Provides human-like, context-aware dialogue, question explanations,
clarifications, hints, and code feedback for the technical interviewer.
Supports Gemini Flash LLM generation when an API key is available,
and a rich, deterministic intent-based engine when offline.
"""

import logging
import re

from google import genai
from google.genai import types

from app.config import get_settings
from app.prompts.interviewer_system import build_interviewer_session_prompt
from app.schemas import CandidateClaimGraph, InterviewMode, InterviewStage, QuestionItem

logger = logging.getLogger(__name__)


def explain_question_in_detail(question: QuestionItem) -> str:
    """Generate a comprehensive, human spoken walkthrough of a technical question."""
    explanation_parts = [
        f"Let me explain '{question.title}' in detail.",
    ]

    if question.verbal_introduction:
        explanation_parts.append(question.verbal_introduction)
    else:
        explanation_parts.append(question.prompt)

    if question.category.value == "SQL":
        explanation_parts.append(
            "In your workbench, the DuckDB environment is pre-seeded with the necessary analytics tables. "
            "You can query them directly. We are looking for clean SQL syntax, correct window frame definitions, "
            "and avoidance of quadratic joins."
        )
    elif question.category.value == "PYTHON":
        explanation_parts.append(
            "The Monaco IDE has a Pyodide WebAssembly Python runner pre-loaded with NumPy. "
            "Focus on an optimal algorithmic implementation with clean Big-O runtime and proper handling of edge cases."
        )
    elif question.category.value == "ML_SYSTEM_DESIGN":
        explanation_parts.append(
            "You have the Excalidraw design canvas on the right to sketch out data pipelines, "
            "feature stores, model serving layers, and monitoring feedback loops. "
            "I encourage you to start with candidate generation and ranking funnels, and quantify your latency budgets."
        )

    explanation_parts.append(
        "Before you start typing or drawing, walk me through your initial high-level approach."
    )
    return " ".join(explanation_parts)


def answer_clarification_question(question: QuestionItem | None, query: str) -> str:
    """Match candidate clarification queries against question criteria or realistic engineering constraints."""
    q_lower = query.lower()

    if not question:
        return (
            "In this stage, assume standard production scale: 50,000 QPS, "
            "p99 latency SLA under 25ms, and high availability. What specific aspect would you like to clarify?"
        )

    # Check question-specific clarifications dictionary
    if question.clarifications:
        for key, val in question.clarifications.items():
            if key.lower() in q_lower:
                return f"Good clarifying question. {val} How does that influence your design?"

    # Generic schema query
    if any(k in q_lower for k in ["schema", "columns", "table", "data type"]):
        if question.category.value == "SQL" and question.seed_sql:
            tables_found = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", question.seed_sql)
            return (
                f"The database contains the following tables: {', '.join(tables_found)}. "
                "You can see the exact column definitions and sample data in the reference schema panel above the editor."
            )
        return "The input data types and function signatures are specified in the starter code. Does that answer what you needed?"

    # Null / Missing values
    if any(k in q_lower for k in ["null", "missing", "nan", "empty"]):
        return (
            "You should assume real-world production data where missing or null values can exist. "
            "Your solution should handle them gracefully without throwing unhandled exceptions."
        )

    # Duplicates
    if any(k in q_lower for k in ["duplicate", "dedup", "tied"]):
        return (
            "Yes, duplicate records or tied values can occur in the dataset. "
            "Make sure your logic accounts for them properly (for instance, using DISTINCT or average ranks)."
        )

    # Scale / Constraints
    if any(k in q_lower for k in ["scale", "rows", "volume", "qps", "traffic"]):
        return (
            "Assume around 50 million active entities and hundreds of millions of events. "
            "Memory efficiency and vectorized execution are critical. An O(N^2) cartesian join would time out in production."
        )

    # Big-O complexity
    if any(k in q_lower for k in ["complexity", "big-o", "runtime", "time complexity"]):
        return (
            "For this problem, we are aiming for optimal asymptotic efficiency. "
            "Ideally O(N) or O(N log N) time complexity with linear or sub-linear auxiliary space."
        )

    return (
        f"Regarding {query.strip()}: in production, you should design for fault tolerance, "
        "deterministic outputs, and minimal memory overhead. How do you plan to handle that in your code?"
    )


def provide_hint(question: QuestionItem | None, hints_given: list[str]) -> str:
    """Provide a progressive hint for the active question."""
    if not question:
        return (
            "Think about decomposing the problem: first define your core baseline logic, "
            "then identify the mathematical invariants or window framing needed to scale it."
        )

    if question.hints:
        for hint in question.hints:
            if hint not in hints_given:
                hints_given.append(hint)
                return f"Here is a targeted hint: {hint} How would you incorporate that?"

    if question.category.value == "SQL":
        return (
            "Consider breaking down the query using a Common Table Expression (WITH clause). "
            "Identify the timestamp truncation first, then apply window functions like ROW_NUMBER or conditional SUM/COUNT."
        )
    elif question.category.value == "PYTHON":
        return (
            "Think about mathematical transformations or sorting. "
            "Often, sorting in O(N log N) allows you to resolve the problem in a single linear pass or binary search."
        )
    else:
        return (
            "Structure your architecture into clear decoupling layers: an offline asynchronous training/feature pipeline, "
            "an online low-latency key-value cache (Redis/Feast), and a lightweight scoring model runtime."
        )


class InterviewerEngine:
    """Manages conversational dialogue generation for the interview session."""

    def __init__(
        self,
        session_id: str,
        target_role: str = "Senior Machine Learning Engineer",
        target_company: str = "Top Tech",
        company_archetype: str = "FAANG_GLOBAL",
        interview_mode: InterviewMode = InterviewMode.FULL_LOOP,
        claim_graph: CandidateClaimGraph | None = None,
        api_key: str | None = None,
    ):
        self.session_id = session_id
        self.target_role = target_role
        self.target_company = target_company
        self.company_archetype = company_archetype
        self.interview_mode = interview_mode
        self.claim_graph = claim_graph
        self.api_key = api_key or get_settings().GEMINI_API_KEY
        self.settings = get_settings()
        self.hints_given: list[str] = []
        self.stage_turn_counts: dict[str, int] = {}

    def generate_stage_greeting(
        self,
        stage: InterviewStage,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Generate a natural, spoken introduction for each stage."""
        if stage == InterviewStage.INTRO:
            if self.company_archetype == "INDIAN_PRODUCT":
                return (
                    f"Hello and welcome! I'm Dr. Elena Vance, Principal Bar-Raiser here at {self.target_company}. "
                    f"My team focuses on solving high-throughput, low-latency ML challenges at Indian market scale. "
                    "Today's session is an open, collaborative technical dialogue rather than a formal test. "
                    "To kick things off, please walk me through your engineering journey, your key ML specializations, "
                    "and a production system you've delivered."
                )
            elif self.company_archetype == "AI_STARTUP":
                return (
                    f"Hi there! I'm Alex Chen, Staff Architect at {self.target_company}. "
                    "We move fast and focus on shipping pragmatic, high-impact AI systems and low-latency inference. "
                    "Feel free to think out loud and challenge assumptions throughout our discussion today. "
                    "To start, tell me a bit about yourself and the most interesting technical challenge you've tackled recently."
                )
            return (
                f"Hello, welcome! I'm Dr. Elena Vance, Principal Bar-Raiser at {self.target_company}. "
                f"I'm pleased to meet you today for our technical interview for the {self.target_role} position. "
                "Today will be a collaborative deep-dive into real-world machine learning engineering. "
                "Let's begin with a concise 60-second overview: walk me through your engineering background, "
                "core technical specializations, and production ML systems you've delivered."
            )

        elif stage == InterviewStage.RESUME_DEEP_DIVE:
            if self.claim_graph and self.claim_graph.projects:
                proj = self.claim_graph.projects[0]
                probe = (
                    proj.probing_questions[0]
                    if proj.probing_questions
                    else "What was your biggest deployment bottleneck?"
                )
                return (
                    f"Thank you for that background summary. Now let's dive into your hands-on production engineering. "
                    f"Looking at your work on '{proj.project_name}', {probe} "
                    "Walk me through your architectural decisions and the trade-offs involved."
                )
            return (
                "Thank you for that overview. Now let's transition to our Resume Deep-Dive. "
                "I'd like to explore the most complex machine learning system or distributed data pipeline "
                "you've built in production. Walk me through the system architecture, baseline models, "
                "and how you measured offline versus online metric alignment."
            )

        elif stage == InterviewStage.ML_BREADTH:
            return (
                "Now we'll transition to our ML Breadth evaluation. "
                "In this round, we'll move rapidly across core foundational machine learning concepts: "
                "bias-variance trade-offs, loss formulations, regularization, feature engineering, and evaluation metrics. "
                "Let's jump straight in: how do you systematically choose between L1 and L2 regularization for high-dimensional sparse features?"
            )

        elif stage == InterviewStage.ML_DEPTH:
            return (
                "Now we'll transition to our ML Depth round. "
                "Here we'll go deep into the mathematical mechanics, derivations, and internal architectural trade-offs. "
                "Let's start with loss optimization: walk me through the analytical gradient derivation for binary cross-entropy with a sigmoid activation, "
                "and explain why saturated sigmoids lead to vanishing gradients."
            )

        elif stage == InterviewStage.GENERATIVE_AI:
            return (
                "Now we'll move into our Generative AI and LLM Systems round. "
                "We'll explore modern LLM architectures, fine-tuning methodologies, RAG retrieval pipelines, and low-latency inference serving. "
                "To begin: when building an enterprise RAG system with high-precision compliance requirements, "
                "how do you architect your chunking, hybrid retrieval, and re-ranking pipeline to minimize hallucinations?"
            )

        elif stage == InterviewStage.LIVE_CODING_SQL_PYTHON:
            if active_question:
                intro = (
                    f"Now we'll move into our live technical coding evaluation. "
                    f"The problem set up in your workbench is '{active_question.title}'. "
                )
                if active_question.verbal_introduction:
                    intro += active_question.verbal_introduction + " "
                else:
                    intro += active_question.prompt + " "
                intro += (
                    "Please review the technical workbench on the right. "
                    "Before writing code, talk me through your thought process and initial approach."
                )
                return intro
            return (
                "Now let's move into our live technical coding round. "
                "Please review the active problem in your workbench, and walk me through your initial algorithm before typing."
            )

        elif stage == InterviewStage.ML_SYSTEM_DESIGN:
            if active_question:
                intro = (
                    f"Great. Now we'll transition to our ML System Design challenge. "
                    f"Our scenario today is '{active_question.title}'. "
                )
                if active_question.verbal_introduction:
                    intro += active_question.verbal_introduction + " "
                else:
                    intro += active_question.prompt + " "
                intro += (
                    "You have the Excalidraw design canvas ready on the right to sketch out system components. "
                    "How would you structure this system, starting from high-level data ingestion and candidate generation?"
                )
                return intro
            return (
                "Now let's transition to our ML System Design section. "
                "You have an interactive design whiteboard available on the right. "
                "Walk me through your high-level architecture and how you plan to handle latency and throughput requirements."
            )

        elif stage == InterviewStage.WRAP_UP:
            return (
                f"That concludes the technical evaluation segments of our interview today. "
                f"You covered substantial technical ground across our discussion for the {self.target_role} role. "
                f"In the time we have remaining, I'd like to open the floor to you: "
                f"what questions do you have for me about engineering at {self.target_company}, our team, or tech stack?"
            )

        return "Understood. Let's continue with our technical discussion."

    def handle_silence(
        self,
        seconds_silent: int = 18,
        stage: InterviewStage = InterviewStage.INTRO,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Provide a gentle, empathetic prompt when candidate is pausing or silent."""
        if seconds_silent <= 25:
            return (
                "Take your time to think through the design. "
                "Feel free to think out loud as you reason through it, or let me know if you want to clarify any assumptions first."
            )
        elif seconds_silent <= 50:
            return (
                "Whenever you're ready, let me know what direction you're leaning toward. "
                "We can also discuss the trade-offs together if that helps."
            )
        return "I'm here whenever you're ready to proceed. Would you like a targeted hint to help kick off your solution?"

    async def generate_turn_response(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate an intelligent, human-feeling interviewer response."""
        u_clean = user_text.strip()
        u_lower = u_clean.lower()
        stage_key = stage.value
        turn_count = self.stage_turn_counts.get(stage_key, 0) + 1
        self.stage_turn_counts[stage_key] = turn_count

        # 1. Detect candidate request to explain the question
        if active_question and any(
            phrase in u_lower
            for phrase in [
                "explain the question",
                "explain question",
                "can you explain",
                "what is the problem",
                "what should i do",
                "what am i supposed to do",
                "walk me through the problem",
                "don't understand",
                "dont understand",
                "clarify the problem",
                "tell me about the problem",
                "repeat the prompt",
                "explain problem",
            ]
        ):
            return explain_question_in_detail(active_question)

        # 2. Detect candidate request for a hint
        if any(
            phrase in u_lower
            for phrase in [
                "give me a hint",
                "can i get a hint",
                "need a hint",
                "give me a clue",
                "i am stuck",
                "i'm stuck",
                "not sure how to start",
                "stuck on this",
                "confused on how",
            ]
        ):
            return provide_hint(active_question, self.hints_given)

        # 3. Detect candidate questions asking for clarification on schemas or constraints
        if any(
            w in u_lower
            for w in [
                "can we assume",
                "is it possible",
                "what are the columns",
                "what is the schema",
                "are there duplicates",
                "can amounts be",
                "can values be",
                "what format",
                "how many rows",
                "what is the latency",
                "null values",
                "missing values",
            ]
        ):
            return answer_clarification_question(active_question, u_clean)

        # 4. If Gemini API key is available, generate dynamic LLM response
        if self.api_key and self.settings.ENVIRONMENT != "test":
            try:
                llm_response = await self._generate_gemini_turn(
                    user_text=u_clean,
                    stage=stage,
                    active_question=active_question,
                    conversation_history=conversation_history or [],
                )
                if llm_response and len(llm_response.strip()) > 10:
                    return llm_response.strip()
            except Exception as exc:
                logger.warning(
                    "Gemini conversational generation failed: %s; using smart local engine", exc
                )

        # 5. Smart Local Intent-Driven Dialogue Engine (Offline Fallback)
        return self._generate_local_dialogue_turn(
            user_text=u_clean,
            stage=stage,
            active_question=active_question,
            turn_count=turn_count,
        )

    async def _generate_gemini_turn(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None,
        conversation_history: list[dict[str, str]],
    ) -> str:
        """Call Gemini model to generate natural, conversational interviewer response."""
        client = genai.Client(api_key=self.api_key)

        claims_summary = (
            self.claim_graph.model_dump_json() if self.claim_graph else "Senior Engineer Profile"
        )
        q_context = ""
        if active_question:
            q_context = (
                f"ACTIVE PROBLEM TITLE: {active_question.title}\n"
                f"CATEGORY: {active_question.category.value}\n"
                f"PROBLEM STATEMENT: {active_question.prompt}\n"
                f"RUBRIC FOCUS: {', '.join(active_question.rubric_criteria)}\n"
            )

        system_instruction = (
            f"{build_interviewer_session_prompt(self.target_role, self.target_company, claims_summary, stage.value, q_context)}\n\n"
            "CRITICAL CONVERSATIONAL GUIDELINES:\n"
            "- Speak naturally as a senior bar-raiser interviewer at a top product tech company.\n"
            "- Keep your response concise (2 to 4 sentences maximum) and suitable for speech synthesis.\n"
            "- Acknowledge the candidate's exact technical point directly before probing deeper.\n"
            "- If the candidate asks you to explain the problem or clarify constraints, explain clearly and warmly.\n"
            "- Do not use empty sycophantic praise ('Great answer!'). Stay calm, professional, and intellectually rigorous.\n"
        )

        # Build message turns
        recent_turns = conversation_history[-8:] if conversation_history else []
        history_str = ""
        for t in recent_turns:
            spk = t.get("speaker", "interviewer").capitalize()
            txt = t.get("text", "")
            history_str += f"{spk}: {txt}\n"

        prompt = f"{history_str}Candidate: {user_text}\nInterviewer (provide next spoken response):"

        response = await client.aio.models.generate_content(
            model=self.settings.EXTRACTOR_MODEL,  # Fast flash model
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                max_output_tokens=300,
            ),
        )

        return response.text or ""

    def _generate_local_dialogue_turn(
        self,
        user_text: str,
        stage: InterviewStage,
        active_question: QuestionItem | None,
        turn_count: int,
    ) -> str:
        """Smart deterministic local dialogue manager providing rich responses."""
        u_lower = user_text.lower()

        if stage == InterviewStage.INTRO:
            if turn_count == 1:
                if self.claim_graph and self.claim_graph.projects:
                    top_proj = self.claim_graph.projects[0]
                    return (
                        f"That is a clear overview. I noticed your experience with {', '.join(self.claim_graph.core_specializations[:2])}, "
                        f"particularly '{top_proj.project_name}'. "
                        "Before we move to coding, what was the primary architectural trade-off you had to make in that system?"
                    )
                return (
                    f"Thank you for that summary. With your focus on production machine learning for {self.target_role}, "
                    "what is the most challenging offline-to-online metric divergence you have had to debug in practice?"
                )
            else:
                return (
                    "Understood. Let's transition directly into our technical challenges. "
                    "Please take a look at the technical workbench on the right and let's begin the coding evaluation."
                )

        elif stage == InterviewStage.RESUME_DEEP_DIVE:
            if self.claim_graph and self.claim_graph.projects:
                proj_idx = min(turn_count - 1, len(self.claim_graph.projects) - 1)
                proj = self.claim_graph.projects[proj_idx]
                probe_idx = min(turn_count % 3, len(proj.probing_questions) - 1)
                probe = proj.probing_questions[probe_idx]
                return f"Understood. Probing deeper into '{proj.project_name}': {probe}"
            else:
                probes = [
                    "How did your online feature store guarantee point-in-time correctness without lookahead leakage?",
                    "What was your fallback strategy when the vector retrieval service experienced tail latency spikes above 20ms?",
                    "How did your pipeline handle delayed ground-truth labels that take 60 days to settle?",
                ]
                return probes[(turn_count - 1) % len(probes)]

        elif stage == InterviewStage.LIVE_CODING_SQL_PYTHON:
            # Check for candidate discussing specific approaches
            if any(
                w in u_lower
                for w in ["window", "partition", "row_number", "dense_rank", "date_trunc"]
            ):
                return (
                    "Using window functions and date truncation is a strong approach here. "
                    "Make sure to frame your window boundary correctly so you don't inadvertently include future transactions. "
                    "How do you plan to handle users who have zero activity in subsequent months?"
                )
            if any(w in u_lower for w in ["join", "left join", "self join", "cartesian"]):
                return (
                    "A join can work, but keep computational scaling in mind: on 100 million transactions, a cartesian self-join can explode. "
                    "Can you accomplish this with a single scan using conditional aggregation or window partitioning?"
                )
            if any(w in u_lower for w in ["hash", "dict", "map", "set"]):
                return (
                    "Using a hash map gives O(1) expected lookup time. "
                    "How do you plan to manage memory overhead if the cardinality of distinct keys reaches tens of millions?"
                )
            if any(w in u_lower for w in ["sort", "n log n", "binary search", "bisect"]):
                return (
                    "O(N log N) sorting is well within our performance budget. "
                    "How will you handle duplicate elements or tied prediction scores?"
                )
            if any(w in u_lower for w in ["vectorize", "numpy", "broadcasting", "einsum"]):
                return (
                    "Vectorized operations in NumPy eliminate Python interpreter overhead. "
                    "Be careful with memory allocation for large intermediate broadcast arrays. Walk me through the array dimensions."
                )

            # Default conversational probing for coding
            coding_probes = [
                "That makes sense conceptually. How do you plan to structure the base query or helper function first?",
                "Good framing. What are the key boundary conditions (e.g. empty inputs, duplicate keys, null values) and how does your approach achieve optimal Big-O complexity?",
                "Walk me through your code line-by-line as you write it. What invariants does your loop or CTE maintain?",
                "Now that you have the basic structure, run your code in the sandbox to verify the output against the expected format.",
            ]
            return coding_probes[(turn_count - 1) % len(coding_probes)]

        elif stage == InterviewStage.ML_SYSTEM_DESIGN:
            if any(w in u_lower for w in ["feature store", "feast", "redis", "dynamo"]):
                return (
                    "A dual-tier feature store with Redis for online inference and Parquet/S3 for offline training is standard. "
                    "How do you ensure zero training-serving feature skew when real-time features arrive with network jitter?"
                )
            if any(
                w in u_lower
                for w in ["two-tower", "two tower", "ann", "hnsw", "embedding", "vector"]
            ):
                return (
                    "Two-tower neural retrieval with HNSW indexing handles high candidate volume well. "
                    "What is your re-indexing cadence for newly published items that have no historical interaction data?"
                )
            if any(w in u_lower for w in ["cache", "caching", "semantic cache"]):
                return (
                    "Semantic caching reduces LLM latency and cost significantly. "
                    "What similarity threshold do you use to balance cache hits with context precision, and how do you invalidate stale entries?"
                )
            if any(w in u_lower for w in ["drift", "evidently", "ks-test", "monitoring"]):
                return (
                    "Drift detection using population stability index (PSI) or Kolmogorov-Smirnov tests is critical. "
                    "When drift is detected, do you trigger automated online fine-tuning, or do you fall back to a conservative heuristics model?"
                )

            design_probes = [
                "Understood. How would your architecture handle downstream feature store degradation if p99 latency spikes during peak 50,000 QPS load?",
                "Walk me through your serving SLA: from the client request entering API Gateway to returning the top-K ranking, what is your latency budget per microservice?",
                "How do you address the cold-start problem for users or items with zero historical interaction signals?",
                "Let's discuss online experimentation: how would you set up your A/B test routing and prevent metric cannibalization across candidate pools?",
            ]
            return design_probes[(turn_count - 1) % len(design_probes)]

        elif stage == InterviewStage.WRAP_UP:
            if any(w in u_lower for w in ["culture", "team", "day to day", "collaboration"]):
                return (
                    f"At {self.target_company}, our engineering culture emphasizes extreme technical ownership. "
                    "Applied Scientists and ML Engineers own the full lifecycle: from exploratory data analysis and mathematical modeling, "
                    "to optimizing CUDA kernels, writing clean streaming pipelines, and deploying canary A/B tests in production."
                )
            if any(w in u_lower for w in ["tech stack", "framework", "models", "infrastructure"]):
                return (
                    "We run distributed training across modern GPU clusters using PyTorch and vLLM / TensorRT-LLM for serving. "
                    "Our real-time feature pipelines leverage Apache Flink and online Redis caches, with Kubernetes orchestration. "
                    "We emphasize low-latency inference and rigorous statistical offline evaluation."
                )
            return (
                "We tackle very high-throughput, low-latency machine learning problems where even a 0.5% offline metric gain "
                "translates to significant business impact. It was a pleasure discussing these problems with you today. "
                "The recruiting team will follow up with you on the next steps."
            )

        return "Understood. Walk me through the next step in your technical reasoning."

    def generate_code_feedback(
        self,
        code: str,
        language: str,
        stdout: str,
        error: str | None = None,
        active_question: QuestionItem | None = None,
    ) -> str:
        """Generate constructive feedback when the candidate executes code or queries."""
        if error:
            err_msg = error.strip()
            # Extract main error message
            if "Traceback" in err_msg:
                lines = err_msg.split("\n")
                last_line = lines[-1] if lines else err_msg
                return (
                    f"I see an exception during execution: '{last_line[:120]}'. "
                    "Take a close look at your variable bindings and boundary conditions. "
                    "How would you adjust your logic to prevent that?"
                )
            return (
                f"I noticed a runtime error during query execution: '{err_msg[:120]}'. "
                "Check your table aliases, column names, and syntax. Let me know what you think went wrong."
            )

        if stdout and ("PASS" in stdout.upper() or "PASSED" in stdout.upper()):
            return (
                "The unit tests passed cleanly! Now, walk me through the asymptotic Big-O runtime and "
                "memory space complexity of your implementation, and explain how it scales to 100 million records."
            )

        if language == "sql" and "rows returned" in stdout.lower():
            return (
                f"Your query executed successfully ({stdout}). "
                "Look at the resulting rows in the console table. Do the cohort retention percentages align with expectations, "
                "and how does your query handle months with zero user transactions?"
            )

        return (
            "Code execution finished. Walk me through the mechanics of your solution, "
            "and what edge cases you've accounted for in this implementation."
        )
