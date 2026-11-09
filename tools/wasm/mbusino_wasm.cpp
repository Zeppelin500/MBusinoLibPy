// Emscripten wrapper around the original C++ MBusinoLib, for the docs/ test page.
//
// Exposes decode_hex(hex) -> JSON string with { slave_address, header,
// header_ok, records_decoded, error_code, records }. It mirrors the Arduino
// example (MbusinoLibExample.ino): decodeHeader() into "header",
// decodeRecords() into "records".
//
// Built by tools/wasm/build.sh (needs em++ on PATH).
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include <emscripten.h>
#include <ArduinoJson.h>

#include "MBusinoLib.h"

// Parse "68 56 56 68 08 00" / "0x68,..." into bytes.
static std::vector<uint8_t> parseHex(const std::string& hexStr) {
    std::vector<uint8_t> bytes;
    const char* p = hexStr.c_str();
    while (*p) {
        while (*p == ' ' || *p == ',' || *p == '\n' || *p == '\t' || *p == '\r') p++;
        if (!*p) break;
        if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) p += 2;
        char* end = nullptr;
        long v = strtol(p, &end, 16);
        if (end == p) { p++; continue; }
        bytes.push_back(static_cast<uint8_t>(v));
        p = end;
    }
    return bytes;
}

static std::string out;

extern "C" EMSCRIPTEN_KEEPALIVE
const char* decode_hex(const char* hex) {
    auto data = parseHex(hex ? hex : "");
    if (data.size() < 6) {
        out = "{\"error\":\"telegram too short\"}";
        return out.c_str();
    }

    uint16_t packet_size = static_cast<uint16_t>(data[1]) + 6;
    if (packet_size > data.size()) {
        out = "{\"error\":\"declared length mismatch\"}";
        return out.c_str();
    }

    const uint8_t start_address = 0x13;  // skip frame header + fixed data header

    JsonDocument doc;
    MBusinoLib payload(254);

    JsonObject headerObj = doc["header"].to<JsonObject>();
    bool headerOk = payload.decodeHeader(data.data(), packet_size, headerObj);

    JsonArray recordsArr = doc["records"].to<JsonArray>();
    uint8_t data_len = static_cast<uint8_t>(packet_size - start_address - 2);
    uint8_t fields = payload.decodeRecords(&data[start_address], data_len, recordsArr);

    doc["slave_address"] = data[5];
    doc["header_ok"] = headerOk;
    doc["records_decoded"] = fields;
    doc["error_code"] = payload.getError();

    out.clear();
    serializeJson(doc, out);
    return out.c_str();
}
