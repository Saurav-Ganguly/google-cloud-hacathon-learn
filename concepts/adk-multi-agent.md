# ADK Multi-Agent Systems

## What They Are

A multi-agent system is an application where multiple `BaseAgent` instances collaborate in a hierarchy to achieve a larger goal. Different agents specialize in different tasks; coordination happens through state, delegation, or explicit tool calls.

**Why use them:**
- Modularity — each agent has a single responsibility
- Specialization — route to the right expert
- Reusability — agents can be shared across systems
- Structured control — workflow agents orchestrate LLM agents

---

## Agent Hierarchy

Agents form parent-child relationships via `sub_agents`:

```python
coordinator = Agent(
    name="coordinator",
    instruction="Route to sales_agent for sales, support_agent for support.",
    sub_agents=[sales_agent, support_agent],
)
```

**Rules:**
- Each agent instance can only have ONE parent
- Use factory functions to reuse an agent in multiple places:

```python
def create_researcher():
    return Agent(name="researcher", ...)

pipeline = SequentialAgent(sub_agents=[create_researcher(), create_analyst()])
```

---

## 3 Communication Mechanisms

### 1. Shared Session State

Agents in the same invocation share `session.state`. Use `output_key` to write:

```python
agent_a = Agent(name="a", output_key="a_result", ...)
agent_b = Agent(name="b", instruction="Use this: {a_result}", ...)

pipeline = SequentialAgent(sub_agents=[agent_a, agent_b])
```

State prefixes control scope:
```python
state["result"] = ...          # session-scoped
state["user:pref"] = ...       # user-persistent
state["app:counter"] = ...     # app-wide
state["temp:scratch"] = ...    # current invocation only
```

### 2. LLM-Driven Delegation (transfer_to_agent)

The LLM autonomously calls `transfer_to_agent(agent_name='target')`. The `description` field is what the parent LLM reads to decide routing.

```python
# Parent sees description, routes based on it
specialist = Agent(
    name="billing_agent",
    description="Handles billing questions, invoices, payment issues.",
    ...
)
coordinator = Agent(
    name="coordinator",
    sub_agents=[specialist, ...],
)
```

Delegation control:
```python
agent = Agent(
    disallow_transfer_to_parent=True,  # can't escalate up
    disallow_transfer_to_peers=True,   # can't route sideways
)
```

### 3. AgentTool (explicit invocation)

Parent stays in control; specialist is called as a tool and returns a result:

```python
from google.adk.tools import AgentTool

root = Agent(
    name="root",
    tools=[AgentTool(specialist_agent)],
)
```

**AgentTool vs sub_agents:**

| | `sub_agents` (LLM delegation) | `AgentTool` |
|---|---|---|
| Who controls flow | LLM decides to transfer | Parent agent explicitly calls |
| Return behavior | Agent takes over conversation | Returns result, parent continues |
| Use when | Dynamic routing needed | Parent needs specialist output |

---

## Common Patterns

### Coordinator / Dispatcher

```python
coordinator = Agent(
    name="coordinator",
    instruction="Route to the right specialist based on the query.",
    sub_agents=[billing_agent, technical_agent, general_agent],
)
```

### Sequential Pipeline (data flows through state)

```python
pipeline = SequentialAgent(sub_agents=[
    ingester,      # output_key="raw_data"
    processor,     # instruction="Process: {raw_data}", output_key="processed"
    formatter,     # instruction="Format: {processed}"
])
```

### Parallel Fan-Out + Gather

```python
pipeline = SequentialAgent(sub_agents=[
    ParallelAgent(sub_agents=[
        Agent(name="fetch_news", output_key="news"),
        Agent(name="fetch_weather", output_key="weather"),
        Agent(name="fetch_stocks", output_key="stocks"),
    ]),
    Agent(
        name="merger",
        instruction="Combine: news={news}, weather={weather}, stocks={stocks}",
    ),
])
```

### Generator-Critic Loop

```python
loop = LoopAgent(
    sub_agents=[
        generator,          # output_key="draft"
        critic,             # output_key="feedback", grades as pass/fail
        escalation_checker, # escalates if grade=="pass"
    ],
    max_iterations=5,
)
```

### Hierarchical Decomposition

```python
root = Agent(
    name="project_manager",
    sub_agents=[
        SequentialAgent(name="research_pipeline", sub_agents=[...]),
        SequentialAgent(name="writing_pipeline", sub_agents=[...]),
        Agent(name="reviewer"),
    ],
)
```

---

## A2A Protocol (cross-system agents)

For agents that live in separate services or languages, ADK supports the Agent-to-Agent (A2A) protocol:

```python
# Expose an agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
to_a2a(root_agent, port=8001)

# Consume a remote agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
remote = RemoteA2aAgent(
    name="remote_specialist",
    description="...",
    agent_card=f"http://remote-host:8001{AGENT_CARD_WELL_KNOWN_PATH}",
)
# Then use remote like any sub_agent or AgentTool
```

Requires: `uv add "google-adk[a2a]"` — see [[concepts/a2a]] for full details.

---

## Related

- [[concepts/adk]] — core primitives, agent types, workflow agents
- [[concepts/adk-graph-workflows]] — graph-based conditional workflows (ADK 2.0)
- [[concepts/a2a]] — Agent-to-Agent protocol
