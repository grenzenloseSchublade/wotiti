---
description: "WoTiTi Dokumentation – Funktionsreferenz, Bedienungsanleitung und Konfiguration."
---

# Dokumentation

Vollständige Referenz zu allen Funktionen, Konfigurationsoptionen und Arbeitsabläufen.

WoTiTi besteht aus zwei Komponenten: der **Erfassungs-App** (Timer) und dem **Analytics-Dashboard**. Diese Seite beschreibt beide.

---

## Erfassungskomponente (Work Time Timer)

### Start, Pause, Stop

Die drei operativen Zustände:

- **[🟢 START]** – Arbeitssitzung beginnt, Timer läuft
- **[🟡 PAUSE]** – Unterbrechung, Timer pausiert, Session bleibt offen
- **[🔴 STOP]** – Sitzung wird beendet und in der Datenbank gespeichert

Jede Session wird mit Benutzer, Projekt, Startzeit, Dauer und Pausen-Intervallen persistiert.

### Benutzer und Projekte

- **Mehrbenutzer-Support**: Benutzer über „Benutzer verwalten" anlegen, aktiver Benutzer per Dropdown auswählen
- **Projektbasierte Kategorisierung**: Projekt-Dropdown mit Autovervollständigung, neue Projekte on-the-fly erstellbar
- Projekte sind benutzerübergreifend (geteilt)

### Pomodoro

Konfigurierbare Fokus-Intervalle:

| Parameter | Standard |
|-----------|----------|
| Arbeitsblock | 25 min |
| Kurze Pause | 5 min |
| Sessions bis lange Pause | 4 |
| Lange Pause | 15 min |

Pausen werden automatisch vorgeschlagen und separat erfasst (`break_events`-Tabelle). Alle Pomodoro-Parameter sind in den Einstellungen änderbar.

### Mini-Modus

Kompakte Always-on-Top-Ansicht (`Ctrl+M`):

- Schwebt über anderen Fenstern, frei verschiebbar
- Zeigt nur Timer und Start/Stop/Pause
- Fensterposition wird persistent gespeichert

### Tastenkürzel

| Kombination | Funktion |
|-------------|----------|
| `Ctrl+S` | Start |
| `Ctrl+E` | Stop |
| `Ctrl+P` | Pause / Resume |
| `Ctrl+M` | Mini-Modus an/aus |

Die Shortcuts funktionieren auch wenn das Timer-Fenster im Hintergrund ist.

### Themes

Zwei integrierte Themes, umschaltbar in Einstellungen → Appearance:

- **Modern** (Standard) – helles Interface, Cyan/Pink-Farbschema
- **Synthwave** – dunkler Retro-Look, augenfreundlich für lange Sessions

### Einstellungen

Erreichbar über Menü → Einstellungen:

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| Datenbank-Pfad | Speicherort der SQLite-DB | `data/wotiti.db` |
| Standard-Benutzer | Vorausgewählter Benutzer | – |
| Dashboard-Port | Port für Analytics-Dashboard | 8050 |
| Theme | Modern / Synthwave | Modern |
| Pomodoro-Optionen | Intervall-Längen | s. oben |
| Entwickler-Konsole | Debug-Output aktivieren | aus |

### Datenspeicherung

- **Format**: SQLite (`data/wotiti.db`)
- **Tabellen**: `users`, `projects`, `events` (Arbeitszeiten), `break_events` (Pausen)
- **Backup**: `.db`-Datei kopieren. Die Datenbank ist nicht verschlüsselt; für sensible Daten wird Festplattenverschlüsselung empfohlen (BitLocker, LUKS).

### Session-Schutz

Bei aktivem Timer wird beim Schließen eine Bestätigung angefordert. Nicht beendete Sessions werden bei Neustart wiederhergestellt.

---

## Analysekomponente (Work Time Insights)

Interaktives Dashboard, erreichbar unter `http://localhost:8050` (Port konfigurierbar). Das Dashboard wird im Hintergrund gestartet, sobald der Timer aktiv ist.

### Tab 1: Grundlagen

Tages-, Wochen- und Monatssummen, Trend-Pfeile, Top-Projekte, durchschnittliche Session-Länge.

### Tab 2: Projekte und Muster

Projekt-Breakdown (Kreisdiagramm), Heatmap (wann an welchem Projekt), Sessions pro Projekt, Detailtabelle.

### Tab 3: Zeitreihen und Trends

Produktivitätskurven, Tagesmuster (Peak-Zeiten), Wochenmuster, Fokus-Stabilität, Pausendisziplin.

### Tab 4: Erweiterte Analysen

- **Deskriptive Statistiken**: Mittelwert, Median, Standardabweichung, Quartile
- **Prognosen** (scikit-learn): Arbeitszeit-Vorhersage, Anomalie-Detektion, Clustering. Aussagekräftiger nach 4–8 Wochen regelmäßiger Nutzung; dient als Orientierungswert.
- **Korrelationsanalysen**: Pomodoro-Disziplin ↔ Gesamtarbeitszeit, Pausenlänge ↔ Fokus-Qualität

---

## Datenfluss

```
┌─────────────────────┐
│  Work Time Timer    │ ← Zeiterfassung
└──────────┬──────────┘
           │ speichert
           ↓
   ┌───────────────┐
   │  SQLite DB    │ ← Lokal gespeichert
   │ (wotiti.db)   │
   └───────┬───────┘
           │
           ↓ liest
   ┌─────────────────────┐
   │ Work Time Insights  │ ← Dashboard
   │  (Dash/Plotly)      │
   └─────────────────────┘
       (http://localhost:8050)
```

Das System ist vollständig offline: keine API-Aufrufe, keine Telemetrie, keine Cloud-Anbindung.

---

## Erste Schritte

### 1. Benutzer und Projekt anlegen

1. „Benutzer verwalten" öffnen → Name eingeben → Hinzufügen
2. Projekt-Dropdown → Projektname eingeben → Enter

### 2. Erste Zeiterfassung

1. **START** (`Ctrl+S`) → Timer läuft
2. Nach 25 min: **PAUSE** (`Ctrl+P`) → kurze Pause
3. Weiterarbeiten: **START** erneut
4. Fertig: **STOP** (`Ctrl+E`) → Session wird gespeichert

### 3. Dashboard nutzen

Browser öffnen: `http://localhost:8050` → Tab wählen → Daten analysieren.

---

## Typische Arbeitsabläufe

### Pomodoro-Workflow

```
08:00 → Projekt wählen, START
08:25 → PAUSE (Auto-Vorschlag)
08:30 → START (neuer Block)
08:55 → STOP
```

### Mehrere Projekte am Tag

```
09:00–09:45  "Team-Meeting"     → 45 min
10:00–12:00  "Dokumentation"    → 120 min
13:30–15:00  "Bug-Fixes"        → 90 min
```

Mittagspause wird nicht erfasst.

---

## Best Practices

**Empfohlen:**

- Täglich Sessions starten – Konsistenz verbessert Datenqualität
- Pausen eintragen – ermöglicht Produktivitätsanalysen
- Projektnamen konsistent halten – „Projekt A" ≠ „Project A"
- Wöchentlich Dashboard reviewen
- Regelmäßig Backup der `.db`-Datei erstellen

**Zu vermeiden:**

- Mehrere Timer gleichzeitig (DB-Konflikte)
- Port-Konflikte mit anderen Anwendungen auf 8050

---

## Troubleshooting

### Dashboard zeigt alte oder keine Daten

1. Browser-Cache leeren (`Ctrl+Shift+R`)
2. Prüfen ob Timer aktiv ist (Dashboard startet mit dem Timer)
3. Port-Einstellungen prüfen

### Mini-Modus nicht sichtbar

`Ctrl+M` drücken, um Fenstergröße zu wechseln, dann repositionieren. Bei Bedarf WoTiTi neu starten.

### Datenexport

Direkter CSV-Export ist geplant. Workaround: SQLite-Datenbank mit [SQLiteBrowser](https://sqlitebrowser.org/) öffnen oder per Python-Script exportieren:

```python
import sqlite3, pandas as pd
df = pd.read_sql("SELECT * FROM events", sqlite3.connect("data/wotiti.db"))
df.to_csv("export.csv")
```

---

## Erweiterte Nutzung

### Datenbank-Speicherort ändern

Einstellungen → Datenbank-Pfad → neuen Pfad eingeben → Neustart.

### Mehrere Instanzen

Separate Ordner mit separaten Konfigurationen verwenden. Beispiel:

- Instanz 1: Port 8050, DB `data/wotiti.db`
- Instanz 2: Port 8051, DB `data2/wotiti.db`

---

## Weitere Ressourcen

- [Installation](../installation/index.md) – Installationsanleitung
- [Contributing](../contributing-guide.md) – Für Entwickler
- [GitHub Repository](https://github.com/grenzenloseSchublade/wotiti) – Quellcode, Issues, Discussions
