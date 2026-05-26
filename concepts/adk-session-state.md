# ADK Session State

A per-session key-value store, shared across all tools and agents in the
session, that **persists across turns**. This is what gives an agent memory.
Part of [[concepts/adk]].

**Reference template**: `test/agent_teams/agent.py` (`get_weather_stateful`).

---

## Argument vs state

| | Function argument (`city`) | Session state (`preferred_unit`) |
|---|---|---|
| Lifetime | one tool call | the whole session |
| Set by | the LLM, per call | seeded / written once, read many |
| Purpose | this request's input | memory & personalisation |

The reason temperature unit lives in state, not as a tool arg: the user states
it once, every later weather call should respect it without re-asking.

---

## The four ways to write state

```python
# 1. From a tool
def get_weather_stateful(city: str, tool_context: ToolContext) -> dict:
    unit = tool_context.state.get("user_preference_temperature_unit", "Celsius")  # READ (with default)
    ...
    tool_context.state["last_city_checked_stateful"] = city                       # WRITE

# 2. From a callback
callback_context.state["guardrail_block_keyword_triggered"] = True

# 3. output_key on the agent  -> auto-saves the agent's final response
root_agent = Agent(..., output_key="last_weather_report")

# 4. Seeded at session creation (the canonical "initial state")
session_service.create_session(
    app_name=..., user_id=..., session_id=...,
    state={"user_preference_temperature_unit": "Fahrenheit"},
)
```

The `.get(key, default)` default exists *because* nobody may have seeded the
key — design tools to degrade gracefully.

---

## The `adk web` seeding gotcha

Under `adk web` you do **not** write the `create_session(state=...)` call, so
state starts **empty** and defaults always win. Worse: in this ADK build the
dev-UI **State tab is read-only** — you cannot seed from the browser.

To exercise stateful behaviour you must either:
- add a tool that writes the preference (user-driven seeding, in-browser), or
- run a runner script with `create_session(state=...)` (the real path; you
  will need this for evals anyway — see [[configs/run-agent-locally]]).

---

## Rigor: prove it is state, not chat history

When the agent answered "which city did I last check?" with "London", that
*looked* like it read `last_city_checked_stateful`. But "London" was also in
the recent conversation, so the model could have answered from chat context.
**You did not isolate the mechanism.** To prove state-as-memory: fresh session
with pre-seeded state, or query a key the conversation never mentioned. (Same
"prove the path" discipline as [[concepts/adk-litellm-models]].)

---

## Related

- [[concepts/adk]] — agent primitives
- [[concepts/adk-sub-agents]] — state is shared across the whole team
- [[concepts/adk-guardrails]] — callbacks write state for auditability
- [[configs/run-agent-locally]] — runner script = the real seeding path
- [[concepts/adk-graph-workflows]] — graph workflows add a *second* state surface (`Event(state=...)`) that persists across nodes within one graph run; that is distinct from `session.state` documented here, which spans the whole session.
