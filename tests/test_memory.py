"""
Unit tests for termux_aichain.memory (ConversationBufferMemory, SQLiteEntityMemory, SQLiteVectorStore, FactExtractor)
"""
import pytest
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, GenerationResult
from termux_aichain.memory.buffer import ConversationBufferMemory
from termux_aichain.memory.sqlite import SQLiteEntityMemory, SQLiteVectorStore
from termux_aichain.memory.extractor import FactExtractor

def test_conversation_buffer_memory_window():
    memory = ConversationBufferMemory(k=2) # Keep last 2 exchanges = 4 messages

    memory.save_context("Hi 1", "Hello 1")
    memory.save_context("Hi 2", "Hello 2")
    memory.save_context("Hi 3", "Hello 3")

    history = memory.load_memory_variables()["history"]
    assert len(history) == 4
    assert history[0].content == "Hi 2"
    assert history[1].content == "Hello 2"
    assert history[2].content == "Hi 3"
    assert history[3].content == "Hello 3"

def test_sqlite_entity_memory_persistence():
    mem = SQLiteEntityMemory(":memory:")

    mem.save_entity("device_model", "Galaxy S20")
    mem.save_entity("os", "Android 13")
    mem.save_entity("specs", {"ram_gb": 12, "arch": "arm64-v8a"})

    assert mem.get_entity("device_model") == "Galaxy S20"
    assert mem.get_entity("os") == "Android 13"
    assert mem.get_entity("specs")["ram_gb"] == 12

    all_entities = mem.get_all()
    assert len(all_entities) == 3

    assert mem.delete("os") is True
    assert mem.get_entity("os") is None

    mem.clear()
    assert len(mem.get_all()) == 0

def test_sqlite_vector_store_cosine():
    store = SQLiteVectorStore(":memory:")
    
    # 3 semantic test vectors
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
    assert results[0].page_content.startswith("Doc A")
    assert results[0].score > 0.99 # Very high cosine similarity
    assert results[1].page_content.startswith("Doc A")

class RuleBasedExtractorModel(BaseChatModel):
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
    llm = RuleBasedExtractorModel()
    mem = SQLiteEntityMemory()
    extractor = FactExtractor(model=llm, memory=mem)

    facts = extractor.extract_and_save("Hi, I am Uno and I use a Galaxy S20+ with 12GB RAM.")
    assert facts["user_alias"] == "Uno"
    assert facts["primary_phone"] == "Galaxy S20+"
    assert mem.get_entity("user_alias") == "Uno"
    assert mem.get_entity("ram_gb") == 12