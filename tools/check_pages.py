#!/usr/bin/env python3
"""Catches the two mistakes that have broken the big single-file pages: a function declared twice (the later one silently wins) and a text key
repeated inside one language block (the later one silently wins). Also checks that the inline script parses.

  python3 tools/check_pages.py            # troves/, trove-helper/, rounds/ and blueprint/
"""
import re
import subprocess
import sys

PAGES = ['troves/index.html', 'trove-helper/index.html', 'rounds/index.html', 'blueprint/index.html']


def check(path):
    s = open(path).read()
    problems = []
    m = re.search(r'<script>(.*)</script>', s, re.S)
    code = m.group(1) if m else ''
    names = re.findall(r'^(?:async )?function ([A-Za-z0-9_$]+)\(', code, re.M)
    for n in sorted({n for n in names if names.count(n) > 1}):
        problems.append(f'function {n} is declared {names.count(n)} times')
    reg = re.search(r'Site\.register\(\{(.*?)\n\}\);', code, re.S)
    if reg:
        body = reg.group(1)
        cut = re.search(r'\n\s*es:\{', body)
        es = body[cut.end():] if cut else ''
        tail = re.search(r'\n\s*(?:en_cunk|es_cunk):\{', es)
        blocks = {'en': body[:cut.start()] if cut else body, 'es': es[:tail.start()] if tail else es}
        for loc, blk in blocks.items():
            keys = re.findall(r"(?:(?<=[\s,{]))([A-Za-z_][A-Za-z0-9_]*):'", blk)
            for k in sorted({k for k in keys if keys.count(k) > 1}):
                problems.append(f'text key {k} is repeated in {loc}')
    try:
        subprocess.run(['node', '-e', 'new Function(require("fs").readFileSync(0,"utf8"))'], input=code.encode(), check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        problems.append('script does not parse: ' + e.stderr.decode()[:200])
    return problems


bad = 0
for p in PAGES:
    pr = check(p)
    print(('FAIL ' if pr else 'ok   ') + p)
    for x in pr:
        print('   ', x)
    bad += len(pr)
sys.exit(1 if bad else 0)
