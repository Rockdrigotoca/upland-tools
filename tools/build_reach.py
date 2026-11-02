#!/usr/bin/env python3
"""The cheapest place to stand for every costly structure property, from what tools/collect_reach.py has read so far.

For each structure property whose teleport price is at least the scanner's --min-fee, look at every property priced within 80 m and within
100 m (the neighbours read by the scanner, and the other structure properties) and keep the cheapest one that costs less, the closer one on
a tie. Writes data/troves/reach-best.json:
  {"updatedAt", "minFee", "best80": {property id: [cheaper property id, its price, metres]}, "best100": {...}}
Only costly properties with a cheaper neighbour appear. Safe to run while the scanner is half way: it uses what is there.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M_LAT = 111320.0
CELL = 0.0012   # degrees, a little more than 100 m


def main():
    fees = load('troves/fees.json', {'fees': {}})['fees']
    best = {80: {}, 100: {}}
    min_fee = 50
    saved = 0
    for fn in sorted(os.listdir(os.path.join(ROOT, 'data/troves/reach'))) if os.path.isdir(os.path.join(ROOT, 'data/troves/reach')) else []:
        if not fn.endswith('.json'):
            continue
        r = json.load(open(os.path.join(ROOT, 'data/troves/reach', fn)))
        min_fee = r.get('minFee', min_fee)
        cd = json.load(open(os.path.join(ROOT, 'data/troves/places', fn)))
        pts = [(str(p[0]), float(p[2]), float(p[3]), fees[str(p[0])]) for p in cd['props'] if str(p[0]) in fees]
        pts += [(x[0], x[1], x[2], x[4]) for x in r.get('rows', []) if x[4] is not None and x[4] >= 0]
        grid = {}
        for p in pts:
            grid.setdefault((math.floor(p[1] / CELL), math.floor(p[2] / CELL)), []).append(p)
        for pid, lat, lng, fee in pts:
            if fee < r.get('minFee', 50) or pid not in fees:
                continue
            cy, cx = math.floor(lat / CELL), math.floor(lng / CELL)
            c = math.cos(math.radians(lat))
            for reach in (80, 100):
                pick = None
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        for q, la, lo, f in grid.get((cy + a, cx + b), ()):
                            if q == pid or f >= fee:
                                continue
                            m = math.hypot((la - lat) * M_LAT, (lo - lng) * M_LAT * c)
                            if m <= reach and (pick is None or (f, m) < (pick[1], pick[2])):
                                pick = [q, f, round(m)]
                if pick:
                    best[reach][pid] = pick
    save('troves/reach-best.json', {'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'minFee': min_fee, 'best80': best[80], 'best100': best[100]})
    s80 = sum(fees[k] - v[1] for k, v in best[80].items())
    log(f'{len(best[80])} costly properties have a cheaper one within 80 m (saving {s80} UPX in all), {len(best[100])} within 100 m')


if __name__ == '__main__':
    main()
