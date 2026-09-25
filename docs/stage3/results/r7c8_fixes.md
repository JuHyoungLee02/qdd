# R7 8회차 지적 수정 (DEFECT D1–D5, DOC D-1·D-2, NOTE N5·N8)

- 작성 2026-09-25 04:30 UTC(`date -u`). 대상 `D:\qdd` `dev` HEAD `aad30d6` + 작업 트리(커밋·푸시 안 함 — 메인 세션). 입력 보고서 `docs/stage3/results/r7_cycle8.md`(판정 FAIL, DEFECT 5, DOC 2).
- 원칙: 사전 등록(`E-first-experiments.md`·`EVAL-evaluation-design.md`·`prereg.json`·`prereg_labeler.md`)과 정본은 구속한다 — 코드는 사전 등록의 값·방식을 그대로 구현하고, 사전 등록이 열어 둔 값은 정본 §73에 적었다(값마다 근거 한 줄). 결정 D1–D5·N5·N8은 메인 세션이 내린 것을 구현했다.
- 건드리지 않은 파일: `stagea_train.PROMPT_FILES` 9개, `train/stageb_data.py`·`stageb_model.py`(체크포인트 `files_sha`, §71) — `git diff --name-only`에 없음. `[사용자]` 줄·사용자 인용 줄은 지우거나 바꾸지 않았다(바뀐 문서 줄 6개 중 '사용자' 포함 0). 정본은 끝에 §73만 덧붙였다(§72 본문 무변경).
- 로컬 임시 = `D:\tools\scratch_qdd\r7c8fix`(aad30d6 사본 `base/` = `git archive`, 대조 스크립트). C: 쓰기 없음(§7 사고 1건 참고).

## 1. 무엇을 바꿨나

| 항목 | 사전 등록·정본 | 코드 |
|---|---|---|
| **D1** E0.5 판정 2 Holm | E §1.7(:131) "한 판정에 여러 조건을 걸면 Holm", §2A.6-2(:257) "LA-2 또는 C2''" | `e05.gain_holm`(:199) = `stats.holm_ci`로 두 이득(LA-2 − newest, C2'' − newest, 에피소드 군집, 같은 뽑기)의 Holm → `judge_input.gain_holm`·`judgments.j2_gain_holm`(가설별 reject·lo·hi·level). `replay.judge_e05`(:29–38): 판정 2 = 점추정 ≥ 0.02 ∧ Holm 기각 ∧ 하한 > 0인 규칙이 하나라도. 보정 없는 `gain_*_lo`는 판정 입력에서 뺌(95% 구간은 `rules.pooled`에 남음) |
| **D2** E1 `ambiguous` | E §3.10(:359) "본 ECE에서 빼고 따로 보고", 정의 E §1.5(:121) 히스테리시스 띠 | `calib.items_from`(:52) 항목에 `ambiguous`; `calibration.evaluate`(:108–150) 모든 ECE(판정 `ece_cal_mass`·구간, 보고 `ece_raw`·`ece_cal`)는 애매하지 않은 항목(`n_ece`), `ambiguous` {n, ece_cal_mass, ece_cal, acc} 따로; `fit_question`(:86–97) §3.6 원 확률 ECE도 제외(`n_fit_ambiguous`); `judge_question`(:193) ECE 없음 → 불합격; `calib.md` 열 "ambiguous n (ECE mass, apart)", `meta.ece` 설명 |
| **D3** 카나리 표류 | 정본 §28(:264)·E §1.8(:139) "하한 > 0, Holm", 군집 E §1.7(:130) | `harvest/canary.canary_compare`(:31–54): 질문마다 (불일치 − 바닥) 에피소드 군집 구간(`episode_of_key` :25, `<kind>_ep<seed>_k<k>` → 편), 질문들에 `holm_ci`, 표류 = 하한 > 0 기각 하나라도; "> 2×바닥" 삭제; 결과 `per_question`·`n_clusters`·`boot_unit`; n_boot = `N_BOOT`. `eval/canary.py` 머리 설명("no Holm correction here" 삭제) |
| **D4** C5 τ 접촉 근처 0 | E §4.12(:487), M4 §4.4(:277)·§4.6(:307), 정본 §7 near/contact 정의(:46) | `core.near_contact`(:42–54) = 단계 목표(o3 → lift까지, 그 뒤 o5)까지 ≤ `CFG.near_in_m` 또는 그리퍼–목표(목표 o5면 o3–o5도) 접촉; `act`가 배달 직전에 `self.near_now`(:435) 계산 → `on_vote(..., near=)`(:282)·`try_commit_prefix(..., near=)`(:441, :503); `m4.try_commit_prefix(q, now, near=False)`(:208, :221–223 `_agrees(..., near)`) |
| **D5** M4 설계 확장 | 사전 등록 C5 = 평탄 W 1·γ 0.67(E §4.12) | 구현 안 함 → 정본 §73 SCOPED, `m4.py` 머리 "Not implemented"(:24–29)에 경계 직후 W 2·γ 1.0, g 0.5·장면 변화 조기 호출, (b) 미확정 실행 엄격화 |
| **D-1** handoff 정본 범위 | — | `handoff.md:3`·`:5`·`:83` → §73(머리 구조 유지, 횟수 없음), §2.8 8회차 줄 |
| **D-2** 열린 값 기록 | — | 정본 §73: 섭동 창 1 s, 시간 블록 정의, `C_flip` 직전 창, E1 스냅샷 모집단, 반분 방법, AUROC 한 부류 뽑기 = 0.5 (각 근거) |
| **N5** E1 범위 | E §3.7 판정 1·8, §3.6 등위 회귀 | 정본 §73 한 줄(판정 1·8만, 7은 지문 결속, 2–6·§3.5 일부·§3.3 반복은 SCOPED; 등위 회귀 비교는 안 함 — §52가 등위를 직접 말하지 않아 §73의 결정으로 적음) |
| **N8** H 인자 | E §4.12·M4 §4.4 "H 1과 3 비교" | `closed --m4-h`(:283, 기본 3), `closed.m4_config(cond, H)`(:151–160, H < 1 거부), 워커 `m4=m4_config(...)`(:227), 스펙·`meta.m4_H`(:396, :424) |
| **추가** E §1.7 해시 줄 | E §1.7(:133) "판정 절 해시와 시각을 실행 기록 첫 줄에" | `eval/common.prereg_meta`(:419–433) → `run_meta`의 `prereg`(`utc` 다음, :437): written_utc·hashes(= `prereg.json`)·check(`tools/prereg_hash.py`로 재해시, "OK"/"CHANGED") |

- 문서 표시(모순 줄): `docs/superpowers/plans/2026-09-24-stage3-experiments.md:1291`(카나리 "2배") [정정 R7 8회차] 표시, 같은 계획서 `judge_e05` 초안 코드 조각(:1492)에 정정 주석 한 줄; `r5_closed_loop.md:36`(순서형 τ = 1) 표시; `r6_eval.md:13`(calib ECE) 표시. M4 설계 문서의 경계 직후 W 2·γ 1.0·g 줄은 설계(구현 서술 아님)라 표시하지 않았다(지시대로 — 정본 §73에 SCOPED로 적음).

## 2. 시험 (RED → GREEN)

새 파일 `tests/eval/test_r7c8_prereg.py`(10개)·`tests/runtime/test_m4_near.py`(3개). RED(구현 전, 12개 → 뒤에 추가한 해시 줄 시험 1개도 RED 확인): 모두 기능 없음으로 실패 — `e05.gain_holm` 없음(AttributeError), `j2_gain_holm` 없음(KeyError), ECE가 애매한 항목 포함(0.58 ≠ 0.42), `ambiguous` 키 없음, 카나리 `drift_suspect` False(2배 조건), `episode_of_key` 없음, `m4_h` 없음, `try_commit_prefix(near=)` 없음(TypeError), `near_contact` 없음, `meta.prereg` 없음(KeyError).

| 시험 | 확인 |
|---|---|
| `test_judgment2_uses_holm_over_la2_and_c2pp` | 검증자 `j2_holm.py` 반례(시드 3, 186번째 뽑기, 30편): 95% 하한 0.0099 > 0이지만 Holm 첫 단계 97.5% 하한 0.0 → 두 규칙 모두 기각 없음 → 판정 2 아님. 점추정 0.063 ≥ 0.02라 판정 3(+2%p 미만)도 아님 → `undecided`(검증자 보고서의 "a_as_stabilizer"는 판정 3 문장과 맞지 않음, §5) |
| `test_judgment2_holds_when_holm_rejects_with_a_positive_gain` | 양의 큰 이득 → `keep_a`; 음의 유의 이득은 Holm 기각이지만 판정 2 아님 |
| `test_analyze_reports_the_judgment2_holm_per_hypothesis` | `analyze` 출력 `j2_gain_holm.tests` = `judge_input.gain_holm`, 가설별 {reject, lo, hi, level} |
| `test_judged_ece_excludes_ambiguous_items_and_reports_them_apart` | 깨끗한 20개(p 0.7, 14 정답) + 애매 10개(p 0.9, 모두 오답): 판정 ECE = 깨끗한 20개의 등질량 ECE, `ambiguous` n 10·ECE 0.9, `n` 30·`n_ece` 20 |
| `test_raw_probability_rule_ece_excludes_ambiguous_items` | `fit_raw_ece` = 깨끗한 항목, `n_fit_ambiguous` 10 |
| `test_items_carry_the_snapshot_ambiguous_flag` | `items_from`이 줄의 `ambiguous`를 싣는다 |
| `test_canary_drift_is_lower_bound_above_floor_without_the_2x_condition` | 검증자 `canary_rule.py`: 바닥 0.10·불일치 0.18 → 표류 의심 True |
| `test_canary_resamples_episodes_and_holms_over_questions` | 3편 × 4스냅샷 × 5질문: 군집 3, 질문별 결과 = 독립 계산 `holm_ci`(에피소드 군집) |
| `test_run_meta_records_the_prereg_hashes_and_check` | `meta.prereg` = `prereg.json`, check OK, `model` 앞 |
| `test_closed_has_an_m4_horizon_argument_default_3` | `--m4-h` 기본 3, `m4_config("C5", 3)` = 기존 `asdict(M4Params())`(기본 출력 불변), C3 덮어쓰기 유지, H = 1 허용, H = 0 거부 |
| `test_prefix_commit_uses_tau_0_near_contact` | 검증자 `tau_near.py`(small, tiny, tiny): 먼 곳 → small 확정(그대로), near → challenger·확정 없음 → 셋째 표에서 교체 → tiny 확정 |
| `test_near_contact_is_the_canon_definition` | 4.9 cm 참, 6 cm 거짓, 그리퍼–o3 접촉 참, carry(목표 o5) 먼 곳 거짓, place의 o3–o5 접촉 참, o3–탁자 접촉 거짓 |
| `test_runtime_passes_near_to_the_ledger` | 가짜 세계 15 s: `on_vote`·`try_commit_prefix`가 near True·False 둘 다 받음 |

- 바뀐 기존 시험 1개: `tests/test_replay.py` — `judge_e05` 입력 `gain_la2_lo`·`gain_c2pp_lo` → `gain_holm`(같은 하한을 `_h()`로 감싼 모양, 기대값 그대로).
- 대조 특성(저장소 밖 스크립트, `D:\tools\scratch_qdd\r7c8fix`):
  - `char_core.py`/`char_cmp.py`(`char_cmp.txt`): 가짜 세계 폐루프 25 s × C0–C6 × 모의 지연 {0.30, 0.55} s, aad30d6 사본 대 수정본의 행동 바이트·표 결과·원장 통계·슬롯 기록 sha256. **C0·C1·C2·C4 8칸(4조건 × 지연 2) 모두 비트 동일**, C3·C5·C6은 표·원장·슬롯이 달라짐(행동 바이트는 같음), `near_contact`를 항상 거짓으로 바꾸면 **14칸 모두 aad30d6과 비트 동일** — 차이는 접촉 근처 τ에서만 온다. near 틱 비율은 성공 판에서 약 60–74 %(쥔 채 들기 = 그리퍼–o3 접촉, 놓은 뒤 o3–o5 접촉).
  - `m4_fuzz.py`(`m4_fuzz.txt`, 검증자 `m4_diff.py` 모양): 원장 400사건 × 150시드 × {consensus, newest} × feedback_b × W {1, 2} × 비가역: near 없음 → 16조합 모두 150/150 동일; near 30 % → newest 150/150 동일, consensus 101–111/150 동일(나머지는 τ 0 때문에 달라짐).
  - 검증자 스크립트 재실행: `j2_holm.py`의 두 규칙 Holm 모두 기각 없음(수정 코드 판정 `undecided`), `canary_rule.py` → True, `tau_near.py` 경로는 위 시험으로 대체.

## 3. 결과
- 로컬(Git Bash, `cd D:/qdd && python -m pytest -q -rs -p no:cacheprovider --basetemp=D:/tools/scratch_qdd/r7c8fix/pt*`, TMP = `D:\tools\scratch_qdd\r7c8fix\tmp`): 수정 전(검증자) 800 passed·11 skipped → **813 passed, 11 skipped**, F·E 0(§3 끝 최종 판). 늘어난 13개 = 새 시험 13개. 건너뜀 11은 전과 같음(torch 7, inspect_robots 2, pyarrow 1, TODO(P3) 1).
- 파드 CPU(`juhyoung-native-7a2a`, `source /data/harvest/env.sh` + `ir/env.sh`, `venv_train`, `CUDA_VISIBLE_DEVICES=""`, 코드 = 작업 트리 추적 파일 + 새 파일 tar(sha256 `acde7de9…`) + `third_party` 4개, 모두 `/data/harvest/tmp/r7c8fix`, `TMPDIR`·`PYTHONPYCACHEPREFIX`·`HARVEST_CANARY_ROOT`도 그 안): **855 passed, 3 skipped** 두 번(EXIT 0, 71 s·74 s; 04:21–04:24 UTC) = 842 + 13. 첫 시도는 `third_party` 누락으로 5개 실패(`FileNotFoundError …/third_party/humanoid_challenge_env/scripts/…`) → 넣고 다시. 경고 1(`test_stagea_loss_torch.py:42`, 전과 같음).
- 파드 정리: `/data/harvest/tmp/r7c8fix`(406 MB) 삭제(04:26 UTC). 04:18:40 UTC 뒤 `/data/harvest`에서 바뀐 것 = 공용 Isaac 하트비트 로그 `home/.nvidia-omniverse/logs/omni.processlifetime.log`(라벨러 Isaac 두 개의 heartbeat — 내 것 아님)와 `tmp` 폴더 시각뿐, `/data` 밖 새 파일 0. GPU 0–3 = 896/5/1/1 MiB(시작 904/5/1/1, GPU 쓰지 않음). 내 파드 프로세스 0. 폐루프 Isaac 판은 돌리지 않았다(τ 경로는 가짜 세계 폐루프로 확인, CAL/TEST 없음).

## 4. 사전 등록 대조표 (수정 뒤, 검증자 §5 47행 다시 채움 + 추가 행)

줄 번호 = 수정 뒤 작업 트리. 바뀌지 않은 파일은 검증자 줄 번호 그대로(확인함).

| # | 사전 등록 값·절차 (출처) | 구현 (file:line) | 판정 |
|---|---|---|---|
| 1 | 군집 부트스트랩 10,000회 (E :130, EVAL :184) | `stats.py:4`; CLI `e05.py:467`·`rd.py:155`·`calib.py:78`·`closed.py:305`; `canary.py:31` | 일치 |
| 2 | 95% 백분위 구간 (EVAL :184) | `stats.py:14-15,28,46`; seed 0 | 일치(§72) |
| 3 | 재표집 단위 = 에피소드 군집 (E :130) | e05 `(kind, seed)` `e05.py:541`; calib `calib.py:51`; rd `rd.py:130` | 일치 |
| 3b | 같은 단위 — 카나리 | `canary.py:25-28`(편), `:44` | **일치(D3 수정)** |
| 4 | 짝 비교 = 같은 시드 짝 (E :130) | `stats.py:32-47`; `closed.py:90-100` | 일치 |
| 5 | Holm — 판정 10 (E :265, :131) | `stats.py:62-81`, `e05.py:209-217` | 일치 |
| 5b | Holm — 판정 2 "LA-2 또는 C2''" (E :131, :257) | `e05.py:199-206,404-405,432`; `replay.py:29-38` | **일치(D1 수정)** |
| 6 | 폐루프 RD 재표집 = layout 짝 (EVAL :184) | `closed.py:112-133` | 일치(§72) |
| 7 | E0.5 표 = t_s − d_p95 − {0, .33, .66} (E :236) | `e05.py:43-55` | 일치 |
| 8 | 같은 시각 K = 3 (E :238) | `e05.py:453` | 일치 |
| 9 | LA-2 γ 0.67 / C2'' 반감기 0.33 / C2' λ 3·τ 5 s·T_vlm 1·5 s / C2'-S λ 1 (E :240) | `replay.py:13,21`; `e05.py:35` | 일치 |
| 10 | 판정 1–3 문턱 5%·+2%p (E :256-258) | `replay.py:36-45` | 일치(판정 2는 Holm) |
| 11 | 판정 4 ×2·AUROC 0.7·0.03 (E :259) | `replay.py:46-51` | 일치 |
| 11b | 판정 4 "섭동 직후 창" 길이 (열림) | `e05.py:159-161,466` 1 s | **정본 §73 기록** |
| 12 | 판정 5 재시험 빼기 (E :260) | `e05.py:422-424` | 일치 |
| 13 | 판정 6 < 1% (E :261) | `replay.py:52-53` | 일치 |
| 14 | 판정 7 C2' − LA-2 ≥ +2%p·하한 > 0 (E :262) | `e05.py:425-426` | 일치 |
| 15 | 판정 8 치환 − 바닥 짝 하한 > 0, 층별 (E :263) | `e05.py:396-397,429-430` | 일치 |
| 16 | 판정 9 −2pt·A3 > 바닥·A4 ≥ 5% (E :264) | `replay.py:54-63` | 일치 |
| 17 | 층 2지·Noul / 3–6 / 7–17 (E :245) | `options.py:48-51` | 일치 |
| 18 | 판정 10 시간 블록 정의·반복 수 (열림) | `e05.py:11-13,454-455` | **정본 §73 기록** |
| 19 | d_p95 = E0 값, 재실행 규칙 (E :236, :278) | `e05.py:456` 0.307 (정본 §55), meta 주의 | 일치 |
| 20 | E1 ECE = 15개 동일 질량 (E :320) | `calibration.py:71-83`, 판정 `:193-194` | 일치 |
| 21 | 판정 1 문턱들 (E :320, :339) | `calibration.py:188-205`, `calib.py:67` | 일치 |
| 22 | 판정 8 J5 (E :330, :347) | `calibration.py:199,206-210`, `calib.py:66` | 일치 |
| 23 | split conformal q̂ (E :330) | `calibration.py:59-64` | 일치 |
| 24 | 원 확률: ECE ≤ .03 ∧ T ∈ [0.8, 1.25], log p 1e-6 (E :333-335) | `calibration.py:20,86-97` | 일치(애매 항목 제외, D2) |
| 25 | 온도 대 등위 회귀 비교 (E :334) | 없음 | **정본 §73 결정(N5)** |
| 26 | `ambiguous` 본 ECE 제외 (E :359) | `calib.py:52`, `calibration.py:126-150`, `:89-90` | **일치(D2 수정)** |
| 27 | 적합/시험 에피소드 분할 (E :296 → §52) | `calib.py:28-31,123-125,146` | 일치(방법 §73) |
| 28 | E1 스냅샷 모집단 (E :296 → §52) | `calib.py:41` 연속 전부 | **정본 §73 기록** |
| 29 | T_c 0.33 / H 1·3 비교 (E :487, M4 :272-273) | `m4.py:43-44`; `closed.py:151-160,283` `--m4-h` | **일치(N8 수정)** |
| 30 | γ 0.67, n_LA 2 (E :487, M4 :275-276) | `m4.py:46-47,221-224` | 일치 |
| 30b | 경계 직후 γ 1.0·W 2 (M4 :150,:214,:221,:281,:291) | 없음 | **SCOPED(정본 §73, D5)**, `m4.py:24-29` |
| 31 | W 1, W 정의·W = 0·W < 0 (§72) | `m4.py:45,61-63,182-191` | 일치 |
| 32 | 비가역 W+1 (M4 :291, :306) | `m4.py:179,187` | 일치 |
| 33 | τ 1(접촉 근처 0) (E :487, M4 :277) | `m4.py:48,142-151,208-224`; `core.py:42-54,282,435,441,503` | **일치(D4 수정)** |
| 34 | STALE 1.5 s, d̂ p95·50회, N_max (E :487, :220, M4 :258,:263) | `m4.py:49,53,118-129` | 일치 |
| 35 | FLIP_TH·θ 게이트 끔 (정본 §6, M4 :282,:287) | `m4.py:50`, J5만 `core.py:323-` | 일치 |
| 36 | 조기 호출: (b) ≠ OK / 큐 임계 g / 장면 변화 (M4 :259-261, :289) | (b)만 `m4.py:266-285`, `core.py:320,374,501` | **SCOPED(정본 §73, D5)** |
| 37 | (b) conformal α 0.01·창 w 5 (E :487, M4 :285-286) | 정본 §61·§64 측정원으로 대체 | 정본 기록 |
| 38 | 시드 구간 (E :115-120, 정본 §66) | `eval/splits.py:13-15`, `datagen/gen.py:34-35` | 일치(TEST2는 N4) |
| 39 | 성공 1 s·60 s·낙하 즉시 실패 (E :107) | `config.py:12`, `closed.py:285`, `aiworker.py:14-15` | 일치 |
| 40 | P1 2 cm·near 5 cm, P2 0.5 s, h_lift 3 cm, tilt 30° (E :420-421, 정본 §7) | `perturb.py:26-28`, `config.py:8-11` | 일치 |
| 41 | POOL 120 × 10, 경계 30% (E :121) | `sim/snapshot.py:31`, `pool.md:17,25` | 일치(가중치 N10) |
| 42 | 라벨 규칙 (prereg_labeler :11-13) | `sim/labeler.py:95-96,131-142` | 일치 |
| 43 | D-short·D-time (prereg_labeler :7-9) | `labeler.py:25,100-111,114-128` | 일치(N9) |
| 44 | 카나리 표류 = 하한 > 0 (Holm) (정본 :264, E :139) | `canary.py:31-54` | **일치(D3 수정)** |
| 45 | EVAL H1/H2 ΔRD (EVAL :186-190) | 없음(기준선 S1) | SCOPED S1 |
| 46 | 주 RD = Score 기반 (EVAL :182) | `closed.py:130` 성공률 기반 | N7(1차판 [가정]) |
| 47 | M4b 자기 사전 등록 2,000회 (`e_m4b_meas.md:94`) | `m4b/*` | 일치(§72 예외) |
| **48** | 판정 절 해시·시각을 실행 기록 첫 줄에 (E §1.7 :133) | 전: 없음 → `common.py:419-437` `meta.prereg` | **추가 수정(일치)** |
| **49** | `C_flip` (i) "직전 창(예: 직전 1초)" (E :242, M4 §3 #7) | `e05.py:74-77` 직전 스텝 3표; 런타임 `m4.py:198-206` 4표 대 4표 | **정본 §73 기록**(열린 값) |
| **50** | 미확정 실행 스텝의 (b) 문턱 한 단계 엄격 (M4 §4.2 :225) | 없음(`core._boundary` 고정 문턱) | **SCOPED(정본 §73)**, `m4.py:29` |
| **51** | 카나리 "모델 식별 필드가 바뀌어도 같은 처리" (E :139, 정본 :264) | 보정 파일 지문 결속(`calibration.Calibration.load`), 카나리 기준일 지문별(`eval/canary.py`) | 정본 §73 해석(재보정 전 게이트 재사용 불가) |
| **52** | 조기 호출은 주기 슬롯 하나를 당겨 씀 (M4 :262) | `core.py:411-416` | 일치 |
| **53** | E0.5 요청 분당 400 이하 [가정] (E §2A.8) | 없음 — 로컬 vLLM(API 한도 없음) | NOTE(해당 없음, API 모델을 쓸 때 넣을 것) |
| **54** | `ambiguous` 정의 = 히스테리시스 띠 술어 (E §1.5 :121) | `sim/snapshot.py:89-100`, 풀 `ambiguous` | 일치; §3.10의 "방향 경계" 애매함은 표시 없음 → 정본 §73 기록 |

- 대조 방법: 검증자 47행의 출처 줄을 다시 읽고 수정 뒤 코드 줄을 `D:\tools\scratch_qdd\r7c8fix\lines.py`로 찾아 맞췄다. 추가 행은 E-first §1.5–§1.8·§2A.3–§2A.8·§3.3–§3.10·§4.12, M4 §4.2–§4.4, EVAL §4.2, `prereg_labeler.md`를 줄마다 훑어 "코드가 쓰는 값·절차인데 표에 없는 것"을 찾은 결과다. EVAL §4.2(:180-190)의 나머지(과제 층화·과제 군집 CI·H1–H3 판정)는 RoboDojo 2차판·기준선 몫이라 S1과 같은 SCOPED.
- 문서 grep(모순 서술): `2배를 넘|2 ?× ?floor|2×바닥|no Holm|gain_la2_lo|τ = 1 칸|ambiguous|H = 3 고정` — 계획서 두 곳·`r5_closed_loop.md:36`·`r6_eval.md:13`·`eval/canary.py` 머리 설명을 고쳤거나 표시했다(§1). 나머지 히트는 당시 기록(검증 보고서, `r7c7_fixes.md`) 또는 이번 수정과 맞는 서술.

## 5. 판단이 갈릴 수 있는 곳
1. **D4 적용 범위**: 지시는 "C0–C4·C6 비트 동일"이었다. τ는 원장의 (a) 합의 규칙의 일부이고 C3(= C5의 (a)만)·C6(= C5에서 겹침만 끔)은 정의상 C5와 같은 합의 규칙을 쓴다(M4 §5 :337·:345; (a)/(b) 분해 그림 C3 − C2가 (a) 몫이 되려면 같은 τ여야 함). 그래서 **C0·C1·C2·C4(newest, 합의 없음)는 비트 동일, C3·C5·C6은 접촉 근처만 달라짐**으로 구현했고 near를 끄면 셋 다 비트 동일임을 보였다. C3·C6을 옛 τ로 두려면 조건별 예외가 필요하다(원하면 `conditions.py`에 `near_tau0` 덮어쓰기 한 줄).
2. **near의 범위가 넓다**: 정본 §7 정의대로 "접촉 술어 참"을 넣으니 쥔 채 드는 동안(그리퍼–o3 접촉)과 놓은 뒤(o3–o5 접촉)가 모두 near다 — 가짜 세계 성공 판에서 틱의 약 60–74 %. 사전 등록 M4 §4.6 "정밀 접촉 구간 τ=0"을 더 좁게(예: descend·close·place_descend·open 단계만, `snapshot.NEAR_CONTACT_PHASES`) 읽을 수도 있다. 지금은 정본 §7 문장을 따랐다.
3. **D1 반례의 판정**: 검증자는 반례가 "사전 등록대로면 a_as_stabilizer"라고 적었지만 판정 3은 "정답률 이득 < +2%p"(점추정)라 점추정 0.063에는 해당하지 않는다 → 수정 코드는 `undecided`(판정 1–3 밖, 기존 처리). 판정 3을 "유의한 이득 없음"으로 읽으려면 사전 등록 해석을 정본에 따로 정해야 한다.
4. **카나리 바닥의 불확실성**: 사전 등록은 바닥 추정법을 정하지 않았다. 바닥을 상수로 두었다(§73). 바닥도 같은 편 뽑기로 다시 계산하면 하한이 낮아진다(더 보수적).
5. **N5 등위 회귀**: §52 본문은 등위 회귀를 언급하지 않는다 — "§52가 덮는다"는 읽기가 아니라 §73에서 새로 정한 결정으로 적었다.
6. **추가 행 48(해시 줄)**: 사전 등록 문장에 [제안] 표시가 있으나 `prereg.json`이 이미 만들어져 채택된 것으로 보고 구현했다. "첫 줄"은 JSON 출력의 `meta` 머리(`utc` 다음)로 읽었다.

## 6. 변경 파일 검사
- 탭·폼피드·NUL: 바뀐 파일·새 파일 모두 0(`draft-log.md`의 탭 1개는 전부터 있던 것, 이번 추가 줄에는 없음). 줄 끝: `m4.py`·계획서 CRLF 유지, 나머지 LF 유지, `draft-log.md`(섞임: 1–284줄 CRLF = 24a1982 때 체크아웃 뒤 내용 무변경, 그 뒤 덧붙인 줄 LF)는 편집 도구가 파일 전체를 CRLF로 바꿨던 것을 되돌렸다(`fix_draftlog_eol.py`: 1–284줄 CRLF, 285줄부터 LF) — 편집 전 CRLF 284/LF 161, 뒤 284/162(이번 줄 LF). 검사 `D:\tools\scratch_qdd\r7c8fix\eol.py`.

## 7. 사고(내 실수) 1건
- 지시(`python -` 표준 입력 금지)를 어기고 `python -`(본문 없음)를 한 번 실행했다 — 파이썬이 표준 입력을 기다려 하네스가 배경 작업으로 옮겼고, 즉시 멈췄다(TaskStop). 만든 파일 없음, 떠 있는 python 프로세스 없음(PowerShell `Get-Process python` 빈 결과). 배경 작업 출력 파일은 하네스가 C:의 자기 작업 폴더(`AppData\Local\Temp\claude\…\tasks`)에 만든 것이다. 이후 모든 스크립트는 Write 도구로 D:에 쓰고 경로로 실행했다.
