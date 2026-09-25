# R7 객관 검증 순회 — 17회차 (cycle 17, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle16.md` §5 표·결론에 기대지 않고 사전 등록 원문에서 대조표를 다시 만들고, 행마다 **구성한 입력 → 실제 함수·런타임 출력** 또는 **파드 원자료 재계산**으로 확인함). 작성 2026-09-25 14:45 UTC 무렵(= 23:45 KST; 로컬 시작 약 14:15 UTC, 파드 첫 명령 14:17:37 UTC, 파드 정리 끝 14:36:28 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 `9a0ae52`(커밋 시각 2026-09-25 14:16:03 UTC). `f91ad52..9a0ae52` = 문서만(`CLAUDE.md` 규칙 2줄, `docs/user-log.md` 72–74, `docs/stage3/results/se2e_diag.md` 8절 데이터 규모 곡선 결과(3478cf2), `draft-log.md`·`handoff.md`·`direction-log.md` 줄, `r7_cycle16.md`). `harvest/`·`tools/`·`tests/`·사전 등록(`prereg*.md`, `prereg.json`, `E-first`, `EVAL`, `M4`)·정본 `00-interfaces.md`는 `git diff f91ad52 9a0ae52`에서 **변경 0**(직접 확인), `paper/`도 이 구간 변경 없음. 검토 중 다른 세션이 `f8c4c29`·`5e87ce0`(user-log 75)·`925b0b0`(`docs/research/astra_role_2026-09-25.md`)·`a1bb055`(정본 §82: 하트비트·경계 확인 강등 등)·`4eb988d`(user-log 76)를 커밋했다 — 범위 밖(다음 순회 참고: 그 구간에서 `docs/user-log.md`가 줄 끝 `\r\r\n`으로 바뀌어 `git diff --numstat` 318+/308−, 공백 무시 비교로는 10줄 추가뿐; 원문 대조 규칙(`CLAUDE.md` 빨간 줄) 때문에 18회차가 확인할 것). `git -c safe.directory=D:/qdd -c core.autocrlf=false archive 9a0ae52`를 Python tarfile로 `D:\tools\scratch_qdd\r7c17\repo`에 풀어 검토했다(493파일). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c17/code`, 494파일 = + JSON `CODE_VERSION` `9a0ae523…`, dirty false); 파드 산출 `meta.git.commit` = `9a0ae5233224…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle7.md`–`r7_cycle16.md`, `r7c7_fixes.md`–`r7c15_fixes.md`, 정본 `00-interfaces.md` §1–§81(뒤 절 우선; [사용자] 제목 절은 그대로; 논문 .tex는 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`(§7 포함)·`prereg_se2e_temporal.md`·`M4-overlap-commit.md`(조건 정의).
- 분류(16회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 정본·사전 등록에 없는 것. 정본(또는 사전 등록)이 "나중에 할 일"로 적은 것은 SCOPED.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만 — 첫 명령이 "dubious ownership"으로 거부돼 전역 설정을 쓰지 않고 명령마다 넘김; 이 보고서 한 파일만 씀, 시작·끝 `git status` 깨끗). 로컬 임시 = `D:\tools\scratch_qdd\r7c17`(스크립트는 모두 Write 도구로 쓰고 경로로 실행; heredoc·`cat >`·`python -` 없음 — 파드용 `se2ev17.sh` 초안에 넣었던 빈 heredoc 두 줄은 올리기 전에 지웠다; 파드로 보낼 때는 로컬 파일을 `tar -cf - | tar -xf -`로, 정리 스크립트는 `bash -s < clean17.sh`로). 로컬 pytest TMP·basetemp = `…\r7c17\tmp`·`…\r7c17\pt`(공용 `scratch_qdd\tmp_local`·`pytest_tmp`·`torchinductor`에 새 파일 0 확인, C: 쓰기 없음 — 하네스 작업 출력 파일만). 파드 = `/data/harvest/tmp/r7c17`(코드 사본·pytest·산출, 정리 전 391 MB). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c17`, `IR_INST` `r7c17_standard`, `IR_ROOT=cyclo`, 기본 `r6` 접두사 안 씀; 그 시각 GPU 1에는 R2_TRAIN `datagen.gen` Isaac 3개가 돌고 있었음 — 건드리지 않음), GPU 0·1 R2_TRAIN·GPU 2·3 E-TC 학습 건드리지 않음, GPU 학습 없음. CPU: 시작 전 파드 cgroup `cpu.stat` 5 s = 사용 약 19.3코어·스로틀 증가 0(쿼터 32) → `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음. 시드 DEV·POOL만(`HARVEST_ALLOW_SPLIT`는 가드 음성 시험 2건에서 `=dev`·`=test`만). 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. `ckpt/se2e*`·`logs/se2e*`·`data/se2e_t`·`r2/train`은 **읽기만**(분석 스크립트 출력은 내 폴더로).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 18 |
| NOTE | 16 |

코드·사전 등록·정본은 16회차 대상(f91ad52)과 바이트가 같고, 모든 행동 확인이 통과했다: 로컬 **1006 passed / 15 skipped**, 파드 CPU **1122 passed / 4 skipped**, LeRobot 6 passed; 가드 22건 rc 1; R2 DEV `validate_episode` **36/36**; 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료·`prereg` OK; 새 시드 **DEV 12**에서 같은 Isaac 워커 C5 → C5' 행동 **1,877개 비트 동일**; 단계 B CPU 스모크(손실 감소·저장/재적재 차 0.0·KI 0.0). 이번에 새로 깊게 본 네 영역 — **Astra 호출 주기(§45)**, **단계 A 학습 자료 경로(labels_v2·§77 `last_step`)**, **LeRobot 내보내기 계약(§63·§66)**, **카나리 도구 여러 날 끝까지(§79 D2·D3)** — 도 동작이 정본과 맞았다(주기의 시간 초과 뒤 재송신 모양만 NOTE N4). **데이터 규모 곡선(`se2e_diag.md` 8절)**은 파드 로그(`ckpt/se2e_scale/*/log.jsonl`, 읽기 전용)에서 §7 규칙으로 다시 계산해 수치·판정("레버 약함(같은 스텝 기준) + 50→100 % 포화", D2 재판정 "학습 가능·일반화 간극")이 문서와 같고, §7은 실행 전에 고정됐다(파일 수정 12:33:46Z가 지금도 그대로 < 실행 12:36:17Z). 다만 **같은 문서의 결론 요약·종합 절이 8.3의 "D2 불확정 해소"를 반영하지 않은 채 "D2 불확정 → 판정 불가 / 규칙상 확정 레버 없음"으로 남아 있다** — 정정 표시 없음 → **DOC 1** → 연속 무결 카운트는 이어지지 않는다(문서만 고치면 되는 항목).

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① **Astra 호출이 15 s 안에 답이 없을 때 재송신 모양**(N4) — K1(= K0 + 단계 경계, 하트비트 없음)에서 T_sub가 시간 초과되면 다음 호출이 하트비트 문구(`HB_TEMPLATE`)로 나가고, K2에서는 시간 초과된 경계 질문이 다시 가지 않고 하트비트로 바뀐다(`astra_hb.py:125-126`, `:93-101`). 정본 §45의 "15 s 무응답이면 기록 후 재송신"은 T_hb 줄에만 있고 T_sub의 시간 초과 처리는 정본에 없다; 이 모양이 영향을 주는 곳은 E-M8c(K0–K4) 조건 순도뿐이며 E-M8 계열은 정본 §77 N8 (13)이 완료 정의 밖 사전 등록 실험으로 둔 것(SCOPED)이고, 유료 API라 지금 돌지 않는다 → DEFECT가 아니라 NOTE로 두고 E-M8c 전에 고치거나 정본에 적기를 권한다. ② `e05`가 가드 거부 전에 `--out` 폴더를 만든다(N10) — 거부 대상 파일은 열지 않으므로 가드 성질은 지켜지고, "폴더를 거부 뒤 만든다"는 §80 N3은 `determinism`만 정했다.)

## 2. DOC

### D-1. `se2e_diag.md`의 종합 칸이 8.3의 D2 재판정 뒤에도 "D2 불확정 → 판정 불가 / 규칙상 확정 레버 없음"으로 남음 (정정 표시 없음)
- 위치: `docs/stage3/results/se2e_diag.md:12`(1절 결론 요약) "종합 칸(사전 등록 5절): D1 아님 × **D2 불확정** × D3 아님 → **판정 불가** …", `:125`(6절 종합 읽기) "사전 등록 표의 칸: D1 아님 × **D2 불확정** × D3 모호성 아님 → 판정 불가 … **규칙상 확정 레버는 없다**".
- 같은 문서의 뒤 결과: `:167`(8.3) "N = 1,000 판 step 2000: 학습 부분집합 1.000 ≥ 0.95 그리고 검증 0.552 ≤ 0.75 → '라벨은 학습 가능, 일반화 간극 → 데이터 늘리기가 듣는다(데이터 규모 레버)'. **D2(4절)의 '불확정'은 이 판으로 해소된다**"; `:14`(요약에 더한 줄)도 "D2 재판정 → 라벨은 학습 가능, 일반화 간극". 사전 등록 `prereg_se2e_diag.md:62`·`:86-87`은 이 판의 목적을 "D2를 원래 규칙으로 해소한다"로 적었다.
- 어긋남: 사전 등록 5절 표(`prereg_se2e_diag.md:45-54`)는 D2 판정을 열쇠로 칸을 정한다. D2가 "학습 가능·간극"으로 해소되면 칸은 `:49` "**아님 × 학습 가능·간극 × 모호성 아님 → 데이터 규모 한계 → 데이터 늘리기**"이고, "판정 불가·확정 레버 없음"은 더 이상 현재 상태가 아니다. 문서는 1절에 8절 줄을 더하면서 종합 줄(`:12`)과 6절(`:125`)을 그대로 두었고 정정·갱신 표시가 없으며, 해소 뒤의 5절 칸을 어디에도 적지 않았다. 게다가 그 칸("데이터 늘리기")은 8.2의 같은 스텝 곡선 판정("데이터 규모 레버 약함, 50→100 % 포화")과 긴장 관계라 8.3 끝 줄(`:169`, "범위가 다르다")만으로는 사전 등록 5절의 읽기가 무엇이 됐는지 독자가 알 수 없다(사전 등록 읽기 표를 결과 뒤 한쪽만 보고하는 모양).
- 확인: 파드 로그 재계산(행 106–113·133–134, §6.1) — D2 원판(1,000스텝 상수 lr) step 1000 학습 0.8853·검증 0.5600 = 불확정(문서 `:9` 맞음), 규모 판 N = 1,000 step 2000 학습 1.000·검증 0.5522 = "학습 가능·간극"(문서 `:167` 맞음). 두 판정 자체는 옳고, 틀린 것은 종합 칸을 갱신하지 않은 현재 시제 서술이다.
- 분류 근거: 15회차 D-1(뒤 결과(§78)로 틀리게 된 채택 서술에 정정 표시 없음 → DOC)과 같은 모양. 이번 것은 3478cf2(f91ad52 뒤)에서 처음 생겨 16회차 대상에는 없었다.
- 고칠 것(제안): `:12`·`:125`에 "[갱신 8.3: D2 재판정(규모 판 N = 1,000, 코사인 2,000스텝) = 학습 가능·일반화 간극 → 사전 등록 5절 칸 = 'D1 아님 × 학습 가능·간극 × 모호성 아님 → 데이터 규모 한계(데이터 늘리기)'; 단 같은 스텝 곡선(8.2)은 9k 이상에서 레버 약함 — 두 읽기의 관계는 8.3]" 같은 표시를 달고, 논문·handoff에 이 문서를 인용할 때 같은 문장을 쓴다.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀. EVAL H1–H3 기준선 비교.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드에서 진행 중(읽기만: `datagen.gen … --seeds 10000-10599 --confirm-train` Isaac 워커, GPU 0·1); `gen gen --seeds 10007-10008` 확인 인자 없이 rc 1(가드 17).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)) — 규모 판·E-TC 체크포인트 내부용.
- S5. §67 C8(M9 복구·T_fail 뒤 하트비트 정지 — `HeartbeatScheduler.pause_until`은 있으나 `core`가 부르지 않음, patch/replace의 A5′ 검사·계약 편집, 확인 헤드 보정 파일 기본 미보정).
- S6. Astra 카나리 "none"(§67 보충) — 파드 DEV 12 C5·C5' Astra 4행 `canary_id` "none".
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위(`calib` = 판정 1·8).
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): E0.5 `fine_dir`, Jev-L E0 측정 도구, 결정 호출 이미지 원본 저장 안 함, **완료 정의 밖 사전 등록 실험(E-M8 계열 포함 — N4의 근거)**.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` "boundary (ambiguous)" 주석 — 9a0ae52에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화(J4를 켜기 전 필수 작업).
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **E-TC 판정은 아직 없음**(`prereg_se2e_temporal.md` §7): 파드(읽기만, 14:31Z) — 규모 판이 끝난 뒤 GPU 3 `video2_motion` 14:00:54Z·GPU 2 `video2_none` 14:01:56Z 시작, 학습 기록 약 1,440 / 2,000스텝, 판 폴더 `CODE_HASHES.txt`가 등록 해시와 같음(행 128). (single, none) 재사용 조건은 이번에 확인됨(N14).

## 4. NOTE
- N1. (16회차 N1 그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`(layout·motion)를 자기 옵션과 대조하지 않는다(`stageb_train.py:646-668`·`:670-686`). 등록 드라이버 `logs/se2e_temporal/run.sh:35`는 `predict`에 학습과 같은 옵션(`"$@"`)을 넘긴다 — E-TC 네 칸 `predict` 결과를 판정 스크립트에 넣기 전에 칸마다 `prompt_config` 일치를 결과 문서에 적기를 권함.
- N2. (16회차 N2 그대로) `cli_label.replay_max`(`cli_label.py:37-43`)의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical`은 NaN을 불신(내 D7 8경우)이라 영향 없음.
- N3. (16회차 N3 그대로) `temporal_verdict.py`의 입력 검사가 `assert`(`:111-116`)이고 검증 집합 = 등록 300·900항목을 보지 않는다. 결과 문서에 `n_val_snapshots`·`val_keys_sha`를 함께 적기를 권함.
- N4. **Astra 시간 초과 뒤 재송신 모양**(`astra_hb.py:93-101`·`:106-112`·`:125-126`, `core.py:462-465`): 가짜 세계 + 느린 모의 Astra(지연 20 s > 15 s)로 확인(`hb17.py`) — K1: 호출 = [sub, sub, **hb(하트비트 문구)**] — 두 번째 경계 질문이 시간 초과되자 K1에 없는 하트비트 호출이 나감; K2: [hb, sub, hb] — 시간 초과된 경계 질문은 다시 가지 않고 하트비트로 바뀜. 지연 3 s면 K1 = [sub, sub]로 정상. §45의 재송신 규칙은 T_hb 줄(`00-interfaces.md:412`)에만 있고 E-M8c는 SCOPED(S13)라 NOTE; E-M8c 전에 "시간 초과된 호출은 같은 종류로 재송신"으로 고치거나 정본에 적기를 권함(K4 예산 계산에도 영향).
- N5. **§7.2 규칙 문구 "둘 다 아니면 → 약함"**(`prereg_se2e_diag.md:82`): 이번 결과는 "확인" 불충족(b 0.090 ≥ 0.05이지만 Δ25 +0.0011 < 0.03) + "포화" 충족이다. 문자 그대로("확인도 포화도 아니면")면 주 판정이 비고, 등록 예시 "확인, 단 50 %→100 % 포화"는 포화를 주 판정에 붙는 표시로 쓰므로, 문서의 읽기("확인 조건 불충족 → 약함" + 포화 표시, `se2e_diag.md:161-163`)가 규칙을 완결하는 유일한 읽기다. 문서에 이 해석을 한 줄 적기를 권함.
- N6. `se2e_diag.md:155` N 37,484 step 2000 NLL "0.774" — 로그 `0.7734998467661596` → 0.773(0.7735로 먼저 반올림한 이중 반올림). 판정 무관(15회차 N4와 같은 종류).
- N7. `se2e_diag.md:179` GPU 사용률 "12:36–14:00Z 창" 69.1 %·68.4 %(중앙 81 %·78 %)는 창 시작을 약 12:37–12:38Z로 잡으면 그대로 나오고, 12:36:17Z부터면 68.7 %·68.0 %(`gpu_window.py` 재실행). 문장 뜻 무관.
- N8. §7 추가 등록의 커밋(9cee78b 12:57:49Z)은 규모 판 시작(12:36:17Z)·첫 평가(약 12:48Z) 뒤다(15회차 N5와 같은 사실). 내용 고정은 확인: 작업 트리 파일 수정 시각이 지금도 **12:33:46Z**(11,465바이트, sha256 `62de50ae…`) = 커밋 블롭, 그 뒤 이 파일을 바꾼 커밋 없음. E-TC는 권고대로 학습 전 커밋(16회차 N7).
- N9. handoff 등 작성 시점 기록: `handoff.md:3` 머리 "마지막 갱신 13:42 UTC"는 14:16 줄(`:111`)을 더한 뒤에도 그대로; `handoff.md:111` "그 사이 커밋은 문서·**논문**·데이터 규모 결과·user-log뿐" — f91ad52..9a0ae52에 `paper/` 변경 커밋 없음(상한 목록이라 틀린 사실은 아님); `draft-log.md:457` "커밋 안 함" → 3478cf2로 커밋됨(13–16회차와 같은 모양).
- N10. `e05`는 `--out` 폴더를 가드 거부 전에 만든다(`e05.py:679`) — 가드 21(`--data …/pool --split dev`)이 rc 1 "not in split dev … never opened"로 거부했지만 빈 `g21/` 폴더가 남음. 파일은 열지 않았다.
- N11. **카나리 `--force` 같은 날 재실행은 그날 파일을 덮는다**(`canary.py:198-201`, 파일 이름 = 날짜 + 지문): 그날 카나리가 표류 의심이었어도 `--force` 재실행이 깨끗하면 `last_drift`가 사라져, 그 표류 뒤에 맞춘 보정이 없어도 J5 게이트가 다시 켜질 수 있다(§79 D3 "재보정 전까지 꺼짐"의 우회로; 운영자가 `--force`를 줘야만 생김). 표류 파일은 덮지 않고 새 이름으로 두기를 권함.
- N12. 시험 수: 로컬 **1006 passed / 15 skipped**(torch 없음 10, inspect_robots 2, pyarrow 1, isaaclab 1, TODO(P3) 1; 140 s), 파드 CPU **1122 passed / 4 skipped**(isaaclab·pyarrow·CUDA 없음·TODO(P3); 120.5 s), LeRobot 6 passed(20.8 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다. 내 구성 시험: `check17.py` 38/38, `verdict17.py` 6/6, `etc17.py` 7/7, 파드 `lr17.py` 30/30.
- N13. 단계 B 소형 CPU 스모크(14:29 UTC): 총손실 처음 5 평균 3.055 → 끝 5 2.903, eval fm 2.438 → 2.132·dec 0.787 → 0.655, `save_load` `max_abs_action_diff` 0.0·eval·정규화 같음, KI stop: 흐름 정합 → 백본 기울기 0.0(시작·끝), aux 0.45/0.75·dec 1.75/1.70 > 0.
- N14. **E-TC (single, none) 재사용 조건 확인**(16회차 S18의 남은 항목): `logs/se2e_temporal/pred_single_none.jsonl` 요약 = `ckpt se2e_scale/37484/last`, `val_keys_sha` `e22f6d8ef7fc`, `dec` **0.7734998467661596** = 규모 판 로그 step 2000 `dec` 그대로, `dec_acc` 0.683333 = 로그, 항목 900개; 드라이버 `single_none predict rc=0` 14:01:56Z.
- N15. `detect_phrase`(§46)는 여전히 고정 대역 표(`perception/seg.py:16`)이고 Astra 계약 편집이 없다(`r5_closed_loop.md:92`, 1회차 N7) — §58 뒤 M1은 모듈형 기준선용, 계약 편집은 S5.
- N16. 논문(NOTE만): `paper/main.tex:8`은 "규모 곡선 진행 중"(12:45 UTC 판)이고 8절 결과·D-1의 종합 칸은 아직 논문에 없다 — user-log 73으로 갱신 주기가 4시간이 되어(마지막 논문 커밋 ad4f7b0 13:47Z) 늦은 것은 아니다. 반영할 때 D-1의 갱신 문장을 같이 쓸 것.

---

## 5. 사전 등록 대조표 (과제 1, 원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**, 파드 산출 `meta.prereg.check` = "OK"(e05·e05o·rd·calib·closed). 사전 등록·정본·코드는 `f91ad52..9a0ae52`에서 바뀌지 않았다(`git diff` 빈 출력). 코드 줄은 `9a0ae52` 기준. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c17\check17.py`(38/38), `verdict17.py`(6/6), `etc17.py`(7/7), `hb17.py`; **파드** = §6(`pod_cpu17.sh`, `pod_eval17.sh`, `data17.py`, `lr17.py`, `canary17.py`, `stagea17.py`, `scale17.py`, `gpu17.py`, `diag17.py`, `se2ev17.sh`, `pod_isaac17.sh`, `closed17.py`, `meta17.py`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1006·파드 1122 묶음에서 통과. 굵게 = 이번에 처음 대조하거나 판정·근거가 바뀐 행.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 (E :113-120, 정본 §66), R2_TRAIN 10000–59999 (§66) | `eval/splits.py:13-14,19-42`, `datagen/gen.py:35-50` | 로컬 경계 19값(0, 29/30, 499/500, 549/550, 999/1000, 1149/1150, 1299/1300, 1329/1330, 1999/2000, 2119/2120) → 기대 분할 그대로, 보호 분할은 변수 없음·다른 값이면 거부·같은 값이면 통과(A1–A6); 파드 가드 22건 rc 1(§6.4) | 일치 |
| 2 | POOL 120 × 10, 경계 30 % 과표집 (E :121, §76 D-2) | `sim/snapshot.py:102-136` | 시험 묶음; 파드 실제 풀 결정 스냅샷 1,200개·시드 2000–2119 120개(행 80) | 일치(주석 S14) |
| 3 | `ambiguous` = 히스테리시스 띠 (E :121) | `snapshot.py:89-99` | 시험 묶음 | 일치 |
| 4 | 분할 = 에피소드 (E :122) | `stagea_data.split_of:151-157`, `calib.halves` | 파드 실제 풀 단계 A 항목 fit→train 3,000·eval→val 3,000; calib `CALIB_DONE`(fit POOL·heldout DEV P1) | 일치 |
| 5 | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py:26-38` | 시험 묶음; 파드 Isaac DEV 12 C5·C5' 성공 1.0, 18.77 s | 일치 |
| 6 | 호출 기록: 질문별 확률·요청/응답 원문(E :125), Astra A6(E :126, §28) | `core.py:279-322,395-426` | **파드 DEV 12 C5·C5' 결정 호출 112행**: `sha256(request_blob)` = `request_sha256` 112/112, 행 이미지 해시가 요청 본문에 있음 112/112, 응답 blob 해시 112/112, `probs` 질문 = `answers` 질문·합 1 112/112; Astra 4행: 요청 해시·머리캠 JPEG 해시·`effort` low·`max_output_tokens` 600·`output_text` 4/4 | 일치 |
| 7 | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py:4,32` | 로컬 `N_BOOT` 10000(E1); 파드 closed·e05·rd `meta.bootstrap` n_boot 10000·seed 0·percentile·단위 기록 | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 C5 대 C5' 같은 워커(행 99) | 일치 |
| 9–12 | 판정 2 Holm, 판정 10, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `e05`, `canary.py`, `eval/common.py` | 시험 묶음; 파드 `meta.prereg` OK(해시 5절); 카나리 비교(`compare`)가 기준일이 있을 때만 계산(행 13) | 일치 |
| 13, 85 | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 집합의 첫날, 판본 바뀌면 새 기준일 (E :136-140, §79 D2) | `eval/canary.py:168-175,188-252` | 로컬 F1(판본 v2 첫날 선택, v3·다른 세트 → None); **파드 카나리 끝까지(모의)**: 세트 고정(같은 이름 재생성 rc 1), 첫 실행 `baseline` null; 전날 파일(같은 세트·qid·답) → `baseline` = 그 파일·`drift_suspect` false; 전날 파일의 qid만 바꿈 → `baseline` null; 9/23·9/24 두 파일 → 이른 9/23 선택 | 일치(`--force` 덮어쓰기 N11) |
| 14 | 모델 식별 필드가 바뀌어도 같은 처리 (E :139) | `Calibration.load` | 시험 묶음 | 일치 |
| 15–17 | E0.5 표·재시험·같은 시각 K = 3 (E :236-238) | `e05.vote_steps`, `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P0,P2 --split dev --episodes 3` → `E05_DONE` | 일치 |
| 18 | γ 2/3 (E :240, M4 :276) | `m4.share_at_least:72-77`, `GAMMA` `:46` | 로컬 (2,3)·(3,4)·(4,6) 참, (1,2)·(3,5) 거짓, 0.67 소수 = 정확값(2/3보다 큼) → (2,3) 거짓 (B1·B2·B4) | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4·층 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록(§73) / 일치 |
| 21–28 | 판정 1–10 경계 (E :256-265) | `replay.judge_e05`, `e05.py` | 시험 묶음; 파드 e05 `E05_DONE` | 일치 |
| 29, 89 | FLIP_TH 후보 α 0.01·범위 {0.001, 0.01, 0.05} (E :253, :487; M4 :285) | `e05.py:437-446` | 시험 묶음(`test_r7c13_flip_th.py`) | 일치 |
| 30 | 같은 시각 뒤집힘 성공·섭동 따로 (E :253, §27) | `e05.py:352-383` | 시험 묶음 | 일치 |
| 31–33 | d_p95 = E0 값, 분당 400 [가정], E1 반분 | `e05 --d-p95`, `calib.halves` | — | 정본 기록 |
| 34–35 | ECE 15 동일 질량, 오답 < 30 판정 불가 (E :320) | `calibration.py` | 시험 묶음 | 일치 |
| 36 | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat:59-64` | 로컬 n 99·α 0.01 → 99번째, n 98 → inf, n 19·α 0.05 → 19번째(E2) | 일치 |
| 37–43 | log p 자름·질문별 온도·원 확률·판정 1·7·8·`ambiguous` ECE 제외 (E :333-346) | `calibration.py`, `core.py:362-393` | 시험 묶음; 파드 calib `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| 45 | N_max = ⌈d̂/T_c⌉+1 (M4 :258) | `m4.py:178-182` | 시험 묶음 | 일치 |
| 46–49 | γ·W·비가역 W+1·τ (E :487, M4 :276, :291, §7) | `m4.py` | 시험 묶음 | 일치 |
| 50 | conformal α 0.01·w 5 ((b) 경계) | 확인 헤드 보정 파일 | 기본 미보정 | SCOPED S5 |
| 51 | STALE_MAX 1.5 s (E :487) | `m4.older_than:56-58`, `M4Params.stale_max:88` | 로컬 나이 1.5 = 유지, 1.5 + 1e-6 = 버림, 기본 1.5·FLIP_TH None (B3·B5) | 일치 |
| 52–53 | C2 = VLM Stream, C0–C6 설정 (M4 :329-345) | `conditions.py`, `m4.py:220-226` | 시험 묶음; 파드 `--conditions C9` "refused before any worker"(가드 13) | 일치 |
| 54 | C5 = §4.2 전체, C5' = (b) 범주 뺌(줄은 none), 판정 3 (M4 :155, :232, :340-342, :361; §77 보충 (3)) | `core.b_line`, `core._boundary:527-578` | **파드 Isaac DEV 12**: C5 `last_step` {none 1, OK 32, LAG 8, DEVIATE 15}, C5' none 56/56, 요청 상태 마지막 줄 = 행 `last_step` 112/112 | 일치(§77) |
| 55 | H 1과 3 (정본 §2, M4 :188-189) | `m4.early_ask_steps:61` | 시험 묶음; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| 56–58 | n_LA 2·조기 호출 당겨 씀·FLIP_TH 끔 (M4 :275, :262, :287) | `m4.py`, `core.py:455-503` | 시험 묶음 | 일치 |
| 59 | 경계 직후 W 2·γ 1.0 등 | 없음 | §73 D5 | SCOPED S9 |
| 60 | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (prereg_labeler :11-12) | `sim/labeler.select_rule:131-142` | 로컬 적격 0.90 정확히 통과·0.8999 → None, 판별력 차 0.02 → plan(단순), 0.0201 → time0.66 (E3) | 일치 |
| 61–62 | 폐루프 RD 재표집 = layout 짝, 주 RD = Score (EVAL :182-184) | `closed.py`, `rd.py` | 파드 `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 2` → `RD_DONE`, `meta.bootstrap` 단위 "(kind, layout seed) … paired" | 일치 |
| 63 | H1/H2/H3 판정 (EVAL :186-191) | 없음 | §71 보충 | SCOPED S1 |
| 64–65 | M4b 2,000회, E-M4-lat 비례 STALE_MAX | `m4b/*` / 없음 | §72 예외 / §74 보충 | 일치 / SCOPED S11 |
| 66–67 | H = 1 창·`lead_max` 유한한 양수 (§75, §76 N4) | `m4.py:106-113`, `closed.py:160-166` | 시험 묶음; 파드 `--m4-lead-max nan` → "refused before any worker"(가드 14) | 일치 |
| 68 | E0 판정 4 (E :183, :197) | `analysis/latency.py` | 시험 묶음 | 일치 |
| 69 | E-M4 판정 7 | 다스텝 DecCall 없음 | §75 보충 (2) | SCOPED S12 |
| 70 | FROZEN = 송신 시각 기준 (M4 :150) | `m4.py:228` | §77 N3 | 정본 기록 |
| 71, 93 | 카나리 표류 → J5 끔, 재보정 뒤 재사용, 다음 날 깨끗한 카나리로는 안 켜짐 (E :139, :347, §77 N6, §79 D3) | `closed.j5_after_canary:169-185`, `canary.latest_canary:149-165` | **파드(실제 CLI 카나리 + 실제 함수)**: 전날 파일의 답을 모두 바꿈 → 오늘 카나리 `drift_suspect` true; 보정 `utc` 오늘 → (0.1, None) 켜짐, 전날 → (None, "J5 off: canary … drift suspect, calibration … fitted … before it") 꺼짐; 표류를 9/24 파일로 옮기고 오늘 깨끗한 카나리 → `last_drift` = 9/24 유지, 보정 9/23 → 여전히 꺼짐, 9/25 → 켜짐; α None → None | 일치(N11) |
| 72–76 | 응답 모델 필드·재시도 기록, E0.5 정답, `fine_dir`, Astra 카나리 | `models`, `common` | §77 N4·N5, §67 보충; 파드 Astra 행 `canary_id` "none" 4/4 | 일치 / SCOPED S13·S6 |
| 77–79 | (b) 범주 줄·런타임 값·경계 틱 호출 = 방금 끝난 스텝 (M4 :232, §77, §79 N1) | `core.b_line`, `core.act:429-515` | 행 54의 파드 판; 시험 묶음(`test_r7c13_boundary_line.py`) | 일치 |
| **80–84** | **학습 자료 값·학습 항목 상태·C5' none·ser-A-min-2·옛 체크포인트 거부 (§77 (iv), §77 보충 (1))** | `deccall_snap.py:31-75,78-105`, `stagea_data.build_items:160-190`, `serialize.with_last_step:12-15` | 로컬: 단계 A 항목 텍스트마다 `last_step:` 줄, 첫 스냅샷 none(D1), 출처는 `oracle` 없는 줄만 받음 35/35(D2), CAL 줄 거부(D3), 모르는 범주 거부·범주 집합 5개(D4), R2 `verify.prev_step` → T1 위반 CONTRADICT·T2 DEVIATE·단계 바뀜 OK·혼합 OR = T2(D5), labels_v2 출처 경계(D6); **파드 실제 풀**: `load_pool(labels_v2)` 6,000항목(1,200 스냅샷 × 5질문), 목표 1개씩, `last_step` {OK 5,775, none 220, CONTRADICT 5}; **정본 §77 보충 수치 재계산**: R2 DEV 결정 스냅샷 **1,081** 중 DEVIATE **21**·CONTRADICT **0**, POOL 결정 스냅샷 1,200 중 CONTRADICT **1** = 정본 그대로 | 일치 |
| 86–88 | 결정 호출 행 `probs`·blob·`last_step`, Astra 원응답, 결정 이미지는 해시만 (E :125, §28 A6, §77 D4) | `core.py`, `reqhash.request_body` | 행 6 | 일치 / 정본 기록 |
| 90 | FLIP_TH = 성공 실행 flip_score의 1−α 분위, 질문별 (M4 :287, §79 D1) | `e05.flip_th_conformal:271-281` | 시험 묶음 | 일치 |
| 91–92 | 같은 시각 뒤집힘 성공·섭동, 층별 A0 대비 flip (§2A.4, §27) | `e05.py` | 시험 묶음 | 일치 |
| 94 | E0 판정 4 집계 (§77 N7) | `latency.step_votes:93`, `judgment4:108` | 시험 묶음 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (a)–(e)·재개·evalck·판정 스크립트 입력 검사·고정본 (`prereg_se2e.md` §3·§4, §77 보충 2, §80 N1) | `tools/se2e/se2e_verdict.py` | **파드: 9a0ae52 사본의 판정 스크립트를 실제 S-E2E 로그(읽기 전용)에 다시 돌림** → rc 0, 키 125개가 기록 `verdict_v2.json`과 **차이 0**, 두 시드 (a)(b)(c)(e) pass; 파드 사본 `ckpt/se2e/prereg_se2e.md` sha256 `29191168…` = 9a0ae52 블롭 | 일치 |
| 98 | 라벨 복원 기준(비트 동일, §78 (1)) | `sim/labeler.py:177-221,313`, `stagea_data.replay_bit_identical:49-53` | 로컬 8경우(0·0.0 참; 1e-12·None·필드 없음·NaN·False·"0" 거짓, D7) | 일치(쓰는 쪽 NaN N2) |
| 99 | 에피소드마다 PhysX 장면 재생성, 모든 호출자 기본 (§78 결정) | `sim/scene.py:418-425,529-532,621-633` | 코드: `hard_reset=True` 기본, `make_env` 호출자(cli_label·cli_pool·datagen·m4b·perception·aiworker·determinism·run_dev) 모두 인자 없음; **파드 Isaac 한 워커 C5 → C5'(DEV 12, 모의 선택기)**: 행동 **1,877개 비트 동일**(첫 차이 없음), 호출 56개·Astra 2개 같은 수 | 일치(행렬은 S16) |
| 100, 118, 132 | 라벨 신뢰 = 재생 비트 동일, 필드 없음·null·NaN 행 제외, 뺀 수와 질문 범위 기록 (§78 (1), §80 D1, §81 N3) | `eval/common.load_truth:378-412` | **파드 실제 `e05 --split pool --seeds 2002,2009,2000 --truth outcome:plan`** → rc 0, `meta.truth_label_trust` = {plan, kept **133**, excluded **17**, questions 5개}, git `9a0ae523`, prereg OK | 일치 |
| 101 | R2_TRAIN은 하드 리셋 빌드, 옛 녹화 처리 보류 (§78 (2)(3)) | 파드 실행(읽기만) | 도는 `datagen.gen gen --out r2/train --seeds 10000-10599 --confirm-train` Isaac 워커(GPU 0·1) | 일치 / SCOPED S17 |
| 102, 120 | 빈 입력·0편 선택 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `eval/common.load_episodes:340-369`, `sim/determinism.py:194-201` | 파드 `determinism fresh --seed 1000`·`history --seeds 3,549` rc 1·폴더 없음(가드 19·20), `canary build-set --seeds 500-502` → "no episode selected" rc 1(가드 22) | 일치(e05 폴더 N10) |
| 103 | Isaac 워커 `OMP_WAIT_POLICY=PASSIVE` (§79) | `closed.worker_cmd:188-199` | 코드 읽기; 내 Isaac 워커가 이 명령으로 돌아 `R6_WORKER_DONE`; `--isaac-gpu 3` rc 1(가드 12) | 일치 |
| 104 | e05 qid 등록부 기본 = `<out>` (§79) | `e05.py:680` | 시험 묶음 | 일치 |
| 106–113 | S-E2E 진단 D1–D3·종합 (`prereg_se2e_diag.md` §1–§5) | 파드 고정 사본 | **파드 로그 재적용**: D1 step 0 `dec` = A step 4686 기록과 차 2.8e-8(< 1e-3), step 1200 `dec` 0.73753 > 0.64388 → "이 lr에서 계산 한계 아님"; D2 step 1000 학습 0.8853·검증 0.5600 → "불확정" = 문서 `:8-9`; D3는 15회차 재계산 그대로(다시 하지 않음) | 일치(종합 칸 갱신은 D-1) |
| **114** | **§7.1 설정: 기반에서 새로, 네 판 2,000스텝·묶음 8·lr 1e-4/1e-4·워밍업 3 % + 코사인·시드 0, 같은 검증 300(150/0), 500마다 평가, 부분집합 1,000(=D2)·25 %·50 %(출처 비율 같음, 포함 관계)·100 %, 학습 부분집합 평가(1,000 전부 / 9,371 안 층화 1,000), GPU 배정, 코드 블롭** | 파드 `code_se2e_diag`(판마다 `CODE_HASHES.txt`), `logs/se2e_scale/scale_run.sh`, 커밋된 `stageb_train.py` | **파드 로그 `config`·`diag_config`**: 네 판 `max_steps` 2000·batch 8·lr 1e-4·lr_heads 1e-4·`lr_schedule` cosine·`warmup_steps` 0(= 기본 3 %: 스텝 1 lr 3.33e-6 = 1e-4/30, 스텝 60 = 1e-4)·seed 0·`val_per_kind` 150·`val_seed` 0·`eval_every` 500·`init_weights`·`resume` 빈 값; N 1,000 = RB1 500·RB2 500·`train_keys_sha` `fb0b5036dcb9`(D2와 같음), 9,371 = 6,070·3,301(`caeff1f56b1c`), 18,742 = 12,140·6,602(`a53ed9e283be`), 37,484 = 부분집합 없음; 학습 부분집합 평가 n 1,000(1,000·9,371 판), 나머지 없음; 드라이버 GPU 2: 1,000(12:36:17–13:22:54Z) → 18,742(–13:59:55Z), GPU 3: 9,371(–13:23:24Z) → 37,484(–14:00:23Z), 모두 rc 0; `CODE_HASHES` `stageb_data` `be1e6214…`·`stageb_model` `5f3eba50…` = S-E2E 블롭, `stageb_train` `11e11795…`; 포함 관계·출처 비율은 파드 시험 `test_train_fraction_keeps_the_source_mix_is_nested_and_order_free` 통과; §7 파일 고정 12:33:46Z < 시작 12:36:17Z(N8) | 일치 |
| **133** | **§7.2 주 지표 = step 2000 검증 dec_acc·dec, 네 점 최소제곱 acc = a + b·log10 N, 확인 ⇔ b ≥ 0.05 ∧ acc100 − acc25 ≥ 0.03, 포화 ⇔ acc100 − acc50 < 0.01, 외삽 N\* = 37,484·10^(0.05/b)** | `logs/se2e_scale/scale_fit.py`(저장소 밖) → 문서 `se2e_diag.md:139-165` | **파드 로그에서 독립 계산(`scale17.py`)**: acc@2000 = 0.552222 / 0.682222 / 0.685556 / 0.683333, dec = 5.34203 / 0.79566 / 0.76804 / 0.77350; 적합 a **0.2944**·b **0.0901**(NLL a 14.276·b −3.124); Δ25 = **+0.00111**, Δ50 = **−0.00222** → 확인 거짓·포화 참 → "레버 약함(같은 스텝 기준) + 50→100 % 포화" = 문서; N\* = **134,460**(문서 "≈ 134,000"); 9k–37k 세 점 기울기 0.0018(문서 "b는 N = 1,000 한 점이 만든 것" 맞음); 표 8.1의 20칸 중 19칸 일치, 37,484 NLL 0.774 ↔ 0.773(N6) | 일치(규칙 문구 N5, 반올림 N6) |
| **134** | **§7.3 D2 해소: N = 1,000 판 step 2000 학습 부분집합·검증에 3절 규칙(≥ 0.95 ∧ ≤ 0.75 → 학습 가능·간극; < 0.85 → 못 맞춤; 그 밖 불확정), 스케줄 다름을 적을 것** | 문서 `se2e_diag.md:166-169` | 파드 로그: 학습 부분집합 1.000(NLL 3.5e-5)·검증 0.5522 → "학습 가능·간극" = 문서 `:167`; 학습 부분집합 곡선 0.199 → 0.607 → 0.944 → 0.999 → 1.000(문서 `:157`), 9,371 판 0.182 → 0.525 → 0.594 → 0.679 → 0.706(NLL 0.7063) = 문서; 스케줄 차이 문장 `:168` 있음 | 일치 |
| **135** | **§7.4 처리량: GPU 사용률(30 s)·스텝 시간 보고** | 문서 `se2e_diag.md:176-180` | 파드: 스텝 시간 중앙값 네 판 모두 **1.00 s**, 판 길이 46.6·47.1·37.0·37.0분(문서 "약 37–47분"); GPU 사용률 재실행 69.1 %/81 %·68.4 %/78 %(창 시작 약 12:37–12:38Z일 때, N7); S-E2E 본 판 45.6 %·46.8 %(`se2e_train.md:45`) = 문서 "약 46 %" | 일치(N7) |
| **136** | **§5 종합 읽기 표: 칸은 D1·D2·D3 판정으로 정함 (`prereg_se2e_diag.md:45-54`), §7 목적 "D2를 원래 규칙으로 해소" (`:62`)** | 문서 `se2e_diag.md:12`, `:125` | D2 해소(행 134) 뒤 칸 = `:49` "아님 × 학습 가능·간극 × 모호성 아님 → 데이터 규모 한계(데이터 늘리기)"인데 문서 종합 줄은 "D2 불확정 → 판정 불가 / 규칙상 확정 레버 없음" 그대로, 표시 없음 | **DOC D-1** |
| **121** | **E-TC 옵션 끔 = 기준 표본, 기본 경로·프롬프트 해시 파일 무수정 (`prereg_se2e_temporal.md` §7, §8)** | `se2e_temporal.load_se2e_t:123-130`, `stageb_train._load_data` | 코드 불변(f91ad52 = 9a0ae52); 파드 E-TC 판 폴더 `CODE_HASHES.txt`의 `stageb_data` `be1e6214…`·`stageb_model` `5f3eba50…`·`prefix_share` `c231a0de…`·`se2e_data` `a08f7127…` = S-E2E·등록 블롭; 파드 시험 `test_stageb_train_defaults_unchanged_and_variant_config` 통과 | 일치 |
| **122** | **V = video2: 카메라마다 [t−0.3 s, t], 10 Hz에서 k−3(0으로 자름), 시각 토큰 수 불변 (§2)** | `se2e_temporal.prev_index:46-47`, `se2e_temporal_model.VideoEncoder` | 로컬 `prev_index` k 0·1·2·3·4·100 → 0·0·0·0·1·97, `DELTA_S` 0.3; 파드 시험 `test_se2e_temporal_qwen.py`(처리기 비트 동일·토큰 수) 통과 | 일치 |
| **123** | **M = 움직임 줄: 인과 후방 차분, 팔 3분위 still < 0.2179 ≤ slow < 0.6070 ≤ fast, 그리퍼 0.85 분위 0.1755 초과면 opening/closing (§3)** | `se2e_temporal.backward_velocity:50-53`·`motion_line:86-92` | 로컬 후방 차분 [0, 10, 20, 30](k+1을 읽지 않음), 경계 0.2178999 still·0.2179 slow·0.6069999 slow·0.6070 fast, 그리퍼 ±0.1755 = still, ±0.17550001 → opening/closing (etc17 7/7); 파드 E-TC 판이 쓰는 `motion_bins.json` sha `e164719a92d5…` = 등록 | 일치 |
| **124** | **드롭아웃 p = 0.3, 난수 (시드, 스텝) 따로, 데이터 순서 난수 불변 (§3)** | `se2e_temporal.motion_dropout:95-109` | 로컬 400스텝 × 30표본 비율 0.29992, 전역 `random` 상태 불변, 같은 (시드, 스텝) 같음·다른 시드 다름, p = 0 항등 | 일치 |
| **125** | **새 판 표지·옵션 판 `prompt_config`에 layout·motion·옵션 파일 해시 → 기본 체크포인트와 섞이지 않음 (§7)** | `stageb_train.prompt_config_t:83-96`, `fused_model.check_prompt:319-344` | 코드 불변; 파드 시험 묶음 통과 | 일치(오프라인 `predict` 대조 N1) |
| **126** | **지표·층: 검증 300 × 3질문 = 900항목, 전이 층 정의 (§4)** | `se2e_temporal.transition_flags:172-178`, `temporal_verdict.metrics:48-60` | 파드 `transition_val.json` sha `ee7b4fdb7962…` = 등록·E-TC 판 `CODE_HASHES`에 기록; (single, none) 예측 900항목·`val_keys_sha` `e22f6d8ef7fc`(N14); 로컬 구성 판정(행 127)이 전이 층·전체를 따로 셈 | 일치 |
| **127** | **채택 규칙: 전체 주효과 ≥ +0.02 ∧ 전이 주효과 ≥ −0.01 ∧ FULL p95 증가 ≤ 10 %(V: (v2, none)/(s, none), M: (s, motion)/(s, none)), CMP_EPS 1e-12 (§6)** | `tools/se2e/temporal_verdict.py:24-34,119-128` | 로컬 구성 입력(300스냅샷, 전이 200 = 600항목; `verdict17.py` 6/6): +18/900(0.020000000000000018)·−6/600·p95 0.33/0.30(+0.10000000000000009) → V 채택; +17/900 → 거짓; 전이 −7/600 → 거짓; p95 0.3300001/0.30 → 거짓; M 경계 → M 채택(V 지연은 (v2, motion) 50 s여도 무관), (s, motion) 0.331 → 거짓 | 일치(입력 검사 N3) |
| **128** | **판정 스크립트·등록 코드 해시, 등록은 학습 전, 실행 순서 (§6, §7)** | 파드 `ckpt/se2e_temporal/*/CODE_HASHES.txt`, `logs/se2e_temporal/driver_*.out` | 두 판 `CODE_HASHES` = 등록 값(`stageb_train` `a79ed547…`, `se2e_temporal` `d5babfb8…`, `se2e_temporal_model` `28265152…`, `tools/se2e_temporal.py` `285a7320…`, `temporal_latency` `a0dcafcf…`, `temporal_verdict` `992d3e20…`) = 9a0ae52 블롭(`stageb_train` 제외 — §81 N2 차이, 16회차 N4); 시작 14:00:54Z(GPU 3 video2_motion)·14:01:56Z(GPU 2 video2_none) = 규모 판 끝(14:00:23Z) 뒤 = §7 순서; (single, none) = `se2e_scale/37484` `predict` rc 0 | 일치 / SCOPED S18 |
| 129 | 지연 측정 (§5) | `tools/se2e/temporal_latency.py:38-112` | 코드 불변(16회차 읽기 확인), 실행 전 | 일치(실행은 S18) |
| 130 | §81 N2 재개 검사 키 | `stageb_train.py:267-293` | 파드 시험 `test_r7c15_resume_keys.py` 통과(코드 불변) | 일치 |
| 131 | §81 N10 라벨 쓰기: 수가 없는 결과가 하나라도 있으면 null | `cli_label.replay_max:37-43` | 시험 묶음(`test_r7c15_label_write.py`) | 일치(N2) |
| **137** | **Astra 호출 주기 = 하트비트(직전 응답 + N, N = 5 s) + 단계 경계 + 사건, in-flight 1, 15 s 무응답 → 기록·재송신, ack는 epoch 불변·patch/replace는 +1, 모델 gpt-6-astra·effort low (§45, §1)** | `runtime/astra_hb.py:33,81-140`, `core.py:242-276,395-426,461-477` | 로컬 스케줄러: K2 첫 호출 = N, 날아가는 중엔 없음, 다음 = 응답 + N(C1), 15 s 정확히 = 유지·초과 = 버림(C2), 초과 뒤 즉시 재송신(C3), 사건이 당김(C4), K0 사건만(C5), K1 경계 → sub 1회·K0는 경계 무시(C6), K3 max(송신 + 1 s, 응답)(C7), K4 예산(C8), `pause_until`(C9), 모델·effort(C10), 닫힌 선택 파싱(C11); **가짜 세계 런타임**: ack만 → epoch 0 그대로(C12), [ack, patch, replace] → epoch 1·2·3·4 차례로(C13), N = 2 s 간격 = 직전 응답 + 2.0 s(C14), 겹침 없음(C15), Astra 행 effort·600·원응답·요청 blob(C16); 파드 Isaac 판 Astra 2회/18.8 s(5 s + 3 s 모의 지연) | 일치(시간 초과 뒤 재송신 모양 N4, T_fail 정지 S5) |
| **138** | **LeRobot v2.1 내보내기 = ROBOTIS 형식(§63), 30 Hz·머리 + 활성 손목 원본 해상도·관절 행동·LeRobot 적재 확인(§66)** | `datagen/lerobot_export.py:28-80,134-185,192-251` | **파드 끝까지**: R2 DEV 3편(standard/mug_tray ep1, dr/mug_marker ep2, standard/bottle_tray ep0) `export` → 3편·922프레임, `verify --src` → 오류 0·PSNR 최소 39.0 dB·**lerobot 0.3.3 `LeRobotDataset`** 922프레임·3편·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·action0 같음; `lr17.py` 30/30: `codebase_version` v2.1 = ROBOTIS `Task_0001…/meta/info.json`과 같음, data/video 경로 틀 같음, 표준 열 5개, `observation.state` = [q, 폭] 비트 같음, `action` = npz 비트 같음, `timestamp` = k/30·`sim_time` 차 ≤ 3.4 ms, `decision` 깃발 = 원본, `next.done` 마지막 한 칸 | 일치 |
| **139** | **R2 DEV 구조 검사(§66, 완료 정의 1)** | `datagen/validate.py:38-` | 파드 `/data/harvest/r2/dev/*/*/P0` 전 편 `validate_episode`: **36/36 오류 없음**(standard·dr × mug_tray·mug_marker·bottle_tray 각 6) | 일치 |

### 5.1 16회차 표(`r7_cycle16.md` §5)와의 차이
- 행 106–113: 종합 칸이 8.3 뒤 갱신되지 않은 것을 새 행 136(D-1)으로 분리.
- 새 행 133–135: 데이터 규모 곡선 결과(§7.2–§7.4)를 파드 로그에서 다시 계산.
- 행 114: 16회차에는 "구현 커밋됨"까지였고, 이번에 네 판의 실제 인자·부분집합 구성·시각·코드 블롭을 로그로 확인.
- 행 13·71·80–84·99·128: 카나리 여러 날 끝까지, 실제 풀 단계 A 자료 경로와 §77 보충 수치, 새 시드 DEV 12, E-TC 실행 해시로 근거 교체.
- 새 행 137–139: Astra 주기(§45), LeRobot 계약(§63·§66), R2 DEV 구조 검사를 표 행으로 올림.

## 6. 확인한 것 (근거)

### 6.1 데이터 규모 곡선 재계산(과제 1 일부, 파드 읽기 전용)
- 입력: `/data/harvest/ckpt/se2e_scale/{1000,9371,18742,37484}/log.jsonl`(2,012·2,012·2,007·2,006줄), `CODE_HASHES.txt`, `/data/harvest/logs/se2e_scale/{driver_2.out, driver_3.out, gpumon.csv, scale_run.sh, gpu_window.py}`. 내 스크립트 `scale17.py`·`gpu17.py`(출력은 내 폴더).
- 결과: 행 114·133–135. 문서 8.1 표 20칸 중 19칸, 8.1 학습 부분집합 곡선 10값, 8.2 적합·Δ·N\*, 8.3 D2, 8.5 스텝 시간·판 길이가 로그와 같다(N6·N7만 차이).
- §7 고정 시각: 로컬 작업 트리 `docs/stage3/prereg_se2e_diag.md` 수정 시각 12:33:46Z(15회차가 13:25Z에 본 값과 같음 = 그 뒤 수정 없음), 크기 11,465바이트 = 커밋 9cee78b 블롭; 드라이버 시작 12:36:17Z; 첫 평가 기록(step 500) 약 12:48Z; 커밋 12:57:49Z(N8).
- 진단 D1·D2 원판도 같은 방식으로 재적용(`diag17.py`, 행 106–113).

### 6.2 덜 본 영역 (과제 2)
- **Astra 클라이언트·하트비트(§45·§46)**: 행 137, N4, N15. `detect_phrase`는 대역 표(N15), T_fail 뒤 정지는 S5.
- **단계 A 학습 자료 경로 대 labels_v2·§77 `last_step`**: 행 80–84. 실제 풀에서 `load_pool(labels_v2_factory)`가 6,000항목을 만들고, 모든 항목 프롬프트가 `last_step:` 줄로 끝나며, 정본 §77 보충의 범주 수(1,081·21·0, POOL CONTRADICT 1)가 지금 코드로 그대로 나온다.
- **LeRobot 내보내기 대 §63·§66**: 행 138(실제 lerobot 0.3.3 적재까지).
- **카나리 도구 끝까지**: 행 13·71·85. 세트 만들기(DEV 가드) → 실행 → 같은 날 재실행 거부·`--force` → 전날 기준일 → 판본 바뀜 → 표류 → J5 게이트(실제 CLI 출력 + 실제 `j5_after_canary`) → 다음 날 깨끗한 카나리 → 폐루프 행의 `canary_id` = 최신 카나리(`cn20260925_mock_6e0e52` 56/56). 틈 N11.

### 6.3 완료 정의 1–5 (직접 돌린 것, 과제 4)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + 코드 사본으로 R2 DEV 전 편 `validate_episode` **36/36**; LeRobot 시험 **6 passed**; 내보내기·되읽기·lerobot 적재 끝까지(행 138). |
| 2 모델 | 충족(CPU) | GPU 없음(0·1 = R2_TRAIN·내 Isaac, 2·3 = E-TC 학습) → CUDA 시험·GPU 재적재 건너뜀. 파드 CPU 스모크(N13), CPU 묶음의 `test_stageb_torch.py`·`test_r7c15_resume_keys.py`·`test_se2e_temporal_qwen.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 12 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c17`, 14:30:26–14:34:41 UTC, `IR_INST` `r7c17_standard`): `CLOSED_DONE` C5·C5' 성공 1.0, 18.77 s, 호출·Astra 행 필드·blob 확인(행 6), `meta.bootstrap` 10000, `meta.prereg` OK, git `9a0ae523`, `code_sha` `9242f67e59a09ee4`, 하드 리셋 빌드(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 14:27–14:28 UTC): `e05 --data jsel_dev/P0,P2 --split dev --episodes 3` → `E05_DONE`, `rd --variants standard=jsel_dev,random=gen_dev/random/P0 --episodes 2` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P1 --heldout-split dev --episodes 5` → `CALIB_DONE`, `e05 --split pool --truth outcome:plan`(행 100) → rc 0. 모두 prereg OK·git `9a0ae523`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·카나리·시드·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`j5_*`·`truth_label_trust`(+ `questions`); 규모 판·E-TC 판은 폴더마다 `CODE_HASHES.txt`; 정리 뒤 흔적 없음(§6.7). |

### 6.4 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`, 14:27:20–14:27:27 UTC)
- `e05 --split cal|test|test_p5`(1–3), `calib --fit-split cal`(4), `calib --heldout-split test`(5), `rd --split test`(6), `closed --split test --seeds 1149`(7), `--split cal --seeds 500`(8), `--split test_p5 --seeds 1300`(9) → "refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 29,30`(10)·`--split pool --seeds 2120`(11) → "not in split … (refused, never opened)". `--isaac-gpu 3`(12) → "GPU 2 never renders" 계열 거부; `--conditions C9`(13)·`--m4-lead-max nan`(14) → "refused before any worker". `HARVEST_ALLOW_SPLIT=dev closed --split cal`(15), `HARVEST_ALLOW_SPLIT=test e05 --split cal`(16) 거부. `gen gen --seeds 10007-10008`(확인 인자 없음, 17), `gen gen --seeds 500 --confirm-train`(18), `determinism fresh --seed 1000`(19), `determinism history --seeds 3,549`(20) 거부. `e05 --data pool --split dev`(21) → "not in split dev … never opened", `canary build-set --seeds 500-502`(22) → "no episode selected". **22건 모두 rc 1**; 출력 폴더는 21번(e05)의 빈 폴더 하나(N10), 나머지 0.

### 6.5 A. 테스트
- 로컬(`…\r7c17\repo` = 9a0ae52 archive, Git Bash, `python -m pytest -q -rs -p no:cacheprovider -o addopts="" --basetemp=D:/tools/scratch_qdd/r7c17/pt`, TMP = `…\r7c17\tmp`): EXIT 0, **1006 passed · 15 skipped**(139.9 s; N12).
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid 등록부 = scratch, 14:23–14:25:14 UTC): **1122 passed, 4 skipped**, EXIT 0.
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`, HF_HOME = scratch): **6 passed**.

### 6.6 같은 사실 grep (과제 3, 추적 파일, `third_party/` 제외, §72–§81 + f91ad52 뒤 새 문서)
- 새 문서: `CLAUDE.md:27`(user-log 73 — 앞 줄 `:26` [사용자] 1시간 규칙은 그대로 두고 "위 1시간 주기를 4시간으로 바꾼다"로 덮음, 맞음), `CLAUDE.md:33`(user-log 72 — 보고 KST, 기록 UTC; 저장소 기록은 UTC 그대로 — 이 보고서도 UTC), `user-log.md` 72–74(원문), `direction-log.md` 16회차 행, `draft-log.md:457-458`, `handoff.md:111`(N9), `r7_cycle16.md`(내 로컬·파드 시험 수·C5→C5' 절차·가드 모양이 16회차 기록과 같은 형태로 재현됨), `se2e_diag.md` 8절(행 133–136, D-1, N5–N7).
- `se2e_diag.md` 8절의 수·주장 대 다른 문서: S-E2E 본 판 GPU 약 46 % = `se2e_train.md:45`(45.6·46.8 %), 0.722 = `se2e_train.md:37`; D2 "불확정"을 현재 상태로 쓰는 곳은 `se2e_diag.md:12`·`:125`(D-1)와 시각이 적힌 기록(`draft-log.md:454`, 논문 NOTE N16)뿐.
- §78 사실(선행 실행 ≠ 비트 동일)·§80 D1·§81 N2·N3·N10·D-2(597행·13시드·20편) 문장: 16회차 이후 바뀐 파일(위 목록)에 새로 나온 곳 없음; 기존 표시 위치(`pool.md:32`·`:33`·`:57`, `e_m4b_meas.md:19`, `r2_datagen.md:99`, `draft-log.md:412`, `cli_pool.py:204-206`)는 9a0ae52에 그대로.
- §77 보충 수치(R2 DEV 1,081·DEVIATE 21·CONTRADICT 0, POOL CONTRADICT 1), §80·§81의 886·805·133/17: 파드에서 다시 계산해 같음(행 80–84·100).
- 정본 범위: `handoff.md:3`·`:5` = §1~§81(맞음, 정본 변경 없음).

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(시작·끝 `git status` 깨끗). 로컬 C:: 이 검토의 산출물 없음(하네스 작업 출력 파일만), 공용 `scratch_qdd` 폴더에 새 파일 0.
- 파드 정리(`clean17.sh`, 경로를 하나씩 적어 둔 스크립트, grep·패턴 없음, 14:36:28 UTC): `tmp/r7c17`(391 MB), 내 Isaac 판이 만든 `tmp/carb.2Ugzer`(14:30:28Z)·`tmp/tmpmushajeq`(14:30:45Z)·`cache/pyc_r6/data/harvest/tmp/tmpmushajeq`·`cache/pyc_r6/data/harvest/tmp/r7c17`, `ir/kitcache/cyclo-r7c17_standard`(208 MB). 판별: 시작 전·Isaac 전후에 저장해 둔 `tmp`·`pyc_r6`·`kitcache`·`cache`·`hf/datasets/parquet` 목록의 차이(새 항목은 이것뿐), 생성 시각이 내 Isaac 창 안, `/proc/*/fd` 전수에서 여는 프로세스 없음. `/data/harvest/home/.nvidia-omniverse/logs/*.log`는 모든 Isaac 판이 함께 쓰는 로그라 두었다. `/data` 밖 새 파일 0(`find / -xdev -newer`, `/tmp` 포함). 끝에 내 프로세스 0(확인 명령의 `grep -c r7c17` = 2는 그 명령 자신과 grep의 자기 매칭).
- 절차 사고 없음(규칙 줄의 heredoc 초안은 올리기 전에 지움).

## 7. 다음 순회 전에 할 일 (제안)
1. **D-1**: `se2e_diag.md:12`·`:125`에 8.3 뒤 5절 칸 갱신 표시(문장 예는 §2 D-1). 논문·handoff에서 이 진단을 인용할 때도 같은 문장. (문서만 — 코드 무변경이면 다음 순회는 연속 무결 0에서 다시 셈.)
2. N4: E-M8c 전에 시간 초과된 Astra 호출을 같은 종류(T_sub면 경계 질문)로 재송신하게 고치거나 정본에 규칙을 적기.
3. N11: 카나리 `--force` 같은 날 재실행이 표류 파일을 지우지 않게(새 이름 또는 거부).
4. N1·N3·N14: E-TC 결과 문서에 칸별 `prompt_config`·`n_val_snapshots`·`val_keys_sha`와 (single, none) 재사용 조건 대조(이번에 확인한 값)를 적기.
5. N5·N6·N7: `se2e_diag.md` 8절에 규칙 문구 해석 한 줄, 37,484 NLL 0.773, GPU 창 시각.
6. N9·N10: handoff 머리 시각, `e05`의 `--out` 생성 순서(선택).
7. (범위 밖, 9a0ae52 뒤 커밋) `docs/user-log.md` 줄 끝 `\r\r\n` 복구 여부 확인, 정본 §82(하트비트 강등)와 N4의 관계를 18회차에서 대조.
