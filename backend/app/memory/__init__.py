"""
Engineering Memory Subsystem (Slice 8E).
Structured canonical store, local vector acceleration, and hybrid RAG retrieval.
"""

from backend.app.memory.models import (
    MemoryType,
    MemoryStatus,
    MemoryApplicability,
    RelationshipType,
    EngineeringMemory,
    MemoryRelationship,
    MemoryCandidate,
    MemorySearchResult,
)
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.embedding import (
    EmbeddingProvider,
    LocalDeterministicEmbeddingProvider,
    LocalOllamaEmbeddingProvider,
)
from backend.app.memory.vector_index import VectorMemoryIndex
from backend.app.memory.hybrid_rag import HybridRAGService
from backend.app.memory.candidate_service import MemoryCandidateService

__all__ = [
    "MemoryType",
    "MemoryStatus",
    "MemoryApplicability",
    "RelationshipType",
    "EngineeringMemory",
    "MemoryRelationship",
    "MemoryCandidate",
    "MemorySearchResult",
    "EngineeringMemoryRepository",
    "EmbeddingProvider",
    "LocalDeterministicEmbeddingProvider",
    "LocalOllamaEmbeddingProvider",
    "VectorMemoryIndex",
    "HybridRAGService",
    "MemoryCandidateService",
]
