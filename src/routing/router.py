"""
src/routing/router.py

LLM-based query router for Intelli-Site.

Purpose:
- Reject unrelated queries
- Detect factual-only structured queries
- Detect zoning/legal reasoning queries
- Extract temporal intent (years)

Router ONLY classifies.
main.py controls execution flow.
"""

import json
import re

from src.generation.gemini_client import generate_text

# ─────────────────────────────────────────────────────
# ROUTING PROMPT
# ─────────────────────────────────────────────────────

ROUTER_SYSTEM_PROMPT = """
You are a routing classifier
for Intelli-Site,
an NYC zoning intelligence system.

Your task:
Classify the user query into ONE route:

1. structured_only
Use ONLY when the query is asking
for factual property/site information.

Examples:
- zoning district
- flood zone
- lot area
- year built
- BBL lookup
- overlay
- special district
- e-designation existence

2. legal_rag
Use when the query requires:
- zoning interpretation
- legal reasoning
- applicability analysis
- bulk regulations
- setbacks
- FAR analysis
- allowed obstructions
- environmental implications
- any uncertainty

IMPORTANT:
If confidence is NOT HIGH,
choose legal_rag.

3. reject
Use for:
- unrelated questions
- general chit-chat
- coding help
- politics
- medicine
- non-zoning topics

Return STRICT JSON ONLY.

Schema:
{
  "route": "...",
  "confidence": 0.0-1.0,
  "reason": "..."
}
"""

# ─────────────────────────────────────────────────────
# TEMPORAL EXTRACTION
# ─────────────────────────────────────────────────────

def extract_query_year(
    question: str
):

    """
    Extract explicit temporal year
    from query.

    Examples:
    - 2015
    - as of 2019
    - before 2020
    - under 2018 rules
    """

    years = re.findall(

        r'\b(19\d{2}|20\d{2})\b',

        question
    )

    if not years:
        return None

    years = [

        int(y)

        for y in years
    ]

    # -------------------------------------------------
    # KEEP MOST RECENT MENTIONED YEAR
    # -------------------------------------------------

    return max(years)

# ─────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────

def route_query(
    question: str
):

    # -------------------------------------------------
    # TEMPORAL EXTRACTION
    # -------------------------------------------------

    query_year = extract_query_year(
        question
    )

    prompt = f"""
{ROUTER_SYSTEM_PROMPT}

USER QUERY:
{question}

Return ONLY valid JSON.
"""

    try:

        text = generate_text(

            prompt=prompt,

            temperature=0.0,

            max_tokens=200
        )

    except Exception as e:

        return {

            "route": "legal_rag",

            "confidence": 0.0,

            "reason": (
                f"Router request failed: {e}. "
                "Defaulting safely to legal_rag."
            ),

            "query_year": query_year
        }

    # print("\nRAW ROUTER RESPONSE:\n")

    # print(text)

    # -------------------------------------------------
    # EXTRACT JSON OBJECT
    # -------------------------------------------------

    match = re.search(

        r'\{.*\}',

        text,

        re.DOTALL
    )

    if not match:

        return {

            "route": "legal_rag",

            "confidence": 0.0,

            "reason": (
                "No JSON detected. "
                "Defaulting safely to legal_rag."
            ),

            "query_year": query_year
        }

    json_text = match.group(0)

    # -------------------------------------------------
    # PARSE JSON
    # -------------------------------------------------

    try:

        parsed = json.loads(
            json_text
        )

    except Exception as e:

        return {

            "route": "legal_rag",

            "confidence": 0.0,

            "reason": (
                f"JSON parse failed: {e}"
            ),

            "query_year": query_year
        }

    # -------------------------------------------------
    # VALIDATE ROUTE
    # -------------------------------------------------

    valid_routes = {

        "structured_only",

        "legal_rag",

        "reject"
    }

    route = parsed.get(
        "route",
        "legal_rag"
    )

    confidence = float(

        parsed.get(
            "confidence",
            0.0
        )
    )

    if route not in valid_routes:

        parsed["route"] = "legal_rag"

        parsed["reason"] = (

            "Invalid route returned. "

            "Defaulted safely to legal_rag."
        )

    # -------------------------------------------------
    # SAFETY OVERRIDE
    # -------------------------------------------------

    if (

        parsed["route"]

        == "structured_only"

        and confidence < 0.90

    ):

        parsed["route"] = "legal_rag"

        parsed["reason"] = (

            "Confidence below 0.90. "

            "Escalated safely to legal_rag."
        )

    # -------------------------------------------------
    # ADD TEMPORAL METADATA
    # -------------------------------------------------

    parsed["query_year"] = query_year

    return parsed
