"""Convert an E-PT-format arm file into E-DIST8 minimal-request training rows (harvest.teach_pt.min_format.convert).
usage: python convert_min.py <src jsonl> <out dir> <track r-min|d-min|h-min> <dst file name>"""
import json
import os
import sys

from harvest.teach_pt import min_format as MF

src, out, track, dst = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
print(json.dumps(MF.convert(src, out, track, dst)))
