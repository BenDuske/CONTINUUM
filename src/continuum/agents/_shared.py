# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Shared prompt fragments for all CONTINUUM agents.

Keeping these in one place means a schema addition or an MCP-call-budget
policy change lands in every agent's instructions on the next process
restart — no six-file sync problem.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# MCP call budget — the session-scoped "cache" is really a prompt-level
# instruction to skip the two round-trips that never change mid-session.
# --------------------------------------------------------------------------- #
MCP_CALL_BUDGET = """
MCP CALL BUDGET — the ClickHouse schema is FIXED. Do NOT call:
- `list_databases` — there is exactly one relevant database: `continuum`.
- `list_tables`    — the tables are enumerated below and in your Key tables
                     list; treat them as ground truth.

Every call to `list_databases` / `list_tables` adds a round-trip over the
MCP stdio pipe and slows the wrap-check demo. Go straight to `run_query`
with a fully-qualified table name (`continuum.<table>`)."""

# Every table in the Living Film Graph, kept in one authoritative place.
# Individual agents still name the SUBSET they care about in their own
# instructions — this constant is the union.
KNOWN_SCHEMA = """
KNOWN SCHEMA (database = `continuum`):

Core Living Film Graph:
- continuum.scenes                (scene_id, scene_number, slug, location, characters, ...)
- continuum.shots                 (shot_id, scene_id, shot_label, planned/captured, ...)
- continuum.takes                 (take_id, shot_id, scene_id, take_number, ...)
- continuum.props                 (prop_id, name, current_state, scenes[], ...)
- continuum.wardrobe              (character, scene_id, item, condition, ...)
- continuum.production_events     (timestamp, entity_type, entity_id, event, ...)
- continuum.continuity_issues     (issue_id, scene_id, category, severity, resolved, ...)
- continuum.scene_dependencies    (from_scene, to_scene, kind)

Vision subsystem (populated by scripts/run_vision_real.py):
- continuum.frame_observations    (take_id, ts_ms, kind, label, confidence, ...)
- continuum.take_dialogue         (take_id, speaker, ts_ms, text, ...)
- continuum.vision_verdicts       (take_id, question, verdict, confidence, ...)
- continuum.frame_embeddings      (take_id, ts_ms, embedding Array(Float32))

Materialized views:
- continuum.scene_coverage_mv     (per-scene captured / planned rollup)
- continuum.production_health     (top-level dashboard metrics)

Schema tracking (do not modify from agents):
- continuum.schema_migrations     (version, applied_at)
"""
