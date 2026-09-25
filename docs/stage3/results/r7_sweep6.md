# R7 문서 전수 정리 sweep6 (5회차 뒤, 6회차 전)

- 작성 2026-09-25 01:54 UTC(`date -u`), 문서 정리 에이전트. 대상: `D:\qdd` `dev` HEAD `541068a` + 미추적 `r7_cycle5.md`. 커밋·푸시 안 함(메인 세션 몫). 파드 건드리지 않음.
- 목적: 5회차 DOC P1·P2와, 1–5회차가 매번 한두 곳씩 찾아낸 "옛 서술"을 한 번에 없앤다. 코드는 **주석·docstring·사용자에게 보이는 오류 문구만** 고쳤고 동작은 바꾸지 않았다.
- 규칙: `[사용자]` 줄·user-log 원문 인용·[사용자] 제목 절 본문은 그대로(지운 `[사용자` 줄 0, `tools/intent_check.py` total 62 flagged 0). 옛 문장은 지우지 않고 "→ **정정/해결/해소/범위 밖(…)**" 표시를 뒤에 붙였다. 정본은 끝에 §71만 덧붙였다. 논문 `.tex`는 건드리지 않았다(§70). 각 파일의 줄 끝(LF/CRLF, `draft-log.md`는 섞임 그대로)을 지켰다. 임시 파일은 `D:\tools\scratch_qdd\sweep6`만.

## 1. 요약

| 범주 | 파일 수 | 내용 |
|---|---|---|
| A. 5회차 P1 | 4 | `handoff.md` 머리 상태 줄(늦어질 숫자 대신 §2.8 마지막 줄을 가리킴, 정본 §1~§71), 코드 무결 횟수 오기(4 → 3회, 2·3·4회차) 정정 표시(`handoff.md`·`direction-log.md`·`r7_cycle4.md` 끝 한 줄), §2.8·direction-log에 5회차 줄 |
| B. 5회차 P2 + 열린 문제 목록 전수 대조 | 13 | 결과 문서 `r3`–`r6`·`stageA_pipeline`·`e_m4b_meas`·`r2_datagen`·`pre_r7_fixes`·`r7_fixes`·`random5`·`e3st`·`p0_inspect_robots`의 열린 문제를 코드·후속 문서와 대조해 해결 / 범위 밖(§67 C8·§68 K6) / 여전히 열림 표시 |
| C. 102°·`ZED_M`·D-stereo(§43·§47 후속) | 9 | M1·D21·SUMMARY·E-first·EVAL·plan v6.8·D23·handoff §2.6·p0 결과 |
| D. D2x [결정 필요] 해소 표시 | 5 | D20·D21·D23·D24·D26 — 정본 §35·§37–§39·§42·§43·§47·§49·§52가 이미 정한 것 |
| E. user-log 62 풀이 표시 | 2 | 계획 39줄, `r5_closed_loop.md` 89줄('같은 vLLM 설정·캐시·lead'는 원문에 없음) + r5 §5 1순위 잔여 표 행 |
| F. 단계 2 문서 머리 안내 줄 | 15 | M1–M10·E-first·EVAL·SUMMARY·plan·design README: Jev → Jev-L(§44)·융합(§58·§60)·카메라(§43·§47) |
| G. 코드 주석·문구 | 10 | `stagea_train` 사용법, `gen` 거부 문구, `m4.py`·`closed.py` 머리, Jev 옛 도구 4개 + `config.py`, `canary.py`, 시험 주석 1 |
| H. 기록 | 3 | 정본 §71, `draft-log.md` 한 줄, 이 문서 |

바뀐 추적 파일 49개 + 새 파일 1개(이 문서). 로컬 스위트 784 passed / 11 skipped(아래 §5).

## 2. 바꾼 곳 (파일:줄 = 바꾼 뒤 줄 번호)

| 파일:줄 | 무엇을 | 왜 |
|---|---|---|
| `docs/handoff.md:3` | 상태 줄 = 갱신 시각 + "회차별 판정·연속 무결 횟수는 §2.8 마지막 줄" + 정본 §1~§71 | P1(갱신 누락·횟수가 줄마다 어긋남) — 다시 늦어지지 않게 숫자를 뺌 |
| `docs/handoff.md:5` | 정본 범위 §1~§71 | §71 추가 |
| `docs/handoff.md:12` | user-log "1~41번 — 지금은 66번까지" | 낡은 범위 |
| `docs/handoff.md:51` | §2.6 `ZED_M` 줄 아래 정정 줄(위 줄은 `[사용자 결정]` 줄이라 그대로) | §43 폐기 |
| `docs/handoff.md:64` | §4 대기 목록 = 단계 2 초기 기록 표시 | 지금 대기 항목은 §2.7 "없음" |
| `docs/handoff.md:83` | 읽을 범위 "§43부터 끝까지(지금 §71)" | 다시 늦어지지 않게 |
| `docs/handoff.md:96` | 4회차 줄 "코드 무결 4회 연속"에 정정 표시(3회, 2·3·4회차) | P1 |
| `docs/handoff.md:97` | 5회차 줄(FAIL, DEFECT 0, DOC 2, 코드 무결 4회 연속 2–5회차) + sweep6 | 요청 1 |
| `docs/stage3/direction-log.md:52` | 4회차 행 횟수 정정 표시 | P1 |
| `docs/stage3/direction-log.md:53` | 5회차 행(방향 질문 6개, 4회차 행과 같은 틀) | 회차마다 기록 |
| `docs/stage3/results/r7_cycle4.md:108-109` | 끝에 정정 한 줄(17줄 "네 번째로 무결" → 3회 연속) | P1 출처 — 보고서 본문은 기록이라 그대로 |
| `docs/stage3/results/r6_eval.md:54` | 열린 문제 1 → 해결(pre-R7 519de26, `closed.py` 'Backends' 줄·`stageb` 분기) | **P2** |
| `docs/stage3/results/r6_eval.md:14` | 명령 표 "vLLM을 띄우고"에 단계 B 체크포인트 = `fused_model` HF 서버 | 같은 사실 형제 |
| `docs/stage3/results/r6_eval.md:56` | 열린 문제 3 → 점수식 확정(§65, 거부권 용도) | 해결 |
| `docs/stage3/results/r6_eval.md:59-60` | 열린 문제 6(쥠 디바운스)·7(K1·K3·K4 훅) → 해결(`pre_r7_fixes.md` §3·§4) | 5회차 N2 |
| `docs/stage3/results/r5_closed_loop.md:98` | 열린 문제 7 → 해결(`fused_model.py`, 23-D 사상, `closed --backend fused`) | **P2** |
| `docs/stage3/results/r5_closed_loop.md:92-94` | 열린 문제 1(T_sub·사건 해결 / A5′·R3 SCOPED / T0·`detect_phrase` 열림), 2(measure·critic 해결 / M9 SCOPED), 3(J5는 R6 구현, θ는 오프라인만, 나머지 열림) | 5회차 N2 |
| `docs/stage3/results/r5_closed_loop.md:85-86` | 1순위 잔여 표 행에 76줄 정정 포인터, 2순위 [미측정] 행에 pre-R7 실측 포인터 | 5회차 N3 |
| `docs/stage3/results/r5_closed_loop.md:89` | user-log 62 풀이 표시 + 1순위 GPU 경합 서술 정정(실제는 한 HF 프로세스, `pre_r7_fixes.md` §1.1·§1.6-1) | 5회차 N3·요청 5 |
| `docs/superpowers/plans/2026-09-25-e2e-ready.md:39` | '같은 vLLM 설정·캐시·lead 호출'은 원문에 없는 Claude 풀이, 융합은 HF(§67 C4), 서빙은 §67 C8 | 요청 5 |
| `docs/stage3/results/r4_stageB.md:40` | §35 'Jev 권위' = 지금은 Jev-L·융합 결정 토큰 | Jev 사용 불가 |
| `docs/stage3/results/r4_stageB.md:147-148,151,153,155-156` | 열린 문제 1(`GraphedSampler`)·2(R3 공유 접두)·9(R2 `g2goal_*` = labels_v2 Δ)·10(pytest.ini·conftest) 해결, 5 SCOPED, 7 갱신(R 훅 자리 있음, 잔차 모드 런타임은 열림) | 5회차 N2 |
| `docs/stage3/results/r3_throughput.md:164` | 열린 문제 3 → 해결(런타임 `question_id@vN` 기록, 보정·prompt_config 대조 거부) | 해결 |
| `docs/stage3/results/stageA_pipeline.md:114,118,120` | 열린 문제 1(풀 labels_v2·§65)·5(qid 연결)·7(`--cameras HW`) 해결 | 해결 |
| `docs/stage3/results/e_m4b_meas.md:247` | 빈 집합 `unknown` [결정 필요] → §64 해소 | 해결 |
| `docs/stage3/results/e_m4b_meas.md:255` | "커밋 안 함"·수집 오류 → 이후 해소 | 현재 시제 낡음 |
| `docs/stage3/results/r2_datagen.md:138,143` | §8 제목·"그 전에 할 것" (1)–(4) → §66 처리 | 해결 |
| `docs/stage3/results/pre_r7_fixes.md:63-65,80,115-118` | §1.6-1~3, §6-1~4 → §67 C8·§68 K6 SCOPED 표시(K3 안전 술어 과제 특화는 열림) | 범위 표시 |
| `docs/stage3/results/r7_fixes.md:51,78-80` | 파드 `ir_run.sh` 주석 → §68 해결, §7 항목 → §67·§67 보충·SCOPED | 해결·범위 |
| `docs/stage3/results/random5.md:23,51` | 500–699 옆에 "→ 3000–3199, 4줄 정정"/"당시 실측" | 4·5회차 N |
| `docs/stage3/results/e3st.md:255` | 명사 표 [결정 필요] → §46 `detect_phrase` 해소 | 해결 |
| `docs/stage3/results/p0_inspect_robots.md:142` | `ZED_M` 쌍 → §43 폐기 | §43 |
| `docs/design/M1-state-representation.md:120` | 102°×57° = 센서 최대 화각, VGA 85°·fx 367, 오차 5/15 mm → fx 367이면 약 3.9/10.8 mm(우리 계산) | §47이 약속한 M1 정정 |
| `docs/design/D21-aiworker-zed.md:30,84,121-122,184,200-201,212` | 102° 인용·비교, VGA ≈272 px 표 아래 정정 줄, `ZED_M`·D-stereo 폐기, "결정할 것" (a)–(d) 해소 | §47이 약속한 D21 정정, §37–§39·§43 |
| `docs/design/SUMMARY.md:669,671-672` | 102° 정정, `ZED_M`·D-stereo 폐기 | §43·§47 |
| `docs/design/E-first-experiments.md:106,671` | 장면 고정 줄의 `ZED_M`·102° → §43·§47 | §43 "E-first §1.4 `ZED_M` 표기는 편집 때 폐기 표시" 미이행분 |
| `docs/design/EVAL-evaluation-design.md:85-86,160,307` | D-stereo·`ZED_M` 폐기 | §43 "EVAL D-stereo 폐기 표시" 미이행분 |
| `docs/plan.md:361-362` | `ZED_M`·D-stereo 폐기 | §43 |
| `docs/design/D23-inspect-robots-integration.md:6-7,102,223` | 머리 정정 줄(`ZED_M`), [결정 필요] 2건 → §42 해소 | §42·§43 |
| `docs/design/D20-expert-role.md:89,119` | [결정 필요] 2건 → §35 해소 | 해결 |
| `docs/design/D24-jev-replacement.md:176` | [결정 필요] (1)(2) → §47·§49 해소 | 해결 |
| `docs/design/D26-vlm-training-recipe.md:69,141,178` | [결정 필요 — 메인] 3건 → §52 잠정 결정 1–3 | 해결 |
| M1–M10 `:4`, `E-first:3`, `EVAL:3`, `SUMMARY:3`, `plan.md:3`, `design/README.md:3` | 머리 안내 줄 1개씩(Jev → Jev-L·융합, 카메라 §43·§47, 최신 상태는 handoff) | "Jev를 쓸 수 있는 것처럼" 읽히는 단계 2 문서 전체 |
| `docs/superpowers/plans/2026-09-24-stage3-experiments.md:7` | 개정 줄: Jev 과제 동결(direction-log 09:44), 지금 계획은 e2e-ready | 옛 계획에 §44 표시 없음 |
| `harvest/train/stagea_train.py:7-9` | `load` 사용법 = 실제 CLI(`--adapter`, 선택 `--pool`/`--n`/`--seed`, `--rule`은 `--target-source outcome`일 때만) | 5회차 N5 |
| `harvest/datagen/gen.py:47-50` | 거부 문구: "DEV 0-29 only (R2_TRAIN … needs --confirm-train)" / "DEV 0-29 and R2_TRAIN … (--confirm-train given)" + "every other seed is refused (…)" — 같은 시드를 같은 예외로 거부(문구만) | 4회차 N9·5회차 N10 |
| `harvest/runtime/m4.py:21-24` | 미구현 목록에서 J5 뺌(R6에서 `core.py`에 구현), θ는 오프라인 판정만 | 옛 서술(이번에 찾음) |
| `harvest/eval/closed.py:8-9` | 바깥 프로세스 서빙 = Jev-L은 vLLM, 단계 B 체크포인트는 `fused_model`(HF) | 5회차 5.1이 짚은 `:8` |
| `harvest/canary.py:1-4`, `harvest/clients/jev.py:1-3`, `harvest/clients/jev_smoke.py:1-3`, `harvest/cli_e0.py:1-3`, `harvest/config.py:17` | "Jev는 쓸 수 없음(user-log 46, §44), 동결된 E0 도구" / canary = 결정 모델 일반 | Jev 사용 불가 |
| `tests/datagen/test_gen_guards.py:20` | 주석: 500–699는 CAL 500–549를 덮는 범위 | grep 대상 설명 |
| `docs/design/00-interfaces.md:590-598` | **정본 §71** 추가(끝에만) | 이 정리의 결정·규칙 기록 |
| `docs/draft-log.md:443` | 5회차·sweep6 한 줄 + 교훈 | 회차마다 기록 |

**되돌린 것**: `harvest/train/stageb_data.py:15`의 'Jev-authority' 안내를 넣었다가 되돌렸다(`git hash-object` = HEAD 블롭 `a174e306…`). 이 파일은 `stageb_train.PROMPT_FILES_B`라서 바이트 해시가 체크포인트 `prompt_config.files_sha`와 대조된다(`runtime/fused_model.check_prompt`, 어긋나면 거부). 주석만 바꿔도 기존 단계 B 체크포인트가 거부되므로 동작 변경이다. 같은 이유로 `stagea_train.PROMPT_FILES`(`clients/jevl.py` 등 9개)·`stageb_model.py`는 건드리지 않았다(정본 §71에 규칙으로 적음). `jevl.py:8`의 "one call"은 모듈형 DecCall 한 번이라는 다른 뜻이고 이 목록 안이라 그대로 둔다.

## 3. 여전히 열린 것 (해결·SCOPED 아님, 결함으로 보지 않음)

1. 정본 §27 끝: R1 금지어 보기 이름(`failure`·`valid_progress` 등) 교체 — `harvest/jevcall.py` `PROGRESS`에 그대로. progress 질문은 지금 호출·학습에서 빠져 있고, `jevcall.py`는 PROMPT_FILES라 바꾸면 재학습·재보정 대상.
2. `r5_closed_loop.md` §6-1: T0 첫 계획 호출(지금은 고정 계약 c1)과 `detect_phrase`(§46) 런타임 반영.
3. 잔차 모드 체크포인트 런타임 거부(`fused_model.py`), R 훅 = 0(`skills.residual_hook_zero`) — `r4_stageB.md` §8-7, `pre_r7_fixes.md` §1.6-4.
4. θ 게이트 런타임 적용 없음(`calibration.py` 오프라인 판정만, `eval/calib.py` 노트와 일치), M4 C3′·agree_mode·align_tol·CUSUM·M5 ref(t)(Ruckig) — `r5` §6-3, `m4.py` 머리.
5. K3 `run_instruction` 안전 술어가 머그→트레이 과제 전용(`pre_r7_fixes.md` §6-4).
6. aiworker 몸체 P1/P2 섭동 막힘(`NotImplementedError`), `SimulationApp.close()` 멈춤은 `os._exit(0)` 우회 — `r5` §6-8·10.
7. 설계·절제 후보(결과 대기): `r4` §8-4(절대 대 Δq)·6(백본 조건 층)·8(`t_state` 물체 id), `r3` §8-1(HW 병합 모델 vLLM 재측정)·2(스냅샷 단위 검증 부분집합)·4(단계 B `evaluate` 묶음화)·5(단계 A 활성 팔 필드)·6·7, `stageA_pipeline` §8-2(progress 미학습)·3(NE 소멸 → J5 집합 크기)·4(순서 순환)·6(보정은 vLLM 확률로)·8·9, `r5` §6-4(라벨 기준점)·5(H 표 공유)·6(SFT H 대 HW), `r6` §5-2·4·5·8·9, `se2e_data.md` §9-4·5(S-E2E 사전 등록).
8. 5회차 NOTE 중 운영 항목: N7(S-E2E 사전 등록 — `--max-val` 층화·중간 저장·`--eval-every`), N8(시작일 카나리 새로 만들기), N9(TEST2 1150–1299가 `eval/splits.py` `RANGES`에 없음), N11(폐루프 공용 `TMPDIR` 누적), N12(PowerShell에서 `harvest/load/session.py`의 `date` 의존 2개 실패).
9. 정본 §59 "남은 일"(RTX PRO 6000 실물 서버 벤치)·§49 LAN 지연 — §67 C8 동시 부하 지연과 함께 실물 서빙 결정 때.
10. 논문 `.tex` vLLM 결정 서빙 서술(§70, 손대지 않음).

## 4. 판단이 불확실했던 것 (메인 세션 확인 권장)

- **정본 §71을 이 정리 에이전트가 덧붙였다.** §67–§70처럼 회차마다 절을 두는 관행을 따랐다. 메인이 따로 절을 쓰려면 번호가 겹치지 않게 이 절을 고치거나 합쳐야 한다.
- **direction-log 5회차 행의 방향 질문 6개 답**은 4회차 행의 틀·근거를 그대로 옮겨 적었다(메인 세션이 직접 답하는 항목이다).
- **단계 2 문서 15개에 머리 안내 줄**을 넣었다. 5회차는 단계 2 문서를 결함으로 세지 않았지만("정본 우선"), "Jev를 쓸 수 있는 것처럼"·102°·`ZED_M` 서술이 수십 줄이라 줄마다 표시하는 대신 문서당 한 줄로 막았다. 본문 줄은 요청받은 곳(M1:120, D21, SUMMARY:669, E-first:106)과 `ZED_M`·D-stereo 문장에만 표시했다.
- **`LatencyChargingController` 스텁**: 검증 보고서는 매 회차 SCOPED S1로 세지만 정본 §67 C8 목록에는 이름이 없다(계획 단계 P3). 정본에 SCOPED로 적을지 메인이 정할 일.
- **CLAUDE.md**의 Jev 서술(텍스트 입력만 등)은 Jev에 대한 사실로는 맞고, 이 에이전트는 CLAUDE.md를 고치지 않는다 — 규칙 줄에 "Jev → Jev-L" 안내를 넣을지는 사용자·메인 몫.
- `harvest/sim/randomization_pools.json:20`의 "run_dev r5calib 2026-09-25"는 KST 날짜로 보이지만 'UTC' 표기가 없고 코드가 읽는 데이터 파일이라 두었다(4회차 판단과 같음).
- 정본 §37(345–346줄)의 102°·"0.6 m 약 5 mm"는 옛 절이라 고치지 않았다(§47·§71이 덮음).
- M1:120의 fx 367 오차값(약 3.9·10.8 mm)은 D21 표와 같은 식(시차 오차 0.25 px, 기선 63 mm)으로 계산한 **우리 계산**이다.

## 5. 검증

- 로컬(Git Bash, `cd D:/qdd && python -m pytest`): **784 passed, 11 skipped**(69.6 s). 실행 뒤 `docs/stage3/qid_registry.json` 생기지 않음.
- 줄 끝·문자: 바뀐 49개 파일 모두 원래 줄 끝 유지(LF 파일은 LF, CRLF 파일은 CRLF, `draft-log.md`는 CRLF 284줄 그대로 + LF 1줄), 탭·폼피드 수는 HEAD와 같음(`draft-log.md` 탭 1개는 원래 있던 것).
- `git diff -U0`에서 지운 줄 중 `[사용자`가 든 줄 0, `python tools/intent_check.py` → total 62 flagged 0. 지운 줄은 모두 같은 줄에 내용을 남긴 채 표시를 덧붙인 것이고, 문장을 바꾼 곳은 handoff 머리 3·5·83줄(상태·범위), 코드 주석·문구뿐이다.
- `harvest/train/stageb_data.py` = HEAD 블롭(`a174e306…`), PROMPT_FILES·`stageb_model.py` 변경 없음.

## 6. 쓴 검색 (다음 순회용)

`D:\tools\scratch_qdd\sweep6\search.py`(추적 파일 전부, `paper/`·`r7_cycle*` 제외, 정규식 대소문자 무시):
`vLLM` + (decide|fused|StageB|융합|결정), `one call|single call|한 번 호출|모델 한 번`, `\[제안\]|\[proposal\]`, `500 ?[-–~] ?699|500, ?700`, `2026-09-25`, `GPU ?2 ?금지|never GPU ?2`, `102 ?°|fx ?272|≈272`, `ZED_M`, `D-stereo`, `실모델 없음|실물 모델 없음|mock_fused ?만|훅이 없다`, `§ ?1 ?[~–-] ?§ ?\d+|§ ?43 ?[~–-] ?§ ?\d+`, `\bJev\b(?!-L)`, `gemma`, `20 ?Hz`, `진행 중|재생성 중|in progress`, `not implemented|not wired|TODO`, `결정 필요`(D2x·결과 문서) — 그리고 각 결과를 `정정|해결|해소|폐기|SCOPED|대체됨|당시|→` 표시 유무로 걸렀다. 결과 문서의 "열린 문제/남은 문제/한계/다음" 절은 항목마다 코드(`grep`)와 `pre_r7_fixes.md`·`r7_fixes.md`·정본 §58–§70으로 대조했다.
