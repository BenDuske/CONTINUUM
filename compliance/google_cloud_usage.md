# Google Cloud Usage Evidence

**Requirement:** Must use Gemini and Google Cloud Agent Builder.

## Runtime Integration Points

| Component | Google Cloud Service | Package |
|---|---|---|
| AI Reasoning | Gemini 2.5 Flash / Pro | `google-genai` |
| Agent Framework | Agent Development Kit (ADK) 2.0 | `google-adk` |
| Agent Engine | Vertex AI Agent Engine | `google-cloud-aiplatform` |
| Deployment | Cloud Run | (infrastructure) |

## Agent Definitions

All agents use `google.adk.agents.Agent` with `model="gemini-2.5-flash"`:
- `continuum_director` — orchestrator
- `storygraph` — narrative analysis
- `continuity` — consistency checking
- `final_take` — coverage assessment
- `cascade` — change-impact analysis
- `skeptic` — adversarial verification

## No Other AI Models Used

CONTINUUM uses **exclusively** Google Cloud AI tools. No OpenAI, Anthropic, AWS, or other AI APIs.
