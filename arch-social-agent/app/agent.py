# ruff: noqa
import os

import google.auth
from google.adk.agents import Agent, SequentialAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.genai import types
from pydantic import BaseModel

from app.tools import generate_image

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


class StrategyOutput(BaseModel):
    linkedin_post: str
    image_prompt: str
    hashtags: list[str]


RESEARCH_INSTRUCTION = """You are an architectural news researcher.

Search the web for the TOP 3 most interesting and recent architectural news stories,
design trends, or notable building projects from the past week.

Use multiple focused search queries such as:
- "latest architectural news 2025"
- "new building designs architecture trends"
- "notable architecture projects completed recently"

For each story, capture: title, brief summary (2-3 sentences), why it matters, and source URL.

Return a structured summary of all 3 findings. Be specific and factual — only include
information backed by actual search results. Never fabricate names, projects, or URLs.
"""

STRATEGY_INSTRUCTION = """You are a social media strategist for the architecture and design industry.

Based on the research findings provided, create compelling LinkedIn content.

Research findings:
{research_findings}

Your task:
1. Pick the single most engaging story from the research
2. Write a professional LinkedIn post (150-200 words) that:
   - Opens with a bold, attention-grabbing first line
   - Shares the architectural insight or trend with genuine expert perspective
   - Explains why this matters to architects, designers, and the built environment
   - Ends with a thought-provoking question to drive engagement
3. Craft a detailed Imagen-style image generation prompt that visually represents
   the story — be specific about: architectural style, lighting, camera perspective,
   mood, color palette, visible materials, time of day
4. Suggest 5 relevant hashtags (without the # symbol in the list)

Return your response in the required structured JSON format.
"""

IMAGE_INSTRUCTION = """You are an image generation specialist.

You have received a social media strategy as JSON. The JSON contains a field called
`image_prompt` with a detailed description for an image.

Strategy JSON:
{strategy_output}

Extract the value of the `image_prompt` field from the JSON above, then call the
`generate_image` tool with that prompt as the argument.

After the image is generated, report the saved file path and confirm completion.
"""


def create_research_agent() -> Agent:
    return Agent(
        name="research_agent",
        model=Gemini(
            model="gemini-flash-latest",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=RESEARCH_INSTRUCTION,
        tools=[google_search],
        output_key="research_findings",
    )


def create_strategy_agent() -> Agent:
    return Agent(
        name="strategy_agent",
        model=Gemini(
            model="gemini-flash-latest",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=STRATEGY_INSTRUCTION,
        output_schema=StrategyOutput,
        output_key="strategy_output",
    )


def create_image_agent() -> Agent:
    return Agent(
        name="image_agent",
        model=Gemini(
            model="gemini-flash-latest",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction=IMAGE_INSTRUCTION,
        tools=[generate_image],
        include_contents="none",
    )


root_agent = SequentialAgent(
    name="arch_social_pipeline",
    sub_agents=[
        create_research_agent(),
        create_strategy_agent(),
        create_image_agent(),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
