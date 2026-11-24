#!/usr/bin/env python3
"""Fill a craft-session page template with a planner's data: fill_page.py <data.json> <out.html> [template.html]

Replaces __DATA__ with the data and __STAMP__ with a fresh stamp. The page keeps its ticks in the browser under a key that carries the
stamp, so a new page always starts with nothing ticked (a page filled without a stamp shares its ticks with every other one).
"""
import json
import os
import sys
import time

here = os.path.dirname(os.path.abspath(__file__))
data, out = sys.argv[1], sys.argv[2]
tpl = sys.argv[3] if len(sys.argv) > 3 else os.path.join(here, 'page_template_city.html')
d = json.load(open(data))
stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + ''.join(c for c in '-'.join(t['t'] for t in d.get('meta', {}).get('unlocked', [])) if c.isalnum() or c == '-')[:40]
html = open(tpl).read().replace('__STAMP__', stamp).replace('__DATA__', json.dumps(d, ensure_ascii=False).replace('</', '<\\/'))
open(out, 'w').write(html)
print(out, len(html) // 1024, 'KB', 'stamp', stamp)
