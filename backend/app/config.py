"""Application settings and feature flags.

Everything is environment-driven (see ``.env.example``) so a single module can be
switched off while the demo is running: the ``FEATURE_*`` flags are read here and
consumed by the routers, and the LLM is only used when a key is present.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = REPO_ROOT / "backend" / "data" / "shonchoy.db"


class Settings(BaseSettings):
    """Runtime configuration (env vars override the defaults below)."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Shonchoy Copilot API"
    api_version: str = "0.7.0"
    port: int = 8000

    # --- demo auth: the token decides the user, never the request body ---
    demo_auth_token: str = "change-me"
    demo_user_id: str = "rahim"
    demo_user_name_en: str = "Rahim"
    demo_user_name_bn: str = "রহিম"

    # --- data ---
    database_path: str = str(DEFAULT_DATABASE)

    # --- web ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,*"

    # --- LLM (Phase 4; the template fallback works without a key) ---
    # One primary key plus two backups. They are tried in this order and the
    # first one that answers wins, so a revoked or rate-limited primary key does
    # not take the demo down. Each backup may override the base URL and model,
    # which lets a backup be a different provider entirely rather than just a
    # second key for the same one. See backend/genai/client.py.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0
    llm_backup_api_key_1: str = ""
    llm_backup_base_url_1: str = ""
    llm_backup_model_1: str = ""
    llm_backup_api_key_2: str = ""
    llm_backup_base_url_2: str = ""
    llm_backup_model_2: str = ""

    # Switch the LLM intent classifier (use 3) off to fall back to keyword
    # classification only, without turning the whole explanation layer off.
    feature_llm_intent: bool = True

    # --- feature flags: switch a module off without a redeploy ---
    feature_forecast: bool = True
    feature_savings_plan: bool = True
    feature_anomalies: bool = True
    feature_signal: bool = True
    feature_tips: bool = True
    feature_voice: bool = True
    feature_llm: bool = True
    feature_metrics: bool = True
    feature_health_coach: bool = True
    feature_feedback: bool = True
    feature_events: bool = True
    feature_goal_templates: bool = True

    # Where the trained artifacts live. ``/metrics`` reads metrics.json from here
    # and nothing else, so a deployment can point at a read-only artifact mount.
    artifact_dir: str = "backend/ml/artifacts"

    # --- feedback + request logs (both PII-free, both beside metrics.json) ---
    # The feedback store is append-only JSONL in the same directory as
    # metrics.json (the "metrics store"), so ``/metrics`` can read it without a
    # new datastore. ``feedback_salt`` anonymises the respondent: only a hash of
    # the demo user id is written, never the id itself.
    feedback_salt: str = "shonchoy-feedback-v1"
    # The request log the no-PII middleware appends to. Optional: if the file
    # cannot be written the logger falls back to the process log only.
    request_log_path: str = "backend/ml/artifacts/requests.jsonl"

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database."""
        path = Path(self.database_path)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def artifact_path(self) -> Path:
        """Absolute path to the directory holding the trained artifacts."""
        path = Path(self.artifact_dir)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def feedback_path(self) -> Path:
        """Absolute path to the append-only feedback store (JSONL)."""
        return self.artifact_path / "feedback.jsonl"

    @property
    def events_path(self) -> Path:
        """Absolute path to the append-only product events store (JSONL)."""
        return self.artifact_path / "events.jsonl"

    @property
    def request_log_file(self) -> Path:
        """Absolute path to the PII-free request log (JSONL)."""
        path = Path(self.request_log_path)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def cors_origin_list(self) -> List[str]:
        """Allowed browser origins, parsed from the comma-separated env value.

        GAP-11: the wildcard is opt-in, never implied. Listing ``localhost``
        does NOT enable ``*`` (that defeated the allow-list). Two explicit
        ways to open LAN/mobile testing: put a literal ``*`` in CORS_ORIGINS,
        or set ``CORS_ALLOW_LAN=1``. Production (Render) sets neither, so the
        dashboard's Vercel domain list is enforced exactly.
        """
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if "*" not in origins and os.getenv("CORS_ALLOW_LAN") == "1":
            origins.append("*")
        return origins

    @property
    def llm_enabled(self) -> bool:
        """The LLM is only used when the flag is on *and* a key is configured."""
        from backend.genai import client as llm_client

        return bool(llm_client.enabled(self))

    @property
    def llm_intent_enabled(self) -> bool:
        """The LLM intent classifier is separately switchable (use 3)."""
        return bool(self.feature_llm and self.feature_llm_intent and self.llm_api_key)

    @property
    def llm_provider_count(self) -> int:
        """How many keys are configured (1 primary + up to 2 backups)."""
        from backend.genai import client as llm_client

        return len(llm_client.providers_from_settings(self))

    def feature_flags(self) -> Dict[str, bool]:
        """Every switch the frontend is allowed to know about."""
        return {
            "forecast": self.feature_forecast,
            "savings_plan": self.feature_savings_plan,
            "anomalies": self.feature_anomalies,
            "signal": self.feature_signal,
            "metrics": self.feature_metrics,
            "health_coach": self.feature_health_coach,
            "feedback": self.feature_feedback,
            "events": self.feature_events,
            "goal_templates": self.feature_goal_templates,
            "tips": self.feature_tips,
            "voice": self.feature_voice,
            "llm": self.llm_enabled,
        }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (FastAPI dependency)."""
    return Settings()

