# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Vision subsystem — Google Video Intelligence + Vertex AI multimodal glue.

The idea for this subsystem was inspired by our internal AVI pipeline, but had
to be completely redesigned to integrate Google's Vertex AI and Video
Intelligence. Every line here is new work written for the Contest Period.
"""

from continuum.vision.provenance import EpistemicLayer, Provenance
from continuum.vision.registry import ENGINE_REGISTRY, EngineSpec

__all__ = ["Provenance", "EpistemicLayer", "ENGINE_REGISTRY", "EngineSpec"]
