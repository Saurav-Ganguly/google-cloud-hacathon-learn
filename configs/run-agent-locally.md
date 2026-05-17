# Run an agents-cli Agent Locally — Definitive Runbook (Windows)

> Read this before running any agents-cli/ADK agent locally in this repo.
> It encodes every Windows fix found so far. Deviating reintroduces solved errors.
> Companion to [[configs/agents-cli-setup]] (scaffold/auth/.env).

## Prerequisites (once per project)

The project must already have:
- A `.env` in the project root (see [[configs/agents-cli-setup]] for exact contents).
- Deps installed: `PYTHONUTF8=1 agents-cli install` run from the project root.
- ADC auth done on the machine (see [[configs/agents-cli-setup]]).

`PYTHONUTF8=1` is mandatory on every agents-cli / `uv run` command on Windows.
Without it the Windows console (cp1252) cannot encode the emoji/checkmark these
tools print, and the process dies — sometimes before doing any real work.

---

## Option A — Single-prompt test script (fastest, most reliable)

Best for quick checks and CI-style verification. Single-turn, no memory between runs.

Each project gets a `test_agent.py` in its root (the `architect-finder` copy is the
reference). It uses ADK's `InMemoryRunner` directly, bypassing the CLI entirely.

```powershell
cd <project-root>
$env:PYTHONUTF8=1
uv run python test_agent.py "your prompt here"
```

Why this exists: `agents-cli run` crashes on Windows (emoji in its output). The
direct-runner script sidesteps the CLI. This is the workhorse for iteration.

---

## Option B — Interactive web UI (multi-turn chat)

Best for testing back-and-forth (e.g. agent asks for a location, you reply).

**Do NOT use `agents-cli playground`.** On agents-cli v0.1.3 it shells out to
`uv run adk web . --host 127.0.0.1 --port 8080`, and that argument form errors
out with an `adk web` usage error — the server never starts. Root-caused
2026-05-17 on `architect-finder`.

**Use `adk web` directly instead:**

```powershell
cd <project-root>
$env:PYTHONUTF8=1
uv run adk web . --port 8080
```

Then open: **http://127.0.0.1:8080**

- The `.` is `AGENTS_DIR` — the project root, whose `app/` subdir is the agent
  package (contains `agent.py` with `root_agent`).
- In the browser, pick the agent (`app`) from the top-left dropdown, then chat.
- `/` returns HTTP 307 → redirects to `/dev-ui/?app=app`. That is normal.
- Stop with `Ctrl+C` in the terminal.

### `ERR_CONNECTION_REFUSED` in the browser

The server is not running. Causes, in order of likelihood:
1. The command exited (a foreground run with a timeout, or you closed the terminal).
   `adk web` is a long-running server — it must stay running in its terminal the
   whole time you use the UI.
2. You ran it from the wrong directory — must be the project root (the one with
   `pyproject.toml`), or `adk web` errors with "No pyproject.toml found".
3. The browser cached the failed page — hard-refresh after the server is up.

Verify the server is actually listening before debugging the browser:

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8080/
```

`307` (or `200`) = server is up, the problem is the browser. No response /
connection refused = the server is down, restart it.

---

## Notes / harmless noise

- `warning: VIRTUAL_ENV=...caveman-compress\.venv does not match ...` — harmless.
  `uv` ignores the stale env var and uses the project's own `.venv`.
- `[EXPERIMENTAL] InMemoryCredentialService` / `BaseCredentialService` warnings
  on `adk web` startup — harmless, expected.

---

## Verified Working

| Project | Date | What worked |
|---------|------|-------------|
| `architect-finder` | 2026-05-17 | Option A (`test_agent.py`) and Option B (`adk web . --port 8080`) both verified. `agents-cli playground` confirmed broken on v0.1.3. |
