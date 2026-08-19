"""Capability registry — declares what each vision engine can do.

Consulted by `ingest.py` to route a job to the right engine, and by the
`vision_tools` module so agents can introspect available capabilities before
requesting them. Keeping this table explicit makes quota planning and stub /
real swapping obvious.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineSpec:
    """Describes one vision engine — inputs, outputs, and its runtime cost."""
    key: str                         # e.g. "video_intelligence"
    provider: str                    # always a Google service for compliance
    source_model: str                # exact model / API version string
    features: tuple[str, ...]        # feature flags this engine can emit
    input_mime_types: tuple[str, ...]  # e.g. ("video/mp4",)
    max_input_bytes: int             # soft cap; larger inputs must be chunked
    typical_latency_s: float         # rough expectation for planning
    quota_hint: str                  # human-readable, e.g. "600 req/min per project"
    notes: str = ""


ENGINE_REGISTRY: dict[str, EngineSpec] = {
    "video_intelligence": EngineSpec(
        key="video_intelligence",
        provider="google-cloud-videointelligence",
        source_model="videointelligence-v1p3beta1",
        features=(
            "SHOT_CHANGE_DETECTION",
            "OBJECT_TRACKING",
            "FACE_DETECTION",
            "PERSON_DETECTION",
            "LABEL_DETECTION",
            "TEXT_DETECTION",
            "SPEECH_TRANSCRIPTION",
            "EXPLICIT_CONTENT_DETECTION",
        ),
        input_mime_types=("video/mp4", "video/quicktime", "video/x-matroska"),
        max_input_bytes=2 * 1024 * 1024 * 1024,  # 2 GiB per VI docs
        typical_latency_s=60.0,
        quota_hint="Long-running operation; 600 req/min per project by default",
    ),
    "gemini_multimodal": EngineSpec(
        key="gemini_multimodal",
        provider="google-genai",
        source_model="gemini-3.5-flash",
        features=("KEYFRAME_VERDICT", "SCENE_MATCH", "PROP_STATE_CHECK"),
        input_mime_types=("image/jpeg", "image/png", "video/mp4"),
        max_input_bytes=20 * 1024 * 1024,        # 20 MiB per Gemini file limit
        typical_latency_s=3.0,
        quota_hint="Gemini RPM per project; check console",
    ),
    "imagen_embed": EngineSpec(
        key="imagen_embed",
        provider="google-cloud-aiplatform",
        source_model="multimodalembedding@001",
        features=("IMAGE_EMBEDDING",),
        input_mime_types=("image/jpeg", "image/png"),
        max_input_bytes=20 * 1024 * 1024,
        typical_latency_s=1.5,
        quota_hint="Vertex AI multimodal embeddings quota",
        notes="Emits 1408-dim vectors into continuum.frame_embeddings",
    ),
}


def list_features() -> dict[str, tuple[str, ...]]:
    """Return {engine_key: features} — used by agent tool introspection."""
    return {k: v.features for k, v in ENGINE_REGISTRY.items()}


def engines_supporting(feature: str) -> list[EngineSpec]:
    """Which engines can emit this feature."""
    return [spec for spec in ENGINE_REGISTRY.values() if feature in spec.features]
