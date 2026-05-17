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
- [[concepts/adk]] — Agent Development Kit (adk.dev)
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
- [[resources/day 1/Agents CLI Build eval and deploy AI agents in minutes/notes]] — Deep dive: ADK 2.0, graph workflows, ambient agents, resume agents, PR roaster demo (Shubham Saboo, Google Cloud Tech)

## Guides & References

- [[resources/agent-platform-onboard/notes]] — Official onboarding guide: Agent Studio, Agent Designer, ADK + agents-cli (Eric Dong, Apr 2026)
- [[resources/agents-cli/notes]] — agents-cli reference: install, commands, skills, auth, local dev without gcloud (v0.1.3, installed 2026-05-16)
- [[resources/cloud-run-pricing/notes]] — Cloud Run pricing breakdown + cron job cost estimate (free tier covers ~2 hrs/day of jobs)
- [[configs/agents-cli-setup]] — GCP project, auth, .env, Windows gotchas — read before scaffold/run/deploy
- [[configs/run-agent-locally]] — Definitive local-run runbook (Windows): test script + `adk web`, why `agents-cli playground` is broken

---

## General Learning

- [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) — curated real LLM app examples, good for project inspiration
- [The Unwind AI](https://www.theunwindai.com/) — AI tutorials and agent walkthroughs

---

## Daily Logs

- [[logs/2026-05-16]] — QS1 complete: Agent Studio → Cloud Run app deployed
- [[logs/2026-05-17]] — QS3 complete: ADK + agents-cli full path (scaffold → eval → deploy → teardown)

---

## TODO

- [[todo]] — Queued videos, next steps, pending tasks

---

## Ideas

*(none yet)*

---

## Projects

- [[projects/arch-social-agent]] — 3-agent sequential pipeline: web research → LinkedIn post + image prompt → Gemini image generation. Needs partner MCP to be hackathon-eligible.
