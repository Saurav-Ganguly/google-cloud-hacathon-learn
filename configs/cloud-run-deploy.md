# Cloud Run Deploy — Definitive Runbook (Windows)

> Canonical, copy-paste deploy procedure for any agents-cli/ADK project in this repo.
> This block encodes **every** fix from the 2026-05-17 caveman-compress deploy. Copy it verbatim — deviating reintroduces solved errors. See [[configs/agents-cli-setup]] for project/auth/.env setup.

> **Do NOT use `agents-cli deploy`** on Windows — it is broken (calls `gcloud` via `subprocess.Popen` without `shell=True`, can't resolve `gcloud.cmd` → `FileNotFoundError`). Use this instead.

Replace `<name>` with the project/service name (e.g. `caveman-compress`); run from the project root.

```powershell
$gcloud = "C:\Users\Hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$env:CLOUDSDK_PYTHON = (& $gcloud components copy-bundled-python 2>&1 | Select-Object -Last 1)
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"

# 1. Deploy. Vertex env vars are baked in here so the container never falls
#    back to the Gemini Developer API. Region MUST be us-east1.
& $gcloud beta run deploy <name> `
  --project absolute-bloom-462810-i9 --region us-east1 --source . `
  --memory 4Gi --no-cpu-throttling --quiet `
  --update-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=absolute-bloom-462810-i9,GOOGLE_CLOUD_LOCATION=global,AGENT_VERSION=0.1.0"

# 2. Make it browser-reachable (skip if it should stay private).
& $gcloud run services add-iam-policy-binding <name> `
  --project absolute-bloom-462810-i9 --region us-east1 `
  --member="allUsers" --role="roles/run.invoker" --quiet
```

Then test in browser at `<service-url>/dev-ui/?app=app`, or end-to-end:

```powershell
$base = "<service-url>"
Invoke-RestMethod -Uri "$base/apps/app/users/u1/sessions/s1" -Method Post -ContentType "application/json" -Body "{}"
$body = @{ app_name="app"; user_id="u1"; session_id="s1"; new_message=@{ role="user"; parts=@(@{ text="verbose text here" }) } } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "$base/run" -Method Post -ContentType "application/json" -Body $body
```

**Every fix is already in the block above — do not deviate.** Why each line is there:

| Line | Prevents |
|------|----------|
| Full `$gcloud` path, not bare `gcloud` | gcloud not in Claude Code PATH; `agents-cli deploy` `subprocess.Popen` can't resolve `.cmd` → `FileNotFoundError` |
| `CLOUDSDK_PYTHON` via `copy-bundled-python` | `gcloud beta` + non-interactive refusing to self-update |
| `PYTHONIOENCODING`/`PYTHONUTF8` | cp1252 emoji crash in agents-cli/gcloud output on Windows |
| `--region us-east1` | Cloud Run rejects `global` (that's only the Vertex AI model endpoint) |
| `GOOGLE_GENAI_USE_VERTEXAI=1` + project + location in `--update-env-vars` | local `.env` is NOT shipped to the container → "No API key was provided" |
| `add-iam-policy-binding allUsers` | `--no-allow-unauthenticated` default → 403 Forbidden in browser |

The default Cloud Run runtime service account already has Vertex AI access — no extra IAM needed.

---

## Verified Deploys

| Project | Date | URL |
|---------|------|-----|
| `caveman-compress` | 2026-05-17 | https://caveman-compress-1035233687590.us-east1.run.app (public, verified) |
