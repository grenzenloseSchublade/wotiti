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
> - Integriertes Analytics-Dashboard mit Cluster-Analyse, Regression, ANOVA
> - SQLite-Datenbank, keine externe Infrastruktur nötig
> - Standalone-EXE via PyInstaller (`bash build.sh` / `build_windows.ps1`)

## 🎯 Systemübersicht

### Work Time Timer (GUI)
- Start/Stop-Funktionalität für Arbeitssitzungen
- Mehrbenutzer-Unterstützung mit Dropdown-Auswahl
- Projektbasierte Zeiterfassung mit Combobox
- Benutzerverwaltung (eigenes Fenster zum Anlegen/Auswählen)
- SQLite-Datenbankintegration (users, projects, events)
- Echtzeit-Timer-Anzeige
- Session-Schutz bei App-Schließen
- Eingabevalidierung (Datumsformat DD-MM-YYYY)

### Work Time Insights (Dashboard)
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
│   ├── utils.py             # Hilfsfunktionen & Konfiguration
│   └── assets/
│       └── style.css        # Dashboard-Styles
├── data/                    # Datenspeicherung (SQLite DBs, gitignored)
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
- **Datum-Setter**: Schnelle Datumseinstellung mit Validierung (DD-MM-YYYY)
- **Gesamtzeit**: Zeigt die kumulierte Arbeitszeit pro Benutzer/Projekt
- **Konsole**: Statusmeldungen und Fehler
- **Session-Schutz**: Warnung bei App-Schließen mit aktiver Session

### Analytics-Dashboard Features
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

### Features
- Flexible Benutzer- und Projektzahlen
- Realistische Arbeitszeitverteilung
- Verschiedene Speicheroptionen (CSV/DB)
- Parameter-Logging für Reproduzierbarkeit

### Beispieldaten
```
user    project     event_type  timestamp           date
user_1  projekt_3   start      01-01-2023 09:00:00 01-01-2023
user_1  projekt_3   stop       01-01-2023 10:30:00 01-01-2023
```

## 🐛 Bekannte Probleme
- Timestamp-Konvertierung bei ungewöhnlichen Formaten
- CPU-Last bei komplexen Dashboard-Analysen

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