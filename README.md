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
- Pomodoro-Unterstützung mit konfigurierbaren Arbeits- und Pausenintervallen
- Mini-Modus als separates Always-on-top Fenster mit persistenter Position
- Dashboard für deskriptive, visuelle und statistische Auswertungen
- Standalone-Builds für Linux und Windows via PyInstaller

## tl;dr - Schnellstart

### Vorgebaute Binärdatei (einfachste Methode)

**[Lade die neueste Version herunter](https://github.com/grenzenloseSchublade/wotiti/releases):**
- Linux x64: [wotiti_1_1-linux-x64.zip](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-linux-x64.zip)
- Windows x64: [wotiti_1_1-win-x64.zip](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-win-x64.zip)

Entpacken → Ausführen. Fertig!

### Aus Quellcode

Ausführung aus dem Quellcode:
```bash
pip install uv
uv sync
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
  ▮▮ = Pausenzeit heute
```

Der Timer zeigt primär die **Tagesarbeitszeit** pro Projekt. Die Gesamtzeit über alle Tage und die heutige Pausensumme werden kompakt darunter angezeigt — Hover-Tooltips erklären die Werte.

**Mini-Modus** (▽/△): Kompakte Always-on-top Ansicht mit Tageszeit, Drag-Support und persistenter Position.

**Funktionsumfang**

- Drei-Zustands-Logik für Arbeitssitzungen: Start, Pause, Stop
- Mehrbenutzer-Unterstützung mit Dropdown-Auswahl
- Projektbasierte Zeiterfassung mit Combobox (intelligentes Caching)
- Benutzerverwaltung (eigenes Fenster zum Anlegen/Auswählen)
- **Tastenkürzel**: `Ctrl+S` Start, `Ctrl+E` Stop, `Ctrl+M` Mini-Modus, `Ctrl+P` Pause
- **Einstellungen**: Datenbank, Defaults, Port, Theme, Entwickler-Konsole, Pomodoro-Optionen, Über-Dialog
- Persistente Konfiguration (`data/config.json`)
- SQLite-Datenbankintegration (users, projects, events, break_events)
- Separate Break-Tabellenlogik für manuelle und Pomodoro-Pausen
- Automatische Bereinigung verwaister Sessions und Pausen nach unsauberem Beenden
- Echtzeit-Timer-Anzeige (Tageszeit + Gesamtzeit)
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

Für eine entwicklungsorientierte, technisch tiefere Beschreibung der Python-Module siehe [src/README.md](src/README.md).

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

## Fachliches Kernmodell

Die Anwendung arbeitet mit zwei logisch getrennten Datentypen:

- `events` für Arbeitsphasen
- `break_events` für Pausenphasen und Pomodoro-bezogene Unterbrechungen

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

Die Laufzeitkonfiguration wird in `data/config.json` gespeichert.

Wichtige Konfigurationsbereiche:

- aktive Datenbank
- Standardbenutzer und Standardprojekt
- Dashboard-Port
- Theme
- Pomodoro-Parameter
- Sounddatei und Mini-Fenster-Position

## Bekannte Einschränkungen

- Timestamp-Konvertierung bei ungewöhnlichen Formaten
- CPU-Last bei komplexen Dashboard-Analysen
- Port-Änderungen werden erst nach Neustart wirksam
- Theme-Umschaltung erfordert Neustart des Dashboards

## Geplante Erweiterungen

- Export-Funktionen für Analysen
- Docker-Container
- GitHub Actions für Build-Automatisierung

## Mitwirkung

1. Repository forken
2. Feature-Branch anlegen
3. Änderungen committen
4. Pull Request erstellen

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.