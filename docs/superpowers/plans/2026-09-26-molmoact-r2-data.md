# MolmoAct R2 데이터 준비(M1·M3·M4·M5·M6) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MolmoAct 이식(E-MAR-AO·E-MAR-S)의 데이터 쪽 성립 조건을 R2에서 만든다 — 궤적 끝 = 놓기 끝(M1), 경로 다양화 편(M3), 같은 장면 두 대상 편(M4), R2에 안전한 덧그림 색(M5), 조종 전용 평가 집합 n ≥ 300(M6). **학습은 하지 않는다**(메인 지시 뒤 E-MAR).

**Architecture:** 생성기(`harvest/datagen/gen.py`)에 명시 옵션 두 개만 더한다 — `--waypoints`(계획기 경유점 혼합, 새 파일 `harvest/sim/waypoint.py`)와 `--layout pair`(머그·병·쟁반 한 배치, `tasks.pair_layout`). 옵션이 없으면 기존 경로가 바이트 동일(배치·DR 표본 digest 시험 + 파드에서 R2_TRAIN 편 재녹화 비트 비교). 궤적 라벨·색·집합은 순수 모듈(`harvest/datagen/trace.py`, `harvest/datagen/molmo.py`)이 기존 녹화(npz의 시뮬 손끝 `tcp`)에서 만든다.

**Tech Stack:** Python 3.13(로컬)·파드 Isaac Sim 5.1(`ir_run.sh IR_ROOT=cyclo`, CPU PhysX), numpy, Pillow, cv2(그리기, 파드 `venv_e3st`), pytest.

**Spec:** `docs/stage3/molmoact_r2_readiness.md` 6절(M1–M9 만드는 법·관문)·7.2절(E-MAR-S 필요량), `docs/research/molmoact_deepdive_2026-09-26.md` 2.6절(조종: 부록 D.7 경로 다양화 절반, 두 그릇), `docs/stage3/results/r2_datagen.md`·`r2_train_gen.md`(생성기·수율), 책 `docs/book/02-pitfalls.md` P68·P69·P72·P80·P81·P82·P83.

## Global Constraints

- 브랜치 `dev`만. 로컬 쓰기는 D:만(스크래치 `D:\tools\scratch_qdd\mar2d`, 끝나면 큰 사본 삭제). 파드는 `/data`만, `source /data/harvest/env.sh`.
- Write 도구 스크립트만(heredoc·`python -`·`python -c`·자기 일치 `pgrep -f`/`pkill -f` 금지), kubectl은 `MSYS_NO_PATHCONV=1`.
- **항상 `git -c safe.directory=D:/qdd commit -F <msg> -- <내 경로들>`**(P72·P80); 커밋 전 `git diff --cached --stat`에 남의 파일이 없는지 확인. 공유 기록 파일(handoff·draft-log·책)은 자기 커밋 직전에만 쓴다.
- 커밋 메시지 끝: `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01Cak1EG98gYtthtAuz7r8W8`.
- 기본 생성 경로 무변경: 옵션 없으면 `task_layout`·`sample_randomization`·계획기 클래스·meta 키가 전과 같다(시험 + G-default). `harvest/datagen/`·`harvest/sim/` 변경은 기준점 뒤 코드 → R7 검토 대상.
- 궤적 라벨 = **시뮬 손끝**(npz `tcp` = `env.finger_mid()`, 탁상 좌표) + 고정 머리 카메라(`r2_ma2.HEAD_K/POS/R`) 투영. URDF FK 금지(G-fk 9.5 mm).
- 시드: R2_TRAIN 범위(정본 §66, `--confirm-train`)만. 분할 = `gen.split_of`(시드 % 20 == 0 → eval). CAL·TEST·random 변형 금지.
- GPU: Isaac 렌더 = **메인 파드 GPU 0**(주) + **x2 파드 GPU 1**(렌더 시험 통과 뒤만). 메인 GPU 1·2, x2 GPU 0 금지. `IR_ROOT=cyclo`, `IR_INST=mar2d_<tag>`, `OMP_WAIT_POLICY=PASSIVE`, `nice 10`. 남의 프로세스 건드리지 않음.
- 출력 루트: `/data/harvest/r2/molmo/`(`wp/`, `pair/`, `trace/`, `sets/`), 코드 사본 `/data/harvest/code_mar2d_<commit>`(`git -c core.autocrlf=false archive`, JSON `CODE_VERSION`), 운영 `/data/harvest/mar2d/`.
- 유료 API 0. 비밀 출력·검색 금지.

## Review Focus

1. 경유점이 작업 영역 밖·팔 도달 한계로 나가 IK 실패 → 경유점은 안전 상자(x 0.30–0.52, y −0.46–0.02, 탁상 위 z ≥ 0.18 m)로 부호 뒤집기 → 자르기(시험 `test_waypoint_safe_box`).
2. 경유점 도달을 단계 전환으로 오인(approach가 경유점에서 descend로) → 경유점이 남아 있으면 목표는 경유점이고 단계 전환 신호는 실제 목표로만(시험 `test_wp_goal_never_reached_at_waypoint`).
3. 두 대상 배치에서 DR 방해물이 다른 과제의 경로를 막음 → keep-out을 두 경로 모두에 적용(시험 `test_placement_ok_multi_path`); 짝 두 편의 DR 표본이 같아야 함(시험 `test_pair_randomization_same_for_both_tasks`).
4. 놓기 없는 편(실패·retreat 없음)에서 궤적 끝 계산 → `release_frame`이 None, 라벨 파일은 유효 편만(시험 `test_release_frame_none_without_retreat`).
5. 조종 평가 집합이 학습 편과 시드가 겹침 → 빌더가 eval 분할 시드만 받고 학습 시드 집합과 교집합 0을 검사(시험 `test_steer_set_rejects_fit_seed`).

---

## 크기(E-MAR-S 필요량에서 고정)

| 산출물 | 구성 | 시도 편 | 예상 유효 | 근거 |
|---|---|---|---|---|
| M3 경로 다양화 `wp/` | R2_TRAIN P0 fit 시드 120개(10001–10126 중 % 20 ≠ 0) × 과제 3 × {standard, dr} | 720 | ≈ 615(과제 수율 0.99·0.99·0.585) | 같은 시드의 R2_TRAIN 기본 편과 짝(같은 목표, 다른 경로) |
| M4 두 대상 학습 `pair/`(fit) | 시드 11001–11199 중 % 20 ≠ 0 = 190개 × {standard, dr} × {mug_tray, bottle_tray} | 760 | ≈ 600 | 한 배치에 머그·병·쟁반, 지시문이 대상 선택 |
| M4 두 대상 평가 `pair/`(eval) | 시드 11000–12780 중 % 20 == 0 = 90개 × 2 변형 × 2 과제 | 360 | 짝 180 | M6 원천 |
| **합** | | **1,840** | **학습 ≈ 1,215** | |

- **E-MAR-S S2 필요량**: 준비 문서 7.2의 "M3·M4 편 = 표본의 20 %". R2_TRAIN fit 유효 4,877편 기준 x/(4,877 + x) = 0.2 → x ≈ 1,220편 → M3 ≈ 615 + M4 fit ≈ 600 = **≈ 1,215**. MolmoAct D.7(시연 절반이 대체 경로)에 맞춰 M3와 M4를 반씩.
- **1:1 궤적 조건(C4)**: 궤적 조건 표본은 학습 로더가 표본마다 50 %로 고른다(M2, 이번 범위 밖). 이 작업은 그 입력인 **모든 유효 편의 프레임별 궤적 라벨**(M1 끝 규칙)을 R2_TRAIN 유효 5,126편 + 새 편 전부에 만든다(`trace/`).
- **M6 n ≥ 300**: 짝 한 쌍에서 머그 편(대체 = 병 편 궤적, 병 편이 유효해야: ≈ 0.585)·병 편(대체 = 머그 편 궤적: ≈ 0.99) → 짝당 약 1.57편 × 각도 조건 통과율 f(배치에서 계산, Task 1 뒤 기록) × 편당 최대 3장. 180짝이면 f = 0.5에서도 ≈ 141편·≈ 420장 ≥ 300, 편 수 ≥ 100. 준비 문서 7.2: n ≥ 300이면 적중률 표준오차 ≤ 0.029.
- 처리량: R2_TRAIN 실측 편당 29.7 s(prefix 포함) → 1,840편 ≈ 15.2 프로세스-시간. 메인 GPU 0에 3 + x2 GPU 1에 2 프로세스면 ≈ 3.5–4 h.

## 관문 (측정 전 고정 — 이 계획 커밋 시각)

- **G-default**(기본 경로 무변경): 새 코드 사본으로 옵션 없이 R2_TRAIN 편 6개(시드 10001 × 과제 3 × 변형 2, P0)를 다시 녹화 → npz 물리 배열(t, q, qd, tau, q_target, grip, grip_q, grip_tau, tcp, obj_pose, action, action_real, hold_n, phase_id, truth) **비트 동일 6/6**, meta 키 집합 동일. 로컬 시험: 배치·DR digest `1aa6be6c4a02…`(변경 전 계산) 동일.
- **G-det**(새 경로 결정성, §78): 경유점 편 2개·짝 편 2개를 다른 이력의 새 프로세스에서 다시 녹화 → 같은 배열 비트 동일 4/4.
- **G-x2**: x2 GPU 1에서 R2_TRAIN 편 2개 재녹화 → 구조 검사 통과, 물리 배열 = R2_TRAIN 비트 동일(물리는 CPU), 영상 눈 검사(검은 화면·깨짐 없음). 통과해야 x2 레인 사용.
- **G-branch-phys**(파일럿): (a) 구조 검사 오류 0(전 편); (b) 과제별 성공률 — M3: 같은 시드 R2_TRAIN 기본 편 성공률 − 5 %p 이상, M4: 머그 ≥ 0.94, 병 ≥ R2_TRAIN 병 P0 0.589 − 0.05, **두 편 모두 성공인 배치 ≥ 60 %**(준비 문서 M4; 예상 0.99 × 0.585 ≈ 0.58이라 위험 — 미달이면 멈추고 메인에 중간 보고); (c) 비대상 물체(머그·병·쟁반·o9) 편 중 이동 ≤ 1 cm인 편 ≥ 95 %(부딪힘 없음); (d) M3 짝 영상 거리(경유점 편 손끝 경로의 각 점에서 기본 편 경로까지 최소 거리의 최댓값, 머리 영상 px) 중앙값 ≥ 40 px; (e) M4 두 대상 영상 거리 ≥ 60 px(배치 규칙으로 보장, 전 짝 확인); (f) **프레임 눈 검사**(Read 도구): M3 시트 12칸(기본 궤적 대 경유점 궤적)·M4 시트 12칸(두 과제 궤적) — 경로가 목표로 가고 물체가 쓰러지거나 밀리지 않았는지 칸마다 적는다.
- **G-trace-end**(M1): 유효 편(파일럿 전부 + R2_TRAIN eval 249)에서 궤적 끝 = 놓기 끝 프레임(`open` 마지막 프레임), 그 손끝 xy가 놓을 곳 중심 1 cm 안인 편 ≥ 95 %; 놓기 끝 뒤 프레임은 라벨 없음(None); 끝 프레임의 phase = `open` 100 %.
- **G-colour**(M5): 덧그림 색이 모든 풀(train·test)·물체 색과 명목 RGB 거리 ≥ 120; 렌더 프레임 96장(standard 48·dr 48)에서 색 거리 < 60인 화소 비율 ≤ 0.1 %; 덧그린 48장 눈 검사(색 혼동 없음). random 변형 렌더는 평가 전용이라 새로 만들지 않고 명목 색 거리로만 본다(한계로 적음).
- **G-M6**: n ≥ 300, 편 수 ≥ 100, 모든 스냅샷 시드가 eval 분할이고 학습 시드(R2_TRAIN fit·M3·M4 fit)와 교집합 0, 스냅샷 조건(자기 대상 xy ≥ 10 cm, approach 단계, 두 방향 각 ≥ 75°, 편당 ≤ 3) 전수 재검사.
- **본 생성 뒤**: `gen check` 병합 → 폴더별 병합 행 수 = 유효 편 `n_rows` 합, 행·라벨 시드 집합 = 유효 편 시드 집합, 계획 항목 누락 0, 시드 범위 확인(N94).
- 관문 실패·버그·무효 > 10 %·시간 2배 초과 → 멈추고 재설계, 이 문서 변경 기록 → 재개(user-log 87, P18).

---

### Task 1: 두 대상 배치와 DR 다중 경로 keep-out

**Files:** Modify `harvest/sim/tasks.py`(`pair_layout`, `PAIR_TASKS`, `PAIR_PATHS`), `harvest/sim/randomize.py:103-125`(`placement_ok` 경로 여러 개), `harvest/sim/scene.py:474-483`(`set_seed(seed, task, layout="task")`). Test: `tests/sim/test_mar2d_layout.py`.

**Interfaces:** Produces `tasks.pair_layout(seed) -> {obj: (x, y, yaw)}`(o3·o8·o5 필수, o9 1/2), `tasks.PAIR_TASKS = ("mug_tray", "bottle_tray")`, `tasks.PAIR_PATHS = (("o3","o5"),("o8","o5"))`, `tasks.layout_for(seed, task, layout)`, `Env.set_seed(seed, task, layout="task"|"pair")`.

- [ ] 실패 시험: 기본 digest 고정(`test_default_layout_digest_unchanged`), `pair_layout` 규칙(대상 둘 다 WS 안, 쟁반과 거리 ≥ max(0.16, fr + fr + 0.03), 머그–병 ≥ 0.13 m, 두 대상 머리 영상 거리 ≥ 60 px, 결정적), `test_placement_ok_multi_path`(한 경로 = 전과 같음, 둘 = 합집합 거부), `test_pair_randomization_same_for_both_tasks`, `layout_for`가 알 수 없는 배치를 거부.
- [ ] 구현 → 시험 통과 → 커밋(`-- <paths>`).

### Task 2: 경유점 계획기와 생성기 옵션

**Files:** Create `harvest/sim/waypoint.py`(순수 `sample_offsets`·`waypoint`·`wp_goal` + `waypoint_mixin(cls)`), Modify `harvest/datagen/gen.py`(`--waypoints`, `--layout`, meta `molmo` 키는 옵션 때만), Test `tests/sim/test_mar2d_waypoint.py`, `tests/datagen/test_mar2d_gen_opts.py`.

**Interfaces:** `waypoint.sample_offsets(seed, task) -> {"approach": s, "carry": s}`(부호 있는 m, |s| ∈ [0.05, 0.09]), `waypoint.waypoint(start, goal, offset) -> np.ndarray(3)`(xy 중점 + 수직 offset, z = 중점, 안전 상자), `waypoint.wp_goal(wp, cmd_pos, real_goal, pass_r=0.02) -> (goal, passed)`, `gen._planner_cls(waypoints=False)`, `gen.gen(..., waypoints=False, layout="task")`, `gen.record_episode(..., waypoints=False, layout="task")`.

- [ ] 실패 시험: 오프셋 범위·결정성(시드·과제별, 변형 무관), 수직성, 안전 상자, 경유점 미통과 동안 목표 = 경유점·통과 반경 안에서 실제 목표, `_planner_cls()` 기본 = 변경 전과 같은 클래스 동작(경유점 속성 없음), `--layout pair`는 `PAIR_TASKS` 밖 과제 거부, `--waypoints`와 `--layout pair` 동시 거부, P1·P2 거부(P0만).
- [ ] 구현 → 통과 → 커밋.

### Task 3: 궤적 라벨(M1)과 덧그림 색(M5)

**Files:** Create `harvest/datagen/trace.py`, Test `tests/datagen/test_mar2d_trace.py`.

**Interfaces:** `trace.release_frame(phases_per_frame) -> int|None`(첫 `retreat` 프레임 − 1), `trace.project_tcp(tcp_table) -> (uv (N,2), depth)`, `trace.molmo_subsample(points, k=5, fallback=None)`(= `tools/mar2/mar2_lib`와 같은 뜻), `trace.to_u255(u, v, W, H)`, `trace.labels(uv, k_end, W=672, H=376, k=5) -> list[list|None]`(t > k_end → None), `trace.TRACE_RGB`, `trace.palette() -> {name: rgb255}`, `trace.min_palette_distance(rgb)`, `trace.draw(img, trace255, rgb=TRACE_RGB, thickness=2, outline=1)`, CLI `python -m harvest.datagen.trace build --src ROOT --dst DST`(유효 편마다 `<dst>/<variant>/<task>/<kind>/ep<seed>.trace.json` + `<dst>/traces.jsonl` 요약).

- [ ] 실패 시험: 놓기 끝 프레임, retreat 없으면 None, 끝 뒤 None, 5점 규칙·끝점 포함, mar2_lib와 동치, 0–255 왕복, 색 명목 거리 ≥ 120(풀 두 개·물체 6개), 그리기가 검은 테두리 + 색 화소를 만듦.
- [ ] 구현 → 통과 → 커밋.

### Task 4: 짝 목록·조종 평가 집합(M3·M4·M6)

**Files:** Create `harvest/datagen/molmo.py`, Test `tests/datagen/test_mar2d_sets.py`.

**Interfaces:** `molmo.path_divergence_px(uv_a, uv_b) -> float`(방향 하우스도르프), `molmo.pairs(pair_root) -> list[dict]`(시드·변형별 mug/bottle 편, 모호 지시문 `"Put the object on the blue tray."`), `molmo.steer_snapshots(ep, alt_ep, max_per_ep=3, min_xy=0.10, min_angle_deg=75) -> list[dict]`(approach 프레임, 대체 궤적 = [현재 손끝] + 대체 편의 가장 가까운 approach 프레임부터 놓기 끝까지 부분표집, 0–255), CLI `python -m harvest.datagen.molmo {wp_pairs,pairs,steer} ...`(`sets/*.jsonl` + 요약 JSON).

- [ ] 실패 시험: 하우스도르프 값, 짝 구성(두 편 모두 있을 때만), 스냅샷 조건 경계(xy 0.0999 거부/0.10 허용, 각 74.9° 거부/75° 허용), 편당 ≤ 3·고르게 펼침, fit 시드 거부, 대체 궤적 첫 점 = 현재 손끝.
- [ ] 구현 → 통과 → 커밋.

### Task 5: 파드 사본·실행기·x2 렌더 시험

**Files:** Create `tools/mar2d/{run.sh,worker.sh,gates.py,sheets.py}`.

- [ ] `git -c core.autocrlf=false archive <commit>` → `/data/harvest/code_mar2d_<commit>`(+ `CODE_VERSION` JSON), 해시 확인.
- [ ] `run.sh <tag> <pod> <gpu> <gen args>`: GPU 0(메인)·1(x2)만 허용, `IR_INST=mar2d_<tag>`, `OMP_WAIT_POLICY=PASSIVE`, `nice 10`, 캐시·TMP `/data/harvest/mar2d/`.
- [ ] G-x2 → G-default → G-det.

### Task 6: 파일럿과 관문

- [ ] 파일럿: M3 시드 10001–10010(% 20 ≠ 0) × 3과제 × 2변형 = 60편, M4 fit 11001–11010 + eval 11000·11020·11040·11060·11080 × 2 × 2 = 60편(같은 큐라 본 생성의 일부가 된다; 관문 통과 전에는 본 생성 시작 금지 — R2_TRAIN 교훈).
- [ ] `gen check` → `gates.py`(G-branch-phys (a)–(e), G-trace-end, G-colour 화소 비율) → `sheets.py` 시트 → Read로 눈 검사 기록.
- [ ] 관문 실패면 멈추고 재설계(이 문서 변경 기록) 또는 메인 중간 보고.

### Task 7: 본 생성·병합·라벨·집합

- [ ] 작업자: 메인 GPU 0 × 3, x2 GPU 1 × 2(G-x2 통과 시). 본 생성 동안 handoff §0 줄.
- [ ] 끝나면 `gen check`(두 루트) → 병합 검증(행 수·시드 집합·누락·범위) → `trace build`(R2_TRAIN 유효 편 + wp + pair) → `molmo wp_pairs/pairs/steer` → G-trace-end·G-M6 전수.

### Task 8: 결과 문서·기록

- [ ] `docs/stage3/results/mar2_data.md`(관문 증거·편 수·유효성·GPU-h·변경 기록·재현 명령) + 같은 커밋에 handoff §0 줄 삭제·§2.8 줄, draft-log 줄, 책 01(상태 네 값 중 하나)·02·04·05(GPU-h)·06(`date -u` 시각) + 기계 검사(상태 칸 네 값, 표 칸 수, CR 0, 인용 경로 존재) + 전체 시험.

## 변경 기록

(측정 뒤 바뀌는 것은 여기에 `date -u` 시각과 함께 적는다.)
