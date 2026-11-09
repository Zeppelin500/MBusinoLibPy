// Minimal Arduino.h shim so the original C++ MBusinoLib compiles for a host
// / Emscripten target without the Arduino core.
//
// The upstream MBusinoLib repo keeps its own copy of this file in test/, but
// it is not tracked by git - so we vendor the needed subset here to keep the
// WebAssembly build reproducible.
#ifndef ARDUINO_H
#define ARDUINO_H

#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <string>

typedef uint8_t byte;

#define DEC 10
#define HEX 16

inline unsigned long millis() { return 0; }
inline void delay(unsigned long ms) {}

// Minimal String class compatible with Arduino's String (std::string backed).
class String : public std::string {
public:
    String() : std::string() {}
    String(const char* s) : std::string(s ? s : "") {}
    String(const std::string& s) : std::string(s) {}
    String(const String& s) : std::string(s) {}
    String(int val, int base = DEC) : std::string() {
        char buf[32];
        if (base == HEX) snprintf(buf, sizeof(buf), "%x", val);
        else snprintf(buf, sizeof(buf), "%d", val);
        assign(buf);
    }
    String(unsigned int val, int base = DEC) : std::string() {
        char buf[32];
        if (base == HEX) snprintf(buf, sizeof(buf), "%x", val);
        else snprintf(buf, sizeof(buf), "%u", val);
        assign(buf);
    }
    String(double val, int decimals = 2) : std::string() {
        char buf[32];
        snprintf(buf, sizeof(buf), "%.*f", decimals, val);
        assign(buf);
    }
    friend String operator+(const String& a, const char* b) {
        String result(a);
        result.append(b);
        return result;
    }
    friend String operator+(const char* a, const String& b) {
        String result(a);
        result.append(b);
        return result;
    }
};

#endif
