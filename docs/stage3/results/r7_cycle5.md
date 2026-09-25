# R7 객관 검증 순회 — 5회차 (cycle 5, 연속 무결 카운트 0에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님). 작성 2026-09-25 01:31 UTC(`date -u`; 파드 `date -u` = `Fri Sep 25 01:17:59 UTC 2026`(시작)·`01:29:25`(정리), 로컬과 같음).
- 대상: `D:\qdd` `dev` 브랜치 HEAD `541068a` = `origin/dev`(`git ls-remote`), 작업 트리 깨끗(검증 전후 `git status` 출력 없음). 파드 사본 = `git -c core.autocrlf=false archive HEAD`(LF 블롭, `stageb_data.py` `git hash-object` = HEAD 블롭 `a174e306…`), 폐루프 `meta.code_sha` = `6f7d5a66cf03ebc8`(4회차 `73a719f0…`와 다른 것은 `fused_action.py` docstring 변경 때문).
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류(DEFECT / DOC / SCOPED / NOTE), `r7_cycle2.md`(K1–K6), `r7_cycle3.md`(L1–L4), `r7_cycle4.md`(M1–M2), `r7_fixes.md`, 정본 `00-interfaces.md` §1–§70(뒤 절 우선; §67–§70 SCOPED는 결함으로 다시 세지 않음, [사용자] 제목 절 본문은 §67 규칙대로 세지 않음, 논문 .tex의 vLLM 서빙 서술은 §70에 따라 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5.
- 분류 기준(이번 판에서 적용한 선): **DOC** = 지금도 참고되는 문서(정본·계획·handoff·결과 문서·코드 주석)가 HEAD의 코드·상태와 다른 **현재 시제** 서술을 하고, 그 문서 안에 정정·해결 표시가 없는 것(2회차 K5·4회차 M2 선례). 관문 당시의 "열린 문제" 목록처럼 기록 성격이고 해결 기록이 후속 문서에 번호로 이어져 있는 것은 NOTE.
- 규칙 준수: 코드·문서 수정·커밋 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`로 실행(전역 설정 안 씀). 로컬 임시 = `D:\tools\scratch_qdd\r7c5`(스크립트는 Write 도구로 D:에 씀, Git Bash heredoc 안 씀, kubectl 경로 변환은 `MSYS_NO_PATHCONV=1`). 파드 파일은 모두 `/data/harvest/tmp/r7c5`(코드 사본·산출·pytest·pyc, 1.6 GB), Isaac kit 캐시 `ir/kitcache/cyclo-r7c5_standard`, 폐루프 작업자가 쓴 `cache/pyc_r6/data/harvest/tmp/r7c5`·`tmp/{carb.jcqcMQ,tmpmcp6wg4o,hub-root.lock}`(생성 시각 01:22:26–01:22:41 UTC = 내 폐루프 판), LeRobot 시험이 만든 `cache/hf/datasets/parquet/default-4f546092340b4f86`(+잠금 파일)에만 썼고 **끝에 모두 지웠다**(01:29 UTC 확인, 남은 것은 폴더 시각뿐). GPU: 단계 A·B 학습·CUDA 시험 = GPU 2(렌더 없음, 시작·끝 1 MiB), Isaac = GPU 1, GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음. 시드 DEV만, `HARVEST_ALLOW_SPLIT`은 가드 음성 시험 1건에서 `=dev`만. 유료 API 호출 없음(Astra 모의). 비밀값 출력·검색 없음(패턴 검사는 개수만).

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 0 |
| DOC | 2 |
| SCOPED | 8 |
| NOTE | 13 |

코드는 2·3·4회차에 이어 **네 번째로 연속 무결**하다(1회차는 코드 DEFECT 2). 완료 정의 1–5를 직접 다시 돌려 모두 충족함을 확인했다. 4회차 M1·M2는 해소됐고, 요청받은 구현 이름·문구 grep(vLLM, HF, StageBFused, one call, 한 번 호출, [제안], [proposal], 500–699, 2026-09-25, GPU2 금지, 102°, §1~§6x)에서 "융합 decide = vLLM"이 표시 없이 남은 곳은 없다. 그러나 (P1) 541068a가 handoff 머리의 정본 범위만 §70으로 올리고 갱신 시각·순회 상태는 그대로 둬서 같은 문서 안에서 어긋나고, 코드 무결 연속 횟수가 handoff·direction-log에 틀리게 적혔다. (P2) 541068a가 정정 표시를 단 바로 그 줄(`r6_eval.md:54`, `r5_closed_loop.md:98`)이 "단계 B 실체크포인트 어댑터가 없다 / `closed --backend fused`는 실체크포인트를 거부한다"는 현재 시제 서술을 그대로 둔다(pre-R7 519de26에서 해결됨). 둘 다 문서만 고치면 된다.

---

## 1. DEFECT

없음.

## 2. DOC

| # | 내용 | 위치 | 근거 |
|---|---|---|---|
| P1 | **handoff 상태 줄이 §70 정정 뒤 갱신되지 않았고, 코드 무결 연속 횟수가 틀렸다.** 머리 3줄 "마지막 갱신: 2026-09-25 **00:56** UTC (… **3회차까지 FAIL(문서만)** …, 정본 §1~§70)" — 같은 줄의 §70(01:14 UTC)보다 갱신 시각이 앞서고, 같은 문서 94줄은 "R7 4회차 … FAIL"이다. "(문서만)"도 1회차 코드 DEFECT 2건과 맞지 않는다(4회차 N2가 이미 짚음). 94줄 "코드 무결 **4회** 연속"과 direction-log 52줄 "5 코드 무결 **4회** 연속"은 틀렸다: 코드 무결은 2·3·4회차 = 3회 연속이었다(direction-log 51줄 3회차 = "코드 무결 2회 연속", 1회차 = DEFECT 2). | `docs/handoff.md:3`, `docs/handoff.md:94`, `docs/stage3/direction-log.md:52` | 541068a의 handoff 차이는 `:3`·`:5`에서 "§1~§69" → "§1~§70"만 바꿨다(`git show 541068a -- docs/handoff.md`). 커밋 시각 541068a = 01:15:45 UTC. 횟수 오류의 출처는 `r7_cycle4.md:17` "코드는 네 번째로 무결하다"(검증 보고서라 기록으로 두고 따로 세지 않음). 3회차 L4·2회차 K4(handoff 머리 상태) 선례와 같은 부류이고, handoff는 새 세션이 가장 먼저 읽는 문서다. |
| P2 | **(§70 형제) 541068a가 정정 표시를 단 줄이 실체크포인트 어댑터가 없다는 현재 시제 서술을 그대로 둔다.** `r6_eval.md:54` "**FusedModel 실모델 없음**: `closed --backend fused`는 `mock_fused`만 받는다. … `StageBFused`(… 정정 …) 어댑터는 R5 열린 문제 7 그대로 — **실체크포인트를 주면 그 메시지로 거부**." `r5_closed_loop.md:98` "**FusedModel 실물 모델 없음**: `StageBFused`(…정정…)는 R4 체크포인트가 나오면 붙인다". 같은 괄호 안의 정정은 "실제 구현은 2순위 … `fused_model.py`"라고 해서 한 문장 안에서 서로 어긋난다. | `docs/stage3/results/r6_eval.md:54`, `docs/stage3/results/r5_closed_loop.md:98` | 현재 코드: `harvest/eval/closed.py:17-19`(fused = mock_fused **또는 REAL stage-B checkpoint dir**), `:335-339`(`info["kind"] == "stageb"`면 `selector = "stageb"`), `harvest/eval/common.py:84-85`, `harvest/runtime/fused_model.py:1`("R5 open item 7, R6 issue 1"). 해결 기록: `pre_r7_fixes.md:13` "FusedModel 실체크포인트 어댑터 (R5 7 / R6 1) — **해결**"(519de26). 2회차는 실제 체크포인트로 `closed --backend fused`를 돌렸다(`r7_cycle2.md:87`). §69 절차("같은 사실을 적은 곳을 모두 고치고 정정 표시")와 2회차 K5(열린 문제 서술이 수정 커밋 뒤 사실과 다르면 표시) 선례. 이 두 줄은 541068a가 직접 편집한 줄이라 기록 성격의 다른 열린 목록(NOTE N2)과 구분했다. |

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(TODO(P3)). 로컬·파드에서 시험 1개 건너뜀(`tests/runtime/test_latency_ctrl.py:11`).
- S2. 본 단계 B 학습·R2_TRAIN 대량 생성(§66 "S-E2E 이후").
- S3. CAL 보정·TEST 평가(`HARVEST_ALLOW_SPLIT`, 메인 세션만). 가드는 §5.5에서 다시 확인.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 목록(M9 복구·T_fail 뒤 하트비트 정지, A5′·M2 R3 합치기, 모듈형 세계 쪽 `unknown`, §52 VQA 기본 끔 — `stageb_train.py` `cmd_train`의 `"vqa": 0.0` 고정과 맞음, 융합 런타임 토크 입력·확인 헤드 보정·동시 부하 지연). 근거("완료 정의 1–5 = 학습 직전 배관")는 계획 7줄("본 E2E 학습은 하지 않는다")과 맞다.
- S6. Astra 카나리 id = "none"(유료라 미실행). 이번 폐루프 `astra` 2/2에 명시로 실렸다.
- S7. S-E2E 체크포인트를 aiworker 런타임에 넣을 때의 tau 마스크 채널 차이(`r7_fixes.md` §7, §67; `fused_model.py:17-19` tau = 학습 평균 대치).
- S8. CONTRADICT-soft(§68 K6, §69 근거 보정). 근거 문장 = 코드(`measure.py` `UNCAL_QHAT`, `m4.py` hold, `core.py` Astra 사건)와 맞다.
- §70 세 번째 줄(논문 vLLM 서빙 서술 보류)의 근거 "실물 서빙 선택(RTX PRO 6000, §67 C8 SCOPED)이 열려 있음"도 타당하다 → N4.

## 4. NOTE
- N1. **ZED Mini 102° 옛 서술(정본은 정정됨)**: `docs/design/M1-state-representation.md:119` "머리 ZED Mini(102°×57° …)"·"VGA에서 0.6 m 약 5 mm", `D21-aiworker-zed.md:84,118`("VGA ≈272 px"), `SUMMARY.md:668`, 정본 §37 `00-interfaces.md:345`, `E-first-experiments.md:105`("ZED Mini 102°와 다름", `ZED_M` 쌍둥이). 정본 §47 `:428`이 "§37·M1의 102°×57°는 센서 최대 화각"으로 정정했고, §43 `:396`이 E-first §1.4 `ZED_M` 줄을 대체했다. 코드는 85°·fx 367(`third_party/humanoid_challenge_env/scripts/FFW_SG2_REAL_cameras.py:64-71`, `harvest/cli_e3st.py:19`)이고 `e3st.md:7,54`에는 정정 표시가 있다. 다만 §47 `:429`가 약속한 "M1·D21 수치 정정은 다음 편집 묶음"은 하지 않았다. 단계 2 설계 문서(정본이 우선, handoff `:5`가 단계 3 이전 판본을 옛 기록으로 지정)라 결함으로 세지 않는다. P1·P2를 고칠 때 M1:119에 "(정본 §47: VGA 85°·fx 367)" 표시를 붙이기를 권한다.
- N2. **관문 당시 열린 문제 목록 중 pre-R7에서 해결된 것에 해결 표시가 없다(P2 외)**: `r6_eval.md:59`(6 DEV 시드 1 집기 실패 → `pre_r7_fixes.md:15` 해결), `:60`(7 "K1·K3·K4는 런타임 훅이 없다" → `:16` 해결, `closed.py:171,193`), `r5_closed_loop.md:92`(1의 T_sub·사건 훅 부분 → `:16`), `r4_stageB.md` §8의 1(CUDA 그래프 → `fused_action.GraphedSampler`)·2(처리량 → R3)·10(pytest 임시 → conftest). 해결 기록 `pre_r7_fixes.md:3`이 대상 번호("r4 §8, r5 §6(7번), r6 §5(1·6·7번)")를 적어 이어져 있어 기록 성격으로 본다. P2를 고칠 때 같은 목록에 "→ 해결: pre_r7_fixes.md §N(519de26)"을 함께 붙이면 다음 순회에서 다시 걸리지 않는다.
- N3. **R5 §5의 1순위 설계 잔여 서술**: `r5_closed_loop.md:85-86`(표 "행동 청크 합(1순위)"·"2순위의 확정 뒤 행동 [미측정]")과 `:89` "같은 GPU에서 vLLM과 HF 행동 서버가 경쟁하므로"는 같은 절 머리 `:76`의 정정 표시(§67 C4, "실제 구현은 2순위")가 덮는다. 계획 `2026-09-25-e2e-ready.md:39` "같은 vLLM 설정·캐시·lead 호출"과 `r5_closed_loop.md:89`의 "(사용자 지시 user-log 62: … 같은 vLLM 설정·캐시·lead)"는 user-log 62 원문(`docs/user-log.md:264-265`, "프로600에서 하는걸 가정해서 여기서 다할거고")에 없는 풀이다. 모듈형 기준선에는 맞고 융합 행은 HF라, 서빙 방식을 정할 때(§67 C8) 함께 다듬기를 권한다.
- N4. 논문 결정 호출 서빙 서술(`paper/sec/3_method.tex:34`, `4_setup.tex:17`, `6_prelim.tex:18,44`)은 vLLM 기준이다. §70이 논문 갱신 때로 미뤘다. `paper/`는 `1373f3d..HEAD`에서 바뀌지 않았다.
- N5. `harvest/train/stagea_train.py:6` 사용법 "load --adapter DIR --pool DIR --rule R": `--rule`은 `--target-source outcome`에서만 쓰인다(`:155-163`, `load`의 `--rule` 기본 ""). labels_v2 기본에서는 무시되므로 동작 문제는 없다. 1회차 C6에서 `train` 줄만 고친 형제.
- N6. `random5.md:23,51`의 500–699(4회차 N1) 그대로. 같은 문서 `:4`에 정정 표시가 있다.
- N7. §69 S-E2E 사전 등록 항목은 코드에 선택지가 없다(4회차 N5): `stageb_train.py:364` `val = va[:a.max_val]`(앞 N개 = RB1만), `:366-369` 끝에 `last`만 저장. 사전 등록 문서에서 `--max-val 0`+큰 `--eval-every` 또는 층화 옵션 추가를 정해야 한다. 정규화 통계는 `new_model(bb, tr, …)`로 **학습 부분집합**(`--max-train` 적용 뒤)에서 맞춘다 — 본 학습(`--max-train 0`)에는 맞고, 이번 판 팔별 mean[0]이 4회차와 다른 것(왼 0.124 / 오 0.441)도 이 때문이다.
- N8. 카나리는 여전히 09-24 UTC 것이다(`cn20260924_mock_ae0d1a`, 이번 `closed.json` `meta.canary.stale = true`). §68대로 S-E2E·본 실험 시작일에 새로 만든다.
- N9. TEST2 1150–1299(`E-first-experiments.md:116`)는 `eval/splits.py:13` `RANGES`에 없어 모든 도구가 거부한다(4회차 N8). 연장을 실제로 쓸 때 넣어야 한다.
- N10. `gen --seeds 3000|60000 --confirm-train`의 거부 문구 "R2 generates DEV 0-29 only; CAL / TEST / TEST-P5 / POOL are never generated here"는 시험 범위·범위 밖 시드에 대해서는 부정확하다(동작은 맞음, `gen.py:43-49`).
- N11. 폐루프 작업자는 공용 `TMPDIR=/data/harvest/tmp`를 써서 판마다 `carb.*`·`hub-root.lock`·`tmp*`를 남긴다(지금 `carb.*` 246개, 이번 판 것은 지움). /data 안이라 규칙 위반은 아니다(4회차 N10).
- N12. 로컬 스위트는 Git Bash에서만 돌렸다. PowerShell 실행 시 `harvest/load/session.py:15`의 `date` 의존으로 2개가 실패하는 문제(4회차 N7)는 이번 범위에서 바뀌지 않았다(`git diff --stat b4a58ce..HEAD -- harvest tools tests` = 주석 4파일).
- N13. 로컬 C: 위생: 시작 표식(01:17:54 UTC) 뒤 C:에서 바뀐 것은 `.claude.json`·`AppData\Local\Temp\claude`(하네스), `.kube/cache/http`(kubectl 자체 캐시), `AppData\Local\Temp\.ses`(53 B, 시각+GUID, 다른 앱 — 이 저장소 것 아님), `AppData\Roaming\{Code,Zoom}`(다른 앱)뿐이다. `pytest-of-USER`·`torchinductor_USER` 없음. Git Bash의 경로 변환으로 C:에 생길 뻔한 `ls` 1건은 파드 쪽 오류로 끝났고 로컬에 아무것도 만들지 않았다(`C:\Program Files\Git\data` 없음 확인).

---

## 5. 확인한 것 (근거)

### 5.1 4회차 M1–M2 해소 여부
| M | 해소 | 확인 |
|---|---|---|
| M1 `fused_action.py` 머리 | 해소 | `harvest/runtime/fused_action.py:3-11` "both on the HF backbone in fused_model.py … vLLM serves only the modular baseline's Jev-L", "chunk at the checkpoint's hz / H (R2 30 Hz, H 15; S-E2E 10 Hz, H 5)". 구현과 맞다: `fused_model.py:4-13`, `:140` `self.hz = cfg["hz"]`, `:272` `expert.cfg.horizon`, `:282` `chunk_dt = 1/hz`. `grep -rn vLLM harvest` → 남은 것은 모두 모듈형·서빙 도구·`closed.py:8`(바로 뒤 `:17-19`에 fused = HF 명시) 서술이다. |
| M2 `r5_closed_loop.md:76,98` | 해소(vLLM 부분) | 두 줄 모두 "정정(정본 §67 C4, R7 4회차 M2)" 표시. `r6_eval.md:54`에도 같은 표시(§70). 같은 줄의 "실모델 없음/거부" 서술 → **P2** |

### 5.2 같은 사실 grep (이번 판 명령, 저장소 추적 파일 379개, `paper/`·`r7_cycle*.md` 제외)
- `vLLM|vllm`: 융합 decide를 vLLM으로 적은 곳은 정정 표시가 있는 `r5_closed_loop.md:76,98`·`r6_eval.md:54`와 N3의 잔여뿐. 나머지는 모듈형 Jev-L·단계 A 서빙·D27 벤치·E3-lite 기록이다.
- `StageBFused`: `fused_model.py`·시험·위 두 결과 문서뿐 → P2.
- `one call|single call|한 번 호출|one fused call`: `00-interfaces.md:511`(§58 [사용자] 절 본문, §67 C4가 덮음), `r4_stageB.md:140,149`(정정 표시), 계획 `:5`(정정 표시), `conditions.py:5,11`·`jevl.py:8`·`models.py:1`·`jevl_mmbench.py:3`(모듈형 DecCall 하나·in-flight 수라는 다른 뜻).
- `\[제안\]|\[proposal\]`: 단계 3 범위에서 R2_TRAIN을 제안으로 적은 곳은 `r2_datagen.md:139`(끝에 L2 정정 표시)뿐. 나머지는 단계 2 설계 문서의 일반 표기.
- `500.699|500, ?700`: `random5.md:4`(정정 표시)·`:23,51`(N6), `test_gen_guards.py:20`(R2_TRAIN과 겹치지 않는지 보는 단정 — 맞음), `r7_fixes.md:57`(기록).
- `2026-09-25`: [사용자] 제목 5개(§67 C1 규칙), 실제 UTC 날짜인 것(§67 보충 00:08, §68 00:33, §69 00:55, §70 01:14, `r7_fixes.md:6`, `r5_closed_loop.md:117`, `se2e_data.md:109`, handoff 92–94), KST를 밝힌 `r5_closed_loop.md:4`, 기준 없는 `randomization_pools.json:20`, 계획 파일 이름. handoff `:3`의 "00:56 UTC"는 날짜 오기가 아니라 갱신 누락 → P1.
- `GPU ?2 ?금지|never GPU ?2|2 금지`: 계획 `:29`(취소선 + "→ user-log 62·64로 대체"), `closed.py:10,140,330`·`test_closed_pure.py:102`(Isaac 렌더 거부 — 맞음), 기록 문서(`r7_fixes.md:49,51,52`, §68).
- `102°`: N1.
- 정본 범위 `§1~§N`·`§43–§N`: handoff `:3,:5` §1~§70, `:81` §43–§70(끝까지), `:80` 제목 "§43~§64"(21:03 시점 요약 — 맞는 기록). 그 밖은 단계 2 문서의 당시 범위.
- 시드 범위 문장 전수 집계(`(DEV|CAL|TEST|TEST-P5|POOL|R2_TRAIN) a–b`): DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 / TEST2 1150–1299(연장 시) 외의 값 0건(DEV 0–9·0–4·15–29 등은 DEV 부분집합 사용 기록).

### 5.3 A. 테스트
- 로컬(Git Bash, `cd /d/qdd && python -m pytest`, TMP·basetemp = `D:\tools\scratch_qdd\r7c5`): 2회(72 s / 69 s) 모두 EXIT 0, 진행 표시 합 790 = 784 통과 + 6 건너뜀 표시(모듈 단위 건너뜀 포함); `-rs` 요약 판: **784 passed, 11 skipped**(68.9 s). 건너뜀: torch 없음 7, inspect_robots 없음 2, pyarrow 1(파드 안내), TODO(P3) 1. 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json` 생기지 않음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + IR 4경로, `CUDA_VISIBLE_DEVICES=""`, basetemp `/data/harvest/tmp/r7c5/pytest_cpu{1,2}`): **826 passed, 3 skipped** 두 번(EXIT 0, 84 s / 70 s). 건너뜀: pyarrow 1, CUDA 없음 1, TODO(P3) 1.
- 파드 GPU 2: `tests/runtime/test_fused_action.py tests/train/test_stageb_torch.py tests/runtime/test_fused_model.py` **26 passed**(GPU 2 시작·끝 1 MiB).
- 파드 LeRobot(`venv_e3st` + `r2/pylib_lerobot` + `r2/pylib_pytest`): `tests/datagen/test_episode_files.py` **6 passed**.

### 5.4 완료 정의 1–5 순회 (이번 판에서 직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | S-E2E 로더(단계 B 학습 진입점 안): hz 10, H 5, n_val **1,799**(= §63), `grip_src` {RB1, RB2}, `grip_space open01@v1`, `proprio_masked` 40/40. LeRobot 내보내기 시험 6/6. `b4a58ce..HEAD` 코드 변경은 주석 4파일뿐(`git diff -U0`로 줄 단위 확인) — 2회차 R2 DEV 재검증 값 유지. |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c5_se2e --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 17` → EXIT 0(01:18:57–01:19:40 UTC). `model_rev ebb281ec…`, prompt_config 카메라 3배치(왼손목·오손목·양손목, §57), 검증 결정 NLL 3.526 → 3.180 → 1.588. `save_load`: `max_abs_action_diff` **0.0**, `eval_before` = `eval_after`(fm 2.35348, dec 1.58798, mse 2.37036 등 모든 표시 값 같음). `stageb.json`: hz 10, data se2e, `norm.arms` 왼/오 통계가 다름(mean[0] 0.1237 / 0.4408, std[0] 0.555 / 0.579), `grip_space open01@v1`. **단계 A**(GPU 2, `TORCH_DISABLE_NATIVE_JIT` 미설정 상태에서 모듈이 스스로 설정): `stagea_train train --run a_c5 --max-steps 4 --max-train 96 --max-val 24 --accum 16 --eval-every 2 --seed 23` → EXIT 0(01:26:49–01:27:22), 검증 NLL 4.429 → 2.564 → **1.1402420202891033**; `load --adapter best --n 24 --seed 23` → NLL **1.1402420202891033**(비트 동일). CUDA 시험 26/26. |
| 3 폐루프 | 충족 | `closed --model mock --split dev --seeds 0 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c5`(141.2 s, 01:22:25–01:24:47) → `CLOSED_DONE`, **성공 16.46 s**(1–4회차와 같은 값, 결정성), 호출 49·오류 0, RTF 0.905, M4 epoch 7, Astra 2. 부가 JSONL(`standard/C5/ours/…/dev0-P0-standard-e0.jsonl`, 행 종류 call 49·step 50·astra 2·event 15·m4 7): `call` 49/49에 64자리 hex `request_sha256`(49개 모두 다름), `image_sha256` {cam_head, cam_wrist_right} 49/49 hex, `canary_id` = `cn20260924_mock_ae0d1a` 49/49. `astra` 2/2에 요청 해시(서로 다름) + `image_sha256` {cam_head} + `canary_id` "none". `closed.json meta`: `code_sha 6f7d5a66cf03ebc8`, `canary {id cn20260924_mock_ae0d1a, date_utc 2026-09-24, stale true}`, split dev, seeds [0]. |
| 4 평가 | 충족 | 한 명령 실행(모의 모델, GPU 없음, `venv_vllm`): `e05 --split dev --episodes 1` → `E05_DONE`, `rd --variants standard=… --split dev` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`(`calibration.json` 생성). 모두 EXIT 0. 가드는 §5.5. |
| 5 운영 | 충족 | 모든 산출이 `/data/harvest` 아래, `meta`에 `code_sha`·카나리·시드, `MODEL_REV` 고정(`ebb281ec…`), 처리량 문서 R3. 문서 잔여 P1·P2(→ FAIL 원인). |

### 5.5 C. 가드 (파드, 변수 없이; `CUDA_VISIBLE_DEVICES=""`; 출력 폴더 `guard_out`은 끝까지 비어 있었음)
- 평가: `e05 --split cal`·`--split test`, `rd --split test_p5`, `calib --fit-split cal` → "--split X refused: set HARVEST_ALLOW_SPLIT=X …". `closed --split test --seeds 1000` 거부. `closed --split dev --seeds 500|30|1300|2000|10000` → "seeds [..] are not in split dev range(0, 30) (refused, never opened)". `HARVEST_ALLOW_SPLIT=dev closed --split cal --seeds 500` 거부. `closed --isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)".
- 생성: `gen --seeds 10000-10001`(확인 인자 없음) → "R2_TRAIN 10000-59999 needs --confirm-train". `--confirm-train`과 함께 500·3000·1149·60000 → 거부. `--variant random` → "TEST pool … use 'dr'". `replay --seed 1300` → 거부.
- `aiworker.check_layout_seed`: 0·29 허용, 30·499·500·549·1000·1149·1300·2000·2119·3000·10000·59999 거부. (datagen은 aiworker를 거치지 않아 R2_TRAIN 생성과 충돌하지 않음 — `grep aiworker harvest/datagen` 0건.)
- 시드 표 일치: `eval/splits.py:13-14` `RANGES` = {dev 0–29, cal 500–549, test 1000–1149, test_p5 1300–1329, pool 2000–2119}, `PROTECTED` = (cal, test, test_p5) = `E-first-experiments.md:114-119`(+ R2_TRAIN 10000–59999 = `gen.py:35` = §66). 시험 시드 3000–3199(`tests/sim/test_randomize_logic.py:13`)는 모든 예약 범위 밖.

### 5.6 B·D. 정본 ↔ 코드 ↔ 문서
- §63 (1)–(3)·§62 hz: 5.4 실측(팔별 통계, `open01@v1`, tau 마스크 40/40, hz 10·H 5)이 `stageb_train.py:1-18`·`se2e_data.md:109`와 맞다.
- §47 카메라: `sim/scene.py:11` 머리 ZED Mini 왼쪽 672×376, 손목 D405 424×240 = `FFW_SG2_REAL_cameras.py:64-84`(fx 367·85°, 87°·fx 223.4) = 정본 §47 = handoff `:82`. 옛 102° 서술은 N1.
- GPU: 계획 `:29,40`(GPU 2 = 학습·vLLM, 렌더 금지) = handoff `:85` = user-log 64("해두돼") = 코드(`closed.py:35,140,330` 렌더 0·1만, `fused_model.py` 모델 GPU 2·3, `stagea_train.py:20`·`stageb_train.py:16-17` GPU 2, `canary`·`e05`·`rd`·`calib`·`closed` `--gpu` 기본 3).
- 날짜: 정본 §67–§70 시각 = 커밋 시각(541068a 01:15:45 UTC ≥ §70 01:14). handoff `:3` → P1.
- 정본 §67–§70 SCOPED 근거: §3 참고. direction-log 52줄·draft-log 442줄·handoff 94줄은 4회차 결과(DOC 2, SCOPED 8, NOTE 11)와 맞지만 "코드 무결 4회 연속"은 틀렸다 → P1.

### 5.7 F. 규칙
- `main` = `origin/main` = `520b2be`(`git ls-remote` 같음), dev = `541068a` = `origin/dev`.
- 비밀값 패턴: `1373f3d..HEAD` 차이 0건, HEAD 트리 0건(개수만 셈).
- `python tools/intent_check.py` → total 62 flagged 0. `1373f3d..HEAD`에서 `[사용자]`가 든 줄 삭제 0.
- 파드 `/data` 밖: 검증 시작(01:17 UTC) 뒤 새 파일 0(`find -xdev -newermt "2026-09-25 01:17:00 UTC"`: `/`·`/tmp`·`/root`·`/home1`·`/var/tmp`·`/isaac-sim`·`/dev/shm`·`/opt`·`/usr/local`·`/etc` 각각 0). 내 프로세스 0. GPU 0–3 = 896 / 5 / 1 / 1 MiB(시작 때와 같음). 공용 `/data/harvest/canary`는 바뀌지 않았다(시각 08:57–08:59 KST 그대로). 라벨러(GPU 0, `cli_label`)는 건드리지 않았다.
- 로컬 C:: N13.

## 6. 다음 순회 전에 할 일 (제안, 모두 문서)
1. P1: `docs/handoff.md:3`을 실제 갱신 시각과 "4회차까지 FAIL(1회차 코드 DEFECT 2, 2–4회차 문서만)"로 고치고(이번 5회차 결과도 반영), `:94`와 `direction-log.md:52`의 "코드 무결 4회 연속"에 "→ 정정: 3회 연속(2·3·4회차)" 표시를 붙인다. 5회차 행을 쓸 때는 "코드 무결 4회 연속(2–5회차)".
2. P2: `r6_eval.md:54`와 `r5_closed_loop.md:98` 끝에 "→ **해결(pre-R7 519de26, `pre_r7_fixes.md` §1)**: `closed --backend fused`는 단계 B 실체크포인트 폴더(stageb.json + adapter/)를 받아 `runtime.fused_model` 서버로 돌린다(`closed.py:17-19,335-339`)"를 붙인다. 같은 김에 N2 목록(r6 6·7, r5 1, r4 §8 1·2·10)에도 해결 포인터를 단다.
3. 같은 사실 grep: 이번 5.2의 명령에 "상태 줄"(`마지막 갱신`, `회차까지`, `연속`)과 "해결된 열린 문제"(`실모델 없음|실물 모델 없음|mock_fused만|훅이 없다`)를 더한다.
4. (권장) N1: `M1-state-representation.md:119`에 정본 §47 정정 표시. N7: S-E2E 사전 등록에 검증 부분집합·`--eval-every`·중간 저장을 적는다. N8: 시작일 카나리를 새로 만든다.
