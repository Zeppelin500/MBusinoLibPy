# tools - generating / checking the golden files

The files under `tests/golden/` come from the **unmodified C++ library**.
This folder contains the three small wrappers used to produce them and the
script that regenerates everything.

> The C++ library itself is only **read** - nothing in the original repo
> `MBusinoLib` is modified. All binaries and intermediate files end up
> outside the repos (default: `/tmp`).

## Requirements

* `g++` (tested with 13.3)
* the headers of [ArduinoJson](https://github.com/bblanchon/ArduinoJson)
  (here: `~/Arduino/libraries/ArduinoJson`, version 7.4.3)
* the original repo `MBusinoLib` with `src/MBusinoLib.{h,cpp}` and the stub
  `test/Arduino.h`

## The three wrappers

| Wrapper | provides | Remark |
|---------|----------|--------|
| `test_decode` (original, `MBusinoLib/test/test_decode`) | `.hex` → `.expected.json`, `.raw.txt` | shipped in the original repo |
| `test_decode_header.cpp` | `.header.json` | only `decodeHeader()` as JSON |
| `test_decode_records.cpp` | `records/*.json` | raw buffers without a telegram frame |

All three call the same `MBusinoLib.cpp` - there is no own decoding logic in
the wrappers.

### Building

```bash
SRC=$HOME/.openclaw/workspace/MBusinoLib        # C++ original (read only)
AJ=$HOME/Arduino/libraries/ArduinoJson/src       # ArduinoJson headers
OUT=/tmp/mbusino-harness && mkdir -p "$OUT"

# IMPORTANT: -O0 and FORTIFY disabled. Otherwise the original compiles with
# _FORTIFY_SOURCE and aborts, because MBusinoLib.cpp lines 535/546 call
# snprintf(datestring, 24, ...) while datestring is only 16 bytes
# (bug in the original - the formatted text always fits anyway).
CXXFLAGS="-std=gnu++11 -O0 -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -w"

g++ $CXXFLAGS -I"$SRC/src" -I"$SRC/test" -I"$AJ" \
    tools/test_decode_header.cpp "$SRC/src/MBusinoLib.cpp" -o "$OUT/test_decode_header"

g++ $CXXFLAGS -I"$SRC/src" -I"$SRC/test" -I"$AJ" \
    tools/test_decode_records.cpp "$SRC/src/MBusinoLib.cpp" -o "$OUT/test_decode_records"
```

The original harness is used as it ships (pre-built): `$SRC/test/test_decode`.

### Special case `mbusino_example` (30 records)

`test_decode.cpp` buffers its JSON in `char jsonBuf[4096]` and truncates in
the middle of the JSON for 30 records (the raw output contains stack garbage
afterwards). For this single telegram a wrapper with `char jsonBuf[262144]`
was used - otherwise exactly the same file:

```bash
sed -e 's/char jsonBuf\[4096\]/char jsonBuf[262144]/' \
    "$SRC/test/test_decode.cpp" > "$OUT/test_decode_big.cpp"
g++ $CXXFLAGS -I"$SRC/src" -I"$SRC/test" -I"$AJ" \
    "$OUT/test_decode_big.cpp" "$SRC/src/MBusinoLib.cpp" -o "$OUT/test_decode_big"
```

**Proof of equivalence:** for the four shorter telegrams the output of
`test_decode` and `test_decode_big` is byte-identical (`diff`).

## Regenerating

```bash
# rewrite all golden files
python3 tools/make_golden.py --harness /tmp/mbusino-harness

# only verify, write nothing
python3 tools/make_golden.py --harness /tmp/mbusino-harness --check
```

Afterwards `python3 -m unittest` from the repository root - everything must
still be green.

## Hex input format

Space separated bytes, the way `test_decode` reads them from `argv`
(`0x` prefixes and commas are also accepted by `MBusinoLibPy._parse_hex`):

```
68 LL LL 68 C A CI  ID ID ID ID  MAN MAN VER MED CNT ST  SIG L  ...  CHK 16
```
