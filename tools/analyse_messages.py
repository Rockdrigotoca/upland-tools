#!/usr/bin/env python3
"""Summarise what was sold, from the downloaded inbox in data/messages/.

Sale messages: purchase_in_secondary_market (someone bought one of my items;
ownerUsername on the asset is the buyer) and my_sub_merch_item_sold (my item sold in another shop).
Sales at exactly 1 UPX are treated as gifts: counted apart, left out of totals.
Writes data/messages/sales_by_item.csv, sales_all.csv and sales_report.md
(all git-ignored, private).
"""
import csv, glob, json, collections
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data" / "messages"
SALE_TYPES = {"purchase_in_secondary_market", "my_sub_merch_item_sold"}  # sub_merch_item_sold = sub-vendors in my shops, not mine
GROUPS = {  # asset category code -> reporting group
    "outdoordecor": "Assets / Outdoor Decor", "structornmt": "Ornaments",
    "seeds": "Seeds", "landvehicle": "Vehicles / Go-karts",
}


def group(cat):
    return GROUPS.get(cat, "Other (" + cat + ")")


def load():
    seen, out = set(), []
    for f in sorted(glob.glob(str(D / "page_*.json"))):
        for m in json.load(open(f)) or []:
            if m["id"] not in seen:
                seen.add(m["id"]); out.append(m)
    return out


def main():
    msgs = load()
    rows = []
    for m in msgs:
        if m["type"] not in SALE_TYPES or m["amount"] is None:
            continue
        for a in m["nft_asset"] or []:
            md = (a.get("metadata") or {}).get("metadata") or {}
            rows.append(dict(
                date=m["created_at"][:10], year=m["created_at"][:4], source=m["type"],
                group=group(a.get("category") or "?"), category=a.get("category") or "?",
                kind=a.get("type") or "", item=md.get("displayName") or "?",
                rarity=md.get("rarityLevel") or "", buyer=a.get("ownerUsername") or "",
                amount=m["amount"], currency=m["currency"],
                gift=(m["currency"] == "UPX" and m["amount"] == 1)))
    with open(D / "sales_all.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    L = ["# Sales report", "",
         "%d messages read, %d sold items; oldest message %s, oldest sale %s." % (
             len(msgs), len(rows), min(m["created_at"] for m in msgs)[:10], min(r["date"] for r in rows)),
         "Gift = exactly 1 UPX (not counted in totals).", ""]
    paid = [r for r in rows if not r["gift"]]
    gifts = [r for r in rows if r["gift"]]

    def tot(rs, cur):
        x = [r["amount"] for r in rs if r["currency"] == cur]
        return len(x), sum(x)

    L += ["## By group", "", "| Group | Sales (UPX) | UPX total | Sales (USD) | USD total | Gifts @1 UPX |", "|---|---|---|---|---|---|"]
    for g in sorted({r["group"] for r in rows}):
        n, s = tot([r for r in paid if r["group"] == g], "UPX")
        nu, su = tot([r for r in paid if r["group"] == g], "USD")
        L.append("| %s | %d | %s | %d | %.2f | %d |" % (g, n, format(round(s), ","), nu, su, len([r for r in gifts if r["group"] == g])))
    n, s = tot(paid, "UPX"); nu, su = tot(paid, "USD")
    L += ["| **All** | %d | %s | %d | %.2f | %d |" % (n, format(round(s), ","), nu, su, len(gifts)), ""]

    L += ["## By year", "", "| Year | Sales (UPX) | UPX total | Sales (USD) | USD total | Gifts |", "|---|---|---|---|---|---|"]
    for y in sorted({r["year"] for r in rows}):
        n, s = tot([r for r in paid if r["year"] == y], "UPX"); nu, su = tot([r for r in paid if r["year"] == y], "USD")
        L.append("| %s | %d | %s | %d | %.2f | %d |" % (y, n, format(round(s), ","), nu, su, len([r for r in gifts if r["year"] == y])))
    L.append("")

    items = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in paid:
        items[r["group"]][(r["category"], r["item"])].append(r)
    csvrows = []
    for g in sorted(items):
        L += ["## " + g, "", "| Item | Sold | UPX total | Avg | Min | Max | USD sales | USD total |", "|---|---|---|---|---|---|---|---|"]
        for (cat, it), rs in sorted(items[g].items(), key=lambda kv: -sum(r["amount"] for r in kv[1] if r["currency"] == "UPX")):
            u = [r["amount"] for r in rs if r["currency"] == "UPX"]; d = [r["amount"] for r in rs if r["currency"] == "USD"]
            L.append("| %s | %d | %s | %s | %s | %s | %d | %.2f |" % (
                it, len(rs), format(round(sum(u)), ","), format(round(sum(u) / len(u)), ",") if u else "-",
                format(round(min(u)), ",") if u else "-", format(round(max(u)), ",") if u else "-", len(d), sum(d)))
            csvrows.append([g, cat, it, len(rs), round(sum(u), 2), len(u), len(d), round(sum(d), 2)])
        L.append("")
    with open(D / "sales_by_item.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["group", "category", "item", "paid_sales", "upx_total", "upx_sales", "usd_sales", "usd_total"]); w.writerows(csvrows)

    L += ["## Sold for exactly 1 UPX (gifts)", "", "| Group | Item | Count |", "|---|---|---|"]
    gc = collections.Counter((r["group"], r["item"]) for r in gifts)
    for (g, it), c in sorted(gc.items(), key=lambda kv: (kv[0][0], -kv[1])):
        L.append("| %s | %s | %d |" % (g, it, c))
    (D / "sales_report.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
