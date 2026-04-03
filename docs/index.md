---
description: "WoTiTi – Lokale Zeiterfassung mit Pomodoro und Analysen. Kostenlos, Open-Source, 100% datenschutzfreundlich. Desktop-App für fokussiertes Arbeiten."
keywords: ["Zeiterfassung", "Pomodoro Timer", "Arbeitszeit Tracker", "Open-Source", "lokal", "Python"]
---

# WoTiTi
## Lokale Zeiterfassung mit Pomodoro und Analysen

> **Fokussiertes Arbeiten, ohne Cloud. Kostenlos. Open-Source.**

WoTiTi ist eine **lokal ausführbare Desktop-Anwendung** zur intelligenten Erfassung von Arbeitszeiten und detaillierten Arbeitszeitanalysen. Perfekt für:

- ✅ **Fokussiertes Arbeiten** mit integrierter Pomodoro-Methode
- ✅ **Datenschutz** – alles lokal, keine Cloud-Abhängigkeit
- ✅ **Detaillierte Analysen** – interaktive Dashboards & Statistiken
- ✅ **Kosten­frei & quelloffen** – MIT-Lizenz, GitHub-Hosting

---

## Das Problem

Kommerzielle Zeiterfassungs-Tools sind:
- **Cloud-abhängig** → Datenschutz-Unsicherheit
- **Kompliziert** → zu viele Klicks für einfaches Tracking
- **Kostenpflichtig** → Lizenzen pro Nutzer
- **Lockout** → Bindung an propriet­äre Systeme

---

## Die Lösung: WoTiTi

| Merkmal | Beschreibung |
|---------|------------|
| **Schnelles Tracking** | Start, Pause, Stop – in 2 Sekunden |
| **Pomodoro-Built-in** | Fokussierte Arbeitsintervalle, automatische Pausenverwaltung |
| **Intelligente Analysen** | 4 Analyse-Tabs: Übersicht, Projekte, Trends, Deep-Dive |
| **Vollständig Lokal** | SQLite-Datenbasis, keine Internetverbindung nötig |
| **Themes** | Modern (Cyan/Pink) und Synthwave – deutschsprachige UI |
| **Plattform-übergreifend** | Linux und Windows, native Builds verfügbar |

---

## Kernfunktionen

- **Zeiterfassung**: Start, Pause, Stop mit Benutzer- und Projektzuordnung
- **Pomodoro**: Konfigurierbare Arbeits- und Pausenintervalle (Standard: 25/5 min)
- **Mini-Modus**: Kompakte Always-on-Top-Ansicht (`Ctrl+M`)
- **Analytics-Dashboard**: 4 Tabs – Übersicht, Projektmuster, Zeitreihen, ML-Analysen
- **Themes**: Modern und Synthwave
- **Tastenkürzel**: `Ctrl+S` (Start), `Ctrl+E` (Stop), `Ctrl+P` (Pause), `Ctrl+M` (Mini)

Siehe [Dokumentation](guide/dokumentation.md) für die vollständige Funktionsreferenz.

---

## Schnellstart

### Option 1: Download (einfachste Variante)

Lade die neueste **vorgebaute Version** herunter:
- **Linux x64**: [wotiti_1_1-linux-x64.zip](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-linux-x64.zip)
- **Windows x64**: [wotiti_1_1-win-x64.zip](https://github.com/grenzenloseSchublade/wotiti/releases/download/v1.1.0/wotiti_1_1-win-x64.zip)

Entpacken → Ausführen. Fertig.

### Option 2: Aus Quellcode

```bash
# Repository klonen
git clone https://github.com/grenzenloseSchublade/wotiti.git
cd wotiti

# Abhängigkeiten installieren
pip install uv
uv sync

# Anwendung starten
uv run python src/main.py
```

### Option 3: Selbst bauen

```bash
# Linux
./build.sh

# Windows
.\build_windows.ps1
```

**Mehr Details?** Siehe [Installations-Guide](installation/index.md)

---

## Erste Schritte

1. **Benutzer + Projekt anlegen** (einmalig)
2. **Timer starten** (`Ctrl+S`) → Arbeit beginnen
3. **Dashboard öffnen** → `http://localhost:8050` → Analysen anschauen

Siehe [Dokumentation](guide/dokumentation.md) für detaillierte Arbeitsabläufe.

---

## Vergleich mit Alternativen

| Feature | WoTiTi | Toggl | Clockify | Timesheet |
|---------|--------|-------|----------|-----------|
| **Lokal** | ✅ | ❌ | ❌ | ✅/❌ |
| **Kostenlos** | ✅ | ⚠️ | ⚠️ | ✅ |
| **Open-Source** | ✅ | ❌ | ❌ | ✅ |
| **Pomodoro** | ✅ | ❌ | ⚠️ | ⚠️ |
| **Desktop-App** | ✅ | ⚠️ | ⚠️ | ✅ |
| **Analyseplots** | ✅ | ⚠️ | ❌ | ❌ |
| **ML-Vorhersagen** | ✅ | ❌ | ❌ | ❌ |

---

## Datenschutz und Sicherheit

- ✅ **100% Offline** – Keine Cloud-Anbindung
- ✅ **Keine Telemetrie** – Keine Nachverfolgung Ihrer Daten
- ✅ **Quelloffen (MIT)** – Vollständige Transparenz, Peer-Review möglich
- ✅ **Lokale SQLite** – Sie kontrollieren, wo Ihre Daten gespeichert werden

---

## Systemanforderungen

- **OS**: Linux oder Windows
- **Speicher**: ~50 MB (für Standalone-Build)
- **Python** (bei Quellcode-Ausführung): ≥ 3.10

---

## Contributing

WoTiTi ist Open-Source und freut sich über Beiträge!

- **Feature-Ideen?** Öffne ein [GitHub Issue](https://github.com/grenzenloseSchublade/wotiti/issues)
- **Bug gefunden?** [Report hier](https://github.com/grenzenloseSchublade/wotiti/issues/new?template=bug_report.md)
- **Code-Beitrag?** [Fork & Pull Request](contributing-guide.md)

Siehe [Contributing Guide](contributing-guide.md) für Details.

---

## Lizenz

WoTiTi ist unter der **MIT-Lizenz** lizenziert. Siehe [LICENSE](https://github.com/grenzenloseSchublade/wotiti/blob/main/LICENSE) für Details.

---

## Links

- **GitHub Repository**: [grenzenloseSchublade/wotiti](https://github.com/grenzenloseSchublade/wotiti)
- **Releases & Downloads**: [GitHub Releases](https://github.com/grenzenloseSchublade/wotiti/releases)
- **Issues & Diskussionen**: [GitHub Discussions](https://github.com/grenzenloseSchublade/wotiti/discussions)

---

<div style="margin-top: 3rem; padding: 2rem; background: linear-gradient(135deg, #00BCD4 0%, #E91E63 100%); color: white; border-radius: 8px; text-align: center;">
  <h3>Bereit loszulegen?</h3>
  <p>WoTiTi ist kostenlos und kann sofort heruntergeladen werden.</p>
  <a href="https://github.com/grenzenloseSchublade/wotiti/releases" style="
    display: inline-block;
    background: white;
    color: #00BCD4;
    padding: 12px 24px;
    border-radius: 4px;
    text-decoration: none;
    font-weight: bold;
    margin-top: 1rem;
  ">Jetzt herunterladen</a>
</div>

---

**Fragen?** Siehe [Dokumentation](guide/dokumentation.md) oder öffne ein [Issue auf GitHub](https://github.com/grenzenloseSchublade/wotiti/issues).

---

<!-- JSON-LD Structured Data for SEO -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "WoTiTi – Work Time Tracker & Insights",
  "description": "Lokale Open-Source Zeiterfassung mit Pomodoro-Funktion und Analyse-Dashboard für fokussiertes Arbeiten. Kostenlos, Desktop-App für Linux und Windows.",
  "url": "https://grenzenloseSchublade.github.io/wotiti/",
  "applicationCategory": "BusinessApplication",
  "applicationSubCategory": "Time Tracking",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "EUR"
  },
  "operatingSystem": ["Linux", "Windows"],
  "downloadUrl": "https://github.com/grenzenloseSchublade/wotiti/releases",
  "license": "https://opensource.org/licenses/MIT",
  "runtimePlatform": "Python 3.10+",
  "keywords": ["Zeiterfassung", "Pomodoro", "Time Tracking", "Desktop App", "Open Source", "Produktivität"],
  "author": {
    "@type": "Organization",
    "name": "WoTiTi Contributors",
    "url": "https://github.com/grenzenloseSchublade/wotiti"
  }
}
</script>
