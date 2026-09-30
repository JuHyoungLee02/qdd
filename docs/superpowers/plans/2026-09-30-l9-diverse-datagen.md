# L9 Diverse Data Generator (stage 1, one arm) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An L9 episode generator (8 environment families x >= 5 layout rules, >= 75 task definitions, left + right arm, 10 light families, 100 % head variation) that writes L8S-format episode folders, passes the spec gates and runs stratified mass production toward >= 38,000 successful episodes.

**Architecture:** New code only in `harvest/l9/` (pure scene / task / variation layers + an Isaac world) and `tools/l9/` (plan, lanes, supervisor, gates, audits, diversity). The episode itself is the L8S collection path (`teach_l8d.collect.collect_episode`: XCollector truth labels + DART perturbations, `XEpisode` multi-step) on an `IsaacWorld` subclass, like `xring` / `xart`. Every L9 task definition compiles to an ordered list of L8-X steps `(target, place[, xy offset])` whose place is one of the four existing predicate kinds (on an object, at an invisible spot, into a kinematic container, on a furniture surface), so success predicates, truth plan and judge are the L8S ones. The arm is fixed per Isaac process (`make_env(arm=...)`); the plan deals episodes to left / right processes 50 / 50 and the scene is sampled for that arm's reach (mirrored reach model).

**Tech Stack:** Python 3.11, numpy, pytest (local, pure modules); Isaac Sim / Isaac Lab on the pods (`tools/teach_l8d/isaac.sh` pattern); SigLIP (open_clip / transformers on pod GPU) for the diversity report.

**Spec:** `docs/superpowers/specs/2026-09-30-l9-diverse-datagen-design.md` (stage 1 only; §0 + §6 amended 2026-09-30 with the user's "every environment must look different" rule).

## Global Constraints

- L8S behaviour unchanged: shared-code edits (executor left arm, `hand` label field, builder left-wrist image) are opt-in (default = L8S path) and pinned by tests; existing relevant test dirs pass.
- Output = L8S episode folder (`meta.json`, `labels.jsonl`, `calls/`, `joints.npz`, `result.json`, `scene.json`) + meta fields `gen: "l9"`, `env_family`, `layout`, `task_family`, `task_id`, `arm`, `head_pose`, `light_family`, `unreal`, `combo_hash`.
- Asset licences: CC0 / CC BY / CC BY-SA / Apache only; per-asset source + licence recorded; stability gate = L8S `validate_objects` (bottom 5 mm, tilt 10 deg, drift 2 cm).
- Gates: per task definition pilot 10 eps success >= 50 %; arm joint step <= 0.04 rad (the used arm); labels pass the runtime parser (`astra_solo.pt_schema.validate`); frame review (head + wrist f0 and middle frame, looked at); 300-episode audits; diversity report vs L8S; combo hash unique; near-duplicate (SigLIP cos > 0.95) pair share below L8S.
- Pods: only `/data`; render GPUs 7a2a 0/1/3 and x2 1; lanes sized to CPU quota (7a2a 32, x2 12 cores; one Isaac ~5-7 CPU); code deployed as LF `git archive` into `/data/harvest/code_l9_<sha>`; long jobs from launcher script files, no pkill/pgrep patterns on the command line.
- Unrealistic mode exists but is off by default (`unreal: false`), not used in production.

## Decisions taken while planning (recorded, not user decisions)

1. **Arm per process.** `make_env` builds the action space for one arm; switching arms per episode would need two envs. Lanes carry `--arm left|right`; the plan keeps each task definition 50 / 50 (within 40-60 % overall). The arm is still "chosen by reach": the scene is sampled so the task's nodes are reachable by that arm (right reach model mirrored in y for the left arm; the robot is mirror-symmetric, MJCF checked: left joints = right with q2, q3, q5, q7 negated).
2. **Top access in stage 1.** The executor approaches from above (`xlabels.plan`). Nodes are generated with open tops (stepped shelves, open cubbies / organisers, containers, seats, zones). Front entry into covered cubbies is excluded from production in stage 1 (spec §4 allowed it only after a pilot; recorded as later work).
3. **Primitives compile to L8-X steps.** `pick+place_on`, `insert_into`, `insert_upright` (narrow holder, tilt <= 15 deg check added in the L9 judge), `stack_on`, `line_up` / `rel_place` / `set` (invisible spots), `sort_into` (containers by colour / kind / size), height moves (surface nodes). `push` is not used in stage 1 (xnew push path is table-only).
4. **Furniture count** = mesh pieces (THOR / Poly Haven / cyclo, gated) + a frozen catalog of parametric furniture specs (`harvest/l9/assets9/furniture_param.json`, each spec = a unique dimensioned composition); reported separately.

## Review Focus

- A left-arm episode whose labels / prompt / wrist image still say "right" -> must say left everywhere (tests in Task 2 and Task 8).
- An L8S row (no `hand` key) going through the parser / d-min builder -> byte-identical output (tests in Task 2).
- A task definition that cannot be instantiated in a sampled scene (too few reachable nodes / objects) -> redraw the scene (bounded), then `skipped.json`, never a crash of the lane (test in Task 5).
- Two episodes with the same (room, furniture set, materials, light family, HDRI, robot pose, head pose) -> the second is redrawn (test in Task 6).
- Instruction naming an object whose colour was changed by variation -> colour words kept (test in Task 6).

---

### Task 1: Left-arm constants and inertia (later_problems 11)

**Files:**
- Create: `harvest/l9/__init__.py`, `harvest/l9/arm.py`
- Modify: `harvest/teach_l8d/clutter_x.py` (`set_arm_inertia(robot, links=None)` + `LEFT_HEAD_INERTIA` table; default unchanged)
- Modify: `harvest/sim/scene.py` (`init_joints(arm)`: right = `INIT_JOINTS` unchanged; left = mirrored start + right stowed; `_build_cfg` uses it)
- Test: `tests/l9/test_arm.py`

**Interfaces (produces):** `arm.mirror_q(q7) -> tuple`, `arm.INIT_L_ARM`, `arm.STOW_R`, `arm.arm_start(arm) -> (x, y, z)`, `arm.goal_yaw(arm, yaw) -> float`, `arm.joint_prefix(arm) -> "arm_r_joint"|"arm_l_joint"`, `scene.init_joints(arm) -> dict`, `clutter_x.set_arm_inertia(robot, links=None)`.

- [ ] Test: `mirror_q(INIT_R_ARM) == INIT_L_ARM`; `mirror_q` negates indices 1, 2, 4, 6; `scene.init_joints("right") == INIT_JOINTS`; left dict has `arm_r_joint1 == 0.75`, `arm_r_joint4 == -2.30`, `arm_l_joint{i}` = INIT_L_ARM; left inertia values equal the MJCF (`arm_l_link4` 0.00633449 ...); `LEFT_HEAD_INERTIA` has head_link1/2.
- [ ] Run, fail; implement; run `pytest tests/l9 tests/sim -q` pass; commit.

### Task 2: `hand` field (parser, labels, d-min builder) — opt-in

**Files:** Modify `harvest/astra_solo/pt_schema.py` (`_command`: optional `hand` in {left, right} kept only when given), `harvest/teach_pt/min_format.py` (`row`: when `r.get("hand") == "left"` swap the wrist wording of the text and add the `hand` key to the answer; when `hand` present add the hand field to the JSON format line), Create `harvest/l9/hand.py` (`left_text(text)`, `with_hand(answer_json, hand)`), Test `tests/l9/test_hand.py`.

- [ ] Tests: L8S answer without hand parses to the same dict as before (no `hand` key); `{"hand": "left"}` parsed; `"hand": "up"` -> error; `left_text` replaces "RIGHT wrist camera" / "right hand" / "right gripper" / "right_wrist" and nothing else; `min_format.row` of an L8S-shaped row unchanged (compare against the function without the change on a fixture row).
- [ ] Implement, run `pytest tests/l9 tests/astra_solo tests/teach_pt -q`, commit.

### Task 3: Variation layer `vary9` (lights, head, unreal, combo hash)

**Files:** Create `harvest/l9/vary9.py`, Test `tests/l9/test_vary9.py`.

**Produces:** `LIGHT_FAMILIES` (>= 10 dicts: intensity range, colour temperature range, key-light direction / elevation, dome gain, ISO bias), `sample_light(family, rng) -> dict`, `head_pose(rng) -> {"tilt", "pan", "random": True}` (tilt 0.785 +- 15 deg clipped to the raised USD limit 57 deg, pan +- 30 deg), `unreal_style(rng)` (off by default), `combo_hash(rec) -> str`, `ComboLedger(path)` (`seen(h)`, `add(h)`; append-only file per lane).

- [ ] Tests: 10 families, all distinct names; head pose ranges; `combo_hash` stable and changes with any field; ledger rejects repeats; colour words: `keep_named_colours(instruction, objects)` returns the object ids whose colour may not change.
- [ ] Implement, test, commit.

### Task 4: Scene layer `scene9` (8 families x >= 5 layout rules, nodes, reach per arm)

**Files:** Create `harvest/l9/scene9.py`, `harvest/l9/nodes.py`, Test `tests/l9/test_scene9.py`.

**Produces:** `FAMILIES` = {shelf_front, dining, living_low, kitchen, entrance, office, store, workbench} each with >= 5 `LayoutRule`s; `sample(family, rule, seed, arm, reach, mesh=None) -> dict` in `furniture.sample_scene` format (`furniture`, `walls`, `surfaces`, `placement_regions`, `lift`) + `nodes` (`top`, `cubby` (open top), `seat`, `slot`, `container`, `zone`; each with `id`, `kind`, `top_z`, `xy_box`, `reach_ok`) + `robot_pose` (distance 0.15-0.45 m, yaw +-20 deg applied as a rotation of the whole scene about the robot base); `MirroredReach(reach)` for the left arm; <= 28 cuboid parts (FX slots).

- [ ] Tests: every (family, rule) samples for seeds 0-19 and both arms without exception; parts <= 28 and outside `KEEP_OUT`; left-arm nodes have y mirrored side reach; >= 1 reachable node of each kind the family promises; rotation keeps parts axis sizes; 40 distinct (family, rule) pairs.
- [ ] Implement, test, commit.

### Task 5: Task layer `task9` (primitives, >= 75 definitions, instantiation)

**Files:** Create `harvest/l9/task9.py`, `harvest/l9/templates9.py`, Test `tests/l9/test_task9.py`.

**Produces:** `DEFS` (>= 75 `TaskDef(id, family, prims, roles, n_obj, needs_nodes, templates)` in 9 families x >= 8); `instantiate(defn, scene, pool, seed, arm) -> Episode9 | None` with `steps [(tgt, place, offset)]`, `layout {id: (x, y, yaw[, support])}`, `spots {id: (x, y, top_z)}`, `containers`, `instruction`, `roles`; templates >= 5 per definition with name / colour / position phrasing.

- [ ] Tests: `len(DEFS) >= 75`, 9 families x >= 8; every definition instantiates on some scene of its allowed families (seeds 0-49); objects do not overlap (footprint + 2 cm); spots are inside a reachable node; instruction mentions every moved object's name; >= 5 templates per def; `None` when the scene cannot host it (no crash).
- [ ] Implement, test, commit.

### Task 6: Asset catalogs `assets9` (objects, containers, furniture, rooms, materials, HDRIs) + pools

**Files:** Create `harvest/l9/assets9.py`, `harvest/l9/assets9/*.json` (catalog tables with per-asset licence / source), `tools/l9/assets/*` (fetch / select / rescale / validate drivers reusing `tools/l8x_assets`), Test `tests/l9/test_assets9.py`.

**Produces:** `load_objects() -> {id: row}` (objv-compatible rows: `usd_physics`, `half_extents`, `height`, `grasp_width`, `category`, `colour`, `licence`, `source`, `stable_upright`), `load_containers()`, `load_rooms()`, `load_materials()`, `load_hdris()`, `pool_for(key, n, needs) -> dict` (per process; rotates through the catalog so every asset is used), licence check `licence_ok(str)`.

- [ ] Tests: every row has a licence in the allowed set; no NC / ND; ids unique; `pool_for` deterministic, covers the categories a pool needs (cups, containers, blocks ...).
- [ ] Catalog growth runs on the pod (objects >= 6,000 through validate_objects, materials >= 650, HDRIs >= 140, rooms >= 190, furniture >= 1,400) — progress recorded in `harvest/l9/assets9/COUNTS.json`.
- [ ] Commit per catalog increment.

### Task 7: Isaac world `world9` + episode wrapper `collect9` + runner `run9`

**Files:** Create `harvest/l9/world9.py`, `harvest/l9/collect9.py`, `harvest/l9/run9.py`; Modify `harvest/teach_l8d/collect.py` (`save_joints`: arm joint prefix from `getattr(world, "arm", "right")`, default unchanged). Test `tests/l9/test_collect9.py` (fake world), `tests/teach_l8d` must pass.

**Produces:** `make_world9(arm, pool, mesh, rooms) -> World9` (IsaacWorld subclass: no table, FX slots + mesh + rooms, pool objects registered, `make_env(arm=arm)`, left: mirrored start / goal yaw / wrist camera mapping, inertia fix both arms + head, per-step joint log, arm velocity cap for the used arm, auto exposure, light family, head pose, occlusion check of first frame); `collect9.run_episode(world, row, out_dir) -> meta` (registers the episode task in `tasks.TASKS` / `X_TASKS` / `X_STEPS`, calls `collect.collect_episode`, then adds the L9 meta fields, `hand` to every label row, the insert-upright tilt judge, combo hash); `run9.main` (`--arm --family --plan --pool-key --out`; resume; `skipped.json`).

- [ ] Fake-world test: meta has all L9 fields, labels rows carry `hand`, left arm max_dq read from `arm_l_joint*`.
- [ ] Pod smoke: one right + one left episode per family renders (head + wrist PNG looked at).
- [ ] Commit.

### Task 8: Pilots (G1) and frame review (G2)

**Files:** Create `tools/l9/plan.py` (pilot + production plans, stratified), `tools/l9/lane.sh`, `tools/l9/isaac.sh` (= teach_l8d/isaac.sh with its own log / STOP dirs), `tools/l9/gate.py` (per task-def yield, arm jumps, parser pass, combo uniqueness), `tools/l9/sheet.py` (contact sheets: head f0 / wrist f0 / middle frame of random episodes).

- [ ] 10 pilot eps per task definition (both arms); definitions < 50 % are fixed or dropped (>= 75 must remain); arm step <= 0.04 rad; parser 100 %; sheets looked at per family.
- [ ] Commit gate report `docs/stage3/results/l9_gates.md` + book pitfalls for new traps.

### Task 9: Diversity report (G4) and near-duplicate check

**Files:** Create `tools/l9/diversity.py` (SigLIP embeddings of head f0 for L9 and L8S samples; random-pair mean cosine distance, k-means effective clusters, nearest-neighbour cosine > 0.95 share; asset / family counts from meta).

- [ ] Run on pilot data vs L8S; write numbers into the gate report; commit.

### Task 10: Mass production (G3)

**Files:** Create `tools/l9/supervisor.sh` (restarts lanes, progress JSON, STOP file `/data/harvest/out/l9/STOP`), `tools/l9/audit.py` (every 300 new episodes: yield, arm jumps, parser, 12 random frame sheets for review).

- [ ] Launch on 7a2a GPU 0/1/3 + x2 GPU 1 with lanes sized to CPU; measure eps/h; board line; stop working and report.
