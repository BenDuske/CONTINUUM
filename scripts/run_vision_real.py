# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Run the vision subsystem end-to-end in REAL mode against a GCS take asset.

Fires all three Google Cloud engines and prints what would be inserted into
ClickHouse — no DB writes (dry-run) unless --write is passed.

Usage:
    python scripts/run_vision_real.py                            # demo asset
    python scripts/run_vision_real.py --gcs gs://bucket/path.mp4
    python scripts/run_vision_real.py --engine video_intelligence
    python scripts/run_vision_real.py --write                    # actually insert to ClickHouse

Requires env (already set at USER scope on Halcyon by the audit run):
    GOOGLE_APPLICATION_CREDENTIALS
    GOOGLE_CLOUD_PROJECT
    CONTINUUM_VISION_LOCATION
    CONTINUUM_GEMINI_BACKEND=vertex           (or omit to use GOOGLE_GENAI_API_KEY)
    CONTINUUM_GCS_BUCKET
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure src/ is importable when run directly.
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from continuum.vision.engines.base import EngineMode  # noqa: E402
from continuum.vision.ingest import ingest_asset  # noqa: E402

DEMO_ASSET = {
    "production_id": "tls-001",
    "take_id": "take-42-03",
    "asset_id": "asset-42-03-A",
    "scene_id": "scene-42",
    "gcs_uri": "gs://continuum-tls-001-assets/tls-001/scene-42/take-03.mp4",
    "mime_type": "video/mp4",
}


def build_sink():
    """Return a ClickHouse writer sink or None for dry-run."""
    try:
        import clickhouse_connect
        return clickhouse_connect.get_client(
            host=os.environ["CLICKHOUSE_HOST"],
            port=int(os.environ.get("CLICKHOUSE_PORT", "8443")),
            username=os.environ.get("CLICKHOUSE_USER", "default"),
            password=os.environ["CLICKHOUSE_PASSWORD"],
            secure=os.environ.get("CLICKHOUSE_SECURE", "true").lower() == "true",
            database=os.environ.get("CLICKHOUSE_DATABASE", "continuum"),
        )
    except (KeyError, ImportError) as e:
        print(f"[warn] ClickHouse sink unavailable ({e}); running dry-run.")
        return None


async def run_one(engine_key: str, asset: dict, context: dict | None, sink) -> dict:
    t0 = time.perf_counter()
    report = await ingest_asset(
        asset=asset,
        engine_key=engine_key,
        context=context,
        sink=sink,
        mode=EngineMode.REAL,
    )
    elapsed = time.perf_counter() - t0
    return {
        "engine": engine_key,
        "state": report.state,
        "written": report.written,
        "elapsed_s": round(elapsed, 2),
        "error": report.error,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcs", help="Override gcs_uri (defaults to the TLS-001 demo asset)")
    parser.add_argument("--engine", choices=["video_intelligence", "gemini_multimodal",
                                              "imagen_embed", "all"],
                        default="all")
    parser.add_argument("--write", action="store_true",
                        help="Insert into ClickHouse (default dry-run).")
    args = parser.parse_args()

    if os.environ.get("CONTINUUM_VISION_ENGINE_MODE", "stub").lower() != "real":
        os.environ["CONTINUUM_VISION_ENGINE_MODE"] = "real"

    asset = dict(DEMO_ASSET)
    if args.gcs:
        asset["gcs_uri"] = args.gcs
    sink = build_sink() if args.write else None

    ctx_gemini = {
        "question": "Does the camera prop visible in this take show damage "
                    "(cracked lens or dented body)?",
        "screenplay_excerpt": (
            "Scene 42, INT. SARAH'S APARTMENT - DUSK. Sarah enters holding "
            "the camera she dropped in Scene 31. The damage from the fall "
            "should be visible: cracked lens, dented body."
        ),
    }

    engines = ["video_intelligence", "gemini_multimodal", "imagen_embed"] \
        if args.engine == "all" else [args.engine]

    results = []
    for e in engines:
        ctx = ctx_gemini if e == "gemini_multimodal" else None
        try:
            r = await run_one(e, asset, ctx, sink)
        except Exception as exc:  # engine errors propagate; report them
            r = {"engine": e, "state": "failed", "error": f"{type(exc).__name__}: {exc}"}
        results.append(r)
        print(json.dumps(r, indent=2))

    print("\n--- SUMMARY ---")
    for r in results:
        print(f"  {r['engine']:22} {r.get('state','?'):10} {r.get('written',{})}")


if __name__ == "__main__":
    asyncio.run(main())
