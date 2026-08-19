# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Vision engines — one per Google service, each with stub + real modes."""

from continuum.vision.engines.base import Engine, EngineMode, EngineResult
from continuum.vision.engines.gemini_multimodal import GeminiMultimodalEngine
from continuum.vision.engines.imagen_embed import ImagenEmbedEngine
from continuum.vision.engines.video_intelligence import VideoIntelligenceEngine

__all__ = [
    "Engine",
    "EngineMode",
    "EngineResult",
    "GeminiMultimodalEngine",
    "ImagenEmbedEngine",
    "VideoIntelligenceEngine",
]


def build_engine(key: str, mode: EngineMode = EngineMode.STUB) -> Engine:
    """Instantiate the engine matching a registry key."""
    if key == "video_intelligence":
        return VideoIntelligenceEngine(mode=mode)
    if key == "gemini_multimodal":
        return GeminiMultimodalEngine(mode=mode)
    if key == "imagen_embed":
        return ImagenEmbedEngine(mode=mode)
    raise KeyError(f"Unknown vision engine: {key}")
