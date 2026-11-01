"""Database engine and SQLAlchemy ORM models for AI Interviewer."""

import datetime
from collections.abc import AsyncGenerator

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


class InterviewSessionModel(Base):
    """Stores metadata, uploaded resume, and current state of an interview session."""

    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    interview_mode = Column(String(50), default="FULL_LOOP", nullable=False)
    target_role = Column(String(100), default="Senior Machine Learning Engineer")
    target_company = Column(String(100), default="Top Tech")
    job_description = Column(Text, nullable=True)

    resume_filename = Column(String(255), nullable=True)
    resume_text = Column(Text, nullable=True)
    claim_graph = Column(Text, nullable=True)  # JSON-encoded CandidateClaimGraph

    status = Column(String(30), default="CREATED", nullable=False)
    fsm_state = Column(String(50), default="INTRO", nullable=False)
    active_question_id = Column(String(100), nullable=True)
    api_key = Column(String(255), nullable=True)

    # Relationships
    transcripts = relationship(
        "TranscriptTurnModel", back_populates="session", cascade="all, delete-orphan"
    )
    evaluation = relationship(
        "EvaluationReportModel",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class TranscriptTurnModel(Base):
    """Stores individual turns spoken or executed during the interview."""

    __tablename__ = "transcript_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    stage = Column(String(50), nullable=False)
    speaker = Column(String(20), nullable=False)  # interviewer, candidate, system
    text = Column(Text, nullable=False)
    code_snapshot = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    session = relationship("InterviewSessionModel", back_populates="transcripts")


class EvaluationReportModel(Base):
    """Stores post-interview BARS scorecard and STAR rewrites."""

    __tablename__ = "evaluation_reports"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    technical_depth_score = Column(Integer, nullable=False)
    production_tradeoffs_score = Column(Integer, nullable=False)
    code_quality_score = Column(Integer, nullable=False)
    communication_score = Column(Integer, nullable=False)
    overall_score = Column(Float, nullable=False)

    summary = Column(Text, nullable=False)
    strengths = Column(Text, nullable=False)  # JSON-encoded list of strings
    improvement_areas = Column(Text, nullable=False)  # JSON-encoded list of strings
    question_critiques = Column(Text, nullable=False)  # JSON-encoded list of QuestionCritique

    session = relationship("InterviewSessionModel", back_populates="evaluation")


async def init_db() -> None:
    """Initialize database tables and run automatic migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in settings.DATABASE_URL:
            result = await conn.execute(text("PRAGMA table_info(interview_sessions)"))
            columns = [row[1] for row in result.fetchall()]
            if "api_key" not in columns:
                await conn.execute(
                    text("ALTER TABLE interview_sessions ADD COLUMN api_key VARCHAR(255)")
                )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
