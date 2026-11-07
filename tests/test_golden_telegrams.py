# -*- coding: utf-8 -*-
"""Golden-Tests für die TELEGRAMM-DEKODIERUNG.

Fünf echte, in den MBusino-/MBusinoLib-Quellen gefundene Telegramme wurden
durch den C++-Harness ``test_decode`` geschickt; dessen Ausgabe liegt als
``tests/golden/<name>.expected.json``. Der Python-Port muss exakt dieselben
Datensätze liefern.

Herkunft und Umstände jeder Datei stehen in ``tests/golden/<name>.source.json``
und in ``tests/golden/README.md``.
"""

import unittest

from MBusinoLibPy import MBUS_ERROR, MBusinoLib

from .helpers import compare_records, golden_telegrams, records_like_test_decode


class TestGoldenTelegrams(unittest.TestCase):
    """Der komplette Ablauf aus test_decode.cpp gegen die C++-Referenz."""

    def test_at_least_five_golden_telegrams(self):
        """Vorgabe: mindestens 3-5 echte Telegramme als Golden-Referenz."""
        telegrams = golden_telegrams()
        self.assertGreaterEqual(
            len(telegrams), 5,
            "weniger als 5 Golden-Telegramme gefunden - Herkunft prüfen",
        )

    def test_every_golden_has_documented_source(self):
        """Jedes Golden-Telegramm braucht eine nachvollziehbare Quelle."""
        for telegram in golden_telegrams():
            with self.subTest(telegram=telegram["_name"]):
                source = telegram["_source"]
                self.assertTrue(source.get("src", "").strip(),
                                "Quelle fehlt für %s" % telegram["_name"])
                self.assertTrue(source.get("note", "").strip(),
                                "Hinweis zur Herkunft fehlt für %s" % telegram["_name"])

    def test_records_match_cpp_reference(self):
        """Datensätze, Anzahl und Fehlercode wie im C++-Harness."""
        for telegram in golden_telegrams():
            with self.subTest(telegram=telegram["_name"]):
                _data, _size, records, error = records_like_test_decode(
                    " ".join("%02X" % b for b in telegram["_hex"])
                )
                self.assertEqual(
                    error, telegram["error_code"],
                    "Fehlercode weicht vom C++-Harness ab",
                )
                self.assertEqual(
                    len(records), telegram["records_decoded"],
                    "Anzahl dekodierter Datensätze weicht vom C++-Harness ab",
                )
                problems = compare_records(records, telegram["records"], telegram["_name"])
                self.assertEqual(problems, [], "\n".join(problems))

    def test_record_keys_match_arduinojson_output(self):
        """Die Keys sind identisch mit dem ArduinoJson-Output des Originals."""
        erlaubt = {"vif", "code", "value_scaled", "value_string", "units",
                   "name", "subUnit", "storage", "tariff", "telegramFollow"}
        gefunden = set()
        for telegram in golden_telegrams():
            for record in telegram["records"]:
                self.assertTrue(set(record) <= erlaubt,
                                "unerwartete Keys: %s" % (set(record) - erlaubt))
                gefunden |= set(record)
        # Sicherstellen, dass die Golden-Daten auch wirklich alle Pfade abdecken
        for erwartet in ("vif", "code", "value_scaled", "name", "units",
                         "value_string", "subUnit", "storage"):
            self.assertIn(erwartet, gefunden,
                          "Key %s kommt in keinem Golden-Telegramm vor" % erwartet)

    def test_known_values_from_reference_telegram(self):
        """Ein paar feste Marken aus dem EFE-WärmeZähler (Hersteller/ID/Medium)."""
        efe = [t for t in golden_telegrams() if t["_name"] == "efe_heat_meter"][0]
        _data, _size, records, _error = records_like_test_decode(
            " ".join("%02X" % b for b in efe["_hex"])
        )
        # Erster Datensatz im Harness: fab_number = 73753409 (Firmwarestand)
        self.assertEqual(records[0]["name"], "fab_number")
        self.assertEqual(records[0]["vif"], "0x78")
        self.assertAlmostEqual(records[0]["value_scaled"], 73753409.0, places=3)
        # 0x03 (innerhalb der ENERGY_WH-Definition) -> Tabellenindex 1,
        # weil UNKNOWN_VIF an Position 0 steht (C++ UND Python). Die
        # AUnit-Erwartung "0" in test.cpp Zeile 244 stammt aus davor.
        self.assertEqual(MBusinoLib._find_definition(0x03), 1)


class TestGoldenErrorCodes(unittest.TestCase):
    """Alle Telegramme müssen fehlerfrei dekodierbar sein (Referenz-C++ auch)."""

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
