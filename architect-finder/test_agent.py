import asyncio
import sys
from dotenv import load_dotenv

load_dotenv(".env")

from google.adk.runners import InMemoryRunner
from google.genai import types
from app.agent import root_agent


async def run(prompt):
    runner = InMemoryRunner(agent=root_agent, app_name="architect-finder")
    session = await runner.session_service.create_session(
        app_name="architect-finder", user_id="test"
    )
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(
        user_id="test", session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "Hi"))
