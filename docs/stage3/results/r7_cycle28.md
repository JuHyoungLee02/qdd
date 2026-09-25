# R7 객관 검증 순회 — 28회차 (cycle 28, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle27.md`의 표·결론을 근거로 쓰지 않고 정정 주장마다 원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드는 **21–27회차와 다른 새 값**, 실험 코드는 실제 함수·CLI를 경계 입력으로 돌렸다. 작성 2026-09-25 21:05 UTC(`date -u` 21:05:28Z; 로컬 사본 풀기 20:41:16Z, 파드 첫 명령 20:42:17Z, 파드 정리 끝 21:02:35Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`47edadb`**(`47edadbd80972d0c388b5bc29ee6a875ea2312ba`, 커밋 시각 2026-09-25 20:37:43 UTC, "R7 cycle 27 FAIL … book 01-06 fixes, astra_motion results/prereg corrections, canon §86 supplement (stream timeout 20 s), pitfall P68, records"). `7a02943..47edadb` = 커밋 3개(5c46056 E-CAM3 사전 등록 20:33:20Z, 40895f8 E-MA3 사전 등록 20:34:19Z, 47edadb 27회차 정정), `git diff --stat` 33파일 +1,936/−16. 검토 내내 HEAD = 47edadb, 작업 트리 깨끗함.
- **범위 나눔(27회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`(런타임·평가·시뮬·분석·학습), `tools/`(실험 도구 제외), 시험, 정본, 27회차 목록의 사전 등록, handoff·기록·결과 문서, 기록책 `docs/book/`. 이번 diff의 코드 변경은 **새 파일 16개뿐(모두 A)** — `harvest/train/se2e_cam3.py`·`se2e_kvcond.py`(옵트인 CLI 포장), `tools/cam3/*`·`tools/ma3/*`·`tools/se2e/paired_verdict.py`, 시험 7개; 기준선 코드 변경 0(`check28` H2, `stageb_train/model/expert.py` LF 블롭 = 6483397 = 파드 `code_cam3`·`code_ma3` 사본). **실험 코드 절**(따로 판정) = 27회차 실험 절 정정(`results/astra_motion.md`, `prereg_astra_motion.md` 14절) + **E-CAM3·E-MA3**(대상 이전 커밋 5c46056·40895f8이므로 범위 안: 사전 등록 2개, 코드·시험 16파일). 두 실험의 예측·평가 파일(`logs/cam3|ma3/predfull_*`·`chunk_*`·`reuse_check.out`·`kv_s1.out`·`cam3_s1.out`, 체크포인트 `log.jsonl`)은 **열지 않았다**(이름·시각만).
- 사본: `git -c core.autocrlf=false archive 47edadb`(tar 주석 = `47edadbd8097…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c28\repo`에 풀었다(**589파일**, 텍스트 537파일 CR 0). 파드 사본 = 같은 archive를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c28/code`(590파일 = + `CODE_VERSION`), 텍스트 CR 0, 올린 스크립트 CR 0(매번 확인). 파드 산출 `meta.git.commit` = `47edadbd8097…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle27.md`, 정본 `00-interfaces.md` §1–§86 보충(뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(27회차 목록 + `prereg_cam3.md`·`prereg_ma3.md`), 결합 설계 스펙 §12·§17, 구현 계획 PROBE 표, 기록책 README 규칙(`:8`–`:10`)과 02-pitfalls P01–P68.
- 분류(27회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약(값은 맞음), 추정 표시(≈·약)가 있는 수치, 반올림 차이는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c28`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c`·`sed` 생성 없음 — 한 번 `cm28.sh` 초안에 `python3 -c` 두 줄을 썼다가 **실행 전에** Write 도구 `.py` 파일로 바꿨다, N101). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c28`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c28_standard`, `--inst-prefix r7c28`; GPU 0·1의 R2_TRAIN 워커 5개는 건드리지 않음), GPU 2·3(E-CAM3·E-MA3 학습)에는 아무것도 올리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음(비용 장부는 사용량·메타·비용 필드만).

## 판정 (기준선): **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 21 |
| NOTE | 70 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — 코드 결함 0, DOC 0**(NOTE E-N12–E-N18)

**기준선 코드는 27회차 대상과 바이트가 같다**(diff의 코드 16파일이 모두 새 옵트인 파일). 회귀: 로컬 **1133 passed / 20 skipped**(Git Bash, 234.8 s; 27회차 1118 + 새 시험 15, 건너뜀 +3은 torch 없는 로컬의 cam3·kvcond·chunk_eval 시험), 파드 CPU **1280 passed / 4 skipped**(176.3 s; 1250 + 30 — cam3·ma3 torch 시험 포함 전부 통과), LeRobot 6 passed; 가드 **28건 + 실험 옵트인 4건 = 32건** 모두 rc ≠ 0(21–27회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 음성 대조 11종**(경계 안 시각 오차 9.9e-7 s는 통과, 1.01e-6 s·k 중복·손목 영상 누락·k0 손목 크기·행 누락·hz·proprio_mask·committed·tau 길이·grip inf — 모두 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 완료; 새 시드 **DEV 22**에서 같은 Isaac 워커 C5 → C5' 행동 **1,691개 비트 동일**(첫 차이 없음, 시각열 동일). **27회차 정정 주장 대부분은 실제 diff와 맞고 원자료로도 참이다**(§6.2): 01 표시 위치·제목, 02 P04 칸 안·P68, 03 §85 보충 행, 05 토큰 588/738/892·"72(끝난 뒤 도착 6 포함)", 정본 §86 보충(20 s = 탐침 `STREAM_TIMEOUT_S`, 5절 표 11.6/14.1 s·요약 12–16 s), 스펙 §17·계획 `timeout_s`, handoff §2.8·draft-log N69·direction-log 줄, 04 생성 계획 P0 10000–10599 → P1 10600–10799 → P2 10800–10999(파드 `r2train/full_slot.sh`와 같음)·"20:10 UTC 기준 P2 생성 중"(워커 5개 20:01:59–20:02:14Z 시작, 20:42Z에도 P2).

**DOC 2건(기준선)**: **D-1** 27회차 D-1 정정이 새로 쓴 책 `04-map.md:61` "19:07Z에 **P0 행 조립 끝**·P1 생성 중이었다"가 파드 원자료와 다르다 — R2_TRAIN의 폴더 행 파일 `r2/train/<변형>/<과제>/P0.stageb.jsonl` 6개는 **12:19:47–12:20:26Z 파일럿 병합**(`gen check` → `episode.merge`)이고 각 19–41시드(10000–10041)만 담는다(편은 지금 600개씩); P0 600편 생성이 끝난(standard 17:02Z, dr 18:08Z) 뒤 병합은 한 번도 없었다(P68 재발, 원천은 `ma1.md:15` 정정의 "'행 조립 전'은 틀렸다"). **D-2** 책 `04-map.md:16` `harvest/astra_motion/` "탐침 코드 `[미커밋, 탐침 에이전트 작업 중]`"(3500f54에 커밋됨)과 `:54` `ckpt/ma1b/` "E-MA1b `[진행 중]`"(끝, 책 `01:52` "끝")이 현재 트리·책 01과 다르다(책 README `:9` "같은 커밋에 고친다"를 3500f54·2df9bdc가 어김; 27회차가 놓침). **연속 무결 0 유지.**

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① `se2e_kvcond._gather`는 문맥 행이 각 캡처 호출의 앞 `T_i` 위치라고 가정한다 — 공유 접두 경로와 문맥별 경로의 K·V가 같음을 파드 시험 `test_se2e_kvcond_qwen.py`(작은 Qwen3-VL, 통과)가 확인하므로 결함 아님. ② `cam3_verdict`·`ma3_verdict`의 `--n-snap`은 기본 1,799이지만 바꿀 수 있다 — 등록 "검증 1,799에서만"은 기본값·입력 검사로 지켜짐 → 실험 절 E-N15.)

## 2. DOC

- **D-1. `docs/book/04-map.md:61` — 27회차 D-1 정정 문장 "19:07Z에 P0 행 조립 끝"이 틀렸다(P68 재발).** 파드(읽기만, `rows28.py`·`rows28b.sh`, 20:43Z): R2_TRAIN 폴더 행 파일 18개(`/data/harvest/r2/train/{dr,standard}/{bottle_tray,mug_marker,mug_tray}/P{0,1,2}.stageb.jsonl`)의 mtime은 모두 **2026-09-25 12:19:47–12:20:26Z**, P0 파일은 각각 **19·30·30·26·40·41시드**(행 5,539·8,657·8,609·7,579·11,518·11,740 — `ma1.md:15`가 적은 행 수와 같다), 시드 범위 10000–10041뿐이다. 같은 폴더의 편(`ep*.meta.json`)은 지금 600개씩(편별 행 `rows/ep*.stageb.jsonl` 600개)이고 P0 생성은 standard 17:02Z·dr 18:08Z에 끝났다. `harvest/datagen/gen.py:365-393` `check`만 `episode.merge`로 폴더 행 파일을 쓰는데, R2_TRAIN의 `check`/병합 기록은 12:19Z 파일럿 뒤 없다(`/data/harvest/r2/train/check.json` mtime도 12:20:26Z — 파일럿 것; `r2train/logs/*.log`에 `MERGE`·`CHECK` 줄 0). 단계 B 로더는 이 폴더 파일을 읽는다(`stageb_data.py:397`, `stageb_train.py:827` 기본 `<folder>.stageb.jsonl`). 따라서 19:07Z(와 지금)의 상태는 "P0 **생성** 끝, 폴더 행 파일은 파일럿 병합(19–41시드)뿐 — 600편 **행 조립 전**, P1 생성 중"이다. 원천: `docs/stage3/results/ma1.md:15`의 2df9bdc 정정 "다만 '과제 폴더만 있고 행 조립 전'은 틀렸다 … `P0.stageb.jsonl`(dr 5,539…행)이 이미 있었고"(파일 존재·행 수는 맞지만 "행 조립 전이 틀렸다"는 판단은 틀림 — '과제 폴더만'이 틀린 부분)와 27회차 보고서 D-1의 요약("P0 행은 이미 조립 …"). 책 `02-pitfalls.md:103` P63 증상 칸("R2_TRAIN을 '과제 폴더만 있고 행 조립 전'이라고 잘못 적음")도 같은 오해를 담는다. **고칠 것**(한 커밋, 06 줄 포함): `04:61` 괄호 정정을 "19:07Z에 P0 생성 끝(폴더 행 파일은 12:19Z 파일럿 병합 19–41시드뿐, 600편 행 조립 전)·P1 생성 중" 식으로, `ma1.md:15`에 "[→ 정정 …: 폴더 행 파일은 12:19Z 파일럿 병합이라 '행 조립 전'은 맞았다; 틀린 것은 '과제 폴더만']", P63 증상 칸을 "'과제 폴더만 있고'라고 잘못 적음(행 파일은 파일럿 병합뿐)"으로. 근거 명령(`find … -name '*.stageb.jsonl' -not -path '*/rows/*' -printf '%T@ %p'`, 시드 수)을 함께 적는다(P63 규칙). 운영 위험은 N94.
- **D-2. `docs/book/04-map.md:16`·`:54` — 지도의 상태 꼬리표가 현재 트리·책 01과 다르다.** `:16` "`harvest/astra_motion/` | 탐침 코드 `[미커밋, 탐침 에이전트 작업 중]`" — 탐침 코드 15파일은 3500f54(2026-09-25 19:09 UTC)에 커밋돼 47edadb 트리에 있다(`git ls-tree --name-only 47edadb harvest/astra_motion/` 15). `:54` "`ckpt/ma1b/` | E-MA1b `[진행 중]`" — E-MA1b는 2df9bdc에서 끝났고 같은 책 `01:52` 상태 칸은 "끝"이다(책 안 모순). 장 머리 `:3` "확인 시각 2026-09-25 18:4x UTC"는 이 두 줄이 쓰인 시각이지만 같은 장이 20:01·20:37에 고쳐지며 20:10 UTC 사실까지 담게 돼 장 시각으로 두 줄을 덮을 수 없고, 책 README `:9`("결과가 나오면 **같은 커밋**에 해당 장을 고친다")·`04:3`("바뀌면 같은 커밋에서 고친다")을 3500f54·2df9bdc가 어겼다(27회차 범위 안이었으나 놓침). **고칠 것**: `:16`을 "탐침 코드(3500f54, 시험 `tests/astra_motion/` 62)", `:54`를 "E-MA1b 끝(불채택, `R/ma1b`)"으로, `:3` 확인 시각 갱신, 같은 커밋에 06 줄. (같은 장의 새 파일 누락은 N90.)

(검토했지만 DOC로 올리지 않은 후보: ① `06-updates.md:12` 19:58 줄의 정정 표시가 표 행 끝 `|` 뒤 다섯째 칸에 붙어 렌더에서 사라진다 — 27회차 N54(P04)와 같은 종류라 NOTE N84(다만 **P68을 더한 바로 그 커밋**에서 P68 예방 규칙 "칸 단위 수정, 칸 수 검사"를 어겼다). ② 결과 `astra_motion.md` 5절 표 Qwen 줄·`01:60` "Qwen 0.36 → 0.047"에 판본 혼재 표시가 없다 — 같은 문서 0절 `:7`·등록 14절이 밝히므로 실험 절 NOTE E-N13. ③ 정본 §86 보충이 책 03에 없다 — 27회차 N72와 같은 종류 NOTE N87.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 R2_TRAIN Isaac 워커 5개 진행 중(20:42Z, `gen gen --kinds P2 --seeds 10800-10999 --confirm-train`, standard 3·dr 2, GPU 0·1; P2 편 68–94/200; 읽기만); 확인 인자 없는 `--seeds 25000` 거부(가드 19). 폴더 행 병합은 아직(D-1·N94).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 47edadb에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현 및 §84·§86(+보충) 결합 설계 구현**(직렬 흐름, 두 층 M4, 카메라 3대·덧그림, `CoupleParams` 상수) — "R7 E2E 준비 기준점 뒤". 지금 코드: 파드 `closed --hb-mode K8`·`"K0,K5"` → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 22 Astra 4행), 흐름 호출 없음.
- S19. **정본 §83 런타임 적용**(새 직렬화 판본) — DEV 22 결정 호출 요청 102/102 `motion:` 없음.
- S20. **E-CAM3·E-MA3 결과**: 두 실험은 20:38Z부터 GPU 2·3에서 진행 중(기준 재사용 검사 끝, `cam3_s1`·`kv_s1` 학습 중, 20:54Z) — 결과·판정 파일은 아직 없고 예측·평가 파일은 열지 않았다(실험 절 7.3).
- S21. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86 "E-Couple에서 판정 밖으로 다시 잰다").

## 4. NOTE
- N1–N3. (그대로) `stageb_train predict`·`evalck`의 `prompt_config` 비대조, `cli_label.replay_max` NaN 순서, 판정 스크립트 입력 검사 수준(책 P25).
- N4. (해소, 27회차와 같음).
- N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45. (그대로, 27회차 목록.) N10 재현: 가드 25(`e05 --data jsel_dev/P0 --split pool --seeds 2111` → "no episode selected")가 빈 `g25/`를 남김.
- N46. (그대로) `RESUME_KEYS`의 `a3d_root`.
- N47·N48. (해소, 27회차와 같음.)
- N49–N52. (그대로) 25회차 시각, 책 `05:13` 출처, `01:50`·`05:33` "15:53–17:21", `05:31` `[미기록]`.
- N53. (그대로) `03:4` §56–§62 날짜 주의·`03:62` 표시.
- N54. (해소) `02:12` P04 표시가 넷째 칸 안으로 옮겨졌다(칸 수 5 = 머리, `check28` H4).
- N55. (일부) `04:61` → D-1; `01:12`·`01:20`·`01:67`은 그대로(`01:67`은 N92).
- N56. (해소, 이력.)
- N57, N58. (그대로) 탐침 등록 0절 꼬리표, 수정 1의 유료 호출 선행.
- N66·N67. (해소) `01:38` 표시가 괄호 뒤로, 행 이름 "1–27회차"(27회차 보고서가 같은 커밋 — 맞음; 23–27회차 FAIL, handoff §2.8과 일치).
- N68. (일부) `06:12` 19:58 줄에 "커밋 2df9bdc 시각은 19:49:56 UTC" 표시를 더했다(값 맞음) — 표시가 칸 밖(N84).
- N69. (해소) draft-log `:477` 표시 "지운 것은 r7c1–r7c24·pytest 임시 폴더; r7c25·r7c26은 남겨 두었고 r7c25는 27회차가 지움" — 이번 회차 시작(20:41Z) 때 `D:\tools\scratch_qdd`의 r7c 폴더는 r7c26·r7c27만(r7c1–r7c24 폴더·`pytest_tmp` 없음; `r7c*_docfix.py` 등 16 KB 파일만 남음), 27회차 보고서 §6.7(r7c25 132 MB 삭제)과 맞다.
- N70. (해소) `05:14`·`:15` = 장부(아래 §7.1).
- N71. (그대로) 정본 §85 보충(`:777`)이 §86 본문 뒤 — 책 03 `:70`이 "(정본에서는 §86 본문 뒤에 붙어 있음)"으로 밝힘. 이번에 §86 보충(`:778`)이 그 뒤에 붙어 순서는 §85 보충 → §86 보충.
- N72. (해소) `03:70` §85 보충 행(20:01, 수치 = 정본 `:777`, 칸 수 4).
- N73. (그대로) 정본 §66 `:563` "본 생성 계획(아직 실행 안 함)".
- N74. (그대로) 스펙 `:123`·`:130`·`:180`·`:185` "[→ §17]" 꼬리표 권함.
- N75–N78, N80–N83. (27회차 회차 자체 기록 — 이번 회차 값은 N95–N101로 새로 적음, 건수에 넣지 않음.)
- N79. (일부) 계획 PROBE 표 `:67`·코드 `:278` `timeout_s` 15 → **20.0**(정본 §86 보충; 계획 시험 `:1084`·`:2265`는 `timeout_s=15.0`을 명시해 기본값 변경과 무관). 그러나 같은 표의 `request_mode "F1"`(`:65`/`:275`), `stale_edit_s 6.0`(`:68`), `latency_init_s 3.0`(`:66`, 실측 p50 9–10 s)은 탐침 전 자리표시 그대로다 — 한 행만 탐침 뒤 값이라 표가 섞였다(머리 `:61` "기본값은 탐침 사전 등록과 같게", 코드 머리 "defaults until … sets them"과 Step 0-2가 여전히 유효라 틀린 서술은 아님). 구현 Task 1 전에 Step 0-2로 F0·15 s·지연 초기값을 함께 채우거나 행마다 "[→ §86]" 꼬리표.
- **N84.** `06-updates.md:12`(2df9bdc 19:58 줄) — 정정 표시 "[→ 정정 2026-09-25 20:37 UTC, R7 27회차 N68: …19:49:56 UTC]"가 행 끝 `|` **뒤**에 붙어 다섯째 칸(머리 4칸)이 됐다 → GFM은 넘치는 칸을 버려 렌더에 표시가 안 보이고 "19:58"만 남는다(`check28` H4·H7: 변경 md 17개 중 칸 수 불일치 유일). 27회차 N54(P04)와 같은 모양이며 **P68("표 행 수정은 칸 단위로, 쓴 뒤 칸 수 검사")을 더한 같은 커밋**에서 생겼다. 표시를 넷째 칸 안으로.
- **N85.** `06-updates.md:16` E-MA3 줄 "2026-09-25 20:35"는 그 커밋 40895f8 시각 20:34:19 UTC보다 늦다(P11; 27회차 N68과 같은 계열). 5c46056 줄 20:31(커밋 20:33:20)·47edadb 줄 20:37(커밋 20:37:43)은 앞선다.
- **N86.** 기록 줄 시각 "20:3x"(handoff `:126` "(2026-09-25 20:3x UTC)", draft-log `:478`, direction-log `:74`) — `date -u` 값이 아닌 자리 표시(P11). 27회차 보고서 작성 20:40 UTC 무렵, 정정 커밋 20:37:43 UTC.
- **N87.** 정본 `:778` "§86 보충(20:37 UTC) 흐름 요청 시간 초과 = 20 s·요청 방식 기본값 F0"이 책 03 결정 연표에 없다(03 `:71` §86 행은 "늦은 답 폐기 6→15 s"까지만). 27회차 N72(§85 보충 누락)를 고친 **같은 커밋**에서 같은 종류가 생겼다. 03에 "§86 보충 | 20:37 | 흐름 요청 시간 초과 20 s(계획 `timeout_s` 15 대체)" 한 줄.
- **N88.** 인용 출처: 정본 `:778`은 "결과 문서 5절 표의 지연 p95 F0 11.6 s·F1 14.1 s(편 평균), 요약의 p95 범위 12–16 s"로 바르게 나눴지만, 스펙 §17 `:199`는 "지연 p95 범위 12–16 s 위; **결과 문서 5절**"이라 적는다(12–16 s는 0절 요약 `:6`; 장부 전체 p95 F0 12.29·F1 16.00 s). 값은 맞음(출처 표기). 또 탐침의 `STREAM_TIMEOUT_S = 20.0`(`harness.py:45`)은 **시뮬 초**(실시간 0.38배 편에서는 벽시계 약 53 s)라 "탐침 실행기와 같음"은 수치만 같다 — 결합 런타임의 `timeout_s`가 벽시계인지 구현 때 명시 권함. (N89 번호는 비워 둠 — 계획 표 건은 N79에 합침.)
- **N90.** 책 04 지도에 대상 트리의 새 파일·경로가 없다: `harvest/train/se2e_cam3.py`·`se2e_kvcond.py`(`:13`), `tools/cam3/`·`tools/ma3/`·`tools/se2e/paired_verdict.py`(`:18`–`:20`), 파드 `code_cam3`·`code_ma3`(`:45`), `ckpt/cam3`·`ckpt/ma3`·`data/cam3`(`:50`–`:56`). 틀린 서술은 아님(D-2와 같은 커밋에 보충 권함).
- **N91.** P68(기록·커밋 주제)이 다. 절(파드·셸·프로세스) 표 끝 P67 뒤에 있다 — 번호 고정 규칙상 문제는 없고 절 배치만 어긋남.
- **N92.** 책 `01:67` R2_TRAIN 줄 "생성 중(작업자 5, P0 시드 10000–10599 …) — `R/ma1.md` 17:3x 기록" — 시각이 붙은 옛 상태(틀린 현재 서술 아님)지만 `04:61`(20:10 P2)과 다르다; D-1 고칠 때 같은 줄을 맞추기 권함.
- **N93.** handoff에 진행 중인 E-CAM3·E-MA3(사전 등록 커밋 5c46056·40895f8, GPU 2·3) 줄이 없다(책 `01:61`·`:63`에만). 사전 등록 커밋에 handoff 줄을 요구하는 규칙은 없어 NOTE; handoff `:89` "GPU 3 = vLLM" 운영 규칙과 E-MA3 학습(GPU 3)의 관계를 한 줄로(움직임 줄 확인 실험도 GPU 2·3 학습을 썼다 — `:121`).
- **N94.** (운영 위험, D-1과 같은 원자료) R2_TRAIN 폴더 행 파일 18개가 12:19–12:20Z 파일럿 병합(P0 19–41시드, P1 11–19, P2 10–20)인 채로 남아 있다. 생성이 끝난 뒤 `gen check`(검증 도장 + `merge`)를 다시 돌리지 않으면 단계 B 학습(`--data r2 --pool <folder>` 기본 `<folder>.stageb.jsonl`)이 **파일럿 부분집합만** 읽는다. R2_TRAIN 보고·단계 B 사전 등록 전에 병합 여부·행 수 대 편 수를 확인하는 단계를 넣을 것.
- **N95.** 텍스트 위생: 사본 텍스트 537파일 CR 0; 변경 md 17개 BOM·C0·C1·영폭 0, 표 칸 수 불일치는 `06:12` 하나(N84). (`check28`가 `r7_cycle27.md:185`를 7칸으로 잡은 것은 `\|delta\|`의 이스케이프 파이프를 센 내 계수기의 오검출 — GFM에서는 5칸, N101.) 책 링크 101개 끊김 0.
- **N96.** 시험 수: 로컬 **1133 passed / 20 skipped**(234.8 s, 20:41:43–20:45:39Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c28/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1 — cam3_cli·kvcond_qwen·ma3_chunk_eval 3 추가), 파드 CPU **1280 passed / 4 skipped**(176.3 s, EXIT 20:49:14Z; 건너뜀 isaaclab·pyarrow 경로·CUDA·TODO), 경고 1(기존), LeRobot 6 passed(19.5 s). 새 시험 15개(로컬 실행분) = `test_ma3_verdict` 1·`test_cam3_build` 2·`test_paired_verdicts` 4·`test_se2e_cam3` 8(`--collect-only`). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- **N97.** 단계 B 소형 CPU 스모크(20:53Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–27회차와 같은 값 — 결정적), expert p50 0.033 s·전체 p50 0.106 s, 맥락 토큰 454.
- **N98.** DEV 22 판: 행동 1,691·16.91 s·결정 호출 51(조건마다), C5 `last_step` {none 1, OK 34, DEVIATE 10, LAG 4, CONTRADICT 2}, C5' none 51/51, 확정 비율 0.8538, 결정 3.018/s, rtf 0.397, 지연 p50·p95 0.3 s, Astra 2(hb 5.0 → 8.0, sub 8.92 → 11.92), `code_sha` `df7fcd9234b49658`, 파일명 `dev22-P0-standard-e0`, 판 248.1 s(20:54:16–20:58:24Z).
- **N99.** 파드 GPU(20:42Z·20:55Z): 0 = R2_TRAIN 워커 2(P2), 1 = R2_TRAIN 워커 3(+ 내 Isaac 20:54Z–20:58:24Z), 2 = E-CAM3(`se2e_cam3 train`, 20:42:33Z 시작, 86.8 GiB), 3 = E-MA3(`se2e_kvcond train`, 20:45:13Z 시작, 87.5 GiB).
- **N100.** 파드 정리 대상 판별: (`attr28.sh`) 내 Isaac 창(20:54:16–20:58:24Z)에 생긴 `tmp/carb.5CpR5e`(20:54:17 생성, Kit 임시)·`tmp/tmp3mno15c8`(20:54:37, `_remote_module_non_scriptable.py`; `.pyc`가 `cache/pyc_r6` 아래 = 내 워커의 접두)·`pyc_r6/…/r7c28`(20:54:16, 772 KB)·`kitcache/cyclo-r7c28_standard`(20:54:16, 208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-CAM3·E-MA3 학습 2개와 GPU 감시 `nvidia-smi` 2개뿐이고 모두 `PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc`(pyc_r6 아님)·20:54Z 전 시작 → 두 임시 항목은 내 것.
- **N101.** (절차, 내 쪽) 자체 점검으로 다시 설계한 항목 3개: ① `pod_eval28.sh`의 LeRobot 왕복이 R2 DEV에 없는 편(dr ep6·ep7; DEV는 폴더마다 ep0–ep5)을 골라 0편 내보내기·`verify` rc 1 → `lr28.sh`로 있는 편(dr/mug_marker/P0 ep5 참, standard/bottle_tray/P0 ep3 거짓)으로 다시 돌려 통과(행 138). ② `check28` H4 칸 계수기가 이스케이프 파이프를 셈 → `r7_cycle27.md:185` 오검출(N95). ③ `cm28.sh` 첫 초안의 `python3 -c` 두 줄(규칙 위반)을 실행 전에 Write 도구 `cm28.py`로 바꿨다. 또 `e05 --truth outcome:plan`은 27회차와 다른 POOL 2015·2071·2118을 골라 `claim` "insufficient_data"로 끝났다(오류 아님, `E05_DONE`).

---

## 5. 사전 등록 대조표 (행마다 이번 회차의 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check28` H3), 파드 산출 `meta.prereg.check` = OK. 27회차 표의 행 번호를 그대로 쓴다. 기준선 코드 블롭은 7a02943 = 47edadb(H2). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c28\check28.py`(H1–H7), **파드** = §6(`pod_cpu28.sh`, `pod_eval28.sh`·`data28.py`·`lr28.sh`, `pod_isaac28.sh`·`closed28.py`, `exp28.py`, `rows28.py`·`rows28b.sh`·`r2plan28.sh`, `cm28.sh`·`cm28.py`, `attr28.sh`·`clean28.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 가드 28건 rc ≠ 0(§6.4): TEST 1148·1050·1099, CAL 503·530·537, TEST-P5 1311, DEV 33·1500, POOL 2121, gen 25000(확인 없음)·70000·3199(확인 있음), determinism 1329·2125 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | 코드 무변경; `calib --heldout jsel_dev/P2 --episodes 2` → `CALIB_DONE`; 가드 3(`--fit-split test_p5`)·4(`--heldout-split cal`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 22** C5·C5' 성공(16.91 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 22 결정 호출 102행**(조건마다 51): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 102/102; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치 |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P1 --split dev --episodes 2` → `E05_DONE`; 가드 24(`canary build-set --seeds 3100-3101`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H`·`m4_lead_max` 3·1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C4'"` → "condition \"C4'\": runtime has ['C0' … 'C6']"; **DEV 22 C5 `last_step` {none 1, OK 34, DEVIATE 10, LAG 4, CONTRADICT 2}, C5' none 51/51, 요청 본문 마지막 `last_step:` 줄 = 행 값 102/102** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard,dr/P1 --episodes 2` → `RD_DONE`; 가드 5 `rd --variants dr=… --split cal` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=-0.0` → "lead_max = -0.0 … finite > 0", 가드 15 `=+inf` → "lead_max = inf … finite > 0", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 기존 블롭 불변(H2; 새 `paired_verdict.py`는 추가 파일); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(21:01Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2015,2071,2118 --truth outcome:plan` → `E05_DONE`(claim insufficient_data, N101) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 22, 20:54:16–20:58:24Z)**: 행동 **1,691개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 51·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | R2_TRAIN 워커 5개 `code_r2train_e8e1864`(`run.sh`), P2 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119" 폴더 없음; 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu=-1`·`5` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 22 hb 5.0 → 8.0, sub 8.92 → 11.92, 겹침 0 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 2편**(standard/bottle_tray/P0 ep3 = `valid_for_training` 거짓 → 건너뜀, dr/mug_marker/P0 ep5 참): 1편·288프레임, `verify` 오류 0·PSNR 최소 38.02 dB·lerobot 0.3.3 적재 288프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 음성 대조 11종**(dr/bottle_tray/P0 ep0, 370프레임): 무수정 오류 0; k185 시각 +9.9e-7 s(허용 1e-6 안) → 오류 0; +1.01e-6 s → "off the 30 Hz grid by 1.01e-06 s"; k 중복 → "frame indices not contiguous from 0"; k185 손목 영상 항목 삭제 → "k185: missing cam_wrist_right"·"images 739 != frames 370 x cams 2"; k0 손목 ← 머리 JPEG → "k0 cam_wrist_right: size (672, 376) != native (424, 240)"; 행 k184 삭제 → "stageb rows are not one per non-terminal frame"; 행 k123 hz 10 → "row k123: hz 10 != 30"; `proprio_mask {q: 2}` → "proprio_mask: keys from …, values 0/1"; `committed {Q_BOGUS}` → "committed: unknown question Q_BOGUS"; npz `tau` 369 → "npz tau: length 369 (want 370)"; `grip` inf → "npz grip: … non-finite" | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 22 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | E-CAM3·E-MA3 등록 0절 자체 검사(결정·표본·사전 실행·도중 관문) 있음, 유료 0 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 블롭 6483397 = 47edadb = 파드 `code_cam3`·`code_ma3` 사본(`98ff930ccb787ffe`); 옵트인 CLI 포장의 옵션 끔 = `stageb_train`(파드 시험 통과), 가드 29–32 | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | §6.3: 링크 101개 끊김 0, 01·03·05 수치 원자료 대조, 06 갱신 줄 전수 | **DOC D-1·D-2** / NOTE N84–N92 |
| **156** | 정본 §86 = 탐침 결과 (`:766`–`:776`) + §86 보충(`:778`) | — | 27회차 원자료 재계산 유지; 보충의 20 s = `harness.STREAM_TIMEOUT_S`(시뮬 초), 11.6/14.1 = 5절 표, 12–16 s = 0절 | 일치(N88) |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 (새 행, 실험 절) | `se2e_cam3`, `se2e_kvcond`, `tools/cam3`·`ma3`, `paired_verdict` | 7장 X9–X16 | 일치 |

### 5.1 27회차 표와의 차이
- 행 157(E-CAM3·E-MA3, 실험 절)을 더했다. 근거 교체: 행 1(새 경계 가드 28건), 5·6·51–58·99·137·151(DEV 22), 13–17·61–62(jsel_dev/P1·dr/P1), 66–67(`-0.0`·`+inf`), 138·139(다른 편·새 음성 대조 11종), 154(새 옵트인 파일과 파드 고정 사본).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status 7a02943 47edadb`: 코드 = 새 파일 16개(A) — `harvest/train/se2e_cam3.py`·`se2e_kvcond.py`, `tools/cam3/{build_cam3,cam3_latency,cam3_verdict}.py`, `tools/ma3/{chunk_eval,ma3_latency,ma3_verdict}.py`, `tools/se2e/paired_verdict.py`, 시험 7개; 기준선 코드 변경 0(H2). 문서 = 책 6장(01 +3/−3, 02 +2/−1, 03 +1, 04 +1/−1, 05 +2/−2, 06 +5/−1), 정본 +1(§86 보충), 스펙 +1(§17), 계획 +2/−2, handoff +2/−1, draft-log +2/−1, direction-log +1, 등록 `prereg_astra_motion.md` +3(14절)·새 `prereg_cam3.md`·`prereg_ma3.md`, 결과 `astra_motion.md` +4/−4, `r7_cycle27.md`.

### 6.2 27회차 정정 주장 대 실제 diff·원자료 (47edadb)
| 주장 (06 `:17`·`:18`, handoff `:126`) | 실제 diff | 원자료·원 문서로 참인가 | 판정 |
|---|---|---|---|
| 04 R2_TRAIN 생성 계획(D-1) | `04:61` 괄호 → "생성 계획 P0 10000–10599 → P1 10600–10799 → P2 10800–10999(2026-09-25 20:10 UTC 기준 P2 생성 중) [→ 정정 …: 앞 정정의 'P0 생성 중'은 틀림 — 19:07Z에 P0 행 조립 끝·P1 생성 중이었다]" | 계획 = 파드 `r2train/full_slot.sh` `B="P0:10000-10599 P1:10600-10799 P2:10800-10999"` ✓; 20:10 P2 = 워커 5개 `--kinds P2 --seeds 10800-10999` 20:01:59–20:02:14Z 시작 ✓; 19:07Z P1 생성 중 = P1 편 mtime 19:41Z(standard)·20:02Z(dr) 끝 ✓; **"P0 행 조립 끝" ✗**(폴더 행 파일 = 12:19Z 파일럿 병합, 19–41시드/600) | **D-1** |
| 01 표시 위치·제목(N66·N67) | `01:38` "FAIL(8회차 DEFECT 5 등) [→ 정정 … N66·N67]", 제목 "1–27회차" | handoff §2.8 PASS = 6·16·20·22회차, 23–27 FAIL ✓; 링크 모양 사라짐(H5 가짜 링크 0) | 맞음 |
| 02 P04 칸 안(N54), P68 추가 | `02:12` 표시가 넷째 칸 안(칸 5 = 머리) ✓; `02:54` P68 5칸 ✓ | P68 내용 = 27회차 D-1·N54·N66 ✓ | 맞음(배치 N91) |
| 03 §85 보충 행(N72) | `03:70` "§85 보충 \| 20:01 \| E-MA1b … 불채택: 합동 +0.0031 [−0.0022, +0.0085] …" | 정본 `:777`(20:01 UTC, 같은 수치, "R2_TRAIN 뒤 E-MA1 재등록") ✓ | 맞음(§86 보충 누락 N87) |
| 05 토큰·호출 수(N70) | `05:14` 588/738/892, `:15` "72(끝난 뒤 도착 6 포함)" | 장부 G1 v2 160행 입력 588(40)·738(40)·892(80) 편차 0; S2 72행 = 편 안 도착 66 + 끝난 뒤 6(편마다 1) ✓(§7.1) | 맞음 |
| 06 19:58 줄 시각(N68) | `06:12` 끝에 "[→ 정정 … 2df9bdc 시각은 19:49:56 UTC]" | 2df9bdc 커밋 시각 2026-09-26T04:49:56+09:00 = 19:49:56 UTC ✓ | 값 맞음, **칸 밖**(N84) |
| 정본 §86 보충(N79) 시간 초과 20 s | `:778` 새 줄 | 20 s = `harness.py:45` `STREAM_TIMEOUT_S = 20.0` ✓(시뮬 초 — N88); "5절 표 p95 F0 11.6·F1 14.1(편 평균)" = 결과 `:54`·`:55` ✓; "요약 p95 12–16 s" = 결과 `:6` ✓; "계획 `timeout_s` 15 s 대체" = 계획 diff ✓; "요청 방식 기본값 F0" = §86 ✓ | 맞음 |
| 스펙 §17·계획 `timeout_s` | 스펙 `:199` 한 줄, 계획 `:67`·`:278` 15.0 → 20.0 | 정본 보충과 같은 값 ✓; 계획 시험은 15.0을 명시 전달(`:1084`·`:2265`) | 맞음(출처 N88, 표 혼재 N79) |
| handoff §2.8 27회차 줄 | `:126` DEFECT 0·DOC 1·SCOPED 21·NOTE 61, 실험 절 FAIL DOC 2 | `r7_cycle27.md` 판정 표와 같음 ✓ | 맞음(시각 N86) |
| draft-log N69 표시·27회차 줄, direction-log | draft-log `:477` 표시·`:478`, direction-log `:74` | N69 표시 내용 = 현재 D: 상태·27회차 §6.7과 맞음 ✓ | 맞음(시각 N86) |
| 결과·등록 정정(E-D1·E-D2) | §7.1 | §7.1 | 맞음(E-N12·E-N13) |
| 갱신 기록 | 47edadb의 책 변경 01–05 → 06 `:17`·`:18` 두 줄(20:37) ✓; 5c46056(01) → `:15`, 40895f8(01) → `:16` ✓ | — | 맞음(N85) |

### 6.3 기록책 (47edadb 사본에서)
- 갱신 기록(H6): 규칙(4117851) 뒤 책을 고친 커밋 10개 가운데 06 줄이 같은 커밋에 없는 것은 641547e 하나(다음 커밋 6483397이 보충, 27회차 N56). 06 줄 시각이 커밋보다 늦은 것: 2df9bdc 19:58(표시 더함, N84), 40895f8 20:35(N85).
- 수치: `05:13`–`:18` = 장부(§7.1, 반올림 `:16` 224·5.7 s는 E-N10), `01:52`·`:60` = 27회차 원자료 재계산값과 같음(`01:60` Qwen 표시 E-N13), `01:61` E-CAM3 "시각 토큰 356 → 460"·20:30:33Z = 등록 0.3절·머리, `01:63` E-MA3 20:34:02Z·"블록 i ← 층 L_i" = 등록, "GPU 2"·"GPU 3" = 파드(N99); `03:70` = 정본 `:777`; `04:61` → D-1; `04:16`·`:54` → D-2; `02` P68 출처(27회차 D-1·N54) 확인.
- 링크 101개 끊김 0(H5).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 20:51:36–20:51:57Z, 21–27회차와 다른 값)
1 `e05 --data P2 --split test --seeds 1148`, 2 `e05 --data P1 --split cal --seeds 503`, 3 `calib --fit-split test_p5 --heldout P2 --heldout-split dev`, 4 `calib --fit-split pool --heldout P2 --heldout-split cal`, 5 `rd --variants dr=gen_dev/dr/P2 --split cal`, 6–8 `closed --split test --seeds 1050`·`cal 530`·`test_p5 1311` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 12,33`, 10 `pool --seeds 2121`, 11 `dev --seeds 1500` → "not in split … never opened"; 12–13 `--isaac-gpu=-1`·`5` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=-0.0`, 15 `=+inf` → "lead_max = -0.0 / inf … finite > 0 s"; 16 `--conditions "C4'"` → "condition \"C4'\": runtime has ['C0', …, \"C5'\", 'C6']"; 17 `HARVEST_ALLOW_SPLIT=test_p5` + `closed --split cal --seeds 537`, 18 `=cal` + `e05 --data P0 --split test --seeds 1099` → 거부; 19 `gen --seeds 25000`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 70000 --confirm-train`, 21 `--seeds 3199 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 1329`, 23 `history --seeds 2125` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P0 --seeds 3100-3101`, 25 `e05 --data P0 --split pool --seeds 2111` → "no episode selected"; 26 `--hb-mode K8`, 27 `--hb-mode "K0,K5"` → "from ('K0', …, 'K4')"; 28 `stageb_train train --aux-extra a3d@v2` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 train --data r2 --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 train --data se2e --cam3 cam3@v1`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)", 31 `se2e_kvcond train --expert-cond kvcond@v2`, 32 `se2e_cam3 train --cam3 cam3@v2` → argparse "invalid choice" rc 2. **32건 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c28\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c28/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0(cam3·kvcond·chunk_eval torch 시험 포함). 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 음성 대조 11종; LeRobot 시험 6 passed, 새 편 내보내기·검증·적재(행 138); `se2e_c1` **5/5 OK**(21:01Z). (R2_TRAIN 폴더 행 병합은 아직 — N94, 완료 정의 1은 R2 DEV 기준.) |
| 2 모델 | 충족(CPU) | CPU 스모크(N97), CPU 묶음의 단계 B·E-MA1b·E-CAM3·E-MA3 시험 통과, 기준선 파일 블롭 불변. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 22 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c28`: `CLOSED_DONE` C5·C5' 1.0, 호출 51·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 20:51:57–20:52:33Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`(dr 낙폭 평균 −0.0032), `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). HEAD 시작·끝 47edadb.
- 파드 정리: (`clean28.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 21:02:35Z): `tmp/r7c28`(510 MB), `tmp/carb.5CpR5e`·`tmp/tmp3mno15c8`·`cache/pyc_r6/data/harvest/tmp/tmp3mno15c8`·`cache/pyc_r6/data/harvest/tmp/r7c28`, `ir/kitcache/cyclo-r7c28_standard`(208 MB). 끝에 r7c28 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c28이 든 프로세스 0, `IR_INST=r7c28` 프로세스 0, 열린 핸들 0. 탐침·E-MA1b·E-CAM3·E-MA3·R2_TRAIN 파일은 읽기만.
- 로컬: 추출 사본 `repo/`(589파일)·pytest basetemp `pt/`·archive `a28.tar`(21 MB) 삭제, 보고 근거 스크립트·출력(`check28.py`·`check28_out.txt`·`pod/`·`*_out.txt`)만 남김(512 KB). 지시대로 `D:\tools\scratch_qdd\r7c26`(28 MB) 삭제 — r7c 폴더는 r7c27·r7c28만. D: 여유 8.1 GB(끝).

## 7. 실험 코드 절 (별도 판정: PASS — 코드 결함 0, DOC 0)

### 7.1 27회차 실험 절 정정(E-D1·E-D2) 대 원자료 (파드 `exp28.py`, 읽기만)
- 비용 장부 `logs/astra_motion/cost.jsonl` **256행, 6,933.37원**. 단계별: API 3(0원), 옛 G1 13(203.99원, 입력 507/657/811 × 3·2·8행), **G1 v2 160(2,682.00원; 입력 588 × 40·738 × 40·892 × 80, 편차 0)**, G2 high 8(223.46원, 입력 892 × 8), S2 F0 45(2,244.73원)·F1 27(1,579.19원).
- **E-D1 ① `astra_motion.md:23`·책 `05:14` 588/738/892 — 맞음.** ② **`:24`·`05:15` "72(끝난 뒤 도착 6 포함)" — 맞음**: 편마다 장부 행 = 편 안 도착 + 1(F0 12/11·10/9·23/22, F1 9/8·8/7·10/9) → 66 + 6. ③ **`:82` "17편에서 close" — 맞음**: `qwen8b/S` 20편 중 `first_close` 17, 첫 close 오차 중앙 223.4 mm(close만)·238.5 mm(없음 = ∞ 포함).
- **E-D2 등록 14절·결과 `:7` — Qwen 판본 맞음**: `qwen8b/S-stream-F{0,1}` s0·s7 4편 `prompt_id` = `a84e4c76efed`(17:47:03–17:51:56Z), s14 2편 = `9b5c5c292765`(18:19:52·18:21:23Z); Qwen 동기 S 20편·Astra S2 6편 결과 = `9b5c5c292765`; Astra S2 장부 72행 `meta.prompt_id` = `9b5c5c292765` 72/72. **다만** 14절의 "Astra 유료 호출(G1 v2 160·S2 72·G2 8)은 모두 `9b5c5c292765`(**R7 27회차가 원장으로 확인**)" 가운데 G1 v2·G2 168행은 장부 `meta`에 `prompt_id` 필드가 없다(키 kind·overlay·rep·snap·views) → E-N12.
- 결과 표의 호출당 값(2,207/244·2,486/302·49.7/58.0원)은 `agg.stream_metrics`의 "도착한 답(편 안 66) 평균의 편별 평균"이다(장부 편별 평균은 끝난 뒤 도착 포함 2,206.7/245.3·2,487.0/309.6·49.78/58.51원) → E-N14.

### 7.2 E-CAM3·E-MA3 사전 등록 대 코드·파드 (X9–X16; 예측·평가 파일은 열지 않음)
| # | 등록 값 | 구현 | 확인 | 판정 |
|---|---|---|---|---|
| X9 | 고정 코드 LF sha256 앞 16(cam3 7절 9파일, ma3 7절 8파일) | 커밋 블롭 | `check28` H1: 17/17이 47edadb·등록 커밋(5c46056·40895f8) 블롭과 같음; 파드 `code_cam3`·`code_ma3` 사본 해시 같음·CR 0, 기준선 `stageb_train/model/expert.py` 사본 = 47edadb | 일치 |
| X10 | 채택 규칙 cam3: 합동 ≥ +0.02 ∧ 하한 > 0(엄격) ∧ 전이 ≥ −0.01 ∧ FULL p95 비 − 1 ≤ 0.10, 상대 CMP_EPS 1e-12 (6절) | `cam3_verdict.rule`, `paired_verdict.ge/le` | 코드 = 등록 문장(`ge(x, t) = x ≥ t − 1e-12·max(1,\|t\|)`, 하한 `> 0`); 파드·로컬 시험 `test_paired_verdicts`·경계 시험 통과 | 일치 |
| X11 | 채택 규칙 ma3: r ≥ 0.05 ∧ r 하한 > 0 ∧ 정확도 하한 ≥ −0.01 ∧ FULL p95 비 − 1 ≤ 0.10 (6절) | `ma3_verdict.rule`, `paired_verdict.rel_reduction` | r_s = 1 − mean(kv)/mean(none), 합동 = 평균, 네 판 같은 부트스트랩 추출(시드 0, 10,000) — 등록과 같음; `test_ma3_verdict` 통과 | 일치 |
| X12 | 입력 검사: 네 판 키 같음·1,799·(키, 질문) 중복 없음·요약 재현; ma3 청크 키 = 항목 키·청크 평균 = 요약 | `load_runs`, `ma3_verdict.main` | 코드에 모두 있음(요약이 없으면 재현 검사 생략 — E-N15) | 일치 |
| X13 | 층 L_i = ⌊(i+1)·36/8⌋ − 1 = 3, 8, 12, 17, 21, 26, 30, 35; K = `k_norm(k_proj(x))`(RoPE 전)·V = `v_proj`, 1024; 사상 8 × 1.58M; KI stop만 | `se2e_kvcond.kv_layers`, `_Capture`, `KVProj`, `as_kvcond` | 식 계산 = 등록 목록; 블록당 2 × (LN 2,048 + 선형 786,432 + 768) = 1,578,496 → 8블록 12.63M; `ki != "stop"` 거부; 파드 `test_se2e_kvcond_qwen.py` 9개(공유 접두 = 문맥별 K·V, 저장·재적재, 기본 적재기 거부 등) 통과 | 일치 |
| X14 | cam3 입력: [머리, 활성 손목(기준 이름표), 반대 손목] 덧붙임, 양팔 행 불변, 없는 프레임 오류, `prompt_config` 새 sha; `--data se2e`·움직임 줄만 | `apply_cam3`, `mark_prompt_config`, `install` | 가드 29·30·32(§6.4); `test_se2e_cam3` 8·`test_se2e_cam3_cli` 4 통과 | 일치 |
| X15 | 데이터: RB1 22,378장(718편)·RB2 13,799장(656편) = 36,177, 빠짐 0, 활성 손목 881장 바이트 동일; 사용 39,283행(25,433 + 13,850), 양팔 3,106 | `build_cam3.py` | 파드 `data/cam3/build_cam3.json`(데이터 준비 기록): RB1 718편·22,378/22,378·check 472·불일치 0, RB2 656편·13,799/13,799·check 409·불일치 0(472 + 409 = 881); `logs/cam3/feasibility.json`: used 25,433·13,850, 양팔 3,055 + 51 = 3,106, 한 손 13,792 + 8,586·5,910 + 7,889, 반대 영상 없음 0 | 일치 |
| X16 | 문턱 근거(이미 본 것): none 0.02992/0.03208(+7.2 %), motion 0.02960/0.03062(+3.5 %), 짝 −1.1 %·−4.5 %(합동 2.8 %); A3d 확정 보기 0.0298·0.0312; 순서 = 등록 → 커밋 → 본 실행 | 기준 요약·파드 시각 | `logs/se2e_confirm/predfull_{none,motion}_s{1,2}` 요약 `sample_mse_norm` 0.029919·0.032082·0.029598·0.030623(비율 1.0722·1.0346, 짝 −1.07 %·−4.55 %); `ma1b.md:29` 0.0298·0.0312; 사전 실행 20:22–20:25Z(등록에 적힘) → 등록 20:30:33Z·20:34:02Z → 커밋 20:33:20Z·20:34:19Z → `run_cam3.sh` 20:33:48Z·`run_ma3.sh` 20:34:44Z → 첫 본 산출 20:38:14Z·20:40:02Z(P15 순서 지킴); GPU 2 = cam3(20:42:33Z)·3 = ma3(20:45:13Z) | 일치 |

### 7.3 이번에 하지 않은 것
- E-CAM3·E-MA3 예측·청크 평가·재사용 검사 출력(`logs/cam3/predfull_none_s*.jsonl`, `reuse_check.out`, `logs/ma3/chunk_none_s*.jsonl`, 학습 로그)은 지시대로 열지 않았다 — 기준 재사용 비트 동일(등록 3절 (2))은 결과 커밋 때 검토.

### 7.4 DOC (실험 절)
없음.

### 7.5 NOTE (실험 절)
- E-N1–E-N11. (27회차 그대로; E-N3 해소.)
- **E-N12.** 등록 14절(`prereg_astra_motion.md:142`)의 "(R7 27회차가 **원장으로** 확인)"은 S2 72행에만 맞다: G1 v2 160·G2 8행은 장부에 `prompt_id`가 없고 27회차는 프롬프트 파일 시각(17:45:04Z < 18:03:51Z)으로 확인했다(27회차 X0). 값("모두 `9b5c5c292765`")은 간접 근거로 성립한다 — 168행 입력 토큰이 옛 G1보다 모두 +81(588/738/892, G2 892)로 한 프롬프트. 출처 표기를 "S2는 장부 `prompt_id`, G1 v2·G2는 파일 시각·입력 토큰"으로(P68).
- **E-N13.** Qwen 흐름 판본 혼재 표시가 결과 0절 `:7`에만 있고 5절 표 `:56`–`:57`·규칙 줄 `:59`·책 `01:60` "Qwen 0.36 → 0.047"에는 없다 — 27회차 E-D2 "결과 5절 Qwen 줄에 같은 표시" 절반 적용(P08). 등록 14절 "표시했다"는 0절 기준으로 맞음.
- **E-N14.** 결과 2절·5절의 호출당 토큰·원은 편 안 도착 66답 기준, "호출" 칸 72는 끝난 뒤 도착 포함 — 표 머리에 정의 한 줄 권함.
- **E-N15.** `cam3_verdict`·`ma3_verdict`의 `--n-snap`(기본 1,799)은 바꿀 수 있고, 판 요약이 없으면 요약 재현 검사를 건너뛴다 — 등록 "검증 1,799에서만"은 기본값으로만 지켜짐(E-N1과 같은 계열).
- **E-N16.** `prereg_cam3.md:8` "문턱(+0.02, 하한 > 0, 전이 ≥ −0.01, FULL p95 ≤ +10 %)은 설계 §12가 먼저 정했고" — 스펙 `:154`는 +0.02·−0.01·10 %와 "E-TC와 같은 틀"만 적는다(하한 > 0은 E-TC 틀에서 옴). 해석상 맞음.
- **E-N17.** 등록 7절은 판 폴더마다 `CODE_HASHES.txt`를 약속(있음: `ckpt/cam3/cam3_s1`, `ckpt/ma3/kv_s1`); 고정 사본 `code_cam3`·`code_ma3`에는 `CODE_VERSION`이 없다(약속 밖, 사본 해시는 X9로 확인).
- **E-N18.** `prereg_cam3.md:17` "로컬 전체 1,132 통과·20 건너뜀"은 개발 사본 상태다 — 등록 커밋 5c46056 트리면 1,132 통과·**18** 건너뜀(ma3 torch 시험 2개가 아직 없음; 47edadb 트리는 1,133·20).

## 8. 다음 순회 전에 할 일 (제안)
1. **D-1(기준선)**: 책 `04:61` 괄호 정정을 "19:07Z P0 생성 끝(폴더 행 파일은 12:19Z 파일럿 병합 19–41시드뿐 — 600편 행 조립 전)·P1 생성 중"으로, `ma1.md:15`·`02:103` P63 증상 칸도 같은 커밋에(근거 명령 기록). 정정 문장은 파드 명령 출력(파일 시각·시드 수)으로 확인한 뒤 쓴다(P68 — 이번이 두 번째 재발).
2. **D-2(기준선)**: 책 `04:16`(탐침 코드 커밋됨)·`:54`(E-MA1b 끝)·`:3`(확인 시각), 새 파일·경로(N90) — 06 줄 한 줄.
3. (선택, NOTE) N84(`06:12` 표시를 칸 안으로 — P68 규칙대로 `split('|')` 칸 수 검사), N85·N86(시각은 `date -u` 값), N87(책 03 §86 보충 행), N88(스펙 §17 출처·시뮬 초), N79(계획 PROBE 표 F0·15 s·지연 초기값), N92·N93, N94(**R2_TRAIN 생성 끝나면 `gen check`/병합을 다시 돌리고 행 수 대 편 수 확인 — 단계 B 전 필수**), E-N12·E-N13·E-N14 한 줄씩.
4. 29회차 대상은 47edadb 이후 HEAD, **연속 무결 0에서**. E-CAM3·E-MA3 결과가 커밋되면 기준 재사용 비트 동일·판정 재계산을 실험 절에서. Git Bash kubectl은 `MSYS_NO_PATHCONV=1`, 문서는 archive 사본에서 읽는다.
