# Knowledge Map

> Entry point for all hackathon research. Navigate here first.

---

## Hackathon

- [[hackathon/overview]] — What we're building, prizes, judging criteria
- [[hackathon/rules]] — Eligibility, submission requirements, dates
- [[hackathon/resources]] — Starter kits, APIs, Google Cloud credits
- [[hackathon/links]] — Key links: devpost, ADK, partner resources

---

## Core Concepts

- [[concepts/vertex-ai]] — Gemini Enterprise Agent Platform (Build/Scale/Govern/Optimize)
- [[concepts/adk]] — Agent Development Kit: primitives, agent types, workflow agents, state (deep reference)
- [[concepts/adk-llm-agent-config]] — `LlmAgent` deep config: schemas, planner, content-config, state templating, `include_contents`, the output_schema↔tools constraint, Gemini-2.5 thinking-budget gotcha, ADK templater regex (`{{...}}` does NOT escape), latest-alias built-in-tool gap
- [[concepts/adk-code-executor]] — `code_executor=BuiltInCodeExecutor()` reference: sandbox limits, reading `part.code_execution_result.output`, mutual-exclusion with `output_schema` + LiteLlm, and the canonical placeholder-substitution pattern for piping LLM artifacts to downstream
- [[concepts/adk-graph-workflows]] — ADK 2.0 graph-based workflows: conditional branching, parallel + join (Beta)
- [[concepts/adk-multi-agent]] — Multi-agent patterns: coordinator, pipeline, fan-out, generator-critic, A2A
- [[concepts/adk-litellm-models]] — Non-Gemini models via LiteLlm + the OpenRouter reasoning-leak gotcha (extra_body fix)
- [[concepts/adk-sub-agents]] — Coordinator/sub-agent delegation; "control sticks" + positive routing
- [[concepts/adk-session-state]] — Per-session memory: read/write, output_key, seeding gotchas
- [[concepts/adk-guardrails]] — `before_model_callback` contract, per-agent scope
- [[concepts/adk-tool-guardrails]] — `before_tool_callback`: guard the resolved action, not the phrasing
- [[concepts/adk-prompt-injection-lessons]] — Live attack: guardrail bypass, keyword evasion, hallucinated identity
- [[concepts/adk-mcp-integration]] — Connecting MCP servers to ADK agents (hackathon critical path)
- [[concepts/adk-ambient-agents]] — Event-driven background agents: Pub/Sub, Eventarc, Cloud Scheduler
- [[concepts/mcp]] — Model Context Protocol (tool integration)
- [[concepts/a2a]] — Agent-to-Agent protocol (multi-agent systems)
- [[concepts/agent-runtime]] — Managed PaaS for deployed agents

---

## Partner Tracks

- [[partners/elastic]] — Elastic MCP server
- [[partners/mongodb]] — MongoDB MCP server
- [[partners/gitlab]] — GitLab MCP server
- [[partners/fivetran]] — Fivetran MCP server
- [[partners/arize]] — Arize MCP server
- [[partners/dynatrace]] — Dynatrace MCP server

---

## Videos & Resources (Day 1)

- [[resources/day 1/What is Gemini Enterprise Agent Platform/notes]] — Agent Platform overview (Holt Skinner)
- [[resources/day 1/Introducing Agents CLI in Agent Platform/notes]] — agents-cli demo: scaffold → eval → deploy → publish, end-to-end in one session (Pier Paolo Ippolito + Ivan Cheung)
- [[resources/Agents CLI Build eval and deploy AI agents in minutes/notes]] — Deep dive: ADK 2.0, graph workflows, ambient agents, resume agents, PR roaster demo (Shubham Saboo, Google Cloud Tech)

## Guides & References

- [[resources/agent-platform-onboard/notes]] — Official onboarding guide: Agent Studio, Agent Designer, ADK + agents-cli (Eric Dong, Apr 2026)
- [[resources/agents-cli/notes]] — agents-cli reference: install, commands, skills, auth, local dev without gcloud (v0.2.0, upgraded 2026-05-20 from v0.1.3; new commands: `data-ingestion`, `lint`, `publish`, `infra`, `login`)
- [[resources/cloud-run-pricing/notes]] — Cloud Run pricing breakdown + cron job cost estimate (free tier covers ~2 hrs/day of jobs)
- [[configs/agents-cli-setup]] — GCP project, auth, .env, Windows gotchas — read before scaffold/run/deploy
- [[configs/run-agent-locally]] — Definitive local-run runbook (Windows): test script + `adk web`, why `agents-cli playground` is broken

## Reference Code

- `test/adk_streaming/agent.py` — **minimal streaming-agent reference**: `Agent` + `google_search` grounding + Live model (`gemini-live-2.5-flash-native-audio`), run via `adk web` voice. Copy this when building any voice/video streaming agent. Gotcha: Vertex Live API requires `GOOGLE_CLOUD_LOCATION=us-central1`, never `global` (see [[logs/2026-05-19]]).
- `test/agent_teams/agent.py` — **canonical annotated ADK feature template** (full agent-team tutorial, all 6 steps): multi-agent delegation, LiteLlm models, session state + `output_key`, model guardrail (`before_model_callback`), tool guardrail (`before_tool_callback`). Best file to copy any of these patterns from later — each section cross-references its `concepts/adk-*` note above.
- `test/LlmDebator/agent.py` — **canonical annotated `LlmAgent`-deep-config template** (2-round Debate Bot, 2026-05-20): 7 agents in a `SequentialAgent`, every feature from [[concepts/adk-llm-agent-config]] used in context — Pydantic `output_schema` + `output_key`, `{var}` state-var templating across 4 rounds, `BuiltInPlanner` thinking, `include_contents='none'`, `generate_content_config` (per-agent temperature + safety_settings + thinking_budget), `google_search` composed with structured output via the research-then-structure pattern, `after_agent_callback` returning labeled `Content` to make `adk web` bubbles show "agent (model)" headers. Best file to copy LlmAgent config patterns from.
- `test/code_runner/agent.py` — **canonical annotated `code_executor` template** (PDF Explainer, 2026-05-21): 5-agent `SequentialAgent` — `intent_capturer` (Gemini schema-fill) → `pdf_extractor` (LiteLlm deepseek + `FunctionTool`, drills FunctionTool-with-LiteLlm) → `structure_planner` (Gemini + `BuiltInPlanner`) → `chart_maker` (Gemini + `BuiltInCodeExecutor`, pinned to `gemini-2.5-flash` since `*-latest` aliases drop the tool) → `html_renderer` (Gemini, free-text HTML). Demonstrates `part.code_execution_result.output` reading, the placeholder-substitution pattern for keeping base64 OUT of LLM prompts, and the ADK templater `{var}` gotcha (no `{{...}}` escape). Best file to copy `code_executor` patterns from.

---

## General Learning

- [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) — curated real LLM app examples, good for project inspiration
- [The Unwind AI](https://www.theunwindai.com/) — AI tutorials and agent walkthroughs

---

## Daily Logs

- [[logs/2026-05-16]] — QS1 complete: Agent Studio → Cloud Run app deployed
- [[logs/2026-05-17]] — QS3 complete: ADK + agents-cli full path (scaffold → eval → deploy → teardown)
- [[logs/2026-05-18]] — ADK deep dive: sub-agents, LiteLlm, session state, model guardrail, live prompt-injection
- [[logs/2026-05-19]] — agent-team tutorial COMPLETE: tool guardrail + "guard the action, not the phrasing"
- [[logs/2026-05-20]] — Debate Bot sandbox COMPLETE: 7-agent Sequential pipeline, every `LlmAgent` config feature exercised; new concept note [[concepts/adk-llm-agent-config]]
- [[logs/2026-05-21]] — PDF Explainer sandbox COMPLETE: 5-agent pipeline drilling `code_executor` + `FunctionTool`-with-LiteLlm. New concept [[concepts/adk-code-executor]]; extended [[concepts/adk-llm-agent-config]] §9-10 with two ADK gotchas (templater regex + latest-alias built-in-tool gap)

---

## TODO

- [[todo]] — Queued videos, next steps, pending tasks

---

## Ideas

*(none yet)*

---

## Projects

- [[projects/arch-social-agent]] — 3-agent sequential pipeline: web research → LinkedIn post + image prompt → Gemini image generation. Needs partner MCP to be hackathon-eligible.

---

## Plans

- [[plans/plan19.05.2026]] — Model-vs-Model Debate Bot sandbox: learn the 4 unused `LlmAgent` features (instruction state-vars, `generate_content_config`, schemas+`output_key`, `planner`) + LiteLlm models debating each other. Queued for 2026-05-20.
