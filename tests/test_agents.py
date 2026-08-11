"""Tests for CONTINUUM agent creation and configuration."""

from google.adk.agents import Agent

from continuum.agents.director import create_director_agent
from continuum.agents.storygraph import create_storygraph_agent
from continuum.agents.continuity import create_continuity_agent
from continuum.agents.final_take import create_final_take_agent
from continuum.agents.cascade import create_cascade_agent
from continuum.agents.skeptic import create_skeptic_agent


def test_all_agents_use_gemini():
    """Every agent must use gemini-3.5-flash (hackathon AI restriction)."""
    agents = [
        create_storygraph_agent(),
        create_continuity_agent(),
        create_final_take_agent(),
        create_cascade_agent(),
        create_skeptic_agent(),
    ]
    for agent in agents:
        assert agent.model == "gemini-3.5-flash", f"{agent.name} uses wrong model"


def test_director_has_all_sub_agents():
    """Director must have all 5 specialist sub-agents."""
    director = create_director_agent()
    sub_names = {a.name for a in director.sub_agents}
    expected = {"storygraph", "continuity", "final_take", "cascade", "skeptic"}
    assert sub_names == expected, f"Missing sub-agents: {expected - sub_names}"


def test_director_is_adk_agent():
    """Director must be a google.adk.agents.Agent instance."""
    director = create_director_agent()
    assert isinstance(director, Agent)


def test_agents_accept_tools():
    """All agent factories must accept a tools parameter."""
    dummy_tools = []  # Empty list simulates no tools
    agents = [
        create_storygraph_agent(tools=dummy_tools),
        create_continuity_agent(tools=dummy_tools),
        create_final_take_agent(tools=dummy_tools),
        create_cascade_agent(tools=dummy_tools),
        create_skeptic_agent(tools=dummy_tools),
        create_director_agent(tools=dummy_tools),
    ]
    assert len(agents) == 6
