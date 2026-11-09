/*
 * Standalone M-Bus telegram decoder test
 * Compiles without Arduino hardware
 *
 * Usage: ./test_decode "68 56 56 68 08 00 ..."
 *        ./test_decode < file_with_hex.txt
 */

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <iostream>
#include <sstream>

// Include ArduinoJson
#include <ArduinoJson.h>

// Include MBusinoLib
#include "MBusinoLib.h"

// Parse hex string like "68 56 56 68 08 00" into byte vector
std::vector<uint8_t> parseHex(const std::string& hexStr) {
    std::vector<uint8_t> bytes;
    std::istringstream iss(hexStr);
    std::string token;
    while (iss >> token) {
        if (token.substr(0, 2) == "0x" || token.substr(0, 2) == "0X")
            token = token.substr(2);
        bytes.push_back(static_cast<uint8_t>(strtol(token.c_str(), nullptr, 16)));
    }
    return bytes;
}

int main(int argc, char* argv[]) {
    std::string hexInput;

    if (argc > 1) {
        hexInput = argv[1];
    } else {
        // Read from stdin
        std::getline(std::cin, hexInput);
    }

    auto data = parseHex(hexInput);
    if (data.size() < 6) {
        fprintf(stderr, "Error: telegram too short (%zu bytes)\n", data.size());
        return 1;
    }

    // M-Bus frame: 68 LL LL 68 C A CI [data] 16
    // data[1] = length, data[5] = slave address
    size_t packet_size = data[1] + 6;
    uint8_t slave_address = data[5];
    uint8_t start_address = 0x13; // Standard: skip header + fixed data

    if (packet_size > data.size()) {
        fprintf(stderr, "Error: declared length %d but only %zu bytes provided\n",
                packet_size, data.size());
        return 1;
    }

    MBusinoLib payload(254);
    JsonDocument jsonBuffer;
    JsonArray root = jsonBuffer.add<JsonArray>();

    uint8_t data_len = packet_size - start_address - 2;
    uint8_t fields = payload.decode(&data[start_address], data_len, root);

    // Output
    printf("Slave Address: %d\n", slave_address);
    printf("Records decoded: %d\n", fields);
    printf("Error code: %d\n", payload.getError());
    printf("\n");

    // JSON output
    char jsonBuf[4096] = {0};
    serializeJsonPretty(root, jsonBuf, sizeof(jsonBuf));
    printf("%s\n\n", jsonBuf);

    // Parsed output
    for (uint8_t i = 0; i < fields; i++) {
        const char* name = root[i]["name"] | "";
        const char* units = root[i]["units"] | "";
        double value = root[i]["value_scaled"].as<double>();
        const char* valueString = root[i]["value_string"] | "";
        const char* vif = root[i]["vif"] | "";
        uint8_t code = root[i]["code"].as<int>();

        printf("[%d] %s (%s)", i+1, name, vif);
        if (strlen(valueString) > 0)
            printf(" = %s", valueString);
        else
            printf(" = %.6g", value);
        if (strlen(units) > 0)
            printf(" %s", units);
        printf("\n");
    }

    return 0;
}
