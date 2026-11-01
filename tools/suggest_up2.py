#!/usr/bin/env python3
"""Suggest the size (UP2) of structures the permits list gives no size for: the smallest property one is seen standing on.

A structure cannot stand on a property smaller than it needs, so the smallest `area` seen is an upper bound on the real minimum and
gets closer as more properties are read. For every service structure of the world scan without a size, this reads up to --samples
properties where it is built (spread over the cities it was found in), adds the properties already read for the players
(data/structures/players/), and writes the smallest area seen to data/structures/up2-suggestions.json. These are suggestions, not
facts: the Builder page marks them as such.
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import random
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAILS = '/Users/rock/Claude/Upland/Troves/city-scan/'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--samples', type=int, default=15)
    ap.add_argument('--rate', type=float, default=5.0)
    ap.add_argument('--max-minutes', type=float, default=45)
    args = ap.parse_args()
    deadline = time.time() + args.max_minutes * 60
    known = {norm(s['name']) for s in load('structures/master.json', {}).get('structures', []) if s.get('up2')}
    world = json.load(open(os.path.join(ROOT, 'data/troves/world.json')))['structures']
    todo = {k: e['name'] for k, e in world.items() if not e.get('living') and norm(e['name']) not in known}
    log(f'{len(todo)} structures without a size')
    seen = {}   # norm name -> {property id: area}
    for f in glob.glob(os.path.join(ROOT, 'data/structures/players/*.json')):
        for r in json.load(open(f)).get('rows', []):
            for b in r[6]:
                if r[3]:
                    seen.setdefault(norm(b), {})[r[0]] = r[3]
    cand = {}   # norm name -> property ids where it is built
    for f in sorted(glob.glob(DETAILS + '*properties.jsonl')):
        for line in open(f):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            for b in j['built']:
                if norm(b) in todo:
                    cand.setdefault(norm(b), []).append(j['id'])
    rnd = random.Random(7)
    want = {}
    for k in todo:
        have = seen.get(k, {})
        pool = [p for p in cand.get(k, []) if p not in have]
        rnd.shuffle(pool)
        want[k] = pool[:max(0, args.samples - len(have))]
    jobs = [(k, p) for k, ps in want.items() for p in ps]
    log(f'{len(jobs)} properties to read')
    pacer = Pacer(1.0 / args.rate)

    def one(job):
        if time.time() > deadline:
            return job, None
        try:
            r = get_json(f'{API}/properties/{job[1]}', pacer)
        except Exception:
            return job, None
        return job, (r or {}).get('area')

    with cf.ThreadPoolExecutor(4) as ex:
        for n, (job, area) in enumerate(ex.map(one, jobs), 1):
            if area:
                seen.setdefault(job[0], {})[job[1]] = area
            if n % 500 == 0:
                log(f'  {n} of {len(jobs)}')
    out = {}
    for k, name in todo.items():
        areas = seen.get(k)
        if areas:
            out[k] = {'name': name, 'min': min(areas.values()), 'samples': len(areas)}
    save('structures/up2-suggestions.json', {'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                             'note': 'Suggested minimum size (UP2): the smallest property each structure was seen on. Not confirmed.', 'structures': out})
    log(f'suggestions for {len(out)} of {len(todo)} structures')


if __name__ == '__main__':
    main()
