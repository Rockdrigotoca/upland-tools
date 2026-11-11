#!/usr/bin/env python3
"""The map of a neighbourhood for the build planner: every lot's outline, what stands on it and where, and one footprint per structure.

1. Reads the Upland record of every property of the neighbourhood (data/structures/hoods.json) and writes
   data/structures/map/<hood>.json:
     rows: [property id, address, area (UP2), centre lat, centre lng, who, outline, buildings]
       who       the owner's username ('' when the lot is not minted); `group` in the file lists the builders of the plan
       outline   [[lng, lat], ...] of the lot (first point not repeated)
       buildings [[name, state (1 built, 0 under construction), lat, lng, turn (radians), scale, model id], ...]
2. Keeps data/structures/footprints.json: for each structure, the footprint Upland draws for it, in metres around the building's
   own point ({key: {name, model, poly, w, d, living, n, min, max, step}}; min, max and step are the spark limits in sparklets). With --fill it also reads one property for each structure of the
   world scan that has no footprint yet (the property lists of the city scan say where each one stands).

  python3 tools/collect_map.py --hoods quailwood
  python3 tools/collect_map.py --hoods quailwood --fill 400
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json   # noqa: E402

GROUP = ['rockdrigo', 'mstullis', 'missmarlow', 'talljames', 'wamawa', 'bielykvietok', 'realistix', 'huskyb']   # the builders of the plan
SCAN = '/Users/rock/Claude/Upland/Troves/city-scan/'


def key(name):
    s = unicodedata.normalize('NFKD', str(name))
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).strip())


def outline(p):
    try:
        g = json.loads(p.get('boundaries') or '{}')
        ring = g['coordinates'][0] if g.get('type') == 'Polygon' else g['coordinates'][0][0]
    except (ValueError, KeyError, IndexError, TypeError):
        return []
    ring = [[round(x, 7), round(y, 7)] for x, y in ring]
    return ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring


def note_footprints(p, prints):
    """Remember the footprint of every building of this property (the first one seen per structure is kept; n counts sightings)."""
    for b in p.get('buildings') or []:
        name, poly = b.get('buildingName'), b.get('polygon')
        if not name or not poly:
            continue
        k = key(name)
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        e = prints.get(k)
        d = b.get('details') or {}
        if e is not None and d.get('maxStackedSparks') and 'max' not in e:   # spark limits, in sparklets as Upland gives them
            e.update({'min': d.get('minStackedSparks'), 'max': d.get('maxStackedSparks'), 'step': d.get('stepSparks')})
        if e is None:
            prints[k] = {'name': name.strip(), 'model': b.get('modelId'), 'poly': [[round(x, 2), round(y, 2)] for x, y in poly[:-1]],
                         'w': round(max(xs) - min(xs), 2), 'd': round(max(ys) - min(ys), 2),
                         'living': 1 if b.get('isAvailableForHomeAddressApplying') else 0, 'n': 1,
                         'min': d.get('minStackedSparks'), 'max': d.get('maxStackedSparks'), 'step': d.get('stepSparks')}
        else:
            e['n'] += 1


def row(p):
    owner = (p.get('owner_username') or '').lower()
    who = owner or ('?' if p.get('owner') else '')
    bs = []
    for b in p.get('buildings') or []:
        if not b.get('buildingName'):
            continue
        rot = b.get('rotate') or [0, 0, 0]
        bs.append([b['buildingName'].strip(), 1 if b.get('constructionStatus') == 'completed' else 0, round(b.get('lat') or 0, 7),
                   round(b.get('lng') or 0, 7), round(rot[1], 5), b.get('scale') or 1, b.get('modelId')])
    return [str(p['prop_id']), p.get('full_address') or '', p.get('area'), round(float(p.get('centerlat') or 0), 7),
            round(float(p.get('centerlng') or 0), 7), who, outline(p), bs]


def read_many(ids, pacer, workers, deadline):
    def one(pid):
        if time.time() > deadline:
            return None
        try:
            return get_json(f'{API}/properties/{pid}', pacer)
        except Exception:
            return None
    with cf.ThreadPoolExecutor(workers) as ex:
        for k, p in enumerate(ex.map(one, ids), 1):
            if k % 200 == 0:
                log(f'  {k} of {len(ids)}')
            yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hoods', default='quailwood', help='comma-separated keys from hoods.json; empty = none')
    ap.add_argument('--fill', type=int, default=0, help='also read up to this many properties for structures without a footprint')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--rate', type=float, default=5.0)
    ap.add_argument('--minutes', type=float, default=30)
    args = ap.parse_args()
    deadline, pacer = time.time() + args.minutes * 60, Pacer(1.0 / args.rate)
    fp = load('structures/footprints.json', {})
    prints = fp.get('structures') or {}
    hoods = load('structures/hoods.json', {}).get('hoods') or {}
    for h in [x for x in args.hoods.split(',') if x]:
        ids = hoods[h]['ids']
        log(f'{h}: reading {len(ids)} properties')
        rows, failed = [], 0
        for p in read_many(ids, pacer, args.workers, deadline):
            if not p:
                failed += 1
                continue
            rows.append(row(p))
            note_footprints(p, prints)
        if failed > len(ids) * 0.1:
            log(f'{h}: {failed} properties could not be read; keeping the previous file')
            continue
        save(f'structures/map/{h}.json', {'hood': h, 'name': hoods[h].get('name', h), 'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                           'failed': failed, 'group': GROUP, 'rows': rows})
        log(f'{h}: {len(rows)} lots, {sum(len(r[7]) for r in rows)} buildings, {failed} failed')
    if args.fill:
        want = {key(e['name']): e['name'] for e in load('troves/world.json', {}).get('structures', {}).values()}
        todo = {k for k in want if k not in prints or not prints[k].get('max')}   # also the ones read before the spark limits were kept
        where = {}
        for f in sorted(glob.glob(SCAN + '*properties.jsonl')):
            for line in open(f):
                try:
                    j = json.loads(line)
                except ValueError:
                    continue
                for b in j.get('built') or []:
                    if key(b) in todo:
                        where.setdefault(key(b), []).append(j['id'])
        log(f'{len(todo)} structures without a footprint, {len(where)} of them seen in the city scan')
        tried = 0
        for attempt in range(3):   # a property may have changed since the scan: try up to three per structure
            ids = [v[attempt] for k, v in sorted(where.items()) if not (prints.get(k) or {}).get('max') and len(v) > attempt][:max(0, args.fill - tried)]
            if not ids:
                break
            tried += len(ids)
            for p in read_many(ids, pacer, args.workers, deadline):
                if p:
                    note_footprints(p, prints)
        left = sorted(want[k] for k in todo if not (prints.get(k) or {}).get('max'))
        log(f'{tried} properties read; still without a footprint or spark limits: {left}')
    save('structures/footprints.json', {'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                        'note': 'Footprint of each structure in metres around its own point, as Upland draws it. n = times seen.',
                                        'structures': dict(sorted(prints.items()))})
    log(f'{len(prints)} footprints')


if __name__ == '__main__':
    main()
