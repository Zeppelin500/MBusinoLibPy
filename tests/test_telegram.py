# -*- coding: utf-8 -*-
"""Tests für ``decode_telegram()`` - die NEUE Metode ohne C++-Gegenstück.

Sie packt den Ablauf aus ``test_decode.cpp`` (Rahmenprüfung, ``packet_size =
data[1] + 6``, Datensätze ab Offset ``0x13``) um die Prüfungen, die dort
NICHT gemacht werden: Start-/Stopbyte, Längenfelder und Checksumme.
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
    """Alle fünf echten Golden-Telegramme."""

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
                # Checksumme wie EN 13757: Summe ab C-Feld bis vor die Checksumme
                erwartet = sum(data[4:packet_size - 2]) & 0xFF
                self.assertEqual(frame["checksum"], erwartet)
                self.assertEqual(frame["checksum_received"], data[packet_size - 2])

                # Datensätze müssen dem Telegramm-Golden entsprechen
                self.assertEqual(len(result["records"]), telegram["records_decoded"])
                self.assertEqual(result["error"], telegram["error_code"])

                # Kopf gegen das eigene Header-Golden
                header_golden = json.load(
                    open(os.path.join(GOLDEN_DIR, telegram["_name"] + ".header.json"),
                         encoding="utf-8")
                )
                self.assertEqual(result["header"], header_golden["header"])

    def test_four_telegrams_have_valid_checksums(self):
        """Vier der fünf Telegramme haben eine gültige Byte-Summe; das
        Elster-Telegramm nicht (Tippfehler in der Quelle, s. source.json)."""
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
    """Rahmenfehler - Start/Ende-Byte, Länge, Checksumme."""

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
        # Ohne 0x68 kann der Header nicht gelesen werden (C++ gibt false aus) ...
        self.assertEqual(result["header"], {})
        # ... die Datensätze werden wie im Original trotzdem gelesen
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
        self.assertIn("Längenfelder ungleich", result["frame"]["error_message"])
        self.assertEqual(result["header"], {})   # C++: false vor dem Schreiben

    def test_declared_length_exceeds_buffer(self):
        """test_decode.cpp bricht mit "declared length ... but only N bytes" ab -
        hier BUFFER_OVERFLOW, keine Dekodierung."""
        data = self._elster()          # 37 Bytes, Länge-Feld 0x1F = 31
        data[1] = data[2] = 0x50       # würde 86 Bytes Rahmen bedeuten
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
        # Dekodierung läuft weiter (das Original prüft das Stopbyte nicht)
        self.assertEqual(len(result["records"]), 2)

    def test_wrong_checksum_is_reported_but_records_are_decoded(self):
        """Das Elster-Telegramm trägt 0xCC, korrekt wäre 0xCF."""
        result = MBusinoLib().decode_telegram(_by_name("elster")["_hex"])
        frame = result["frame"]
        self.assertFalse(frame["checksum_ok"])
        self.assertFalse(frame["quartet_checksum_ok"])
        self.assertFalse(frame["ok"])
        self.assertEqual(frame["checksum"], 0xCF)
        self.assertEqual(frame["checksum_received"], 0xCC)
        self.assertIn("Checksumme", frame["error_message"])
        # Fehlercode bleibt 0: MBUS_ERROR hat keinen Checksummen-Code,
        # error_message meldet das Problem trotzdem (s. Docstring)
        self.assertEqual(result["error"], int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(result["error_message"], frame["error_message"])
        self.assertEqual(len(result["records"]), 2)

    def test_quartet_checksum_is_accepted(self):
        """Quartett-Summe (Summe aller Halbbytes) als gültige Alternative."""
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
        """Hex-Text wie im Harness (Leerzeichen, Kommata, 0x-Präfixe)."""
        text = " ".join("0x%02X" % b for b in _by_name("elster")["_hex"])
        result = MBusinoLib().decode_telegram(text)
        self.assertEqual(len(result["records"]), 2)
        # gleiche Ergebnis wie mit bytes
        gleich = MBusinoLib().decode_telegram(_by_name("elster")["_hex"])
        self.assertEqual(result["records"], gleich["records"])

    def test_error_is_reset_between_calls(self):
        """decode_telegram setzt den internen Fehler zurück (s. Docstring)."""
        lib = MBusinoLib()
        # erst ein Telegramm mit Fehler
        kaputt = bytearray(_by_name("elster")["_hex"])
        kaputt[1] = kaputt[2] = 0x50
        lib.decode_telegram(bytes(kaputt))
        # dann ein sauberes
        result = lib.decode_telegram(_by_name("efe_heat_meter")["_hex"])
        self.assertEqual(result["error"], int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))


if __name__ == "__main__":
    unittest.main()
