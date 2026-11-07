# -*- coding: utf-8 -*-
"""Kernklasse ``MBusinoLib`` - 1:1-Port aus ``MBusinoLib.cpp`` (C++/Arduino).

Jede Methode nennt in ihrem Kommentar die zugehörige C++-Funktion samt
Zeilennummer in ``MBusinoLib/src/MBusinoLib.cpp``, damit man Funktion für
Funktion zwischen beiden Welten hin- und herwechseln kann.

Bewusste Abweichungen vom Original (Vorgabe 4 des Porting-Auftrags):

* Der interne Puffer samt ``reset()``/``getBuffer()``/``copy()``/``getSize()``
  entfällt komplett - die Python-API bekommt ``bytes``/``bytearray`` als
  Argument. Übrig bleibt nur ``_error`` analog zum C++-``_error``.
* ``get_error()`` verhält sich wie im C++: Rückgabe **und** Zurücksetzen
  auf ``NO_ERROR`` (MBusinoLib.cpp Zeile 54-58).
* Statt UB (Out-of-Bounds-Lesezugriffe im Original) bricht Python sauber ab
  und setzt ``BUFFER_OVERFLOW`` - die betroffenen Stellen sind einzeln
  kommentiert.

Alle Zahlen-Operationen laufen in der gleichen Reihenfolge und mit den
gleichen Typen wie im C++ (``int16_t``/``int32_t``-Überlauf, ``int8_t``-
Abschneiden des Scalars, 32-Bit-``float`` für "real"-Datensätze), damit die
Werte bit-identisch sind. Nur die *Ausgabe* von ArduinoJson rundet, deshalb
vergleichen die Golden-Tests ``value_scaled`` mit einer Toleranz
(relativ 1e-6 / absolut 1e-6, s. ``ARDUINO_FLOAT_DECIMALS = 6``).
"""

from __future__ import annotations

import struct
from enum import IntEnum  # noqa: F401  (nur für Typ-Verwendbarkeit importiert)

from .enums import (
    ARDUINO_FLOAT_DECIMALS,  # noqa: F401  (Dokumentationswert, s. enums.py)
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
# NEU (in MBusinoLib nicht vorhanden): lesbare deutsche Fehlermeldungen
# ---------------------------------------------------------------------------
# Zuordnung entspricht `enum MBUS_ERROR` aus MBusinoLib.h Zeile 185-192.
# UNSUPPORTED_CODING / UNSUPPORTED_RANGE / NEGATIVE_VALUE sind Überbleibsel
# des AllWize-Encoders - beim Dekodieren setzt das Original sie nie
# (Beleg: einzige Fehlerzuweisungen in MBusinoLib.cpp sind die Zeilen 226,
# 283 und 382), sie stehen hier trotzdem vollständig im Dict.
_ERROR_MESSAGES = {
    MBUS_ERROR.NO_ERROR: "Kein Fehler.",
    MBUS_ERROR.BUFFER_OVERFLOW: (
        "Puffer zu klein oder Telegramm unvollständig: Die deklarierte Länge "
        "passt nicht in die übergebenen Daten, oder ein Datensatz würde uber "
        "das Ende des Puffers hinaus."
    ),
    MBUS_ERROR.UNSUPPORTED_CODING: (
        "Nicht unterstützte Datenkodierung (DIF-Kodierung)."
    ),
    MBUS_ERROR.UNSUPPORTED_RANGE: (
        "Nicht unterstützter Wertebereich: Kombination aus Code und Skalierung "
        "nicht darstellbar."
    ),
    MBUS_ERROR.UNSUPPORTED_VIF: (
        "Unbekannter oder nicht unterstützter VIF - der Datensatz könnte keiner "
        "Definition aus vif_defs zugeordnet werden."
    ),
    MBUS_ERROR.NEGATIVE_VALUE: (
        "Negativer Wert, der vom Original nicht unterstützt wird."
    ),
}


# ---------------------------------------------------------------------------
# Kleine Helfer für die C++-Typsemantik
# ---------------------------------------------------------------------------
class _OutOfBounds(Exception):
    """Intern: Lesezugriff außerhalb des echten Puffers (im C++ würde das UB)."""


def _to_int8(value: int) -> int:
    """C++: Zuweisung eines Ausdrucks (uint32_t-Arithmetik) auf ``int8_t``.

    GCC/Clang schneiden auf die niederwertigen 8 Bit ab und deuten sie als
    zweierkomplementär (in C++20 definiert, davor implementation-definiert).
    ``2**32`` ist ein Vielfaches von 256, deshalb reicht hier das Abschneiden
    auf 8 Bit - auch für negative Python-Zwischenwerte (``-3 & 0xFF == 0xFD``).
    """
    low = value & 0xFF
    return low - 0x100 if low & 0x80 else low


def _to_int16(value: int) -> int:
    """C++: ``value = (int64_t)value16;`` mit ``int16_t value16`` (Vorzeichen-Erweiterung)."""
    low = value & 0xFFFF
    return low - 0x10000 if low & 0x8000 else low


def _to_int32(value: int) -> int:
    """C++: ``value = (int64_t)value32;`` mit ``int32_t value32`` (Vorzeichen-Erweiterung)."""
    low = value & 0xFFFFFFFF
    return low - 0x100000000 if low & 0x80000000 else low


def _parse_hex(text: str):
    """Entspricht ``parseHex()`` in test_decode.cpp Zeile 10-22.

    Zerlegt "68 56 56 68 ..."/"0x68,0x56,..."-Eingaben in eine Bytefolge.
    Komfortfunktion für ``decode_telegram("68 56 ...")`` - das Original liest
    die Eingabe nur aus argv/stdin, hier darf man sie direkt als Text geben.
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
# Die Klasse
# ---------------------------------------------------------------------------
class MBusinoLib:
    """Dekodierer für M-Bus-RUP_UD-Telegramme - Entsprechung zur C++-Klasse.

    C++: ``class MBusinoLib`` in MBusinoLib.h Zeile 369-399.

    Beispiel::

        decode = MBusinoLib()
        records = decode.decode_records(telegram[0x13:packet_size],
                                        packet_size - 0x13 - 2)
        print(decode.get_error())
    """

    # __init__ entspricht MBusinoLib::MBusinoLib() in MBusinoLib.cpp Zeile 27-31.
    # Dort wird nur der Arbeitspuffer alloziiert und _cursor/_error gesetzt;
    # den Puffer gibt es in Python nicht (Vorgabe 4), _error startet wie im
    # C++ bei NO_ERROR (MBusinoLib.h Zeile 398: ``uint8_t _error = NO_ERROR;``).
    def __init__(self) -> None:
        self._error: IntEnum = MBUS_ERROR.NO_ERROR

    # ------------------------------------------------------------------
    # Fehler
    # ------------------------------------------------------------------
    def get_error(self) -> int:
        """Entspricht MBusinoLib::getError() in MBusinoLib.cpp Zeile 54-58.

        Wie im Original: gibt den Fehlercode zurück UND setzt den internen
        Fehler sofort wieder auf ``NO_ERROR`` zurück. Wer den Fehler behalten
        will, liest ``decode._error`` oder ruft ``get_error_message()`` VORHER auf.
        """
        error = self._error
        self._error = MBUS_ERROR.NO_ERROR
        return int(error)

    def get_error_message(self, code: int = None) -> str:
        """NEU (im C++ nicht vorhanden): lesbare deutsche Fehlermeldung.

        Ohne Argument meldet die Methode den zuletzt gespeicherten Fehler -
        im Gegensatz zu ``get_error()`` wird dabei NICHTs zurückgesetzt, man
        kann also erst ``get_error_message()`` und danach ``get_error()`` lesen.

        :param code: optional ein MBUS_ERROR-Wert statt des internen Standes
        """
        if code is None:
            code = self._error
        try:
            return _ERROR_MESSAGES.get(MBUS_ERROR(code), "Unbekannter Fehlercode %s." % code)
        except ValueError:
            # Wert außerhalb des Enums (z.B. ein Rohtext-/Fehlerwert von anderswo)
            return "Unbekannter Fehlercode %s." % code

    # ------------------------------------------------------------------
    # Nachschlagetabellen (entspricht den vier C++-switch-Methoden)
    # ------------------------------------------------------------------
    def get_code_name(self, code: int) -> str:
        """Entspricht MBusinoLib::getCodeName() in MBusinoLib.cpp Zeile 847-1165.

        :param code: MBUS_CODE-Wert (z.B. ``MBUS_CODE.ENERGY_WH``)
        :return: Datensatzname wie "energy", bei unbekanntem Code "" (C++: default)
        """
        return CODE_NAME.get(code, "")

    def get_code_units(self, code: int):
        """Entspricht MBusinoLib::getCodeUnits() in MBusinoLib.cpp Zeile 660-845.

        :return: Einheit ("Wh", "m³", ...) oder ``None`` - ``None`` entspricht
                 dem NULL-Zeiger, den das Original mit ``return 0;`` liefert
        """
        return CODE_UNITS.get(code)  # kein Eintrag -> None wie im C++

    def get_device_class(self, code: int, medium: int = 0xFF) -> str:
        """Entspricht MBusinoLib::getDeviceClass() in MBusinoLib.cpp Zeile 1182-1380.

        :param code: MBUS_CODE-Wert
        :param medium: M-Bus-Medium-Byte aus ``decode_header()`` ("medium_code"),
                       Standard 0xFF = unbekannt - wie der C++-Default-Parameter
        :return: Home Assistant device_class, "" wenn keine passende existiert
        """
        # C++ Zeile 1202-1206: die drei Volumen-Codes rufen die Medium-Hilfs-
        # funktion auf (case VOLUME_M3 / VOLUME_FT3 / VOLUME_GAL).
        if code in (MBUS_CODE.VOLUME_M3, MBUS_CODE.VOLUME_FT3, MBUS_CODE.VOLUME_GAL):
            return _volume_class_from_medium(medium)
        return DEVICE_CLASS.get(code, "")

    def get_state_class(self, code: int) -> str:
        """Entspricht MBusinoLib::getStateClass() in MBusinoLib.cpp Zeile 1382-1525.

        :return: "total_increasing" / "measurement" / "" (C++: default)
        """
        # SPECIAL_SUPPLIER_INFO hat im C++ keinen eigenen case und fällt über
        # default auf "" - hier liefert .get() dasselbe.
        return STATE_CLASS.get(code, "")

    # ------------------------------------------------------------------
    # interne Helfer (entsprechen den protected C++-Methoden)
    # ------------------------------------------------------------------
    @staticmethod
    def _find_definition(vif: int) -> int:
        """Entspricht MBusinoLib::_findDefinition() in MBusinoLib.cpp Zeile 1528-1539.

        Sucht den ERSTEN Tabelleneintrag mit ``base <= vif < base + size``.

        :return: Index in ``VIF_DEFS`` oder -1 wenn nichts gefunden wurde
                   (C++: ``int16_t``, Rückgabe -1)
        """
        for index, (_code, base, size, _scalar) in enumerate(VIF_DEFS):
            if base <= vif < (base + size):
                return index
        return -1

    @staticmethod
    def _get_vif(code: int, scalar: int) -> int:
        """Entspricht MBusinoLib::_getVIF() in MBusinoLib.cpp Zeile 1541-1555.

        Umkehrung von ``_find_definition``: liefert den VIF, der zu Code und
        Skalierung passt (wird vom Original beim Dekodieren nicht benutzt,
        nur von den AUnit-Tests).

        :return: VIF-Wert oder 0xFF wenn keine gültige Kombination existiert
                 (C++-Kommentar: "this is not a valid VIF")
        """
        for _code, base, size, def_scalar in VIF_DEFS:
            if code == _code:
                if def_scalar <= scalar < (def_scalar + size):
                    return base + (scalar - def_scalar)
        return 0xFF

    # ------------------------------------------------------------------
    # Datensätze
    # ------------------------------------------------------------------
    def decode_records(self, buffer, size: int = None) -> list:
        """Entspricht MBusinoLib::decodeRecords() in MBusinoLib.cpp Zeile 62-657.

        Zerlegt den Nutzdatenbereich eines Telegramms in einzelne Datensätze.

        :param buffer: Bytes ab dem ersten DIF (bei Telegrammen ab Offset 0x13)
        :param size: Anzahl der zu lesenden Bytes - so wie im C++ der Parameter
                     ``uint8_t size``. ``test_decode.cpp`` übergibt hier
                     ``packet_size - 0x13 - 2`` (also OHNE Checksumme und
                     Stopbyte, obwohl ``buffer`` 2 Bytes länger ist).
                     ``None`` (Voreinstellung) bedeutet ``len(buffer)``.
        :return: Liste der Datensätze - identisch mit dem C++-``JsonArray``,
                 jeder Eintrag hat die Keys
                 ``vif``, ``code``, ``value_scaled``, ``value_string``,
                 ``units``, ``name`` und optional ``subUnit``, ``storage``,
                 ``tariff``, ``telegramFollow``.
                 ACHTUNG: Bei einem Fehler wäre der C++-Rückgabewert 0, das
                 JsonArray enthält aber bereits decodierte Datensätze - diese
                 gibt Python zurück (der Fehler steht in ``get_error()``).
        """
        data = bytes(buffer)
        buf_len = len(data)
        if size is None:
            size = buf_len

        records: list = []
        index = 0

        def rd(pos: int) -> int:
            """Ein Byte lesen wie ``buffer[pos]`` im C++ - dort OHNE Prüfung.

            Jeder Zugriff, der im Original über das Ende hinausreichen
            würde (UB), läuft hier über diese Funktion und löst
            ``_OutOfBounds`` aus -> ``BUFFER_OVERFLOW``.
            """
            if 0 <= pos < buf_len:
                return data[pos]
            raise _OutOfBounds(pos)

        try:
            # `while (index < size)` - MBusinoLib.cpp Zeile 66
            while index < size:
                # ------------------------------------------------------------ #
                # DIF dekodieren - MBusinoLib.cpp Zeile 71-162
                # ------------------------------------------------------------ #
                dif = rd(index)          # C++: uint8_t dif = buffer[index++];
                index += 1
                dif_least4bit = dif & 0x0F
                dif_function_field = (dif & 0x30) >> 4

                # switch(difLeast4bit) - MBusinoLib.cpp Zeile 98-162:
                # -> (Länge in Byte, Datenkodierungsart)
                #   0 = keine Daten, 1 = Ganzzahl, 2 = BCD, 3 = real (float32),
                #   4 = variabel, 5 = Spezialfunktion,
                #   6 = Datum+Zeit Typ F, 7 = Datum Typ G
                #   (6/7 kommen weiter unten über den VIF dazu)
                #
                # C++-Tabelle (Zeile 80-95): DIF-Bit 0..3 = Länge/Kodierung,
                # Bit 4..5 = Funktion (0=current,1=_max,2=_min,3=_err)
                length, data_coding_type = _DIF_TABLE[dif_least4bit]

                # Funktion-Feld anhängen - MBusinoLib.cpp Zeile 164-179
                function_field = _FUNCTION_FIELDS[dif_function_field]

                # ------------------------------------------------------------ #
                # DIFE behandeln - MBusinoLib.cpp Zeile 181-211
                # ------------------------------------------------------------ #
                # Bit 6 des DIF = "Speicher 1" vorbelegt
                storage_number = 1 if (dif & 0x40) == 0x40 else 0
                dife_number = 0
                # C++: uint8_t dife[10] = {0};  (Index 0 bleibt unbenutzt,
                # die DIFEs liegen ab Index 1 - daher hier 11 Plätze, damit
                # der C++-Zugriff dife[difeNumber+1] (Zeile 197-208) am Ende
                # der Schleife auf den Wert 0 trifft statt ins Leere zu laufen)
                dife = [0] * 11
                if_dife = (dif & 0x80) == 0x80  # Bit 7 = "eine DIFE folgt"
                while if_dife:
                    dife_number += 1
                    if dife_number > 9:
                        # C++ schreibt hier über dife[10] hinaus (UB)
                        raise _OutOfBounds(dife_number)
                    dife[dife_number] = rd(index)      # C++ Zeile 191
                    if_dife = (rd(index) & 0x80) == 0x80  # weitere DIFE?
                    index += 1

                # Auswertung der DIFEs - MBusinoLib.cpp Zeile 194-210
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

                # Ende DIFE-Behandlung (C++: "// End of DIFE handling" Zeile 212)

                # ------------------------------------------------------------ #
                # VIF(E) holen - MBusinoLib.cpp Zeile 213-246
                # ------------------------------------------------------------ #
                vif = 0
                vifarray = [0] * 10          # C++: uint8_t vifarray[10] = {0};
                vifcounter = 0
                custom_vif_len = 0           # C++: uint8_t customVIFlen = 0;
                custom_vif = ""              # C++: char customVIF[20] = {0};
                if_custom_vif = False        # C++: bool ifcustomVIF = false;

                while True:
                    if index == size:
                        # C++ Zeile 225-228: expliziter BUFFER_OVERFLOW
                        self._error = MBUS_ERROR.BUFFER_OVERFLOW
                        return records
                    if vifcounter > 9:
                        # C++ schreibt hier über vifarray[10] hinaus (UB)
                        raise _OutOfBounds(vifcounter)
                    vifarray[vifcounter] = rd(index)   # C++ Zeile 230
                    index += 1

                    if (vifarray[0] & 0x7F) == 0x7C and vifcounter == 0:
                        # Customized ASCII VIF (C++ Zeile 232-237):
                        # das nachfolgende Byte ist die Länge des ASCII-Strings
                        custom_vif_len = rd(index)
                        if vifarray[0] == 0xFC:
                            # Beim 0xFC-VIF den ASCII-String überspringen,
                            # um an die VIFE(s) dahinter zu kommen
                            index = index + custom_vif_len + 1

                    if vifcounter < 2:
                        # normalerweise reichen VIF + erste VIFE (C++ Zeile 239)
                        vif = (vif << 8) + vifarray[vifcounter]
                    elif vifcounter == 2 and vif == 0xFDFD:
                        # ... außer VIF 0xFDFD braucht das dritte Byte (Zeile 242)
                        vif = (vif << 8) + vifarray[vifcounter]

                    vifcounter += 1
                    # Abbruch, sobald das Bit 7 des zuletzt gelesenen Byte fehlt
                    if (vifarray[vifcounter - 1] & 0x80) != 0x80:
                        break

                # ------------------------------------------------------------ #
                # VIF-Feinjustierung - MBusinoLib.cpp Zeile 248-276
                # ------------------------------------------------------------ #
                # Wenn das höchste Bit im ERSTEN Byte steht und es keiner der
                # "Erweiterungs-Kennbyte" 0xFD/0xFC/0xFB/0xFF ist, steckt der echte
                # VIF allein in diesem Byte (Erweiterungsbit maskieren weg).
                if (
                    (vifarray[0] & 0x80) == 0x80
                    and vifarray[0] != 0xFD
                    and vifarray[0] != 0xFC
                    and vifarray[0] != 0xFB
                    and vifarray[0] != 0xFF
                ):
                    vif = vifarray[0] & 0x7F

                if vifarray[0] == 0x7C:
                    vif = 0x7C00   # C++ Zeile 253-255

                # 0x6D = Datum+Zeit Typ F, 0x6C = Datum Typ G -> Kodierung
                # unabhängig vom DIF überschreiben (C++ Zeile 257-263)
                if (vif & 0x7F) == 0x6D:
                    data_coding_type = 6
                elif (vif & 0x7F) == 0x6C:
                    data_coding_type = 7
                elif (vif & 0x7F00) == 0x7C00:
                    # Customized ASCII VIF: den String jetzt wirklich lesen
                    # (C++ Zeile 264-277)
                    vif = 0xFC00
                    if vifarray[0] == 0xFC:
                        # beim 0xFC wurde der String oben bereits übersprungen,
                        # deshalb den Zeiger zurücksetzen
                        index = index - custom_vif_len - 1
                    # C++: char vifBuffer[customVIFlen + 1]; (uninitialisiert!)
                    vif_buffer = [0] * (custom_vif_len + 1)
                    for i in range(custom_vif_len + 1):
                        # C++ Zeile 271: vifBuffer[customVIFlen-i] = buffer[index - vifcounter + 1];
                        # Der Lesestart verschiebt sich mit -vifcounter, weil
                        # index beim 0xFC-Fall um die VIFE(n) weiter steht -
                        # am Ende zeigt der Zeiger exakt auf das Längenbyte.
                        vif_buffer[custom_vif_len - i] = rd(index - vifcounter + 1)
                        index += 1
                    # C++: strncpy(customVIF, vifBuffer, customVIFlen);
                    # vifBuffer[customVIFlen] enthält das Längenbyte und
                    # bleibt unberücksichtigt; die Zeichen stehen gedreht
                    # (M-Bus sendet ASCII rückwärts) und werden hier wieder
                    # in Leserichtung gedreht.
                    # char customVIF[20] -> höchstens 19 Zeichen + NUL.
                    # (C++ würde bei längeren Strings über den Puffer laufen)
                    custom_vif = bytes(vif_buffer[:custom_vif_len]).decode(
                        "latin-1", errors="replace"
                    )[:19]
                    if_custom_vif = True

                # Bit 7 des letzten VIF-Bytes löschen (C++ Zeile 278), sonst
                # findet _findDefinition() keinen Treffer
                vif = vif & 0xFFFFFF7F

                # ------------------------------------------------------------ #
                # Definition suchen - MBusinoLib.cpp Zeile 280-287
                # ------------------------------------------------------------ #
                def_index = self._find_definition(vif)
                if def_index < 0:
                    # C++ setzt den Fehler und arbeitet DANACH mit Eintrag 0
                    # weiter (UNKNOWN_VIF) - die Zeile "return 0" ist dort
                    # auskommentiert. Genau so verhält sich Python auch.
                    self._error = MBUS_ERROR.UNSUPPORTED_VIF
                    def_index = 0

                # ------------------------------------------------------------ #
                # VIFE-Erweiterungen - MBusinoLib.cpp Zeile 288-378
                # ------------------------------------------------------------ #
                extension_scaler = 0                # C++: int8_t extensionScaler
                extension_additive_constant = 0.0   # C++: double extensionAdditiveConstant
                name_extension = ""                 # C++: char stringNameExtension[10]
                no_unit = False                     # C++: bool noUnit

                if vifcounter - 1 > 0:  # mindestens eine VIFE vorhanden
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
                            # C++ liest hier über vifarray[10] hinaus (UB)
                            raise _OutOfBounds(extensions_counter)
                        byte = vifarray[extensions_counter]

                        if (byte & 0x7F) == 0x7D:
                            # E111 1101: multiplikativer Korrekturfaktor 1000
                            extension_scaler = 3
                        elif (byte & 0x78) == 0x70:
                            # E111 0nnn: multiplikativer Faktor 10^(nnn-6)
                            extension_scaler = (byte & 0x07) - 6
                        elif (byte & 0x7C) == 0x78:
                            # E111 10nn: additives Korrektur-Konstante 10^(nn-3)
                            additive_scaler = (byte & 0x03) - 3
                            extension_additive_constant = 1.0
                            for _ in range(additive_scaler):
                                extension_additive_constant *= 10.0
                            for _ in range(-additive_scaler if additive_scaler < 0 else 0):
                                extension_additive_constant /= 10.0
                        elif (byte & 0x7A) == 0x6A:
                            # E110 1f1b: Datum/Zeit - passt die Kodierung an
                            if dif_least4bit == 4:
                                data_coding_type = 6
                            elif dif_least4bit == 2:
                                data_coding_type = 7
                            name_extension = "_TimeSt"
                            no_unit = True
                        elif byte == 0xFC or byte == 0xFF:
                            # "Lesebenutzer"-Erweiterung: das NAECHSTE Byte
                            # wählt Phase/Bezugsgrösse (C++ Zeile 334-372)
                            if extensions_counter + 1 > 9:
                                raise _OutOfBounds(extensions_counter + 1)
                            extension_buffer = vifarray[extensions_counter + 1] & 0x7F
                            suffix = _PHASE_SUFFIX.get(extension_buffer)
                            if suffix is not None:
                                name_extension = suffix
                                extensions_counter += 1  # C++ springt über das Byte
                        extensions_counter += 1
                        if extensions_counter > vifcounter:
                            break

                # ------------------------------------------------------------ #
                # Pufferüberlauf-Prüfung - MBusinoLib.cpp Zeile 380-384
                # ------------------------------------------------------------ #
                if index + length > size or index + length > buf_len:
                    self._error = MBUS_ERROR.BUFFER_OVERFLOW
                    return records

                # ------------------------------------------------------------ #
                # Wert lesen - MBusinoLib.cpp Zeile 386-580
                # ------------------------------------------------------------ #
                value16 = 0            # C++ Zeile 387: int16_t - merkt negative 2-Byte-Werte
                value32 = 0            # C++ Zeile 388: int32_t - merkt negative 4-Byte-Werte
                value = 0              # C++ Zeile 389: int64_t
                value_float = 0.0      # C++ Zeile 391: float (echte 32-Bit-Zahl!)
                date = b""             # C++ Zeile 395: uint8_t date[len]
                datestring = ""        # C++ Zeile 396: char datestring[16]
                datestring2 = ""       # C++ Zeile 397: char datestring2[30]
                value_string = ""      # C++ Zeile 398: char valueString[30]
                switch_again = False   # C++ Zeile 399
                negative = False       # C++ Zeile 400
                ascii_value = 0        # C++ Zeile 401: 0=double, 1=ASCII, 2=beides

                # C++: do { switch(dataCodingType) ... } while(switchAgain);
                while True:
                    switch_again = False

                    if data_coding_type == 0:
                        # case 0 (C++ Zeile 405): keine Daten, value bleibt 0
                        pass

                    elif data_coding_type == 1:
                        # case 1 (C++ Zeile 408-425): Ganzzahl, LITTLE-ENDIAN
                        # (die Schleife baut das Byte mit dem Index len-i-1 zum
                        # höchstwertigen Byte auf - M-Bus sendet LSB zuerst)
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
                        # case 2 (C++ Zeile 427-461): BCD, je Byte 2 Ziffern
                        if length == 2:
                            value16 = 0
                        elif length == 4:
                            value32 = 0
                        else:
                            value = 0
                        for i in range(length):
                            byte = rd(index + length - i - 1)
                            if i == 0 and (byte & 0xF0) == 0xF0:
                                # Nur unsigned BCD ist vorgesehen, manche
                                # Hersteller setzen ein F in das oberste
                                # Halbbyte als "negativ"-Merkmal.
                                # QUIRK des Originals: dabei geht auch die
                                # Zehnerziffer dieses Bytes verloren
                                # (byte wird auf 0x0F reduziert).
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
                            # C++ Zeile 458-460: nur BCD kennt den Negativ-Fall
                            value = value * -1

                    elif data_coding_type == 3:
                        # case 3 (C++ Zeile 464-467): real = IEEE-754 32 Bit
                        value = 0
                        for i in range(length):
                            value = (value << 8) + rd(index + length - i - 1)
                        # C++: memcpy(&valueFloat, &value, sizeof(valueFloat))
                        # -> die NIEDRIGEN 4 Byte von value werden als float
                        # interpretiert (gleiche Bytereihenfolge wie oben).
                        value_float = struct.unpack(
                            "<f", struct.pack("<I", value & 0xFFFFFFFF)
                        )[0]

                    elif data_coding_type == 4:
                        # case 4 (C++ Zeile 470-522): variable Länge, LVAR
                        #   00..BFh ASCII, C0..CFh positiv. BCD,
                        #   D0..DFh negativ. BCD, E0..EFh Bytes als Ganzzahl,
                        #   F0..FAh Bytes als Float, FB..FFh reserviert
                        lvar = rd(index)
                        if lvar <= 0xBF:
                            # ASCII-String mit LVAR Zeichen (C++ Zeile 483-494)
                            length = lvar
                            index += 1
                            char_buffer = [0] * (length + 1)
                            for i in range(length + 1):
                                # Zeichen rückwärts wie im Original: damit
                                # steht der String wieder in Leserichtung da
                                char_buffer[i] = rd(index + (length - i - 1))
                            # C++: strncpy(valueString, charBuffer, len);
                            # char valueString[30] -> höchstens 29 Zeichen
                            value_string = bytes(char_buffer[:length]).decode(
                                "latin-1", errors="replace"
                            )[:29]
                            ascii_value = 1
                        elif 0xC0 <= lvar <= 0xCF:
                            # positiv. BCD, (LVAR - C0h) Byte (C++ Zeile 495)
                            length = lvar - 0xC0
                            index += 1
                            data_coding_type = 2
                            switch_again = True
                        elif 0xD0 <= lvar <= 0xDF:
                            # negativ. BCD (C++ Zeile 501)
                            length = lvar - 0xD0
                            index += 1
                            data_coding_type = 2
                            switch_again = True
                            negative = True
                        elif 0xE0 <= lvar <= 0xEF:
                            # Binzzahl, (LVAR - E0h) Byte (C++ Zeile 508)
                            length = lvar - 0xE0
                            index += 1
                            data_coding_type = 1
                            switch_again = True
                        elif 0xF0 <= lvar <= 0xFA:
                            # Gleitkommazahl, (LVAR - F0h) Byte (C++ Zeile 515)
                            length = lvar - 0xF0
                            index += 1
                            data_coding_type = 3
                            switch_again = True
                        # FB..FF reserviert -> wie im Original nichts passieren,
                        # length bleibt 0 und der nächste Datensatz folgt

                    elif data_coding_type == 5:
                        # case 5 (C++ Zeile 524): Spezialfunktion, nichts zu tun
                        pass

                    elif data_coding_type == 6:
                        # case 6 (C++ Zeile 527-552): Datum+Zeit Typ F, 4 Byte
                        date = data[index:index + length]
                        if len(date) < 4:
                            # C++ liest date[0..3] aus einem zu kleinen VLA (UB)
                            raise _OutOfBounds(len(date))
                        if (date[0] & 0x80) == 0:
                            # Bit 7 des Minuten-Bytes = "Zeit ungültig" (C++ Zeile 531)
                            year = ((date[2] & 0xE0) >> 5) | ((date[3] & 0xF0) >> 1)
                            month = date[3] & 0x0F
                            mday = date[2] & 0x1F
                            hour = date[1] & 0x1F
                            minute = date[0] & 0x3F
                            # C++ snprintf("20%02d%02d%02d%02d%02d") - die
                            # Formate ergeben exakt dieselben Zeichenketten.
                            # (Die dort angegebene Pufferlänge 24 bei
                            # char[16] ist ein BUG, wird aber nie erreicht,
                            # weil max. 13 Zeichen entstehen.)
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
                        # case 7 (C++ Zeile 554-578): Datum Typ G, 2 Byte
                        date = data[index:index + length]
                        if len(date) < 2:
                            raise _OutOfBounds(len(date))
                        if (date[1] & 0x0F) <= 12:
                            # Monat > 12 = ungültig (C++ Zeile 560)
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

                # C++ Zeile 582: index += len;
                index += length

                # ------------------------------------------------------------ #
                # Skalierung - MBusinoLib.cpp Zeile 584-606
                # ------------------------------------------------------------ #
                scaled = 0.0
                scalar = 0
                if def_index != 0:
                    # C++ Zeile 587-589 (uint32_t-Arithmetik, Ergebnis auf
                    # int8_t abgeschnitten - s. _to_int8):
                    #   scalar = vif_defs[def].scalar + vif - vif_defs[def].base + extensionScaler
                    _code, base, _size, def_scalar = VIF_DEFS[def_index]
                    scalar = _to_int8(def_scalar + vif - base + extension_scaler)

                if data_coding_type == 3:
                    # echte Gleitkommazahl: nur der VIF-Skalierungswert zählt
                    scaled = value_float
                    if vifarray[0] != 0xFF:
                        # C++ Zeile 591-596: erstmal mit 10 multiplizieren,
                        # dann (wenn scalar negativ) durch 10 dividieren und
                        # zuletzt die additive Konstante drauf - REIHENFOLGE
                        # exakt wie im Original, damit das Ergebnis bit-identisch
                        # ist (Division und Multiplikation sind nicht vertauschbar).
                        for _ in range(scalar if scalar > 0 else 0):
                            scaled *= 10.0
                        for _ in range(-scalar if scalar < 0 else 0):
                            scaled /= 10.0
                        scaled = scaled + extension_additive_constant
                elif vifarray[0] == 0xFF:
                    # herstellerspezifisch: NICHT skalieren, NICHT addieren
                    scaled = float(value)   # C++ Zeile 599-600
                else:
                    scaled = float(value)
                    for _ in range(scalar if scalar > 0 else 0):
                        scaled *= 10.0
                    for _ in range(-scalar if scalar < 0 else 0):
                        scaled /= 10.0
                    scaled = scaled + extension_additive_constant

                # ------------------------------------------------------------ #
                # Datensatz anlegen - MBusinoLib.cpp Zeile 608-646
                # ------------------------------------------------------------ #
                # Die Key-Reihenfolge entspricht exakt der C++-Schreibreihenfolge.
                record = {}
                # C++ Zeile 610: String("0x" + String(vif,HEX)) -> kleines
                # Hex ohne führende Nullen
                record["vif"] = "0x%x" % vif
                record["code"] = VIF_DEFS[def_index][0]

                if ascii_value != 1:
                    # C++ Zeile 616-620: reiner Zahlwert (nicht bei ASCII)
                    record["value_scaled"] = scaled
                if ascii_value > 0:
                    # C++ Zeile 621-623: formatierter String (Datum/ASCII)
                    record["value_string"] = value_string

                if if_custom_vif:
                    # C++ Zeile 624-626: Einheit kommt aus dem ASCII-VIF
                    record["units"] = custom_vif
                elif self.get_code_units(VIF_DEFS[def_index][0]) is not None and not no_unit:
                    # C++ Zeile 627-629: Einheit aus der Nachschlagetabelle;
                    # "noUnit" schaltet die Einheit ab (z.B. bei _TimeSt)
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
                # Abschlussmarken - MBusinoLib.cpp Zeile 648-655
                # ------------------------------------------------------------ #
                # Prüfe das Byte, das AUF den Datensatz folgt. `index != size`
                # steht im C++ NACH dem Lesezugriff (dort also immer ein Byte
                # gelesen, auch wenn index schon am Ende ist - bei der üblichen
                # Übergabe ist das die Checksumme).
                following = rd(index) if index < buf_len else None
                if following == 0x0F and index != size:
                    # 0x0F: ab hier herstellerspezifische Daten -> aufhören
                    break
                if following == 0x1F and index != size:
                    # 0x1F: nächste Nachricht enthält mehr Datensätze
                    record["telegramFollow"] = 1
                    break

        except _OutOfBounds:
            # Entspricht den "return 0"-Stellen des Originals; dort endet die
            # Schleife sofort, bereits angehängte Datensätze bleiben im
            # JsonArray (und werden hier zurückgegeben).
            self._error = MBUS_ERROR.BUFFER_OVERFLOW
            return records

        return records

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def decode_header(self, buffer, length: int = None) -> dict:
        """Entspricht MBusinoLib::decodeHeader() in MBusinoLib.cpp Zeile 1563-1677.

        Dekodiert den Fixed-Data-Header eines Long-Frame-Telegramms.

        :param buffer: das KOMPLETTE Telegramm inkl. Start-/Stopbyte
        :param length: Gesamtlänge, die gelesen werden darf
                       (``None`` = ``len(buffer)``). Das Original erwartet hier
                       wie in ``decode_telegram()`` und im Beispiel die
                       ``packet_size`` (``data[1] + 6``), NICHT die Dateilänge.
        :return: Dict mit den ArduinoJson-Keys ``len``, ``c_field``, ``address``,
                 ``ci_field`` und - wenn CI 0x72/0x76 ist - ``id``,
                 ``manufacturer``, ``version``, ``medium_code``, ``medium``,
                 ``access_counter``, ``status``, ``status_details`` (verschachtelt)
                 und ``signature``.

                 Rückgabe-Mapping zum bool'schen C++-Rückgabewert:
                 * ``{}``  -> C++ ``false`` vor dem Schreiben (zu kurz,
                   Startbyte falsch oder Längenfelder ungleich)
                 * Dict ohne ``"id"`` -> C++ ``false`` NACH dem Schreiben
                   (CI ist kein 0x72/0x76, nur die Basisfelder stehen drin)
                 * Dict mit ``"id"`` -> C++ ``true``
        """
        data = bytes(buffer)
        if length is None:
            length = len(data)

        # 1. Mindestlänge für Long Frame mit Fixed Data Header (C++ Zeile 1570-1574)
        if length < 19 or len(data) < 19:
            return {}
        # 2. Startbytes 68 ... 68 prüfen (C++ Zeile 1576-1579)
        if data[0] != 0x68 or data[3] != 0x68:
            return {}
        # 3. Längenfelder müssen identisch sein (C++ Zeile 1581-1584)
        if data[1] != data[2]:
            return {}

        header = {
            "len": data[1],          # C++ Zeile 1587
            "c_field": data[4],      # C++ Zeile 1588
            "address": data[5],      # C++ Zeile 1589  (README nennt das "a_field"!)
            "ci_field": data[6],     # C++ Zeile 1590
        }

        # Nur CI 0x72 (long/variable) und 0x76 (short/variable) tragen den
        # Fixed Data Header (C++ Zeile 1594-1596)
        if data[6] not in (0x72, 0x76):
            return header  # -> entspricht `return false` hinter dem Schreiben

        # 4. Identifikationsnummer, 4 Byte BCD, LSB zuerst (C++ Zeile 1599-1602)
        header["id"] = "%02X%02X%02X%02X" % (data[10], data[9], data[8], data[7])
        # 5. Hersteller, 2 Byte, LSB zuerst -> 3 Buchstaben zu je 5 Bit (Zeile 1605-1612)
        manuf_code = (data[12] << 8) | data[11]
        header["manufacturer"] = "".join(
            chr(((manuf_code >> shift) & 0x001F) + 64) for shift in (10, 5, 0)
        )
        # 6. Version (C++ Zeile 1615)
        header["version"] = data[13]
        # 7. Medium als Code und als Klartext (C++ Zeile 1618-1636)
        medium = data[14]
        header["medium_code"] = medium
        header["medium"] = MEDIUM_NAMES.get(medium, "Unknown")
        # 8. Zählerstand (C++ Zeile 1639)
        header["access_counter"] = data[15]
        # 9. Statusbyte inkl. DetailaufSchlüsselung (C++ Zeile 1642-1651)
        status = data[16]
        header["status"] = status
        app_error = status & 0x03
        status_details = {
            "battery_low": bool(status & 0x04),
            "permanent_error": bool(status & 0x08),
            "temporary_error": bool(status & 0x10),
        }
        # QUIRK: 0x03 (reserviert) bekommt im Original KEINEN app_status-Key
        if app_error == 0x00:
            status_details["app_status"] = "no_error"
        elif app_error == 0x01:
            status_details["app_status"] = "busy"
        elif app_error == 0x02:
            status_details["app_status"] = "any_error"
        header["status_details"] = status_details
        # 10. Signatur, 2 Byte, LSB zuerst (C++ Zeile 1654-1656)
        header["signature"] = (data[18] << 8) | data[17]

        return header

    # ------------------------------------------------------------------
    # NEU: komplettes Telegramm
    # ------------------------------------------------------------------
    def decode_telegram(self, raw) -> dict:
        """NEU (im C++ nicht vorhanden): zerlegt ein komplettes M-Bus-Telegramm.

        Rahmenbedingung wie ``test_decode.cpp``:

        * Aufbau ``68 LL LL 68 C A CI ... CHK 16``
        * ``packet_size = data[1] + 6`` (test_decode.cpp Zeile 51: 4 Bytes
          Start/Länge + L Nutzdaten + Checksumme + Stopbyte)
        * Datensätze beginnen ab Offset ``0x13`` (test_decode.cpp Zeile 53:
          "Standard: skip header + fixed data header")
        * Datensatzlänge ``packet_size - 0x13 - 2`` (test_decode.cpp Zeile 64:
          die 2 sind Checksumme und Stopbyte)

        :param raw: Telegramm als ``bytes``/``bytearray``/Liste von Werten oder
                    als Hex-String ("68 56 56 68 ...", Kommas und "0x"-Prefixe
                    sind erlaubt - siehe ``_parse_hex``)
        :return:::

            {
              "frame": {...},          # Rahmenprüfungen, s. unten
              "header": {...},         # Ergebnis von decode_header()
              "records": [...],        # Ergebnis von decode_records()
              "error": <int>,          # MBUS_ERROR-Code der Dekodierung
              "error_message": <str>   # deutsche Meldung zum ersten Problem
            }

        ``frame`` enthält ``byte_count``, ``packet_size``, ``slave_address``,
        ``c_field``, ``ci_field``, ``start_ok``, ``length_ok``, ``fits``,
        ``stop_ok``, ``checksum``, ``checksum_received``, ``checksum_ok``,
        ``quartet_checksum_ok``, ``ok`` und ``error_message``.

        Fehlerlogik: ``error`` trägt die MBUS_ERROR-Kennzahl (die Enum hat
        keinen eigenen Rahmenfehler-Code; nur "Länge passt nicht" wird als
        ``BUFFER_OVERFLOW`` gemeldet, weil auch test_decode.cpp diesen Fall
        mit "declared length ... but only N bytes provided" abbricht).
        ``error_message`` nennt immer das erste gefundene Problem - wenn nur die
        Checksumme stimmt, steht ``error`` auf 0, die Meldung beschreibt aber
        dennoch den Fehler und ``frame["ok"]`` ist ``False``.
        """
        data = bytes(raw) if not isinstance(raw, str) else _parse_hex(raw)
        # Vor jeder neuen Nachricht den Fehler zurücksetzen - im C++ leert
        # getError() den Stand nach dem Auslesen, hier liefern wir ihn direkt.
        self._error = MBUS_ERROR.NO_ERROR

        # --- Startwerte für die Rahmenprüfung -------------------------
        byte_count = len(data)
        too_short = byte_count < 6      # test_decode.cpp Zeile 37-40
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
            frame_error = "Telegramm zu kurz: %d Bytes, mindestens 6 werden benötigt." % byte_count
            error = MBUS_ERROR.BUFFER_OVERFLOW
        else:
            # PaketGröße: 68 | LL | LL | 68 | C | A | CI | Daten | CHK | 16
            #   -> 4 Kopf-Bytes + LL Bytes (C bis Ende der Daten) + CHK + 16
            packet_size = data[1] + 6          # test_decode.cpp Zeile 51
            start_ok = data[0] == 0x68 and data[3] == 0x68  # test_decode prüft das NICHT
            length_ok = data[1] == data[2]     # beide Längenfelder identisch
            fits = packet_size <= byte_count    # test_decode.cpp Zeile 56-60
            if fits:
                # Checksumme: Byte vor dem Stopbyte
                #   C++/EN 13757: einfache Byte-Summe ab dem C-Feld (Offset 4)
                #   bis zum letzten Datenbyte (Offset packet_size-3)
                checksum = sum(data[4:packet_size - 2]) & 0xFF
                checksum_received = data[packet_size - 2]
                checksum_ok = checksum_received == checksum
                # Quartett-Summe (Summe aller Halbbytes) - in manchen
                # Implementationen benutzt, hier als Alternative akzeptiert
                quartet = 0
                for byte in data[4:packet_size - 2]:
                    quartet += (byte & 0x0F) + (byte >> 4)
                quartet_checksum_ok = checksum_received == (quartet & 0xFF)
                stop_ok = data[packet_size - 1] == 0x16

            # --- erstes Problem benennen --------------------------------
            if not start_ok:
                frame_error = "Startbyte unerwartet: 0x%02X/0x%02X statt 0x68/0x68." % (data[0], data[3])
            elif not length_ok:
                frame_error = "Längenfelder ungleich: L1=0x%02X, L2=0x%02X." % (data[1], data[2])
            elif not fits:
                frame_error = ("Deklarierte Länge %d erwartet %d Bytes, "
                               "aber nur %d Bytes vorhanden." % (data[1], packet_size, byte_count))
                error = MBUS_ERROR.BUFFER_OVERFLOW
            elif not stop_ok:
                frame_error = "Stopbyte fehlt: 0x%02X statt 0x16." % data[packet_size - 1]
            elif not checksum_ok and not quartet_checksum_ok:
                frame_error = ("Checksumme stimmt nicht überein: erwartet 0x%02X, "
                               "erhalten 0x%02X." % (checksum, checksum_received))

            # --- dekodieren (analog test_decode.cpp, unabhängig von ------
            #     Startbyte/Checksumme - das Original prüft das nicht) ----
            if fits:
                header = self.decode_header(data, packet_size)          # C++ decodeHeader()
                # Daten ab Offset 0x13, ohne Checksumme(1) und Stopbyte(1)
                start_address = 0x13                                     # test_decode.cpp Zeile 53
                data_len = max(0, packet_size - start_address - 2)       # test_decode.cpp Zeile 64
                records = self.decode_records(data[start_address:packet_size], data_len)
                error = self._error

        if isinstance(error, IntEnum):
            error = int(error)

        # Fehlermeldung: wenn ein MBUS_ERROR vorliegt dessen Text, sonst den
        # Rahmenhinweis - "Kein Fehler" nur, wenn wirklich alles passte.
        if error != MBUS_ERROR.NO_ERROR:
            error_message = self.get_error_message(error)
        elif frame_error:
            error_message = frame_error
        else:
            error_message = "Kein Fehler"

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
# DIF-Tabelle (C++: switch(difLeast4bit) in MBusinoLib.cpp Zeile 98-162)
# Index = untere 4 Bit des DIF, Wert = (Länge in Byte, Datenkodierungsart)
#   Art: 0 = keine Daten, 1 = Ganzzahl, 2 = BCD, 3 = real,
#        4 = variabel, 5 = Spezialfunktion
# ---------------------------------------------------------------------------
_DIF_TABLE = (
    (0, 0),   # 0x00 -> No data            (C++ Zeile  99)
    (1, 1),   # 0x01 -> 8 Bit Integer      (C++ Zeile 102)
    (2, 1),   # 0x02 -> 16 Bit Integer     (C++ Zeile 105)
    (3, 1),   # 0x03 -> 24 Bit Integer     (C++ Zeile 108)
    (4, 1),   # 0x04 -> 32 Bit Integer     (C++ Zeile 111)
    (4, 3),   # 0x05 -> 32 Bit Real        (C++ Zeile 114)
    (6, 1),   # 0x06 -> 48 Bit Integer     (C++ Zeile 117)
    (8, 1),   # 0x07 -> 64 Bit Integer     (C++ Zeile 120)
    (0, 0),   # 0x08 -> Selection for Readout, nicht unterstützt (C++ Zeile 123)
    (1, 2),   # 0x09 -> 2 digit BCD        (C++ Zeile 126)
    (2, 2),   # 0x0A -> 4 digit BCD        (C++ Zeile 129)
    (3, 2),   # 0x0B -> 6 digit BCD        (C++ Zeile 132)
    (4, 2),   # 0x0C -> 8 digit BCD        (C++ Zeile 135)
    (0, 4),   # 0x0D -> variable length    (C++ Zeile 138)
    (6, 2),   # 0x0E -> 12 digit BCD       (C++ Zeile 141)
    (0, 5),   # 0x0F -> Special Functions  (C++ Zeile 144)
)

# Funktion-Feld (C++: switch(difFunctionField) in MBusinoLib.cpp Zeile 164-179)
# Bit 4+5 des DIF: 0=current, 1=_max, 2=_min, 3=_err
_FUNCTION_FIELDS = ("", "_max", "_min", "_err")

# Namensendungen für die "Lesebenutzer"-VIFE 0xFC/0xFF
# (C++: switch(vifExtensionBuffer) in MBusinoLib.cpp Zeile 335-371)
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
