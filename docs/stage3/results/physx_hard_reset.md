# 에피소드마다 PhysX 장면 재생성 (physx_hard_reset)

- 작업 시각: 2026-09-25 09:58–11:10 UTC(파드 `date -u`). 파드 `juhyoung-native-7a2a`, GPU 0·1만(GPU 2·3은 S-E2E 학습 중, 안 씀). 동시 Isaac 프로세스 최대 3개. 모든 Isaac 실행에 `OMP_WAIT_POLICY=PASSIVE`(비교하는 두 실행은 항상 같은 설정). 예외: 폐루프 작업자는 `eval/closed.py`의 `worker_cmd`가 환경 변수를 고정해 넘기므로 이 설정이 빠졌다(이번 범위 밖 파일이라 안 고침).
- 코드 사본은 파드 `/data/harvest/tmp/hardreset/`(수정 전 `code_red`, 수정 뒤 `code_fix2`)에서 돌렸고, 끝난 뒤 스크래치·kit 캐시(`ir/kitcache/cyclo-hardreset_*`)·pyc를 지웠다. 풀(`/data/harvest/data/pool/*`)은 읽기만 했다. 시드: DEV 0–1·3·5·8·11·17·19·26, POOL 2027·2073(스크래치 폴더에 새로 생성). CAL/TEST 없음, 유료 API 없음. 커밋 안 함.
- 원자료(로그·matrix.json·labtest.jsonl): 로컬 `D:\tools\scratch_qdd\hardreset\pod_out\`, 실행 스크립트 `D:\tools\scratch_qdd\hardreset\`(`run.sh`·`lanes.sh`·`timing.py`·`frames_check.py`·`lab_test.py`).

## 요약

| 질문 | 답 |
|---|---|
| 무엇을 바꿨나 | `harvest/sim/scene.py` `Env.reset()`이 매번 먼저 `_recreate_physx_scene()`을 부른다: 타임라인 stop → 물체 5개(o3·o5·o8·o9·o10)의 USD 자세를 **이번 시드의 리셋 자세**로 쓰기 → `sim.reset(soft=False)`(play). 카메라는 재초기화하지 않고 그대로 둔다. `_sim_step_counter = 0`. `make_env(..., hard_reset=True)`가 기본, `False`면 예전 소프트 리셋. |
| 결정성 | **수정 뒤 DEV 4시드 × 이력 3가지 × {카메라 없음, 카메라 2대} = 24/24 비트 동일**(매 틱 로봇 q·qd 전 관절, 물체 5개 자세·속도, 에피소드 전체, 새 프로세스 기준). 수정 전은 1/1 불일치(DEV 3, 첫 틱부터). 카메라 켬/끔끼리도 4/4 비트 동일. |
| 비용 | 리셋 1회당 **벽시계 +0.28 s, CPU +0.26 s**(카메라 없음, 8쌍 평균) / **+0.26 s, +0.31 CPU-s**(카메라 2대, 4쌍). `sim.reset(soft=False)` 호출 자체는 0.15–0.6 s(중앙 ≈ 0.25 s). 에피소드 전체(≈ 6 s 벽, 12 CPU-s)에서는 잡음(±1 s)보다 작다. 메모리·렌더 프로덕트 증가 없음(RSS 4.4–4.6 GB 일정, 렌더 프로덕트 3개 그대로). |
| 누가 받나 | `Env.reset()`을 거치는 모두: 풀 생성(`cli_pool`), R2 생성·재생(`datagen/gen.py`), 라벨러(`sim/labeler.py` 재실행), 폐루프 작업자(`runtime/aiworker.py` `reset()` → `e.reset()`), `sim/run_dev.py`, `m4b/fidev.py`, 선행 실행(`canonical_prefix`·`warmup`). 호출부는 하나도 안 고쳤다. |
| 확인한 호출부 | R2 DEV 6편 생성 → 구조 검사 6/6 유효, 새 프로세스 재생(`replay`, 사슬 없이) 2/2 **편차 0.0**. 모의 폐루프 1편(C5, DEV 0) 성공 16.1 s. 라벨러: 새로 만든 POOL 2027·2073의 스냅샷 6개 × 롤아웃 132개 **전부 첫 시도에 `replay_maxabs = 0`**. |
| 주의 | **지금 풀(옛 소프트 리셋으로 녹화)은 새 물리로 재현되지 않는다**(2027 5.3 mm, 2073 29.2 mm, 첫 스냅샷부터). 새 코드로 기존 풀을 다시 라벨하면 롤아웃마다 16회 재시도 뒤 어긋난 상태에서 분기한다. 풀과 라벨을 함께 다시 만들거나, 기존 풀 재라벨에는 `make_env(..., hard_reset=False)`가 필요하다(`cli_label`에 옵션은 아직 없음). |

## 1. 변경

`harvest/sim/scene.py`만 바꿨다(나머지는 새 파일).

- `Env._recreate_physx_scene()` (`reset()` 맨 앞, `hard_reset`이 참일 때):
  1. 카메라 센서의 STOP/PLAY 콜백을 잠시 무동작으로 가린다. Isaac Lab `Camera`는 PLAY 때마다 `rep.create.render_product`를 새로 만들고 옛 것을 지우지 않아(`_sensor_prims`도 계속 늘어남) 에피소드마다 렌더 프로덕트가 쌓인다. 카메라는 PhysX 핸들이 없고(`XFormPrim`은 자기 PHYSICS_READY 콜백으로 백엔드를 갱신), 가려도 영상이 정상임을 3절에서 확인했다. 관절체·물체·접촉 센서는 PLAY 때 Isaac Lab이 PhysX 뷰를 새로 만든다(같은 파이썬 객체라 `env.robot`·`env.objects`·`env.contact` 참조는 그대로 유효).
  2. `sim._disable_app_control_on_stop_handle = True`로 두고 `sim.stop()`. Isaac Lab은 이 깃발이 없으면 STOP 이벤트 안에서 PLAY를 기다리며 렌더만 돈다.
  3. 멈춘 동안 물체 5개의 USD 자세를 `_object_reset_pose(k, self.layout)`(리셋 이벤트가 쓰는 값 = `make_env(seed)`가 처음에 쓰는 값)로 쓴다(`_author_usd_pose`).
  4. `sim.reset(soft=False)` → PLAY, PhysX 장면 재생성, Isaac Lab의 렌더 2회.
  5. `env._sim_step_counter = 0`: 렌더 주기(`render_interval`) 위상을 에피소드 시작부터 센다. 폐루프 작업자(`aiworker.step`)는 이 카운터로 새 프레임 여부를 정하는데, 전에는 앞 에피소드 길이에 따라 위상이 달랐다.
- 3단계(USD 자세)가 필요한 이유(실측): 처음에는 `sim.reset(soft=False)`만 넣었다. 그러면 같은 프로세스 안의 이력은 모두 비트 동일해졌지만 **DEV 11만 새 프로세스와 달랐다**(첫 틱부터, 머그 10 mm). 이력 프로세스는 `make_env(5)`로 만들어져 USD에 o8이 탁상 위에 있었고, DEV 11은 o8을 치워 둔다. 새 PhysX 장면은 USD 자세로 만들어진 뒤 리셋 이벤트가 옮기므로 "처음 어디서 만들어졌나"가 궤적을 바꿨다. 이 시드의 자세를 먼저 쓰자 4/4 일치(2절). randomize의 `rd_*` 방해물은 USD에서 항상 같은 주차 자세라 따로 쓰지 않는다.
- `make_env(..., hard_reset=True)` / `Env(..., hard_reset=True)`: `False`면 예전 동작(옛 녹화 재생용).
- 새 도구 `harvest/sim/determinism.py`(`python -m harvest.sim.determinism fresh|history|compare`): 리셋의 안정화 스텝을 포함해 `env.step`마다 상태를 기록하고, 새 프로세스의 궤적과 비교한다. 시드는 DEV 0–29만 받는다.

## 2. 증거 — 비트 동일 행렬

`fresh` = 새 프로세스에서 `make_env(S)` → S 한 편. `history` = 한 프로세스(`make_env(5)`, 카메라 판은 `make_env(8)`)에서 시드마다 [DEV 5(카메라 판 8) 완주 → **S**(after_full)] [DEV 8을 스냅샷 k8(2.64 s, 쥐기 전)에서 중단 → **S**(after_partial)] [**S** 한 번 더(twice)]. 각 S를 `fresh`와 틱 단위로 비교했다(기록 208–234틱 = 안정화 20틱 + 에피소드, P0).

| 코드 | 카메라 | 시드 | after_full | after_partial | twice |
|---|---|---|---|---|---|
| 수정 전(`code_red`) | 없음 | 3 | ✗ 첫 틱부터, 209 vs 208틱, 머그 13 mm | ✗ 같음 | ✗ 같음 |
| `sim.reset`만(중간 판) | 없음 | 3·19·26 | ✓ | ✓ | ✓ |
| `sim.reset`만(중간 판) | 없음 | 11 | ✗ 첫 틱부터(머그 10 mm) | ✗ | ✗ |
| **최종**(`code_fix2`) | 없음 | 3·11·19·26 | **✓ 4/4** | **✓ 4/4** | **✓ 4/4** |
| **최종** | head + 오른손목 | 3·11·19·26 | **✓ 4/4** | **✓ 4/4** | **✓ 4/4** |

- ✓ = 전 틱에서 로봇 전 관절 q·qd, 물체 5개 자세(위치+쿼터니언)·속도가 float32 비트 동일, 길이 동일. 최종 판 24칸 전부 최대 차이 0.0.
- 최종 판 `fresh` 카메라 판과 카메라 없는 판도 4시드 모두 비트 동일(렌더가 물리에 영향 없음).
- 파드 pytest(Isaac 파이썬): `tests/sim/test_determinism_isaac.py`(한 프로세스, DEV 3 k10까지 → DEV 17 k14까지 → DEV 3 → DEV 3)가 수정 전 코드에서 **실패**(첫 틱부터, 94틱), 수정 뒤 **통과**.
- 수정 전 1행: 이력 셋이 서로는 같은 궤적(208 대 209틱)이었고 새 프로세스만 달랐다 — pool_replay_debug.md의 "첫 실행 효과"와 같은 모습.

## 3. 카메라·렌더

- 렌더 프로덕트 수: 카메라 2대 프로세스에서 하드 리셋 8번 뒤에도 3개 그대로(가리지 않으면 Isaac Lab `Camera._initialize_impl` 소스상 리셋마다 카메라 수만큼 늘어난다 — 가리지 않은 판은 돌리지 않았다). RSS 13.0 GB 일정.
- 프레임(`frames_check.py`, DEV 3, 한 프로세스): 옛 소프트 리셋의 첫 실행(make_env가 만든 장면 그대로) → 하드 리셋 두 번. **물리 상태는 세 번 모두 전 스냅샷(26개) 비트 동일**(= 새 장면은 make_env 직후 장면과 같다). 영상은 비트 동일이 아니다: 스냅샷마다 평균 |픽셀 차| 최대 1.19(head)·1.24(손목) / 255이고, **하드 리셋 두 번끼리도**(상태 동일) 다르다 → 렌더러 자체의 비결정성(RTX 시간 누적·잡음 제거로 추정, 확인 안 함)이지 카메라 오작동이 아니다. 눈으로 본 비교(k0·8·16·24, 소프트 첫 실행 | 하드 리셋): `physx_hard_reset_frames.jpg` — 두 카메라 모두 로봇을 따라가고 같은 장면이다.
- R2 생성 프레임(`gen sheet`, DEV 1, 과제 3개 × k0/lift/open, head·손목): 노출·카메라 위치 정상(로컬 `pod_out/out/r2_sheet.jpg`).

## 4. 비용 (리셋 1회당)

`timing.py`: 한 프로세스에서 DEV 3 P0 에피소드를 하드/소프트 번갈아(카메라 없음 8쌍, 카메라 2대 4쌍). "리셋" = `Env.reset()` 전체(안정화 1 s 포함).

| | 리셋 벽시계 하드 / 소프트 | 리셋 CPU-s 하드 / 소프트 | 에피소드 벽시계 하드 / 소프트 | 에피소드 CPU-s 하드 / 소프트 |
|---|---|---|---|---|
| 카메라 없음 | 0.83 / 0.56 (**+0.28**) | 1.48 / 1.21 (**+0.26**) | 5.95 / 6.02 | 11.80 / 11.73 |
| 카메라 2대 | 1.39 / 1.13 (**+0.26**) | 3.46 / 3.15 (**+0.31**) | 12.07 / 12.05 | 31.3 / 29.9 |

- 파드는 다른 작업(S-E2E 학습, cgroup 32코어 쿼터에서 스로틀)과 함께라 에피소드 단위 차는 잡음(±1 s) 안이다. CPU를 더 태우는 스레드가 생기지는 않았다(리셋 CPU 증가 ≈ 리셋 벽시계 증가).
- 호출부별 추가: 풀 생성 편당 리셋 2회(prefix + 에피소드) ≈ +0.6 s, R2 생성 편당 2–3회 ≈ +0.6–0.9 s(편당 ≈ 17 s), 라벨러 롤아웃당 2회(prefix + 재실행) ≈ +0.6 s(롤아웃당 ≈ 10–12 s 실측), 폐루프 에피소드당 1회.
- 더 줄일 수 있는 곳(안 함, 호출부 변경): 하드 리셋 뒤에는 `canonical_prefix`·`warmup`·gen의 `prefix`가 결과에 아무 영향이 없다(이력이 지워지므로). 없애면 R2 편당 ≈ 2.5 s(r2_datagen.md 실측 prefix), 라벨러 롤아웃당 prefix 한 편이 줄어 하드 리셋 비용보다 크게 절약된다. 단 결과가 같다는 것은 이번 행렬이 보인 것(이력 무관)에서 나오는 추론이고, prefix를 뺀 판을 따로 돌려 보지는 않았다.

## 5. 호출부 확인

| 확인 | 명령(파드, 코드 사본) | 결과 |
|---|---|---|
| R2 DEV 구조 검사 | `gen gen --variant standard --tasks all --kinds P0 --seeds 0-1` → `gen check` | 6편 성공 6·유효 6, 프레임 1,824, 행 1,818 |
| R2 재생(새 프로세스, 사슬 없음) | `gen replay --task mug_tray --seed 1`, `--task bottle_tray --seed 0` | **첫 어긋난 프레임 없음, 물체·관절 최대 오차 0.0** (전에는 재생 정확도가 앞 이력에 달려 `--chain`·과제별 prefix가 필요했다, r2_datagen.md·`gen.prefix` 설명) |
| 모의 폐루프 | `python -m harvest.eval.closed --model mock --seeds 0 --conditions C5 --isaac-gpu 1 --astra mock` | C5/standard 1/1 성공(16.12 s), 호출 48·오류 0, RTF 0.46, 작업자 197 s |
| 라벨러 | `cli_pool pool --seeds 2027,2073 --confirm-pool --out <스크래치>`(새 코드로 녹화) → 다른 프로세스에서 `cli_label.label_pool`과 같은 절차(make_env → warmup → `Labeler` → `label_snapshot`)로 결정 스냅샷 3개씩 | 2027 k6(descend)·k16(carry)·k25(open), 2073(P1) k1(approach)·k11(lift)·k23(place_descend): 롤아웃 24·20·25·21·20·22 = **132개 전부 `replay_attempts = 1`, `replay_maxabs = 0.0`**. 스냅샷당 200–315 s |
| 기존 풀과의 관계 | 같은 프로세스에서 기존 풀 녹화(`data/pool/ep2027`, `ep2073`, 읽기만)와 하드 리셋 재실행 비교 | 2027: k0부터 다름, 최대 5.32 mm / 2073: k0부터, 29.22 mm → 옛 녹화는 새 물리로 재현 불가 |

- 라벨러의 비트 동일 확인·재시도(`REPLAY_HISTORIES`)는 그대로 두었다(안전망). 하드 리셋 뒤에는 재시도도 같은 결과를 내므로, 어긋나면 16회를 다 쓰고 어긋난 상태로 분기한다 — 새 풀에서는 일어나지 않았고(132/132 첫 시도), 옛 풀에 돌리면 항상 일어난다.
- E0.5(`eval/e05.py`)는 시뮬레이터를 쓰지 않는다(`make_env` 호출 없음) → 해당 없음.

## 6. 테스트

- 로컬 `tests/sim/test_hard_reset.py`(Isaac 없음, 8개): 비교 함수 3개(동일 / 틱 7의 1 ulp 차 / 길이 차), 리셋 동작 5개 — 에피소드 리셋 전에 매번 `sim.reset(soft=False)`, 물리 자산은 매번 재초기화되지만 카메라 렌더 프로덕트는 늘지 않고 클래스 콜백이 복구됨, STOP과 PLAY 사이에 이번 시드 자세를 쓰고 앱 제어 깃발을 켰다 끔, 렌더 카운터 0, `hard_reset=False`면 예전 동작. 먼저 실패(3개, 이어서 USD 자세 1개)를 보고 구현했다.
- 파드 `tests/sim/test_determinism_isaac.py`(`pytest.importorskip("isaaclab")`, 로컬에서는 건너뜀): 수정 전 실패 → 수정 뒤 통과(2절).
- 로컬 전체 `cd D:/qdd && python -m pytest`: **906 통과, 13 건너뜀, 실패 0**(다른 작업자의 진행 중 파일 포함한 작업 트리).

## 7. 다루지 않은 것

1. **기존 POOL 120편과 그 라벨**: 새 물리로 재현되지 않는다(5절). pool_replay_debug.md 6절의 "29편 재라벨"을 새 코드로 하면 안 된다(16회 재시도 뒤 어긋난 분기). 선택지: (가) 풀과 라벨을 새 코드로 함께 다시 만든다(권장, 재시도·prefix가 필요 없어짐) — 풀 경로가 바뀌므로 사용자/정본 결정 필요, (나) 옛 풀 재라벨은 `hard_reset=False`로 — `cli_label`에 옵션이 없어 한 줄 추가가 필요하다(이번엔 안 함).
2. 이미 만든 R2 DEV/학습 데이터, E0.5 스냅샷 등 옛 소프트 리셋으로 녹화된 것도 새 코드에서 같은 궤적이 나오지 않는다(재생·비교 시 `hard_reset=False` 또는 재생성).
3. 변형 `dr`/`random`, CUDA PhysX(`sim_device="cuda"`), 섭동 P2의 결정성 행렬은 돌리지 않았다(standard P0 + 라벨러의 P1 1편만). `dr`/`random`의 방해물은 USD 주차 자세가 시드와 무관해 같은 원리로 맞을 것으로 보지만 확인 안 함.
4. 렌더 영상은 같은 물리 상태에서도 비트 동일이 아니다(평균 ≈ 1/255, 3절). 원인(RTX 시간 누적 등)은 조사 안 함. 기존에도 그랬는지는 비교 자료가 없다.
5. prefix·warmup 제거(4절)와 라벨러 재시도 목록 축소는 호출부 변경이라 안 했다.
6. 폐루프 작업자에 `OMP_WAIT_POLICY=PASSIVE`가 전달되지 않는다(`eval/closed.py` `worker_cmd`, 이번 범위 밖).

## 8. 파일

- 수정: `harvest/sim/scene.py`
- 새: `harvest/sim/determinism.py`, `tests/sim/test_hard_reset.py`, `tests/sim/test_determinism_isaac.py`, `docs/stage3/results/physx_hard_reset_frames.jpg`, 이 문서
