"""Scoring band — scoring + score_router + refiner + refresh.

Graph region:

    join_node --> scoring --> score_router --REJECT---->          reject
                                          \\--REFINE---->  refiner --> refresh --> scoring (cycle)
                                          \\--APPROVE---->          report_writer
                                          \\--APPROVE_MARGINAL---> report_writer

Concepts exercised:
  - LlmAgent with output_schema + planner                   -> scoring
  - FunctionNode reading state to route                     -> score_router
  - Event(state=...) writing tiny scalars                   -> refresh (counter)
  - Conditional cycle (REFINE edge satisfies the rule)      -> refiner -> refresh -> scoring

The refinement loop avoids re-running the 4 paid Google searches: refresh
only updates `state.idea` (to the new refined version) and bumps
`state.refinement_attempts`. Scoring re-runs against the SAME cached
research texts (state.market_text etc.) but with the new idea.

Reference: concepts/adk-graph-workflows.md (Event.state for tiny scalars).
"""

from __future__ import annotations

from google.adk import Event
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.adk.workflow import FunctionNode
from google.genai import types

from .prompts import REFINER_INSTRUCTION, SCORING_INSTRUCTION
from .schemas import RefinedIdea, Score
from .tracing import emit_enter, emit_exit, emit_info, make_after, make_before


GEMINI_MODEL = "gemini-flash-latest"


# -----------------------------------------------------------------------------
# NODE — scoring
# -----------------------------------------------------------------------------
# Reads idea + 4 research texts from state via {key} templating, picks 5
# scoring dimensions, gives each 1-10, rolls up to an average, and emits a
# Score JSON.
#
# Gemini + BuiltInPlanner + output_schema co-exist; pattern lives in
# test/LlmDebator/agent.py judge_agent.
# -----------------------------------------------------------------------------
scoring = LlmAgent(
    name="scoring",
    model=GEMINI_MODEL,
    description="Scores the idea on 5 dimensions, averaged to a /10 score.",
    instruction=SCORING_INSTRUCTION,
    output_schema=Score,
    output_key="score",
    mode="single_turn",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        ),
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    before_agent_callback=make_before("scoring", GEMINI_MODEL),
    after_agent_callback=make_after("scoring", GEMINI_MODEL, "score"),
)


# -----------------------------------------------------------------------------
# NODE — score_router (FunctionNode)
# -----------------------------------------------------------------------------
# Reads the scoring agent's Score (passed as node_input) and the current
# refinement counter (from state.refinement_attempts), routes to REJECT /
# REFINE / APPROVE / APPROVE_MARGINAL, and writes state.marginal for the
# report_writer to template.
#
# Routing table (only 3 distinct routes; report_writer handles the marginal
# preamble itself by reading {marginal} from state — no separate route needed):
#   avg < 5                              -> REJECT
#   avg > 8                              -> APPROVE   (marginal=False)
#   5 <= avg <= 8 AND attempts < 3       -> REFINE
#   5 <= avg <= 8 AND attempts >= 3      -> APPROVE   (marginal=True)
# -----------------------------------------------------------------------------
def _score_router(node_input: Score, refinement_attempts: int = 0):
    avg = node_input.avg_out_of_10
    yield emit_enter(
        "score_router",
        f"avg={avg:.1f}/10 attempts={refinement_attempts}",
    )

    if avg < 5:
        route, marginal = "REJECT", False
    elif avg > 8:
        route, marginal = "APPROVE", False
    elif refinement_attempts >= 3:
        route, marginal = "APPROVE", True
    else:
        route, marginal = "REFINE", False

    yield emit_exit("score_router", f"route={route} marginal={marginal}")
    yield Event(
        route=route,
        output=node_input,
        state={"marginal": marginal},
    )


score_router = FunctionNode(func=_score_router, name="score_router")


# -----------------------------------------------------------------------------
# NODE — refiner
# -----------------------------------------------------------------------------
# Reads {idea} + {score} + {refinement_attempts} + the 4 research texts from
# state, proposes a refined idea that addresses the weakest scoring
# dimension. Outputs RefinedIdea JSON; the post-node `refresh` FunctionNode
# applies it to state.
# -----------------------------------------------------------------------------
refiner = LlmAgent(
    name="refiner",
    model=GEMINI_MODEL,
    description="Refines a mid-scoring idea (5-8/10) for the next round.",
    instruction=REFINER_INSTRUCTION,
    output_schema=RefinedIdea,
    output_key="refined_idea",
    mode="single_turn",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        ),
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
    before_agent_callback=make_before("refiner", GEMINI_MODEL),
    after_agent_callback=make_after("refiner", GEMINI_MODEL, "refined_idea"),
)


# -----------------------------------------------------------------------------
# NODE — refresh (FunctionNode)
# -----------------------------------------------------------------------------
# Bridges refiner -> scoring on the loop back-edge:
#   - reads the refiner's RefinedIdea (as node_input)
#   - overwrites state.idea with the new refined idea string
#   - increments state.refinement_attempts
#   - emits an Event whose output goes to scoring (scoring ignores it -
#     it reads from state)
#
# The cycle (refiner -> refresh -> scoring) is unconditional in this segment,
# but the cycle as a whole is conditional via the upstream `score_router`
# REFINE edge, so the workflow validator accepts it.
# -----------------------------------------------------------------------------
def _refresh(node_input: RefinedIdea, refinement_attempts: int = 0):
    new_attempts = refinement_attempts + 1
    yield emit_enter(
        "refresh",
        f"applying refined idea (attempt #{new_attempts})",
    )
    yield emit_info(
        "refresh",
        f"new idea: {node_input.new_idea[:80]}",
    )
    yield emit_exit("refresh", "looping back to scoring")
    yield Event(
        output=node_input,
        state={
            "idea": node_input.new_idea,
            "refinement_attempts": new_attempts,
        },
    )


refresh = FunctionNode(func=_refresh, name="refresh")
