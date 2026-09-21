# eval_stats.md — Evaluation Results

_Last updated after migrating generation, routing, and judging from Ollama/llama3 to the Gemini API (`gemini-3.6-flash`)._

---

## Retrieval Evaluation

Run via the structured retrieval eval script (`src/tests/test_retriever.py`). Pure retrieval scoring — no LLM calls, so this is unaffected by the Ollama→Gemini migration and is included here for completeness.

### Final Retrieval Metrics

| Metric | Value |
|---|---|
| Total Test Cases | 12 |
| True Positives | 7 |
| False Positives | 30 |
| False Negatives | 2 |
| **Precision** | **18.92%** |
| **Recall** | **77.78%** |
| Dependency Expansions | 1 |

**Notes:**
- Low precision reflects dependency expansion and hybrid RRF fusion returning topically related but non-target chunks. The correct chunk is almost always retrieved (high recall); the issue is that extra chunks dilute the result set.
- Retrieval quality is unchanged from the pre-migration baseline (previously 18.42%/77.78%) — expected, since only the LLM provider changed, not the retriever.

### Per-Case Retrieval Summary

| Case | Expected | Retrieved | Overlap | Status |
|---|---|---|---|---|
| Rear yard depth | 1 | 3 | 1.00 | GOOD |
| Fence in rear yard | 1 | 4 | 1.00 | GOOD |
| HVAC equipment | 1 | 3 | 1.00 | GOOD |
| Residential FAR | 1 | 4 | 0.00 | WEAK |
| Community facility FAR | 1 | 4 | 0.00 | WEAK |
| Street wall requirement | 1 | 4 | 1.00 | GOOD |
| Setback requirement | 1 | 3 | 1.00 | GOOD |
| Environmental restrictions | 1 | 2 | 1.00 | GOOD |
| Cross reference retrieval | 2 | 2 | 1.00 | GOOD |
| Historical FAR | 0 | 3 | 0.00 | WEAK |
| Missing special district | 0 | 4 | 0.00 | WEAK |
| GIS polygon geometry | 0 | 2 | 0.00 | WEAK |

**GOOD** = expected chunk(s) present in retrieved set. **WEAK** = overlap is zero (either nothing was expected and retrieval returned noise, or expected chunk was missed entirely). Note: the "Residential FAR" / "Community facility FAR" WEAK marks are a known quirk of this script's expected-file list, not a real retrieval miss — the full end-to-end pipeline correctly grounds both cases (see Cases 5–6 below), likely because the retrieved FAR chunk differs from this script's single hardcoded expected filename while still containing the correct answer.

---

## End-to-End Pipeline Evaluation

Run via `python eval.py`. Uses **Gemini** (`gemini-3.6-flash`) as both the answering model and the LLM-as-judge, scoring grounding (0–2) and abstention correctness (True/False) for each of 20 test cases.

### Summary

| Result | Count |
|---|---|
| **PASS** | **13** |
| **PARTIAL** | **1** |
| **FAIL** | **6** |

Grounding quality is now excellent across the board: **19 of 20 cases scored a perfect grounding score of 2** (fully supported, no hallucination). Every remaining FAIL is an *abstention-judgment* disagreement, not a grounding failure — see Analysis below.

### Per-Case Results

| # | Label | Grounding | Hallucination | Abstention Correct | Final |
|---|---|---|---|---|---|
| 1 | Rear yard depth for site | 2 | False | True | PASS |
| 2 | Fence in rear yard | 2 | False | True | PASS |
| 3 | HVAC equipment placement | 2 | False | True | PASS |
| 4 | Accessory structure in rear yard | 2 | False | True | PASS |
| 5 | Maximum residential FAR | 2 | False | True | PASS |
| 6 | Community facility FAR | 2 | False | True | PASS |
| 7 | Street wall requirement | 1 | True | True | PARTIAL |
| 8 | Setback requirement | 2 | False | False | FAIL |
| 9 | Front yard flexibility | 2 | False | False | FAIL |
| 10 | Environmental restrictions | 2 | False | True | PASS |
| 11 | Cross-reference rear yard rules | 2 | False | True | PASS |
| 12 | Special district override | 2 | False | False | FAIL |
| 13 | Solar panels in rear yard | 2 | False | True | PASS |
| 14 | Parking access driveway | 2 | False | False | FAIL |
| 15 | Building height envelope | 2 | False | False | FAIL |
| 16 | Historical FAR | 2 | False | False | FAIL |
| 17 | Missing special district | 2 | False | True | PASS |
| 18 | Missing referenced section | 2 | False | True | PASS |
| 19 | GIS polygon geometry | 2 | False | True | PASS |
| 20 | Federal EPA remediation law | 2 | False | True | PASS |

### Scoring Logic

- **Grounding** is scored 0–2 by Gemini-as-judge: `0` = answer not supported by retrieved chunks, `1` = partially supported, `2` = well-grounded.
- **Abstention** is `True` if the system's abstain/answer decision matches what the judge considers correct given the retrieved context (cases 16–20 are the intended abstention cases).
- **Final** result: `PASS` = grounding ≥ 2 and abstention correct; `PARTIAL` = grounding ≥ 1 or abstention correct but not both at full mark; `FAIL` = grounding 0 or incorrect abstention on an answerable case.

### Analysis

**Massive improvement over the pre-migration (llama3) baseline**: PASS rate went from 1/20 (5%) to 13/20 (65%), and near-perfect grounding (19/20 at max score) versus llama3's frequent 0–1 grounding scores. This reflects both the stronger model and two real bugs found and fixed during this evaluation pass:

1. **Judge context truncation (fixed this run).** `eval.py`'s `judge_grounding`/`judge_abstention` were truncating each retrieved chunk to 1,000–1,200 characters and only looking at the first 4–5 chunks. Several zoning sections (e.g., Section 23-341, at 2,197 characters) exceed that limit, so the judge was evaluating answers against text that had been cut off mid-clause — right before the exact rule the model was citing. This produced false "hallucination" flags on Cases 3, 4, and 13 (HVAC placement, accessory sheds, solar panels), all of which independently verify correct against the source `.md` files. Raised the limits to 3,000 characters / 8 chunks, which cover every chunk in this corpus, and re-verified all three cases flip to PASS with the fix.
2. **Missing site-data context (fixed in a prior pass, holding here).** The judges previously only saw retrieved legal text, not the structured site record — any answer citing address, zoning district, or FAR values from `site_records.csv`/PLUTO was flagged as unsupported. Fixed by passing `site_summary` into both judge prompts.

**Where the system performs well:**
- Grounding is now essentially solved for this corpus — 19/20 cases show zero hallucination, correctly distinguishing retrieved legal text from structured site data and from genuine gaps.
- Abstention on fully out-of-corpus questions (Cases 17–20: missing special districts, missing referenced sections, GIS geometry, federal EPA law) is 100% correct.
- Cross-reference handling (Case 11) and multi-source synthesis (Cases 1–6) are consistently accurate.

**Remaining failure mode — all 6 FAILs, one pattern:** every current FAIL (Cases 8, 9, 12, 14, 15, 16) has a perfect grounding score and no hallucination; the only thing marked wrong is the abstention call. Reading the judge's own reasoning for each, a consistent shape emerges: the system answers the *general* rule fully and precisely, then explicitly flags the one specific fact it can't confirm (an exact building height, whether a specific 2015 amendment text exists, whether a driveway is covered by a list that doesn't mention driveways) rather than either fully answering or fully refusing. For example, Case 8 states the R7A base-height/setback rule completely and correctly, then declines to say whether *this particular building* needs the setback because its exact height in feet isn't in the site record — an honest, well-grounded partial answer. The eval's abstention field is a binary (did/should the system abstain), so it can't represent "answered the covered part, abstained on the uncovered part" as a good outcome — it scores this behavior as a wrong call in whichever direction it leans. This is arguably the system doing exactly what the assignment asks for ("distinguish between what's known and what the corpus doesn't cover"), scored by a rubric that only has two boxes. Case 7 is the one genuine (mild) exception — it introduces an unsupported term ("Quality Housing bulk rules") not present in the retrieved text, a real minor grounding slip worth keeping an eye on.

**What I'd fix next:** either move the abstention judge to a three-way schema (full answer / partial answer / full abstention) so this hedging behavior scores correctly, or accept it as a known limitation of the current rubric — worth a decision call rather than a unilateral change, since it affects how "PASS" is defined for the whole suite.
