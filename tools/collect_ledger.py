#!/usr/bin/env python3
"""Collect the group's UPX sales for Rockdrigo's Receipts.

Reads Upland's public chain history (the same stream the price collector reads), keeps every shop
sale where a group player was the seller, the buyer or the shop owner, for every kind of asset,
and stores them in data/ledger/YYYY-MM.json. It needs almost nothing from Upland's own API: one
lookup per player, once, to learn their chain account.

Each run adds the newest sales and goes a number of days further back, a day at a time, until it
reaches April 2025 (the oldest the chain server keeps). USD sales leave no price on the chain, so
they can't be tracked.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import chain_actions, iso, load, log, parse_ts, save, amount, HISTORY_FLOOR, OWNER_RE   # noqa: E402
from collect_collections import GROUP, get as upland_get   # noqa: E402

OWNED_RE = re.compile(r'is now the owner of the (.+?) NFT "(.*)" mint (\d+)\. NFT ID: (\d+)')
OWNS_RE = re.compile(r'owns the NFT "(.*?)"')
FIELDS = ['ts', 'trx', 'nft', 'kind', 'name', 'mint', 'price', 'fee', 'mfee', 'seller', 'buyer', 'shop', 'bundle']


def resolve_members(pause=2.0):
    """username → chain account, learned once from one of the player's properties (its owner field)."""
    members = load('ledger/members.json', {'users': {}})
    users = members.setdefault('users', {})
    for u in GROUP:
        if u in users:
            continue
        ids = (load(f'collections/users/{u}.json', {}) or {}).get('props') or []
        try:
            pid = ids[0] if ids else ((upland_get(f'/profile/{u}', pause) or {}).get('properties') or [{}])[0].get('property_id')
            d = upland_get(f'/properties/{pid}', pause) if pid else None
        except Exception as e:
            log(f'  {u}: could not resolve ({e})')
            continue
        if d and (d.get('owner_username') or '').lower() == u and d.get('owner'):
            users[u] = d['owner']
            log(f'  {u} → {d["owner"]}')
        else:
            log(f'  {u}: no account found yet')
    save('ledger/members.json', members)
    return users


def read_window(actions, tracked, names):
    """Sales in a window where a tracked account is the seller, buyer or shop owner, any asset type."""
    by_trx = {}
    for a in actions:
        by_trx.setdefault(a['trx_id'], []).append(a)
        memo = (a['act'].get('data') or {}).get('memo') or ''
        m = OWNER_RE.search(memo)
        if m:
            names[m.group(2)] = m.group(1)
    rows = []
    for trx, acts in by_trx.items():
        pay = next((a for a in acts if a['act']['name'] == 'n112'), None)
        if not pay:
            continue
        d = pay['act']['data']
        seller, buyer, shop = d.get('p25'), d.get('p14'), d.get('p135')
        if not ({seller, buyer, shop} & tracked):
            continue
        items = []
        for a in acts:
            if a['act']['name'] != 'transfernft':
                continue
            memo = (a['act']['data'] or {}).get('memo') or ''
            m = OWNED_RE.search(memo)
            if m:
                items.append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4))))
            else:
                o = OWNS_RE.search(memo)
                ids = a['act']['data'].get('dgood_ids') or [0]
                items.append(('Other', o.group(1) if o else '?', 0, int(ids[0])))
        if not items:
            continue
        ts = int(parse_ts(pay['@timestamp']).timestamp())
        n = len(items)
        for kind, name, mint, nft in items:   # a purchase of several NFTs shares the one payment equally
            rows.append([ts, trx[:16], nft, kind, name, mint, round(amount(d.get('p141')) / n, 2), round(amount(d.get('p142')) / n, 2),
                         round(amount(d.get('p143')) / n, 2), seller, buyer, shop, n])
    return rows


def store_rows(new):
    months = {}
    for r in new:
        months.setdefault(datetime.fromtimestamp(r[0], timezone.utc).strftime('%Y-%m'), []).append(r)
    added = 0
    for month, rows in months.items():
        path = f'ledger/{month}.json'
        old = load(path, {'rows': []})['rows']
        seen = {(r[1], r[2]) for r in old}
        fresh = [r for r in rows if (r[1], r[2]) not in seen]
        added += len(fresh)
        save(path, {'fields': FIELDS, 'rows': sorted(old + fresh, key=lambda r: r[0])})
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=float, default=10, help='older days to add this run')
    ap.add_argument('--minutes', type=float, default=25, help='time budget for the chain reads')
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60

    users = resolve_members()
    tracked = set(users.values())
    if not tracked:
        log('no player accounts known yet; nothing to track')
        return
    names = {k: v for k, v in load('ledger/names.json', {}).items()}
    state = load('ledger/state.json', {})
    end = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=3)
    to = parse_ts(state['to']) if state.get('to') else end
    frm = parse_ts(state['from']) if state.get('from') else end
    total = 0

    # newest sales since last run
    if to < end:
        rows = []
        day = to
        while day < end:
            nxt = min(day + timedelta(days=1), end)
            rows += read_window(chain_actions(day, nxt), tracked, names)
            day = nxt
        total += store_rows(rows)
        log(f'forward {iso(to)} → {iso(end)}: {len(rows)} sales')
        state['to'] = iso(end)
    state.setdefault('to', iso(end))

    # older history, a day at a time, newest first, until the budget or the floor is reached
    floor = HISTORY_FLOOR.replace(tzinfo=timezone.utc)
    stop = frm - timedelta(days=args.days)
    while frm > max(stop, floor) and time.time() < deadline:
        start = max(frm - timedelta(days=1), floor)
        rows = read_window(chain_actions(start, frm), tracked, names)
        total += store_rows(rows)
        frm = start
        state['from'] = iso(frm)
        save('ledger/state.json', state)
        log(f'  back to {iso(frm)}: {len(rows)} sales in that day')
    state.setdefault('from', iso(frm))

    used = set()
    for f in sorted(os.listdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'ledger'))):
        if re.fullmatch(r'\d{4}-\d{2}\.json', f):
            for r in load(f'ledger/{f}', {'rows': []})['rows']:
                used.update(x for x in r[9:12] if x)
    seed = load('accounts.json', {})   # names the price collector already learned
    save('ledger/names.json', {a: names.get(a) or seed.get(a) for a in sorted(used) if names.get(a) or seed.get(a)})
    state['updatedAt'] = iso(datetime.now(timezone.utc)) + 'Z'
    state['members'] = sorted(users)
    save('ledger/state.json', state)
    log(f'done: {total} new sales; history now reaches back to {state["from"]}')


if __name__ == '__main__':
    main()
