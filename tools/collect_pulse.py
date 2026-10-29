#!/usr/bin/env python3
"""Daily neighbourhood numbers for the Quailwood and Nomentano pulse.

Reads each neighbourhood's overview from Uplytics (uplytics.org, by Laban), the same small JSON its own page loads.
One request per neighbourhood per run, so it stays very light. Stores a growing history in data/pulse/<key>.json,
one entry per day, so weekly changes can be worked out later.
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prices import load, log, save   # noqa: E402

UA = 'upland-tools-collector/1.0 (+https://github.com/Rockdrigotoca/upland-tools)'
NODES = {'qw': 'Quailwood', 'nomentano': 'Nomentano'}
KEEP = ['total_properties', 'owned_properties', 'unminted_properties', 'for_sale_properties', 'total_buildings', 'under_construction',
        'total_service_structures', 'total_living_units', 'total_service_units', 'total_residents', 'total_unique_owners',
        'total_home_addresses', 'occupancy_rate', 'su_per_lu', 'build_out_percentage', 'total_staked_sparklet', 'active_homeowners_7d']


def fetch(key):
    req = urllib.request.Request(f'https://uplytics.org/api/get_overview_stats_with_trend.php?nh={key}', headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def main():
    for i, (key, name) in enumerate(NODES.items()):
        if i:
            time.sleep(3)
        try:
            d = fetch(key)
        except Exception as e:
            log(f'{name}: could not read ({e})')
            continue
        if d.get('error') or not d.get('stat_date'):
            log(f'{name}: no data ({d.get("error")})')
            continue
        path = f'pulse/{key}.json'
        old = load(path, {'history': []})
        row = {'date': d['stat_date']}
        row.update({k: d[k] for k in KEEP if k in d})
        hist = [h for h in old.get('history', []) if h['date'] != row['date']] + [row]
        hist.sort(key=lambda h: h['date'])
        save(path, {'node': key, 'name': name, 'city': 'Bakersfield' if key == 'qw' else 'Rome', 'source': 'uplytics.org',
                    'latest': row, 'history': hist[-400:]})
        log(f'{name}: {row["date"]}, {row.get("total_residents")} residents, {row.get("total_buildings")} buildings')


if __name__ == '__main__':
    main()
