# tools - Golden-Dateien erzeugen / prüfen

Die Dateien unter `tests/golden/` stammen aus der **unveränderten
C++-Bibliothek**. Dieses Verzeichnis enthält die drei kleinen Wrapper, mit
denen sie erzeugt wurden, und das Skript, das alles neu anlegt.

> Die C++-Bibliothek selbst wird **nur gelesen** – nichts im Original-Repo
> `MBusinoLib` wird verändert. Alle Binärdateien und Zwischenstände landen
> außerhalb der Repos (Standard: `/tmp`).

## Voraussetzungen

* `g++` (getestet mit 13.3)
* die Header von [ArduinoJson](https://github.com/bblanchon/ArduinoJson)
  (hier: `~/Arduino/libraries/ArduinoJson`, Version 7.4.3)
* das Original-Repo `MBusinoLib` mit `src/MBusinoLib.{h,cpp}` und dem
  Stub `test/Arduino.h`

## Die drei Hüllen

| Wrapper | liefert | Bemerkung |
|---------|---------|-----------|
| `test_decode` (Original, `MBusinoLib/test/test_decode`) | `.hex` → `.expected.json`, `.raw.txt` | wie im Original-Repo vorhanden |
| `test_decode_header.cpp` | `.header.json` | nur `decodeHeader()` als JSON |
| `test_decode_records.cpp` | `records/*.json` | Rohpuffer ohne Telegrammrahmen |

Alle drei rufen dieselbe `MBusinoLib.cpp` auf – es gibt keine eigene
Dekodierlogik in den Wrappern.

### Bauen

```bash
SRC=$HOME/.openclaw/workspace/MBusinoLib        # C++-Original (nur lesen)
AJ=$HOME/Arduino/libraries/ArduinoJson/src       # ArduinoJson-Header
OUT=/tmp/mbusino-harness && mkdir -p "$OUT"

# WICHTIG: -O0 und FORTIFY aus. Das Original kompiliert sonst mit
# _FORTIFY_SOURCE und stürzt ab, weil MBusinoLib.cpp Zeile 535/546
# snprintf(datestring, 24, ...) aufruft, obwohl datestring nur 16 Byte hat
# (Bug im Original - der formatierte Text passt trotzdem immer hinein).
CXXFLAGS="-std=gnu++11 -O0 -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -w"

g++ $CXXFLAGS -I"$SRC/src" -I"$SRC/test" -I"$AJ" \
    tools/test_decode_header.cpp "$SRC/src/MBusinoLib.cpp" -o "$OUT/test_decode_header"

g++ $CXXFLAGS -I"$SRC/src" -I"$SRC/test" -I"$AJ" \
    tools/test_decode_records.cpp "$SRC/src/MBusinoLib.cpp" -o "$OUT/test_decode_records"
```

Der originale Harness wird einfach mitgeliefert (vorkompiliert):
`$SRC/test/test_decode`.

### Sonderfall `mbusino_example` (30 Datensätze)

`test_decode.cpp` puffert sein JSON in `char jsonBuf[4096]` und schneidet bei
30 Datensätzen mitten im JSON ab (im Roh-Output steht danach Stack-Müll).
Für dieses eine Telegramm wurde daher ein Wrapper mit `char jsonBuf[262144]`
benutzt – sonst exakt dieselbe Datei:

```bash
sed -e 's/char jsonBuf\[4096\]/char jsonBuf[262144]/' \
    "$SRC/test/test_decode.cpp" > "$OUT/test_decode_big.cpp"
g++ $CXXFLAGS -I"$SRC/src" -I"$SRC/test" -I"$AJ" \
    "$OUT/test_decode_big.cpp" "$SRC/src/MBusinoLib.cpp" -o "$OUT/test_decode_big"
```

**Nachweis der Äquivalenz:** für die vier kürzeren Telegramme ist die Ausgabe
von `test_decode` und `test_decode_big` per `diff` byte-identisch.

## Neu erzeugen

```bash
# alle Golden-Dateien neu schreiben
python3 tools/make_golden.py --harness /tmp/mbusino-harness

# nur prüfen, ohne etwas anzuschreiben
python3 tools/make_golden.py --harness /tmp/mbusino-harness --check
```

Danach `python3 -m unittest` aus dem Repo-Wurzelverzeichnis – es muss
weiterhin alles grün sein.

## Aufbau der Hex-Eingabe

Leerzeichen-getrennte Bytes, wie `test_decode` sie aus `argv` liest
(`0x`-Präfixe und Kommas werden von `MBusinoLibPy._parse_hex` ebenfalls
verstanden):

```
68 LL LL 68 C A CI  ID ID ID ID  MAN MAN VER MED CNT ST  SIG L  ...  CHK 16
```
