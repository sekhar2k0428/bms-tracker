import re
from curl_cffi import requests as cf

BUNDLES = [
    "https://generic-web-assets-in.bmscdn.com/public/build/chunks/js/seatlayout-library.acaae459.js",
    "https://generic-web-assets-in.bmscdn.com/public/build/chunks/js/app-seatlayout-movies.49541a29.js",
]

session = cf.Session(impersonate="chrome124")

for url in BUNDLES:
    fname = url.rsplit("/", 1)[-1]
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

    hits = set(re.findall(r'["\']([^"\']{0,10}/[^"\']{0,150}seat[^"\']{0,80})["\']', text, re.I))
    hits |= set(re.findall(r'["\']([^"\']{0,80}seat[^"\']{0,10}/[^"\']{0,150})["\']', text, re.I))

    if hits:
        print(f"  {len(hits)} path-like strings containing 'seat':")
        for h in sorted(hits)[:25]:
            print("   ", h)
    else:
        print("  No path-like string containing 'seat' found — trying broader search...")
        broad = set(re.findall(r'["\']([^"\']{0,120}seat[^"\']{0,120})["\']', text, re.I))
        print(f"  {len(broad)} broader 'seat'-containing quoted strings (showing up to 20):")
        for h in sorted(broad)[:20]:
            print("   ", h)
