# R7 객관 검증 순회 — 35회차 (cycle 35, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle34.md`의 표·결론을 근거로 쓰지 않고 b2b0b3e의 바뀐 줄마다 diff·원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). R2_TRAIN 수치는 R2_TRAIN 에이전트의 `analyze.py`·`verify_merge.py`·`loadcount.py`를 쓰지 않고 원 파일(`ep*.meta.json`·행/라벨 파일·합본·로그)에서 새 스크립트로 다시 셌다. 가드·음성 대조·Isaac 시드·모의 평가 입력은 **21–34회차와 다른 새 값**. 작성 2026-09-26 00:0x UTC [→ 정정 2026-09-25 23:58 UTC, 메인: 이 머리 시각은 틀림 — 이 보고서는 2026-09-25 23:58 UTC 커밋 a73f6bb에 이미 들어 있으므로 작성은 그 전(2026-09-25 23:5x UTC 무렵)](archive 23:33:31Z, 로컬 사본 풀기 23:33:58Z, 파드 첫 명령 23:34:16Z, 파드 정리 끝 23:53:21Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`b2b0b3e`**(`b2b0b3ebda09529bc423080707634859d0a8a89d`, 커밋 시각 2026-09-26 08:30:31 +0900 = **2026-09-25 23:30:31 UTC**, "R2_TRAIN results (6,000 generated, 5,126 valid, 1,495,348 stage-B rows, merge verified; LeRobot export pending) + R7 cycle 34 FAIL fix …"). `972b0be..b2b0b3e` = 커밋 1개, 10파일, **모두 `.md` 문서**(책 01·02·04·05·06, handoff, draft-log, direction-log, 새 `r2_train_gen.md`, 새 `r7_cycle34.md`); **코드·시험·사전 등록·정본·계획 변경 0**(`check35` H1, `git diff --stat 972b0be b2b0b3e -- harvest tools tests docs/design docs/stage3/prereg* docs/superpowers` 빈 결과). 뒤 커밋(`fde4f6a`, 23:33:15Z, 책 01·06)은 범위 밖. 작업 트리의 미커밋 E-MA2 파일(`prereg_ma2.md`, `r2_ma2.py`, `tools/ma2/`, 시험 4개)은 범위 밖 — 읽지 않음.
- **범위 나눔(34회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책. **실험 코드 절**(따로 판정) = b2b0b3e 이하에 커밋됐으나 아직 검토되지 않은 실험 코드.
- 사본: `git -c core.autocrlf=false archive b2b0b3e`(tar 주석 = `b2b0b3eb…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c35\repo`에 풀었다(**599파일** = 34회차 597 + `r2_train_gen.md`·`r7_cycle34.md`, 텍스트 515파일 CR 0). 파드 사본 = 같은 tar(텍스트 멤버 CR 0 확인 뒤)를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c35/code`(600파일 = + `CODE_VERSION`), 코드 사본 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `b2b0b3eb…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle34.md`, 정본 `00-interfaces.md` §1–마지막 절(보충 포함, 뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(`prereg.json` 해시, `prereg_*.md` 10개, E-first `§1.5`·`§1.6` 원문), 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P72.
- 분류(34회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. handoff §0·결과 문서의 `[결과 전]` 항목은 **그 줄의 확인 시각에 참이면** 뒤에 일이 진행돼도 낡은 것으로 보지 않는다. SCOPED·NOTE는 34회차 정의 그대로.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c35`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·sed 생성 없음; `r2ls35.sh` 초안에 들어간 `python -c 'pass'` 한 조각은 실행 전에 Edit로 지웠다 — N189). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c35`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`. GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c35_standard`, `--inst-prefix r7c35`); GPU 0·2·3에는 아무것도 올리지 않음. 남의 프로세스(R2 LeRobot `export_all.sh`·그 내보내기 6개, E-MA2 `r2_ma2 train` 2개가 GPU 2·3 사용 중, 23:33:49Z 시작)는 건드리지 않음; R2_TRAIN 파일·로그는 읽기만. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만(R2_TRAIN 시드는 기존 파일 읽기만). 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **FAIL** (DOC 2 → 연속 무결 **0** 유지)

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 20 |
| NOTE | 143 |

## 판정 (실험 코드 절, 카운트와 별개): **해당 없음 — b2b0b3e 이하에 검토되지 않은 실험 코드 없음**

`972b0be..b2b0b3e`에 코드 경로 0(H1). 그 앞의 마지막 실험 코드(E-CAM3·E-MA3, `5c46056`·`40895f8`)는 28–34회차가 검토했다. 확인만 다시 함: 사전 등록 문서에 적힌 (경로, LF 블롭 sha256 앞 16) 쌍 **26개**(`prereg_cam3` 9·`prereg_ma3` 8·`prereg_ma1` 4·`prereg_ma1b` 5)를 등록 원문에서 직접 읽어 b2b0b3e 사본과 비교 → 불일치 0(`hashes35.py`). 작업 트리의 미커밋 E-MA2 파일은 범위 밖.

**기준선 코드는 972b0be(=d0e25f4)와 바이트가 같고 모든 동작 검사가 통과했다**: 로컬 **1133 passed / 20 skipped**(221.7 s), 파드 CPU **1280 passed / 4 skipped**(171.2 s), LeRobot 6 passed; 가드 **35건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–34회차와 다른 경계값, 새 가드 2건 포함); R2 DEV `validate_episode` **36/36** + **새 종류 대조 13종**(통과해야 할 경계 4종 통과, 검출해야 할 7종 모두 검출, 성공 거짓 특수 1종 맞음, 관찰 1종); R2_TRAIN 54편 재검증(b2b0b3e 검증기 대 도장된 메타 불일치 0); 실데이터 훑기(DEV 36편 + R2_TRAIN 새 3폴더 **가운데** 100시드씩 300편 90,837프레임: 불일치 0); 모의 평가 한 명령씩 완료; 새 시드 **DEV 27**에서 같은 Isaac 워커 C5 → C5' 행동 **1,526개 비트 동일**. **R2_TRAIN 결과 문서·책의 수치는 두 곳을 빼고 모두 원자료와 같다**(§6.2, 18폴더 전부·파일럿·실패 분해·로그·로더 재집계). **실패 사유는 문서 두 건**: 병 놓기 실패 수 798(원자료 794, D-1)과 본 생성 시작 시각·순서(D-2).

---

## 1. DEFECT

없음. (`git diff --name-status 972b0be b2b0b3e`에 `harvest/`·`tools/`·`tests/`·`prereg*`·정본 경로 0 — `check35` H1.)

## 2. DOC

- **D-1. "실패 874 중 798이 병 놓기" — 원자료는 794.** `docs/stage3/results/r2_train_gen.md:107` "**실패의 91 %(798/874)가 병의 놓기 단계**다", `docs/book/01-experiments.md:69` "실패 874 중 798이 병 놓기: 전도 384·놓을 곳 밖 237·탁상 밖 173", `docs/draft-log.md:486` "실패 874 중 798이 병 놓기".
  - 원자료(`r2verify35.py`, 6,000개 `ep*.meta.json`의 `stage`·`info`에서 직접 분류): bottle_tray 실패 830 = 접근 IK 18 + 들기 7 + 옮기기 11 + **놓기 794**(`on` 참·`upright` 거짓 384, `on` 거짓 237, `reason off_table` 173). 798 = 과제 전체의 놓기 실패(384 + 4(mug_tray 전도) + 237 + 173)다. 같은 문서의 §4.3 표(병 칸 합 830, 놓기 세 칸 384·237·173)와 책 01 줄 자체의 세 수(합 794)와도 어긋난다. 91 %는 794/874 = 90.8 %라서 그대로 맞다.
  - **고침**: 세 곳의 798 → **794**(또는 "놓기 단계 전체 798 중 병 794"). 책을 고치면 06에 한 줄.
- **D-2. 본 생성 시작 시각과 순서가 원자료와 다르다.** `r2_train_gen.md:31` "파일럿 420편(11:16–12:17Z …) → 검사·분석(§3) → 이상 없음 → 본 생성은 파일럿 작업자가 끝나는 대로 자리를 이어받아 자동 시작", `:32` "본 생성 **12:15**–21:56Z: GPU 1에 3프로세스(w1·w2·w5) …", `:157` "(본 생성 약 **9 h 40 min**)".
  - 원자료: `logs/workers.log` "DET lane a done 12:00:15" → "WORKER **w5** gpu=1 … start **12:00:24**"(결정성 lane a 자리를 이어받음; 파일럿 작업자 pA·pC는 12:15:07–10에 끝남); w5의 gen 프로세스(`_workers/standard_…_3299425_20260925T120025.jsonl`)가 **12:03:32Z에 첫 본 생성 편**(standard/mug_tray/P0 10030)을 기록했다(`r2more35b.py`, 메타 `worker.chain`·`utc`). 파일럿 검사·분석은 `pilot/check_at_pilot_end.log`·`analyze_pilot.json` 12:20:26–27Z — 본 생성이 이미 17분 돌던 뒤다. 따라서 본 생성은 12:00–21:56Z(약 9 h 56 min)이고, 파일럿 검사가 관문이 아니었다. (w1·w3는 12:15:24, w2 12:16:44, w4 12:32:34 시작 — 동시 5는 계속 지켜졌다.)
  - **고침**: `:32` "본 생성 12:00–21:56Z(w5 12:00:24 = 결정성 lane a 자리, w1·w3 12:15, w2 12:16, w4 12:32 = lane b 자리)", `:157` "본 생성 약 9 h 56 min", `:31`은 "본 생성은 자리가 비는 대로 자동 시작했고, 파일럿 검사·분석(12:20Z)은 그 뒤에 돌아 이상이 없었다"처럼 실제 순서로. 책·handoff에는 이 수치가 없어 다른 파일은 고칠 것 없음.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN(§66, §77 N8 (4)) — 원본 생성·병합·로더 확인 끝, 결과 문서 커밋됨(§6.2). LeRobot 내보내기는 `[결과 전]`(23:53:01Z에 데이터셋마다 579–690 parquet, `dr_bottle_tray` 579 = 기대 수 도달). 확인 인자 없는 `--seeds 10004` 거부(가드 19).
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`) — 가드 §6.3.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8. S6. Astra 카나리 "none"(§67 보충). S7. S-E2E 체크포인트 런타임 형식 차(§77 보충 (2), §80). S8. CONTRADICT-soft(§68 K6). S9. §73 D5 M4 설계 확장. S10. §73 N5 E1 범위. S11. §74 보충 E-M4-lat 비례 STALE_MAX. S12. §75 보충 (2) E-M4 판정 7. S13. §77 N8 (13) 완료 정의 밖 사전 등록 실험. S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석(그대로). S15. §79 보충 `flip_th` 질문별 사전화. S16. §78 "남은 것"(dr·random 변형, CUDA PhysX, P2 결정성 행렬). S17. §78 (2) 옛 물리 녹화 재녹화·재라벨(책 01 `:70` `[예정]`).
- S18. 정본 §82·§84·§86(+보충) 결합 설계 구현("R7 관문 뒤") — `closed --hb-mode K11`·`"K0,K4"`(예산 없음) 워커 전 거부(가드 26·27), DEV 27 Astra 요청 이미지 1장·effort low·600, 흐름 호출 없음.
- S19. 정본 §83 런타임 적용("R7 관문 뒤") — DEV 27 결정 호출 요청 92/92 `motion:` 없음.
- S20. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3, N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45, N46, N49–N53, N57, N58, N71, N73, N74, N79, N90, N91, N129, N131–N138, N142–N148, N151–N155, N162, N164–N172. (그대로.) N10 재현: 가드 25(`e05 --data jsel_dev/P2 --split pool --seeds 2106`)가 빈 `g25/`를 남김. N155: DEV 27에서는 `astra_by_kind {hb 1, sub 1}` = Astra 행 2로 어긋남이 나타나지 않았다(에피소드가 15.26 s에 끝나 끝에 날아가는 호출이 없었음) — NOTE는 그대로. 검증기 N131·N132·N142·N143·N154·N165: 태그 뒤 TDD(그대로; 새 관찰 `skillbogus`도 같은 계열, N190).
- N4, N47, N48, N54–N56, N66–N70, N72, N84–N88, N92, N93, N102–N108, N116–N122, N128, N130, N139, N140, N149. (해소·표시, 그대로.) N109–N115, N123–N127, N156–N160(이전 회차 자체 기록).
- **해소(이번 회차, 수에서 뺌)**: **N94**(단계 B가 파일럿 병합분만 읽을 위험) — 18폴더 최종 병합 = 유효 편 행 합(§6.2) 확인; **N141**(책 04 괄호) — `04:63`이 최종 병합 사실로 정리됨; **N161**(옛 §0 R2_TRAIN 줄 표기) — 줄이 결과 문서로 대체됨; **N163**(R2 에이전트 확인 작업이 draft-log에 없음) — `draft-log:486`에 병합 검증·로더 표본·재적재가 들어감. 계산: 34회차 128 − 해소 4 + 새 19(N173–N191) = **143**.
- **N173.** `r2_train_gen.md` §4.3 표의 단계 이름은 설명어다: 메타 `stage` 값은 `approach_ik`·`grasp`·`lift`·`carry`·`release`(표의 "쥐기(close)"는 메타 `grasp`, `phase` 값이 `close`). 수는 모두 같음.
- **N174.** `r2_train_gen.md:78` "유효 편 한 편 평균 293프레임(**9.8 s** 시뮬)" — 293/30 = 9.77 s에서 반올림; 메타 `sim_time_s`(= (프레임 − 1)/30) 평균은 **9.725 s**. 규약 차이(끝 프레임 포함 여부) → "9.7 s" 권함.
- **N175.** `r2_train_gen.md:20` "비교 **8쌍**" — `det/cmp1–3.json`은 항목마다 기준(원본) 대 새 프로세스·이력 프로세스 2쌍(= 6쌍), `cmp3a.json`은 cmp3의 새 프로세스 쌍을 한 번 더 비교(7번째, 중복). 8쌍이 되는 셈법이 원자료에 없다. 모든 비교가 `identical` 참이고 "3/3 항목 비트 동일"은 맞다 → "6쌍(항목 3 × 새·이력)" 권함.
- **N176.** `r2_train_gen.md` §8 CPU 서술(`cpumon.log` 743줄): 5프로세스 분 607개의 코어 p10/p50/p90 = 18.5/20.4/28.1, 스로틀 0 %인 분 65.6 %; 정상 구간은 18–22코어·0 %가 맞고, 스로틀은 1–5분짜리 봉우리로 나타나 곧 풀린다(서술과 같음). 적힌 창(17:02–17:07, 18:09–18:13, 20:03–20:06)은 맞으나, 3자리가 동시에 넘어간 19:41–19:43·21:35–21:37(100 % 분 각 1개)과 12:16–12:21(본 생성 합류, 100 % 2분)은 목록에 없다.
- **N177.** `r2_train_gen.md:145` "약 9편/분/데이터셋" — 23:27Z 381–453편 / 50.2분 = 7.6–9.0편/분(상한). 23:27:00Z 379–450 · 23:27:59Z 386–459 parquet(`r2logs35.py`)이라 "381–453편"은 그 분 안의 값으로 맞다(확인 시각 기준 참).
- **N178.** 책 `05:38` "≈ **21.4** GPU-h" = 10.7 h × 2(반올림 뒤 곱); 11:16:17–21:56:28Z = 10.67 h × 2 = 21.34 h. "≈"로 덮이나 21.3이 정확.
- **N179.** 사후 확인 불가 값: `r2_train_gen.md:158`·책 `05:38`의 "프로세스당 메모리 약 4 GB, 사용률 20–50 %", `:29`의 "libgomp 스레드 약 63개·각 22 %·프로세스당 약 11코어"(첫 파일럿) — 저장된 로그(`cpumon.log`은 CPU만, 첫 파일럿 로그)에 없다. README 규칙상 책 05의 사용률은 `[미검증]` 표기가 맞다(결과 문서가 출처라 DOC로 올리지 않음).
- **N180.** `r2_train_gen.md:187` "평균 |픽셀 차| ≤ 1.2/255" — 출처 `physx_hard_reset.md` §3은 머리 1.19·손목 **1.24**/255(반올림으로 덮임).
- **N181.** handoff `:139` 34회차 줄에 보고 시각이 없다(N162와 같은 모양). 판정·수치(DEFECT 0·DOC 1·SCOPED 20·NOTE 128)는 보고서와 같다(H10).
- **N182.** 범위 밖 뒤 커밋 `fde4f6a`(23:33:15Z, 책 01·06; 06 줄 `2026-09-25 23:32 | 01` 있음)는 검토하지 않았다 — 36회차 대상.
- **N183.** (P72 기계 검사, 범위를 넓힘) handoff **전체**와 책 7장 **전체**의 백틱·링크 저장소 경로 **217개**를 b2b0b3e 사본에서 확인(중괄호 전개, `:줄` 꼬리 제거, `<자리표시>`·`*`는 glob): 없는 경로 0. 처음 결과의 1건 `docs/design/Mx-*.md`(handoff `:65`, "모듈마다 한 개" 이름 틀)는 `x`가 번호 자리표시라 `M*-*.md`로 다시 봄 → M1–M10 존재(자체 점검, 설계 보정). 34회차 D-1이 가리킨 `results/r2_train_gen.md`는 이제 커밋에 있다.
- **N184.** 파드에서 E-MA2(`r2_ma2 train` 2개, GPU 2·3 각 약 125 GB, `TMPDIR=/data/harvest/tmp`, `pyc` 접두)가 23:33:49Z부터 돌았다. 내 Isaac 창의 새 항목은 `pyc_r6` 쪽 쌍둥이 경로와 시각으로 내 것임을 확인하고 지웠다(§6.6).
- **N185.** `e05 --truth outcome:plan`(POOL 2021·2055·2097) → `E05_DONE`, claim `a_as_stabilizer`(34회차 입력은 `insufficient_data`, N166), `judge_input` 필요 키 모두 있음, `retest_flip` n 430·0.0, 사전 등록 해시 OK, `meta.git` b2b0b3e dirty false.
- **N186.** 시험 수: 로컬 **1133 passed / 20 skipped**(221.65 s, 23:34:04–23:37:46Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c35/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(171.23 s, 끝 23:40:08Z), 경고 1(기존), LeRobot 6 passed(19.05 s). 로컬 `tools/prereg_hash.py --check` → OK, `tools/intent_check.py` → total 124 flagged 0.
- **N187.** 단계 B 소형 CPU 스모크(23:51:07Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–34회차와 같음 — 결정적), expert p50 0.036 s·전체 p50 0.101 s, 맥락 토큰 454, dec_acc 0.292 → 0.708.
- **N188.** DEV 27 판: 행동 1,526·15.26 s 성공 종료(`terminations` success 1), 결정 호출 46(조건마다), C5 `last_step` {none 1, OK 34, LAG 4, DEVIATE 7}, C5' none 46/46, 확정 비율 0.8809, 결정 3.016/s, rtf 0.5496, 지연 p50·p95 0.3 s, Astra 행 2(hb 5.0 → 8.0, sub 8.26 → 11.26, 겹침 0), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28–34회차와 같음), 파일명 `dev27-P0-standard-e0`, 판 206.4 s(23:49:06–23:52:34Z). 파드 GPU 0·1 전·후 0 MiB(2·3은 E-MA2).
- **N189.** (절차, 자체 점검) ① `r2ls35.sh` 초안에 `python -c 'pass'` 조각이 들어가 있어 실행 전에 지웠다. ② 첫 후속 스크립트 `r2more35.py`는 메타 `worker.pid`를 `workers.log`의 작업자 셸 PID와 맞추려 해 전부 '?'가 됐다(메타 PID는 gen 파이썬 프로세스) → `r2more35b.py`에서 메타 `worker.chain`(gen 프로세스 체인 파일, 이름에 시작 시각)으로 다시 설계. ③ 스크립트 올리기(`up35.sh`, `kubectl exec -i … tar`) 한 번이 멈춰 로컬 작업을 멈추고(TaskStop) `timeout 90`으로 다시 올렸다(파드에 남은 프로세스 없음 확인). ④ 가드 13 `--isaac-gpu " 1"`(앞 공백)은 문자열 검사(`closed.py:391`)로 워커 전 거부됨을 코드로 먼저 확인했다. ⑤ 가드 30은 `--motion-line none`을 **명시**해 E-CAM3 옵트인이 움직임 줄 없이 거부되는지 봤고(이전 회차는 기본값), 29는 `predict --data r2`(새 조합). ⑥ 새 가드 34(`gen --variant random --seeds 10005 --confirm-train` → "variant 'random' is the TEST pool … (canon §34 D35)"), 35(`gen --variant dr --kinds P3 --seeds 4` → "DEV perturbations P0-P2 only") — 21–34회차에 없던 거부 경로. ⑦ 음성 대조 원본 = dr/mug_tray/P0의 **네 번째** 유효 편 ep3(261프레임; 25–34회차 원본과 다름). ⑧ LeRobot 새 입력: 유효 dr/mug_tray/P0 ep4·standard/mug_tray/P0 ep1(26–34회차 LeRobot 입력과 겹치지 않음) + 무효 dr/bottle_tray/P0 ep2(DEV 무효 4편이 모두 쓰였으므로 재사용). ⑨ 정리 스크립트는 `bash -s`로 흘려 명령줄에 태그가 없게 했다.
- **N190.** (검증기 관찰, 새 종류 `skillbogus`) 행 `skill_id`를 `'r7c35_skill'`로 바꿔도 오류 0 — `check_row`는 `skill_id` 존재만 본다(N143·N154·N165 계열). 태그 뒤 TDD 묶음에 함께.
- **N191.** 텍스트 위생·기계 검사(`check35`): 사본 텍스트 515파일 CR 0; 변경 md 10개 BOM·CR·C0·C1·영폭 0, 표 행 칸 수 불일치 0(H3); 책 7장 표 칸 수 불일치 0, 링크 **113개** 끊김 0(H4); 이 커밋의 책 변경(01·02·04·05) ↔ 06 줄 2개(23:29 `01·04·05`, 23:30 `02`, 칸 4, 시각 ≤ 커밋 23:30:31Z)(H5; 전 이력 2건은 N164 그대로); 현재형 진행 상태 검색(H9) — 02·06 이력 인용, README·04 규칙 문장, `01:38` "(아직)", `03:13`·`03:63` 결정 내용뿐(새 것은 P72 문장의 '미커밋'·'아직' = 사건 서술); R7 보고서 판정 줄(H10): 34개, PASS [6, 16, 20, 22, 31, 33], FAIL 28 — handoff §2.8 34줄 모두 같은 판정, 30–34회차는 네 건수까지 같음; 책 01 상태 칸(H11) 3표 **40칸** — `끝` 35·`` `[예정]` `` 5, `` `[결과 전]` `` 0(R2_TRAIN `:69`가 `끝`으로 — 결과 문서 커밋과 같은 커밋), 벗어난 칸 0.

---

## 5. 사전 등록 대조표 (원 등록 문서에서 다시 만든 행, 행마다 이번 회차의 새 입력으로 행동 확인)

`prereg.json` 해시(E-first §2.7·2A.6·3.7·4.8·5.6): 로컬 `prereg_hash.py --check` OK, 파드 산출 `meta.prereg.check` = OK(closed·e05 둘 다). 사전 등록 md 10개·계획·정본은 972b0be와 같다(H1). 원문 재확인: E-first `§1.5` 표(DEV 0~29 / CAL 500~549 / TEST 1000~1149 / TEST-P5 1300~1329 / POOL 2000~2119 / R2_TRAIN 10000~59999) = `eval/splits.py` `RANGES`; 성공 규칙 "1 s 연속·60 s·낙하 즉시 실패" = `sim/planner.py`(`success_hold_s`·off_table·time_limit); 부트스트랩 10,000 = `analysis/stats.py`; γ 2/3 = `runtime/m4.py` `GAMMA = "2/3"`; H 3·STALE_MAX 1.5·lead_max 1.0 = `m4.py`; Astra = `astra_hb.py`(gpt-6-astra, low, 600; K0–K4). "확인" 열: **로컬** = `check35.py`·`hashes35.py`, **파드** = §6(`pod_cpu35.sh`, `pod_eval35.sh`·`data35.py`·`gtxt35.sh`·`e05o35.py`·`lr35.sh`, `pod_isaac35.sh`·`closed35.py`, `r2ls35.sh`·`r2verify35.py`·`r2logs35.py`·`r2more35.py`·`r2more35b.py`, `attr35.sh`·`clean35.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E §1.5, §66) | `eval/splits.py`, `datagen/gen.py` | 가드(§6.3): TEST 1089·1101, CAL 519·543, TEST-P5 1319, DEV 7,36·1160, POOL 2131, gen 10004(확인 없음)·9994·60003(확인 있음), determinism 512·18,1312, 다른 분할 허용 2건(17 `test_p5`→test·18 `dev`→cal) → 모두 거부 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | `calib --heldout jsel_dev/P1 --episodes 4` → `CALIB_DONE`; 가드 3(`--fit-split test_p5`, heldout P1 pool)·4(`--heldout-split test_p5`, heldout P2) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | DEV 27 C5·C5' 둘 다 **성공 종료** 15.26 s·1,526스텝, 두 조건 같음 | 일치 |
| **6** | 호출 기록·Astra A6 (E §1.6, §28) | `core.py` | **DEV 27 결정 호출 92행**(조건마다 46): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 92/92; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치(N155) |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` n_boot 10000·seed 0·percentile(closed·e05); `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P0 --split dev --episodes 4` → `E05_DONE`(claim `a_as_stabilizer`); 가드 24(`canary build-set --data jsel_dev/P2 --seeds 3160-3161`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `"C5,C12"` → "condition 'C12': runtime has ['C0' … 'C6']", 가드 33 `--m4-h=-1` → "M4 H = -1 … >= 1"; **DEV 27 C5 `last_step` {none 1, OK 34, LAG 4, DEVIATE 7}, C5' none 46/46, 요청 본문 마지막 `last_step:` 줄 = 행 값 92/92** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P1 --episodes 3` → `RD_DONE`(dr 낙폭 −0.0022 [−0.0069, 0.0], n 455); 가드 5 `rd --variants dr=gen_dev/dr/P2 --split test` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-0.25` → "lead_max = -0.25 … finite > 0 s", 15 `=infinity` → "lead_max = inf …", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(23:53Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2021,2055,2097 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`, N185) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 27, 23:49:06–23:52:34Z)**: 행동 **1,526개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 46·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | `code_r2train_e8e1864`(`CODE_VERSION` e8e1864·태그 stage3-hardreset = 로컬 `git tag --points-at e8e1864`); 18폴더 독립 재집계 18/18, 결정성 cmp 4파일 `all_identical` 참(§6.2) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119"(폴더 없음); 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 8`·`" 1"` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 27 hb 5.0 → 8.0, sub 8.26 → 11.26, 겹침 0; 가드 26 `K11`·27 `"K0,K4"`(예산 없음) 거부 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 입력**(dr/mug_tray/P0 ep4·standard/mug_tray/P0 ep1 참, dr/bottle_tray/P0 ep2 **거짓**): 내보낸 편 2·559프레임(277 + 282, 무효 편 건너뜀 ✓), `verify` 오류 0·PSNR 최소 36.28 dB·lerobot 0.3.3 적재 559프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 구조 검사 (§66, 완료 정의 1, `r2_datagen.md:55`) | `datagen/validate.py` | **DEV 36/36 오류 없음**, 검증기 대 메타 불일치 0; **R2_TRAIN 54편**(18폴더 첫 3시드) b2b0b3e 검증기 재실행 대 도장 메타: 오류 0·`valid_for_training`·`structural_ok` 불일치 0; **새 대조 13종**(dr/mug_tray/P0 ep3, 261프레임): 무수정 오류 0; npz `hold_n[K]` +5 → 오류 0(합은 `[:K]`); npz 여분 배열 → 오류 0; 행 k247 `valid` 실수형 [1.0 × 13, 0.0 × 2] → 오류 0; 행 k57 `H` 삭제 → "missing field 'H'"; 행 k106 `proprio` 삭제 → "missing field 'proprio'"; 행 k174 `valid` 삭제 → "missing field 'valid'"; npz `action[K//2, 0]` NaN → "npz action: … non-finite"; npz `hold_n[130]` +1 → "hold_n does not add up to the episode duration"; 끝 프레임 k260 손목 경로 ← 머리 JPEG → "k260 cam_wrist_right: size (672, 376) != native (424, 240)"; 행 k31 aux reg `r7c35_reg` → "unknown aux names ['r7c35_reg']"; 메타 `success` 거짓 → `structural_ok` 참·오류 0·`valid_for_training` 거짓. 관찰: `skillbogus` 오류 0(N190). 실데이터 훑기 불일치 0 | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 27 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 이 범위 새 실험 없음 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 코드 변경 0(H1); 가드 28(`predict --aux-extra a3d@v5` → argparse "invalid choice … ('none', 'a3d@v1')") | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | 상태 칸 40개 0 벗어남, 링크 113개 끊김 0, 표 칸 수 0 불일치, 06 줄 2개; 01·04·05 R2_TRAIN 수치 대 원자료(§6.2) — **`01:69` "798"** | **DOC D-1** |
| **156** | 정본 = 마지막 절까지 | — | 정본 무변경(H1) | 일치 |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond` | 옵트인 가드 29(`predict --data r2` → "--cam3: --data se2e only")·30(`predict --data se2e --motion-line none` → "--cam3: with the motion line (prereg_cam3 cells)")·31(`kvcond@v5`)·32(`" cam3@v1"` 앞 공백) 거부; 등록 블롭 해시 26/26 | 일치 |
| **158** | handoff §0 = 확인 시각에 참인 진행 상태, 결과 커밋 때 삭제(README `:11`, P69) | — | 옛 R2_TRAIN 줄 삭제·결과 문서 같은 커밋 ✓; 새 LeRobot 줄(23:27) 참(N177); R7 줄(23:30) 참 | 일치 |
| **159** | 결과 문서 = 원자료 (책 README `:7`, P68) | — | `r2_train_gen.md` 전 수치 재집계(§6.2) — **`:107` 798, `:31`–`:32`·`:157` 본 생성 시각** | **DOC D-1·D-2** |
| **160** | 인용 경로 = 커밋에 있음 (P72) | — | handoff 전체·책 7장 경로 217개 없음 0(N183) | 일치 |

### 5.1 34회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드), 5·6·51–58·99·137·151(DEV 27), 13–17·61–62(jsel_dev/P0·gen_dev/dr/P1), 2–4(jsel_dev/P1), 66–67(`-0.25`·`infinity`), 98(POOL 2021·2055·2097), 101(18폴더 재집계 + 결정성 cmp), 138(새 입력), 139(새 대조 13종 + R2_TRAIN 54편 재검증 + 가운데 100시드 훑기), 155(D-1), 157(새 조합 가드 + 등록 해시 26쌍), 158(34회차 D-1 해소). 새 행: 159(결과 문서 대 원자료), 160(P72 경로 검사).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status 972b0be b2b0b3e`: M 책 01(`:69` 1줄 교체), 02(`:115` P72 +1), 04(`:3`·`:50`·`:63` 교체), 05(`:38` 교체), 06(`:26`·`:27` +2), draft-log(`:486`·`:487` +2), handoff(`:3` 머리, `:11` §0 R2_TRAIN 줄 → LeRobot 줄, `:12` §0 R7 줄, `:139` §2.8 34회차 +1), direction-log(`:81` +1); A `r2_train_gen.md`(196줄), `r7_cycle34.md`(160줄). 요청된 범위와 정확히 같다.

### 6.2 바뀐 줄마다 대 원자료 (R2_TRAIN 수치는 `r2verify35.py`·`r2logs35.py`·`r2more35(b).py`, 에이전트 스크립트 안 씀)
| 바뀐 줄·주장 | 원자료 | 판정 |
|---|---|---|
| `r2_train_gen` §1·§4.1: 6,000편, 구조 6,000/6,000(오류·경고 0), 유효 5,126(85.4 %); mug_tray 1,982 · mug_marker 1,974 · bottle 1,170; standard 2,569 · dr 2,557; P0 3,102/3,600 · P1 988/1,200 · P2 1,036/1,200; §4.1 표 18칸 | 6,000 메타: `validation.structural_ok` 참·오류 0·경고 0 6,000/6,000; 칸별 유효(표와 18/18 같음); 백분율 재계산 같음 | 맞음 |
| §1·§4.2 프레임 1,806,160 / 유효 1,500,474 · 행 1,495,348 · 결정 152,409 · fit 4,877 / eval 249; §4.2 표 6행 | 메타 `n_frames`·`n_rows`·`n_decisions` 합 = 편별 행 파일 줄 합 = 편별 라벨 파일 줄 합; `split` = (시드 % 20 == 0) 불일치 0; 6행 18값 같음 | 맞음 |
| §4.1 "평균 293프레임(9.8 s)·결정 약 30" | 292.72프레임, `sim_time_s` 평균 9.725, 29.73 | 맞음(N174) |
| §4.3 표(단계 × 과제 21칸, 합 874) | 메타 `stage`·`info`(`on(·)`·`upright(·)`·`reason off_table`)에서 직접 분류: 21칸 모두 같음 | 맞음(N173) |
| `:107` "91 %(798/874)가 병의 놓기" | 병 놓기 794(384 + 237 + 173) | **DOC D-1** |
| `:107` 쥐기·들기 29; `:108` 섭동별 병 707/1,200 · 227/400 · 236/400; `:109` 머그 44 = P1 39(IK 12·들기 12·쥐기 7·옮기기 4·전도 4) + P0 5(쥐기 3·IK 2) + P2 0; `:110` 431 / 443 | 모두 같음 | 맞음 |
| §3.1 파일럿 표 18칸, 357/420, 과제별 138·138·81, 병 P0 39/60, 프레임 104,322·행 103,965·결정 10,613·fit 335/eval 22 | 파일럿 시드 띠(P0 10000–10029·P1 10600–10619·P2 10800–10819)로 다시 셈: 모두 같음; DEV 열 12/12·12/12·8/12 = `r2_datagen.md:11`·§4.1 | 맞음 |
| §3.2 파일럿 실패 63(병 59 = 놓기 55(전도 32·밖 15·탁상 밖 8) + 옮기기 2 + IK 2; mug_marker P1 들기 1·옮기기 1; mug_tray P1 IK 2) | 모두 같음 | 맞음 |
| §3.3 결정성 표(앞 편 수 2·8·7 / 0 / 4·5·3, 프레임 307·329·264, GPU 1·0·1, 이력 프로세스 구성) | `det/cmp1–3.json` `worker_seq`·`n_frames`·`identical` 참; `det_fresh*.log`·`det_hist*.log` START 줄 gpu·시드; 원 녹화 GPU 0·1·1(메타 `worker.gpu`) | 맞음 |
| §1 "비교 8쌍" | 비교 6쌍(+cmp3a 중복 1) | 맞음 아님 → NOTE(N175) |
| §5 병합 표 18행(편·유효·병합 행·병합 라벨·시드 범위) + "병합 행 = 유효 n_rows 합, 시드 집합 = 유효 시드, 띠 누락 0·띠 밖 0" | 18/18: 합본 줄 수·정규식 시드 집합·라벨 줄 수·띠 검사 모두 같음, 시드 범위 끝 10002·10994 = 유효 최소·최대; 합본 mtime 22:01:16–22:32:29Z | 맞음 |
| §5 `gen check` 21:57:32Z–22:32:29Z 종료 0, `CHECK {"episodes": 6000, …, "rows": 1800160, "gb": 101.661}` | `final/check.log` 같은 줄; rows 1,800,160 = 전체 `n_rows` 합; gb = `check.json` `bytes` 합 101.661 GB | 맞음 |
| §5 `verify_merge.py` 18폴더 ok | `verify_merge.json` `all_ok` 참, ok 18/18 | 맞음 |
| §7 로더: config `data r2`·max 3/16/4·batch 2·eval 2, `hz 30`·`H 15`·팔 right·`open01@v1`(`sim_width_m`), val 71,994, `max_abs_action_diff 0.0`·`eval_equal`·`norm_equal`, 577 s, 22:36:56Z 시작; 파일럿 2폴더(standard mug_tray P1 + dr bottle_tray P2) 12:37Z val 581; GPU 2 | `full18.log`·`pilot_p12.log` 같은 값(22:46:33 − 577 s = 22:36:56); `loadercheck.sh` `CUDA_VISIBLE_DEVICES=2` | 맞음 |
| §7 `loadcount` 1,495,348 = 병합 행(폴더마다), train 1,423,354 / val 71,994, 결정 질문 759,350, hz 30·H 15, 524 s | `loadcount.log` 18폴더 줄·`LOADCOUNT` 합 같음, wall 523.8 | 맞음 |
| §1·§8 벽시계 11:16:17Z → 21:56:28Z, 프로세스 48회 종료 0·Traceback 0, 누적 GPU 1 31.3 h + GPU 0 21.1 h + 결정성 0.5 h = 52.8 h, 잠금 잔여 0 | `workers.log` pA 11:16:17·w2 done 21:56:28; 로그 48쌍 START/EXIT 모두 0, Traceback 0, 31.26 + 21.05 + 0.49 = 52.80; `_queue` 0항목 | 맞음 |
| §2 작업자 배치(GPU 1 w1·w2·w5, GPU 0 w3·w4, 동시 최대 5) | `workers.log` 같음, 겹치는 시간 구간마다 5 이하 | 맞음 |
| `:31`–`:32`·`:157` 본 생성 12:15–21:56Z · 9 h 40 min · 파일럿 검사 뒤 시작 | w5 12:00:24 시작, 첫 본 생성 편 12:03:32Z, 파일럿 검사 12:20:26Z | **DOC D-2** |
| §8 편당 29.7 s = 20.8 + 8.9, 시뮬 10.0 s, 평균 약 560편/h, prefix 약 30 % | `check.json` 평균 `wall_s` 20.77·`prefix_s` 8.92·`sim_s` 10.00; 6,000/10.67 h = 562 | 맞음 |
| §8 CPU(정상 18–22코어·0 %, 창 3개) | `cpumon.log` | 맞음(N176) |
| §8 디스크 107.9 GB(standard 46.4 · dr 61.6) | `final/du.txt` 107,941,495,290 B; 46.38 · 61.56 GB | 맞음 |
| §2.1 첫 파일럿(6b013ac) 09:09–09:50Z, GPU 1 2프로세스, 120편·구조 120·성공 107, 격리 경로 | `logs_pilot_6b013ac/*.log`(START 09:09:25·09:40:27, EXIT 1 09:49:59), 격리 폴더 메타 120·구조 120·성공 107, `CODE_VERSION` 6b013ac | 맞음(N179) |
| §6 `[결과 전]`(확인 23:27 UTC): 22:36Z 시작, 23:27Z 381–453편, 기대 991·987·591/579, 방식(보기 루트·심볼릭 링크), 로그 경로 | parquet ≤ 23:27:00Z 379–450 · ≤ 23:27:59Z 386–459, 첫 parquet 22:36:51Z; `export_all.sh`·`train_views/` 6개; 기대 수 = 유효 편 수 | 맞음(확인 시각 기준, N177) |
| §10 인용: `r2_datagen` §4.1(20–24°), 정본 §66(병 약 67 % 감수), `physx_hard_reset` §3(픽셀 차)·§4(prefix 추론), 4.1 s/편 | `r2_datagen.md:77`·`:122`, 정본 `:561`–`:562`, `physx_hard_reset.md:52`·`:66` | 맞음(N180) |
| §11 파일 목록(원본·운영·폐기·코드 사본·로컬 스크립트) | 파드 경로 모두 있음, `code_r2train`(6b013ac)·`code_r2train_e8e1864` `CODE_VERSION`, 로컬 `D:\tools\scratch_qdd\r2train\pod\` 있음 | 맞음 |
| 책 `01:69` R2_TRAIN 행(상태 `끝`) | 위 값들 — "798" 제외 모두 같음; 로더 표본 train 1,423,354 / val 71,994 | **DOC D-1**(798) |
| 책 `02:115` P72 | 34회차 D-1·N163과 같은 사건·예방 규칙; P14 `:22` 있음 | 맞음 |
| 책 `04:3`·`:50`·`:63` | 경로(`r2/dev*`, `r2/dev_lerobot`, `r2/train/<variant>/<task>/<P0\|P1\|P2>`, 합본·`CODE_VERSION` e8e1864, `r2/train_lerobot/`(6개), `r2train/`, `data/r2/train_pilot_prefix_6b013ac`) 파드에 있음; 시드 띠·6,000/5,126·`gen check` 시각·행 1,495,348·`split_of` = 시드 % 20 | 맞음 |
| 책 `05:38` | 11:16–21:56 ≈ 10.7 h × 2, 52.8, GPU 2 11 min(0.2 h), 첫 파일럿 0.7 h | 맞음(N178·N179) |
| 책 `06:26`·`:27` | 이 커밋의 책 변경과 장 목록 같음, 시각 ≤ 커밋 | 맞음 |
| handoff `:3` 23:30 UTC | ≤ 커밋 23:30:31Z | 맞음 |
| handoff `:11` §0 LeRobot 줄(확인 23:27 UTC) | 위 §6 행; `export_all.sh` 실행 중(23:37:10Z `ps`), `data/chunk-000` 6개 | 맞음 |
| handoff `:12` §0 R7 줄(23:30 UTC) | `r7_cycle34.md` 판정 | 맞음 |
| handoff `:139` 34회차 줄 | `r7_cycle34.md:12`–`:19`·`:35`–`:36` | 맞음(N181) |
| draft-log `:486` | 위 값들 — "798" 제외 같음; "프로세스당 11 → 3–4코어"(정상 5프로세스 약 20코어) | **DOC D-1**(798) |
| draft-log `:487`, direction-log `:81` | 34회차 보고서 | 맞음 |
| `r7_cycle34.md` 전체 | 표본 대조: 로컬 1133/20, 파드 1280/4, 가드 33 + 재설계 2, DEV 16 1,611 비트 동일, 재집계 18/18, 정리 출력 — `D:\tools\scratch_qdd\r7c34` 원 출력과 같음 | 맞음 |

### 6.3 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 23:49:06–23:49:24Z, 21–34회차와 다른 값; 사유는 `gtxt35.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data jsel_dev/P2 --split test --seeds 1089`, 2 `e05 --data jsel_dev/P0 --split cal --seeds 519`, 3 `calib --fit-split test_p5 --heldout P1 --heldout-split pool`, 4 `calib --fit-split pool --heldout P2 --heldout-split test_p5`, 5 `rd --variants dr=gen_dev/dr/P2 --split test`, 6–8 `closed --split test --seeds 1101`·`cal 543`·`test_p5 1319` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 7,36` → "seeds [36] are not in split dev", 10 `pool --seeds 2131`, 11 `dev --seeds 1160` → "(refused, never opened)"; 12–13 `--isaac-gpu 8`·`" 1"` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-0.25`, 15 `=infinity` → "lead_max = -0.25 / inf … finite > 0 s"; 16 `--conditions "C5,C12"` → "condition 'C12': runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=test_p5` + `closed --split test --seeds 1102` → "set HARVEST_ALLOW_SPLIT=test", 18 `=dev` + `e05 --data P2 --split cal --seeds 542` → "set HARVEST_ALLOW_SPLIT=cal"; 19 `gen --seeds 10004`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9994 --confirm-train`, 21 `--seeds 60003 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 512`, 23 `history --seeds 18,1312` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P2 --seeds 3160-3161`, 25 `e05 --data P2 --split pool --seeds 2106` → "no episode selected"; 26 `--hb-mode K11` → "from ('K0', …, 'K4')", 27 `--hb-mode "K0,K4"`(예산 없음) → "K4 needs --hb-budget"; 28 `stageb_train predict --aux-extra a3d@v5` → argparse "invalid choice" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 predict --data r2 --ckpt <없음> --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 predict --data se2e --ckpt <없음> --cam3 cam3@v1 --motion-line none` → "--cam3: with the motion line (prereg_cam3 cells)"(둘 다 rc 1, 체크포인트 열기 전), 31 `se2e_kvcond train --expert-cond kvcond@v5`, 32 `se2e_cam3 train --cam3 " cam3@v1"` → argparse "invalid choice" rc 2. **추가**: 33 `closed --m4-h=-1` → "M4 H = -1: decision steps per call must be >= 1"; **새** 34 `gen --variant random --seeds 10005 --confirm-train` → "variant 'random' is the TEST pool: never used for training (canon §34 D35); use 'dr'", 35 `gen --variant dr --kinds P3 --seeds 4` → "DEV perturbations P0-P2 only". **35건 모두 rc ≠ 0**(28·31·32 rc 2, 나머지 rc 1); 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.4 A. 테스트
- 로컬(`…\r7c35\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c35/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.5 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 대조 13종 + 실데이터 훑기(DEV 36·R2_TRAIN 300편 불일치 0); R2_TRAIN 18폴더 재집계 18/18 + 54편 재검증; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(무효 편 건너뜀); `se2e_c1` **5/5 OK**. |
| 2 모델 | 충족(CPU) | CPU 스모크(N187), CPU 묶음의 단계 B·실험 시험 통과, 기준선 코드 무변경; R2_TRAIN 로더 확인 기록(§6.2; 34회차 N172: `stageb_data.py`는 e8e1864와 기준선이 같음). GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 27 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c35`: `CLOSED_DONE`, 호출 46·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 23:49:24–23:50:06Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`, `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`(N185). |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 미커밋 E-MA2 파일은 읽지 않음.
- 파드 정리 대상 판별(`attr35.sh`, 23:53:01Z): 내 Isaac 창(23:49:06–23:52:34Z)에 생긴 `tmp/carb.DXXkfs`(23:49:08)·`tmp/tmpk9p656li`(23:49:26)·`pyc_r6/…/tmpk9p656li`·`pyc_r6/…/r7c35`(772 KB)·`kitcache/cyclo-r7c35_standard`(208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-MA2 `r2_ma2` 2개(23:33:49 시작)뿐이고 이들의 캐시 접두는 `pyc`(= `pyc_r6` 아님) — `tmpk9p656li`는 `pyc_r6` 쪽 쌍둥이가 있어 내 Isaac 워커 것, `carb.*`는 Isaac(carbonite) 것 → 모두 내 것.
- 파드 정리(`clean35.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 23:53:21Z): `tmp/r7c35`(505 MB), 위 Isaac 항목 5개. 끝에 r7c35 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c35가 든 프로세스 0, `IR_INST=r7c35` 프로세스 0, 열린 핸들 0, GPU 0·1 0 MiB. 남의 `export_all.sh` 6개·`r2_ma2` 2개 그대로.
- 로컬: 추출 사본 `repo/`·pytest basetemp `pt/`·archive `a35.tar` 삭제, 스크립트·작은 출력만 남김; 지시대로 `D:\tools\scratch_qdd\r7c33` 삭제 — r7c 폴더는 r7c34·r7c35만. C: 쓰기 없음.

## 7. 실험 코드 절
검토할 새 실험 코드 없음(위 판정 절). 등록 블롭 해시 26/26 일치.

## 8. 다음 순회 전에 할 일 (제안)
1. **35회차 기준선 FAIL(DOC 2) — 연속 무결 0.** 코드는 무결; 36회차가 기준선 PASS면 연속 1.
2. D-1 고침 = `r2_train_gen.md:107`·책 `01:69`·`draft-log:486`의 798 → 794(책 변경 → 06 한 줄). D-2 고침 = `r2_train_gen.md:31`–`:32`·`:157` 본 생성 시각·순서. 정정 문장·수치는 파드 명령 출력으로 확인한 뒤(P68) 이 보고서 §2·§6.2 값과 같아야 한다.
3. (선택, NOTE) N174·N175·N178(결과 문서 수치 표기), N179(책 05 사용률 `[미검증]`), N190(검증기 `skill_id` — N142·N143·N154·N165와 함께 태그 뒤 TDD), N181(§2.8 보고 시각).
4. 36회차 대상은 b2b0b3e 이후 HEAD(`fde4f6a` 포함), **연속 무결 0에서**.
