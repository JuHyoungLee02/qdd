# Onboarding autotune: per-robot settings measured, not hand-tuned (tools/onboard/autotune)

2026-10-03 KST. User order (10-03): the per-robot settings teams tune by hand become one general tool. A person enters
simple values, and the tool measures everything else. Rules: `board/L9_PRINCIPLES.md` (fixes are general, and
robots differ only by measured data), `board/L9_generalize_audit.md` rows 1, 2, 5, 9, 10, 12, 16, 17 and 22. This
tool extends the onboarding tool (`onboarding_tool.md`) and replaces none of it.

## What a person enters (the only manual part)

`tools/onboard/autotune/robots/<profile>.json`, one short file per robot:

- URDF, plus the root height (or a stand range relative to the surface for a robot on a stand, such as Franka
  `root_z_rel_surface`);
- the hand descriptor per arm: fingertip links and the opposition groups, in the same format as `hands9.json` of the
  grip layer. A parallel gripper is the N=2 case. The descriptor sets the yaw symmetry: 180° if every opposition
  pair has equal sides, otherwise 360°;
- the robot's real cameras: parent link, mount, HFOV and size, plus an optional pitch joint (AIW neck) or an
  adjustable mount pitch range (Franka mast);
- optional lift/torso joints. `null` takes the URDF limits.

The 4 files hold only real robot data: the URDFs, the cameras from `robot9`/`FFW_SG2_REAL_cameras`, and the
`hands9.json` descriptors. They hold no tuned value.

## Method (one rule for every robot, no robot-name branch)

1. **Sweep** (`sweep.py`, pod, cuRobo v0.8.0 batch IK only, no render, non-render cards). It covers the grid of the
   given body joints (`body_n` values each) × surface 0.40–1.10 m (0.05 steps) × work points x 0.10–0.90 /
   y −0.55..0.15 m from the root (mirrored for the left arm) × TCP height above the surface {0.04 grasp, 0.09, 0.14,
   0.19, 0.24, 0.29} × hand orientation (yaws over the hand's period in 30° steps × tilt {0°, 30° forward,
   30° inward}). For each cell it records IK success (self-collision on, empty world) and whether the target is
   inside the robot's own head camera, with body/neck FK, for every camera pitch option.
   - Cost control without any new algorithm: IK runs only at points the camera sees, because the score multiplies by
     visibility. Targets are snapped to 3 cm in the base frame and deduplicated per base-rotation group (0.05 rad),
     and targets beyond the FK-sampled arm reach radius count as unreachable. All requests go into one batched solve,
     sharded over cards. `--selftest` sends FK-generated poses back through IK: AIW 0.95/0.95, Franka 0.96, G1 0.70
     (right).
   - Generalizes r1b `probe2`/`probe3`/`varfeas` (from the R1 torso closed form to any body joints by URDF FK, and
     from the ZED to any camera) and the G1 team's own-reach plus own-camera gate.
2. **Ranges** (`ranges.py` + `make_profile.py`, pure numpy, 14 unit tests in `tests/l9/test_onboard_autotune.py`).
   - A cell is (body config, surface, stance d).
   - Cell score = mean over the work band (x ∈ [d, d+0.25], y ∈ [−0.40, 0] on the arm's side) of
     *yaw coverage × visible*. Yaw coverage is the share of hand yaws for which some tilt reaches both the grasp
     level and the lift level (+0.10 m).
   - A common camera rule applies to every robot: a camera option counts only with its pitch inside 20–70°
     (`ranges.CAM_PITCH_BAND`). That band is the union of the pitches the four robots' accepted production views use
     today. It removes postures whose camera looks straight down (R1 lean >1 rad: 85–90°).
   - The feasible set is the cells scoring ≥ 0.7 × that robot's own best cell. Every output is a **range or a set**,
     never one value, and `cells` keeps the coupled set because surface and posture interact.
   - The per-arm outputs are:
     - hand yaw ok/bad: bad means below ¾ of the best yaw;
     - tilt;
     - the fallback order: which (Δyaw, tilt) most often rescues a failed nominal grasp, which generalizes
       YAW_FB/TILTFB;
     - lift and carry clearance: ≥ 0.8 of grasps still reachable;
     - the ready TCP height above the surface;
     - the camera pitch, or neck-joint range;
     - lateral band and `work_mask`: the r1b blind-spot mask made generic.
3. **Profile**: `harvest/l9/assets9/env_profiles/<profile>.json`, schema `l9-env-profile-v1`, agreed with the grip-layer
   agent. The reader/draw is the grip layer's `envprof9.py`, which validated 3 of 3 files before R1 was added. The
   common executor reads `carry_clear_m`. Keys:
   - `surface_z_m`, `stance_x_m` (root → near edge of the 0.25 m work band), `lateral_m`;
   - `body{joints, lean_rad, mount_above_surface_m}` (mount = the cuRobo base link origin above the surface);
   - `hand{yaw_deg_ok, yaw_deg_bad, tilt_deg, fallback}`, `ready.tcp_above_surface_m`, `lift_clear_m`,
     `carry_clear_m`;
   - `head_cam{pitch_deg[, pitch_joint]}`, `lift` (stand);
   - `cells` + `cell_half` (draw jitter), `core` (cells ≥ 0.9 × best), `arms.<arm>.*` (per-arm detail and
     `work_mask`), `stats`.
4. **Offline comparison** (`compare.py`). The hand-tuned settings are reference data only (`hand_tuned.json`) and
   are scored on the same sweep. Pass: the mean score of the auto cells ≥ the mean of the hand cells over the same
   stance range.

One robot end to end: `tools/onboard/autotune/run.sh <gpu-uuid-prefix> <profile> [shards]` (sweep → profile →
compare). Cost on these 4 robots:

| robot | runtime | cards |
|---|---|---|
| AIW | ~12 min | 1 card |
| Franka | ~10 min | 1 card |
| G1 | ~6 min per arm | 1 card |
| R1 Pro | 11 min per shard | 4 shards on 4 cards |

The R1 Pro sweep covers 216 torso configs and 5.7 M IK.

## Results (4 robots, dev 8ee26d03)

| | AIW (ffw_sg2) | Franka (mast) | R1 Pro | G1 |
|---|---|---|---|---|
| best cell score | 1.00 | 1.00 | 0.95 | 0.45 |
| feasible cells | 369 / 1080 | 795 / 1080 | 330 / 38880 | 49 / 1620 |
| surface_z_m | 0.40–1.10 (lift couples) | 0.40–1.10 (stand couples) | 0.40–1.10 (core 0.40–0.95) | 0.65–0.90 (core 0.70–0.80) |
| body | lift −0.5–0, mount 0.08–0.68 | stand −0.40..+0.10 vs surface | lean 0.03–0.80, mount −0.20–0.49 | lean −0.13–0.39 (core 0.26–0.39) |
| stance_x_m | 0.15–0.45 | 0.10–0.65 | 0.10–0.65 | 0.10–0.30 |
| hand yaw bad | none | none | **60°, 90°** (right) | 120–300° (thumb side) |
| camera pitch | neck head_joint1 0.78–0.985 (45–56°) | mast 20–40° | 22–66° | 40–70° |
| lift / carry / ready | 0.05–0.25 / 0.05–0.25 / 0.14–0.29 | same | 0.05–0.20 / 0.05–0.25 / 0.14–0.24 | 0.05–0.25 / 0.05–0.25 / 0.14–0.29 |
| offline auto vs hand (same stance range) | 0.88 vs 0.54 PASS | 0.90 vs 0.87 PASS | 0.77 vs 0.30 PASS | 0.37 vs 0.20 PASS |

### Required R1 rediscoveries

- **Hand yaw.** The right arm's yaw rates are 0°: 0.79, 30°: 0.75, **60°: 0.51, 90°: 0.49**, 120°: 0.69,
  150°: 0.79. Yaws 60 and 90 are the two flagged bad, the same two r1b measured as worst with probe2 (+0.20 m:
  0.04/0.10). The top fallback for a failed nominal is Δyaw ±60–90° with a 30° tilt, the same family as r1b YAW_FB
  plus TILTFB. The left arm shows no yaw dip in the mirrored convention, so the R1 yaw problem is right-arm specific.
- **Lean/surface band.** 8 of the 12 top cells lie at lean 0.66–0.80 rad and torso_link4 0.37–0.46 m above the
  surface. The best is lean 0.72 / 0.44 m, score 0.95. This is the r1b band (0.65–0.80 / 0.36–0.42) and the R1
  team's recommendation (0.75–0.85 / 0.36–0.40). The upper lean limit 0.80 comes from the common camera band, which
  matches the R1 team's note that a near-vertical ZED looks unnatural. The full range also keeps lower leans
  (0.2–0.6 at lower mounts) that score 0.86–0.90, which gives diversity as the principles ask for.
- The hand setting (lean 0.8, mount 0.36, surfaces ≤0.77) scores 0.62 at its best stance. Its weak point is the
  stance: at the R1 surfaces the work band must start 0.35–0.6 m ahead (r1b probe4: blind spot x < 0.46). Reachable
  cells cluster at **low surfaces 0.40–0.50 m** with the torso squatted.

### Other robots

- **G1** has the lowest ceiling (best 0.45). The thumb-side yaws are poor (240–270°: 0.15–0.21), so hand yaw
  matters for G1 more than for any other robot. The auto core (lean 0.26–0.39, surface 0.70–0.80) overlaps the G1
  team's hand band (lean 0.10–0.40, surface 0.55–0.78) at its top end.
- **AIW**: the hand REL_OK band (surface − lift 0.62–0.88) includes mounts 0.7–0.81 m above the surface, where
  top-down reach collapses (0.35 → 0). Production avoids that by choosing the lift per scene, so the hand mean
  here understates production. The auto profile simply never draws those mounts. The neck auto range (0.78–0.985)
  is the upper half of the production neck draw.
- **Franka**: the hand stand drop (0–0.12 m below the surface) sits inside the auto stand range (−0.40..+0.10). The
  auto range is wider, which adds diversity, at a near-equal score (0.90 vs 0.87).

## Stage 3: sim A/B, env profile only (envprof_ab5 + ab5x, 2026-10-03)

Setup:
- Code: dev 3705df9c, profiles v2 (41bf10aa). Profile cells require >= 70 % of the work band in the robot's own
  camera view and body clearance from the furniture.
- Consumer: uses the cell torso and stance with no AIW keep-out clamp, and places objects inside the arm work_mask.
- Arms: same rows and seeds in both. A = L9_ENV_PROFILE off, B = on, nothing else differs.
- Rows: 20 per robot, plus 25 more each for R1 and G1. Run on e9f3 GPU1, 6 lanes.
- Dirs: /data/harvest/l9v2/gab/envprof_ab5{,x} (report.txt).
- Not used for the verdict: ab (d8f8cb9, no consumer, so B == A), ab2 (profile v1, humanoid out-of-view skips) and
  ab3/ab4 (replaced before any result).

| robot | A success / rendered | B success / rendered | B skips that A did not have |
|---|---|---|---|
| AIW | 3/7 | 3/7 | none (identical episodes; the profile is only consumed on the R1/G1 path) |
| Franka | 6/12 | 6/12 | none (identical) |
| R1 Pro | 2/9 | 0/7 | reach 12 vs 5 (work_mask final check), out of view 5 vs 2 |
| G1 | 3/16 | 3/9 | out of view 7 vs 2 |

Head camera, 5 frames per row (`autotune_out/frames/headcam_sheet_ab5.png`):
- R1 B frames show the table at an angle from above, as in A and AIW.
- Many G1 B frames are close-ups where the arm covers up to about 1/3 of the image, which is less natural than AIW.

**Verdict: not adopted for the general spec in this round.** Neither rendered rows nor successes improve, and R1 is
worse. No humanoid reached 20 rendered episodes in either arm. So this shows no gain; it does not prove harm.

Before discarding (re-check rule), candidates for the next round:
- a G1 stance floor against close-ups;
- the final mask check uses the drawn cell's own reach/view mask instead of the all-cells mean;
- the surface height comes from the profile only where the robot's own reach band agrees (grip-layer 20e4a27 issue).

## Caveats (the "re-check before discarding" rule)

- **Assumptions in the score.** Empty world, no furniture collision, no own-body occlusion; a 0.03 m snap and
  8 IK seeds. The score is a relative reach/visibility signal, not a success rate. G1 selftest 0.70 means some
  reachable G1 poses are missed, which makes the G1 ranges conservative.
- **Constants.** The methodology constants (work band 0.25 m × 0.40 m, lift reference 0.10 m, rel 0.7, pitch band
  20–70°) are one set for all robots. They are not tuned per robot.
- **R1 grid.** R1 uses a 6-value grid on 3 torso joints. The hand-band cells exist only at a few surfaces, so
  `hand_n` is 36.
- **Left arm.** Left-arm yaws are reported in the mirrored convention: yaw → −yaw, so "inward" means the same for
  both arms.

## Files

- `tools/onboard/autotune/`: `geom.py`, `sweep.py`, `ranges.py`, `make_profile.py`, `compare.py`, `run.sh`,
  `runat.sh`, `robots/*.json`, `hand_tuned.json`
- `harvest/l9/assets9/env_profiles/{ffw_sg2,franka_mast,r1pro,g1}.json`
- pod sweeps: `/data/harvest/autotune/out` (AIW, Franka, G1), `/data/harvest/autotune/out2` (R1), logs
  `/data/harvest/autotune/logs/`
