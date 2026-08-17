# Google Cloud Usage Evidence

**Requirement:** Must use Gemini and Google Cloud AI tools. No other AI permitted.

## Runtime Integration Points

| Component | Google Cloud Service | Package | Runtime Usage |
|---|---|---|---|
| AI Reasoning | Gemini 3.5 Flash | `google-genai` | Agent model calls via ADK |
| Agent Framework | Agent Development Kit (ADK) 2.x | `google-adk` | Multi-agent orchestration |
| Agent Engine | Vertex AI Agent Engine | `google-cloud-aiplatform` | Cloud deployment |
| Video Analysis | Video Intelligence API (v1p3beta1) | `google-cloud-videointelligence` | Shot / object / face / label / OCR / speech extraction from take assets (`continuum.vision.engines.video_intelligence`) |
| Multimodal Verdicts | Gemini 3.5 Flash (multimodal) | `google-genai` | Structured continuity verdicts on keyframes given screenplay context (`continuum.vision.engines.gemini_multimodal`) |
| Image Embeddings | Vertex AI `multimodalembedding@001` (Imagen 3 family) | `google-cloud-aiplatform` | 1408-dim frame embeddings for nearest-frame lookup (`continuum.vision.engines.imagen_embed`) |
| Asset Storage | Cloud Storage | `google-cloud-storage` | Take media inputs and provenance sidecars |

## Agent Definitions (all use `google.adk.agents.Agent`)

All agents use `model="gemini-3.5-flash"`:
- `continuum_director` — orchestrator (routes to sub-agents, queries ClickHouse via MCP)
- `storygraph` — narrative analysis
- `continuity` — consistency checking
- `final_take` — coverage assessment
- `cascade` — change-impact analysis
- `skeptic` — adversarial verification

## Runtime Code Paths

1. **`src/continuum/runner.py`**: Creates `Runner` with `InMemorySessionService`,
   initializes `McpToolset` for mcp-clickhouse, calls `runner.run_async()` which
   invokes Gemini 3.5 Flash for each agent turn.

2. **`src/continuum/agents/*.py`**: Each agent is a `google.adk.agents.Agent` instance
   with model, instructions, and MCP tools.

3. **`src/continuum/web/app.py`**: FastAPI endpoints call `runner.run_agent_query()`,
   `runner.run_wrap_check()`, etc., which trigger real Gemini API calls.

## No Other AI Models Used

CONTINUUM uses **exclusively** Google Cloud AI tools. No OpenAI, Anthropic, AWS,
or other AI APIs are present in the codebase.

Verified by: `grep -rn 'openai\|anthropic\|aws.*ai\|langchain\|cohere\|mistral' src/` → 0 results.

The vision subsystem's provider allow-list (`src/continuum/vision/registry.py`)
restricts every engine to Google Cloud SDKs, and `tests/vision/test_registry.py`
asserts this at test time so a non-Google provider cannot be added silently.

See also: `compliance/vision_blueprint_note.md` (disclosure that the vision
subsystem's *idea* originated from a prior internal project; no code or
architecture from that project ships in this repository).
