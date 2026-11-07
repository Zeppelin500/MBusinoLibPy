# MBusinoLibPy - a Python M-Bus Decoder

[![version](https://img.shields.io/badge/version-0.10.0-brightgreen.svg)](CHANGELOG.md)
[![license](https://img.shields.io/badge/license-GPL--3.0-orange.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue.svg)](https://www.python.org/)
[![dependencies](https://img.shields.io/badge/runtime%20deps-0-brightgreen.svg)](pyproject.toml)

**MBusinoLibPy** is a function-by-function Python port of the Arduino library
[**MBusinoLib**](https://github.com/Zeppelin500/MBusinoLib) (version 0.10.0,
GPL-3.0). It decodes M-Bus (Meterbus) **RSP_UD** telegrams - the answer a slave
sends to the master - using nothing but the Python standard library.

Every Python function carries a comment pointing at the C++ function it was
ported from, including the line number in `MBusinoLib.cpp` /
`MBusinoLib.h`, so you can always diff the two implementations side by side.

* **No runtime dependencies** - Python ≥ 3.9, standard library only.
* **Byte-for-byte value parity** with the C++ decoder (proven by golden tests,
  see [Testing](#testing)).
* New: `decode_telegram()` validates a *complete* frame (start/stop byte,
  declared length, checksum) before decoding header and records.

### Credits

Port based on **MBusinoLib** by Zeppelin500, which is based on the
[AllWize/mbus-payload](https://github.com/allwize/mbus-payload) library with
much more decode capability. Thanks to **AllWize** for the original library,
and thanks to **HWHardsoft** and **TrystanLea** for the M-Bus communication
used by [MBusino](https://github.com/Zeppelin500/MBusino).

## Installation

```bash
pip install .            # or: pip install -e .  (development checkout)
```

No third-party packages are required at runtime.

## Quick start

```python
from MBusinoLibPy import MBusinoLib

# A complete M-Bus long frame: 68 LL LL 68 C A CI ... CHK 16
telegram = bytes.fromhex(
    "68 C1 C1 68 08 00 72 09 34 75 73 C5 14 00 0D 43 00 00 00 04"
    "78 41 63 65 04 04 06 AA 29 00 00 04 13 40 A1 75 00 04 2B 00"
    "00 00 00 14 2B 3C F3 00 00 ... 75 16"          # shortened for readability
)

decode = MBusinoLib()
result = decode.decode_telegram(telegram)

print(result["frame"]["ok"], result["error_message"])   # True Kein Fehler
print(result["header"]["manufacturer"], result["header"]["id"])   # EFE 73753409
print(result["header"]["medium"])                      # Heat (Mass)

for record in result["records"]:
    print(record["name"], record.get("value_scaled"), record.get("units"))
# fab_number 73753409.0 None
# volume 7708.992 m³
# ...
```

A hex string works too (spaces, commas and `0x` prefixes are accepted):

```python
result = MBusinoLib().decode_telegram("68 1F 1F 68 08 00 72 78 56 34 ... CC 16")
```

## Decoding

### Method: `decode_telegram(raw)`

**New in the Python port** (no C++ counterpart). Validates a complete frame and
then decodes header and records:

```python
def decode_telegram(raw: bytes) -> dict
```

* `raw` - complete telegram as `bytes`/`bytearray`, a list of byte values, or a
  hex string.
* returns

  ```python
  {
      "frame": {          # frame checks
          "byte_count", "packet_size", "slave_address", "c_field", "ci_field",
          "start_ok", "length_ok", "fits", "stop_ok",
          "checksum", "checksum_received", "checksum_ok", "quartet_checksum_ok",
          "ok", "error_message",
      },
      "header": {...},    # decode_header() output
      "records": [...],   # decode_records() output
      "error": 0,         # MBUS_ERROR code of the decoding step
      "error_message": "...",  # German message for the first problem found
  }
  ```

Frame layout assumed (exactly as in `test_decode.cpp`):

| offset | meaning |
|--------|---------|
| 0, 3   | start bytes `0x68` |
| 1, 2   | length fields L1, L2 (must be equal) |
| 4      | C field (control) |
| 5      | A field (slave address) |
| 6      | CI field (`0x72`/`0x76` = variable data with fixed header) |
| 7 … 18 | fixed data header (ID, manufacturer, version, medium, counter, status, signature) |
| `0x13` (19) | **first data record** |
| `data[1] + 6` | `packet_size` = 4 header bytes + L + checksum + stop byte |
| `packet_size - 2` | checksum (sum of bytes from the C field up to here, mod 256) |
| `packet_size - 1` | stop byte `0x16` |

Records are decoded from offset `0x13` with length `packet_size - 0x13 - 2`
(both trailing bytes excluded) - the same calculation as `test_decode.cpp`.

Both the plain byte sum and the alternative *quartet* checksum (sum of all
half-bytes) are accepted; which one matched is reported individually.

### Method: `decode_records(buffer, size=None)`

```python
def decode_records(buffer, size=None) -> list[dict]
```

* `buffer` - record bytes, normally `telegram[0x13:packet_size]`.
* `size` - how many bytes to read (mirrors the C++ `uint8_t size` parameter).
  `test_decode.cpp` passes `packet_size - 0x13 - 2`, i.e. two bytes *less*
  than the slice length. Default: `len(buffer)`.
* returns the list of decoded records - the same content as the C++
  `JsonArray`.

Each record contains (keys are only present when the C++ code writes them):

| key | content |
|-----|---------|
| `vif` | VIF/VIFE as lower-case hex string, e.g. `"0xfd1b"` |
| `code` | `MBUS_CODE` value (the record type, *not* the VIF byte) |
| `value_scaled` | numeric value, already scaled - absent for pure ASCII records |
| `value_string` | formatted value (dates, ASCII) - only when the C++ sets it |
| `units` | unit such as `"Wh"`, `"m³"`, `"°C"` - absent when none applies |
| `name` | record name plus VIFE/function suffix, e.g. `"power_L1"` |
| `subUnit` | > 0 only |
| `storage` | > 0 only |
| `tariff` | > 0 only |
| `telegramFollow` | `1` when the frame ends with the `0x1F` marker |

> **Error semantics:** the C++ `decodeRecords()` *returns* `0` on error while
> the `JsonArray` keeps the records decoded so far. Python returns that
> partial list (it is what the C++ library prints as JSON) and reports the
> failure through `get_error()`.

### Method: `decode_header(buffer, length=None)`

```python
def decode_header(buffer, length=None) -> dict
```

* `buffer` - the **complete** telegram including start/stop bytes.
* `length` - usable length; pass `data[1] + 6` (`packet_size`) like the C++
  examples do. Default: `len(buffer)`.
* returns the header fields; the C++ `bool` result maps as follows:

| Python return | C++ return |
|---------------|-----------|
| `{}` | `false` before writing (too short, wrong start byte, L1 ≠ L2) |
| dict without `"id"` | `false` after writing (CI is not `0x72`/`0x76`) |
| dict with `"id"` | `true` |

Possible header fields:

* `len`, `c_field`, `address`, `ci_field` - basic frame header
* `id` - meter identification number as HEX string (4 byte BCD, LSB first)
* `manufacturer` - 3-letter manufacturer code
* `version`, `medium_code`, `medium` - meter version and medium as text
* `access_counter`, `status`
* `status_details` - nested dict: `battery_low`, `permanent_error`,
  `temporary_error`, `app_status`
* `signature`

> The C++ source writes the address under the key **`address`**
> (`MBusinoLib.cpp` line 1589); the C++ README calls it `a_field`. This port
> follows the **code**.

### Methods: `get_code_name`, `get_code_units`, `get_device_class`, `get_state_class`

```python
get_code_name(code)                 -> str     # "" when unknown
get_code_units(code)                -> str|None # None == C++ return 0 (NULL)
get_device_class(code, medium=0xFF) -> str     # "" when Home Assistant has no class
get_state_class(code)               -> str     # "" when not applicable
```

The four C++ `switch` statements are reproduced as complete lookup tables in
`MBusinoLibPy/lookup_tables.py`, grouped exactly like the C++ fall-through
groups. For the cumulative volume codes (`VOLUME_M3`/`FT3`/`GAL`) the
`medium` argument selects the Home Assistant `device_class`
(`water` / `gas` / `volume`) - same behaviour as in MBusinoLib 0.10.0.

```python
from MBusinoLibPy import MBUS_CODE, MBusinoLib

decode = MBusinoLib()
decode.get_code_name(MBUS_CODE.ENERGY_WH)            # 'energy'
decode.get_code_units(MBUS_CODE.VOLUME_M3)           # 'm³'
decode.get_device_class(MBUS_CODE.VOLUME_M3, 0x07)   # 'water' (medium = Water)
decode.get_device_class(MBUS_CODE.VOLUME_M3, 0x03)   # 'gas'   (medium = Gas)
decode.get_state_class(MBUS_CODE.ENERGY_WH)          # 'total_increasing'
```

### Method: `get_error`

```python
decode.get_error()         -> int   # MBUS_ERROR value, then reset to NO_ERROR
decode.get_error_message() -> str   # readable German message, does NOT reset
```

Exactly like `MBusinoLib::getError()` (`MBusinoLib.cpp` line 54): the value is
returned *and* cleared. `get_error_message()` only reads, so call it before
`get_error()` if you need both.

Possible error values (`MBUS_ERROR`, identical numbering to the C++):

| value | name | meaning while decoding |
|-------|------|------------------------|
| 0 | `NO_ERROR` | no error |
| 1 | `BUFFER_OVERFLOW` | declared length does not fit, or a record reaches past the buffer |
| 2 | `UNSUPPORTED_CODING` | (encoder legacy, never set while decoding) |
| 3 | `UNSUPPORTED_RANGE` | (encoder legacy, never set while decoding) |
| 4 | `UNSUPPORTED_VIF` | VIF is not in `vif_defs`; the record falls back to `unknown_vif` |
| 5 | `NEGATIVE_VALUE` | (encoder legacy, never set while decoding) |

### Enums

`MBUS_CODE` (123 members) and `MBUS_ERROR` (6 members) are `IntEnum`s with the
same member order - and therefore the same integer values - as the C++
enums in `MBusinoLib.h`. `VIF_DEFS` is the 1:1 copy of the `vif_defs` table
(132 entries: `(code, base, size, scalar)`).

## Differences from the C++ library

1. **No internal buffer API.** `reset()`, `getSize()`, `getBuffer()` and
   `copy()` are gone; you pass `bytes`/`bytearray` instead (the constructor
   takes no size argument).
2. **`decode_telegram()` is new** and performs the frame checks that
   `test_decode.cpp` does not (start/stop byte, L1 = L2, checksum).
3. **No undefined behaviour.** Wherever the C++ reads past the end of the
   buffer (several spots in `decodeRecords()`), Python stops and sets
   `BUFFER_OVERFLOW`; the affected lines are commented in the source.
4. **`get_error_message()` is new** - readable German text per error code.
5. `value_scaled` is computed with the same operations in the same order as in
   the C++, so the double results are bit-identical; only the *serialisation*
   by ArduinoJson rounds (see below).

## Testing

```bash
python3 -m unittest          # from the repository root (75 tests)
python3 -m pytest            # equivalent, if pytest is installed
```

The suite is **golden-based**: expected outputs were produced by the *actual
C++ library* and committed under `tests/golden/`.

* `tests/golden/*.hex` + `*.expected.json` - five real telegrams decoded by the
  original `test_decode` harness; `*.raw.txt` is its raw output,
  `*.source.json` documents where each telegram was found.
* `tests/golden/*.header.json` - `decodeHeader()` output for the same
  telegrams plus four negative cases.
* `tests/golden/records/*.json` - raw record buffers (the AUnit test vectors
  from `test/aunit/test.cpp`, excerpts from the golden telegrams and two
  documented edge cases).
* `tests/test_tables.py` - spot checks of enums, `vif_defs` and the four
  lookup tables against the C++ source.

`value_scaled` is compared with `math.isclose(rel_tol=1e-6, abs_tol=1e-6)`
(`ARDUINO_FLOAT_DECIMALS = 6`) because ArduinoJson rounds when serialising:
values below 1e7 are printed with 6 decimals, larger ones with 9 significant
digits (e.g. `202602132030` becomes `2.02602132e11`). Everything else -
`name`, `units`, `value_string`, `vif`, `code`, `subUnit`, `storage`, `tariff`,
`telegramFollow` and the key set itself - must match **exactly**. In practice
the observed deviation is at most `7.3e-08` relative; 80 of 88 numeric values
are bit-identical.

How to regenerate the golden files is documented in
[`tools/README.md`](tools/README.md).

## References

* [The M-Bus: A Documentation Rev. 4.8 - Appendix](https://m-bus.com/assets/downloads/MBDOC48.PDF)
* [Dedicated Application Layer (M-Bus)](https://datasheet.datasheetarchive.com/originals/crawler/m-bus.com/ba82a2f0a320ffda901a2d9814f48c24.pdf) by H. Ziegler
* [MBusinoLib (C++ original)](https://github.com/Zeppelin500/MBusinoLib)

## License

MBusinoLibPy is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

See [LICENSE](LICENSE) for the full text.
