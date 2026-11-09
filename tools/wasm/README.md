# tools/wasm - C++ MBusinoLib → WebAssembly

Builds the **original C++ `MBusinoLib`** into WebAssembly so the docs/ test
page can show its output next to the Python port.

## Build

```bash
source /path/to/emsdk/emsdk_env.sh     # puts em++ on PATH
tools/wasm/build.sh
```

Output (committed, because GitHub Pages serves `docs/` from `main`):

- `docs/cpp/mbusino_cpp.js`  – Emscripten glue (MODULARIZE factory)
- `docs/cpp/mbusino_cpp.wasm`

Pinned by default: MBusinoLib `d9acd52` (v0.10.0), ArduinoJson `v7.4.3` (MIT).
Override with `MBUSINO_REF` / `ARDUINOJSON_REF`, or point `MBUSINO_SRC` at a
local MBusinoLib checkout.

## Notes

- Emscripten must be invoked as **`em++`**; `emcc` leaves the C++ stdlib
  symbols undefined.
- `arduino/Arduino.h` is a vendored minimal host shim. The upstream repo has
  its own copy under `test/`, but it is not tracked by git, so we keep ours to
  make the build reproducible.
- The wrapper (`mbusino_wasm.cpp`) mirrors the Arduino example: `decodeHeader()`
  into `header`, `decodeRecords()` into `records`, plus `slave_address`,
  `header_ok`, `records_decoded`, `error_code`.
- ArduinoJson is header-only and only needed at build time.
