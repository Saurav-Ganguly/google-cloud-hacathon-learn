# ADK LlmAgent configuration: schemas, planner, content-config, state templating

Deep reference for the `LlmAgent` features documented at
https://adk.dev/agents/llm-agents/ that were never exercised hands-on until
the 2-round Debate Bot sandbox (2026-05-20). The canonical annotated example
is `test/LlmDebator/agent.py` — every section below points at the line of
that file where the feature is used.

Companion notes: [[concepts/adk]] (the high-level reference) and
[[concepts/adk-session-state]] (`output_key` + state templating mechanism).

---

## What this note covers

| Feature | Used in |
|---|---|
| `instruction` with `{var}` state-variable templating | every Debate Bot agent |
| `output_schema` + `output_key` (controlled JSON generation) | topic_refiner, pro_r1/r2, con_r1/r2, judge |
| `generate_content_config` (temperature, safety, thinking) | every agent |
| `planner=BuiltInPlanner(...)` for native Gemini thinking | judge_agent |
| `include_contents='none'` (strip chat history) | judge_agent |
| `after_agent_callback` returning `Content` (replace UI output) | every agent (logger) |

Plus two HARD CONSTRAINTS the file demonstrates by working around them:

1. **`output_schema` disables tools** (and agent-transfer) on the same agent.
2. **Gemini 2.5 hidden thinking eats `max_output_tokens`** unless disabled.

---

## 1. `{var}` state-variable templating

ADK substitutes `{key}` in an agent's `instruction` with `state["key"]` at
run time. Lifecycle inside `test/LlmDebator/agent.py`:

```
topic_refiner   writes state["debate_topic"]
pro_agent_r1    reads  {debate_topic}                        ->  writes pro_case_r1
con_agent_r1    reads  {debate_topic}, {pro_case_r1}         ->  writes con_case_r1
pro_agent_r2    reads  {debate_topic}, {pro_case_r1}, {con_case_r1}
con_agent_r2    reads  {debate_topic}, {pro_case_r1}, {con_case_r1}, {pro_case_r2}
fact_check      reads  all four debate slots                 ->  writes fact_check
judge           reads  everything + model labels             ->  writes verdict
```

Key facts:

- When the value at `state[key]` is a dict (because the writer had an
  `output_schema=PydanticModel`), it gets stringified into the instruction.
  The LLM handles the str-of-dict fine.
- Templating only fires for keys that ALREADY exist in state. Read order
  matters: the writer must run before the reader (this is why
  [[concepts/adk]]'s `SequentialAgent` is the right top-level here).
- Optional read: `{key?}` succeeds even if the key is missing. Not used in
  the Debate Bot because the SequentialAgent guarantees ordering.

See [[concepts/adk-session-state]] for the underlying state mechanics.

---

## 2. `output_schema` + `output_key`

`output_schema=SomeModel` configures the LLM with JSON-only controlled
generation against a Pydantic model. The model's response MUST conform or
generation fails. `output_key="slot"` then stores the parsed dict into
`state["slot"]` for downstream agents to read.

In `test/LlmDebator/agent.py`:
- `DebateTopic` (topic_refiner)
- `ProCase` (pro_agent_r1 AND pro_agent_r2 — schema reuse, distinct output_keys)
- `ConCase` (con_agent_r1 AND con_agent_r2)
- `Verdict` (judge_agent)

### HARD CONSTRAINT — `output_schema` disables tools

Setting `output_schema` makes the agent CANNOT:
- use any `tools=[...]` (functions, `AgentTool`, or built-in tools like `google_search`)
- transfer control to sub-agents (LLM-driven delegation off)

This is why the Debate Bot has a **separate `fact_check_agent`** (uses
`google_search`, NO `output_schema`, returns plain text) and the judge
reads the fact-check as a text blob. Pattern: **research-then-structure** —
one agent grounds with tools and produces unstructured findings; the next
agent consumes them as text and produces structured JSON.

---

## 3. `generate_content_config` (temperature, safety, thinking)

Per-agent generation tuning. Important fields used in the Debate Bot:

```python
types.GenerateContentConfig(
    temperature=0.95,                                   # hot Pro
    temperature=0.25,                                   # cold Con (deliberate contrast)
    temperature=0.4,                                    # mild topic_refiner
    safety_settings=[                                   # per-agent overrides
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
    ],
    thinking_config=types.ThinkingConfig(thinking_budget=0),  # see gotcha 4
)
```

`max_output_tokens` is intentionally OMITTED — the model's default cap is
generous, and tight caps bit us first try (truncated `{` and mid-string
JSON). Only set it if you specifically need to bound cost or latency.

---

## 4. `planner=BuiltInPlanner(...)`

Enables Gemini's native thinking (chain-of-thought) as a SEPARATE channel
from the visible response.

```python
planner=BuiltInPlanner(
    thinking_config=types.ThinkingConfig(
        include_thoughts=True,       # surfaces a "Thought" event in adk web
        thinking_budget=1024,        # caps thinking tokens
    ),
)
```

Used on judge_agent in `test/LlmDebator/agent.py`.

### Why `BuiltInPlanner` co-exists with `output_schema`

`BuiltInPlanner` thinking lives in a dedicated thought channel — separate
from the visible response — so the final response is still pure schema-
conforming JSON.

### Why `PlanReActPlanner` does NOT co-exist with `output_schema`

`PlanReActPlanner` emits `/*PLANNING*/.../*FINAL_ANSWER*/` markers in the
**visible** response — directly colliding with JSON-only generation. If you
need ReAct-style explicit planning AND structured output, you have to split:
one agent ReActs to plain text, the next agent reads it and structures it.

---

## 5. `include_contents='none'` — strip chat history

By default, ADK feeds the model the full conversation history alongside the
filled-in instruction. `include_contents='none'` strips ALL history before
each call. The model sees ONLY its instruction.

Used on judge_agent. Pedagogically it's the **proof** that state-passing
(not chat memory) is what carries information between agents — even with no
history, the judge's instruction contains `{pro_case_r1}` / `{con_case_r1}`
/ etc. via templating, and the judge produces a coherent verdict.

---

## 6. `after_agent_callback` returning `Content`

The callback runs after the agent emits its output. Two return modes:

- return `None`         → agent's original output flows through unchanged
- return `types.Content` → REPLACES the agent's final output in the event stream

State written via `output_key` is ALREADY saved by the time the callback
runs, so replacing the chat-bubble Content is safe — you keep the parsed
dict in state and show a labeled, friendlier version in the UI.

In `test/LlmDebator/agent.py`, `make_logger(...)` is a factory that returns
an `after_agent_callback` doing both:
- print a labeled banner to the terminal (`agent_name (model) -> state['key']`)
- return Content that prefixes the bubble with `agent_name (model_label)`

This is how each chat bubble in `adk web` shows which model produced it.
The last agent's logger sets `dump_full_state=True` so the terminal also
prints the entire accumulated session state at the end of a run — a useful
end-of-run audit since `adk web`'s State tab is scoped to a single event's
delta.

---

## 7. Gotcha: Gemini 2.5 hidden thinking eats the response budget

Symptom: a Gemini agent with `output_schema` emits only `'{\n'` then
truncates. Pydantic raises `Invalid JSON: EOF while parsing an object`.

Root cause: Gemini 2.5 Flash has thinking ON by default, and thinking
tokens count against the model's response budget. With a small explicit
`max_output_tokens`, the hidden thinking eats the budget before any JSON
appears.

Two fixes, used together in the Debate Bot:

1. **Disable thinking explicitly** on schema-fill agents that don't need to
   reason:
   ```python
   thinking_config=types.ThinkingConfig(thinking_budget=0)
   ```
   Used on topic_refiner and fact_check_agent.

2. **Don't set `max_output_tokens`** unless you need to cap cost. Default
   caps are generous.

Agents that DO want thinking (judge_agent) use `BuiltInPlanner` whose
thinking budget is SEPARATE from the response budget — no starvation risk.

Debugged 2026-05-20 — [[logs/2026-05-20]].

---

## 8. Gotcha: `output_schema` disables tools (re-iterated)

Repeat for emphasis because this is the constraint that shapes most
multi-agent designs once you start using structured output.

Compositions forced by this constraint:

- **Research-then-structure**: grounding agent (tools, plain text) →
  structuring agent (no tools, `output_schema`).
- **AgentTool-as-shared-research**: a tool-using agent wrapped as an
  `AgentTool` — but the CALLING agents can't have `output_schema` either.
  So shared `AgentTool` access also requires plain-text consumers.

The Debate Bot uses the first pattern: `fact_check_agent` does grounding,
`judge_agent` consumes its plain text alongside the structured pro/con
JSON from state.

---

## Reference implementation

[`test/LlmDebator/agent.py`](../test/LlmDebator/agent.py) — every feature
listed here used in context, with line-level inline comments and the
section banners that name the relevant feature. Best file to copy patterns
from when building any agent that needs:

- structured I/O via Pydantic schemas
- multi-round agent dialogues passing state forward
- a planner agent that thinks before responding with strict JSON
- grounding via `google_search` composed with structured output
- per-agent labeling/logging via `after_agent_callback`

---

## Related

- [[concepts/adk]] — high-level ADK primitives reference
- [[concepts/adk-session-state]] — state mechanics + `output_key` deep dive
- [[concepts/adk-litellm-models]] — non-Gemini models + reasoning-off pattern
- [[concepts/adk-multi-agent]] — SequentialAgent, LoopAgent, generator-critic
- [[plans/plan19.05.2026]] — design plan that led to this build
- [[logs/2026-05-20]] — the build session that vaulted this knowledge
