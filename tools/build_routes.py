#!/usr/bin/env python3
"""Small per-city stop lists for the Discord trove helper (Sir Quailbert's /go) and any other light reader.

For each city in data/troves/places/ this writes data/helper/routes/<city id>.json:
  {"city", "name", "updated", "troves": [names], "rare": [indexes into troves],
   "kinds": [[trove indexes that one kind of structure gives]], "kindNames": [the structure each kind is, as it is written],
   "stops": [[property id, address, lat, lng, stand fee or null, stand property id, near, [trove indexes], [kind indexes of every structure within 80 m]]]}
and data/helper/routes/index.json: [[city id, name, stops]].

A stop is a property with structures on it. "Stand property" is where to stand: the cheaper neighbour within 80 m when
data/troves/reach-best.json knows one, else the property itself. "near" counts the other stops within 80 m. The list keeps
the stops with the most structures in reach, the most troves and the lowest fees, so a reader can rank by need and by value
(finds per visit are one per structure in reach, each picked from that structure's list) without loading a whole city.

  python3 tools/build_routes.py            # all cities
  python3 tools/build_routes.py 32 141     # some cities
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')
OUT = os.path.join(D, 'helper', 'routes')
POOL = 300        # kept by most structures in reach, by most troves, and by lowest fee
M_LAT = 111320.0


def norm(s):
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip())


def main():
    os.makedirs(OUT, exist_ok=True)
    places = json.load(open(os.path.join(D, 'troves/places.json')))
    fees = json.load(open(os.path.join(D, 'troves/fees.json')))['fees']
    best = json.load(open(os.path.join(D, 'troves/reach-best.json')))['best80']
    hunts = json.load(open(os.path.join(D, 'troves/rockdrigo/hunts.json')))
    seen = {}
    for f in hunts['finds']:
        if hunts['src'][f[2]][1] != 'balloon':
            seen[hunts['troves'][f[3]]] = seen.get(hunts['troves'][f[3]], 0) + 1
    findable = [r for r in places['troves'] if r[2]]            # a trove with at least one structure that gives it
    names = [r[0] for r in findable]
    tidx = {n: i for i, n in enumerate(names)}
    rare = [i for i, r in enumerate(findable) if len(r[2]) <= 4 or seen.get(r[0], 0) <= 3]
    kind, kname = {}, {}                                         # structure name -> trove indexes, and as it is written
    kind_ix, kinds = {}, []                                      # structure name -> index in kinds
    for i, r in enumerate(findable):
        for s in r[2]:
            kind.setdefault(norm(s), []).append(i)
            kname.setdefault(norm(s), re.sub(r' 1$', '', s))
    for k in sorted(kind):
        kind_ix[k] = len(kinds)
        kinds.append(kind[k])
    ids = sorted(f[:-5] for f in os.listdir(os.path.join(D, 'troves/places')) if f.endswith('.json'))
    if len(sys.argv) > 1:
        ids = [i for i in ids if i in sys.argv[1:]]
    index = []
    for cid in ids:
        cd = json.load(open(os.path.join(D, 'troves/places', cid + '.json')))
        sn = [norm(s) for s in cd['structs']]
        rows = []
        for p in cd['props']:
            ts = sorted({t for k in p[5] for t in kind.get(sn[k], [])})
            if not ts:
                continue
            pid = str(p[0])
            b = best.get(pid)
            stand, fee = (str(b[0]), b[1]) if b else (pid, fees.get(pid))
            rows.append({'pid': pid, 'addr': p[1], 'lat': p[2], 'lng': p[3], 'stand': stand, 'fee': fee, 'ts': ts, 'own': [kind_ix[sn[k]] for k in p[5] if sn[k] in kind_ix]})
        # stops within 80 m of each other
        r80 = 80 / M_LAT
        grid = {}
        cell = lambda x: (math.floor(x['lat'] / r80), math.floor(x['lng'] / (r80 / max(math.cos(math.radians(x['lat'])), .2))))
        for x in rows:
            grid.setdefault(cell(x), []).append(x)
        for x in rows:
            cy, cx = cell(x)
            n, reach = 0, list(x['own'])
            for a in (-1, 0, 1):
                for c in (-1, 0, 1):
                    for o in grid.get((cy + a, cx + c), []):
                        if o is not x and math.hypot((o['lat'] - x['lat']) * M_LAT, (o['lng'] - x['lng']) * M_LAT * math.cos(math.radians(x['lat']))) <= 80:
                            n += 1
                            reach.extend(o['own'])
            x['near'], x['reach'] = n, reach
        by_n = sorted(rows, key=lambda x: (-len(x['ts']), x['fee'] if x['fee'] is not None else 999))[:POOL]
        by_reach = sorted(rows, key=lambda x: (-len(x['reach']), x['fee'] if x['fee'] is not None else 999))[:POOL]
        by_fee = sorted((x for x in rows if len(x['ts']) >= 2 and x['fee'] is not None), key=lambda x: (x['fee'], -len(x['ts'])))[:POOL]
        keep = {x['pid']: x for x in by_n + by_reach + by_fee}
        stops = [[x['pid'], x['addr'], round(x['lat'], 5), round(x['lng'], 5), x['fee'], x['stand'], x['near'], x['ts'], sorted(x['reach'])] for x in sorted(keep.values(), key=lambda x: (x['fee'] if x['fee'] is not None else 999, -len(x['ts'])))]
        json.dump({'city': int(cid), 'name': cd['name'], 'updated': places.get('updated', ''), 'troves': names, 'rare': rare, 'kinds': kinds, 'kindNames': [kname[k] for k in sorted(kind)], 'stops': stops},
                  open(os.path.join(OUT, cid + '.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
        index.append([int(cid), cd['name'], len(stops)])
        print(cd['name'], len(rows), '->', len(stops), os.path.getsize(os.path.join(OUT, cid + '.json')) // 1024, 'KB')
    if len(sys.argv) == 1:
        json.dump(sorted(index, key=lambda r: r[1]), open(os.path.join(OUT, 'index.json'), 'w'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
