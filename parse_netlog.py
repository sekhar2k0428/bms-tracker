"""
Parses a Chrome net-export NetLog JSON dump. Builds a source-id -> URL
map from request-start events, then scans every event's string params
for hex-encoded byte data, decodes it, and searches for seat/row/
booking-related content — printing the associated URL when found.
"""

import sys
import json
import binascii

FNAME = sys.argv[1] if len(sys.argv) > 1 else "netlog.json"
KEYWORDS = ["seat", "row", "eventcode", "venuecode", "sessionid", "layout"]
NOISE = ["sentry", "clickstream", "doubleclick", "clevertap", "branch.io", "googleads"]

print(f"Loading {FNAME} ...")
with open(FNAME) as f:
    data = json.load(f)

events = data.get("events", [])
print(f"{len(events)} events total")

source_urls = {}
for e in events:
    sid = e.get("source", {}).get("id")
    url = e.get("params", {}).get("url") if isinstance(e.get("params"), dict) else None
    if sid is not None and url:
        source_urls[sid] = url


def try_hex_decode(s):
    if not isinstance(s, str) or len(s) < 8:
        return None
    try:
        raw = binascii.unhexlify(s)
        return raw.decode("utf-8", errors="ignore")
    except (binascii.Error, ValueError):
        return None


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


hits = []
for e in events:
    sid = e.get("source", {}).get("id")
    url = source_urls.get(sid, "")
    if any(n in url.lower() for n in NOISE):
        continue
    for s in walk_strings(e.get("params", {})):
        decoded = try_hex_decode(s)
        text = decoded if decoded else s
        low = text.lower()
        if any(k in low for k in KEYWORDS) and "bookmyshow" in url.lower():
            hits.append((url, text[:500]))

print(f"\n{len(hits)} matching hits (URL from a non-noise bookmyshow source, containing a keyword):\n")
seen_urls = set()
for url, text in hits:
    if url not in seen_urls:
        seen_urls.add(url)
        print(f"URL: {url}")
    print(f"  >>> {text}")
    print()
