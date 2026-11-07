# -*- coding: utf-8 -*-
"""Tests for ``decode_telegram()`` - the NEW method without a C++ counterpart.

It wraps the flow of ``test_decode.cpp`` (frame check, ``packet_size =
data[1] + 6``, records from offset ``0x13``) around the checks that are
NOT done there: start/stop byte, length fields and checksum.
"""

import json
import os
import unittest

from MBusinoLibPy import MBUS_ERROR, MBusinoLib

from . import GOLDEN_DIR
from .helpers import golden_telegrams


def _by_name(name):
    for telegram in golden_telegrams():
        if telegram["_name"] == name:
            return telegram
    raise AssertionError(name)


def _hex_bytes(telegram):
    return telegram["_hex"]


class TestDecodeTelegramHappyPath(unittest.TestCase):
    """All five real golden telegrams."""

    def test_frame_header_and_records_are_consistent(self):
        for telegram in golden_telegrams():
            with self.subTest(telegram=telegram["_name"]):
                result = MBusinoLib().decode_telegram(_hex_bytes(telegram))
                data = _hex_bytes(telegram)
                packet_size = data[1] + 6

                # Rahmen
                frame = result["frame"]
                self.assertEqual(frame["byte_count"], len(data))
                self.assertEqual(frame["packet_size"], packet_size)
                self.assertTrue(frame["start_ok"])
                self.assertTrue(frame["length_ok"])
                self.assertTrue(frame["fits"])
                self.assertTrue(frame["stop_ok"])
                self.assertEqual(frame["slave_address"], data[5])
                self.assertEqual(frame["c_field"], data[4])
                self.assertEqual(frame["ci_field"], data[6])
                # checksum like EN 13757: sum from the C field up to before the checksum
                erwartet = sum(data[4:packet_size - 2]) & 0xFF
                self.assertEqual(frame["checksum"], erwartet)
                self.assertEqual(frame["checksum_received"], data[packet_size - 2])

                # records must match the telegram golden
                self.assertEqual(len(result["records"]), telegram["records_decoded"])
                self.assertEqual(result["error"], telegram["error_code"])

                # header against its own header golden
                header_golden = json.load(
                    open(os.path.join(GOLDEN_DIR, telegram["_name"] + ".header.json"),
                         encoding="utf-8")
                )
                self.assertEqual(result["header"], header_golden["header"])

    def test_four_telegrams_have_valid_checksums(self):
        """Four of the five telegrams have a valid byte sum; the
        Elster telegram does not (typo in the source, see source.json)."""
        ok, schlecht = [], []
        for telegram in golden_telegrams():
            result = MBusinoLib().decode_telegram(_hex_bytes(telegram))
            (ok if result["frame"]["checksum_ok"] else schlecht).append(telegram["_name"])
        self.assertEqual(sorted(schlecht), ["elster"])
        self.assertEqual(len(ok), 4)
        for name in ok:
            self.assertIn(name, ["efe_heat_meter", "ernie_power_meter",
                                 "hw_thermostat", "mbusino_example"])

    def test_error_and_message_for_clean_telegram(self):
        result = MBusinoLib().decode_telegram(_by_name("efe_heat_meter")["_hex"])
        self.assertEqual(result["error"], int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(result["error_message"], "Kein Fehler")
        self.assertTrue(result["frame"]["ok"])
        self.assertEqual(result["frame"]["error_message"], "")


class TestDecodeTelegramErrors(unittest.TestCase):
    """Frame errors - start/stop byte, length, checksum."""

    def _elster(self):
        return bytearray(_by_name("elster")["_hex"])

    def test_too_short(self):
        result = MBusinoLib().decode_telegram(bytes([0x68, 0x05]))
        self.assertEqual(result["error"], int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertFalse(result["frame"]["ok"])
        self.assertIsNone(result["frame"]["packet_size"])
        self.assertIsNone(result["frame"]["slave_address"])
        self.assertEqual(result["header"], {})
        self.assertEqual(result["records"], [])
        self.assertIn("zu kurz", result["frame"]["error_message"])
        self.assertEqual(result["error_message"],
                         MBusinoLib().get_error_message(MBUS_ERROR.BUFFER_OVERFLOW))

    def test_wrong_start_byte(self):
        data = self._elster()
        data[0] = 0x10
        result = MBusinoLib().decode_telegram(bytes(data))
        self.assertFalse(result["frame"]["start_ok"])
        self.assertFalse(result["frame"]["ok"])
        self.assertIn("Startbyte", result["frame"]["error_message"])
        # without 0x68 the header cannot be read (C++ returns false) ...
        self.assertEqual(result["header"], {})
        # ... the records are read anyway, like in the original
        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["error"], int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(result["error_message"], result["frame"]["error_message"])

    def test_second_start_byte_missing(self):
        data = self._elster()
        data[3] = 0x15
        result = MBusinoLib().decode_telegram(bytes(data))
        self.assertFalse(result["frame"]["start_ok"])

    def test_length_fields_differ(self):
        data = self._elster()
        data[2] ^= 0x01
        result = MBusinoLib().decode_telegram(bytes(data))
        self.assertFalse(result["frame"]["length_ok"])
        self.assertFalse(result["frame"]["ok"])
        self.assertIn("Laengenfelder ungleich", result["frame"]["error_message"])
        self.assertEqual(result["header"], {})   # C++: false before writing

    def test_declared_length_exceeds_buffer(self):
        """test_decode.cpp aborts with "declared length ... but only N bytes" -
        here BUFFER_OVERFLOW, no decoding."""
        data = self._elster()          # 37 bytes, length field 0x1F = 31
        data[1] = data[2] = 0x50       # would mean an 86 byte frame
        result = MBusinoLib().decode_telegram(bytes(data))
        self.assertFalse(result["frame"]["fits"])
        self.assertFalse(result["frame"]["ok"])
        self.assertEqual(result["error"], int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(result["records"], [])
        self.assertEqual(result["header"], {})
        self.assertEqual(result["error_message"],
                         MBusinoLib().get_error_message(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertIn("erwartet 86 Bytes", result["frame"]["error_message"])

    def test_wrong_stop_byte(self):
        data = self._elster()
        data[-1] = 0x15
        result = MBusinoLib().decode_telegram(bytes(data))
        self.assertFalse(result["frame"]["stop_ok"])
        self.assertFalse(result["frame"]["ok"])
        self.assertIn("Stopbyte", result["frame"]["error_message"])
        # decoding continues (the original does not check the stop byte)
        self.assertEqual(len(result["records"]), 2)

    def test_wrong_checksum_is_reported_but_records_are_decoded(self):
        """The Elster telegram carries 0xCC, 0xCF would be correct."""
        result = MBusinoLib().decode_telegram(_by_name("elster")["_hex"])
        frame = result["frame"]
        self.assertFalse(frame["checksum_ok"])
        self.assertFalse(frame["quartet_checksum_ok"])
        self.assertFalse(frame["ok"])
        self.assertEqual(frame["checksum"], 0xCF)
        self.assertEqual(frame["checksum_received"], 0xCC)
        self.assertIn("Checksumme", frame["error_message"])
        # error code stays 0: MBUS_ERROR has no checksum code,
        # error_message reports the problem anyway (see docstring)
        self.assertEqual(result["error"], int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(result["error_message"], frame["error_message"])
        self.assertEqual(len(result["records"]), 2)

    def test_quartet_checksum_is_accepted(self):
        """Quartet sum (sum of all half bytes) as a valid alternative."""
        data = self._elster()
        packet_size = data[1] + 6
        quartet = 0
        for byte in data[4:packet_size - 2]:
            quartet += (byte & 0x0F) + (byte >> 4)
        data[packet_size - 2] = quartet & 0xFF
        result = MBusinoLib().decode_telegram(bytes(data))
        self.assertFalse(result["frame"]["checksum_ok"])
        self.assertTrue(result["frame"]["quartet_checksum_ok"])
        self.assertTrue(result["frame"]["ok"])
        self.assertEqual(result["error_message"], "Kein Fehler")

    def test_hex_string_input(self):
        """Hex text like in the harness (spaces, commas, 0x prefixes)."""
        text = " ".join("0x%02X" % b for b in _by_name("elster")["_hex"])
        result = MBusinoLib().decode_telegram(text)
        self.assertEqual(len(result["records"]), 2)
        # same result as with bytes
        gleich = MBusinoLib().decode_telegram(_by_name("elster")["_hex"])
        self.assertEqual(result["records"], gleich["records"])

    def test_error_is_reset_between_calls(self):
        """decode_telegram clears the internal error (see docstring)."""
        lib = MBusinoLib()
        # first a telegram with an error
        kaputt = bytearray(_by_name("elster")["_hex"])
        kaputt[1] = kaputt[2] = 0x50
        lib.decode_telegram(bytes(kaputt))
        # then a clean one
        result = lib.decode_telegram(_by_name("efe_heat_meter")["_hex"])
        self.assertEqual(result["error"], int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))


if __name__ == "__main__":
    unittest.main()
