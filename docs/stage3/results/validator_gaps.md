# R2 검증기 약점 묶음 (태그 뒤 TDD)

- 작성: 2026-09-26 01:02:45 UTC(`date -u`) 시작, 최종 검증 01:15:29 UTC. 기준: 태그 `stage3-e2e-ready` = 3d4738a 뒤의 dev(첫 검증 HEAD 18d4e2f, 최종 검증 HEAD 205db33 — 둘 다 `validate.py`는 태그와 같은 6111b4e 판). 범위: R7 31–37회차 NOTE의 검증기 관찰 N131·N132·N142·N143·N154·N165·N190·N193·N210.
- 바꾼 코드: `harvest/datagen/validate.py`만(+ 새 시험 `tests/datagen/test_validate_gaps.py` 37개). **`harvest/train/stageb_data.py`(`check_row`)는 바꾸지 않았다** — `stageb_train.PROMPT_FILES_B`에 들어 있어 체크포인트 `files_sha`가 바뀐다(아래 판정 1).
- 기준점 태그 이후의 코드 변경이므로 다음 R7 회차의 검토 대상이다(handoff §0 R7 줄).

## 1. 결론

- 9개 관찰 모두 **예외나 조용한 통과 대신 기록되는 구조 오류**가 됐다. 약점 시험 32개: RED(고치기 전) **32 failed** → GREEN. 첫 구현이 R7 37회차가 통과시킨 경계(행 `H` 15.0 실수)를 예외로 만드는 것을 커밋 전에 찾아 경계 시험 5개를 더했다(3개 RED → GREEN, 5절).
- 실데이터(파드, 읽기 전용, 최종 코드): R2 DEV **36/36 오류 0**(예외 0, 도장 메타 대비 `structural_ok`·`valid_for_training` 불일치 0), R2_TRAIN **306편**(18폴더 × 17시드, 폴더 안 시드 등간격) **오류 0**(예외 0, 불일치 0). 새 검사로 떨어지는 실제 편은 없다.
- 실제 편 사본(DEV dr/mug_tray/P0 ep0, 274프레임)에 약점 15종을 하나씩 넣으면 **15/15 모두 오류로 기록**, 무수정 사본은 오류 0.
- 전체 시험(최종 코드): 로컬(Git Bash) **1,203 passed · 21 skipped, EXIT 0**, 파드 CPU **1,352 passed · 6 skipped, EXIT 0**.

## 2. 약점별 확인 → 고침

줄 번호는 18d4e2f(= 3d4738a)의 `validate.py`에서 다시 확인했다(`git show HEAD:harvest/datagen/validate.py | grep -n`).

| NOTE | 옛 동작(확인한 위치) | 고침 | 오류 문구 |
|---|---|---|---|
| N131 | `:78` 검증 대상 검사가 줄의 `decision` 표지를 읽음(라벨 검사는 `is_decision`) → k20 표지 끄고 `prev_step` 지우면 통과 | 검증 대상은 `is_decision(k)`로 고르고, 줄 표지 ≠ `is_decision(k)`도 따로 오류 | `decision flag != is_decision(k) at [20]`, `verification target missing at [20]` |
| N132 · N210② | `:83` `z[key]`가 없는 배열에서 `KeyError`(`grip`·`tau`), `:86` `hold_n` 같음 | `key not in z.files` → 오류 기록, 다음 검사 계속 | `npz grip: missing` |
| N193 | `:65` `[r["k"] …]`가 `check_row` 전에 `KeyError: 'k'` | `r.get("k")`(목록 검사가 어긋남을 기록), 행 오류 문구도 `r.get`; 행 `k`가 편의 프레임이 아니면(null 등) 행 오류 | `stageb rows are not one per non-terminal frame`, `row kNone: missing field 'k'` |
| N142 · N210③ | `:49` `max()`가 가운데 NaN을 못 고름(비교가 늘 거짓) → 통과; 문자열 `t`는 `TypeError` | 프레임마다 `t`가 유한한 수(bool 아님)인지 먼저 검사, 격자 편차는 수인 프레임만, `hold_n` 합 검사는 첫·끝 시각이 수일 때만(아니면 앞 오류가 이미 기록됨) | `frame time not a finite number at [145]` |
| N143 | 행 `seed` 변경·`phase_id` null 통과(`check_row`는 필드 존재만) | 행 `seed`·`kind`·`task` = 편(파일 시드·메타), 행 `phase_id` = 그 프레임 줄의 `phase` | `row k40: seed 1 != episode 0`, `row k40: phase_id None != frame phase 'descend'` |
| N154 | 행 `kind`·라벨 행 비-`k` 필드 변경 통과(라벨은 k 집합만) | 행은 위와 같고, 라벨 행 `seed`·`kind`·`task` = 편 | `row k50: kind 'P9' != episode 'P0'`, `labels_v2 k30: seed 1 != episode 0` |
| N165 | aux 값 NaN·`action_exec` 1e6 통과 | aux `reg` = 유한한 수 또는 null, `cls` = 0/1 또는 null; 행 `action_exec`·`action_script` = npz `action`의 그 청크(`timing.chunk`, 끝 패딩 포함, atol 1e-5) | `row k60: aux.reg.g2tgt_dx = nan, want a finite number or null`, `row k70: action_exec != npz action (chunk at k70, atol 1e-5)` |
| N190 | 행 `skill_id` 아무 문자열 통과 | `skill_id` = `rows.skill_of(phase_id)`(생성기와 같은 함수) | `row k80: skill_id 'r7c35_skill' != 'pick'` |
| N210① | 행 `proprio.q` NaN 통과(`check_row`는 길이만) | `validate.py`에서 `proprio` 네 키(q·qd·tau·grip) 값이 모두 유한한 수 | `row k90: proprio.q not finite: [nan, …]` |

행 오류는 기존과 같이 편마다 앞 3개만 적고 `row_errors`에 수를 센다; 라벨 행 오류도 앞 3개만 적는다.

## 3. 판정(결정)

1. **N210① 행 고유감각 유한성 — 계약에 넣는다, 단 `validate.py`에서만.** 행 `proprio`는 학습 입력(expert proprio)이라 NaN이면 손실이 깨진다; 계약(`stageb_data.py` 머리말)은 값을 rad·rad/s·N m·m로 정의하므로 유한한 수가 계약의 뜻이다. 그러나 `check_row`가 든 `stageb_data.py`는 `PROMPT_FILES_B`(체크포인트 `files_sha`)에 들어 있어 고치면 기존 체크포인트 해시가 모두 바뀐다 → **바꾸지 않고** R2 검증기(`validate.py`)에만 넣었다. 결과: R2 생성 편은 막히지만, `check_row`만 쓰는 다른 경로(S-E2E 변환 행 등)는 여전히 길이만 본다(남은 범위, 4절).
2. **N165 행동 값 — 범위 문턱 대신 npz 대조.** 관절 한계 같은 새 문턱을 정하지 않고, 행이 만들어진 원천(npz `action` = 실행된 명령)과 같은지를 본다. 실측 최대 차 **5.0e-7**(DEV 10,615행 전부, 행은 소수 6자리 반올림) 대 허용 1e-5(20배 여유). R2는 잔차가 없어 `action_script` = `action_exec`(`rows.stageb_row`)이므로 둘 다 대조한다. npz `action` 자체의 값 범위는 보지 않는다(유한성만 — 기존 검사).
3. **N131 — 두 겹.** 검증 대상은 `is_decision(k)`로 고르고(라벨 검사와 같은 원천), 줄 `decision` 표지가 다르면 그 자체를 오류로 적는다(LeRobot `decision` 열이 이 표지를 쓴다).
4. **N143·N190 — 원천 대조.** `phase_id`는 허용 목록이 아니라 그 프레임 줄의 `phase`와 같아야 하고(null이면 다름), `skill_id`는 생성기와 같은 `skill_of`로 계산한 값과 같아야 한다.
5. **N154 — 키 필드만.** 라벨 행의 `seed`·`kind`·`task`를 편과 대조한다. `labels_v2` 답 내용을 줄에서 다시 계산해 대조하지는 않았다(범위 밖, 4절).
6. **예외 계열(N132·N193·N210②③)** — 검사 하나가 깨져도 나머지 검사를 계속하고 오류 목록에 적는다; `valid_for_training`은 거짓이 된다(조용한 통과 없음).
7. **이전 회차가 통과시킨 경계는 그대로 통과.** R7 31–37회차 139번 대조 중 '오류 0'이었던 21종(여분 필드·`aux {}`·`hz 30.0`·`H 15.0`·프레임 `k 137.0`·`valid` 실수형 등)을 새 검사와 대조했다; 새 검사가 닿는 것(`H`·행/줄 `k` 실수형, `aux {}`, proprio 여분 키, 라벨 여분 필드)은 시험으로 고정했다.

## 4. 남은 범위(이번에 고치지 않음)

- 프레임 줄의 `k`·`verify`·`images` 필드 자체가 없을 때의 예외(관찰된 NOTE가 아님), 깨진 npz 파일(`np.load` 실패).
- `labels_v2` 답 내용 재계산 대조, npz 배열 값의 물리 범위.
- `check_row`(`stageb_data.py`)의 고유감각·aux 유한성 — 판정 1에 따라 R2 밖 경로는 그대로.

## 5. 시험

- **RED 1**(고치기 전, 로컬): 약점 시험 **32 failed** — 조용한 통과(`errors == []`) 23개(가운데 프레임 `t` NaN 포함), `KeyError` 4개(npz `grip`·`tau`·`hold_n`, 행 `k`), `TypeError` 3개(프레임 `t` 문자열·None·끝 프레임 문자열), 다른 문구 2개(`t` = inf·True → 격자 편차로만 잡힘). 첫 구현 뒤 32 passed.
- **RED 2**(첫 구현 뒤, 커밋 전 경계 점검): R7 37회차 대조 '행 k101 `H` 15.0 → 오류 0'을 첫 구현의 `chunk(act, k, H)`가 `TypeError`로 깨뜨린다는 것을 코드 검토에서 찾음 → 경계 시험 추가: 행 `H` 15.0(`TypeError`)·행 `k` 5.0(`IndexError`)·행 `k`·`phase_id` null(`TypeError`) **3 failed**, 줄 `k` 5.0 1 passed(보존 확인). 고침: 행 `k`가 편의 프레임이 아니면 `ValueError`, 청크는 `int(k)`·`int(H)`로. 보존 시험 1개(`aux {}`·proprio 여분 키·라벨 여분 필드)는 처음부터 통과(기존 동작 고정용).
- **GREEN**: `tests/datagen/test_validate_gaps.py` 37 passed; `tests/datagen` 54 passed · 1 skipped(pyarrow 없음 — 기존).
- **전체(로컬, Git Bash)**, `python -m pytest -rs -o addopts="-p no:cacheprovider" -o tmp_path_retention_policy=failed --basetemp=D:/tools/scratch_qdd/valgaps/ptall tests`: 최종 코드 **1,203 passed · 21 skipped, EXIT 0**(4 min 20 s). 그 전 첫 구현 때 1회차는 **1 failed · 1,197 passed · 21 skipped** — 실패는 `tests/astra_motion/test_e2e_fake.py::test_stagger_truth_succeeds_and_replays[F0]`(`stream_time_limit`; 벽시계 `time.sleep` 지연 모델로 실시간 비율을 재는 시험, `validate.py`를 부르지 않음), 그 파일만 다시 돌리면 14 passed, 2회차 전체 1,198 passed · 21 skipped(함정 P74). 로컬 작업 트리에는 다른 에이전트의 미커밋 `tests/couple/`가 있어 로컬 수에 들어간다.
- **파드 CPU**(`venv_train`, `CUDA_VISIBLE_DEVICES=""`, `nice 10`, `OMP_WAIT_POLICY=PASSIVE`; 사본 = `git -c core.autocrlf=false archive HEAD`(205db33) + 이 변경 두 파일, CR 0, `CODE_VERSION` JSON `dirty: true`): **1,352 passed · 6 skipped, EXIT 0**(01:12:46–01:15:29Z). 첫 구현 때 파드 첫 실행(18d4e2f 사본)은 13 failed였는데 원인은 사본의 `CODE_VERSION`을 JSON이 아닌 글로 쓴 내 실수(`eval/common.git_commit`이 JSON으로 읽음, 함정 P73) — JSON으로 고친 뒤 1,337 passed · 6 skipped.

## 6. 실데이터 재검증 (파드, 읽기 전용, 최종 코드)

| 묶음 | 편 | 폴더 | 프레임 | 행 | 결정 프레임 | 예외 | 오류 있는 편 | 도장 메타 대비 불일치 | 유효 |
|---|---|---|---|---|---|---|---|---|---|
| R2 DEV `/data/harvest/r2/dev` | 36(전부) | 6 | 10,651 | 10,615 | 1,081 | 0 | **0** | 0 | 32 |
| R2_TRAIN `/data/harvest/r2/train` | 306(6,000 중) | 18 | 90,502 | 90,196 | 9,181 | 0 | **0** | 0 | 272 |

- 표본: 폴더마다 시드 순으로 17개 등간격(첫·끝 포함). 최종 코드 실행 01:12:14–01:12:39Z(첫 구현 때 00:54:17–00:55:25Z에도 같은 수). 스크립트 `D:\tools\scratch_qdd\valgaps\revalidate.py`(파드 `/data/harvest/tmp/valgaps/reval2.json`).
- 행동 대조 여유: DEV 전 행 `|행 − npz 청크|` 최대 5.0e-7(`act_margin.py`).
- 음성 대조(실제 편 사본, `neg_real.py`; 원본은 읽기만, 이미지는 링크): 무수정 오류 0; N131 표지 k20 → `decision flag …`; 표지 + `prev_step` 삭제 → 두 오류; npz `grip`·`tau` 삭제 → `missing`; 행 k30 `k` 삭제 → 두 오류; 프레임 k145 `t` NaN·문자열 → `frame time not a finite number at [145]`; 행 seed·phase_id null·kind P9·라벨 seed·aux NaN·`action_exec` 1e6·`skill_id`·`proprio.q` NaN → 2절 문구. **15/15 검출, 예외 0**(최종 코드 01:12:41Z).

## 7. 규칙 준수

- dev만, 저장소 밖 쓰기는 `D:\tools\scratch_qdd\valgaps`(C: 쓰기 없음). 스크립트는 Write 도구로 만들어 경로로 실행; 파드 작업 폴더 `/data/harvest/tmp/valgaps`, `source /data/harvest/env.sh`, CPU만(GPU 2·3의 E-MA2와 남의 프로세스 무접촉). 파드에서 결과 JSON 개수를 한 번 `python3 -c`로 읽었다(읽기 전용 한 줄, 규칙 어김 — 기록해 둠).
