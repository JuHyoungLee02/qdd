# L9v2-general — integrated A/B, all general elements ON vs current (pre-registration, 2026-10-03)

Purpose (user 10-03 03h): before the general production (L9v2-general) starts, run one paired A/B on all four robots.
B turns on every general element at once. A is the current way. Production starts only if B is not worse.
This file was written before any result. The rules below do not change after the runs start.

## Arms
Both arms use the **same code copy** (`/data/harvest/code_l9_gab_<sha>` = dev `<sha>`, recorded in the Results section). Every element
in B is opt-in, so A with the switches off runs the current production path. Common to both arms:
`L9V2_COLLIDERS=1` (production), `L9_TIMING=1`, the production head-camera coin (`HCAM_ON` in each arm dir), the
camera rule r2-cams (each robot's own cameras; not under test, user decision) and R1 Pro's dev defaults (lean 0.8,
ready pose, carry clearance, reverse approach, grasp-link check).

| element | switch (B only) | source |
|---|---|---|
| GraspGen-X candidates + label rule ggx_v1 | `L9V2_GGX_GRASPS=/data/harvest/l9v2/grasps_ggx` `L9V2_GGX_TESTED=/data/harvest/l9v2/tested_ggx` `L9V2_SEL=ggx_v1` | dev 59c3a29 (owner af9cdf1e) |
| common grip layer (measured free gap, max-over-fingers grip, spec r4-grip) | `L9_GRIP_LAYER=1` | dev 238b57b (owner ade5e035) |
| per-robot env profile (autotune ranges; a robot with no profile keeps its current draw) | `L9_ENV_PROFILE=1` | dev fed711c + 4 profiles dev 8ee26d0 (autotune a8caa656) |
| carry keeps the object in view | `L9_CARRY_INVIEW=1` | dev ef829ad |
| common executor (carry height range, reverse straight approach, grasp-link check, place-aware grasp, lift_clear skip, joint-margin ready pose, both closing-axis signs) | `L9_COMMON_EXEC=1` | dev ed4dab8 + 44a3695 + 6e8f535 retreat axis (owner a9ea58a9) |
| place round-trip prescription: P0 (carry-height meaning matched) + (a) tolerance place + (d) hysteresis + (b) place-ready evidence | `L9V2_PLACE_ABOVE=1` (P0) `L9V2_PLACE_TOL=1` (a) `L9V2_PLACE_HYST=1` (d); (b) = build flag `build_v2 --rationale on` (label text only, no sim effect) | ef4728c merged into dev (owner ab86d5b7) |
| high/shelf place share lever (extra high fixture draw per scene; plan reweighting is plan-time only, unused here) | `L9_HIGH_SHARE=0.10` | dev (work of a747477b, committed by this A/B) |

Notes fixed before the runs:
- GGX caches exist only for ffw_sg2 and franka (sim-tested only for the GGX A/B objects). R1 and G1 run ggx_v1 on
  antipodal candidates only (`GGXDBG ... ggx_file=missing`). This is what general production would do today, so B keeps
  it on for every robot (no per-robot switch, L9_PRINCIPLES "one way for every robot").
- G1 team switches that are not on dev (`L9V2_G1_*`) are in neither arm. The short-arm mechanisms `L9_EXEC_TABLE` / `L9_CSPACE_READY` (dev 84e45f2c, own G1/R1 A/B running) are in neither arm.
- Known label defect in both arms (external review 1): some left-arm rows' prompt says "You control the right arm".
  It changes label text only, not the sim outcome, so it does not bias this comparison; it is fixed generally elsewhere.
- **Revision 2 (06:00 KST, before any main-A/B episode; coordinator decision)**: P0 + (a)(d) (`L9V2_PLACE_ABOVE/TOL/HYST`)
  are taken OUT of this A/B. Their own K0/K4 smoke (same seeds, 30 rows each, fe08 /data/harvest/out/l9/posc/) failed:
  K0 3/10 success, GT ABA 0/7 vs K4 2/10, GT ABA 2/7 (cause: P0 carry_over height vs the carry_up branch, (a) tolerance
  edge). After the owner's fix and a passing re-smoke, the place prescription gets a short separate confirmation A/B on
  top of this B. The general spec is frozen only after both A/Bs. Main run: code dev b69a765, B env =
  GGX + GRIP_LAYER + ENV_PROFILE + CARRY_INVIEW + COMMON_EXEC + HIGH_SHARE=0.10; 4 robots × 32 rows (production-rendered
  rows), 5 rows per job (one Isaac boot per job; boots take 10–13 min under load), 64 jobs.
- **Revision 3 (07:1x KST, main run half done, no verdict looked at)**: the b69a765 copy lacked the env-profile
  CONSUMER in world9 (919c2ab2: per-episode body/stance cell for every robot with a profile). B drew surface heights
  from the profile but kept the old body limits, so R1 B skipped 6/7 rows (world9 DIAG 8, "surface above its torso
  reach"; A 0). The run in `gab/main` is stopped (lanes finish their job, nothing killed) and kept as a bug baseline.
  `gab/main2` reruns BOTH arms of all 4 robots on the same rows (main's plan after the ext_p split, 76 jobs) with code
  dev b4fe4a4c (contains 919c2ab2). Checked in B.env: none of `L9V2_PLACE_*`, `L9_CSPACE_READY`, `L9_PLACE_FREE`,
  `L9_IK_SEED`, `L9_EXEC_TABLE`, `L9_IK_SEEDS_CANDIDATE` is set (all opt-in, default off in b4fe4a4c); B.env = A.env +
  GGX (3 vars) + GRIP_LAYER + CARRY_INVIEW + COMMON_EXEC + ENV_PROFILE + HIGH_SHARE=0.10. The verdict is computed on
  main2 only.
- The smoke test (below) runs B without P0. The main A/B runs only with P0 included (coordinator 10-03: no
  trajectory-mode mix inside one spec).

## Rows and seeds
- Sources (train split, single-arm pick/place definitions; bimanual, handover and articulated rows excluded):
  ffw_sg2 `pilot1/plan_pilot_v2.json`, franka_mast `pilotF/plan_pilot_v2.json`, r1pro `r1sweep/plan_pilot_v2.json`,
  g1 `g1b/gate1/plan_pilot_v2.json` (all under `/data/harvest/l9v2`).
- `tools/l9/gab/gab_select.py <ab dir> 30 ...`: **30 rows per robot** (14 families, 30 definitions for AIW/Franka/R1,
  13 families for G1), round-robin over families, then definitions inside a family,
  arms as the plan drew them (no forced left/right balance), order by a fixed hash of the seed. One row per job. A and B
  get the same rows and seeds.
- The queue interleaves robots and puts A and B of a row next to each other, so both arms see the same cards and the
  same time of day. Lanes: `tools/l9/gab/gab_lane.sh` (per-arm env file `<ab>/{A,B}.env`).
- Scene skips (no episode, `skipped.json`) are not failures and leave the denominator (robot gate rule (a)). If a robot
  ends with < 20 rendered episodes in either arm, add rows (next 10 from the same selection) before judging.

## Metrics (`tools/l9/gab/gab_report.py`)
- Success = `success` and `max_dq_rad <= 0.04` (production gate). Per robot, per family, paired by seed.
- Left/right (user 10-03, revision 1 before any result): the general spec does not force symmetric or centred placement;
  scenes come from each robot's own cameras and reach, and the left/right balance is made at BUILD time (thin the
  larger arm, top up the smaller one). So the left/right check applies to the built set, not to raw production; in
  this A/B the left share is reported for reference only and is not part of the verdict. B contains no forcing switch.
- Diversity of successful episodes (robot_gate9.profile): approach-family shares, image rotation bins, left share (reference only),
  IQR of support height and of grasp x / y, high/shelf place share.
- Place round trip (ABA): share of episodes (that reach the carry phase) whose GT carry steps (labels.jsonl "step" in carry_up/carry_over/lower_open, qmon9.aba_oscillations) contain h[k] = h[k-2] != h[k-1]
  (definition in docs/research/place_oscillation_2026-10-03.md, function from the owner ab86d5b7). The result.json "knocked" field over-counts on multi-step definitions (external review 1) and is not used.
- Proof that each switch ran: spec_version `...r4-grip` on B metas, `GGXDBG load` lines, common-executor and
  carry-in-view log lines.

## Verdict rule (pre-registered)
B passes for a robot when all hold:
1. B success rate >= A − 10 pp, and no family where A has >= 2 successes and B has 0.
2. Diversity not narrower: `robot_gate9.diversity_check(B, ref=A)` ok (top family <= max(50 %, A top + 10 pp), every
   family A uses at >= 5 % is used, rotation bins >= 0.8 × A, IQRs >= 0.8 × A,
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
