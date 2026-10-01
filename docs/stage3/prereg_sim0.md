# E-SIM0 — 본 35B(무학습) SimplerEnv Google Robot 시범, π0.5와 같은 조건 비교 (사전 등록)

- 작성: LIB0 에이전트, 2026-10-02 01시대 KST. **결과를 보기 전에** 커밋한다.
- 사용자 원문(10-01 23시경 KST): "음 심플이엔브이등 pi0.5와 비교할 수 있는것들 다 해보고 난다음에 최종적으로 리베로 미세조정하고 이런거 있어야할 것 같은데" (user-log 238). 메인 결정은 10-02 00시대에 내려졌다(1순위 SimplerEnv Google Robot).
- 성격: **시범(보고 전용)**, 무료, 학습 없음. 판정과 지표는 E-LIB0(prereg_lib0.md §4)과 같다.
- 결과 `/data/harvest/out/sim0/`, 영상 `/data/harvest/videos/sim0/`, 코드 `/data/harvest/code_sim0_<커밋>`.

## 1. 왜 Google Robot인가
- SimplerEnv(MIT, 별 1.2k)의 Google Robot 카메라 `overhead_camera`는 로봇 머리 링크 `link_camera`에 붙어 있다(640×512, fx = fy = 425). 우리 원칙(로봇 몸에 고정된 머리 시점)과 맞는다.
- **손목 카메라는 없다.**

## 2. 팔

| 팔 | 모델 | 이 벤치 학습 | 역할 |
|---|---|---|---|
| **A (우리)** | 본 35B ep2.5(병합본), vLLM, 7a2a GPU2 | 없음 | 주 비교 |
| **B (π0.5 base)** | openpi `pi05_base` 가중치, 무학습 | 없음 | 주 비교 |
| 참고 | 공개 수치: π0.5 Fractal 미세조정 VM(StarVLA arXiv 2604.05014 표, 학습자 미확인), π0 Fractal(arXiv 2602.12684 표), RT-1(SimplerEnv 논문) | 있음 | 참고 줄 |

- A 어댑터는 E-LIB0c와 같은 원리를 쓰고, **처음부터 Google Robot 실측값**을 넣는다. 실측은 시범 전에 `tools/sim0/robot_geom.py`로 하고 변경 1에 적는다.
  - 집게 열림·닫힘 폭과 척도: 학습 척도 ×10.7/열림 폭.
  - 닫힘 축, 패드·손끝·몸통의 TCP 기준 높이.
  - z 바닥 = 손끝 + 0.25 cm.
  - 작업 상자 x·y: 이 시범 장면들의 물체 위치 + 5 cm.
  - 로봇 이름 문장: "a robot arm (Google Robot)".
  - 테두리 잡기(빈 물체)는 켜 둔다. 콜라 캔·물병은 빈 물체로 판정되지 않을 것이다.
- **손목 자리**: A의 image 2에는 회색 빈 영상을 넣고, NOW 끝에 "NOTE: this robot has no wrist camera: image 2 is blank."를 붙인다. B·RT-1과 같은 센서를 쓰기 위해서다.
- 머리 깊이와 로봇 분할은 SimplerEnv `rgbd` 관측(depth, Segmentation)과 `camera_param`(intrinsic_cv, extrinsic_cv)을 쓴다. 로봇 바닥 좌표는 `agent.base_pose` 기준이다.
- **제어**: SimplerEnv 표준 Google Robot 설정을 그대로 쓴다(제어 3 Hz, sim 513 Hz, `arm_pd_ee_delta_pose_align_interpolate_by_planner` + 집게 `..._target_delta_pos_interpolate_by_planner`).
  - A의 최소 저크 기준점을 3 Hz 걸음마다 EE 델타로 넣는다. 자세는 시작 자세를 유지한다.
  - 집게는 멈출 때까지 기다린다(E-LIB0b 2b와 같고, 최대 10 s).
- **B 입출력**: openpi `pi05_libero` 형식을 그대로 쓴다.
  - 입력: image = 머리 영상(openpi `resize_with_pad` 224), wrist = 0 영상, state = TCP 위치(로봇 바닥 좌표) + 축각 + 집게 2축, prompt = 과제 문장.
  - 행동 7차원(EE 델타 xyz, 델타 회전, 집게)을 RT-1·Octo SimplerEnv 래퍼와 같은 변환으로 env 행동으로 바꾼다.
  - 정규화 통계는 Google Robot 데이터(fractal) 행동 통계다. Octo 공개 `dataset_statistics.json`(MIT)에서 가져온다.
  - 학습 가중치에는 이 통계 말고 Google Robot 정보가 들어가지 않는다(E-LIB0 B와 같은 원칙).
  - replan 5걸음으로 openpi LIBERO와 같게 한다.
- **렌더**: SAPIEN 2.2.2는 파드 NVIDIA Vulkan에서 촬영이 멈춘다(78dc·x3·7a2a에서 확인). 그래서 모든 팔이 **CPU Vulkan(Mesa lavapipe)**으로 렌더한다. 시뮬은 78dc CPU에서 돈다(검증 묶음).

## 3. 범위 (결과 전 고정)
- **pick coke can, visual matching**: 표준 스크립트 `rt1_pick_coke_can_visual_matching.sh`와 같은 장면·오버레이를 쓴다. 방향 3개(lr_switch, upright, laid_vertically) × 물체 위치 5×5 = **75편**이다. URDF 변형은 기본(None)만 쓴다(표준은 4종을 평균).
- **move near, visual matching**: 표준과 같은 장면이고 편 0–59 = **60편**이다. URDF는 None만 쓴다.
- 서랍 과제(open/close, put in drawer)는 표준 VM이 광선 추적 렌더를 쓰는데 lavapipe에 없다. 그래서 이번에는 뺀다.
- 걸음 한도: B는 표준 `max_episode_steps`(80)을 쓴다. A는 학습 실행기 한도(30호출·120 s)를 쓰고, 보조 지표로 80걸음(26.7 s) 안 성공률을 낸다.
- 팔마다 135편이다. 성공 판정은 env `success`(표준)이고, pick coke can은 들어 올려 유지하는 표준 조건이다.

## 4. 판정·지표
- E-LIB0 §4와 같다. 과제별 성공률(Wilson 95 %), A−B 짝(같은 편, 과제 안 편 부트스트랩 10,000회), 실패 유형, 호출 지연을 낸다.
- 참고 줄의 공개 수치는 URDF 4종 평균·광선 추적 조건이라 우리 시범과 조건이 다르다고 표시한다.

## 5. 자체 검사
- **G0**: B 대신 공개 기준인 RT-1이 없으므로 환경 검사는 A·B 없이 한다. 대본 정책(물체 참값 위치로 내려가 잡고 드는 규칙, 시뮬 참값은 이 검사에만 쓴다)으로 pick coke can upright 5편을 돌려 4편 이상 성공하면 통과다. 제어·집게 연결을 확인하는 검사다.
- **G1**: E-LIB0와 같은 방식으로 변환기 xy 오차(콜라 캔 중심, 시뮬 참값 비교)를 잰다. 중앙 ≤ 20 mm여야 한다.
- **G2**: A 형식 오류율 50 % 미만이어야 한다.

## 6. 라이선스
- SimplerEnv·ManiSkill2_real2sim은 MIT, SAPIEN 2.2.2는 MIT(미확인 시 Apache-2.0)다. 실사 오버레이 그림은 SimplerEnv 저장소에 들어 있다.
- π0.5 가중치는 Gemma 약관이고 내부 기준선으로만 쓴다(E-LIB0와 같음). Octo 통계 파일은 MIT다.

## 변경 기록
- **변경 1 (시범 전, 모델 결과 없음; 2026-10-02 01시대 KST)**: 실측값과 G0/G1 결과를 적는다(`tools/sim0/robot_geom.py`, `track_dbg.py`, `harvest/sim0/run_a.py --g0`).
  - Google Robot 집게:
    - 손가락은 base x 방향으로 닫힌다.
    - 다 열린 손톱 링크 간격은 21.8 cm이고, 학습 척도에서 10.7 cm로 보이도록 × 0.107/0.218로 바꾼다.
    - 닫으면 두 손끝이 TCP(`link_gripper_tcp`)에서 만난다. 가장 낮은 손가락 점은 TCP 높이이고, 손가락 길이는 약 11 cm, 몸통은 TCP 위 15 cm부터다.
    - 이 사실들을 집게 문구에 넣는다(run_a `TEXT_G`). z 바닥은 탁자 + 0.5 cm다.
  - **자세**: 학습 문구 '곧장 아래를 향함'에 맞추려고 시작 자세에서 곧은 아래 자세로 돌리면 표준 제어기의 IK가 풀리지 않는다(시험에서 로봇이 전혀 움직이지 않음). 그래서 시작 자세(수직에서 약 20°)를 유지하고, 문구를 "It points almost straight down (tilted about 20 degrees)"로 바꾼다.
  - 작업 상자: x 0.35–0.90, y −0.45–0.45 m(로봇 바닥 좌표), z 2.5 mm–40 cm 대신 0.5–40 cm다.
  - 테두리 잡기의 '열린 집게 폭'은 15 cm로 둔다(콜라 캔 6.6 cm는 빈 물체로 판정되지 않는다).
  - OBJECTS 줄: 장면 액터 이름(번호·밑줄 뺌)이다. 지시문에 이름 단어가 있으면 "task object", 없으면 "obstacle"이다.
  - **G0 통과**: 대본 정책으로 upright 캔 3/3(앞선 5편 판도 5/5)이다. 누운 캔은 대본 높이 규칙이 맞지 않아 실패하는데, G0 정의(upright)에 해당하지 않는다.
  - **G1 통과**: 변환기 xy 오차 2.3·2.9·3.1·7.7·14.4 mm, 중앙 3.1 mm다.
  - B 정규화 통계: Octo 공개 fractal 행동 통계에는 분위수가 없다. pi05 분위수 정규화용 q01/q99 = 평균 ∓ 2.326 표준편차를 min/max로 자른 근사를 쓴다(`tools/sim0/fractal_norm.py`). 상태는 pi05가 읽지 않으므로 0/1이다.
  - B 서버는 x3 GPU0 :8703(`serve_pi.sh G`)이다. 영상은 3 fps 머리 RGB(A·B 같음)다.
