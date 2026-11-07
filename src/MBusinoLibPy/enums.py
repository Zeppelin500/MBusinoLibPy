# -*- coding: utf-8 -*-
"""Enumerations and constants - 1:1 port from MBusinoLib.h.

The order of the MBUS_CODE members is identical to the C++ enum in
MBusinoLib.h (line 37-165): C++ numbers them 0,1,2,... in declaration
order and Python's IntEnum does exactly the same. Therefore all
numeric values (and with them vif_defs + getCodeName & Co.) match.
"""

from enum import IntEnum

# Constants from MBusinoLib.h line 31-33
MBUS_DEFAULT_BUFFER_SIZE = 254  # size of the internal C++ buffer (dropped in Python, see spec item 4)
ARDUINO_FLOAT_MIN = 1e-6        # "Assume 0 if less than this" - never used in the C++ code, documentation only
ARDUINO_FLOAT_DECIMALS = 6      # "6 decimals is just below the limit for Arduino float maths" -
                                # corresponds to the tolerance of the golden tests for value_scaled


class MBUS_CODE(IntEnum):
    """Supported VIF codes - corresponds to `enum MBUS_CODE` in MBusinoLib.h line 37.

    The value is the internal record identifier ("code" field of the JSON output),
    NOT the VIF byte value. The latter lives in the vif_defs table.
    """
    # unknown VIF - the original uses it as a failure hint (VIF 0x7E is not used in the Slave -> Master direction)
    UNKNOWN_VIF = 0

    # without VIFE: physical quantities straight from table 8.4.1 (EN 13757)
    ENERGY_WH = 1
    ENERGY_J = 2
    VOLUME_M3 = 3
    MASS_KG = 4
    ON_TIME_S = 5
    ON_TIME_MIN = 6
    ON_TIME_H = 7
    ON_TIME_DAYS = 8
    OPERATING_TIME_S = 9
    OPERATING_TIME_MIN = 10
    OPERATING_TIME_H = 11
    OPERATING_TIME_DAYS = 12
    POWER_W = 13
    POWER_J_H = 14
    VOLUME_FLOW_M3_H = 15
    VOLUME_FLOW_M3_MIN = 16
    VOLUME_FLOW_M3_S = 17
    MASS_FLOW_KG_H = 18
    FLOW_TEMPERATURE_C = 19
    RETURN_TEMPERATURE_C = 20
    TEMPERATURE_DIFF_K = 21
    EXTERNAL_TEMPERATURE_C = 22
    PRESSURE_BAR = 23
    TIME_POINT_DATE = 24
    TIME_POINT_DATETIME = 25
    AVG_DURATION_S = 26
    AVG_DURATION_MIN = 27
    AVG_DURATION_H = 28
    AVG_DURATION_DAYS = 29
    ACTUAL_DURATION_S = 30
    ACTUAL_DURATION_MIN = 31
    ACTUAL_DURATION_H = 32
    ACTUAL_DURATION_DAYS = 33
    FABRICATION_NUMBER = 34
    BUS_ADDRESS = 35

    # VIFE 0xFD: operating and counter data
    CREDIT = 36
    DEBIT = 37
    ACCESS_NUMBER = 38
    MANUFACTURER = 39
    PARAMETER_SET_ID = 40
    MODEL_VERSION = 41
    HARDWARE_VERSION = 42
    FIRMWARE_VERSION = 43
    SOFTWARE_VERSION = 44
    CUSTOMER_LOCATION = 45
    CUSTOMER = 46
    ERROR_FLAGS = 47
    ERROR_MASK = 48
    DIGITAL_OUTPUT = 49
    DIGITAL_INPUT = 50
    BAUDRATE_BPS = 51
    RESPONSE_DELAY_TIME = 52
    RETRY = 53
    SIZE_OF_STORAGE_BLOCK = 54
    STORAGE_INTERVAL_MONTH = 55
    GENERIC = 56
    VOLTS = 57
    AMPERES = 58
    RESET_COUNTER = 59
    CUMULATION_COUNTER = 60
    SPECIAL_SUPPLIER_INFO = 61

    # VIFE 0xFDFD: double extension (VIFE on VIFE)
    CURRENT_SELECTED_APL = 62
    SUB_DEVICES = 63
    REMAIN_BAT_LIFE_MONTH = 64
    CARBON_DIOXIDE_PPM = 65
    CARBON_MONOXIDE_PPM = 66
    VOLATILE_ORG_COMP_ppb = 67
    VOLATILE_ORG_COMP_UG_M3 = 68
    PARTICLES_UNSPEC_UG_M3 = 69
    PARTICLES_PM1_UG_M3 = 70
    PARTICLES_PM2_5_UG_M3 = 71
    PARTICLES_PM10_UG_M3 = 72
    PARTICLES_UNSPEC_1M3 = 73
    PARTICLES_PM1_1M3 = 74
    PARTICLES_PM2_5_1M3 = 75
    PARTICLES_PM10_1M3 = 76
    ILLUMINANCE_LUX = 77
    LUMINOUS_INTENSITY_CD = 78
    RADIANT_FLUX_DENS = 79
    WIND_SPEED_M_S = 80
    RAINFALL_L_MM = 81
    FORMAZIN_NEPHELOMETER_U = 82
    POTENTIAL_HYDROGEN_PH = 83
    DISMOUNTS_COUNTER = 84
    TEST_BUTTON_COUNTER = 85
    ALARM_COUNTER = 86
    ALARM_MUTE_COUNTER = 87
    OBSTACLE_DETECT_COUNTER = 88
    SMOKE_ENTRIES_COUNTER = 89
    SMOKE_CHAMBER_DEFECTS = 90
    SELF_TEST_COUNTER = 91
    SOUNDER_DEFECT_COUNTER = 92
    DECIBEL_A = 93
    BATTERY_PERCENTAGE = 94
    CHAMBER_POLLUTION_LEVEL = 95
    DISTANCE_MM = 96
    MOISTURE_LEVEL_PERCENT = 97
    PRESSURE_SENS_STATUS = 98
    SMOKE_ALARM_STATUS = 99
    CO_ALARM_STATUS = 100
    HEAT_ALARM_STATUS = 101
    DOOR_WINDOW_SENS_STATUS = 102

    # VIFE 0xFB: internationale Einheiten / abweichende Skalierung
    REACTIVE_ENERGY = 103
    REACTIVE_POWER = 104
    RELATIVE_HUMIDITY = 105
    VOLUME_FT3 = 106
    VOLUME_GAL = 107
    VOLUME_FLOW_GAL_M = 108
    VOLUME_FLOW_GAL_H = 109
    APPARENT_POWER = 110
    FLOW_TEMPERATURE_F = 111
    RETURN_TEMPERATURE_F = 112
    TEMPERATURE_DIFF_F = 113
    EXTERNAL_TEMPERATURE_F = 114
    TEMPERATURE_LIMIT_F = 115
    TEMPERATURE_LIMIT_C = 116
    MAX_POWER_W = 117
    PHASE_VOLT_DEG = 118
    PHASE_CURR_DEG = 119
    FREQUENCY = 120

    # VIFE 0xFC: benutzerdefinierter VIF als ASCII-String
    CUSTOMIZED_VIF = 121

    # VIFE 0xFF: manufacturer specific (never scaled)
    MANUFACTURER_SPECIFIC = 122


class MBUS_ERROR(IntEnum):
    """Error codes - corresponds to `enum MBUS_ERROR` in MBusinoLib.h line 168-176."""
    NO_ERROR = 0
    BUFFER_OVERFLOW = 1
    UNSUPPORTED_CODING = 2
    UNSUPPORTED_RANGE = 3
    UNSUPPORTED_VIF = 4
    NEGATIVE_VALUE = 5
