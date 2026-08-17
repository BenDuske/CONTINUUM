"""ADK tool functions for vision — exposed to CONTINUITY, FINAL TAKE, CASCADE.

These are thin ClickHouse readers. They intentionally do NOT trigger new VI
runs; ingestion is triggered by the web layer or a batch worker, never by
an agent mid-conversation.
"""

from __future__ import annotations

from typing import Any

from continuum.tools.clickhouse_tools import _get_client  # reuse the shared factory


def observations_for_take(take_id: str, feature: str | None = None) -> list[dict[str, Any]]:
    """Every frame observation attached to a take, optionally filtered by feature."""
    client = _get_client()
    if feature:
        query = """
            SELECT obs_id, feature, ts_ms, end_ms, entity_kind, entity_id,
                   entity_label, confidence, epistemic, source_model
            FROM frame_observations
            WHERE take_id = {tid:String} AND feature = {feat:String}
            ORDER BY ts_ms
        """
        result = client.query(query, parameters={"tid": take_id, "feat": feature})
    else:
        query = """
            SELECT obs_id, feature, ts_ms, end_ms, entity_kind, entity_id,
                   entity_label, confidence, epistemic, source_model
            FROM frame_observations
            WHERE take_id = {tid:String}
            ORDER BY ts_ms
        """
        result = client.query(query, parameters={"tid": take_id})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def dialogue_for_take(take_id: str) -> list[dict[str, Any]]:
    """Speech-transcription segments for a take, in temporal order."""
    client = _get_client()
    query = """
        SELECT segment_index, ts_ms, end_ms, speaker_tag,
               transcript, confidence, source_model, epistemic
        FROM take_dialogue
        WHERE take_id = {tid:String}
        ORDER BY segment_index
    """
    result = client.query(query, parameters={"tid": take_id})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def verdicts_for_take(take_id: str) -> list[dict[str, Any]]:
    """Gemini multimodal verdicts on a take — INFERRED until SKEPTIC confirms."""
    client = _get_client()
    query = """
        SELECT verdict_id, question, verdict, evidence, confidence,
               source_model, epistemic
        FROM vision_verdicts
        WHERE take_id = {tid:String}
        ORDER BY verdict_id
    """
    result = client.query(query, parameters={"tid": take_id})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def props_observed_in_take(take_id: str) -> list[dict[str, Any]]:
    """Object-tracking rows mapped to prop-shaped candidates."""
    client = _get_client()
    query = """
        SELECT entity_id, entity_label, MIN(ts_ms) AS first_ms,
               MAX(end_ms) AS last_ms, AVG(confidence) AS avg_conf
        FROM frame_observations
        WHERE take_id = {tid:String}
          AND feature = 'object'
          AND entity_kind = 'prop'
        GROUP BY entity_id, entity_label
        ORDER BY avg_conf DESC
    """
    result = client.query(query, parameters={"tid": take_id})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]
