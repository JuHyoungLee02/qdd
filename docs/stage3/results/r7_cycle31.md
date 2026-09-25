# R7 객관 검증 순회 — 31회차 (cycle 31, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle30.md`의 표·결론을 근거로 쓰지 않고 30회차 정정 주장마다 diff·원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드는 **21–30회차와 다른 새 값**. 작성 2026-09-25 22:09 UTC 무렵(로컬 사본 풀기 21:54:10Z, 파드 첫 명령 21:56:57Z, 파드 정리 끝 22:07:14Z, 로컬 정리 22:08:00Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`ac7a314`**(`ac7a31445f6834b124d3c2e70b86d19f2d46a652`, 커밋 시각 2026-09-25 21:51:11 UTC, "R7 cycle 30 baseline FAIL (DOC 1: status cells partly unified) — book 01 all status cells normalized by script + machine check, README status rule and §0 removal rule, map GPU 3 role/evidence wording, handoff N116-N119 markers, records"). `272432e..ac7a314` = 커밋 1개, 8파일(문서만: 책 01·04·06·README, draft-log, handoff, direction-log, 새 `r7_cycle30.md`), **코드·시험 변경 0**(`check31` H1). 검토 내내 HEAD = ac7a314(`git log ac7a314..HEAD` 비어 있음), 작업 트리 깨끗함(이 보고서만 추가).
- **범위 나눔(30회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책 `docs/book/`. **실험 코드 절**(따로 판정) = ac7a314 이전에 커밋됐으나 아직 검토하지 않은 실험 쪽 변경 — **없음**(ac7a314의 실험 쪽 파일 변경 0). E-CAM3·E-MA3 결과는 ac7a314까지 커밋되지 않아(`git ls-tree ac7a314 docs/stage3/results/`에 cam3·ma3 0) **범위 밖** — 두 실험의 예측·평가 파일은 **열지 않았다**(프로세스 이름·시작 시각과 GPU 메모리만).
- 사본: `git -c core.autocrlf=false archive ac7a314`(tar 주석 = `ac7a31445f68…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c31\repo`에 풀었다(**592파일** = 30회차 591 + `r7_cycle30.md`, 텍스트 508파일 CR 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c31/code`(593파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `ac7a31445f68…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle30.md`, 정본 `00-interfaces.md` §1–§86 보충(뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(30회차 목록), 결합 설계 스펙 §12·§17, 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P69.
- 분류(30회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0의 줄은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약(값은 맞음), 추정 표시가 있는 수치, 반올림 차이, 적힌 사실은 참이지만 범위가 멈춘 이름(30회차 N105 선례)은 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c31`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음; 30회차 스크립트는 읽기만 하고 새로 썼다). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c31`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c31_standard`, `--inst-prefix r7c31`); R2_TRAIN 워커는 21:56:57Z에 이미 없었다(GPU 0·1 = 0 MiB, 생성 프로세스 0 — N130); GPU 2·3(E-CAM3·E-MA3)에는 아무것도 올리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **PASS** (연속 무결 0 → **1**)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 21 |
| NOTE | 100 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — 검토할 새 실험 쪽 변경 없음, 코드 결함 0, DOC 0**(NOTE E-N19 그대로)

**기준선 코드는 30회차 대상(272432e)·29회차 대상(0cc45ae)과 바이트가 같다**(ac7a314는 문서만). 회귀: 로컬 **1133 passed / 20 skipped**(Git Bash, 227.5 s), 파드 CPU **1280 passed / 4 skipped**(164.9 s), LeRobot 6 passed; 가드 **28건 + 실험 옵트인 4건 = 32건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–30회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 대조 12종**(통과해야 할 경계 4종 통과, 검출해야 할 8종 모두 검출) + 관찰 2종(N131·N132); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 완료; 새 시드 **DEV 14**에서 같은 Isaac 워커 C5 → C5' 행동 **1,691개 비트 동일**(첫 차이 없음, 시각열 동일). **30회차 정정 주장은 모두 diff와 맞고 원자료로도 참이다**(§6.2): 책 01의 **모든 표**(A 20행·C 9행·D 11행 = 상태 칸 40개; 표 B는 상태 칸 없음)의 상태 칸이 네 값 중 하나와 정확히 같다(`status31.py`, 기계 검사: `끝` 32·`` `[결과 전]` `` 3·`` `[예정]` `` 5, 벗어난 칸 0, 칸 수 불일치 0); 옮긴 링크·"바뀐 결정" 문장은 32개 바뀐 행 모두 결과 칸으로 **잃은 글자 없이** 옮겨졌다(행 단위 글자 다중집합 동일 32/32, 결과 칸 = 원래 결과 칸 + 상태 칸에서 뺀 글 31/32, 나머지 1행은 괄호 위치만 바뀜 — N137 ②). README 상태 칸 규칙·§0 줄 삭제 규칙, 책 04 GPU 3 역할·근거 명령 표기(파드에서 그 명령으로 재현), handoff §0 R7 줄 확인 시각·E-CAM3/E-MA3 등록 대 커밋 시각·N117 표시·28회차 줄(handoff·draft-log·direction-log)·30회차 줄, 06 줄 모두 참.

---

## 1. DEFECT

없음. (ac7a314는 코드·시험을 바꾸지 않았다 — `git diff --name-status 272432e ac7a314`에 `harvest/`·`tools/`·`tests/` 경로 0, `check31` H1.)

## 2. DOC

없음.

(검토했지만 DOC로 올리지 않은 후보: ① 책 `01:38` "R7 객관 검증 1–29회차" — `r7_cycle30.md`가 같은 커밋에 들어왔는데 범위가 29에서 멈췄다. 적힌 사실(1–29회차의 PASS 회차 6·16·20·22)은 참이고 29회차 N105가 같은 모양을 NOTE로 둔 선례 → N128. ② handoff §0 R2_TRAIN 줄 "P2 생성 중"(확인 21:29 UTC) — 파드에서 생성은 21:56:26Z에 끝났지만 확인 시각에 참이고 커밋 시각 21:51:11Z에도 dr P2가 아직 생성 중이었다(21:51:11Z 뒤에 끝난 편 dr 52편) → N130. ③ handoff §2.8 29회차 줄 끝의 N103 표시가 인용하는 '보고 21:02'는 ac7a314가 28회차 줄을 고쳐 더는 없다 — 시각이 붙은 이력 표시 → N129.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드(21:57Z, `r2state31.sh`·`epoch31.py`, 읽기만): 생성 끝(P0 3,600편 끝 18:08:13Z, P1 1,200편 끝 20:02:13Z, P2 1,200편 끝 21:56:26Z), 생성 프로세스 0; 폴더 행 병합은 아직(N94·N130). 확인 인자 없는 `--seeds 59999` 거부(가드 19).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — ac7a314에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. 정본 §82 구현 및 §84·§86(+보충) 결합 설계 구현 — "R7 E2E 준비 기준점 뒤". 지금 코드: 파드 `closed --hb-mode K5`·`K4`(예산 없음) → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 14 Astra 4행), 흐름 호출 없음.
- S19. 정본 §83 런타임 적용(새 직렬화 판본) — DEV 14 결정 호출 요청 102/102 `motion:` 없음.
- S20. **E-CAM3·E-MA3 결과**: 결과 커밋 없음. 파드에서 본 것(이름·시각·메모리만): 21:56:57Z에 `se2e_cam3 train`(21:27:59Z 시작, GPU 2 86.8 GiB)·`se2e_kvcond train`(21:28:07Z 시작, GPU 3 87.5 GiB) 실행 중; 22:06:41Z에 GPU 3 = 4 MiB, `tools/ma3/chunk_eval.py`(22:06:22Z 시작) 실행 중. 예측·평가 파일은 열지 않았다(실험 절 7.2).
- S21. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3. (그대로) `stageb_train predict`·`evalck`의 `prompt_config` 비대조, `cli_label.replay_max` NaN 순서, 판정 스크립트 입력 검사 수준(책 P25).
- N4. (해소, 27회차와 같음).
- N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45. (그대로, 28–30회차 목록.) N10 재현: 가드 25(`e05 --data jsel_dev/P1 --split pool --seeds 2119` → "no episode selected")가 빈 `g25/`를 남김.
- N46. (그대로) `RESUME_KEYS`의 `a3d_root`.
- N47·N48. (해소.)
- N49–N53. (그대로.)
- N54. (해소.)
- N55. (해소, 30회차와 같음.)
- N56. (해소, 이력.)
- N57, N58. (그대로.)
- N66·N67. (해소.)
- N68–N70, N72, N84–N88. (해소, 30회차와 같음.)
- N71. (그대로) 정본 §85 보충이 §86 본문 뒤 — 책 03 `:70`이 밝힘.
- N73. (그대로) 정본 §66 `:563` "본 생성 계획(아직 실행 안 함)".
- N74. (그대로) 스펙 `:123`·`:130`·`:180`·`:185` "[→ §17]" 꼬리표 권함.
- N79. (그대로) 계획 PROBE 표의 자리표시와 `timeout_s 20.0`이 섞임.
- N90. (그대로) 책 04 지도에 `se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3|ma3/`·파드 `code_cam3|ma3`·`ckpt/cam3|ma3`·`logs/cam3|ma3` 없음; `04:49` "산출 위치는 R2_TRAIN 보고 뒤 확정 `[미검증]`".
- N91. (그대로) P68·P69가 다. 절 P67 뒤.
- N92, N93. (해소.)
- N94. (그대로, 운영 위험 — 이제 급함) R2_TRAIN 생성이 21:56:26Z에 끝났는데 폴더 행 파일 18개와 `check.json`은 여전히 12:19:47–12:20:26Z 파일럿 병합분(21:57Z `r2state31.sh`: 12:21Z 뒤 바뀐 행 파일 0, 로그 MERGE·CHECK 줄 0). handoff §0·책 `04:61`의 "생성 끝난 뒤 병합·검사 필수" ✓ — 이제 할 차례(N130).
- N102. (해소.)
- N103. (해소) handoff `:133` 28회차 줄 = "보고서 머리 21:05 UTC, 파드 정리 끝 21:02 UTC [… R7 30회차 N119]", draft-log `:479` "21:02 UTC(파드 정리 끝; 보고서 머리 21:05 — …N119)", direction-log `:75` "21:02(파드 정리 끝; 보고 21:05)" — `r7_cycle28.md:3` "작성 2026-09-25 21:05 UTC(`date -u` 21:05:28Z", `:189` 파드 정리 21:02:35Z ✓(표시 번호는 N129).
- N104–N108. (해소, 30회차와 같음.)
- N109–N115, N123–N127. (29·30회차 자체 기록 — 이번 회차는 N133–N138.)
- N116. (해소) handoff `:13` "**R7** (확인 2026-09-25 21:50 UTC): 30회차 기준선 FAIL(DOC 1) → 정정 뒤 31회차. 연속 무결 0." — 30회차 보고서 머리 판정·작성 21:49 UTC ✓, 21:50 ≤ 커밋 21:51:11 ✓.
- N117. (해소) handoff `:93` 끝에 "[→ 2026-09-25 21:50 UTC, R7 30회차 N117: 이 줄의 진행 상태는 옛 기록 — 지금 진행 상태는 §0]" ✓.
- N118. (해소) handoff `:12` "사전 등록(문서 시각 20:30:33Z·20:34:02Z, 커밋 5c46056 20:33:20Z·40895f8 20:34:19Z …)" — `prereg_cam3.md:1` "(2026-09-25T20:30:33Z, 학습 전)", `prereg_ma3.md:1` "(2026-09-25T20:34:02Z, 학습 전)", `git log` 커밋 시각 20:33:20 +0000·20:34:19 +0000 ✓.
- N119. (해소, N103과 같이.)
- N120. (해소) `04:61` 근거 명령 "파드 `ls -l --time-style=+%H:%M:%S` 18파일 12:19:47–12:20:26 UTC(파드 표시는 KST)" — 파드에서 그 명령을 그대로 돌리면(기본 TZ Asia/Seoul) 21:19:47…21:20:26 18줄, `TZ=UTC`면 12:19:47Z…12:20:26Z(`r2state31.sh`) ✓. `ma1.md:15`의 "`ls -l --time-style`"는 형식 인자만 생략한 같은 명령.
- N121. (해소) `04:36` "3 = vLLM·보조 VLM 서버 자리(탐침 Qwen3-VL-8B 포트 8341; 서버가 없을 때는 실험 학습에도 씀 — 지금 쓰임은 handoff §0)" — handoff §0 `:12` "E-MA3 (GPU 3)" ✓, 파드 21:56:57Z GPU 3 = `se2e_kvcond train` 87.5 GiB·vLLM 없음 ✓.
- N122. (해소) README `:11` "실험 장부의 상태 칸은 정확히 `끝`·`중단`·`[결과 전]`·`[예정]` 넷 중 하나만 쓰고(링크·설명은 결과 칸), 커밋 전에 기계 검사한다 … 결과가 커밋되면 handoff §0의 해당 줄은 같은 커밋에서 지운다." — 장부 전체 규칙 + §0 줄 삭제 규칙 ✓; `01:4` 범례·`01:56`(표 D 줄)과 모순 없음.
- **N128.** `01:38` "R7 객관 검증 1–29회차" — ac7a314에 `r7_cycle30.md`가 들어와 보고서는 30개(`git ls-tree` r7_cycle 30개)인데 범위가 1–29로 멈췄다(PASS 목록 6·16·20·22는 30회차 FAIL이라 여전히 참). 29회차 N105와 같은 모양 — 범위를 "1–30"으로 하거나 행 이름에서 회차 범위를 빼면 매 회차 갱신이 필요 없다.
- **N129.** handoff §2.8 29회차 줄(`:134`) 끝 "[→ … R7 29회차 N103: 28회차 줄 '보고 21:02'는 파드 정리 끝 시각, 보고서 머리 21:05]"가 인용하는 '보고 21:02'는 ac7a314가 28회차 줄을 "보고서 머리 21:05 UTC, 파드 정리 끝 21:02 UTC"로 고쳐 더는 없다(이력 표시라 무해). 또 28회차 줄 고침은 30회차 **N103**이 지적한 것인데 표시는 **N119**(29회차 줄 '21:2x' 근사 확인 ✓)로 붙었다 — 번호만 어긋남.
- **N130.** (운영, handoff §0) R2_TRAIN 줄(확인 21:29 UTC, "P2 생성 중")은 확인 시각에 참이고 커밋 시각(21:51:11Z)에도 dr P2 생성 중이었다(`epoch31.py`: 21:51:11Z 뒤 끝난 편 dr bottle_tray 17·mug_marker 18·mug_tray 17, standard 0 — standard P2 끝 21:35:02–21:35:28Z). 21:56:26Z에 P2 마지막 편이 끝나 21:57Z에는 생성 프로세스 0(`cpumon.log` 21:57:21 gen_procs=0), 종류별 편 수 P0 3,600·P1 1,200·P2 1,200. 다음 커밋에서 §0 줄을 "생성 끝, 병합·검사 전"으로 바꾸고 병합·검사 결과가 나오면 README 규칙대로 줄을 지운다.
- **N131.** (검증기 관찰, 음성 대조 `decflip`) `validate.py:73`의 검증 대상 검사는 줄의 `decision` 깃발을 읽고(`ln["decision"] and "prev_step" not in ln["verify"]`), `:70`의 라벨 검사는 `is_decision(k)`를 쓴다. 결정 프레임 k20의 `decision`을 False로 바꾸고 `prev_step`을 지우면 오류 0으로 통과한다. 생성기가 두 값을 같은 원천에서 쓰므로 실제 위험은 낮다(권함: `ln["decision"] == is_decision(ln["k"])` 검사 한 줄).
- **N132.** (검증기 관찰, `nogripkey`) npz에 `grip` 배열이 없으면 `validate.py:76`–`:79`가 오류 목록에 적지 않고 `KeyError: 'grip is not a file in the archive'`로 멈춘다(크게 실패하므로 조용히 통과하지는 않음). 권함: `key not in z.files`를 오류로 기록.
- **N133.** 텍스트 위생(`check31`): 사본 텍스트 508파일 CR 0; 변경 md 8개 BOM·CR·C0·C1·영폭 0, **표 칸 수 불일치 0**(H3 — 코드 구간·이스케이프 파이프 제외); 책 링크 101개 끊김 0(H4); ac7a314는 책 01·04·06·README를 바꾸고 06 `:22` 한 줄("01·README·04", 21:50 ≤ 커밋 21:51:11 ✓)을 더했다(H5). 책 본문 현재형 진행 상태 검색(H9: `진행 중|생성 중|학습 중|작업 중|미커밋|아직|지금|현재`) — 02·06 이력 인용과 README·01·04의 "handoff로" 안내·규칙 문장, `01:38` "(아직)"(커밋으로만 바뀌는 E2E 기준점), `04:22`·`04:48` "현재"(판본)뿐 → 현재형 진행 상태 없음.
- **N134.** 시험 수: 로컬 **1133 passed / 20 skipped**(227.5 s, 21:54:36–21:58:25Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c31/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(164.9 s, 21:57:41–22:00:28Z; 건너뜀 isaaclab·pyarrow 경로·CUDA·TODO), 경고 1(기존), LeRobot 6 passed(16.8 s). 30회차와 같은 수(코드 무변경).
- **N135.** 단계 B 소형 CPU 스모크(22:02:42Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–30회차와 같은 값 — 결정적), expert p50 0.041 s·전체 p50 0.112 s, 맥락 토큰 454.
- **N136.** DEV 14 판: 행동 1,691·16.91 s·결정 호출 51(조건마다), C5 `last_step` {none 1, OK 35, LAG 6, DEVIATE 9}, C5' none 51/51, 확정 비율 0.8885, 결정 3.018/s, rtf 0.510, 지연 p50·p95 0.3 s, Astra 2(hb 5.0 → 8.0, sub 9.58 → 12.58, 겹침 0), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28–30회차와 같음 — 코드 무변경), 파일명 `dev14-P0-standard-e0`, 판 201.6 s(22:02:53–22:06:15Z). 파드 GPU(22:02:53Z 전·22:06:15Z 뒤): 0·1 = 0 MiB(내 Isaac 창 동안만 GPU 1 사용), 2 = 86.8 GiB, 3 = 87.5 GiB → 22:06:41Z 4 MiB(E-MA3 학습 끝·평가 시작, S20).
- **N137.** (절차, 자체 점검) ① 가드 12·13(`--isaac-gpu 2`·`01`)은 `closed.py:38`·`:391`(문자열 `("0", "1")` 검사가 워커 실행 전)을 먼저 읽고 골랐고 `CUDA_VISIBLE_DEVICES=""`로 돌렸다 — 검사가 새도 GPU 2·3에서 렌더할 수 없게. 실험 옵트인 가드 30(`se2e_cam3 train --data se2e --cam3 cam3@v1`)도 `install`의 움직임 줄 검사가 데이터 적재 전(`se2e_cam3.py:103`–`:104`, `main :121`)임을 확인하고 골랐다. ② 첫 행 비교 설계(결과 칸 = 원래 결과 칸 + 상태 칸에서 뺀 글)는 E-Astra-motion 행(`01:62`)을 "확인 필요"로 냈다 — 원래 상태 칸 "끝 ([R/astra_motion](…)) — 바뀐 결정: …"이 결과 칸 끝 "([R/astra_motion](…) — 바뀐 결정: …)"로 괄호 안에 합쳐졌기 때문. 비교를 행 전체 글자 다중집합(공백 제외) 동일 + 눈 읽기로 다시 설계했다: 32/32 동일, 내용 손실 0. ③ 음성 대조 원본은 표준 변형의 **두 번째** 유효 편(`standard/bottle_tray/P0` ep1, 340프레임 — 28회차 첫 dr, 29회차 마지막 standard, 30회차 마지막 dr과 다름). ④ R2_TRAIN 워커 코드 폴더는 워커가 없어 다시 확인할 대상이 없다. ⑤ 정리 스크립트의 "r7c31이 든 명령줄 프로세스" 검사는 `grep 'r7c[3]1'`로 자기 매칭을 피했다.
- **N138.** handoff §2.7 `:95` "운영 규칙(추가) … GPU 3 = vLLM"(09-24 21:03 절)은 `04:36`의 새 서술("서버가 없을 때는 실험 학습에도 씀")보다 좁다 — 시각이 붙은 옛 절이라 NOTE; 다음 정리 때 "→ 책 04 GPU 역할" 표시 권함.

---

## 5. 사전 등록 대조표 (행마다 이번 회차의 행동 확인)

`prereg.json` 해시: 파드 산출 `meta.prereg.check` = OK(ac7a314 코드, 사전 등록 변경 0 — H1). 30회차 표의 행 번호를 그대로 쓴다. 기준선 코드 = 272432e와 같음(H1). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c31\check31.py`(H1·H3·H4·H5·H9)·`status31.py`, **파드** = §6(`pod_cpu31.sh`, `pod_eval31.sh`·`data31.py`·`gtxt31.sh`·`lr31.sh`, `pod_isaac31.sh`·`closed31.py`, `r2state31.sh`·`epoch31.py`·`who31.sh`, `attr31.sh`·`clean31.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 가드 28건 rc ≠ 0(§6.4): TEST 1149·1000, CAL 500·549, TEST-P5 1329, DEV 29,30·2000, POOL 1999, gen 59999(확인 없음)·9999·60000(확인 있음), determinism 30·1999 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | 코드 무변경; `calib --heldout jsel_dev/P0 --episodes 2` → `CALIB_DONE`; 가드 3(`--fit-split test`)·4(`--heldout-split test_p5`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 14** C5·C5' 성공(16.91 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 14 결정 호출 102행**(조건마다 51): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 102/102; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치 |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P1 --split dev --episodes 2` → `E05_DONE`; 가드 24(`canary build-set --data P0 --seeds 3198-3199`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H`·`m4_lead_max` 3·1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,C5''"` → "condition \"C5''\": runtime has ['C0' … 'C6']"; **DEV 14 C5 `last_step` {none 1, OK 35, LAG 6, DEVIATE 9}, C5' none 51/51, 요청 본문 마지막 `last_step:` 줄 = 행 값 102/102** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P1 --episodes 2` → `RD_DONE`(dr 낙폭 평균 −0.0032, n 310); 가드 5 `rd --variants dr=gen_dev/dr/P1 --split test` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-0.5` → "lead_max = -0.5 … finite > 0 s", 15 `=nan` → "lead_max = nan … finite > 0 s", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(22:06Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2005,2066,2093 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 14, 22:02:53–22:06:15Z)**: 행동 **1,691개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 51·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | 생성 끝(21:56:26Z), 워커 없음(N130) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119" 폴더 없음; 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 2`·`01` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 14 hb 5.0 → 8.0, sub 9.58 → 12.58, 겹침 0 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 3편 입력**(standard/bottle_tray/P0 ep4·dr/mug_marker/P0 ep2 참, dr/bottle_tray/P0 ep1 **거짓**): 내보낸 편 2·627프레임(360 + 267, 무효 편 건너뜀 ✓), `verify` 오류 0·PSNR 최소 39.0 dB·lerobot 0.3.3 적재 627프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 대조 12종**(standard/bottle_tray/P0 ep1, 340프레임): 무수정 오류 0; k170 머리 경로 ← 손목 경로 → 오류 0(크기 검사는 k0·K만); 모든 프레임에 `cam_extra` 추가 → 오류 0; 행 k169 `proprio_mask {'tau': 0}` → 오류 0; 전 프레임 시각 +0.5 s → "off the 30 Hz grid by 5.00e-01 s"; 끝 프레임 줄 삭제 → "stageb rows are not one per non-terminal frame" + npz 길이 오류; 라벨 행 k170·k180 순서 바꿈 → "labels_v2 rows != decision frames"; 행 k84 `valid[-1]` = 2 → "valid: H values in {0,1}"; 행 k254 `proprio_mask {'foo': 1}` → "proprio_mask: keys from […]"; 행 k135 `phase_id` 삭제 → "missing field 'phase_id'"; 마지막 행 k338 → 339 → "stageb rows are not one per non-terminal frame"; npz `grip` 가운데 NaN → "npz grip: … non-finite". 관찰: `decflip` 오류 0(N131), `nogripkey` KeyError(N132) | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 14 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 이번 대상에 새 유료·GPU 실험 등록 없음 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | ac7a314 코드 변경 0(H1); 옵트인 가드 28–32(argparse·install 단계 거부) | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | §6.3: 상태 칸 40개 기계 검사 0 벗어남, 행 32개 내용 보존, 링크 101개 끊김 0, 04 수치·근거 명령 파드 재현, 06 갱신 줄 | 일치 / NOTE N128·N133 |
| **156** | 정본 §86 = 탐침 결과 + §86 보충(`:778`) | — | 정본 무변경(H1); 30회차 확인 그대로 | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond`, … | 코드 무변경; 가드 29–32 거부; 결과 커밋 없음(S20) | 일치 |

### 5.1 30회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드 28건), 5·6·51–58·99·137·151(DEV 14), 13–17·61–62(jsel_dev/P1·gen_dev/dr/P1), 2–4(jsel_dev/P0), 66–67(`-0.5`·`nan`), 98(POOL 2005·2066·2093), 101(생성 끝), 138(다른 세 편), 139(새 대조 12종 + 관찰 2종), 155(D-1 해소 확인), 156(정본 무변경).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status 272432e ac7a314`: M 책 01·04·06·README, draft-log, handoff, direction-log; A `r7_cycle30.md`. 코드·시험·정본·사전 등록 0. 책 01 = 32행 바뀜(±32줄), 04 = 2줄, 06 = +1, README = 1줄.

### 6.2 30회차 정정 주장 대 실제 diff·원자료 (ac7a314)
| 주장 (06 `:22`, handoff §0·`:135`, 커밋 메시지) | 실제 diff | 원자료·원 문서로 참인가 | 판정 |
|---|---|---|---|
| 01 모든 표 상태 칸을 네 값으로 기계 정리(D-1) — 표 A·C·D의 링크·바뀐 결정은 결과 칸으로 | 표 A 20행·C 9행·D 3행(`:60`–`:62`)의 상태 칸 → `끝`, 뺀 글 → "결과 (실측)"·"결과" 칸 끝 | `status31.py`(ac7a314 사본): 상태 칸 있는 표 3개(A `:9` 7칸·C `:42` 8칸·D `:58` 5칸; B `:34`는 상태 칸 없음), 상태 칸 40개 모두 {`끝`, `` `[결과 전]` ``, `` `[예정]` ``} 안(`중단` 0), 칸 수 불일치 0; 272432e 대 ac7a314 행 단위: 바뀐 행 32개 = 상태 칸 행 전부 중 옮길 글이 있던 행, 바뀐 칸은 상태 칸 + 결과 칸 둘뿐, 결과 칸 = 원래 + 뺀 글 31행, `:62`는 괄호 위치만 다름(행 글자 다중집합 동일 32/32) | 맞음 |
| README 상태 칸 규칙·§0 삭제 규칙(N122) | `README.md:11` | 규칙 문장 ✓; `01:4`·`01:56`과 모순 없음 | 맞음 |
| 04 GPU 3 역할(N121) | `04:36` | handoff §0 GPU 3 = E-MA3 ✓, 파드 21:56:57Z GPU 3 = `se2e_kvcond train` ✓ | 맞음 |
| 04 근거 명령 표기(N120) | `04:61` "`ls -l --time-style=+%H:%M:%S` … (파드 표시는 KST)" | 파드에서 그 명령 → 21:19:47–21:20:26(KST), `TZ=UTC` → 12:19:47Z–12:20:26Z 18파일 ✓ | 맞음 |
| handoff §0 R7 줄 확인 시각(N116) | `handoff.md:13` "(확인 2026-09-25 21:50 UTC): 30회차 기준선 FAIL(DOC 1) → 정정 뒤 31회차. 연속 무결 0." | 30회차 머리 FAIL·DOC 1 ✓, 21:50 ≤ 21:51:11 ✓ | 맞음 |
| handoff §0 E-CAM3·E-MA3 등록 대 커밋 시각(N118) | `handoff.md:12` | 등록 문서 머리 20:30:33Z·20:34:02Z ✓, 커밋 20:33:20Z·20:34:19Z ✓; "학습 중(확인 21:02 UTC)"은 30회차가 확인(시드 1 20:42:33–21:23:33Z·20:45:14–21:23:02Z) | 맞음 |
| handoff 옛 진행 줄 N117 표시 | `handoff.md:93` 끝 표시 | 줄 앞 "(21:03 기준; …)" = 09-24 절 ✓ | 맞음 |
| 28회차 줄 시각(N119; handoff·draft-log·direction-log) | `handoff.md:133`, draft-log `:479`, direction-log `:75` | `r7_cycle28.md:3` 작성 21:05 UTC(21:05:28Z) ✓, `:189` 파드 정리 21:02:35Z ✓; direction-log 칸 수 4 ✓ | 맞음(N129 번호) |
| 30회차 줄(handoff·draft-log·direction-log) | `handoff.md:135` "보고 2026-09-25 21:49 UTC 무렵 … DEFECT 0, DOC 1(…앞 세 줄…), SCOPED 21, NOTE 89. 실험 절 PASS. 정정(21:50 UTC) … 기계 검사(네 값 외 0). 연속 무결 0회 → 31회차"; draft-log `:481`; direction-log `:77` | `r7_cycle30.md` 판정 표(0·1·21·89)·실험 절 PASS·작성 21:49 UTC ✓; "네 값 외 0" = 내 기계 검사 ✓ | 맞음 |
| handoff 머리 "마지막 갱신 21:50 UTC" | `handoff.md:3` | ≤ 커밋 21:51:11 ✓ | 맞음 |
| 갱신 기록 | 06 `:22` "2026-09-25 21:50 \| 01·README·04 \| R7 30회차 정정 …" | ac7a314 책 변경 01·04·06·README = 줄이 덮음 ✓, 21:50 ≤ 21:51:11 ✓ | 맞음 |

### 6.3 기록책 (ac7a314 사본에서)
- 상태 칸 기계 검사·행 보존: §6.2 첫 행. 표 B(재현성·검증)는 `| ID | 질문 | 결과 | 판정 → 결정 | 문서 |`로 상태 칸이 없다.
- 현재형 진행 상태: N133(없음). 수치: `04:61` 파드 재현 ✓, 01 행 수치는 글자 그대로 이동(바뀐 숫자 0).
- 링크 101개 끊김 0(H4); 06 갱신 줄(N133). 남은 것: `01:38` 범위(N128).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 22:01:07–22:01:24Z, 21–30회차와 다른 값; 사유는 `gtxt31.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data P0 --split test --seeds 1149`, 2 `e05 --data P2 --split cal --seeds 500`, 3 `calib --fit-split test --heldout P1 --heldout-split dev`, 4 `calib --fit-split pool --heldout P1 --heldout-split test_p5`, 5 `rd --variants dr=gen_dev/dr/P1 --split test`, 6–8 `closed --split test --seeds 1000`·`cal 549`·`test_p5 1329` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 29,30` → "seeds [30] are not in split dev", 10 `pool --seeds 1999`, 11 `dev --seeds 2000` → "not in split … (refused, never opened)"; 12–13 `--isaac-gpu 2`·`01` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-0.5`, 15 `=nan` → "lead_max = -0.5 / nan … finite > 0 s"; 16 `--conditions "C5,C5''"` → "condition \"C5''\": runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=test_p5` + `closed --split cal --seeds 520`, 18 `=cal` + `e05 --data P1 --split test --seeds 1149` → 거부(다른 분할 허용은 통하지 않음); 19 `gen --seeds 59999`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9999 --confirm-train`, 21 `--seeds 60000 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 30`, 23 `history --seeds 1999` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P0 --seeds 3198-3199`, 25 `e05 --data P1 --split pool --seeds 2119` → "no episode selected"; 26 `--hb-mode K5` → "from ('K0', …, 'K4')", 27 `--hb-mode K4`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d@v2` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 evalck --data pool --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 train --data se2e --cam3 cam3@v1`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)", 31 `se2e_kvcond predict --expert-cond kvcond@v2`, 32 `se2e_cam3 predict --cam3 CAM3@V1` → argparse "invalid choice" rc 2. **32건 모두 rc ≠ 0**(1–27·29·30 rc 1, 28·31·32 rc 2); 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c31\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c31/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 12종(+관찰 2); LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀, 행 138); `se2e_c1` **5/5 OK**(22:06Z). (R2_TRAIN 폴더 행 병합은 아직 — N94·N130, 완료 정의 1은 R2 DEV 기준.) |
| 2 모델 | 충족(CPU) | CPU 스모크(N135), CPU 묶음의 단계 B·E-MA1b·E-CAM3·E-MA3 시험 통과, 기준선 코드 무변경. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 14 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c31`: `CLOSED_DONE` C5·C5' 1.0, 호출 51·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 22:01:24–22:01:57Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`(dr 낙폭 −0.0032), `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). HEAD 시작·끝 ac7a314.
- 파드 정리 대상 판별(`attr31.sh`, 22:06:41Z): 내 Isaac 창(22:02:53–22:06:15Z)에 생긴 `tmp/carb.9ZaJmk`(22:02:54 생성, Kit 임시)·`tmp/tmpqjbfwc8w`(22:03:12, `_remote_module_non_scriptable.py`; `.pyc`가 `cache/pyc_r6` 아래 = 내 워커의 접두)·`pyc_r6/…/r7c31`(22:02:54, 772 KB)·`kitcache/cyclo-r7c31_standard`(22:02:54, 208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-CAM3 학습(21:27:59Z)·E-MA3 평가(22:06:22Z 시작 — 내 창 뒤)·GPU 감시 `nvidia-smi` 2개뿐이고 모두 `PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc`(pyc_r6 아님) → 두 임시 항목은 내 것(30회차와 같은 모양).
- 파드 정리(`clean31.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 22:07:14Z): `tmp/r7c31`(509 MB), `tmp/carb.9ZaJmk`·`tmp/tmpqjbfwc8w`·`cache/pyc_r6/data/harvest/tmp/tmpqjbfwc8w`·`cache/pyc_r6/data/harvest/tmp/r7c31`, `ir/kitcache/cyclo-r7c31_standard`(208 MB). 끝에 r7c31 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c31이 든 프로세스 0, `IR_INST=r7c31` 프로세스 0, 열린 핸들 0. R2_TRAIN·E-CAM3·E-MA3 파일은 읽기만(E-CAM3·E-MA3는 프로세스 이름·시각·GPU 메모리만).
- 로컬: 추출 사본 `repo/`(26 MB)·pytest basetemp `pt/`·archive `a31.tar`(21 MB) 삭제, 보고 근거 스크립트·출력만 남김(`r7c31` 416 KB); 지시대로 `D:\tools\scratch_qdd\r7c29`(592 KB) 삭제 — r7c 폴더는 r7c30(480 KB)·r7c31만. D: 여유 8.1 GB(끝, 22:08Z). C: 쓰기 없음.

## 7. 실험 코드 절 (별도 판정: PASS — 새 실험 쪽 변경 없음)

### 7.1 ac7a314의 실험 쪽 변경
- 없음. `git diff --name-status 272432e ac7a314`는 책·기록·보고서뿐이고, 실험 코드(`harvest/train/se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3|ma3/`)·실험 결과·사전 등록 변경 0. 옵트인 가드 29–32(다른 하위 명령·값)로 두 실험 경로의 거부가 그대로임을 다시 확인(§6.4).

### 7.2 E-CAM3·E-MA3
- ac7a314까지 결과 커밋 없음 → 범위 밖(S20). 파드에서 본 것은 프로세스 이름·시작 시각·GPU 메모리뿐(`who31.sh`·`attr31.sh`). 예측·평가 파일(`predfull_*`·`chunk_*`·`reuse_check.out`·`verify_results.py`)과 로그 내용은 열지 않았다.

### 7.3 DOC (실험 절)
없음.

### 7.4 NOTE (실험 절)
- E-N1–E-N11. (27회차 그대로; E-N3 해소.)
- E-N12. (그대로.)
- E-N13. (해소.)
- E-N14–E-N18. (그대로.)
- E-N19. (그대로) 결과 `astra_motion.md:7`·`:58`의 "17:43–17:52Z" — ac7a314는 이 파일을 바꾸지 않았다.

## 8. 다음 순회 전에 할 일 (제안)
1. **31회차는 기준선 PASS — 연속 무결 1.** 32회차가 기준선 PASS면 E2E 준비 기준점(2회 연속).
2. (운영, N94·N130) R2_TRAIN 생성이 21:56:26Z에 끝났다 → 병합·검사를 돌리고 행 수 대 편 수(P0 3,600·P1 1,200·P2 1,200)를 확인; handoff §0 R2_TRAIN 줄을 UTC 확인 시각과 함께 갱신하고, 결과가 커밋되면 README 규칙대로 그 줄을 지운다(같은 커밋에 책 04 `:61`의 파일럿 병합 서술 정리와 06 줄).
3. (선택, NOTE) N128(`01:38` 범위 1–30 또는 범위 빼기), N129(표시 번호), N131·N132(검증기 한 줄씩), N138(handoff §2.7 GPU 3), N90(지도 새 경로).
4. 32회차 대상은 ac7a314 이후 HEAD, **연속 무결 1에서**. E-CAM3·E-MA3 결과가 커밋되면 기준 재사용 비트 동일·판정 재계산을 실험 절에서.
