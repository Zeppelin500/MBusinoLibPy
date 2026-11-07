# -*- coding: utf-8 -*-
"""MBusinoLibPy - Python-Port der Arduino-Bibliothek **MBusinoLib**.

Diese Bibliothek dekodiert M-Bus (Meterbus) RUP_UD-Telegramme - die Antwort
eines Slave auf die Anfrage des Master - vollständig in reinem Python
(Standardbibliothek, keine Laufzeit-Abhängigkeiten).

Der Port folgt dem C++-Original ``MBusinoLib`` (Version 0.10.0, GPL-3.0)
Funktion für Funktion; jede Python-Funktion verweist in ihrem Kommentar auf
die zugehörige C++-Funktion samt Zeilennummer.

Schnellstart::

    from MBusinoLibPy import MBusinoLib

    telegram = bytes.fromhex(
        "68 C1 C1 68 08 00 72 09 34 75 73 C5 14 00 0D 43 00 00 00"
        "04 78 41 63 65 04 04 06 AA 29 00 00 ... 75 16"
    )
    decode = MBusinoLib()
    result = decode.decode_telegram(telegram)
    print(result["header"]["manufacturer"], result["records"][0])

Alle öffentlichen Namen:

* ``MBusinoLib`` - die Dekodiererklasse
* ``MBUS_CODE`` - Enum der unterstützten Datensatz-Codes (identisch zu C++)
* ``MBUS_ERROR`` - Enum der Fehlercodes (identisch zu C++)
* ``VIF_DEFS`` / ``MBUS_VIF_DEF_NUM`` - die VIF-Definitionstabelle
* ``CODE_NAME`` / ``CODE_UNITS`` / ``DEVICE_CLASS`` / ``STATE_CLASS`` /
  ``MEDIUM_NAMES`` - die vier Nachschlagetabellen aus dem C++-Original
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

__version__ = "0.10.0"  # entspricht der Version des C++-Originals (library.json)

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
