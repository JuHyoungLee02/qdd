# R7 객관 검증 순회 — 16회차 (cycle 16, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle15.md` §5 표·`r7c15_fixes.md`의 시험에 기대지 않고 사전 등록 원문에서 대조표를 다시 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력**으로 확인함). 작성 2026-09-25 14:15 UTC 무렵(= 23:15 KST; 로컬 시작 약 13:50 UTC, 파드 첫 명령 13:53:45 UTC, 파드 정리 끝 14:11:31 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `f91ad52`(태그 `stage3-r7fix15`, 커밋 시각 2026-09-25 13:49:47 UTC). `9cee78b..f91ad52` = 논문(b283da2·ad4f7b0), **E-TC 시간 맥락 2×2 사전 등록 + 선택 옵션 코드**(0b853c2: `docs/stage3/prereg_se2e_temporal.md`, `harvest/train/se2e_temporal.py`·`se2e_temporal_model.py`, `tools/se2e_temporal.py`, `tools/se2e/temporal_latency.py`·`temporal_verdict.py`, `stageb_train.py` 선택 플래그, 데이터 규모 옵션 `--train-fraction`·`--eval-train-per-kind`), **15회차 수정**(f91ad52, 정본 §81). `git -c safe.directory=D:/qdd -c core.autocrlf=false archive f91ad52`(sha256 `341d0713…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c16\repo`에 풀어 검토했다. 파드 사본 = 같은 archive + JSON `CODE_VERSION`(`f91ad522…`, dirty false); 파드 산출 `meta.git.commit` = `f91ad522…`. 검토 중 다른 세션이 `d734d00`·`585786d`(user-log 72·73)·`3478cf2`(데이터 규모 곡선 결과)를 커밋했다 — 범위 밖.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle15.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§81(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·**`prereg_se2e_temporal.md`**·`M4-overlap-commit.md`(조건 정의).
- 분류(15회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본과 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본·사전 등록에 없는 것. 정본(또는 사전 등록)이 "나중에 할 일"로 적은 것은 SCOPED.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory`로만, 전역 설정 쓰기 없음; 이 보고서 한 파일만 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c16`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`python -` 없음; 파드로 보낼 때는 로컬 파일을 `tar`/`sh -s` 표준 입력으로 넘김). 로컬 pytest TMP = `D:\tools\scratch_qdd\r7c16\tmp`(C: 쓰기 없음). 파드 = `/data/harvest/tmp/r7c16`(코드 사본·pytest·산출, 정리 전 381 MB). GPU: Isaac = GPU 1에 한 프로세스(`--inst-prefix r7c16`, `IR_INST` `r7c16_standard`, 기본 `r6` 접두사 안 씀), GPU 0·1 R2_TRAIN·GPU 2·3 S-E2E 판 건드리지 않음, GPU 학습 없음. CPU: 시작 전 파드 cgroup `cpu.stat` 10 s = 사용 약 19.7코어·스로틀 증가 0(쿼터 32) → `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=test`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e_scale`·`se2e_temporal`·`logs/se2e_scale`·`se2e_temporal`·`data/se2e_t`·`code_se2e_*`는 **읽기만**(`tools/se2e_temporal.py bins/transition` 재실행은 출력을 내 폴더로).
- **절차 사고 1건**: 파드 정리 1단계에서 새로 쓰려던 `pod_clean16.sh`가 Write 거부(파일을 먼저 읽지 않음)로 저장되지 않아, 15회차 스크립트를 `r7c16`으로 치환만 한 앞 판이 실행됐다. 그 판이 지운 것은 `tmp/r7c16`(내 폴더)·`ir/kitcache/cyclo-r7c16_standard`(없었음)와 15회차 검토자가 이미 지운 옛 이름(`carb.nW31hS` 등, 존재하지 않음)뿐이라 남의 파일 피해는 없다. 대신 내 폴더 안의 "Isaac 시작 전 tmp 목록"을 잃어, 내 Isaac 판이 만든 `tmp/carb.3ZFqsb`(14:06:30Z)·`tmp/tmpameswd3b`(14:06:49Z)·`cache/pyc_r6/data/harvest/tmp/tmpameswd3b`는 생성 시각(내 판 시작 14:06:29Z 직후, 같은 시각대 다른 새 항목 없음)·열린 파일 핸들 없음(`/proc/*/fd` 전수)으로 가려 지웠다. 산출 수치는 삭제 전에 모두 읽어 이 보고서에 옮겼다.

## 판정: **PASS**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 18 |
| NOTE | 16 |

15회차 수정(정본 §81)은 **모두 동작으로 확인했다**: `RESUME_KEYS`는 파서의 `train` 옵션을 하나씩 바꿔 넣은 결과(파드, torch) 거부된 키 집합 = `RESUME_KEYS` 40개와 정확히 같고 받아들인 것 = `RESUME_FREE` 11개; **실제 옛 체크포인트**(`ckpt/se2e/se2e_A_s0/ckpt/step_002000/train_state.pt`, 새 옵션 13개가 없는 인자)로 같은 명령 → 받아들임, `lr_schedule`·`train_fraction`·`camera_layout`·`motion_dropout`·`eval_train_per_kind` 변경 → 거부, `save_every`·`eval_every` → 받아들임. 라벨 쓰기 쪽 `replay_max`는 0.0·0.3·None·필드 없음·bool·문자열·int·inf·빈 결과 9경우가 규칙대로(NaN 순서 의존은 N2). 질문 범위 기록은 파드 실제 풀 라벨에서 `load_truth` {133, 17, questions 5개}, 실제 `e05 --truth outcome:plan` `meta.truth_label_trust.questions` 같음, 풀 불신 886(전체)·805(5질문) = 정본 §81. 정정 표시 5곳 + 같은 사실 grep 추가분 모두 있음. **E-TC**(새 사전 등록)는 (a) 옵션 끔 = 기준 표본(구성 행: 증강 행 → `load_se2e` 결과가 원 행과 같음; 기본 학습 경로는 코드상 `D.load_for_training` 그대로), (b) video2 = 카메라마다 [label, now, prev], prev = 프레임 max(0, k−3)(구성 입력 경계 k 0–4·29, **실제 원본 영상 디코드로 16/16 k−3이 가장 가까움**), 한 시간 패치의 칸 0 = 과거·칸 1 = 현재 = **Qwen3-VL 비디오 처리기 출력과 비트 동일**(실제 프레임 4표본), LLM 시각 토큰 356 = 356, (c) 움직임 줄 = 원본 parquet 상태의 인과 후방 차분(실제 241행 차이 0, 중앙 차분과 같은 행 0), 등록 구간 경계(0.2179·0.6070 = slow·fast 쪽, |속도| = 0.1755 → still), 드롭아웃은 (시드, 스텝) 난수·전역 난수 불변·학습 배치에만, (d) 전이 층 정의(구성 7경우)·판정 스크립트 채택 규칙 경계(+0.02·−0.01·+10 % 정확히 → 채택, 한 항목 모자라면 불채택, 13/13), (e) 네 형식의 `prompt_config` sha 모두 다르고 런타임 `check_prompt`가 video2(camera·files)·motion(files)를 거부 — 로 확인했다. 등록 구간·전이 층 비율(0.6507, 1,921행)·분포 수는 파드에서 독립 코드로 다시 계산해 같다. 완료 정의 1–5 충족, 새 시드(DEV 21)에서 같은 Isaac 워커 C5 → C5' 행동 **1,398개 비트 동일**. 불일치·정정 누락을 찾지 못했다 → **연속 무결 1회**.

---

## 1. DEFECT

없음.

## 2. DOC

없음.

(검토한 후보와 판단: ① `prereg_se2e_temporal.md` §7의 `stageb_train.py` 해시 `a79ed547…`는 파드 고정 사본(= 0b853c2 블롭)의 값이고 f91ad52 블롭은 `1f56bb6d…`다 — 등록 문서는 "이 판이 쓰는 파드 사본"을 적은 것이라 사실이고, 차이는 §81 N2(`RESUME_KEYS`)뿐이며 §81이 "고정 사본에서 돌아 이 변경과 무관"이라 적었다(N4). ② 전이 층에서 에피소드 끝 너머 프레임(k + j ≥ 길이)을 "다름"으로 세지 않는 것은 등록 문장 "k와 k + j에서 하나라도 다르면"의 자연 해석(없는 프레임은 다를 수 없음)이라 열린 값으로 보지 않았다(N6). ③ `handoff.md:110`·`r7c15_fixes.md:3`의 "커밋 안 함"은 작성 시점 기록(N9, 13–15회차와 같은 모양).)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀. EVAL H1–H3 기준선 비교.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드에서 진행 중(읽기만: `datagen.gen` 워커 5개 `r2t_w1…w5`, GPU 0·1); `gen gen --seeds 10007-10008` 확인 인자 없이 rc 1.
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)) — E-TC 체크포인트도 내부용(`prereg_se2e_temporal.md` §0).
- S5. §67 C8(검사기·계획 서명·편집 거리, 확인 헤드 보정 파일 기본 미보정, M9 복구).
- S6. Astra 카나리 "none"(§67 보충) — 파드 C5·C5' `astra` 행.
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이와 새 코드의 거부(§77 보충 (2), §80) — 파드 `se2e_scale/9371/last` `check_prompt` 불일치 `serializer_ok`·`files_ok`.
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. §74 보충 E-M4-lat 비례 STALE_MAX, 런타임에 없는 조건(파드 `closed.json` `meta.not_in_runtime`).
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): E0.5 `fine_dir`, Jev-L E0 측정 도구, 결정 호출 이미지 원본 저장 안 함, 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` "boundary (ambiguous)" 주석 — f91ad52에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화(J4를 켜기 전 필수 작업).
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬(본 실험 전).
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정 — 그때까지 `--truth outcome:`은 불신 행을 뺀 정답(§80·§81).
- **S18**. **E-TC 학습·판정은 아직 없음**(`prereg_se2e_temporal.md` §7 실행 순서: 데이터 규모 판 두 GPU가 끝난 뒤). 13:53Z 파드: `ckpt/se2e_temporal` 비어 있음, 드라이버 `driver_2.out`·`driver_3.out` 0바이트(대기). (single, none) 칸 재사용 조건(§7 — 그 판 args·rc 0·step 2000·`last/`, 그리고 이 사본 `predict` 요약 = 그 판 step 2000 평가)은 `run.sh`가 `predict`만 하고 비교는 결과 뒤 사람이 할 일로 남아 있다(N3과 함께 결과 문서에서 확인할 것). (15회차 S18 — 데이터 규모 옵션이 커밋 밖 — 은 0b853c2로 해소: N5.)

## 4. NOTE
- N1. **`stageb_train predict`·`evalck`는 체크포인트의 `prompt_config`(layout·motion)를 자기 옵션과 대조하지 않는다**(`stageb_train.py:646-668`·`:670-686`; 파드 확인 `predict_reads_ckpt_prompt_config` false). video2 체크포인트를 `--camera-layout` 없이 `predict`하면 한 시점 입력으로 조용히 평가된다(반대도). 런타임(`fused_model.check_prompt`)은 거부하고(행 125), 등록 드라이버 `logs/se2e_temporal/run.sh`는 학습과 같은 옵션(`"$@"`)을 `predict`에 넘기므로 등록 파이프라인은 맞다. `load_heads` 뒤 `stageb.json`의 `prompt_config.layout`·`motion`과 인자를 비교해 다르면 거부하기를 권함.
- N2. **`cli_label.replay_max`(`cli_label.py:37-43`)의 NaN은 순서에 따라 신뢰가 된다**: 결과 {0.0, NaN} → `max` = 0.0(= 신뢰), {NaN, 0.0} → NaN(= 불신). `isinstance(nan, float)`가 참이라 "수가 없는 결과"(§81 N10)로 걸리지 않는다. 파드 실제 풀 6,627행 row 수준 null 0·NaN 없음(라벨 파일의 `outcomes`에는 `replay_maxabs`를 저장하지 않으므로 결과 수준 검사는 불가), `labeler._replay_rollout`이 NaN을 낼 경로도 보이지 않아 영향 없음. `math.isfinite` 조건을 더하기를 권함.
- N3. **`tools/se2e/temporal_verdict.py` 입력 검사 범위**: 네 칸의 키 집합 동일(`:115`)·요약 대 항목 평균(`:112-113`)·칸 이름(`:104`)은 검사하고, 흐름 파일에 없는 키는 KeyError로 멈춘다(구성 시험 G). 다만 검증 집합이 등록된 300개(`val_keys_sha` `e22f6d8ef7fc`)인지·칸마다 900항목인지·요약 기록이 있는지는 보지 않고, 검사가 `assert`(`python -O`에서 빠짐)다. 판정 규칙에는 영향 없음(등록 문장은 스크립트 검사 범위를 정하지 않음). 결과 문서에 `n_val_snapshots`·키 sha를 함께 적기를 권함.
- N4. 등록 §7의 해시(`se2e_temporal.py` `d5babfb8…`·`se2e_temporal_model.py` `28265152…`·`tools/se2e_temporal.py` `285a7320…`·`temporal_latency.py` `a0dcafcf…`·`temporal_verdict.py` `992d3e20…`)는 f91ad52 블롭 = 파드 `code_se2e_temporal` 파일과 모두 같다. `stageb_train.py`는 파드 `a79ed547…` = 0b853c2 블롭(등록값), f91ad52 = `1f56bb6d…`(§81 N2 `RESUME_KEYS`만 차이; E-TC는 `--resume`을 쓰지 않음). 파드 사본의 `stageb_data.py` `be1e6214…`·`stagea_data.py` `a8c7f527…`은 S-E2E 고정 블롭(S7).
- N5. **15회차 S18 해소**: 파드 `code_se2e_diag/harvest/train/stageb_train.py`(`11e11795…`, 데이터 규모 판이 쓴 파일)와 0b853c2 블롭의 차이는 E-TC 추가분(TEMPORAL_FILES·`temporal_on`·`prompt_config_t`·`batch_fn`·`--motion-*` 등)뿐이다 → `--train-fraction`·`--eval-train-per-kind` 구현이 커밋됨. 파드 규모 판 `diag_config`: 1,000(RB1 500·RB2 500, `fb0b5036dcb9`), 9,371(6,070·3,301), 18,742(12,140·6,602), 모두 `val_keys_sha` `e22f6d8ef7fc`, 2,000스텝 = `prereg_se2e_diag.md` §7.1(`:71`의 "RB1 6,070·3,301"은 RB2 표기가 빠진 것).
- N6. 전이 층 끝 처리: `se2e_temporal.transition_flags`(`:172-178`)는 k + j가 에피소드 밖이면 비교하지 않는다(마지막 프레임 = 정상). 도구 `meta.rule`에도 "j in 1..3"만 있다. 등록 문장의 자연 해석이지만 결과 문서에 한 줄 적기를 권함. 흐름은 val **행** 1,921개(필요 카메라가 없는 행 포함)로 만들고 표본은 1,799개 — 판정은 키로 찾으므로 무해.
- N7. **E-TC 사전 등록은 학습 전에 커밋됐다**: 파일 머리 13:05:07Z, 커밋 0b853c2 13:07:12Z(이 파일의 유일한 커밋), 13:53Z 현재 E-TC 학습 시작 전(드라이버 대기, 체크포인트 없음) — 15회차 N5(실행 뒤 커밋) 권고가 지켜졌다. 파드 `logs/se2e_temporal/prereg/`는 빈 폴더(등록 문서는 파드 사본을 주장하지 않음).
- N8. 파드 탐침 `logs/se2e_temporal/probe_proc.out`의 키 이름이 헷갈린다: `"video2"`(= 인자 2개, `size` 덮어쓰기)는 실패(StrictDataclassFieldValidationError)했고 등록 표의 "비디오 = 쌍 채움 비트 동일"은 `"video1"`(인자 1개, `do_sample_frames=False`) 결과다. 커밋 시험(`test_se2e_temporal_qwen.py`, 파드 통과)과 내 실제 프레임 확인(행 122)이 같은 결론이라 수치는 맞다.
- N9. handoff: `docs/handoff.md:110`·`r7c15_fixes.md:3`은 15회차 수정을 "커밋 안 함"으로 적었으나 f91ad52·태그 `stage3-r7fix15`로 커밋됨(작성 시점 기록, 13–15회차와 같은 모양); `:12` user-log "70번"(지금 73).
- N10. `motion_dropout`(기본 0.3)은 `RESUME_KEYS`라 움직임 줄을 끈 판에서도 값을 바꾸면 재개가 거부된다(보수적, 무해).
- N11. 시험 수: 로컬 **1006 passed / 15 skipped**(= `r7c15_fixes.md:26`; torch 없음 10, inspect_robots 2, pyarrow 1, isaaclab 1, TODO(P3) 1), 파드 CPU 전체 **1122 passed / 4 skipped**(isaaclab·pyarrow·CUDA 없음·TODO(P3); `test_se2e_temporal_qwen.py`·`test_r7c15_resume_keys.py` 포함), LeRobot 6 passed. 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N12. 단계 B 소형 CPU 스모크(`smoke --backbone tiny --device cpu --steps 40`, 14:05 UTC): 총손실 처음 5 평균 3.055 → 끝 5 2.903, eval fm 2.438 → 2.132·dec 0.787 → 0.655, `save_load` `max_abs_action_diff` 0.0·eval 같음, KI(흐름 정합 → 백본) 기울기 0.0.
- N13. video2는 카메라 표지가 길어져 결정 프롬프트 텍스트 토큰이 표본당 +25(머리 + 손목 2대; RB1 107 → 132, RB2 87 → 112)다. 등록 §2가 "지연 측정 때 실측 보고"로 둔 값이고, 지연 도구가 `prompt_tokens_first_sample`을 기록한다.
- N14. 내 기대 오류 1건: 로컬 `check16.py` c14(`batch_fn(` 호출 수 = 1)는 docstring을 세어 실패로 나왔다 — grep으로 호출 줄이 학습 스텝 `stageb_train.py:358` 하나뿐임을 확인(행 124).
- N15. 15회차 N1(`--m4-h` 도움말)·N4(`se2e_train.md` 반올림 5칸)는 지시 범위 밖으로 남아 있다(`r7c15_fixes.md` §5) — 그대로.
- N16. 논문(NOTE만): `paper/sec/3_method.tex:28-30`·`5_plan.tex:160-185`의 E-TC 서술(Δ 0.3 s, 구간 0.218·0.607·0.176, 드롭아웃 0.3, 채택 규칙 +0.02·−0.01·10 %, (single, none) = 규모 곡선 100 % 판 재사용)은 등록 문서와 같다.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = "OK"(e05·rd·calib·closed). 사전 등록 문서는 `9cee78b..f91ad52`에서 `prereg_se2e_temporal.md` 추가(0b853c2) 말고 바뀌지 않았다. 코드 줄은 `f91ad52` 기준. `9cee78b..f91ad52`의 코드 변경은 `cli_label.py`(N10)·`cli_pool.py`·`gen.py`(주석)·`eval/common.py`(N3 한 줄)·`stagea_train.py`(N3)·`stageb_train.py`(E-TC 선택 옵션·규모 옵션·N2)와 E-TC 새 파일뿐이라 행 1–99의 구현은 15회차 대상과 같다. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c16\check16.py`(22건 중 21 — 남은 1건은 내 기대 오류 N14), `verdict16.py`(13/13); **파드** = §6(`pod_cpu16.sh`, `pod_etc16.sh`, `data16.py`, `e16.py`, `trust16.py`, `pod_defs16.sh`, `pod_isaac16.sh`, `closed16_check.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1006·파드 1122 묶음에서 통과. 굵게 = 이번에 처음 대조하거나 판정·근거가 바뀐 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120, 정본 §66) | `eval/splits.py:19-42` | 시험 묶음(경계 시험); 파드 가드 19건 rc 1(§6.4: `--seeds 29,30`·`2120` "not in split … never opened") | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:102-136` | 시험 묶음 | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `pool_split`, `calib.halves` | 파드 calib `CALIB_DONE`(fit POOL·heldout DEV P1) | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; 파드 Isaac C5·C5' 성공, 13.97 s | 일치 |
| 6 | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py:289-322,408-418` | 파드 DEV 21 C5·C5' 호출 84행: `request_blob` = `request_sha256` = sha256(blob) 84/84, blob 이미지 해시 = 행 84/84, 응답 blob 해시·`probs` 질문 = `answers` 질문·합 1 84/84; Astra 4행 요청 해시·JPEG 해시·`output_text`·`max_output_tokens`·`effort` 4/4 | 일치 |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `stats.py:4` | 파드 closed `meta.bootstrap` n_boot 10000·seed 0·percentile·단위 layout seed | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 C5 대 C5' 같은 워커(행 99) | 일치 |
| 9–12 | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `e05`, `canary.py`, `eval/common.py` | 시험 묶음; 파드 `meta.prereg` OK | 일치 |
| 13 | 카나리 기준일 = 세트를 처음 돌린 날 (E :140, §79 D2) | `eval/canary.py:168-175,227-228` | 시험 묶음(`test_r7c13_canary.py`) | 일치 |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load` | 시험 묶음 | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 e05 `E05_DONE`(DEV P0·P2 3편씩) | 일치 |
| 18 | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72` | 시험 묶음(15회차 유리수 경계 12건과 코드 불변) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py` | 시험 묶음; 파드 e05 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 {0.001, 0.01, 0.05} (E :253, :487; M4 :285) | `e05.py:437-446` | 행 90 | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `e05 --d-p95`, `calib.halves` | — | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.py` | 시험 묶음 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59` | 코드 불변(15회차 18,006경우 대조); 시험 묶음 | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:128-130` | 시험 묶음; 파드 calib `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.py:178-182` | 시험 묶음 | 일치 |
| 46–49 | γ·W·비가역 W+1·τ (E :487, M4 :276, :291, §7) | `m4.py` | 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487) | `m4.older_than:56` | 시험 묶음(코드 불변) | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 시험 묶음; 파드 `--conditions C9` "refused before any worker" | 일치 |
| 54 | C5 = §4.2 전체, C5' = (b) 범주 뺌, 판정 3 (M4 :155, :232, :340-342, :361) | `core.b_line:199-205` | 파드 Isaac DEV 21: C5 `last_step` {none 1, OK 32, LAG 5, DEVIATE 4}, C5' none 42/42, 요청 상태 마지막 줄 = 행 `last_step` 84/84 | 일치(§77) |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61` | 시험 묶음; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치(15회차 N1 그대로, N15) |
| 56–58 | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔 (M4 :275, :262, :287) | `m4.py`, `core.py:459-503` | 시험 묶음 | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131` | 시험 묶음(코드 불변) | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 rd `RD_DONE`(`drop.random` n 275) | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| 66–67 | H = 1 창·`lead_max` 유한한 양수 (§75, §76 N4) | `m4.py:106-113`, `closed.py:390` | 시험 묶음; 파드 `--m4-lead-max nan` rc 1 "refused before any worker" | 일치 |
| 68 | E0 판정 4 (E :183, :197) | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 다스텝 DecCall 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용 (E :139, :347, §79 D3) | `closed.j5_after_canary:169-185` | 시험 묶음; 파드 closed `meta.j5_alpha` None·`j5_canary_gate` 기록 | 일치 |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act:455-503` | 행 54의 파드 판; 시험 묶음 | 일치 |
| 80–84 | 학습 자료 값·학습 항목 상태·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77) | `deccall_snap.py`, `stagea_data`, `serialize.py`, `stagea_train.serializer_of` | 시험 묶음; 파드 `se2e_scale/9371/last` `check_prompt` → `serializer_ok` 거짓(S7) | 일치 |
| 85 | 카나리 세트 = 고정 `question_id@vN`, 판본 바뀌면 새 기준일 (§79 D2) | `canary.select_baseline:168-175` | 시험 묶음 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 (E :125, §28 A6, §77 D4) | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 코드 불변(15회차 18,006경우); 시험 묶음 | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip (§2A.4, §27) | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py`, `stageb_train` | 코드·스크립트 `9cee78b..f91ad52` 불변(판정 스크립트 블롭 같음); 15회차 실제 로그 재계산 바이트 동일; 파드 CPU `test_stageb_torch.py`(재개 비트 재현·기본 lr 비트 동일·새 `train_fraction` 시험) 통과 | 일치 |
| 98 | 라벨 복원 기준(비트 동일, §78 (1)) | `sim/labeler.py:177-221,313` | `REPLAY_TOL` 0.0, 시험 묶음 | 일치(NaN 틈 N2) |
| 99 | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py`, `make_env(hard_reset=True)` | **파드 Isaac 한 워커 C5 → C5'(DEV 21, 모의 선택기)**: 행동 1,398개 비트 동일(첫 차이 없음), 호출 42개 시각·답 동일 | 일치(행렬은 S16) |
| 100, 118 | 라벨 신뢰 = 재생 비트 동일, 필드 없음·null·NaN 행 제외, 뺀 수 기록 (§78 (1), §80 D1) | `stagea_data.replay_bit_identical:49-53`, `eval/common.load_truth:378-412` 등 | 시험 묶음(`test_r7c14_label_trust.py`, 통계 비교에 `questions` 추가만); **파드 실제 풀**: 6,627행 중 불신 886·5질문 6,000행 중 805, row 수준 null 0; 2002·2009·2000에서 `load_truth` {133, 17} = 15회차 독립 계산 | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | 도는 `datagen.gen` 워커 5개(GPU 0·1) | 일치 / SCOPED S17 |
| 102, 120 | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes:340-369`, `sim/determinism.py:194-201` | 코드 불변; 시험 묶음; 파드 `determinism fresh --seed 1000`·`history --seeds 3,549` rc 1·폴더 없음 | 일치 |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 코드 불변; 파드 `--isaac-gpu 3` rc 1·폴더 없음 | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 106–113 | S-E2E 진단 D1–D3·종합 (`prereg_se2e_diag.md` §1–§5) | 파드 고정 사본 | 결과 불변(15회차 재계산) | 일치 |
| **114** | **§7 데이터 규모 곡선: 설정·부분집합 (§7.1)** | `stageb_train.train_fraction`(0b853c2 커밋), 파드 `ckpt/se2e_scale/*` | 파드 `diag_config`: N 1,000 = RB1 500·RB2 500, 9,371 = 6,070·3,301, 18,742 = 12,140·6,602, 37,484 = 부분집합 없음, 모두 2,000스텝·`val_keys_sha` `e22f6d8ef7fc`; 판이 쓴 파일 `11e11795…` = 0b853c2 블롭 − E-TC 추가분(N5); 시험 `test_train_fraction_keeps_the_source_mix_is_nested_and_order_free` 통과 | 일치(S18 해소) |
| **121** | **E-TC 옵션 끔 = 기준 표본, 기본 경로·프롬프트 해시 파일 무수정 (`prereg_se2e_temporal.md` §7, §8)** | `se2e_temporal.load_se2e_t:123-130`, `stageb_train._load_data`(`temporal_on` 거짓 → `D.load_for_training`) | 로컬 구성 에피소드(30프레임, 이중 팔 28행): 증강 행의 `load_se2e` = 원 행의 `load_se2e`(a1), 끔 = 위임 그대로(a2); 파드 증강 행 표본 600개 원 필드 = S-E2E 행(차 0), 등록 `check_data.json` `off_equal` true·39,283표본; `prefix_share.py`·`stageb_model.py`·`se2e_data.py` 블롭 = 등록 해시, `PROMPT_FILES` 무변경(0b853c2), 기본 `prompt_config` 불변(파드 시험 `test_stageb_train_defaults_unchanged_and_variant_config`) | 일치 |
| **122** | **V = video2: 카메라마다 [t−0.3 s, t], 10 Hz에서 k−3(시작에서 0으로 자름), 한 시간 패치 칸 0 = 과거·칸 1 = 현재 = Qwen3-VL 비디오 처리기 출력, 시각 토큰 수 불변 (§2)** | `se2e_temporal.prev_index:46-47`·`hist_fields:56-66`·`_video_images:113-120`, `se2e_temporal_model.VideoEncoder.pixels:39-55` | 로컬: `prev_index` k 0·1·2·3·4·100 → 0·0·0·0·1·97, 표본마다 now = 기준 프레임·prev = `img_prev/k{max(0,k−3)}`·표지 "(2 frames: t-0.3 s, t):"·나머지 필드 기준과 같음(b1–b3); 파드 **실제 원본 영상**: 증강 행의 과거 JPEG를 k−4·k−3·k−2 디코드 프레임과 비교 → k ≥ 4 16/16이 k−3에 가장 가까움, k = 0 → 프레임 0(평균 차 1.43/255); 표본-카메라 81,672 중 k−k_prev = 3 78,885·0 2,787(등록과 같음), 모든 행 `k_prev = max(0, k−3)`; **실제 프레임 4표본(RB1 k0·k5, RB2 k0·k15)**: 쌍 픽셀 = `video_processor([prev, now], do_sample_frames=False)` 비트 동일 4/4, 칸 1 = 정지 이미지(현재) 4/4, 칸 0 ≠ 현재(k ≥ 3) / = 현재(k = 0), grid 같음, 시각 토큰 356 = 356; 파드 시험(`test_se2e_temporal_qwen.py` 6건) 통과 | 일치(텍스트 +25토큰 N13) |
| **123** | **M = 움직임 줄: 인과 후방 차분 (x[k]−x[k−1])×10 Hz(k = 0은 0), 팔 = 활성 팔 7관절 속도 노름 3분위 still < 0.2179 ≤ slow < 0.6070 ≤ fast, 그리퍼 = [0, 1] 열림 속도(+ = 열림), 0.85 분위 0.1755 초과면 opening/closing; 로봇 줄 다음, 맥락과 세 질문 모두 (§3)** | `se2e_temporal.backward_velocity:50-53`·`motion_values:70-74`·`fit_motion_bins:77-83`·`motion_line:86-92`·`load_se2e_t:142-154` | 로컬: 구성 상태에서 qd_bwd·grip = 후방 차분(c1), 중앙 차분 `proprio.qd`와 같은 행 0(c2), 프레임 ≥ k+1을 바꿔도 행 k 불변(c3); 경계 0.2178999 still·0.2179 slow·0.6069999 slow·0.6070 fast·−0.7 fast(c4), RB1 관절값 감소 = + 열림(c5), |속도| = 문턱 → still, 한 ulp 아래 문턱 → 부호대로 closing/opening(c6), 학습 행만·3분위·q0.85(c7), 줄 위치 = "robot:" 줄 다음·맥락과 모든 질문·나머지 기준과 같음(c8); **파드 실제 원본 parquet** 8에피소드 241행: 후방 차분 차이 0·그리퍼 차이 0·중앙 차분과 같은 행 0; 구간을 내 코드(np.quantile)로 다시 계산 → n 37,484·0.21791767·0.60703500·0.17551597 = `motion_bins.json`(sha 앞 12 `e164719a92d5` = 등록), 0 비율 60.2 %·q0.80 0.0405·q0.90 0.783 = 등록 §3; 줄 분포 still/slow/fast 12,495/12,494/12,495, closing 2,846·opening 2,765 = 등록; 커밋 도구 `bins` 재실행 = 등록 파일 | 일치 |
| **124** | **드롭아웃: 학습 배치에서 표본마다 p = 0.3으로 "motion: arm=unknown gripper=unknown", 난수는 (시드, 스텝)으로 따로, 데이터 순서 난수 불변, 평가에서는 끄지 않음 (§3)** | `se2e_temporal.motion_dropout:95-109`, `stageb_train.train_loop:356-358`, `cmd_train:594-597` | 로컬: 400스텝 × 30표본 비율 0.2999(c9), 전역 `random` 상태 불변(c10), 같은 (시드, 스텝) 같은 결과·다른 시드 다름(c11), 떨군 표본은 맥락·모든 질문에 unknown·실제 줄 없음·이미지/행동 공유(c12), 원 표본 불변(c13); `batch_fn` 호출은 학습 스텝(`:358`) 하나뿐 — `evaluate`·`evalck`·`predict`·`extra_evals`는 원 표본(N14); `train_loop`의 데이터 순서 난수는 `random.Random(seed)` 별도 | 일치 |
| **125** | **새 판 표지 `D27v2-video2`·`se2e-motion@v1`, 옵션 판 `prompt_config`에 layout·motion(구간 포함)·옵션 파일 해시 → 기본 체크포인트와 섞이지 않음 (§7)** | `stageb_train.prompt_config_t:83-96`, `TEMPORAL_FILES:75-76`, `fused_model.check_prompt:319-344` | 파드: 네 형식 + 다른 구간의 sha 5개 모두 다름; `check_prompt(strict)` — (single, none) 받음, (video2, none)·(video2, motion) 거부 [`camera_ok`, `files_ok`], (single, motion)·다른 구간 거부 [`files_ok`]; `--motion-bins` 판본 ≠ `--motion-line` → 거부(`motion_bins_of:99-107`, 읽음) | 일치(오프라인 `predict`·`evalck`는 대조 안 함 N1) |
| **126** | **지표·층: 검증 300(`--val-per-kind 150 --val-seed 0`) × 3질문 = 900항목, dec_acc·dec, 전이 층 = 어떤 질문이든 프레임 라벨이 k와 k+j(j = 1..3)에서 다르면 (§4)** | `se2e_temporal.transition_flags:172-178`, `tools/se2e_temporal.py:117-154`, `temporal_verdict.metrics:48-60` | 로컬 7경우(k+3 변화 참, k+4만 거짓, k+1 참, 마지막 프레임 거짓, 창 밖 거짓, A-B-A 참, k 앞 변화 거짓) + 질문별(d1·d2); 파드: 내 프레임 루프(원본 parquet → `episode_rows` stride 1)로 12 val 에피소드 245행 다시 계산 → 등록 흐름과 불일치 0, 행 라벨 불일치 0; 커밋 도구 `transition` 재실행 = `transition_val.json`(1,921행, 0.6507, sha 앞 12 `ee7b4fdb7962` = 등록) | 일치(끝 처리 N6) |
| **127** | **채택 규칙: 주효과 V·M = 두 수준 평균 차, 상호작용 식; 채택 ⇔ 전체 주효과 ≥ +0.02 ∧ 전이 주효과 ≥ −0.01 ∧ FULL p95 증가 ≤ 10 %(V: (v2, none)/(s, none), M: (s, motion)/(s, none)), 상대 CMP_EPS 1e-12 (§6)** | `tools/se2e/temporal_verdict.py:24-34,63-67,119-128` | 로컬 구성 예측(300스냅샷, 전이 200 = 600항목): 전체 +18/900 = 0.02(부동 0.020000000000000018)·전이 −6/600(−0.010000000000000009)·p95 0.33/0.30(+0.10000000000000009) → V 채택; 전체 0.019444 → c1 거짓; 전이 −0.010833 → c2 거짓; p95 0.3300001/0.30 → c3 거짓; V 지연은 (v2, none)만 봄((v2, motion) 9 s여도 참); M 경계·(s, motion) +10 % → M 채택, +10.3 % → 거짓; 상호작용 = (a_v1−a_v0)−(a_s1−a_s0) 0.0667; 키 다른 칸·칸 이름 중복·요약 불일치 → 거부 (13/13) | 일치(입력 검사 범위 N3) |
| **128** | **판정 스크립트·등록 코드 해시, 등록은 학습 전 (§6, §7, 머리)** | 파드 `code_se2e_temporal`, `logs/se2e_temporal/run.sh` | 해시 6개 = f91ad52 블롭 = 파드 사본(N4); 등록 머리 13:05:07Z < 커밋 13:07:12Z < 학습 시작 전(13:53Z 드라이버 대기, 체크포인트 없음); `run.sh` 설정 = §7(2,000스텝, 묶음 8, lr 1e-4·헤드 1e-4, 평가 500, 검증 150/0, 시드 0, GPU 2 = video2_none, GPU 3 = video2_motion, 먼저 끝난 쪽 = single_motion, (single, none) = `se2e_scale/37484` `predict`, `predict`에 학습과 같은 옵션, 지연 = GPU 2·37484 체크포인트) | 일치 / SCOPED S18 |
| **129** | **지연 측정: 머리 + 손목 1대 표본 50(출처별 25, 시드 0), 네 형식 라운드 로빈, 워밍업 30 뒤 형식마다 200회, FULL·GPU p50/p95, 부하 평균 (§5)** | `tools/se2e/temporal_latency.py:38-112` | 코드 읽기: `stratified_val(va_2img, 25, 0)`, 기본 `--n 50 --reps 4` = 200, `--warm 30`, FULL = `forward_shared([표본])`(이미지 읽기·전처리·쌍 채움·토큰화·순전파, cuda 동기), GPU = 미리 인코딩한 묶음의 `shared_forward`, `getloadavg` 앞뒤 | 일치(실행은 S18) |
| **130** | **§81 N2 재개 검사: 학습 궤적·기록 평가 집합을 정하는 옵션은 재개 때 같아야, 나머지는 `RESUME_FREE`, 옛 체크포인트의 없는 키 = 기본값** | `stageb_train.py:267-293` | 파드(torch): 파서 기본값에서 옵션마다 한 번씩 바꿈 → 거부 집합 = `RESUME_KEYS` 40개와 같음, 받음 = `cmd`·`eval_every`·`grad_ckpt`·`init_weights`·`out_root`·`overwrite`·`reload_check`·`resume`·`run`·`save_every`·`stop_at`; `RESUME_KEYS` 중 파서에 없는 키 0; 실제 S-E2E A `step_002000/train_state.pt` 인자(새 옵션 13개 없음) → 같은 명령 받음, 5개 옵션 변경 거부, `save_every`·`eval_every` 받음; `evaluate`는 자기 생성기(`torch.Generator().manual_seed(seed)`)만 써 `eval_every`가 궤적과 무관함을 코드로 확인 | 일치 |
| **131** | **§81 N10 라벨 쓰기: 수가 없는 결과가 하나라도 있으면 null** | `cli_label.replay_max:37-43` | 로컬 9경우 규칙대로; NaN 순서 의존(N2) | 일치(N2) |
| **132** | **§81 N3 뺀 수의 질문 범위 기록** | `eval/common.load_truth:411`, `stagea_train._items:228-229`·`STAGEA_TRUST_QUESTIONS:215` | 파드 실제 풀 `load_truth` stats `questions` = 5질문; 실제 `e05 --split pool --seeds 2002,2009,2000 --truth outcome:plan` rc 0 `meta.truth_label_trust` = {plan, 133, 17, questions 5개}, git `f91ad522`, prereg OK; 단계 A 쪽은 시험 묶음(`test_r7c15_label_write.py`) | 일치 |

### 5.1 15회차 표(`r7_cycle15.md` §5)와의 차이
- 행 114: 구현이 커밋됨(15회차 S18 해소, N5).
- 행 99: 새 시드 DEV 21로 §78 재확인(1,398개 비트 동일).
- 새 행 121–129: E-TC 사전 등록 전 항목을 구성 입력·실제 원본 영상/parquet·실제 처리기로 확인.
- 새 행 130–132: 15회차 수정(§81 N2·N10·N3).

## 6. 확인한 것 (근거)

### 6.1 15회차 수정(정본 §81)의 독립 확인 (과제 2)
- **N2 재개 키**: 행 130. 분류의 완전성은 커밋 시험(`test_every_train_option_is_classified`)과 별개로 내 전수 변경으로 확인했다. 궤적 영향 판단: `eval_every`(평가는 자기 난수 생성기·`model.eval()`), `save_every`(`torch.get_rng_state` 읽기만), `reload_check`(학습 끝 뒤), `grad_ckpt`(재계산), `init_weights`(재개와 함께면 거부, `cmd_train`) — `RESUME_FREE` 분류가 맞다.
- **N10**: 행 131(NaN은 N2).
- **N3**: 행 132; 풀 불신 886(전체)·805(5질문) = §81 수치.
- **문서 D-1·D-2·N15·N7**: 표시 위치 `pool.md:32`·`:33`·`:57`, `e_m4b_meas.md:19`, `D28-m4-critic-measurement.md:149`, `r2_datagen.md:99`, `draft-log.md:412`, `cli_pool.py:204-206`·`:222-223`·`:500-501`, `gen.py:267`, `r7c14_fixes.md:24`, `handoff.md:3`·`:108` — 모두 있음. §81 본문(D-2 13시드·20편, N15 12:57:49 UTC)은 15회차 보고서 수치와 같다.

### 6.2 E-TC 사전 등록 대 코드·데이터 (과제 1 일부)
- 파드 읽기 전용: `data/se2e_t/{motion_bins.json, transition_val.json, conv/*.stageb.jsonl, conv/augment.json, conv/img_prev/}`, `data/se2e/{raw, conv}`, `logs/se2e_temporal/{run.sh, check_data.json, probe_proc.out, bins_probe.json, augment.out}`, `code_se2e_temporal`, `code_se2e_diag/harvest/train/stageb_train.py`, `ckpt/se2e_scale/*/log.jsonl`(`diag_config`·`config`), `ckpt/se2e_scale/9371/last/stageb.json`, `ckpt/se2e/se2e_A_s0/ckpt/step_002000/train_state.pt`. 행 114·121–130.
- `augment.out`: RB1 25,433행·RB2 17,380행 원 필드 모두 같음(합 42,813 = 등록 §7), 에피소드 718·856.
- 시각 순서: 등록 13:05:07Z < 커밋 0b853c2 13:07:12Z < E-TC 드라이버 기동(13:10:54Z, 규모 판 끝 대기) < 이 검토 13:53Z(학습 없음). 규모 곡선 결과는 검토 중 커밋(3478cf2, 범위 밖).

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 errors 없음**(standard·dr × mug_tray·mug_marker·bottle_tray 각 6). LeRobot 내보내기 시험 **6 passed**(14:04 UTC). |
| 2 모델 | 충족(CPU) | GPU 없음(0·1 = R2_TRAIN·내 Isaac, 2·3 = S-E2E 판) → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N12): 손실 감소·`save_load` 차 0.0·KI 0.0; CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 21 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c16`, 14:06:29–14:10:23 UTC, `IR_INST` `r7c16_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 13.97 s, 호출·Astra 행 필드·blob 확인(행 6), `meta.bootstrap` 10000, `meta.prereg` OK, git `f91ad522`, `code_sha` `9242f67e59a09ee4`, 하드 리셋 빌드(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 14:05–14:06 UTC): `e05 --data …/jsel_dev/P0,…/P2 --split dev --episodes 3` → `E05_DONE`, `rd --variants standard=…/jsel_dev,random=…/gen_dev/random/P0 --episodes 2` → `RD_DONE`(n 275), `calib --fit-data …/pool --fit-split pool --heldout …/jsel_dev/P1 --heldout-split dev --episodes 5` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan`(행 132) → rc 0. 모두 prereg OK. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`j5_*`·`truth_label_trust`(+ `questions`); 규모 판·E-TC 판은 폴더마다 `CODE_HASHES.txt`; 정리 뒤 흔적 없음(머리 규칙 줄). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`)
- `e05 --split cal|test|test_p5`, `calib --fit-split cal`, `calib --heldout-split test`, `rd --split test`, `closed --split test --seeds 1149`, `closed --split cal --seeds 500`, `closed --split test_p5 --seeds 1300` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 29,30`·`--split pool --seeds 2120` → "not in split … (refused, never opened)". `--isaac-gpu 3` rc 1; `--conditions C9`·`--m4-lead-max nan` → "refused before any worker". `HARVEST_ALLOW_SPLIT=dev closed --split cal`, `HARVEST_ALLOW_SPLIT=test e05 --split cal` 거부. `gen gen --seeds 10007-10008`(확인 인자 없음), `determinism fresh --seed 1000`, `determinism history --seeds 3,549` 거부. **19건 모두 rc 1**, 거부된 명령의 출력 폴더 0개. (15회차 절차 사고의 원인이던 `--m4-h 2` 줄은 목록에서 뺐다.)

### 6.5 A. 테스트
- 로컬(`…\r7c16\repo` = f91ad52 archive, Git Bash, `python -m pytest -rs -p no:cacheprovider -o addopts="" --basetemp=…\r7c16\pt`): EXIT 0, **1006 passed · 15 skipped**(136 s; N11).
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch, 13:54–13:56:35 UTC): **1122 passed, 4 skipped**, EXIT 0.

### 6.6 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외, §72–§81)
- §78 사실(선행 실행 ≠ 비트 동일): 문서·코드 주석 전수(`prefix|warmup|선행|canonical` × `bit|비트|exact|0.0`) — 남은 곳 `pool.md:58-59`·`r2_datagen.md:89-93`은 그 시점 측정값 행(채택 서술 `:57`·`:99`에 정정 표시), `pool_replay_debug.md`·`physx_hard_reset.md`는 맞음. 새 불일치 없음.
- §81 N2(`RESUME_KEYS`)·N10(`replay_max`)·N3(`questions`): 코드·정본·수정 보고서 서술이 코드와 같다; `summarize`·`poolsum`의 `or 0.0`(`cli_label.py:208-210`)은 §80·§81이 두기로 한 요약.
- §80 D1 수치 886·805·29편: `pool_replay_debug.md`·`labeler.md`·논문 `6_prelim.tex:61`과 같음.
- E-TC(새 등록) 대 문서: 논문 서술 같음(N16); 규모 곡선 부분집합 수 = 로그(N5).
- 정본 범위: `handoff.md:3`·`:5` = §1~§81(맞음). 날짜 순서: §81 13:42 UTC·`r7c15_fixes.md` 13:48 UTC < 커밋 f91ad52 13:49:47 UTC(순서 맞음).

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(시작·끝 `git status` 깨끗, 검토 중 다른 세션 커밋 3개 — 범위 밖). 로컬 C:: 이 검토의 산출물 없음(하네스 작업 출력 파일만). 파드: 내 항목만 삭제 — `tmp/r7c16`(381 MB), 내 Isaac 판이 만든 `tmp/carb.3ZFqsb`·`tmp/tmpameswd3b`·`cache/pyc_r6/data/harvest/tmp/tmpameswd3b`, LeRobot 시험이 만든 `cache/hf/datasets/parquet/default-1b907c94c80dd9f3`(+ 잠금, `dataset_info.json`에 r7c16 경로), `ir/kitcache/cyclo-r7c16_standard`(없었음). `tmp/hub-root.lock`(전부터 있음)은 두었다. 끝에 내 프로세스 0, `/data` 밖 새 파일 0. 절차 사고 1건(머리 규칙 줄).

## 7. 다음 순회 전에 할 일 (제안, 통과에는 영향 없음)
1. N1: `stageb_train predict`·`evalck`에 체크포인트 `prompt_config`(layout·motion) 대 인자 대조 — E-TC 결과 `predict` 전에 넣으면 칸 혼동을 막는다(단, 고정 사본을 바꾸는 일이라 등록 §7 "재사용 조건" 절차와 함께 판단).
2. N2: `cli_label.replay_max`에 유한성 검사.
3. N3·N6·S18: E-TC 결과 문서에 `n_val_snapshots`·`val_keys_sha`·전이 층 끝 처리·(single, none) 재사용 조건 대조 결과를 적기.
4. N9·N15: handoff 15회차 줄 커밋 표시, 남은 15회차 NOTE(N1·N4).
