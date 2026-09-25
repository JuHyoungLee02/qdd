# R7 객관 검증 순회 — 25회차 (cycle 25, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle24.md` §5 표·결론을 근거로 쓰지 않고 사전 등록 원문에서 대조표를 다시 만들었다. 행마다 **21–24회차와 다른 새 경계값으로 구성한 입력 → 실제 함수·CLI 출력** 또는 **파드 원자료 재계산**으로 확인했다). 작성 2026-09-25 18:25 UTC 무렵(로컬 시작 17:55:08 UTC, 파드 첫 명령 17:58:15 UTC, 파드 정리 끝 18:20:16 UTC, 마지막 파드 읽기 18:21:13 UTC). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`c767c3a`**(`c767c3ade0b621a0…`, 커밋 시각 2026-09-25 17:54:04 UTC, "R7 cycle 24 FAIL (DOC 1: handoff user-wait items stale after canon §84) — fix handoff §2.7/key decisions, logs, NOTE N17/N35/N37/N38"). `6e3fda6..c767c3a` = 커밋 8개(7dced6a 확인 실험 결과·정본 §83 보충, 06355f0 E-MA1 사전 등록 + 코드, a62164d 탐침 사전 등록, 5320dd2·075c505 user-log 87, ee1b000 G0 실패 기록 + `se2e_trace_model.py`, ed478e4 `CLAUDE.md` 규칙, c767c3a 24회차 보고서·정정), `git diff --stat` 22파일 +2,002/−7.
- **범위 나눔(메인 결정)**: **기준선 판정**(연속 무결 카운트에 들어감) = `harvest/`(런타임·평가·시뮬·분석·학습 파이프라인), `tools/`(새 실험 도구 제외), 시험, 정본, 아래 사전 등록, handoff·기록·결과 문서. **실험 코드 절**(따로 판정, 기준선 파일을 바꾸지 않는 한 카운트에 영향 없음) = E-MA1 파일(`harvest/train/se2e_trace.py`·`se2e_trace_model.py`, `tools/ma1/*`, 그 시험 4개, `prereg_ma1.md`, `results/ma1.md`·`ma1_g0_sheet.jpg`)과 탐침 사전 등록 `prereg_astra_motion.md`. 확인 결과: `6e3fda6..c767c3a`에서 문서가 아닌 변경은 **모두 새 파일 추가**(`--name-status` A만, `check25` H5), `PROMPT_FILES`·`PROMPT_FILES_B`(`stageb_data.py`·`stageb_model.py`) 블롭 6e3fda6 = c767c3a(H4), 기존 사전 등록 10개 블롭 동일, 기준선 모듈 중 새 모듈을 import하는 곳 0(S6, `tools/ma1/g0.py`·`g0_point.py`만).
- 사본: `git -c core.autocrlf=false archive c767c3a`(해시 고정)를 Python tarfile로 `D:\tools\scratch_qdd\r7c25\repo`에 풀었다(**525파일** = 24회차 510 + 15). 파드 사본 = 같은 archive(`/data/harvest/tmp/r7c25/code`, 526파일 = + JSON `CODE_VERSION` `c767c3ad…`, dirty false); 파드 산출 `meta.git.commit` = `c767c3ade0b6…`.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle24.md`, 정본 `00-interfaces.md` §1–§84(끝의 §84 보충 1·2와 §83 보충까지; 뒤 절 우선; [사용자] 제목 절은 그대로), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`·`prereg_se2e.md`·`prereg_se2e_diag.md`·`prereg_se2e_temporal.md`·`prereg_se2e_motion_confirm.md`·`M4-overlap-commit.md`(실험 절: + `prereg_ma1.md`·`prereg_astra_motion.md`).
- 분류(24회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·같은 문서의 뒤 결과와 다르고 정정 표시가 없는 것, 사전 등록이 열어 둔 값을 코드가 정해 쓰는데 기록이 없는 것. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 승인된 설계(스펙)·연구 문서의 제안은 지금 코드·결정을 틀리게 말하지 않는 한 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c25`(C: 쓰기 없음; 하네스 작업 출력 파일만). 스크립트는 Write 도구로 쓰고 경로로 실행(스크립트 몇 개는 Edit·`sed`로 고친 뒤 재실행 — N44). **절차상 어긋남(내 쪽) 1건**: 18:00 UTC 무렵 로컬에서 부동소수 산술 확인에 인라인 `python -c`를 한 번 썼다(저장소·파드 영향 없음, N44). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c25`, `source /data/harvest/env.sh`, 업로드 = `tar -cf - | kubectl exec -i … tar -xf -`, **모든 kubectl에 `MSYS_NO_PATHCONV=1`**(24회차 N41 재발 없음, 끝에 `/C:` 부재 확인), 업로드한 파드 스크립트 CR 바이트 0(매번 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`--inst-prefix r7c25`, `IR_INST` `r7c25_standard`, `IR_ROOT=cyclo`; 같은 GPU의 R2_TRAIN Isaac 워커 4개와 탐침의 `astram_s2_qwen14` Isaac 실행은 건드리지 않음), GPU 2(E-MA1b)·3(탐침 Qwen 서버)에는 아무것도 올리지 않음(가드 12·13은 워커 전에 거부). CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`, 한 번에 한 묶음(CPU 시험 → 가드·평가·데이터·확인 실험·G0 재계산 → Isaac → 정리). 시드 DEV·POOL만. 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. **E-MA1b 예측 파일은 열지 않았다**(`/data/harvest/logs/ma1b`·`ckpt/ma1b`·`tmp/ma1b`는 이름·시각 목록만). 확인 실험 예측·판정 파일은 결과가 커밋된 뒤라 값을 읽었다(메인 허용). 탐침 비용 장부는 시각·모델·effort·비용 필드만 읽었다(프롬프트·답 안 읽음).

## 판정 (기준선): **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 1 |
| SCOPED | 21 |
| NOTE | 45 |

## 판정 (실험 코드 절, 카운트와 별개): **FAIL — 코드 결함 0, DOC 3**

코드·시험·기준선 사전 등록은 6e3fda6와 바이트가 같고(추가 파일만) 모든 행동 확인이 통과했다: 로컬 **1046 passed / 16 skipped**(Git Bash, 160.3 s), 파드 CPU **1168 passed / 4 skipped**(141.2 s), LeRobot 6 passed; 가드 **28건** 모두 rc ≠ 0(21–24회차와 다른 값; 14번은 내 설계 실수로 argparse에서 걸려 28번 `--m4-lead-max=-inf`로 다시 확인 — N44); R2 DEV `validate_episode` **36/36** + 21–24회차와 **다른 종류**의 음성 대조 4종(검증 목표 제거, 프레임 번호 중복, stageb 행 삭제, k0 머리 이미지를 손목 크기 JPEG로 — 모두 검출, 무수정 사본 오류 0); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 모두 완료; 새 시드 **DEV 20**에서 같은 Isaac 워커 C5 → C5' 행동 **1,596개 비트 동일**; 로컬 구성 시험 `check25.py` **89/89**; `prereg_hash.py --check` OK; 제어 문자 전수 0·변경 문서 12개 표 칸 수 불일치 0. **확인 실험 결과 문서의 모든 수치가 파드 판정 파일과 같다**: 등록 판정 스크립트(`fa7299062cc5e1d1`)를 c767c3a 사본으로 네 예측 파일에 다시 돌린 출력이 `verdict_full.json`·`verdict_300.json`과 **바이트 동일**, 내 독립 재계산도 합동 효과 0.032240·전이 0.029607로 같다. **E-MA1 G0는 원자료에서 재현됐다**: 등록 코드로 다시 판정한 결과가 `g0.json`과 같고(fail, 유효 119), 120프레임 선택·손끝 FK·명목 투영이 `se2e_c1`에서 오차 0으로 재현되며, 등록 뒤(17:33:19Z 첫 산출 > 커밋 17:32:42Z) 실행·학습 산출물 없음.

**DOC 1건(기준선)**: 정본 §82 보충(`00-interfaces.md:732`)이 여전히 "실행 자체는 여전히 구현 완료 뒤 **사용자 승인**"이라고 현재 규칙으로 적는데, 대상 안의 뒤 사용자 결정 user-log 87(075c505·5320dd2, "나에게 승인은 안받아도되지만 자체적으로 저걸 해보라는거지")과 그것을 올린 `CLAUDE.md:33`(ed478e4, "유익성 판단은 Claude가 하고 사용자 승인은 받지 않는다")·handoff `:88`(c767c3a, "(2) 유료 실행은 user-log 87로 사용자 승인 대신 Claude 자체 검사")는 반대로 말한다. 정본에는 user-log 87을 기록한 절도 표시도 없다(`grep 'user-log 87'` 0곳). handoff는 "정본 §1부터 마지막 절까지가 현재 판"이라 적으므로 두 문서가 충돌한다(D-1). **연속 무결 0 유지.**

---

## 1. DEFECT

없음.

(검토한 후보와 판단: ① `stats.CMP_EPS`는 **절대** 1e-12(`stats.py:12–29`)인데 정본 §77 보충 2(`:683`)는 "(상대)"라 적는다 — 통계 함수로 비교하는 등록 문턱은 모두 |t| ≤ 1.25라 max(1, |t|) 상대 비교와 차이 ≤ 2.5e-13이고 정본 §74(`:638`)는 함수 이름·값만 정했다 → NOTE N42. ② `ma1_verdict.py`·`g0.py`의 입력 검사는 assert·argparse 수준(N3와 같은 성격)이지만 네 칸 검증 키가 다르면 거부한다(W8) → 실험 절 NOTE.)

## 2. DOC

- **D-1. `docs/design/00-interfaces.md:732`(§82 보충) — "실행 자체는 여전히 구현 완료 뒤 사용자 승인"이 user-log 87 이후에도 현재 규칙으로 남아 있다.** 대상 커밋 트리에서: user-log 87(`docs/user-log.md:372–379`, 17:41–17:45 UTC) "고 나에게 승인은 안받아도되지만 자체적으로 저걸 해보라는거지" → 조치 "유료 실험의 유익성 판단은 Claude가 한다(승인 불필요)"; `CLAUDE.md:33`(ed478e4) "모든 실험(유료·GPU 모두)은 매번 자체 검사 … 유익성 판단은 Claude가 하고 사용자 승인은 받지 않는다"; handoff `:88`(c767c3a) "(2) 유료 실행은 user-log 87로 사용자 승인 대신 Claude 자체 검사 … **지금 사용자 대기 항목 없음**". 정본은 §84 보충 2(user-log 86)가 마지막 [사용자 결정]이고 user-log 87을 옮긴 절이 없으며 `:732`에 정정 표시도 없다. handoff 머리(`:5`)가 "정본 §1부터 마지막 절까지가 현재 판"이라 하므로, 정본만 읽는 다음 세션은 유료 실행에 사용자 승인을 다시 구하게 된다(24회차 D-1의 반대 방향: 그때는 정본이 앞서고 handoff가 낡았다). 사용자 결정이 정본 문장과 반대이고 표시가 없으므로 DOC. **고칠 것**: 정본에 [사용자 결정] 절 하나(예: §85 "유료·GPU 실험은 Claude 자체 검사로 실행 — 사용자 승인 불필요, 시작 전·도중·끝 검사, 비용 한도 약 10만 원·실험별 상한은 그대로", user-log 87)를 더하고 `:732` 끝에 "[→ §85: 사용자 승인 대신 자체 검사(user-log 87)]" 표시. 재발 방지: user-log에 [사용자 결정]을 적는 커밋에서 정본 절 추가 여부를 같은 커밋에서 확인(24회차 교훈의 반대 방향).

(검토했지만 DOC로 올리지 않은 후보: handoff `:84` 핵심 결정의 "정본 §84(2026-09-25 17:54 UTC 반영) … (E-MA1: G0 실패 → E-MA1b 3D 궤적 보조 손실 …)"은 E-MA1b를 "정본 §84 반영" 표지 아래 적지만 정본에는 G0 실패·E-MA1b가 없고 E-MA1b 사전 등록은 대상 2초 뒤(ded38d7)에 커밋됐다 — 계획의 기록이고 지금 코드·결정을 틀리게 말하지 않는다 → N41. 탐침 사전 등록이 user-log 87 재범위(15,000원)를 반영하지 않은 것 → 실험 절 E-D2(handoff `:88`의 15,000원은 user-log 87과 같아 맞다). `se2e_diag.md`의 중앙 차분 한계 줄 없음 → N43.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 GPU 0·1 R2_TRAIN Isaac 워커 4개 진행 중(`gen gen --seeds 10000-10599 --confirm-train`, 읽기만); 확인 인자 없는 `gen gen --seeds 44444` rc 1(가드 19).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — c767c3a에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. **정본 §82 구현 및 §84 결합 설계 구현**(보충 2 흐름 호출 = 동시 1개, 두 층 M4, 카메라 3대·덧그림, falsify 먼저 평가 + 재사용 한 번 상한) — §84 "런타임 코드 구현은 R7 E2E 준비 기준점(연속 무결 2회) 뒤". 지금 코드: `CADENCES` = K0–K4, "K5"·"stream"·"K2 " 거부(`check25` C3), 파드 `closed --hb-mode K5`·`serial` → 워커 전 거부(가드 26·27), `RuntimeConfig()` = ("K2", 5.0)(C5), Astra 요청 이미지 1장(S3, 파드 Astra 4행 이미지 수 1), `harvest/`에 `falsify` 0곳이고 `trace5`·`eetrace`는 옵트인 E-MA1 파일 둘뿐(S5), 파드 DEV 20 Astra 겹침 0(hb 5.0 → 8.0, sub 8.59 → 11.59).
- S19. **정본 §83 런타임 적용**(새 직렬화 판본·런타임 속도 구간화·보정/카나리 재생성) — `harvest/serialize`에 움직임 줄 없음(`check25` D3), 파드 결정 호출 요청 96/96 `motion:` 없음.
- S20. **대상 뒤 커밋**: 검토 중 HEAD가 **745af38**로 움직였다 — ded38d7(E-MA1b 사전 등록 + 코드: 새 `se2e_a3d.py`·`build_a3d.py`·`ma1b_verdict.py`, **기준선 파일 `harvest/train/stageb_train.py` +62/−7 수정**, `se2e_trace_model.py` +73/−34 수정), 7bb9035(결합 구현 계획), 13f3495(user-log 88 + `CLAUDE.md`), 745af38(논문). 26회차가 행동으로 볼 것(N40).
- S21. **탐침 E-Astra-motion 실행·결과**: 대상 트리에는 사전 등록만 있고 코드(`harvest/astra_motion/`, `tests/astra_motion/`)는 미추적, 결과 문서 없음 — 검토 대상 아님(등록 문서 자체는 실험 절에서 검토).

(24회차 S20 "확인 실험 결과"는 대상에 들어와 행 147–149에서 값까지 확인했으므로 SCOPED에서 뺐고, S21 "E-MA1"은 실험 절로 옮겼다.)

## 4. NOTE
- N1. (그대로) `stageb_train predict`·`evalck`는 체크포인트 `prompt_config`를 자기 옵션과 대조하지 않는다.
- N2. (그대로) `cli_label.replay_max`의 NaN 순서 의존. 읽는 쪽 `replay_bit_identical` 새 경우: `0.0`·`1e-300*0` → 신뢰, `"nan"`·`1e-320`·`inf`·`{}`·필드 없음 → 불신(D1).
- N3. (그대로 + 해소 일부) `temporal_verdict.py`·`motion_confirm_verdict.py` 입력 검사는 assert·argparse 수준. 확인 실험 결과 문서는 §2 표 머리에 "5,397항목"을 적었고 파드 재계산에서 네 판 항목·스냅샷 수가 같다(5,397/1,799, 900/300).
- N4. (그대로) Astra 시간 초과 뒤 늦게 온 답 처리 — 구현 때 정본 한 줄 권함.
- N5–N6. (그대로) `se2e_diag.md:131`·`:13`.
- N7. (그대로) 연구 문서 `astra_role_2026-09-25.md:239`·`:515`·`:517` 표시 권함.
- N8. (그대로) `CLAUDE.md:32` 위치; `CLAUDE.md:48`·정본 `:11`의 하위 VLM 계단식 호출은 §84 보충 2와 대상이 다름.
- N9. (그대로) `steering_representation_2026-09-25.md:33`·`:81` 표시 렌더 누락.
- N10. (그대로, 재현) `e05`는 `--out` 폴더를 거부 전에 만든다 — 가드 25(`e05 --split pool --seeds 2044`, P0 → "no episode selected" rc 1)가 빈 `g25/`를 남김.
- N11. (그대로) 카나리 `--force` 같은 날 재실행.
- N12. (해소 기록) **24회차 정정이 실제 diff와 맞다**: handoff `:88` 끝 "[→ 갱신 17:54 UTC, R7 24회차 D-1: … (1) falsify 먼저 평가 결정 … (3) 결합 설계 승인; (2) … **지금 사용자 대기 항목 없음**]", `:84` 핵심 결정에 "정본 §84(17:54 UTC 반영)" 토막, `:3` 17:54 UTC, §2.8 `:119`(확인 실험)·`:120`(24회차), draft-log `:467`–`:471`(확인 실험·§84 줄(N38)·E-MA1·탐침·24회차), direction-log `:71`, 정본 `:753` N35 표시·`:755` N37 표시, 스펙 `:1` 제목 "(승인됨 …)"·`:3` 상태 "승인됨(정본 §84), 구현 전"(N17) — 모두 보고서와 **같은 커밋** c767c3a(`git show --stat`: 보고서 + handoff + draft-log + direction-log + 정본 + 스펙).
- N13. (그대로) `draft-log.md:462` "커밋 안 함" 관용 표기.
- N14–N16. (그대로) `prereg_se2e_temporal.md` §7 해시, `e_m4b_meas.md` 원문 복사, 계획 `:12`·`:26` "Astra 하트비트".
- N17. (대부분 해소) 스펙 `:1`·`:3` 고침. 남은 것: `:5` "미정: 손끝 목표의 공간 표현(E-Astra-motion 탐침: P-pc / P-plane / P-tri / S)"(user-log 83으로 P 변형 제거)과 `:7` 머리 개정 문단의 "1 Hz 계단식 호출 … 유지"에 표시 없음 — `:17` "읽는 법"이 덮으므로 NOTE.
- N18. (그대로) §82 `:726` 강등 줄과 흐름 호출의 관계 한 구절 권함.
- N19–N21. (그대로).
- N22. (해소 유지).
- N23. (그대로) 등록 §5 "무수정" 해시 3개 = CRLF 형태(`check25` H3).
- N24. (해소) 등록 §3 "(none)끼리·(motion)끼리 시드 간 정확도 차"를 결과 문서 §3이 보고(none +0.0050·motion +0.0009 — 파드 값 0.6774−0.6724, 0.7076−0.7067과 같음).
- N26. (그대로) 확인 실험 등록 고정 시점.
- N28–N29. (그대로) `astra_effort` 기록용; 부트스트랩 한 흐름.
- N30. (그대로) 로컬 시험은 Git Bash에서.
- N31. 시험 수: 로컬 **1046 passed / 16 skipped**(160.3 s, 17:57:59–18:00:40Z; 24회차 1014/15 대비 E-MA1 시험 +32 통과, `test_se2e_trace_model.py`는 torch 없어 건너뜀 +1), 파드 CPU **1168 passed / 4 skipped**(141.2 s, 18:01:23–18:03:48Z; +38, torch 쪽 trace 모델 시험 포함), 경고 1개(`test_stagea_loss_torch.py:42` 기존 UserWarning), LeRobot 6 passed(28.4 s). 파드 CUDA 시험·`test_determinism_isaac.py`는 돌리지 않았다.
- N32. 단계 B 소형 CPU 스모크(18:13–18:14Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–24회차와 같은 값 — 결정적), 저장·재적재 평가 동일(`eval_equal` 참), expert p50 0.042 s·전체 p50 0.107 s(CPU, 참고), 맥락 토큰 454.
- N33. DEV 20 판: 행동 1,596·15.96 s·호출 48, `last_step` {none 1, OK 34, DEVIATE 8, LAG 5}, 확정 비율 0.902, 결정 3.009/s, rtf 0.392, Astra 2(hb 5.0 → 8.0, sub 8.59 → 11.59). 파일명 `dev20-P0-standard-e0`.
- N34. (그대로) 가드 12·13 거부 문구 "(GPU 2 never renders)"는 GPU 3을 이름으로 들지 않는다.
- N35. (해소) 정본 `:753` "[→ 대체 … 보충 2]" 표시.
- N36. (그대로) 스펙 §15 비용 추정 산술(대체된 내용).
- N37. (해소) 정본 `:755` "(… Claude 해석 …)" 표시.
- N38. (부분 해소) draft-log `:468` §84 줄 추가. direction-log `:69`–`:71`(22–24회차) 행은 여전히 앞 행의 여섯 질문 형식이 아니다 — 기록 문서라 NOTE.
- N39. (그대로) MolmoAct 연구 문서의 코드 서술 맞음.
- N40. 검토 중 HEAD가 745af38로 움직였다(S20). 26회차 대상은 **새 코드가 기준선 파일 `stageb_train.py`를 고친 ded38d7 이후**이므로 기준선 판정 범위에 새 코드가 들어간다: `PROMPT_FILES_B` 해시 불변, 옵션 기본값 = 기존 동작(옵션 끔 표본 = 기준 로더 표본), E-MA1b 판정 스크립트 경계값, 사전 등록 시각 < 첫 A3d 실행, 탐침 등록 개정의 커밋 시각 < 재개된 유료 호출(E-D2)을 볼 것.
- N41. handoff `:84`가 "정본 §84(17:54 UTC 반영)" 표지 아래 "(E-MA1: G0 실패 → E-MA1b 3D 궤적 보조 손실, 이미지 궤적·덧그림은 R2 뒤)"를 적는데, 정본에는 G0 실패 기록·E-MA1b가 없다(§83 보충처럼 결과 한 줄을 정본에 두는 관례와 다름). E-MA1b 등록은 대상 2초 뒤(ded38d7 17:54:06Z). 정본 §84에 "보충 3 — E-MA1 G0 실패(결과 `results/ma1.md`) → R2 전까지 카메라 없는 E-MA1b로(Claude 결정, user-log 87)" 한 줄 권함.
- N42. `stats.CMP_EPS`(절대 1e-12, `stats.py:12–29`) 대 정본 §77 보충 2 `:683` "(상대)" 표기 — 통계 함수가 쓰는 등록 문턱은 |t| ≤ 1.25라 실질 차이 ≤ 2.5e-13; 판정 스크립트들(`se2e_verdict`·`motion_confirm_verdict`·`ma1_verdict`·`se2e_trace._le`)은 max(1, |t|) 상대. 표현 통일 권함.
- N43. 확인 실험 결과 문서 `se2e_motion_confirm.md:58`이 "이전 S-E2E 결과 문서의 행동 지표는 중앙 차분 고유감각으로 잰 값 — 한 줄 적는 일은 메인 몫"이라 남겼는데 `se2e_train.md:56`·`se2e_temporal.md:81`에는 있고 `se2e_diag.md`에는 없다.
- N44. (절차, 내 쪽) ① 인라인 `python -c` 1회(18:00Z 무렵, 부동소수 산술 확인만, 로컬). ② 가드 14 `--m4-lead-max -inf`는 argparse가 `-inf`를 옵션으로 읽어 rc 2("expected one argument")로 끝나 검증 경로를 거치지 않았다 → 가드 28 `--m4-lead-max=-inf` → "refused before any worker" rc 1. ③ `check25.py` 자체 점검으로 다시 설계한 항목 7개(user-log 87·CLAUDE.md 규칙): E1(첫 판이 t = 1000에서 상대 eps를 가정 — 정본 `:638`은 절대값, 등록 문턱 범위 |t| ≤ 1로 재설계), T3(요 축 기대식 오류: 피치 뒤 요 → (cos p cos y, sin y, −sin p cos y)), T7(aux 입력을 None으로 줌), T12(t = 12의 상대 eps 1.2e-11을 잊음), T15(Molmo2 답 형식에 점 번호가 있음을 파드 원답으로 확인), T16(임의 "< 1 px" 대신 최소제곱 대비 강건성), T17(보정 반 9장 구성 오류) — 모두 내 입력·기대의 잘못이고 코드 쪽은 등록 정의대로였다.
- N45. 파드 상태 목록은 `TZ=UTC`로 찍었다. 내 Isaac 창(18:14:36–18:19:08Z) 안에 생긴 `ir/kitcache/cyclo-astram_s2_qwen14`(18:15:33Z)는 탐침(PID 574205, `IR_INST=astram_s2_qwen14`, `TMPDIR=/data/harvest/code_astra_motion/tmp`) 것이라 남겼다; `tmp/carb.8jQC9b`(18:14:38Z)·`tmp/tmpewbajtza`(18:15:00Z, +24 s 패턴)는 내 워커(`TMPDIR=/data/harvest/tmp`, `closed.py:192–194`) 것으로 판별해 지웠다.

---

## 5. 사전 등록 대조표 (원문에서 새로 만듦, 행마다 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check25` H1), 파드 산출 `meta.prereg.check` = "OK"(closed). 원문 인용 줄은 `refcheck25.py`로 다시 읽어 확인(24회차와 같은 줄; 사전 등록 10개 블롭 6e3fda6 = c767c3a). 코드 줄은 c767c3a 기준(6e3fda6와 블롭 동일). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c25\check25.py`(A–H·S·V·R·T·W·K, 89/89), `ctrlscan25.py`, `refcheck25.py`; **파드** = §6(`pod_cpu25.sh`, `pod_eval25.sh`, `data25.py`, `conf25.py`, `ma1_25.py`, `pod_isaac25.sh`·`closed25.py`, `guard28.sh`·`cost25.py`, `who25.sh`, `clean25.sh`). "시험 묶음" = 해당 구현을 부르는 저장소 시험이 로컬 1046·파드 1168 묶음에서 통과. 경계값은 21–24회차와 다르게 새로 골랐다.

| # | 사전 등록 값·절차 (출처 file:line) | 구현 (file:line) | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 로컬 A1 새 24값(4·19·25/34·495·504·533·545/554·1004·1088·1146/1153·1260·1303·1326/1333·1996·2003·2116/2123·9996·60003·−7) 기대대로, A2 `cal`은 env 없음·`test_p5`·`test` 거부/`cal` 통과, `test`에 `test_p5` 거부, A3 "DEV"·"pool "·"Cal"·"testp5"·"r2_eval"·"val" 거부, A4 [4, 25, 34]·[2116, 2123] 통째 거부, A6 R2 가드 12경우(4·25 무확인 허용, 34·60005·2063·533·1088·9995·1326 거부, 10004·59977 확인 시만), A7 10060·59940·30000 eval, 10061·59941·44445 fit; 파드 가드 28건 rc ≠ 0(§6.4) | 일치 |
| 2–4 | POOL 120 × 10·경계 과표집, `ambiguous` 띠, 분할 = 에피소드 (E :121-122) | `sim/snapshot.py`, `stagea_data.split_of`, `calib.halves` | 코드 무변경, 시험 묶음; 파드 `CALIB_DONE` | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 20** C5·C5' 성공(15.96 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **파드 DEV 20 C5·C5' 결정 호출 96행**: 요청 blob 해시 = `request_sha256` 96/96, 이미지 해시가 요청 본문에 96/96, 응답 blob 해시 96/96, `probs` 질문 = `answers`·합 1·[0,1] 96/96, `canary_id`·`question_id@vN` 96/96; Astra 4행 요청 해시·머리 JPEG 해시·effort low(행·요청 본문)·600·`output_text` 4/4 | 일치 |
| **7** | 95 % 구간 = 군집 부트스트랩 10,000 (E :130, EVAL :184) | `analysis/stats.py` | 로컬 E3 일반 경로 = 군집 합 경로(새 41군집·seed 21), **E4 군집 안 행 1배 대 3배 → 구간 동일**; 파드 `meta.bootstrap` 10000·seed 0·percentile | 일치 |
| 8 | 같은 시드 짝 비교 (E :130) | `closed.aggregate` | 파드 C5 대 C5' 같은 워커 | 일치 |
| **9–12** | 판정 2 Holm, 카나리 Holm, 판정 절 해시 (E :131, :265, :139, :133) | `stats.holm`, `eval/common.py` | 로컬 E5 **여섯 가설 정확한 문턱**(0.05/6, 0.01, 0.0125, 0.05/3, 0.025, 0.05) 모두 기각, 둘째 0.0101 > 0.01 → 첫째만(입력 순서 뒤집음); `meta.prereg` OK | 일치 |
| **13, 85** | 카나리 기준일 = 같은 세트 × 같은 `question_id@vN` 첫날 (E :136-140, §79 D2) | `eval/canary.py` | 로컬 G1: 다른 세트의 앞선 실행 무시, 부분 집합 맵 = 자기 사슬, 키 순서 무관(첫 = q2), 새 판본 = 자기 사슬, 다른 세트에 없는 맵 → None | 일치(N11) |
| 14–17 | 모델 식별 필드, E0.5 표·재시험·K = 3 (E :139, :236-238) | `Calibration.load`, `e05.py` | 시험 묶음; 파드 `e05 --data jsel_dev/P2 --split dev --episodes 4` → `E05_DONE` | 일치 |
| **18** | γ 2/3 (E :240, M4 :276) | `m4.share_at_least` | 로컬 B1 12/18·34/51·667/1000·7/10·4000/6000 참, 33/50·666/1000·1/2 거짓 | 일치 |
| 19–20 | `C_flip` 두 식, A0–A4 (E :242, :246) | `e05.py` | 시험 묶음 | 정본 기록 / 일치 |
| **21–28** | 판정 1–10 경계 (E :256-265) | `stats.at_least/below` | 로컬 E1(절대 1e-12, N42·N44): at_least(0.1+0.2, 0.3) 참·below(0.3, 0.1+0.2) 거짓, at_least(0.75−1.1e-12, 0.75) 거짓·below 참, 0.75−0.9e-12 참, at_most(0.03+0.9e-12) 참·above 거짓; 파드 `E05_DONE` 2회 | 일치 |
| 29–30 | FLIP_TH α 0.01, 같은 시각 뒤집힘 (E :253, :487; M4 :285) | `e05.py` | 시험 묶음 | 일치 |
| 31–35 | d_p95·분당 400·반분, ECE 15 동일 질량 (E :320) | `M4Params`, `calibration.ece_mass` | 로컬 E6(450예측 → 0.2766 ∈ [0, 1]) | 정본 기록 / 일치 |
| **36** | J5 q̂ = ⌈(n+1)(1−α)⌉번째 (E :330) | `calibration.conformal_qhat` | 로컬 E2(유리수 기준값): 39·α 0.1 → 36, 29·0.05 → 29, 13·0.1 → 13, 12·0.1 → 12, 10·0.1 → 10, 199·α 0.005 → 199, 198·0.005 → inf | 일치 |
| 37–43 | log p 자름·온도·원 확률·`ambiguous` ECE 제외 (E :333-346) | `calibration.py` | 시험 묶음; 파드 `calib --heldout jsel_dev/P0 --episodes 4` → `CALIB_DONE` | 일치 |
| 44 | E1 판정 2–6 | 없음 | §73 N5 | SCOPED S10 |
| **45** | N_max = ⌈d̂/T_c⌉+1, d̂ = 최근 50회 p95 (M4 :258, :263) | `m4.CommitLedger` | 로컬 B9: d̂ 1.32 → 5(정확히 4.0), 1.3201 → 6; 창 50: 1..80 ms → 78 ms(31..80의 48번째), 1..40 ms(n 40) → 38 ms | 일치 |
| 46–50 | γ·W·τ, conformal (b) 경계 | `m4.py`, 확인 헤드 보정 | 시험 묶음; 기본 미보정 | 일치 / SCOPED S5 |
| **51** | STALE_MAX 1.5 s (E :487) | `m4.older_than` | 로컬 B3 **400 Hz** 틱 1,500곳 모두 600틱 유지·601틱 버림, B4 +9.9e-10 유지·+1.02e-9 버림 | 일치 |
| 52–53 | C0–C6 설정 (M4 :329-345) | `conditions.py` | 파드 `--conditions "C5,C9"` → "refused before any worker"(가드 16) | 일치 |
| **54** | C5 = §4.2 전체, C5' = (b) 범주 뺌 (M4 :155, :232, :340-342; §77 보충 (3)) | `core.b_line` | **파드 Isaac DEV 20**: C5 `last_step` {none 1, OK 34, DEVIATE 8, LAG 5}, C5' none 48/48, 요청 본문 마지막 `last_step:` 줄 = 행 값 96/96 | 일치 |
| 55 | H 1과 3 (M4 :188-189) | `m4.early_ask_steps` | 로컬 B8 H 3; 파드 `meta.m4_H` 3·`m4_lead_max` 1.0 | 일치 |
| **56–58** | n_LA 2·조기 호출·H = 1 창 (§75) | `m4.py` | 로컬 B5 다섯 창 = 정확한 유리수 창: (0.33, 0.66, 0.33, 1.65) → [3..6](양 끝 0.99·1.98 경계), (2.0, 0.31, 0.33, 0.64) → [7, 8], (0.05, 0.6, 0.33, 0.1) → [2](창 빔), (0.99, 0, 0.33, 0) → [3](한 점), (1.2, 0.12, 0.33, 0.78) → [4..6] | 일치 |
| 59 | 경계 직후 W 2 등 | 없음 | §73 D5 | SCOPED S9 |
| **60** | 라벨 규칙: 적격 ≥ 0.90, 차 ≤ 0.02 단순한 쪽 (labeler :11-12) | `sim/labeler.select_rule` | 로컬 E7: 0.63 − 0.61(부동소수 0.020000000000000018) → plan, 0.6300001 → time, 0.91 단독 → plan, 0.8999999999 단독 → None | 일치 |
| 61–62 | RD 재표집·주 RD (EVAL :182-184) | `rd.py` | 파드 `rd --variants standard,dr/P0 --episodes 2` → `RD_DONE` | 일치 |
| 63–65 | H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §71 보충 / §72 / §74 보충 | SCOPED S1·S11 / 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 로컬 B8b `M4Params(lead_max = −inf / −1e-300 / −0.0)` 모두 거부; 파드 `--m4-lead-max 0` → 워커 전 거부(가드 15), `--m4-lead-max=-inf` → 거부(가드 28; 14는 N44) | 일치 |
| 68–70 | E0 판정 4, E-M4 판정 7, FROZEN (M4 :150) | `latency.py` / 없음 / `m4.py` | 시험 묶음 | 일치 / SCOPED S12 / 정본 기록 |
| 71–79, 86–88, 90–94 | 카나리 표류·재사용, 응답 기록, (b) 범주 줄, 결정 호출 행, FLIP_TH 분위 (E :139, :347; M4 :232, :287; §77, §79) | `closed`, `canary`, `core`, `e05` | 행 6·54; 시험 묶음 | 일치 / SCOPED S13·S6 |
| **80–84** | `last_step` 학습 자료 값 (§77 (iv), 보충 (1)) | `serialize.with_last_step` | 로컬 D2 닫힌 집합, "ok"·"DEVIATE\n"·"" 거부, "LAG"·"OK" 수용 | 일치 |
| 95–97, 105, 115–117, 119 | S-E2E 설정·판정 (`prereg_se2e.md`) | `tools/se2e/se2e_verdict.py` | 코드 무변경; 시험 묶음 | 일치 |
| **98** | 라벨 복원 기준(비트 동일, §78 (1)) | `stagea_data.replay_bit_identical` | 로컬 D1 새 7경우(N2) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **파드 Isaac 한 워커 C5 → C5'(DEV 20, 18:14:36–18:19:08Z)**: 행동 **1,596개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 48·Astra 2 같은 수·같은 시각, `code_sha` `b92feadc5810c8a7` | 일치(S16) |
| 100, 118, 132 | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1, §81 N3) | `eval/common.load_truth` | 파드 `e05 --split pool --seeds 2024,2079,2101 --truth outcome:plan` → `E05_DONE` | 일치 |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | GPU 0·1 R2_TRAIN 워커 4개 진행 중 | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, `determinism` 시드 검사가 `--out` 앞 (§79 N5, §80 N3) | `common.load_episodes`, `sim/determinism.py` | 가드 22(`fresh --seed 30`)·23(`history --seeds 1400`) → "only DEV 0-29 and POOL" rc 1·폴더 없음; 24(`canary build-set --seeds 1333-1334`)·25(`e05 --split pool --seeds 2044`, P0) → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 기본 (§79) | `closed.worker_cmd`, `e05.py` | 내 워커가 이 명령으로 `CLOSED_DONE`; `--isaac-gpu 2`·`3` rc 1(가드 12·13) | 일치(N34) |
| 106–114, 121–131, 133–136 | S-E2E 진단·E-TC (`prereg_se2e_diag.md`, `prereg_se2e_temporal.md`) | `se2e_temporal.py`, `temporal_verdict.py` | `temporal_verdict.py` `992d3e20…` = 등록(H2); 로컬 F1 Δ 0.3 s: 30 Hz k 9·40 → 0·31, 10 Hz k 3·25 → 0·22; **F2a 네 관절 1-2-2-4 분할 노름**(하한×0.99999999 still·×1.00000001 slow·상한×0.99999999 slow·×1.00000001 fast·0 still), F2b 그리퍼 1.0000001배 opening/closing·0.9999999배·정확히 −t still, F3 15 Hz [2, 2, 3, 1, 1, 5] → [0, 0, 15, −30, 0, 60], F4 40,000표본 0.3007·시드별 난수 | 일치 |
| 137 | Astra 주기 = 하트비트(응답 + 5 s)·경계·사건, in-flight 1, 15 s 재송신, low·600 (§45, §82 보충 2) | `runtime/astra_hb.py`, `core.py` | 로컬 C1 송신 0.7 뒤 1.0 없음, 응답 3.2 뒤 8.1999 없음·8.2 hb, C2 송신 8.2 → 23.2 유지·23.2000001 초과, C4; **파드 판 Astra hb 5.0 → 8.0, sub 8.59 → 11.59, 겹침 0** | 일치(N4) |
| 138 | LeRobot v2.1 내보내기 (§63, §66) | `datagen/lerobot_export.py` | **파드 새 2편**(dr/bottle_tray ep1 = `valid_for_training` 거짓 → 건너뜀, standard/mug_marker ep2 참): 1편·267프레임, `verify` 오류 0·PSNR 최소 39.14 dB·lerobot 0.3.3 적재 267프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참; LeRobot 시험 6 passed | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | 파드 전 편 **36/36 오류 없음**(6폴더 × 6), 메타 불일치 0; **새 종류 음성 대조 4종**(dr/mug_marker ep5, 288프레임): 무수정 사본 오류 0, k150 `verify.prev_step` 제거 → "verification target missing at [150]", 프레임 144의 k를 143으로 → "frame indices not contiguous from 0"(+ 시각 격자 3.00e-02 s), stageb 행 하나 삭제 → "stageb rows are not one per non-terminal frame", k0 머리 경로를 손목 JPEG로 → "k0 cam_head: size (424, 240) != native (672, 376)" | 일치 |
| **140–141** | 정본 §82 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 로컬 C3·C5·D3, 파드 가드 26·27, 요청 96/96 `motion:` 없음 | SCOPED S18·S19 |
| **142** | 속도 누수 수정: v[k] = (x[k] − x[k−1]) × 10 Hz, v[0] = 0 (`prereg_se2e_motion_confirm.md:10`) | `se2e_data.py:134-140` | 로컬 V1 53×16 무작위 보행 비트 동일, V2 `backward_velocity`와 비트 동일, V3 k = 0·11·40·51 뒤를 sin 변환해도 0..k 불변, V4 2프레임, V6 30 Hz = 3배, V7 `episode_rows`(RB1 16차원, 보폭 4) 행마다 자기 팔 후방 차분·k = 0 행 0; H2 `se2e_data.py` = 등록 `c6adc96f…`(24회차 뒤 무변경) | 일치 |
| **143** | 재변환: qd·grip[1] 외 모든 필드 같지 않으면 멈춤 (`:11`) | `tools/se2e_convert.py` | 로컬 R1 수용, **R2 행의 다른 최상위 필드 26개 전부(각각 다른 행에서) + `proprio.q`·`proprio.tau` 변경 거부**(부동소수는 상대 1e-12), R3 새 행 하나 더·키 하나 다름 거부, R5 `--hist`, R6 `--conv` = `--src`+구분자·`--src` 아래 깊은 경로·`.` 표기 → rc 1(폴더 안 만듦), 기존 출력 "exists"·불변 | 일치 |
| **144** | 판본 `se2e_c1` 표 (`:12-23`) | 파드(읽기만) | `sha256sum -c SHA256SUMS.txt` **5/5 OK**(18:21Z) | 일치 |
| **145** | 분할·키 불변: train 37,484 / val 1,799 (`:22`) | `se2e_data.load_se2e` | 파드 판정 파일 네 판 `val_keys_summary_sha` = `f03062db4b1d`(1,799)·`e22f6d8ef7fc`(300) — 등록 `:22`의 키 sha와 같음 | 일치 |
| 146 | 설계·스케줄 (`:26-31`) | 파드 판 로그 | 24회차 `conf24`(네 판 설정) 이후 로그 불변; 이번에 2,000스텝 시간 2,171.9·2,222.1·2,165.7·2,226.4 s, `prompt_config` sha none `6ee05d18ad30`·motion `7d1cf93de7b5`(체크포인트 `stageb.json`) = 결과 문서 §5 | 일치 |
| **147** | 지표·판정: 합동 = ½(e_1 + e_2), 부트스트랩 10,000·시드 0, 확인됨 ⇔ 합동 ≥ +0.015 ∧ 하한 > 0 ∧ 전이 ≥ −0.01 (`:33-42`) | `tools/se2e/motion_confirm_verdict.py` | **파드: 등록 스크립트(c767c3a 사본, sha16 `fa7299062cc5e1d1`)로 네 예측 파일에서 다시 만든 판정 = `verdict_full.json`·`verdict_300.json`과 바이트 동일**; 합동 0.032240(≥ 0.015), 하한 0.021864(> 0), 전이 0.029607(≥ −0.01) → confirmed; 내 독립 재계산(항목에서 직접) 합동 0.032240·전이 0.029607 같음; 300은 하한 −0.00056 → 규칙이면 미확인(결과 문서 `:38`과 같음) | 일치 |
| **148** | 판정 스크립트·코드 해시 (`:42`, `:47-48`) | `code_se2e_confirm` | 로컬 H2·H3; 파드 확인 사본 판정 스크립트 sha16 = 등록 = 내 사본 | 일치(N23) |
| **149** | 결과 문서 수치 (`results/se2e_motion_confirm.md`, 정본 §83 보충 `:758`, handoff `:119`, draft-log `:467`) | 파드 판정 파일 | **모든 인용 수치 일치**(§6.1 목록): 표 1 +0.0322·+0.0219 [+0.0219, +0.0425]·+0.0296 [+0.0157, +0.0430]; 표 2 네 판 × 9열(예: none s1 0.6724/0.8090/0.5953/0.9623/0.8103/0.5347/0.613/0.799/0.605); 항목 전이 6쌍; 검증 300 표 4판 × 7열·+0.0256 [−0.0006, +0.0517]·전이 +0.0199 [−0.011, +0.051]; 표 3 세 층 × 6열; 폭 0.052 → 0.021(40 %); 질문별 평균 효과 +0.035·+0.051·+0.011 | 일치 |
| 150 | 하지 않는 것 (`:52-53`) | 파드 실행 | `PROMPT_FILES_B` 블롭 불변(H4), 판 GPU 2·3(24회차 확인) | 일치 |
| **151** | 정본 §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT`, `core.py` | 로컬 S1·S2·C4; 파드 Astra 4행 effort low·요청 본문 low 4/4 | 일치(N28) |
| **152** | 정본 §84·보충 1·2 (`:743`–`:756`) | 없음(현 구현 §45 K2) | 로컬 C3·C5·S3·S5·S6, 파드 가드 26·27, DEV 20 Astra 겹침 0 | SCOPED S18 |
| **153** | **§82 보충 `:732` "유료 실행은 구현 완료 뒤 사용자 승인" 대 user-log 87·`CLAUDE.md:33`** | — | 문서 대조(§2) | **DOC D-1** |

### 5.1 24회차 표와의 차이
- 행 147–149를 "구조만"에서 **값 재현**(판정 파일 바이트 동일 + 독립 재계산 + 결과 문서 수치 전수 대조)으로 바꿨다. 행 153(D-1)을 더했다. E-MA1·탐침 행은 §7(실험 절)로 옮겼다. 근거 교체: 행 1(새 24값·새 가드 28건), 5·6·54·99·137(DEV 20, 96행, 행동 1,596개), 7(1배 대 3배), 9–12(여섯 가설), 13(부분 집합 맵), 36·45(창 50, n 40)·51(400 Hz)·56–58·60·66–67(−inf·−1e-300·−0.0), 121–129(네 관절 분할·15 Hz), 138·139(다른 편·새 음성 대조 4종), 142–143(RB1 16차원·보폭 4·필드 전수 변경).

## 6. 확인한 것 (근거)

### 6.1 변경분·24회차 정정 확인
- `git diff 6e3fda6 c767c3a`: 기준선 문서 = `CLAUDE.md` +1(user-log 87 규칙 `:33`), 정본 +4/−2(N35·N37 표시, §83 보충 `:758`), draft-log +5(`:467`–`:471`), handoff +4/−4(`:3`·`:84`·`:88`·`:119`·`:120`), direction-log +1(`:71`), 스펙 +2/−2(`:1`·`:3`), user-log +8(87), 새 결과 문서 `se2e_motion_confirm.md`(+77)·`r7_cycle24.md`(+234). 실험 파일 = 새 13개(코드 5·시험 4·등록 2·결과 1·그림 1). 나머지(`harvest/`·`tools/` 기존 파일·시험 기존 파일·사전 등록 10개·계획·`paper/`) 변경 0.
- 24회차 권고 반영(§7-1 D-1): **모두 들어감**, 보고서와 같은 커밋(N12). §7-2 선택 항목: N17 대부분·N35·N37·N38(draft-log) 해소, N18·N7·N21 그대로.
- 확인 실험 결과 문서·정본 §83 보충·handoff `:119`·draft-log `:467`의 수치 전수(행 149): 파드 판정 파일과 반올림까지 같다. 다섯째 자리 반올림 경계 값(전이 시드 차 −0.00895 → "−0.0090", 질문 mag 0.4355 → "0.435")은 표기 관례 차이로 NOTE 대상도 아님.
- **제어 문자·줄 끝 전수**(`ctrlscan25.py`, archive 텍스트 475파일): `\r\r\n` 0, 외톨이 `\r` 0, CRLF 0, `\t` 0, 기타 C0·C1·영폭 0, BOM 0, UTF-8 아님 0; 끝 줄바꿈 없음 1(`prereg.json` — 해시 고정 원문). 변경된 md 12개의 표 행 칸 수 = 머리 칸 수(불일치 0).

### 6.2 같은 사실 grep (추적 파일)
- 유료 실행 승인(`승인` × `유료|Astra|탐침|실행`): 정본 `:732`(D-1), `:530`·`:549`(옛 E-M4b-meas 기록 — 과거 실험 서술), `CLAUDE.md:33`·handoff `:88`(user-log 87 반영), 탐침 등록 `:3`(user-log 79 승인 인용 — 맞음). 정본에 `user-log 87`·"자체 검사" 0곳.
- E-MA1 결과·다음(`E-MA1b|G0 실패`): handoff `:84`(N41), draft-log `:469`, `results/ma1.md:12`·`:56`(실험 절 E-N1). 정본 0곳.
- 탐침 예산(`15,000|30,000|35,000`): handoff `:88`·user-log `:377`(15,000, user-log 87 재범위), 탐침 등록 `:74`–`:87`(30,000·35,000 — 실험 절 E-D2).
- 회차 상태(`2[3-4]회차|연속 무결`): handoff `:118`·`:120`, draft-log `:466`·`:471`, direction-log `:70`·`:71` — 커밋된 결과와 같음.

### 6.3 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | 파드 `venv_e3st` + c767c3a 사본으로 R2 DEV 전 편 `validate_episode` **36/36** + 새 음성 대조 4종 검출; LeRobot 시험 6 passed; 새 편 내보내기·검증·적재(행 138); `se2e_c1` 5/5 해시(행 144). |
| 2 모델 | 충족(CPU) | GPU 학습 없음 → CUDA 시험 건너뜀. 파드 CPU 스모크(N32, 저장·재적재 동일), CPU 묶음의 `test_stageb_torch.py`·`test_se2e_temporal_qwen.py`·`test_se2e_motion_confirm_verdict.py`·`test_se2e_trace_model.py` 통과. |
| 3 폐루프 | 충족 | Isaac 한 워커(`closed --model mock --split dev --seeds 20 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c25`, 18:14:36–18:19:08Z): `CLOSED_DONE` C5·C5' 성공 1.0, 15.96 s, 호출 48·오류 0, 확정 비율 0.902, 결정 3.009/s, 행 필드·blob(행 6), `meta.bootstrap` 10000, `prereg` OK, git `c767c3ad`, 하드 리셋 빌드 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 18:11:25–18:12:33Z): `e05`(P2, 4편) → `E05_DONE`, `rd`(standard + dr/P0) → `RD_DONE`, `calib`(P0, 4편) → `CALIB_DONE`, `e05 --split pool --seeds 2024,2079,2101 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.6). |

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 18:09:02–18:11:25Z + 가드 28, 21–24회차와 다른 값)
1 `e05 --data P0 --split test --seeds 1142`, 2 `e05 --data P2 --split cal --seeds 537`, 3 `calib --fit-split test`, 4 `calib --heldout-split test_p5`, 5 `rd --split cal`, 6–8 `closed --split test --seeds 1277`·`cal 548`·`test_p5 1302` → "refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 29,30`, 10 `pool --seeds 2124`, 11 `dev --seeds 2007` → "not in split … never opened"; 12–13 `--isaac-gpu 2`·`3` → "(GPU 2 never renders)"; 14 `--m4-lead-max -inf` → argparse rc 2(N44), 15 `--m4-lead-max 0`, 16 `--conditions "C5,C9"` → "refused before any worker"; 17 `HARVEST_ALLOW_SPLIT=cal` + `closed --split test_p5 --seeds 1320`, 18 `=dev` + `e05 --split test` → 거부; 19 `gen --seeds 44444`(확인 없음), 20 `--seeds 9998 --confirm-train`, 21 `--seeds 2087 --confirm-train` → 거부; 22 `determinism fresh --seed 30`, 23 `history --seeds 1400` → "only DEV 0-29 and POOL"; 24 `canary build-set --seeds 1333-1334`, 25 `e05 --split pool --seeds 2044`(P0) → "no episode selected"; 26 `closed --hb-mode K5`, 27 `--hb-mode serial` → "from ('K0', …, 'K4')"; **28 `--m4-lead-max=-inf` → "refused before any worker"**. **28건 모두 rc ≠ 0**; 출력 폴더는 25번(e05)의 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c25\repo` = c767c3a archive, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider -q" --basetemp=D:/tools/scratch_qdd/r7c25/pt`): EXIT 0, **1046 passed · 16 skipped**.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + `ir/env.sh`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, TMPDIR·pyc·카나리·qid = scratch): **1168 passed, 4 skipped**, EXIT 0.
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot`·`pylib_pytest`): **6 passed**.

### 6.6 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). 검토 시작 때 HEAD = ded38d7(대상 c767c3a 바로 뒤), 끝날 때 HEAD = 745af38(N40) — 내가 만든 것 아님. 작업 트리의 다른 에이전트 미커밋 변경(`prereg_astra_motion.md`·`results/ma1.md` 수정, `harvest/astra_motion/`·`tests/astra_motion/`)은 열지도 건드리지도 않았다.
- 파드 정리(`clean25.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로 보냄, 열린 핸들 0 확인 뒤, 18:20:16Z): `tmp/r7c25`(416 MB, 코드 사본·가드·평가·데이터·판정 재계산 산출), 내 Isaac 판의 `tmp/carb.8jQC9b`·`tmp/tmpewbajtza`·`cache/pyc_r6/data/harvest/tmp/tmpewbajtza`·`cache/pyc_r6/data/harvest/tmp/r7c25`, `ir/kitcache/cyclo-r7c25_standard`(208 MB). 판별 근거 N45. 끝에 `tmp`·`kitcache`·`pyc_r6`의 r7c25 항목 0, 파드 루트 `/C:` 없음, 명령줄에 r7c25가 든 프로세스 0. 그 뒤 18:21Z에 `se2e_c1` 해시 확인(읽기만, 산출 없음). `ckpt/se2e_confirm`·`logs/se2e_confirm`·`data/se2e_c1`·`code_se2e_confirm`·`logs/ma1`·`code_ma1_g0`·`logs/astra_motion/cost.jsonl`은 읽기만, `*/ma1b`는 이름·시각만.
- 로컬 임시(`D:\tools\scratch_qdd\r7c25`: `src.tar`, `repo/`, `pt/`, `tmp/`, `pod/`(스크립트·`out/` 파드 출력 사본), `check25.py`·`check25_out.txt`, `ctrlscan25.py`, `refcheck25.py`, `local_pytest.txt`)는 다음 순회 대조용으로 남김.

## 7. 실험 코드 절 (E-MA1·탐침 사전 등록 — 별도 판정: FAIL, 코드 결함 0, DOC 3)

### 7.1 행동 확인 (모두 통과)
| # | 등록 값 (`prereg_ma1.md` file:line) | 구현 | 확인 | 판정 |
|---|---|---|---|---|
| M1 | 고정 코드 해시 4개(`:77`) | `se2e_trace.py` `86a4831c…`, `g0.py` `1876c5ca…`, `g0_point.py` `fa4905ed…`, `ma1_verdict.py` `a4859739…` | 로컬 K1: LF 블롭 sha16이 06355f0 = c767c3a = 등록; 파드 `code_ma1_g0` 네 파일 = 등록 = 내 사본; 결과 문서의 등록 문서 sha `cc49b650680a489d` = 블롭(K2) | 일치 |
| M2 | 카메라: URDF 머리 사슬 → ZED 왼쪽 광학, fx = fy 367·cx 336·cy 188, RB1 머리 (0.5492, 0)(`:16`) | `se2e_trace.project`·`head_camera`·`head_q` | 로컬 T1(핀홀 정확), T2(보정 p′ = R(w)p + t, 0 = 명목), T3(피치 0.37·요 −0.21 → 광축 (cos p cos y, sin y, −sin p cos y)); 파드: 실제 URDF 머리 사슬 = 시험 사슬(4자세 최대 차 0.0), RB2 학습 16,612행 `head_joint1` 중앙값 0.5492·q05/q95 0.5492/0.5507·`joint2` −0.0061…0.0031(등록 `:7`과 같음) | 일치 |
| M3 | G0 표본: 원천 × 팔 30장, 서로 다른 에피소드 무작위(시드 0), 모자라면 채움, 앞 15 = 보정 반(`:17`) | `g0_select`·`g0_cal_half` | 로컬 T13(순서·중복 없음·채움·제외 조건·시드), T14(홀수 칸 7 → 3); **파드: `se2e_c1`에서 다시 뽑은 120키·보정 플래그·손끝 FK·명목 uv가 `g0_frames.jsonl`과 같음(최대 차 0.0)**; 칸별 서로 다른 에피소드 21·30·28·30(E-D3) | 일치 |
| M4 | 기준점: Molmo2-ER, 탐욕, 64토큰, 모델 카드 파서(1000 척도), 점 없으면 실패·사람 대체 0, 유효 < 90 → 실패 경로(`:18`) | `g0_point.py`, `parse_point`, `g0.judge` | 로컬 T15(실제 답 형식 "frame idx x y"), T17(89유효 → `insufficient_references`·`next` R2); 파드: 저장된 120답에서 `parse_point`가 점 유무를 120/120 재현, 실패 1(`RB1_ep37_k0` "There are none."), 사람 대체 0 | 일치(E-N2) |
| M5 | 통과 ⇔ 중앙값 ≤ 12 ∧ p90(선형 보간) ≤ 30, CMP_EPS 1e-12(`:20`) | `g0_stats`·`g0_pass` | 로컬 T11(11값 p90 정확히 30), T12(12·30 정확히 통과, 12(1+2e-12)·12+1.3e-11·30+1e-10 실패, 12+1.1e-11 통과 — t = 12의 상대 eps 1.2e-11), T17(오차 중앙값 정확히 12·p90 정확히 30 → `pass_nominal`) | 일치 |
| M6 | 실패 → 원천별 6자유도 PnP(soft-L1 10 px, LM) → 검사 반 재판정, 보정 반 < 10 → 실패(`:21`) | `fit_correction`, `g0.judge` | 로컬 T16(무잡음 20시점 복원 < 1e-6; 175 px 이상치 하나에 soft-L1 인라이어 중앙 1.04 px 대 최소제곱 14.98 px), T17(RB2 보정 기준점 9장 → `fail`, 일정 80/40 px 편차 → `pass_pnp`·보정값이 카메라 모델) | 일치 |
| M7 | 그래도 실패 → R2 준비면 새 등록, 아니면 보고하고 멈춤(`:22`, 정본 §84 `:746`) | 결과 문서 `:12`–`:14` | **파드: 등록 `g0.py`로 다시 판정 = `g0.json`(파싱 동일): `fail`·`next` R2·유효 119**; 명목 100.9/264.5, PnP 검사 86.9/212.1(결과 문서 `:9`–`:10`); R2_TRAIN 워커 진행 중(준비 안 됨); **`ckpt/ma1`·`data/ma1` 없음, `logs/ma1`은 G0 파일 7개뿐** → 학습·예측·지연·판정 안 돌림 | 일치 |
| M8 | 등록 시각 < G0 실행(`:1`, `:3`) | 커밋·파일 시각 | 등록 머리 17:32:31Z < 커밋 17:32:42Z < `g0_frames.jsonl` 17:33:19Z < `g0_points` 17:34:44Z < `g0.json` 17:34:46Z; 결과 문서의 파일 sha16 3개 = 파드 파일 | 일치 |
| M9 | trace5: 끝 = 그리퍼 상태가 바뀌는 첫 프레임(> 0.5 닫힘) 또는 끝, 상한 3 s; 5점 등간격 3D 보간 후 투영; 깊이 ≤ 0.05·영상 밖 마스크(`:27`–`:28`) | `event_end`·`trace5` | 로컬 T4(0.5 열림·0.5000001 닫힘, 상한 30프레임, 에피소드 끝), T4b(k+30 변화는 잡고 k+31은 상한; 30 Hz 상한 90), T5(e = k+7 → 0, 1.75, 3.5, 5.25, 7), T6(z 0.05 마스크·0.0500001 유지, u = 672 정확히 유지·넘으면 마스크, v = 0 유지) | 일치 |
| M10 | 보조 목표 21회귀(11 + 10), 좌표/0.05, 마스크 smooth-L1, λ 0.1(`:29`) | `trace_aux_vecs`, `se2e_trace_model.py` | 로컬 T7; 파드 torch 시험(`test_se2e_trace_model.py`) 통과 | 일치 |
| M11 | 덧그림: 과거 k−20..k, 빨강 2 px, 불투명도 1.0 → 0.25, 깊이 ≤ 0.05에서 끊음, 고리 4 px; 학습 때만 p 0.3 제거, 난수 (`eetrace@v1`, 시드, 스텝)(`:33`–`:35`) | `render_overlay`·`overlay_dropout` | 로컬 T8, T9(가장 새 선분 (255, 32, 32), 가장 오래된 (64, 8, 8), 끊긴 곳 검정, 고리), T10(48,000회 0.3018·결정적·다른 시드 다름·입력 불변·전역 난수 불변·p 0 = 그대로) | 일치 |
| M12 | 채택 규칙: 주효과 ≥ +0.02 ∧ 전이 ≥ −0.01 ∧ p95 증가 ≤ 10 %; 시드 0 통과 요인만 시드 1, 두 시드 평균으로 최종; O 불채택 → VLA 덧그림 버림; 의존 하락 > 0.05 경고; 부트스트랩 10,000·시드 0(`:61`–`:72`) | `ma1_verdict.py` | 로컬 W0 상수, W1(주효과 정확히 0.02·전이 정확히 −0.01·p95 정확히 +10 % → 통과; 0.1000001 → c3 거짓), W2(0.01999995 → 실패), W3(상호작용·전이 −0.05 실패), **W4 CLI 끝까지**(300 스냅샷 × 3, `RB1_`/`RB2_` 키 — 파드 실제 키 `RB1_ep37_k0` 형식과 같음; 내 재계산 = 출력, O p95 +11 % → 'drop', 원천별 효과 계산, 시드 1 없음 → final None), W5 부트스트랩 재구현 오차 0, W6(두 시드 평균 경계), W7(0.05 경고 없음·0.0500001 경고), W8(모르는 칸 이름·한 칸 스냅샷 하나 빠짐 → 거부) | 일치(학습 안 돌아 실제 입력 없음) |
| M13 | 기준선 무수정(`:79`) | — | H4·H5·S6: `PROMPT_FILES`·`PROMPT_FILES_B`·`se2e_data.py`·`se2e_temporal.py`·`harvest/runtime` 블롭 불변, 기준선 모듈이 새 모듈을 import하지 않음 | 일치 |
| P1 | 탐침 등록 "유료 호출 전"(`prereg_astra_motion.md:1`, 커밋 a62164d 17:39:06Z) | 파드 비용 장부(시각·비용만) | 첫 유료 호출 17:40:44Z(커밋 뒤); 비용 0인 API 설정 시험 3회는 17:38:56–57Z(등록 머리 시각 뒤·커밋 10초 전); 17:41:35Z까지 유료 13회 203.99원 = user-log 87 "13회 204원", 그 뒤 대상 커밋까지 유료 호출 0 | 일치(E-N3) |

### 7.2 DOC (실험 절)
- **E-D1. `docs/stage3/prereg_astra_motion.md:6`–`:11`(0절 변경 기록) — 시각이 등록 문서 자신의 고정 시각보다 뒤다.** 머리 `:1`은 "사전 등록 (2026-09-25T17:38:25Z, 유료 호출 전)", 커밋 a62164d는 17:39:06Z인데 변경 기록은 "2. 2026-09-25 약 17:40 — P 변형 전부 제거", "3. 약 17:50 …", "4. 약 18:10 …", "5. **약 18:20** — 직렬 호출(user-log 86 …)"이라 적는다(`:6` "시각 UTC"). user-log 86은 17:18 UTC, user-log 83(P 변형 제거 원인)은 16:17 UTC라 기록 시각이 약 1시간 늦게 적힌 것으로 보인다. "모두 유료·모델 호출 전"이라는 등록의 핵심 주장을 문서 스스로 읽을 수 없게 만든다. **고칠 것**: 실제 UTC(user-log·커밋 시각 기준)로 바꾸고 "[→ 정정 …, R7 25회차 E-D1: 시각 +1 h 오기]" 표시.
- **E-D2. `docs/stage3/prereg_astra_motion.md:74`–`:87`(8절 비용·단계) — user-log 87 재범위가 등록에 없다.** 대상 트리에서 user-log 87(`user-log.md:377`, 17:43 UTC)은 "탐침 재범위 — 유료는 G1 + S2 + G2(low 오답에만 high ≤ 8회), S1 Astra 뺌, 누적 하드 정지 15,000원 … 관문마다 결함이면 멈추고 재설계 → **사전 등록 변경 기록 → 재개**"라 적고 handoff `:88`도 15,000원을 현재 값으로 적는데, 등록 8절은 여전히 "목표 ≤ 30,000원, 하드 정지 35,000원", S1(동기 S 약 4편)·S3 포함 단계표다(커밋 메시지 a62164d "hard stop to be amended to 30,000 KRW"와도 다름). 비용 장부를 보면 유료 호출은 대상 뒤(17:54Z 이후) 다시 시작되어 18:15:23Z 누적 3,558.59원(유료 행 237)이 됐고, 등록 개정은 대상·HEAD 어느 커밋에도 없고 작업 트리의 미커밋 수정으로만 있다(검토 안 함). **고칠 것**: 재범위(단계·상한 15,000원·S1 제외·재개 조건)를 등록 변경 기록으로 커밋; 다음 순회는 그 커밋 시각 < 재개된 첫 유료 호출인지 확인.
- **E-D3. `docs/stage3/results/ma1.md:28` — "원천 × 활성 팔마다 30장(서로 다른 에피소드, 시드 0)"은 재현한 선택과 다르다.** 파드에서 `se2e_c1`로 다시 뽑은(= `g0_frames.jsonl`과 키 동일) 120장의 칸별 서로 다른 에피소드 수는 RB1-왼 **21**, RB1-오 30, RB2-왼 **28**, RB2-오 30 — 두 칸은 등록 `:17`의 "모자라면 고른 에피소드의 다른 행으로 채움" 규칙으로 채워졌다(코드는 등록대로, T13). 결과 문서의 표본 서술만 틀리다. **고칠 것**: "(칸마다 서로 다른 에피소드 최대 30; RB1-왼 21·RB2-왼 28편은 등록대로 같은 에피소드의 다른 행으로 채움)".

### 7.3 NOTE (실험 절)
- E-N1. `results/ma1.md:56` "## 5. 다음 (결정 필요)"·`:59` "어느 쪽도 권하지 않는다" — 같은 대상 트리의 draft-log `:469`·handoff `:84`는 "E-MA1b(로봇 기준 3D 궤적 보조 손실, 카메라 불필요)로 재설계"라 적는다(등록 ded38d7은 대상 뒤). "[→ E-MA1b 재설계 …]" 표시 권함(N41과 함께).
- E-N2. `parse_point`의 `_POINTS` 정규식은 좌표 3–4자리만 받는다(2자리 "45" → 점 없음, "045" → 인식). 이번 119답의 좌표 토큰 238개는 모두 3자리라 잃은 점 없음. "모델 카드의 파서"라는 출처는 파드의 카드 사본(`tmp/ma1/molmo2_readme.md`)에서 정규식 문장을 찾지 못해 확인 못 함 — R2 재등록 때 출처 URL·줄을 등록에 적기를 권함.
- E-N3. 탐침 등록에는 코드 해시가 없다(코드 `harvest/astra_motion/`는 미추적, 등록 `:26` "코드 `44c907d` + 탐침 파일") — 다른 등록(`prereg_ma1` §8, 확인 실험 §5)처럼 고정 해시를 적기를 권함.
- E-N4. `ma1_verdict.py` 입력 검사는 assert 수준이고 등록 검증 집합(300, `val_keys_sha` `e22f6d8ef7fc`)을 스크립트가 확인하지 않는다(N3와 같은 성격; 네 칸 키 일치는 강제 — W8).
- E-N5. `prereg_ma1.md:78`의 "이후 구현" 파일(`build_data.py`·`ma1_latency.py`·`stageb_train.py` 옵션)은 중단으로 만들어지지 않았다(결과 `:54`와 같음). ded38d7(대상 뒤)이 `stageb_train.py`를 고쳤으므로 26회차 기준선 범위(N40).
- E-N6. 결과 문서 `:30` PnP 보정값(RB1 ω (0.53, −0.49, 0.15)·t (0.22, 0.18, 0.25), RB2 ω (−0.49, 0.36, −0.04)·t (−0.23, −0.28, 0.05))·`:36`–`:43` 진단 표(≤ 30·≤ 60 px 비율, 영상 밖 31/59·5/60, 다른 팔 8·6, 제외 뒤 102.1/220.4·56.3/162.0, du/dv (−17, −88)·(−40, +2))·"다른 팔 14/119"는 파드 `g0.json`·`g0_diag.json`과 같다.

## 8. 다음 순회 전에 할 일 (제안)
1. **D-1(기준선)**: 정본에 user-log 87 [사용자 결정] 절(유료·GPU 실험 = Claude 자체 검사, 사용자 승인 불필요, 한도·실험별 상한 유지)을 더하고 `:732`에 "[→ §85 …]" 표시. user-log에 사용자 결정을 적는 커밋마다 정본 절을 같은 커밋에 넣는지 `git show --stat`로 확인.
2. **실험 절**: E-D1(탐침 등록 변경 기록 시각 정정), E-D2(재범위 등록 개정 커밋 — 재개된 유료 호출보다 앞선 커밋인지 기록), E-D3(`results/ma1.md:28` 표본 서술).
3. (선택, NOTE) N41(정본 §84 보충 3: G0 실패·E-MA1b), N43(`se2e_diag.md` 중앙 차분 한계 줄), N42(CMP_EPS "상대" 표기), N17 스펙 `:5`·`:7` 표시, N38 direction-log 형식, E-N1·E-N2·E-N3.
4. 26회차 대상은 745af38 이후 HEAD, **연속 무결 0에서, 기준선 파일을 고친 새 코드 포함**(ded38d7 `stageb_train.py`·`se2e_trace_model.py`): 옵션 끔 = 기존 동작(체크포인트 해시·`prompt_config` 불변), E-MA1b 판정 스크립트 경계값·등록 해시, 등록 시각 < 첫 A3d 실행, 탐침 등록 개정의 커밋 시각 < 재개된 유료 호출, 7bb9035 결합 구현 계획·user-log 88·`CLAUDE.md` 규칙과 정본의 관계(D-1과 같은 유형 재발 여부). Git Bash kubectl은 `MSYS_NO_PATHCONV=1`, argparse 음수 값은 `--opt=-x` 형태로(N44).
