#!/usr/bin/env python3
"""Rockdrigo's Troves: turn the HAR you saved from your Upland Troves page into a small, safe file to upload.

A HAR is a recording of everything your browser sent and received, including your login token. This script reads it on your
own computer, keeps ONLY your trove inventory and recipes (names and numbers), and writes a small file with no headers, no
cookies and no token. It refuses to write anything if it finds something that looks like a token.

    python3 clean_har.py                    # reads trove_balance.har in the same folder as this script
    python3 clean_har.py ~/Downloads/x.har  # any other HAR
    python3 clean_har.py --list x.har       # only show which JSON responses the HAR holds

Writes trove_balance-YYYY-MM-DD.json next to the HAR. Then it deletes the HAR, because that is the file that holds your
token (use --keep-har to keep it). The HAR is only deleted when your trove inventory was found in it.

Upload the .json on the Troves page: https://rockdrigotoca.github.io/upland-tools/troves/
Needs only Python 3. Nothing is sent anywhere.
"""
import argparse
import json
import os
import re
import sys
import time

FORMAT = 'upland-troves-v1'
# A JWT (eyJ...), a "Bearer ..." value, or a key that says token/secret/authorization/cookie followed by a long value.
TOKEN = re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}|[Bb]earer\s+[A-Za-z0-9._~+/=-]{20,}'
                   r'|"(?:access_?token|refresh_?token|id_?token|authorization|cookie|set-cookie|secret|password)"\s*:\s*"[^"]{12,}"', re.I)


def bodies(path):
    """Every JSON response body of a HAR (or of the older 'responses' file this script used to write)."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if 'log' in data:
        for e in data['log']['entries']:
            c = e['response'].get('content') or {}
            if c.get('text'):
                try:
                    yield e['request']['url'].split('?')[0], json.loads(c['text'])
                except ValueError:
                    pass
    else:
        for r in data.get('responses', []):
            yield r.get('url', ''), r.get('body')


def slim(balance, stamina, date):
    """Only what the Troves page needs: [name, category, held, banked level, [3 banking costs]] and [recipe, [[ingredient, needed]]]."""
    items = [[i['name'], c['name'], i['quantity'], i.get('bankedLevel') or 0, [l['requiredTrovesCount'] for l in i.get('bankingLevels') or []]]
             for c in balance['categories'] for i in c['items']]
    recipes = [[r['name'], [[g['name'], g['required']] for g in r['ingredients'] if g.get('assetType', 'trove') == 'trove']] for r in balance['discoveredRecipes']]
    out = {'format': FORMAT, 'date': date, 'troves': {'found': balance.get('totalCount'), 'max': balance.get('maxCount')}, 'items': items, 'recipes': recipes}
    if isinstance(stamina, dict) and 'current' in stamina:
        out['stamina'] = {'current': stamina['current'], 'max': stamina.get('max')}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('har', nargs='?', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trove_balance.har'))
    ap.add_argument('--list', action='store_true', help='only list the JSON responses in the file; writes nothing')
    ap.add_argument('-o', '--out', help='output file (default: <har name>-YYYY-MM-DD.json next to it)')
    ap.add_argument('--keep-har', action='store_true', help='do not delete the original HAR afterwards')
    args = ap.parse_args()

    if not os.path.exists(args.har):
        sys.exit(f'File not found: {args.har}')
    if args.list:
        for url, body in bodies(args.har):
            print(f'{len(json.dumps(body)):>9}  {url}')
        return

    balance = stamina = None
    for url, body in bodies(args.har):
        if isinstance(body, dict) and 'discoveredRecipes' in body and 'categories' in body:
            balance = body
        elif url.endswith('/stamina/total'):
            stamina = body
    if balance is None:
        sys.exit('Your trove inventory is not in this file, so nothing was written (and nothing deleted).\n'
                 'Open your Troves page with the browser tools on the Network tab, reload, then save the HAR again.')

    date = time.strftime('%Y-%m-%d')
    out = slim(balance, stamina, date)
    text = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    hit = TOKEN.search(text)
    if hit:
        sys.exit(f'Something that looks like a login token is in the result ({hit.group(0)[:10]}...): nothing written.')

    path = args.out or re.sub(r'\.(har|json)$', '', args.har) + '-' + date + '.json'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'{len(out["items"])} troves and {len(out["recipes"])} recipes, {len(text) / 1024:.0f} KB, no headers, cookies or token -> {path}')
    if args.keep_har:
        print('Original file kept. If it is a HAR it still holds your token: delete it when you are done.')
    elif args.har.endswith('.har'):
        os.remove(args.har)
        print('Original HAR deleted.')


if __name__ == '__main__':
    main()
