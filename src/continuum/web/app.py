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


@app.get("/api/production/{production_id}/timeline")
async def production_timeline(production_id: str, at: str | None = None):
    """Reconstruct the Living Film Graph as of ``at`` (ISO 8601, UTC).

    ClickHouse's superpower here is time — the ``production_events`` table is
    an append-only MergeTree ordered by ``timestamp``, so answering
    "what did the production look like at 10:32 last Tuesday?" is a single
    range scan, not a rebuild. Missing ``at`` reports the current wall-clock.

    Response fields
    ---------------
    ``as_of`` — the timestamp the state is reconstructed to.
    ``event_count`` — total events at or before ``as_of``.
    ``event_types`` — event-type histogram at or before ``as_of``.
    ``prop_states`` — last known state per prop from PROP_STATE_CHANGED events.
    ``captured_shot_count`` — distinct shots captured at or before ``as_of``.
    ``script_revisions`` — count of SCRIPT_REVISION events at or before ``as_of``.
    ``last_event`` — the most recent event (for narrative context).
    """
    client = _get_ch_client()

    # Default to "now" if the caller didn't pin a moment.
    if at is None:
        as_of_expr = "now64(3)"
        params: dict[str, object] = {"pid": production_id}
    else:
        as_of_expr = "parseDateTime64BestEffort({at:String}, 3)"
        params = {"pid": production_id, "at": at}

    def q(sql: str):
        return client.query(sql, parameters=params)

    total = q(
        f"SELECT count() FROM production_events "
        f"WHERE production_id = {{pid:String}} AND timestamp <= {as_of_expr}"
    )
    event_count = total.result_rows[0][0] if total.result_rows else 0

    types = q(
        f"SELECT event_type, count() AS c FROM production_events "
        f"WHERE production_id = {{pid:String}} AND timestamp <= {as_of_expr} "
        f"GROUP BY event_type ORDER BY c DESC"
    )
    event_types = {row[0]: row[1] for row in types.result_rows}

    # Prop state = the most recent PROP_STATE_CHANGED per entity at or before as_of.
    # argMax picks the ``data`` payload for the row with the largest timestamp.
    prop_state_rows = q(
        f"SELECT entity_id, argMax(data, timestamp) AS latest, max(timestamp) AS ts "
        f"FROM production_events "
        f"WHERE production_id = {{pid:String}} "
        f"  AND event_type = 'PROP_STATE_CHANGED' "
        f"  AND timestamp <= {as_of_expr} "
        f"GROUP BY entity_id"
    )
    prop_states = []
    for entity_id, latest, ts in prop_state_rows.result_rows:
        try:
            import json as _json
            payload = _json.loads(latest) if latest else {}
        except Exception:
            payload = {"raw": latest}
        prop_states.append({
            "prop_id": entity_id,
            "state": payload.get("to") or payload.get("state"),
            "reason": payload.get("reason"),
            "as_of": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        })

    captured = q(
        f"SELECT uniqExact(JSONExtractString(data, 'shot')) "
        f"FROM production_events "
        f"WHERE production_id = {{pid:String}} "
        f"  AND event_type = 'TAKE_CAPTURED' "
        f"  AND timestamp <= {as_of_expr}"
    )
    captured_shots = captured.result_rows[0][0] if captured.result_rows else 0

    revisions = event_types.get("SCRIPT_REVISION", 0)

    last = q(
        f"SELECT timestamp, event_type, entity_type, entity_id, source "
        f"FROM production_events "
        f"WHERE production_id = {{pid:String}} AND timestamp <= {as_of_expr} "
        f"ORDER BY timestamp DESC LIMIT 1"
    )
    last_event = None
    if last.result_rows:
        ts, et, en_t, en_id, src = last.result_rows[0]
        last_event = {
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "event_type": et,
            "entity_type": en_t,
            "entity_id": en_id,
            "source": src,
        }

    resolved_as_of = q(f"SELECT {as_of_expr}").result_rows[0][0]

    return {
        "production_id": production_id,
        "as_of": resolved_as_of.isoformat() if hasattr(resolved_as_of, "isoformat") else str(resolved_as_of),
        "event_count": event_count,
        "event_types": event_types,
        "prop_states": prop_states,
        "captured_shot_count": captured_shots,
        "script_revisions": revisions,
        "last_event": last_event,
    }


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
