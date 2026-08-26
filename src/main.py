"""
src/main.py

Main orchestration pipeline for Intelli-Site.

Pipeline:
1. LLM routing
2. Structured retrieval
3. Hybrid legal retrieval
4. Prompt construction
5. Llama3 generation
6. Validation
7. Citation evaluation
8. Temporal evaluation
9. Final response formatting
"""

import re

from pprint import pprint

from src.routing.router import (
    route_query
)

from src.structured.retrieval import (
    get_complete_site_profile,
    summarize_site_profile
)

from src.retrieval.retriever import (
    retrieve_chunks
)

from src.prompt_builder import (
    build_prompt
)

from src.generation.llm import (
    generate_answer
)

from src.generation.validator import (
    validate_answer
)

from src.evaluation.citation_evaluator import (
    evaluate_citations
)

from src.evaluation.temporal_layer import (
    evaluate_temporal_risk
)

from src.response_formatter import (
    format_response
)

from src.logging.pipeline_logger import (
    log_pipeline_run
)

import time

pipeline_start = time.time()

# ─────────────────────────────────────────────────────
# RETRIEVAL CONFIG
# ─────────────────────────────────────────────────────

TOP_K = 5

THRESHOLD = 0.38

# ─────────────────────────────────────────────────────
# OPTIONAL BBL EXTRACTION
# ─────────────────────────────────────────────────────

def extract_bbl_from_question(
    question: str
):

    match = re.search(
        r"\b\d{10}\b",
        question
    )

    if match:

        return match.group(0)

    return None

# ─────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────

def run_intelli_site(

    question: str,

    bbl: str = None,

    top_k: int = TOP_K,

    threshold: float = THRESHOLD
):

    pipeline_start = time.time()

    print("\n" + "=" * 80)

    print("INTELLI-SITE PIPELINE")

    print("=" * 80)

    print("\nQUESTION:\n")

    print(question)

    # -------------------------------------------------
    # BBL EXTRACTION
    # -------------------------------------------------

    if not bbl:

        bbl = extract_bbl_from_question(
            question
        )

    print("\nBBL:\n")

    print(bbl)

    # -------------------------------------------------
    # ROUTER
    # -------------------------------------------------

    print(
        "\n[STEP 1] "
        "LLM routing..."
    )

    routing = route_query(
        question
    )

    # print("\nROUTER DECISION:\n")

    # pprint(routing)

    route = routing["route"]

    query_year = routing.get(
        "query_year"
    )

    # print("\nTEMPORAL YEAR:\n")

    # print(query_year)

    # -------------------------------------------------
    # REJECT ROUTE
    # -------------------------------------------------

    if route == "reject":

        rejection = {

            "question": question,

            "route": "reject",

            "answer": (

                "This query does not appear "

                "to be related to NYC zoning "

                "or site analysis."
            )
        }

        print("\n" + "=" * 80)

        print("QUERY REJECTED")

        print("=" * 80)

        print("\n")

        print(rejection["answer"])

        return rejection

    # -------------------------------------------------
    # STRUCTURED RETRIEVAL
    # -------------------------------------------------

    site_summary = {}

    if bbl:

        print(
            "\n[STEP 2] "
            "Structured retrieval..."
        )

        profile = get_complete_site_profile(
            bbl
        )

        site_summary = summarize_site_profile(
            profile
        )

        # print(
        #     "\nSTRUCTURED SITE SUMMARY:\n"
        # )

        # pprint(site_summary)

    else:

        print(
            "\n[INFO] "
            "No BBL available."
        )

    # -------------------------------------------------
    # LEGAL RETRIEVAL
    # -------------------------------------------------

    retrieved_chunks = []

    warnings = []

    if route == "legal_rag":

        print(
            "\n[STEP 3] "
            "Hybrid legal retrieval..."
        )

        retrieved_chunks, warnings = retrieve_chunks(

            question=question,

            top_k=top_k,

            threshold=threshold
        )

        # print(
        #     f"\nRetrieved "
        #     f"{len(retrieved_chunks)} "
        #     f"chunks"
        # )

        # print("\nRETRIEVED CHUNKS:\n")

        # for chunk in retrieved_chunks:

        #     print(

        #         f"{chunk['citation_id']} | "

        #         f"{chunk['source_file']} | "

        #         f"{chunk['subsection_title']} | "

        #         f"{chunk['retrieval_method']}"
        #     )

    else:

        print(
            "\n[INFO] "
            "Skipping legal retrieval "
            "(structured_only route)."
        )

    # -------------------------------------------------
    # WARNINGS
    # -------------------------------------------------

    # print("\nWARNINGS:\n")

    # if warnings:

    #     for w in warnings:

    #         print("-", w)

    # else:

    #     print("None")

    # -------------------------------------------------
    # PROMPT BUILDING
    # -------------------------------------------------

    print(
        "\n[STEP 4] "
        "Building grounded prompt..."
    )

    prompt = build_prompt(

        question=question,

        route=route,

        site_summary=site_summary,

        retrieved_chunks=retrieved_chunks,

        warnings=warnings
    )

    # print(
    #     f"\nPrompt length: "
    #     f"{len(prompt)} chars"
    # )

    # -------------------------------------------------
    # GENERATION
    # -------------------------------------------------

    print(
        "\n[STEP 5] "
        "Generating answer with Gemini..."
    )

    answer = generate_answer(
        prompt
    )

    # print("\nRAW ANSWER:\n")

    # print(answer)

    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    print(
        "\n[STEP 6] "
        "Validating response..."
    )

    validation = validate_answer(
        answer
    )

    # print("\nVALIDATION:\n")

    # pprint(validation)

    # -------------------------------------------------
    # CITATION EVALUATION
    # -------------------------------------------------

    citation_evaluation = {}

    if route == "legal_rag":

        print(
            "\n[STEP 7] "
            "Evaluating citations..."
        )

        citation_evaluation = evaluate_citations(

            answer=answer,

            retrieved_chunks=retrieved_chunks
        )

        # print("\nCITATION EVALUATION:\n")

        # pprint(citation_evaluation)

    else:

        print(
            "\n[INFO] "
            "Skipping citation evaluation "
            "(structured_only route)."
        )

    # -------------------------------------------------
    # TEMPORAL EVALUATION
    # -------------------------------------------------

    temporal_warnings = []

    if route == "legal_rag":

        print(
            "\n[STEP 8] "
            "Evaluating temporal reliability..."
        )

        temporal_warnings = evaluate_temporal_risk(

            answer=answer,

            retrieved_chunks=retrieved_chunks,

            query_year=query_year
        )

        print("\nTEMPORAL WARNINGS:\n")

        if temporal_warnings:

            for w in temporal_warnings:

                print("-", w)

        else:

            print("None")

    # -------------------------------------------------
    # MERGE WARNINGS
    # -------------------------------------------------

    final_warnings = warnings + temporal_warnings

    # -------------------------------------------------
    # RESPONSE FORMATTER
    # -------------------------------------------------

    print(
        "\n[STEP 9] "
        "Formatting final response..."
    )

    formatted_response = format_response(

        answer=answer,

        retrieved_chunks=retrieved_chunks,

        warnings=final_warnings
    )

    # -------------------------------------------------
    # LOGGING
    # -------------------------------------------------

    runtime_seconds = (
        time.time() - pipeline_start
    )

    log_pipeline_run(

        question=question,

        bbl=bbl,

        route_result=routing,

        retrieved_chunks=retrieved_chunks,

        warnings=final_warnings,

        temporal_warning=(
            temporal_warnings
        ),

        validation=validation,

        final_answer=formatted_response,

        runtime_seconds=runtime_seconds
    )

    # -------------------------------------------------
    # FINAL OUTPUT
    # -------------------------------------------------

    print("\n")

    print(formatted_response)

    # -------------------------------------------------
    # RETURN OBJECT
    # -------------------------------------------------

    return {

        "question": question,

        "route": route,

        "routing": routing,

        "query_year": query_year,

        "bbl": bbl,

        "site_summary": site_summary,

        "retrieved_chunks": retrieved_chunks,

        "warnings": final_warnings,

        "prompt": prompt,

        "answer": answer,

        "formatted_response": formatted_response,

        "validation": validation,

        "citation_evaluation": (
            citation_evaluation
        ),

        "temporal_warnings": (
            temporal_warnings
        )
    }
# ─────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────────────

if __name__ == "__main__":

    QUESTION = (

        "What was the FAR in 2015 "
        "for BBL 1016800019?"
    )

    run_intelli_site(

        question=QUESTION
    )