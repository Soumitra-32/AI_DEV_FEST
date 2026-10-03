# Backend API image (local reproducibility; Render builds from source, not this).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /srv

# libgomp1 = OpenMP runtime required by LightGBM/scikit-learn.
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 curl libgomp1 \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend package + data generator + default config. NEVER copy .env
# (secrets arrive via environment, see docs/DEPLOYMENT.md).
COPY backend/app ./backend/app
COPY backend/__init__.py ./backend/__init__.py
COPY backend/data ./backend/data
COPY backend/genai ./backend/genai
COPY backend/ml ./backend/ml
COPY backend/rules ./backend/rules
COPY backend/scripts ./backend/scripts

# Generate the synthetic dataset on first boot when no DB is mounted.
# Deterministic seeds in backend/data/config.yaml -> same data every time.
CMD ["sh", "-c", "test -f backend/data/shonchoy.db || python backend/scripts/generate_data.py; exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
