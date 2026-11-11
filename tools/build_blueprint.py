#!/usr/bin/env python3
"""What each structure is worth for troves, for Sir Quailbert's Blueprint: data/structures/trove-value.json.

  {"troves": [names], "structures": {key: {"name", "h": hard troves found there, "b": troves only a bonus drop gives that it can drop,
                                           "n": troves found there in all, "c": troves crafted there}}}   (h and b index into troves)

A trove is hard when 12 places or fewer give it (data/helper/hard.json). Keys are the same as in data/structures/footprints.json.

  python3 tools/build_blueprint.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_map import key   # noqa: E402
from collect_prices import load, save   # noqa: E402


def main():
    places, hard = load('troves/places.json', {}), load('helper/hard.json', {})
    prints = load('structures/footprints.json', {}).get('structures', {})
    names, idx, out = [], {}, {}

    def ti(n):
        if n not in idx:
            idx[n] = len(names)
            names.append(n)
        return idx[n]

    def entry(s):
        return out.setdefault(key(s), {'name': s, 'h': [], 'b': [], 'n': 0, 'c': 0})

    for r in places['troves']:
        for s in r[2]:
            e = entry(s)
            e['n'] += 1
            if r[0] in hard['troves']:
                e['h'].append(ti(r[0]))
        for s in r[4]:
            entry(s)['c'] += 1
    for trove, structs in hard['bonus'].items():
        for s in structs:
            entry(s)['b'].append(ti(trove))
    for k, e in out.items():
        e['h'], e['b'] = sorted(set(e['h'])), sorted(set(e['b']))
        if k in prints:
            e['name'] = prints[k]['name']
    save('structures/trove-value.json', {'updated': places.get('updated', ''), 'troves': names, 'structures': dict(sorted(out.items()))})
    lost = sorted(e['name'] for k, e in out.items() if k not in prints and (e['h'] or e['b']))
    print(f'{len(out)} structures, {len(names)} hard or bonus-only troves; worth something but without a footprint: {len(lost)}', file=sys.stderr)
    print('  ' + ', '.join(lost), file=sys.stderr)


if __name__ == '__main__':
    main()
