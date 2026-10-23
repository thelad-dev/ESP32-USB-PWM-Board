ESP32 PWM-/Tacho-Board (4-Pin-Luefter, USB-Serial)

Dieses Dokument beschreibt die **v1-Schaltung (1 Kanal)** und die **v2-Erweiterung (4 Kanal + Temperatur, ESP32-C6 SuperMini)**.

---

## Teil A - v1 (1 Kanal, DevKitC)

Dokumentation fuer ein kleines Board: ESP32 per USB (Serial Monitor / eigenes Tool), PWM und Tacho (RPM) fuer einen 4-Pin-PC-Luefter (+12V, GND, Tach, PWM).

1. Ziel und Prinzip
USB am ESP32 → Kommunikation (z. B. Baud 115200) fuer Soll-PWM und Auslesen der Drehzahl.
Ein Kanal (leicht erweiterbar auf mehr GPIOs).
Am Luefter ist der PWM-Eingang typisch als Open-Drain/Open-Collector von der „Motherboard-Seite“ gedacht: High ueber Pull-up (oft im Luefter), Low durch Ziehen nach GND.
Der ESP32 soll die Leitung nicht mit 3,3 V Push-Pull direkt treiben, wenn der High-Pegel >3,3 V sein kann → Low-Side-Schalter mit N-MOSFET: Drain an Luefter-PWM, Source an GND.
2. MOSFET (Standard: IRLZ44N)
Teil Typ Bemerkung
Q1
IRLZ44NPBF
Logic-Level N-Kanal, TO-220, Serie „Z“, fuer Ansteuerung aus 3,3 V-GPIO geeignet. Viel Stromreserve; der PWM-Pin des Luefters ist kein Motor-Hauptstrom, aber der FET ist robust und gut dokumentiert.
Gate-Beschaltung

R1: ca. 100 Ω zwischen GPIO und Gate (daempft Ringing, schont ESP-Ausgang).
R2: ca. 100 kΩ Gate → GND (Pulldown, definiert AUS beim Boot).
(Bei sehr hoher PWM-Frequenz und Problemen mit Flanken ggf. Treiber diskutieren; fuer typ. ~25 kHz PC-Luefter meist nicht noetig.)

Alternativen (spaeter SMD/kleiner): IRLML6344, AO3400A - hier ist IRLZ44N die feste Empfehlung fuer v1.

3. Tacho (RPM)
Typisch Open-Collector am Luefter: Impulse nach GND.
Am ESP32: R3 = 10 kΩ Pull-up auf 3,3 V, Zwischenpunkt an GPIO (mit Interrupt fuer Flanken / Pulszähler).
Wichtig: Mit dem Oszilloskop pruefen, ob auf der Tach-Leitung kein dauerhaftes 12 V auf den ESP-Pin kommt. Manche Aufbauten erwarten Motherboard-Pull-up auf hoehere Spannung → dann Spannungsteiler, Z-Diode/Clamp oder Optokoppler statt direktem 3,3 V-PU.

4. Stromversorgung und Masse
+12 V fuer den Luefter (Netzteil dimensionieren, ggf. Sicherung/TVS nach Bedarf).
ESP32 z. B. ueber USB (DevKit) oder eigenen 3,3 V-Regler auf dem Board.
Gemeinsame Masse: USB-GND, 12 V-GND, Luefter-GND, MOSFet-Source niederimpedant verbinden (Stern/Masseflaeche).
5. Luefter-Pinbelegung (typisch 4-Pin)
Pin Funktion
1
+12V
2
GND
3
Tach
4
PWM
Stecker/Keying je nach Gehaeuse pruefen → Datenblatt Luefter.

6. Blockschaltbild (ASCII)
        USB                    +12V (Luefter)
         │                          │
    ┌────┴────┐                     │
    │  ESP32  │                     │
    │ 3V3 GND │                     │
    └─┬──┬──┬─┘                     │
      │  │  │                       │
      │  │  └── GPIO_PWM ──[100R]── Gate Q1 (IRLZ44N)
      │  │              └── 100k ── GND
      │  │                     │
      │  │              Drain ──┼── Luefter PWM (Pin 4)
      │  │              Source ─┴── GND
      │  │
      │  └── GPIO_TACH ──[10k]── 3V3
      │              └── Luefter Tach (Pin 3)
      │
      └────────────── GND ──────── Luefter GND (Pin 2)
Luefter Pin 1: +12V
7. Serial / Firmware (Vorschlag)
Baud: z. B. 115200
Beispiel-Befehle: PWM 0 … PWM 100 (Duty in %), RPM oder ? fuer letzte Messung.
PWM-Ausgang: LEDC o. ae., Frequenz typ. ~25 kHz (PC-Luefter ueblich).
Tacho: 2 Impulse/Umdrehung ist bei vielen Lueftern ueblich - im Code als Konstante, ggf. pro Modell anpassen.
Firmware-Archiv: `legacy/1ch/`.
8. Abschnitt fuer KiCad / Fertigung (v1)
KiCad liest kein Markdown direkt als Schaltplan. Praktisch:

8.1 BOM als CSV
Siehe `hardware/bom-1channel.csv` (LCSC damals leer - bewusst; Bestellung laeuft ueber v2).

8.2 Netzliste / Signale (Referenz fuers Zeichnen in Eeschema)
Netname Beschreibung
+3V3
3,3 V (R3 Pull-up, optional C1)
GND
ESP-GND, Q1 Source, Luefter GND, R2
+12V
Luefter Pin 1
PWM_DRV
GPIO → R1 → Gate Q1
FAN_PWM
Q1 Drain ↔ Luefter Pin 4
FAN_TACH
GPIO ↔ Mitte R3 ↔ Luefter Pin 3
8.3 Hinweis „KiCad importieren“
Eine vollstaendige .kicad_sch per Copy-Paste aus dem Chat ist fehleranfaellig (UUIDs, Symbole). Sinnvoll: neues Projekt in KiCad anlegen und diese Netze + BOM abarbeiten.

9. Checkliste Inbetriebnahme (v1)

 Tach-Leitung vermessen: kein gefaehrlicher Pegel fuer 3,3 V-GPIO.

 PWM-Frequenz und Duty im sinnvollen Bereich fuer den Luefter.

 gemeinsame Masse 12 V / Logik / USB.

 Optional: Sicherung / TVS auf 12 V, Kondensator nahe Luefteranschluss.

---

## Teil B - v2 (4 Kanaele + Temperatur, ESP32-C6 SuperMini)

Ziel: vier unabhaengige Luefterkanaele (PWM out + Tach in), ein Temperatureingang am Kuehlkoerper (SAS-Karte / pxmx), ESP32-C6 SuperMini **gesteckt** (Buchsenleisten), bestellbares PCB.

### 10. Warum Erweiterung statt Neuanfang

v1-Prinzip bleibt: Low-Side-N-MOSFET auf Luefter-PWM, Gate 100 Ω / 100 kΩ Pulldown, gemeinsame Masse, USB-Serial. Geaendert werden Modul (C6 SuperMini), Kanalzahl, Tach-Schutz, 12 V-Absicherung, Fail-safe-Klarstellung und Temperatureingang. TO-220 IRLZ44N wird pro Kanal durch **AO3400A (SOT-23)** ersetzt: der Luefter-PWM-Pin fuehrt nur Signalstrom; vier TO-220 waeren unnoetig gross.

### 11. Temperatursensor: DS18B20 (1-Wire)

Entscheidung: **DS18B20+ (TO-92, LCSC C9753)** am Kuehlkoerper, optional ueber 3-Pin-Header mit Kabelsonde.

Begruendung gegen NTC: keine Widerstandsteiler-Kalibrierung, digitale °C-Werte, wasserdichte Sonden ueblich, ein GPIO reicht, ±0,5 °C reicht fuer Luefterkurven am Kuehlkoerper (keine Laborgenauigkeit noetig). NTC waere billiger, braucht aber ADC und Kalibrierung.

Beschaltung: VDD→3V3, GND→GND, DQ→GPIO21 mit 4,7 kΩ Pull-up. Onboard TO-92 und paralleler Header `J_TEMP` (GND / DQ / 3V3) teilen einen Bus; es darf immer nur einer von beiden DS18B20 angeschlossen sein.

### 11b. Bestand: MOSFET-Modul und Levelshifter

Siehe `hardware/v2-c6-4ch/INVENTORY-DECISIONS.md`. Kurz: fertiges 4-Kanal-MOSFET-PWM-Modul schaltet die **Lastversorgung**, nicht den Luefter-PWM-Steuerpin - bleibt ungenutzt fuer die Kanaele. 2447-Levelshifter und 817-Optokoppler-Module bleiben Steckmodule; Tacho-Schutz ist diskret auf dem Board (1k + 10k + BAT54S).

### 12. ESP32-C6 Pinbudget und Belegung

Entscheidung: C6 statt C3 (Bestand). C6-SuperMini hat **2×10** Header und andere Pinreihenfolge als C3-SuperMini - **kein gemeinsamer Steckplatz**.

Sichere GPIOs (kein Strapping 4-9, kein LED 15, kein USB 12/13, kein UART 16/17):

| Funktion | GPIO | Hinweis |
|----------|------|---------|
| PWM1…PWM4 | 0, 1, 2, 3 | LEDC ~25 kHz |
| TACH1…TACH4 | 20, 19, 18, 14 | Interrupt FALLING |
| TEMP DQ | 21 | Stempelpad / J_IO21, 1-Wire |

Buchsen: 2× 1×10 Female, Reihenabstand ~15,24 mm; plus 1×1 fuer GPIO21. Modul vor dem Stecken messen.

USB-CDC am Modul. 802.15.4 am C6 aendert das Luefter-Layout nicht.

### 13. Fail-safe in der Schaltung (nicht nur Firmware)

Intel-4-Pin: offener PWM-Eingang → interner Pull-up → Luefter laeuft **voll**.

- Gate-Pulldown 100 kΩ → MOSFET aus, wenn ESP fehlt, steckt, oder Pin High-Z (Reset) → Drain offen → PWM offen → **Vollgas**.
- Firmware startet mit 100 % Soll (MOSFET weitgehend aus), nicht mit 0 %.
- Risiko Rest: GPIO haengt dauerhaft High (MOSFET an → Luefter langsam/aus). Selten nach Watchdog-Reset (Pins wieder High-Z). Kein externes Hardware-WDT auf diesem Board; Folgearbeit moeglich.

### 14. Tach-Schutz (Open-Collector vs. 12 V)

Pro Kanal:

```
Fan Tach --[1k]--+-- GPIO
                 +--[10k]-- 3V3
                 +-- BAT54S (Anode am GPIO-Knoten, Kathode 3V3)
```

Kein 12 V-Pull-up auf dem Board. Serie begrenzt Stoerstrom; Schottky clamp begrenzt GPIO auf ~3,3 V + Vf. Board nicht parallel an Motherboard-Tach mit 12 V-PU haengen.

### 15. Netzteil: Verpolung und Kurzschluss

```
J_PWR(+12V) --[PTC 3A/30V]--+12V_F-- Fans Pin1
                            +-- SS34 Kathode (Anode GND)   // Verpolung → PTC
                            +-- SMAJ15A                    // TVS
                            +-- 10u bulk
GND gemeinsam mit Logik/USB-Masse.
```

ESP-Versorgung weiter ueber USB am Modul (kein 12→3V3-Regler auf dem Board).

### 16. Anschluesse

- 4× 2510-4A / 2,54 mm 4-Pin-Header (PC-Luefter-kompatibel), Pin 1=+12V … 4=PWM.
- 1× Schraubklemme 5,08 mm 2P fuer 12 V / GND.
- 2× Female 1×10 fuer C6 SuperMini.
- 1× 1×3 fuer optionale Temp-Sonde.

### 17. Blockschaltbild v2 (ein Kanal stellvertretend)

```
 USB-C (am Modul)              J_PWR +12V --PTC-- +12V_F ---- Fan1..4 Pin1
        │                                         │
   ESP32-C6 SuperMini                             + SS34/TVS/10u → GND
   (in Buchsen)
        │
   GPIOx --[100R]-- Gate AO3400A --[100k]-- GND
                      Drain --------------- Fan PWM
                      Source -------------- GND
   GPIOy --[1k]-- from Fan Tach; 10k→3V3; BAT54S→3V3
   GPIO21 -- DS18B20 DQ (4.7k→3V3)
```

### 18. Fertigung und BOM

Pfad: `hardware/v2-c6-4ch/`

- Gerber-ZIP: `fab/JLCPCB-gerbers-esp32-c6-pwm-4ch.zip`
- BOM mit geprueften LCSC-Links: `bom.csv`
- CPL (nur SMD, optional): `fab/cpl-smd.csv`
- Handloeten als Standard: `HAND_SOLDER.md`
- Bestell-Absatz: `ORDER.md`
- PCB regenerieren: `python3 scripts/build_pcb.py` (KiCad 6 Footprints noetig)

Platine: 90 mm × 70 mm, 2 Layer. GND als explizite Tracks (kein automatisches Zone-Fill im Headless-Generator).

**Preise / Lager / Lieferzeit: ungeprueft** - im Fertiger-/LCSC-Warenkorb pruefen.

### 19. Firmware v2

PlatformIO-Env `esp32-c6-supermini`. Befehle: `PWM`, `RPM`, `TEMP`, `STATUS` (siehe README). Im Automatikbetrieb wird die Temperatur einmal pro Regelzyklus gelesen und auf alle vier Kanaele angewendet: unter 40 °C 35 %, ab 40/45/50/55 °C 50/65/80/100 %. Beim Abkuehlen bleibt die aktuelle Stufe bis 2 °C unter der jeweiligen Einschaltschwelle erhalten. 35 % ist die Mindestvorgabe.

Ein gueltiger serieller `PWM`-Befehl uebernimmt den betroffenen Kanal beziehungsweise alle Kanaele fuer fuenf Minuten; danach faellt jeder betroffene Kanal automatisch auf die Temperaturkurve zurueck. Ein fehlender oder ungueltiger DS18B20-Wert setzt alle Kanaele unverzueglich auf 100 % und hat Vorrang vor dem Handbetrieb. Sobald wieder ein gueltiger Temperaturwert vorliegt, gilt ein noch laufender Handbetrieb weiter; andernfalls wird automatisch geregelt. `STATUS` kennzeichnet die Kanaele mit `AUTO`, `MANUAL` oder `FAILSAFE`.

### 20. Checkliste Inbetriebnahme v2

1. Modul-Pinabstand gegen Buchsen messen; Ausrichtung USB laut Silkscreen.
2. Ohne ESP: 12 V anlegen → Luefter sollen voll laufen (Fail-safe).
3. ESP stecken, USB, `STATUS` / `TEMP` / `PWM 1 50`.
4. Tach-Pegel am GPIO mit Scope/Logikpruefer: nur 0…3,3 V.
5. Verpolungstest nur mit PTC/Schutz - kurz, PTC darf ausloesen.
