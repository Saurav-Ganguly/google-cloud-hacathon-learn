# Introducing Agents CLI in Agent Platform

**Source**: https://www.youtube.com/watch?v=ECYKo70pPNc
**Presenters**: Pier Paolo Ippolito (Product Manager), Ivan Cheung (Software Engineer) — Google
**Date Saved**: 2026-05-16
**Transcript**: transcript.vtt

---

## Summary

Official announcement and demo of agents-cli — a tool that gives coding agents (Claude Code, Gemini CLI, etc.) the skills and commands to build, evaluate, deploy, and publish ADK agents on Google Cloud. The video walks through a complete end-to-end demo: building an outage recovery agent from a natural language prompt all the way to a published Gemini Enterprise agent, with Gemini CLI doing all the heavy lifting.

---

## Key Concepts

- **The problem**: Building agents on Google Cloud is fragmented — AI coding assistants hallucinate APIs and get stuck in loops without proper grounding
- **agents-cli as a bridge**: Packages all Google Cloud tools into a simple CLI + a set of skills that teach coding agents the full ADK lifecycle
- **The 4-step lifecycle**: scaffold → eval → deploy → publish
- **Skills as the key insight**: The CLI comes with 7 bundled skills that inform coding agents *how* to use each command correctly — not just what to run
- **Gemini Enterprise integration**: Deployed agents can be registered to Gemini Enterprise so teams can use them directly in their everyday workspace, no custom frontend needed
- **YOLO mode**: Gemini CLI's `Ctrl+Y` autonomous mode — lets the agent execute the full workflow without approval at each step

---

## Demo Walkthrough (Outage Recovery Agent)

### 1. Scaffold (0:57 — 1:47)
User tells Gemini CLI: *"I need to build an outage recovery agent that can parse server logs, classify incidents by severity, and generate incident reports. Use ADK, deploy to Google Cloud."*

Gemini CLI activates the **scaffold skill** → runs `agents-cli scaffold` → generates standard ADK folder structure → modifies boilerplate to match the use case.

### 2. Evaluate (1:49 — 2:40)
User: *"Run the evaluations for the outage recovery agent using agents-cli and show me the results."*

Gemini CLI adds eval scenarios (hypothetical conversations + expected tool calls + LLM judge criteria) → runs `agents-cli eval run`.

Eval output shows **perfect scores** on 3 criteria:
- **Relevance** (1.0 / 100% pass rate) — response directly addresses the query
- **Accuracy** (1.0 / 100% pass rate) — correctly maps log lines to severity levels (INFO/WARNING/CRITICAL)
- **Action Taken** (1.0 / 100% pass rate) — agent saved incident report and informed user

### 3. Deploy (2:56 — 3:11)
User: *"Let's deploy this agent to Google Cloud."*

Gemini CLI runs `agents-cli deploy` → agent pushed to **Agent Runtime** (Vertex AI Agent Engine).
Output shows: Agent Engine ID, service account, link to Console Playground.

### 4. Publish to Gemini Enterprise (3:19 — 3:48)
User: *"Can you integrate this with Gemini Enterprise?"*

Agent registered directly to Gemini Enterprise. Team can now select the outage recovery agent from the Gemini Enterprise UI — no custom frontend needed. Agent has secure access to production logs.

---

## Important Moments

- `0:05` — Presenters introduced: Pier Paolo Ippolito (PM) + Ivan Cheung (SWE)
- `0:17` — agents-cli announced as a single tool for building + deploying ADK agents
- `0:35` — "Think of agents-cli as a bridge — it packages all the Google Cloud tools you need into a simple command line interface"
- `0:45` — "It comes with a set of skills to guide the coding agent throughout the process"
- `1:30` — Gemini CLI demo starts: scaffold skill activated, ADK folder structure generated
- `1:49` — Evaluation harness introduced: "How do we guarantee quality at enterprise level?"
- `2:08` — `agents-cli eval run` executed, LLM-as-judge results shown — perfect scores
- `3:06` — Deployment successful: Agent Runtime (Vertex AI Agent Engine) with full IAM/secret management automated
- `3:22` — Published to Gemini Enterprise; team can use it in everyday workspace
- `4:06` — "agents-cli cuts down the busy work, saves time and token cost, and actually gets your agents to production"

---

## Hackathon Relevance

This is the core workflow for QS3 — the serious hackathon build path. Key takeaways:
- The eval step (`agents-cli eval run`) is what separates a prototype from a submission-ready agent — use it before deploying
- Gemini Enterprise publishing is the final step to make the agent usable by non-technical team members — worth doing for the demo
- The demo shows that the full lifecycle (idea → deployed, evaluated, published agent) can happen in one conversation session with Claude Code or Gemini CLI

---

## Related Notes

- [[index]] — Knowledge map
- [[concepts/adk]] — ADK is the agent framework agents-cli builds on
- [[concepts/agent-runtime]] — Vertex AI Agent Engine is the deployment target shown in the demo
- [[concepts/vertex-ai]] — Gemini Enterprise is the publish target
- [[resources/agents-cli/notes]] — Full agents-cli reference: install, commands, auth
- [[resources/agent-platform-onboard/notes]] — QS3 is this exact workflow
