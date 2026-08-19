"""Registry sanity — every engine points at a Google Cloud provider."""

from __future__ import annotations

from continuum.vision.registry import ENGINE_REGISTRY, engines_supporting

ALLOWED_PROVIDERS = {
    "google-cloud-videointelligence",
    "google-genai",
    "google-cloud-aiplatform",
}


def test_all_engines_are_google_cloud():
    for spec in ENGINE_REGISTRY.values():
        assert spec.provider in ALLOWED_PROVIDERS, (
            f"Engine {spec.key} uses non-Google provider {spec.provider} "
            "— hackathon rules forbid other AI providers."
        )


def test_video_intelligence_supports_expected_features():
    vi = ENGINE_REGISTRY["video_intelligence"]
    for f in (
        "SHOT_CHANGE_DETECTION",
        "OBJECT_TRACKING",
        "FACE_DETECTION",
        "LABEL_DETECTION",
        "TEXT_DETECTION",
        "SPEECH_TRANSCRIPTION",
    ):
        assert f in vi.features


def test_engines_supporting_lookup():
    matches = engines_supporting("OBJECT_TRACKING")
    assert any(m.key == "video_intelligence" for m in matches)
    assert not engines_supporting("NOT_A_REAL_FEATURE")
