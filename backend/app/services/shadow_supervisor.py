"""Slow-Loop Async Shadow Supervisor Service."""

import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config import get_settings
from app.prompts.supervisor_system import SUPERVISOR_SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)


class SupervisorAssessment(BaseModel):
    """Output from the background shadow evaluator."""

    has_technical_gap: bool = Field(
        ..., description="True if a technical gap, shallow claim, or suboptimal code was detected"
    )
    detected_gap_summary: str | None = Field(
        None, description="Summary of the technical weakness identified"
    )
    injected_directive: str | None = Field(
        None, description="Silent directive instructing the interviewer on the next probe"
    )


def _heuristic_shadow_check(
    transcript_text: str,
    code_snippet: str | None = None,
) -> SupervisorAssessment:
    """Fast local heuristic check used for tests or offline execution."""
    lower_transcript = transcript_text.lower()
    lower_code = (code_snippet or "").lower()

    # Check for O(N^2) or nested loop patterns in Python
    if "for " in lower_code and lower_code.count("for ") >= 2:
        return SupervisorAssessment(
            has_technical_gap=True,
            detected_gap_summary="Nested for-loop detected in solution with potential O(N^2) complexity.",
            injected_directive="Probe candidate on the computational time complexity of their nested loop and how to vectorize or hash-index it.",
        )

    # Check for missing window partition in SQL
    if "select" in lower_code and "over (" in lower_code and "partition by" not in lower_code:
        return SupervisorAssessment(
            has_technical_gap=True,
            detected_gap_summary="SQL window function lacks PARTITION BY clause.",
            injected_directive="Ask candidate whether their window aggregation needs to be scoped per entity using PARTITION BY.",
        )

    # Check for hand-waving words
    if any(
        phrase in lower_transcript
        for phrase in ["standard approach", "obviously", "just used a model", "high accuracy"]
    ):
        return SupervisorAssessment(
            has_technical_gap=True,
            detected_gap_summary="Candidate gave high-level or hand-waving statement without production calibration.",
            injected_directive="Press candidate on production edge cases: specifically how they measured p99 latency and handled drift.",
        )

    return SupervisorAssessment(
        has_technical_gap=False,
        detected_gap_summary=None,
        injected_directive=None,
    )


async def evaluate_turn_in_shadow(
    transcript_turn: str,
    code_snippet: str | None = None,
    api_key: str | None = None,
) -> SupervisorAssessment:
    """Asynchronously evaluate candidate response and formulate targeted probe directives."""
    settings = get_settings()
    effective_key = api_key or settings.GEMINI_API_KEY

    if not effective_key:
        return _heuristic_shadow_check(transcript_turn, code_snippet)

    try:
        client = genai.Client(api_key=effective_key)
        user_content = f"LATEST CANDIDATE TRANSCRIPT TURN:\n{transcript_turn}\n"
        if code_snippet:
            user_content += f"\nACTIVE CODE SNIPPET:\n{code_snippet}\n"

        response = await client.aio.models.generate_content(
            model=settings.REASONING_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SUPERVISOR_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=SupervisorAssessment,
                temperature=0.1,
            ),
        )

        if response.text:
            parsed = json.loads(response.text)
            return SupervisorAssessment.model_validate(parsed)
        return _heuristic_shadow_check(transcript_turn, code_snippet)

    except Exception as exc:
        logger.error("Shadow supervisor call failed, falling back to heuristic: %s", exc)
        return _heuristic_shadow_check(transcript_turn, code_snippet)
