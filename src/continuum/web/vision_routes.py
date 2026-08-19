"""FastAPI routes for the vision subsystem.

Exposes the endpoints the dashboard and demo scripts call:
  POST /api/production/{pid}/vision/ingest   — kick a VI run on an asset
  GET  /api/take/{take_id}/observations      — read frame observations
  GET  /api/take/{take_id}/verdicts          — read Gemini verdicts
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from continuum.vision.engines.base import EngineMode
from continuum.vision.ingest import ingest_asset

router = APIRouter(prefix="/api", tags=["vision"])


class IngestRequest(BaseModel):
    asset: dict[str, Any] = Field(
        description="take_media_assets row (production_id, take_id, asset_id, gcs_uri, scene_id, mime_type)."
    )
    engine: str = Field(default="video_intelligence")
    features: list[str] | None = None
    context: dict[str, Any] | None = None
    mode: str = Field(default="stub", description="stub | real")


class IngestResponse(BaseModel):
    job_id: str
    engine: str
    state: str
    written: dict[str, int]
    error: str | None = None


@router.post("/production/{production_id}/vision/ingest", response_model=IngestResponse)
async def ingest_endpoint(production_id: str, req: IngestRequest) -> IngestResponse:
    if req.asset.get("production_id") not in (None, production_id):
        raise HTTPException(status_code=400, detail="asset.production_id must match path")
    req.asset["production_id"] = production_id
    try:
        mode = EngineMode(req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report = await ingest_asset(
        asset=req.asset,
        engine_key=req.engine,
        features=req.features,
        context=req.context,
        sink=None,  # dashboard triggers are dry-run by default; wire a sink for prod
        mode=mode,
    )
    return IngestResponse(
        job_id=report.job_id,
        engine=report.engine,
        state=report.state,
        written=report.written,
        error=report.error,
    )


@router.get("/take/{take_id}/observations")
def get_observations(take_id: str, feature: str | None = None) -> list[dict[str, Any]]:
    from continuum.tools.vision_tools import observations_for_take
    return observations_for_take(take_id, feature=feature)


@router.get("/take/{take_id}/verdicts")
def get_verdicts(take_id: str) -> list[dict[str, Any]]:
    from continuum.tools.vision_tools import verdicts_for_take
    return verdicts_for_take(take_id)


@router.get("/vision/capabilities")
def get_capabilities() -> dict[str, Any]:
    """Introspection endpoint — returns the engine registry as JSON."""
    from continuum.vision.registry import ENGINE_REGISTRY
    return {
        key: {
            "provider": spec.provider,
            "source_model": spec.source_model,
            "features": list(spec.features),
            "typical_latency_s": spec.typical_latency_s,
            "quota_hint": spec.quota_hint,
        }
        for key, spec in ENGINE_REGISTRY.items()
    }
