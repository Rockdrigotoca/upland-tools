#!/usr/bin/env python3
"""What does it cost to teleport to the properties worth visiting for troves? The public property record carries `teleport_price`
(UPX). This reads it for: the properties of --city that carry a structure giving a trove the latest inventory is missing, the
properties listed in data/troves/city-specific.json, and the Bermuda fish properties. Resumable: ids already in fees.json are skipped.

Writes data/troves/fees.json: {"updatedAt":..., "fees": {property id: UPX}}. One request per property, about five a second.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cities', default='32,91', help='city ids whose hotspots are read (32 is Los Angeles), or "all" for every scanned city')
    ap.add_argument('--all', action='store_true', help='read every property of --cities that carries a service structure, not only trove hotspots')
    ap.add_argument('--rate', type=float, default=5.0)
    ap.add_argument('--max-minutes', type=float, default=30)
    args = ap.parse_args()
    deadline = time.time() + args.max_minutes * 60
    inv = json.load(open(os.path.join(ROOT, 'data/troves/rockdrigo/latest.json')))
    held = {i[0]: i[2] for i in inv['items']}
    missing = {g for _, ings in inv['recipes'] for g, q in ings if held.get(g, 0) < q}
    places = {t[0]: t for t in json.load(open(os.path.join(ROOT, 'data/troves/places.json')))['troves']}
    wanted = {norm(s) for n in missing for s in places.get(n, [0, 0, []])[2]}
    ids = []
    cities = args.cities.split(',')
    if args.cities == 'all':   # cities with a special build first, then the biggest
        special = {str(x['city']) for x in json.load(open(os.path.join(ROOT, 'data/troves/city-specific.json')))['structures']}
        files = [f[:-5] for f in os.listdir(os.path.join(ROOT, 'data/troves/places')) if f.endswith('.json')]
        size = {c: len(json.load(open(os.path.join(ROOT, f'data/troves/places/{c}.json')))['props']) for c in files}
        cities = sorted(files, key=lambda c: (c not in special, -size[c]))
    for cid in cities:
        cd = json.load(open(os.path.join(ROOT, f'data/troves/places/{cid}.json')))
        sn = [norm(x) for x in cd['structs']]
        ids += [p[0] for p in cd['props'] if args.all or any(sn[i] in wanted for i in p[5])]
    for s in json.load(open(os.path.join(ROOT, 'data/troves/city-specific.json')))['structures']:
        ids += [p[0] for p in s['spots']]
    for cid in ([] if args.cities == 'all' else os.listdir(os.path.join(ROOT, 'data/troves/places'))):
        cd = json.load(open(os.path.join(ROOT, 'data/troves/places', cid)))
        if cd['name'] == 'Bermuda':
            sn = [norm(x) for x in cd['structs']]
            ids += [p[0] for p in cd['props'] if any(sn[i] in wanted for i in p[5])]
    out = load('troves/fees.json', {'fees': {}})
    todo = [i for i in dict.fromkeys(ids) if i not in out['fees']]
    log(f'{len(todo)} properties to read ({len(out["fees"])} already)')
    pacer = Pacer(1.0 / args.rate)

    def one(pid):
        if time.time() > deadline:
            return pid, None
        try:
            r = get_json(f'{API}/properties/{pid}', pacer)
        except Exception:
            return pid, None
        return pid, (r or {}).get('teleport_price')

    with cf.ThreadPoolExecutor(4) as ex:
        for n, (pid, fee) in enumerate(ex.map(one, todo), 1):
            if fee is not None:
                out['fees'][pid] = fee
            if n % 300 == 0:
                out['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                save('troves/fees.json', out)
                log(f'  {n} of {len(todo)}')
    out['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    save('troves/fees.json', out)
    log(f'done: {len(out["fees"])} fees')


if __name__ == '__main__':
    main()
