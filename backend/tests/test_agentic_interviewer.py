"""Tests for AgenticInterviewer and Gemini Search Grounding."""

import pytest

from app.schemas import CompanyArchetype, InterviewMode, InterviewStage
from app.services.agentic_interviewer import AgenticInterviewer
from app.services.gemini_search_grounding import (
    fetch_recent_company_interview_questions,
)


@pytest.mark.asyncio
async def test_agentic_interviewer_self_introduction():
    """Verify interviewer introduces themselves, their team, and sets agenda."""
    agent = AgenticInterviewer(
        session_id="test-session-agent",
        target_role="Senior ML Engineer",
        target_company="Swiggy",
        company_archetype=CompanyArchetype.INDIAN_PRODUCT,
        interview_mode=InterviewMode.ML_BREADTH,
        persona_id="elena",
    )

    intro = await agent.generate_self_introduction()
    assert len(intro) > 30
    assert "Elena" in intro or "Swiggy" in intro
    assert (
        "dialogue" in intro.lower() or "journey" in intro.lower() or "background" in intro.lower()
    )


@pytest.mark.asyncio
async def test_agentic_interviewer_silence_handling():
    """Verify patience and gentle silence handling."""
    agent = AgenticInterviewer(
        session_id="test-session-agent",
        target_role="Staff ML Engineer",
        target_company="Google",
    )

    nudge_1 = await agent.handle_silence(seconds_silent=18, stage=InterviewStage.INTRO)
    assert "time" in nudge_1.lower()

    nudge_2 = await agent.handle_silence(seconds_silent=35, stage=InterviewStage.INTRO)
    assert "ready" in nudge_2.lower() or "mind" in nudge_2.lower()


@pytest.mark.asyncio
async def test_agentic_interviewer_ml_breadth_and_depth_turns():
    """Verify track-specific intelligent probing in ML Breadth and Depth."""
    breadth_agent = AgenticInterviewer(
        session_id="test-breadth",
        interview_mode=InterviewMode.ML_BREADTH,
    )
    b_resp = await breadth_agent.generate_turn_response(
        user_text="I prefer L1 regularization because it sets coefficients to zero.",
        stage=InterviewStage.ML_BREADTH,
    )
    assert len(b_resp) > 20
    assert "l1" in b_resp.lower() or "lasso" in b_resp.lower() or "feature" in b_resp.lower()

    depth_agent = AgenticInterviewer(
        session_id="test-depth",
        interview_mode=InterviewMode.ML_DEPTH,
    )
    d_resp = await depth_agent.generate_turn_response(
        user_text="The gradient of binary cross-entropy with sigmoid simplifies to p minus y.",
        stage=InterviewStage.ML_DEPTH,
    )
    assert len(d_resp) > 20
    assert "gradient" in d_resp.lower() or "loss" in d_resp.lower() or "sigmoid" in d_resp.lower()


@pytest.mark.asyncio
async def test_gemini_search_grounding_fallback_catalog():
    """Verify curated company questions fallback for Indian Product tech and FAANG."""
    swiggy_qs = await fetch_recent_company_interview_questions(
        company="Swiggy",
        role="Senior ML Engineer",
        track="ML_SYSTEM_DESIGN",
    )
    assert len(swiggy_qs) >= 2
    assert any(
        "swiggy" in q.lower() or "delivery" in q.lower() or "eta" in q.lower() for q in swiggy_qs
    )

    cred_qs = await fetch_recent_company_interview_questions(
        company="CRED",
        role="Senior Data Scientist",
    )
    assert len(cred_qs) >= 2
    assert any(
        "cred" in q.lower() or "fraud" in q.lower() or "imbalance" in q.lower() for q in cred_qs
    )
