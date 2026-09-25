# R7 객관 검증 순회 — 7회차 (cycle 7, 연속 무결 카운트 1에서 시작)

- 검증자: 독립 검증 에이전트(이 코드의 작성자가 아님, 6회차 결론에 기대지 않고 다시 돌림). 작성 2026-09-25 02:45 UTC(`date -u`; 시작 표식 02:22:02 UTC, 파드 `date -u` = `Fri Sep 25 02:22:24 UTC 2026`(시작)·`02:41:55`(정리), 로컬과 같음).
- 대상: `D:\qdd` `dev` HEAD `3ed2e49` = `origin/dev`(`git ls-remote`), `main` = `origin/main` = `520b2be`. 작업 트리 깨끗(검증 전후 `git status` 출력 없음). `ac7095a..3ed2e49` 차이 = `docs/handoff.md`·`docs/stage3/direction-log.md`·`docs/draft-log.md` 각 1줄 + `r7_cycle6.md`(코드 무변경). 파드 사본 = `git -c core.autocrlf=false archive HEAD`, 폐루프 `meta.code_sha` = `f642bc0994e7cc54`(6회차와 같음 — 코드 무변경과 맞음), `stageb_data.py` HEAD 블롭 `a174e306…`, 체크포인트 `files_sha` `be1e6214d840`(6회차와 같음).
- 기준: `r7_cycle1.md` 점검 틀(A–G)·분류, `r7_cycle2.md`–`r7_cycle6.md`, `r7_fixes.md`, `r7_sweep6.md`, 정본 `00-interfaces.md` §1–§71(뒤 절 우선; §67–§71 SCOPED는 근거만 확인, [사용자] 제목 절 본문은 §67 규칙, 논문 .tex vLLM 서빙 서술은 §70에 따라 NOTE, `r7_sweep6.md` §3 열린 항목은 완료 정의 1–5를 막지 않으면 NOTE), 계획 `2026-09-25-e2e-ready.md` 완료 정의 1–5, 사전 등록 `docs/design/E-first-experiments.md`(해시 절 + §1.7 통계 공통)·`docs/stage3/prereg.json`·`docs/stage3/prereg_labeler.md`.
- 분류 기준(6회차와 같음): **DOC** = 지금도 참고되는 문서·주석의 현재 시제 서술이 HEAD와 다르고 정정·해결 표시가 없는 것. **DEFECT** = 코드가 정본·사전 등록 규칙과 다르게 동작하고 그 차이를 정한 기록(정본 결정·SCOPED)이 없는 것.
- 이번 판의 새 눈 영역(과제 2): (a) M4 확정 규칙·J5·epoch/전제·T1/T2 측정(§61/§64/§68)과 (c) 평가 스크립트 통계 ↔ 사전 등록 문서. (c)는 1–6회차 보고서에 `prereg`·`bootstrap`·`Holm` 점검 기록이 한 번도 없다(`grep`). (d) S-E2E 변환·로더도 실행으로 대조.
- 규칙 준수: 코드·문서 수정·커밋 없음(이 보고서만 씀). git은 `-c safe.directory=D:/qdd`. 로컬 임시 = `D:\tools\scratch_qdd\r7c7`(스크립트는 Write 도구로 D:에 씀, kubectl 경로는 `MSYS_NO_PATHCONV=1`). 파드 파일은 `/data/harvest/tmp/r7c7`(코드 사본·산출·체크포인트·pytest, 1.6 GB), Isaac kit 캐시 `ir/kitcache/cyclo-r7c7_standard`·`cyclo-r7c7f_standard`, 작업자가 만든 `cache/pyc_r6/data/harvest/tmp/r7c7`·`tmp/{carb.LUUTmB,carb.eBEGyM,tmpy5p6zbbu,tmpoktanvre,hub-root.lock}`(생성 02:23:27–02:38:47 UTC = 내 두 폐루프 판, `hub-root.lock` 생성 02:23:31), 융합 서버 빈 폴더 `tmp/fused_frames/2948756`, LeRobot 시험의 `cache/hf/datasets/parquet/default-f49e9c76a1c3eb5d`(+잠금)에만 썼고 **끝에 모두 지웠다**(02:41:55 UTC 확인, 남은 것은 공용 폴더 시각뿐). GPU: 단계 A·B 학습·CUDA 시험·융합 서버 = GPU 2(렌더 없음, 시작·끝 1 MiB), Isaac = GPU 1(시작·끝 5 MiB), GPU 0(라벨러 896 MiB)·GPU 3 건드리지 않음. 시드 DEV만, `HARVEST_ALLOW_SPLIT`은 가드 음성 시험 1건에서 `=dev`만. 유료 API 없음(Astra 모의). 비밀값 출력·검색 없음. 로컬 C: 사고 1건은 N14에 적었다.

## 판정: **FAIL**

| 분류 | 건수 |
|---|---|
| DEFECT | 1 |
| DOC | 0 |
| SCOPED | 8 |
| NOTE | 14 |

문서 쪽은 무결이다: 6회차 이후 바뀐 기록 3줄은 사실이고(§5.1), 전 저장소 같은 사실 grep(문구 + 구현 이름)에서 표시 없는 현재 시제 오류를 찾지 못했다(§5.8). 완료 정의 1–5도 직접 다시 돌려 모두 동작한다(§5.5). 그러나 이번 판의 새 영역 (c)에서 **평가 스크립트가 사전 등록 통계 규칙(에피소드 군집 부트스트랩 10,000회)과 다른 기본값(2,000회)으로 판정을 내고, 그 차이를 정한 기록이 없다**(E1). 코드 결함이므로 **연속 무결 1 → 0회**. 고치는 일은 기본값 한 줄씩(또는 정본 결정 + 기록)이라 작다.

---

## 1. DEFECT

### E1. 평가 스크립트의 부트스트랩 횟수 기본값 2,000 ≠ 사전 등록 10,000 (기록 없음, 출력에도 횟수가 남지 않음)
- 사전 등록: `docs/design/E-first-experiments.md:130`(§1.7 통계 공통, "네 실험 모두") "95% 구간은 **에피소드(또는 스냅샷의 에피소드) 군집 부트스트랩 10,000회**". 같은 값: `EVAL-evaluation-design.md:184,317`(10,000회), 옛 단계 3 계획 `2026-09-24-stage3-experiments.md:1525`(E0.5 분석 "에피소드 군집 부트스트랩 10,000회, Holm"). 단계 3 결과 문서들도 이 규칙대로 10,000회를 썼다(`jevl_model_select.md:8,26`, `e3lite.md:32`, `stageA_sft.md:25`, `stageA_generalize.md:22`). 예외는 자기 사전 등록(D28 §4)에 2,000회를 적은 `e_m4b_meas.md:94`뿐이다.
- 코드(완료 정의 4의 "한 명령" 스크립트): `harvest/eval/e05.py:437`, `harvest/eval/rd.py:154`, `harvest/eval/calib.py:76`, `harvest/eval/closed.py:282` 모두 `--n-boot` 기본 **2000**. 라이브러리 기본값도 2000: `e05.py:165,173,183`, `runtime/calibration.py:103`(`evaluate`), `eval/closed.py:54`(`aggregate`), `harvest/canary.py:19`.
- 이 구간이 곧 사전 등록 판정의 입력이다: E0.5 판정 1–3·7–9의 하한(`e05.py:379-406` `gain_la2_lo`·`c2prime_minus_la2` ci·`a1_minus_a0_lo`·`subst_minus_floor` ci), E1 판정 1·8의 ECE 상한·AUROC 하한·θ 구간 정확도 하한·J5 커버리지 하한(`runtime/calibration.py:171-192` `judge_question`). 즉 문서(`r6_eval.md:11-13`)에 적힌 명령을 그대로 치면 사전 등록과 다른 절차로 판정이 나온다.
- 기록 없음: 정본·계획·`r6_eval.md`·R7 보고서 어디에도 2,000회를 정한 줄이 없다(`grep -rn "n.boot\|2,000회\|10,000"` docs 전체). 출력 `e05.json`·`calib.json`·`rd.json`·`closed.json`에는 횟수가 남지 않는다(`grep n_boot` 0건; `meta.argv`는 인자를 줬을 때만 보인다).
- 확인(파드, 모의 모델, DEV): 같은 입력으로 `e05 --n-boot 10000` → EXIT 0, 10 s(2,000회 판 2.7 s), `calib --n-boot 10000` → EXIT 0, 7 s. 즉 10,000회는 비용 문제가 아니다.
- 고칠 것(제안): 네 CLI와 라이브러리 기본값을 10000으로(또는 2,000을 정본 결정으로 적고 근거를 남김), 그리고 출력 `meta`에 `n_boot`를 싣는다. 판정 10의 Holm 대용(N3)도 같은 때 정리하면 좋다.

## 2. DOC

없음.

## 3. SCOPED (통과에 영향 없음, 근거 재확인)
- S1. `LatencyChargingController` 스텁(`runtime/latency_ctrl.py:9`, 정본 §71 보충) — 로컬·파드 모두 `tests/runtime/test_latency_ctrl.py:11` 1개 건너뜀. 근거(기준선 비교는 본 실험 단계)는 완료 정의 4(E0.5·RD·CAL, 기준선 없음)와 맞다.
- S2. 본 단계 B 학습·R2_TRAIN 대량 생성(§66 "S-E2E 이후"). `gen --confirm-train` 없이 R2_TRAIN 시드 거부 확인(§5.6).
- S3. CAL 보정·TEST 평가(메인 세션만, `HARVEST_ALLOW_SPLIT`). 가드는 §5.6.
- S4. RB1 라이선스(§63-(6)).
- S5. §67 C8 목록 — 코드 그대로: `core.py:355`(patch/replace = epoch만), 융합 판 `VerifyCal.default()`(`core.py:110`, 이번 융합 판 `measure.verify_calibrated false`).
- S6. Astra 카나리 id "none" — 이번 두 폐루프 판 `astra` 행 2/2·2/2에 명시.
- S7. S-E2E 체크포인트의 aiworker 런타임 tau 마스크 채널 차이(`r7_fixes.md` §7).
- S8. CONTRADICT-soft(§68 K6, §69 근거 보정) — `measure.expected_check`는 여전히 단일 DEVIATE(§5.2 행동 시험).

## 4. NOTE
- N1. **`docs/handoff.md:3` "마지막 갱신: 2026-09-25 01:48 UTC"** — 3ed2e49(커밋 2026-09-25 02:20:29 UTC)가 같은 문서 `:98`에 6회차 줄을 더했는데 머리 시각은 그대로다. 같은 줄이 "회차별 판정·연속 무결 횟수는 §2.8 마지막 줄"을 가리키고 그 줄(`:98`)이 맞으므로 6회차 N12와 같은 판단으로 NOTE로 둔다. 정본 §71이 `마지막 갱신`을 정정 grep 목록에 넣었으니 **E1을 고칠 때 이 시각도 함께 고치거나 시각을 빼기를 권한다**(다음 순회에서 DOC로 볼 여지가 있다).
- N2. **M4 유예 창 W의 뜻(코드 ↔ 정본 §5 문장)**: `m4.py:166-177`은 M4 §4.2 의사코드 그대로 첫 도전 표에 `defer_left = W`, 같은 도전 표마다 1 빼고 0 이하면 교체 → 행동 시험(§5.2): W = 1이면 도전 표 **2개**에서 교체, 비가역이면 3개. 그런데 정본 §5(`00-interfaces.md:35`)·M4 §4.4 표는 "M5 L1의 '연속 2표'는 **W = 2** 설정으로 흡수"라고 적는다(코드로는 W = 2 = 3표). 또 W = 0도 첫 도전 표에서 바로 바꾸지 않아 W = 1과 같다. 기본값(W = 1)과 모든 조건(`conditions.py`에 W 덮어쓰기 없음)은 영향이 없다. E-M4 변수 절제(W ∈ {0, 1, 2}, M4 §4.4)의 사전 등록 전에 W의 정의를 정해야 한다.
- N3. **E0.5 판정 10의 Holm 대용**: 사전 등록 §2A.6-10(해시 절)은 "블록 여러 개면 Holm", 코드 `e05.py:183-197`는 쌍마다 Bonferroni 수준 구간의 최대 부호 하한(docstring에 "stand-in for Holm on intervals"). 더 보수적이고 기본 `--blocks 2`(쌍 1개)에서는 같다. 블록을 3개 이상 쓸 때 전에 정본에 적거나 Holm으로.
- N4. **E1 ECE 구간 방식**: E §3.4는 "ECE(15개 동일 질량 구간)", 판정 1(`calibration.py:176`)은 등폭 15구간 `ece_cal`과 그 부트스트랩 상한을 쓴다(등질량 `ece_cal_mass`는 계산·보고만, `r6_eval.md:13` "등폭·등질량"). 해시 절 §3.7은 구간 방식을 적지 않았다 — E1 실행 전 어느 쪽으로 판정하는지 적어 둘 것.
- N5. `eval/closed.py:103-118` 폐루프 RD 구간은 (시드, epoch) 짝을 한 단위로 다시 뽑는다(시드 군집 아님). `--epochs 1`이면 같다.
- N6. **융합 폐루프 결정 지연이 6회차보다 크다**: 이번 R2 체크포인트 융합 판(DEV 시드 7) 결정 55·청크 59·오류 0이지만 결정 지연 p50 **1.62 s** / p95 4.39 s(서버 `t_decide_s` 0.49–6.82 s; 6회차 p50 0.331 s), 청크 0.09–0.83 s. GPU 2는 비어 있었고(1 MiB), 파드 CPU 쿼터 32코어에 load 27–35(라벨러 2 × 263 %) → CPU 경합이 유력하나 원인은 따로 재지 않았다. 완료 정의 2·3(서빙이 끝까지 돎)은 충족, S-E2E 학습과는 무관. 본 실험·R3 처리량 수치를 옮길 때 파드 CPU 부하를 함께 기록할 것.
- N7. (6회차 N1 재확인) 융합 판 `closed.json` `meta.prompt_config` = 모듈형 구성(`camera HW, state S1`), 모델은 IMG·D27v1를 받음. 모의 판은 `layout H`인데 호출 행 `image_sha256`에 `cam_wrist_right`도 있다 — 해시는 런타임이 넘긴 프레임 전체이지 H 배치 모델이 본 것만이 아니다. 두 가지 모두 표기 문제(필수 필드는 있음).
- N8. 6회차 N2–N6 그대로(handoff `:46`·`:55` 날짜 붙은 옛 절, `stageA_pipeline.md:53` 등 당시 기록, `CLAUDE.md` Jev 서술, `stageb_data.py:15`(PROMPT_FILES_B라 표시 금지, §71), 논문 vLLM 서빙(§70)).
- N9. `r7_sweep6.md` §3 열린 항목 코드 재확인 — 모두 여전히 열림, 완료 정의 1–5를 막지 않음: 잔차 체크포인트 거부 `fused_model.py:126`, θ 게이트 런타임 없음, 계약 편집 = epoch만 `core.py:355`, aiworker P1/P2 `aiworker.py:130`, `jevcall.PROGRESS` 보기 이름(`tests/test_jevcall.py:28`).
- N10. 카나리: 모의 판 `meta.canary` = `cn20260924_mock_ae0d1a`, `stale: true`; 융합 판 `{"id": "none", "reason": "no canary for model fingerprint caa77d6071f2e90e"}`. §68대로 S-E2E 시작일에 새로 만든다.
- N11. TEST2 1150–1299는 `splits.RANGES`에 없다 — `check_layout_seed(1150)`·`(1299)` 거부 확인. 연장을 실제로 쓸 때 넣을 것.
- N12. §69 S-E2E 사전 등록 항목(층화 검증 부분집합·중간 체크포인트·평가 간격)은 여전히 코드 선택지가 없다: 이번 판도 n_val 1,799 중 `--max-val 4` = 앞 4개.
- N13. 파드 공용 폴더의 남의 잔여물(지우지 않음): 1회차의 `code_r7c1`·`cache/pyc_r7c1`·`cache/pyc_r7c1b`·`ir/kitcache/cyclo-r7c1{bf,bm,c,f,m}_standard`, `tmp/fused_frames/{2789848,2810373}` 빈 폴더, `tmp/carb.*`, `tmp` 전체 1.9 GB. draft-log `:444`가 적은 `tmp/r7c1` 삭제는 사실(없음 확인). 모두 /data 안.
- N14. **로컬 C: 위생(내 실수 1건 포함)**: (1) 검증 초반 Git Bash 명령 하나에 빈 heredoc(`python - <<'EOF'` / `EOF`)을 실수로 넣었다 — 내용 없는 heredoc이라 파일을 만들지 않았고, Git Bash가 쓰는 임시 파일(`%TEMP%\sh-thd*`)은 남지 않았다; 파이썬이 대화형으로 떠 내가 띄운 프로세스(PID 53467)만 종료했고 `~/.python_history`는 생기지 않았다. (2) 시작 표식 뒤 C:에서 바뀐 것: `.claude`·`.claude.json`·`AppData\Roaming\npm`(하네스), `AppData\Local\Temp\claude\…`(하네스 배경 작업 출력), 그리고 `AppData\Local\Temp\f6fe8abc-f118-4098-9d3f-8508191b85de.tmp`(0바이트, 02:36:24 UTC — 출처 확인 못 함, 이 저장소 산출물 아님, 지우지 않음). `pytest-of-USER`·`torchinductor_USER` 없음. 로컬 스위트는 TMP/basetemp 모두 D:.

---

## 5. 확인한 것 (근거)

### 5.1 6회차 이후 바뀐 기록(과제 1)
| 위치 | 주장 | 확인 |
|---|---|---|
| `handoff.md:98` | 6회차 02:20 UTC PASS, DEFECT 0·DOC 0·SCOPED 8·NOTE 14, sweep6 표시 28개, 융합 실체크포인트 폐루프, 연속 무결 1회, 코드 무변경 | `r7_cycle6.md:9-16,67-97,124` 그대로. 3ed2e49 커밋 = 02:20:29 UTC. `git diff --stat ac7095a HEAD`에 코드 없음 → "코드 무변경" 사실 |
| `direction-log.md:54` | "코드 무결 5회 연속(2–6)" | 1회차 DEFECT 2, 2–6회차 DEFECT 0 → 5회 맞음 |
| `draft-log.md:444` | 6회차 PASS 수치, "파드 1회차 잔여 `tmp/r7c1`(2 GB) 삭제" | 수치 맞음, `/data/harvest/tmp/r7c1` 없음(`ls`). `code_r7c1` 등은 삭제했다고 적지 않았음(N13) |
| `handoff.md:3` | 마지막 갱신 01:48 | N1 |

### 5.2 새 눈 영역 (a) M4 확정 규칙·측정 — 정본·M4 §4.2와 일치 (행동 시험 `D:\tools\scratch_qdd\r7c7\m4_probe.py`, 로컬, 쓰기 없음)
- `CommitLedger` 실행 결과: 첫 표 → `tentative`; 도전 표 1 → `challenger`, 2 → `replaced`(W = 1); 표 나이 > STALE_MAX 1.5 s → `dropped_stale`; `premise_epoch` < 원장 epoch → `dropped_epoch`(#6); 새 epoch 표 2개 합의 → LA-2 확정 `[10]`; 확정 칸·시작된 칸 → `log_only`(#1); (b) = LAG 뒤 도전 표 → 즉시 `replaced`(gate_hard); 비가역 도전 → `challenger, defer, replaced`(W+1, §4.6); DEVIATE → `{epoch 1, early_call, hold False, reopened 1}`, CONTRADICT → `{…, hold True}`(정지 아님, 직전 확정 유지 + 감속 = `core.py` `hold_step`); d̂ 0.307에서 N_max 2 = ⌈d̂/T_c⌉+1. 설정값 T_c 0.33·STALE 1.5·γ 0.67·FLIP_TH 끔 = 정본 §7 설정 표·§6(E1 전 게이트 끔).
- J5(`core.py:306-337`): 보정 파일 + `j5_alpha`일 때만, 원소 하나면 그 보기로 표, 둘 이상이거나 NE 포함이면 표를 넣지 않음(칸은 가진 것 유지), 2회 연속이면 하트비트 앞당김 = 정본 §31 J5·M4 §4.1 J5 몫. `Calibration.load`가 모델 지문·question_id 불일치를 거부.
- 측정(§61/§64): `ProprioRules` 기본값 = 파드 `/data/harvest/m4b/results.json` `m4b.P_params`(5개 모두 비트 동일: 80.5 mm·50.1 mm·80 mm·1.136·12.4 cm), critic 문턱 `critic.V1h.thr.v1h` = 0.94737(= `measure.py:13` "0.947"), V1h q̂ 0.003–0.179(near_tp 2.8e-6은 양성 1개로 평가 제외, `e_m4b_meas.md:155`) = `e_m4b_meas.md:247` "0.003–0.18". `conformal_value`: 둘 다·빈 집합 → None(unknown, §64). `measure()` 출처 표: gripper_open·holding_t·lifted_holding = proprio T1, 나머지 = V1h T2. `expected_check`: T1 거짓 → CONTRADICT(하드), T2 {거짓} → DEVIATE, unknown → 판정 없음. 스킬 CONTRADICT(`skills.py:141,147,150`)도 T1 값(`core._exec_pred`)으로만 난다. critic = V1h 단독(PC3), 하드 채널 2회 연속(PC2) = `measure.py` `Critic`·`HardChannel`.
- 차이는 N2(W의 뜻) 하나 — 의사코드를 그대로 옮긴 것이고 기본 동작은 정본과 맞다.

### 5.3 새 눈 영역 (c) 평가 통계 ↔ 사전 등록
- `python tools/prereg_hash.py --check` → **OK**(E-first §2.7·§2A.6·§3.7·§4.8·§5.6 해시가 `prereg.json`과 같음 — sweep6의 E-first 머리 안내 줄은 판정 절을 건드리지 않았다).
- E0.5 `analysis/replay.judge_e05` ↔ §2A.6: 판정 1(flip < 5 % ∧ 두 이득 < +2 %p), 2(flip ≥ 5 % ∧ 이득 ≥ +2 %p ∧ 하한 > 0), 3, 4(섭동 flip ≥ 2 × 성공 flip ∧ AUROC ≥ 0.7, 차 ≥ 0.03이면 그 식, 아니면 표 분포 거리), 5(재시험 빼기), 6(< 1 %), 7(C2′ − LA-2 ≥ +2 %p ∧ 하한 > 0), 8(치환 − 바닥 하한 > 0), 9(중립/유지/순서 A4 ≥ 5 %), 10(N3) — 모두 문턱이 같다. `la2`의 γ = 2/3, 순서형 없음.
- E1 `calibration.judge_question` ↔ §3.7: ECE ≤ 0.05 ∧ 상한 ≤ 0.08, AUROC ≥ 0.75 ∧ 하한 ≥ 0.70(오답 < 30이면 판정 불가, §3.4), θ 구간 정확도 ≥ θ − 0.03 ∧ 하한 ≥ θ − 0.08 ∧ 적용률 ≥ 20 %, J5 커버리지 하한 ≥ 1 − α − 0.03 ∧ 원소 하나 ≥ 50 % ∧ 원소 하나 정확도 ≥ 1 − α, 적합 < 400이면 "보장 없음". 온도: 원 ECE ≤ 0.03 ∧ T ∈ [0.8, 1.25]면 원 확률(§3.6). split conformal q̂ = ⌈(n+1)(1−α)⌉번째. ECE 구간은 N4.
- 공통 통계 `analysis/stats.py`: 군집 부트스트랩·짝 차(같은 군집 id 공유)·Holm 단계 하강 — 구현은 맞다. **횟수 기본값이 E1**.
- 라벨 점수식 사전 등록(`prereg_labeler.md`) ↔ `sim/labeler.select_rule`: 적격 ≥ 0.90, 판별력 최대, 0.02 안이면 단순한 쪽(plan > time > short, 긴 h). 파드 원자료 `/data/harvest/data/pool_selfcheck/*.jsonl`(90편·900 스냅샷·4,970줄)로 HEAD 코드가 다시 계산(읽기만): plan 0.986/0.025, time0.66 0.872/0.167, time0.33 0.796/0.353, short3 0.745/0.469, short2 0.696/0.556, short1 0.578/0.677 → **선택 plan** = 정본 §65 수치와 전부 같다.

### 5.4 새 눈 영역 (d) S-E2E 변환 ↔ §62/§63 (실행 확인)
- `se2e_data.py`: `CHUNK_S` 0.5 → H 5, `HORIZON_S` 1/3 → 3스텝 = 0.30 s(§62 "가장 가까운 스텝 수", §63 "다음 0.30 s"), `LABEL_SRC` `se2e_heur_ee033@v1`, 검증 분할 = crc32(kind:ep) % 100 < 5, RB1 손목 90° 회전(`se2e_convert.py:36`), 카메라 없는 행 건너뜀(RB2 617–816).
- 단계 B 진입점 실행(§5.5 정의 2): `config` 행 `data se2e, hz 10, H 5, n_val 1799`(= §63), `grip_space open01@v1`, `grip_src [RB1, RB2]`, `proprio_masked 40`(= 40표본 전부 tau 마스크), `train_arms {left 20, right 20}`, `expert.proprio_dim 27`(= 23 + 마스크 4), `norm.arms` 왼/오 통계 다름(mean[0] 0.1425 / 0.5558).

### 5.5 완료 정의 1–5 순회 (이번 판에서 직접 돌린 것)
| 정의 | 판정 | 실행 |
|---|---|---|
| 1 데이터 | 충족 | R2 DEV 36편 `validate_episode`만(스탬프 안 함): **36/36 구조 이상 없음**, 모든 시드 DEV, 성공 mug_tray 12/12·mug_marker 12/12·bottle_tray 8/12(= §66). LeRobot 내보내기 시험(`venv_e3st` + `pylib_lerobot`) **6 passed**. S-E2E 로더는 §5.4. |
| 2 모델 | 충족 | **단계 B S-E2E**(GPU 2): `stageb_train train --data se2e --run r7c7_se2e --max-train 40 --max-steps 6 --batch 2 --max-val 4 --eval-every 3 --reload-check --seed 7` → EXIT 0(02:23:25–02:24:20 UTC), 검증 dec 3.526 → 3.817 → 2.036, `save_load` `max_abs_action_diff` **0.0**, `eval_equal`·`norm_equal` true. **단계 B R2**(GPU 2): `--data r2 --pool …/standard/mug_tray/P0,…/dr/mug_marker/P0 --dev-val-seeds 5 … --reload-check --seed 13` → EXIT 0, `save_load` 차 **0.0**. **서빙**: 이 R2 체크포인트로 `closed --backend fused`(정의 3 (b)). **단계 A**(GPU 2): `stagea_train train --run a_c7 --max-steps 4 --max-train 96 --max-val 24 --accum 16 --eval-every 2 --seed 41` → EXIT 0, NLL 6.030 → 2.001 → **1.3780686060587566**; `load --adapter best --n 24 --seed 41` → **1.3780686060587566**(비트 동일). CUDA 시험(GPU 2) **26 passed**. |
| 3 폐루프 | 충족 | (a) `closed --model mock --split dev --seeds 3 --max-seconds 40 --astra mock --isaac-gpu 1 --inst-prefix r7c7`(02:23:25–02:25:57) → `CLOSED_DONE`, **성공 14.92 s**, 호출 45·오류 0, RTF 0.854, M4 epoch 3, Astra 2, commit_ratio 0.861. 부가 JSONL(`call` 45·`step` 46·`astra` 2·`event` 11·`m4` 3): `call` 45/45 64자리 hex `request_sha256`(45개 모두 다름), `image_sha256` {cam_head, cam_wrist_right} 45/45 hex, `canary_id` `cn20260924_mock_ae0d1a` 45/45; `astra` 2/2 요청 해시(다름) + `image_sha256` {cam_head} + `canary_id` "none". `meta.code_sha f642bc0994e7cc54`, split dev, seeds [3]. (b) **융합 실체크포인트**: `closed --backend fused --model ckpt/r7c7_r2/last --split dev --seeds 7 --max-seconds 20 --astra mock --isaac-gpu 1 --gpu 2 --inst-prefix r7c7f`(02:38:15–02:41:02) → `CLOSED_DONE`, 끝까지 돎(`max_steps`, 6스텝 모델이라 성공 요구 아님), `call` 55/55·`chunk` 59/59·`astra` 2/2 모두 hex 요청 해시(모두 다름)·이미지 해시·`canary_id`("none", 이유 명시), 오류 0, `measure` 56행, M4 epoch 54, RTF 0.757. 지연은 N6. |
| 4 평가 | 충족(통계 기본값은 E1) | 모의 모델 한 명령(`venv_vllm`, GPU 없음): `e05 --split dev --episodes 2` → `E05_DONE`(claim a_as_stabilizer), `rd --variants standard=… --split dev` → `RD_DONE`, `calib --fit-data pool --fit-split pool --heldout jsel_dev/P0 --heldout-split dev --episodes 4` → `CALIB_DONE`(`calibration.json`). 모두 EXIT 0. `--n-boot 10000` 판도 EXIT 0(E1). |
| 5 운영 | 충족 | 산출 모두 `/data/harvest` 아래, `meta`에 `code_sha`·카나리·시드·모델 지문, `model_rev ebb281ec…` 고정, 체크포인트 `files_sha` 대조(`stageb_data.py` `be1e6214d840`). |

### 5.6 C. 가드 (파드, 변수 없이, `CUDA_VISIBLE_DEVICES=""`; `guard_out`은 끝까지 비어 있었음)
- 평가: `e05 --split cal`·`--split test_p5`, `rd --split test`, `calib --fit-split cal`·`--heldout-split test`, `closed --split test --seeds 1000`·`--split cal --seeds 549` → "--split X refused: set HARVEST_ALLOW_SPLIT=X (main session only …)". `closed --split dev --seeds 499|1149|1329|2119|59999|3100` → "seeds [..] are not in split dev range(0, 30) (refused, never opened)". `HARVEST_ALLOW_SPLIT=dev closed --split test --seeds 1000` 거부. `--isaac-gpu 2` → "0 or 1 only (GPU 2 never renders)".
- 생성: `gen --seeds 10005-10006`(확인 인자 없음) 거부, `--confirm-train`과 함께 549·3199·1300·9999·30 거부, `--variant random` → "TEST pool … use 'dr'", `replay --seed 1000` 거부. `check_r2_seed`: (0,F)(29,T)(10000,T)(59999,T) 허용, (30,F)(10000,F)(60000,T)(549,T)(3000,T)(2000,T)(1329,T) 거부.
- `aiworker.check_layout_seed`: 0·29 허용, 30·499·500·549·999·1000·1149·1150·1299·1300·1329·2000·2119·3000·3199·10000·59999 거부.
- `splits.RANGES` = {dev 0–29, cal 500–549, test 1000–1149, test_p5 1300–1329, pool 2000–2119}, `PROTECTED` = (cal, test, test_p5) = 정본 §66 + R2_TRAIN 10000–59999(`gen.py:35`), 시험 시드 3000–3199(`test_randomize_logic.py:13`).

### 5.7 A. 테스트
- 로컬(Git Bash, `python -m pytest -q -rs -p no:cacheprovider`, TMP = `D:\tools\scratch_qdd\r7c7\tmp`, basetemp = `pytest.ini`의 D:): 2회(72 s / 70 s) 모두 EXIT 0, 진행 표시 **784 통과 · 건너뜀 표시 6**(요약 11: torch 없음 7, inspect_robots 2, pyarrow 1, TODO(P3) 1), F·E 0. 실행 뒤 `git status` 깨끗, `docs/stage3/qid_registry.json` 생기지 않음.
- 파드 CPU(`venv_train`, PYTHONPATH = 코드 사본 + IR 4경로, `CUDA_VISIBLE_DEVICES=""`): **826 passed, 3 skipped** 두 번(EXIT 0, 74 s / 70 s). 파드 GPU 2: 26 passed. 파드 LeRobot: 6 passed.

### 5.8 같은 사실 grep (과제 3, `D:\tools\scratch_qdd\r7c7\g.py` — 추적 파일, `paper/`·`third_party/`·R7 보고서 제외, 표시 유무 분리)
- 구현 이름 `vLLM` + decide/fused/StageB/융합: 표시 없는 7줄 모두 모듈형 = vLLM, 융합 = fused HF 서버로 구분(`closed.py:18`, `fused_model.py:15`, `canary.py:9,257`, `pre_r7_fixes.md:24`, `r6_eval.md:14`, `r7_fixes.md:40`). `StageBFused|fused_model|HF 백본`: 코드·문서 모두 HF 서버로 일치.
- `one call|한 번 호출|모델 한 번`: 표시 없는 것은 §58 [사용자] 절(`00-interfaces.md:511`, §67 C4), DecCall 하나·in-flight 뜻(`jevl.py:8`, `conditions.py:5,11`, `models.py:1`, `jevl_mmbench.py:3`, `r5_closed_loop.md:33,96`, `jevl_latency.md:36,79`).
- `[제안]|[proposal]`(단계 3 문서·코드): `e3st.md:104,149`(지금도 제안), `CLAUDE.md:62`·`handoff.md:13`(표기 규칙·옛 절). R2_TRAIN을 제안으로 적은 표시 없는 곳 0.
- `500–699`: 표시 없는 것은 `tests/datagen/test_gen_guards.py:20`(거부 범위 주석, 맞음).
- `2026-09-25 … UTC`: [사용자] 제목 §56·§57·§58·§62(§67 C1), §68 K1(정정 서술), `handoff.md:3`(N1), `r7_fixes.md:6`(실제 UTC). 잘못된 UTC 날짜 0.
- `GPU 2` + 금지/never/렌더: 모두 렌더 금지 뜻(`closed.py:11,36,141,331`, `ir_run.sh:56`, 계획 `:40`)이거나 당시 기록. 현재 시제 "GPU 2 금지" 0.
- `102°|fx 272|ZED_M|D-stereo`: `e3st.md:138`(머리 `:7` fx 정정이 1–7절을 덮음), `e3st.md:154,268-270,326`(재계산 기록), `cli_e3st.py:19-20`·`test_stereo_metrics.py:36`(옛 값 재현 옵션), `planner_dev.md:139`·`scene_bringup.md:91,114,129,179`(쓰지 않았다는 기록), `handoff.md:50`(`:51` 정정 줄).
- 정본 범위 `§1~§N`: `handoff.md:3` §1~§71(맞음), `:27`·`:82`(옛·날짜 붙은 절, N8), 단계 2 문서 당시 범위.
- `\bJev\b`: 단계 3 코드는 옛 도구마다 "unusable (user-log 46)" 표시(`canary.py:3`, `cli_e0.py:3`, `clients/jev.py:3`, `jev_smoke.py:3`, `config.py:17`), `r4_stageB.md:40` 표시, `stageb_data.py:15`(N8), `CLAUDE.md`(N8). Jev를 지금 쓰는 선택기로 적은 곳 0.
- `20 Hz`: 모두 풀·라벨·계획기 경로의 옛 20 Hz(`scene.py:377,584`, `planner.py:192-194`, `skills.py:41`, `gen.py:37`, `m4b/fidev.py:8,255`) 또는 "기존 20 Hz 동작 유지" 기록. 우리 수집 주기를 20 Hz로 적은 곳 0(R2 30 Hz, S-E2E 10 Hz = §62; 이번 S-E2E 판 hz 10 확인).
- `진행 중|아직|미구현`: `handoff.md:85`(21:03 기준 + "R2·R6은 이후 완료 — §2.8" 표시, 결과 라벨은 지금도 진행 — 파드 `cli_label` 경과 11:31:35 확인), 결과 문서의 "이 시각 전에 한 일"(당시 기록), `r4_stageB.md:39`(VQA 원천 없음 — 사실, SCOPED), 코드의 보기 문구.
- 시드 문장: DEV 0–29 / CAL 500–549 / TEST 1000–1149 / TEST-P5 1300–1329 / POOL 2000–2119 / R2_TRAIN 10000–59999 / 시험 3000–3199 밖의 값을 현재 시제로 적은 곳 0.
- 카메라(§47): 머리 ZED Mini 왼쪽 672×376·fx 367(85°), 손목 D405 424×240·fx 223.4(87°) — `scene.py:11`, `aiworker.py:8,34`, `cli_e3st.py:50`, `se2e_data.py:5`, `scene_bringup.md:34-40`, `test_challenge_cameras.py:31,41`, `test_stageb_qwen.py:54`에서 모두 같다.

### 5.9 F. 규칙
- `main` = `origin/main` = `520b2be`, dev = `3ed2e49` = `origin/dev`.
- 파드 `/data` 밖: 검증 시작(02:22 UTC) 뒤 새 파일 0(`find -xdev -newermt`: `/`·`/tmp`·`/root`·`/home1`·`/var/tmp`·`/isaac-sim`·`/dev/shm`·`/opt`·`/usr/local`·`/etc` 각각 0, 정리 뒤 다시 0). 내 프로세스 0. GPU 0–3 = 896 / 5 / 1 / 1 MiB(시작 때와 같음). 공용 `canary`·`r2/dev`·`m4b/results.json`·`data/pool_selfcheck`는 읽기만. 라벨러(GPU 0)는 건드리지 않음.
- 로컬 C:: N14.

## 6. 다음 순회 전에 할 일 (제안)
1. **E1 수정**: `e05`·`rd`·`calib`·`closed`의 `--n-boot` 기본값과 `calibration.evaluate`·`closed.aggregate`·`e05` 도우미·`canary.canary_compare` 기본값을 10000으로(또는 2,000을 정본 결정으로 적음), 출력 `meta`에 `n_boot` 기록, 시험 1개(기본값 = 사전 등록 값). 코드 변경이므로 연속 무결은 0부터 다시 센다.
2. 같은 편집 묶음에서 N1(handoff 머리 시각)과, 원하면 N3(판정 10 Holm)·N4(E1 ECE 구간 방식)를 정본 한 절에 적어 두면 다음 순회의 판단 여지가 줄어든다.
3. S-E2E로 넘어갈 때(연속 2회 뒤): N10 시작일 카나리, N12 검증 부분집합 층화·중간 저장·평가 간격을 사전 등록에, N6(파드 CPU 부하)을 지연 수치와 함께 기록.
4. E-M4 사전 등록 전: N2 W의 정의(W = 0이 "즉시 교체"가 되도록 할지, 정본 §5 "W = 2 흡수" 문장을 고칠지).
