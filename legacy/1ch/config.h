#pragma once

#include <Arduino.h>

// Anschluss gemäß Schaltung (writeup): Low-Side PWM, Tach mit Pull-up
static constexpr uint8_t PIN_FAN_PWM = 25;   // → Gate Q1 über R1
static constexpr uint8_t PIN_FAN_TACH = 26;  // → Lüfter Tach (Pin 3), R3 nach 3V3

static constexpr uint32_t SERIAL_BAUD = 115200;

// Typische PC-Lüfter-PWM-Frequenz
static constexpr uint32_t FAN_PWM_HZ = 25000;
static constexpr uint8_t FAN_PWM_RES_BITS = 8; // Duty 0–255

// Viele 4-Pin-Lüfter: 2 Tach-Impulse pro Umdrehung (anpassen falls nötig)
static constexpr unsigned PULSES_PER_REVOLUTION = 2;

// Messfenster für RPM (ms)
static constexpr uint32_t RPM_SAMPLE_MS = 1000;
