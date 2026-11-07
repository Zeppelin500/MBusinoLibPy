# -*- coding: utf-8 -*-
"""Golden tests for TELEGRAM decoding.

Five real telegrams found in the MBusino-/MBusinoLib sources were fed
through the C++ harness ``test_decode``; its output is stored as
``tests/golden/<name>.expected.json``. The Python port must deliver
exactly the same records.

Origin and circumstances of every file are in
``tests/golden/<name>.source.json`` and in ``tests/golden/README.md``.
"""

import unittest

from MBusinoLibPy import MBUS_ERROR, MBusinoLib

from .helpers import compare_records, golden_telegrams, records_like_test_decode


class TestGoldenTelegrams(unittest.TestCase):
    """The complete flow of test_decode.cpp against the C++ reference."""

    def test_at_least_five_golden_telegrams(self):
        """Requirement: at least 3-5 real telegrams as golden reference."""
        telegrams = golden_telegrams()
        self.assertGreaterEqual(
            len(telegrams), 5,
            "fewer than 5 golden telegrams found - check the provenance",
        )

    def test_every_golden_has_documented_source(self):
        """Every golden telegram needs a traceable source."""
        for telegram in golden_telegrams():
            with self.subTest(telegram=telegram["_name"]):
                source = telegram["_source"]
                self.assertTrue(source.get("src", "").strip(),
                                "source missing for %s" % telegram["_name"])
                self.assertTrue(source.get("note", "").strip(),
                                "provenance note missing for %s" % telegram["_name"])

    def test_records_match_cpp_reference(self):
        """Records, count and error code like in the C++ harness."""
        for telegram in golden_telegrams():
            with self.subTest(telegram=telegram["_name"]):
                _data, _size, records, error = records_like_test_decode(
                    " ".join("%02X" % b for b in telegram["_hex"])
                )
                self.assertEqual(
                    error, telegram["error_code"],
                    "error code differs from the C++ harness",
                )
                self.assertEqual(
                    len(records), telegram["records_decoded"],
                    "number of decoded records differs from the C++ harness",
                )
                problems = compare_records(records, telegram["records"], telegram["_name"])
                self.assertEqual(problems, [], "\n".join(problems))

    def test_record_keys_match_arduinojson_output(self):
        """The keys are identical to the ArduinoJson output of the original."""
        erlaubt = {"vif", "code", "value_scaled", "value_string", "units",
                   "name", "subUnit", "storage", "tariff", "telegramFollow"}
        gefunden = set()
        for telegram in golden_telegrams():
            for record in telegram["records"]:
                self.assertTrue(set(record) <= erlaubt,
                                "unerwartete Keys: %s" % (set(record) - erlaubt))
                gefunden |= set(record)
        # make sure the golden data really covers all paths
        for erwartet in ("vif", "code", "value_scaled", "name", "units",
                         "value_string", "subUnit", "storage"):
            self.assertIn(erwartet, gefunden,
                          "key %s does not appear in any golden telegram" % erwartet)

    def test_known_values_from_reference_telegram(self):
        """A few fixed markers from the EFE heat meter (manufacturer/ID/medium)."""
        efe = [t for t in golden_telegrams() if t["_name"] == "efe_heat_meter"][0]
        _data, _size, records, _error = records_like_test_decode(
            " ".join("%02X" % b for b in efe["_hex"])
        )
        # first record in the harness: fab_number = 73753409 (firmware version)
        self.assertEqual(records[0]["name"], "fab_number")
        self.assertEqual(records[0]["vif"], "0x78")
        self.assertAlmostEqual(records[0]["value_scaled"], 73753409.0, places=3)
        # 0x03 (inside the ENERGY_WH definition) -> table index 1,
        # because UNKNOWN_VIF sits at position 0 (in C++ AND Python). The
        # AUnit expectation "0" in test.cpp line 244 predates that.
        self.assertEqual(MBusinoLib._find_definition(0x03), 1)


class TestGoldenErrorCodes(unittest.TestCase):
    """All telegrams must decode without errors (the C++ reference too)."""

    def test_no_decode_errors_in_golden_set(self):
        for telegram in golden_telegrams():
            with self.subTest(telegram=telegram["_name"]):
                self.assertEqual(telegram["error_code"], int(MBUS_ERROR.NO_ERROR))
                _d, _s, records, error = records_like_test_decode(
                    " ".join("%02X" % b for b in telegram["_hex"])
                )
                self.assertEqual(int(error), int(MBUS_ERROR.NO_ERROR))


if __name__ == "__main__":
    unittest.main()
