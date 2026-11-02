# ai-interviewer — Privacy-First Multimodal Technical Interviewer

> **An open-source, local-first, Bring-Your-Own-Key (BYOK) technical interview preparation platform tailored for Senior Data Scientists, Machine Learning Engineers, and Applied Scientists targeting top tier product companies (Google, Meta, Stripe, Netflix).**

---

## 🌟 Key Architectural Highlights

- **Dual-Loop Multiplexer Architecture:**
  - **Fast Loop (Bidirectional Audio/Visual WebSocket):** Powered by the **Gemini Multimodal Live API** (`google-genai` SDK) streaming 16kHz PCM microphone audio in, receiving 24kHz PCM synthesized speech out, debounced code snapshots, and whiteboard diagrams.
  - **Slow Loop (Async Shadow Supervisor):** Runs asynchronously in the background using `gemini-2.5-pro`. Detects shallow mathematical claims, $O(N^2)$ loops, or missing `PARTITION BY` clauses, dynamically injecting silent directives into the live voice agent.
- **Client-Side WebAssembly Execution Engine (Zero-Server Compute):**
  - **Python (Pyodide WASM):** Executes Python data manipulation and algorithmic code directly in the browser with unit test assertions.
  - **SQL (DuckDB-WASM):** In-browser SQL analytical engine pre-seeded with realistic product tables: `users`, `events`, `transactions`, `model_predictions`.
- **Deterministic Finite State Machine (FSM) & Rolling Context Compaction:**
  - Manages stage transitions: `INTRO (2m) -> RESUME_DEEP_DIVE (10m) -> LIVE_CODING_SQL_PYTHON (12m) -> ML_SYSTEM_DESIGN (10m) -> WRAP_UP (2m)`.
  - Performs rolling compaction between stages to maintain bounded $O(1)$ context windows and ultra-low latency.
- **Strict Local-First Privacy & BYOK:**
  - Resumes, webcam streams, audio recordings, transcripts, and evaluation scorecards stay 100% local (SQLite + Browser Storage).
  - Webcams are rendered client-side only (`navigator.mediaDevices.getUserMedia`) for Zoom/Meet camera exposure desensitization without streaming face video to external servers.
- **Anti-Sycophant "Bar-Raiser" Persona:**
  - Zero sycophantic praise ("Great answer!", "Awesome!"). Probes 3 layers deep into data leakage, class imbalance, p99 latency SLAs, concept drift, and offline-to-online metric alignment.
- **Constructive Mentor Post-Interview BARS Evaluator:**
  - Once the call ends, grades transcripts across Behaviorally Anchored Rating Scales (1–5) and crafts gold-standard 60-second STAR rewrites for every question.

---

## 📐 System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                 CLIENT BROWSER                                    |
|                                                                                   |
|  [Local Camera Mirror]        [Audio Recorder 16kHz]     [Audio Queue 24kHz]      |
|  (Zero remote video)          (Web Audio ScriptProc)     (AnalyserNode Halo)      |
|                                         │                         ▲               |
|  [Monaco IDE]                 [Excalidraw Whiteboard]             │               |
|  • Pyodide WASM (Python)      • Debounced JPEG snapshot           │               |
|  • DuckDB-WASM (SQL)          • Dynamic VAD Gate Hold             │               |
+─────────────────────────────────────────┼─────────────────────────┼───────────────+
                                          │ WebSocket               │
                                          ▼                         │
+───────────────────────────────────────────────────────────────────┼───────────────+
|                           FASTAPI BACKEND SERVICE                 │               |
|                                                                   │               |
|  [Fast Loop: Gemini Live Multiplexer] ────────────────────────────┘               |
|   • 16kHz PCM In / 24kHz PCM Out (client.aio.live.connect)                        |
|   • Code diffs + JPEG canvas frames                                               |
|   • Keystroke-Aware VAD Suppression                                               |
|                                                                                   |
|  [Deterministic FSM Orchestrator]                                                 |
|   • INTRO -> RESUME_DEEP_DIVE -> LIVE_CODING -> ML_SYSTEM_DESIGN -> WRAP_UP       |
|   • Rolling Context Compaction: Bounded O(1) LLM memory                           |
|                                                                                   |
|  [Slow Loop: Async Shadow Supervisor]                                             |
|   • Background depth checker: Injects silent interviewer follow-up probes         |
|                                                                                   |
|  [Curated 21-Problem Bank with In-Session Switching]                               |
|   • 7 DuckDB SQL Window/Cohort Problems                                           |
|   • 7 Python Algorithmic Problems with Unit Tests                                 |
|   • 7 ML System Design Prompts with Detailed Rubrics                              |
|                                                                                   |
|  [Local SQLite Database]                                                          |
|   • Sessions, Transcripts, and BARS Scorecards                                    |
+───────────────────────────────────────────────────────────────────────────────────+
```

---

## 📂 Project Structure

```text
ai-interviewer/
├── backend/
│   ├── app/
│   │   ├── config.py                 # Pydantic Settings (models, sample rates, DB)
│   │   ├── database.py               # Local SQLite engine & SQLAlchemy models
│   │   ├── schemas.py                # Pydantic models (ClaimGraph, FSMState, BARSReport)
│   │   ├── services/
│   │   │   ├── resume_parser.py      # PyMuPDF extraction + structured ClaimGraph
│   │   │   ├── fsm_orchestrator.py   # Deterministic FSM & rolling context compaction
│   │   │   ├── gemini_live.py        # Fast Loop: Gemini Multimodal Live multiplexer
│   │   │   ├── shadow_supervisor.py  # Slow Loop: Async depth checker & probe injector
│   │   │   ├── rubric_evaluator.py   # Post-interview BARS grader & STAR rewriter
│   │   │   └── question_bank.py      # 21 Curated DS/ML problems with DuckDB seeds
│   │   ├── prompts/
│   │   │   ├── interviewer_system.py # Anti-sycophantic Bar-Raiser system prompt
│   │   │   ├── supervisor_system.py  # Shadow evaluator instructions
│   │   │   └── grader_system.py      # Constructive mentor & BARS rubric prompt
│   │   └── main.py                   # FastAPI application, CORS, REST & WS endpoints
│   ├── tests/                        # 24 Pytest integration & unit tests
│   ├── pyproject.toml                # Ruff & Pytest configuration
│   ├── requirements.txt              # Production Python dependencies
│   └── Dockerfile                    # Multi-stage backend container
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Onboarding dashboard & resume upload
│   │   │   ├── interview/[id]/page.tsx # Split-screen Zoom-style interview room
│   │   │   └── report/[id]/page.tsx  # Post-interview BARS scorecard & STAR rewrites
│   │   ├── components/
│   │   │   ├── InterviewerAvatar.tsx # 2D Portrait + Web Audio glowing halo
│   │   │   ├── CandidateWebcam.tsx   # Local-only mirror tile + gaze/presence timer
│   │   │   ├── CodeSandbox.tsx       # Monaco Editor + Pyodide + DuckDB-WASM
│   │   │   ├── SystemDesignCanvas.tsx # Whiteboard canvas + debounced snapshot emitter
│   │   │   └── ScorecardView.tsx     # BARS dimension cards, diffs & STAR rewrites
│   │   └── lib/
│   │       ├── audioStream.ts        # 16kHz PCM capture & 24kHz playback queue
│   │       ├── pyodideRunner.ts      # Browser WebAssembly Python execution
│   │       └── duckdbRunner.ts       # Browser WebAssembly DuckDB SQL engine
│   ├── package.json
│   └── Dockerfile                    # Multi-stage Next.js container
├── .github/workflows/
│   └── ci.yml                        # GitHub Actions CI (Ruff, Pytest, Next.js build)
├── docker-compose.yml                # Full-stack Docker deployment
└── README.md
```

---

## 🤖 AI, LLM & Machine Learning Architecture

The platform combines a **Dual-Loop Multiplexer Architecture** with client-side WebAssembly compute to balance real-time, conversational voice responsiveness (<600ms) with deep, asynchronous technical supervision and evaluation.

### Architecture Topology & Execution Loops

```text
                                  +─────────────────────────────────────────+
                                  |         Candidate Browser Audio         |
                                  |         16kHz PCM Linear Stream         |
                                  +────────────────────┬────────────────────+
                                                       │ WebSocket
                                                       ▼
                                  +─────────────────────────────────────────+
                                  |         FAST-LOOP REAL-TIME AGENT       |
                                  |          (Gemini 2.0 Flash Live)        |
                                  |  • Voice response latency: <600ms       |
                                  |  • Anti-sycophantic Bar-Raiser persona  |
                                  |  • Ingests Monaco code & Excalidraw     |
                                  +────────────────────┬────────────────────+
                                                       │
                                   Transcripts & Diffs │ Background Ingestion
                                                       ▼
+───────────────────────────────────+     +─────────────────────────────────────────+
|     LOCAL WEBASSEMBLY ENGINES     |     |       SLOW-LOOP SHADOW SUPERVISOR       |
|                                   |     |            (Gemini 2.5 Pro)             |
| • DuckDB-WASM: In-browser SQL     |     | • Async evaluation every 3 turns        |
| • Pyodide WASM: CPython + NumPy   |     | • Detects shallow math & O(N²) loops    |
| • Web Audio: FFT Voice Halo       |     | • Injects silent interviewer probes     |
+───────────────────────────────────+     +────────────────────┬────────────────────+
                                                               │
                                               Session Summary │ Call Completed
                                                               ▼
                                          +─────────────────────────────────────────+
                                          |       POST-INTERVIEW BARS GRADER        |
                                          |        (Gemini 2.5 Pro / Flash)         |
                                          | • 4-Dimension BARS Rubric (1-5)         |
                                          | • Strengths, Weaknesses, Verdict        |
                                          | • Staff-Level 60-Sec STAR Rewrites      |
                                          +─────────────────────────────────────────+
```

### Comprehensive AI & ML Model Matrix

| Component | Model / Engine | Modality & Flow | Latency SLA / Cadence | Implementation Source |
| :--- | :--- | :--- | :--- | :--- |
| **Fast-Loop Voice Agent** | `gemini-2.0-flash-exp` *(Gemini Live API)* | Bidirectional 16kHz PCM Audio In / 24kHz PCM Audio Out, Code Diffs, Canvas Frames | Sub-second (~300–600ms) | [`gemini_live.py`](file:///home/deepak/ai-interviewer/backend/app/services/gemini_live.py) |
| **Resume Claim Extractor** | `gemini-2.5-flash` (`EXTRACTOR_MODEL`) | PDF text $\rightarrow$ Strict Pydantic JSON `CandidateClaimGraph` | One-shot on upload (~2s) | [`resume_parser.py`](file:///home/deepak/ai-interviewer/backend/app/services/resume_parser.py) |
| **Conversational Bar-Raiser** | `gemini-2.5-flash` + Deterministic Fallback | Anti-sycophantic dialogue, hints, schema clarifications, real-time code reviews | Spoken turn cadence (~1s) | [`interviewer_engine.py`](file:///home/deepak/ai-interviewer/backend/app/services/interviewer_engine.py) |
| **Shadow Supervisor** | `gemini-2.5-pro` (`SUPERVISOR_MODEL`) | Asynchronous background semantic depth checker & silent probe injector | Every 3 turns or on code run | [`shadow_supervisor.py`](file:///home/deepak/ai-interviewer/backend/app/services/shadow_supervisor.py) |
| **BARS Rubric Grader** | `gemini-2.5-flash` / `gemini-2.5-pro` (`REASONING_MODEL`) | Complete transcript & code audit $\rightarrow$ 4 BARS dimensions & Staff STAR rewrites | End of interview (~5–8s) | [`rubric_evaluator.py`](file:///home/deepak/ai-interviewer/backend/app/services/rubric_evaluator.py) |
| **In-Browser SQL Engine** | `DuckDB-WASM` | Relational OLAP query execution on pre-seeded memory tables | Local instant (<50ms) | [`duckdbRunner.ts`](file:///home/deepak/ai-interviewer/frontend/src/lib/duckdbRunner.ts) |
| **In-Browser Python Engine** | `Pyodide WASM` + NumPy | CPython code execution against automated unit test assertion suites | Local fast (<200ms) | [`pyodideRunner.ts`](file:///home/deepak/ai-interviewer/frontend/src/lib/pyodideRunner.ts) |
| **Deterministic Audio Halo** | Web Speech API + Web Audio `AnalyserNode` | Persona voice synthesis fallback + 60fps real-time audio FFT frequency halo | Local continuous (60fps) | [`voiceManager.ts`](file:///home/deepak/ai-interviewer/frontend/src/lib/voiceManager.ts) |

---

### Detailed Subsystem Breakdown

#### 1. Fast-Loop Gemini Multimodal Live Voice Agent (`gemini-2.0-flash-exp`)
- **WebSocket Protocol**: Connects via `client.aio.live.connect` using bidirectional audio streaming.
- **Audio Processing Pipeline**: 
  - *Microphone Ingestion*: Captured at 16kHz PCM mono via the browser `ScriptProcessorNode` / `AudioWorklet` and streamed in 512-sample chunks.
  - *Speech Synthesis Out*: Emits raw 24kHz linear PCM audio directly from the model, pushed into a client-side streaming jitter buffer queue (`AudioQueue`) for smooth playback.
- **Multimodal Visual Inputs**: Receives debounced code diffs from the Monaco Editor and JPEG snapshots of the Excalidraw whiteboard canvas every 5 seconds.
- **Keystroke-Aware VAD Suppression**: Dynamic Voice Activity Detection suppresses AI interruptions while the candidate is actively typing code or drawing architecture diagrams.
- **Location**: [`backend/app/services/gemini_live.py`](file:///home/deepak/ai-interviewer/backend/app/services/gemini_live.py), [`frontend/src/lib/audioStream.ts`](file:///home/deepak/ai-interviewer/frontend/src/lib/audioStream.ts)

#### 2. Candidate Resume Claim Graph Extractor (`gemini-2.5-flash`)
- **Extraction Pipeline**: Reads candidate PDF resumes locally via PyMuPDF (`fitz`), eliminating cloud document upload leakage.
- **Structured Pydantic Output**: Feeds raw text to `gemini-2.5-flash` with a strict JSON schema returning `CandidateClaimGraph`:
  - **Identified Claims**: Project titles, target metrics, baseline models, production constraints.
  - **3-Layer Probing Vectors**:
    1. *Mathematical Foundations*: Loss functions, regularization, gradient clipping, sample weightings.
    2. *Production Constraints*: P99 latency budgets, memory limits, QPS bottlenecks, feature store consistency.
    3. *Offline vs. Online Divergence*: Feedback delays, position bias, covariate drift, survivorship bias.
- **Location**: [`backend/app/services/resume_parser.py`](file:///home/deepak/ai-interviewer/backend/app/services/resume_parser.py), [`backend/app/schemas.py`](file:///home/deepak/ai-interviewer/backend/app/schemas.py)

#### 3. Conversational Bar-Raiser Engine (`gemini-2.5-flash` + Local Semantic Fallback)
- **Anti-Sycophantic Persona**: Formulated via [`interviewer_system.py`](file:///home/deepak/ai-interviewer/backend/app/prompts/interviewer_system.py). Emulates a Google/Meta L6+ Staff Applied Scientist interviewer.
- **Key Behavioral Rules**:
  - Eliminates sycophantic conversational filler ("Awesome!", "Great answer!").
  - Immediately jumps into technical evaluation, probing edge cases, mathematical formulation, and trade-offs.
  - Contextually answers candidate clarifying questions regarding database schema, nullability, SLA boundaries, and data distribution using active question metadata.
  - Delivers graduated hints without prematurely revealing canonical answers.
  - Reviews live code execution outputs and test failures, providing Socratic guidance.
- **Graceful Offline Mode**: Includes a local deterministic fallback engine that synthesizes human-like spoken prompts and reviews code even when running zero-key offline.
- **Location**: [`backend/app/services/interviewer_engine.py`](file:///home/deepak/ai-interviewer/backend/app/services/interviewer_engine.py)

#### 4. Slow-Loop Async Shadow Supervisor (`gemini-2.5-pro`)
- **Asynchronous Execution**: Operates out-of-band in a background thread every 3 candidate conversational turns or immediately upon code execution.
- **Audit Objectives**:
  - Detects superficial hand-waving or ungrounded claims (e.g. reciting high-level buzzwords without specifying loss formulations or feature engineering).
  - Detects algorithmic inefficiencies (e.g. nested $O(N^2)$ loops, full-table scans, unindexed joins, missing `PARTITION BY` clauses).
  - Evaluates whiteboard architectural bottlenecks (e.g. single points of failure, unbuffered Kafka topics, embedding latency spikes).
- **Silent Probe Injection**: When an issue is detected, the supervisor synthesizes a concise, pointed question and injects it into the live interviewer's context window as an internal directive for the next conversational turn.
- **Location**: [`backend/app/services/shadow_supervisor.py`](file:///home/deepak/ai-interviewer/backend/app/services/shadow_supervisor.py), [`backend/app/prompts/supervisor_system.py`](file:///home/deepak/ai-interviewer/backend/app/prompts/supervisor_system.py)

#### 5. Post-Interview BARS Grader & Staff STAR Rewriter (`gemini-2.5-flash` / `gemini-2.5-pro`)
- **Evaluation Criteria**: Analyzes the complete interview transcript, executed code, test results, and whiteboard canvas against 4 Behaviorally Anchored Rating Scale (BARS) dimensions (1–5 scale):
  1. *Coding & Algorithmic Rigor* (syntax, complexity, modularity, edge cases)
  2. *System Design & Scalability* (component decoupling, latency SLAs, backpressure, failure modes)
  3. *Communication & Structured Thinking* (clarification asking, active signposting, conciseness)
  4. *Domain Depth & Technical Truth* (mathematical understanding, metric alignment, production realities)
- **Hiring Manager Output**: Generates an overall hiring recommendation (`CLEAR HIRE`, `INCLINE HIRE`, `WEAK LEAN`, `NO HIRE`), bulleted strengths, bulleted improvement areas, and a synthesized hiring manager summary.
- **60-Second Staff-Level STAR Rewrites**: For every substantive question asked, rewrites candidate answers into how a Staff/Principal Engineer would present the same project in under 60 seconds (Situation, Task, Action, Result) with precise mathematical trade-offs.
- **Location**: [`backend/app/services/rubric_evaluator.py`](file:///home/deepak/ai-interviewer/backend/app/services/rubric_evaluator.py), [`backend/app/prompts/grader_system.py`](file:///home/deepak/ai-interviewer/backend/app/prompts/grader_system.py)

---

## 📚 Question Bank & Sandboxed WebAssembly Execution Engine

### Why a Question Bank Exists (Live AI vs. Grounded Execution)

A frequent question in AI-driven technical interviewing is: **"Why do we need a question bank if the AI can conduct live discussions and evaluations dynamically?"**

The answer lies in the fundamental difference between **conversational reasoning** and **sandboxed technical execution**:

1. **Deterministic Execution vs. Hallucinated Schemas**: In a real technical coding interview, candidates must write code that actually runs against real tables and passes automated unit tests. While an LLM can generate question text, generating reproducible database schemas, populated relational tables (`seed_sql`), and executable unit test assertions on the fly is prone to syntax errors, non-deterministic schemas, and schema-query mismatches.
2. **True In-Browser Zero-Server Execution**: Our platform executes SQL queries in **DuckDB-WASM** and Python algorithms in **Pyodide WASM** directly inside the user's browser. This requires pre-compiled, valid seed data and assertable test cases that run instantaneously without spinning up costly remote containers.
3. **Calibrated FAANG Bar-Raiser Rubrics**: Real senior interviewers grade against standardized, calibrated rubrics (e.g. handling skewed partitions, window frames, time-travel joins, p99 latency trade-offs). Pre-calibrated rubric criteria ensure scoring is objectively consistent across candidates rather than drifting with LLM randomness.
4. **Organic Spoken Interaction Built on Top**: The question bank provides the **technical ground truth** (schema, tests, rubrics), while the **AI interviewer delivers the organic, human-like experience**:
   - Spoken verbal introductions tailored to candidate background.
   - Dynamic clarification answers when candidates ask about nulls, duplicate keys, or SLAs.
   - Contextual, non-spoiler hints when a candidate gets stuck.
   - Socratic follow-up probes challenging edge cases or algorithmic complexity.

---

### Dynamic Randomization & Practice Variety System

To ensure candidates practicing over multiple weeks never experience repetitive lock-in, the platform features a multi-tiered variety system:

- **Dynamic Stage Assignment**: When entering `LIVE_CODING_SQL_PYTHON` or `ML_SYSTEM_DESIGN`, the FSM orchestrator dynamically selects a randomized, uncompleted question from the bank if one was not manually chosen.
- **Pre-Interview Focus Selector**: On the onboarding dashboard (`/`), candidates can explicitly choose their practice domain or problem (e.g. *Cohort Retention Analysis*, *Leaky Bucket Rate Limiter*, *Real-Time Fraud Detection Feature Store*), or leave it set to "Auto-Select Fresh Problem".
- **In-Interview "Next Problem" Switcher**: The interactive workbench header features a **"Next Problem"** button allowing candidates to switch to a fresh problem at any time without exiting the session or losing their interview transcript.
- **Zero-Lockout Extensibility**: Adding a new problem to `question_bank.py` automatically registers it across all REST endpoints, the frontend picker, and the FSM orchestrator with zero database migrations.

---

### Complete Question Bank Integration Map

The Question Bank is integrated end-to-end across both backend services and frontend UI components:

```text
                               +──────────────────────────────────────────────────+
                               |     backend/app/services/question_bank.py        |
                               |  • 21 Curated Problems (7 SQL, 7 Py, 7 System)   |
                               |  • Schema, Seeds, Tests, Rubrics, Hints          |
                               +─────────────────────────┬────────────────────────+
                                                         │
               ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
               ▼                                         ▼                                         ▼
+──────────────────────────────+          +──────────────────────────────+          +──────────────────────────────+
|   fsm_orchestrator.py        |          |   interviewer_engine.py      |          |       gemini_live.py         |
| • Dynamic random selection   |          | • Verbal introductions       |          | • Injects problem context    |
| • Prevents problem lock-in   |          | • Schema clarifications      |          | • Emits fsm_snapshot via WS  |
| • Assigns active problem     |          | • Progressive hints          |          | • Syncs state with client    |
+──────────────┬───────────────+          +──────────────┬───────────────+          +──────────────┬───────────────+
               │                                         │                                         │
               └─────────────────────────────────────────┼─────────────────────────────────────────┘
                                                         │
                                                         ▼
                                          +──────────────────────────────+
                                          |         FastAPI REST         |
                                          | • GET /api/questions         |
                                          | • POST /api/session/init     |
                                          | • POST /.../switch_question  |
                                          +──────────────┬───────────────+
                                                         │
               ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
               ▼                                         ▼                                         ▼
+──────────────────────────────+          +──────────────────────────────+          +──────────────────────────────+
|       frontend/page.tsx      |          |   interview/[id]/page.tsx    |          |       CodeSandbox.tsx        |
| • Practice focus dropdown    |          | • "Next Problem" switcher    |          | • DuckDB-WASM seed tables    |
| • Category-grouped picker    |          | • Active problem badge       |          | • Pyodide WASM unit tests    |
| • Dynamic problem metadata   |          | • Schema reference drawer    |          | • Monaco starter code        |
+──────────────────────────────+          +──────────────────────────────+          +──────────────────────────────+
```

1. **Definition & Dataclass Schema ([`question_bank.py`](file:///home/deepak/ai-interviewer/backend/app/services/question_bank.py))**:
   - Contains 21 curated problems structured under the `Question` dataclass: `id`, `title`, `category`, `difficulty`, `scenario`, `verbal_introduction`, `starter_code`, `seed_sql`, `unit_tests`, `rubric_criteria`, `clarifications`, and `hints`.
2. **Deterministic Stage Assignment ([`fsm_orchestrator.py`](file:///home/deepak/ai-interviewer/backend/app/services/fsm_orchestrator.py))**:
   - Dynamically selects randomized problems via `get_random_question()` upon entering `LIVE_CODING_SQL_PYTHON` and `ML_SYSTEM_DESIGN` stages.
3. **Conversational Engine & Dynamic Guidance ([`interviewer_engine.py`](file:///home/deepak/ai-interviewer/backend/app/services/interviewer_engine.py))**:
   - Converts `verbal_introduction` into human-like spoken prompts.
   - Uses `question.clarifications` to answer candidate inquiries regarding schema types, null values, and constraints.
   - Uses `question.hints` to provide progressive, Socratic assistance.
4. **WebSocket State Synchronization ([`gemini_live.py`](file:///home/deepak/ai-interviewer/backend/app/services/gemini_live.py))**:
   - Injects active problem context into Gemini Live's system instructions and sends `fsm_snapshot` containing `active_question` to the frontend.
5. **REST API Endpoints ([`main.py`](file:///home/deepak/ai-interviewer/backend/app/main.py))**:
   - `GET /api/questions`: Lists all 21 problems grouped by category.
   - `POST /api/session/init`: Initializes interview sessions with candidate-specified `question_id`.
   - `POST /api/session/{session_id}/switch_question`: Dynamically switches problems mid-session.
6. **Candidate Onboarding Dashboard ([`page.tsx`](file:///home/deepak/ai-interviewer/frontend/src/app/page.tsx))**:
   - Interactive dropdown allowing candidates to target specific questions or practice areas.
7. **Interview Workbench & Problem Switcher ([`interview/[id]/page.tsx`](file:///home/deepak/ai-interviewer/frontend/src/app/interview/[id]/page.tsx))**:
   - Real-time navigation bar with problem badges and a "Next Problem" button to switch questions seamlessly.
8. **Client-Side Monaco CodeSandbox ([`CodeSandbox.tsx`](file:///home/deepak/ai-interviewer/frontend/src/components/CodeSandbox.tsx))**:
   - Injects `starter_code` into Monaco Editor.
   - Executes `seed_sql` in DuckDB-WASM, creating real relational tables and an interactive schema drawer.
   - Executes Python code with `unit_tests` in Pyodide WASM, reporting passing/failing test assertions.
9. **Interactive Whiteboard Canvas ([`SystemDesignCanvas.tsx`](file:///home/deepak/ai-interviewer/frontend/src/components/SystemDesignCanvas.tsx))**:
   - Displays real-world system design scenarios, scale constraints (QPS, storage, latency), and debounces snapshots for the live interviewer.
10. **Post-Interview BARS Scorecard ([`ScorecardView.tsx`](file:///home/deepak/ai-interviewer/frontend/src/components/ScorecardView.tsx) & [`report/[id]/page.tsx`](file:///home/deepak/ai-interviewer/frontend/src/app/report/[id]/page.tsx))**:
    - Benchmarks candidate code and whiteboard architecture against the canonical `rubric_criteria`.

---

### Complete 21-Problem Catalog

#### Category 1: SQL Analytical & Window Function Problems (DuckDB-WASM)

| ID | Problem Title | Difficulty | Key Concepts & Analytical Focus |
| :--- | :--- | :--- | :--- |
| `sql_01_retention_cohort` | Monthly User Retention & Cohort Analysis | Medium | Self-joins, `DATE_TRUNC`, cohort grouping, churn tracking |
| `sql_02_rolling_metrics` | Rolling 7-Day Revenue & Anomaly Outliers | Medium | `SUM() OVER (RANGE/ROWS BETWEEN)`, window frames, standard deviation z-score filtering |
| `sql_03_funnel_conversion` | Multi-Touch Funnel Conversion Rates | Hard | Sequential session tracking, `LAG()` / `LEAD()`, drop-off percentage calculations |
| `sql_04_sessionization` | User Activity Sessionization & Inactivity Spans | Hard | Time-gap thresholding, cumulative flags, session grouping |
| `sql_05_surge_pricing` | Dynamic Surge Pricing Multiplier Windows | Hard | Temporal range joins, dense ranking, demand/supply ratio windows |
| `sql_06_point_in_time_features` | Point-in-Time Feature Store Temporal Joins | Hard | Data leakage prevention, `AS OF` temporal join logic, feature snapshotting |
| `sql_07_experiment_cuped` | A/B Testing Variance Reduction (CUPED) | Hard | Pre-experiment covariate adjustment, variance reduction calculation, OLS slope estimator |

#### Category 2: Python Algorithmic & Vectorized Problems (Pyodide WASM)

| ID | Problem Title | Difficulty | Key Concepts & Algorithmic Focus |
| :--- | :--- | :--- | :--- |
| `py_01_vector_similarity` | Top-K Cosine Similarity & Vector Search | Medium | NumPy vectorization, matrix dot products, heap-based Top-K selection |
| `py_02_gradient_descent` | Logistic Regression SGD from Scratch | Medium | Sigmoid activation, cross-entropy loss, gradient calculation, L2 regularization |
| `py_03_decision_tree_split` | Best Split Feature Selector (Gini Impurity) | Hard | Gini impurity calculation, multi-feature sweep, threshold optimization |
| `py_04_kmeans_clustering` | K-Means Clustering & Centroid Assignment | Medium | Vectorized Euclidean distance, Voronoi partition update, Lloyd's algorithm |
| `py_05_leaky_bucket` | Token Bucket / Leaky Bucket Rate Limiter | Hard | Thread-safe token consumption, replenishment calculation, burst capacity |
| `py_06_reservoir_sampling` | Streaming Reservoir Sampling (Algorithm R) | Medium | Single-pass random sampling, uniform probability distribution over unbounded streams |
| `py_07_trie_autocomplete` | Prefix Trie with Frequency Ranking | Hard | Tree traversal, prefix matching, frequency-ordered priority queue suggestions |

#### Category 3: Machine Learning System Design Problems (Excalidraw Whiteboard)

| ID | Problem Title | Difficulty | Key Architectural & Scaling Challenges |
| :--- | :--- | :--- | :--- |
| `sys_01_realtime_fraud` | Real-Time Payment Fraud Detection Engine | Hard | Sub-50ms p99 SLA, extreme class imbalance, low-latency Redis feature store |
| `sys_02_recsys_two_stage` | Two-Stage E-Commerce Video Recommender | Hard | 100M item corpus, Two-Tower ANN retrieval (HNSW), heavy GBDT/DLRM ranker |
| `sys_03_search_embeddings` | Semantic Search & Multimodal Vector Store | Hard | Multimodal encoders (CLIP), vector indexing (IVF-PQ/HNSW), hybrid keyword search |
| `sys_04_ab_testing_platform` | Enterprise A/B Testing & Feature Flagging | Hard | Consistent SHA-256 hashing, sample ratio mismatch (SRM) detection, sequential testing |
| `sys_05_llm_rag_pipeline` | Enterprise Hybrid RAG System | Hard | Chunking strategies, dense+BM25 hybrid retrieval, cross-encoder re-ranking, hallu-guardrails |
| `sys_06_autonomous_ride_dispatch` | Real-Time Ride Matching & Dynamic Pricing | Hard | Spatio-temporal indexing (H3/S2 cells), bipartite graph matching, supply-demand forecasting |
| `sys_07_ad_click_prediction` | High-Throughput Ad CTR Prediction (DLRM) | Hard | 100k QPS, terabyte-scale sparse embedding tables, continuous online training |

---

## 🚀 Quickstart

### Prerequisites & Authentication Options

- **Python 3.11+**
- **Node.js 20+**
- **Authentication Options**:
  - **Option 1: Zero-Key Local Mode (No API Key Required)**
    - You can run the entire platform without any API key or Google Cloud account.
    - Python execution (Pyodide WASM), SQL queries (DuckDB-WASM), local webcam mirror, drawing canvas, stage progression, and deterministic BARS evaluations run 100% in your browser and local SQLite with zero setup.
  - **Option 2: Google AI Studio API Key (Recommended for Live Voice)**
    - For real-time bidirectional voice conversation with Gemini Multimodal Live, obtain a free API key at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** (takes 10 seconds, zero billing setup).
    - Provide it either via the UI setup screen (stored only in browser `sessionStorage`) or in your `.env` file as `GEMINI_API_KEY`.
  - **Option 3: Google Cloud Application Default Credentials (ADC / Vertex AI)**
    - If you authenticated using `gcloud auth application-default login`, the unified `google-genai` SDK can communicate with Vertex AI.
    - Note that Vertex AI requires an active Google Cloud project with billing and the Vertex AI API (`aiplatform.googleapis.com`) enabled. The live bidirectional voice WebSocket stream is natively supported out of the box via Google AI Studio keys.

### 💰 API Pricing, Rate Limits & Costs (2026 Reference)

The platform supports both **100% Free** usage and **Pay-As-You-Go** tiers:

#### 1. Free Tier (Google AI Studio) — $0 Cost
- **Cost**: **$0.00** (no credit card or billing account required).
- **Available Models**: Gemini 2.5 Flash, Gemini 2.0 Flash, Gemini 1.5 Flash.
- **Quotas & Rate Limits**:
  - **15 RPM** (Requests Per Minute)
  - **1,000,000 TPM** (Tokens Per Minute)
  - **1,500 RPD** (Requests Per Day — resets daily at midnight PT)
- **Data Policy Note**: On the free tier, Google may log inputs/outputs to train and improve models. (For 100% private zero-logging, see Pay-As-You-Go below).
- **Adequacy**: 1,500 requests per day is more than enough to conduct **5 to 10 full 45-minute technical interviews daily completely free of charge**.

#### 2. Pay-As-You-Go Tier (Google AI Studio / Vertex AI)
If you link a billing account or use enterprise GCP credentials:
- **Zero Training Guarantee**: Inputs and outputs are strictly private and **never** used for model training.
- **Model Token Pricing**:
  | Modality / Model | Input Cost | Output Cost | Approx. Real-Time Cost |
  | :--- | :--- | :--- | :--- |
  | **Gemini Flash (Text/Code)** | $0.075 / 1M tokens | $0.30 / 1M tokens | — |
  | **Gemini Pro (BARS Grader)** | $1.25 / 1M tokens | $5.00 / 1M tokens | — |
  | **Multimodal Live Audio (Flash)** | $3.00 / 1M tokens | $12.00 / 1M tokens | ~$0.005 / min (in) <br> ~$0.018 / min (out) |

- **Real-World Session Cost**:
  - Live 25-minute voice interaction (~25 tokens/sec audio): **~$0.18 – $0.35**
  - Full BARS rubric evaluation report (Gemini Pro reasoning): **~$0.04 – $0.08**
  - **Total estimated cost per complete mock interview: ~$0.25 to $0.45.**

#### 3. Zero-Key Local Mode — $0 Cost & 100% Private
- If no API key is provided, the platform automatically switches to **local simulation mode**.
- Uses client-side WebAssembly (DuckDB-WASM + Pyodide) and local PyMuPDF extraction.
- **Cost: Exactly $0.00 forever**, with zero network calls and complete offline privacy.

---

### Method A: Local Development

#### 1. Start Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000` (docs at `http://localhost:8000/docs`).

#### 2. Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run Next.js dev server
npm run dev
```
Open `http://localhost:3000` in your browser.

---

### Method B: Docker Compose

```bash
# Export your Gemini API key (or enter it in the browser UI)
export GEMINI_API_KEY="your-gemini-api-key"

docker compose up --build
```

- Frontend: `http://localhost:3001` (or `http://localhost:3000` via `FRONTEND_PORT=3000`)
- Backend API: `http://localhost:8000`

> **Note on Port Allocation:** The Docker frontend defaults to port `3001` (`3001:3000`) to avoid collisions with other host services (like Grafana). You can customize it by setting `FRONTEND_PORT=3000` if port 3000 is free.

## 🤖 2026 Agentic Architecture & Behavioral Flow

The interviewer is engineered with a multi-turn, stateful **Agentic Interviewer** (`AgenticInterviewer`) designed to replicate the spontaneous, conversational rigor of top human technical interviewers:

```
[Candidate Action / Voice / Code]
               │
               ▼
┌──────────────────────────────────────────────┐
│       Acoustic Echo Guard & Barge-In         │
│ • Discards mic self-echo while speaking      │
│ • Instant speech cancellation on barge-in    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│         Agentic Interviewer Engine           │
│ • Dynamic persona self-introduction          │
│ • Trajectory-aware probing & follow-ups      │
│ • Track-specialized prompts (Breadth/Depth)  │
│ • Human-like silence & patience monitoring   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Gemini 2.5 Live + Google Search Grounding   │
│ • Real-time 2025/2026 interview questions    │
│ • Native types.GoogleSearch() (No 3rd-party) │
│ • Dual fallback for Indian tech & AI startups│
└──────────────────────────────────────────────┘
```

### 1. Dynamic Human Self-Introduction
Rather than jumping abruptly into static problem statements, the interviewer introduces themselves dynamically with their name, role, and engineering team at the target company (e.g., *"Hi, I'm Maya from the ML Platform team at Swiggy. Today we'll do an ML Breadth sprint focused on ranking metrics, loss functions, and latency optimizations."*), sets clear expectations, and warmly opens the floor for introductions.

### 2. Instant Barge-In / Interruption
Candidates are not held hostage by a pre-recorded monologue. Candidates can **interrupt at any moment** by speaking, typing, or clicking the **Cut In / Speak** button. The interviewer immediately halts speech synthesis, stops audio chunk playback, and listens attentively.

### 3. Acoustic Self-Echo Guard
Speech recognition incorporates an intelligent 1000ms acoustic guard window. Audio received from the microphone while the interviewer is speaking is discarded, completely eliminating the robotic infinite self-echo loop.

### 4. Attentive Silence & Patience Detection
If a candidate pauses for 25–45 seconds to think through a derivation or system architecture, the interviewer does not blabber or prematurely interrupt. A comforting reassurance banner appears (*"Take your time to structure your thoughts, or speak up whenever you're ready"*), with one-click access to hints or constraint clarifications.

---

## 🧠 Comprehensive Map of ML, LLM & AI Models Used Across the Platform

Every AI/ML component is purposefully separated by latency budget and reasoning requirements:

| Model / Technology | Component File | Role & Architectural Purpose | Mode / Input Modality |
| :--- | :--- | :--- | :--- |
| **`gemini-2.5-pro`** (`INTERVIEWER_MODEL`) | `backend/app/services/agentic_interviewer.py` | **Persistent Multi-Turn Dialogue Agent:** Uses Google GenAI native chat session (`client.aio.chats.create`). Retains full conversational memory across turns, enforces strict zero-sycophancy rules, directly acknowledges candidate answers before asking follow-ups, and handles context-aware silence nudges and code feedback. | Multi-turn async chat session |
| **`gemini-2.5-flash-native-audio-preview`** (`LIVE_MODEL`) | `backend/app/services/gemini_live.py` | **Fast Loop Multimodal WebSocket:** Bidirectional low-latency streaming multiplexer. Ingests 16kHz PCM candidate microphone audio and outputs 24kHz PCM synthesized speech chunks and live captions. | Real-time bidirectional streaming |
| **`gemini-2.5-pro`** (`REASONING_MODEL`) | `backend/app/services/shadow_supervisor.py` | **Slow Loop Async Shadow Supervisor:** Asynchronously inspects candidate utterances and code diffs in the background. Detects $O(N^2)$ algorithmic loops, data leakage, missing window partitioning, or shallow math claims, dynamically injecting silent follow-up directives to the interviewer. | Background async reasoning |
| **`gemini-2.5-flash`** (`EXTRACTOR_MODEL`) | `backend/app/services/resume_parser.py` | **Resume Claim Graph Extractor:** Parses uploaded PDF resumes into a high-fidelity structured Pydantic `CandidateClaimGraph` (projects, metrics, tech stack, and quantitative production claims) via JSON schema enforcement. | Structured JSON output |
| **`gemini-2.5-pro`** (`REASONING_MODEL`) | `backend/app/services/rubric_evaluator.py` | **Post-Interview BARS Evaluator & Mentor:** Generates rigorous 1–5 Behaviorally Anchored Rating Scale (BARS) evaluations across 4 core competencies, providing unvarnished hiring manager feedback, honest 0.0 scores for silent sessions, and 60-second gold-standard STAR rewrites for every question asked. | Complex evaluation report generation |
| **Native Google Search Grounding** | `backend/app/services/gemini_search_grounding.py` | **Real-Time Company Interview Retrieval:** Uses official `types.Tool(google_search=types.GoogleSearch())` to pre-fetch reported 2025/2026 interview questions for target companies (e.g., Swiggy, CRED, Google, Meta, Stripe) without 3rd-party search APIs. | Real-time Web Search Grounding |
| **Pyodide (Python WASM)** | `frontend/src/app/interview/[id]/page.tsx` | **Client-Side Python Sandbox:** Executes Python algorithms, self-attention layers, and streaming quantiles directly inside the browser with unit test assertions and zero backend compute cost. | In-browser WebAssembly execution |
| **DuckDB-WASM** | `frontend/src/app/interview/[id]/page.tsx` | **Client-Side Analytical SQL Engine:** In-browser columnar database running SQL cohort retention queries, rolling anomaly detection, and window rank functions on pre-seeded tables. | In-browser WebAssembly database |
| **Web Speech API & VoiceManager** | `frontend/src/lib/voiceManager.ts` | **Acoustic Echo Suppression & Synthesis:** Chromium-resilient deterministic persona voice synthesis (`voiceManager`) with acoustic guard windows, Spacebar instant barge-in, and echo loop cancellation. | Browser native speech synthesis/recognition |

---

## 📚 Where & How the Question Bank is Used Across the Platform

The question bank provides a diverse, extensible repository of technical interview problems designed for continuous practice over weeks without getting stuck in a repetitive loop:

### 1. Where the Question Bank Lives
- **Definition:** Located in `backend/app/services/question_bank.py` (`QUESTIONS_BANK`).
- **Diversity:** Includes 21 curated problems spanning 3 categories:
  - **7 SQL Problems (DuckDB):** Cohort retention, rolling 30-day anomaly detection, top-K window ranking, cumulative sessionization, customer lifetime value deciles, inventory turnover, and multi-touch attribution. Pre-seeded with realistic database tables (`users`, `transactions`, `events`, `predictions`).
  - **7 Python Algorithmic & ML Problems:** Scaled dot-product self-attention, streaming quantile estimation (Greenwald-Khanna), AUC-ROC curve calculation from scratch, IoU bounding box computation, non-maximum suppression (NMS), token-bucket rate limiter, and LRU cache with TTL. Each comes with starter code and automated test assertions.
  - **7 ML System Design Prompts:** Hyperlocal delivery dispatch & ETA at Swiggy scale, real-time UPI fraud detection at Razorpay, two-tower neural retrieval at Netflix, LLM RAG customer support system, real-time demand forecasting, multimodal visual search, and automated model drift & continuous training pipeline. Includes rubrics and scale SLA targets.

### 2. How Questions are Selected and Used in the Pipeline
1. **Session Creation (`POST /api/session/init`):**
   - If a specific `question_id` is supplied, that question is selected.
   - If no `question_id` is specified, `get_random_question()` automatically draws a fresh, randomized question tailored to the selected interview track. Each new interview session starts with a different problem, avoiding locking into the same challenge.
2. **FSM Stage Progression (`fsm_orchestrator.py`):**
   - When transitioning into `LIVE_CODING_SQL_PYTHON`, the FSM automatically verifies or picks an active coding problem from the bank.
   - When transitioning into `ML_SYSTEM_DESIGN`, it picks an active system design problem and rubric.
   - The question's prompt, starter code, and database seeds are pushed to the frontend via the `fsm_snapshot` WebSocket event.
3. **In-Session Dynamic Question Switching (`POST /api/session/{id}/advance-question`):**
   - If you have already solved a question or want to practice a different scenario during an active call, you can click **Switch Question** in the workbench or invoke the API to immediately swap to another problem from the bank.
4. **Agentic Probing & Hint Context Injection (`agentic_interviewer.py`):**
   - The active question's title, statement, category, and rubric criteria are injected into the persistent Gemini chat session context `[SYSTEM: Active problem: ...]`. This allows Dr. Elena, Alex, or Sarah to guide you on edge cases, provide progressive hints, and probe computational complexity tailored to that specific problem.
5. **Interactive Client Workbench (`page.tsx`):**
   - When an SQL question is active, the Monaco editor loads the SQL starter query, and DuckDB-WASM executes the seed script.
   - When a Python question is active, Pyodide executes the solution against the question's unit test assertions.
   - When a System Design question is active, Excalidraw opens for whiteboard diagramming.

### 3. How to Add More Questions to the Bank
To add your own custom questions for multi-week practice:
1. Open `backend/app/services/question_bank.py`.
2. Append a new `QuestionItem(...)` to `QUESTIONS_BANK` with your desired category (`SQL`, `PYTHON`, or `ML_SYSTEM_DESIGN`), prompt, starter code, seed SQL or unit tests, and rubric criteria.
3. The platform will automatically include your new questions in randomized rotation!

---

## 🎯 7 Specialized Interview Tracks

Prepare holistically for any stage in an engineering recruitment pipeline:

1. **Full Comprehensive Loop (5 Stages):** Intro → Resume Deep Dive → SQL/Python Coding → ML System Design → Behavioral Bar-Raiser.
2. **Pure ML Breadth Sprint:** Fast-paced, wide-ranging foundational & applied ML concepts (AUC-ROC vs PR, bias-variance tradeoffs, L1 vs L2 regularization, XGBoost vs Neural Nets, Adam vs AdamW, vanishing gradients).
3. **Pure ML Depth & Theory:** Deep mathematical derivations, loss formulation (triplet loss, infoNCE), backprop through attention, FlashAttention tiling mechanics, LoRA low-rank updates.
4. **Generative AI & LLM Engineering:** Production LLM architectures, RAG chunking & hybrid dense/sparse retrieval, LoRA vs DPO fine-tuning, KV cache optimization, vLLM PagedAttention, tool calling, and guardrails.
5. **Live Coding (Python + SQL):** In-browser Monaco editor with Pyodide Python WASM execution and DuckDB in-memory SQL sandbox.
6. **ML System Design:** Excalidraw-powered interactive canvas with real-time architectural component vision analysis.
7. **Resume & Project Deep Dive:** Automated parsing of candidate resumes with targeted probing of reported claims, metrics, and trade-offs.

---

## 🌐 Holistic Industry Archetypes

Prepare for real-world interviews across diverse market segments:

- 🇮🇳 **Indian Product Tech:** Tailored scenarios for Swiggy, Zomato, CRED, Razorpay, Flipkart, and Zepto (handling IPL order surges, hyperlocal delivery dispatch algorithms, bilingual search ranking, UPI fraud detection, and 10-minute dark store route optimization).
- 🚀 **AI Startups & Frontier Labs:** Fast-paced velocity, zero-to-one architecture, vLLM cost optimization, agentic tool workflows, and low-latency inference.
- 🏢 **Global Tech & FAANG:** Google, Meta, Amazon, Microsoft, Netflix, Apple, and Stripe bar-raiser rigor.

---

## 🔍 Native Gemini Google Search Grounding

To guarantee questions reflect actual 2025/2026 industry interviews, the platform integrates **Gemini Native Google Search Grounding**:
- Uses official Gemini API tools (`types.Tool(google_search=types.GoogleSearch())`).
- Requires **no third-party search subscriptions** (no Tavily or DuckDuckGo API keys required).
- Grounds interview questions in real reported interview experiences for the specific company and role.
- Backed by an offline curated real-world repository for Indian product unicorns and AI labs when offline or running in mock mode.

---

## 🧪 Testing & Quality Assurance

The codebase adheres to rigorous engineering standards with full test coverage and automated GitHub Actions CI.

```bash
# Run backend linters & formatters
ruff check backend/
ruff format --check backend/

# Run complete pytest test suite (29 tests)
pytest backend/tests/ -v

# Run frontend type checking & production build
cd frontend && npm run build
```

---

## 🔒 Privacy & Security Guarantees

1. **Zero Cloud Camera Upload:** Video streams from `navigator.mediaDevices.getUserMedia` are piped strictly into local `<video>` DOM elements. They are never sent to external servers.
2. **BYOK (Bring Your Own Key):** Your Gemini API key is stored in your browser's ephemeral `sessionStorage` and passed directly in authorization headers.
3. **Local SQLite Persistence:** Resumes, transcripts, and evaluation scorecards are stored in a local SQLite file (`ai_interviewer.db`) on your machine.

---

## 📄 License

MIT License. Contributions, issues, and feature requests are welcome!
