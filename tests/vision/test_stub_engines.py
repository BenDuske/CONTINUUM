# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""End-to-end pipeline through every engine in stub mode.

Uses a FakeSink so the writers path is exercised without a live ClickHouse.
No Google network calls happen — stub mode only.
"""

from __future__ import annotations

from typing import Any

import pytest

from continuum.vision.engines.base import EngineMode
from continuum.vision.ingest import ingest_asset


class FakeSink:
    """Captures inserts so tests can assert on them."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[list[Any]], list[str]]] = []

    def insert(self, table: str, data: list[list[Any]], column_names: list[str]) -> None:
        self.calls.append((table, data, column_names))

    def tables(self) -> list[str]:
        return [c[0] for c in self.calls]


DEMO_ASSET = {
    "production_id": "tls-001",
    "take_id": "take-42-03",
    "asset_id": "asset-42-03-A",
    "scene_id": "scene-42",
    "gcs_uri": "gs://continuum-demo/tls-001/scene-42/take-03.mp4",
    "mime_type": "video/mp4",
}


@pytest.mark.asyncio
async def test_video_intelligence_stub_writes_expected_tables():
    sink = FakeSink()
    report = await ingest_asset(
        asset=DEMO_ASSET,
        engine_key="video_intelligence",
        features=[
            "SHOT_CHANGE_DETECTION",
            "OBJECT_TRACKING",
            "FACE_DETECTION",
            "LABEL_DETECTION",
            "TEXT_DETECTION",
            "SPEECH_TRANSCRIPTION",
        ],
        sink=sink,
        mode=EngineMode.STUB,
    )
    assert report.state == "succeeded"
    assert "continuum.frame_observations" in sink.tables()
    assert "continuum.take_dialogue" in sink.tables()
    # Demo asset must produce a camera object track — foundation for the wrap check.
    obs_call = next(c for c in sink.calls if c[0] == "continuum.frame_observations")
    labels = [row[obs_call[2].index("entity_label")] for row in obs_call[1]]
    assert "camera" in labels


@pytest.mark.asyncio
async def test_gemini_multimodal_stub_returns_damage_verdict():
    sink = FakeSink()
    report = await ingest_asset(
        asset=DEMO_ASSET,
        engine_key="gemini_multimodal",
        context={
            "question": "Does Camera P-14 show damage in this take?",
            "screenplay_excerpt": "Scene 42: SARAH enters her apartment holding the damaged camera.",
        },
        sink=sink,
        mode=EngineMode.STUB,
    )
    assert report.state == "succeeded"
    verdict_call = next(c for c in sink.calls if c[0] == "continuum.vision_verdicts")
    verdict_row = verdict_call[1][0]
    verdict_val = verdict_row[verdict_call[2].index("verdict")]
    conf_val = verdict_row[verdict_call[2].index("confidence")]
    assert verdict_val == "yes"
    assert conf_val > 0.8


@pytest.mark.asyncio
async def test_imagen_embed_stub_produces_1408_dim_unit_vector():
    sink = FakeSink()
    report = await ingest_asset(
        asset=DEMO_ASSET,
        engine_key="imagen_embed",
        sink=sink,
        mode=EngineMode.STUB,
    )
    assert report.state == "succeeded"
    embed_call = next(c for c in sink.calls if c[0] == "continuum.frame_embeddings")
    embedding = embed_call[1][0][embed_call[2].index("embedding")]
    assert len(embedding) == 1408
    norm = sum(x * x for x in embedding) ** 0.5
    assert abs(norm - 1.0) < 1e-4
