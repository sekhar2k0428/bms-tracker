import main as m

watches = m.load_json("watches.json", [])
for w in watches:
    event_code, region_slug, _ = m.parse_bms_url(w["url"])
    region_code, lat, lon, geohash = m.resolve_region(region_slug)
    data = m.fetch_showtimes(event_code, None, region_code, region_slug, lat, lon, geohash)
    if not data:
        print(w["label"], "- no data")
        continue
    shows = [s for s in m.parse_shows(data) if m.matches_filters(s, w.get("theatre", ""), "")]
    print(f"\n=== {w['label']} (event {event_code}) ===")
    for s in shows:
        print(f"  {s['time']} | date={s['date']} | sessionId={s['session_id']}")
