"""L9 v2 diagnosis: a sub-plan of chosen seeds from a plan json, all in one job (pure).
usage: python tools/l9/diag/sub_plan.py <plan.json> <out.json> <job name> <seed,seed,...>"""
import json
import sys


def main():
    src, dst, job, seeds = sys.argv[1], sys.argv[2], sys.argv[3], {int(s) for s in sys.argv[4].split(",")}
    rows = [dict(r, job=job) for r in json.load(open(src)) if int(r["seed"]) in seeds]
    json.dump(rows, open(dst, "w"))
    print(len(rows), "rows", sorted(r["seed"] for r in rows))


if __name__ == "__main__":
    main()
