"""
src/generation/gemini_client.py

Shared low-level Gemini client for Intelli-Site.

Every LLM call site in this codebase (router, generation,
citation grounding judge, eval judges) goes through this
single wrapper so the model config and failure handling
stay consistent in one place.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

_client = None


def _get_client():

    global _client

    if _client is None:

        if not GEMINI_API_KEY:

            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file."
            )

        _client = genai.Client(api_key=GEMINI_API_KEY)

    return _client


def generate_text(
    prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 1200
) -> str:

    client = _get_client()

    response = client.models.generate_content(

        model=MODEL_NAME,

        contents=prompt,

        config=types.GenerateContentConfig(

            temperature=temperature,

            max_output_tokens=max_tokens,

            # Reasoning models (gemini-2.5+/3.x) spend part of
            # max_output_tokens on invisible thinking tokens before
            # writing the visible answer — this truncates short
            # classification/JSON output and even long answers if
            # left at the default. This system does grounded
            # extraction/classification work, not something that
            # benefits from extended chain-of-thought. Gemini 3.x
            # models use thinking_level ("minimal" is the lowest —
            # thinking cannot be fully disabled); Gemini 2.5.x models
            # use thinking_budget (0 disables it) instead — if you
            # switch GEMINI_MODEL back to a 2.5.x model, swap this
            # for `thinking_budget=0`.
            thinking_config=types.ThinkingConfig(
                thinking_level="minimal"
            )
        )
    )

    return (response.text or "").strip()
