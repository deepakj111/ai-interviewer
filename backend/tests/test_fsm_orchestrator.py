"""Unit tests for FSM orchestrator and context compaction."""

from app.schemas import InterviewMode, InterviewStage
from app.services.fsm_orchestrator import InterviewFSM, compact_stage_transcript


def test_fsm_initialization():
    fsm = InterviewFSM(mode=InterviewMode.FULL_LOOP)
    assert fsm.current_stage == InterviewStage.INTRO
    assert not fsm.is_terminal
    assert fsm.current_index == 0


def test_fsm_mode_stages():
    fsm_resume = InterviewFSM(mode=InterviewMode.RESUME_DEEP_DIVE)
    assert fsm_resume.stages == [
        InterviewStage.INTRO,
        InterviewStage.RESUME_DEEP_DIVE,
        InterviewStage.WRAP_UP,
    ]

    fsm_coding = InterviewFSM(mode=InterviewMode.SQL_PYTHON_CODING)
    assert fsm_coding.stages == [
        InterviewStage.INTRO,
        InterviewStage.LIVE_CODING_SQL_PYTHON,
        InterviewStage.WRAP_UP,
    ]


def test_fsm_transition_and_vad_gate():
    fsm = InterviewFSM(mode=InterviewMode.FULL_LOOP)
    assert not fsm.should_transition()

    # Tick past intro budget (120s)
    fsm.tick(125)
    assert fsm.should_transition()

    # If user is actively typing, transition should be blocked
    fsm.set_working_state(True)
    assert not fsm.should_transition()

    # Once user finishes typing, transition is allowed
    fsm.set_working_state(False)
    assert fsm.should_transition()

    # Transition to next stage
    new_stage, announcement = fsm.transition_next()
    assert new_stage == InterviewStage.RESUME_DEEP_DIVE
    assert "Resume Deep-Dive" in announcement or "RESUME_DEEP_DIVE" in announcement
    assert fsm.stage_start_elapsed == 0


def test_rolling_context_compaction():
    turns = [
        {"speaker": "interviewer", "text": "Tell me about your recommender system architecture."},
        {
            "speaker": "candidate",
            "text": "We deployed a two-tower deep model using Faiss indexing.",
        },
        {"speaker": "interviewer", "text": "How did you monitor embedding drift in production?"},
        {
            "speaker": "candidate",
            "text": "We computed daily Wasserstein distance across embedding slices.",
        },
    ]

    compacted = compact_stage_transcript(InterviewStage.RESUME_DEEP_DIVE, turns)
    assert "Completed 4 turns" in compacted
    assert "Wasserstein distance" in compacted

    fsm = InterviewFSM()
    fsm.record_stage_summary(InterviewStage.RESUME_DEEP_DIVE, compacted)
    ctx = fsm.get_compacted_context()
    assert "COMPACTED PREVIOUS STAGES SUMMARY" in ctx
    assert "[RESUME_DEEP_DIVE]" in ctx
