#!/usr/bin/env python3
"""Turn the private inbox download (data/messages/, git-ignored) into the public
sales file data/mysales.json that sales/index.html reads.

Only what the dashboard needs is kept: date, asset category, item name, price and
currency. No message ids, buyers or other personal details.
Sale messages: purchase_in_secondary_market (an item of mine was bought) and
sub_merch_item_sold (sold through a shop).
"""
import glob, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SALE_TYPES = {"purchase_in_secondary_market", "sub_merch_item_sold"}

seen, msgs = set(), []
for f in sorted(glob.glob(str(ROOT / "data/messages/page_*.json"))):
    for m in json.load(open(f)) or []:
        if m["id"] not in seen:
            seen.add(m["id"]); msgs.append(m)

rows = []
for m in msgs:
    if m["type"] not in SALE_TYPES or m["amount"] is None:
        continue
    for a in m["nft_asset"] or []:
        md = (a.get("metadata") or {}).get("metadata") or {}
        rows.append([m["created_at"][:19] + "Z", a.get("category") or "?",
                     md.get("displayName") or "?", m["amount"], m["currency"]])
rows.sort(reverse=True)
out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
       "from": min(m["created_at"] for m in msgs)[:10], "to": max(m["created_at"] for m in msgs)[:10],
       "rows": rows}
(ROOT / "data/mysales.json").write_text(json.dumps(out, separators=(",", ":")))
print(len(msgs), "messages,", len(rows), "sales ->", "data/mysales.json")
