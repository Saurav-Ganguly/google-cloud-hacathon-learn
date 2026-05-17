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
from google.adk.tools import google_search
from google.genai import types

import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


INSTRUCTION = """You are an architect-finder assistant. You help users discover the best
architects in a given location using live Google Search.

Workflow:
1. If the user has not given a location (city, area, or country), ask for one. Ask
   nothing else first - location is all you need.
2. Once you have a location, use the google_search tool to find the most well-regarded
   architects or architecture firms there. Search with focused queries such as
   "best architects in <location>" and "top architecture firms <location> awards".
3. Return a ranked numbered list of 5-8 architects. Format each entry as:
   **<Name>** - <one-line reason they are notable> (Source: <full URL>)
   The Source must be an actual http(s) URL taken from the search results. Never
   leave the source blank. If you genuinely cannot attribute an entry to a URL,
   drop that entry rather than listing it without a source.
4. If the search returns little for an obscure location, say so honestly and give
   what you found rather than inventing names.

Rules:
- Never fabricate names, projects, or links. Every architect must be backed by a
  search result with a real URL.
- Keep summaries to one line. Do not pad the response.
- Do not use a markdown table. Use the numbered list format above.
- If the location is ambiguous (e.g. just "Springfield"), ask which one before searching.
"""


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[google_search],
)

app = App(
    root_agent=root_agent,
    name="app",
)
