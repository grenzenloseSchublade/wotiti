---
description: "WoTiTi Benutzer-Guide – Erste Schritte, Workflows, Best Practices für Zeiterfassung und Produktivität."
---

# 📖 Benutzer-Guide

Praktische Anleitung für **Einsteiger & erfahrene Nutzer**.

---

## 🚀 Erste Schritte (5 Minuten)

### Schritt 1: Benutzer & Projekt erstellen

Nach dem **ersten Start**:

1. Klicke auf **"Benutzer verwalten"** (Fenster öffnet sich)
2. Gib Deinen Namen ein, z.B. `Max Mustermann`
3. Klick auf **"Hinzufügen"**
4. Schließe Fenster → Dein Name ist jetzt im Dropdown sichtbar

**Projekt erstellen:**

1. Klick auf das **Projekt-Dropdown** (leeres Feld)
2. Gib einen Projektnamen ein, z.B. `Webseite redesign`
3. Enter drücken → Projekt wird erstellt & gespeichert

### Schritt 2: Erste Zeiterfassung

1. **[🟢 START]** klicken → Timer beginnt zu laufen
2. Arbeite 25 Minuten (Pomodoro-Standard)
3. **[🟡 PAUSE]** klicken → kurze Pause
4. Nach 5 min: **[🟢 START]** erneut klicken → weiterarbeiten
5. **[🔴 STOP]** klicken wenn fertig → Session wird gespeichert ✅

**Gratuliere!** 🎉 Deine erste Session wurde aufgezeichnet.

### Schritt 3: Dashboard öffnen

1. Öffne Browser: **`http://localhost:8050`**
2. Wähle einen **Tab** (Grundlagen, Projekte, Trends, erweitert)
3. Sieh Deine Daten visualisiert! 📊

---

## 💼 Typische Workflows

### Workflow 1: Fokussiertes Arbeiten (Pomodoro)

**Szenario:** Du hast einen **anspruchsvollen Programmier­task**.

**Ablauf:**

```
08:00 → Benutzer: Max, Projekt: Code Refactoring
        [🟢 START]
        ↓
        25 min tiefe Konzentration
        ↓
08:25 → [🟡 PAUSE] (Auto-Vorschlag nach Pomodoro-Zeit)
        ↓
        5 min Kaffee trinken
        ↓
08:30 → [🟢 START] (neuer Block)
        ↓
        25 min weitere Arbeit
        ↓
08:55 → [🔴 STOP] wenn fertig
```

**Dashboard später:** "Refactoring" nahm 50 Min in 2 Sessions auf.

---

### Workflow 2: Meeting + Dokumentation (Mehrere Projekte)

**Szenario:** Gemischter Arbeitstag mit verschiedenen Aktivitäten.

**Ablauf:**

```
09:00 → Projekt: "Team-Meeting"
        [🟢 START]
09:45 → [🔴 STOP]         ✓ Meeting: 45 min

10:00 → Projekt: "Dokumentation"
        [🟢 START]
12:00 → [🔴 STOP]         ✓ Doku: 120 min

12:00 → LUNCH (wird NICHT getracked)

13:30 → Projekt: "Bug-Fixes"
        [🟢 START]
15:00 → [🔴 STOP]         ✓ Bugs: 90 min
```

**Dashboard später:** 
- Team-Meeting: 45 min
- Dokumentation: 120 min
- Bug-Fixes: 90 min
- Gesamtarbeitszeit: 255 min (4h 15min)

---

### Workflow 3: Pausen-Management

**Szenario:** Du möchtest ausgeglichene Pausen­disziplin.

**Best Practice:**

- Nutze den **Mini-Modus** (`Ctrl+M`) → nimmt wenig Platz
- Nach 25 min Arbeit: **PAUSE drücken** (`Ctrl+P`)
- Nach 4 Sessions: **15 min lange Pause** nutzen (konfigurierbar)

**Das System erfasst:**
- Arbeitsblöcke separat
- Pausenlängen separat (in `break_events`)
- Im Dashboard siehst Du: Fokus + Pausen-Disziplin

---

## ⌨️ Tastenkürzel im Überblick

Nutze diese **Shortcuts** für schnelle Bedienung ohne Maus:

| Shortcut | Funktion | Nutzen |
|----------|----------|--------|
| `Ctrl+S` | Start Timer | Arbeit beginnt schnell |
| `Ctrl+E` | Stop Timer | Session beendet |
| `Ctrl+P` | Pause / Resume | Pausen einlegen, weitermachen |
| `Ctrl+M` | Mini-Modus | Fenster klein/groß Toggle |

**Tipp:** Diese Shortcuts funktionieren auch wenn das Timer-Fenster im Hintergrund ist!

---

## 🎨 Einstellungen konfigurieren

### Zugriff

**Menü** → **Einstellungen ⚙️**

### Wichtigste Optionen

#### 🍅 Pomodoro-Optionen

- **Arbeits­block-Länge**: Standard 25 min (z.B. auf 30 min setzen für längere Arbeit)
- **Kurz-Pause-Länge**: Standard 5 min
- **Session bis lange Pause**: Standard 4 Sessions
- **Lang-Pause-Länge**: Standard 15 min

**Beispiel-Konfiguration für `Deep Work`:**
- Arbeits­block: **50 min**
- Kurz-Pause: **10 min**
- Lange Pause nach **2 Sessions**: **20 min**

#### 🎨 Theme

- **Modern**: Hell, produktiv, modern aussehend
- **Synthwave**: Dunkel, augen­freundlich, retro-futuristisch

**Empfehlung:** Synthwave für lange Arbeitstage (weniger Augen­belastung).

#### 🌐 Dashboard-Port

Falls Port 8050 bereits verwendet wird:
- Änder zu **8051**, 8052, etc.
- Browser danach zu `http://localhost:8051` öffnen

#### 📁 Datenbank-Pfad

- Standard: `data/wotiti.db`
- **Backup-Tipp**: Regelmäßig die `.db`-Datei kopieren!

---

## 📊 Dashboard Tipps

### Tab 1: Grundlagen – Schnelle Übersicht

- **"Heute"** vs. **"Durchschnitt"**: Arbeite ich mehr oder weniger?
- **Trend-Pfeile**: Produktivität steigendig?
- **Top-Projekte**: Was nimmt die meiste Zeit?

**Aktion:** Setze Dir **Tages-Ziele**, z.B. "8 Stunden arbeiten" und prüfe jeden Abend.

### Tab 2: Projekte & Muster – Ressourcen-Verteilung

- **Pie Chart**: Wie ist Zeit auf Projekte verteilt?
- **Heatmap**: Wann arbeite ich an welchem Projekt?
- **Sessions-Anzahl**: Ein Projekt mit vielen kurzen Sessions = fragmentierte Arbeit

**Aktion:** Erkenne Ablenkungsmuster. Zu viele Projekt-Wechsel?

### Tab 3: Zeitreihen – Langzeittrends

- **Produktivitäts­kurve**: Steigt/fällt die Arbeitszeit? (Indiz für Engagement)
- **Tages-Muster**: Peak-Zeiten erkennen (z.B. 10-12 Uhr am produktivsten?)
- **Wochen­unterschiede**: Arbeitswochen vs. Ferien?

**Aktion:** Plane anspruchsvolle Tasks in Deine Peak-Zeiten.

### Tab 4: Erweiterte Analysen – Statistik & Prognose

- **Vorhersage**: "Arbeite ich nächste Woche gleich viel wie diese Woche?"
- **Anomalien**: Ungewöhnliche Arbeitstage erkennen
- **Korrelationen**: Hängt Pausenlänge mit Fokus zusammen?

**Aktion:** Nutze Prognosen um realistische Workload-Planung zu treffen.

---

## 🔍 Häufige Fragen im Workflow

### "Ich habe vergessen STOP zu drücken, die Session läuft noch!"

→ Keine Panik! Drücke einfach **STOP**, die Session wird mit der tatsächlichen Zeit gespeichert.

Danach kannst Du optional die Zeit im Dashboard anpassen (wenn nötig).

### "Kann ich alte Sessions bearbeiten?"

→ Die App speichert Zeiten automatisch. Manuelle Bearbeitung ist geplant (Feature-Request).

Workaround: Direkt Datenbank editieren (Fortgeschrittene) oder Issue auf GitHub öffnen.

### "Ich nutze Mini-Modus, aber sehe den Timer nicht mehr!"

→ Mini-Fenster ist möglicherweise hinter anderen Fenstern. Nutze `Ctrl+M` um es größer zu machen, dann wieder klein (`Ctrl+M`).

Oder: Click auf Timer-Icon im Taskbar/Dock um Fenster zu fokussieren.

### "Dashboard zeigt alte Daten, obwohl ich neue Session erfasst habe"

→ Dashboard cacht Daten. **Browser-Refresh** (`F5` oder `Ctrl+R`).

Falls Dashboard komplett nicht lädt: 
- Prüf ob Timer noch läuft
- Prüf ob Port 8050 frei ist (Einstellungen)

---

## 💡 Best Practices

### ✅ Gute Gewohnheiten

1. **Täglich Session starten** – Consistency ist wichtig für Datenqualität
2. **Pausen eintragen** – Ermöglicht echte Produktivitäts-Analysen
3. **Projekt konsistent benennen** – "Projekt A" != "Project A", sonst fragmentiert
4. **Wöchentliche Review** – Jeden Freitag Dashboard anschauen
5. **Backup regelmäßig** – `data/wotiti.db` kopieren

### ❌ Zu vermeiden

1. **Mehrere Timer gleichzeitig** – DB-Konflikte, Datenverlust
2. **Extreme Projektnamen** – Zu lang oder Sonderzeichen vermeiden
3. **Dashboard ignorieren** – Features sind wertlos wenn nicht genutzt
4. **Port-Konflikte** – Andere Apps auf Port 8050 können Probleme verursachen

---

## 🆘 Support & Hilfe

- **Bugs?** → [Öffne ein Issue auf GitHub](https://github.com/grenzenloseSchublade/wotiti/issues)
- **Feature-Wunsch?** → [GitHub Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions)
- **Crash oder Fehler?** → Aktivier Developer­-Konsole in Einstellungen, Post Output in Issue
- **Frage?** → [❓ FAQ](../faq.md)

---

## 🎓 Erweiterte Topics

### Datenexport

- **Raw-Zugriff**: Öffne `data/wotiti.db` mit SQLite Browser (z.B. [SQLiteBrowser](https://sqlitebrowser.org/))
- **CSV-Export**: Geplant für zukünftige Versionen (🎫 GitHub Issues)

### Custom Datenbank-Speicherort

Möchtest Du Daten z.B. auf **externe Festplatte** speichern?

1. Einstellungen → Datenbank-Pfad
2. Gib neuen Pfad ein: z.B. `/media/usb-stick/wotiti.db`
3. Neustart → neue DB wird dort erstellt

### Mehrere Instanzen (für verschiedene Teams)

- **Instanz 1**: Port 8050, DB `data/wotiti.db`
- **Instanz 2**: Port 8051, DB `data2/wotiti.db`

Einfach zwei separate Ordner mit separaten Configs.

---

## 📚 Weitere Ressourcen

- **[✨ Features](../features/index.md)** – Detaillierte Feature-Erklärungen
- **[❓ FAQ](../faq.md)** – Häufig gestellte Fragen
- **[📥 Installation](../installation/index.md)** – Problem beim Start?
- **[GitHub Repository](https://github.com/grenzenloseSchublade/wotiti)**

---

**Noch Fragen?** Schreib ein [📧 Issue](https://github.com/grenzenloseSchublade/wotiti/issues/new) oder stöbere in [Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions).
