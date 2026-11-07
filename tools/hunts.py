#!/usr/bin/env python3
"""Keep the hunting-session exports in the repo and fold what they show into the trove source list.

  tools/hunts.py "/path/to/trove-hunting-session-....json" [--places]

Each export is merged into data/troves/rockdrigo/hunts.json (finds are de-duplicated by their id, so overlapping exports are fine).
The file is compact on purpose: one row per find, with the sources, troves, cities and properties kept in side tables.
  finds: [seconds since epoch, kind (0 structure, 1 plant), source index, trove index, quantity, property index, source instance]
  props: [property id, address, city index]
With --places, every (trove, source) pair seen in the log that data/troves/places.json does not list yet is added to it
(structures and plants alike; the balloon event is left out, it is not a place).
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'troves', 'rockdrigo', 'hunts.json')
PLACES = os.path.join(ROOT, 'data', 'troves', 'places.json')


def city_of(addr):
    p = [s.strip() for s in addr.split(',')]
    return p[-2] if len(p) >= 3 else (p[-1] if len(p) == 2 else '?')


def source_of(f):
    name = (f.get('sourceTypeName') or '').strip()
    model = f.get('sourceModel') or ''
    if model.startswith('balloon/'):
        return 'Balloon (' + model.split('_')[1] + ')', 'balloon'
    if name:
        return name, 'plant' if f['sourceKind'] == 'plant' else 'structure'
    return (f.get('sourceVariantName') or '').strip() or 'Unknown', f['sourceKind']


def table(rows, key):
    out, idx = [], {}
    for r in rows:
        k = key(r)
        if k not in idx:
            idx[k] = len(out)
            out.append(k)
    return out, idx


def load():
    if os.path.exists(OUT):
        return json.load(open(OUT))
    return {'format': 'upland-trove-hunts-v1', 'finds': [], 'src': [], 'troves': [], 'cities': [], 'props': []}


def from_recorder(raw):
    """The steampunk hunt recorder writes one row per hunt (a visit to a structure or plant) with its troves inside; turn it into the
    one-row-per-find shape the rest of this file works with. Structures are named from their model folder, which is all that export has."""
    addr = {}
    # properties the recorder gave no address for: the route files of the helper know many of them
    import glob
    for f in glob.glob(os.path.join(ROOT, 'data', 'helper', 'routes', '*.json')):
        if f.endswith('index.json'):
            continue
        r = json.load(open(f))
        for st in r['stops']:
            addr[str(st[0])] = st[1] + ', ' + r['name']
    for h in raw['hunts']:
        if h.get('address'):
            addr[h['prop']] = h['address']
    finds = []
    for h in raw['hunts']:
        if not h.get('troves'):
            continue
        model = h.get('model') or ''
        if h['kind'] == 'plant':
            name = h.get('type') or 'Unknown'
        else:
            parts = model.split('/')
            name = parts[1].replace('_', ' ').title() if len(parts) > 2 else 'Unknown'
        for t in h['troves']:
            finds.append({'at': h['t'], 'propertyId': h['prop'], 'name': t['name'], 'quantity': t.get('n', 1), 'sourceKind': h['kind'],
                          'sourceTypeName': name, 'sourceModel': model, 'sourceInstanceId': h['id'], 'address': addr.get(h['prop']) or ''})
    return {'createdAt': raw.get('createdAt', ''), 'from': raw.get('from', ''), 'finds': finds}


def merge(path):
    d = load()
    raw = json.load(open(path))
    if 'hunts' in raw and 'finds' not in raw:
        raw = from_recorder(raw)
    # no ids are kept: a find is the same find when second, property, source and trove agree; overlapping exports add only the surplus
    have = {}
    for at, _, si, ti, _, pi, inst in d['finds']:
        k = (at, d['props'][pi][0], tuple(d['src'][si]), d['troves'][ti], inst); have[k] = have.get(k, 0) + 1
    new = []
    for f in raw['finds']:
        k = (round(f['at'] / 1000), f['propertyId'], source_of(f), f['name'], int(f['sourceInstanceId']))
        if have.get(k, 0) > 0: have[k] -= 1
        else: new.append(f)
    src = {(s[0], s[1]): i for i, s in enumerate(d['src'])}
    tr = {t: i for i, t in enumerate(d['troves'])}
    ct = {c: i for i, c in enumerate(d['cities'])}
    pr = {p[0]: i for i, p in enumerate(d['props'])}
    for f in new:
        s = source_of(f)
        if s not in src:
            src[s] = len(d['src']); d['src'].append(list(s))
        if f['name'] not in tr:
            tr[f['name']] = len(d['troves']); d['troves'].append(f['name'])
        c = city_of(f['address'])
        if c not in ct:
            ct[c] = len(d['cities']); d['cities'].append(c)
        if f['propertyId'] not in pr:
            pr[f['propertyId']] = len(d['props']); d['props'].append([f['propertyId'], f['address'], ct[c]])
        d['finds'].append([round(f['at'] / 1000), 0 if f['sourceKind'] == 'structure' else 1, src[s], tr[f['name']], f['quantity'], pr[f['propertyId']], int(f['sourceInstanceId'])])
    d['finds'].sort(key=lambda r: r[0])
    d['updatedAt'] = raw.get('createdAt', '')[:10]
    d['from'] = raw.get('from', '')[:10]
    json.dump(d, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(new)} new finds, {len(d["finds"])} in all; {os.path.getsize(OUT) // 1024} KB')
    return d


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def add_places(d):
    p = json.load(open(PLACES))
    rows = {r[0]: r for r in p['troves']}
    added = 0
    for _, kind, si, ti, _, _, _ in d['finds']:
        name, skind = d['src'][si]
        if skind == 'balloon' or name == 'Unknown':
            continue
        r = rows.get(d['troves'][ti])
        if not r:
            continue
        lst = r[3] if skind == 'plant' else r[2]
        have = {re.sub(r' 1$', '', norm(x)) for x in r[2] + r[3]}
        if re.sub(r' 1$', '', norm(name)) in have:
            continue
        lst.append(name); lst.sort()
        added += 1
    p['updated'] = d.get('updatedAt', p.get('updated'))
    p['note'] = 'Where each trove is found and where it is crafted, from the Troves page of the Upland app, plus every place the hunting log has seen it come from.'
    json.dump(p, open(PLACES, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'{added} places added')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('export')
    ap.add_argument('--places', action='store_true')
    a = ap.parse_args()
    data = merge(a.export)
    if a.places:
        add_places(data)
