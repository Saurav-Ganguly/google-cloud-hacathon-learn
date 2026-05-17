# arch-social-agent

**Status**: Working prototype — needs partner MCP to be hackathon-eligible  
**Location**: `arch-social-agent/` (sibling to `architect-finder`, `caveman-compress`)  
**Built**: 2026-05-17

---

## What It Does

A 3-agent sequential pipeline that turns architectural news into a LinkedIn-ready post + AI-generated image, fully automated.

**Pipeline:**
1. **ResearchAgent** — searches the web via `google_search` for top 3 architectural news stories from the past week
2. **StrategyAgent** — picks the best story, writes a 150-200 word LinkedIn post, and crafts a detailed image generation prompt (structured output via Pydantic)
3. **ImageAgent** — calls `gemini-3.1-flash-image-preview` with the image prompt, saves PNG to `output/`

---

## Tech Stack

- [[concepts/adk]] `SequentialAgent` for deterministic pipeline orchestration
- `google_search` built-in ADK tool for live web grounding
- `gemini-flash-latest` for research + strategy agents
- `gemini-3.1-flash-image-preview` for image generation
- Vertex AI (`absolute-bloom-462810-i9`, location `global`)

---

## Run Locally

```powershell
cd arch-social-agent
$env:PYTHONUTF8=1
uv run python test_agent.py          # single-turn test
uv run adk web . --port 8080         # interactive web UI
```

Open http://127.0.0.1:8080, select `app`, send: `Run the architecture social media pipeline`

---

## What's Missing for Hackathon

Must integrate at least one partner MCP server. Candidates:

| Partner | Fit |
|---------|-----|
| [[partners/elastic]] | Index + search architectural articles |
| [[partners/arize]] | Trace and evaluate pipeline quality |
| [[partners/mongodb]] | Store generated posts + images |

---

## File Structure

```
arch-social-agent/
├── app/
│   ├── agent.py      ← SequentialAgent + 3 sub-agents (factories)
│   └── tools.py      ← generate_image custom tool
├── output/           ← generated PNGs (gitignored)
└── test_agent.py     ← InMemoryRunner test script
```
