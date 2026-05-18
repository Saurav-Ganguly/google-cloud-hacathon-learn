# ADK Sub-Agents & LLM-Driven Delegation

How a coordinator agent delegates to specialist sub-agents, and the one
behaviour that surprises everyone: **control sticks**. Part of [[concepts/adk]];
see also [[concepts/adk-multi-agent]] for the higher-level patterns.

**Reference template**: `test/agent_teams/agent.py` (heavily commented).

---

## Wiring a team

```python
greeting_agent = Agent(
    model=...,
    name="greeting_agent",
    instruction="You are the Greeting Agent. ...",
    description="Handles simple greetings using 'say_hello'.",  # <- delegation signal
    tools=[say_hello],
)

root_agent = Agent(
    name="weather_agent_v1",
    model=GEMINI_MODEL,
    instruction="You coordinate a team. Delegate greetings to greeting_agent ...",
    tools=[get_weather_stateful],
    sub_agents=[greeting_agent, farewell_agent],   # <- enables delegation
)
```

- `sub_agents=[...]` on the parent is what makes delegation possible. ADK
  injects a `transfer_to_agent` capability automatically.
- The coordinator's LLM decides *when* to delegate by reading each sub-agent's
  **`description`** — not its instruction. A vague description = bad routing.
  Keep descriptions crisp and disjoint.

---

## The key lesson: control STICKS

After the coordinator calls `transfer_to_agent`, the **sub-agent becomes the
active agent for every following turn** until *it* explicitly transfers back.
ADK does **not** auto-return control to root after one turn.

Observed live: after "hi" delegated to `greeting_agent`, the next message
("what is your task?") was *also* handled by `greeting_agent`, not root.

Consequences:
- A narrow sub-agent can get stuck holding the whole conversation.
- Anything attached to root only (e.g. a `before_model_callback`) does **not**
  run while a sub-agent has control. This is the root cause of the guardrail
  bypass in [[concepts/adk-prompt-injection-lessons]].

---

## Returning control: positive routing beats prohibition

A sub-agent only hands back if its LLM chooses to call `transfer_to_agent`.
Make that a **positive instruction**, not a negative one.

- Weak:   `"Do not engage in any other conversation."`
- Strong: `"If the user asks anything that is not a greeting request,
  transfer back to the coordinator."`

LLMs follow "when X, do Y" far more reliably than "don't do X". Adding the
positive route was the single change that fixed meta-questions ("what is your
job?") snapping back to the coordinator instead of being answered by the
greeting agent.

---

## Related

- [[concepts/adk]] — agent primitives
- [[concepts/adk-multi-agent]] — coordinator / pipeline / fan-out patterns
- [[concepts/adk-litellm-models]] — putting cheap models on sub-agents
- [[concepts/adk-session-state]] — state is shared across the whole team
- [[concepts/adk-guardrails]] — callbacks are per-agent (matters because control sticks)
- [[concepts/adk-prompt-injection-lessons]] — the bypass this enables
