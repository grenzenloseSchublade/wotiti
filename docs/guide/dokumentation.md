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

### Wochenansicht (Zeitmaschine)

Die Timer-Kachel lässt sich auf eine scrollbare 7-Tage-Übersicht umschalten:

- Balkendiagramm der Tagesarbeitszeiten mit stabilen Projektfarben
- Navigation durch beliebige Wochen per Pfeilen (‹ ›), der Titel zeigt die Kalenderwoche (KW)
- Wochenenden grau, Feiertage rot markiert (Land/Region konfigurierbar in den Einstellungen)

### Tagesnotizen und Übertragen-Status

Pro Benutzer, Projekt und Tag kann eine **Notiz** (max. 44 Wörter) erfasst werden – als Gedächtnisstütze für den manuellen Übertrag der Zeiten in ein Firmensystem. Ist der Übertrag erledigt, markiert die Checkbox **„übertragen"** den Projekt-Tag (mit Zeitstempel); der Status erscheint als `✓ übertragen` in der Ereignisliste und in der Wochenansicht. Dort lassen sich Tage einzeln per Tages-Häkchen oder gesammelt per Wochen-Häkchen abhaken.

### Tastenkürzel

| Kombination | Funktion |
|-------------|----------|
| `Strg+S` | Start |
| `Strg+E` | Stop |
| `Strg+P` | Pause / Resume |
| `Strg+M` | Mini-Modus an/aus |
| `Strg+←` / `Strg+→` | Tag zurück / vor |
| `Strg+T` | Heute |
| `F5` | Anzeige neu laden |

Die Shortcuts funktionieren auch wenn das Timer-Fenster im Hintergrund ist.

### Themes

Zwei integrierte Themes, umschaltbar in Einstellungen → Appearance:

- **Modern** (Standard) – helles Interface, Cyan/Pink-Farbschema
- **Synthwave** – dunkler Retro-Look, augenfreundlich für lange Sessions


### Menüleiste und Verwaltung (v2.2.0)

Selten genutzte Aktionen liegen in der Menüleiste: **Datei** (Datenbank laden, Beenden), **Ansicht** (Wochen-/Timer-Ansicht, Mini-Modus, Neu laden F5), **Extras** (Auswertung, Einstellungen), **Hilfe** (Über). Sichtbare Buttons sind nur Start/Pause/Stop/Mini.

In **Einstellungen → Verwaltung** lassen sich Benutzer und Projekte **ausblenden (archivieren)** und wieder einblenden: Archivierte Einträge verschwinden aus den Auswahl-Listen, ihre Daten (Zeiten, Notizen, Statistik) bleiben vollständig erhalten. Neue Benutzer/Projekte werden weiterhin direkt über die Comboboxen im Hauptfenster angelegt.

Bei **Rechner-Standby** (z. B. übers Wochenende) wird eine laufende Session automatisch beendet — der Stop wird auf den Zeitpunkt vor dem Standby **rückdatiert**, ebenso beim Inaktivitäts-Auto-Stop (konfigurierbare Schwelle, Standard 120 min; kurze Pausen zählen weiter als Arbeitszeit).

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

### KW-Report (v2.3.0)

Erster Tab des Dashboards: die **Kalenderwochen-Matrix** Projekt × Mo–So in **H:MM** — exakt die Werte für den manuellen Übertrag ins Firmensystem. Mit KW-Navigation (‹ ›), Zeilen-/Spaltensummen, ✓ an bereits übertragenen Tagen (Tooltip zeigt Übertragungsdatum), ° markiert Tagesnotizen (Volltext im Tooltip) und einem Hinweis-Badge für offene (nicht übertragene) Tage. Der frühere Tab „Erweitert" (Cluster/Regression/Benutzer-ANOVA) wurde entfernt; „Projekt-Unterschiede" lebt jetzt im Tab „Projekte & Muster".


Interaktives Dashboard, erreichbar unter `http://localhost:8050` (Port konfigurierbar). Das Dashboard wird im Hintergrund gestartet, sobald der Timer aktiv ist.

### Tab 1: KW-Report

Kalenderwochen-Matrix Projekt × Mo–So in H:MM mit ✓ (übertragen), Notiz-Markern und Offen-Badge — siehe Abschnitt oben.

### Tab 2: Übersicht

Eckdaten der geladenen Datenbasis: Gesamtstunden, Zeitraum, Arbeitstage, Sessions, Projekte/Benutzer, Datenqualitäts-Badges (offene Sessions, Wochenend-/Feiertags-Einträge). Datums- und Projektfilter wirken hier, der Wochenend-Schalter bewusst nicht.

### Tab 3: Grundlagen

Stunden pro Projekt (Kreisdiagramm), Gesamtstunden und Ø Stunden pro Tag. Bei nur einem Benutzer werden die Vergleichs-Controls automatisch ausgeblendet.

### Tab 4: Projekte & Muster

Projektzeit-Statistiken, Tägliche Projektstunden (eine Linie je Projekt), Projektwechsel, Ø Startzeit pro Projekt, Startzeit- und Session-Dauer-Verteilung, Projekt-Unterschiede (explorativ).

### Tab 5: Zeitreihen

Wöchentliche Durchschnittsstunden (Schlüssel `JJJJ-KWnn`, jahresübergreifend eindeutig), Wochentags-Muster (Ø je gearbeitetem Tag, mit Stichproben-Anzahl im Hover), Aktivitäts-Heatmap, Arbeit vs. Pause.

Alle Zeiten erscheinen in Tooltips/Beschriftungen als **H:MM** — identisch zur App. Globale Filter: Datumsbereich (mit Schnellwahl „Diese Woche / Letzte Woche / Alles"), Projekte, Wochenend-Schalter (Startzustand aus der Config, danach gewinnt der Schalter).

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
