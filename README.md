# Rockdrigo's Upland Tools

Free, browser-only tools for [Upland](https://upland.me) players, by Rockdrigo.

| Tool | What it does |
|---|---|
| [Ornament Optimizer](ornament-optimizer/) | Enter a username to get one ornament per season on every structure: what to apply now, which ornaments to move (with one-click links), shortages, extras and storage cleanup. |
| [Cheapskate](cheapskate/) | Ornament prices: UPX sale history, current UPX/USD listings with the showroom and its address, and what a player's ornaments are worth. |

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
cheapskate/           ornament prices page
data/                 price data written by the collector
tools/collect_prices.py   the collector (runs every 12 hours in GitHub Actions)
```

## Price data

A GitHub Actions job (`.github/workflows/collect-prices.yml`) runs `tools/collect_prices.py` every 12 hours. It reads ornament shop sales from Upland's public chain history, snapshots ornament listings in ornament and variety shops, and commits small JSON files to `data/`. Each run also adds a few older days of history until it reaches April 2025. USD sale prices are not public, so USD sales are estimated from USD listings that disappear when the ornament changes owner without a UPX payment.

## Run locally

```
python3 -m http.server 8765
```

Then open http://localhost:8765.

Not affiliated with Upland.
