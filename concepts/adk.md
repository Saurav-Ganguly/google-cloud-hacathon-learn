# ADK — Agent Development Kit

**URL**: https://adk.dev
**Languages**: Python, TypeScript, Java, Go
**Open source**: yes
**pip package**: `google-adk`

## Core Idea

Code-first framework. Define a `root_agent` in `agent.py` — that's the only required element.

```python
from google.adk.agents.llm_agent import Agent
from google.adk.models.gemini import Gemini

root_agent = Agent(
    name="my_agent",
    model=Gemini(model="gemini-flash-latest"),
    instruction="...",
    tools=[my_tool],          # optional
)
```

## Project Structure

```
my_agent/
  agent.py       # root_agent definition
  .env           # env vars
  __init__.py
```

**.env required vars:**
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

## Setup

```bash
uv add google-adk
adk create my_agent
cd my_agent
adk run my_agent         # CLI interactive
adk web --port 8000      # Web UI
```

## agents-cli Integration

The `agents-cli` wraps the full agent lifecycle. Use it via your coding agent (Claude Code, Gemini CLI, etc.):

```bash
# Install
pip install agents-cli   # or check agents-cli docs for uv method

# Scaffold
agents-cli create my-agent --prototype --yes
cd my-agent && agents-cli install

# Run
agents-cli run "test prompt"

# Evaluate
agents-cli eval run      # runs tests/eval/evalsets/*.evalset.json

# Deploy to Cloud Run
agents-cli scaffold enhance --deployment-target cloud_run
agents-cli deploy

# Observability infra
agents-cli infra single-project   # provisions SA + GCS + BigQuery
```

Eval config lives in `tests/eval/eval_config.json` (LLM-as-judge criteria).

## Agent Types

- Sequential agents
- Graph-based deterministic agents
- Multi-agent systems (via [[concepts/a2a]])

## Tool Integration

- [[concepts/mcp]] — connect any MCP server as tools
- [[concepts/a2a]] — talk to other agents

## Supports

- Any model: Gemini, Anthropic, Ollama
- ADK agents deploy to [[concepts/agent-runtime]] or Cloud Run or GKE

## Related

- [[concepts/vertex-ai]] — Platform that ships ADK
- [[resources/day 1/What is Gemini Enterprise Agent Platform/notes]] — intro video
- [[resources/agent-platform-onboard/notes]] — hands-on setup guide
