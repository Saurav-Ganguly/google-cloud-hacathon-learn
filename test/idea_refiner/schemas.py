"""Pydantic schemas — typed data bus contracts for the Idea Refiner graph.

Used as `output_schema` on LlmAgents (forces strict JSON generation) and as
`input_schema` type hints on FunctionNodes (Pydantic auto-coerces dict ->
model on the node_input parameter).

Note: instruction templating in ADK uses `{simple_key}` substitution from
session.state — there is no `{ClassName.field}` syntax. So these schemas
are for VALIDATION on the data bus, not for prompt templating. Agents read
prompt content via simple state keys that FunctionNodes write upstream.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ParseResult(BaseModel):
    """Output of `idea_parser` — was the input a business idea or not."""

    is_business_idea: bool = Field(
        description="True if the user's input describes a real business idea."
    )
    reason: str = Field(description="One sentence: why it does or does not qualify.")
    cleaned_idea: Optional[str] = Field(
        default=None,
        description="The user's idea polished into one crisp sentence. "
        "None if is_business_idea=False.",
    )


class ResearchPrompts(BaseModel):
    """Output of `prompt_builder` — four targeted research prompts.

    The matching `split_prompts` FunctionNode unpacks these into individual
    state keys (idea, market_prompt, tech_prompt, etc.) so each research
    agent can read its specific prompt via `{simple_key}` templating.
    """

    idea: str = Field(description="The cleaned idea, carried forward.")
    market_prompt: str
    tech_prompt: str
    competitor_prompt: str
    devils_advocate_prompt: str


class ScoreParameter(BaseModel):
    """One of the five scoring dimensions the `scoring` agent picks."""

    name: str = Field(description="e.g. 'Market Size', 'Technical Risk'.")
    score: int = Field(ge=1, le=10, description="Score 1-10 for this dimension.")
    reasoning: str = Field(description="One-sentence justification.")


class Score(BaseModel):
    """Output of `scoring` — five parameters plus the rolled-up average."""

    parameters: List[ScoreParameter] = Field(
        description="Exactly five scoring dimensions chosen by the agent."
    )
    sum_out_of_50: int = Field(ge=5, le=50)
    avg_out_of_10: float = Field(ge=1.0, le=10.0)
    weakest_parameter: str = Field(
        description="Name of the lowest-scoring parameter."
    )
    overall_reasoning: str = Field(
        description="2-3 sentences summarising the score."
    )


class RefinedIdea(BaseModel):
    """Output of `refiner` — the new idea + how it addresses the weakness."""

    new_idea: str = Field(description="One-sentence refined business idea.")
    what_changed: str = Field(description="What is different from the previous version.")
    addresses_weakness: str = Field(
        description="How this refinement addresses the weakest parameter "
        "from the previous score."
    )
