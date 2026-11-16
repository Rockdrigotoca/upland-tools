#!/usr/bin/env python3
"""Download the whole Upland message inbox (read-only) into data/messages/.

Private data: data/messages/ is git-ignored. The login token is read from the
UPLAND_TOKEN environment variable or the file named in UPLAND_TOKEN_FILE;
it is never written anywhere by this script.

Pages are saved as raw JSON (page_<offset>.json) so a run can resume.
Usage: UPLAND_TOKEN_FILE=... python3 tools/collect_messages.py [--fresh]
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "messages"
URL = "https://api.prod.upland.me/api/messages?limit=%d&offset=%d"
PAUSE = 1.0


def token():
    t = os.environ.get("UPLAND_TOKEN")
    if not t and os.environ.get("UPLAND_TOKEN_FILE"):
        t = Path(os.environ["UPLAND_TOKEN_FILE"]).read_text().strip()
    if not t:
        sys.exit("set UPLAND_TOKEN or UPLAND_TOKEN_FILE")
    return t


def fetch(limit, offset, tok):
    req = urllib.request.Request(URL % (limit, offset), headers={
        "authorization": "Bearer " + tok, "origin": "https://play.upland.me",
        "platform": "web", "appversion": "0.14.1148", "locale": "en-US",
        "content-type": "application/json", "accept": "*/*",
        "referer": "https://play.upland.me/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return None
            if e.code in (401, 403):
                sys.exit("auth refused (%d): token expired?" % e.code)
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))
    sys.exit("giving up at offset %d" % offset)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = token()
    limit = 50
    for cand in (100, 50):  # the server rejects big pages; find the largest allowed
        if fetch(cand, 0, tok) is not None:
            limit = cand
            break
    print("page size", limit, flush=True)
    offset, total = 0, 0
    while True:
        f = OUT / ("page_%06d_%d.json" % (offset, limit))
        if f.exists() and "--fresh" not in sys.argv:
            page = json.loads(f.read_text())
        else:
            page = fetch(limit, offset, tok)
            f.write_text(json.dumps(page))
            time.sleep(PAUSE)
        if not page:
            break
        total += len(page)
        if (offset // limit) % 20 == 0:
            print("offset", offset, "oldest so far", page[-1]["created_at"], flush=True)
        offset += limit
    print("done:", total, "messages in", OUT, flush=True)


if __name__ == "__main__":
    main()
