"""
Probe: fetch the real seat-selection pages and scan the HTML for any
embedded API endpoint references (script src bundles won't be scanned,
just the page's own HTML/inline scripts — often enough to spot the
seat-layout API path or an embedded JSON state blob).
"""

import re
from curl_cffi import requests as cf

TARGETS = [
    {
        "label": "AMB Cinemas 10:20 PM",
        "warmup": "https://in.bookmyshow.com/movies/hyd/buytickets/ET00505091/",
        "seat_url": "https://in.bookmyshow.com/movies/hyd/seat-layout/ET00505091/AMBH/116305/20260812",
        "outfile": "amb_seatpage.html",
    },
    {
        "label": "Allu Cinemas 11:00 PM",
        "warmup": "https://in.bookmyshow.com/movies/hyd/buytickets/ET00502689/",
        "seat_url": "https://in.bookmyshow.com/movies/hyd/seat-layout/ET00502689/ALUC/3435/20260812",
        "outfile": "allu_seatpage.html",
    },
]

HEADERS = {"Accept-Language": "en-IN,en;q=0.9"}


def scan(html, label):
    print(f"\n=== {label} — page length: {len(html)} chars ===")

    hits = set(re.findall(r'["\']([^"\']{0,200}api[^"\']{0,200})["\']', html, re.I))
    seat_hits = sorted(h for h in hits if "seat" in h.lower())
    other_api_hits = sorted(h for h in hits if "seat" not in h.lower())

    if seat_hits:
        print("  Candidates containing BOTH 'api' and 'seat':")
        for h in seat_hits[:15]:
            print("   ", h)
    else:
        print("  No quoted string contains both 'api' and 'seat'.")
        print(f"  Other 'api'-containing strings found ({len(other_api_hits)} total, showing up to 15):")
        for h in other_api_hits[:15]:
            print("   ", h)

    for marker in ["__NEXT_DATA__", "__INITIAL_STATE__", "window.__"]:
        if marker in html:
            idx = html.find(marker)
            print(f"  Found marker '{marker}' at char {idx} — snippet:")
            print("   ", html[idx:idx + 300].replace("\n", " "))


for t in TARGETS:
    session = cf.Session(impersonate="chrome124")
    try:
        session.get(t["warmup"], headers=HEADERS, timeout=15)
    except Exception as e:
        print(f"{t['label']}: warm-up failed: {e}")

    try:
        resp = session.get(t["seat_url"], headers=HEADERS, timeout=20)
        print(f"{t['label']}: seat page status {resp.status_code}")
        with open(t["outfile"], "w") as f:
            f.write(resp.text)
        scan(resp.text, t["label"])
    except Exception as e:
        print(f"{t['label']}: seat page fetch failed: {e}")
