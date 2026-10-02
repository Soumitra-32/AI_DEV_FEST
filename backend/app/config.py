"""Application settings and feature flags.

Everything is environment-driven (see ``.env.example``) so a single module can be
switched off while the demo is running: the ``FEATURE_*`` flags are read here and
consumed by the routers, and the LLM is only used when a key is present.
"""
from __future__ import annotations

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
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- LLM (Phase 4; the template fallback works without a key) ---
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0

    # --- feature flags: switch a module off without a redeploy ---
    feature_forecast: bool = True
    feature_savings_plan: bool = True
    feature_anomalies: bool = True
    feature_signal: bool = True
    feature_tips: bool = True
    feature_voice: bool = True
    feature_llm: bool = True

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database."""
        path = Path(self.database_path)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def cors_origin_list(self) -> List[str]:
        """Allowed browser origins, parsed from the comma-separated env value."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_enabled(self) -> bool:
        """The LLM is only used when the flag is on *and* a key is configured."""
        return bool(self.feature_llm and self.llm_api_key)

    def feature_flags(self) -> Dict[str, bool]:
        """Every switch the frontend is allowed to know about."""
        return {
            "forecast": self.feature_forecast,
            "savings_plan": self.feature_savings_plan,
            "anomalies": self.feature_anomalies,
            "signal": self.feature_signal,
            "tips": self.feature_tips,
            "voice": self.feature_voice,
            "llm": self.llm_enabled,
        }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (FastAPI dependency)."""
    return Settings()

