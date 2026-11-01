#!/usr/bin/env python3
"""Put every structure scan together: which structure exists in which city, and how many.

Reads data/structures/world/<city id>.json (the service-structure scan of a whole city) and, for cities not scanned that way yet, the
neighbourhood scans we already have (Nomentano in Rome, Quailwood in Bakersfield, Estrella in Madrid). Writes data/troves/world.json,
which the Troves page uses to say where in the world each trove can be found, and which troves are tied to one city.
"""
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import DATA, load, log, save   # noqa: E402

NEIGHBOURHOOD_SCANS = {'nomentano': 115, 'quailwood': 9, 'estrella-madrid': 117}
NAMES = {9: 'Bakersfield', 32: 'Los Angeles', 85: 'Washington D.C.', 91: 'Paris', 115: 'Rome', 117: 'Madrid', 137: 'Florence', 139: 'Takasaki'}


def norm(name):
    n = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', n).strip())


def living_set():
    return {norm(n) for n in load('structures/world/kinds.json', {}).get('living', [])}


def main():
    living = living_set()
    names = {**NAMES, **{int(k): v for k, v in load('structures/world/cities.json', {}).items()}}
    cities, structures = {}, {}

    def add(cid, kind, label, built, building, read, total, done):
        cities[cid] = {'id': cid, 'name': names.get(cid) or label or f'City {cid}', 'kind': kind, 'read': read, 'total': total, 'done': done}
        for n, c in built.items():
            e = structures.setdefault(norm(n), {'name': n, 'c': {}})
            if norm(n) in living:
                e['living'] = True   # a home, not a service structure: kept apart so it is never counted as one
                e.setdefault('h', {})[str(cid)] = e.get('h', {}).get(str(cid), 0) + c
                continue
            e['c'][str(cid)] = e['c'].get(str(cid), 0) + c
        for n, c in building.items():
            if norm(n) in living:
                continue
            e = structures.setdefault(norm(n), {'name': n, 'c': {}})
            e.setdefault('b', {})[str(cid)] = e.get('b', {}).get(str(cid), 0) + c

    wdir = os.path.join(DATA, 'structures', 'world')
    for f in sorted(os.listdir(wdir)) if os.path.isdir(wdir) else []:
        if f.endswith('.json') and f != 'cities.json' and f[:-5].isdigit():
            d = load(f'structures/world/{f}', {})
            if d.get('built') is not None:
                add(d['city_id'], 'scan', d.get('name'), d['built'], d.get('building', {}), d.get('read', 0), d.get('total', 0), bool(d.get('done')))
    for key, cid in NEIGHBOURHOOD_SCANS.items():
        if cid in cities:
            continue
        d = load(f'structures/{key}.json', {})
        if d.get('built'):
            add(cid, 'neighbourhood', None, d['built'], d.get('building', {}), d.get('read', 0), d.get('properties', 0), True)
            cities[cid]['name'] = f"{names.get(cid, 'City ' + str(cid))} (only {d.get('name', key)})"
    out = {'updatedAt': time.strftime('%Y-%m-%d', time.gmtime()), 'cities': sorted(cities.values(), key=lambda c: c['name']), 'structures': structures}
    save('troves/world.json', out)
    log(f'{len(cities)} cities, {len(structures)} structure types -> data/troves/world.json')


if __name__ == '__main__':
    main()
