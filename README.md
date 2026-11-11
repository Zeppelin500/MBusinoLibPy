# MBusinoLibPy - a Python M-Bus Decoder

[![version](https://img.shields.io/badge/version-0.11.0-brightgreen.svg)](CHANGELOG.md)
[![PyPI](https://img.shields.io/badge/PyPI-MBusinoLibPy-blue.svg)](https://pypi.org/project/MBusinoLibPy/)
[![license](https://img.shields.io/badge/license-GPL--3.0-orange.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue.svg)](https://www.python.org/)
[![dependencies](https://img.shields.io/badge/runtime%20deps-0-brightgreen.svg)](pyproject.toml)

**MBusinoLibPy** decodes M-Bus (Meterbus) **RSP_UD** telegrams - the answer a
slave sends to the master - into plain Python dicts. It uses nothing but the
Python standard library and is the Python port of the Arduino library
[**MBusinoLib**](https://github.com/Zeppelin500/MBusinoLib) (v0.10.0,
GPL-3.0).

* **No runtime dependencies** - Python ≥ 3.9, standard library only.
* **Supports any M-Bus slave** - there is no fixed device list: any slave that
  answers with a standard RSP_UD telegram is supported.
* **Try it live in the browser** - the web decoder at
  <https://zeppelin500.github.io/MBusinoLibPy/> (source: [docs/](docs/))
  decodes a telegram with the Python port, the original C++ library and the
  Rust port side by side.
* Validates a *complete* frame (start/stop byte, declared length, checksum)
  before decoding header and records.
* Known record types come with readable names, units and Home Assistant
  metadata.

## Installation

Install the published package from PyPI:

```bash
pip install MBusinoLibPy
```

Distribution names are case-insensitive, so `pip install mbusinolibpy` works
just as well.

Want the latest state straight from GitHub instead? Install from the repository:

```bash
pip install git+https://github.com/Zeppelin500/MBusinoLibPy.git
```

Working on the code itself? Use a development checkout:

```bash
git clone https://github.com/Zeppelin500/MBusinoLibPy.git
cd MBusinoLibPy
pip install -e .
```

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

print(result["frame"]["ok"], result["error_message"])   # True No error
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

More runnable examples: [examples/](examples/) - start with
[`examples/minimal_hex_to_json.py`](examples/minimal_hex_to_json.py)
(hex spaghetti in, JSON out).

## API reference

All decoding entry points are methods of the `MBusinoLib` class.

### `decode_telegram(raw)`

```python
def decode_telegram(raw: bytes) -> dict
```

Validates a complete frame and then decodes header and records.

* `raw` - complete telegram as `bytes`/`bytearray`, a list of byte values, or
  a hex string.
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
      "error": 0,         # error code of the decoding step (see Error handling)
      "error_message": "...",  # message for the first problem found
  }
  ```

  `frame["ok"]` is `True` only when everything matched: start bytes, equal
  length fields, declared length vs. actual size, stop byte and checksum.
  The checksum is verified both as a plain byte sum and as an alternative
  *quartet* (half-byte) sum - either match counts, and both results are
  reported individually.

### `decode_records(buffer, size=None)`

```python
def decode_records(buffer, size=None) -> list[dict]
```

* `buffer` - record bytes, normally `telegram[0x13:packet_size]`.
* `size` - how many bytes to read. Default: `len(buffer)`.
* returns the list of decoded records.

Each record contains these keys (a key is only present when the telegram
carries it):

| key | content |
|-----|---------|
| `vif` | VIF/VIFE as lower-case hex string, e.g. `"0xfd1b"` |
| `code` | `MBUS_CODE` value (the internal record type, *not* the VIF byte) |
| `value_scaled` | numeric value, already scaled - absent for pure ASCII records |
| `value_string` | formatted value (dates, ASCII) |
| `units` | unit such as `"Wh"`, `"m³"`, `"°C"` - absent when none applies |
| `name` | record name plus VIFE/function suffix, e.g. `"power_L1"` |
| `subUnit` | > 0 only |
| `storage` | > 0 only |
| `tariff` | > 0 only |
| `telegramFollow` | `1` when the frame ends with the `0x1F` marker |

> **Error semantics:** when a record would run past the end of the buffer,
> decoding stops, `BUFFER_OVERFLOW` is set, and the records decoded so far
> are returned - so a partial result is always usable.

### `decode_header(buffer, length=None)`

```python
def decode_header(buffer, length=None) -> dict
```

* `buffer` - the **complete** telegram including start/stop bytes.
* `length` - usable length of the telegram. Default: `len(buffer)`.
* returns the header fields; an empty/partial dict signals failure:

| Python return | meaning |
|---------------|---------|
| `{}` | failed before writing (too short, wrong start byte, L1 ≠ L2) |
| dict without `"id"` | failed after writing (CI is not `0x72`/`0x76`) |
| dict with `"id"` | success |

Possible header fields:

* `len`, `c_field`, `address`, `ci_field` - basic frame header
* `id` - meter identification number as HEX string (4 byte BCD, LSB first)
* `manufacturer` - 3-letter manufacturer code
* `version`, `medium_code`, `medium` - meter version and medium as text
* `access_counter`, `status`
* `status_details` - nested dict: `battery_low`, `permanent_error`,
  `temporary_error`, `app_status`
* `signature`

### `get_code_name`, `get_code_units`, `get_device_class`, `get_state_class`

```python
get_code_name(code)                 -> str      # "" when unknown
get_code_units(code)                -> str|None # None == no unit
get_device_class(code, medium=0xFF) -> str      # "" when Home Assistant has no class
get_state_class(code)               -> str      # "" when not applicable
```

Four lookup methods for `MBUS_CODE` values, implemented as complete lookup
tables in `MBusinoLibPy/lookup_tables.py`. For the cumulative volume codes
(`VOLUME_M3`/`FT3`/`GAL`) the `medium` argument selects the Home Assistant
`device_class` (`water` / `gas` / `volume`).

```python
from MBusinoLibPy import MBUS_CODE, MBusinoLib

decode = MBusinoLib()
decode.get_code_name(MBUS_CODE.ENERGY_WH)            # 'energy'
decode.get_code_units(MBUS_CODE.VOLUME_M3)           # 'm³'
decode.get_device_class(MBUS_CODE.VOLUME_M3, 0x07)   # 'water' (medium = Water)
decode.get_device_class(MBUS_CODE.VOLUME_M3, 0x03)   # 'gas'   (medium = Gas)
decode.get_state_class(MBUS_CODE.ENERGY_WH)          # 'total_increasing'
```

### `get_error` / `get_error_message`

```python
decode.get_error()         -> int   # error code, then reset to NO_ERROR
decode.get_error_message(code=None) -> str  # readable message, does NOT reset
```

`get_error()` returns the stored error code **and** clears it, so the next
call starts fresh. `get_error_message()` only reads - with no argument it
reports the currently stored error, with a code argument it translates that
code. Call `get_error_message()` before `get_error()` if you need both.

## Error handling

Problems show up in two places:

* **frame level** - `result["frame"]["ok"]` is `False` and
  `result["frame"]["error_message"]` says what was wrong (start byte, length
  fields, truncation, stop byte, checksum).
* **decoding level** - `result["error"]` carries an error code and
  `result["error_message"]` the matching text.

The decoder itself can produce these codes:

| value | name | meaning |
|-------|------|---------|
| 0 | `NO_ERROR` | no error |
| 1 | `BUFFER_OVERFLOW` | declared length does not fit, or a record reaches past the buffer |
| 4 | `UNSUPPORTED_VIF` | VIF is not known; the record falls back to `unknown_vif` |

The C++ enum also numbers three encoder leftovers - `UNSUPPORTED_CODING` (2),
`UNSUPPORTED_RANGE` (3) and `NEGATIVE_VALUE` (5). The decoder never sets
them, so they were removed from the Python enum; the gaps in the numbering
are deliberate and the surviving codes keep their original C++ values.

How to check errors:

```python
result = MBusinoLib().decode_telegram(telegram)

if not result["frame"]["ok"]:
    print(result["frame"]["error_message"])     # e.g. "Checksum mismatch: ..."
if result["error"] != 0:
    print(result["error_message"])              # e.g. "Unknown or unsupported VIF - ..."
```

When decoding records directly, use the instance methods (note that
`get_error()` clears the value):

```python
decode = MBusinoLib()
records = decode.decode_records(buf)
code = decode.get_error()                       # int, reset to 0 afterwards
if code != 0:
    print(decode.get_error_message(code))
```

### Enums

`MBUS_CODE` (123 members) and `MBUS_ERROR` (3 members) are `IntEnum`s.
`VIF_DEFS` is the VIF definition table (132 entries: `(code, base, size,
scalar)`).

## License

MBusinoLibPy is free software under the GNU General Public License v3 (or
later) - see [LICENSE](LICENSE).

## Development

Run the test suite from the repository root: `python3 -m unittest`.

Internal development notes and open points from the implementation live in
[dev_issues/](dev_issues/README.md).
