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
echo "[*] Step 1/4: Provisioning system packages and runtimes..."
if command -v pkg >/dev/null 2>&1; then
    pkg update -y
    pkg install -y python nodejs-lts termux-api ffmpeg git
else
    echo "[*] Non-Termux host environment detected. Proceeding with pip installation."
fi

# 2. Upgrade pip runtime
echo "[*] Step 2/4: Upgrading pip..."
python3 -m pip install --upgrade pip

# 3. Install termux-aichain (Zero Heavy Dependencies)
echo "[*] Step 3/4: Installing termux-aichain..."
python3 -m pip install --upgrade termux-aichain

# 4. Diagnostics check
echo "[*] Step 4/4: Executing environment diagnostics..."
termux-aichain setup

echo "=============================================================================="
echo "[OK] termux-aichain successfully installed and verified!"
echo "- Launch Web Dashboard : termux-aichain serve --port 8080"
echo "- Pull verified model  : termux-aichain pull qwen-2.5-1.5b"
echo "- View documentation   : https://uno-km.vercel.app/lib/aichain/"
echo "=============================================================================="