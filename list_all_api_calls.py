import json
import re

FNAME = "chrome-net-export-log.json"

with open(FNAME) as f:
    data = json.load(f)

events = data.get("events", [])
source_urls = {}
for e in events:
    sid = e.get("source", {}).get("id")
    url = e.get("params", {}).get("url") if isinstance(e.get("params"), dict) else None
    if sid is not None and url:
        source_urls[sid] = url

NOISE = ["sentry", "clickstream", "doubleclick", "clevertap", "branch.io",
         "googleads", "google.com", "analytics.google", "gstatic", "googletagmanager"]

api_urls = set()
for url in source_urls.values():
    low = url.lower()
    if "bookmyshow" not in low:
        continue
    if any(n in low for n in NOISE):
        continue
    if "/api/" in low or ".aspx" in low:
        api_urls.add(url.split("?")[0])

print(f"{len(api_urls)} unique BMS API paths called during this page load:\n")
for u in sorted(api_urls):
    print(" ", u)
