# ADK + LiteLlm: non-Gemini models & the reasoning-leak gotcha

How to use non-Gemini models in [[concepts/adk]] agents via `LiteLlm`, and the
reasoning-content trap when those models are reasoning models reached through
OpenRouter. Discovered while building the [[resources/agents-cli/notes]] agent-team
tutorial (greeting/farewell sub-agents on a cheap model).

---

## Using a non-Gemini model

ADK agents take `model=` as either a string (Gemini, native) or a `LiteLlm`
wrapper for anything LiteLLM supports:

```
from google.adk.models.lite_llm import LiteLlm
Agent(model=LiteLlm(model="openrouter/deepseek/deepseek-v4-pro"), ...)
```

The `LiteLlm` constructor forwards extra kwargs down to `litellm.completion()`.
That forwarding is the key to everything below.

A common multi-agent pattern: put Gemini on the coordinator (`root_agent`) and a
cheaper model on trivial sub-agents (see [[concepts/adk-multi-agent]]).

---

## The reasoning-leak problem

**Symptom**: a sub-agent on a reasoning model (deepseek-v4-pro) returned its
final answer with the chain-of-thought glued on:

> "The tool returned 'Hello there!' ... I'll present this to the user.Hello there!"

**Root cause** — a *path* problem, not a prompt problem:

1. Gemini's adapter maps reasoning to a dedicated **thought channel**; ADK's
   dev-UI renders it as a separate `THOUGHT` block.
2. The ADK `LiteLlm` adapter **drops** LiteLLM's separate `reasoning_content`
   channel ([adk-python #3694](https://github.com/google/adk-python/issues/3694)).
3. deepseek-v4-pro emits reasoning **inline as plain content** anyway, so it
   lands inside the final answer string. No prompt instruction fixes this — the
   leak is structural.

Tightening the instruction ("do not return thinking steps") does **not** work —
it decorates the symptom, not the cause.

---

## The fix: turn reasoning off at the source

The off-switch depends on the **provider doorway**, not the model:

- Native DeepSeek provider (`deepseek/...`): `reasoning_effort="none"`.
- **Via OpenRouter** (`openrouter/deepseek/...`): `reasoning_effort` is
  **rejected** — `litellm.UnsupportedParamsError`. OpenRouter uses its own
  `reasoning` object instead.

OpenRouter's request body accepts:

```
reasoning: { effort, max_tokens, exclude: bool, enabled: bool }
```

- `enabled: false` — model does not reason at all. Best for trivial one-tool
  agents (greeting/farewell). Fastest, cheapest.
- `exclude: true` — model still reasons internally but it is stripped from the
  response. Use when the reasoning genuinely helps answer quality but you don't
  want it surfaced.

Pass it through LiteLLM's provider **passthrough channel** — `extra_body`
(NOT `allowed_openai_params`/`drop_params`, which are for OpenAI-standard params):

```
LiteLlm(
    model="openrouter/deepseek/deepseek-v4-pro",
    extra_body={"reasoning": {"enabled": False}},
)
```

Result: clean `Hello there!`, no THOUGHT block, no leak.

---

## Transferable debugging lesson

Every bug in this episode was *the path to the thing*, not the thing:

1. Wrong import **source** — `pyparsing.Optional` vs `typing.Optional`.
2. Wrong **target** — fix applied to `farewell_agent`, test hit `greeting_agent`.
3. Wrong provider **doorway** — `reasoning_effort` is a native-DeepSeek param,
   not an OpenRouter one.
4. Right param, right **passthrough channel** — `extra_body`.

Always prove *which code path the test exercises* before concluding a fix failed.

---

## Reference implementation

`test/agent_teams/agent.py` — heavily commented template demonstrating
LiteLlm + `extra_body` reasoning-off alongside sub-agents, session state, and
a guardrail. Single best file to copy patterns from.

---

## Related

- [[concepts/adk]] — agent primitives, model selection
- [[concepts/adk-multi-agent]] — coordinator-on-Gemini, sub-agents-on-cheap-model pattern
- [[concepts/adk-sub-agents]] — putting cheap models on delegated specialists
- [[concepts/adk-session-state]] — shared state across the team
- [[concepts/adk-guardrails]] — `before_model_callback` contract
- [[concepts/adk-prompt-injection-lessons]] — model identity / prove-the-path discipline
- [[configs/agents-cli-setup]] — auth / .env / Windows gotchas
- [[configs/run-agent-locally]] — how `adk web` is run locally on Windows
