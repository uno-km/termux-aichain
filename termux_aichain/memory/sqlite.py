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
from termux_aichain.memory.embeddings import BaseEmbeddings

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
            import logging as _logging
            _sqlite_logger = _logging.getLogger("termux_aichain.memory.sqlite")
            try:
                self.conn.execute("PRAGMA journal_mode = WAL;")
                self.conn.execute("PRAGMA synchronous = NORMAL;")
                self.conn.execute("PRAGMA busy_timeout = 5000;")
            except sqlite3.OperationalError as _pragma_err:
                # WAL/NORMAL 설정 실패 — 읽기전용 FS 등. DB 작동은 계속되나 성능 최적화 비활성.
                _sqlite_logger.warning(
                    "[sqlite] PRAGMA config failed (degraded performance): %s", _pragma_err
                )
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
    """
    On-Device SQLite Vector Store with automatic embeddings binding,
    batch streaming, heap top-k, and SQLite FTS5 hybrid search.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        embeddings: Optional[BaseEmbeddings] = None
    ):
        self.db_path = db_path
        self.embeddings = embeddings
        self._fts5_supported = False
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        if self.db_path != ":memory:":
            import logging as _logging
            _vec_logger = _logging.getLogger("termux_aichain.memory.sqlite")
            try:
                self.conn.execute("PRAGMA journal_mode = WAL;")
                self.conn.execute("PRAGMA synchronous = NORMAL;")
                self.conn.execute("PRAGMA busy_timeout = 5000;")
            except sqlite3.OperationalError as _pragma_err:
                _vec_logger.warning(
                    "[sqlite/vector] PRAGMA config failed (degraded performance): %s", _pragma_err
                )
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
            try:
                self.conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
                        doc_id UNINDEXED,
                        content
                    )
                """)
                self._fts5_supported = True
            except sqlite3.OperationalError:
                self._fts5_supported = False

    def add_texts(
        self,
        texts: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[int]:
        if embeddings is None:
            if self.embeddings is None:
                raise ValueError("Embeddings must be provided either in add_texts() or bound to SQLiteVectorStore.")
            embeddings = self.embeddings.embed_documents(texts)

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
                row_id = cursor.lastrowid
                inserted_ids.append(row_id)
                if self._fts5_supported:
                    try:
                        self.conn.execute(
                            "INSERT INTO fts_documents (doc_id, content) VALUES (?, ?)",
                            (str(row_id), text)
                        )
                    except sqlite3.Error as fts_err:
                        import logging
                        logging.getLogger("termux_aichain.memory.sqlite").warning(
                            "[sqlite/vector] Failed to insert FTS document %s: %s", row_id, fts_err
                        )
        return inserted_ids

    def add_documents(self, documents: List[Document]) -> List[int]:
        """Convenience method to add Document objects."""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts=texts, metadatas=metadatas)

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

        while rows := cursor.fetchmany(256):
            for doc_id, text, emb_str, meta_str, dim in rows:
                if dim > 0 and dim != q_dim:
                    continue

                try:
                    doc_emb: List[float] = json.loads(emb_str)
                    meta: Dict[str, Any] = json.loads(meta_str)
                except Exception:
                    continue

                score = _cosine_similarity(query_embedding, doc_emb)
                doc = Document(page_content=text, metadata=meta, score=round(score, 4))
                item = (score, doc_id, doc)

                if len(bounded_heap) < k:
                    heapq.heappush(bounded_heap, item)
                elif score > bounded_heap[0][0]:
                    heapq.heapreplace(bounded_heap, item)

        sorted_top_k = sorted(bounded_heap, key=lambda x: x[0], reverse=True)
        return [doc for score, doc_id, doc in sorted_top_k]

    def similarity_search(
        self,
        query: str,
        k: int = 4
    ) -> List[Document]:
        """Computes query embedding via bound embeddings model and executes vector search."""
        if self.embeddings is None:
            raise ValueError("similarity_search requires an embeddings model bound to SQLiteVectorStore.")
        query_emb = self.embeddings.embed_query(query)
        return self.similarity_search_by_vector(query_emb, k=k)

    def hybrid_search(
        self,
        query: str,
        k: int = 4,
        alpha: float = 0.5,
        query_embedding: Optional[List[float]] = None
    ) -> List[Document]:
        """
        Executes 2-stage Hybrid Search with Reciprocal Rank Fusion (RRF):
        1. FTS5 B-Tree Inverted Index filtering (Top 100 candidate doc_ids in O(log N))
        2. Cosine Vector Reranking on the bounded candidate set.
        Falls back to standard bounded vector scan if FTS5 is not available or query returns no keyword matches.
        """
        if isinstance(k, bool) or not isinstance(k, int) or not (1 <= k <= 100):
            raise ValueError(f"k must be an integer between 1 and 100, got: {k}")

        if query_embedding is None:
            if self.embeddings is None:
                raise ValueError("hybrid_search requires either query_embedding or bound embeddings.")
            query_embedding = self.embeddings.embed_query(query)

        if not self._fts5_supported:
            return self.similarity_search_by_vector(query_embedding, k=k)

        import re
        tokens = re.findall(r"\w+", query)
        if not tokens:
            return self.similarity_search_by_vector(query_embedding, k=k)

        fts_query = " OR ".join(tokens)
        cursor = self.conn.cursor()
        fts_ranks: Dict[int, int] = {}
        try:
            cursor.execute(
                "SELECT doc_id FROM fts_documents WHERE fts_documents MATCH ? ORDER BY rank LIMIT 100",
                (fts_query,)
            )
            for rank_idx, (d_id_str,) in enumerate(cursor.fetchall(), start=1):
                try:
                    fts_ranks[int(d_id_str)] = rank_idx
                except ValueError:
                    continue
        except Exception:
            fts_ranks = {}

        if not fts_ranks:
            # Fallback to pure vector scan
            return self.similarity_search_by_vector(query_embedding, k=k)

        # Vector Reranking on bounded candidate set
        candidate_ids = list(fts_ranks.keys())
        placeholders = ",".join("?" for _ in candidate_ids)
        cursor.execute(
            f"SELECT id, text, embedding, metadata, dimension FROM vector_documents WHERE id IN ({placeholders})",
            candidate_ids
        )
        rows = cursor.fetchall()

        q_dim = len(query_embedding)
        vec_scored: List[Tuple[float, int, str, Dict[str, Any]]] = []
        for doc_id, text, emb_str, meta_str, dim in rows:
            if dim > 0 and dim != q_dim:
                continue
            try:
                doc_emb = json.loads(emb_str)
                meta = json.loads(meta_str)
            except Exception:
                continue
            sim = _cosine_similarity(query_embedding, doc_emb)
            vec_scored.append((sim, doc_id, text, meta))

        # Sort candidate items by vector similarity
        vec_scored.sort(key=lambda x: x[0], reverse=True)
        vec_ranks = {doc_id: rank for rank, (_, doc_id, _, _) in enumerate(vec_scored, start=1)}

        # RRF Fusion: score = alpha * (1 / (60 + fts_rank)) + (1 - alpha) * (1 / (60 + vec_rank))
        rrf_results: List[Tuple[float, Document]] = []
        for sim, doc_id, text, meta in vec_scored:
            f_rank = fts_ranks.get(doc_id, 100)
            v_rank = vec_ranks.get(doc_id, 100)
            rrf_score = alpha * (1.0 / (60.0 + f_rank)) + (1.0 - alpha) * (1.0 / (60.0 + v_rank))
            meta["fts_rank"] = f_rank
            meta["vec_rank"] = v_rank
            doc = Document(page_content=text, metadata=meta, score=round(rrf_score, 5))
            rrf_results.append((rrf_score, doc))

        rrf_results.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in rrf_results[:k]]

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM vector_documents")
            if self._fts5_supported:
                try:
                    self.conn.execute("DELETE FROM fts_documents")
                except sqlite3.Error as fts_err:
                    import logging
                    logging.getLogger("termux_aichain.memory.sqlite").warning(
                        "[sqlite/vector] Failed to clear FTS documents: %s", fts_err
                    )

    def close(self) -> None:
        self.conn.close()