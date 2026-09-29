"""G-px rows from the E-DIST8 D rows: training (b1 train_d-min) and evaluation (x_dev / x_ood_h d-min clean).
usage: python build_gpx.py <out dir>"""
import json
import sys

from harvest.teach_strip8 import gpx as G

out = sys.argv[1]
res = {"train": G.build("/data/harvest/out/dist8/data_b1/train_d-min.jsonl", out, "train_g-px"),
       "x_dev": G.build("/data/harvest/out/dist8/data_x/x_dev_d-min_clean.jsonl", out, "x_dev_g-px"),
       "x_ood_h": G.build("/data/harvest/out/dist8/data_x/x_ood_h_d-min_clean.jsonl", out, "x_ood_h_g-px")}
print("BUILD_GPX " + json.dumps(res))
