# ADK Guardrails (`before_model_callback`)

A callback that runs **before** an agent's LLM call, able to inspect the
request and short-circuit it. Deterministic, code-level — unlike instruction
wording, which is unreliable model judgment. Part of [[concepts/adk]]. The
second layer — gating the *tool call* the model decided on — is
[[concepts/adk-tool-guardrails]].

**Reference template**: `test/agent_teams/agent.py` (`block_keyword_guardrail`).

---

## The contract (memorise this)

```python
def block_keyword_guardrail(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    ...
    return None          # -> ADK proceeds to the LLM normally
    # OR
    return LlmResponse(  # -> ADK SKIPS the LLM and returns this instead
        content=types.Content(role="model", parts=[types.Part(text="refused")])
    )
```

Wire it on the agent:

```python
root_agent = Agent(..., before_model_callback=block_keyword_guardrail)
```

Reading the user message: walk `llm_request.contents` in reverse for the last
`role == "user"` part. Record the event in state for auditability:
`callback_context.state["guardrail_block_keyword_triggered"] = True` — a later
callback, analytics job, or eval can read that flag.

---

## Per-agent scope (critical)

`before_model_callback` fires **only for the agent it is attached to**.
Combined with "control sticks" ([[concepts/adk-sub-agents]]): a guardrail on
root does **nothing** while a sub-agent holds the conversation. To cover the
whole team, attach the *same* function to every agent.

---

## Deterministic vs model judgment

| Layer | Catches | Misses | Cost |
|---|---|---|---|
| Deterministic callback (keyword/regex/schema/PII) | enumerable known-bad | paraphrase, synonyms | ~free |
| Model / classifier judgment | fuzzy & semantic intent | itself attackable; non-deterministic | latency + $ |

Neither alone is enough. Production pattern: cheap deterministic filter first,
then a semantic classifier (or guard agent) for what it misses. The strongest
defence is architectural — **don't put secrets in model-reachable context**;
you cannot leak what isn't there.

The concrete failure modes of the naive keyword filter are documented in
[[concepts/adk-prompt-injection-lessons]] — read that before trusting one.

---

## Related

- [[concepts/adk]] — agent primitives, callbacks
- [[concepts/adk-tool-guardrails]] — the second layer: gate the resolved action
- [[concepts/adk-sub-agents]] — why per-agent scope matters (control sticks)
- [[concepts/adk-session-state]] — callbacks use state for audit flags
- [[concepts/adk-prompt-injection-lessons]] — live evasions of this guardrail
