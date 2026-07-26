# Project Matilda — Architectural Blueprint

## Central Architectural Axiom
> The LLM should not determine historical truth. Historical claims should come from structured knowledge and verifiable evidence. LLMs may assist with contextual classification and grounded explanation.

---

## Phase Roadmap & Data Flow

```text
Phase 1: Document Intelligence (PDF Parsing → Structure: Doc/Page/Paragraph/Sentence)
Phase 2: Person & Concept Extraction (NER + Disambiguation)
Phase 3: Historical Knowledge Graph (Entities & Provenance-backed Relations)
Phase 4: Graph Topology Analysis (PageRank, BFS, Centrality)
Phase 5: Bias & Erasure Detection (Credit Displacement, Minimization)
Phase 6: Evidence Retrieval / RAG (Grounded Explanation)
Phase 7: Matilda Scoring & Visualization UI
```

---

## Data Tier Boundaries

1. **PostgreSQL**: Application state, raw documents, extracted mentions, audit runs, Matilda score reports.
2. **NetworkX / Neo4j**: Historical knowledge graph (Person, Discovery, Publication, Institution nodes & verified relations).
3. **Qdrant**: Vector storage for semantic passage retrieval, biographies, and primary evidence sources.
