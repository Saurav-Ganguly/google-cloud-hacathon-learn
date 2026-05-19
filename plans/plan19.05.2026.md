# Plan — Model-vs-Model Debate Bot (LlmAgent feature sandbox)

**Created**: 2026-05-19
**Tutorial**: https://adk.dev/agents/llm-agents/ — ADK `LlmAgent` reference
**Status**: Queued — build tomorrow (2026-05-20)
**Concepts**: [[concepts/adk]] · [[concepts/adk-litellm-models]] · [[concepts/adk-session-state]] · [[concepts/adk-sub-agents]]

---

## Why

The ADK [`LlmAgent` page](https://adk.dev/agents/llm-agents/) documents features
**never used hands-on** in this vault (verified against `test/agent_teams/agent.py`,
`test/adk_streaming/agent.py`, [[projects/arch-social-agent]]):

1. `instruction` state-variable templating (`{var}`)
2. `generate_content_config` (temperature / max_output_tokens / safety_settings)
3. `input_schema` / `output_schema` / `output_key` (structured I/O)
4. `planner` (`BuiltInPlanner`, `PlanReActPlanner`)

A **pure learning sandbox**: two *different LLMs* (via LiteLlm) debate opposite
sides, a third model judges. Drills every feature in one small fun project.
Outcome = annotated reference agent + a new concept note, same pattern as the
existing `concepts/adk-*` notes.

## Architecture

`SequentialAgent` `debate_arena`, three sub-agents in order:

```
DebateInput{topic}            (input_schema — typed JSON entry)
   |
 pro_agent  (LiteLlm model A, hot temp)  --output_key--> state["pro_case"]
   |
 con_agent  (LiteLlm model B, cold temp) --output_key--> state["con_case"]
   |   (instruction injects {pro_case} -> rebut Pro directly)
 judge_agent (native Gemini, BuiltInPlanner thinking)
   |   (include_contents='none'; instruction injects {pro_case}+{con_case})
   +--output_key--> state["verdict"]   (output_schema Verdict)
```

Sequential order is what makes templating work: Con can't read `{pro_case}`
until Pro wrote it; Judge needs both. See [[concepts/adk-session-state]].

## Feature → implementation

| Feature | Use |
|---|---|
| `input_schema` | `DebateInput{topic:str}` on `pro_agent`; user msg must be JSON `{"topic":"..."}` |
| `output_schema` | `ProCase{thesis,arguments[]}`, `ConCase{rebuttals[],counter_arguments[]}`, `Verdict{winner,reasoning,pro_score,con_score}` |
| `output_key` | pro→`pro_case`, con→`con_case`, judge→`verdict` |
| `{var}` templating | Con: `"Pro argued: {pro_case}. Rebut every point."` Judge: `"PRO: {pro_case}\nCON: {con_case}"` |
| `include_contents='none'` | Judge — judges ONLY from injected state, not chat history (proves state-passing, not history, does the work) |
| `generate_content_config` | Pro `temperature=0.95`; Con `temperature=0.25`; `max_output_tokens=600`; Judge `safety_settings` (DANGEROUS_CONTENT → BLOCK_ONLY_HIGH) so spicy topics aren't refused |
| `planner` | Judge: `BuiltInPlanner(ThinkingConfig(include_thoughts=True, thinking_budget=512))` |
| LiteLlm multi-model | Pro = OpenRouter model A, Con = OpenRouter model B (different models fighting); pattern from [[concepts/adk-litellm-models]] (`extra_body={"reasoning":{"enabled":False}}`). Judge = native `gemini-flash-latest` (needed for thinking) |

### Gotchas to capture in the new concept note

- **`PlanReActPlanner` ✗ `output_schema`**: ReAct emits `/*PLANNING*/…/*FINAL_ANSWER*/`
  markers; `output_schema` demands pure JSON — they fight. Resolution: Judge uses
  `BuiltInPlanner` (native Gemini thinking is a separate channel, coexists with
  `output_schema`). Record *why PlanReActPlanner was rejected here*.
- **`output_schema` disables tool calling** on non-Gemini models → Pro/Con are
  deliberately tool-free (no `google_search` grounding); arguments come from
  model knowledge only. Acceptable for a sandbox; note the tradeoff.

## Models (swappable, one-line edit at top of agent.py)

- Pro: `openrouter/tencent/hy3-preview` (known-working here)
- Con: a *different* OpenRouter model (e.g. `openrouter/deepseek/deepseek-chat`) — point is Pro ≠ Con
- Judge: `gemini-flash-latest` (native; required for `BuiltInPlanner`)

## Files

```
test/debate_bot/
  __init__.py        # from . import agent
  agent.py           # 3 agents + SequentialAgent, annotated like test/agent_teams/agent.py
  .env               # copy test/agent_teams/.env verbatim (Vertex global OK — BuiltInPlanner
                     #   thinking is NOT the Live API; OPENROUTER_API_KEY required)
  test_debate.py     # InMemoryRunner — sends JSON {"topic":"..."}, prints pro/con/verdict
```

Test script (not just `adk web`) because `input_schema` requires a JSON user
message — scripted `InMemoryRunner` is the clean path per [[configs/run-agent-locally]].

## Incremental steps

1. Scaffold `test/debate_bot/` (`__init__.py`, `.env` from `test/agent_teams/.env`).
2. Define 4 Pydantic models.
3. `pro_agent` only → validate `state["pro_case"]` is valid JSON. **Stop & check.**
4. Add `con_agent` (injects `{pro_case}`) → validate Con rebuts Pro's specific points.
5. Add `judge_agent` (`BuiltInPlanner`, `include_contents='none'`, `output_schema`, `safety_settings`) → validate `state["verdict"]`; thinking events visible.
6. Annotate `agent.py` (feature headers + concept cross-refs).
7. Write `concepts/adk-llm-agent-config.md` (4 features + 2 gotchas); add to [[index]] (Core Concepts + Reference Code).
8. Append `logs/2026-05-20.md` entry; tick the item in [[todo]].
9. One git commit. **Never stage `.env`** (live OpenRouter key).

## Verify

```powershell
cd c:\Users\Hp\Desktop\code\google_cloud_hacathon\test\debate_bot
$env:PYTHONUTF8=1
uv run python test_debate.py
```

Expect: `pro_case` JSON (bold thesis), `con_case` JSON whose rebuttals cite
Pro's actual points, `verdict` JSON with winner + per-side scores. Confirm each
behavior is observable (Con cites Pro = templating; Judge ignores history =
`include_contents='none'`; thinking events = `BuiltInPlanner`; spicy topic
passes = relaxed `safety_settings`). Then run once via
`adk web . --port 8080` typing `{"topic":"..."}` to exercise the `input_schema` path.

## Out of scope (YAGNI)

Multi-round `LoopAgent`; `google_search` (collides with `output_schema`);
`code_executor` / `{artifact.var}` / `AgentTool` — note they exist, not needed here.

---

## Related

- [[index]] — knowledge map
- [[todo]] — queued tasks
- [[concepts/adk]] — ADK deep reference (LlmAgent config section)
- [[concepts/adk-litellm-models]] — the multi-model LiteLlm pattern this reuses
- [[concepts/adk-session-state]] — `output_key` + state templating mechanism
- [[logs/2026-05-19]] — session where this plan was designed
