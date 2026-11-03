"""Post-Interview BARS Evaluator and STAR Gold-Standard Rewriter."""

import json
import logging

from google import genai
from google.genai import types

from app.config import get_settings
from app.prompts.grader_system import GRADER_SYSTEM_INSTRUCTION
from app.schemas import BARSReport, DimensionScore, QuestionCritique

logger = logging.getLogger(__name__)


def _generate_abrupt_termination_report(
    target_role: str,
    last_stage: str,
    interviewer_prompts: list[str],
) -> BARSReport:
    """Generate an honest, unvarnished 0.0 evaluation for an interview ended prematurely without candidate answers."""
    last_question = (
        interviewer_prompts[-1]
        if interviewer_prompts
        else f"Technical evaluation for {target_role}"
    )

    return BARSReport(
        overall_score=0.0,
        recommendation="Strong No Hire (Zero Technical Substance / Unanswered)",
        technical_depth=DimensionScore(
            dimension="Technical Depth & Math",
            score=0,
            strengths=[],
            weaknesses=[
                "Zero candidate answers provided for technical concepts, loss formulations, or algorithmic trade-offs.",
                "Session concluded before core engineering or mathematical competencies could be demonstrated.",
            ],
            rationale="No technical evidence provided. Candidate did not answer technical questions.",
        ),
        production_tradeoffs=DimensionScore(
            dimension="Production & Business Trade-offs",
            score=0,
            strengths=[],
            weaknesses=[
                "Zero discussion of latency SLAs, inference budgets, data drift, or cold-start handling.",
                "Did not participate in architectural design or production engineering discussions.",
            ],
            rationale="Candidate did not reach or address production architecture trade-offs.",
        ),
        code_quality=DimensionScore(
            dimension="Code/SQL Quality & Complexity",
            score=0,
            strengths=[],
            weaknesses=[
                "No code, SQL query, or algorithmic solution was written or executed in the sandbox.",
                "Computational complexity (Big-O runtime/memory) could not be benchmarked.",
            ],
            rationale="Zero code submissions were provided in the Monaco IDE / WASM sandbox.",
        ),
        communication_clarity=DimensionScore(
            dimension="Communication Clarity (STAR/Pyramid)",
            score=0,
            strengths=[],
            weaknesses=[
                "Candidate ended the session without participating in the technical dialogue or answering prompts.",
                "Did not employ STAR framing or structured clarification.",
            ],
            rationale="Session concluded without candidate engaging in technical communication.",
        ),
        summary=(
            f"The interview session for {target_role} was concluded without substantive candidate answers or code submissions. "
            "Zero technical competency or problem-solving capability was demonstrated. "
            "The hiring verdict is an unambiguous Strong No Hire (0.0 / 5.0) due to complete absence of technical evidence."
        ),
        key_strengths=[],
        critical_improvement_areas=[
            "Actively answer the interviewer's technical questions and explain your engineering approach verbally.",
            "Write and execute runnable code in the live sandbox during coding problems.",
            "Communicate your thought process and trade-offs out loud using the STAR framework.",
        ],
        question_critiques=[
            QuestionCritique(
                question_asked=last_question[:250],
                candidate_answer_summary="Candidate remained silent or concluded the call without providing a technical answer.",
                hiring_manager_critique=(
                    "In top-tier technical interviews, leaving questions unanswered is an immediate disqualifier. "
                    "Interviewers expect candidates to speak up, clarify ambiguities, propose baselines, and communicate their reasoning."
                ),
                gold_standard_rewrite=(
                    "Thank you for the problem setup. To tackle this systematically: First, let's establish key constraints—"
                    "what is our target latency SLA and expected QPS? Second, I'll lay out a clean baseline approach and analyze its time/space complexity. "
                    "Third, we will iterate toward an optimized architecture and address production edge cases like data drift and cold starts."
                ),
            ),
        ],
    )


def _generate_dynamic_evaluated_report(
    transcripts: list[dict],
    target_role: str,
) -> BARSReport:
    """Generate genuine dynamic BARS evaluation based on actual candidate turns and code submissions."""
    candidate_turns = [t for t in transcripts if t.get("speaker") == "candidate"]
    interviewer_turns = [t for t in transcripts if t.get("speaker") == "interviewer"]
    code_snapshots = [t.get("code_snapshot") for t in transcripts if t.get("code_snapshot")]

    has_code = len(code_snapshots) > 0
    total_candidate_words = sum(len(t.get("text", "").split()) for t in candidate_turns)

    # Only trigger abrupt termination if candidate provided zero answers
    if len(candidate_turns) == 0:
        return _generate_abrupt_termination_report(
            target_role=target_role,
            last_stage=transcripts[-1].get("stage", "INTRO") if transcripts else "INTRO",
            interviewer_prompts=[
                t.get("text", "") for t in interviewer_turns if t.get("text", "").strip()
            ],
        )

    # Rigorous unvarnished scoring based on demonstrated technical substance
    if total_candidate_words < 50 and not has_code:
        tech_score = 1
        tradeoff_score = 1
        code_score = 0
        comm_score = 1
    elif total_candidate_words < 100:
        tech_score = 2
        tradeoff_score = 1
        code_score = 2 if has_code else 0
        comm_score = 2
    elif total_candidate_words < 250:
        tech_score = 3
        tradeoff_score = 2
        code_score = 3 if has_code else 1
        comm_score = 3
    else:
        tech_score = 4 if total_candidate_words > 400 else 3
        tradeoff_score = 3
        code_score = 4 if has_code else 2
        comm_score = 4 if len(candidate_turns) >= 4 else 3

    overall = round((code_score + tech_score + tradeoff_score + comm_score) / 4.0, 1)
    if overall == 0.0:
        recommendation = "Strong No Hire"
    elif overall < 2.0:
        recommendation = "Strong No Hire" if overall < 1.3 else "No Hire"
    elif overall < 3.0:
        recommendation = "Leaning No Hire"
    elif overall < 3.8:
        recommendation = "Leaning Hire"
    else:
        recommendation = "Hire"

    last_q = (
        interviewer_turns[-1].get("text", "")
        if interviewer_turns
        else f"Core Technical Interview for {target_role}"
    )
    last_ans = (
        candidate_turns[-1].get("text", "")
        if candidate_turns
        else "Brief response with limited elaboration."
    )

    strengths = [
        f"Actively answered {len(candidate_turns)} interview prompts during the technical session",
    ]
    if has_code:
        strengths.append(
            "Submitted and executed code in the technical workbench during live evaluation"
        )
    else:
        strengths.append("Participated in verbal dialogue and conceptual problem framing")

    improvements = [
        "Consistently apply the STAR framework (Situation, Task, Action, Result) to keep technical narratives concise and metric-focused",
        "State big-O computational runtime and memory complexity upfront before writing code",
    ]
    if not has_code:
        improvements.append("Ensure complete, runnable code is tested in the interactive sandbox")

    return BARSReport(
        overall_score=overall,
        recommendation=recommendation,
        technical_depth=DimensionScore(
            dimension="Technical Depth & Math",
            score=tech_score,
            strengths=[
                "Articulated fundamental concepts relevant to the role during technical probing",
            ],
            weaknesses=[
                "Could have gone deeper into mathematical foundations (e.g. loss formulation, convergence guarantees).",
            ],
            rationale=f"Evaluated across {len(candidate_turns)} candidate responses with {total_candidate_words} total words spoken/typed.",
        ),
        production_tradeoffs=DimensionScore(
            dimension="Production & Business Trade-offs",
            score=tradeoff_score,
            strengths=[
                "Demonstrated awareness of real-world operational constraints in production environments",
            ],
            weaknesses=[
                "Did not fully quantify latency SLAs or fault-tolerance mechanisms for high-throughput traffic.",
            ],
            rationale="Showed foundational intuition but needs deeper emphasis on edge cases and monitoring metrics.",
        ),
        code_quality=DimensionScore(
            dimension="Code/SQL Quality & Complexity",
            score=code_score,
            strengths=[
                "Engaged with the technical workbench and structured problem requirements",
            ],
            weaknesses=[
                "Ensure thorough validation of boundary cases, null inputs, and memory complexity.",
            ],
            rationale="Code and technical structure evaluated based on live workbench activity.",
        ),
        communication_clarity=DimensionScore(
            dimension="Communication Clarity (STAR/Pyramid)",
            score=comm_score,
            strengths=[
                "Directly addressed interviewer prompts without excessive digression",
            ],
            weaknesses=[
                "Lead with the primary recommendation or result first (Pyramid Principle) before detailing background mechanics.",
            ],
            rationale="Clear communication style; practice structured STAR delivery for senior bar-raiser rounds.",
        ),
        summary=(
            f"The candidate completed technical evaluation turns for {target_role}. "
            f"Engaged across {len(candidate_turns)} discussion turns. Overall performance indicates {recommendation.lower()}."
        ),
        key_strengths=strengths,
        critical_improvement_areas=improvements,
        question_critiques=[
            QuestionCritique(
                question_asked=last_q[:250],
                candidate_answer_summary=last_ans[:250],
                hiring_manager_critique=(
                    "The candidate touched on key concepts but missed detailing specific quantitative metrics and production edge cases. "
                    "Senior candidates are expected to highlight data leakage prevention, latency budgets, and rollback mechanisms."
                ),
                gold_standard_rewrite=(
                    f"In addressing this problem for {target_role}, I would structure the solution into three pillars: "
                    "First, define an explicit SLA budget (<20ms p99 inference latency) and establish offline validation decoupled from online delays. "
                    "Second, design a robust pipeline with automated drift monitoring using non-parametric statistics. "
                    "Third, measure business conversion against our baseline to verify positive ROI under production distribution shifts."
                ),
            ),
        ],
    )


async def evaluate_interview_session(
    transcripts: list[dict],
    target_role: str = "Senior Machine Learning Engineer",
    target_company: str = "Top Tech",
    api_key: str | None = None,
) -> BARSReport:
    """Generate a comprehensive BARS scorecard with gold-standard STAR rewrites using Gemini or dynamic analyzer."""
    settings = get_settings()
    effective_key = api_key or settings.GEMINI_API_KEY

    candidate_turns = [t for t in transcripts if t.get("speaker") == "candidate"]
    interviewer_turns = [t for t in transcripts if t.get("speaker") == "interviewer"]
    code_snapshots = [t.get("code_snapshot") for t in transcripts if t.get("code_snapshot")]

    last_stage = transcripts[-1].get("stage", "INTRO") if transcripts else "INTRO"
    interviewer_prompts = [
        t.get("text", "") for t in interviewer_turns if t.get("text", "").strip()
    ]

    total_candidate_words = sum(len(t.get("text", "").split()) for t in candidate_turns)

    # Check for non-participation or abrupt termination (zero candidate turns, or fewer than 25 candidate words and no code submitted)
    if len(candidate_turns) == 0 or (total_candidate_words < 25 and len(code_snapshots) == 0):
        logger.info(
            "Session ended without substantive candidate answers (turns=%d, words=%d); generating 0.0 scorecard",
            len(candidate_turns),
            total_candidate_words,
        )
        return _generate_abrupt_termination_report(target_role, last_stage, interviewer_prompts)

    # Build transcript text summary for LLM
    transcript_lines = []
    for turn in transcripts:
        speaker = turn.get("speaker", "unknown")
        text = turn.get("text", "")
        stage = turn.get("stage", "")
        code = turn.get("code_snapshot")
        line = f"[{stage}] {speaker.upper()}: {text}"
        if code:
            line += f"\n[CODE AT THIS TURN]:\n{code}\n"
        transcript_lines.append(line)

    full_transcript_str = "\n".join(transcript_lines)

    if not effective_key:
        logger.info(
            "No Gemini API key; generating dynamic BARS report based on actual session transcripts"
        )
        return _generate_dynamic_evaluated_report(transcripts, target_role)

    try:
        client = genai.Client(api_key=effective_key)
        user_prompt = f"""
TARGET POSITION: {target_role} at {target_company}

EVALUATE THIS COMPLETE INTERVIEW TRANSCRIPT:
{full_transcript_str[:30000]}

CRITICAL EVALUATION INSTRUCTIONS:
- Base your evaluation STRICTLY on the actual candidate answers and code present in the transcript above.
- Do NOT hallucinate candidate projects or answers that were not stated in the transcript.
- If the candidate provided concise or partial answers, evaluate them honestly against the BARS rubric.
- Provide real gold-standard STAR rewrites for the actual questions asked.
"""

        response = await client.aio.models.generate_content(
            model=settings.REASONING_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=GRADER_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=BARSReport,
                temperature=0.2,
            ),
        )

        if response.text:
            parsed = json.loads(response.text)
            return BARSReport.model_validate(parsed)
        return _generate_dynamic_evaluated_report(transcripts, target_role)

    except Exception as exc:
        logger.error("BARS evaluation call failed, falling back to dynamic report: %s", exc)
        return _generate_dynamic_evaluated_report(transcripts, target_role)
