# Diagnose: Windows 11 geht nicht in den Ruhezustand

**Datum:** 2026-08-14 · **Betroffen:** Win11-Notebook mit wotiti im Autostart
**Symptom:** Der PC geht manchmal nicht in den Ruhemodus — der Bildschirm wird
schwarz, aber die Maschine läuft im Hintergrund weiter (warm, Lüfter, Akku-Drain).

## Kurzfazit

**wotiti ist nachweislich *nicht* die Ursache.** Die `powercfg`-Messungen zeigen wotiti
als vernachlässigbaren Faktor. Der Rechner nutzt **Modern Standby (S0)** und erreicht den
tiefen Idle-Zustand nicht, weil **andere, klar benannte Prozesse und ein defekter
Treiber** ihn aktiv halten — allen voran **WSL2** und ein **fehlerhafter GlobalProtect-
Netzwerkadapter**.

---

## Warum es passiert: Modern Standby (S0)

`powercfg /a` ergab: verfügbar ist nur **Standby (S0 Low Power Idle) Network Connected**,
dazu Ruhezustand + Schnellstart. **S1/S2/S3 sind alle deaktiviert** (Firmware, S3 zusätzlich
per Device Guard).

Das heißt: Es gibt **kein klassisches Sleep (S3)**, bei dem der ganze Rechner suspendiert.
Beim „Einschlafen" schaltet Windows nur den Bildschirm ab und *versucht*, in einen tiefen
Energiesparzustand (DRIPS) zu fallen. **Jeder Prozess bzw. jedes Gerät, das aktiv bleibt,
verhindert das** → „schwarzer Bildschirm, läuft aber weiter". Genau das beobachtest du.

---

## Beweislage

### wotiti scheidet aus
- **`powercfg /requests` → überall „Keine".** Kein Prozess hält einen formalen
  Wachhalte-Request (`SetThreadExecutionState`). wotiti verbietet Schlaf *nicht*.
- **`powercfg /energy`:** Plattform-Timerauflösung steht auf dem **Default 15,6 ms** —
  kein Prozess hat sie erhöht. wotiti/python tauchen **nicht** unter den Top-CPU-Prozessen
  auf.
- **`powercfg /sleepstudy` (174 Standby-Sitzungen):** `wotiti.exe` = **1229 CPU-Einheiten
  gesamt** — weit außerhalb der Top 20, rund **1/70** des Hauptverursachers.

### Die tatsächlichen Störer (aus `sleepstudy` / `energy`)

| Rang | Verursacher | CPU im Standby¹ | Was es ist |
|-----:|-------------|----------------:|------------|
| 1 | **`vmmemWSL`** | **85 675** | WSL2-VM bleibt im Standby aktiv (typ. via Docker Desktop / offene Distro) |
| 2 | `Code.exe` | 23 372 | VS Code läuft im Hintergrund weiter |
| 3 | `System` | 21 398 | Kernel/Treiber-Aktivität |
| 4 | `svchost [netsvcs][Winmgmt]` | 18 220 | WMI/Dienste |
| 5 | **MS Teams (zwei Versionen!)** | 15 306 + 15 009 | doppelte Installation, beide aktiv |
| 6 | `dwm.exe`, `powershell.exe`, `msedge`/WebView2, `Obsidian.exe`, `MsMpEng` (Defender), Claude | je 7–14 k | Dauerläufer |
| … | **`wotiti.exe`** | **1 229** | **vernachlässigbar** |

¹ Summierte `CpuPowerConsumption`-Einheiten über alle 174 Standby-Sitzungen.

### Zusätzliche Fehler / Fehlkonfiguration (aus `powercfg /energy`)
- **FEHLER — defekter Netzwerktreiber:** „**PA Virtual Ethernet Adapter Secure**",
  Geräte-ID `ROOT\PAVED\0000`, **Problemcode 0x16**. Das ist der virtuelle Adapter von
  **Palo Alto GlobalProtect** in einem Fehlerzustand. Ein Netzwerkadapter, der nicht sauber
  energiesparen kann, ist ein **klassischer Modern-Standby-Blocker**.
- **FEHLER — PCIe-ASPM deaktiviert** (Active-State Power Management, HW-Inkompatibilität).
- **WARNUNG — minimaler Prozessorleistungszustand = 80 %** (Netzbetrieb): Die CPU taktet
  nie unter 80 % herunter → „läuft warm", höherer Verbrauch.
- **WARNUNG — Standby-Timeout 60 min** (Netzbetrieb); Bildschirm-Timeout 10 min (Akku).

---

## Behebungsanleitung (nach Hebelwirkung geordnet)

> Alle Schritte auf dem **Win11-Rechner** ausführen, `powercfg`-Befehle in einer
> **Administrator-PowerShell**.

### 1. WSL2 stoppen, wenn nicht gebraucht (größter Hebel)
```powershell
wsl --shutdown
```
Prüfen, was WSL wachhält (oft **Docker Desktop** im Autostart):
```powershell
wsl -l -v                 # laufende Distros/Status
```
Wenn Docker Desktop nicht dauerhaft gebraucht wird: in dessen Einstellungen
„Start Docker Desktop when you log in" deaktivieren, bzw. WSL-Integration abschalten.

### 2. Defekten GlobalProtect-Netzwerkadapter bereinigen
1. `Win+X` → **Geräte-Manager** → **Netzwerkadapter**.
2. „**PA Virtual Ethernet Adapter Secure**" suchen (gelbes Warndreieck, `ROOT\PAVED\0000`).
3. Entweder **GlobalProtect aktualisieren/neu installieren**, oder — falls VPN aktuell
   nicht gebraucht — den Adapter per Rechtsklick **deaktivieren**.
4. Kontrolle nach Neustart:
   ```powershell
   powercfg /energy /duration 60
   ```
   Der Adapter sollte nicht mehr als Fehler auftauchen.

### 3. Schwere Hintergrund-Apps entschärfen
- **Doppelte MS-Teams-Installation** bereinigen (alte klassische *und* neue Teams-App sind
  installiert) — die nicht genutzte deinstallieren.
- **VS Code / Obsidian** vor dem Standby schließen oder deren „im Hintergrund weiterlaufen"-
  Verhalten prüfen (VS Code: Einstellung *Window: Close When Empty* / offene Terminals mit
  laufenden Prozessen beenden).

### 4. Energieplan korrigieren
Minimalen Prozessorzustand senken (Netz **und** Akku) und Standby beschleunigen:
```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 5
powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 5
powercfg /setactive SCHEME_CURRENT
```
(PCIe-ASPM lässt sich nur aktivieren, wenn die HW es zulässt — hier laut Report
deaktiviert wegen bekannter Inkompatibilität; belassen.)

### 5. Gegentest
1. Schritte 1–2 anwenden.
2. Rechner in Standby schicken, einige Minuten warten, aufwecken.
3. Report neu erzeugen und prüfen:
   ```powershell
   powercfg /sleepstudy
   ```
   Erwartung: **„Low Power %" der neuen Sitzung steigt deutlich**, `vmmemWSL` und der
   PAVED-Adapter verschwinden aus den Top-Verursachern.

---

## Zur ursprünglichen Vermutung (Programm-Konflikt / Deadlock)

- **Konflikt mit „Go-to-Sleep"?** Nein — wotiti stellt keinen Power-Request und ist in den
  Messungen ein Nicht-Faktor.
- **Deadlock / Livelock durch die Standby-Stop-Funktion?** Ausgeschlossen: Die Erkennung
  (`_check_suspend_gap`, `_maybe_auto_stop_idle`) läuft auf dem einzigen Tk-UI-Thread
  (kein Lock-Zyklus → kein Deadlock), der Takt ist per `after(1000)` fest gedeckelt und die
  Stops sind idempotent (kein Livelock). Selbst hypothetisch würde weder das eine noch das
  andere den PC wachhalten — ein blockierter Prozess verbraucht keine CPU und stellt keinen
  Power-Request.

## Anhang — Diagnose-Befehle (read-only)
```powershell
powercfg /a                    # verfügbare Schlafzustände (S0 vs. S3)
powercfg /requests             # aktuelle Wachhalte-Blocker (live)
powercfg /energy /duration 60  # 60-s-Trace → energy-report.html (Timerauflösung, Treiber)
powercfg /sleepstudy           # Historie → sleepstudy-report.html (Low Power %, Verursacher)
```
