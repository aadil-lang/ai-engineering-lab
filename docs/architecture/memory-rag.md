# Engineering Memory & Local Hybrid RAG Architecture

## 1. Conceptual Distinction

To maintain technical precision and prevent conflation, Engineering Lab v1 defines clear boundaries between related concepts:

```text
Evidence
= What happened (Authoritative runtime observations: DOM, HAR, logs, screenshots)

Engineering Memory
= Validated knowledge derived from previous evidence (Past failures, diagnoses, verified fixes)

Vector Index
= Retrieval accelerator (Local vector representations for sub-millisecond semantic search)

RAG (Retrieval-Augmented Generation)
= Mechanism for retrieving relevant memory chunks into LLM prompt contexts

LLM
= Consumer and interpreter of retrieved context (Synthesizes candidate diagnoses and code diffs)
```

---

## 2. Core Architectural Guarantees

1. **SQLite is Canonical**:
   - The authoritative store of engineering memory records is a local SQLite database (`engineering_memories`).
   - The vector index is a disposable, rebuildable acceleration cache. If the index is deleted or corrupted, it can be re-indexed from SQLite with zero data loss.

2. **Local Embeddings**:
   - Semantic representations are computed using local sentence-transformers models or local hash projections. No private engineering code or memories are transmitted to external embedding APIs.

3. **Current Runtime Evidence Overrides Historical Memory**:
   - If historical memory states that a component failed due to a missing API key, but current runtime evidence demonstrates an HTTP 200 with an empty body, the current evidence is authoritative.
   - Historical memory provides context, not truth.

4. **Contradictions Are Preserved**:
   - When past diagnoses conflict (e.g., version 1 fixed by patch A, version 2 broke under patch A), the memory system records both episodes with version lineage rather than silently overwriting history.

5. **Stale or Invalidated Memories Are Filtered**:
   - Memories associated with superseded prompt versions or obsolete architectures receive decay weighting during retrieval. Stale memories are never treated as active system invariants.
