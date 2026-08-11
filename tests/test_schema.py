"""Basic tests for CONTINUUM schema models."""

from continuum.schema.models import (
    CoverageAssessment,
    EpistemicState,
    ProductionEvent,
    Scene,
    Severity,
    Take,
    TakeRating,
)


def test_production_event_creation():
    event = ProductionEvent(
        event_id="evt-001",
        production_id="tls-001",
        timestamp="2026-08-15T14:03:22",
        event_type="TAKE_CAPTURED",
        entity_type="take",
        entity_id="take-42a-3",
        data={"camera": "A", "lens": "50mm"},
    )
    assert event.event_type == "TAKE_CAPTURED"
    assert event.epistemic == EpistemicState.OBSERVED


def test_scene_creation():
    scene = Scene(
        scene_id="scene-42",
        production_id="tls-001",
        scene_number=42,
        slug="INT. SARAH'S APARTMENT — NIGHT",
        characters=["Sarah Chen"],
        props=["Camera P-14"],
    )
    assert scene.scene_number == 42
    assert "Sarah Chen" in scene.characters
    assert not scene.wrapped


def test_coverage_assessment():
    assessment = CoverageAssessment(
        scene_id="scene-42",
        planned_shots=12,
        captured_shots=11,
        usable_takes=9,
        audio_verified=8,
        continuity_verified=10,
        director_selects=7,
        coverage_confidence=0.73,
        missing=["Sarah reaction CU", "clean plate", "room tone"],
        safe_to_wrap=False,
        recommendation="Capture Sarah CU + clean plate + room tone before wrap.",
    )
    assert not assessment.safe_to_wrap
    assert assessment.coverage_confidence == 0.73
    assert len(assessment.missing) == 3


def test_take_rating_enum():
    take = Take(
        take_id="take-42a-3",
        scene_id="scene-42",
        shot_id="shot-42a",
        take_number=3,
        rating=TakeRating.SELECT,
        audio_clean=True,
    )
    assert take.rating == TakeRating.SELECT
