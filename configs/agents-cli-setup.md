# agents-cli Project Setup — Working Configuration

> Read this before scaffolding, running, or deploying any agents-cli project in this repo.
> **Deploying to Cloud Run? Go straight to the "Cloud Run Deploy — Definitive Runbook" section below and copy the block verbatim.** It already encodes every fix; deviating reintroduces solved errors.

## GCP Project

| Field | Value |
|-------|-------|
| Project ID | `absolute-bloom-462810-i9` |
| Project name | "My First Project" |
| Why this one | Agent Platform API is enabled here |

**Do NOT use** `gen-lang-client-0842989663` ("Gemini API") — it does not have Agent Platform API enabled and will 403.

---

## Auth Setup (one-time, per machine)

Both commands are required. They are independent — doing one does not do the other.

```bash
# 1. CLI auth (for gcloud commands)
gcloud auth login

# 2. ADC auth (for SDK/ADK code — this is what agents actually use)
gcloud auth application-default login
gcloud auth application-default set-quota-project absolute-bloom-462810-i9
```

ADC credentials are stored at:
`C:\Users\Hp\AppData\Roaming\gcloud\application_default_credentials.json`

---

## .env File — Required for Every New Project

Create a `.env` in the project root (e.g., `caveman-compress/.env`):

```env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=absolute-bloom-462810-i9
GOOGLE_CLOUD_LOCATION=global
```

**Critical**: use `global` for `GOOGLE_CLOUD_LOCATION`, not `us-central1` or `us-east1`.
`gemini-flash-latest` and other latest-alias models are only available via the `global` endpoint in Vertex AI.

ADK loads `.env` automatically **locally only** — it walks up from the agent directory to find one. The `.env` is NOT shipped to Cloud Run; deploys must pass these same vars via `--update-env-vars` (the runbook below does this).

---

## Windows Gotchas

### agents-cli run times out / crashes

`agents-cli run` on Windows crashes due to emoji in its output (`✅`) which cp1252 (Windows console) cannot encode. The server may actually start, but the CLI process dies before reporting ready.

**Workaround — test the agent directly:**

```python
import asyncio
from dotenv import load_dotenv
load_dotenv('.env')

from google.adk.runners import InMemoryRunner
from google.genai import types
from app.agent import root_agent

async def run(prompt):
    runner = InMemoryRunner(agent=root_agent, app_name='your-app-name')
    session = await runner.session_service.create_session(app_name='your-app-name', user_id='test')
    content = types.Content(role='user', parts=[types.Part(text=prompt)])
    async for event in runner.run_async(user_id='test', session_id=session.id, new_message=content):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    print(part.text)

asyncio.run(run('your test prompt'))
```

Run it with: `uv run python test_agent.py`

### gcloud not in PATH for Claude Code sessions

`gcloud` is only in the User PATH. PowerShell sessions spawned by Claude Code don't inherit it.

**Workaround**: use the full path:
```powershell
& "C:\Users\Hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" projects list
```

---

## Cloud Run Deploy

Deploying to Cloud Run? Use the canonical copy-paste runbook: **[[configs/cloud-run-deploy]]** (`configs/cloud-run-deploy.md`). It encodes every Windows fix in a single block — do not improvise a deploy.

---

## Scaffold Command

```bash
agents-cli scaffold create <project-name> --agent adk --prototype --agent-guidance-filename CLAUDE.md
```

The scaffold may crash at the end on Windows (emoji in success message) — that is cosmetic. Check if the directory was created; if yes, the scaffold succeeded.

---

## Verified Working Projects

| Project | Date | Notes |
|---------|------|-------|
| `caveman-compress` | 2026-05-17 | Deployed & verified on Cloud Run (public), evals 3/3 — service since deleted to stop billing. Local code remains as the reference QS3 walkthrough. |
