"""Input band — parser + parse_router + HITL re-prompt.

Graph region:

    START -> idea_parser -> parse_router --OK--------> prompt_builder
                                       \\
                                        --NEED_IDEA--> request_idea
                                                         |
                                                         v
                                                      idea_parser (cycle)

Concepts exercised:
  - LlmAgent node with output_schema + mode="single_turn"  -> idea_parser
  - LiteLlm wrapper around an OpenRouter model              -> idea_parser
  - FunctionNode emitting Event(route=...)                  -> parse_router
  - Branching edge dict in agent.py                         -> parse_router
  - RequestInput HITL (message + payload)                   -> request_idea
  - Conditional cycle (NEED_IDEA edge satisfies the rule)   -> request_idea

Reference: concepts/adk-graph-workflows.md (node types + edge syntax).
"""

from __future__ import annotations

from google.adk import Event
from google.adk.agents import LlmAgent
from google.adk.events import RequestInput
from google.adk.models.lite_llm import LiteLlm
from google.adk.workflow import FunctionNode
from google.genai import types

from .prompts import IDEA_PARSER_INSTRUCTION
from .schemas import ParseResult
from .tracing import emit_enter, emit_exit, make_after, make_before


# -----------------------------------------------------------------------------
# MODEL — LiteLlm + deepseek via OpenRouter
# -----------------------------------------------------------------------------
# Per user spec: classification is cheap; deepseek-v4-flash is plenty smart for
# "is this a business idea?". The reasoning-disable in extra_body prevents
# OpenRouter from leaking chain-of-thought into the JSON output (would break
# output_schema validation). Same pattern as test/LlmDebator/agent.py
# con_agent_r1.
# -----------------------------------------------------------------------------
DEEPSEEK_MODEL = "openrouter/deepseek/deepseek-v4-flash"
DEEPSEEK_LABEL = "deepseek-v4-flash via OpenRouter"


# -----------------------------------------------------------------------------
# NODE — idea_parser
# -----------------------------------------------------------------------------
# First node in the graph. Receives the user's raw typed message as
# node_input. Classifies + cleans + writes ParseResult JSON.
#
# mode="single_turn"  -> required for any LlmAgent used as a graph node.
# output_schema       -> ADK forces JSON-only generation against ParseResult;
#                        the parsed object becomes this node's Event.output
#                        and flows to parse_router.
# output_key          -> session.state["parse_result"] also receives the JSON,
#                        which the make_after callback can read for the EXIT
#                        banner.
# -----------------------------------------------------------------------------
idea_parser = LlmAgent(
    name="idea_parser",
    model=LiteLlm(
        model=DEEPSEEK_MODEL,
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Classifies user input as a business idea or not.",
    instruction=IDEA_PARSER_INSTRUCTION,
    output_schema=ParseResult,
    output_key="parse_result",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),
    before_agent_callback=make_before("idea_parser", DEEPSEEK_LABEL),
    after_agent_callback=make_after("idea_parser", DEEPSEEK_LABEL, "parse_result"),
)


# -----------------------------------------------------------------------------
# NODE — parse_router (FunctionNode)
# -----------------------------------------------------------------------------
# Reads the parser's ParseResult, yields trace messages, then yields the final
# routing Event(route=..., output=...). The next node receives `output` as its
# node_input and the edge dict picks the branch by `route`.
#
# Per FunctionNode internals: yielded items become events; a generator's
# `return` value is dropped (StopIteration.value is not surfaced). So the
# routing Event MUST be the final yield, not a return.
# -----------------------------------------------------------------------------
def _parse_router(node_input: ParseResult):
    """Routes to OK (->prompt_builder) or NEED_IDEA (->request_idea HITL).

    On OK, also seeds the state keys that downstream agents will template:
      - state.idea            (cleaned idea)
      - state.refinement_attempts = 0  (fresh counter for the loop)
    """
    yield emit_enter("parse_router", f"is_business={node_input.is_business_idea}")
    if node_input.is_business_idea and node_input.cleaned_idea:
        route = "OK"
        state_seed = {
            "idea": node_input.cleaned_idea,
            "refinement_attempts": 0,
            # Initialise these too so {marginal} substitution is safe before
            # score_router runs — the report only renders post-router, but
            # an early-fail trace might still print them.
            "marginal": False,
        }
    else:
        route = "NEED_IDEA"
        state_seed = {"parse_reason": node_input.reason}
    yield emit_exit("parse_router", f"route={route}")
    yield Event(route=route, output=node_input, state=state_seed)


parse_router = FunctionNode(func=_parse_router, name="parse_router")


# -----------------------------------------------------------------------------
# NODE — request_idea (RequestInput, HITL)
# -----------------------------------------------------------------------------
# Pauses the workflow, asks the user for a business idea, then resumes when
# they reply. Their reply becomes this node's Event.output, which flows along
# the cycle back-edge to idea_parser for re-classification.
#
# responseSchema is intentionally OMITTED — adk web sends plain text from the
# chat input; ADK will not coerce it into a Pydantic shape (caution from
# concepts/adk-graph-workflows.md). idea_parser handles the re-classification
# on the next cycle iteration.
# -----------------------------------------------------------------------------
def _request_idea(node_input):
    # node_input here is the parser's `reason` string (carried by parse_router).
    yield emit_enter("request_idea", "asking user for a business idea")
    yield RequestInput(
        message=(
            "I could not detect a business idea in your message. "
            "Reason: " + str(node_input) + "\n"
            "Please describe a business idea you would like me to validate."
        ),
        payload={"prior_reason": str(node_input)},
    )
    yield emit_exit("request_idea", "user reply received -> back to parser")


request_idea = FunctionNode(func=_request_idea, name="request_idea")
