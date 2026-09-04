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

def test_sparse_bm25_embeddings():
    from termux_aichain.memory.embeddings import SparseBM25Embeddings
    embedder = SparseBM25Embeddings(dimension=64)

    docs = [
        "Apple banana fresh organic fruit",
        "Deep neural network training on GPU",
        "Apple orange citrus sweet fruit"
    ]
    doc_embs = embedder.embed_documents(docs)
    assert len(doc_embs) == 3
    assert len(doc_embs[0]) == 64

    # Check L2 normalization
    import math
    norm0 = math.sqrt(sum(x * x for x in doc_embs[0]))
    assert abs(norm0 - 1.0) < 1e-4

    query_emb = embedder.embed_query("apple fruit")
    from termux_aichain.memory.sqlite import _cosine_similarity
    sim0 = _cosine_similarity(query_emb, doc_embs[0])
    sim1 = _cosine_similarity(query_emb, doc_embs[1])
    sim2 = _cosine_similarity(query_emb, doc_embs[2])

    assert sim0 > sim1
    assert sim2 > sim1

def test_local_embeddings_mock(monkeypatch):
    import io
    import json
    from termux_aichain.memory.embeddings import LocalEmbeddings

    class FakeHTTPResponse:
        def __init__(self, data):
            self.data = data
            self.status = 200

        def read(self):
            return json.dumps(self.data).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def mock_urlopen(req, timeout=30.0):
        body = json.loads(req.data.decode("utf-8"))
        inputs = body["input"]
        mock_data = []
        for idx, text in enumerate(inputs):
            # Return dummy 4-dim embedding
            mock_data.append({"index": idx, "embedding": [0.1, 0.2, 0.3, 0.4]})
        return FakeHTTPResponse({"data": mock_data})

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    embedder = LocalEmbeddings(base_url="http://127.0.0.1:8080/v1", batch_size=2)
    embs = embedder.embed_documents(["doc1", "doc2", "doc3"])
    assert len(embs) == 3
    assert embs[0] == [0.1, 0.2, 0.3, 0.4]

    q_emb = embedder.embed_query("query")
    assert q_emb == [0.1, 0.2, 0.3, 0.4]

def test_sqlite_vector_store_with_embeddings_binding():
    from termux_aichain.memory.embeddings import SparseBM25Embeddings
    from termux_aichain.core.splitters import Document

    embedder = SparseBM25Embeddings(dimension=32)
    store = SQLiteVectorStore(":memory:", embeddings=embedder)

    store.add_texts([
        "Galaxy S20 smartphone Android Termux",
        "iPhone 15 Pro Max iOS Apple",
        "Ubuntu Linux server terminal bash"
    ])

    results = store.similarity_search("Android smartphone", k=2)
    assert len(results) == 2
    assert "Galaxy" in results[0].page_content

    # Document convenience method
    store.add_documents([Document(page_content="DeepSeek and Qwen open source models")])
    assert len(store.similarity_search("Qwen models", k=1)) == 1

def test_sqlite_vector_store_hybrid_search():
    from termux_aichain.memory.embeddings import SparseBM25Embeddings

    embedder = SparseBM25Embeddings(dimension=64)
    store = SQLiteVectorStore(":memory:", embeddings=embedder)

    store.add_texts([
        "High performance GPU tensor autograd compiler",
        "Speech to text audio diarization Whisper",
        "Headless web browser automation Playwright"
    ])

    hybrid_results = store.hybrid_search("GPU autograd", k=2, alpha=0.5)
    assert len(hybrid_results) >= 1
    assert "autograd" in hybrid_results[0].page_content
    assert "fts_rank" in hybrid_results[0].metadata or hybrid_results[0].score > 0