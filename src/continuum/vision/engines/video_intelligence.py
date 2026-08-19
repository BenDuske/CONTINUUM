# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Video Intelligence engine — long-running analysis of take video assets.

STUB mode reads a canned fixture so pipelines can be exercised end-to-end
without Google quota. REAL mode issues an `annotate_video` operation and
polls until completion, then normalizes VI's response into the row shape
that `writers.observations_to_rows` expects.
"""

from __future__ import annotations

import uuid
from typing import Any

from continuum.vision.engines.base import Engine, EngineMode, EngineResult
from continuum.vision.provenance import EpistemicLayer, Provenance
from continuum.vision.registry import ENGINE_REGISTRY
from continuum.vision.stubs.fixtures import video_intelligence_fixture


class VideoIntelligenceEngine(Engine):
    key = "video_intelligence"

    def __init__(self, mode: EngineMode = EngineMode.STUB):
        super().__init__(mode=mode)
        self._spec = ENGINE_REGISTRY[self.key]

    async def analyze(
        self,
        *,
        asset: dict[str, Any],
        features: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> EngineResult:
        requested = tuple(features) if features else self._spec.features
        provenance = Provenance(
            source_model=self._spec.source_model,
            engine=self.key,
            engine_mode=self.mode.value,
            epistemic=EpistemicLayer.OBSERVED,
            confidence=1.0,
            extra={"requested_features": list(requested)},
        )

        if self._is_real():
            payload = await self._call_video_intelligence(asset, requested)
        else:
            payload = video_intelligence_fixture(asset=asset, features=requested)

        return _payload_to_result(
            asset=asset,
            features=requested,
            payload=payload,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # Real Google Cloud call — kept in its own method so the STUB path
    # never imports the heavy SDK.
    # ------------------------------------------------------------------
    async def _call_video_intelligence(
        self, asset: dict[str, Any], features: tuple[str, ...]
    ) -> dict[str, Any]:
        from google.cloud import videointelligence  # type: ignore

        from continuum.vision.clients import video_intelligence_client

        client = video_intelligence_client()
        feature_enums = [
            getattr(videointelligence.Feature, f) for f in features
        ]
        request = {
            "input_uri": asset["gcs_uri"],
            "features": feature_enums,
        }
        operation = client.annotate_video(request=request)
        # VI operations can take minutes. `operation.result` blocks; called
        # inside an async context we release the loop briefly.
        import asyncio

        response = await asyncio.to_thread(operation.result, timeout=600)
        return _vi_response_to_dict(response)


# ----------------------------------------------------------------------
# Response normalization — same shape whether we came from stub or real.
# ----------------------------------------------------------------------
def _payload_to_result(
    *,
    asset: dict[str, Any],
    features: tuple[str, ...],
    payload: dict[str, Any],
    provenance: Provenance,
) -> EngineResult:
    obs: list[dict[str, Any]] = []
    dialogue: list[dict[str, Any]] = []

    scene_id = asset.get("scene_id", "")
    prod_id = asset["production_id"]
    take_id = asset["take_id"]
    asset_id = asset["asset_id"]

    for shot in payload.get("shots", []):
        obs.append(_row(
            prod_id, take_id, asset_id, scene_id,
            feature="shot",
            ts_ms=shot["start_ms"],
            end_ms=shot["end_ms"],
            entity_kind="shot",
            entity_id=f"shot:{shot['index']}",
            entity_label=f"Shot {shot['index']}",
            payload=shot,
            provenance=provenance,
            confidence=1.0,
        ))

    for track in payload.get("object_tracks", []):
        obs.append(_row(
            prod_id, take_id, asset_id, scene_id,
            feature="object",
            ts_ms=track["start_ms"],
            end_ms=track["end_ms"],
            entity_kind="prop",
            entity_id=f"object:{track['label']}",
            entity_label=track["label"],
            payload=track,
            provenance=provenance,
            confidence=float(track.get("confidence", 0.0)),
        ))

    for face in payload.get("faces", []):
        obs.append(_row(
            prod_id, take_id, asset_id, scene_id,
            feature="face",
            ts_ms=face["start_ms"],
            end_ms=face["end_ms"],
            entity_kind="face",
            entity_id=f"face:{face['track_id']}",
            entity_label=face.get("label", "unknown"),
            payload=face,
            provenance=provenance,
            confidence=float(face.get("confidence", 0.0)),
        ))

    for label in payload.get("labels", []):
        obs.append(_row(
            prod_id, take_id, asset_id, scene_id,
            feature="label",
            ts_ms=label.get("start_ms", 0),
            end_ms=label.get("end_ms", 0),
            entity_kind="label",
            entity_id=f"label:{label['description']}",
            entity_label=label["description"],
            payload=label,
            provenance=provenance,
            confidence=float(label.get("confidence", 0.0)),
        ))

    for text in payload.get("text", []):
        obs.append(_row(
            prod_id, take_id, asset_id, scene_id,
            feature="text",
            ts_ms=text["start_ms"],
            end_ms=text["end_ms"],
            entity_kind="ocr_text",
            entity_id=f"text:{text['text'][:32]}",
            entity_label=text["text"],
            payload=text,
            provenance=provenance,
            confidence=float(text.get("confidence", 0.0)),
        ))

    for seg in payload.get("speech", []):
        dialogue.append({
            "obs_id": str(uuid.uuid4()),
            "production_id": prod_id,
            "take_id": take_id,
            "asset_id": asset_id,
            "scene_id": scene_id,
            "segment_index": seg["segment_index"],
            "ts_ms": seg["start_ms"],
            "end_ms": seg["end_ms"],
            "speaker_tag": int(seg.get("speaker_tag", -1)),
            "transcript": seg["transcript"],
            "confidence": float(seg.get("confidence", 0.0)),
            **provenance.to_row(),
        })

    for safety in payload.get("safety", []):
        obs.append(_row(
            prod_id, take_id, asset_id, scene_id,
            feature="safety",
            ts_ms=safety.get("ts_ms", 0),
            end_ms=safety.get("ts_ms", 0),
            entity_kind="safety_flag",
            entity_id=f"safety:{safety['category']}",
            entity_label=safety["category"],
            payload=safety,
            provenance=provenance,
            confidence=float(safety.get("confidence", 0.0)),
        ))

    return EngineResult(
        engine="video_intelligence",
        mode=EngineMode(provenance.engine_mode),
        provenance=provenance,
        observations=obs,
        dialogue=dialogue,
    )


def _row(
    prod_id: str,
    take_id: str,
    asset_id: str,
    scene_id: str,
    *,
    feature: str,
    ts_ms: int,
    end_ms: int,
    entity_kind: str,
    entity_id: str,
    entity_label: str,
    payload: dict[str, Any],
    provenance: Provenance,
    confidence: float,
) -> dict[str, Any]:
    import json

    return {
        "obs_id": str(uuid.uuid4()),
        "production_id": prod_id,
        "take_id": take_id,
        "asset_id": asset_id,
        "scene_id": scene_id,
        "feature": feature,
        "ts_ms": int(ts_ms),
        "end_ms": int(end_ms),
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "entity_label": entity_label,
        "payload": json.dumps(payload, sort_keys=True),
        "source_model": provenance.source_model,
        "confidence": float(confidence),
        "epistemic": provenance.epistemic.value,
    }


def _vi_response_to_dict(response: Any) -> dict[str, Any]:
    """Convert a VI AnnotateVideoResponse into the flat dict our normalizer
    expects. Kept minimal — extend as more feature types are wired in.
    """
    out: dict[str, Any] = {
        "shots": [],
        "object_tracks": [],
        "faces": [],
        "labels": [],
        "text": [],
        "speech": [],
        "safety": [],
    }

    if not response.annotation_results:
        return out
    annot = response.annotation_results[0]

    for idx, shot in enumerate(getattr(annot, "shot_annotations", []) or []):
        out["shots"].append({
            "index": idx,
            "start_ms": _td_to_ms(shot.start_time_offset),
            "end_ms": _td_to_ms(shot.end_time_offset),
        })

    for track in getattr(annot, "object_annotations", []) or []:
        segs = track.segment
        out["object_tracks"].append({
            "label": track.entity.description,
            "confidence": track.confidence,
            "start_ms": _td_to_ms(segs.start_time_offset),
            "end_ms": _td_to_ms(segs.end_time_offset),
        })

    for face in getattr(annot, "face_detection_annotations", []) or []:
        for i, track in enumerate(face.tracks):
            out["faces"].append({
                "track_id": i,
                "start_ms": _td_to_ms(track.segment.start_time_offset),
                "end_ms": _td_to_ms(track.segment.end_time_offset),
                "confidence": track.confidence,
                "label": "unknown",
            })

    for label in getattr(annot, "segment_label_annotations", []) or []:
        for seg in label.segments:
            out["labels"].append({
                "description": label.entity.description,
                "confidence": seg.confidence,
                "start_ms": _td_to_ms(seg.segment.start_time_offset),
                "end_ms": _td_to_ms(seg.segment.end_time_offset),
            })

    for text in getattr(annot, "text_annotations", []) or []:
        for seg in text.segments:
            out["text"].append({
                "text": text.text,
                "confidence": seg.confidence,
                "start_ms": _td_to_ms(seg.segment.start_time_offset),
                "end_ms": _td_to_ms(seg.segment.end_time_offset),
            })

    if getattr(annot, "speech_transcriptions", None):
        seg_idx = 0
        for trans in annot.speech_transcriptions:
            for alt in trans.alternatives:
                if not alt.words:
                    continue
                out["speech"].append({
                    "segment_index": seg_idx,
                    "transcript": alt.transcript,
                    "confidence": alt.confidence,
                    "start_ms": _td_to_ms(alt.words[0].start_time),
                    "end_ms": _td_to_ms(alt.words[-1].end_time),
                    "speaker_tag": getattr(alt.words[0], "speaker_tag", -1),
                })
                seg_idx += 1

    for flag in getattr(annot, "explicit_annotation", None).frames or [] \
            if getattr(annot, "explicit_annotation", None) else []:
        out["safety"].append({
            "category": "explicit",
            "confidence": float(flag.pornography_likelihood),
            "ts_ms": _td_to_ms(flag.time_offset),
        })

    return out


def _td_to_ms(td: Any) -> int:
    """protobuf.Duration -> milliseconds."""
    if td is None:
        return 0
    return int(getattr(td, "seconds", 0) * 1000 + getattr(td, "nanos", 0) // 1_000_000)
