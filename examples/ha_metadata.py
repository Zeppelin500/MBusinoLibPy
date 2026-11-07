#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Home Assistant metadata: the four lookup methods plus error handling.

Run it from the repository root, no installation required::

    python3 examples/ha_metadata.py

None of this needs a telegram - the lookups are plain tables that mirror the
four C++ switch methods (``MBusinoLib.cpp`` lines 660, 847, 1182 and 1382).
The last section shows ``get_error()`` / ``get_error_message()`` and their
read-vs-read-and-clear difference.
"""

import os
import sys

# See examples/basic_decode.py for why src/ is put on the path here.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from MBusinoLibPy import MBUS_CODE, MEDIUM_NAMES, MBusinoLib  # noqa: E402


def main() -> None:
    decode = MBusinoLib()

    # --- name and unit of a record type ---------------------------------
    print("name:  ", decode.get_code_name(MBUS_CODE.ENERGY_WH))          # energy
    print("units: ", decode.get_code_units(MBUS_CODE.VOLUME_M3))         # m³
    print("units: ", decode.get_code_units(MBUS_CODE.UNKNOWN_VIF))       # None (C++: return 0 / NULL)

    # --- device_class: for the volume codes the medium byte decides -----
    # medium 0x07 = Water, 0x03 = Gas, anything else (incl. 0xFF) = volume
    for medium in (0x07, 0x03, 0xFF):
        label = MEDIUM_NAMES.get(medium, "unknown")
        print("device_class %-8s 0x%02X:" % (label, medium),
              decode.get_device_class(MBUS_CODE.VOLUME_M3, medium))
    # device_class Water    0x07: water
    # device_class Gas      0x03: gas
    # device_class unknown  0xFF: volume

    print("state:  ", decode.get_state_class(MBUS_CODE.ENERGY_WH))       # total_increasing

    # --- error handling -------------------------------------------------
    # get_error_message() only reads, get_error() returns the code AND
    # resets it - so always read the message FIRST (fresh instance here):
    print("message:", decode.get_error_message())                         # No error.
    print("code:   ", decode.get_error())                                 # 0

    # A record buffer that stops in the middle of a record sets an error,
    # exactly like the C++ decoder (BUFFER_OVERFLOW = 1):
    broken = MBusinoLib()
    print("records:", broken.decode_records(bytes.fromhex("04 78 41"), 4))  # []
    print("message:", broken.get_error_message())
    # Buffer too small or telegram incomplete: the declared length does not fit ...
    print("code:   ", broken.get_error())                                 # 1 (and clears)
    print("message:", broken.get_error_message())                         # No error. (cleared)

    # Frame problems (start/stop byte, length, checksum) are NEW - the C++
    # original does not check them - and arrive in the result dict:
    result = MBusinoLib().decode_telegram("68 05 05 68 08 00 72")
    print("frame ok:", result["frame"]["ok"])                             # False
    print("code:    ", result["error"])                                   # 1
    print("message: ", result["error_message"])                           # Buffer too small or telegram incomplete: ...


if __name__ == "__main__":
    main()
