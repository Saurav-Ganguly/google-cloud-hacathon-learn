"""Shared observability helpers for the Idea Refiner graph.

Every node — FunctionNode AND Agent — emits its lifecycle in TWO channels:

  Channel 1: console (stdout). The `adk web` server runs in the foreground
             terminal, so `print(...)` lines appear there as the graph runs.
  Channel 2: adk web event stream. FunctionNodes `yield Event(message=...)`;
             Agent nodes use before/after callbacks that ALSO print, while
             the agent's natural response goes to the event stream as usual.

Plain ASCII only — CLAUDE.md bans emojis in code/print/logging.
"""

from __future__ import annotations

import json
from typing import Optional

from google.adk import Event
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


# -----------------------------------------------------------------------------
# FunctionNode helpers — call from inside a FunctionNode body
# -----------------------------------------------------------------------------

def emit_enter(node_name: str, payload_summary: str = "") -> Event:
    """Print + return an Event(message=...) marking node entry.

    Used like:
        def parse_router(node_input):
            yield emit_enter("parse_router", f"input={node_input!r}")
            ...
    """
    line = _format_line(node_name, "ENTER", payload_summary)
    print(line)
    return Event(message=line)


def emit_exit(node_name: str, payload_summary: str = "") -> Event:
    """Print + return an Event(message=...) marking node exit."""
    line = _format_line(node_name, "EXIT ", payload_summary)
    print(line)
    return Event(message=line)


def emit_info(node_name: str, info: str) -> Event:
    """Mid-node breadcrumb — for chatty FunctionNodes (e.g. score router)."""
    line = _format_line(node_name, "INFO ", info)
    print(line)
    return Event(message=line)


def _format_line(node_name: str, kind: str, payload_summary: str) -> str:
    """Trim long payload summaries so the event stream stays readable."""
    suffix = f"  {payload_summary}" if payload_summary else ""
    if len(suffix) > 120:
        suffix = suffix[:117] + "..."
    return f"[{node_name}] {kind} {suffix}".rstrip()


# -----------------------------------------------------------------------------
# Agent-node helpers — attach as before/after_agent_callback on LlmAgent
# -----------------------------------------------------------------------------
# LlmAgent supports `before_agent_callback` and `after_agent_callback`. We use
# these to print ENTER/EXIT banners to the console. The agent's natural LLM
# response goes to the adk web event stream as usual, so we don't need to
# manually emit Event(message=...) for agent nodes — adk web already shows
# the full text bubble.
#
# Pattern adapted from test/LlmDebator/agent.py `make_logger`.
# -----------------------------------------------------------------------------

def make_before(node_name: str, model_label: str):
    """Return a before_agent_callback that prints an ENTER banner."""

    def _cb(callback_context: CallbackContext) -> Optional[types.Content]:
        bar = "=" * 78
        print(f"\n{bar}")
        print(f"[{node_name}] ENTER  ({model_label})")
        print(bar)
        return None  # do not short-circuit the agent

    return _cb


def make_after(
    node_name: str,
    model_label: str,
    output_key: Optional[str] = None,
    replace_bubble: bool = True,
):
    """Return an after_agent_callback that prints an EXIT banner.

    If `output_key` is given, the freshly-written state value is dumped
    alongside the banner. If `replace_bubble=True` the agent's chat bubble
    in adk web is replaced with a labelled version "[node_name] (model)..."
    so the user can tell at a glance which node produced each bubble.
    """

    def _cb(callback_context: CallbackContext) -> Optional[types.Content]:
        agent_name = callback_context.agent_name
        body: str
        if output_key is not None:
            value = callback_context.state.get(output_key)
            if isinstance(value, (dict, list)):
                body = json.dumps(value, indent=2, ensure_ascii=False, default=str)
            else:
                body = str(value) if value is not None else "(no output)"
        else:
            body = "(no output_key configured)"

        bar = "=" * 78
        print(f"\n{bar}")
        print(f"[{node_name}] EXIT   ({model_label})  agent={agent_name}")
        if output_key is not None:
            print(f"state[{output_key!r}] =")
            print(body)
        print(bar)
        print()

        if replace_bubble:
            labeled = f"[{node_name}]  ({model_label})\n\n{body}"
            return types.Content(role="model", parts=[types.Part(text=labeled)])
        return None

    return _cb
