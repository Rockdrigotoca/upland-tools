#!/usr/bin/env python3
"""Collect collection data for Rockdrigo's Freeloader.

For a fixed group of players, reads each profile (properties, active and collected
collections) and, for every property, its monthly base yield, city, street and the
collections it can join. Property details are cached in data/collections/props.json and
refreshed after 30 days, so each run only reads new or stale properties, up to a time
budget, slowly and gently. There's no rush: the first catch-up of the whole group is spread
over about a week of 12-hourly runs, and after that each run only reads new or stale properties.
"""
import argparse
import signal
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import HEADERS, load, save, log   # noqa: E402

API = 'https://api.prod.upland.me/api'
# Collected in this order: Rockdrigo first, then mstullis, missmarlow, talljames, bielykvietok, leflof2p and maikn1 last.
GROUP = ['rockdrigo', 'mstullis', 'missmarlow', 'talljames', 'bielykvietok', 'leflof2p', 'maikn1', 'rjonk', 'wamawa']
REFRESH_DAYS = 30


class Limited(Exception):
    pass


def get(path, pause):
    """GET with a fixed pause; on 429 wait as Upland asks, then retry."""
    for attempt in range(6):
        time.sleep(pause)
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path, headers=HEADERS), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get('Retry-After') or 60) + 5
                log(f'  rate limited; waiting {wait}s')
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            raise
        except Exception as e:
            log(f'  retry {attempt + 1} for {path}: {e}')
            time.sleep(5 * (attempt + 1))
    raise Limited(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', type=float, default=90, help='time budget for property lookups this run')
    ap.add_argument('--pause', type=float, default=2.0, help='seconds between requests to Upland')
    ap.add_argument('--max', type=int, default=0, help='stop after reading this many properties (0 = no limit)')
    ap.add_argument('--users', default=','.join(GROUP), help='comma-separated players to collect')
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60

    colls = get('/collections', args.pause)
    save('collections/collections.json', {'rows': [
        {k: c.get(k) for k in ('id', 'name', 'amount', 'category', 'yield_boost', 'one_time_reward', 'city_id', 'requirements')} for c in colls]})

    props = load('collections/props.json', {})
    users = {}
    for u in [x.strip() for x in args.users.split(',') if x.strip()]:
        p = get(f'/profile/{u}', args.pause)
        if not p:
            log(f'{u}: profile not found')
            continue
        users[u] = {'props': [x['property_id'] for x in p.get('properties') or []],
                    'active': [c['id'] for c in p.get('collections') or []],
                    'collected': [c['id'] for c in p.get('previouslyCompletedCollections') or []]}
        log(f'{u}: {len(users[u]["props"])} properties')

    now = int(time.time())
    wanted = [pid for u in users.values() for pid in u['props']]
    todo = [pid for pid in dict.fromkeys(wanted)
            if str(pid) not in props or now - props[str(pid)].get('at', 0) > REFRESH_DAYS * 86400]
    log(f'{len(todo)} properties to read (of {len(set(wanted))})')
    done = 0
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        for pid in todo:
            if time.time() > deadline or (args.max and done >= args.max):
                break
            d = get(f'/properties/{pid}', args.pause)
            m = get(f'/properties/match/{pid}', args.pause)
            if not d:
                continue
            props[str(pid)] = {'at': now, 'a': d.get('full_address'), 'c': (d.get('city') or {}).get('id'),
                               'cn': (d.get('city') or {}).get('name'), 's': (d.get('street') or {}).get('id'),
                               'st': (d.get('state') or {}).get('name'), 'y': d.get('yield_per_hour') or 0,
                               'm': [x['id'] for x in (m or [])]}
            done += 1
            if done % 10 == 0:
                log(f'  {done} read')
                save('collections/props.json', props)
    except Limited as e:
        log(f'stopping early, Upland keeps refusing: {e}')
    except KeyboardInterrupt:
        log('stopped; saving what was read')
    save('collections/props.json', props)
    for u, v in users.items():
        missing = sum(1 for pid in v['props'] if str(pid) not in props)
        v['missing'] = missing
        save(f'collections/users/{u}.json', v)
    state = load('collections/state.json', {})
    group = sorted(set(state.get('group', [])) | set(users))
    save('collections/state.json', {'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'group': group,
                                    'remaining': len(todo) - done})
    log(f'read {done}; {len(todo) - done} left for later runs')


if __name__ == '__main__':
    main()
