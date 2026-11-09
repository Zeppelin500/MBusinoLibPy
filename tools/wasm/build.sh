#!/usr/bin/env bash
# Build the original C++ MBusinoLib to WebAssembly for the docs/ test page.
#
#   source /path/to/emsdk/emsdk_env.sh   # once, so em++ is on PATH
#   tools/wasm/build.sh
#
# Output: docs/cpp/mbusino_cpp.js + docs/cpp/mbusino_cpp.wasm (committed, since
# GitHub Pages serves docs/ from the main branch).
#
# The C++ sources are fetched at build time - the Python repo does not vendor
# them. Pin newer revisions with MBUSINO_REF / ARDUINOJSON_REF, or point
# MBUSINO_SRC at a local checkout.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/docs/cpp"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

MBUSINO_REF="${MBUSINO_REF:-d9acd52}"          # C++ MBusinoLib v0.10.0
ARDUINOJSON_REF="${ARDUINOJSON_REF:-v7.4.3}"   # header-only, MIT

if ! command -v em++ >/dev/null 2>&1; then
    echo "error: em++ not found - source emsdk_env.sh first" >&2
    exit 1
fi

if [ -n "${MBUSINO_SRC:-}" ]; then
    SRC="$MBUSINO_SRC"
    echo "using local MBusinoLib: $SRC"
else
    git clone --quiet https://github.com/Zeppelin500/MBusinoLib "$WORK/MBusinoLib"
    git -C "$WORK/MBusinoLib" checkout --quiet "$MBUSINO_REF"
    SRC="$WORK/MBusinoLib"
    echo "fetched MBusinoLib @ $MBUSINO_REF"
fi

git clone --quiet --depth 1 --branch "$ARDUINOJSON_REF" \
    https://github.com/bblanchon/ArduinoJson "$WORK/ArduinoJson"
echo "fetched ArduinoJson @ $ARDUINOJSON_REF"

mkdir -p "$OUT"
# -I "$ROOT/tools/wasm/arduino" provides our vendored Arduino.h shim (the
# library's own test/Arduino.h is not tracked by git).
# Must be em++ (not emcc) or the C++ stdlib symbols stay undefined.
em++ -O2 -std=c++17 \
    -I "$ROOT/tools/wasm/arduino" -I "$SRC/src" -I "$WORK/ArduinoJson/src" \
    "$ROOT/tools/wasm/mbusino_wasm.cpp" "$SRC/src/MBusinoLib.cpp" \
    -o "$OUT/mbusino_cpp.js" \
    -s MODULARIZE=1 -s EXPORT_NAME=createMBusinoCpp \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s EXPORTED_FUNCTIONS='["_decode_hex"]' \
    -s EXPORTED_RUNTIME_METHODS='["cwrap"]'

echo "built: $OUT/mbusino_cpp.js + $OUT/mbusino_cpp.wasm"
