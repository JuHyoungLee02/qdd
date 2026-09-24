# Task 10 — Inspect Robots P0 결과 (DC3)

- 실행 시각: 2026-09-24 08:33–08:42 UTC (파드 `date -u` 기준)
- 파드: `p-test2/juhyoung-native-7a2a` (노드 h200-03-w-7a2a). **GPU 0만 사용**(`CUDA_VISIBLE_DEVICES=0`). Isaac 로그의 GPU 표에서 Active는 0번뿐이었다.
- 작업 폴더: 파드 `/data/juhyoung_qdd/ir/`. 로그는 `logs/`, RTF 산출물은 `rtf/`에 있다. 스크립트 사본은 로컬 `D:\tools\scratch_qdd\ir\`에 있다.
- Step 7(agent + Astra)은 지시대로 **건너뛰었다**(비용 절감, 나중에 실행).

## 요약

| Step | 내용 | 결과 |
|---|---|---|
| 1 | chroot 진입 방식 확인 | 확인함. native 방식(unshare -m + bind + chroot) 사용 |
| 2 | 소스 고정 설치 | **통과**. HEAD `7e506e3b6f39530f18e75cf97b23c4287aa90f12` = 태그 `v0.59.0`. editable 설치, Isaac 패키지 판본 변동 없음 |
| 3 | `inspect-robots doctor` | 명령은 정상 실행됨. `cubepick`은 적합, `isaacsim`은 부적합 3건(D23 예측과 같음) |
| 4 | smoke_async 3모드 | **통과**. sync/simlat/wall 모두 status=success, 16/16. 하네스 오버헤드 **57–59 µs/step** |
| 5 | boot_proof | **통과**(Isaac Lab 2.3.0 rootfs). `BOOT PROOF: SUCCESS`, 32.9 s. Isaac Lab이 없는 순수 isaac-sim rootfs에서는 실패함(예상대로) |
| 6 | RTF (Franka Lift, 60 s) | 카메라 켬 **RTF 1.13**, 카메라 끔 **RTF 2.32** |
| 7 | agent + Astra | 건너뜀 |
| 8 | DC3 관문 | **충족**(Step 4·5 통과). 태그와 커밋은 메인 세션이 한다 |

## Step 1 — 진입 방식

`/data/juhyoung_infra/HANDOFF.md` §3의 원래 방식은 `bin/isaacshell`(proot)이다. bwrap은 AppArmor 때문에 쓸 수 없다고 적혀 있다.

그런데 proot는 추적자 스레드가 하나뿐이라 RTX 카메라 부하에서 멈춘다. 그래서 이 파드는 SYS_ADMIN 권한과 AppArmor unconfined(`/proc/self/attr/current` = `unconfined`, uid root)로 다시 만들어졌고, `/data/juhyoung_pi05/native_run.sh`(V4-250)의 native 방식을 쓴다. 이번에도 그 방식을 그대로 가져왔다.

- `unshare -m`으로 전용 마운트 네임스페이스를 만든다.
- 그 안에서 `/dev /proc /sys /data`, `nvidia_libs → /nvidia-driver`, `nvidia-smi`, vulkan ICD, `nvoptix.bin`, `resolv.conf`를 rootfs에 bind한다.
- kit의 `cache/data/logs`는 인스턴스별 디렉터리로 bind한다.
- 마지막으로 `chroot $R env -i … "$@"`로 실행한다.

사본은 `/data/juhyoung_qdd/ir/ir_run.sh`이다. 원본과 다른 점은 셋이다.
- rootfs를 고를 수 있다: `IR_ROOT=isaac`는 `/data/juhyoung_infra/isaac-sim-5.1.0-rootfs`, `IR_ROOT=cyclo`는 `/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0`이다.
- cyclo를 고르면 `/data/newproj/rep_v3test`를 `/workspace/cyclo_lab`에 **읽기 전용**으로 bind한다.
- kit 캐시는 `/data/juhyoung_qdd/ir/kitcache/<root>-<inst>`에 둔다.
- `CUDA_VISIBLE_DEVICES`를 주지 않으면 0으로 고정한다.

```bash
cd /data/juhyoung_qdd/ir; . ./env.sh            # PYTHONPATH 설정
IR_ROOT=cyclo IR_INST=boot ./ir_run.sh /isaac-sim/python.sh <script.py>
```

## Step 2 — 설치

```bash
git clone https://github.com/robocurve/inspect-robots /data/juhyoung_qdd/ir/src
cd src && git checkout 7e506e3 && git rev-parse HEAD   # 7e506e3b6f39530f18e75cf97b23c4287aa90f12
git tag --points-at HEAD                                # v0.59.0
./ir_run.sh bash -c "cd /data/juhyoung_qdd/ir/src && /isaac-sim/python.sh -m pip install --no-deps \
  --target /data/juhyoung_qdd/ir/pylib -e . -e plugins/inspect-robots-agent -e plugins/inspect-robots-isaacsim"
# 순수 isaac rootfs에 httpx가 없어 agent import가 실패함 -> cyclo rootfs와 같은 판본을 pylib에 넣음
./ir_run.sh /isaac-sim/python.sh -m pip install --no-deps --target /data/juhyoung_qdd/ir/pylib httpx==0.28.1 httpcore==1.0.9
```

- 설치 판본: inspect-robots 0.59.0, inspect-robots-agent 0.27.0, inspect-robots-isaacsim 0.1.1. 모두 editable이다.
- `--no-deps`를 쓴 이유: 의존성을 함께 받으면 numpy 등이 pylib에 들어가 Isaac 판본을 가린다. 설치 후 numpy는 Isaac prebundle의 1.26.0이 그대로 로드됐다.
- **주의:** `--target` 설치에서는 editable `.pth` 파일이 처리되지 않는다(PYTHONPATH 디렉터리이기 때문). 그래서 `env.sh`의 PYTHONPATH에 소스 경로를 직접 넣는다. 엔트리포인트 등록은 pylib의 dist-info가 맡는다.
  ```
  PYTHONPATH=/data/juhyoung_qdd/ir/pylib:/data/juhyoung_qdd/ir/src/src:/data/juhyoung_qdd/ir/src/plugins/inspect-robots-agent/src:/data/juhyoung_qdd/ir/src/plugins/inspect-robots-isaacsim/src
  ```
- `pip list` 전후 비교(`logs/piplist_{isaac,cyclo}_{before,after}.txt`):
  - isaac rootfs: 추가 5개(httpcore 1.0.9, httpx 0.28.1, inspect-robots 3종). 모두 pylib에 있다.
  - cyclo rootfs: 추가 3개(inspect-robots 3종).
  - **기존 패키지의 판본 변화: 0건.** rootfs의 site-packages는 건드리지 않았다.
- import 확인: 두 rootfs 모두 `inspect_robots`, `inspect_robots_agent`, `inspect_robots_isaacsim`이 import된다. Python 3.11.13.

## Step 3 — doctor (전체 출력: `logs/step3_doctor.txt`)

두 rootfs의 결과가 같다.

```
inspect-robots list
  embodiments: cubepick, isaacsim | policies: agent, noop, random, scripted | tasks: cubepick-reach
  graders: operator, vlm | scorers: episode_length, min_distance_to_goal, operator, reached_goal_state, success_at_end
  sinks: json, live-json, rerun
inspect-robots doctor --embodiment cubepick   -> cubepick: conformant (no issues)   exit 0
inspect-robots doctor --embodiment isaacsim   -> isaacsim: 3 issue(s)               exit 1
  [error] bounds: action space needs finite low/high bounds; ...
  [error] dim_labels: action dims are unlabeled; ...
  [error] state_alignment: absolute-target control needs exactly one StateSpec field with shape (8,) ...; found none
```

→ D23 §3의 "기본 isaacsim 플러그인은 그대로 못 쓴다"를 실측으로 확인했다. P1의 `aiworker` 몸체가 이 세 가지를 채워야 한다.

## Step 4 — 스모크 (`logs/step4_smoke.txt`, `logs/step4_overhead.txt`)

- `D:\tools\audit_d23\smoke\smoke_async.py`를 파드로 옮겼다. 바꾼 것은 `log_dir` 경로 하나뿐이다(`/data/juhyoung_qdd/ir/smoke/logs`).
- 실행: `./ir_run.sh /isaac-sim/python.sh smoke_async.py {sync|simlat|wall}` (isaac rootfs)

```
== clock=sync   status=success wall=4.1s max_steps=500 metrics={'priv_success': 1.0}
== clock=simlat status=success wall=6.0s max_steps=500 metrics={'priv_success': 1.0}
== clock=wall   status=success wall=4.8s max_steps=500 metrics={'priv_success': 1.0}
```

- 세 모드 모두 4장면 × 2 epoch = 8/8 성공.
- 짝 장면 시드도 같다: std-L3와 rnd-L3가 모두 (3720929858, 2865746644)이고, L7은 (3670100638, 2915465736)이다. D23 로컬 결과와 같다.
- 성공 시점(시뮬 시각): sync 0.15–0.34 s, simlat 0.57–0.96 s, wall 0.40–0.94 s.
- 대기 시간: sync는 0.21–1.04 s를 막혔고(세계가 멈춤), wall은 0 s였다.
- 하네스 오버헤드(`overhead.py`, 20000 스텝, 가드레일과 행동 로그 포함, 3회): **57 / 58 / 59 µs/step**. 로컬 노트북에서는 약 80 µs였다.

## Step 5 — boot_proof

| rootfs | Isaac Lab | 결과 |
|---|---|---|
| `isaac-sim-5.1.0-rootfs` (Isaac Sim 5.1.0-rc.19) | **없음** | 실패: `RuntimeError: Isaac Sim / Isaac Lab is not importable ... (No module named 'isaaclab')` (`logs/step5_boot_isaac.txt`) |
| `rootfs/cyclo-lab-2.0.0` (Isaac Sim 5.1.0-rc.19, 같은 빌드) | **Isaac Lab 2.3.0** (`third_party/IsaacLab/VERSION`; isaaclab 0.47.2, isaaclab_tasks 0.11.6) | **통과** (`logs/step5_boot_cyclo.txt`) |

```
[adapter] name=isaacsim action_dim=8 sim=True caps=['privileged_success', 'renderable', 'resettable', 'seedable']
[INFO][AppLauncher]: Using device: cuda:0
[boot] SimulationApp live in 32.9s  is_running=True  app=SimulationApp
[boot] app.update() x3 OK
BOOT PROOF: SUCCESS  (SimulationApp started + stepped on GPU in 32.9s)
```

- 로그의 `[Error]`는 0건이다. Vulkan GPU 표에 4장이 보이지만 Active는 0번뿐이다.
- 나머지 GPU에 대한 "Skipping NVIDIA GPU due CUDA being in bad state" 경고는 `CUDA_VISIBLE_DEVICES=0`으로 제한했기 때문에 나오는 것이다.
- **Isaac Lab 상태:** 별도 설치는 필요 없었다. cyclo_lab 2.0.0 rootfs에 Isaac Lab 2.3.0이 editable로 들어 있다(`/workspace/cyclo_lab/third_party/IsaacLab`, 저장소 bind 필요). **D23의 [미확인] "Isaac Lab 2.3 / Sim 5.1 호환"은 부팅, 과제 생성, 스텝, 카메라 렌더까지 해소됐다.**
- 순수 isaac-sim 5.1.0 rootfs에는 Isaac Lab이 없다. 앞으로 IR은 **cyclo rootfs(`IR_ROOT=cyclo`)에서 돌린다.**

## Step 6 — RTF (`/data/juhyoung_qdd/ir/rtf_lift.py`, `rtf/rtf_{cam,nocam}.json`)

**측정 조건**
- 과제는 `Isaac-Lift-Cube-Franka-v0`이고, 기본 `IsaacSimEmbodiment` 어댑터를 거쳐 `inspect_robots.eval()`로 돌렸다.
- step_dt는 0.02 s이다(sim.dt 0.01 × decimation 2). 3000 스텝 = 시뮬 60 s.
- 정책은 hold(행동 0 = 기본 자세 유지, 그리퍼 열림)이다.
- 기본 에피소드 길이 5 s를 70 s로 늘려 한 에피소드로 이어지게 했다.
- **카메라 조건:** 기본 Lift 과제에는 카메라가 없다. 그래서 `AppLauncher(enable_cameras=True)`로 띄우고, 224×224 `TiledCamera` 1대(`base_rgb`, 로봇 앞 1.5 m, 높이 0.7 m, 30° 내려다봄)를 장면과 policy 관측군에 추가했다.
- 벽시계 시간은 첫 `act()`부터 롤아웃 끝까지 쟀다. 부팅과 환경 생성 시간은 뺐다.

| 조건 | 스텝 | 시뮬 시간 | 벽시계 | **RTF** | ms/step | 부팅 | 환경 생성 | 이미지 |
|---|---|---|---|---|---|---|---|---|
| 카메라 켬 (224², 1대) | 3000 | 60.0 s | 52.9 s | **1.13** | 17.6 | 58.7 s | 15.4 s | (224,224,3) |
| 카메라 끔 | 3000 | 60.0 s | 25.9 s | **2.32** | 8.6 | 11.9 s | 5.1 s | — |

- 두 실행 모두 status=success, `[Error]` 0건이다.
- 카메라 실행의 CPU 사용 시간은 user 16 min / real 2.2 min이다. RTX 렌더가 여러 코어를 쓴다.
- **프레임 검증:** 50번째 스텝 프레임을 `docs/stage3/results/p0_ir_lift_cam_frame.png`에 저장했다. Franka, 테이블, 큐브가 정상 렌더됐다. RT 코어가 없는 H200에서도 RTX 렌더가 된다.
- **해석:**
  - 카메라 1대, 224²에서 RTF가 1을 겨우 넘는다(1.13).
  - ZED_M 좌우 2대 + 손목 카메라에 VGA 해상도를 쓰고, D23 권고대로 decimation 1(100 Hz)로 바꾸면 RTF < 1이 될 가능성이 크다(추정, 미측정).
  - 따라서 **wall 모드를 시뮬에 쓰는 것은 부적합하다.** D23 권고대로 simlat을 주 트랙으로 하고, RTF를 로그에 남겨야 한다.

## 막힌 점 / 주의

1. **순수 Isaac Sim 5.1.0 rootfs에는 Isaac Lab이 없다.** isaacsim 플러그인(`AppLauncher`, `isaaclab_tasks`)을 쓰려면 cyclo-lab-2.0.0 rootfs와 cyclo_lab 저장소 bind가 필요하다. 새로 설치하지 않고 이것으로 해결했다.
2. `pip --target` + editable은 `.pth`가 처리되지 않는다. PYTHONPATH에 소스 경로를 직접 넣어야 한다(`env.sh`).
3. 기본 isaacsim 어댑터는 doctor 부적합 3건(bounds, dim_labels, state_alignment)이 있어 agent·capx에 그대로 붙일 수 없다. P1에서 자체 몸체가 필요하다(D23 §3과 같음).
4. HANDOFF.md는 proot 기준(08-15)으로 쓰여 있고, native 방식은 `native_run.sh` 주석에만 기록돼 있다.

## DC3 판정

**충족.** 근거는 셋이다.
- Step 4: 3모드 스모크 통과, 오버헤드 수십 µs/step.
- Step 5: Isaac Lab 2.3.0 + Isaac Sim 5.1.0 chroot에서 boot_proof 통과.
- RTF 기록: 카메라 켬 1.13, 카메라 끔 2.32.

태그 `stage3-dc3`와 커밋은 메인 세션이 한다.
