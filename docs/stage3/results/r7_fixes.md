# R7 순회 수정 기록

## 사이클 1 수정

- 대상: `r7_cycle1.md`의 코드 항목(D1, D2, C6 코드 주석, N1–N5 중 코드·파드 항목). 문서 항목 C1–C5·C7·C8은 메인 세션이 따로 고친다(이 절에서 정본·handoff·계획·direction-log·user-log는 건드리지 않음).
- 작성 2026-09-25 00:05 UTC(`date -u`, 파드 시계와 같음). 커밋 안 함. 작업 트리 기준 HEAD `36de5c4` + 수정 파일(아래 목록).
- 방법: 항목마다 실패하는 시험을 먼저 쓰고(로컬에서 실패 확인) 고친 뒤 통과를 확인했다(TDD).
- 파드 규칙: 모든 파일은 `/data/harvest` 아래(코드 사본 `/data/harvest/code_r7fix`, 산출 `/data/harvest/tmp/r7fix`, 카나리 `/data/harvest/canary`, 캐시 `/data/harvest/cache/pyc_r7fix`, 무거운 kit 캐시 `ir/kitcache/cyclo-r7fix`). GPU 2 = 학습 계산만(시작 전 1 MiB 확인), GPU 3 = vLLM(카나리), 렌더 없음, GPU 0(라벨러 사용 중)·1은 쓰지 않음. 시드 DEV·R2-DEV만.

### 1. D1 — 정본 §63 (1)–(3)과 §62 hz를 코드에 넣음

| §63 결정 | 코드 |
|---|---|
| (1) 팔별(왼·오) 정규화 통계 | `stageb_data.ActionNorm`: `arms[arm] = {mean, std, p_mean, p_std}`, `stats(arm)`; `target/action/cond_script/proprio`가 표본의 `arm`을 받는다. 최상위 통계는 전체 합(그 팔 통계가 없을 때와 §63 전 체크포인트용). `stageb_model.cond/targets/predict`, `stageb_train.evaluate`, 런타임 `fused_model`(한 팔 = right 통계, tau 대치값도 right)이 팔별 통계를 쓴다. |
| (2) 그리퍼 → 데이터셋별 [0, 1] 열림 정도, 범위 밖 자름 | `stageb_data.GRIP_CAL`·`grip_open01`·`grip_rate01`(속도는 같은 배율, 자르지 않음)·`grip_value`(역사상)·`grip_source`. `make_sample`이 행동 8번째 차원과 proprio `grip`을 사상한다(행 원본은 그대로). 보정: 시뮬 = 패드 간격 m, 열림 0.107 m(`sim.scene.GRIP_MAX_W`)·닫힘 0; S-E2E = `gripper_{l,r}_joint1`, 열림 0.0·닫힘 = 기록 상태의 99.5 백분위 두 팔 평균(RB1 1.096/1.1005 → **1.10**, RB2 1.152/1.118 → **1.14**; 0.5 백분위 0.000 / 0.003–0.017 → 0.0). 원자료 `/data/harvest/tmp/r7fix/grip_range.json`(RB1 25,433행, RB2 17,380행). 원격조종 명령은 −0.46…1.34까지 나가서 잘린다. 보정이 없는 실데이터 kind(예: RB9)는 거부. `ActionNorm.grip_space = "open01@v1"`가 체크포인트에 기록되고, 런타임(`fused_model.grip_to_model/grip_from_model`)은 aiworker 패드 간격을 열림 정도로 넣고 청크 그리퍼 열을 m로 되돌린다. `grip_space`가 없는 옛 체크포인트는 m 그대로. 잔차 모드 그리퍼 ξ 기본값은 0.005 m → 0.05(열림 정도, = 5 mm/107 mm)로 단위를 맞췄다. |
| (3) 토크 없음 → `tau` 마스크 0(입력·손실에서 제외) | `proprio_mask`를 실제로 읽는다: `ActionNorm.fit`은 가려진 값을 통계에서 뺀다, `proprio(p, arm, mask)`는 가려진 차원을 0으로, expert 입력에 키별 마스크 채널 4개를 붙인다(`PROPRIO_IN_DIM = 23 + 4`, 새 모델의 `ExpertConfig.proprio_dim`; 23차원 옛 expert는 값만). proprio를 읽는 손실은 없다(시험으로 손실 로그 키 확인). `check_row`가 `proprio_mask` 키·값(0/1)을 검사. |
| §62 로더가 데이터셋별 hz를 받음 | `stageb_data.DATA_HZ = {pool: 30, r2: 30, se2e: 10}`, `load_for_training(data, …) -> (samples, hz)`, `load_stageb(…, hz)`, `se2e_data.load_se2e(…, hz)`(다른 hz 행은 `check_row`가 거부), 한 학습 세트에 H가 섞이면 거부. `stageb_train train --data r2|pool|se2e`(`--se2e-root`, `--se2e-kinds`, `--no-labels`), hz·데이터 종류를 `stageb.json`에 저장(런타임 `chunk_dt = 1/hz`), `--reload-check`(저장 → 새 백본에 재적재 → 같은 잡음으로 청크·검증 지표 비교, N10도 해소). |

시험(먼저 실패 확인 → 통과):
- `tests/train/test_stageb_data.py`: `test_grip_openness_maps_per_dataset_and_clips`, `test_make_sample_maps_the_gripper_to_openness_without_touching_the_row`, `test_action_norm_keeps_per_arm_statistics`(옛 JSON 적재 포함), `test_masked_proprio_is_left_out_of_statistics_and_input`, `test_training_loader_takes_the_dataset_rate`.
- `tests/train/test_stageb_torch.py`(파드, torch): `test_masked_proprio_is_zeroed_with_a_mask_channel_and_never_reaches_the_expert`(가려진 tau를 999로 바꿔도 조건이 비트 단위로 같음, 마스크 채널 [1, 1, 0, 1]), `test_pre_s63_expert_without_mask_channel_keeps_its_23_d_condition`, `test_per_arm_statistics_are_used_for_each_samples_arm`(왼팔 표본의 목표·조건·복원이 왼팔 통계, 오른팔 통계와 다름).
- `tests/runtime/test_fused_model.py`: `test_gripper_space_round_trip_at_the_runtime_boundary`.

실제 실행(파드 GPU 2, 계산만, `/data/harvest/tmp/r7fix/run_stageb.sh`, 로그 `run_stageb.log`, 체크포인트 `tmp/r7fix/ckpt/{se2e_smoke,r2_smoke}/last`; 파이프라인 확인이며 결과 수치 아님 §56):

| 데이터 | hz / H | 학습·검증 표본 | 팔 | 그리퍼 원천 | 6스텝 | 저장 → 재적재 |
|---|---|---|---|---|---|---|
| S-E2E(`--data se2e`, RB1+RB2 전체 적재 후 train 64개 무작위) | 10 / 5 | 64 / 1,799 | 왼 24·오 40 | RB1, RB2 | 끝까지 돎. 결정 NLL(학습) 2.14 → 0.68, 검증 결정 4.10 → 1.77 | 행동 최대 차 **0.0**, 검증 지표 같음, norm 같음 |
| R2 DEV(`--data r2`, standard/mug_tray + dr/bottle_tray, 검증 시드 5) | 30 / 15 | 64 / 564 | 오 64 | sim_width_m | 끝까지 돎. fm·aux·ver 손실 계산 | 행동 최대 차 **0.0**, 검증 지표 같음, norm 같음 |

- S-E2E 64개는 전부 `proprio_mask.tau = 0` → 저장된 tau 통계 p_mean 0·p_std 1(값이 하나도 없으므로 중립), `stageb.json`: hz 10, horizon 5, proprio_dim 27, arms {left, right}, grip_space open01@v1. R2: hz 30, horizon 15, arms {right}.
- 끝난 뒤 GPU 2 = 1 MiB(프로세스 남지 않음).

### 2. D2 — 요청 해시·카나리 id를 폐루프 로그에, 매일 카나리 최소 구현

- `harvest/runtime/reqhash.py`(새): `request_hash(payload, images)` = 정렬된 키·압축 구분자 JSON(`{"payload", "images": {이름: sha256}}`)의 sha256. 이미지 해시: 바이트(보낸 JPEG) = sha256, 배열(원 프레임) = "shape|dtype|" + 바이트의 sha256(런타임 JPEG 인코딩은 결정적이라 원 프레임이 보낸 바이트를 식별).
- `runtime/core.py`: 결정 호출(`call` 행), 청크 호출(`chunk` 행), Astra 하트비트(`astra` 행)마다 `request_sha256`, `image_sha256`, `canary_id`를 기록. 해시 계산은 작업 스레드에서(롤아웃 스레드 비용 없음). Astra 요청은 base64 이미지를 빼고 그 JPEG sha256을 넣어 해시(§28 A6). `RuntimeConfig.canary_id`(결정 모델, 기본 "none") / `astra_canary_id`(= "none": Astra 카나리는 유료 호출이라 돌리지 않음, 이 실행들의 Astra는 모의 — "없음"을 명시로 기록).
- `harvest/eval/canary.py`(새, `python -m harvest.eval.canary`):
  - `build-set --data DIR --seeds 0-2 --n 12 --name dev_v1`: DEV 결정 스냅샷을 고르게 골라 프레임과 함께 `/data/harvest/canary/sets/<name>/`로 복사(`lines.jsonl` + `img/` + `manifest.json`의 set_sha), splits 가드로 DEV만, 세트는 다시 쓰지 않음, 풀 `oracle`은 복사하지 않음.
  - `--model M [--set] [--repeats 2] [--gpu 3]`: 세트 × 결정 질문 5개(question_id@vN 기록)를 zero-shot/병합/어댑터(vLLM, lead) 또는 단계 B 체크포인트(fused 서버 `/decide`, IMG) 또는 mock으로 `repeats`번 → `/data/harvest/canary/canary_<YYYYMMDD UTC>_<지문>.json`(id, 보기 키·확률, 그날 test-retest 바닥, 같은 지문·세트의 가장 이른 기준일, `harvest.canary.canary_compare` 비교·`drift_suspect`, 확률 TV 거리). 모델·날짜당 하나(`--force`면 새 id로 다시).
  - `latest_canary(fp)`: 그 지문의 최신 카나리 id(없으면 `{"id": "none", "reason"}`), `canary_id_for(model_path)`.
- 읽고 기록하는 곳: `eval/common.run_meta`에 `"canary"`(e05·rd·calib·closed 모두), `eval/closed.py`가 워커 spec에 `canary_id`를 넣어 `RuntimeConfig.canary_id` → 부가 JSONL 모든 호출 행, `runtime/run_r5.py`도 같음.
- 시험: `tests/runtime/test_reqhash.py`(2), `tests/runtime/test_core_fakeworld.py::test_every_call_logs_its_request_hash_and_canary_id`(modular·fused, call·chunk·astra 행 모두 64자리 해시, 이미지 해시, canary id / Astra "none"), `tests/eval/test_canary_cmd.py`(세트 만들기·불변, CAL 500 거부, mock 카나리 id·기준일 비교에서 drift 검출·최신 id·`--force`, run_meta 기록), `tests/eval/test_closed_pure.py::test_worker_spec_carries_the_latest_canary_id`("none"과 실제 id 두 경우).
- 파드 실제 실행: 세트 `dev_v1`(jsel_dev/P0 DEV 0–2에서 12 스냅샷, set_sha `96bfc52a21afc751`). mock 카나리 `cn20260924_mock_ae0d1a`. **단계 A SFT 병합 모델**(`ckpt/stageA/sftA_pool_v1/merged`, 지문 `ed387f59…` = R7 cycle-1 보정 파일의 지문) vLLM GPU 3, 반복 2: id **`cn20260924_ed387f59_76f160`**, 호출 오류 0, 바닥 0.0(배치 불변), 97 s, 끝난 뒤 GPU 3 = 1 MiB(자기 vLLM만 종료). 이 모델로 폐루프를 돌리면 이 id가 모든 call 행에 기록된다. 기준일이 오늘이라 비교는 다음 날부터.
- 한계(기록): Astra 카나리 없음("none" 명시), 한 모델·하루 한 검정이라 Holm 없음, 세트 크기·반복 수는 [가정](E-first §1.8 "E0 뒤 정함").

### 3. C6 — GPU 문구(코드 주석)

- `harvest/train/stageb_train.py` 머리: "GPU only when free (never GPU 2)" → "GPU 2 = training / inference compute (user-log 62, 64: no rendering on GPU 2; nvidia-smi로 비었는지 먼저 확인)".
- `harvest/train/stagea_train.py` 머리: `CUDA_VISIBLE_DEVICES=1 (smoke)` → `CUDA_VISIBLE_DEVICES=2`(GPU 1 = Isaac 렌더, 3 = vLLM), 사용법 첫 줄 `train --pool DIR --rule R` → labels_v2 기본(`--rule`은 `--target-source outcome`일 때만).
- `tools/ir/ir_run.sh`(로컬 사본) "GPU 0 만 … (GPU2 금지)" → "렌더는 GPU 0·1만(1 = Isaac, 0 = 비어 있을 때만; GPU 2 학습 전용·렌더 금지, 3 = vLLM)". 동작(미지정 시 0)은 그대로. 파드 `/data/harvest/ir/ir_run.sh`는 공용 실행 파일이라 건드리지 않음(같은 주석이 남아 있음).
- 나머지 검색 결과: `eval/closed.py`의 "never GPU 2"는 Isaac 렌더에 대한 문구라 맞음, `runtime/fused_model.py`("model GPU 2 or 3")·`m4b/vhead.py`(GPU 2)·`tools/r3_bench.py`(GPU 2)·`tools/r5/serve.sh`(GPU 3) 맞음. `cli_e3st.py:10`·`perception/run_r1.py`의 GPU 1은 user-log 62 이전의 끝난 실험(E3-ST, R1) 실행 기록이라 고치지 않았다.

### 4. NOTE 처리

- N1 `TORCH_DISABLE_NATIVE_JIT=1`: 파드 `/data/harvest/env.sh` 끝에 `export TORCH_DISABLE_NATIVE_JIT=1`(설명 주석 포함) 추가, 원본 백업 `/data/harvest/tmp/env.sh.bak_r7fix`. `stagea_train.py`·`stageb_train.py`가 torch import 전에 `os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")`(명시 값은 존중). 시험 `tests/train/test_stagea_train_cli.py::test_import_disables_torch_native_jit_unless_set`. 이 변수에 기대는 로컬 실행 스크립트는 저장소에 없음(fused 서버는 `eval/common.py`가 이미 넣음, 파드의 옛 run 스크립트는 env.sh를 source하므로 이제 받음).
- N2: `tests/sim/test_randomize_logic.py` `EXTRA = range(500, 700)` → `range(3000, 3200)`, 주석 교정(CAL 500–549 / TEST / TEST-P5 / POOL / R2_TRAIN 밖). 새 시험 `test_extra_seeds_avoid_every_reserved_split`(수정 전 실패 확인). 풀 항목 전부 사용 등 기존 단정은 새 범위에서도 통과.
- N3: LeRobot 내보내기 시험의 건너뜀 이유를 명시("… pod: venv_e3st + pylib_lerobot + pylib_pytest"), lerobot이 있으면 `LeRobotDataset` 적재 결과(프레임 12·에피소드 1·action0 같음)까지 단정. 파드에 pytest를 venv 밖 대상 폴더 `/data/harvest/r2/pylib_pytest`로 설치(venv 수정 없음). `venv_e3st/bin/python -m pytest`(PYTHONPATH = 코드:pylib_lerobot:pylib_pytest)로 `tests/datagen/test_episode_files.py` **6 passed**(내보내기 왕복 포함). 로컬·venv_train에서는 이유를 밝히고 건너뜀.
- N4 파드 고아 대기 셸: 5개(692841·1222511·1223858·1728423·1728657) 각각 전체 명령줄 확인 = `bash -c until ! pgrep -f "r3_bench.py stagea|stageb" …; do sleep …; done; grep … /data/harvest/r3/bench_{a,b}.out`, 부모 없음(PPID 0), 시작 2026-09-25 04:03–04:32 KST(= 09-24 19:03–19:32 UTC, R3 시간대), 살아 있는 `r3_bench` 프로세스 없음. cwd는 `/`(kubectl exec 기본값)라 "cwd가 /data/harvest 아래" 조건 자체는 맞지 않았다. 대신 명령줄이 우리 R3 산출물(`/data/harvest/r3/…`)만 읽는 것으로 귀속을 확인했고, 죽이기 직전 같은 명령에서 명령줄 패턴을 다시 맞춘 뒤 PID로 종료 → 5개 모두 사라짐. 확인 중 같은 종류의 R3 고아 2개를 더 찾았다: **2624175**(`r3_bench.py stageb` 대기 → `bench_b2.out` grep), **2629029**(`r3_bench.py` 대기가 풀리면 `/data/harvest/r3/smoke_a.sh`를 새로 써서 GPU 2에서 단계 A 학습을 띄우는 셸 — pgrep 자기매칭으로 영원히 대기, 풀리면 위험). 둘 다 같은 방식으로 확인 후 종료. 남은 `until ! pgrep` 셸 0개. 다른 프로세스(`while true; sleep 300` 두 개, `/data/juhyoung_pi05/mill_handoff.sh` 등 다른 프로젝트)는 건드리지 않음.
- N5 `/home1/irteam/.triton/cache`: 트리에 파일 0개(빈 해시 폴더 `q4oI…` 하나), `.triton`·`cache`·해시 폴더 모두 2026-09-24 17:57:21 KST(08:57 UTC) 같은 순간 생성 → `rmdir`(빈 폴더만 지워지는 명령)로 해시 폴더·`cache`·빈 `.triton`까지 제거. 이번 작업으로 `/data` 밖에 새로 생긴 파일 없음(`/home1/irteam` 폴더 시각만 rmdir로 바뀜).
- N10: `stageb_train train --reload-check`로 해소(위 1절).

### 5. 시험 결과

- 로컬 `cd D:/qdd && python -m pytest -q`: **784 passed, 11 skipped**(수정 전 768/11). 건너뜀은 torch·pyarrow·inspect_robots 없음과 TODO(P3).
- 파드(`venv_train`, IR PYTHONPATH, CPU, `code_r7fix` + docs): **826 passed, 3 skipped**(pyarrow → venv_e3st에서 따로 통과, CUDA 없음 1, TODO(P3) 1). torch 시험(`test_stageb_torch` 새 3개, `test_stageb_qwen` tiny 실구조 포함) 모두 통과.
- 파드 `venv_e3st` LeRobot: 6 passed.

### 6. 바꾼 파일

- 코드: `harvest/train/stageb_data.py`, `harvest/train/stageb_model.py`, `harvest/train/stageb_train.py`, `harvest/train/se2e_data.py`, `harvest/train/stagea_train.py`, `harvest/runtime/core.py`, `harvest/runtime/fused_model.py`, `harvest/runtime/run_r5.py`, `harvest/eval/common.py`, `harvest/eval/closed.py`, 새 `harvest/runtime/reqhash.py`, 새 `harvest/eval/canary.py`, `tools/ir/ir_run.sh`(주석).
- 시험: `tests/train/test_stageb_data.py`, `tests/train/test_stageb_torch.py`, `tests/train/test_stagea_train_cli.py`, `tests/runtime/test_fused_model.py`, `tests/runtime/test_core_fakeworld.py`, 새 `tests/runtime/test_reqhash.py`, 새 `tests/eval/test_canary_cmd.py`, `tests/eval/test_closed_pure.py`, `tests/sim/test_randomize_logic.py`, `tests/datagen/test_episode_files.py`.
- 파드(모두 `/data` 아래): `env.sh`(한 줄 추가), `code_r7fix/`, `tmp/r7fix/`(1.3 GB, 작은 체크포인트 2개 포함 — 지워도 됨), `canary/`(세트 dev_v1 + 카나리 2개), `r2/pylib_pytest/`, `cache/pyc_r7fix`, `ir/kitcache/cyclo-r7fix`(Isaac python 의존성 확인 1회).
- `/data` 밖 변경: 파드 `/home1/irteam/.triton`(빈 폴더) 삭제뿐. 로컬 C: 쓰기 없음(임시 = `D:\tools\scratch_qdd\r7fix`, pytest = `D:/tools/scratch_qdd/pytest_tmp`).

### 7. 남은 것 / 다음 순회에 볼 것

- 문서 항목 C1–C5·C7·C8은 메인 세션 몫. §63 (1)–(3) 구현과 D2(요청 해시·카나리)를 정본 §42·§63 영향 줄, `r5_closed_loop.md:16` 주장과 맞출지는 메인 세션이 판단.
- 그리퍼 사상은 정본대로 선형이다. 시뮬 패드 간격은 관절값과 비선형(`sim.scene._GW`)이라 두 데이터셋의 "열림 0.5"는 물리적으로 같지 않다. S-E2E와 시뮬을 한 모델에 섞을 때 영향 확인 필요.
- 런타임 tau는 여전히 학습 평균 대치(C8-5)다. 새 체크포인트는 마스크 채널이 있어 "tau 마스크 0"으로 넣을 수도 있지만, R2(토크 있음)로만 학습한 모델엔 분포 밖이라 바꾸지 않았다.
