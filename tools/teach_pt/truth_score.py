"""E-PT gate G0 (a): score an arm's own truth answers through the runtime path (harvest.teach_pt.metrics) -- the
ceiling of the interface's goal computation (pt: depth resolver + robot mask). Rows without the arm's label are
skipped (counted). usage: python truth_score.py <data jsonl> <arm>"""
import json
import sys

from harvest.teach_pt import metrics as M

rows = [json.loads(x) for x in open(sys.argv[1])]
arm = sys.argv[2]
ctrl = [r for r in rows if r["kind"] == "control"]
sc = [M.score(r, r["answer"], arm) for r in ctrl if not r.get("label_missing")]
print("TRUTH_SCORE " + json.dumps({"arm": arm, "n_control": len(ctrl), "n_scored": len(sc),
                                   "label_missing": sum(bool(r.get("label_missing")) for r in ctrl),
                                   **M.summarize(sc)}))
