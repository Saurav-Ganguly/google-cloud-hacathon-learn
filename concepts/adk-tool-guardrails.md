# ADK Tool Guardrails (`before_tool_callback`)

The second guardrail layer. `before_model_callback` ([[concepts/adk-guardrails]])
gates the **LLM call**; `before_tool_callback` gates the **tool execution** the
model decided to make. Part of [[concepts/adk]].

**Reference template**: `test/agent_teams/agent.py` (`block_paris_tool_guardrail`).

---

## The contract

```python
def block_paris_tool_guardrail(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    ...
    return None     # -> ADK runs the real tool function normally
    # OR
    return {        # -> ADK SKIPS the tool, this dict becomes its result
        "status": "error",
        "error_message": "Policy restriction: ..."
    }
```

Wire it on the agent:

```python
root_agent = Agent(..., before_tool_callback=block_paris_tool_guardrail)
```

When blocked, the real tool body **never runs** (its `print` never fires). The
returned dict flows back into the LLM exactly as a real tool result would, so
the model then phrases a normal refusal to the user.

---

## Each callback impersonates the thing it stands in front of

| | `before_model_callback` | `before_tool_callback` |
|---|---|---|
| Sits in front of | the LLM | a tool function |
| Inspects | raw user text (`llm_request.contents`) | structured `args` the model produced |
| Block return shape | `LlmResponse` (fakes "model answered") | `dict` (fakes "tool ran") |
| Proceed | `None` | `None` |

The return shapes differ because each callback must hand back **what the stage
it replaced normally produces**, so the next stage doesn't choke.

---

## The principle: guard the action, not the phrasing

The model callback inspects **attacker-controlled raw text** — easy to reword
around (synonym / tokenisation evasions, see
[[concepts/adk-prompt-injection-lessons]]). The tool callback inspects the
**model-normalised structured arg** (`args["city"] == "Paris"`). The user can
phrase the request a thousand ways; if the model resolves any of them to
`city="Paris"`, the tool guard catches it. The attacker no longer controls the
thing being inspected — the model normalised it first.

> Input guards filter words (reword-able). Tool guards filter *resolved
> intent* — the structured effect the model committed to. The closer the check
> sits to the real side effect (DB write, API call, spend), the harder it is to
> talk past.

This is the **other half** of the [[concepts/adk-prompt-injection-lessons]]
conclusion: that note says "keep secrets out of model-reachable context"; this
says "when an action *must* happen, gate the action itself, not the request."
Defence in depth: model callback = cheap noisy first filter; tool callback =
the real gate in front of consequential actions.

**Caveat — still not a wall.** The tool guard is only as strong as the model's
parsing. Trick the model into `city="P​aris"` (zero-width char) or a
different tool, and you are around it again. Taller speed bump, not a wall.

---

## Related

- [[concepts/adk-guardrails]] — the model-call layer (`before_model_callback`)
- [[concepts/adk-prompt-injection-lessons]] — why raw-text guards are reword-able
- [[concepts/adk-sub-agents]] — per-agent callback scope applies here too
- [[concepts/adk-session-state]] — guards write audit flags to state
- [[concepts/adk]] — agent primitives, callbacks
