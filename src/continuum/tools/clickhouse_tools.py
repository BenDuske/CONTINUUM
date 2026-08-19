# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""ClickHouse query tools for CONTINUUM agents.

These are ADK tool functions that agents call to query the production memory.
They wrap clickhouse-connect for direct DB access. The mcp-clickhouse MCP server
runs alongside for MCP-native integrations.
"""

from __future__ import annotations

import json
from typing import Any

import clickhouse_connect

from continuum.config import config


def _get_client():
    """Create a ClickHouse client from config."""
    return clickhouse_connect.get_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.user,
        password=config.clickhouse.password,
        secure=config.clickhouse.secure,
        database=config.clickhouse.database,
    )


# ---------------------------------------------------------------------------
# ADK Tool Functions (decorated with @tool when wired into agents)
# ---------------------------------------------------------------------------

def query_scenes(production_id: str, scene_numbers: list[int] | None = None) -> list[dict]:
    """Query scenes from the production memory.

    Args:
        production_id: The production to query.
        scene_numbers: Optional list of specific scene numbers. If None, returns all.

    Returns:
        List of scene dictionaries.
    """
    client = _get_client()
    if scene_numbers:
        placeholders = ", ".join(str(n) for n in scene_numbers)
        query = f"""
            SELECT * FROM scenes
            WHERE production_id = {{pid:String}}
            AND scene_number IN ({placeholders})
            ORDER BY scene_number
        """
    else:
        query = """
            SELECT * FROM scenes
            WHERE production_id = {pid:String}
            ORDER BY scene_number
        """
    result = client.query(query, parameters={"pid": production_id})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_takes_for_scene(production_id: str, scene_id: str) -> list[dict]:
    """Query all takes captured for a specific scene.

    Args:
        production_id: The production to query.
        scene_id: The scene to check.

    Returns:
        List of take dictionaries with ratings, audio status, etc.
    """
    client = _get_client()
    result = client.query(
        """
        SELECT * FROM takes
        WHERE production_id = {pid:String}
        AND scene_id = {sid:String}
        ORDER BY shot_id, take_number
        """,
        parameters={"pid": production_id, "sid": scene_id},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_shots_for_scene(production_id: str, scene_id: str) -> list[dict]:
    """Query planned shots for a scene.

    Args:
        production_id: The production to query.
        scene_id: The scene to check.

    Returns:
        List of shot dictionaries.
    """
    client = _get_client()
    result = client.query(
        """
        SELECT * FROM shots
        WHERE production_id = {pid:String}
        AND scene_id = {sid:String}
        ORDER BY shot_label
        """,
        parameters={"pid": production_id, "sid": scene_id},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_props(production_id: str, prop_ids: list[str] | None = None) -> list[dict]:
    """Query props and their current states.

    Args:
        production_id: The production to query.
        prop_ids: Optional specific prop IDs to query.

    Returns:
        List of prop dictionaries.
    """
    client = _get_client()
    if prop_ids:
        result = client.query(
            """
            SELECT * FROM props
            WHERE production_id = {pid:String}
            AND prop_id IN {pids:Array(String)}
            """,
            parameters={"pid": production_id, "pids": prop_ids},
        )
    else:
        result = client.query(
            "SELECT * FROM props WHERE production_id = {pid:String}",
            parameters={"pid": production_id},
        )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_production_events(
    production_id: str,
    event_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Query the production event stream.

    Args:
        production_id: The production to query.
        event_type: Optional filter by event type.
        entity_id: Optional filter by affected entity.
        limit: Max events to return.

    Returns:
        List of event dictionaries, newest first.
    """
    client = _get_client()
    conditions = ["production_id = {pid:String}"]
    params: dict[str, Any] = {"pid": production_id, "lim": limit}

    if event_type:
        conditions.append("event_type = {etype:String}")
        params["etype"] = event_type
    if entity_id:
        conditions.append("entity_id = {eid:String}")
        params["eid"] = entity_id

    where = " AND ".join(conditions)
    result = client.query(
        f"""
        SELECT * FROM production_events
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT {{lim:UInt32}}
        """,
        parameters=params,
    )
    rows = [dict(zip(result.column_names, row)) for row in result.result_rows]
    # Parse JSON data field
    for row in rows:
        if isinstance(row.get("data"), str):
            try:
                row["data"] = json.loads(row["data"])
            except (json.JSONDecodeError, TypeError):
                pass
    return rows


def query_continuity_issues(
    production_id: str,
    scene_id: str | None = None,
    unresolved_only: bool = True,
) -> list[dict]:
    """Query detected continuity issues.

    Args:
        production_id: The production to query.
        scene_id: Optional filter by scene.
        unresolved_only: If True, only return unresolved issues.

    Returns:
        List of issue dictionaries.
    """
    client = _get_client()
    conditions = ["production_id = {pid:String}"]
    params: dict[str, Any] = {"pid": production_id}

    if scene_id:
        conditions.append("scene_id = {sid:String}")
        params["sid"] = scene_id
    if unresolved_only:
        conditions.append("resolved = 0")

    where = " AND ".join(conditions)
    result = client.query(
        f"SELECT * FROM continuity_issues WHERE {where} ORDER BY detected_at DESC",
        parameters=params,
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def insert_production_event(event: dict) -> bool:
    """Insert a new production event into ClickHouse.

    Args:
        event: Event dictionary matching the ProductionEvent schema.

    Returns:
        True if successful.
    """
    client = _get_client()
    client.insert(
        "production_events",
        data=[[
            event["event_id"],
            event["production_id"],
            event["timestamp"],
            event["event_type"],
            event["entity_type"],
            event["entity_id"],
            json.dumps(event.get("data", {})),
            event.get("source", "system"),
            event.get("epistemic", "observed"),
        ]],
        column_names=[
            "event_id", "production_id", "timestamp", "event_type",
            "entity_type", "entity_id", "data", "source", "epistemic",
        ],
    )
    return True
