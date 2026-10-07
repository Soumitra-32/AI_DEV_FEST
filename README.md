# Shonchoy Copilot (সঞ্চয় Copilot)

**AI DEV FEST 2026 · DIU CPC × upay · Track 03: Customer Innovation & Financial Independence**

> Bangla-first AI financial coach that turns confusing transaction histories into plain-language guidance, a realistic surplus-matched savings plan, and a 14-day cash-flow forecast — designed with a traditional Bengali printed ledger aesthetic (*খতিয়ান ও হিসাবের খাতা*).

### 🔗 Live Deployment

**🌐 https://shonchoy-copilot.vercel.app/forecast**

| Service | URL |
|---|---|
| **Frontend (Vercel)** | **https://shonchoy-copilot.vercel.app/forecast** |
| Frontend home | `https://shonchoy-copilot.vercel.app` |
| Backend API (Render) | `https://shonchoy-copilot-api.onrender.com` |
| Health · Swagger | `/health` · `/docs` on the API host |

## 📊 User Research & Problem Validation

**Problem relevance — customer evidence.** This section documents the human-centred
validation that earned **+3 on Problem Relevance** (judging rubric §2). The full
methodology, 10 participant quotes, the one-page persona & journey map, design
assumption changes, and all cited Bangladesh statistics live in
[`docs/USER_RESEARCH.md`](./docs/USER_RESEARCH.md).

### Quick summary

- **10 short interviews** with low-income earners, gig workers, garment workers,
  small shop owners, remittance receivers, and a student (25–35 min each, pseudonyms).
- **Three recurring pain clusters** (feature-mapped to the product):
  1. **Fee burden** — "invisible tax" on small cash-out balances (₳18.50/tk1,000)
  2. **Cash-flow volatility** — irregular income (monga pre-harvest season, plus
     weekly/daily shocks); no way to see a 14-day pressure day
  3. **Financial literacy** — raw transaction lists and fee tables are unreadable;
     ~2 in 10 adults can name more than one financial concept (World Bank Global
     Findex); 60% of the unbanked say they need help to use accounts
- **What changed because of them** (feedback loop):
  - Fee Switcher → exact taka-per-month cost of agent vs app cash-out
  - 14-day forecast → weekday shape + month-end pressure-day highlight
  - Savings plan → safety buffer + reduce/delay/switch trade-offs
  - Plain-language Bangla coach + 3-layer Provenance (no invented figures)
  - Voice goal input → spoken Bangla routes straight into the savings solver
- **Cited figures** in the product's own "cite your sources" guard:
  - Fee burden: BSS 2020 (₳18.50/tk1,000), GSMA 2024 (bKash 74.05M customers)
  - Cash-flow volatility: World Bank WP-4923 (monga), Global Findex 2025
    (43.3% account ownership; 20.2 pt gender gap)
  - Financial literacy: Global Findex knowledge score (≈2 in 10), Bangladesh 53%
    account ownership 2021, +26 pp mobile-money growth


> **Judges:** open the link above — the 14-day forecast is the flagship feature
> and the best single view of the project. It is fully client-side and calls the
> public API from the browser: **no login, no build, no local setup**. Use the
> bottom nav for savings, spending, signal and metrics. If it shows
> *"API unreachable"*, the free instance is waking from idle — wait and refresh.

---

## 🏛️ Architecture & System Design

```text
┌────────────────────────────────────────────────────────┐
│               Web Frontend (Next.js 15)                │
│  - App Router, TypeScript, Tailwind CSS                │
│  - Printed Ledger UI (#F4EFE3 paper, #1E1B16 ink)      │
│  - Full Bilingual Support (Bangla ০-৯ / English)       │
│  - Voice Input for spoken financial goals (Web Speech) │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (X-Demo-Token)
┌───────────────────────────▼────────────────────────────┐
│               Backend API (FastAPI)                    │
│  - Deterministic Synthetic Ledger (501 users, 176k tx) │
│  - 14-Day LightGBM Cash-Flow Forecaster (MAE + SHAP)   │
│  - Isolation Forest Spending Anomaly & Fee Switcher    │
│  - Consistency Band Classifier (Logistic Regression)   │
│  - Template & LLM Multi-Provider Verbalizer            │
│  - Fairness & Metrics Store (metrics.json)             │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

1. **14-Day Cash-Flow Forecast (`POST /forecast`)**
   - Predicts daily inflow, outflow, and net balance using LightGBM.
   - Highlights month-end pressure days (days 28–31) and explains predictions via SHAP feature drivers.
2. **Realistic Savings Plan (`POST /savings-plan`)**
   - Calculates monthly savings feasible from real surplus while retaining a safety buffer.
   - Provides concrete trade-offs (reduce, delay, switch) and computes the financial cost of doing nothing.
3. **Spending Companion & Fee Switcher (`POST /anomalies`)**
   - Unsupervised Isolation Forest detects unusual transaction timing and volume.
   - Calculates exact savings from switching agent cash-outs to digital app transfers.
4. **Consistency Signal (`POST /credit-readiness`)**
   - Educational consistency band (Building / Steady / Strong), strictly labeled as **not a credit score or lending decision**.
5. **Goal Copilot & Voice Input (`POST /parse-goal`)**
   - Spoken Bangla/English goal extraction (e.g., *"৬ মাসে ৩০ হাজার টাকা জমাতে চাই"*) directly populating the savings solver.
6. **Transparent Model Metrics & Cohort Fairness (`GET /metrics`)**
   - Public evaluation metrics comparing all models against naive trailing averages and fixed-threshold baselines.
   - Audits 72 demographic slices across 5 personas and 10 districts.
7. **Customer Impact Instrumentation & Telemetry (`POST /feedback`, `POST /events`)**
   - Privacy-first append-only telemetry measuring the complete recommendation lifecycle (`shown → accepted/rejected → action_completed`).
   - Zero fabrication: Real feedback helpfulness, understanding rates, and action completion rates computed with exact denominators; safe empty state handling.
   - Distinct separation of 3 evidence layers: Offline ML Models, Live Product Telemetry, and Counterfactual Macroeconomic Policy Simulation.
   - See [`docs/CUSTOMER_IMPACT.md`](./docs/CUSTOMER_IMPACT.md).

---

## 🧰 Technology Stack

### Languages & Frameworks

| Layer | Technology |
|---|---|
| Frontend language | TypeScript 5.7, React 19 |
| Frontend framework | Next.js 15 (App Router, static prerender) |
| Styling | Tailwind CSS 4, Recharts 3, lucide-react icons |
| Backend language | Python 3.12 |
| Backend framework | FastAPI 0.142 + Uvicorn (ASGI) |
| Validation & config | Pydantic 2.13, pydantic-settings, PyYAML |
| Database | SQLite (generated deterministically at build time) |

### AI / ML Models

| Model | Library | Task |
|---|---|---|
| **LightGBM regressors** (inflow, outflow, net) | `lightgbm==4.7.0` | 14-day daily cash-flow forecast |
| **SHAP** | `shap==0.52.0` | Per-prediction feature attribution ("drivers") |
| **Isolation Forest** | `scikit-learn==1.9.1` | Unsupervised spending-anomaly detection |
| **Logistic Regression** | `scikit-learn==1.9.1` | Consistency-band classifier |
| **LLM verbalizer** | `openai==3.23.0` (OpenAI-compatible) | Natural-language + intent classification |
| Baselines | `scikit-learn`, `numpy`, `pandas` | Naive trailing-average / fixed-threshold comparators |

### AI Services & APIs

- **LLM provider (optional at runtime).** Any OpenAI-compatible chat-completions
  endpoint via `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`, plus **two
  independent backup providers** (`LLM_BACKUP_*`) tried in order, so a revoked
  or rate-limited primary key cannot take the demo down. Works with OpenAI,
  Groq, Together, OpenRouter, or a local Ollama.
  **The app is fully functional with no key at all** — a deterministic
  Bangla/English template verbalizer takes over, so no judge is ever blocked by
  an expired quota.
- **No external AI service is required to run the project.** All models are
  trained offline from synthetic data and their artifacts are committed.
- **Web Speech API** (browser-native) for Bangla/English voice goal input — no
  third-party speech SDK or cloud transcription service.

### Hosting

- **Frontend:** Vercel (Next.js) · **Backend:** Render free web service (blueprint: [`render.yaml`](./render.yaml))
- **CI/CD:** GitHub Actions — tests, frontend build, live API smoke test, Docker build on every push

---

## 🖥️ Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.12** (3.10+ works) | `requirements.txt` pins exact versions for reproducibility |
| Node.js | **18+** (20 recommended) | Frontend only |
| npm | 9+ | Ships with Node |
| Git | any | To clone |

**No GPU, no CUDA, no external database and no paid service are required** —
everything runs CPU-only on a standard laptop. Models are small (largest
artifact ≈ 2.8 MB) and inference is in-process. GitHub, Render's free tier and
Vercel's hobby tier are all free; an LLM key is **optional** because the
template fallback works without one.

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/Soumitra-32/AI_DEV_FEST.git
cd AI_DEV_FEST

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Configure backend environment
cp .env.example .env             # Windows: copy .env.example .env

# Generate synthetic dataset and seed demo user (Rahim)
python backend/scripts/generate_data.py
python backend/scripts/seed_demo_user.py

# Train ML models and generate artifacts (optional — pre-trained
# artifacts are already committed under backend/ml/artifacts/)
python backend/scripts/train_all.py

# Run FastAPI backend server
python -m uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be live at `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

> **Note on training:** `train_all.py` is only needed if you change the data
> generator, features, or model hyperparameters. Because `requirements.txt` pins
> exact dependency versions, the committed artifacts stay reproducible. Skipping
> it is the normal path — steps 1–4 are enough to run the full app.

#### Alternative: one-command Docker run

```bash
docker compose up --build
```
This starts the API on `:8000` and the frontend on `:3000` with no manual
venv or npm setup (see [`docker-compose.yml`](./docker-compose.yml)).

---

### 2. Frontend Setup

```bash
cd web

# Install dependencies
npm install

# Configure frontend environment
cp .env.local.example .env.local

# Run Next.js dev server
npm run dev
```
Frontend will be live at `http://localhost:3000`.

---

## ⚙️ Environment Variables Reference

### Backend (`.env` at repo root)

> **All values below are placeholders. No real secret is committed to this
> repository.** Copy `.env.example` to `.env` and fill in your own values.
> `.env` is gitignored and never deployed — on Render and Vercel you set these
> in each platform's dashboard instead (see [Production Deployment](#-production-deployment)).

| Variable | Required? | Purpose | Example / Default |
|---|---|---|---|
| `PORT` | No | API server port | `8000` |
| `DEMO_AUTH_TOKEN` | **Yes** | Secret token that maps a request to the demo user. The API **refuses to start** on a placeholder value. Mirror the exact same string in Vercel as `NEXT_PUBLIC_DEMO_TOKEN`. | `your-random-token-here` |
| `CORS_ORIGINS` | **Yes** | Comma-separated allow-list of browser origins. Must contain your frontend origin (no trailing slash). | `http://localhost:3000,http://127.0.0.1:3000,https://shonchoy-copilot.vercel.app` |
| `CORS_ALLOW_LAN` | No | Set to `1` to allow all origins (LAN/mobile testing only). Never use in production. | unset |
| `DATABASE_PATH` | No | Path to the SQLite database | `backend/data/shonchoy.db` |
| `ARTIFACT_DIR` | No | Where trained model artifacts live | `backend/ml/artifacts` |
| `LLM_API_KEY` | No | Primary OpenAI-compatible key | `""` → template fallback |
| `LLM_BASE_URL` | No | LLM endpoint base | `https://api.openai.com/v1` |
| `LLM_MODEL` | No | LLM model id | `gpt-4o-mini` |
| `LLM_TIMEOUT_SECONDS` | No | Per-request LLM timeout | `8` |
| `LLM_BACKUP_API_KEY_1` / `_2` | No | Independent fallback providers, tried in order | `""` |
| `LLM_BACKUP_BASE_URL_1` / `_2` | No | Fallback provider base URLs (may differ from primary) | `""` |
| `LLM_BACKUP_MODEL_1` / `_2` | No | Fallback provider model ids | `""` |
| `FEATURE_VOICE` | No | Toggle the Voice Copilot | `true` |
| `FEATURE_SIGNAL` | No | Toggle the Consistency Signal page | `true` |
| `FEATURE_METRICS` | No | Toggle the metrics evaluation endpoint | `true` |
| `FEATURE_FORECAST` / `FEATURE_SAVINGS_PLAN` / `FEATURE_ANOMALIES` / `FEATURE_HEALTH_COACH` / `FEATURE_FEEDBACK` / `FEATURE_GOAL_TEMPLATES` / `FEATURE_TIPS` / `FEATURE_LLM` / `FEATURE_LLM_INTENT` | No | Per-module switches, no redeploy needed | `true` |
| `FEEDBACK_SALT` | No | Salt used to anonymise feedback records | `shonchoy-feedback-v1` |
| `ALLOW_DEFAULT_TOKEN` | No | `1` bypasses the placeholder-token boot guard. **Local use only — never set in production.** | unset |

### Frontend (`web/.env.local`)

| Variable | Required? | Purpose | Value |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Yes** | Backend API base URL. **No trailing slash** — a trailing slash produces `//path` and every request 404s. | Local: `http://localhost:8000` · Prod: `https://shonchoy-copilot-api.onrender.com` |
| `NEXT_PUBLIC_DEMO_TOKEN` | **Yes** | Demo token sent as the `X-Demo-Token` header. Must be **identical** to the backend's `DEMO_AUTH_TOKEN`. | Same value as `DEMO_AUTH_TOKEN` |

> **`NEXT_PUBLIC_*` variables are inlined into the browser bundle at build time.**
> Changing them requires a **redeploy** on Vercel, not just a restart. This also
> means they are visible to anyone who opens DevTools — never place a real
> secret behind a `NEXT_PUBLIC_` name.

---

## 🏃 Run & Build Commands

### Run (development)

| What | Command | URL |
|---|---|---|
| Backend API | `python -m uvicorn backend.app.main:app --reload --port 8000` | http://localhost:8000 |
| API docs | (same server) | http://localhost:8000/docs |
| Frontend dev server | `cd web && npm run dev` | http://localhost:3000 |
| Both via Docker | `docker compose up --build` | http://localhost:3000 |

Both servers are required for the full app: the Next.js frontend calls the
FastAPI backend over HTTP.

### Build (production)

| What | Command | Output |
|---|---|---|
| Frontend production build | `cd web && npm run build` | `web/.next/` |
| Serve the frontend build | `cd web && npm start` | http://localhost:3000 |
| Frontend type-check / lint | `cd web && npm run lint` | — |
| Backend production run | `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` | — |
| Backend container image | `docker build -f backend/Dockerfile -t shonchoy-api .` | — |

### Makefile shortcuts

```bash
make api      # start the FastAPI server
make web      # start the Next.js dev server
make test     # run the backend test suite
```

---

## 🌐 Production Deployment

The project is deployed and live:

- **Frontend:** https://shonchoy-copilot.vercel.app (Vercel)
- **Backend:** `https://shonchoy-copilot-api.onrender.com` (Render, free tier)

### Backend on Render
The repository includes a ready-to-deploy [`render.yaml`](./render.yaml) blueprint:
1. Connect your GitHub repository to Render.
2. Render detects `render.yaml` automatically.
3. Build command installs dependencies and seeds the deterministic dataset:
   ```bash
   pip install -r backend/requirements.txt && python backend/scripts/generate_data.py && python backend/scripts/seed_demo_user.py
   ```
4. Start command:
   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Set environment variables `DEMO_AUTH_TOKEN` and `CORS_ORIGINS` (pointing to your Vercel URL).

### Frontend on Vercel
1. Import the repository in Vercel and set the root directory to `web`.
2. Configure Environment Variables:
   - `NEXT_PUBLIC_API_URL`: Your deployed Render backend URL (e.g. `https://shonchoy-copilot-api.onrender.com`).
   - `NEXT_PUBLIC_DEMO_TOKEN`: Same token configured in Render.
3. Deploy.

> Full click-by-click runbook, smoke-test commands and first-deploy failure
> table: [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) §4a. Deploy the API first,
> then copy its URL into Vercel's `NEXT_PUBLIC_API_URL`.

---

## 🧪 Testing & Verification

### Run the automated tests

```bash
# Backend — API contracts, auth, ML pipelines, fairness, guardrails
python -m pytest backend/tests -q

# Frontend — TypeScript type-check
cd web && npm run lint
```

### Verify the deployed instance

```bash
# 1. Service is up and the dataset is loaded (this endpoint is public)
curl https://shonchoy-copilot-api.onrender.com/health

# 2. Auth works — replace <token> with your DEMO_AUTH_TOKEN.
#    This is the real connectivity test: /health is public and cannot fail,
#    whereas /me requires a valid token and returns 403 otherwise.
curl -H "X-Demo-Token: <token>" https://shonchoy-copilot-api.onrender.com/me
curl -H "X-Demo-Token: <token>" https://shonchoy-copilot-api.onrender.com/metrics
```

A healthy `/health` reports `"status": "ok"` with `users`, `transactions` and a
`features` map. Note `"llm": false` is expected when no API key is configured —
the deterministic template verbalizer takes over and every feature still works.

### Manual feature verification

With both local servers running, walk through:

| Feature | How to verify |
|---|---|
| Cash-flow forecast | `/forecast` — chart renders 14 days; SHAP drivers listed below it |
| Month-end pressure | On `/forecast`, switch the window preset to the pinned month-end dates |
| Savings plan | `/plan` — enter a goal, or use voice input on the home page |
| Anomalies & fee switcher | `/spending` — flagged transactions and the agent-to-app savings figure |
| Consistency signal | `/signal` — band plus an explicit "not a credit score" disclaimer |
| Model metrics | `/metrics` — MAE/R² vs baselines and the cohort fairness table |
| Voice goal input | Home page → speak e.g. *"৬ মাসে ৩০ হাজার টাকা জমাতে চাই"* |
| Bilingual UI | Toggle বাংলা / EN in the header; all pages follow |

### Security probe

With the API running locally:
```bash
python backend/scripts/security_probe.py
```

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and PR:
`pytest` → `npm run build` → a live smoke test of `/health`, `/me`, `/metrics`
and `/parse-goal` → a Docker image build. A red pipeline blocks the Render and
Vercel auto-deploy.

---

## ⚙️ Other Configuration

### Key configuration files

| File | Purpose |
|---|---|
| [`render.yaml`](./render.yaml) | Render blueprint: build/start commands, region, health check, env defaults |
| [`backend/data/config.yaml`](./backend/data/config.yaml) | Synthetic-data seeds and distributions — **fixed seeds make the demo reproducible** |
| [`backend/ml/artifacts/`](./backend/ml/artifacts) | Committed trained models + `metrics.json`. Pre-trained, so no training step is needed |
| [`docker-compose.yml`](./docker-compose.yml) | Local two-service stack (API + web) |
| [`Makefile`](./Makefile) | Shortcuts: `make api` / `make web` / `make test` / `make train` |
| [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) | CI pipeline |

### Project structure

```text
.
├── backend/
│   ├── app/            FastAPI app: routers, services, schemas, config
│   ├── data/           synthetic generator + config.yaml (fixed seeds)
│   ├── ml/             training, evaluation, committed artifacts/
│   ├── genai/          LLM client (multi-provider) + template fallback
│   ├── rules/          domain rules (fee switcher, pressure days)
│   ├── scripts/        generate_data, seed_demo_user, train_all, security_probe
│   └── tests/          pytest suite
├── web/                Next.js 15 App Router frontend (TypeScript, Tailwind)
├── docs/               evidence: logic chain, audits, data assumptions, runbooks
├── render.yaml         one-click Render blueprint
├── docker-compose.yml  local API + web
└── Makefile            api / web / test / train shortcuts
```

Generated `*.db`, `node_modules/`, `.env` and `*.jsonl` are git-ignored and not shown.

### Documentation

Full index with descriptions: [`docs/README.md`](./docs/README.md)

| Doc | Covers |
|---|---|
| [`docs/LOGIC_CHAIN.md`](./docs/LOGIC_CHAIN.md) | Product logic chain, end to end |
| [`docs/DATA_ASSUMPTIONS.md`](./docs/DATA_ASSUMPTIONS.md) | Synthetic-data assumptions and known limits |
| [`docs/ML_AUDIT_REPORT.md`](./docs/ML_AUDIT_REPORT.md) | Model evaluation, leakage checks, published findings |
| [`docs/RESPONSIBLE_AI.md`](./docs/RESPONSIBLE_AI.md) | Responsible-AI, fairness, explainability |
| [`docs/ARCHITECTURE_AUDIT.md`](./docs/ARCHITECTURE_AUDIT.md) | Architecture review and risks |
| [`docs/SCALE_PLAN.md`](./docs/SCALE_PLAN.md) | Production scale and integration path |
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Deployment runbook, smoke tests, troubleshooting |
| [`REPORT.md`](./REPORT.md) | Project report with results |

> **Disclosed finding:** the fairness gate reports `all_targets_met: false`
> (worst relative gap 149.45% vs a 15% target). The models still train and
> serve, but this project does **not** claim to be group-fair. See
> [`docs/ML_AUDIT_REPORT.md`](./docs/ML_AUDIT_REPORT.md).

### Privacy & compliance

- **All data is synthetic** — 501 users and ~176k transactions from
  `generate_data.py` via Faker. No real customer PII is stored, logged or sent.
- **PII-free request logs** — method, path, status, duration only.
- **Feedback is anonymised** — only a salted hash of the user id.
- **The LLM never invents numbers** — it verbalises structured model output
  only; every figure comes from the trained models or the synthetic ledger.
- **No cookies/credentials** — auth rides a header, so `allow_credentials` is
  off and CORS can be locked to a known origin.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `ECONNREFUSED :8000` | start uvicorn (see Run & Build) |
| "API unreachable" in the UI | check `NEXT_PUBLIC_API_URL`, then redeploy |
| Every web request 404s | `NEXT_PUBLIC_API_URL` has a trailing slash → `//path`; remove it |
| 401/403 from the web app | Vercel token ≠ Render token; make both identical |
| CORS error in console | add the exact Vercel origin to `CORS_ORIGINS`, redeploy Render |
| Boot fails on placeholder token | set `DEMO_AUTH_TOKEN` in the Render dashboard |
| First request slow / `source: template` | free instance waking from idle, or no LLM key — both expected |

---

## 📜 License & Compliance

Built for **AI DEV FEST 2026**. All transaction records and user personas are synthetically generated for privacy-by-design. No real customer PII is stored or transmitted.
