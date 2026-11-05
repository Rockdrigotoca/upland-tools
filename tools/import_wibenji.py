#!/usr/bin/env python3
"""Folds Wibenji's TroveHelper baseline (used with permission) into two small files for the trove pages.

  python3 tools/import_wibenji.py ~/Downloads/trove-helper-baseline.json

Writes data/troves/wibenji.json: {"credit", "fetchedAt",
  "hotspots": {city name: [[property id, address, neighbourhood, structure count, trove count]]},   (top 25 per city that has data)
  "plants": [{"name", "troves": [names], "props": [[property id, address, city]]}]}   (every plant family with at least one known property)
Only what the pages use is kept: the file is not copied whole.
"""
import json
import sys


def city_of(addr):
    p = [s.strip() for s in addr.split(',')]
    return p[-2] if len(p) >= 3 else '?'


def main(path):
    d = json.load(open(path))
    hot = {c['name']: [[h['propertyId'], h['address'], h.get('neighborhood', ''), h['structureCount'], h['troveCount']] for h in c['hotspots']] for c in d['cities'] if c['hotspots']}
    fam = {}
    for a in d['associations']:
        if a['sourceKind'] != 'plant' or not a['sourceTypeName']:
            continue
        f = fam.setdefault(a['sourceTypeName'], {'troves': set(), 'props': {}})
        f['troves'].add(a['name'])
        for p in a['properties']:
            f['props'][p['id']] = [p['id'], p['address'], city_of(p['address'])]
    plants = [{'name': n, 'troves': sorted(f['troves']), 'props': sorted(f['props'].values(), key=lambda r: (r[2], r[1]))} for n, f in sorted(fam.items()) if f['props']]
    out = {'credit': 'Wibenji’s TroveHelper scan, used with permission', 'fetchedAt': d.get('fetchedAt', ''), 'hotspots': hot, 'plants': plants}
    json.dump(out, open('data/troves/wibenji.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(hot), 'cities with hotspots,', len(plants), 'plant families,', sum(len(p['props']) for p in plants), 'plant properties')


if __name__ == '__main__':
    main(sys.argv[1])
