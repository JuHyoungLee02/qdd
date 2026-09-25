# R7 객관 검증 순회 — 30회차 (cycle 30, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle29.md`의 표·결론을 근거로 쓰지 않고 29회차 정정 주장마다 원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드는 **21–29회차와 다른 새 값**. 작성 2026-09-25 21:49 UTC(`date -u` 21:49:11Z, 로컬 정리 직후; 로컬 사본 풀기 21:32:14Z, 파드 첫 명령 21:33:37Z, 파드 정리 끝 21:45:38Z, 보고서 쓰기 시작 21:46Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`272432e`**(`272432eb211f6fdc1efb883bc692cea58ef65637`, 커밋 시각 2026-09-25 21:30:23 UTC, "R7 cycle 29 baseline FAIL (DOC 3) — handoff §0 'in-progress work' with UTC checks (status only there), book 01 table D status column unified, book 04 seed counts per kind, P69 cycles, canon N88 sim-seconds note, ma1 evidence"). `0cc45ae..272432e` = 커밋 1개, 10파일(문서만: 책 01·02·04·06, 정본 `00-interfaces.md`, draft-log, handoff, direction-log, 결과 `ma1.md`, 새 `r7_cycle29.md`), **코드·시험 변경 0**(`check30` H1). 검토 내내 HEAD = 272432e(뒤 커밋 없음), 작업 트리 깨끗함(이 보고서만 추가).
- **범위 나눔(29회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책 `docs/book/`. **실험 코드 절**(따로 판정) = 272432e 이전에 커밋됐으나 아직 검토하지 않은 실험 쪽 변경 — **없음**(272432e의 실험 쪽 파일 변경 0; `ma1.md` 근거 표시는 29회차처럼 기준선 결과 문서로 봤다). E-CAM3·E-MA3 결과는 272432e까지 커밋되지 않아(`git ls-tree 272432e docs/stage3/results/`에 cam3·ma3 0) **범위 밖** — 두 실험의 예측·평가 파일은 **열지 않았다**(폴더·파일 이름·시각과 GPU 감시 CSV만).
- 사본: `git -c core.autocrlf=false archive 272432e`(tar 주석 = `272432eb211f…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c30\repo`에 풀었다(**591파일**, 텍스트 539파일 CR 0). 파드 사본 = 같은 tar(텍스트 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c30/code`(592파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `272432eb211f…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle29.md`, 정본 `00-interfaces.md` §1–§86 보충(뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(29회차 목록), 결합 설계 스펙 §12·§17, 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P69.
- 분류(29회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0의 줄은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약(값은 맞음), 추정 표시(≈·약·`2x`)가 있는 수치, 반올림 차이는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c30`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음; 29회차 스크립트는 읽기만 하고 새로 썼다). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c30`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c30_standard`, `--inst-prefix r7c30`; GPU 0·1의 R2_TRAIN 워커 5개는 건드리지 않음), GPU 2·3(E-CAM3·E-MA3 학습)에는 아무것도 올리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 21 |
| NOTE | 89 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — 검토할 새 실험 쪽 변경 없음, 코드 결함 0, DOC 0**(NOTE E-N19 그대로)

**기준선 코드는 29회차 대상(0cc45ae)·28회차 대상(47edadb)과 바이트가 같다**(272432e는 문서만). 회귀: 로컬 **1133 passed / 20 skipped**(Git Bash, 234.2 s), 파드 CPU **1280 passed / 4 skipped**(251.0 s), LeRobot 6 passed; 가드 **28건 + 실험 옵트인 4건 = 32건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–29회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 대조 12종**(통과해야 할 경계 4종 통과, 검출해야 할 8종 모두 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 완료; 새 시드 **DEV 24**에서 같은 Isaac 워커 C5 → C5' 행동 **1,745개 비트 동일**(첫 차이 없음, 시각열 동일). **29회차 정정 주장은 하나를 빼고 diff와 맞고 원자료로도 참이다**(§6.2): handoff 새 §0의 세 줄(R2_TRAIN 21:29 UTC: P0·P1 끝·P2 생성 중·생성 프로세스 15개·행 파일 12:19:47–12:20:26 UTC·파드 `ls` KST 표시; E-CAM3·E-MA3 21:02 UTC 학습 중), 책 04 종류별 시드 수(P0 19–41·P1 11–19·P2 10–20)와 확인 시각 줄, 02 P69 회차, 정본 §86 보충 "시뮬 초", `ma1.md` 근거 표시, R7 행 "1–29회차", handoff §2.8 29회차 줄·draft-log·direction-log·06 줄.

**DOC 1건(기준선)** — **D-1** 책 `01-experiments.md:56`이 새로 "상태 칸은 `끝`·`중단`·`[결과 전]`·`[예정]`만; 근거·참조는 결과 칸 괄호에"라고 적고 06 `:21`이 "01 표 D 상태 칸 통일(D-1·N107)"이라 기록했으나, 같은 표의 **`:60`·`:61`·`:62` 세 행 상태 칸에 여전히 결과 문서 링크가 있고 `:62`에는 "— 바뀐 결정: spec §4 F0 기본, §12 …"까지 들어 있다**(`check30` H7: 10행 중 3행이 네 값 중 하나와 정확히 같지 않음). 29회차 D-1과 같은 모양(규칙·기록은 '통일', 표 칸은 일부만)이다. **연속 무결 0 유지.**

---

## 1. DEFECT

없음. (272432e는 코드·시험을 바꾸지 않았다 — `git diff --name-status 0cc45ae 272432e`에 `harvest/`·`tools/`·`tests/` 경로 0, `check30` H1.)

## 2. DOC

- **D-1. `docs/book/01-experiments.md:56` 대 `:60`–`:62` — 표 D 상태 칸 '통일'이 세 행에서 안 됨(06 `:21` 기록과도 다름).** `:56`(272432e가 새로 넣은 줄): "(상태 칸은 `끝`·`중단`·`[결과 전]`·`[예정]`만; 근거·참조는 결과 칸 괄호에 — 2026-09-25 21:30 UTC, R7 29회차 D-1·N107)". 표 D 상태 칸(`check30` H7): `:60` Astra 모델 ID `끝 ([R/astra_model_id](…))`, `:61` Sol·Luna `끝 ([R/sol_luna_probe](…))`, `:62` E-Astra-motion `끝 ([R/astra_motion](…)) — 바뀐 결정: spec §4 F0 기본, §12 손목 필수·잡기 확인은 고유 감각·V1h 우선, §15·§16 폐기 문턱 6 s는 너무 짧음(p95 11–14 s), §11 부드러운 반영 유지`. 나머지 7행(`:63`–`:70`)만 정확히 네 값 중 하나다. 272432e diff는 `:63`–`:69`만 고쳤고 `:60`–`:62`는 손대지 않았다. 06 `:21` "01 표 D 상태 칸 통일(D-1·N107)"과 커밋 메시지 "book 01 table D status column unified"도 이 세 행에서 참이 아니다. (표 A·C의 상태 칸도 `끝 ([R/…])` 꼴이지만 `:56`의 규칙은 표 D에만 붙어 있어 거기엔 DOC로 보지 않는다 — N122.) **고칠 것**: `:60`·`:61`의 링크를 결과 칸 괄호로(예: "`gpt-6-astra`, low 첫 토큰 2.975 s(1회) ([R/astra_model_id](…))"), `:62`의 링크와 "바뀐 결정 …"을 결과 칸 끝으로 옮겨 상태 칸을 `끝`만 남긴다(칸 단위 수정, 쓴 뒤 칸 수 검사 — P68); 같은 커밋에 06 줄. 고친 뒤 표 D 상태 칸이 네 값과 **정확히 같은지** 기계적으로 확인한다(`check30.py` H7과 같은 방식).

(검토했지만 DOC로 올리지 않은 후보: ① handoff §0의 R7 줄에 확인 시각이 없다 — §0 머리 "각 줄에 확인 시각 UTC"와 어긋나지만 내용은 커밋으로만 바뀌는 값이고 272432e에서 참 → N116. ② handoff `:93` "**진행 중**(21:03 기준; …): 결과 라벨(T14…)"이 §0 밖의 진행 상태다 — 시각이 붙은 옛 기록 → N117. ③ 책 `04:36` "3 = vLLM·보조 VLM 서버"는 실제 GPU 3 사용(E-MA1b·E-MA3 학습)과 다르다 — 272432e 이전부터 있던 역할 서술 → N121.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 R2_TRAIN Isaac 워커 5개 진행 중(21:33Z, `gen gen --kinds P2 --seeds 10800-10999 --confirm-train`, dr 2·standard 3, GPU 0·1; P2 편 dr 137/200·standard 196–197/200; 읽기만); 확인 인자 없는 `--seeds 10000` 거부(가드 19). 폴더 행 병합은 아직(N94).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8.
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험.
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 272432e에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. 정본 §82 구현 및 §84·§86(+보충) 결합 설계 구현 — "R7 E2E 준비 기준점 뒤". 지금 코드: 파드 `closed --hb-mode k4`·`"K 4"` → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 24 Astra 4행), 흐름 호출 없음.
- S19. 정본 §83 런타임 적용(새 직렬화 판본) — DEV 24 결정 호출 요청 104/104 `motion:` 없음.
- S20. **E-CAM3·E-MA3 결과**: 시드 1 학습 끝(`logs/cam3/cam3_s1.out` 20:42:33–21:23:33Z, `logs/ma3/kv_s1.out` 20:45:14–21:23:02Z), 시드 2 학습 중(`se2e_cam3 train` 21:27:59Z·`se2e_kvcond train` 21:28:07Z 시작, `cam3_s2.out`·`kv_s2.out` 21:34:08Z 갱신) — 결과 커밋 없음, 예측·평가 파일(`predfull_*`·`chunk_*`·`reuse_check.out`·`verify_results.py`)은 열지 않았다(실험 절 7.2).
- S21. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3. (그대로) `stageb_train predict`·`evalck`의 `prompt_config` 비대조, `cli_label.replay_max` NaN 순서, 판정 스크립트 입력 검사 수준(책 P25).
- N4. (해소, 27회차와 같음).
- N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45. (그대로, 28·29회차 목록.) N10 재현: 가드 25(`e05 --data jsel_dev/P0 --split pool --seeds 2110` → "no episode selected")가 빈 `g25/`를 남김.
- N46. (그대로) `RESUME_KEYS`의 `a3d_root`.
- N47·N48. (해소.)
- N49–N53. (그대로.)
- N54. (해소.)
- N55. (해소) `04:61` 시드 수 종류별(D-2 해소), `01:69` 상태 칸 `[결과 전]`(29회차 D-1 해소). `01:12`·`01:20` 그대로.
- N56. (해소, 이력.)
- N57, N58. (그대로.)
- N66·N67. (해소.)
- N68–N70, N72, N84–N87. (해소, 29회차와 같음.)
- N71. (그대로) 정본 §85 보충이 §86 본문 뒤 — 책 03 `:70`이 밝힘.
- N73. (그대로) 정본 §66 `:563` "본 생성 계획(아직 실행 안 함)".
- N74. (그대로) 스펙 `:123`·`:130`·`:180`·`:185` "[→ §17]" 꼬리표 권함.
- N79. (그대로) 계획 PROBE 표의 자리표시와 `timeout_s 20.0`이 섞임.
- N88. (해소) 정본 `:778` §86 보충에 "탐침의 20 s는 시뮬 초이므로 실기에서는 벽시계로 다시 잰다 [2026-09-25 21:30 UTC, R7 29회차 N88]" — `harness.py:45` 주석 "sim s", `:539` `t - x["send_t"] > STREAM_TIMEOUT_S`(t = 시뮬 시각) ✓; 11.6/14.1 s·12–16 s는 결과 5절·0절 `:6`과 같음 ✓.
- N90. (그대로) 책 04 지도에 `se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3|ma3/`·파드 `code_cam3|ma3`·`ckpt/cam3|ma3`·`logs/cam3|ma3` 없음. 또 `04:49` "산출 위치는 R2_TRAIN 보고 뒤 확정 `[미검증]`" — 산출 위치 `/data/harvest/r2/train`은 `04:61`·handoff §0·`ma1.md:15`에 이미 적혀 있다.
- N91. (그대로) P68·P69가 다. 절 P67 뒤.
- N92. (해소.)
- N93. (해소) handoff §0에 E-CAM3·E-MA3 줄.
- N94. (그대로, 운영 위험) R2_TRAIN 폴더 행 파일 18개가 여전히 12:19:47–12:20:26Z 파일럿 병합(21:33Z `r2state30.sh`: 12:21Z 뒤 바뀐 행 파일 0, 로그 MERGE·CHECK 줄 0). handoff §0·책 `04:61`의 "생성 끝난 뒤 병합·검사 필수" ✓.
- N102. (해소) `04:61`의 "아직 돌지 않았다" 삭제, "병합 여부 등 진행 상태는 이 장에 적지 않는다(handoff 참조)".
- N103. (일부) 표시가 **29회차 줄 끝**(handoff `:134`)에 붙었다 — 고쳐야 할 28회차 줄(handoff `:133` "보고 2026-09-25 21:02 UTC")과 draft-log `:479`·direction-log `:75`의 "21:02"에는 표시가 없다(값은 파드 정리 끝 21:02:35Z, 보고서 머리 21:05 — `r7_cycle28.md` 머리 확인).
- N104. (해소) `02:55` P69 "(27·28·29회차; 26회차 정정이 꼬리표를 만듦 …)" — 27 D-1·28 D-1/D-2·29 D-1/D-3 모두 상태 표기 계열 ✓.
- N105. (해소) `01:38` "R7 객관 검증 1–29회차" — 29개 보고서의 판정 머리: PASS = 6·16·20·22, 나머지 FAIL(25–29는 기준선 FAIL) ✓.
- N106. (해소) `04:3` "21:07·21:30 UTC에 R2_TRAIN·탐침·E-MA1b 줄 재확인" — 적힌 내용은 21:33Z 파드와 맞다(재확인 행위 자체는 확인 불가).
- N107. (→ D-1) 표 D 칸 정리가 7/10행만.
- N108. (해소) `ma1.md:15` 끝에 "[근거 2026-09-25 21:30 UTC, R7 29회차 N108: 파드 `ls -l --time-style` 18파일 12:19:47–12:20:26 UTC(파드 표시는 KST), 시드 수 계수는 `r7_cycle29.md`]" — 값 ✓(파드 `/etc/localtime` → Asia/Seoul, 기본 `ls -l`은 "Sep 25 21:20", `TZ=UTC`면 12:20:23Z·12:20:26Z). 근거 명령 표기는 N120.
- N109–N115. (29회차 자체 기록 — 이번 회차는 N123–N127.)
- **N116.** handoff `:13` "**R7**: 29회차 기준선 FAIL(DOC 3) → 정정 뒤 30회차 예정. 연속 무결 0." — §0 머리 `:9` "각 줄에 확인 시각 UTC"와 달리 시각이 없다. 272432e에서 참이고 커밋으로만 바뀌는 값이라 NOTE; "(2026-09-25 21:30 UTC)"를 붙이거나 §2.8 마지막 줄 참조로 바꾼다.
- **N117.** handoff §0 머리 "이 절만 진행 상태를 적는다" 대 `:93` "**진행 중**(21:03 기준; R2·R6은 이후 완료 — §2.8): 결과 라벨(T14, GPU 0 장시간)" — 옛(09-24) 시각이 붙은 기록이라 낡은 현재형은 아니지만, 규칙과 모양이 어긋난다. "(09-24 기록)" 표시 또는 삭제 권함.
- **N118.** handoff `:12` "사전 등록 5c46056(20:30:33Z)·40895f8(20:34:02Z)" — 괄호 시각은 사전 등록 문서 머리의 등록 시각(`prereg_cam3.md:1`·`prereg_ma3.md:1` ✓)이고 커밋 시각은 20:33:20·20:34:19 UTC다(해시 옆에 커밋 아닌 시각 — 28회차 N85와 같은 종류). "확인 21:02 UTC `nvidia-smi` 90·91 %"의 순간 값은 다시 확인할 수 없다: 실험의 GPU 감시 CSV(`logs/cam3/gpumon.csv`, 30 s 간격, KST 표기)에서 21:01:56–21:02:56Z GPU 2 = 99·100·100 %, GPU 3 = 43·100·100 %; 두 학습(시드 1)은 그때 돌고 있었다(20:42:33–21:23:33Z·20:45:14–21:23:02Z) → "학습 중" ✓.
- **N119.** (N103 참조) 29회차 줄 "보고 2026-09-25 21:2x UTC, 파드 정리 21:23:27Z"(handoff `:134`), draft-log `:480` "21:2x UTC", direction-log `:76` "21:2x" — `r7_cycle29.md` 머리 "작성 21:28 UTC" ✓(2x 근사).
- **N120.** 같은 사실(행 파일 mtime)의 근거 명령이 `04:61`에는 "파드 `stat -c %y` 18파일", `ma1.md:15`에는 "파드 `ls -l --time-style` 18파일"로 다르게 적혔다; 29회차가 실제로 쓴 것은 `rows29.py`(os.path.getmtime)·`rows29b.sh`(find -printf)다. 값은 같다.
- **N121.** `04:36` GPU 역할 "3 = vLLM·보조 VLM 서버(탐침 Qwen3-VL-8B 포트 8341)" — GPU 3은 E-MA3 학습(`01:65`, handoff §0; 87.5 GiB)에 쓰이고 21:33Z에 vLLM 프로세스가 없다. '역할'로 읽으면 정책이지만 지도의 현재형 서술로는 낡았다. "3 = vLLM·보조 VLM 또는 학습(실험별 — handoff §0)" 식 권함.
- **N122.** README `:11` "실험 장부의 상태 칸은 `예정`·`끝`·`중단`처럼 …" 대 `01:56`(표 D만) 네 값 — 표 A·C의 상태 칸은 전부 `끝 ([R/…])` 꼴(`check30` H7: A 20행·C 9행)이다. 장부 전체에 같은 규칙을 둘지(링크를 문서 칸으로) 표 D만 둘지 정하면 D-1 같은 반쪽 적용이 줄어든다. 또 29회차 권고 3의 "결과가 커밋되면 §0 줄을 지우는 규칙"은 README·P69 어디에도 더해지지 않았다.
- **N123.** 텍스트 위생: 사본 텍스트 539파일 CR 0; 변경 md 10개 BOM·C0·C1·영폭 0, **표 칸 수 불일치 0**(`check30` H3 — 코드 구간·이스케이프 파이프 제외); 책 링크 101개 끊김 0(H4); `prereg_hash --check` OK(H2). 272432e는 책 01·02·04·06을 바꾸고 06 `:21` 한 줄(01·02·04, 21:30 ≤ 커밋 21:30:23 ✓)을 더했다(H5).
- **N124.** 시험 수: 로컬 **1133 passed / 20 skipped**(234.2 s, 21:32:31–21:36:26Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c30/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(251.0 s, EXIT 21:38:49Z; 건너뜀 isaaclab·pyarrow 경로·CUDA·TODO), 경고 1(기존), LeRobot 6 passed(18.7 s). 29회차와 같은 수(코드 무변경).
- **N125.** 단계 B 소형 CPU 스모크(21:41:42Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–29회차와 같은 값 — 결정적), 저장·재적재 행동 차 0.0, expert p50 0.035 s·전체 p50 0.114 s, 맥락 토큰 454.
- **N126.** DEV 24 판: 행동 1,745·17.45 s·결정 호출 52(조건마다), C5 `last_step` {none 1, OK 31, LAG 9, DEVIATE 11}, C5' none 52/52, 확정 비율 0.8226, 결정 2.982/s, rtf 0.365, 지연 p50·p95 0.3 s, Astra 2(hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28·29회차와 같음 — 코드 무변경), 파일명 `dev24-P0-standard-e0`, 판 254.5 s(21:40:14–21:44:29Z). 파드 GPU(21:33Z·21:45Z): 0 = R2_TRAIN 워커 2(dr P2, 8.1 GiB), 1 = R2_TRAIN 워커 3(standard P2, 12.2 GiB; + 내 Isaac 21:40–21:44Z), 2 = E-CAM3(86.8 GiB), 3 = E-MA3(87.5 GiB).
- **N127.** (절차, 자체 점검) ① 음성 대조 `verk0`(k0 검증 대상에서 `prev_step` 삭제)는 원본 k0에 `prev_step`이 **처음부터 없어서**(키 `['truth']`) 아무것도 바꾸지 않았다 — 결과("k < 10은 검사 안 함" 경계 통과)는 무수정 원본으로 이미 보인 것이라 새 정보가 없다; `verk10`(키 `['prev_step', 'truth']` → 삭제 → "verification target missing at [10]")이 실제 경계 검사다. 설계 착오로 기록하고 12종 계수에는 넣되 새 종류로 세지 않는다(실질 11종). ② 정리 스크립트의 "r7c30이 든 명령줄 프로세스" 검사는 `grep 'r7c[3]0'`으로 자기 매칭을 피했다(29회차 N115 ③). ③ R2_TRAIN 워커 코드 폴더(`code_r2train_e8e1864`)는 이번에도 `/proc/<pid>/cwd`로 다시 확인하지 않았다(28회차 확인값).

---

## 5. 사전 등록 대조표 (행마다 이번 회차의 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check30` H2), 파드 산출 `meta.prereg.check` = OK. 29회차 표의 행 번호를 그대로 쓴다. 기준선 코드 = 0cc45ae와 같음(H1). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c30\check30.py`(H1–H9), **파드** = §6(`pod_cpu30.sh`, `pod_eval30.sh`·`data30.py`·`gtxt30.sh`·`show30.sh`, `pod_isaac30.sh`·`closed30.py`, `r2state30.sh`·`epoch30.py`·`exp30.sh`·`who30.sh`, `attr30.sh`·`clean30.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 가드 28건 rc ≠ 0(§6.4): TEST 1077·1088, CAL 523·537, TEST-P5 1317·1311, DEV 24,31·1998, POOL 2125, gen 10000(확인 없음)·9000·60001(확인 있음), determinism 1000·2120 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | 코드 무변경; `calib --heldout jsel_dev/P2 --episodes 2` → `CALIB_DONE`; 가드 3(`--fit-split test_p5`)·4(`--heldout-split cal`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 24** C5·C5' 성공(17.45 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 24 결정 호출 104행**(조건마다 52): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 104/104; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치 |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P0 --split dev --episodes 2` → `E05_DONE`; 가드 24(`canary build-set --data P2 --seeds 3120-3121`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H`·`m4_lead_max` 3·1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,C7"` → "condition 'C7': runtime has ['C0' … 'C6']"; **DEV 24 C5 `last_step` {none 1, OK 31, LAG 9, DEVIATE 11}, C5' none 52/52, 요청 본문 마지막 `last_step:` 줄 = 행 값 104/104** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P0 --episodes 2` → `RD_DONE`(dr 낙폭 평균 0.0, n 275); 가드 5 `rd --variants dr=gen_dev/dr/P0 --split cal` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=inf` → "lead_max = inf … finite > 0 s", 15 `=0` → "lead_max = 0.0 … finite > 0 s", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(21:45Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2011,2058,2104 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 24, 21:40:14–21:44:29Z)**: 행동 **1,745개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 52·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | R2_TRAIN 워커 5개 P2 진행 중(21:33Z); 코드 폴더는 28회차 확인값(N127 ③) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119" 폴더 없음; 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu=-1`·`4` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 24 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 3편 입력**(standard/mug_marker/P0 ep3·dr/mug_tray/P0 ep1 참, dr/bottle_tray/P0 ep2 **거짓**): 내보낸 편 2·560프레임(무효 편 건너뜀 ✓), `verify` 오류 0·PSNR 최소 34.27 dB·lerobot 0.3.3 적재 560프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 대조 12종**(dr/mug_tray/P0 ep5, 289프레임): 무수정 오류 0; k0 시각 +9.95e-7 s → 오류 0; k288 시각 −1.2e-6 s → "off the 30 Hz grid by 1.20e-06 s"; k144·k145 줄 순서 바꿈 → "frame indices not contiguous from 0"; stageb 행 추가 → "stageb rows are not one per non-terminal frame"; 라벨 행 k140 → 141 → "labels_v2 rows != decision frames"; k0 `prev_step` 없음 → 오류 0(N127 ①); k10 `prev_step` 삭제 → "verification target missing at [10]"; k96 행 `H` 15 → 14 → "action_exec: shape (15, 8), expected (14, 8)"; npz `q` +inf → "npz q: … non-finite"; npz `t` 288 → "npz t: length 288 (want 289)"; `hold_n[288]` +7(합산 범위 `[:K]` 밖) → 오류 0 | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 24 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 이번 대상에 새 유료·GPU 실험 등록 없음 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 272432e 코드 변경 0(H1); 옵트인 가드 28–32(argparse·install 단계 거부) | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | §6.3: 링크 101개 끊김 0, 04·01 수치 파드 원자료 대조, 06 갱신 줄 | **DOC D-1** / NOTE N116–N122 |
| **156** | 정본 §86 = 탐침 결과 + §86 보충(`:778`) | — | 보충의 20 s = `harness.STREAM_TIMEOUT_S`(시뮬 초, `:45`·`:539`), 11.6/14.1 = 5절 표(편별 평균 `:58`), 12–16 s = 0절 `:6` | 일치(N88 해소) |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond`, … | 코드 무변경; 가드 29–32 거부; 결과 커밋 없음(S20) | 일치 |

### 5.1 29회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드 28건), 5·6·51–58·99·137·151(DEV 24), 13–17·61–62(jsel_dev/P0·gen_dev/dr/P0), 2–4(jsel_dev/P2), 66–67(`inf`·`0`), 98(POOL 2011·2058·2104), 138(다른 두 편 + 무효 편 건너뜀), 139(새 대조 12종), 155(D-1), 156(N88 해소).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --numstat 0cc45ae 272432e`: 코드 0. 문서 = 책 01 +10/−8, 02 +1/−1, 04 +2/−2, 06 +1, 정본 +1/−1, draft-log +1, handoff +8/−1, direction-log +1, `ma1.md` +1/−1, 새 `r7_cycle29.md`(223줄).

### 6.2 29회차 정정 주장 대 실제 diff·원자료 (272432e)
| 주장 (06 `:21`, handoff §0·`:134`, 커밋 메시지) | 실제 diff | 원자료·원 문서로 참인가 | 판정 |
|---|---|---|---|
| handoff §0 R2_TRAIN 줄(29회차 D-3) "확인 2026-09-25 21:29 UTC: P0·P1 생성 끝, P2(10800–10999) 생성 중(생성 프로세스 15개, dr·standard); `P*.stageb.jsonl`·`check.json`은 12:19:47–12:20:26 UTC 파일럿 병합분(파드 `ls`는 KST — 21:19–21:20 KST)" | `handoff.md:9`–`:13` 새 §0 | 파드(21:33Z, `r2state30.sh`·`epoch30.py`): P0 폴더 6개 600편·마지막 끝 17:01:57–18:08:13Z, P1 6개 200편·마지막 19:41:30–20:02:13Z(모두 21:29 전) ✓; P2 dr 137·standard 196–197편, 21:29 뒤에도 6–10편씩 끝남 ✓; `datagen.gen` 프로세스 15개(= 워커 5 × timeout·bash·python3, 20:01:59–20:02:14Z 시작, dr 2·standard 3) ✓; 행 파일 18개 12:19:47–12:20:26Z, `check.json` 12:20:26Z, 12:21Z 뒤 바뀐 행 파일 0 ✓; 파드 `/etc/localtime` = Asia/Seoul, 기본 `ls -l` "Sep 25 21:20" ✓ | 맞음 |
| handoff §0 E-CAM3·E-MA3 줄 "사전 등록 5c46056(20:30:33Z)·40895f8(20:34:02Z) 뒤 학습 중(확인 21:02 UTC `nvidia-smi` 90·91 %). 결과 문서 없음." | `handoff.md:12` | 등록 시각 = 등록 문서 머리 ✓(커밋 20:33:20·20:34:19 UTC); 21:02Z 학습 중 ✓(시드 1 20:42:33–21:23:33Z·20:45:14–21:23:02Z; GPU 감시 CSV 21:02:26Z 100·100 %); 결과 문서 없음 ✓(272432e) | 맞음(N118) |
| handoff §0 R7 줄 | `handoff.md:13` | 29회차 FAIL(DOC 3)·연속 무결 0 ✓ | 맞음(N116) |
| 01 표 D 상태 칸 통일(29회차 D-1·N107) | `01:56` 새 규칙 줄, `:63`–`:69` 상태 칸 = 네 값, 근거를 결과 칸 괄호로 | `:63`–`:70` ✓; **`:60`–`:62` 상태 칸에 링크·"바뀐 결정" 남음 ✗** | **D-1** |
| 01 R7 행 "1–29회차"(N105) | `01:38` | 보고서 29개, PASS 6·16·20·22 ✓ | 맞음 |
| 04 시드 수 종류별(29회차 D-2)·확인 시각(N106) | `04:61` "과제당 시드 수 P0 19–41 · P1 11–19 · P2 10–20 … 근거 = 파드 `stat -c %y` 18파일 12:19:47–12:20:26Z", "병합 여부 등 진행 상태는 이 장에 적지 않는다"; `04:3` "21:07·21:30 UTC에 … 재확인" | 파드 `epoch30.py`: P0 19·30·30·26·40·41, P1 11·19·19·11·19·19, P2 10·20·20·10·20·20 ✓; mtime ✓; "아직" 삭제(N102 해소) ✓ | 맞음(N120) |
| 02 P69 회차(N104) | `02:55` "(27·28·29회차; 26회차 정정이 꼬리표를 만듦 — …N104)" | 27 D-1·28 D-1/D-2·29 D-1/D-3 ✓, 칸 수 5 ✓ | 맞음 |
| 정본 §86 보충 시뮬 초(N88) | `00-interfaces.md:778`에 "[2026-09-25 21:30 UTC, R7 29회차 N88]" 구절 | `harness.py:45` "sim s", `:539` ✓; "0절 요약의 p95 범위 12–16 s" = 결과 `:6` ✓ | 맞음 |
| `ma1.md` 근거 표시(N108) | `ma1.md:15` 끝 "[근거 …]" | 값 ✓, KST ✓ | 맞음(N120) |
| handoff §2.8 29회차 줄·N103 표시, draft-log·direction-log | `handoff.md:134`, draft-log `:480`, direction-log `:76` | 건수 DEFECT 0·DOC 3·SCOPED 21·NOTE 77·실험 절 PASS = `r7_cycle29.md` 판정 표 ✓; 파드 정리 21:23:27Z ✓; "21:2x" = 작성 21:28 ✓; N103 표시는 28회차 줄이 아니라 29회차 줄 끝 | 맞음(N103·N119) |
| 갱신 기록 | 06 `:21` "2026-09-25 21:30 \| 01·02·04 \| …" | 272432e 책 변경 01·02·04·06 = 줄이 덮음 ✓, 21:30 ≤ 21:30:23 ✓; "01 표 D 상태 칸 통일" 주장은 D-1로 불완전 | 맞음(D-1) |

### 6.3 기록책 (272432e 사본에서)
- 현재형 진행 상태 검색(`check30` H9: `진행 중|생성 중|학습 중|작업 중|미커밋|아직|지금|현재`): 02·06 이력 인용(P14·P68·P69, 06 `:15`·`:16`·`:20`)과 README·01·04의 "handoff로" 안내·규칙 문장을 빼면 `01:38` "(아직)"(E2E 기준점 — 커밋으로만 바뀌는 값), `04:22`·`04:48` "현재"(판본·결정)뿐 → 책 본문에 현재형 진행 상태 없음. "지금 상태는 handoff" 안내 5곳이 가리키는 §0이 이제 있다(29회차 D-3 해소).
- 수치: `04:61` ✓(§6.2); `01:69` "계획 P0–P2 시드 10000–10999" = 파드 워커 명령 `--seeds 10800-10999`(P2)·29회차 확인 ✓; `01:63`·`:65` GPU 2·3 = 파드 ✓.
- 링크 101개 끊김 0(H4); 06 갱신 줄(N123).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 21:39:27–21:39:45Z, 21–29회차와 다른 값; 사유는 `gtxt30.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data P0 --split test --seeds 1077`, 2 `e05 --data P1 --split cal --seeds 523`, 3 `calib --fit-split test_p5 --heldout P2 --heldout-split dev`, 4 `calib --fit-split pool --heldout P2 --heldout-split cal`, 5 `rd --variants dr=gen_dev/dr/P0 --split cal`, 6–8 `closed --split test --seeds 1088`·`cal 537`·`test_p5 1317` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 24,31` → "seeds [31] are not in split dev", 10 `pool --seeds 2125`, 11 `dev --seeds 1998` → "not in split … (refused, never opened)"; 12–13 `--isaac-gpu=-1`·`4` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=inf`, 15 `=0` → "lead_max = inf / 0.0 … finite > 0 s"; 16 `--conditions "C5,C7"` → "condition 'C7': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test --seeds 1111`, 18 `=test` + `e05 --data P0 --split test_p5 --seeds 1311` → 거부(다른 분할 허용은 통하지 않음); 19 `gen --seeds 10000`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9000 --confirm-train`, 21 `--seeds 60001 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 1000`, 23 `history --seeds 2120` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P2 --seeds 3120-3121`, 25 `e05 --data P0 --split pool --seeds 2110` → "no episode selected"; 26 `--hb-mode k4`, 27 `--hb-mode "K 4"` → "from ('K0', …, 'K4')"; 28 `stageb_train predict --aux-extra a3d@V1` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 train --data pool --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 evalck --data se2e --cam3 cam3@v1`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)", 31 `se2e_kvcond train --expert-cond kvcond@V1`, 32 `se2e_cam3 predict --cam3 cam3@v0` → argparse "invalid choice" rc 2. **32건 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c30\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c30/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 12종; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀, 행 138); `se2e_c1` **5/5 OK**(21:45Z). (R2_TRAIN 폴더 행 병합은 아직 — N94, 완료 정의 1은 R2 DEV 기준.) |
| 2 모델 | 충족(CPU) | CPU 스모크(N125), CPU 묶음의 단계 B·E-MA1b·E-CAM3·E-MA3 시험 통과, 기준선 코드 무변경. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 24 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c30`: `CLOSED_DONE` C5·C5' 1.0, 호출 52·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 21:39:45–21:40:21Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`(dr 낙폭 0.0), `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). HEAD 시작·끝 272432e.
- 파드 정리 대상 판별(`attr30.sh`, 21:45Z): 내 Isaac 창(21:40:14–21:44:29Z)에 생긴 `tmp/carb.Uv8Ckm`(21:40:15 생성, Kit 임시)·`tmp/tmpv_2_xrv8`(21:40:32, `_remote_module_non_scriptable.py`; `.pyc`가 `cache/pyc_r6` 아래 = 내 워커의 접두)·`pyc_r6/…/r7c30`(21:40:15, 772 KB)·`kitcache/cyclo-r7c30_standard`(21:40:14, 208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-CAM3·E-MA3 학습 2개(21:27:59·21:28:07Z 시작)와 GPU 감시 `nvidia-smi` 2개뿐이고 모두 `PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc`(pyc_r6 아님) → 두 임시 항목은 내 것(29회차 N114와 같은 모양).
- 파드 정리(`clean30.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 21:45:38Z): `tmp/r7c30`(501 MB), `tmp/carb.Uv8Ckm`·`tmp/tmpv_2_xrv8`·`cache/pyc_r6/data/harvest/tmp/tmpv_2_xrv8`·`cache/pyc_r6/data/harvest/tmp/r7c30`, `ir/kitcache/cyclo-r7c30_standard`(208 MB). 끝에 r7c30 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c30이 든 프로세스 0, `IR_INST=r7c30` 프로세스 0, 열린 핸들 0. R2_TRAIN·E-CAM3·E-MA3 파일은 읽기만(E-CAM3·E-MA3는 이름·시각·GPU 감시 CSV만).
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a30.tar` 삭제, 보고 근거 스크립트·출력만 남김; 지시대로 `D:\tools\scratch_qdd\r7c28` 삭제 — r7c 폴더는 r7c29(592 KB)·r7c30(480 KB)만. D: 여유 8.1 GB(끝, 21:49Z). 이 보고서 표 칸 수 불일치 0·CR 0(`cellcheck30.py`).

## 7. 실험 코드 절 (별도 판정: PASS — 새 실험 쪽 변경 없음)

### 7.1 272432e의 실험 쪽 변경
- 없음. `git diff --name-status 0cc45ae 272432e`는 책·정본·기록·`ma1.md`·보고서뿐이고, 실험 코드(`harvest/train/se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3|ma3/`)·실험 결과·사전 등록 변경 0. 옵트인 가드 29–32로 두 실험 경로의 거부가 그대로임을 다시 확인(§6.4).

### 7.2 E-CAM3·E-MA3
- 272432e까지 결과 커밋 없음 → 범위 밖(S20). 파드에서 본 것은 이름·시각뿐(`exp30.sh`): `ckpt/cam3/cam3_s1`(21:23:33Z)·`cam3_s2`(21:28:28Z)·`ckpt/ma3/kv_s1`(21:23:02Z)·`kv_s2`(21:28:36Z), 로그 `cam3_s2.out`·`kv_s2.out` 21:34Z 갱신(학습 중). 사전 등록 커밋(20:33:20·20:34:19 UTC)이 각 실험의 첫 파드 기록(`logs/cam3/pytest.out`·`predfull_none_s1.out` 20:33:56Z, `logs/ma3/pytest.out`·`chunk_none_s1.out` 20:34:44Z)보다 앞선다 ✓. `predfull_*`·`chunk_*`·`reuse_check.out`·`verify_results.py`는 열지 않았다.

### 7.3 DOC (실험 절)
없음.

### 7.4 NOTE (실험 절)
- E-N1–E-N11. (27회차 그대로; E-N3 해소.)
- E-N12. (그대로.)
- E-N13. (해소.)
- E-N14–E-N18. (그대로.)
- E-N19. (그대로) 결과 `astra_motion.md:7`·`:58`의 "17:43–17:52Z" — 272432e는 이 파일을 바꾸지 않았다.

## 8. 다음 순회 전에 할 일 (제안)
1. **D-1**: `01:60`·`:61`·`:62` 상태 칸의 링크(와 `:62`의 "바뀐 결정 …")를 결과 칸으로 옮겨 상태 칸을 `끝`만 남기고, 06 줄. 고친 뒤 표 D 상태 칸이 네 값과 정확히 같은지 기계 검사(`split('|')` 마지막 칸 == `끝`/`중단`/`` `[결과 전]` ``/`` `[예정]` ``) 결과를 06 줄이나 커밋 메시지에 적는다(P68).
2. (선택, NOTE) N116(§0 R7 줄 시각), N117(`:93` 옛 진행 줄 표시), N103·N119(28회차 줄 시각 표시 위치), N121(`04:36` GPU 3 역할), N122(장부 전체 상태 칸 규칙·§0 줄 삭제 규칙), N90(지도 새 경로), N120(근거 명령 표기 통일).
3. 31회차 대상은 272432e 이후 HEAD, **연속 무결 0에서**. E-CAM3·E-MA3 결과가 커밋되면 기준 재사용 비트 동일·판정 재계산을 실험 절에서. R2_TRAIN 생성이 끝나면 병합·행 수 대 편 수(N94), 그리고 handoff §0 줄 갱신.
