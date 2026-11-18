from curl_cffi import requests as cf

EVENT = "ET00511463"
VENUE = "AMBH"
DATE = "20260814"
SESSION = "116349"
REGION_SLUG = "hyd"
REGION_CODE = "HYD"

BASE = "https://in.bookmyshow.com"
seat_page_url = f"{BASE}/movies/{REGION_SLUG}/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}"

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

CANDIDATES = [
    ("/api/v1/mobile/secondary/init", {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "sessionId": SESSION}),
    ("/api/movies-data/seatlayout/v1/secondary", {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "sessionId": SESSION}),
    ("/api/movies-data/seatlayout/v2/secondary", {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "sessionId": SESSION}),
    ("/api/movies-data/seatlayout/v1/secondary/init", {"eventCode": EVENT, "dateCode": DATE, "regionCode": REGION_CODE, "venueCode": VENUE, "sessionId": SESSION}),
]

for path, params in CANDIDATES:
    url = BASE + path
    try:
        resp = session.get(url, headers=headers, params=params, timeout=15)
        print(f"[{resp.status_code}] {path}  len={len(resp.text)}")
        if resp.status_code == 200 and len(resp.text) > 3000:
            fname = "secondary_" + path.strip("/").replace("/", "_") + ".json"
            with open(fname, "w") as f:
                f.write(resp.text)
            print(f"   >>> saved to {fname}, preview: {resp.text[:200]}")
    except Exception as e:
        print(f"[ERR] {path} — {e}")
