# R7 객관 검증 순회 — 33회차 (cycle 33, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle32.md`의 표·결론을 근거로 쓰지 않고 d0e25f4·76ab10c의 바뀐 줄마다 diff·원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드는 **21–32회차와 다른 새 값**. 작성 2026-09-25 22:55 UTC 무렵(로컬 사본 풀기 22:38:08Z, 파드 첫 명령 22:38:46Z, 파드 정리 끝 22:52:33Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`d0e25f4`**(`d0e25f4f9448f99d519c4d9d1fe310766d9a886f`, 커밋 시각 2026-09-26 07:36:22 +0900 = **2026-09-25 22:36:22 UTC**, "R7 cycle 32 baseline FAIL (DOC 2) — handoff §0 R2_TRAIN line rewritten from pod script output, book 01 R7 row points to §2.8 instead of a PASS list, N139/N141/N149 markers, records"). `4c532d2..d0e25f4` = 커밋 2개: **`76ab10c`**(22:22:11 UTC, E-CAM3·E-MA3 결과) + `d0e25f4`. 13파일, 모두 문서(책 01–06, 정본 +2줄, draft-log, handoff, direction-log, 새 `cam3.md`·`ma3.md`·`r7_cycle32.md`); **코드·시험·사전 등록 변경 0**(`check33` H1). 뒤 커밋은 범위 밖. 작업 트리에는 이 보고서만 추가.
- **범위 나눔(32회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책. 76ab10c의 정본 보충(§57 보충·§84 보충 3)·handoff·draft-log·책 01–06·결과 문서 `cam3.md`·`ma3.md`의 서술은 기준선 문서로 검토했다. **실험 코드 절**(따로 판정) = E-CAM3·E-MA3 코드(`harvest/train/se2e_cam3.py`·`se2e_kvcond.py`, `tools/cam3`·`tools/ma3`, `tools/se2e/paired_verdict.py`)의 사전 등록 대비 동작, 파드 예측·평가 파일로 판정 재계산, 등록 → 학습 순서, 기준 재사용 비트 동일, 기준 파일 무수정.
- 사본: `git -c core.autocrlf=false archive d0e25f4`(tar 주석 = `d0e25f4f9448…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c33\repo`에 풀었다(**596파일** = 32회차 593 + `r7_cycle32.md`·`cam3.md`·`ma3.md`, 텍스트 512파일 CR 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c33/code`(597파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `d0e25f4f9448…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle32.md`, 정본 `00-interfaces.md` §1–§86 보충·§57 보충·§84 보충 3(`:779`–`:780`, 뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(`prereg.json` 해시, `prereg_*.md` 10개 — 특히 `prereg_cam3.md`·`prereg_ma3.md`), 결합 설계 스펙 §12, 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P71.
- 분류(32회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0의 줄은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약, 추정 표시가 있는 수치, 반올림·부호 표기 차이, 시각이 붙은 이력 표시는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c33`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c33`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c33_standard`, `--inst-prefix r7c33`); GPU 0·2·3에는 아무것도 올리지 않음. R2_TRAIN `final_check.sh`는 이미 끝나 있었고(`FINAL_DONE 22:36:38Z`) 파일·로그는 읽기만; 남의 프로세스(`export_all.sh` LeRobot 내보내기 6개, `loadercheck.sh`)는 건드리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **PASS** (연속 무결 0 → **1**)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 20 |
| NOTE | 117 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — E-CAM3·E-MA3 코드 결함 0, DOC 0; 두 판정 모두 파드 원자료에서 독립 재계산으로 재현(불채택)**

**기준선 코드는 32회차 대상(4c532d2 = ac7a314 코드)과 바이트가 같고 모든 동작 검사가 통과했다**: 로컬 **1133 passed / 20 skipped**(235.1 s), 파드 CPU **1280 passed / 4 skipped**(166.6 s), LeRobot 6 passed; 가드 **28건 + 실험 옵트인 4건 + 추가 1건 = 33건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–32회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 대조 13종**(통과해야 할 경계 4종 통과, 검출해야 할 9종 모두 검출) + 관찰 2종; 실데이터 일관성 훑기(DEV 36편 10,651프레임 + R2_TRAIN 새 3폴더 300편 91,067프레임: 불일치 0); 모의 평가 한 명령씩 완료; 새 시드 **DEV 6**에서 같은 Isaac 워커 C5 → C5' 행동 **1,551개 비트 동일**. **32회차 정정 두 건(D-1·D-2)과 N139·N141·N149 표시가 모두 원자료와 맞고**, 76ab10c의 결과 반영(정본 보충 2개, 책 01–05 + 06 줄, handoff §0 줄 삭제·§2.8 줄, draft-log)의 모든 수치가 파드 예측·평가 파일에서 다시 계산한 값과 같다.

---

## 1. DEFECT

없음. (`git diff --name-status 4c532d2 d0e25f4`에 `harvest/`·`tools/`·`tests/`·`prereg*` 경로 0, 정본은 보충 2줄 추가만 — `check33` H1.)

## 2. DOC

없음.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 생성 끝(npz·jsonl 마지막 P0 18:08:13Z·P1 20:02:13Z·P2 21:56:26Z), `final_check.sh` 끝(`check.log`: `CHECK_EXIT 0 22:32:29Z wall_s=2097`, `FINAL_DONE 22:36:38Z`, `CHECK {"episodes": 6000, "valid": 5126, "rows": 1800160}`). 병합·검사 결과 문서는 아직 커밋되지 않음(메인 세션 일). 확인 인자 없는 `--seeds 10002` 거부(가드 19).
- S3. CAL 보정·TEST 평가(메인 세션, `HARVEST_ALLOW_SPLIT`) — 가드 §6.4.
- S4. RB1 라이선스(§63-(6)) — E-CAM3·E-MA3 체크포인트도 내부용 표기.
- S5. §67 C8.
- S6. Astra 카나리 "none"(§67 보충).
- S7. S-E2E 계열 체크포인트의 런타임 형식 차이(§77 보충 (2), §80).
- S8. CONTRADICT-soft(§68 K6).
- S9. §73 D5 M4 설계 확장.
- S10. §73 N5 E1 범위.
- S11. §74 보충 E-M4-lat 비례 STALE_MAX.
- S12. §75 보충 (2) E-M4 판정 7.
- S13. §77 N8 (13): 완료 정의 밖 사전 등록 실험(E-CAM3·E-MA3 포함).
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — d0e25f4에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. 정본 §82 구현 및 §84·§86(+보충) 결합 설계 구현("R7 관문 뒤") — 지금 코드: `closed --hb-mode K9`·`"K2,K4"`(예산 없음) → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 6 Astra 4행), 흐름 호출 없음.
- S19. 정본 §83 런타임 적용("R7 관문 뒤") — DEV 6 결정 호출 요청 94/94 `motion:` 없음.
- S20. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).
- (32회차 S20 "E-CAM3·E-MA3 결과 없음"은 76ab10c로 해소 → 실험 절 §7에서 검토.)

## 4. NOTE
- N1–N3, N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45, N46, N49–N53, N57, N58, N71, N73, N74, N79, N90, N91, N94, N129, N131–N138, N142–N148. (그대로.) N10 재현: 가드 25(`e05 --data jsel_dev/P1 --split pool --seeds 2101` → "no episode selected")가 빈 `g25/`를 남김. N94: `final_check.sh` 끝, 결과 문서는 메인 세션 일(S2).
- N4, N47, N48, N54–N56, N66–N70, N72, N84–N88, N92, N93, N102–N108, N116–N122, N128, N130. (해소, 그대로.)
- N109–N115, N123–N127. (이전 회차 자체 기록.) 계산: 32회차 109 − 해소 3(N139·N140·N149) + 새 11(N150–N160) = **117**.
- **N139.** (해소) handoff `:136` 31회차 줄 "보고서 머리 22:09 UTC, 파드 정리 22:07 UTC [… R7 32회차 N139]", draft-log `:482` "22:09 UTC(보고서 머리; 파드 정리 22:07 …)", direction-log `:78` "22:09" — `r7_cycle31.md:3`(작성 22:09 무렵, 파드 정리 끝 22:07:14Z)과 같다 ✓.
- **N140.** (해소) handoff §0 E-CAM3·E-MA3 줄이 결과 커밋 76ab10c에서 지워졌다(README `:11` 규칙대로 같은 커밋) ✓.
- **N141.** (표시됨 — NOTE 유지) 책 `04:63` 괄호 끝에 "[→ 2026-09-25 22:36 UTC, R7 32회차 N141: 위 괄호의 '파일럿 병합분'은 22:0x UTC 이후 `gen check`가 다시 병합하며 낡음 — 병합 결과는 R2_TRAIN 결과 문서에 기록하고 이 괄호는 그 커밋에서 정리한다]" — 첫 재병합 22:01:16Z(`dr/bottle_tray/P0.stageb.jsonl` mtime = ctime)와 맞고, 06 `:25` 줄 ✓. 정리는 R2_TRAIN 결과 커밋에서.
- **N149.** (해소) handoff `:136` "`validate.py:78`(… `decision` 표지 …, N131)·`:82-85`(npz에 `grip` 없으면 `:83`에서 KeyError, N132)" — d0e25f4(`validate.py` 마지막 변경 `6111b4e`)에서 `:78` = `miss_v = […ln["decision"]…]`, `:82`–`:85` = npz 키 고리, `:83` = `a = z[key]` ✓. 같은 줄 "32회차가 실데이터 336편에서 불일치 0" = 36 + 300 ✓, N142·N143 서술 ✓.
- **N150.** handoff `:11` §0 R2_TRAIN 줄(확인 22:35 UTC) — **확인 시각에 참**: 생성 끝 21:56:26Z(npz·jsonl mtime, `dr/mug_marker/P2/ep10999.npz`; P2 폴더마다 602 항목), `final_check.sh` 시작 21:57:31Z(`check.log` `CHECK_START 21:57:32Z`)이고 22:35에는 아직 실행 중(`FINAL_DONE 22:36:38Z` — 커밋 22:36:22Z보다도 뒤), 행 파일 18개 모두 mtime = ctime 22:01:16–22:32:29Z(21:57Z 뒤 18/18, 22:35Z 뒤 0), `labels_v2` 18/18도 21:57Z 뒤, `check.json` mtime = ctime 22:32:29Z. 인용한 `r2stat.sh`는 로컬 `D:\tools\scratch_qdd\r2stat.sh`(22:35:52Z 작성, 파드로 흘려 실행; 내용 = `ps`·`TZ=UTC stat -c %Y`·21:57Z 비교·`check.json` `ls`) — 적힌 방법과 같다. 세부: 22:35에는 괄호가 정의한 `gen check` 단계 자체는 이미 `CHECK_EXIT 0`(22:32:29Z)로 끝났고 `final_check.sh`가 `verify_merge`·`analyze`·`du` 단계였다 — 줄은 스크립트 기준으로 쓰였으므로 참. 다음 갱신 때 결과 커밋과 함께 README 규칙대로 줄을 지운다.
- **N151.** 책 `01:38` R7 행 결과 칸은 이제 "회차별 PASS·FAIL은 handoff §2.8(… R7 32회차 D-2; 예: 8회차 DEFECT 5)"(`r7_cycle8.md` DEFECT 5 ✓)이고, 그 뒤에 옛 목록을 가리키던 정정 표시 "[→ 정정 … 20:01 UTC, R7 26회차 D-1: 6회차 PASS 누락; …]"가 남아 있다 — 시각이 붙은 이력 표시라 NOTE. `(아직)`(기준점 칸)은 32회차 N144와 같은 안내 문장.
- **N152.** (부호 표기) E-MA3 청크 오차 감소를 문서마다 다른 부호로 적었다: 책 `01:65`·`ma3.md` 1절 표 "합동 상대 감소 **+2.19 %** [+1.48 %, +2.88 %]", 정본 `:780` "2.19 % [1.48 %, 2.88 %]", 책 `03:70` "청크 오차 −2.19 % [하한 1.48 %]", draft-log `:483` "−2.19 % [1.48, 2.88]"(점은 음수, 구간은 양수), `ma3.md` 1절 본문 "s1 −3.4 %, s2 −1.0 %". 재계산 값(상대 감소 0.021875, 구간 [0.01479, 0.02881], 시드 0.03407·0.00968)과 크기는 모두 같고 "오차 변화 = −, 감소 = +"로 읽으면 뜻도 같다 → NOTE. 다음에 쓸 때 "상대 감소 +2.19 %"로 통일 권함.
- **N153.** `cam3.md` 3절 관문 (1) "다른 두 키(`aux_extra`·`a3d_root`)는 기준 뒤에 생긴 옵션의 기본값(`none`)" — `a3d_root`의 기본값은 `none`이 아니라 `/data/harvest/data/ma1b/conv`(`stageb_train.py:843`)이고 `args_check_s1.out`의 값도 그 경로다(`ma3.md`는 "기본값만 다름"으로 바르게 적음). 결론(두 키는 기준 `config.args`에 없음 = 옵션 도입 전 체크포인트, `check_resume_args` `:320`–`:327`이 없는 키를 기본값으로 봄)은 맞다 → NOTE(요약 표기).
- **N154.** (검증기 관찰, 새 종류 `rowkind`·`labval`) 행 `kind`를 다른 문자열로 바꾸거나 labels_v2 행의 k 밖 필드(`seed`)를 바꿔도 오류 0 — `check_row`는 필드 존재만, 라벨은 k 집합만 본다(N143과 같은 계열). 실데이터 훑기에서 행 kind 불일치 0. 권함: N142·N143과 함께 태그 뒤 TDD(행·라벨 `seed`·`kind` = 편 메타).
- **N155.** (런타임 관찰) DEV 6 판은 15.51 s에 성공으로 끝났고, 그때 in-flight였던 Astra hb 1건은 행이 없다: 요약 `astra_by_kind {hb 2, sub 1}`(= `astra_hb.sent()`가 센 보낸 수 3, `astra_hb.py:106`–`:108`) 대 `astra_calls` 2·Astra 행 2(`core._deliver_hb`가 전달 때만 행을 씀, `core.close()`는 `cancel_futures=True`). 정본 §28 A6·§77 D4는 기록할 필드를 정하고 편 끝 미전달 호출은 정하지 않아 사전 등록 위반은 아니며, 실제 유료 Astra 경로는 S18(R7 관문 뒤). 결합 설계 구현 때 "편 끝 미전달" 행(hb_no·t_send·요청 해시)을 남겨 비용 장부와 맞추기를 권함.
- **N156.** 시험 수: 로컬 **1133 passed / 20 skipped**(235.1 s, 22:38:13–22:42:09Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c33/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(166.6 s, 22:40:02–22:42:52Z), 경고 1(기존), LeRobot 6 passed(17.8 s). 32회차와 같은 수(코드 무변경). 로컬 `tools/prereg_hash.py --check` → OK, `tools/intent_check.py` → flagged 0.
- **N157.** 단계 B 소형 CPU 스모크(22:46:34Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–32회차와 같은 값 — 결정적), expert p50 0.041 s·전체 p50 0.115 s, 맥락 토큰 454.
- **N158.** DEV 6 판: 행동 1,551·15.51 s(`terminations` success 1 — 32회차 DEV 19의 40 s 상한과 달리 성공 종료 경로를 탔다), 결정 호출 47(조건마다), C5 `last_step` {none 1, OK 31, LAG 9, DEVIATE 4, CONTRADICT 2}, C5' none 47/47, 확정 비율 0.9447, 결정 3.032/s, rtf 0.508, 지연 p50·p95 0.3 s, Astra 행 2(hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0; N155), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28–32회차와 같음), 파일명 `dev6-P0-standard-e0`, 판 206.3 s(22:47:31–22:50:57Z). 파드 GPU 전·후 모두 0 MiB(0–3).
- **N159.** (절차, 자체 점검) ① 음성 대조 `commitval`을 처음에는 "비어 있지 않은 `committed`가 있는 행의 값 바꾸기"로 설계했으나 원본 편(dr/mug_marker/P0 ep2)의 어느 행에도 `committed`가 없어 스크립트가 "no row matches"로 멈췄다 → "알려진 질문 이름(`dir_xy`) + 가짜 값"을 한 행에 넣는 것으로 다시 설계하고 다시 돌렸다(첫 실행의 중간 산출은 모두 새 사본으로 덮임). ② 음성 대조 원본 = dr/mug_marker/P0의 **세 번째** 유효 편 ep2(267프레임; 25–32회차 원본과 다름). ③ LeRobot 새 입력: 유효 standard/mug_marker/P0 ep5·dr/mug_tray/P0 ep3(26–32회차와 겹치지 않음) + 무효 standard/bottle_tray/P0 ep3 — DEV의 무효 편 4개가 모두 이미 쓰였으므로 가장 오래전(28회차) 것을 다시 썼다. ④ 가드 13 `--isaac-gpu 1.0`은 문자열 검사(`closed.py`)로 워커 전 거부됨을 확인. ⑤ 정리 스크립트는 `bash -s`로 흘려 명령줄에 태그가 없게 했고, 자기 매칭은 `grep 'r7c[3]3'`로 피했다.
- **N160.** 텍스트 위생·기계 검사(`check33`): 사본 텍스트 512파일 CR 0; 변경 md 13개 BOM·CR·C0·C1·영폭 0, 표 행 칸 수 불일치 0(H3); 책 링크 108개 끊김 0(H4); **책 변경 커밋마다 06 줄**(H5): 76ab10c는 책 01·02·03·04·05를 바꾸고 06 `:24` "2026-09-25 22:21 | 01·02·03·04·05 | …"(22:21 ≤ 커밋 22:22:11Z ✓, 칸 4 ✓), d0e25f4는 책 01·04를 바꾸고 06 `:25` "2026-09-25 22:36 | 01·04 | …"(22:36 ≤ 22:36:22Z ✓). 책 01 상태 칸 기계 검사(H11): 상태 칸 있는 표 3개(`:9` 7칸 20행·`:42` 8칸 9행·`:58` 5칸 11행; `:34` 표 B는 상태 칸 없음) 상태 칸 **40개** — `끝` 34·`` `[예정]` `` 5·`` `[결과 전]` `` 1(E-CAM3·E-MA3 두 칸이 `끝`으로), 벗어난 칸 0, 칸 수 불일치 0. 현재형 진행 상태 검색(H9) — 02·06 이력 인용, README·04 규칙 문장, `01:38` "(아직)", `03:13`·`03:63` "실행 중 흐름/Astra effort"(결정 내용)뿐. R7 보고서 판정 줄(H10): PASS [6, 16, 20, 22, 31], FAIL 27개 — handoff §2.8 줄 32개 모두 보고서와 같은 판정.

---

## 5. 사전 등록 대조표 (원 등록 문서에서 다시 만든 행, 행마다 이번 회차의 행동 확인)

`prereg.json` 해시(E-first §2.7·2A.6·3.7·4.8·5.6): 로컬 `prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = OK. 사전 등록 md 10개·계획은 4c532d2와 같고(H1), 정본은 보충 2줄만 추가. 기준선 코드 = 4c532d2(= ac7a314)와 같음. "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c33\check33.py`(H1·H3·H4·H5·H9·H10·H11)·`hashes33.py`, **파드** = §6(`pod_cpu33.sh`, `pod_eval33.sh`·`data33.py`·`gtxt33.sh`·`lr33.sh`, `pod_isaac33.sh`·`closed33.py`·`astra33.py`, `r2state33.sh`·`gentime33.sh`, `ls33.sh`·`exp33.py`·`exp33b.py`, `attr33.sh`·`clean33.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV 0–29/CAL 500–549/TEST 1000–1149/TEST-P5 1300–1329/POOL 2000–2119/R2_TRAIN 10000–59999 (E :113-120, §66, 책 `04:63`) | `eval/splits.py`, `datagen/gen.py` | 가드(§6.4): TEST 1133·1117, CAL 507·533, TEST-P5 1326, DEV 27,32·1990, POOL 2122, gen 10002(확인 없음)·9996·61000(확인 있음), determinism 1136·27,1995, 다른 분할 허용 2건(17·18) → 모두 거부 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | `calib --heldout jsel_dev/P1 --episodes 2` → `CALIB_DONE`; 가드 3(`--fit-split test`)·4(`--heldout-split test`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | DEV 6 C5·C5' 둘 다 **성공 종료** 15.51 s·1,551스텝(`terminations` success 1), 두 조건 같음 | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 6 결정 호출 94행**(조건마다 47): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 94/94; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치(N155) |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P1 --split dev --episodes 2` → `E05_DONE`(claim `insufficient_data`); 가드 24(`canary build-set --data P0 --seeds 3180-3181`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H`·`m4_lead_max` 3·1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,C9"` → "condition 'C9': runtime has ['C0' … 'C6']", 가드 33 `--m4-h -2` → "M4 H = -2 … >= 1"; **DEV 6 C5 `last_step` {none 1, OK 31, LAG 9, DEVIATE 4, CONTRADICT 2}, C5' none 47/47, 요청 본문 마지막 `last_step:` 줄 = 행 값 94/94** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P1 --episodes 2` → `RD_DONE`(dr 낙폭 평균 −0.0032); 가드 5 `rd --variants dr=gen_dev/dr/P1 --split test_p5` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-2.5` → "lead_max = -2.5 … finite > 0 s", 15 `=1e500` → "lead_max = inf … finite > 0 s", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(22:52Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2019,2081,2117 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 6, 22:47:31–22:50:57Z)**: 행동 **1,551개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 47·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | 생성 끝 21:56:26Z, `final_check.sh` 끝 22:36:38Z(§3 S2) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119"(폴더 없음); 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 5`·`1.0` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 6 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0; 가드 26 `K9`·27 `"K2,K4"`(예산 없음) 거부 | 일치(N155) |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 입력**(standard/mug_marker/P0 ep5·dr/mug_tray/P0 ep3 참, standard/bottle_tray/P0 ep3 **거짓**): 내보낸 편 2·549프레임(288 + 261, 무효 편 건너뜀 ✓), `verify` 오류 0·PSNR 최소 39.09 dB·lerobot 0.3.3 적재 549프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1, `r2_datagen.md:55`) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 대조 13종**(dr/mug_marker/P0 ep2, 267프레임): 무수정 오류 0; 행 k93 `valid` 끝 한 칸 0(끝 패딩) → 오류 0; 행 k146 알려진 aux reg `g2goal_dist` 삭제 → 오류 0; 행 k172 `committed {dir_xy: 'r7c33_bogus'}` → 오류 0; 행 k66 `hz 30.5` → "hz 30.5 != 30"; 행 k106 `action_exec` 열 하나 빼기 → "shape (15, 7), expected (15, 8)"; 행 k199 `valid` 16값 → "valid: H values in {0,1}"; 행 k53 aux cls `r7c33_cls` → "unknown aux names ['r7c33_cls']"; 행 k239 `kind` 삭제 → "missing field 'kind'"; 행 k26 `proprio.qd` 8값 → "proprio.qd: 7 values"; 끝 프레임 k266 → 271 → "frame indices not contiguous from 0" + 시각 격자; 프레임 k133 `cam_wrist_right` 키 이름 → `cam_wrist_left` → "k133: missing cam_wrist_right" + "images 533 != frames 267 x cams 2"; npz `t` 가운데 NaN → "npz t: … non-finite". 관찰: `rowkind`·`labval` 오류 0(N154). 실데이터 훑기 불일치 0(N131) | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 6 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | E-CAM3·E-MA3 결과 문서 3절 자체 검사 관문 표·재설계 없음(§7) | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 코드 변경 0(H1); `git diff 7a02943 d0e25f4` 기준 파일 7종·`harvest/runtime` 빈 결과; 가드 28(`--aux-extra a3d@v3` → argparse "invalid choice") | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 상태 칸 40개 기계 검사 0 벗어남, 링크 108개 끊김 0, 책 변경 커밋 2개 모두 06 줄 ✓; 76ab10c 책 수치 = 파드 재계산(§6.2); `01:38` 목록 제거(32회차 D-2 해소) | 일치(N151·N152·N141) |
| **156** | 정본 §86 = 탐침 결과 + 보충; §57 보충·§84 보충 3 = 결과 문서 | — | `:779`·`:780` 수치·등록 커밋·문턱 = `cam3.md`·`ma3.md`·재계산(§6.2) | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond`, … | 옵트인 가드 29(`train --data r2` → "--data se2e only")·30(`train` 움직임 줄 없음 → "with the motion line")·31(`kvcond@v3`)·32(`Cam3@v1`) 거부; 판정 재계산 = 불채택 두 건(§7) | 일치 |
| **158** | handoff §0 = 확인 시각에 참인 진행 상태(README `:11`, P69) | — | R2_TRAIN 줄(22:35) 참(N150), R7 줄(22:36) 참, E-CAM3·E-MA3 줄은 결과 커밋에서 삭제 | 일치 |

### 5.1 32회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드), 5·6·51–58·99·137·151(DEV 6 — 성공 종료 경로), 13–17·61–62(jsel_dev/P1·gen_dev/dr/P1), 2–4(jsel_dev/P1), 66–67(`-2.5`·`1e500`), 98(POOL 2019·2081·2117), 101(`FINAL_DONE`), 138(새 입력), 139(새 대조 13종 + 관찰 2종 + 새 R2_TRAIN 폴더 훑기), 153·156·157(E-CAM3·E-MA3 결과), 155·158(32회차 D-1·D-2 해소).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status 4c532d2 d0e25f4`: M 책 01–06, 정본(+2), draft-log, handoff, direction-log; A `cam3.md`·`ma3.md`·`r7_cycle32.md`. 코드·시험·사전 등록 0.
- 76ab10c: 책 01(E-CAM3·E-MA3 두 줄), 02(아. 절 P70·P71), 03(§57 상태 칸, §57 보충·§84 보충 3 행), 04(모듈·도구·코드 사본·체크포인트 행), 05(GPU 두 줄), 06 +1; 정본 `:779`·`:780`; handoff 머리 22:21·§0 E-CAM3/E-MA3 줄 삭제·§2.8 `:128` 새 줄; draft-log `:483`.
- d0e25f4: 책 01 `:38`, 04 `:63` N141 표시, 06 `:25`; handoff 머리 `:3` 22:36·§0 `:11`·`:12`·§2.8 `:136`(수정)·`:137`(새); draft-log `:482`(수정)·`:484`(새); direction-log `:78`(수정)·`:79`(새); `r7_cycle32.md`.

### 6.2 바뀐 줄마다 대 원자료
| 바뀐 줄 | 원자료·원 문서 | 판정 |
|---|---|---|
| handoff `:11` R2_TRAIN "(확인 22:35 UTC, `r2stat.sh`) 생성 끝(21:56:26Z)" | npz·jsonl 마지막 21:56:26Z(`gentime33.sh`), P2 6폴더 602 | 맞음 |
| 같은 줄 "`final_check.sh` … 21:57:31Z부터 실행 중" | `CHECK_START 21:57:32Z`, `FINAL_DONE 22:36:38Z` > 22:35 | 맞음(N150) |
| 같은 줄 "폴더 행 파일 18개 모두 21:57Z 뒤 다시 병합됨" | 18/18 mtime = ctime 22:01:16–22:32:29Z, `MERGE` 줄 18개 | 맞음 |
| 같은 줄 "`check.json`은 22:32:29Z에 새로 씀" | mtime = ctime 22:32:29Z | 맞음 |
| 같은 줄 D-1 정정 표시 "22:11 줄 … 그때 이미 6개 파일이 다시 병합" | 22:11 이전 재병합 `dr/bottle_tray/P0–P2`(22:01:16·22:02:34·22:03:15Z)·`dr/mug_marker/P0–P2`(22:06:55·22:08:07·22:08:51Z) = 6 | 맞음 |
| handoff `:12` R7 "(확인 22:36 UTC) 32회차 기준선 FAIL(DOC 2) → 연속 무결 0 → 33회차" | `r7_cycle32.md:11` FAIL·DOC 2·연속 0 | 맞음 |
| handoff `:3` "마지막 갱신 22:36 UTC" | ≤ 커밋 22:36:22Z | 맞음 |
| handoff `:136` 31회차 줄(N139·N149 반영) | 위 N139·N149 | 맞음 |
| handoff `:137` 32회차 줄 "대상 4c532d2 … DEFECT 0, DOC 2(D-1 …, D-2 …), SCOPED 21, NOTE 109. 실험 절 PASS. 코드는 ac7a314와 바이트 동일. 정정(22:36 UTC) … 연속 무결 0 → 33회차" | `r7_cycle32.md:11`–`:20`, H1(코드 무변경) | 맞음 |
| draft-log `:482`·`:484`, direction-log `:78`·`:79`(칸 4) | 위 두 보고서 | 맞음 |
| 책 `01:38` 결과 칸 "회차별 PASS·FAIL은 handoff §2.8(… 32회차 D-2; 예: 8회차 DEFECT 5)" | §2.8 32줄 = 보고서 판정(H10), `r7_cycle8.md` DEFECT 5 | 맞음(N151) |
| 책 `04:63` N141 표시 | 첫 재병합 22:01:16Z | 맞음 |
| 06 `:25` "22:36 \| 01·04 \| …" | 바뀐 장 01·04, 22:36 ≤ 22:36:22Z | 맞음 |
| **76ab10c** 책 `01:63` E-CAM3 "none 0.7067/0.7076 → cam3 0.7111/0.7059, 합동 +0.0014 [−0.0041, +0.0069], 전이 +0.0016, FULL p95 +11.7 %(84.6 → 94.6 ms; 356 → 460), 불채택, ≈ 1.7 GPU-h" | `exp33.py`: 정답 3,814/3,838/3,819/3,810 of 5,397, 합동 0.001390, 구간 [−0.004076, +0.006856], 전이 +0.001589, p95 84.649 → 94.569 ms(비 1.11718), 토큰 356·460 | 맞음 |
| 책 `01:65` E-MA3 "0.02960/0.03062 → 0.02859/0.03033, +2.19 % [+1.48 %, +2.88 %], 시드 3.4 %·1.0 %, 결정 +0.0061 [+0.0009, +0.0113], FULL p95 −3.4 %" | 청크 평균 0.029598/0.028589/0.030623/0.030327, r 0.021875 [0.014794, 0.028811], 시드 0.03407·0.00968, 결정 0.006115 [0.000926, 0.011303], p95 119.41 → 115.37 ms(비 0.96618) | 맞음(N152) |
| 정본 `:779` §57 보충·`:780` §84 보충 3; 책 03 `:33`·`:34`·`:70` | 같은 값, 층 3·8·12·17·21·26·30·35(체크포인트 `stageb.json`), 등록 커밋 `5c46056`·`40895f8` | 맞음(N152) |
| 책 02 P70·P71 | P71 "+0.006 [+0.0009, +0.011]" ✓, `clip_grad_norm_(params, 1.0)`가 모든 매개변수 묶음의 전체 노름(`stageb_train.py:352`·`:362`·`:394`) ✓; P70 "R2_TRAIN 작업자는 21:56에 이미 끝" = 생성 끝 21:56:26Z ✓ | 맞음 |
| 책 04 새 행 | `se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3`(3)·`tools/ma3`(3)·`paired_verdict.py` 존재; 파드 `code_cam3`·`code_ma3`·`ckpt/cam3/cam3_s{1,2}`·`ckpt/ma3/kv_s{1,2}` 존재, `img_cam3` JPEG **36,177**(RB1 22,378·RB2 13,799) | 맞음 |
| 책 05 두 줄 | 학습 20:42:33–21:23:35(41.0분)·21:28:00–22:08:33(40.6분); 20:45:14–21:23:05(37.9분)·21:28:08–22:06:22(38.2분) (`driver_main.out`) | 맞음 |
| 06 `:24` "22:21 \| 01·02·03·04·05" | 바뀐 장과 같음, ≤ 22:22:11Z | 맞음 |
| handoff §0 E-CAM3·E-MA3 줄 삭제, §2.8 `:128` | README `:11`; "≈ 3.4 GPU-h, 유료 0원" = 1.7 × 2 | 맞음 |
| draft-log `:483` | 등록 시각·값·이탈(파드 `python -c` 1·heredoc 2·`pkill -f`) = `cam3.md` 4절 | 맞음(N152) |
| `cam3.md`·`ma3.md` 2절 판별 값(질문별·NLL 층별·원천별·지연 p50·GPU p95·dec_acc 궤적·학습 시각) | `exp33.py`·`exp33b.py`·체크포인트 `log.jsonl`: 질문별 0.653/0.818/0.650 … 모두 같음, NLL 합동 +0.0017(전이 −0.0001·정상 +0.0049), MA3 흐름 손실 +2.37 % [1.62, 3.10]·팔 MAE +0.51 % [0.15, 0.89]·예측 조건 청크 +1.83 % [1.08, 2.58], dec_acc 궤적 네 판 같음, NaN 0 | 맞음(N153) |

### 6.3 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 22:44:46–22:45:04Z, 21–32회차와 다른 값; 사유는 `gtxt33.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data jsel_dev/P1 --split test --seeds 1133`, 2 `e05 --data P0 --split cal --seeds 507`, 3 `calib --fit-split test --heldout P0 --heldout-split dev`, 4 `calib --fit-split pool --heldout P1 --heldout-split test`, 5 `rd --variants dr=gen_dev/dr/P1 --split test_p5`, 6–8 `closed --split test --seeds 1117`·`cal 533`·`test_p5 1326` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 27,32` → "seeds [32] are not in split dev", 10 `pool --seeds 2122`, 11 `dev --seeds 1990` → "not in split … (refused, never opened)"; 12–13 `--isaac-gpu 5`·`1.0` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-2.5`, 15 `=1e500` → "lead_max = -2.5 / inf … finite > 0 s"; 16 `--conditions "C5,C9"` → "condition 'C9': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test --seeds 1044` → "set HARVEST_ALLOW_SPLIT=test", 18 `=test` + `e05 --data P0 --split cal --seeds 546` → "set HARVEST_ALLOW_SPLIT=cal"; 19 `gen --seeds 10002`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9996 --confirm-train`, 21 `--seeds 61000 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 1136`, 23 `history --seeds 27,1995` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P0 --seeds 3180-3181`, 25 `e05 --data P1 --split pool --seeds 2101` → "no episode selected"; 26 `--hb-mode K9` → "from ('K0', …, 'K4')", 27 `--hb-mode "K2,K4"`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d@v3` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 train --data r2 --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 train --data se2e --cam3 cam3@v1`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)", 31 `se2e_kvcond train --expert-cond kvcond@v3`, 32 `se2e_cam3 predict --cam3 Cam3@v1` → argparse "invalid choice" rc 2. **추가**: 33 `closed --m4-h -2` → "M4 H = -2: decision steps per call must be >= 1". **33건 모두 rc ≠ 0**(28·31·32 rc 2, 나머지 rc 1); 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.4 A. 테스트
- 로컬(`…\r7c33\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c33/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.5 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 13종(+관찰 2) + 실데이터 훑기(DEV 36·R2_TRAIN 새 3폴더 300편 불일치 0); LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀, 행 138); `se2e_c1` **5/5 OK**. |
| 2 모델 | 충족(CPU) | CPU 스모크(N157), CPU 묶음의 단계 B·E-MA1b·E-CAM3·E-MA3 시험 통과, 기준선 코드 무변경. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 6 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c33`: `CLOSED_DONE`, 호출 47·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 22:45:04–22:45:39Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함).
- 파드 정리 대상 판별(`attr33.sh`, 22:52:09Z): 내 Isaac 창(22:47:31–22:50:57Z)에 생긴 `tmp/carb.pmRbHF`(22:47:32 생성)·`tmp/tmpvfkg813q`(22:47:49, `_remote_module_non_scriptable.py`)·`pyc_r6/…/tmpvfkg813q`·`pyc_r6/…/r7c33`(772 KB)·`kitcache/cyclo-r7c33_standard`(208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`이거나 `pyc_r6` 접두인 다른 프로세스 0 → 모두 내 것.
- 파드 정리(`clean33.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 22:52:33Z): `tmp/r7c33`(508 MB), 위 Isaac 항목 5개. 끝에 r7c33 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c33이 든 프로세스 0, `IR_INST=r7c33` 프로세스 0, 열린 핸들 0. 정리 뒤 남의 `export_all.sh` 7개 그대로. R2_TRAIN 파일·로그는 읽기만.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a33.tar` 삭제, 보고 근거 스크립트·출력만 남김; 지시대로 `D:\tools\scratch_qdd\r7c31` 삭제 — r7c 폴더는 r7c32·r7c33만. C: 쓰기 없음.

## 7. 실험 코드 절 (별도 판정: PASS)

### 7.1 등록 → 학습 순서, 고정 코드
- 등록 커밋 `5c46056`(20:33:20Z, 문서 시각 20:30:33Z)·`40895f8`(20:34:19Z, 20:34:02Z). 코드 사본 `code_cam3` 20:33:47Z·`code_ma3` 20:34:43Z(커밋 뒤), 기준 재예측·청크 평가 20:34–20:45Z, **학습 시작** `cam3_s1` 20:42:33Z(첫 로그 20:43:05Z)·`kv_s1` 20:45:14Z(첫 로그 20:45:44Z) — 둘 다 등록 커밋 뒤. 등록 전 20:22–20:25Z 20스텝 사전 실행은 두 등록 0.3절에 공개(개발 사본, 판정 불사용).
- 등록 7절 LF 블롭 sha256 앞 16자리 16개 = d0e25f4 사본 16/16 일치(`hashes33.py`); 파드 고정 사본 `code_cam3` 5/5·`code_ma3` 5/5 일치, 두 사본의 기준 파일 7종(`stageb_train/model/data/expert`·`prefix_share`·`se2e_data`·`se2e_temporal`)이 d0e25f4와 바이트 같음(`exp33.py`).
- 기준 파일 무수정: `git diff --name-status 7a02943 d0e25f4 -- harvest/runtime stageb_train.py stageb_model.py stageb_data.py stageb_expert.py prefix_share.py se2e_data.py se2e_temporal*` 빈 결과(체크포인트 해시 대상 `PROMPT_FILES(_B)`가 든 `stageb_data.py`·`stageb_model.py` 포함). 새 코드는 새 파일 두 개(`5c46056^..40895f8`: 코드 +385줄은 `se2e_cam3.py`·`se2e_kvcond.py`뿐, 나머지 도구·시험).

### 7.2 동작 대 사전 등록
- `se2e_cam3.py`: 이미지 목록 = [머리, 활성 손목(기준 이름표 그대로), 반대 손목 `"<left|right> wrist camera (other arm):"`] — 기준 두 이미지 보존, 양팔 행(이미지 3장) 그대로(`:40`–`:68`); 프레임 없으면 `FileNotFoundError`(`:61`); 활성 이름표가 팔과 다르면 거부(`:57`); `prompt_config`에 `cam3`·`layout3`·파일 해시 넣고 sha 재계산(`:76`–`:82`) — 체크포인트 `prompt_config.sha` `0d79e8b3d51e`, `cam3 cam3@v1`, `layout3 D27v3-cam3`; 옵션 끔이면 `stageb_train.main` 그대로(`:99`), `--data se2e`·움직임 줄 요구(가드 29·30). 등록 2절과 같음.
- `se2e_kvcond.py`: 층 ⌊(i+1)·36/8⌋−1 = 3, 8, 12, 17, 21, 26, 30, 35(`:42`–`:43`; 체크포인트 `expert_cond` 같은 값·`kv_dim` 1024); K = `k_norm` 출력(회전 전, `flatten(-2)`), V = `v_proj` 출력(`:117`–`:118`); 블록마다 LayerNorm + Linear K·V 따로(`:65`–`:72`); KI stop만(`:180`), K·V detach(`:122`)·`insulate`(`:171`); 새 사상은 기준 헤드 뒤 생성(`:101`–`:107`); `load_heads_kv`는 기본 체크포인트면 `load_heads` 그대로(`:204`–`:205`). 등록 2절과 같음.
- 판정 스크립트(`cam3_verdict.py`·`ma3_verdict.py`·`paired_verdict.py`): 규칙 네 조건·CMP_EPS·엄격 하한·입력 검사(키 집합·1,799·중복·요약 재현·청크 평균 = 요약)가 등록 6절 문장과 같다.

### 7.3 판정 재계산 (파드 `/data/harvest/logs/{cam3,ma3}` 읽기만, 실험 판정 코드를 부르지 않는 자체 구현 `exp33.py`)
- **기준 재사용 비트 동일**: `cam3/predfull_none_s{1,2}.jsonl` 대 `se2e_confirm/predfull_motion_s{1,2}.jsonl` 항목 5,397개 순서까지 `utc` 밖 동일, 요약 다른 키 0; `ma3/chunk_none_s{1,2}.jsonl` 항목 5,397 동일, 요약은 새 필드 `chunk_mse_pred`·`expert_cond`만 추가(옛 필드 차이 0). 네 판 키 집합 같음(1,799, 해시 `eeefe665e542`), 전이 표지 파일 sha 앞 12 `7bcfc8f609c2`(등록 값).
- **E-CAM3**: 합동 +0.001390(s1 +24항목 +0.00445, s2 −9항목 −0.00167), 부트스트랩(시드 0) [−0.004076, +0.006856], 전이 +0.001589, FULL p95 비 1.117179 → (1) ✗ (2) ✗ (3) ✓ (4) ✗ → **불채택** — `verdict_full.json`과 모든 값 같음. 다른 부트스트랩 시드(20260926)에서도 [−0.00398, +0.00686] → 같은 판정.
- **E-MA3**: 청크 상대 감소 합동 0.021875(s1 0.034073, s2 0.009677), 구간 [0.014794, 0.028811], 결정 정확도 합동 +0.006115 [+0.000926, +0.011303], FULL p95 비 0.966182 → (1) ✗ (2)–(4) ✓ → **불채택** — `verdict_full.json`과 모든 값 같음; 다른 시드 구간 [0.01480, 0.02867]도 같은 판정.
- 관문: 학습 로그 비유한 값 0(네 판), 검증 dec_acc 궤적(step 500–2000) 결과 문서와 같음, 학습 시간 41.0·40.6·37.9·38.2분(각 문턱 90·75분 안), 재설계 없음(등록 8절 변경 기록 없음과 일치).

### 7.4 DOC (실험 절)
없음.

### 7.5 NOTE (실험 절)
- E-N1–E-N19. (32회차 그대로.)
- **E-N20.** 기준 재사용 조건 (1)의 문자 그대로 검사(`args_check_s1.out`)는 `"equal": false`(`a3d_root`·`aux_extra`가 기준 `config.args`에 없음)다. 두 결과 문서가 이를 공개하고 `check_resume_args`(`stageb_train.py:320`–`:327`, 없는 키 = 옵션 기본값)로 같은 설정이라 판단했으며, 새 판의 두 값이 파서 기본값(`none`, `/data/harvest/data/ma1b/conv` — `:841`·`:843`)이고 조건 (2) 비트 동일이 기본 경로 불변을 보이므로 등록 위반으로 보지 않는다(N153은 표기만).
- **E-N21.** 판정 재계산은 실험 코드와 독립인 구현으로 했고(같은 추출 방식 → 같은 구간, 다른 시드 → 판정 불변), 예측·평가 파일은 읽기만 했다.

## 8. 다음 순회 전에 할 일 (제안)
1. **33회차 기준선 PASS — 연속 무결 1.** 34회차가 기준선 PASS면 E2E 준비 기준점(연속 2회). 기준선 코드는 태그 전까지 바꾸지 않는다.
2. handoff §0 R2_TRAIN 줄: `final_check.sh`는 22:36:38Z에 끝났다(`CHECK_EXIT 0`, valid 5,126/6,000, 행 1,800,160) — 결과 문서를 커밋할 때 README 규칙대로 §0 줄을 지우고 책 `04:63` 괄호 정리(N141)·06 한 줄을 같은 커밋에. 정정 문장은 파드 명령 출력으로 확인한 뒤(P68).
3. (선택, NOTE) N152(E-MA3 부호 통일), N153(`cam3.md` 기본값 표기), N155(편 끝 미전달 Astra 행 — 결합 설계 구현 때), N142·N143·N154(검증기 한 줄씩 — 기준점 태그 뒤 TDD), N151(옛 정정 표시).
4. 34회차 대상은 d0e25f4 이후 HEAD, **연속 무결 1에서**.
