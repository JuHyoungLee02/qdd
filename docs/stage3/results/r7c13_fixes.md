# R7 13회차 수정 (D1–D3, N1, N5, DOC D-1·D-2, Isaac 워커 환경)

- 작성 2026-09-25 11:55 UTC, 수정 에이전트. 대상 `r7_cycle13.md`(검토 대상 `e6ab856`); 작업 시작 HEAD `93c68d7`, 도중 메인이 `e8e1864`(PhysX 하드 리셋, 정본 §78)를 커밋 — 이 수정은 그 위의 커밋 안 된 작업 트리. 정본 **§79**. **커밋 안 함**.
- 원칙: 사전 등록(`E-first-experiments.md`·`EVAL-evaluation-design.md`·`M4-overlap-commit.md`·`prereg.json`)과 정본은 구속한다. 사전 등록 문서 무변경(`tools/prereg_hash.py --check` OK). 시험 먼저(TDD: 새 시험이 실패하는 것을 본 뒤 코드). `harvest/sim/*`·`tests/sim/*`(하드 리셋 에이전트), `stagea_train.PROMPT_FILES`·`stageb_data.py`·`stageb_model.py`는 건드리지 않았다(작업 중 다른 세션이 `harvest/train/stageb_train.py`·`tests/train/test_stageb_torch.py`를 수정 중 — 내 것 아님, 손대지 않음).
- 로컬 임시 `D:\tools\scratch_qdd\r7c13fix`(93c68d7 사본 `base/`, 대조 `char_run.py`·`char_cmp.py`·`char_*.json`·`char_cmp.txt`, 분해용 변형 `variantB/`·`mk_variant.py`, 파드 사본 `podcode.tar`·`mk_podcode.py`·`pod_cpu.sh`·`pod_cpu.log`). 파드 `juhyoung-native-7a2a:/data/harvest/tmp/r7c13fix`(194 MB)는 끝에 지웠다(11:51 UTC). GPU·Isaac 안 씀.
- 절차 사고 1건: 첫 e05 시험 판이 `question_id` 등록부 기본 경로(작업 폴더 기준 `docs/stage3/qid_registry.json`)에 새 파일을 만들었다(추적 안 되는 새 파일, 내 판이 만든 것) — scratch(`stray_qid_registry.json`)로 옮기고, `e05`가 등록부를 실행 폴더에 두게 고쳐 시험으로 막았다(아래 N5 곁).

## 1. 결정과 사전 등록 근거

| 항목 | 사전 등록·정본 문장 | 구현 |
|---|---|---|
| **D1** FLIP_TH 초기값 | M4 §4.4 :287 "성공 실행 flip_score의 1−α 분위(split conformal) … E0.5 재생 자료로 먼저 잡는다 … `question_id@vN`별로 잡는다(J4)"; M4 :44 "임계는 성공 실행으로 conformal 보정"; q̂ 행 :283·E §3.5 :330 "⌈(n+1)(1−α)⌉"; 정본 §28 J4 :260 "감시는 `question_id@vN`별로만", §12 :111 | `e05.flip_th_conformal`(:271): ⌈(n+1)(1−α)⌉번째 작은 값(α 소수 그대로 유리수 계산), 순위 > n이면 값 `None`·`finite` false·`n_needed` = ⌈1/α − 1⌉. 점수는 질문마다(`succ_q`, :327) — 5질문 평균·`np.quantile` 보간 삭제. 출력 `c_flip.flip_th_candidates[q0.99/q0.999/q0.95][질문]`, `flip_th_initial.per_question`, `c_flip.question_ids`(:695). [Claude 결정] 판정 4 AUROC는 질문 평균 그대로(사전 등록이 질문별을 적지 않음); 창 차이(재생 직전 스텝 3표 대 런타임 4 대 4)는 §73 그대로; 런타임 `flip_th`는 한 값·지금 꺼짐 — 켤 때 질문별로(정본 §79) |
| **D2** 카나리 기준일 | E §1.8 :137 "고정 스냅샷 × 고정 `question_id@vN`", :140 "기준일 = 카나리 세트를 처음 돌린 날", §3.7-7 :345–346, 정본 §77 "새 기준일" | `canary.select_baseline`(:168): 세트 해시와 `question_ids`가 모두 같은 첫 카나리; 없으면 이 판이 새 판본의 기준일; `question_ids` 없는 옛 카나리는 기준 아님 |
| **D3** 표류 뒤 J5 | E §1.8 :139 "E1 보정 부분을 다시 돌린 뒤에 게이트를 재사용", §3.7-8 :347 "끄고 재보정" | `latest_canary`가 `last_drift`(가장 최근 표류 의심 카나리)를 싣고(:158), `closed.j5_after_canary`(:169)가 그것과 보정 `utc` 날짜를 비교 — 표류 다음 날 깨끗한 카나리만으로는 켜지지 않음; 같은 날 경계·전체 질문 끔은 §77 N6 그대로 |
| **N1** 경계 틱 호출 | M4 §4.2 :232 `on_step_executed` → `next_jev_input.add_line(f"last_step: {s.outcome}")`; 학습 자료 = 스냅샷 k에 k에서 끝난 스텝(§77 (iv)) | `core.act`: 결정 호출을 경계 판정 뒤에 만든다(:495). in-flight·N_max·d̂·대상 슬롯·조기 호출 깃발은 틱 시작 값(:459–460) → 조기 호출은 전처럼 다음 틱. 학습 자료 유도(`deccall_snap`)는 **바꾸지 않음**(런타임을 학습에 맞춤). §77 (ii) 문장 정정은 정본 §79 |
| **N5** 빈 입력 | (검토 권고) | `common.load_episodes`(:346–352): 폴더 목록 비음·폴더 없음·`ep*.jsonl` 없음 → SystemExit; `rd.expand_dirs`는 못 찾으면 폴더 이름 그대로 넘김 |
| 워커 환경(메인 요청) | — | `closed.worker_cmd` 워커 환경에 `OMP_WAIT_POLICY=PASSIVE`(:195) |
| 곁 | — | `e05`가 qid 등록부 기본값을 `<out>/qid_registry.json`로(:680, `calib`·카나리와 같음) |

## 2. 시험 (RED → GREEN)
- `tests/eval/test_r7c13_flip_th.py` 10개: n 47·α 0.01 → 순위 48 > 47, 문턱 없음, `n_needed` 99; n 99 → 최댓값; n 200·α 0.05 → 순위 191 = 190(`np.quantile` 189.05와 다름); α별 `n_needed` 경계(999·99·19); 빈 입력; `analyze` 질문별(dir_z TV 1/3·one 1.0 — 평균이면 1/6·0.5, n 102·순위 102), 성공 스텝 48이면 문턱 없음, 섭동 편 점수 제외. RED: `AttributeError`(함수 없음)·`KeyError 'dir_z'`(질문별 키 없음).
- `tests/eval/test_r7c13_canary.py` 15개: 새 판본 → `baseline` None·비교 없음; `question_ids` 없는 옛 판 기준 아님; 같은 판본의 첫날(09-02, 09-01 옛 판본 건너뜀) 기준; `select_baseline` 순수 4경우; 09-20 기준·09-21 표류·09-22 깨끗 + 보정 09-20 → 끔, 보정 09-21T13·09-22 → 켬; 표류 없음 → 켬; 다른 지문 표류 무시; 같은 날 경계 4건(09-24T23:59:59 끔·09-25T00:00 켬·11:00 켬·`utc` 없음 끔) 불변; `closed.run` 스펙 `j5_alpha` None; 워커 명령에 `OMP_WAIT_POLICY=PASSIVE`. RED 8개(나머지 7개 — 재보정 뒤 켬 2·다른 지문·같은 날 경계 4 — 는 기존 동작이 바뀌지 않았음을 보는 시험이라 처음부터 통과).
- `tests/eval/test_r7c13_data_paths.py` 7개: `load_episodes` 없는 폴더·빈 폴더·빈 목록, `e05`·`rd`·`calib` 없는 `--data` → SystemExit; `e05` 출력 `c_flip.question_ids`와 등록부 위치. RED 7개.
- `tests/runtime/test_r7c13_boundary_line.py` 13개: C4·C5·C6 × {LAG, DEVIATE} × {모듈형, 융합} — 경계 틱에 보낸 모든 호출의 줄 = 그 틱에서 확인한 스텝 범주, 모든 호출의 줄 = 그때까지 마지막으로 끝난 스텝 범주; 검토자 사례(LAG 4.29 s 경계 → 4.29 s 호출 LAG). RED 13개(예: 0.33 s 호출 'none' ≠ 'OK').
- 기존 시험 수정 2개(새 동작에 맞춤): `test_r7c12_e05.py`(후보 구조가 질문별), `test_r7c12_b_feedback.py`(창에 경계 틱 포함, 주석 순서).

## 3. N1 무작위 대조 (가짜 세계, 93c68d7 대비)
`char_run.py`(12회차 도구 + 경계 틱 호출 기록): 160판 = 8조건(C0–C6, C5') × 20, H ∈ {1, 3}, W 0–2, 잡음 0/15/30 %, 지연 0.2–1.6 s 고정 또는 흔들림, 시작 오프셋, 무작위 틱 강제 DEVIATE.

| 조건 | 비트 동일(행동·원장·epoch·호출 수·호출 시각·요청 상태) | 경계 틱 호출 줄 = 방금 끝난 스텝 (93c68d7 → 수정) |
|---|---|---|
| C0 / C1 / C2 / C3 | 20 / 20 / 20 / 20 | none 17/17 · 11/11 · 109/109 · 109/109 (그대로) |
| C4 | 18/20 (c3_C4 원장·행동, c11_C4 줄만) | 2/4 → 4/4 |
| C5 | 19/20 (c15_C5 줄만) | 0/1 → 1/1 |
| C5' | 20/20 | none 4/4 (그대로) |
| C6 | 19/20 (c10_C6 원장·행동) | 37/38 → 38/38 |

- 달라진 4판은 모두 주기 호출이 앞 스텝과 범주가 다른 스텝의 경계 틱에 걸린 판. c3_C4·c10_C6은 DEVIATE 경계 틱 호출이 이제 확인 뒤 epoch를 달아 표가 버려지지 않음(`dropped_epoch` 45 → 30, 15 → 0; c10_C6 확정 140 → 142). 성공 여부 160판 모두 같음.
- 분해: 처음 판(호출 블록 전체를 경계 뒤로 — d̂·N_max를 배달 뒤 값으로, 조기 호출을 같은 틱으로)은 C3 7판·C4 20·C5 20·C5' 19판이 달라졌다(원인: 배달로 갱신된 d̂, 조기 호출 한 틱 당김 → 주기 격자 이동). 사전 등록이 요구하지 않는 변화라 게이트·슬롯·조기 깃발을 틱 시작 값으로 되돌렸다(`variantB`로 먼저 확인 → 최종 코드와 160판 동일).

## 4. 시험 묶음
- 로컬(Git Bash, `cd D:/qdd && python -m pytest`, basetemp = scratch): **953 passed, 13 skipped**, rc 0(건너뜀: torch 없음 8, inspect_robots 2, pyarrow 1, isaaclab 1(하드 리셋 에이전트 시험), TODO(P3) 1). 실패 없음.
- 파드 CPU(`juhyoung-native-7a2a`, `venv_train`, `CUDA_VISIBLE_DEVICES=""`, `OMP_WAIT_POLICY=PASSIVE`, 코드 = `git -c core.autocrlf=false archive e8e1864` + 이 수정 파일 13개, third_party 포함, `CODE_VERSION` JSON {commit e8e1864…, dirty true}, tar sha256 `42e3f1372abb0820…`, 11:48–11:50 UTC): **1001 passed, 4 skipped**, rc 0(건너뜀: isaaclab 1, pyarrow 1, CUDA 없음 1, TODO(P3) 1). 새·수정 시험 60개 따로 60 passed.

## 5. 문서
- DOC D-1: `handoff.md` 12회차 줄, `r7c12_fixes.md` :20·:22·§8(1–3)에 [해결 R7 13회차 D-1: 정본 §77 보충(10:25 UTC)] 표시. DOC D-2: `r6_eval.md:46`에 [정정 R7 13회차 D-2, 정본 §77]. handoff 머리·정본 범위 §1~§79, §2.8 13회차 줄, `direction-log.md` 행, `draft-log.md` 줄.
- 정본 §79: 위 결정 전부(사전 등록 줄 번호 포함), §77 (ii) 정정, 논문 갱신 항목.

## 6. 남은 것·확실하지 않은 것
- D1: 런타임 `M4Params.flip_th`는 한 값(모든 질문 공통)이다 — 지금 꺼져 있어 동작은 없지만, E0.5 뒤 켤 때 질문별 값을 받게 바꿔야 J4와 맞는다(정본 §79에 적음, 코드 안 바꿈). E0.5 점수 창(직전 스텝 3표)과 런타임 창(최근 4표 대 앞 4표)의 차이는 §73 결정 그대로라, "런타임과 같은 점수"는 질문별·TV 척도까지만 같다.
- D1: α 0.01이면 질문마다 성공 스텝 ≥ 99가 있어야 문턱이 생긴다(POOL P0 성공 편에서는 충분할 것으로 보이나 E0.5 본 판에서 확인).
- N1: 경계 틱 호출이 확인 뒤 epoch를 다는 것은 줄과 함께 오는 결과다(M4 "다음 Jev 입력"). 조기 호출은 다음 틱 그대로라 DEVIATE 경계에 주기 호출이 걸리면 그 호출과 다음 틱 조기 호출이 모두 DEVIATE를 싣는다(호출 예산은 불변 — 조기 호출이 다음 주기 칸을 당겨 씀).
