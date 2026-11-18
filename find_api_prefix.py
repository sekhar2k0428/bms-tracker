import re

FILES = ["seatlayout-library.acaae459.js", "app-seatlayout-movies.49541a29.js"]

for fname in FILES:
    print(f"\n{'=' * 20} {fname} {'=' * 20}")
    try:
        text = open(fname).read()
    except FileNotFoundError:
        print("  not found — run find_seat_api.py first")
        continue

    hits = set(re.findall(r'["\']([^"\']{0,20}api[^"\']{0,150})["\']', text, re.I))
    hits = {h for h in hits if "/" in h}
    print(f"  {len(hits)} 'api'-containing path-like strings:")
    for h in sorted(hits)[:40]:
        print("   ", h)

    md_hits = set(re.findall(r'["\']([^"\']{0,150}movies-data[^"\']{0,80})["\']', text, re.I))
    if md_hits:
        print(f"  {len(md_hits)} 'movies-data'-containing strings:")
        for h in sorted(md_hits):
            print("   ", h)

    idx = text.find("fullSeatLayout")
    if idx != -1:
        print("  Context around 'fullSeatLayout' (600 chars before):")
        print("   ", text[max(0, idx - 600):idx + 100])
