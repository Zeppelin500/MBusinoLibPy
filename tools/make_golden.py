#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Creates (or checks) all golden files with the C++ harnesses.

Aufruf:

    python3 tools/make_golden.py --harness /tmp/mbusino-harness
    python3 tools/make_golden.py --harness /tmp/mbusino-harness --check

``--harness`` must contain these three executables:

* ``test_decode``         - the original harness from MBusinoLib/test
* ``test_decode_header``  - wrapper, only decodeHeader() (tools/test_decode_header.cpp)
* ``test_decode_records`` - wrapper, raw records (tools/test_decode_records.cpp)

The inputs already live in the repository (`tests/golden/*.hex` or the
``hex`` field in `tests/golden/records/*.json`); this script derives the
reference outputs from them. With ``--check`` it only compares
(exit code 1 on differences), without ``--check`` it overwrites.

See tools/README.md for the build instructions.
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

# Output of the original harness: Slave/Records/Error + formatted JSON array
_TELEGRAM_RE = re.compile(
    r"Slave Address: (\d+)\nRecords decoded: (\d+)\nError code: (\d+)\n\n(\[.*?\n\])\n",
    re.S,
)
# Wrapper: Records/Error + formatiertes JSON-Array
_RECORD_RE = re.compile(
    r"Records decoded: (\d+)\nError code: (\d+)\n\n(\[.*?\n\])\n", re.S
)
# Wrapper: "header_ok: 0|1" on the first line, then optionally the JSON object
# (an empty object comes as "{}" on ONE line - therefore no regex on it)


def run(binary: str, argument: str) -> str:
    """Pass hex input to the harness like test_decode.cpp reads it."""
    ergebnis = subprocess.run([binary, argument], capture_output=True, text=True)
    if ergebnis.returncode != 0:
        raise SystemExit("%s schlug fehl: %s" % (binary, ergebnis.stderr.strip()))
    return ergebnis.stdout


def als_json(objekt) -> str:
    return json.dumps(objekt, indent=2, ensure_ascii=False) + "\n"


def schreibe(pfad: str, inhalt: str, check: bool) -> bool:
    """Write a file or (with --check) compare it against what is there.

    :return: True if identical or updated, False on a difference
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
    print("Telegram goldens (.hex -> .expected.json/.raw.txt):")
    for hex_pfad in sorted(glob.glob(os.path.join(GOLDEN, "*.hex"))):
        name = os.path.basename(hex_pfad)[:-4]
        with open(hex_pfad, encoding="ascii") as handle:
            hex_text = handle.read().strip()
        ausgabe = run(harness, hex_text)
        match = _TELEGRAM_RE.search(ausgabe)
        if not match:
            raise SystemExit("%s: output not parseable (buffer too small?)" % name)
        record_list = json.loads(match.group(4))
        if int(match.group(2)) != len(record_list):
            raise SystemExit(
                "%s: the harness reports %s records but only %d are in the "
                "JSON - its buffer is too small (test_decode.cpp: char "
                "jsonBuf[4096]). Use a wrapper with a larger buffer, see "
                "tools/README.md." % (name, match.group(2), len(record_list))
            )
        erwartet = {
            "slave_address": int(match.group(1)),
            "records_decoded": int(match.group(2)),
            "error_code": int(match.group(3)),
            "records": record_list,
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
            raise SystemExit("%s: output not parseable" % os.path.basename(pfad))
        header_ok = bool(int(zeilen[0].split(":", 1)[1].strip()))
        body = "\n".join(zeilen[1:]).strip()
        try:
            header = json.loads(body) if body.startswith("{") else {}
        except ValueError as fehler:
            raise SystemExit("%s: invalid JSON: %s" % (os.path.basename(pfad), fehler))
        neu = {
            "hex": alt["hex"],
            "header_ok": header_ok,
            "header": header,
            # Herkunftsangabe bleibt unangetastet
            "source": alt.get("source", ""),
        }
        # order as before: hex, header_ok, header, source
        reihenfolge = ["hex", "header_ok", "header", "source"]
        neu = {key: neu[key] for key in reihenfolge if key in neu}
        ok &= schreibe(pfad, als_json(neu), check)
    return ok


def records_erzeugen(harness: str, check: bool) -> bool:
    ok = True
    print("Record goldens (records/*.json):")
    for pfad in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
        with open(pfad, encoding="utf-8") as handle:
            alt = json.load(handle)
        ausgabe = run(harness, alt["hex"])
        match = _RECORD_RE.search(ausgabe)
        if not match:
            raise SystemExit("%s: output not parseable" % os.path.basename(pfad))
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
                        help="directory with test_decode, test_decode_header, test_decode_records")
    parser.add_argument("--check", action="store_true",
                        help="only compare, do not overwrite (exit 1 on differences)")
    args = parser.parse_args()

    binaires = {}
    for name in ("test_decode", "test_decode_header", "test_decode_records"):
        pfad = os.path.join(args.harness, name)
        if not os.access(pfad, os.X_OK):
            raise SystemExit("not executable: %s" % pfad)
        binaires[name] = pfad

    alles_ok = True
    alles_ok &= telegramme_erzeugen(binaires["test_decode"], args.check)
    alles_ok &= header_erzeugen(binaires["test_decode_header"], args.check)
    alles_ok &= records_erzeugen(binaires["test_decode_records"], args.check)

    if args.check:
        print("\nRESULT: %s" % ("all golden files match the C++ harness"
                                  if alles_ok else "UNTERSCHIEDE GEFUNDEN"))
        return 0 if alles_ok else 1
    print("\nfertig - jetzt: python3 -m unittest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
