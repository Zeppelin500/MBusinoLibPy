#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""The minimal end-to-end example: hex spaghetti in, JSON out.

Run it from the repository root, no installation required::

    python3 examples/minimal_hex_to_json.py

This is the copy-paste-and-run variant: the telegram is inlined on purpose,
so the whole example fits in a handful of lines. It is the real
``hw_thermostat`` capture from ``tests/golden/`` (provenance:
``tests/golden/hw_thermostat.source.json``). For the file-based variant with
more commentary see ``examples/basic_decode.py``.
"""

import json
import os
import sys

# See examples/basic_decode.py for why src/ is put on the path here - this is
# what lets the example run from a plain checkout without installation.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from MBusinoLibPy import MBusinoLib  # noqa: E402  (path setup first)

# A complete M-Bus long frame: 68 LL LL 68 C A CI ... CHK 16.
# decode_telegram() accepts spaces, commas and 0x prefixes alike.
HEX_SPAGHETTI = (
    "68 53 53 68 08 02 72 11 82 00 24 96 15 16 00 20 00 00 00 01 "
    "FD 1B 00 02 FC 03 48 52 25 74 62 17 22 FC 03 48 52 25 74 5C 17 "
    "12 FC 03 48 52 25 74 68 17 02 65 A2 08 22 65 9E 08 12 65 A2 08 "
    "01 72 00 72 65 00 00 B2 01 65 00 00 0C 78 11 82 00 24 03 FD 0F "
    "05 09 03 1F 9F 16"
)


def main() -> None:
    result = MBusinoLib().decode_telegram(HEX_SPAGHETTI)

    # decode_telegram() returns a plain dict (frame + header + records), so it
    # serialises straight to JSON - no custom encoder needed.
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
