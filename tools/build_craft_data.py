#!/usr/bin/env python3
"""The data Sir Quailbert's craft plan reads (published with the rest of data/helper/ on GitHub Pages).

  python3 tools/build_craft_data.py [session.json ...]

Writes
  data/helper/craft-data.json     every recipe version of every trove and the structures that craft it
  data/helper/craft/<city>.json   one file per city that has structure data: properties, their structure kinds and the fee

craft-data.json:  {format, updated, noSite: [troves with no known craft site],
                   troves: {name: [{ing: [[item, qty]...], at: [structure key...]}]}}
Structure keys are the normalised names (lower case, letters and digits only, a trailing " 1" dropped), the same on both sides.
A version whose structures are not known has an empty `at`. Where a structure is seen crafting a version (upxland's list, Upland's own
structure recipes, and any hunting-session exports passed as arguments) it is listed.

craft/<city>.json: {city, name, kinds: [structure key...], hoods: [...], props: [[property id, address, lat, lng, fee, hood, [kind index...]]]}
Properties in HOWARD BEACH (hard to find on the map) are left out; a fee that is not known is null.
"""
import collections
import glob
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'data', 'troves')
H = os.path.join(ROOT, 'data', 'helper')


def norm(s):
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip())


def key(ing):
    return tuple(sorted((x, q) for x, q in ing))


def main(sessions):
    master = json.load(open(os.path.join(H, 'master.json')))
    versions = collections.defaultdict(list)
    for name, ing in master['recipes']:
        k = key(ing)
        if k not in [key(v) for v in versions[name]]:
            versions[name].append(ing)
    sites = collections.defaultdict(dict)   # (trove, key) -> {structure key: source}
    for t, v in json.load(open(os.path.join(T, 'craft-sites.json')))['troves'].items():
        for ver in v['versions']:
            for a in ver['at']:
                sites[(t, key(ver['ing']))].setdefault(norm(a), 'upxland')
    for b, d in json.load(open(os.path.join(T, 'structure-recipes.json')))['structures'].items():
        for t, names in d.items():
            for v in versions.get(t, []):
                if sorted(x for x, _ in v) == sorted(names):
                    sites[(t, key(v))][norm(b)] = 'seen'
    # Crafts seen in hunting-session exports are kept in data/troves/craft-seen.json, so a run without the exports loses nothing
    seen_path = os.path.join(T, 'craft-seen.json')
    seen = json.load(open(seen_path)) if os.path.exists(seen_path) else {}   # {recipe: {ingredients key: [structure keys]}}
    for path in sessions:
        for c in json.load(open(path)).get('crafts', []):
            e = seen.setdefault(c['recipe'], {}).setdefault(json.dumps(sorted([x, q] for x, q in c['ingredients'])), [])
            if norm(c['building']) not in e:
                e.append(norm(c['building']))
    for recipe, d in seen.items():
        for ik, bs in d.items():
            for b in bs:
                sites[(recipe, key([tuple(x) for x in json.loads(ik)]))][b] = 'seen'
    json.dump({r: {k: sorted(v) for k, v in d.items()} for r, d in sorted(seen.items())}, open(seen_path, 'w'), separators=(',', ':'), sort_keys=True)
    # crafts the sources above do not show but Rockdrigo has done
    sites[('Chisel Set', key([('Iron Ore', 2), ('Twine', 1)]))].update({'art gallery': 'seen', 'art museum': 'seen'})
    sites[('Holiday Ham', key([('Pork', 5), ('Honey', 5), ('Hooray', 5)]))].update({'community center': 'seen'})
    NO_SITE = {'Golden Record', 'Invisible Cloak', 'Jade Dragon', 'Meteorite', 'Skeleton Key'}   # no structure is known to craft these
    troves = {}
    for name in sorted(versions):
        out = []
        for ing in versions[name]:
            at = sorted(sites.get((name, key(ing)), {}))
            if name == 'Compass' and any(x == 'Binoculars' for x, _ in ing):
                at = []
            out.append({'ing': [[x, q] for x, q in ing], 'at': at})
        troves[name] = out
    no_site = sorted(t for t in NO_SITE if t in troves) + sorted(t for t, v in troves.items() if t not in NO_SITE and not any(x['at'] for x in v))
    doc = {'format': 'quailbert-craft-data-v1', 'updated': time.strftime('%Y-%m-%d'), 'noSite': no_site, 'troves': troves}
    json.dump(doc, open(os.path.join(H, 'craft-data.json'), 'w'), separators=(',', ':'))
    print('craft-data.json: %d troves, %d with no known site, %d KB' % (len(troves), len(no_site), os.path.getsize(os.path.join(H, 'craft-data.json')) // 1024))

    fees = json.load(open(os.path.join(T, 'fees.json')))['fees']
    STAND = {a['pid']: a['use'] for a in json.load(open(os.path.join(T, 'avoid.json')))['avoid']}   # stand on the stand-in instead
    BAD = {('81313162700822', 'community center')}   # the property is listed with a Community Center that never showed one
    os.makedirs(os.path.join(H, 'craft'), exist_ok=True)
    for f in sorted(glob.glob(os.path.join(T, 'places', '*.json'))):
        q = json.load(open(f))
        city = os.path.splitext(os.path.basename(f))[0]
        kinds, kidx = [], {}
        for n in q['structs']:
            k = norm(n)
            if k not in kidx:
                kidx[k] = len(kinds)
                kinds.append(k)
        props = []
        for p in q['props']:
            if q['hoods'][p[4]] == 'HOWARD BEACH':
                continue
            ks = sorted({kidx[norm(q['structs'][i])] for i in p[5] if (str(p[0]), norm(q['structs'][i])) not in BAD})
            if not ks:
                continue
            fee = fees.get(str(p[0]))
            if str(p[0]) in STAND:
                u = STAND[str(p[0])]
                props.append([u['pid'], u['addr'], u['lat'], u['lng'], u['fee'], p[4], ks])
                continue
            props.append([str(p[0]), p[1], p[2], p[3], fee if isinstance(fee, (int, float)) else None, p[4], ks])
        if not props:
            continue
        out = {'city': int(city), 'name': q.get('name'), 'kinds': kinds, 'hoods': q['hoods'], 'props': props}
        path = os.path.join(H, 'craft', city + '.json')
        json.dump(out, open(path, 'w'), separators=(',', ':'), ensure_ascii=False)
        print('craft/%s.json: %s, %d properties, %d kinds, %d KB' % (city, q.get('name'), len(props), len(kinds), os.path.getsize(path) // 1024))


if __name__ == '__main__':
    main(sys.argv[1:])
