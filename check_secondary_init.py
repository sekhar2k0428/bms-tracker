import json

with open("secondary_api_v1_mobile_secondary_init.json") as f:
    data = json.load(f)

def find_keys(obj, path="root", results=None, depth=0):
    if results is None:
        results = []
    if depth > 12:
        return results
    keywords = ("row", "seat", "area", "categor", "avail", "block", "layout")
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
        for i, item in enumerate(obj[:2]):
            find_keys(item, f"{path}[{i}]", results, depth + 1)
    return results

hits = find_keys(data)
print(f"{len(hits)} row/seat/area/category-related keys found:")
for p, v in hits[:60]:
    print(f"  {p} = {v}")

print(f"\nTop-level 'data' keys: {list(data.get('data', {}).keys())}")
