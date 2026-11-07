/*
 * Header-Golden Harness (nur für die Portierung, nicht Teil der Repos)
 * Liest ein Telegramm wie test_decode.cpp und gibt NUR decodeHeader() als JSON aus.
 * Usage: ./test_decode_header "68 56 56 68 ..."
 */
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <iostream>
#include <sstream>
#include <ArduinoJson.h>
#include "MBusinoLib.h"

std::vector<uint8_t> parseHex(const std::string& hexStr) {
    std::vector<uint8_t> bytes;
    std::istringstream iss(hexStr); std::string token;
    while (iss >> token) {
        if (token.substr(0, 2) == "0x" || token.substr(0, 2) == "0X") token = token.substr(2);
        bytes.push_back(static_cast<uint8_t>(strtol(token.c_str(), nullptr, 16)));
    }
    return bytes;
}

int main(int argc, char* argv[]) {
    std::string hexInput;
    if (argc > 1) hexInput = argv[1]; else std::getline(std::cin, hexInput);
    auto data = parseHex(hexInput);
    if (data.size() < 6) { printf("Error: telegram too short\n"); return 1; }
    uint8_t packet_size = data[1] + 6;

    MBusinoLib decode;
    JsonDocument doc;
    JsonObject headerObj = doc.to<JsonObject>();
    bool ok = decode.decodeHeader(data.data(), packet_size, headerObj);
    printf("header_ok: %d\n", ok ? 1 : 0);
    char buf[4096] = {0};
    serializeJsonPretty(headerObj, buf, sizeof(buf));
    printf("%s\n", buf);
    return 0;
}
