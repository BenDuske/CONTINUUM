"""CONTINUUM Web Application — Production Command Center.

FastAPI app serving the CONTINUUM dashboard. This is what filmmakers see:
production health, scene status, coverage confidence, continuity alerts,
and the signature WRAP SCENE button.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from continuum.config import config

app = FastAPI(
    title="CONTINUUM",
    description="Know you have the movie before you leave the set.",
    version="0.1.0",
)

# Static files and templates
_WEB_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_WEB_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Production Command Center — main dashboard."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "CONTINUUM",
        "production_name": "THE LAST SIGNAL",  # TODO: load from DB
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "continuum", "version": "0.1.0"}


@app.get("/api/production/{production_id}/status")
async def production_status(production_id: str):
    """Get production health metrics."""
    # TODO: Query ClickHouse for real data
    return {
        "production_id": production_id,
        "production_name": "THE LAST SIGNAL",
        "production_day": 17,
        "total_days": 31,
        "scenes_total": 47,
        "scenes_filmed": 30,
        "scenes_wrapped": 29,
        "coverage_confidence": 0.94,
        "continuity_confidence": 0.97,
        "open_issues": 3,
        "critical_issues": 1,
        "missing_shots": 3,
        "reshoot_exposure": "HIGH",
    }


@app.post("/api/production/{production_id}/scene/{scene_id}/wrap-check")
async def wrap_check(production_id: str, scene_id: str):
    """FINAL TAKE — Run wrap assessment for a scene.

    This is the signature feature. Triggers the full agent pipeline:
    FinalTake → Continuity → StoryGraph → Skeptic → CASCADE → verdict.
    """
    # TODO: Wire to ADK agent runner
    return {
        "scene_id": scene_id,
        "verdict": "NOT_SAFE_TO_WRAP",
        "coverage_confidence": 0.73,
        "message": "Agent pipeline not yet connected — scaffold only.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.port)
