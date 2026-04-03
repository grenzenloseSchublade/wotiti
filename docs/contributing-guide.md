---
description: "WoTiTi Contributing Guide – So kannst Du zu diesem Open-Source Projekt beitragen."
---

# Contributing Guide

Dieses Dokument beschreibt, wie Du Bug-Reports, Feature-Requests oder Code-Beiträge einreichen kannst. Es gilt der [Code of Conduct](code-of-conduct.md).

---

## Issues und Feature-Requests

1. Prüfe zunächst, ob das Problem oder die Idee bereits als [Issue](https://github.com/grenzenloseSchublade/wotiti/issues) existiert.
2. Falls nicht: [Neues Issue](https://github.com/grenzenloseSchublade/wotiti/issues/new) erstellen.
3. Für offene Fragen oder Brainstorming: [Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions) nutzen.

**Bug-Reports** sollten enthalten: Schritte zum Reproduzieren, erwartetes vs. tatsächliches Verhalten, Umgebung (OS, Version), Fehlermeldung/Logs.

**Feature-Requests** sollten enthalten: Problembeschreibung, vorgeschlagene Lösung, ggf. Alternativen.

---

## Development Setup

```bash
# 1. Repository forken (GitHub UI)
# 2. Fork klonen
git clone https://github.com/Dein-Name/wotiti.git
cd wotiti

# 3. Abhängigkeiten installieren
pip install uv
uv sync --group dev

# 4. Branch erstellen
git checkout -b feature/beschreibender-name
```

---

## Code-Style

WoTiTi nutzt **Ruff** als Linter und Formatter:

```bash
uv run ruff check src/        # Lint
uv run ruff format src/        # Format
uv run pytest                  # Tests
```

Konventionen:

- Max. 120 Zeichen Zeilenlänge
- Type Hints und Docstrings bei Funktionen/Klassen
- Neue Features sollten Tests haben
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

---

## Pull Request Workflow

```bash
# Code schreiben, lokal testen
uv run python src/main.py
uv run ruff check src/ --fix && uv run ruff format src/
uv run pytest

# Commit und Push
git commit -m "feat: Beschreibende Commit-Message"
git push origin feature/beschreibender-name
```

Anschließend Pull Request auf GitHub erstellen. Vor dem Submit prüfen:

- [ ] Feature funktioniert lokal
- [ ] Keine Linting-Fehler
- [ ] Tests bestanden
- [ ] Commit-Messages sind aussagekräftig

---

## Dokumentation

Markdown-Dateien unter `docs/` bearbeiten. Lokale Vorschau:

```bash
mkdocs serve
# → http://localhost:8000
```

---

## Release Process (Maintainer)

```bash
# Version in pyproject.toml aktualisieren
./build.sh           # Linux
.\build_windows.ps1  # Windows

git tag -a v1.2.0 -m "Release 1.2.0"
git push origin v1.2.0
# GitHub Release erstellen + Binaries hochladen
```
