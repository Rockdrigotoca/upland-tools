#!/usr/bin/env python3
"""Which route stops a player can reach for free by walking from one of their own properties.

  python3 tools/build_own_routes.py            # every player in data/structures/players/

For each player and each city route (data/helper/routes/<city id>.json) this writes data/helper/own/<user>/<city id>.json:
  {"user", "updated", "max": 250, "stops": {stop property id: [own property id, own address, metres]}}
The nearest of the player's own properties within 250 m of each stop. A visit to your own property costs nothing, so the bot (and later the
helper) can offer the stop for free: visit the property, then walk the avatar toward the stop. The reach rules (80 m) are untouched.
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')
MAX = 250
M_LAT = 111320.0


def main():
    routes = {}
    for f in os.listdir(os.path.join(D, 'helper', 'routes')):
        if f.endswith('.json') and f != 'index.json':
            r = json.load(open(os.path.join(D, 'helper', 'routes', f)))
            routes[r['name']] = r
    pdir = os.path.join(D, 'structures', 'players')
    for f in sorted(os.listdir(pdir)):
        if not f.endswith('.json'):
            continue
        user = f[:-5]
        data = json.load(open(os.path.join(pdir, f)))
        by_city = {}
        for r in data['rows']:
            if r[2] in routes:
                by_city.setdefault(r[2], []).append(r)
        out_dir = os.path.join(D, 'helper', 'own', user)
        os.makedirs(out_dir, exist_ok=True)
        for fn in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, fn))
        made = total = 0
        dl = MAX / M_LAT
        for city, own in by_city.items():
            route = routes[city]
            stops = {}
            for s in route['stops']:
                best = None
                for o in own:
                    if abs(o[4] - s[2]) > dl:
                        continue
                    d = math.hypot((o[4] - s[2]) * M_LAT, (o[5] - s[3]) * M_LAT * math.cos(math.radians(s[2])))
                    if d <= MAX and (best is None or d < best[0]):
                        best = (d, o)
                if best:
                    stops[s[0]] = [str(best[1][0]), best[1][1], round(best[0])]
            if stops:
                json.dump({'user': user, 'updated': data.get('updatedAt', ''), 'max': MAX, 'stops': stops}, open(os.path.join(out_dir, str(route['city']) + '.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
                made += 1; total += len(stops)
        print(user, len(data['rows']), 'properties ->', made, 'cities,', total, 'free stops')


if __name__ == '__main__':
    main()
