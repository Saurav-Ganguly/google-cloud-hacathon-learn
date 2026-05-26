# TODO

Things queued up — process before diving deeper.

> **Note (2026-05-25):** 2026-05-22, 23, and 24 had no work — no logs
> exist for those days. The graph-workflows item below was originally
> queued for 22; it resumed today as a docs-first session (concept
> rewrite + tutorial). The runnable sandbox is still pending.

---

## Videos to Watch

- [x] https://www.youtube.com/watch?v=nXafozNIk3c — ingested 2026-05-17, notes at [[resources/Agents CLI Build eval and deploy AI agents in minutes/notes]]

---

## Docs to Read

- [ ] https://adk.dev/ — ADK official docs, read before scaffolding first agent
- [x] https://adk.dev/agents/llm-agents/ — `LlmAgent` deep-config COMPLETE 2026-05-20. Built the 2-round Debate Bot sandbox (`test/LlmDebator/agent.py`) exercising every config feature: `{var}` templating, `output_schema`+`output_key`, `generate_content_config`, `BuiltInPlanner`, `include_contents='none'`, plus `google_search` via research-then-structure. New concept: [[concepts/adk-llm-agent-config]]. Original plan: [[plans/plan19.05.2026]] (superseded mid-build: critic-loop → 2 symmetric rounds).
- [x] https://adk.dev/tutorials/agent-team/ — agent-team tutorial COMPLETE 2026-05-19 (all 6 steps). Reference template: `test/agent_teams/agent.py`. Concepts: [[concepts/adk-sub-agents]], [[concepts/adk-litellm-models]], [[concepts/adk-session-state]], [[concepts/adk-guardrails]], [[concepts/adk-tool-guardrails]], [[concepts/adk-prompt-injection-lessons]]
- [x] https://adk.dev/agents/llm-agents/#code-execution — `code_executor` COMPLETE 2026-05-21. Built a 5-agent PDF Explainer pipeline (`test/code_runner/agent.py`) — `intent_capturer → pdf_extractor (LiteLlm deepseek + FunctionTool) → structure_planner → chart_maker (code_executor) → html_renderer` — turning a hardcoded PDF into a Tailwind HTML page with inline matplotlib charts. New concept: [[concepts/adk-code-executor]]. Extended [[concepts/adk-llm-agent-config]] §9-10 (template regex gotcha, latest-alias built-in-tool gap).
- [x] https://adk.dev/graphs/ — Graph-based agent workflows (ADK 2.0). **COMPLETE 2026-05-26**: docs ([[concepts/adk-graph-workflows]] + [[concepts/adk-graph-workflows-tutorial]]) + runnable sandbox `test/idea_refiner/` exercising every primitive (FunctionNode, JoinNode, RequestInput HITL, parallel fan-out + join, **two conditional cycles** — HITL re-prompt and refinement loop, output_schema + planner, LiteLlm deepseek alongside Gemini). All VERIFY-ON-BUILD items resolved; concept doc corrected on the `{ClassName.field}` templating claim (it doesn't exist — use `{simple_key}` from state).
- [ ] https://docs.litellm.ai/docs/ — LiteLLM docs, unified interface for calling 100+ LLMs (model fallback / multi-provider via ADK)
- [x] https://google.github.io/agents-cli/guide/getting-started/ — agents-cli getting started guide, QS3 walked end-to-end 2026-05-17
- [x] https://adk.dev/get-started/streaming/quickstart-streaming/ — streaming quickstart COMPLETE 2026-05-19 (voice + Google Search grounding via `adk web`). Reference: `test/adk_streaming/agent.py`. Gotcha: Vertex Live API needs `GOOGLE_CLOUD_LOCATION=us-central1` (not `global`)

---

## Next Steps

- [x] Install gcloud CLI — done, installed at `C:\Users\Hp\AppData\Local\Google\Cloud SDK\`
- [x] Open new terminal → `gcloud auth application-default login` → re-run `PYTHONUTF8=1 uvx google-agents-cli setup`
- [x] Scaffold first agent with agents-cli: understand the full workflow hands-on
- [x] Learn how to make agents with ADK + agents-cli (QS3 proper)
- [x] Build `arch-social-agent` — 3-agent sequential pipeline (research → LinkedIn post → image gen) — done 2026-05-17
- [x] Complete the ADK agent-team tutorial end-to-end (sub-agents, LiteLlm, state, model + tool guardrails) — done 2026-05-19, vaulted as `test/agent_teams/agent.py` template
- [x] Build Debate Bot sandbox per [[plans/plan19.05.2026]] — done 2026-05-20 as 2-round version (architecture revised mid-build). Drills every `LlmAgent` config feature. Reference template: `test/LlmDebator/agent.py`. New concept: [[concepts/adk-llm-agent-config]].
- [x] Code execution tutorial (`BuiltInCodeExecutor`) — done 2026-05-21 as the 5-agent PDF Explainer (`test/code_runner/agent.py`). New concept: [[concepts/adk-code-executor]].
- [x] Graph-based agent workflows basics — **COMPLETE 2026-05-26**. Sandbox `test/idea_refiner/` built end-to-end (10 nodes, 11 edges, 2 conditional cycles). Docs corrected: `{ClassName.field}` instruction syntax doesn't exist in ADK 2.0 — use `{simple_key}` from state with FunctionNodes unpacking Pydantic outputs.
- [ ] **Re-test `agents-cli playground` on v0.2.0** — still pending from 2026-05-21 carry-over.
- [ ] **NEXT (hackathon critical path)**: Add a partner MCP server to `arch-social-agent` to make it hackathon-eligible (candidates: Elastic, MongoDB, Arize) — see [[concepts/adk-mcp-integration]]

---

## Related

- [[index]] — Knowledge map
- [[resources/agents-cli/notes]] — agents-cli reference
- [[resources/agent-platform-onboard/notes]] — QS3 is the full code path
- [[logs/2026-05-26]] — last session log (Idea Refiner sandbox build)
- [[logs/2026-05-25]] — prior session log (graph workflows docs phase)
