#include <Arduino.h>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include "config.h"

#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 2
#endif

#if ESP_ARDUINO_VERSION_MAJOR >= 3
#define LEDC_ATTACH(pin, freq, res) ledcAttach((pin), (freq), (res))
#define LEDC_WRITE(pin, duty)       ledcWrite((pin), (duty))
#else
static constexpr uint8_t kLedcChannel = 0;
#define LEDC_ATTACH(pin, freq, res) \
  do {                               \
    ledcSetup(kLedcChannel, (freq), (res)); \
    ledcAttachPin((pin), kLedcChannel);     \
  } while (0)
#define LEDC_WRITE(pin, duty) ledcWrite(kLedcChannel, (duty))
#endif

static volatile uint32_t s_tachPulseTotal = 0;

void IRAM_ATTR tachIsr() { s_tachPulseTotal++; }

static void setupPwm() {
  LEDC_ATTACH(PIN_FAN_PWM, FAN_PWM_HZ, FAN_PWM_RES_BITS);
  LEDC_WRITE(PIN_FAN_PWM, 0);
}

static void setFanDutyPercent(unsigned percent) {
  if (percent > 100) {
    percent = 100;
  }
  const uint32_t maxDuty = (1U << FAN_PWM_RES_BITS) - 1;
  const uint32_t duty = (percent * maxDuty) / 100;
  LEDC_WRITE(PIN_FAN_PWM, duty);
}

static uint8_t s_dutyPercent = 0;
static float s_lastRpm = 0;

static void updateRpmEstimate() {
  static uint32_t t0 = 0;
  static uint32_t pulses0 = 0;

  const uint32_t now = millis();
  if (t0 == 0) {
    t0 = now;
    pulses0 = s_tachPulseTotal;
    return;
  }

  const uint32_t dt = now - t0;
  if (dt < RPM_SAMPLE_MS) {
    return;
  }

  noInterrupts();
  const uint32_t pulsesNow = s_tachPulseTotal;
  interrupts();

  const uint32_t delta = pulsesNow - pulses0;
  pulses0 = pulsesNow;
  t0 = now;

  if (delta == 0 || PULSES_PER_REVOLUTION == 0) {
    s_lastRpm = 0;
    return;
  }

  const float revs = static_cast<float>(delta) / static_cast<float>(PULSES_PER_REVOLUTION);
  const float minutes = static_cast<float>(dt) / 60000.0f;
  s_lastRpm = (minutes > 0) ? (revs / minutes) : 0;
}

static void printHelp() {
  Serial.println(F("Befehle (115200 Baud):"));
  Serial.println(F("  PWM <0-100>  Soll-Duty in %"));
  Serial.println(F("  RPM          letzte Drehzahl (1s-Fenster)"));
  Serial.println(F("  ?            wie RPM"));
  Serial.println(F("  STATUS       PWM-% und RPM"));
}

static void handleLine(const char *line) {
  while (*line == ' ' || *line == '\t') {
    line++;
  }
  if (*line == '\0') {
    return;
  }

  char cmd[8];
  unsigned n = 0;
  while (line[n] && line[n] != ' ' && line[n] != '\t' && n < sizeof(cmd) - 1) {
    cmd[n] = static_cast<char>(std::tolower(static_cast<unsigned char>(line[n])));
    n++;
  }
  cmd[n] = '\0';

  while (line[n] == ' ' || line[n] == '\t') {
    n++;
  }

  if (strcmp(cmd, "pwm") == 0) {
    int v = atoi(line + n);
    if (v < 0) {
      v = 0;
    }
    if (v > 100) {
      v = 100;
    }
    s_dutyPercent = static_cast<unsigned>(v);
    setFanDutyPercent(s_dutyPercent);
    Serial.print(F("OK PWM "));
    Serial.println(s_dutyPercent);
    return;
  }

  if (strcmp(cmd, "rpm") == 0 || strcmp(cmd, "?") == 0) {
    Serial.print(F("RPM "));
    Serial.println(s_lastRpm, 0);
    return;
  }

  if (strcmp(cmd, "status") == 0) {
    Serial.print(F("PWM "));
    Serial.print(s_dutyPercent);
    Serial.print(F("%  RPM "));
    Serial.println(s_lastRpm, 0);
    return;
  }

  if (strcmp(cmd, "help") == 0 || strcmp(cmd, "h") == 0) {
    printHelp();
    return;
  }

  Serial.println(F("ERR unbekannt — HELP"));
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(100);

  pinMode(PIN_FAN_TACH, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_FAN_TACH), tachIsr, FALLING);

  setupPwm();
  setFanDutyPercent(0);

  Serial.println();
  Serial.println(F("ESP32 USB PWM / Tacho — bereit"));
  printHelp();
}

void loop() {
  updateRpmEstimate();

  static String buf;
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      buf.trim();
      if (buf.length() > 0) {
        handleLine(buf.c_str());
      }
      buf = "";
      continue;
    }
    if (buf.length() < 96) {
      buf += c;
    }
  }
}
