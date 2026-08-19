# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""CONTINUUM Web Application — Production Command Center.

FastAPI app serving the CONTINUUM dashboard. This is what filmmakers see:
production health, scene status, coverage confidence, continuity alerts,
and the signature WRAP SCENE button.

All endpoints query ClickHouse for real data and invoke ADK agents for analysis.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import clickhouse_connect
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from continuum import runner
from continuum.config import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize and clean up the agent pipeline."""
    logger.info("CONTINUUM starting up...")
    yield
    await runner.shutdown()
    logger.info("CONTINUUM shut down.")


app = FastAPI(
    title="CONTINUUM",
    description="Know you have the movie before you leave the set.",
    version="0.1.0",
    lifespan=lifespan,
)

# Vision subsystem routes (Google Video Intelligence + Vertex AI + Gemini multimodal)
from continuum.web.vision_routes import router as vision_router  # noqa: E402

app.include_router(vision_router)

# Templates
_WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=_WEB_DIR / "templates")


def _get_ch_client():
    """Create a ClickHouse client for direct queries (dashboard data)."""
    return clickhouse_connect.get_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.user,
        password=config.clickhouse.password,
        secure=config.clickhouse.secure,
        database=config.clickhouse.database,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Production Command Center — main dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "title": "CONTINUUM",
            "production_name": "THE LAST SIGNAL",
        },
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    # Verify ClickHouse connectivity
    try:
        client = _get_ch_client()
        result = client.query("SELECT 1")
        ch_ok = len(result.result_rows) > 0
    except Exception:
        ch_ok = False

    return {
        "status": "ok" if ch_ok else "degraded",
        "service": "continuum",
        "version": "0.1.0",
        "clickhouse": "connected" if ch_ok else "unreachable",
    }


# ---------------------------------------------------------------------------
# Production Data API (queries ClickHouse directly for dashboard metrics)
# ---------------------------------------------------------------------------

@app.get("/api/production/{production_id}/status")
async def production_status(production_id: str):
    """Get production health metrics from ClickHouse."""
    client = _get_ch_client()

    # Scene counts
    scenes = client.query(
        "SELECT count() as total, "
        "sum(filmed) as filmed, "
        "sum(wrapped) as wrapped "
        "FROM scenes WHERE production_id = {pid:String}",
        parameters={"pid": production_id},
    )
    total, filmed, wrapped = scenes.result_rows[0] if scenes.result_rows else (0, 0, 0)

    # Shot coverage
    shots = client.query(
        "SELECT count() as total, sum(captured) as captured "
        "FROM shots WHERE production_id = {pid:String}",
        parameters={"pid": production_id},
    )
    total_shots, captured_shots = shots.result_rows[0] if shots.result_rows else (0, 0)

    # Open issues
    issues = client.query(
        "SELECT count() as total, "
        "countIf(severity = 'critical') as critical "
        "FROM continuity_issues "
        "WHERE production_id = {pid:String} AND resolved = 0",
        parameters={"pid": production_id},
    )
    open_issues, critical = issues.result_rows[0] if issues.result_rows else (0, 0)

    # Takes count
    takes = client.query(
        "SELECT count() FROM takes WHERE production_id = {pid:String}",
        parameters={"pid": production_id},
    )
    total_takes = takes.result_rows[0][0] if takes.result_rows else 0

    coverage = captured_shots / total_shots if total_shots > 0 else 0.0
    missing = total_shots - captured_shots

    return {
        "production_id": production_id,
        "production_name": "THE LAST SIGNAL",
        "scenes_total": total,
        "scenes_filmed": filmed,
        "scenes_wrapped": wrapped,
        "shots_total": total_shots,
        "shots_captured": captured_shots,
        "coverage_confidence": round(coverage, 2),
        "total_takes": total_takes,
        "open_issues": open_issues,
        "critical_issues": critical,
        "missing_shots": missing,
    }


@app.get("/api/production/{production_id}/scenes")
async def list_scenes(production_id: str, limit: int = 50):
    """List scenes with their status."""
    client = _get_ch_client()
    result = client.query(
        "SELECT scene_id, scene_number, slug, int_ext, location_name, "
        "time_of_day, characters, filmed, wrapped "
        "FROM scenes WHERE production_id = {pid:String} "
        "ORDER BY scene_number LIMIT {lim:UInt32}",
        parameters={"pid": production_id, "lim": limit},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


@app.get("/api/production/{production_id}/scene/{scene_id}")
async def scene_detail(production_id: str, scene_id: str):
    """Get full detail for a scene including shots, takes, and props."""
    client = _get_ch_client()

    # Scene info
    scene = client.query(
        "SELECT * FROM scenes WHERE production_id = {pid:String} AND scene_id = {sid:String}",
        parameters={"pid": production_id, "sid": scene_id},
    )
    scene_data = dict(zip(scene.column_names, scene.result_rows[0])) if scene.result_rows else {}

    # Shots
    shots = client.query(
        "SELECT * FROM shots WHERE production_id = {pid:String} AND scene_id = {sid:String} "
        "ORDER BY shot_label",
        parameters={"pid": production_id, "sid": scene_id},
    )
    shots_data = [dict(zip(shots.column_names, row)) for row in shots.result_rows]

    # Takes
    takes = client.query(
        "SELECT * FROM takes WHERE production_id = {pid:String} AND scene_id = {sid:String} "
        "ORDER BY shot_id, take_number",
        parameters={"pid": production_id, "sid": scene_id},
    )
    takes_data = [dict(zip(takes.column_names, row)) for row in takes.result_rows]

    return {
        "scene": scene_data,
        "shots": shots_data,
        "takes": takes_data,
    }


# ---------------------------------------------------------------------------
# Agent API (runs ADK agents via Gemini + mcp-clickhouse)
# ---------------------------------------------------------------------------

class AgentQueryRequest(BaseModel):
    """Free-form agent query."""
    query: str
    production_id: str = "tls-001"


class CascadeRequest(BaseModel):
    """CASCADE change-impact analysis request."""
    change_description: str
    production_id: str = "tls-001"


@app.post("/api/agent/query")
async def agent_query(req: AgentQueryRequest):
    """Run a free-form query through the CONTINUUM agent pipeline."""
    response = await runner.run_agent_query(req.query)
    return {"query": req.query, "response": response}


@app.post("/api/production/{production_id}/scene/{scene_id}/wrap-check")
async def wrap_check(production_id: str, scene_id: str):
    """FINAL TAKE — Run wrap assessment for a scene.

    This is the signature feature. Triggers the full agent pipeline:
    Director → FinalTake → Continuity → Skeptic → verdict.
    """
    result = await runner.run_wrap_check(production_id, scene_id)
    return result


@app.post("/api/production/{production_id}/scene/{scene_id}/continuity-check")
async def continuity_check(production_id: str, scene_id: str):
    """Run a continuity check for a scene."""
    result = await runner.run_continuity_check(production_id, scene_id)
    return result


@app.post("/api/production/{production_id}/cascade")
async def cascade_analysis(production_id: str, req: CascadeRequest):
    """Run a CASCADE change-impact analysis."""
    result = await runner.run_cascade_analysis(production_id, req.change_description)
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=config.port)
