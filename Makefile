# Shonchoy Copilot — stub targets, filled in per phase.
# Phase 0 only defines the target names; recipes come later.

.PHONY: data seed train test api web deploy clean

data:            ## Generate synthetic dataset (Phase 1)
	python backend/scripts/generate_data.py

seed:            ## Seed the demo user "Rahim" (Phase 1)
	python backend/scripts/seed_demo_user.py

train:           ## Train all models (Phase 3+)
	@echo "TODO(phase 3): python backend/scripts/train_all.py"

test:            ## Run backend tests
	python -m pytest backend/tests -q

api:             ## Start FastAPI server (Phase 2)
	python -m uvicorn backend.app.main:app --reload --port 8000

web:             ## Start Next.js dev server (Phase 2)
	cd web && npm run dev

deploy:          ## Deploy (Vercel + Render) (Phase 9)
	@echo "TODO(phase 9): deploy steps"

clean:           ## Remove generated data and artifacts
	@echo "TODO: remove backend/data/*.db and backend/ml/artifacts/*"

