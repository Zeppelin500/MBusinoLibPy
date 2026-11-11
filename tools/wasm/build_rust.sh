#!/usr/bin/env bash
# Build the Rust port (Zeppelin500/mbusino-lib-rs) to WebAssembly for the
# docs/ test page.
#
#   tools/wasm/build_rust.sh
#
# Needs a Rust toolchain (cargo). The wasm32 target is added automatically.
# The library crate is fetched by cargo from GitHub (pinned rev in
# tools/wasm/rust/Cargo.toml), like build.sh fetches MBusinoLib.
#
# Output: docs/rust/mbusino_rs.wasm (committed, since GitHub Pages serves
# docs/ from the main branch). The loader docs/rust/mbusino_rs.js is static
# and not generated.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CRATE="$ROOT/tools/wasm/rust"
OUT="$ROOT/docs/rust"
WASM="$CRATE/target/wasm32-unknown-unknown/release/mbusino_rs_wasm.wasm"

if ! command -v cargo >/dev/null 2>&1; then
    echo "error: cargo not found - install Rust first (https://rustup.rs)" >&2
    exit 1
fi

rustup target add wasm32-unknown-unknown

cargo build --release --manifest-path "$CRATE/Cargo.toml" \
    --target wasm32-unknown-unknown

mkdir -p "$OUT"
cp "$WASM" "$OUT/mbusino_rs.wasm"
echo "built: $OUT/mbusino_rs.wasm ($(wc -c < "$OUT/mbusino_rs.wasm") bytes)"
