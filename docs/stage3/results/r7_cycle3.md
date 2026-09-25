# R7 객관 검증 순회 — 3회차 (파일명 cycle3, 연속 무결 카운트 0에서 시작한 두 번째 판)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님). 작성 2026-09-25 00:52 UTC(`date -u`, 로컬·파드 시계 일치: 파드 `Fri Sep 25 00:52:06 UTC 2026`).
- 대상: `D:\qdd` `dev` 브랜치 HEAD `543b6b0` = `origin/dev`, 작업 트리 깨끗(검증 전후 `git status` 출력 없음). 파드 사본 = `git archive HEAD`(LF 블롭, `stageb_data.py` sha256 `be1e6214…` = HEAD 블롭), 산출 `run_meta.code_sha` = `57857ca40ab3ca1a`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류(DEFECT / DOC / SCOPED / NOTE), `r7_cycle2.md`(K1–K6), `r7_fixes.md`, 정본 `00-interfaces.md` §1–§68(뒤 절 우선, §67·§68 SCOPED는 결함으로 다시 세지 않음), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5.
- 규칙 준수: 코드·문서 수정·커밋 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`로 실행(전역 설정 안 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c3`. 파드 파일은 모두 `/data/harvest/tmp/r7c3`(코드 사본 포함, 1.6 GB)와 Isaac kit 캐시 `ir/kitcache/cyclo-r7c3m_standard`(208 MB)에만 썼고, **끝에 둘 다 지웠다**. GPU: 학습·CUDA 시험 = GPU 2(렌더 없음, 시작·끝 1 MiB), Isaac = GPU 1, GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음. 시드 DEV·POOL만, `HARVEST_ALLOW_SPLIT` 안 씀(가드 음성 시험 1건에서 `=dev`만). 유료 API 호출 없음(Astra 모의). 비밀값 출력·검색 없음(비밀값 패턴 검사는 개수만, 가림 처리).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 4 |
| SCOPED | 8 |
| NOTE | 10 |

코드는 이번에도 무결하다. 완료 정의 1–5를 직접 다시 돌려 모두 충족함을 확인했다. 그러나 2회차 K1·K2·K3·K4와 **같은 사실을 적은 다른 문서·주석**이 네 군데 남아 있다(2회차 교훈 "같은 사실을 적은 모든 곳을 grep으로" 가 덜 적용됨). DOC가 0이 아니므로 통과가 아니다. 모두 문서·주석 수정만으로 끝난다.

---

## 1. DEFECT

없음.

## 2. DOC

| # | 내용 | 위치 | 근거 |
|---|---|---|---|
| L1 | **(K1 형제) S-E2E 데이터 문서의 작성 날짜가 기준 없이 KST 날짜다.** 2회차 K1은 `r2_datagen.md`·`r3_throughput.md`·`r4_stageB.md`의 "작성 2026-09-25"(기준 없음)를 짚었고 543b6b0이 셋을 "2026-09-24 UTC"로 고쳤다. 같은 날 같은 형식으로 쓴 `se2e_data.md`는 빠졌다. | `docs/stage3/results/se2e_data.md:3` "작성 2026-09-25, S-E2E 데이터 에이전트" | 이 문서의 결정 절 정본 §63 = "2026-09-24 19:48 UTC", draft-log 430 "19:48 UTC S-E2E 데이터 준비 완료". 즉 UTC로는 09-24다. `head -8 docs/stage3/results/*.md \| grep 2026-09-2` 결과 기준 없는 09-25는 이 한 줄뿐이다(`r5_closed_loop.md:4`는 "KST 03:20–04:20"을 함께 적어 맞다 — NOTE 5). §68 K1 줄도 "R2·R3·R4·R6"만 적었다. |
| L2 | **(K3 형제) R2 결과 문서가 R2_TRAIN을 아직 "[제안]"으로, 시험 시드를 500–699로 적는다.** 543b6b0은 같은 사실을 적은 `gen.py`와 `random5.md`에는 정정을 넣었지만 R2 문서는 그대로다. | `docs/stage3/results/r2_datagen.md:139` "`R2_TRAIN_SEEDS = 10000–59999`를 [제안]으로 코드에 두었다(… randomize 논리 시험 500–699와 겹치지 않음 …) … 정본에 시드 범위 한 줄을 넣은 뒤 연다." | 정본 §66(결정)·E-first 시드 표 `E-first-experiments.md:119`에 이미 들어갔고, 시험 범위는 b4a58ce에서 3000–3199(`tests/sim/test_randomize_logic.py:13`)로 옮겼다. `grep -rn "proposal\|제안\|500–699" docs/stage3/results` → 정정 표시 없는 곳은 이 줄뿐(`random5.md:4`에는 정정 표시가 있다). R2는 본 생성(§66) 때 다시 읽힐 문서다. |
| L3 | **(K2 형제) 런타임 코드 주석이 융합 경로를 "한 번 호출"·"decide = vLLM"으로 적는다.** §67 C4는 "스텝마다 두 호출(decide → chunk), vLLM이 은닉 상태를 내주지 않아 HF 한 백본"으로 정정했고 543b6b0은 계획 줄에 정정 표시를 달았지만, 코드 주석 두 곳은 그대로다. | `harvest/runtime/core.py:48` `backend: str = "modular"  # … \| fused (one call: decisions + chunk)`, `harvest/runtime/models.py:11` "FusedModel …: ONE backbone gives decision-token probabilities (decide(), vLLM) and … chunk(ctx, committed), HF backbone context" | 실제 구현 `harvest/runtime/fused_model.py:4-13`: "HF for both paths … decide = the R3 shared-prefix forward … chunk = expert flow sampling …", `FusedClient`는 `/decide`·`/chunk` 두 HTTP 호출(`fused_model.py:412-433`). `grep -rn "one call" harvest` → 이 두 곳(`models.py:1`의 "one call interface"와 `conditions.py`의 "one call in flight"는 다른 뜻이라 제외). |
| L4 | **(K4 잔여) handoff의 정본 범위 표기가 아직 낡았다.** 머리 3줄은 "정본 §1~§68"인데 같은 문서의 5줄은 "정본 §1~§42", §2.7의 "먼저 읽을 것"은 "`00-interfaces.md` §43–§64"다. 새 세션이 "먼저 읽을 것"을 따르면 §65–§68(결과 라벨 거부권, R2_TRAIN 시드, 날짜 정정, SCOPED 목록, CONTRADICT-soft 범위)을 건너뛴다. | `docs/handoff.md:5` "현재 판본: … 정본 §1~§42. … (정본 §1~§68)"(한 줄 안에서 두 범위), `docs/handoff.md:80` 제목 "정본 §43~§64", `docs/handoff.md:81` "`docs/design/00-interfaces.md` §43–§64" | 2회차 K4 근거 목록에 `:81 "§43–§64"`가 들어 있었으나 543b6b0은 3·5·83·90줄만 고쳤다(`git show 543b6b0 -- docs/handoff.md`). |

## 3. SCOPED (통과에 영향 없음, 근거 확인)
- S1. `LatencyChargingController` 스텁(TODO(P3), 로컬·파드 시험 1개 건너뜀 `tests/runtime/test_latency_ctrl.py:11`).
- S2. 본 단계 B 학습·R2_TRAIN 대량 생성(§66 "S-E2E 이후").
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`, 메인 세션만) — 가드 동작은 §5.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 목록(M9 복구·T_fail 뒤 하트비트 정지, patch/replace A5′·M2 R3 합치기, 모듈형 세계 쪽 측정 `unknown`, §52 VQA 공동학습 기본 끔, 융합 런타임 토크 입력·확인 헤드 보정 파일·동시 부하 지연). 근거("완료 정의 1–5는 학습 직전까지의 배관, 이 항목들은 학습된 체크포인트·본 실험이 있어야 의미")는 계획 목표 줄("본 E2E 학습은 하지 않는다")과 맞다.
- S6. Astra 카나리 id = "none"(유료 호출이라 미실행). 이번 폐루프 `astra` 행 2/2에 "none"이 명시로 실린 것을 확인(§5.3).
- S7. S-E2E 체크포인트를 aiworker 런타임에 넣을 때 tau 마스크 채널 차(학습 0 / 런타임 평균 대치), `r7_fixes.md` §7, §67 "융합 런타임의 토크 입력".
- S8. (§68 새 항목) CONTRADICT-soft(D28: 같은 T2 술어 연속 2회 conformal {거짓}). 확인 헤드 보정 뒤로 미루는 판단은 타당하다. 다만 근거 문장이 조금 넘친다 — NOTE 1.

## 4. NOTE
- N1. **§68 K6 근거 문장의 정확도.** (1) "conformal {거짓} 판정에는 보정 파일이 있어야" — 지금 런타임은 보정 파일 없이도 `UNCAL_QHAT = 0.5`(argmax 단일 원소, `harvest/runtime/measure.py:30,129`)로 {거짓}을 내고 `DEVIATE`를 매번 올린다(`core.py:293-299`). 보정되지 않은 판정이라는 점은 로그에 `calibrated = False`로 남는다. (2) "지금의 런타임 동작은 달라지지 않는다" — CONTRADICT-soft를 M4에 `CONTRADICT`로 넘기면 `hold`(`m4.py:268`)와 Astra 사건 호출(`core.py:476`)이 더해져 동작이 달라진다. `DEVIATE`로 넘기는 경우에만 같다. 범위 결정은 그대로 두되, 구현 때 M4 쪽 경로(DEVIATE로 둘지)를 함께 정하기를 권한다.
- N2. **S-E2E 검증 부분집합이 RB1만이다(새로 찾음).** `stageb_train train`의 `--max-val N`은 앞쪽 N개(`val = va[:a.max_val]`, `harvest/train/stageb_train.py:364`)이고, 표본은 RB1 → RB2 순서로 쌓인다. 파드에서 로더로 잰 값: val 1,799 = RB1 1,153 + RB2 646, `va[:50|200|500|1000]`은 **모두 RB1**. `r3_throughput.md:139`가 권한 `--max-val 200–500`을 쓰면 검증 지표와 `--reload-check`가 RB2(OrderPicking)를 전혀 보지 않는다. 단계 A는 `select_val`로 무작위 추출이라(`r3_throughput.md:90`) 두 단계가 다르다. S-E2E 사전 등록 때 층화·무작위 부분집합을 쓰거나 `--max-val 0`(전체, 1회 약 9분 [추정: 0.3 s/표본])을 정하기를 권한다.
- N3. **S-E2E 실행 운영.** `stageb_train train`은 끝에 `last`만 저장한다(`stageb_train.py:367`, 중간 체크포인트·재개 없음). 기본 `--eval-every 10`(`:385`) + `--max-val 0`(`:418`, 전체 1,799)이면 10스텝마다 약 9분 평가가 돌아 학습이 평가에 묻힌다 — 사전 등록에서 두 값을 정해야 한다. 계획의 "2+3 DDP"는 조건부("학습이 2장 필요하면")이고 코드에 DDP 경로는 없다. 묶음 4 기준 한 장 메모리(합성 29.7 GB, `r3_throughput.md:97`)로는 H200 한 장이면 된다. 따라서 결함은 아니다.
- N4. 카나리는 여전히 09-24 UTC 것뿐이다(`cn20260924_mock_ae0d1a`, `cn20260924_ed387f59_76f160`). 이번 폐루프 `run_meta.canary.stale = true`. §68 NOTE 처리("S-E2E·본 실험 시작 때 그날 카나리를 새로 만든다")와 같다.
- N5. 날짜 표기 잔여(결함 아님): `r5_closed_loop.md:4` "실행: 2026-09-25 (… 파드 시계 KST 03:20–04:20)"는 KST로 맞다. 정본 §58 `00-interfaces.md:511` "R5(런타임 = 모델 한 번 호출 …)"은 §67 C4가 덮는다(정본은 덧붙임 방식). `r4_stageB.md:140,149`는 "R5에서 정할 일"로 적은 당시 기록. `harvest/sim/randomization_pools.json:20` "run_dev r5calib 2026-09-25"는 기준(UTC/KST)이 없다(자료 파일 주석).
- N6. S-E2E 양팔 표본은 이미지 3장(머리 + 오른·왼 손목, 둘 다 "(active arm)" 표시)이다 — 이번 학습 `prompt_config.camera`에 `D27v1:head camera:|right wrist camera (active arm):|left wrist camera (active arm):`가 있다. §57("양팔 스킬일 때만 두 손목")과 맞다. 다만 vLLM `--limit-mm-per-prompt image:2`(1회차 N6)라 단계 A/모듈형 경로로는 이 배치를 서빙할 수 없다(융합 서버는 HF라 제약 없음).
- N7. 앞선 순회의 파드 산출물이 `/data` 아래 남아 있다(규칙 위반 아님): `code_r7c1` 2.1 MB, `code_r7c1b` 18 MB, `code_r7fix` 8.3 MB, `tmp/r7c1` 2.0 GB, `tmp/r7fix` 1.3 GB, `cache/pyc_r7c1{,b}` 약 670 MB, `ir/kitcache/cyclo-{pr7*,r7c1*,r7fix}`. 이번 판(r7c3)은 모두 지웠다.
- N8. `tools/ir/ir_run.sh:58`: `CUDA_VISIBLE_DEVICES`가 없으면 GPU 0으로 렌더한다. 지금 GPU 0은 라벨러 장시간 작업이다. 모든 호출자(`closed`·`rd`·`tools/r5`)가 `--isaac-gpu 1`/`CUDA_VISIBLE_DEVICES=1`을 명시하므로 실제 충돌은 없었다.
- N9. 로컬 C: 위생: 검증 시작 표식 뒤 C:에서 바뀐 것은 `.claude.json`(하네스), `.kube/cache/http`(kubectl 캐시), `AppData\Local\Temp`의 폴더 시각과 `2026-09-25_mservice.txt`(다른 서비스 파일, 이 저장소와 무관)뿐이다. Temp 폴더 시각 변화는 내가 처음 네 번 Git Bash heredoc(`cat > D:\… <<EOF`)으로 스크립트를 쓸 때 셸이 만들었다 지운 임시 파일일 수 있다(남은 파일 없음). 이후 스크립트는 Write 도구로 D:에 썼다. pytest는 `D:/tools/scratch_qdd/pytest_tmp/p<PID>`·`tmp_local`만 썼다.
- N10. 1·2회차 NOTE 중 변화 없는 것: 파드 사본 `run_meta.git = {"commit": null}`(재현은 `code_sha`), `lerobot_export.verify(dst)`는 src 없으면 PSNR 없음, `detect_phrase` 고정 표, 결과 라벨 거부권 코드 없음(label4 진행 중), ledger gitignore, 테스트 시드 3000–3199는 정본 시드 표 대신 §68 K3 줄과 `gen.py:35`에만 적힘. 2회차 N2(파드 `ir_run.sh` 옛 GPU 주석)는 해소 확인: 파드 `/data/harvest/ir/ir_run.sh`(CR 제거) = 저장소 `tools/ir/ir_run.sh`(`diff` 같음, 56줄 "렌더는 GPU 0·1 만 …").

---

## 5. 확인한 것 (근거)

### 5.1 2회차 K1–K6 해소 여부
| K | 해소 | 확인 |
|---|---|---|
| K1 날짜 | 부분 — 지적한 파일은 모두 고쳐짐 | `r6_eval.md:4`·`r4_stageB.md:3,45,93`·`r2_datagen.md:3`·`r3_throughput.md:3,70`·`D28:3`·`e_m4b_meas.md:9` 모두 09-24 UTC 또는 "KST 오기" 정정. 같은 형식의 `se2e_data.md:3`이 빠짐 → L1 |
| K2 계획 한 번 호출 | 부분 — 계획 5줄에 §67 C4 정정 표시 있음 | 코드 주석 `core.py:48`·`models.py:11` → L3 |
| K3 gen.py | 부분 — `gen.py:18-19,35-36`은 §66·3000–3199로 고쳐짐, `random5.md:4` 정정 표시 | `r2_datagen.md:139` → L2 |
| K4 handoff | 부분 — 3·5·83·90·92줄 갱신(b4a58ce·`stage3-r7fix1`·"0부터"·2회차 줄) | 5줄 "§1~§42", 80·81줄 "§43–§64" → L4 |
| K5 se2e_data §9 | 해소 | `se2e_data.md:109` 갱신 표시(b4a58ce, 팔별 통계·`open01@v1`·tau 마스크). 코드와 맞음(§5.2) |
| K6 CONTRADICT-soft | 해소(SCOPED) | 정본 §68(`00-interfaces.md:576`). 근거 문장 정확도는 N1 |

### 5.2 A. 테스트 (각 두 번, 불안정 없음)
- 로컬 `cd D:/qdd && python -m pytest`: **784 passed, 11 skipped**(1회 75 s, 2회 70 s). 건너뜀: torch 없음 7, inspect_robots 없음 2, pyarrow 1(파드 안내 문구), TODO(P3) 1. 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json` 생기지 않음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, basetemp `/data/harvest/tmp/r7c3/pytest_cpu{1,2}`): **826 passed, 3 skipped**(두 번 모두, EXIT 0). 건너뜀: pyarrow 1, CUDA 없음 1, TODO(P3) 1.
- 파드 GPU 2: `test_fused_action.py`·`test_stageb_torch.py`·`test_fused_model.py` **26 passed**(시작·끝 GPU 2 = 1 MiB).
- 파드 LeRobot(`venv_e3st` + `pylib_lerobot` + `pylib_pytest`): `tests/datagen/test_episode_files.py` **6 passed**.

### 5.3 완료 정의 1–5 순회 (이번 판에서 직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | S-E2E 로더 전량 적재(`load_for_training("se2e")`): hz 10, train **37,484** / val **1,799** = 정본 §63과 같음(RB1 24,280·RB2 13,204 / 1,153·646). R2 DEV 36편 재검증은 2회차 값(36/32/10,651/10,615)을 그대로 두고 다시 돌리지 않았다(코드·자료 변경 없음: b4a58ce..543b6b0 코드 변경은 `gen.py` 주석뿐). |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 11` → 끝까지(EXIT 0, 38 s). config: n_train 40 / n_val 1,799, hz 10, H 5, 팔 왼 15·오 25, `grip_space open01@v1`, `grip_src` {RB1, RB2}, `proprio_masked` 40/40, `model_rev ebb281ec…`. 검증 결정 NLL 3.53 → 2.06, `save_load`: `max_abs_action_diff` **0.0**, `eval_equal` true, `norm_equal` true. `stageb.json`: hz 10, data se2e, expert horizon 5·proprio_dim 27·act_dim 8, 팔별 통계 다름(q mean[0] 왼 0.1575 / 오 0.1449, 그리퍼 mean 0.52 / 0.51 = 열림 정도 단위). **단계 A**(GPU 2, `TORCH_DISABLE_NATIVE_JIT`를 일부러 unset → 모듈 기본값): `stagea_train train --max-steps 4 --max-train 96 --max-val 24 --accum 16 --eval-every 2 --seed 5` → 검증 NLL 5.01 → 1.16 → **0.9823218981424967**, `load --adapter best --n 24 --seed 5` NLL **0.9823218981424967 = 학습 중 값과 비트 단위로 같음**. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 0 --max-seconds 40 --astra mock --isaac-gpu 1`(168 s): **성공 16.46 s**(1·2회차와 같은 값, 결정성), 호출 49·오류 0, RTF 0.896, M4 epoch 7, Astra 2. 부가 JSONL(`ours/…/dev0-P0-standard-e0.jsonl`): `call` 49/49에 64자리 `request_sha256`(49개 모두 다름), `image_sha256` {cam_head, cam_wrist_right} 49/49, `canary_id` = `cn20260924_mock_ae0d1a` 49/49. `astra` 2/2에 해시 + `image_sha256` {cam_head} + `canary_id` "none". `run_meta.canary` = mock id, `stale: true`(N4). |
| 4 평가 | 충족 | 한 명령(mock, GPU 없음): `e05 --model mock --data jsel_dev/P0 --split dev --episodes 1` → `E05_DONE`(claim `a_as_stabilizer`), `calib --model mock --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`, `calibration.json` 생성. vLLM(SFT 병합) 판은 2회차 결과를 그대로 둠(평가 코드 변경 없음). |
| 5 운영 | 충족 | 처리량 문서 R3, 모든 산출 `/data/harvest` 아래, `run_meta`에 `code_sha`·지문·질문 id·카나리, `MODEL_REV` 고정. 문서 잔여 L1–L4(→ FAIL 원인). |

### 5.4 C. 가드 (파드, 변수 없이; 출력 폴더 `guard_out`은 끝까지 비어 있었고 지움)
- 평가: `e05 --split cal`·`--split test`, `rd --split test_p5`, `calib --fit-split cal` → "refused: set HARVEST_ALLOW_SPLIT=…". `closed --split test --seeds 1000` 거부, `closed --split dev --seeds 500` → "seeds [500] are not in split dev … (refused, never opened)", `HARVEST_ALLOW_SPLIT=dev closed --split cal --seeds 500` 거부.
- 생성: `gen --seeds 10000-10001`(확인 인자 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", `--confirm-train`을 준 500·3000 → 거부, `--variant random` → "TEST pool … use 'dr'", `replay --seed 1300` → 거부.
- 기타: `aiworker.check_layout_seed(1000)`·`(10000)` → 거부. 카나리 `build-set --seeds 500-501`은 DEV 폴더라 표본 0으로 멈춤(파일 없음); CAL 폴더 거부는 `load_episodes → check_seeds`(`eval/common.py:344`)와 `tests/eval/test_canary_cmd.py:36-38`(통과)로 확인.
- 시드 표 일치: `eval/splits.py:13` RANGES(DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119) = `E-first-experiments.md:114-119` + R2_TRAIN 10000–59999(`gen.py:35`, §66). 시험 시드 3000–3199(`test_randomize_logic.py:13`)는 모든 예약 범위 밖.

### 5.5 B·D. 정본 ↔ 코드 ↔ 문서
- §63 (1)–(3)·§62 hz: 위 5.3 실측과 `stageb_train.py:1-18` 설명이 맞다. 단계 B `evaluate` 부분집합은 N2.
- §57 카메라 배치: S-E2E 활성 팔 손목·양팔 두 손목(N6), §47 카메라: `sim/scene.py:11` 672×376 / 424×240, `cli_e3st.py:19` fx 367(272.1은 재현 옵션만), `se2e_data.md` RB1 손목 회전 — 맞다.
- GPU 배분: user-log 62·64 = 계획 40줄 = handoff 85줄 = 코드 기본값(`e05`·`rd`·`calib`·`canary`·`closed --gpu 3`, `closed --isaac-gpu 1`·`ISAAC_GPUS = ("0","1")`, `stagea_train.py:20`·`fused_model.py:23`·`tools/r3_bench.py:11` GPU 2). 예외는 N8.
- 정본 날짜: §56·§57·§58·§60·§62만 [사용자] 표시 제목이라 09-25로 남고 §67 C1이 읽는 법을 적었다. 나머지 §59·§61·§63–§67은 09-24 UTC, §68은 09-25 00:33 UTC(커밋 543b6b0 = 00:35 UTC와 맞음).
- 논문(`paper/sec`, `main.tex`, `mindmap.tex`): "한 번 호출"·옛 시드 범위 표기 없음(`grep`), `stage3-r1r6..HEAD`에서 `paper/` 변경 없음(컴파일 생략).

### 5.6 F. 규칙
- `main` = `origin/main` = `520b2be`, `git ls-remote`: main `520b2be`, dev `543b6b0`.
- 비밀값 패턴: `b4a58ce..HEAD` 차이에서 1건 → 가려서 보니 `r7_cycle2.md`의 패턴 이름 설명 문장(값 아님). HEAD 트리 0건.
- `python tools/intent_check.py` → total 62 flagged 0. `b4a58ce..HEAD`에서 `[사용자]` 줄 삭제 0, `stage3-r1r6..HEAD` `user-log.md` 삭제 줄 0.
- 파드 `/data` 밖: 검증 시작(09:36 KST) 뒤 새 파일 0(`find / -xdev … -newermt`, `/tmp`·`/home1`·`/root`·`/isaac-sim`·`/var/tmp` 각각 0; `/dev/shm`은 Isaac 실행 중 생겼다 지워진 세그먼트로 폴더 시각만 바뀜, 남은 항목은 09-20 것). 내 프로세스 0, GPU 0–3 = 896 / 5 / 1 / 1 MiB(시작 때와 같음). 파드 공용 파일(`/data/harvest/canary` 등)은 바뀌지 않음(시각 08:57–08:59 KST 그대로).
- 로컬 C:: N9.

## 6. 다음 순회 전에 할 일 (제안, 모두 문서·주석)
1. L1: `se2e_data.md:3`을 "작성 2026-09-24 UTC(…KST 날짜 정정)"로. §68 K1 줄 목록에도 더한다.
2. L2: `r2_datagen.md:139`에 "정정(R7 3회차): §66에서 결정, 시험 시드는 3000–3199(b4a58ce)" 표시.
3. L3: `core.py:48`을 "fused (two calls per step: decide -> chunk, one backbone forward; §67 C4)"로, `models.py:11`의 "(decide(), vLLM)"을 "(decide(), HF shared-prefix forward in the fused server)"로.
4. L4: `handoff.md:5`의 "정본 §1~§42"를 판본 표기와 분리하거나 지우고, §2.7 제목·81줄에 "(이후 §65–§68은 §2.8)"을 붙인다.
5. 같은 사실 grep(이번에 쓴 명령): `grep -rnE "작성 2026-09-25|실행: 2026-09-25" docs/stage3/results`, `grep -rn "제안\]\|proposal\|500–699\|500-699" docs harvest tests`, `grep -rn "one call\|한 번 호출\|decide(), vLLM" harvest docs`, `grep -n "§43–§64\|§1~§42" docs/handoff.md`.
6. (권장, S-E2E 사전 등록) N2·N3: 단계 B 검증 부분집합을 층화·무작위로, `--eval-every`·`--max-val`·중간 저장 여부를 사전 등록에 적는다.
