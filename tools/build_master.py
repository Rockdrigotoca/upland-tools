#!/usr/bin/env python3
"""The master trove list Sir Quailbert checks inventories against: data/helper/master.json

  python3 tools/build_master.py            # reads data/troves/rockdrigo/latest.json (the cleaned balance)

items:   [name, category, [troves asked at each of the 5 banking levels]]  (category and levels are empty for troves nobody holds yet)
recipes: [trove, [[ingredient, quantity], ...]]  (every recipe version we know)
Only names, numbers and recipes: nothing about the player the balance came from.
"""
import json, os, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
b = json.load(open(os.path.join(ROOT, 'data', 'troves', 'rockdrigo', 'latest.json')))
items = {i[0]: [i[0], i[1], list(i[4])] for i in b['items']}
for name, ings in b['recipes']:
    items.setdefault(name, [name, '', []])
    for g, _ in ings:
        items.setdefault(g, [g, '', []])
out = {'format': 'upland-master-v1', 'updated': datetime.date.today().isoformat(), 'max': b['troves']['max'],
       'items': sorted(items.values()), 'recipes': b['recipes']}
p = os.path.join(ROOT, 'data', 'helper', 'master.json')
json.dump(out, open(p, 'w'), separators=(',', ':'))
print(len(out['items']), 'troves,', len(out['recipes']), 'recipes,', os.path.getsize(p) // 1024, 'KB')
