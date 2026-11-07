#!/usr/bin/env python3
"""Rockdrigo's hunting sessions, trimmed to what the Rounds page needs: data/troves/rockdrigo/rounds.json

  python3 tools/build_rounds.py "/path/to/trove-hunting-session-....json" [more exports]

One row per hunt event, [seconds since epoch, property index, trove units found, source index], plus the sends (stand fees), as
[seconds, fee]. Addresses, trove names and ids are left out: the page only needs when, how much and from what kind of source.
Exports that overlap are merged by event id.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'troves', 'rockdrigo', 'rounds.json')


def source(h):
    if h['kind'] == 'plant':
        return h.get('type') or 'Plant'
    parts = (h.get('model') or '').split('/')
    return parts[1].replace('_', ' ').title() if len(parts) > 2 else 'Structure'


def main(paths):
    seen, events, sends = set(), [], {}
    for path in paths:
        raw = json.load(open(path))
        for h in raw['hunts']:
            k = (h['t'], h['id'], h['prop'])
            if k in seen:
                continue
            seen.add(k)
            events.append((round(h['t'] / 1000), h['prop'], sum(t['n'] for t in h['troves']), source(h)))
        for s in raw.get('sends', []):
            sends[(s['t'], s['prop'])] = s['fee']
    events.sort()
    props, srcs = {}, {}
    rows = []
    for t, p, n, s in events:
        rows.append([t, props.setdefault(p, len(props)), n, srcs.setdefault(s, len(srcs))])
    out = {'format': 'upland-rounds-v1', 'from': events[0][0], 'to': events[-1][0], 'events': rows, 'src': list(srcs), 'sends': sorted([round(t / 1000), f] for (t, _), f in sends.items())}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print(len(rows), 'events,', len(out['sends']), 'sends,', os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main(sys.argv[1:])
