#!/usr/bin/env python3
"""The hard-to-find troves and where each can be had cheaply, city by city: data/helper/hard.json, plus "bonus": {trove: structures that can drop it when something is crafted there} for the troves only a bonus drop gives.

  {"updated", "max": largest number of places that still counts as hard,
   "troves": {name: {"s": places that give it (structures and plants), "c": {city id: [properties that carry a structure giving it,
                     stand fee, stand property id, address]}}}}

A trove is hard when 12 places or fewer give it (and at least one is a structure, which is what a property can carry). For each city
the entry is the cheapest property to stand at: the property with the structure, or the cheaper one within 80 m when
data/troves/reach-best.json knows one. Read by the Discord bot (Discover), the Trove Helper and the Troves page.

  python3 tools/build_hard.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')
MAX = 12


def norm(s):
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip())


def main():
    places = json.load(open(os.path.join(D, 'troves/places.json')))
    fees = json.load(open(os.path.join(D, 'troves/fees.json')))['fees']
    best = json.load(open(os.path.join(D, 'troves/reach-best.json')))['best80']
    hard = {r[0]: {'s': len(r[2]) + len(r[3]), 'h': {norm(x) for x in r[2]}, 'c': {}} for r in places['troves'] if r[2] and len(r[2]) + len(r[3]) <= MAX}
    by_struct = {}
    for n, h in hard.items():
        for k in h['h']:
            by_struct.setdefault(k, []).append(n)
    for f in sorted(os.listdir(os.path.join(D, 'troves/places'))):
        if not f.endswith('.json') or f == 'index.json':
            continue
        cid = f[:-5]
        cd = json.load(open(os.path.join(D, 'troves/places', f)))
        sn = [norm(s) for s in cd['structs']]
        for p in cd['props']:
            pid = str(p[0])
            names = {n for k in p[5] for n in by_struct.get(sn[k], [])}
            if not names:
                continue
            b = best.get(pid)
            stand, fee = (str(b[0]), b[1]) if b else (pid, fees.get(pid))
            for n in names:
                c = hard[n]['c'].get(cid)
                if c is None:
                    hard[n]['c'][cid] = [1, fee, stand, p[1]]
                else:
                    c[0] += 1
                    if fee is not None and (c[1] is None or fee < c[1]):
                        c[1:] = [fee, stand, p[1]]
    # troves no structure or plant gives: they only drop as a bonus when something is crafted at one of these structures
    bonus = {r[0]: sorted(r[5], key=lambda x: (len(x), x)) for r in places['troves'] if len(r) > 5 and r[5] and not r[2] and not r[3]}
    out = {'updated': places.get('updated', ''), 'max': MAX, 'troves': {n: {'s': v['s'], 'c': v['c']} for n, v in sorted(hard.items())}, 'bonus': bonus}
    path = os.path.join(D, 'helper', 'hard.json')
    json.dump(out, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(out['troves']), 'hard troves,', os.path.getsize(path) // 1024, 'KB')


if __name__ == '__main__':
    main()
