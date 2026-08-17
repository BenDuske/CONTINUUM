"""Provenance sidecar — every vision observation carries where it came from.

CONTINUUM's three epistemic layers (OBSERVED / INFERRED / CONFIRMED) map onto
this sidecar directly. The DIRECTOR + SKEPTIC agents rely on these fields to
decide whether a finding may be escalated to the crew.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EpistemicLayer(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class Provenance:
    """Attached to every row the vision layer writes to ClickHouse.

    `source_model` is one of the Google Cloud model identifiers actually
    called at runtime — no other AI providers are permitted per hackathon rules.
    """
    source_model: str                        # e.g. "videointelligence-v1p3beta1"
    engine: str                              # registry key, e.g. "video_intelligence"
    engine_mode: str                         # "stub" | "real"
    epistemic: EpistemicLayer
    confidence: float                        # 0..1
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    extra: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        """Flatten to the columns frame_observations / vision_verdicts expect."""
        return {
            "source_model": self.source_model,
            "confidence": float(self.confidence),
            "epistemic": self.epistemic.value,
        }

    def to_sidecar(self) -> dict[str, Any]:
        """Full JSON sidecar (useful when writing to GCS alongside an asset)."""
        d = asdict(self)
        d["generated_at"] = self.generated_at.isoformat()
        d["epistemic"] = self.epistemic.value
        return d
