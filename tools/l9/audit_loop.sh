#!/bin/bash
# L9 G3 audit loop (pod): every time the run has 300 more episodes, write audit_<n>.json (tools/l9/gate.py: yield per
# definition, arm jumps, label parser, combination duplicates) and sheet_<n>.jpg (12 random successful episodes: head /
# wrist f0, middle, last call) for the frame review; flags (audit_flags.log) when the running yield drops below 30 %,
# any label fails the parser, a combination repeats, or > 5 % of the new episodes jumped. Ends with the STOP file.
# usage: audit_loop.sh <code dir> <run dir>
C=$1; R=$2
P=/data/harvest/venv_train/bin/python
mkdir -p $R/audit
last=0
while [ ! -f /data/harvest/out/l9/STOP ]; do
  n=$(find $R/collect -name meta.json 2>/dev/null | wc -l)
  if [ $((n - last)) -ge 300 ]; then
    last=$n
    cd $C && $P tools/l9/gate.py $R/collect $R/audit/audit_$n.json --per 10 > $R/audit/audit_$n.txt 2>&1
    $P tools/l9/sheet.py $R/collect $R/audit/sheet_$n.png --n 12 --seed $n --success >/dev/null 2>&1 \
      && $P -c "from PIL import Image; Image.open('$R/audit/sheet_$n.png').save('$R/audit/sheet_$n.jpg', quality=70)" \
      && rm -f $R/audit/sheet_$n.png
    $P - $R/audit/audit_$n.json >> $R/audit/audit_flags.log 2>&1 <<'EOF'
import json, sys
r = json.load(open(sys.argv[1]))
f = []
y = r["n_success"] / max(r["n_episodes"], 1)
if y < 0.30: f.append(f"yield {y:.2f}")
if r["parser"].get("bad"): f.append(f"parser bad {r['parser']['bad']}")
if r["combo_duplicates"]: f.append(f"combo dup {r['combo_duplicates']}")
if r["arm_jumps"] > 0.05 * r["n_episodes"]: f.append(f"arm jumps {r['arm_jumps']}")
print(sys.argv[1], "OK" if not f else "FLAG " + "; ".join(f))
EOF
  fi
  sleep 600
done
