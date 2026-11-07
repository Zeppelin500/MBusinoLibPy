# -*- coding: utf-8 -*-
"""Golden tests for ``decode_header()``.

Produced with the C++ harness ``test_decode_header`` (same MBusinoLib.cpp,
own main() wrapper that prints only ``decodeHeader()`` as JSON).

Enthaltend:

* the five real golden telegrams (complete fixed data header)
* four negative cases: CI not 0x72/0x76, unequal length fields,
  length parameter below 19, wrong start byte
"""

import json
import os
import unittest

from MBusinoLibPy import MBusinoLib

from . import GOLDEN_DIR
from .helpers import read_hex


def _header_golden():
    out = []
    for filename in sorted(os.listdir(GOLDEN_DIR)):
        if not filename.endswith(".header.json"):
            continue
        with open(os.path.join(GOLDEN_DIR, filename), encoding="utf-8") as handle:
            item = json.load(handle)
        item["_name"] = filename[: -len(".header.json")]
        out.append(item)
    return out


class TestGoldenHeader(unittest.TestCase):
    """decodeHeader() against the C++ reference output."""

    def test_all_header_goldens(self):
        for case in _header_golden():
            with self.subTest(case=case["_name"]):
                data = read_hex_from_text(case["hex"])
                packet_size = data[1] + 6  # wie im C++-Harness
                result = MBusinoLib().decode_header(data, packet_size)

                # C++: boolean criterion. true <=> the original wrote the full
                # fixed data header fields <=> "id" is present.
                self.assertEqual(
                    "id" in result, case["header_ok"],
                    "bool-Status weicht ab (C++ meldete %s)" % case["header_ok"],
                )
                self.assertEqual(result, case["header"],
                                 "header fields differ from the C++ output")

    def test_header_ok_flag_matches_cxx_for_all_cases(self):
        """Additionally explicit: the key "id" marks the C++ true case."""
        ok_fälle = [c for c in _header_golden() if c["header_ok"]]
        self.assertGreaterEqual(len(ok_fälle), 5)


class TestHeaderDetails(unittest.TestCase):
    """Fixed values from the EFE heat meter telegram."""

    def setUp(self):
        case = [c for c in _header_golden() if c["_name"] == "efe_heat_meter"][0]
        data = read_hex_from_text(case["hex"])
        self.header = MBusinoLib().decode_header(data, data[1] + 6)

    def test_identity_and_medium(self):
        # id: 4 byte BCD, LSB first (bytes 7..10 = 09 34 75 73 -> "73753409")
        self.assertEqual(self.header["id"], "73753409")
        # manufacturer: 2 byte LSB first (C5 14) -> 3x5-bit -> "EFE"
        self.assertEqual(self.header["manufacturer"], "EFE")
        # medium 0x0D = "Heat (Mass)" (MBusinoLib.cpp line 1625)
        self.assertEqual(self.header["medium_code"], 0x0D)
        self.assertEqual(self.header["medium"], "Heat (Mass)")
        self.assertEqual(self.header["version"], 0)
        self.assertEqual(self.header["access_counter"], 0x43)
        self.assertEqual(self.header["status"], 0)
        self.assertEqual(self.header["signature"], 0)

    def test_status_details_structure(self):
        """status_details is a nested dict like the JsonArray in C++."""
        details = self.header["status_details"]
        self.assertEqual(
            set(details), {"battery_low", "permanent_error", "temporary_error", "app_status"}
        )
        self.assertEqual(details["app_status"], "no_error")
        self.assertIs(details["battery_low"], False)

    def test_status_bit_decode(self):
        """Individual status bits (MBusinoLib.cpp line 1645-1651)."""
        data = bytearray(read_hex_from_text(
            [c for c in _header_golden() if c["_name"] == "efe_heat_meter"][0]["hex"]
        ))
        data[16] = 0x04 | 0x08 | 0x10 | 0x01  # battery_low + permanent + temporary + busy
        header = MBusinoLib().decode_header(bytes(data), len(data))
        self.assertIs(header["status_details"]["battery_low"], True)
        self.assertIs(header["status_details"]["permanent_error"], True)
        self.assertIs(header["status_details"]["temporary_error"], True)
        self.assertEqual(header["status_details"]["app_status"], "busy")
        # app_error == 3 (reserviert) bekommt im Original KEINEN Key
        data[16] = 0x03
        header = MBusinoLib().decode_header(bytes(data), len(data))
        self.assertNotIn("app_status", header["status_details"])


class TestHeaderErrorCases(unittest.TestCase):
    """Error cases - returning {} corresponds to C++ `return false` BEFORE writing."""

    def test_empty_on_missing_start_bytes(self):
        # 19 zeros: no 0x68 at position 0 and 3
        self.assertEqual(MBusinoLib().decode_header(bytes(19)), {})

    def test_empty_on_length_mismatch(self):
        data = bytearray(bytes(19))
        data[0] = data[3] = 0x68
        data[1] = 10
        data[2] = 11
        self.assertEqual(MBusinoLib().decode_header(bytes(data)), {})

    def test_empty_when_length_parameter_below_19(self):
        data = bytes(30)   # gross genug, aber length-Argument zu klein
        self.assertEqual(MBusinoLib().decode_header(data, 18), {})

    def test_short_buffer_returns_empty_instead_of_reading_out_of_bounds(self):
        """Deliberate deviation: the original reads past the end when
        `length >= 19` but the buffer is shorter (undefined behaviour - in
        the C++ harness you saw random values). Python returns {} and reads nothing."""
        self.assertEqual(MBusinoLib().decode_header(bytes(10), 37), {})

    def test_basic_fields_only_when_ci_is_not_variable(self):
        """CI neither 0x72 nor 0x76 -> only the four basic fields, C++: false."""
        data = bytearray(bytes(25))
        data[0] = data[3] = 0x68
        data[1] = data[2] = 19
        data[6] = 0x7A   # CI "short header" - not 0x72/0x76
        header = MBusinoLib().decode_header(bytes(data))
        self.assertEqual(header, {"len": 19, "c_field": 0, "address": 0, "ci_field": 0x7A})
        self.assertNotIn("id", header)


def read_hex_from_text(text: str) -> bytes:
    return bytes(int(token, 16) for token in text.split())


if __name__ == "__main__":
    unittest.main()
