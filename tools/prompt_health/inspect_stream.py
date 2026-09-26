"""Print result.json stream answers (first n) and the call list keys of one probe stream episode (pod helper for the
prompt health check; read-only). usage: python tools/prompt_health/inspect_stream.py <result.json> [n]"""
import json
import sys


def main():
    d = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    s = d["stream"]
    print("stream keys", sorted(s), "sites", json.dumps(s.get("sites"))[:300])
    for a in s["answers"][:n]:
        print(json.dumps(a)[:1500])
    for c in d["calls"][:n]:
        print(json.dumps(c.get("parsed"))[:1200])


if __name__ == "__main__":
    main()
