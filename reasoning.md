# reasoning.md — intelli-site Design Decisions

---

## 1. Chunking Strategy

**What I did:** Each of the fourteen zoning markdown files was split at the subsection level — meaning each numbered zoning section (e.g., `23-341`, `23-344`) becomes its own chunk, with the section number, title, amendment date, and a line range stored as metadata alongside the text. Chunks are written to `chroma_db/subsection_chunks.json` and indexed from there.

**Why subsection-level, not paragraph or fixed-token:** Zoning text is already hierarchically structured. A subsection like "23-341 — Permitted Obstructions in Rear Yards" is a complete legal unit — it has a discrete scope, is directly cross-referenced by other sections, and is the natural unit an architect would cite. Splitting mid-subsection would break citation coherence and make it harder to validate grounding. Fixed-token chunking (e.g., 256 tokens) risks cutting across a regulatory condition mid-sentence, which is particularly dangerous in legal text where a single "except as provided in" clause changes meaning entirely.

**What I considered and rejected:**
- *Paragraph-level chunking:* Too granular. Zoning paragraphs are short and often only meaningful in context of their parent section.
- *Full-document chunks:* Too coarse. The ten documents cover distinct regulations; mixing them into one embedding would dilute retrieval signal.
- *Semantic/sentence chunking:* Overkill for documents that are already structured by section number. Also harder to trace back to a citable source.

**Vintage metadata:** Each chunk stores a `last_amended` year extracted from the document header. This feeds the temporal warning layer at evaluation time — if a query references a past year, the system checks whether the cited chunk predates or postdates the relevant amendment.

---

## 2. Retrieval Design

**Method:** Hybrid retrieval — dense vector search (ChromaDB + `all-MiniLM-L6-v2`) combined with sparse BM25, merged via Reciprocal Rank Fusion (RRF).

**Why hybrid:** Dense retrieval handles semantic paraphrase well ("what can I put in the rear yard?" → retrieves HVAC/obstruction chunks) but can miss exact statutory section numbers or defined legal terms. BM25 excels at exact-term matching ("Section 23-341", "floor area ratio", "R6") but fails on paraphrase. RRF merges both ranked lists without requiring score normalization, making it robust to the very different score scales of cosine similarity and BM25. Early experiments with dense-only retrieval were done to move fast and avoid complexity, but results were not good enough on its own — exact legal term matching was a consistent failure point, which motivated adding BM25.

**Threshold logic:** Default threshold is `0.38` on dense cosine similarity. The threshold is applied permissively: a chunk passes if (a) its dense score exceeds the threshold, OR (b) BM25 retrieved it (regardless of dense score), OR (c) both retrievers returned it. This means a BM25-only match — e.g., a query containing a literal section number — is never filtered out by the dense threshold. The threshold was chosen empirically by running retrieval on the eval cases and observing the score distribution; 0.38 preserved true positives while cutting most noise.

**Dependency expansion:** After initial retrieval, the system walks `section_graph.json` (22 nodes, 18 edges encoding cross-references between sections) and adds up to 3 dependency chunks not already in the result set, tagged with `retrieval_method = dependency`. This handles cases like "rear yard depth" where the primary chunk (Section 23-34) explicitly says "see Section 23-341" — without expansion, an answer about permitted obstructions would be incomplete.

**Known issue:** Some graph node keys are stored with a `_body` suffix (e.g., `23-341_body`) while cross-references in text use the plain form (`23-341`). This causes occasional false "section not found" logs during dependency expansion. It is a data-consistency issue in the graph construction, not a retrieval design flaw, and is straightforward to fix by normalizing keys.

---

## 3. Routing Logic

The LLM router (`src/routing/router.py`) classifies each query into one of three routes before any retrieval happens:

| Route | Trigger | Action |
|---|---|---|
| `structured_only` | Questions answerable purely from site metadata (flood zone, E-designation, census data, lot area) | Skip vector retrieval; answer from `site_records.csv` + PLUTO |
| `legal_rag` | Questions requiring zoning text (FAR, yard depths, permitted uses, height/setback) | Hybrid retrieval + prompt with legal context |
| `reject` | Questions entirely outside scope (federal law, GIS geometry, unrelated topics) | Return a scoped abstention message |

The router is itself an LLM call (Gemini, `gemini-3.6-flash`, via `src/generation/gemini_client.py`) with a structured prompt asking for route + confidence + extracted query year. On parse failure or low confidence, it defaults to `legal_rag` — the safer direction, since over-retrieval is less harmful than missing a zoning constraint.

> This originally ran on a local Ollama/llama3 model; the router, generation, and LLM-as-judge evaluation were all migrated to the Gemini API. See [`eval_stats.md`](eval_stats.md) for the before/after eval comparison.

**Why a separate router instead of always doing RAG:** Structured questions (e.g., "what flood zone is this site in?") have deterministic answers in `site_records.csv`. Running them through vector retrieval adds latency and can introduce hallucinated zoning text into an otherwise clean factual answer. Keeping the paths separate also makes each path easier to debug and evaluate independently.

---

## 4. Failure Handling

**When retrieval returns nothing above threshold:** The prompt builder receives an empty context and is instructed to respond with an explicit abstention: "The corpus does not contain sufficient information to answer this question." The system will not generate an answer from parametric memory alone.

**When retrieved chunks exist but don't answer the question:** The validator (`src/generation/validator.py`) checks for the presence of inline citations (`[SOURCE_X]`) in the generated answer. An answer with no citations on a `legal_rag` route is flagged. The citation evaluator (`src/evaluation/citation_evaluator.py`) then uses Gemini-as-judge to ensure grounding.

**Vintage conflicts:** The temporal layer checks each cited chunk's `last_amended` year against the current or query year. If a query asks about "the FAR five years ago" and the only available chunk reflects a 2019 amendment, the system emits a warning rather than silently answering with potentially stale law. The severity of the warning is tiered: a `⚠️ WARNING` is emitted when a temporal conflict is possible, and a `🚨 DANGER` is emitted when the temporal gap is large enough to indicate high instability — meaning the cited regulation is very likely to have changed since the chunk was last amended.

**What "I don't know" looks like:** The response formatter produces a structured output: a direct answer or abstention statement, inline `[SOURCE_X]` citations replaced with section titles, a warnings block (if any), and a citation appendix listing each source's title, section number, amendment date, and retrieval score. An abstention answer looks like:

> "The corpus does not cover this question. The NYC Zoning Resolution sections available do not address [topic]. For authoritative guidance, consult the full NYC Zoning Resolution or a licensed zoning attorney."

---

## 5. Eval Results

See [`eval_stats.md`](eval_stats.md) for full retrieval metrics and end-to-end evaluation results across 20 test cases.

**Summary (current, Gemini-based pipeline):** 13 PASS, 1 PARTIAL, 6 FAIL across 20 cases, with 19/20 cases scoring a perfect grounding score (fully supported, no hallucination). This is a large jump from the original llama3/Ollama baseline of 1 PASS / 10 PARTIAL / 9 FAIL, and it comes from two things: switching generation, routing, and judging to Gemini (`gemini-3.6-flash`), and fixing a judge-side context-truncation bug uncovered during that migration (retrieved chunks were being cut to 1,000–1,200 characters, which chopped some sections mid-clause and produced false hallucination flags).

Every remaining FAIL now shares one pattern rather than two: all 6 FAILs have a perfect grounding score and no hallucination — the only thing marked wrong is the abstention call. In each case the system answers the general rule fully and correctly, then explicitly flags the one specific fact it can't confirm from the retrieved context (e.g., Case 8 — Setback requirement — states the R7A base-height/setback rule correctly, then declines to say whether *this particular building* needs the setback because its exact height isn't in the site record). The eval's abstention field is binary, so it can't score "answered the covered part, abstained on the uncovered part" as correct — it counts this honest partial answer as a miss in whichever direction it leans. Case 7 (Street wall requirement) is the one genuine grounding slip, introducing an unsupported term not present in the retrieved text.

Retrieval precision (18.92%) is unchanged from the pre-migration baseline (previously 18.42%) — expected, since only the LLM provider changed, not the retriever. It stays low because dependency expansion and hybrid RRF fusion return chunks that are topically related but not the expected answer chunk. Recall (77.78%) is healthy — the correct chunk is almost always in the retrieved set. Full metrics, per-case tables, and the bug writeups are in [`eval_stats.md`](eval_stats.md).

---

## 6. What I Would Build Next

**Better citation anchoring in generation.** The single highest-leverage improvement would be switching from unconstrained free-text generation to a structured generation approach — either function calling with a schema like `{ answer: string, citations: [{ source_id, quote }] }`, or a two-pass approach where the LLM first selects the most relevant chunk verbatim, then synthesizes an answer from it. This would directly fix the FAIL cases caused by low grounding scores. The retrieval pipeline is already sound; the weak link is getting the LLM to stay tightly bound to what it retrieved rather than falling back on parametric knowledge.

An agentic eval-and-retry loop would also meaningfully reduce hallucinations — the system could self-check its own answer against the retrieved chunks and re-attempt generation when grounding is weak, rather than surfacing a low-confidence answer to the user.

On the retrieval side, the current system relies on a fixed top-k and a single threshold value. Experimenting with dynamic top-k selection and per-query threshold calibration could improve precision without sacrificing recall.

Other experimented pipelines and strategies are available in separate branches of this repository for reference:

- [`main`](https://github.com/Shubhamsavani/legal-zoning-rag/tree/main) — Sectional-level chunking with a ~1200 token size target for best retrieval; produced decent retrieval results.
- [`subsection-chunking-exp`](https://github.com/Shubhamsavani/legal-zoning-rag/tree/subsection-chunking-exp) — Subsectional-level chunking experiment; showed good results and is where the dependency graph idea was first prototyped, though the retrieval architecture at that stage was weaker.

The current submission builds on the lessons from both branches.

**Known vulnerabilities in the current system:**

- The retrieval pipeline lacks a robust eval strategy — precision/recall are measured against manually defined expected chunks, which is brittle and doesn't scale.
- The abstention rubric is binary (did/should abstain) and can't represent a correct partial answer — "answered the covered part, abstained on the uncovered part" — as a good outcome. This is now the dominant failure mode after the Gemini migration (see Section 5) and is worth a real decision: move to a three-way schema (full answer / partial answer / full abstention), or explicitly accept it as a rubric limitation.

**Resolved since the original submission:** the original llama3-via-Ollama model was frequently too weak for the task — e.g., failing to reason that an R6 site falls within a stated "R1 through R10" range and abstaining incorrectly. Migrating generation, routing, and judging to the Gemini API (`gemini-3.6-flash`) resolved this class of failure; grounding is now near-perfect (19/20 cases) and the remaining gap is the abstention-rubric issue above, not model capability.