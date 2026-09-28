"""
Slice 8E — Local Vector Memory Index

Provides vector similarity search over engineering memories using numpy.
Invariant: The vector index is purely a retrieval accelerator and may never become
the source of truth. All memories are 100% rebuildable from canonical SQLite store.
"""

from __future__ import annotations
import numpy as np
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from backend.app.memory.models import EngineeringMemory
from backend.app.memory.embedding import EmbeddingProvider

logger = logging.getLogger("ai_qa_platform.vector_index")


class VectorMemoryIndex:
    """
    Local vector similarity index mapping high-dimensional vectors to memory IDs.
    Supports candidate filtering, dynamic updates, persistence, and full reconstruction.
    """

    def __init__(self, dimension: int = 128, storage_path: Optional[str] = None):
        self.dimension = dimension
        self.storage_path = Path(storage_path) if storage_path else None
        self.memory_ids: List[str] = []
        self.id_to_idx: Dict[str, int] = {}
        self.vectors: np.ndarray = np.empty((0, dimension), dtype=np.float32)

    @property
    def total_vectors(self) -> int:
        return len(self.memory_ids)

    def add_vector(self, memory_id: str, vector: List[float]):
        """Adds or updates a single vector in the index."""
        vec = np.array(vector, dtype=np.float32).reshape(1, -1)
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm

        if memory_id in self.id_to_idx:
            idx = self.id_to_idx[memory_id]
            self.vectors[idx] = vec[0]
        else:
            self.id_to_idx[memory_id] = len(self.memory_ids)
            self.memory_ids.append(memory_id)
            if self.vectors.shape[0] == 0:
                self.vectors = vec
            else:
                self.vectors = np.vstack([self.vectors, vec])

    def add_batch(self, memory_ids: List[str], vectors: List[List[float]]):
        """Batch adds vectors to the index."""
        for mid, vec in zip(memory_ids, vectors):
            self.add_vector(mid, vec)

    def remove_vector(self, memory_id: str):
        """Removes a memory vector from the index."""
        if memory_id not in self.id_to_idx:
            return

        remove_idx = self.id_to_idx[memory_id]
        self.memory_ids.pop(remove_idx)
        self.vectors = np.delete(self.vectors, remove_idx, axis=0)

        # Rebuild ID to index mapping
        self.id_to_idx = {mid: i for i, mid in enumerate(self.memory_ids)}

    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        candidate_memory_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Calculates cosine similarities between query vector and indexed memories.
        If candidate_memory_ids is provided, restricts search only to the candidate population.
        Returns: List of (memory_id, similarity_score) sorted descending.
        """
        if len(self.memory_ids) == 0:
            return []

        q_vec = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(q_vec)
        if norm > 1e-9:
            q_vec = q_vec / norm

        if candidate_memory_ids is not None:
            # Filter indices
            candidate_set = set(candidate_memory_ids)
            target_indices = [
                self.id_to_idx[mid]
                for mid in self.memory_ids
                if mid in candidate_set
            ]
            if not target_indices:
                return []
            sub_vectors = self.vectors[target_indices]
            sub_ids = [self.memory_ids[i] for i in target_indices]
            sims = np.dot(sub_vectors, q_vec.T).flatten()
            top_k_indices = np.argsort(sims)[::-1][:k]
            return [(sub_ids[i], float(sims[i])) for i in top_k_indices]

        # Full index dot product
        sims = np.dot(self.vectors, q_vec.T).flatten()
        top_k_indices = np.argsort(sims)[::-1][:k]
        return [(self.memory_ids[i], float(sims[i])) for i in top_k_indices]

    def save(self, filepath: Optional[str | Path] = None):
        """Persists index structure to disk."""
        target_path = Path(filepath) if filepath else self.storage_path
        if not target_path:
            raise ValueError("No storage path provided for vector index persistence.")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "dimension": self.dimension,
            "memory_ids": self.memory_ids,
            "vectors": self.vectors.tolist(),
        }
        target_path.write_text(json.dumps(data), encoding="utf-8")

    def load(self, filepath: Optional[str | Path] = None) -> bool:
        """Loads index structure from disk."""
        target_path = Path(filepath) if filepath else self.storage_path
        if not target_path or not target_path.exists():
            return False

        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            self.dimension = data["dimension"]
            self.memory_ids = data["memory_ids"]
            self.id_to_idx = {mid: i for i, mid in enumerate(self.memory_ids)}
            self.vectors = np.array(data["vectors"], dtype=np.float32)
            return True
        except Exception as e:
            logger.error(f"Failed to load vector index: {e}")
            return False

    def rebuild_from_repository(
        self,
        repo: Any,
        embedding_provider: EmbeddingProvider,
        application_id: Optional[str] = None,
    ) -> int:
        """
        Reconstructs the entire vector index from canonical SQLite storage.
        Invariant: Vector index is fully recoverable if deleted or corrupted.
        """
        memories = repo.list_memories(application_id=application_id, limit=5000)
        self.memory_ids = []
        self.id_to_idx = {}
        self.dimension = embedding_provider.dimension
        self.vectors = np.empty((0, self.dimension), dtype=np.float32)

        if not memories:
            return 0

        texts = [m.content for m in memories]
        vecs = embedding_provider.embed_batch(texts)
        self.add_batch([m.memory_id for m in memories], vecs)
        logger.info(f"[VECTOR_INDEX] Rebuilt index with {len(memories)} memories")
        return len(memories)
