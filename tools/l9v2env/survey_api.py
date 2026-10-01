"""L9 v2 asset survey (pod, stdlib): live counts of Poly Haven (textures / HDRIs / models + model file formats) and
ambientCG (materials by displayCategory). usage: python3 survey_api.py OUT.json"""
import json
import sys
import urllib.request
from collections import Counter


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qdd-l9v2-survey"}), timeout=120) as r:
        return json.loads(r.read())


def main():
    out = {}
    for t in ("textures", "hdris", "models"):
        a = get(f"https://api.polyhaven.com/assets?t={t}")
        cats = Counter(c for r in a.values() for c in (r.get("categories") or []))
        out[f"ph_{t}"] = {"n": len(a), "top_categories": cats.most_common(40)}
        if t == "models":
            fm = Counter()
            for k in sorted(a)[:10]:
                fm.update(get(f"https://api.polyhaven.com/files/{k}").keys())
            out["ph_model_file_keys_first10"] = dict(fm)
            out["ph_models_ids"] = sorted(a)
    acg, off = [], 0
    while True:
        j = get(f"https://ambientcg.com/api/v2/full_json?type=Material&limit=250&offset={off}&include=displayData")
        f = j.get("foundAssets") or []
        acg += f
        if len(f) < 250:
            break
        off += 250
    out["acg_materials"] = {"n": len(acg), "by_category": Counter(r.get("displayCategory") for r in acg).most_common()}
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print(json.dumps({k: v["n"] for k, v in out.items() if isinstance(v, dict) and "n" in v}))


if __name__ == "__main__":
    main()
