"""
Unit tests for termux_aichain.core.splitters
"""
import os
import tempfile
import pytest
from termux_aichain.core.splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter, Document, TextLoader

def test_character_text_splitter():
    splitter = CharacterTextSplitter(separator="\n\n", chunk_size=50, chunk_overlap=10)
    text = "Paragraph 1 is here.\n\nParagraph 2 is here and slightly longer.\n\nParagraph 3 is final."
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 60

def test_recursive_character_text_splitter():
    splitter = RecursiveCharacterTextSplitter(chunk_size=40, chunk_overlap=10)
    text = (
        "Termux AI Chain is ultra lightweight.\n"
        "It supports on-device LLMs like BitNet.\n"
        "Zero external heavy dependencies are required."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    assert all(len(c) <= 45 for c in chunks)

def test_text_loader():
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".txt") as f:
        f.write("Termux Native File Load Test Content")
        tmp_path = f.name
    
    try:
        loader = TextLoader(tmp_path)
        docs = loader.load()
        assert len(docs) == 1
        assert docs[0].page_content == "Termux Native File Load Test Content"
        assert docs[0].metadata["source"] == tmp_path
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)