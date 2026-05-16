# Gemini Enterprise Agent Platform — Onboarding Guide

**Source**: [goo.gle/agent-platform-onboard](https://goo.gle/agent-platform-onboard)
**Author**: Eric Dong, Apr 22 2026

## What It Is

Step-by-step onboarding from zero to deployed autonomous AI agents on Google Cloud. Three entry paths depending on how much code you want to write.

---

## Three Quick Starts

### QS1: Agent Studio — Prompt → Cloud Run App

No code. UI-only path.

1. Console → Agent Platform → Studio → New Chat
2. Set system instructions + prompt in editor
3. Test interactively
4. Click **Code → Deploy → Cloud Run → Deploy as app**
5. Get a public URL with a chat UI in minutes

Use case: rapid prototype, demo, stakeholder sign-off before investing in code.

Note: First deploy may fail (permissions propagation). Click "Update app" after ~1 min to retry.

### QS2: Agent Designer — Low-Code Visual Builder

1. Agent Studio → Agent tab → Create agent
2. **Flow tab**: visual canvas, define agent + subagents
3. **Preview tab**: test via chat as you build
4. Pre-built tools: Google Search, URL Context (add more with +)
5. Click **Get code** → exports as ADK-compatible Python
6. Click **Deploy** → goes to Agent Runtime instance

Use case: design visually, then graduate to code via ADK.

### QS3: ADK + agents-cli — Full Code Path

The serious path. Uses Claude Code (or Gemini CLI / Codex) as the orchestrator.

**Workflow** (natural language → working deployed agent):

| You say | agents-cli does |
|---|---|
| "Build a caveman compressor agent" | Scaffold project, write agent.py, test locally |
| "Write evals and run them" | Create evalset.json, configure LLM-as-judge, run `agents-cli eval run` |
| "Deploy this to Cloud Run" | Add deployment infra, run `agents-cli deploy` |
| "Set up observability" | Provision service account, GCS bucket, BigQuery dataset |

**Key commands:**
```bash
agents-cli create caveman-agent --prototype --yes
cd caveman-agent && agents-cli install
agents-cli run "test prompt here"
agents-cli eval run
agents-cli scaffold enhance --deployment-target cloud_run
agents-cli deploy
```

**Minimal agent structure:**
```python
from google.adk.agents.llm_agent import Agent
from google.adk.models.gemini import Gemini

root_agent = Agent(
    name="my_agent",
    model=Gemini(model="gemini-flash-latest"),
    instruction="...",
    tools=[my_tool],
)
```

**Project layout after `adk create`:**
```
my_agent/
  agent.py      # root_agent lives here
  .env          # GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI
  __init__.py
```

---

## API Setup (one-time per project)

### 1. Project + Billing
- Console → Agent Platform → create/select project
- Billing must be enabled

### 2. gcloud CLI
```bash
gcloud init
```

### 3. Enable APIs
```bash
gcloud services enable aiplatform.googleapis.com
# or use Console → Enable APIs button
```

### 4. Authentication (choose one)

| Method | Best for |
|---|---|
| ADC (recommended) | Local dev on your own machine |
| API Key | Quickest for prototyping |
| Service Account | Hosted apps, CI/CD |

```bash
# ADC (recommended)
gcloud auth application-default login
gcloud auth application-default set-quota-project [PROJECT_ID]
```

### 5. SDK Initialization

| SDK | Package | When to use |
|---|---|---|
| Google Gen AI SDK | `google-genai` | Talk to Gemini, Imagen, Veo |
| Vertex AI SDK | `google-cloud-aiplatform` | MLOps, model training, endpoints |
| ADK | `google-adk` | Build/deploy autonomous agents |

```python
# Gen AI SDK — simplest path to Gemini
from google import genai
client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
response = client.models.generate_content(model="gemini-3.1-pro-preview", contents="...")

# ADK — for agent development
# install: pip install google-adk (or uv add google-adk)
# create: adk create my_agent
# run: adk run my_agent  OR  adk web --port 8000
```

---

## Observe in Production

Cloud Trace enabled by default — no setup needed. For full prompt/response logging:
```
"Set up observability infrastructure for my agent"
```
This provisions: service account + GCS bucket + BigQuery dataset.

---

## Related Concepts

- [[concepts/vertex-ai]] — Platform overview
- [[concepts/adk]] — ADK deep dive
- [[concepts/agent-runtime]] — Managed deployment target
- [[concepts/mcp]] — Adding external tools
