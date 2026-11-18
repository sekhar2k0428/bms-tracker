"""
Properly extracts window.__INITIAL_STATE__ as real JSON (brace-matched,
not string-terminator-guessed) from the saved seat pages, then
recursively searches it for any key/value that looks seat-related.
"""

import json


def extract_initial_state(html):
    marker = "window.__INITIAL_STATE__ = "
    start = html.find(marker)
    if start == -1:
        return None
    start += len(marker)
    brace_start = html.find("{", start)
    if brace_start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    i = brace_start
    for i in range(brace_start, len(html)):
        c = html[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
    json_text = html[brace_start:i + 1]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"  JSON parse failed: {e}")
        with open("failed_state.json", "w") as f:
            f.write(json_text)
        return None


def find_seat_keys(obj, path="root", results=None, depth=0):
    if results is None:
        results = []
    if depth > 12:
        return results
    keywords = ("seat", "row", "layout", "block", "category", "avail")
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}"
            if any(kw in k.lower() for kw in keywords):
                preview = json.dumps(v)[:200] if not isinstance(v, (dict, list)) else f"<{type(v).__name__} len={len(v)}>"
                results.append((new_path, preview))
            find_seat_keys(v, new_path, results, depth + 1)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj[:3]):
            find_seat_keys(item, f"{path}[{idx}]", results, depth + 1)
    return results


for label, fname in [("AMB", "amb_seatpage.html"), ("Allu", "allu_seatpage.html")]:
    print(f"\n{'=' * 20} {label} {'=' * 20}")
    try:
        html = open(fname).read()
    except FileNotFoundError:
        print(f"  {fname} not found — run probe_seatpage.py first")
        continue

    state = extract_initial_state(html)
    if state is None:
        print("  Could not extract/parse __INITIAL_STATE__")
        continue

    with open(f"{label.lower()}_state.json", "w") as f:
        json.dump(state, f, indent=2)
    print(f"  Parsed OK, top-level keys: {list(state.keys())}")

    hits = find_seat_keys(state)
    if hits:
        print(f"  {len(hits)} seat/row/layout-related keys found:")
        for path, preview in hits[:40]:
            print(f"    {path} = {preview}")
    else:
        print("  No seat/row/layout-related keys found in this state blob.")
