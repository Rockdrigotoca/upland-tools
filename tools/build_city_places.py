#!/usr/bin/env python3
"""Turn a city's per-property scan file (one JSON line per property, kept outside the repository) into the compact file the Troves page
uses to point at real addresses: data/troves/places/<city id>.json.

Each property: [property id, address, latitude, longitude, neighbourhood number, [structure numbers]], only service structures that
are finished. Homes (living units) are left out. No owners anywhere.

    python3 tools/build_city_places.py 32 ~/Claude/Upland/Troves/city-scan/la-properties.jsonl
"""
import json
import sys

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from analyse_world import living_set, norm   # noqa: E402
from collect_prices import load, save        # noqa: E402


def main():
    cid, path = int(sys.argv[1]), sys.argv[2]
    living = living_set()
    name = (load(f'structures/world/{cid}.json', {}) or {}).get('name') or str(cid)
    hoods, structs, props = [], [], []
    hi, si = {}, {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            built = sorted({b for b in r['built'] if norm(b) not in living})
            if not built:
                continue
            h = r.get('hood') or ''
            hi.setdefault(h, len(hi)) if h not in hi else None
            if h not in hoods:
                hoods.append(h)
            ids = []
            for b in built:
                if b not in si:
                    si[b] = len(structs)
                    structs.append(b)
                ids.append(si[b])
            props.append([r['id'], (r.get('address') or '').title(), round(float(r['lat']), 5) if r.get('lat') else None,
                          round(float(r['lng']), 5) if r.get('lng') else None, hoods.index(h), ids])
    save(f'troves/places/{cid}.json', {'city': cid, 'name': name, 'hoods': hoods, 'structs': structs, 'props': props})
    print(f'{name}: {len(props)} properties with a service structure, {len(structs)} structure types, {len(hoods)} neighbourhoods')


if __name__ == '__main__':
    main()
