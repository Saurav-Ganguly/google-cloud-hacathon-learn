# TODO

Things queued up — process before diving deeper.

---

## Videos to Watch

- [x] https://www.youtube.com/watch?v=nXafozNIk3c — ingested 2026-05-17, notes at [[resources/Agents CLI Build eval and deploy AI agents in minutes/notes]]

---

## Docs to Read

- [ ] https://adk.dev/ — ADK official docs, read before scaffolding first agent
- [x] https://adk.dev/tutorials/agent-team/ — agent-team tutorial COMPLETE 2026-05-19 (all 6 steps). Reference template: `test/agent_teams/agent.py`. Concepts: [[concepts/adk-sub-agents]], [[concepts/adk-litellm-models]], [[concepts/adk-session-state]], [[concepts/adk-guardrails]], [[concepts/adk-tool-guardrails]], [[concepts/adk-prompt-injection-lessons]]
- [ ] https://docs.litellm.ai/docs/ — LiteLLM docs, unified interface for calling 100+ LLMs (model fallback / multi-provider via ADK)
- [x] https://google.github.io/agents-cli/guide/getting-started/ — agents-cli getting started guide, QS3 walked end-to-end 2026-05-17

---

## Next Steps

- [x] Install gcloud CLI — done, installed at `C:\Users\Hp\AppData\Local\Google\Cloud SDK\`
- [x] Open new terminal → `gcloud auth application-default login` → re-run `PYTHONUTF8=1 uvx google-agents-cli setup`
- [x] Scaffold first agent with agents-cli: understand the full workflow hands-on
- [x] Learn how to make agents with ADK + agents-cli (QS3 proper)
- [x] Build `arch-social-agent` — 3-agent sequential pipeline (research → LinkedIn post → image gen) — done 2026-05-17
- [x] Complete the ADK agent-team tutorial end-to-end (sub-agents, LiteLlm, state, model + tool guardrails) — done 2026-05-19, vaulted as `test/agent_teams/agent.py` template
- [ ] **NEXT (hackathon critical path)**: Add a partner MCP server to `arch-social-agent` to make it hackathon-eligible (candidates: Elastic, MongoDB, Arize) — see [[concepts/adk-mcp-integration]]

---

## Related

- [[index]] — Knowledge map
- [[resources/agents-cli/notes]] — agents-cli reference
- [[resources/agent-platform-onboard/notes]] — QS3 is the full code path
- [[logs/2026-05-16]] — last session log
