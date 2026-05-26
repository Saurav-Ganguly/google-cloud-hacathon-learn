"""Research band — prompt_builder + split_prompts + 4 agents + join.

Graph region:

    parse_router --OK--> prompt_builder --> split_prompts ----> market_research ---+
                                                            \\-> tech_feasibility --+--> join_node --> scoring
                                                            \\-> competitor_landscape -+
                                                            \\-> devils_advocate ----+

Concepts exercised:
  - Gemini Agent with BuiltInPlanner + output_schema           -> prompt_builder
  - FunctionNode unpacking a Pydantic output to state keys     -> split_prompts
  - Parallel fan-out (4 rows from split_prompts)               -> agent.py edges
  - Agent nodes with google_search tool, NO output_schema      -> 3 research agents
  - LiteLlm + deepseek agent in a graph                        -> devils_advocate
  - JoinNode collecting 4 upstream branches                    -> join_node

Hard ADK constraint: output_schema disables tools. The 3 google_search
agents therefore have no output_schema and emit free text. Each agent
writes its result to state under its own `output_key`, so the downstream
`scoring` agent can read the four texts via `{simple_key}` templating.

Reference: concepts/adk-graph-workflows.md (per-node schemas + parallel + join).
"""

from __future__ import annotations

from google.adk import Event
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.adk.workflow import FunctionNode, JoinNode
from google.genai import types

from .nodes_input import DEEPSEEK_LABEL, DEEPSEEK_MODEL
from .prompts import (
    COMPETITOR_LANDSCAPE_INSTRUCTION,
    DEVILS_ADVOCATE_INSTRUCTION,
    MARKET_RESEARCH_INSTRUCTION,
    PROMPT_BUILDER_INSTRUCTION,
    TECH_FEASIBILITY_INSTRUCTION,
)
from .schemas import ResearchPrompts
from .tracing import emit_enter, emit_exit, make_after, make_before


GEMINI_MODEL = "gemini-flash-latest"


# -----------------------------------------------------------------------------
# NODE — prompt_builder
# -----------------------------------------------------------------------------
# Reads state.idea (seeded by parse_router on the OK route), uses Gemini +
# BuiltInPlanner to think about the idea, then emits 4 targeted research
# prompts as a single ResearchPrompts JSON blob.
#
# BuiltInPlanner + output_schema co-exist (thinking is a separate channel
# from the visible response). Pattern lives in test/LlmDebator/agent.py
# judge_agent.
# -----------------------------------------------------------------------------
prompt_builder = LlmAgent(
    name="prompt_builder",
    model=GEMINI_MODEL,
    description="Splits the idea into 4 targeted research prompts.",
    instruction=PROMPT_BUILDER_INSTRUCTION,
    output_schema=ResearchPrompts,
    output_key="research_prompts",
    mode="single_turn",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        ),
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
    before_agent_callback=make_before("prompt_builder", GEMINI_MODEL),
    after_agent_callback=make_after("prompt_builder", GEMINI_MODEL, "research_prompts"),
)


# -----------------------------------------------------------------------------
# NODE — split_prompts (FunctionNode)
# -----------------------------------------------------------------------------
# Unpacks prompt_builder's ResearchPrompts output into individual state keys
# so each research agent can template just its own prompt via {market_prompt}
# etc. instead of having to parse a full JSON blob from a single state key.
#
# Pass-through output (the ResearchPrompts itself) so downstream nodes still
# get the typed payload as node_input if they want it; they mostly ignore it.
# -----------------------------------------------------------------------------
def _split_prompts(node_input: ResearchPrompts):
    yield emit_enter("split_prompts", "unpacking ResearchPrompts -> state keys")
    seed = {
        "idea": node_input.idea,
        "market_prompt": node_input.market_prompt,
        "tech_prompt": node_input.tech_prompt,
        "competitor_prompt": node_input.competitor_prompt,
        "devils_advocate_prompt": node_input.devils_advocate_prompt,
    }
    yield emit_exit("split_prompts", f"wrote {len(seed)} state keys")
    yield Event(output=node_input, state=seed)


split_prompts = FunctionNode(func=_split_prompts, name="split_prompts")


# -----------------------------------------------------------------------------
# NODES — 4 parallel research agents
# -----------------------------------------------------------------------------
# Each templates its own prompt from state (set by split_prompts above) and
# emits free text. The three with google_search must NOT have output_schema
# (tools and output_schema are mutually exclusive). devils_advocate uses
# LiteLlm deepseek with pure reasoning — kept symmetric (no schema, free text)
# for consistency at the join.
#
# Each writes to its own output_key in state so the downstream `scoring`
# agent can read all four via simple `{key}` templating.
# -----------------------------------------------------------------------------

market_research = LlmAgent(
    name="market_research",
    model=GEMINI_MODEL,
    description="Web-grounded market sizing + customer analysis.",
    instruction=MARKET_RESEARCH_INSTRUCTION,
    tools=[google_search],
    output_key="market_text",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    before_agent_callback=make_before("market_research", GEMINI_MODEL),
    after_agent_callback=make_after("market_research", GEMINI_MODEL, "market_text"),
)


tech_feasibility = LlmAgent(
    name="technical_feasibility",
    model=GEMINI_MODEL,
    description="Web-grounded technical feasibility review.",
    instruction=TECH_FEASIBILITY_INSTRUCTION,
    tools=[google_search],
    output_key="tech_text",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    before_agent_callback=make_before("technical_feasibility", GEMINI_MODEL),
    after_agent_callback=make_after("technical_feasibility", GEMINI_MODEL, "tech_text"),
)


competitor_landscape = LlmAgent(
    name="competitor_landscape",
    model=GEMINI_MODEL,
    description="Web-grounded competitor / adjacent-solution scan.",
    instruction=COMPETITOR_LANDSCAPE_INSTRUCTION,
    tools=[google_search],
    output_key="competitor_text",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    before_agent_callback=make_before("competitor_landscape", GEMINI_MODEL),
    after_agent_callback=make_after("competitor_landscape", GEMINI_MODEL, "competitor_text"),
)


devils_advocate = LlmAgent(
    name="devils_advocate",
    model=LiteLlm(
        model=DEEPSEEK_MODEL,
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Pure-reasoning critique of the idea (no web search).",
    instruction=DEVILS_ADVOCATE_INSTRUCTION,
    output_key="devils_text",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
    before_agent_callback=make_before("devils_advocate", DEEPSEEK_LABEL),
    after_agent_callback=make_after("devils_advocate", DEEPSEEK_LABEL, "devils_text"),
)


# -----------------------------------------------------------------------------
# NODE — join_node (JoinNode)
# -----------------------------------------------------------------------------
# Waits for all 4 research agents to emit, then passes the aggregated dict to
# the downstream `scoring` agent. Scoring ignores the dict (reads everything
# from state) but the JoinNode serves as the parallel-branch synchronisation
# point. The 4 texts are already in state under their output_keys by this
# point, so scoring's `{market_text}` etc. templating works.
# -----------------------------------------------------------------------------
join_node = JoinNode(name="collect_research")
