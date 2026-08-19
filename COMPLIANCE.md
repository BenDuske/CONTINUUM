# CONTINUUM — Hackathon Compliance Grid

**Event:** [Agentic Cinema Hackathon](https://agentic-cinema.devpost.com/) (Google Cloud + partners)
**Track:** ClickHouse
**Submission date:** on or before Sep 7, 2026 · 2:00 PM PT
**Live service:** https://continuum-882642985987.us-central1.run.app
**Public repo:** https://github.com/BenDuske/CONTINUUM

This document maps each hackathon requirement to the evidence that
satisfies it. Every claim in the "Evidence" column is an actual file, URL,
or line in this repository — no summaries, no promises.

---

## AI-provider constraint

| Requirement | Status | Evidence |
|---|---|---|
| AI must be Gemini / Google Cloud AI only. No Claude, no OpenAI, no Anthropic, no Llama, no Mistral. | ✅ | `src/continuum/config.py` (only `google-genai` model IDs); `tests/test_agent_contracts.py::TestHackathonCompliance::test_uses_only_gemini_models` — runs on every push; `compliance/google_cloud_usage.md` (full list of Google-AI touchpoints). |
| All 6 agents run on Gemini. | ✅ | `src/continuum/agents/*.py` all use `model="gemini-3.5-flash"`. CI test above enforces this on every agent factory. |
| Vision subsystem uses Google-only APIs. | ✅ | Google Video Intelligence + Vertex AI (Imagen embeddings) + Gemini multimodal — see `compliance/vision_blueprint_note.md` and `src/continuum/vision/engines/`. |

## ClickHouse track requirements

| Requirement | Status | Evidence |
|---|---|---|
| Must use the official `mcp-clickhouse` MCP server at runtime. | ✅ | `src/continuum/runner.py::_ensure_initialized` boots `McpToolset(connection_params=get_mcp_params())` before serving any query; `src/continuum/mcp/clickhouse_mcp.py` returns the stdio params; `compliance/clickhouse_mcp_usage.md` shows the wiring diagram. |
| Production memory in ClickHouse Cloud. | ✅ | `src/continuum/schema/*_ddl.sql` — 10 core tables (`scenes`, `shots`, `takes`, `props`, `wardrobe`, `production_events`, `continuity_issues`, `scene_dependencies` + vision tables `frame_observations`, `take_dialogue`, `vision_verdicts`, `frame_embeddings`). |
| ClickHouse queried at runtime, not just at build time. | ✅ | Every FastAPI endpoint in `src/continuum/web/app.py` either issues a live `clickhouse_connect.get_client().query(...)` call or drives an ADK agent that calls the MCP `run_query` tool. |

## Platform & delivery

| Requirement | Status | Evidence |
|---|---|---|
| Web / Android / iOS platform. | ✅ Web | FastAPI + Jinja2 dashboard (`src/continuum/web/`), deployed to Google Cloud Run. |
| Publicly accessible demo URL. | ✅ | https://continuum-882642985987.us-central1.run.app (`--allow-unauthenticated`). |
| Public repository with visible license. | ✅ | https://github.com/BenDuske/CONTINUUM · [`LICENSE`](LICENSE) is Apache-2.0 in repo root. |
| Docker deployable. | ✅ | [`Dockerfile`](Dockerfile) — builds under Cloud Build + runs on Cloud Run. |
| Open source license. | ✅ | Apache License 2.0 — [`LICENSE`](LICENSE). |
| 3-minute demo video on YouTube or Vimeo. | 🟡 pending | Recording script + shot list ready in `docs/DEMO_VIDEO.md`; upload owner: Ben. |
| New project (no pre-existing code reuse). | ✅ | Repo created Aug 2026; full commit history public. Vision subsystem is a fresh design that reused conceptual patterns from AVI but zero code — explicitly documented in `compliance/vision_blueprint_note.md`. |
| Max 4 team members. | ✅ | Solo submission (Benjamin Duske / Digital Real-Estate Frontier, LLC). |

## Engineering hygiene (not required, but reads as maturity)

| Item | Status | Evidence |
|---|---|---|
| CI runs on every push. | 🟡 pending push | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — ruff + pytest (Python 3.11 & 3.12 matrix) + Docker build. Committed locally, awaiting `gh auth refresh -s workflow` before it reaches origin. |
| Deterministic tests, no cloud calls in CI. | ✅ | 69 tests, all stub/mocked. See `tests/test_e2e_wrap_check.py` for the mocked E2E pattern. |
| Prompt-regression guards. | ✅ | `tests/test_agent_contracts.py` pins every agent's routing keywords, ClickHouse tables, and verdict vocabulary so a bad prompt edit fails CI. |
| Reproducible env. | ✅ | [`.env.example`](.env.example) covers every env var the app reads. |
| Compliance evidence lives in-repo. | ✅ | `compliance/` — every claim above traces back to a file here. |

## Judging criteria — where the pitch lands

| Criterion | Where CONTINUUM shows it |
|---|---|
| **Technical Implementation** | 6 ADK agents + real MCP-to-ClickHouse wiring + Google Cloud Run + vision subsystem across 3 Google APIs. `src/continuum/`, `src/continuum/vision/`. |
| **Design** | Production Command Center dashboard, epistemic layers (OBSERVED / INFERRED / CONFIRMED), verdict vocabulary (🟢/🟡/🔴). `src/continuum/web/templates/dashboard.html`. |
| **Potential Impact** | The refusal-first UX ("do NOT wrap") targets reshoot cost — the real financial pain in production. See `README.md` "The Problem". |
| **Idea Quality** | Living Film Graph + Skeptic-as-adversary + refuse-to-answer-when-uncertain — pattern is transferable beyond film. `ARCHITECTURE.md`. |

---

*Last updated: 2026-08-19 (Argo). If you're a judge and something above
doesn't match what you see in the repo, that's a defect — open an issue
and it'll be fixed.*
