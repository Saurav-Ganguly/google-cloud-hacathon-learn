# Google Cloud Rapid Agent Hackathon — Knowledge Base

## What This Is

This is an Obsidian vault and learning base for the Google Cloud Rapid Agent Hackathon (deadline: Jun 11, 2026 @ 5PM EDT). Dual purpose:
1. Learn agent development deeply (ADK, MCP, A2A, Vertex AI)
2. Build something good enough to win ($60,000 prize pool)

**Entry point**: always start from `index.md` — it is the Map of Content for everything.

**GitHub**: https://github.com/Saurav-Ganguly/google-cloud-hacathon-learn

---

## Folder Structure

```
google_cloud_hacathon/
├── index.md                  ← MOC — start here
├── concepts/                 ← One note per core technical concept
│   ├── vertex-ai.md          ← Gemini Agent Platform (Build/Scale/Govern/Optimize)
│   ├── adk.md                ← Agent Development Kit (adk.dev)
│   ├── mcp.md                ← Model Context Protocol
│   ├── a2a.md                ← Agent-to-Agent protocol
│   └── agent-runtime.md      ← Managed PaaS (<1s cold start, 7-day sessions)
├── partners/                 ← One note per partner MCP track
│   ├── elastic.md
│   ├── mongodb.md
│   ├── gitlab.md
│   ├── fivetran.md
│   ├── arize.md
│   └── dynatrace.md
├── hackathon/                ← Hackathon-specific context
│   ├── overview.md           ← Prizes, judging criteria, what to build
│   ├── rules.md              ← Eligibility, submission requirements
│   ├── resources.md          ← Starter kits, APIs, Google Cloud credits
│   └── links.md              ← Quick links: devpost, ADK, partner resources
├── ideas/                    ← Project ideas (one file per idea)
├── projects/                 ← Active builds
├── resources/                ← Ingested content (videos, docs)
│   └── day 1/
│       └── What is Gemini Enterprise Agent Platform/
│           └── notes.md
└── tools/
    └── watch_yt.py           ← Video download + frame extraction script
```

---

## Skills Available

Two Claude Code skills handle all ingestion:

**`/watch-a-yt-video <url>`** — Process a YouTube video:
- Downloads video + transcript with yt-dlp
- Extracts frames every 5s with ffmpeg
- Analyzes frames + transcript using Claude's Read tool (no API key needed)
- Creates `resources/{day N}/{title}/notes.md` with dynamic `[[wiki-links]]`
- Updates `index.md` automatically
- Commits to git

**`/parse-my-resources`** — Link manually-added notes:
- Scans vault for `.md` files not yet in `index.md`
- Adds `[[wiki-links]]` to related concepts/partners
- Updates the right section of `index.md`
- Commits to git

---

## Conventions

### Wiki-links
Always use Obsidian `[[wiki-link]]` syntax for internal links. Path-aware:
- `[[concepts/adk]]` not `[[adk]]`
- `[[partners/elastic]]` not `[[elastic]]`
- `[[hackathon/overview]]` not `[[overview]]`
- `[[index]]` for the MOC

### index.md is the source of truth
Every new note must be linked from `index.md`. Skills do this automatically. For manually-created notes, run `/parse-my-resources` or add the line yourself.

### Git commits
One commit per resource added. Message format:
- `resource: add notes for '{video title}'`
- `knowledge: link new resources to graph`
- `idea: add {idea name}`
- `concept: expand {concept name}`

### Video files are gitignored
Raw video files (`*.mp4`, `*.webm`, `*.mkv`, `*.avi`, `*.mov`, `*.wmv`, `*.flv`, `*.m4v`) under `resources/` are never committed.

---

## Hackathon Requirements (must satisfy to win)

1. Use **Gemini** as the AI model
2. Use **Google Cloud Agent Builder** (Vertex AI Agent Platform)
3. Integrate at least one **partner MCP server** (elastic, mongodb, gitlab, fivetran, arize, or dynatrace)
4. Submit on **Devpost** by Jun 11, 2026 @ 5PM EDT

---

## When Helping with This Project

- Read `index.md` first to understand current knowledge state
- When creating notes, add `[[wiki-links]]` to related concepts and partners
- When expanding concept stubs, pull facts from ingested resources — don't make things up
- Partner notes should track: what the MCP server does, what data it exposes, project ideas that could use it
- Idea notes go in `ideas/` and should link to relevant `[[concepts/]]` and `[[partners/]]`
- Keep notes concise — this is a navigable graph, not a dump
