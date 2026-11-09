# Open points - MBusinoLibPy port

Unclean and unresolved things noticed while porting **MBusinoLib 0.10.0** to
Python. **Every item here is `Status: open`** until it is fixed - the items
OP-1, OP-8 and OP-9 were fixed on branch `fix/open-points` (see their status
lines).
Fundstellen refer to the C++ original (local checkout `~/…/MBusinoLib`,
upstream <https://github.com/Zeppelin500/MBusinoLib>) unless stated
otherwise. Line numbers were re-checked against the current checkout on
2026-11-07.

The user-facing documentation lives in the [root README](../README.md); the
port documentation itself is [port-notes.md](port-notes.md).

---

## OP-1 - Unused error codes `MBUS_ERROR` 2, 3 and 5

* **What:** `UNSUPPORTED_CODING` (2), `UNSUPPORTED_RANGE` (3) and
  `NEGATIVE_VALUE` (5) are never set while decoding - they are leftovers of
  the old AllWize encoder that was removed from MBusinoLib.
* **Fundstelle:** the entire C++ source contains exactly three error
  assignments: `MBusinoLib.cpp` line 226 (`BUFFER_OVERFLOW`), line 283
  (`UNSUPPORTED_VIF`) and line 382 (`BUFFER_OVERFLOW`); line 56 only resets to
  `NO_ERROR`. No assignment writes 2, 3 or 5. (The Python port mirrors the
  same three assignments, see `src/MBusinoLibPy/mbusino_lib.py`.)
* **Status:** fixed (branch `fix/open-points`): the three unused members were
  removed from the Python `MBUS_ERROR` enum, the remaining codes keep their
  values (gaps at 2, 3 and 5 are documented as deliberate), and README,
  tests and port-notes were updated to match.
* **Suggestion:** decide between (a) keep the codes for enum-numbering
  compatibility and document them as "never set" (what the Python port does),
  or (b) delete them upstream and treat the renumbering as a breaking change.
  The aunit test `test/aunit/test.cpp` line 156 still *expects* code 2 from
  the removed encoder - that expectation must go either way (see OP-4).

## OP-2 - `snprintf` size argument larger than the target buffer

* **What:** `MBusinoLib.cpp` line 395 declares `char datestring[16] = {0};`
  but line 535 calls `snprintf(datestring, 24, "20%02d%02d%02d%02d%02d", …)`.
  The size argument (24) lies about the object size (16).
* **Effect:** under `_FORTIFY_SOURCE` glibc checks `size > sizeof(object)`
  and aborts in `__chk_fail` - *before* any output is produced. This is
  exactly why `tools/README.md` builds the test harness with FORTIFY
  disabled. (The formatted result is 13 bytes and would fit in 16; the
  abort is caused by the size argument alone.) Line 563
  (`snprintf(datestring, 12, …)`) and line 543 (`snprintf(datestring2, 24, …)`
  into `char datestring2[30]`) are fine.
* **Status:** open
* **Suggestion:** one-line fix - use `sizeof(datestring)` (i.e. 16) at line
  535. The Python port is unaffected (normal strings).

## OP-3 - Wrong checksum in the Elster test telegram

* **What:** the commented-out "Elster" example telegram carries checksum
  byte `0xCC`, but the correct byte-sum checksum is `0xCF`.
* **Fundstelle:** `MBusino/archive/telegram_test/telegram_test.ino` line 96
  (`… 0x00, 0x00, 0x00, 0xCC, 0x16`).
* **Verified:** recomputed over the telegram (37 bytes, L = 0x1F = 31): the
  plain byte sum of the bytes from the C field (offset 4) to the last data
  byte (offset 34) is **0xCF**; the alternative quartet sum (sum of all
  half-bytes) is **0xC5**. So `0xCC` matches neither - it is a typo in the
  source.
* **Effect:** anybody using this telegram as a test vector gets a checksum
  mismatch.
* **Status:** open
* **Suggestion:** correct the byte to `0xCF` in the MBusino sketch.

## OP-4 - Outdated AUnit test file

* **What:** `MBusinoLib/test/aunit/test.cpp` (342 lines) is the original
  AllWize test file and no longer matches the current library.
* **Fundstelle / findings:**
  * Header still says "original File from AllWize", "MBUSPayload library"
    and carries an **LGPL** header, while the repository is **GPL-3.0**.
  * It tests the **removed encoder API**: `addRaw()`, `addField()` and
    `MBUS_CODING` are referenced (lines 156-275) but exist nowhere in
    `src/MBusinoLib.{h,cpp}` (grep: zero hits) → **the file cannot compile**
    against the current library.
  * `EncoderTest, Unsupported_Coding` (line 156) expects
    `MBUS_ERROR::UNSUPPORTED_CODING` from `addRaw()` - the very code the
    decoder never sets (OP-1).
  * The decoder tests call `decode()`, which is marked
    `[[deprecated("use decodeRecords()")]]` (`MBusinoLib.h` lines 377-378) →
    deprecation warnings.
  * Uses ArduinoJson **v6** API (`DynamicJsonDocument`,
    `createNestedArray()`) while the dependency is unpinned
    (`ArduinoJson` in `test/aunit/platformio.ini`) - v7 changed/removed
    these.
  * `platformio.ini` has no `test_framework = aunit`.
* **Status:** open
* **Suggestion:** either port the file to the current decoder-only API
  (drop the encoder tests, switch to `decodeRecords()`, ArduinoJson v7
  syntax, add `test_framework = aunit`) or delete it - the Python golden
  suite covers the decoder anyway. Fix the license header to GPL-3.0 in
  either case.

## OP-5 - C++ reads past the buffer end in `decodeRecords()`

* **What:** several spots read beyond `size` / beyond the real buffer. The
  Python port stops at each of them and raises `BUFFER_OVERFLOW`; in the C++
  original they are undefined behaviour. Fundstellen traced from the
  comments in `src/MBusinoLibPy/mbusino_lib.py` back to the C++ original:
  1. **DIFE loop** - `MBusinoLib.cpp` lines 189-195: `dife[difeNumber] =
     buffer[index];` and `buffer[index] & 0x80` run inside `while(ifDife)`
     with **no `index < size` check**; additionally the 10th DIFE writes past
     `dife[10]` (line 191), and the evaluation loop (lines 199-210) reads
     `dife[difeNumber+1]` - `dife[10]`, one past the array - already at 9
     DIFEs. Python: `raise _OutOfBounds` at `dife_number > 9`, reads via the
     bounds-checked `rd()`.
  2. **VIF copy loop** - line 230: `vifarray[vifcounter] = buffer[index++];`
     is guarded against `index == size` (lines 225-228) but **not** against
     `vifcounter > 9` → write past `vifarray[10]` with more than 10 VIF/VIFE
     bytes (Python comment: "C++ reads past vifarray[10] here (UB)").
  3. **VIFE extension evaluation** - lines 309-376: `vifarray[extensionsCounter]`
     and `vifarray[extensionsCounter+1]` (line 334) with
     `while(extensionsCounter <= vifcounter)` can reach index 10/11 of the
     10-byte array.
  4. **Custom ASCII VIF** - lines 233/235/271: `customVIFlen = buffer[index]`
     runs right after the `index++` of line 230 without a bounds check;
     `index = index + customVIFlen + 1` (line 235) can jump past `size`; and
     line 271 `vifBuffer[customVIFlen-i] = buffer[index-vifcounter+1];` reads
     at a computed offset (with `char vifBuffer[customVIFlen+1]`, line 269,
     used **uninitialised** - the `= {0}` is commented out).
  5. **Value read / LVAR** - lines 483-516: the overflow guard at line 381
     (`index + len > size`) runs with `len = 0` for variable length (DIF
     `0x0D`, line 152), so the LVAR reads `buffer[index]` and the ASCII loop
     `buffer[index + (len-i-1)]` (line 488) have no bound check at all.
  6. **Date VLA** - lines 257-261 + 394 + 529/556: the VIF alone can set
     `dataCodingType = 6/7` while `len` still comes from the DIF (e.g. 0 or
     1) → `uint8_t date[len]` (line 394) is shorter than the 4 (resp. 2)
     bytes read into it at lines 529/556 → stack out-of-bounds read (Python comment:
     "C++ reads date[0..3] out of a too small VLA (UB)").
  7. **Trailing markers** - lines 648 and 652:
     `if(buffer[index] == 0x0F && index != size)` reads `buffer[index]`
     *before* the `index != size` test - one byte past the record region
     (with the usual parameters that byte is the frame checksum, but for an
     exact-sized record buffer it is past the end).
* **Status:** open
* **Suggestion:** add explicit `index < size` guards at each spot (or one
  bounds-checked read helper used everywhere). The Python port already
  stops at exactly these places and can serve as the checklist.

## OP-6 - Name mismatch: `address` vs `a_field`

* **What:** the C++ code writes the address field under the key
  **`address`**, the C++ README documents it as **`a_field`**.
* **Fundstelle:** `MBusinoLib.cpp` line 1583 (`json["address"] = buffer[5];`)
  vs `MBusinoLib/README.md` lines 137 and 160 (`"a_field"`). The Python port
  follows the **code** (`address`).
* **Status:** open
* **Suggestion:** fix the upstream README (Zeppelin500/MBusinoLib) to say
  `address` - renaming the key in code would break existing consumers for a
  documentation-only gain.

## OP-7 - `uint8_t packet_size = data[1] + 6` can wrap around

* **What:** `MBusinoLib/test/test_decode.cpp` line 55 computes the frame
  size in a `uint8_t`.
* **Verified:** `L` is a single byte (0-255), so `L ≥ 250` gives 256-261,
  which wraps to 0-5. Consequences:
  * `data_len = packet_size - start_address - 2` (line 69) is **unaffected**
    - the mod-256 wrap cancels: `(L + 6 - 21) mod 256 = L - 15`, and
    `L - 15 ≤ 240` always fits - so the records are decoded with the correct
    length even when `packet_size` itself is wrong.
  * The truncation guard `if (packet_size > data.size())` (line 59) **is
    defeated**: a truncated telegram with `L ≥ 250` passes the check and
    `decodeRecords(&data[19], data_len)` then reads past the end of the
    `std::vector` (heap OOB read). Even the common "max. 256-byte frame"
    convention (`L ≤ 250`) still hits `L = 250` → wrap.
  * The Python port is **not** affected (`data[1] + 6` is an
    arbitrary-precision int; `fits = packet_size <= byte_count`).
* **Status:** fixed (harness vendored into `tools/test_decode.cpp` with
  `size_t packet_size`)
* **Suggestion:** declare `size_t packet_size = data[1] + 6;` in the
  harness (test-only file, no library impact).

## OP-8 - Stale line references in the Python source comments

* **What:** several line numbers in `src/MBusinoLibPy/mbusino_lib.py`
  drifted away from the current C++ files. Verified examples:
  * `json["address"]` annotated "C++ line 1589" → actually line **1583**.
  * `enum MBUS_ERROR` annotated "MBusinoLib.h line 185-192" → actually
    **184-191**.
  * constructor "MBusinoLib.cpp line 27-31" → actually **28-31**.
  * `decodeHeader() … line 1563-1677` → `MBusinoLib.cpp` has only **1662**
    lines; the function ends at EOF.
  * `test_decode.cpp` references are off by 4-5 lines: "line 51" → actual
    **55** (`packet_size`), "line 53" → **57** (`start_address`), "line
    56-60" → **59-63** (truncation guard), "line 64" → **69** (`data_len`),
    "line 37-40" → **48-51** (too-short check).
* **Status:** fixed (branch `fix/open-points`): all C++ line-number
  references in `src/MBusinoLibPy/mbusino_lib.py` were dropped in favour of
  function names (`decodeRecords()`, `decodeHeader()`, `getError()`,
  `test_decode.cpp main()`/`parseHex()`, …), so they cannot drift again.
* **Suggestion:** re-sync the numbers against the current C++ checkout, or
  drop the line numbers and keep only function names (they drift far less).

## OP-9 - Docs still say "German" after the messages became English

* **What:** all runtime error messages were translated to English
  (commit `b5ffe90`, owner decision), but two docstrings in
  `src/MBusinoLibPy/mbusino_lib.py` still promise German text:
  * line 168: `"""NEW (not in C++): readable German error message.`
  * line 950: `# German message for the first problem found`
  * line 43 still contains a German comment fragment
    (`(Dokumentationswert, s. enums.py)`) although commit `c2f8ad2` claimed
    the German leftovers were removed.
* **Status:** fixed (branch `fix/open-points`): the German fragment
  `(Dokumentationswert, s. enums.py)` was translated; the other two spots
  had already become English (`readable English error message`,
  `# English message for the first problem found`) - `grep -rniE
  'german|deutsch|fuer |für |…' src/` is now empty.
* **Suggestion:** fix the three spots in `src/` (excluded from this
  documentation pass).

## OP-10 - `tools/README.md` overstates the FORTIFY problem

* **What:** `tools/README.md` says "MBusinoLib.cpp lines 535/546 call
  `snprintf(datestring, 24, …)` while datestring is only 16 bytes". Only
  **line 535** has size > buffer; line 543 writes `datestring2[30]` with 24,
  which fits.
* **Related:** the Python comment in `mbusino_lib.py` says the bug "is never
  reached, because at most 13 characters are produced". That is true for the
  *output*, but glibc's `_FORTIFY_SOURCE` aborts on the *size argument*
  regardless - which is exactly why `tools/README.md` has to disable FORTIFY.
  The two documents contradict each other in wording (see also OP-2).
* **Status:** open
* **Suggestion:** correct the line numbers in `tools/README.md` and reword
  the Python comment to mention the fortify abort.

## OP-11 - `strncpy` with attacker-controlled length into fixed stack buffers

* **What:** two copies take their length straight from telegram bytes:
  * `MBusinoLib.cpp` line 490: `strncpy(valueString, charBuffer, len)` with
    `len = buffer[index]` up to `0xBF` (191) into `char valueString[30]`
    (line 397) → up to 191 bytes written into a 30-byte stack buffer.
  * line 274: `strncpy(customVIF, vifBuffer, customVIFlen)` with
    `customVIFlen` up to 255 into `char customVIF[20]` (line 220) → same
    problem.
* **Effect:** stack buffer overflow on a malicious telegram (write, not only
  read). The Python port clamps both to 29 / 19 characters.
* **Status:** open
* **Suggestion:** clamp every copy to `sizeof(dst) - 1` in the C++ original.

## OP-12 - `test_decode.cpp` uses the deprecated `decode()`

* **What:** `MBusinoLib/test/test_decode.cpp` line 70 calls
  `payload.decode(…)` although `decode()` is marked
  `[[deprecated("use decodeRecords()")]]` (`MBusinoLib.h` lines 377-378) →
  every build of the harness (and therefore every golden-file regeneration)
  emits a deprecation warning.
* **Status:** open
* **Suggestion:** switch the harness to `decodeRecords()` - output stays
  identical (`decode()` is a one-line inline forwarder).

## OP-13 - `MBUS_ERROR` has no frame-level error code

* **What:** the Python-only `decode_telegram()` reports frame problems
  ("telegram too short", "declared length does not fit") as
  `BUFFER_OVERFLOW`, because the enum has no frame error code - the meaning
  of code 1 is thereby widened beyond "a record ran past the buffer".
  Purely frame-level problems that have their own flags (bad start/stop
  byte, checksum mismatch) leave `error = 0` and only fill
  `frame["error_message"]` / `frame["ok"]`.
* **Status:** open
* **Suggestion:** document as-is (done in the root README), or add a
  dedicated frame error code in a future major version of the enum.

## OP-14 - Dead lines and commented-out leftovers in the C++ original

* **What (all in `MBusinoLib.cpp` unless noted):**
  * line 218: `uint8_t vifes = 0;` - declared, never used.
  * line 285: `//return 0;` - the disabled early-out after
    `UNSUPPORTED_VIF`; the decoder instead continues with `def = 0`.
  * lines 532 and 560: `//out_len = snprintf(output, output_size, "invalid");`
    - commented-out fragment inside the date checks.
  * lines 640-646: `/* // only for debug … */` block writing `difes` /
    `dife1` / `dife2` into a `data` object that does not exist in that
    scope.
  * `test/test_decode.cpp` line 70 uses the deprecated `decode()` - see
    OP-12.
* **Status:** open
* **Suggestion:** delete the dead declarations/comments when the C++
  original is touched next; low priority (no behavioural effect).
