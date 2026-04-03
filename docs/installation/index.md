---
description: "WoTiTi Installationsanleitung – Download, Quellcode-Setup, und Build-Anleitung für Linux und Windows."
---

# 📥 Installation & Quickstart

WoTiTi kann auf **3 verschiedene Wege** installiert werden:

1. **[Vorgebaute Binaerdatei](#vorgebaute-binaerdatei)** – einfachste Methode, empfohlen
2. **[Aus Quellcode](#aus-quellcode)** – für Entwickler & Contributor
3. **[Selbst bauen](#selbst-bauen)** – für Anpassungen und Windows-Build

---

## 💻 Systemanforderungen

| Anforderung | Minimum |
|-------------|---------|
| **OS** | Linux (x64) oder Windows (x64) |
| **RAM** | 512 MB (empfohlen: 2 GB) |
| **Speicher** | ~50 MB für Standalone-Build |
| **Python** | 3.10+ (nur für Quellcode-Variante) |

---

## 📦 Option 1: Vorgebaute Binärdatei (empfohlen) { #vorgebaute-binaerdatei }

Die **einfachste und schnellste** Variante – keine Installation nötig.

### Linux (x64)

1. Lade herunter: [**wotiti_1_1-linux-x64.zip**](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-linux-x64.zip)
2. Entpacke die ZIP-Datei:
   ```bash
   unzip wotiti_1_1-linux-x64.zip
   cd wotiti_1_1-linux-x64/
   ```
3. Führe die Anwendung aus:
   ```bash
   ./wotiti
   ```

?> **Tipp**: Falls die Anwendung nicht startet, stelle sicher, dass die Datei ausführbar ist: `chmod +x wotiti`

### Windows (x64)

1. Lade herunter: [**wotiti_1_1-win-x64.zip**](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-win-x64.zip)
2. Entpacke die ZIP-Datei mit Windows Explorer oder 7-Zip
3. Navigiere in den Ordner und doppelklicke auf `wotiti.exe`
4. Windows Smartscreen Warnung? → Klick auf "Weitere Informationen" → "Trotzdem ausführen"

?> **Hinweis**: Auf manchen Windows-Systemen kann die erste Ausführung länger dauern (Caching).

---

## 🔧 Option 2: Aus Quellcode { #aus-quellcode }

Ideal für **Entwickler** und wenn Du die neueste **Development-Version** testen möchtest.

### Voraussetzungen

- **Git** installiert: [git-scm.com](https://git-scm.com)
- **Python 3.10+** installiert: [python.org](https://www.python.org/downloads)
- Terminal bereits geöffnet

### Installation

```bash
# 1. Repository klonen
git clone https://github.com/grenzenloseSchublade/wotiti.git
cd wotiti

# 2. Umgebung Setup (einmalig)
pip install uv
uv sync

# 3. Anwendung starten
uv run python src/main.py
```

#### Detaillierte Schritte

**Schritt 1: Repository klonen**

```bash
git clone https://github.com/grenzenloseSchublade/wotiti.git
cd wotiti
```

**Schritt 2: Abhängigkeiten installieren**

WoTiTi nutzt **uv** – einen schnellen Python-Package-Manager:

```bash
# uv global installieren (einmalig)
pip install uv

# Projekt-Abhängigkeiten installieren
uv sync
```

Dies erstellt eine isolierte Python-Umgebung im `.venv` Ordner.

**Schritt 3: WoTiTi starten**

```bash
uv run python src/main.py
```

Die **Erfassungs­komponente (Timer)** startet sofort. 🎉

!!! info "Dashboard öffnen"
    Das **Analytics-Dashboard** ist separat erreichbar unter `http://localhost:8050` (Browser).
    Port kann in den Einstellungen der Timer-App geändert werden.

---

## 🏗️ Option 3: Selbst bauen (Build) { #selbst-bauen }

Falls Du eine **custom-angepasste Version** bauen oder für ein anderes OS kompilieren möchtest.

### Voraussetzungen

Zusätzlich zu Option 2:
- **PyInstaller** (wird automatisch installed): `pip install pyinstaller>=6.12.0`

### Linux Build

```bash
cd wotiti
pip install uv
uv sync --group dev

# Build durchführen
./build.sh
```

Ausgabe: `build/wotiti/wotiti` (ausführbare Binärdatei)

### Windows Build

```powershell
# PowerShell als Administrator öffnen!
cd wotiti
pip install uv
uv sync --group dev

# Build durchführen
.\build_windows.ps1
```

Ausgabe: `build\wotiti\wotiti.exe`

?> **Tipp**: Der Build-Prozess dauert 2-5 Minuten, je nach System.

---

## ✅ Verifizierung: Installation erfolgreich?

Nach der Installation solltest Du folgende Punkte prüfen:

- [ ] **Timer-Fenster** öffnet sich beim Start
- [ ] **Buttons** (Start, Pause, Stop) sind klickbar
- [ ] **Tastenkürzel** funktionieren (z.B. `Ctrl+S` für Start)
- [ ] **Benutzer hinzufügbar** über "Benutzer verwalten"
- [ ] **Projekt hinzufügbar** über Dropdown-Combobox
- [ ] **Mini-Modus** schaltbar (`Ctrl+M`)
- [ ] **Dashboard** erreichbar unter `http://localhost:8050` (falls aktiviert)

!!! success "Alles funktioniert?"
    Glückwunsch! 🎉 Deine WoTiTi Installation ist bereit. Siehe [📖 Benutzer-Guide](../guide/user-guide.md) für nächste Schritte.

---

## 🐛 Troubleshooting

### Problem: "Permission denied" (Linux)

**Fehler:**
```bash
./wotiti: Permission denied
```

**Lösung:**
```bash
chmod +x wotiti
./wotiti
```

### Problem: "Windows Defender warnt vor Malware"

Das ist ein **falsches Positiv** bei selbstgebauten .exe-Dateien. Windows erkennt PyInstaller-Binaries manchmal als verdächtig.

**Lösung:**
1. Klick auf "Weitere Informationen"
2. Klick auf "Trotzdem ausführen"
3. Die Warnung kommt nur beim ersten Start

Oder: Lade direkt von [GitHub Releases](https://github.com/grenzenloseSchublade/wotiti/releases) herunter (dort ist das Signaturebuilding stabiler).

### Problem: "Dashboard lädt nicht / Port 8050 nicht erreichbar"

**Fehler:**
```
http://localhost:8050 antwortet nicht
```

**Lösungen:**
1. Port in Timer-App Einstellungen ⚙️ ändern (z.B. zu 8051)
2. Prüfen, ob Port bereits von anderer Anwendung benutzt wird: `lsof -i :8050` (Linux/Mac)
3. Firewall ggf. konfigurieren

### Problem: "Python not found" (beim Quellcode-Start)

**Fehler:**
```bash
python: command not found
```

**Lösung:**
1. Python 3.10+ von [python.org](https://www.python.org/downloads) installieren
2. Nach Installation Windows-Neustart machen
3. Terminal neu öffnen
4. Erneut `uv sync` und `uv run python src/main.py` versuchen

### Problem: Datenbank-Fehler beim Start

**Fehler:**
```
sqlite3.OperationalError: database is locked
```

**Lösung:**
1. Stelle sicher, dass **nicht mehrere WoTiTi-Instanzen** gleichzeitig laufen
2. Delete `data/wotiti.db` (Backup erstellen!) und App neustarten → neue Datenbank wird erstellt
3. Prüf die Dateirechte: `ls -l data/` (Linux)

---

## 📚 Nächste Schritte

- **[✨ Alle Features](../features/index.md)** – Detaillierte Feature-Erklärung
- **[📖 Benutzer-Guide](../guide/user-guide.md)** – Erste Schritte & Workflows
- **[❓ FAQ](../faq.md)** – Häufig gestellte Fragen
- **[GitHub Issues](https://github.com/grenzenloseSchublade/wotiti/issues)** – Bug berichten

---

Noch Fragen? → [Öffne ein Issue auf GitHub](https://github.com/grenzenloseSchublade/wotiti/issues/new)
