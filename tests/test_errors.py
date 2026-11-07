# -*- coding: utf-8 -*-
"""Tests für Fehlerbehandlung: ``get_error()`` und ``get_error_message()``.

``get_error()`` verhält sich exakt wie MBusinoLib::getError()
(MBusinoLib.cpp Zeile 54-58): Rückgabe UND Zurücksetzen auf NO_ERROR.
"""

import unittest

from MBusinoLibPy import MBUS_CODE, MBUS_ERROR, MBusinoLib


class TestGetError(unittest.TestCase):
    """C++: `uint8_t getError() { uint8_t error = _error; _error = NO_ERROR; return error; }`"""

    def test_initial_state_is_no_error(self):
        lib = MBusinoLib()
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(lib.get_error_message(), "Kein Fehler.")

    def test_get_error_clears_the_error(self):
        """Rückgabe, danach ist der Fehler weg - Aufruf zweimal = 4, dann 0."""
        lib = MBusinoLib()
        lib.decode_records(bytes([0x07, 0x00, 0x11]))     # BUFFER_OVERFLOW
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))

    def test_error_does_not_clear_itself_by_decoding(self):
        """decodeRecords() löscht den Fehler NICHT (nur getError() tut das)."""
        lib = MBusinoLib()
        lib.decode_records(bytes([0x07, 0x00, 0x11]))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))

    def test_error_message_does_not_clear(self):
        """get_error_message() ist rein lesend - deshalb kann man sie VOR
        get_error() aufrufen und beide Informationen behalten."""
        lib = MBusinoLib()
        lib.decode_records(bytes([0x01, 0x6E, 0x2A]))     # UNSUPPORTED_VIF
        nachricht = lib.get_error_message()
        self.assertIn("VIF", nachricht)
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.UNSUPPORTED_VIF))
        self.assertIn("VIF", nachricht)   # war nicht gelöscht

    def test_explicit_code_argument(self):
        """Für JEDEN Enum-Wert existiert eine lesbare deutsche Meldung."""
        lib = MBusinoLib()
        for code in MBUS_ERROR:
            with self.subTest(code=code.name):
                meldung = lib.get_error_message(code)
                self.assertTrue(meldung.strip())
                self.assertTrue(meldung.endswith("."), "Meldung endet ohne Punkt")
        # Kerninhalte prüfen, ohne den Wortlaut zu festschreiben
        self.assertIn("Kein Fehler", lib.get_error_message(MBUS_ERROR.NO_ERROR))
        self.assertIn("VIF", lib.get_error_message(MBUS_ERROR.UNSUPPORTED_VIF))
        self.assertIn("Puffer", lib.get_error_message(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertIn("DIF", lib.get_error_message(MBUS_ERROR.UNSUPPORTED_CODING))
        self.assertIn("Skalierung", lib.get_error_message(MBUS_ERROR.UNSUPPORTED_RANGE))
        self.assertIn("Negativ", lib.get_error_message(MBUS_ERROR.NEGATIVE_VALUE))

    def test_return_type_is_plain_int(self):
        lib = MBusinoLib()
        wert = lib.get_error()
        self.assertIsInstance(wert, int)
        # Vergleiche mit dem Enum funktionieren trotzdem (IntEnum)
        self.assertEqual(wert, MBUS_ERROR.NO_ERROR)


class TestErrorPathsDuringDecode(unittest.TestCase):
    """Welche Fehler kann das Dekodieren überhaupt setzen?"""

    def test_supported_vif_never_raises_error(self):
        lib = MBusinoLib()
        # DIF 01 + VIF 00 (ENERGY_WH) + 1 Byte
        lib.decode_records(bytes([0x01, 0x00, 0x42]))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))

    def test_unsupported_vif(self):
        lib = MBusinoLib()
        lib.decode_records(bytes([0x01, 0x6E, 0x2A]))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.UNSUPPORTED_VIF))

    def test_buffer_overflow_on_truncated_record(self):
        lib = MBusinoLib()
        lib.decode_records(bytes([0x04, 0x00, 0x01, 0x02]))  # 4 Byte erwartet, 2 vorhanden
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))

    def test_buffer_overflow_when_vif_chain_never_ends(self):
        """Endlose VIFE-Kette (alle Bytes mit Bit 7) -> wie im Original BUFFER_OVERFLOW
        (C++ Zeile 225-228, dort: `if (index == size)`)."""
        lib = MBusinoLib()
        records = lib.decode_records(bytes([0x01, 0x81, 0x81, 0x81]))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(records, [])

    def test_encoder_only_codes_are_never_set_while_decoding(self):
        """UNSUPPORTED_CODING / UNSUPPORTED_RANGE / NEGATIVE_VALUE stammen aus
        dem alten AllWize-Encoder und werden beim Dekodieren nicht gesetzt
        (Beleg: einzige Fehlerzuweisungen in MBusinoLib.cpp sind die Zeilen
        226, 283 und 382)."""
        lib = MBusinoLib()
        # vollständige Datensätze mit ungewöhnlichen Kodierungen ...
        lib.decode_records(bytes([0x05, 0x6D, 0x00, 0x00, 0x00, 0x00]))  # real + Datum Typ F
        lib.decode_records(bytes([0x0D, 0x00, 0x02, 0x41, 0x42]))        # variable Länge, ASCII (2 Zeichen)
        # ... duerfen keine der drei nur-im-Encoder-definierten Codes erzeugen
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))

    def test_get_error_message_for_unknown_code(self):
        lib = MBusinoLib()
        self.assertIn("Unbekannter Fehlercode", lib.get_error_message(999))


class TestEnumMirroring(unittest.TestCase):
    """MBUS_ERROR muss identisch zu C++ sein, damit Codes austauschbar sind."""

    def test_error_codes_as_int(self):
        self.assertEqual([int(c) for c in MBUS_ERROR], [0, 1, 2, 3, 4, 5])
        self.assertEqual([c.name for c in MBUS_ERROR], [
            "NO_ERROR", "BUFFER_OVERFLOW", "UNSUPPORTED_CODING",
            "UNSUPPORTED_RANGE", "UNSUPPORTED_VIF", "NEGATIVE_VALUE",
        ])

    def test_code_names_for_home_assistant_mapping(self):
        """Die Codes sind die Brücke zu den Home-Assistant-Tabellen."""
        self.assertEqual(MBUS_CODE.ENERGY_WH, 1)
        self.assertEqual(int(MBUS_CODE.VOLUME_M3), 3)


if __name__ == "__main__":
    unittest.main()
