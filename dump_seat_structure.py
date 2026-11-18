import json
from curl_cffi import requests as cf

EVENT = "ET00511463"
VENUE = "AMBH"
DATE = "20260814"
REGION_SLUG = "hyd"
REGION_CODE = "HYD"

BASE = "https://in.bookmyshow.com"
seat_page_url = f"{BASE}/movies/{REGION_SLUG}/seat-layout/{EVENT}/{VENUE}/116349/{DATE}"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": seat_page_url,
    "Origin": BASE,
    "x-app-code": "WEB",
    "x-region-code": REGION_CODE,
    "x-region-slug": REGION_SLUG,
    "x-location-selection": "manual",
}

session = cf.Session(impersonate="chrome124")
session.get(seat_page_url, headers=headers, timeout=15)

url = f"{BASE}/api/movies-data/seatlayout/v1/primary"
params = {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE}
resp = session.get(url, headers=headers, params=params, timeout=15)
data = resp.json()

with open("seat_layout_full.json", "w") as f:
    json.dump(data, f, indent=2)
print(f"Saved full response ({len(resp.text)} chars) to seat_layout_full.json")

def find_keys(obj, path="root", results=None, depth=0):
    if results is None:
        results = []
    if depth > 10:
        return results
    keywords = ("row", "seat", "area", "categor", "status", "avail", "block")
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if any(kw in k.lower() for kw in keywords):
                if isinstance(v, (dict, list)):
                    results.append((p, f"<{type(v).__name__} len={len(v)}>"))
                else:
                    results.append((p, json.dumps(v)[:100]))
            find_keys(v, p, results, depth + 1)
    elif isinstance(obj, list) and obj:
        find_keys(obj[0], f"{path}[0]", results, depth + 1)
    return results

hits = find_keys(data)
print(f"\n{len(hits)} row/seat/area/category/status-related keys:")
for p, v in hits[:60]:
    print(f"  {p} = {v}")
