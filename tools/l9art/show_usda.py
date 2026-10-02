"""Print the USDA of one fixture: python tools/l9art/show_usda.py <family> <seed>"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9art import fixtures as FX  # noqa: E402

print(FX.usda(FX.sample(sys.argv[1], int(sys.argv[2]))))
