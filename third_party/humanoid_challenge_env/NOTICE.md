# humanoid-challenge-env (vendored, unmodified)

- Source: https://github.com/kairobahq/humanoid-challenge-env
- Commit: `523ea8e8ebcd80a607e8b41aaeadc345fdfa5792` (2026-09-24 15:56:50 +0900), cloned to the pod at
  `/data/harvest/src/humanoid-challenge-env` on 2026-09-24.
- License: Apache License 2.0 (`LICENSE`, copied from the repository root). The copied files keep their own
  license headers (`FFW_SG2_REAL_cameras.py`: "Copyright 2026."; `taskC_ffw_sg2.py`: "Copyright 2025 ROBOTIS CO., LTD.").
- Copied byte-for-byte (sha256 checked against the pod clone; `tests/sim/test_challenge_cameras.py` re-checks):

| file | sha256 |
|---|---|
| `LICENSE` | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| `scripts/FFW_SG2_REAL_cameras.py` | `5b71adc52bd6c22a78964de78c0b86e5ff2196ace784690a37ae7404234e478f` |
| `scripts/taskC/taskC_ffw_sg2.py` | `a5a6bbef929b47f36e324cb0472c595d4ec44eddea2997157432f34440a62462` |

- Not present upstream: `scripts/FFW_SG2_REAL_cameras.md` (the .py docstring refers to it; the file is not in the
  repository at this commit).
- The robot USD comes from the official `ROBOTIS-GIT/cyclo_lab` at `42dcd8256651f7ccad64d7ba0c9bd34bb878e7d6` (the
  commit `FFW_SG2_REAL_cameras.py` pins as "CL"), checked out as a git worktree at
  `/data/harvest/cyclo_lab_42dcd82`. `FFW_SG2.usd` (blob `08a5bd5`) and `assets/robots/FFW_SG2.py` (blob
  `004ee05`) are identical at `42dcd82` and at our earlier clone `f4c0470`.

Why these two files: the challenge's task A/B scripts spawn `FFW_SG2_MOBILE_CFG` from the cyclo_lab inside the
challenge Docker image (not in this repository); the only robot config file the repository itself carries is
`scripts/taskC/taskC_ffw_sg2.py` (`FFW_SG2_MOBILE_CFG`, task C data-collection version). The cameras of all three
tasks come from `scripts/FFW_SG2_REAL_cameras.py`.

How we use them: `harvest/sim/scene.py` imports both by path. The single deviation (base fixed,
`fix_root_link=True`, canon §38) is applied on a copy of the config in `scene._robot_cfg()`; the files here are not
edited.
