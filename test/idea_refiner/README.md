# Idea Refiner — ADK Graph-Workflow Sandbox

A business-idea validator built as an ADK 2.0 `Workflow` graph. Exercises
every primitive documented in
[../../concepts/adk-graph-workflows.md](../../concepts/adk-graph-workflows.md):

- `FunctionNode`, `Agent` (`mode="single_turn"`), `JoinNode`, `RequestInput`
- Sequential / branching / parallel-fan-out / parallel-and-join edges
- **Two conditional cycles** (HITL re-prompt, refinement loop)
- `Event(output=...)`, `Event(message=...)`, `Event(state={...})`, `Event(route=...)`
- Per-agent `output_schema` + `output_key` for state-keyed handoffs
- `BuiltInPlanner` thinking on Gemini agents
- `LiteLlm` + deepseek for the two non-Gemini agents
- `google_search` tool on the 3 web-research agents

See the **plan** at `C:\Users\Hp\.claude\plans\luminous-stirring-swing.md` for
the design rationale.

## Graph at a glance

```
START
 -> idea_parser (LiteLlm deepseek)
 -> parse_router  -- NEED_IDEA -> request_idea -> idea_parser (cycle)
                  -- OK ------> prompt_builder (Gemini + planner)
 -> split_prompts (FunctionNode -> 4 state keys)
 -> [market_research | tech_feasibility | competitor_landscape | devils_advocate]  (parallel)
 -> join_node
 -> scoring (Gemini + planner)
 -> score_router -- REJECT -> reject
                 -- REFINE -> refiner -> refresh -> scoring (cycle, max 3)
                 -- APPROVE -> report_writer (marginal flag from state)
```

## Run it

Prereqs: `.env` in this directory (created from
[../../configs/agents-cli-setup.md](../../configs/agents-cli-setup.md));
ADC auth done once per machine.

```powershell
cd C:\Users\Hp\Desktop\code\google_cloud_hacathon\test\idea_refiner
$env:PYTHONUTF8=1
uv run adk web . --port 8080
```

Open <http://127.0.0.1:8080>, pick `idea_refiner` in the agent dropdown,
chat.

Try:

| Input | Expected path |
|---|---|
| `An AI tutor that adapts to a student's learning style` | OK -> research -> scoring -> APPROVE or REFINE |
| `asdfasdf` | NEED_IDEA -> request_idea -> cycle back |
| `Sell ice to people in Antarctica door-to-door` | REJECT |

The console (this terminal) shows `[node_name] ENTER/EXIT` traces for every
node, in parallel for the 4 research agents. The adk web event stream
shows the same lines as `message` events plus the full agent outputs.

## Module layout

| File | Region of the graph |
|---|---|
| `agent.py` | Workflow assembly + edges array |
| `schemas.py` | Pydantic models (ParseResult, ResearchPrompts, Score, RefinedIdea) |
| `prompts.py` | Long instruction strings, by node name |
| `tracing.py` | `emit_enter` / `emit_exit` + Agent before/after callbacks |
| `nodes_input.py` | idea_parser + parse_router + request_idea |
| `nodes_research.py` | prompt_builder + split_prompts + 4 agents + join_node |
| `nodes_scoring.py` | scoring + score_router + refiner + refresh |
| `nodes_output.py` | reject + report_writer |

## Cost note

Each happy-path run hits `google_search` 3 times (market / tech /
competitor) and runs ~7 LLM calls. The refinement loop multiplies the
scoring + refiner calls by up to 3. Keep an eye on quota when iterating.
