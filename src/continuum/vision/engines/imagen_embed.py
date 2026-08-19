# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Imagen 3 multimodal-embedding engine.

Produces 1408-dim vectors for keyframes / stills that CASCADE uses to find
"nearest frames" when a scene changes (e.g. "which shots look like the
current apartment set?").
"""

from __future__ import annotations

import uuid
from typing import Any

from continuum.vision.engines.base import Engine, EngineMode, EngineResult
from continuum.vision.provenance import EpistemicLayer, Provenance
from continuum.vision.registry import ENGINE_REGISTRY
from continuum.vision.stubs.fixtures import imagen_embedding_fixture


class ImagenEmbedEngine(Engine):
    key = "imagen_embed"

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
        provenance = Provenance(
            source_model=self._spec.source_model,
            engine=self.key,
            engine_mode=self.mode.value,
            epistemic=EpistemicLayer.OBSERVED,
            confidence=1.0,
        )

        if self._is_real():
            embedding = await self._call_vertex(asset)
        else:
            embedding = imagen_embedding_fixture(asset)

        row = {
            "obs_id": str(uuid.uuid4()),
            "production_id": asset["production_id"],
            "take_id": asset["take_id"],
            "asset_id": asset["asset_id"],
            "ts_ms": int(context.get("ts_ms", 0)) if context else 0,
            "embedding": embedding,
            "source_model": provenance.source_model,
        }
        return EngineResult(
            engine=self.key,
            mode=self.mode,
            provenance=provenance,
            embeddings=[row],
        )

    async def _call_vertex(self, asset: dict[str, Any]) -> list[float]:
        from vertexai.vision_models import Image, MultiModalEmbeddingModel  # type: ignore

        from continuum.vision.clients import vertex_prediction_client

        vertex_prediction_client()  # ensures aiplatform.init has run
        model = MultiModalEmbeddingModel.from_pretrained(self._spec.source_model)
        image = Image.load_from_file(asset["gcs_uri"])
        result = model.get_embeddings(image=image, dimension=1408)
        return list(result.image_embedding)
