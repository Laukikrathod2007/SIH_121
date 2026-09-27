# SIH 26121 — Knowledge Graph Research: Entity Ontologies & GraphRAG

## 1. Executive Summary
This document investigates the application of Knowledge Graphs (KG) and GraphRAG in structuring drilling institutional memory. It defines the formal petroleum engineering ontology, evaluates graph databases (Neo4j) versus relational modeling (PostgreSQL with recursive CTEs and JSONB), and determines the optimal architecture for the prototype and enterprise production.

---

## 2. The Drilling Knowledge Graph Ontology

Drilling experiences are naturally interconnected. A single operational event links subsurface geology, mechanical equipment, chemistry, human decisions, and physical documentation:

```
[WELL] ──(:HAS_WELLBORE)──► [WELLBORE] ──(:PENETRATES)──► [FORMATION]
                                │                              │
                                │                              │ (:OCCURS_IN)
                                ▼                              ▼
                       [CASING_STRING]              [HISTORICAL_EVENT]
                                                            │
                       ┌────────────────────────────────────┼────────────────────────────────────┐
                       ▼ (:CAUSED_BY)                       ▼ (:RESOLVED_BY)                     ▼ (:EVIDENCED_BY)
                  [ROOT_CAUSE]                         [MITIGATION]                        [DOCUMENT_PAGE]
             (Depleted Sand Overbalance)           (Spot 15 m³ LCM Pill)                (NH-09 DDR #42, Page 2)
```

### Core Node Types:
1. `Well`: Surface location, operator, field.
2. `Formation`: Geological stratigraphic horizon (Barail, Kopili, Tipam).
3. `HistoricalEvent`: Standardized complication (Mud Loss, Stuck Pipe, Kick).
4. `RootCause`: Underlying physical failure mode.
5. `Mitigation`: Operational chemical/mechanical countermeasure.
6. `DocumentPage`: Bounding-box audited PDF page.

---

## 3. Technology Comparison: Dedicated Graph DB vs. Relational Schema

| Architectural Dimension | Dedicated Graph Database (Neo4j / Memgraph) | Relational PostgreSQL with Foreign Keys & JSONB |
| :--- | :--- | :--- |
| **Data Model Fit** | Native graph traversal via Cypher queries. | Clean tabular joins, relational foreign keys, JSONB metadata. |
| **Deployment Complexity** | High: Requires separate JVM service, custom cluster setup, and separate auth. | Low: Single robust engine handles relational tables, PostGIS, pgvector, and JSONB! |
| **Query Latency (10–50 Wells)**| $< 10$ ms. | $< 10$ ms (Negligible difference at hackathon/asset scale). |
| **Developer Ecosystem** | Specialized graph query languages. | Standard SQL, universal ORM support (Prisma, SQLAlchemy, Drizzle). |
| **Recommendation** | `[FUTURE ENTERPRISE EXTENSION]` | `[RECOMMENDED MVP ARCHITECTURE]` |

---

## 4. Architectural Verdict for SIH 26121

**Verdict:** `[RELATIONAL-FIRST WITH GRAPH SEMANTICS]`.
- For the SIH prototype, **do NOT add a separate Neo4j database container**. It introduces unnecessary memory overhead, deployment fragility, and network latency.
- Instead, model the graph ontology directly inside **PostgreSQL** using relational foreign keys (`well_id`, `formation_id`, `event_id`, `document_id`) and indexed JSONB columns.
- This gives NWIS **100% of the semantic power of a knowledge graph** while maintaining the simplicity, reliability, and speed of a unified relational database.
