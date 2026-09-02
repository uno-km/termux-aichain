#!/bin/bash
# ==============================================================================
# termux-aichain One-Touch Zero-State Bootstrap Script for Android Termux
# ==============================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/uno-km/termux-aichain/main/scripts/install.sh | bash
# ==============================================================================

set -e

echo "=============================================================================="
echo "[BOOTSTRAP] termux-aichain One-Touch Sovereign Installation"
echo "=============================================================================="

# 1. Update Termux Packages and core toolchain
echo "[*] Step 1/3: Provisioning system packages and runtimes..."
if command -v pkg >/dev/null 2>&1; then
    pkg update -y
    pkg install -y python nodejs-lts termux-api ffmpeg git clang cmake libjpeg-turbo libpng
else
    echo "[*] Host OS environment detected. Proceeding with pip installation."
fi

# 2. Upgrade pip and install termux-aichain (and optional ecosystem)
echo "[*] Step 2/3: Installing termux-aichain package..."
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade termux-aichain

if [ "$1" == "--all" ] || [ "$1" == "all" ] || [ "$1" == "--ecosystem" ]; then
    echo "[*] Installing complete AMEVA Multimodal Ecosystem (bitnet, stt, diffusion, playwright, train, tts, vision)..."
    termux-aichain install --all
fi

# 3. Environment verification
echo "[*] Step 3/3: Running one-touch verification..."
termux-aichain setup

echo "=============================================================================="
echo "[OK] termux-aichain successfully installed and ready!"
echo "- Install Ecosystem    : termux-aichain install --all"
echo "- Install TTS Only     : termux-aichain install tts"
echo "- Install Vision Only  : termux-aichain install vision"
echo "- Pull model           : termux-aichain pull qwen-2.5-1.5b"
echo "- Start Web Dashboard  : termux-aichain serve --port 8080"
echo "- Documentation        : https://uno-km.vercel.app/lib/aichain/"
echo "=============================================================================="