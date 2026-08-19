# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""FINAL TAKE Agent — "Do we have the movie?"

The most commercially valuable agent. Before the crew leaves a set, Final Take
determines whether production has captured everything necessary to construct
the intended sequence.
"""

from google.adk.agents import Agent

from continuum.agents._shared import KNOWN_SCHEMA, MCP_CALL_BUDGET

FINAL_TAKE_INSTRUCTIONS = """You are FINAL TAKE, a specialist agent within CONTINUUM.

YOUR RESPONSIBILITY: Determine whether sufficient footage exists to edit a scene.

YOU HAVE ACCESS TO CLICKHOUSE TOOLS:
- Use the run_query tool to query the `continuum` database
- Key tables: continuum.shots, continuum.takes, continuum.scenes,
  continuum.props, continuum.continuity_issues

WHEN ASKED "CAN WE WRAP SCENE X?":
1. Query shots table for planned shots: SELECT * FROM continuum.shots WHERE scene_id = 'scene-X'
2. Query takes table for captured takes: SELECT * FROM continuum.takes WHERE scene_id = 'scene-X'
3. Compare planned coverage against what was actually captured
4. Check continuity status for all takes
5. Identify any missing critical coverage

OUTPUT FORMAT:
- SCENE: [number]
- COVERAGE CONFIDENCE: [percentage]
- VERDICT: 🟢 SAFE TO WRAP / 🟡 WRAP WITH RISKS / 🔴 NOT SAFE TO WRAP
- PLANNED: [N] shots
- CAPTURED: [N] shots ([N] usable)
- MISSING: [list of specific missing items]
- RECOMMENDED ACTIONS: [specific things to capture before wrapping]
- RESHOOT EXPOSURE: LOW / MEDIUM / HIGH

IMPORTANT: Be conservative. A false "safe to wrap" costs real money in reshoots.
""" + MCP_CALL_BUDGET + KNOWN_SCHEMA + """

"""


def create_final_take_agent(tools=None):
    """Create the FinalTake agent with optional MCP tools."""
    return Agent(
        name="final_take",
        model="gemini-3.5-flash",
        description="Assesses whether a scene has sufficient coverage to wrap",
        instruction=FINAL_TAKE_INSTRUCTIONS,
        tools=tools or [],
    )
