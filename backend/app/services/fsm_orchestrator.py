"""Deterministic Finite State Machine (FSM) and Rolling Context Compaction."""

from app.schemas import FSMStateSnapshot, InterviewMode, InterviewStage, QuestionItem
from app.services.question_bank import get_questions_by_category

STAGE_BUDGETS_SECONDS: dict[InterviewStage, int] = {
    InterviewStage.INTRO: 120,  # 2 minutes
    InterviewStage.RESUME_DEEP_DIVE: 600,  # 10 minutes
    InterviewStage.LIVE_CODING_SQL_PYTHON: 720,  # 12 minutes
    InterviewStage.ML_SYSTEM_DESIGN: 600,  # 10 minutes
    InterviewStage.WRAP_UP: 120,  # 2 minutes
}

MODE_STAGES: dict[InterviewMode, list[InterviewStage]] = {
    InterviewMode.FULL_LOOP: [
        InterviewStage.INTRO,
        InterviewStage.RESUME_DEEP_DIVE,
        InterviewStage.LIVE_CODING_SQL_PYTHON,
        InterviewStage.ML_SYSTEM_DESIGN,
        InterviewStage.WRAP_UP,
    ],
    InterviewMode.RESUME_DEEP_DIVE: [
        InterviewStage.INTRO,
        InterviewStage.RESUME_DEEP_DIVE,
        InterviewStage.WRAP_UP,
    ],
    InterviewMode.SQL_PYTHON_CODING: [
        InterviewStage.INTRO,
        InterviewStage.LIVE_CODING_SQL_PYTHON,
        InterviewStage.WRAP_UP,
    ],
    InterviewMode.ML_SYSTEM_DESIGN: [
        InterviewStage.INTRO,
        InterviewStage.ML_SYSTEM_DESIGN,
        InterviewStage.WRAP_UP,
    ],
}


class InterviewFSM:
    """Manages deterministic interview progression and stage constraints."""

    def __init__(
        self,
        mode: InterviewMode = InterviewMode.FULL_LOOP,
        initial_stage: InterviewStage | None = None,
        active_question_id: str | None = None,
    ):
        self.mode = mode
        self.stages: list[InterviewStage] = MODE_STAGES.get(
            mode, MODE_STAGES[InterviewMode.FULL_LOOP]
        )
        self.current_index: int = 0

        if initial_stage and initial_stage in self.stages:
            self.current_index = self.stages.index(initial_stage)

        self.stage_start_elapsed: int = 0
        self.total_elapsed: int = 0
        self.candidate_active_working: bool = False
        self.active_question_id: str | None = active_question_id
        self.stage_summaries: dict[InterviewStage, str] = {}

    @property
    def current_stage(self) -> InterviewStage:
        return self.stages[self.current_index]

    @property
    def is_terminal(self) -> bool:
        return self.current_index >= len(self.stages) - 1

    @property
    def current_budget_seconds(self) -> int:
        return STAGE_BUDGETS_SECONDS.get(self.current_stage, 300)

    def set_working_state(self, is_active: bool) -> None:
        """Update VAD gate state indicating user is actively coding/drawing."""
        self.candidate_active_working = is_active

    def tick(self, seconds: int = 1) -> None:
        """Advance time counter."""
        self.total_elapsed += seconds
        self.stage_start_elapsed += seconds

    def should_transition(self) -> bool:
        """Check if time budget expired and user is not in the middle of active typing."""
        if self.is_terminal:
            return False
        # Do not interrupt while user is actively typing or executing code
        if self.candidate_active_working:
            return False
        return self.stage_start_elapsed >= self.current_budget_seconds

    def transition_next(self) -> tuple[InterviewStage, str]:
        """Advance to the next stage in the pipeline."""
        if self.is_terminal:
            return self.current_stage, "The interview is now in the final wrap-up stage."

        prev_stage = self.current_stage
        self.current_index += 1
        self.stage_start_elapsed = 0
        new_stage = self.current_stage

        # Assign relevant question if entering coding or system design
        if new_stage == InterviewStage.LIVE_CODING_SQL_PYTHON and not self.active_question_id:
            sql_questions = get_questions_by_category(_app_schemas_category := "SQL")
            if sql_questions:
                self.active_question_id = sql_questions[0].id

        transition_announcement = (
            f"Transitioning from {prev_stage.value} to {new_stage.value}. "
            f"Focus for this stage: {new_stage.value}."
        )
        return new_stage, transition_announcement

    def record_stage_summary(self, stage: InterviewStage, summary: str) -> None:
        """Record compacted summary of a finished stage."""
        self.stage_summaries[stage] = summary

    def get_compacted_context(self) -> str:
        """Generate bounded O(1) rolling context string containing past stage summaries."""
        if not self.stage_summaries:
            return "No previous stage summaries yet."

        lines = ["--- COMPACTED PREVIOUS STAGES SUMMARY ---"]
        for stage, summary in self.stage_summaries.items():
            lines.append(f"[{stage.value}]: {summary}")
        lines.append("------------------------------------------")
        return "\n".join(lines)

    def get_snapshot(self, active_question: QuestionItem | None = None) -> FSMStateSnapshot:
        """Generate client-facing FSM state snapshot."""
        return FSMStateSnapshot(
            current_stage=self.current_stage,
            stage_index=self.current_index + 1,
            total_stages=len(self.stages),
            elapsed_seconds=self.total_elapsed,
            stage_budget_seconds=self.current_budget_seconds,
            candidate_active_working=self.candidate_active_working,
            active_question=active_question,
        )


def compact_stage_transcript(stage: InterviewStage, turns: list[dict[str, str]]) -> str:
    """Perform rolling context compaction on transcript turns for O(1) context scaling."""
    if not turns:
        return f"Stage {stage.value} concluded with minimal interaction."

    topics_covered = []
    for turn in turns:
        text = turn.get("text", "").strip()
        speaker = turn.get("speaker", "unknown")
        if text:
            # Extract first sentence as key point
            first_sentence = text.split(".")[0].strip()
            if len(first_sentence) > 10:
                topics_covered.append(f"{speaker}: {first_sentence[:100]}")

    sample_coverage = "; ".join(topics_covered[-4:]) if topics_covered else "Discussion concluded."
    return f"Completed {len(turns)} turns. Key points: {sample_coverage}"
