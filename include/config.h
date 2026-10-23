#pragma once

#include <Arduino.h>

// ESP32-C6 SuperMini pin map (v2 board, MakerGO-compatible header).
// Safe GPIOs only: avoid strapping 4-9, LED 15, USB 12/13, UART 16/17.
// PWM: low-side MOSFET gate via 100R; Tach: 1k series + 10k to 3V3 + BAT54S clamp.
// TEMP on GPIO21 via stamp pad / J_IO21 (not on the 2x10 side headers).

static constexpr uint8_t FAN_COUNT = 4;

static constexpr uint8_t PIN_FAN_PWM[FAN_COUNT] = {0, 1, 2, 3};
static constexpr uint8_t PIN_FAN_TACH[FAN_COUNT] = {20, 19, 18, 14};
static constexpr uint8_t PIN_TEMP_DQ = 21;

static constexpr uint32_t SERIAL_BAUD = 115200;

static constexpr uint32_t FAN_PWM_HZ = 25000;
static constexpr uint8_t FAN_PWM_RES_BITS = 8;

static constexpr unsigned PULSES_PER_REVOLUTION = 2;
static constexpr uint32_t RPM_SAMPLE_MS = 1000;

// Boot / missing-ESP failsafe in hardware: gate pulldown => MOSFET off => fan full.
static constexpr uint8_t DEFAULT_FAN_PERCENT = 100;
