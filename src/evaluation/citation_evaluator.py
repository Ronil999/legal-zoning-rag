"""
src/evaluation/citation_evaluator.py

Citation attribution and grounding evaluator
for Intelli-Site.

Purpose:
- Validate citation usage
- Detect unsupported reasoning
- Measure grounding confidence
- Preserve abstention-safe behavior
"""

import re
import json

from src.generation.gemini_client import generate_text

# ─────────────────────────────────────────────────────
# LEGAL / SPECULATIVE TERMS
# heuristic unsupported reasoning detector
# ─────────────────────────────────────────────────────

SPECULATIVE_TERMS = [

    "variance",

    "special permit",

    "waiver",

    "exception",

    "appeal",

    "override",

    "automatically allowed",

    "guaranteed approval",

    "by right",

    "non-compliant"
]

# ─────────────────────────────────────────────────────
# EXTRACT CITATIONS
# ─────────────────────────────────────────────────────

def extract_citations(
    answer: str
):

    citations = re.findall(

        r'\[SOURCE_\d+\]',

        answer
    )

    return sorted(list(set(citations)))

# ─────────────────────────────────────────────────────
# VALIDATE CITATIONS EXIST
# ─────────────────────────────────────────────────────

def validate_citation_existence(

    citations: list,

    retrieved_chunks: list
):

    valid = set(

        f"[{c['citation_id']}]"

        for c in retrieved_chunks
    )

    invalid = []

    for citation in citations:

        if citation not in valid:

            invalid.append(citation)

    return {

        "valid": len(invalid) == 0,

        "invalid_citations": invalid
    }

# ─────────────────────────────────────────────────────
# ABSTENTION DETECTION
# ─────────────────────────────────────────────────────

def detect_abstention(
    answer: str
):

    patterns = [

        "insufficient information",

        "cannot determine",

        "unable to determine",

        "not enough information",

        "does not contain enough",

        "insufficient context"
    ]

    lower = answer.lower()

    for p in patterns:

        if p in lower:
            return True

    return False

# ─────────────────────────────────────────────────────
# UNSUPPORTED CLAIM HEURISTICS
# ─────────────────────────────────────────────────────

def detect_unsupported_terms(

    answer: str,

    retrieved_chunks: list
):

    combined_context = "\n".join(

        chunk["text"]

        for chunk in retrieved_chunks
    ).lower()

    unsupported = []

    lower_answer = answer.lower()

    for term in SPECULATIVE_TERMS:

        if (

            term in lower_answer

            and term not in combined_context

        ):

            unsupported.append(term)

    return unsupported

# ─────────────────────────────────────────────────────
# LLM GROUNDING EVALUATION
# ─────────────────────────────────────────────────────

def llm_grounding_check(

    answer: str,

    retrieved_chunks: list
):

    context = "\n\n".join([

        f"""
[{chunk['citation_id']}]

{chunk['text']}
"""

        for chunk in retrieved_chunks
    ])

    prompt = f"""
You are a legal grounding evaluator.

Your task:
Determine whether the answer is
supported by the provided evidence.

RULES:
- Be conservative.
- Flag unsupported legal reasoning.
- Do NOT require exact wording matches.
- Paraphrasing is acceptable.
- Abstentions are GOOD behavior.
- Unsupported legal procedures are BAD.

Return STRICT JSON ONLY.

Schema:
{{
  "grounded": true/false,
  "grounding_score": 0.0-1.0,
  "unsupported_claims": [
    ...
  ],
  "reason": "..."
}}

==================================================
EVIDENCE
==================================================

{context}

==================================================
ANSWER
==================================================

{answer}
"""

    try:

        text = generate_text(

            prompt=prompt,

            temperature=0.0,

            max_tokens=400
        )

    except Exception as e:

        return {

            "grounded": False,

            "grounding_score": 0.0,

            "unsupported_claims": [],

            "reason": (
                f"Grounding request failed: {e}"
            )
        }

    # -------------------------------------------------
    # EXTRACT JSON
    # -------------------------------------------------

    match = re.search(

        r'\{.*\}',

        text,

        re.DOTALL
    )

    if not match:

        return {

            "grounded": False,

            "grounding_score": 0.0,

            "unsupported_claims": [],

            "reason": (
                "Could not parse "
                "grounding evaluation."
            )
        }

    try:

        parsed = json.loads(
            match.group(0)
        )

    except Exception:

        return {

            "grounded": False,

            "grounding_score": 0.0,

            "unsupported_claims": [],

            "reason": (
                "Grounding parser failed."
            )
        }

    return parsed

# ─────────────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────────────

def evaluate_citations(

    answer: str,

    retrieved_chunks: list
):

    # -------------------------------------------------
    # CITATIONS
    # -------------------------------------------------

    citations = extract_citations(
        answer
    )

    citation_validation = (

        validate_citation_existence(

            citations,

            retrieved_chunks
        )
    )

    # -------------------------------------------------
    # ABSTENTION
    # -------------------------------------------------

    abstaining = detect_abstention(
        answer
    )

    # -------------------------------------------------
    # UNSUPPORTED TERMS
    # -------------------------------------------------

    unsupported_terms = (

        detect_unsupported_terms(

            answer,

            retrieved_chunks
        )
    )

    # -------------------------------------------------
    # LLM GROUNDING
    # -------------------------------------------------

    grounding = llm_grounding_check(

        answer,

        retrieved_chunks
    )

    # -------------------------------------------------
    # TRUST DECISION
    # -------------------------------------------------

    trustworthy = True

    if not citation_validation["valid"]:

        trustworthy = False

    if grounding.get("grounded") is False:

        trustworthy = False

    if unsupported_terms:

        trustworthy = False

    # abstention is SAFE behavior

    if abstaining:

        trustworthy = True

    return {

        "citations_found": citations,

        "citation_validation": (

            citation_validation
        ),

        "is_abstaining": abstaining,

        "unsupported_terms": (

            unsupported_terms
        ),

        "grounding": grounding,

        "trustworthy": trustworthy
    }