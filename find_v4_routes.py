import re
from curl_cffi import requests as cf

BASE = "https://generic-web-assets-in.bmscdn.com/public/build/chunks/js/"
BUNDLES = [
    "app.5daea9ac.js",
    "common-code.161142cf.js",
    "vendor-secondary.4b8c8035.js",
    "vendor-primary.7ef97d4e.js",
    "runtime.b58d471a.js",
]

session = cf.Session(impersonate="chrome124")

for fname in BUNDLES:
    url = BASE + fname
    print(f"\n{'=' * 20} {fname} {'=' * 20}")
    try:
        resp = session.get(url, timeout=30)
        print(f"  status {resp.status_code}, {len(resp.text)} chars")
    except Exception as e:
        print(f"  fetch failed: {e}")
        continue

    text = resp.text
    with open(fname, "w") as f:
        f.write(text)

    hits = set(re.findall(r'["\']([^"\']{0,60}movies-data[^"\']{0,120})["\']', text, re.I))
    if hits:
        print(f"  {len(hits)} 'movies-data'-containing strings:")
        for h in sorted(hits):
            print("   ", h)
    else:
        print("  none found in this file")
