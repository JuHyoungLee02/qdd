# R7 객관 검증 순회 — 4회차 (cycle 4, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님). 작성 2026-09-25 01:12 UTC(`date -u`; 파드 `date -u` = `Fri Sep 25 01:10:58 UTC 2026`, 로컬과 같음).
- 대상: `D:\qdd` `dev` 브랜치 HEAD `1373f3d` = `origin/dev`(`git ls-remote`), 작업 트리 깨끗(검증 전후 `git status` 출력 없음). 파드 사본 = `git -c core.autocrlf=false archive HEAD`(LF 블롭, `stageb_data.py` sha256 `be1e6214…` = HEAD 블롭), 폐루프 `meta.code_sha` = `73a719f041fa25d3`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류(DEFECT / DOC / SCOPED / NOTE), `r7_cycle2.md`(K1–K6), `r7_cycle3.md`(L1–L4), `r7_fixes.md`, 정본 `00-interfaces.md` §1–§69(뒤 절 우선; §67–§69 SCOPED는 결함으로 다시 세지 않음, [사용자] 표시 제목의 날짜는 §67 C1 규칙대로 세지 않음), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5.
- 규칙 준수: 코드·문서 수정·커밋 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`로 실행(전역 설정 안 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c4`(스크립트는 Write 도구로 D:에 씀, Git Bash heredoc 안 씀). 파드 파일은 모두 `/data/harvest/tmp/r7c4`(코드 사본·산출·pytest·pyc), Isaac kit 캐시 `ir/kitcache/cyclo-r7c4_standard`(208 MB), 폐루프 작업자가 쓴 `cache/pyc_r6/data/harvest/tmp/r7c4`·`tmp/{carb.mBOoTG,hub-root.lock,tmpat9qdxaj}`, LeRobot 시험이 만든 `cache/hf/datasets/parquet/default-4440af650e3d1db0`(+잠금 파일)에만 썼고 **끝에 모두 지웠다**(01:10 UTC 확인). GPU: 단계 B 학습·CUDA 시험 = GPU 2(렌더 없음, 시작·끝 1 MiB), Isaac = GPU 1, GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음. 시드 DEV만, `HARVEST_ALLOW_SPLIT`은 가드 음성 시험 1건에서 `=dev`만. 유료 API 호출 없음(Astra 모의). 비밀값 출력·검색 없음(패턴 검사는 개수만).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 8 |
| NOTE | 11 |

코드는 네 번째로 무결하다. 완료 정의 1–5를 직접 다시 돌려 모두 충족함을 확인했다. 3회차 L1–L4는 모두 고쳐졌다. 그러나 L3(“융합 decide = vLLM”이라는 옛 사실)과 **같은 사실을 적은 곳**이 코드 주석 1곳과 R5 결과 문서 2줄에 남아 있다. 3회차 수정은 `"one call"`로만 grep해서 `"vLLM"` 표기를 놓쳤다. §69가 정한 정정 절차(“저장소 전체를 grep해 같은 사실을 적은 곳을 모두 고치고 정정 표시를 붙인다”)를 지키지 못했으므로 DOC 2건이다. 둘 다 주석·문서만 고치면 된다.

---

## 1. DEFECT

없음.

## 2. DOC

| # | 내용 | 위치 | 근거 |
|---|---|---|---|
| M1 | **(L3 형제, 코드 주석) 융합 행동 경로 모듈의 설명이 decide를 vLLM으로 적는다.** "one fused step is two calls on the same backbone: decide() = decision-token probabilities (**vLLM**, prefix + multimodal cache, lead mode; canon §59) -> M4 commit -> chunk(committed) = backbone context forward + expert flow sampling (HF torch; vLLM does not return hidden states)". 3회차 L3에서 고친 `models.py:11`은 이제 청크 경로 설명을 이 파일로 넘긴다("…CUDA-graphed expert, fused_action.py"). 그래서 그 링크를 따라가면 바로 틀린 문장을 읽게 된다. | `harvest/runtime/fused_action.py:3-5` | 실제 구현: `harvest/runtime/fused_model.py:4-13` "R5 §5 '2순위': HF for both paths … decide = the R3 shared-prefix forward". 정본 §67 C4 "decide = 공유 접두 순전파 한 번 … vLLM이 은닉 상태를 내주지 않고", §69 L3 정정 목록에는 `core.py`·`models.py`만 있다. `grep -rn "vLLM" harvest/runtime` → 틀린 곳은 이 한 곳뿐이다. `models.py:9,138`(모듈형 JevL은 실제로 vLLM)와 `fused_model.py:15`("like the vLLM server of the modular stack")는 맞다. 같은 docstring 8줄의 "30 Hz chunk (stageb_data.HZ, H = 15)"도 §62 뒤에는 기본값 설명일 뿐이다(NOTE 4). |
| M2 | **(L3·r4 형제, 결과 문서) R5 문서가 융합 decide를 vLLM으로 적고, 정정 표시가 없다.** 76줄 "1순위(**지금 구현**) = **결정은 vLLM**(lead, 접두·멀티모달 캐시), 행동은 … HF 행동 서버", 98줄 "`StageBFused`(**vLLM decide** + HF chunk)는 R4 체크포인트가 나오면 붙인다". 사전 수정(pre-R7) 뒤 구현은 2순위(HF 한 백본)다. 같은 사실을 적은 `r4_stageB.md:140,149`에는 d363f46에서 "정정(정본 §67 C4) … 둘 다 HF 백본" 표시가 붙었지만 R5 문서에는 붙지 않았다(117줄 정정은 D2 로그 스키마 건뿐). | `docs/stage3/results/r5_closed_loop.md:76`, `:98` | `fused_model.py:4-5`, 정본 §67 C4, §69 절차 문장(`00-interfaces.md:581`). 3회차는 `r4_stageB.md:140,149`를 "당시 기록"(N5)으로 두었다. 그러나 §69가 그 뒤에 "원래 문장은 두고 정정 표시를 붙인다"를 명문화했고, 메인은 r4 두 줄에 표시를 달았다. 형제 문서도 같은 기준을 적용해야 한다. `r5_closed_loop.md`는 폐루프 재현 절차(§7)를 담은 문서라 S-E2E 뒤 융합 폐루프를 돌릴 때 다시 읽힌다. |

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(TODO(P3)). 로컬·파드에서 시험 1개 건너뜀(`tests/runtime/test_latency_ctrl.py:11`).
- S2. 본 단계 B 학습·R2_TRAIN 대량 생성(§66 "S-E2E 이후").
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`, 메인 세션만). 가드는 §5.4에서 다시 확인했다.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 목록(M9 복구·T_fail 뒤 하트비트 정지, A5′·M2 R3 합치기, 모듈형 세계 쪽 `unknown`, §52 VQA 기본 끔, 융합 런타임 토크 입력·확인 헤드 보정·동시 부하 지연). 근거("완료 정의 1–5 = 학습 직전 배관")는 계획 목표 줄 7("본 E2E 학습은 하지 않는다")과 맞다.
- S6. Astra 카나리 id = "none"(유료라 미실행). 이번 폐루프 `astra` 2/2에 명시로 실렸다.
- S7. S-E2E 체크포인트를 aiworker 런타임에 넣을 때의 tau 마스크 채널 차이(`r7_fixes.md` §7, §67).
- S8. CONTRADICT-soft(§68 K6, §69 근거 보정). 보정한 근거 문장("argmax 기본값으로 {거짓}은 나온다; CONTRADICT로 보내면 정지·Astra 호출이 더해져 동작이 달라진다; 문턱은 보정된 conformal 집합 위에서 정해야 의미") = 코드(`measure.py` `UNCAL_QHAT`, `m4.py` hold, `core.py` Astra 사건)와 맞다. 미루는 판단도 타당하다.

## 4. NOTE
- N1. **`random5.md` 본문의 500–699 두 줄**: `docs/stage3/results/random5.md:23` "keep-out(DEV 0–29 + 500–699, …)", `:51` "DEV 0–29와 500–699에서 제외 0건". 같은 문서 머리 `:4`에 "정정(R7 2회차): … 시험 시드는 커밋 b4a58ce에서 3000–3199로 옮겼다"가 있어서 이 사실에는 정정 표시가 붙어 있는 셈이다. 51줄은 당시 실측 기록이다. 결함으로 세지 않지만, M1·M2를 고칠 때 23줄 괄호에 "(→ 3000–3199, :4 정정)"을 붙이면 깔끔하다.
- N2. **handoff 잔여 표기**: `docs/handoff.md:80` §2.7 제목 "정본 §43~§64"는 21:03 UTC 시점 요약의 범위라 맞는 기록이다. 바로 아래 81줄은 "§43–§69(끝까지)", 5줄은 "§2.7·§2.8"로 안내한다. `:3` "3회차까지 FAIL(문서만)"은 1회차에 코드 DEFECT 2건이 있었으므로 "(2·3회차는 문서만)"이 정확하다(90줄에는 정확히 적혀 있다).
- N3. **논문의 결정 호출 서빙 서술**: `paper/sec/3_method.tex:34`("호출과 서빙": lead 호출, vLLM 배치 불변 모드)와 `4_setup.tex:17`("같은 vLLM 설정으로 … 가정해 수행")은 결정 호출을 vLLM으로 서빙한다고 쓴다. 융합 런타임의 지금 구현은 HF다(§67 C4). 다만 실물 서빙 방식은 동시 부하 지연 문제(§67 C8 SCOPED, `pre_r7_fixes.md:63` "결정은 vLLM(R5 1순위)·청크는 HF로 나누거나")로 아직 열려 있고, 논문은 설계 초안(주황 잠정값)이다. 그래서 결함으로 세지 않는다. 서빙 방식을 정할 때 3절에 decide → chunk 두 호출 구조(§67 C4)와 함께 반영하기를 권한다. `paper/`는 `stage3-r1r6..HEAD`에서 바뀌지 않았다.
- N4. `harvest/runtime/fused_action.py:8` "the expert's 30 Hz chunk (stageb_data.HZ, H = 15 = 0.5 s)": 런타임은 체크포인트의 hz를 쓴다(`fused_model.py:140` `self.hz = cfg["hz"]`, `:282` `chunk_dt = 1/hz`). 그래서 S-E2E(10 Hz, H 5)에서도 동작은 맞다. M1을 고칠 때 이 줄도 함께 고치기를 권한다.
- N5. **§69 사전 등록 항목은 코드에 선택지가 없다.** `stageb_train.py:364` `val = va[:a.max_val]`(앞 N개, 3회차 N2: N ≤ 1,153이면 RB1만)와 `:367` 끝에 `last`만 저장(중간 체크포인트·재개 없음)은 그대로다. §69는 이것을 "사전 등록에 넣을 것"으로 정했다. S-E2E 사전 등록에서 (a) `--max-val 0`(전체 1,799)과 큰 `--eval-every`를 쓰거나 (b) 층화 무작위 부분집합 옵션을 먼저 추가해야 한다. 어느 쪽인지 사전 등록 문서에 적어야 한다. 학습을 막지는 않으므로 결함이 아니다.
- N6. 카나리는 여전히 09-24 UTC 것이다(`cn20260924_mock_ae0d1a`). 이번 `closed.json` `meta.canary.stale = true`. §68대로 S-E2E·본 실험 시작일에 새로 만든다.
- N7. 로컬 스위트를 **PowerShell**에서 돌리면 2개가 실패한다(`tests/test_cli_e0.py::test_main_writes_session_and_summary`, `tests/test_load.py::test_run_session_writes_header_curl_and_all_phases`). `harvest/load/session.py:15`가 `date` 실행 파일을 부르는데 Git Bash에만 있기 때문이다(`FileNotFoundError [WinError 2]`). Git Bash에서는 784/11로 통과한다. 옛 E0 도구의 환경 의존이고 이번 범위의 변경이 아니다.
- N8. TEST2 1150–1299(`E-first-experiments.md:116,434`, "연장 시")는 `eval/splits.py:13` `RANGES`에 없다. 지금은 어느 분할에도 속하지 않아 `closed`·`e05`(`check_seeds`)·`gen`(DEV만)·`check_layout_seed`(DEV만)가 모두 거부한다. 즉 막혀 있다. 연장을 실제로 쓸 때 `RANGES`/`PROTECTED`에 넣어야 한다.
- N9. `gen --seeds 3000 --confirm-train`의 거부 문구 "CAL / TEST / TEST-P5 / POOL are never generated here"는 3000(시험 전용 범위)에 대해서는 부정확하다. 거부 동작은 맞다(`gen.py:47-49`).
- N10. 폐루프 작업자는 `TMPDIR=/data/harvest/tmp`(`eval/closed.py:142`)라서 한 판마다 공용 tmp에 `carb.*`·`hub-root.lock`·`tmp*`를 남긴다(현재 `carb.*` 246개, 이번 판 것 3개는 지움). 모두 /data 안이라 규칙 위반은 아니다. 누적 정리나 실행별 TMPDIR을 권한다. 앞선 순회의 파드 산출물(`code_r7c1*`, `code_r7fix`, `cache/pyc_r7c1*`, `pyc_r7fix` 등, 3회차 N7)도 남아 있다.
- N11. 로컬 C: 위생: 검증 시작(09:57 KST) 뒤 C:에서 바뀐 것은 `.claude`·`.claude.json`·`AppData\Local\Temp\claude`(하네스), 0바이트 GUID `.tmp`(다른 앱, 2회차 N6과 같음)뿐이다. `pytest-of-USER`·`torchinductor_USER` 없음. kubectl 자체 캐시(`.kube/cache`)는 kubectl이 쓴다.

---

## 5. 확인한 것 (근거)

### 5.1 3회차 L1–L4 해소 여부
| L | 해소 | 확인 |
|---|---|---|
| L1 se2e_data 날짜 | 해소 | `se2e_data.md:3` "작성 2026-09-24 19:48 UTC 무렵(R7 3회차 L1 정정…)". `grep -rn 2026-09-25` 전체: 남은 곳은 [사용자] 제목 5개(§67 C1이 규칙으로 처리), 계획 파일 이름, 실제 UTC 날짜인 것(§67 보충 00:08, §68 00:33, §69 00:55, `r7_fixes.md:6` 00:05, `r5_closed_loop.md:117` 00:08, `se2e_data.md:109` 00:33, handoff 92–93줄 — 커밋 시각 00:35·00:56 UTC와 맞음), KST를 밝힌 `r5_closed_loop.md:4`, 기준 없는 논문 주석(`paper/main.tex:4`, `preamble.tex:88`, `main.bib:505`, `figures/src/make_figs.py:4`, `randomization_pools.json:20` — "UTC"라고 쓰지 않았으므로 "KST를 UTC로" 오기가 아니다)이다. |
| L2 r2_datagen 시드 | 해소 | `r2_datagen.md:139` 끝에 "정정(R7 3회차 L2) … §66 확정 … 3000–3199". `grep -rn "R2_TRAIN\|500.699\|500, 700"`: `test_gen_guards.py:20` `range(500, 700)`는 R2_TRAIN이 CAL을 포함하는 상위 범위와 겹치지 않는지 보는 단정이라 맞다. `random5.md:23,51`은 N1. |
| L3 런타임 주석 | 부분 | `core.py:48` "two calls per step: decide -> chunk, canon §67", `models.py:11` "(decide(), HF backbone)". 형제 `fused_action.py:3-5` → **M1**, `r5_closed_loop.md:76,98` → **M2** |
| L4 handoff 범위 | 해소 | `handoff.md:3,5` §1~§69, `:81` "§43–§69(끝까지)". 80줄 제목은 N2 |

### 5.2 A. 테스트 (각 두 번, 불안정 없음)
- 로컬(Git Bash, `cd /d/qdd && python -m pytest`): **784 passed, 11 skipped**(1회 약 70 s, 2회 69 s). 건너뜀: torch 없음 7, inspect_robots 없음 2, pyarrow 1(파드 안내), TODO(P3) 1. 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json` 생기지 않음. (PowerShell 실행은 N7.)
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + IR 4경로, `CUDA_VISIBLE_DEVICES=""`, basetemp `/data/harvest/tmp/r7c4/pytest_cpu{1,2}`): **826 passed, 3 skipped**(두 번 모두 EXIT 0, 80 s / 73 s). 건너뜀: pyarrow 1, CUDA 없음 1, TODO(P3) 1.
- 파드 GPU 2: `tests/runtime/test_fused_action.py tests/train/test_stageb_torch.py tests/runtime/test_fused_model.py` **26 passed**(GPU 2 시작·끝 1 MiB).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot` + `r2/pylib_pytest`): `tests/datagen/test_episode_files.py` **6 passed**.

### 5.3 완료 정의 1–5 순회 (이번 판에서 직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | S-E2E 로더(단계 B 학습 진입점 안): hz 10, H 5, n_val **1,799**(= §63), `grip_src` {RB1, RB2}, `grip_space open01@v1`, `proprio_masked` 40/40. R2 DEV 재검증은 2회차 값을 그대로 둔다. 543b6b0..1373f3d의 코드 변경은 주석 2줄뿐이다(`git diff --stat -- harvest tools tests` = `core.py`·`models.py` 각 1줄). LeRobot 내보내기 시험 6/6. |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 13` → EXIT 0(01:04:06–01:04:25 UTC). 팔 왼 19·오 21, `model_rev ebb281ec…`, prompt_config 카메라 3배치(왼손목·오손목·양손목, §57). 검증 결정 NLL 3.53 → 1.59 → 1.56. `save_load`: `max_abs_action_diff` **0.0**, `eval_equal` true, `norm_equal` true. `stageb.json`: hz 10, data se2e, `norm.arms` 왼/오 통계가 다름(mean[0] 0.1629 / 0.5533, std[0] 0.680 / 0.431), `grip_space` 있음. 단계 A: 코드 변경이 없어 3회차 판(NLL 비트 동일 재적재)을 그대로 둔다. CUDA 시험 26/26. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 0 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c4`(143.5 s) → `CLOSED_DONE`, **성공 16.46 s**(1–3회차와 같은 값, 결정성), 호출 49·오류 0, 확정 0.76, RTF 0.89, M4 epoch 7, Astra 2. 부가 JSONL(`standard/C5/ours/…/dev0-P0-standard-e0.jsonl`, 행 종류 call 49·step 50·astra 2·event 15·m4 7): `call` 49/49에 64자리 hex `request_sha256`(49개 모두 다름), `image_sha256` {cam_head, cam_wrist_right} 49/49 hex, `canary_id` = `cn20260924_mock_ae0d1a` 49/49. `astra` 2/2에 요청 해시(서로 다름) + `image_sha256` {cam_head} + `canary_id` "none". `closed.json meta`: `code_sha 73a719f041fa25d3`, `canary {id cn20260924_mock_ae0d1a, stale true}`, split dev, seeds [0]. |
| 4 평가 | 충족 | 평가 코드는 3회차 뒤 바뀌지 않았다(위 diff). 3회차의 `e05`·`calib` 한 명령 판을 그대로 두고, 이번에는 가드(§5.4)와 파드 스위트의 `tests/eval`(826 안)로 확인했다. |
| 5 운영 | 충족 | 모든 산출이 `/data/harvest` 아래, `meta`에 `code_sha`·카나리·시드, `MODEL_REV` 고정, 처리량 문서 R3. 문서 잔여 M1·M2(→ FAIL 원인). |

### 5.4 C. 가드 (파드, 변수 없이; `CUDA_VISIBLE_DEVICES=""`; 출력 폴더 `guard_out`은 끝까지 비어 있었음)
- 평가: `e05 --split cal`·`--split test`, `rd --split test_p5`, `calib --fit-split cal` → "--split X refused: set HARVEST_ALLOW_SPLIT=X …". `closed --split test --seeds 1000` 거부. `closed --split dev --seeds 500`·`--seeds 10000` → "seeds [..] are not in split dev … (refused, never opened)". `HARVEST_ALLOW_SPLIT=dev closed --split cal --seeds 500` 거부.
- 생성: `gen --seeds 10000-10001`(확인 인자 없음) → "R2_TRAIN 10000-59999 needs --confirm-train". `--confirm-train`과 함께 500·3000·1149 → 거부. `--variant random` → "TEST pool … use 'dr'". `replay --seed 1300` → 거부.
- `aiworker.check_layout_seed`: 0·29 허용, 30·500·1000·1300·2000·3000·10000 거부.
- 시드 표 일치: `eval/splits.py:13-14` RANGES(DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119) = `E-first-experiments.md:114-119`(+ R2_TRAIN 10000–59999 = `gen.py:35`, §66). 시험 시드 3000–3199(`tests/sim/test_randomize_logic.py:13`)는 모든 예약 범위 밖이다(`test_extra_seeds_avoid_every_reserved_split` 통과). TEST2는 N8.

### 5.5 B·D. 정본 ↔ 코드 ↔ 문서
- 같은 사실 grep(이번에 쓴 명령): `grep -rn "2026-09-25"`, `grep -rn "R2_TRAIN\|10000.?59999\|500.699\|500, 700"`, `grep -rni "one call\|한 번 호출\|한 호출\|decide.{0,40}vLLM\|vLLM decide\|결정은 vLLM"`, `grep -rn "vLLM" harvest/runtime harvest/train harvest/eval`, `grep -rn "§1~§[0-9]*\|§43[–~-]§[0-9]*"`, `grep -rn "never GPU 2\|GPU2 금지\|CUDA_VISIBLE_DEVICES=1 (smoke"`. "한 호출"이 나오는 다른 곳(`00-interfaces.md:17`, `D24`, `D27`, `E-first:56`, `jevl_latency.md`, `r5_closed_loop.md:33,96`, `conditions.py`)은 모듈형 DecCall 하나의 질문 묶음 또는 in-flight 수를 말하는 다른 뜻이다. 정본 `:511` §58 "한 번 호출"은 [사용자] 절 본문이라 §67 C4가 덮는다.
- §63 (1)–(3)·§62 hz: 5.3 실측(팔별 통계, `open01@v1`, tau 마스크 40/40, hz 10·H 5)이 `stageb_train.py`·`se2e_data.md:109`와 맞다.
- §47 카메라: `sim/scene.py:11` 머리 ZED Mini 왼쪽 672×376, 손목 D405 424×240 = 정본 §47(fx 367 / 223.4). 단계 B prompt_config의 카메라 표지 순서 = §59.
- GPU: 계획 29·40줄(GPU 2 = 학습·vLLM, 렌더 금지) = handoff 85줄 = 코드(`closed.py:140,330` 렌더 0·1만, `fused_model.py` 모델 GPU 2·3, `canary`·`e05`·`rd`·`calib` `--gpu` 기본 3). "GPU 2 금지"류 옛 문구는 기록 문서(draft-log, r7_fixes, §68)에만 있다.
- 정본 §67–§69 SCOPED 근거: §3 S5·S8 참고. §69 사전 등록 항목은 N5.
- direction-log 마지막 행(00:55 "R7 3회차 … FAIL(DOC 4) → 4회차")과 draft-log 441줄, handoff 93줄이 서로 맞다.

### 5.6 F. 규칙
- `main` = `origin/main` = `520b2be`(`git ls-remote` 같음), dev = `1373f3d`.
- 비밀값 패턴: `543b6b0..HEAD` 차이 0건, HEAD 트리 0건(개수만 셈).
- `python tools/intent_check.py` → total 62 flagged 0. `543b6b0..1373f3d`에서 `[사용자]`가 든 줄 삭제 0.
- 파드 `/data` 밖: 검증 시작(00:57 UTC) 뒤 새 파일 0(`find / -xdev -newermt "2026-09-25 00:57:00 UTC"` = 0; `/tmp`·`/root`·`/home1`·`/var/tmp`·`/isaac-sim`·`/dev/shm`·`/opt`·`/usr/local` 각각 0). 내 프로세스 0. GPU 0–3 = 896 / 5 / 1 / 1 MiB(시작 때와 같음). 공용 `/data/harvest/canary`는 바뀌지 않았다(시각 08:57–08:59 KST 그대로).
- 로컬 C:: N11.

## 6. 다음 순회 전에 할 일 (제안, 모두 주석·문서)
1. M1: `harvest/runtime/fused_action.py:3-5`를 "decide() = decision-token probabilities from the HF shared-prefix forward of the fused server (runtime.fused_model; canon §67 C4 — vLLM does not return hidden states) -> M4 commit -> chunk(committed) = expert flow sampling on the cached context"로 고친다. 8줄은 "the expert's chunk at the checkpoint hz (30 Hz R2 / 10 Hz S-E2E, stageb.json)"로 고친다(N4).
2. M2: `r5_closed_loop.md:76`과 `:98` 끝에 "→ **정정(정본 §67 C4, R7 4회차)**: 사전 수정(pre-R7)에서 2순위(HF 한 백본: decide = 공유 접두 순전파, chunk = 캐시 문맥 + CUDA 그래프 expert, `harvest/runtime/fused_model.py`)로 구현했다"를 붙인다.
3. 같은 사실 grep: 이번 5.5의 명령에 `grep -rn "vLLM" harvest docs/stage3 paper`를 더해 "융합 decide = vLLM"이 남은 곳이 없는지 확인한다. (N1 `random5.md:23`, N2 `handoff.md:3`도 같은 묶음으로 손보면 좋다.)
4. (권장, S-E2E 사전 등록) N5: 검증 부분집합(`--max-val 0` 또는 층화 옵션 추가), `--eval-every`, 중간 저장 여부를 사전 등록 문서에 적는다. N6: 시작일 카나리를 새로 만든다.

> 정정(2026-09-25 01:48 UTC, R7 5회차 P1·sweep6): 17줄 '코드는 네 번째로 무결하다'는 틀렸다 — 1회차에 코드 DEFECT 2건이 있었으므로 이 4회차까지 코드 무결은 2·3·4회차 **3회 연속**이다. 위 판정·발견 목록은 검증 기록이라 고치지 않는다.
