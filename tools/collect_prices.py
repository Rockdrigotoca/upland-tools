#!/usr/bin/env python3
"""Collect structure-ornament prices for Rockdrigo's Cheapskate.

Runs every 12 hours from GitHub Actions (or by hand). Each run:
  1. Reads new UPX shop sales from Upland's public chain history since the last run.
  2. Extends the sale history a few days further back, until it reaches April 2025.
  3. Takes a snapshot of every ornament listed in ornament and variety shops.
  4. Compares with the previous snapshot: a USD-listed ornament that disappeared and
     changed owner without a UPX payment is recorded as a USD sale at its last price.
  5. Writes small JSON files under data/ for the web page.

Only the Python standard library is used. Upland's routes are undocumented and may change.
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

API = 'https://api.prod.upland.me'
CHAIN = 'https://chain-history.upland.me'
HEADERS = {'User-Agent': 'upland-tools-collector/1.0 (+https://github.com/Rockdrigotoca/upland-tools)',
           'Accept': 'application/json'}
HISTORY_FLOOR = datetime(2025, 4, 28, tzinfo=timezone.utc)   # oldest data the chain server keeps
SHOP_TYPES = {'ORNAMENT_SHOP', 'VARIETY_SHOP'}
PAUSE = 0.2   # seconds between calls to Upland, to stay gentle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

OWNER_RE = re.compile(r'Upland user (\S+) with corresponding EOS account (\S+)')
ORNAMENT_RE = re.compile(r'is now the owner of the Structure Ornament NFT "(.*)" mint (\d+)\. NFT ID: (\d+)')


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def http_json(url, body=None, tries=4):
    for i in range(tries):
        try:
            headers = dict(HEADERS)
            if body is not None:
                headers['Content-Type'] = 'application/json'
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:  # network hiccups and rate limits: back off and retry
            if getattr(e, 'code', None) in (400, 403, 404):
                raise
            wait = 3 * (i + 1)
            log(f'  retry {i + 1} for {url[:90]} ({e}); waiting {wait}s')
            time.sleep(wait)
    raise RuntimeError(f'gave up on {url}')


def upland(path, body=None):
    time.sleep(PAUSE)
    return http_json(API + path, body)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def parse_ts(s):
    return datetime.fromisoformat(s.replace('Z', '')).replace(tzinfo=timezone.utc)


def load(name, default):
    try:
        with open(os.path.join(DATA, name)) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(name, obj):
    path = os.path.join(DATA, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


# ---------- chain history ----------

def chain_actions(start, end):
    """All shop-sale (n112) and NFT-transfer actions between start and end, oldest first."""
    out, seen, cur, skip = [], set(), iso(start), 0
    while True:
        url = (f'{CHAIN}/v2/history/get_actions?filter=playuplandme:n112,uplandnftact:transfernft'
               f'&after={cur}&before={iso(end)}&limit=1000&sort=asc&skip={skip}')
        page = http_json(url).get('actions', [])
        fresh = [a for a in page if a['global_sequence'] not in seen]
        for a in fresh:
            seen.add(a['global_sequence'])
        out.extend(fresh)
        if len(page) < 1000:
            return out
        last = page[-1]['@timestamp']
        if last[:19] == cur:          # a full page inside one second: page through it
            skip += 1000
        else:
            cur, skip = last[:19], 0
        time.sleep(0.3)


def amount(q):
    return float(q.split()[0]) if q else 0.0


def read_sales(actions, accounts):
    """Turn raw actions into ornament UPX sales, plus ornament ownership changes without a UPX payment."""
    by_trx = defaultdict(list)
    for a in actions:
        by_trx[a['trx_id']].append(a)
        memo = (a['act'].get('data') or {}).get('memo') or ''
        m = OWNER_RE.search(memo)
        if m:
            accounts[m.group(2)] = m.group(1)
    sales, lone = [], {}
    for trx, acts in by_trx.items():
        pay = next((a for a in acts if a['act']['name'] == 'n112'), None)
        for a in acts:
            if a['act']['name'] != 'transfernft':
                continue
            m = ORNAMENT_RE.search((a['act']['data'] or {}).get('memo') or '')
            if not m:
                continue
            name, mint, nft = m.group(1), int(m.group(2)), int(m.group(3))
            ts = int(parse_ts(a['@timestamp']).timestamp())
            if pay:
                d = pay['act']['data']
                sales.append({'ts': ts, 'nft': nft, 'memoName': name, 'mint': mint, 'cur': 'UPX',
                              'price': amount(d.get('p141')), 'fee': amount(d.get('p142')), 'mfee': amount(d.get('p143')),
                              'seller': d.get('p25'), 'buyer': d.get('p14'), 'shopOwner': d.get('p135'), 'shop': None, 'trx': trx})
            elif sum(1 for x in acts if x['act']['name'] == 'transfernft') == 1:
                lone[nft] = {'ts': ts, 'buyer': a['act']['data'].get('to'), 'trx': trx}
    return sales, lone


# ---------- designs (season, structure type, image) ----------

class Designs:
    """Maps sold or listed NFTs to a design key "Name | Structure type" with season and image.

    Most names are unique, so one lookup per name is enough. Rarity-prefixed names
    ("Uncanny Zombie") exist for several structure types, so those are looked up per NFT.
    """
    def __init__(self):
        self.designs = load('designs.json', {})
        self.by_name = load('name_keys.json', {})
        self.by_nft = {int(k): v for k, v in load('nft_keys.json', {}).items()}
        self.rarities = set(load('rarities.json', ['Uncanny']))
        self.seasons = {}

    def is_rare(self, name, rarity=None):
        return bool(rarity) or name.split(' ', 1)[0] in self.rarities

    def key(self, nft, name, rarity=None):
        rare = self.is_rare(name, rarity)
        if nft in self.by_nft:
            return self.by_nft[nft]
        if not rare and name in self.by_name:
            return self.by_name[name]
        try:
            md = upland(f'/nft/assets/decorations/nft-id/{nft}').get('metadata') or {}
        except Exception as e:
            log(f'  no design info for {name} ({nft}): {e}')
            return name
        if md.get('rarityLevel'):
            self.rarities.add(md['rarityLevel'])
            rare = True
        disp = md.get('displayName') or name
        k = f"{disp} | {md.get('subtitle')}"
        if k not in self.designs:
            d = md.get('decorationId')
            if d not in self.seasons:
                try:
                    self.seasons[d] = upland(f'/business/decorations/{d}/preview').get('seasonName')
                except Exception as e:
                    log(f'  no season for {disp}: {e}')
                    self.seasons[d] = None
            self.designs[k] = {'n': disp, 'd': d, 'ty': md.get('subtitle'), 's': self.seasons[d],
                               'img': md.get('image'), 'r': md.get('rarityLevel')}
            log(f'  new design: {k} · {self.seasons[d]}')
        if rare:
            self.by_nft[nft] = k
        else:
            self.by_name[name] = k
        return k

    def save(self):
        save('designs.json', self.designs)
        save('name_keys.json', self.by_name)
        save('nft_keys.json', {str(k): v for k, v in self.by_nft.items()})
        save('rarities.json', sorted(self.rarities))


# ---------- shops and listings ----------

def snapshot_listings(shops):
    pins = upland('/business/pins')
    targets = [p['options'] for p in pins
               if p.get('options', {}).get('key') == 'venture' and p['options'].get('type') in SHOP_TYPES]
    log(f'snapshot: {len(targets)} ornament and variety shops')
    rows = []
    for i, o in enumerate(targets):
        sid = int(o['shopId'])
        try:
            items = upland(f'/metaventures/secondary-shop/{sid}/items', b'{}')
        except Exception as e:
            log(f'  shop {sid}: {e}')
            continue
        orn = [x for x in items if x.get('nftCategory') == 'structornmt' and x.get('status') == 'ON_SALE']
        if orn and str(sid) not in shops:
            shops[str(sid)] = shop_info(sid, o)
        for x in orn:
            rows.append({'shop': sid, 'nft': x['dGoodId'], 'name': x.get('tokenDisplayName'), 'mint': x.get('mintNumber'),
                         'price': x.get('askingPrice'), 'total': round(x.get('totalPrice') or 0, 2), 'cur': x.get('currency'),
                         'sellerAcct': x.get('ownerId'), 'seller': x.get('ownerUserName'), 'exp': x.get('listingExpiresAt'),
                         'rarity': x.get('rarityLevel')})
        if (i + 1) % 200 == 0:
            log(f'  …{i + 1} shops read, {len(rows)} ornament listings so far')
    return rows


def shop_info(sid, pin):
    info = {'n': pin.get('pillButton', {}).get('name'), 't': pin.get('type')}
    try:
        s = upland(f'/metaventures/secondary-shop/{sid}')
        info.update({'n': s.get('name') or info['n'], 'o': s.get('ownerUsername'), 'oa': s.get('ownerId'), 'p': s.get('propertyId')})
        if s.get('propertyId'):
            p = upland(f"/api/properties/{s['propertyId']}")
            info.update({'a': p.get('full_address'), 'c': (p.get('city') or {}).get('name')})
    except Exception as e:
        log(f'  shop {sid} details: {e}')
    return info


# ---------- summaries ----------

def summarize(months, now):
    """Per-design sale stats for the page. Giveaway-priced sales (2 UPX or less) are left out of medians."""
    cut30, cut90 = now - 30 * 86400, now - 90 * 86400
    rows = defaultdict(list)
    for month_rows in months.values():
        for r in month_rows:
            rows[r[2]].append(r)
    out = {}
    for name, rs in rows.items():
        rs.sort(key=lambda r: r[0])
        upx = [r for r in rs if r[4] == 'UPX' and r[5] > 2]
        usd = [r for r in rs if r[4] == 'USD']
        def stats(lst, since):
            p = [r[5] for r in lst if r[0] >= since]
            return [len(p), round(statistics.median(p), 2), min(p), max(p)] if p else [0, None, None, None]
        low = [r[5] for r in upx if r[3] <= 10]
        rest = [r[5] for r in upx if r[3] > 10]
        out[name] = {
            'u30': stats(upx, cut30), 'u90': stats(upx, cut90), 'uAll': stats(upx, 0),
            'uLast': upx[-1][:6] if upx else None, 'dLast': usd[-1][:6] if usd else None, 'dCount': len(usd),
            'lowMint': round(statistics.median(low), 2) if low else None, 'otherMint': round(statistics.median(rest), 2) if rest else None,
            'junk': sum(1 for r in rs if r[4] == 'UPX' and r[5] <= 2)
        }
    return out


# ---------- main ----------

SALE_FIELDS = ['ts', 'nft', 'key', 'mint', 'cur', 'price', 'fee', 'merchantFee', 'seller', 'buyer', 'shopOwner', 'shop']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--backfill-days', type=float, default=4, help='how many older days of history to add this run')
    ap.add_argument('--first-days', type=float, default=1, help='on the very first run, how far back to start')
    ap.add_argument('--no-listings', action='store_true', help='skip the shop snapshot (for quick tests)')
    args = ap.parse_args()

    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    end = now_dt - timedelta(minutes=3)            # leave the newest blocks to settle
    state = load('state.json', {})
    designs = Designs()
    shops = load('shops.json', {})
    accounts = load('accounts.json', {})
    prev = load('listings.json', None)

    # 1) new sales since last run
    fwd_start = parse_ts(state['chainCursor']) if state.get('chainCursor') else end - timedelta(days=args.first_days)
    log(f'forward: {iso(fwd_start)} → {iso(end)}')
    fwd_actions = chain_actions(fwd_start, end)
    fwd_sales, lone = read_sales(fwd_actions, accounts)
    log(f'  {len(fwd_actions)} actions, {len(fwd_sales)} ornament UPX sales, {len(lone)} ornament transfers without UPX')

    # 2) older history, a few days per run
    back_sales = []
    back_end = parse_ts(state['backfillCursor']) if state.get('backfillCursor') else fwd_start
    if back_end > HISTORY_FLOOR and args.backfill_days > 0:
        back_start = max(HISTORY_FLOOR, back_end - timedelta(days=args.backfill_days))
        log(f'backfill: {iso(back_start)} → {iso(back_end)}')
        back_sales, _ = read_sales(chain_actions(back_start, back_end), accounts)
        log(f'  {len(back_sales)} older ornament UPX sales')
        state['backfillCursor'] = iso(back_start)

    # 3) shop snapshot
    listings = None
    if not args.no_listings:
        listings = snapshot_listings(shops)
        log(f'  {len(listings)} ornament listings in {len({r["shop"] for r in listings})} shops')

    # 4) match vanished listings with sales
    usd_sales = []
    if listings is not None and prev:
        now_ids = {r['nft'] for r in listings}
        last_seen = {r['nft']: r for r in prev.get('rows', [])}
        by_nft = {s['nft']: s for s in fwd_sales}
        for nft, r in last_seen.items():
            if nft in now_ids:
                continue
            if nft in by_nft:
                by_nft[nft]['shop'] = r['shop']           # UPX sale: now we know which shop it sold from
            elif nft in lone and r['cur'] == 'USD':
                l = lone[nft]
                usd_sales.append({'ts': l['ts'], 'nft': nft, 'memoName': r.get('key'), 'key': r.get('key'), 'mint': r['mint'], 'cur': 'USD',
                                  'price': r['total'], 'fee': None, 'mfee': None, 'seller': r['sellerAcct'],
                                  'buyer': l['buyer'], 'shopOwner': None, 'shop': r['shop'], 'trx': l['trx']})
        log(f'  {len(usd_sales)} USD sales inferred from vanished listings')
    for r in (listings or []):
        if r.get('sellerAcct') and r.get('seller'):
            accounts[r['sellerAcct']] = r['seller']
    for s in shops.values():
        if s.get('oa') and s.get('o'):
            accounts[s['oa']] = s['o']

    # 5) design (name + structure type) for every sale and listing
    for s in fwd_sales + back_sales + usd_sales:
        s['key'] = s.get('key') or designs.key(s['nft'], s['memoName'])
    for r in (listings or []):
        r['key'] = designs.key(r['nft'], r['name'], r.get('rarity'))

    # 6) write monthly sale files
    months = {}
    for f in sorted(os.listdir(os.path.join(DATA, 'sales'))) if os.path.isdir(os.path.join(DATA, 'sales')) else []:
        if f.endswith('.json'):
            months[f[:-5]] = load(os.path.join('sales', f), {'rows': []})['rows']
    known = {(r[1], r[0]) for rows in months.values() for r in rows}
    added = 0
    for s in fwd_sales + back_sales + usd_sales:
        key = (s['nft'], s['ts'])
        if key in known:
            continue
        known.add(key)
        row = [s['ts'], s['nft'], s['key'], s['mint'], s['cur'], s['price'], s['fee'], s['mfee'],
               accounts.get(s['seller'], s['seller']), accounts.get(s['buyer'], s['buyer']),
               accounts.get(s['shopOwner'], s['shopOwner']) if s['shopOwner'] else None, s['shop']]
        month = datetime.fromtimestamp(s['ts'], timezone.utc).strftime('%Y-%m')
        months.setdefault(month, []).append(row)
        added += 1
    for m, rows in months.items():
        rows.sort(key=lambda r: r[0])
        save(os.path.join('sales', f'{m}.json'), {'fields': SALE_FIELDS, 'rows': rows})
    log(f'sales: {added} new rows across {len(months)} months')

    # 7) listings, summaries, state
    if listings is not None:
        fields = ['shop', 'nft', 'key', 'mint', 'price', 'total', 'cur', 'seller', 'exp']
        save('listings.json', {'at': iso(now_dt) + 'Z', 'fields': fields,
                               'rows': [{k: r[k] for k in fields} | {'sellerAcct': r['sellerAcct']} for r in listings]})
        state['lastSnapshotAt'] = iso(now_dt)
    save('summary.json', summarize(months, int(now_dt.timestamp())))
    designs.save()
    save('shops.json', shops)
    used = {a for rows in months.values() for r in rows for a in (r[8], r[9], r[10]) if a}
    save('accounts.json', {k: v for k, v in accounts.items() if k in used or v in used})
    state['chainCursor'] = iso(end)
    state['updatedAt'] = iso(now_dt) + 'Z'
    state['historyFrom'] = state.get('backfillCursor')
    state['months'] = sorted(months)
    save('state.json', state)
    log('done')


if __name__ == '__main__':
    main()
