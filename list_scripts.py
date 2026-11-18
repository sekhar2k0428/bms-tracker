import re

for label, fname in [("AMB", "amb_seatpage.html"), ("Allu", "allu_seatpage.html")]:
    print(f"\n{'=' * 20} {label} {'=' * 20}")
    try:
        html = open(fname).read()
    except FileNotFoundError:
        print(f"  {fname} not found")
        continue
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I)
    seen = []
    for s in srcs:
        if s not in seen:
            seen.append(s)
    print(f"  {len(seen)} script tags found:")
    for s in seen:
        print("   ", s)
