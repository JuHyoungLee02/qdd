"""Pre-registration hashes for E-first judgment sections (E §1.7)."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/design/E-first-experiments.md"
OUT = ROOT / "docs/stage3/prereg.json"
SECTIONS = ["### 2.7", "### 2A.6", "### 3.7", "### 4.8", "### 5.6"]


def section_hash(md_text: str, heading: str) -> str:
    lines = md_text.replace("\r\n", "\n").split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(heading)), None)
    if start is None:
        raise KeyError(heading)
    body = []
    for l in lines[start + 1:]:
        if l.startswith("## ") or l.startswith("### "):
            break
        body.append(l)
    return hashlib.sha256("\n".join(body).strip().encode("utf-8")).hexdigest()


def current() -> dict:
    text = DOC.read_text(encoding="utf-8")
    return {s: section_hash(text, s) for s in SECTIONS}


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.write:
        now = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%MZ"], capture_output=True, text=True).stdout.strip()
        OUT.write_text(json.dumps({"written_utc": now, "hashes": current()}, indent=1), encoding="utf-8")
        print("written", now)
        return 0
    saved = json.loads(OUT.read_text(encoding="utf-8"))["hashes"]
    bad = [s for s, h in current().items() if saved.get(s) != h]
    print("OK" if not bad else f"CHANGED {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
