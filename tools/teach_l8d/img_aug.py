"""Augment a built JSONL's images (harvest.teach_l8d.img_aug). usage: python img_aug.py <src.jsonl> <dst.jsonl> <img dir>"""
import json
import sys

from harvest.teach_l8d.img_aug import aug_rows

print(json.dumps(aug_rows(*sys.argv[1:4])))
