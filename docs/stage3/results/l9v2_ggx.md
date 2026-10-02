# L9 v2 — GraspGen-X in production grasp selection (A/B, 2026-10-03)

## What changes
- Candidates = analytic antipodal (grasp9) ∪ GraspGen-X. GGX is NVlabs/GraspGenX, code Apache-2.0, weights NVIDIA OML; both are approved in L9_PRINCIPLES §8.
- GGX candidates are generated offline from the object mesh, which is privileged information (`tools/l9/ggx_gen.py`, `harvest/l9/ggx_cache.py`).
  - Each GGX pose is converted to our TCP frame.
  - The closing line through the GGX TCP is then ray-cast on the mesh. It is tried at GGX's own depth first, then at depths snapped to the surface along the approach. No per-gripper constant is used.
  - The contacts are the entry and exit hits that have finger room. The pose is re-centred between the two contacts.
  - The same support-clearance and swept-volume checks as the antipodal candidates then apply.
  - Last, the same sim lift/shake test runs (`tools/l9/grasp_test.py --grasps grasps_ggx --out tested_ggx`). Only candidates that pass it are valid.
- Label rule `ggx_v1` (`grasp9.select_ggx`) picks, among the valid candidates (sim pass, support, clearance, IK), the one with the highest
  `S = ggx_s + 0.5·natural_prior + 0.3·exp(−slip_mm/10)`.
  - `ggx_s` is the candidate's own GGX confidence for a GGX candidate. For an antipodal candidate it is the best GGX confidence within 1.5 cm and 25° of it.
  - `natural_prior` = 1 − rank/len(order) when the candidate's (family, part) is in the object's natural order, else 0. It is soft and never filters.
  - `slip_mm` comes from the sim test. An untested candidate scores 0.5 on this term.
  - Ties are broken by robot side, then reach margin, then index, so the result is deterministic.
  - Instructed rows use the same score, restricted to the instructed family.
- The VLM row format does not change (point, approach, rotation, rationale). `approach_reason` keeps the same values. The rationale builder is unchanged.
- Everything is opt-in. `L9V2_GGX_GRASPS` and `L9V2_GGX_TESTED` turn on the merge; `L9V2_SEL=ggx_v1` turns on the new rule. All three are on the `tools/l9/isaac.sh` env whitelist.
- Proof that the code really runs: `GGXDBG load <obj> ... ggx=<n> ggx_pass=<n>` lines in the run log (rt9 `_merge_ggx`), and `GGXDBG gen` lines in the generator.

## Pre-registered A/B (written before the results)
- Episodes: for each robot, AIW (ffw_sg2, pilot1 plans) and Franka (franka_mast, pilotF plans), take the 24 newest single-arm production episodes, one per definition. Rebuild their plan rows with the same seeds (`ab_select.py`).
- Both arms use the same code copy (dev 600d9b9) and the same GPU (fe08 GPU5, 3 lanes). The two arms are interleaved job by job.
  - `rule`: current production (`natural_v1`, antipodal only).
  - `ggx`: merged cache + `ggx_v1`.
- Adopt only if, for **each** robot, all of the following hold:
  1. Success rate (success with max_dq ≤ 0.04) in `ggx` ≥ `rule` − 5 pp (about one episode of 24).
  2. Grasp distribution gate still passes in `ggx`: top ≤ 50 %, every family ≥ 5 %, rot image bins used ≥ 8 of 12 (gate_v2 thresholds).
  3. Re-grasp episode rate in `ggx` ≤ `rule` + 10 pp.
  4. Label checks: part None count not higher than `rule`; visible-point share ≥ `rule` − 5 pp.
- If adopted, the L9 owner switches **new** production rows with a spec bump: `specgate9` currently counts only `natural_v1` as SPEC. Existing rows stay valid.

## Results
(pending)
