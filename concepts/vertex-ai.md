# Vertex AI / Gemini Enterprise Agent Platform

**Also known as**: Gemini Enterprise Agent Platform (rebranding of Vertex AI)
**Console**: https://console.cloud.google.com/agent-platform/overview
**Phases**: Build → Scale → Govern → Optimize

## Three Entry Paths

| Path | Tool | Code level | Best for |
|---|---|---|---|
| QS1 | Agent Studio (Chat/Prompt) | None | Rapid prototype, demo |
| QS2 | Agent Designer | Low-code visual | Design first, code later |
| QS3 | ADK + agents-cli | Full code | Production agents |

## Key Components

- [[concepts/adk]] — Core build framework (code-first)
- [[concepts/mcp]] — Tool integration standard
- [[concepts/a2a]] — Multi-agent communication
- [[concepts/agent-runtime]] — Managed deployment (Agent Designer → Deploy)

## Agent Studio

UI at Console → Agent Platform → Studio. Supports:
- Chat, Image, Video, Music, Speech, Live API sessions
- System instructions + prompt editor
- One-click deploy to Cloud Run as a web app
- Export code (ADK-compatible Python) via **Code** button

## Agent Designer

Visual canvas inside Agent Studio (Agent tab):
- **Flow tab**: define agents, subagents, control logic
- **Preview tab**: chat with agent live while building
- Built-in tools: Google Search, URL Context
- Export to ADK code → `agents-cli` → Agent Runtime

## Three SDKs

| SDK | pip package | Focus |
|---|---|---|
| Google Gen AI SDK | `google-genai` | Gemini, Imagen, Veo — generative models |
| Vertex AI SDK | `google-cloud-aiplatform` | MLOps, training, endpoints |
| ADK | `google-adk` | Autonomous multi-agent systems |

## Required API

```bash
gcloud services enable aiplatform.googleapis.com
```

## Deep Dive

- [[resources/day 1/What is Gemini Enterprise Agent Platform/notes]] — overview video
- [[resources/agent-platform-onboard/notes]] — step-by-step onboarding guide
