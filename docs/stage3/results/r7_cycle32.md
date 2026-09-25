# R7 객관 검증 순회 — 32회차 (cycle 32, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle31.md`의 표·결론을 근거로 쓰지 않고 4c532d2의 바뀐 줄마다 diff·원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드는 **21–31회차와 다른 새 값**. 작성 2026-09-25 22:35 UTC 무렵(로컬 사본 풀기 22:14:29Z, 파드 첫 명령 22:15:00Z, 파드 정리 끝 22:31:18Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`4c532d2`**(`4c532d2aa8ca52d4ff2473f8c798a2119d903986`, 커밋 시각 2026-09-26 07:12:05 +0900 = **2026-09-25 22:12:05 UTC**, "R7 cycle 31 baseline PASS (clean count 1) — records, handoff §0 R2_TRAIN/R7 lines, book 01 R7 row name without range (N128)"). `ac7a314..4c532d2` = 커밋 1개, 6파일(문서만: 책 01·06, draft-log, handoff, direction-log, 새 `r7_cycle31.md`), **코드·시험·정본·사전 등록 변경 0**(`check32` H1). 검토 중 `dev`에 뒤 커밋 `76ab10c`(E-CAM3·E-MA3 결과)가 올라왔으나 **범위 밖 — 열지 않았다**. 작업 트리에는 이 보고서만 추가.
- **범위 나눔(31회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책 `docs/book/`. **실험 코드 절**(따로 판정) = 4c532d2 이전에 커밋됐으나 아직 검토하지 않은 실험 쪽 변경 — **없음**. E-CAM3·E-MA3 결과는 4c532d2에 없다(`git ls-tree 4c532d2 docs/stage3/results/`에 cam3·ma3 0) → **범위 밖**, 예측·평가 파일은 열지 않았다.
- 사본: `git -c core.autocrlf=false archive 4c532d2`(tar 주석 = `4c532d2aa8ca…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c32\repo`에 풀었다(**593파일** = 31회차 592 + `r7_cycle31.md`, 텍스트 509파일 CR 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c32/code`(594파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `4c532d2aa8ca…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle31.md`, 정본 `00-interfaces.md` §1–§86 보충(`:778`, 뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5(`:9`–`:14`), 사전 등록(`prereg.json` E-first §2.7·2A.6·3.7·4.8·5.6 해시, `prereg_labeler/se2e/se2e_diag/se2e_temporal/se2e_motion_confirm/astra_motion/ma1/ma1b/cam3/ma3.md`), 결합 설계 스펙 §12·§17, 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P69.
- 분류(31회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0의 줄은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약, 추정 표시가 있는 수치, 반올림 차이, 시각이 붙은 이력 표시는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c32`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음; 31회차 스크립트는 읽기만 하고 새로 썼다). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c32`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c32_standard`, `--inst-prefix r7c32`); GPU 2·3에는 아무것도 올리지 않음(검토 내내 0 MiB); R2_TRAIN `final_check.sh`/`gen check`(PID 1277833·1277838)는 읽기만(`ps`·`stat`·로그 머리 줄). CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **FAIL — DOC 2** (연속 무결 1 → **0**)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 21 |
| NOTE | 109 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — 검토할 새 실험 쪽 변경 없음, 코드 결함 0, DOC 0**

**기준선 코드는 31회차 대상(ac7a314)과 바이트가 같고 모든 동작 검사가 통과했다**: 로컬 **1133 passed / 20 skipped**(226.3 s), 파드 CPU **1280 passed / 4 skipped**(163.6 s), LeRobot 6 passed; 가드 **28건 + 실험 옵트인 4건 + 추가 1건 = 33건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–31회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 대조 12종**(통과해야 할 경계 4종 통과, 검출해야 할 8종 모두 검출) + 관찰 3종; 실데이터 일관성 훑기(DEV 36편 10,651프레임 + R2_TRAIN 300편 91,474프레임: 결정 표지 불일치 0·시각 비유한 0·격자 이탈 0·행 seed/kind 불일치 0); 모의 평가 한 명령씩 완료; 새 시드 **DEV 19**에서 같은 Isaac 워커 C5 → C5' 행동 **4,000개 비트 동일**. **실패 원인은 문서 두 줄**: handoff §0 R2_TRAIN 줄이 자기 확인 시각(22:11 UTC)에 이미 틀렸고(D-1), 책 01 R7 행이 회차 범위를 handoff §2.8로 넓히면서 같은 커밋의 31회차 PASS를 빠뜨렸다(D-2).

---

## 1. DEFECT

없음. (4c532d2는 코드·시험·정본·사전 등록을 바꾸지 않았다 — `git diff --name-status ac7a314 4c532d2`에 `harvest/`·`tools/`·`tests/`·`docs/design/`·`prereg*` 경로 0, `check32` H1.)

## 2. DOC

- **D-1. `docs/handoff.md:11` §0 R2_TRAIN 줄 — 확인 시각 22:11 UTC에 이미 거짓인 문장.** 줄: "(확인 2026-09-25 22:11 UTC, 파드 `ps`·`TZ=UTC ls`) … `gen check`(`final_check.sh`)가 21:57Z부터 실행 중. **폴더의 `P*.stageb.jsonl`·`check.json`은 아직 12:19:47–12:20:26 UTC 파일럿 병합분**". 파드 원자료(`r2detail32.sh`, `TZ=UTC stat`): `final_check.sh`가 부르는 `gen check`는 "validate + stamp + **merge every folder**"(`final_check.sh:2` 주석, `harvest/datagen/gen.py:365`–`:392` — 폴더마다 검증·도장 뒤 바로 `merge(folder)`)이고, `episode.merge()`(`episode.py:112`)는 `open(…, "w")`로 제자리에 쓴다(이름 바꾸기 없음 → mtime = ctime = 쓰기 끝). 22:11 UTC 이전에 이미 다시 병합된 폴더 행 파일 **6개**: `dr/bottle_tray/P0·P1·P2.stageb.jsonl` 22:01:16Z·22:02:34Z·22:03:15Z(413.6·136.3·136.0 MB), `dr/mug_marker/P0·P1·P2` 22:06:55Z·22:08:07Z·22:08:51Z(690.9·226.0·229.8 MB), 같은 시각의 `P*.labels_v2.jsonl` 6개. 내용도 전체 병합: `gentime32.py` — `dr/bottle_tray/P1` 34,004행 = 유효 112편 편별 행 합 34,004(마지막 행 seed 10799), `dr/bottle_tray/P2` 33,951 = 117편 합(마지막 seed 10999), `dr/mug_marker/P2` 57,650 = 200편 합(마지막 seed 10999). 22:11에 파일럿분이었던 것은 `check.json`(12:20:26Z)과 나머지 12개 행 파일뿐이었다(그 뒤 `dr/mug_tray` 3개도 22:12:18–22:14:17Z에 다시 병합; 22:15Z 기준 standard 9개만 파일럿분). 같은 줄의 나머지 사실은 참: 생성 끝 21:56:26Z(`gentime32.py`: P2 마지막 `.npz`·`.jsonl` 21:56:26Z `dr/mug_marker/P2/ep10999`, P0 18:08:13Z, P1 20:02:13Z; `gen check`가 `.meta.json`을 다시 도장하므로 meta mtime이 아니라 npz·jsonl mtime으로 확인 — N148 ③), 폴더마다 P2 항목 602(= ep 200편 × jsonl·meta·npz 3 + `img`·`rows`, 6폴더 모두), `final_check.sh`·`gen check` 시작 21:57:31Z·실행 중(22:31Z에도 `check.log` = `CHECK_START 21:57:32Z`만). 단계 B에 쓰지 말라는 결론은 여전히 안전하지만 확인 시각의 사실 서술이 원자료와 다르고 정정 표시가 없다(28회차 D-1과 같은 모양 — R2_TRAIN 행 파일 상태 서술 오류). **고침**: 행 파일 상태를 파일별로 적지 말고 "`gen check`가 폴더 순서대로 검증·도장·다시 병합 중(확인 HH:MM UTC: 다시 병합된 폴더 N/18, `check.json`은 파일럿분 — `check.json`은 모든 폴더 뒤에 한 번 씀) → `final/check.log`에 `CHECK_EXIT 0`·`FINAL_DONE`이 찍히고 행 수·시드 범위를 확인하기 전에는 단계 B 학습에 쓰지 않는다"처럼 확인 명령(`TZ=UTC ls -l --time-style=+%FT%TZ`)과 함께 새 확인 시각으로 적는다.
- **D-2. `docs/book/01-experiments.md:38` R7 행 — 범위를 넓히며 31회차 PASS를 빠뜨림.** 4c532d2가 행 이름을 "R7 객관 검증 1–29회차" → "R7 객관 검증(**회차 범위는 handoff §2.8**)"로 바꿨다(N128 반영). handoff §2.8은 이 커밋에서 1–31회차 줄을 갖고(`handoff.md:136` "R7 31회차 … 기준선 PASS"), 같은 커밋이 `r7_cycle31.md`(판정 **PASS**)를 더했다. 그런데 결과 칸은 그대로 "**6·16·20·22회차 PASS, 나머지 FAIL**" → 이제 범위 안의 31회차를 FAIL로 말한다. 기계 확인(`check32` H10): 보고서 31개의 첫 "## 판정" 줄 — PASS **[6, 16, 20, 22, 31]**, FAIL 나머지 26개. 26회차 D-1("6회차 PASS 누락")과 같은 모양. 31회차 N128이 NOTE였던 것은 범위가 1–29로 닫혀 있어 적힌 사실이 참이었기 때문인데, 범위를 여는 순간 목록을 같은 커밋에서 갱신해야 했다(README `:10` 갱신 규칙, P05). **고침**: `01:38` 결과 칸을 "6·16·20·22·31회차 PASS, 나머지 FAIL(…)"로(32회차 FAIL 반영 여부는 그 커밋의 §2.8과 맞춤) — 또는 매 회차 갱신이 필요 없게 "PASS 회차와 판정은 handoff §2.8 줄마다; 8회차 DEFECT 5 등"으로 목록을 빼고, 06에 한 줄.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 생성 끝(P0 3,600·P1 1,200·P2 1,200편, npz·jsonl 기준 마지막 18:08:13Z·20:02:13Z·21:56:26Z), `gen check` 실행 중(21:57:31Z–, 22:31Z 미완). 확인 인자 없는 `--seeds 10001` 거부(가드 19).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 4c532d2에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. 정본 §82 구현(`:730` "R7 관문(연속 무결 2회) 확인 뒤 착수") 및 §84·§86(+보충) 결합 설계 구현(`:747` "R7 E2E 준비 기준점 뒤") — 지금 코드: `closed --hb-mode k3`·`K1,K4`(예산 없음) → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 19 Astra 10행), 흐름 호출 없음.
- S19. 정본 §83 런타임 적용(`:740` "R7 관문 뒤") — DEV 19 결정 호출 요청 244/244 `motion:` 없음.
- S20. **E-CAM3·E-MA3 결과**: 4c532d2에 결과 없음. 파드에서 본 것: 22:15:00Z부터 GPU 2·3 = 0 MiB, `se2e_*` 프로세스 0(이름·메모리만). 뒤 커밋 `76ab10c`는 범위 밖, 열지 않음.
- S21. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3, N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45, N46, N49–N53, N57, N58, N71, N73, N74, N79, N90, N91, N94, N129, N131–N138. (그대로, 31회차 목록.) N10 재현: 가드 25(`e05 --data jsel_dev/P2 --split pool --seeds 2100` → "no episode selected")가 빈 `g25/`를 남김. N94: 이제 `gen check`가 병합 중(D-1).
- N4, N47, N48, N54–N56, N66–N70, N72, N84–N88, N92, N93, N102–N108, N116–N122. (해소, 31회차와 같음.)
- N109–N115, N123–N127, N133–N138. (이전 회차 자체 기록 — 이번 회차 새 NOTE는 N139–N149; 31회차 100 − 해소 2(N128·N130) + 새 11 = 109.)
- **N128.** (해소 — 그러나 D-2) 행 이름에서 범위를 뺐다(`01:38`), 06 `:23` 줄 ✓.
- **N130.** (해소) handoff §0 R2_TRAIN 줄이 "생성 끝"으로 갱신됨 — 다만 그 줄의 병합 서술은 D-1.
- **N131·N132.** (그대로 NOTE — 태그 뒤 고침은 메인 결정대로) 재분류 검토: 완료 정의 1은 "생성기·검증기·소규모 샘플 통과"(`e2e-ready.md:10`)이고 `r2_datagen.md:55`의 검사 목록은 "확인 목표 존재"다. 검증기는 확인 목표를 줄의 `decision` 표지로 고른다(`validate.py:78`; 라벨 검사는 `:75`–`:77`의 `is_decision`) — 이 차이가 실데이터에 영향이 있는지 직접 훑었다(`data32.py` SCAN): R2 DEV 36편 10,651프레임과 R2_TRAIN 300편 91,474프레임(standard/mug_tray/P2·dr/bottle_tray/P1·dr/mug_marker/P0 각 앞 100편)에서 `bool(decision) != is_decision(k)` **0**, 그러니 검증기가 실제로 모든 결정 프레임의 확인 목표를 봤다. N132(`grip` 키 없으면 KeyError)는 크게 실패해 조용히 통과하지 않는다. → 사전 등록 동작·완료 정의를 깨지 않음, NOTE 유지.
- **N139.** handoff §2.8 31회차 줄(`:136`) "보고 2026-09-25 22:07 UTC 무렵", draft-log `:482` "22:07 UTC 무렵", direction-log `:78` "22:07" — `r7_cycle31.md:3`은 "작성 2026-09-25 22:09 UTC 무렵(… 파드 정리 끝 22:07:14Z, 로컬 정리 22:08:00Z)". 29회차 N103(28회차 줄 '보고 21:02' = 파드 정리 끝)과 같은 모양 — "무렵"이 붙은 근사, NOTE. 나머지 값(대상 ac7a314, DEFECT 0·DOC 0·SCOPED 21·NOTE 100, 실험 절 PASS, 연속 무결 1, 40칸·32줄)은 보고서와 모두 같다 ✓.
- **N149.** (위치 표기만 어긋남) handoff `:136`의 "검증기 `validate.py:73`(… `decision` 표지 …, N131)·`:76-79`(npz에 `grip` 없으면 KeyError, N132)"는 `r7_cycle31.md:94`–`:95`에서 옮긴 줄 번호인데, 4c532d2(=ac7a314, `validate.py` 마지막 변경 `6111b4e`)의 실제 위치는 결정 표지 검사 `:78`, 라벨 검사 `:75`–`:77`, npz 키 고리 `:82`–`:85`(KeyError는 `:83` `z[key]`)다. 내용은 맞고 번호만 약 5줄 어긋남 → NOTE. 태그 뒤 고칠 때 이 번호로.
- **N140.** handoff §0 E-CAM3·E-MA3 줄(`:12`) "학습 중(확인 21:02 UTC …)"은 확인 시각이 21:02로 남아 있고 머리 "마지막 갱신 22:12"와 함께 읽힌다. 확인 시각에 참(30회차 확인)이라 규칙상 낡음 아님; 22:15Z에는 GPU 2·3 = 0 MiB·학습 프로세스 0(31회차 S20: E-MA3 학습 22:06Z 전에 끝). 다음 갱신 때 확인 시각을 새로 하거나 결과 커밋(범위 밖 `76ab10c`)과 함께 README 규칙대로 줄을 지운다.
- **N141.** 책 `04:61`의 정정 괄호 "폴더의 `P*.stageb.jsonl`은 12:20Z 파일럿 병합분(…)이다 [… 21:30·21:50 UTC …]"는 시각이 붙은 정정 이력이라 NOTE지만, 22:01Z부터 폴더 행 파일이 다시 병합되고 있어(D-1) 현재형으로 읽으면 이미 일부 거짓이다. 병합·검사 결과를 커밋할 때 같은 커밋에서 정리하고 06 한 줄(31회차 §8 ②와 같음).
- **N142.** (검증기 관찰, 음성 대조 `tnan`) 가운데 프레임(k145)의 `t`를 NaN으로 바꾸면 오류 0으로 통과한다: `validate.py:49`의 `max(abs(ln["t"] - tick_time(k)))`에서 NaN은 비교가 늘 거짓이라 첫 자리가 아니면 최댓값이 되지 못하고, `hold_n` 검사(`:86`)는 첫·끝 프레임 시각만 쓴다(npz `t`의 유한 검사는 따로 있음). 실데이터 훑기에서 비유한 시각 0·격자 이탈 0 → 위험 낮음. 권함: `math.isfinite` 검사 한 줄(N131·N132와 같이 태그 뒤).
- **N143.** (검증기 관찰, `rowseed`·`phasenull`) 행 `seed`를 다른 값(3 → 4)으로 바꾸거나 `phase_id`를 null로 해도 통과한다(`check_row`는 필드 존재만 봄). 실데이터 행 seed·kind 불일치 0. NOTE(권함: 행 seed = 편 seed 검사).
- **N144.** 텍스트 위생(`check32`): 사본 텍스트 509파일 CR 0; 변경 md 6개 BOM·CR·C0·C1·영폭 0, 표 칸 수 불일치 0(H3); 책 링크 101개 끊김 0(H4); 4c532d2는 책 01·06을 바꾸고 06 `:23` 한 줄("2026-09-25 22:12 | 01 | R7 행 이름에서 회차 범위를 뺌 …")을 더했다 — 22:12 ≤ 커밋 22:12:05Z ✓, 바뀐 책 장 = 01 ✓(H5). handoff 머리 "마지막 갱신 22:12 UTC" ✓, §0 R7 줄 "(확인 22:12 UTC): 31회차 기준선 PASS(연속 무결 1) → 32회차가 PASS면 … 태그" ✓. 책 01 상태 칸 기계 검사(H11): 상태 칸 있는 표 3개(`:9` 7칸 20행·`:42` 8칸 9행·`:58` 5칸 11행; `:34` 표 B는 상태 칸 없음) 상태 칸 **40개** — `끝` 32·`` `[결과 전]` `` 3·`` `[예정]` `` 5, 벗어난 칸 0, 칸 수 불일치 0. 현재형 진행 상태 검색(H9, `실행 중|병합 중` 추가) — 02·06 이력 인용, README·01·04 규칙·안내 문장, `01:38` "(아직)", `03:13`·`03:62` "실행 중 흐름/Astra effort"(결정 내용), `04:22`·`04:48` "현재"(판본)뿐.
- **N145.** 시험 수: 로컬 **1133 passed / 20 skipped**(226.3 s, 22:14:35–22:18:22Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c32/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(163.6 s, 22:20:01–22:22:47Z), 경고 1(기존), LeRobot 6 passed(17.0 s). 31회차와 같은 수(코드 무변경). 로컬 `tools/prereg_hash.py --check` → OK, `tools/intent_check.py` → flagged 0.
- **N146.** 단계 B 소형 CPU 스모크(22:24:57Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–31회차와 같은 값 — 결정적), expert p50 0.040 s·전체 p50 0.114 s, 맥락 토큰 454.
- **N147.** DEV 19 판: 행동 4,000·40.0 s(`--max-seconds 40` 상한, `terminations` max_steps 1 — 성공·낙하 없음), 결정 호출 122(조건마다), C5 `last_step` {none 1, OK 15, LAG 6, DEVIATE 100}, C5' none 122/122, 확정 비율 0.223, 결정 3.051/s, rtf 0.532, 지연 p50·p95 0.3 s, Astra 5(hb 5.0/16.01/24.01/32.01, sub 8.01 → 11.01, 겹침 0), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28–31회차와 같음), 파일명 `dev19-P0-standard-e0`, 판 286.5 s(22:25:43–22:30:30Z). 파드 GPU 전·후 모두 0 MiB(0–3).
- **N148.** (절차, 자체 점검) ① 가드 12·13(`--isaac-gpu 10`·`0x1`)은 `closed.py:391` 문자열 검사가 워커 실행 전(`:377`–`:392`)임을 읽고 골랐고 `CUDA_VISIBLE_DEVICES=""`로 돌렸다. 처음 떠올린 `--hb-mode K4 --hb-budget -5`는 예산 부호 검사가 없어(`:387`은 None만 봄) 워커가 뜰 수 있어 버리고 `"K1,K4"`(예산 없음)로 바꿨다. 옵트인 가드 31을 `se2e_kvcond train --aux-extra`로 하려다 그 거부가 데이터 적재·모델 생성 뒤(`se2e_kvcond.py:238`–`:243`)라 GPU·긴 적재 위험 → argparse 단계 값(`KVCOND@v1`)으로 바꿨다. 추가 가드 33(`--m4-h 0`)은 새 종류. ② 음성 대조 원본은 dr 변형의 **두 번째** 유효 편(`dr/bottle_tray/P0` ep3, 291프레임 — 28회차 첫 dr, 29회차 마지막 standard, 30회차 마지막 dr, 31회차 두 번째 standard와 다름). 처음 설계한 `kstr`(프레임 k를 문자열로)는 `tick_time` TypeError로 검증기가 예외를 던질 뿐 규칙 확인이 안 돼 `labsempty`로 바꿨다. ③ R2_TRAIN "생성 끝 21:56:26Z" 확인을 31회차처럼 `ep*.meta.json` mtime으로 하려 했으나 `gen check`가 meta를 다시 도장해(22:01–22:15Z) 첫 출력(`epoch32.py`)은 생성 시각이 아니었다 → npz·jsonl mtime(`gentime32.py`)으로 다시 설계. ④ LeRobot 새 3편: standard/mug_tray/P0 ep2·dr/mug_marker/P0 ep4 참, standard/bottle_tray/P0 ep2 거짓(28·30·31회차와 겹치지 않음). ⑤ 정리 스크립트의 자기 매칭은 `grep 'r7c[3]2'`로 피했다.

---

## 5. 사전 등록 대조표 (원 등록 문서에서 다시 만든 행, 행마다 이번 회차의 행동 확인)

`prereg.json` 해시(E-first §2.7·2A.6·3.7·4.8·5.6): 로컬 `prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = OK. 사전 등록 md 10개·정본·계획은 ac7a314와 같다(H1). 기준선 코드 = ac7a314와 같음. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c32\check32.py`(H1·H3·H4·H5·H9·H10·H11), **파드** = §6(`pod_cpu32.sh`, `pod_eval32.sh`·`data32.py`·`gtxt32.sh`·`lr32.sh`, `pod_isaac32.sh`·`closed32.py`, `who32.sh`·`r2state32.sh`·`r2detail32.sh`·`epoch32.py`·`gentime32.py`, `attr32.sh`·`clean32.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV 0–29/CAL 500–549/TEST 1000–1149/TEST-P5 1300–1329/POOL 2000–2119/R2_TRAIN 10000–59999 (E :113-120, §66, 책 `04:61`) | `eval/splits.py`, `datagen/gen.py` | 가드(§6.4): TEST 1037·1062, CAL 531·512, TEST-P5 1317, DEV 28,31·499, POOL 2135, gen 10001(확인 없음)·9997·65000(확인 있음), determinism 1024·29,2120, 다른 분할 허용 2건(17·18) → 모두 거부 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | `calib --heldout jsel_dev/P2 --episodes 3` → `CALIB_DONE`; 가드 3(`--fit-split test_p5`)·4(`--heldout-split cal`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | DEV 19 C5·C5' `--max-seconds 40` 상한에서 40.0 s·4,000스텝 `max_steps` 종료(성공·낙하 없음 — 상한 규칙대로), 두 조건 같음 | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 19 결정 호출 244행**(조건마다 122): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 244/244; Astra 10행 해시·effort low·600·이미지 1장·`output_text` 10/10 | 일치 |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P2 --split dev --episodes 3` → `E05_DONE`(claim `insufficient_data`); 가드 24(`canary build-set --data P1 --seeds 3175-3176`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H`·`m4_lead_max` 3·1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,C11"` → "condition 'C11': runtime has ['C0' … 'C6']", 가드 33 `--m4-h 0` → "M4 H = 0 … >= 1"; **DEV 19 C5 `last_step` {none 1, OK 15, LAG 6, DEVIATE 100}, C5' none 122/122, 요청 본문 마지막 `last_step:` 줄 = 행 값 244/244** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P2 --episodes 2` → `RD_DONE`(dr 낙폭 평균 0.0, n 275); 가드 5 `rd --variants dr=gen_dev/dr/P2 --split cal` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-1e-9` → "lead_max = -1e-09 … finite > 0 s", 15 `=1e309` → "lead_max = inf … finite > 0 s", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(22:31Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2012,2074,2109 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 19, 22:25:43–22:30:30Z)**: 행동 **4,000개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 122·Astra 5 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | 생성 끝 21:56:26Z(npz·jsonl), `gen check` 실행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119"(폴더 없음); 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 10`·`0x1` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 19 hb 5.0 → 8.0, sub 8.01 → 11.01, hb 16.01·24.01·32.01, 겹침 0; 가드 26 `k3`·27 `K1,K4`(예산 없음) 거부 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 3편 입력**(standard/mug_tray/P0 ep2·dr/mug_marker/P0 ep4 참, standard/bottle_tray/P0 ep2 **거짓**): 내보낸 편 2·556프레임(261 + 295, 무효 편 건너뜀 ✓), `verify` 오류 0·PSNR 최소 35.05 dB·lerobot 0.3.3 적재 556프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1, `r2_datagen.md:55`) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 대조 12종**(dr/bottle_tray/P0 ep3, 291프레임): 무수정 오류 0; 행 k87 `aux {}` → 오류 0; 행 k174 `committed {}` → 오류 0; 모든 행에 여분 필드 → 오류 0; 행 k130 `hz "30"` → "hz 30 != 30"; 행 k43 `action_script` 14단계 → "shape (14, 8), expected (15, 8)"; 행 k246 `proprio.tau` 삭제 → "proprio.tau: 7 values"; 프레임 k145 머리 경로 → 없는 파일 → "missing cam_head" + "images 581 != …"; npz `action` 한 줄 추가 → "length 292 (want 291)"; 행 파일 비움 → "stageb rows are not one per non-terminal frame"; 라벨 파일 비움 → "labels_v2 rows != decision frames"; npz `grip` 끝 값 삭제 → "npz grip: length 290". 관찰: `tnan`·`rowseed`·`phasenull` 오류 0(N142·N143). 실데이터 훑기 불일치 0(N131) | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 19 Astra 10행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 이번 대상에 새 유료·GPU 실험 등록 없음 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 코드 변경 0(H1); 가드 28(`--aux-extra a3d` → argparse "invalid choice") | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 상태 칸 40개 기계 검사 0 벗어남, 링크 101개 끊김 0, 06 갱신 줄 ✓; **`01:38` PASS 목록이 31회차를 빠뜨림** | **불일치 → D-2** / NOTE N141 |
| **156** | 정본 §86 = 탐침 결과 + §86 보충(`:778`) | — | 정본 무변경(H1) | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond`, … | 코드 무변경; 옵트인 가드 29(`train --data pool` → "--data se2e only")·30(`predict` 움직임 줄 없음 → "with the motion line")·31(`KVCOND@v1`)·32(`cam3@v0`) 거부; 결과 4c532d2에 없음(S20) | 일치 |
| **158** | handoff §0 = 확인 시각에 참인 진행 상태(README `:11`, P69) | — | R2_TRAIN 줄의 병합 서술이 22:11에 거짓(§6.2) | **불일치 → D-1** |

### 5.1 31회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드), 5·6·51–58·99·137·151(DEV 19), 13–17·61–62(jsel_dev/P2·gen_dev/dr/P2), 2–4(jsel_dev/P2), 66–67(`-1e-9`·`1e309`), 98(POOL 2012·2074·2109), 101(npz·jsonl mtime), 138(다른 세 편), 139(새 대조 12종 + 관찰 3종 + 실데이터 훑기), 155(D-2), 158 새 행(D-1).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status ac7a314 4c532d2`: M 책 01·06, draft-log, handoff, direction-log; A `r7_cycle31.md`. 코드·시험·정본·사전 등록 0. 책 01 = 1줄(`:38` 행 이름), 06 = +1(`:23`), handoff = 머리(`:3`)·§0 두 줄(`:11`·`:13`)·§2.8 +1(`:136`), draft-log +1(`:482`), direction-log +1(`:78`).

### 6.2 바뀐 줄마다 대 원자료 (4c532d2)
| 바뀐 줄 | 원자료·원 문서 | 판정 |
|---|---|---|
| handoff `:11` R2_TRAIN "(확인 22:11 UTC) P0·P1·P2 생성 끝(21:56:26Z; 폴더마다 P2 항목 602)" | npz·jsonl 마지막 21:56:26Z(`dr/mug_marker/P2/ep10999`); P2 6폴더 `ls -A` = 602(200 × 3 + `img`·`rows`) | 맞음 |
| 같은 줄 "`gen check`(`final_check.sh`)가 21:57Z부터 실행 중" | PID 1277833 `./final_check.sh`·1277838 `gen check` 시작 21:57:31Z, `check.log` `CHECK_START 21:57:32Z`, 22:31Z에도 실행 중 | 맞음 |
| 같은 줄 "폴더의 `P*.stageb.jsonl`·`check.json`은 아직 12:19:47–12:20:26 UTC 파일럿 병합분" | `check.json` 12:20:26Z ✓; 행 파일 dr/bottle_tray·dr/mug_marker 6개는 22:01:16–22:08:51Z에 전체 병합(행 수 = 유효 편 합) | **틀림(D-1)** |
| handoff `:13` R7 "(확인 22:12 UTC): 31회차 기준선 PASS(연속 무결 1) → 32회차가 PASS면 … 태그. 기준선 코드(검증기 N131·N132 등)는 태그 전까지 바꾸지 않는다" | `r7_cycle31.md:11` PASS·1 ✓; 22:12 ≤ 22:12:05 ✓ | 맞음 |
| handoff `:3` "마지막 갱신 22:12 UTC" | ≤ 커밋 22:12:05Z ✓ | 맞음 |
| handoff `:136` 31회차 줄 | 판정 표 0·0·21·100, 실험 절 PASS, 40칸·32줄, N131·N132 위치 ✓; "보고 22:07 무렵" 대 머리 22:09(N139) | 맞음(N139) |
| draft-log `:482` "22:07 UTC 무렵 … R2_TRAIN 생성 끝(21:56:26Z), 병합·검사 실행 중" | 22:07에 `gen check` 실행 중이고 병합도 시작됨(22:01:16Z부터) ✓ | 맞음(N139) |
| direction-log `:78` "22:07 \| R7 31회차 \| 결함 0 · 문서 0, 상태 칸 기계 검사 통과 \| PASS → 연속 무결 1" | 칸 수 4 ✓, 내용 ✓ | 맞음(N139) |
| 책 `01:38` 행 이름 "R7 객관 검증(회차 범위는 handoff §2.8)" + 결과 칸 "6·16·20·22회차 PASS, 나머지 FAIL" | §2.8 = 1–31회차; 보고서 판정 PASS [6, 16, 20, 22, 31](H10) | **틀림(D-2)** |
| 06 `:23` "2026-09-25 22:12 \| 01 \| R7 행 이름에서 회차 범위를 뺌 …" | 바뀐 책 장 01 ✓, 22:12 ≤ 22:12:05 ✓ | 맞음 |

### 6.3 기록책 (4c532d2 사본에서)
- 상태 칸 기계 검사: N144(40칸, 벗어남 0). 현재형 진행 상태: 없음(N144). 수치: 바뀐 숫자 없음(`01:38` "8회차 DEFECT 5" = `r7_cycle8.md:13` ✓). 링크 101개 끊김 0. 남은 것: `01:38` PASS 목록(D-2), `04:61` 정정 괄호(N141).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 22:23:17–22:23:34Z, 21–31회차와 다른 값; 사유는 `gtxt32.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data P0 --split test --seeds 1037`, 2 `e05 --data P2 --split cal --seeds 531`, 3 `calib --fit-split test_p5 --heldout P1 --heldout-split dev`, 4 `calib --fit-split pool --heldout P2 --heldout-split cal`, 5 `rd --variants dr=gen_dev/dr/P2 --split cal`, 6–8 `closed --split test --seeds 1062`·`cal 512`·`test_p5 1317` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 28,31` → "seeds [31] are not in split dev", 10 `pool --seeds 2135`, 11 `dev --seeds 499` → "not in split … (refused, never opened)"; 12–13 `--isaac-gpu 10`·`0x1` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-1e-9`, 15 `=1e309` → "lead_max = -1e-09 / inf … finite > 0 s"; 16 `--conditions "C5,C11"` → "condition 'C11': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=test` + `closed --split test_p5 --seeds 1305`, 18 `=test_p5` + `e05 --data P2 --split cal --seeds 538` → 거부; 19 `gen --seeds 10001`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9997 --confirm-train`, 21 `--seeds 65000 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 1024`, 23 `history --seeds 29,2120` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P1 --seeds 3175-3176`, 25 `e05 --data P2 --split pool --seeds 2100` → "no episode selected"; 26 `--hb-mode k3` → "from ('K0', …, 'K4')", 27 `--hb-mode "K1,K4"`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 train --data pool --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 predict --data se2e --cam3 cam3@v1`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)", 31 `se2e_kvcond predict --expert-cond KVCOND@v1`, 32 `se2e_cam3 evalck --cam3 cam3@v0` → argparse "invalid choice" rc 2. **추가**: 33 `closed --m4-h 0` → "M4 H = 0: decision steps per call must be >= 1". **33건 모두 rc ≠ 0**(28·31·32 rc 2, 나머지 rc 1); 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c32\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c32/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 12종(+관찰 3) + 실데이터 훑기(DEV 36·R2_TRAIN 300편 불일치 0); LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀, 행 138); `se2e_c1` **5/5 OK**. (R2_TRAIN 폴더 병합은 `gen check`가 진행 중 — D-1·N94; 완료 정의 1은 R2 DEV 기준.) |
| 2 모델 | 충족(CPU) | CPU 스모크(N146), CPU 묶음의 단계 B·E-MA1b·E-CAM3·E-MA3 시험 통과, 기준선 코드 무변경. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 19 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c32`: `CLOSED_DONE`, 호출 122·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 22:23:34–22:24:09Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함).
- 파드 정리 대상 판별(`attr32.sh`, 22:31:02Z): 내 Isaac 창(22:25:43–22:30:30Z)에 생긴 `tmp/carb.0aSHL8`(22:25:44 생성)·`tmp/tmpytl3ppz0`(22:26:03, `_remote_module_non_scriptable.py`)·`pyc_r6/…/tmpytl3ppz0`·`pyc_r6/…/r7c32`(772 KB)·`kitcache/cyclo-r7c32_standard`(208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`이거나 `pyc_r6` 접두인 다른 프로세스 0 → 모두 내 것.
- 파드 정리(`clean32.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 22:31:18Z): `tmp/r7c32`(514 MB), 위 Isaac 항목 5개. 끝에 r7c32 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c32가 든 프로세스 0, `IR_INST=r7c32` 프로세스 0, 열린 핸들 0. R2_TRAIN 파일과 `final_check` 프로세스는 읽기만.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a32.tar` 삭제, 보고 근거 스크립트·출력만 남김; 지시대로 `D:\tools\scratch_qdd\r7c30` 삭제 — r7c 폴더는 r7c31·r7c32만. C: 쓰기 없음.

## 7. 실험 코드 절 (별도 판정: PASS — 새 실험 쪽 변경 없음)

### 7.1 4c532d2의 실험 쪽 변경
- 없음. `git diff --name-status ac7a314 4c532d2`는 책·기록·보고서뿐이고, 실험 코드(`harvest/train/se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3|ma3/`)·실험 결과·사전 등록 변경 0. 옵트인 가드 29–32(31회차와 다른 하위 명령·값)로 두 실험 경로의 거부가 그대로임을 다시 확인(§6.4).

### 7.2 E-CAM3·E-MA3
- 4c532d2까지 결과 커밋 없음 → 범위 밖(S20). 검토 중 올라온 `76ab10c`(결과)는 33회차 대상 — 열지 않았다.

### 7.3 DOC (실험 절)
없음.

### 7.4 NOTE (실험 절)
- E-N1–E-N19. (31회차 그대로; E-N3·E-N13 해소.)

## 8. 다음 순회 전에 할 일 (제안)
1. **32회차는 기준선 FAIL(DOC 2) — 연속 무결 0.** 코드는 무변경·전 검사 통과이므로 문서 두 줄만 고친다.
2. D-1: handoff §0 R2_TRAIN 줄을 새 확인 시각으로 — 병합은 `gen check` 안에서 폴더 순서대로 진행 중이며 몇 폴더가 끝났는지(명령과 함께), `check.json`은 끝에 한 번 쓰인다는 사실, 사용 금지 조건(`CHECK_EXIT 0`·`FINAL_DONE`·행 수·시드 범위 확인). 병합·검사 결과를 커밋하면 README 규칙대로 줄을 지우고 책 `04:61` 정리(N141)·06 한 줄.
3. D-2: 책 `01:38` PASS 목록에 31(과 그 뒤 회차 결과)을 넣거나 목록을 빼 §2.8로 넘기고, 06 한 줄. 정정 전 `check32` H10처럼 보고서 판정 줄을 기계로 모아 대조한다(P68).
4. (선택, NOTE) N139(§2.8 시각 표기), N140(§0 E-CAM3·E-MA3 줄 — 결과 커밋 `76ab10c`와 함께 정리), N131·N132·N142·N143(검증기 한 줄씩 — 기준점 태그 뒤 TDD).
5. 33회차 대상은 4c532d2 이후 HEAD(`76ab10c` 포함), **연속 무결 0에서**. E-CAM3·E-MA3 결과는 실험 절에서 기준 재사용 비트 동일·판정 재계산.
