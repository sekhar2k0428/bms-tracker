from curl_cffi import requests as cf

EVENT = "ET00505091"
VENUE = "AMBH"
SESSION = "116305"
DATE = "20260812"
REGION_SLUG = "hyd"
REGION_CODE = "HYD"

MAIN = "https://in.bookmyshow.com"
SVC = "https://services-in.bookmyshow.com"
seat_page_url = f"{MAIN}/movies/{REGION_SLUG}/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": seat_page_url,
    "Origin": MAIN,
    "x-app-code": "WEB",
    "x-region-code": REGION_CODE,
    "x-region-slug": REGION_SLUG,
    "x-location-selection": "manual",
}

CANDIDATES = [
    f"/api/v1/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/v2/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/v1/seatlayout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/movies-data/v4/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/movies-data/v4/seatlayout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/seatlayout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/booking/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/inventory/seat-layout/{EVENT}/{VENUE}/{SESSION}",
    f"/api/v1/seatlayout?eventCode={EVENT}&venueCode={VENUE}&sessionId={SESSION}&dateCode={DATE}",
]

session = cf.Session(impersonate="chrome124")
try:
    session.get(seat_page_url, headers=headers, timeout=15)
except Exception as e:
    print(f"warm-up failed: {e}")

for path in CANDIDATES:
    url = SVC + path
    try:
        resp = session.get(url, headers=headers, timeout=15)
        preview = resp.text[:150].replace("\n", " ")
        print(f"[{resp.status_code}] {path}")
        if resp.status_code == 200:
            print(f"    >>> {preview}")
    except Exception as e:
        print(f"[ERR] {path} — {e}")
