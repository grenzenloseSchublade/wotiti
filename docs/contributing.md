---
description: "WoTiTi Contributing Guide – So kannst Du zu diesem Open-Source Projekt beitragen."
---

# 👥 Contributing Guide

Vielen Dank, dass Du WoTiTi verbessern möchtest! 🙏

Dieses Dokument erklärt wie Du **Bug-Reports**, **Feature-Requests** oder **Code-Beiträge** einreichen kannst.

---

## 🤝 Code of Conduct

WoTiTi folgt einem einfachen Grundsatz: **Respektvolles, konstruktives Feedback**.

- ✅ Sei höflich und unterstützend
- ✅ Gib aussagekräftiges Feedback
- ✅ Lerne von anderen
- ❌ Keine Beleidigungen oder Diskriminierung

---

## 🐛 Bugs berichten

Falls Du einen **Bug** (Fehler) findest:

### Schritt 1: Suche ob Issue bereits existiert

Bevor Du einen neuen Bug-Report erstellst, prüfe ob das Problem bereits bekannt ist:

- **[Issues](https://github.com/grenzenloseSchublade/wotiti/issues)** durchschauen
- **Such-Funktion** nutzen (z.B. "crash", "database locked")

### Schritt 2: Bug-Report erstellen

Falls nicht vorhanden:

1. Öffne [New Issue](https://github.com/grenzenloseSchublade/wotiti/issues/new)
2. Wähle Template: "🐛 Bug Report"
3. Fülle Felder aus:

```
**Titel:** Kurze Zusammenfassung, z.B. "Timer crashed beim Start"

**Beschreibung:**
Erkläre was Du getan hast und was schiefgelaufen ist.

**Schritte zum Reproduzieren:**
1. WoTiTi starten
2. Benutzer einrichten
3. [START] drücken
4. → Crash

**Erwartetes Verhalten:**
Timer sollte funktionieren

**Aktuelles Verhalten:**
[Fehlermeldung hier einfügen]

**Umgebung:**
- OS: Linux Debian / Windows 11 / etc.
- WoTiTi Version: 1.1.0
- Python Version (falls Quellcode): 3.11
- Browser (Dashboard): Chrome / Firefox / Safari

**Logs/Screenshots:**
[Fehlermeldung hier]
```

### Schritt 3: Warte auf Feedback

Maintainer wird sich melden! ✅

---

## 💡 Feature-Requests

Hast Du eine **Idee** für ein neues Feature?

### Feature Request einreichen

1. Öffne [New Issue](https://github.com/grenzenloseSchublade/wotiti/issues/new)
2. Wähle Template: "✨ Feature Request"
3. Beschreib:

```
**Titel:** Feature-Name, z.B. "CSV-Export für Events"

**Problem:**
Was ist das Problem, das Du lösen möchtest?
Beispiel: "Ich möchte meine Daten in Excel analysieren können"

**Lösung:**
Wie könnte die Lösung aussehen?
Beispiel: "Button in Dashboard → Export sessions als CSV"

**Alternativen:**
Gibt es andere Wege das zu lösen?

**Zusätzlicher Context:**
Screenshots, Mockups, Ideen.
```

### Diskussion vs. Issue

- **[Issues](https://github.com/grenzenloseSchublade/wotiti/issues)**: Concrete Feature/Bug
- **[Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions)**: Offene Fragen, Ideen, Brainstorming

Wenn Du dir unsicher bist → erst in **Discussions** fragen! 💬

---

## 💻 Code-Beiträge

Du möchtest **selbst Code schreiben**? Super! 🚀

### Voraussetzungen

- **Git** Grundlagen
- **Python 3.10+**
- **Terminal/Command Prompt**-Komfort

### Development Setup

```bash
# 1. Repository forken (auf GitHub)
# Dein-Name/wotiti

# 2. Clone deinen Fork
git clone https://github.com/Dein-Name/wotiti.git
cd wotiti

# 3. Setup
pip install uv
uv sync --group dev

# 4. Development Branch erstellen
git checkout -b fix/dein-feature-name
```

### Code-Style Guidelines

WoTiTi nutzt **Ruff** (Python Linter):

```bash
# Linter prüfen
uv run ruff check src/

# Automatisch formatieren
uv run ruff format src/

# Tests laufen
uv run pytest
```

**Code-Style:**
- **Line-Length**: max 120 Zeichen
- **Type Hints**: Wo möglich nutzen
- **Docstrings**: Bei Funktionen/Klassen
- **Test-Coverage**: Neue Features sollten Tests haben

---

### Workflow: Feature entwickeln

```bash
# 1. Feature Branch
git checkout -b feature/sweet-new-feature

# 2. Code schreiben
vim src/app.py

# 3. Test lokal
uv run python src/main.py

# 4. Format + Lint
uv run ruff check src/ --fix
uv run ruff format src/

# 5. Tests laufen
uv run pytest

# 6. Commit
git add src/app.py
git commit -m "feat: Add sweet new feature"

# 7. Push zu deinem Fork
git push origin feature/sweet-new-feature

# 8. GitHub: Pull Request erstellen
```

**Pull Request Template** wird automatisch angezeigt. Füll es aus:

```
**Beschreibung:**
Was macht diese PR?

**Issue:**
Closes #123 (verlinke verwandtes Issue)

**Testing:**
Wie hast Du es getestet?

**Checklist:**
- [ ] Code folgt Style-Guidelines
- [ ] Tests hinzugefügt/aktualisiert
- [ ] README aktualisiert (falls nötig)
```

---

#### Code-Beispiele

##### ✅ Good

```python
def calculate_total_hours(sessions: list[dict]) -> float:
    """Calculate total hours from sessions.
    
    Args:
        sessions: List of session dictionaries with 'duration' key
        
    Returns:
        Total hours as float
    """
    total_seconds = sum(s.get("duration", 0) for s in sessions)
    return total_seconds / 3600
```

##### ❌ Bad

```python
def calc(s):
    return sum([x['d'] for x in s]) / 3600
```

---

### Commits schreiben

Verwende **Conventional Commits**:

```bash
git commit -m "feat: Add user-friendly error messages"
git commit -m "fix: Database lock retry logic"
git commit -m "docs: Update installation guide"
git commit -m "refactor: Simplify timer logic"
git commit -m "test: Add dashboard tests"
```

Nicht:

```bash
git commit -m "fix stuff"  # ❌
git commit -m "asdf"       # ❌
```

---

### Pull Request Checklist

Vor dem Submit prüf:

- [ ] Feature funktioniert lokal: `uv run python src/main.py`
- [ ] Dashboard lädt: `http://localhost:8050`
- [ ] Keine Linting-Fehler: `uv run ruff check src/`
- [ ] Code formatiert: `uv run ruff format src/`
- [ ] Tests bestanden: `uv run pytest`
- [ ] Commit-Messages sind aussagekräftig
- [ ] Keine großen unerwarteten Abhängigkeiten hinzugefügt

---

## 📚 Dokumentation verbessern

Du möchtest **Docs aktualisieren**?

```bash
cd docs/

# Edit Markdown
vim index.md

# (Optional) MkDocs lokal previeuwen
mkdocs serve
# → Browser: http://localhost:8000
```

Dann PR einreichen wie bei Code-Changes.

---

## 🧪 Tests schreiben

WoTiTi benutzt **pytest**:

```python
# tests/test_db_helper.py
import pytest
from src.db_helper import DBHelper

def test_add_user():
    db = DBHelper(":memory:")
    db.add_user("Max")
    assert db.get_user("Max") is not None
```

Laufen:

```bash
uv run pytest tests/
uv run pytest tests/test_db_helper.py::test_add_user  # Einzeltest
uv run pytest --cov=src                               # Mit Coverage
```

Neue Features sollten Tests haben! 🎫

---

## 🎨 Design Changes

Falls Du UI/UX Änderungen vorschlagst:

1. **Mock / Screenshot** erstellen (z.B. Figma, Paint)
2. **Issue erstellen** mit Visual
3. **Diskutieren** bevor viel Code geschrieben wird
4. **Code + PR** nach Feedback

Warum? UI-Changes sind subjektiv. Besser vorher diskutieren! 💬

---

## 🚀 Release Process (für Maintainer)

(Nur für Projekt-Owner relevant)

```bash
# Version aktualisieren
vim pyproject.toml  # version = "1.2.0"

# Build
./build.sh          # Linux
.\build_windows.ps1 # Windows

# Tag erstellen
git tag -a v1.2.0 -m "Release 1.2.0"
git push origin v1.2.0

# GitHub Release erstellen + Binaries uploaden
# (via GitHub Release UI)
```

---

## ❓ Hilf & Support

- **Fragen?** → [Schreib in Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions)
- **Stuck?** → Kommentiere im Issue
- **Idee?** → Diskutier zuerst bevor viel Code geschrieben wird

---

## 🏆 Danksagungen

Jeder Beitrag wird gewertet! – egal ob:
- 🐛 Bug-Reports
- 💡 Feature-Ideen
- 📖 Dokumentation
- 💻 Code
- 🎨 Design

**Vielen Dank für Deine Unterstützung!** 🙏

---

**Bereit zu beitragen?**

1. **[Fork das Repo](https://github.com/grenzenloseSchublade/wotiti/fork)**
2. **[Erstelle einen Branch](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)**
3. **[Stelle einen PR](https://github.com/grenzenloseSchublade/wotiti/pulls)**

Viel Erfolg! 🚀
