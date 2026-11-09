#!/usr/bin/env python3
"""Rockdrigo's crafting history from the hunting recorder's session files: data/troves/rockdrigo/crafts.json

  python3 tools/build_crafts.py "/path/to/trove-hunting-session-....json" [more exports]

One row per craft: [seconds since epoch, structure, recipe, [[trove, units], ...]] where the outputs list the product and any bonus drop
(a different trove, or the product more than once). Addresses and ids are left out. Exports that overlap are merged by time, structure
instance and recipe, so the same craft is never counted twice.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'troves', 'rockdrigo', 'crafts.json')


def main(paths):
    seen, rows = set(), []
    if os.path.exists(OUT):
        old = json.load(open(OUT))
        for r in old['crafts']:
            seen.add((r[0], r[1], r[2])); rows.append(r)
    added = 0
    for path in paths:
        for c in json.load(open(path)).get('crafts', []):
            k = (c['t'] // 1000, c['building'], c['recipe'])
            if k in seen:
                continue
            seen.add(k)
            rows.append([c['t'] // 1000, c['building'], c['recipe'], [[o['name'], o['n']] for o in c['out']]])
            added += 1
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    json.dump({'format': 'upland-crafts-v1', 'note': 'Crafts seen by the hunting recorder: [seconds, structure, recipe, [[trove, units]...]]. A bonus drop is an output that is not the recipe, or the recipe made more than once.', 'crafts': rows}, open(OUT, 'w'), separators=(',', ':'))
    print('%d new crafts, %d in all, %d KB' % (added, len(rows), os.path.getsize(OUT) // 1024))


if __name__ == '__main__':
    main(sys.argv[1:])
