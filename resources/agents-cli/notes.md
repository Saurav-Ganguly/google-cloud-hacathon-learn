# agents-cli — Reference Notes

**Repo**: https://github.com/google/agents-cli
**PyPI**: https://pypi.org/project/google-agents-cli/
**Docs**: https://google.github.io/agents-cli/
**Version installed**: v0.1.3 (2026-05-16)

> The CLI and skills that turn any coding assistant into an expert at creating, evaluating, and deploying AI agents on Google Cloud.

---

## What It Is

`agents-cli` is a tool **for** coding agents (Claude Code, Gemini CLI, Codex, etc.) — not a coding agent itself. It provides:
- CLI commands for scaffolding, eval, and deployment
- Skills that teach your coding agent the full ADK development lifecycle

Works on top of [[concepts/adk]] and targets [[concepts/agent-runtime]] / Cloud Run for deployment.

---

## Installation

**Prerequisites**: Python 3.11+, `uv`, Node.js

```bash
# Install CLI + skills (use UTF-8 flag on Windows to avoid encoding error)
PYTHONUTF8=1 uvx google-agents-cli setup --skip-auth

# After gcloud is installed, authenticate:
gcloud auth application-default login
gcloud auth application-default set-quota-project [PROJECT_ID]

# Then re-run setup to complete auth step:
PYTHONUTF8=1 uvx google-agents-cli setup
```

**Windows note**: Always prefix with `PYTHONUTF8=1` — the logo uses Unicode that Windows cp1252 can't encode.

---

## Skills Installed

All 7 skills are installed globally and available in Claude Code:

| Skill | What it teaches Claude Code |
|---|---|
| `google-agents-cli-workflow` | Dev lifecycle, code preservation, model selection |
| `google-agents-cli-adk-code` | ADK Python API — agents, tools, orchestration, callbacks, state |
| `google-agents-cli-scaffold` | Project scaffolding — `create`, `enhance`, `upgrade` |
| `google-agents-cli-eval` | Evaluation — metrics, evalsets, LLM-as-judge, trajectory scoring |
| `google-agents-cli-deploy` | Deployment — Agent Runtime, Cloud Run, GKE, CI/CD, secrets |
| `google-agents-cli-publish` | Gemini Enterprise registration |
| `google-agents-cli-observability` | Cloud Trace, logging, third-party integrations |

---

## Key Commands

```bash
agents-cli scaffold <name>          # Create new agent project
agents-cli scaffold enhance         # Add deployment/CI/CD to existing project
agents-cli install                  # Install project dependencies
agents-cli run "prompt"             # Run agent with a single prompt
agents-cli eval run                 # Run evaluations
agents-cli deploy                   # Deploy to Google Cloud
agents-cli login --status           # Check auth status
agents-cli info                     # Show project config + CLI version
```

---

## Auth Status (as of 2026-05-16)

- CLI installed: yes (v0.1.3)
- Skills installed: yes (all 7, global)
- gcloud CLI: installing
- ADC configured: pending (needs gcloud installed first)

---

## Local Dev Without gcloud

For `scaffold`, `run`, and `eval` — no gcloud needed. Use AI Studio API key:
- Get key: https://aistudio.google.com/apikey
- Set `GOOGLE_API_KEY` in `.env`
- ADK will use it automatically

For `deploy` — gcloud + ADC required.

---

## Related

- [[concepts/adk]] — The agent framework agents-cli builds on
- [[concepts/agent-runtime]] — Managed deployment target
- [[concepts/vertex-ai]] — Platform overview
- [[resources/agent-platform-onboard/notes]] — QS3 is the full agents-cli path
