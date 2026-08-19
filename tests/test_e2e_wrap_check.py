"""E2E test for the signature demo — /api/production/{pid}/scene/{sid}/wrap-check.

This test exercises the whole HTTP surface end-to-end WITHOUT touching
ClickHouse Cloud or Gemini:

  FastAPI route
      → runner.run_wrap_check
          → runner.run_agent_query   (mocked — simulates the Gemini
                                      response that comes back after the
                                      agents inspect ClickHouse)
      → verdict reducer
      → JSON response body

The demo scenario is baked in: production tls-001, scene-42, damaged Camera
P-14, missing shots 42G+42H → verdict must come out NOT_SAFE_TO_WRAP. If
anything in the wiring drifts (route path, request contract, verdict
reducer, response shape), this test fails first.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from continuum import runner
from continuum.web.app import app


# The kind of narrative response Gemini produces after querying ClickHouse
# in the signature demo. Includes the shots/takes math + prop-state red flag.
DEMO_SCENE_42_RESPONSE = """\
SCENE: 42
COVERAGE CONFIDENCE: 75%
VERDICT: 🔴 NOT SAFE TO WRAP

PLANNED: 8 shots (42A through 42H)
CAPTURED: 6 shots (42A, 42B, 42C, 42D, 42E, 42F)
MISSING: 42G (medium of Sarah entering) and 42H (insert of damaged camera on the table)

CONTINUITY: Camera P-14 must show damage per Scene 31 events. All 6 captured
takes are consistent with damaged state. The 2 missing shots would need to
maintain the damaged state as well.

RECOMMENDATION: Do NOT wrap. Reshoot 42G and 42H before releasing the location.
"""


@pytest.fixture
def client():
    """FastAPI TestClient with runner.run_agent_query mocked out.

    Mocking at run_agent_query rather than run_wrap_check preserves the
    verdict-reducer code path — exactly what an E2E should exercise.
    """
    async def _fake_run_agent_query(query, user_id="production"):
        # Guardrail: the wrap-check runner MUST build a query that references
        # the specific scene + production. If someone breaks that in runner.py,
        # this assertion fails inside the mock and the test errors loudly.
        assert "scene-42" in query, "wrap-check query lost the scene_id"
        assert "tls-001" in query, "wrap-check query lost the production_id"
        return DEMO_SCENE_42_RESPONSE

    with patch.object(runner, "run_agent_query", side_effect=_fake_run_agent_query):
        with TestClient(app) as tc:
            yield tc


def test_scene_42_wrap_check_returns_not_safe_verdict(client):
    """The signature demo: wrap-check on scene-42 must refuse to wrap."""
    resp = client.post("/api/production/tls-001/scene/scene-42/wrap-check")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Contract with the frontend (dashboard.html reads these keys).
    assert body["verdict"] == "NOT_SAFE_TO_WRAP"
    assert body["scene_id"] == "scene-42"
    assert body["production_id"] == "tls-001"
    assert 0.0 <= body["coverage_confidence"] <= 1.0

    # The analysis narrative must survive — judges read this.
    assert "42G" in body["analysis"]
    assert "42H" in body["analysis"]
    assert "Camera P-14" in body["analysis"]


def test_wrap_check_response_shape_matches_frontend_contract(client):
    """Prevent silent renames of the JSON keys the dashboard consumes."""
    resp = client.post("/api/production/tls-001/scene/scene-42/wrap-check")
    body = resp.json()
    assert set(body.keys()) == {
        "scene_id",
        "production_id",
        "verdict",
        "coverage_confidence",
        "analysis",
    }


def test_wrap_check_route_path_is_stable():
    """The URL is documented in the README and the 3-min demo video will
    reference it. Any change to this path is a breaking change."""
    # This route (with these HTTP method + path params) MUST exist in the app.
    matching_routes = [
        r for r in app.routes
        if getattr(r, "path", None) == "/api/production/{production_id}/scene/{scene_id}/wrap-check"
        and "POST" in getattr(r, "methods", set())
    ]
    assert len(matching_routes) == 1, "wrap-check route missing or duplicated"
