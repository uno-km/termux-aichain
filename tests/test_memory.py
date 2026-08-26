"""
Unit tests for termux_aichain.memory (ConversationBufferMemory, SQLiteEntityMemory, SQLiteVectorStore, FactExtractor)
"""
import os
import tempfile
import pytest
from termux_aichain.core.schema import HumanMessage, AIMessage, GenerationResult
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.splitters import Document
from termux_aichain.memory.buffer import ConversationBufferMemory
from termux_aichain.memory.sqlite import SQLiteEntityMemory, SQLiteVectorStore
from termux_aichain.memory.extractor import FactExtractor

def test_conversation_buffer_memory_window():
    mem = ConversationBufferMemory(k=2, return_messages=True)
    mem.save_context("Hello", "Hi there!")
    mem.save_context("How is the weather?", "It is sunny.")
    mem.save_context("What is my device?", "Galaxy S20.")

    # With k=2, only last 4 messages (2 turns) should remain
    vars_dict = mem.load_memory_variables()
    history = vars_dict["history"]
    assert len(history) == 4
    assert history[0].content == "How is the weather?"
    assert history[3].content == "Galaxy S20."

def test_sqlite_entity_memory_persistence():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    try:
        mem1 = SQLiteEntityMemory(db_path=db_path)
        mem1.set("user_name", "UnoKim")
        mem1.set("device_profile", {"model": "SM-G986N", "os": "Android 13"})
        mem1.close()

        # Reopen same DB file to verify persistence
        mem2 = SQLiteEntityMemory(db_path=db_path)
        assert mem2.get("user_name") == "UnoKim"
        prof = mem2.get("device_profile")
        assert prof["model"] == "SM-G986N"
        assert prof["os"] == "Android 13"
        mem2.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_sqlite_vector_store_cosine():
    store = SQLiteVectorStore()
    
    # 3 mock embeddings
    # Vector 1: [1.0, 0.0, 0.0] -> Concept A
    # Vector 2: [0.9, 0.1, 0.0] -> Concept A closely related
    # Vector 3: [0.0, 1.0, 0.0] -> Concept B orthogonal
    texts = ["Doc A1: High performance AI", "Doc A2: Fast neural networks", "Doc B1: Audio speech recognition"]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.9, 0.1, 0.0],
        [0.0, 1.0, 0.0]
    ]
    store.add_texts(texts, embeddings, metadatas=[{"topic": "AI"}, {"topic": "AI"}, {"topic": "STT"}])

    # Query vector close to Concept A
    query_emb = [0.95, 0.05, 0.0]
    results = store.similarity_search_by_vector(query_emb, k=2)

    assert len(results) == 2
    assert results[0][0].page_content.startswith("Doc A")
    assert results[0][1] > 0.99 # Very high cosine similarity
    assert results[1][0].page_content.startswith("Doc A")

class MockExtractorLLM(BaseChatModel):
    def generate(self, messages, **kwargs):
        json_resp = '{"user_alias": "Uno", "primary_phone": "Galaxy S20+", "ram_gb": 12}'
        return GenerationResult(content=json_resp, message=AIMessage(content=json_resp))

    async def agenerate(self, messages, **kwargs):
        return self.generate(messages, **kwargs)

    def stream(self, messages, **kwargs):
        raise NotImplementedError

    async def astream(self, messages, **kwargs):
        raise NotImplementedError

def test_fact_extractor():
    llm = MockExtractorLLM()
    mem = SQLiteEntityMemory()
    extractor = FactExtractor(model=llm, memory=mem)

    facts = extractor.extract_and_save("Hi, I am Uno and I use a Galaxy S20+ with 12GB RAM.")
    assert facts["user_alias"] == "Uno"
    assert facts["primary_phone"] == "Galaxy S20+"
    assert mem.get("user_alias") == "Uno"
    assert mem.get("ram_gb") == 12