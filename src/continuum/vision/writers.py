# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""ClickHouse writers — take an EngineResult and INSERT its rows.

Kept separate from the engines so tests can exercise engines against a
`FakeWriter` (see tests/vision/) without a live ClickHouse.
"""

from __future__ import annotations

from typing import Any, Protocol

from continuum.vision.engines.base import EngineResult


class WriteSink(Protocol):
    """Minimal interface a writer needs. `clickhouse_connect.Client` fits."""

    def insert(  # pragma: no cover - protocol
        self, table: str, data: list[list[Any]], column_names: list[str]
    ) -> Any: ...


_OBS_COLUMNS = [
    "obs_id", "production_id", "take_id", "asset_id", "scene_id",
    "feature", "ts_ms", "end_ms",
    "entity_kind", "entity_id", "entity_label",
    "payload", "source_model", "confidence", "epistemic",
]

_DIALOGUE_COLUMNS = [
    "obs_id", "production_id", "take_id", "asset_id", "scene_id",
    "segment_index", "ts_ms", "end_ms",
    "speaker_tag", "transcript", "confidence",
    "source_model", "epistemic",
]

_VERDICT_COLUMNS = [
    "verdict_id", "production_id", "take_id", "asset_id", "scene_id",
    "question", "verdict", "evidence", "confidence",
    "source_model", "epistemic",
]

_EMBEDDING_COLUMNS = [
    "obs_id", "production_id", "take_id", "asset_id",
    "ts_ms", "embedding", "source_model",
]


def _rows(dicts: list[dict[str, Any]], cols: list[str]) -> list[list[Any]]:
    return [[d.get(c) for c in cols] for d in dicts]


def write_result(sink: WriteSink, result: EngineResult) -> dict[str, int]:
    """Insert every table the result contributes to. Returns counts by table."""
    counts: dict[str, int] = {}

    if result.observations:
        sink.insert(
            "continuum.frame_observations",
            _rows(result.observations, _OBS_COLUMNS),
            _OBS_COLUMNS,
        )
        counts["frame_observations"] = len(result.observations)

    if result.dialogue:
        sink.insert(
            "continuum.take_dialogue",
            _rows(result.dialogue, _DIALOGUE_COLUMNS),
            _DIALOGUE_COLUMNS,
        )
        counts["take_dialogue"] = len(result.dialogue)

    if result.verdicts:
        sink.insert(
            "continuum.vision_verdicts",
            _rows(result.verdicts, _VERDICT_COLUMNS),
            _VERDICT_COLUMNS,
        )
        counts["vision_verdicts"] = len(result.verdicts)

    if result.embeddings:
        sink.insert(
            "continuum.frame_embeddings",
            _rows(result.embeddings, _EMBEDDING_COLUMNS),
            _EMBEDDING_COLUMNS,
        )
        counts["frame_embeddings"] = len(result.embeddings)

    return counts
