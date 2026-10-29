# Rockdrigo's Upland Tools

Free, browser-only tools for [Upland](https://upland.me) players, by Rockdrigo.

| Tool | What it does |
|---|---|
| [Ornament Optimizer](ornament-optimizer/) | Enter a username to get one ornament per season on every structure: what to apply now, which ornaments to move (with one-click links), shortages, extras and storage cleanup. |
| [Collection Hoarder](hoarder/) | Collections: overview of active, collected and missing collections by rarity and city; which collection each property should sit in for the most monthly yield, what to change, and collections you're 1–3 properties short of. Earnings (with and without boosts); Freeloader (borrow), Lend and Swaps: never-collected collections the group can finish by lending each other up to 3 properties, with the reward and the cooldown-period bonus shared fairly after the lender's costs and Upland's tax, burner properties, and swaps paired by rarity; Compare: what two players have collected. Buy: the cheapest properties for sale (UPX and USD) to finish what's missing, by rarity. |
| [Receipts](receipts/) | What a player has sold in UPX by week, month, year and all time, by asset type, with best sellers and latest sales (also purchases and shop fees). Read from Upland's public chain history. |
| [Backstage](status/) | Which data jobs are on, when each last delivered data, and how far the long backfills have got. |
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
tools/collect_prices.py   ornament prices collector
receipts/             sales tracker
status/               collector status page
hoarder/              collections tool (freeloader/ redirects here)
tools/collect_collections.py   reads the group's properties and collections
tools/collect_ledger.py       reads sales from the chain history
tools/collect_buy.py          prices the cheapest for-sale properties per collection
tools/commit_data.sh          commits and pushes a collector's data files
```

## Collectors: one queue, one switch

Everything that talks to Upland runs from one workflow, `.github/workflows/collect.yml`, every 12 hours. Upland tolerates about one request per second and drops connections when two things hit it at once, so the jobs run **one after another, never together**, and only the ones that are switched on:

| Job | What it collects | Budget per run |
|---|---|---|
| `prices` | ornament sales, listings and daily price history | about 25 min |
| `buy` | cheapest properties for sale per collection | 90 min |
| `collections` | the group's properties and collections | 90 min |

Switch jobs on or off with a repo variable, no code change:

```
gh variable set COLLECTORS --body "prices,buy,collections"   # jobs that run (no spaces)
gh variable set COLLECTORS --body ""                          # pause everything
gh workflow run Collectors -f only=buy                        # run one job once, right now
```

## Price data

The `prices` job runs `tools/collect_prices.py`. It reads ornament shop sales from Upland's public chain history, snapshots ornament listings in ornament and variety shops, and commits small JSON files to `data/`. Each run also adds a few older days of history until it reaches April 2025. USD sale prices are not public, so USD sales are estimated from USD listings that disappear when the ornament changes owner without a UPX payment.

## Run locally

```
python3 -m http.server 8765
```

Then open http://localhost:8765.

Not affiliated with Upland.
