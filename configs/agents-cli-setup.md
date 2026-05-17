# agents-cli Project Setup — Working Configuration

> Read this before scaffolding or running any agents-cli project in this repo.

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

ADK loads `.env` automatically **locally only** — it walks up from the agent directory to find one. The `.env` is NOT shipped to a deployed container; any deploy must pass these same vars to the runtime environment explicitly.

---

## Windows Gotchas

### Running an agent locally

For the full local-run runbook (test script, `adk web`, why `agents-cli playground`
is broken on v0.1.3), see **[[configs/run-agent-locally]]** (`configs/run-agent-locally.md`).
Short version of the crash below.

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

## Scaffold Command

```bash
PYTHONUTF8=1 agents-cli scaffold create <project-name> --agent adk --prototype --agent-guidance-filename CLAUDE.md
```

**Always prefix with `PYTHONUTF8=1`.** Without it the scaffold crashes on Windows
on the very first emoji/checkmark print — which happens during *GCP credential
verification, before any files are written*, so the project is never created (not
a cosmetic end-of-run crash). `PYTHONUTF8=1` forces UTF-8 stdout so every emoji
print succeeds and the scaffold completes with exit 0. Verified 2026-05-17 on the
`architect-finder` project. Apply the same prefix to `agents-cli install` and any
`uv run python` test scripts.

---

## Verified Working Projects

| Project | Date | Notes |
|---------|------|-------|
| `caveman-compress` | 2026-05-17 | Deployed & verified on Cloud Run (public), evals 3/3 — service since deleted to stop billing. Local code remains as the reference QS3 walkthrough. |
