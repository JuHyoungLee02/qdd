# R7 객관 검증 순회 — 27회차 (cycle 27, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle26.md`의 표·결론을 근거로 쓰지 않고 사전 등록·정본·원자료에서 대조표를 다시 만들었다. 행마다 **21–26회차와 다른 새 경계값 입력 → 실제 함수·CLI 출력**, **실험 코드의 실제 함수를 경계 입력·가짜 세계·스텁으로 돌린 결과**, 또는 **파드 원자료(비용 장부·결과 JSON·예측 파일) 재계산**으로 확인했다). 작성 2026-09-25 20:40 UTC 무렵(로컬 사본 풀기 20:07:03Z, 파드 첫 명령 20:10:41Z, 파드 정리 끝 20:29:29Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`7a02943`**(`7a02943ded0a325a8eb9a537c5b1625a27f080d0`, 커밋 시각 2026-09-25 20:02:57 UTC, "book: pitfall P67 …"). `6483397..7a02943` = 커밋 6개(3500f54 탐침 결과·정본 §86·스펙 §17·탐침 코드 + 62시험, 2df9bdc E-MA1b 결과, cc38f6d 논문, dc945bf 26회차 보고서·정정, 7a02943 책 P67), `git diff --stat` 61파일 +4,090/−41. 검토 시작 때 HEAD = 7a02943, 보고서를 쓰는 동안 HEAD가 **40895f8**로 움직였다(5c46056 E-CAM3 사전 등록 20:33:20Z, 40895f8 E-MA3 사전 등록 20:34:19Z — 대상 뒤, 범위 밖; 모든 대조는 7a02943 archive 사본에서 했다).
- **범위 나눔(26회차와 같음)**: **기준선 판정**(연속 무결 카운트) = `harvest/`(런타임·평가·시뮬·분석·학습), `tools/`(실험 도구 제외), 시험, 정본, 26회차 목록의 사전 등록, handoff·기록·결과 문서, 기록책 `docs/book/`. 이번 diff의 코드 변경은 **새 탐침 패키지 `harvest/astra_motion/` 15파일 + `tests/astra_motion/` 8파일뿐**(모두 추가, 기준선 코드 변경 0 — `check27` H2). **실험 코드 절**(따로 판정) = 탐침 코드·시험(3500f54), `prereg_astra_motion.md`(+ 수정 1·2, 정정 13절), `results/astra_motion.md`, E-MA1b 결과(`results/ma1b.md`, 2df9bdc)와 26회차에서 미룬 S22 두 검사. E-CAM3·E-MA3(GPU 2·3 시작 중)은 범위 밖.
- 사본: `git -c core.autocrlf=false archive 7a02943`(tar 주석 = `7a02943ded0a…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c27\repo`에 풀었다(**570파일**, 텍스트 518파일 CR 0). 파드 사본 = 같은 archive를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c27/code`(571파일 = + `CODE_VERSION`), 텍스트 CR 0, 올린 스크립트 CR 0(매번 확인). 파드 산출 `meta.git.commit` = `7a02943ded0a…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle26.md`, 정본 `00-interfaces.md` §1–§86(뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e*.md`·`M4-overlap-commit.md`·`prereg_astra_motion.md`·`prereg_ma1b.md`, 결합 설계 스펙(§17)·구현 계획(상수 표).
- 분류(26회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약 수치(값은 맞음), 추정 표시(≈·약)가 있는 수치, 반올림 차이는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c27`(C: 쓰기 없음). 스크립트는 Write 도구로 쓰고 경로로 실행(heredoc·`python -c`·`python -` 없음). **절차상 어긋남(내 쪽) 1건**: `pod_isaac27.sh`·`closed27.py` 두 개는 26회차 스크립트를 `sed` 치환 + 리디렉션으로 만들었다(Write 도구 아님; 치환 결과를 실행 전 `grep`으로 확인, CR 0) — N83. 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c27`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c27_standard`, `--inst-prefix r7c27`; GPU 0·1의 R2_TRAIN 워커 5개는 건드리지 않음), GPU 2·3에는 아무것도 올리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음(비용 장부는 사용량·메타·비용 필드만).

## 판정 (기준선): **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 21 |
| NOTE | 61 |

## 판정 (실험 코드 절, 카운트와 별개): **FAIL — 코드 결함 0, DOC 2**

**기준선 코드는 26회차 대상과 바이트가 같다**(diff의 코드 경로 23개가 모두 `astra_motion` 추가). 회귀: 로컬 **1118 passed / 17 skipped**(Git Bash, 395.3 s; 26회차 1056 + 탐침 시험 62), 파드 CPU **1250 passed / 4 skipped**(176.4 s; 1188 + 62), LeRobot 6 passed; 가드 **28건** 모두 rc ≠ 0(21–26회차와 다른 경계값: TEST 1000·1149, CAL 500·549, TEST-P5 1300·1329, DEV 30, POOL 1999·2120, R2_TRAIN 9999·59999(확인 없음)·60000, `--m4-lead-max=0`·`=nan`, `--isaac-gpu 4`·`1,2`, `--conditions "C5,c5"`, `--hb-mode K5`·`K2,K9`, `--aux-extra A3D@v1` 등); R2 DEV `validate_episode` **36/36** + **새 종류 음성 대조 7종**(경계 안 시각 오차 5e-7 s는 통과, 2e-6 s·머리 영상 크기·labels 한 줄 누락·검증 목표 누락·npz NaN·hold_n 합 — 모두 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 완료; 새 시드 **DEV 13**에서 같은 Isaac 워커 C5 → C5' 행동 **1,413개 비트 동일**. **26회차 정정 주장 가운데 책 01(PASS 회차)·03(ECE §72)·정본 N47·N48 표시·§85 E-MA1b 보충·handoff §2.8·draft-log·direction-log·06 갱신 줄은 실제 diff와 맞다**(§6.2). 탐침 결과는 정본 §86·스펙 §17과 일치하고 현재 시제 "6 s" 확정값은 없다(스펙·계획의 6 s는 모두 '잠정' 표기 — N79).

**DOC 1건(기준선)**: 26회차 N55 정정으로 새로 쓴 책 `04-map.md:61`의 괄호 "(지금 생성 중인 P0 = 10000–10599 등)"이 같은 대상 트리의 결과 `ma1.md:15` 정정(2df9bdc, "P0 행은 이미 조립 … 19:07Z에는 P1 섭동 종류를 생성 중")과 26회차 보고서 N55(dc945bf, "19:13Z 파드는 P1 10600–10799")에 어긋난다(D-1). **연속 무결 0 유지.**

**DOC 2건(실험 절)**: E-D1 `results/astra_motion.md` 2절 비용 표의 G1 v2 입력 토큰(507/657/811 — 실제 장부 588/738/892)과 S2 호출 수 서술("72 (+ 끝난 뒤 도착 6)" — 장부 72행이 끝난 뒤 도착 6을 포함), 7절 "16편에서 close"(17편); E-D2 등록 13절 자체 점검 "Qwen 6편 … 모두 프롬프트 판본 `9b5c5c292765`"가 원자료와 다르다 — Qwen S2 6편 가운데 4편(s0·s7 × F0·F1, 17:43–17:52Z 무료 사전 실행)은 옛 판본 `a84e4c76efed`.

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① 부드러운 실행기 `SmoothExec`는 뒤집힘(`flip`)과 집기 동작 순간에 속도를 한 틱에 0으로 만든다 — 가속 1.6–1.9 m/s²(상한 0.32의 5–6배, `check27` X1c). 등록 4.2절이 "뒤집힌 답이면 속도를 0으로 되돌린 뒤 새 경사", "이동을 빨리 한 뒤 바로 집기"로 그 동작을 적었고, 명령 속도 상한 8 cm/s는 지켜진다(X1b) → 실험 절 NOTE E-N5. ② 러너의 무효율 관문은 모드 "S"에서 `S*` 폴더(흐름 포함)를 한 단계로 묶는다 — S1은 수정 2로 삭제돼 쓰이지 않음 → E-N7.)

## 2. DOC

- **D-1. `docs/book/04-map.md:61` — R2_TRAIN 현재 상태를 틀리게 적었다.** 26회차 N55 정정(dc945bf, 2026-09-25 20:01 UTC)이 시드 영역을 10000–59999로 바르게 고치면서 괄호 "(지금 생성 중인 P0 = 10000–10599 등)"을 새로 넣었다. 같은 대상 트리의 `docs/stage3/results/ma1.md:15`(2df9bdc 정정 19:55 UTC)는 "`dr|standard/<과제>/` 아래에 편 폴더 `P0/`와 과제별 `P0.stageb.jsonl` … 이 이미 있었고, 19:07Z에는 P1 섭동 종류를 생성 중"이라 적고, 같은 커밋의 `r7_cycle26.md` N55도 "19:13Z 파드는 P1 10600–10799 워커 5개"라 적는다(파드 20:10Z에는 `--kinds P2 --seeds 10800-10999` 워커 5개). "지금 생성 중인 P0"은 현재 시제 서술인데 원 문서와 다르고, 뒤의 정정 표시는 이 괄호를 '정정된 값'으로 보이게 한다(책 P08 "정정했다고 적었는데 반쪽만"). **고칠 것**: 괄호를 "(생성 계획 10000–10999: P0 10000–10599 → P1 10600–10799 → P2 10800–10999; 진행 상태는 `R/ma1.md` 1절·handoff)"처럼 시각 없는 계획 서술로 바꾸거나 "(2026-09-25 19:07Z P1 생성 중 — `R/ma1.md`)"처럼 시각을 붙이고, 같은 커밋에 `06-updates.md` 한 줄. 재발 방지: 책에 "지금·현재"를 쓸 때는 확인 시각을 함께 적는다.

(검토했지만 DOC로 올리지 않은 후보: ① 책 `05-costs.md:14`·`:15`의 G1 v2 토큰 507/657/811·"72 (+ 끝난 뒤 도착 6)"은 원자료와 다르지만 **인용한 결과 문서 2절과 같은 값**(책 README `:8` 규칙대로 옮김) → 원천 오류는 실험 절 E-D1, 책은 같은 커밋에 함께 고칠 NOTE N70. ② 책 `03-decisions.md`에 정본 "§85 보충"(20:01, E-MA1b 불채택) 줄이 없다 — 03은 보충 가운데 §82·§84 것만 싣고 있고 틀린 서술은 없음 → N72. ③ 06 갱신 줄 "2026-09-25 19:58"(2df9bdc)은 커밋 시각 19:49:56 UTC보다 늦다(로컬·파드 시계 차 < 0.2 s 측정) → 시각 기록 오차 N68(26회차 N49와 같은 계열).)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 R2_TRAIN Isaac 워커 5개 진행 중(20:10Z, `gen gen --kinds P2 --seeds 10800-10999 --confirm-train`, standard·dr, GPU 0·1; 읽기만); 확인 인자 없는 `--seeds 59999` 거부(가드 19).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 7a02943에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현 및 §84·§86 결합 설계 구현**(직렬 흐름, 두 층 M4, 카메라 3대·덧그림, `CoupleParams` 상수 반영) — "R7 E2E 준비 기준점 뒤". 지금 코드: 파드 `closed --hb-mode K5`·`K2,K9` → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 13 Astra 2행), 흐름 호출 없음. 계획 상수 표는 탐침 뒤 Step 0-2에서 채우게 적혀 있음(N79).
- S19. **정본 §83 런타임 적용**(새 직렬화 판본) — DEV 13 결정 호출 요청 84/84 `motion:` 없음.
- S20. **E-CAM3·E-MA3**: 검토 중 작업 트리의 미추적 등록·코드·시험 10파일(`prereg_cam3.md`, `prereg_ma3.md`, `se2e_cam3.py`, `se2e_kvcond.py` 등)이 대상 뒤 커밋 5c46056·40895f8로 들어갔다 — 대상 밖, 열지 않음(28회차).
- S21. 탐침 E-Astra-motion 결과의 E-Couple 재측정(F0/F1 뒤집힘은 표본 부족, §86 "E-Couple에서 판정 밖으로 다시 잰다").

## 4. NOTE
- N1–N3. (그대로) `stageb_train predict`·`evalck`의 `prompt_config` 비대조, `cli_label.replay_max` NaN 순서, 판정 스크립트 입력 검사 수준(책 P25).
- N4. (해소) Astra 늦은 답 처리 — 정본 §86 `:769` "15 s보다 늦은 답은 평가만 쓰고 `edit`은 버린다".
- N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45. (그대로, 26회차 목록.) N10 재현: 가드 25(`e05 --data jsel_dev/P2 --split pool --seeds 2119` → "no episode selected")가 빈 `g25/`를 남김.
- N46. (그대로) `RESUME_KEYS`의 `a3d_root`.
- N47. (해소) 정본 `:729` "[→ 표시 … N47: 유료 실행 조건은 §85(자체 검사)로 대체]", `:730` "[→ 해소 §84(falsify 먼저 평가, 보충 1 …)]" — dc945bf.
- N48. (해소) 정본 §85 `:762` "(자체 검사는 저장소 CLAUDE.md 규칙과 같고, 80 % 정지는 설계 문서 §15 [→ 정정 …])" — dc945bf.
- N49–N52. (그대로) 25회차 시각, 책 `05:13` 출처, `01:50`·`05:33` "15:53–17:21", `05:31` `[미기록]`.
- N53. (일부 해소) `03:47` ECE 출처 §72 표시(맞음, 정본 `:606`); `03:4` §56–§62 날짜 주의·`03:62` 표시는 그대로.
- N54. (일부) `02:12` P04 표시를 더했으나 **표 행 끝 `|` 뒤에 붙어 6번째 칸**이 됐다(머리 5칸) — GFM은 넘치는 칸을 버려 렌더에서 표시가 보이지 않는다(`check27` H5 유일한 칸 수 불일치). 표시를 넷째 칸 안으로. P48 출처·P07 "세 번"은 그대로.
- N55. (일부) `04:61` 시드 영역은 맞게 고침(→ D-1은 괄호), `01:12`·`01:20`·`01:67`은 그대로.
- N56. (해소) 책 갱신 기록: e15270a 이후 책을 고친 커밋 7개 중 641547e(README) 하나만 같은 커밋에 06 줄이 없고 다음 커밋 6483397이 보충; 3500f54·2df9bdc·dc945bf·7a02943은 모두 같은 커밋에 06 줄(`check27`).
- N57, N58. (그대로) 탐침 등록 0절 꼬리표, 수정 1의 유료 호출 선행.
- N66. `01:38` 정정 표시가 문장 가운데 "FAIL [→ 정정 …](8회차 DEFECT 5 등)"으로 들어가 링크 문법 모양이 됐다(목적지에 공백이 있어 링크로는 렌더되지 않고 글자 그대로 보임; `check27` 링크 검사가 "8회차"를 끊긴 링크로 잡음). 값(6·16·20·22회차 PASS, handoff `:100`·`:113`·`:117`·`:119`, `r7_cycle{6,16,20,22}.md` 판정 PASS와 일치)은 맞다. 표시를 괄호 뒤로.
- N67. `01:38` 행 이름 "R7 객관 검증 1–25회차"는 26회차 보고서 커밋 뒤에도 25에서 멈춰 있다(회차별 줄은 handoff §2.8로 위임 — 틀린 서술은 아님). 책 P06 규칙("R7 보고서 커밋 = … +책 01장")대로 범위를 "1–26회차"로.
- N68. 시각 기록: 2df9bdc(커밋 19:49:56 UTC)가 적은 `06-updates.md:12` "19:58", handoff `:122` "(2026-09-25 19:58 UTC 기록)", `ma1.md:15` "[정정 2026-09-25 19:55 UTC"는 모두 커밋보다 늦다(책 P11).
- N69. draft-log `:477` "D: 여유 20 MB 경보 → 옛 R7 임시 폴더 삭제로 확보"와 책 P67 "→ 옛 r7c·pytest 폴더 삭제"·"R7은 직전 한 회차만 보관" — 이번 회차 시작(20:07Z) 때 `D:\tools\scratch_qdd\r7c25`(132 MB)가 남아 있었다(지시대로 내가 삭제). P67 증상 칸 "20 MB"와 발생 칸 "26회차 보고(29 MB)"는 다른 시점 값.
- N70. 책 `05-costs.md:14` G1 v2 "입력 약 507/657/811"·`:15` "72 (+ 끝난 뒤 도착 6)"은 결과 문서 2절을 그대로 옮긴 값 — 실험 절 E-D1과 같은 커밋에 고칠 것(588/738/892, "72(끝난 뒤 도착 6 포함)").
- N71. 정본 "§85 보충"(`:777`, 20:01 UTC)이 §86 본문 끝에 붙어 있다 — 뒤 절 우선 규칙과 모순은 없지만 §86 항목으로 읽힌다. §85 끝으로 옮기거나 "§86 뒤 덧붙임" 표시.
- N72. 책 03에 "§85 보충(20:01) E-MA1b 불채택" 줄이 없다(01·handoff·정본에는 있음). 책 P05 규칙상 결정 연표에 한 줄.
- N73. 정본 §66 `:563` "본 생성 계획(아직 실행 안 함)" — R2_TRAIN은 실행 중(S2). 절 시각이 있는 옛 서술이라 NOTE; 뒤 절 표시 권함.
- N74. 스펙 `:123` "E-Astra-motion 탐침(준비 중)", `:130` "요청 방식(F0/F1) … 탐침 뒤", `:180` "추정 1분당 약 0.5–0.9천 원 … 탐침에서 실측으로 바꾼다", `:185` "상한(탐침 뒤 고정, 잠정 6 s)" — 같은 문서 §17(`:198`)이 덮는다(26회차 N17 계열). 각 줄에 "[→ §17]" 꼬리표 권함.
- N75. 테이블 칸 수·제어 문자: 텍스트 518파일 CR·BOM·C0·C1·영폭 0; 변경 md 15개 표 칸 수 불일치는 N54 한 곳뿐.
- N76. 시험 수: 로컬 **1118 passed / 17 skipped**(395.3 s, 20:07:53–20:14:31Z; `-o tmp_path_retention_policy=failed`, `PYTHONDONTWRITEBYTECODE=1`, basetemp `r7c27/pt`), 파드 CPU **1250 passed / 4 skipped**(176.4 s, EXIT 20:21:06Z), 경고 1(`test_stagea_loss_torch.py:42` 기존), LeRobot 6 passed(22.9 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N77. 단계 B 소형 CPU 스모크(20:23Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–26회차와 같은 값 — 결정적), expert p50 0.040 s·전체 p50 0.090 s, 맥락 토큰 454.
- N78. DEV 13 판: 행동 1,413·14.13 s·호출 42, `last_step` {none 1, OK 30, LAG 6, DEVIATE 5}, 확정 비율 0.9256, 결정 2.975/s, rtf 0.40, Astra 2(hb 5.0 → 8.0, sub 8.01 → 11.01), `code_sha` `2d53a5ce235bd567`, 파일명 `dev13-P0-standard-e0`.
- N79. **§86·스펙 §17·계획 상수 대조**: §86 `:768`–`:776`의 수치는 결과 문서·원자료와 맞다(§7.2). 현재 시제로 "6 s 확정"을 적은 곳은 없다: 스펙 `:185`(잠정 6 s, §17이 대체), 계획 `:21` "6 s(잠정, 탐침 뒤 고정)"·`:68`/`:286` `stale_edit_s 6.0`("설계 §15 잠정")·`:65`/`:275` `request_mode "F1"`은 모두 "탐침 결과로 채울 기본값"(계획 `:57` Step 0-2, 코드 블록 머리 `:262` "defaults until the E-Astra-motion result … sets them")이다. 다만 계획 `timeout_s 15.0`(`:67`, 규칙 "직렬 지연 p95 × 1.5")은 실측 p95(F1 16.0 s)보다 짧아 규칙대로면 약 18–24 s — §86·§17은 시간 초과를 정하지 않았다. 구현(Task 1) 때 Step 0-2로 F0·15 s·시간 초과를 함께 반영할 것, 계획 `:21`·`:65`·`:68`에 "[→ §86]" 꼬리표 권함.
- N80. 파드 GPU(20:10Z·20:17Z): 0 = R2_TRAIN 워커 2(P2), 1 = R2_TRAIN 워커 3(+ 내 Isaac 20:24–20:28Z), 2·3 = 1 MiB(E-CAM3·E-MA3 아직 GPU 미사용).
- N81. 파드 정리 대상 판별(`attr27.sh`): 내 Isaac 창(20:24:03–20:27:57Z)에 생긴 `tmp/carb.3XSIDJ`(20:24:04 생성)·`tmp/tmp6_gkzeeg`(20:24:26, `.pyc`가 `cache/pyc_r6` 아래)·`pyc_r6/…/r7c27`(20:24:03)·`kitcache/cyclo-r7c27_standard`(20:24:03, 208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`나 `pyc_r6` 접두를 쓰는 다른 프로세스 0.
- N82. (절차, 내 쪽) 자체 점검으로 다시 설계한 항목 1개: `check27` X1 램프 기대("≤ 2.5 cm")는 등록 4.2절의 "창이 끝나면 0.5 s에 걸쳐 감쇠"를 빠뜨린 내 기대 오류(실측 2.729 cm = 2.5 + 감쇠분 0.21 + 가속 한 틱) — 기대를 등록 문장대로 고치면 일치(실험 절 E-N6로 기록). 나머지 항목은 첫 설계대로.
- N83. (절차, 내 쪽) 규칙 이탈 1건: Isaac 판 스크립트 두 개(`pod_isaac27.sh`, `closed27.py`)를 26회차 판에서 `sed` 치환·리디렉션으로 만들었다(시드 3 → 13, r7c26 → r7c27). 내용은 치환 뒤 `grep`으로 확인했고 파드 올림 때 CR 0. 다음 순회는 Write 도구로 새로 쓸 것(책 P03).

---

## 5. 사전 등록 대조표 (원문에서 새로 만듦, 행마다 이번 회차의 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check27` H3), 파드 산출 `meta.prereg.check` = "OK". 26회차 표의 행 번호를 그대로 쓴다. 기준선 코드 블롭은 6483397 = 7a02943(H2). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c27\check27.py`(H·X), **파드** = §6(`pod_cpu27.sh`, `pod_eval27.sh`·`data27.py`, `pod_isaac27.sh`·`closed27.py`, `exp27.py`·`exp27b.py`·`exp27c.py`, `ma1b27.py`, `attr27.sh`·`clean27.sh`). 코드 무변경 행은 새 가드 값·새 판으로 다시 확인했다.

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 가드 28건 rc ≠ 0(§6.4): 경계 TEST 1000·1149, CAL 500·549, TEST-P5 1300·1329, DEV 30, POOL 1999·2120, gen 59999(확인 없음)·60000·9999(확인 있음), determinism 30·1999 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | 코드 무변경; `calib --heldout jsel_dev/P0 --episodes 2` → `CALIB_DONE`; 가드 3(`--fit-split cal`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 13** C5·C5' 성공(14.13 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 13 결정 호출 84행**: 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 84/84; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치 |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P2 --split dev --episodes 2` → `E05_DONE`; 가드 24(`canary build-set --seeds 3150`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,c5"` → "condition 'c5': runtime has [C0 … C6]"; **DEV 13 C5 `last_step` {none 1, OK 30, LAG 6, DEVIATE 5}, C5' none 42/42, 요청 본문 마지막 `last_step:` 줄 = 행 값 84/84** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard,dr/P0 --episodes 2` → `RD_DONE`; 가드 5 `rd --variants random=… --split test` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=0` → "lead_max = 0.0 … finite > 0", 가드 15 `=nan` → "lead_max = nan … finite > 0", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H2); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(20:29Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2007,2058,2104 --truth outcome:plan` → `E05_DONE` | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 13, 20:24:03–20:27:57Z)**: 행동 **1,413개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 42·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | R2_TRAIN 워커 5개 진행 중(P2) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL" 폴더 없음; 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 4`·`1,2` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 13 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 2편**(standard/bottle_tray ep2 = `valid_for_training` 거짓 → 건너뜀, standard/mug_marker ep3 참): 1편·278프레임, `verify` 오류 0·PSNR 최소 39.11 dB·lerobot 0.3.3 적재 278프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 음성 대조 7종**(standard/mug_tray ep4, 277프레임): 무수정 오류 0; k92 시각 +5e-7 s(허용 1e-6 안) → 오류 0; +2e-6 s → "off the 30 Hz grid by 2.00e-06 s"; k276 머리 영상이 손목 JPEG → "size (424, 240) != native (672, 376)"; labels 28 → 27 → "labels_v2 rows != decision frames"; k140 `prev_step` 삭제 → "verification target missing at [140]"; `qd` NaN → "npz qd … non-finite"; `hold_n[3]` + 1 → "hold_n does not add up" | 일치 |
| **140–141, 152** | 정본 §82·§84·§86 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 84/84 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 13 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | `:729`·`:730`·`:762` 표시(N47·N48 해소) | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 블롭 6483397 = 7a02943(26회차 §6.1 결과 유지) | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | §6.3: 링크 98개(끊김 0, `01:38` 가짜 링크 1 — N66), 01·05 탐침·E-MA1b 수치 원자료 대조, 06 갱신 줄 전수 | **DOC D-1** / NOTE N54·N66–N72 |
| **156** | 정본 §86 = 탐침 결과 (`:766`–`:776`) | — | §7.2 원자료 재계산과 일치(F0, 15 s, 지연·나이, 13/25, 3 대 3, 0.83/2.36, 0/6·0/20·238 mm, 49.7–58.0·16.8·27.9원, 6,933.4원, 12/14 → 1/7) | 일치(N79) |

### 5.1 26회차 표와의 차이
- 행 156(정본 §86)을 더했다. 근거 교체: 행 1(새 경계 가드 28건), 5·6·51–58·99·137(DEV 13, 84행, 행동 1,413개), 61–62(dr/P0), 66–67(`0`·`nan`), 138·139(다른 편·새 음성 대조 7종). 행 154는 이번 diff에 기준선 코드 변경이 없어 블롭 동일로 확인.

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status 6483397 7a02943`: 코드 = `harvest/astra_motion/` 15 + `tests/astra_motion/` 8(모두 A), 기준선 코드 변경 0(H2). 문서 = 정본 +16/−3(§86 3500f54, N47·N48 표시·§85 보충 dc945bf), 스펙 +4(§17), handoff +4/−2, draft-log +3, direction-log +1, 책 6장, 결과 `astra_motion.md`·그림 2·`ma1b.md`·`ma1.md` 정정·`r7_cycle26.md`, `paper/` 21파일.

### 6.2 26회차 정정 주장 대 실제 diff (dc945bf·7a02943)
| 주장 | 실제 | 판정 |
|---|---|---|
| 책 01 PASS 목록 | `01:38` "6·16·20·22회차 PASS" — handoff `:100`·`:113`·`:117`·`:119`, `r7_cycle{6,16,20,22}.md` 판정 PASS와 일치 | 맞음(표시 위치 N66, 범위 N67) |
| 03 ECE 출처 | `03:47` "ECE는 §72에서 정함 [→ 정정 …]" — 정본 `:606`(§72 N4 "E1 ECE = 15개 동일 질량 구간") | 맞음 |
| 04 R2_TRAIN 시드 영역 | `04:61` "R2_TRAIN 시드 영역 10000–59999" = 정본 §66 `:562`·가드 19–21 | 영역은 맞음, 괄호 **D-1** |
| 02 P04 표시, 새 P67 | P04 표시 있음(표 밖 칸 — N54), P67 추가(다. 절, 번호 순은 유지) | 맞음(N54) |
| 06 줄 | dc945bf `:13`(20:01), 7a02943 `:14`(20:02) — 각 커밋 시각과 맞음 | 맞음 |
| 정본 N47·N48 표시, §85 E-MA1b 보충 | `:729`·`:730`·`:762` 표시, `:777` 보충(수치 = `ma1b.md`·판정 파일) | 맞음(위치 N71) |
| handoff §2.8 26회차 줄·draft-log·direction-log | handoff `:125` DEFECT 0·DOC 1·SCOPED 22·NOTE 54 = 26회차 보고서, draft-log `:477`, direction-log `:73` | 맞음(N69) |

### 6.3 기록책 (7a02943 사본에서)
- 갱신 기록: 책을 고친 커밋 e15270a·4117851·641547e·6483397·3500f54·2df9bdc·dc945bf·7a02943 — 규칙(4117851) 뒤 06 줄이 같은 커밋에 없는 것은 641547e 하나(다음 커밋이 보충, N56). 06 줄 시각은 커밋 시각과 맞고 2df9bdc 한 줄만 늦다(N68).
- 수치: `01:52`(E-MA1b) = 판정 파일·예측 파일 재계산(§7.3), `01:60`(탐침) = 원자료 재계산(§7.2), `05:13`–`:18` 비용·호출·지연 = 장부(예외 `:14` 토큰·`:15` 호출 수 서술 — N70), `05:35` GPU 시간 = `driver_main.out`(18:06:27–18:47:26, 18:56:17–19:33:24 → 41.0·37.1분), `02` P57–P67 출처 확인(P61 쥠 25/안 쥠 15, P58 0.38배, P62 5.1 cm, P64 1,165·10 = `ma1b.md:47`).
- 링크 98개 끊김 0(가짜 링크 1 — N66).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 20:21:54–20:22:07Z, 21–26회차와 다른 값)
1 `e05 --data P0 --split test --seeds 1000`, 2 `e05 --data P2 --split cal --seeds 549`, 3 `calib --fit-split cal`, 4 `calib --heldout-split test_p5`, 5 `rd --variants random=… --split test`, 6–8 `closed --split test --seeds 1149`·`cal 500`·`test_p5 1300` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 30`, 10 `pool --seeds 2120`, 11 `pool --seeds 1999` → "not in split … never opened"; 12–13 `--isaac-gpu 4`·`1,2` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=0`, 15 `=nan` → "finite > 0 … refused before any worker"; 16 `--conditions "C5,c5"` → "condition 'c5'"; 17 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test --seeds 1000`, 18 `=test` + `e05 --split test_p5 --seeds 1329` → 거부; 19 `gen --seeds 59999`(확인 없음) → "needs --confirm-train", 20 `--seeds 60000 --confirm-train`, 21 `--seeds 9999 --confirm-train` → 거부; 22 `determinism fresh --seed 30`, 23 `history --seeds 1999` → "only DEV 0-29 and POOL"; 24 `canary build-set --seeds 3150`, 25 `e05 --split pool --seeds 2119` → "no episode selected"; 26 `--hb-mode K5`, 27 `--hb-mode "K2,K9"` → "from ('K0', …, 'K4')"; 28 `stageb_train train --aux-extra A3D@v1` → argparse "invalid choice" rc 2. **28건 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c27\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider -q" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c27/pt tests`): EXIT 0, **1118 passed · 17 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1250 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 음성 대조 7종; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(행 138); `se2e_c1` 5/5. |
| 2 모델 | 충족(CPU) | CPU 스모크(N77), CPU 묶음의 단계 B·E-MA1b 시험 통과, 기준선 파일 블롭 불변. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 13 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c27`(20:24:03–20:27:57Z): `CLOSED_DONE` C5·C5' 1.0, 호출 42·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 20:22:07–20:22:43Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`(claim a_as_stabilizer). |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). HEAD 시작 7a02943, 끝 40895f8(S20 — 내가 만든 것 아님). 다른 에이전트 파일은 건드리지 않음.
- 파드 정리(`clean27.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 20:29:29Z): `tmp/r7c27`(480 MB), `tmp/carb.3XSIDJ`·`tmp/tmp6_gkzeeg`·`cache/pyc_r6/data/harvest/tmp/tmp6_gkzeeg`·`cache/pyc_r6/data/harvest/tmp/r7c27`, `ir/kitcache/cyclo-r7c27_standard`(208 MB). 끝에 r7c27 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c27이 든 프로세스 0, `IR_INST=r7c27` 프로세스 0, 열린 핸들 0. 탐침·E-MA1b·`se2e_confirm` 파일은 읽기만.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·게이트 시험 임시 폴더 삭제, 보고 근거 스크립트·출력(`check27.py`·`check27_out.txt`·`pod/`·`out/`)만 남김. 지시대로 `D:\tools\scratch_qdd\r7c25`(132 MB) 삭제.

## 7. 실험 코드 절 (별도 판정: FAIL — 코드 결함 0, DOC 2)

### 7.1 탐침 코드 행동 확인 (`check27` X, 파드 `exp27*.py`)
| # | 등록 값 (`prereg_astra_motion.md`) | 구현 | 확인 | 판정 |
|---|---|---|---|---|
| X0 | 프롬프트 판본 동결 `9b5c5c292765`(12절) | `prompts.PROMPT_ID` | 커밋 `prompts.py`로 계산 = `9b5c5c292765`; 파드 실행 사본 `code_astra_motion` 15/15파일 = 커밋 블롭(LF sha256), `prompts.py` 수정 17:45:04Z < 첫 G1 v2 유료 18:03:51Z; **유료 S2 장부 72/72행 `prompt_id` = `9b5c5c292765`**, Astra S2 결과 6/6 같음(G1·G2 행은 판본 필드가 없어 파일 시각으로 확인) | 일치 |
| X1 | 부드러운 실행기: 창 동안 일정 속도 = 배율 × delta / 창, 0.5 s 감쇠, 뒤집힘이면 0에서 새 경사, 가속 0.32 m/s², 속도 8 cm/s, 집기는 \|delta\|/8 cm/s(≥ 0.5 s) 뒤 바로, 같은 집기 요청은 첫 마감 유지(4.2절) | `executor.SmoothExec` | 일반 경사 최대 속도 0.00833·가속 0.0167(상한 안), 5 cm/0.3 s 요청 → 0.0800 m/s로 잘림, 감쇠 3.0→3.5 s 선형, 집기 마감 0.625 s, 반복 close 마감 유지·keep이 대기 집기 유지; **뒤집힘·집기 순간 한 틱 정지(가속 1.92·1.60 m/s²)** | 일치(E-N5) |
| X2 | 같은 명령 = 종류·집기·방향 35°; 뒤집힘 = 90° 넘음(6절, 4.2절) | `harness.same_command`, `opposite` | 34.9° 같음·35.1° 다름, 집기 다르면 다름, stop 대 hold 다름; 90.1° 뒤집힘·89.9° 아님 | 일치 |
| X3 | 뒤집힘율 = 도착 순 연속 유효 답 쌍 중 유효 명령이 다른 비율, 무효 답 건너뜀(6절) | `agg.stream_metrics` | 구성 입력 5유효·1무효 → 2/4 = 0.5, 근거 없는 뒤집힘 0.5(기대대로) | 일치 |
| X4 | **F1 채택 = F1 뒤집힘 ≤ 0.5 × F0 그리고 F1 성공 ≥ F0(7-1)** | `agg.f1_rule` | 0.297 = 0.5 × 0.594 → F1, 0.2971 → F0, 뒤집힘 반감이어도 성공 1 대 0이면 F0 | 일치 |
| X5 | **무효율 관문 = 단계 단위 > 10 %**(12절, 13절 정정) | `run.run` | 실제 러너를 스텁 세계·모델로: 편 2/10(20 %)·단계 2/64 → 멈추지 않고 6편; 단계 8/64(12.5 %) → `REDESIGN_STOP` 5편에서; 6/64(9.4 %) → 계속 | 일치 |
| X6 | 비용 = (입력 − 캐시) × $10 + 캐시 × $1 + 출력 × $50 / 1M × 1,450; 하드 정지 = 파일 전체 합 + 날아가는 호출 예약(12절, 13절) | `cost.cost_usd`, `Ledger` | 2,207/244 토큰 → 49.69원; 캐시 가격; 두 `Ledger`가 같은 파일을 볼 때 725 + 예약 100 + 200 > 1,000 → `BudgetStop` | 일치 |
| X7 | 편집 ≤ 5 cm·회전 ≤ 0.35 rad(3절) | `schema.validate` | 5.000 cm 유효·5.064 cm 무효, 0.35 유효·0.3501 무효 | 일치 |
| X8 | 유효 창 = 최근 3개 답 나이 중앙값, 처음 3 s, 1–8 s로 자름; 배율 50 %/100 %(4.2절) | `harness._stagger` | 가짜 세계 실제 흐름 12답: 창 = 규칙 값 12/12, 배율 규칙 일치 | 일치 |

### 7.2 탐침 원자료 재계산 (파드, 읽기만)
- **비용 장부** `logs/astra_motion/cost.jsonl` **256행**: API 설정 3(0원), 옛 G1 13(203.99원, 호출당 15.69, 지연 p50 4.20 s, 입력 507/657/811, 출력 73.0·추론 19.5), **G1 v2 160(2,682.00원, 16.76/호출, p50 3.45 s, 입력 588/738/892, 출력 75.7·추론 22.3)**, G2 high 8(223.46원, 27.93/호출, p50 5.79 s, 추론 64–289), S2 F0 45(2,244.73원, p50 9.32·p95 12.29 s, 입력 2,212.5·출력 245.5), S2 F1 27(1,579.19원, p50 10.33·p95 16.00 s, 2,487.4/309.3) → **합 6,933.37원**, 행마다 사용량으로 다시 계산한 비용과 차이 ≤ 3.5e-6 USD, 캐시 적중 0, `charged_max` 0, 오류 0, 최대 누적 6,933원 < 15,000원. S2 장부 72행 = 편 안 도착 66 + 끝난 뒤 도착 6(편마다 1).
- **정정 13절 "다른 점 2"(프로세스별 합계)**: 장부 `cum_krw`가 파일 누적과 어긋난 행 215개가 모두 18:04:26–18:15:23Z(G1 v2·S2 동시 실행 창, 최대 3,088.92원 차), 18:16Z 뒤 0 — 서술과 맞음.
- **"다른 점 1"(편 단위 관문)**: 러너 순서 s0 F0·F1, s7 F0·F1, s14 F0에서 단계 2/64(3.1 %)·편 2/10(20 %); 로그 `s2_astra.log`의 `REDESIGN_STOP {"invalid_share": 0.2}`, 수정된 `run.py`(파드 18:16:22Z) 뒤 `s2_astra_b.log` 18:21:34Z 재개(`--cap-krw 12500`) → s14 F1 — 서술과 맞음.
- **S2 흐름**(결과 JSON): Astra F0 뒤집힘 **22/37 = 0.5946**, F1 **8/21 = 0.3810**(커밋 `same_command`와 내 독립 구현이 같은 수), `agg.f1_rule` → **F0**; 무효 F0 2·F1 0, revise 15(확인 4·미확인 5), 확신 F0 medium 25·high 15, F1 22·2, low 0 → 불확실 → continue 0; 6 s 넘은 답 F0 0.697(s7 빼면 0.909·1.0), F1 1.0; 원/로봇 분 498.8·350.9; 성공 0/6, 실패 단계 approach 6/6. Qwen F0 31/86 = 0.3605, F1 4/85 = 0.0471.
- **G1 v2**(40장: 쥠 25·안 쥠 15, 상태 10 × 4): Astra 머리만 거짓 잡음 0/15·놓침 25/25·uncertain 39, 머리 + 오른손목 1/15·13/25, 셋 모두 0/15·13/25, + 덧그림 0/15·13/25; Qwen 0/15·25/25, 1/15·14/25, 7/15(pre 5)·4/25, 0/15·12/25. 덧그림 짝 24/10/3/3. 상태별 closed 7/10·grasped 5/9·miss-쥠 0/6·pre 10/10·miss-안 쥠 4/4. **G2 선정 규칙**(오답 수 많은 순·이름 순)을 G1 v2 Astra 답으로 다시 적용 → `g2_only.txt` 8장과 같음(모두 네 조건 오답); high 고침 2/8(s2·s3 grasped).
- **재생**: 부드러운 재생 6/6이 실시간 판과 경로까지 같음, 중앙 최대 속도·jerk RMS 0.0364·0.83 대 즉시 0.0948·2.355.
- **Qwen 동기 S 20편**: 성공 0/20, approach 20/20, 편당 28.95호출, 무효 9(1.6 %), 지연 p50 1.57 s, low 5 → continue 5, close 있는 편 **17**, 첫 close 오차 중앙 238.5 mm(close 없음 = ∞ 포함; close만 223.4 mm); oracle 7/7·nomodel 6/7(앞 7편). 옛 G1 Qwen 셋 모두 거짓 잡음 12/14(덧그림 켬·끔 각각), 진단 base 6/7(pre 4/4)·define 1/7·gray 6/7·order 5/7.
- **정본 §86·스펙 §17**: 위 값과 모두 맞다(§5 행 156).

### 7.3 E-MA1b 결과 (`results/ma1b.md` 대 `/data/harvest/logs/ma1b/`, 읽기만)
- 예측 파일 네 개를 독립 집계: 항목 5,397·스냅샷 1,799·키 집합 같음, 정답 3,814/3,831/3,819/3,836, 시드별 +17항목 = +0.00315, RB1 +0.0059(s1 +0.0061·s2 +0.0058), RB2 −0.0018 — `verdict_full.json`·결과 문서와 같음. 판정 파일: 합동 +0.00315, 하한 −0.00222, 구간 [−0.0022, +0.0085], 전이 0.0000 [−0.0071, +0.0072], 정상 +0.0088 [+0.0013, +0.0165], `adopt` 거짓, 규칙 상수(0.02·0·0.01·10,000·0·1e-12).
- **커밋 `ma1b_verdict.py`(7a02943 사본)를 같은 입력으로 다시 돌린 JSON = `verdict_full.json`(완전 동일).**
- **S22 (a) 기준 재사용 비트 동일**: `predfull_none_s{1,2}.jsonl` 대 `logs/se2e_confirm/predfull_motion_s{1,2}.jsonl` — 5,398/5,398줄이 `utc` 밖에서 같음(두 시드).
- **S22 (b) 실제 체크포인트 보기 검사**: `view300_trained` 대 `view300_base`(a3d_s1 `last/`) — 항목 900/900 `utc` 밖 동일, 요약 줄은 `aux`(0.5495 대 0.0)·`utc`만 다름.
- 보조 오차 9.9006/9.5376 cm, 중앙 6.39/6.62, 점별 5.06/9.29/11.94/13.32·4.96/8.96/11.46/12.77; 참고 변위 0 12.383 cm·학습 평균 12.435; 청크 MSE 0.0301(0.0298)·0.0317(0.0312); step 2000 dec_acc 0.6956·0.6967, aux 0.831→0.549·0.831→0.541; 학습 18:06:27–18:47:26·18:56:17–19:33:24(41.0·37.1분); `CODE_HASHES.txt`에 등록 해시; 등록 문서 sha256(LF) 앞 16 `7b4bff2c6e565a98` = `ma1b.md:3`.

### 7.4 DOC (실험 절)
- **E-D1. `docs/stage3/results/astra_motion.md` 수치 서술 3곳이 원자료와 다르다.** ① `:23` G1 v2 행 "영상 1장 약 507, 2장 657, 3장 811" — 장부 G1 v2 160행의 입력 토큰은 **588/738/892**(각 40·40·80행, 편차 0); 507/657/811은 옛 설계 G1 13행 값(쥠 정의를 넣은 새 프롬프트가 81토큰 김). ② `:24` S2 "72 (+ 끝난 뒤 도착 6)" — 장부 S2는 72행이고 그 안에 끝난 뒤 도착 6이 들어 있다(편 안 도착 66); 표의 "호출/편" 15.0·9.0도 끝난 뒤 도착을 포함한 값. ③ `:82` "(16편에서 close" — `qwen8b/S` 결과 20편 중 `first_close`가 있는 편은 **17**. **고칠 것**: ① 588/738/892, ② "72(끝난 뒤 도착 6 포함; 편 안 도착 66)", ③ 17편 — 같은 커밋에 책 `05-costs.md:14`·`:15`(N70)과 `06-updates.md` 한 줄, 결과 문서 정정 표시.
- **E-D2. 등록 13절 자체 점검(`prereg_astra_motion.md:135`)의 "S2(… Qwen 6편) … 모두 프롬프트 판본 `9b5c5c292765`"가 틀렸다.** Qwen S2 결과 JSON의 `prompt_id`: s0·s7 × F0·F1 4편 = **`a84e4c76efed`**(`s2_qwen.log` 시작 17:43:08Z, 결과 17:47–17:52Z — 수정 2(17:47:43Z)·프롬프트 동결(`prompts.py` 17:45:04Z) 전후의 무료 사전 실행), s14 2편만 `9b5c5c292765`(18:19–18:21Z). 결과 5절 표의 Qwen 흐름 줄(F0 0.360 → F1 0.047 "규칙 충족", 책 `01:60` 인용)은 두 판본이 섞인 값인데 표시가 없다(같은 편끼리의 F0·F1 짝은 판본이 같아 규칙 비교 자체는 짝 안에서 성립). Qwen 동기 S 20편과 Astra 유료 판은 모두 `9b5c5c292765`. **고칠 것**: 13절에 "[정정] Qwen S2 s0·s7(F0·F1)은 옛 판본 `a84e4c76efed`(무료 사전 실행 재사용), s14만 새 판본" 한 줄, 결과 5절 Qwen 줄에 같은 표시.

### 7.5 NOTE (실험 절)
- E-N1. (그대로) `ma1b_verdict.py`는 "검증 1,799에서만"을 강제하지 않는다(이번 재실행 `n_val_snapshots` 1,799).
- E-N2. (그대로) `cmd_predict`의 `json.dump(…, open(…))`.
- E-N3. (해소) S22 두 검사 — §7.3.
- E-N4. (그대로) a3d 점별 cm 4개.
- E-N5. 부드러운 실행기의 가속 상한은 경사에만 걸린다: 뒤집힘 재설정(`apply(flip=True)`)과 집기 동작 순간(`tick`의 `self.v = 0`)에 명령 속도가 한 틱(50 ms)에 최대 8 cm/s → 0(가속 1.6–1.9 m/s²). 등록 4.2절 문장("속도를 0으로 되돌린 뒤 새 경사", "이동을 빨리 한 뒤 바로 집기")과 맞지만 같은 절의 "속도 변화는 가속 상한 0.32 m/s²"와 함께 읽으면 모호하다. 실제 판에서 뒤집힘 1회·집기 사건 10회(s7 F0 9, s0 F1 1); 결과 6절 결론(부드러운 쪽 jerk가 더 작음)은 이 튐을 포함한 채로도 성립. 결과 6절에 "가속 상한은 경사에만" 한 줄 권함.
- E-N6. 창이 끝난 뒤 0.5 s 선형 감쇠 때문에 한 답의 실제 이동은 배율 × delta보다 v·0.25 s만큼 더 간다(창 3 s면 +8 %, 1 s면 +25 %; X1 2.729 cm 대 2.5 cm). 등록 문장대로이나 결과 문서에 적히지 않음.
- E-N7. 러너 무효율 관문의 단계 묶음은 `m.split("-F")[0] + "*"` — 모드 "S"면 `S*`(흐름 폴더 포함); `grasp` 명령에는 무효율 관문이 없다(G1 v2·G2 무효 0이라 영향 없음).
- E-N8. `agg.summarize`의 `stream_flips_pooled`는 편별 반올림(소수 3자리) 비율에 쌍 수를 곱해 합친다 — 정확한 22/37·8/21과 소수 3자리까지 같음.
- E-N9. 결과 3절 표의 "정답"은 "잡음 대 그 밖"의 이분법(uncertain을 '안 쥠' 주장으로 셈): Astra 머리만 15/40은 uncertain 39개 가운데 안 쥠 14개를 정답으로 센 값(확정 답으로는 1/40). 표 머리에 정의 한 줄 권함.
- E-N10. 반올림: 결과 2절 G2 "224원"(장부 223.46), "지연 p50 5.7 s"(5.79); `ma1b.md` 2절 a3d_s1 mag_coarse "0.652"(0.6515), none_s2 dir_z "0.811"(0.8105); 5절 "F0 약 36개" 쌍(37).
- E-N11. 결과 1절·등록 13절의 "S2 Astra low 6편 중 5편 + 재개 1편"·"두 유료 프로세스" 서술과 장부 시각이 맞다(§7.2).

## 8. 다음 순회 전에 할 일 (제안)
1. **D-1(기준선)**: 책 `04-map.md:61` 괄호를 시각 없는 생성 계획 또는 시각을 붙인 상태로 고치고 같은 커밋에 `06-updates.md` 한 줄. 책에 "지금·현재"를 쓸 때는 확인 시각을 붙인다.
2. **실험 절 E-D1·E-D2**: 결과 `astra_motion.md` `:23`·`:24`·`:82`와 책 `05:14`·`:15`(N70), 등록 13절·결과 5절 Qwen 판본 표시 — 한 커밋에(정정 표시 + 06 줄 + handoff·draft-log·direction-log 기록 줄).
3. (선택, NOTE) N54(P04 표시를 칸 안으로), N66(`01:38` 표시 위치), N67(`01:38` 1–26회차), N68(시각), N71(§85 보충 위치), N72(책 03 §85 보충 줄), N73·N74(정본 `:563`·스펙 `:123`–`:185` 꼬리표), N79(계획 `:21`·`:65`·`:68` 꼬리표와 `timeout_s`), E-N5·E-N6·E-N9 한 줄씩.
4. 28회차 대상은 7a02943 이후 HEAD, **연속 무결 0에서**. E-CAM3·E-MA3이 커밋되면 범위 나눔(실험 절)을 다시 정할 것. Git Bash kubectl은 `MSYS_NO_PATHCONV=1`, 문서는 archive 사본에서 읽는다.
