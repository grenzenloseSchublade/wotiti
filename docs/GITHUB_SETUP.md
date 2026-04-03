# GitHub Repository Optimierung - SEO & Sichtbarkeit

## 📋 Manuelle GitHub Repo-Einstellungen

Die folgende Konfiguration sollte manuell in der GitHub Web-UI eingegeben werden:

### 1. Repository Description (About)

**Ort**: GitHub Repo Seite → "About" (Zahnrad-Icon rechts oben)

**Kurze Beschreibung (ca. 125 Zeichen):**
```
📊 Lokale Zeiterfassung mit Pomodoro & Analysen – kostenlos, Open-Source, datenschutzfreundlich
```

**Website**: 
```
https://grenzenloseSchublade.github.io/wotiti/
```

**Haken setzen:**
- ✅ "Include in the home page" (falls gewünscht)
- ✅ "Discussions" aktivieren (Community-Support)

### 2. Topics (Tags)

**Ort**: GitHub Repo Seite → "About" (Zahnrad-Icon rechts oben) → "Topics"

**Füge folgende Topics hinzu** (bis max 5):
```
1. time-tracking
2. pomodoro
3. productivity
4. open-source
5. python
```

**Zukünftig (nach English-Rollout):**
```
time-tracker (en)
```

### 3. Repository Visibility & Settings

**Ort**: Settings → General

- ✅ Public (für SEO & Auffindbarkeit)
- ✅ "Issue templates" (für Bug-Reports)
- ✅ "Discussions" Tab sichtbar
- ✅ "Wiki" deaktivieren (nicht nötig, haben Docs)

### 4. Branches & Deploy

**Ort**: Settings → Pages

**Source:**
- Quelle: Deploy from a branch
- Branch: `gh-pages`
- Folder: `/ (root)`

**Enforce HTTPS**: ✅ Aktivieren (für SEO)

### 5. Zusätzliche Sichtbarkeit (Optional)

- **GitHub Stars**: Badge einbinden (auffallend)
- **Code-Owner Datei**: `.github/CODEOWNERS` (Contributor-Transparenz)
- **Security Policy**: `.github/SECURITY.md` (Vertrauen)

---

## 🤖 Automatisierte CLI-Befehle (optional)

Falls Du `gh` CLI nutzen möchtest:

### GitHub Repo-Beschreibung aktualisieren

```bash
gh repo edit grenzenloseSchublade/wotiti \
  --description "📊 Lokale Zeiterfassung mit Pomodoro & Analysen – kostenlos, Open-Source, datenschutzfreundlich" \
  --homepage "https://grenzenloseSchublade.github.io/wotiti/"
```

### Topics hinzufügen

```bash
gh repo edit grenzenloseSchublade/wotiti \
  --add-topic time-tracking \
  --add-topic pomodoro \
  --add-topic productivity \
  --add-topic open-source \
  --add-topic python
```

### Diskussionen aktivieren

```bash
gh repo edit grenzenloseSchublade/wotiti \
  --enable-discussions
```

---

## ✅ Checkliste zum Abhaken

Nach der Konfiguration prüfe:

- [ ] Repository Description zeigt den korrekten Text
- [ ] Website-Link in "About" sichtbar & funktioniert
- [ ] 5 Topics sichtbar auf der Repo-Seite
- [ ] Discussions Tab aktiviert
- [ ] GitHub Pages erfolgt (Settings → Pages)
- [ ] Website erreichbar unter `https://grenzenloseSchublade.github.io/wotiti/`
- [ ] Robots.txt vorhanden (`https://grenzenloseSchublade.github.io/wotiti/robots.txt`)
- [ ] Sitemap vorhanden (`https://grenzenloseSchublade.github.io/wotiti/sitemap.xml`)

---

## 🔍 SEO-Validierung nach Setup

### Google Search Console (optional später)

1. Öffne: https://search.google.com/search-console
2. Füge Property hinzu: `https://grenzenloseSchublade.github.io/wotiti/`
3. Verifiziere via DNS/Meta-Tag
4. Sitemap einreichen: `/sitemap.xml`

### Lighthouse Score prüfen

1. Browser: Chrome DevTools → Lighthouse
2. Audite die Website
3. Ziel: Score > 90 in "SEO" und "Performance"

### Schema Validator

1. Öffne: https://validator.schema.org/
2. Paste Website-URL
3. Prüfe ob SoftwareApplication Schema grün wird

---

## 📊 Langfristige SEO Monitoring

Nach Setup regelmäßig prüfen:

- **GitHub Stars**: Monatlich (Indikator für Popularität)
- **Search Console**: Monatlich (Impressions, Clicks, CTR)
- **Website Analytics** (optional): Google Analytics 4 oder Fathom
- **Backlinks**: Mit Moz oder Ahrefs (3-6 monatlich)
- **Awesome Lists**: Prüfe ob WoTiTi aufgenommen wurde

---

## 🎯 Nächste Phasen (nicht MVP)

Nach diesem Setup können folgende Aktivitäten stattfinden:

### Phase 2: Content & Community
- Awesome Lists Registration
- Reddit/Dev.to Erwähnungen
- GitHub Discussions moderieren
- Blog/News auf Website

### Phase 3: Englische Expansion
- I18n Setup
- Site-Duplikation en/de
- English README + Docs
- Topics auf Englisch erweitern

---

## 📝 Kontakt & Support

Fragen? → [Öffne ein Issue](https://github.com/grenzenloseSchublade/wotiti/issues)
