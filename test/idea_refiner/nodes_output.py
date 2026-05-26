"""Output band — report_writer + reject (leaf nodes).

Graph region:

    score_router --REJECT-----------> reject
                  --APPROVE----------> report_writer
                  --APPROVE_MARGINAL-> report_writer

Concepts exercised:
  - LlmAgent leaf nodes (no successors)
  - Free-text output (no output_schema) — required for prose output
  - Native Gemini (gemini-flash-latest) — fast formatting model

Both nodes read everything they need from state via `{simple_key}` templating
(idea, score, marginal, refinement_attempts, market_text, etc.). They don't
care what node_input they receive — typed data flows on the bus for
validation, but instructions pull from state.

Reference: concepts/adk-graph-workflows.md.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.genai import types

from .prompts import REJECT_INSTRUCTION, REPORT_WRITER_INSTRUCTION
from .tracing import make_after, make_before


GEMINI_MODEL = "gemini-flash-latest"


# -----------------------------------------------------------------------------
# NODE — reject
# -----------------------------------------------------------------------------
# Reached when score_router routes REJECT (avg < 5). Free-text prose output
# explaining the rejection and suggesting a pivot direction.
# -----------------------------------------------------------------------------
reject = LlmAgent(
    name="reject",
    model=GEMINI_MODEL,
    description="Writes the final 'not viable' message for the user.",
    instruction=REJECT_INSTRUCTION,
    output_key="reject_message",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        # Disable hidden thinking; this is pure formatting.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    before_agent_callback=make_before("reject", GEMINI_MODEL),
    after_agent_callback=make_after("reject", GEMINI_MODEL, "reject_message"),
)


# -----------------------------------------------------------------------------
# NODE — report_writer
# -----------------------------------------------------------------------------
# Reached when score_router routes APPROVE or APPROVE_MARGINAL. Reads all the
# state keys (idea, score, marginal, refinement_attempts, the 4 research
# texts) and emits a complete markdown report.
#
# The {marginal} substitution distinguishes the two paths: True triggers the
# "did not clear 8/10" preamble in the report.
# -----------------------------------------------------------------------------
report_writer = LlmAgent(
    name="report_writer",
    model=GEMINI_MODEL,
    description="Generates the final markdown validation report.",
    instruction=REPORT_WRITER_INSTRUCTION,
    output_key="final_report",
    mode="single_turn",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    before_agent_callback=make_before("report_writer", GEMINI_MODEL),
    after_agent_callback=make_after("report_writer", GEMINI_MODEL, "final_report"),
)
