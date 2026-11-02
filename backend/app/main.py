"""FastAPI Application Entry Point for AI Interviewer."""

import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import (
    EvaluationReportModel,
    InterviewSessionModel,
    TranscriptTurnModel,
    get_db,
    init_db,
)
from app.schemas import (
    BARSReport,
    CandidateClaimGraph,
    DimensionScore,
    InterviewMode,
    InterviewStage,
    QuestionCategory,
    QuestionCritique,
    QuestionItem,
    SessionDetailResponse,
    SessionInitResponse,
)
from app.services.fsm_orchestrator import InterviewFSM
from app.services.gemini_live import LiveInterviewSessionHandler
from app.services.gemini_search_grounding import fetch_recent_company_interview_questions
from app.services.question_bank import (
    get_all_questions,
    get_question_by_id,
    get_questions_by_category,
    get_random_question,
)
from app.services.resume_parser import extract_text_from_pdf, generate_claim_graph
from app.services.rubric_evaluator import evaluate_interview_session

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize SQLite database schema on startup."""
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Privacy-First Multimodal Technical Interviewer for Senior DS & ML Engineers",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "project": settings.PROJECT_NAME, "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Session Management Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/session/init", response_model=SessionInitResponse)
async def init_session(
    resume_file: UploadFile | None = File(None),
    target_role: str = Form("Senior Machine Learning Engineer"),
    target_company: str = Form("Top Tech"),
    company_archetype: str = Form("FAANG_GLOBAL"),
    interview_mode: InterviewMode = Form(InterviewMode.FULL_LOOP),
    enable_live_web_search: bool = Form(False),
    job_description: str | None = Form(None),
    api_key: str | None = Form(None),
    question_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Initialize a new interview session and extract CandidateClaimGraph from PDF resume."""
    session_id = str(uuid.uuid4())
    resume_text = ""
    filename = None

    if resume_file:
        filename = resume_file.filename
        pdf_bytes = await resume_file.read()
        resume_text = extract_text_from_pdf(pdf_bytes)

    claim_graph = await generate_claim_graph(
        resume_text=resume_text,
        target_role=target_role,
        target_company=target_company,
        api_key=api_key,
    )

    if not question_id:
        if interview_mode == InterviewMode.SQL_PYTHON_CODING:
            random_q = (
                get_random_question(category=QuestionCategory.PYTHON) or get_random_question()
            )
            question_id = random_q.id if random_q else None
        elif interview_mode == InterviewMode.ML_SYSTEM_DESIGN:
            random_q = (
                get_random_question(category=QuestionCategory.ML_SYSTEM_DESIGN)
                or get_random_question()
            )
            question_id = random_q.id if random_q else None
        else:
            random_q = get_random_question()
            question_id = random_q.id if random_q else None

    fsm = InterviewFSM(mode=interview_mode, active_question_id=question_id)

    session_record = InterviewSessionModel(
        id=session_id,
        interview_mode=interview_mode.value,
        target_role=target_role,
        target_company=target_company,
        company_archetype=company_archetype,
        enable_live_web_search=enable_live_web_search,
        job_description=job_description,
        resume_filename=filename,
        resume_text=resume_text,
        claim_graph=claim_graph.model_dump_json() if claim_graph else None,
        status="IN_PROGRESS",
        fsm_state=fsm.current_stage.value,
        active_question_id=fsm.active_question_id,
        api_key=api_key.strip() if api_key and api_key.strip() else None,
    )
    db.add(session_record)
    await db.commit()
    await db.refresh(session_record)

    return SessionInitResponse(
        session_id=session_record.id,
        interview_mode=InterviewMode(session_record.interview_mode),
        target_role=session_record.target_role,
        target_company=session_record.target_company,
        company_archetype=session_record.company_archetype or "FAANG_GLOBAL",
        enable_live_web_search=session_record.enable_live_web_search or False,
        claim_graph=claim_graph,
        initial_stage=fsm.current_stage,
        created_at=session_record.created_at,
    )


@app.get("/api/session/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve session details, claim graph, and current question."""
    session = await db.get(InterviewSessionModel, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    claim_graph = None
    if session.claim_graph:
        claim_graph = CandidateClaimGraph.model_validate_json(session.claim_graph)

    active_q = (
        get_question_by_id(session.active_question_id) if session.active_question_id else None
    )

    return SessionDetailResponse(
        session_id=session.id,
        status=session.status,
        interview_mode=InterviewMode(session.interview_mode),
        fsm_state=InterviewStage(session.fsm_state),
        target_role=session.target_role,
        target_company=session.target_company,
        company_archetype=getattr(session, "company_archetype", "FAANG_GLOBAL") or "FAANG_GLOBAL",
        enable_live_web_search=getattr(session, "enable_live_web_search", False) or False,
        claim_graph=claim_graph,
        created_at=session.created_at,
        active_question=active_q,
    )


@app.get("/api/questions/recent_real_world")
async def get_recent_real_world_questions(
    company: str = "Google",
    role: str = "Senior Machine Learning Engineer",
    track: str = "ML_SYSTEM_DESIGN",
    api_key: str | None = None,
):
    """Fetch recently reported actual interview questions via Gemini Google Search grounding or curated fallback."""
    questions = await fetch_recent_company_interview_questions(
        company=company,
        role=role,
        track=track,
        api_key=api_key,
    )
    return {"company": company, "role": role, "track": track, "questions": questions}


@app.get("/api/session/{session_id}/transcripts")
async def get_transcripts(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all transcript turns for an interview session."""
    query = (
        select(TranscriptTurnModel)
        .where(TranscriptTurnModel.session_id == session_id)
        .order_by(TranscriptTurnModel.timestamp.asc())
    )
    result = await db.execute(query)
    turns = result.scalars().all()
    return [
        {
            "id": turn.id,
            "stage": turn.stage,
            "speaker": turn.speaker,
            "text": turn.text,
            "code_snapshot": turn.code_snapshot,
            "timestamp": turn.timestamp.isoformat(),
        }
        for turn in turns
    ]


@app.post("/api/session/{session_id}/advance_stage")
async def advance_stage(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Manually advance the interview to the next FSM stage."""
    session = await db.get(InterviewSessionModel, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    fsm = InterviewFSM(
        mode=InterviewMode(session.interview_mode),
        initial_stage=InterviewStage(session.fsm_state),
        active_question_id=session.active_question_id,
    )
    new_stage, announcement = fsm.transition_next()

    session.fsm_state = new_stage.value
    session.active_question_id = fsm.active_question_id
    await db.commit()

    return {
        "previous_stage": session.fsm_state,
        "new_stage": new_stage.value,
        "announcement": announcement,
    }


@app.post("/api/session/{session_id}/switch_question")
async def switch_question(
    session_id: str,
    question_id: str | None = Query(None),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Switch active question for the session to a specific ID or next randomized question from bank."""
    session = await db.get(InterviewSessionModel, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    new_q = None
    if question_id:
        new_q = get_question_by_id(question_id)
    else:
        # Determine appropriate category based on current stage or query
        cat_enum = None
        if category:
            try:
                cat_enum = QuestionCategory(category)
            except ValueError:
                pass
        if not cat_enum:
            curr_q = (
                get_question_by_id(session.active_question_id)
                if session.active_question_id
                else None
            )
            if curr_q:
                cat_enum = curr_q.category
            elif session.fsm_state == "ML_SYSTEM_DESIGN":
                cat_enum = QuestionCategory.ML_SYSTEM_DESIGN
            else:
                cat_enum = QuestionCategory.SQL

        available = [
            q for q in get_questions_by_category(cat_enum) if q.id != session.active_question_id
        ]
        if available:
            import random

            new_q = random.choice(available)
        else:
            new_q = get_question_by_id(session.active_question_id)

    if not new_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No suitable question found"
        )

    session.active_question_id = new_q.id
    await db.commit()

    return {
        "status": "success",
        "new_question": new_q,
    }


# ---------------------------------------------------------------------------
# Post-Interview BARS Evaluation Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/session/{session_id}/evaluate", response_model=BARSReport)
async def evaluate_session(
    session_id: str,
    api_key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Generate post-interview BARS rubric evaluation and STAR rewrites."""
    session = await db.get(InterviewSessionModel, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Fetch transcripts
    query = (
        select(TranscriptTurnModel)
        .where(TranscriptTurnModel.session_id == session_id)
        .order_by(TranscriptTurnModel.timestamp.asc())
    )
    result = await db.execute(query)
    turns = result.scalars().all()

    transcript_dicts = [
        {
            "stage": turn.stage,
            "speaker": turn.speaker,
            "text": turn.text,
            "code_snapshot": turn.code_snapshot,
        }
        for turn in turns
    ]

    effective_key = api_key or session.api_key
    report = await evaluate_interview_session(
        transcripts=transcript_dicts,
        target_role=session.target_role,
        target_company=session.target_company,
        api_key=effective_key,
    )

    # Upsert evaluation report in SQLite
    existing_report = await db.get(EvaluationReportModel, session_id)
    if existing_report:
        await db.delete(existing_report)

    eval_record = EvaluationReportModel(
        id=session_id,
        session_id=session_id,
        technical_depth_score=report.technical_depth.score,
        production_tradeoffs_score=report.production_tradeoffs.score,
        code_quality_score=report.code_quality.score,
        communication_score=report.communication_clarity.score,
        overall_score=report.overall_score,
        summary=report.summary,
        strengths=json.dumps(report.key_strengths),
        improvement_areas=json.dumps(report.critical_improvement_areas),
        question_critiques=json.dumps([qc.model_dump() for qc in report.question_critiques]),
    )
    session.status = "EVALUATED"
    db.add(eval_record)
    await db.commit()

    return report


@app.get("/api/session/{session_id}/report")
async def get_evaluation_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve saved BARS evaluation report."""
    eval_record = await db.get(EvaluationReportModel, session_id)
    if not eval_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation report not found. Call /evaluate first.",
        )

    critiques_raw = json.loads(eval_record.question_critiques)
    critiques = [QuestionCritique.model_validate(c) for c in critiques_raw]

    return BARSReport(
        overall_score=eval_record.overall_score,
        recommendation="Hire" if eval_record.overall_score >= 3.5 else "Leaning No Hire",
        technical_depth=DimensionScore(
            dimension="Technical Depth & Math",
            score=eval_record.technical_depth_score,
            rationale="Demonstrated technical foundation on core ML principles.",
        ),
        production_tradeoffs=DimensionScore(
            dimension="Production & Business Trade-offs",
            score=eval_record.production_tradeoffs_score,
            rationale="Operational engineering and production latency awareness.",
        ),
        code_quality=DimensionScore(
            dimension="Code/SQL Quality & Complexity",
            score=eval_record.code_quality_score,
            rationale="Algorithmic problem solving and query precision.",
        ),
        communication_clarity=DimensionScore(
            dimension="Communication Clarity (STAR/Pyramid)",
            score=eval_record.communication_score,
            rationale="Structured STAR communication and clear delivery.",
        ),
        summary=eval_record.summary,
        key_strengths=json.loads(eval_record.strengths),
        critical_improvement_areas=json.loads(eval_record.improvement_areas),
        question_critiques=critiques,
    )


# ---------------------------------------------------------------------------
# Questions Catalog Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/questions", response_model=list[QuestionItem])
async def list_questions(category: QuestionCategory | None = Query(None)):
    """List questions in the bank, optionally filtered by category."""
    if category:
        return get_questions_by_category(category)
    return get_all_questions()


@app.get("/api/questions/{question_id}", response_model=QuestionItem)
async def get_question(question_id: str):
    """Retrieve a single question by ID."""
    q = get_question_by_id(question_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return q


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/interview/{session_id}")
async def websocket_interview_endpoint(
    websocket: WebSocket,
    session_id: str,
    api_key: str | None = Query(None),
):
    """Live bidirectional audio, code, and stage WebSocket endpoint."""
    handler = LiveInterviewSessionHandler(
        websocket=websocket,
        session_id=session_id,
        api_key=api_key,
    )
    await handler.handle_client()
