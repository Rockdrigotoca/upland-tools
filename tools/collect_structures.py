#!/usr/bin/env python3
"""Which structures does each neighbourhood have, and which are still missing?

1. Reads the master list of service structures (the community's permits Google Sheet, published as CSV): name, size,
   stake range, sparklet hours. Structures the sheet doesn't list (branded ones) come from data/structures/extra.json.
2. Reads the Upland record of every property of a neighbourhood (data/structures/hoods.json) and takes the name and
   state of its buildings. Four workers at a time, about five requests a second in all, with a longer wait whenever
   Upland pushes back.
3. Writes data/structures/master.json and data/structures/<hood>.json: what is built, what is under construction, what is
   missing (with its cost and the train tier it fits), and built names the master list doesn't know yet.

Only structure names and counts are written, never owners.
"""
import argparse
import concurrent.futures as cf
import csv
import io
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import HEADERS, load, log, save   # noqa: E402

API = 'https://api.prod.upland.me/api'
PERMITS = ('https://docs.google.com/spreadsheets/d/e/2PACX-1vQTR52CDCZl7ZgzJun5NwbIOUsrC2pwI1TC9D3wfV6cqJ9N1jt9flP0QzVMprBoh9Vqmj0RIz2BnP9b/'
           'pub?output=csv&gid=0')
# Train tiers by sparklet-hour cost (thousands), as the Nomentano sign-up sheet splits them.
TIERS = [(7200, 1), (16650, 3)]   # up to 7,200 -> 1 spark, up to 16,650 -> 3 spark, above -> 5 spark
# Names that differ between Upland and the permits sheet. Keys and values are already in normalised form.
ALIASES = {'court house': 'courthouse', 'movie theatre': 'movie theater', 'bowling': 'bowling alley',
           'performing arts center': 'performing arts', 'electronic store': 'electronics store', 'planitarium': 'planetarium',
           'auto repair': 'auto repair shop'}


def norm(name):
    """Lower case, no accents, no trailing ' 1' (Upland numbers some duplicates), aliases applied."""
    n = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode().lower().strip()
    n = re.sub(r'\s+', ' ', re.sub(r' 1$', '', n))
    return ALIASES.get(n, n)


def tier(sph):
    if sph is None:
        return None
    for limit, t in TIERS:
        if sph <= limit:
            return t
    return 5


class Pacer:
    """Keeps all workers together under a request rate: at least `interval` seconds between any two requests."""
    def __init__(self, interval):
        self.interval, self.lock, self.next = interval, threading.Lock(), 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            slot = max(now, self.next)
            self.next = slot + self.interval
        if slot > now:
            time.sleep(slot - now)


def get_json(url, pacer, attempts=6):
    for attempt in range(attempts):
        pacer.wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            wait = int(e.headers.get('Retry-After') or 30) + 2 if e.code == 429 else 4 * (attempt + 1)
            log(f'  {e.code} for {url[-40:]}; waiting {wait}s')
            time.sleep(wait)
        except Exception as e:
            log(f'  retry {attempt + 1} for {url[-40:]}: {e}')
            time.sleep(4 * (attempt + 1))
    raise RuntimeError('Upland keeps refusing: ' + url)


def master_list(pacer):
    """{normalised name: {name, sph, up2, min, max, released}} from the permits sheet, plus the extra structures."""
    out = {}
    try:
        req = urllib.request.Request(PERMITS, headers={'User-Agent': HEADERS.get('User-Agent', 'upland-tools')})
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = list(csv.reader(io.StringIO(r.read().decode('utf-8'))))
        num = lambda x: int(x.replace(',', '')) if x.replace(',', '').strip().isdigit() else None
        for row in rows:
            if len(row) > 22 and row[0].strip().isdigit():
                out[norm(row[1])] = {'name': row[1].strip().title(), 'sph': num(row[9]), 'up2': num(row[7]), 'min': num(row[10]),
                                     'max': num(row[11]), 'released': row[22].strip(), 'source': 'permits'}
        log(f'permits sheet: {len(out)} structures')
    except Exception as e:
        log(f'permits sheet not read ({e}); keeping the last master list')
        old = load('structures/master.json', {}).get('structures') or []
        out = {norm(s['name']): s for s in old if s.get('source') == 'permits'}
    for s in (load('structures/extra.json', {}).get('structures') or []):
        out.setdefault(norm(s['name']), {'name': s['name'], 'sph': s.get('sph'), 'source': 'extra', 'category': s.get('category')})
    for s in out.values():
        s['tier'] = tier(s.get('sph'))
    return out


def read_hood(key, hood, pacer, workers, deadline):
    """Counts of built and under-construction structures over every property of the neighbourhood."""
    built, building, vacant, read, failed = {}, {}, 0, 0, 0
    ids = hood['ids']

    def one(pid):
        if time.time() > deadline:
            return pid, 'late'
        try:
            return pid, get_json(f'{API}/properties/{pid}', pacer)
        except Exception as e:
            return pid, 'error'

    with cf.ThreadPoolExecutor(workers) as ex:
        for k, (pid, p) in enumerate(ex.map(one, ids), 1):
            if p in ('late', 'error', None):
                failed += 1
                continue
            read += 1
            bs = p.get('buildings') or []
            if not bs:
                vacant += 1
            for b in bs:
                name, status = b.get('buildingName'), b.get('constructionStatus')
                if not name:
                    continue
                bucket = built if status == 'completed' else building if status == 'processing' else None
                if bucket is not None:
                    bucket[name] = bucket.get(name, 0) + 1
            if k % 200 == 0:
                log(f'  {key}: {k} of {len(ids)}')
    return {'built': built, 'building': building, 'vacant': vacant, 'read': read, 'failed': failed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--rate', type=float, default=5.0, help='requests per second in all')
    ap.add_argument('--minutes', type=float, default=60)
    ap.add_argument('--hoods', default='', help='comma-separated keys from hoods.json (default: all)')
    ap.add_argument('--max', type=int, default=0, help='only read this many properties per neighbourhood (testing)')
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60
    pacer = Pacer(1.0 / args.rate)

    master = master_list(pacer)
    save('structures/master.json', {'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'tiers': {'1': '<= 7,200', '3': '<= 16,650', '5': 'above'},
                                    'structures': sorted(master.values(), key=lambda s: s['name'].lower())})
    hoods = load('structures/hoods.json', {}).get('hoods') or {}
    for key, hood in hoods.items():
        if args.hoods and key not in args.hoods.split(','):
            continue
        if args.max:
            hood = {**hood, 'ids': hood['ids'][:args.max]}
        log(f'{hood.get("name", key)}: reading {len(hood["ids"])} properties')
        r = read_hood(key, hood, pacer, args.workers, deadline)
        have = {}
        for src, label in ((r['built'], 'built'), (r['building'], 'building')):
            for name, n in src.items():
                have.setdefault(norm(name), {'name': name, 'built': 0, 'building': 0})[label] += n
        missing = [{'name': s['name'], 'sph': s.get('sph'), 'tier': s.get('tier'), 'up2': s.get('up2')} for k, s in master.items() if k not in have]
        missing.sort(key=lambda s: (s['tier'] or 9, -(s['sph'] or 0)))
        unknown = sorted(h['name'] for k, h in have.items() if k not in master)
        out = {'hood': key, 'name': hood.get('name', key), 'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'properties': len(hood['ids']),
               'read': r['read'], 'failed': r['failed'], 'vacant': r['vacant'], 'built': r['built'], 'building': r['building'],
               'missing': missing, 'unknown': unknown}
        if r['failed'] > len(hood['ids']) * 0.1:
            log(f'{key}: {r["failed"]} properties could not be read; keeping the previous file')
            continue
        save(f'structures/{key}.json', out)
        log(f'{key}: {r["read"]} read, {len(have)} structure types, {len(missing)} missing, {len(unknown)} names the list does not know')
    log('done')


if __name__ == '__main__':
    main()
