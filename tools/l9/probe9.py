"""L9 wide reach probe (pod, Isaac): = harvest.teach_l8d.probe_reach (right arm, top-down columns) on a wider grid
than the L8-D gate (y -0.52..+0.08 instead of -0.40..-0.06, x 0.30..0.68), so L9 layouts can use the arm's real
band (the left arm uses the y-mirror). usage: python -m tools.l9.probe9 --out reach_wide.json"""
from harvest.teach_l8d import probe_reach as PR
from harvest.teach_l8d import spec as S

S.GATE_Y = (-0.52, -0.46, -0.40, -0.32, -0.23, -0.15, -0.06, 0.02, 0.08)
PR.XS = [round(0.30 + 0.02 * i, 2) for i in range(20)]  # 0.30 .. 0.68

if __name__ == "__main__":
    PR.main()
