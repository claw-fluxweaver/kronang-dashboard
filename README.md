# Kronängs IF - Aktivitetskalender

En snygg dashboard för att visa Kronängs IF's kalender med filtrering per lag och aktivitetstyp.

## 🌐 Live Demo

[https://fluxweaver.github.io/kronang-dashboard/](https://fluxweaver.github.io/kronang-dashboard/)

## 📁 Projektstruktur

```
kronang-dashboard/
├── scraper.py              # Python-scraper för kalendern
├── index.html              # Dashboard
├── style.css               # Styling
├── app.js                  # JavaScript-logik
├── requirements.txt        # Python dependencies
├── data/
│   └── calendar.json       # Scrapad data (auto-genererad)
├── .github/
│   └── workflows/
│       └── scrape.yml      # GitHub Actions för auto-uppdatering
└── README.md
```

## 🚀 Installation

### Lokalt

1. Klona repot:
```bash
git clone https://github.com/fluxweaver/kronang-dashboard.git
cd kronang-dashboard
```

2. Installera Python-dependencies:
```bash
pip install -r requirements.txt
```

3. Kör scrapern:
```bash
python scraper.py
```

4. Öppna `index.html` i din webbläsare eller använd en lokal server:
```bash
python -m http.server 8000
```

### GitHub Pages

1. Pusha till GitHub
2. Gå till Settings → Pages
3. Välj "Deploy from a branch" och välj `main`
4. Ditt repo kommer finnas på `https://<username>.github.io/kronang-dashboard/`

## ⚙️ Auto-uppdatering

GitHub Actions kör scrapern dagligen kl 06:00 UTC och commitar uppdaterad data automatiskt.

Manuell körning: Gå till Actions → Scrape Calendar → Run workflow

## 🛠️ Tekniker

- **Python 3.11** + BeautifulSoup för scraping
- **Vanilla HTML/CSS/JS** för dashboard
- **GitHub Actions** för automation
- **GitHub Pages** för hosting

## 📊 Datakällor

- [kronangsif.se](https://www.kronangsif.se) - SportAdmin-kalender

## 📝 Licens

MIT License - se LICENSE för detaljer.

---

Byggd av FluxWeaver 🧙‍♂️
