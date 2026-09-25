# R7 15회차 수정 (DOC D-1·D-2, N2, N10, N3, N15·N7)

- 작성 2026-09-25 13:48 UTC, 수정 에이전트(시각은 `date -u`). 대상 `r7_cycle15.md`(검토 대상 `9cee78b`); 작업 시작 HEAD `0b853c2`(메인의 b283da2·0b853c2 커밋 뒤, 작업 트리는 `r7_cycle15.md` 미추적 한 파일뿐이었다). 정본 **§81**(append만, §80 본문 무수정). **커밋 안 함**.
- 원칙: 사전 등록과 정본은 구속한다. 사전 등록 문서 무변경(`tools/prereg_hash.py --check` OK). 코드는 시험 먼저(TDD: 새 시험이 실패하는 것을 본 뒤 코드). 건드리지 않은 것: `paper/**`, `harvest/train/se2e_temporal*.py`, `tools/se2e/temporal_*.py`, 프롬프트 파일(`stagea_train.PROMPT_FILES`·`PROMPT_FILES_B`·`TEMPORAL_FILES` — 그래서 프롬프트 해시 불변), 파드의 실행 중 실험 폴더(`ckpt/se2e_scale`·`se2e_temporal`·그 로그·`r2/train`)와 고정 사본 `code_se2e_temporal`. [사용자] 줄·user-log 인용 무변경.
- 로컬 임시 `D:\tools\scratch_qdd\r7c15fix`(`pod_counts.py`, `mk_podcode.py`·`red.tar`·`green.tar`·`final.tar`, `pod_tests.sh`, `pod_final.log`, `local_pytest.log`, `sec81.md`·`draftlog_line.txt`·`apply_docs.py`). 파드 `juhyoung-native-7a2a:/data/harvest/tmp/r7c15fix`(코드 사본·pytest)는 끝에 지웠다. GPU·Isaac 안 씀; 파드 쓰기는 이 폴더뿐, 파드 명령은 `nice 10`·`OMP_NUM_THREADS=2`·`CUDA_VISIBLE_DEVICES=""`.
- **절차 사고 1건**: 로컬 Bash에 빈 `python -`(내용 없음)을 한 번 보냈다 — 표준 입력을 기다리며 멈춰 바로 중지(TaskStop); 파일 변화 없음(14회차 사고 (ii)와 같은 종류).

## 1. 문서 (DOC)

| 항목 | 근거 | 처리 |
|---|---|---|
| **D-1** 고정 선행 실행 = 비트 동일 서술 | 정본 §78 사실, `pool_replay_debug.md:15`(선행 실행은 이력 의존을 못 없앰), 풀 불신 886행·29편 | [정정 R7 15회차 D-1, 정본 §78 …] 표시: `pool.md:32`·`:33`(첫 6편 0.0은 그 편들의 측정값)·`:57`, `e_m4b_meas.md:19`, `D28-m4-critic-measurement.md:149`. 같은 사실 grep(문서·코드 주석, `third_party/`·`paper/` 제외, 선행 실행·prefix·warmup × 비트 동일·exact·0.0)으로 더 찾은 곳: `r2_datagen.md:99`("머그만 쓰는 이력에서 검증"), `draft-log.md:412`(T13 완료 줄), 코드 주석 `harvest/cli_pool.py` `canonical_prefix`·`warmup` 설명과 `warmup(env)` 호출 줄, `harvest/datagen/gen.py:266`. 맞게 적힌 곳(`pool_replay_debug.md`, `physx_hard_reset.md`, `labeler.md`, `sim/labeler.py:182-183`)과 다른 뜻의 prefix(`try_commit_prefix`, vLLM prefix cache, `--inst-prefix`, 학습 warmup)는 두었다 |
| **D-2** 자체 점검 "597행·13편" | 정본 §65(자체 점검 90편 = DEV 30시드 × P0–P2) | 파드 재확인(아래 §3) 13시드·**20편** → 정본 §81 정정 줄, `r7c14_fixes.md:24`에 [정정 R7 15회차 D-2, 정본 §81] 표시. 원인: 14회차 `pod_inspect.py`가 시드만 셌다 |
| **N15** 기록 시각 | 커밋 0790dd4 = 2026-09-25 12:57:49 UTC(`git log`, 태그 `stage3-r7fix14`) | §80 제목·`r7c14_fixes.md:3`·`handoff.md:3`의 "13:10 UTC"는 짐작 시각 → 정본 §81 정정 줄(§80 제목은 그대로); `handoff.md` 머리 = 이번 갱신 시각 + 정정 괄호 |
| **N7** handoff | 0790dd4·태그 `stage3-r7fix14` | `handoff.md:108` "커밋 안 함"에 [정정 R7 15회차 N7·N15] 표시, 정본 범위 §1~§81(`:3`·`:5`·`:83`), §2.8에 메인 커밋 줄(9cee78b·b283da2·0b853c2)과 15회차 줄, `direction-log.md` 15회차 행, `draft-log.md` 줄 |

## 2. 코드 (시험 먼저)

| 항목 | 결정 | 구현 | 시험 |
|---|---|---|---|
| **N2** 재개 검사 키 | 학습 궤적을 바꾸거나 기록되는 평가 집합을 정하는 옵션은 모두 재개 때 같아야 한다 | `stageb_train.RESUME_KEYS` + `lr_schedule`·`warmup_steps`·`train_subset`·`train_subset_seed`·`train_fraction`·`eval_train_subset`·`eval_train_per_kind`·`camera_layout`·`motion_line`·`motion_bins`·`motion_dropout`·`se2e_t_root`; 새 `RESUME_FREE`(`cmd`·`run`·`out_root`·`resume`·`stop_at`·`overwrite`·`reload_check`·`save_every`·`eval_every`·`grad_ckpt`·`init_weights`). `eval_train_*`는 학습 궤적을 바꾸지 않지만(`evaluate`는 자기 생성기) `val_per_kind`와 같은 규칙으로 넣음. `check_resume_args`: 저장된 인자에 없는 키 = 파서 기본값(옵션이 생기기 전 체크포인트 — 기본값 = 이전 동작) | `tests/train/test_r7c15_resume_keys.py`(torch 필요 → 파드): 파서의 모든 `train` 옵션이 둘 중 하나(겹침 없음), 지정 12개 ⊂ `RESUME_KEYS`, `RESUME_KEYS` 40개 각각을 바꾸면 거부(메시지에 키 이름), `RESUME_FREE`를 모두 바꿔도 받음, 12개 키가 없는 옛 인자 + 기본값 → 받음·하나라도 바꾸면 거부. **RED 15 failed / 30 passed**(12개 키 + 분류 + `RESUME_FREE` 없음 + 옛 인자) → GREEN |
| **N10** 라벨 쓰기 쪽 | 재생 거리가 없는 결과가 있으면 행은 근거 없음(§80 (1)) → null | `cli_label.replay_max(outs, field)`: 모든 결과가 수(bool 아님)면 최댓값, 아니면 None; `replay_maxabs`·`replay_obj_mm`·`replay_jpos_rad` 셋에 적용. 호출 경로 확인: `label_pool`·`selfcheck`는 늘 `state`와 `replay`를 넘기고 `labeler._replay_rollout`은 기준 상태가 있으면 분기 전에 세 값을 적는다 → 실제 값을 잃는 경로 없음(파드 풀 6,627행·자체 점검 4,970행 필드 없음·null 0). `summarize`·`poolsum`은 그대로(§80) | `tests/eval/test_r7c15_label_write.py`: 모두 0.0 → 0.0·신뢰, 한 결과 0.3 → 0.3·불신, 한 결과 필드 없음/None → 세 필드 null·불신·JSON 가능, 그 행을 `load_truth`가 모두 뺌. **RED 3** → GREEN |
| **N3** 뺀 수의 질문 범위 | 세는 방식은 그대로, 범위를 기록 | `common.load_truth`: `stats["questions"]` = 5질문 목록(→ `e05`·`calib` `meta.truth_label_trust.questions`, `rd`는 변형별); `stagea_train._items`: 결과 라벨을 읽었으면 `stats["questions"]` = `STAGEA_TRUST_QUESTIONS`("all label rows … + fine_dir near contact") → `config.json` `label_trust.questions`. `stagea_data.py`(프롬프트 파일)는 건드리지 않음 | 같은 파일: 5질문 신뢰 + `fine_dir` 불신 한 스냅샷 → `load_truth` {kept 5, excluded 0, questions 5개}, 단계 A {kept 5, excluded 1, questions = 상수}. **RED 2** → GREEN. 기존 `test_r7c14_label_trust.py`의 통계 전체 비교 5곳에 `questions` 추가(값 비교는 그대로) |

## 3. 실제 자료 확인 (파드, 읽기 전용, `pod_counts.py`, 13:32 UTC)
- 자체 점검 폴더 찾기: `data/**/dev*_P*.jsonl` → `data/pool_selfcheck`(현행) + `pool_superseded_liftcut/*` 3곳(옛 풀). 현행: 파일 90·`.done` 90·시드 30, 4,970행, 불신 **597**(필드 없음·null 0), **13시드·20편** = 3P1, 4P1, 6P0, 6P2, 9P0, 9P2, 10P1, 13P0, 13P2, 16P1, 17P1, 20P1, 21P1, 24P0, 24P1, 24P2, 25P1, 26P0, 26P1, 26P2(검토 보고서와 같음); 질문별 dir_xy 120·dir_z 108·mag_coarse 110·target 101·phase 101·fine_dir 57.
- 풀 `data/pool/labels`: 6,627행(5질문 각 1,200 + `fine_dir` 627), 불신 전체 **886**·29편, 5질문 **805**(dir_xy 167·dir_z 155·mag_coarse 160·target 160·phase 163) + `fine_dir` 81 → N3의 두 수 차 = `fine_dir`.

## 4. 시험 묶음
- 로컬(Git Bash, `cd D:/qdd && python -m pytest -rs`, 13:43–13:45 UTC): **1006 passed, 15 skipped**, rc 0(건너뜀: torch 없음 10 — 새 `test_r7c15_resume_keys.py` 포함, inspect_robots 2, pyarrow 1, isaaclab 1, TODO(P3) 1). 작업 트리의 다른 에이전트 파일은 없었다(HEAD 0b853c2 + 이 수정).
- 파드 CPU(`juhyoung-native-7a2a`, `venv_train`, 새 코드 사본 = `git -c core.autocrlf=false archive 0b853c2` + 이 수정 코드·시험 9파일(CRLF → LF), `CODE_VERSION` JSON {commit 0b853c2…, dirty true}, tar sha256 `86785a5f89a5541d`; 고정 사본 `code_se2e_temporal`은 쓰지 않음): RED 사본(`857d907c…`, `stageb_train.py` 수정 전)에서 재개 시험 15 failed; GREEN 사본에서 `test_r7c15_resume_keys.py`·`test_stageb_torch.py`·`test_r7c15_label_write.py`·`test_r7c14_label_trust.py` **105 passed**; 최종 사본(같은 sha)에서 **`tests/train` + `tests/eval` 381 passed**, rc 0(13:45:18–13:46:27 UTC).

## 5. 남은 것·확실하지 않은 것
- N2의 "옛 체크포인트 = 기본값" 규칙은 각 옵션이 이전 동작을 지키는 기본값으로 더해졌다는 사전 등록 문장(`prereg_se2e_diag.md` §1, E-TC 사전 등록의 OPT-IN 기본값)에 기댄다. 앞으로 옵션을 더할 때 이 성질이 없으면 기본값 비교가 틀린다 — 분류 시험이 새 옵션을 잡으므로 그때 정한다.
- 파드의 시간 맥락 실험(고정 사본)은 옛 `RESUME_KEYS`로 돈다(재개를 쓰면 이 빈틈이 그 사본에 남음) — 건드리지 말라는 지시대로 두었다.
- `poolsum`·`summarize`는 null 행을 0으로 요약한다(§80대로 그대로). 지금 null 행은 없다.
- 검토 NOTE 중 N1(`--m4-h` 도움말), N4(`se2e_train.md` 반올림 5칸), N5(사전 등록 커밋 시각), N9(논문)는 이번 지시 범위 밖이라 두었다.
