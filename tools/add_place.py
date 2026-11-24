#!/usr/bin/env python3
"""Add (or refresh) one property in data/troves/places/<city id>.json from Upland's public property record.

  python3 tools/add_place.py <city id> <property id> [...]

The city files come from a one-off scan (LA: 2026-10-31), so a property that was built after it is missing. This reads the record
(address, position, finished service structures; homes are left out), puts the structure names the file does not know yet at the end of
`structs`, takes the neighbourhood of the nearest property already listed, and writes the row. Run tools/build_routes.py and
tools/build_craft_data.py afterwards.
"""
import json
import math
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    cid = sys.argv[1]
    path = os.path.join(ROOT, 'data', 'troves', 'places', cid + '.json')
    q = json.load(open(path))
    for pid in sys.argv[2:]:
        j = json.load(urllib.request.urlopen(urllib.request.Request('https://api.prod.upland.me/api/properties/' + pid, headers={'User-Agent': 'Mozilla/5.0 (upland-tools add_place)'}), timeout=30))
        lat, lng = round(float(j['centerlat']), 5), round(float(j['centerlng']), 5)
        names = sorted({b['buildingName'] for b in j.get('buildings') or [] if b.get('constructionStatus') == 'completed' and b.get('buildingType') != 'residential' and b.get('buildingName')})
        idx = []
        for n in names:
            if n not in q['structs']:
                q['structs'].append(n)
            idx.append(q['structs'].index(n))
        if not idx:
            print(pid, j['full_address'], '| no finished service structures yet, not added')
            continue
        near = min(q['props'], key=lambda p: math.hypot(p[2] - lat, (p[3] - lng) * math.cos(math.radians(lat))))
        addr = re.sub(r'\b(\w)(\w*)', lambda m: m.group(1).upper() + m.group(2).lower(), j['full_address'])
        row = [str(pid), addr, lat, lng, near[4], sorted(idx)]
        q['props'] = [p for p in q['props'] if str(p[0]) != str(pid)] + [row]
        print(addr, '|', len(idx), 'structures |', q['hoods'][near[4]], '| teleport', j.get('teleport_price'))
    json.dump(q, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
