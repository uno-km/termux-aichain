"""
==============================================================================
termux-aichain Embeddings Engine: Zero-Dependency On-Device Vectorizers
==============================================================================
Provides standard BaseEmbeddings, LocalEmbeddings (llama-server /v1/embeddings),
and SparseBM25Embeddings (pure math zero-state offline vectorizer).
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
import math
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence


class EmbeddingGenerationError(RuntimeError):
    """Raised when an embedding backend fails to vectorize text."""
    pass


class BaseEmbeddings(ABC):
    """Abstract Base Class for text embeddings interfaces."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Vectorizes a sequence of documents."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Vectorizes a single query text string."""
        pass


class LocalEmbeddings(BaseEmbeddings):
    """
    Connects to on-device llama-server or OpenAI-compatible /v1/embeddings endpoint.
    Zero Python dependencies - Uses standard urllib with strict timeouts and batching.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model: str = "default",
        timeout_seconds: float = 30.0,
        batch_size: int = 16,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/embeddings"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.batch_size = max(1, batch_size)
        self.api_key = api_key

    @classmethod
    def local(
        cls,
        endpoint: str = "http://127.0.0.1:8080",
        model: str = "bge-micro",
        **kwargs: Any
    ) -> "LocalEmbeddings":
        """Factory method for local edge llama-server embeddings."""
        v1_url = f"{endpoint.rstrip('/')}/v1"
        return cls(base_url=v1_url, model=model, **kwargs)

    def _post_batch(self, texts: List[str]) -> List[List[float]]:
        payload = {
            "model": self.model,
            "input": texts
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status != 200:
                    raise EmbeddingGenerationError(f"Embeddings endpoint returned HTTP status {resp.status}")
                raw = resp.read().decode("utf-8")
                body = json.loads(raw)
        except urllib.error.HTTPError as ex:
            err_body = ex.read().decode("utf-8", errors="ignore") if hasattr(ex, "read") else ""
            raise EmbeddingGenerationError(f"Embedding request failed (HTTP {ex.code}): {err_body or str(ex)}") from ex
        except Exception as ex:
            raise EmbeddingGenerationError(f"Embedding endpoint connection error: {str(ex)}") from ex

        if "data" not in body or not isinstance(body["data"], list):
            raise EmbeddingGenerationError(f"Invalid response schema from embeddings endpoint: {body}")

        # Sort embeddings by original response index
        sorted_items = sorted(body["data"], key=lambda x: x.get("index", 0))
        embeddings: List[List[float]] = []
        for item in sorted_items:
            emb = item.get("embedding", [])
            if not emb or any(math.isnan(v) or math.isinf(v) for v in emb):
                raise EmbeddingGenerationError("Model returned invalid or NaN/Inf vector values.")
            embeddings.append(emb)
        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i : i + self.batch_size]
            all_embeddings.extend(self._post_batch(chunk))
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        res = self.embed_documents([text])
        if not res:
            raise EmbeddingGenerationError("Empty embedding returned for query.")
        return res[0]


class SparseBM25Embeddings(BaseEmbeddings):
    """
    100% Offline, Zero-State Hashing BM25 / TF-IDF Vectorizer.
    Generates deterministic bounded fixed-dimension sparse float vectors without any model weights.
    """

    def __init__(self, dimension: int = 256, k1: float = 1.5, b: float = 0.75):
        self.dimension = dimension
        self.k1 = k1
        self.b = b
        self._doc_count = 0
        self._doc_freq: Counter[str] = Counter()
        self._avg_dl = 1.0

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"\w+", text.lower())
        return [t for t in tokens if len(t) > 1]

    def _hash_token(self, token: str) -> int:
        h = 0
        for ch in token:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return h % self.dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        doc_tokens_list = [self._tokenize(t) for t in texts]
        self._doc_count += len(texts)
        total_len = sum(len(toks) for toks in doc_tokens_list)
        self._avg_dl = max(1.0, total_len / max(1, len(doc_tokens_list)))

        for toks in doc_tokens_list:
            unique_terms = set(toks)
            self._doc_freq.update(unique_terms)

        results: List[List[float]] = []
        for toks in doc_tokens_list:
            vec = [0.0] * self.dimension
            if not toks:
                results.append(vec)
                continue
            tf = Counter(toks)
            dl = len(toks)
            for term, count in tf.items():
                slot = self._hash_token(term)
                df = self._doc_freq.get(term, 1)
                idf = math.log(1.0 + (self._doc_count - df + 0.5) / (df + 0.5))
                bm25_tf = (count * (self.k1 + 1.0)) / (count + self.k1 * (1.0 - self.b + self.b * (dl / self._avg_dl)))
                vec[slot] += max(0.0, idf * bm25_tf)

            # L2 Normalize
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            results.append(vec)
        return results

    def embed_query(self, text: str) -> List[float]:
        toks = self._tokenize(text)
        vec = [0.0] * self.dimension
        if not toks:
            return vec
        tf = Counter(toks)
        dl = len(toks)
        for term, count in tf.items():
            slot = self._hash_token(term)
            df = self._doc_freq.get(term, 1)
            idf = math.log(1.0 + (self._doc_count - df + 0.5) / (df + 0.5))
            bm25_tf = (count * (self.k1 + 1.0)) / (count + self.k1 * (1.0 - self.b + self.b * (dl / self._avg_dl)))
            vec[slot] += max(0.0, idf * bm25_tf)

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
