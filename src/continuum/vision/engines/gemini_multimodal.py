"""Gemini multimodal engine — asks Gemini 3.5 Flash structured questions
about a keyframe or short clip, given the relevant screenplay context.

Used by CONTINUITY to promote a claim from OBSERVED (Video Intelligence saw
an object) to INFERRED (the object appears in the required state — e.g. the
camera looks damaged). SKEPTIC then decides whether to CONFIRM.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from continuum.vision.engines.base import Engine, EngineMode, EngineResult
from continuum.vision.provenance import EpistemicLayer, Provenance
from continuum.vision.registry import ENGINE_REGISTRY
from continuum.vision.stubs.fixtures import gemini_verdict_fixture


_VERDICT_SCHEMA_INSTRUCTIONS = """You are a film continuity analyst. Given the
screenplay excerpt and the supplied media, answer the QUESTION.
Return STRICT JSON with fields:
  verdict:    "yes" | "no" | "unclear"
  confidence: number in [0, 1]
  evidence:   short paragraph citing which frames/timestamps or dialogue lines
              support the verdict.
Do not include any prose outside the JSON."""


class GeminiMultimodalEngine(Engine):
    key = "gemini_multimodal"

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
        context = context or {}
        question: str = context.get("question", "Describe what is visible.")
        screenplay: str = context.get("screenplay_excerpt", "")

        provenance = Provenance(
            source_model=self._spec.source_model,
            engine=self.key,
            engine_mode=self.mode.value,
            epistemic=EpistemicLayer.INFERRED,
            confidence=0.0,  # replaced with verdict confidence below
            extra={"question": question},
        )

        if self._is_real():
            verdict_json = await self._call_gemini(
                asset=asset, question=question, screenplay=screenplay
            )
        else:
            verdict_json = gemini_verdict_fixture(
                asset=asset, question=question, screenplay=screenplay
            )

        verdict = {
            "verdict_id": str(uuid.uuid4()),
            "production_id": asset["production_id"],
            "take_id": asset["take_id"],
            "asset_id": asset["asset_id"],
            "scene_id": asset.get("scene_id", ""),
            "question": question,
            "verdict": verdict_json.get("verdict", "unclear"),
            "evidence": json.dumps(verdict_json.get("evidence", ""), sort_keys=True),
            "confidence": float(verdict_json.get("confidence", 0.0)),
            "source_model": provenance.source_model,
            "epistemic": provenance.epistemic.value,
        }
        # Reflect the model's confidence into provenance so the sidecar matches.
        provenance = Provenance(
            source_model=provenance.source_model,
            engine=provenance.engine,
            engine_mode=provenance.engine_mode,
            epistemic=provenance.epistemic,
            confidence=verdict["confidence"],
            extra=provenance.extra,
        )
        return EngineResult(
            engine=self.key,
            mode=self.mode,
            provenance=provenance,
            verdicts=[verdict],
        )

    async def _call_gemini(
        self, *, asset: dict[str, Any], question: str, screenplay: str
    ) -> dict[str, Any]:
        from continuum.vision.clients import gemini_client

        client = gemini_client()
        parts: list[Any] = [
            {"text": _VERDICT_SCHEMA_INSTRUCTIONS},
            {"text": f"SCREENPLAY EXCERPT:\n{screenplay or '(none provided)'}"},
            {"text": f"QUESTION: {question}"},
            {"file_data": {"file_uri": asset["gcs_uri"], "mime_type": asset.get("mime_type", "video/mp4")}},
        ]
        response = client.models.generate_content(
            model=self._spec.source_model,
            contents=parts,
            config={"response_mime_type": "application/json"},
        )
        raw = getattr(response, "text", "") or ""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"verdict": "unclear", "confidence": 0.0, "evidence": raw[:512]}
