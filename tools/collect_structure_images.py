#!/usr/bin/env python3
"""Small pictures of the structures, for the Troves page.

Upland's property record carries `buildingImage`, a path under https://static.upland.me/3d-models/ (a 700 KB picture). For every structure
that gives or crafts a trove (data/troves/places.json) this reads one property that carries it, downloads the picture once and keeps a
96 px copy in data/structures/images/, with data/structures/images.json mapping the structure name to the file. Resumable.

  python3 tools/collect_structure_images.py --max-minutes 20
"""
import argparse
import concurrent.futures as cf
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import HEADERS, load, log, save   # noqa: E402
from collect_structures import API, Pacer, get_json   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://static.upland.me/3d-models/'
OUT = os.path.join(ROOT, 'data', 'structures', 'images')


def norm(s):
    return re.sub(r' 1$', '', re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip())


def main():
    from PIL import Image
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--max-minutes', type=float, default=20)
    ap.add_argument('--rate', type=float, default=4.0)
    args = ap.parse_args()
    deadline = time.time() + args.max_minutes * 60
    places = json.load(open(os.path.join(ROOT, 'data/troves/places.json')))['troves']
    wanted = {norm(x): x for r in places for x in r[2] + r[4]}
    sample = {}   # normalised name -> (raw name, a property id that carries it)
    for fn in sorted(os.listdir(os.path.join(ROOT, 'data/troves/places'))):
        cd = json.load(open(os.path.join(ROOT, 'data/troves/places', fn)))
        sn = [norm(x) for x in cd['structs']]
        for p in cd['props']:
            for i in p[5]:
                if sn[i] in wanted and sn[i] not in sample:
                    sample[sn[i]] = (cd['structs'][i], str(p[0]))
    done = load('structures/images.json', {'format': 'upland-structure-images-v1', 'files': {}})
    os.makedirs(OUT, exist_ok=True)
    pacer = Pacer(1.0 / args.rate)
    todo = [(k, v) for k, v in sample.items() if wanted[k] not in done['files'] and v[0] not in done['files']]
    log(f'{len(todo)} structures to picture ({len(done["files"])} done)')
    def one(item):
        k, (raw, pid) = item
        if time.time() > deadline:
            return raw, None
        try:
            rec = get_json(f'{API}/properties/{pid}', pacer) or {}
            blds = (rec.get('buildings') or []) + ([rec['building']] if rec.get('building') else [])
            b = next((x for x in blds if norm(x.get('buildingName', '')) == k and x.get('buildingImage')), None)
            if not b:
                return raw, None
            req = urllib.request.Request(BASE + urllib.parse.quote(b['buildingImage'], safe='/'), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                img = Image.open(io.BytesIO(r.read())).convert('RGBA')
            img.thumbnail((96, 96))
            slug = re.sub(r'[^a-z0-9]+', '-', k).strip('-')[:80] + '.png'
            img.save(os.path.join(OUT, slug), optimize=True)
            return raw, slug
        except Exception as e:
            log(f'  {raw}: {str(e)[:80]}')
            return raw, None

    with cf.ThreadPoolExecutor(6) as ex:
        for n, (raw, slug) in enumerate(ex.map(one, todo), 1):
            if slug:
                done['files'][raw] = slug
            if n % 25 == 0:
                save('structures/images.json', done)
                log(f'  {n} of {len(todo)}')
    save('structures/images.json', done)
    log(f'{len(done["files"])} pictures in all')


if __name__ == '__main__':
    main()
