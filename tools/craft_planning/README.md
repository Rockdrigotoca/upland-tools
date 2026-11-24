# Trove crafting and hunting plans (Rockdrigo)

Scripts used to plan the crafting sessions and hunting routes. They were written in a scratch folder: paths such as `s9/data.json` and
`/Users/rock/Downloads/...` are hard-coded, so run them from a scratch folder next to the page template, or edit the paths first.

| File | What it does |
|---|---|
| `plan_queens_session.py` | Plans a craft session in Queens for a list of target troves: cheapest recipe by missing items, shared stock, set-cover of properties, random + local search of the stop order, per-stop merge of crafts. Writes the data the page template embeds. |
| `plan_quailwood_session.py` | Same idea for Quailwood (Bakersfield): build-up of the intermediates for the next troves, your properties first (free), then the others by fee. |
| `page_template_*.html` | The standalone page. Replace `__DATA__` with the planner's JSON. Buttons: copy address, copy recipe name, text size, dark mode. |
| `city_check.py`, `plan_city_session.py` | What can be crafted in any city now (`city_check.py 70 -- 'A,B'`), and a session page for it: `plan_city_session.py <city id> '<City, ST>' 'targets' out.json` (page template `page_template_city.html`). With `COVER_SEED=n` a different stop cover is tried (use it when stops stay unscheduled); a trove crafted earlier in the target list counts as an ingredient for later ones. With `BUILDUP=1` it adds every craft the city can do now toward the targets, the first targets getting their ingredients first. |
| `add_recipe_links.py` | Adds the direct link to each structure's recipe screen (`play.upland.me/nft/structures/<id>/structure/recipe`) for every stop and fallback of a session's data, read from Upland's public property records. Run it on the planner's json before filling the page template. |
| `fill_page.py` | `fill_page.py <data.json> <out.html>`: fills the city page template with the planner's data and a fresh stamp, so the page's ticks (kept in the browser under a key with the stamp) start empty. Always use it instead of replacing `__DATA__` by hand. |
| `next_five.py` | `next_five.py <session data.json> [city id]`: the next five troves after a session, measured against the stock you will hold when it is done (ranked by raw items still short), a combined shopping list for the five, and cards for 15 troves with ingredients, crafts and structures. Adds `next5` to the data; the city page template shows it as a "The next 5" page with sortable collapsible cards. |
| `../build_craft_data.py` | Builds `data/helper/craft-data.json` and `data/helper/craft/<city>.json`, the data Sir Quailbert's craft-and-hunt loop reads (recipe versions with their structures; properties, kinds and fees per city). |
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
