/*
 * Record-level golden harness (only for the port, not part of the repos)
 * Decodes RAW record bytes (without a telegram frame) and prints the
 * ArduinoJson-Array wie test_decode.cpp aus.
 *
 * Usage: ./test_decode_records "01 FB 01 C8"
 *        echo "01 FB 01 C8" | ./test_decode_records
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
    std::istringstream iss(hexStr);
    std::string token;
    while (iss >> token) {
        if (token.substr(0, 2) == "0x" || token.substr(0, 2) == "0X") token = token.substr(2);
        bytes.push_back(static_cast<uint8_t>(strtol(token.c_str(), nullptr, 16)));
    }
    return bytes;
}

int main(int argc, char* argv[]) {
    std::string hexInput;
    if (argc > 1) hexInput = argv[1];
    else std::getline(std::cin, hexInput);

    auto data = parseHex(hexInput);
    MBusinoLib payload(254);
    JsonDocument jsonBuffer;
    JsonArray root = jsonBuffer.add<JsonArray>();

    uint8_t fields = payload.decodeRecords(data.data(), (uint8_t)data.size(), root);

    printf("Records decoded: %d\n", fields);
    printf("Error code: %d\n", payload.getError());
    printf("\n");
    char jsonBuf[65536] = {0};
    serializeJsonPretty(root, jsonBuf, sizeof(jsonBuf));
    printf("%s\n", jsonBuf);
    return 0;
}
