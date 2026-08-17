"""Vision engine base class.

Every engine has two modes:
  - STUB: returns deterministic fixtures. No Google quota consumed.
           Used by tests and by the demo when credits are unavailable.
  - REAL: calls the actual Google Cloud service.
Both modes emit identical row shapes so downstream writers do not care.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from continuum.vision.provenance import Provenance


class EngineMode(str, Enum):
    STUB = "stub"
    REAL = "real"


@dataclass
class EngineResult:
    """What every engine returns — a bag of observations plus provenance.

    `observations` are shaped for `continuum.frame_observations` inserts.
    `dialogue`, `verdicts`, and `embeddings` populate their dedicated tables.
    """
    engine: str
    mode: EngineMode
    provenance: Provenance
    observations: list[dict[str, Any]] = field(default_factory=list)
    dialogue: list[dict[str, Any]] = field(default_factory=list)
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    embeddings: list[dict[str, Any]] = field(default_factory=list)


class Engine(abc.ABC):
    """Abstract vision engine."""

    key: str

    def __init__(self, mode: EngineMode = EngineMode.STUB):
        self.mode = mode

    @abc.abstractmethod
    async def analyze(
        self,
        *,
        asset: dict[str, Any],
        features: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> EngineResult:
        """Run analysis on a take_media_assets row.

        Args:
            asset: dict with at least production_id, take_id, asset_id, scene_id, gcs_uri.
            features: subset of registry features to request (engine-specific).
            context: optional extras (e.g. screenplay excerpt for Gemini verdicts).
        """
        raise NotImplementedError

    def _is_real(self) -> bool:
        return self.mode == EngineMode.REAL
