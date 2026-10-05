# SIH 26121 — RAG Architecture & Historical Institutional Knowledge

## 1. Executive Summary
This document analyzes the retrieval architectures applicable to mission-critical drilling operations. It exposes why generic vector Retrieval-Augmented Generation (RAG) fails in petroleum engineering and designs a **Hybrid Tool-Augmented RAG Architecture** that combines SQL parametric filtering, BM25 domain tokenization, dense semantic vector search, and strict citation guardrails to guarantee zero hallucination.

---

## 2. Why Generic Vector RAG Fails in Drilling Operations

Most AI hackathon projects rely on "Naive RAG":
$$\text{Query} \xrightarrow{\text{Embedding}} \text{Cosine Search on Chunks} \xrightarrow{\text{Top 3 Chunks}} \text{LLM Output}$$

In drilling engineering, Naive RAG causes catastrophic operational failures:

```
[FAILURE SCENARIO 1: THE DEPTH INVERSION TRAP]
Query: "Show mud loss incidents in the Barail Sandstone between 3,100 m and 3,300 m."
- Naive vector search returns a chunk from Well 14 mentioning "severe mud loss in Barail Sandstone at 2,450 m" because the semantic embedding matches strongly.
- The LLM merges the text and reports that losses occur at 3,150 m. The engineer acts on false depth advice!

[FAILURE SCENARIO 2: NUMERICAL HALLUCINATION]
Query: "What mud weight was used to cure the kick in Well NH-05?"
- Context chunk states: "Spotted 15 m3 heavy pill. Mud weight in pits was 1.25 SG; weighted to 1.34 SG."
- LLM outputs: "A mud weight of 1.45 SG was used."
- An unnecessary 0.11 SG over-weighting in a narrow-margin well will fracture the formation, causing total lost circulation!
```

---

## 3. The 4-Tier Hybrid Retrieval Architecture

NWIS abandons naive vector search in favor of a **Deterministic-First Hybrid Retrieval Engine**:

```
[DRILLING ENGINEER QUERY]
"Show me mud loss mitigations in Barail formation with mud weight > 1.30 SG"
       │
       ▼
[TIER 1: QUERY INTENT & PARAMETER EXTRACTION]
Deterministic regex & semantic parser extracts structured SQL constraints:
├── Formation = "Barail Coal-Shale" OR "Barail Sand"
├── Event_Category = "LOST_CIRCULATION"
└── Mud_Weight >= 1.30 SG
       │
       ▼
[TIER 2: RELATIONAL PARAMETRIC FILTERING (SQL PRE-FILTER)]
Executes hard SQL query over structured relational database:
`SELECT event_id, narrative_chunk_id FROM events WHERE formation = 'Barail' AND mw >= 1.30;`
Reduces 50,000 document chunks down to 18 physically valid candidates!
       │
       ▼
[TIER 3: HYBRID RANKING FUSION (SPARSE + DENSE)]
Across the 18 candidates, executes dual ranking:
├── Sparse (BM25): Matches exact domain acronyms ("LCM", "nut plug", "calcium carbonate").
└── Dense (pgvector / Sentence-Transformers): Matches semantic intent ("curing losses").
Combined via Reciprocal Rank Fusion (RRF):
$$RRF\_Score(d) = \sum_{m \in \{BM25, Dense\}} \frac{1}{60 + \text{Rank}_m(d)}$$
       │
       ▼
[TIER 4: CONSTRAINED CITATION-GROUNDED LLM GENERATION]
Prompts LLM with strict deterministic instructions:
"Answer using ONLY the provided facts. Quote the exact report page.
If the information is missing, output: 'INSUFFICIENT HISTORICAL EVIDENCE'."
```

---

## 4. Citation Grounding & Hallucination Guardrails

To meet industrial reliability criteria, NWIS enforces five non-negotiable guardrails:

1. **Temperature Zero ($T = 0.0$):** Eliminates stochastic sampling variance in technical answers.
2. **Explicit Numerical Provenance:** Every numerical entity (depth, mud weight, pressure, volume) generated in the text must be an exact substring of the retrieved source text. If a number does not appear in the context, the response is rejected by a post-generation regex validator.
3. **Mandatory Page & Well ID Metadata:** The LLM is structurally barred from generating a recommendation without appending the source citation badge:
   `[Well: OIL-NH-09 | DDR #42 | Page 2 | Depth: 3,224 m MD]`
4. **"Insufficient Historical Evidence" Fallback:** If the database contains fewer than two comparable offset records, the system explicitly outputs:
   > ⚠️ *"INSUFFICIENT HISTORICAL EVIDENCE IN OFFSET REPOSITORY. No comparable offset well has penetrated this formation under the specified parameters. Rely on real-time LWD/MWD formation evaluation."*
   This prevents the system from fabricating confidence when entering an un-drilled frontier block.
5. **Human-in-the-Loop Verification Button:** Every AI-generated synthesis includes a one-click button: *"Open Original Report Page"*, jumping directly to the highlighted scanned PDF.
