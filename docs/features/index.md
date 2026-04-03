---
description: "WoTiTi Features – Zeiterfassung, Pomodoro-Timer, Mini-Modus, Dashboard-Analysen, Themes und mehr."
---

# ✨ Features & Funktionalität

WoTiTi hat zwei Hauptkomponenten: die **Erfassungs-App** (Timer) und das **Analytics-Dashboard**. Hier ist eine komplette Übersicht.

---

## 🎯 Erfassungs­komponente (Work Time Timer)

Die **operative Schnittstelle** für schnelle Zeiterfassung im Alltag.

### Start / Pause / Stop Logic

Die Kernfunktion von WoTiTi:

- **[🟢 START]** – Arbeits­sitzung startet, Timer läuft
- **[🟡 PAUSE]** – Kurze Unterbrechung (Kaffee, Toilette), Timer pausiert, Zeit wird noch nicht als "Arbeitszeit" gezählt
- **[🔴 STOP]** – Arbeits­sitzung endet, Daten werden in DB gespeichert

Jede Session wird mit:
- Benutzer
- Projekt
- Start­zeit
- Dauer
- Pausen-Intervalle

…gespeichert.

### Mehrbenutzer-Support

WoTiTi unterstützt mehrere Benutzer im gleichen System:

- **Benutzer hinzufügbar** über Fenster "Benutzer verwalten"
- **Aktiver Benutzer** ist immer sichtbar (Dropdown)
- **Separate Zeitverfolgung** pro Benutzer & Projekt
- Ideal für:
  - Shared Workstations
  - Team-Zeiterfassung
  - Separate Rollen (z.B. Entwickler vs. Manager)

### Projektbasierte Kategorisierung

Alle erfassten Stunden werden auf **Projekte** verteilt:

- **Projekt-Dropdown** mit intelligenter Autovervollständigung
- **Neue Projekte** können on-the-fly hinzugefügt werden
- **Projekt-Historie** wird gecacht für schnelle Auswahl
- Projekte sind **Benutzer-übergreifend** (geteilt)

**Beispiel-Projekte:**
- `Kundenauftrag A – Web-Redesign`
- `Interne Spielzeit – Forschung`
- `Admin – Meetings & Overhead`

### 🍅 Pomodoro-Integriert

Gezielte Fokus-Intervalle:

- **Konfigurierbare Arbeits-/Pausenintervalle**: Standard 25 min Arbeit / 5 min Pause
- **Automatische Pause-Erkennung**: Nach konfig. Zeit auto­matisch Pause vorschlagen
- **Break-Tracking**: Pausen werden separat erfasst (wichtig für Analysen!)
- **Pomodoro-Statistiken** im Dashboard sichtbar

**Einstellungen:**
- Arbeitsblock-Länge (z.B. 25 min)
- Kurze-Pause-Länge (z.B. 5 min)
- Lange-Pause nach N Sessions (z.B. alle 4 Sessions)
- Lange-Pause-Länge (z.B. 15 min)

### 📌 Mini-Modus (Always-on-Top)

Kompakte Fenster-Variante, die nie im Weg ist:

- **Toggle**: `Ctrl+M` oder Button "▼ Mini" / "▲ Max"
- **Always-on-Top**: Schwebt über anderen Fenstern
- **Draggable**: Kann beliebig repositioniert werden
- **Position persistent**: Letzte Position wird nach App-Neustart wiederhergestellt
- **Minimales UI**: Nur Timer + Start/Stop/Pause sichtbar
- **Ideal für**: Multi-Monitor-Setups, ablenkungsfreie Arbeit

### ⌨️ Tastenkürzel (Shortcuts)

| Tastenkombination | Funktion |
|------------------|----------|
| `Ctrl+S` | Start Arbeits­sitzung |
| `Ctrl+E` | Stop Arbeits­sitzung |
| `Ctrl+P` | Pause / Resume |
| `Ctrl+M` | Mini-Modus an/aus |

### 🎨 Themes

Zwei integrierte **visuelle Themes**:

1. **Modern** (Standard)
   - Farben: Cyan, Pink, Gelb
   - Clean, helles Interface
   - Modern & hochwertig

2. **Synthwave**
   - Retro-futuristischer Look
   - Dunkle Hintergründe, leuchtende Neon-Farben
   - Besser für lange Arbeitssessions (Augen-freundlich)

**Umschaltbar in** → Einstellungen ⚙️ → Appearance

### ⚙️ Einstellungen & Konfiguration

Im Menü "Einstellungen":

- **Datenbank**: Pfad zur SQLite-DB anpassen
- **Defaults**: Standard-Benutzer & Projekt
- **Dashboard-Port**: Port für Analytics-Dashboard (default 8050)
- **Theme**: Modern / Synthwave
- **Pomodoro-Optionen**: Intervall-Längen
- **Entwickler-Konsole**: Debug-Output (für Entwickler)

### 💾 Daten­speicherung

- **Format**: SQLite (`data/wotiti.db`)
- **Struktur**:
  - `users` Tabelle
  - `projects` Tabelle
  - `events` Tabelle (Arbeitszeiten)
  - `break_events` Tabelle (Pausen)
- **Lokale Kontrolle**: Du bestimmst wo Daten gespeichert werden
- **Backup**: Einfach die `.db`-Datei kopieren

### 📋 Session-Schutz

- **Warnung beim Schließen**: Falls aktive Session läuft → "Wirklich beenden?"
- **Verhindert versehentliche Datenverluste**
- **Noch nicht beendete Sessions** werden bei Neustart wiederhergestellt

---

## 📊 Analyse­komponente (Work Time Insights)

Das interaktive **Analytics-Dashboard** mit detaillierten Auswertungen.

### Zugriff

Verfügbar unter: **`http://localhost:8050`** (im Browser)

?> **Hinweis**: Port änderbar in Timer-Einstellungen. Dashboard läuft im Hintergrund, wenn Timer aktiv ist.

### Tab 1: Grundlagen 📈

Schneller Überblick:

- **Tagessummen**: Heute erfasste Arbeitszeit
- **Wochensummen**: Diese Woche
- **Monatssummen**: Dieser Monat
- **Trend-Pfeile**: ↑ (mehr arbeitet als Durchschnitt) / ↓ (weniger)
- **Top-Projekte**: Welche sind zeitintensiv?
- **Durchschnittliche Session-Länge**: Wie fokussiert arbeitet der Nutzer?

### Tab 2: Projekte & Muster 🔍

Tiefergehende Projekt-Analysen:

- **Projekt-Breakdown**: Kreisdiagramm (Pie Chart) mit Zeitverteilung
- **Projekt-Heatmap**: Wann wird an welchem Projekt gearbeitet?
- **Häufigste Projekt-Kombinationen**: Welche Projekte laufen immer parallel?
- **Sessions pro Projekt**: Anzahl der Arbeits­blöcke per Projekt
- **Detailtabelle**: Alle Projekte mit Summierungs-Optionen

### Tab 3: Zeitreihen & Trends 📉

Längerfristiges Muster-Erkennung:

- **Produktivitäts-Kurven**: Arbeitszeit pro Tag über mehrere Wochen
- **Tages-Muster**: Wann arbeite ich am liebsten? (Morgens? Abends?)
- **Wochenmuster**: Unterscheiden sich Wochenende und Arbeitstage?
- **Fokus-Stabilität**: Werden Arbeits­blöcke länger oder kürzer?
- **Pausen­disziplin**: Wie regelmäßig sind Pausen?

### Tab 4: Erweiterte Analysen 🚀

Statistische & ML-Features:

- **Deskriptive Statistiken**:
  - Mittelwert, Median, Standardabweichung
  - Min/Max Werte
  - Quartile & Boxplots
  
- **Prognosen** (ML):
  - Vorhersage: Wie viel Zeit werde ich nächste Woche arbeiten?
  - Anomalie-Detektion: Ungewöhnliche Muster erkennen
  - Clustering: Ähnliche Arbeitstage gruppieren
  
- **Korrelations­analysen**:
  - Zusammenhang zwischen Pomodoro-Disziplin und Gesamtarbeitszeit?
  - Korrelation Pausenlänge ↔ Fokus-Qualität?

---

## 🌐 UI-Sprache & Lokalisierung

- **Vollständig deutschsprachig**: Timer, Dashboard, Menüs, Fehlermeldungen
- **Lokale Datenformate**: Datumsangaben im Format DD.MM.YYYY
- **Englische Version**: Geplant für zukünftige Versionen (Roadmap)

---

## 🔐 Dataflow & Sicherheit

```
┌─────────────────────┐
│  Work Time Timer    │ ← Startest Zeiterfassung
└──────────┬──────────┘
           │ speichert
           ↓
   ┌───────────────┐
   │  SQLite DB    │ ← Lokal, verschlüsselt optional
   │ (wotiti.db)   │
   └───────┬───────┘
           │
           ↓ liest
   ┌─────────────────────┐
   │ Work Time Insights  │
   │  (Dash Dashboard)   │
   └─────────────────────┘
       (http://localhost:8050)
```

**Sicherheitsaspekte:**
- ✅ Keine externe API-Aufrufe
- ✅ Keine Telemetrie
- ✅ Keine Cloud-Anbindung
- ✅ SQLite Datenbank bleibt lokal
- ✅ HTTPS nicht erforderlich (nur lokal)

---

## 🎬 Typischer Workflow

1. **Morgens**: Timer starten (`Ctrl+S`), Projekt wählen
2. **Nach 25 min (Pomodoro)**: Timer pausiert automatisch → kurze Pause
3. **Nach Pause**: Timer weiterlaufen oder neuer Block starten
4. **Mittags**: Stop (`Ctrl+E`), Lunch-Pause (wird nicht getracked)
5. **Nachmittags**: Neue Session starten
6. **Feierabend**: Stop
7. **Am Wochenende**: Dashboard öffnen, Woche analysieren 📊

---

## 🚀 Performance & Ressourcen

- **RAM-Nutzung**: ~50-100 MB während Runtime
- **CPU**: Minimal (nur bei Timer-Tick)
- **Speicher**: DB-Größe ~0.1 MB pro 1000 Sessions (ca. 1000 Tage Arbeit)
- **DB-Performance**: SQLite ist schnell genug für Single-User-Nutzung

---

## 📋 Vergleich: WoTiTi vs. Alternative

| Feature | WoTiTi | Toggl | Clockify | Timesheet |
|---------|--------|-------|----------|-----------|
| **Lokal** | ✅ | ❌ | ❌ | ✅/❌ |
| **Kostenlos** | ✅ | ⚠️ | ⚠️ | ✅ |
| **Open-Source** | ✅ | ❌ | ❌ | ✅ |
| **Pomodoro** | ✅ | ❌ | ⚠️ | ⚠️ |
| **Desktop-App** | ✅ | ⚠️ | ⚠️ | ✅ |
| **Analyseplots** | ✅ | ⚠️ | ❌ | ❌ |
| **ML/Vorhersagen** | ✅ | ❌ | ❌ | ❌ |

---

## 📚 Weitere Ressourcen

- **[📖 Benutzer-Guide](../guide/user-guide.md)** – Schritt-für-Schritt Anleitung
- **[❓ FAQ](../faq.md)** – Häufig gestellte Fragen
- **[👥 Contributing](../contributing-guide.md)** – Für Entwickler
- **[GitHub Repository](https://github.com/grenzenloseSchublade/wotiti)**

---

Fragen zu einem Feature? → [Öffne ein Issue auf GitHub](https://github.com/grenzenloseSchublade/wotiti/issues)
