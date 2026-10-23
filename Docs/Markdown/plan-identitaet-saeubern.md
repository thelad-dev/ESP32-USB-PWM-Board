# Plan: Identitaet saeubern (Entscheidungsformulierungen, Gedankenstriche)

## Annahme

- Die bekannten Fundstellen auf main nach PR #1 sind vollstaendig; weitere Treffer ergeben sich nur aus einer Repo-weiten Suche.
- Commit-Nachrichten und Git-Historie bleiben unangetastet (laut Auftrag geprueft und sauber).
- Gerber-/CAD-Ausgaben und `legacy/` bleiben aussen vor; automatische Build-Artefakte ebenfalls.

## Zwei Wege

1. **Auftragsweg:** Nur die fuenf genannten Stellen umschreiben und danach suchen.
2. **Alternative (genommen):** Zuerst Repo-weit auf Drittperson-/Anrede-Sprache und lange Gedankenstriche suchen, dann alle Treffer in versioniertem Text (Markdown, ini, Quellkommentare/-strings, BOM/ORDER) in einem Diff bereinigen. So bleibt der Nachweis im PR eine leere Suche, nicht nur die bekannten Zeilen.

Gelassen: Nur die genannten fuenf Zeilen anfassen und Gedankenstriche anderswo stehen lassen - wuerde Punkt 3 und den Nachweis verfehlen.

## Ablehnung

Ein erfahrener Kollege wuerde ablehnen, wenn die technische Begruendung (9x C6 vs 3x C3, 2x8 vs 2x10, kein gemeinsamer Steckplatz) wegfiele oder weichgespult wuerde; oder wenn Firmware/Pinout/Hardware mitgeaendert wuerden.

## Nachweis

- `rg` ueber den versionierten Bestand (ohne `.git`, `.venv`, `legacy`) auf die Suchbegriffe aus Punkt 2 und auf lange Gedankenstriche: null Treffer.
- Falls `platformio.ini` geaendert: `pio run -e esp32-c6-supermini` gruen.

## Grenze

Keine Aenderung an Firmware-Verhalten, Pinbelegung, Hardware-Design, Gerberdaten, BOM-Inhalt (nur Gedankenstriche in Zellen/Kommentartext), Projektstruktur. Keine Umbenennungen, kein History-Rewrite.
