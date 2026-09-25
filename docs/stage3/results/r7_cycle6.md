# R7 객관 검증 순회 — 6회차 (cycle 6, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님). 작성 2026-09-25 02:17 UTC(`date -u`; 파드 `date -u` = `Fri Sep 25 02:01:14 UTC 2026`(시작)·`02:15:24`(정리), 로컬과 같음).
- 대상: `D:\qdd` `dev` 브랜치 HEAD `ac7095a` = `origin/dev`(`git ls-remote`), `main` = `origin/main` = `520b2be`. 작업 트리 깨끗(검증 전후 `git status` 출력 없음). 파드 사본 = `git -c core.autocrlf=false archive HEAD`(LF 블롭, `stageb_data.py` `git hash-object` = HEAD 블롭 `a174e306…`), 폐루프 `meta.code_sha` = `f642bc0994e7cc54`(5회차 `6f7d5a66…`와 다른 것은 ac7095a가 `closed.py`·`m4.py` 등 주석을 바꿨기 때문).
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류(DEFECT / DOC / SCOPED / NOTE), `r7_cycle2.md`–`r7_cycle5.md`, `r7_fixes.md`, `r7_sweep6.md`, 정본 `00-interfaces.md` §1–§71(뒤 절 우선; §67–§71 SCOPED는 결함으로 다시 세지 않되 근거를 확인, [사용자] 제목 절 본문은 §67 규칙대로 세지 않음, 논문 .tex의 vLLM 서빙 서술은 §70에 따라 NOTE, `r7_sweep6.md` §3의 "여전히 열린 것"은 완료 정의 1–5를 막지 않으면 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5.
- 분류 기준(1–5회차와 같음): **DOC** = 지금도 참고되는 문서(정본·계획·handoff·결과 문서·코드 주석)가 HEAD의 코드·상태와 다른 **현재 시제** 서술을 하고, 그 줄(또는 그 줄을 명시로 가리키는 같은 문서의 정정 줄)에 정정·해결 표시가 없는 것. 표시가 붙은 옛 줄, 날짜가 붙은 기록 절, 단계 2 설계 문서 본문(머리 안내 줄 + 정본 우선)은 해결된 것으로 본다.
- 규칙 준수: 코드·문서 수정·커밋 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`로 실행(전역 설정 안 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c6`(스크립트는 Write 도구로 D:에 씀, Git Bash heredoc 안 씀, kubectl 경로 변환은 `MSYS_NO_PATHCONV=1`). 파드 파일은 모두 `/data/harvest/tmp/r7c6`(코드 사본·산출·체크포인트·pytest·pyc, 2.2 GB), Isaac kit 캐시 `ir/kitcache/cyclo-r7c6_standard`·`cyclo-r7c6f_standard`, 폐루프 작업자가 쓴 `cache/pyc_r6/data/harvest/tmp/r7c6`·`tmp/{carb.jlVTwh,carb.kjmYN1,tmpex7ztn5u,tmpumthnh5i,hub-root.lock}`(생성 시각 02:04:12–02:10:46 UTC = 내 두 폐루프 판, `hub-root.lock` 생성 02:04:15), 융합 서버가 만든 빈 폴더 `tmp/fused_frames/2921117`, LeRobot 시험이 만든 `cache/hf/datasets/parquet/default-0550a1269cbe6f1d`(+잠금 파일)에만 썼고 **끝에 모두 지웠다**(02:15 UTC 확인; 남은 것은 공용 폴더 시각뿐). GPU: 단계 A·B 학습·CUDA 시험·융합 서버 = GPU 2(렌더 없음, 시작·끝 1 MiB), Isaac = GPU 1(시작·끝 5 MiB), GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음. 시드 DEV만, `HARVEST_ALLOW_SPLIT`은 가드 음성 시험 1건에서 `=dev`만. 유료 API 호출 없음(Astra 모의). 비밀값 출력·검색 없음(패턴 검사는 개수만).

## 판정: **PASS**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 8 |
| NOTE | 14 |

코드는 2–6회차 **다섯 번 연속 무결**하다(1회차는 코드 DEFECT 2). 5회차 P1·P2는 해소됐고, sweep6(ac7095a)이 붙인 해결·정정 표시 28개를 코드·정본·후속 문서와 대조해 모두 사실임을 확인했다(§5.2). ac7095a의 `harvest/`·`tests/` 차이는 주석·docstring·오류 문구뿐이며(시드 거부 동작은 같음, 직접 실행 확인), `stagea_train.PROMPT_FILES`·`stageb_data.py`·`stageb_model.py`는 b4a58ce 이후 바뀌지 않았다. 요청받은 문구·구현 이름 grep에서 표시 없는 현재 시제 오류는 찾지 못했다. 완료 정의 1–5를 직접 다시 돌려 모두 충족함을 확인했다(이번 판은 융합 백엔드 실체크포인트 서빙 폐루프도 다시 돌림). **연속 무결 0 → 1회**.

---

## 1. DEFECT

없음.

## 2. DOC

없음.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(TODO(P3)) — 이제 정본 §71 보충(01:59 UTC)에 SCOPED로 적혔다. 근거("기준선 비교는 본 실험 단계, 완료 정의 1–5와 무관")는 계획 완료 정의 4(E0.5·RD·CAL 보정 스크립트, 기준선 없음)와 맞다. 로컬·파드에서 시험 1개 건너뜀(`tests/runtime/test_latency_ctrl.py:11`).
- S2. 본 단계 B 학습·R2_TRAIN 대량 생성(§66 "S-E2E 이후").
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`, 메인 세션만). 가드는 §5.5에서 다시 확인.
- S4. RB1 라이선스(§63-(6), `se2e_data.md` §9-6, handoff §2.7 "논문 전 확인").
- S5. §67 C8 목록(M9 복구·T_fail 뒤 하트비트 정지, A5′·M2 R3 합치기, 모듈형 세계 쪽 `unknown`, §52 VQA 기본 끔, 융합 런타임 토크 입력·확인 헤드 보정 파일·동시 부하 지연). 근거("완료 정의 1–5 = 학습 직전 배관, 위 항목은 학습된 체크포인트·본 실험이 있어야 의미")는 계획 7줄("본 E2E 학습은 하지 않는다")과 맞다. 코드도 그대로다: `core.py:355`(patch/replace = epoch만), `fused_model.py:17-19`(tau 학습 평균 대치), `pre_r7_fixes.md:64` `VerifyCal.default()`.
- S6. Astra 카나리 id = "none"(유료라 미실행). 이번 두 폐루프 판의 `astra` 행 2/2·5/5에 명시로 실렸다.
- S7. S-E2E 체크포인트를 aiworker 런타임에 넣을 때의 tau 마스크 채널 차이(`r7_fixes.md` §7, §67).
- S8. CONTRADICT-soft(§68 K6, §69 근거 보정). `measure.py`는 여전히 단일 DEVIATE(`pre_r7_fixes.md:116` 표시와 맞음).
- §70 세 번째 줄(논문 vLLM 서빙 서술 보류)과 §71의 "PROMPT_FILES는 주석도 고치지 않음" 근거도 타당하다: `fused_model.check_prompt`(`:319-335`)는 `files_sha`(바이트 sha256, `stagea_train.file_sha`)가 다르면 `strict_prompt=True`(기본, `:112`)에서 거부한다.

## 4. NOTE
- N1. **(새로 찾음) 융합 폐루프 판의 `closed.json` `meta.prompt_config`는 모듈형 Jev-L 프롬프트 구성이다.** 이번 융합 판(`--backend fused --model <단계 B 체크포인트>`)의 `meta.prompt_config` = `{"camera": "HW", "state": "S1", "step_cm": 0.1, "names": "A0", …}` — `closed.py:393` `C.prompt_config_eval(layout)`를 백엔드와 무관하게 싣는다. 모델이 실제로 받은 것은 IMG 상태·D27v1 배치다. 실제 대조는 맞게 돈다: 융합 서버가 `check_prompt`로 체크포인트 `prompt_config`와 런타임 입력을 엄격 대조하고(`fused_model.py:130`), 같은 `meta`의 `model.train_prompt_config`(state IMG)와 트라이얼 `policy_config`(`selector stageb`, `question_ids` 5개, `state_repr` "fused: images …")도 맞다. `closed.md` 머리의 "prompt_config <sha>"가 융합 판에서는 쓰이지 않은 S1 구성의 해시라 오해할 수 있다 — 융합 판이면 이 필드를 체크포인트 구성으로 바꾸거나 `modular_prompt_config`로 이름을 바꾸기를 권한다. 정본 §42 필수 필드(요청 해시·카나리 id·question_id@vN)는 모두 있어 결함으로 세지 않는다.
- N2. **handoff의 날짜 붙은 단계 2 절 안 현재 시제 줄**: `docs/handoff.md:46` "사용자 [결정 필요]: `SUMMARY.md` §5.1 … plan §8의 18·19"(§2.5, 2026-09-24 01:30 UTC 절), `:55` "다음(단계 3, 사용자 go 대기) … 사용자 지시 전에는 시작하지 않는다"(§2.6), `:13` "현재 계획 **v5.6**". 줄마다 표시는 없지만 머리 `:5`가 "단계 3 이전 판본(plan v6.8, SUMMARY v3.10, §1의 v5.6)은 옛 기록 … 최신 상태는 §2.7·§2.8"로 명시해 덮고, §2.7 `:88` "사용자 대기 항목: 없음"이 현재 상태다. 1–5회차와 같은 판단. 다음 정리 때 `:46`·`:55` 끝에 "(→ §2.7·§2.8)" 포인터를 붙이면 더 안전하다.
- N3. **결과 문서 본문 줄이 해결된 열린 문제 번호를 가리키는 경우**: `stageA_pipeline.md:53` "`question_id@vN`: DecCall 경로는 아직 `qid.py` 레지스트리에 연결돼 있지 않아서 … (열린 문제 5)" → 가리키는 `:118`(열린 문제 5)에 해결 표시 있음. `stageA_pipeline.md:4` "본 학습은 시작하지 않았다"(작성 당시 기록, 이후 `stageA_sft.md`), `r3_throughput.md:127` "`se2e_data.md`는 아직 없어"(당시 기록). 기록 성격이라 세지 않는다.
- N4. `CLAUDE.md:33,38,85,86,91`의 Jev 서술(텍스트 입력만, Astra + Jev 계층 등)은 Jev에 대한 사실로는 맞고 사용자 규칙 파일이다. 첫 규칙(`:6`)이 handoff를 먼저 읽게 하고 handoff §2.7이 "Jev 사용 불가 → Jev-L → 융합"을 적는다. 고칠지는 사용자·메인 몫(sweep6 §4와 같은 판단).
- N5. `harvest/train/stageb_data.py:15` "Task-space Jev-authority projection (§35)"는 PROMPT_FILES_B라 표시를 붙이지 않은 것이 맞다(§71). §35의 Jev 권위 = 지금은 Jev-L·융합 결정 토큰이라는 풀이는 `r4_stageB.md:40`에 있다.
- N6. 논문 결정 호출 서빙 서술(`paper/sec/*.tex`)은 vLLM 기준(§70 보류). `paper/`는 `541068a..HEAD`에서 바뀌지 않았다.
- N7. `r7_sweep6.md` §3의 열린 항목을 코드로 다시 확인했다 — 모두 여전히 열림이고 완료 정의 1–5를 막지 않는다: 잔차 모드 체크포인트 거부(`fused_model.py:126`), θ 게이트 런타임 없음(`eval/calib.py:161` 노트, `core.py`에 θ 없음; J5는 `core.py:306` `_j5`가 보정 파일 + `j5_alpha`일 때만), 계약 편집 = epoch만(`core.py:355`), aiworker P1/P2 막힘(`aiworker.py:130`), 단계 B `evaluate`는 표본 1개씩(`stageb_train.py:135`, `r3` §8-4), `jevcall.PROGRESS` 보기 이름(`tests/test_jevcall.py:28`).
- N8. 카나리는 여전히 09-24 UTC 것이다(`cn20260924_mock_ae0d1a`, 모의 판 `meta.canary.stale = true`; 융합 판은 `{"id": "none", "reason": "no canary for model fingerprint bf13614a3166f11c"}`). §68대로 S-E2E·본 실험 시작일에 새로 만든다.
- N9. TEST2 1150–1299(`E-first-experiments.md`)는 `eval/splits.py` `RANGES`에 없어 모든 도구가 거부한다(4·5회차와 같음). 연장을 실제로 쓸 때 넣어야 한다.
- N10. §69 S-E2E 사전 등록 항목은 코드 선택지가 없다(5회차 N7과 같음): 이번 판도 n_val 1,799 중 `--max-val 4` = 앞 4개. 정규화 통계는 학습 부분집합에서 맞춘다(이번 팔별 mean[0] 왼 −0.0097 / 오 0.2028, 5회차와 다른 값은 `--seed`·부분집합이 달라서).
- N11. 파드 공용 `TMPDIR=/data/harvest/tmp`의 남은 것(내 것은 모두 지움): `carb.*` 245개, `fused_frames/<pid>` 빈 폴더 7개(융합 서버 기본 `frame_dir`, `fused_model.py:145`), 1회차가 남긴 `tmp/r7c1`(2.0 GB, 09-24 23:27 UTC, 1회차 보고서가 "지워도 됨"이라 적음). 모두 /data 안이라 규칙 위반은 아니다. 남의 것이라 지우지 않았다.
- N12. `docs/handoff.md:3` "마지막 갱신: 2026-09-25 01:48 UTC"는 sweep6 편집 끝(보고서 작성 01:54)·커밋(01:59:41 UTC)·§71 보충(01:59)보다 이르다. 같은 줄의 내용(정본 §1~§71, 상태는 §2.8 마지막 줄)은 맞으므로 서술 오류는 아니다.
- N13. 로컬 스위트는 Git Bash에서만 돌렸다. PowerShell 실행 시 `harvest/load/session.py`의 `date` 의존 문제(4·5회차 N)는 이번 범위에서 바뀌지 않았다.
- N14. 로컬 C: 위생: 시작 표식(02:01:00 UTC) 뒤 C:에서 바뀐 것은 `.claude`·`.claude.json`·`AppData\Roaming\npm\claude*`·`AppData\Local\npm-cache\_logs`(하네스), `.kube` 캐시(kubectl), `AppData\Roaming\{Code,Microsoft\Credentials}`(다른 앱), `AppData\Local\Temp\mat-debug-34812.log`(다른 앱 — 이 저장소 것 아님)뿐이다. `pytest-of-USER`·`torchinductor_USER` 없음. 로컬 파이썬 실행이 만든 `__pycache__`는 저장소 안(무시 대상, `git status` 깨끗).

---

## 5. 확인한 것 (근거)

### 5.1 5회차 P1–P2 해소 여부
| P | 해소 | 확인 |
|---|---|---|
| P1 handoff 상태 줄·횟수 | 해소 | `handoff.md:3` "회차별 판정·연속 무결 횟수는 §2.8 마지막 줄, 정본 §1~§71", `:5` §1~§71, `:83` "§43부터 끝까지(지금 §71)". `:96`·`direction-log.md:52` "코드 무결 4회 연속(→ **정정(R7 5회차 P1)**: 3회 연속 — 2·3·4회차 …)", `r7_cycle4.md` 끝 정정 줄. `:97`·`direction-log.md:53` 5회차 "코드 무결 4회 연속(2–5회차)" = 맞음(1회차 DEFECT 2, 2–5회차 0). |
| P2 해결된 어댑터 서술 | 해소 | `r6_eval.md:54`·`r5_closed_loop.md:98` 끝에 "→ **해결(pre-R7 519de26 …)**" + "위 서술은 당시 기록". 해결 내용은 코드와 맞다: `closed.py:18`(Backends: fused = mock_fused 또는 REAL 체크포인트), `:338-341`(`info["kind"] == "stageb"` → `selector = "stageb"`), `fused_model.py:43` `proprio23`(23-D ← 8-D). 이번 판에서 실제로 `closed --backend fused --model <체크포인트>`를 돌려 확인(§5.4 정의 2·3). |

### 5.2 sweep6 표시 대조 (28개, 모두 사실)
| # | 표시 위치 | 주장 | 확인 |
|---|---|---|---|
| 1 | `r6_eval.md:14` | 단계 B 체크포인트면 `runtime.fused_model` HF 서버 | `closed.py:8-9,18`, 이번 융합 판 `vllm_ready 15.1 s`는 fused 서버 기동 시간(`common.Server`) |
| 2 | `r6_eval.md:56` | 점수식 plan, 판별력 0.025, 거부권 용도 | 정본 §65 |
| 3 | `r6_eval.md:59` | 쥠 디바운스 `HOLD_DEBOUNCE_S`, DEV 0–9 10/10 | `skills.py:41,130`, `pre_r7_fixes.md:93` |
| 4 | `r6_eval.md:60` | `astra_hb.py` K0–K4, `--hb-mode/--hb-budget/--astra scripted` | `astra_hb.py:4-14,34`, `closed.py:194-196,264-267` |
| 5 | `r5_closed_loop.md:92` | T_sub(K1)·K3/K4 구현, A5′·R3 SCOPED, T0·`detect_phrase` 열림 | `astra_hb.py:6`, 정본 §67 C8, `core.py:355` |
| 6 | `r5_closed_loop.md:93` | `measure()`·critic 구현, M9 SCOPED | `measure.py:108-122`, `core.py:136` `Critic`, §67 C8 |
| 7 | `r5_closed_loop.md:94` | J5 런타임(보정 파일 + `--j5-alpha`일 때만), θ 오프라인만 | `core.py:306-335`(`al is None`이면 건너뜀) |
| 8 | `r5_closed_loop.md:85-86` | 청크 그래프 30.0 ms, 폐루프 청크 p50 80–591 ms | `pre_r7_fixes.md:41,52-54` |
| 9 | `r5_closed_loop.md:89` | user-log 62 원문 "프로600에서 하는걸 가정해서 여기서 다할거고" | `user-log.md` 62 인용과 같음(5회차 N3 확인 그대로) |
| 10 | `r4_stageB.md:147` | `GraphedSampler`, 그래프 대 eager 차 0.0 | `fused_action.py:43`, `pre_r7_fixes.md:41-44` |
| 11 | `r4_stageB.md:148` | 공유 접두 `samples_forward`·`forward_shared` | `prefix_share.py:278`, `stageb_model.py:112` |
| 12 | `r4_stageB.md:151` | VQA SCOPED | §67 C8, `stageb_train.py` `cmd_train` `"vqa": 0.0` |
| 13 | `r4_stageB.md:153` | `apply_residual`·훅 0, 잔차 체크포인트 거부 | `skills.py:249,254`, `fused_model.py:126` |
| 14 | `r4_stageB.md:155` | `g2goal_*` = labels_v2 Δ | `datagen/rows.py:4,33-42`, `r2_datagen.md:32` |
| 15 | `r4_stageB.md:156` | `pytest.ini` basetemp D:, `tests/conftest.py` | `pytest.ini`, `tests/conftest.py` 있음 |
| 16 | `r3_throughput.md:164` | 런타임 `question_ids`, 보정 파일 qid 대조 거부, 융합 prompt_config 거부 | `run_r5.py:20,101`, `calibration.py:203-212`, `fused_model.py:319-335` |
| 17 | `stageA_pipeline.md:114` | 풀 labels_v2 경로 | `stageA_sft.md:12` |
| 18 | `stageA_pipeline.md:120` | `--cameras HW` 기본 | `stagea_train.py:11,416-417` |
| 19 | `e_m4b_meas.md:247` | 빈 집합 = unknown | `measure.py:108-113`(`has1 == has0` → None) |
| 20 | `r2_datagen.md:143` | (1)–(4) → §66 | 정본 §66 결정 (1)–(4) 문구와 같음 |
| 21 | `e3st.md:255` | 명사 표 → §46 `detect_phrase` | 정본 §46 |
| 22 | `M1:120`·`D21:121` | fx 367이면 0.6 m 약 3.9 mm, 1.0 m 약 10.8 mm | 직접 계산: δZ = Z²·0.25/(367·0.063) = 3.89 mm / 10.81 mm. fx 367·실측 364.0 = 정본 §47, `FFW_SG2_REAL_cameras.py:5-12` |
| 23 | `D21:212` | (a) §37·§38 (b) §43 (c) §38 (d) §39 | 정본 §37–§39·§43 본문과 맞음 |
| 24 | `D20`·`D23`·`D24`·`D26` [결정 필요] 해소 | §35(양자화·D-AE 내부 절제), §42(주 표·정보 동등), §47·§49(손목 D405·RTX PRO 6000), §52 잠정 결정 1–3 | 각 정본 절 문구와 같음 |
| 25 | `r7_fixes.md:51` | 파드 `ir_run.sh`도 저장소 판으로 동기화 | 파드에서 `diff`(CR 제거) → 같음, `:56` "렌더는 GPU 0·1 만 … GPU 2 는 학습 전용" |
| 26 | `harvest/runtime/m4.py:21-24` | J5는 core.py(R6), θ 오프라인만 | 7번과 같음 |
| 27 | `harvest/canary.py:1-4`·`clients/jev.py`·`cli_e0.py` | `eval.canary`가 `canary_compare` 호출, `CallRecord`를 `jevl.py`가 재사용, `jevl_latency.md` 있음 | `eval/canary.py:173,221`, `jevl.py:22`, `results/jevl_latency.md` |
| 28 | `harvest/train/stagea_train.py:7-9` | `load --adapter [--pool] [--n] [--seed]`, `--rule`은 outcome일 때만 | `:401-411` 파서(`--pool` 기본값 있음, `--rule` 기본 "") |

- 코드 차이(ac7095a): `git show ac7095a -- harvest tests` = `canary.py`·`cli_e0.py`·`clients/jev.py`·`clients/jev_smoke.py`·`config.py`(줄 끝 주석)·`datagen/gen.py`(오류 문구)·`eval/closed.py`·`runtime/m4.py`·`train/stagea_train.py`(docstring)·`tests/datagen/test_gen_guards.py`(주석 1줄). `gen.check_r2_seed`를 로컬에서 직접 불러 (0,F)(29,T)(10000,T) 허용, (10000,F)(500,T)(3000,T)(60000,T)(1149,F) 거부 — 예외 종류·허용 집합은 그대로, 문구만 바뀜.
- 체크포인트 프롬프트 해시: `git diff --stat b4a58ce HEAD --` PROMPT_FILES 9개 + `stageb_data.py` + `stageb_model.py` → 빈 출력. 이번 단계 B 체크포인트 `files_sha`의 `stageb_data.py` = `be1e6214d840`(sha256 앞 12자리), 파드 사본 `git hash-object` = HEAD 블롭 `a174e306…`.
- 정본 차이: `git show ac7095a -- docs/design/00-interfaces.md`의 hunk는 `@@ -588,0 +589,11 @@` 하나(끝에 §71만 덧붙임). `[사용자]`가 든 지운 줄 0(`541068a..HEAD`), `tools/intent_check.py` → total 62 flagged 0. sweep6이 지운 줄은 모두 같은 내용에 표시를 덧붙인 것(M1·D21 등 표본 확인).

### 5.3 같은 사실 grep (이번 판 명령, 추적 파일, `paper/`·`r7_cycle*`·`r7_sweep6`·`third_party/` 제외, 표시 유무 분리 — `D:\tools\scratch_qdd\r7c6\g.py`)
- `vLLM` + (decide|fused|StageB|융합|결정 호출): 표시 없는 줄은 `pre_r7_fixes.md:24`(모듈형 vLLM 서버와 "같은 배치" = 프로세스 배치 비교, 맞음), `r6_eval.md:14`(같은 줄에 pre-R7 HF 서버 괄호), `eval/canary.py:9,257`·`closed.py:18`·`fused_model.py:15`(모듈형 = vLLM, 융합 = fused 서버로 구분해 적음 — 맞음). 융합 decide = vLLM을 표시 없이 적은 곳 0.
- `one call|single call|한 번 호출|모델 한 번`: 표시 없는 것은 §58 [사용자] 절 본문(`00-interfaces.md:511`, §67 C4가 덮음), `D12:49`(타 논문), `research/v3/04`(단계 1 조사), `jevl.py:8`·`conditions.py:5,11`·`models.py:1`·`tools/jevl_mmbench.py:3`(DecCall 하나·in-flight 수 — 다른 뜻).
- `\[제안\]|\[proposal\]`(단계 3 범위): `r2_datagen.md:139`(L2 정정 표시), `e3st.md:104,149`(M1 쪽 제안 — 지금도 제안), `CLAUDE.md:62`·`handoff.md:13`(표기 규칙·옛 판본, N2). R2_TRAIN을 제안으로 적은 표시 없는 곳 0.
- `500–699`: `random5.md:4,23,51`(정정 표시), `r2_datagen.md:139`(정정), `test_gen_guards.py:20-21`(CAL을 덮는 범위로 R2_TRAIN과 겹치지 않는지 보는 단정 — 맞음), 정본 §68·§69(기록).
- `2026-09-25`: [사용자] 제목 §56·§57·§58·§60·§62(§67 C1 규칙), 실제 UTC 날짜인 것(§67 보충 00:08, §68 00:33, §69 00:55, §70 01:14, §71 01:48, sweep6 개정 줄 01:48, `r7_fixes.md:6` 00:05, handoff 94–97), KST를 밝힌 `r5_closed_loop.md:4`, 계획 파일 이름, 기준 없는 `randomization_pools.json:20`(데이터 파일, 4·5회차 판단 그대로). 잘못된 UTC 날짜 0.
- `GPU 2` + 금지/never/렌더: 계획 `:29`(취소선 + 대체), `:40`, handoff `:87`, `closed.py:11,36,141,331`·`test_closed_pure.py:102`(Isaac 렌더 거부 — 맞음), `stagea_train.py:22`·`stageb_train.py:17`·`tools/r3_bench.py:11`(GPU 2 = 학습 계산), `tools/ir/ir_run.sh:56`, 나머지는 당시 기록(`pool.md:4`, `stageA_generalize.md:42`, direction-log). 현재 시제로 "GPU 2 금지"라 적은 곳 0.
- `102°|fx 272|≈272|ZED_M|D-stereo`(표시 없는 줄): 정본 §37 본문(`:345,353`, §43·§47이 덮음), `D21:118`(바로 아래 `:121` 정정 줄), `D21:185`(원문 인용 — ZED 확장 목록), `D21:209`(결정할 것 (b), `:212` 해소 줄), `D23:94,131`(`:6-7` 머리 정정 줄), `handoff.md:50`(바로 아래 `:51` 정정 줄), `e3st.md:154,268-270`(fx 272.1 → 367 재계산 기록 자체), `cli_e3st.py:19-20`·`test_stereo_metrics.py:36`(옛 값 재현 옵션 — 맞음), `planner_dev.md:139`·`scene_bringup.md:129,179`(ZED_M을 쓰지 않았다는 기록), 옛 계획 `2026-09-24-stage3-experiments.md:102,1319,1347`(머리 `:7` 개정 줄, 지금 계획은 e2e-ready).
- 정본 범위 `§1~§N`·`§43~§N`: handoff `:3,:5` §1~§71, `:83` "끝까지(지금 §71)", `:82` 제목 §43~§64(21:03 시점 절 제목 — 기록). 그 밖은 단계 2 문서의 당시 범위.
- `\bJev\b`(Jev-L 아님, 단계 3 범위): `CLAUDE.md`(N4), 옛 계획(머리 개정 줄), Jev 옛 도구(`canary.py`·`jev.py`·`jev_smoke.py`·`cli_e0.py`·`config.py` — 이제 "쓸 수 없음" 표시), 시험 파일(옛 도구 시험), `r4_stageB.md:40`(표시), `stageb_data.py:15`(N5). Jev를 지금 쓰는 선택기로 적은 표시 없는 곳 0.
- `20 Hz`: 모두 풀·계획기·라벨 경로의 옛 20 Hz(`scene.py:377,584`, `planner.py:192-194`, `skills.py:41`, `gen.py:37`, `m4b/fidev.py`)이거나 R2 문서의 "기존 20 Hz 동작 유지" 서술. 우리 수집 주기를 20 Hz로 적은 곳 0(R2 = 30 Hz, S-E2E = 10 Hz, 정본 §62).
- `진행 중|재생성 중|in progress|아직|미구현` 등(표시 없는 줄): direction-log 30분 루프 행(시각 기록), 결과 문서의 "이 시각 전에 한 일"·당시 기록(N3), `se2e_data.md:112`(`:109` 갱신 줄이 1–3을 덮음), `r4_stageB.md:39`(VQA 원천 없음 — 지금도 사실, 열린 문제 5 SCOPED), 코드의 `in_progress`(큐 상태 키)·Astra 보기 문구. handoff §2.7 "진행 중(21:03 기준): 결과 라벨(T14, GPU 0)"은 지금도 사실이다(파드 `cli_label label --pool … --seeds 2000-2119`, 경과 10:51, GPU 0 896 MiB).
- `not implemented|not wired|TODO|NotImplemented|stub`(코드): `latency_ctrl.py`(S1), `aiworker.py:130`·`core.py:355`·`astra_hb.py:17`·`fused_model.py:126`·`m4.py:21`·`calib.py:161`(N7), `perturb.py:8`(P3–P5 TEST 전용), `scene.py:265`(오른팔 한 팔) — 모두 문서의 열린·범위 밖 목록과 맞음.
- `결정 필요`(단계 3 결과 문서·D2x, 표시 없는 줄): 표기 규칙 줄(`D24:7`, `D26:5`), 조건부 규칙(`D25:191`, `D28:180`, `e_m4b_meas.md:50,211` — PC5 미실행이라 올리지 않음), `e3st.md:30`(Task_0001 라이선스 — 지금도 열림, S4와 같은 부류), handoff 표기·옛 절(N2).
- 시드 범위 문장: DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 / 시험 3000–3199(`test_randomize_logic.py:13`, `gen.py:36`) 외의 값을 현재 시제로 적은 곳 0.

### 5.4 완료 정의 1–5 순회 (이번 판에서 직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV 36편 읽기 전용 구조 검사(`datagen.validate.validate_episode`만, `stamp` 안 함; `pod_data.py`): **36/36 오류 없음**, 성공 mug_tray 12/12·mug_marker 12/12·bottle_tray 8/12(= 정본 §66). S-E2E 로더(단계 B 학습 진입점): hz 10, H 5, n_val **1,799**(= §63), `grip_src` {RB1, RB2}, `grip_space open01@v1`, `proprio_masked` 40/40, 팔 왼 20·오 20. LeRobot 내보내기 시험 6/6(`venv_e3st` + `r2/pylib_lerobot`). |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c6_se2e --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 29` → EXIT 0(02:02:00–02:02:46 UTC). `model_rev ebb281ec…`, prompt_config 카메라 3배치(§57), state IMG, 검증 결정 NLL 3.526 → 1.993 → 1.682. `save_load`: `max_abs_action_diff` **0.0**, `eval_equal`·`norm_equal` true. `stageb.json`: hz 10, data se2e, `norm.arms` 왼/오 통계 다름(mean[0] −0.0097 / 0.2028, std[0] 0.473 / 0.492). **단계 B R2**(GPU 2): `--data r2 --pool r2/dev/standard/mug_tray/P0,r2/dev/dr/mug_marker/P0 --dev-val-seeds 5 --max-train 40 --max-steps 6 … --reload-check --seed 31` → EXIT 0, `save_load` 차 **0.0**, 평가 전후 같음(aux·dec 포함 모든 손실 계산). **서빙**: 이 R2 체크포인트로 `closed --backend fused`(모델 서버 GPU 2, Isaac GPU 1) — 정의 3 행. **단계 A**(GPU 2, `TORCH_DISABLE_NATIVE_JIT` 미설정 — 모듈이 스스로 설정): `stagea_train train --run a_c6 --max-steps 4 --max-train 96 --max-val 24 --accum 16 --eval-every 2 --seed 23` → EXIT 0(02:07:21–02:07:54), 검증 NLL 4.429 → 2.555 → **1.1434364318847656**; `load --adapter best --n 24 --seed 23` → NLL **1.1434364318847656**(비트 동일). CUDA 시험(GPU 2) 26/26. |
| 3 폐루프 | 충족 | (a) `closed --model mock --split dev --seeds 0 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c6`(02:04:11–02:06:54) → `CLOSED_DONE`, **성공 16.46 s**(1–5회차와 같은 값, 결정성), 호출 49·오류 0, RTF 0.887, M4 epoch 7, Astra 2. 부가 JSONL(행 종류 call 49·step 50·astra 2·event 15·m4 7): `call` 49/49에 64자리 hex `request_sha256`(49개 모두 다름), `image_sha256` {cam_head, cam_wrist_right} 49/49 hex, `canary_id` = `cn20260924_mock_ae0d1a` 49/49; `astra` 2/2에 요청 해시(서로 다름) + `image_sha256` {cam_head} + `canary_id` "none". `closed.json meta`: `code_sha f642bc0994e7cc54`, `canary {id cn20260924_mock_ae0d1a, date_utc 2026-09-24, stale true}`, split dev, seeds [0]. (b) **융합 실체크포인트**: `closed --backend fused --model tmp/r7c6/ckpt/r7c6_r2/last --split dev --seeds 0 --max-seconds 20 --astra mock --isaac-gpu 1 --gpu 2 --inst-prefix r7c6f`(02:10:15–02:13:00) → `CLOSED_DONE`, 끝까지 돎(`max_steps` — 6스텝 모델이라 성공은 요구 아님, 2회차와 같음), 결정 61·청크 60·호출 오류 0, 결정 지연 p50 0.331 s, RTF 0.79, M4 epoch 54, Astra 5, `measure` 58행. `call` 61/61·`chunk` 60/60·`astra` 5/5 모두 hex 요청 해시(모두 다름)·이미지 해시·`canary_id`("none", 이유 명시). 트라이얼 `policy_config`: `backend fused`, `selector stageb`, `question_ids` 5개(`dir_xy 4701591c8818@v1` …). meta 필드 표기는 N1. |
| 4 평가 | 충족 | 한 명령 실행(모의 모델, GPU 없음, `venv_vllm`): `e05 --split dev --episodes 1` → `E05_DONE`, `rd --variants standard=… --split dev --episodes 1` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`(`calibration.json` 생성). 모두 EXIT 0. 가드는 §5.5. |
| 5 운영 | 충족 | 모든 산출이 `/data/harvest` 아래, `meta`에 `code_sha`·카나리·시드·모델 지문, `MODEL_REV` 고정(`ebb281ec…`), 처리량 문서 R3, 체크포인트 프롬프트 해시 대조(§3 끝). 문서: DOC 0(§5.3). |

### 5.5 C. 가드 (파드, 변수 없이; `CUDA_VISIBLE_DEVICES=""`; 출력 폴더 `guard_out`은 끝까지 비어 있었음)
- 평가: `e05 --split cal`·`--split test`, `rd --split test_p5`, `calib --fit-split cal` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split test --seeds 1000` 거부. `closed --split dev --seeds 500|30|1300|2000|10000` → "seeds [..] are not in split dev range(0, 30) (refused, never opened)". `HARVEST_ALLOW_SPLIT=dev closed --split cal --seeds 500` 거부. `closed --isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)".
- 생성: `gen --seeds 10000-10001`(확인 인자 없음) → "R2 generates DEV 0-29 only (R2_TRAIN 10000-59999 needs --confirm-train); every other seed is refused …". `--confirm-train`과 함께 500·3000·1149·60000 → "R2 generates DEV 0-29 and R2_TRAIN 10000-59999 (--confirm-train given); every other seed is refused …"(5회차 N10의 문구 부정확 해소). `--variant random` → "TEST pool … use 'dr'". `replay --seed 1300` → 거부.
- `aiworker.check_layout_seed`: 0·29 허용, 30·499·500·549·1000·1149·1300·2000·2119·3000·10000·59999 거부.
- 시드 표 일치: `eval/splits.py` `RANGES` = {dev 0–29, cal 500–549, test 1000–1149, test_p5 1300–1329, pool 2000–2119}, `PROTECTED` = (cal, test, test_p5) = 정본 §66 시드 표(+ R2_TRAIN 10000–59999 = `gen.py:35`). 시험 시드 3000–3199(`tests/sim/test_randomize_logic.py:13`)는 모든 예약 범위 밖.

### 5.6 A. 테스트
- 로컬(Git Bash, `cd /d/qdd && python -m pytest -q -rs`, TMP = `D:\tools\scratch_qdd\r7c6\tmp`, basetemp = pytest.ini의 D:): 2회(74 s / 83 s) 모두 EXIT 0, 진행 표시 합 784 통과 + 6 건너뜀 표시(모듈 단위 건너뜀 5 포함 요약 11) = **784 passed, 11 skipped**. 건너뜀: torch 없음 7, inspect_robots 없음 2, pyarrow 1(파드 안내), TODO(P3) 1. 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json` 생기지 않음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + IR 4경로, `CUDA_VISIBLE_DEVICES=""`, basetemp `/data/harvest/tmp/r7c6/pytest_cpu{1,2}`): **826 passed, 3 skipped** 두 번(EXIT 0, 115 s / 82 s). 건너뜀: pyarrow 1, CUDA 없음 1, TODO(P3) 1.
- 파드 GPU 2: `tests/runtime/test_fused_action.py tests/train/test_stageb_torch.py tests/runtime/test_fused_model.py` **26 passed**(GPU 2 시작·끝 1 MiB).
- 파드 LeRobot: `tests/datagen/test_episode_files.py` **6 passed**.

### 5.7 B·D. 정본 ↔ 코드 ↔ 문서
- §47 카메라: `sim/scene.py:8-12` 머리 ZED Mini 왼쪽 672×376, 손목 D405 424×240 = `FFW_SG2_REAL_cameras.py`(fx 367 = 85°, 실측 364.0; D405 87° fx 223.4, 실측 218.4/217.6) = `cli_e3st.py:50` `HEAD_FX = 367.0` = 정본 §47 = handoff `:51,:84`. 옛 102° 서술은 모두 정정 줄이 붙었거나 정본 §37 본문(§43·§47이 덮음).
- GPU: 계획 `:29,40`(GPU 2 = 학습·vLLM, 렌더 금지) = handoff `:87` = user-log 64 = 코드(`closed.py:36` `ISAAC_GPUS = ("0","1")`, `:141,331` 거부, `stagea_train.py:22`·`stageb_train.py:16-17` GPU 2, `fused_model` 모델 GPU 2·3, `closed --gpu` 기본 3) = 파드 `ir_run.sh:56`.
- 날짜: 정본 §71(01:48 UTC)·§71 보충(01:59 UTC) ≤ 커밋 ac7095a(2026-09-25 10:59:41 +0900 = 01:59:41 UTC). handoff 시각은 N12.
- §63 (1)–(3)·§62 hz: §5.4 실측(팔별 통계, `open01@v1`, tau 마스크 40/40, hz 10·H 5; R2는 30 Hz)과 `stageb_data.py:31-35,54-55`(proprio 23 + 마스크 4 = 27 = `se2e_data.md:109`)가 맞다.
- handoff·direction-log 상태: `handoff.md:97`·`direction-log.md:53`·`draft-log.md:443`의 5회차 줄(DEFECT 0, DOC 2, SCOPED 8, NOTE 13, 코드 무결 4회 연속 2–5회차)은 `r7_cycle5.md`와 맞다. "연속 무결 0회 → 6회차"도 맞다.

### 5.8 F. 규칙
- `main` = `origin/main` = `520b2be`, dev = `ac7095a` = `origin/dev`.
- 비밀값 패턴: `541068a..HEAD` 차이 0건, HEAD 트리 0건(개수만 셈).
- 파드 `/data` 밖: 검증 시작(02:01 UTC) 뒤 새 파일 0(`find -xdev -newermt "2026-09-25 02:01:00 UTC"`: `/`·`/tmp`·`/root`·`/home1`·`/var/tmp`·`/isaac-sim`·`/dev/shm`·`/opt`·`/usr/local`·`/etc` 각각 0, 정리 뒤 다시 0). 내 프로세스 0. GPU 0–3 = 896 / 5 / 1 / 1 MiB(시작 때와 같음). 공용 `/data/harvest/canary`·`r2/dev`는 읽기만 했다(구조 검사는 `stamp` 없이). 라벨러(GPU 0, `cli_label`)는 건드리지 않았다.
- 로컬 C:: N14.

## 6. 다음 순회 전에 할 일 (제안, 모두 선택 — 이번 판정에는 영향 없음)
1. 7회차는 이 HEAD(`ac7095a`) 그대로 새 검증 에이전트가 돈다(PASS 2회 연속이면 S-E2E). 그 사이 커밋이 이 보고서·handoff·direction-log 줄 추가뿐이면 코드 순회 결과는 그대로 유효하다.
2. (권장) N1: 융합 판의 `closed.json` `meta.prompt_config`를 체크포인트 구성으로 바꾸거나 이름을 `modular_prompt_config`로 — 코드 변경이라 다음 순회에서 다시 확인 대상이 된다. 급하지 않으면 S-E2E 뒤로.
3. (권장) N2: handoff `:46`·`:55` 끝에 "(→ §2.7·§2.8)" 포인터. N11: 공용 `tmp/fused_frames/<pid>` 빈 폴더와 1회차 `tmp/r7c1`(2.0 GB) 정리는 메인 세션이 판단.
4. (S-E2E 사전 등록) N8 시작일 카나리, N10 검증 부분집합 층화·중간 저장·`--eval-every`.
