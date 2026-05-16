# What is Gemini Enterprise Agent Platform

**Source**: https://www.youtube.com/watch?v=j8qW5poBkEU
**Presenter**: Holt Skinner, Developer Advocate, Google Cloud AI
**Date Saved**: 2026-05-16
**Transcript**: transcript.vtt

---

## Summary

Google Cloud announced **Gemini Enterprise Agent Platform** — an evolution of Vertex AI (formerly Model Garden + Agent Builder) restructured around an agent-first lifecycle. The platform covers everything needed to build, deploy, govern, and optimize enterprise-grade AI agents. It is organized around four phases: **Build → Scale → Govern → Optimize**.

---

## Key Concepts

### BUILD

- **ADK (Agent Development Kit)** — Google's open-source framework at `adk.dev`. Supports Python, TypeScript, Java, Go. Builds everything from simple sequential agents to complex multi-agent systems. Latest version supports deterministic graph-based agents (choose between fully dynamic model-led reasoning or strict deterministic logic). Optimized for Gemini but works with any model (Anthropic, Ollama, etc.)
- **MCP (Model Context Protocol)** — The standard pattern to connect agents to external tools. Fully supported by ADK. This is the integration required by the hackathon.
- **A2A (Agent-to-Agent Protocol)** — Built into ADK. Multi-agent systems built like microservices. Every remote agent exposes the same API surface. Supported by LangGraph, CrewAI, AG2.
- **Agent CLI** — Programmatic interface for AI-assisted / "vibe coding" development. Offers Agent Skills for AI-assisted dev, automated evaluation, and automated deployment to runtimes.
- **Agent Studio** — Low-code visual builder inside Cloud Console. Map agent flows, test in real time, see model reasoning, deploy directly to Agent Runtime or export as ADK code (then deploy to Cloud Run, GKE, anywhere).
- **Agent Garden** — Library of pre-built agent templates for common enterprise patterns (financial analysis, marketing campaigns). Good starting point for the hackathon.

### SCALE

- **Agent Runtime** — Managed PaaS specifically for enterprise agents. <1 second cold starts. Supports long-running agents up to **7 days**. Framework-agnostic: works with ADK, LangGraph, LangChain, or custom stacks.
- **Agent Sessions** — Tracks all interactions between users and agents. Auto-managed on Agent Runtime. Supports custom session IDs to map to internal customer/project records.
- **Memory Bank** — Cross-session memory so agents remember users over time without re-asking.
- **Agent Sandbox** — Safe isolated environment for agents that need to execute code or interact with UIs (e.g. legacy apps with no API).

### GOVERN

- **Agent Identity** — Every agent deployed to Agent Runtime gets its own **IAM principal**. Enables attribution of exactly which agent took which action.
- **Agent Registry** — Auto-catalogs agents across Agent Runtime, GKE, Gemini Enterprise, and Google Workspace. Also catalogs first-party MCP servers and MCP servers from Apigee. Supports registering third-party A2A agents and MCP servers for secure access.
- **Agent Policies** — Set IAM policies on agents, tools, and the registry itself.
- **Model Armor + Sensitive Data Protection** — Sanitizes both input prompts and agent responses. Blocks prompt injection attacks and PII leaks.
- **Agent Gateway** — Single entry point that intercepts all ingress/egress calls to audit and enforce policies. Uses **LLM-as-a-judge** anomaly detection to flag weird or stalled reasoning patterns. Security threats visible in Agent Security dashboard.

### OPTIMIZE

- **Agent Observability** — Full visibility into agent decision-making. Turnkey dashboards + automatic tracing showing why an agent made a decision, which tools it called, and where logic went wrong.
- **Agent Topology** — Graph-like view of all agents and MCP servers in a system with aggregated traces.
- **Agent Evaluation** — Automated evaluation of complex multi-step interactions. Addresses the non-deterministic nature of generative AI (can't use traditional unit tests).

---

## Important Moments

- **0:05** — Intro: Holt Skinner introduces Gemini Enterprise Agent Platform
- **0:23** — Four lifecycle phases revealed: Build, Scale, Govern, Optimize
- **0:45** — Naming clarification: Agent Platform = evolution of Vertex AI (same underlying functionality, restructured)
- **1:08** — BUILD section begins: ADK introduced as the core framework
- **1:42** — ADK model flexibility: Gemini-optimized but supports Anthropic, Ollama, etc.
- **2:03** — MCP introduced as the standard tool integration pattern
- **2:13** — A2A protocol for connecting to external agents across frameworks
- **2:37** — Getting started with ADK: go to adk.dev
- **2:52** — Agent CLI introduced for "vibe coding" / agentic-assisted development
- **3:16** — Agent Studio demo: visual builder showing a "Soccer Game Forecast" agent with Gemini 2.5 Pro
- **3:47** — Agent Garden: library of pre-built enterprise agent templates
- **4:07** — SCALE section begins: Agent Runtime as managed PaaS
- **4:20** — Agent Runtime: <1s cold start, up to 7-day long-running agents
- **4:43** — Agent Sessions: multi-user session management
- **5:10** — Memory Bank: cross-session memory
- **5:16** — Agent Sandbox: safe code execution environment
- **5:30** — GOVERN section begins
- **5:47** — Agent Identity: IAM principal per agent
- **5:56** — Agent Registry: auto-cataloging across all deployment targets
- **6:30** — Agent Policies + Model Armor: prompt injection blocking, PII protection
- **6:44** — Agent Gateway: single enforcement point with anomaly detection
- **7:05** — OPTIMIZE section begins: Agent Observability
- **7:38** — Agent Topology: graph view of multi-agent systems
- **7:47** — Agent Evaluation: automated testing for non-deterministic AI

---

## Hackathon Relevance

This is the exact platform stack required for the competition:

| Hackathon Requirement | Platform Component |
|---|---|
| Build AI agent | ADK (adk.dev) |
| Integrate partner MCP server | MCP support in ADK |
| Connect to external agents | A2A protocol |
| Deploy hosted project | Agent Runtime |
| Enterprise-grade submission | Govern + Optimize features |

**Start here:** `adk.dev` → select Python → choose agent design pattern → pick model from Model Garden → build.

**For the hackathon:** Use Agent Garden for templates, MCP for partner integration (Arize, Elastic, Fivetran, GitLab, MongoDB, or Dynatrace), deploy to Agent Runtime.

---

## Related Notes

- [[hackathon/overview]] — Hackathon summary, prizes, challenge themes, submission checklist
- [[hackathon/resources]] — Starter kits, APIs, Google Cloud credits, partner docs
- [[hackathon/rules]] — Eligibility, submission requirements, legal details
