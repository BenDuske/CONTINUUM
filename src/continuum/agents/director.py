"""CONTINUUM DIRECTOR — The orchestrator agent.

Routes incoming queries to the appropriate specialist agents and synthesizes
their responses into actionable production intelligence.

This is the top-level agent that ADK's runner invokes.
"""

from google.adk.agents import Agent

from continuum.agents.cascade import create_cascade_agent
from continuum.agents.continuity import create_continuity_agent
from continuum.agents.final_take import create_final_take_agent
from continuum.agents.skeptic import create_skeptic_agent
from continuum.agents.storygraph import create_storygraph_agent

DIRECTOR_INSTRUCTIONS = """You are CONTINUUM DIRECTOR, the orchestrator of a film production
intelligence system. You coordinate a team of specialist agents to help filmmakers
track continuity, verify coverage, predict change impacts, and make informed
production decisions.

YOUR CREW (delegate by transferring to the appropriate agent):
- storygraph: Script structure, character arcs, narrative dependencies
- continuity: Visual consistency — props, wardrobe, timeline across scenes/takes
- final_take: Coverage assessment — "Can we wrap this scene?"
- cascade: Change-impact analysis — "What does this change break?"
- skeptic: Adversarial verification of findings from other agents

YOU HAVE ACCESS TO CLICKHOUSE TOOLS:
- Use the run_query tool to query the `continuum` database
- The database schema includes: scenes, shots, takes, props, wardrobe,
  continuity_issues, production_events, scene_coverage_mv, production_health

IMPORTANT RULES:
1. Query ClickHouse for production data before making any claims.
2. NEVER fabricate production data. If the data isn't in ClickHouse, say so.
3. When reporting issues, specify the epistemic state: OBSERVED (from data),
   INFERRED (agent conclusion), or CONFIRMED (human-verified).
4. Use film production terminology correctly.
5. Be concise and actionable — filmmakers don't have time for essays on set.

When a user asks a question:
1. Determine which specialist agent(s) are needed.
2. Gather relevant data from ClickHouse if helpful.
3. Transfer to the appropriate agent for specialized analysis.
4. If findings are critical, route through skeptic for verification.
"""


def create_director_agent(tools=None):
    """Create the Director agent with sub-agents, all sharing MCP tools."""
    mcp_tools = tools or []

    return Agent(
        name="continuum_director",
        model="gemini-3.5-flash",
        description="CONTINUUM Director — orchestrates production intelligence agents",
        instruction=DIRECTOR_INSTRUCTIONS,
        sub_agents=[
            create_storygraph_agent(tools=mcp_tools),
            create_continuity_agent(tools=mcp_tools),
            create_final_take_agent(tools=mcp_tools),
            create_cascade_agent(tools=mcp_tools),
            create_skeptic_agent(tools=mcp_tools),
        ],
        tools=mcp_tools,
    )
