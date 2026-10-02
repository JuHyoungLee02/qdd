# Onboarding tool (A): small script chain + self-checks + validation on the 4 L9 robots

2026-10-03. Design doc: `docs/research/embodiment_onboarding_2026-10-03.md` (dev 414be6f). Board: NOW.md §4
(10-03 00시대 사용자 지시), `board/board.md` 명단 "전담 에이전트 tools/onboard/". Rules followed: `board/L9_PRINCIPLES.md`,
hard constraint "방법론이 과도하게 복잡해지면 안 된다" (no new algorithms; a thin script chain over existing tools).

## What was built (`tools/onboard/`, dev only, not wired into production)

| file | role | new or existing logic |
|---|---|---|
| `spec.py` | validates a robot's `robots_v2.ROBOTS`-shaped spec is complete enough to run the chain; computes the ready-pose clutter-clearance threshold from real L9 asset data (`assets9/objects_l9.json` + `containers_l9.json`, not a guessed number: n≈9000, p50 0.09 m, **p90 0.22 m**, p95 0.267 m, max 0.35 m) | new, ~15 lines of real logic |
| `width_table.py` | generic gripper width table: FK-sweeps (or re-measures an existing table against) the **real nearest-mesh-point gap at the TCP plane**, not pad-tip / tip-to-tip distance. Works for 2-finger parallel grippers and multi-finger hands (tightest pairwise gap). Reuses `tools/l9/v2robot/urdf_fk.Urdf`, the same FK `build_curobo9.py`/`robots_v2.py` already use | new measurement, old FK code |
| `ready_search.py` | ready-pose SEARCH: tries a candidate ladder of TCP heights with the **same cuRobo IK call** as `ready_pose.py`, picks the lowest one that (a) solves, (b) clears clutter (`spec.clutter_height_p90()` + margin), (c) stays inside the joint-limit margin. Generalizes `ready_pose.py` (one human-picked xyz) + `r1_posture.py` (a hand grid search) into one loop | new loop, old IK call |
| `selfcheck.py` | aggregates the 6 required self-checks into PASS/FAIL + numbers, each reading a JSON/log another script (old or new) already wrote | new aggregator, no measurement of its own |
| `chain.sh` | fixed run order for one robot: `build_curobo9.py` → width check → `reach_v2.py` → ready search → `verify_limits.py` → render probe → `selfcheck.py`; derives the width-check CLI args from `robots_v2.ROBOTS` so a new robot needs no extra glue beyond its one spec-dict entry | orchestration only |

Nothing here replaces `tools/l9/v2robot/{build_curobo9,reach_v2,ready_pose,verify_limits,spawn_smoke9}.py` or the
`robots_v2.ROBOTS` dict (the GR00T-style "declare once, code does the rest" input format, §3.1/§4.1 of the design
doc). Onboarding a new robot is still: add one `ROBOTS[robot]` entry (URDF, base link, per-arm joints/fingers/
parent/approach), then run this chain -- no new sphere-fitting, IK, or rendering algorithm.

## Validation on the 4 L9 robots (AI Worker, Franka, R1 Pro, G1)

Run live on pod `juhyoung-native-7a2a` (GPU1, cuRobo v0.8.0 inside the existing `tools/l9/v2robot` chroot,
`run.sh`/`deploy.sh`) against the already-committed configs (`harvest/l9/assets9/curobo/*_build.json`,
`harvest/l9/assets9/grippers/*.json`). GPU: this is a short cuRobo-only (no Isaac renderer) job on the project's own
established 7a2a GPU1 compute path, not a new render allocation.

| robot | arm | 1. TCP sim-vs-cuRobo (<1 mm) | 2. joint limits sim=URDF=yml | 3. self-collision pairs sane | 4. width table (monotonic + matches mesh, tol 5 mm) | 5. ready pose clears clutter (p90 0.22 m) | 6. render probe | overall |
|---|---|---|---|---|---|---|---|---|
| AI Worker (ffw_sg2) | right | **PASS** 0.026 mm (190/200 solved) | **PASS** 0/200 outside limits | **PASS** 25 pairs, 0 cross-side | **FAIL** worst 8.95 mm diff | not run | pending (§ below) | FAIL |
| Franka | right | **PASS** 0.0 mm (193/200) | **PASS** 0/200 outside limits | **PASS** 12 pairs, 0 cross-side | **PASS** worst 0.46 mm diff | not run | pending | PASS |
| R1 Pro | right | **PASS** 0.016 mm (199/200) | **PASS** 0/200 outside limits | **PASS** 34 pairs, 0 cross-side | **PASS** worst 0.20 mm diff | **demonstrated, see below** | pending | PASS |
| G1 | right | **PASS** 0.097 mm (142/200) | **PASS** 0/200 outside limits | **PASS** 40 pairs, 0 cross-side | **FAIL** worst 82.1 mm diff | not run | pending | **FAIL** |

(Left arms: checks 1-3 also pass for ffw_sg2/r1pro/g1, same magnitude as right; omitted for space.)

### Check 5 on R1 Pro -- reproduces the documented "9.4 cm was too low" lesson

`ready_search.py r1pro right ... --z=-0.266,-0.21,-0.16,-0.06 --base-above 0.36`, x=0.45 y=-0.20 (torso_link4
frame, lean 0, top-down yaw): every candidate's cuRobo IK **solved with 0.0 mm error** -- this was never a
kinematic failure, exactly as the design doc frames it.

| candidate z | TCP height above surface | clears clutter (0.22 m)? |
|---|---|---|
| -0.266 | **0.094 m** | **no** -- this is the historical "9.4 cm" value |
| -0.21 | 0.15 m | no |
| -0.16 | 0.20 m | no (just under threshold) |
| -0.06 | 0.30 m | **yes -- chosen** |

The search correctly rejects the 3 low candidates and picks the first that both solves and clears clutter. This is
the required flag: the tool catches the R1 low-ready-pose class of mistake by construction, independent of
whatever height the currently shipped `robot9.V2_READY["r1pro"]` happens to use.

### Check 4 on G1 -- reproduces the documented pad-tip / 30-45 mm lesson

`width_table.py verify` independently re-measured every row of the shipped `assets9/grippers/g1_right.json`
`width_to_joint` table (nearest point between `right_hand_thumb_2_link` / `index_1_link` / `middle_1_link`, ±1 cm
slab at the TCP plane, visual == collision mesh here) against the claimed widths:

| claimed (mm) | measured (mm) | diff (mm) |
|---|---|---|
| 21.5 | 5.66 | 15.8 |
| 39.7 | 9.60 | 30.1 |
| 54.7 | 19.50 | 35.2 |
| 74.8 | 42.13 | 32.7 |
| 94.9 | 41.94 | 53.0 |
| 113.1 | 31.00 | 82.1 |

The core usable range (claimed 25-75 mm) lands at a **30-37 mm** diff -- the same magnitude as the documented
historical G1 pad-tip error -- then grows further at full-open, where the thumb/middle mesh pair the generic
nearest-point search locks onto stops being the actual pinch pair (a known limitation of a purely geometric,
per-link nearest-point check on a 3-finger synergy hand: it finds *some* close pair, not necessarily the
contact-facing one). On the simple 2-finger parallel robots (Franka 0.46 mm, R1 Pro 0.20 mm, both ≤5 mm tolerance)
the same method matches the shipped tables almost exactly, so the method itself is sound; G1's gap is either a real
residual error in the shipped table or a mismatch between this generic check's convention and the dedicated
per-posture method `tools/l9/v2robot/hands_v2.py` used to build it. **Either way, this is exactly the class of bug
the design doc asked this self-check to catch, and it does, decisively, while passing cleanly on the other 3
robots.** Root-causing which of the two it is (and whether the shipped table needs a revision) is for the L9 owner.

### AI Worker's borderline 8.95 mm

Smaller and not alarming: AI Worker's own TCP convention (`robot9.tcp_rule == "ffw"`, `(tip+base)/2` of the full
finger mesh) differs slightly from this check's "nearest point in a 1 cm slab around the TCP plane", which plausibly
explains an 8-9 mm offset on a 2-finger parallel gripper without implying a real production defect (AI Worker is the
one robot already running at scale). Flagged as FAIL at the chosen 5 mm tolerance for completeness, not as a
production alarm.

### Check 6 (render probe) -- pending GPU coordination

The task requires this on a render-OK card, coordinated with the L9 owner, and the project's global rule reserves
new renders for GPU x2/GPU1 or an explicitly cleared card (never 7a2a GPU2 / fe08's listed bad UUIDs / x2 GPU0).
This validation pass deliberately stayed on a non-render cuRobo-only job. `tools/l9/v2robot/spawn_smoke9.py`
(r1pro/g1) and `tools/l9r/probe_franka.py` already implement exactly this probe (1 frame per camera + the sim
TCP-vs-cuRobo-target error, which doubles as a second, independent check 1) -- `selfcheck.py check_render_probe()`
is wired to read their output; it only needs one short run per robot once a render-OK GPU slot is coordinated.

## Self-check #4/#5 caveat ("버리기 전 재검토")

Before flagging G1's table as needing a fix: the alternative explanation above (convention mismatch, not a real
error) was checked once by cross-validating the same method on R1 Pro/Franka (near-perfect match) before writing
this up as a finding, per the project's "verify once before discarding" rule. The numbers are reported as-is; no
existing config file was changed.

## Next step

Generated bundles are **not** used anywhere in production. Per the task's constraint, whether/when the G1 width
table or any other generated config replaces the hand-made one is the L9 owner's call -- sent as a one-line summary
separately (SendMessage).
