# Contributing to WoTiTi

Danke, dass du zu WoTiTi beitragen moechtest.

Diese Datei ist der GitHub-Einstieg fuer Mitwirkung. Die vollstaendige, detaillierte Anleitung findest du in der Doku:

- Voller Guide: https://grenzenloseSchublade.github.io/wotiti/contributing/

## Verhaltensregeln

Bitte lies und befolge den Code of Conduct:

- .github/CODE_OF_CONDUCT.md

## Wie du beitragen kannst

- Bugs melden: https://github.com/grenzenloseSchublade/wotiti/issues
- Ideen diskutieren: https://github.com/grenzenloseSchublade/wotiti/discussions
- Pull Requests einreichen: https://github.com/grenzenloseSchublade/wotiti/pulls

## Kurzablauf fuer Code-Beitraege

1. Repository forken
2. Branch erstellen
3. Aenderungen umsetzen
4. Lint und Tests lokal ausfuehren
5. Pull Request erstellen

Beispiel lokal:

```bash
pip install uv
uv sync --group dev
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pytest
```

## Pull Request Erwartungen

- Kleine, fokussierte Aenderungen
- Nachvollziehbare Commit-Nachrichten
- Kurze Beschreibung von Problem, Loesung und Test

Danke fuer deinen Beitrag.
