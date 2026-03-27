# WoTiTi - Work Time Tracker & Insights 🕒

WoTiTi ist ein umfassendes Zeiterfassungssystem, bestehend aus zwei Hauptkomponenten:
1. **Work Time Timer**: Eine benutzerfreundliche GUI-Anwendung zur Zeiterfassung
2. **Work Time Insights**: Ein fortgeschrittenes Analyse-Dashboard für Zeitdaten

## ⚡ TL;DR

> **Was?** Desktop-App (tkinter) zum Tracken von Arbeitszeiten pro Benutzer und Projekt, mit integriertem Analytics-Dashboard (Dash/Plotly).
>
> **Schnellstart:**
> ```bash
> pip install uv && uv sync && uv run python src/main.py
> ```
>
> **Kernfunktionen:**
> - ▶ Start / ■ Stop pro Benutzer & Projekt mit Echtzeit-Timer
> - Benutzerverwaltung (Dropdown-Auswahl, eigenes Verwaltungsfenster)
> - Projektverwaltung (Combobox mit bestehenden Projekten)
> - ⚙ Einstellungen (Datenbank wechseln/erstellen/löschen, Defaults, Theme)
> - Integriertes Analytics-Dashboard mit Cluster-Analyse, Regression, ANOVA
> - SQLite-Datenbank, keine externe Infrastruktur nötig
> - Konfiguration wird in `data/config.json` persistiert
> - Standalone-EXE via PyInstaller (`bash build.sh` / `build_windows.ps1`)

## 🎯 Systemübersicht

### Work Time Timer (GUI)
- Start/Stop-Funktionalität für Arbeitssitzungen
- Mehrbenutzer-Unterstützung mit Dropdown-Auswahl
- Projektbasierte Zeiterfassung mit Combobox
- Benutzerverwaltung (eigenes Fenster zum Anlegen/Auswählen)
- **Einstellungen (⚙)**: Datenbank erstellen/auswählen/löschen, Standard-Benutzer/-Projekt, Dashboard-Port, Theme
- Persistente Konfiguration (`data/config.json`)
- SQLite-Datenbankintegration (users, projects, events)
- Echtzeit-Timer-Anzeige
- Session-Schutz bei App-Schließen
- Eingabevalidierung (Datumsformat DD-MM-YYYY)

### Work Time Insights (Dashboard)
- Durchgehend **deutschsprachige** Oberfläche (Titel, Achsen, UI-Elemente)
- Eigenes Plotly-Template „wotiti" (Dark Theme, konsistente Farben, automargin)
- 4 Tab-Bereiche: Grundlagen, Projekte & Muster, Zeitreihen & Trends, Erweiterte Analysen
- Interaktive Datenvisualisierung
- Fortgeschrittene statistische Analysen
- Arbeitsmuster-Erkennung
- Vorhersagemodelle
- Vergleichsanalysen

## 📁 Projektstruktur

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
├── data/                    # Datenspeicherung (SQLite DBs, config.json, gitignored)
├── tests/
│   ├── test_app.py         # GUI-Tests
│   └── test_db_helper.py   # Datenbank-Tests
├── build.sh                # Linux/macOS Build-Skript
├── build_windows.ps1       # Windows Build-Skript
├── pyproject.toml          # uv/pyproject-Konfiguration
└── README.md
```

## 🚀 Installation & Setup

```bash
# Repository klonen
git clone https://github.com/yourusername/wotiti.git

# uv installieren
pip install uv

# Abhängigkeiten installieren (Basis)
uv sync

# Optional: Stats/Dev-Abhängigkeiten
uv sync --extra stats --extra dev
```

## 📊 Verwendung

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

## 🔧 Funktionen im Detail

### Timer-GUI Komponenten
- **Start/Stop-Buttons**: Prominente Sitzungssteuerung (▶/■)
- **Benutzer-Auswahl**: Combobox mit Dropdown aller bestehenden Benutzer
- **Projekt-Auswahl**: Combobox mit bestehenden Projekten
- **Benutzerverwaltung**: Eigenes Fenster zum Anlegen/Auswählen von Benutzern
- **Einstellungen (⚙)**: Konfigurationsfenster mit:
  - Datenbank auswählen, erstellen oder löschen (mit Bestätigung)
  - Standard-Benutzer und Standard-Projekt festlegen
  - Dashboard-Port konfigurieren
  - Theme-Auswahl (Modern / Synthwave)
- **Datum-Setter**: Schnelle Datumseinstellung mit Validierung (DD-MM-YYYY)
- **Gesamtzeit**: Zeigt die kumulierte Arbeitszeit pro Benutzer/Projekt
- **Konsole**: Statusmeldungen und Fehler
- **Session-Schutz**: Warnung bei App-Schließen mit aktiver Session

### Analytics-Dashboard Features
- **Durchgehend deutschsprachig**: Alle Plot-Titel, Achsenbeschriftungen und UI-Elemente
- **Eigenes Plotly-Template** „wotiti": Dark Theme, 8-Farben-Palette, automargin, Inter-Font
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

## 📈 Datenanalyse

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

## 🛠️ Build-Optionen

### Linux / macOS
```bash
./build.sh
```

### Windows (PowerShell)
```powershell
.\build_windows.ps1
```

Beide Skripte erzeugen ein ausführbares Verzeichnis unter `dist/wotiti/` via PyInstaller (`--onedir`).

## 📚 Dependencies
- **GUI**: tkinter (Standardbibliothek)
- **Datenverarbeitung**: polars
- **Dashboard** (optional): dash, plotly, dash-bootstrap-components
- **Analysen** (optional): scikit-learn, scipy, statsmodels
- **Datenbank**: sqlite3 (Standardbibliothek)
- **Build** (optional): pyinstaller

## 🔍 Testdatengenerierung

Der Generator erzeugt statistisch aussagekräftige Beispieldaten mit einem **Archetypen-System**:

### Benutzer-Archetypen
| Archetyp | Arbeitszeit | Verhalten |
|---|---|---|
| **Frühaufsteher** | 06:00–14:00 | Fokussiert, wenige Projektwechsel |
| **Kernzeit-Arbeiter** | 09:00–17:00 | Moderate Wechselrate |
| **Spätarbeiter** | 11:00–19:30 | Viele kurze Blöcke, häufige Wechsel |
| **Teilzeit** | 08:00–13:00 | Kurzer Tag, keine Mittagspause |
| **Flexibler Arbeiter** | 07:00–18:00 | ±90 Min Startzeit-Variation, Context-Switcher |

### Realismus-Features
- **Wochenenden** werden übersprungen (nur Mo–Fr)
- **Kranktage** (~3 % der Arbeitstage)
- **Ausreißer-Tage** (~7 %: Überstunden oder halber Tag)
- **Wochentags-Effekte** (Mo/Fr kürzer, Mi am produktivsten)
- **Zeitlicher Trend** (Sinuswelle über 90 Tage)
- **Ermüdungskurve** (Blocklänge nimmt im Tagesverlauf ab)
- **Mittagspause** (30–60 Min, archetyp-abhängig)
- **Projekt-Spezialisierung** (Primärprojekt erhält 55–70 %)
- 10 Benutzer (2 pro Archetyp), 90 Tage → ~8.000 Events

### Beispieldaten
```
user    project     event_type  timestamp           date
user_1  projekt_2   start      01-01-2025 06:12:00 2025-01-01
user_1  projekt_2   stop       01-01-2025 08:45:00 2025-01-01
```

## ⚙ Konfiguration

Einstellungen werden in `data/config.json` persistiert und beim App-Start automatisch geladen.

| Option | Beschreibung | Standard |
|---|---|---|
| `database_path` | Pfad zur aktiven SQLite-Datenbank | `data/app_database.db` |
| `default_user` | Vorausgewählter Benutzer beim Start | `Hans` |
| `default_project` | Vorausgewähltes Projekt beim Start | `1` |
| `dashboard_port` | Startport für das Analytics-Dashboard | `8052` |
| `theme` | Farbschema für das Dashboard | `Modern` |

Alle Optionen sind über das Zahnrad-Menü (⚙) in der GUI erreichbar.

## 🐛 Bekannte Probleme
- Timestamp-Konvertierung bei ungewöhnlichen Formaten
- CPU-Last bei komplexen Dashboard-Analysen
- Port-Änderung in den Einstellungen wird erst beim nächsten App-Start wirksam
- Theme-Umschaltung erfordert Dashboard-Neustart

## 🔜 Geplante Features
- [ ] QT-Migration (geplant für späteres Release)
- [ ] Export-Funktionen für Analysen
- [ ] Nachträgliche Zeitkorrekturen
- [ ] API-Schnittstelle
- [ ] Docker-Container
- [ ] Automatische Backups
- [ ] Performance-Optimierungen

## 🤝 Beitragen
1. Fork des Repositories
2. Feature-Branch erstellen
3. Änderungen committen
4. Pull Request erstellen

## 📝 Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert.