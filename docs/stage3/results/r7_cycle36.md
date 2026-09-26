# R7 객관 검증 순회 — 36회차 (cycle 36, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle35.md`의 표·결론을 근거로 쓰지 않고 `b2b0b3e..ffe335c`의 바뀐 줄마다 diff·원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). R2_TRAIN 정정 수치는 R2_TRAIN 에이전트 스크립트와 35회차 스크립트를 쓰지 않고 원 파일(`ep*.meta.json`·`workers.log`·`det/cmp*.json`·`pilot/`)에서 새 스크립트(`r2chk36.py`·`detshow36.py`)로 다시 셌다. 가드·음성 대조·Isaac 시드·모의 평가 입력·LeRobot 입력은 **21–35회차와 다른 새 값**. 작성 2026-09-26 00:20 UTC(`date -u` = 2026-09-26T00:20:35Z; archive 2026-09-25T23:59:49Z, 로컬 사본 풀기 00:00:19Z, 파드 첫 명령 00:04:44Z, 파드 정리 끝 00:19:39Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`ffe335c`**(`ffe335cac7c5a7ed0554cb95e6687142ebec811d`, 커밋 시각 2026-09-26 08:58:51 +0900 = **2026-09-25 23:58:51 UTC**). `b2b0b3e..ffe335c` = 커밋 5개(요청된 구성과 같음): `fde4f6a`(23:33:15Z, E-MA2 사전 등록·코드·시험, 책 01·06, handoff §0), `daed3f5`(23:46:22Z, handoff §0 E-MA2 진행 줄), `54b9205`(23:57:20Z, paper/ 4시간 갱신 14파일), `a73f6bb`(23:58:34Z, 35회차 정정·기록), `ffe335c`(23:58:51Z, 35회차 보고서 머리 시각 정정·handoff 줄). 뒤 커밋은 범위 밖.
- **범위 나눔(35회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책(paper/는 분류 규칙상 NOTE 수준). **실험 코드 절**(따로 판정) = 이번 범위의 E-MA2 코드(`harvest/train/r2_ma2.py`, `tools/ma2/`, 시험 4개).
- 사본: `git -c core.autocrlf=false archive ffe335c`(tar 주석 = `ffe335ca…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c36\repo`에 풀었다(**609파일** = 35회차 599 + `prereg_ma2.md`·`r2_ma2.py`·`tools/ma2/` 3·시험 4·`r7_cycle35.md`, 텍스트 552파일(.tex 포함) CR 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c36/code`(610파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `ffe335ca…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle35.md`, 정본 `00-interfaces.md` §1–마지막 절(보충 포함, 뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(`prereg.json` 해시, `prereg_*.md` 11개 — 새 `prereg_ma2.md` 포함, E-first `§1.5`·`§1.6` 원문), 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P72.
- 분류(35회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0·결과 문서의 `[결과 전]` 항목은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. 정정 표시(`[→ 정정 …]`)가 붙은 원문은 DOC가 아니다. SCOPED·NOTE는 35회차 정의 그대로.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c36`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c36`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c36_standard`, `--inst-prefix r7c36`); GPU 0·2·3에는 아무것도 올리지 않음. 남의 프로세스(E-MA2 `run_ma2.sh` A·B와 그 학습·평가 — GPU 2·3; R2 LeRobot `export_all.sh`)는 건드리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음. **E-MA2 예측·평가 파일은 열지 않음**(학습 로그 `train_c0.out`·`train_c1.out`의 관문 줄, 데이터·명령 표·화살표 입력 이미지, 드라이버, 코드 사본만 읽음; `eval_set.json`도 열지 않고 명령 표에서 다시 만들어 등록 sha와 비교).

## 판정 (기준선): **PASS** (DEFECT 0 · DOC 0 → 연속 무결 **1**)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 0 |
| SCOPED | 20 |
| NOTE | 152 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — E-MA2 코드 결함 없음**

`fde4f6a`의 E-MA2 코드(`r2_ma2.py`, `tools/ma2/build_ma2.py`·`ma2_latency.py`·`ma2_verdict.py`, 시험 4개)를 `prereg_ma2.md` §2·§3·§5·§6 원문과 동작으로 대조: 되짚기 명령·50 % 배정·문장·화살표·재라벨·평가 회전·준수율·판정 규칙이 등록과 같다(§7). 등록 커밋 `fde4f6a`(23:33:15Z)가 본 실행(`run_ma2.sh` A·B와 첫 학습 프로세스 23:33:49Z, 첫 학습 스텝 23:35:42Z)보다 앞선다. 실행 코드 사본 `/data/harvest/code_ma2`(`COMMIT` = `fde4f6a`)는 ffe335c 사본과 `harvest/`·`tools/`·`tests/` 328파일 바이트 동일, 등록 블롭 해시 8/8 일치. **기준선 파일 수정 0**(`git diff --name-status b2b0b3e ffe335c`의 `harvest/`·`tools/`·`tests/` 항목은 모두 `A`). NOTE 4건(§7).

**기준선은 코드 변경 없이(새 파일만) 모든 동작 검사가 통과했고, 문서 변경은 모두 출처와 같다**: 로컬 **1156 passed / 21 skipped**(= 35회차 1133/20 + E-MA2 새 시험 23 통과·1 건너뜀), 파드 CPU **1307 passed / 4 skipped**, LeRobot 6 passed; 가드 **39건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–35회차와 다른 경계값, E-MA2 옵트인 가드 4건 포함); R2 DEV `validate_episode` **36/36** + **새 종류 대조 13종**(통과해야 할 경계 4종 통과, 검출해야 할 7종 모두 검출, 특수 1종 맞음, 관찰 1종); R2_TRAIN **끝 3시드** 54편 재검증(ffe335c 검증기 대 도장된 메타 불일치 0); 실데이터 훑기(DEV 36편 + R2_TRAIN 새 3폴더 25 % 위치부터 100시드씩 300편 90,690프레임: 불일치 0); 모의 평가 한 명령씩 완료; 새 시드 **DEV 23**에서 같은 Isaac 워커 C5 → C5' 행동 **1,775개 비트 동일**. **35회차 정정(D-1·D-2·N174·N175·N178·N179·N181)과 새 E-MA2 문서 줄은 모두 원자료와 같다**(§6.2).

---

## 1. DEFECT

없음. (`b2b0b3e..ffe335c`의 `harvest/`·`tools/`·`tests/` 변경은 새 파일 8개(`A`)뿐이고 `M` 0 — `check36` H1. 기존 기준선 코드는 b2b0b3e와 바이트 동일.)

## 2. DOC

없음. 바뀐 문서 줄 전부를 원자료와 대조했다(§6.2). 35회차가 지적한 두 곳은 정정 표시와 함께 고쳐졌다: `r2_train_gen.md:107`·책 `01:69`·`draft-log:486`의 794, `r2_train_gen.md:31`(원문 + 정정 표시)·`:32`·`:157`의 본 생성 12:00–21:56Z·9 h 56 min·파일럿 검사가 관문이 아님. 저장소 전체(docs·paper) 검색에서 고치지 않은 798·12:15 시작·9 h 40·8쌍·9.8 s·21.4 GPU-h 사본 없음(`check36` H14; 06 `:26`의 21.4는 이력 줄).

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN(§66, §77 N8 (4)) — 원본·병합·로더 확인 끝, 결과 문서 커밋됨. LeRobot 내보내기는 `[결과 전]`(handoff §0 확인 23:27 UTC 줄). 확인 인자 없는 `--seeds 10777` 거부(가드 19).
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`) — 가드 §6.3.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8. S6. Astra 카나리 "none"(§67 보충). S7. S-E2E 체크포인트 런타임 형식 차(§77 보충 (2), §80). S8. CONTRADICT-soft(§68 K6). S9. §73 D5 M4 설계 확장. S10. §73 N5 E1 범위. S11. §74 보충 E-M4-lat 비례 STALE_MAX. S12. §75 보충 (2) E-M4 판정 7. S13. §77 N8 (13) 완료 정의 밖 사전 등록 실험(E-MA2 포함). S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석(그대로). S15. §79 보충 `flip_th` 질문별 사전화. S16. §78 "남은 것"(dr·random 변형, CUDA PhysX, P2 결정성 행렬). S17. §78 (2) 옛 물리 녹화 재녹화·재라벨(책 01 `:70` `[예정]`).
- S18. 정본 §82·§84·§86(+보충) 결합 설계 구현("R7 관문 뒤") — `closed --hb-mode K12`·`"K2,K3,K4"`(예산 없음) 워커 전 거부(가드 26·27), DEV 23 Astra 요청 이미지 1장·effort low·600, 흐름 호출 없음.
- S19. 정본 §83 런타임 적용("R7 관문 뒤") — DEV 23 결정 호출 요청 106/106 `motion:` 없음.
- S20. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3, N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45, N46, N49–N53, N57, N58, N71, N73, N74, N79, N90, N91, N129, N131–N138, N142–N148, N151–N155, N162, N164–N173, N176, N177, N180, N183–N191. (그대로.) N10 재현: 가드 25(`e05 --data jsel_dev/P0 --split pool --seeds 2114`)가 빈 `g25/`를 남김. **N155 재현**: DEV 23에서 요약 `astra_by_kind {hb 2, sub 1}`(3) 대 Astra 로그 행 2(hb 5.0 → 8.0, sub 8.01 → 11.01) — 에피소드 끝(17.75 s)에 날아가던 hb 호출이 행을 남기지 않음; 결합 구현 때 처리로 미룬 NOTE 그대로(사전 등록 동작·완료 정의를 깨지 않음 — 결정 호출 행은 106/106 온전). 검증기 N131·N132·N142·N143·N154·N165·N190: 태그 뒤 TDD(그대로; 새 관찰 `nok`도 같은 계열, N193).
- N4, N47, N48, N54–N56, N66–N70, N72, N84–N88, N92–N94, N102–N108, N116–N122, N128, N130, N139–N141, N149, N161, N163. (해소·표시, 그대로.) N109–N115, N123–N127, N156–N160(이전 회차 자체 기록).
- **해소(이번 회차, 수에서 뺌)**: **N174**(`r2_train_gen.md:78` 9.8 s → 9.7 s·정정 표시, 원자료 `sim_time_s` 평균 9.7247), **N175**(`:20` 8쌍 → 6쌍·정정 표시; `det/cmp1–3.json`의 `runs[0]`은 기준 자신, 기준 대 새·이력 2쌍 × 3 = 6, `cmp3a`는 중복 — `detshow36.py`), **N178**(책 05 21.3(21.34) — 10.6697 h × 2 = 21.339), **N179**(책 05 사용률 `[미검증]` 표기), **N181**(handoff §2.8 34회차 줄에 보고서 머리 시각 23:20 UTC 표시 = `r7_cycle34.md` 머리와 같음), **N182**(범위 밖이던 `fde4f6a` — 이번에 검토). 계산: 35회차 143 − 해소 6 + 새 15(N192–N206) = **152**.
- **N192.** (paper, NOTE 수준) `paper/mindmap/sec/4_experiments.tex`의 이번 판 줄 "09-25 23:56 UTC"와 `paper/sec/5_plan.tex` E-MA2 행·절 제목("사전 등록 중"·"사전 등록 작성 중")은 그 시각에 이미 사전 등록이 커밋(`fde4f6a`, 23:33:15Z)되고 본 실행(23:33:49Z)이 돌던 사실과 어긋난다(`\tentative{예정}` 표지는 결과 전이라 맞음). 수치(R2_TRAIN 6,000·5,126·85.4 %·병 58.5 %·1,495,348·152,409, E-CAM3·E-MA1b·E-MA3 값)는 결과 문서와 같다. 다음 4시간 갱신 때 "사전 등록 `fde4f6a`, 학습 중" 식으로 고치길 권함.
- **N193.** (검증기 관찰, 새 종류 `nok`) 행에서 `k` 필드를 지우면 `validate_episode`가 구조 오류를 내지 않고 `KeyError: 'k'`로 멈춘다 — `validate.py:65`가 `check_row`(누락 필드 검사) 전에 `[r["k"] for r in rows]`를 만든다(N132 `grip` KeyError와 같은 계열). 실데이터 훑기에서 행 `k`는 모두 있음. 태그 뒤 TDD 묶음에 함께.
- **N194.** `e05 --data jsel_dev/P1 --split dev --episodes 3`(모의) → `E05_DONE`, claim `insufficient_data`: 성공 창 뒤집힘이 없어 `flip_rate_success`가 None → `judge_input`에서 빠짐(`e05.py:458`·`:480`–`:483`, 설계대로). 결함 아님.
- **N195.** DEV 23 판 `meta.code_sha` = `05e42ada69c2143d`(28–35회차 `df7fcd9234b49658`). `common.code_sha()`는 `harvest/**/*.py` 전체 해시라 새 파일 `harvest/train/r2_ma2.py`가 들어가 바뀐 것 — 로컬 사본에서 그 파일만 빼고 다시 계산하면 `df7fcd9234b49658`(`codesha36.py`). 기존 파일 무변경과 일치.
- **N196.** (P72 기계 검사) handoff 전체와 책 7장 전체의 백틱·링크 저장소 경로 **220개**를 ffe335c 사본에서 확인: 없는 경로 0. 처음 결과의 1건 `docs/design/Mx-*.md`(handoff `:66`)는 `x`가 번호 자리표시라 `M*-*.md`로 다시 봄 → M1–M10 존재(35회차 N183과 같은 자체 설계 보정).
- **N197.** `e05 --truth outcome:plan`(POOL 2008·2062·2116) → `E05_DONE`, claim `a_as_stabilizer`, `judge_input` 필요 키 모두 있음, `retest_flip` n 425·0.0, 사전 등록 해시 OK, `meta.git` ffe335c dirty false.
- **N198.** 시험 수: 로컬 **1156 passed / 21 skipped**(222.65 s, 00:00:24–00:04:08Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c36/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 16(새 `test_r2_ma2_cli.py` 포함)·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1307 passed / 4 skipped**(169.26 s, 끝 00:07:41Z), 경고 1(기존), LeRobot 6 passed(17.47 s). 로컬 `tools/prereg_hash.py --check` → OK, `tools/intent_check.py` → total 124 flagged 0. 등록 블롭 해시(`hashes36.py`, 사전 등록 문서 원문에서 직접 읽음) **34쌍**(`prereg_cam3` 9·`prereg_ma1` 4·`prereg_ma1b` 5·`prereg_ma2` 8·`prereg_ma3` 8) 불일치 0.
- **N199.** 단계 B 소형 CPU 스모크(00:13:16Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–35회차와 같음 — 결정적), expert p50 0.040 s·전체 p50 0.118 s, 맥락 토큰 454, dec_acc 0.292 → 0.708(21–35회차와 같음).
- **N200.** DEV 23 판: 행동 1,775·17.75 s 성공 종료(두 조건 `env_success` 참), 결정 호출 53(조건마다), C5 `last_step` {none 1, OK 31, LAG 8, DEVIATE 13}, C5' none 53/53, 확정 비율 0.7852, 결정 2.988/s(시뮬 초), rtf 0.51, 지연 p50·p95 0.3 s, Astra 행 2(겹침 0), `hb_mode` K2, 파일명 `dev23-P0-standard-e0`, 판 212.4 s(00:14:22–00:17:55Z). 파드 GPU 0·1 전·후 0 MiB(2·3은 E-MA2).
- **N201.** (절차, 자체 점검) ① `check36.py` 첫 실행이 Windows 콘솔 인코딩(cp949)으로 커밋 제목의 '—'에서 멈춰 `PYTHONIOENCODING=utf-8`로 다시 돌렸다(검사 내용 무변경). ② `v36.py`(판정 스크립트 종단 시험)는 50항목으로는 정확도 경계 −0.01을 정확히 만들 수 없어, 정확도 경계는 `decide()`에 실수 값 0.79 대 0.8(−0.010000000000000009)로 따로 넣었다(재설계). ③ 가드 13 `--isaac-gpu 01`은 문자열 검사(`closed.py:391`)로 거부됨을 코드로 먼저 확인했고, 가드 29·30은 35회차의 `predict` 대신 `train` 경로로 옵트인 거부를 봤다(같은 `install`). ④ E-MA2 가드 38·39는 argparse 단계 거부(체크포인트·풀 경로는 없는 값)라 GPU·데이터를 건드리지 않는다. ⑤ 음성 대조 원본 = standard/mug_marker/P0의 **네 번째** 유효 편 ep3(278프레임; 25–35회차 원본과 다름). ⑥ LeRobot 새 입력: 유효 dr/mug_marker/P0 ep0·standard/mug_tray/P0 ep3(26–35회차 LeRobot 입력과 겹치지 않음) + 무효 standard/bottle_tray/P0 ep2(무효 DEV 4편이 모두 쓰였으므로 가장 오래전(32회차) 것 재사용). ⑦ 정리 스크립트는 `bash -s`로 흘려 명령줄에 태그가 없게 했다.
- **N202.** 텍스트 위생·기계 검사(`check36`): 사본 텍스트 552파일 CR 0; 변경 md 9개 BOM·CR·C0·C1·영폭 0, 표 행 칸 수 불일치 0(H3); 책 7장 표 칸 수 불일치 0, 링크 **115개** 끊김 0(H4); 이 범위의 책 변경 커밋 2개 ↔ 06 줄(`fde4f6a` ↔ `23:32 | 01`, `a73f6bb` ↔ `23:58 | 01·05`, 칸 4, 시각 ≤ 커밋 23:33:15Z·23:58:34Z)(H5; 전 이력 2건은 N164 그대로); 현재형 진행 상태 검색(H9) — 새 것 없음(02·06 이력 인용, README·04 규칙 문장, `01:38` "(아직)", `03:13`·`03:63` 결정 내용); R7 보고서 판정 줄(H10): 35개, PASS [6, 16, 20, 22, 31, 33], FAIL 29 — handoff §2.8 35줄 모두 같은 판정, 30–35회차는 네 건수까지 같음; 책 01 상태 칸(H11) 3표 **40칸** — `끝` 35·`` `[결과 전]` `` 1(E-MA2 — 사전 등록 커밋·결과 문서 없음 = README `:8` 규칙대로)·`` `[예정]` `` 4, 벗어난 칸 0; handoff §0 세 줄 모두 확인 시각 있음(H13).
- **N203.** (E-MA2 관문 줄 수치, handoff §0 확인 23:46 UTC) 학습 로그의 `config` `n_train` 144,562 + `n_val` 7,308 = 151,870; `ma2_apply` c0 given 0, c1 given 75,895/151,870(0.4997 → "50.0 %")·missing 0; 23:46:59Z까지 스텝 c0 587(679.8 s → 1.158 s/스텝)·c1 561(667.2 s → 1.189 s/스텝) → 평균 약 1.17(줄 값과 같음); step ≤ 500 NaN 0; 검증 dec step 0 → 500: c0 5.3651 → 0.4059, c1 5.0862 → 0.3414(줄의 5.37→0.41·5.09→0.34와 같음). 확인 시각 기준 참.
- **N204.** 내 Isaac 창(00:14:22–00:17:55Z)에 E-MA2 c2 학습(00:14:28Z 시작, GPU 2)과 c0 `ma2eval`(00:18:31Z, GPU 3)이 새로 떴다. 이들의 `PYTHONPYCACHEPREFIX`는 `/data/harvest/cache/pyc`(= `pyc_r6` 아님)라, `pyc_r6` 쪽 쌍둥이가 있는 `tmpis1az6ih`와 carbonite `carb.VhilXY`(00:14:24)는 내 Isaac 워커 것으로 판별(§6.6). 남의 프로세스는 건드리지 않음.
- **N205.** `prereg_ma2.md:18` "GPU 0·1 = Isaac 렌더·R7 34회차 Isaac 확인 GPU 1" — 등록 시각(23:32Z)에는 35회차가 돌고 있었다(34회차 Isaac은 그 전에 끝남). 사실 서술이 아니라 자원 배정 설명이라 판정 영향 없음; 등록 문서는 결과 뒤 고치지 않으므로 그대로 둠.
- **N206.** `docs/draft-log.md`·`direction-log.md`에 E-MA2 사전 등록·시작(`fde4f6a`·`daed3f5`)과 paper 갱신(`54b9205`) 줄이 없다. 책 P06의 '같은 커밋 기록 줄'은 결과 문서·R7 보고서 커밋에 대한 규칙이고 진행 상태는 handoff §0에만 적는 규칙(README `:11`)이라 위반 아님 — 결과 커밋 때 함께 적으면 됨.

---

## 5. 사전 등록 대조표 (원 등록 문서에서 다시 만든 행, 행마다 이번 회차의 새 입력으로 행동 확인)

`prereg.json` 해시(E-first §2.7·2A.6·3.7·4.8·5.6): 로컬 `prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = OK(closed·e05 둘 다). 사전 등록 md 10개(기존)·계획·정본은 b2b0b3e와 같다(H1; 새 `prereg_ma2.md`는 §7). 원문 재확인: E-first `§1.5` 표(DEV 0~29 / CAL 500~549 / TEST 1000~1149 / TEST-P5 1300~1329 / POOL 2000~2119 / R2_TRAIN 10000~59999) = `eval/splits.py` `RANGES`; 성공 규칙 "1 s 연속·60 s·낙하 즉시 실패" = `sim/planner.py`; 부트스트랩 10,000 = `analysis/stats.py`; γ 2/3 = `runtime/m4.py`; H 3·STALE_MAX 1.5·lead_max 1.0 = `m4.py`; Astra = `astra_hb.py`(gpt-6-astra, low, 600; K0–K4). "확인" 열: **로컬** = `check36.py`·`hashes36.py`·`codesha36.py`·`v36.py`, **파드** = §6(`pod_cpu36.sh`, `pod_eval36.sh`·`data36.py`·`gtxt36.sh`·`e05o36.py`·`lr36.sh`, `pod_isaac36.sh`·`closed36.py`, `r2chk36.py`·`detshow36.py`, `ma2ls36.sh`·`ma2chk36.py`·`ma2gate36.py`, `attr36.sh`·`clean36.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E §1.5, §66) | `eval/splits.py`, `datagen/gen.py` | 가드(§6.3): TEST 1066·1128, CAL 534·529·(calib fit) cal, TEST-P5 1316, DEV 10,41·1245, POOL 2138, gen 10777(확인 없음)·9993·60004(확인 있음), determinism 550·25,2140, 다른 분할 허용 2건(17 `cal`→test_p5·18 `test`→cal) → 모두 거부 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | `calib --heldout jsel_dev/P2 --episodes 3` → `CALIB_DONE`; 가드 3(`--fit-split cal`, heldout P0 dev)·4(`--heldout-split test`, heldout P0) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | DEV 23 C5·C5' 둘 다 **성공 종료** 17.75 s·1,775스텝, 두 조건 같음 | 일치 |
| **6** | 호출 기록·Astra A6 (E §1.6, §28) | `core.py` | **DEV 23 결정 호출 106행**(조건마다 53): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 106/106; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치(N155) |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` n_boot 10000·seed 0·percentile(closed·e05); `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P1 --split dev --episodes 3` → `E05_DONE`(claim `insufficient_data`, N194); 가드 24(`canary build-set --data jsel_dev/P0 --seeds 3110-3111`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `"C5,C13"` → "condition 'C13': runtime has ['C0' … 'C6']", 가드 33 `--m4-h=-3` → "M4 H = -3 … >= 1"; **DEV 23 C5 `last_step` {none 1, OK 31, LAG 8, DEVIATE 13}, C5' none 53/53, 요청 본문 마지막 `last_step:` 줄 = 행 값 106/106** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P2 --episodes 4` → `RD_DONE`(dr 낙폭 0.0 [0.0, 0.0], n 535); 가드 5 `rd --variants dr=gen_dev/dr/P0 --split cal` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-1e-3` → "lead_max = -0.001 … finite > 0 s", 15 `=1e309`(double 넘침) → "lead_max = inf …", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(00:19Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2008,2062,2116 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`, N197) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 23, 00:14:22–00:17:55Z)**: 행동 **1,775개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 53·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | 6,000 메타 재집계(§6.2), 결정성 `cmp1–3` 각 기준 대 새·이력 2쌍 `identical` 참 + `cmp3a` 중복 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119"(폴더 없음); 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 9`·`01` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 23 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0; 가드 26 `K12`·27 `"K2,K3,K4"`(예산 없음) 거부 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 입력**(dr/mug_marker/P0 ep0·standard/mug_tray/P0 ep3 참, standard/bottle_tray/P0 ep2 **거짓**): 내보낸 편 2·516프레임(255 + 261, 무효 편 건너뜀 ✓, 과제 2), `verify` 오류 0·PSNR 최소 39.73 dB·lerobot 0.3.3 적재 516프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 구조 검사 (§66, 완료 정의 1, `r2_datagen.md:55`) | `datagen/validate.py` | **DEV 36/36 오류 없음**, 검증기 대 메타 불일치 0; **R2_TRAIN 54편**(18폴더 **끝 3시드**: 10597–10599·10797–10799·10997–10999) ffe335c 검증기 재실행 대 도장 메타: 오류 0·`valid_for_training`·`structural_ok` 불일치 0; **새 대조 13종**(standard/mug_marker/P0 ep3, 278프레임): 무수정 오류 0; 모든 프레임 줄에 여분 최상위 필드 → 오류 0; 라벨 행마다 여분 필드 → 오류 0; 가운데 프레임 k139 손목 경로 ← 머리 JPEG → 오류 0(크기 검사는 k0·K만); 행 k85 `hz` 삭제 → "missing field 'hz'"; 행 k130 `action_exec` 삭제 → "missing field 'action_exec'"; 행 k229 `action_script` 삭제 → "missing field 'action_script'"; 행 k52 `valid` (H, 1) 중첩 → "valid: H values in {0,1}, first step valid"; 행 k199 `valid` 문자열 "1"/"0" → 같은 오류; npz `q` 끝 행 삭제 → "npz q: length 277 (want 278) or non-finite"; 끝 프레임 k277 손목 경로 → 없는 파일 → "k277: missing cam_wrist_right" + "images 555 != frames 278 x cams 2"; 메타 `success` 키 삭제 → `structural_ok` 참·오류 0·`valid_for_training` 거짓. 관찰: `nok` → `KeyError: 'k'`(N193). 실데이터 훑기 불일치 0 | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 23 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | E-MA2 등록 §0 관문(NaN·90분·데이터 수·실행 경로) 줄과 로그 확인(N203); 유료 0 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | `harvest/`·`tools/`·`tests/` `M` 0(H1); 가드 28(`predict --aux-extra a3d@v6` → argparse "invalid choice … ('none', 'a3d@v1')"); `code_sha` 변화는 새 파일 하나로 설명됨(N195) | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 상태 칸 40개 0 벗어남, 링크 115개 끊김 0, 표 칸 수 0 불일치, 06 줄 2개; `01:64` E-MA2 행·`01:69` R2_TRAIN 794·`05:38` 21.3(21.34)·`[미검증]` 대 원자료(§6.2) | 일치 |
| **156** | 정본 = 마지막 절까지 | — | 정본 무변경(H1) | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3·E-MA1(b) 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond` | 옵트인 가드 29(`train --data r2` → "--cam3: --data se2e only")·30(`train --data se2e --motion-line none` → "--cam3: with the motion line (prereg_cam3 cells)")·31(`kvcond@v6`)·32(`"cam3@v1 "` 뒤 공백) 거부; 등록 블롭 해시 26/26 | 일치 |
| **158** | handoff §0 = 확인 시각에 참인 진행 상태, 결과 커밋 때 삭제(README `:11`, P69) | — | LeRobot 줄(23:27) 그대로(35회차 확인); R7 줄(23:58) 참; **E-MA2 줄(23:46) 참**(N203, 드라이버·프로세스 시작 23:33:49Z) | 일치 |
| **159** | 결과 문서 = 원자료 (책 README `:7`, P68) | — | `r2_train_gen.md` 정정 6곳 재집계(§6.2) | 일치 |
| **160** | 인용 경로 = 커밋에 있음 (P72) | — | handoff 전체·책 7장 경로 220개 없음 0(N196) | 일치 |
| **161** | 사전 등록 E-MA2 (`prereg_ma2.md`) | `r2_ma2`, `tools/ma2/*` | §7 실험 코드 절 | 실험 절 PASS |

### 5.1 35회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드), 5·6·51–58·99·137·151(DEV 23), 13–17·61–62(jsel_dev/P1·gen_dev/dr/P2), 2–4(jsel_dev/P2), 66–67(`-1e-3`·`1e309`), 98(POOL 2008·2062·2116), 101(재집계 + 결정성 구조), 138(새 입력), 139(새 대조 13종 + R2_TRAIN 끝 3시드 54편 + 25 % 위치 100시드 훑기), 154(`code_sha` 설명), 155(35회차 D-1 해소), 157(새 조합 가드 + 등록 해시), 158(E-MA2 줄), 159(35회차 D-1·D-2 해소). 새 행: 161(E-MA2).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status b2b0b3e ffe335c`(31파일): M 책 01(`:64` E-MA2 행, `:69` R2_TRAIN 794), 05(`:38`), 06(`:28`·`:29` +2), draft-log(`:486` 교체, `:488` +1), handoff(`:3` 머리, `:12` §0 R7 줄, `:13` §0 E-MA2 줄(+`fde4f6a`, `daed3f5`에서 교체), `:140` §2.8 34회차 표시, `:141` 35회차 +1), direction-log(`:82` +1), `r2_train_gen.md`(`:20`·`:31`·`:32`·`:78`·`:107`·`:157`); A `prereg_ma2.md`(75줄), `r7_cycle35.md`(194줄, `ffe335c`에서 머리 정정); A 코드·시험 8파일; M paper 14파일(`.tex` 11·그림 3). 요청된 범위와 정확히 같다.

### 6.2 바뀐 줄마다 대 원자료 (R2_TRAIN은 `r2chk36.py`·`detshow36.py`, E-MA2는 `ma2chk36.py`·`ma2gate36.py`·`ma2ls36.sh`)
| 바뀐 줄·주장 | 원자료 | 판정 |
|---|---|---|
| `r2_train_gen.md:107` "91 %(794/874)가 병의 놓기" + 정정 표시(798 = 과제 전체 놓기, 머그·쟁반 전도 4 포함; 병 384 + 237 + 173) | 6,000 메타에서 실패 874의 원래 조합을 먼저 출력: bottle_tray `release` (`on` 참·`upright` 거짓) 384, (`on` 거짓) 237, `reason off_table` 173; mug_tray `release` 전도 4 → 놓기 전체 798, 병 794, 794/874 = 0.9085 | 맞음 |
| 책 `01:69`·`draft-log:486` "실패 874 중 794 [→ 정정 …]" | 같음 | 맞음 |
| `:31` 원문 + 정정 표시(w5 12:00:24Z GPU 1, 결정성 자리 이어받음, 첫 본 편 standard/mug_tray/P0 10030 12:03:32Z, 파일럿 검사 12:20:26Z, 관문 아님) | `workers.log` "DET lane a done 12:00:15" → "WORKER w5 gpu=1 … start 12:00:24"; 비파일럿 편 5,580 중 첫 편 12:03:32 standard/mug_tray/P0 10030(GPU 1, 체인 `…_3299425_20260925T120025`); `pilot/check_at_pilot_end.log` mtime 12:20:26·`analyze_pilot.json` 12:20:27; 12:03:32 → 12:20:26 = 16 min 54 s ≈ 17분 | 맞음 |
| `:31` "파일럿 420편(11:16–12:17Z …)" | 파일럿 편 420, 첫 11:19:03·마지막 12:16:47(pD done 12:16:51) | 맞음 |
| `:32` "본 생성 12:00–21:56Z(w5 12:00, w1·w3 12:15, w2 12:16, w4 12:32 시작)" + 정정 표시 | w3·w1 12:15:24, w2 12:16:44, w4 12:32:34(DET lane b done 12:32:34), 마지막 w2 done 21:56:28 | 맞음 |
| `:157` "본 생성 12:00–21:56Z 약 9 h 56 min" + 정정 표시 | 12:00:24 → 21:56:28 = 9:56:04 | 맞음 |
| `:20` "비교 6쌍 모두 [→ 정정 … 8 → 6]" | `cmp1–3.json` `runs` 3개 = 기준(`/data/harvest/r2/train`, 자기 자신) + `det/fresh*` + `det/hist*` → 기준 대 2쌍 × 3 = 6, 모두 `identical` 참; `cmp3a` = cmp3의 새 프로세스 쌍 중복 | 맞음 |
| `:78` "9.7 s 시뮬 [→ 정정 … 9.725 s]" | 유효 5,126편 `sim_time_s` 평균 9.7247, 프레임 평균 292.718(÷30 = 9.757) | 맞음 |
| 책 `05:38` "≈ 21.3 GPU-h(21.34; …) · 사용률 20–50 % `[미검증]` — 저장된 로그에 없음 [→ 정정 … N178·N179]" | 11:16:17 → 21:56:28 = 10.6697 h × 2 = 21.339; 사용률 출처 없음(35회차 N179, 결과 문서 `:158`은 원출처라 그대로) | 맞음 |
| 책 `06:28` `23:32 \| 01` E-MA2 등록 줄, `06:29` `23:58 \| 01·05` 35회차 정정 줄 | 각 커밋의 책 변경(01 / 01·05)과 같음, 시각 ≤ 커밋(23:33:15Z / 23:58:34Z) | 맞음 |
| 책 `01:64` E-MA2 행(등록 링크 2026-09-25T23:32:45Z, 결정 스냅샷 151,870, C0/C1/C2, 되짚기 명령 50 %, 평가 eval 분할 1,200, 상태 `[결과 전]`) | `prereg_ma2.md:1`·`:7`·§2·§3; 명령 표 151,870행·given 0.4997; 등록 커밋 있음·결과 문서 없음 | 맞음 |
| handoff `:3` 23:58 UTC | ≤ 커밋 `a73f6bb` 23:58:34Z·`ffe335c` 23:58:51Z | 맞음 |
| handoff `:12` §0 R7 줄(확인 23:58 UTC) | `r7_cycle35.md` 판정 FAIL(DOC 2) | 맞음 |
| handoff `:13` §0 E-MA2 줄(확인 23:46 UTC): `fde4f6a`, 본 실행 23:33:49Z, GPU 2 c0(다음 c2 → c2 평가 → 지연)·GPU 3 c1(다음 c0·c1 평가), 드라이버, 관문 수치, 1.17 s/스텝 | `ps` lstart `run_ma2.sh A`·`B`·학습 2개 23:33:49; `run_ma2.sh` 본문(lane A: train c0 → c2 → evalm c2 → lane B 끝 뒤 latency; lane B: train c1 → evalm c0 → c1); 관문 수치 N203 | 맞음 |
| handoff `:140` 34회차 줄 "[보고서 머리 작성 2026-09-25 23:20 UTC — … N181]" | `r7_cycle34.md` 머리 "작성 2026-09-25 23:20 UTC" | 맞음 |
| handoff `:141` 35회차 줄(보고서 작성 23:5x UTC 무렵, D-1·D-2, SCOPED 20, NOTE 143, 정정 23:58) | `r7_cycle35.md:11`–`:18`·`:32`–`:39`; H10 건수 같음 | 맞음 |
| draft-log `:488`, direction-log `:82` | 35회차 보고서 | 맞음 |
| `r7_cycle35.md:3` 머리 정정 표시("00:0x"는 틀림, `a73f6bb` 23:58에 이미 들어 있음) | `a73f6bb` 커밋 시각 23:58:34Z에 보고서 추가(`git show --name-status`) | 맞음 |
| `r7_cycle35.md` 나머지(판정·표·NOTE) | 표본 대조: `r2chk36` 값(794·12:03:32·12:20:26·9.7247·21.339)과 같음; `det` 쌍 셈 N175와 같음 | 맞음 |
| `prereg_ma2.md` §0·§4의 데이터 주장(151,870·fit/eval·given 75,895·1,200·참 xy ≥ 1 cm 638·화살표 75,895 + 3,600·코드 사본 LF archive) | `ma2chk36` (2)–(5): 명령 표 151,870행·중복 0·give 재계산 불일치 0·fit 144,562/eval 7,308; 메타에서 독립 셈 151,870; 평가 집합 재구성 sha `61b2bce64ee1`·638; 화살표 파일 true 75,895·e0/e90/e180 각 1,200; `code_ma2/COMMIT` = `fde4f6a`, 파일 동일 | 맞음(N205) |
| paper 14파일(`54b9205`) | R2_TRAIN·E-CAM3·E-MA1b·E-MA3 수치 = 결과 문서; E-MA2 "사전 등록 중" 표기만 낡음 | NOTE(N192) |

### 6.3 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 00:11:15–00:11:42Z, 21–35회차와 다른 값; 사유는 `gtxt36.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data jsel_dev/P1 --split test --seeds 1066`, 2 `e05 --data jsel_dev/P2 --split cal --seeds 534`, 3 `calib --fit-split cal --heldout P0 --heldout-split dev`, 4 `calib --fit-split pool --heldout P0 --heldout-split test`, 5 `rd --variants dr=gen_dev/dr/P0 --split cal`, 6–8 `closed --split test --seeds 1128`·`cal 529`·`test_p5 1316` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 10,41` → "seeds [41] are not in split dev", 10 `pool --seeds 2138`, 11 `dev --seeds 1245` → "(refused, never opened)"; 12–13 `--isaac-gpu 9`·`01` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-1e-3`, 15 `=1e309` → "lead_max = -0.001 / inf … finite > 0 s"; 16 `--conditions "C5,C13"` → "condition 'C13': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test_p5 --seeds 1317` → "set HARVEST_ALLOW_SPLIT=test_p5", 18 `=test` + `e05 --data P1 --split cal --seeds 536` → "set HARVEST_ALLOW_SPLIT=cal"; 19 `gen --seeds 10777`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9993 --confirm-train`, 21 `--seeds 60004 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 550`, 23 `history --seeds 25,2140` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P0 --seeds 3110-3111`, 25 `e05 --data P0 --split pool --seeds 2114` → "no episode selected"; 26 `--hb-mode K12` → "from ('K0', …, 'K4')", 27 `--hb-mode "K2,K3,K4"`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d@v6` → argparse "invalid choice" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 train --data r2 --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 train --data se2e --cam3 cam3@v1 --motion-line none` → "--cam3: with the motion line (prereg_cam3 cells)"(둘 다 rc 1, 적재 전), 31 `se2e_kvcond train --expert-cond kvcond@v6`, 32 `se2e_cam3 train --cam3 "cam3@v1 "` → argparse "invalid choice" rc 2. **추가**: 33 `closed --m4-h=-3` → "M4 H = -3: decision steps per call must be >= 1"; 34 `gen --variant random --seeds 10999 --confirm-train` → "variant 'random' is the TEST pool … (canon §34 D35)", 35 `gen --kinds P4 --seeds 6` → "DEV perturbations P0-P2 only". **E-MA2 옵트인(실험 절)**: 36 `r2_ma2 train --data se2e --ma2 c1` → "--ma2: --data r2 only"(rc 1, 적재 전), 37 `--ma2 c3` → "invalid choice … ('off', 'c0', 'c1', 'c2')", 38 `ma2eval` `--eval-set` 없음 → "the following arguments are required: --eval-set", 39 `ma2eval --ma2 off` → "invalid choice … ('c0', 'c1', 'c2')"(37–39 rc 2). **39건 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.4 A. 테스트
- 로컬(`…\r7c36\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c36/pt tests`): EXIT 0, **1156 passed · 21 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1307 passed, 4 skipped**, EXIT 0(E-MA2 torch 시험 포함). 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.5 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 13종 + 실데이터 훑기(DEV 36·R2_TRAIN 300편 불일치 0); R2_TRAIN 6,000 메타 재집계 + 끝 3시드 54편 재검증; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀); `se2e_c1` **5/5 OK**. |
| 2 모델 | 충족(CPU) | CPU 스모크(N199), CPU 묶음의 단계 B·실험 시험 통과, 기준선 코드 무변경(새 파일만). GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 23 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c36`: `CLOSED_DONE`, 호출 53·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 00:11:42–00:12:16Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`(N197). |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함).
- 파드 정리 대상 판별(`attr36.sh`, 00:18:57Z): 내 Isaac 창(00:14:22–00:17:55Z)에 생긴 `tmp/carb.VhilXY`(00:14:24)·`tmp/tmpis1az6ih`(00:14:42)·`pyc_r6/…/tmpis1az6ih`·`pyc_r6/…/r7c36`(772 KB)·`kitcache/cyclo-r7c36_standard`(208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-MA2 c2 학습(00:14:28Z)과 c0 `ma2eval`(00:18:31Z)뿐이고 캐시 접두는 `pyc`(= `pyc_r6` 아님) → 모두 내 것(N204).
- 파드 정리(`clean36.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 00:19:39Z): `tmp/r7c36`(501 MB), 위 Isaac 항목 5개. 끝에 r7c36 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c36이 든 프로세스 0, `IR_INST=r7c36` 프로세스 0, 열린 핸들 0, GPU 0·1 0 MiB. 남의 `export_all.sh`·`r2_ma2` 2개 그대로.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a36.tar`·판정 시험 폴더 `v/` 삭제, 스크립트·작은 출력만 남김; 지시대로 `D:\tools\scratch_qdd\r7c34` 삭제 — r7c 폴더는 r7c35·r7c36만. C: 쓰기 없음.

## 7. 실험 코드 절 (E-MA2, `fde4f6a`)

`prereg_ma2.md` 원문 대 코드·동작:

| 등록 항목 (절) | 구현 | 확인 | 판정 |
|---|---|---|---|
| 되짚기 명령 = 손끝 `tcp[k+30] − tcp[k]`(끝 넘으면 마지막 프레임), 축마다 ±5 cm (§2) | `r2_ma2.hindsight_cmd` | 시험 + R2_TRAIN 무작위 40편 1,197스냅샷에서 npz `tcp`로 다시 계산: 명령 표와 최대 차 5.0e-7(6자리 반올림), 저장 `tcp` = npz 최대 차 5.0e-7; `tcp` z 0.084–0.245 m(탁자 위 높이 좌표) | 일치 |
| 주는 표본 50 %: sha256("ma2give@v1\|<변형>/<과제>/<섭동>/ep<시드>/k<k>") 앞 8자리 < 0.5 (§2) | `give`, `sample_id` | 151,870행 모두 독립 구현으로 재계산 불일치 0, given 75,895(0.4997); C1·C2 같은 표본(학습 로그 `idx` 순서 c0·c1 같음) | 일치 |
| C1 문장: 문맥 끝과 모든 질문 같은 자리, cm 소수 1자리 (§2) | `cmd_line`, `with_command` | 시험(문맥·질문 접두 유지, 입력 불변) | 일치 |
| C2 화살표: 원 r 3·선 3 px·화살촉 10 px(≥ 4 px), 청록, 투영 상수, q90 (§2) | `draw_arrow`, `project_head`, `build_ma2 arrows` | 무작위 given 6개를 ffe335c 사본으로 원 JPEG에서 다시 그려 q90 저장 → 저장된 학습 이미지와 **바이트 동일 6/6**; 확인 그림(`arrow_sheet36.jpg`)에서 시작점이 손끝, −z 명령은 아래로 | 일치 |
| 재라벨: 준 표본의 `dir_xy`·`dir_z` 정답·확정 = 명령 칸(1 cm 사각대), 나머지 labels_v2 (§2) | `cmd_bins`(= `labels_v2.dir_xy_label`·`dir_z_label`, `DEADBAND_M` 0.01) | 시험 | 일치 |
| `prompt_config` 표지·sha 변경, C0는 given 0 (§2, §5 (c)) | `mark_prompt_config`, `install` | c0 로그 `ma2_apply` given 0; 시험 | 일치 |
| 스케줄 2,000스텝·묶음 8·lr 1e-4/1e-4·워밍업 3 %+코사인·시드 0·검증 원천별 50·500마다·KI stop·λ 1/1/0.1/0.1·Qwen3-VL-4B `ebb281ec` (§3) | `run_ma2.sh` → `stageb_train` | 학습 로그 `config`: max_steps 2000·batch 8·lr·lr_heads 1e-4·seed 0·val_per_kind 50·val_seed 0·eval_every 500·ki stop·λ 1/1/0.1/0.1·`model_rev` `ebb281ec…`; step 1 `lr_heads` 3.33e-6 = 1e-4/30(워밍업 60 = 3 %) | 일치 |
| 두 줄 배치 GPU 2(c0 → c2 → c2 평가 → 지연)·GPU 3(c1 → c0 평가 → c1 평가), PASSIVE·8스레드·nice (§3) | `run_ma2.sh` | 드라이버 본문 같음 | 일치 |
| 평가 집합: eval 분할 7,308에서 (변형, 과제) 6층 × 200, 정렬 뒤 시드 0 표본, sha `61b2bce64ee1` (§3) | `select_eval`, `cmd_evalset` | 명령 표에서 독립 재구성(층 크기 860·1,374·1,433·836·1,374·1,431) → 1,200·sha **`61b2bce64ee1`**·모두 eval 분할·참 xy ≥ 1 cm **638**(`eval_set.json`은 열지 않음) | 일치 |
| 평가 조건 none + e0/e90/e180(반시계, xy ≤ 2 cm, z ±2 cm), 결정 = 보기 로그확률 최댓값(공유 접두), 청크 = 예측 결정 조건 expert(Euler 10, 잡음 스냅샷마다 고정·조건 사이 같음), FK(마지막) − FK(첫) (§3) | `eval_cmd`, `cmd_ma2eval`, `stageb_expert.sample_actions`(Euler), `se2e_data.fk_ee` | 코드 읽기 + 시험(회전·상한); FK 관문 재확인: `action[:, :7]` FK 0.5 s 변위 대 `tcp` 변위(xy ≥ 1 cm, 12편 155개) 코사인 중앙 0.9985·20분위 0.9953, 크기 비 0.979(E-N4) | 일치 |
| 준수율·명령 없는 정확도·판정 1–4·CMP_EPS 1e-12·부트스트랩 10,000 시드 0 (§6) | `ma2_verdict.py` | 시험 + **새 경계값 종단 시험**(`v36.py`, main() 전체 경로): A 준수율 0.6/0.7(차 0.09999999999999998)·p95 비 − 1 = 0.09999999999999987 → **C2**; B 화살표 쪽 두 쌍 변위 0 → 준수율 0.6/0.6 → **C1**; E 0.55/0.55 → **NONE**(규칙 1); `decide()` 정확도 차 −0.010000000000000009 → C2 조건 참, −0.0101 → C2 거짓 → C1 | 일치 |
| 입력 검사: id × 조건 정확히 한 번, 요약 조건, 기록된 돌린 명령 = 재계산 (§6) | `load`, `per_snapshot` | C 기록 명령 2e-5 m 변조 → SystemExit; D c0 파일에 여분 `e90` → SystemExit | 일치(E-N1) |
| 지연: `forward_shared`, FULL = 읽기(+C2 메모리 그리기)·전처리·토큰화·GPU, 묶음 1, 시드 0 표본 50(e0), 세 형식 교차, 예열 30, 4회, 가중치 c0 (§6) | `ma2_latency.py` | 코드 읽기: `Image.open` 가로채기가 `prefix_share.encode_group`·`HFEncoder.inputs`의 모듈 속성 호출에 걸림(`enc.root` "" → 표지 경로 그대로) | 일치 |
| 도중 관문 (1)–(4) (§0) | 로그 | NaN 0·step 500 dec < step 0(c0 5.37 → 0.41, c1 5.09 → 0.34), 1.16–1.19 s/스텝(90분 한도 안), `n_train + n_val` 151,870, given/n 0.4997·missing 0 | 일치(E-N2) |
| 새 파일뿐, 기준 파일 무수정 (§5 (a)) | — | `git diff --name-status b2b0b3e ffe335c`: `harvest/`·`tools/`·`tests/` 항목 A 8·M 0; `code_sha` 변화 = 새 파일 하나(N195) | 일치 |
| 등록이 본 실행보다 먼저 (§0, P15) | — | 등록 커밋 23:33:15Z < `run_ma2.sh`·학습 프로세스 23:33:49Z < 첫 스텝 23:35:42Z; 코드 사본 `COMMIT` `fde4f6a`, `harvest/`·`tools/`·`tests/` 328파일 = ffe335c 사본, 등록 해시 8/8 | 일치 |
| 옵트인 가드 | `install`, argparse | 가드 36–39(§6.3) | 일치 |

- **E-N1.** `ma2_verdict.per_snapshot`는 기록된 돌린 명령을 **채점 대상 쌍**(참 |xy| ≥ 1 cm, 돌린 칸 ≠ `none_xy`, e0 포함)에서만 재계산과 비교한다. 채점 밖 쌍의 기록 명령과 요약 `n`, `eval_set` sha는 확인하지 않는다 — 판정에 들어가는 값은 모두 검사되므로 결과 영향 없음.
- **E-N2.** `apply_ma2`의 `missing`은 항상 0이다(명령 표에 없는 표본은 `KeyError`로 멈춤 — 등록 관문 "missing > 0이면 멈춤"보다 엄격). 학습 중 검증 표본에도 명령이 주어져(50 %) c1·c2 로그의 검증 `dec`는 재라벨된 정답 섞임 기준이다(관문 (1) 판단에는 영향 없음; 판정 지표는 `ma2eval`).
- **E-N3.** 결과 전이라 `ma2eval`·지연·판정 출력은 열지 않았다; 파드에서 c0 `ma2eval`이 00:18:31Z에 시작한 것만 프로세스 목록으로 봤다.
- **E-N4.** FK 관문 재확인은 등록과 다른 표본·방법(`action` 목표 관절, 0.5 s)이라 값이 조금 다르다(코사인 중앙 0.9985 대 등록 0.9999, 크기 비 0.979 대 1.017); 준수율의 방향 측정(코사인 > 0.5)에는 충분하다.

## 8. 다음 순회 전에 할 일 (제안)
1. **36회차 기준선 PASS — 연속 무결 1.** 37회차가 기준선 PASS면 연속 2 = E2E 준비 기준점(태그).
2. (선택, NOTE) N192(paper E-MA2 "사전 등록 중" → 다음 4시간 갱신), N193(검증기 행 `k` 누락 KeyError — N131·N132·N142·N143·N154·N165·N190과 함께 태그 뒤 TDD), N155(결합 구현 때), E-N1·E-N2(E-MA2 결과 문서에 한계로 적기).
3. 37회차 대상은 ffe335c 이후 HEAD, **연속 무결 1에서**. E-MA2 결과가 커밋되면 그 실험 절(판정 재계산)을 함께 본다.
