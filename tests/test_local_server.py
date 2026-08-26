"""
Unit tests for termux_aichain.core.providers (Advanced sampling & LocalServerManager)
"""
import pytest
from termux_aichain.core.schema import HumanMessage
from termux_aichain.core.providers.openai_compatible import OpenAICompatibleChat
from termux_aichain.core.providers.local_server import LocalServerConfig, LlamaCppServer, BitNetServer

def test_openai_compatible_advanced_payload():
    chat = OpenAICompatibleChat(
        base_url="http://127.0.0.1:8088/v1",
        model="Qwen2.5-7B-Instruct",
        temperature=0.2,
        top_p=0.85,
        top_k=20,
        min_p=0.1,
        repeat_penalty=1.15,
        stop=["<|im_end|>"],
        seed=42,
        extra_body={"mirostat": 2}
    )
    payload = chat._build_payload([HumanMessage(content="Hello")], stream=False)
    assert payload["model"] == "Qwen2.5-7B-Instruct"
    assert payload["temperature"] == 0.2
    assert payload["top_p"] == 0.85
    assert payload["top_k"] == 20
    assert payload["min_p"] == 0.1
    assert payload["repeat_penalty"] == 1.15
    assert payload["stop"] == ["<|im_end|>"]
    assert payload["seed"] == 42
    assert payload["mirostat"] == 2

def test_local_server_config_cli_builder():
    config = LocalServerConfig(
        model_path="/path/to/model-Q4_K_M.gguf",
        host="0.0.0.0",
        port=8080,
        threads=4,
        n_ctx=4096,
        n_batch=512,
        n_ubatch=256,
        n_gpu_layers=33,
        flash_attn=True,
        cache_type_k="q8_0",
        cache_type_v="q8_0",
        mmap=True,
        mlock=True,
        cont_batching=True,
        rope_freq_scale=0.5
    )
    server = LlamaCppServer(config)
    cli_args = server.build_cli_args()
    
    assert "llama-server" in cli_args[0]
    assert "-m" in cli_args and "/path/to/model-Q4_K_M.gguf" in cli_args
    assert "-t" in cli_args and "4" in cli_args
    assert "-c" in cli_args and "4096" in cli_args
    assert "-ngl" in cli_args and "33" in cli_args
    assert "-fa" in cli_args
    assert "-ctk" in cli_args and "q8_0" in cli_args
    assert "-ctv" in cli_args and "q8_0" in cli_args
    assert "--mlock" in cli_args
    assert "--cont-batching" in cli_args
    assert "--rope-freq-scale" in cli_args and "0.5" in cli_args

def test_bitnet_server_cli_builder():
    config = LocalServerConfig(
        model_path="/path/to/bitnet-b1.58-3b.tl1",
        port=8088,
        threads=6,
        n_ctx=2048
    )
    server = BitNetServer(config)
    cli_args = server.build_cli_args()
    assert "-m" in cli_args
    assert "-t" in cli_args and "6" in cli_args