# ADK Graph-Based Workflows

> **ADK 2.0 — Beta.** Not production-ready yet.

## What They Are

Graph-based workflows let you build agents with explicit control flow — combining code logic and AI reasoning as a network of nodes and edges. Each node can be an AI agent, a tool, or plain Python code.

**When to use over SequentialAgent:**
- You need conditional branching (if this → go there, else → go somewhere else)
- You need parallel fan-out + join
- You want human input gates mid-pipeline
- You want some nodes to skip the LLM entirely

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| `Workflow` | Assembles the graph; takes an `edges` parameter |
| Node | Any callable: an `Agent`, a plain Python function, or `JoinNode` |
| Edge | A tuple defining connections between nodes |
| Route | A string returned from a node to control which branch executes next |
| `JoinNode` | Waits for all parallel branches to complete before continuing |

---

## Edge Definition Format

```python
from google.adk.workflows import Workflow  # ADK 2.0

# Sequential: A → B → C
Workflow(edges=[("START", node_a, node_b, node_c)])

# Conditional routing: router decides which branch
Workflow(edges=[
    ("START", router_fn),
    (router_fn, {
        "ROUTE_A": handler_a,
        "ROUTE_B": handler_b,
    }),
])

# Parallel fan-out + join
Workflow(edges=[
    ("START", task_a, task_b),   # both start in parallel
    (task_a, join),
    (task_b, join),
    (join, final_step),
])
```

---

## Routing Nodes

A routing function returns an `Event` with a `route` value:

```python
from google.adk.events import Event

def router(node_input: str) -> Event:
    if "urgent" in node_input.lower():
        return Event(route="PRIORITY")
    return Event(route="STANDARD")
```

An LLM agent can also be a routing node — its output schema determines the route value.

---

## Agent Nodes

Use ADK agents as nodes — they get the same session context:

```python
from google.adk.agents import Agent

classifier = Agent(
    name="classifier",
    model="gemini-flash-latest",
    instruction="Classify the input as TECHNICAL or GENERAL. Output only the label.",
    output_key="classification",
)

technical_handler = Agent(
    name="technical",
    model="gemini-flash-latest",
    instruction="Answer the technical question: {input}",
)
```

---

## Sub-pages (ADK 2.0 docs)

- `adk.dev/workflows/graph-routes/` — routing patterns
- `adk.dev/workflows/data-handling/` — passing data between nodes
- `adk.dev/workflows/human-input/` — human-in-the-loop gates
- `adk.dev/workflows/` — overview

---

## Key Differences from Workflow Agents

| | Workflow Agents (ADK 1.x) | Graph Workflows (ADK 2.0) |
|---|---|---|
| Branching | No (sequential/parallel fixed) | Yes (conditional routing) |
| Non-LLM nodes | No | Yes (plain Python functions) |
| Parallel + join | Limited | `JoinNode` |
| Maturity | Stable | Beta |

---

## Related

- [[concepts/adk]] — core ADK concepts and workflow agents
- [[concepts/adk-multi-agent]] — multi-agent coordination patterns
