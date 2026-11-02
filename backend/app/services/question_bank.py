"""Curated 15-question Senior DS/ML interview bank with DuckDB seeds and unit tests."""

from app.schemas import QuestionCategory, QuestionItem

QUESTIONS_BANK: list[QuestionItem] = [
    # -------------------------------------------------------------------------
    # 5 SQL PROBLEMS (With DuckDB Seed Scripts)
    # -------------------------------------------------------------------------
    QuestionItem(
        id="sql_01_retention_cohort",
        category=QuestionCategory.SQL,
        title="Monthly User Retention Cohort Analysis",
        prompt=(
            "Write a SQL query to calculate month-over-month user retention cohorts. "
            "For each user's signup month (Cohort Month), calculate the percentage of users "
            "who executed at least one transaction in Month 0, Month 1, Month 2, and Month 3. "
            "Output columns: cohort_month, cohort_size, m0_retention_pct, m1_retention_pct, m2_retention_pct, m3_retention_pct."
        ),
        difficulty="Senior",
        starter_code="""-- Write your cohort retention query here
SELECT
    -- cohort_month, cohort_size, m0_retention_pct, ...
FROM users u
LEFT JOIN transactions t ON u.user_id = t.user_id
GROUP BY 1;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR PRIMARY KEY,
    signup_date DATE,
    country VARCHAR
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    amount DECIMAL(10, 2),
    transaction_date DATE
);

INSERT INTO users VALUES
    ('u1', '2024-01-10', 'US'),
    ('u2', '2024-01-15', 'US'),
    ('u3', '2024-01-20', 'UK'),
    ('u4', '2024-02-05', 'US'),
    ('u5', '2024-02-18', 'CA');

INSERT INTO transactions VALUES
    ('t1', 'u1', 49.99, '2024-01-12'),
    ('t2', 'u1', 99.00, '2024-02-14'),
    ('t3', 'u1', 19.99, '2024-03-01'),
    ('t4', 'u2', 25.00, '2024-01-15'),
    ('t5', 'u2', 30.00, '2024-03-22'),
    ('t6', 'u3', 15.00, '2024-01-21'),
    ('t7', 'u4', 100.00, '2024-02-05'),
    ('t8', 'u4', 120.00, '2024-03-10');
""",
        rubric_criteria=[
            "Correct use of DATE_TRUNC to define cohort month and transaction month",
            "Correct month difference calculation between signup and transaction date",
            "Conditional aggregation (COUNT(DISTINCT ...) FILTER or CASE WHEN) for cohort percentages",
            "Handling 0 transactions in subsequent months gracefully",
        ],
    ),
    QuestionItem(
        id="sql_02_rolling_spend_anomaly",
        category=QuestionCategory.SQL,
        title="Rolling 30-Day Moving Average Anomaly Detection",
        prompt=(
            "Detect fraudulent spend spikes: Identify transactions where the transaction amount is "
            "greater than 3 times the user's average daily spend over their preceding 30 days. "
            "Exclude users with fewer than 5 transactions in that lookback window."
        ),
        difficulty="Senior",
        starter_code="""-- Identify anomalous transactions using rolling window functions
SELECT
    transaction_id,
    user_id,
    amount,
    transaction_date
FROM transactions;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    amount DOUBLE,
    transaction_date DATE
);

INSERT INTO transactions VALUES
    ('tx1', 'u10', 10.0, '2024-01-01'),
    ('tx2', 'u10', 12.0, '2024-01-05'),
    ('tx3', 'u10', 11.0, '2024-01-10'),
    ('tx4', 'u10', 15.0, '2024-01-15'),
    ('tx5', 'u10', 14.0, '2024-01-20'),
    ('tx6', 'u10', 95.0, '2024-01-22'), -- anomaly!
    ('tx7', 'u20', 100.0, '2024-01-02');
""",
        rubric_criteria=[
            "Proper window framing: ROWS BETWEEN ... PRECEDING OR RANGE BETWEEN INTERVAL",
            "Exclusion of current row from historical moving average calculation",
            "Correct count filter (> 5 transactions in historical lookback)",
            "Query performance and avoidance of quadratic cartesian self-joins",
        ],
    ),
    QuestionItem(
        id="sql_03_clickstream_sessionization",
        category=QuestionCategory.SQL,
        title="Event Stream Sessionization (30-Minute Inactivity Demarcation)",
        prompt=(
            "Sessionize user web events: Assign a unique `session_id` to each event. "
            "A new session starts if more than 30 minutes of inactivity have elapsed since "
            "the user's previous event or if it is the user's very first event."
        ),
        difficulty="Senior",
        starter_code="""-- Sessionize events using window functions
SELECT
    event_id,
    user_id,
    event_time,
    -- generated session identifier
FROM events;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    event_time TIMESTAMP,
    event_type VARCHAR
);

INSERT INTO events VALUES
    ('e1', 'usr1', '2024-01-01 10:00:00', 'page_view'),
    ('e2', 'usr1', '2024-01-01 10:15:00', 'click'),
    ('e3', 'usr1', '2024-01-01 10:20:00', 'add_to_cart'),
    ('e4', 'usr1', '2024-01-01 11:10:00', 'page_view'), -- new session (>30 min gap)
    ('e5', 'usr1', '2024-01-01 11:25:00', 'checkout');
""",
        rubric_criteria=[
            "Accurate use of LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time)",
            "Timestamp delta comparison against 30-minute threshold (1800 seconds)",
            "Cumulative SUM() over step indicators to generate monotonically increasing session IDs",
        ],
    ),
    QuestionItem(
        id="sql_04_ab_test_lift_srm",
        category=QuestionCategory.SQL,
        title="A/B Experiment Conversion & Sample Ratio Mismatch (SRM) Check",
        prompt=(
            "Given an experiments table and user conversion events, write a query that outputs: "
            "the count of assigned users per variant, the observed conversion rate, and an indicator "
            "flag if variant allocation deviates from the expected 50/50 split by more than 2% (SRM sanity check)."
        ),
        difficulty="Senior",
        starter_code="""-- Calculate variant sizes, conversion rates, and SRM flag
SELECT
    variant_name,
    COUNT(DISTINCT e.user_id) AS total_users,
    COUNT(DISTINCT c.user_id) * 1.0 / COUNT(DISTINCT e.user_id) AS cvr
FROM experiment_assignments e
LEFT JOIN conversions c ON e.user_id = c.user_id
GROUP BY 1;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS experiment_assignments (
    user_id VARCHAR PRIMARY KEY,
    variant_name VARCHAR,
    assigned_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversions (
    conversion_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    converted_at TIMESTAMP,
    revenue DOUBLE
);

INSERT INTO experiment_assignments VALUES
    ('u1', 'control', '2024-02-01 09:00:00'),
    ('u2', 'treatment', '2024-02-01 09:05:00'),
    ('u3', 'treatment', '2024-02-01 09:10:00'),
    ('u4', 'control', '2024-02-01 09:15:00'),
    ('u5', 'treatment', '2024-02-01 09:20:00');

INSERT INTO conversions VALUES
    ('c1', 'u2', '2024-02-01 10:00:00', 50.0),
    ('c2', 'u5', '2024-02-01 11:00:00', 80.0);
""",
        rubric_criteria=[
            "Correct temporal filtering (only count conversions occurring AFTER assignment)",
            "Accurate conversion rate computation handling divide-by-zero",
            "SRM deviation check comparing variant counts against overall expected proportions",
        ],
    ),
    QuestionItem(
        id="sql_05_prediction_drift_deciles",
        category=QuestionCategory.SQL,
        title="ML Model Calibration Deciles & Prediction Drift",
        prompt=(
            "Write a query to evaluate ML model calibration. Bucket model predictions into 10 deciles "
            "using NTILE(10). For each decile, compute the average predicted probability vs. "
            "the actual empirical conversion rate (ground truth), and output the calibration gap."
        ),
        difficulty="Senior",
        starter_code="""-- Evaluate model calibration deciles
WITH scored_deciles AS (
    SELECT
        prediction_id,
        predicted_prob,
        actual_label,
        NTILE(10) OVER (ORDER BY predicted_prob ASC) AS decile
    FROM model_predictions
)
SELECT
    decile,
    COUNT(*) AS count_predictions,
    AVG(predicted_prob) AS avg_predicted,
    AVG(actual_label) AS actual_rate,
    ABS(AVG(predicted_prob) - AVG(actual_label)) AS calibration_gap
FROM scored_deciles
GROUP BY decile
ORDER BY decile;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS model_predictions (
    prediction_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    predicted_prob DOUBLE,
    actual_label INT
);

INSERT INTO model_predictions VALUES
    ('p1', 'u1', 0.05, 0),
    ('p2', 'u2', 0.12, 0),
    ('p3', 'u3', 0.25, 0),
    ('p4', 'u4', 0.48, 1),
    ('p5', 'u5', 0.65, 1),
    ('p6', 'u6', 0.78, 1),
    ('p7', 'u7', 0.85, 1),
    ('p8', 'u8', 0.92, 1);
""",
        rubric_criteria=[
            "Proper use of NTILE(10) window function ordered by probability",
            "Correct aggregation per decile of predicted vs actual outcomes",
            "Understanding of model reliability curves / calibration analysis",
        ],
    ),
    # -------------------------------------------------------------------------
    # 5 PYTHON / ALGORITHMIC PROBLEMS (With Unit Tests)
    # -------------------------------------------------------------------------
    QuestionItem(
        id="py_01_auc_roc",
        category=QuestionCategory.PYTHON,
        title="Exact ROC-AUC Computation Without Sklearn",
        prompt=(
            "Implement a function `calculate_roc_auc(y_true, y_score)` from first principles "
            "in O(N log N) time without using scikit-learn or scipy. "
            "`y_true` is a binary list (0 or 1), and `y_score` is a list of continuous prediction floats. "
            "Handle tied prediction scores properly."
        ),
        difficulty="Senior",
        starter_code="""from typing import List

def calculate_roc_auc(y_true: List[int], y_score: List[float]) -> float:
    \"\"\"
    Compute Area Under the Receiver Operating Characteristic Curve (ROC-AUC).
    Time Complexity: O(N log N)
    Space Complexity: O(N)
    \"\"\"
    # TODO: Implement using Wilcoxon-Mann-Whitney rank-sum statistic
    pass
""",
        unit_tests="""
def test_roc_auc():
    # Perfect ranking
    y_true = [0, 0, 1, 1]
    y_score = [0.1, 0.4, 0.35, 0.8]
    score = calculate_roc_auc(y_true, y_score)
    assert abs(score - 0.75) < 1e-4, f"Expected 0.75, got {score}"

    # Inverted ranking
    y_true_inv = [1, 1, 0, 0]
    y_score_inv = [0.1, 0.2, 0.8, 0.9]
    assert abs(calculate_roc_auc(y_true_inv, y_score_inv) - 0.0) < 1e-4

    # Perfect
    y_true_perf = [1, 0]
    y_score_perf = [0.9, 0.1]
    assert abs(calculate_roc_auc(y_true_perf, y_score_perf) - 1.0) < 1e-4
    print("All ROC-AUC tests passed!")

test_roc_auc()
""",
        rubric_criteria=[
            "Recognition of equivalence between ROC-AUC and the Wilcoxon-Mann-Whitney U statistic",
            "Correct handling of tied prediction scores via average ranks",
            "Optimal O(N log N) sorting time complexity instead of naive O(N^2) pairwise comparisons",
        ],
    ),
    QuestionItem(
        id="py_02_reservoir_sampling",
        category=QuestionCategory.PYTHON,
        title="Streaming Reservoir Sampling (Algorithm R)",
        prompt=(
            "Implement an online streaming sampler `ReservoirSampler(k)` that samples exactly `k` items "
            "uniformly at random from an unbounded stream of items of unknown length N. "
            "Ensure that every item seen so far has an exact k/n probability of being in the reservoir."
        ),
        difficulty="Senior",
        starter_code="""import random
from typing import Any, List, Optional

class ReservoirSampler:
    def __init__(self, k: int):
        self.k = k
        self.count = 0
        self.reservoir: List[Any] = []

    def feed(self, item: Any) -> None:
        \"\"\"Process a single incoming stream item in O(1) time.\"\"\"
        # TODO: Implement reservoir sampling logic
        pass

    def get_sample(self) -> List[Any]:
        return list(self.reservoir)
""",
        unit_tests="""
def test_reservoir_sampler():
    sampler = ReservoirSampler(3)
    stream = list(range(100))
    for x in stream:
        sampler.feed(x)
    sample = sampler.get_sample()
    assert len(sample) == 3
    assert all(item in stream for item in sample)
    print("Reservoir sampling test passed!")

test_reservoir_sampler()
""",
        rubric_criteria=[
            "First k items always populate the reservoir",
            "For item n > k, generate uniform random integer in [0, n-1]; replace if index < k",
            "Mathematical proof knowledge: P(item selected) = k/n at any step",
        ],
    ),
    QuestionItem(
        id="py_03_time_decay_feature",
        category=QuestionCategory.PYTHON,
        title="Vectorized Exponential Time-Decay Counter",
        prompt=(
            "Write a function `exponential_time_decay(events_df, half_life_hours)` that takes an event stream "
            "with `['user_id', 'timestamp', 'weight']` and computes the exponential decay cumulative sum "
            "for each user up to each event timestamp without lookahead data leakage."
        ),
        difficulty="Senior",
        starter_code="""import pandas as pd
import numpy as np

def exponential_time_decay(df: pd.DataFrame, half_life_hours: float) -> pd.Series:
    \"\"\"
    Compute cumulative decayed interaction score per user.
    decay = exp(-ln(2) * delta_t / half_life)
    \"\"\"
    # TODO: Implement vectorized computation per user
    pass
""",
        unit_tests="""
def test_time_decay():
    df = pd.DataFrame({
        'user_id': ['u1', 'u1', 'u1'],
        'timestamp': pd.to_datetime(['2024-01-01 00:00:00', '2024-01-01 02:00:00', '2024-01-01 04:00:00']),
        'weight': [1.0, 1.0, 1.0]
    })
    # Half life of 2 hours means value decays to 0.5 after 2 hours
    # First event = 1.0
    # Second event = 1.0 * 0.5 + 1.0 = 1.5
    # Third event = 1.5 * 0.5 + 1.0 = 1.75
    res = exponential_time_decay(df, half_life_hours=2.0)
    assert abs(res.iloc[0] - 1.0) < 1e-3
    assert abs(res.iloc[1] - 1.5) < 1e-3
    assert abs(res.iloc[2] - 1.75) < 1e-3
    print("Time decay test passed!")
""",
        rubric_criteria=[
            "Prevention of target leakage or lookahead bias (strictly causal computation)",
            "Vectorized calculation or efficient single-pass recursive formulation",
            "Correct exponential half-life decay math: lambda = ln(2) / half_life",
        ],
    ),
    QuestionItem(
        id="py_04_kmeans_step",
        category=QuestionCategory.PYTHON,
        title="Vectorized K-Means Assignment and Centroid Update",
        prompt=(
            "Implement one full iteration of Lloyd's K-Means algorithm `kmeans_iteration(X, centroids)` "
            "in NumPy without Python `for` loops over data points. "
            "`X` has shape (N, D), and `centroids` has shape (K, D). "
            "Return `(new_centroids, cluster_assignments)`."
        ),
        difficulty="Senior",
        starter_code="""import numpy as np
from typing import Tuple

def kmeans_iteration(X: np.ndarray, centroids: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    \"\"\"
    X: shape (N, D)
    centroids: shape (K, D)
    Returns: (new_centroids (K, D), cluster_assignments (N,))
    \"\"\"
    # TODO: Compute pairwise Euclidean distances using broadcasting
    pass
""",
        unit_tests="""
def test_kmeans():
    X = np.array([[0.0, 0.0], [0.1, 0.1], [10.0, 10.0], [10.1, 10.1]])
    centroids = np.array([[0.0, 0.0], [10.0, 10.0]])
    new_c, assign = kmeans_iteration(X, centroids)
    assert assign[0] == 0 and assign[1] == 0
    assert assign[2] == 1 and assign[3] == 1
    assert np.allclose(new_c[0], [0.05, 0.05])
    assert np.allclose(new_c[1], [10.05, 10.05])
    print("K-means iteration test passed!")

test_kmeans()
""",
        rubric_criteria=[
            "Broadcasting for pairwise Euclidean distance: ||x - c||^2 = ||x||^2 - 2x.c + ||c||^2",
            "NumPy argmin along centroid axis",
            "Centroid update using bincount or boolean masking",
            "Handling empty clusters gracefully",
        ],
    ),
    QuestionItem(
        id="py_05_scaled_dot_product_attention",
        category=QuestionCategory.PYTHON,
        title="Scaled Dot-Product Attention with Causal Mask",
        prompt=(
            "Implement scaled dot-product attention in NumPy: "
            "`scaled_dot_product_attention(Q, K, V, mask=None)` where `Attention(Q,K,V) = softmax(Q K^T / sqrt(d_k)) V`. "
            "Ensure numerical stability in the softmax computation (subtracting max) and correct application of additive causal mask."
        ),
        difficulty="Senior",
        starter_code="""import numpy as np
from typing import Optional

def scaled_dot_product_attention(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> np.ndarray:
    \"\"\"
    Q, K, V: shape (batch_size, seq_len, d_k)
    mask: shape (seq_len, seq_len) with 1 for attend, 0 for mask
    \"\"\"
    # TODO: Implement numerically stable scaled dot-product attention
    pass
""",
        unit_tests="""
def test_attention():
    np.random.seed(42)
    B, T, D = 2, 4, 8
    Q = np.random.randn(B, T, D)
    K = np.random.randn(B, T, D)
    V = np.random.randn(B, T, D)
    out = scaled_dot_product_attention(Q, K, V)
    assert out.shape == (B, T, D)
    assert not np.isnan(out).any()
    print("Scaled dot product attention test passed!")

test_attention()
""",
        rubric_criteria=[
            "Scaling by sqrt(d_k) to prevent vanishing gradients in softmax",
            "Numerically stable softmax: exp(x - max(x)) / sum(exp(x - max(x)))",
            "Proper masking with -1e9 or -inf before softmax",
        ],
    ),
    # -------------------------------------------------------------------------
    # 5 ML SYSTEM DESIGN PROBLEMS (With Detailed Rubrics)
    # -------------------------------------------------------------------------
    QuestionItem(
        id="sys_01_realtime_fraud",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Real-Time Payment Fraud Detection Engine (p99 < 25ms)",
        prompt=(
            "Design an end-to-end real-time fraud detection engine for an e-commerce payment processor "
            "processing 50,000 transactions per second. The model must return an allow/deny/step-up authentication "
            "verdict with a strict p99 latency SLA of 25ms. Address: feature store architecture (online vs offline), "
            "extreme class imbalance (0.01% fraud rate), delayed feedback labels (chargebacks take 30-90 days), and concept drift."
        ),
        difficulty="Senior / Staff",
        rubric_criteria=[
            "Low-latency serving architecture (Redis / Feast online feature store, ONNX runtime / TensorRT)",
            "Addressing delayed feedback and label leakage in training pipeline",
            "Handling extreme class imbalance (Focal Loss, hard negative mining, precision@recall constraints)",
            "Shadow deployment, fallback rule engine on timeout, and online model drift monitoring",
        ],
    ),
    QuestionItem(
        id="sys_02_multimodal_search",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Multimodal E-Commerce Search & Two-Tower Retrieval (100M Catalog)",
        prompt=(
            "Design a personalized multimodal search engine for a catalog of 100M items. "
            "Users can search via free-form text queries, uploaded photos, or both. "
            "Cover candidate generation (Two-Tower CLIP embeddings, ANN indexing via HNSW/IVF-PQ), "
            "multi-task ranking (CTR, CVR, Return Rate), and real-time business reranking (diversity, margin, sponsored items)."
        ),
        difficulty="Senior / Staff",
        rubric_criteria=[
            "Two-tower architecture for asymmetric multimodal query and product item embeddings",
            "Approximate Nearest Neighbor (ANN) index scaling with HNSW or ScaNN and sharding strategy",
            "Multi-task learning (MTL) ranking model combining click and conversion objectives",
            "Cold-start item indexing and real-time freshness updates",
        ],
    ),
    QuestionItem(
        id="sys_03_feed_ranking",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Personalized Social Feed Ranking with Delayed Negative Feedback",
        prompt=(
            "Design the recommendation and ranking engine for a high-volume social feed (1B active users). "
            "The system must retrieve and rank 50 items out of billions of posts in under 80ms. "
            "Specifically explain: multi-stage funnel (candidate generation, coarse ranking, fine ranking), "
            "mitigating exposure bias, and training with delayed negative feedback."
        ),
        difficulty="Senior / Staff",
        rubric_criteria=[
            "Multi-stage retrieval funnel architecture (Retrieval -> Heavy Ranker -> Reranking/Diversity)",
            "Debiasing techniques for position bias and exposure bias (Inverse Propensity Scoring)",
            "Addressing delayed feedback (Importance weighting or survival models for delayed conversions)",
            "Efficient caching and user state vector management",
        ],
    ),
    QuestionItem(
        id="sys_04_rag_guardrails",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Enterprise LLM RAG System with Semantic Caching & Guardrails",
        prompt=(
            "Design an enterprise retrieval-augmented generation (RAG) platform querying 10M internal technical and financial documents. "
            "Ensure response latency is < 1s for 95% of queries, hallucinations are caught before serving, and semantic caching "
            "reduces LLM inference cost by 40%. Cover chunking strategies, hybrid search (dense + BM25 sparse), cross-encoder reranking, "
            "and evaluation metrics (RAGAS: faithfulness, answer relevance, context recall)."
        ),
        difficulty="Senior / Staff",
        rubric_criteria=[
            "Hybrid dense vector + BM25 sparse retrieval with Reciprocal Rank Fusion (RRF)",
            "Cross-encoder reranker with latency/accuracy trade-off analysis",
            "Semantic caching layer (e.g., GPTCache / vector similarity thresholding)",
            "RAG evaluation framework (RAGAS / TruLens) and hallucination guardrails",
        ],
    ),
    QuestionItem(
        id="sys_05_pricing_eta",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Ride-Sharing Spatiotemporal ETA Prediction & Dynamic Surge Pricing",
        prompt=(
            "Design the machine learning system for real-time ride-sharing trip duration (ETA) prediction "
            "and dynamic surge pricing across 200 cities. Address spatiotemporal graph modeling (H3 hexagons / Road network graphs), "
            "weather and traffic volatility, fairness constraints in pricing, and model retraining cadence."
        ),
        difficulty="Senior / Staff",
        rubric_criteria=[
            "Spatial indexing using Uber H3 or S2 cells with hierarchical aggregations",
            "Spatiotemporal Graph Neural Networks (GNN) or gradient-boosted trees with lag features",
            "Reinforcement learning or PID control loops for supply/demand surge balancing",
            "Offline backtesting on historical counterfactuals without price elasticity bias",
        ],
    ),
    # -------------------------------------------------------------------------
    # ADDITIONAL SQL PROBLEMS (With Recursive CTE & Funnel Seeds)
    # -------------------------------------------------------------------------
    QuestionItem(
        id="sql_06_hierarchical_org_rollup",
        category=QuestionCategory.SQL,
        title="Recursive Org Tree Rollup & Cumulative Budget Hierarchy",
        prompt=(
            "Using a Recursive Common Table Expression (WITH RECURSIVE), calculate the total headcount "
            "and cumulative salary budget under every manager in the company hierarchy. "
            "For each employee who is a manager, output: manager_id, direct_reports_count, "
            "total_org_headcount, total_org_salary."
        ),
        difficulty="Senior",
        verbal_introduction=(
            "In this problem, we want to evaluate your ability to write recursive hierarchical queries in SQL. "
            "You have an employees table where each person reports to a manager_id. "
            "Your query must traverse parent-child relationships downward to compute cumulative headcounts and salary totals."
        ),
        starter_code="""-- Recursive organizational rollup query
WITH RECURSIVE org_hierarchy AS (
    -- Anchor member: every employee as the root of their subtree
    SELECT
        emp_id AS root_manager_id,
        emp_id,
        name,
        salary,
        manager_id,
        0 AS depth
    FROM employees
    UNION ALL
    -- Recursive member: child employees
    SELECT
        h.root_manager_id,
        e.emp_id,
        e.name,
        e.salary,
        e.manager_id,
        h.depth + 1
    FROM org_hierarchy h
    JOIN employees e ON h.emp_id = e.manager_id
)
SELECT
    root_manager_id AS manager_id,
    COUNT(DISTINCT emp_id) - 1 AS total_org_headcount,
    SUM(salary) AS total_org_salary
FROM org_hierarchy
GROUP BY root_manager_id
HAVING COUNT(DISTINCT emp_id) > 1
ORDER BY total_org_salary DESC;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS employees (
    emp_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    manager_id VARCHAR,
    salary DOUBLE,
    department VARCHAR
);

INSERT INTO employees VALUES
    ('e1', 'Sarah (CEO)', NULL, 250000.0, 'Executive'),
    ('e2', 'Michael (VP Eng)', 'e1', 180000.0, 'Engineering'),
    ('e3', 'Lisa (VP Sales)', 'e1', 170000.0, 'Sales'),
    ('e4', 'Alex (Director Eng)', 'e2', 140000.0, 'Engineering'),
    ('e5', 'David (Staff ML)', 'e4', 130000.0, 'Engineering'),
    ('e6', 'Emma (Senior ML)', 'e4', 115000.0, 'Engineering'),
    ('e7', 'John (Account Exec)', 'e3', 95000.0, 'Sales');
""",
        rubric_criteria=[
            "Correct formulation of anchor member and recursive member in WITH RECURSIVE",
            "Accurate join condition matching children (manager_id = parent emp_id)",
            "Handling cycle termination and depth tracking",
            "Correct aggregation of cumulative organizational headcount and salary",
        ],
        clarifications={
            "cycle": "Assume standard acyclic organizational hierarchy tree without circular manager references.",
            "direct": "Direct reports count includes only immediate child nodes (depth = 1), whereas total org includes the full subtree.",
        },
        hints=[
            "Start your anchor query with every employee acting as the root manager of their subtree.",
            "In the recursive step, join the working table with employees on h.emp_id = e.manager_id.",
            "Group by root_manager_id and filter out leaf employees who have no reports using HAVING COUNT(DISTINCT emp_id) > 1.",
        ],
    ),
    QuestionItem(
        id="sql_07_funnel_dropoff_attribution",
        category=QuestionCategory.SQL,
        title="Multi-Step Conversion Funnel & Drop-Off Velocity",
        prompt=(
            "Analyze a 4-step user checkout funnel: (1) view_item, (2) add_to_cart, (3) checkout_start, (4) purchase. "
            "Write a query calculating: (a) number of users reaching each step, (b) drop-off percentage from the prior step, "
            "and (c) average minutes elapsed from the first step to purchase for users who converted."
        ),
        difficulty="Senior",
        verbal_introduction=(
            "Funnel drop-off and conversion velocity are central to e-commerce and product data science. "
            "We have a funnel_events table recording event timestamps. "
            "You need to measure step completion counts, step-over-step drop-offs, and conversion velocities."
        ),
        starter_code="""-- Multi-step checkout funnel drop-off query
WITH step_counts AS (
    SELECT
        step_name,
        step_order,
        COUNT(DISTINCT user_id) AS user_count
    FROM funnel_events
    GROUP BY step_name, step_order
)
SELECT
    step_name,
    user_count,
    LAG(user_count) OVER (ORDER BY step_order) AS prev_step_count,
    ROUND(100.0 * (1.0 - (user_count * 1.0 / NULLIF(LAG(user_count) OVER (ORDER BY step_order), 0))), 2) AS drop_off_pct
FROM step_counts
ORDER BY step_order;
""",
        seed_sql="""
CREATE TABLE IF NOT EXISTS funnel_events (
    event_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    step_name VARCHAR,
    step_order INT,
    event_time TIMESTAMP
);

INSERT INTO funnel_events VALUES
    ('ev1', 'u1', 'view_item', 1, '2024-03-01 10:00:00'),
    ('ev2', 'u1', 'add_to_cart', 2, '2024-03-01 10:05:00'),
    ('ev3', 'u1', 'checkout_start', 3, '2024-03-01 10:10:00'),
    ('ev4', 'u1', 'purchase', 4, '2024-03-01 10:15:00'),
    ('ev5', 'u2', 'view_item', 1, '2024-03-01 11:00:00'),
    ('ev6', 'u2', 'add_to_cart', 2, '2024-03-01 11:10:00'),
    ('ev7', 'u3', 'view_item', 1, '2024-03-01 12:00:00'),
    ('ev8', 'u4', 'view_item', 1, '2024-03-01 13:00:00'),
    ('ev9', 'u4', 'add_to_cart', 2, '2024-03-01 13:05:00'),
    ('ev10', 'u4', 'checkout_start', 3, '2024-03-01 13:12:00'),
    ('ev11', 'u4', 'purchase', 4, '2024-03-01 13:30:00');
""",
        rubric_criteria=[
            "Correct step ordering filter ensuring chronological sequence per user",
            "Accurate step count and LAG window function to compute drop-off percentage",
            "Time difference calculation for end-to-end converted users",
            "Handling users who drop off before final checkout gracefully without division errors",
        ],
        clarifications={
            "order": "Users can only advance to step N if they completed step N-1 with an earlier timestamp.",
            "repeat": "If a user visits a step multiple times, take their earliest occurrence in this session.",
        },
        hints=[
            "First aggregate the user counts for each step_name and step_order.",
            "Apply LAG(user_count) OVER (ORDER BY step_order) to compute the step-over-step drop-off percentage.",
        ],
    ),
    # -------------------------------------------------------------------------
    # ADDITIONAL PYTHON PROBLEMS
    # -------------------------------------------------------------------------
    QuestionItem(
        id="py_06_bpe_tokenizer",
        category=QuestionCategory.PYTHON,
        title="Byte-Pair Encoding (BPE) Subword Tokenizer Merge Loop",
        prompt=(
            "Implement the core vocabulary learning loop for a Byte-Pair Encoding (BPE) subword tokenizer. "
            "Given a dictionary of word frequencies where words are represented as lists of character symbols "
            "ending with a special word-boundary token '</w>', iteratively find the most frequent adjacent pair of symbols "
            "across the entire corpus, merge all occurrences of that pair, and repeat for `num_merges` iterations. "
            "Return the list of learned merge pairs in order and the updated word symbol dictionary."
        ),
        difficulty="Senior",
        verbal_introduction=(
            "Subword tokenization like BPE is the foundation of modern Large Language Models such as GPT and LLaMA. "
            "In this exercise, you will implement the core BPE merge algorithm from scratch. "
            "Focus on clean frequency counting, efficient dictionary updates, and correct pair replacement."
        ),
        starter_code="""from collections import defaultdict

def train_bpe(word_freqs: dict[str, int], num_merges: int) -> tuple[list[tuple[str, str]], dict[str, int]]:
    \"\"\"
    Train BPE merge rules on a vocabulary of space-separated symbol words.

    Args:
        word_freqs: Mapping of space-delimited symbol strings to counts,
                    e.g. {'l o w </w>': 5, 'l o w e r </w>': 2, 'n e w e s t </w>': 6}
        num_merges: Number of merge iterations to perform.

    Returns:
        (merges_list, updated_word_freqs)
    \"\"\"
    vocab = dict(word_freqs)
    merges = []

    for _ in range(num_merges):
        # Count all adjacent pairs
        pairs = defaultdict(int)
        for word, freq in vocab.items():
            symbols = word.split()
            for i in range(len(symbols) - 1):
                pairs[(symbols[i], symbols[i + 1])] += freq

        if not pairs:
            break

        best_pair = max(pairs, key=pairs.get)
        if pairs[best_pair] == 0:
            break

        merges.append(best_pair)

        # Merge the best pair in vocabulary words
        new_vocab = {}
        target = " ".join(best_pair)
        replacement = "".join(best_pair)
        for word, freq in vocab.items():
            new_word = word.replace(target, replacement)
            new_vocab[new_word] = freq
        vocab = new_vocab

    return merges, vocab
""",
        unit_tests="""
def test_bpe():
    vocab = {
        'l o w </w>': 5,
        'l o w e r </w>': 2,
        'n e w e s t </w>': 6,
        'w i d e s t </w>': 3
    }
    merges, updated = train_bpe(vocab, 3)
    assert len(merges) == 3, f"Expected 3 merges, got {len(merges)}"
    assert ('e', 's') in merges, "Expected ('e', 's') merge rule"
    print("All BPE unit tests passed successfully!")

test_bpe()
""",
        rubric_criteria=[
            "Correct adjacent pair frequency counting weighted by word frequency",
            "Optimal argmax extraction of the highest frequency bigram",
            "Accurate replacement of symbol pairs without accidental partial merges",
            "Clean time complexity avoiding unneeded quadratic re-scans",
        ],
        clarifications={
            "tie": "If two symbol pairs have identical frequency counts, you may break ties deterministically.",
            "spaces": "Symbols within words are delimited by single spaces, and '</w>' denotes end-of-word boundary.",
        },
        hints=[
            "Use a defaultdict(int) to accumulate pair frequencies: for word, freq in vocab.items(): symbols = word.split(); for i in range(len(symbols)-1): pairs[symbols[i], symbols[i+1]] += freq.",
            "Pick best_pair = max(pairs, key=pairs.get). If pairs is empty or max count is 0, break early.",
            "Reconstruct each word in vocab by replacing 's1 s2' with 's1s2'.",
        ],
    ),
    QuestionItem(
        id="py_07_multi_head_attention_numpy",
        category=QuestionCategory.PYTHON,
        title="Vectorized Scaled Dot-Product Multi-Head Attention in NumPy",
        prompt=(
            "Implement the Multi-Head Scaled Dot-Product Attention mechanism in pure NumPy (no PyTorch/TensorFlow). "
            "Function signature: `multi_head_attention(Q, K, V, num_heads, causal_mask=False) -> np.ndarray`. "
            "Assume inputs Q, K, V have shape `(batch_size, seq_len, d_model)`. "
            "Split d_model into num_heads (where d_k = d_model // num_heads), compute scaled dot-product attention scores "
            "Q @ K.T / sqrt(d_k), apply softmax along the last dimension, apply optional causal lower-triangular mask, "
            "multiply by V, and concatenate heads back to `(batch_size, seq_len, d_model)`."
        ),
        difficulty="Senior",
        verbal_introduction=(
            "Multi-head self-attention is the central engine of the Transformer architecture. "
            "In this challenge, you will implement vectorized multi-head attention in pure NumPy. "
            "Pay close attention to tensor transpose shapes, numerical stability in softmax, and the causal autoregressive mask."
        ),
        starter_code="""import numpy as np

def multi_head_attention(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
    num_heads: int,
    causal_mask: bool = False
) -> np.ndarray:
    \"\"\"
    Computes Scaled Dot-Product Multi-Head Attention.

    Q, K, V: shape (batch_size, seq_len, d_model)
    Returns: shape (batch_size, seq_len, d_model)
    \"\"\"
    B, S, D = Q.shape
    d_k = D // num_heads

    # Reshape and transpose to (B, num_heads, S, d_k)
    Q_h = Q.reshape(B, S, num_heads, d_k).transpose(0, 2, 1, 3)
    K_h = K.reshape(B, S, num_heads, d_k).transpose(0, 2, 1, 3)
    V_h = V.reshape(B, S, num_heads, d_k).transpose(0, 2, 1, 3)

    # Scaled dot-product
    scores = np.matmul(Q_h, K_h.transpose(0, 1, 3, 2)) / np.sqrt(d_k)

    if causal_mask:
        mask = np.triu(np.ones((S, S)), k=1).astype(bool)
        scores[:, :, mask] = -1e9

    # Numerically stable softmax
    exp_scores = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
    attn_weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)

    # Apply attention to values
    context = np.matmul(attn_weights, V_h)

    # Transpose and concatenate back to (B, S, D)
    out = context.transpose(0, 2, 1, 3).reshape(B, S, D)
    return out
""",
        unit_tests="""
def test_mha():
    np.random.seed(42)
    B, S, D, H = 2, 4, 16, 4
    Q = np.random.randn(B, S, D)
    K = np.random.randn(B, S, D)
    V = np.random.randn(B, S, D)

    out = multi_head_attention(Q, K, V, num_heads=H, causal_mask=False)
    assert out.shape == (B, S, D), f"Expected shape {(B, S, D)}, got {out.shape}"
    assert not np.isnan(out).any(), "Output contains NaN values"

    out_causal = multi_head_attention(Q, K, V, num_heads=H, causal_mask=True)
    assert out_causal.shape == (B, S, D), "Causal output shape mismatch"
    assert not np.isnan(out_causal).any(), "Causal output contains NaN values"
    print("Multi-Head Attention tests passed successfully!")

test_mha()
""",
        rubric_criteria=[
            "Correct tensor reshaping and transposition: (batch, seq, heads, d_k) -> (batch, heads, seq, d_k)",
            "Scaling by 1 / sqrt(d_k) to prevent vanishing gradients in softmax",
            "Numerically stable softmax (subtracting max before exp)",
            "Correct application of causal mask (-1e9 or -inf on upper triangle)",
            "Clean concatenation back to (batch, seq, d_model)",
        ],
        clarifications={
            "divisible": "You can assume d_model is evenly divisible by num_heads.",
            "mask": "Causal mask ensures position i can only attend to positions j <= i.",
        },
        hints=[
            "Reshape Q to (B, S, H, d_k), then transpose to (B, H, S, d_k). Do the same for K and V.",
            "Compute scores = np.matmul(Q_trans, K_trans.transpose(0, 1, 3, 2)) / np.sqrt(d_k).",
            "If causal_mask: mask = np.triu(np.ones((S, S)), k=1).astype(bool); scores[:, :, mask] = -1e9.",
            "Apply softmax along axis=-1, matmul with V, transpose back to (B, S, H, d_k), and reshape to (B, S, D).",
        ],
    ),
    # -------------------------------------------------------------------------
    # ADDITIONAL ML SYSTEM DESIGN PROBLEMS
    # -------------------------------------------------------------------------
    QuestionItem(
        id="sys_06_autonomous_driving_perception",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Autonomous Vehicle Multi-Sensor 3D Perception & Trajectory Forecasting (30 FPS)",
        prompt=(
            "Design the real-time onboard perception and motion prediction system for an autonomous vehicle (L4 robotaxi). "
            "The vehicle processes 8 high-resolution cameras (1080p @ 30 FPS) and 2 roof LiDARs (100k points/sec) "
            "with an end-to-end inference budget under 35ms on dual automotive SOCs (e.g. NVIDIA DRIVE Orin). "
            "Cover: (1) LiDAR point cloud voxelization, (2) Camera Bird's Eye View (BEV) temporal feature fusion, "
            "(3) 3D bounding box detection and velocity estimation, (4) Multi-agent probabilistic trajectory forecasting, "
            "and (5) Sensor occlusion fail-safes and out-of-distribution (OOD) uncertainty estimation."
        ),
        difficulty="Senior / Staff",
        verbal_introduction=(
            "Autonomous vehicle perception is one of the most demanding edge AI domains. "
            "You have multi-modal camera streams and LiDAR point clouds operating under strict 35ms latency budgets. "
            "Walk me through your multi-sensor fusion architecture, BEV representation, and how you estimate future trajectory distributions."
        ),
        rubric_criteria=[
            "BEV temporal fusion representation (BEVFormer / Lift-Splat-Shoot) combining LiDAR depth and camera features",
            "LiDAR point-cloud preprocessing (PointPillars / Sparse 3D Convolutions) optimized for TensorRT",
            "Multi-task perception head: 3D bounding boxes, map segmentation, semantic lane graphs",
            "Multi-modal trajectory prediction with GNNs/Transformers (Wayformer / MotionNet) modeling road topology",
            "Safety-critical latency budgeting, ASIL-D fallback controllers, and runtime anomaly monitoring",
        ],
        clarifications={
            "sensors": "Assume 8 cameras, 2 128-beam LiDARs, and IMU/GNSS odometry.",
            "budget": "The onboard inference budget is strictly 35ms at 30Hz.",
        },
        hints=[
            "Structure your design into 4 phases: Sensor Ingestion -> BEV Fusion Backbone -> Perception Heads -> Trajectory Forecasting.",
            "Explain how camera perspective coordinates are projected to Bird's-Eye-View using learned depth distributions.",
            "Quantify compute budgets: INT8 quantization, TensorRT kernels, and pipelining across multiple accelerator engines.",
        ],
    ),
    QuestionItem(
        id="sys_07_generative_code_completion",
        category=QuestionCategory.ML_SYSTEM_DESIGN,
        title="Ultra-Low Latency (<15ms) IDE Code Completion with Speculative Decoding",
        prompt=(
            "Design the cloud and edge architecture for an AI code completion engine (similar to GitHub Copilot / Cursor) "
            "serving 500,000 active software engineers. "
            "The system must suggest multi-line completions in under 15ms p95 latency while developers are actively typing. "
            "Cover: (1) Cross-file repository context retrieval (Tree-sitter AST parsing + semantic chunking), "
            "(2) Fill-in-the-Middle (FIM) training and prompt structuring, (3) Speculative decoding using small draft models "
            "and continuous KV-cache prefix management, and (4) Client-side keystroke debouncing, cancellation tokens, and acceptance rate tracking."
        ),
        difficulty="Senior / Staff",
        verbal_introduction=(
            "Real-time code completion has extreme latency SLAs—anything over 20ms feels sluggish to a typing developer. "
            "How would you architect a system that retrieves repository context, manages KV caches across keystrokes, "
            "and uses speculative decoding to serve completions under 15ms?"
        ),
        rubric_criteria=[
            "Fill-in-the-Middle (FIM) prompt formatting (Prefix, Suffix, Middle)",
            "Speculative decoding architecture (fast 500M draft model validated by 7B target model)",
            "KV-cache prefix tree management (Radix tree caching for shared repo prefixes)",
            "Context retrieval using Tree-sitter AST symbols and locally indexed BM25/vector embeddings",
            "Client-side event loops: keystroke VAD, cancellation tokens via gRPC/WebSocket, and acceptance metrics",
        ],
        clarifications={
            "scale": "500k concurrent active typing sessions, global distribution.",
            "sla": "p95 time-to-first-token under 15ms from the IDE.",
        },
        hints=[
            "Divide the architecture into: IDE Extension -> Edge Routing -> KV-Cache/Context Engine -> Speculative Inference Cluster.",
            "Explain why naive autoregressive token-by-token generation is too slow and how draft models or n-gram caching solve it.",
            "Describe the Tree-sitter parsing layer to extract imported function signatures without shipping the entire repository on every keystroke.",
        ],
    ),
]


def get_all_questions() -> list[QuestionItem]:
    """Retrieve all available questions."""
    return QUESTIONS_BANK


def get_question_by_id(question_id: str) -> QuestionItem | None:
    """Find a question by ID."""
    for q in QUESTIONS_BANK:
        if q.id == question_id:
            return q
    return None


def get_questions_by_category(category: QuestionCategory) -> list[QuestionItem]:
    """Filter questions by category."""
    return [q for q in QUESTIONS_BANK if q.category == category]


def get_random_question(
    category: QuestionCategory | None = None,
    exclude_ids: list[str] | None = None,
) -> QuestionItem | None:
    """Select a randomized question from the bank with optional category filter and exclusions."""
    import random

    pool = QUESTIONS_BANK
    if category:
        pool = [q for q in pool if q.category == category]
    if exclude_ids:
        filtered = [q for q in pool if q.id not in exclude_ids]
        if filtered:
            pool = filtered
    return (
        random.choice(pool) if pool else (random.choice(QUESTIONS_BANK) if QUESTIONS_BANK else None)
    )
