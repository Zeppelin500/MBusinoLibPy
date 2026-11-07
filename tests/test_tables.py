# -*- coding: utf-8 -*-
"""Spot checks for the enums, the vif_defs table and the four lookup tables.

All expected values were copied from the C++ original; every block
states the location in ``MBusinoLib`` (``src/MBusinoLib.h`` /
``src/MBusinoLib.cpp``). That way the tests check the match of the
TABLES, while the golden tests check the match of the DECODING.
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
    """Values and order like `enum MBUS_CODE` / `enum MBUS_ERROR` (MBusinoLib.h)."""

    def test_mbus_code_values(self):
        """C++ enums without explicit values count 0,1,2,... in declaration
        order (MBusinoLib.h line 37-165)."""
        erwartet = {
            "UNKNOWN_VIF": 0,            # erster Eintrag
            "ENERGY_WH": 1,              # MBusinoLib.h line 41
            "VOLUME_M3": 3,              # line 43
            "POWER_W": 13,               # line 49
            "FLOW_TEMPERATURE_C": 19,    # line 54
            "TIME_POINT_DATE": 24,       # line 59
            "CREDIT": 36,                # line 71 - Beginn "VIFE 0xFD"
            "MANUFACTURER": 39,          # line 75
            "ERROR_FLAGS": 47,           # line 87
            "CURRENT_SELECTED_APL": 62,  # line 101 - Beginn "VIFE 0xFDFD"
            "REACTIVE_ENERGY": 103,      # line 155 - Beginn "VIFE 0xFB"
            "FREQUENCY": 120,            # line 172
            "CUSTOMIZED_VIF": 121,       # line 176 - Beginn "VIFE 0xFC"
            "MANUFACTURER_SPECIFIC": 122 # line 180 - letzter Eintrag
        }
        for name, wert in erwartet.items():
            with self.subTest(code=name):
                self.assertEqual(int(getattr(MBUS_CODE, name)), wert)

    def test_mbus_code_count(self):
        self.assertEqual(len(MBUS_CODE), 123)

    def test_mbus_error_values(self):
        """C++ (MBusinoLib.h line 185-192): NO_ERROR=0 ... NEGATIVE_VALUE=5."""
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
        """IntEnum: directly serialisable in JSON, comparable with int."""
        self.assertEqual(MBUS_CODE.ENERGY_WH, 1)
        self.assertIsInstance(int(MBUS_CODE.ENERGY_WH), int)
        self.assertEqual(MBUS_ERROR.UNSUPPORTED_VIF, 4)


class TestVifDefs(unittest.TestCase):
    """The vif_defs table 1:1 from MBusinoLib.h line 179-345."""

    def test_entry_count(self):
        """#define MBUS_VIF_DEF_NUM 132 (MBusinoLib.h line 177)"""
        self.assertEqual(MBUS_VIF_DEF_NUM, 132)
        self.assertEqual(len(VIF_DEFS), 132)

    def test_first_and_last_entry(self):
        self.assertEqual(tuple(VIF_DEFS[0]), (MBUS_CODE.UNKNOWN_VIF, 0x7E, 1, 0))
        self.assertEqual(tuple(VIF_DEFS[-1]), (MBUS_CODE.MANUFACTURER_SPECIFIC, 0xFF00, 254, 0))

    def test_known_entries(self):
        erwartet = [
            # (code, base, size, scalar)  -  MBusinoLib.h line ...
            ((MBUS_CODE.ENERGY_WH, 0x00, 8, -3), 183),        # Energieskala -3
            ((MBUS_CODE.ENERGY_J, 0x08, 8, 0), 184),
            ((MBUS_CODE.VOLUME_M3, 0x10, 8, -6), 185),        # m3 with -6
            ((MBUS_CODE.POWER_W, 0x28, 8, -3), 191),
            ((MBUS_CODE.FLOW_TEMPERATURE_C, 0x58, 4, -3), 197),
            ((MBUS_CODE.TIME_POINT_DATE, 0x6C, 1, 0), 201),
            ((MBUS_CODE.VOLUME_M3, 0x933A, 1, -3), 206),      # Erweiterungs-VIF
            ((MBUS_CODE.CREDIT, 0xFD00, 4, -3), 210),         # VIFE 0xFD
            ((MBUS_CODE.VOLTS, 0xFD40, 16, -9), 226),         # 16 values in the block
            ((MBUS_CODE.AMPERES, 0xFD50, 16, -12), 227),
            ((MBUS_CODE.ILLUMINANCE_LUX, 0xFDFD1F, 1, 0), 251),  # VIFE 0xFDFD
            ((MBUS_CODE.ENERGY_WH, 0xFB00, 2, 5), 283),       # VIFE 0xFB
            ((MBUS_CODE.RELATIVE_HUMIDITY, 0xFB1A, 2, -1), 289),
            ((MBUS_CODE.CUSTOMIZED_VIF, 0xFC00, 254, 0), 341),
        ]
        for erwarteter_eintrag, zeile in erwartet:
            with self.subTest(eintrag=erwarteter_eintrag):
                self.assertIn(tuple(erwarteter_eintrag), VIF_DEFS,
                              "not found (C++ MBusinoLib.h line %d)" % zeile)


class TestFindDefinition(unittest.TestCase):
    """_findDefinition() - MBusinoLib.cpp line 1528-1539."""

    def test_known_lookups(self):
        self.assertEqual(MBusinoLib._find_definition(0x7E), 0)   # UNKNOWN_VIF-Eintrag
        self.assertEqual(MBusinoLib._find_definition(0x03), 1)   # ENERGY_WH
        self.assertEqual(MBusinoLib._find_definition(0xFD0A), 41)  # MANUFACTURER
        self.assertEqual(MBusinoLib._find_definition(0xFDFD00), 64)
        self.assertEqual(MBusinoLib._find_definition(0xFF00), 131)

    def test_first_match_wins(self):
        """The C++ loop stops at the FIRST match - 0x00 lies in the
        ENERGY_WH definition (index 1), later table entries could have
        claimed 0x00 in theory."""
        self.assertEqual(MBusinoLib._find_definition(0x00), 1)

    def test_gap_returns_minus_one(self):
        """0x6E (HCA) is commented out in vif_defs -> -1 like in C++."""
        self.assertEqual(MBusinoLib._find_definition(0x6E), -1)

    def test_aunit_expectation_documented(self):
        """AUnit test `Find_Definition` (test.cpp line 244) expects index 0 for
        0x03. That only holds as long as UNKNOWN_VIF is NOT at the front of
        the table - today it is (C++ AND Python), so 1 is the right answer.
        The AUnit file is outdated for the current library (it also calls
        encoder methods that no longer exist).
        """
        self.assertEqual(MBusinoLib._find_definition(0x03), 1)


class TestGetVif(unittest.TestCase):
    """_getVif() - MBusinoLib.cpp line 1541-1555; values 1:1 from the
    AUnit expectations `Get_VIF` (test.cpp line 247-254)."""

    def test_aunit_values(self):
        erwartet = [
            (-4, 0xFF),   # outside the ENERGY_WH definition -> "not a valid VIF"
            (-3, 0x00),
            (0, 0x03),
            (3, 0x06),
            (4, 0x07),
            (5, 0xFB00),  # switch into the VIFE 0xFB table
            (6, 0xFB01),
            (7, 0xFF),    # outside again
        ]
        for scalar, wert in erwartet:
            with self.subTest(scalar=scalar):
                self.assertEqual(MBusinoLib._get_vif(MBUS_CODE.ENERGY_WH, scalar), wert)


class TestLookupTables(unittest.TestCase):
    """getCodeName/getCodeUnits/getDeviceClass/getStateClass - Stichproben
    against the C++ switch statements."""

    def setUp(self):
        self.lib = MBusinoLib()

    # ---- getCodeUnits (MBusinoLib.cpp line 660) -------------------------
    def test_code_units(self):
        erwartet = [
            (MBUS_CODE.ENERGY_WH, "Wh"),            # line 663
            (MBUS_CODE.VOLUME_M3, "m³"),            # line 669
            (MBUS_CODE.ON_TIME_S, "s"),             # line 672 (4 codes share "s")
            (MBUS_CODE.AVG_DURATION_S, "s"),        # line 673
            (MBUS_CODE.POWER_W, "W"),               # line 687
            (MBUS_CODE.VOLUME_FLOW_M3_H, "m³/h"),   # line 693
            (MBUS_CODE.FLOW_TEMPERATURE_C, "°C"),   # line 701
            (MBUS_CODE.TEMPERATURE_DIFF_K, "K"),    # line 706
            (MBUS_CODE.PRESSURE_BAR, "bar"),        # line 709
            (MBUS_CODE.TIME_POINT_DATE, "YYYYMMDD"),# line 712
            (MBUS_CODE.VOLTS, "V"),                 # line 721
            (MBUS_CODE.FREQUENCY, "Hz"),            # line 754
            (MBUS_CODE.PARTICLES_PM10_UG_M3, "µg/m³"),  # line 771
            (MBUS_CODE.DISTANCE_MM, "mm"),          # line 786
        ]
        for code, einheit in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_code_units(code), einheit)

    def test_code_units_null_for_codes_without_unit(self):
        """C++: `return 0;` -> NULL -> Python None (no entry in the table)."""
        for code in (MBUS_CODE.UNKNOWN_VIF, MBUS_CODE.MANUFACTURER,
                     MBUS_CODE.ACCESS_NUMBER, MBUS_CODE.CUSTOMIZED_VIF):
            self.assertIsNone(self.lib.get_code_units(code), code)
        # unknown code (outside the enum) is None as well
        self.assertIsNone(self.lib.get_code_units(999))

    # ---- getCodeName (MBusinoLib.cpp line 847) --------------------------
    def test_code_name(self):
        erwartet = [
            (MBUS_CODE.UNKNOWN_VIF, "unknown_vif"),        # line 850
            (MBUS_CODE.ENERGY_WH, "energy"),               # line 853
            (MBUS_CODE.ENERGY_J, "energy"),                # gleiche Fallgruppe
            (MBUS_CODE.VOLUME_M3, "volume"),               # line 857
            (MBUS_CODE.ON_TIME_H, "on_time"),              # line 866
            (MBUS_CODE.POWER_W, "power"),                  # line 880
            (MBUS_CODE.VOLUME_FLOW_GAL_H, "volume_flow"),  # line 887
            (MBUS_CODE.FLOW_TEMPERATURE_F, "flow_temperature"),  # line 893
            (MBUS_CODE.TIME_POINT_DATETIME, "time_point"),  # line 908
            (MBUS_CODE.MANUFACTURER, "manufacturer"),       # line 925
            (MBUS_CODE.CUSTOMIZED_VIF, "customized_vif"),   # line 1012
            (MBUS_CODE.MANUFACTURER_SPECIFIC, "manufactur_specific"),  # line 1015
            (MBUS_CODE.CARBON_DIOXIDE_PPM, "CO²"),          # line 1033 (Unicode!)
            (MBUS_CODE.PARTICLES_PM2_5_UG_M3, "particles_PM2,5"),  # line 1057
            (MBUS_CODE.POTENTIAL_HYDROGEN_PH, "PH"),        # line 1069
        ]
        for code, name in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_code_name(code), name)

    def test_code_name_default_is_empty_string(self):
        """C++: `return "";` im default-Zweig."""
        self.assertEqual(self.lib.get_code_name(9999), "")

    # ---- getDeviceClass (MBusinoLib.cpp line 1182) ----------------------
    def test_device_class(self):
        erwartet = [
            (MBUS_CODE.ENERGY_WH, "energy"),           # line 1185
            (MBUS_CODE.MASS_KG, "weight"),             # line 1191
            (MBUS_CODE.OPERATING_TIME_DAYS, "duration"),  # line 1210
            (MBUS_CODE.POWER_W, "power"),              # line 1212
            (MBUS_CODE.FLOW_TEMPERATURE_C, "temperature"),  # line 1221
            (MBUS_CODE.TEMPERATURE_DIFF_K, "temperature_delta"),  # line 1229
            (MBUS_CODE.PRESSURE_BAR, "pressure"),      # line 1232
            (MBUS_CODE.BAUDRATE_BPS, "data_rate"),     # line 1235
            (MBUS_CODE.RELATIVE_HUMIDITY, "humidity"), # line 1243
            (MBUS_CODE.FREQUENCY, "frequency"),        # line 1246
            (MBUS_CODE.CARBON_DIOXIDE_PPM, "carbon_dioxide"),  # line 1271
            (MBUS_CODE.PARTICLES_PM10_UG_M3, "pm10"),  # line 1279
            (MBUS_CODE.RAINFALL_L_MM, "precipitation"),  # line 1281
        ]
        for code, klasse in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_device_class(code), klasse)

    def test_device_class_volume_depends_on_medium(self):
        """C++ line 1202-1206: VOLUME codes go through _volumeClassFromMedium
        (MBusinoLib.cpp line 1167-1180)."""
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
        """Large default branch (C++ line 1284-1377) returns ""."""
        for code in (MBUS_CODE.UNKNOWN_VIF, MBUS_CODE.TIME_POINT_DATE,
                     MBUS_CODE.MANUFACTURER, MBUS_CODE.CUSTOMIZED_VIF,
                     MBUS_CODE.SPECIAL_SUPPLIER_INFO, MBUS_CODE.MASS_FLOW_KG_H):
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_device_class(code), "")

    # ---- getStateClass (MBusinoLib.cpp line 1382) -----------------------
    def test_state_class(self):
        erwartet = [
            (MBUS_CODE.ENERGY_WH, "total_increasing"),    # line 1389
            (MBUS_CODE.VOLUME_M3, "total_increasing"),    # line 1391
            (MBUS_CODE.RAINFALL_L_MM, "total_increasing"),  # line 1397
            (MBUS_CODE.ON_TIME_DAYS, "total_increasing"), # line 1411
            (MBUS_CODE.AMPERES, "measurement"),           # line 1416
            (MBUS_CODE.POWER_W, "measurement"),           # line 1418
            (MBUS_CODE.RELATIVE_HUMIDITY, "measurement"), # line 1441
            (MBUS_CODE.BATTERY_PERCENTAGE, "measurement"),  # line 1452
            (MBUS_CODE.PARTICLES_PM10_UG_M3, "measurement"),  # line 1467
            (MBUS_CODE.UNKNOWN_VIF, ""),                  # line 1474
            (MBUS_CODE.TIME_POINT_DATE, ""),              # line 1479
            (MBUS_CODE.MANUFACTURER, ""),                 # line 1483
            (MBUS_CODE.SPECIAL_SUPPLIER_INFO, ""),        # no case -> default
        ]
        for code, klasse in erwartet:
            with self.subTest(code=code):
                self.assertEqual(self.lib.get_state_class(code), klasse)

    def test_state_class_default(self):
        self.assertEqual(self.lib.get_state_class(4242), "")


def self_device_class_via_helper(code) -> bool:
    """Checks the medium special case of the three volume codes."""
    lib = MBusinoLib()
    return (lib.get_device_class(code, 0x07) == "water"
            and lib.get_device_class(code, 0x03) == "gas"
            and lib.get_device_class(code) == "volume")


class TestTableIntegrity(unittest.TestCase):
    """Structure checks across the four tables."""

    def test_every_enum_code_has_name_and_device_class(self):
        """getCodeName knows ALL 123 enum values (the C++ switch has a case
        for every code); getDeviceClass all but the three volume codes,
        which run through the medium helper."""
        volumen = {MBUS_CODE.VOLUME_M3, MBUS_CODE.VOLUME_FT3, MBUS_CODE.VOLUME_GAL}
        for code in MBUS_CODE:
            with self.subTest(code=code.name):
                self.assertIn(code, CODE_NAME)
                if code not in volumen:
                    self.assertIn(code, DEVICE_CLASS)
                else:
                    # special case via _volumeClassFromMedium (C++ line 1202)
                    self.assertTrue(self_device_class_via_helper(code))

    def test_state_class_covers_all_but_one(self):
        """getStateClass has no case for SPECIAL_SUPPLIER_INFO (C++ default)."""
        fehlend = [code.name for code in MBUS_CODE if code not in STATE_CLASS]
        self.assertEqual(fehlend, ["SPECIAL_SUPPLIER_INFO"])

    def test_table_structure(self):
        """All tables: numeric keys, string values, no duplicates.
        (Dicts cannot have duplicate keys by construction - a silent
        entry would be the only hint that something collapsed during the
        port, therefore checked against the C++ group count.)"""
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
        # empty values are only allowed where C++ also returns ""
        for tabelle in (CODE_NAME, CODE_UNITS, MEDIUM_NAMES):
            for key, wert in tabelle.items():
                self.assertNotEqual(wert, "", "C++ liefert hier keinen leeren String: %r" % key)

    def test_device_class_empty_values_exist(self):
        """getDeviceClass/getStateClass deliberately return "" (no HA class)."""
        self.assertEqual(DEVICE_CLASS[MBUS_CODE.UNKNOWN_VIF], "")
        self.assertEqual(STATE_CLASS[MBUS_CODE.UNKNOWN_VIF], "")

    def test_medium_names_match_cpp_switch(self):
        """decodeHeader switch, MBusinoLib.cpp line 1610-1636."""
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
