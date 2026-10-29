#!/usr/bin/env python3
"""Collect the cheapest properties for sale that would complete each collection.

For every collection that is tied to a neighborhood, a street or a whole city, this finds the cheapest
properties on Upland's public for-sale search (UPX and USD listings separately), confirms each
one really counts for that collection through the property's own collection list, and stores
the cheapest few. Confirmed eligibility is cached forever (it doesn't change), so each property
is checked once. Gentle by design: one request every couple of seconds, a time budget per run,
oldest collections refreshed first.
"""
import argparse
import json
import re
import sys
import os
import time
import urllib.parse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, save, log   # noqa: E402
from collect_collections import get, Limited  # noqa: E402

REFRESH_BOXES_DAYS = 30
EXTRA = 2          # keep this many spare candidates per collection, so overlaps can be resolved
MAX_PAGES = 3      # at most 3 pages of 20 cheapest listings per currency
SPECIAL = re.compile(r'same street|same city|different|any \d? ?property|a property in', re.I)
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())


def bbox(coords, box=None):
    """Grow [north, south, east, west] to include every [lng, lat] point in a (nested) coordinate list."""
    box = box or [-90, 90, -180, 180]
    if coords and isinstance(coords[0], (int, float)):
        lng, lat = coords[0], coords[1]
        box[0], box[1] = max(box[0], lat), min(box[1], lat)
        box[2], box[3] = max(box[2], lng), min(box[3], lng)
        return box
    for c in coords:
        bbox(c, box)
    return box


def merge(a, b):
    return [max(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), min(a[3], b[3])]


def load_boxes(pause):
    """Neighborhood and city boxes, refreshed monthly (the source is a ~13 MB download)."""
    st = load('buy/boxes.json', {})
    if st and time.time() - st.get('at', 0) < REFRESH_BOXES_DAYS * 86400:
        return st
    log('downloading neighborhood boundaries…')
    hoods = get('/neighborhood', pause)
    out = {'at': int(time.time()), 'hoods': {}, 'cities': {}}
    for h in hoods:
        if not (h.get('boundaries') or {}).get('coordinates'):
            continue
        b = bbox(h['boundaries']['coordinates'])
        k = f"{h['city_id']}|{norm(h['name'])}"
        out['hoods'][k] = merge(out['hoods'][k], b) if k in out['hoods'] else b
        cid = str(h['city_id'])
        out['cities'][cid] = merge(out['cities'][cid], b) if cid in out['cities'] else b
    save('buy/boxes.json', out)
    return out


def classify(c, boxes):
    """('hood'|'street', box, text) for collections we can price, else (None, reason)."""
    req = (c.get('requirements') or '')
    if SPECIAL.search(req):
        return None, 'special rule'
    hood = boxes['hoods'].get(f"{c['city_id']}|{norm(c['name'])}")
    if hood and 'neighborhood' in req.lower() or hood and not re.search(r'\bon [a-z]', req.lower()):
        return 'hood', hood, None
    m = re.search(r'\bon ([A-Za-z0-9 .\'-]+?)(?: in |\.|$)', req)
    city = boxes['cities'].get(str(c['city_id']))
    if m and city:
        street = re.sub(r'\.', '', c['name']).strip().upper()
        return 'street', city, street
    # "Own 3 properties in Amsterdam": the whole city, still confirmed property by property.
    if city and re.search(r'properties in ', req, re.I) and not re.search(r'neighborhood|county|district', req, re.I):
        return 'city', city, None
    return None, 'not tied to a neighborhood, street or city'


def list_view(box, currency, offset, pause, text=None):
    q = {'north': box[0], 'south': box[1], 'east': box[2], 'west': box[3], 'sort': 'asc', 'limit': 20, 'offset': offset, 'currency': currency}
    if text:
        q['text'] = text
    return get('/properties/list-view?' + urllib.parse.urlencode(q), pause) or {'properties': []}


def eligible(pid, cid, elig, pause):
    k = str(pid)
    if k not in elig:
        m = get(f'/properties/match/{pid}', pause)
        elig[k] = sorted({x['id'] for x in (m or [])})
    return cid in elig[k]


def price_collection(c, kind, box, text, elig, pause):
    need = c['amount'] + EXTRA
    out = {}
    for cur in ('USD', 'UPX'):
        picks, seen = [], set()
        for page in range(MAX_PAGES):
            rows = (list_view(box, cur, page * 20, pause, text).get('properties') or [])
            for r in rows:
                if r['prop_id'] in seen:
                    continue
                seen.add(r['prop_id'])
                if eligible(r['prop_id'], c['id'], elig, pause):
                    picks.append({'id': r['prop_id'], 'a': r['full_address'], 'cn': (r.get('city') or {}).get('name'),
                                  'p': r['price'], 'o': r.get('owner')})
                    if len(picks) >= need:
                        break
            if len(picks) >= need or len(rows) < 20:
                break
        out['usd' if cur == 'USD' else 'upx'] = picks
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', type=float, default=90)
    ap.add_argument('--pause', type=float, default=2.0)
    ap.add_argument('--max', type=int, default=0, help='stop after this many collections (0 = no limit)')
    ap.add_argument('--ids', default='', help='only these collection ids (comma separated)')
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60

    colls = get('/collections', args.pause)
    boxes = load_boxes(args.pause)
    sets = load('buy/sets.json', {})
    elig = load('buy/elig.json', {})
    only = {int(x) for x in args.ids.split(',') if x.strip()}

    plan, skipped = [], {}
    for c in colls:
        if only and c['id'] not in only:
            continue
        kind, *rest = classify(c, boxes)
        if kind is None:
            skipped[str(c['id'])] = rest[0]
        else:
            plan.append((c, kind, rest[0], rest[1]))
    # never-priced first, then the oldest; bigger rewards first inside each group
    plan.sort(key=lambda x: (sets.get(str(x[0]['id']), {}).get('at', 0), -(x[0].get('one_time_reward') or 0)))
    log(f'{len(plan)} collections can be priced, {len(skipped)} cannot; budget {args.minutes} min')

    done = 0
    try:
        for c, kind, box, text in plan:
            if time.time() > deadline or (args.max and done >= args.max):
                break
            r = price_collection(c, kind, box, text, elig, args.pause)
            sets[str(c['id'])] = {'at': int(time.time()), 'k': kind, **r}
            done += 1
            if done % 5 == 0:
                log(f'  {done} priced')
                save('buy/sets.json', sets)
                save('buy/elig.json', elig)
    except Limited as e:
        log(f'stopping early, Upland keeps refusing: {e}')
    except KeyboardInterrupt:
        log('stopped; saving')
    save('buy/sets.json', sets)
    save('buy/elig.json', elig)
    save('buy/state.json', {'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'priced': len(sets), 'priceable': len(plan),
                            'skipped': skipped})
    log(f'priced {done} this run; {len(sets)}/{len(plan)} total')


if __name__ == '__main__':
    main()
