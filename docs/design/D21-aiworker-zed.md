# D21 ROBOTIS AI Worker + ZED 스테레오 플랫폼 조사 (user-log 37)

저장 2026-09-24 07:28 UTC. 조사 에이전트 보고 전문. 메인 원 출처 재확인(D:/tools/audit_d21, curl): 공식 사양 페이지 "Head Camera: Stereolabs ZED Mini"·"Hand Cameras: Intel RealSense D405 (x2)"·"Arm: 7 DOF x 2"·"RH-P12-RN"·"Jetson AGX Orin", 힘/토크 센서 표기 없음 / ai_worker `common_stereo.yaml` "depth_mode: 'NONE'", `zedm.yaml` "grab_resolution: 'VGA'"·"grab_frame_rate: 30" / cyclo_lab "Isaac Sim 5.1.0" / RoboDojo "ARX X5 bimanual platform" — 모두 일치.


D:\qdd는 읽기만 했습니다. 내려받은 자료는 모두 `D:\tools\audit_d21\`에 있습니다(README, 설정 yaml, URDF, 트리 json, Stereolabs 문서 .md). C: 드라이브는 쓰지 않았습니다.

---

## 1. AI Worker 사양 (1차 출처)

### 1.1 모델과 자유도
출처는 공식 사양 페이지 https://ai.robotis.com/ai_worker/hardware_ai_worker.html 입니다.
- 팔로어(실행 로봇): **FFW-SG2**(스워브 이동 베이스)와 **FFW-BG2**(고정 베이스, 원문 "FFW-BG2 is sold in Korea only"). "FFW-SH3P is currently in preparation for release"라고 되어 있습니다.
- 리더(원격조종 장치): FFW-LG2("Gripper: 1 DOF x 2"). "FFW-LH5 … Hand: 20 DOF x 2"는 준비 중입니다.
- 자유도(원문):
  - SG2: "Total: 25 DOF – Arm: 7 DOF x 2 – Gripper: 1 DOF x 2 – Head: 2 DOF x 1 – Lift: 1 DOF x 1 – Mobile: 6 DOF"
  - BG2: "Total: 19 DOF"(이동 없음)
- 그 밖의 원문 수치:
  - 팔 도달 거리 "641 mm (to wrist) + hand"
  - 가반하중 "3.0 kg (single arm) – 6.0 kg (dual arm)"(정격)
  - 리프트 "0 ~ 500 mm"
  - 머리 "Head Pitch: -50° ~ 30°", "Head Yaw: -20° ~ 20°"
- 그리퍼: "RH-P12-RN", "1-DOF two-fingered robot hand", "0 ~ 107.6 mm", "5kg" 가반. 원문 "Dexterous Finger Actuator in development".
- 손 모델 코드: GitHub 설정에는 `ffw_sh5`·`ffw_bh5`(손 메시 `hx5_d20`) 팔로어 설정이 이미 있습니다. 판매 상태는 [미확인]입니다.
- 계산기: "NVIDIA Jetson AGX Orin 32GB".
- 구동기: 팔 1–3축 "YM080-230-R099-RH", 4–6축 "YM070-210-R099-RH", 7축 "PH42-020-S300-R"(모두 DYNAMIXEL). 통신은 "RS-485", "4 Mbps".

### 1.2 카메라
- 머리: **"Stereolabs ZED Mini"**, "Stereoscopic RGBD with 6DoF IMU", "102°(H) x 57°(V)", "0.1m to 9m".
- 손목: **"Intel RealSense D405" ×2**, "87°(H) × 58°(V)", "7cm to 50cm".
  - 참고: URDF 파일 이름은 `wrist_d401.urdf.xacro`라서 이름이 어긋납니다. 사양 페이지 기준으로 D405로 봅니다. 차이의 이유는 [미확인]입니다.
- 라이다: "LakiBeam 1 (x2)".
- 배포된 ZED 설정(`ffw_bringup/config/common/zedm.yaml`, `common_stereo.yaml`): `grab_resolution: 'VGA'`, `grab_frame_rate: 30`, **`depth_mode: 'NONE'`**.
  - 즉 **ROBOTIS 기본 구성은 깊이를 계산하지 않습니다.** 런치 파일이 덮어쓰는 흔적도 찾지 못했습니다.

### 1.3 제어 인터페이스
- ROS 2 **Jazzy**입니다(CI `ros_distribution: jazzy`, `physical_ai_tools`도 `-b jazzy`).
- 제어기(`ffw_sg2_follower_ai_hardware_controller.yaml`):
  - `update_rate: 100 # Hz`
  - 팔마다 `joint_trajectory_controller/JointTrajectoryController`(팔 7축 + gripper_joint1), `command_interfaces: position`
  - 머리·리프트 JTC 별도, 스워브 제어기 별도
- ros2_control 상태 인터페이스(`ffw_sg2_follower.ros2_control.xacro`): `position`, `velocity`, **`effort`** 가 있고, 서보 레지스터 "Present Current"를 읽습니다.
  - **손목 힘/토크 센서는 사양·URDF 어디에도 없습니다.**
  - 센서 시스템은 IMU(ID 200)와 LED뿐입니다.
- 서보 내부 프로파일(오른팔 1축 원문): `Drive Mode 69`, `Profile Velocity 3591`, `Profile Acceleration 3591`, `Profile Acceleration Time 250`, `Profile Time 500`, `Velocity Limit 3591`.
  - `_smooth` 판에서는 `Profile Acceleration Time 750`입니다.
  - 단위와 시간 기반 프로파일 여부는 [미확인]입니다. 다만 이 값이 켜져 있으면 **우리 Ruckig 궤적 위에 서보가 한 번 더 평활화할 수 있습니다**. 이는 M4 (b)의 `ref(t)`와 실제 추종 사이의 지연이 됩니다 [추정].
- URDF 관절 한계(`ffw_sg2_follower.urdf`): 팔 모든 관절이 `velocity="4.8"`, `effort="1000"`으로 같습니다. 자리표시 값으로 보입니다 [추정]. 가속·저크 한계는 없습니다.

### 1.4 원격조종과 데이터 수집
- 원격조종 방식:
  - 리더 FFW-LG2(관절 대응 방식)
  - VR: cyclo_lab README "ROBOTIS HAND VR Teleoperation in Isaac Sim"
- `physical_ai_tools` 설정(`ffw_sg2_rev1_config.yaml`)이 기록하는 관측:
  - `cam_head:/zed/zed_node/left/image_rect_color/compressed`(**왼쪽 영상만, 깊이 없음**)
  - 좌우 손목 D405 color
  - `/joint_states`, `/odom`, 리더 궤적
- 현행 도구 Cyclo Intelligence(https://docs.robotis.com/docs/systems/aiworker/imitation_learning/):
  - 기록: "rosbag2 episodes", MCAP, 이후 LeRobot 변환
  - 학습 가능 정책: ACT, Diffusion, SmolVLA, XVLA, Pi0/Pi0.5, "GR00T N1.7", MolmoAct2. 원문 "Train only the policies that have a matching inference backend."
- HF 공개 데이터(https://huggingface.co/ROBOTIS, `meta/info.json` 직접 확인)는 모두 LeRobot v2.1입니다.

| 데이터 | 로봇 | fps | 에피소드 | 머리 카메라 |
|---|---|---|---|---|
| Task_0001_CoffeeClassification | ffw_bg2_rev4_custom | 10 | 718 | `cam_head`와 **`cam_head_right`**(스테레오 쌍) 376×672, 손목 424×240 |
| Task_0002_OrderPicking | ffw_bg2_rev4 | 10 | 857 | 왼쪽·오른쪽 스테레오 쌍 376×672, 상태 19차원 |
| Task_0003·0004·0005·0006 | ffw_arm_only | 15 | — | 왼쪽 머리 1280×720 한 대만 |

  - 공개 모델: GR00T-N1.5/N1.6 파인튜닝 체크포인트 6개.
  - 공식 벤치마크 수치는 찾지 못했습니다.

### 1.5 공식 시뮬 자산

| 저장소 | 별 | 내용 |
|---|---|---|
| ROBOTIS-GIT/ai_worker | 187★ | URDF/xacro, Gazebo(`gz_ros2_control`) 런치, MoveIt 설정 |
| **ROBOTIS-GIT/cyclo_lab** (구 robotis_lab) | 145★ | **Isaac Sim 5.1.0 / Isaac Lab 2.3.0** 기반. USD `FFW_BG2.usd`·`FFW_SG2.usd`·`FFW_SH5`. 과제 예시 `Cyclo-Reach-FFW-BG2-v0`, `Cyclo-PickPlace-FFW-BG2-IK-Rel-v0`(Isaac Lab Mimic 데이터 생성 포함), `Cyclo-Real-Pick-Place-FFW-SG2-v0`(Sim2Real, `isaaclab2lerobot.py` 변환기). 최신 릴리스 2.0.2(2026-07-24) |
| ROBOTIS-GIT/robotis_mujoco_menagerie | 74★ | MJCF `ffw_bg2.xml`·`ffw_sg2.xml`·`ffw_sh5.xml`. `ffw_sg2.xml`에는 `<camera>` 정의가 없습니다(grep 결과) |
| ROBOTIS-GIT/physical_ai_tools | 145★ | — |
| cyclo_intelligence | 34★ | — |

- cyclo_lab의 카메라가 ZED Mini의 실제 쌍둥이가 아닙니다.
  - SG2 머리 카메라: **단안 RGB 672×376**, focal 10.4 / aperture 20.955 → 수평 화각 약 90°(우리 계산). ZED Mini는 102°입니다.
  - BG2: 머리 244×244 `rgb` + `distance_to_image_plane`, 손목 244×244 RGB.
- 시뮬 설정 `sim.dt = 0.01`(100 Hz), `decimation = 5`.
- 액추에이터(Implicit): 팔 `velocity_limit_sim=15.0`, `effort_limit_sim` 61.4 / 31.7 / 5.1.

---

## 2. ZED 스테레오 깊이

### 2.1 ZED Mini 공식 사양
출처: https://docs.stereolabs.com/docs/products/cameras/zed/specifications.md
- 기선 "63 mm"
- "1/3" 4 MP … rolling shutter"
- 출력 "2x(2208x1242) @15 fps, 2x(1920x1080) @30 fps, 2x(1280x720) @60 fps, 2x(672x376) @100 fps"
- 깊이 "0.1 m to 15 m", ideal "0.1 m to 9 m"
- 정확도 "< 1.0% at 2 m, < 1.8% at 4 m"
- IMU 800 Hz
- **지연 수치는 공개되지 않았습니다 [미확인].**

### 2.2 ZED SDK 5 깊이 모드
출처: https://docs.stereolabs.com/docs/development/zed-sdk/modules/depth-sensing/depth-modes.md
- 원문 "The legacy `PERFORMANCE`, `QUALITY`, and `ULTRA` modes are still available in the API but are deprecated". 선택지는 `NEURAL_LIGHT` / `NEURAL` / `NEURAL_PLUS`이고, **`CUSTOM`은 "feed the SDK your own disparity or depth"** 를 허용합니다. 외부 학습 스테레오를 ZED 파이프라인에 넣을 수 있다는 뜻입니다.
- Orin AGX 성능: NEURAL 카메라 1대 30 FPS, GPU 26%. NEURAL_LIGHT 1대 30 FPS, GPU 11%.
  - 단서: ZED X와 SDK 5.0.1 RC로 잰 값이고, ZED Mini로 잰 값은 [미확인]입니다.
- NEURAL 정확도(ZED X 기준): "[0.3 - 4] < 1%".
- 원문 "SVO files store only the raw unrectified images … can be replayed later with any depth mode". 기록한 뒤 깊이 모드를 바꿔 다시 계산할 수 있습니다.

### 2.3 우리 거리에서의 깊이 오차 [추정 계산]
- 가정: 시차 오차 0.25 px.
- 수식: 초점거리 f ≈ (가로 폭/2)/tan(51°), 깊이 오차 Δz = z²·Δd/(f·B).
- 결과:

| 해상도 | f | z = 0.6 m | z = 1.0 m |
|---|---|---|---|
| VGA | ≈272 px | 약 5 mm | 약 15 mm |
| HD720 | ≈518 px | 약 3 mm | 약 8 mm |

- 해석: M1 T1 술어 문턱(cm 단위)에는 대체로 충분합니다. 접촉 근처는 D405(7–50 cm)가 맡는 편이 맞습니다.

### 2.4 학습 스테레오 대안 (기간: 2025-03-24 이후)

| 모델 | 출처·등급 | 별 | 핵심 |
|---|---|---|---|
| **Fast-FoundationStereo** | arXiv 2512.11130, README "accepted to CVPR 2026", NVIDIA — **HIGH** | 1,497★ | 원문 "run over 10× faster than FoundationStereo while closely matching its zero-shot accuracy". 3090·640×480 TRT 14.0–23.4 ms. 상업용 C-Fast-FS는 NVIDIA Open Model Agreement. 원문 "If you obtain images from stereo cameras such as Zed, they usually have handled this for you" |
| FoundationStereo | arXiv 2501.09898(기간 경계 밖), CVPR 2025 | 2,924★ | 교사 모델로만 |
| Lite Any Stereo V2 | arXiv 2606.24457, 학회 표기 없음 — **LOW-MED** | [미확인] | 초록 요약: Fast-FS보다 zero-shot이 낫고 "1.8× faster on H200, 2.7× … Orin". 대안 1순위로 올리지 않습니다 |
| DEFOM-Stereo | CVPR 2025 | 298★ | 대안 |
| Stereo Anywhere | CVPR 2025 | 284★ | 대안 |
| S2M2 | ICCV 2025 | [미확인] | 대안 |

- Orin에서의 Fast-FS 실측은 [미확인]입니다.

---

## 3. 우리 설계에 미치는 영향과 제안

### 3.1 M1 앞단
- M1 §4 "깊이(스테레오면 Fast-FoundationStereo)"는 사용자 결정과 그대로 맞습니다.
- [제안] 깊이는 이렇게 둡니다.
  - 머리: 1순위 **ZED SDK NEURAL**(Orin 30 FPS 공식), 비교 조건 **Fast-FS**(`DEPTH_MODE::CUSTOM`으로 같은 파이프라인에 주입).
  - 손목: D405 센서 깊이(근거리). 손목도 스테레오 원시 영상이 있어 Fast-FS를 돌릴 수 있습니다(README "tested … RealSense D4XX").
- [제안] **ROBOTIS 기본 `depth_mode: NONE`을 바꿔야 합니다.** 기록은 SVO(원시 스테레오)로 남겨 깊이 모드를 오프라인에서 바꿔 비교합니다.
- [제안] **로봇이 없어도 지금 할 수 있는 실물 오프라인 시험**: HF `ROBOTIS/Task_0001`(718편)과 `Task_0002`(857편)에 **머리 좌우 쌍이 LeRobot 영상으로 들어 있습니다.** 여기에 Fast-FS를 돌려 SAM 3.1 → 3D 중심 → 술어가 프레임 사이에서 얼마나 안정한지 잴 수 있습니다.
  - 한계: mp4 압축이 정합을 해칠 수 있음 [가정], 보정값(기선·내부 행렬)이 데이터에 없음 [미확인], 정답 자세 없음 → 정확도는 못 재고 **안정성만** 잽니다.
- 트랙 O/D 문제(EVAL §2.1): AI Worker 실물에서는 깊이가 "센서 입력"이 되므로 트랙 D가 자연스럽습니다. RoboDojo 쪽 처리는 §3.7에서 다룹니다.

### 3.2 카메라 배치와 Astra 다중 프레임 격자(M8 §4.3)
- AI Worker는 머리 ZED Mini 1대(팬·틸트 가능)와 손목 D405 2대입니다. RoboDojo의 "머리 1 + 손목 2" 구성과 **대수·배치가 같습니다.**
- [제안] Astra에는 **ZED 왼쪽 영상만** 격자로 보냅니다(카메라별 한 장, M8 규칙 그대로). 오른쪽 영상과 깊이 컬러맵은 보내지 않습니다. 깊이 컬러맵은 절제 조건으로만 둡니다.
- 칸 해상도: VGA 672×376이면 5×2 격자가 3360×752입니다. 토큰 수는 M8 표 계산식으로 다시 계산해야 합니다(표에 없는 해상도).
- 손목 424×240은 칸이 작습니다. 손목 격자는 3×2 이하로 두거나 현재 프레임 1장만 보내는 쪽을 권합니다 [제안].
- 머리 팬·틸트가 있으므로 M6에 `look_at(target)` 스킬을 넣습니다. 격자 칸마다 머리 자세가 다를 수 있으니 칸 덧그림에 머리 각을 표시합니다 [제안].

### 3.3 M5 한계(Ruckig)
- 제어 구조: 100 Hz JTC 위치 명령 → DYNAMIXEL 내부 프로파일.
- [제안] 순서:
  1. 실물에서 `get_dxl_data`로 Profile/Drive Mode를 읽고 계단 응답을 잽니다.
  2. 서보 내부 프로파일이 켜져 있으면 끄거나 최소화합니다. 불가하면 그 지연을 `ref(t)` 모델에 포함합니다(M4 (b) 가짜 LAG 방지).
  3. 관절 Ruckig 한계는 URDF 4.8 rad/s(자리표시로 보임)가 아니라 실측과 서보 사양에서 정하고 50%로 시작합니다 [가정].
- M5 직교 한계(v 0.25 m/s 등)는 가반 3 kg에서 무리가 없어 보이지만 [가정], 7자유도 여유가 있으므로 IK 영공간 규칙이 필요합니다.
- M5 §7-4 "한계값은 벤치마크 로봇 사양이 정해진 뒤"는 **로봇별 한계표 두 벌**(ARX X5, AI Worker)로 바꿉니다.

### 3.4 스킬 세트(양팔)
- 기존 pick/place FSM과 `arms: left|right|both` 결정 지점(M6 §351)은 그대로 씁니다.
- [제안] 추가 스킬: `look_at`(머리 2축), `set_lift`(0–500 mm, 작업 높이 맞춤), `handover`(좌→우), `bimanual_hold`.
- SG2의 이동 베이스는 범위 밖으로 둡니다. 실물은 **BG2 또는 SG2 베이스 고정** [제안].
- 그리퍼는 1-DOF 평행형이라 E §1.4 "7자유도 팔 + 평행 그리퍼" 가정과 한 팔 기준으로 그대로 맞습니다.

### 3.5 잔차 R의 힘 입력
- **손목 F/T 센서가 없습니다.** R 입력의 "힘/토크"는 **관절 `effort`(Present Current 기반)와 그리퍼 전류**로 바꿔 적어야 합니다.
- CR-DAgger 근거는 손목 F/T 기준이라 **근거가 한 단계 약해집니다**(설계 문서에 표기).
- [제안] 절제 조건 R-noforce를 추가합니다. 시뮬에서는 관절 토크에 전류 잡음 모델을 씌웁니다 [가정].
- 선택지: 손목 F/T 추가 장착. 기계 인터페이스는 [미확인]입니다.

### 3.6 GT 생성용 시뮬
- **AI Worker Isaac 모델이 공식으로 있습니다**(cyclo_lab, Isaac Sim 5.1 / Isaac Lab 2.3).
  - **RoboDojo와 시뮬 판본이 같습니다**(EVAL 표: "Isaac Sim 5.1 + Isaac Lab 2.3"). 같은 설치에서 두 로봇을 돌릴 수 있습니다.
- [제안] E0–E3와 R·B의 GT 생성 장면인 "단일 팔 자작 장면"을 **FFW-BG2 한 팔(7자유도 + RH-P12-RN)**로 고정합니다. 문서의 요구 조건과 정확히 일치하고, 실물 E-real까지 같은 로봇이 됩니다.
- 카메라는 cyclo_lab 단안 카메라 대신 **Stereolabs ZED Isaac Sim 확장**(zed-isaac-sim 29★)의 `ZED_M` 디지털 쌍둥이를 붙입니다.
  - 원문: "Every ZED camera as a calibrated digital twin", "Ground-truth depth streaming", "ZED Sim2Real … (experimental)", Camera Model 목록에 `ZED_M` 포함.
  - 오라클은 렌더러 GT 깊이를 쓰고, 인식 조건은 스트리밍 경로로 ZED SDK 깊이나 Fast-FS를 씁니다.
- 원문 주의: "Only the streaming path involves the ZED SDK and its stereo-matched depth; the other two deliver Isaac Sim's ground-truth renderer depth."
- 데이터 경로: cyclo_lab Mimic → `isaaclab2lerobot.py` → LeRobot. §33의 도메인 무작위화는 우리가 추가합니다.
- 액추에이터 게인은 cyclo_lab 값(stiffness 600 등)이 실물 서보와 같다는 근거가 없습니다. 실물 계단 응답으로 다시 맞춥니다 [가정].

### 3.7 RoboDojo와의 불일치와 정합 방안
- RoboDojo 원문(arXiv 2607.04434 HTML):
  - 시뮬: "ARX X5 bimanual platform, with the two arm bases separated by 0.6 m"
  - 실물: "ARX X5, Piper, and Piper X"
  - 카메라: "one head camera and two wrist cameras"(RGB)
- 우리 EVAL 표: 팔 6축 ×2, 480×640, 25 Hz, 깊이·행렬은 설정으로 켤 수 있음.
- **AI Worker는 RoboDojo 지원 로봇이 아닙니다.** 새 로봇 추가 절차에 대한 원문 언급도 없습니다.
- [제안] 3층으로 나눕니다.
  1. **결정 층 비교(주장 H2·H3, RD 낙폭) = RoboDojo-Sim ARX X5 그대로.** 공개 수치(π0.5, Astra, GPT-as-Policy)와 같은 열로 비교하려면 로봇을 바꾸면 안 됩니다.
     - M1은 트랙 D로 시뮬 깊이를 씁니다. 보조로 **"트랙 D-stereo"** 를 둡니다: 머리 카메라 옆 63 mm에 가상 카메라를 하나 더 두어 스테레오 쌍을 렌더링하고, AI Worker와 **같은 Fast-FS/M1 코드 경로**를 씁니다. 표에 "입력 다름"을 표기합니다.
  2. **개발·GT·모듈 실험(E0–E3, E-M4, E-R·E-AE) = cyclo_lab FFW-BG2 + ZED_M 쌍둥이**, Isaac 5.1.
  3. **E-real = 실물 AI Worker**(ZED Mini + D405, ROS 2 Jazzy, 100 Hz JTC).
     - 결정 층·술어 등록부·Jev/Astra 계약은 로봇과 무관하게 공유합니다.
     - 스킬·M5 한계·R은 로봇별로 둡니다. 논문에는 "결정 층은 두 로봇에서 같은 코드, 실행 층은 로봇별"이라고 적습니다.
- 위험 1: 7축과 6축, 머리 이동 유무, 베이스 간격이 다르므로 **스킬 이식 비용이 두 벌**입니다(RoboDojo 이식은 이미 [가정: 미구현]).
- 위험 2: 논문 제출 2026-11-16까지 약 7주라 **E-real은 최소판**을 권합니다.
- 결정할 것(주 세션에 올릴 것):
  - (a) E0–E3 장면을 FFW-BG2로 바꿀지(권장)
  - (b) RoboDojo 트랙 D-stereo를 둘지
  - (c) 실물을 BG2로 할지 SG2 베이스 고정으로 할지
  - (d) R의 힘 입력을 전류로 바꾸는 것과 F/T 추가 장착 중 무엇으로 할지

---

## 확인 못 한 것 [미확인]
- ZED Mini 지연과 Orin에서의 ZED Mini NEURAL FPS
- Fast-FS의 Orin 실측
- DYNAMIXEL-Y 프로파일 레지스터의 단위와 시간 기반 여부
- D405와 D401 이름 차이
- SH5 손의 판매 상태
- HF 데이터의 보정값과 라이선스
- S2M2와 LAS2의 별 수

---

## 주요 출처
- https://ai.robotis.com/ai_worker/hardware_ai_worker.html
- https://docs.robotis.com/docs/systems/aiworker/imitation_learning/ (하위 페이지 data_recording, model_training)
- https://github.com/ROBOTIS-GIT/ai_worker (187★): 설정 yaml, xacro, URDF
- https://github.com/ROBOTIS-GIT/cyclo_lab (145★)
- https://github.com/ROBOTIS-GIT/robotis_mujoco_menagerie (74★)
- https://github.com/ROBOTIS-GIT/physical_ai_tools (145★)
- https://huggingface.co/ROBOTIS (데이터 7개, 모델 6개)
- https://docs.stereolabs.com/docs/products/cameras/zed/specifications.md
- https://docs.stereolabs.com/docs/development/zed-sdk/modules/depth-sensing/depth-modes.md
- https://docs.stereolabs.com/docs/integrations/isaac-sim.md
- https://docs.stereolabs.com/docs/integrations/isaac-sim/sdk-free-depth-capture.md
- https://arxiv.org/abs/2512.11130 (Fast-FoundationStereo) / https://github.com/NVlabs/Fast-FoundationStereo (1,497★)
- https://arxiv.org/abs/2606.24457 (Lite Any Stereo V2)
- https://arxiv.org/html/2607.04434 (RoboDojo)
