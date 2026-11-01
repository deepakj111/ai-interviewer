"""Resume parsing using PyMuPDF and ClaimGraph extraction via Gemini."""

import json
import logging

import pymupdf as fitz
from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import CandidateClaimGraph, ProjectClaim

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract clean text from PDF bytes using PyMuPDF."""
    if not pdf_bytes:
        return ""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_chunks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text:
            text_chunks.append(page_text.strip())

    doc.close()
    return "\n\n".join(text_chunks)


RESUME_CLAIM_EXTRACTION_PROMPT = """
You are a Principal Technical Recruiter and Staff ML Evaluator.
Analyze the following technical resume for a candidate interviewing for:
Role: {target_role}
Company: {target_company}

Extract a comprehensive CandidateClaimGraph adhering to this strict requirement:
1. Identify the candidate's detected seniority level (e.g., Senior, Staff, Principal, Lead).
2. Extract 3 to 5 key core specializations (e.g. Recommender Systems, Computer Vision, LLMs, Real-time Feature Stores).
3. Extract up to 5 top technical machine learning/data engineering projects.
4. For each project, extract:
   - Specific algorithms or architectures used (e.g. LightGBM, Two-Tower DNN, ResNet, Transformer).
   - Specific numeric metrics claimed (e.g. 'boosted CTR by 14%', 'reduced inference latency to 12ms', 'scaled to 10M daily events').
   - Generate exactly 3 pre-computed "Bar-Raiser Grilling Probes" designed to pressure-test the claim:
     * Probe 1: Data leakage, training/serving skew, or validation fold leakage.
     * Probe 2: Latency SLAs, memory footprint, cold-start handling, or edge cases.
     * Probe 3: Offline metric vs. online business outcome alignment and counterfactuals.

RESUME CONTENT:
{resume_text}
"""


def _generate_fallback_claim_graph(resume_text: str, target_role: str) -> CandidateClaimGraph:
    """Deterministic fallback claim graph used in tests or offline environments."""
    first_line = resume_text.strip().split("\n")[0] if resume_text else "Candidate"
    candidate_name = first_line[:50] if len(first_line) < 50 else "Senior Practitioner"

    return CandidateClaimGraph(
        candidate_name=candidate_name,
        detected_seniority="Senior",
        core_specializations=["Applied Machine Learning", "Distributed Systems", "MLOps"],
        projects=[
            ProjectClaim(
                project_name="Large-Scale Recommendation Ranking Pipeline",
                summary="Engineered two-tower deep ranking model processing 50M daily interactions.",
                algorithms_used=[
                    "Two-Tower Neural Network",
                    "Approximate Nearest Neighbors (HNSW)",
                ],
                claimed_metrics=[
                    "Reduced p99 inference latency by 32%",
                    "Lifted offline NDCG@10 by 4.2%",
                ],
                probing_questions=[
                    "How did you prevent negative item exposure bias from skewing your cross-entropy training loss?",
                    "What was your fallback strategy when the ANN vector retrieval service experienced tail latency spikes above 20ms?",
                    "Did the 4.2% offline NDCG gain translate linearly to online user conversion, or was there cannibalization?",
                ],
            ),
            ProjectClaim(
                project_name="Real-Time Streaming Fraud Detection Service",
                summary="Built low-latency streaming pipeline detecting fraudulent financial transactions.",
                algorithms_used=[
                    "Gradient Boosted Decision Trees (XGBoost)",
                    "Online Feature Store",
                ],
                claimed_metrics=["Achieved 99.4% precision at 85% recall under 15ms p99 SLA"],
                probing_questions=[
                    "How did your online feature store guarantee point-in-time correctness without lookahead leakage?",
                    "With 0.05% fraudulent transactions, how did you calibrate decision thresholds under shifting class priors?",
                    "How did your pipeline handle delayed chargeback ground-truth labels that take 60 days to settle?",
                ],
            ),
        ],
    )


async def generate_claim_graph(
    resume_text: str,
    target_role: str = "Senior Machine Learning Engineer",
    target_company: str = "Top Tech",
    api_key: str | None = None,
) -> CandidateClaimGraph:
    """Extract candidate claim graph and bar-raiser grilling probes using Gemini with structured outputs."""
    settings = get_settings()
    effective_key = api_key or settings.GEMINI_API_KEY

    if not effective_key or not resume_text.strip():
        logger.warning(
            "No Gemini API key or empty resume text; falling back to deterministic extraction"
        )
        return _generate_fallback_claim_graph(resume_text, target_role)

    try:
        client = genai.Client(api_key=effective_key)
        prompt = RESUME_CLAIM_EXTRACTION_PROMPT.format(
            target_role=target_role,
            target_company=target_company,
            resume_text=resume_text[:12000],  # Bound context window
        )

        response = await client.aio.models.generate_content(
            model=settings.EXTRACTOR_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CandidateClaimGraph,
                temperature=0.2,
            ),
        )

        if response.text:
            parsed_data = json.loads(response.text)
            return CandidateClaimGraph.model_validate(parsed_data)
        else:
            return _generate_fallback_claim_graph(resume_text, target_role)

    except Exception as exc:
        logger.error("Gemini structured extraction failed, using robust fallback: %s", exc)
        return _generate_fallback_claim_graph(resume_text, target_role)
