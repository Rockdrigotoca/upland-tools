#!/usr/bin/env python3
"""Record what one special-builds city gave, so the cities can be compared at the end.

  tools/city_result.py 125 --before b884e06 --after data/troves/rockdrigo/latest.json --find "Chickpea @ Ramen Restaurant, 7030 Oso Ave"

--before / --after are a balance file or a git revision of data/troves/rockdrigo/latest.json (after defaults to the file as it is now).
The difference is the net trove count gained, with the levels banked in between added back.
--together 138,32 stores the same result on each of those cities (two cities visited before one balance was taken).
--append adds a later visit to a city that already has a result.
--next ID marks the city to visit next. Results go to data/troves/special-results.json.
"""
import argparse
import json
import os
import subprocess
import time

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
    args = ap.parse_args()
    d = json.load(open(OUT)) if os.path.exists(OUT) else {'cities': {}}
    if args.city:
        ids = [int(x) for x in (args.together or args.city).split(',')]
        rec = {'status': 'done', 'date': args.date, 'note': args.note}
        if args.before:
            rec.update(diff(balance(args.before), balance(args.after)))
        if len(ids) > 1:
            rec['together'] = ids
        rec['finds'] = args.find
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
