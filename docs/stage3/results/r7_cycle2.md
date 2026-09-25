# R7 객관 검증 순회 — 수정 뒤 1회차 (파일명 cycle2, 순회 카운트는 0부터 다시 센 첫 판)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님). 작성 2026-09-25 00:30 UTC(`date -u`, 로컬·파드 시계 일치: 파드 `Fri Sep 25 00:30:16 UTC 2026`).
- 대상: `D:\qdd` `dev` 브랜치 HEAD `b4a58ce`(태그 `stage3-r7fix1`) = `origin/dev`, 작업 트리 깨끗. 파드 사본 = `git archive HEAD`(LF 블롭, `stageb_data.py` sha256 `be1e6214…` = HEAD 블롭).
- 기준: `r7_cycle1.md`의 점검 틀(A–G)·분류(DEFECT / DOC / SCOPED / NOTE), 수정 기록 `r7_fixes.md`, 정본 `00-interfaces.md` §1–§67(뒤 절 우선, §67 SCOPED는 결함으로 다시 세지 않음), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5.
- 규칙 준수: 코드 수정·커밋 없음(이 보고서만 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c1b`. 파드 파일은 모두 `/data/harvest` 아래(코드 `code_r7c1b` 18 MB, 산출 `tmp/r7c1b` 2.0 GB — 작은 체크포인트 3개 포함, 지워도 됨, 캐시 `cache/pyc_r7c1b`, Isaac kit 캐시 `ir/kitcache/cyclo-r7c1b{m,f}_standard` 각 208 MB). GPU: 학습·fused 모델 = GPU 2(렌더 없음, 시작·끝 1 MiB), vLLM = GPU 3, Isaac = GPU 1, GPU 0(라벨러) 건드리지 않음. 시드 DEV·POOL·R2-DEV만, `HARVEST_ALLOW_SPLIT` 안 씀(가드 음성 시험 1건에서 `=dev`만). 유료 API 호출 없음(Astra 모의). 비밀값 출력·검색 없음.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 6 |
| SCOPED | 7 |
| NOTE | 9 |

코드 결함(1회차 D1·D2)은 실제 실행으로 해소를 확인했다. 그러나 1회차 DOC 중 넷(C1·C2·C4·C5)과 C8 일부가 덜 고쳐졌고, 새 코드와 어긋난 문서가 하나 생겼다(DOC 6건). DOC가 0이 아니므로 통과가 아니다. 모두 문서·주석 수정만으로 끝나는 항목이다.

---

## 1. DEFECT

없음. 1회차 D1·D2의 해소 근거는 §5.2·§5.3에 있다.

## 2. DOC

| # | 내용 | 위치 | 근거 |
|---|---|---|---|
| K1 | **(C1 잔여) 결과 문서 날짜.** §67은 정본 제목과 계획 파일 이름만 다뤘다. 결과 문서에는 UTC라고 적었지만 날짜가 하루 늦은 곳, 시계 탓으로 잘못 설명한 곳, 기준 없이 "2026-09-25"만 적은 곳이 남아 있다. | `docs/stage3/results/r6_eval.md:4` "실행: 2026-09-25 (… 파드 UTC 21:00–21:45)", `docs/stage3/results/r4_stageB.md:93` "2026-09-25 18:12–18:13 UTC 파드 시계 기준", `docs/design/D28-m4-critic-measurement.md:3` "하루 어긋남 — 로컬 시계 문제로 보이며", `docs/stage3/results/e_m4b_meas.md:9` "D28 머리말과 같은 시계 차", `r2_datagen.md:3`·`r3_throughput.md:3,70`·`r4_stageB.md:3` "작성 2026-09-25"(기준 없음) | `grep -rn 2026-09-25 docs`. 두 UTC 시각(09-25 21:00·18:12 UTC)은 이 검증 시각(09-25 00:30 UTC)보다 뒤다. 1회차 C1이 `pre_r7_fixes.md:4`의 "시계 차" 문장을 틀렸다고 판정했고 그 문장은 고쳐졌지만, 같은 주장을 담은 D28·e_m4b_meas는 그대로다. |
| K2 | **(C4 잔여) 계획 머리 개정 줄이 여전히 "R5 런타임은 모델 한 번 호출"이다.** §67이 이를 "스텝마다 두 호출(decide → chunk)"로 정정했는데, 계획에는 표시나 포인터가 없다. 같은 계획의 GPU 줄(C6)은 취소선과 "→ 대체"로 고쳤다. | `docs/superpowers/plans/2026-09-25-e2e-ready.md:5` | 1회차 C4는 "정본·계획에 반영되지 않았다"고 적었다. 이번 수정(6e2889f)은 정본(§67 `00-interfaces.md:568`)만 고쳤다. |
| K3 | **(C5 잔여 + 새로 낡음) `gen.py`가 R2_TRAIN을 아직 "proposal"로 적고, 시험 시드 범위 설명도 낡았다.** | `harvest/datagen/gen.py:18-19` "(proposal for the stage-B generation, not run in this gate)", `:35` "[proposal]", `:36` "the randomize logic-test range 500-699" | §66이 R2_TRAIN 10000–59999를 결정했고 E-first 시드 표(`E-first-experiments.md:119`)에도 들어갔다. 1회차 C5가 `gen.py:19`·`:35`를 짚었지만 6e2889f·b4a58ce 모두 `gen.py`를 고치지 않았다(`git show --stat`). b4a58ce가 논리 시험 범위를 3000–3199로 옮겨서(`tests/sim/test_randomize_logic.py:13`) `:36`의 500–699 설명은 이제 틀렸다. 동작(가드)은 맞다(§5.4). |
| K4 | **(C2 잔여) handoff가 HEAD 상태를 반영하지 않고, 안에서 서로 어긋난다.** | `docs/handoff.md:3` "R7 1회차 FAIL → 수정 중", `:90` "코드 수정 에이전트 진행 중 … 수정 뒤 2회차부터 다시 센다", `:83` "진행 중: R2 데이터 생성기, R6 평가 스크립트", `:5` "최신 상태는 §2.6", `:81` "§43–§64" | 수정 커밋 b4a58ce와 태그 `stage3-r7fix1`이 handoff에 없다. `:83`의 "진행 중"은 `:89`의 "R1–R6 관문 … 완료"와 맞지 않는다. 순회 횟수 표현도 다르다: `draft-log`(b4a58ce)는 "R7 순회 카운트 0부터 다시", handoff는 "2회차부터 다시 센다". 새 세션이 가장 먼저 읽는 문서다. |
| K5 | **`se2e_data.md` §9가 b4a58ce 뒤로 사실과 다르다.** "ActionNorm이 왼팔·오른팔 값을 한 통계로 섞는다", "모델은 아직 proprio_mask를 읽지 않는다", 그리퍼 변환식이 "필요"하다고 적혀 있다. 정정 표시도 없다(`r5_closed_loop.md:117`에는 정정 표시를 달았다). | `docs/stage3/results/se2e_data.md:107-110` | 정본 §63(1)–(3)은 b4a58ce에서 구현됐다(§5.2에서 실측). 이 문서는 다음 단계인 S-E2E의 데이터 문서다. |
| K6 | **(C8 잔여) "T2 연속 2회 {거짓} → CONTRADICT-soft"(D28)가 구현되지 않았는데, §67 SCOPED 목록에도 없다.** 1회차 C8-2의 두 항목 중 §67은 "M9 복구"만 옮겼다. | `docs/design/00-interfaces.md:569`(SCOPED 목록), `docs/design/D28-m4-critic-measurement.md:106`, `harvest/runtime/measure.py:156`(T2 거짓은 매번 단일 `DEVIATE`) | `grep -rn CONTRADICT harvest/runtime`: soft 판이 없다. `pre_r7_fixes.md:116`도 "넣지 않았다"고 적었다. 구현하거나 §67 목록에 넣어야 한다. |

## 3. SCOPED (통과에 영향 없음)
- S1. `LatencyChargingController` 스텁(TODO(P3), 파드 시험 1개 건너뜀 `tests/runtime/test_latency_ctrl.py:11`).
- S2. 본 단계 B 학습·R2_TRAIN 대량 생성(§66 "S-E2E 이후").
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`, 메인 세션만).
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 목록: M9 복구·T_fail 뒤 하트비트 정지, patch/replace A5′·M2 R3 합치기, 모듈형 세계 쪽 측정(`unknown`), §52 VQA 공동학습(기본 끔), 융합 런타임 토크 입력·확인 헤드 보정 파일·동시 부하 지연.
- S6. Astra 카나리 id = "none"(유료 호출이라 미실행). §67 보충(`00-interfaces.md:571`), `RuntimeConfig.astra_canary_id`.
- S7. S-E2E로 학습한 체크포인트를 aiworker 런타임에 넣으면 tau 마스크 채널이 학습 때와 다르다. 학습 = tau 마스크 0, 런타임 = 마스크 없음(1) + 학습 평균 대치. `r7_fixes.md` §7에 기록돼 있고, §67 "융합 런타임의 토크 입력"에 들어간다.

## 4. NOTE
- N1. 카나리는 09-24 UTC 것 둘뿐이다(`cn20260924_ed387f59_76f160`, `cn20260924_mock_ae0d1a`). 오늘(09-25) 실행한 e05·calib·closed는 어제 id를 싣는다. `run_meta.canary`에는 `"stale": true`가 붙지만 호출 행에는 id만 있다. §28 "매일"을 지키려면 S-E2E 전날·당일에 다시 돌려야 한다.
- N2. 파드 공용 실행 파일 `/data/harvest/ir/ir_run.sh`에는 옛 주석 "GPU2 금지"가 남아 있다(로컬 `tools/ir/ir_run.sh`만 고침, `r7_fixes.md:51`에 기록됨).
- N3. `docs/stage3/results/random5.md:4,23,51`은 "예약되지 않은 500–699"라고 적었다(CAL 500–549와 겹침). 지난 기록이고 시험 범위는 이미 3000–3199로 옮겼다. 정정 표시만 달면 된다.
- N4. 파드 사본은 git 저장소가 아니라서 `run_meta.git` = `{"commit": null}`이다. 재현은 `code_sha`(예: e05 `0e41f59d7567b3be`)로 한다.
- N5. S-E2E 원격조종 명령은 −1.16…1.34까지 나간다(`/data/harvest/tmp/r7fix/grip_range.json`). §63(2) 자름 때문에 닫힘 1.10/1.14를 넘는 "더 세게 쥠" 명령은 모두 열림 정도 0이 된다. 정본대로이며, 시뮬 비선형 차이와 함께 §67 보충에 "섞을 때 재검토"로 적혀 있다.
- N6. 로컬 C:에 새로 생긴 것은 이 저장소와 무관하다. 매시 생기는 `mat-debug-*.log`(0바이트)와 0바이트 GUID `.tmp`는 다른 앱이 만든 것이고, `.kube/cache/http`는 kubectl 자체 캐시다. pytest는 `D:/tools/scratch_qdd/pytest_tmp/p<PID>`·`tmp_local`만 썼다.
- N7. 테스트 전용 시드 3000–3199는 정본 시드 표에 없다(메모리 안 표집만, 파일 생성 없음). 적어 두면 좋다.
- N8. `lerobot_export.verify(dst)`는 `src`를 주지 않으면 PSNR을 계산하지 않는다(`psnr_min_db: null`). 1회차 34.27 dB는 src를 준 판이다.
- N9. 1회차 NOTE 중 N6(vLLM `image:2` — 양팔 3장 불가), N7(`detect_phrase` 고정 표), N8(결과 라벨 거부권 코드 없음, label4 진행 중), N9(ledger gitignore), N11, N12는 변화 없음.

---

## 5. 확인한 것 (근거)

### 5.1 A. 테스트 (각 두 번, 불안정 없음)
- 로컬 `cd D:/qdd && python -m pytest`: **784 passed, 11 skipped**(69 s / 75 s). 건너뜀 이유(`-rs`): torch 없음 7, inspect_robots 없음 2, pyarrow 1(파드 venv_e3st 안내 문구), TODO(P3) 1. 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json` 생기지 않음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 + IR 3경로 + `ir/pylib`, `CUDA_VISIBLE_DEVICES=""`, `--basetemp /data/harvest/tmp/r7c1b/pytest_cpu{1,2}`): **826 passed, 3 skipped**(두 번 모두). 건너뜀: pyarrow 1, CUDA 없음 1, TODO(P3) 1.
- 파드 LeRobot(`venv_e3st` + `pylib_lerobot` + `pylib_pytest`): `tests/datagen/test_episode_files.py` **6 passed**.
- 파드 GPU 2: `test_fused_action.py`·`test_stageb_torch.py`·`test_fused_model.py` **26 passed**(시작·끝 GPU 2 = 1 MiB).

### 5.2 D1 재검증 — 정본 §63 (1)–(3)과 §62 hz (파드 GPU 2, `/data/harvest/tmp/r7c1b/run_stageb.sh`, 로그 `run_stageb.log`)
| 명령 | 결과 |
|---|---|
| `stageb_train train --data se2e --max-train 48 --max-steps 6 --batch 2 --max-val 4 --reload-check --seed 7` | 끝까지 돎(50 s). n_train 48 / n_val **1,799**. 결정 NLL 3.53 → 1.82(검증). `save_load`: `max_abs_action_diff` **0.0**, `eval_equal` true, `norm_equal` true |
| `stageb_train train --data r2 --pool r2/dev/standard/mug_marker/P0,r2/dev/dr/mug_tray/P0 --dev-val-seeds 5 … --reload-check` | 끝까지 돎. fm·aux·ver·dec 손실 모두 계산, n_val 575. `save_load` 차 **0.0**, eval·norm 같음 |

체크포인트 `stageb.json`을 읽은 결과(`probe_ckpt.py`):
- se2e: `hz` 10, `data` se2e, `horizon` 5, `proprio_dim` **27**(= 23 + 마스크 4), `grip_space` `open01@v1`, `arms` {left, right}. 팔별 통계가 서로 다르다(q mean[0]: 왼 0.133 / 오 0.473). tau `p_mean` 0·`p_std` 1(값이 모두 가려져 통계에서 빠짐).
- r2: `hz` 30, `horizon` 15, `arms` {right}, tau 통계는 실제 값(p_mean −20.8 …), 그리퍼 mean 0.65(열림 정도 단위).

로더 표본 직접 확인(RB1·RB2 행 108개):
- 원 그리퍼 −0.298…1.318 → 열림 정도 **0.0…1.0**.
- `proprio_mask` = {tau: 0, 나머지 1}, (hz, H, 원천) = {(10, 5, RB1), (10, 5, RB2)}, 팔 오 58 / 왼 50.
- 10 Hz 행을 hz=30으로 넣으면 거부("hz 10 != 30"), kind RB9는 거부("no gripper calibration").

그리퍼 보정값(`GRIP_CAL` RB1 1.10 / RB2 1.14)은 `/data/harvest/tmp/r7fix/grip_range.json`의 99.5 백분위(1.096/1.1005, 1.152/1.118)와 같다.

### 5.3 D2 재검증 — 폐루프 로그의 요청 해시·이미지 해시·카나리 id (파드, Isaac GPU 1, `run_closed.sh`, `probe_logs.py`)
| 판 | 결과 | 부가 JSONL 행 |
|---|---|---|
| `closed --model mock --split dev --seeds 0 --max-seconds 40 --astra mock` | 성공 **16.46 s**(1회차·pre-R7과 같은 값, 결정성), 호출 49·오류 0 | `call` 49/49에 64자리 `request_sha256`(49개 모두 다름), `image_sha256` {cam_head, cam_wrist_right}, `canary_id` = `cn20260924_mock_ae0d1a`. `astra` 2/2에 해시 + `image_sha256` {cam_head} + `canary_id` "none" |
| `closed --backend fused --model tmp/r7c1b/ckpt/r2_c2/last`(위에서 만든 **§63 새 형식** 체크포인트, 모델 GPU 2) `--max-seconds 20` | 끝까지 돎(`max_steps`, 6스텝 모델이라 예상된 결과), 결정 59·청크 60·호출 오류 0 | `call` 59·`chunk` 60·`astra` 5 모두 해시·이미지 해시·`canary_id`("none", 이 지문의 카나리 없음 — `run_meta.canary.reason`에 명시) |
- fused 판의 `grip_space` = `open01@v1`. 실행된 aiworker 그리퍼 행동 2,000개가 **0.0165…0.1070 m**다. 즉 열림 정도가 패드 간격 m로 되돌려졌다(`fused_model.grip_from_model`).
- `run_meta.canary`: e05·calib = `cn20260924_ed387f59_76f160`(SFT 병합 지문 `ed387f59…`, `stale: true`, N1), mock = mock 카나리, fused = `{"id":"none","reason":…}`.
- 카나리 산출물: `/data/harvest/canary/sets/dev_v1/manifest.json`(set_sha `96bfc52a21afc751`, DEV 0–2, 12 스냅샷, `oracle` 없음), `canary_20260924_ed387f593652252e.json`(오류 0, floor 0.0, 반복 2) — `r7_fixes.md`와 같다.
- `r5_closed_loop.md:117` 정정 표시 있음.

### 5.4 C. 자료·가드 (파드 CPU, `guards.sh`, `probe_data.py`)
- R2 DEV 전수 재검증(`validate_episode`, 읽기만): 36편 구조 36/36, 성공 32, 과제 3 × 12, standard·dr, 프레임 10,651, 행 **10,615 모두 `check_row(hz=30)` + `make_sample` 통과** — `r2_datagen.md` §4.1과 같다.
- LeRobot 내보내기 `verify(/data/harvest/r2/dev_lerobot)`: 32편 오류 0. lerobot 0.3.3 `LeRobotDataset` 프레임 9,288·30 fps. 영상 모양 머리 [3, 376, 672]·손목 [3, 240, 424](§47과 일치), `action0_equal` true.
- 가드(변수 없이 실행) — 모두 거부됐고 파일은 생기지 않았다(`guard_out` 비어 있음):
  - 평가: `e05 --split cal`·`--split test`, `rd --split test_p5`, `calib --fit-split cal`, `closed --split test --seeds 1000`, `closed --split dev --seeds 500`("not in split dev"), `HARVEST_ALLOW_SPLIT=dev closed --split cal`.
  - 생성: `gen --seeds 10000-10001`(확인 인자 없음), `--confirm-train`을 준 500·3000, `--variant random`, `replay --seed 1300`.
  - 기타: `aiworker.check_layout_seed(10000)`. 카나리 CAL 거부는 `tests/eval/test_canary_cmd.py`(통과)로 확인했다.
- 시드 표(`E-first-experiments.md:114-119`) = `eval/splits.py:13` RANGES + `gen.py` R2_TRAIN. 테스트 범위 3000–3199는 모든 예약 범위 밖이다(`test_extra_seeds_avoid_every_reserved_split` 통과).
- 카메라(§47): `sim/scene.py:11` 머리 672×376 / 손목 424×240, `cli_e3st.py` fx 367. 틀린 fx(272.1)를 기본값으로 쓰는 곳은 없다(재현 옵션만 있음).
- GPU 문구: `stagea_train.py:20`·`stageb_train.py:16`(GPU 2 = 학습), `closed.py:35,140,330`(렌더는 0·1만, GPU 2 거부), `canary.py`·`e05`·`calib`·`rd` `--gpu` 기본 3 — user-log 62·64·계획 40줄과 맞다. 파드 `ir_run.sh` 주석만 옛 문구(N2).

### 5.5 완료 정의 1–5 순회
| 정의 | 판정 | 이번 검증에서 돌린 것 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV 36편 재검증·행 10,615 계약 통과·LeRobot 적재(§5.4). 과제 3, standard/dr(random 학습 거부), 30 Hz 관절 행동, labels_v2 + aux + 확인 헤드 목표. 결과 기반 라벨은 §65에 따라 거부권 용도라 필수 아님. S-E2E 표본 39,283 중 val 1,799 로더로 재현 |
| 2 모델 | 충족 | 단계 A: `stagea_train train`(풀, 6스텝, GPU 2, **`TORCH_DISABLE_NATIVE_JIT`를 일부러 unset** → 모듈 기본값으로 동작, N1 해소 확인). 검증 NLL 3.19 → 0.557, `load --adapter best` NLL **0.5574117660522461 = 학습 중 값과 비트 단위로 같음**. 단계 B: §5.2(두 데이터, 저장·재적재 차 0.0). KI·확률 일치 시험 통과(§5.1). 서빙: 단계 A = vLLM(e05·rd·calib), 단계 B = fused 서버(§5.3) |
| 3 폐루프 | 충족 | mock 모듈형 DEV 0 성공 16.46 s(Astra 하트비트 → DecCall → M4 → 스킬, simlat, RTF 0.883). fused §63 새 형식 체크포인트로 한 판 완주, 호출 오류 0 |
| 4 평가 | 충족 | 한 명령 실행(SFT 병합, vLLM GPU 3): `e05`(DEV 1편, 27 스냅샷, 오류 0, 114 s), `rd`(standard/random/dr 각 1편, dr pooled 0.901/0.899), `calib`(POOL 적합 → DEV 2편, `calibration.json` 5 질문). 모두 exit 0, `run_meta.canary` 기록 |
| 5 운영 | 충족 | 처리량 문서 R3. 모든 산출이 `/data/harvest` 아래. `run_meta`에 `code_sha`·모델 지문·질문 id·카나리. `MODEL_REV` 고정. 문서는 K1–K6이 남아 있다(→ 이번 판정 FAIL의 원인) |

### 5.6 F. 규칙
- `main` = `origin/main` = `520b2be`. `git ls-remote`: main `520b2be`, dev `b4a58ce`.
- 비밀값 패턴(`sk-proj-`, `hf_`, `ghp_`): `stage3-r1r6..HEAD` 차이에서 0건, HEAD 트리에서 0건.
- `python tools/intent_check.py` → total 62 flagged 0. `stage3-r1r6..HEAD`에서 `user-log.md` 삭제 줄 0, `[사용자]` 줄 삭제 0(6e2889f에서 바꿨던 제목은 f42fc44가 되돌림), `paper/` 변경 없음(그래서 컴파일 생략).
- 파드 `/data` 밖: 검증 시작(09:11 KST) 뒤 새 파일 0(`find / -xdev -newermt …` → 없음). 수정 기간(08:30 KST 이후)에 바뀐 것은 `/home1/irteam`(수정 에이전트가 빈 `.triton`을 rmdir, 기록됨)과 `/run/secrets`(k8s)뿐이다. `until ! pgrep` 고아 셸 0. 검증이 끝난 뒤 내 프로세스는 남지 않았고 GPU 0–3 사용량은 시작 때와 같다(0 = 896 MiB 라벨러, 나머지 1–5 MiB).
- 로컬 C:: N6.

### 5.7 G. 문서 수치 대조 (이번 판에서 다시 잰 것)
- `r7_fixes.md` §5: 로컬 784/11, 파드 826/3, LeRobot 6 — 같다.
- `r7_fixes.md` §1: S-E2E val 1,799, se2e `stageb.json` hz 10·H 5·proprio_dim 27·arms {left, right}·grip_space `open01@v1`, tau 통계 0/1, 재적재 차 0.0 — 같다(표본 수 64 대신 48로 다시 잼).
- `r7_fixes.md` §2: 카나리 세트 `96bfc52a21afc751`, id `cn20260924_ed387f59_76f160`, 오류 0, floor 0.0 — 같다.
- `r2_datagen.md` §4.1: 36/32/10,651/10,615 — 같다. 폐루프 mock DEV 0 16.46 s — 1회차와 같다.

## 6. 다음 순회 전에 할 일 (제안, 모두 문서·주석)
1. K1: 결과 문서 날짜를 UTC 기준으로 고치거나 "(KST)"를 붙인다. D28:3·e_m4b_meas.md:9의 "시계 차" 문장을 정정한다.
2. K2: 계획 5줄에 "→ §67: 스텝마다 두 호출(decide → chunk), 백본 순전파 1회"를 붙인다.
3. K3: `gen.py:18-19,35-36`에서 "[proposal]"을 없애고 §66 결정을 참조하게 한다. 논리 시험 범위를 3000–3199로 고친다.
4. K4: handoff 머리·§2.8을 b4a58ce·`stage3-r7fix1`·"카운트 0부터" 상태로 갱신하고, §2.7 "진행 중" 줄에 대체 표시를 단다.
5. K5: `se2e_data.md` §9에 "§63 결정·b4a58ce 구현" 정정 표시를 단다.
6. K6: CONTRADICT-soft를 §67 SCOPED 목록에 넣거나 구현한다.
