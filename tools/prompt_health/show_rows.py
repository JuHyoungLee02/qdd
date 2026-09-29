"""Print compact rows of a run_dyn.py JSONL (pod helper; read-only).
usage: python tools/prompt_health/show_rows.py <jsonl> [test] [raw_chars]"""
import json
import sys

KEYS = ("test", "snap", "variant", "temp", "rep", "valid", "errors", "truth", "state", "grasp_state", "execution",
        "intent", "command_raw", "command", "gate", "claims_raw", "edit_dp", "edit_gripper", "dp", "api_error",
        "latency_s", "in_tok", "out_tok")


def main():
    path = sys.argv[1]
    test = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    for line in open(path):
        r = json.loads(line)
        if test and r["test"] != test:
            continue
        print(json.dumps({k: r[k] for k in KEYS if k in r}))
        if n:
            print("   RAW:", r["raw"][:n].replace("\n", " "))


if __name__ == "__main__":
    main()
