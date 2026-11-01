"""Tests for InterviewerEngine service."""

import pytest

from app.schemas import InterviewStage, QuestionCategory, QuestionItem
from app.services.interviewer_engine import (
    InterviewerEngine,
    answer_clarification_question,
    explain_question_in_detail,
    provide_hint,
)


@pytest.fixture
def mock_question():
    return QuestionItem(
        id="test_sql_q",
        category=QuestionCategory.SQL,
        title="Test Cohort Retention",
        prompt="Calculate month-over-month retention from Month 0 to Month 3.",
        difficulty="Senior",
        seed_sql="CREATE TABLE IF NOT EXISTS users (user_id VARCHAR);",
        verbal_introduction="We are analyzing how user cohorts retain across their first 3 months.",
        clarifications={"schema": "Users table has user_id and signup_date."},
        hints=["Use DATE_TRUNC to find cohort month."],
    )


def test_explain_question_in_detail(mock_question):
    explanation = explain_question_in_detail(mock_question)
    assert "Test Cohort Retention" in explanation
    assert "We are analyzing how user cohorts retain" in explanation
    assert "workbench" in explanation.lower() or "duckdb" in explanation.lower()


def test_answer_clarification_question(mock_question):
    ans_schema = answer_clarification_question(mock_question, "Can you clarify the schema?")
    assert "schema" in ans_schema.lower() or "users" in ans_schema.lower()

    ans_scale = answer_clarification_question(mock_question, "What is the expected scale and QPS?")
    assert "scale" in ans_scale.lower() or "production" in ans_scale.lower()


def test_provide_hint(mock_question):
    hints_given = []
    hint = provide_hint(mock_question, hints_given)
    assert "DATE_TRUNC" in hint
    assert len(hints_given) == 1


@pytest.mark.asyncio
async def test_interviewer_engine_turn_responses(mock_question):
    engine = InterviewerEngine(
        session_id="test_session",
        target_role="Staff ML Engineer",
        target_company="Google",
    )

    # Stage greeting
    greeting = engine.generate_stage_greeting(InterviewStage.INTRO)
    assert "Staff ML Engineer" in greeting
    assert "Google" in greeting

    # Coding stage greeting explains question
    code_greeting = engine.generate_stage_greeting(
        InterviewStage.LIVE_CODING_SQL_PYTHON, mock_question
    )
    assert "Test Cohort Retention" in code_greeting

    # Candidate asks to explain the question
    explain_reply = await engine.generate_turn_response(
        user_text="Can you explain the question in more detail?",
        stage=InterviewStage.LIVE_CODING_SQL_PYTHON,
        active_question=mock_question,
    )
    assert "Test Cohort Retention" in explain_reply

    # Candidate asks for a hint
    hint_reply = await engine.generate_turn_response(
        user_text="I'm stuck, can you give me a hint?",
        stage=InterviewStage.LIVE_CODING_SQL_PYTHON,
        active_question=mock_question,
    )
    assert "hint" in hint_reply.lower() or "date_trunc" in hint_reply.lower()

    # Candidate proposes an approach
    approach_reply = await engine.generate_turn_response(
        user_text="I'm thinking of using a window function with partition by user_id",
        stage=InterviewStage.LIVE_CODING_SQL_PYTHON,
        active_question=mock_question,
    )
    assert "window" in approach_reply.lower() or "frame" in approach_reply.lower()

    # Code feedback
    err_fb = engine.generate_code_feedback(
        code="SELECT *",
        language="sql",
        stdout="",
        error="Syntax error near SELECT",
        active_question=mock_question,
    )
    assert "error" in err_fb.lower() or "syntax" in err_fb.lower()

    pass_fb = engine.generate_code_feedback(
        code="def f(): pass",
        language="python",
        stdout="All tests passed successfully!",
        error=None,
        active_question=mock_question,
    )
    assert "pass" in pass_fb.lower()
    assert "complexity" in pass_fb.lower()
