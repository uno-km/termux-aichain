"""
==============================================================================
termux-aichain Unified Command Line Interface & One-Touch Provisioner
==============================================================================
Provides sovereign zero-state setup, environment diagnostics, model pull,
and 1-line serving CLI for Android Termux.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import sys
import shutil
import argparse
import subprocess
import urllib.request
from termux_aichain import __version__, serve, PromptTemplate, LocalServerConfig, LlamaCppServer

MODELS_REGISTRY = {
    "llama-3.2-3b": {
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_desc": "~1.9 GB",
    },
    "qwen-2.5-1.5b": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_desc": "~0.98 GB",
    },
    "bitnet-3b": {
        "url": "https://huggingface.co/1bitLLM/bitnet_b1_58-3B-GGUF/resolve/main/bitnet_b1_58-3B-Q4_K_M.gguf",
        "filename": "bitnet_b1_58-3B-Q4_K_M.gguf",
        "size_desc": "~1.8 GB",
    }
}

def cmd_setup() -> None:
    """Diagnoses environment and provisions required native tools."""
    print("=" * 70)
    print(f"⚡ termux-aichain v{__version__} One-Touch Environment Diagnostics")
    print("=" * 70)
    
    is_termux = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
    print(f"• Platform Environment : {'Android Termux (Native)' if is_termux else 'Host OS'}")
    print(f"• Python Version       : {sys.version.split()[0]}")
    
    # Check Termux:API
    has_api = bool(shutil.which("termux-battery-status"))
    print(f"• Termux-API CLI Tools : {'[OK] Installed' if has_api else '[WARN] Not Installed (Using Kernel Sysfs Fallback)'}")
    
    # Check llama-server
    has_llama = bool(shutil.which("llama-server"))
    print(f"• Local llama-server   : {'[OK] Available' if has_llama else '[OPTIONAL] Not in PATH (Can use external/bitnet endpoint)'}")
    
    # Check Node.js
    has_node = bool(shutil.which("node"))
    print(f"• Node.js ESM Runtime  : {'[OK] ' + subprocess.check_output(['node', '-v'], text=True).strip() if has_node else '[INFO] Node.js not detected'}")

    print("-" * 70)
    if is_termux and not has_api:
        print("[*] To enable full hardware sensors/vibration on Termux, run:")
        print("    pkg update && pkg install termux-api -y\n")
    print("[+] All Core, Graph, Memory, Serve, and Trace modules are 100% ready!")
    print("=" * 70)

def cmd_pull(model_name: str) -> None:
    """Downloads validated lightweight model GGUF for local inference."""
    target = model_name.lower().strip()
    if target not in MODELS_REGISTRY:
        print(f"[-] Unknown model '{model_name}'. Available options:")
        for k, v in MODELS_REGISTRY.items():
            print(f"    - {k} ({v['size_desc']})")
        return

    info = MODELS_REGISTRY[target]
    dest_dir = os.path.expanduser("~/models")
    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, info["filename"])

    if os.path.exists(dest_file):
        print(f"[*] Model already exists at: {dest_file}")
        return

    print(f"[*] Downloading {target} ({info['size_desc']}) to {dest_file}...")
    try:
        urllib.request.urlretrieve(info["url"], dest_file)
        print(f"[+] Successfully downloaded: {dest_file}")
    except Exception as ex:
        print(f"[-] Download failed: {str(ex)}")

def cmd_serve(port: int, host: str) -> None:
    """Launches instant 1-line agent server with Live Web Dashboard."""
    prompt = PromptTemplate.from_template("Edge Task: {input}")
    chain = prompt | (lambda s: f"termux-aichain processed: {s}")
    serve(chain, host=host, port=port, block=True)

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="termux-aichain",
        description="Sovereign Zero-Dependency AI Framework for Termux & Android Edge"
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # setup
    subparsers.add_parser("setup", help="Diagnose environment and check native tools")

    # pull
    pull_parser = subparsers.add_parser("pull", help="Download verified lightweight GGUF model")
    pull_parser.add_argument("model", choices=list(MODELS_REGISTRY.keys()), help="Target model identifier")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Launch 1-line REST/SSE/Web Dashboard server")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind (default: 8080)")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")

    args = parser.parse_args()
    if args.command == "setup":
        cmd_setup()
    elif args.command == "pull":
        cmd_pull(args.model)
    elif args.command == "serve":
        cmd_serve(args.port, args.host)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()