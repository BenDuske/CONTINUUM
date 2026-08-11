"""CONTINUUM Runner — Initializes and runs the ADK agent pipeline.

Connects the mcp-clickhouse MCP server to the agents, creates the runner,
and provides an async interface for the web app to invoke agent queries.

This is the runtime glue that makes CONTINUUM a real system, not a scaffold.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncGenerator

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import McpToolset
from google.genai import types

from continuum.agents.director import create_director_agent
from continuum.mcp.clickhouse_mcp import get_mcp_params

logger = logging.getLogger(__name__)

# Module-level state — initialized once, reused across requests
_runner: Runner | None = None
_session_service: InMemorySessionService | None = None
_mcp_toolset: McpToolset | None = None
_director: Agent | None = None
_init_lock = asyncio.Lock()


async def _ensure_initialized() -> Runner:
    """Lazily initialize the MCP toolset, agents, and runner."""
    global _runner, _session_service, _mcp_toolset, _director

    async with _init_lock:
        if _runner is not None:
            return _runner

        logger.info("Initializing CONTINUUM agent pipeline...")

        # Connect to mcp-clickhouse via stdio
        mcp_params = get_mcp_params()
        _mcp_toolset = McpToolset(connection_params=mcp_params)

        logger.info("Connected to mcp-clickhouse MCP server")

        # Create the director agent with MCP tools
        _director = create_director_agent(tools=[_mcp_toolset])

        # Create session service and runner with auto_create_session
        _session_service = InMemorySessionService()
        _runner = Runner(
            agent=_director,
            app_name="continuum",
            session_service=_session_service,
            auto_create_session=True,
        )

        logger.info("CONTINUUM agent pipeline ready")
        return _runner


async def run_agent_query(query: str, user_id: str = "production") -> str:
    """Run a query through the CONTINUUM agent pipeline.

    Args:
        query: Natural language query from the user.
        user_id: User identifier for session tracking.

    Returns:
        The agent's response text.
    """
    runner = await _ensure_initialized()

    # Each query gets a unique session
    session_id = f"session-{uuid.uuid4().hex[:8]}"

    # Build the user message
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    # Run the agent and collect response parts
    response_parts = []
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        # Collect text from agent responses (skip tool call/response events)
        if event.content and event.content.parts:
            for part in event.content.parts:
                # Check if this part has text (not a function call or response)
                text = getattr(part, "text", None)
                function_call = getattr(part, "function_call", None)
                function_response = getattr(part, "function_response", None)
                if text and not function_call and not function_response:
                    response_parts.append(text)
                    final_text = text  # Keep track of the last text

    # Return all collected text, or just the final response
    if response_parts:
        return "\n".join(response_parts)
    return "No response from agent pipeline."


async def run_wrap_check(production_id: str, scene_id: str) -> dict:
    """Run the FINAL TAKE wrap assessment for a scene.

    This is the signature feature — triggers the full agent pipeline.

    Args:
        production_id: The production ID (e.g., "tls-001").
        scene_id: The scene ID (e.g., "scene-42").

    Returns:
        Dict with verdict, confidence, and details.
    """
    query = f"""Run a FINAL TAKE wrap assessment for scene {scene_id} in production {production_id}.

First, query ClickHouse for:
1. All planned shots: SELECT * FROM continuum.shots WHERE scene_id = '{scene_id}' AND production_id = '{production_id}'
2. All captured takes: SELECT * FROM continuum.takes WHERE scene_id = '{scene_id}' AND production_id = '{production_id}'
3. All props in this scene: SELECT * FROM continuum.props WHERE production_id = '{production_id}' AND has(scenes, '{scene_id}')
4. Any existing continuity issues: SELECT * FROM continuum.continuity_issues WHERE scene_id = '{scene_id}' AND production_id = '{production_id}'

Then run the CONTINUITY check and FINAL TAKE coverage assessment.
Provide a clear WRAP / NO WRAP verdict with evidence."""

    response = await run_agent_query(query)

    # Parse a structured result from the response
    verdict = "NOT_SAFE_TO_WRAP"
    confidence = 0.0

    response_lower = response.lower()
    if "safe to wrap" in response_lower and "not safe" not in response_lower:
        verdict = "SAFE_TO_WRAP"
        confidence = 0.90
    elif "wrap with risks" in response_lower:
        verdict = "WRAP_WITH_RISKS"
        confidence = 0.70
    else:
        verdict = "NOT_SAFE_TO_WRAP"
        confidence = 0.50

    return {
        "scene_id": scene_id,
        "production_id": production_id,
        "verdict": verdict,
        "coverage_confidence": confidence,
        "analysis": response,
    }


async def run_continuity_check(production_id: str, scene_id: str) -> dict:
    """Run a continuity check for a scene.

    Args:
        production_id: The production ID.
        scene_id: The scene ID.

    Returns:
        Dict with continuity issues found.
    """
    query = f"""Run a CONTINUITY check for scene {scene_id} in production {production_id}.

Query ClickHouse for:
1. Scene details: SELECT * FROM continuum.scenes WHERE scene_id = '{scene_id}' AND production_id = '{production_id}'
2. Props in this scene: SELECT * FROM continuum.props WHERE production_id = '{production_id}' AND has(scenes, '{scene_id}')
3. Related scenes (story dependencies): Get the scene's story_dependencies, then query those scenes too
4. Production events for these props: SELECT * FROM continuum.production_events WHERE production_id = '{production_id}' AND entity_type = 'prop'

Check all prop states, wardrobe, and timeline consistency. Report any conflicts."""

    response = await run_agent_query(query)

    return {
        "scene_id": scene_id,
        "production_id": production_id,
        "analysis": response,
    }


async def run_cascade_analysis(production_id: str, change_description: str) -> dict:
    """Run a CASCADE change-impact analysis.

    Args:
        production_id: The production ID.
        change_description: What changed.

    Returns:
        Dict with impact analysis.
    """
    query = f"""Run a CASCADE change-impact analysis for production {production_id}.

The change: {change_description}

Query ClickHouse to trace all downstream impacts:
1. Find affected scenes: SELECT * FROM continuum.scenes WHERE production_id = '{production_id}'
2. Find affected props: SELECT * FROM continuum.props WHERE production_id = '{production_id}'
3. Find already-filmed takes: SELECT * FROM continuum.takes WHERE production_id = '{production_id}'
4. Check production event history: SELECT * FROM continuum.production_events WHERE production_id = '{production_id}' ORDER BY timestamp DESC

Identify all upstream (already filmed) and downstream (not yet filmed) impacts.
Provide resolution options."""

    response = await run_agent_query(query)

    return {
        "production_id": production_id,
        "change": change_description,
        "analysis": response,
    }


async def shutdown():
    """Clean up MCP connections."""
    global _runner, _session_service, _mcp_toolset, _director
    if _mcp_toolset:
        logger.info("Shutting down mcp-clickhouse connection...")
        _mcp_toolset = None
    _runner = None
    _session_service = None
    _director = None
