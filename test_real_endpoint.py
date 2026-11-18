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
print("STATUS:", resp.status_code)
print("Content-Type:", resp.headers.get("content-type"))
print("Response headers with 'encrypt' in name:", [h for h in resp.headers if "encrypt" in h.lower()])
print("\nFirst 1000 chars of body:")
print(resp.text[:1000])
