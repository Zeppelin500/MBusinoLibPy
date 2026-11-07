#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Erzeugt (oder prüft) alle Golden-Dateien mit den C++-Harnessen.

Aufruf:

    python3 tools/make_golden.py --harness /tmp/mbusino-harness
    python3 tools/make_golden.py --harness /tmp/mbusino-harness --check

``--harness`` muss diese drei ausführenbaren Dateien enthalten:

* ``test_decode``        - der Original-Harness aus MBusinoLib/test
* ``test_decode_header`` - Wrapper, nur decodeHeader() (tools/test_decode_header.cpp)
* ``test_decode_records``- Wrapper, Rohdatensätze (tools/test_decode_records.cpp)

Die Eingaben liegen bereits im Repository (`tests/golden/*.hex` bzw. das
Feld ``hex`` in `tests/golden/records/*.json`); dieses Skript leitet daraus
die Referenz-Ausgaben neu ab. Mit ``--check`` wird nur verglichen
(Exit-Code 1 bei Unterschieden), ohne ``--check`` überschrieben.

Siehe tools/README.md für die Build-Anleitung.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(REPO, "tests", "golden")
RECORDS = os.path.join(GOLDEN, "records")

# Ausgabe des Original-Harness: Slave/Records/Error + formatiertes JSON-Array
_TELEGRAM_RE = re.compile(
    r"Slave Address: (\d+)\nRecords decoded: (\d+)\nError code: (\d+)\n\n(\[.*?\n\])\n",
    re.S,
)
# Wrapper: Records/Error + formatiertes JSON-Array
_RECORD_RE = re.compile(
    r"Records decoded: (\d+)\nError code: (\d+)\n\n(\[.*?\n\])\n", re.S
)
# Wrapper: "header_ok: 0|1" als erste Zeile, danach ggf. das JSON-Objekt
# (ein leeres Objekt kommt als "{}" EINER Zeile - deshalb kein Regex darauf)


def run(binary: str, argument: str) -> str:
    """Hex-Eingabe an den Harness übergeben wie test_decode.cpp sie liest."""
    ergebnis = subprocess.run([binary, argument], capture_output=True, text=True)
    if ergebnis.returncode != 0:
        raise SystemExit("%s schlug fehl: %s" % (binary, ergebnis.stderr.strip()))
    return ergebnis.stdout


def als_json(objekt) -> str:
    return json.dumps(objekt, indent=2, ensure_ascii=False) + "\n"


def schreibe(pfad: str, inhalt: str, check: bool) -> bool:
    """Datei schreiben oder (bei --check) gegen den Bestand vergleichen.

    :return: True wenn identisch bzw. aktualisiert, False bei Unterschied
    """
    vorhanden = None
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as handle:
            vorhanden = handle.read()
    if vorhanden == inhalt:
        return True
    if check:
        print("  UNGLEICH: %s" % os.path.relpath(pfad, REPO))
        return False
    with open(pfad, "w", encoding="utf-8", newline="") as handle:
        handle.write(inhalt)
    print("  geschrieben: %s" % os.path.relpath(pfad, REPO))
    return False


def telegramme_erzeugen(harness: str, check: bool) -> bool:
    ok = True
    print("Telegramm-Golden (.hex -> .expected.json/.raw.txt):")
    for hex_pfad in sorted(glob.glob(os.path.join(GOLDEN, "*.hex"))):
        name = os.path.basename(hex_pfad)[:-4]
        with open(hex_pfad, encoding="ascii") as handle:
            hex_text = handle.read().strip()
        ausgabe = run(harness, hex_text)
        match = _TELEGRAM_RE.search(ausgabe)
        if not match:
            raise SystemExit("%s: Ausgabe nicht parsebar (Puffer zu klein?)" % name)
        datensätze = json.loads(match.group(4))
        if int(match.group(2)) != len(datensätze):
            raise SystemExit(
                "%s: der Harness meldet %s Datensätze, liefert aber nur %d im "
                "JSON - sein Puffer reicht nicht (test_decode.cpp: char "
                "jsonBuf[4096]). Wrapper mit größerem Puffer benutzen, s. "
                "tools/README.md." % (name, match.group(2), len(datensätze))
            )
        erwartet = {
            "slave_address": int(match.group(1)),
            "records_decoded": int(match.group(2)),
            "error_code": int(match.group(3)),
            "records": datensätze,
        }
        ok &= schreibe(os.path.join(GOLDEN, name + ".expected.json"),
                       als_json(erwartet), check)
        ok &= schreibe(os.path.join(GOLDEN, name + ".raw.txt"), ausgabe, check)
    return ok


def header_erzeugen(harness: str, check: bool) -> bool:
    ok = True
    print("Header-Golden (.header.json):")
    for pfad in sorted(glob.glob(os.path.join(GOLDEN, "*.header.json"))):
        with open(pfad, encoding="utf-8") as handle:
            alt = json.load(handle)
        ausgabe = run(harness, alt["hex"])
        zeilen = ausgabe.splitlines()
        if not zeilen or not zeilen[0].startswith("header_ok:"):
            raise SystemExit("%s: Ausgabe nicht parsebar" % os.path.basename(pfad))
        header_ok = bool(int(zeilen[0].split(":", 1)[1].strip()))
        körperer = "\n".join(zeilen[1:]).strip()
        try:
            header = json.loads(körperer) if körperer.startswith("{") else {}
        except ValueError as fehler:
            raise SystemExit("%s: JSON ungültig: %s" % (os.path.basename(pfad), fehler))
        neu = {
            "hex": alt["hex"],
            "header_ok": header_ok,
            "header": header,
            # Herkunftsangabe bleibt unangetastet
            "source": alt.get("source", ""),
        }
        # Reihenfolge wie bisher: hex, header_ok, header, source
        reihenfolge = ["hex", "header_ok", "header", "source"]
        neu = {key: neu[key] for key in reihenfolge if key in neu}
        ok &= schreibe(pfad, als_json(neu), check)
    return ok


def records_erzeugen(harness: str, check: bool) -> bool:
    ok = True
    print("Datensatz-Golden (records/*.json):")
    for pfad in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
        with open(pfad, encoding="utf-8") as handle:
            alt = json.load(handle)
        ausgabe = run(harness, alt["hex"])
        match = _RECORD_RE.search(ausgabe)
        if not match:
            raise SystemExit("%s: Ausgabe nicht parsebar" % os.path.basename(pfad))
        neu = {
            "hex": alt["hex"],
            "records_decoded": int(match.group(1)),
            "error_code": int(match.group(2)),
            "records": json.loads(match.group(3)),
            "source": alt.get("source", ""),
        }
        ok &= schreibe(pfad, als_json(neu), check)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness", required=True,
                        help="Verzeichnis mit test_decode, test_decode_header, test_decode_records")
    parser.add_argument("--check", action="store_true",
                        help="nur vergleichen, nichts überschreiben (Exit 1 bei Unterschieden)")
    args = parser.parse_args()

    binaires = {}
    for name in ("test_decode", "test_decode_header", "test_decode_records"):
        pfad = os.path.join(args.harness, name)
        if not os.access(pfad, os.X_OK):
            raise SystemExit("nicht ausführenbar: %s" % pfad)
        binaires[name] = pfad

    alles_ok = True
    alles_ok &= telegramme_erzeugen(binaires["test_decode"], args.check)
    alles_ok &= header_erzeugen(binaires["test_decode_header"], args.check)
    alles_ok &= records_erzeugen(binaires["test_decode_records"], args.check)

    if args.check:
        print("\nERGEBNIS: %s" % ("alle Golden-Dateien stimmen mit dem C++-Harness überein"
                                  if alles_ok else "UNTERSCHIEDE GEFUNDEN"))
        return 0 if alles_ok else 1
    print("\nfertig - jetzt: python3 -m unittest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
