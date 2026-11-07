# -*- coding: utf-8 -*-
"""Stichproben für Enums, vif_defs-Tabelle und die vier Nachschlagetabellen.

Alle erwarteten Werte sind aus dem C++-Original abgeschrieben; hinter jedem
Block steht die Fundstelle in ``MBusinoLib`` (``src/MBusinoLib.h`` /
``src/MBusinoLib.cpp``). Damit prüfen die Tests die Übereinstimmung der
TABELLEN, während die Golden-Tests die Übereinstimmung der DEKODIERUNG prüfen.
"""

import unittest

from MBusinoLibPy import (
    CODE_NAME,
    CODE_UNITS,
    DEVICE_CLASS,
    MEDIUM_NAMES,
    STATE_CLASS,
    MBUS_CODE,
    MBUS_ERROR,
    MBUS_VIF_DEF_NUM,
    VIF_DEFS,
    MBusinoLib,
)


class TestEnums(unittest.TestCase):
    """Werte und Reihenfolge wie `enum MBUS_CODE` / `enum MBUS_ERROR` (MBusinoLib.h)."""

    def test_mbus_code_values(self):
        """C++-Enums ohne explizite Werte zählen 0,1,2,... in Deklarations-
        reihenfolge (MBusinoLib.h Zeile 37-165)."""
        erwartet = {
            "UNKNOWN_VIF": 0,            # erster Eintrag
            "ENERGY_WH": 1,              # MBusinoLib.h Zeile 41
            "VOLUME_M3": 3,              # Zeile 43
            "POWER_W": 13,               # Zeile 49
            "FLOW_TEMPERATURE_C": 19,    # Zeile 54
            "TIME_POINT_DATE": 24,       # Zeile 59
            "CREDIT": 36,                # Zeile 71 - Beginn "VIFE 0xFD"
            "MANUFACTURER": 39,          # Zeile 75
            "ERROR_FLAGS": 47,           # Zeile 87
            "CURRENT_SELECTED_APL": 62,  # Zeile 101 - Beginn "VIFE 0xFDFD"
            "REACTIVE_ENERGY": 103,      # Zeile 155 - Beginn "VIFE 0xFB"
            "FREQUENCY": 120,            # Zeile 172
            "CUSTOMIZED_VIF": 121,       # Zeile 176 - Beginn "VIFE 0xFC"
            "MANUFACTURER_SPECIFIC": 122 # Zeile 180 - letzter Eintrag
        }
        for name, wert in erwartet.items():
            with self.subTest(code=name):
                self.assertEqual(int(getattr(MBUS_CODE, name)), wert)

    def test_mbus_code_count(self):
        self.assertEqual(len(MBUS_CODE), 123)

    def test_mbus_error_values(self):
        """C++ (MBusinoLib.h Zeile 185-192): NO_ERROR=0 ... NEGATIVE_VALUE=5."""
        erwartet = {
            "NO_ERROR": 0,
            "BUFFER_OVERFLOW": 1,
            "UNSUPPORTED_CODING": 2,
            "UNSUPPORTED_RANGE": 3,
            "UNSUPPORTED_VIF": 4,
            "NEGATIVE_VALUE": 5,
        }
        for name, wert in erwartet.items():
            self.assertEqual(int(getattr(MBUS_ERROR, name)), wert, name)
        self.assertEqual(len(MBUS_ERROR), 6)

    def test_enums_behave_like_ints(self):
        """IntEnum: in JSON direkt serialisierbar, vergleichbar mit int."""
        self.assertEqual(MBUS_CODE.ENERGY_WH, 1)
        self.assertIsInstance(int(MBUS_CODE.ENERGY_WH), int)
        self.assertEqual(MBUS_ERROR.UNSUPPORTED_VIF, 4)


class TestVifDefs(unittest.TestCase):
    """Die vif_defs-Tabelle 1:1 aus MBusinoLib.h Zeile 179-345."""

    def test_entry_count(self):
        """#define MBUS_VIF_DEF_NUM 132 (MBusinoLib.h Zeile 177)"""
        self.assertEqual(MBUS_VIF_DEF_NUM, 132)
        self.assertEqual(len(VIF_DEFS), 132)

    def test_first_and_last_entry(self):
        self.assertEqual(tuple(VIF_DEFS[0]), (MBUS_CODE.UNKNOWN_VIF, 0x7E, 1, 0))
        self.assertEqual(tuple(VIF_DEFS[-1]), (MBUS_CODE.MANUFACTURER_SPECIFIC, 0xFF00, 254, 0))

    def test_known_entries(self):
        erwartet = [
            # (code, base, size, scalar)  -  MBusinoLib.h Zeile ...
            ((MBUS_CODE.ENERGY_WH, 0x00, 8, -3), 183),        # Energieskala -3
            ((MBUS_CODE.ENERGY_J, 0x08, 8, 0), 184),
            ((MBUS_CODE.VOLUME_M3, 0x10, 8, -6), 185),        # m3 mit -6
            ((MBUS_CODE.POWER_W, 0x28, 8, -3), 191),
            ((MBUS_CODE.FLOW_TEMPERATURE_C, 0x58, 4, -3), 197),
            ((MBUS_CODE.TIME_POINT_DATE, 0x6C, 1, 0), 201),
            ((MBUS_CODE.VOLUME_M3, 0x933A, 1, -3), 206),      # Erweiterungs-VIF
            ((MBUS_CODE.CREDIT, 0xFD00, 4, -3), 210),         # VIFE 0xFD
            ((MBUS_CODE.VOLTS, 0xFD40, 16, -9), 226),         # 16 Werte im Block
            ((MBUS_CODE.AMPERES, 0xFD50, 16, -12), 227),
            ((MBUS_CODE.ILLUMINANCE_LUX, 0xFDFD1F, 1, 0), 251),  # VIFE 0xFDFD
            ((MBUS_CODE.ENERGY_WH, 0xFB00, 2, 5), 283),       # VIFE 0xFB
            ((MBUS_CODE.RELATIVE_HUMIDITY, 0xFB1A, 2, -1), 289),
            ((MBUS_CODE.CUSTOMIZED_VIF, 0xFC00, 254, 0), 341),
        ]
        for erwarteter_eintrag, zeile in erwartet:
            with self.subTest(eintrag=erwarteter_eintrag):
                self.assertIn(tuple(erwarteter_eintrag), VIF_DEFS,
                              "nicht gefunden (C++ MBusinoLib.h Zeile %d)" % zeile)


class TestFindDefinition(unittest.TestCase):
    """_findDefinition() - MBusinoLib.cpp Zeile 1528-1539."""

    def test_known_lookups(self):
        self.assertEqual(MBusinoLib._find_definition(0x7E), 0)   # UNKNOWN_VIF-Eintrag
        self.assertEqual(MBusinoLib._find_definition(0x03), 1)   # ENERGY_WH
        self.assertEqual(MBusinoLib._find_definition(0xFD0A), 41)  # MANUFACTURER
        self.assertEqual(MBusinoLib._find_definition(0xFDFD00), 64)
        self.assertEqual(MBusinoLib._find_definition(0xFF00), 131)

    def test_first_match_wins(self):
        """Der C++-Loop bricht beim ERSTEN Treffer ab - 0x00 liegt in der
        ENERGY_WH-Definition (Index 1), auch spätere Tabellen hätten 0x00
        theoretisch zuordnen können."""
        self.assertEqual(MBusinoLib._find_definition(0x00), 1)

    def test_gap_returns_minus_one(self):
        """0x6E (HCA) ist in vif_defs auskommentiert -> -1 wie im C++."""
        self.assertEqual(MBusinoLib._find_definition(0x6E), -1)

    def test_aunit_expectation_documented(self):
        """AUnit-Test `Find_Definition` (test.cpp Zeile 244) erwartet Index 0 für
        0x03. Das trifft nur zu, solange UNKNOWN_VIF NICHT an erster Stelle der
        Tabelle steht - heute steht er dort (C++ UND Python), also ist 1 die
        richtige Antwort. Die AUnit-Datei ist gegen die aktuelle Bibliothek
        veraltet (sie ruft zudem Encoder-Methoden auf, die es nicht mehr gibt).
        """
        self.assertEqual(MBusinoLib._find_definition(0x03), 1)


class TestGetVif(unittest.TestCase):
    """_getVif() - MBusinoLib.cpp Zeile 1541-1555; Werte 1:1 aus den
    AUnit-Erwartungen `Get_VIF` (test.cpp Zeile 247-254)."""

    def test_aunit_values(self):
        erwartet = [
            (-4, 0xFF),   # außerhalb der ENERGY_WH-Definition -> "not a valid VIF"
            (-3, 0x00),
            (0, 0x03),
            (3, 0x06),
            (4, 0x07),
            (5, 0xFB00),  # Wechsel in die VIFE-0xFB-Tabelle
            (6, 0xFB01),
            (7, 0xFF),    # wieder außerhalb
        ]
        for scalar, wert in erwartet:
            with self.subTest(scalar=scalar):
                self.assertEqual(MBusinoLib._get_vif(MBUS_CODE.ENERGY_WH, scalar), wert)


class TestLookupTables(unittest.TestCase):
    """getCodeName/getCodeUnits/getDeviceClass/getStateClass - Stichproben
    gegen die C++-switch-Anweisungen."""

    def setUp(self):
        self.lib = MBusinoLib()

    # ---- getCodeUnits (MBusinoLib.cpp Zeile 660) -------------------------
    def test_code_units(self):
        erwartet = [
            (MBUS_CODE.ENERGY_WH, "Wh"),            # Zeile 663
            (MBUS_CODE.VOLUME_M3, "m³"),            # Zeile 669
            (MBUS_CODE.ON_TIME_S, "s"),             # Zeile 672 (4 Codes teilen "s")
            (MBUS_CODE.AVG_DURATION_S, "s"),        # Zeile 673
            (MBUS_CODE.POWER_W, "W"),               # Zeile 687
            (MBUS_CODE.VOLUME_FLOW_M3_H, "m³/h"),   # Zeile 693
            (MBUS_CODE.FLOW_TEMPERATURE_C, "°C"),   # Zeile 701
            (MBUS_CODE.TEMPERATURE_DIFF_K, "K"),    # Zeile 706
            (MBUS_CODE.PRESSURE_BAR, "bar"),        # Zeile 709
            (MBUS_CODE.TIME_POINT_DATE, "YYYYMMDD"),# Zeile 712
            (MBUS_CODE.VOLTS, "V"),                 # Zeile 721
            (MBUS_CODE.FREQUENCY, "Hz"),            # Zeile 754
            (MBUS_CODE.PARTICLES_PM10_UG_M3, "µg/m³"),  # Zeile 771
            (MBUS_CODE.DISTANCE_MM, "mm"),          # Zeile 786
        ]
        for code, einheit in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_code_units(code), einheit)

    def test_code_units_null_for_codes_without_unit(self):
        """C++: `return 0;` -> NULL -> Python None (kein Eintrag in der Tabelle)."""
        for code in (MBUS_CODE.UNKNOWN_VIF, MBUS_CODE.MANUFACTURER,
                     MBUS_CODE.ACCESS_NUMBER, MBUS_CODE.CUSTOMIZED_VIF):
            self.assertIsNone(self.lib.get_code_units(code), code)
        # Unbekannter Code (außerhalb des Enums) ebenfalls None
        self.assertIsNone(self.lib.get_code_units(999))

    # ---- getCodeName (MBusinoLib.cpp Zeile 847) --------------------------
    def test_code_name(self):
        erwartet = [
            (MBUS_CODE.UNKNOWN_VIF, "unknown_vif"),        # Zeile 850
            (MBUS_CODE.ENERGY_WH, "energy"),               # Zeile 853
            (MBUS_CODE.ENERGY_J, "energy"),                # gleiche Fallgruppe
            (MBUS_CODE.VOLUME_M3, "volume"),               # Zeile 857
            (MBUS_CODE.ON_TIME_H, "on_time"),              # Zeile 866
            (MBUS_CODE.POWER_W, "power"),                  # Zeile 880
            (MBUS_CODE.VOLUME_FLOW_GAL_H, "volume_flow"),  # Zeile 887
            (MBUS_CODE.FLOW_TEMPERATURE_F, "flow_temperature"),  # Zeile 893
            (MBUS_CODE.TIME_POINT_DATETIME, "time_point"),  # Zeile 908
            (MBUS_CODE.MANUFACTURER, "manufacturer"),       # Zeile 925
            (MBUS_CODE.CUSTOMIZED_VIF, "customized_vif"),   # Zeile 1012
            (MBUS_CODE.MANUFACTURER_SPECIFIC, "manufactur_specific"),  # Zeile 1015
            (MBUS_CODE.CARBON_DIOXIDE_PPM, "CO²"),          # Zeile 1033 (Unicode!)
            (MBUS_CODE.PARTICLES_PM2_5_UG_M3, "particles_PM2,5"),  # Zeile 1057
            (MBUS_CODE.POTENTIAL_HYDROGEN_PH, "PH"),        # Zeile 1069
        ]
        for code, name in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_code_name(code), name)

    def test_code_name_default_is_empty_string(self):
        """C++: `return "";` im default-Zweig."""
        self.assertEqual(self.lib.get_code_name(9999), "")

    # ---- getDeviceClass (MBusinoLib.cpp Zeile 1182) ----------------------
    def test_device_class(self):
        erwartet = [
            (MBUS_CODE.ENERGY_WH, "energy"),           # Zeile 1185
            (MBUS_CODE.MASS_KG, "weight"),             # Zeile 1191
            (MBUS_CODE.OPERATING_TIME_DAYS, "duration"),  # Zeile 1210
            (MBUS_CODE.POWER_W, "power"),              # Zeile 1212
            (MBUS_CODE.FLOW_TEMPERATURE_C, "temperature"),  # Zeile 1221
            (MBUS_CODE.TEMPERATURE_DIFF_K, "temperature_delta"),  # Zeile 1229
            (MBUS_CODE.PRESSURE_BAR, "pressure"),      # Zeile 1232
            (MBUS_CODE.BAUDRATE_BPS, "data_rate"),     # Zeile 1235
            (MBUS_CODE.RELATIVE_HUMIDITY, "humidity"), # Zeile 1243
            (MBUS_CODE.FREQUENCY, "frequency"),        # Zeile 1246
            (MBUS_CODE.CARBON_DIOXIDE_PPM, "carbon_dioxide"),  # Zeile 1271
            (MBUS_CODE.PARTICLES_PM10_UG_M3, "pm10"),  # Zeile 1279
            (MBUS_CODE.RAINFALL_L_MM, "precipitation"),  # Zeile 1281
        ]
        for code, klasse in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_device_class(code), klasse)

    def test_device_class_volume_depends_on_medium(self):
        """C++ Zeile 1202-1206: VOLUMEN-Codes gehen über _volumeClassFromMedium
        (MBusinoLib.cpp Zeile 1167-1180)."""
        for code in (MBUS_CODE.VOLUME_M3, MBUS_CODE.VOLUME_FT3, MBUS_CODE.VOLUME_GAL):
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_device_class(code, 0x03), "gas")   # Gas
                self.assertEqual(self.lib.get_device_class(code, 0x07), "water")  # Water
                self.assertEqual(self.lib.get_device_class(code, 0x06), "water")  # Warm Water
                self.assertEqual(self.lib.get_device_class(code, 0x15), "water")  # Hot water
                self.assertEqual(self.lib.get_device_class(code, 0x16), "water")  # Cold water
                self.assertEqual(self.lib.get_device_class(code, 0x17), "water")  # Dual water
                self.assertEqual(self.lib.get_device_class(code, 0x01), "volume") # Öl -> generisch
                # Standardparameter 0xFF (unbekannt) -> generisch "volume"
                self.assertEqual(self.lib.get_device_class(code), "volume")
                self.assertEqual(self.lib.get_device_class(code, 0xFF), "volume")

    def test_device_class_empty_without_ha_class(self):
        """Grosser default-Zweig (C++ Zeile 1284-1377) liefert ""."""
        for code in (MBUS_CODE.UNKNOWN_VIF, MBUS_CODE.TIME_POINT_DATE,
                     MBUS_CODE.MANUFACTURER, MBUS_CODE.CUSTOMIZED_VIF,
                     MBUS_CODE.SPECIAL_SUPPLIER_INFO, MBUS_CODE.MASS_FLOW_KG_H):
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_device_class(code), "")

    # ---- getStateClass (MBusinoLib.cpp Zeile 1382) -----------------------
    def test_state_class(self):
        erwartet = [
            (MBUS_CODE.ENERGY_WH, "total_increasing"),    # Zeile 1389
            (MBUS_CODE.VOLUME_M3, "total_increasing"),    # Zeile 1391
            (MBUS_CODE.RAINFALL_L_MM, "total_increasing"),  # Zeile 1397
            (MBUS_CODE.ON_TIME_DAYS, "total_increasing"), # Zeile 1411
            (MBUS_CODE.AMPERES, "measurement"),           # Zeile 1416
            (MBUS_CODE.POWER_W, "measurement"),           # Zeile 1418
            (MBUS_CODE.RELATIVE_HUMIDITY, "measurement"), # Zeile 1441
            (MBUS_CODE.BATTERY_PERCENTAGE, "measurement"),  # Zeile 1452
            (MBUS_CODE.PARTICLES_PM10_UG_M3, "measurement"),  # Zeile 1467
            (MBUS_CODE.UNKNOWN_VIF, ""),                  # Zeile 1474
            (MBUS_CODE.TIME_POINT_DATE, ""),              # Zeile 1479
            (MBUS_CODE.MANUFACTURER, ""),                 # Zeile 1483
            (MBUS_CODE.SPECIAL_SUPPLIER_INFO, ""),        # kein case -> default
        ]
        for code, klasse in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_state_class(code), klasse)

    def test_state_class_default(self):
        self.assertEqual(self.lib.get_state_class(4242), "")


def self_device_class_via_helper(code) -> bool:
    """Prüft den Medium-Sonderfall der drei Volumen-Codes."""
    lib = MBusinoLib()
    return (lib.get_device_class(code, 0x07) == "water"
            and lib.get_device_class(code, 0x03) == "gas"
            and lib.get_device_class(code) == "volume")


class TestTableIntegrity(unittest.TestCase):
    """Struktur-Prüfungen über die vier Tabellen hinweg."""

    def test_every_enum_code_has_name_and_device_class(self):
        """getCodeName kennt ALLE 123 Enum-Werte (der C++-switch hat für jeden
        Code einen case); getDeviceClass alle außer den drei Volumen-Codes,
        die über die Medium-Hilfsfunktion laufen."""
        volumen = {MBUS_CODE.VOLUME_M3, MBUS_CODE.VOLUME_FT3, MBUS_CODE.VOLUME_GAL}
        for code in MBUS_CODE:
            with self.subTest(code=code.name):
                self.assertIn(code, CODE_NAME)
                if code not in volumen:
                    self.assertIn(code, DEVICE_CLASS)
                else:
                    # Sonderfall über _volumeClassFromMedium (C++ Zeile 1202)
                    self.assertTrue(self_device_class_via_helper(code))

    def test_state_class_covers_all_but_one(self):
        """getStateClass hat keinen case für SPECIAL_SUPPLIER_INFO (C++-default)."""
        fehlend = [code.name for code in MBUS_CODE if code not in STATE_CLASS]
        self.assertEqual(fehlend, ["SPECIAL_SUPPLIER_INFO"])

    def test_table_structure(self):
        """Alle Tabellen: numerische Schlüssel, String-Werte, keine Duplikate.
        (Dicts erlauben doppelte Schlüssel per Konstrukt nicht - ein stummer
        Eintrag wäre der einzige Hinweis darauf, dass beim Port etwas
        zusammengefallen ist, deshalb gegen die C++-Fallanzahl geprüft.)"""
        erwartete_fallanzahl = [(CODE_NAME, 123, "getCodeName"),
                                (CODE_UNITS, 79, "getCodeUnits"),
                                (DEVICE_CLASS, 120, "getDeviceClass"),
                                (STATE_CLASS, 122, "getStateClass"),
                                (MEDIUM_NAMES, 20, "decodeHeader/Medium")]
        for tabelle, anzahl, quelle in erwartete_fallanzahl:
            with self.subTest(tabelle=quelle):
                self.assertEqual(len(tabelle), anzahl)
                for key, wert in tabelle.items():
                    self.assertIsInstance(key, int if tabelle is MEDIUM_NAMES else MBUS_CODE)
                    self.assertIsInstance(wert, str)
        # Leere Werte sind nur dort erlaubt, wo auch das C++ "" liefert
        for tabelle in (CODE_NAME, CODE_UNITS, MEDIUM_NAMES):
            for key, wert in tabelle.items():
                self.assertNotEqual(wert, "", "C++ liefert hier keinen leeren String: %r" % key)

    def test_device_class_empty_values_exist(self):
        """getDeviceClass/getStateClass liefern bewusst "" (keine HA-Klasse)."""
        self.assertEqual(DEVICE_CLASS[MBUS_CODE.UNKNOWN_VIF], "")
        self.assertEqual(STATE_CLASS[MBUS_CODE.UNKNOWN_VIF], "")

    def test_medium_names_match_cpp_switch(self):
        """decodeHeader-Switch, MBusinoLib.cpp Zeile 1610-1636."""
        erwartet = {
            0x01: "Oil", 0x02: "Electricity", 0x03: "Gas", 0x04: "Heat",
            0x05: "Steam", 0x06: "Warm Water", 0x07: "Water",
            0x08: "Heat Cost Allocator", 0x09: "Compressed Air",
            0x0A: "Cooling load meter (Volume)", 0x0B: "Cooling load meter (Mass)",
            0x0C: "Heat (Volume)", 0x0D: "Heat (Mass)",
            0x0E: "Combined Heat/Cooling", 0x0F: "Bus/System component",
            0x14: "Calorific value", 0x15: "Hot water", 0x16: "Cold water",
            0x17: "Dual water", 0x37: "Radio converter",
        }
        self.assertEqual(MEDIUM_NAMES, erwartet)


if __name__ == "__main__":
    unittest.main()
