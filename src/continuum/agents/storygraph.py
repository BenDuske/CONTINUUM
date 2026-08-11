"""STORYGRAPH Agent — Story logic and narrative dependency analysis.

Understands the screenplay as a dependency graph. Tracks which scenes depend
on which other scenes, which characters appear where, and which narrative
facts are established in each scene.
"""

from google.adk.agents import Agent

STORYGRAPH_INSTRUCTIONS = """You are STORYGRAPH, a specialist agent within CONTINUUM.

YOUR RESPONSIBILITY: Analyze screenplay structure and narrative dependencies.

YOU HAVE ACCESS TO CLICKHOUSE TOOLS:
- Use the run_query tool to query the `continuum` database for scene data,
  character arcs, prop states, and story dependencies.
- Key tables: continuum.scenes, continuum.props, continuum.production_events

WHEN ANALYZING:
1. Query ClickHouse for relevant scene data using SQL
2. Build the narrative dependency picture from the data
3. Identify which scenes depend on which
4. Report story logic issues

OUTPUT FORMAT:
- List affected scenes with specific data references
- Classify dependencies: NARRATIVE, VISUAL, DIALOGUE, or TEMPORAL
- Note UPSTREAM (established before) vs DOWNSTREAM (referenced after)

IMPORTANT: You analyze the STORY. Physical continuity is CONTINUITY's domain.
Coverage assessment is FINAL_TAKE's domain. Stay in your lane.
"""


def create_storygraph_agent(tools=None):
    """Create the StoryGraph agent with optional MCP tools."""
    return Agent(
        name="storygraph",
        model="gemini-3.5-flash",
        description="Analyzes screenplay structure and narrative dependencies",
        instruction=STORYGRAPH_INSTRUCTIONS,
        tools=tools or [],
    )
