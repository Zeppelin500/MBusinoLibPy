# -*- coding: utf-8 -*-
"""Lookup tables for getCodeName()/getCodeUnits()/getDeviceClass()/getStateClass().

Diese vier C++-switch-Anweisungen sind hier als Dicts 1:1 abgebildet - jede
Every C++ fall-through group (several `case` before one `return`) is a group of
dict entries with a comment line. Missing keys mean the
C++ `default` return:

* CODE_UNITS: no entry -> C++ `return 0` (NULL) -> Python None
* CODE_NAME / DEVICE_CLASS / STATE_CLASS: no entry -> C++ `return ""` -> Python ""
"""

from .enums import MBUS_CODE


# ---------------------------------------------------------------------------
# Helper function from MBusinoLib.cpp line 1167: _volumeClassFromMedium()
# (called directly by getDeviceClass() for the volume codes)
# ---------------------------------------------------------------------------
# C++: switch (medium) with the M-Bus medium codes from decodeHeader().
_MEDIUM_TO_VOLUME_CLASS = {
    0x03: "gas",   # Gas
    0x06: "water",  # Warm Water
    0x07: "water",  # Water
    0x15: "water",  # Hot water
    0x16: "water",  # Cold water
    0x17: "water",  # Dual water
    # default: -> "volume" (unknown medium, everything else, incl. 0xFF)
}


def _volume_class_from_medium(medium: int) -> str:
    """Corresponds to _volumeClassFromMedium() in MBusinoLib.cpp line 1167-1180.

    Picks the Home Assistant device_class for cumulative volume records:
    Wasser-Medien -> "water", Gas -> "gas", alles andere (inkl. 0xFF) -> "volume".
    """
    return _MEDIUM_TO_VOLUME_CLASS.get(medium, "volume")


# ===========================================================================
# getCodeUnits() - C++ MBusinoLib.cpp line 660
# ===========================================================================
CODE_UNITS = {
    # Corresponds to MBusinoLib::getCodeUnits() in MBusinoLib.cpp line 660 (C++ switch with fall-through groups).
    # Every comment line names one C++ fall-through group, the lines below are its case statements.
    # C++: ENERGY_WH -> return "Wh"
    MBUS_CODE.ENERGY_WH: "Wh",
    # C++: ENERGY_J -> return "J"
    MBUS_CODE.ENERGY_J: "J",
    # C++: VOLUME_M3 -> return "m³"
    MBUS_CODE.VOLUME_M3: "m³",
    # C++: MASS_KG -> return "kg"
    MBUS_CODE.MASS_KG: "kg",
    # C++: ON_TIME_S / OPERATING_TIME_S / AVG_DURATION_S / ACTUAL_DURATION_S -> return "s"
    MBUS_CODE.ON_TIME_S: "s",
    MBUS_CODE.OPERATING_TIME_S: "s",
    MBUS_CODE.AVG_DURATION_S: "s",
    MBUS_CODE.ACTUAL_DURATION_S: "s",
    # C++: ON_TIME_MIN / OPERATING_TIME_MIN / AVG_DURATION_MIN / ACTUAL_DURATION_MIN -> return "min"
    MBUS_CODE.ON_TIME_MIN: "min",
    MBUS_CODE.OPERATING_TIME_MIN: "min",
    MBUS_CODE.AVG_DURATION_MIN: "min",
    MBUS_CODE.ACTUAL_DURATION_MIN: "min",
    # C++: ON_TIME_H / OPERATING_TIME_H / AVG_DURATION_H / ACTUAL_DURATION_H -> return "h"
    MBUS_CODE.ON_TIME_H: "h",
    MBUS_CODE.OPERATING_TIME_H: "h",
    MBUS_CODE.AVG_DURATION_H: "h",
    MBUS_CODE.ACTUAL_DURATION_H: "h",
    # C++: ON_TIME_DAYS / OPERATING_TIME_DAYS / AVG_DURATION_DAYS
    #      ACTUAL_DURATION_DAYS -> return "d"
    MBUS_CODE.ON_TIME_DAYS: "d",
    MBUS_CODE.OPERATING_TIME_DAYS: "d",
    MBUS_CODE.AVG_DURATION_DAYS: "d",
    MBUS_CODE.ACTUAL_DURATION_DAYS: "d",
    # C++: POWER_W / MAX_POWER_W -> return "W"
    MBUS_CODE.POWER_W: "W",
    MBUS_CODE.MAX_POWER_W: "W",
    # C++: POWER_J_H -> return "J/h"
    MBUS_CODE.POWER_J_H: "J/h",
    # C++: VOLUME_FLOW_M3_H -> return "m³/h"
    MBUS_CODE.VOLUME_FLOW_M3_H: "m³/h",
    # C++: VOLUME_FLOW_M3_MIN -> return "m³/min"
    MBUS_CODE.VOLUME_FLOW_M3_MIN: "m³/min",
    # C++: VOLUME_FLOW_M3_S -> return "m³/s"
    MBUS_CODE.VOLUME_FLOW_M3_S: "m³/s",
    # C++: MASS_FLOW_KG_H -> return "kg/h"
    MBUS_CODE.MASS_FLOW_KG_H: "kg/h",
    # C++: FLOW_TEMPERATURE_C / RETURN_TEMPERATURE_C / EXTERNAL_TEMPERATURE_C
    #      TEMPERATURE_LIMIT_C -> return "°C"
    MBUS_CODE.FLOW_TEMPERATURE_C: "°C",
    MBUS_CODE.RETURN_TEMPERATURE_C: "°C",
    MBUS_CODE.EXTERNAL_TEMPERATURE_C: "°C",
    MBUS_CODE.TEMPERATURE_LIMIT_C: "°C",
    # C++: TEMPERATURE_DIFF_K -> return "K"
    MBUS_CODE.TEMPERATURE_DIFF_K: "K",
    # C++: PRESSURE_BAR -> return "bar"
    MBUS_CODE.PRESSURE_BAR: "bar",
    # C++: TIME_POINT_DATE -> return "YYYYMMDD"
    MBUS_CODE.TIME_POINT_DATE: "YYYYMMDD",
    # C++: TIME_POINT_DATETIME -> return "YYYYMMDDhhmm"
    MBUS_CODE.TIME_POINT_DATETIME: "YYYYMMDDhhmm",
    # C++: BAUDRATE_BPS -> return "bit/s"
    MBUS_CODE.BAUDRATE_BPS: "bit/s",
    # C++: VOLTS -> return "V"
    MBUS_CODE.VOLTS: "V",
    # C++: AMPERES -> return "A"
    MBUS_CODE.AMPERES: "A",
    # C++: VOLUME_FT3 -> return "ft³"
    MBUS_CODE.VOLUME_FT3: "ft³",
    # C++: VOLUME_GAL -> return "gal"
    MBUS_CODE.VOLUME_GAL: "gal",
    # C++: VOLUME_FLOW_GAL_M -> return "gal/min"
    MBUS_CODE.VOLUME_FLOW_GAL_M: "gal/min",
    # C++: VOLUME_FLOW_GAL_H -> return "gal/h"
    MBUS_CODE.VOLUME_FLOW_GAL_H: "gal/h",
    # C++: FLOW_TEMPERATURE_F / RETURN_TEMPERATURE_F / TEMPERATURE_DIFF_F
    #      EXTERNAL_TEMPERATURE_F / TEMPERATURE_LIMIT_F -> return "°F"
    MBUS_CODE.FLOW_TEMPERATURE_F: "°F",
    MBUS_CODE.RETURN_TEMPERATURE_F: "°F",
    MBUS_CODE.TEMPERATURE_DIFF_F: "°F",
    MBUS_CODE.EXTERNAL_TEMPERATURE_F: "°F",
    MBUS_CODE.TEMPERATURE_LIMIT_F: "°F",
    # C++: STORAGE_INTERVAL_MONTH / REMAIN_BAT_LIFE_MONTH -> return "month"
    MBUS_CODE.STORAGE_INTERVAL_MONTH: "month",
    MBUS_CODE.REMAIN_BAT_LIFE_MONTH: "month",
    # C++: RELATIVE_HUMIDITY / BATTERY_PERCENTAGE / CHAMBER_POLLUTION_LEVEL
    #      MOISTURE_LEVEL_PERCENT -> return "%"
    MBUS_CODE.RELATIVE_HUMIDITY: "%",
    MBUS_CODE.BATTERY_PERCENTAGE: "%",
    MBUS_CODE.CHAMBER_POLLUTION_LEVEL: "%",
    MBUS_CODE.MOISTURE_LEVEL_PERCENT: "%",
    # C++: REACTIVE_ENERGY -> return "kvarh"
    MBUS_CODE.REACTIVE_ENERGY: "kvarh",
    # C++: REACTIVE_POWER -> return "kvar"
    MBUS_CODE.REACTIVE_POWER: "kvar",
    # C++: APPARENT_POWER -> return "kVA"
    MBUS_CODE.APPARENT_POWER: "kVA",
    # C++: PHASE_VOLT_DEG / PHASE_CURR_DEG -> return "°"
    MBUS_CODE.PHASE_VOLT_DEG: "°",
    MBUS_CODE.PHASE_CURR_DEG: "°",
    # C++: FREQUENCY -> return "Hz"
    MBUS_CODE.FREQUENCY: "Hz",
    # C++: CARBON_DIOXIDE_PPM / CARBON_MONOXIDE_PPM -> return "ppm"
    MBUS_CODE.CARBON_DIOXIDE_PPM: "ppm",
    MBUS_CODE.CARBON_MONOXIDE_PPM: "ppm",
    # C++: VOLATILE_ORG_COMP_ppb -> return "ppb"
    MBUS_CODE.VOLATILE_ORG_COMP_ppb: "ppb",
    # C++: VOLATILE_ORG_COMP_UG_M3 / PARTICLES_UNSPEC_UG_M3 / PARTICLES_PM1_UG_M3
    #      PARTICLES_PM2_5_UG_M3 / PARTICLES_PM10_UG_M3 -> return "µg/m³"
    MBUS_CODE.VOLATILE_ORG_COMP_UG_M3: "µg/m³",
    MBUS_CODE.PARTICLES_UNSPEC_UG_M3: "µg/m³",
    MBUS_CODE.PARTICLES_PM1_UG_M3: "µg/m³",
    MBUS_CODE.PARTICLES_PM2_5_UG_M3: "µg/m³",
    MBUS_CODE.PARTICLES_PM10_UG_M3: "µg/m³",
    # C++: PARTICLES_UNSPEC_1M3 / PARTICLES_PM1_1M3 / PARTICLES_PM2_5_1M3
    #      PARTICLES_PM10_1M3 -> return "1/m³"
    MBUS_CODE.PARTICLES_UNSPEC_1M3: "1/m³",
    MBUS_CODE.PARTICLES_PM1_1M3: "1/m³",
    MBUS_CODE.PARTICLES_PM2_5_1M3: "1/m³",
    MBUS_CODE.PARTICLES_PM10_1M3: "1/m³",
    # C++: ILLUMINANCE_LUX -> return "lx"
    MBUS_CODE.ILLUMINANCE_LUX: "lx",
    # C++: LUMINOUS_INTENSITY_CD -> return "cd"
    MBUS_CODE.LUMINOUS_INTENSITY_CD: "cd",
    # C++: RADIANT_FLUX_DENS -> return "W/m²"
    MBUS_CODE.RADIANT_FLUX_DENS: "W/m²",
    # C++: WIND_SPEED_M_S -> return "m/s"
    MBUS_CODE.WIND_SPEED_M_S: "m/s",
    # C++: RAINFALL_L_MM / DISTANCE_MM -> return "mm"
    MBUS_CODE.RAINFALL_L_MM: "mm",
    MBUS_CODE.DISTANCE_MM: "mm",
    # C++: FORMAZIN_NEPHELOMETER_U -> return "FNU"
    MBUS_CODE.FORMAZIN_NEPHELOMETER_U: "FNU",
    # C++: DECIBEL_A -> return "dB"
    MBUS_CODE.DECIBEL_A: "dB",
}
# Note: the 44 enum codes without an entry return `return 0` (NULL) in C++,
# e.g. UNKNOWN_VIF, ACCESS_NUMBER, MANUFACTURER - they carry no unit.


# ===========================================================================
# getCodeName() - C++ MBusinoLib.cpp line 847
# ===========================================================================
CODE_NAME = {
    # Corresponds to MBusinoLib::getCodeName() in MBusinoLib.cpp line 847 (C++ switch with fall-through groups).
    # Every comment line names one C++ fall-through group, the lines below are its case statements.
    # C++: UNKNOWN_VIF -> return "unknown_vif"
    MBUS_CODE.UNKNOWN_VIF: "unknown_vif",
    # C++: ENERGY_WH / ENERGY_J -> return "energy"
    MBUS_CODE.ENERGY_WH: "energy",
    MBUS_CODE.ENERGY_J: "energy",
    # C++: VOLUME_M3 / VOLUME_FT3 / VOLUME_GAL -> return "volume"
    MBUS_CODE.VOLUME_M3: "volume",
    MBUS_CODE.VOLUME_FT3: "volume",
    MBUS_CODE.VOLUME_GAL: "volume",
    # C++: MASS_KG -> return "mass"
    MBUS_CODE.MASS_KG: "mass",
    # C++: ON_TIME_S / ON_TIME_MIN / ON_TIME_H / ON_TIME_DAYS -> return "on_time"
    MBUS_CODE.ON_TIME_S: "on_time",
    MBUS_CODE.ON_TIME_MIN: "on_time",
    MBUS_CODE.ON_TIME_H: "on_time",
    MBUS_CODE.ON_TIME_DAYS: "on_time",
    # C++: OPERATING_TIME_S / OPERATING_TIME_MIN / OPERATING_TIME_H
    #      OPERATING_TIME_DAYS -> return "operating_time"
    MBUS_CODE.OPERATING_TIME_S: "operating_time",
    MBUS_CODE.OPERATING_TIME_MIN: "operating_time",
    MBUS_CODE.OPERATING_TIME_H: "operating_time",
    MBUS_CODE.OPERATING_TIME_DAYS: "operating_time",
    # C++: AVG_DURATION_S / AVG_DURATION_MIN / AVG_DURATION_H
    #      AVG_DURATION_DAYS -> return "avg_duration"
    MBUS_CODE.AVG_DURATION_S: "avg_duration",
    MBUS_CODE.AVG_DURATION_MIN: "avg_duration",
    MBUS_CODE.AVG_DURATION_H: "avg_duration",
    MBUS_CODE.AVG_DURATION_DAYS: "avg_duration",
    # C++: ACTUAL_DURATION_S / ACTUAL_DURATION_MIN / ACTUAL_DURATION_H
    #      ACTUAL_DURATION_DAYS -> return "actual_duration"
    MBUS_CODE.ACTUAL_DURATION_S: "actual_duration",
    MBUS_CODE.ACTUAL_DURATION_MIN: "actual_duration",
    MBUS_CODE.ACTUAL_DURATION_H: "actual_duration",
    MBUS_CODE.ACTUAL_DURATION_DAYS: "actual_duration",
    # C++: POWER_W / MAX_POWER_W / POWER_J_H -> return "power"
    MBUS_CODE.POWER_W: "power",
    MBUS_CODE.MAX_POWER_W: "power",
    MBUS_CODE.POWER_J_H: "power",
    # C++: VOLUME_FLOW_M3_H / VOLUME_FLOW_M3_MIN / VOLUME_FLOW_M3_S / VOLUME_FLOW_GAL_M
    #      VOLUME_FLOW_GAL_H -> return "volume_flow"
    MBUS_CODE.VOLUME_FLOW_M3_H: "volume_flow",
    MBUS_CODE.VOLUME_FLOW_M3_MIN: "volume_flow",
    MBUS_CODE.VOLUME_FLOW_M3_S: "volume_flow",
    MBUS_CODE.VOLUME_FLOW_GAL_M: "volume_flow",
    MBUS_CODE.VOLUME_FLOW_GAL_H: "volume_flow",
    # C++: MASS_FLOW_KG_H -> return "mass_flow"
    MBUS_CODE.MASS_FLOW_KG_H: "mass_flow",
    # C++: FLOW_TEMPERATURE_C / FLOW_TEMPERATURE_F -> return "flow_temperature"
    MBUS_CODE.FLOW_TEMPERATURE_C: "flow_temperature",
    MBUS_CODE.FLOW_TEMPERATURE_F: "flow_temperature",
    # C++: RETURN_TEMPERATURE_C / RETURN_TEMPERATURE_F -> return "return_temperature"
    MBUS_CODE.RETURN_TEMPERATURE_C: "return_temperature",
    MBUS_CODE.RETURN_TEMPERATURE_F: "return_temperature",
    # C++: EXTERNAL_TEMPERATURE_C / EXTERNAL_TEMPERATURE_F -> return "external_temperature"
    MBUS_CODE.EXTERNAL_TEMPERATURE_C: "external_temperature",
    MBUS_CODE.EXTERNAL_TEMPERATURE_F: "external_temperature",
    # C++: TEMPERATURE_LIMIT_C / TEMPERATURE_LIMIT_F -> return "temperature_limit"
    MBUS_CODE.TEMPERATURE_LIMIT_C: "temperature_limit",
    MBUS_CODE.TEMPERATURE_LIMIT_F: "temperature_limit",
    # C++: TEMPERATURE_DIFF_K / TEMPERATURE_DIFF_F -> return "temperature_diff"
    MBUS_CODE.TEMPERATURE_DIFF_K: "temperature_diff",
    MBUS_CODE.TEMPERATURE_DIFF_F: "temperature_diff",
    # C++: PRESSURE_BAR -> return "pressure"
    MBUS_CODE.PRESSURE_BAR: "pressure",
    # C++: TIME_POINT_DATE / TIME_POINT_DATETIME -> return "time_point"
    MBUS_CODE.TIME_POINT_DATE: "time_point",
    MBUS_CODE.TIME_POINT_DATETIME: "time_point",
    # C++: BAUDRATE_BPS -> return "baudrate"
    MBUS_CODE.BAUDRATE_BPS: "baudrate",
    # C++: VOLTS -> return "voltage"
    MBUS_CODE.VOLTS: "voltage",
    # C++: AMPERES -> return "current"
    MBUS_CODE.AMPERES: "current",
    # C++: FABRICATION_NUMBER -> return "fab_number"
    MBUS_CODE.FABRICATION_NUMBER: "fab_number",
    # C++: BUS_ADDRESS -> return "bus_address"
    MBUS_CODE.BUS_ADDRESS: "bus_address",
    # C++: CREDIT -> return "credit"
    MBUS_CODE.CREDIT: "credit",
    # C++: DEBIT -> return "debit"
    MBUS_CODE.DEBIT: "debit",
    # C++: ACCESS_NUMBER -> return "access_number"
    MBUS_CODE.ACCESS_NUMBER: "access_number",
    # C++: MANUFACTURER -> return "manufacturer"
    MBUS_CODE.MANUFACTURER: "manufacturer",
    # C++: PARAMETER_SET_ID -> return "set_id"
    MBUS_CODE.PARAMETER_SET_ID: "set_id",
    # C++: MODEL_VERSION -> return "model_version"
    MBUS_CODE.MODEL_VERSION: "model_version",
    # C++: HARDWARE_VERSION -> return "hardware_version"
    MBUS_CODE.HARDWARE_VERSION: "hardware_version",
    # C++: FIRMWARE_VERSION -> return "firmware_version"
    MBUS_CODE.FIRMWARE_VERSION: "firmware_version",
    # C++: SOFTWARE_VERSION -> return "software_version"
    MBUS_CODE.SOFTWARE_VERSION: "software_version",
    # C++: CUSTOMER_LOCATION -> return "customer_location"
    MBUS_CODE.CUSTOMER_LOCATION: "customer_location",
    # C++: CUSTOMER -> return "customer"
    MBUS_CODE.CUSTOMER: "customer",
    # C++: ERROR_FLAGS -> return "error_flags"
    MBUS_CODE.ERROR_FLAGS: "error_flags",
    # C++: ERROR_MASK -> return "error_mask"
    MBUS_CODE.ERROR_MASK: "error_mask",
    # C++: DIGITAL_OUTPUT -> return "digital_output"
    MBUS_CODE.DIGITAL_OUTPUT: "digital_output",
    # C++: DIGITAL_INPUT -> return "digital_input"
    MBUS_CODE.DIGITAL_INPUT: "digital_input",
    # C++: RESPONSE_DELAY_TIME -> return "response_delay"
    MBUS_CODE.RESPONSE_DELAY_TIME: "response_delay",
    # C++: RETRY -> return "retry"
    MBUS_CODE.RETRY: "retry",
    # C++: SIZE_OF_STORAGE_BLOCK -> return "sizeof_storageblock"
    MBUS_CODE.SIZE_OF_STORAGE_BLOCK: "sizeof_storageblock",
    # C++: STORAGE_INTERVAL_MONTH -> return "storage_interval"
    MBUS_CODE.STORAGE_INTERVAL_MONTH: "storage_interval",
    # C++: GENERIC -> return "generic"
    MBUS_CODE.GENERIC: "generic",
    # C++: RESET_COUNTER / CUMULATION_COUNTER -> return "counter"
    MBUS_CODE.RESET_COUNTER: "counter",
    MBUS_CODE.CUMULATION_COUNTER: "counter",
    # C++: CUSTOMIZED_VIF -> return "customized_vif"
    MBUS_CODE.CUSTOMIZED_VIF: "customized_vif",
    # C++: MANUFACTURER_SPECIFIC -> return "manufactur_specific"
    MBUS_CODE.MANUFACTURER_SPECIFIC: "manufactur_specific",
    # C++: RELATIVE_HUMIDITY -> return "humidity"
    MBUS_CODE.RELATIVE_HUMIDITY: "humidity",
    # C++: REACTIVE_ENERGY -> return "reactive_energy"
    MBUS_CODE.REACTIVE_ENERGY: "reactive_energy",
    # C++: REACTIVE_POWER -> return "reactive_power"
    MBUS_CODE.REACTIVE_POWER: "reactive_power",
    # C++: APPARENT_POWER -> return "apparent_power"
    MBUS_CODE.APPARENT_POWER: "apparent_power",
    # C++: PHASE_VOLT_DEG -> return "phase_deg_voltage"
    MBUS_CODE.PHASE_VOLT_DEG: "phase_deg_voltage",
    # C++: PHASE_CURR_DEG -> return "phase_deg_current"
    MBUS_CODE.PHASE_CURR_DEG: "phase_deg_current",
    # C++: FREQUENCY -> return "frequency"
    MBUS_CODE.FREQUENCY: "frequency",
    # C++: SPECIAL_SUPPLIER_INFO -> return "special_suppl_info"
    MBUS_CODE.SPECIAL_SUPPLIER_INFO: "special_suppl_info",
    # C++: CURRENT_SELECTED_APL -> return "current_selected_appl."
    MBUS_CODE.CURRENT_SELECTED_APL: "current_selected_appl.",
    # C++: SUB_DEVICES -> return "sub_devices"
    MBUS_CODE.SUB_DEVICES: "sub_devices",
    # C++: REMAIN_BAT_LIFE_MONTH -> return "remain_bat_life"
    MBUS_CODE.REMAIN_BAT_LIFE_MONTH: "remain_bat_life",
    # C++: CARBON_DIOXIDE_PPM -> return "CO²"
    MBUS_CODE.CARBON_DIOXIDE_PPM: "CO²",
    # C++: CARBON_MONOXIDE_PPM -> return "CO"
    MBUS_CODE.CARBON_MONOXIDE_PPM: "CO",
    # C++: VOLATILE_ORG_COMP_ppb / VOLATILE_ORG_COMP_UG_M3 -> return "VOC"
    MBUS_CODE.VOLATILE_ORG_COMP_ppb: "VOC",
    MBUS_CODE.VOLATILE_ORG_COMP_UG_M3: "VOC",
    # C++: PARTICLES_UNSPEC_UG_M3 / PARTICLES_UNSPEC_1M3 -> return "particels_unspecific"
    MBUS_CODE.PARTICLES_UNSPEC_UG_M3: "particels_unspecific",
    MBUS_CODE.PARTICLES_UNSPEC_1M3: "particels_unspecific",
    # C++: PARTICLES_PM1_UG_M3 / PARTICLES_PM1_1M3 -> return "particles_PM1"
    MBUS_CODE.PARTICLES_PM1_UG_M3: "particles_PM1",
    MBUS_CODE.PARTICLES_PM1_1M3: "particles_PM1",
    # C++: PARTICLES_PM2_5_UG_M3 / PARTICLES_PM2_5_1M3 -> return "particles_PM2,5"
    MBUS_CODE.PARTICLES_PM2_5_UG_M3: "particles_PM2,5",
    MBUS_CODE.PARTICLES_PM2_5_1M3: "particles_PM2,5",
    # C++: PARTICLES_PM10_UG_M3 / PARTICLES_PM10_1M3 -> return "particles_PM10"
    MBUS_CODE.PARTICLES_PM10_UG_M3: "particles_PM10",
    MBUS_CODE.PARTICLES_PM10_1M3: "particles_PM10",
    # C++: ILLUMINANCE_LUX -> return "illuminance"
    MBUS_CODE.ILLUMINANCE_LUX: "illuminance",
    # C++: LUMINOUS_INTENSITY_CD -> return "luminus_idensity"
    MBUS_CODE.LUMINOUS_INTENSITY_CD: "luminus_idensity",
    # C++: RADIANT_FLUX_DENS -> return "radiant_flux_density"
    MBUS_CODE.RADIANT_FLUX_DENS: "radiant_flux_density",
    # C++: WIND_SPEED_M_S -> return "wind_speed"
    MBUS_CODE.WIND_SPEED_M_S: "wind_speed",
    # C++: RAINFALL_L_MM -> return "rainfall"
    MBUS_CODE.RAINFALL_L_MM: "rainfall",
    # C++: FORMAZIN_NEPHELOMETER_U -> return "formazin_nephelometric"
    MBUS_CODE.FORMAZIN_NEPHELOMETER_U: "formazin_nephelometric",
    # C++: POTENTIAL_HYDROGEN_PH -> return "PH"
    MBUS_CODE.POTENTIAL_HYDROGEN_PH: "PH",
    # C++: DISMOUNTS_COUNTER -> return "dismounts_counter"
    MBUS_CODE.DISMOUNTS_COUNTER: "dismounts_counter",
    # C++: TEST_BUTTON_COUNTER -> return "test_button_counter"
    MBUS_CODE.TEST_BUTTON_COUNTER: "test_button_counter",
    # C++: ALARM_COUNTER -> return "alarm_counter"
    MBUS_CODE.ALARM_COUNTER: "alarm_counter",
    # C++: ALARM_MUTE_COUNTER -> return "alarm_mute_counter"
    MBUS_CODE.ALARM_MUTE_COUNTER: "alarm_mute_counter",
    # C++: OBSTACLE_DETECT_COUNTER -> return "obstacle_detect_counter"
    MBUS_CODE.OBSTACLE_DETECT_COUNTER: "obstacle_detect_counter",
    # C++: SMOKE_ENTRIES_COUNTER -> return "smoke_entries_counter"
    MBUS_CODE.SMOKE_ENTRIES_COUNTER: "smoke_entries_counter",
    # C++: SMOKE_CHAMBER_DEFECTS -> return "smoke_chamber_defects"
    MBUS_CODE.SMOKE_CHAMBER_DEFECTS: "smoke_chamber_defects",
    # C++: SELF_TEST_COUNTER -> return "self_test_counter"
    MBUS_CODE.SELF_TEST_COUNTER: "self_test_counter",
    # C++: SOUNDER_DEFECT_COUNTER -> return "sounder_defect_counter"
    MBUS_CODE.SOUNDER_DEFECT_COUNTER: "sounder_defect_counter",
    # C++: DECIBEL_A -> return "decibel_A"
    MBUS_CODE.DECIBEL_A: "decibel_A",
    # C++: BATTERY_PERCENTAGE -> return "battery"
    MBUS_CODE.BATTERY_PERCENTAGE: "battery",
    # C++: CHAMBER_POLLUTION_LEVEL -> return "chamber_pollution_level"
    MBUS_CODE.CHAMBER_POLLUTION_LEVEL: "chamber_pollution_level",
    # C++: DISTANCE_MM -> return "distance"
    MBUS_CODE.DISTANCE_MM: "distance",
    # C++: MOISTURE_LEVEL_PERCENT -> return "moisture_level"
    MBUS_CODE.MOISTURE_LEVEL_PERCENT: "moisture_level",
    # C++: PRESSURE_SENS_STATUS -> return "pressure_sens_status"
    MBUS_CODE.PRESSURE_SENS_STATUS: "pressure_sens_status",
    # C++: SMOKE_ALARM_STATUS -> return "smoke_alarm_status"
    MBUS_CODE.SMOKE_ALARM_STATUS: "smoke_alarm_status",
    # C++: CO_ALARM_STATUS -> return "CO_alarm_status"
    MBUS_CODE.CO_ALARM_STATUS: "CO_alarm_status",
    # C++: HEAT_ALARM_STATUS -> return "heat_alarm_status"
    MBUS_CODE.HEAT_ALARM_STATUS: "heat_alarm_status",
    # C++: DOOR_WINDOW_SENS_STATUS -> return "door_window_sens_status"
    MBUS_CODE.DOOR_WINDOW_SENS_STATUS: "door_window_sens_status",
}


# ===========================================================================
# getDeviceClass() - C++ MBusinoLib.cpp line 1182
# ===========================================================================
# NOTE: the three volume codes are missing here on purpose - in C++ they
# switch to _volumeClassFromMedium(medium); that special case lives
# steckt in MBusinoLib.get_device_class().
DEVICE_CLASS = {
    # Corresponds to MBusinoLib::getDeviceClass() in MBusinoLib.cpp line 1182 (C++ switch with fall-through groups).
    # Every comment line names one C++ fall-through group, the lines below are its case statements.
    # C++: ENERGY_WH / ENERGY_J -> return "energy"
    MBUS_CODE.ENERGY_WH: "energy",
    MBUS_CODE.ENERGY_J: "energy",
    # C++: MASS_KG -> return "weight"
    MBUS_CODE.MASS_KG: "weight",
    # C++: OPERATING_TIME_S / OPERATING_TIME_MIN / OPERATING_TIME_H / OPERATING_TIME_DAYS
    #      ON_TIME_S / ON_TIME_MIN / ON_TIME_H / ON_TIME_DAYS / AVG_DURATION_S / AVG_DURATION_MIN
    #      AVG_DURATION_H / AVG_DURATION_DAYS / ACTUAL_DURATION_S / ACTUAL_DURATION_MIN
    #      ACTUAL_DURATION_H / ACTUAL_DURATION_DAYS -> return "duration"
    MBUS_CODE.OPERATING_TIME_S: "duration",
    MBUS_CODE.OPERATING_TIME_MIN: "duration",
    MBUS_CODE.OPERATING_TIME_H: "duration",
    MBUS_CODE.OPERATING_TIME_DAYS: "duration",
    MBUS_CODE.ON_TIME_S: "duration",
    MBUS_CODE.ON_TIME_MIN: "duration",
    MBUS_CODE.ON_TIME_H: "duration",
    MBUS_CODE.ON_TIME_DAYS: "duration",
    MBUS_CODE.AVG_DURATION_S: "duration",
    MBUS_CODE.AVG_DURATION_MIN: "duration",
    MBUS_CODE.AVG_DURATION_H: "duration",
    MBUS_CODE.AVG_DURATION_DAYS: "duration",
    MBUS_CODE.ACTUAL_DURATION_S: "duration",
    MBUS_CODE.ACTUAL_DURATION_MIN: "duration",
    MBUS_CODE.ACTUAL_DURATION_H: "duration",
    MBUS_CODE.ACTUAL_DURATION_DAYS: "duration",
    # C++: POWER_W / MAX_POWER_W -> return "power"
    MBUS_CODE.POWER_W: "power",
    MBUS_CODE.MAX_POWER_W: "power",
    # C++: VOLUME_FLOW_M3_H / VOLUME_FLOW_M3_MIN / VOLUME_FLOW_M3_S / VOLUME_FLOW_GAL_M
    #      VOLUME_FLOW_GAL_H -> return "volume_flow_rate"
    MBUS_CODE.VOLUME_FLOW_M3_H: "volume_flow_rate",
    MBUS_CODE.VOLUME_FLOW_M3_MIN: "volume_flow_rate",
    MBUS_CODE.VOLUME_FLOW_M3_S: "volume_flow_rate",
    MBUS_CODE.VOLUME_FLOW_GAL_M: "volume_flow_rate",
    MBUS_CODE.VOLUME_FLOW_GAL_H: "volume_flow_rate",
    # C++: FLOW_TEMPERATURE_C / FLOW_TEMPERATURE_F / RETURN_TEMPERATURE_C / RETURN_TEMPERATURE_F
    #      EXTERNAL_TEMPERATURE_C / EXTERNAL_TEMPERATURE_F / TEMPERATURE_LIMIT_C
    #      TEMPERATURE_LIMIT_F -> return "temperature"
    MBUS_CODE.FLOW_TEMPERATURE_C: "temperature",
    MBUS_CODE.FLOW_TEMPERATURE_F: "temperature",
    MBUS_CODE.RETURN_TEMPERATURE_C: "temperature",
    MBUS_CODE.RETURN_TEMPERATURE_F: "temperature",
    MBUS_CODE.EXTERNAL_TEMPERATURE_C: "temperature",
    MBUS_CODE.EXTERNAL_TEMPERATURE_F: "temperature",
    MBUS_CODE.TEMPERATURE_LIMIT_C: "temperature",
    MBUS_CODE.TEMPERATURE_LIMIT_F: "temperature",
    # C++: TEMPERATURE_DIFF_K / TEMPERATURE_DIFF_F -> return "temperature_delta"
    MBUS_CODE.TEMPERATURE_DIFF_K: "temperature_delta",
    MBUS_CODE.TEMPERATURE_DIFF_F: "temperature_delta",
    # C++: PRESSURE_BAR -> return "pressure"
    MBUS_CODE.PRESSURE_BAR: "pressure",
    # C++: BAUDRATE_BPS -> return "data_rate"
    MBUS_CODE.BAUDRATE_BPS: "data_rate",
    # C++: VOLTS -> return "voltage"
    MBUS_CODE.VOLTS: "voltage",
    # C++: AMPERES -> return "current"
    MBUS_CODE.AMPERES: "current",
    # C++: RELATIVE_HUMIDITY -> return "humidity"
    MBUS_CODE.RELATIVE_HUMIDITY: "humidity",
    # C++: FREQUENCY -> return "frequency"
    MBUS_CODE.FREQUENCY: "frequency",
    # C++: APPARENT_POWER -> return "apparent_power"
    MBUS_CODE.APPARENT_POWER: "apparent_power",
    # C++: REACTIVE_POWER -> return "reactive_power"
    MBUS_CODE.REACTIVE_POWER: "reactive_power",
    # C++: REACTIVE_ENERGY -> return "reactive_energy"
    MBUS_CODE.REACTIVE_ENERGY: "reactive_energy",
    # C++: BATTERY_PERCENTAGE -> return "battery"
    MBUS_CODE.BATTERY_PERCENTAGE: "battery",
    # C++: MOISTURE_LEVEL_PERCENT -> return "moisture"
    MBUS_CODE.MOISTURE_LEVEL_PERCENT: "moisture",
    # C++: ILLUMINANCE_LUX -> return "illuminance"
    MBUS_CODE.ILLUMINANCE_LUX: "illuminance",
    # C++: RADIANT_FLUX_DENS -> return "irradiance"
    MBUS_CODE.RADIANT_FLUX_DENS: "irradiance",
    # C++: WIND_SPEED_M_S -> return "wind_speed"
    MBUS_CODE.WIND_SPEED_M_S: "wind_speed",
    # C++: POTENTIAL_HYDROGEN_PH -> return "ph"
    MBUS_CODE.POTENTIAL_HYDROGEN_PH: "ph",
    # C++: DISTANCE_MM -> return "distance"
    MBUS_CODE.DISTANCE_MM: "distance",
    # C++: DECIBEL_A -> return "sound_pressure"
    MBUS_CODE.DECIBEL_A: "sound_pressure",
    # C++: CARBON_DIOXIDE_PPM -> return "carbon_dioxide"
    MBUS_CODE.CARBON_DIOXIDE_PPM: "carbon_dioxide",
    # C++: CARBON_MONOXIDE_PPM -> return "carbon_monoxide"
    MBUS_CODE.CARBON_MONOXIDE_PPM: "carbon_monoxide",
    # C++: VOLATILE_ORG_COMP_UG_M3 -> return "volatile_organic_compounds"
    MBUS_CODE.VOLATILE_ORG_COMP_UG_M3: "volatile_organic_compounds",
    # C++: PARTICLES_PM1_UG_M3 -> return "pm1"
    MBUS_CODE.PARTICLES_PM1_UG_M3: "pm1",
    # C++: PARTICLES_PM2_5_UG_M3 -> return "pm25"
    MBUS_CODE.PARTICLES_PM2_5_UG_M3: "pm25",
    # C++: PARTICLES_PM10_UG_M3 -> return "pm10"
    MBUS_CODE.PARTICLES_PM10_UG_M3: "pm10",
    # C++: RAINFALL_L_MM -> return "precipitation"
    MBUS_CODE.RAINFALL_L_MM: "precipitation",
    # C++: MASS_FLOW_KG_H / POWER_J_H / TIME_POINT_DATE / TIME_POINT_DATETIME / UNKNOWN_VIF
    #      FABRICATION_NUMBER / BUS_ADDRESS / CREDIT / DEBIT / ACCESS_NUMBER / MANUFACTURER
    #      PARAMETER_SET_ID / MODEL_VERSION / HARDWARE_VERSION / FIRMWARE_VERSION
    #      SOFTWARE_VERSION / CUSTOMER_LOCATION / CUSTOMER / ERROR_FLAGS / ERROR_MASK
    #      DIGITAL_OUTPUT / DIGITAL_INPUT / RESPONSE_DELAY_TIME / RETRY / SIZE_OF_STORAGE_BLOCK
    #      STORAGE_INTERVAL_MONTH / GENERIC / RESET_COUNTER / CUMULATION_COUNTER / CUSTOMIZED_VIF
    #      MANUFACTURER_SPECIFIC / PHASE_VOLT_DEG / PHASE_CURR_DEG / SPECIAL_SUPPLIER_INFO
    #      CURRENT_SELECTED_APL / SUB_DEVICES / REMAIN_BAT_LIFE_MONTH / VOLATILE_ORG_COMP_ppb
    #      PARTICLES_UNSPEC_UG_M3 / PARTICLES_UNSPEC_1M3 / PARTICLES_PM1_1M3
    #      PARTICLES_PM2_5_1M3 / PARTICLES_PM10_1M3 / LUMINOUS_INTENSITY_CD
    #      FORMAZIN_NEPHELOMETER_U / DISMOUNTS_COUNTER / TEST_BUTTON_COUNTER / ALARM_COUNTER
    #      ALARM_MUTE_COUNTER / OBSTACLE_DETECT_COUNTER / SMOKE_ENTRIES_COUNTER
    #      SMOKE_CHAMBER_DEFECTS / SELF_TEST_COUNTER / SOUNDER_DEFECT_COUNTER
    #      CHAMBER_POLLUTION_LEVEL / PRESSURE_SENS_STATUS / SMOKE_ALARM_STATUS / CO_ALARM_STATUS
    #      HEAT_ALARM_STATUS / DOOR_WINDOW_SENS_STATUS -> return ""
    MBUS_CODE.MASS_FLOW_KG_H: "",
    MBUS_CODE.POWER_J_H: "",
    MBUS_CODE.TIME_POINT_DATE: "",
    MBUS_CODE.TIME_POINT_DATETIME: "",
    MBUS_CODE.UNKNOWN_VIF: "",
    MBUS_CODE.FABRICATION_NUMBER: "",
    MBUS_CODE.BUS_ADDRESS: "",
    MBUS_CODE.CREDIT: "",
    MBUS_CODE.DEBIT: "",
    MBUS_CODE.ACCESS_NUMBER: "",
    MBUS_CODE.MANUFACTURER: "",
    MBUS_CODE.PARAMETER_SET_ID: "",
    MBUS_CODE.MODEL_VERSION: "",
    MBUS_CODE.HARDWARE_VERSION: "",
    MBUS_CODE.FIRMWARE_VERSION: "",
    MBUS_CODE.SOFTWARE_VERSION: "",
    MBUS_CODE.CUSTOMER_LOCATION: "",
    MBUS_CODE.CUSTOMER: "",
    MBUS_CODE.ERROR_FLAGS: "",
    MBUS_CODE.ERROR_MASK: "",
    MBUS_CODE.DIGITAL_OUTPUT: "",
    MBUS_CODE.DIGITAL_INPUT: "",
    MBUS_CODE.RESPONSE_DELAY_TIME: "",
    MBUS_CODE.RETRY: "",
    MBUS_CODE.SIZE_OF_STORAGE_BLOCK: "",
    MBUS_CODE.STORAGE_INTERVAL_MONTH: "",
    MBUS_CODE.GENERIC: "",
    MBUS_CODE.RESET_COUNTER: "",
    MBUS_CODE.CUMULATION_COUNTER: "",
    MBUS_CODE.CUSTOMIZED_VIF: "",
    MBUS_CODE.MANUFACTURER_SPECIFIC: "",
    MBUS_CODE.PHASE_VOLT_DEG: "",
    MBUS_CODE.PHASE_CURR_DEG: "",
    MBUS_CODE.SPECIAL_SUPPLIER_INFO: "",
    MBUS_CODE.CURRENT_SELECTED_APL: "",
    MBUS_CODE.SUB_DEVICES: "",
    MBUS_CODE.REMAIN_BAT_LIFE_MONTH: "",
    MBUS_CODE.VOLATILE_ORG_COMP_ppb: "",
    MBUS_CODE.PARTICLES_UNSPEC_UG_M3: "",
    MBUS_CODE.PARTICLES_UNSPEC_1M3: "",
    MBUS_CODE.PARTICLES_PM1_1M3: "",
    MBUS_CODE.PARTICLES_PM2_5_1M3: "",
    MBUS_CODE.PARTICLES_PM10_1M3: "",
    MBUS_CODE.LUMINOUS_INTENSITY_CD: "",
    MBUS_CODE.FORMAZIN_NEPHELOMETER_U: "",
    MBUS_CODE.DISMOUNTS_COUNTER: "",
    MBUS_CODE.TEST_BUTTON_COUNTER: "",
    MBUS_CODE.ALARM_COUNTER: "",
    MBUS_CODE.ALARM_MUTE_COUNTER: "",
    MBUS_CODE.OBSTACLE_DETECT_COUNTER: "",
    MBUS_CODE.SMOKE_ENTRIES_COUNTER: "",
    MBUS_CODE.SMOKE_CHAMBER_DEFECTS: "",
    MBUS_CODE.SELF_TEST_COUNTER: "",
    MBUS_CODE.SOUNDER_DEFECT_COUNTER: "",
    MBUS_CODE.CHAMBER_POLLUTION_LEVEL: "",
    MBUS_CODE.PRESSURE_SENS_STATUS: "",
    MBUS_CODE.SMOKE_ALARM_STATUS: "",
    MBUS_CODE.CO_ALARM_STATUS: "",
    MBUS_CODE.HEAT_ALARM_STATUS: "",
    MBUS_CODE.DOOR_WINDOW_SENS_STATUS: "",
}


# ===========================================================================
# getStateClass() - C++ MBusinoLib.cpp line 1382
# ===========================================================================
STATE_CLASS = {
    # Corresponds to MBusinoLib::getStateClass() in MBusinoLib.cpp line 1382 (C++ switch with fall-through groups).
    # Every comment line names one C++ fall-through group, the lines below are its case statements.
    # C++: ENERGY_WH / ENERGY_J / VOLUME_M3 / VOLUME_FT3 / VOLUME_GAL / REACTIVE_ENERGY
    #      RAINFALL_L_MM / OPERATING_TIME_S / OPERATING_TIME_MIN / OPERATING_TIME_H
    #      OPERATING_TIME_DAYS / ON_TIME_S / ON_TIME_MIN / ON_TIME_H / ON_TIME_DAYS
    #      AVG_DURATION_S / AVG_DURATION_MIN / AVG_DURATION_H / AVG_DURATION_DAYS
    #      ACTUAL_DURATION_S / ACTUAL_DURATION_MIN / ACTUAL_DURATION_H
    #      ACTUAL_DURATION_DAYS -> return "total_increasing"
    MBUS_CODE.ENERGY_WH: "total_increasing",
    MBUS_CODE.ENERGY_J: "total_increasing",
    MBUS_CODE.VOLUME_M3: "total_increasing",
    MBUS_CODE.VOLUME_FT3: "total_increasing",
    MBUS_CODE.VOLUME_GAL: "total_increasing",
    MBUS_CODE.REACTIVE_ENERGY: "total_increasing",
    MBUS_CODE.RAINFALL_L_MM: "total_increasing",
    MBUS_CODE.OPERATING_TIME_S: "total_increasing",
    MBUS_CODE.OPERATING_TIME_MIN: "total_increasing",
    MBUS_CODE.OPERATING_TIME_H: "total_increasing",
    MBUS_CODE.OPERATING_TIME_DAYS: "total_increasing",
    MBUS_CODE.ON_TIME_S: "total_increasing",
    MBUS_CODE.ON_TIME_MIN: "total_increasing",
    MBUS_CODE.ON_TIME_H: "total_increasing",
    MBUS_CODE.ON_TIME_DAYS: "total_increasing",
    MBUS_CODE.AVG_DURATION_S: "total_increasing",
    MBUS_CODE.AVG_DURATION_MIN: "total_increasing",
    MBUS_CODE.AVG_DURATION_H: "total_increasing",
    MBUS_CODE.AVG_DURATION_DAYS: "total_increasing",
    MBUS_CODE.ACTUAL_DURATION_S: "total_increasing",
    MBUS_CODE.ACTUAL_DURATION_MIN: "total_increasing",
    MBUS_CODE.ACTUAL_DURATION_H: "total_increasing",
    MBUS_CODE.ACTUAL_DURATION_DAYS: "total_increasing",
    # C++: AMPERES / MASS_KG / POWER_W / MAX_POWER_W / POWER_J_H / VOLUME_FLOW_M3_H
    #      VOLUME_FLOW_M3_MIN / VOLUME_FLOW_M3_S / VOLUME_FLOW_GAL_M / VOLUME_FLOW_GAL_H
    #      MASS_FLOW_KG_H / FLOW_TEMPERATURE_C / FLOW_TEMPERATURE_F / RETURN_TEMPERATURE_C
    #      RETURN_TEMPERATURE_F / EXTERNAL_TEMPERATURE_C / EXTERNAL_TEMPERATURE_F
    #      TEMPERATURE_LIMIT_C / TEMPERATURE_LIMIT_F / TEMPERATURE_DIFF_K / TEMPERATURE_DIFF_F
    #      PRESSURE_BAR / BAUDRATE_BPS / VOLTS / RELATIVE_HUMIDITY / PHASE_VOLT_DEG
    #      PHASE_CURR_DEG / FREQUENCY / APPARENT_POWER / REACTIVE_POWER / BATTERY_PERCENTAGE
    #      MOISTURE_LEVEL_PERCENT / ILLUMINANCE_LUX / RADIANT_FLUX_DENS / WIND_SPEED_M_S
    #      POTENTIAL_HYDROGEN_PH / CARBON_DIOXIDE_PPM / CARBON_MONOXIDE_PPM
    #      VOLATILE_ORG_COMP_ppb / VOLATILE_ORG_COMP_UG_M3 / PARTICLES_UNSPEC_UG_M3
    #      PARTICLES_UNSPEC_1M3 / PARTICLES_PM1_UG_M3 / PARTICLES_PM1_1M3 / PARTICLES_PM2_5_UG_M3
    #      PARTICLES_PM2_5_1M3 / PARTICLES_PM10_UG_M3 / PARTICLES_PM10_1M3
    #      LUMINOUS_INTENSITY_CD / FORMAZIN_NEPHELOMETER_U / DISTANCE_MM / DECIBEL_A
    #      CHAMBER_POLLUTION_LEVEL -> return "measurement"
    MBUS_CODE.AMPERES: "measurement",
    MBUS_CODE.MASS_KG: "measurement",
    MBUS_CODE.POWER_W: "measurement",
    MBUS_CODE.MAX_POWER_W: "measurement",
    MBUS_CODE.POWER_J_H: "measurement",
    MBUS_CODE.VOLUME_FLOW_M3_H: "measurement",
    MBUS_CODE.VOLUME_FLOW_M3_MIN: "measurement",
    MBUS_CODE.VOLUME_FLOW_M3_S: "measurement",
    MBUS_CODE.VOLUME_FLOW_GAL_M: "measurement",
    MBUS_CODE.VOLUME_FLOW_GAL_H: "measurement",
    MBUS_CODE.MASS_FLOW_KG_H: "measurement",
    MBUS_CODE.FLOW_TEMPERATURE_C: "measurement",
    MBUS_CODE.FLOW_TEMPERATURE_F: "measurement",
    MBUS_CODE.RETURN_TEMPERATURE_C: "measurement",
    MBUS_CODE.RETURN_TEMPERATURE_F: "measurement",
    MBUS_CODE.EXTERNAL_TEMPERATURE_C: "measurement",
    MBUS_CODE.EXTERNAL_TEMPERATURE_F: "measurement",
    MBUS_CODE.TEMPERATURE_LIMIT_C: "measurement",
    MBUS_CODE.TEMPERATURE_LIMIT_F: "measurement",
    MBUS_CODE.TEMPERATURE_DIFF_K: "measurement",
    MBUS_CODE.TEMPERATURE_DIFF_F: "measurement",
    MBUS_CODE.PRESSURE_BAR: "measurement",
    MBUS_CODE.BAUDRATE_BPS: "measurement",
    MBUS_CODE.VOLTS: "measurement",
    MBUS_CODE.RELATIVE_HUMIDITY: "measurement",
    MBUS_CODE.PHASE_VOLT_DEG: "measurement",
    MBUS_CODE.PHASE_CURR_DEG: "measurement",
    MBUS_CODE.FREQUENCY: "measurement",
    MBUS_CODE.APPARENT_POWER: "measurement",
    MBUS_CODE.REACTIVE_POWER: "measurement",
    MBUS_CODE.BATTERY_PERCENTAGE: "measurement",
    MBUS_CODE.MOISTURE_LEVEL_PERCENT: "measurement",
    MBUS_CODE.ILLUMINANCE_LUX: "measurement",
    MBUS_CODE.RADIANT_FLUX_DENS: "measurement",
    MBUS_CODE.WIND_SPEED_M_S: "measurement",
    MBUS_CODE.POTENTIAL_HYDROGEN_PH: "measurement",
    MBUS_CODE.CARBON_DIOXIDE_PPM: "measurement",
    MBUS_CODE.CARBON_MONOXIDE_PPM: "measurement",
    MBUS_CODE.VOLATILE_ORG_COMP_ppb: "measurement",
    MBUS_CODE.VOLATILE_ORG_COMP_UG_M3: "measurement",
    MBUS_CODE.PARTICLES_UNSPEC_UG_M3: "measurement",
    MBUS_CODE.PARTICLES_UNSPEC_1M3: "measurement",
    MBUS_CODE.PARTICLES_PM1_UG_M3: "measurement",
    MBUS_CODE.PARTICLES_PM1_1M3: "measurement",
    MBUS_CODE.PARTICLES_PM2_5_UG_M3: "measurement",
    MBUS_CODE.PARTICLES_PM2_5_1M3: "measurement",
    MBUS_CODE.PARTICLES_PM10_UG_M3: "measurement",
    MBUS_CODE.PARTICLES_PM10_1M3: "measurement",
    MBUS_CODE.LUMINOUS_INTENSITY_CD: "measurement",
    MBUS_CODE.FORMAZIN_NEPHELOMETER_U: "measurement",
    MBUS_CODE.DISTANCE_MM: "measurement",
    MBUS_CODE.DECIBEL_A: "measurement",
    MBUS_CODE.CHAMBER_POLLUTION_LEVEL: "measurement",
    # C++: UNKNOWN_VIF / TIME_POINT_DATE / TIME_POINT_DATETIME / FABRICATION_NUMBER / BUS_ADDRESS
    #      CREDIT / DEBIT / ACCESS_NUMBER / MANUFACTURER / PARAMETER_SET_ID / MODEL_VERSION
    #      HARDWARE_VERSION / FIRMWARE_VERSION / SOFTWARE_VERSION / CUSTOMER_LOCATION / CUSTOMER
    #      ERROR_FLAGS / ERROR_MASK / DIGITAL_OUTPUT / DIGITAL_INPUT / RESPONSE_DELAY_TIME
    #      RETRY / SIZE_OF_STORAGE_BLOCK / STORAGE_INTERVAL_MONTH / GENERIC / RESET_COUNTER
    #      CUMULATION_COUNTER / CUSTOMIZED_VIF / MANUFACTURER_SPECIFIC / CURRENT_SELECTED_APL
    #      SUB_DEVICES / REMAIN_BAT_LIFE_MONTH / DISMOUNTS_COUNTER / TEST_BUTTON_COUNTER
    #      ALARM_COUNTER / ALARM_MUTE_COUNTER / OBSTACLE_DETECT_COUNTER / SMOKE_ENTRIES_COUNTER
    #      SMOKE_CHAMBER_DEFECTS / SELF_TEST_COUNTER / SOUNDER_DEFECT_COUNTER
    #      PRESSURE_SENS_STATUS / SMOKE_ALARM_STATUS / CO_ALARM_STATUS / HEAT_ALARM_STATUS
    #      DOOR_WINDOW_SENS_STATUS -> return ""
    MBUS_CODE.UNKNOWN_VIF: "",
    MBUS_CODE.TIME_POINT_DATE: "",
    MBUS_CODE.TIME_POINT_DATETIME: "",
    MBUS_CODE.FABRICATION_NUMBER: "",
    MBUS_CODE.BUS_ADDRESS: "",
    MBUS_CODE.CREDIT: "",
    MBUS_CODE.DEBIT: "",
    MBUS_CODE.ACCESS_NUMBER: "",
    MBUS_CODE.MANUFACTURER: "",
    MBUS_CODE.PARAMETER_SET_ID: "",
    MBUS_CODE.MODEL_VERSION: "",
    MBUS_CODE.HARDWARE_VERSION: "",
    MBUS_CODE.FIRMWARE_VERSION: "",
    MBUS_CODE.SOFTWARE_VERSION: "",
    MBUS_CODE.CUSTOMER_LOCATION: "",
    MBUS_CODE.CUSTOMER: "",
    MBUS_CODE.ERROR_FLAGS: "",
    MBUS_CODE.ERROR_MASK: "",
    MBUS_CODE.DIGITAL_OUTPUT: "",
    MBUS_CODE.DIGITAL_INPUT: "",
    MBUS_CODE.RESPONSE_DELAY_TIME: "",
    MBUS_CODE.RETRY: "",
    MBUS_CODE.SIZE_OF_STORAGE_BLOCK: "",
    MBUS_CODE.STORAGE_INTERVAL_MONTH: "",
    MBUS_CODE.GENERIC: "",
    MBUS_CODE.RESET_COUNTER: "",
    MBUS_CODE.CUMULATION_COUNTER: "",
    MBUS_CODE.CUSTOMIZED_VIF: "",
    MBUS_CODE.MANUFACTURER_SPECIFIC: "",
    MBUS_CODE.CURRENT_SELECTED_APL: "",
    MBUS_CODE.SUB_DEVICES: "",
    MBUS_CODE.REMAIN_BAT_LIFE_MONTH: "",
    MBUS_CODE.DISMOUNTS_COUNTER: "",
    MBUS_CODE.TEST_BUTTON_COUNTER: "",
    MBUS_CODE.ALARM_COUNTER: "",
    MBUS_CODE.ALARM_MUTE_COUNTER: "",
    MBUS_CODE.OBSTACLE_DETECT_COUNTER: "",
    MBUS_CODE.SMOKE_ENTRIES_COUNTER: "",
    MBUS_CODE.SMOKE_CHAMBER_DEFECTS: "",
    MBUS_CODE.SELF_TEST_COUNTER: "",
    MBUS_CODE.SOUNDER_DEFECT_COUNTER: "",
    MBUS_CODE.PRESSURE_SENS_STATUS: "",
    MBUS_CODE.SMOKE_ALARM_STATUS: "",
    MBUS_CODE.CO_ALARM_STATUS: "",
    MBUS_CODE.HEAT_ALARM_STATUS: "",
    MBUS_CODE.DOOR_WINDOW_SENS_STATUS: "",
}
# Note: SPECIAL_SUPPLIER_INFO has no own case in the C++ switch and falls
# through `default` to "" - therefore no entry here, .get(code, "") returns "".



# ===========================================================================
# decodeHeader() - medium names, C++ MBusinoLib.cpp line 1610-1636
# ===========================================================================
MEDIUM_NAMES = {
    0x01: "Oil",
    0x02: "Electricity",
    0x03: "Gas",
    0x04: "Heat",
    0x05: "Steam",
    0x06: "Warm Water",
    0x07: "Water",
    0x08: "Heat Cost Allocator",
    0x09: "Compressed Air",
    0x0A: "Cooling load meter (Volume)",
    0x0B: "Cooling load meter (Mass)",
    0x0C: "Heat (Volume)",
    0x0D: "Heat (Mass)",
    0x0E: "Combined Heat/Cooling",
    0x0F: "Bus/System component",
    0x14: "Calorific value",
    0x15: "Hot water",
    0x16: "Cold water",
    0x17: "Dual water",
    0x37: "Radio converter",
    # default (all other codes) -> "Unknown"
}
