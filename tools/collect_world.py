#!/usr/bin/env python3
"""Which structures does each Upland city have? A resumable scan, city by city, that only reads properties with a service structure.

1. Lists the neighbourhoods of the city (Upland's /neighborhood boundaries) and, for each one, asks the map which properties lie
   inside it and carry a service building (a house is "residential"; a shop, a bank or a bus stop is not). That is one request per
   neighbourhood, and it leaves only a few percent of the properties (Los Angeles: 6,611 of 475,235).
   The result is kept in data/structures/world/ids/<city id>.json, so it is done once.
2. Reads the Upland record of those properties, four workers at a time, about five requests a second, and counts the buildings by
   name: built, and under construction, for the city and for each neighbourhood. Progress is saved after every batch, so a run can
   be stopped and the next one carries on where it stopped. Output: data/structures/world/<city id>.json.

Only structure names and counts are written to data/. With --details FILE, one line per property (address, neighbourhood, buildings)
goes to a file of your choice outside the repository, for planning a trip.
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import HEADERS, load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json    # noqa: E402

CACHE = os.environ.get('UPLAND_CACHE') or os.path.join(os.path.expanduser('~'), '.cache', 'upland-tools')
IDS_MAX_AGE = 30 * 86400
BATCH = 200


def hoods_of_city(city_id):
    """The neighbourhoods of one city, with their boundaries. The full list is a ~13 MB download, kept for a day."""
    path = os.path.join(CACHE, 'neighborhoods.json')
    if not (os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400):
        log('downloading the neighbourhood boundaries...')
        req = urllib.request.Request(API + '/neighborhood', headers=HEADERS)
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
        os.makedirs(CACHE, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
    with open(path) as f:
        return [h for h in json.load(f) if h['city_id'] == city_id and (h.get('boundaries') or {}).get('coordinates')]


def polygons(h):
    b = h['boundaries']
    return [b['coordinates']] if b['type'] == 'Polygon' else b['coordinates']


def inside(x, y, polys):
    for rings in polys:
        ring, hit = rings[0], False
        for i in range(len(ring)):
            (x1, y1), (x2, y2) = ring[i - 1][:2], ring[i][:2]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
        if hit:
            return True
    return False


def has_service(models):
    return any(m.get('modelType') == 'building' and m.get('subType') != 'residential' for m in models or [])


def list_ids(city_id, name, args, pacer):
    """[[property id, neighbourhood id], ...] of the properties of the city that carry a service building."""
    f = f'structures/world/ids/{city_id}.json'
    old = load(f, {})
    if old.get('ids') and time.time() - old.get('at', 0) < IDS_MAX_AGE and not args.refresh:
        return old
    hoods = sorted(hoods_of_city(city_id), key=lambda h: h['id'])
    if args.max_hoods:
        hoods = hoods[:args.max_hoods]
    seen, out, names = set(), [], {}
    for k, h in enumerate(hoods, 1):
        ps = polygons(h)
        pts = [p[:2] for rings in ps for p in rings[0]]
        url = (f"{API}/map?north={max(p[1] for p in pts)}&south={min(p[1] for p in pts)}"
               f"&east={max(p[0] for p in pts)}&west={min(p[0] for p in pts)}")
        rows = get_json(url, pacer) or []
        names[str(h['id'])] = h['name']
        for r in rows:
            pid = str(r['prop_id'])
            if pid not in seen and has_service(r.get('models')) and inside(float(r['centerlng']), float(r['centerlat']), ps):
                seen.add(pid)
                out.append([pid, h['id']])
        log(f'  {name}: neighbourhood {k} of {len(hoods)} ({h["name"]}): {len(out)} properties with a service structure so far')
    res = {'city_id': city_id, 'name': name, 'at': int(time.time()), 'hoods': names, 'ids': out}
    if not args.max_hoods:
        save(f, res)
    return res


def read_city(city_id, name, listing, args, pacer, deadline):
    f = f'structures/world/{city_id}.json'
    res = load(f, {}) if not args.restart else {}
    res = {'city_id': city_id, 'name': name, 'hoods': listing.get('hoods', {}), 'next': res.get('next', 0), 'read': res.get('read', 0),
           'failed': res.get('failed', 0), 'built': res.get('built', {}), 'building': res.get('building', {}), 'byHood': res.get('byHood', {})}
    ids = listing['ids']
    if args.max:
        ids = ids[:args.max]
    details = open(args.details, 'a') if args.details else None

    def one(item):
        pid, hid = item
        if time.time() > deadline:
            return item, 'late'
        try:
            return item, get_json(f'{API}/properties/{pid}', pacer)
        except Exception:
            return item, 'error'

    with cf.ThreadPoolExecutor(args.workers) as ex:
        while res['next'] < len(ids) and time.time() < deadline:
            batch = ids[res['next']:res['next'] + BATCH]
            results = list(ex.map(one, batch))
            if any(p == 'late' for _, p in results):   # out of time: keep only the part of the batch that was read, in order
                cut = next(i for i, (_, p) in enumerate(results) if p == 'late')
                results = results[:cut]
            for (pid, hid), p in results:
                if p in ('error', None):
                    res['failed'] += 1
                    continue
                res['read'] += 1
                if (p.get('city') or {}).get('name') and not args.name:
                    res['name'] = p['city']['name']   # the city's own name, from the first record that has it
                built, building = [], []
                for b in p.get('buildings') or []:
                    n, st = b.get('buildingName'), b.get('constructionStatus')
                    if not n:
                        continue
                    if st == 'completed':
                        built.append(n)
                    elif st == 'processing':
                        building.append(n)
                for n in built:
                    res['built'][n] = res['built'].get(n, 0) + 1
                    h = res['byHood'].setdefault(str(hid), {})
                    h[n] = h.get(n, 0) + 1
                for n in building:
                    res['building'][n] = res['building'].get(n, 0) + 1
                if details:
                    details.write(json.dumps({'id': pid, 'hood': res['hoods'].get(str(hid)), 'address': p.get('full_address'),
                                              'lat': p.get('centerlat'), 'lng': p.get('centerlng'), 'built': built, 'building': building}) + '\n')
            res['next'] += len(results)
            res['total'] = len(ids)
            res['done'] = res['next'] >= len(ids)
            res['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            if not args.max:
                save(f, res)
            if details:
                details.flush()
            log(f'  {name}: {res["next"]} of {len(ids)} read ({res["failed"]} failed), {len(res["built"])} structure types')
    if details:
        details.close()
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--city', required=True, help='city id (Los Angeles is 32); comma-separated for several')
    ap.add_argument('--name', default='', help='name to store with the city (one city only)')
    ap.add_argument('--minutes', type=float, default=60, help='stop reading after this long; the next run resumes')
    ap.add_argument('--rate', type=float, default=5.0, help='property reads per second in all')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--refresh', action='store_true', help='list the properties of the city again')
    ap.add_argument('--restart', action='store_true', help='forget the progress and read the city from the start')
    ap.add_argument('--details', help='append one line per property read to this file (keep it out of the repository)')
    ap.add_argument('--max-hoods', type=int, default=0, help='testing: only list this many neighbourhoods, writes nothing')
    ap.add_argument('--max', type=int, default=0, help='testing: only read this many properties, writes nothing')
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60
    map_pacer, read_pacer = Pacer(1.0), Pacer(1.0 / args.rate)
    for cid in [int(x) for x in args.city.split(',')]:
        name = args.name or str(cid)
        listing = list_ids(cid, name, args, map_pacer)
        log(f'{name}: {len(listing["ids"])} properties with a service structure')
        r = read_city(cid, name, listing, args, read_pacer, deadline)
        log(f'{name}: {r["next"]} of {len(listing["ids"][:args.max] if args.max else listing["ids"])} read')
    log('done')


if __name__ == '__main__':
    main()
