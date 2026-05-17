import asyncio
import json
import sys

from dotenv import load_dotenv

load_dotenv(".env")

from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import root_agent

APP_NAME = "arch-social-agent"


async def run(prompt: str) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id="test"
    )
    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    async for event in runner.run_async(
        user_id="test", session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    print(f"\n[{event.author}]\n{part.text}")

    session = await runner.session_service.get_session(
        app_name=APP_NAME, user_id="test", session_id=session.id
    )
    if session and session.state.get("strategy_output"):
        print("\n--- Strategy Output ---")
        val = session.state["strategy_output"]
        print(json.dumps(val if isinstance(val, dict) else val, indent=2, default=str))


asyncio.run(
    run(sys.argv[1] if len(sys.argv) > 1 else "Run the architecture social media pipeline")
)
