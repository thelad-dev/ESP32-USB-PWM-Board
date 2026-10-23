#pragma once

#include <Arduino.h>

// Minimal DS18B20 bitbang (avoids OneWire GPIO hacks that break on ESP32-C6).
namespace ds18b20 {

inline void writeBit(uint8_t pin, bool bit) {
  if (bit) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
    delayMicroseconds(6);
    pinMode(pin, INPUT_PULLUP);
    delayMicroseconds(64);
  } else {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
    delayMicroseconds(60);
    pinMode(pin, INPUT_PULLUP);
    delayMicroseconds(10);
  }
}

inline bool readBit(uint8_t pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
  delayMicroseconds(3);
  pinMode(pin, INPUT_PULLUP);
  delayMicroseconds(10);
  const bool v = digitalRead(pin);
  delayMicroseconds(50);
  return v;
}

inline bool reset(uint8_t pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
  delayMicroseconds(480);
  pinMode(pin, INPUT_PULLUP);
  delayMicroseconds(70);
  const bool presence = !digitalRead(pin);
  delayMicroseconds(410);
  return presence;
}

inline void writeByte(uint8_t pin, uint8_t v) {
  for (uint8_t i = 0; i < 8; i++) {
    writeBit(pin, v & 0x01);
    v >>= 1;
  }
}

inline uint8_t readByte(uint8_t pin) {
  uint8_t v = 0;
  for (uint8_t i = 0; i < 8; i++) {
    if (readBit(pin)) {
      v |= static_cast<uint8_t>(1U << i);
    }
  }
  return v;
}

inline uint8_t crc8(const uint8_t *data, uint8_t length) {
  uint8_t crc = 0;
  for (uint8_t i = 0; i < length; i++) {
    uint8_t value = data[i];
    for (uint8_t bit = 0; bit < 8; bit++) {
      const uint8_t mix = (crc ^ value) & 0x01;
      crc >>= 1;
      if (mix) {
        crc ^= 0x8C;
      }
      value >>= 1;
    }
  }
  return crc;
}

// Returns true and writes Celsius, or false on bus/sensor error.
// Only one DS18B20 may be connected: onboard U_TEMP or external J_TEMP, never both.
inline bool readCelsius(uint8_t pin, float *outC) {
  if (!reset(pin)) {
    return false;
  }
  writeByte(pin, 0xCC); // SKIP ROM
  writeByte(pin, 0x44); // CONVERT T
  delay(750);

  if (!reset(pin)) {
    return false;
  }
  writeByte(pin, 0xCC);
  writeByte(pin, 0xBE); // READ SCRATCHPAD
  uint8_t scratchpad[9];
  for (uint8_t i = 0; i < 9; i++) {
    scratchpad[i] = readByte(pin);
  }
  if (crc8(scratchpad, 8) != scratchpad[8]) {
    return false;
  }
  const int16_t raw = static_cast<int16_t>((static_cast<uint16_t>(scratchpad[1]) << 8) | scratchpad[0]);
  *outC = static_cast<float>(raw) / 16.0f;
  return true;
}

} // namespace ds18b20
