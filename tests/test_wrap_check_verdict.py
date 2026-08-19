# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Verdict-parsing tests for run_wrap_check.

`run_wrap_check` calls Gemini via ADK, then reduces the free-text response to a
structured verdict. The reducer is pure text logic — testable without hitting
the cloud. These tests pin the reducer's behavior so a stray edit to the
substring rules can't silently flip the demo's wrap/no-wrap outcome.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from continuum import runner


def _run_with_mocked_response(response_text: str) -> dict:
    """Call run_wrap_check but mock out the ADK/Gemini query."""

    async def _fake_run_agent_query(query, user_id="production"):
        return response_text

    import asyncio

    with patch.object(runner, "run_agent_query", side_effect=_fake_run_agent_query):
        return asyncio.run(runner.run_wrap_check("tls-001", "scene-42"))


@pytest.mark.parametrize(
    "response,expected_verdict,expected_conf",
    [
        # Signature demo path — Scene 42 damaged camera, missing coverage.
        (
            "SCENE: 42\nVERDICT: 🔴 NOT SAFE TO WRAP\nMissing shots 42G and 42H.",
            "NOT_SAFE_TO_WRAP",
            0.50,
        ),
        # Clean wrap.
        (
            "SCENE: 12\nVERDICT: 🟢 SAFE TO WRAP\nAll planned coverage captured.",
            "SAFE_TO_WRAP",
            0.90,
        ),
        # Middle ground.
        (
            "SCENE: 7\nVERDICT: 🟡 WRAP WITH RISKS\nCoverage complete but continuity flagged.",
            "WRAP_WITH_RISKS",
            0.70,
        ),
        # Adversarial: "safe to wrap" and "not safe" both present → NOT_SAFE_TO_WRAP wins.
        # Prevents a substring-order bug from silently green-lighting a bad scene.
        (
            "Analysis suggests it is NOT SAFE to wrap. It would be safe to wrap "
            "only after reshoots.",
            "NOT_SAFE_TO_WRAP",
            0.50,
        ),
        # No verdict phrase at all → default to NOT_SAFE_TO_WRAP (safety-first).
        (
            "The agent returned narrative analysis but no verdict phrase.",
            "NOT_SAFE_TO_WRAP",
            0.50,
        ),
        # Case insensitivity — verdict phrase in any case must be picked up.
        (
            "Safe To Wrap.",
            "SAFE_TO_WRAP",
            0.90,
        ),
    ],
)
def test_verdict_parsing(response, expected_verdict, expected_conf):
    result = _run_with_mocked_response(response)
    assert result["verdict"] == expected_verdict
    assert result["coverage_confidence"] == pytest.approx(expected_conf)
    assert result["scene_id"] == "scene-42"
    assert result["production_id"] == "tls-001"
    # Full analysis text must round-trip.
    assert result["analysis"] == response


def test_result_shape_is_stable():
    """The web API depends on these exact keys."""
    result = _run_with_mocked_response("🟢 SAFE TO WRAP")
    assert set(result.keys()) == {
        "scene_id",
        "production_id",
        "verdict",
        "coverage_confidence",
        "analysis",
    }
