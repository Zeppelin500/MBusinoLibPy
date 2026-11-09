# -*- coding: utf-8 -*-
"""MBusinoLibPy - Python port of the Arduino library **MBusinoLib**.

This library decodes M-Bus (Meterbus) RSP_UD telegrams - the answer a
slave sends to the master - entirely in pure Python
(standard library only, no runtime dependencies).

The port follows the C++ original ``MBusinoLib`` (version 0.10.0, GPL-3.0)
function by function; every Python function refers in its comment to
the corresponding C++ function including the line number.

Schnellstart::

    from MBusinoLibPy import MBusinoLib

    telegram = bytes.fromhex(
        "68 C1 C1 68 08 00 72 09 34 75 73 C5 14 00 0D 43 00 00 00"
        "04 78 41 63 65 04 04 06 AA 29 00 00 ... 75 16"
    )
    decode = MBusinoLib()
    result = decode.decode_telegram(telegram)
    print(result["header"]["manufacturer"], result["records"][0])

All public names:

* ``MBusinoLib`` - the decoder class
* ``MBUS_CODE`` - enum of the supported record codes (identical to C++)
* ``MBUS_ERROR`` - enum of the error codes (identical to C++)
* ``VIF_DEFS`` / ``MBUS_VIF_DEF_NUM`` - the VIF definition table
* ``CODE_NAME`` / ``CODE_UNITS`` / ``DEVICE_CLASS`` / ``STATE_CLASS`` /
  ``MEDIUM_NAMES`` - the four lookup tables from the C++ original
"""

from .enums import (
    ARDUINO_FLOAT_DECIMALS,
    ARDUINO_FLOAT_MIN,
    MBUS_DEFAULT_BUFFER_SIZE,
    MBUS_CODE,
    MBUS_ERROR,
)
from .lookup_tables import (
    CODE_NAME,
    CODE_UNITS,
    DEVICE_CLASS,
    MEDIUM_NAMES,
    STATE_CLASS,
)
from .mbusino_lib import MBusinoLib
from .vif_defs import MBUS_VIF_DEF_NUM, VIF_DEFS

__version__ = "0.11.0"  # corresponds to the version of the C++ original (library.json)

__all__ = [
    "MBusinoLib",
    "MBUS_CODE",
    "MBUS_ERROR",
    "VIF_DEFS",
    "MBUS_VIF_DEF_NUM",
    "CODE_NAME",
    "CODE_UNITS",
    "DEVICE_CLASS",
    "STATE_CLASS",
    "MEDIUM_NAMES",
    "MBUS_DEFAULT_BUFFER_SIZE",
    "ARDUINO_FLOAT_MIN",
    "ARDUINO_FLOAT_DECIMALS",
    "__version__",
]
