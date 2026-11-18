from curl_cffi import requests as cf

EVENT = "ET00505091"
VENUE = "AMBH"
SESSION = "116305"
DATE = "20260812"
REGION_SLUG = "hyd"
REGION_CODE = "HYD"

BASE = "https://in.bookmyshow.com"
warmup_url = f"{BASE}/movies/{REGION_SLUG}/buytickets/{EVENT}/"
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

CANDIDATES = [
    f"/api/movies-data/v4/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/showtimes-by-event/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/seatlayout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v5/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v5/seatlayout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/venue/{VENUE}/seat-layout/{SESSION}",
    f"/api/movies-data/v4/full-seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/seat-layout?eventCode={EVENT}&venueCode={VENUE}&sessionId={SESSION}&dateCode={DATE}",
    f"/api/movies-data/v4/seat-layout?eventCode={EVENT}&venueCode={VENUE}&fullSeatLayout=true",
    f"/api/de/seat-layout/{EVENT}/{VENUE}/{SESSION}/{DATE}",
    f"/api/movies-data/v4/inventory/{EVENT}/{VENUE}/{SESSION}",
    f"/api/movies-data/v4/session/{SESSION}/seat-layout",
]

session = cf.Session(impersonate="chrome124")
try:
    session.get(warmup_url, headers=headers, timeout=15)
except Exception as e:
    print(f"warm-up failed: {e}")

for path in CANDIDATES:
    url = BASE + path
    try:
        resp = session.get(url, headers=headers, timeout=15)
        preview = resp.text[:150].replace("\n", " ")
        print(f"[{resp.status_code}] {path}")
        if resp.status_code == 200:
            print(f"    >>> {preview}")
    except Exception as e:
        print(f"[ERR] {path} — {e}")
