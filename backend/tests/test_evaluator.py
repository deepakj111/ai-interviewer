"""Unit tests for shadow supervisor and rubric evaluator."""

import pytest

from app.services.rubric_evaluator import evaluate_interview_session
from app.services.shadow_supervisor import _heuristic_shadow_check, evaluate_turn_in_shadow


def test_heuristic_shadow_check_nested_loops():
    code_with_nested_loop = """
def find_pairs(arr):
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] + arr[j] == 0:
                return (i, j)
"""
    assessment = _heuristic_shadow_check("I wrote a nested loop.", code_with_nested_loop)
    assert assessment.has_technical_gap is True
    assert "O(N^2)" in (assessment.detected_gap_summary or "")
    assert assessment.injected_directive is not None


def test_heuristic_shadow_check_missing_partition():
    sql_code = "SELECT user_id, amount, AVG(amount) OVER (ORDER BY date) FROM txs;"
    assessment = _heuristic_shadow_check("Here is my rolling query.", sql_code)
    assert assessment.has_technical_gap is True
    assert "PARTITION BY" in (assessment.detected_gap_summary or "")


@pytest.mark.asyncio
async def test_shadow_supervisor_async():
    assessment = await evaluate_turn_in_shadow(
        transcript_turn="It was just a standard approach with high accuracy.",
        code_snippet=None,
        api_key=None,
    )
    assert assessment.has_technical_gap is True
    assert assessment.injected_directive is not None


@pytest.mark.asyncio
async def test_rubric_evaluator_report_structure():
    sample_transcripts = [
        {"speaker": "interviewer", "stage": "INTRO", "text": "Welcome to the interview."},
        {
            "speaker": "candidate",
            "stage": "INTRO",
            "text": "Thank you, excited to discuss my ML background.",
        },
        {
            "speaker": "interviewer",
            "stage": "RESUME_DEEP_DIVE",
            "text": "How did you monitor drift?",
        },
        {
            "speaker": "candidate",
            "stage": "RESUME_DEEP_DIVE",
            "text": "We tracked daily Wasserstein distance across embedding centroids.",
        },
    ]

    report = await evaluate_interview_session(
        transcripts=sample_transcripts,
        target_role="Senior ML Engineer",
        target_company="Stripe",
        api_key=None,
    )

    assert report is not None
    assert 1.0 <= report.overall_score <= 5.0
    assert report.technical_depth.score in [1, 2, 3, 4, 5]
    assert report.production_tradeoffs.score in [1, 2, 3, 4, 5]
    assert report.code_quality.score in [1, 2, 3, 4, 5]
    assert report.communication_clarity.score in [1, 2, 3, 4, 5]
    assert len(report.question_critiques) >= 1

    for critique in report.question_critiques:
        assert critique.question_asked
        assert critique.hiring_manager_critique
        assert critique.gold_standard_rewrite


@pytest.mark.asyncio
async def test_rubric_evaluator_abrupt_termination():
    # Only interviewer greeting, no candidate turns
    empty_candidate_transcripts = [
        {"speaker": "interviewer", "stage": "INTRO", "text": "Welcome to the interview."},
    ]

    report = await evaluate_interview_session(
        transcripts=empty_candidate_transcripts,
        target_role="Senior ML Engineer",
        target_company="Google",
        api_key=None,
    )

    assert report is not None
    assert report.overall_score < 2.0
    assert "No Hire" in report.recommendation
    assert "abruptly" in report.summary.lower() or "abruptly" in report.recommendation.lower()
    assert report.technical_depth.score == 1
    assert report.code_quality.score == 1
    assert len(report.question_critiques) >= 1

