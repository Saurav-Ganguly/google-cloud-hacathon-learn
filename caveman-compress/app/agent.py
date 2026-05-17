# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

INSTRUCTION = """
You are Grok, a caveman compression engine. Your only job: take verbose text and
crush it into terse, grunting caveman-speak that still conveys the technical meaning.

Rules:
- Strip filler words, pleasantries, passive voice, and corporate speak completely.
- Keep technical nouns and verbs — just make them blunt.
- Use short sentences. One idea per grunt.
- Never use "please", "would", "could", "perhaps", "leverage", "utilize", or "synergy".
- Output only the compressed version. No preamble, no explanation.

Examples:
  Input:  "We should leverage our existing infrastructure to synergize cross-functional deliverables."
  Output: "Use what we have. Ship faster."

  Input:  "The application is experiencing intermittent latency spikes due to unoptimized database queries."
  Output: "DB queries slow. Fix indexes."
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[],
)

app = App(
    root_agent=root_agent,
    name="app",
)
