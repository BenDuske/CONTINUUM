# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Per-agent contract tests.

These tests are prompt-regression guards. They don't call Gemini — they assert
that each agent's instruction string still names the concepts, tables, and
verdict vocabulary the rest of the system (and the demo) depends on. If
someone edits an agent's prompt and drops (e.g.) the shots-vs-takes rule,
CI catches it before the demo does.
"""

from __future__ import annotations

import re

import pytest

from continuum.agents.cascade import create_cascade_agent
from continuum.agents.continuity import create_continuity_agent
from continuum.agents.director import create_director_agent
from continuum.agents.final_take import create_final_take_agent
from continuum.agents.skeptic import create_skeptic_agent
from continuum.agents.storygraph import create_storygraph_agent


def _instr(agent) -> str:
    """Return the agent's instruction string, lower-cased for keyword matching."""
    return agent.instruction.lower()


# --------------------------------------------------------------------------- #
# DIRECTOR — routing contract
# --------------------------------------------------------------------------- #

class TestDirectorRouting:
    """Director must know each specialist by name AND by domain."""

    def setup_method(self):
        self.director = create_director_agent()
        self.instr = _instr(self.director)

    @pytest.mark.parametrize(
        "sub_name",
        ["storygraph", "continuity", "final_take", "cascade", "skeptic"],
    )
    def test_names_each_specialist(self, sub_name):
        assert sub_name in self.instr, f"Director instructions never name '{sub_name}'"

    def test_mentions_wrap_domain_routing(self):
        # Wrap-check queries must route to final_take (that's the signature demo).
        assert "wrap" in self.instr and "final_take" in self.instr

    def test_mentions_change_impact_routing(self):
        # Change-impact queries must route to cascade.
        assert "change" in self.instr and "cascade" in self.instr

    def test_mentions_continuity_domain_routing(self):
        assert re.search(r"prop|wardrobe|continuity", self.instr)

    def test_has_all_sub_agents_wired(self):
        sub_names = {a.name for a in self.director.sub_agents}
        assert sub_names == {"storygraph", "continuity", "final_take", "cascade", "skeptic"}


# --------------------------------------------------------------------------- #
# CONTINUITY — prop-state rule
# --------------------------------------------------------------------------- #

class TestContinuityAgent:
    """Continuity is the digital script supervisor — state tracking is its job."""

    def setup_method(self):
        self.agent = create_continuity_agent()
        self.instr = _instr(self.agent)

    def test_tracks_prop_state(self):
        assert "prop" in self.instr
        # Must reference state (damaged/intact style tracking).
        assert re.search(r"state|damaged|intact|condition", self.instr)

    def test_tracks_wardrobe(self):
        assert "wardrobe" in self.instr

    def test_uses_story_order_not_shoot_order(self):
        # Critical distinction — takes are shot out of order, continuity must
        # reason in story order.
        assert "story order" in self.instr or "not shoot order" in self.instr

    def test_queries_clickhouse_props_table(self):
        assert "continuum.props" in _instr(self.agent) or "props" in self.instr


# --------------------------------------------------------------------------- #
# FINAL TAKE — shots-vs-takes math
# --------------------------------------------------------------------------- #

class TestFinalTakeAgent:
    """Final Take answers 'Can we wrap?' — it must compare shots to takes."""

    def setup_method(self):
        self.agent = create_final_take_agent()
        self.instr = _instr(self.agent)

    def test_queries_shots_table(self):
        assert "shots" in self.instr

    def test_queries_takes_table(self):
        assert "takes" in self.instr

    def test_compares_planned_to_captured(self):
        # The math: planned shots vs captured takes.
        assert re.search(r"planned.*captur|compare.*coverage|missing.*coverage", self.instr)

    def test_emits_three_verdict_states(self):
        # 🟢 SAFE / 🟡 WRAP WITH RISKS / 🔴 NOT SAFE — all three must be present.
        assert "safe to wrap" in self.instr
        assert "wrap with risks" in self.instr
        assert "not safe to wrap" in self.instr

    def test_reports_coverage_confidence(self):
        assert "coverage confidence" in self.instr or "percentage" in self.instr


# --------------------------------------------------------------------------- #
# CASCADE — downstream impact
# --------------------------------------------------------------------------- #

class TestCascadeAgent:
    """CASCADE traces what a change breaks downstream."""

    def setup_method(self):
        self.agent = create_cascade_agent()
        self.instr = _instr(self.agent)

    def test_traces_dependency_graph(self):
        assert re.search(r"dependency graph|downstream|impact", self.instr)

    def test_covers_scene_shot_take_chain(self):
        # Must know the propagation chain.
        for entity in ("scene", "shot", "take"):
            assert entity in self.instr, f"CASCADE forgets about {entity}s"

    def test_flags_already_filmed_conflicts(self):
        assert re.search(r"already.filmed|filmed material|conflicts", self.instr)

    def test_proposes_resolutions(self):
        assert re.search(r"resolution|options|propose", self.instr)


# --------------------------------------------------------------------------- #
# SKEPTIC — adversarial verification
# --------------------------------------------------------------------------- #

class TestSkepticAgent:
    """SKEPTIC tries to disprove other agents. It must render one of 3 verdicts."""

    def setup_method(self):
        self.agent = create_skeptic_agent()
        self.instr = _instr(self.agent)

    def test_seeks_counter_evidence(self):
        assert "counter-evidence" in self.instr or "counter evidence" in self.instr

    @pytest.mark.parametrize("verdict", ["confirmed", "weakened", "refuted"])
    def test_emits_three_verdicts(self, verdict):
        assert verdict in self.instr, f"SKEPTIC missing verdict '{verdict.upper()}'"

    def test_considers_script_revisions(self):
        assert "script revision" in self.instr or "revisions" in self.instr

    def test_considers_director_override(self):
        assert "override" in self.instr


# --------------------------------------------------------------------------- #
# STORYGRAPH — narrative dependencies
# --------------------------------------------------------------------------- #

class TestStoryGraphAgent:
    """STORYGRAPH reasons about screenplay structure, not physical state."""

    def setup_method(self):
        self.agent = create_storygraph_agent()
        self.instr = _instr(self.agent)

    def test_analyzes_scene_dependencies(self):
        assert "dependenc" in self.instr and "scene" in self.instr

    def test_classifies_dependency_kinds(self):
        # NARRATIVE / VISUAL / DIALOGUE / TEMPORAL — at least one classification
        # scheme must exist.
        assert re.search(r"narrative|visual|dialogue|temporal", self.instr)

    def test_defers_physical_continuity_to_continuity_agent(self):
        # STORYGRAPH must NOT try to do CONTINUITY's job.
        assert "continuity" in self.instr  # references it (delegates to it)


# --------------------------------------------------------------------------- #
# Cross-agent contract: hackathon compliance
# --------------------------------------------------------------------------- #

class TestHackathonCompliance:
    """Rules that apply to ALL agents (Agentic Cinema hackathon)."""

    ALL_FACTORIES = [
        create_storygraph_agent,
        create_continuity_agent,
        create_final_take_agent,
        create_cascade_agent,
        create_skeptic_agent,
        create_director_agent,
    ]

    @pytest.mark.parametrize("factory", ALL_FACTORIES)
    def test_uses_only_gemini_models(self, factory):
        # Hackathon forbids Claude / OpenAI / any non-Google model.
        agent = factory()
        model = agent.model.lower()
        assert model.startswith("gemini"), f"{agent.name} uses non-Gemini model: {agent.model}"
        for forbidden in ("claude", "gpt", "openai", "anthropic", "llama", "mistral"):
            assert forbidden not in model, f"{agent.name} touches forbidden provider '{forbidden}'"

    @pytest.mark.parametrize("factory", ALL_FACTORIES)
    def test_accepts_tools_parameter(self, factory):
        # Every agent factory must accept tools=... so MCP toolset can be
        # injected at runtime.
        agent = factory(tools=[])
        assert agent is not None
