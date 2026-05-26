"""Root assembly — wires every node into the full Idea Refiner Workflow.

Keep this file thin: imports + the `root_agent = Workflow(edges=[...])`
declaration. The shape of the graph should be readable end-to-end without
scrolling.

Reference: concepts/adk-graph-workflows.md (Edge syntax section).
Plan:      C:/Users/Hp/.claude/plans/luminous-stirring-swing.md

`root_agent` is the magic name adk web looks up in this module.
"""

from __future__ import annotations

from google.adk import Workflow

from .nodes_input import idea_parser, parse_router, request_idea
from .nodes_output import reject, report_writer
from .nodes_research import (
    competitor_landscape,
    devils_advocate,
    join_node,
    market_research,
    prompt_builder,
    split_prompts,
    tech_feasibility,
)
from .nodes_scoring import refiner, refresh, score_router, scoring


# -----------------------------------------------------------------------------
# ROOT — Workflow graph (full assembly)
# -----------------------------------------------------------------------------
# Bands, top to bottom:
#   1. input    : idea_parser -> parse_router  (with NEED_IDEA->HITL cycle)
#   2. research : prompt_builder -> split_prompts -> 4 parallel -> join_node
#   3. scoring  : scoring -> score_router  (with REFINE -> refiner -> refresh
#                  -> scoring cycle, max 3 iterations)
#   4. output   : reject (leaf) and report_writer (leaf)
#
# Cycles in this graph (both conditional, both accepted by the validator):
#   - request_idea -> idea_parser  (gated by parse_router's NEED_IDEA edge)
#   - refresh      -> scoring      (gated by score_router's REFINE edge)
# -----------------------------------------------------------------------------
root_agent = Workflow(
    name="idea_refiner",
    description=(
        "Business-idea validator: parses input, runs 4-way parallel research, "
        "scores on 5 dimensions, refines up to 3 times, emits a markdown "
        "report. HITL re-prompt on bad input. Conditional cycles for "
        "re-prompt + refinement."
    ),
    edges=[
        # ---- INPUT BAND ----
        ("START", idea_parser, parse_router),
        (parse_router, {
            "OK":        prompt_builder,
            "NEED_IDEA": request_idea,
        }),
        (request_idea, idea_parser),                # cycle (conditional via parse_router)

        # ---- RESEARCH BAND ----
        (prompt_builder, split_prompts),
        (split_prompts, market_research, join_node),
        (split_prompts, tech_feasibility, join_node),
        (split_prompts, competitor_landscape, join_node),
        (split_prompts, devils_advocate, join_node),

        # ---- SCORING BAND ----
        (join_node, scoring, score_router),
        (score_router, {
            "REJECT":  reject,
            "REFINE":  refiner,
            "APPROVE": report_writer,
        }),
        (refiner, refresh, scoring),                # cycle (conditional via score_router)
    ],
)
