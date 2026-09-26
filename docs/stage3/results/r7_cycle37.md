# R7 객관 검증 순회 — 37회차 (cycle 37, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle36.md`의 표·결론을 근거로 쓰지 않고 `ffe335c..3d4738a`의 바뀐 줄마다 diff·원 문서·파드 원자료로 다시 확인했다 — 책 P68). 대조표는 사전 등록 원문(E-first §1.5–§1.7, `prereg_*.md`, 정본)에서 다시 만들었고, 가드·음성 대조·Isaac 시드·모의 평가 입력·LeRobot 입력은 **21–36회차 보고서에서 뽑은 사용값 목록(`usedvals37.py`)과 겹치지 않는 새 값**. 작성 2026-09-26 00:42 UTC(`date -u` = 2026-09-26T00:42:18Z; archive 00:26:58Z, 로컬 사본 풀기 00:27:27Z, 파드 첫 명령 00:29:41Z, 파드 정리 끝 00:41:46Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`3d4738a`**(`3d4738ad95f00776a85a92d08b306a64fc33683c`, 커밋 시각 2026-09-26 09:25:49 +0900 = **2026-09-26 00:25:49 UTC**). `ffe335c..3d4738a` = 커밋 1개(`3d4738a` "R7 cycle 36 baseline PASS (clean count 1) — records only"). 뒤 커밋은 범위 밖.
- **범위 나눔(36회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책(paper/는 NOTE 수준). **실험 코드 절**(따로 판정) = 3d4738a까지 커밋됐으나 아직 검토되지 않은 실험 코드.
- 사본: `git -c core.autocrlf=false archive 3d4738a`(tar 주석 = `3d4738ad…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c37\repo`에 풀었다(**610파일** = 36회차 609 + `r7_cycle36.md`; 텍스트 554파일(.tex·.bib 포함) CR 0·BOM 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c37/code`(611파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `3d4738ad…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle36.md`, 정본 `00-interfaces.md` §1–마지막 절(§86 + 보충, 뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(`prereg.json` 해시, `prereg_*.md` 11개, E-first `§1.5`–`§1.7` 원문), 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P72.
- 분류(36회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0·결과 문서의 `[결과 전]` 항목은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. 미룬 NOTE(N131·N132·N142·N143·N154·N165·N190·N193, N155, N192)는 사전 등록 동작·완료 정의를 깨지 않는 한 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c37`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음; 파드 상태·정리 스크립트는 Write로 만든 파일을 `bash -s`로 흘림). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c37`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c37_standard`, `--inst-prefix r7c37`); GPU 0·2·3에는 아무것도 올리지 않음. 남의 프로세스(E-MA2 `run_ma2.sh`·c2 학습 — GPU 2; R2 LeRobot `export_all.sh`)는 건드리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음. **E-MA2 예측·평가 파일은 열지 않음**(이번 회차는 E-MA2 데이터·로그도 읽지 않음; 프로세스 목록만).

## 판정 (기준선): **PASS** (DEFECT 0 · DOC 0 → 연속 무결 **2** = E2E 준비 기준점)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 20 |
| NOTE | 164 |

## 판정 (실험 코드 절, 카운트와 별개): **검토할 새 실험 코드 없음**

`ffe335c..3d4738a`에 코드·시험·도구 변경 0(H1). 3d4738a 이전의 마지막 실험 코드(E-MA2 `fde4f6a`)와 paper 갱신(`54b9205`)은 36회차가 검토했다. 확인만 다시 함: 사전 등록 문서의 (경로, LF 블롭 sha256 앞 16) 쌍 **34개**(`prereg_cam3` 9·`prereg_ma1` 4·`prereg_ma1b` 5·`prereg_ma2` 8·`prereg_ma3` 8)를 등록 원문에서 직접 읽어 3d4738a 사본과 비교 → 불일치 0(`hashes37.py`); E-MA2 옵트인 가드 4건(새 형식) 모두 거부(§6.3 가드 36–39). E-MA2는 학습 중이라 결과·예측 파일은 열지 않음.

**기준선은 코드 변경 없이 모든 동작 검사가 통과했고, 문서 변경(기록 4파일)은 모두 출처와 같다**: 로컬 **1156 passed / 21 skipped**, 파드 CPU **1307 passed / 4 skipped**, LeRobot 6 passed; 가드 **39건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–36회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 대조 16종**(통과해야 할 경계 4종 통과, 검출해야 할 8종 모두 검출, 특수 1종 맞음, 관찰 3종); R2_TRAIN **가운데 3시드** 54편 재검증(3d4738a 검증기 대 도장 메타 불일치 0); 실데이터 훑기(DEV 36편 + R2_TRAIN 새 3폴더 60 % 위치부터 260편 77,788프레임, 새 항목 행 고유감각 유한성 포함: 불일치 0); 모의 평가 한 명령씩 완료; 새 시드 **DEV 12**에서 같은 Isaac 워커 C5 → C5' 행동 **1,877개 비트 동일**.

---

## 1. DEFECT

없음. (`ffe335c..3d4738a`의 `harvest/`·`tools/`·`tests/`·`configs/` 변경 0 — `check37` H1. 기준선 코드는 ffe335c와 바이트 동일, `code_sha` `05e42ada69c2143d` = 36회차 값.)

## 2. DOC

없음. 바뀐 4파일의 바뀐 줄 전부(handoff `:3`·`:12`·`:142`, draft-log `:489`, direction-log `:83`, 새 `r7_cycle36.md`)를 출처와 대조했다(§6.2). 36회차 보고서 자체의 건수·머리 시각·NOTE 계산도 확인(§6.2 끝).

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN(§66, §77 N8 (4)) — 원본·병합 끝, 결과 문서 커밋됨. LeRobot 내보내기는 `[결과 전]`(handoff §0 확인 23:27 UTC 줄, N212). 확인 인자 없는 `--seeds 23456` 거부(가드 19).
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`) — 가드 §6.3.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8. S6. Astra 카나리 "none"(§67 보충). S7. S-E2E 체크포인트 런타임 형식 차(§77 보충 (2), §80). S8. CONTRADICT-soft(§68 K6). S9. §73 D5 M4 설계 확장. S10. §73 N5 E1 범위. S11. §74 보충 E-M4-lat 비례 STALE_MAX. S12. §75 보충 (2) E-M4 판정 7. S13. §77 N8 (13) 완료 정의 밖 사전 등록 실험(E-MA2 포함). S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석(그대로). S15. §79 보충 `flip_th` 질문별 사전화. S16. §78 "남은 것"(dr·random 변형, CUDA PhysX, P2 결정성 행렬). S17. §78 (2) 옛 물리 녹화 재녹화·재라벨(책 01 `[예정]`).
- S18. 정본 §82·§84·§86(+보충) 결합 설계 구현("R7 관문 뒤") — `closed --hb-mode K13`·`"K1,K2,K4"`(예산 없음) 워커 전 거부(가드 26·27), DEV 12 Astra 요청 이미지 1장·effort low·600, 흐름 호출 없음.
- S19. 정본 §83 런타임 적용("R7 관문 뒤") — DEV 12 결정 호출 요청 112/112 `motion:` 없음.
- S20. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3, N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45, N46, N49–N53, N57, N58, N71, N73, N74, N79, N90, N91, N129, N131–N138, N142–N148, N151–N155, N162, N164–N173, N176, N177, N180, N183–N206. (그대로.) N10 재현: 가드 25(`e05 --data jsel_dev/P1 --split pool --seeds 2091`)가 빈 `g25/`를 남김. **N155 재현**: DEV 12에서 요약 `astra_by_kind {hb 2, sub 1}`(3) 대 Astra 로그 행 2(hb 5.0 → 8.0, sub 8.01 → 11.01) — 에피소드 끝(18.77 s)에 날아가던 hb 호출이 행을 남기지 않음; 결합 구현 때 처리로 미룬 NOTE 그대로(결정 호출 행 112/112 온전). 검증기 N131·N132·N142·N143·N154·N165·N190·N193: 태그 뒤 TDD(그대로; 이번 관찰 N210도 같은 묶음). N192(paper E-MA2 "사전 등록 중")는 paper 무변경이라 그대로.
- N4, N47, N48, N54–N56, N66–N70, N72, N84–N88, N92–N94, N102–N108, N116–N122, N128, N130, N139–N141, N149, N161, N163, N174, N175, N178, N179, N181, N182. (해소·표시, 그대로.) N109–N115, N123–N127, N156–N160(이전 회차 자체 기록).
- 해소(이번 회차): 없음. 계산: 36회차 152 − 해소 0 + 새 12(N207–N218) = **164**.
- **N207.** 시험 수: 로컬 **1156 passed / 21 skipped**(227.99 s, 00:27:30–00:31:19Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c37/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 16·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1307 passed / 4 skipped**(164.09 s, 끝 00:32:56Z), 경고 1(기존), LeRobot 6 passed(17.84 s). 로컬 `tools/prereg_hash.py --check` → OK, `tools/intent_check.py` → total 124 flagged 0. 등록 블롭 해시 34쌍 불일치 0.
- **N208.** 단계 B 소형 CPU 스모크(00:35:21–00:35:51Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(결정적, 21–36회차와 같음), 저장·재적재 `max_abs_action_diff` 0.0·`eval_equal` 참, expert p50 0.018 s·전체 p50 0.100 s, 맥락 토큰 454, dec_acc 0.292 → 0.708.
- **N209.** DEV 12 판: 행동 1,877·18.77 s 성공 종료(두 조건 `env_success` 참), 결정 호출 56(조건마다), C5 `last_step` {none 1, OK 32, LAG 8, DEVIATE 15}, C5' none 56/56, 두 조건 호출의 `t_state`·`t_deliver`·`latency_s`·`answers` 56/56 같음, 확정 비율 0.8105, 결정 2.985/s(시뮬 초), rtf 0.53, 지연 p50·p95 0.3 s, Astra 행 2(겹침 0), `hb_mode` K2, 파일명 `dev12-P0-standard-e0`, 판 209.7 s(00:36:34–00:40:04Z). 파드 GPU 0·1 전·후 0 MiB(GPU 2 = E-MA2 c2 학습 125 GB, GPU 3 0 MiB).
- **N210.** (검증기 관찰, 새 종류 3개) ① 행 `proprio.q[0]` = NaN → 오류 0·`valid_for_training` 참: `check_row`는 고유감각의 **길이**만 본다(`stageb_data.py:150`–`:152`). 문서화된 구조 검사(`r2_datagen.md:55`: 행은 `check_row(hz=30)`, 유한성은 npz만)와 같은 동작이라 결함 아님; 실데이터 훑기에서 행 고유감각 비유한 값 0(DEV 10,615행 + R2_TRAIN 77,528행). ② npz에서 `tau` 배열 삭제 → `KeyError`로 멈춤(`validate.py:83`), ③ 프레임 `t` 문자열 → `TypeError`로 멈춤(`validate.py:49`) — 둘 다 N193(`k` 누락 KeyError)과 같은 계열(구조 오류 대신 예외). 태그 뒤 TDD 묶음에 함께.
- **N211.** `M4Params(H=0)`은 데이터클래스 자체에서 거부되지 않는다(`lead_max`·`W`만 `__post_init__` 검사). H ≥ 1은 `closed.m4_config`(`closed.py:160`–`:161`)가 막고, H를 사용자가 정하는 경로는 `closed --m4-h` 하나뿐(`grep`으로 확인)이라 가드 33(`--m4-h=-4` 거부)으로 충분. 결함 아님.
- **N212.** handoff §0 LeRobot 줄(확인 23:27 UTC)의 "데이터셋마다 381–453편 끝 / 기대 579–991편"을 파드 parquet mtime으로 다시 셈: 23:27:00Z까지 379–450, 23:27:30Z까지 383–454 → 줄의 값은 그 사이(23:27 확인 시각에 참); 기대 579–991 = `r2_train_gen.md:69`–`:74`(591/579·987·991). 지금(00:40Z)은 6개 중 4개(dr_bottle_tray 579, standard_* 591·987·991)의 `meta/episodes.jsonl`이 생겼고 dr_mug_marker·dr_mug_tray는 진행 중 — 확인 시각 규칙상 낡음 아님, 다음 handoff 갱신 때 새로 적으면 됨.
- **N213.** 모의 평가(`venv_vllm`, GPU 없음, 00:34:15–00:34:49Z): `e05 --data jsel_dev/P2 --split dev --episodes 4` → `E05_DONE`, claim `insufficient_data`(성공 창 뒤집힘 없음 → `flip_rate_success` 없음, N194와 같은 설계), retest_flip n 535·0.0; `rd --variants standard=jsel_dev,dr=gen_dev/dr/P1 --episodes 5` → `RD_DONE`(dr 낙폭 −0.0015 [−0.0044, 0.0], n 680); `calib --heldout jsel_dev/P0 --episodes 4` → `CALIB_DONE`; `e05 --truth outcome:plan`(POOL 2017·2069·2112) → `E05_DONE`, claim `a_as_stabilizer`, `judge_input` 필요 키 모두 있음, retest_flip n 410·0.0. 네 산출 모두 `meta.git` 3d4738a dirty false·`prereg` OK·부트스트랩 10,000 시드 0 percentile.
- **N214.** (절차, 자체 점검·재설계) ① R2_TRAIN 훑기 폴더 standard/bottle_tray/P1·dr/mug_tray/P2는 편이 200개라 60 % 위치부터 100편이 80편만 나옴 → 합 260편(300 아님; 셈은 그대로 보고). ② `closed37.py`의 호출 시각 비교가 내가 가정한 키 이름(`t`·`t_send`·`t_call`)이 없어 빈 비교가 됐다 → `callkeys37.py`로 실제 키(`t_state`·`t_deliver`·`latency_s`)를 뽑아 다시 비교(56/56 같음). ③ `attr37.sh`의 열린 핸들 1은 그 스크립트 파일을 연 bash 자신 → 정리는 `bash -s`로 흘려 핸들 0에서 실행. ④ 정리 스크립트의 명령줄 검사는 `grep 'r7c3[7]'`로 자기 일치를 피함(P70). ⑤ 음성 대조 원본 = dr/mug_tray/P0 **ep0**(274프레임; 24–36회차 원본과 다름). ⑥ LeRobot 새 입력: 유효 standard/mug_marker/P0 ep2·dr/bottle_tray/P0 ep3(28–36회차 LeRobot 입력과 겹치지 않음) + 무효 standard/bottle_tray/P0 ep3(무효 DEV 4편이 모두 쓰였으므로 가장 오래전(33회차) 것 재사용).
- **N215.** DEV 12 판 `meta.code_sha` = `05e42ada69c2143d` = 36회차 값(로컬 사본 `common.code_sha()`도 같음) — 코드 무변경과 일치.
- **N216.** (P72 기계 검사) handoff 전체와 책 7장 전체의 백틱·링크 저장소 경로(`R/`·`P/` 약칭 풀어서, 중괄호 펼침, `:줄` 꼬리 제거) **215개**를 3d4738a 사본에서 확인: 없는 경로 0. 걸린 1건 `docs/design/Mx-*.md`(handoff `:66`)는 `x`가 번호 자리표시 → `M*-*.md` M1–M10 존재(N183·N196과 같은 판단). 36회차 220개와 개수가 다른 것은 토큰 나누는 규칙 차이.
- **N217.** 텍스트 위생·기계 검사(`check37`): 변경 md 4개 BOM·CR·C0·C1·영폭·탭 0, 표 칸 수 불일치 0(H2); 책 7장 표 칸 수 불일치 0, 링크 **115개** 끊김 0(H3); 이 범위의 책 변경 0 → 06 새 줄 필요 없음, 06 23행 모두 칸 4·시각 비내림(H4); 책 01 상태 칸(H5) **40칸** — `끝` 35·`` `[결과 전]` `` 1(E-MA2)·`` `[예정]` `` 4, 벗어난 칸 0; R7 보고서 판정 줄(H7) 36개 ↔ handoff §2.8 36줄 판정 모두 같고, 건수가 적힌 회차는 네 건수까지 같음; handoff §0 세 줄 모두 확인 시각 있음(H8); 현재형 상태어 검색(H9) — 새 것 없음(02·06 이력 인용, README·04 규칙 문장, `01:4` 규칙 설명, `01:38` "E2E 준비 기준점(아직)" — 3d4738a 시점 연속 무결 1이라 참).
- **N218.** 내 Isaac 창(00:36:34–00:40:04Z) 전·후 목록 차로 생긴 항목: `tmp/carb.mEwAKL`(00:36:35)·`tmp/tmpxn09g2la`(00:36:53)·`pyc_r6/…/tmpxn09g2la`·`pyc_r6/…/r7c37`(772 KB)·`kitcache/cyclo-r7c37_standard`(208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-MA2 c2 학습(pid 1669127, 00:14:28Z 시작 — 내 창 전, `PYTHONPYCACHEPREFIX` = `pyc`)뿐 → 모두 내 것(§6.6).

---

## 5. 사전 등록 대조표 (원 등록 문서에서 다시 만든 행, 행마다 이번 회차의 새 입력으로 행동 확인)

`prereg.json` 해시(E-first §2.7·2A.6·3.7·4.8·5.6): 로컬 `prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = OK(closed·e05·rd·calib). 사전 등록 md 11개·계획·정본은 ffe335c와 같다(H1 — `docs/design`·`docs/superpowers`·`docs/stage3/prereg*` diff 0). 원문 재확인(`const37.py`, 코드 객체에서 직접 출력): E-first `§1.5` 표(DEV 0~29 / CAL 500~549 / TEST 1000~1149 / TEST-P5 1300~1329 / POOL 2000~2119 / R2_TRAIN 10000~59999) = `eval/splits.py` `RANGES`, 경계 20점(−1·0·29·30·499·500·549·550·999·1000·1149·1150·1299·1300·1329·1330·1999·2000·2119·2120)의 `split_of`가 표와 같음; 성공 규칙 "1 s 연속·60 s" = `planner.CFG` `success_hold_s` 1.0·`episode_limit_s` 60.0; 부트스트랩 10,000(§1.7) = `stats.N_BOOT`; γ 2/3 = `m4.GAMMA` "2/3"(정확 분수: 2/3 참, 1999/3000 거짓, 2000/3000 참); H 3·STALE_MAX 1.5·lead_max 1.0·W 1 = `M4Params`(lead_max 0·NaN·−1e-12 거부); `early_ask_steps(0, 0.3, 1/3, 1.0)` = [1, 2, 3], lead_max 0.3334 → [1]; Astra = `astra_hb.py`(`gpt-6-astra`, low, 600; K0–K4). "확인" 열: **로컬** = `check37.py`·`hashes37.py`·`const37.py`·`usedvals37.py`, **파드** = §6(`pod_cpu37.sh`, `pod_eval37.sh`·`data37.py`·`gtxt37.sh`·`e05o37.py`·`lr37.sh`·`lr0check37.sh`·`lr0b37.sh`, `pod_isaac37.sh`·`closed37.py`·`callkeys37.py`, `attr37.sh`·`clean37.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E §1.5, §66) | `eval/splits.py`, `datagen/gen.py` | 가드(§6.3): TEST 1097·1109, CAL 517·513·(calib fit) cal, TEST-P5 1324·(calib heldout)·(rd), DEV 2,47·1188, POOL 2143, gen 23456(확인 없음)·9989·60077(확인 있음), determinism 1041·4,2127, 다른 분할 허용 2건(17 `test`→test_p5·18 `test_p5`→cal) → 모두 거부; `split_of` 경계 20점 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | `calib --heldout jsel_dev/P0 --episodes 4` → `CALIB_DONE`(dir_xy 적합 T 0.055·`ambiguous` 적합 7·보류 11); 가드 3(`--fit-split cal`, heldout P1 dev)·4(`--heldout-split test_p5`, heldout P2) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | `CFG` 1.0·60.0; DEV 12 C5·C5' 둘 다 **성공 종료** 18.77 s·1,877스텝, 두 조건 같음 | 일치 |
| **6** | 호출 기록·Astra A6 (E §1.6, §28) | `core.py` | **DEV 12 결정 호출 112행**(조건마다 56): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs` 정규화·`canary_id`·`question_id@vN` 112/112; Astra 4행 요청 해시·이미지 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치(N155) |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 (E §1.7) | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` n_boot 10000·seed 0·percentile(closed·e05·rd·calib); e05 `gain_holm` level 0.975(두 가설 Holm); `meta.prereg` OK | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P2 --split dev --episodes 4` → `E05_DONE`(claim `insufficient_data`, N213); 가드 24(`canary build-set --data jsel_dev/P1 --seeds 3133-3134`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | γ 정확 분수 경계(위); 코드 무변경·시험 묶음; `meta.m4_H` 3·`m4_lead_max` 1.0; calib J5 q̂(α 0.05·0.1·0.2) 출력 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `"C5,C14"` → "condition 'C14': runtime has ['C0' … 'C6']", 가드 33 `--m4-h=-4` → "M4 H = -4 … >= 1"(N211); **DEV 12 C5 `last_step` {none 1, OK 32, LAG 8, DEVIATE 15}, C5' none 56/56, 요청 본문 마지막 `last_step:` 줄 = 행 값 112/112** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P1 --episodes 5` → `RD_DONE`(dr 낙폭 −0.0015 [−0.0044, 0.0], n 680); 가드 5 `rd --variants dr=gen_dev/dr/P1 --split test_p5` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-1e-300` → "lead_max = -1e-300 … finite > 0 s", 15 `=Infinity` → "lead_max = inf …", 워커 전 거부; `M4Params` 0·NaN·−1e-12 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·51–58; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1), 시험 묶음 | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2017,2069,2112 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`, retest n 410, N213) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 12, 00:36:34–00:40:04Z)**: 행동 **1,877개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 56·Astra 2 같은 수·같은 `t_state`·`t_deliver`·답 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | 18폴더 **가운데 3시드** 54편(10299–10301·10699–10701·10899–10901) 3d4738a 검증기 재실행 대 도장 메타: 오류 0·`valid_for_training`·`structural_ok` 불일치 0(유효 43) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119"(폴더 없음); 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 11`·`1e0` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 12 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0; 가드 26 `K13`·27 `"K1,K2,K4"`(예산 없음) 거부 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 입력**(standard/mug_marker/P0 ep2·dr/bottle_tray/P0 ep3 참, standard/bottle_tray/P0 ep3 **거짓**): 내보낸 편 2·558프레임(267 + 291, 무효 편 건너뜀 ✓, 과제 2), `verify` 오류 0·PSNR 최소 39.14 dB·lerobot 0.3.3 적재 558프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 구조 검사 (§66, 완료 정의 1, `r2_datagen.md:55`) | `datagen/validate.py` | **DEV 36/36 오류 없음**, 검증기 대 메타 불일치 0; R2_TRAIN 54편(행 101); **새 대조 16종**(dr/mug_tray/P0 ep0, 274프레임): 무수정 오류 0; 행 k101 `H` 15.0(실수) → 오류 0; 프레임 줄 137 `k` 137.0(실수) → 오류 0; 행 k174 `proprio_mask {q: True, grip: False}` → 오류 0; 행 k76 `action_exec` 문자열 → "could not convert string to float: 'r7c37'"; 행 k144 `hz` None → "hz None != 30"; k0 머리 경로 → 20바이트 JPEG 머리(SOF 없음) → "k0 cam_head: size None != native (672, 376)"; 행 k210 `proprio.q` 8값 → "proprio.q: 7 values"; 행 k30 `valid` 전부 0 → "valid: H values in {0,1}, first step valid"; 라벨 행 k140 중복 → "labels_v2 rows != decision frames"; 프레임 k137 손목 경로 `""` → "k137: missing cam_wrist_right" + "images 547 != frames 274 x cams 2"; npz `q[0, 0]` −inf → "npz q: length 274 (want 274) or non-finite"; 메타 `success` 0 → `structural_ok` 참·오류 0·`valid_for_training` 거짓. 관찰: `proprionan` 오류 0, `npznotau` KeyError, `tstr` TypeError(N210). 실데이터 훑기 불일치 0 | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 112/112 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 12 Astra 4행 effort low, 요청 본문 `"effort": "low"` | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 유료 0; E-MA2 관문 줄은 36회차 확인 그대로(handoff §0 확인 23:46, 무변경) | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | `harvest/`·`tools/`·`tests/` diff 0(H1); 가드 28(`predict --aux-extra a3d@v7` → argparse "invalid choice … ('none', 'a3d@v1')"); `code_sha` 무변(N215) | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 이 범위 책 변경 0; 상태 칸 40개 0 벗어남, 링크 115개 끊김 0, 표 칸 수 0 불일치, 06 23행 형식 맞음(N217) | 일치 |
| **156** | 정본 = 마지막 절까지 | — | 정본 무변경(H1), 마지막 절 §86 | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3·E-MA1(b) 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond` | 옵트인 가드 29(**`predict`** 경로 `--data r2 --cam3 cam3@v1` → "--cam3: --data se2e only")·30(**`evalck`** 경로 `--data se2e --cam3 cam3@v1 --motion-line none` → "--cam3: with the motion line (prereg_cam3 cells)")(둘 다 rc 1, 적재 전)·31(`kvcond@v7`)·32(`cam3@v10`) argparse 거부; 등록 블롭 해시 26/26 | 일치 |
| **158** | handoff §0 = 확인 시각에 참인 진행 상태, 결과 커밋 때 삭제(README `:11`, P69) | — | LeRobot 줄(23:27) 파드 mtime으로 확인 시각에 참(N212); **R7 줄(00:25)** 참(36회차 PASS·연속 1); E-MA2 줄(23:46) 무변경(36회차 N203) | 일치 |
| **159** | 결과 문서 = 원자료 (책 README `:7`, P68) | — | 이 범위의 결과 문서 = `r7_cycle36.md`(§6.2) | 일치 |
| **160** | 인용 경로 = 커밋에 있음 (P72) | — | handoff 전체·책 7장 경로 215개 없음 0(N216) | 일치 |
| **161** | 사전 등록 E-MA2 (`prereg_ma2.md`) | `r2_ma2`, `tools/ma2/*` | 등록 해시 8/8(무변); 옵트인 가드 36–39 | 36회차 실험 절 PASS 유지 |

### 5.1 36회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드 + `split_of` 경계 20점), 5·6·51–58·99·137·151(DEV 12), 7–12(rd·calib 메타 추가), 13–17·61–62(jsel_dev/P2·gen_dev/dr/P1), 2–4(jsel_dev/P0), 18–50(γ 정확 분수 경계), 66–67(`-1e-300`·`Infinity` + `M4Params` 직접), 98(POOL 2017·2069·2112), 101(가운데 3시드), 138(새 입력), 139(새 대조 16종), 157(`predict`·`evalck` 경로 가드), 158(§0 LeRobot 줄 mtime 재확인). 새 행 없음.

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status ffe335c 3d4738a`(4파일): M `docs/draft-log.md`(`@@ -488,0 +489 @@` +1), M `docs/handoff.md`(`@@ -3 +3 @@` 머리, `@@ -12 +12 @@` §0 R7 줄, `@@ -141,0 +142 @@` §2.8 36회차 줄 +1), M `docs/stage3/direction-log.md`(`@@ -82,0 +83 @@` +1), A `docs/stage3/results/r7_cycle36.md`(195줄; 커밋 블롭 = 작업 트리 파일). `harvest`·`tools`·`tests`·`configs`·`docs/design`·`docs/superpowers`·`docs/book`·`paper`·`prereg*` diff 0. 요청된 구성(보고서, handoff §0 R7 줄·§2.8 36회차 줄·머리 시각, draft-log 줄, direction-log 행)과 정확히 같다.

### 6.2 바뀐 줄마다 대 출처
| 바뀐 줄·주장 | 출처 | 판정 |
|---|---|---|
| handoff `:3` "마지막 갱신: 2026-09-26 00:25 UTC" | ≤ 커밋 `3d4738a` 00:25:49Z; 36회차 머리 00:20:35Z 뒤 | 맞음 |
| handoff `:12` §0 R7 줄 "(확인 2026-09-26 00:25 UTC): 36회차 기준선 PASS(연속 무결 1) → 37회차가 PASS면 E2E 준비 기준점 태그" | `r7_cycle36.md:11` 판정 PASS·연속 무결 1, `:193` 다음 할 일 1 | 맞음 |
| handoff `:142` §2.8 36회차 줄: 대상 ffe335c, 보고서 머리 00:20:35 UTC, DEFECT 0·DOC 0·SCOPED 20·NOTE 152, 실험 절(E-MA2) PASS, 연속 무결 1, N193(`validate.py:65` KeyError, N132 계열), N192 | `r7_cycle36.md:3`(`date -u` = 2026-09-26T00:20:35Z)·`:4`(ffe335c)·`:11`–`:20`(표)·`:20`(실험 절)·`:50`–`:51`(N192·N193); 3d4738a 사본 `validate.py:65` = `if [r["k"] for r in rows] != list(range(K)):`(N193 서술과 같음) | 맞음 |
| draft-log `:489` "00:25 UTC 기록(2026-09-26): R7 36회차 기준선 PASS(연속 무결 1; 대상 ffe335c), 실험 절(E-MA2) PASS." | `r7_cycle36.md:4`·`:11`·`:20`; 시각 ≤ 커밋 | 맞음 |
| direction-log `:83` "\| 00:25 \| R7 36회차 \| 결함 0 · 문서 0, E-MA2 코드 등록 대조 통과 \| PASS → 연속 무결 1 \|"(칸 4) | `r7_cycle36.md:11`–`:22` | 맞음 |
| `r7_cycle36.md` 건수·머리 시각(handoff 줄이 인용) | 표 DEFECT 0·DOC 0·SCOPED 20·NOTE 152(H7), SCOPED S1–S20 20개; NOTE 계산 "35회차 143 − 해소 6 + 새 15(N192–N206) = 152" 산술 맞음, 새 N192–N206 15개 연속, 해소 6개(N174·N175·N178·N179·N181·N182)는 35회차 새 번호 N173–N191과 범위 밖 N182이고 36회차 활성 목록에 없음, 35회차 표 NOTE 143 = 35회차 계산(128 − 4 + 19)과 같음(H10); 머리 시각 00:20:35Z는 36회차 로컬 산출 mtime 순서(정리 출력 09:19:40 KST = 00:19:40Z < 00:20:35Z < 커밋 00:25:49Z)와 맞음 | 맞음 |
| `r7_cycle36.md` 텍스트 | BOM·CR·C0·C1·영폭·탭 0, 표 칸 수 불일치 0(H2) | 맞음 |

### 6.3 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 00:33:48–00:34:15Z, 21–36회차와 다른 값; 사유는 `gtxt37.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data jsel_dev/P0 --split test --seeds 1097`, 2 `e05 --data jsel_dev/P1 --split cal --seeds 517`, 3 `calib --fit-split cal --heldout P1 --heldout-split dev`, 4 `calib --fit-split pool --heldout P2 --heldout-split test_p5`, 5 `rd --variants dr=gen_dev/dr/P1 --split test_p5`, 6–8 `closed --split test --seeds 1109`·`cal 513`·`test_p5 1324` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 2,47` → "seeds [47] are not in split dev", 10 `pool --seeds 2143`, 11 `dev --seeds 1188` → "(refused, never opened)"; 12–13 `--isaac-gpu 11`·`1e0` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-1e-300`, 15 `=Infinity` → "lead_max = -1e-300 / inf … finite > 0 s"; 16 `--conditions "C5,C14"` → "condition 'C14': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=test` + `closed --split test_p5 --seeds 1326` → "set HARVEST_ALLOW_SPLIT=test_p5", 18 `=test_p5` + `e05 --data P2 --split cal --seeds 545` → "set HARVEST_ALLOW_SPLIT=cal"; 19 `gen --seeds 23456`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9989 --confirm-train`, 21 `--seeds 60077 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 1041`, 23 `history --seeds 4,2127` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P1 --seeds 3133-3134`, 25 `e05 --data P1 --split pool --seeds 2091` → "no episode selected"; 26 `--hb-mode K13` → "from ('K0', …, 'K4')", 27 `--hb-mode "K1,K2,K4"`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d@v7` → argparse "invalid choice" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 predict --data r2 --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 evalck --data se2e --cam3 cam3@v1 --motion-line none` → "--cam3: with the motion line (prereg_cam3 cells)"(둘 다 rc 1, 체크포인트·데이터 적재 전), 31 `se2e_kvcond train --expert-cond kvcond@v7`, 32 `se2e_cam3 train --cam3 cam3@v10` → argparse "invalid choice" rc 2. **추가**: 33 `closed --m4-h=-4` → "M4 H = -4: decision steps per call must be >= 1"; 34 `gen --variant random --seeds 10444 --confirm-train` → "variant 'random' is the TEST pool … (canon §34 D35)", 35 `gen --kinds P5 --seeds 2` → "DEV perturbations P0-P2 only". **E-MA2 옵트인(실험 절)**: 36 `r2_ma2 predict --data se2e --ma2 c2` → "--ma2: --data r2 only"(rc 1, 적재 전), 37 `train --ma2 C1` → "invalid choice … ('off', 'c0', 'c1', 'c2')", 38 `ma2eval` `--ckpt` 없음 → "the following arguments are required: --ckpt", 39 `ma2eval --ma2 "c2 "` → "invalid choice … ('c0', 'c1', 'c2')"(37–39 rc 2). **39건 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.4 A. 테스트
- 로컬(`…\r7c37\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c37/pt tests`): EXIT 0, **1156 passed · 21 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1307 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.5 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 16종 + 실데이터 훑기(DEV 36편 10,651프레임·10,615행, R2_TRAIN 260편 77,788프레임·77,528행 불일치 0); R2_TRAIN 가운데 3시드 54편 재검증; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀). |
| 2 모델 | 충족(CPU) | CPU 스모크(N208: 손실 감소·저장·재적재 동일·지연), CPU 묶음의 단계 A·B 시험 통과, 기준선 코드 무변경. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 12 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c37`: `CLOSED_DONE`, 호출 56·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 00:34:15–00:34:49Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`(N213). |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`·`isaac_gpu`; 정리 뒤 흔적 없음(§6.6). |

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 검토 시작·끝 작업 트리 깨끗(이 파일 외).
- 파드 정리 대상 판별(`attr37.sh`, 00:40:15Z): 내 Isaac 창(00:36:34–00:40:04Z)에 생긴 `tmp/carb.mEwAKL`·`tmp/tmpxn09g2la`·`pyc_r6/…/tmpxn09g2la`·`pyc_r6/…/r7c37`(772 KB)·`kitcache/cyclo-r7c37_standard`(208 MB) — N218.
- 파드 정리(Write로 만든 `clean37.sh`를 `bash -s`로, 열린 핸들 0·`IR_INST=r7c37` 프로세스 0 확인 뒤, 00:41:46Z): `tmp/r7c37`(503 MB), 위 Isaac 항목 5개. 끝에 r7c37 항목 0(tmp·kitcache·pyc 캐시), 파드 루트 `/C:` 없음, 명령줄에 r7c37이 든 프로세스 0, `IR_INST=r7c37` 프로세스 0, 열린 핸들 0, GPU 0·1 0 MiB. 남의 `export_all.sh`·`run_ma2.sh`·`r2_ma2` 그대로.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a37.tar` 삭제, 스크립트·작은 출력만 남김(`r7c37` 약 0.6 MB); 지시대로 `D:\tools\scratch_qdd\r7c35` 삭제 — r7c 폴더는 r7c36·r7c37만. D: 여유 8.0 GB. C: 쓰기 없음.

## 7. 실험 코드 절

검토할 새 실험 코드 없음(위 판정 절). E-MA2 결과가 커밋되면 다음 회차 실험 절에서 판정 재계산(`ma2_verdict.py` 독립 구현)과 E-N1·E-N2 한계 서술을 본다.

## 8. 다음 순회 전에 할 일 (제안)
1. **37회차 기준선 PASS — 연속 무결 2 = E2E 준비 기준점(태그 대상 `3d4738a`).**
2. (선택, NOTE) 태그 뒤 TDD 묶음: 검증기 예외 계열 N132·N193·N210 ②③(`KeyError`·`TypeError` 대신 구조 오류), 통과 계열 N131·N142·N143·N154·N165·N190·N210 ①(행 고유감각 유한성은 계약에 넣을지 결정부터); N155(결합 구현 때); N192(paper 다음 4시간 갱신); N212(handoff §0 LeRobot 줄 다음 갱신 때 새로).
3. 38회차가 있다면 대상은 3d4738a 이후 HEAD.
