# Google's Agents CLI: Build, Eval, and Deploy AI Agents in Minutes

**Source**: https://www.youtube.com/watch?v=nXafozNIk3c
**Channel**: Google Cloud Tech — The Agent Factory
**Guest**: Shubham Saboo, Senior AI Product Manager at Google (creator of [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps), 105K stars)
**Date Published**: 2026-04-27
**Date Saved**: 2026-05-17
**Duration**: 53 minutes
**Transcript**: transcript.en.vtt

---

## Summary

Full walkthrough of [[concepts/adk]] 2.0 and [[configs/agents-cli-setup]] by the PM who built it. Two live demos (caveman compressor built + deployed end-to-end in ~10 minutes; multi-agent PR roaster with image generation). Covers ADK 2.0's new graph-based workflows, ambient agents, and resume agents. Ends with rapid-fire opinions on agent architecture philosophy.

---

## What Is agents-cli

agents-cli = CLI + skills package bundled together. Install once, globally picked up by any coding agent (Gemini CLI, Claude Code, Codex, etc.). The skills give the coding agent deep knowledge of ADK internals, syntax, and best practices — no more copy-pasting from docs.

**7 skills covering the full lifecycle:**
1. Scaffold (create project structure)
2. Build (implement agent logic)
3. Eval (generate + run evaluations)
4. Deploy (to Agent Runtime / Cloud Run / GKE)
5. Observe (telemetry + tracing)
6. Publish
7. Workflow guidance

**Install:**
```bash
uvx google-agents-cli   # or: uv tool install google-agents-cli
```

**Key insight from Shubham**: before agents-cli, asking a coding agent to build ADK code meant hallucinations or broken imports. agents-cli fixes this by giving the coding model authoritative, current ADK knowledge as a skill.

---

## Demo 1: Caveman Compressor (Single Agent, ~10 min end-to-end)

Prompt given to Gemini CLI:
> "Use agent CLI to build a caveman style agent that compresses verbose text into technical grunts."

What agents-cli did automatically:
1. Scaffolded project with correct structure
2. Wrote agent code with proper ADK imports
3. Ran a smoke test (verbose input → caveman output, e.g. "Model wars hot. Buy more H100s.")
4. Started ADK web UI at `localhost:8080` for interactive testing
5. Deployed to Agent Engine when asked ("deploy to agent engine")
6. Generated 20 eval criteria AND ran them — all passing

Deployment takes ~5-10 minutes. agents-cli always asks for explicit approval before touching external services.

**State after 10 minutes**: Agent built → tested locally → deployed to Agent Engine → evals passing → tools addable via prompt.

---

## Demo 2: Multi-Agent PR Roaster

**Architecture**: Streamlit app + 2 ADK agents in sequence:
- **Agent 1 (Code Analyst)** — fetches GitHub PR, scores for quality/bugs/security/performance
- **Agent 2 (Roast Master)** — takes analyst output, writes jokes + generates a meme prompt → feeds to **`gemini-flash-image-preview`** (the image model, called "nanobanana" in demo) to generate a meme image

**Live result**: PR scored 9.2/10. Roast: *"Calling load_env twice is like checking if you locked the front door, walking to your car, and going back to check again while your house is in your car because of your error handling."* Meme generated.

**Key quote**: "Prompt history is the new code. All you need is the prompt to regenerate the code."

Built entirely from terminal without opening an IDE.

---

## ADK 2.0 New Features

### 1. Graph-Based Agent Workflows

**Problem solved**: Prompt-only multi-agent workflows become "lazy" by turn 5-7 — agent forgets earlier tool calls, skips rules, takes shortcuts.

**Solution**: Explicitly draw the agent flow graph. Two node types:
- **Deterministic nodes** — compliance checks, routing logic, validation. Never changes regardless of LLM. Reliable and auditable.
- **Reasoning nodes** — model decides dynamically (tool selection, content generation).

**Same workflow gives you both.** Use deterministic where reliability matters, reasoning nodes where flexibility matters.

### 2. Ambient Agents

Agents that trigger themselves — no human prompt required.

**Trigger types:**
- Pub/Sub message arrives
- File lands in Cloud Storage / local drive
- Cron job fires at scheduled time

**Out of the box**: concurrency limits, retries, dead letter queues — no infrastructure code needed.

**Shubham's own setup**: 6-agent team running 24/7 on Open Claude, managing social media, newsletter, and open source repo (agent named "Ross" manages PRs on awesome-llm-apps).

### 3. Resume Agents

**Problem**: Production agents run for hours or days. Network drops, services go down.

**Solution**: One flag:
```python
# In App config
is_resumable=True
```

Tracks which tools already ran → skips them on restart → resumes from the exact breakpoint. Previously required restart from scratch.

### 4. Multi-Language ADK

ADK now supports: **Python, TypeScript, Go, Java**

Teams don't need to rewrite existing stacks to use ADK. Use whatever language your current workflows are in.

---

## Open Ecosystem

Google built an open ecosystem of tools and plugins for ADK — not just Google tools, sourced from what developers actually asked for. Add with a line or few lines of code. This includes MCP servers, partner integrations, etc.

---

## Agent Design Philosophy (Rapid Fire + Discussion)

### "Best agent architecture is the simplest one that works"
**100% agree.** Shubham has reviewed hundreds of LLM apps — the most popular ones always have the simplest architecture. People should be able to run it and read the code.

### "RAG is dead, fine-tuning is the future"
**Wrong framing.** The real debate is **RAG vs long context** (Karpathy's LLM Wiki concept — structured second-brain that lets you skip RAG with long context windows).

### Open source vs proprietary models
**Complicated.** Open source (Qwen, Gemma 4) catching up fast → will cover ~80% of use cases. Frontier closed-source models still needed for ~20% (state-of-the-art complex reasoning).

### Treating agents like employees (not magic boxes)

Two failure modes when setting up an agent:
1. **Too little context** — generic answers, agent doesn't know anything about you
2. **Context explosion** — dump 100 files, agent drowns and can't prioritize

**Fix**: Onboard like an intern. Tell them who you are, what you need. Start simple. Build up. **Let the agent interview you** — ask follow-up questions to learn about you.

Shubham's "Monica" pattern: agent built a `soul.md` (personality file) and `user.md` (user context file) by interviewing him over time. Agents are smart enough to structure their own memory if you communicate well.

### Soft skills > technical skills for agent builders

*"Communication, understanding the problem, user empathy — these are becoming really really important because the technical part is either being solved or getting solved."*

---

## Key Moments

| Time | Content |
|------|---------|
| 00:12 | Intro: Shubham Saboo, creator of awesome-llm-apps (105K stars) |
| 08:07 | agents-cli explained: CLI + skills package for coding agents |
| 09:55 | Demo 1 starts: caveman compressor build |
| 12:30 | ADK web UI launched locally from terminal |
| 13:07 | Deployment options walkthrough (Agent Engine / Cloud Run / GKE) |
| 14:40 | Deploy to Agent Engine triggered with approval prompt |
| 16:04 | ADK web UI demo — events panel, states, artifacts visible |
| 17:33 | Eval generation: 20 criteria generated + run by coding agent |
| 21:11 | Evals all passing; tool addition demo (google_search) |
| 23:16 | Demo 2: multi-agent PR roaster introduced |
| 25:31 | PR roaster code walkthrough (code analyst + roast master + image gen) |
| 26:49 | Live PR roast — 9.2/10 score + meme generated |
| 29:52 | ADK 2.0 features intro (Google Cloud Next announcements) |
| 30:33 | Graph-based agent workflows explained |
| 32:30 | Agent Runtime changes: ambient agents + resume agents |
| 33:14 | Resume agents: `is_resumable=True` flag |
| 34:14 | Ambient agents: event-triggered, cron, pub/sub |
| 36:24 | Multi-language ADK: Python, TypeScript, Go, Java |
| 37:47 | Open ecosystem of tools and plugins |
| 38:43 | Shubham's 6-agent Open Claude team running 24/7 |
| 41:06 | Agent onboarding philosophy: not too little, not too much context |
| 42:01 | "Let the agent interview you" + soul file / user.md pattern |
| 45:56 | Rapid fire: RAG vs long context, simplest architecture wins |

---

## Hackathon Relevance

| Insight | Application |
|---------|------------|
| agents-cli builds 99% of agent patterns in one shot | Use for all scaffolding — don't write ADK code from scratch |
| Graph-based workflows for reliable multi-agent pipelines | Use `SequentialAgent`/`LoopAgent` for deterministic steps in [[projects/arch-social-agent]] |
| Ambient agents + cron triggers | Automate the social media pipeline to run daily without manual prompts |
| Gemini image model ("nanobanana" = `gemini-flash-image-preview`) | Already using this in [[projects/arch-social-agent]] — confirmed correct pattern |
| Simplest architecture wins | Don't over-engineer; one pipeline, clear agents, clean state handoff |
| Eval-first mindset | Generate evals early, ask coding agent to run them, catch regressions fast |

---

## Related Notes

- [[concepts/adk]] — ADK core concepts and agent types
- [[configs/agents-cli-setup]] — Setup, auth, Windows gotchas, .env template
- [[configs/run-agent-locally]] — How to run agents locally (adk web, test scripts)
- [[resources/day 1/Introducing Agents CLI in Agent Platform/notes]] — Earlier agents-cli intro video
- [[projects/arch-social-agent]] — Our multi-agent pipeline (validated against this episode)
