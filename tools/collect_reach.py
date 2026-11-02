#!/usr/bin/env python3
"""Cheaper places to stand while you trove: the teleport price of every property within reach of a costly structure property.

You collect from a structure by standing within reach of it (about 80 to 110 m by the hunting log), and the teleport price you pay is that of
the property you go to, not of the structure. So where a structure's own property costs 50 or 125 UPX, a house or an empty lot a few doors
away may cost 25. This reads those neighbours.

For each city (the one with the most costly structure properties first):
  1. every property of data/troves/places/<city>.json whose teleport price in data/troves/fees.json is at least --min-fee is a "seed";
  2. around each seed one small request to Upland's map lists every property of the box with its centre; the ones within --reach metres of
     the seed (and not structure properties already priced) are kept as candidates;
  3. each candidate's own record gives its teleport price.
Both steps are resumable: a stopped run is carried on by the next one. Output: data/troves/reach/<city id>.json, one small file per city:
  {"city", "name", "reach", "minFee", "seeds", "listed", "statuses", "rows": [[property id, lat, lng, status index, teleport price]]}
and data/troves/reach-state.json for the Backstage page (progress, and an estimate of what is left).

  python3 tools/collect_reach.py --max-minutes 300        # what the workflow runs
  python3 tools/collect_reach.py --cities 32 --max-minutes 5
  python3 tools/collect_reach.py --plan                    # only write the estimate
"""
import argparse
import concurrent.futures as cf
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PER_CIRCLE = 34      # properties inside a 100 m circle at Los Angeles's density (about 1,090 a km2)
OVERLAP = 0.55       # circles of neighbouring seeds overlap, so the new properties per seed are fewer
M_LAT = 111320.0


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def metres(lat1, lng1, lat2, lng2):
    return math.hypot((lat2 - lat1) * M_LAT, (lng2 - lng1) * M_LAT * math.cos(math.radians((lat1 + lat2) / 2)))


def seeds_of(cid, fees, min_fee):
    cd = json.load(open(os.path.join(ROOT, 'data/troves/places', f'{cid}.json')))
    seeds = sorted((str(p[0]), float(p[2]), float(p[3])) for p in cd['props'] if fees.get(str(p[0]), 0) >= min_fee)
    return cd['name'], seeds, {str(p[0]) for p in cd['props']}


def list_around(seed, reach, pacer):
    pid, lat, lng = seed
    h = (reach + 25) / M_LAT
    w = h / math.cos(math.radians(lat))
    rows = get_json(f'{API}/map?north={lat + h}&south={lat - h}&east={lng + w}&west={lng - w}', pacer)
    if rows is None:
        return None
    out = []
    for r in rows:
        try:
            q = str(r['prop_id'])
            la, lo = float(r['centerlat']), float(r['centerlng'])
        except (KeyError, ValueError, TypeError):
            continue
        if q != pid and metres(lat, lng, la, lo) <= reach:
            out.append((q, la, lo, r.get('status') or ''))
    return out


def estimate(cities, rate):
    """Properties still to list and read, and hours at the working rate, from what is done and the density of Los Angeles."""
    reads = lists = props = 0
    for c in cities:
        seeds, listed, cand, priced = c['seeds'], c['listed'], c['cand'], c['priced']
        lists += max(0, seeds - listed)
        total = len(cand) + max(0, seeds - listed) * PER_CIRCLE * OVERLAP
        props += total
        reads += max(0, total - priced)
    return {'listRequests': int(lists), 'estProps': int(props), 'readsLeft': int(reads), 'hoursLeft': round((lists + reads) / (rate * 0.85) / 3600, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cities', default='all', help='city ids, comma separated, or "all" (most costly structure properties first)')
    ap.add_argument('--min-fee', type=int, default=50, help='a structure property that costs at least this many UPX is worth looking around')
    ap.add_argument('--reach', type=float, default=100.0, help='metres around the structure property')
    ap.add_argument('--rate', type=float, default=5.0)
    ap.add_argument('--max-minutes', type=float, default=30)
    ap.add_argument('--plan', action='store_true', help='only write the estimate, read nothing from Upland')
    args = ap.parse_args()
    deadline = time.time() + args.max_minutes * 60
    fees = load('troves/fees.json', {'fees': {}})['fees']
    ids = [f[:-5] for f in os.listdir(os.path.join(ROOT, 'data/troves/places')) if f.endswith('.json')]
    info = {c: seeds_of(c, fees, args.min_fee) for c in ids}
    order = sorted((c for c in ids if info[c][1]), key=lambda c: (c != '32', -len(info[c][1])))
    if args.cities != 'all':
        want = args.cities.split(',')
        order = [c for c in order if c in want]
    pacer = Pacer(1.0 / args.rate)
    files, summary = {}, []

    def snapshot():
        cities = []
        for c in sorted(info, key=lambda c: (c != '32', -len(info[c][1]))):
            if not info[c][1]:
                continue
            d = files.get(c) or load(f'troves/reach/{c}.json', {})
            cand = d.get('rows', [])
            cities.append({'id': c, 'name': info[c][0], 'seeds': len(info[c][1]), 'listed': d.get('listed', 0), 'cand': cand, 'priced': sum(1 for x in cand if x[4] is not None)})
        est = estimate(cities, args.rate)
        save('troves/reach-state.json', {
            'updatedAt': now(), 'minFee': args.min_fee, 'reach': args.reach, 'cities': len(cities),
            'citiesDone': sum(1 for c in cities if c['listed'] >= c['seeds'] and c['priced'] >= len(c['cand'])),
            'seeds': sum(c['seeds'] for c in cities), 'listed': sum(min(c['listed'], c['seeds']) for c in cities),
            'candidates': sum(len(c['cand']) for c in cities), 'priced': sum(c['priced'] for c in cities), **est,
            'byCity': [[c['name'], c['seeds'], min(c['listed'], c['seeds']), len(c['cand']), c['priced']] for c in cities[:12]]})
        return est

    if args.plan:
        log(json.dumps(snapshot()))
        return
    for cid in order:
        if time.time() > deadline:
            break
        name, seeds, structure_ids = info[cid]
        path = f'troves/reach/{cid}.json'
        d = load(path, {})
        if d.get('minFee') != args.min_fee or d.get('reach') != args.reach:
            d = {}
        d.update({'city': int(cid), 'name': name, 'reach': args.reach, 'minFee': args.min_fee, 'seeds': len(seeds)})
        d.setdefault('listed', 0)
        d.setdefault('statuses', [])
        d.setdefault('rows', [])
        files[cid] = d
        have = {x[0]: x for x in d['rows']}
        # 1. list the neighbours of every costly property, 200 seeds at a time
        while d['listed'] < len(seeds) and time.time() < deadline:
            chunk = seeds[d['listed']:d['listed'] + 200]
            with cf.ThreadPoolExecutor(4) as ex:
                res = list(ex.map(lambda s: list_around(s, args.reach, pacer) if time.time() < deadline else None, chunk))
            ok = 0
            for r in res:
                if r is None:
                    break
                ok += 1
                for q, la, lo, st in r:
                    if q in have or q in structure_ids or q in fees:
                        continue
                    if st not in d['statuses']:
                        d['statuses'].append(st)
                    x = [q, round(la, 6), round(lo, 6), d['statuses'].index(st), None]
                    have[q] = x
                    d['rows'].append(x)
            d['listed'] += ok
            d['updatedAt'] = now()
            save(path, d)
            est = snapshot()
            log(f'{name}: {d["listed"]} of {len(seeds)} costly properties looked around, {len(d["rows"])} neighbours so far (about {est["hoursLeft"]} h left in all)')
            if ok < len(chunk):
                break
        if d['listed'] < len(seeds):
            break
        # 2. each neighbour's teleport price
        todo = [x for x in d['rows'] if x[4] is None]

        def one(x):
            if time.time() > deadline:
                return x, None
            try:
                r = get_json(f'{API}/properties/{x[0]}', pacer)
            except Exception:
                return x, None
            if r is None:
                return x, -1          # the record is gone: do not ask again
            p = r.get('teleport_price')
            return x, (-1 if p is None else p)

        with cf.ThreadPoolExecutor(4) as ex:
            for n, (x, p) in enumerate(ex.map(one, todo), 1):
                if p is not None:
                    x[4] = p
                if n % 400 == 0:
                    d['updatedAt'] = now()
                    save(path, d)
                    est = snapshot()
                    log(f'{name}: {n} of {len(todo)} prices read (about {est["hoursLeft"]} h left in all)')
        d['updatedAt'] = now()
        save(path, d)
        snapshot()
        log(f'{name}: {sum(1 for x in d["rows"] if x[4] is not None)} of {len(d["rows"])} neighbours priced')
    est = snapshot()
    log(f'stopped: about {est["hoursLeft"]} h of work left')


if __name__ == '__main__':
    main()
