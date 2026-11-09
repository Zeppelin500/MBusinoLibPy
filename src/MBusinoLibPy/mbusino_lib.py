# -*- coding: utf-8 -*-
"""Core class ``MBusinoLib`` - a 1:1 port of ``MBusinoLib.cpp`` (C++/Arduino).

Every method states in its comment the corresponding C++ function in
``MBusinoLib/src/MBusinoLib.cpp``, so you can switch between the two
implementations function by function.

Deliberate deviations from the original (spec item 4 of the porting task):

* The internal buffer plus ``reset()``/``getBuffer()``/``copy()``/``getSize()``
  is dropped completely - the Python API takes ``bytes``/``bytearray`` as
  arguments. Only ``_error`` remains, just like the C++ ``_error``.
* ``get_error()`` behaves like the C++ version: it returns **and** clears
  the error (the C++ ``getError()``).
* Instead of UB (out-of-bounds reads in the original) Python stops cleanly
  and sets ``BUFFER_OVERFLOW`` - every affected spot is commented
  individually.

All numeric operations run in the same order and with the same types as in
the C++ code (``int16_t``/``int32_t`` wrap-around, truncation of the
``int8_t`` scalar, 32-bit ``float`` for "real" records), so the values
are bit-identical. Only ArduinoJson's *output* rounds, therefore the
golden tests compare ``value_scaled`` with a tolerance
(relative 1e-6 / absolute 1e-6, see ``ARDUINO_FLOAT_DECIMALS = 6``).
"""

from __future__ import annotations

import struct
from enum import IntEnum  # noqa: F401  (imported only so the type is available)

from .enums import (
    ARDUINO_FLOAT_DECIMALS,  # noqa: F401  (documentation value, see enums.py)
    ARDUINO_FLOAT_MIN,  # noqa: F401
    MBUS_DEFAULT_BUFFER_SIZE,  # noqa: F401
    MBUS_CODE,
    MBUS_ERROR,
)
from .lookup_tables import (
    CODE_NAME,
    CODE_UNITS,
    DEVICE_CLASS,
    MEDIUM_NAMES,
    STATE_CLASS,
    _volume_class_from_medium,
)
from .vif_defs import VIF_DEFS

# ---------------------------------------------------------------------------
# NEW (not present in MBusinoLib): readable error messages
# ---------------------------------------------------------------------------
# Mapping follows the `enum MBUS_ERROR` from MBusinoLib.h. The C++ enum
# still carries UNSUPPORTED_CODING (2), UNSUPPORTED_RANGE (3) and
# NEGATIVE_VALUE (5) - leftovers from the old AllWize encoder that the
# decoder never sets (the only error assignments in MBusinoLib.cpp live in
# decodeRecords(): BUFFER_OVERFLOW twice, UNSUPPORTED_VIF once) - they were
# dropped from the Python enum, see enums.py.
_ERROR_MESSAGES = {
    MBUS_ERROR.NO_ERROR: "No error.",
    MBUS_ERROR.BUFFER_OVERFLOW: (
        "Buffer too small or telegram incomplete: the declared length does not "
        "fit into the given data, or a record would run past the end of the "
        "buffer."
    ),
    MBUS_ERROR.UNSUPPORTED_VIF: (
        "Unknown or unsupported VIF - the record could not be matched to any "
        "definition in vif_defs."
    ),
}


# ---------------------------------------------------------------------------
# Small helpers for the C++ type semantics
# ---------------------------------------------------------------------------
class _OutOfBounds(Exception):
    """Internal: read outside the real buffer (in C++ this would be UB)."""


def _to_int8(value: int) -> int:
    """C++: assignment of an expression (uint32_t arithmetic) to ``int8_t``.

    GCC/Clang truncate to the low 8 bits and read them as two's complement
    (defined in C++20, implementation-defined before that).
    ``2**32`` is a multiple of 256, so truncating to 8 bits is enough -
    also for negative Python intermediate values (``-3 & 0xFF == 0xFD``).
    """
    low = value & 0xFF
    return low - 0x100 if low & 0x80 else low


def _to_int16(value: int) -> int:
    """C++: ``value = (int64_t)value16;`` with ``int16_t value16`` (sign extension)."""
    low = value & 0xFFFF
    return low - 0x10000 if low & 0x8000 else low


def _to_int32(value: int) -> int:
    """C++: ``value = (int64_t)value32;`` with ``int32_t value32`` (sign extension)."""
    low = value & 0xFFFFFFFF
    return low - 0x100000000 if low & 0x80000000 else low


def _parse_hex(text: str):
    """Corresponds to ``parseHex()`` in test_decode.cpp.

    Splits "68 56 56 68 ..." / "0x68,0x56,..." input into a byte sequence.
    Convenience for ``decode_telegram("68 56 ...")`` - the original reads
    the input only from argv/stdin, here a plain string is accepted as well.
    """
    raw = []
    for token in text.replace(",", " ").split():
        token = token.strip()
        if token.lower().startswith("0x"):
            token = token[2:]
        if not token:
            continue
        raw.append(int(token, 16) & 0xFF)
    return bytes(raw)


# ---------------------------------------------------------------------------
# The class
# ---------------------------------------------------------------------------
class MBusinoLib:
    """Decoder for M-Bus RSP_UD telegrams - counterpart of the C++ class.

    C++: ``class MBusinoLib`` in MBusinoLib.h.

    Example::

        decode = MBusinoLib()
        records = decode.decode_records(telegram[0x13:packet_size],
                                        packet_size - 0x13 - 2)
        print(decode.get_error())
    """

    # __init__ corresponds to MBusinoLib::MBusinoLib() in MBusinoLib.cpp.
    # That constructor only allocates the work buffer and sets _cursor/_error;
    # there is no buffer in Python (spec item 4) and _error starts at
    # NO_ERROR like in C++ (``uint8_t _error = NO_ERROR;`` in MBusinoLib.h).
    def __init__(self) -> None:
        self._error: IntEnum = MBUS_ERROR.NO_ERROR

    # ------------------------------------------------------------------
    # Errors
    # ------------------------------------------------------------------
    def get_error(self) -> int:
        """Corresponds to MBusinoLib::getError() in MBusinoLib.cpp.

        Like the original: returns the error code AND clears the internal
        error back to ``NO_ERROR``. To keep the value, read
        ``decode._error`` or call ``get_error_message()`` FIRST.
        """
        error = self._error
        self._error = MBUS_ERROR.NO_ERROR
        return int(error)

    def get_error_message(self, code: int = None) -> str:
        """NEW (not in C++): readable English error message.

        Without an argument the method reports the currently stored error -
        unlike ``get_error()`` it clears nothing, so you can read
        ``get_error_message()`` first and ``get_error()`` afterwards.

        :param code: optional MBUS_ERROR value instead of the internal state

        Example::

            >>> MBusinoLib().get_error_message()
            'No error.'
            >>> MBusinoLib().get_error_message(4)   # MBUS_ERROR.UNSUPPORTED_VIF
            'Unknown or unsupported VIF - the record could not be matched to any definition in vif_defs.'
        """
        if code is None:
            code = self._error
        try:
            return _ERROR_MESSAGES.get(MBUS_ERROR(code), "Unknown error code %s." % code)
        except ValueError:
            # Value outside the enum (e.g. a raw/error value from somewhere else)
            return "Unknown error code %s." % code

    # ------------------------------------------------------------------
    # Lookup tables (correspond to the four C++ switch methods)
    # ------------------------------------------------------------------
    def get_code_name(self, code: int) -> str:
        """Corresponds to MBusinoLib::getCodeName() in MBusinoLib.cpp.

        :param code: MBUS_CODE value (e.g. ``MBUS_CODE.ENERGY_WH``)
        :return: record name like "energy", "" for unknown codes (C++: default)
        """
        return CODE_NAME.get(code, "")

    def get_code_units(self, code: int):
        """Corresponds to MBusinoLib::getCodeUnits() in MBusinoLib.cpp.

        :return: unit ("Wh", "m³", ...) or ``None`` - ``None`` corresponds to
                 the NULL pointer the original returns via ``return 0;``

        Example::

            >>> MBusinoLib().get_code_units(MBUS_CODE.VOLUME_M3)
            'm³'
            >>> MBusinoLib().get_code_units(MBUS_CODE.UNKNOWN_VIF) is None   # C++: return 0 / NULL
            True
        """
        return CODE_UNITS.get(code)  # no entry -> None, just like in C++

    def get_device_class(self, code: int, medium: int = 0xFF) -> str:
        """Corresponds to MBusinoLib::getDeviceClass() in MBusinoLib.cpp.

        :param code: MBUS_CODE value
        :param medium: M-Bus medium byte from ``decode_header()`` ("medium_code"),
                       default 0xFF = unknown - like the C++ default parameter
        :return: Home Assistant device_class, "" when none applies

        Example (the medium byte selects water/gas for volume records)::

            >>> MBusinoLib().get_device_class(MBUS_CODE.VOLUME_M3, medium=0x07)
            'water'
            >>> MBusinoLib().get_device_class(MBUS_CODE.VOLUME_M3, medium=0x03)
            'gas'
        """
        # in getDeviceClass(): the three volume codes call the medium helper
        # (case VOLUME_M3 / VOLUME_FT3 / VOLUME_GAL).
        if code in (MBUS_CODE.VOLUME_M3, MBUS_CODE.VOLUME_FT3, MBUS_CODE.VOLUME_GAL):
            return _volume_class_from_medium(medium)
        return DEVICE_CLASS.get(code, "")

    def get_state_class(self, code: int) -> str:
        """Corresponds to MBusinoLib::getStateClass() in MBusinoLib.cpp.

        :return: "total_increasing" / "measurement" / "" (C++: default)
        """
        # SPECIAL_SUPPLIER_INFO has no own case in the C++ switch and falls
        # through default to "" - .get() does the same here.
        return STATE_CLASS.get(code, "")

    # ------------------------------------------------------------------
    # Internal helpers (correspond to the protected C++ methods)
    # ------------------------------------------------------------------
    @staticmethod
    def _find_definition(vif: int) -> int:
        """Corresponds to MBusinoLib::_findDefinition() in MBusinoLib.cpp.

        Searches for the FIRST table entry with ``base <= vif < base + size``.

        :return: index into ``VIF_DEFS`` or -1 when nothing was found
                   (C++: ``int16_t``, returns -1)
        """
        for index, (_code, base, size, _scalar) in enumerate(VIF_DEFS):
            if base <= vif < (base + size):
                return index
        return -1

    @staticmethod
    def _get_vif(code: int, scalar: int) -> int:
        """Corresponds to MBusinoLib::_getVIF() in MBusinoLib.cpp.

        Inverse of ``_find_definition``: returns the VIF matching code and
        scaling (the original never calls it while decoding, only the
        AUnit tests do).

        :return: VIF value or 0xFF when no valid combination exists
                 (C++ comment: "this is not a valid VIF")
        """
        for _code, base, size, def_scalar in VIF_DEFS:
            if code == _code:
                if def_scalar <= scalar < (def_scalar + size):
                    return base + (scalar - def_scalar)
        return 0xFF

    # ------------------------------------------------------------------
    # Records
    # ------------------------------------------------------------------
    def decode_records(self, buffer, size: int = None) -> list:
        """Corresponds to MBusinoLib::decodeRecords() in MBusinoLib.cpp.

        Splits the payload area of a telegram into individual records.

        :param buffer: bytes starting at the first DIF (offset 0x13 for telegrams)
        :param size: number of bytes to read - exactly like the C++ parameter
                     ``uint8_t size``. ``test_decode.cpp`` passes
                     ``packet_size - 0x13 - 2`` (i.e. WITHOUT checksum and
                     stop byte even though ``buffer`` is 2 bytes longer).
                     ``None`` (default) means ``len(buffer)``.
        :return: list of records - identical to the C++ ``JsonArray``, every
                 entry has the keys
                 ``vif``, ``code``, ``value_scaled``, ``value_string``,
                 ``units``, ``name`` and optionally ``subUnit``, ``storage``,
                 ``tariff``, ``telegramFollow``.
                 NOTE: on error the C++ return value would be 0, but the
                 JsonArray already holds records decoded so far - Python
                 returns those (the error is reported by ``get_error()``).
        """
        data = bytes(buffer)
        buf_len = len(data)
        if size is None:
            size = buf_len

        records: list = []
        index = 0

        def rd(pos: int) -> int:
            """Read one byte like ``buffer[pos]`` in C++ - there WITHOUT a check.

            Every access that would run past the end in the original (UB)
            goes through this function and raises
            ``_OutOfBounds`` -> ``BUFFER_OVERFLOW``.
            """
            if 0 <= pos < buf_len:
                return data[pos]
            raise _OutOfBounds(pos)

        try:
            # `while (index < size)` in decodeRecords()
            while index < size:
                # ------------------------------------------------------------ #
                # decode the DIF (decodeRecords())
                # ------------------------------------------------------------ #
                dif = rd(index)          # C++: uint8_t dif = buffer[index++];
                index += 1
                dif_least4bit = dif & 0x0F
                dif_function_field = (dif & 0x30) >> 4

                # switch(difLeast4bit) in decodeRecords():
                # -> (length in bytes, data coding type)
                #   0 = no data, 1 = integer, 2 = BCD, 3 = real (float32),
                #   4 = variable length, 5 = special function,
                #   6 = date+time type F, 7 = date type G
                #   (6/7 are applied further down via the VIF)
                #
                # C++ table (DIF comment in decodeRecords()): DIF bits 0..3 = length/coding,
                # bits 4..5 = function (0=current,1=_max,2=_min,3=_err)
                length, data_coding_type = _DIF_TABLE[dif_least4bit]

                # append the function field - switch(difFunctionField) in decodeRecords()
                function_field = _FUNCTION_FIELDS[dif_function_field]

                # ------------------------------------------------------------ #
                # handle the DIFEs (decodeRecords())
                # ------------------------------------------------------------ #
                # bit 6 of the DIF pre-sets "storage 1"
                storage_number = 1 if (dif & 0x40) == 0x40 else 0
                dife_number = 0
                # C++: uint8_t dife[10] = {0};  (index 0 stays unused,
                # the DIFEs start at index 1 - therefore 11 slots here, so
                # the C++ access dife[difeNumber+1] at the end of the DIFE loop
                # of the loop hits the value 0 instead of running past the array)
                dife = [0] * 11
                if_dife = (dif & 0x80) == 0x80  # Bit 7 = "eine DIFE folgt"
                while if_dife:
                    dife_number += 1
                    if dife_number > 9:
                        # C++ writes past dife[10] here (UB)
                        raise _OutOfBounds(dife_number)
                    dife[dife_number] = rd(index)      # C++: dife[difeNumber] = buffer[index];
                    if_dife = (rd(index) & 0x80) == 0x80  # weitere DIFE?
                    index += 1

                # evaluate the DIFEs (decodeRecords())
                sub_unit = 0
                tariff = 0
                i = 0
                # C++: for(uint8_t i=0; difeNumber>0 && i<=difeNumber; i++)
                while dife_number > 0 and i <= dife_number:
                    if i == 0:
                        storage_number |= (dife[i + 1] & 0x0F) << 1
                    else:
                        storage_number |= (dife[i + 1] & 0x0F) << (4 * i)
                    sub_unit |= (((dife[i + 1] & 0x40) >> 6) << i)
                    tariff |= (((dife[i + 1] & 0x30) >> 4) << (2 * i))
                    i += 1

                # end of DIFE handling (C++ comment "// End of DIFE handling")

                # ------------------------------------------------------------ #
                # fetch the VIF(E) (decodeRecords())
                # ------------------------------------------------------------ #
                vif = 0
                vifarray = [0] * 10          # C++: uint8_t vifarray[10] = {0};
                vifcounter = 0
                custom_vif_len = 0           # C++: uint8_t customVIFlen = 0;
                custom_vif = ""              # C++: char customVIF[20] = {0};
                if_custom_vif = False        # C++: bool ifcustomVIF = false;

                while True:
                    if index == size:
                        # C++: explicit BUFFER_OVERFLOW when index == size
                        self._error = MBUS_ERROR.BUFFER_OVERFLOW
                        return records
                    if vifcounter > 9:
                        # C++ reads past vifarray[10] here (UB)
                        raise _OutOfBounds(vifcounter)
                    vifarray[vifcounter] = rd(index)   # C++: vifarray[vifcounter] = buffer[index++];
                    index += 1

                    if (vifarray[0] & 0x7F) == 0x7C and vifcounter == 0:
                        # Customized ASCII VIF (in decodeRecords()):
                        # the next byte is the length of the ASCII string
                        custom_vif_len = rd(index)
                        if vifarray[0] == 0xFC:
                            # for a 0xFC VIF skip the ASCII string in order
                            # to reach the VIFE(s) behind it
                            index = index + custom_vif_len + 1

                    if vifcounter < 2:
                        # normally VIF + first VIFE are enough (C++: if(vifcounter < 2))
                        vif = (vif << 8) + vifarray[vifcounter]
                    elif vifcounter == 2 and vif == 0xFDFD:
                        # ... unless VIF 0xFDFD needs the third byte (C++: vifcounter == 2 && vif == 0xFDFD)
                        vif = (vif << 8) + vifarray[vifcounter]

                    vifcounter += 1
                    # stop as soon as bit 7 of the last byte read is missing
                    if (vifarray[vifcounter - 1] & 0x80) != 0x80:
                        break

                # ------------------------------------------------------------ #
                # fine-tune the VIF (decodeRecords())
                # ------------------------------------------------------------ #
                # When the top bit is set in the FIRST byte and it is none of
                # the "extension marker bytes" 0xFD/0xFC/0xFB/0xFF, the real
                # VIF sits in this byte alone (mask the extension bit away).
                if (
                    (vifarray[0] & 0x80) == 0x80
                    and vifarray[0] != 0xFD
                    and vifarray[0] != 0xFC
                    and vifarray[0] != 0xFB
                    and vifarray[0] != 0xFF
                ):
                    vif = vifarray[0] & 0x7F

                if vifarray[0] == 0x7C:
                    vif = 0x7C00   # C++: if(vifarray[0] == 0x7C) vif = 0x7C00;

                # 0x6D = date+time type F, 0x6C = date type G -> overwrite
                # the coding independently of the DIF (the C++ sets dataCodingType from the VIF here)
                if (vif & 0x7F) == 0x6D:
                    data_coding_type = 6
                elif (vif & 0x7F) == 0x6C:
                    data_coding_type = 7
                elif (vif & 0x7F00) == 0x7C00:
                    # Customized ASCII VIF: actually read the string now
                    # (C++: customized ASCII VIF block in decodeRecords())
                    vif = 0xFC00
                    if vifarray[0] == 0xFC:
                        # for 0xFC the string was already skipped above,
                        # therefore rewind the pointer
                        index = index - custom_vif_len - 1
                    # C++: char vifBuffer[customVIFlen + 1]; (uninitialised!)
                    vif_buffer = [0] * (custom_vif_len + 1)
                    for i in range(custom_vif_len + 1):
                        # C++: vifBuffer[customVIFlen-i] = buffer[index - vifcounter + 1];
                        # The read start shifts by -vifcounter because index
                        # is further ahead in the 0xFC case (past the VIFE(s)) -
                        # at the end the pointer is exactly on the length byte.
                        vif_buffer[custom_vif_len - i] = rd(index - vifcounter + 1)
                        index += 1
                    # C++: strncpy(customVIF, vifBuffer, customVIFlen);
                    # vifBuffer[customVIFlen] holds the length byte and
                    # stays unused; the characters are stored reversed
                    # (M-Bus sends ASCII backwards) and are flipped back into
                    # reading order here.
                    # char customVIF[20] -> at most 19 characters + NUL.
                    # (C++ would run past the buffer for longer strings)
                    custom_vif = bytes(vif_buffer[:custom_vif_len]).decode(
                        "latin-1", errors="replace"
                    )[:19]
                    if_custom_vif = True

                # clear bit 7 of the last VIF byte (C++: vif &= 0xFFFFFF7F), otherwise
                # _findDefinition() finds no match
                vif = vif & 0xFFFFFF7F

                # ------------------------------------------------------------ #
                # look up the definition - _findDefinition() in the C++ original
                # ------------------------------------------------------------ #
                def_index = self._find_definition(vif)
                if def_index < 0:
                    # C++ sets the error and then CONTINUES with entry 0
                    # (UNKNOWN_VIF) - the "return 0" line is commented out
                    # there. Python behaves exactly the same way.
                    self._error = MBUS_ERROR.UNSUPPORTED_VIF
                    def_index = 0

                # ------------------------------------------------------------ #
                # VIFE extensions (decodeRecords())
                # ------------------------------------------------------------ #
                extension_scaler = 0                # C++: int8_t extensionScaler
                extension_additive_constant = 0.0   # C++: double extensionAdditiveConstant
                name_extension = ""                 # C++: char stringNameExtension[10]
                no_unit = False                     # C++: bool noUnit

                if vifcounter - 1 > 0:  # at least one VIFE present
                    if (
                        vifarray[0] == 0xFB
                        or (vifarray[0] == 0xFD and vifarray[1] != 0xFD)
                        or vifarray[0] == 0xFF
                    ):
                        first_vife_extension = 2
                    elif vifarray[0] == 0xFD and vifarray[1] == 0xFD:
                        first_vife_extension = 3
                    else:
                        first_vife_extension = 1

                    extensions_counter = first_vife_extension
                    # C++: do { ... } while(extensionsCounter <= vifcounter);
                    while True:
                        if extensions_counter > 9:
                            # C++ reads past vifarray[10] here (UB)
                            raise _OutOfBounds(extensions_counter)
                        byte = vifarray[extensions_counter]

                        if (byte & 0x7F) == 0x7D:
                            # E111 1101: multiplicative correction factor 1000
                            extension_scaler = 3
                        elif (byte & 0x78) == 0x70:
                            # E111 0nnn: multiplicative factor 10^(nnn-6)
                            extension_scaler = (byte & 0x07) - 6
                        elif (byte & 0x7C) == 0x78:
                            # E111 10nn: additive correction constant 10^(nn-3)
                            additive_scaler = (byte & 0x03) - 3
                            extension_additive_constant = 1.0
                            for _ in range(additive_scaler):
                                extension_additive_constant *= 10.0
                            for _ in range(-additive_scaler if additive_scaler < 0 else 0):
                                extension_additive_constant /= 10.0
                        elif (byte & 0x7A) == 0x6A:
                            # E110 1f1b: date/time - adapt the coding
                            if dif_least4bit == 4:
                                data_coding_type = 6
                            elif dif_least4bit == 2:
                                data_coding_type = 7
                            name_extension = "_TimeSt"
                            no_unit = True
                        elif byte == 0xFC or byte == 0xFF:
                            # "reading user" extension: the NEXT byte
                            # selects phase/reference (C++: switch(vifExtensionBuffer))
                            if extensions_counter + 1 > 9:
                                raise _OutOfBounds(extensions_counter + 1)
                            extension_buffer = vifarray[extensions_counter + 1] & 0x7F
                            suffix = _PHASE_SUFFIX.get(extension_buffer)
                            if suffix is not None:
                                name_extension = suffix
                                extensions_counter += 1  # C++ skips over that byte
                        extensions_counter += 1
                        if extensions_counter > vifcounter:
                            break

                # ------------------------------------------------------------ #
                # buffer overflow check (decodeRecords())
                # ------------------------------------------------------------ #
                if index + length > size or index + length > buf_len:
                    self._error = MBUS_ERROR.BUFFER_OVERFLOW
                    return records

                # ------------------------------------------------------------ #
                # read the value (decodeRecords())
                # ------------------------------------------------------------ #
                value16 = 0            # C++: int16_t value16 - notices negative 2-byte values
                value32 = 0            # C++: int32_t value32 - notices negative 4-byte values
                value = 0              # C++: int64_t value
                value_float = 0.0      # C++: float valueFloat (a real 32-bit number!)
                date = b""             # C++: uint8_t date[len]
                datestring = ""        # C++: char datestring[16]
                datestring2 = ""       # C++: char datestring2[30]
                value_string = ""      # C++: char valueString[30]
                switch_again = False   # C++: bool switchAgain
                negative = False       # C++: bool negative
                ascii_value = 0        # C++: uint8_t asciiValue (0=double, 1=ASCII, 2=both)

                # C++: do { switch(dataCodingType) ... } while(switchAgain);
                while True:
                    switch_again = False

                    if data_coding_type == 0:
                        # case 0: no data, value stays 0 (C++: case 0)
                        pass

                    elif data_coding_type == 1:
                        # case 1: integer, LITTLE-ENDIAN (C++: case 1)
                        # (the loop builds the byte at index len-i-1 into the
                        # most significant byte - M-Bus sends LSB first)
                        if length == 2:
                            value16 = 0
                            for i in range(length):
                                value16 = (value16 << 8) + rd(index + length - i - 1)
                            value = _to_int16(value16)   # C++: (int64_t)value16
                        elif length == 4:
                            value32 = 0
                            for i in range(length):
                                value32 = (value32 << 8) + rd(index + length - i - 1)
                            value = _to_int32(value32)   # C++: (int64_t)value32
                        else:
                            value = 0
                            for i in range(length):
                                value = (value << 8) + rd(index + length - i - 1)

                    elif data_coding_type == 2:
                        # case 2: BCD, 2 digits per byte (C++: case 2)
                        if length == 2:
                            value16 = 0
                        elif length == 4:
                            value32 = 0
                        else:
                            value = 0
                        for i in range(length):
                            byte = rd(index + length - i - 1)
                            if i == 0 and (byte & 0xF0) == 0xF0:
                                # Only unsigned BCD is intended, but some
                                # manufacturers put an F into the top half
                                # byte as a "negative" marker.
                                # QUIRK of the original: the tens digit of
                                # that byte is lost as well
                                # (the byte is reduced to 0x0F).
                                byte = byte & 0x0F
                                negative = True
                            if length == 2:
                                value16 = value16 * 100 + ((byte >> 4) * 10) + (byte & 0x0F)
                            elif length == 4:
                                value32 = value32 * 100 + ((byte >> 4) * 10) + (byte & 0x0F)
                            else:
                                value = value * 100 + ((byte >> 4) * 10) + (byte & 0x0F)
                        if length == 2:
                            value = _to_int16(value16)
                        elif length == 4:
                            value = _to_int32(value32)
                        if negative:
                            # C++: only BCD has the negative case
                            value = value * -1

                    elif data_coding_type == 3:
                        # case 3: real = IEEE-754 32 bit (C++: case 3)
                        value = 0
                        for i in range(length):
                            value = (value << 8) + rd(index + length - i - 1)
                        # C++: memcpy(&valueFloat, &value, sizeof(valueFloat))
                        # -> the LOW 4 bytes of value are read as float
                        # (same byte order as above).
                        value_float = struct.unpack(
                            "<f", struct.pack("<I", value & 0xFFFFFFFF)
                        )[0]

                    elif data_coding_type == 4:
                        # case 4: variable length, LVAR (C++: case 4)
                        #   00..BFh ASCII, C0..CFh positive BCD,
                        #   D0..DFh negative BCD, E0..EFh bytes as integer,
                        #   F0..FAh bytes as float, FB..FFh reserved
                        lvar = rd(index)
                        if lvar <= 0xBF:
                            # ASCII string with LVAR characters (C++: LVAR 0x00-0xBF)
                            length = lvar
                            index += 1
                            char_buffer = [0] * (length + 1)
                            for i in range(length + 1):
                                # characters arrive reversed like in the original:
                                # this restores reading order
                                char_buffer[i] = rd(index + (length - i - 1))
                            # C++: strncpy(valueString, charBuffer, len);
                            # char valueString[30] -> at most 29 characters
                            value_string = bytes(char_buffer[:length]).decode(
                                "latin-1", errors="replace"
                            )[:29]
                            ascii_value = 1
                        elif 0xC0 <= lvar <= 0xCF:
                            # positive BCD, (LVAR - C0h) bytes (C++: LVAR 0xC0-0xCF)
                            length = lvar - 0xC0
                            index += 1
                            data_coding_type = 2
                            switch_again = True
                        elif 0xD0 <= lvar <= 0xDF:
                            # negative BCD (C++: LVAR 0xD0-0xDF)
                            length = lvar - 0xD0
                            index += 1
                            data_coding_type = 2
                            switch_again = True
                            negative = True
                        elif 0xE0 <= lvar <= 0xEF:
                            # binary number, (LVAR - E0h) bytes (C++: LVAR 0xE0-0xEF)
                            length = lvar - 0xE0
                            index += 1
                            data_coding_type = 1
                            switch_again = True
                        elif 0xF0 <= lvar <= 0xFA:
                            # floating point, (LVAR - F0h) bytes (C++: LVAR 0xF0-0xFA)
                            length = lvar - 0xF0
                            index += 1
                            data_coding_type = 3
                            switch_again = True
                        # FB..FF reserved -> nothing happens, as in the original,
                        # length stays 0 and the next record follows

                    elif data_coding_type == 5:
                        # case 5: special function, nothing to do (C++: case 5)
                        pass

                    elif data_coding_type == 6:
                        # case 6: date+time type F, 4 bytes (C++: case 6)
                        date = data[index:index + length]
                        if len(date) < 4:
                            # C++ reads date[0..3] out of a too small VLA (UB)
                            raise _OutOfBounds(len(date))
                        if (date[0] & 0x80) == 0:
                            # bit 7 of the minutes byte = "time invalid" (C++ checks (date[0] & 0x80))
                            year = ((date[2] & 0xE0) >> 5) | ((date[3] & 0xF0) >> 1)
                            month = date[3] & 0x0F
                            mday = date[2] & 0x1F
                            hour = date[1] & 0x1F
                            minute = date[0] & 0x3F
                            # C++ snprintf("20%02d%02d%02d%02d%02d") - the
                            # formats produce exactly the same strings.
                            # (The buffer length of 24 given there for
                            # char[16] is a BUG, but it is never reached,
                            # because at most 13 characters are produced.)
                            datestring = "20%02d%02d%02d%02d%02d" % (
                                year, month, mday, hour, minute,
                            )
                            datestring2 = "20%02d-%02d-%02d %02d:%02d:00" % (
                                year, month, mday, hour, minute,
                            )
                            value = float(datestring)   # C++: atof(datestring)
                            value_string = datestring2
                            ascii_value = 2

                    elif data_coding_type == 7:
                        # case 7: date type G, 2 bytes (C++: case 7)
                        date = data[index:index + length]
                        if len(date) < 2:
                            raise _OutOfBounds(len(date))
                        if (date[1] & 0x0F) <= 12:
                            # month > 12 = invalid (C++ checks (date[1] & 0x0F) > 12)
                            year = ((date[0] & 0xE0) >> 5) | ((date[1] & 0xF0) >> 1)
                            month = date[1] & 0x0F
                            mday = date[0] & 0x1F
                            datestring = "20%02d%02d%02d" % (year, month, mday)
                            datestring2 = "20%02d-%02d-%02d" % (year, month, mday)
                            value = float(datestring)   # C++: atof(datestring)
                            value_string = datestring2
                            ascii_value = 2

                    if not switch_again:
                        break

                # C++: index += len;
                index += length

                # ------------------------------------------------------------ #
                # scaling (decodeRecords())
                # ------------------------------------------------------------ #
                scaled = 0.0
                scalar = 0
                if def_index != 0:
                    # C++ (uint32_t arithmetic, result truncated
                    # to int8_t - see _to_int8):
                    #   scalar = vif_defs[def].scalar + vif - vif_defs[def].base + extensionScaler
                    _code, base, _size, def_scalar = VIF_DEFS[def_index]
                    scalar = _to_int8(def_scalar + vif - base + extension_scaler)

                if data_coding_type == 3:
                    # real floating point: only the VIF scaling value counts
                    scaled = value_float
                    if vifarray[0] != 0xFF:
                        # C++: first multiply by 10,
                        # then (when scalar is negative) divide by 10 and
                        # finally add the additive constant - the ORDER is
                        # exactly like the original so the result stays
                        # bit-identical (division and multiplication do not commute).
                        for _ in range(scalar if scalar > 0 else 0):
                            scaled *= 10.0
                        for _ in range(-scalar if scalar < 0 else 0):
                            scaled /= 10.0
                        scaled = scaled + extension_additive_constant
                elif vifarray[0] == 0xFF:
                    # manufacturer specific: do NOT scale, do NOT add
                    scaled = float(value)   # C++: scaled = value;
                else:
                    scaled = float(value)
                    for _ in range(scalar if scalar > 0 else 0):
                        scaled *= 10.0
                    for _ in range(-scalar if scalar < 0 else 0):
                        scaled /= 10.0
                    scaled = scaled + extension_additive_constant

                # ------------------------------------------------------------ #
                # build the record (decodeRecords())
                # ------------------------------------------------------------ #
                # The key order matches the C++ writing order exactly.
                record = {}
                # C++: String("0x" + String(vif,HEX)) -> lower-case
                # hex without leading zeros
                record["vif"] = "0x%x" % vif
                record["code"] = VIF_DEFS[def_index][0]

                if ascii_value != 1:
                    # C++: plain numeric value (not for ASCII)
                    record["value_scaled"] = scaled
                if ascii_value > 0:
                    # C++: formatted string (date/ASCII)
                    record["value_string"] = value_string

                if if_custom_vif:
                    # C++: unit comes from the ASCII VIF
                    record["units"] = custom_vif
                elif self.get_code_units(VIF_DEFS[def_index][0]) is not None and not no_unit:
                    # C++: unit from the lookup table;
                    # "noUnit" switches the unit off (e.g. for _TimeSt)
                    record["units"] = self.get_code_units(VIF_DEFS[def_index][0])

                record["name"] = (
                    self.get_code_name(VIF_DEFS[def_index][0]) + name_extension + function_field
                )

                if sub_unit > 0:
                    record["subUnit"] = sub_unit
                if storage_number > 0:
                    record["storage"] = storage_number
                if tariff > 0:
                    record["tariff"] = tariff

                records.append(record)

                # ------------------------------------------------------------ #
                # trailing markers (decodeRecords())
                # ------------------------------------------------------------ #
                # Check the byte that FOLLOWS the record. In C++ `index != size`
                # comes AFTER the read (so one byte is always read, even
                # when index is already at the end - with the usual
                # parameter that byte is the checksum).
                following = rd(index) if index < buf_len else None
                if following == 0x0F and index != size:
                    # 0x0F: manufacturer specific data starts here -> stop
                    break
                if following == 0x1F and index != size:
                    # 0x1F: the next telegram carries more records
                    record["telegramFollow"] = 1
                    break

        except _OutOfBounds:
            # Corresponds to the "return 0" spots of the original; there the
            # loop ends immediately, records already appended stay in the
            # JsonArray (and are returned here).
            self._error = MBUS_ERROR.BUFFER_OVERFLOW
            return records

        return records

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def decode_header(self, buffer, length: int = None) -> dict:
        """Corresponds to MBusinoLib::decodeHeader() in MBusinoLib.cpp.

        Decodes the fixed data header of a long frame telegram.

        :param buffer: the COMPLETE telegram including start/stop byte
        :param length: total length that may be read
                       (``None`` = ``len(buffer)``). The original expects
                       the ``packet_size`` (``data[1] + 6``) here - as in
                       ``decode_telegram()`` and in the examples - NOT the
                       file length.
        :return: dict with the ArduinoJson keys ``len``, ``c_field``,
                 ``address``, ``ci_field`` and - when CI is 0x72/0x76 - ``id``,
                 ``manufacturer``, ``version``, ``medium_code``, ``medium``,
                 ``access_counter``, ``status``, ``status_details`` (nested)
                 and ``signature``.
                 Mapping to the boolean C++ return value:
                 * ``{}``  -> C++ ``false`` before writing (too short,
                   wrong start byte or unequal length fields)
                 * dict without ``"id"`` -> C++ ``false`` AFTER writing
                   (CI is not 0x72/0x76, only the basic fields are present)
                 * dict with ``"id"`` -> C++ ``true``
        """
        data = bytes(buffer)
        if length is None:
            length = len(data)

        # 1. minimum length for a long frame with fixed data header (C++: if (length < 19))
        if length < 19 or len(data) < 19:
            return {}
        # 2. check the start bytes 68 ... 68 (C++: buffer[0] != 0x68 || buffer[3] != 0x68)
        if data[0] != 0x68 or data[3] != 0x68:
            return {}
        # 3. both length fields must be identical (C++)
        if data[1] != data[2]:
            return {}

        header = {
            "len": data[1],
            "c_field": data[4],
            "address": data[5],      # in decodeHeader() (the C++ README calls this "a_field"!)
            "ci_field": data[6],
        }

        # Only CI 0x72 (long/variable) and 0x76 (short/variable) carry the
        # fixed data header (C++: if (buffer[6] == 0x72 || buffer[6] == 0x76))
        if data[6] not in (0x72, 0x76):
            return header  # -> corresponds to `return false` after writing

        # 4. identification number, 4 byte BCD, LSB first (C++ decodeHeader() step 4)
        header["id"] = "%02X%02X%02X%02X" % (data[10], data[9], data[8], data[7])
        # 5. manufacturer, 2 byte, LSB first -> 3 letters of 5 bits each
        manuf_code = (data[12] << 8) | data[11]
        header["manufacturer"] = "".join(
            chr(((manuf_code >> shift) & 0x001F) + 64) for shift in (10, 5, 0)
        )
        # 6. version
        header["version"] = data[13]
        # 7. medium as code and as text
        medium = data[14]
        header["medium_code"] = medium
        header["medium"] = MEDIUM_NAMES.get(medium, "Unknown")
        # 8. transmission counter
        header["access_counter"] = data[15]
        # 9. status byte incl. bit breakdown
        status = data[16]
        header["status"] = status
        app_error = status & 0x03
        status_details = {
            "battery_low": bool(status & 0x04),
            "permanent_error": bool(status & 0x08),
            "temporary_error": bool(status & 0x10),
        }
        # QUIRK: 0x03 (reserved) gets NO app_status key at all in the original
        if app_error == 0x00:
            status_details["app_status"] = "no_error"
        elif app_error == 0x01:
            status_details["app_status"] = "busy"
        elif app_error == 0x02:
            status_details["app_status"] = "any_error"
        header["status_details"] = status_details
        # 10. signature, 2 byte, LSB first
        header["signature"] = (data[18] << 8) | data[17]

        return header

    # ------------------------------------------------------------------
    # NEW: complete telegram
    # ------------------------------------------------------------------
    def decode_telegram(self, raw) -> dict:
        """NEW (not in C++): splits a complete M-Bus telegram apart.

        Frame rules like ``test_decode.cpp``:

        * layout ``68 LL LL 68 C A CI ... CHK 16``
        * ``packet_size = data[1] + 6`` (test_decode.cpp main(): 4 bytes
          start/length + L payload + checksum + stop byte)
        * records start at offset ``0x13`` (test_decode.cpp main() start_address:
          "Standard: skip header + fixed data header")
        * record length ``packet_size - 0x13 - 2`` (test_decode.cpp main() data_len:
          the 2 are checksum and stop byte)

        :param raw: telegram as ``bytes``/``bytearray``/list of values or
                    as hex string ("68 56 56 68 ...", commas and "0x" prefixes
                    are allowed - see ``_parse_hex``)
        :return:::

            {
              "frame": {...},          # frame checks, see below
              "header": {...},         # result of decode_header()
              "records": [...],        # result of decode_records()
              "error": <int>,          # MBUS_ERROR code of the decoding step
              "error_message": <str>   # English message for the first problem found
            }

        ``frame`` contains ``byte_count``, ``packet_size``, ``slave_address``,
        ``c_field``, ``ci_field``, ``start_ok``, ``length_ok``, ``fits``,
        ``stop_ok``, ``checksum``, ``checksum_received``, ``checksum_ok``,
        ``quartet_checksum_ok``, ``ok`` and ``error_message``.

        Error logic: ``error`` carries the MBUS_ERROR code (the enum has no
        frame error code of its own; only "length does not fit" is reported
        as ``BUFFER_OVERFLOW``, because test_decode.cpp also aborts on that
        case with "declared length ... but only N bytes provided").
        ``error_message`` always names the first problem found - when only
        the checksum is wrong, ``error`` stays 0 but the message still
        describes the problem and ``frame["ok"]`` is ``False``.

        Example - a minimal valid telegram, i.e. the smallest possible frame
        ``68 0F 0F 68 | 08 00 72 | 12 header bytes | CHK 16`` (EFE heat meter
        header, fixed header only, no records, checksum 0xC8 = byte sum)::

            >>> hex_str = "68 0F 0F 68 08 00 72 09 34 75 73 C5 14 00 0D 43 00 00 00 C8 16"
            >>> MBusinoLib().decode_telegram(hex_str)["frame"]["ok"]
            True
        """
        data = bytes(raw) if not isinstance(raw, str) else _parse_hex(raw)
        # Clear the error before every new message - in C++ getError()
        # empties the state after reading, here we deliver it directly.
        self._error = MBUS_ERROR.NO_ERROR

        # --- initial values for the frame checks ---------------------
        byte_count = len(data)
        too_short = byte_count < 6      # test_decode.cpp main(): "telegram too short" check
        packet_size = None
        start_ok = False
        length_ok = False
        fits = False
        stop_ok = False
        checksum = None
        checksum_received = None
        checksum_ok = False
        quartet_checksum_ok = False
        frame_error = ""
        error = MBUS_ERROR.NO_ERROR
        header: dict = {}
        records: list = []

        if too_short:
            frame_error = "Telegram too short: %d bytes, at least 6 required." % byte_count
            error = MBUS_ERROR.BUFFER_OVERFLOW
        else:
            # packet size: 68 | LL | LL | 68 | C | A | CI | data | CHK | 16
            #   -> 4 header bytes + LL bytes (C up to end of data) + CHK + 16
            packet_size = data[1] + 6          # test_decode.cpp main(): frame size
            start_ok = data[0] == 0x68 and data[3] == 0x68  # test_decode does NOT check this
            length_ok = data[1] == data[2]     # both length fields identical
            fits = packet_size <= byte_count    # test_decode.cpp main(): truncation guard
            if fits:
                # checksum: byte in front of the stop byte
                #   C++/EN 13757: plain byte sum from the C field (offset 4)
                #   up to the last data byte (offset packet_size-3)
                checksum = sum(data[4:packet_size - 2]) & 0xFF
                checksum_received = data[packet_size - 2]
                checksum_ok = checksum_received == checksum
                # quartet sum (sum of all half bytes) - used by some
                # implementations, accepted here as an alternative
                quartet = 0
                for byte in data[4:packet_size - 2]:
                    quartet += (byte & 0x0F) + (byte >> 4)
                quartet_checksum_ok = checksum_received == (quartet & 0xFF)
                stop_ok = data[packet_size - 1] == 0x16

            # --- name the first problem --------------------------------
            if not start_ok:
                frame_error = "Unexpected start byte: 0x%02X/0x%02X instead of 0x68/0x68." % (data[0], data[3])
            elif not length_ok:
                frame_error = "Length fields differ: L1=0x%02X, L2=0x%02X." % (data[1], data[2])
            elif not fits:
                frame_error = ("Declared length %d expects %d bytes, "
                               "but only %d bytes present." % (data[1], packet_size, byte_count))
                error = MBUS_ERROR.BUFFER_OVERFLOW
            elif not stop_ok:
                frame_error = "Stop byte missing: 0x%02X instead of 0x16." % data[packet_size - 1]
            elif not checksum_ok and not quartet_checksum_ok:
                frame_error = ("Checksum mismatch: expected 0x%02X, "
                               "received 0x%02X." % (checksum, checksum_received))

            # --- decode (like test_decode.cpp, independent of -----------
            #     start byte/checksum - the original does not check those) ----
            if fits:
                header = self.decode_header(data, packet_size)          # C++ decodeHeader()
                # data from offset 0x13, without checksum(1) and stop byte(1)
                start_address = 0x13                                     # test_decode.cpp main(): skip header + fixed data
                data_len = max(0, packet_size - start_address - 2)       # test_decode.cpp main(): records length
                records = self.decode_records(data[start_address:packet_size], data_len)
                error = self._error

        if isinstance(error, IntEnum):
            error = int(error)

        # Error message: the text of an MBUS_ERROR if there is one, otherwise
        # the frame hint - "No error" only when everything really fitted.
        if error != MBUS_ERROR.NO_ERROR:
            error_message = self.get_error_message(error)
        elif frame_error:
            error_message = frame_error
        else:
            error_message = "No error"

        frame = {
            "byte_count": byte_count,
            "packet_size": packet_size,
            "slave_address": data[5] if not too_short else None,
            "c_field": data[4] if not too_short else None,
            "ci_field": data[6] if not too_short else None,
            "start_ok": start_ok,
            "length_ok": length_ok,
            "fits": fits,
            "stop_ok": stop_ok,
            "checksum": checksum,
            "checksum_received": checksum_received,
            "checksum_ok": checksum_ok,
            "quartet_checksum_ok": quartet_checksum_ok,
            "ok": (not too_short) and start_ok and length_ok and fits and stop_ok
                  and (checksum_ok or quartet_checksum_ok),
            "error_message": frame_error,
        }

        return {
            "frame": frame,
            "header": header,
            "records": records,
            "error": error,
            "error_message": error_message,
        }


# ---------------------------------------------------------------------------
# DIF table (C++: switch(difLeast4bit) in decodeRecords())
# index = low 4 bits of the DIF, value = (length in bytes, data coding type)
#   type: 0 = no data, 1 = integer, 2 = BCD, 3 = real,
#         4 = variable, 5 = special function
# ---------------------------------------------------------------------------
_DIF_TABLE = (
    (0, 0),   # 0x00 -> No data           
    (1, 1),   # 0x01 -> 8 Bit Integer     
    (2, 1),   # 0x02 -> 16 Bit Integer    
    (3, 1),   # 0x03 -> 24 Bit Integer    
    (4, 1),   # 0x04 -> 32 Bit Integer    
    (4, 3),   # 0x05 -> 32 Bit Real       
    (6, 1),   # 0x06 -> 48 Bit Integer    
    (8, 1),   # 0x07 -> 64 Bit Integer    
    (0, 0),   # 0x08 -> Selection for Readout, not supported
    (1, 2),   # 0x09 -> 2 digit BCD       
    (2, 2),   # 0x0A -> 4 digit BCD       
    (3, 2),   # 0x0B -> 6 digit BCD       
    (4, 2),   # 0x0C -> 8 digit BCD       
    (0, 4),   # 0x0D -> variable length   
    (6, 2),   # 0x0E -> 12 digit BCD      
    (0, 5),   # 0x0F -> Special Functions 
)

# Function field (C++: switch(difFunctionField) in decodeRecords())
# bits 4+5 of the DIF: 0=current, 1=_max, 2=_min, 3=_err
_FUNCTION_FIELDS = ("", "_max", "_min", "_err")

# Name suffixes for the "reading user" VIFE 0xFC/0xFF
# (C++: switch(vifExtensionBuffer) in decodeRecords())
_PHASE_SUFFIX = {
    1: "_L1",
    2: "_L2",
    3: "_L3",
    4: "_N",
    5: "_L1-L2",
    6: "_L2-L3",
    7: "_L3-L1",
    10: "_abs.",
    12: "_delta",
}
