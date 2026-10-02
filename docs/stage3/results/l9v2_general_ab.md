# L9v2-general — integrated A/B, all general elements ON vs current (pre-registration, 2026-10-03)

Purpose (user 10-03 03h): before the general production (L9v2-general) starts, run one paired A/B on all four robots.
B turns on every general element at once. A is the current way. Production starts only if B is not worse.
This file was written before any result. The rules below do not change after the runs start.

## Arms
Both arms use the **same code copy** (`/data/harvest/code_l9_gab_<sha>`, sha in the Results section). Every element
in B is opt-in, so A with the switches off runs the current production path. Common to both arms:
`L9V2_COLLIDERS=1` (production), `L9_TIMING=1`, the production head-camera coin (`HCAM_ON` in each arm dir), the
camera rule r2-cams (each robot's own cameras; not under test, user decision) and R1 Pro's dev defaults (lean 0.8,
ready pose, carry clearance, reverse approach, grasp-link check).

| element | switch (B only) | source |
|---|---|---|
| GraspGen-X candidates + label rule ggx_v1 | `L9V2_GGX_GRASPS=/data/harvest/l9v2/grasps_ggx` `L9V2_GGX_TESTED=/data/harvest/l9v2/tested_ggx` `L9V2_SEL=ggx_v1` | dev 59c3a29 (owner af9cdf1e) |
| common grip layer (measured free gap, max-over-fingers grip, spec r4-grip) | `L9_GRIP_LAYER=1` | 724a10d..5e944ed (owner ade5e035) |
| per-robot env profile (autotune ranges; a robot with no profile keeps its current draw) | `L9_ENV_PROFILE=1` | e5e7b52 (grip layer) + profiles from autotune (a8caa656) |
| carry keeps the object in view | `L9_CARRY_INVIEW=1` | dev ef829ad |
| common executor (carry height range, reverse straight approach, grasp-link check, place-aware grasp, lift_clear skip, joint-margin ready pose, both closing-axis signs) | `L9_COMMON_EXEC=1` | dev ed4dab8 + 44a3695 (owner a9ea58a9) |
| place round-trip prescription: P0 (carry-height meaning matched) + (a) tolerance place + (d) hysteresis + (b) place-ready evidence | switches named by the owner | owner ab86d5b7, sha added below when ready |

Notes fixed before the runs:
- GGX caches exist only for ffw_sg2 and franka (sim-tested only for the GGX A/B objects). R1 and G1 run ggx_v1 on
  antipodal candidates only (`GGXDBG ... ggx_file=missing`). This is what general production would do today, so B keeps
  it on for every robot (no per-robot switch, L9_PRINCIPLES "one way for every robot").
- G1 team switches that are not on dev (`L9V2_G1_*`) are in neither arm.
- The smoke test (below) runs B without P0. The main A/B runs only with P0 included (coordinator 10-03: no
  trajectory-mode mix inside one spec).

## Rows and seeds
- Sources (train split, single-arm pick/place definitions; bimanual, handover and articulated rows excluded):
  ffw_sg2 `pilot1/plan_pilot_v2.json`, franka_mast `pilotF/plan_pilot_v2.json`, r1pro `r1sweep/plan_pilot_v2.json`,
  g1 `g1b/gate1/plan_pilot_v2.json` (all under `/data/harvest/l9v2`).
- `tools/l9/gab/gab_select.py <ab dir> 30 ...`: **30 rows per robot** (14 families, 30 definitions for AIW/Franka/R1,
  13 families for G1), round-robin over families, definitions inside a family, arms alternating L/R for two-armed
  robots (15/15), order by a fixed hash of the seed. One row per job. A and B get the same rows and seeds.
- The queue interleaves robots and puts A and B of a row next to each other, so both arms see the same cards and the
  same time of day. Lanes: `tools/l9/gab/gab_lane.sh` (per-arm env file `<ab>/{A,B}.env`).
- Scene skips (no episode, `skipped.json`) are not failures and leave the denominator (robot gate rule (a)). If a robot
  ends with < 20 rendered episodes in either arm, add rows (next 10 from the same selection) before judging.

## Metrics (`tools/l9/gab/gab_report.py`)
- Success = `success` and `max_dq_rad <= 0.04` (production gate). Per robot, per family, paired by seed.
- Diversity of successful episodes (robot_gate9.profile): approach-family shares, image rotation bins, left share,
  IQR of support height and of grasp x / y, high/shelf place share.
- Place round trip (ABA): share of episodes whose held-phase height commands contain h[k] = h[k-2] != h[k-1]
  (definition in docs/research/place_oscillation_2026-10-03.md; the function comes from the owner ab86d5b7).
- Proof that each switch ran: spec_version `...r4-grip` on B metas, `GGXDBG load` lines, common-executor and
  carry-in-view log lines.

## Verdict rule (pre-registered)
B passes for a robot when all hold:
1. B success rate >= A − 10 pp, and no family where A has >= 2 successes and B has 0.
2. Diversity not narrower: `robot_gate9.diversity_check(B, ref=A)` ok (top family <= max(50 %, A top + 10 pp), every
   family A uses at >= 5 % is used, rotation bins >= 0.8 × A, left share 40–60 % for two-armed robots, IQRs >= 0.8 × A,
   high share >= 0.8 × A when A >= 2 %).
3. Episodes over the 0.04 rad step gate: B <= A + 1.
4. ABA share: B <= A + 2 pp (P0 is expected to lower it).
5. >= 20 rendered episodes per arm.

Overall PASS = all four robots pass and the pooled success rate B >= A − 5 pp. PASS → the L9 owner freezes
L9v2-general and starts general production. FAIL → the report names the robot and the failing item; the element
behind it is found from the logs (no rerun of the same arms to fish for a pass).

## Smoke (B without P0)
2 rows per robot, B only, `/data/harvest/l9v2/gab/smoke1`, e9f3b GPU 0/1. Goal: nothing crashes with all switches on.

## Results
(pending)
