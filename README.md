# Rockdrigo's Upland Tools

Free, browser-only tools for [Upland](https://upland.me) players, by Rockdrigo.

| Tool | What it does |
|---|---|
| [Ornament Optimizer](ornament-optimizer/) | Enter a username to get one ornament per season on every structure: what to apply now, which ornaments to move (with one-click links), shortages, extras and storage cleanup. |
| Ornament Price Finder *(coming soon)* | UPX sale prices, current UPX/USD asking prices, and which showroom lists each ornament. |

Every tool shares the same settings: English/Spanish, text size, and Cunk mode (on by default).

## How it works

The pages read Upland's public game data directly from the browser. Nothing is sent anywhere else and there is no login. Upland's routes are undocumented and can change without notice, so the optimizer also accepts Upland's CSV exports as a backup.

## Layout

```
index.html            home page listing the tools
ornament-optimizer/   the ornament optimizer
shared/theme.css      shared look, light/dark, text size
shared/site.js        header, settings, footer, translations
shared/upland.js      helpers for Upland's public data
```

## Run locally

```
python3 -m http.server 8765
```

Then open http://localhost:8765.

Not affiliated with Upland.
