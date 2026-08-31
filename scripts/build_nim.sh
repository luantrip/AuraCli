#!/usr/bin/env bash
# =============================================================================
# Aura CLI — Nim Build Script (Multi-platform)
# =============================================================================
# Compiles modules to bin/<platform>-<architecture>/.
#
# Usage:
#   ./scripts/build_nim.sh              # release build (default)
#   ./scripts/build_nim.sh --debug      # debug build
#   ./scripts/build_nim.sh --target nexus  # single target
#   ./scripts/build_nim.sh --check      # verify nim is available only
#
# Requirements:
#   - nim >= 1.6.0  (https://nim-lang.org/install.html)
#   - OpenSSL dev headers (for aura-monitor with -d:ssl)
#
# Outputs (bin/):
#   imagination, nexus, sentinel, prism, forge, aura-monitor
#   notebook.dylib | notebook.so | notebook.dll
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NIM_DIR="$PROJECT_ROOT/modules_nim"
BIN_ROOT="$PROJECT_ROOT/bin"
PACKAGE_BIN_ROOT="$PROJECT_ROOT/packages/aura-cli-nim/aura_cli_nim/bin"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
BUILD_MODE="release"
TARGET=""        # empty = build all
CHECK_ONLY=false

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)   BUILD_MODE="debug"; shift ;;
        --release) BUILD_MODE="release"; shift ;;
        --target)  TARGET="$2"; shift 2 ;;
        --check)   CHECK_ONLY=true; shift ;;
        -h|--help)
            sed -n '2,30p' "$0" | sed 's/^# //'
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Detect platform
# ---------------------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Darwin)  PLATFORM="macos";   LIB_EXT="dylib" ;;
    Linux)   PLATFORM="linux";   LIB_EXT="so"    ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows"; LIB_EXT="dll" ;;
    *)       PLATFORM="unknown"; LIB_EXT="so"    ;;
esac

case "$ARCH" in
    x86_64|amd64) ARCH_TAG="x86_64" ;;
    arm64|aarch64) ARCH_TAG="aarch64" ;;
    *) ARCH_TAG="$ARCH" ;;
esac

PLATFORM_TAG="${PLATFORM}-${ARCH_TAG}"
EXE_EXT=""
if [[ "$PLATFORM" == "windows" ]]; then
    EXE_EXT=".exe"
fi
TARGET_CONFIG="$PROJECT_ROOT/config/nim-targets/$PLATFORM_TAG.env"
if [[ ! -f "$TARGET_CONFIG" ]]; then
    echo "❌ Unsupported Nim target: $PLATFORM_TAG (missing $TARGET_CONFIG)"
    exit 1
fi
# shellcheck disable=SC1090 -- target is a tracked repository configuration
source "$TARGET_CONFIG"
if [[ "$AURA_NIM_PLATFORM" != "$PLATFORM" || "$AURA_NIM_ARCH" != "$ARCH_TAG" ]]; then
    echo "❌ Invalid target configuration: $TARGET_CONFIG"
    exit 1
fi
LIB_EXT="$AURA_NIM_LIB_EXT"
BIN_DIR="$BIN_ROOT/$PLATFORM_TAG"
PACKAGE_BIN_DIR="$PACKAGE_BIN_ROOT/$PLATFORM_TAG"
NIMCACHE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/aura-cli-nimcache.XXXXXX")"
trap 'rm -rf "$NIMCACHE_ROOT"' EXIT

echo "🔧 Aura Nim Build — target=$PLATFORM_TAG mode=$BUILD_MODE"

# ---------------------------------------------------------------------------
# Check nim
# ---------------------------------------------------------------------------
NIM_BIN=""
# Look for Nim compiler specifically (avoid Perl's 'nim' network tool)
for candidate in \
    "$HOME/.nimble/bin/nim" \
    "$HOME/choosenim/toolchains/nim-stable/bin/nim" \
    "/usr/local/nim/bin/nim" \
    "/opt/homebrew/bin/nim"; do
    [[ -z "$candidate" || ! -x "$candidate" ]] && continue
    _ver="$("$candidate" --version 2>&1 || true)"
    if echo "$_ver" | grep -qi "nim compiler"; then
        NIM_BIN="$candidate"
        break
    fi
done

# Also check PATH, but only if it looks like the real Nim
if [[ -z "$NIM_BIN" ]]; then
    _path_nim="$(command -v nim 2>/dev/null || true)"
    if [[ -n "$_path_nim" ]]; then
        _ver="$("$_path_nim" --version 2>&1 || true)"
        if echo "$_ver" | grep -qi "nim compiler"; then
            NIM_BIN="$_path_nim"
        fi
    fi
fi

if [[ -z "$NIM_BIN" ]]; then
    echo ""
    echo "❌ Nim compiler not found."
    echo "   Install via choosenim: curl https://nim-lang.org/choosenim/init.sh -sSf | sh"
    echo "   Or: https://nim-lang.org/install.html"
    exit 1
fi

NIM_VERSION="$("$NIM_BIN" --version 2>/dev/null | head -1 || echo 'unknown')"
echo "   nim: $NIM_VERSION ($NIM_BIN)"

if $CHECK_ONLY; then
    echo "✅ nim is available."
    exit 0
fi

# ---------------------------------------------------------------------------
# Prepare bin/
# ---------------------------------------------------------------------------
if [[ -n "$TARGET" ]]; then
    case "$TARGET" in
        imagination|nexus|sentinel|prism|forge|aura-monitor|notebook) ;;
        *) echo "❌ Unknown Nim target: $TARGET"; exit 1 ;;
    esac
fi

mkdir -p "$BIN_DIR" "$PACKAGE_BIN_DIR"

# ---------------------------------------------------------------------------
# Build flags
# ---------------------------------------------------------------------------
if [[ "$BUILD_MODE" == "release" ]]; then
    FLAGS="-d:release --opt:speed"
else
    FLAGS="-d:debug --debuginfo --lineDir:on"
fi

# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------
build_binary() {
    local name="$1"
    local src="$2"
    local extra_flags="${3:-}"
    local out="$BIN_DIR/$name$EXE_EXT"
    local package_out="$PACKAGE_BIN_DIR/$name$EXE_EXT"
    rm -f "$out" "$package_out"

    echo ""
    echo "  ▶ Building $name..."
    if "$NIM_BIN" c $FLAGS $extra_flags --nimcache:"$NIMCACHE_ROOT/$name" -o:"$out" "$src"; then
        chmod +x "$out"
        install -m 755 "$out" "$package_out"
        local size
        size=$(du -sh "$out" 2>/dev/null | cut -f1)
        echo "  ✅ $name → bin/$name ($size)"
    else
        echo "  ❌ Failed to build $name"
        return 1
    fi
}

build_library() {
    local name="$1"
    local src="$2"
    local out="$BIN_DIR/${name}.${LIB_EXT}"
    local package_out="$PACKAGE_BIN_DIR/${name}.${LIB_EXT}"
    rm -f "$out" "$package_out"

    echo ""
    echo "  ▶ Building $name.$LIB_EXT..."
    # Keep Nim's shared-library initialization; --noMain leaves the runtime
    # uninitialized when the library is loaded through ctypes.
    if "$NIM_BIN" c $FLAGS --app:lib --nimcache:"$NIMCACHE_ROOT/$name" -o:"$out" "$src"; then
        chmod 644 "$out"
        install -m 644 "$out" "$package_out"
        local size
        size=$(du -sh "$out" 2>/dev/null | cut -f1)
        echo "  ✅ $name.$LIB_EXT → bin/$name.$LIB_EXT ($size)"
    else
        echo "  ❌ Failed to build $name.$LIB_EXT"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Target definitions
# ---------------------------------------------------------------------------
build_target() {
    local t="$1"
    case "$t" in
        imagination)
            build_binary "imagination" "$NIM_DIR/imagination.nim"
            ;;
        nexus)
            build_binary "nexus" "$NIM_DIR/nexus.nim"
            ;;
        sentinel)
            build_binary "sentinel" "$NIM_DIR/sentinel.nim"
            ;;
        prism)
            build_binary "prism" "$NIM_DIR/prism.nim"
            ;;
        forge)
            build_binary "forge" "$NIM_DIR/forge.nim"
            ;;
        aura-monitor)
            # Requires OpenSSL for -d:ssl; fall back gracefully
            if [[ "$AURA_NIM_SSL" == "brew" ]]; then
                if command -v brew >/dev/null 2>&1; then
                    OPENSSL_PREFIX="$(brew --prefix openssl@3 2>/dev/null || brew --prefix openssl 2>/dev/null || true)"
                else
                    OPENSSL_PREFIX=""
                fi
                if [[ -n "$OPENSSL_PREFIX" ]]; then
                    SSL_FLAGS="-d:ssl --passL:-L$OPENSSL_PREFIX/lib --passC:-I$OPENSSL_PREFIX/include"
                else
                    SSL_FLAGS="-d:ssl"
                fi
            elif [[ "$AURA_NIM_SSL" == "system" ]]; then
                SSL_FLAGS="-d:ssl"
            else
                SSL_FLAGS=""
            fi
            build_binary "aura-monitor" "$NIM_DIR/monitor/monitor.nim" "$SSL_FLAGS"
            ;;
        notebook)
            build_library "notebook" "$NIM_DIR/notebook/notebook.nim"
            ;;
        *)
            echo "  ❌ Unknown target: $t"
            return 1
            ;;
    esac
}

ALL_TARGETS=(imagination nexus sentinel prism forge aura-monitor notebook)

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
FAILED=()

if [[ -n "$TARGET" ]]; then
    build_target "$TARGET" || FAILED+=("$TARGET")
else
    for t in "${ALL_TARGETS[@]}"; do
        build_target "$t" || FAILED+=("$t")
    done
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ ${#FAILED[@]} -eq 0 ]]; then
    if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
        VERIFY_PYTHON="$PROJECT_ROOT/.venv/bin/python"
    else
        VERIFY_PYTHON="python3"
    fi
    if ! "$VERIFY_PYTHON" "$PROJECT_ROOT/scripts/verify_nim_release.py" \
        "$PLATFORM_TAG" --write-manifest; then
        echo "❌ Nim release verification failed for $PLATFORM_TAG"
        exit 1
    fi
    echo "✅ All targets built successfully → bin/$PLATFORM_TAG/"
    ls -lh "$BIN_DIR" | grep -v "^total" | awk '{print "   " $NF " (" $5 ")"}'
else
    echo "⚠️  Build completed with errors:"
    for f in "${FAILED[@]}"; do
        echo "   ❌ $f"
    done
    exit 1
fi
