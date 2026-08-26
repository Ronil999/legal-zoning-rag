"""
src/generation/llm.py

LLM generation layer for Intelli-Site.

Responsibilities:
- Gemini interaction
- prompt submission
- response extraction
- safe generation config
"""

from src.generation.gemini_client import generate_text

# ─────────────────────────────────────────────────────
# GENERATION
# ─────────────────────────────────────────────────────

def generate_answer(

    prompt: str,

    temperature: float = 0.1,

    timeout: int = 300
):

    try:

        return generate_text(

            prompt=prompt,

            temperature=temperature,

            max_tokens=1200
        )

    except Exception as e:

        return f"ERROR: Gemini generation failed: {e}"
