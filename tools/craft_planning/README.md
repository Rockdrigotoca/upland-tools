# Trove crafting and hunting plans (Rockdrigo)

Scripts used to plan the crafting sessions and hunting routes. They were written in a scratch folder: paths such as `s9/data.json` and
`/Users/rock/Downloads/...` are hard-coded, so run them from a scratch folder next to the page template, or edit the paths first.

| File | What it does |
|---|---|
| `plan_queens_session.py` | Plans a craft session in Queens for a list of target troves: cheapest recipe by missing items, shared stock, set-cover of properties, random + local search of the stop order, per-stop merge of crafts. Writes the data the page template embeds. |
| `plan_quailwood_session.py` | Same idea for Quailwood (Bakersfield): build-up of the intermediates for the next troves, your properties first (free), then the others by fee. |
| `page_template_*.html` | The standalone page. Replace `__DATA__` with the planner's JSON. Buttons: copy address, copy recipe name, text size, dark mode. |
| `what_is_left.py` | Which locked troves are craftable now, what each lacks. |
| `runs_needed.py` | Hunting runs (100 sends) needed to cover the missing raw items, from the real yield per send. |
| `queens_hunt_route.py` | Queens hunting route (3 files of 40), scored by the visits you really made. |
| `hunt_route.py` | Any city, any need list: `hunt_route.py <city id> <tag> '{"Coal Lump":18,...}' [files]` (Queens 4, Los Angeles 32). History comes from hunts.json. |
| `coffee_hunt_route.py` | Single-trove hunting route for any city (used for Coffee Bean in Queens and Los Angeles). |
| `best_city_for_materials.py` | Compares cities for Amethyst, Sand, Coal Lump and Quartz. |

## Strategy notes (so they are not forgotten)
- Balance HAR -> `tools/clean_har.py`; session JSON -> `tools/hunts.py --places`, `tools/build_crafts.py`. `rounds.json` is appended by hand (property indices of older events are not recoverable).
- A structure offers ONE recipe version of a trove; the page shows the expected recipe and an "Avoid" line for the other versions.
- Crafting at another owner's property costs a send fee; your own properties are free, so they come first.
- Prefer properties with few structures unless 2 or more of them are needed. Avoid Howard Beach (hard to locate). 23810 Hillside Ave is the verified Community Center; the Point Breeze property 81313162700822 never showed one.
- The model overstates finds: your real results are about half of the structure model (Coffee Bean about a tenth). Score properties by your own visit history blended with the model.
- Reach: sure up to 60 m, fading to 0 at 100 m (see the memory note on reach geometry).
- Coffee Bean cannot be crafted. Chocolate Bar needs 3 Cacao Pod = 15 beans. Chisel Set and Holiday Ham have no known Queens source.
- For Amethyst and Quartz the best city is Los Angeles; Sand is best in Queens; Coal Lump is about equal everywhere. An LA test route (40 properties) is the way to validate before committing to LA.
- Later: improve routes from visit history, validate the LA test route, then plan the real crafts of the Quailwood build-up.

- 2026-11-18: Holiday Ham is crafted at Community Center (Pork 5, Honey 5, Hooray 5); Chisel Set at Art Gallery / Art Museum (Iron Ore 2, Twine 1). That makes Emerald and Sunday Dinner craftable with no hunting. Hardware Store version (Flint 2, Horsehair 1) waits for your own store to be finished.
