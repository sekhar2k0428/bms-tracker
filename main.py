"""
BookMyShow Ticket Tracker (All Formats + All Available Dates Edition)
=====================================================================
Give ANY single BMS movie page URL (e.g. ET00439706).
Automatically:
  1. Discovers all sibling format/language ET codes (2D, 3D, IMAX, Dolby, Barco HDR, 4DX)
  2. Discovers all BOOKABLE / AVAILABLE dates for each format when "date" is ""
  3. Tracks new dates opening, new showtimes, and sold-out categories opening new seats
"""

import os
import re
import sys
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import urlparse

from curl_cffi import requests as cf
from notify import send_telegram, send_email

WATCHES_FILE = os.getenv("WATCHES_FILE", "watches.json")
STATE_FILE = os.getenv("STATE_FILE", "bms_state.json")
API_URL = "https://in.bookmyshow.com/api/movies-data/v4/showtimes-by-event/primary-dynamic"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

AVAIL = {"0": "SOLD OUT", "1": "ALMOST FULL", "2": "FILLING FAST", "3": "AVAILABLE"}
DATE_STYLE = {"date-selected": "BOOKABLE", "date-disabled": "NOT_OPEN", "date-default": "AVAILABLE"}
TIME_WINDOWS = {"morning": (600, 1200), "afternoon": (1200, 1600), "evening": (1600, 1900), "night": (1900, 2400)}

REGIONS = {
    "chennai": ("CHEN", "13.056", "80.206", "tf3"),
    "mumbai": ("MUMBAI", "19.076", "72.878", "te7"),
    "delhi-ncr": ("NCR", "28.613", "77.209", "ttn"),
    "bengaluru": ("BANG", "12.972", "77.594", "tdr"),
    "bangalore": ("BANG", "12.972", "77.594", "tdr"),
    "hyderabad": ("HYD", "17.385", "78.487", "tep"),
    "hyd": ("HYD", "17.385", "78.487", "tep"),
    "kolkata": ("KOLK", "22.573", "88.364", "tun"),
    "pune": ("PUNE", "18.520", "73.856", "te2"),
    "kochi": ("KOCH", "9.932", "76.267", "t9z"),
}

_RUN_CACHE = {}


def parse_bms_url(url):
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    event_code = next((p for p in parts if re.match(r"^ET\d{8,}$", p)), None)
    date_code = next((p for p in parts if re.match(r"^\d{8}$", p)), "")

    region_slug = None
    for p in parts:
        if p.lower() in REGIONS:
            region_slug = p.lower()
            break
    if not region_slug and "movies" in parts:
        idx = parts.index("movies")
        if idx + 1 < len(parts) and not parts[idx + 1].startswith("ET"):
            region_slug = parts[idx + 1].lower()
        elif idx > 0:
            region_slug = parts[idx - 1].lower()

    return event_code, region_slug, date_code


def resolve_region(slug):
    key = (slug or "").lower()
    return REGIONS.get(key, (key.upper()[:6], "0", "0", ""))


def create_bms_session(region_slug, event_code):
    proxy = os.getenv("PROXY_URL", "").strip()
    session = cf.Session(
        impersonate="chrome124",
        proxies={"http": proxy, "https": proxy} if proxy else None,
    )
    try:
        session.get(
            f"https://in.bookmyshow.com/movies/{region_slug}/buytickets/{event_code}/",
            headers={"Accept-Language": "en-IN,en;q=0.9"},
            timeout=15,
        )
    except Exception:
        pass
    return session


def fetch_single_et(session, event_code, date_code, region_code, region_slug, lat, lon, geohash):
    cache_key = f"{event_code}|{date_code}|{region_code}"
    if cache_key in _RUN_CACHE:
        return _RUN_CACHE[cache_key]

    api_headers = {
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://in.bookmyshow.com/movies/{region_slug}/buytickets/{event_code}/",
        "Origin": "https://in.bookmyshow.com",
        "x-app-code": "WEB",
        "x-region-code": region_code,
        "x-region-slug": region_slug,
        "x-geohash": geohash,
        "x-latitude": lat,
        "x-longitude": lon,
        "x-location-selection": "manual",
    }
    params = {
        "eventCode": event_code, "dateCode": date_code or "", "isDesktop": "true",
        "regionCode": region_code, "xLocationShared": "false", "lat": lat, "lon": lon,
    }
    for attempt in range(3):
        try:
            resp = session.get(API_URL, headers=api_headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                _RUN_CACHE[cache_key] = data
                # Also cache under the actual returned dateCode so we don't fetch it twice
                actual_dc = str(data.get("data", {}).get("additionalData", {}).get("dateCode", ""))
                if actual_dc:
                    _RUN_CACHE[f"{event_code}|{actual_dc}|{region_code}"] = data
                return data
            print(f"    HTTP {resp.status_code} for {event_code} [{date_code or 'default'}] (attempt {attempt + 1}/3)")
        except Exception as e:
            print(f"    Request failed for {event_code} [{date_code or 'default'}] (attempt {attempt + 1}/3): {e}")
        if attempt < 2:
            time.sleep(3 * (attempt + 1))
    return None


def parse_dates(data):
    out = {}
    for w in data.get("data", {}).get("topStickyWidgets", []):
        if w.get("type") != "horizontal-block-list":
            continue
        for item in w.get("data", []):
            dc = str(item.get("id", ""))
            if re.match(r"^\d{8}$", dc):
                out[dc] = DATE_STYLE.get(item.get("styleId", ""), "UNKNOWN")
    return out


def fetch_all_formats_and_dates(event_code, target_date_filter, region_code, region_slug, lat, lon, geohash):
    """
    Discovers all sibling format ET codes AND fetches all open/bookable dates
    (unless target_date_filter specifies particular date(s)).
    """
    group_key = f"GROUP_ALL|{event_code}|{target_date_filter}|{region_code}"
    if group_key in _RUN_CACHE:
        return _RUN_CACHE[group_key]

    session = create_bms_session(region_slug, event_code)
    primary = fetch_single_et(session, event_code, "", region_code, region_slug, lat, lon, geohash)
    if not primary:
        return [], set(), set()

    blob = (
        json.dumps(primary.get("data", {}).get("bottomSheetData", {}))
        + json.dumps(primary.get("data", {}).get("header", {}))
    )
    discovered_ets = sorted(set(re.findall(r"ET\d{8,}", blob)) | {event_code})

    # If user specified explicit date(s) like "20261217,20261218", only check those
    explicit_dates = [d.strip() for d in (target_date_filter or "").split(",") if re.match(r"^\d{8}$", d.strip())]

    payloads = []
    scanned_dates = set()

    for ec in discovered_ets:
        first_data = primary if ec == event_code else fetch_single_et(
            session, ec, "", region_code, region_slug, lat, lon, geohash
        )
        if not first_data:
            continue

        ec_dates = parse_dates(first_data)
        first_dc = str(first_data.get("data", {}).get("additionalData", {}).get("dateCode", ""))

        if explicit_dates:
            dates_to_fetch = explicit_dates
        else:
            # Automatically grab every date that is BOOKABLE or AVAILABLE for this format
            open_dates = [dc for dc, st in ec_dates.items() if st in ("BOOKABLE", "AVAILABLE")]
            if first_dc and first_dc not in open_dates:
                open_dates.append(first_dc)
            dates_to_fetch = sorted(set(open_dates))

        if not dates_to_fetch and first_dc:
            dates_to_fetch = [first_dc]

        for dc in dates_to_fetch:
            scanned_dates.add(dc)
            if dc == first_dc:
                payloads.append((ec, dc, first_data))
            else:
                d_data = fetch_single_et(session, ec, dc, region_code, region_slug, lat, lon, geohash)
                if d_data:
                    payloads.append((ec, dc, d_data))

    result = (payloads, set(discovered_ets), scanned_dates)
    _RUN_CACHE[group_key] = result
    return result


def extract_screen_info(st, sa):
    candidates = [
        st.get("screenAttr", ""),
        sa.get("screenAttr", ""),
        st.get("subtitle", ""),
        st.get("cta", {}).get("analytics", {}).get("format", ""),
        sa.get("attributes", ""),
        sa.get("format", ""),
    ]
    cleaned = []
    for item in candidates:
        s = str(item or "").strip()
        if s and s.lower() != "none" and s not in cleaned:
            cleaned.append(s)
    return " | ".join(cleaned)


def parse_shows(data, event_code="", fallback_date=""):
    shows = []
    actual_dc = str(data.get("data", {}).get("additionalData", {}).get("dateCode") or fallback_date or "")
    for w in data.get("data", {}).get("showtimeWidgets", []):
        if w.get("type") != "groupList":
            continue
        for g in w.get("data", []):
            if g.get("type") != "venueGroup":
                continue
            for card in g.get("data", []):
                if card.get("type") != "venue-card":
                    continue
                venue = card.get("additionalData", {}).get("venueName", "Unknown")
                for st in card.get("showtimes", []):
                    sa = st.get("additionalData", {})
                    date_code = str(sa.get("showDateCode") or sa.get("dateCode") or actual_dc)
                    screen_info = extract_screen_info(st, sa)
                    cats = [
                        {"name": c.get("priceDesc", ""), "price": c.get("curPrice", "0"),
                         "status": str(c.get("availStatus", ""))}
                        for c in sa.get("categories", [])
                    ]
                    shows.append({
                        "event_code": event_code,
                        "venue": venue,
                        "time": st.get("title", ""),
                        "time_code": sa.get("showTimeCode", ""),
                        "date": date_code,
                        "session_id": sa.get("sessionId", ""),
                        "screen": screen_info,
                        "raw_blob": json.dumps(st).lower(),
                        "categories": cats,
                    })
    return shows


def matches_filters(show, theatre, screen_filter, time_filter):
    if theatre and not any(k.strip().lower() in show["venue"].lower()
                            for k in theatre.split(",") if k.strip()):
        return False
    if screen_filter:
        keywords = [k.strip().lower() for k in screen_filter.split(",") if k.strip()]
        if not any(k in show["screen"].lower() or k in show["raw_blob"] for k in keywords):
            return False
    if time_filter:
        try:
            tc = int(show["time_code"])
        except ValueError:
            tc = 0
        periods = [p.strip().lower() for p in time_filter.split(",") if p.strip()]
        if not any(lo <= tc < hi for p in periods for lo, hi in [TIME_WINDOWS.get(p, (-1, -1))]):
            return False
    return True


def build_watch_state(shows, dates, category_filter):
    show_state = {}
    for s in shows:
        for c in s["categories"]:
            if category_filter and category_filter.lower() not in c["name"].lower():
                continue
            # Include date in key so multiple days never collide
            key = f"{s['venue']}|{s['date']}|{s['session_id']}|{c['name']}"
            show_state[key] = {
                "venue": s["venue"], "time": s["time"], "date": s["date"],
                "screen": s["screen"], "cat": c["name"], "price": c["price"], "status": c["status"]
            }
    return {"shows": show_state, "dates": dates, "initialized": True}


def diff_state(old, new):
    changes = []
    old_dates, new_dates = old.get("dates", {}), new.get("dates", {})
    for dc, status in sorted(new_dates.items()):
        if old_dates.get(dc) in (None, "NOT_OPEN", "UNKNOWN") and status in ("BOOKABLE", "AVAILABLE"):
            changes.append(f"Date {dc} is now OPEN for booking")

    old_shows, new_shows = old.get("shows", {}), new.get("shows", {})
    for key in sorted(set(new_shows) - set(old_shows)):
        s = new_shows[key]
        scr = f" [{s['screen']}]" if s.get("screen") else ""
        changes.append(f"New showtime/tickets: {s['venue']}{scr} {s['time']} [{s['date']}] "
                        f"— {s['cat']} Rs.{s['price']} ({AVAIL.get(s['status'], 'OPEN')})")
    for key, ns in sorted(new_shows.items()):
        os_ = old_shows.get(key)
        if not os_:
            continue
        try:
            old_val, new_val = int(os_["status"]), int(ns["status"])
        except (ValueError, TypeError):
            continue
        if new_val > old_val:
            scr = f" [{ns['screen']}]" if ns.get("screen") else ""
            changes.append(f"More seats opened: {ns['venue']}{scr} {ns['time']} [{ns['date']}] "
                            f"— {ns['cat']} {AVAIL.get(os_['status'], '?')} -> {AVAIL.get(ns['status'], 'UNKNOWN')}")
    return changes


def watch_id(watch):
    basis = "|".join([
        watch.get("url", ""),
        watch.get("theatre", ""),
        watch.get("screen", ""),
        watch.get("category", ""),
        watch.get("date", ""),
    ])
    return hashlib.sha1(basis.encode()).hexdigest()[:10]


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def extract_movie_title(data):
    return data.get("data", {}).get("header", {}).get("title", {}).get("text", "")


def run_watch(watch, old_state):
    theatre_label = watch.get("theatre") or "All Theatres"
    screen_label = watch.get("screen") or "All Screens"
    event_code, region_slug, url_date = parse_bms_url(watch["url"])
    if not event_code or not region_slug:
        print(f"  [{watch.get('label') or theatre_label}] Invalid BMS URL.")
        return None, []

    region_code, lat, lon, geohash = resolve_region(region_slug)
    # Only filter by date if explicitly set in watch["date"] or URL; otherwise scan ALL open dates
    target_date_filter = watch.get("date") or url_date or ""

    payloads, discovered_ets, scanned_dates = fetch_all_formats_and_dates(
        event_code, target_date_filter, region_code, region_slug, lat, lon, geohash
    )
    movie_title = extract_movie_title(payloads[0][2]) if payloads else ""
    label = watch.get("label") or f"{movie_title or event_code} — {theatre_label} ({screen_label})"
    print(f"  [{label}]")

    if not payloads:
        print("    Bookings not open yet or no response from BMS.")
        baseline = old_state if old_state else {"shows": {}, "dates": {}, "initialized": True}
        return baseline, []

    all_shows = []
    merged_dates = {}
    seen_sessions = set()
    for ec, dc, pdata in payloads:
        for d_key, d_val in parse_dates(pdata).items():
            # If any format has a date as BOOKABLE/AVAILABLE, mark it open
            if d_val in ("BOOKABLE", "AVAILABLE") or d_key not in merged_dates:
                merged_dates[d_key] = d_val
        for s in parse_shows(pdata, ec, dc):
            uniq = f"{s['venue']}|{s['date']}|{s['session_id']}"
            if uniq not in seen_sessions:
                seen_sessions.add(uniq)
                all_shows.append(s)

    shows = [
        s for s in all_shows
        if matches_filters(s, watch.get("theatre", ""), watch.get("screen", ""), watch.get("time", ""))
    ]
    print(
        f"    Scanned {len(discovered_ets)} format(s) across {len(scanned_dates)} open date(s) "
        f"({', '.join(sorted(scanned_dates))}) -> {len(shows)} matching showtime(s) (of {len(all_shows)} city-wide)"
    )
    for s in sorted(shows, key=lambda x: (x["date"], x["time_code"])):
        cats = ", ".join(f"{c['name']}={AVAIL.get(c['status'], '?')}" for c in s["categories"])
        scr = f" [{s['screen']}]" if s.get("screen") else ""
        print(f"      [{s['date']}] {s['venue']}{scr} — {s['time']} — {cats}")

    new_state = build_watch_state(shows, merged_dates, watch.get("category", ""))
    changes = diff_state(old_state, new_state) if old_state else []
    labeled_changes = [f"{label}: {c}" for c in changes]
    return new_state, labeled_changes


def add_watch_cli(url, theatre="", screen="", date="", category="", time_filter=""):
    watches = load_json(WATCHES_FILE, [])
    event_code, region_slug, url_date = parse_bms_url(url)
    if not event_code or not region_slug:
        print("Error: Could not extract ET code or city from URL.")
        return
    label_parts = [event_code]
    if theatre:
        label_parts.append(theatre)
    if screen:
        label_parts.append(f"({screen})")
    new_entry = {
        "label": " — ".join(label_parts),
        "url": url,
        "theatre": theatre,
        "screen": screen,
        "date": date or url_date,
        "category": category,
        "time": time_filter,
    }
    watches.append(new_entry)
    save_json(WATCHES_FILE, watches)
    print(f"Added watch: {new_entry['label']} | City: {region_slug} | Date: {new_entry['date'] or 'ALL Available Dates'}")


def main():
    _RUN_CACHE.clear()
    print(f"[{datetime.now()}] BMS tracker run")
    watches = load_json(WATCHES_FILE, [])
    if not watches:
        print(f"  No watches defined in {WATCHES_FILE} — nothing to do.")
        return

    all_state = load_json(STATE_FILE, {})
    new_all_state = {}
    all_changes = []

    for watch in watches:
        wid = watch_id(watch)
        new_state, changes = run_watch(watch, all_state.get(wid, {}))
        new_all_state[wid] = new_state if new_state is not None else all_state.get(wid, {})
        all_changes.extend(changes)

    save_json(STATE_FILE, new_all_state)

    if not all_changes:
        print("  No changes across any watch.")
        return

    text = "BMS Alert!\n\n" + "\n".join(f"- {c}" for c in all_changes)
    print(f"  {len(all_changes)} change(s) — sending notifications")
    send_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, text)
    send_email(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_TO,
               f"BMS Alert: {len(all_changes)} change(s)", text)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        u = sys.argv[2]
        th = sys.argv[3] if len(sys.argv) > 3 else ""
        sc = sys.argv[4] if len(sys.argv) > 4 else ""
        dt = sys.argv[5] if len(sys.argv) > 5 else ""
        add_watch_cli(u, th, sc, dt)
    else:
        main()
