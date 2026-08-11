# CONTINUUM 🎬

**An agentic production-intelligence system for film.**

> *Know you have the movie before you leave the set.*

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Google Cloud](https://img.shields.io/badge/Google_Cloud-Gemini_+_ADK-4285F4.svg)](https://cloud.google.com)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-Cloud-FADB14.svg)](https://clickhouse.com)

---

## The Problem

Film productions don't have persistent machine-understandable memory.

A movie begins as one document — a screenplay — and explodes into thousands of interconnected decisions involving people, locations, props, wardrobe, shots, equipment, money, schedules, footage, and continuity. That information is scattered across scripts, PDFs, spreadsheets, emails, call sheets, photos, video, audio, notes, and people's memories.

When something changes, **humans manually propagate the consequences.**

The result:
- **Script changes create cascading production changes** that nobody fully traces
- **Continuity errors** surface in the edit bay, not on set
- **Missing coverage** is discovered after the location is struck
- **Production knowledge disappears** between departments and phases

These problems cost real productions real money in reshoots, delays, and post-production fixes.

## The Solution

**CONTINUUM** is an agentic production-intelligence system that maintains a **Living Film Graph** — a temporal, event-driven memory of the entire movie from screenplay through final cut.

It detects conflicts, predicts change impacts, verifies coverage, and coordinates corrective actions **before problems become reshoots.**

### Agent Network

CONTINUUM is a multi-agent system powered by **Gemini** and **Google Cloud Agent Development Kit (ADK)**:

| Agent | Responsibility |
|---|---|
| **DIRECTOR** | Orchestrator — routes queries to specialist agents |
| **STORYGRAPH** | Story logic and narrative dependency analysis |
| **CONTINUITY** | Visual/narrative state consistency (digital script supervisor) |
| **FINAL TAKE** | Coverage assessment — "Do we have the movie?" |
| **CASCADE** | Change-impact propagation — "What does this change break?" |
| **CUTMIND** | Semantic footage intelligence |
| **SKEPTIC** | Adversarial verification of agent conclusions |
| **RESEARCH** | External intelligence via Parallel Search API |

### Three Epistemic Layers

CONTINUUM knows the difference between data, inference, and decision:

- **OBSERVED** — Detected directly from production data
- **INFERRED** — An agent believes this is true
- **CONFIRMED** — A human or authoritative system accepted it

Only findings that survive the SKEPTIC's adversarial challenge get escalated to the crew.

## Architecture

```
                         CONTINUUM
              ┌─────────────────────────┐
              │   PRODUCTION COMMAND    │
              │        CENTER           │
              │     (FastAPI Web UI)    │
              └────────────┬────────────┘
                           │
                    Gemini / Google ADK
                           │
                 CONTINUUM DIRECTOR
                    Orchestrator Agent
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   STORYGRAPH          FINAL TAKE         CASCADE
      Agent               Agent             Agent
        │                  │                  │
   CONTINUITY           CUTMIND           SKEPTIC
      Agent               Agent             Agent
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
              ┌────────────┼─────────────┐
              │            │             │
         ClickHouse    Parallel       Grafana*
          MEMORY       RESEARCH      DASHBOARDS
       (MCP Server)  (Search API)   (* optional)
```

### Technology Stack

| Component | Technology | Role |
|---|---|---|
| **AI Intelligence** | Google Gemini (via `google-adk`) | All reasoning, multimodal analysis |
| **Agent Framework** | Google Cloud ADK 2.0 | Multi-agent orchestration |
| **Production Memory** | ClickHouse Cloud (via `mcp-clickhouse`) | Event stream + Living Film Graph |
| **External Research** | Parallel Search API | Location scouting, historical verification |
| **Web Interface** | FastAPI + Jinja2 | Production Command Center |
| **Deployment** | Google Cloud Run | Serverless hosting |

## Quick Start

### Prerequisites

- Python 3.10+
- A [Google Cloud](https://cloud.google.com/free) account with Gemini API access
- A [ClickHouse Cloud](https://clickhouse.com/cloud) account ($400 free credits for new accounts)
- A [Parallel](https://parallel.ai) API key

### Installation

```bash
# Clone the repository
git clone https://github.com/BenDuske/CONTINUUM.git
cd CONTINUUM

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys and ClickHouse credentials

# Initialize ClickHouse schema
# (after configuring your ClickHouse connection)
python scripts/init_db.py

# Load sample production data
python scripts/load_sample_data.py

# Run the application
python -m continuum.web.app
```

Visit `http://localhost:8080` to see the Production Command Center.

### Running the ADK Agent

```bash
# Run the agent with ADK CLI
adk run continuum_director

# Or with the web interface
adk web continuum_director
```

## Demo Scenario: "The Last Signal"

CONTINUUM ships with a fictional sci-fi production — *THE LAST SIGNAL* — demonstrating the full agent pipeline:

1. **Upload** the screenplay and production state
2. **Change** Scene 42: "damaged camera" → "undamaged camera"
3. **Watch** agents detect the cascade: StoryGraph finds the conflict with Scene 31, Continuity flags the prop state mismatch, CutMind identifies already-filmed footage
4. **Try** to wrap Scene 42 — FINAL TAKE refuses: missing coverage + unresolved continuity conflict
5. **Fix** the issues and re-assess → 🟢 SAFE TO WRAP

## Hackathon Track

**Agentic Cinema: The Blockbuster Hackathon** — ClickHouse Track

- ClickHouse provides the production memory — every agent queries it via MCP
- Gemini provides all AI reasoning (no other AI models used)
- Google Cloud ADK orchestrates the multi-agent network

## Project Structure

```
CONTINUUM/
├── src/continuum/
│   ├── agents/          # ADK agent definitions
│   │   ├── director.py  # Orchestrator
│   │   ├── storygraph.py
│   │   ├── continuity.py
│   │   ├── final_take.py
│   │   ├── cascade.py
│   │   └── skeptic.py
│   ├── schema/          # Pydantic models + ClickHouse DDL
│   ├── tools/           # ClickHouse query functions
│   ├── mcp/             # MCP server integration
│   └── web/             # FastAPI dashboard
├── data/                # Sample production data
├── tests/               # Test suite
├── docs/                # Documentation
├── compliance/          # Hackathon compliance evidence
└── scripts/             # DB init, data loading
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Author

**Benjamin Duske** — [Aetherion Technology](https://aetheriontechnologys.com)

Built for the [Agentic Cinema Hackathon](https://agentic-cinema.devpost.com/) (Google Cloud + ClickHouse Track).
