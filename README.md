# WoTiTi - Work Time Tracker and Insights

WoTiTi ist ein lokal ausführbares System zur Zeiterfassung und Arbeitszeitanalyse. Die Anwendung besteht aus zwei funktional getrennten Komponenten:

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
- Pomodoro-Unterstützung mit konfigurierbaren Arbeits- und Pausenintervallen
- Mini-Modus als separates Always-on-top Fenster mit persistenter Position
- Dashboard für deskriptive, visuelle und statistische Auswertungen
- Standalone-Builds für Linux und Windows via PyInstaller

**Schnellstart**

Ausführung aus dem Quellcode:
```bash
pip install uv
uv sync
uv run python src/main.py
```

Build unter Linux:
```bash
./build.sh
```

Build unter Windows:
```powershell
.\build_windows.ps1
```

Herunterladbare Builds:
- Aktuelle Releases: [GitHub Releases](https://github.com/grenzenloseSchublade/wotiti/releases)
- Version `v1.1.0` Linux x64: [wotiti_1_1-linux-x64.zip](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-linux-x64.zip)
- Version `v1.1.0` Windows x64: [wotiti_1_1-win-x64.zip](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-win-x64.zip)

## Motivation und Designprinzipien

WoTiTi wurde als lokal ausführbares System für Zeiterfassung und explorative Arbeitszeitanalyse entwickelt. Das Projekt verfolgt zwei Ziele: eine operativ einfache Erfassung von Arbeitsphasen im Alltag und eine methodisch nachvollziehbare Auswertung derselben Daten ohne externe Infrastruktur.

Der Ansatz ist bewusst datenlokal und modular. Die Erfassungskomponente ist als kleine tkinter-Anwendung realisiert, die Analysekomponente als separates Dash/Plotly-Dashboard. Diese Trennung reduziert die Komplexität der Interaktionen im täglichen Tracking und schafft gleichzeitig eine belastbare Grundlage für statistische und visuelle Auswertungen.

Ein zentrales Gestaltungsprinzip der Erfassungskomponente ist funktionale Schlichtheit im Primärworkflow: Start, Pause, Stop, Benutzerwahl und Projektauswahl sind in der Hauptansicht direkt zugänglich, ohne verschachtelte Dialogführung. Die Oberfläche ist dabei nicht minimalistisch im engeren Sinn, sondern bewusst kompakt und werkzeugartig aufgebaut. Erweiterte Funktionen wie Konfiguration, Auswertung oder Detailbearbeitung bleiben vorhanden, dominieren jedoch nicht den eigentlichen Erfassungsvorgang.

Im Unterschied zu vielen kommerziellen Zeiterfassungslösungen, bei denen erweiterte Funktionen oft an Lizenzstufen, Zusatzmodule oder cloudgebundene Betriebsmodelle gekoppelt sind, verfolgt WoTiTi bewusst einen kostenlosen, quelloffenen und lokal betreibbaren Ansatz.

Zusätzlich erweitert WoTiTi die reine Zeiterfassung um eine strukturierte Pomodoro- und Pausenlogik: Arbeitsphasen werden zeitlich segmentiert, Pausen explizit erfasst und Unterbrechungen von Arbeitsblöcken datenbasiert nachvollziehbar gemacht. Dadurch entsteht neben der reinen Arbeitszeitmessung ein zweiter analytischer Blick auf Arbeitsrhythmus, Pausendisziplin und die Stabilität fokussierter Arbeitsintervalle.

Aus technischer Sicht ist das Projekt insbesondere durch folgende Eigenschaften charakterisiert:

- vollständig lokale Datenspeicherung
- reproduzierbare SQLite-basierte Datenhaltung
- explizite Trennung von operativer Eingabe und analytischer Auswertung
- Build- und Distributionspfade für Windows und Linux ohne Cloud-Abhängigkeit

WoTiTi ist damit als kompaktes, lokal betriebenes System zur Erfassung und Analyse von Arbeitszeitdaten konzipiert.

## Systemarchitektur

### Erfassungskomponente (Work Time Timer)
- Drei-Zustands-Logik für Arbeitssitzungen: Start, Pause, Stop
- Mehrbenutzer-Unterstützung mit Dropdown-Auswahl
- Projektbasierte Zeiterfassung mit Combobox (intelligentes Caching)
- Benutzerverwaltung (eigenes Fenster zum Anlegen/Auswählen)
- **Mini-Modus** (▽/△): Kompakte Always-on-top Ansicht als separates Fenster mit Drag-Support und persistenter letzter Position
- **Tastenkürzel**: `Ctrl+S` Start, `Ctrl+E` Stop, `Ctrl+M` Mini-Modus, `Ctrl+P` Pause
- **Einstellungen**: Datenbank, Defaults, Port, Theme, Entwickler-Konsole, Pomodoro-Optionen
- Persistente Konfiguration (`data/config.json`)
- SQLite-Datenbankintegration (users, projects, events, break_events)
- Separate Break-Tabellenlogik für manuelle und Pomodoro-Pausen
- Echtzeit-Timer-Anzeige
- Session-Schutz bei App-Schließen
- Eingabevalidierung (Datumsformat DD-MM-YYYY)
- Log-Rotation (`data/wotiti.log`, 1 MB, 3 Backups)

### Analysekomponente (Work Time Insights)
- Durchgehend **deutschsprachige** Oberfläche (Titel, Achsen, UI-Elemente)
- **Theme-System**: Modern (Cyan/Pink/Gelb) & Synthwave — umschaltbar in den Einstellungen
- Eigenes Plotly-Template `wotiti` mit definierter Farbpalette und Layoutvorgaben
- 4 Tab-Bereiche: Grundlagen, Projekte & Muster, Zeitreihen & Trends, Erweiterte Analysen
- Interaktive Datenvisualisierung
- Fortgeschrittene statistische Analysen
- Arbeitsmuster-Erkennung
- Vorhersagemodelle
- Vergleichsanalysen

## Projektstruktur

```
wotiti/
├── src/
│   ├── main.py              # Einstiegspunkt (GUI + Dashboard-Start)
│   ├── app.py               # GUI-Implementation (tkinter)
│   ├── db_helper.py         # Datenbankoperationen (SQLite)
│   ├── stats_dashboard.py   # Analyse-Dashboard (Dash)
│   ├── stats_calculations.py # Statistische Berechnungen
│   ├── stats_plotting.py    # Visualisierungsfunktionen (Plotly)
│   ├── stats_generator.py   # Testdatengenerierung
│   ├── utils.py             # Hilfsfunktionen, Pfade & Konfiguration
│   └── assets/
│       └── style.css        # Dashboard-Styles
├── data/                    # Laufzeitdaten (DBs, config.json, sounds)
├── tests/
│   ├── test_app.py         # GUI-Tests
│   └── test_db_helper.py   # Datenbank-Tests
├── build.sh                # Linux Build-Skript
├── build_windows.ps1       # Windows Build-Skript
├── pyproject.toml          # uv/pyproject-Konfiguration
└── README.md
```

## Installation

```bash
# Repository klonen
git clone https://github.com/grenzenloseSchublade/wotiti.git

# uv installieren
pip install uv

# Abhängigkeiten installieren (Basis)
uv sync

# Optional: Stats/Dev-Abhängigkeiten
uv sync --extra stats --extra dev
```

## Ausführung

### Timer-Anwendung
```bash
# GUI starten
uv run python src/main.py
```

### Analyse-Dashboard
```bash
# Dashboard öffnen
uv run python src/stats_dashboard.py

# Testdaten generieren (optional)
uv run python src/stats_generator.py
```

## Funktionale Beschreibung

### Erfassungskomponente
- **Start/Pause/Stop-Logik**: Klare Zustandswechsel zwischen laufender Session, aktiver Pause und vollständigem Stop
- **Benutzer-Auswahl**: Combobox mit Dropdown aller bestehenden Benutzer
- **Projekt-Auswahl**: Combobox mit bestehenden Projekten (intelligentes Caching)
- **Benutzerverwaltung**: Eigenes Fenster zum Anlegen/Auswählen von Benutzern
- **Aktualisieren**: Zeigt die kumulierte Arbeitszeit pro Benutzer/Projekt
- **Mini-Modus**: Kompakte Always-on-top Ansicht als separates Fenster mit Drag-Support und Wiederherstellung an der zuletzt verwendeten Position
- **Einstellungen**: Konfigurationsfenster mit:
  - Datenbank auswählen, erstellen oder löschen (mit Bestätigung)
  - Standard-Benutzer und Standard-Projekt festlegen
  - Dashboard-Port konfigurieren
  - Theme-Auswahl (Modern / Synthwave)
  - Pomodoro-Konfiguration (Arbeitszeit, kurze/lange Pause, Intervall, Auto-Pause)
  - Pausen-Sound (Aktivierung, lokaler Dateipfad)
  - Entwickler-Konsole: Log-Viewer mit Aktualisieren, Löschen und Copy-Button
- **Datum-Setter**: Schnelle Datumseinstellung mit Validierung und Format-Hinweis (TT-MM-JJJJ)
- **Einträge bearbeiten**: Doppelklick auf Event in der Listbox öffnet Edit-Dialog (Projekt, Datum, Zeitstempel ändern oder Eintrag löschen)
- **Konsole**: Statusmeldungen und Fehler mit Copy-Funktion
- **Session-Schutz**: Warnung bei App-Schließen mit aktiver Session, sauberes Herunterfahren (DB-Close, Timer-Stop, Dashboard-Cleanup)
- **Break-Tracking**: Pausen werden in `break_events` separat protokolliert, um Auswertung und operative Logik zu entkoppeln

### Datenmodell der Zeiterfassung

Die operative Zeiterfassung ist in zwei logisch getrennte Datentypen aufgeteilt:

- `events`: Arbeitsphasen (Start/Stop)
- `break_events`: Pausenphasen und Pomodoro-bezogene Unterbrechungen

Für `break_events` werden neben Benutzer-, Projekt- und Zeitinformationen zusätzliche Key-Value-artige Fachattribute persistiert:

| Feld | Bedeutung |
|---|---|
| `break_kind` | Typ der Pause, z. B. `manual`, `short`, `long` |
| `is_auto` | Kennzeichnet, ob die Pause automatisch ausgelöst wurde |
| `source` | Fachliche Quelle der Pause, z. B. `custom_break` oder `pomodoro_break` |
| `pomodoro_cycle` | Nummer des aktuellen Pomodoro-Zyklus zum Zeitpunkt der Pause |
| `work_interval_minutes` | Konfiguriertes Arbeitsintervall in Minuten |

Diese zusätzlichen Attribute erlauben nicht nur eine operative Steuerung der GUI, sondern auch eine spätere Untersuchung von Arbeitsrhythmen, automatischen Pausenmustern und der Wirkung konfigurierter Arbeitsintervalle auf das individuelle Arbeitsverhalten.

### Tastenkürzel

| Kürzel | Aktion |
|---|---|
| `Ctrl+S` | Session starten |
| `Ctrl+E` | Session stoppen |
| `Ctrl+M` | Mini-Modus umschalten |
| `Ctrl+P` | Pause starten |

### Analyse-Dashboard
- **Durchgehend deutschsprachig**: Alle Plot-Titel, Achsenbeschriftungen und UI-Elemente
- **Eigenes Plotly-Template** `wotiti` mit definierter Farbpalette und Layoutvorgaben
- **4 Tab-Bereiche**: Grundlagen, Projekte & Muster, Zeitreihen & Trends, Erweiterte Analysen
- **Echtzeit-Visualisierungen** der Arbeitszeiten
- **Interaktive Grafiken** mit Drill-Down
- **Arbeitsmuster-Erkennung**
  - Frühe Starter (vor 8 Uhr)
  - Kernzeitarbeiter (9-17 Uhr)
  - Spätarbeiter (nach 17 Uhr)
- **Statistische Analysen**
  - Cluster-Analyse
  - ANOVA-Tests
  - Regressionsmodelle

## Analytische Verfahren

### Timestamp-Verarbeitung
- **Unterstützte Formate**:
  - YYYY-MM-DD HH:MM:SS (Standard)
  - DD-MM-YYYY HH:MM:SS
- **Automatische Konvertierung**
- **Einheitliche Speicherung**

### Analysemodelle
- **Clustering**: K-Means für Arbeitsmuster
- **Regression**: Vorhersagemodelle
- **ANOVA**: Gruppenvergleiche
- **Zeitreihen**: Trendanalysen

## Build und Distribution

### Build unter Linux
```bash
./build.sh
```

### Windows-EXE erstellen
Die Windows-EXE **muss auf einem Windows-System** gebaut werden (PyInstaller erzeugt plattformspezifische Binaries):

```powershell
# Auf einem Windows 10/11 System mit Python 3.10+ und uv:
.\build_windows.ps1
```

### Dokumentation des Release-Prozesses
Der vollständige Release-Workflow (inkl. GitHub-Veröffentlichung von Dateien/Assets) wurde in eine eigene Datei ausgelagert:

- [README_RELEASE.md](README_RELEASE.md)

> **Hinweis:** Die EXE-Binaries werden **nicht** ins Git-Repository eingecheckt (zu groß). Sie werden als **GitHub Release Assets** veröffentlicht.

### Technische Build-Details
- PyInstaller `--onedir` + `--noconsole`
- Hidden Imports: `tkinter.filedialog`, `sklearn`, `scipy`, unter Windows zusätzlich `winsound`
- Assets (`src/assets/`) werden eingebettet
- `data/`-Ordner wird neben die Anwendung kopiert
- `config.json` wird im Release-Build bewusst nicht mit ausgeliefert, damit keine entwicklerspezifischen Pfade verteilt werden
- `app_database.db` wird als leere Laufzeitdatenbank erzeugt
- Build-Skripte erzeugen Hilfsskripte für Autostart unter Windows und Linux

Beide Skripte erzeugen ein ausführbares Verzeichnis unter `dist/wotiti/` via PyInstaller (`--onedir`).

## Abhängigkeiten
- **GUI**: tkinter (Standardbibliothek)
- **Datenverarbeitung**: polars
- **Dashboard** (optional): dash, plotly, dash-bootstrap-components
- **Analysen** (optional): scikit-learn, scipy, statsmodels
- **Datenbank**: sqlite3 (Standardbibliothek)
- **Build** (optional): pyinstaller
- **Linting/Formatierung** (dev): ruff
- **Tests** (dev): pytest, pytest-cov

## Qualitätssicherung und Code-Qualität

- **Linting**: [ruff](https://docs.astral.sh/ruff/) (ersetzt flake8 + black), konfiguriert in `pyproject.toml`
- **Type Hints**: Alle öffentlichen Funktionen in `utils.py`, `db_helper.py` und `stats_plotting.py` sind typisiert (`from __future__ import annotations`)
- **Combobox-Caching**: Benutzer-/Projekt-Dropdowns werden nur bei Datenänderungen aktualisiert (Dirty-Flag)
- **Log-Rotation**: `RotatingFileHandler` (1 MB, 3 Backups) nach `data/wotiti.log`
- **Atomare Config-Writes**: `config.json` wird via tmp + `os.replace()` geschrieben

```bash
# Linting
ruff check src/ tests/

# Tests
python -m pytest tests/ -v
```

## Testdatengenerierung

Der Generator erzeugt statistisch aussagekräftige Beispieldaten auf Basis eines **Archetypenmodells**:

### Benutzer-Archetypen
| Archetyp | Arbeitszeit | Verhalten |
|---|---|---|
| **Frühaufsteher** | 06:00–14:00 | Fokussiert, wenige Projektwechsel |
| **Kernzeit-Arbeiter** | 09:00–17:00 | Moderate Wechselrate |
| **Spätarbeiter** | 11:00–19:30 | Viele kurze Blöcke, häufige Wechsel |
| **Teilzeit** | 08:00–13:00 | Kurzer Tag, keine Mittagspause |
| **Flexibler Arbeiter** | 07:00–18:00 | ±90 Min Startzeit-Variation, Context-Switcher |

### Eigenschaften des synthetischen Datensatzes
- **Wochenenden** werden übersprungen (nur Mo–Fr)
- **Kranktage** (~3 % der Arbeitstage)
- **Ausreißer-Tage** (~7 %: Überstunden oder halber Tag)
- **Wochentags-Effekte** (Mo/Fr kürzer, Mi am produktivsten)
- **Zeitlicher Trend** (Sinuswelle über 90 Tage)
- **Ermüdungskurve** (Blocklänge nimmt im Tagesverlauf ab)
- **Mittagspause** (30–60 Min, archetyp-abhängig)
- **Projekt-Spezialisierung** (Primärprojekt erhält 55–70 %)
- 10 Benutzer (2 pro Archetyp), 90 Tage → ~8.000 Events

### Beispielstruktur
```
user    project     event_type  timestamp           date
user_1  projekt_2   start      01-01-2025 06:12:00 2025-01-01
user_1  projekt_2   stop       01-01-2025 08:45:00 2025-01-01
```

## Konfiguration

Einstellungen werden in `data/config.json` persistiert und beim App-Start automatisch geladen.

| Option | Beschreibung | Standard |
|---|---|---|
| `database_path` | Pfad zur aktiven SQLite-Datenbank | `data/app_database.db` |
| `default_user` | Vorausgewählter Benutzer beim Start | `Hans` |
| `default_project` | Vorausgewähltes Projekt beim Start | `1` |
| `dashboard_port` | Startport für das Analyse-Dashboard | `8052` |
| `theme` | Farbschema für das Dashboard | `Modern` |
| `window_geometry` | Letzte Geometrie des Hauptfensters | `""` |
| `mini_window_position` | Letzte Position des Mini-Fensters (`+x+y`) | `""` |
| `pomodoro_enabled` | Pomodoro-Modus aktivieren/deaktivieren | `false` |
| `pomodoro_work_minutes` | Länge der Arbeitsphase in Minuten | `25` |
| `pomodoro_break_minutes` | Länge der kurzen Pause in Minuten | `5` |
| `pomodoro_long_break_minutes` | Länge der langen Pause in Minuten | `15` |
| `pomodoro_long_break_every` | Lange Pause nach N Arbeitsphasen | `4` |
| `pomodoro_auto_break` | Automatische Pause/Fortsetzung nutzen | `true` |
| `pomodoro_sound_enabled` | Ton bei Pause-Start und Pause-Ende | `true` |
| `pomodoro_sound_local_path` | Relativer oder absoluter Pfad zur Sounddatei | `sounds/StartupSound.wav` |

Alle Optionen sind über das Einstellungsfenster der GUI erreichbar.

Hinweis zur Auswertung: Das Dashboard nutzt weiterhin primär `events` für Arbeitsphasen. Pausen werden separat in `break_events` gespeichert, damit Arbeitszeit- und Pausenlogik analytisch getrennt bleiben.

Für analytische Fragestellungen zum Arbeitsrhythmus sind die in `break_events` abgelegten Pomodoro-Metadaten relevant, da sie die Arbeitszeitdaten um strukturelle Informationen zu Pausenursprung, Intervalllänge und Zyklusfortschritt ergänzen.

Empfohlene Ablage für manuell bereitgestellte Sounddateien: `data/sounds/`.

## Bekannte Einschränkungen
- Timestamp-Konvertierung bei ungewöhnlichen Formaten
- CPU-Last bei komplexen Dashboard-Analysen
- Port-Änderung in den Einstellungen wird erst beim nächsten App-Start wirksam
- Theme-Umschaltung erfordert Dashboard-Neustart

## Geplante Erweiterungen
- [ ] Export-Funktionen für Analysen
- [ ] API-Schnittstelle
- [ ] Docker-Container
- [ ] Automatische Backups
- [ ] GitHub Actions CI/CD (automatisierte Builds bei Tag-Push)

## Mitwirkung
1. Fork des Repositories
2. Feature-Branch erstellen
3. Änderungen committen
4. Pull Request erstellen

## Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert.