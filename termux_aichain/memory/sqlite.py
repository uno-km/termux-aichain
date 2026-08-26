"""
==============================================================================
termux-aichain Memory Engine: SQLite Persistent Storage & Micro Vector Store
==============================================================================
Provides SQLite-backed persistent memory and streaming Micro Vector Store
optimized for small on-device datasets with heap-based top-k selection.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import math
import json
import heapq
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from termux_aichain.core.splitters import Document

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors with NaN/Inf protection."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(v1, v2):
        if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
            return 0.0
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

class SQLiteEntityMemory:
    """Persistent entity & key-value fact memory backed by SQLite with WAL optimization."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        if self.db_path != ":memory:":
            try:
                self.conn.execute("PRAGMA journal_mode = WAL;")
                self.conn.execute("PRAGMA synchronous = NORMAL;")
            except Exception:
                pass
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def set(self, key: str, value: Any) -> None:
        val_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        with self.conn:
            self.conn.execute(
                "INSERT INTO entity_store (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (key, val_str)
            )

    def save_entity(self, key: str, value: Any) -> None:
        self.set(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM entity_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return default
        raw_val = row[0]
        try:
            return json.loads(raw_val)
        except Exception:
            return raw_val

    def get_entity(self, key: str, default: Any = None) -> Any:
        return self.get(key, default)

    def delete(self, key: str) -> bool:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM entity_store WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def get_all(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM entity_store")
        results = {}
        for key, val in cursor.fetchall():
            try:
                results[key] = json.loads(val)
            except Exception:
                results[key] = val
        return results

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM entity_store")

    def close(self) -> None:
        self.conn.close()

class SQLiteVectorStore:
    """Linear-scan Micro Vector Store for small on-device datasets with batch streaming and heap top-k."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        if self.db_path != ":memory:":
            try:
                self.conn.execute("PRAGMA journal_mode = WAL;")
                self.conn.execute("PRAGMA synchronous = NORMAL;")
            except Exception:
                pass
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    dimension INTEGER NOT NULL DEFAULT 0
                )
            """)

    def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[int]:
        if len(texts) != len(embeddings):
            raise ValueError(f"Mismatch: {len(texts)} texts and {len(embeddings)} embeddings")

        inserted_ids: List[int] = []
        with self.conn:
            for idx, (text, emb) in enumerate(zip(texts, embeddings)):
                if not emb:
                    raise ValueError(f"Embedding at index {idx} must not be empty.")

                if any(math.isnan(x) or math.isinf(x) for x in emb):
                    raise ValueError(f"Embedding at index {idx} contains NaN or Infinite values.")

                meta = metadatas[idx] if metadatas and idx < len(metadatas) else {}
                cursor = self.conn.execute(
                    "INSERT INTO vector_documents (text, embedding, metadata, dimension) VALUES (?, ?, ?, ?)",
                    (text, json.dumps(emb), json.dumps(meta, ensure_ascii=False), len(emb))
                )
                inserted_ids.append(cursor.lastrowid)
        return inserted_ids

    def similarity_search_by_vector(
        self,
        query_embedding: List[float],
        k: int = 4
    ) -> List[Document]:
        if isinstance(k, bool) or not isinstance(k, int) or not (1 <= k <= 100):
            raise ValueError(f"k must be an integer between 1 and 100, got: {k}")

        if not query_embedding or any(math.isnan(x) or math.isinf(x) for x in query_embedding):
            return []

        cursor = self.conn.cursor()
        cursor.execute("SELECT id, text, embedding, metadata, dimension FROM vector_documents")
        q_dim = len(query_embedding)
        bounded_heap: List[Tuple[float, int, Document]] = []

        # P1-4: Batch streaming with strictly O(k) bounded memory
        while rows := cursor.fetchmany(256):
            for doc_id, text, emb_str, meta_str, dim in rows:
                if dim > 0 and dim != q_dim:
                    continue

                try:
                    doc_emb: List[float] = json.loads(emb_str)
                    meta: Dict[str, Any] = json.loads(meta_str)
                except Exception:
                    continue  # Skip corrupted single row safely

                score = _cosine_similarity(query_embedding, doc_emb)
                doc = Document(page_content=text, metadata=meta, score=round(score, 4))
                item = (score, doc_id, doc)

                if len(bounded_heap) < k:
                    heapq.heappush(bounded_heap, item)
                elif score > bounded_heap[0][0]:
                    heapq.heapreplace(bounded_heap, item)

        # Sort descending by score
        sorted_top_k = sorted(bounded_heap, key=lambda x: x[0], reverse=True)
        return [doc for score, doc_id, doc in sorted_top_k]

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM vector_documents")

    def close(self) -> None:
        self.conn.close()