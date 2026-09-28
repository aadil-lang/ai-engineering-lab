"""
Slice 8E — Local Embedding Provider

Provides fully local, reproducible embedding generation without cloud APIs.
Guarantees secret redaction prior to vector calculation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
import math
import hashlib
import re
import logging
import httpx

from backend.app.control_plane.redaction import RedactionEngine

logger = logging.getLogger("ai_qa_platform.memory_embedding")


class EmbeddingProvider(ABC):
    """Abstract interface for local embedding engines."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class LocalDeterministicEmbeddingProvider(EmbeddingProvider):
    """
    100% local, deterministic, reproducible feature-hashing embedding provider.
    
    Transforms text into L2-normalized vector representations using sub-word n-grams,
    token frequencies, and semantic feature projections.
    Guarantees zero network access and deterministic reproducibility across platforms.
    """

    def __init__(self, dimension: int = 128, version: str = "v1.0-local-hash"):
        self._dim = dimension
        self._version = version
        self._model_id = "local-deterministic-hasher-128d"

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def version(self) -> str:
        return self._version

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single string into an L2-normalized vector.
        Redacts sensitive tokens before generating the embedding.
        """
        # Invariant: Secret redaction prior to embedding generation
        sanitized, _ = RedactionEngine.redact_text(text or "")
        return self._compute_vector(sanitized)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation."""
        return [self.embed_text(t) for t in texts]

    def _compute_vector(self, text: str) -> List[float]:
        vector = [0.0] * self._dim
        if not text.strip():
            return vector

        # Extract tokens and character tri-grams
        words = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
        features = list(words)

        for w in words:
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    features.append(w[i:i+3])

        if not features:
            return vector

        # Project features into vector space using salted hash functions
        for feat in features:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vector[idx] += sign

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 1e-9:
            vector = [v / norm for v in vector]
        return vector


class LocalOllamaEmbeddingProvider(EmbeddingProvider):
    """
    Attempts to use local Ollama embedding endpoint (e.g. nomic-embed-text / all-minilm).
    Falls back gracefully to LocalDeterministicEmbeddingProvider if Ollama is unavailable.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        fallback_dim: int = 128,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback = LocalDeterministicEmbeddingProvider(dimension=fallback_dim)
        self._dim = fallback_dim

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_id(self) -> str:
        return f"ollama/{self.model}"

    @property
    def version(self) -> str:
        return "v1.0-ollama-hybrid"

    def embed_text(self, text: str) -> List[float]:
        sanitized, _ = RedactionEngine.redact_text(text or "")
        try:
            r = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": sanitized},
                timeout=3.0,
            )
            if r.status_code == 200:
                vec = r.json().get("embedding", [])
                if vec:
                    # L2 normalize
                    norm = math.sqrt(sum(v * v for v in vec))
                    return [v / norm for v in vec] if norm > 1e-9 else vec
        except Exception:
            pass

        # Fallback to deterministic local provider
        return self.fallback.embed_text(sanitized)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
