# Golden-Referenzen (Testdaten aus dem C++-Original)

Alles in diesem Ordner wurde **von der unveränderten C++-Bibliothek
`MBusinoLib` erzeugt** und dient als Referenzoutput für die Python-Tests.
Es wurde nichts erfunden oder von Hand nachgerechnet.

## Aufbau

| Datei | Inhalt |
|-------|--------|
| `<name>.hex` | Eingabe: ein komplettes Telegramm, Leertrennung wie bei `./test_decode "68 56 ..."` |
| `<name>.expected.json` | Erwartetes Ergebnis: `slave_address`, `records_decoded`, `error_code`, `records` (das geparste JSON-Array des Harness) |
| `<name>.raw.txt` | Rohausgabe des Harness (unverändert, inkl. der `[n] name (vif) = wert` Zeilen) |
| `<name>.source.json` | **Herkunft**: Quelldatei + Zeilennummer, Erkennungsmerkmale, Besonderheiten |
| `<name>.header.json` | Erwartetes Ergebnis von `decodeHeader()` plus `header_ok` (der bool-Rückgabewert des C++) |
| `records/<name>.json` | Rohdatensatz-Puffer ohne Telegrammrahmen: `hex`, `records_decoded`, `error_code`, `records`, `source` |

## Die fünf Telegramme

Alle stammen aus den für diesen Port durchsuchten Repositories
`MBusino` und `MBusinoLib` (Datei + Zeile steht jeweils in der `source.json`):

| Name | Bytes | L | Datensätze | Checksumme | Hersteller / ID / Medium | Fundstelle |
|------|-------|---|-----------|-----------|--------------------------|------------|
| `efe_heat_meter` | 199 | 193 | 29 | 0x75 gültig | EFE / 73753409 / Heat (Mass) | `MBusino/archive/telegram_test/telegram_test.ino:94` (aktives `mbus_data[]`) |
| `ernie_power_meter` | 164 | 158 | 16 | 0x8B gültig | IME / 00067609 / Electricity | `MBusino/playground/MBusino_ernie/MBusino_ernie.ino:514` |
| `hw_thermostat` | 89 | 83 | 12 | 0x9F gültig | ELV / 24008211 / Unknown | `MBusino/archive/telegram_test/telegram_test.ino:92` |
| `mbusino_example` | 202 | 196 | 30 | 0xFB gültig | WZG / 29079172 / Cold water | `MBusinoLib/examples/MbusinoLibExample/MbusinoLibExample.ino:15` |
| `elster` | 37 | 31 | 2 | **0xCC statt 0xCF – ungültig** | ELS / 12345678 / Gas | `MBusino/archive/telegram_test/telegram_test.ino:96` |

Abdeckung der Pfade:

* `efe_heat_meter` – längstes realistisches Set an Datensätzen: 32-Bit-Ganzzahl,
  BCD, real, Datum Typ F und Typ G, Doppelvolumen-VIF (0x933A/0x943A),
  Speicher-/Tarif-DIFE.
* `ernie_power_meter` – Drehstromzähler mit Phasen-VIFE (0xFC/0xFF → `_L1`…),
  SubUnit, 0xFF-Herstellerdaten (uns skaliert) und der **0x0F-Marke**
  (Abbruch „manufacturer specific", `MBusinoLib.cpp` Zeile 648).
* `hw_thermostat` – ASCII-VIF (0xFC mit eigenem Einheitstext) und die
  **0x1F-Marke** („mehr Datensätze folgen", `telegramFollow`, Zeile 652).
* `mbusino_example` – 30 Datensätze, Speicher 1–6, Status-/Fehlerdatensätze.
* `elster` – **bewusst fehlerhafte Checksumme** (Quellen-Tippfehler). Das
  C++-Original prüft keine Checksumme und dekodiert es trotzdem; der Test
  prüft, dass `decode_telegram()` genau das in `frame["ok"] = False`
  sichtbar macht, die Datensatzanzahl aber gleich bleibt.

Weitere Hinweise zu jedem Telegramm (warum es gewählt wurde, welche
Besonderheit es abdeckt) stehen in den jeweiligen `*.source.json`.

## Datensatz-Golden (`records/`)

* `aunit_*` – die acht Decoder-Testvektoren aus
  `MBusinoLib/test/aunit/test.cpp` (`Number_1`…`Number_6`, `MultiField`,
  `Decode_2bcd`, `Decode_8bcd`). Achtung: Diese Datei ist gegen die aktuelle
  Bibliothek veraltet (sie ruft Encoder-Methoden auf, die es nicht mehr gibt,
  und `Find_Definition` erwartet Index 0, obwohl `UNKNOWN_VIF` inzwischen an
  erster Stelle der `vif_defs`-Tabelle steht) – genutzt werden deshalb nur
  die Puffer, nicht die dortigen Erwartungswerte.
* `excerpt_*` – echte Datensatz-Ausschnitte aus den Golden-Telegrammen
  (ASCII-Variable-Length aus `elster`, Datum Typ F/G aus `efe_heat_meter`,
  BCD mit F-Halbbyte-Negativzeichen aus `hw_thermostat`).
* `konstrukt_*` – zwei bewusst konstruierte Grenzfälle zur Abdeckung von
  DIF 0x03 (24 Bit) und DIF 0x0D + LVAR 0xC0 (positiv. BCD). Beide sind
  Ein-Puffer-Unit-Tests, **keine** Telegramme und nicht Teil der
  Telegramm-Golden; die Herkunft steht in der jeweiligen `source`-Angabe.

`records/…/konstrukt_var_bcd` ist besonders interessant: Der C++-Harness
meldet hier `Records decoded: 0` (Rückgabewert bei `BUFFER_OVERFLOW`), das
JSON-Array enthält aber bereits einen Datensatz. Der Python-Test prüft
genau dieses Verhalten.

## Wie die Dateien entstanden sind

Siehe [`tools/README.md`](../../tools/README.md) – kurz:

1. `test_decode` (vorkompiliert im Original-Repo) für `.hex`/`.expected.json`/`.raw.txt`
2. `tools/test_decode_header.cpp` für `.header.json`
3. `tools/test_decode_records.cpp` für `records/*.json`

Für `mbusino_example` musste ein Wrapper mit größerem JSON-Puffer her
(4096 Byte reichen für 30 Datensätze nicht; der Wrapper ist sonst
byte-identisch, was an den vier kürzeren Telegrammen nachgewiesen ist).

## Vergleichsregeln im Test

* `name`, `units`, `value_string`, `vif`, `code`, `subUnit`, `storage`,
  `tariff`, `telegramFollow` **exakt**, ebenso die Menge der Keys.
* `value_scaled` mit `math.isclose(rel_tol=1e-6, abs_tol=1e-6)`
  (`ARDUINO_FLOAT_DECIMALS = 6`), weil ArduinoJson beim Serialisieren rundet:
  kleine Werte mit 6 Nachkommastellen, große mit 9 signifikanten Stellen
  (`202602132030` → `"2.02602132e11"`).
  Über alle 123 verglichenen Golden-Datensätze gemessen: 89 von 102 Zahlen-
  werten stimmen bit-identisch, größte Abweichung `7.3e-08` relativ
  (ArduinoJson rundet hier einen Datumswert), null Key-Abweichungen.
* Datensatzanzahl und Fehlercode müssen exakt übereinstimmen.
