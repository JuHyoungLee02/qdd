# E-RC0 — RoboCasa365 target 50과제 시범: 본 35B(무학습) 대 공식 π0.5 (사전 등록, 보고 전용)

- 작성: LIB0 에이전트, 2026-10-02 06시대 KST. **결과를 보기 전에** 커밋한다.
- 근거:
  - 사용자 원문(10-02 03시대) "pi0.5 … 다른거랑 비교하면서 내놨던걸 … 진짜 여러개를 다 비교"
  - 메인 결정(10-02 06시대): (나) RoboCasa365 먼저
  - 원칙: 지금 모델 그대로. 어댑터에는 로봇 실제 설정값만 넣는다.
- 벤치:
  - RoboCasa365 리더보드(robocasa.ai, 2026-04-02). 코드 robocasa(MIT), robosuite master(MIT), 자산 CC BY 4.0(혼합, 미확인).
  - 공식 π0.5 = HF `robocasa/robocasa365_checkpoints` `pi05_pretrain_human300/multitask_learning/75000`. RoboCasa 팀이 Human300으로 학습했다. 평가 코드는 robocasa-benchmark/openpi ca4c6d7 `examples/robocasa/main.py`(split target, replan 5, horizon = 과제 horizon × 1.5, seed 7)다.
  - 공개 수치: Atomic-Seen 39.6 / Composite-Seen 7.1 / Composite-Unseen 1.2(종합 16.9).

## 범위 (결과 전 고정)
- target 50과제(Atomic-Seen 18, Composite-Seen 16, Composite-Unseen 16) × **과제당 3편**(env 시드 7, `reset` 순서 1–3편째) = 150편/팔.
- 공식 평가는 과제당 50편이다. 시범이라 줄였고, 구간을 적는다.

## 팔
- **P = 공식 π0.5**: 공식 평가 경로 그대로, 서버 x3 GPU0 또는 7a2a GPU2.
- **A = 본 35B ep2.5**: 무학습, 서버 7a2a GPU2.
  - 로봇은 PandaOmron(이동 바닥 + 몸통 + Panda 팔)이다. 우리는 **팔만** 조종하고 바닥·몸통은 움직이지 않는다(상위 형식에 이동 명령이 없다).
  - 이동이 필요한 과제(NavigateKitchen 등)는 '해당 없음'으로 따로 적지만, 성공률 분모에는 넣는다(실패로 셈).
  - 머리 자리 = `robot0_agentview_left`(이동 바닥에 고정된 카메라), 손목 = `robot0_eye_in_hand`.
  - 집게·TCP·작업 범위·카메라는 RoboCasa 로봇 실측값을 쓴다(실측은 변경 1에 적는다). 제어는 RoboCasa 기본 컨트롤러의 팔 OSC 델타다.
  - E-LIB0b 어댑터(척도·집게 대기)와 같은 원리이고, 잡기 규칙은 없다.
- B(π0.5 base 무학습)는 넣지 않는다(정보가 적다, 메인 원칙).

## 지표
- prereg_lib0 §4와 같다. 묶음별 성공률(Wilson), A−P 짝 차이(과제 부트스트랩), 실패 유형, 지연을 낸다.

## 설치·스모크 기록 (결과 전)
- `/data/harvest/rc`: robocasa-benchmark/openpi ca4c6d7의 uv venv, robosuite·robocasa(master, `commits.txt`), 자산 23 GB, 체크포인트 42 GB.
- 설치 중 고친 것:
  - `av>=15`로 바꿈(lerobot이 av를 소스로 빌드하려다 실패)
  - numpy 2.2.5, OpenCV headless 4.11, huggingface-hub <1.0
  - numba JIT 끔(`NUMBA_DISABLE_JIT=1`: 배치 샘플러 컴파일 중 LLVM 세그폴트)
  - OSMesa 경로
- 서빙: `tools/rc0/serve_rc.py`. 설정의 학습 데이터 경로만 비운다. 정규화 통계는 체크포인트 assets에서 읽으므로 정책은 같다.
- 스모크 1편(PickPlaceCounterToCabinet k0, 결과 표에 넣지 않음): P는 시간 초과(1,125걸음, 487 s), A는 stall(8호출)이었다.
  - A 벽시계가 1,291 s였는데, 상태를 읽을 때마다 env가 카메라 3대를 다시 렌더한 탓이었다. 걸음마다 받은 gym 관측(같은 값)을 쓰도록 고쳤다.
- 로봇 실측(같은 Panda 손): TCP = `gripper0_right_grip_site`, 기준 좌표 = `robot0_base`(이동 바닥).
  - 팔 OSC는 입력 좌표계 base, 단위당 0.05 m / 0.5 rad이다(+1 × 5걸음에 x +5.2 cm).
  - 집게 간격 척도와 빈손 닫힘 폭은 E-LIB0b와 같다.
  - 작업 상자: x 0.15–0.85, y −0.45–0.45, z 1.2–40 cm(Panda 도달 범위, 바닥 기준).

## 변경 기록
- **변경 1 (A 결과를 본 뒤 — 어댑터 버그, 재실행; 2026-10-02 09시대 KST)**: RoboCasa의 `robot0_base` 몸체는 (10, 10, 0)에 있는 고정 자리표시자다. 우리 세계는 이것을 로봇 바닥 좌표로 써서, 카메라·깊이 점(x ≈ −10 m)이 TCP(env의 base_to_eef)와 다른 좌표계에 있었다. 그래서 첫 A 판은 150편 전부 목표가 작업 상자 밖으로 잘려 0/150이었다. 이 판은 **무효(v1)**로 `/data/harvest/out/rc0/A_v1`에 보존한다. 고친 코드는 env가 주는 이동 바닥 자세(`state.base_position/base_rotation`)를 쓴다(이것이 OSC 입력·TCP 관측의 좌표계다). 등록에 있던 G1 기하 검사를 첫 판 전에 하지 않은 절차 실수가 원인이다. `tools/rc0/geom_check.py` 결과: 빨대 5 mm, 조리대 방해물 17 mm로 통과했다. A만 같은 150편을 다시 돈다. P는 영향이 없다.
