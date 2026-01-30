# WoTiTi - Work Time Tracker & Insights 🕒

WoTiTi ist ein umfassendes Zeiterfassungssystem, bestehend aus zwei Hauptkomponenten:
1. **Work Time Timer**: Eine benutzerfreundliche GUI-Anwendung zur Zeiterfassung
2. **Work Time Insights**: Ein fortgeschrittenes Analyse-Dashboard für Zeitdaten

## 🎯 Systemübersicht

### Work Time Timer (GUI)
- Start/Stop-Funktionalität für Arbeitssitzungen
- Mehrbenutzer-Unterstützung
- Projektbasierte Zeiterfassung
- SQLite-Datenbankintegration
- Echtzeit-Timer-Anzeige
- Nachträgliche Zeitkorrekturen

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
│   ├── main.py              # GUI-Hauptanwendung
│   ├── app.py               # GUI-Implementation
│   ├── db_helper.py         # Datenbankoperationen
│   ├── stats_dashboard.py   # Analyse-Dashboard
│   ├── stats_calculations.py # Statistische Berechnungen
│   ├── stats_plotting.py    # Visualisierungsfunktionen
│   ├── stats_generator.py   # Testdatengenerierung
│   └── utils.py             # Hilfsfunktionen
├── data/                    # Datenspeicherung
├── tests/                   # Testdateien
│   ├── test_app.py         # GUI-Tests
│   └── test_db_helper.py   # Datenbank-Tests
├── pyproject.toml          # uv/pyproject-Konfiguration
└── README.md              # Dokumentation
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
- **Start/Stop-Buttons**: Sitzungssteuerung
- **Projekt-Auswahl**: Zuordnung von Zeiten
- **Benutzer-Management**: Mehrbenutzer-Unterstützung
- **Datum-Setter**: Schnelle Datumseinstellung
- **Konsole**: Statusmeldungen und Fehler

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

### uv Build (empfohlen)
```bash
uv run pyinstaller --onefile --windowed src/main.py
```

### Debian 11 Build (GLIBC 2.31)
```bash
pip install pyinstaller==6.12
pyinstaller --windowed --onefile src/main.py
```

## 📚 Dependencies
- **GUI**: tkinter
- **Dashboard**: dash, plotly
- **Datenverarbeitung**: pandas, numpy
- **Analysen**: scikit-learn, scipy
- **Datenbank**: sqlite3

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
- CPU-Last bei komplexen Analysen
- Async-Timer-Implementierung ausstehend

## 🔜 Geplante Features
- [ ] Export-Funktionen für Analysen
- [ ] Erweiterte Benutzerrollen
- [ ] API-Schnittstelle
- [ ] Docker-Container
- [ ] Automatische Backups
- [ ] Nachträgliche Zeitkorrekturen
- [ ] Performance-Optimierungen

## 🤝 Beitragen
1. Fork des Repositories
2. Feature-Branch erstellen
3. Änderungen committen
4. Pull Request erstellen

## 📝 Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert.