#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decode only the record area of a telegram - the ``test_decode.cpp`` slice.

Run it from the repository root, no installation required::

    python3 examples/decode_records.py

This is the low-level path: no frame check, no header - just
``decode_records()`` on the payload bytes, cut exactly like the original
harness cuts them (``test_decode.cpp`` lines 51-66). For the comfortable
variant with frame validation use ``examples/basic_decode.py``.

The telegram is the real ``hw_thermostat`` capture from ``tests/golden/``
(provenance: ``tests/golden/hw_thermostat.source.json``).
"""

import os
import sys

# See examples/basic_decode.py for why src/ is put on the path here.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from MBusinoLibPy import MBusinoLib  # noqa: E402

HEX_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tests", "golden", "hw_thermostat.hex"
)


def main() -> None:
    with open(HEX_FILE, encoding="ascii") as handle:
        data = bytes(int(token, 16) for token in handle.read().split())

    # test_decode.cpp line 51: packet_size = L + 6 (4 start/length bytes,
    # L bytes from the C field to the last data byte, checksum, stop byte).
    packet_size = data[1] + 6
    # test_decode.cpp line 53/64: records start at 0x13 (skip frame header
    # + fixed data header) and their length leaves out checksum and stop byte.
    start_address = 0x13
    data_len = packet_size - start_address - 2

    decode = MBusinoLib()
    records = decode.decode_records(data[start_address:packet_size], data_len)

    print("slave address:", data[5])                    # 2
    print("packet size:  ", packet_size)                # 89
    print("record bytes: ", data_len)                   # 68
    print("records (%d):" % len(records))               # records (12):
    for record in records:
        value = record.get("value_scaled", record.get("value_string"))
        units = record.get("units") or ""
        extra = ""
        if record.get("telegramFollow"):
            extra = " [more records follow, 0x1F marker]"
        print(("  %-24s %14s %s%s" % (record["name"], value, units, extra)).rstrip())
    #   customized_vif                 59.86 %RH   (ASCII unit text, VIF 0xFC)
    #   external_temperature              22.1 °C
    #   fab_number                 24008211.0
    #   software_version            198917.0  [more records follow, 0x1F marker]

    # Read the message BEFORE get_error(): get_error() returns the code and
    # clears it in the same call (like MBusinoLib::getError() in C++).
    print("error message:", decode.get_error_message())  # No error.
    print("error code:   ", decode.get_error())          # 0


if __name__ == "__main__":
    main()
