# -*- coding: utf-8 -*-
"""Shared helpers for the golden tests.

Vergleichsregeln
----------------
``name``, ``units``, ``value_string``, ``vif``, ``code``, ``subUnit``,
``storage``, ``tariff`` and ``telegramFollow`` must match **exactly** -
just like in the C++ JSON. The same applies to the key set (the ArduinoJson
record only keeps keys that are present).

``value_scaled`` may deviate slightly, because ArduinoJson rounds the number
while serialising (observed on the original harness: small values with
6 decimals, large ones with 9 significant digits, e.g.
202602132030 -> "2.02602132e11"). Deshalb:

    math.isclose(py_wert, cxx_wert, rel_tol=1e-6, abs_tol=1e-6)

``1e-6`` corresponds to ``ARDUINO_FLOAT_DECIMALS = 6`` from MBusinoLib.h. In
practice the real deviation is much smaller (see README),
because the calculations are bit-identical to the C++.
"""

import json
import math
import os
import re

from . import GOLDEN_DIR

#: tolerance for value_scaled (ARDUINO_FLOAT_DECIMALS = 6)
VALUE_REL_TOL = 1e-6
VALUE_ABS_TOL = 1e-6


def read_hex(path: str) -> bytes:
    """Reads a .hex file (space separated) like the harness reads argv."""
    with open(path, encoding="ascii") as handle:
        return bytes(int(token, 16) for token in handle.read().split())


def golden_telegrams():
    """All telegram golden files as a list of dicts."""
    out = []
    for filename in sorted(os.listdir(GOLDEN_DIR)):
        if not filename.endswith(".expected.json"):
            continue
        base = filename[: -len(".expected.json")]
        with open(os.path.join(GOLDEN_DIR, filename), encoding="utf-8") as handle:
            expected = json.load(handle)
        expected["_name"] = base
        expected["_hex"] = read_hex(os.path.join(GOLDEN_DIR, base + ".hex"))
        expected["_source"] = json.load(
            open(os.path.join(GOLDEN_DIR, base + ".source.json"), encoding="utf-8")
        )
        out.append(expected)
    return out


def golden_records():
    """All record golden files (tests/golden/records)."""
    out = []
    folder = os.path.join(GOLDEN_DIR, "records")
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(folder, filename), encoding="utf-8") as handle:
            item = json.load(handle)
        item["_name"] = filename[: -len(".json")]
        out.append(item)
    return out


def compare_records(got, want, label="") -> list:
    """Compares two record lists, see the module docstring for the rules.

    :return: list of found deviations (empty = everything identical)
    """
    problems = []
    if len(got) != len(want):
        problems.append("%s: Anzahl %d statt %d" % (label, len(got), len(want)))
    for index, (g_item, w_item) in enumerate(zip(got, want)):
        where = "%s[%d]" % (label, index)
        if set(g_item) != set(w_item):
            problems.append("%s: keys differ: only here %s / only there %s"
                            % (where, sorted(set(g_item) - set(w_item)),
                               sorted(set(w_item) - set(g_item))))
            continue
        for key in w_item:
            if key == "value_scaled":
                if not math.isclose(float(g_item[key]), float(w_item[key]),
                                    rel_tol=VALUE_REL_TOL, abs_tol=VALUE_ABS_TOL):
                    problems.append("%s: value_scaled %r != %r (Abweichung %g)"
                                    % (where, g_item[key], w_item[key],
                                       abs(float(g_item[key]) - float(w_item[key]))))
            elif g_item[key] != w_item[key]:
                problems.append("%s: %s %r != %r" % (where, key, g_item[key], w_item[key]))
    return problems


def records_like_test_decode(hex_text: str):
    """Runs exactly the flow of test_decode.cpp line 51-66.

    ``packet_size = data[1] + 6``, records from offset ``0x13`` with the
    length ``packet_size - 0x13 - 2`` (i.e. without checksum and stop byte,
    even though the buffer is 2 bytes longer - exactly like in C++).
    """
    from MBusinoLibPy import MBusinoLib  # erst nach sys.path-Einhang

    data = bytes(int(token, 16) for token in hex_text.split())
    packet_size = data[1] + 6
    start_address = 0x13
    data_len = packet_size - start_address - 2
    decoder = MBusinoLib()
    records = decoder.decode_records(data[start_address:packet_size], data_len)
    return data, packet_size, records, decoder.get_error()


def parse_harness_output(text: str) -> dict:
    """Parses the output of test_decode (for reproduction purposes)."""
    match = re.search(
        r"Slave Address: (\d+)\nRecords decoded: (\d+)\nError code: (\d+)\n\n(\[.*?\n\])\n",
        text,
        re.S,
    )
    if not match:
        raise ValueError("harness output not parseable")
    return {
        "slave_address": int(match.group(1)),
        "records_decoded": int(match.group(2)),
        "error_code": int(match.group(3)),
        "records": json.loads(match.group(4)),
    }
