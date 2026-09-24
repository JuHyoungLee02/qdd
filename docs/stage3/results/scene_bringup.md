# Task 11 — 시뮬 장면 기동 결과 (AI Worker 한 팔 + 머그/트레이)

- 작업 시각: 2026-09-24 08:44–10:54 UTC (파드 `date -u`)
- 파드: `p-test2/juhyoung-native-7a2a`, **GPU 0만** 사용(`CUDA_VISIBLE_DEVICES=0`, `ir_run.sh` 기본값)
- 실행 환경: `IR_ROOT=cyclo` rootfs(Isaac Sim 5.1.0-rc.19 + Isaac Lab 2.3.0), `ir_run.sh`(unshare -m + bind + chroot)
- 코드: `harvest/sim/scene.py`, `harvest/sim/oracle_state.py`, 실행기 `harvest/sim/run_dev.py`
- 산출물(파드): `/data/juhyoung_qdd/out/t11_12/`

## 요약

| 항목 | 결과 |
|---|---|
| 로봇 | **FFW-SG2**(`FFW_SG2.usd`), 베이스 고정, **오른팔 7관절 + 그리퍼만 행동** |
| 카메라 | **cyclo_lab 기본 머리캠 `cam_head` 그대로**(단안 672×376, 수평 90.4°). ZED_M 쌍둥이·추가 스테레오 쌍 없음(사용자 지시로 Step 2 취소) |
| 깊이 | 기본 머리캠에 렌더러 GT 깊이 annotator(`distance_to_image_plane`)만 켬. 카메라 prim은 그대로 |
| 물체 | 머그 o3(빨강 원기둥), 트레이 o5(파랑 판), 방해물 o8·o9(시드로 0–2개), P2 전용 o10(평소 주차) |
| 시드 0 정착 | 100스텝(5 s) 뒤 머그 0.006 mm/s, 트레이 0.009 mm/s → **< 1 mm/s 통과**. 스폰→정착 이동 1.0 mm(스폰 높이 여유 1 mm) |
| RTF | 머리캠 켬(672×376 RGB+깊이) **0.536**, 카메라 끔(플래너 실행 중, DEV 90판 중앙값) **0.56–0.58** |
| 프레임 | `docs/stage3/results/scene_seed0.png`(머리캠, 166 KB), 깊이 `scene_seed0_depth.png` |

## Step 1 — 로봇 모델 결정 (정본 §38 → §37)

**결정: FFW-SG2, 베이스 고정, 한 팔(오른팔).**

근거(공식 저장소 `ROBOTIS-GIT/cyclo_lab`, 파드 클론 `/data/juhyoung_qdd/cyclo_lab`, 커밋 `f4c0470a5e0af54a18327cf96967e8716d64dbc0`, 2026-09-18):

- `grep`: `Cyclo-Real-Pick-Place-FFW-SG2-v0`(`config/ffw_sg2/joint_pos_env_cfg.py:FFWSG2PickPlaceEnvCfg`)와 `Cyclo-Real-Mimic-Pick-Place-FFW-SG2-v0`가 등록돼 있다. BG2는 `Cyclo-PickPlace-FFW-BG2-IK-Rel-v0` 등.
- SG2 과제의 행동 항목은 팔마다 따로다(`arm_r_action` = `JointPositionActionCfg(joint_names=["arm_r_joint[1-7]"])`, `gripper_r_action`, 왼팔·머리·리프트도 각각). 그래서 **오른팔 7관절 + 오른 그리퍼만 행동으로 두는 설정이 그대로 된다**. 왼팔·머리·리프트는 행동이 없고 PD 목표를 기본 자세로 둔다.
- 베이스: `FFW_SG2_CFG`를 실어 보니 `is_fixed_base=True`, 루트가 원점에 고정(USD에 world FixedJoint). 바퀴 관절 액추에이터는 공식 설정에서 주석 처리돼 있다(구동 안 됨).
- 관절 이름·한계(실측): `arm_r_joint1..7`, `gripper_r_joint1..4`(0 = 열림, 1.1 = 닫힘), `head_joint1`(−0.232–0.695), `lift_joint`(−0.5–0).
- 초기 자세: cyclo SG2 과제 기본값(`arm_*_joint1 = 0.75`, `arm_*_joint4 = −2.30`, `lift_joint = −0.0993`)에 **머리 pitch만 0.69**(한계 0.695 근처, 공식값 0.549)로 더 숙였다. 탁상 작업 영역이 머리캠에 들어오게 하려는 것이다.

`/data/newproj/rep_v3test`(T10이 `/workspace/cyclo_lab`에 읽기 전용 bind)는 다른 프로젝트가 고친 cyclo_lab 사본(taskC·convstore 등 추가)이라 **로봇·과제 설정에는 쓰지 않았다**. 여기서는 그 안의 `third_party/IsaacLab`(Isaac Lab 2.3.0 런타임)만 쓴다. `cyclo_lab` 패키지는 우리 클론을 `sys.path` 앞에 넣어 가져온다(`cyclo_lab.__file__` = `/data/juhyoung_qdd/cyclo_lab/...` 확인).

## Step 2 — 카메라 (사용자 지시로 변경: 모델 기본 카메라만)

원래 계획(ZED_M 확장 또는 머리 기선 63 mm 두 카메라)은 **사용자 지시로 취소했다.** AI Worker 모델에 기본으로 달린 카메라만 쓴다. 카메라 prim은 추가·이동·수정하지 않고, 필요하면 렌더러 깊이 annotator만 켠다.

### cyclo_lab 기본 카메라 목록 (공식 클론 f4c0470 기준)

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

### 머리캠 시야와 탁상 높이

cyclo 기본 머리캠은 머리 pitch 한계(0.695 rad)에서 수직 화각 58.8°라 가까운 탁상면이 잘 안 보인다. 탁상 윗면 0.76 m에서는 보이는 띠(x ≥ 0.385 m)와 오른팔이 위에서 집을 수 있는 띠(x ≤ 약 0.47 m)가 거의 겹치지 않았다(첫 프레임에서 머그가 화면 아래 끝에 걸림). 그래서 **탁상 윗면을 0.85 m로 올리고** 작업 영역을 x 0.36–0.48 m, y −0.40–−0.06 m로 옮겼다. 시드 0 프레임에서 머그·트레이가 모두 보인다.

## Step 3 — 머그·트레이 에셋

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

## Step 4 — 순수 로직 테스트 (로컬, Isaac 없이)

- `tests/sim/test_sim_logic.py::test_table_frame_origin`(기존) — 월드 → 탁상 윗면 원점.
- `tests/sim/test_scene_logic.py`(새로, 36개): 시드 결정성, 배치 제약(DEV 0–29 전부), 방해물 수 0·1·2 모두 나옴, 그리퍼 폭↔관절 왕복·단조, `support_from_contacts`(접촉한 아래 물체 중 가장 높은 것 / 탁상 / 공중 None).
- 로컬 전체: `python -m pytest -p no:cacheprovider -q tests` 통과, 파드(`pod_sync.sh`)도 통과.

## Step 5 — 부팅 확인 (파드, 시드 0)

명령: `ir_run.sh env HOME=… TMPDIR=… /isaac-sim/python.sh -m harvest.sim.run_dev boot` (결과 `boot_seed0.json`)

- 과정: 리셋 1회(상태 쓰기 1회), 정착 대기 없이 팔을 제자리 유지 명령으로 100스텝(= 5 s, 스텝 0.05 s = dt 0.01 × decimation 5).
- 정착: 마지막 10스텝 최대 속도 머그 **0.006 mm/s**, 트레이 **0.009 mm/s** → < 1 mm/s 통과. 바닥 높이(탁상 좌표) 둘 다 0.0 mm, 스폰→정착 이동 1.0 mm.
- RTF(머리캠 672×376 RGB + GT 깊이 켬): **0.536**(100스텝 = 시뮬 5.0 s에 벽시계 9.32 s). `make_env` 22.2 s(앱 기동 포함, 셰이더 캐시가 데워진 상태).
- 머리캠 내부 행렬(실측): fx = fy = 333.5, cx = 336, cy = 188. GT 깊이 유효 비율 1.0, 범위 0.22–6.9 m.
- 프레임: `scene_seed0.png` — 탁상, 파란 트레이, 빨간 머그(오른쪽), 화면 아래 양팔 그리퍼가 보인다. 깊이 `scene_seed0_depth.png`에서 탁상·그리퍼 윤곽이 보인다.

## 부딪힌 문제와 해결 (재발 방지용)

1. **행동이 없는 관절이 0으로 끌려감**: Isaac Lab은 행동 항목이 없는 관절의 PD 목표를 0으로 둔다. 리셋 뒤 머리 pitch가 0(수평)으로, 리프트가 0으로 돌아가 머리캠이 바닥만 비췄다. 리셋 이벤트에서 **기본 자세를 PD 목표로 한 번 설정**해 해결(상태 쓰기 아님, 목표 설정).
2. **매 스텝 상태 쓰기 금지**: 물체 배치는 리셋 이벤트에서 한 번만 쓴다. 섭동(P1·P2)도 발동 순간 자세 1회 쓰기뿐이다.
3. `SimulationApp.close()`가 chroot 안에서 멈춰서 실행기는 결과를 다 쓴 뒤 `os._exit(0)`로 끝낸다.

## /data 밖에 쓴 것 (사용자 지시에 따른 보고, 지우지 않음)

지시(모든 파일·캐시는 /data 아래) 전에 쓴 것:
- 파드 `/tmp/zedm_dump.py`(ZED_M USD 점검 스크립트, 890 B, 17:46 KST = 08:46 UTC).
- cyclo rootfs 안(물리 위치는 `/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0/`, 즉 /data 아래지만 chroot 안의 `/tmp`·`/root`):
  - `<rootfs>/tmp/carb.*`(약 12개), `<rootfs>/tmp/tmp*/_remote_module_non_scriptable.py`(약 12개), `<rootfs>/tmp/hub-root.lock` — 08:44–09:24 UTC 사이 우리 Isaac 실행이 만든 것.
  - `<rootfs>/root/.nvidia-omniverse/logs/*.log`(7개, 09:24–09:29 UTC 갱신).
- 지시 뒤(09:3x UTC~)의 모든 실행은 `HOME=/data/juhyoung_qdd/home TMPDIR=/data/juhyoung_qdd/tmp XDG_CACHE_HOME=/data/juhyoung_qdd/cache HF_HOME=…/cache/hf TORCH_HOME=…/cache/torch PIP_CACHE_DIR=…/cache/pip WARP_CACHE_PATH=…/cache/warp`를 chroot 안 프로세스에 준다. kit 캐시·데이터·로그는 `ir_run.sh`가 이미 `/data/juhyoung_qdd/ir/kitcache/<root>-<inst>`로 bind한다(확인).

## 방향 점검 메모 (질문 5: 장면 RTF ≪ 1?)
- RTF는 카메라 끔 0.56–0.58, 머리캠 켬 0.54로 1보다 작다(T10 Franka Lift 카메라 끔 2.32보다 4배 느림). 원인 후보(미측정): SG2 관절 31개·자기 충돌·위치 반복 32, 물체 5개 접촉 센서, 스텝마다 파이썬 술어·IK. "≪ 1"로 볼 수준은 아니지만 이 장면에서 벽시계(wall) 트랙은 못 쓰고 simlat가 기본이다(정본 §42와 같은 결론). 풀 생성(T13)은 프로세스 분할로 시간을 맞춘다.
