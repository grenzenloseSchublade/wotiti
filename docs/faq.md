---
description: "WoTiTi FAQ – Häufig gestellte Fragen zu Installation, Nutzung, Datenschutz und Features."
---

# ❓ Häufig gestellte Fragen (FAQ)

---

## 📥 Installation & Setup

### F: Welche Betriebssysteme werden unterstützt?

**A:** Aktuell:
- ✅ **Linux** (x64)
- ✅ **Windows** (x64)

macOS ist nicht offiziell unterstützt, könnte aber theoretisch aus Quellcode gebaut werden. [Issue für macOS](https://github.com/grenzenloseSchublade/wotiti/issues) öffnen!

---

### F: Muss ich Python installieren um WoTiTi zu nutzen?

**A:** **Nein**, wenn Du die **vorgebaute Binärdatei** (.zip) herunterladest. Diese funktioniert "out-of-the-box".

**Ja** nur, wenn Du aus **Quellcode** starten möchtest.

---

### F: Funktioniert WoTiTi ohne Internetverbindung?

**A:** **Ja, absolut!** WoTiTi ist **100% offline**. Keine Cloud-Anbindung, keine API-Aufrufe. Alles läuft lokal auf Deinem Rechner.

Das ist ein Core-Feature!

---

### F: Kann ich WoTiTi auf mehreren Rechnern installieren?

**A:** **Ja**, jeder Rechner kann eine separate Installation haben mit eigenem Datenbank.

**Datensync** zwischen Rechnern ist derzeit nicht unterstützt. Das wäre aber eine gute Nachbar-Idee – [öffne ein Feature-Request](https://github.com/grenzenloseSchublade/wotiti/issues/new).

---

### F: Wie viel Speicherplatz braucht WoTiTi?

**A:**
- **Binärdatei**: ~50-100 MB
- **Datenbank pro 1000 Sessions**: ~0.1 MB (sehr effizient)
- **Gesamtgröße**: typischerweise <200 MB für Jahresbetrieb

---

## 🎯 Nutzung & Features

### F: Kann ich die Arbeitszeit nachträglich ändern?

**A:** Die UI bietet derzeit keine direkte Bearbeitungs-Option.

**Workarounds:**
1. Bearbeite die SQLite-DB direkt (Tech-Nutzer): Öffne `data/wotiti.db` mit [SQLiteBrowser](https://sqlitebrowser.org/)
2. Öffne ein [Feature-Request für UI-Editing](https://github.com/grenzenloseSchublade/wotiti/issues/new)

---

### F: Was ist der Unterschied zwischen "Pause" und "Stop"?

**A:** 
- **PAUSE** (`Ctrl+P`): Kurze Unterbrechung. Die Session läuft noch, Timer pausiert.
- **STOP** (`Ctrl+E`): Session beendet. Daten werden in DB gespeichert.

**Beispiel:**
```
10:00 START
10:05 PAUSE (Kaffee trinken)
10:10 START (weitere Arbeit)
11:00 STOP (Session komplett beendet)
```

Das wird als **1 Session à 50 Minuten** gerechnet (mit 5-min Pausenunterbrechung).

---

### F: Können mehrere Benutzer gleichzeitig arbeiten?

**A:** **Technisch**: Ja, verschiedene Benutzer können verschiedene Sessions erfassen.

**Praktisch**: NUR ein Timer läuft gleichzeitig (sonst Datenbank-Konflikte). Also nicht gleichzeitig zwei Personen an einem Rechner arbeiten.

Für echten **Team-Betrieb** wären separate Installationen besser.

---

### F: Wie sichert man die Daten?

**A:** Einfach: **Kopiere die `.db`-Datei!**

```bash
# Linux
cp data/wotiti.db backup/wotiti_backup_2026-04-03.db

# Windows
copy data\wotiti.db backup\wotiti_backup_2026-04-03.db
```

Empfehlung: **Automatisches Backup** (z.B. via Cron/Task Scheduler) auf externe Festplatte oder Cloud-Storage.

---

### F: Kann ich die Mini-Modus-Position nicht finden?

**A:** Der Mini-Modus ist wahrscheinlich hinter dem Hauptfenster.

**Lösung:**
1. Drücke `Ctrl+M` um Größe zu toggle
2. Verschiebe das Fenster mit der Maus
3. Drücke `Ctrl+M` wieder um zu mini­mieren

Falls komplett verschwunden: WoTiTi neustarten (Fenster wird bei Default-Position erstellt).

---

### F: Warum ist das Dashboard leerer/zeigt alte Daten?

**A:** Typische Gründe:
1. **Browser-Cache**: `F5` (Refresh) oder `Ctrl+Shift+R` (Hard Refresh)
2. **Timer nicht aktiv**: Dashboard läuft nur wenn Timer läuft
3. **Port falsch**: Prüf Einstellungen ob Port 8050 korrekt
4. **Datenbank leer**: Zu wenig Sessions für aussagekräftige Chartgen

**Debugging:**
- Öffne Entwickler-Konsole (Einstellungen → Entwickler-Modus)
- Schau nach Error-Messages
- Öffne [Issue mit Debug-Output](https://github.com/grenzenloseSchublade/wotiti/issues/new)

---

## 🔒 Datenschutz & Sicherheit

### F: Werden meine Daten irgendwo hochgeladen?

**A:** **Nein, absolut nicht!**

WoTiTi:
- ✅ Macht **keine API-Aufrufe**
- ✅ Hatno **Telemetrie**
- ✅ Hat **keine Netzwerk-Zugriffe** (außer zum Laden des Dashboards lokal)
- ✅ Speichert alles **lokal in SQLite**

Du kontrollierst 100% Deine Daten.

---

### F: Ist die SQLite-Datenbank verschlüsselt?

**A:** Die `.db`-Datei ist **nicht standardmäßig verschlüsselt** (SQLite unverschlüsselt).

**Sicherheitsimplikation:** 
- Falls Dein Rechner physisch gestohlen wird, könnte jemand die DB auslesen.
- Für hochsensible Daten: Nutze **Festplatten-Verschlüsselung** (Windows BitLocker, Linux LUKS).

**Feature-Request für DB-Encryption**: [Öffne ein Issue](https://github.com/grenzenloseSchublade/wotiti/issues).

---

### F: Teilt WoTiTi Daten mit GitHub?

**A:** **Nein.** Das GitHub-Repository ist nur für Code/Versionshistorie. 

Deine Zeits-Daten bleiben auf Deinem lokalen Rechner.

---

### F: Was passiert mit meinen Daten wenn WoTiTi nicht mehr gepflegt wird?

**A:** Der Code ist **Open-Source (MIT-Lizenz)**. Selbst wenn das Projekt nicht mehr gepflegt wird:

- ✅ Du kannst den Source-Code forken & selbst weiterpflegen
- ✅ Deine Daten sind IMMER in SQLite (portabel)
- ✅ Du bist nicht vendor-locked-in

Das ist ein großer Vorteil gegenüber Cloud-Tools!

---

## 📊 Analysen & Daten

### F: Warum sind meine Werte im Dashboard so klein?

**A:** Das ist normal wenn Du:
- Erst seit kurzem WoTiTi nutzt (wenige Sessions)
- Wenig Stunden trackst

**Statistiken werden aussagekräftiger** nach:
- 2-4 Wochen tägliche Nutzung
- 50+ Sessions pro Kategorie

---

### F: Kann ich Daten in CSV/Excel exportieren?

**A:** Derzeit **nicht direkt** via UI.

**Workarounds:**
1. **SQLiteBrowser**: Öffne DB → Exportiere einzelne Tabellen als CSV
   
   ```sql
   SELECT * FROM events;
   ```

2. **Python-Script**: Mit `polars` oder `sqlite3` (Du hast Code-Zugriff!)
   
   ```python
   import sqlite3
   import pandas as pd
   df = pd.read_sql("SELECT * FROM events", sqlite3.connect("data/wotiti.db"))
   df.to_csv("export.csv")
   ```

**Feature-Request für native CSV-Export**: [Öffne ein Issue](https://github.com/grenzenloseSchublade/wotiti/issues).

---

### F: Funktioniert die Vorhersage korrekt?

**A:** Die **ML-Prognosen** (Tab 4) basieren auf historischen Daten:
- Sehr akkurat nach **4-8 Wochen** regelmäßiger Daten
- Ungenau bei < 2 Wochen Daten (zu wenig Muster)
- Können durch große Anomalien (Urlaub, Krankheit) verzerrt sein

**Verwende die Vorhersage als Richtlinie**, nicht als Wahrheit!

---

## 🛠️ Technische Fragen

### F: Kann ich WoTiTi modifizieren/erweitern?

**A:** **Ja!** Es ist Open-Source (Python + Tkinter + Dash).

1. Fork das GitHub-Repo
2. Modifiziere `src/` Code
3. Test lokal: `uv run python src/main.py`
4. (Optional) Pull-Request einreichen um Änderungen zu teilen

**Contributor-Guide**: [📖 Contributing](contributing-guide.md)

---

### F: Welche Abhängigkeiten nutzt WoTiTi?

**A:** Hauptabhängigkeiten:
- **tkinter** (Python-Standard, für Timer-UI)
- **polars** (Datenverarbeitung)
- **plotly** (Dashboard-Visualisierung)
- **dash** (Web-Server für Dashboard)
- **scikit-learn** (ML für Vorhersagen)

Vollständige Liste: [pyproject.toml](https://github.com/grenzenloseSchublade/wotiti/blob/main/pyproject.toml)

---

### F: Läuft WoTiTi auf meinem Raspberry Pi?

**A:** **Theoretisch ja**, praktisch **unklar** (noch nicht getestet).

- RPi hat meistens ARM64, aber WoTiTi ist nur für x64
- Ein PyInstaller-Build für ARM wäre nötig

**Wenn Du einen RPi hast**: [Öffne ein Issue](https://github.com/grenzenloseSchublade/wotiti/issues) um Feature-Request zu machen!

---

## 🚀 Roadmap & Zukunft

### F: Wann kommt die englische Version?

**A:** **Geplant**, aber noch nicht im MVP. 

Deutsch kommt zuerst, danach englische Lokalisierung.

Timeline: Abhängig von Community-Feedback und Contributor-Zeit.

---

### F: Gibt es macOS Support?

**A:** **Nicht offiziell**, aber möglich. 

**Darum nicht:**
- Hauptentwickler nutzt Linux/Windows
- Keine macOS-Test-Umgebung

**Wenn Du macOS-Support willst**: [Öffne ein Issue + biete ggf. Help beim Testen](https://github.com/grenzenloseSchublade/wotiti/issues/new)

---

### F: Kommt eine Mobile-App (iOS/Android)?

**A:** **Aktuell nicht geplant** – würde andere Tech-Stack brauchen (Swift/Kotlin statt Python).

**Alternativ**: Remote-Desktop-Zugriff auf Deinen Rechner für Dashboard-Checks?

---

## ❓ Noch Fragen?

1. **Schau die [Features](features/index.md)** – detaillierte Erklärungen
2. **Lies den [Benutzer-Guide](guide/user-guide.md)** – praktische Workflows
3. **Öffne ein [Issue](https://github.com/grenzenloseSchublade/wotiti/issues)** – eigentliche Bugs/Requests
4. **Schau [Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions)** – Community-Fragen

---

**Diese FAQ nicht hilfreich?** Öffne ein [Pull Request um die FAQ zu erweitern](https://github.com/grenzenloseSchublade/wotiti/pulls)! 🤝
