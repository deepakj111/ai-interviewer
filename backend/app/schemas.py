"""Pydantic schemas and structured output models for AI Interviewer."""

import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class InterviewMode(StrEnum):
    """Interview operational modes."""

    FULL_LOOP = "FULL_LOOP"
    RESUME_DEEP_DIVE = "RESUME_DEEP_DIVE"
    SQL_PYTHON_CODING = "SQL_PYTHON_CODING"
    ML_SYSTEM_DESIGN = "ML_SYSTEM_DESIGN"
    ML_BREADTH = "ML_BREADTH"
    ML_DEPTH = "ML_DEPTH"
    GENERATIVE_AI_LLM = "GENERATIVE_AI_LLM"


class InterviewStage(StrEnum):
    """Deterministic stages in the interview Finite State Machine."""

    INTRO = "INTRO"
    RESUME_DEEP_DIVE = "RESUME_DEEP_DIVE"
    LIVE_CODING_SQL_PYTHON = "LIVE_CODING_SQL_PYTHON"
    ML_SYSTEM_DESIGN = "ML_SYSTEM_DESIGN"
    ML_BREADTH = "ML_BREADTH"
    ML_DEPTH = "ML_DEPTH"
    GENERATIVE_AI = "GENERATIVE_AI"
    WRAP_UP = "WRAP_UP"


class CompanyArchetype(StrEnum):
    """Company cultural and engineering archetypes."""

    FAANG_GLOBAL = "FAANG_GLOBAL"
    INDIAN_PRODUCT = "INDIAN_PRODUCT"
    AI_STARTUP = "AI_STARTUP"


class QuestionCategory(StrEnum):
    """Categories of interview questions."""

    SQL = "SQL"
    PYTHON = "PYTHON"
    ML_SYSTEM_DESIGN = "ML_SYSTEM_DESIGN"
    ML_BREADTH = "ML_BREADTH"
    ML_DEPTH = "ML_DEPTH"
    GENERATIVE_AI = "GENERATIVE_AI"


# ---------------------------------------------------------------------------
# Claim Graph Schemas (Extracted from Resume)
# ---------------------------------------------------------------------------


class ProjectClaim(BaseModel):
    """Extracted project with technical claims and bar-raiser probes."""

    project_name: str = Field(..., description="Name of the machine learning or data project")
    summary: str = Field(..., description="1-2 sentence technical summary of the project")
    algorithms_used: list[str] = Field(
        default_factory=list,
        description="Core algorithms or architectures applied (e.g. XGBoost, Two-Tower, Transformer)",
    )
    claimed_metrics: list[str] = Field(
        default_factory=list,
        description="Specific metric improvements claimed (e.g. 'Reduced p99 latency by 35%')",
    )
    probing_questions: list[str] = Field(
        default_factory=list,
        description="3 pre-computed Bar-Raiser probing questions on data leakage, class imbalance, latency, drift, or metric alignment",
    )


class CandidateClaimGraph(BaseModel):
    """Full candidate technical claim graph extracted from resume."""

    candidate_name: str | None = Field(None, description="Candidate name if found")
    detected_seniority: str = Field(
        "Senior",
        description="Seniority assessment (e.g., Mid-Level, Senior, Staff/Principal)",
    )
    core_specializations: list[str] = Field(
        default_factory=list,
        description="Key specializations (e.g. Recommender Systems, LLM Ops, Computer Vision)",
    )
    projects: list[ProjectClaim] = Field(
        default_factory=list,
        description="Top 3 to 5 projects extracted from the resume with bar-raiser grilling probes",
    )


# ---------------------------------------------------------------------------
# Question Bank Schemas
# ---------------------------------------------------------------------------


class QuestionItem(BaseModel):
    """Standard interview question definition."""

    id: str
    category: QuestionCategory
    title: str
    prompt: str
    difficulty: str = "Senior"
    starter_code: str | None = None
    seed_sql: str | None = None
    unit_tests: str | None = None
    rubric_criteria: list[str] = Field(default_factory=list)
    verbal_introduction: str | None = None
    clarifications: dict[str, str] = Field(default_factory=dict)
    hints: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# FSM State & Session Schemas
# ---------------------------------------------------------------------------


class FSMStateSnapshot(BaseModel):
    """Current snapshot of the interview Finite State Machine."""

    current_stage: InterviewStage
    stage_index: int
    total_stages: int
    elapsed_seconds: int
    stage_budget_seconds: int
    candidate_active_working: bool = False
    active_question: QuestionItem | None = None


class SessionInitResponse(BaseModel):
    """Response returned upon creating an interview session."""

    session_id: str
    interview_mode: InterviewMode
    target_role: str
    target_company: str
    company_archetype: str = "FAANG_GLOBAL"
    enable_live_web_search: bool = False
    claim_graph: CandidateClaimGraph | None = None
    initial_stage: InterviewStage
    created_at: datetime.datetime


class SessionDetailResponse(BaseModel):
    """Detailed view of an interview session."""

    session_id: str
    status: str
    interview_mode: InterviewMode
    fsm_state: InterviewStage
    target_role: str
    target_company: str
    company_archetype: str = "FAANG_GLOBAL"
    enable_live_web_search: bool = False
    claim_graph: CandidateClaimGraph | None = None
    created_at: datetime.datetime
    active_question: QuestionItem | None = None


# ---------------------------------------------------------------------------
# BARS Evaluation Report Schemas
# ---------------------------------------------------------------------------


class QuestionCritique(BaseModel):
    """Question-by-question diff with gold-standard STAR rewrite."""

    question_asked: str
    candidate_answer_summary: str
    hiring_manager_critique: str
    gold_standard_rewrite: str


class DimensionScore(BaseModel):
    """Score and behavioral evidence for a single rubric dimension."""

    dimension: str
    score: int = Field(
        ..., ge=0, le=5, description="0 to 5 BARS score (0 = no evidence / unanswered)"
    )
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    rationale: str


class BARSReport(BaseModel):
    """Complete post-interview evaluation report."""

    overall_score: float = Field(..., ge=0.0, le=5.0)
    recommendation: str = Field(
        ...,
        description="Hiring recommendation: Strong Hire, Hire, Leaning Hire, Leaning No Hire, No Hire, Strong No Hire",
    )
    technical_depth: DimensionScore
    production_tradeoffs: DimensionScore
    code_quality: DimensionScore
    communication_clarity: DimensionScore
    summary: str
    key_strengths: list[str]
    critical_improvement_areas: list[str]
    question_critiques: list[QuestionCritique]


# ---------------------------------------------------------------------------
# WebSocket Communication Payloads
# ---------------------------------------------------------------------------


class ClientAudioPayload(BaseModel):
    """Audio chunk sent from client."""

    type: str = "audio"
    data: str  # Base64-encoded 16kHz PCM audio bytes


class ClientCodeUpdatePayload(BaseModel):
    """Code AST or snapshot sent from client Monaco editor."""

    type: str = "code_update"
    language: str  # python or sql
    code: str
    stdout: str | None = None
    error: str | None = None


class ClientCanvasUpdatePayload(BaseModel):
    """Excalidraw canvas snapshot sent from client."""

    type: str = "canvas_update"
    image_base64: str  # JPEG data URL or raw base64


class ClientWorkingStatePayload(BaseModel):
    """VAD suppression flag indicating candidate is actively typing/drawing."""

    type: str = "working_state"
    is_active: bool


class ClientInterruptPayload(BaseModel):
    """Barge-in signal indicating candidate has interrupted ongoing interviewer speech."""

    type: str = "interrupt"


class ClientSilencePingPayload(BaseModel):
    """Ping indicating candidate has been silent and may need encouragement or hint."""

    type: str = "silence_ping"
    seconds_silent: int = 18
