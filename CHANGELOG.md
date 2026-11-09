# MBusinoLibPy change log

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

The version number tracks the C++ library it was ported from, so **0.10.0**
means "port of MBusinoLib 0.10.0".

## [Unreleased]

### Added

- Web decoder: the original C++ `MBusinoLib` runs alongside the Python port.
  It is compiled to WebAssembly (`tools/wasm/build.sh` → `docs/cpp/mbusino_cpp.*`)
  and both decoders are fed by the same hex input, showing their results side by
  side. Requires Emscripten for rebuilds; the built artifacts are committed so
  GitHub Pages works as-is.
- Runnable examples in `examples/` and doctest examples in the main docstrings
  (covered by the test suite). Added `examples/minimal_hex_to_json.py`, the
  shortest end-to-end example: a telegram hex string in, JSON out.

### Changed

- Web decoder (`docs/`): the fixed-data-header list is now a two-column
  layout (label | value). Previously it used an auto-fill grid that put `<dt>`
  and `<dd>` in separate columns, so on wide screens a value wrapped onto the
  next row, away from its label. Long labels now wrap inside the label column.
- Web decoder (`docs/`): the records table lists the user-facing fields
  (`vif`, `subUnit`, `storage`, `tariff`). When the telegram is followed by
  another one (`telegramFollow` / `0x1F` marker) an orange note box under the
  table reports that another telegram is ready for retrieval.
- README documents the PyPI release: `pip install MBusinoLibPy` is now the
  primary installation path, with the GitHub checkout as the alternative for
  the latest development state.
- README states that the decoder supports any M-Bus slave (no fixed device
  list) and links the live browser decoder on GitHub Pages
  (https://zeppelin500.github.io/MBusinoLibPy/).
- Documentation restructured: README now targets end users, development notes
  and open points moved to `dev_issues/`.
- All runtime error messages (`get_error_message()`, the `decode_telegram()`
  frame hints) are now English instead of German, and the last German
  identifiers/comments in tests and tools were translated — everything on
  GitHub is English now.

## [0.10.0] - 2026-11-07

Initial Python port of [MBusinoLib 0.10.0](https://github.com/Zeppelin500/MBusinoLib).

### Added

- `MBusinoLib.decode_records(buffer, size=None)` - port of
  `MBusinoLib::decodeRecords()` (`MBusinoLib.cpp` line 62). Returns the list of
  records, keys identical to the ArduinoJson output (`vif`, `code`,
  `value_scaled`, `value_string`, `units`, `name`, `subUnit`, `storage`,
  `tariff`, `telegramFollow`).
- `MBusinoLib.decode_header(buffer, length=None)` - port of
  `MBusinoLib::decodeHeader()` (line 1563). The C++ `bool` result maps to
  "dict contains `id`".
- `MBusinoLib.decode_telegram(raw)` - **new**, no C++ counterpart. Validates a
  complete frame (`68 LL LL 68 C A CI … CHK 16`): start/stop byte, both length
  fields, declared length vs. buffer size, byte-sum *and* quartet checksum,
  then decodes header and records in the `test_decode.cpp` way
  (`packet_size = data[1] + 6`, records from offset `0x13` with length
  `packet_size - 0x13 - 2`).
- `MBusinoLib.get_error()` - port of `getError()` (line 54), including the
  "return and clear" behaviour.
- `MBusinoLib.get_error_message(code=None)` - **new**: readable German message
  per `MBUS_ERROR` value, read-only (does not clear the error).
- `MBusinoLib.get_code_name()`, `get_code_units()`, `get_device_class(code,
  medium=0xFF)`, `get_state_class()` - ports of the four C++ lookup methods
  (lines 660, 847, 1182, 1382), backed by complete lookup tables in
  `lookup_tables.py` that mirror the C++ fall-through groups one to one.
- `MBUS_CODE` (123 members) and `MBUS_ERROR` (6 members) as `IntEnum` with the
  same order and values as the C++ enums in `MBusinoLib.h`.
- `VIF_DEFS` - the `vif_defs` table, 132 entries, byte-identical
  (`code`, `base`, `size`, `scalar`), plus `MBUS_VIF_DEF_NUM`.
- `MEDIUM_NAMES` - the medium switch from `decodeHeader()`.
- Golden test suite (`tests/`): five real telegrams, nine header cases and
  fourteen record buffers captured from the unmodified C++ library, plus table,
  header, frame and error-code unit tests (76 tests, stdlib `unittest`).
- `tools/` - harness wrappers and the script used to regenerate the golden
  files.

### Notes

- The internal buffer API (`reset()`, `getSize()`, `getBuffer()`, `copy()`,
  constructor size argument) is intentionally **not** ported: Python receives
  `bytes`/`bytearray` as arguments instead.
- `value_scaled` uses the same operations in the same order as the C++
  (including `int16_t`/`int32_t` wrap-around, `int8_t` scalar truncation and
  32-bit `float` for "real" records), so the computed doubles are identical.
  The golden tests allow `rel_tol=abs_tol=1e-6` (`ARDUINO_FLOAT_DECIMALS = 6`)
  only because ArduinoJson rounds while serialising.
- Known C++ quirks are preserved and documented in the source comments
  (see `src/MBusinoLibPy/mbusino_lib.py`).

[0.10.0]: https://github.com/Zeppelin500/MBusinoLibPy/releases/tag/v0.10.0
