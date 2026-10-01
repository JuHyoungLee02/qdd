"""Pilot frame sheets per robot / head-camera mode (pod, venv python): symlink the episodes of each group into
<run>/sheet_<group>/<family>/<episode> and run tools/l9/sheet.py on it (head f0 | wrist f0 | head mid | wrist mid |
head last), successes only and all episodes.
usage: python tools/l9r/sheets.py <run dir> <code dir> [--n 12]"""
import glob
import json
import os
import subprocess
import sys


def main():
    run, code = sys.argv[1], sys.argv[2]
    n = sys.argv[sys.argv.index("--n") + 1] if "--n" in sys.argv else "12"
    groups = {}
    for m in glob.glob(os.path.join(run, "collect", "**", "meta.json"), recursive=True):
        d = json.load(open(m))
        g = f"{d.get('robot') or 'ffw_sg2'}_{((d.get('head_cam') or {}).get('draw') or {}).get('mode', 'std')}"
        groups.setdefault(g, []).append(os.path.dirname(m))
    py = sys.executable
    for g, eps in sorted(groups.items()):
        root = os.path.join(run, f"sheet_{g}")
        for e in eps:
            fam = os.path.join(root, os.path.basename(os.path.dirname(e)))
            os.makedirs(fam, exist_ok=True)
            link = os.path.join(fam, os.path.basename(e))
            if not os.path.islink(link):
                os.symlink(e, link)
        for tag, extra in (("succ", ["--success"]), ("all", [])):
            out = os.path.join(run, f"sheet_{g}_{tag}.png")
            subprocess.run([py, os.path.join(code, "tools", "l9", "sheet.py"), root, out, "--n", n, "--seed", "1"] + extra,
                           check=False)
            print(g, tag, out, len(eps))


if __name__ == "__main__":
    main()
