"""
src/prompt_builder.py

Route-aware grounded prompt builder
for Intelli-Site.

Supports:
- structured_only
- legal_rag
"""

from typing import List, Dict

# ─────────────────────────────────────────────────────
# SITE CONTEXT
# ─────────────────────────────────────────────────────

def format_site_context(
    site_summary: Dict
) -> str:

    if not site_summary:

        return (
            "No structured site data available."
        )

    lines = []

    fields = [

        # -------------------------------------------------
        # CORE
        # -------------------------------------------------

        ("BBL", "bbl"),

        ("Address", "address"),

        ("Borough", "borough"),

        # -------------------------------------------------
        # ZONING
        # -------------------------------------------------

        ("Zoning District", "zoning_district"),

        ("Special District", "special_district"),

        ("Overlay", "overlay"),

        ("Zoning Map", "zoning_map"),

        # -------------------------------------------------
        # FAR
        # -------------------------------------------------

        ("Built FAR", "built_far"),

        ("Residential FAR", "residential_far"),

        ("Commercial FAR", "commercial_far"),

        ("Facility FAR", "facility_far"),

        # -------------------------------------------------
        # LOT
        # -------------------------------------------------

        ("Lot Area (sqft)", "lot_area_sqft"),

        ("Building Area (sqft)", "building_area_sqft"),

        ("Lot Front (ft)", "lot_front_ft"),

        ("Lot Depth (ft)", "lot_depth_ft"),

        ("Building Front (ft)", "building_front_ft"),

        ("Building Depth (ft)", "building_depth_ft"),

        # -------------------------------------------------
        # BUILDING
        # -------------------------------------------------

        ("Year Built", "year_built"),

        ("Year Altered 1", "year_altered_1"),

        ("Year Altered 2", "year_altered_2"),

        ("Number of Floors", "num_floors"),

        ("Land Use", "land_use"),

        # -------------------------------------------------
        # ENVIRONMENT
        # -------------------------------------------------

        ("Flood Zone", "flood_zone"),

        ("E Designation", "e_designation"),

        ("E Designation Type", "e_designation_type"),

        ("Landmark", "landmark"),

        ("Historic District", "historic_district"),
    ]

    for label, key in fields:

        value = site_summary.get(key)

        if value not in [None, ""]:

            lines.append(
                f"- {label}: {value}"
            )

    notes = site_summary.get("notes")

    if notes:

        lines.append(
            f"- Notes: {notes}"
        )

    return "\n".join(lines)

# ─────────────────────────────────────────────────────
# LEGAL CONTEXT
# ─────────────────────────────────────────────────────

def format_legal_context(
    retrieved_chunks: List[Dict]
) -> str:

    if not retrieved_chunks:

        return (
            "No legal sections retrieved."
        )

    blocks = []

    for chunk in retrieved_chunks:

        citation = chunk.get(
            "citation_id",
            "UNKNOWN"
        )

        subsection = chunk.get(
            "subsection_title",
            ""
        )

        text = chunk.get(
            "text",
            ""
        )

        # -------------------------------------------------
        # CLEAN TEXT
        # -------------------------------------------------

        cleaned_lines = []

        seen = set()

        for line in text.splitlines():

            clean = (
                line.strip()
                .replace("  ", " ")
            )

            if not clean:
                continue

            if clean == "---":
                continue

            if clean.lower().startswith(
                "**retrieved:**"
            ):
                continue

            if clean.lower().startswith(
                "**source:**"
            ):
                continue

            normalized = clean.lower()

            if normalized in seen:
                continue

            seen.add(normalized)

            cleaned_lines.append(clean)

        cleaned_text = "\n".join(
            cleaned_lines
        )

        block = f"""
[{citation}]

{subsection}

{cleaned_text}
"""

        blocks.append(
            block.strip()
        )

    return "\n\n".join(blocks)

# ─────────────────────────────────────────────────────
# WARNINGS
# ─────────────────────────────────────────────────────

def format_warnings(
    warnings: List[str]
) -> str:

    if not warnings:

        return (
            "No retrieval warnings."
        )

    return "\n".join([
        f"- {w}"
        for w in warnings
    ])

# ─────────────────────────────────────────────────────
# STRUCTURED-ONLY PROMPT
# ─────────────────────────────────────────────────────

def build_structured_prompt(

    question: str,

    site_context: str

):

    return f"""
You are Intelli-Site,
a factual NYC zoning/property assistant.

STRICT RULES:

1. Use ONLY the provided structured data.
2. Return exact factual values only.
3. Do NOT infer or estimate.
4. Do NOT perform legal reasoning.
5. Do NOT speculate.
6. If data is missing,
   explicitly state that it is unavailable.
7. Keep answers concise and factual.
8. Do NOT use citation markers like [SOURCE_X] —
   no legal text was retrieved for this question,
   so there is nothing to cite. Reference the
   structured data by field name instead.

==================================================
USER QUESTION
==================================================

{question}

==================================================
STRUCTURED SITE DATA
==================================================

{site_context}

==================================================
TASK
==================================================

Answer ONLY from the structured data.
""".strip()

# ─────────────────────────────────────────────────────
# LEGAL RAG PROMPT
# ─────────────────────────────────────────────────────

def build_legal_prompt(

    question: str,

    site_context: str,

    legal_context: str,

    warning_context: str

):

    return f"""
You are Intelli-Site,
a provenance-aware NYC zoning assistant.

STRICT RULES:

1. Use ONLY the provided context.
2. Never invent zoning rules.
3. Never fabricate legal conclusions.
4. Cite supporting sections from the
   RETRIEVED LEGAL CONTEXT using citation
   IDs like [SOURCE_1]. Only use citation
   IDs that literally appear in that section.
5. Facts drawn from STRUCTURED SITE DATA
   (address, zoning district, FAR, etc.)
   need NO citation marker at all — state
   them plainly. Do NOT invent a citation ID
   such as [SOURCE_SITE_DATA] for them.
6. If context is insufficient,
   explicitly abstain.
7. If warnings indicate missing sections,
   acknowledge uncertainty.
8. Distinguish clearly between:
   - factual site data
   - zoning regulations
   - assumptions
9. Prefer conservative legal interpretation.
10. Do NOT cite sections not provided.
11. Do NOT speculate beyond the corpus.

==================================================
USER QUESTION
==================================================

{question}

==================================================
STRUCTURED SITE DATA
==================================================

{site_context}

==================================================
RETRIEVED LEGAL CONTEXT
==================================================

{legal_context}

==================================================
RETRIEVAL WARNINGS
==================================================

{warning_context}

==================================================
TASK
==================================================

Provide a grounded zoning analysis.

Use citations whenever possible.

If information is insufficient,
state that explicitly.
""".strip()

# ─────────────────────────────────────────────────────
# MAIN ENTRYPOINT
# ─────────────────────────────────────────────────────

def build_prompt(

    question: str,

    route: str,

    site_summary: Dict,

    retrieved_chunks: List[Dict],

    warnings: List[str]

):

    site_context = format_site_context(
        site_summary
    )

    # -------------------------------------------------
    # STRUCTURED ONLY
    # -------------------------------------------------

    if route == "structured_only":

        return build_structured_prompt(

            question=question,

            site_context=site_context
        )

    # -------------------------------------------------
    # LEGAL RAG
    # -------------------------------------------------

    legal_context = format_legal_context(
        retrieved_chunks
    )

    warning_context = format_warnings(
        warnings
    )

    return build_legal_prompt(

        question=question,

        site_context=site_context,

        legal_context=legal_context,

        warning_context=warning_context
    )
