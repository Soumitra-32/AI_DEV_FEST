# Shonchoy Copilot (সঞ্চয় Copilot)

**AI DEV FEST 2026 · DIU CPC × upay · Track 03: Customer Innovation & Financial Independence**

> Bangla-first AI financial coach that turns confusing transaction histories into plain-language guidance, a realistic surplus-matched savings plan, and a 14-day cash-flow forecast — designed with a traditional Bengali printed ledger aesthetic (*খতিয়ান ও হিসাবের খাতা*).

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
4. **Consistency Signal (`POST /signal`)**
   - Educational consistency band (Building / Steady / Strong), strictly labeled as **not a credit score or lending decision**.
5. **Goal Copilot & Voice Input (`POST /parse-goal`)**
   - Spoken Bangla/English goal extraction (e.g., *"৬ মাসে ৩০ হাজার টাকা জমাতে চাই"*) directly populating the savings solver.
6. **Transparent Model Metrics & Cohort Fairness (`GET /metrics`)**
   - Public evaluation metrics comparing all models against naive trailing averages and fixed-threshold baselines.
   - Audits 72 demographic slices across 5 personas and 10 districts.

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/Taskif/AI_DEV_FEST.git
cd AI_DEV_FEST

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Generate synthetic dataset and seed demo user (Rahim)
python backend/scripts/generate_data.py
python backend/scripts/seed_demo_user.py

# Train ML models and generate artifacts
python backend/scripts/train_all.py

# Configure backend environment
cp .env.example .env

# Run FastAPI backend server
python -m uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be live at `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

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

### Backend (`.env`)

| Variable | Description | Default / Example |
|---|---|---|
| `PORT` | API server port | `8000` |
| `DEMO_AUTH_TOKEN` | Secret token mapped to demo user | `e97f8bfd87cf85d2e47985d7ff1babdc71d17b304918a243` |
| `CORS_ORIGINS` | Comma-separated allowed CORS origins | `http://localhost:3000,http://127.0.0.1:3000,https://shonchoy-copilot.vercel.app` |
| `DATABASE_PATH` | Path to SQLite database file | `backend/data/shonchoy.db` |
| `LLM_API_KEY` | (Optional) Primary OpenAI-compatible key | `""` (defaults to template fallback) |
| `LLM_MODEL` | LLM model name | `gpt-4o-mini` |
| `FEATURE_VOICE` | Enable Voice Copilot | `true` |
| `FEATURE_SIGNAL` | Enable Consistency Signal | `true` |
| `FEATURE_METRICS` | Enable Metrics evaluation endpoint | `true` |

### Frontend (`web/.env.local`)

| Variable | Description | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` (local) or production Render URL |
| `NEXT_PUBLIC_DEMO_TOKEN` | Demo user authentication token | Same value as `DEMO_AUTH_TOKEN` |

---

## 🌐 Production Deployment

### Backend on Render
The repository includes a ready-to-deploy [`render.yaml`](file:///home/taskifbin/Documents/AI%20HACKATHON/AI_DEV_FEST/render.yaml) blueprint:
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

---

## 🧪 Testing

Run backend tests:
```bash
python -m pytest backend/tests -q
```
All 361 backend integration tests verify API contracts, auth tokens, ML pipelines, fairness auditing, and guardrails.

---

## 📜 License & Compliance

Built for **AI DEV FEST 2026**. All transaction records and user personas are synthetically generated for privacy-by-design. No real customer PII is stored or transmitted.
