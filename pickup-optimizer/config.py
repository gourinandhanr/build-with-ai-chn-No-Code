"""
config.py – Centralised application settings.

All tunables are read from environment variables (or a .env file).
Pydantic-settings validates types and provides sensible defaults so the
service can start immediately in "mock" mode without any external keys.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide configuration loaded from env vars / .env file."""

    # ── Google Maps ──────────────────────────────────────────────────────
    google_maps_api_key: str = "UNSET"
    mock_maps: bool = True  # When True, maps_service returns fake data

    # ── Pickup decision tunables ─────────────────────────────────────────
    pickup_weight_threshold: float = 50.0   # kg – avg weight to trigger pickup
    pickup_trend_days: int = 7              # look-back window for trend calc
    pickup_max_interval_days: int = 14      # force pickup after N days

    # ── BigQuery ─────────────────────────────────────────────────────────
    gcp_project: str = "mock-project-for-local-dev"
    bigquery_dataset: str = "pickup_dataset"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton – import this wherever you need settings
settings = Settings()
