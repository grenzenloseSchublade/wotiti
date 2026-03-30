# WoTiTi Release Guide

Diese Datei beschreibt den vollständigen Release-Prozess für WoTiTi und erklärt ausführlich, wie du Dateien in GitHub veröffentlichst.

## Ziel dieses Dokuments

- Reproduzierbarer Release-Prozess für neue Versionen
- Saubere Trennung zwischen Quellcode und Binärdateien
- Klare Anleitung für Veröffentlichung per Git, GitHub Web UI und GitHub CLI

## Kurzantwort: Ist „Publish your first package“ relevant?

In diesem Projekt: **nein, in der Regel nicht**.

„Publish your first package“ bezieht sich auf das Veröffentlichen von Bibliotheken/Packages in Registries (z. B. npm, PyPI, GitHub Packages). WoTiTi ist primär eine Anwendung mit Release-Artefakten (ZIP/EXE).

Relevant wird das Thema nur, wenn du bewusst ein eigenes Python-Paket oder npm-Paket aus diesem Repository heraus veröffentlichen willst.

## Release-Strategie für WoTiTi

- Quellcode bleibt im Repository.
- Build-Artefakte (EXE/ZIP) werden nicht eingecheckt.
- Veröffentlichte Binärdateien gehen als Assets an ein GitHub Release.

Damit bleibt das Repo klein, nachvollziehbar und CI-freundlich.

## Voraussetzungen

- Git installiert
- GitHub-Konto mit Schreibrechten auf das Repository
- Für Linux-Build: Linux-System mit Python 3.10+ und uv
- Für Windows-Build: Windows 10/11 mit Python 3.10+ und uv
- Optional: GitHub CLI (`gh`) installiert und eingeloggt (`gh auth login`)

## Schritt 1: Linux-Build erstellen

Auf einem Linux-System im Repository ausführen:

```bash
./build.sh
```

Erwartetes Ergebnis: ein lauffähiger Ordner unter `dist/wotiti`.

Linux-Artefakt zippen:

```bash
cd dist
zip -r wotiti-linux-x64.zip wotiti
```

Optional prüfen:

```bash
ls -lh wotiti-linux-x64.zip
```

## Schritt 2: Windows-Build erstellen

Auf einem Windows-System im Repository ausführen:

```powershell
.\build_windows.ps1
```

Erwartetes Ergebnis: ein lauffähiger Ordner unter `dist\wotiti`.

## Schritt 3: Windows-Artefakt zippen

```powershell
Compress-Archive -Path dist\wotiti -DestinationPath dist\wotiti-win-x64.zip
```

Optional prüfen:

```powershell
Get-Item dist\wotiti-win-x64.zip
```

Hinweis: Für ein gemeinsames Release werden zwei Dateien benötigt:

- `dist/wotiti-linux-x64.zip`
- `dist/wotiti-win-x64.zip`

Wenn beide Builds auf unterschiedlichen Rechnern erstellt werden, eine der ZIP-Dateien auf den Release-Rechner kopieren.

## Schritt 4: Code-Stand committen und Tag setzen

Auf deinem Entwicklungsrechner:

```bash
git status
git add -A
git commit -m "release: v0.x.0"
git push origin main

git tag v0.x.0
git push origin v0.x.0
```

Hinweis: Ersetze `main` und `v0.x.0` durch deinen tatsächlichen Branch/Versionsstand.

## Schritt 5: GitHub Release erstellen (beide Assets direkt downloadbar)

### Variante A: Mit GitHub CLI (empfohlen)

Wenn beide ZIP-Dateien lokal vorliegen:

```bash
gh release create v0.x.0 \
	dist/wotiti-win-x64.zip \
	dist/wotiti-linux-x64.zip \
	--title "WoTiTi v0.x.0" \
	--notes "Direktdownload: Windows- und Linux-Build (--onedir)"
```

Falls das Release bereits existiert, können Assets nachträglich ergänzt werden:

```bash
gh release upload v0.x.0 dist/wotiti-win-x64.zip dist/wotiti-linux-x64.zip --clobber
```

Wenn ZIP-Dateien noch nicht auf dem Rechner liegen, zuerst übertragen (SCP, Cloud, USB), dann obigen Befehl nutzen.

### Variante B: Über GitHub Weboberfläche

1. Repository auf GitHub öffnen.
2. Rechts in der Seitenleiste auf „Releases" klicken.
3. „Draft a new release" wählen.
4. Tag auswählen oder neu anlegen (`v0.x.0`).
5. Release-Titel vergeben (z. B. `WoTiTi v0.x.0`).
6. Changelog/Notizen eintragen.
7. Unter „Attach binaries" beide Dateien hochladen:
	- `wotiti-win-x64.zip`
	- `wotiti-linux-x64.zip`
8. „Publish release" klicken.

## Datei in GitHub veröffentlichen: Welche Wege gibt es?

Je nach Ziel gibt es drei saubere Wege:

### 1) Datei als Quellcode ins Repository (Git)

Nutze das für kleine, versionierbare Dateien (Code, Doku, Konfig):

```bash
git add path/to/file
git commit -m "docs: add file"
git push origin main
```

Ergebnis: Datei ist Teil des Repositories und jeder Commit-Historie.

### 2) Datei direkt in GitHub hochladen (Web UI)

Nutze das für schnelle Einzeldateien ohne lokale Git-CLI:

1. Im Zielordner auf GitHub „Add file" wählen.
2. „Upload files" anklicken.
3. Datei ziehen/auswählen.
4. Commit-Nachricht setzen.
5. Branch wählen und committen.

Ergebnis: Datei landet ebenfalls versioniert im Repository.

### 3) Datei als Release-Asset veröffentlichen

Nutze das für große Binärdateien (ZIP, EXE, Installer):

- Nicht in Git-Historie, sondern an einer Version (Tag) angehängt
- Für Endnutzer ideal, weil direkt downloadbar

## Wann welches Vorgehen?

- Quellcode/Doku: Repository-Commit
- Große Build-Dateien: Release-Asset
- Pakete (PyPI/npm/GitHub Packages): nur dann „Publish package"

## Häufige Fehler und Lösungen

- Fehler: „Tag existiert nicht"
	- Lösung: Tag lokal erstellen und pushen (`git tag ...`, `git push origin ...`).

- Fehler: ZIP ist zu groß fürs Repository
	- Lösung: Nicht committen, als Release-Asset hochladen.

- Fehler: `gh` meldet Auth-Probleme
	- Lösung: `gh auth login` erneut ausführen und Repo-Rechte prüfen.

- Fehler: Windows-Build läuft unter Linux/macOS nicht
	- Lösung: EXE immer auf Windows bauen (plattformabhängig).

- Fehler: Linux-Artefakt fehlt im Release
	- Lösung: Linux-Build mit `./build.sh` erstellen, `wotiti-linux-x64.zip` erzeugen und per `gh release upload` nachreichen.

- Fehler: Falscher Asset-Name im Release
	- Lösung: Einheitliche Namen verwenden (`wotiti-win-x64.zip`, `wotiti-linux-x64.zip`) oder mit `--clobber` überschreiben.

## Empfohlene Release-Checkliste

1. Tests/Lint laufen lokal sauber.
2. Versionsänderungen und Changelog aktualisiert.
3. Linux-Build erstellt und `wotiti-linux-x64.zip` erzeugt.
4. Windows-Build erstellt und `wotiti-win-x64.zip` erzeugt.
5. Beide ZIPs getestet (Start, Datenpfade, Assets).
6. Commit + Tag + Push ausgeführt.
7. GitHub Release inkl. beider Assets veröffentlicht.
8. Kurzer Smoke-Test beider Downloads aus dem Release-Tab.
