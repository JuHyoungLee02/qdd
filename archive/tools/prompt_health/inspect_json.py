"""Print the top-level keys (and short values) of a JSON file or the first row of a JSONL file (pod helper for the
prompt health check; read-only). usage: python tools/prompt_health/inspect_json.py <file> [max_chars]"""
import json
import sys


def main():
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 160
    with open(path) as f:
        d = json.loads(f.readline()) if path.endswith(".jsonl") else json.load(f)
    items = d.items() if isinstance(d, dict) else enumerate(d[:3])
    for k, v in items:
        if isinstance(v, list) and v and isinstance(v[0], dict):
            print(f"{k}: list[{len(v)}] of dict keys={sorted(v[0])[:40]}")
            print(f"   first: {json.dumps(v[0])[:n * 4]}")
        elif isinstance(v, dict):
            print(f"{k}: dict keys={sorted(v)[:40]} {json.dumps(v)[:n]}")
        else:
            print(f"{k}: {json.dumps(v)[:n]}")


if __name__ == "__main__":
    main()
