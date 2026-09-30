"""Pipeline overview (2026-09-30, redrawn per user request): same picture as paper_v2 Fig. 1.
Runtime row (upper VLM -> coordinate conversion -> joystick VLA -> robot) above the offline row
(data -> training -> evaluation), one thin dashed feedback line, four role colours.
Run: MPLCONFIGDIR=D:/tools/mplcache PYTHONPATH=D:/tools/pylib python docs/design/pipeline_2026-09-30.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "paper_v2", "figures", "src", "make_figs_v2.py")

if __name__ == "__main__":
    tmp = tempfile.mkdtemp(dir=os.environ.get("MPLCONFIGDIR"))
    subprocess.run([sys.executable, "-c",
                    f"import sys; sys.argv=['x', r'{tmp}']; import runpy; "
                    f"g = runpy.run_path(r'{SRC}', run_name='lib'); g['f1_overview']()"], check=True)
    shutil.copy(os.path.join(tmp, "f1_overview.png"), os.path.join(HERE, "pipeline_2026-09-30.png"))
    shutil.rmtree(tmp, ignore_errors=True)
