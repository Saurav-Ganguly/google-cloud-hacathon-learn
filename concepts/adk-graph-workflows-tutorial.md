# Tutorial — ADK Graph-Based Workflows by Example

> A single worked example that introduces every primitive from
> [[concepts/adk-graph-workflows]] as we use it. Plain language.
> Assumes you've done [[resources/Agents CLI Build eval and deploy AI agents in minutes/notes]]
> or the agent-team tutorial.

The reference doc tells you *what* each primitive does. This page is
about *why* you reach for them in a real shape — by building one
support-ticket triage workflow top to bottom.

> **Status (2026-05-26).** Imports VERIFIED while building
> `test/idea_refiner/`. See the reference doc's "VERIFIED imports"
> table.
>
> **CORRECTION — instruction templating.** The `{ClassName.field}` and
> `<ClassName.field from source_node>` syntax used throughout this tutorial
> below **does NOT exist** in the installed `google-adk==2.0.x`. ADK's
> `inject_session_state` (the only instruction templater) only
> substitutes `{simple_identifier}` from `session.state`. Use the
> working pattern instead — see [[concepts/adk-graph-workflows#templating-into-agent-instructions]]:
> a `FunctionNode` upstream writes individual scalars into state via
> `Event(state={...})`, and the agent reads them via `{simple_key}`.
> The runnable reference is `test/idea_refiner/` (`nodes_research.py`
> `split_prompts` is the canonical example of this pattern).

---

## The shape

We're going to build this:

```
START
  |
  v
[FunctionNode: load_ticket]        ← deterministic fixture loader (no LLM)
  |
  v
[Agent: classify_ticket]           ← single-turn LLM, output_schema=Classification
  |
  v
[FunctionNode: router]             ← emits Event(route="BUG"|"SUPPORT"|"LOGISTICS")
  |
  +-----------+-------------+
  v           v             v
[bug_branch][support_branch][logistics_branch]   ← each one is a NESTED Workflow
  |           |             |
  +-----------+-------------+
              |
              v
[RequestInput: human_approval]      ← pause; ask a human to approve
              |
              v
[FunctionNode: post_reply]          ← emit Event(message=...) for the user
```

Why this shape exercises everything:

| Step | Concept it shows |
|---|---|
| `load_ticket` | A `FunctionNode` — the simplest possible node. |
| `classify_ticket` | An `Agent` node with `output_schema` and `mode="single_turn"`. |
| `router` | A `FunctionNode` that emits `Event(route=...)` for a branching dict. |
| Three branches | Conditional routing + **nested `Workflow` as node**. |
| Inside the branches | `input_schema`, `{ClassName.field}` and `<...from source>` instruction syntax, structured `Event(output=...)` handoffs. |
| `human_approval` | `RequestInput` with `message`, `payload`, and `response_schema`. |
| `post_reply` | `Event(message=...)` to talk to the user; `Event(state=...)` to bump a counter. |

A *second*, smaller example at the end of this page shows
**parallel fan-out + `JoinNode`**. We don't try to bolt that into the
main flow — only one branch fires when a router picks, so parallel
joins would be artificial there.

---

## Step 1 — The Workflow skeleton and the START keyword

A graph is a `Workflow` with an `edges` array. The first row's first
element is always the literal string `"START"`. Everything else hangs
off subsequent rows.

```python
from google.adk import Workflow

# (we'll fill in the nodes as we go)
root_agent = Workflow(
    name="ticket_triage",
    edges=[
        ("START", load_ticket, classify_ticket, router),
        (router, {
            "BUG":       bug_branch,
            "SUPPORT":   support_branch,
            "LOGISTICS": logistics_branch,
        }),
        # All three branches converge into human_approval, so each
        # branch's final node's output flows directly here.
        (bug_branch,       human_approval),
        (support_branch,   human_approval),
        (logistics_branch, human_approval),
        (human_approval,   post_reply),
    ],
)
```

A few things to notice already:

- The first row is **sequential**: load → classify → router.
- The second row is **branching**: `router` emits a `route` string;
  the dict picks one branch.
- Each branch is *one node* in the parent graph even though, as we'll
  see, each branch is itself a small `Workflow`.

---

## Step 2 — A FunctionNode (load_ticket)

The simplest node is a bare Python function that takes `node_input`
and returns an `Event`. No decorator, no registration — just put the
function name in the `edges` array.

```python
from google.adk import Event
from pydantic import BaseModel

class Ticket(BaseModel):
    id: str
    customer: str
    subject: str
    body: str

def load_ticket(node_input):
    # Pretend we hit a ticketing system. Hardcoded for the tutorial.
    return Event(output=Ticket(
        id="T-1042",
        customer="alex@example.com",
        subject="App crashes on launch",
        body="Whenever I open the app on Android 14 it crashes within 2s.",
    ))
```

`load_ticket` ignores `node_input` because nothing came before it. The
next node will receive the `Ticket` object as *its* `node_input`.

> **Why `return` and not `yield`?** A function node that produces one
> output uses `return`. `yield` is for the multi-emit case (e.g. send
> two `Event(message=...)` for the user, then a final `Event(output=...)`
> for the next node). See the [[concepts/adk-graph-workflows#The Event class — the data bus|Event reference]].

---

## Step 3 — An Agent node with `output_schema` and `mode="single_turn"`

Now the LLM step: classify the ticket. We force structured output
with `output_schema` so the next node gets a typed object, and we set
`mode="single_turn"` because every agent inside a graph must run
non-interactively.

```python
from google.adk import Agent
from typing import Literal

class Classification(BaseModel):
    category: Literal["BUG", "SUPPORT", "LOGISTICS"]
    confidence: float

classify_ticket = Agent(
    name="classify_ticket",
    model="gemini-flash-latest",
    instruction=(
        "Classify the support ticket into BUG, SUPPORT, or LOGISTICS.\n"
        "Return only the structured Classification object."
    ),
    input_schema=Ticket,             # validates what this node receives
    output_schema=Classification,    # validates what this node emits
    mode="single_turn",              # MUST set this for graph nodes
)
```

Two things land here:

1. **`input_schema=Ticket`** — ADK validates `load_ticket`'s output
   against `Ticket` before this agent runs. If `load_ticket` ever
   returns the wrong shape, this is where it'll be caught — not
   three nodes downstream.
2. **`mode="single_turn"`** — see the
   [[concepts/adk-graph-workflows#Cautions / gotchas|cautions]] in the
   reference. Forget this and the workflow tries to run an
   interactive chat session as a node and stalls.

---

## Step 4 — A FunctionNode that emits `Event(route=...)`

The router picks a branch by setting `route` on its `Event`. The
branching edge dict (next step) reads that `route` string.

```python
def router(node_input: Classification):
    # node_input is the Classification the previous agent emitted.
    return Event(route=node_input.category)
```

Conventions:
- The router's emitted `route` value must be a key in the branching
  dict. If it returns `"OTHER"` and the dict doesn't have `"OTHER"`,
  you get a routing error — explicit, which is what you want.
- A router can also emit other Event fields (like `state`) at the
  same time, but its job is the `route` decision.

---

## Step 5 — Branching with the edges dict

We've already written this row in step 1, but here it is on its own:

```python
edges = [
    ...,
    (router, {
        "BUG":       bug_branch,
        "SUPPORT":   support_branch,
        "LOGISTICS": logistics_branch,
    }),
    ...,
]
```

This says: "after `router` runs, look at `Event.route`. If it's `BUG`,
run `bug_branch` next; if `SUPPORT`, run `support_branch`; etc."

Only **one** branch fires per run. That's why fan-out + join is a
separate example below.

---

## Step 6 — Nested Workflows (each branch is its own graph)

Each of `bug_branch`, `support_branch`, `logistics_branch` is a
`Workflow` of its own, used as a single node in the parent. This is
nesting — it scales naturally as branches grow.

The bug branch is the most interesting; it has a deterministic
enrichment step plus an LLM drafter:

```python
class EnrichedTicket(BaseModel):
    ticket: Ticket
    related_log_lines: list[str]

def enrich_with_logs(node_input: Ticket):
    # Pretend we hit a log store. Returns the ticket plus context.
    return Event(output=EnrichedTicket(
        ticket=node_input,
        related_log_lines=[
            "FATAL android.runtime: signal 11 (SIGSEGV)",
            "RenderThread: GL error 0x0506",
        ],
    ))

class DraftReply(BaseModel):
    to: str
    subject: str
    body: str

write_repro_steps = Agent(
    name="write_repro_steps",
    model="gemini-flash-latest",
    input_schema=EnrichedTicket,
    output_schema=DraftReply,
    mode="single_turn",
    instruction=(
        "You are a support engineer. Using the ticket body and related "
        "log lines, draft a reply that thanks the customer, lists "
        "minimal repro steps you'd ask them to confirm, and asks for "
        "device + OS details if not already supplied.\n\n"
        "Ticket subject: {EnrichedTicket.ticket.subject}\n"
        "Body: {EnrichedTicket.ticket.body}\n"
        "Recent logs:\n{EnrichedTicket.related_log_lines}\n"
    ),
)

bug_branch = Workflow(
    name="bug_branch",
    edges=[("START", enrich_with_logs, write_repro_steps)],
)
```

Worth noticing:

- `enrich_with_logs` declares **`input_schema=EnrichedTicket`-shaped
  input** by typing `node_input: Ticket`. The shape it accepts is
  what came in from the parent graph (which was the `Classification`
  from `classify_ticket`). The reality is we'd need a small adapter
  if we want the *original* `Ticket` here — see "data handling
  pitfalls" below.
- The agent's `instruction` uses `{EnrichedTicket.ticket.subject}` —
  that's the `{ClassName.field}` syntax from the reference doc. It
  works because `input_schema=EnrichedTicket` is set.

The other two branches follow the same shape; here are slimmer
versions:

```python
write_apology = Agent(
    name="write_apology",
    model="gemini-flash-latest",
    input_schema=Ticket,
    output_schema=DraftReply,
    mode="single_turn",
    # SOURCE-RESTRICTED syntax: <Class.field from source_node_name>
    # Useful when several upstream nodes could produce a Ticket and
    # you want to lock to exactly one.
    instruction=(
        "Write a warm, brief apology to <Ticket.customer from load_ticket> "
        "acknowledging the issue described in "
        "<Ticket.body from load_ticket>. Offer next steps."
    ),
)

support_branch = Workflow(
    name="support_branch",
    edges=[("START", write_apology)],
)

def lookup_shipment(node_input: Ticket):
    # Pretend we hit a shipping API.
    return Event(output={
        "ticket": node_input,
        "tracking_url": "https://shipper.example/track/abc123",
        "eta": "2026-05-29",
    })

write_status_update = Agent(
    name="write_status_update",
    model="gemini-flash-latest",
    mode="single_turn",
    output_schema=DraftReply,
    instruction=(
        "Compose a short shipment status update including the tracking "
        "URL and ETA from the previous node's output."
    ),
)

logistics_branch = Workflow(
    name="logistics_branch",
    edges=[("START", lookup_shipment, write_status_update)],
)
```

**Nested-workflow event semantics.** When a node *inside*
`bug_branch` emits an `Event`, that Event bubbles up to the parent
workflow's stream — you still see it in traces and the dev UI. The
parent treats the *final* leaf node's output (here, `write_repro_steps`'s
`DraftReply`) as the nested node's output.

---

## Step 7 — `Event(output=...)` and the one-per-node rule

You've already seen `return Event(output=...)`. The rule that bites
people: a node may `yield` many `Event`s, but **no more than one of
them may carry `output=`**. The runtime errors if you try.

If you want to surface progress to the user *and* hand off data,
yield a `message` first, then `return` the `output`:

```python
def slow_lookup(node_input):
    yield Event(message="Looking up shipment...")
    # ... do the work ...
    return Event(output={"tracking_url": "...", "eta": "..."})
```

---

## Step 8 — `RequestInput` for human approval

After the chosen branch produces a `DraftReply`, we don't want to
auto-post it. We pause and ask a human:

```python
from google.adk.events import RequestInput

class ApprovalDecision(BaseModel):
    approved: bool
    edits: str = ""

def human_approval(node_input: DraftReply):
    yield RequestInput(
        message=(
            "Review the draft reply below. Approve or provide edits."
        ),
        payload=node_input,                # shows the DraftReply to the user
        response_schema=ApprovalDecision,  # the user's response must conform
    )
```

A few caveats from the
[[concepts/adk-graph-workflows#RequestInput (human-in-the-loop)|reference]]:

- `response_schema` is enforced, **but not auto-coerced.** If a user
  types free text, ADK won't turn it into `ApprovalDecision`. Either
  provide a UI that posts the structured object, or put an `Agent`
  node after `human_approval` to normalize.
- `payload` is what you want the human to see (the draft reply here).
  `message` is the instruction to the human.
- The workflow truly **pauses** until the user responds; this is
  different from a non-blocking notification.

---

## Step 9 — `Event(message=...)` and `Event(state=...)`

Final node: post the reply (pretend) and tell the user we're done.
Also bump an attempts counter in `Event(state=...)` to show how state
flows.

```python
def post_reply(node_input: ApprovalDecision):
    if not node_input.approved:
        # We could route to a re-draft loop here; out of scope for the tutorial.
        yield Event(message="Draft rejected. (Re-draft loop not shown.)")
        return

    # Pretend we posted it.
    yield Event(state={"posted_count": 1})  # small scalar — fine for Event.state
    yield Event(message=f"Reply posted to ticket. Edits requested: {node_input.edits or 'none'}.")
```

Two things to take away:

1. **`Event.state` is for tiny scalars.** A counter or flag is fine.
   Do not stuff a full reply payload in there — use `Event.output` or
   ADK artifacts. State carries across nodes in the same run; it's
   *not* the same surface as global `session.state` from
   [[concepts/adk-session-state]] (which persists across whole
   sessions, not just this run).
2. **`Event.message` is the user-facing channel.** Use it sparingly —
   it shows up in the chat. `Event.output` is what flows downstream;
   `Event.message` is for the human.

---

## The whole workflow, in one block

Putting it together (annotated):

```python
from typing import Literal
from pydantic import BaseModel

from google.adk import Agent, Event, Workflow
from google.adk.events import RequestInput   # VERIFY ON BUILD

# ── Schemas ──────────────────────────────────────────────────────────
class Ticket(BaseModel):
    id: str
    customer: str
    subject: str
    body: str

class Classification(BaseModel):
    category: Literal["BUG", "SUPPORT", "LOGISTICS"]
    confidence: float

class EnrichedTicket(BaseModel):
    ticket: Ticket
    related_log_lines: list[str]

class DraftReply(BaseModel):
    to: str
    subject: str
    body: str

class ApprovalDecision(BaseModel):
    approved: bool
    edits: str = ""

# ── Function nodes ──────────────────────────────────────────────────
def load_ticket(node_input):
    return Event(output=Ticket(
        id="T-1042",
        customer="alex@example.com",
        subject="App crashes on launch",
        body="Whenever I open the app on Android 14 it crashes within 2s.",
    ))

def router(node_input: Classification):
    return Event(route=node_input.category)

def enrich_with_logs(node_input: Ticket):
    return Event(output=EnrichedTicket(
        ticket=node_input,
        related_log_lines=[
            "FATAL android.runtime: signal 11 (SIGSEGV)",
            "RenderThread: GL error 0x0506",
        ],
    ))

def lookup_shipment(node_input: Ticket):
    return Event(output={
        "ticket": node_input,
        "tracking_url": "https://shipper.example/track/abc123",
        "eta": "2026-05-29",
    })

def human_approval(node_input: DraftReply):
    yield RequestInput(
        message="Review the draft reply below. Approve or provide edits.",
        payload=node_input,
        response_schema=ApprovalDecision,
    )

def post_reply(node_input: ApprovalDecision):
    if not node_input.approved:
        yield Event(message="Draft rejected. (Re-draft loop not shown.)")
        return
    yield Event(state={"posted_count": 1})
    yield Event(message=f"Reply posted. Edits requested: {node_input.edits or 'none'}.")

# ── Agent nodes ─────────────────────────────────────────────────────
classify_ticket = Agent(
    name="classify_ticket",
    model="gemini-flash-latest",
    input_schema=Ticket,
    output_schema=Classification,
    mode="single_turn",
    instruction="Classify the support ticket into BUG, SUPPORT, or LOGISTICS.",
)

write_repro_steps = Agent(
    name="write_repro_steps",
    model="gemini-flash-latest",
    input_schema=EnrichedTicket,
    output_schema=DraftReply,
    mode="single_turn",
    instruction=(
        "Draft a reply asking for repro confirmation, using:\n"
        "Subject: {EnrichedTicket.ticket.subject}\n"
        "Body: {EnrichedTicket.ticket.body}\n"
        "Logs:\n{EnrichedTicket.related_log_lines}\n"
    ),
)

write_apology = Agent(
    name="write_apology",
    model="gemini-flash-latest",
    input_schema=Ticket,
    output_schema=DraftReply,
    mode="single_turn",
    instruction=(
        "Write a warm, brief apology to "
        "<Ticket.customer from load_ticket> about "
        "<Ticket.body from load_ticket>."
    ),
)

write_status_update = Agent(
    name="write_status_update",
    model="gemini-flash-latest",
    mode="single_turn",
    output_schema=DraftReply,
    instruction="Compose a shipment status update with tracking URL and ETA.",
)

# ── Branch workflows (nested) ───────────────────────────────────────
bug_branch = Workflow(
    name="bug_branch",
    edges=[("START", enrich_with_logs, write_repro_steps)],
)
support_branch = Workflow(
    name="support_branch",
    edges=[("START", write_apology)],
)
logistics_branch = Workflow(
    name="logistics_branch",
    edges=[("START", lookup_shipment, write_status_update)],
)

# ── Root workflow ───────────────────────────────────────────────────
root_agent = Workflow(
    name="ticket_triage",
    edges=[
        ("START", load_ticket, classify_ticket, router),
        (router, {
            "BUG":       bug_branch,
            "SUPPORT":   support_branch,
            "LOGISTICS": logistics_branch,
        }),
        (bug_branch,       human_approval),
        (support_branch,   human_approval),
        (logistics_branch, human_approval),
        (human_approval,   post_reply),
    ],
)
```

---

## Side example — parallel fan-out + `JoinNode`

Conditional routing picks one branch. To run several nodes **at the
same time** and gather their outputs, use multiple `("START", ...)`
rows feeding a `JoinNode`. Here's a tiny example that runs three
enrichment agents on the same ticket and joins their results for a
drafter.

```python
from google.adk.workflow import JoinNode   # VERIFY ON BUILD

def get_recent_logs(node_input: Ticket):
    return Event(output={"logs": ["...recent log lines..."]})

def get_customer_history(node_input: Ticket):
    return Event(output={"prior_tickets": 3})

def get_app_version(node_input: Ticket):
    return Event(output={"app_version": "4.2.1"})

collect = JoinNode(name="collect_enrichment")

draft_with_all_context = Agent(
    name="draft_with_all_context",
    model="gemini-flash-latest",
    mode="single_turn",
    instruction=(
        "Draft a support reply using the ticket and all the enrichment "
        "outputs collected from the parallel branches."
    ),
)

root_parallel = Workflow(
    name="parallel_enrich",
    edges=[
        ("START", load_ticket, get_recent_logs, collect),
        ("START", load_ticket, get_customer_history, collect),
        ("START", load_ticket, get_app_version, collect),
        (collect, draft_with_all_context),
    ],
)
```

**The gotcha to internalize.** If `get_app_version` raises silently
and never emits, `collect` waits for it forever and the workflow
halts. Always make sure every branch that feeds a join emits
*something* — even an empty `Event()` from an except block:

```python
def get_app_version(node_input: Ticket):
    try:
        # ...
        return Event(output={"app_version": "4.2.1"})
    except Exception:
        return Event(output={"app_version": None})   # failsafe
```

---

## Why a graph here, vs a `SequentialAgent`?

Honest reflection: if this were only "load → classify → draft →
post," `SequentialAgent` would be simpler. Two things tipped the
balance toward a graph:

1. **The branching.** Three categories with different sub-pipelines
   is exactly where prompt-orchestrated routing
   ([[concepts/adk-multi-agent]]) starts hiding logic in instruction
   strings. Putting it in `edges` makes the flow first-class — you
   can read it without reading a prompt.
2. **The HITL gate.** `RequestInput` is graph-only. If you need a
   human in the loop mid-process, a `Workflow` is the natural place.

Without either of those — no branching and no human gate — reach for
`SequentialAgent` instead.

---

## Cautions, restated as "what would have bitten us"

A reframe of the [[concepts/adk-graph-workflows#Cautions / gotchas|reference cautions]],
in tutorial form:

- **Forgetting `mode="single_turn"` on an agent node.** The workflow
  tries to start an interactive chat as a step, and the run stalls
  with no useful error.
- **Yielding two `Event(output=...)` in one node** (e.g. as a
  ["just in case"](one-output-per-node) thing). Runtime error.
- **Stuffing the full ticket history into `Event(state=...)`** so
  every later node can read it. Works at first, breaks when the
  state grows; use `Event.output` (explicit data flow) or an artifact.
- **Forgetting that a branch only runs one of its handlers.** If you
  add code in the parent that assumes "all three branch outputs are
  available," you'll get None — the unselected branches never ran.
- **JoinNode that never resolves.** Some upstream raised and didn't
  emit. Always emit a failsafe Event from every parallel branch.
- **Multi-turn LlmAgent leaked into a graph as a node.** Graphs need
  every node to return promptly; chat agents don't.

---

## Next: turn this into a runnable sandbox

When this is built (next session), the to-validate list is:

1. The four import paths flagged `VERIFY ON BUILD` in
   [[concepts/adk-graph-workflows]].
2. That `mode="single_turn"` is the actual parameter name on
   `Agent`.
3. That a router emitting `Event(route="BUG")` actually selects
   `bug_branch` from the dict.
4. That `Event(state=...)` values persist across the chosen branch
   into `post_reply`.
5. That `RequestInput` actually pauses the run under `adk web`.

Once those check out, the tutorial above is the canonical reference
shape for graph workflows in this vault.

---

## Related

- [[concepts/adk-graph-workflows]] — reference doc (terse, scannable).
- [[concepts/adk]] — base primitives and built-in workflow agents.
- [[concepts/adk-multi-agent]] — the prompt-orchestrated alternative.
- [[concepts/adk-llm-agent-config]] — every LlmAgent knob still
  applies to agents used as graph nodes (with `mode="single_turn"`).
- [[concepts/adk-session-state]] — global session.state vs the per-run
  Event(state=...) bag inside a graph.
