#!/usr/bin/env python3
"""Fold UPXLand's trove lists (data/troves/upxland.json, read from upxland.me/troves/structures) into data/troves/places.json.

  python3 tools/merge_upxland.py

For every trove the structure and plant lists become the union of ours and UPXLand's (names that differ only in case or punctuation count as the
same), "crafted here" is added to craftAt, and a sixth entry lists the structures that can drop it as a bonus when something is crafted there.
Troves we did not have yet are added (their category is taken from the latest balance when you hold one, else left empty).
Safe to run again.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data', 'troves')


def norm(s):
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip())


def union(ours, theirs):
    have = {norm(x) for x in ours}
    out = list(ours)
    for x in theirs:
        if norm(x) not in have:
            have.add(norm(x))
            out.append(x)
    return sorted(out, key=lambda x: x.lower())


def main():
    up = json.load(open(os.path.join(D, 'upxland.json')))
    places = json.load(open(os.path.join(D, 'places.json')))
    bal = json.load(open(os.path.join(D, 'rockdrigo', 'latest.json')))
    cats = {i[0]: i[1] for i in bal['items']}
    names = up['troves']
    found, crafted, bonus, plants = {}, {}, {}, {}
    for s in up['structures']:
        for key, dst in (('found', found), ('crafted', crafted), ('bonus', bonus)):
            for i in s[key]:
                dst.setdefault(names[i], []).append(s['name'])
    for p in up['plants']:
        for i in p['found']:
            plants.setdefault(names[i], []).append(p['name'])
    rows = {r[0]: r for r in places['troves']}
    added = grew = 0
    for n in names:
        b = sorted(set(bonus.get(n, [])), key=lambda x: x.lower())
        if n not in rows:
            rows[n] = [n, cats.get(n, ''), [], [], [], []]
            added += 1
        r = rows[n]
        r += [[]] * (6 - len(r))
        before = (len(r[2]), len(r[3]), len(r[4]))
        r[2] = union(r[2], found.get(n, []))
        r[3] = union(r[3], plants.get(n, []))
        r[4] = union(r[4], crafted.get(n, []))
        r[5] = b
        grew += before != (len(r[2]), len(r[3]), len(r[4]))
    for r in rows.values():
        r += [[]] * (6 - len(r))
    places['troves'] = sorted(rows.values(), key=lambda r: r[0])
    places['updated'] = '2026-11-07'
    places['note'] = ('Where each trove is found and where it is crafted, from the Troves page of the Upland app and UPXLand, plus every place the hunting log has seen it come from. '
                      'The last entry is the structures that can drop it as a bonus when something is crafted there.')
    json.dump(places, open(os.path.join(D, 'places.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(places["troves"])} troves ({added} added, {grew} grew), bonus lists on {sum(1 for r in places["troves"] if r[5])}')


if __name__ == '__main__':
    main()
