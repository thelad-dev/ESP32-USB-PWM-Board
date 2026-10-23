#include <Arduino.h>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include "config.h"
#include "ds18b20.h"

#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 2
#endif

static void pwmAttach(uint8_t ch, uint8_t pin) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch;
  ledcAttach(pin, FAN_PWM_HZ, FAN_PWM_RES_BITS);
#else
  ledcSetup(ch, FAN_PWM_HZ, FAN_PWM_RES_BITS);
  ledcAttachPin(pin, ch);
#endif
}

static void pwmWrite(uint8_t ch, uint8_t pin, uint32_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch;
  ledcWrite(pin, duty);
#else
  (void)pin;
  ledcWrite(ch, duty);
#endif
}

static volatile uint32_t s_tachPulseTotal[FAN_COUNT] = {0};

void IRAM_ATTR tachIsr0() { s_tachPulseTotal[0]++; }
void IRAM_ATTR tachIsr1() { s_tachPulseTotal[1]++; }
void IRAM_ATTR tachIsr2() { s_tachPulseTotal[2]++; }
void IRAM_ATTR tachIsr3() { s_tachPulseTotal[3]++; }

static void (*const kTachIsr[FAN_COUNT])() = {tachIsr0, tachIsr1, tachIsr2, tachIsr3};

static uint8_t s_dutyPercent[FAN_COUNT];
static float s_lastRpm[FAN_COUNT];
static float s_lastTempC = NAN;
static bool s_tempOk = false;
static constexpr uint32_t AUTO_TEMP_SAMPLE_MS = 1000;
static constexpr uint32_t MANUAL_OVERRIDE_MS = 5UL * 60UL * 1000UL;
static constexpr float TEMP_HYSTERESIS_C = 2.0f;
static constexpr float TEMP_BAND_C[] = {40.0f, 45.0f, 50.0f, 55.0f};
static constexpr uint8_t FAN_AUTO_DUTY[] = {35, 50, 65, 80, 100};
static uint8_t s_autoBand = 0;
static uint8_t s_manualDutyPercent[FAN_COUNT];
static uint32_t s_manualOverrideUntil[FAN_COUNT];
static bool s_manualActive[FAN_COUNT] = {false};
static uint32_t s_nextTempSampleMs = 0;

static void setupPwm() {
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    pwmAttach(i, PIN_FAN_PWM[i]);
  }
}

// percent = desired fan speed. Low-side MOSFET: GPIO high => PWM pin low => slow.
static void setFanDutyPercent(uint8_t ch, unsigned percent) {
  if (ch >= FAN_COUNT) {
    return;
  }
  if (percent > 100) {
    percent = 100;
  }
  s_dutyPercent[ch] = static_cast<uint8_t>(percent);
  const uint32_t maxDuty = (1U << FAN_PWM_RES_BITS) - 1;
  const uint32_t inverted = ((100U - percent) * maxDuty) / 100U;
  pwmWrite(ch, PIN_FAN_PWM[ch], inverted);
}

static void setAllFans(unsigned percent) {
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    setFanDutyPercent(i, percent);
  }
}

static uint8_t automaticDutyForTemperature(float temperatureC) {
  while (s_autoBand < 4 && temperatureC >= TEMP_BAND_C[s_autoBand]) {
    s_autoBand++;
  }
  while (s_autoBand > 0 && temperatureC < TEMP_BAND_C[s_autoBand - 1] - TEMP_HYSTERESIS_C) {
    s_autoBand--;
  }
  return FAN_AUTO_DUTY[s_autoBand];
}

static bool manualOverrideActive(uint8_t ch, uint32_t now) {
  return s_manualActive[ch] && static_cast<int32_t>(s_manualOverrideUntil[ch] - now) > 0;
}

static void applyFanControl(uint32_t now) {
  if (!s_tempOk) {
    setAllFans(100);
    return;
  }
  const unsigned automaticDuty = automaticDutyForTemperature(s_lastTempC);
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    if (manualOverrideActive(i, now)) {
      setFanDutyPercent(i, s_manualDutyPercent[i]);
    } else {
      s_manualActive[i] = false;
      setFanDutyPercent(i, automaticDuty);
    }
  }
}

static void setManualFanDutyPercent(uint8_t ch, unsigned percent) {
  if (ch >= FAN_COUNT) {
    return;
  }
  s_manualDutyPercent[ch] = static_cast<uint8_t>(percent > 100 ? 100 : percent);
  s_manualActive[ch] = true;
  s_manualOverrideUntil[ch] = millis() + MANUAL_OVERRIDE_MS;
  applyFanControl(millis());
}

static void setManualAllFans(unsigned percent) {
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    setManualFanDutyPercent(i, percent);
  }
}

static void updateRpmEstimate() {
  static uint32_t t0 = 0;
  static uint32_t pulses0[FAN_COUNT] = {0};

  const uint32_t now = millis();
  if (t0 == 0) {
    t0 = now;
    noInterrupts();
    for (uint8_t i = 0; i < FAN_COUNT; i++) {
      pulses0[i] = s_tachPulseTotal[i];
    }
    interrupts();
    return;
  }

  const uint32_t dt = now - t0;
  if (dt < RPM_SAMPLE_MS) {
    return;
  }

  uint32_t pulsesNow[FAN_COUNT];
  noInterrupts();
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    pulsesNow[i] = s_tachPulseTotal[i];
  }
  interrupts();

  const float minutes = static_cast<float>(dt) / 60000.0f;
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    const uint32_t delta = pulsesNow[i] - pulses0[i];
    pulses0[i] = pulsesNow[i];
    if (delta == 0 || PULSES_PER_REVOLUTION == 0 || minutes <= 0) {
      s_lastRpm[i] = 0;
      continue;
    }
    const float revs =
        static_cast<float>(delta) / static_cast<float>(PULSES_PER_REVOLUTION);
    s_lastRpm[i] = revs / minutes;
  }
  t0 = now;
}

static void sampleTemperature() {
  float t = 0;
  if (!ds18b20::readCelsius(PIN_TEMP_DQ, &t) || !(t >= -55.0f && t <= 125.0f)) {
    s_tempOk = false;
    s_lastTempC = NAN;
    return;
  }
  s_tempOk = true;
  s_lastTempC = t;
}

static void printHelp() {
  Serial.println(F("Befehle (115200 Baud), 4 Kanaele + Temp:"));
  Serial.println(F("  PWM 0 / PWM <5-100>   alle Kanaele"));
  Serial.println(F("  PWM <1-4> <0-100>     ein Kanal"));
  Serial.println(F("  PWM ALL <0-100>       alle Kanaele (inkl. 1-4%)"));
  Serial.println(F("  PWM setzt Handbetrieb fuer 5 Minuten"));
  Serial.println(F("  RPM [1-4]             Drehzahl"));
  Serial.println(F("  TEMP                  Kuehlkoerper C"));
  Serial.println(F("  STATUS                PWM/RPM/Temp"));
  Serial.println(F("  HELP"));
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
    const char *arg = line + n;
    while (*arg == ' ' || *arg == '\t') {
      arg++;
    }
    bool explicitAll = std::tolower(static_cast<unsigned char>(arg[0])) == 'a' &&
                       std::tolower(static_cast<unsigned char>(arg[1])) == 'l' &&
                       std::tolower(static_cast<unsigned char>(arg[2])) == 'l' &&
                       (arg[3] == '\0' || arg[3] == ' ' || arg[3] == '\t');
    if (explicitAll) {
      arg += 3;
      while (*arg == ' ' || *arg == '\t') {
        arg++;
      }
      char *end = nullptr;
      const long duty = strtol(arg, &end, 10);
      while (end && (*end == ' ' || *end == '\t')) {
        end++;
      }
      if (end == arg || !end || *end != '\0' || duty < 0 || duty > 100) {
        Serial.println(F("ERR PWM Syntax"));
        return;
      }
      setManualAllFans(static_cast<unsigned>(duty));
      Serial.print(F("OK PWM ALL "));
      Serial.println(duty);
      return;
    }

    char *end = nullptr;
    const long first = strtol(arg, &end, 10);
    if (end == arg) {
      Serial.println(F("ERR PWM Syntax"));
      return;
    }
    while (*end == ' ' || *end == '\t') {
      end++;
    }
    if (*end == '\0') {
      if (first >= 1 && first <= FAN_COUNT) {
        Serial.println(F("ERR PWM duty required for channel"));
        return;
      }
      if (first < 0 || first > 100) {
        Serial.println(F("ERR PWM range 0-100"));
        return;
      }
      setManualAllFans(static_cast<unsigned>(first));
      Serial.print(F("OK PWM ALL "));
      Serial.println(first);
      return;
    }

    if (first < 1 || first > FAN_COUNT) {
      Serial.println(F("ERR Kanal 1-4"));
      return;
    }
    char *dutyEnd = nullptr;
    const long duty = strtol(end, &dutyEnd, 10);
    if (dutyEnd == end) {
      Serial.println(F("ERR PWM Syntax"));
      return;
    }
    while (*dutyEnd == ' ' || *dutyEnd == '\t') {
      dutyEnd++;
    }
    if (*dutyEnd != '\0' || duty < 0 || duty > 100) {
      Serial.println(F("ERR PWM Syntax"));
      return;
    }
    setManualFanDutyPercent(static_cast<uint8_t>(first - 1), static_cast<unsigned>(duty));
    Serial.print(F("OK PWM"));
    Serial.print(first);
    Serial.print(F(" "));
    Serial.println(duty);
    return;
  }

  if (strcmp(cmd, "rpm") == 0 || strcmp(cmd, "?") == 0) {
    if (line[n] != '\0') {
      char *end = nullptr;
      const long parsed = strtol(line + n, &end, 10);
      while (end && (*end == ' ' || *end == '\t')) {
        end++;
      }
      if (end == line + n || !end || *end != '\0' || parsed < 1 || parsed > FAN_COUNT) {
        Serial.println(F("ERR Kanal 1-4"));
        return;
      }
      const int ch = static_cast<int>(parsed);
      Serial.print(F("RPM"));
      Serial.print(ch);
      Serial.print(F(" "));
      Serial.println(s_lastRpm[ch - 1], 0);
      return;
    }
    for (uint8_t i = 0; i < FAN_COUNT; i++) {
      Serial.print(F("RPM"));
      Serial.print(i + 1);
      Serial.print(F(" "));
      Serial.print(s_lastRpm[i], 0);
      if (i + 1 < FAN_COUNT) {
        Serial.print(F("  "));
      }
    }
    Serial.println();
    return;
  }

  if (strcmp(cmd, "temp") == 0) {
    sampleTemperature();
    applyFanControl(millis());
    if (!s_tempOk) {
      Serial.println(F("TEMP ERR"));
      return;
    }
    Serial.print(F("TEMP "));
    Serial.println(s_lastTempC, 2);
    return;
  }

  if (strcmp(cmd, "status") == 0) {
    sampleTemperature();
    applyFanControl(millis());
    for (uint8_t i = 0; i < FAN_COUNT; i++) {
      Serial.print(F("CH"));
      Serial.print(i + 1);
      Serial.print(F(" PWM "));
      Serial.print(s_dutyPercent[i]);
      Serial.print(F("% RPM "));
      Serial.print(s_lastRpm[i], 0);
      Serial.print(F(" "));
      if (!s_tempOk) {
        Serial.println(F("FAILSAFE"));
      } else if (manualOverrideActive(i, millis())) {
        Serial.println(F("MANUAL"));
      } else {
        Serial.println(F("AUTO"));
      }
    }
    if (s_tempOk) {
      Serial.print(F("TEMP "));
      Serial.println(s_lastTempC, 2);
    } else {
      Serial.println(F("TEMP ERR"));
    }
    return;
  }

  if (strcmp(cmd, "help") == 0 || strcmp(cmd, "h") == 0) {
    printHelp();
    return;
  }

  Serial.println(F("ERR unbekannt - HELP"));
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(200);

  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    pinMode(PIN_FAN_TACH[i], INPUT);
    attachInterrupt(digitalPinToInterrupt(PIN_FAN_TACH[i]), kTachIsr[i], FALLING);
    s_dutyPercent[i] = DEFAULT_FAN_PERCENT;
    s_lastRpm[i] = 0;
  }

  setupPwm();
  setAllFans(DEFAULT_FAN_PERCENT);
  pinMode(PIN_TEMP_DQ, INPUT_PULLUP);
  for (uint8_t i = 0; i < FAN_COUNT; i++) {
    s_manualDutyPercent[i] = DEFAULT_FAN_PERCENT;
  }

  Serial.println();
  Serial.println(F("ESP32-C6 USB PWM/Tacho 4ch + Temp - bereit"));
  printHelp();
}

void loop() {
  updateRpmEstimate();

  const uint32_t now = millis();
  if (static_cast<int32_t>(now - s_nextTempSampleMs) >= 0) {
    sampleTemperature();
    applyFanControl(millis());
    s_nextTempSampleMs = millis() + AUTO_TEMP_SAMPLE_MS;
  }

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
