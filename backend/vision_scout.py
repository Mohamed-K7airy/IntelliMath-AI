"""
Llama 4 Scout Vision Module
=============================
This module handles all vision-related tasks.
Its sole purpose is to read uploaded files/images, extract texts/equations/context accurately,
and provide this information as a structured text payload for the main LLM to solve.

You can configure the API Key in your .env file:
SCOUT_API_KEY=your_key_here
"""

import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# The user can update the model name here or via env vars
SCOUT_API_KEY = os.getenv("SCOUT_API_KEY", os.getenv("GROQ_API_KEY"))
SCOUT_MODEL = os.getenv("SCOUT_MODEL","meta-llama/llama-4-scout-17b-16e-instruct") # Defaulting to the current vision model, change when Llama 4 is available

scout_client = None
if SCOUT_API_KEY:
    try:
        scout_client = Groq(api_key=SCOUT_API_KEY, timeout=60.0)
        print("✅ Llama 4 Scout (Vision) loaded")
    except Exception as e:
        print(f"⚠️ Failed to initialize Llama 4 Scout client: {e}")
else:
    print("⚠️ SCOUT_API_KEY not found. Vision features will be unavailable. Please add it to your .env file.")


def analyze_image_bytes(image_bytes: bytes) -> str:
    """
    Reads raw image bytes, extracts all math expressions, text, and context,
    and returns a structured text format for the main LLM.
    """
    if scout_client is None:
        raise RuntimeError("Llama Scout client not initialized. Check SCOUT_API_KEY in .env.")
    
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return _send_to_scout(f"data:image/jpeg;base64,{base64_image}")
    except Exception as e:
        raise RuntimeError(f"Llama Scout Vision error: {e}")


def analyze_image_base64(base64_image_data: str) -> str:
    """
    Reads a base64 encoded image directly (e.g. from a data URI),
    extracts the math and text, and returns it.
    """
    global scout_client
    if scout_client is None:
        if SCOUT_API_KEY:
            try:
                scout_client = Groq(api_key=SCOUT_API_KEY, timeout=60.0)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Llama Scout client: {e}")
        else:
            raise RuntimeError("Llama Scout client not initialized. Check SCOUT_API_KEY/GROQ_API_KEY in .env.")
        
    try:
        # Some frontend passes 'data:image/png;base64,...' so we pass it directly
        return _send_to_scout(base64_image_data)
    except Exception as e:
        raise RuntimeError(f"Llama Scout Vision error: {e}")


def _send_to_scout(image_url: str) -> str:
    """
    Internal helper to send the actual prompt to the scout model.
    """
    if "application/pdf" in image_url:
        return "[SYSTEM NOTE: The user uploaded a PDF file, but I currently only support image analysis. Please politely ask the user to take a screenshot or upload an image instead.]"

    prompt_text = (
        "You are an OCR and equation extraction tool. "
        "Extract all mathematical problems, equations, text, and tables from the image. "
        "Only return the exact transcription without ANY extra commentary or filler words."
    )

    response = scout_client.chat.completions.create(
        model=SCOUT_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        }
                    }
                ]
            }
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()
