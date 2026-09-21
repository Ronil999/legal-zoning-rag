import os
import json
import argparse

from datetime import datetime

from rich.console import Console
from rich.table import Table

from src.main import run_intelli_site
from src.generation.gemini_client import generate_text

console = Console()


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of an LLM judge response,
    tolerating markdown code fences despite instructions
    not to use them."""

    cleaned = text.strip()

    if cleaned.startswith("```"):

        cleaned = cleaned.strip("`")

        cleaned = cleaned.split("\n", 1)[-1]

        if cleaned.rstrip().endswith("```"):

            cleaned = cleaned.rstrip()[:-3]

    return json.loads(cleaned.strip())

# =========================================================
# TEST CASES
# =========================================================

TEST_CASES = [

    # =====================================================
    # SITE + ZONING ANALYSIS QUESTIONS
    # =====================================================

    {
        "case_id": 1,
        "label": "Rear yard depth for site",
        "bbl": "1016800019",
        "question": (
            "For this property, how deep does "
            "the required rear yard need to be?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 2,
        "label": "Fence in rear yard",
        "bbl": "1016800019",
        "question": (
            "Can I build a fence in the "
            "required rear yard of this site?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 3,
        "label": "HVAC equipment placement",
        "bbl": "1016800019",
        "question": (
            "Can HVAC or air conditioning "
            "equipment project into the "
            "rear yard on this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 4,
        "label": "Accessory structure in rear yard",
        "bbl": "1016800019",
        "question": (
            "Can I place a small accessory "
            "shed in the rear yard of this lot?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 5,
        "label": "Maximum residential FAR",
        "bbl": "1016800019",
        "question": (
            "What is the maximum residential "
            "FAR allowed for this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 6,
        "label": "Community facility FAR",
        "bbl": "1016800019",
        "question": (
            "If this site were developed as "
            "a community facility, what FAR "
            "would apply?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 7,
        "label": "Street wall requirement",
        "bbl": "1016800019",
        "question": (
            "Does this property need to place "
            "its street wall close to the "
            "street line?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 8,
        "label": "Setback requirement",
        "bbl": "1016800019",
        "question": (
            "Would this building require "
            "a setback above the base height?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 9,
        "label": "Front yard flexibility",
        "bbl": "1016800019",
        "question": (
            "Can the front yard requirement "
            "for this property be reduced "
            "based on neighboring lots?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 10,
        "label": "Environmental restrictions",
        "bbl": "1016800019",
        "question": (
            "Does this property have any "
            "environmental restrictions "
            "or E-designation issues?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 11,
        "label": "Cross-reference rear yard rules",
        "bbl": "1016800019",
        "question": (
            "Are there any other zoning "
            "sections I need to review for "
            "rear yard regulations on this lot?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 12,
        "label": "Special district override",
        "bbl": "1016800019",
        "question": (
            "Could special district regulations "
            "override the normal rear yard "
            "rules for this site?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 13,
        "label": "Solar panels in rear yard",
        "bbl": "1016800019",
        "question": (
            "Can solar panels be installed "
            "within the rear yard area "
            "of this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 14,
        "label": "Parking access driveway",
        "bbl": "1016800019",
        "question": (
            "Can a driveway pass through "
            "the rear yard of this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 15,
        "label": "Building height envelope",
        "bbl": "1016800019",
        "question": (
            "What building height envelope "
            "rules would apply to this site?"
        ),
        "should_abstain": False,
    },

    # =====================================================
    # ABSTENTION CASES
    # =====================================================

    {
        "case_id": 16,
        "label": "Historical FAR",
        "bbl": "1016800019",
        "question": (
            "What was the exact FAR allowed "
            "on this property in 2015?"
        ),
        "should_abstain": True,
    },

    {
        "case_id": 17,
        "label": "Missing special district",
        "bbl": "1016800019",
        "question": (
            "What are the exact zoning rules "
            "for this property if it falls "
            "inside the Special Hudson Yards District?"
        ),
        "should_abstain": True,
    },

    {
        "case_id": 18,
        "label": "Missing referenced section",
        "bbl": "1016800019",
        "question": (
            "What alternative rear yard "
            "rules apply under Section 23-711 "
            "for this property?"
        ),
        "should_abstain": True,
    },

    {
        "case_id": 19,
        "label": "GIS polygon geometry",
        "bbl": "1016800019",
        "question": (
            "Can you provide the GIS polygon "
            "geometry coordinates for this lot?"
        ),
        "should_abstain": True,
    },

    {
        "case_id": 20,
        "label": "Federal EPA remediation law",
        "bbl": "1016800019",
        "question": (
            "What federal EPA remediation "
            "requirements legally apply "
            "to this site?"
        ),
        "should_abstain": True,
    },

    # =====================================================
    # EXPANDED CORPUS COVERAGE (R1-R5 / Commercial)
    # =====================================================

    {
        "case_id": 21,
        "label": "R4 maximum residential FAR",
        "bbl": "3049930009",
        "question": (
            "What is the maximum residential "
            "FAR allowed for this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 22,
        "label": "R3-2 lot coverage on corner lot",
        "bbl": "5004980028",
        "question": (
            "What is the maximum lot coverage "
            "allowed for this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 23,
        "label": "C4-2 commercial maximum FAR",
        "bbl": "4049630075",
        "question": (
            "What is the maximum commercial "
            "FAR allowed for this property?"
        ),
        "should_abstain": False,
    },

    {
        "case_id": 24,
        "label": "R4 flat-roof height limit",
        "bbl": "3049930009",
        "question": (
            "What is the maximum building height "
            "for a flat-roof building on this property?"
        ),
        "should_abstain": False,
    },
]


# =========================================================
# ABSTENTION PHRASES
# =========================================================

ABSTAIN_PHRASES = [

    "corpus does not",
    "corpus doesn't",
    "not in the corpus",
    "cannot be determined",
    "not enough information",
    "unable to answer",
    "not present in the corpus",
    "outside the scope",
    "does not support",
    "not covered in the corpus",
]

# =========================================================
# HALLUCINATION JUDGE
# =========================================================
def judge_grounding(
    question,
    chunks,
    response,
    site_summary=None
):

    legal_context = "\n\n".join(

        str(
            c.get("text", "")
        )[:3000]

        for c in chunks[:8]
    )

    site_context = "\n".join(

        f"{k}: {v}"

        for k, v in (site_summary or {}).items()

        if v not in (None, "")
    )

    context = (

        f"STRUCTURED SITE DATA:\n{site_context or '(none)'}"

        f"\n\nLEGAL TEXT:\n{legal_context or '(none)'}"
    )

    prompt = f"""
You are a strict legal RAG hallucination evaluator.

TASK:
Determine whether the answer contains claims NOT supported by the retrieved context.

IMPORTANT:
- The retrieved context below includes BOTH structured site data (from
  the site's property record) AND retrieved legal text. Facts drawn from
  either section are grounded — do not flag structured site facts
  (address, zoning district, lot dimensions, FAR, etc.) as hallucinated
  just because they only appear in the structured section.
- Use ONLY the retrieved context.
- Do NOT use outside knowledge.
- If the answer adds unsupported legal rules, mark hallucination=true.

Return ONLY valid minified JSON.
No markdown.
No explanation outside JSON.

Required schema:

{{
"hallucination": true,
"grounding_score": 0,
"reason": "short reason"
}}

Scoring:
2 = fully grounded
1 = minor unsupported additions
0 = major hallucinations

QUESTION:
{question}

RETRIEVED CONTEXT:
{context}

ANSWER:
{response}
"""

    try:

        raw = generate_text(

            prompt=prompt,

            temperature=0,

            max_tokens=300
        )

        data = _extract_json(raw)

        return {

            "judge_available": True,

            "hallucination": data.get(
                "hallucination"
            ),

            "grounding_score": data.get(
                "grounding_score"
            ),

            "reason": data.get(
                "reason"
            )
        }

    except Exception as e:

        return {

            "judge_available": False,

            "hallucination": None,

            "grounding_score": None,

            "reason": str(e)
        }

# =========================================================
# ABSTENTION JUDGE
# =========================================================
def judge_abstention(
    case,
    response,
    chunks,
    site_summary=None
):

    legal_context = "\n\n".join(

        str(
            c.get("text", "")
        )[:3000]

        for c in chunks[:8]
    )

    site_context = "\n".join(

        f"{k}: {v}"

        for k, v in (site_summary or {}).items()

        if v not in (None, "")
    )

    context = (

        f"STRUCTURED SITE DATA:\n{site_context or '(none)'}"

        f"\n\nLEGAL TEXT:\n{legal_context or '(none)'}"
    )

    prompt = f"""
You are evaluating abstention behavior in a legal RAG system.

Determine:
- should the system abstain?
- did the system abstain correctly?

IMPORTANT:
- The retrieved context below includes BOTH structured site data AND
  retrieved legal text. Facts drawn from either section are grounded —
  do not treat structured site facts as invented just because they
  only appear in the structured section.
- Use ONLY retrieved context.
- If context is insufficient, abstention is correct.
- If answer invents unsupported information, abstention is incorrect.

Return ONLY valid minified JSON.

Required schema:

{{
"correct_abstention": true,
"did_abstain": true,
"reason": "short reason"
}}

QUESTION:
{case["question"]}

RETRIEVED CONTEXT:
{context}

ANSWER:
{response}

EXPECTED SHOULD ABSTAIN:
{case["should_abstain"]}
"""

    try:

        raw = generate_text(

            prompt=prompt,

            temperature=0,

            max_tokens=250
        )

        data = _extract_json(raw)

        return {

            "judge_available": True,

            "correct_abstention": data.get(
                "correct_abstention"
            ),

            "did_abstain": data.get(
                "did_abstain"
            ),

            "reason": data.get(
                "reason"
            )
        }

    except Exception as e:

        return {

            "judge_available": False,

            "correct_abstention": None,

            "did_abstain": None,

            "reason": str(e)
        }

# =========================================================
# FINAL SCORE
# =========================================================

def final_score(
    grounding_score,
    abstention_ok
):

    if grounding_score is None:

        return "UNKNOWN"

    if grounding_score == 2 and abstention_ok:

        return "PASS"

    if grounding_score == 1:

        return "PARTIAL"

    return "FAIL"

# =========================================================
# RUN CASE
# =========================================================

def run_case(case):

    console.rule(
        f"[bold blue]Case {case['case_id']}[/bold blue]"
    )

    result = run_intelli_site(

        question=case["question"],

        bbl=case["bbl"]
    )

    response = result.get(
        "formatted_response",
        ""
    )

    chunks = result.get(
        "retrieved_chunks",
        []
    )

    site_summary = result.get(
        "site_summary",
        {}
    )

    console.print(
        f"[bold]Question:[/bold] {case['question']}"
    )

    console.print(
        f"[bold]Answer:[/bold] {response[:350]}"
    )

    # =====================================================
    # GROUNDING
    # =====================================================

    grounding = judge_grounding(

        case["question"],

        chunks,

        response,

        site_summary
    )

    # =====================================================
    # ABSTENTION
    # =====================================================

    abstention = judge_abstention(

        case,

        response,

        chunks,

        site_summary
    )

    abstention_ok = abstention.get(
        "correct_abstention",
        False
    )

    # =====================================================
    # FINAL SCORE
    # =====================================================

    score = final_score(

        grounding.get(
            "grounding_score"
        ),

        abstention_ok
    )

    console.print(
        f"[cyan]Grounding Score:[/cyan] "
        f"{grounding.get('grounding_score')}"
    )

    console.print(
        f"[cyan]Hallucination:[/cyan] "
        f"{grounding.get('hallucination')}"
    )

    console.print(
        f"[cyan]Abstention Correct:[/cyan] "
        f"{abstention_ok}"
    )

    console.print(
        f"[bold green]FINAL:[/bold green] "
        f"{score}"
    )

    return {

        "case_id": case["case_id"],

        "label": case["label"],

        "question": case["question"],

        "response": response[:500],

        "grounding": grounding,

        "abstention": abstention,

        "score": score,

        "retrieved_sources": list(set(

            c.get(
                "source_file",
                "unknown"
            )

            for c in chunks
        ))
    }

# =========================================================
# MAIN
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--case",
        type=int,
        default=None
    )

    args = parser.parse_args()

    os.makedirs(
        "logs",
        exist_ok=True
    )

    selected_cases = TEST_CASES

    if args.case is not None:

        selected_cases = [

            c for c in TEST_CASES

            if c["case_id"] == args.case
        ]

    all_results = []

    for case in selected_cases:

        try:

            result = run_case(case)

            all_results.append(result)

        except Exception as e:

            console.print(
                f"[red]FAILED CASE "
                f"{case['case_id']}[/red]: {e}"
            )

    # =====================================================
    # SUMMARY TABLE
    # =====================================================

    table = Table(
        title="Evaluation Summary"
    )

    table.add_column("#")
    table.add_column("Label")
    table.add_column("Grounding")
    table.add_column("Abstention")
    table.add_column("Final")

    for r in all_results:

        table.add_row(

            str(r["case_id"]),

            r["label"],

            str(
                r["grounding"].get(
                    "grounding_score"
                )
            ),

            str(
                r["abstention"].get(
                    "correct_abstention"
                )
            ),

            r["score"]
        )

    console.print(table)

    # =====================================================
    # COUNTS
    # =====================================================

    pass_count = len([

        r for r in all_results

        if r["score"] == "PASS"
    ])

    partial_count = len([

        r for r in all_results

        if r["score"] == "PARTIAL"
    ])

    fail_count = len([

        r for r in all_results

        if r["score"] == "FAIL"
    ])

    console.print(
        f"\n[bold green]PASS:[/bold green] "
        f"{pass_count}"
    )

    console.print(
        f"[bold yellow]PARTIAL:[/bold yellow] "
        f"{partial_count}"
    )

    console.print(
        f"[bold red]FAIL:[/bold red] "
        f"{fail_count}"
    )

    # =====================================================
    # SAVE JSON
    # =====================================================

    output = {

        "timestamp": datetime.now().isoformat(),

        "total_cases": len(all_results),

        "pass": pass_count,

        "partial": partial_count,

        "fail": fail_count,

        "cases": all_results
    }

    with open(

        "logs/eval_results.json",

        "w",

        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2
        )

    console.print(
        "\n[bold green]Saved:[/bold green] "
        "logs/eval_results.json"
    )

# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    main()
