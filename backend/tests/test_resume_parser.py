"""Unit tests for resume parser and claim graph generator."""

import pymupdf as fitz
import pytest

from app.services.resume_parser import extract_text_from_pdf, generate_claim_graph


def test_extract_text_from_pdf_empty():
    assert extract_text_from_pdf(b"") == ""


def test_extract_text_from_synthetic_pdf():
    # Create a small in-memory PDF using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Jane Doe - Senior Machine Learning Engineer\nBuilt fraud detection model with 99% precision.",
    )
    pdf_bytes = doc.write()
    doc.close()

    extracted = extract_text_from_pdf(pdf_bytes)
    assert "Jane Doe" in extracted
    assert "Senior Machine Learning Engineer" in extracted
    assert "fraud detection" in extracted


@pytest.mark.asyncio
async def test_generate_claim_graph_fallback():
    resume_text = "Alex Mercer\nSenior Applied Scientist with 7 years experience in deep ranking."
    claim_graph = await generate_claim_graph(resume_text, "Staff ML Engineer", "TechCorp")

    assert claim_graph is not None
    assert len(claim_graph.projects) >= 2
    for proj in claim_graph.projects:
        assert proj.project_name
        assert len(proj.algorithms_used) > 0
        assert len(proj.claimed_metrics) > 0
        assert len(proj.probing_questions) == 3
        # Check probing questions address key bar-raiser criteria
        combined_probes = " ".join(proj.probing_questions).lower()
        assert any(
            term in combined_probes
            for term in ["leakage", "latency", "drift", "online", "threshold"]
        )
