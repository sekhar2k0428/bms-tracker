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

attempts = [
    {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "fullSeatLayout": "true"},
    {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "fullSeatLayout": "Y"},
    {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "sessionId": "116349", "fullSeatLayout": "true"},
]

for i, params in enumerate(attempts):
    resp = session.get(url, headers=headers, params=params, timeout=15)
    print(f"\nAttempt {i+1}: params={params}")
    print(f"  status={resp.status_code}, len={len(resp.text)} chars")
    if len(resp.text) > 6000:
        fname = f"seat_layout_full_{i+1}.json"
        with open(fname, "w") as f:
            f.write(resp.text)
        print(f"  >>> Bigger response! Saved to {fname}")
