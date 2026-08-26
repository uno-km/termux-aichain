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
    """Persistent entity & key-value fact memory backed by SQLite."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
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
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]

    def get_entity(self, key: str, default: Any = None) -> Any:
        """Alias for get() matching documented high-level memory API."""
        return self.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM entity_store")
        res = {}
        for k, v in cursor.fetchall():
            try:
                res[k] = json.loads(v)
            except Exception:
                res[k] = v
        return res

    def delete(self, key: str) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM entity_store WHERE key = ?", (key,))
            return cur.rowcount > 0

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM entity_store")

    def close(self) -> None:
        self.conn.close()

class SQLiteVectorStore:
    """Zero-dependency micro vector store using SQLite and pure cosine similarity."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding TEXT NOT NULL
                )
            """)

    def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[int]:
        if len(texts) != len(embeddings):
            raise ValueError("Length of texts and embeddings must match.")
        
        ids = []
        with self.conn:
            for i, text in enumerate(texts):
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                emb_json = json.dumps(embeddings[i])
                meta_json = json.dumps(meta, ensure_ascii=False)
                cursor = self.conn.execute(
                    "INSERT INTO vector_documents (content, metadata, embedding) VALUES (?, ?, ?)",
                    (text, meta_json, emb_json)
                )
                ids.append(cursor.lastrowid)
        return ids

    def add_documents(self, documents: List[Document], embeddings: List[List[float]]) -> List[int]:
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, embeddings, metadatas)

    def similarity_search_by_vector(
        self,
        query_embedding: List[float],
        k: int = 4
    ) -> List[Document]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT content, metadata, embedding FROM vector_documents")
        
        scored: List[Document] = []
        for content, meta_str, emb_str in cursor.fetchall():
            emb = json.loads(emb_str)
            meta = json.loads(meta_str)
            score = _cosine_similarity(query_embedding, emb)
            doc = Document(page_content=content, metadata=meta, score=score)
            scored.append(doc)

        # Sort descending by cosine similarity
        scored.sort(key=lambda x: x.score or 0.0, reverse=True)
        return scored[:k]

    def close(self) -> None:
        self.conn.close()