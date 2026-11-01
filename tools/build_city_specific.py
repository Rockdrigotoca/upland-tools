#!/usr/bin/env python3
"""The structures that exist in only one scanned city ("special builds"), with the troves each gives, a few properties to visit
and a suggested order for travelling between the cities that have them (shortest path by air distance, starting at --start).

Reads data/troves/world.json, data/troves/places.json and data/troves/places/<city>.json (all already collected: no Upland calls).
Writes data/troves/city-specific.json.
"""
import argparse
import json
import math
import os
import re
import unicodedata

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'troves')
SPOTS = 6
# Confirmed by the player: factories and nurseries give no troves, so they are not worth a visit.
SKIP = re.compile(r'factory|nursery', re.I)


def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def nn(s):
    return re.sub(r' 1$', '', norm(s))


def km(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    x = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def route(points, start):
    """Shortest open path through all points starting at `start` (Held-Karp; there are only a dozen or so cities)."""
    ids = [start] + [c for c in points if c != start]
    n = len(ids)
    d = [[km(points[a], points[b]) for b in ids] for a in ids]
    full = 1 << n
    best = {(1, 0): (0.0, None)}
    for mask in range(1, full):
        if not mask & 1:
            continue
        for last in range(n):
            if (mask, last) not in best:
                continue
            cost = best[(mask, last)][0]
            for nxt in range(1, n):
                if mask & (1 << nxt):
                    continue
                key = (mask | 1 << nxt, nxt)
                c = cost + d[last][nxt]
                if key not in best or c < best[key][0]:
                    best[key] = (c, (mask, last))
    last = min(range(1, n), key=lambda i: best[(full - 1, i)][0])
    total, state, path = best[(full - 1, last)][0], (full - 1, last), []
    while state:
        path.append(ids[state[1]])
        state = best[state][1]
    return path[::-1], total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--start', default='Bermuda', help='city to start the route from')
    args = ap.parse_args()
    world = json.load(open(os.path.join(DATA, 'world.json')))
    cities = {c['id']: c for c in world['cities']}
    holds = {}
    for t in json.load(open(os.path.join(DATA, 'places.json')))['troves']:
        for s in t[2]:
            holds.setdefault(nn(s), []).append(t[0])
    out, coords, files = [], {}, {}
    for e in world['structures'].values():
        if e.get('living') or len(e['c']) != 1 or SKIP.search(e['name']):
            continue
        cid = int(next(iter(e['c'])))
        if cid not in files:
            f = os.path.join(DATA, 'places', f'{cid}.json')
            files[cid] = json.load(open(f)) if os.path.exists(f) else None
        cd = files[cid]
        spots = []
        if cd:
            idx = {i for i, sname in enumerate(cd['structs']) if nn(sname) == nn(e['name'])}
            hits = [p for p in cd['props'] if idx & set(p[5])]
            by_hood = {}
            for p in hits:
                by_hood[p[4]] = by_hood.get(p[4], 0) + 1
            hits.sort(key=lambda p: (-by_hood[p[4]], p[4], p[1]))
            spots = [[p[0], p[1], cd['hoods'][p[4]]] for p in hits[:SPOTS]]
            if cid not in coords and cd['props']:
                coords[cid] = [round(sum(p[2] for p in cd['props']) / len(cd['props']), 4), round(sum(p[3] for p in cd['props']) / len(cd['props']), 4)]
        out.append({'name': e['name'], 'city': cid, 'n': next(iter(e['c'].values())), 'troves': sorted(set(holds.get(nn(e['name']), []))), 'spots': spots})
    out.sort(key=lambda x: (cities[x['city']]['name'], -x['n']))
    used = {x['city'] for x in out if x['city'] in coords}
    # the starting city is part of the route even without a special build (it is where the player goes for other troves)
    start = next((cid for cid, c in cities.items() if c['name'] == args.start), None)
    if start is not None and start not in coords:
        f = os.path.join(DATA, 'places', f'{start}.json')
        if os.path.exists(f):
            cd = json.load(open(f))
            coords[start] = [round(sum(p[2] for p in cd['props']) / len(cd['props']), 4), round(sum(p[3] for p in cd['props']) / len(cd['props']), 4)]
    if start in coords:
        used.add(start)
    else:
        start = min(used)
    order, total = route({c: coords[c] for c in used}, start)
    res = {'updatedAt': world.get('updatedAt'), 'cities': {str(c): {'name': cities[c]['name'], 'pos': coords[c]} for c in used},
           'route': order, 'routeKm': round(total), 'structures': out}
    with open(os.path.join(DATA, 'city-specific.json'), 'w') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
    print(len(out), 'structures in', len(used), 'cities; route', ' > '.join(cities[c]['name'] for c in order), f'({total:,.0f} km)')


if __name__ == '__main__':
    main()
