#!/usr/bin/env python3
"""Record what one special-builds city gave, so the cities can be compared at the end.

  tools/city_result.py 125 --before b884e06 --after data/troves/rockdrigo/latest.json --find "Chickpea @ Ramen Restaurant, 7030 Oso Ave"

--before / --after are a balance file or a git revision of data/troves/rockdrigo/latest.json (after defaults to the file as it is now).
The difference is the net trove count gained, with the levels banked in between added back.
--together 138,32 stores the same result on each of those cities (two cities visited before one balance was taken).
--append adds a later visit to a city that already has a result.
--next ID marks the city to visit next. Results go to data/troves/special-results.json.

From the hunting log instead of two balances (data/troves/rockdrigo/hunts.json, see tools/hunts.py):
  tools/city_result.py 125 --hunts --since 2026-11-01T13:00 --until 2026-11-01T15:00 --note "..." --next 122
Everything the log holds for that city inside the window becomes the result: troves, types, categories, the most found, the troves seen
for the first time in the log, how many properties and minutes it took, and every rarely seen trove with where it came from.
Add --dry to print the result without writing it.
"""
import argparse
import json
import os
import subprocess
import re
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAL = 'data/troves/rockdrigo/latest.json'
OUT = os.path.join(ROOT, 'data', 'troves', 'special-results.json')


def balance(ref):
    if ref and os.path.exists(ref):
        return json.load(open(ref))
    return json.loads(subprocess.check_output(['git', 'show', f'{ref or "HEAD"}:{BAL}'], cwd=ROOT))


def diff(a, b):
    x = {i[0]: i for i in a['items']}
    gain, types, cat, tops, new = 0, 0, {}, [], []
    for i in b['items']:
        p = x.get(i[0])
        if not p:
            new.append(i[0])
            continue
        d = i[2] - p[2] + sum(p[4][p[3]:i[3]])   # levels banked in between used troves up: add them back
        if d > 0:
            gain += d
            types += 1
            cat[i[1]] = cat.get(i[1], 0) + d
            tops.append([i[0], d])
    tops.sort(key=lambda t: -t[1])
    return {'gain': gain, 'types': types, 'byCat': cat, 'top': tops[:8], 'new': new, 'found': [a['troves']['found'], b['troves']['found']]}


def local(s):
    return int(datetime.fromisoformat(s).timestamp()) if s else None


def from_hunts(cid, since, until):
    hunts = json.load(open(os.path.join(ROOT, 'data', 'troves', 'rockdrigo', 'hunts.json')))
    name = json.load(open(os.path.join(ROOT, 'data', 'troves', 'city-specific.json')))['cities'][str(cid)]['name']
    cat = {r[0]: r[1] for r in json.load(open(os.path.join(ROOT, 'data', 'troves', 'places.json')))['troves']}
    t0, t1 = local(since) or 0, local(until) or 10 ** 12
    total, first = {}, {}
    rows = []
    for at, kind, si, ti, q, pi, inst in hunts['finds']:
        tr = hunts['troves'][ti]
        total[tr] = total.get(tr, 0) + q
        first.setdefault(tr, at)
        if hunts['cities'][hunts['props'][pi][2]] == name and t0 <= at <= t1 and hunts['src'][si][1] != 'balloon':
            rows.append((at, kind, hunts['src'][si][0], tr, q, hunts['props'][pi]))
    if not rows:
        raise SystemExit(f'No finds for {name} in that window.')
    qty = {}
    for r in rows:
        qty[r[3]] = qty.get(r[3], 0) + r[4]
    bycat, src = {}, {}
    for r in rows:
        bycat[cat.get(r[3], 'junk')] = bycat.get(cat.get(r[3], 'junk'), 0) + r[4]
        src[r[2]] = src.get(r[2], 0) + 1
    rare, seen = [], set()
    for at, kind, source, tr, q, prop in rows:
        if (total[tr] <= 3 or (since and t0 <= first[tr] <= t1)) and tr not in seen:
            seen.add(tr)
            addr = re.sub(r'(\d)(St|Nd|Rd|Th)\b', lambda m: m.group(1) + m.group(2).lower(), prop[1].split(',')[0].title())
            rare.append(f'{tr} @ {source}, {addr}')
    # minutes: a break of 20 minutes or more ends a session
    mins, start, last = 0, rows[0][0], rows[0][0]
    for r in rows[1:]:
        if r[0] - last > 1200:
            mins += max(last - start, 60); start = r[0]
        last = r[0]
    mins += max(last - start, 60)
    return {'gain': sum(qty.values()), 'types': len(qty), 'byCat': bycat, 'top': sorted(([k, v] for k, v in qty.items()), key=lambda x: -x[1])[:8],
            'new': sorted(k for k in qty if since and t0 <= first[k] <= t1),
            'n': len(rows), 'props': len({r[5][0] for r in rows}), 'minutes': round(mins / 60), 'bySource': sorted(src.items(), key=lambda x: -x[1])[:6],
            'seenFirst': rare}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('city', nargs='?', help='city id')
    ap.add_argument('--before')
    ap.add_argument('--after', default=os.path.join(ROOT, BAL))
    ap.add_argument('--together', help='comma-separated city ids that share this result')
    ap.add_argument('--find', action='append', default=[], help='"Trove @ where", repeatable')
    ap.add_argument('--note', default='')
    ap.add_argument('--date', default=time.strftime('%Y-%m-%d'))
    ap.add_argument('--append', action='store_true', help='another visit to a city that already has a result: keep the first and add this one')
    ap.add_argument('--next', type=int, help='city id to visit next')
    ap.add_argument('--hunts', action='store_true', help='read the result from the hunting log instead of two balances')
    ap.add_argument('--since', help='with --hunts: start of the window, local time, e.g. 2026-11-01T13:00')
    ap.add_argument('--until', help='with --hunts: end of the window')
    ap.add_argument('--dry', action='store_true', help='print the result and write nothing')
    args = ap.parse_args()
    d = json.load(open(OUT)) if os.path.exists(OUT) else {'cities': {}}
    if args.city:
        ids = [int(x) for x in (args.together or args.city).split(',')]
        rec = {'status': 'done', 'date': args.date, 'note': args.note}
        if args.hunts:
            rec.update(from_hunts(ids[0], args.since, args.until))
            rec['finds'] = args.find or rec.pop('seenFirst')
            if args.dry:
                print(json.dumps(rec, ensure_ascii=False, indent=1)); return
        elif args.before:
            rec.update(diff(balance(args.before), balance(args.after)))
        if len(ids) > 1:
            rec['together'] = ids
        rec['finds'] = rec.get('finds') if args.hunts else args.find
        for cid in ids:
            old = d['cities'].get(str(cid), {})
            if args.append and old:
                old.setdefault('more', []).append(rec)
            else:
                d['cities'][str(cid)] = {**old, **rec, 'finds': args.find or old.get('finds', [])}
    if args.next:
        d['next'] = args.next
    d['updatedAt'] = time.strftime('%Y-%m-%d')
    json.dump(d, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(d, ensure_ascii=False)[:1800])


if __name__ == '__main__':
    main()
