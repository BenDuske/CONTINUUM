# ARCHITECTURE.md

> Technical architecture of CONTINUUM — an agentic production-intelligence system for film.

---

## System Overview

CONTINUUM maintains a **Living Film Graph** — a temporal, event-driven memory of an entire film production. Six AI agents powered by Gemini 3.5 Flash reason over this graph via ClickHouse, detecting continuity errors, assessing shot coverage, and tracing the impact of changes **before they become reshoots.**

```
                    ┌────────────────────────────────────────────┐
                    │          PRODUCTION COMMAND CENTER         │
                    │          FastAPI + Jinja2 (Web UI)         │
                    └───────────────────┬────────────────────────┘
                                        │
                              ┌─────────┴──────────┐
                              │                    │
                         Agent API            Data API
                     (POST /api/agent/*)   (GET /api/production/*)
                              │                    │
                     ADK Runner (async)     clickhouse-connect
                              │              (direct client)
                              │                    │
                    ┌─────────┴──────────┐         │
                    │   DIRECTOR AGENT   │         │
                    │   (orchestrator)    │         │
                    └─────────┬──────────┘         │
                              │                    │
           ┌──────┬───────┬───┴───┬────────┐       │
           │      │       │       │        │       │
       STORY   CONTIN-  FINAL  CASCADE  SKEPTIC    │
       GRAPH   UITY     TAKE                       │
           │      │       │       │        │       │
           └──────┴───────┴───┬───┴────────┘       │
                              │                    │
                       McpToolset (ADK)            │
                     mcp-clickhouse (stdio)        │
                              │                    │
                              └────────┬───────────┘
                                       │
                              ┌────────┴────────┐
                              │  ClickHouse     │
                              │  Cloud          │
                              │  (us-central1)  │
                              └─────────────────┘
```

### Dual Data Path

CONTINUUM accesses ClickHouse through two independent paths:

| Path | Used by | Protocol | Purpose |
|------|---------|----------|---------|
| **MCP** (`mcp-clickhouse`) | AI agents via ADK `McpToolset` | stdio / MCP protocol | Agent-driven SQL queries (`run_query`, `list_tables`, `list_databases`) |
| **Direct** (`clickhouse-connect`) | Web API endpoints | Native ClickHouse HTTP | Dashboard metrics, scene listings, health checks |

This separation matters: agents reason freely over the database through MCP (the hackathon requirement), while the dashboard gets fast, predictable queries without agent overhead.

---

## Agent Network

All agents are Google ADK `Agent` instances using `gemini-3.5-flash`. The Director holds all five specialists as sub-agents and routes queries via ADK's built-in transfer mechanism.

```
                         DIRECTOR
                    (orchestrator, router)
                            │
         ┌──────────────────┼──────────────────┐
         │          │          │         │          │
    STORYGRAPH  CONTINUITY  FINAL    CASCADE    SKEPTIC
                            TAKE
```

### Agent Responsibilities

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| **DIRECTOR** | Orchestrator | Routes queries to specialists; enforces epistemic labeling; never fabricates data |
| **STORYGRAPH** | Story logic | Narrative dependency analysis; classifies links as NARRATIVE / VISUAL / DIALOGUE / TEMPORAL; tracks UPSTREAM vs DOWNSTREAM |
| **CONTINUITY** | Digital script supervisor | Tracks prop states, wardrobe, makeup, lighting, screen direction across scenes in **story order** (not shoot order) |
| **FINAL TAKE** | Coverage assessment | Compares planned shots vs captured takes; verdict: SAFE TO WRAP / WRAP WITH RISKS / NOT SAFE TO WRAP; conservative by default |
| **CASCADE** | Change-impact propagation | Traces dependency graph (scene → shots → takes → props → wardrobe); distinguishes already-filmed (expensive) from upcoming (cheap) |
| **SKEPTIC** | Adversarial verification | Tries to **disprove** other agents' findings; three verdicts: CONFIRMED / WEAKENED / REFUTED; defaults to confirming (false negatives cost more than false positives in film) |

### Agent Factory Pattern

Agents are created via factory functions, not module-level instances:

```python
# src/continuum/agents/director.py
def create_director_agent(tools=None) -> Agent:
    return Agent(
        name="continuum_director",
        model="gemini-3.5-flash",
        instruction="...",
        sub_agents=[
            create_storygraph_agent(tools),
            create_continuity_agent(tools),
            create_final_take_agent(tools),
            create_cascade_agent(tools),
            create_skeptic_agent(tools),
        ],
        tools=tools or [],
    )
```

This allows MCP tools to be injected at runtime — the `McpToolset` is created once in `runner.py` and passed through the entire agent tree.

### Three Epistemic Layers

Every finding carries an epistemic state label:

| Layer | Meaning | Example |
|-------|---------|---------|
| **OBSERVED** | Detected directly from production data | "Camera P-14 has 'damaged' state in the props table" |
| **INFERRED** | An agent believes this is true | "Scene 42 likely needs the camera to show damage based on Scene 31" |
| **CONFIRMED** | A human or authoritative system accepted it | "Script supervisor verified: damaged camera is correct for Scene 42" |

Only findings that survive the SKEPTIC's adversarial challenge get escalated to the crew.

---

## Runtime Pipeline

### Initialization (`runner.py`)

```
_ensure_initialized()
    │
    ├── get_mcp_params()          → StdioServerParameters for mcp-clickhouse
    ├── McpToolset(params)        → launches mcp-clickhouse as stdio subprocess
    ├── create_director_agent()   → full agent tree with MCP tools injected
    ├── InMemorySessionService()  → ephemeral session store
    └── Runner(agent, session_service, auto_create_session=True)
```

### Query Flow

```
HTTP POST /api/agent/query
    │
    ▼
run_agent_query(query)
    │
    ├── _ensure_initialized()
    ├── Create unique session ID: session-{uuid[:8]}
    │
    ▼
runner.run_async(user_id, session_id, new_message=query)
    │
    ├── DIRECTOR receives query
    ├── DIRECTOR transfers to specialist (e.g., FINAL TAKE)
    ├── Specialist calls mcp-clickhouse tools:
    │     ├── list_tables("continuum")
    │     ├── run_query("SELECT * FROM shots WHERE scene_id = ...")
    │     └── run_query("SELECT * FROM takes WHERE scene_id = ...")
    ├── Specialist returns analysis to DIRECTOR
    ├── DIRECTOR may transfer to SKEPTIC for verification
    └── Final response collected from text parts
    │
    ▼
Return response text (or structured dict for wrap-check/cascade)
```

Each query creates a fresh session — there is no cross-request conversation memory.

### Wrap Check (Signature Feature)

The wrap check at `POST /api/production/{id}/scene/{id}/wrap-check` triggers the full agent pipeline:

```
run_wrap_check(production_id, scene_id)
    │
    ├── Construct detailed prompt with SQL context
    │     "Assess whether scene-42 in tls-001 can be wrapped..."
    │
    ▼
DIRECTOR → FINAL TAKE
    ├── Queries shots (planned vs captured)
    ├── Queries takes (ratings, coverage)
    └── Returns coverage confidence + gaps
    │
DIRECTOR → CONTINUITY
    ├── Queries props (state consistency)
    ├── Queries story dependencies
    └── Returns continuity conflicts
    │
DIRECTOR → SKEPTIC
    ├── Attempts to disprove findings
    └── Returns CONFIRMED / WEAKENED / REFUTED
    │
    ▼
Parse response for verdict:
    🟢 SAFE TO WRAP
    🟡 WRAP WITH RISKS
    🔴 NOT SAFE TO WRAP
```

---

## Data Model

### ClickHouse Schema

The Living Film Graph is stored across 9 tables in ClickHouse Cloud:

```
┌─────────────────────────────────────────────────┐
│                 LIVING FILM GRAPH                │
├─────────────────────────────────────────────────┤
│                                                 │
│  production_events ← append-only event stream   │
│  (MergeTree, partitioned by month)              │
│       │                                         │
│       ├── scenes (ReplacingMergeTree)            │
│       │     ├── shots (ReplacingMergeTree)       │
│       │     │     └── takes (MergeTree)          │
│       │     └── story_dependencies[]             │
│       │                                         │
│       ├── props (ReplacingMergeTree)             │
│       ├── wardrobe (ReplacingMergeTree)          │
│       └── continuity_issues (ReplacingMergeTree) │
│                                                 │
│  Materialized views:                            │
│    scene_coverage_mv (SummingMergeTree)          │
│    production_health (ReplacingMergeTree)        │
└─────────────────────────────────────────────────┘
```

| Table | Engine | Order Key | Notes |
|-------|--------|-----------|-------|
| `production_events` | MergeTree | `(production_id, timestamp, event_type)` | Core event stream; PARTITION BY month; append-only |
| `scenes` | ReplacingMergeTree | `(production_id, scene_number)` | Upsert on scene_number; `Array(String)` for characters, props, dependencies |
| `shots` | ReplacingMergeTree | `(production_id, scene_id, shot_label)` | Planned shots per scene |
| `takes` | MergeTree | `(production_id, scene_id, shot_id, take_number)` | Actual filmed takes |
| `props` | ReplacingMergeTree | `(production_id, prop_id)` | Current state tracking (intact → damaged, etc.) |
| `wardrobe` | ReplacingMergeTree | `(production_id, character, wardrobe_id)` | Per-character wardrobe states |
| `continuity_issues` | ReplacingMergeTree | `(production_id, scene_id, issue_id)` | Detected issues with severity |
| `scene_coverage_mv` | SummingMergeTree | `(production_id, scene_id)` | Materialized coverage aggregates |
| `production_health` | ReplacingMergeTree | `(production_id)` | Roll-up production metrics |

**Design choices:**
- `LowCardinality(String)` for enum-like columns (event types, severities)
- `Array(String)` for multi-value fields (characters in a scene, props list)
- `ReplacingMergeTree` for entity tables — upsert semantics without explicit DELETE
- `MergeTree` for event stream and takes — append-only, immutable records

### Pydantic Models

The Python domain models in `src/continuum/schema/models.py` mirror the ClickHouse schema with additional validation:

- `ProductionEvent`, `Scene`, `Shot`, `Take`, `Prop`, `WardrobeItem`
- `ContinuityIssue` — with `EpistemicState` and `Severity` enums
- `CoverageAssessment` — the output of a wrap check (0.0–1.0 confidence)
- `ChangeImpact` — the output of a CASCADE analysis

---

## Web Layer

### FastAPI Application (`src/continuum/web/app.py`)

| Endpoint | Method | Handler | Data Source |
|----------|--------|---------|-------------|
| `/` | GET | `dashboard()` | Jinja2 template |
| `/health` | GET | `health()` | ClickHouse `SELECT 1` |
| `/api/production/{id}/status` | GET | `production_status()` | Direct ClickHouse queries |
| `/api/production/{id}/scenes` | GET | `list_scenes()` | Direct ClickHouse queries |
| `/api/production/{id}/scene/{id}` | GET | `scene_detail()` | Direct ClickHouse queries |
| `/api/agent/query` | POST | `agent_query()` | ADK Runner → Gemini → MCP → ClickHouse |
| `/api/production/{id}/scene/{id}/wrap-check` | POST | `wrap_check()` | ADK Runner (full pipeline) |
| `/api/production/{id}/scene/{id}/continuity-check` | POST | `continuity_check()` | ADK Runner |
| `/api/production/{id}/cascade` | POST | `cascade_analysis()` | ADK Runner |

### Dashboard

The Production Command Center (`templates/dashboard.html`) is a dark-themed monitoring UI showing:
- Production progress metrics (scenes complete, coverage, continuity confidence)
- Scene-level controls (ANALYZE, FINAL TAKE, WRAP SCENE buttons)
- Continuity issue feed with severity levels

---

## Configuration

All configuration loads from environment variables via `python-dotenv`:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GOOGLE_API_KEY` | ✅ | — | Gemini API authentication |
| `CLICKHOUSE_HOST` | ✅ | `localhost` | ClickHouse Cloud hostname |
| `CLICKHOUSE_PORT` | — | `8443` | ClickHouse HTTPS port |
| `CLICKHOUSE_USER` | — | `default` | ClickHouse username |
| `CLICKHOUSE_PASSWORD` | ✅ | — | ClickHouse password |
| `CLICKHOUSE_DATABASE` | — | `continuum` | Target database |
| `CLICKHOUSE_SECURE` | — | `true` | TLS enabled |
| `GOOGLE_CLOUD_PROJECT` | — | — | GCP project ID |
| `PARALLEL_API_KEY` | — | — | Parallel Search (optional) |
| `CONTINUUM_ENV` | — | `development` | Environment mode |
| `CONTINUUM_PORT` | — | `8080` | Web server port |

---

## Deployment

### Cloud Run

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  gcloud run  │────▶│ Cloud Build  │────▶│  Cloud Run       │
│  deploy      │     │ (Dockerfile) │     │  (us-central1)   │
│  --source .  │     │              │     │                  │
└──────────────┘     └──────────────┘     │  ┌────────────┐  │
                                          │  │ uvicorn    │  │
                                          │  │ port $PORT │  │
                                          │  └─────┬──────┘  │
                                          │        │         │
                                          │  mcp-clickhouse  │
                                          │  (stdio subproc) │
                                          └──────────────────┘
                                                   │
                                          ClickHouse Cloud
                                          (GCP us-central1)
```

**Dockerfile** (single-stage, `python:3.12-slim`):
1. Install `gcc` (clickhouse-connect C extensions)
2. `pip install .` — installs all deps including `mcp-clickhouse` binary
3. Copy `data/` and `scripts/`
4. `CMD uvicorn continuum.web.app:app --host 0.0.0.0 --port $PORT`

**Key deployment details:**
- `--min-instances 0` — scales to zero when idle (cost control)
- `--max-instances 2` — limits concurrent containers
- `--memory 1Gi` — sufficient for ADK + MCP subprocess
- `--timeout 300` — agent queries can take 10-30s on cold ClickHouse
- Secrets passed as `--set-env-vars` (not committed to repo)

---

## Project Structure

```
CONTINUUM/
├── src/continuum/
│   ├── __init__.py              # Version
│   ├── config.py                # Env-based configuration (dataclasses)
│   ├── runner.py                # ADK Runner + MCP initialization + query functions
│   ├── agents/
│   │   ├── director.py          # Orchestrator (routes to sub-agents)
│   │   ├── storygraph.py        # Narrative dependency analysis
│   │   ├── continuity.py        # Digital script supervisor
│   │   ├── final_take.py        # Coverage assessment ("can we wrap?")
│   │   ├── cascade.py           # Change-impact propagation
│   │   └── skeptic.py           # Adversarial verification
│   ├── mcp/
│   │   └── clickhouse_mcp.py    # StdioServerParameters for mcp-clickhouse
│   ├── schema/
│   │   ├── clickhouse_ddl.sql   # ClickHouse CREATE TABLE statements
│   │   └── models.py            # Pydantic domain models + enums
│   ├── tools/
│   │   └── clickhouse_tools.py  # Direct ClickHouse query functions
│   └── web/
│       ├── app.py               # FastAPI endpoints
│       └── templates/
│           └── dashboard.html   # Production Command Center UI
├── data/
│   └── sample_production/
│       └── the_last_signal.json # Demo production (47 scenes)
├── scripts/
│   ├── init_db.py               # Create ClickHouse schema
│   └── load_sample_data.py      # Load demo data
├── tests/
│   ├── test_agents.py           # Agent creation + configuration tests
│   └── test_schema.py           # Pydantic model validation tests
├── compliance/
│   ├── google_cloud_usage.md    # Gemini compliance evidence
│   └── clickhouse_mcp_usage.md  # MCP compliance evidence
├── Dockerfile                   # Cloud Run container
├── pyproject.toml               # Dependencies + build config
├── LICENSE                      # Apache 2.0
└── README.md
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **AI Model** | Gemini 3.5 Flash | via `google-genai` |
| **Agent Framework** | Google Cloud ADK | 2.x (`google-adk`) |
| **MCP Server** | mcp-clickhouse | 0.4.x (FastMCP 2.14.7) |
| **Database** | ClickHouse Cloud | 26.2.1 (GCP us-central1) |
| **Web Framework** | FastAPI | 0.115+ |
| **ASGI Server** | Uvicorn | 0.30+ |
| **Templating** | Jinja2 | 3.1+ |
| **Data Validation** | Pydantic | 2.x |
| **Deployment** | Google Cloud Run | Managed |
| **Build** | Cloud Build | Dockerfile |
| **Language** | Python | 3.12 |

---

## Compliance (Hackathon Rules)

| Rule | How CONTINUUM Complies |
|------|----------------------|
| **AI restriction: Gemini only** | All 6 agents use `gemini-3.5-flash` exclusively; no other AI providers |
| **ClickHouse track: mcp-clickhouse at runtime** | `McpToolset` launches `mcp-clickhouse` as stdio subprocess; agents call `run_query` / `list_tables` / `list_databases` at runtime |
| **Public repo** | `github.com/BenDuske/CONTINUUM` |
| **Open-source license** | Apache 2.0 (`LICENSE` file) |
| **Web platform** | FastAPI served via Cloud Run |
| **New project** | First commit after hackathon announcement |

Evidence logs in `compliance/google_cloud_usage.md` and `compliance/clickhouse_mcp_usage.md`.
