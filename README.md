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
|  [Curated 15-Problem Bank]                                                        |
|   • 5 DuckDB SQL Window/Cohort Problems                                           |
|   • 5 Python Algorithmic Problems with Unit Tests                                 |
|   • 5 ML System Design Prompts with Detailed Rubrics                              |
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
│   │   │   └── question_bank.py      # 15 Curated DS/ML problems with DuckDB seeds
│   │   ├── prompts/
│   │   │   ├── interviewer_system.py # Anti-sycophantic Bar-Raiser system prompt
│   │   │   ├── supervisor_system.py  # Shadow evaluator instructions
│   │   │   └── grader_system.py      # Constructive mentor & BARS rubric prompt
│   │   └── main.py                   # FastAPI application, CORS, REST & WS endpoints
│   ├── tests/                        # 19 Pytest integration & unit tests
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

---

## 🧪 Testing & Quality Assurance

The codebase adheres to rigorous engineering standards with full test coverage and automated GitHub Actions CI.

```bash
# Run backend linters & formatters
ruff check backend/
ruff format --check backend/

# Run complete pytest test suite (19 tests)
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
