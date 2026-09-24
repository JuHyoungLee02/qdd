# Task 11 — 시뮬 장면 기동 결과 (AI Worker 한 팔 + 머그/트레이)

## v2 (challenge-env config) — 2026-09-24 11:05–12:45 UTC

사용자 지시(2026-09-24, 원문): "우손목캠 있음 https://github.com/kairobahq/humanoid-challenge-env 여기에 있는 로봇 설정 그대로 가져와서 복사해서 써보자". 로봇·카메라 설정을 그 저장소에서 **바이트 그대로 복사**해 쓴다. 아래 v1 절은 이전 장면 기록으로 그대로 둔다.

- 원본: `kairobahq/humanoid-challenge-env` 커밋 `523ea8e8ebcd80a607e8b41aaeadc345fdfa5792`(파드 클론 `/data/harvest/src/humanoid-challenge-env`, Apache-2.0)
- 복사본: `third_party/humanoid_challenge_env/`(`LICENSE`, `scripts/FFW_SG2_REAL_cameras.py`, `scripts/taskC/taskC_ffw_sg2.py`, `NOTICE.md` = 출처·커밋·sha256). 파일은 한 글자도 고치지 않았다(`tests/sim/test_challenge_cameras.py`가 sha256을 다시 잰다).
- 로봇 USD: 공식 `ROBOTIS-GIT/cyclo_lab` **`42dcd8256651`**(카메라 파일이 "CL"로 고정한 커밋). 파드에 git worktree `/data/harvest/cyclo_lab_42dcd82`를 추가했고 `scene.CYCLO_LAB_SRC`가 거기를 본다. `FFW_SG2.usd`(blob `08a5bd5`)·`assets/robots/FFW_SG2.py`(blob `004ee05`)는 `42dcd82`와 v1의 `f4c0470`에서 같다(확인).
- 코드: `harvest/sim/scene.py`(두 파일을 경로로 import), `harvest/sim/planner.py`, `harvest/sim/run_dev.py`. 산출물(파드) `/data/harvest/out/t11_12_v2/`.

### 무엇을 복사했나 — 로봇

저장소에 들어 있는 로봇 설정 파일은 `scripts/taskC/taskC_ffw_sg2.py` 하나다(과제 A·B 스크립트는 도커 이미지 안 cyclo_lab의 `FFW_SG2_MOBILE_CFG`를 import하는데, 그 파일은 저장소에 없다). 카메라 파일은 로봇을 "`FFW_SG2_MOBILE_CFG` — USD, gains, swerve, masses, joint limits untouched"라고 적는다. 그래서 **`taskC_ffw_sg2.FFW_SG2_MOBILE_CFG`를 그대로** 쓴다.

| 항목 | 복사한 값 (v1 = cyclo_lab `FFW_SG2_CFG`) |
|---|---|
| USD | cyclo_lab `robots/FFW/FFW_SG2.usd` (v1과 같은 파일) |
| 팔 PD | DY_80(관절 1–2) k 600 / d 30 / 61.4 N·m, DY_70(3–6) 600 / 20 / 31.7, DP-42(7) 200 / 3 / 5.1 (v1과 같음) |
| 그리퍼 | 오른손 주 관절 `gripper_r_joint1` k 100 / d 4 / 30 N·m, 왼손 k 300, 보조 관절 2–4 k 2 / d 0.5 / 20 N·m (**v1의 보조 관절 게인 변경을 없앴다**) |
| 리프트·머리 | lift k 10000 / d 100, head k 150 / d 3 |
| 중력 | **로봇 링크 중력 켬**(`disable_gravity=False`; v1은 끔) |
| 스폰 함수 `spawn_sg2_mobile` | 턱(jaw) 마찰 재질 정지 2.0 / 운동 1.8(`friction_combine_mode=max`), 콜라이더가 없던 링크 9개 콜라이더 복원(`arm_base_link, arm_l_link6, arm_r_link6, head_link1/2, 좌우 바퀴`, 로그로 확인), 몸통–바퀴·link7–턱·머리–몸통 충돌 필터, `head_joint1` 아래쪽 한계 45°, 바퀴 관절 한계 |
| 스워브 | `base_steer`(k 10000), `base_drive`(속도 제어) 액추에이터 — 베이스가 고정이라 움직이지 않음 |

**복사본과 다른 점은 하나: 베이스 고정**(`fix_root_link` False → True, 정본 §38). `scene._robot_cfg()`가 설정의 사본에만 적용한다(USD의 world FixedJoint를 다시 켬). 기동 때 `robot.is_fixed_base == True`를 확인하고 아니면 예외를 낸다. 실측: 루트 (0, 0, 0), 관절 31개.

과제 C 스크립트(`task_c_demo.py`/`task_c_replay.py`)는 import 뒤 스크립트 안에서 팔 강성 ×25(`TASKC_ARM_K_MUL`)·리프트 k 100000을 덧씌운다. 이것은 로봇 설정 파일이 아니라 과제 C 재생 스크립트의 보정이라 **복사하지 않았다**(설정 파일 값 그대로).

### 무엇을 복사했나 — 카메라 (`FFW_SG2_REAL_cameras.camera_cfg` 그대로, 깊이 annotator만 추가)

| 이름(데이터셋 키) | 실물 | 해상도 | fx = fy (px) | 화각 (수평 × 수직) | 붙는 곳 · 장착 변환 | clip | 녹화 |
|---|---|---|---|---|---|---|---|
| `cam_head` | ZED Mini 왼눈(rectified) | 672×376 | 367.0 (focal 11.444 / aperture 20.955) | 84.95° × 54.25° | `head_link2/cam_head`, 위치 (0.0238122, 0.0249820, −0.0109594) m, 회전 없음(world 규약: +X 앞, +Z 위) | 0.1–100 m | 예 |
| `cam_wrist_right` | RealSense D405 컬러 | 424×240 | 223.40 (focal 11.041) | 87.0° × 56.49° | `arm_r_link7/camera_r_bottom_screw_frame/camera_r_link/cam_wrist_right`, offset 0. link7 기준 [t, q] = (0.09824, 0.0, −0.07249), (0.47544, −0.47544, 0.52341, 0.52341) | 0.03–100 m | 예 |
| `cam_wrist_left` | RealSense D405 컬러 | 424×240 | 223.40 | 87.0° × 56.49° | `arm_l_link7/.../camera_l_link` — 오른쪽과 같은 수치(URDF가 거울 대칭이 아님) | 0.03–100 m | 아니오(장면에는 있음) |

- `scene.KNOWN_CAMERAS = DEFAULT_CAMERAS = ("cam_head", "cam_wrist_left", "cam_wrist_right")`, `RECORD_CAMERAS = ("cam_head", "cam_wrist_right")`. `make_env(cameras=...)`는 이 이름만 받는다.
- 깊이: `camera_cfg(name, data_types=["rgb", "distance_to_image_plane"])` — 렌더러 GT 깊이 annotator만 켠다. 카메라 prim·위치·화각은 복사본 그대로다(정본 §43의 "추가·교체·이동 없음"은 이 카메라 셋이 실물 기본 구성이므로 그대로 지켜진다. v1의 `cam_head`는 cyclo_lab 과제 설정의 카메라였고, 이번 것은 실기 사양에서 온 값이다).
- 실측 내부 행렬: 머리 [[367, 0, 336], [0, 367, 188]], 우손목 [[223.4, 0, 212], [0, 223.4, 120]] — 설정값과 같다.
- **주의(재발 방지)**: `camera.data.pos_w`/`quat_w_world`는 이 장면에서 USD에 적힌 초기 자세를 돌려준다(머리 (0.09, 0.025, 1.579)·회전 없음, 손목 (0.078, −0.2275, 0.718) — 팔 초기 자세를 바꿔도 같은 값). 그림은 링크를 따라간다(머리는 숙인 시야, 손목은 위에서 내려다본 시야). 외부 파라미터가 필요하면 링크 자세(`body_pos_w/quat_w`) × `mount_transform()`을 쓴다.
- 순수 함수 테스트(`tests/sim/test_challenge_cameras.py`, 함수 6개·7건): 복사본 sha256, 카메라 이름·기본값·녹화 셋, `_fx_from_hfov`(424 px, 87° → 223.40), 표의 해상도·fx·화각·clip, 머리 장착 변환, 손목 장착 변환을 URDF rpy (−π/2, 1.66678943569, 0)로 따로 계산한 값과 비교(위치 1e-9 m, 회전 행렬), 물리 장치 선택.

### 물리 장치 (정본 §48): 기본 CPU PhysX

`make_env(..., sim_device="cpu" | "cuda")`, 기본 `"cpu"`(렌더는 GPU 0 그대로). `run_dev --sim-device`로 고른다.

### 기동 결과 (시드 0, 리셋 1회 뒤 제자리 유지 100스텝 = 5 s)

| 항목 | CPU PhysX | GPU PhysX |
|---|---|---|
| RTF, 머리캠 + 우손목캠(RGB + GT 깊이) 켬 | **2.246** (5.0 s / 2.23 s); 세 카메라 모두 켬 1.878 | 0.595 (5.0 s / 8.41 s) |
| RTF, 카메라 끔(플래너 실행, P0 30판 단독 실행 중앙값) | **5.18** (4.87–5.36) | 0.20 (P0·P1·P2 세 프로세스 동시 실행 중앙값, 단독 값 아님; v1 단독 0.56–0.58) |
| 정착(마지막 10스텝 최대 속도) | 머그 0.004 mm/s, 트레이 0.009 mm/s → < 1 mm/s 통과 | 머그 0.006, 트레이 0.009 mm/s → 통과 |
| 스폰 → 정착 이동 / 바닥 높이 | 1.0 mm / 0.0 mm | |
| `make_env` | 21.3 s | 21.0 s |
| 리프트 | 목표 −0.0993 → 실측 −0.1254 (중력으로 26 mm 처짐: 리프트 위 약 26 kg, k 10000. 복사한 설정대로의 결과) | |
| `head_joint1` | 0.6916 (목표 0.69) | |
| 깊이 | 머리 유효 1.0, 0.25–5.75 m / 손목 유효 1.0, 0.069–1.28 m | |

- 프레임: `docs/stage3/results/scene_v2_seed0_head.png`(152 KB) — 탁상·트레이·머그, 오른쪽에 위에서 내려다보는 자세의 오른손(아래 "초기 자세" 참고), 화면 아래 왼손. `scene_v2_seed0_wrist.png`(39 KB) — 우손목캠이 위에서 탁상을 내려다보고 머그(왼쪽 아래)·트레이가 보이며 손가락이 화면 왼쪽 위아래에 걸린다(복사본 주석의 "fingers show on the LEFT of the image, one above the other"와 같은 모양).
- 공유 rootfs `/tmp` 항목 수: 첫 v2 실행 전 137,917 → 11:1x UTC 첫 기동 뒤 137,917(같음) → 12:23 UTC 137,923 → 12:45 UTC 137,929. 내 실행은 `ir_run.sh`가 `/tmp`를 `kitcache/<root>-<inst>/tmp`로 덮은 상태에서 돌았고, 늘어난 12개는 옆 파드(x2)의 다른 프로젝트 Isaac 실행분으로 메인이 확인했다(내 실행은 mountinfo상 `/tmp`가 kitcache로 덮여 있음).

### 초기 자세 변경 (장면 판정, 로봇 설정은 그대로)

v1의 오른팔 초기 자세(cyclo 기본 `arm_r_joint1 = 0.75, joint4 = −2.30`)에서는 v2 로봇으로 P0가 무너졌다(GPU PhysX: 수정 없이 시드 0–3 전부 approach_ik, 중력 보정 뒤에도 18/30). 원인을 단계별로 쟀다(시드 1, GPU PhysX, 접촉 센서는 진단용 실행에서만 켬).

| 실측 | 값 |
|---|---|
| 접근 중 오른팔 링크 접촉 | `arm_r_link1` ↔ `arm_r_link6` 134–201 N(t 1.05–1.35 s), 두 링크만 같은 크기 → **자기 충돌** |
| 그때 관절 | `arm_r_joint4` −2.93(팔꿈치를 끝까지 접음), 명령 대비 TCP가 위로 최대 30 cm 벗어남 |
| A/B (같은 시드) | 자기 충돌 끔 → 성공(접근 3.95 s), 켬 → 머그가 쓰러져 실패 |
| v1이 된 이유 | 스폰 함수가 `arm_r_link6`의 빠진 콜라이더를 복원했다. v1에는 link6 콜라이더가 없어 팔이 제 몸을 통과한 경로였다 |
| 관절 공간 "준비 자세" 이동(플래너 쪽 대안) | 목표 4곳 모두 손끝이 탁상 근처로 쓸고 지나감: 물체 구역(x > 0.30) 최저 손끝 높이 −12.8 / +6.8 / +60 / +61 mm(머그 95 mm) → 기각 |

→ **판정: 오른팔 초기 자세를 위에서 내려다보는 자세로 바꾼다** — TCP (0.34, −0.25, 탁상 + 0.25 m), yaw π/2, `INIT_R_ARM = (−1.0511, −1.0975, 1.2281, −2.3934, 0.4838, 1.2356, 1.80)`(플래너 IK로 구함, 1.8 mm; `arm_r_joint7`은 IK가 한계 1.820에 붙어 1.80으로 둠). 왼팔·머리·리프트는 v1 값. 로봇 설정은 건드리지 않는다. 대가: 첫 머리캠 프레임에서 오른손이 화면 오른쪽에 들어와 머그를 일부 가릴 수 있다(시드 0). 화면 밖 자세(TCP y −0.50)도 시험했으나 같은 조임(0.012)에서 P0 27/30(파지 실패 3)으로 이 자세(29/30)보다 나빴다.

## v1 (cyclo_lab `FFW_SG2_CFG` + cyclo 머리캠 `cam_head`) — 원래 기록

- 작업 시각: 2026-09-24 08:44–10:54 UTC (파드 `date -u`)
- 파드: `p-test2/juhyoung-native-7a2a`, **GPU 0만** 사용(`CUDA_VISIBLE_DEVICES=0`, `ir_run.sh` 기본값)
- 실행 환경: `IR_ROOT=cyclo` rootfs(Isaac Sim 5.1.0-rc.19 + Isaac Lab 2.3.0), `ir_run.sh`(unshare -m + bind + chroot)
- 코드: `harvest/sim/scene.py`, `harvest/sim/oracle_state.py`, 실행기 `harvest/sim/run_dev.py`
- 산출물(파드): `/data/juhyoung_qdd/out/t11_12/`

### 요약

| 항목 | 결과 |
|---|---|
| 로봇 | **FFW-SG2**(`FFW_SG2.usd`), 베이스 고정, **오른팔 7관절 + 그리퍼만 행동** |
| 카메라 | **cyclo_lab 기본 머리캠 `cam_head` 그대로**(단안 672×376, 수평 90.4°). ZED_M 쌍둥이·추가 스테레오 쌍 없음(사용자 지시로 Step 2 취소) |
| 깊이 | 기본 머리캠에 렌더러 GT 깊이 annotator(`distance_to_image_plane`)만 켬. 카메라 prim은 그대로 |
| 물체 | 머그 o3(빨강 원기둥), 트레이 o5(파랑 판), 방해물 o8·o9(시드로 0–2개), P2 전용 o10(평소 주차) |
| 시드 0 정착 | 100스텝(5 s) 뒤 머그 0.006 mm/s, 트레이 0.009 mm/s → **< 1 mm/s 통과**. 스폰→정착 이동 1.0 mm(스폰 높이 여유 1 mm) |
| RTF | 머리캠 켬(672×376 RGB+깊이) **0.536**, 카메라 끔(플래너 실행 중, DEV 90판 중앙값) **0.56–0.58** |
| 프레임 | `docs/stage3/results/scene_seed0.png`(머리캠, 166 KB), 깊이 `scene_seed0_depth.png` |

### Step 1 — 로봇 모델 결정 (정본 §38 → §37)

**결정: FFW-SG2, 베이스 고정, 한 팔(오른팔).**

근거(공식 저장소 `ROBOTIS-GIT/cyclo_lab`, 파드 클론 `/data/juhyoung_qdd/cyclo_lab`, 커밋 `f4c0470a5e0af54a18327cf96967e8716d64dbc0`, 2026-09-18):

- `grep`: `Cyclo-Real-Pick-Place-FFW-SG2-v0`(`config/ffw_sg2/joint_pos_env_cfg.py:FFWSG2PickPlaceEnvCfg`)와 `Cyclo-Real-Mimic-Pick-Place-FFW-SG2-v0`가 등록돼 있다. BG2는 `Cyclo-PickPlace-FFW-BG2-IK-Rel-v0` 등.
- SG2 과제의 행동 항목은 팔마다 따로다(`arm_r_action` = `JointPositionActionCfg(joint_names=["arm_r_joint[1-7]"])`, `gripper_r_action`, 왼팔·머리·리프트도 각각). 그래서 **오른팔 7관절 + 오른 그리퍼만 행동으로 두는 설정이 그대로 된다**. 왼팔·머리·리프트는 행동이 없고 PD 목표를 기본 자세로 둔다.
- 베이스: `FFW_SG2_CFG`를 실어 보니 `is_fixed_base=True`, 루트가 원점에 고정(USD에 world FixedJoint). 바퀴 관절 액추에이터는 공식 설정에서 주석 처리돼 있다(구동 안 됨).
- 관절 이름·한계(실측): `arm_r_joint1..7`, `gripper_r_joint1..4`(0 = 열림, 1.1 = 닫힘), `head_joint1`(−0.232–0.695), `lift_joint`(−0.5–0).
- 초기 자세: cyclo SG2 과제 기본값(`arm_*_joint1 = 0.75`, `arm_*_joint4 = −2.30`, `lift_joint = −0.0993`)에 **머리 pitch만 0.69**(한계 0.695 근처, 공식값 0.549)로 더 숙였다. 탁상 작업 영역이 머리캠에 들어오게 하려는 것이다.

`/data/newproj/rep_v3test`(T10이 `/workspace/cyclo_lab`에 읽기 전용 bind)는 다른 프로젝트가 고친 cyclo_lab 사본(taskC·convstore 등 추가)이라 **로봇·과제 설정에는 쓰지 않았다**. 여기서는 그 안의 `third_party/IsaacLab`(Isaac Lab 2.3.0 런타임)만 쓴다. `cyclo_lab` 패키지는 우리 클론을 `sys.path` 앞에 넣어 가져온다(`cyclo_lab.__file__` = `/data/juhyoung_qdd/cyclo_lab/...` 확인).

### Step 2 — 카메라 (사용자 지시로 변경: 모델 기본 카메라만)

원래 계획(ZED_M 확장 또는 머리 기선 63 mm 두 카메라)은 **사용자 지시로 취소했다.** AI Worker 모델에 기본으로 달린 카메라만 쓴다. 카메라 prim은 추가·이동·수정하지 않고, 필요하면 렌더러 깊이 annotator만 켠다.

#### cyclo_lab 기본 카메라 목록 (공식 클론 f4c0470 기준)

| 이름 | 정의 위치 | prim 경로 | 해상도 | 화각 | 출력 | 깊이 출력 가능 | 머리 좌우 스테레오 쌍 |
|---|---|---|---|---|---|---|---|
| `cam_head` (SG2) | `pick_place/config/ffw_sg2/joint_pos_env_cfg.py` | `Robot/ffw_sg2_follower/head_link2/zed/cam_head` (offset pos (0, 0.03, 0), rot (0.5, 0.5, −0.5, −0.5)) | 672×376 | focal 10.4 mm, h-aperture 20.955 mm → **수평 90.4°, 수직 58.8°**(fx = fy = 333.5 px 실측) | `rgb` | 가능(renderer `distance_to_image_plane`, 우리가 annotator만 켬) | **아니오**(단안. ZED Mini 오른쪽 눈은 설정에 없음) |
| `head_cam` (BG2) | `pick_place/config/ffw_bg2/joint_pos_env_cfg.py` | `Robot/ffw_bg2_follower/head/head_link2/head_cam` | 244×244 | focal 12 mm → 수평 82.3° | `rgb`, `distance_to_image_plane` | 예(설정에 이미 켜짐) | 아니오 |
| `right_wrist_cam` (BG2) | 같은 파일 | `Robot/ffw_bg2_follower/right_arm/arm_r_link7/camera_r_bottom_screw_frame/camera_r_link/right_wrist_cam` (offset (−0.08, 0, 0)) | 244×244 | focal 18 mm → 수평 60.4°, clip 0.1–2 m | `rgb` | 가능(annotator) | 해당 없음 |
| SG2 손목캠 | **없음** | SG2 USD에는 D405 장착 프레임 `arm_r_link7/camera_r_bottom_screw_frame/camera_r_link`(와 왼쪽)만 있고 Camera prim은 없다. SG2 과제 설정에도 손목캠 정의가 없다 | — | — | — | — | — |

- USD 자체 점검(`FFW_SG2.usd`, `FFW_BG2.usd`를 열어 Camera 형식 prim 탐색): **두 USD 모두 Camera prim 0개.** 카메라는 전부 cyclo_lab 과제 설정(`CameraCfg`)이 만든다. 따라서 "기본 카메라" = cyclo_lab 과제 설정에 정의된 카메라다.
- `make_env(cameras=...)`는 이 기본 카메라 이름만 받는다(`KNOWN_CAMERAS`). 기본값은 `("cam_head",)`. 다른 이름은 `ValueError`.
  - `cam_head`: SG2 공식 정의 객체를 그대로 가져와(`FFWSG2PickPlaceEnvCfg().scene.cam_head`) 깊이 annotator만 더한다.
  - `right_wrist_cam`: **SG2 공식 설정에는 없다.** BG2 공식 정의를 SG2의 같은 이름 장착 프레임(`camera_r_link`)에 경로 접두어만 바꿔 붙이는 선택지로 남겼다(해상도·화각·offset 그대로). 기본값에 넣지 않았고 이번 결과 어디에도 쓰지 않았다. SG2 기본이 아니므로 쓸지는 메인/사용자가 정한다.
- 이미 추가했던 카메라 코드: ZED_M/63 mm 쌍 코드는 장면에 넣기 전에 지시를 받아 **작성하지 않았다**(`scene.py`에 없음). 탐색용으로 받은 `stereolabs/zed-isaac-sim` 클론(`/data/juhyoung_qdd/ext/zed-isaac-sim`, 커밋 `0164268`)은 파드에 남아 있다(쓰지 않음). 참고: 이 확장은 kit 110 대상이고 네이티브 플러그인 빌드가 필요해 Isaac Sim 5.1(kit 107)에서 그대로 로드되지 않는다. `ZED_M.usdc`의 좌우 카메라 기선은 63 mm였다.

#### 머리캠 시야와 탁상 높이

cyclo 기본 머리캠은 머리 pitch 한계(0.695 rad)에서 수직 화각 58.8°라 가까운 탁상면이 잘 안 보인다. 탁상 윗면 0.76 m에서는 보이는 띠(x ≥ 0.385 m)와 오른팔이 위에서 집을 수 있는 띠(x ≤ 약 0.47 m)가 거의 겹치지 않았다(첫 프레임에서 머그가 화면 아래 끝에 걸림). 그래서 **탁상 윗면을 0.85 m로 올리고** 작업 영역을 x 0.36–0.48 m, y −0.40–−0.06 m로 옮겼다. 시드 0 프레임에서 머그·트레이가 모두 보인다.

### Step 3 — 머그·트레이 에셋

YCB 머그(Isaac 5.1 클라우드 `Props/YCB/Axis_Aligned/025_mug.usd`)는 시각 메시만 있고 물리 판(`Axis_Aligned_Physics/025_mug.usd`)은 404였다. 손잡이 달린 메시에 충돌 분해를 직접 만들면 오라클 플래너의 파지가 불안정해지므로, 정본 E §1.4의 "대상 물체 1(머그/블록)"에 맞춰 **해석적 기본 도형**을 썼다.

| id | 이름 | 모양 | 크기 | 질량 | 마찰(정/동) | 비고 |
|---|---|---|---|---|---|---|
| o3 | mug red | 원기둥 | r 32 mm, h 95 mm | 0.20 kg | 1.0 / 1.0 | 대상 |
| o5 | tray blue | 직육면체 | 180 × 140 × 15 mm | 0.40 kg | 0.8 / 0.8 | 놓을 곳(동적 강체) |
| o8 | bottle green | 원기둥 | r 25 mm, h 100 mm | 0.15 kg | 0.8 / 0.8 | 방해물(시드로 0–2개) |
| o9 | box yellow | 직육면체 | 50 × 50 × 70 mm | 0.10 kg | 0.8 / 0.8 | 방해물 |
| o10 | box purple | 직육면체 | 60 × 50 × 80 mm | 0.10 kg | 0.8 / 0.8 | **P2 전용**, 평소엔 로봇 뒤 바닥에 주차 |
| table | — | 정적 직육면체 | 0.70 × 1.00 × 0.04 m, 윗면 z = 0.85 m | 정적 | 0.6 / 0.6 | 탁상 좌표 원점 z = 0 |

- 공통: 반발 0, `contact_offset` 4 mm, `rest_offset` 0, `max_depenetration_velocity` 1.0 m/s, 물체마다 접촉 센서(손가락 링크 4개 + 다른 물체로 필터).
- 초기 배치: `sample_layout(seed)`(순수 함수, 시드 결정적). 머그–트레이 중심 거리 ≥ 16 cm, 방해물은 머그에서 ≥ 10 cm(손가락 자리), 물체끼리 겹침 없음. DEV 0–29에서 방해물 수 0·1·2가 모두 나온다(테스트).
- 로봇: `FFW_SG2_CFG` 그대로(자기 충돌 켬, 위치 반복 32, 로봇 링크 중력 끔 = cyclo 설정). **바꾼 것 하나: 그리퍼.** cyclo는 `gripper_r_joint1`만 강하게(강성 100), 나머지 세 손가락 관절은 강성 2로 둔다. 이 상태로 머그를 쥐면 손가락이 비대칭으로 닫혀(실측 관절 [0.88, 1.10, 0.16, 0.40]) 머그를 28 mm 밀고 팔까지 밀렸다. 그래서 cyclo BG2 과제가 하는 대로 **네 관절에 같은 목표**를 주고(`close_command_expr "gripper_r_joint.*"`와 같은 방식), 보조 관절 게인을 주 관절 값으로 맞췄다. 실제 게인은 나중에 실물 계단 응답으로 다시 맞춘다(정본 §37 [가정]).
- 그리퍼 폭: 명령은 폭(m) → `gripper_r_joint1` 목표(무부하 실측 표 보간, 0 → 107.0 mm, 1.1 → 2.3 mm). 읽기는 관절값이 아니라 **손가락 link2 원점 거리 − 7.7 mm**(USD 경계 상자로 잰 패드 안쪽 면 거리)로 잰다.
- TCP: link7 원점에서 그리퍼 축(link7 −z)으로 **167.1 mm**(패드 중심), 손끝 194.5 mm. USD 기본 자세의 손가락 경계 상자에서 계산했다(`_measure_finger_offsets`).

### Step 4 — 순수 로직 테스트 (로컬, Isaac 없이)

- `tests/sim/test_sim_logic.py::test_table_frame_origin`(기존) — 월드 → 탁상 윗면 원점.
- `tests/sim/test_scene_logic.py`(새로, 36개): 시드 결정성, 배치 제약(DEV 0–29 전부), 방해물 수 0·1·2 모두 나옴, 그리퍼 폭↔관절 왕복·단조, `support_from_contacts`(접촉한 아래 물체 중 가장 높은 것 / 탁상 / 공중 None).
- 로컬 전체: `python -m pytest -p no:cacheprovider -q tests` 통과, 파드(`pod_sync.sh`)도 통과.

### Step 5 — 부팅 확인 (파드, 시드 0)

명령: `ir_run.sh env HOME=… TMPDIR=… /isaac-sim/python.sh -m harvest.sim.run_dev boot` (결과 `boot_seed0.json`)

- 과정: 리셋 1회(상태 쓰기 1회), 정착 대기 없이 팔을 제자리 유지 명령으로 100스텝(= 5 s, 스텝 0.05 s = dt 0.01 × decimation 5).
- 정착: 마지막 10스텝 최대 속도 머그 **0.006 mm/s**, 트레이 **0.009 mm/s** → < 1 mm/s 통과. 바닥 높이(탁상 좌표) 둘 다 0.0 mm, 스폰→정착 이동 1.0 mm.
- RTF(머리캠 672×376 RGB + GT 깊이 켬): **0.536**(100스텝 = 시뮬 5.0 s에 벽시계 9.32 s). `make_env` 22.2 s(앱 기동 포함, 셰이더 캐시가 데워진 상태).
- 머리캠 내부 행렬(실측): fx = fy = 333.5, cx = 336, cy = 188. GT 깊이 유효 비율 1.0, 범위 0.22–6.9 m.
- 프레임: `scene_seed0.png` — 탁상, 파란 트레이, 빨간 머그(오른쪽), 화면 아래 양팔 그리퍼가 보인다. 깊이 `scene_seed0_depth.png`에서 탁상·그리퍼 윤곽이 보인다.

### 부딪힌 문제와 해결 (재발 방지용)

1. **행동이 없는 관절이 0으로 끌려감**: Isaac Lab은 행동 항목이 없는 관절의 PD 목표를 0으로 둔다. 리셋 뒤 머리 pitch가 0(수평)으로, 리프트가 0으로 돌아가 머리캠이 바닥만 비췄다. 리셋 이벤트에서 **기본 자세를 PD 목표로 한 번 설정**해 해결(상태 쓰기 아님, 목표 설정).
2. **매 스텝 상태 쓰기 금지**: 물체 배치는 리셋 이벤트에서 한 번만 쓴다. 섭동(P1·P2)도 발동 순간 자세 1회 쓰기뿐이다.
3. `SimulationApp.close()`가 chroot 안에서 멈춰서 실행기는 결과를 다 쓴 뒤 `os._exit(0)`로 끝낸다.

### /data 밖에 쓴 것 (사용자 지시에 따른 보고, 지우지 않음)

지시(모든 파일·캐시는 /data 아래) 전에 쓴 것:
- 파드 `/tmp/zedm_dump.py`(ZED_M USD 점검 스크립트, 890 B, 17:46 KST = 08:46 UTC).
- cyclo rootfs 안(물리 위치는 `/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0/`, 즉 /data 아래지만 chroot 안의 `/tmp`·`/root`):
  - `<rootfs>/tmp/carb.*`(약 12개), `<rootfs>/tmp/tmp*/_remote_module_non_scriptable.py`(약 12개), `<rootfs>/tmp/hub-root.lock` — 08:44–09:24 UTC 사이 우리 Isaac 실행이 만든 것.
  - `<rootfs>/root/.nvidia-omniverse/logs/*.log`(7개, 09:24–09:29 UTC 갱신).
- 지시 뒤(09:3x UTC~)의 모든 실행은 `HOME=/data/juhyoung_qdd/home TMPDIR=/data/juhyoung_qdd/tmp XDG_CACHE_HOME=/data/juhyoung_qdd/cache HF_HOME=…/cache/hf TORCH_HOME=…/cache/torch PIP_CACHE_DIR=…/cache/pip WARP_CACHE_PATH=…/cache/warp`를 chroot 안 프로세스에 준다. kit 캐시·데이터·로그는 `ir_run.sh`가 이미 `/data/juhyoung_qdd/ir/kitcache/<root>-<inst>`로 bind한다(확인).

### 방향 점검 메모 (질문 5: 장면 RTF ≪ 1?)
- RTF는 카메라 끔 0.56–0.58, 머리캠 켬 0.54로 1보다 작다(T10 Franka Lift 카메라 끔 2.32보다 4배 느림). 원인 후보(미측정): SG2 관절 31개·자기 충돌·위치 반복 32, 물체 5개 접촉 센서, 스텝마다 파이썬 술어·IK. "≪ 1"로 볼 수준은 아니지만 이 장면에서 벽시계(wall) 트랙은 못 쓰고 simlat가 기본이다(정본 §42와 같은 결론). 풀 생성(T13)은 프로세스 분할로 시간을 맞춘다.
