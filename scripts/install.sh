#!/bin/bash
# ==============================================================================
# termux-aichain One-Touch Zero-State Bootstrap Script for Android Termux
# ==============================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/uno-km/termux-aichain/main/scripts/install.sh | bash
# ==============================================================================

set -e

echo "=============================================================================="
echo "⚡ termux-aichain One-Touch Sovereign Installation"
echo "=============================================================================="

# 1. Update Termux Packages
echo "[*] Step 1/4: Checking Termux packages..."
if command -v pkg >/dev/null 2>&1; then
    pkg update -y
    pkg install -y python nodejs termux-api git
else
    echo "[*] Non-Termux environment detected. Skipping pkg."
fi

# 2. Upgrade pip and build tools
echo "[*] Step 2/4: Upgrading pip and wheel runtime..."
python3 -m pip install --upgrade pip setuptools wheel

# 3. Install termux-aichain
echo "[*] Step 3/4: Installing termux-aichain (Zero Heavy Dependencies)..."
python3 -m pip install --upgrade termux-aichain || python3 -m pip install -e .

# 4. Diagnostics check
echo "[*] Step 4/4: Running diagnostics verification..."
termux-aichain setup

echo "=============================================================================="
echo "✅ termux-aichain successfully installed and ready!"
echo "• Start 1-line Web Dashboard : termux-aichain serve --port 8080"
echo "• Pull recommended model    : termux-aichain pull qwen-2.5-1.5b"
echo "=============================================================================="