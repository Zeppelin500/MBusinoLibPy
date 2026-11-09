# -*- coding: utf-8 -*-
"""Tests for error handling: ``get_error()`` and ``get_error_message()``.

``get_error()`` behaves exactly like MBusinoLib::getError()
(MBusinoLib.cpp line 54-58): return AND clear back to NO_ERROR.
"""

import unittest

from MBusinoLibPy import MBUS_CODE, MBUS_ERROR, MBusinoLib


class TestGetError(unittest.TestCase):
    """C++: `uint8_t getError() { uint8_t error = _error; _error = NO_ERROR; return error; }`"""

    def test_initial_state_is_no_error(self):
        lib = MBusinoLib()
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))
        self.assertEqual(lib.get_error_message(), "No error.")

    def test_get_error_clears_the_error(self):
        """Returns it, afterwards the error is gone - calling twice = 4, then 0."""
        lib = MBusinoLib()
        lib.decode_records(bytes([0x07, 0x00, 0x11]))     # BUFFER_OVERFLOW
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))

    def test_error_does_not_clear_itself_by_decoding(self):
        """decodeRecords() does NOT clear the error (only getError() does)."""
        lib = MBusinoLib()
        lib.decode_records(bytes([0x07, 0x00, 0x11]))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))

    def test_error_message_does_not_clear(self):
        """get_error_message() only reads - therefore you can call it BEFORE
        get_error() and keep both pieces of information."""
        lib = MBusinoLib()
        lib.decode_records(bytes([0x01, 0x6E, 0x2A]))     # UNSUPPORTED_VIF
        nachricht = lib.get_error_message()
        self.assertIn("VIF", nachricht)
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.UNSUPPORTED_VIF))
        self.assertIn("VIF", nachricht)   # was not cleared

    def test_explicit_code_argument(self):
        """Every enum value has a readable English message."""
        lib = MBusinoLib()
        for code in MBUS_ERROR:
            with self.subTest(code=code.name):
                message = lib.get_error_message(code)
                self.assertTrue(message.strip())
                self.assertTrue(message.endswith("."), "message does not end with a period")
        # check the key contents without fixing the exact wording
        self.assertIn("No error", lib.get_error_message(MBUS_ERROR.NO_ERROR))
        self.assertIn("VIF", lib.get_error_message(MBUS_ERROR.UNSUPPORTED_VIF))
        self.assertIn("Buffer", lib.get_error_message(MBUS_ERROR.BUFFER_OVERFLOW))

    def test_return_type_is_plain_int(self):
        lib = MBusinoLib()
        value = lib.get_error()
        self.assertIsInstance(value, int)
        # comparisons with the enum still work (IntEnum)
        self.assertEqual(value, MBUS_ERROR.NO_ERROR)


class TestErrorPathsDuringDecode(unittest.TestCase):
    """Which errors can decoding actually set?"""

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
        lib.decode_records(bytes([0x04, 0x00, 0x01, 0x02]))  # 4 bytes expected, only 2 present
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))

    def test_buffer_overflow_when_vif_chain_never_ends(self):
        """Endless VIFE chain (all bytes with bit 7) -> BUFFER_OVERFLOW like in
        the original (C++ line 225-228: `if (index == size)`)."""
        lib = MBusinoLib()
        records = lib.decode_records(bytes([0x01, 0x81, 0x81, 0x81]))
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.BUFFER_OVERFLOW))
        self.assertEqual(records, [])

    def test_encoder_only_codes_are_never_set_while_decoding(self):
        """The encoder-only codes UNSUPPORTED_CODING (2), UNSUPPORTED_RANGE (3)
        and NEGATIVE_VALUE (5) were removed from the Python enum (OP-1) -
        the decoder never sets them either (the only error assignments in
        MBusinoLib.cpp live in decodeRecords(): BUFFER_OVERFLOW twice,
        UNSUPPORTED_VIF once)."""
        lib = MBusinoLib()
        # complete records with unusual codings ...
        lib.decode_records(bytes([0x05, 0x6D, 0x00, 0x00, 0x00, 0x00]))  # real + Datum Typ F
        lib.decode_records(bytes([0x0D, 0x00, 0x02, 0x41, 0x42]))        # variable length, ASCII (2 characters)
        # ... must not produce any error for the unusual codings
        self.assertEqual(lib.get_error(), int(MBUS_ERROR.NO_ERROR))

    def test_get_error_message_for_unknown_code(self):
        lib = MBusinoLib()
        self.assertIn("Unknown error code", lib.get_error_message(999))


class TestEnumMirroring(unittest.TestCase):
    """MBUS_ERROR keeps the C++ numbering for every code the decoder can set
    (the removed encoder leftovers leave deliberate gaps, OP-1)."""

    def test_error_codes_as_int(self):
        """Only the three codes the decoder can set - the gaps at 2, 3 and 5
        (removed encoder leftovers, OP-1) are deliberate."""
        self.assertEqual([int(c) for c in MBUS_ERROR], [0, 1, 4])
        self.assertEqual([c.name for c in MBUS_ERROR], [
            "NO_ERROR", "BUFFER_OVERFLOW", "UNSUPPORTED_VIF",
        ])
        # the removed encoder leftovers must be gone, the surviving codes
        # keep their original C++ values
        for removed in (2, 3, 5):
            self.assertNotIn(removed, [int(c) for c in MBUS_ERROR])

    def test_code_names_for_home_assistant_mapping(self):
        """The codes are the bridge to the Home Assistant tables."""
        self.assertEqual(MBUS_CODE.ENERGY_WH, 1)
        self.assertEqual(int(MBUS_CODE.VOLUME_M3), 3)


if __name__ == "__main__":
    unittest.main()
