#!/usr/bin/env python3
"""The next five troves after a craft session, measured against the stock you will hold when the session is done.

  python3 next_five.py <session data.json> [city id=32] [out.json]

Reads the planner's data (meta.final = [item, before, after] for every item the session changes), rebuilds the stock after the
session, ranks every locked trove that has a known craft site by how few raw items it still lacks, and writes data['next5']:
  rank      the five names, in order
  combined  one shopping list for the five together (shared stock, in rank order): [item, need, have after, missing, [who needs it]]
  cards     every ranked trove (first 5 = the next 5, then up to 10 more): ingredients, crafts, structures, misses in the city and in Queens
Troves with no known craft site are left out.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1]
CITY = int(sys.argv[2]) if len(sys.argv) > 2 else 32
OUT = sys.argv[3] if len(sys.argv) > 3 else DATA
NO_SITE = {'Golden Record', 'Invisible Cloak', 'Jade Dragon', 'Meteorite', 'Skeleton Key'}

# reuse the planner's loading code (balance, recipes, craft sites) up to the point where it reads its targets
src = open(os.path.join(HERE, 'plan_city_session.py')).read().split('TARGETS=TARGETS_ARG')[0]
sys.argv = ['plan_city_session.py', str(CITY), 'x', 'x']
G = {'__name__': 'plan'}
exec(compile(src, 'plan_city_session', 'exec'), G)
V, norm, REC, SITES, STOCK = G['V'] if 'V' in G else (lambda *a: tuple(sorted(a))), G['norm'], G['REC'], G['SITES'], G['STOCK']
SITES[('Chisel Set', tuple(sorted((('Iron Ore', 2), ('Twine', 1)))))].update({'art gallery': 'seen', 'art museum': 'seen'})
SITES[('Holiday Ham', tuple(sorted((('Pork', 5), ('Honey', 5), ('Hooray', 5)))))].update({'community center': 'seen'})

d = json.load(open(DATA))
meta = d['meta']
after = collections.Counter(STOCK)
for name, before, aft in meta['final']:
    after[name] = aft
bal = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'data/troves/rockdrigo/latest.json')))
FOUND = {i[0] for i in bal['items']}
unlocked = {u['t'] for u in meta['unlocked']}


def keys_for(city):
    q = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'data/troves/places/%d.json' % city)))
    return {norm(n) for n in q['structs']}


KEYS = {CITY: keys_for(CITY), 4: keys_for(4)}


def sites(item, v, city):
    if item == 'Compass' and any(x == 'Binoculars' for x, _ in v):
        return {}
    return {k: e for k, e in SITES.get((item, v), {}).items() if k in KEYS[city]}


def plan(item, n, stock, depth, path, city):
    miss = collections.Counter()
    crafts = []
    have = min(stock[item], n)
    stock[item] -= have
    need = n - have
    while need > 0:
        if item not in REC or item in path or depth <= 0:
            miss[item] += need
            return miss, crafts
        best = None
        for v in REC[item]:
            if not sites(item, v, city):
                continue
            st = collections.Counter(stock)
            m = collections.Counter()
            cr = []
            for x, q in v:
                mm, cc = plan(x, q, st, depth - 1, path + (item,), city)
                m += mm
                cr += cc
            sc = (sum(m.values()), len(cr))
            if best is None or sc < best[0]:
                best = (sc, m, cr, st, v)
        if best is None:
            miss[item] += need
            return miss, crafts
        _, m, cr, st, v = best
        stock.clear()
        stock.update(st)
        miss += m
        crafts += cr + [(item, v)]
        need -= 1
    return miss, crafts


def describe(name, stock, city):
    """One trove planned alone against `stock` (a Counter, copied)."""
    st = collections.Counter(stock)
    miss, crafts = plan(name, 1, st, 8, (), city)
    need = collections.Counter()
    made = collections.Counter()
    for item, v in crafts:
        made[item] += 1
        for x, q in v:
            need[x] += q
    # what comes out of your stock (or is missing): everything needed that the plan does not itself craft
    raw = {}
    for x, q in need.items():
        take = q - made[x]
        if take > 0:
            raw[x] = take
    by_item = collections.OrderedDict()
    for item, v in crafts:
        e = by_item.setdefault(item, {'n': 0, 'at': sorted(k.title() for k in sites(item, v, city))[:4], 'ver': [[x, q] for x, q in v]})
        e['n'] += 1
    return miss, crafts, raw, list(by_item.items())


cand = sorted(t for t in REC if t not in FOUND and t not in NO_SITE and t not in unlocked)
rows = []
for t in cand:
    miss, crafts, raw, by = describe(t, after, CITY)
    qmiss, qcr, _, _ = describe(t, after, 4)
    rows.append((sum(miss.values()), len(crafts), t, miss, crafts, raw, by, qmiss))
rows.sort(key=lambda r: (r[0], r[1], r[2]))
top = rows[:15]

# combined list for the first five, in rank order, with shared stock
shared = collections.Counter(after)
comb_need = collections.Counter()
comb_miss = collections.Counter()
who = collections.defaultdict(list)
for r in top[:5]:
    st = collections.Counter(shared)
    miss, crafts = plan(r[2], 1, st, 8, (), CITY)
    shared = st
    comb_miss += miss
    for x in miss:
        who[x].append(r[2]) if r[2] not in who[x] else None
    made = collections.Counter(i for i, _ in crafts)
    need = collections.Counter()
    for item, v in crafts:
        for x, q in v:
            need[x] += q
    for x, q in need.items():
        if q - made[x] > 0:
            comb_need[x] += q - made[x]
            who[x].append(r[2])
# missing items that never reached `need` (they are needed but absent from stock): add them
for x, q in comb_miss.items():
    comb_need[x] = max(comb_need[x], q)
combined = []
for x in comb_need:
    have = after[x]
    need = comb_need[x]
    combined.append([x, need, have, max(0, need - have), list(dict.fromkeys(who[x]))])
combined.sort(key=lambda c: (-c[3], -c[1], c[0]))

cards = []
for i, (nm, nc, t, miss, crafts, raw, by, qmiss) in enumerate(top):
    ing = []
    for x, q in raw.items():
        have = after[x]
        ing.append([x, q, have, max(0, q - have)])
    ing.sort(key=lambda a: (-a[3], -a[1], a[0]))
    others = [o[2] for o in top[:5] if o[2] != t]
    comp = []
    for x, q, have, m in ing:
        users = [o[2] for o in top[:5] if o[2] != t and x in o[5]]
        if users and sum([o[5].get(x, 0) for o in top[:5]]) > have:
            comp.append([x, users])
    cards.append({'name': t, 'rank': i + 1, 'next5': i < 5, 'missing': sum(miss.values()), 'units': sum(raw.values()), 'crafts': len(crafts),
                  'miss': dict(miss), 'qmiss': sum(qmiss.values()), 'qmissItems': dict(qmiss), 'ingredients': ing,
                  'chain': [[item, e['n'], e['at'], e['ver']] for item, e in by], 'competes': comp})

d['next5'] = {'rank': [c['name'] for c in cards[:5]], 'combined': combined, 'cards': cards, 'city': CITY,
              'basis': 'stock after the session: %d troves, %d items changed by the plan' % (meta['val']['total'] + len(unlocked), len(meta['final']))}
json.dump(d, open(OUT, 'w'), ensure_ascii=False)
print('next five:', d['next5']['rank'])
for c in cards:
    print('%2d %-14s missing %3d  units %4d  crafts %3d  queens-missing %3d' % (c['rank'], c['name'], c['missing'], c['units'], c['crafts'], c['qmiss']))
print('combined missing:', [(c[0], c[3]) for c in combined if c[3]])
