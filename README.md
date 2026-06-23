# WoTiTi - Work Time Tracker and Insights

**[Zur Dokumentation](https://grenzenloseSchublade.github.io/wotiti/)** | [Jetzt herunterladen](https://github.com/grenzenloseSchublade/wotiti/releases) | [Bugs berichten](https://github.com/grenzenloseSchublade/wotiti/issues)

---

WoTiTi ist ein **lokal ausführbares System zur Zeiterfassung und Arbeitszeitanalyse** mit integrierter Pomodoro-Methode. Die Anwendung besteht aus zwei funktional getrennten Komponenten:

1. **Work Time Timer**: Erfassungskomponente auf Basis von tkinter
2. **Work Time Insights**: Analysekomponente auf Basis von Dash und Plotly

## Kurzüberblick

WoTiTi ist eine lokal ausführbare Desktop-Anwendung zur Erfassung von Arbeitszeiten mit zugehörigem Analyse-Dashboard.

**Zielsetzung**
- operative Erfassung von Arbeits- und Pausenphasen mit geringer Interaktionslast
- lokale, reproduzierbare Speicherung ohne externe Infrastruktur
- getrennte analytische Auswertung derselben Datenbasis

**Kernmerkmale**
- Start-, Pause- und Stop-Logik pro Benutzer und Projekt
- separate Persistierung von Arbeitsphasen (`events`) und Pausenphasen (`break_events`)
- Tagesnotizen je Projekt/Tag (max. 44 Wörter) mit „übertragen"-Status für den manuellen Übertrag ins Firmensystem
- Ereignisliste mit Session-Bearbeitung (Doppelklick) und manueller Nacherfassung für vergangene Tage
- Pomodoro-Unterstützung mit konfigurierbaren Arbeits- und Pausenintervallen
- Auto-Stop bei systemweiter Inaktivität (konfigurierbares Idle-Timeout)
- Mini-Modus als separates Always-on-top Fenster mit persistenter Position
- Zeitmaschine: scrollbare 7-Tage-Wochenansicht mit Balkendiagramm und KW-Anzeige
- Feiertags- und Wochenend-Erkennung (konfigurierbar: Land, Region)
- Dashboard für deskriptive, visuelle und statistische Auswertungen
- Standalone-Builds für Linux und Windows via PyInstaller

## tl;dr - Schnellstart

### Vorgebaute Binärdatei (einfachste Methode)

**[Releases – neueste Version herunterladen](https://github.com/grenzenloseSchublade/wotiti/releases)**  
Dort finden sich die aktuellen ZIP-Pakete für Linux x64 und Windows x64 (Dateinamen enthalten die Versionsnummer, z. B. `wotiti_2_0_2-*`).

Entpacken → Ausführen. Fertig!

### Aus Quellcode

Ausführung aus dem Quellcode (Python 3.10–3.13):
```bash
pip install uv
uv sync --extra stats      # --extra stats wird für das Insights-Dashboard benötigt
uv run python src/main.py
```

### Dev Container (Docker / VS Code / Cursor)

Für eine reproduzierbare Entwicklungsumgebung: **Ordner `wotiti` öffnen** (Repository-Wurzel mit `pyproject.toml`), nicht nur ein beliebiges Elternverzeichnis. Anschließend in der Command Palette „Dev Containers: Reopen in Container“ wählen. Die Konfiguration liegt unter [`.devcontainer/`](.devcontainer/).

- Vor dem Start legt [`.devcontainer/init.sh`](.devcontainer/init.sh) auf dem **Host** ggf. Platzhalter für fehlende Bind-Mount-Pfade an (z. B. `/mnt/wslg/PulseServer` ohne WSLg), damit Docker nicht abbricht.
- Das Dash-Dashboard nutzt standardmäßig Ports um **8052**; bei Port-Konflikten werden bis zu 20 Folgeports probiert – diese sind in der Dev-Container-Konfiguration weitergeleitet (`forwardPorts`).
- Optionale Variablen sind in [`.env.example`](.env.example) beschrieben.

### Build

Build unter Linux:
```bash
./build.sh
```

Build unter Windows:
```powershell
.\build_windows.ps1
```

➡️ **[Detaillierte Installationshilfe →](https://grenzenloseSchublade.github.io/wotiti/installation/)**

## Motivation und Designprinzipien

WoTiTi verfolgt zwei Ziele: eine operativ einfache Erfassung von Arbeitsphasen im Alltag und eine methodisch nachvollziehbare Auswertung derselben Daten ohne externe Infrastruktur. Der Ansatz ist bewusst datenlokal und modular – die Erfassung als kleine tkinter-Anwendung, die Analyse als separates Dash/Plotly-Dashboard. Diese Trennung hält das tägliche Tracking schlank und schafft zugleich eine belastbare Grundlage für statistische und visuelle Auswertungen.

Leitprinzip der Erfassungskomponente ist funktionale Schlichtheit im Primärworkflow: Start, Pause, Stop, Benutzer- und Projektauswahl sind direkt zugänglich, ohne verschachtelte Dialoge. Die Oberfläche ist kompakt und werkzeugartig; erweiterte Funktionen (Konfiguration, Auswertung, Detailbearbeitung) bleiben vorhanden, dominieren aber den Erfassungsvorgang nicht. Anders als bei vielen kommerziellen Lösungen sind diese Funktionen weder an Lizenzstufen noch an cloudgebundene Betriebsmodelle gekoppelt – WoTiTi ist kostenlos, quelloffen und lokal betreibbar.

Zusätzlich erweitert eine strukturierte Pomodoro- und Pausenlogik die reine Zeitmessung: Pausen werden explizit erfasst und Unterbrechungen datenbasiert nachvollziehbar. Dadurch entsteht ein zweiter analytischer Blick auf Arbeitsrhythmus, Pausendisziplin und die Stabilität fokussierter Arbeitsintervalle.

Aus technischer Sicht ist das Projekt insbesondere durch folgende Eigenschaften charakterisiert:

- vollständig lokale Datenspeicherung
- reproduzierbare SQLite-basierte Datenhaltung
- explizite Trennung von operativer Eingabe und analytischer Auswertung
- Build- und Distributionspfade für Windows und Linux ohne Cloud-Abhängigkeit

WoTiTi ist damit als kompaktes, lokal betriebenes System zur Erfassung und Analyse von Arbeitszeitdaten konzipiert.

## Systemarchitektur

### Erfassungskomponente (Work Time Timer)

**Timer-Anzeige**

```
┌──────────────────────────────────────────────────────────┐
│  01:23:45      [Hans]      Projekt: 1           05:00    │
│  Σ 42:15:30                               ▮▮ 00:15:00   │
└──────────────────────────────────────────────────────────┘
   ▲ Tageszeit    ▲ User      ▲ Projekt   ▲ Pause-Timer
   (rot, groß)                             (blau)

Zeile 2 (kompakt, Tooltip bei Hover):
   Σ = Gesamte Projektzeit (alle Tage)
  ▮▮ = Summe der Pausen am gewählten Kalendertag
```

Der Timer zeigt primär die **Tagesarbeitszeit** für das **im Datumsfeld gewählte Datum** (nicht nur „heute“). **Σ** bleibt die **Gesamtzeit des Projekts über alle Tage**. **▮▮** ist die **Tages-Pausensumme** für dasselbe gewählte Datum. Weitere Tooltips u. a. am Button **Auswertung** (Status Farbe) und am Pause-Timer.

**Datumsfeld (TT-MM-JJJJ)**  
Steuert die **Ereignisliste** (nur Einträge dieses Tages) und die **angezeigten Tageswerte** (Haupttimer, ▮▮). Nach **Enter** oder beim Verlassen des Felds wird neu geladen; **Heute** setzt auf den aktuellen Tag und aktualisiert sofort. Ist ein **anderer Tag** gewählt, erscheint das Datumsfeld **leicht gelb** hinterlegt. Der **Live-Zähler** (laufende Session) läuft nur, wenn **heute** angezeigt wird; für vergangene Tage sieht man den gespeicherten Stand aus der Datenbank. Der Button **Aktualisieren** bleibt als manueller Fallback. Nach **Bearbeiten/Löschen** eines Listeneintrags werden die Zeiten ebenfalls neu berechnet.

**Mini-Modus** (▽/△): Kompakte Always-on-top Ansicht mit Tageszeit, Drag-Support und persistenter Position.

**Zeitmaschine** (Wochenansicht): Zeigt die letzten 7 Tage als Balkendiagramm direkt in der Timer-Kachel. Per Pfeil-Navigation (‹ ›) durch beliebige Wochen scrollen, Titel zeigt die aktuelle Kalenderwoche. Wochenenden werden grau, Feiertage rot markiert (Land und Region konfigurierbar in den Einstellungen).

**Ereignisliste & Bearbeitung**  
Die Liste zeigt die Sessions des im Datumsfeld gewählten Tages, gruppiert nach Benutzer und Projekt; Dauern werden als **H:MM** dargestellt (`8:05 h`, nicht dezimal). Über eine Einstellung lässt sich die Liste auf eine **chronologische** Darstellung (Projekt je Zeile) umschalten. Ein **Doppelklick** auf eine Session öffnet den Editor (Projekt, Datum, Start-/Stop-Zeit, Notiz, Übertragungsstatus); laufende Sessions sind schreibgeschützt. Für **vergangene Tage** erlaubt der **„+"-Button** die manuelle Nacherfassung eines Start-/Stop-Paares.

**Tagesnotizen & Übertragungsstatus**  
Pro Benutzer, Projekt und Tag kann eine **Notiz** (max. 44 Wörter) erfasst werden, gedacht als Gedächtnisstütze für den **manuellen Übertrag der Zeiten in ein Firmensystem**. Ist der Übertrag erledigt, markiert die Checkbox **„übertragen"** den Projekt-Tag (mit Zeitstempel); der Status erscheint als `✓ übertragen` in der Ereignisliste und in der Wochenansicht. Notizen werden in der Liste lesbar umbrochen.

**Auto-Stop bei Inaktivität**  
Bleibt das System länger als das konfigurierte Idle-Timeout (Standard 120 min, `0` = aus) ohne Eingabe, wird eine laufende Session automatisch gestoppt und das Fenster in den Vordergrund geholt.

**Ein Fenster (Single-Instance)**  
Ein erneuter Start der Anwendung (EXE/App unter Windows/Linux) beendet sich und holt stattdessen das **laufende WoTITI-Hauptfenster** (bzw. den **Mini-Modus**, falls aktiv) in den Vordergrund. Das betrifft **nicht** den Browser oder das Auswertungs-Dashboard. Zum Testen mehrerer Instanzen kann in `data/config.json` `single_instance` auf `false` gesetzt werden (optional auch `single_instance_port` für den reinen IPC-Port).

**Funktionsumfang**

- Drei-Zustands-Logik für Arbeitssitzungen: Start, Pause, Stop
- Mehrbenutzer-Unterstützung mit Dropdown-Auswahl
- Projektbasierte Zeiterfassung mit Combobox (intelligentes Caching)
- Benutzerverwaltung (eigenes Fenster zum Anlegen/Auswählen)
- Tagesnotizen (max. 44 Wörter) und „übertragen"-Status pro Projekt/Tag
- Ereignisliste umschaltbar (nach Projekt gruppiert ⟷ chronologisch), Dauern als H:MM
- Session-Bearbeitung per Doppelklick; manuelle Nacherfassung für vergangene Tage
- Auto-Stop bei systemweiter Inaktivität (konfigurierbares Idle-Timeout)
- **Tastenkürzel**: `Ctrl+S` Start, `Ctrl+E` Stop, `Ctrl+M` Mini-Modus, `Ctrl+P` Pause
- **Einstellungen**: Datenbank, Defaults, Dashboard-Port, Theme, Feiertags-Land/-Region, Listen-Darstellung, Pomodoro & Pausen, Idle-Timeout, Sound, Entwickler-Konsole, Über-Dialog
- Persistente Konfiguration (`data/config.json`)
- SQLite-Datenbankintegration (users, projects, events, break_events, daily_notes)
- Separate Break-Tabellenlogik für manuelle und Pomodoro-Pausen
- Automatische Bereinigung verwaister Sessions und Pausen nach unsauberem Beenden
- Echtzeit-Timer-Anzeige (Tageszeit bezogen auf gewähltes Datum, Σ gesamt, ▮▮ Pausen am gewählten Tag)
- Zeitmaschine: 7-Tage-Balkendiagramm mit Wochennavigation (‹ ›) und KW-Anzeige
- Feiertags-Erkennung in der Wochenansicht (rot markiert, Land/Region konfigurierbar)
- Wochenend-/Feiertags-Filter für Dashboard-Statistiken (Durchschnitte, Trends)
- Session-Schutz bei App-Schließen
- Eingabevalidierung (Datumsformat DD-MM-YYYY)
- Log-Rotation (`data/wotiti.log`, 1 MB, 3 Backups)

### Analysekomponente (Work Time Insights)
- Datenaufbereitung mit **Polars** (schnelle, speichereffiziente Tabellenoperationen)
- Durchgehend **deutschsprachige** Oberfläche (Titel, Achsen, UI-Elemente)
- **Theme-System**: Modern (Cyan/Pink/Gelb) & Synthwave — umschaltbar in den Einstellungen
- Eigenes Plotly-Template `wotiti` mit definierter Farbpalette und Layoutvorgaben
- 5 Tab-Bereiche: Übersicht, Grundlagen, Projekte & Muster, Zeitreihen, Erweitert
- Interaktive Datenvisualisierung
- Fortgeschrittene statistische Analysen
- Arbeitsmuster-Erkennung
- Vorhersagemodelle
- Vergleichsanalysen

## Projektstruktur

Eine technisch tiefere Beschreibung der einzelnen Python-Module findet sich als Kommentar/Docstring direkt im jeweiligen Modulkopf (siehe Baum unten).

```
wotiti/
├── src/
│   ├── main.py              # Einstiegspunkt (GUI + Dashboard-Start, Logging, IPC)
│   ├── app.py               # GUI-Implementation (tkinter)
│   ├── db_helper.py         # Datenbankoperationen (SQLite)
│   ├── idle_monitor.py      # OS-Idle-Erkennung (Windows user32 / Linux X11)
│   ├── single_instance.py   # Single-Instance-IPC (TCP-Port + Windows-Mutex)
│   ├── stats_dashboard.py   # Analyse-Dashboard (Dash)
│   ├── stats_calculations.py # Statistische Berechnungen
│   ├── stats_plotting.py    # Visualisierungsfunktionen (Plotly)
│   ├── stats_generator.py   # Testdatengenerierung
│   ├── utils.py             # Hilfsfunktionen, Pfade, Konfiguration & Themes
│   └── assets/
│       ├── style.css        # Dashboard-Styles
│       ├── wotiti.ico       # App-/Taskbar-Icon
│       └── wotiti_preview.png
├── data/                    # Laufzeitdaten (DBs, config.json, sounds, Log)
├── tests/
│   ├── test_app.py             # GUI-Tests
│   ├── test_db_helper.py       # Datenbank-Tests
│   ├── test_idle_monitor.py    # Idle-Erkennung
│   ├── test_stats_calculations.py # Statistik-Funktionen
│   └── test_utils_workdays.py  # Arbeitstag-/Feiertagslogik
├── build.sh                # Linux Build-Skript
├── build_windows.ps1       # Windows Build-Skript
├── pyproject.toml          # uv/pyproject-Konfiguration (Feld `version` = App-Version)
└── README.md
```

## Fachliches Kernmodell

Die Anwendung arbeitet mit logisch getrennten Datentypen:

- `events` für Arbeitsphasen
- `break_events` für Pausenphasen und Pomodoro-bezogene Unterbrechungen
- `daily_notes` für Tagesnotizen je Benutzer/Projekt/Tag inkl. Übertragungsstatus (`transferred`, `transferred_at`)

Für Pausen werden zusätzlich fachliche Metadaten gespeichert, darunter:

- `break_kind`
- `is_auto`
- `source`
- `pomodoro_cycle`
- `work_interval_minutes`

Dadurch lassen sich Arbeitszeit, Pausenverhalten und Pomodoro-Rhythmus analytisch getrennt betrachten.


## Qualitätssicherung

- Linting mit `ruff`
- atomare Schreibvorgänge für `config.json`
- Log-Rotation nach `data/wotiti.log`
- Tests für GUI- und Datenbanklogik unter `tests/`

```bash
ruff check src/ tests/
python -m pytest tests/ -v
```

## Konfiguration

Die Laufzeitkonfiguration wird in `data/config.json` gespeichert (Standardwerte in `src/utils.py`, `DEFAULT_CONFIG`).

Wichtige Konfigurationsschlüssel:

- `database_path` – aktive Datenbank
- `default_user`, `default_project` – Standardbenutzer/-projekt
- `dashboard_port` – Port des Insights-Dashboards (bei Konflikt werden Folgeports probiert)
- `theme` – Dashboard-Theme (`Modern` / `Synthwave`)
- `pomodoro_*` – Pomodoro-/Pausen-Parameter (Arbeits-/Pausenlängen, Auto-Pause, Sound)
- `pomodoro_sound_local_path` – Sounddatei; `mini_window_position`, `window_geometry` – Fenster-Positionen
- `idle_timeout_minutes` – Auto-Stop bei Inaktivität (`0` = aus)
- `holiday_country`, `holiday_subdiv` – Land/Region für Feiertags-Erkennung (z. B. `DE` / `NW`)
- `exclude_weekends_in_averages`, `include_holidays_in_exclusion`, `count_weekend_work` – Wochenend-/Feiertags-Filter für Statistiken
- `entry_list_chronological` – Ereignisliste chronologisch statt nach Projekt gruppiert
- `single_instance` (+ optional `single_instance_port`) – Ein-Fenster-Verhalten
- `project_colors` – feste Farbzuordnung je Projekt in der Wochenansicht

## Bekannte Einschränkungen

- Timestamp-Konvertierung bei ungewöhnlichen Formaten
- CPU-Last bei komplexen Dashboard-Analysen
- Port-Änderungen werden erst nach Neustart wirksam
- Theme-Umschaltung erfordert Neustart des Dashboards

## Geplante Erweiterungen

- Export-Funktionen für Analysen
- Endnutzer-Docker-Image (optional; Entwicklung: siehe Dev Container oben)
- Weitere Build-/Release-Automatisierung

## Mitwirkung

1. Repository forken
2. Feature-Branch anlegen
3. Änderungen committen
4. Pull Request erstellen

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.