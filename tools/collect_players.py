#!/usr/bin/env python3
"""What can each player build on the properties they own? One-off, resumable read of the Upland record of every property of a
few players: size in UP2 (the record's `area`), city, position, and the buildings on it (name, kind, state).

Writes data/structures/players/<user>.json as rows [property id, address, city, UP2, lat, lng, [built names], [under construction],
living unit?]. Public data only (what anyone sees on the map). Four workers, about five requests a second in all; progress is
saved after every batch so a later run carries on where this one stopped.
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json   # noqa: E402

BATCH = 200


def row(p):
    built, going, home = [], [], 0
    for b in p.get('buildings') or []:
        if b.get('buildingType') == 'residential':
            home = 1
        n = b.get('buildingName')
        if n and b.get('buildingType') != 'residential':
            (built if b.get('constructionStatus') == 'completed' else going).append(n)
    return [str(p['prop_id']), p.get('full_address'), (p.get('city') or {}).get('name'), p.get('area'),
            round(float(p['centerlat']), 5), round(float(p['centerlng']), 5), built, going, home]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--users', default='mstullis,rockdrigo,talljames,missmarlow,bielykvietok,wamawa')
    ap.add_argument('--minutes', type=float, default=120)
    ap.add_argument('--rate', type=float, default=5.0)
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60
    pacer = Pacer(1.0 / args.rate)
    for u in args.users.split(','):
        ids = load(f'collections/users/{u}.json', {}).get('props', [])
        f = f'structures/players/{u}.json'
        res = load(f, {'user': u, 'rows': [], 'next': 0})
        log(f'{u}: {len(ids)} properties, {res["next"]} already read')
        with cf.ThreadPoolExecutor(4) as ex:
            while res['next'] < len(ids) and time.time() < deadline:
                batch = ids[res['next']:res['next'] + BATCH]
                got = list(ex.map(lambda pid: get_json(f'{API}/properties/{pid}', pacer), batch))
                res['rows'] += [row(p) for p in got if p]
                res['next'] += len(batch)
                res['done'] = res['next'] >= len(ids)
                res['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                save(f, res)
                log(f'  {u}: {res["next"]} of {len(ids)}')
    log('done')


if __name__ == '__main__':
    main()
