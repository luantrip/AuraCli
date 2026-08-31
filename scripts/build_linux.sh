#!/usr/bin/env bash
# =============================================================================
# Aura CLI — Linux Quick Build (Nim binaries)
# =============================================================================
# Run this once on Linux to compile the Nim Powerpack binaries.
# The bin/ directory ships macOS (Mach-O) binaries by default.
# This script recompiles them for the current Linux platform.
#
# Usage:
#   chmod +x scripts/build_linux.sh
#   ./scripts/build_linux.sh
#
# Requirements:
#   - Nim compiler (install it explicitly before running this script)
#   - gcc or clang
#   - libssl-dev (for aura-monitor with SSL)
#
# After running, verify with:
#   ./bin/imagination --version
#   ./bin/forge --version
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🐧 Aura CLI — Linux Nim Build"
echo "   Project root: $PROJECT_ROOT"
echo ""

# ---------------------------------------------------------------------------
# 1. Check Nim
# ---------------------------------------------------------------------------
NIM_BIN=""
for candidate in \
    "$HOME/.nimble/bin/nim" \
    "$HOME/choosenim/toolchains/nim-stable/bin/nim" \
    "/usr/local/bin/nim"; do
    [[ -x "$candidate" ]] || continue
    if "$candidate" --version 2>&1 | grep -qi "nim compiler"; then
        NIM_BIN="$candidate"
        break
    fi
done

if [[ -z "$NIM_BIN" ]]; then
    _path_nim="$(command -v nim 2>/dev/null || true)"
    if [[ -n "$_path_nim" ]] && "$_path_nim" --version 2>&1 | grep -qi "nim compiler"; then
        NIM_BIN="$_path_nim"
    fi
fi

if [[ -z "$NIM_BIN" ]]; then
    echo "❌ Nim compiler not found."
    echo "   Install it from https://nim-lang.org/install.html and rerun this script."
    exit 1
else
    echo "✅ Nim found: $($NIM_BIN --version | head -1) at $NIM_BIN"
fi

# Ensure nimble bin is in PATH for this session
export PATH="$HOME/.nimble/bin:$PATH"

# ---------------------------------------------------------------------------
# 2. Check build dependencies (Linux)
# ---------------------------------------------------------------------------
if ! command -v gcc >/dev/null 2>&1 && ! command -v clang >/dev/null 2>&1; then
    echo "❌ A C compiler (gcc or clang) is required."
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Build via existing build_nim.sh
# ---------------------------------------------------------------------------
echo ""
echo "🔨 Building all Nim binaries for Linux..."
bash "$SCRIPT_DIR/build_nim.sh" "$@"

# ---------------------------------------------------------------------------
# 4. Verify
# ---------------------------------------------------------------------------
echo ""
echo "🔍 Verifying binaries..."
BINARIES=(imagination nexus sentinel forge prism aura-monitor)
FAILED=()
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH_TAG="x86_64" ;;
    arm64|aarch64) ARCH_TAG="aarch64" ;;
    *) ARCH_TAG="$ARCH" ;;
esac
PLATFORM_BIN="$PROJECT_ROOT/bin/linux-$ARCH_TAG"

for b in "${BINARIES[@]}"; do
    path="$PLATFORM_BIN/$b"
    if [[ -x "$path" ]]; then
        echo "   ✅ $b"
    else
        echo "   ❌ $b — not found or not executable"
        FAILED+=("$b")
    fi
done

LIB="$PLATFORM_BIN/notebook.so"
if [[ -f "$LIB" ]]; then
    echo "   ✅ notebook.so"
else
    echo "   ❌ notebook.so — not found"
    FAILED+=("notebook.so")
fi

echo ""
if [[ ${#FAILED[@]} -eq 0 ]]; then
    echo "🎉 All Nim binaries built for Linux successfully!"
    echo "   Run 'aura' to start using the full Nim Powerpack."
else
    echo "⚠️  Some binaries failed to build: ${FAILED[*]}"
    echo "   The CLI will work with Python fallbacks for those features."
    exit 1
fi
