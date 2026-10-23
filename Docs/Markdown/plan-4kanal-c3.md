# Plan: 4-Kanal PWM/Tacho + Temp auf ESP32-C3 Supermini

## Annahme

- Das bestehende 1-Kanal-Design (writeup, BOM, Firmware) bleibt als Referenz und wird erweitert, nicht ersetzt.
- `hardware/kicad/` fehlt im Repo trotz Erwaehnung im Brief; Schaltung steht nur in writeup/BOM. Neuaufbau der KiCad-Dateien fuer die 4-Kanal-Variante ist noetig, 1-Kanal-Doku bleibt.
- ESP32-C3 Supermini hat genug GPIOs fuer 4xPWM + 4xTach + 1xTemp (ohne IO8/IO9 Strapping, ohne IO2 LED).
- Bestellung zielt auf JLCPCB (Gerber + BOM + optional Handbestueckung).
- KiCad ist lokal nicht installiert und wird fuer Gerber-Export nachgezogen, falls sudo greift; sonst Gerber per Skript aus `.kicad_pcb`.

## Zwei Wege

1. **Auftragsweg:** Vier Kanaele wie bisher (IRLZ44N TO-220, 4-Pin-Header), Temp-Sensor, C3 gesteckt, Fertigungsarchiv.
2. **Alternative (genommen):** Pro Kanal SMD-Logic-FET (z. B. AO3400A) statt TO-220 - PWM-Leitung fuehrt nur Gate-Strom am Luefter-PWM-Eingang, TO-220 ist Overkill und blockiert Platinenflaeche bei vier Kanaelen. 1-Kanal-Doku und Prinzip (Low-Side, Gate 100R/100k, Tach-Pull-up) bleiben; Bauform wechselt begruendet.

**Gelassen:** Vier IRLZ44N vertical auf einer Handloet-Platine - funktioniert, aber unnoetig gross und teuer fuer Signalstrom.

## Ablehnung

- Tach nur mit 3V3-Pull-up ohne Clamp: bei fremdem 12V-Pull-up am Tach zerstoert den C3.
- Fail-safe nur in Firmware: ESP fehlt oder haengt mit Gate high → Luefter aus.
- LCSC-Nummern geraten: Bestellung scheitert oder falsche Teile.
- Pinbelegung mit nicht existierenden C3-GPIOs.
- Altes 1-Kanal-Material loeschen ohne Begruendung.

## Nachweis

- Pinliste C3 vs. benoetigte Signale (Tabelle in writeup/README).
- BOM: jede LCSC-Nummer gegen LCSC/DeepAPI oder Herstellerseite geprueft; ungepruefte Preise gekennzeichnet.
- Gerber-ZIP existiert und enthaelt Edge/Copper/Mask/Silk/Drill.
- Firmware: `pio run` fuer `esp32-c3-devkitm-1` oder Aequivalent (falls pio verfuegbar), sonst Syntax-Review + dokumentierte Luecke.
- Schaltungsbeschreibung zeigt Tach-Schutz, Verpolungsschutz, Fail-safe (Gate-Pulldown → MOSFET aus → Luefter-PWM offen → Vollgas nach Intel-4-Pin-Verhalten).

## Grenze

- Keine Bauteilbestellung, keine Konten, kein Merge, kein Push auf default.
- Keine fertige PID-/Kurvenregelung; nur Grundstock Temp lesen + 4 Kanaele setzen.
- 1-Kanal-Firmware-Env und writeup-Abschnitte zum Altstand bleiben lesbar; Erweiterung als v2 / C3-4ch.
