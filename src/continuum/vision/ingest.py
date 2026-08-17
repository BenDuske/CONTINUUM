"""Ingest — glue that runs a job end-to-end.

    take_media_assets row  →  Engine.analyze()  →  writers.write_result()

Also owns the small job-state helper that records progress into
`continuum.vision_jobs`.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from continuum.vision.engines import build_engine
from continuum.vision.engines.base import EngineMode, EngineResult
from continuum.vision.writers import WriteSink, write_result


def _mode_from_env() -> EngineMode:
    raw = os.environ.get("CONTINUUM_VISION_ENGINE_MODE", "stub").lower()
    return EngineMode(raw) if raw in {"stub", "real"} else EngineMode.STUB


@dataclass
class IngestReport:
    job_id: str
    engine: str
    asset: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None = None
    state: str = "pending"                   # pending|running|succeeded|failed
    error: str | None = None
    written: dict[str, int] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "production_id": self.asset["production_id"],
            "asset_id": self.asset["asset_id"],
            "take_id": self.asset["take_id"],
            "engine": self.engine,
            "features": [],
            "state": self.state,
            "operation_name": "",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error or "",
        }


async def ingest_asset(
    *,
    asset: dict[str, Any],
    engine_key: str,
    features: list[str] | None = None,
    context: dict[str, Any] | None = None,
    sink: WriteSink | None = None,
    mode: EngineMode | None = None,
) -> IngestReport:
    """Run one engine over one asset and persist the result.

    `sink` is optional so callers (and tests) can execute in dry-run mode.
    """
    report = IngestReport(
        job_id=str(uuid.uuid4()),
        engine=engine_key,
        asset=asset,
        started_at=datetime.now(timezone.utc),
        state="running",
    )
    resolved_mode = mode or _mode_from_env()
    engine = build_engine(engine_key, mode=resolved_mode)

    try:
        result: EngineResult = await engine.analyze(
            asset=asset, features=features, context=context
        )
        if sink is not None:
            report.written = write_result(sink, result)
        else:
            report.written = {
                "observations": len(result.observations),
                "dialogue": len(result.dialogue),
                "verdicts": len(result.verdicts),
                "embeddings": len(result.embeddings),
            }
        report.state = "succeeded"
    except Exception as exc:  # broad on purpose — job state must record failures
        report.state = "failed"
        report.error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report.finished_at = datetime.now(timezone.utc)

    return report
