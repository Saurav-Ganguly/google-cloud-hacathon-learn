# =============================================================================
# PDF EXPLAINER  —  ADK code_executor sandbox  (2026-05-21)
# =============================================================================
# Single deeply-annotated file. Drills the last unused LlmAgent config slot,
# `code_executor=BuiltInCodeExecutor()`, alongside FunctionTool-with-LiteLlm
# (deepseek via OpenRouter calling a local pypdf tool).
#
# Pipeline (top-down):
#
#   SequentialAgent  root_agent  ("pdf_explainer")
#   |
#   +-- intent_capturer   (Gemini)   — what's the PDF about + desired output
#   |     output_schema=UserIntent, output_key="user_intent"
#   |
#   +-- pdf_extractor     (LiteLlm deepseek + FunctionTool extract_pdf_text)
#   |     tool reads ./test.pdf with pypdf; deepseek returns the text verbatim
#   |     output_key="pdf_text"
#   |
#   +-- structure_planner (Gemini + BuiltInPlanner thinking)
#   |     reads {pdf_text} + {user_intent}; produces ExplanationPlan JSON
#   |     output_schema=ExplanationPlan, output_key="explain_plan"
#   |
#   +-- chart_maker       (Gemini + code_executor=BuiltInCodeExecutor)
#   |     for each section flagged visual_hint="chart", writes matplotlib
#   |     code and runs it; code prints base64 PNG between CHART_START/END
#   |     markers; after_agent_callback parses them into state["chart_images"]
#   |
#   +-- html_renderer     (Gemini, free-text HTML output)
#         reads {pdf_text}, {user_intent}, {explain_plan}, {chart_images};
#         emits a complete Tailwind-CDN HTML doc. after_agent_callback writes
#         ./output.html and prints a clickable file:/// URL.
#
# Hard constraints anchoring the design (see plan + concepts notes):
#   1. BuiltInCodeExecutor is a Gemini-native built-in tool. It cannot run on
#      LiteLlm models (deepseek/gemma via OpenRouter). LiteLlm agents can only
#      use plain FunctionTools.
#   2. The Gemini code-executor sandbox has no pypdf and no host filesystem
#      access — PDF text extraction must run in our local process via a
#      FunctionTool.
#   3. output_schema disables tools AND code_executor. So chart_maker and
#      html_renderer have NO output_schema (chart_maker needs code_executor;
#      html_renderer emits free HTML).
#
# Cross-references:
#   - concepts/adk-llm-agent-config.md  (every config field used here)
#   - concepts/adk-litellm-models.md    (extra_body reasoning-off pattern)
#   - test/LlmDebator/agent.py          (style template for annotations)
# =============================================================================

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.genai import types


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
# GEMINI_MODEL — used wherever we need built-in tools (code_executor) OR
#                thinking (BuiltInPlanner). Both are Gemini-only features.
# EXTRACT_MODEL — deepseek via OpenRouter. Calling a deterministic FunctionTool
#                doesn't need a smart model; deepseek-flash is cheap and good
#                enough at "see-tool, call-tool, return-result-verbatim".
# PDF_PATH — hardcoded per plan. The user dropped test.pdf into this directory.
#            Resolved at import time so the LLM-rendered instruction substitutes
#            an absolute path (deepseek otherwise hallucinates relative paths).
# OUTPUT_HTML — where the final HTML is written. Gitignored.
# -----------------------------------------------------------------------------
GEMINI_MODEL = "gemini-flash-latest"
# Code-execution-capable Gemini. The `*-latest` aliases on Vertex's `global`
# endpoint don't expose the built-in code-execution tool (verified 2026-05-21
# in adk web: "Gemini code execution tool is not supported for model
# gemini-flash-latest"). Pin to an explicit version that DOES support it.
CODE_EXEC_MODEL = "gemini-2.5-flash"
EXTRACT_MODEL = "openrouter/deepseek/deepseek-v4-flash"

_THIS_DIR = Path(__file__).resolve().parent
PDF_PATH = str(_THIS_DIR / "test.pdf")
OUTPUT_HTML = _THIS_DIR / "output.html"

# Human-readable labels for the make_logger banners (so adk web bubbles show
# which model produced each step).
EXTRACT_LABEL = "deepseek-v4-flash (via OpenRouter)"
GEMINI_LABEL = GEMINI_MODEL


# -----------------------------------------------------------------------------
# LOCAL TOOL — extract_pdf_text
# -----------------------------------------------------------------------------
# Plain Python function. ADK auto-wraps any callable passed in `tools=[...]`
# into a FunctionTool, exposing it to the LLM as a callable tool with name +
# arg schema derived from the Python signature + docstring.
#
# WHY this lives here (not in the Gemini code-executor sandbox):
#   The sandbox has no pypdf and no host filesystem access. PDF text extraction
#   MUST happen in our local Python process. FunctionTool is the bridge — the
#   LLM emits a tool call, ADK runs the function locally, returns the result
#   to the LLM as a tool-response.
#
# Return type is a dict (ADK conventions: tools return dicts so the model sees
# a structured tool-response, not a bare string).
# -----------------------------------------------------------------------------
def extract_pdf_text(path: str) -> dict:
    """Extracts all text from a PDF file using pypdf.

    Args:
        path: Absolute path to the PDF file on the local filesystem.

    Returns:
        Dict with 'status', 'text' (joined page texts), and 'pages' count.
    """
    import pypdf  # local import keeps cold-start of the module lighter

    reader = pypdf.PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return {
        "status": "ok",
        "pages": len(pages),
        "text": "\n\n".join(pages),
    }


# -----------------------------------------------------------------------------
# PYDANTIC OUTPUT SCHEMAS
# -----------------------------------------------------------------------------
# When an LlmAgent sets `output_schema=SomeModel`, ADK configures the LLM with
# JSON-only controlled generation. The model's response MUST conform to the
# schema or generation fails. Stored under output_key in session.state.
#
# HARD CONSTRAINT (bake this in):
#   output_schema  -> agent CANNOT use tools, transfer to other agents, OR
#                     use code_executor. Pure shape-fill engine.
#   Resolution here: chart_maker and html_renderer have NO output_schema.
# -----------------------------------------------------------------------------

class UserIntent(BaseModel):
    """What the user wants out of this run, derived from their adk-web message."""
    background: str = Field(
        description="One sentence summarising what the PDF is about, per the user."
    )
    output_style: str = Field(
        description="The desired explanation style — e.g. 'for a 12-year-old', "
        "'academic summary', 'infographic-style', 'executive briefing'."
    )


class Section(BaseModel):
    """One section of the explanation plan."""
    title: str = Field(description="Section heading.")
    key_points: List[str] = Field(
        description="2-5 short bullet points to explain in this section."
    )
    visual_hint: Literal["chart", "none"] = Field(
        description="'chart' if a matplotlib visualization would genuinely "
        "aid understanding (real numeric data, comparisons, distributions). "
        "Use 'none' otherwise — DO NOT force fake charts onto text-only content."
    )


class ExplanationPlan(BaseModel):
    """How the PDF will be explained in HTML."""
    title: str = Field(description="A friendly title for the explanation page.")
    sections: List[Section] = Field(
        description="3-7 sections that together explain the PDF clearly."
    )


# -----------------------------------------------------------------------------
# DEBUG LOGGER  (after_agent_callback factory)
# -----------------------------------------------------------------------------
# Same pattern as test/LlmDebator/agent.py. For each agent:
#   (a) Prints a labeled banner to the adk-web terminal.
#   (b) Returns a types.Content that REPLACES the chat bubble with a labeled
#       version "<agent_name> (<model>)\n\n<output>", so the UI shows which
#       model produced each step.
#
# after_agent_callback semantics: return None -> output flows through; return
# Content -> replaces the final output in the event stream. State written via
# output_key is ALREADY in session state by the time this fires, so replacing
# the chat bubble is safe.
# -----------------------------------------------------------------------------
def make_logger(model_label: str, output_key: str, dump_full_state: bool = False):
    """Returns an after_agent_callback that labels output for stdout + chat."""

    def _cb(callback_context: CallbackContext) -> Optional[types.Content]:
        agent_name = callback_context.agent_name
        output = callback_context.state.get(output_key)

        if isinstance(output, (dict, list)):
            body = json.dumps(output, indent=2, ensure_ascii=False)
        else:
            body = str(output) if output is not None else "(no output)"

        bar = "=" * 78
        print(f"\n{bar}")
        print(f"{agent_name}  ({model_label})  ->  state[{output_key!r}]")
        print(bar)
        # Truncate very long bodies in terminal (state still has the full thing).
        print(body[:4000] + ("\n... [truncated]" if len(body) > 4000 else ""))
        print(bar)

        if dump_full_state:
            try:
                full = callback_context.state.to_dict()
            except AttributeError:
                full = dict(callback_context.state)
            print("\n*** FULL SESSION STATE keys:", list(full.keys()), "***\n")

        labeled = f"{agent_name}  ({model_label})\n\n{body[:4000]}"
        return types.Content(
            role="model",
            parts=[types.Part(text=labeled)],
        )

    return _cb


# -----------------------------------------------------------------------------
# AGENT 1 — intent_capturer
# -----------------------------------------------------------------------------
# Entry point. The user's free-text adk-web message tells us (a) what the PDF
# is about, in their words, and (b) how they want it explained. We turn that
# into a structured UserIntent dict that flows downstream.
#
# Drills: output_schema, output_key, thinking_budget=0 (avoid yesterday's
# Gemini-2.5 EOF gotcha on schema-fill agents).
# -----------------------------------------------------------------------------
intent_capturer = LlmAgent(
    name="intent_capturer",
    model=GEMINI_MODEL,
    description="Captures user's stated background and desired output style.",
    instruction=(
        "The user's message describes a PDF they want explained. Extract:\n"
        "- background: one sentence summarising what the PDF is about, in the "
        "user's terms.\n"
        "- output_style: how they want it explained (e.g. 'for a 12-year-old', "
        "'academic', 'infographic-style', 'executive briefing'). If the user "
        "doesn't specify, default to 'clear, friendly explanation for a general "
        "adult reader'.\n"
        "Output strict UserIntent JSON."
    ),
    output_schema=UserIntent,
    output_key="user_intent",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        # GOTCHA (from 2026-05-20): Gemini 2.5 Flash has hidden thinking ON by
        # default and thinking tokens count against response budget. For pure
        # schema-fill, disable thinking explicitly.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    after_agent_callback=make_logger(GEMINI_LABEL, "user_intent"),
)


# -----------------------------------------------------------------------------
# AGENT 2 — pdf_extractor
# -----------------------------------------------------------------------------
# Deepseek via OpenRouter + a local FunctionTool. We deliberately use a
# LiteLlm model here to drill the FunctionTool-with-LiteLlm pattern we hadn't
# exercised yet in the vault.
#
# The instruction is STRICT — without it, deepseek tries to "be helpful" and
# narrate what's in the PDF instead of returning the raw extracted text.
#
# output_key="pdf_text": ADK stores the agent's FINAL response text under this
# key. Since we tell the model to return the tool result verbatim, the state
# slot ends up with the extracted PDF text.
# -----------------------------------------------------------------------------
pdf_extractor = LlmAgent(
    name="pdf_extractor",
    model=LiteLlm(
        model=EXTRACT_MODEL,
        # Kills OpenRouter's "reasoning" leak — without this, reasoning-capable
        # models on OpenRouter leak chain-of-thought into the visible response.
        extra_body={"reasoning": {"enabled": False}},
    ),
    description="Calls the local pypdf tool to extract text from test.pdf.",
    instruction=(
        f"You MUST call the tool `extract_pdf_text` with path='{PDF_PATH}' "
        "as your VERY FIRST action. Then return the value of the tool's "
        "'text' field VERBATIM as your final response — no summary, no "
        "commentary, no markdown formatting. Just the raw extracted text."
    ),
    # Bare function — ADK auto-wraps as a FunctionTool. The function's
    # docstring and type hints become the tool schema the LLM sees.
    tools=[extract_pdf_text],
    output_key="pdf_text",
    after_agent_callback=make_logger(EXTRACT_LABEL, "pdf_text"),
)


# -----------------------------------------------------------------------------
# AGENT 3 — structure_planner
# -----------------------------------------------------------------------------
# Reads {pdf_text} and {user_intent} (state-var templating). Produces an
# ExplanationPlan with 3-7 sections. The planner ALSO decides per-section
# whether a chart would genuinely help — chart_maker downstream only fires
# on sections flagged "chart".
#
# Drills:
#   - planner=BuiltInPlanner(...) with include_thoughts=True — Gemini-only
#     native thinking. Co-exists with output_schema (BuiltInPlanner emits
#     thoughts in a separate channel that doesn't conflict with JSON output).
#   - Multi-var instruction templating: {pdf_text} AND {user_intent}.
# -----------------------------------------------------------------------------
structure_planner = LlmAgent(
    name="structure_planner",
    model=GEMINI_MODEL,
    description="Designs the section structure for the HTML explanation.",
    instruction=(
        "Plan how to explain this PDF in HTML for the user.\n\n"
        "User context (background + desired style):\n{user_intent}\n\n"
        "PDF raw text:\n{pdf_text}\n\n"
        "Design 3-7 sections. For each section choose visual_hint='chart' "
        "ONLY when matplotlib could draw a meaningful, honest visualization "
        "of REAL data present in the PDF (numbers, comparisons, distributions, "
        "timelines). Otherwise use 'none'. DO NOT invent fake data to force "
        "a chart. Output strict ExplanationPlan JSON."
    ),
    output_schema=ExplanationPlan,
    output_key="explain_plan",
    # BuiltInPlanner — Gemini's native thinking. include_thoughts=True surfaces
    # the thought stream in the event log (visible in adk web). Coexists with
    # output_schema because thoughts are a separate channel from final output.
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        ),
    ),
    after_agent_callback=make_logger(GEMINI_LABEL, "explain_plan"),
)


# -----------------------------------------------------------------------------
# AGENT 4 — chart_maker  (today's headline feature)
# -----------------------------------------------------------------------------
# THE one agent in the pipeline that uses code_executor=BuiltInCodeExecutor.
# Reads the ExplanationPlan; for each section flagged visual_hint="chart",
# writes matplotlib code that draws the chart and prints its base64-encoded
# PNG between sentinel markers we can parse downstream.
#
# Why base64-via-print and NOT capturing inline_data Parts:
#   The Gemini code-executor sandbox produces image Parts in the model's
#   response, but capturing them across the agent boundary is fiddly. Having
#   the executed code itself print "CHART_START:title:<b64>:CHART_END" gives
#   us a 100%-deterministic capture path via plain text parsing — much more
#   robust for a learning sandbox.
#
# NO output_schema here (would disable code_executor). Free-text output.
# -----------------------------------------------------------------------------
def _parse_chart_output(text: str) -> list[dict]:
    """Pulls CHART_START|||title|||b64|||CHART_END blocks out of chart_maker output.

    Uses `|||` as delimiter (not `:`) because section titles regularly contain
    colons (e.g. "TSP Manipulation: Hidden Revenue"). Verified 2026-05-21 —
    early colon-delimited version captured 0 charts when titles had colons.
    """
    # title group: any chars EXCEPT `|` or newline — prevents the regex from
    # spanning across multiple markers or absorbing surrounding text.
    # b64 group: strict base64 charset only.
    pattern = re.compile(
        r"CHART_START\|\|\|([^|\r\n]+?)\|\|\|([A-Za-z0-9+/=\s]+?)\|\|\|CHART_END",
        flags=re.DOTALL,
    )
    out = []
    for m in pattern.finditer(text or ""):
        title = m.group(1).strip()
        b64 = re.sub(r"\s+", "", m.group(2))
        try:
            base64.b64decode(b64, validate=True)
        except Exception:
            continue
        out.append({"section_title": title, "b64_png": b64})
    return out


def _collect_agent_text(callback_context: CallbackContext, agent_name: str) -> str:
    """Walks session events backwards to find ALL text emitted by this agent
    in its most recent invocation. Critical for chart_maker — the printed
    stdout from code_executor lives in part.code_execution_result.output,
    NOT in part.text. Without collecting both, chart markers get missed."""
    chunks: list[str] = []
    try:
        events = callback_context._invocation_context.session.events
        for ev in events:
            if getattr(ev, "author", None) != agent_name:
                continue
            content = getattr(ev, "content", None)
            if not content or not getattr(content, "parts", None):
                continue
            for p in content.parts:
                # Plain model text (the "Produced 4 charts..." summary line).
                t = getattr(p, "text", None)
                if t:
                    chunks.append(t)
                # The stdout from executed code — where our CHART_START
                # markers actually appear. The .output field holds whatever
                # the executed Python printed.
                cer = getattr(p, "code_execution_result", None)
                if cer is not None:
                    o = getattr(cer, "output", None)
                    if o:
                        chunks.append(o)
                # NOTE: deliberately NOT reading part.executable_code. The
                # source has the literal f-string template like
                # 'CHART_START|||{title}|||{image_base64}|||CHART_END' which
                # would let the chart-marker regex span across code AND
                # stdout, polluting captured titles with code fragments.
                # Only the printed stdout is authoritative.
    except Exception as e:  # noqa: BLE001
        print(f"[_collect_agent_text] event walk failed: {e}")
    return "\n".join(chunks)


def chart_maker_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """After chart_maker runs, parse its event stream for chart blocks and
    store them in state["chart_images"] so html_renderer can embed them.

    The base64-encoded PNGs are printed by the executed Python — that text
    arrives in `part.code_execution_result.output`, NOT in `part.text`. We
    collect both via _collect_agent_text and run the marker regex over the
    combined haystack.
    """
    agent_name = callback_context.agent_name
    text = _collect_agent_text(callback_context, agent_name)
    charts = _parse_chart_output(text)
    # Two state writes:
    #   chart_images  -> full list of {section_title, b64_png} (consumed by
    #                    html_renderer_callback during placeholder substitution)
    #   chart_titles  -> JUST the titles (cheap, injected into html_renderer's
    #                    prompt so the LLM knows which placeholders to emit).
    #                    The LLM never sees the base64 — it would only
    #                    hallucinate it and bloat output tokens.
    callback_context.state["chart_titles"] = [c["section_title"] for c in charts]
    callback_context.state["chart_images"] = charts

    bar = "=" * 78
    print(f"\n{bar}\n{agent_name}  ({CODE_EXEC_MODEL})  ->  state['chart_images']")
    print(bar)
    print(f"captured {len(charts)} chart(s): " + ", ".join(c["section_title"] for c in charts))
    print(bar)

    labeled_body = (
        f"Captured {len(charts)} chart image(s):\n"
        + "\n".join(f"  - {c['section_title']}" for c in charts)
        + ("\n\n(no charts produced — planner may have flagged all sections 'none')"
           if not charts else "")
    )
    return types.Content(
        role="model",
        parts=[types.Part(text=f"{agent_name}  ({CODE_EXEC_MODEL})\n\n{labeled_body}")],
    )


chart_maker = LlmAgent(
    name="chart_maker",
    # Explicit code-execution-capable model. gemini-flash-latest rejects
    # code_executor with "code execution tool is not supported" on Vertex's
    # global endpoint — pinned to 2.5-flash here. See CODE_EXEC_MODEL note.
    model=CODE_EXEC_MODEL,
    description="Generates matplotlib charts (base64 PNG) for plan sections "
    "flagged visual_hint='chart'.",
    instruction=(
        "You produce matplotlib visualisations for an HTML explainer page.\n\n"
        "Plan:\n{explain_plan}\n\n"
        "PDF text (for reference, to ensure charts reflect real content):\n"
        "{pdf_text}\n\n"
        "For EACH section in the plan whose visual_hint == 'chart', write and "
        "execute Python that:\n"
        "  1. Builds a clear matplotlib figure illustrating that section's "
        "key points. Use real numbers from the PDF where present. If the data "
        "is purely qualitative, draw a simple labelled diagram (e.g. bar chart "
        "of named concepts, flow boxes, timeline).\n"
        "  2. Saves the figure to a BytesIO buffer as PNG.\n"
        "  3. Encodes the PNG to base64 and PRINTS exactly one line per "
        "chart, using triple-pipe `|||` as the delimiter (NOT colons — "
        "section titles often contain colons). The line must look like:\n"
        "       CHART_START|||TITLE|||BASE64DATA|||CHART_END\n"
        "     where TITLE is the section title verbatim and BASE64DATA is "
        "the base64-encoded PNG bytes. Use a Python f-string or .format() "
        "to splice in your title and base64 variables; do not include any "
        "other text between the |||CHART_END marker and the start of the "
        "next CHART_START on a new line.\n"
        "  4. Calls plt.close() to free the figure before the next chart.\n\n"
        "Use ONE code block PER section that needs a chart. Sections flagged "
        "'none' get NO chart — do nothing for them.\n\n"
        "After all chart code has executed, give a one-line natural-language "
        "summary like 'Produced N charts for sections X, Y, Z.' — do NOT "
        "repeat the base64 in your summary."
    ),
    # THE feature this sandbox exists to drill. BuiltInCodeExecutor lets Gemini
    # write and run Python in a sandbox (numpy/pandas/matplotlib/sympy
    # allowed; no network, no host fs). Output Parts from executed code feed
    # back into the model's context automatically.
    code_executor=BuiltInCodeExecutor(),
    # NO output_schema — code_executor and output_schema are mutually
    # exclusive (same wall as tools↔schema). chart_maker's output is free
    # text; we parse it in the callback.
    # NO output_key — chart_images is set imperatively in the callback
    # because it needs to be a list of dicts parsed from the model's text.
    after_agent_callback=chart_maker_callback,
)


# -----------------------------------------------------------------------------
# AGENT 5 — html_renderer
# -----------------------------------------------------------------------------
# Reads ALL four state vars and emits a complete Tailwind-CDN HTML document.
# Plain text output (no schema). The callback writes ./output.html and prints
# a clickable file:/// URL so the user can open it in their browser.
#
# Drills: multi-var instruction templating (4 vars), after_agent_callback as
# side-effect (file write), no output_schema.
# -----------------------------------------------------------------------------
def html_renderer_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Write the rendered HTML to disk and tell the user where to open it.

    Substitutes <!--CHART:title--> placeholders the LLM emitted with real
    <img src='data:image/png;base64,...'> tags built from state["chart_images"].
    This keeps the huge b64 strings OUT of the LLM's prompt and response —
    the model would otherwise hallucinate / loop on the patterns and bloat
    output tokens. Verified failure mode 2026-05-21: model produced 92KB of
    garbage repeating base64 before hitting the output cap.
    """
    agent_name = callback_context.agent_name
    text = _collect_agent_text(callback_context, agent_name)

    # Strip ``` fences if the model wrapped the HTML in a code block.
    html = text.strip()
    fence_match = re.search(r"```(?:html)?\s*(.*?)```", html, flags=re.DOTALL)
    if fence_match:
        html = fence_match.group(1).strip()

    # Substitute chart placeholders with real <img> tags.
    charts = callback_context.state.get("chart_images") or []
    chart_by_title = {c["section_title"]: c["b64_png"] for c in charts}
    used_titles: list[str] = []

    def _sub(m: re.Match) -> str:
        title = m.group(1).strip()
        b64 = chart_by_title.get(title)
        if not b64:
            # Fallback: try a tolerant lookup (case + whitespace insensitive).
            norm = re.sub(r"\s+", "", title.lower())
            for k, v in chart_by_title.items():
                if re.sub(r"\s+", "", k.lower()) == norm:
                    b64 = v
                    title = k
                    break
        if not b64:
            return f"<!-- chart not found for: {title} -->"
        used_titles.append(title)
        return (
            f'<img src="data:image/png;base64,{b64}" alt="{title}" '
            f'class="my-6 mx-auto max-w-full rounded shadow" />'
        )

    placeholder = re.compile(r"<!--\s*CHART:\s*(.*?)\s*-->", flags=re.DOTALL)
    html = placeholder.sub(_sub, html)

    missing = [t for t in chart_by_title if t not in used_titles]

    # Sanity floor: if the model produced no <html, save what we got anyway so
    # the user can inspect — but log a warning.
    if "<html" not in html.lower():
        print("[html_renderer_callback] WARNING: response doesn't look like HTML.")

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    url = f"file:///{OUTPUT_HTML.resolve().as_posix().lstrip('/')}"

    bar = "=" * 78
    print(f"\n{bar}\n{agent_name}  ({GEMINI_LABEL})  ->  wrote {OUTPUT_HTML.name}")
    print(bar)
    print(f"Open in browser: {url}")
    print(f"({len(html)} chars written, {len(used_titles)} chart(s) embedded)")
    if missing:
        print(f"WARNING: {len(missing)} chart(s) captured but no placeholder "
              f"in HTML: {missing}")
    print(bar)
    # Dump full session state for end-of-run inspection.
    try:
        full = callback_context.state.to_dict()
    except AttributeError:
        full = dict(callback_context.state)
    print("\n*** FULL SESSION STATE keys:", list(full.keys()), "***\n")

    return types.Content(
        role="model",
        parts=[types.Part(text=(
            f"{agent_name}  ({GEMINI_LABEL})\n\n"
            f"Wrote {len(html)} chars to {OUTPUT_HTML.name}.\n"
            f"Open: {url}"
        ))],
    )


html_renderer = LlmAgent(
    name="html_renderer",
    model=GEMINI_MODEL,
    description="Renders the final Tailwind HTML explanation page.",
    instruction=(
        "Produce a SINGLE complete HTML document that explains the PDF for "
        "the user. Output ONLY the HTML — no markdown fences, no "
        "commentary.\n\n"
        "Inputs:\n"
        "User intent (background + desired style):\n{user_intent}\n\n"
        "Structured plan:\n{explain_plan}\n\n"
        "PDF text (source material):\n{pdf_text}\n\n"
        "Charts already drawn for the following section titles "
        "(the actual images will be spliced in by a post-processor — DO NOT "
        "generate or paste any base64 yourself):\n{chart_titles}\n\n"
        "Requirements for the HTML:\n"
        "  - Use Tailwind via CDN: <script src='https://cdn.tailwindcss.com'></script>\n"
        "  - Modern, readable layout: max-w-4xl mx-auto, generous spacing, "
        "section headings, bullet lists, soft background.\n"
        "  - Match the user's requested output_style in tone and complexity.\n"
        "  - Each plan section becomes a <section> with the title as <h2> and "
        "the key_points as either bullets or short paragraphs.\n"
        "  - For every section title listed in chart_titles, insert an HTML "
        "comment placeholder on its own line inside that section in the "
        "natural place a chart should go:\n"
        "        <!-- CHART: EXACT_SECTION_TITLE_HERE -->\n"
        "    The title MUST match the chart_titles entry EXACTLY (same "
        "capitalisation, punctuation, spacing). The post-processor replaces "
        "each placeholder with a real <img> tag — you do not write any "
        "<img>, base64, or data: URI yourself.\n"
        "  - Include a short intro paragraph based on user_intent.background.\n"
        "Output: a self-contained HTML5 document. Start with <!doctype html>."
    ),
    # NO output_schema — we need free-form HTML output.
    # NO output_key — html_renderer's role is the side-effect file write.
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        # CRITICAL (verified hung-for-5min, 2026-05-21): Gemini 2.5 Flash has
        # hidden thinking ON by default with an UNLIMITED budget. On a 30k-
        # char prompt the model can think for many minutes before emitting
        # output tokens — looks indistinguishable from a hang. HTML generation
        # is a transcription task, not a reasoning task; disable thinking
        # explicitly. Same fix as topic_refiner in test/LlmDebator/agent.py.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
    after_agent_callback=html_renderer_callback,
)


# -----------------------------------------------------------------------------
# ROOT PIPELINE
# -----------------------------------------------------------------------------
# SequentialAgent: deterministic phase ordering. Each child runs to completion
# before the next starts; state mutations accumulate across the run.
# -----------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="pdf_explainer",
    description=(
        "Turn a hardcoded local PDF into a Tailwind-styled HTML explainer page, "
        "with charts drawn live by Gemini's code executor."
    ),
    sub_agents=[
        intent_capturer,
        pdf_extractor,
        structure_planner,
        chart_maker,
        html_renderer,
    ],
)
