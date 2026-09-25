# R7 객관 검증 순회 — 29회차 (cycle 29, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드·문서의 작성자가 아님; `r7_cycle28.md`의 표·결론을 근거로 쓰지 않고 28회차 정정 주장마다 원 문서·파드 원자료·파드 명령 출력으로 다시 확인했다 — 책 P68). 가드·음성 대조·Isaac 시드는 **21–28회차와 다른 새 값**. 작성 2026-09-25 21:28 UTC(`date -u` 21:28:19Z, 로컬 정리 직후; 로컬 사본 풀기 21:10:02Z, 파드 첫 명령 21:11:21Z, 파드 정리 끝 21:23:27Z, 보고서 쓰기 시작 21:24:28Z). 기록 시각은 UTC(user-log 72).
- 대상: `D:\qdd` `dev` 커밋 **`0cc45ae`**(`0cc45ae2d1289e591b679bcc32592ed4d7b1864a`, 커밋 시각 2026-09-25 21:07:54 UTC, "R7 cycle 28 baseline FAIL … structural fix: progress status lives only in handoff (book P69, [결과 전] vocabulary), ma1.md/P63 corrections, spec N88, book 03 §86 supplement, 06 cell/time fixes, R2_TRAIN merge warning"). `47edadb..0cc45ae` = 커밋 1개, 14파일(문서만: 책 7장·draft-log·handoff·direction-log·결과 `astra_motion.md`·`ma1.md`·새 `r7_cycle28.md`·결합 설계 스펙), **코드·시험 변경 0**(`check29` H1). 검토 내내 HEAD = 0cc45ae, 작업 트리 깨끗함(이 보고서만 추가).
- **범위 나눔(28회차와 같은 틀)**: **기준선 판정**(연속 무결 카운트) = `harvest/`·`tools/`(실험 도구 제외)·시험·정본·사전 등록·handoff·기록·결과 문서·기록책 `docs/book/`. **실험 코드 절**(따로 판정) = 0cc45ae 이전에 커밋됐으나 아직 검토하지 않은 실험 쪽 변경 = 결과 `astra_motion.md` 5절 Qwen 판본 줄(28회차 E-N13 정정) 하나. E-CAM3·E-MA3 결과는 0cc45ae까지 커밋되지 않아 **범위 밖** — 두 실험의 예측·평가 파일은 **열지 않았다**(폴더·파일 이름과 시각만).
- 사본: `git -c core.autocrlf=false archive 0cc45ae`(tar 주석 = `0cc45ae2d128…`)를 Python tarfile로 `D:\tools\scratch_qdd\r7c29\repo`에 풀었다(**590파일**, 텍스트 538파일 CR 0). 파드 사본 = 같은 archive를 `kubectl exec -i … tar -xf -`로 `/data/harvest/tmp/r7c29/code`(591파일 = + `CODE_VERSION`), 텍스트 CR 0, 올린 스크립트 CR 0(올릴 때마다 확인). 파드 산출 `meta.git.commit` = `0cc45ae2d128…`, dirty false.
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle21.md`–`r7_cycle28.md`, 정본 `00-interfaces.md` §1–§86 보충(뒤 절 우선), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록(28회차 목록), 결합 설계 스펙 §12·§17, 기록책 README 규칙(`:8`–`:11`)과 02-pitfalls P01–P69.
- 분류(28회차와 같음): **DEFECT** = 코드가 사전 등록·정본과 다르게 동작하고 그 차이를 정한 정본 결정이 없는 것, 또는 완료 정의 1–5를 깨는 것. **DOC** = 현재 시제 서술이 커밋·정본·결과 문서·원자료와 다르고 정정 표시가 없는 것. 정본이 "나중에 할 일"로 적은 것은 SCOPED. 뒤 절이 덮는 문장, 출처 표기만 어긋난 요약(값은 맞음), 추정 표시(≈·약)가 있는 수치, 반올림 차이는 NOTE.
- 규칙 준수: 저장소 수정·커밋·푸시 없음(git은 `-c safe.directory=D:/qdd`로만; 이 보고서 한 파일만 씀, 커밋 안 함). 로컬 임시 = `D:\tools\scratch_qdd\r7c29`(C: 쓰기 없음). 스크립트는 전부 Write 도구로 쓰고 경로로 실행(heredoc·`cat >`·`python -`·`python -c` 없음 — 한 번 28회차 스크립트를 `sed`로 이름만 바꿔 복사했다가 **실행 전에 모두 지우고** Write 도구로 다시 썼다, N115). 파드 = `juhyoung-native-7a2a`, 작업 폴더 `/data/harvest/tmp/r7c29`, `source /data/harvest/env.sh`, 모든 kubectl에 `MSYS_NO_PATHCONV=1`(끝에 `/C:` 없음 확인). GPU: Isaac = GPU 1에 **내 프로세스 하나**(`IR_ROOT=cyclo`, `IR_INST` `r7c29_standard`, `--inst-prefix r7c29`; GPU 0·1의 R2_TRAIN 워커 5개는 건드리지 않음), GPU 2·3(E-CAM3·E-MA3 학습)에는 아무것도 올리지 않음. CPU: `nice 10`·`OMP_NUM_THREADS=2`·`OMP_WAIT_POLICY=PASSIVE`. 시드 DEV·POOL만. 유료 API 없음. 비밀값 출력·검색 없음.

## 판정 (기준선): **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 3 |
| SCOPED | 21 |
| NOTE | 77 |

## 판정 (실험 코드 절, 카운트와 별개): **PASS — 코드 결함 0, DOC 0**(NOTE E-N19)

**기준선 코드는 28회차 대상(47edadb)과 바이트가 같다**(0cc45ae는 문서만). 회귀: 로컬 **1133 passed / 20 skipped**(Git Bash, 231.0 s), 파드 CPU **1280 passed / 4 skipped**(175.7 s), LeRobot 6 passed; 가드 **28건 + 실험 옵트인 4건 = 32건** 모두 rc ≠ 0이고 거부 사유가 맞다(21–28회차와 다른 경계값); R2 DEV `validate_episode` **36/36** + **새 종류 음성 대조 12종**(경계 안 시각 오차 −9.9e-7 s는 통과; −1.5e-6 s·프레임 빠짐·마지막 프레임 손목 크기·머리 영상 없음·라벨 행 추가·행 필드 없음·`action_script` NaN·`valid[0]=0`·proprio 길이·npz `qd` 길이·`action` NaN·`hold_n` −1 — 모두 검출); 모의 평가 한 명령씩(e05·rd·calib·`--truth outcome:plan`) 완료; 새 시드 **DEV 9**에서 같은 Isaac 워커 C5 → C5' 행동 **1,384개 비트 동일**(첫 차이 없음, 시각열 동일). **28회차 정정 주장 대부분은 diff와 맞고 원자료로도 참이다**(§6.2): `ma1.md:15` 두 번째 정정(P0 파일 = 12:19:47–12:20:23Z 파일럿 병합, 과제당 19–41시드, 600편 병합 없음), 02 P63 칸·P69, 03 §86 보충 행(20 s = 탐침 `STREAM_TIMEOUT_S`, 시뮬 초), 스펙 §17(0절 12–16 s·5절 편 평균 11.6/14.1 s·시뮬 초), 06 `:12`(칸 안)·`:16`(40895f8 = 20:34:19 UTC), handoff·draft-log·direction-log의 27회차 시각(47edadb = 20:37:43 UTC), 04 `:16`(3500f54에 15파일)·`:54`(`ckpt/ma1b` = `a3d_s1`·`a3d_s2`).

**DOC 3건(기준선)** — 셋 모두 28회차의 "상태는 handoff에만"(P69) 구조 조치 자체가 반만 적용된 것이다(P68 세 번째 재발): **D-1** 책 `01-experiments.md:67` R2_TRAIN 줄의 **상태 칸이 여전히 `[진행 중]`** — 같은 커밋이 README `:8`에서 "`[진행 중]` 폐지", `:11`에서 "상태 칸은 `예정`·`끝`·`중단`처럼 커밋으로 바뀌는 값만", 06 `:20`에서 "README·01·05 상태 표기 통일: `[진행 중]` → `[결과 전]`"이라 적었다. **D-2** 책 `04-map.md:61` 새 정정 "폴더의 `P*.stageb.jsonl`은 12:20Z 파일럿 병합분(**과제당 시드 19–41개**)뿐" — 19–41은 P0 파일에만 맞고 P1 파일은 과제당 11–19시드, P2 파일은 10–20시드다(파드 `rows29.py`, 21:12Z). **D-3** 책이 현재 상태를 handoff로 넘긴다("지금 진행 상황은 handoff" `01:4`, "지금 상태는 handoff" `01:67`, "지금 상태는 `docs/handoff.md`" `04:3`, "handoff 참조" `04:61`, README `:11`)는데, 0cc45ae의 handoff에는 **R2_TRAIN 진행 상태·E-CAM3·E-MA3 진행 줄이 없다**(28회차 N93이 이미 적은 누락; 구조 조치가 상태를 책에서 빼기만 하고 handoff에 넣지 않았다). **연속 무결 0 유지.**

---

## 1. DEFECT

없음. (0cc45ae는 코드·시험을 바꾸지 않았다 — `git diff --name-status 47edadb 0cc45ae`에 `harvest/`·`tools/`·`tests/` 경로 0, `check29` H1.)

## 2. DOC

- **D-1. `docs/book/01-experiments.md:67` — R2_TRAIN 줄 상태 칸 `[진행 중]`이 남았다(폐지한 표기, 현재형 진행 상태).** 같은 줄의 결과 칸은 `[결과 전]`으로 바뀌었지만 다섯째(상태) 칸은 `` `[진행 중]` ``그대로다(`check29` H7: 표 D에서 상태 칸이 `[진행 중]`인 행은 이 하나). 같은 커밋의 규칙·기록과 모순: README `:8` "시작했으나 결과 문서가 없으면 `[결과 전]` … [→ … P69: `[진행 중]` 폐지]", README `:11` "실험 장부의 상태 칸은 `예정`·`끝`·`중단`처럼 커밋으로 바뀌는 값만 쓴다", `01:4` 범례(끝 / 중단 / `[결과 전]` / `[예정]`), 06 `:20` "README·01·05 | 상태 표기 통일: `[진행 중]`·'생성 중' → `[결과 전]`". 과제에서 요구한 "`docs/book/*`에 인용 이력(02·06) 밖 현재형 진행 상태 없음"을 깨는 유일한 칸이다(`grep -nE '진행 중|생성 중|작업 중|미커밋' docs/book/*.md` → 01 `:67` 상태 칸, 나머지는 02 P14·P68·P69·P60과 06 `:15`·`:16`·`:20`의 이력 인용뿐). **고칠 것**: `01:67` 상태 칸을 `` `[결과 전]` ``로(결과 칸의 괄호 설명은 그대로), 같은 커밋에 06 줄.
- **D-2. `docs/book/04-map.md:61` — 28회차 정정 문장의 시드 수가 P1·P2 파일과 다르다(P68 재발).** 문장: "폴더의 `P*.stageb.jsonl`은 12:20Z 파일럿 병합분(과제당 시드 19–41개)뿐이고 600편 전체 병합(`gen check`/merge)은 아직 돌지 않았다". 파드(읽기만, `rows29.py`, 21:12Z): 18개 파일 mtime 2026-09-25 12:19:47–12:20:26Z(✓), **P0** 파일 과제당 19·30·30·26·40·41시드(범위 10000–10041, ✓ 19–41), **P1** 파일 11·19·19·11·19·19시드(10600–10619), **P2** 파일 10·20·20·10·20·20시드(10800–10819) — `P*` 전체로는 "19–41"이 12개 파일에서 틀리고, 과제당 세 종류 합(40·69·69·47·79·80)으로 읽어도 틀리다. 같은 정정의 원천 `ma1.md:15`는 "과제별 `P0.stageb.jsonl`은 … 19–41개"로 P0에 한정해 바르다 — 04로 옮기며 범위를 `P*`로 넓히면서 수만 그대로 가져왔다. (병합 없음은 참: `check.json` mtime 12:20:26Z, `r2train/logs/*.log`에 MERGE·CHECK 줄 0, 21:23:01Z에도 12:21Z 뒤 바뀐 폴더 행 파일 0 — `r2cwd29.sh`.) **고칠 것**: "`P0.stageb.jsonl`은 … 과제당 19–41시드(P1 11–19·P2 10–20)" 식으로 종류별로 적거나 P0에 한정하고, 근거 명령(`rows29.py`의 파일별 줄 수·시드 수·mtime)을 함께 적는다(P63 규칙). 06 줄.
- **D-3. 책의 "지금 상태는 handoff" 안내가 가리키는 곳이 비어 있다 — `docs/book/01-experiments.md:4`·`:67`, `04-map.md:3`·`:61`, `README.md:11` 대 `docs/handoff.md`.** 28회차 구조 조치(P69 "진행 상태는 handoff 한 곳에만")로 책은 E-CAM3·E-MA3·R2_TRAIN의 진행 상황을 handoff로 넘겼다: `01:4` "`[결과 전]`(시작했으나 결과 문서 없음 — **지금 진행 상황은 handoff**)", `01:67` "생성 뒤 병합·검사 필요 — **지금 상태는 handoff**", `04:3` "지금 상태는 `docs/handoff.md`", `04:61` "진행 상태는 이 장에 적지 않는다(handoff 참조)". 그러나 0cc45ae의 handoff(비지 않은 줄 115)에서 `E-CAM3|E-MA3|cam3|ma3`는 `:127`의 "실험 절 PASS(탐침 정정·E-CAM3/E-MA3 등록 확인)" 한 번뿐이고 두 실험의 시작·GPU·진행 줄은 없다; R2_TRAIN은 `:93`(§66 시드 영역)·`:108`(11:14 UTC "하드 리셋 빌드로 재기동")·`:122`(E-MA1b 뒤 재등록)·`:127`(N94 운영 주의)뿐으로 어느 종류가 끝났고 무엇이 진행 중인지(파드 21:11Z: P0·P1 600·200편 끝, P2 107–155/200 생성 중, 병합 전) 적힌 줄이 없다. 28회차 N93이 "handoff에 진행 중인 E-CAM3·E-MA3 줄이 없다"를 NOTE로 남겼는데(당시엔 규칙이 없었음), 이번 커밋이 규칙과 안내를 만들면서 그 줄을 채우지 않아 안내가 거짓이 됐다. **고칠 것**: handoff에 "진행 중 작업(UTC 시각)" 절을 두고 R2_TRAIN(종류별 끝·진행, 병합 여부)·E-CAM3(GPU 2, 사전 등록 5c46056)·E-MA3(GPU 3, 40895f8) 줄을 시각과 함께 넣는다; 결과가 커밋되면 그 줄을 지우는 것을 결과 커밋 규칙에 더한다.

(검토했지만 DOC로 올리지 않은 후보: ① `04:61`의 "600편 전체 병합은 **아직** 돌지 않았다"는 같은 문장의 "진행 상태는 이 장에 적지 않는다"와 어긋나는 현재형 상태지만 21:07 UTC 표시가 붙은 정정 안에 있고 지금도 참이다(21:23:01Z) → N102. ② 28회차 줄의 "보고 21:02 UTC"(handoff `:127`, draft-log `:479`, direction-log `:75`)는 28회차 보고서 머리의 작성 시각 21:05 UTC와 다르다(21:02:35Z는 파드 정리 끝) → N103(P11 계열, 28회차 N86과 같은 종류). ③ `01:38` R7 행 "1–27회차"가 28회차 보고서를 더한 커밋에서 "1–28"로 늘지 않았다 — 적힌 사실은 참 → N105.)

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(§71 보충) — 로컬·파드 `test_latency_ctrl.py:11` 건너뜀.
- S2. 본 단계 B·R2_TRAIN 대량 생성(§66, §77 N8 (4)) — 파드 R2_TRAIN Isaac 워커 5개 진행 중(21:11Z, `gen gen --kinds P2 --seeds 10800-10999 --confirm-train`, standard 3·dr 2, GPU 0·1; P2 편 107–155/200; 읽기만); 확인 인자 없는 `--seeds 59998` 거부(가드 19). 폴더 행 병합은 아직(D-2·N94).
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
- S14. §77 "보류(DOC)" `harvest/sim/snapshot.py:31` 주석 — 0cc45ae에 그대로.
- S15. §79 보충: 런타임 `M4Params.flip_th` 질문별 사전화.
- S16. §78 "남은 것": dr·random 변형, CUDA PhysX, P2의 결정성 행렬.
- S17. §78 (2): 옛 물리 녹화의 재녹화·재라벨 방식은 R2_TRAIN 뒤 결정.
- S18. 정본 §82 구현 및 §84·§86(+보충) 결합 설계 구현 — "R7 E2E 준비 기준점 뒤". 지금 코드: 파드 `closed --hb-mode k0`·`"K-1"` → 워커 전 거부(가드 26·27), Astra 요청 이미지 1장·effort low·600(DEV 9 Astra 4행), 흐름 호출 없음.
- S19. 정본 §83 런타임 적용(새 직렬화 판본) — DEV 9 결정 호출 요청 84/84 `motion:` 없음.
- S20. **E-CAM3·E-MA3 결과**: 21:17Z에도 학습 중(`logs/cam3/cam3_s1.out`·`logs/ma3/kv_s1.out` 21:17Z 갱신, `ckpt/cam3/cam3_s1`·`ckpt/ma3/kv_s1`) — 결과 커밋 없음, 예측·평가 파일은 열지 않았다(실험 절 7.3).
- S21. 탐침 E-Astra-motion 결과의 E-Couple 재측정(§86).

## 4. NOTE
- N1–N3. (그대로) `stageb_train predict`·`evalck`의 `prompt_config` 비대조, `cli_label.replay_max` NaN 순서, 판정 스크립트 입력 검사 수준(책 P25).
- N4. (해소, 27회차와 같음).
- N5–N11, N13–N21, N23, N26, N28–N30, N34, N36, N38, N39, N45. (그대로, 28회차 목록.) N10 재현: 가드 25(`e05 --data jsel_dev/P1 --split pool --seeds 2097` → "no episode selected")가 빈 `g25/`를 남김.
- N46. (그대로) `RESUME_KEYS`의 `a3d_root`.
- N47·N48. (해소, 27회차와 같음.)
- N49–N52. (그대로.)
- N53. (그대로.)
- N54. (해소.)
- N55. (일부) `04:61` → D-2; `01:12`·`01:20` 그대로, `01:67` → D-1.
- N56. (해소, 이력.)
- N57, N58. (그대로.)
- N66·N67. (해소.) 다만 `01:38` 행 이름 → N105.
- N68. (해소) `06:12` 표시가 넷째 칸 안(칸 4 = 머리, `check29` H3).
- N69, N70, N72. (해소, 28회차와 같음.)
- N71. (그대로) 정본 §85 보충이 §86 본문 뒤 — 책 03 `:70`이 밝힘.
- N73. (그대로) 정본 §66 `:563` "본 생성 계획(아직 실행 안 함)".
- N74. (그대로) 스펙 `:123`·`:130`·`:180`·`:185` "[→ §17]" 꼬리표 권함.
- N79. (그대로) 계획 PROBE 표의 `request_mode "F1"`·`stale_edit_s 6.0`·`latency_init_s 3.0` 자리표시와 `timeout_s 20.0`이 섞임.
- N84. (해소) `06:12` 표시가 칸 안으로(0cc45ae, 칸 수 4).
- N85. (해소) `06:16`에 "40895f8 시각 20:34:19 UTC — 줄 시각이 커밋보다 늦음" 표시(값 = `git show -s` 20:34:19 UTC).
- N86. (해소) handoff `:126`·draft-log `:478`·direction-log `:74`의 27회차 시각 = 정정 커밋 47edadb 20:37:43 UTC. (28회차 줄의 새 시각 → N103.)
- N87. (해소) 책 `03:71` §86 보충 행(20:37, 20 s·F0 = 정본 `:778`, 칸 4).
- N88. (일부) 스펙 §17 `:199`가 "0절 요약 — 5절 표는 편 평균 F0 11.6 s·F1 14.1 s; 탐침의 20 s는 시뮬 초"로 바로잡혔고 책 03 `:71`도 "탐침에서는 시뮬 초"를 적었다(값 = 결과 `:6`·`:54`–`:55`·`:57`, `harness.py:45`·`:539` `t - send_t > STREAM_TIMEOUT_S`의 `t`는 시뮬 시각 ✓). 정본 `:778`은 여전히 "탐침 실행기와 같음"만 적어 책·스펙이 정본보다 자세하다 — 다음 정본 보충 때 한 구절.
- N90. (그대로) 책 04 지도에 `se2e_cam3.py`·`se2e_kvcond.py`·`tools/cam3|ma3/`·`paired_verdict.py`·파드 `code_cam3|ma3`·`ckpt/cam3|ma3`·`data/cam3`이 없다(28회차 D-2 권고의 "새 파일·경로" 보충이 안 됨).
- N91. (그대로) P68·P69(기록·커밋 주제)가 다. 절 P67 뒤.
- N92. (해소 → D-1) `01:67`의 옛 "생성 중 … 17:3x" 문장은 `[결과 전]`으로 바뀜; 남은 상태 칸은 D-1.
- N93. (→ D-3) handoff에 E-CAM3·E-MA3 줄 없음 — 이번 커밋이 책 안내를 handoff로 돌리면서 DOC가 됐다.
- N94. (그대로, 운영 위험) R2_TRAIN 폴더 행 파일 18개가 여전히 12:19–12:20Z 파일럿 병합(21:23:01Z 확인). 0cc45ae가 handoff `:127`·책 `04:61`에 "학습 전 필수: 생성이 끝나면 병합·검사" 경고를 더했다(✓) — 단계 B 사전 등록 전 행 수 대 편 수 확인 단계 권고는 그대로.
- **N102.** `04:61` "600편 전체 병합(`gen check`/merge)은 **아직 돌지 않았다**" — 같은 문장이 "진행 상태는 이 장에 적지 않는다"고 하면서 현재형 진행 상태를 적었다. 21:07 UTC 정정 표시 안이고 지금도 참(병합 흔적 0, 21:23:01Z)이라 NOTE지만, 병합이 돌면 바로 낡는다(P69가 막으려던 모양). "12:20Z 기준" 식으로 시각을 문장에 넣거나 handoff로 옮긴다(D-3과 같은 커밋).
- **N103.** 28회차 줄의 시각 "보고 2026-09-25 21:02 UTC"(handoff `:127`), "21:02 UTC"(draft-log `:479`), "21:02"(direction-log `:75`) — 28회차 보고서 머리는 "작성 2026-09-25 21:05 UTC(`date -u` 21:05:28Z; … 파드 정리 끝 21:02:35Z)"다. 21:02는 파드 정리 끝 시각이다(P11 계열; 28회차 N86을 고친 바로 그 커밋에서 새 근사 시각).
- **N104.** P69 증상 칸 "R7 DOC가 반복(26·27·28회차)" — 상태 꼬리표 DOC는 27회차(D-1)·28회차(D-1·D-2)다; 26회차 DOC는 R7 PASS 회차 누락(`r7_cycle26.md:36`)이고, 26회차 **정정**(dc945bf)이 27회차 D-1의 상태 문장을 만들었다. "26회차 정정이 만든 꼬리표 → 27·28회차 DOC"가 정확하다.
- **N105.** `01:38` "R7 객관 검증 1–27회차" — 28회차 보고서(`r7_cycle28.md`)가 같은 커밋에 들어왔는데 행 이름·PASS 목록 범위가 1–27로 남았다(27회차 N67 때는 보고서 커밋과 같이 늘렸다). 적힌 사실은 1–27회차로 참이라 NOTE; "회차별 줄은 handoff §2.8"로 이미 넘기므로 행 이름에서 회차 범위를 빼면 매 회차 갱신이 필요 없다.
- **N106.** `04:3` "확인 시각 2026-09-25 18:4x UTC"가 그대로다(28회차 D-2 "`:3` 확인 시각 갱신" 권고 미반영). 장이 "위치만"으로 바뀌었지만 `:16`·`:54`·`:61`에 21:07 UTC 사실이 들어 있어 장 머리 시각이 내용보다 이르다.
- **N107.** 책 01 표 D(`:56` 머리 "ID | 질문 | 등록 | 결과 | 상태")의 상태 칸에 E-CAM3 "설계 §12", E-MA2 "연구 문서 §6.2", E-MA3 "정본 §84", E-SR0 "설계 §9", E-Couple "[계획]", E-Astra-necessity "정본 §82"가 들어 있고 `[결과 전]`·`[예정]`은 결과·등록 칸에 있다(`check29` H7) — 오래된 배치라 README `:11` "상태 칸은 예정·끝·중단…"을 기계적으로 검사할 수 없다; 또 README `:11`의 값 목록(예정·끝·중단)과 `01:4` 범례(`[결과 전]` 포함)가 조금 다르다. 칸 정리 권함.
- **N108.** `ma1.md:15` 두 번째 정정은 사실로 맞다(파드: P0 파일 12:19:47–12:20:23Z, 19–41시드, 편 600개씩 standard 17:02Z·dr 18:08Z 끝, 병합 없음; 원문 17:3x "작업자 5개가 P0" = standard P0이 17:02Z에 끝난 뒤 w1·w3·w5가 dr P0로 넘어감 — `r2train/logs/w{1,3,5}_dr_P0.log`, 17:25–17:45Z에 끝난 편은 dr P0 폴더뿐 `epoch29.py`). 다만 P63 예방 규칙 "판단 근거 명령을 결과 문서에 적는다"를 이 정정 자체가 따르지 않았다(근거는 `r7_cycle28.md` D-1에만). "12:20Z"는 12:19:47–12:20:23Z의 근사.
- N109–N115: 이번 회차 자체 기록(아래; 28회차 N95–N101 자리를 대신함).
- **N109.** 텍스트 위생: 사본 텍스트 538파일 CR 0; 변경 md 14개 BOM·C0·C1·영폭 0, **표 칸 수 불일치 0**(`check29` H3 — 코드 구간·이스케이프 파이프 제외); 책 링크 101개 끊김 0(H4); `prereg_hash --check` OK(H2). 책을 고친 커밋(4117851 이후 11개) 가운데 같은 커밋에 06 줄이 없는 것은 641547e 하나(27회차 N56, 6483397이 보충) — 0cc45ae는 06 `:19`·`:20` 두 줄(21:07 ≤ 커밋 21:07:54 ✓).
- **N110.** 시험 수: 로컬 **1133 passed / 20 skipped**(231.0 s, 21:10:19–21:14:11Z, Git Bash, `-o addopts="-p no:cacheprovider"`, `-o tmp_path_retention_policy=failed`, basetemp `r7c29/pt`, `PYTHONDONTWRITEBYTECODE=1`; 건너뜀 = torch 15·isaaclab 1·LeRobot pyarrow 1·inspect_robots 2·TODO 1), 파드 CPU **1280 passed / 4 skipped**(175.7 s, EXIT 21:17:17Z; 건너뜀 isaaclab·pyarrow 경로·CUDA·TODO), 경고 1(기존), LeRobot 6 passed(18.6 s). 28회차와 같은 수(코드 무변경).
- **N111.** 단계 B 소형 CPU 스모크(21:20:25Z): 총손실 처음 5 평균 3.055168 → 끝 5 2.902712(21–28회차와 같은 값 — 결정적), expert p50 0.034 s·전체 p50 0.111 s, 맥락 토큰 454.
- **N112.** DEV 9 판: 행동 1,384·13.84 s·결정 호출 42(조건마다), C5 `last_step` {none 1, OK 30, LAG 7, DEVIATE 4}, C5' none 42/42, 확정 비율 0.9333, 결정 3.037/s, rtf 0.369, 지연 p50·p95 0.3 s, Astra 2(hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0), `hb_mode` K2, `code_sha` `df7fcd9234b49658`(28회차와 같음 — 코드 무변경), 파일명 `dev9-P0-standard-e0`, 판 237.9 s(21:18:11–21:22:09Z).
- **N113.** 파드 GPU(21:11Z·21:22Z): 0 = R2_TRAIN 워커 2(dr P2, 8.1 GiB), 1 = R2_TRAIN 워커 3(standard P2, 12.2 GiB; + 내 Isaac 21:18:11–21:22:09Z), 2 = E-CAM3(`se2e_cam3 train`, 20:42:33Z 시작, 86.8 GiB), 3 = E-MA3(`se2e_kvcond train`, 20:45:13Z 시작, 87.5 GiB).
- **N114.** 파드 정리 대상 판별(`attr29.sh`): 내 Isaac 창(21:18:11–21:22:09Z)에 생긴 `tmp/carb.UHGew8`(21:18:12 생성, Kit 임시)·`tmp/tmpko8deq87`(21:18:29, `_remote_module_non_scriptable.py`; `.pyc`가 `cache/pyc_r6` 아래 = 내 워커의 접두)·`pyc_r6/…/r7c29`(21:18:11, 772 KB)·`kitcache/cyclo-r7c29_standard`(21:18:11, 208 MB). 그 시각 `TMPDIR=/data/harvest/tmp`인 다른 프로세스는 E-CAM3·E-MA3 학습 2개와 GPU 감시 `nvidia-smi` 2개뿐이고 모두 `PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc`(pyc_r6 아님)·21:18Z 전 시작 → 두 임시 항목은 내 것.
- **N115.** (절차, 내 쪽 자체 점검으로 다시 설계한 것) ① 28회차 스크립트를 `sed`로 이름만 바꿔 `r7c29/pod/`에 복사했다 — 규칙("sed 생성 스크립트 금지") 위반이라 **아무것도 실행하기 전에** 모두 지우고 Write 도구로 다시 썼다. ② 가드 요약 줄의 `grep -o` 첫 일치가 16번에서 엉뚱한 문자열("finite > 0")을 집었다 — `gtxt29.sh`로 각 가드 로그의 마지막 오류 줄을 따로 읽어 32건 사유를 모두 확인했다(16번 = `condition "C6'": runtime has [...]`). ③ `attr29.sh`의 "r7c29 명령줄 프로세스 2"는 명령 치환 하위 셸의 자기 매칭이다 — 정리는 명령줄에 r7c29가 없는 `bash -s`(표준 입력)로 돌려 0을 확인했다. ④ R2_TRAIN 워커의 코드 폴더(`code_r2train_e8e1864`, 책 `01:67`)는 `/proc/<pid>/cwd`로는 보이지 않아(`/data/harvest/ir`, rootfs) 다시 확인하지 못했다 — 28회차의 `run.sh` 확인값을 따른다. ⑤ LeRobot 왕복은 이번에 두 편 모두 `valid_for_training` 참이라 "무효 편 건너뜀" 경로는 이번 회차에 다시 확인하지 않았다(28회차 확인).

---

## 5. 사전 등록 대조표 (행마다 이번 회차의 행동 확인)

`prereg.json` 해시: 로컬 `tools/prereg_hash.py --check` **OK**(`check29` H2), 파드 산출 `meta.prereg.check` = OK. 28회차 표의 행 번호를 그대로 쓴다. 기준선 코드 = 47edadb와 같음(H1). "확인" 열: **로컬** = `D:\tools\scratch_qdd\r7c29\check29.py`(H1–H7), **파드** = §6(`pod_cpu29.sh`, `pod_eval29.sh`·`data29.py`·`gtxt29.sh`·`show29.sh`, `pod_isaac29.sh`·`closed29.py`, `exp29.py`, `rows29.py`·`rows29b.sh`·`epoch29.py`·`r2cwd29.sh`, `attr29.sh`·`clean29.sh`).

| # | 사전 등록 값·절차 (출처) | 구현 | 확인(구성 입력 → 출력) | 판정 |
|---|---|---|---|---|
| 1 | 시드 분할 DEV/CAL/TEST/TEST-P5/POOL/R2_TRAIN (E :113-120, §66) | `eval/splits.py`, `datagen/gen.py` | 가드 28건 rc ≠ 0(§6.4): TEST 1003·1126, CAL 548·501·544, TEST-P5 1325·1302, DEV 14,40·2050, POOL 1998, gen 59998(확인 없음)·9990·60500(확인 있음), determinism 31·1999 | 일치 |
| 2–4 | POOL 과표집·`ambiguous` 띠·에피소드 분할 (E :121-122) | `sim/snapshot.py`, `calib.halves` | 코드 무변경; `calib --heldout jsel_dev/P1 --episodes 2` → `CALIB_DONE`; 가드 3(`--fit-split test`)·4(`--heldout-split test_p5`) 거부 | 일치(S14) |
| **5** | 성공 1 s 연속·60 s·낙하 즉시 실패 (E :107) | `sim/planner.py` | 파드 Isaac **DEV 9** C5·C5' 성공(13.84 s, `terminations` success 1) | 일치 |
| **6** | 호출 기록·Astra A6 (E :125-126, §28) | `core.py` | **DEV 9 결정 호출 84행**(조건마다 42): 요청 blob 해시·이미지 해시 포함·응답 blob·`probs`·`canary_id`·`question_id@vN` 84/84; Astra 4행 해시·effort low·600·이미지 1장·`output_text` 4/4 | 일치 |
| 7–12 | 군집 부트스트랩 10,000, Holm, 판정 절 해시 | `analysis/stats.py`, `eval/common.py` | 파드 `meta.bootstrap` 10000·seed 0·percentile; `meta.prereg` OK; 시험 묶음 | 일치 |
| 13–17 | 카나리 기준일, 모델 식별 필드, E0.5 | `eval/canary.py`, `e05.py` | `e05 --data jsel_dev/P2 --split dev --episodes 2` → `E05_DONE`; 가드 24(`canary build-set --seeds 3050-3051`) 거부 | 일치(N11) |
| 18–50 | γ 2/3, `C_flip`, 판정 1–10, FLIP_TH, ECE, J5 q̂, N_max·d̂ | `m4`, `stats`, `calibration` | 코드 무변경·시험 묶음; `meta.m4_H`·`m4_lead_max` 3·1.0 | 일치 / SCOPED S5 |
| **51–58** | STALE_MAX, C0–C6, C5·C5', H, n_LA (M4 §4, §75, §77) | `m4`, `conditions`, `core.b_line` | 가드 16 `--conditions "C5,C6'"` → "condition \"C6'\": runtime has ['C0' … 'C6']"; **DEV 9 C5 `last_step` {none 1, OK 30, LAG 7, DEVIATE 4}, C5' none 42/42, 요청 본문 마지막 `last_step:` 줄 = 행 값 84/84** | 일치 |
| 59, 63–65 | W 2, H1–H3, M4b, E-M4-lat | 없음 / `m4b/*` | §73 D5, §71 보충, §74 보충 | SCOPED S9·S1·S11 |
| 60 | 라벨 규칙 | `sim/labeler.select_rule` | 코드 무변경·시험 묶음 | 일치 |
| 61–62 | RD 재표집 (EVAL :182-184) | `rd.py` | `rd --variants standard=jsel_dev,dr=gen_dev/dr/P2 --episodes 2` → `RD_DONE`(dr 낙폭 평균 0.0, n 275); 가드 5 `rd --variants dr=… --split test` 거부 | 일치 |
| **66–67** | `lead_max` 유한 양수 (§75, §76 N4) | `m4.py`, `closed.py` | 가드 14 `--m4-lead-max=nan` → "lead_max = nan … finite > 0", 15 `=-1e-9` → "lead_max = -1e-09 … finite > 0", 워커 전 거부 | 일치 |
| 68–94 | E0 판정 4, E-M4 판정 7, 카나리 표류, (b) 범주, `last_step` | `latency`, `canary`, `core`, `serialize` | 행 6·54; 시험 묶음 | 일치 / SCOPED S12·S13·S6 |
| 95–97, 105–136 | S-E2E·진단·E-TC·움직임 줄 확인 | `tools/se2e/*`, `se2e_temporal*.py` | 코드 블롭 불변(H1); 파드 `se2e_c1` `sha256sum -c` **5/5 OK**(21:22Z) | 일치 |
| **98, 100, 118, 132** | 라벨 신뢰 = 재생 비트 동일 (§78, §80 D1) | `stagea_data.replay_bit_identical`, `eval/common.load_truth` | `e05 --split pool --seeds 2002,2049,2093 --truth outcome:plan` → `E05_DONE`(claim `a_as_stabilizer`) | 일치 |
| **99** | 에피소드마다 PhysX 장면 재생성 (§78) | `sim/scene.py` | **Isaac 한 워커 C5 → C5'(DEV 9, 21:18:11–21:22:09Z)**: 행동 **1,384개 비트 동일**(첫 차이 없음, 시각열 동일), 호출 42·Astra 2 같은 수·같은 시각 | 일치(S16) |
| 101 | R2_TRAIN = 하드 리셋 빌드 (§78 (2)(3)) | 파드(읽기만) | R2_TRAIN 워커 5개 P2 진행 중(21:11Z); 코드 폴더는 28회차 확인값(N115 ④) | 일치 / SCOPED S17 |
| **102, 120** | 빈 입력·0편 거부, 시드 검사가 `--out` 앞 | `common.load_episodes`, `sim/determinism.py` | 가드 22·23 → "only DEV 0-29 and POOL 2000-2119" 폴더 없음; 24·25 → "no episode selected" | 일치(N10) |
| 103–104 | Isaac 워커 PASSIVE, qid 등록부 | `closed.worker_cmd` | 내 워커 `CLOSED_DONE`; 가드 12·13 `--isaac-gpu 7`·`10` → "0 or 1 only" | 일치(N34) |
| 137 | Astra 주기·in-flight 1·low·600 (§45, §82 보충 2) | `runtime/astra_hb.py` | DEV 9 hb 5.0 → 8.0, sub 8.01 → 11.01, 겹침 0 | 일치 |
| 138 | LeRobot v2.1 내보내기 | `datagen/lerobot_export.py` | **새 2편**(standard/mug_tray/P0 ep2·dr/bottle_tray/P0 ep4, 모두 참): 2편·637프레임, `verify` 오류 0·PSNR 최소 35.06 dB·lerobot 0.3.3 적재 637프레임·fps 30·머리 [3, 376, 672]·손목 [3, 240, 424]·`action0_equal` 참 | 일치 |
| **139** | R2 DEV 구조 검사 (§66, 완료 정의 1) | `datagen/validate.py` | **36/36 오류 없음**, 검증기 대 메타 `valid_for_training` 불일치 0; **새 음성 대조 12종**(standard/mug_tray/P0 ep5, 289프레임): 무수정 오류 0; k144 시각 −9.9e-7 s → 오류 0; −1.5e-6 s → "off the 30 Hz grid by 1.50e-06 s"; k144 줄 삭제 → "frame indices not contiguous from 0"(+ 행·npz 길이); k288 손목 ← 머리 JPEG → "k288 cam_wrist_right: size (672, 376) != native (424, 240)"; k96 머리 경로 없음 → "k96: missing cam_head"·"images 577 != frames 289 x cams 2"; 라벨 행 추가 → "labels_v2 rows != decision frames"; k144 `skill_id` 삭제 → "missing field 'skill_id'"; k72 `action_script` NaN → "action_script: … finite"; k57 `valid[0]=0` → "valid: … first step valid"; k48 `proprio.q` 한 값 줄임(7 → 6) → "proprio.q: 7 values"(기대 길이 7); npz `qd` 290 → "npz qd: length 290 (want 289)"; `action` NaN → "npz action: … non-finite"; `hold_n[0]` −1 → "hold_n does not add up" | 일치 |
| **140–141, 152** | 정본 §82·§84·§86(+보충) 구현, §83 런타임 적용 = "R7 관문 뒤" | 없음 | 가드 26·27, 요청 `motion:` 없음 | SCOPED S18·S19 |
| 151 | §82 보충 2: 실행 중 effort = low | `astra_hb.EFFORT` | DEV 9 Astra 4행 effort low | 일치 |
| 153 | 정본 §85: 유료·GPU 실험 = 자체 검사 | — | 이번 대상에 새 유료·GPU 실험 등록 없음 | 일치 |
| 154 | 기준선 파일 `stageb_train.py` 기본 경로 불변 | — | 0cc45ae 코드 변경 0(H1); 옵트인 가드 28–32(argparse·install 단계 거부) | 일치 |
| **155** | 책 `docs/book/` 현재 서술·수치 = 출처 | — | §6.3: 링크 101개 끊김 0, 04·01 수치 파드 원자료 대조, 06 갱신 줄 전수 | **DOC D-1·D-2·D-3** / NOTE N102–N108 |
| **156** | 정본 §86 = 탐침 결과 + §86 보충(`:778`) | — | 보충의 20 s = `harness.STREAM_TIMEOUT_S`(시뮬 초, `:539`), 11.6/14.1 = 5절 표(편별 평균 `:57`), 12–16 s = 0절 `:6` | 일치(N88) |
| **157** | 사전 등록 E-CAM3·E-MA3 판정·데이터·경로 | `se2e_cam3`, `se2e_kvcond`, … | 28회차 X9–X16 뒤 코드 무변경; 가드 29–32 거부; 결과 커밋 없음(S20) | 일치 |

### 5.1 28회차 표와의 차이
- 근거 교체: 행 1(새 경계 가드 28건), 5·6·51–58·99·137·151(DEV 9), 13–17·61–62(jsel_dev/P2·dr/P2), 2–4(jsel_dev/P1), 66–67(`nan`·`-1e-9`), 98(POOL 2002·2049·2093), 138·139(다른 편·새 음성 대조 12종), 153(새 등록 없음), 154(코드 무변경), 157(결과 전).

## 6. 확인한 것 (근거)

### 6.1 변경분
- `git diff --name-status 47edadb 0cc45ae`: 코드 0. 문서 = 책 README +2/−1, 01 +5/−5, 02 +2/−1, 03 +1, 04 +4/−4, 05 +1/−1, 06 +4/−2, draft-log +2/−1, handoff +3/−2, direction-log +2/−1, 결과 `astra_motion.md` +1, `ma1.md` +1/−1, 스펙 +1/−1, 새 `r7_cycle28.md`.

### 6.2 28회차 정정 주장 대 실제 diff·원자료 (0cc45ae)
| 주장 (06 `:19`·`:20`, handoff `:127`, 커밋 메시지) | 실제 diff | 원자료·원 문서로 참인가 | 판정 |
|---|---|---|---|
| 04 R2_TRAIN 서술(28회차 D-1) | `04:61` 끝에 "[→ 정정 … 28회차 D-1: … 폴더의 `P*.stageb.jsonl`은 12:20Z 파일럿 병합분(과제당 시드 19–41개)뿐 … 병합은 아직 …] **학습 전 필수** …" | 파일 mtime 12:19:47–12:20:26Z ✓, 병합 없음 ✓(`check.json` 12:20:26Z, 로그 MERGE·CHECK 0, 21:23:01Z까지 새 파일 0), "학습 전 필수" 경고 = `gen.py` check/merge·로더 기본 경로(28회차 확인) ✓; **"`P*` … 과제당 19–41" ✗**(P1 11–19, P2 10–20) | **D-2**(N102) |
| 04 상태 꼬리표 제거(28회차 D-2) | `:16` "E-Astra-motion 탐침 코드(3500f54)", `:54` "E-MA1b 체크포인트 `a3d_s{1,2}`(불채택, `results/ma1b.md`)", `:3` 규칙 문장 | `git ls-tree 3500f54 harvest/astra_motion/` 15 ✓; 파드 `ckpt/ma1b` = `a3d_s1`·`a3d_s2` ✓; `results/ma1b.md` 있음 ✓; `:3` 확인 시각은 그대로(N106), 새 경로 누락 그대로(N90) | 맞음 |
| '상태는 책에 적지 않음' 규칙·`[결과 전]` 표기(P69) | README `:8`·`:11`, `01:4`, `01:61`·`:63`·`:67` 결과 칸, `05:36`, 06 `:20` | README·범례·결과 칸·05 ✓; **`01:67` 상태 칸 `[진행 중]` 남음** ✗; **handoff에 넘긴 진행 상태 없음** ✗ | **D-1·D-3** |
| 02 P63 정정·P69 | `02:103` 증상 칸 안 표시, `02:55` P69(5칸) | P63 표시 내용 = 파드(P0 파일럿 병합, '과제 폴더만'이 틀림) ✓; P69 "26·27·28회차" 범위 △ | 맞음(N104) |
| `ma1.md:15` 두 번째 정정 | 끝에 "[→ 정정 … 28회차 D-1: … 과제별 `P0.stageb.jsonl`은 12:20Z 파일럿 병합분(과제당 시드 19–41개) … '과제 폴더만 있음'뿐]" | P0 파일 12:19:47–12:20:23Z·19/30/30/26/40/41시드 ✓, 600편 병합 없음 ✓, 17:3x 원문의 "작업자 5개 P0" ✓(N108) | 맞음(N108) |
| 01 Qwen 판본 표시(E-N13) | `01:60` "(Qwen 흐름은 프롬프트 판본 두 개 혼재 — [→ … E-N13])", 결과 `astra_motion.md:58` 새 줄 | 실험 절 7.1 | 맞음 |
| 03 §86 보충 행(N87) | `03:71` "§86 보충 \| 20:37 \| 흐름 요청 시간 초과 20 s(탐침 실행기 값 — 탐침에서는 시뮬 초; 실기 적용 때 벽시계로 다시 확인), 요청 방식 기본 F0" | 정본 `:778`(20:37 UTC, 20 s, F0) ✓; 시뮬 초 = `harness.py:45` 주석·`:539` 비교 ✓; 칸 4 ✓ | 맞음(N88 정본 쪽) |
| 스펙 §17 N88 | `:199` "지연 p95 범위 12–16 s 위; 결과 문서 0절 요약 — 5절 표는 편 평균 F0 11.6 s·F1 14.1 s; 탐침의 20 s는 시뮬 초 기준이라 실기에서는 벽시계로 다시 잰다" | 0절 `:6` "p95 12–16 s" ✓; 5절 `:54`·`:55` 지연 p95 11.6·14.1, `:57` "(편별 평균 …)" ✓; 시뮬 초 ✓ | 맞음 |
| 06 N84 칸·N85 표시 | `06:12` 표시가 넷째 칸 안 + "(칸 안으로, … N84)"; `06:16` "[→ … N85: 40895f8 시각 20:34:19 UTC …]" | 칸 수 4(H3) ✓; 40895f8 = 2026-09-25 20:34:19 UTC ✓, 2df9bdc = 19:49:56 UTC ✓ | 맞음 |
| handoff·draft-log·direction-log N86 | handoff `:126` "보고 20:3x UTC → 정정 커밋 47edadb 20:37:43 UTC", draft-log `:478` "20:37 UTC(정정 커밋 47edadb …)", direction-log `:74` "20:37" | 47edadb = 20:37:43 UTC ✓ | 맞음 |
| 28회차 줄 | handoff `:127`, draft-log `:479`, direction-log `:75`: DEFECT 0·DOC 2·SCOPED 21·NOTE 70, 실험 절 PASS, "보고 21:02" | 건수·내용 = `r7_cycle28.md` 판정 표 ✓; 시각 21:02 ≠ 작성 21:05 | 맞음(N103) |
| 갱신 기록 | 0cc45ae 책 변경(README·01–06) → 06 `:19`·`:20`(21:07 ≤ 커밋 21:07:54) | 두 줄이 README·01·02·03·04·05·06을 모두 덮음 ✓; `:20`의 "`[진행 중]` → `[결과 전]` 통일" 주장은 D-1로 불완전 | 맞음(D-1) |

### 6.3 기록책 (0cc45ae 사본에서)
- 현재형 진행 상태 검색(`grep -nE '진행 중|생성 중|작업 중|미커밋|아직|지금|현재' docs/book/*.md`): 02·06의 이력 인용(P14·P60·P68·P69, 06 `:15`·`:16`·`:20`)을 빼면 **01 `:67` 상태 칸 `[진행 중]`(D-1)**, `04:61` "아직 돌지 않았다"(N102, 시각 표시 안), `01:38` "(아직)"(E2E 기준점 — 커밋으로만 바뀌는 값), `04:48` "현재 사용"(결정)뿐. "지금 … handoff" 안내 5곳 → D-3.
- 수치: `04:61` → D-2; `04:16`·`:54` ✓; `01:67` "계획 P0–P2 시드 10000–10999" = 파드 `r2train/*.sh` `B="P0:10000-10599 P1:10600-10799 P2:10800-10999"` ✓; `03:71` = 정본 `:778` ✓; `01:61`·`:63` "GPU 2"·"GPU 3" = 파드(N113) ✓.
- 링크 101개 끊김 0(H4); 06 갱신 줄 전수(N109).

### 6.4 C. 가드 (파드, `CUDA_VISIBLE_DEVICES=""`, 21:18:04–21:18:22Z, 21–28회차와 다른 값; 사유는 `gtxt29.sh`로 로그 마지막 오류 줄 확인)
1 `e05 --data P1 --split test --seeds 1003`, 2 `e05 --data P2 --split cal --seeds 548`, 3 `calib --fit-split test --heldout P1 --heldout-split dev`, 4 `calib --fit-split pool --heldout P1 --heldout-split test_p5`, 5 `rd --variants dr=gen_dev/dr/P1 --split test`, 6–8 `closed --split test --seeds 1126`·`cal 501`·`test_p5 1325` → "--split … refused: set HARVEST_ALLOW_SPLIT=…"; 9 `dev --seeds 14,40` → "seeds [40] are not in split dev", 10 `pool --seeds 1998`, 11 `dev --seeds 2050` → "not in split … (refused, never opened)"; 12–13 `--isaac-gpu 7`·`10` → "0 or 1 only (GPU 2 never renders)"; 14 `--m4-lead-max=nan`, 15 `=-1e-9` → "lead_max = nan / -1e-09 … finite > 0 s"; 16 `--conditions "C5,C6'"` → "condition \"C6'\": runtime has [...]"; 17 `HARVEST_ALLOW_SPLIT=test` + `closed --split test_p5 --seeds 1302`, 18 `=test_p5` + `e05 --data P2 --split cal --seeds 544` → 거부; 19 `gen --seeds 59998`(확인 없음) → "R2_TRAIN 10000-59999 needs --confirm-train", 20 `--seeds 9990 --confirm-train`, 21 `--seeds 60500 --confirm-train` → "every other seed is refused"; 22 `determinism fresh --seed 31`, 23 `history --seeds 1999` → "only DEV 0-29 and POOL 2000-2119"; 24 `canary build-set --data P1 --seeds 3050-3051`, 25 `e05 --data P1 --split pool --seeds 2097` → "no episode selected"; 26 `--hb-mode k0`, 27 `--hb-mode "K-1"` → "from ('K0', …, 'K4')"; 28 `stageb_train predict --aux-extra a3d@v0` → argparse "invalid choice … ('none', 'a3d@v1')" rc 2. **실험 옵트인 가드**: 29 `se2e_cam3 evalck --data pool --cam3 cam3@v1` → "--cam3: --data se2e only", 30 `se2e_cam3 predict --data se2e --cam3 cam3@v1`(움직임 줄 없음) → "--cam3: with the motion line (prereg_cam3 cells)", 31 `se2e_kvcond predict --expert-cond kvcond@v0`, 32 `se2e_cam3 train --cam3 CAM3@V1` → argparse "invalid choice" rc 2. **32건 모두 rc ≠ 0**; 출력 폴더는 25번 빈 폴더 하나(N10).

### 6.5 A. 테스트
- 로컬(`…\r7c29\repo`, Git Bash, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/r7c29/pt tests`): EXIT 0, **1133 passed · 20 skipped**.
- 파드 CPU(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`): **1280 passed, 4 skipped**, EXIT 0. 파드 LeRobot(`venv_e3st`): **6 passed**.

### 6.6 완료 정의 1–5 (직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV **36/36** + 새 음성 대조 12종; LeRobot 시험 6 passed, 새 2편 내보내기·검증·적재(행 138); `se2e_c1` **5/5 OK**(21:22Z). (R2_TRAIN 폴더 행 병합은 아직 — N94, 완료 정의 1은 R2 DEV 기준.) |
| 2 모델 | 충족(CPU) | CPU 스모크(N111), CPU 묶음의 단계 B·E-MA1b·E-CAM3·E-MA3 시험 통과, 기준선 코드 무변경. GPU 학습 없음. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 9 --conditions "C5,C5'" --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c29`: `CLOSED_DONE` C5·C5' 1.0, 호출 42·오류 0, 행동 비트 동일(행 99). |
| 4 평가 | 충족 | 모의 한 명령씩(`venv_vllm`, GPU 없음, 21:18:22–21:19:15Z): `e05` → `E05_DONE`, `rd` → `RD_DONE`(dr 낙폭 0.0), `calib` → `CALIB_DONE`, `e05 --truth outcome:plan` → `E05_DONE`. |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 git·`code_sha`·부트스트랩·사전 등록 해시·`m4_H`·`m4_lead_max`·`hb_mode`; 정리 뒤 흔적 없음(§6.7). |

### 6.7 F. 규칙·위생
- 저장소: 이 보고서 한 파일만 추가(커밋 안 함). HEAD 시작·끝 0cc45ae.
- 파드 정리(`clean29.sh`, 경로를 하나씩 적은 스크립트를 `bash -s`로, 열린 핸들 0 확인 뒤, 21:23:27Z): `tmp/r7c29`(511 MB), `tmp/carb.UHGew8`·`tmp/tmpko8deq87`·`cache/pyc_r6/data/harvest/tmp/tmpko8deq87`·`cache/pyc_r6/data/harvest/tmp/r7c29`, `ir/kitcache/cyclo-r7c29_standard`(208 MB). 끝에 r7c29 항목 0(tmp·kitcache·pyc_r6·pyc), 파드 루트 `/C:` 없음, 명령줄에 r7c29가 든 프로세스 0, `IR_INST=r7c29` 프로세스 0, 열린 핸들 0. R2_TRAIN·E-CAM3·E-MA3·탐침 파일은 읽기만.
- 로컬(21:28:19Z): 추출 사본 `repo/`(26 MB, 590파일)·pytest basetemp `pt/`(16 KB)·archive `a29.tar`(21 MB) 삭제, 보고 근거 스크립트·출력(`check29.py`·`check29_out.txt`·`cellcheck29.py`·`pod/`·`*_out.txt`)만 남김(592 KB). 지시대로 `D:\tools\scratch_qdd\r7c27`(528 KB) 삭제 — r7c 폴더는 r7c28·r7c29만. D: 여유 8.1 GB(끝). 이 보고서 표 칸 수 불일치 0·CR 0(`cellcheck29.py`).

## 7. 실험 코드 절 (별도 판정: PASS — 코드 결함 0, DOC 0)

### 7.1 0cc45ae의 실험 쪽 변경: 결과 `astra_motion.md:58` (28회차 E-N13 정정) 대 원자료 (파드 `exp29.py`, 읽기만)
- 새 줄 "Qwen 8B 두 행은 프롬프트 판본이 섞여 있다: s0·s7(F0·F1)은 `a84e4c76efed`(17:43–17:52Z 무료 사전 실행), s14는 `9b5c5c292765` — 기술 참고값" — 파드 `out/astra_motion/qwen8b/S-stream-F{0,1}/s{0,7}_*/result.json` 4편 `prompt_id` = `a84e4c76efed` ✓, `s14_bottle_tray` 2편 = `9b5c5c292765` ✓(18:19:07–18:21:23Z). 책 `01:60`에도 같은 표시 ✓ → 28회차 E-N13 해소. 시각 → E-N19.
- 표 아래 "(편별 평균 …)" 줄과 F1 채택 규칙 줄 사이에 들어가 표 칸 수에 영향 없음(H3).

### 7.2 E-CAM3·E-MA3
- 0cc45ae까지 결과 커밋 없음 → 범위 밖(S20). 파드에서 본 것은 이름·시각뿐: `ckpt/cam3/cam3_s1`(20:43:05Z)·`ckpt/ma3/kv_s1`(20:45:44Z), 로그 `cam3_s1.out`·`kv_s1.out` 21:17Z 갱신(학습 중). `predfull_*`·`chunk_*`·`reuse_check.out` 등은 열지 않았다.

### 7.3 이번에 하지 않은 것
- E-CAM3·E-MA3 예측·청크 평가·재사용 검사 출력은 지시대로 열지 않았다 — 기준 재사용 비트 동일(등록 3절 (2))·판정 재계산은 결과 커밋 때.

### 7.4 DOC (실험 절)
없음.

### 7.5 NOTE (실험 절)
- E-N1–E-N11. (27회차 그대로; E-N3 해소.)
- E-N12. (그대로) 등록 14절 "원장으로 확인"의 출처 표기(G1 v2·G2 장부에 `prompt_id` 없음).
- E-N13. (해소) 결과 5절 `:58`·책 `01:60`에 판본 혼재 표시.
- E-N14–E-N18. (그대로.)
- **E-N19.** 결과 0절 `:7`·5절 `:58`의 "17:43–17:52Z 무료 사전 실행" — 파드 편 폴더의 가장 이른 파일은 s0 F0 17:46:17Z(`wall_s` 90.0, 끝 17:47:03Z)이고 마지막 편 끝은 17:51:56Z다. 17:43은 모델 기동 등 편 밖 시각일 수 있으나 편 폴더로는 확인되지 않는다(값 차이는 3분, 판본 구분에는 영향 없음). 근거를 한 구절로 적거나 "17:46–17:52Z(편 파일 기준)"으로.

## 8. 다음 순회 전에 할 일 (제안)
1. **D-1**: `01:67` 상태 칸 `[진행 중]` → `[결과 전]`(06 줄). 고친 뒤 `grep -nE '\[진행 중\]|생성 중|미커밋' docs/book/*.md`가 02·06 이력 인용만 내는지 확인.
2. **D-2**: `04:61`의 시드 수를 종류별(P0 19–41·P1 11–19·P2 10–20)로 또는 P0 한정으로, 근거 명령과 함께(06 줄). 정정 문장은 파드 명령 출력으로 확인한 뒤 쓴다(P68 — 이번이 세 번째).
3. **D-3**: handoff에 "진행 중 작업(UTC 시각)" 줄 — R2_TRAIN(종류별 끝·진행·병합 여부), E-CAM3(GPU 2), E-MA3(GPU 3). 결과 커밋 때 그 줄을 지우는 것을 규칙에(README `:11` 또는 P69 예방 칸). 같은 커밋에서 N102(`04:61` "아직" → handoff로)·N106(`04:3` 확인 시각)·N90(새 경로)·N105(`01:38` 행 이름) 권함.
4. (선택, NOTE) N103(28회차 줄 시각 = 보고서 작성 21:05), N104(P69 회차), N107(표 D 칸 정리), N108(`ma1.md:15` 근거 명령), N88(정본 §86 보충에 "시뮬 초" 한 구절), E-N19.
5. 30회차 대상은 0cc45ae 이후 HEAD, **연속 무결 0에서**. E-CAM3·E-MA3 결과가 커밋되면 기준 재사용 비트 동일·판정 재계산을 실험 절에서. R2_TRAIN 생성이 끝나면 병합·행 수 대 편 수(N94).
