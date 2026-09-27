# eRTMAC-NWIS: Modules 2 and 3 — Geospatial Map Intelligence and Knowledge Repository
# Master Document 2 of 6

> An AI reading this file can build Modules 2 and 3 completely.
> Module 2: The interactive geospatial map with formation-aware well coloring and offset ranking.
> Module 3: The searchable RAG knowledge repository with bounding-box proof.

---

## MODULE 2: Map-Based Nearby Well Intelligence

### 2.1 What Module 2 Produces

A live, interactive map of the Upper Assam drilling area that:
  - Shows all known OIL wells as colored markers (color = formation currently being drilled)
  - Updates the active well marker in real time as bit depth advances
  - Draws a radius ring that adjusts automatically based on formation type
  - Shows fault polygon overlays that block correlation across faults
  - Renders the Omega-ranked offset wells with NPT event history popups
  - Allows the drilling engineer to click any offset well and see its DDR history

### 2.2 Why Euclidean Distance Alone Fails (and How We Fix It)

PROBLEM: A well 2 km away on the OTHER SIDE of the Naga-Duliajan thrust fault has
ZERO geological relevance — the formations were disrupted by the fault and do not
connect hydraulically or structurally. A well 8 km away in the same fault block
has HIGH relevance if it drilled the same formation.

NAIVE SOLUTION (wrong): "Find all wells within 5 km radius" — includes irrelevant
fault-block neighbors, excludes relevant distant same-block wells.

NWIS SOLUTION:
  1. Load simplified fault polygons for the Upper Assam shelf (from published OIL
     structural maps, vectorized as PostGIS geometry).
  2. Before including any offset well in the ranking, check:
     ST_Within(active_well_point, fault_block_polygon) ==
     ST_Within(offset_well_point, same_fault_block_polygon)
     If FALSE: offset well is in different fault block -> excluded from ranking (or ranked
     at the bottom with explicit warning: "CROSS-FAULT — geological uncertainty HIGH").
  3. Use PostGIS ST_Distance for the actual proximity score within a confirmed same-block search.

### 2.3 PostGIS Spatial Queries

  -- Find offset wells within 50 km in same fault block as active well:
  SELECT
      w.well_id,
      w.well_name,
      w.field_name,
      ST_Distance(w.geom::geography, aw.geom::geography) / 1000.0 AS distance_km,
      fb.block_name
  FROM wells w
  JOIN wells aw ON aw.well_id = %(active_well_id)s
  JOIN fault_blocks fb ON ST_Within(w.geom, fb.geom)
  JOIN fault_blocks fb2 ON ST_Within(aw.geom, fb2.geom)
  WHERE
      ST_DWithin(w.geom::geography, aw.geom::geography, 50000)  -- 50 km radius
      AND fb.block_id = fb2.block_id  -- same fault block
      AND w.well_id != aw.well_id
      AND w.status = 'COMPLETED'
  ORDER BY distance_km ASC;

  -- Spatial index required (create once):
  CREATE INDEX wells_geom_idx ON wells USING GIST (geom);
  CREATE INDEX fault_blocks_geom_idx ON fault_blocks USING GIST (geom);

### 2.4 Frontend Map Technology

  Framework: Leaflet.js with react-leaflet wrapper
  Base tiles: Offline tiles from OpenStreetMap (mbtiles format for air-gapped deployment)
              OR mapbox-gl-js with locally hosted vector tiles
  CRS: EPSG:4326 (WGS84 lat/lon)

  Well Marker Colors (color by formation currently being drilled):
    Gurjan/Girujan (surface clays):  GRAY (#9E9E9E)
    Tipam Sandstone:                 ORANGE (#FF9800) — lost circulation risk
    Surma Group:                     YELLOW (#FFEB3B)
    Barail Lower Sand:               GREEN (#4CAF50) — primary reservoir
    Barail Coal-Shale:               BROWN (#795548) — stuck pipe risk
    Kopili Formation:                RED (#F44336) — overpressure risk
    Unknown/Surface:                 GRAY (#9E9E9E)

  Active Well: Pulsing green circle animation (CSS keyframe)
  Top 5 Offset Wells: Blue pin markers with Omega score badge
  NPT Event Wells: Red triangle markers (scaled by event severity)

### 2.5 Formation-Aware Radius Adjustment

  The search radius should shrink in geologically complex zones:
    Tipam Sandstone:   50 km radius (formation is laterally consistent)
    Barail Lower Sand: 30 km radius (more lateral variability)
    Barail Coal-Shale: 15 km radius (coal seam geometry is highly local)
    Kopili/Sylhet:     10 km radius (deep, structurally complex)

  Implemented as a configurable lookup:
  FORMATION_SEARCH_RADIUS = {
      "Gurjan": 50, "Girujan": 50, "Tipam": 50,
      "Surma": 30, "Barail_Lower": 30,
      "Barail_Coal": 15, "Kopili": 10, "Sylhet": 10
  }

### 2.6 Map Layer Controls

  Layer 1 (always on): Wellhead locations
  Layer 2 (toggle): NPT event heatmap (kernel density estimation of all events)
  Layer 3 (toggle): Formation contour lines (Tipam Sandstone top in TVDSS, from kriging)
  Layer 4 (toggle): Fault polygon overlays
  Layer 5 (toggle): Active well bit path (3D trajectory projected to surface as dotted line)
  Layer 6 (toggle): Seismic survey coverage polygons (if available)

### 2.7 Well Popup on Click

  When engineer clicks any offset well marker, popup shows:
  +-----------------------------------------+
  | NHK-089 — Nahorkatiya Field             |
  | Drilled: 2015 | TD: 4,210 m MD          |
  | Current Formation: Barail Lower Sand     |
  | Omega Score: 0.87 (Rank #1)             |
  +-----------------------------------------+
  | NPT Events at Current Zone (xi ±0.1):   |
  | - Lost Circulation @ 3,228 m TVDSS      |
  |   Severity: 4/5 | Duration: 8.5 hrs    |
  |   "Mixed 30 bbl nut plug..."            |
  |   [View DDR PDF] <-- opens Module 3     |
  +-----------------------------------------+
  | Formation Tops:                         |
  | Tipam: 1,612 m TVDSS                   |
  | Barail Lower: 3,180 m TVDSS            |
  | Barail Coal: 3,890 m TVDSS             |
  +-----------------------------------------+

---

## MODULE 3: Searchable Drilling Knowledge Repository

### 3.1 What Module 3 Produces

A production-ready knowledge repository that:
  - Indexes every OCR-extracted text passage from the DDR/WCR corpus
  - Supports semantic search (vector similarity) for geology-aware queries
  - Returns results with 1-click PDF highlight (bounding box proof)
  - Runs entirely on-premise (no OpenAI API calls in the demo path)
  - Gives the drilling engineer instant access to 50 years of institutional knowledge

### 3.2 The RAG Architecture (Retrieval-Augmented Generation)

  QUERY: "What happened when drilling through Barail Coal shale in Nahorkatiya?"

  Step 1 — Encode query to vector:
    query_vector = encoder.encode(query)  # 768-dimensional vector

  Step 2 — PostgreSQL + pgvector similarity search:
    SELECT chunk_id, doc_id, page_number, chunk_text, bbox_x0, bbox_y0, bbox_x1, bbox_y1,
           (1 - (embedding <=> query_vector)) AS cosine_similarity
    FROM document_chunks
    WHERE cosine_similarity > 0.65
    ORDER BY cosine_similarity DESC
    LIMIT 10;

  Step 3 — Apply metadata filters:
    Filter by well_field (Nahorkatiya wells only if requested)
    Filter by formation_name (Barail Coal-Shale context chunks only)
    Filter by npt_type (STUCK_PIPE chunks only)
    This avoids returning generic mud weight paragraphs that are not relevant.

  Step 4 — Generate answer with LOCAL LLM (llama.cpp or Ollama):
    context = "\n\n".join([chunk.chunk_text for chunk in retrieved_chunks[:5]])
    prompt = f"""You are an expert OIL drilling engineer. Using ONLY the following
    drilling reports, answer the question. Do NOT add information not in the reports.
    Do NOT give numerical recommendations not explicitly stated.

    REPORTS:
    {context}

    QUESTION: {query}

    ANSWER:"""
    answer = local_llm.generate(prompt, max_tokens=400, temperature=0.1)

  Step 5 — Return structured response:
    {
      "answer": "In DDR NHK-089-2015-Day-142, total mud losses of 45 bbl/hr were recorded
                 while drilling the Barail Coal-Shale at 3,228 m TVDSS. The crew mixed
                 30 bbl medium nut plug LCM pill...",
      "source_documents": [
        {
          "doc_id": "NHK089_DDR_2015_D142",
          "page": 2,
          "confidence": 0.91,
          "highlight_bbox": [124, 340, 520, 360],
          "pdf_url": "/api/docs/NHK089_DDR_2015_D142.pdf"
        }
      ]
    }

### 3.3 The Local LLM Choice (Critical: No Cloud API)

For air-gapped deployment, we use a LOCALLY HOSTED small language model.
Options (in order of preference for this use case):

  Option A — Ollama + LLaMA 3.1 8B (RECOMMENDED for demo):
    ollama serve  # starts local server
    ollama pull llama3.1:8b
    API: http://localhost:11434/api/generate (compatible with OpenAI API format)
    Latency: 2-8 seconds on CPU (acceptable for query response)
    VRAM: 6 GB GPU or 16 GB RAM for CPU inference

  Option B — llama.cpp with quantized model (4-bit GGUF):
    Runs on CPU-only laptop with 8 GB RAM.
    Models: Mistral-7B-Instruct-v0.3.Q4_K_M.gguf or llama-3.1-8b-instruct.Q4_K_M.gguf
    Latency: 5-15 seconds on a modern laptop CPU.

  Option C — SentenceTransformers + template response (no LLM):
    If LLM is too slow for demo environment, skip generation step.
    Return the top-3 retrieved passages verbatim with bounding box highlights.
    This is simpler and MORE DEFENSIBLE to jury ("no hallucination possible").

### 3.4 Embedding Model (for Vector Search)

  Recommended: sentence-transformers/all-MiniLM-L6-v2
    Dimension: 384 (smaller, faster)
    License: Apache 2.0 (open, air-gap compatible)
    Inference: 50ms per chunk on CPU

  Alternative: intfloat/e5-small-v2 (better for technical/domain text)
    Dimension: 384
    License: MIT

  Petroleum-domain fine-tuned option: PetroSage embeddings (research models from SPE papers)
  Note: General embedding models work adequately for drilling text. Domain fine-tuning
  is nice-to-have but not required for a working demo.

  Indexing setup:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Index all document chunks (run once):
    for chunk in document_chunks:
        embedding = model.encode(chunk.text)
        db.execute("UPDATE document_chunks SET embedding = %s WHERE chunk_id = %s",
                   (embedding.tolist(), chunk.chunk_id))

### 3.5 Petroleum-Domain Query Enhancement

  Raw engineer query: "mud losses in Barail"
  Enhanced query: "lost circulation mud loss total loss partial loss Barail Group
                   Barail Lower Arenaceous Unit Main Pay Sand Tipam Sandstone drilling fluid"

  Enhancement is done by a simple keyword expansion dictionary:
  QUERY_EXPANSION = {
      "barail": ["Barail Group", "Barail Lower Arenaceous", "Main Pay Sand", "Rudrasagar"],
      "mud loss": ["lost circulation", "total loss", "partial loss", "LCM", "nut plug"],
      "stuck": ["stuck pipe", "differential sticking", "key seat", "pack off"],
      "kick": ["gas kick", "influx", "well control", "shut-in", "BOP"],
  }

### 3.6 The 1-Click PDF Bounding Box Proof

This is a key differentiator — judges need to see that answers are GROUNDED in real documents.

  Frontend implementation:
  1. RAG response includes: {doc_id, page_number, bbox: [x0, y0, x1, y1]}
  2. Engineer clicks "View Source" button next to any answer.
  3. PDF viewer opens (pdf.js embedded in the React app).
  4. Page jumps to page_number.
  5. A yellow highlight rectangle is drawn at coordinates [x0, y0, x1, y1] on the page.
  6. The highlighted text IS the exact sentence the AI used to generate the answer.

  Backend endpoint:
  GET /api/docs/{doc_id}/page/{page_number}?highlight_bbox=124,340,520,360
  Returns: rendered PDF page as PNG with yellow highlight rectangle overlaid.

  Alternative (simpler): Return the raw PDF page image from PyMuPDF with
  a highlight rectangle drawn in Python (cv2.rectangle or PIL.ImageDraw).

### 3.7 Module 3 Search Interface

  The search panel (right sidebar in cockpit) has two modes:

  Mode 1 — Free Text Search:
  Engineer types: "What mud weight to use in Barail Coal?"
  System returns: Top 5 DDR passages + LLM-synthesized answer + source buttons.

  Mode 2 — Formation + Event Filter:
  Dropdown: Formation = "Barail Coal-Shale"
  Dropdown: Event Type = "Stuck Pipe"
  Date range: 2010 - 2024
  Radius: 10 km
  Returns: All NPT events matching criteria, sorted by severity, with source DDR links.

  Mode 3 — Active Well Auto-Query (the smart mode):
  When telemetry shows the active well approaching a known hazard depth,
  Module 3 AUTOMATICALLY runs a query without engineer input:
  "What happened in Barail Coal-Shale zone in wells ranked in top 5 by Omega?"
  The results panel pre-loads the answer so it is ready when the engineer needs it.
  This is the "proactive intelligence" capability that SIH judges will notice.

### 3.8 Module 3 Validation Criteria

Test 1 — Retrieval Precision:
  Given 10 known DDR passages with specific NPT events, query for each event type.
  Acceptance: 8/10 relevant passages appear in top 5 results (Precision@5 >= 0.80)

Test 2 — Hallucination Check:
  Ask a question for which NO DDR document contains the answer.
  Acceptance: System returns "No relevant records found" — does NOT fabricate an answer.
  Implementation: If max cosine_similarity < 0.60, return "No relevant records" message.

Test 3 — Bounding Box Accuracy:
  For 5 verified passages, confirm the rendered highlight covers the correct text.
  Acceptance: Highlighted region visually contains the target sentence.

Test 4 — Latency:
  Full query (embed + search + LLM generate + response): < 10 seconds.
  Retrieval only (embed + search, no LLM): < 1 second.
  Acceptance: End-to-end < 10 seconds for conversational use.
