"""
==============================================================================
termux-aichain Memory Engine: SQLite Persistent Storage & Micro Vector Store
==============================================================================
Provides zero-dependency SQLite-backed persistent memory and pure cosine vector search.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import math
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from termux_aichain.core.splitters import Document

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors using pure math."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

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
        """Alias for set() matching documented high-level memory API."""
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
        """Alias for get() matching documented high-level memory API."""
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
    """Ultra-lightweight SQLite vector store executing pure cosine similarity without C extensions."""

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
                    metadata TEXT NOT NULL
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
                meta = metadatas[idx] if metadatas and idx < len(metadatas) else {}
                cursor = self.conn.execute(
                    "INSERT INTO vector_documents (text, embedding, metadata) VALUES (?, ?, ?)",
                    (text, json.dumps(emb), json.dumps(meta, ensure_ascii=False))
                )
                inserted_ids.append(cursor.lastrowid)
        return inserted_ids

    def similarity_search_by_vector(
        self,
        query_embedding: List[float],
        k: int = 4
    ) -> List[Document]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, text, embedding, metadata FROM vector_documents")
        scored_docs: List[Tuple[float, Document]] = []

        for doc_id, text, emb_str, meta_str in cursor.fetchall():
            doc_emb: List[float] = json.loads(emb_str)
            meta: Dict[str, Any] = json.loads(meta_str)
            score = _cosine_similarity(query_embedding, doc_emb)
            doc = Document(page_content=text, metadata=meta, score=round(score, 4))
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:k]]

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM vector_documents")

    def close(self) -> None:
        self.conn.close()