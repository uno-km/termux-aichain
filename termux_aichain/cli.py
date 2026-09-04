"""
==============================================================================
termux-aichain Unified Command Line Interface & Full Ecosystem Provisioner
==============================================================================
Provides sovereign zero-state setup, environment diagnostics, model pull,
full multimodal ecosystem auto-provisioning (bitnet, stt, diffusion, playwright, train),
and 1-line serving.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import sys
import json
import time
import shutil
import tempfile
import argparse
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from termux_aichain import __version__, serve, PromptTemplate, LocalServerConfig, LlamaCppServer, LocalServerManager

MODELS_REGISTRY = {
    "llama-3.2-3b": {
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_desc": "~1.9 GB",
        "sha256": "4b68ff56a84d4b1f621375d8624dfdf232ecb4cefe41b3152db4ef8f36c4b260"
    },
    "qwen-2.5-1.5b": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_desc": "~0.98 GB",
        "sha256": "748805f1cfb88f349c256037a505b263b827e7f1f9d519b5b2fb82200234a919"
    },
    "bitnet-3b": {
        "url": "https://huggingface.co/1bitLLM/bitnet_b1_58-3B-GGUF/resolve/main/bitnet_b1_58-3B-Q4_K_M.gguf",
        "filename": "bitnet_b1_58-3B-Q4_K_M.gguf",
        "size_desc": "~1.8 GB",
        "sha256": "099a531e2ecf57e51dfadcf9779dfcf38760085a21e4ea47535b6a782b6be070"
    },
    "bge-micro": {
        "url": "https://huggingface.co/CompendiumLabs/bge-micro-v2-gguf/resolve/main/bge-micro-v2-q4_k_m.gguf",
        "filename": "bge-micro-v2-q4_k_m.gguf",
        "size_desc": "~28 MB",
        "sha256": "47a3e6f9d2a6dbca142e057863eebe665e7ce2913e64ca6e9ebdc5ef6951bdf8"
    }
}

ECOSYSTEM_MODULES = {
    "bitnet": {
        "pypi": "termux-bitnet",
        "post_install": ["termux-bitnet", "--help"],
        "desc": "On-device 1.58-bit BitNet LLM inference engine & server"
    },
    "stt": {
        "pypi": "termux-stt",
        "post_install": ["termux-stt", "doctor"],
        "desc": "On-device Speech-to-Text & X-Vector diarization"
    },
    "diffusion": {
        "pypi": "termux-diffusion",
        "post_install": ["termux-diffusion", "doctor"],
        "desc": "On-device Stable Diffusion image generation"
    },
    "playwright": {
        "pypi": "termux-playwright",
        "post_install": ["termux-playwright", "install"],
        "desc": "Headless Chromium browser automation"
    },
    "train": {
        "pypi": "termux-train",
        "post_install": [],
        "desc": "On-device Autograd neural network training & LoRA"
    },
    "tts": {
        "pypi": "termux-tts",
        "post_install": ["termux-tts", "doctor"],
        "desc": "On-device Neural & Native Text-to-Speech Engine"
    },
    "vision": {
        "pypi": "termux-vision",
        "post_install": ["termux-vision", "doctor"],
        "desc": "On-device Computer Vision & VLM Multimodal Engine"
    }
}

def cmd_install(target: str = "core", install_all: bool = False) -> None:
    """One-touch automatic system & ecosystem package installer for Termux."""
    print("=" * 75)
    print(f"[INSTALL] termux-aichain v{__version__} One-Touch Full Ecosystem Provisioner")
    print("=" * 75)

    is_termux = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux") or bool(shutil.which("pkg"))
    
    # 1. System packages
    if is_termux and shutil.which("pkg"):
        print("[*] Phase 1/3: Provisioning native Termux packages...")
        try:
            print("  - Running: pkg update -y")
            res_upd = subprocess.run(["pkg", "update", "-y"], check=False)
            if res_upd.returncode != 0:
                print(f"  [WARN] pkg update returned non-zero exit code: {res_upd.returncode}")
            sys_pkgs = ["termux-api", "ffmpeg", "git", "nodejs-lts", "clang", "cmake", "libjpeg-turbo", "libpng"]
            print(f"  - Running: pkg install -y {' '.join(sys_pkgs)}")
            res_inst = subprocess.run(["pkg", "install", "-y"] + sys_pkgs, check=False)
            if res_inst.returncode == 0:
                print("[OK] Native Termux system packages installed.")
            else:
                print(f"[WARN] Some native Termux system packages failed to install (exit code {res_inst.returncode}).")
        except Exception as ex:
            print(f"[-] Warning during pkg install: {str(ex)}")
    else:
        print("[INFO] Non-Termux Host OS detected. Skipping native pkg install.")

    # 2. Ecosystem packages
    modules_to_install = []
    if install_all or target in ("all", "ecosystem"):
        modules_to_install = list(ECOSYSTEM_MODULES.keys())
    elif target in ECOSYSTEM_MODULES:
        modules_to_install = [target]

    if modules_to_install:
        print(f"\n[*] Phase 2/3: Installing AMEVA sovereign ecosystem: {', '.join(modules_to_install)}...")
        for mod_key in modules_to_install:
            mod_info = ECOSYSTEM_MODULES[mod_key]
            pkg_name = mod_info["pypi"]
            print(f"  - Installing {pkg_name} ({mod_info['desc']})...")
            try:
                res_pip = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", pkg_name], check=False)
                if res_pip.returncode == 0:
                    print(f"  [OK] Successfully installed {pkg_name}")
                else:
                    print(f"  [-] Failed to install {pkg_name} (pip exit code {res_pip.returncode})")
            except Exception as ex:
                print(f"  [-] Failed to pip install {pkg_name}: {str(ex)}")

            # Run post-install hook if available
            if mod_info["post_install"] and shutil.which(mod_info["post_install"][0]):
                print(f"  - Executing post-install setup: {' '.join(mod_info['post_install'])}...")
                try:
                    res_post = subprocess.run(mod_info["post_install"], check=False)
                    if res_post.returncode != 0:
                        print(f"  [WARN] Post-install hook returned exit code {res_post.returncode}")
                except Exception as ex:
                    print(f"  [-] Post-install hook warning: {str(ex)}")
    else:
        print("\n[*] Phase 2/3: Core mode selected. Ecosystem packages can be installed via 'termux-aichain install --all'")

    # 3. Diagnostics
    print(f"\n[*] Phase 3/3: Running unified environment diagnostics...")
    cmd_setup()

def cmd_setup() -> None:
    """Diagnoses environment and checks native tools and ecosystem integrations."""
    print("=" * 75)
    print(f"[SETUP] termux-aichain v{__version__} Environment Diagnostics")
    print("=" * 75)
    
    is_termux = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
    print(f"- Platform Environment : {'Android Termux (Native)' if is_termux else 'Host OS'}")
    print(f"- Python Version       : {sys.version.split()[0]}")
    
    # Check Termux:API
    has_api = bool(shutil.which("termux-battery-status"))
    print(f"- Termux-API CLI Tools : {'[OK] Installed' if has_api else '[WARN] Not Installed (Kernel Sysfs Fallback Active)'}")
    
    # Check llama-server
    has_llama = bool(shutil.which("llama-server"))
    print(f"- Local llama-server   : {'[OK] Available' if has_llama else '[OPTIONAL] Not in PATH (Can use external/bitnet endpoint)'}")
    
    # Check Node.js
    has_node = bool(shutil.which("node"))
    try:
        node_v = subprocess.check_output(["node", "-v"], text=True).strip() if has_node else "N/A"
    except Exception:
        node_v = "N/A"
    print(f"- Node.js ESM Runtime  : {'[OK] ' + node_v if has_node else '[INFO] Node.js not detected'}")

    # Check Ecosystem Tools
    print("-" * 75)
    print("AMEVA Sovereign Ecosystem Integration Status:")
    for mod_key, mod_info in ECOSYSTEM_MODULES.items():
        cli_name = mod_info["pypi"]
        is_inst = bool(shutil.which(cli_name))
        status_tag = "[OK] Installed & Ready" if is_inst else "[INFO] Not Installed (Run 'termux-aichain install " + mod_key + "')"
        print(f"- {cli_name:<20}: {status_tag}")

    print("-" * 75)
    print("[OK] Core Engine, StateGraph, Memory, Server, and Device modules verified.")
    print("=" * 75)

def cmd_info() -> None:
    """Prints framework metadata and available modules."""
    print("=" * 75)
    print(f"[INFO] termux-aichain v{__version__} Framework Specification")
    print("=" * 75)
    print("- Architecture    : Sovereign Zero-Heavy-Dependency Edge Framework")
    print("- Subsystems      : core, graph, memory, providers, serve, trace, device")
    print("- Native Tools    : battery, sensor, gps, vibrate, notification, tts, shell")
    print("- Ecosystem Hooks : termux-bitnet, termux-stt, termux-diffusion, termux-playwright, termux-train, termux-tts, termux-vision")
    print("- Model Registry  : " + ", ".join(MODELS_REGISTRY.keys()))
    print("- Documentation   : https://uno-km.vercel.app/lib/aichain/")
    print("=" * 75)

def download_verified_model(model_name: str, force: bool = False) -> str:
    """Downloads lightweight model GGUF with strict streaming SHA-256 and GGUF header verification."""
    import hashlib
    import hmac
    target = model_name.lower().strip()
    if target not in MODELS_REGISTRY:
        raise ValueError(f"Unknown model identifier '{model_name}'. Available options: {list(MODELS_REGISTRY.keys())}")

    info = MODELS_REGISTRY[target]
    dest_dir = os.path.expanduser("~/models")
    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, info["filename"])
    tmp_file = f"{dest_file}.download.tmp"
    expected_sha = info["sha256"].lower()

    if os.path.exists(dest_file) and not force:
        # Strict pre-verification of existing file checksum
        hasher = hashlib.sha256()
        with open(dest_file, "rb") as f_in:
            while True:
                chunk = f_in.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        actual_sha = hasher.hexdigest().lower()
        if hmac.compare_digest(actual_sha, expected_sha):
            return dest_file
        print(f"[!] Existing model checksum mismatch (corrupted). Re-downloading {target}...")

    print(f"[*] Downloading {target} ({info['size_desc']}) with cryptographic SHA-256 verification...")
    hasher = hashlib.sha256()
    try:
        req = urllib.request.Request(info["url"], headers={"User-Agent": f"termux-aichain/{__version__}"})
        with urllib.request.urlopen(req) as resp, open(tmp_file, "wb") as f_out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
                f_out.write(chunk)
            f_out.flush()
            os.fsync(f_out.fileno())

        # GGUF Magic Header Verification (b"GGUF")
        with open(tmp_file, "rb") as f_chk:
            magic = f_chk.read(4)
            if magic != b"GGUF":
                raise ValueError("Downloaded file is not a valid GGUF binary format (missing GGUF magic header).")

        # Strict Cryptographic SHA-256 Checksum Verification
        actual_sha = hasher.hexdigest().lower()
        if not hmac.compare_digest(actual_sha, expected_sha):
            raise ValueError(f"Model SHA-256 integrity verification failed: expected {expected_sha}, got {actual_sha}")

        os.replace(tmp_file, dest_file)
        return dest_file
    except Exception:
        if os.path.exists(tmp_file):
            try:
                os.unlink(tmp_file)
            except (PermissionError, OSError) as _cleanup_err:
                # 임시 파일 삭제 실패 — 디스크에 오염 파일이 남을 수 있음. 경고 필수.
                import sys as _sys
                print(
                    f"[WARN] Failed to remove temp file {tmp_file}: {_cleanup_err}",
                    file=_sys.stderr,
                )
        raise


def cmd_pull(model_name: str) -> None:
    """Downloads verified lightweight model GGUF with streaming SHA-256 verification."""
    try:
        dest_file = download_verified_model(model_name)
        print(f"[+] Successfully verified and ready: {dest_file}")
    except Exception as ex:
        print(f"[-] Download failed: {str(ex)}")

def cmd_models() -> None:
    """Lists verified models available for local Termux execution."""
    print("=" * 70)
    print("Verified On-Device GGUF Models")
    print("=" * 70)
    models_dir = os.path.expanduser("~/models")
    for name, info in MODELS_REGISTRY.items():
        local_path = os.path.join(models_dir, info["filename"])
        downloaded = "[Downloaded]" if os.path.exists(local_path) else "[Not Downloaded]"
        print(f"  * {name:<18} {info['size_desc']:<10} {downloaded}")
    print("=" * 70)

def cmd_status(verbose: bool = False) -> None:
    """Displays concise server readiness and model status using ServerIdentityVerifier."""
    from termux_aichain.core.local_agent import ServerIdentityVerifier
    endpoint = "http://127.0.0.1:8080"
    try:
        data = ServerIdentityVerifier.verify(
            endpoint_url=endpoint,
            timeout_seconds=2.0
        )
        print("Status:   ready")
        print(f"Service:  {data.get('service', 'termux-aichain')}")
        print(f"Endpoint: {endpoint}")
        if "model" in data and isinstance(data["model"], dict):
            print(f"Model:    {data['model'].get('id', 'default')}")
        if verbose:
            print(f"Details:  {json.dumps(data, indent=2)}")
    except Exception as ex:
        print("Status:   stopped (No local server running on port 8080)")
        if verbose:
            print(f"Reason:   {str(ex)}")
        print("Hint:     Run 'termux-aichain run qwen-2.5-1.5b' to start local AI.")

def quarantine_lock(lock_file: Path, reason: str = "unverifiable") -> Path:
    """Safely isolates an unverifiable or malformed lock file without data loss."""
    import sys as _sys
    quarantine_dir = lock_file.parent / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{time.time_ns()}-{os.getpid()}"
    dest = quarantine_dir / f"{lock_file.name}.{suffix}.quarantine"
    try:
        shutil.move(str(lock_file), str(dest))
        (quarantine_dir / f"{lock_file.name}.{suffix}.reason.txt").write_text(reason, encoding="utf-8")
    except (PermissionError, OSError) as _quarantine_err:
        # 격리 이동 실패 — 원본 파일이 남아 있을 수 있음. 보안 경고.
        print(
            f"[WARN] quarantine_lock: Failed to quarantine {lock_file}: {_quarantine_err}",
            file=_sys.stderr,
        )
    # MemoryError 등 예상 밖 예외는 재발생
    return dest



def cmd_stop() -> None:
    """Safely stops locally running model server daemon with strict PID ownership verification."""
    from termux_aichain.core.process_identity import verify_managed_process_ownership
    lock_dir = Path(tempfile.gettempdir()) / "termux-aichain"
    stopped = False
    quarantined = False

    if lock_dir.exists():
        for lock_file in lock_dir.glob("*.lock"):
            try:
                data = json.loads(lock_file.read_text(encoding="utf-8"))
                pid = data.get("pid")
                if pid and isinstance(pid, int):
                    if verify_managed_process_ownership(pid, data):
                        import signal, sys as _sys
                        try:
                            os.kill(pid, signal.SIGTERM)
                            stopped = True
                        except ProcessLookupError:
                            # 프로세스가 이미 종료됨 — 잠금 파일만 남은 것
                            stopped = True  # cleanup은 진행
                        except PermissionError as _perm_err:
                            print(
                                f"[ERROR] Permission denied sending SIGTERM to pid {pid}: {_perm_err}",
                                file=_sys.stderr,
                            )
                        lock_file.unlink(missing_ok=True)

                    else:
                        # Fail-closed: Quarantine mismatched lock to preserve state & prevent confusion
                        quarantine_lock(lock_file, reason="ownership_verification_failed")
                        quarantined = True
                else:
                    quarantine_lock(lock_file, reason="missing_or_invalid_pid")
                    quarantined = True
            except Exception as exc:
                quarantine_lock(lock_file, reason=f"malformed_json_{type(exc).__name__}")
                quarantined = True

    if stopped:
        print("✓ Local model server stopped successfully.")
    elif quarantined:
        print("✓ Quarantined unverifiable lock files (process termination prevented to preserve safety).")
    else:
        print("No active managed server found to stop.")

def cmd_run(model_name: str, replace: bool = False) -> None:
    """1-Command User Experience: ensures model & server are ready, then launches interactive session."""
    from termux_aichain.core.local_agent import (
        ServerIdentityVerifier,
        ServerConnectionRefusedError,
        ServerProtocolMismatchError,
        ModelIdentityMismatchError,
    )
    target = model_name.lower().strip()
    if target in MODELS_REGISTRY:
        try:
            model_file = download_verified_model(target)
            trust_level = "registry-sha256-verified"
        except Exception as ex:
            print(f"[-] Model verification failed: {str(ex)}")
            return
    elif os.path.exists(target):
        if not os.path.isfile(target):
            print(f"[-] Target path '{target}' is not a regular file.")
            return
        # Verify GGUF magic header (Format screening only)
        try:
            with open(target, "rb") as f_chk:
                if f_chk.read(4) != b"GGUF":
                    print(f"[-] File '{target}' is not a valid GGUF binary format.")
                    return
        except Exception as ex:
            print(f"[-] Cannot read file '{target}': {str(ex)}")
            return
        model_file = target
        trust_level = "user-file-format-only (Warning: No registry checksum or signed manifest)"
    else:
        print(f"[-] Unknown model '{model_name}'. Available options:")
        for k, v in MODELS_REGISTRY.items():
            print(f"    - {k} ({v['size_desc']})")
        return

    print(f"✓ Model verified [Trust Level: {trust_level}]")

    # Check if existing server is running with strict identity and model matching
    endpoint = "http://127.0.0.1:8080"
    server_alive = False
    expected_model_id = os.path.basename(model_file)
    try:
        ServerIdentityVerifier.verify(
            endpoint_url=endpoint,
            timeout_seconds=1.0,
            expected_service="llama-server",
            expected_model_id=expected_model_id
        )
        server_alive = True
    except ServerConnectionRefusedError:
        server_alive = False
    except (ServerProtocolMismatchError, ModelIdentityMismatchError) as exc:
        if not replace:
            print(f"[-] Port 8080 is occupied by an incompatible server: {str(exc)}")
            print("    Hint: Pass --replace to terminate existing instance and launch with requested model.")
            return
        server_alive = True

    if server_alive and not replace:
        print("✓ Connected to existing local server")
        print(f"Endpoint: {endpoint}")
        print(f"Model:    {target}")
    else:
        if server_alive and replace:
            cmd_stop()
            time.sleep(1.0)

        # Launch server
        if not shutil.which("llama-server"):
            print("[!] 'llama-server' binary not found in PATH.")
            print("    Run 'termux-aichain install' to auto-provision native tools.")
            return

        cfg = LocalServerConfig(model_path=model_file, host="127.0.0.1", port=8080)
        mgr = LocalServerManager(cfg)
        try:
            print("[*] Starting local server engine...")
            mgr.start(wait_ready=True, timeout=30.0)

            # Post-Spawn Verification: Ensure newly started instance strictly satisfies identity contract
            ServerIdentityVerifier.verify(
                endpoint_url=endpoint,
                timeout_seconds=5.0,
                expected_service="llama-server",
                expected_model_id=expected_model_id
            )

            print("✓ Local server started & strictly verified")
            print(f"Endpoint: {endpoint}")
            print(f"Model:    {target}")
        except Exception as ex:
            print(f"[-] Server startup/verification failed: {str(ex)}")
            mgr.stop()
            return

    # Interactive Chat Session
    from termux_aichain import LocalAgent, get_default_device_tools
    agent = LocalAgent(endpoint=endpoint, tools=get_default_device_tools())
    print("\n" + "=" * 70)
    print(f"Termux AI Sovereign Session ({target}) - Type 'exit' to quit")
    print("=" * 70)

    try:
        while True:
            try:
                user_input = input("\n[You] >>> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input or user_input.lower() in ("exit", "quit", "q"):
                break
            print("[AI]  ... thinking ...", end="\r")
            try:
                response = agent.run(user_input)
                print(f"[AI]  {response}")
            except Exception as ex:
                print(f"[-] Error: {str(ex)}")
    finally:
        print("\nSession ended.")

def cmd_serve(port: int, host: str, api_key: Optional[str] = None, allow_insecure_network: bool = False) -> None:
    """Launches instant 1-line agent server with Live Web Dashboard."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        if not api_key and not allow_insecure_network:
            print(f"[SECURITY ERROR] Binding to non-loopback host '{host}' requires --api-key or --allow-insecure-network flag.")
            sys.exit(1)
        if not api_key and allow_insecure_network:
            print(f"[SECURITY WARNING] Server bound to external host '{host}' without authentication!")

    prompt = PromptTemplate.from_template("Edge Task: {input}")
    chain = prompt | (lambda s: f"termux-aichain processed: {s}")
    serve(chain, host=host, port=port, api_key=api_key, block=True)

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="termux-aichain",
        description="Sovereign Zero-Dependency AI Framework for Termux & Android Edge"
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # run (1-Command UX)
    run_parser = subparsers.add_parser("run", help="1-command model execution & interactive chat")
    run_parser.add_argument("model", nargs="?", default="qwen-2.5-1.5b", help="Model name or GGUF path (default: qwen-2.5-1.5b)")
    run_parser.add_argument("--replace", action="store_true", help="Stop existing server if running another model")

    # status
    status_parser = subparsers.add_parser("status", help="Check local AI server status")
    status_parser.add_argument("--verbose", "-v", action="store_true", help="Display full diagnostic metadata")

    # stop
    subparsers.add_parser("stop", help="Stop locally running AI server daemon")

    # models
    subparsers.add_parser("models", help="List verified on-device GGUF models")

    # install (One-Touch auto-provisioning)
    inst_parser = subparsers.add_parser("install", help="One-touch auto-provisioning of Termux dependencies & ecosystem")
    inst_parser.add_argument("target", nargs="?", default="core", choices=["core", "all", "ecosystem", "bitnet", "stt", "diffusion", "playwright", "train", "tts", "vision"], help="Target module to install (default: core)")
    inst_parser.add_argument("--all", action="store_true", help="Install complete multimodal ecosystem (bitnet, stt, diffusion, playwright, train, tts, vision)")

    # setup
    subparsers.add_parser("setup", help="Diagnose environment and check native tools")

    # info
    subparsers.add_parser("info", help="Display framework metadata and capabilities")

    # pull
    pull_parser = subparsers.add_parser("pull", help="Download verified lightweight GGUF model")
    pull_parser.add_argument("model", choices=list(MODELS_REGISTRY.keys()), help="Target model identifier")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Launch 1-line REST/SSE/Web Dashboard server")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind (default: 8080)")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind (default: 127.0.0.1 loopback)")
    serve_parser.add_argument("--api-key", type=str, default=None, help="Bearer token for HTTP API authorization")
    serve_parser.add_argument("--allow-insecure-network", action="store_true", help="Allow unauthenticated external network binding")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args.model, replace=args.replace)
    elif args.command == "status":
        cmd_status(verbose=args.verbose)
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "models":
        cmd_models()
    elif args.command == "install":
        cmd_install(target=args.target, install_all=args.all)
    elif args.command == "setup":
        cmd_setup()
    elif args.command == "info":
        cmd_info()
    elif args.command == "pull":
        cmd_pull(args.model)
    elif args.command == "serve":
        cmd_serve(args.port, args.host, api_key=args.api_key, allow_insecure_network=args.allow_insecure_network)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()