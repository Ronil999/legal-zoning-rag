"""
app.py

Run from project root:

streamlit run app.py
"""

import re

import streamlit as st

from src.main import run_intelli_site

from src.response_formatter import (
    build_citation_map,
    replace_inline_citations
)


def strip_orphaned_citations(text: str) -> str:
    """Defensive cleanup: remove any [SOURCE_*] markers that
    survived citation replacement — e.g. the model referenced a
    source that was never actually retrieved (SOURCE_7 when only
    5 chunks came back), or invented a non-numeric marker like
    [SOURCE_SITE_DATA] for structured facts that were never
    assigned a citation ID in the first place."""

    cleaned = re.sub(r"\s*\[SOURCE_[A-Za-z0-9_]*\]", "", text)

    return re.sub(r"\s*\[UNKNOWN_CITATION:[^\]]*\]", "", cleaned)


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(

    page_title="Intelli-Site",

    page_icon="🏙️",

    layout="wide"
)


# =====================================================
# STYLES
# =====================================================

st.markdown(
    """
<style>

.block-container {
    padding-top: 2.2rem;
    max-width: 1100px;
}

.is-eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    font-weight: 600;
    opacity: 0.55;
    margin-bottom: 0.15rem;
}

.is-answer p, .is-answer li {
    font-size: 1.02rem;
    line-height: 1.65;
}

.is-badge-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 0.35rem 0 0.1rem 0;
}

.is-badge {
    display: inline-block;
    padding: 0.18rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: rgba(120, 120, 120, 0.14);
    border: 1px solid rgba(120, 120, 120, 0.22);
}

.is-badge-route-legal_rag {
    background: rgba(59, 130, 246, 0.14);
    border-color: rgba(59, 130, 246, 0.30);
}

.is-badge-route-structured_only {
    background: rgba(16, 185, 129, 0.14);
    border-color: rgba(16, 185, 129, 0.30);
}

.is-badge-route-reject {
    background: rgba(239, 68, 68, 0.14);
    border-color: rgba(239, 68, 68, 0.30);
}

.is-citation {
    display: inline-block;
    padding: 0.05rem 0.45rem;
    border-radius: 5px;
    font-size: 0.82rem;
    font-family: "Source Code Pro", monospace;
    background: rgba(120, 120, 120, 0.14);
    border: 1px solid rgba(120, 120, 120, 0.22);
    white-space: nowrap;
}

.is-source-title {
    font-weight: 600;
    font-size: 0.95rem;
}

.is-source-meta {
    font-size: 0.8rem;
    opacity: 0.65;
    font-family: "Source Code Pro", monospace;
}

.is-method-dense { color: #3b82f6; }
.is-method-bm25 { color: #a855f7; }
.is-method-dense-bm25 { color: #10b981; }
.is-method-dependency { color: #f59e0b; }

hr {
    margin: 1.6rem 0;
    opacity: 0.15;
}

</style>
""",
    unsafe_allow_html=True
)


# =====================================================
# HEADER
# =====================================================

st.title("Intelli-Site")

st.caption(
    "Provenance-aware legal RAG for NYC zoning analysis"
)


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Query Settings")

top_k = st.sidebar.slider(

    "Top-K Retrieval",

    min_value=1,

    max_value=10,

    value=5
)

threshold = st.sidebar.slider(

    "Similarity Threshold",

    min_value=0.0,

    max_value=1.0,

    value=0.38,

    step=0.01
)

show_chunks = st.sidebar.checkbox(

    "Show Retrieved Chunks",

    value=True
)

show_prompt = st.sidebar.checkbox(

    "Show Final Prompt",

    value=False
)

show_debug = st.sidebar.checkbox(

    "Show Debug Info",

    value=False
)


# =====================================================
# INPUTS
# =====================================================

col1, col2 = st.columns([1, 2])

with col1:

    bbl = st.text_input(

        "BBL",

        value="4049630075"
    )

with col2:

    question = st.text_input(

        "Question",

        value=(
            "Can HVAC equipment "
            "project into a "
            "required rear yard?"
        )
    )

run_query = st.button(

    "Run Query",

    type="primary",

    use_container_width=True
)


# =====================================================
# HELPERS
# =====================================================

ROUTE_LABELS = {

    "legal_rag": "Legal Analysis",

    "structured_only": "Structured Lookup",

    "reject": "Rejected"
}

METHOD_LABELS = {

    "dense": "Semantic Match",

    "bm25": "Keyword Match",

    "dense+bm25": "Semantic + Keyword",

    "dependency": "Referenced Section"
}


def route_badge(route: str) -> str:

    label = ROUTE_LABELS.get(
        route,
        route or "unknown"
    )

    css_class = (
        f"is-badge is-badge-route-{route}"
    )

    return (
        f'<span class="{css_class}">{label}</span>'
    )


def method_badge(method: str) -> str:

    label = METHOD_LABELS.get(
        method,
        method or "unknown"
    )

    css_class = (
        "is-method-"
        + (method or "unknown").replace("+", "-")
    )

    return (
        f'<span class="{css_class}">{label}</span>'
    )


# =====================================================
# RUN QUERY
# =====================================================

if run_query:

    with st.spinner("Running Intelli-Site pipeline..."):

        result = run_intelli_site(

            question=question,

            bbl=bbl,

            top_k=top_k,

            threshold=threshold
        )

    route = result.get("route", "")

    # -------------------------------------------------
    # REJECTED QUERY — distinct, minimal state
    # -------------------------------------------------

    if route == "reject":

        st.divider()

        st.markdown(route_badge("reject"), unsafe_allow_html=True)

        st.write("")

        st.info(result.get("answer", "This query could not be processed."))

    else:

        retrieved_chunks = result.get("retrieved_chunks", [])

        site_summary = result.get("site_summary", {}) or {}

        warnings = result.get("warnings", [])

        validation = result.get("validation", {}) or {}

        # ===============================================
        # ANSWER
        # ===============================================

        st.divider()

        st.markdown(
            '<div class="is-eyebrow">Answer</div>',
            unsafe_allow_html=True
        )

        citation_map = build_citation_map(retrieved_chunks)

        clean_answer = replace_inline_citations(

            answer=result.get("answer", ""),

            citation_map=citation_map
        )

        clean_answer = strip_orphaned_citations(clean_answer)

        with st.container(border=True):

            st.markdown(
                f'<div class="is-answer">',
                unsafe_allow_html=True
            )

            st.markdown(clean_answer)

            st.markdown('</div>', unsafe_allow_html=True)

            badges = [route_badge(route)]

            if result.get("query_year"):

                badges.append(
                    f'<span class="is-badge">'
                    f'Query year: {result["query_year"]}'
                    f'</span>'
                )

            if bbl:

                badges.append(
                    f'<span class="is-badge">BBL {bbl}</span>'
                )

            st.markdown(
                '<div class="is-badge-row">'
                + "".join(badges)
                + "</div>",
                unsafe_allow_html=True
            )

        # ===============================================
        # WARNINGS
        # ===============================================

        if warnings:

            st.markdown(
                '<div class="is-eyebrow">Warnings</div>',
                unsafe_allow_html=True
            )

            for w in warnings:

                st.warning(w)

        # ===============================================
        # SITE DATA
        # ===============================================

        site_fields = {

            k: v

            for k, v in site_summary.items()

            if v not in (None, "")
        }

        if site_fields:

            st.markdown(
                '<div class="is-eyebrow">Site Data</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                field_items = list(site_fields.items())

                midpoint = (
                    (len(field_items) + 1) // 2
                )

                col_a, col_b = st.columns(2)

                for col, chunk_items in (

                    (col_a, field_items[:midpoint]),

                    (col_b, field_items[midpoint:])
                ):

                    with col:

                        for key, value in chunk_items:

                            label = (
                                key.replace("_", " ").title()
                            )

                            st.markdown(
                                f"**{label}**  \n{value}"
                            )

        # ===============================================
        # SOURCES
        # ===============================================

        if retrieved_chunks:

            st.markdown(
                '<div class="is-eyebrow">Sources</div>',
                unsafe_allow_html=True
            )

            seen = set()

            for chunk in retrieved_chunks:

                citation_id = chunk.get("citation_id")

                if citation_id in seen:
                    continue

                seen.add(citation_id)

                title = (
                    chunk.get("subsection_title")
                    or chunk.get("section_title")
                    or "Untitled section"
                )

                with st.container(border=True):

                    top_row = st.columns([5, 2])

                    with top_row[0]:

                        st.markdown(
                            f'<span class="is-citation">'
                            f'{citation_id}</span> '
                            f'<span class="is-source-title">'
                            f'{title}</span>',
                            unsafe_allow_html=True
                        )

                    with top_row[1]:

                        st.markdown(
                            method_badge(
                                chunk.get("retrieval_method", "")
                            ),
                            unsafe_allow_html=True
                        )

                    st.markdown(
                        f'<div class="is-source-meta">'
                        f'{chunk.get("source_file", "")} '
                        f'&nbsp;·&nbsp; lines '
                        f'{chunk.get("start_line")}'
                        f'-{chunk.get("end_line")}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    if show_chunks:

                        with st.expander("View chunk text"):

                            st.text(chunk.get("text", ""))

        # ===============================================
        # DEBUG (opt-in)
        # ===============================================

        if show_debug:

            st.markdown(
                '<div class="is-eyebrow">Debug</div>',
                unsafe_allow_html=True
            )

            with st.container(border=True):

                d1, d2, d3 = st.columns(3)

                d1.metric(
                    "Has Citations",
                    "Yes" if validation.get("has_citations") else "No"
                )

                d2.metric(
                    "Abstaining",
                    "Yes" if validation.get("is_abstaining") else "No"
                )

                d3.metric(
                    "Answer Length",
                    validation.get("answer_length", 0)
                )

        if show_prompt:

            st.markdown(
                '<div class="is-eyebrow">Final Prompt</div>',
                unsafe_allow_html=True
            )

            st.code(result.get("prompt", ""))
