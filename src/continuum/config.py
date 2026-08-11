"""CONTINUUM configuration — loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class GeminiConfig:
    """Google Gemini / Vertex AI settings."""

    api_key: str = field(default_factory=lambda: os.environ.get("GOOGLE_GENAI_API_KEY", ""))
    project: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
    location: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
    model: str = "gemini-3.5-flash"  # fast + capable; upgrade to pro for complex reasoning


@dataclass(frozen=True)
class ClickHouseConfig:
    """ClickHouse Cloud connection settings."""

    host: str = field(default_factory=lambda: os.environ.get("CLICKHOUSE_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.environ.get("CLICKHOUSE_PORT", "8443")))
    user: str = field(default_factory=lambda: os.environ.get("CLICKHOUSE_USER", "default"))
    password: str = field(default_factory=lambda: os.environ.get("CLICKHOUSE_PASSWORD", ""))
    secure: bool = field(default_factory=lambda: os.environ.get("CLICKHOUSE_SECURE", "true").lower() == "true")
    database: str = "continuum"


@dataclass(frozen=True)
class ParallelConfig:
    """Parallel Search API settings."""

    api_key: str = field(default_factory=lambda: os.environ.get("PARALLEL_API_KEY", ""))


@dataclass(frozen=True)
class AppConfig:
    """Top-level application config."""

    env: str = field(default_factory=lambda: os.environ.get("CONTINUUM_ENV", "development"))
    port: int = field(default_factory=lambda: int(os.environ.get("CONTINUUM_PORT", "8080")))
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    clickhouse: ClickHouseConfig = field(default_factory=ClickHouseConfig)
    parallel: ParallelConfig = field(default_factory=ParallelConfig)

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


# Singleton
config = AppConfig()
