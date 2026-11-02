"""Gemini Native Google Search Grounding for Live Real-World Interview Questions.

Uses google-genai SDK's native GoogleSearch tool to retrieve real-world interview
questions recently asked at specific companies (FAANG, Indian Product Tech, AI Startups)
without requiring any third-party search APIs.
Includes a rich offline fallback catalog for zero-key local operation.
"""

import logging

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

# Curated fallback library of verified real-world questions from top tier companies
CURATED_REAL_WORLD_QUESTIONS: dict[str, list[str]] = {
    "swiggy": [
        "How would you model dynamic delivery fee multipliers during rain or traffic spikes while minimizing customer cart abandonment?",
        "Design the real-time ETA prediction system for Swiggy: how do you separate kitchen food preparation time variance from delivery partner transit time?",
        "How do you handle cold-start recommendation for newly onboarded restaurants that have zero historical order ratings?",
        "How would you implement semantic search on restaurant menus that gracefully handles phonetic Indian English and transliterated queries (e.g. 'biryani' vs 'biriyani')?",
    ],
    "zomato": [
        "How would you model and detect fraudulent restaurant reviews and fake order cancellations in real time?",
        "Design a ranking model for Zomato Dining Out that balances user distance, average spend, and historical cuisine affinity.",
        "How would you measure the offline vs. online metric alignment when optimizing restaurant listing rank for long-term user retention instead of immediate clicks?",
    ],
    "cred": [
        "In credit card payment anomaly detection at CRED, fraud accounts for <0.01% of transactions. How do you formulate loss functions and evaluate models under extreme class imbalance?",
        "Design a low-latency feature pipeline that computes a user's 30-day rolling transaction velocity across multiple cards within a 15ms SLA.",
        "How would you design an uplift modeling framework to target reward voucher notifications only to users whose payment behavior is persuadable?",
    ],
    "razorpay": [
        "How would you build an intelligent payment routing engine that dynamically predicts bank downtime and routes transactions to maximize success rates across 50+ banking APIs?",
        "Design a merchant risk classification system that predicts high-risk merchants prone to future chargeback disputes at the time of KYC onboarding.",
        "How do you guarantee point-in-time correctness in real-time fraud features without lookahead leakage when events arrive out-of-order via Kafka?",
    ],
    "flipkart": [
        "How do you build a product catalog classification model for 500 million SKUs that handles multi-lingual queries and transliterated Hinglish search terms?",
        "How would you formulate demand forecasting for Flipkart Big Billion Days flash sales where historical time-series data has massive structural demand spikes?",
        "Design a two-tower neural retrieval system for related product recommendations: how do you prevent popular items from dominating the retrieval candidate pool?",
    ],
    "zepto": [
        "How do you design a real-time dark store stock-out prediction model that updates available inventory within 200ms when orders are actively being picked?",
        "How would you optimize rider batching and multi-order dispatch for 10-minute deliveries using bipartite graph matching and travel time prediction?",
    ],
    "google": [
        "Explain the mathematical formulation of the cross-entropy loss gradient with respect to logits, and why temperature scaling calibrates confidence without changing rankings.",
        "How do you prevent data leakage and train-serve feature skew in large-scale multi-task ranking systems?",
        "In A/B testing with two-sided marketplace network effects (like YouTube or Google Ads), why does standard Bernoulli randomization violate SUTVA, and how do you design cluster-based randomization?",
    ],
    "meta": [
        "In deep learning recommendation models (DLRM), embedding tables for sparse categorical features are terabytes in size. How do you shard and distribute them across GPU memory?",
        "How would you design a feedback delay compensation model for ad conversions that take up to 7 days to finalize after the click event?",
    ],
    "stripe": [
        "How do you architect an online machine learning inference system for payment authorization with a hard 30ms p99 latency SLA and zero fallback downtime?",
        "How would you build an adversarial fraud detection system that resists evasion attacks where fraudsters intentionally modify transaction amounts to stay under detection thresholds?",
    ],
    "netflix": [
        "How does contextual bandit recommendation balance exploration and exploitation in real time compared to static matrix factorization or two-tower ANN?",
        "How would you design an offline counterfactual evaluation framework (Inverse Propensity Scoring) to evaluate recommendation models without running live A/B tests on every variant?",
    ],
    "ai_startup": [
        "When serving 70B open-weights LLMs in production, compare the memory and latency trade-offs of PagedAttention, Speculative Decoding, and FP8 Quantization.",
        "How do you architect an enterprise RAG pipeline with hybrid dense-sparse retrieval (HNSW + BM25) and cross-encoder re-ranking to achieve sub-400ms end-to-end response times?",
        "How do you evaluate and prevent prompt injection and tool-use authorization leakage in autonomous multi-step agent frameworks?",
    ],
}


async def fetch_recent_company_interview_questions(
    company: str,
    role: str = "Senior Machine Learning Engineer",
    track: str = "ML_SYSTEM_DESIGN",
    api_key: str | None = None,
) -> list[str]:
    """Retrieve recently asked real-world interview questions for a company and role.

    Uses Gemini's native GoogleSearch tool when an API key is available,
    or falls back to the curated engineering interview repository.
    """
    settings = get_settings()
    key = api_key or settings.GEMINI_API_KEY
    company_clean = company.strip().lower()

    if key and settings.ENVIRONMENT != "test":
        try:
            client = genai.Client(api_key=key)
            prompt = (
                f"Search for actual real-world technical interview questions asked at {company} "
                f"for {role} positions in 2025 or 2026, specifically focusing on {track}. "
                "Extract and list exactly 3 to 4 distinct, highly realistic, specific interview questions. "
                "Output each question on a new line prefixed with a dash (-). Do not include introductory conversational filler."
            )

            # Native Gemini Google Search Tool
            search_tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(
                tools=[search_tool],
                temperature=0.3,
                max_output_tokens=600,
            )

            response = await client.aio.models.generate_content(
                model=settings.EXTRACTOR_MODEL,
                contents=prompt,
                config=config,
            )

            if response.text:
                extracted = []
                for line in response.text.split("\n"):
                    cleaned = line.strip().lstrip("-*123456789. ")
                    if len(cleaned) > 20 and "?" in cleaned:
                        extracted.append(cleaned)
                if extracted:
                    logger.info(
                        "Successfully fetched %d live search questions for %s",
                        len(extracted),
                        company,
                    )
                    return extracted[:4]
        except Exception as exc:
            logger.warning(
                "Gemini Google Search grounding query failed: %s; using curated fallback", exc
            )

    # Offline curated fallback
    for key_name, questions in CURATED_REAL_WORLD_QUESTIONS.items():
        if key_name in company_clean or company_clean in key_name:
            return questions

    # Default to startup / tech depth questions if company not explicitly matched
    if "breadth" in track.lower():
        return [
            "How do you mathematically diagnose whether high validation loss is caused by high bias versus high variance, and what are your respective remediation strategies?",
            "Compare the convergence rate, computational complexity, and memory requirements of Batch Gradient Descent, Mini-Batch SGD, and Adam optimization.",
            "Explain why Area Under the Precision-Recall Curve (PR-AUC) is mathematically more informative than ROC-AUC when evaluating fraud detection with severe class imbalance.",
        ]
    elif "depth" in track.lower():
        return [
            "Walk me through the analytical derivation of the backpropagation gradient for Multi-Head Self-Attention: dL/dQ and dL/dK.",
            "Explain how FlashAttention uses GPU SRAM tiling and online softmax recomputation to achieve O(N) memory scaling instead of O(N^2).",
            "In Low-Rank Adaptation (LoRA), why is the scaling factor alpha/rank critical for stabilization, and how does the low-rank delta matrix interact with base model singular values?",
        ]
    elif "genai" in track.lower() or "llm" in track.lower():
        return CURATED_REAL_WORLD_QUESTIONS["ai_startup"]

    return CURATED_REAL_WORLD_QUESTIONS["google"]
