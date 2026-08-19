# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Lazy client factories for Google Cloud SDKs.

Kept lazy so importing the vision package (for tests / stub mode) does not
require the heavy Google Cloud dependencies to be present or authenticated.
"""

from __future__ import annotations

import functools
import os
from typing import Any


def _require_project() -> str:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Vision engines in 'real' mode "
            "require a Google Cloud project id."
        )
    return project


def _require_location() -> str:
    return os.environ.get("CONTINUUM_VISION_LOCATION", "us-central1")


@functools.lru_cache(maxsize=1)
def video_intelligence_client() -> Any:
    """Cloud Video Intelligence long-running client."""
    from google.cloud import videointelligence  # type: ignore
    return videointelligence.VideoIntelligenceServiceClient()


@functools.lru_cache(maxsize=1)
def vertex_prediction_client() -> Any:
    """Vertex AI prediction endpoint (Imagen embeddings live here)."""
    from google.cloud import aiplatform  # type: ignore
    aiplatform.init(project=_require_project(), location=_require_location())
    return aiplatform


@functools.lru_cache(maxsize=1)
def gemini_client() -> Any:
    """Google GenAI SDK client — supports Vertex or API-key backends.

    Backend is selected by env:
      - CONTINUUM_GEMINI_BACKEND=vertex -> uses project + location
      - otherwise -> API key (GOOGLE_GENAI_API_KEY)
    """
    from google import genai  # type: ignore

    backend = os.environ.get("CONTINUUM_GEMINI_BACKEND", "api_key").lower()
    if backend == "vertex":
        return genai.Client(
            vertexai=True,
            project=_require_project(),
            location=_require_location(),
        )
    api_key = os.environ.get("GOOGLE_GENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_GENAI_API_KEY is not set and CONTINUUM_GEMINI_BACKEND is not 'vertex'."
        )
    return genai.Client(api_key=api_key)


@functools.lru_cache(maxsize=1)
def storage_client() -> Any:
    """GCS client for reading take assets and writing provenance sidecars."""
    from google.cloud import storage  # type: ignore
    return storage.Client(project=_require_project())
