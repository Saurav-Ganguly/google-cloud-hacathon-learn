import os
import time

from google import genai
from google.genai import types


def generate_image(prompt: str) -> dict:
    """Generates an image using Gemini image generation and saves it to the output directory.

    Args:
        prompt: A detailed text description of the image to generate.

    Returns:
        dict with 'status' and 'file_path' or 'message' keys.
    """
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        ),
    )

    os.makedirs("output", exist_ok=True)

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            file_path = f"output/{int(time.time())}.png"
            with open(file_path, "wb") as f:
                f.write(part.inline_data.data)
            return {"status": "success", "file_path": file_path}

    return {"status": "error", "message": "No image data in response"}
