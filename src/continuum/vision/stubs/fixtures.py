# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Deterministic stub outputs.

Reflect the shapes real Google services would return, seeded by asset id so
tests can assert on stable values without any network call.
"""

from __future__ import annotations

import hashlib
from typing import Any


def _seed(asset: dict[str, Any]) -> int:
    key = f"{asset['production_id']}|{asset['take_id']}|{asset['asset_id']}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)


def video_intelligence_fixture(
    *, asset: dict[str, Any], features: tuple[str, ...] | list[str]
) -> dict[str, Any]:
    """Mimic a VI AnnotateVideoResponse in our normalized dict form.

    Uses the sample production's canonical demo asset (Scene 42, damaged
    Camera P-14) when the asset id ends in the demo marker, otherwise
    returns a minimal shot-only fixture.
    """
    seed = _seed(asset)
    features = tuple(features)
    is_demo = asset.get("scene_id") == "scene-42"

    out: dict[str, Any] = {
        "shots": [
            {"index": 0, "start_ms": 0, "end_ms": 4200},
            {"index": 1, "start_ms": 4200, "end_ms": 12800},
        ],
        "object_tracks": [],
        "faces": [],
        "labels": [],
        "text": [],
        "speech": [],
        "safety": [],
    }

    if "OBJECT_TRACKING" in features:
        out["object_tracks"].append({
            "label": "camera" if is_demo else "cup",
            "confidence": 0.87 if is_demo else 0.62,
            "start_ms": 1500,
            "end_ms": 12800,
        })

    if "FACE_DETECTION" in features:
        out["faces"].append({
            "track_id": 0,
            "start_ms": 0,
            "end_ms": 12800,
            "confidence": 0.94,
            "label": "sarah" if is_demo else "unknown",
        })

    if "LABEL_DETECTION" in features:
        out["labels"].append({
            "description": "apartment" if is_demo else "room",
            "confidence": 0.71,
            "start_ms": 0,
            "end_ms": 12800,
        })

    if "TEXT_DETECTION" in features and is_demo:
        out["text"].append({
            "text": "TLS-001 SC42 TK03",
            "confidence": 0.98,
            "start_ms": 0,
            "end_ms": 800,
        })

    if "SPEECH_TRANSCRIPTION" in features and is_demo:
        out["speech"].append({
            "segment_index": 0,
            "transcript": "The signal — it's back.",
            "confidence": 0.89,
            "start_ms": 5200,
            "end_ms": 7100,
            "speaker_tag": 1,
        })

    if "EXPLICIT_CONTENT_DETECTION" in features:
        out["safety"].append({
            "category": "explicit",
            "confidence": 0.02,
            "ts_ms": 0,
        })

    # Silence unused-warning while giving downstream code something deterministic.
    out["_seed"] = seed
    return out


def gemini_verdict_fixture(
    *, asset: dict[str, Any], question: str, screenplay: str
) -> dict[str, Any]:
    """Return a plausible structured verdict for the demo scenario."""
    is_demo = asset.get("scene_id") == "scene-42"
    q = question.lower()
    if is_demo and "damage" in q and "camera" in q:
        return {
            "verdict": "yes",
            "confidence": 0.91,
            "evidence": (
                "Frames 42-187 show a handheld camera prop with visible "
                "cracked glass on the left face and a dented top plate, "
                "consistent with the Scene 31 drop noted in the screenplay."
            ),
        }
    if is_demo and "actor" in q:
        return {
            "verdict": "yes",
            "confidence": 0.86,
            "evidence": "Face track 0 spans the take; features match Sarah.",
        }
    return {
        "verdict": "unclear",
        "confidence": 0.4,
        "evidence": "Stub verdict — insufficient signal for a strong claim.",
    }


def imagen_embedding_fixture(asset: dict[str, Any]) -> list[float]:
    """Deterministic 1408-dim vector, unit-scaled per asset."""
    seed = _seed(asset)
    # A tiny linear-congruential generator, kept in-file to avoid extra deps.
    vec: list[float] = []
    state = seed & 0xFFFFFFFF
    for _ in range(1408):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        vec.append((state / 0x7FFFFFFF) * 2.0 - 1.0)
    # L2-normalize so cosine similarity is meaningful in tests.
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]
