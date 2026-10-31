# World structure scan: the plan

Goal: know which structures exist in every Upland city, so Rockdrigo's Troves can say which city has the troves you are missing, and
which troves are tied to one city (for example, whether a trove only exists in Paris).

## What it measures

For each city: how many of each service structure are built (and under construction), in total and per neighbourhood. Only structure
names and counts go into the repository. Addresses (for planning a trip) go to a local file that stays out of the repository.

## Method (tools/collect_world.py)

1. **List the city's properties that carry a service building.** Upland's map returns every property of a bounding box with its
   models. A house is `residential`; anything else is a service structure. One request per neighbourhood, point-in-polygon against
   the neighbourhood boundary. Los Angeles: 6,611 of 475,235 properties (1.4%), so about 70 times fewer reads than scanning everything.
   Saved once per city in `data/structures/world/ids/<city id>.json`.
2. **Read those properties' records** (four workers, about five requests a second, longer waits when Upland pushes back) and count
   buildings by name. Progress is saved after every batch of 200: a stopped run is resumed by the next one. Output:
   `data/structures/world/<city id>.json` (built, building, and the same per neighbourhood).

Never runs next to another Upland script: it joins the collectors' concurrency group on GitHub, and by hand it is run on its own.

## Size and time

- 65 cities, 2,478 neighbourhoods.
- Listing: 2,478 map requests. Los Angeles took about 10 minutes for 131 neighbourhoods, so allow about 2 hours for everything.
- Reading: roughly 1% to 3% of each city's properties, so tens of thousands of reads in all, at five a second: a few hours.
  The real number is known after the listing; each city reports its own count first.
- Refresh: the structure mix changes slowly. Re-list a city about monthly, re-read it when a trove question needs fresh numbers.

## Order

1. Los Angeles (running now, 22 minutes).
2. Paris (city 91), because of the Paris trove question.
3. The cities the troves tell us matter: those with the structures that hold the troves you are missing.
4. Washington D.C. (85), Rome (115, Nomentano is already done), Madrid (117), then the rest by size.

## What it answers

- **Which city has what:** for each of your missing troves, the cities where any structure that holds it exists, and how many.
- **City-specific troves:** a trove whose structures exist in one city (or two) only. Structure names already hint at some of them
  ("Florence Retro Googie Farmers Market", "Takasaki Retro Googie Farmers Market"); the scan turns the hint into a list.
- **Where to go inside a city:** the neighbourhoods with the most of the structures you need.

## Structures like the Florence market (asked for by Rockdrigo, to show once the scan is done)

For every structure: the cities where it exists, so the ones tied to one city or a few stand out. From names alone, before any scan:
Florence, Omaha and Takasaki Retro Googie Farmers Market, Cape Town Modular: Padstal Edition, Seattle Music Venue, Singapore Kopitiam,
The Amsterdam Cheese House, and the regional modular families (East Coast, European, South America, Asian, Main Street). The scan
confirms which are real city-only structures, and which troves each one holds.

## To build after the first cities

- `data/structures/world/cities.json`: names for the 65 city ids (the collections list names only some).
- A "Where in the world" tab on the Troves page, from the world files plus the trove places.
- `tools/analyse_world.py`: the city-specific list, written to `data/troves/city-specific.json`.
- A `world` job in the collectors workflow, off until Rockdrigo says go.
