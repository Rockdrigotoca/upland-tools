#!/usr/bin/env python3
"""What each structure is worth for troves, for Sir Quailbert's Blueprint: data/structures/trove-value.json.

  {"troves": [names], "structures": {key: {"name", "h": hard troves found there, "b": troves only a bonus drop gives that it can drop,
                                           "f": every trove found there, "c": troves crafted there},
   "hard": how many of the first troves are hard or bonus-only}   (h, b and f index into troves; the hard and bonus-only ones come first)

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
        return out.setdefault(key(s), {'name': s, 'h': [], 'b': [], 'f': [], 'c': 0})

    for r in places['troves']:   # hard troves first, so their numbers stay low
        if r[0] in hard['troves']:
            for st in r[2]:
                entry(st)['h'].append(ti(r[0]))
    for trove, structs in hard['bonus'].items():
        for st in structs:
            entry(st)['b'].append(ti(trove))
    n_hard = len(names)
    for r in places['troves']:
        for st in r[2]:
            entry(st)['f'].append(ti(r[0]))
        for st in r[4]:
            entry(st)['c'] += 1
    for k, e in out.items():
        e['h'], e['b'], e['f'] = sorted(set(e['h'])), sorted(set(e['b'])), sorted(set(e['f']))
        if k in prints:
            e['name'] = prints[k]['name']
    save('structures/trove-value.json', {'updated': places.get('updated', ''), 'hard': n_hard, 'troves': names, 'structures': dict(sorted(out.items()))})
    lost = sorted(e['name'] for k, e in out.items() if k not in prints and (e['h'] or e['b']))
    print(f'{len(out)} structures, {n_hard} hard or bonus-only troves of {len(names)}; worth something but without a footprint: {len(lost)}', file=sys.stderr)
    print('  ' + ', '.join(lost), file=sys.stderr)


if __name__ == '__main__':
    main()
