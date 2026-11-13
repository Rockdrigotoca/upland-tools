#!/usr/bin/env python3
"""Focused hunting routes for the trove extension: the hardest troves of one city, as two CSV files (top tier, then the next best).

  python3 tools/build_focus_csv.py --city 85 --user bielykvietok --out ~/Downloads --tag Bielyk_Washington

Columns are the extension's own: name,property_id,city_id,order  (the same as Focused_route.csv and Discovery_route.csv).

Which troves: the hard ones of data/helper/hard.json (12 places or fewer give them) that the city can give. How much each is worth is read
from the player's own trove file (data/troves/rockdrigo/latest.json, "my data"): a trove never banked counts triple, one banked once with a
small stock counts double. Tier 1 is the hardest (5 places or fewer give it, or it was never banked); tier 2 is the rest of the hard ones.

Which properties: every property of the city with a structure, scored by the chance that a visit finds a tier trove. A structure in reach
(sure up to 60 m, fading to 100 m, see memory trove-reach-geometry) gives one find, drawn from its own list, so a trove's chance from a structure is
1 / the length of that structure's list. The list is built greedily: best property first, then the best of what is still unfound, so the order spreads
over the city and stops when a new property adds almost nothing. Tier 2 never repeats a property of tier 1. Where the player owns a property within
250 m (data/helper/own/<user>/<city>.json) the row is that free property ("own, free") and the avatar then walks to the stop; otherwise it is the cheapest
stand within 80 m, with its fee.
"""
import argparse
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')
M_LAT = 111320.0


def norm(s):
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip())


def reach_weight(d):
    if d <= 60:
        return 1.0
    if d >= 100:
        return 0.0
    pts = [(60, 1.0), (70, .63), (80, .46), (90, .3), (100, 0.0)]
    for (d0, w0), (d1, w1) in zip(pts, pts[1:]):
        if d <= d1:
            return w0 + (w1 - w0) * (d - d0) / (d1 - d0)
    return 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--city', default='85')
    ap.add_argument('--user', default='bielykvietok')
    ap.add_argument('--out', default=os.path.expanduser('~/Downloads'))
    ap.add_argument('--tag', default='Focus')
    ap.add_argument('--walk', type=int, default=150, help='longest walk from one of her own properties to a stop, in metres')
    ap.add_argument('--max', type=int, default=400, help='most properties in one file')
    ap.add_argument('--floor', type=float, default=0.005, help='stop when a property adds less than this share of the first one')
    a = ap.parse_args()
    cid = str(a.city)
    places = json.load(open(os.path.join(D, 'troves/places.json')))
    hard = json.load(open(os.path.join(D, 'helper/hard.json')))
    mine = {x[0]: x for x in json.load(open(os.path.join(D, 'troves/rockdrigo/latest.json')))['items']}   # name, category, quantity, banked level
    fees = json.load(open(os.path.join(D, 'troves/fees.json')))['fees']
    best = json.load(open(os.path.join(D, 'troves/reach-best.json')))['best80']
    cd = json.load(open(os.path.join(D, 'troves/places', cid + '.json')))
    try:
        own = json.load(open(os.path.join(D, 'helper/own', a.user, cid + '.json')))['stops']
    except FileNotFoundError:
        own = {}
    # what each kind of structure can give (its whole list), and the hard troves this city can give
    kind = {}
    for r in places['troves']:
        for s in r[2]:
            kind.setdefault(norm(s), set()).add(r[0])
    sn = [norm(s) for s in cd['structs']]
    present = {n for p in cd['props'] for k in p[5] for n in [sn[k]]}
    targets = {}
    for n, v in hard['troves'].items():
        if cid not in v['c']:
            continue
        x = mine.get(n)
        level, qty = (x[3], x[2]) if x else (0, 0)
        need = 3 if level == 0 else 2 if level == 1 and qty < 10 else 1
        tier = 1 if v['s'] <= 5 or level == 0 else 2
        targets[n] = {'s': v['s'], 'need': need, 'tier': tier, 'value': need * 12.0 / v['s']}
    # properties with a structure, and what is in reach of each
    rows = []
    for p in cd['props']:
        ks = [sn[k] for k in p[5] if sn[k] in kind]
        if ks:
            rows.append({'pid': str(p[0]), 'addr': p[1], 'lat': p[2], 'lng': p[3], 'ks': ks})
    r100 = 100 / M_LAT
    grid = {}
    cell = lambda x: (math.floor(x['lat'] / r100), math.floor(x['lng'] / (r100 / max(math.cos(math.radians(x['lat'])), .2))))
    for x in rows:
        grid.setdefault(cell(x), []).append(x)
    for x in rows:
        cy, cx = cell(x)
        chance = {}   # trove -> chance a visit here finds it (any structure in reach, one find each)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for o in grid.get((cy + dy, cx + dx), []):
                    d = 0 if o is x else math.hypot((o['lat'] - x['lat']) * M_LAT, (o['lng'] - x['lng']) * M_LAT * math.cos(math.radians(x['lat'])))
                    w = reach_weight(d)
                    if w <= 0:
                        continue
                    for k in o['ks']:
                        lst = kind[k]
                        for t in lst:
                            if t in targets:
                                chance[t] = 1 - (1 - chance.get(t, 0)) * (1 - w / len(lst))
        x['chance'] = chance
        b = best.get(x['pid'])
        x['stand'], x['fee'] = (str(b[0]), b[1]) if b else (x['pid'], fees.get(x['pid']))
        o = own.get(x['pid'])
        x['own'] = o if o and o[2] <= a.walk else None   # [own property id, own address, metres] or None
        x['key'] = x['own'][0] if x['own'] else x['stand']   # the property the extension visits: never twice in a file
    out_dir = os.path.expanduser(a.out)
    used = set()
    summary = []
    chosen = []
    for tier in (1, 2):
        T = {n: t for n, t in targets.items() if t['tier'] == tier}
        left = {n: 1.0 for n in T}   # chance a trove is still unfound
        picked, first = [], None
        pool = [x for x in rows if x['key'] not in used and any(t in T for t in x['chance'])]
        while pool and len(picked) < a.max:
            def score(x):
                g = sum(T[t]['value'] * left[t] * c for t, c in x['chance'].items() if t in T)
                fee = 0 if x['own'] else (x['fee'] if x['fee'] is not None else 50)
                return g / (1 + fee / 100.0), g
            sc = [(score(x), x) for x in pool]
            (s, g), x = max(sc, key=lambda z: z[0][0])
            if first is None:
                first = s
            if s < first * a.floor:
                break
            picked.append((x, g))
            for t, c in x['chance'].items():
                if t in T:
                    left[t] *= 1 - c
            pool = [y for y in pool if y['key'] != x['key']]   # a property already in the list is not visited again
            used.add(x['key'])
            chosen.append(x)
        name = f'{a.tag}_tier{tier}_{"hardest" if tier == 1 else "next_best"}.csv'
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8', newline='') as f:
            f.write('name,property_id,city_id,order\n')
            for i, (x, g) in enumerate(picked, 1):
                top = [t for t, c in sorted(x['chance'].items(), key=lambda kv: -T.get(kv[0], {'value': 0})['value'] * kv[1]) if t in T]
                hit = '/'.join(top[:6]) + (f' +{len(top) - 6}' if len(top) > 6 else '')
                if x['own']:
                    label, pid = f'{x["own"][1]} (own, free) -> ~{x["own"][2]} m to {x["addr"]} [{hit}]', x['own'][0]
                else:
                    label, pid = f'{x["addr"]} (fee {x["fee"] if x["fee"] is not None else "?"}) [{hit}]', x['stand']
                f.write('"' + label.replace('"', "'") + f'",{pid},{cid},{i}\n')
        got = {t: round(1 - left[t], 2) for t in T}
        summary.append((name, len(picked), sum(1 for x, _ in picked if x['own']), T, got, targets))
        cum = [sum(g for _, g in picked[:n]) for n in (20, 100, len(picked))]
        print(f'  worth-weighted hits per visit: first 20 {cum[0] / max(1, min(20, len(picked))):.2f}, first 100 {cum[1] / max(1, min(100, len(picked))):.2f}, last visit {picked[-1][1]:.2f}')
        print(f'{name}: {len(picked)} properties ({sum(1 for x, _ in picked if x["own"])} free), {len(T)} troves; chance each is found once over the whole file:')
        print('   ' + ', '.join(f'{t} {got[t]:.2f}' for t in sorted(T, key=lambda t: got[t])[:12]) + (' ...' if len(T) > 12 else ''))
    # over both files together: the chance each hard trove is found at least once in one full pass, and how many finds to expect
    print('both files together, one full pass (chance of at least one find / finds to expect):')
    for t in sorted(targets, key=lambda t: (targets[t]['tier'], targets[t]['s'])):
        miss, exp = 1.0, 0.0
        for x in chosen:
            c = x['chance'].get(t, 0)
            miss *= 1 - c
            exp += c
        targets[t]['p'], targets[t]['exp'] = 1 - miss, exp
    for tier in (1, 2):
        print(f'  tier {tier}: ' + ', '.join(f'{t} {targets[t]["p"]:.2f}/{targets[t]["exp"]:.1f}' for t in sorted((t for t in targets if targets[t]['tier'] == tier), key=lambda t: targets[t]['p'])))
    print('hard troves this city cannot give:', sorted(n for n in hard['troves'] if n not in targets))


if __name__ == '__main__':
    main()
