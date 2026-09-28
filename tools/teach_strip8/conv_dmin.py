"""E-PT-format pt training rows -> d-min rows (teach_pt.min_format.convert, the path B-D's rows were made by).
usage: python conv_dmin.py <train_pt.jsonl> <out dir>  -> <out dir>/train_d-min.jsonl"""
import json
import os
import sys

from harvest.teach_pt import min_format as MF

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
print("CONV " + json.dumps(MF.convert(src, out, "d-min", "train_d-min.jsonl")))
