"""Print lines a..b of an episode's measured history (result.json). usage: python dist8_hist.py <result.json> <a> <b>"""
import json
import sys

h = json.load(open(sys.argv[1]))["history"]
for ln in h[int(sys.argv[2]):int(sys.argv[3])]:
    print(ln[:260])
