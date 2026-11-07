# -*- coding: utf-8 -*-
"""Golden tests for RECORD decoding (without a telegram frame).

These cases come from two sources:

1. ``MBusinoLib/test/aunit/test.cpp`` - the original AllWize decoder tests,
   which pass raw buffers instead of a whole telegram.
2. Real record excerpts from the golden telegrams (e.g. the
   ASCII record piece of the Elster meter) plus two deliberately
   constructed edge cases - all with their origin in the respective file.

Produced with the C++ harness ``test_decode_records`` (identical
MBusinoLib.cpp, eigener main()-Wrapper).
"""

import unittest

from MBusinoLibPy import MBUS_ERROR, MBusinoLib

from .helpers import compare_records, golden_records


class TestGoldenRecords(unittest.TestCase):
    """Raw record buffer against the C++ reference output."""

    def test_all_record_goldens_match(self):
        for case in golden_records():
            with self.subTest(case=case["_name"]):
                data = bytes(int(token, 16) for token in case["hex"].split())
                decoder = MBusinoLib()
                records = decoder.decode_records(data)
                error = decoder.get_error()
                self.assertEqual(error, case["error_code"],
                                 "error code differs from the C++ harness")
                problems = compare_records(records, case["records"], case["_name"])
                self.assertEqual(problems, [], "\n".join(problems))

    def test_aunit_cases_covered(self):
        """The decoder tests from test.cpp are taken over completely."""
        names = {case["_name"] for case in golden_records()}
        for erwartet in ("aunit_number_1", "aunit_number_2", "aunit_number_3",
                         "aunit_number_4", "aunit_number_6", "aunit_multifield",
                         "aunit_decode_2bcd", "aunit_decode_8bcd"):
            self.assertIn(erwartet, names)

    def test_cpp_return_value_vs_json_array(self):
        """QUIRK: on error decodeRecords() returns 0 in C++,
        but the JsonArray stays partially filled.

        Python returns the content of the JsonArray (that is what the
        C++ harness prints as JSON) - the error is reported by get_error().
        """
        case = [c for c in golden_records() if c["_name"] == "konstrukt_var_bcd"][0]
        data = bytes(int(token, 16) for token in case["hex"].split())
        decoder = MBusinoLib()
        records = decoder.decode_records(data)
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        # C++ return value (error case) ...
        self.assertEqual(case["records_decoded"], 0)
        # ... but the JsonArray holds the record already decoded,
        # and that is exactly what Python returns:
        self.assertEqual(len(records), len(case["records"]))
        self.assertEqual(len(records), 1)

    def test_unsupported_vif_sets_error(self):
        """0x7E is the "unknown" hint used by the original; a VIF
        outside all definitions raises UNSUPPORTED_VIF (C++ line 281-285)."""
        # 0x6E = HCA - im Original in vif_defs auskommentiert (MBusinoLib.h
        # line 222: `//{ MBUS_CODE::HCA , 0x6E , 1, 0},`), therefore no match
        decoder = MBusinoLib()
        records = decoder.decode_records(bytes([0x01, 0x6E, 0x2A]))
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.UNSUPPORTED_VIF))
        # The original CONTINUES with entry 0 (def = 0), therefore:
        # unknown_vif, code 0 AND (because def == 0) no scaling - the value
        # stays the raw 42 (C++ line 586: `if(def != 0)` does not apply)
        self.assertEqual(records[0]["name"], "unknown_vif")
        self.assertEqual(records[0]["code"], 0)
        self.assertEqual(records[0]["vif"], "0x6e")
        self.assertEqual(records[0]["value_scaled"], 42.0)
        self.assertNotIn("units", records[0])

    def test_buffer_overflow_is_reported(self):
        """Record reaching past the end -> BUFFER_OVERFLOW
        (C++ line 380-384: `if (index + len > size)`)."""
        # DIF 0x07 = 64-bit integer, but only 1 byte of data present
        decoder = MBusinoLib()
        records = decoder.decode_records(bytes([0x07, 0x00, 0x11]))
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(records, [])

    def test_buffer_overflow_keeps_already_decoded_records(self):
        """Two records, the second runs past the buffer."""
        # record 1 complete (DIF 01, VIF 00, 1 byte), then DIF 07 without data
        decoder = MBusinoLib()
        records = decoder.decode_records(bytes([0x01, 0x00, 0x2A, 0x07, 0x00]))
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(len(records), 1)
        # DIF 01 + VIF 00 (ENERGY_WH, Skalar -3) + 0x2A = 42 -> 0.042 Wh
        self.assertEqual(records[0]["value_scaled"], 0.042)


if __name__ == "__main__":
    unittest.main()
