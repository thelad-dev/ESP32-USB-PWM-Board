# ESP32 PWM- / Tacho-Board (4-Pin-Luefter)

## Varianten

| Variante | Beschreibung | Hardware | Firmware |
|----------|--------------|----------|----------|
| v1 (1 Kanal) | ESP32-DevKitC, ein Luefterkanal | [writeup.md](writeup.md) Teil A, [hardware/bom-1channel.csv](hardware/bom-1channel.csv) | [legacy/1ch/](legacy/1ch/) |
| **v2 (4 Kanal + Temp)** | ESP32-C6 SuperMini gesteckt, 4x PWM/Tach, DS18B20 | [hardware/v2-c6-4ch/](hardware/v2-c6-4ch/) | `src/`, `include/` |

Captain-Entscheidung: **C6** wegen Bestand (9x). C3-SuperMini ist pin-inkompatibel (2x8 vs 2x10) — siehe [INVENTORY-DECISIONS.md](hardware/v2-c6-4ch/INVENTORY-DECISIONS.md).

## Firmware v2 (PlatformIO)

```bash
pio run -e esp32-c6-supermini -t upload
pio device monitor -e esp32-c6-supermini
```

Baud **115200**. Pins in `include/config.h` (PWM 0/1/2/3, Tach 20/19/18/14, Temp 21).

### Serielle Befehle

| Befehl | Wirkung |
|--------|---------|
| `PWM 0` / `PWM <5-100>` | Handbetrieb fuer alle Kanaele, 5 Minuten |
| `PWM ALL <0-100>` | Handbetrieb fuer alle Kanaele, auch bei 1-4%, 5 Minuten |
| `PWM <1-4> <0-100>` | ein Kanal im Handbetrieb fuer 5 Minuten |
| `RPM` / `RPM <1-4>` | Drehzahl |
| `TEMP` | DS18B20 °C |
| `STATUS` | PWM, RPM, Temp |
| `HELP` | Hilfe |

Unvollstaendige oder fehlerhafte `PWM`-Argumente werden abgelehnt, ohne die
Luefterwerte zu aendern. Ein einzelnes `PWM 1` ist daher kein All-Kanaele-Befehl.

Im Automatikbetrieb gilt eine stufige Temperaturkurve: unter 40 °C 35 %, ab
40/45/50/55 °C 50/65/80/100 %. Beim Abkuehlen wird jede Stufe erst 2 °C unter
ihrer Einschaltschwelle verlassen. 35 % ist die Mindestvorgabe. Ein fehlender
oder ungueltiger Sensorwert setzt alle Kanaele sofort auf 100 % und uebersteuert
auch den Handbetrieb. `STATUS` zeigt `AUTO`, `MANUAL` oder `FAILSAFE` pro Kanal.

## Bestellbares PCB (v2)

- Gerber: `hardware/v2-c6-4ch/fab/JLCPCB-gerbers-esp32-c6-pwm-4ch.zip`
- BOM + Stock-Spalte: `hardware/v2-c6-4ch/bom.csv`
- Handloeten: `hardware/v2-c6-4ch/HAND_SOLDER.md`
- Bestell-Absatz: `hardware/v2-c6-4ch/ORDER.md`
