# v2: 4-Kanal PWM/Tacho + DS18B20 (ESP32-C6 SuperMini)

- `bom.csv` — Stueckliste mit LCSC und Spalte Stock (vorhanden/zu bestellen)
- `INVENTORY-DECISIONS.md` — C6 vs C3, MOSFET-Modul, Levelshifter
- `fab/JLCPCB-gerbers-esp32-c6-pwm-4ch.zip` — Fertigungsdaten
- `fab/cpl-smd.csv` — optionale SMD-Platzierung
- `ORDER.md` / `HAND_SOLDER.md`
- `kicad/esp32-c6-pwm-4ch.kicad_pcb`
- `scripts/build_pcb.py`

Schaltung: `../../writeup.md` Teil B.

Am 1-Wire-Bus darf immer nur ein DS18B20 angeschlossen sein: entweder der onboard
Sensor U_TEMP oder eine externe Sonde an J_TEMP, niemals beide gleichzeitig.
