# =============================================================================
# DEBATE BOT  —  ADK LlmAgent feature sandbox  (2026-05-20)
# =============================================================================
# Single deeply-annotated file. Drills every LlmAgent feature documented at
# https://adk.dev/agents/llm-agents/ that was NEVER used hands-on before today
# in this vault, plus a SequentialAgent at the top.
#
# Pipeline (top-down):
#
#   SequentialAgent  root_agent  ("debate_arena")
#   |
#   +-- topic_refiner          (Gemini — refines/invents debate topic)
#   |     output_schema=DebateTopic, output_key="debate_topic"
#   |
#   +-- pro_agent_r1           (LiteLlm gemma, hot temp)  ROUND 1 OPENING
#   |     output_schema=ProCase, output_key="pro_case_r1"
#   |     instruction reads {debate_topic}
#   |
#   +-- con_agent_r1           (LiteLlm deepseek, cold temp)  ROUND 1 REBUTTAL
#   |     output_schema=ConCase, output_key="con_case_r1"
#   |     instruction reads {debate_topic} + {pro_case_r1}
#   |
#   +-- pro_agent_r2           (LiteLlm gemma)  ROUND 2 REJOINDER
#   |     output_schema=ProCase, output_key="pro_case_r2"
#   |     instruction reads {debate_topic} + {pro_case_r1} + {con_case_r1}
#   |     -> defends original arguments AND rebuts Con's rebuttals
#   |
#   +-- con_agent_r2           (LiteLlm deepseek)  ROUND 2 CLOSING
#   |     output_schema=ConCase, output_key="con_case_r2"
#   |     instruction reads {debate_topic} + r1 of both + {pro_case_r2}
#   |     -> closes by rebutting Pro's r2 defenses
#   |
#   +-- fact_check_agent       (Gemini + google_search, NO output_schema)
#   |     output_key="fact_check"     <-- plain text grounding notes
#   |     reads ALL four debate slots and fact-checks their strongest claims
#   |
#   +-- judge_agent            (Gemini + BuiltInPlanner thinking)
#         output_schema=Verdict, output_key="verdict"
#         include_contents='none'   <-- proves state-passing (not chat history)
#         reads all four debate slots + fact_check + model labels (f-string)
#         safety_settings relax DANGEROUS_CONTENT for spicy topics
#
# Why two rounds, no loop, no critic:
#   The earlier loop+critic design had Con always getting the last word and
#   never letting Pro respond -- unfair. A fixed 2-round pro/con/pro/con
#   alternation is symmetric: each side opens AND closes its line. Simpler
#   than a critic-driven LoopAgent and easier to reason about.
#
# Hard ADK constraint shaping the design:
#   output_schema disables tool use AND agent transfer. So:
#     - pro/con/judge all have output_schema -> no tools, no delegation
#     - fact_check_agent uses google_search -> NO output_schema (plain text)
#     - judge reads fact_check as a TEXT blob, not parsed JSON
#   This is the "research-then-structure" composition forced by the constraint.
#
# Features-to-vault-notes index:
#   instruction {var} templating ......... concepts/adk-session-state
#   output_schema + output_key ........... concepts/adk (LlmAgent reference)
#   generate_content_config .............. concepts/adk (LlmAgent reference)
#   planner (BuiltInPlanner) ............. concepts/adk (LlmAgent reference)
#   include_contents='none' .............. concepts/adk (LlmAgent reference)
#   LiteLlm + reasoning-off .............. concepts/adk-litellm-models
#   after_agent_callback ................. concepts/adk-session-state
#
# Why NO input_schema:
#   `input_schema` validates the inbound USER message. In a SequentialAgent
#   the user only types once (free text into topic_refiner); every downstream
#   agent receives data via state templating, not as a fresh user message. So
#   input_schema has nowhere natural to attach here. Documented and skipped.
#
# Run:
#   cd c:\Users\Hp\Desktop\code\google_cloud_hacathon\test\LlmDebator
#   $env:PYTHONUTF8=1
#   uv run adk web . --port 8080
#   then open http://127.0.0.1:8080
# =============================================================================

import json
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.genai import types


# -----------------------------------------------------------------------------
# MODEL SELECTION
# -----------------------------------------------------------------------------
# Three model "doorways" appear in this file:
#   1. Native Gemini strings  ->  Agent(model="gemini-...")
#   2. LiteLlm wrapper        ->  Agent(model=LiteLlm(model="openrouter/..."))
#   3. extra_body passthrough ->  LiteLlm(..., extra_body={"reasoning":{...}})
#
# GEMINI_MODEL: native Gemini -- required by BuiltInPlanner (thinking is a
#       Gemini-only feature) AND by google_search (built-in Google tool).
# PRO/CON via OpenRouter: the WHOLE point of this sandbox is model diversity --
#       Pro and Con MUST be different models so the debate isn't a single LLM
#       arguing against itself. extra_body kills reasoning leakage (see
#       concepts/adk-litellm-models for the full story).
# -----------------------------------------------------------------------------
GEMINI_MODEL = "gemini-flash-latest"
PRO_MODEL = "openrouter/google/gemma-4-26b-a4b-it"
CON_MODEL = "openrouter/deepseek/deepseek-v4-flash"

# Human-readable labels passed to the judge in its instruction (so the final
# Verdict can name the actual winning model, not just "Pro" or "Con").
PRO_LABEL = "Pro (gemma-4-26b-a4b-it via OpenRouter)"
CON_LABEL = "Con (deepseek-v4-flash via OpenRouter)"


# -----------------------------------------------------------------------------
# PYDANTIC OUTPUT SCHEMAS
# -----------------------------------------------------------------------------
# When an LlmAgent sets `output_schema=SomeModel`, ADK configures the LLM with
# JSON-only controlled generation. The model's response MUST conform to the
# schema or generation fails. The schema-conforming JSON is then auto-parsed
# and stored in session.state under the agent's `output_key`.
#
# Trade-off (HARD CONSTRAINT — bake this into your mental model):
#   output_schema  -> the agent CANNOT use tools or transfer to other agents.
#   The model becomes a pure "shape-fill" engine. If you need both grounding
#   AND structure, split the work: one agent grounds (tools, no schema), the
#   next agent reads its output as text and structures it (schema, no tools).
#
# Schema reuse note:
#   ProCase is used by BOTH pro_agent_r1 AND pro_agent_r2 (same for ConCase).
#   We differentiate the two rounds only by output_key (-> distinct state
#   slots) and by the instruction text (-> different roles per round). Keeps
#   the schema surface small while still preserving every round in state.
# -----------------------------------------------------------------------------

class DebateTopic(BaseModel):
    """The polished topic the debate will argue over."""
    topic: str = Field(description="Crisp, debatable proposition (one sentence).")
    framing: str = Field(description="One-paragraph framing of why this is debatable.")


class ProCase(BaseModel):
    """Pro side's structured argument (used for both rounds)."""
    thesis: str = Field(description="One-sentence positive position for this round.")
    arguments: List[str] = Field(
        description="3-5 one-sentence arguments. In round 2 these are framed as "
        "defenses-of-original + rebuttals-of-Con."
    )


class ConCase(BaseModel):
    """Con side's structured rebuttal + counter-case (used for both rounds)."""
    rebuttals: List[str] = Field(
        description="3-5 rebuttals naming Pro's specific claims from the round "
        "being responded to."
    )
    counter_arguments: List[str] = Field(
        description="2-4 independent counter-arguments. In round 2 this can "
        "include a closing summary."
    )


class Verdict(BaseModel):
    """Final judge output — names which model won the debate."""
    winner_label: Literal["Pro", "Con"] = Field(description="Pro or Con.")
    winner_model: str = Field(description="The model identifier of the winner.")
    reasoning: str = Field(description="3-5 sentences justifying the verdict.")
    pro_score: int = Field(ge=0, le=10, description="Pro's score, 0-10.")
    con_score: int = Field(ge=0, le=10, description="Con's score, 0-10.")


# -----------------------------------------------------------------------------
# DEBUG LOGGER  (after_agent_callback factory)
# -----------------------------------------------------------------------------
# Does TWO things for every agent that fires:
#   (a) Prints a labeled banner to the terminal (the `adk web` console) with
#       agent name + model + state-key + the just-produced output.
#   (b) Returns a types.Content that REPLACES the agent's chat-bubble output
#       with a labeled version "<agent_name> (<model>):\n\n<output>" — so in
#       the adk web UI you can SEE which model produced each bubble.
#
# Why a factory: each agent's output lives under a DIFFERENT state key
# (its output_key) and each agent uses a different model. The factory closes
# over both so the call site stays one line per agent.
#
# after_agent_callback semantics:
#   - return None     -> agent's original output flows through unchanged
#   - return Content  -> REPLACES the agent's final output in the event stream.
#                        State written via output_key is ALREADY in session
#                        state by the time the callback runs, so replacing
#                        the chat bubble is safe.
# -----------------------------------------------------------------------------
def make_logger(model_label: str, output_key: str, dump_full_state: bool = False):
    """Returns an after_agent_callback that labels output for stdout + chat.

    dump_full_state=True is set on the LAST agent (judge) so the terminal
    shows the entire accumulated session state at the end of a run. Useful
    because adk web's State tab is scoped to a single event's delta.
    """

    def _cb(callback_context: CallbackContext) -> Optional[types.Content]:
        agent_name = callback_context.agent_name
        output = callback_context.state.get(output_key)

        # Render once -- used for both stdout banner and chat replacement.
        if isinstance(output, (dict, list)):
            body = json.dumps(output, indent=2, ensure_ascii=False)
        else:
            body = str(output) if output is not None else "(no output)"

        # (a) Terminal banner.
        bar = "=" * 78
        print(f"\n{bar}")
        print(f"{agent_name}  ({model_label})  ->  state[{output_key!r}]")
        print(bar)
        print(body)
        print(bar)

        # Optional full-state dump (judge only) so the terminal shows the
        # entire session state at the end of a run.
        if dump_full_state:
            try:
                # CallbackContext.state behaves dict-like; .to_dict() returns
                # a plain dict of every key written so far in the session.
                full = callback_context.state.to_dict()
            except AttributeError:
                full = dict(callback_context.state)
            print("\n*** FULL SESSION STATE ***")
            print(f"keys: {list(full.keys())}")
            print(json.dumps(full, indent=2, ensure_ascii=False, default=str))
            print("***\n")
        else:
            print()

        # (b) Replace the chat bubble with a labeled version.
        labeled = f"{agent_name}  ({model_label})\n\n{body}"
        return types.Content(
            role="model",
            parts=[types.Part(text=labeled)],
        )

    return _cb


# -----------------------------------------------------------------------------
# AGENT 1 — topic_refiner
# -----------------------------------------------------------------------------
# Entry point. The user types free text into adk web; this agent decides:
#   - input is empty/nonsense -> INVENT a topic
#   - input is a workable topic -> POLISH it
# Writes a DebateTopic JSON to state["debate_topic"], which the rest of the
# pipeline reads via {debate_topic} templating.
# -----------------------------------------------------------------------------
topic_refiner = LlmAgent(
    # Unique identifier. ADK uses this in logs, events, and (for LLM-driven
    # delegation, not used here) as the routing target name.
    name="topic_refiner",
    # Native Gemini model string -- no LiteLlm wrapper. Gemini is the only
    # model family that supports BuiltInPlanner and google_search natively;
    # we use Gemini for every "infrastructure" agent in this pipeline.
    model=GEMINI_MODEL,
    # Short summary. In LLM-driven coordinator setups (not this one) the
    # parent agent's LLM reads sibling descriptions to decide who to delegate
    # to. In a SequentialAgent (this pipeline) it's just documentation.
    description="Turns the user's raw input into a professional debate topic.",
    # The model's system prompt. Plain {var} placeholders here would be filled
    # from state -- none used in this agent because it's the entry point and
    # state is still empty.
    instruction=(
        "You set up a debate. The user's message is your raw input.\n"
        "- If the user input is empty, vague, or nonsensical: INVENT a fresh "
        "debatable proposition on a topic likely to interest a curious adult.\n"
        "- If the user input names a topic: REFINE it into a single crisp "
        "debatable proposition with clear stakes and a one-paragraph framing.\n"
        "Output strictly conforming to the DebateTopic schema."
    ),
    # output_schema activates JSON-only controlled generation against this
    # Pydantic model. Model output is auto-parsed before reaching state.
    output_schema=DebateTopic,
    # output_key is the state slot where the parsed dict gets stored. Other
    # agents read it via {debate_topic} in their own instruction strings.
    output_key="debate_topic",
    # Generation tuning -- temperature lower for deterministic-ish refinement,
    # plus the thinking-budget fix below.
    generate_content_config=types.GenerateContentConfig(
        # Mildly creative but not chaotic; topic polish benefits from low temp.
        temperature=0.4,
        # CRITICAL GOTCHA (debugged 2026-05-20):
        # Gemini 2.5 Flash has hidden thinking ON by default, and thinking
        # tokens count against the model's response budget. For schema-fill
        # agents that don't need to reason, disable thinking explicitly
        # (thinking_budget=0) -- faster, cheaper, no risk of hidden thought
        # starving the visible JSON output. Agents that DO need thinking
        # (judge) opt back in via BuiltInPlanner with its own budget.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    # After the agent emits its JSON, this callback fires. It pretty-prints
    # the result to the terminal AND replaces the chat bubble with a labeled
    # version so the UI shows "topic_refiner (gemini-flash-latest)" above the
    # output. See make_logger above for the full mechanism.
    after_agent_callback=make_logger(GEMINI_MODEL, "debate_topic"),
)


# -----------------------------------------------------------------------------
# AGENT 2 — pro_agent_r1  (Round 1 opening for Pro side)
# -----------------------------------------------------------------------------
# Argues the affirmative for the first time. Reads only {debate_topic}.
#
# Three things on this agent that matter for the learning index:
#   1. LiteLlm wrapper  (concepts/adk-litellm-models)
#   2. extra_body kills OpenRouter "reasoning" leak (without this, reasoning
#      models leak chain-of-thought into the final answer).
#   3. {debate_topic} state-var templating — debate_topic was just written by
#      topic_refiner; ADK substitutes it into the instruction at run time.
# -----------------------------------------------------------------------------
pro_agent_r1 = LlmAgent(
    name="pro_agent_r1",
    # The LiteLlm wrapper makes any non-Gemini model usable in ADK. The
    # wrapper forwards extra kwargs (like extra_body) down to LiteLLM, which
    # in turn forwards them to the provider (OpenRouter here).
    model=LiteLlm(
        # OpenRouter-style identifier "<provider>/<vendor>/<model>".
        model=PRO_MODEL,
        # extra_body is LiteLLM's provider-passthrough channel. OpenRouter
        # accepts a top-level `reasoning` object to control thinking. Setting
        # enabled=False disables thinking entirely -- prevents the model from
        # leaking chain-of-thought into the visible answer (was the cause of
        # the 2026-05-18 reasoning-leak bug; see concepts/adk-litellm-models).
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Pro side, round 1 opening.",
    # {debate_topic} is the state-var templating in action. ADK substitutes
    # state["debate_topic"] (a DebateTopic dict) here at run time. Because the
    # value is a dict, it gets stringified -- the LLM still reads it fine.
    instruction=(
        "You are the Pro debater, opening round. The motion is:\n"
        "{debate_topic}\n\n"
        "Argue STRONGLY in favour of the proposition. Be confident, concrete, "
        "and persuasive. Output strict ProCase JSON: a single-sentence thesis "
        "and 3-5 one-sentence arguments. No prose outside the schema."
    ),
    output_schema=ProCase,
    # Distinct state slot for round 1. The matching pro_agent_r2 writes to
    # pro_case_r2 -- so both rounds survive in state simultaneously.
    output_key="pro_case_r1",
    generate_content_config=types.GenerateContentConfig(
        # HIGH temperature -- we want bold, varied opening arguments. The
        # deliberate contrast with Con's cold temp creates clearer debate
        # dynamics (warm aggressor vs. cool surgeon).
        temperature=0.95,
        # No thinking_config here: OpenRouter models don't have Gemini's
        # default-thinking issue (and reasoning is already disabled above
        # via extra_body). Setting thinking_config on a LiteLlm model is
        # not supported and would be ignored anyway.
    ),
    after_agent_callback=make_logger(PRO_MODEL, "pro_case_r1"),
)


# -----------------------------------------------------------------------------
# AGENT 3 — con_agent_r1  (Round 1 rebuttal for Con side)
# -----------------------------------------------------------------------------
# The {pro_case_r1} template substitution proves state-passing works: con
# does NOT get pro_agent's output as a chat message -- it gets it injected
# into its own system instruction at run time, via session state.
# -----------------------------------------------------------------------------
con_agent_r1 = LlmAgent(
    name="con_agent_r1",
    # Same LiteLlm + extra_body pattern as Pro, but a DIFFERENT model. The
    # cross-model debate is the whole point of this sandbox -- otherwise it
    # would be one LLM arguing against itself.
    model=LiteLlm(
        model=CON_MODEL,
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Con side, round 1 rebuttal.",
    # Two state vars filled here: {debate_topic} (set by topic_refiner) and
    # {pro_case_r1} (just set by the previous agent). Because con_agent_r1
    # runs AFTER pro_agent_r1 in the SequentialAgent, the pro_case_r1 slot
    # is guaranteed to exist by the time this instruction is rendered.
    instruction=(
        "You are the Con debater, round 1. The motion is:\n"
        "{debate_topic}\n\n"
        "Pro just argued (round 1):\n"
        "{pro_case_r1}\n\n"
        "Rebut Pro's specific arguments by name, then add independent counter-"
        "arguments of your own. Output strict ConCase JSON: 3-5 rebuttals that "
        "cite Pro's points and 2-4 counter-arguments."
    ),
    output_schema=ConCase,
    output_key="con_case_r1",
    generate_content_config=types.GenerateContentConfig(
        # LOW temperature -- tight, surgical rebuttals. The contrast with
        # Pro's hot temp (0.95) is intentional: deterministic-ish Con gives
        # the loop a more reliable rebuttal style.
        temperature=0.25,
    ),
    after_agent_callback=make_logger(CON_MODEL, "con_case_r1"),
)


# -----------------------------------------------------------------------------
# AGENT 4 — pro_agent_r2  (Round 2 rejoinder for Pro side)
# -----------------------------------------------------------------------------
# This is the NEW agent that fixes the "Con always gets the last word" issue.
# Pro now reads Con's round-1 rebuttals AND its own round-1 case, then:
#   - defends/refines its original arguments
#   - directly rebuts Con's rebuttals point-by-point
# Same ProCase schema as r1 -- state slot is distinct (pro_case_r2).
# -----------------------------------------------------------------------------
pro_agent_r2 = LlmAgent(
    name="pro_agent_r2",
    # SAME model as pro_agent_r1 (the same "debater" coming back for round 2).
    # In ADK terms it's a NEW agent instance with the same model -- ADK
    # doesn't share LLM context between instances, so all continuity must
    # flow through the state-var injections in the instruction below.
    model=LiteLlm(
        model=PRO_MODEL,
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Pro side, round 2 rejoinder.",
    # THREE state vars filled here -- this is the canonical pattern for a
    # round-aware agent: read your own previous round + the opponent's
    # response + the original motion. The agent then has the full prior
    # context without needing chat history.
    instruction=(
        "You are the Pro debater, round 2. The motion is:\n"
        "{debate_topic}\n\n"
        "Your round-1 case was:\n"
        "{pro_case_r1}\n\n"
        "Con responded (round 1):\n"
        "{con_case_r1}\n\n"
        "REJOINDER: directly rebut each of Con's rebuttals AND counter-"
        "arguments by name, and where useful reinforce or refine your round-1 "
        "points. Output strict ProCase JSON: a single-sentence thesis (your "
        "round-2 position, may be the same or sharpened) and 3-5 one-sentence "
        "arguments where each addresses Con's claims head-on."
    ),
    # Same ProCase schema as r1 -- schema reuse + distinct output_key is the
    # pattern. Saves us defining a near-identical ProRejoinder model.
    output_schema=ProCase,
    output_key="pro_case_r2",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.95,
    ),
    after_agent_callback=make_logger(PRO_MODEL, "pro_case_r2"),
)


# -----------------------------------------------------------------------------
# AGENT 5 — con_agent_r2  (Round 2 closing for Con side)
# -----------------------------------------------------------------------------
# Final word for Con. Reads ALL prior rounds and delivers a closing rebuttal
# focused on Pro's round-2 rejoinder, plus a brief closing summary.
# -----------------------------------------------------------------------------
con_agent_r2 = LlmAgent(
    name="con_agent_r2",
    model=LiteLlm(
        model=CON_MODEL,
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Con side, round 2 closing.",
    # FOUR state vars filled here -- Con's round-2 closing has the most
    # context: it sees both round-1 cases (its own + Pro's) and Pro's
    # round-2 rejoinder. This is the closing position, so it gets the most
    # information and the last word.
    instruction=(
        "You are the Con debater, round 2 (closing). The motion is:\n"
        "{debate_topic}\n\n"
        "Round 1 history:\n"
        "Pro r1: {pro_case_r1}\n"
        "Con r1 (you): {con_case_r1}\n\n"
        "Pro just rebutted in round 2:\n"
        "{pro_case_r2}\n\n"
        "CLOSING: rebut Pro's round-2 points specifically -- focus on whether "
        "Pro's rejoinder actually addressed your round-1 critiques, or merely "
        "restated. Output strict ConCase JSON: 3-5 final rebuttals naming "
        "Pro's round-2 claims, and 2-4 counter-arguments where the last entry "
        "should be a one-sentence closing summary of why Con prevails."
    ),
    output_schema=ConCase,
    output_key="con_case_r2",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.25,
    ),
    after_agent_callback=make_logger(CON_MODEL, "con_case_r2"),
)


# -----------------------------------------------------------------------------
# AGENT 6 — fact_check_agent  (Gemini + google_search, NO output_schema)
# -----------------------------------------------------------------------------
# Runs ONCE after all four debate rounds. Uses google_search to fact-check
# the strongest claims from BOTH rounds of BOTH sides. Output is plain text.
#
# Why no output_schema here: output_schema disables tools. We need google_search
# more than we need structured JSON for this stage. The judge will consume
# fact_check as TEXT, treating it as grounding notes (not parsed JSON). This
# is the "research-then-structure" composition forced by the ADK constraint.
# -----------------------------------------------------------------------------
fact_check_agent = LlmAgent(
    name="fact_check_agent",
    # Must be Gemini -- google_search is a Gemini-native tool. LiteLlm models
    # cannot use it (and even if they could, the schema-vs-tools conflict
    # would block it).
    model=GEMINI_MODEL,
    description="Web-search grounded fact check of the strongest claims.",
    # FIVE state vars filled here -- the fact checker reads EVERYTHING in
    # state up to this point so it can cross-reference claims across rounds.
    instruction=(
        "You fact-check a 2-round debate. Use Google Search to verify the "
        "strongest checkable factual claims from BOTH sides across BOTH rounds.\n\n"
        "Motion: {debate_topic}\n\n"
        "Pro round 1:\n{pro_case_r1}\n\n"
        "Con round 1:\n{con_case_r1}\n\n"
        "Pro round 2:\n{pro_case_r2}\n\n"
        "Con round 2:\n{con_case_r2}\n\n"
        "For each side, pick 2-3 specific factual claims (prefer claims that "
        "are repeated or sharpened across rounds) and check them. For each "
        "claim, write a brief plain-text note in this shape:\n"
        "  - [Pro|Con] claim: \"...\" -> verdict: <supported|disputed|"
        "uncheckable> -> source: <url or 'web search'>.\n"
        "Then write a one-paragraph overall accuracy summary. Plain text "
        "only -- do NOT output JSON, do NOT wrap in code fences."
    ),
    # google_search is the ADK-native Google grounding tool. Works ONLY with
    # Gemini models (built-in tool routing) and CANNOT be combined with
    # output_schema -- attempting either yields an ADK validation error.
    # This constraint is WHY fact_check produces plain text instead of JSON
    # (the only agent in this pipeline that does).
    tools=[google_search],
    # No output_schema here -- so the agent's FINAL text response (plain
    # text, may include citations from google_search) is stored under this
    # key. output_key works on any LlmAgent regardless of whether a schema
    # is set.
    output_key="fact_check",
    generate_content_config=types.GenerateContentConfig(
        # Low temp for accuracy-focused work.
        temperature=0.2,
        # Disable hidden thinking; google_search does the heavy lifting.
        # Same Gemini-2.5-thinking-eats-budget gotcha as topic_refiner.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    after_agent_callback=make_logger(GEMINI_MODEL, "fact_check"),
)


# -----------------------------------------------------------------------------
# AGENT 7 — judge_agent  (Gemini + BuiltInPlanner)
# -----------------------------------------------------------------------------
# Final structured verdict. Reads BOTH rounds of BOTH sides + fact-check.
#
# Three features stacked here:
#
# 1) include_contents='none'
#    Strips ALL chat history out of the model's context window. The judge
#    therefore CANNOT cheat by reading what other agents said earlier in the
#    events. It can only see its filled-in instruction. This is the *proof*
#    that the {pro_case_r1}/{con_case_r1}/{pro_case_r2}/{con_case_r2}/
#    {fact_check} templating is doing the work -- not conversation memory.
#
# 2) safety_settings
#    Per-agent safety overrides. Relaxing DANGEROUS_CONTENT lets spicy
#    debate topics survive without getting refused at the final step.
#
# 3) BuiltInPlanner + output_schema co-existence
#    BuiltInPlanner uses Gemini's dedicated thinking channel (separate from
#    the visible response), so the final response is still pure schema-
#    conforming JSON. (PlanReActPlanner does NOT co-exist with output_schema:
#    it emits /*PLANNING*/.../*FINAL*/ markers in the visible response, which
#    collide with JSON-only generation. That's the gotcha to remember.)
#
# Model labels are baked in via f-string at construction time so the model
# can name the actual winning model in the Verdict (not just "Pro"/"Con").
# -----------------------------------------------------------------------------
judge_instruction = (
    "You are the FINAL JUDGE of a two-round debate.\n\n"
    f"PRO is: {PRO_LABEL}\n"
    f"CON is: {CON_LABEL}\n\n"
    "Motion: {debate_topic}\n\n"
    "Pro round 1 (JSON):\n{pro_case_r1}\n\n"
    "Con round 1 (JSON):\n{con_case_r1}\n\n"
    "Pro round 2 (JSON):\n{pro_case_r2}\n\n"
    "Con round 2 (JSON):\n{con_case_r2}\n\n"
    "Fact-check notes (plain text, web-grounded):\n{fact_check}\n\n"
    "Score each side 0-10 based on:\n"
    "  - argument strength across BOTH rounds\n"
    "  - direct engagement (did each side actually answer the other?)\n"
    "  - factual accuracy (use the fact-check notes)\n"
    "  - whether round 2 actually advanced the case or just restated\n\n"
    f"Set winner_model to the EXACT model identifier of the winning side: "
    f"either {PRO_MODEL!r} (if Pro wins) or {CON_MODEL!r} (if Con wins). "
    "Output strict Verdict JSON."
)

judge_agent = LlmAgent(
    name="judge_agent",
    # Native Gemini -- BuiltInPlanner is Gemini-only.
    model=GEMINI_MODEL,
    description="Final scored verdict on the two-round debate.",
    # Built above via f-string so PRO_LABEL / CON_LABEL / PRO_MODEL /
    # CON_MODEL are baked into the prompt as literals -- the model can name
    # the actual winning model string in its Verdict output.
    instruction=judge_instruction,
    output_schema=Verdict,
    output_key="verdict",
    # Strip conversation history before the model call. The judge sees ONLY
    # its filled-in instruction -- no chat memory -- so the verdict must come
    # purely from the state-injected debate slots + fact-check notes. This
    # is the pedagogical proof that state-passing (not chat history) is what
    # actually carries information between ADK agents.
    include_contents="none",
    # BuiltInPlanner enables Gemini's native thinking. include_thoughts=True
    # surfaces a separate "Thought" block in adk web's event stream so you
    # can watch the judge reason before producing the Verdict JSON.
    # thinking_budget=1024 caps the thinking tokens.
    # CRITICAL: BuiltInPlanner thinking is a SEPARATE channel from the
    # visible response -- so it coexists with output_schema (Verdict JSON
    # still validates). PlanReActPlanner would NOT work here: it emits
    # /*PLANNING*/.../*FINAL*/ markers in the visible response, which
    # collide with JSON-only generation.
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        ),
    ),
    generate_content_config=types.GenerateContentConfig(
        # Low temp for stable, considered judgement.
        temperature=0.2,
        # Per-agent safety override. Default Gemini safety filters can refuse
        # spicy debate topics ("AI rights vs human rights" etc.) at the
        # final-output step. Relaxing DANGEROUS_CONTENT to BLOCK_ONLY_HIGH
        # lets thoughtful debates survive. Other harm categories keep their
        # defaults so the override is narrowly scoped.
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ],
    ),
    # dump_full_state=True is special on the LAST agent: the terminal banner
    # prints the entire accumulated session state after the verdict, so you
    # can see every state slot in one place (independent of adk web's
    # per-event State tab quirk).
    after_agent_callback=make_logger(GEMINI_MODEL, "verdict", dump_full_state=True),
)


# -----------------------------------------------------------------------------
# ROOT — SequentialAgent
# -----------------------------------------------------------------------------
# Top-level orchestrator. Runs its sub_agents in order, exactly once each:
#   topic_refiner -> pro_r1 -> con_r1 -> pro_r2 -> con_r2 -> fact_check -> judge
#
# `root_agent` is the magic name `adk web` looks for in this module.
# -----------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="debate_arena",
    description=(
        "Refines a debate topic, runs Pro vs Con through two symmetric rounds "
        "(opening + rejoinder for each side), fact-checks all claims with "
        "web search, and delivers a structured judge verdict."
    ),
    sub_agents=[
        topic_refiner,
        pro_agent_r1,
        con_agent_r1,
        pro_agent_r2,
        con_agent_r2,
        fact_check_agent,
        judge_agent,
    ],
)


# -----------------------------------------------------------------------------
# FINAL STATE SHAPE  (after one full run, for reference)
# -----------------------------------------------------------------------------
#   debate_topic   : DebateTopic dict
#   pro_case_r1    : ProCase dict — Pro's round-1 opening
#   con_case_r1    : ConCase dict — Con's round-1 rebuttal
#   pro_case_r2    : ProCase dict — Pro's round-2 rejoinder
#   con_case_r2    : ConCase dict — Con's round-2 closing
#   fact_check     : plain text grounding notes (with web citations)
#   verdict        : Verdict dict — winner, reasoning, scores
#
# The judge's terminal banner dumps this entire dict via dump_full_state=True
# so you can verify it in one place at the end of every run.
# -----------------------------------------------------------------------------
