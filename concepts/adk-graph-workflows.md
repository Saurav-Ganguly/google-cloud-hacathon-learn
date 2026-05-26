# ADK Graph-Based Workflows

> **ADK 2.0 — actively evolving.** Reference doc. For a learn-by-doing walkthrough see [[concepts/adk-graph-workflows-tutorial]].
>
> **Reference template**: `test/idea_refiner/` — full end-to-end sandbox exercising every primitive below (verified 2026-05-26).

## What it is

Graph-based workflows let you wire agent logic as an explicit graph of
**nodes** connected by **edges**. Each node can be an `Agent`, a plain
Python function, a `JoinNode`, a `RequestInput` (human-in-the-loop), or
a nested `Workflow`. Edges define the order, branches, and joins.

The point is **precise control**. A prompt-orchestrated coordinator
([[concepts/adk-multi-agent]]) lets the LLM decide what runs next; a
graph lets *you* decide, in code, with the LLM doing reasoning only at
the nodes you place. That trades flexibility for predictability — the
right call when the process has known steps, mandatory gates, or hard
routing rules.

---

## When to reach for it

| Need | Best tool |
|---|---|
| Linear A→B→C, no branching | `SequentialAgent` |
| LLM decides who handles what | Coordinator + `sub_agents` ([[concepts/adk-multi-agent]]) |
| **Conditional branching, parallel + join, HITL gates, mixed code/LLM nodes** | **`Workflow` graph** |
| Iterate-until-pass | `LoopAgent` |

Reach for a graph workflow when you find yourself writing branching
logic inside a coordinator prompt, or chaining `SequentialAgent`s with
custom routing glue. The graph makes the flow first-class instead of
hiding it in instruction strings.

---

## Core primitives

- **`Workflow`** — the graph container. Takes an `edges` array.
- **Node** — anything that can run:
  - `Agent` (LlmAgent in task / `single_turn` mode)
  - plain Python function (a "FunctionNode")
  - `JoinNode`
  - `RequestInput` (HITL)
  - another `Workflow` (nested)
- **Edge** — a tuple in the `edges` array describing sequence,
  branching, or joining.
- **`Event`** — the data bus. Every node consumes one and emits one.

---

## The `Workflow` class

```python
from google.adk import Workflow

root_agent = Workflow(
    name="my_workflow",
    edges=[
        ("START", node_a, node_b, node_c),
    ],
)
```

- `name` — identifies the workflow.
- `edges` — list of tuples. The first element of the first row is the
  literal string `"START"`.
- Each tuple after the first describes additional routing (branches,
  joins, nested graph hookups).

See [[concepts/adk-graph-workflows-tutorial]] §wireframe for the same
shape used end-to-end.

---

## The `Event` class — the data bus

Every node receives a `node_input` (the previous node's `Event.output`)
and emits an `Event`. The four useful parameters:

```python
from google.adk import Event

# 1. output — payload for the NEXT node
return Event(output="the result")

# 2. message — text shown to the USER mid-run
yield Event(message="Beginning research process...")

# 3. state — small KV bag persisted across nodes for this run
yield Event(state={"attempts": 1})

# 4. route — string used by a branching edge dict (see Edge syntax)
return Event(route="BUG")
```

`yield` vs `return`:
- `return Event(...)` — emit once and exit. Use when the node has one
  result and no further processing.
- `yield Event(...)` — emit one or more `Event`s; each call appends to
  a list passed to the next node. Use when the node produces multiple
  data items (e.g. several `message`s before the final `output`).
- `return` or `yield` with no argument passes `None` to the next node.

**Caution: one `Event.output` per node.** You can `yield` many times,
but more than one `yield Event(output=...)` in the same node is a
runtime error. Use a single `output` payload (a list, dict, or
Pydantic model) if you need to pass multiple items.

**Caution: `state` is not artifact storage.** Event.state persists
across nodes in the same run, but it's meant for tiny scalars
(counters, flags, IDs). Do not stash large blobs there — use ADK
artifacts or a database tool instead. (Separate from session-wide
`session.state`; see [[concepts/adk-session-state]].)

---

## Node types

### FunctionNode (Python function wrapped as a node)

Wrap a sync/async function or generator in `FunctionNode`:

```python
from google.adk import Event
from google.adk.workflow import FunctionNode

def _shout(node_input: str):
    yield Event(output=node_input.upper())

shout = FunctionNode(func=_shout, name="shout")
```

- The wrapped function may declare `node_input: <Type>` — ADK auto-coerces
  the upstream output to that Pydantic model.
- It may also declare extra parameters by name (e.g. `idea: str`,
  `refinement_attempts: int = 0`) — those are looked up in `session.state`.
  This is the **state binding** mode (default).
- **For generator functions, the routing Event MUST be `yield`ed, not
  `return`ed** — `return Event(...)` in a generator gets dropped
  (StopIteration.value is not surfaced). Use `yield Event(route=..., output=...)`
  as the final statement.

### Agent node (must be task / single-turn mode)

`LlmAgent` works as a node, but **must be in single-turn / task mode**:

```python
from google.adk import Agent

classifier = Agent(
    name="classify_ticket",
    model="gemini-flash-latest",
    instruction="Classify as BUG, SUPPORT, or LOGISTICS.",
    output_schema=str,
    mode="single_turn",     # CAUTION: required when used inside a Workflow
)
```

All the usual [[concepts/adk-llm-agent-config]] knobs apply
(`output_schema`, `input_schema`, `generate_content_config`, etc.),
just with the single-turn mode constraint.

**Caution: multi-turn agents inside graphs.** You cannot run an
interactive chat session as a graph node — graphs need each node to
return promptly to the next edge.

### JoinNode (parallel + join)

Waits for *all* upstream branches to emit an `Event`, then passes the
collected outputs as a list to the next node:

```python
from google.adk.workflow import JoinNode

collect = JoinNode(name="collect_results")

edges = [
    ("START", branch_a, collect),
    ("START", branch_b, collect),
    ("START", branch_c, collect),
    (collect, summarize),
]
```

**Caution: a stuck upstream stalls the whole join.** If any branch
fails silently and never emits, the `JoinNode` waits forever and the
workflow halts. Always emit a failsafe `Event` (even an empty
`Event()`) from every branch that feeds a join.

### RequestInput (human-in-the-loop)

Pauses the workflow and prompts the user for input:

```python
from google.adk.events import RequestInput

def approval_gate(node_input):
    yield RequestInput(
        message="Approve this draft reply?",
        payload=node_input,                # structured data shown to user
        response_schema=ApprovalDecision,  # how the user's reply will be parsed
    )
```

Parameters:
- `message` — prompt shown to the user.
- `payload` — structured object presented alongside the message.
- `response_schema` — the user's reply must conform to this shape.

**Caution: response_schema does NOT auto-reformat.** ADK does not coerce
free-text user replies into the schema. Either provide a UI that
collects structured input, or place an `Agent` node after the
`RequestInput` to normalize the response.

### Nested Workflow (Workflow-as-node)

A `Workflow` can be a node inside another `Workflow`:

```python
bug_branch = Workflow(name="bug_branch", edges=[...])
support_branch = Workflow(name="support_branch", edges=[...])

root_agent = Workflow(
    name="parent",
    edges=[
        ("START", classify, router),
        (router, {"BUG": bug_branch, "SUPPORT": support_branch}),
    ],
)
```

Event semantics with nested workflows:
- Nodes inside the nested workflow emit Events as normal.
- Those Events also **bubble up** to the parent workflow's event
  stream, so traceability is preserved.
- The nested workflow's *final* leaf node's output is what the parent
  receives as the nested node's output.

---

## Edge syntax

```python
# Sequential — A then B then C
edges = [("START", a, b, c)]

# Multiple START rows = parallel kickoff
edges = [
    ("START", task_a),
    ("START", task_b),
    ("START", task_c),
]

# Branching — router emits Event(route="X"); dict maps to handlers
edges = [
    ("START", classifier, router),
    (router, {
        "BUG":     handle_bug,
        "SUPPORT": handle_support,
        "LOGISTICS": handle_logistics,
    }),
]

# Parallel + join
edges = [
    ("START", enrich_a, join),
    ("START", enrich_b, join),
    ("START", enrich_c, join),
    (join, drafter),
]
```

Rules:
- The first row's first element is the string `"START"`.
- More than one `"START"` row launches those rows in parallel.
- A branching dict node must be paired with a previous node that emits
  `Event(route="<key>")`.

**Caution: not everything parallelizes.** You cannot run two
interactive chat-style agents in the same session in parallel. Stick
to function nodes or single-turn agent nodes for parallel branches.

---

## Per-node schemas

Both `input_schema` and `output_schema` work on any node — not just
agents:

```python
from pydantic import BaseModel

class Ticket(BaseModel):
    id: str
    body: str
    severity: int

def enrich(node_input: Ticket):
    return Event(output={"enriched": node_input.body.upper()})

enrich_node = Agent(            # same idea on an Agent node
    name="enrich",
    input_schema=Ticket,
    output_schema=EnrichedTicket,
    mode="single_turn",
    ...
)
```

Schemas validate at the node boundary — a malformed input raises
before the node runs, which surfaces routing bugs early.

See [[concepts/adk-llm-agent-config]] for the same `input_schema`
/`output_schema` parameters on standalone agents.

---

## Templating into agent instructions

> **Correction (2026-05-26, verified against `google-adk==2.0.x`):** the
> `{ClassName.field}` and `<ClassName.field from source_node>` syntax shown
> in the ADK 2.0 docs **does NOT exist in `inject_session_state`** — the
> only instruction-templating function. That function (`utils/instructions_utils.py:127-149`)
> only substitutes `{simple_identifier}` where the identifier is a valid
> Python name (optionally with `app:` / `user:` / `temp:` prefix or a `?`
> optional marker). Anything that isn't a valid identifier — including
> `ClassName.field` — is **left literal in the prompt**.

The working pattern, demonstrated in `test/idea_refiner/`:

1. Upstream **FunctionNode** writes individual scalars to `session.state`
   via `Event(state={...})` or `ctx.state[...] = ...`.
2. Downstream **Agent** templates each value with `{simple_key}`.
3. `input_schema` is still useful — it validates the data-bus payload —
   but it does NOT enable `{ClassName.field}` templating.

```python
# 1) FunctionNode unpacks a Pydantic object into individual state keys
def split_prompts(node_input: ResearchPrompts):
    yield Event(
        output=node_input,
        state={
            "idea":          node_input.idea,
            "market_prompt": node_input.market_prompt,
            "tech_prompt":   node_input.tech_prompt,
        },
    )

# 2) Downstream Agent reads via simple-identifier templating
market_research = Agent(
    name="market_research",
    instruction="Idea: {idea}\n\nBrief:\n{market_prompt}\n\n...",
    mode="single_turn",
)
```

Optional marker: `{var?}` returns empty string if `var` is missing from
state instead of raising `KeyError`. Useful for keys that may or may not
be set on a given path (e.g. `{refinement_attempts?}`).

---

## Cautions / gotchas

- **`Event.output` is one-per-node.** Yielding two of them is a
  runtime error.
- **`Event.state` is for tiny scalars only.** Use artifacts or DB
  tools for large data — graphs make data-flow explicit, abusing
  state hides it.
- **`JoinNode` hangs on any incomplete upstream.** Always emit a
  failsafe `Event()` from every branch that feeds a join.
- **Agents inside graphs MUST run in single-turn / task mode**
  (`mode="single_turn"`). Multi-turn chat agents cannot be graph
  nodes — they don't return promptly.
- **Live Streaming is not compatible with graph workflows.** If you
  need voice/streaming, use a streaming agent
  ([[resources/day 1/Introducing Agents CLI in Agent Platform/notes]]
  Live patterns), not a graph.
- **Some third-party integrations are not compatible** with graphs;
  consult the integration's docs before placing it in a graph node.
- **Branch handlers should always return something.** A branching dict
  picks exactly one handler — if that handler quietly returns `None`,
  downstream nodes get `None` as their `node_input`.

---

## VERIFIED imports (2026-05-26)

All resolved against the installed `google-adk` package while building
`test/idea_refiner/`:

```python
from google.adk import Workflow, Event
from google.adk.agents import LlmAgent
from google.adk.events import RequestInput
from google.adk.workflow import FunctionNode, JoinNode
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
```

- `FunctionNode` **is a real class** — wrap functions, don't rely on
  bare-function detection: `FunctionNode(func=my_fn, name="my_fn")`.
- `Agent` mode parameter: `mode="single_turn"` (exact string).
- `RequestInput` parameter: `responseSchema` (camelCase), not
  `response_schema`. Often omitted because the framework does NOT coerce
  free-text user replies — leave it unset and let a downstream node
  normalise.
- **Cycles** are validated by `workflow/_graph.py:381-417`: rejected
  only if EVERY edge in the cycle is unconditional. A cycle with at
  least one routed edge is fine. `test/idea_refiner/` has two such
  cycles (HITL re-prompt, refinement loop).

---

## Related

- [[concepts/adk]] — base ADK primitives and built-in workflow agents.
- [[concepts/adk-multi-agent]] — prompt-orchestrated coordinator,
  the alternative when you want the LLM to choose the path.
- [[concepts/adk-llm-agent-config]] — every `LlmAgent` knob still
  applies to agents used as graph nodes (modulo `mode="single_turn"`).
- [[concepts/adk-session-state]] — global `session.state` is *separate*
  from a graph's per-run `Event(state=...)` bag.
- [[concepts/adk-graph-workflows-tutorial]] — single end-to-end worked
  example exercising every primitive above.
