# ADK — Agent Development Kit

**URL**: https://adk.dev
**Languages**: Python, TypeScript, Java, Go
**Open source**: yes
**pip package**: `google-adk`

## Core Idea

Code-first framework. Define a `root_agent` in `agent.py` — that's the only required element.

```python
from google.adk.agents.llm_agent import Agent

def get_weather(city: str) -> dict:
    """Returns weather for a city."""
    return {"status": "success", "weather": "sunny"}

root_agent = Agent(
    name="weather_agent",
    model="gemini-flash-latest",
    instruction="You help users check the weather. Use get_weather tool.",
    description="Provides weather information.",
    tools=[get_weather],
)
```

---

## Architecture: 6 Core Primitives

| Primitive | Role |
|-----------|------|
| **Agent** | The execution unit — LLM-driven (`LlmAgent`) or deterministic (`SequentialAgent`, etc.) |
| **Tool** | Extends agent capability — external APIs, code execution, other agents |
| **Session** | A single conversation thread: history (Events) + short-term memory (State) |
| **State** | Key-value dict inside a Session for working memory; supports prefixes |
| **Event** | Atomic unit: user input, agent response, tool invocations — forms conversation history |
| **Runner** | Orchestration engine; manages execution flow, coordinates backend services |
| **Memory** | Long-term memory *across* sessions (distinct from session State) |

**Flow**: `Runner` receives user message → creates `Event` → routes to `Agent` → agent reasons with LLM, calls `Tools`, writes to `State` → yields `Events` back → loop

---

## Project Structure

```
my_agent/
  agent.py       # root_agent definition (required)
  .env           # env vars
  __init__.py
tests/
  eval/
    eval_config.json
    evalsets/
```

**.env for Vertex AI:**
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

**.env for AI Studio (dev):**
```
GOOGLE_API_KEY=your-key
GOOGLE_GENAI_USE_VERTEXAI=False
```

## Setup

```bash
uv add google-adk
adk create my_agent
adk run my_agent         # CLI interactive
adk web --port 8000      # Web UI at localhost:8000
adk api_server my_agent  # FastAPI server
```

---

## Agent Types

Three categories, often combined in real systems:

| Type | Class | When to use |
|------|-------|-------------|
| **LLM Agent** | `Agent` / `LlmAgent` | Dynamic decisions, natural language tasks, flexible routing |
| **Workflow Agent** | `SequentialAgent`, `ParallelAgent`, `LoopAgent` | Deterministic pipelines, structured processes, predictable execution |
| **Custom Agent** | `BaseAgent` subclass | Unique orchestration logic, conditional routing, specialized integrations |

Real systems combine them: LLM agents handle reasoning, workflow agents handle orchestration, custom agents handle special cases.

---

## LLM Agent — Full Configuration

```python
from google.adk.agents import Agent
from google.genai import types as genai_types

agent = Agent(
    # Identity
    name="my_agent",            # required; avoid reserved name "user"
    model="gemini-flash-latest", # required
    description="...",           # used by other agents for routing decisions

    # Behavior
    instruction="You are a {role} assistant. Preferences: {user_preferences?}",
    # {key} injects state value; {key?} is optional (no error if undefined)

    # Tools
    tools=[my_tool, AgentTool(specialist_agent)],

    # Output
    output_schema=MyPydanticModel,  # DISABLES tool calling (except Gemini 3.0+)
    output_key="agent_response",    # saves final text to session state

    # Context
    input_schema=InputModel,
    include_contents='default',     # 'default' = history sent | 'none' = stateless

    # LLM parameters
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1024,
    ),

    # Advanced reasoning
    planner=BuiltInPlanner(),       # uses model's thinking feature
    # or: planner=PlanReActPlanner() — structured plan-then-execute

    code_executor=BuiltInCodeExecutor(),  # allows agent to run code

    # Delegation control
    disallow_transfer_to_parent=False,
    disallow_transfer_to_peers=False,
    sub_agents=[specialist_agent],

    # Callbacks
    before_agent_callback=my_callback,
    after_agent_callback=my_callback,
    before_model_callback=my_callback,
    after_model_callback=my_callback,
    before_tool_callback=my_callback,
    after_tool_callback=my_callback,
)
```

**Gotchas:**
- `output_schema` disables tools unless Gemini 3.0+ model
- `{key}` in instruction raises error if state key missing; use `{key?}` for optional
- Avoid agent name "user" (reserved)
- `description` is what *other* agents read to decide if they should route here

---

## Workflow Agents

Deterministic — no LLM decides the flow.

### SequentialAgent
Runs sub-agents one-by-one in order. State from earlier agents flows to later ones via `output_key`.

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[fetcher, summarizer, formatter],
)
```

### ParallelAgent
Runs sub-agents concurrently. Use distinct `output_key` per agent to avoid race conditions.

```python
from google.adk.agents import ParallelAgent, SequentialAgent

parallel = ParallelAgent(name="fetchers", sub_agents=[fetch_a, fetch_b])
pipeline = SequentialAgent(name="full", sub_agents=[parallel, merger])
```

### LoopAgent
Repeats sub-agents until `max_iterations` or an `escalate=True` event.

```python
from google.adk.agents import LoopAgent

loop = LoopAgent(
    name="refinement",
    sub_agents=[evaluator, refiner, escalation_checker],
    max_iterations=5,
)
```

Escalation checker pattern:
```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

class EscalationChecker(BaseAgent):
    async def _run_async_impl(self, ctx):
        result = ctx.session.state.get("evaluation")
        if result and result.get("grade") == "pass":
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)
```

---

## Custom Agents (BaseAgent)

For logic you can't express with workflow agents.

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator
from google.adk.events import Event

class ConditionalRouter(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_type = ctx.session.state.get("user_type", "regular")
        agent = self.premium_agent if user_type == "premium" else self.regular_agent
        async for event in agent.run_async(ctx):
            yield event
```

**Factory function pattern** (avoids "agent already has a parent" error):
```python
def create_researcher():
    return Agent(name="researcher", ...)

root = SequentialAgent(sub_agents=[create_researcher(), create_analyst()])
# Always CALL the factory — passing the function reference causes ValidationError
```

---

## Multi-Agent Communication

Three patterns:

1. **Shared State** — agents read/write `session.state` via `output_key`
2. **LLM Delegation** — agent transfers control to sub-agent based on reasoning
3. **AgentTool** — parent invokes another agent as a tool (parent stays in control)

```python
from google.adk.tools import AgentTool

root = Agent(
    name="root",
    tools=[AgentTool(specialist_agent)],
)
```

---

## agents-cli Integration

The `agents-cli` wraps the full agent lifecycle:

```bash
agents-cli scaffold create my-agent --template adk_base --yes
cd my-agent && agents-cli install

agents-cli run "test prompt"
agents-cli eval run
agents-cli scaffold enhance --deployment-target cloud_run
agents-cli deploy
agents-cli infra single-project
```

See [[configs/agents-cli-setup]] for auth setup and Windows gotchas.
See [[configs/run-agent-locally]] for local-run runbook (InMemoryRunner pattern).

---

## State Prefixes

```python
state["booking_step"] = 2           # session-scoped (default)
state["user:preferred_lang"] = "en" # user-persistent (across sessions)
state["app:total_queries"] = 1000   # app-wide (all users)
state["temp:intermediate"] = data   # current invocation only
```

---

## Running Programmatically

```python
from google.adk.runners import InMemoryRunner
from google.genai import types

runner = InMemoryRunner(agent=root_agent, app_name="my_app")
session = await runner.session_service.create_session(
    app_name="my_app", user_id="user1"
)
async for event in runner.run_async(
    user_id="user1",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part.from_text("Hello!")]),
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

---

## Related

- [[concepts/adk-graph-workflows]] — graph-based deterministic workflows (ADK 2.0)
- [[concepts/adk-multi-agent]] — multi-agent system patterns
- [[concepts/adk-mcp-integration]] — connecting MCP servers to ADK agents
- [[concepts/adk-ambient-agents]] — background/event-driven agents (ADK 2.0)
- [[concepts/mcp]] — Model Context Protocol overview
- [[concepts/a2a]] — Agent-to-Agent protocol
- [[concepts/agent-runtime]] — managed PaaS deployment target
- [[concepts/vertex-ai]] — platform that ships ADK
