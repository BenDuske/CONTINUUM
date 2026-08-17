"""Provenance shape + epistemic mapping."""

from __future__ import annotations

from continuum.vision.provenance import EpistemicLayer, Provenance


def test_provenance_to_row_matches_clickhouse_columns():
    p = Provenance(
        source_model="videointelligence-v1p3beta1",
        engine="video_intelligence",
        engine_mode="stub",
        epistemic=EpistemicLayer.OBSERVED,
        confidence=0.87,
    )
    row = p.to_row()
    assert row == {
        "source_model": "videointelligence-v1p3beta1",
        "confidence": 0.87,
        "epistemic": "observed",
    }


def test_provenance_sidecar_serializable():
    p = Provenance(
        source_model="gemini-3.5-flash",
        engine="gemini_multimodal",
        engine_mode="stub",
        epistemic=EpistemicLayer.INFERRED,
        confidence=0.91,
        extra={"question": "Does Camera P-14 show damage?"},
    )
    side = p.to_sidecar()
    assert side["source_model"] == "gemini-3.5-flash"
    assert side["epistemic"] == "inferred"
    assert side["extra"]["question"].startswith("Does Camera")
    # generated_at should be an ISO-8601 string
    assert "T" in side["generated_at"]
