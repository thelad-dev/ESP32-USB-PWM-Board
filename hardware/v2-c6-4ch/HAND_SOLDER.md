# Bestueckung

**Standard: komplett von Hand loeten.** Es gibt keine Pflicht zur Fertiger-Bestueckung.

`fab/cpl-smd.csv` ist nur vorhanden, falls spaeter JLCPCB SMT fuer die SMD-Teile gewuenscht wird. THT-Teile (J_ESP_L/R, J_FAN1-4, J_PWR, J_TEMP, U_TEMP) bleiben Handarbeit; das ESP32-C6-SuperMini-Modul wird in die Buchsenleisten gesteckt, nicht verloetet.

Am 1-Wire-Bus nur einen DS18B20 anschliessen: entweder U_TEMP oder die externe
Sonde an J_TEMP, niemals beide gleichzeitig.
