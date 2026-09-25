# R7 7회차 지적 수정 (E1 결함 + 사전 등록 대조 N1–N5·N7)

- 작성 2026-09-25 03:11 UTC(`date -u`). 대상 `D:\qdd` `dev` HEAD `3ed2e49` + 작업 트리(커밋·푸시 안 함 — 메인 세션). 입력 보고서 `docs/stage3/results/r7_cycle7.md`(판정 FAIL, DEFECT 1).
- 원칙: 사전 등록은 구속한다 — 코드는 사전 등록의 값·방식을 그대로 구현하고, 사전 등록이 정하지 않은 값은 정본 §72에 적었다. 결정마다 따르는 사전 등록 줄은 §72에 있다.
- 건드리지 않은 파일: `stagea_train.PROMPT_FILES` 9개, `train/stageb_data.py`·`stageb_model.py`(체크포인트 `files_sha` 대조, §71) — `git diff --name-only`로 확인. `[사용자]` 줄·사용자 인용 줄은 지우거나 바꾸지 않았다(수정 전 줄 중 '사용자' 포함 0).
- 로컬 임시 = `D:\tools\scratch_qdd\r7c7fix`, pytest basetemp = `pytest.ini`의 D:. C: 쓰기 없음(아래 §6 사고 2건 포함 확인).

## 1. 무엇을 바꿨나

| 항목 | 결정 | 코드 |
|---|---|---|
| **E1** 부트스트랩 횟수 | 사전 등록 E §1.7(:130)·EVAL §4.2(:184) = 10,000 → 모든 기본값 10,000, 출력에 기록 | `analysis/stats.py` `N_BOOT = 10000`; `e05`·`rd`·`calib`·`closed` `--n-boot` 기본값과 `e05.mean_ci`·`diff_ci`·`block_diff_lo`·`analyze`, `rd.majority`·`offline_rd`·`drd`, `runtime/calibration.evaluate`, `eval/closed.aggregate`, `harvest/canary.canary_compare` 기본값 = `N_BOOT`. `eval/common.bootstrap_meta` → `meta.bootstrap` {n_boot, seed 0, level 0.95, percentile, unit, prereg}(`e05.json`·`rd.json`·`calib.json`·`closed.json`; `closed.json`은 `result.bootstrap`에도). 카나리 비교 결과에 `n_boot`·`boot_seed`·`boot_unit`. `m4b/*`(D28 자기 사전 등록 2,000)·`tools/*`(지난 결과 재현)는 그대로 |
| **N3** 판정 10 Holm | 사전 등록 §2A.6-10(:265) "블록 여러 개면 Holm" → Holm 단계 하강 구현 | `stats.holm_ci`(구간 역산 Holm), `e05.block_diff_holm` → `floor.block_pairs_holm`·`judgments.j10_block_pairs_holm`(쌍별 기각). 판정 10의 참·거짓은 `block_diff_lo > 0` 그대로 — Holm 첫 단계 = 수준 1 − α/m이므로 "한 쌍이라도 유의"는 Holm·Bonferroni가 정확히 같다(docstring 정정) |
| **N4** E1 ECE | 사전 등록 §3.4(:320) "15개 동일 질량 구간" → 판정 1(§3.7 :339)·원 확률 규칙(§3.6 :335) 모두 등질량 | `calibration.judge_question`은 `ece_cal_mass` + 새 `ece_cal_mass_ci`로 판정, `fit_question.fit_raw_ece` = `ece_mass`, 등폭 `ece_raw`·`ece_cal`은 보고만(`ece_cal_ci`(등폭) 삭제), `calib.md` 열 이름에 (width)/(mass, judged), `meta.ece` 설명 |
| **N5** 폐루프 RD 단위 | EVAL §4.2(:184 layout 짝 재표집, :179 1차판도 같은 규칙) → 레이아웃 시드 군집, epoch는 시드 안(사전 등록이 epoch를 정하지 않음 → §72에 기록) | `closed.aggregate` `rd_ci`: 시드별 (표준 성공 합, 변형 성공 합)을 뽑아 RD* = 1 − Σ변형/Σ표준, `n_seeds` 출력 |
| **N2** M4 W | 정의(M4 §3 #3 :148, §4.2 :212–214) = 첫 도전 표 뒤에 더 필요한 같은 도전 표 수. 정본 §5·M4 §4.4·M5 L1·SUMMARY의 "연속 2표 = W=2"는 이 정의와 어긋난 옮김 → **W=1**로 정정(§72). 기본 W = 1(E-first §4.12 :487 C5 설정, M4 §4.4)이고 `conditions.py`가 W를 덮어쓰지 않으므로 **C0–C6 기본 동작은 그대로**. W = 0은 의사코드대로면 W = 1과 같았음 → 첫 도전 표에서 즉시 교체(절제 {0,1,2}가 세 수준), W < 0 거부 | `runtime/m4.py` `on_vote`(W+비가역 = 0이면 즉시 `_replace`), `M4Params.__post_init__`, 머리 설명 |
| **N7** 융합 판 prompt_config | 단계 B 체크포인트 판은 체크포인트의 학습 prompt_config를 기록(서버 `check_prompt`가 런타임과 같음을 강제) | `closed.run_prompt_config(selector, pc, layout)`, `run()` meta |
| **N1** handoff 머리 시각 | 지금 시각으로, 구조 유지(횟수 없음) + §2.8 7회차 줄 | `docs/handoff.md:3`, §2.8 |

- 문서 표시(과제 9): `M4-overlap-commit.md` §4.4 W 행, `M5-smoothing.md` L1, `SUMMARY.md` 2곳에 "[정정 R7 7회차, 정본 §72: … W=1]"; `r6_eval.md` 명령 표 E1 줄(판정은 등질량)과 meta 설명(`meta.bootstrap`, 기본 10,000)에 표시; `eval/calib.py` 머리 설명. 정본 §5(:35) 원문은 규칙대로 두고 §72가 뒤 절로 우선. `D1-verification.md:77`(당시 검증 기록 표)은 그대로. 저장소에 `n_boot 2000`·`Bonferroni`·"stand-in for Holm"을 현재 규칙으로 적은 곳은 이제 없다(`e_m4b_meas.md`의 2,000회는 D28 자기 사전 등록).
- 파드 정리(과제 8, 1회차 검증자 잔여, 목록 확인 뒤 이 이름만): `/data/harvest/code_r7c1`(2.1 MB)·`code_r7c1b`(18 MB)·`cache/pyc_r7c1`(326 MB)·`cache/pyc_r7c1b`(341 MB)·`ir/kitcache/cyclo-r7c1{bf,bm,c,f,m}_standard`(각 208 MB) 삭제(03:02:58 UTC, 사용 중 프로세스 없음 확인). 약 1.7 GB.

## 2. 시험 (RED → GREEN)

새 파일 `tests/eval/test_r7c7_prereg.py`(11개)·`tests/runtime/test_m4_window.py`(5개). RED(구현 전, `D:\tools\scratch_qdd\r7c7fix\red.txt`): 12개 실패, 이유는 모두 기능 없음 — 기본값 2000(`AssertionError: mean_ci`), `meta.bootstrap` 없음(`KeyError`), `holm_ci`·`block_diff_holm`·`run_prompt_config` 없음, `ece_cal_mass_ci` 없음·판정이 `ece_cal_ci`를 읽음, `fit_raw_ece` ≠ 등질량, `rd_ci` = [0.1667, 1.0](짝 재표집) ≠ [0, 1], W = 0이 `challenger`, W = −1 허용. RED에서 통과한 4개: `test_ece_mass_hand_example`(등질량 함수 `ece_mass`는 이미 있었음 — 손 계산 값 고정용)와 기본 동작 고정용 특성 시험 3개(W = 1 → 도전 표 2개, W = 2 → 3개, W = 0 비가역 → W+1 = 2개). 특성 시험은 수정 전후 모두 통과해 기본 동작이 그대로임을 보인다.

| 시험 | 확인 내용 |
|---|---|
| `test_bootstrap_defaults_are_the_preregistered_10000` | 라이브러리 10개 기본값·CLI 4개 기본값 = 10000 |
| `test_outputs_record_bootstrap_meta` | e05·calib·rd 모의 한 명령 → `meta.bootstrap.n_boot` = 준 값, seed 0, 0.95, 단위 |
| `test_closed_aggregate_and_canary_record_n_boot` | `closed.aggregate()["bootstrap"]`(단위 layout seed), 카나리 `n_boot` |
| `test_holm_on_intervals_differs_from_bonferroni` | p = {0.001, 0.02, 0.5}: Holm 기각 {a, b}, Bonferroni(0.05/3)는 b를 못 기각; `stats.holm`과 일치; 첫 단계 실패면 멈춤 |
| `test_e05_judgment10_reports_holm_per_block_pair` | 블록 3개(0,0,1): 0-2·1-2 기각, 0-1 유지, any = `block_diff_lo > 0` |
| `test_ece_mass_hand_example` | 손 계산 ECE 등질량 0.225 ≠ 등폭 0.125, 기본 구간 15 |
| `test_e1_judgment1_uses_equal_mass_ece` | 등폭 0.02·등질량 0.07 → 불합격, 등폭 0.07·등질량 0.03(상한 0.06) → 합격 |
| `test_evaluate_bootstraps_the_equal_mass_ece` | `ece_cal_mass_ci`가 점추정을 감쌈 |
| `test_fit_question_raw_ece_is_equal_mass` | §3.6 원 확률 ECE = 등질량 |
| `test_closed_rd_ci_resamples_layout_seeds_not_seed_epoch_pairs` | 시드 2 × epoch 3: 구간 [0, 1](시드 군집), `n_seeds` 2·`n_pairs` 6 |
| `test_fused_run_records_the_checkpoint_prompt_config` | 단계 B → 체크포인트 구성(sha·IMG·source), 모듈형 → S1·배치 |
| `test_m4_window.py` 5개 | W = 0 즉시 교체(RED→GREEN), W = 1 도전 표 2개·기본 W = 1, W = 2 3개, W = 0 비가역 2개, W < 0 거부(RED→GREEN) |

- 바뀐 기존 시험 1개: `tests/eval/test_calib_pure.py::test_judge_question_follows_e1_rules`의 입력 키를 `ece_cal`/`ece_cal_ci` → `ece_cal_mass`/`ece_cal_mass_ci`(판정 입력이 바뀐 것에 맞춤, 기대값 그대로). 이 시험은 구현 뒤 전체 실행에서 `KeyError: 'ece_cal_mass'`로 한 번 실패했고 키를 고친 뒤 통과.

## 3. 결과
- 로컬(Git Bash, `cd D:/qdd && python -m pytest -p no:cacheprovider`, TMP = `D:\tools\scratch_qdd\r7c7fix\tmp`): 수정 전 **784 passed, 11 skipped**(80.7 s) → 수정 뒤 **800 passed, 11 skipped**(85.9 s). 늘어난 16개 = `test_r7c7_prereg.py` 11개 + `test_m4_window.py` 5개. 건너뜀 11은 전과 같음(torch 7, inspect_robots 2, pyarrow 1, TODO(P3) 1).
- 파드 CPU(`juhyoung-native-7a2a`, `source /data/harvest/env.sh` + `ir/env.sh` 4경로, `venv_train`, `CUDA_VISIBLE_DEVICES=""`, 코드 = `git stash create` 커밋의 `core.autocrlf=false` archive + 새 시험 2개, `/data/harvest/tmp/r7c7fix` 아래): **842 passed, 3 skipped**(이전 판 826/3 + 16), EXIT 0 두 번(03:03:53–03:05:15 UTC 판, 66 s 판). 경고 1개는 `tests/eval`·`tests/runtime`·`tests/test_stats.py`만 돌린 판에는 없음(바뀐 코드 밖). 건너뜀 = pyarrow 1·CUDA 없음 1·TODO(P3) 1.
- 파드 정리: `/data/harvest/tmp/r7c7fix`(566 MB) 삭제. `/data` 밖 새 파일 0(`find / -xdev -newermt "2026-09-25 03:03:00 UTC"`, /proc·/sys·/data 제외). `/data/harvest`에서 그 뒤 바뀐 것은 라벨러(GPU 0)의 `out/t13/label4_*.log`·`data/pool/labels`뿐(내 것 아님). GPU 0–3 = 896/5/1/1 MiB(시작과 같음, GPU 쓰지 않음). 내가 띄운 파드 프로세스 0.
- 변경 파일 탭·폼피드 검사: §5.

## 4. 판단이 갈릴 수 있는 곳
1. **W의 정의**: 과제 지시는 "정본이 W=2 = 연속 2표로 분명하면 코드를 맞추라, 단 기본 조건 동작이 같은지 확인"이었다. 정본 §5는 W를 정의하지 않고 "M5 '연속 2표' = W=2"라는 옮김만 적었고, W를 정의하는 M4 §3 #3·§4.2와 사전 등록 C5 설정(W=1, E-first §4.12)은 "W=1 = 도전 표 2개"다. 정본 문장대로 코드를 바꾸면(W = 필요한 도전 표 수) 기본 W = 1이 "첫 도전 표에서 즉시 교체"가 되어 **C0–C6 기본 동작이 바뀐다**. 그래서 정의 쪽(M4 §4.2)을 따르고 정본 §5 문장을 §72에서 W=1로 정정했다. 반대로 가려면(정본 문장 우선) 기본값을 W = 2로 올려야 기본 동작이 유지된다 — 메인 세션이 다르게 보면 되돌리기 쉽다(코드 변경은 W = 0 경로와 음수 거부뿐).
2. **Holm의 판정 영향**: 판정 10의 참·거짓은 수학적으로 전과 같다(Holm의 "하나라도 기각" = Bonferroni 첫 단계). 바뀐 것은 쌍별 결과를 새로 내는 것. 7회차 N3의 "더 보수적"은 쌍별 결과에만 맞는 말이었다.
3. **ECE 판정 입력 키 변경**: `ece_cal_ci`(등폭)를 없애고 `ece_cal_mass_ci`로 바꿨다. 옛 `calib.json`을 읽는 도구는 없다(`grep`). 런타임 `calibration.json`(모델 지문 × question_id) 형식 `r6-calib-v1`은 그대로 — 다만 이미 만들어진 보정 파일의 `theta_gate`(ECE 조건)·`use_raw`(§3.6)는 옛 규칙(등폭)으로 정해졌으므로(`j5_ok`는 ECE와 무관), E1 판정에 쓸 보정 파일은 이 코드로 다시 만들어야 한다(지금까지의 보정 파일은 모두 DEV/POOL 스모크).
4. **부트스트랩 seed**: EVAL :317(RoboDojo 공개 자료 재계산)은 seed 0·1을 쓰지만 우리 평가 규칙의 seed는 사전 등록에 없다 → seed 0 고정으로 §72에 기록.
5. **폐루프 과제 층화**: EVAL §4.2의 "과제 고정" 층화는 폐루프 과제가 하나라 적용할 것이 없다. 과제가 늘면 과제 안 재표집을 넣어야 한다(§72에 적음).

## 5. 변경 파일 검사
- 탭·폼피드: 변경·새 파일 모두 `\t`·`\f` 0개(아래 명령). 줄 끝: 편집 도구(`sub.py`·`append.py`, 파일의 기존 줄 끝을 따라 변환)로 보존 — `m4.py`·`SUMMARY.md` CRLF 유지, 나머지 LF 유지. `draft-log.md`(CRLF·LF 섞임)는 마지막 줄과 같은 LF로 덧붙임.
- 확인 명령: `git diff --name-only` + 새 파일 → 바이트 검사 스크립트(`D:\tools\scratch_qdd\r7c7fix\check_ws.py`).

## 6. 사고(내 실수) 2건
- 지시(heredoc 금지)를 어기고 Git Bash heredoc을 두 번 썼다: (1) `cat > D:/tools/scratch_qdd/r7c7fix/edit_stats.py <<'X'` — 빈 파일이 D:에 생겼고 바로 지웠다. (2) `python - <<'EOF'`(빈 본문) — 파이썬이 끝나지 않아 하네스가 배경 작업으로 옮겼고, 그 작업을 멈췄다(TaskStop). 두 경우 모두 `%TEMP%\sh-thd*` 잔여 없음, 떠 있는 python 프로세스 없음(PowerShell `Get-Process python` 빈 결과) 확인. 배경 작업 출력 파일은 하네스가 C:의 자기 작업 폴더(`AppData\Local\Temp\claude\…\tasks`)에 만든 것이다. 이후 모든 파일은 Write 도구·`.py` 스크립트로만 만들었다.
