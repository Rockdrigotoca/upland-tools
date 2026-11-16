#!/usr/bin/env python3
"""Turn the private inbox download (data/messages/, git-ignored) into the public
sales file data/mysales.json that sales/index.html reads.

Only what the dashboard needs is kept: date, asset category, item name, price and
currency. No message ids, buyers or other personal details.
Row = [date, asset category, item, price, currency, source, shop]. Sources:
  s  purchase_in_secondary_market: one of my items was bought on the market (mine)
  v  my_sub_merch_item_sold: my item sold in somebody else's shop (mine)
  h  sub_merch_item_sold: a sub-vendor's item sold in one of MY shops. The price is
     the sub-vendor's, not my income, so the dashboard keeps it apart.
"""
import glob, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = {"purchase_in_secondary_market": "s", "my_sub_merch_item_sold": "v", "sub_merch_item_sold": "h"}

seen, msgs = set(), []
for f in sorted(glob.glob(str(ROOT / "data/messages/page_*.json"))):
    for m in json.load(open(f)) or []:
        if m["id"] not in seen:
            seen.add(m["id"]); msgs.append(m)

rows = []
for m in msgs:
    if m["type"] not in SRC or m["amount"] is None:
        continue
    for a in m["nft_asset"] or []:
        md = (a.get("metadata") or {}).get("metadata") or {}
        td = a.get("tradeData") or {}
        row = [m["created_at"][:19] + "Z", a.get("category") or "?",
               md.get("displayName") or "?", m["amount"], m["currency"], SRC[m["type"]], td.get("shopName") or ""]
        if SRC[m["type"]] == "h":
            row.append(td.get("subMerchantUsername") or "")  # public in-game username of the sub-vendor
        rows.append(row)
rows.sort(reverse=True)
out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
       "from": min(m["created_at"] for m in msgs)[:10], "to": max(m["created_at"] for m in msgs)[:10],
       "rows": rows}
(ROOT / "data/mysales.json").write_text(json.dumps(out, separators=(",", ":")))
print(len(msgs), "messages,", len(rows), "sales ->", "data/mysales.json")
