"""Print the key structure of one R2 view row (pod helper for the prompt health check; read-only).
usage: python tools/prompt_health/inspect_r2.py <view jsonl> [row index]"""
import json
import sys


def walk(d, pre="", depth=0):
    if depth > 4:
        return
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)) and not (isinstance(v, list) and v and not isinstance(v[0], (dict, list))):
                print(f"{pre}{k}: {type(v).__name__}({len(v)})")
                if isinstance(v, dict) and k != "pred":
                    walk(v, pre + "  ", depth + 1)
            else:
                s = json.dumps(v)
                print(f"{pre}{k}: {s[:160]}")


def main():
    path = sys.argv[1]
    i = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    with open(path) as f:
        for j, line in enumerate(f):
            if j == i:
                walk(json.loads(line))
                break


if __name__ == "__main__":
    main()
