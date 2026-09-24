# R7 객관 검증 순회 — 1회차 (cycle 1)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님). 작성 2026-09-24 23:28 UTC(`date -u`, 로컬·파드 시계 일치).
- 대상: `D:\qdd` `dev` 브랜치, 태그 `stage3-r1r6` = `519de26`. 검증 중 HEAD가 `706db65`("stage3 loop check", `docs/stage3/direction-log.md` 한 줄)로 올라갔으나 코드는 같다(파드 사본 `code_sha` = `5d35a99d556d91a8` = pre-R7 최종 판 사본 `code_pre_r7_run2`와 같음).
- 기준: `docs/superpowers/plans/2026-09-25-e2e-ready.md`(완료 정의 1–5, 관문 R1–R6), 정본 `docs/design/00-interfaces.md` §43–§66(뒤 절 우선), 사용자 지시 user-log 61.
- 규칙 준수: 고치지 않음, 커밋 안 함. 파드 파일은 모두 `/data/harvest` 아래(코드 사본 `/data/harvest/code_r7c1`, 산출 `/data/harvest/tmp/r7c1`(2.0 GB, 작은 체크포인트 포함 — 지워도 됨), 캐시 `/data/harvest/cache/pyc_r7c1`, Isaac 캐시 `ir/kitcache/cyclo-r7c1{m,f,c}_standard`). GPU: 학습 = GPU 2(렌더 없음), vLLM = GPU 3, Isaac = GPU 1(비어 있을 때), GPU 0(라벨러 사용 중) 건드리지 않음. 시드 DEV만. 유료 API 호출 없음(Astra 모의). 로컬 임시 파일은 `D:\tools\scratch_qdd\r7c1`, 컴파일 `D:\tools\texbuild_r7c1`.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 2 |
| DOC | 8 |
| SCOPED | 4 |
| NOTE | 12 |

DEFECT·DOC가 0이 아니므로 이번 순회는 통과가 아니다. 고친 뒤 순회 횟수를 처음부터 다시 센다(계획 R7).

---

## 1. DEFECT

### D1. 정본 §63 열린 문제 처리 (1)–(3)이 코드에 없고, 단계 B 학습 진입점이 S-E2E 자료를 받지 못한다
- §63 결정: (1) 정규화 = **팔별(왼·오) 통계**, (2) 그리퍼 = 데이터셋별 관절값을 **[0, 1] 열림 정도**로 선형 사상, (3) 토크 없음 → `tau` **마스크 0(손실·입력에서 제외)**. §62: "단계 B 로더는 데이터셋별 hz를 받는다".
- 코드:
  - `harvest/train/stageb_data.py:200-222` `ActionNorm.fit`은 모든 행을 **한 통계**로 합친다(팔 구분 없음).
  - `proprio_mask`는 `harvest/train/se2e_data.py:194`에서 쓰기만 하고 읽는 곳이 없다(`grep proprio_mask` → 이 한 줄). 모델은 `tau = 0`을 그대로 입력으로 받는다.
  - 그리퍼 [0, 1] 사상 코드가 없다(S-E2E 행의 `grip`은 관절값 그대로, `se2e_data.py:16` 주석 "joint units").
  - `harvest/train/stageb_train.py:292-305` `cmd_train`은 `D.load_stageb`(풀 폴더 + R2 행, `make_sample` 기본 hz = 30)만 부른다. `se2e_data.load_se2e`를 부르는 곳은 테스트뿐이다(`grep load_se2e`). 즉 S-E2E(10 Hz) 자료로 단계 B를 학습할 명령이 없다.
- 확인: 모델 자체는 S-E2E 표본을 받는다 — 검증 드라이버(`/data/harvest/tmp/r7c1/stageb_check.py`, GPU 2)에서 RB2 표본 2개로 `losses()`가 계산됨(fm 2.85, dec 1.34, H = 5). 빠진 것은 §63 처리와 진입점이다.
- `se2e_data.md` §9는 이것들을 "열린 문제"로 두었고 §63이 결정했지만, 코드는 결정 전 상태 그대로다. 이 항목을 E2E-ready 범위 밖(S-E2E 준비 단계)으로 미룬다는 기록도 없다.

### D2. 폐루프 로그가 §42 필수 필드(요청 해시·카나리 id)를 싣지 않는데, R5 문서는 "로그 스키마(§42) 확인"이라고 적었다
- §42 로그: "트라이얼별 부가 JSONL(M4 표·option_key·epoch·**요청 해시·카나리 id**)". E-first §1.6도 호출마다 요청·응답 원문, 두 모델의 그날 카나리 id를 요구한다.
- 실제 부가 JSONL(`/data/harvest/tmp/r7c1/eval/closed_fused/.../dev0-P0-standard-e0.jsonl`, pre-R7 최종 판도 같음):
  - `call` 행 키 = `answers, call_id, call_no, critic, epoch_sent, error, latency_s, meta, phase, slots, t_deliver, t_state, type, verify, votes` — 요청 해시 없음.
  - `astra` 행 키 = `type, hb_no, kind, cadence, prompt_id, t_send, t_deliver, latency_s, decision, note, error, model, usage, http, first_token_s` — 이미지·요청 해시 없음.
  - `grep -rn canary harvest/runtime harvest/eval` → 0건.
- `docs/stage3/results/r5_closed_loop.md:16` "로그 스키마(§42) 확인", §2.3에는 이 두 필드가 빠진 사실이 없다.
- (참고) Jev가 로컬 VLM으로 바뀌어(§44) 결정층 카나리는 필요 없을 수 있다. 그렇다면 정본에 그 판단을 적고 Astra 쪽만 넣는 식으로 정본과 코드를 맞춰야 한다.

## 2. DOC

### C1. 정본 §56–§66의 날짜가 하루 틀렸고, pre-R7 문서가 "파드 시계가 하루 뒤졌다"고 잘못 적었다
- 정본 §56 "2026-09-25 17:13 UTC" … §66 "2026-09-25 22:13 UTC" — `2026-09-25` 표기가 11줄(`grep -c 2026-09-25 00-interfaces.md`). 실제 UTC 날짜는 2026-09-24다.
  - git 커밋 시각: §62 커밋 `f337b7e` = 2026-09-25 04:18 +0900 = **2026-09-24 19:18 UTC**. `519de26` = 2026-09-24 23:00 UTC.
  - 파드 `date -u` = `Thu Sep 24 23:02:07 UTC 2026`, 로컬 `date -u`도 같다. 파드 `TZ=Asia/Seoul`(`date` = Fri Sep 25 08:05 KST).
  - §66 "2026-09-25 22:13 UTC"는 이 검증 시점(09-24 23:28 UTC)보다 약 23시간 뒤의 시각이다.
- `pre_r7_fixes.md:4` "파드 시계는 하루 뒤진 2026-09-24 22:0x UTC로 찍힘 — 이전 문서들과 같은 시계 차"는 틀렸다. 파드 시계가 맞고, 문서 날짜가 KST 날짜에 UTC 시각을 붙인 것이다. 같은 날 문서라도 `r1_perception.md`(2026-09-24 18:04 UTC)는 맞게 적었다. `r2_datagen.md`·`r3_throughput.md`·`r6_eval.md`의 "작성/실행 2026-09-25"와 계획 파일 이름(2026-09-25, KST 날짜)은 기준을 밝히지 않았다.

### C2. `docs/handoff.md`(새 세션이 가장 먼저 읽는 문서)가 낡았다
- 머리 "마지막 갱신: 2026-09-24 21:03 UTC (… 정본 §1~§64 …)", §2.7 "먼저 읽을 것 … §43–§64", "**진행 중**: R2 데이터 생성기, R6 평가 스크립트".
- 실제: §65(21:33)·§66(22:13), R6 커밋 `44a81da`, R2 커밋 `6111b4e`, pre-R7 수정 `519de26`, 태그 `stage3-r1r6`, R7 시작. 이 중 어느 것도 handoff에 없다.

### C3. 관문 R1–R6의 방향 검사(질문 6개) 기록이 없다
- 계획: "방향 질문 6개는 관문마다". `docs/stage3/direction-log.md`에서 관문 행(`**관문`)은 17:08 "단계 A SFT" 하나뿐이다. R1–R6은 30분 루프 행만 있다. `draft-log.md:435`가 "R1–R6 관문 모두 완료"라고 적었지만 관문별 1–6 답은 어디에도 없다. 태그 `stage3-r1r6`에 대응하는 관문 기록이 없다.

### C4. 정본 §58·계획은 "런타임 = 모델 한 번 호출"인데, 구현과 R5 결정은 스텝마다 두 호출이다
- 정본 §58 영향 줄(`00-interfaces.md:511`) "R5(런타임 = 모델 한 번 호출로 결정 + 행동)", 계획 개정 줄 "R5 런타임은 모델 한 번 호출".
- `r5_closed_loop.md:76` [Claude] "결정과 행동은 한 호출이 될 수 없고 스텝마다 두 단계". `runtime/fused_model.py`도 `decide` → M4 확정 → `chunk` 두 HTTP 호출이다(같은 프로세스·문맥 캐시). 설계 판단 자체는 근거가 있지만(expert가 확정 결정을 조건으로 받음), 정본·계획에 반영되지 않았다.

### C5. §66 "R2_TRAIN 시드를 정본 시드 표에 추가"가 반영되지 않았다
- 정본 시드 표 `docs/design/E-first-experiments.md` §1.5(112–118줄)에 R2_TRAIN 10000–59999 줄이 없다.
- `harvest/datagen/gen.py:19` "(proposal for the stage-B generation, not run in this gate)", `:35` "[proposal]" — §66에서 결정된 뒤에도 제안으로 적혀 있다.
- 가드 동작은 맞다(§3.3).

### C6. GPU 배분 문구가 서로 다르다
- `harvest/train/stageb_train.py:11` "GPU only when free (**never GPU 2**)". 이는 user-log 62·64(GPU 2 = 학습 전용)와 반대다. R3·R4·pre-R7 모두 실제로는 GPU 2에서 학습했다.
- `harvest/train/stagea_train.py:18` "Pod: run with CUDA_VISIBLE_DEVICES=1 (smoke)" — GPU 1은 Isaac 렌더용이다(user-log 62). 같은 docstring 첫 줄의 `train --pool DIR --rule R`도 기본 정답이 labels_v2가 된 뒤의 사용법과 맞지 않는다.
- 계획 24줄 "GPU: 0 = 결과 라벨 작업, 1 = Isaac, 3 = vLLM/학습 스모크, **2 금지**"는 같은 문서의 user-log 62 절로 대체됐지만, 대체됐다는 표시가 없다.

### C7. 완료 정의 1 "인식 추정 상태(M1) 입력"이 §58 뒤에 고쳐지지 않았다
- §58은 명시적 M1을 런타임 의존에서 빼고, 특권 기하는 보조 손실·정답으로만 쓰게 했다. 그래서 R2 자료에는 M1 추정 상태가 없다. R2 행은 IMG 상태 + `aux` 특권 기하 + labels_v2다(`r2_datagen.md` §2.2).
- 계획 머리의 개정 줄("R1은 보조 라벨·기준선용")과 완료 정의 1의 문장이 서로 다르다. 적힌 그대로의 완료 정의 1은 검증할 수 없다.

### C8. 알려진 공백들이 "R7에 넘김"으로만 남아 있고, E2E-ready 범위 밖이라는 결정·포인터가 없다
`pre_r7_fixes.md` §6과 `r4_stageB.md` §8은 아래 항목을 R7로 넘겼다. 정본에는 적혀 있지만 구현되지 않았고, "E2E-ready 범위 밖(언제 무엇으로)"이라는 결정도 없다.
1. §45 합치기 규칙: T_fail 뒤 "복구 끝 + 2 s까지 하트비트 정지", `patch`/`replace`의 A5′ 검사 → M2 R3 경계 교체 → 실패 시 이전 계약 유지, 30 s 안 두 번 되돌리는 patch 보류. 지금은 epoch만 올린다(`pre_r7_fixes.md` §6-2·§6-4).
2. M7 FAIL → M9 복구 없음(critic 경보는 기록 + Astra 앞당김만). T2 연속 {거짓} → CONTRADICT-soft도 없음.
3. 모듈형 스택의 세계 쪽 측정이 항상 `unknown`이다. 따라서 §60 주 표에 병기할 모듈형 행에서는 critic이 동작하지 않는다(§6-3).
4. §52 "백본은 결정 토큰 + 일반 VQA 공동 학습(1:1:0.25)": `vqa_loss`는 있지만 자료 원천이 없다. `stageb_train.py` `cmd_train`은 `"vqa": 0.0`을 고정해서 켤 수도 없다(`r4_stageB.md` §8-5).
5. 융합 런타임 토크 입력 평균 대치, 확인 헤드 보정 파일 없음, 동시 부하 지연(§1.6).
- 각 항목은 (a) 구현하거나 (b) 계획·정본에 "E2E-ready 범위 밖, 처리 시점·담당"을 적어 SCOPED로 바꿔야 한다.

## 3. SCOPED (통과에 영향 없음)
- S1. `LatencyChargingController` 스텁: `harvest/runtime/latency_ctrl.py` 설명("not needed for R5 … the baselines (P3) will implement it"), `r5_closed_loop.md:100`. 테스트 1개 건너뜀(TODO(P3)).
- S2. 본 단계 B 학습(R2 30 Hz 행)과 R2_TRAIN 대량 생성: §66 "본 생성 계획(아직 실행 안 함) … S-E2E 이후", `pre_r7_fixes.md` §6-1 "작업 범위 밖".
- S3. CAL 보정·TEST 평가: `HARVEST_ALLOW_SPLIT`는 메인 세션만 사전 등록 시각에 쓴다(`splits.py`, `r6_eval.md` §2).
- S4. RB1 라이선스 확인은 논문 전(§63-(6), handoff "RB1 라이선스는 논문 전 확인").

## 4. NOTE
- N1. 단계 A 학습 명령은 `TORCH_DISABLE_NATIVE_JIT=1` 없이는 GPU에서 바로 죽는다: `RuntimeError: Failed to find C compiler`(triton, Qwen3-VL mrope bmm) — 검증 첫 실행(`/data/harvest/tmp/r7c1/ckptA.train.log`). 이 조건은 `stageA_pipeline.md:100`에만 있고 `env.sh`·`stagea_train.py`에는 없다(`eval/common.py:232`는 fused 서버에 넣음). `env.sh`나 모듈에 넣기를 권한다.
- N2. `tests/sim/test_randomize_logic.py:13` `EXTRA = range(500, 700)`의 주석은 "non-reserved"다. 그러나 CAL 500–549가 들어 있다(메모리 안의 배치 표집만 하고 파일은 없음). 다른 범위(예: 3000–3199)로 옮기기를 권한다.
- N3. LeRobot 내보내기 pytest(`tests/datagen/test_episode_files.py:116`)는 모든 환경에서 건너뛴다(pytest + pyarrow + av가 한 venv에 없음). 수동 확인은 통과했다: `LX.verify(/data/harvest/r2/dev_lerobot)` 오류 0, 32편·9,288프레임·PSNR ≥ 34.27 dB, lerobot 0.3.3 `LeRobotDataset` 적재 OK.
- N4. 파드에 고아 대기 셸 5개가 있다: PID 692841·1222511·1223858·1728423·1728657, `until ! pgrep -f "r3_bench.py stagea|stageb"; do sleep …` — 자기 명령줄에 걸려 영원히 안 끝난다(pgrep 자기매칭). 해는 없지만 누수다. 내 프로세스가 아니라 건드리지 않았다.
- N5. `/data` 밖 흔적 중 귀속이 불확실한 것: `/home1/irteam/.triton/cache/q4oI…`(빈 폴더, 2026-09-24 08:57 UTC 생성 — user-log 45 /data 규칙(09:24) 이전, E3-ST 무렵). `/tmp`의 새 파일은 모두 Task C 프로젝트 것(`taskC_qr_scene_*`, `seqtest*` 등). 로컬 `C:\Users\USER\AppData\Local\Temp\torchinductor_USER`는 빈 폴더(09-24 14:38 UTC), 귀속 불명. 세션 scratchpad는 비어 있다. 하네스 백그라운드 출력 39 MB(`…\1a853580…\tasks`)는 Claude Code가 쓴 것이고 비밀값 검색 0건.
- N6. vLLM `--limit-mm-per-prompt image:2`(`eval/common.py:173`, `tools/r5/serve.sh`) — §57 양팔 스킬(머리 + 두 손목 = 3장)은 막힌다. 지금 과제는 한 팔이라 문제 없다.
- N7. `detect_phrase`는 고정 표로 대신한다(`perception/seg.py:16`, `r1_perception.md` §1.2 "Astra 대역"). §58 뒤 R1은 기준선용이다.
- N8. §65 "결과 기반 라벨 = 거부권 용도"를 쓰는 코드가 아직 없다(라벨 label4 진행 중, `finalize` 전).
- N9. `.superpowers/sdd/…/progress.md`(handoff가 가리키는 ledger)는 gitignore된 로컬 파일이고, e2e-ready 계획 과제가 반영되지 않았다.
- N10. `stageb_train train`은 `last`만 저장하고 재적재 확인이 없다. 재적재 동일성은 검증 드라이버에서 확인했다(§3.4).
- N11. 보정 판 `closed_cal`(SFT + `calibration.json` + J5 α 0.1, DEV 0, 40 s)은 `max_steps`로 실패했다. 이는 R6의 60 s 판과 조건이 다른 탓이며 성공 여부는 요구 사항이 아니다(§56). J5는 동작했다(held 121 / escalated 60 / passed 363).
- N12. `Calibration.load`는 런타임 지문이 `None`(모의)이면 지문 검사를 건너뛴다(`runtime/calibration.py:208`).

---

## 5. 확인한 것 (근거)

### 5.1 A. 테스트 (두 번씩 실행, 불안정 없음)
- 로컬 `cd D:/qdd && python -m pytest -q`: **768 passed, 11 skipped**(1회차 1분 05초, 2회차 1분 03초). 건너뜀 11개의 이유는 torch·pyarrow·inspect_robots 없음과 TODO(P3) 1개.
- 파드(`venv_train`, IR PYTHONPATH, CPU): 1회차 `tests/train tests/runtime tests/eval tests/m4b` **271 passed, 2 skipped**. 2회차 전체 `tests`는 **807 passed, 3 skipped**(pyarrow 1, CUDA 없음 1, TODO(P3) 1).
- CUDA 시험 `tests/runtime/test_fused_action.py`를 GPU 2에서 돌렸다: 3 passed.
- 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json`은 생기지 않았다.

### 5.2 B. 정본 ↔ 코드 (위 D·C 항목 외에는 일치)
- §54: S1 1 mm — `eval/common.py:28 STEP_CM = 0.1`, `perception/state.py:30`, `stagea_train` `--step-cm` 기본 0.1. labels_v2가 결정 정답이다.
- §57·§59: `head camera:` → `right wrist camera (active arm):` 순서가 `jevl._body_mm`·`stageb_data.CAM_LABEL`·`runtime/models.py`·`fused_model.py`에서 같다. 호출 방식 기본은 lead(`jevl.acall_mm`, 첫 시퀀스 뒤 병렬). vLLM은 `--enable-prefix-caching`에 멀티모달 캐시 기본값, `VLLM_BATCH_INVARIANT=1`. 카메라 배치는 `question_id` legend(`run_r5.question_ids`의 `cameras=…;state=…`)에 들어간다. H 배치로 보정한 파일을 HW 질문 id로 부르면 거부된다(§5.5).
- §58·§60: `closed --backend modular|fused` 두 행이 모두 돈다.
- §61·§64: `runtime/measure.py` `SOURCE_TABLE` — T1 = gripper_open·holding_t·lifted_holding(고유 감각 코드, E-M4b 문턱 그대로), T2 = 세계 5 + contact_stall(V1h). critic = V1h 단독, 지속 2, T1 하드 채널은 따로. 빈 집합·둘 다 = `unknown`. 단계 B 확인 헤드 손실이 있다(학습 로그 `ver`).
- §62: R2 = 30 Hz(행 9,256개 모두 `check_row(hz=30)` 통과), S-E2E 행 = hz 10·H 5(로더가 `make_sample(hz=r["hz"])`로 받음). 학습 진입점 쪽은 D1.
- §66 가드는 §5.3 참고.

### 5.3 C. 자료·가드 (파드, `/data/harvest/tmp/r7c1/loaders.py`, `guards.sh`)
- 풀(단계 A, HW, labels_v2 파일): 항목 6,000(train 3,000 / val 3,000), 질문 5 × 1,200, 120편. 항목 키에 `oracle`이 없다.
- R2 DEV(`load_stageb`, 6폴더, dev_val_seeds {5}): 표본 **9,256** · 결정 항목 **4,690** · val **1,698** — `r2_datagen.md`와 같다.
- S-E2E(`load_se2e`, conv RB1·RB2): 25,433 + 13,850 = **39,283**(train 37,484 / val 1,799) — §63·`se2e_data.md`와 같다.
- 풀 `oracle`을 정답으로 쓰는 곳: 없음. `stagea_data`는 줄에서 `oracle`을 빼고 가짜를 넣는다. `eval/common.build_request`도 가짜 oracle을 쓴다. e05·rd·calib의 정답은 `load_truth`(labels_v2 / outcome)다. `oracle`을 읽는 곳은 옛 도구(`tools/jevl_*`, `labels_v2_eval`)와 라벨러의 사전 등록 비교(`cli_label` oracle_in_best)뿐이다.
- 가드(변수 없이 실행): `e05 --split cal`·`--split test`, `rd --split test_p5`, `calib --fit-split cal`, `closed --split test --seeds 1000`, `HARVEST_ALLOW_SPLIT=dev closed --split cal` → 모두 거부. `closed --split dev --seeds 500` → "not in split dev" 거부. `gen --seeds 10000-10001`(확인 인자 없음) → 거부("needs --confirm-train"). `--confirm-train`을 줘도 500·1000은 거부. `--variant random`·`replay --seed 1300` → 거부. `aiworker.check_layout_seed`는 2000·10000 등을 거부한다.

### 5.4 D. 학습 준비 (GPU 2, 렌더 없음, 시작 전 GPU 2 = 1 MiB)
- 단계 A(`stagea_train train`, 풀 실데이터, HW, `TORCH_DISABLE_NATIVE_JIT=1`, 6스텝): 검증 NLL 3.19 → 0.555(3스텝) → 0.975. 학습 손실 5.67 → 1.33. `load --adapter best` NLL **0.5546350479125977 = 학습 중 값과 소수점 끝자리까지 같음**.
- 단계 B CLI(`stageb_train train`, R2 DEV 실행 2폴더, 6스텝): 끝까지 돎, `last/{adapter,heads.pt,stageb.json}` 저장.
- 단계 B 드라이버(같은 함수, R2 DEV 3폴더, 8스텝): KI 확인 fm → 백본 기울기 **0.0**(시작·끝 모두), aux·dec → 백본 > 0. 결정 NLL 5.41 → 0.88. 저장 → 새 백본에 재적재 → 행동 최대 차 **0.0**, 검증 지표가 모두 같다.
- 학습/추론 확률 일치 시험: `test_stagea_loss_torch::test_training_logprobs_equal_jevl_inference_logprobs`, `test_r3_shared_qwen`(Jev-L 에뮬레이션), `test_fused_model`(decide = 전체 행 경로) 모두 통과. pre-R7 벤치 FP32 차 1.69e-5(원자료 `fused/bench_fp32.json`).

### 5.5 E. 폐루프·평가 (DEV 소규모, `/data/harvest/tmp/r7c1/eval/`)
| 명령 | 입력 | 결과 |
|---|---|---|
| `e05` | SFT 병합, jsel_dev/P0 2편(55 스냅샷), vLLM GPU 3 | 끝까지 돎, 호출 오류 0, 136 s |
| `rd` | standard/random/dr 각 1편/종류 | 끝까지 돎(A 0.901/0.897/0.899, 확인용) |
| `calib` | 적합 POOL 4편 → 보류 DEV P0 4편 | `calibration.json` 생성(지문 `ed387f593652252e`, question_id 5개) |
| `closed` 모의 | DEV 0, 40 s | 성공 16.46 s — pre-R7 시드 0과 같은 값(결정성) |
| `closed --backend fused` | tiny ckpt, DEV 0, 모델 GPU 2 + Isaac GPU 1 | 끝까지 돎, 결정 34·청크 34·호출 오류 0, `off_table`(작은 모델, 예상된 결과) |
| `closed` + 보정 | SFT, `--calibration … --j5-alpha 0.1` | 보정 파일 적재, J5 동작(held 121 / escalated 60 / passed 363) |
- 보정 파일 묶기: 같은 지문·H 질문 id → 적재. 다른 지문 → "fingerprint … != served model (recalibrate)" 거부. HW 질문 id → "question_id of dir_xy … != runtime" 거부.
- §42 로그: `policy_config`(astra_prompt_id·question_ids·model·effort·T_c·clock simlat·M4 파라미터)는 있다. 부가 JSONL의 M4 표·option_key·epoch도 있다. 요청 해시·카나리 id는 없다(D2).

### 5.6 F. 규칙
- main 무손상: `main` = `origin/main` = `520b2be`(2026-09-06), `git ls-remote` main 같음. dev는 264커밋 앞.
- 비밀값: HEAD 트리와 전 이력에서 `sk-proj-…`·`hf_…`·`ghp_…` 패턴 0건.
- `python tools/intent_check.py` → total 62 flagged 0. `[사용자]` 줄과 `\intent` 줄은 `stage3-dc1..519de26`에서 삭제·수정 0건이다. `user-log.md`는 덧붙임만 있다(`-` 줄 0). (`tools/user_line_check.py`는 휴리스틱이라 68개 중 27개를 표시하지만, 의역 [사용자] 줄 형식 때문이고 이번 범위의 변경은 없다.)
- 파드 `/data` 밖: 이번 검증 실행에서 남은 파일 없음(`find / -xdev -newermt "2026-09-24 23:00"` → `/`·`/tmp` 폴더 시각만 바뀜). 앞선 흔적은 N5.
- 로컬 C: 프로젝트 산출물 없음(N5). pytest 임시 폴더 = `D:/tools/scratch_qdd/pytest_tmp/p<PID>`(conftest).

### 5.7 G. 문서 수치 대조 (파드 원자료, 모두 일치)
1. `pre_r7_fixes.md` §8 모의 DEV 0–9 판(`out/pre_r7/closed_mock_dev0_9_final/closed.json`): 10/10, 성공 시각 중앙 15.42 s(13.94–16.63), 호출 461·오류 0, RTF 0.862, epoch 중앙 3.5, Astra 20. 시드별 사건에 `t1_contradict`·하드 사건 0.
2. `pre_r7_fixes.md` §1.3 벤치(`fused/bench.json`): decide 104.24/147.01 ms, 확인 헤드 0.69/0.79, 그래프 29.98/30.09, eager 36.91/42.8, 그래프 = eager 0.0, BF16 0.029. FP32 1.69e-5.
3. `e_m4b_meas.md`·§64(`m4b/results.json`): PC1 0.9494 [0.9275, …], ECE 0.0040, 커버리지 0.9048, V1q 0.959. PC3 V1h+P 재현율 0.786·FWER 0.033, V1h 0.871·0.0.
4. `r2_datagen.md` §4.1(`r2/dev/check.json`): 36편, 유효 32, 프레임 10,651, 행 10,615, 결정 1,081, bottle_tray 실패 4.
5. `r3_throughput.md`(`r3/bench_a.json`·`bench_b.json`): HW old 3.61 → shared micro 4 23.57 항목/s(62.7 GB), 단계 B 5.00 → 0.42 s/스텝.
6. `se2e_data.md`·§63: 표본 39,283 / 37,484 / 1,799(로더로 재계산).
- 논문: Tectonic 절차로 `main.tex` 19쪽·`mindmap.tex` 9쪽 컴파일, 미해결 참조(`??`) 0. 경고는 xdvipdfmx 글꼴 조회와 lineno.sty UTF-8 등 기존 것.

## 6. 다음 순회 전에 할 일 (제안)
1. D1: §63 (1)–(3)을 `ActionNorm`·표본 생성·학습 진입점에 넣고(`--se2e <conv>` 같은 경로), 시험을 추가한다. 아니면 정본에 "S-E2E 준비 단계에서 구현"이라고 명시해 SCOPED로 옮긴다.
2. D2: 호출·Astra 행에 요청 해시(+이미지 해시)와 카나리 id(또는 "카나리 없음" 결정)를 넣거나, 정본 §42를 §44 뒤 상황에 맞게 고친다. R5 문서 주장도 고친다.
3. C1–C8 문서 정리: 정본 날짜 교정(+ pre-R7 "시계 차" 문장), handoff 갱신, R1–R6 관문 기록, §58 두 호출 반영, 시드 표 R2_TRAIN, GPU 문구, 완료 정의 1, C8 공백별 범위 결정.
