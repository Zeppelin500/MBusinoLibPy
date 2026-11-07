# -*- coding: utf-8 -*-
"""Golden-Tests für die DATENSEATZ-DEKODIERUNG (ohne Telegrammrahmen).

Diese Fälle kommen aus zwei Quellen:

1. ``MBusinoLib/test/aunit/test.cpp`` - die Original-Decoder-Tests von AllWize,
   die Rohpuffer statt eines ganzen Telegramms übergeben.
2. Echte Datensatz-Ausschnitte aus den Golden-Telegrammen (z.B. das
   ASCII-Datensatz-Stück des Elster-Zählers) sowie zwei bewusst konstruierte
   Grenzfälle - alle mit Herkunft in der jeweiligen Golden-Datei.

Erzeugt mit dem C++-Harness ``test_decode_records`` (identische
MBusinoLib.cpp, eigener main()-Wrapper).
"""

import unittest

from MBusinoLibPy import MBUS_ERROR, MBusinoLib

from .helpers import compare_records, golden_records


class TestGoldenRecords(unittest.TestCase):
    """Rohdatensatz-Puffer gegen den C++-Referenz-Output."""

    def test_all_record_goldens_match(self):
        for case in golden_records():
            with self.subTest(case=case["_name"]):
                data = bytes(int(token, 16) for token in case["hex"].split())
                decoder = MBusinoLib()
                records = decoder.decode_records(data)
                error = decoder.get_error()
                self.assertEqual(error, case["error_code"],
                                 "Fehlercode weicht vom C++-Harness ab")
                problems = compare_records(records, case["records"], case["_name"])
                self.assertEqual(problems, [], "\n".join(problems))

    def test_aunit_cases_covered(self):
        """Die Decoder-Tests aus test.cpp sind vollständig übernommen."""
        names = {case["_name"] for case in golden_records()}
        for erwartet in ("aunit_number_1", "aunit_number_2", "aunit_number_3",
                         "aunit_number_4", "aunit_number_6", "aunit_multifield",
                         "aunit_decode_2bcd", "aunit_decode_8bcd"):
            self.assertIn(erwartet, names)

    def test_cpp_return_value_vs_json_array(self):
        """QUIRK: Bei einem Fehler liefert decodeRecords() im C++ den Wert 0,
        das JsonArray bleibt aber teilweise gefüllt.

        Python gibt den Inhalt des JsonArray zurück (das ist das, was der
        C++-Harness auch als JSON ausgibt) - der Fehler steht in get_error().
        """
        case = [c for c in golden_records() if c["_name"] == "konstrukt_var_bcd"][0]
        data = bytes(int(token, 16) for token in case["hex"].split())
        decoder = MBusinoLib()
        records = decoder.decode_records(data)
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        # C++-Rückgabewert (Fehlerfall) ...
        self.assertEqual(case["records_decoded"], 0)
        # ... aber das JsonArray enthält den bereits decodierten Datensatz,
        # und genau den liefert Python zurück:
        self.assertEqual(len(records), len(case["records"]))
        self.assertEqual(len(records), 1)

    def test_unsupported_vif_sets_error(self):
        """0x7E ist der vom Original benutzte "unbekannt"-Hinweis; ein VIF
        außerhalb aller Definitionen erzeugt UNSUPPORTED_VIF (C++ Zeile 281-285)."""
        # 0x6E = HCA - im Original in vif_defs auskommentiert (MBusinoLib.h
        # Zeile 222: `//{ MBUS_CODE::HCA , 0x6E , 1, 0},`), also kein Treffer
        decoder = MBusinoLib()
        records = decoder.decode_records(bytes([0x01, 0x6E, 0x2A]))
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.UNSUPPORTED_VIF))
        # Das Original läuft MIT Eintrag 0 weiter (def = 0), deshalb:
        # unknown_vif, code 0 UND (weil def == 0) kein Scaling - der Wert
        # bleibt der rohe 42 (C++ Zeile 586: `if(def != 0)` greift nicht)
        self.assertEqual(records[0]["name"], "unknown_vif")
        self.assertEqual(records[0]["code"], 0)
        self.assertEqual(records[0]["vif"], "0x6e")
        self.assertEqual(records[0]["value_scaled"], 42.0)
        self.assertNotIn("units", records[0])

    def test_buffer_overflow_is_reported(self):
        """Datensatz, der über das Ende hinausreicht -> BUFFER_OVERFLOW
        (C++ Zeile 380-384: `if (index + len > size)`)."""
        # DIF 0x07 = 64-Bit-Ganzzahl, aber nur 1 Byte Daten vorhanden
        decoder = MBusinoLib()
        records = decoder.decode_records(bytes([0x07, 0x00, 0x11]))
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(records, [])

    def test_buffer_overflow_keeps_already_decoded_records(self):
        """Zwei Datensätze, der zweite läuft über den Puffer hinaus."""
        # Datensatz 1 vollständig (DIF 01, VIF 00, 1 Byte), danach DIF 07 ohne Daten
        decoder = MBusinoLib()
        records = decoder.decode_records(bytes([0x01, 0x00, 0x2A, 0x07, 0x00]))
        self.assertEqual(decoder.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(len(records), 1)
        # DIF 01 + VIF 00 (ENERGY_WH, Skalar -3) + 0x2A = 42 -> 0.042 Wh
        self.assertEqual(records[0]["value_scaled"], 0.042)


if __name__ == "__main__":
    unittest.main()
