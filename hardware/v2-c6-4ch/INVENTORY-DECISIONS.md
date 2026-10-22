# Bestand und Bauentscheidungen (WHIN 2026-10-22)

## Modul: ESP32-C6 SuperMini (Captain)

Captain: mit C6 planen, mehr Stueck auf Lager (9x C6 vs 3x C3).

Pinbelegung C6 SuperMini (MakerGO / uebliche Klone, USB oben):

- Links 10 Pins: GPIO16, 17, 0, 1, 2, 3, 4, 5, 6, 7
- Rechts 10 Pins: 5V, GND, 3V3, GPIO20, 19, 18, 15, 14, 9, 8
- Stempel/extra: GPIO21, 22, 23, 12, 13

Das ist **nicht** die C3-SuperMini-Belegung (dort 2x8 und andere Reihenfolge). Gleicher Steckplatz fuer C3 und C6 geht ohne Kompromiss nicht — C6 hat Vorrang, C3 passt nicht auf diese Buchsen.

Sichere GPIOs fuer PWM/Tach (kein Strapping/LED/USB/UART): 0,1,2,3,14,18,19,20. Neunter Pin TEMP = GPIO21 ueber Stempelbuchse `J_IO21`.

802.15.4/Zigbee/Thread am C6: fuer dieses Board ohne Einfluss auf Layout (USB-Strom, Antenne bleibt auf dem Modul).

## Temperatursensor: DS18B20

Vorrat: 2x DS18B20 TO-92, 1x NTC 12W39. Gewaehlt: DS18B20 (digital, vorhanden, 1-Wire). NTC nur Fallback.

## 4-Kanal-MOSFET-PWM-Modul (Bestand)

Das Modul ist ein **Lastschalter auf der Versorgungsleitung** (12 V ein/aus bzw. Last-PWM). Ein 4-Pin-PC-Luefter braucht dagegen ein Open-Collector-/Low-Side-Signal am **PWM-Steuerpin**, waehrend +12 V dauerhaft anliegt. Deshalb bleiben die vier AO3400A auf der Platine; das fertige Modul ersetzt sie nicht.

## Level Converter 2447 / Optokoppler 817

Fuer Tacho: Open-Collector nach GND, Pull-up auf 3,3 V, Serie 1 kΩ, BAT54S-Clamp. Die Steckmodule (I2C-Levelshifter bzw. grosse Optokoppler-Boards) sind fuer Breadboard gedacht, nicht als SMD auf dieser Traegerplatine. On-Board-Diskret bleibt die passende Bauform.

## 100 kΩ

Gate-Pulldowns aus dem Vorrat (100x Metallfilm, Kiste-2 R1-F6). SMD-Footprint 0603 in der BOM; wer THT aus dem Beutel nimmt, verdrahtet freifliegend oder adaptiert — LCSC-Nummer bleibt fuer Nachbestellung/SMD.

## EMI-Filter

Drei DC-EMI-Filter 0–50 V / 4 A vorhanden: optional in Serie vor `J_PWR`, kein Footprint auf dem PCB.
