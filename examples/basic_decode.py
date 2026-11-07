#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decode one complete M-Bus telegram - the smallest useful end-to-end example.

Run it from the repository root, no installation required::

    python3 examples/basic_decode.py

The telegram is the real ``efe_heat_meter`` capture from ``tests/golden/``.
Where exactly it was found (source file + line, recognition features) is
documented in ``tests/golden/efe_heat_meter.source.json`` and
``tests/golden/README.md`` - everything in that folder was produced by the
unmodified C++ library.
"""

import os
import sys

# This repository uses a src/ layout: "import MBusinoLibPy" only works after
# an installation. Adding ../src (relative to THIS file, not the current
# working directory) makes the example run from a plain checkout - the same
# trick the tests use in tests/__init__.py.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from MBusinoLibPy import MBusinoLib  # noqa: E402  (path setup first)

# Space separated hex input, exactly like the original test_decode harness.
TELEGRAM_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tests", "golden", "efe_heat_meter.hex"
)


def main() -> None:
    with open(TELEGRAM_FILE, encoding="ascii") as handle:
        telegram = " ".join(handle.read().split())

    decode = MBusinoLib()
    result = decode.decode_telegram(telegram)

    # Frame check: True only when start/stop byte, both length fields,
    # declared length and checksum (byte sum OR quartet sum) all matched.
    print("frame ok:", result["frame"]["ok"], "-", result["error_message"])  # frame ok: True - No error

    # Fixed data header: id / manufacturer / version / medium and friends.
    for key, value in result["header"].items():
        print("  %-16s %s" % (key + ":", value))
    #   len:             193
    #   manufacturer:    EFE
    #   id:              73753409
    #   medium:          Heat (Mass)
    #   ...

    # Every record: name, value (numeric, already scaled - or the formatted
    # string for dates/ASCII records) and the unit when one applies.
    records = result["records"]
    print("records (%d), error %d:" % (len(records), result["error"]))  # records (29), error 0:
    for record in records:
        value = record.get("value_scaled", record.get("value_string"))
        units = record.get("units") or ""
        print(("  %-24s %14s %s" % (record["name"], value, units)).rstrip())
    #   fab_number           73753409.0
    #   energy               10666000.0 Wh
    #   volume                 7708.992 m³
    #   flow_temperature          25.0 °C
    #   time_point         202310171003.0 YYYYMMDDhhmm


if __name__ == "__main__":
    main()
