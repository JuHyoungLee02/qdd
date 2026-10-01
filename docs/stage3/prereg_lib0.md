# E-LIB0 — 본 35B 상위(무학습) LIBERO 시범 평가, π0.5와 같은 조건 비교 (사전 등록)

- 작성: LIB0 에이전트, 2026-10-01 21시대 KST. **결과를 보기 전에** 커밋한다(커밋 시각 = 등록 시각).
- 사용자 원문(10-01 21시경 KST): "일단 지금 버전에서 그걸 그냥 검증만 해볼까/ 성능이 어느정도나오는지를 pi0.5하고 동일로 비교를 해볼 수 있으면 좋을 것 같아"
- 성격: **시범(보고 전용)**. 채택·기각 판정은 없다. 수치와 신뢰구간만 적는다.
- 무료다. 유료 API·Astra·교사 정책은 쓰지 않는다. LIBERO 데이터로 학습하지 않는다(우리 팔).
- 결과 루트: `/data/harvest/out/lib0/`. 영상: `/data/harvest/videos/lib0/`. 코드 사본: `/data/harvest/code_lib0_<커밋>`.

## 1. 팔 (같은 과제·같은 초기 상태·같은 편 수)

| 팔 | 모델 | LIBERO 학습 | 역할 |
|---|---|---|---|
| **A (우리)** | 본 35B **ep2.5** 병합본(`/data/harvest/out/main35/merged_ep2.5`), vLLM BF16, 사고 끔 | 없음 | 주 비교 |
| **B (π0.5 base)** | openpi `pi05_base` 가중치 + `pi05_libero` 설정(입력 변환·LIBERO 행동 정규화 통계) | 없음 | 주 비교 |
| R (참고) | openpi `pi05_libero` 체크포인트 | **있음(LIBERO 미세조정)** | 참고 줄. A·B와 학습 조건이 다르다 |

- **체크포인트를 ep2.5로 고른 이유**: 본 35B 사전 등록(prereg_main35)의 고르기 규칙(보류 검증 실패율 최소, 0.2159)이 고른 최종 체크포인트이고, 사용자가 말한 "지금 버전"이다. ep1.5는 E-CL15 폐루프 10편에서만 쓴 것이고 등록된 고르기 결과가 아니다. LIBERO 결과를 보고 바꾸지 않는다.
- B의 정규화 통계: base 체크포인트에는 LIBERO 행동 통계가 없다. 그래서 `pi05_libero` 체크포인트의 `assets/physical-intelligence/libero/norm_stats.json`(LIBERO 데이터 통계, 학습 가중치 아님)을 base 가중치 옆에 둔다. 이것 말고 LIBERO 정보는 B에 들어가지 않는다.
- B·R 실행 경로: openpi 공식 LIBERO 예제(`examples/libero/main.py`)와 같다. 서버 `scripts/serve_policy.py policy:checkpoint --policy.config pi05_libero`, 클라이언트는 같은 전처리(180° 회전, `resize_with_pad` 224, 상태 = eef 위치 + 축각 + 집게 2축)와 같은 `replan_steps 5`, `num_steps_wait 10`, 묶음별 `max_steps`(Spatial 220, Object 280, Goal 300, Long 520)를 쓴다. 다른 점은 영상 저장(agentview + 손목)과 호출 지연 기록뿐이다.

## 2. 우리 팔 A의 실행기 (E-CL15와 같게, LIBERO에 맞춘 것만 적음)

- 실행기 클래스: E-CL15와 같은 `with_loop_break(LimitEpisode)`이다. d-min 형식, 점 기억(mem_points), 기존 LoopGuard(fix_loop), 반복 끊기(`--loop-break --stall-n 3`)를 쓴다. 호출 30회·동작 120 s에서 끊고, 프롬프트에 적는 한도(40회·180 s)는 그대로 둔다.
- **자기 점검 슬롯**(assessment)과 '직전 명령과 결과' 줄 형식은 학습 그대로다.
- **입력 영상**: 머리 자리(image 1) = LIBERO `agentview`를 512×512로 렌더하고, 학습 때처럼 TCP 원만 그린다. 손목 자리(image 2) = `robot0_eye_in_hand` 256×256이다. 영상은 카메라가 실제로 보는 방향(OpenGL 세로 뒤집기만 되돌림)이다.
- **프롬프트**: 학습 형식(d-min) 본문은 그대로 둔다. 코드가 채우는 칸만 LIBERO 값으로 바꾼다.
  - 바꾸는 칸: 작업 상자 x·y, 머리 카메라 크기·자세, NOW(손목 카메라 자세·TCP·집게 간격·호출/시간), 닫힘 폭, 과제 문장, 성공 문장, 물체 목록.
  - 물체 목록: BDDL의 관심 물체(`obj_of_interest`)는 "(task object)", 나머지 물체와 탁자 아닌 가구는 "(obstacle)"로 적는다. 학습 때의 "옮길 물체 / 놓을 곳" 구분은 문장 해석이 틀릴 수 있어 쓰지 않는다. 이름은 BDDL 이름에서 번호와 밑줄을 뺀 것이다(예: `akita_black_bowl_1` → "akita black bowl").
  - 성공 문장(새 문구): "Success = what the TASK sentence asks is done (the simulator checks it). Then answer stop."
  - **고정 문구는 학습 그대로**다: 로봇 이름(AI Worker), 패드 길이 4.5 cm, 열림 폭 10.7 cm, 닫힘 축. Franka와 다르다. 이것은 한계로 적는다.
- **점 → 3D 목표**: agentview 깊이 렌더(MuJoCo z-버퍼 → 미터 z-깊이)와 카메라 내부 파라미터(fovy, 정사각 화소), 외부 파라미터(카메라 자세 → 로봇 바닥 좌표)로 E-CL15와 같은 변환기(`resolve.py`)를 쓴다. 바꾼 것은 둘이다.
  1. 로봇 자신 화소는 분할 렌더로 깊이에서 뺀다. L8S 전용 높이 규칙(`robot_mask`, 10.5 cm)은 끈다. LIBERO에는 그보다 높은 가구가 있기 때문이다.
  2. 탁자 높이 사전값은 첫 관측의 깊이 점 높이 최빈값(5 mm 칸)으로 정한다. 실행 중에는 매 호출 깊이에서 다시 잰다.
- **로봇 제어**: LIBERO/robosuite 기본 제어기 `OSC_POSE`(델타, 20 Hz)를 쓴다.
  - 최소 저크 직선 실행기(8 cm/s, 도착·정착·막힘 규칙 같음)가 낸 매 걸음 TCP 기준점과 지금 TCP의 차이를 OSC 위치 입력(÷0.05 m, ±1로 자름)으로 넣는다.
  - 자세는 시작 자세를 유지한다. 집게는 닫기 +1, 열기 −1이다.
- **작업 상자**: 모델을 돌리기 전에 `tools/lib0/box.py`로 40과제(k=0)의 모든 BDDL 물체 위치를 로봇 바닥 좌표로 쟀다(물체 xy 최소 (0.242, −0.323), 최대 (0.798, 0.340)). 여유 5 cm를 두고 5 cm 단위로 바깥 반올림해 **x 0.15–0.85, y −0.40–0.40 m**로 고정했다. z는 학습과 같다(탁자 위 2.5–40 cm).

## 3. 범위와 시드 (결과 전 고정)

- 묶음 4개: LIBERO-Spatial·Object·Goal·Long(libero_10), 묶음마다 과제 10개.
- **과제마다 5편**: LIBERO 표준 초기 상태 0–4번이다. `env.seed(7)`, `reset` → `set_init_state` → 빈 행동 10걸음으로 openpi와 같다. 팔 3개 모두 같은 편을 쓴다.
- 팔마다 200편이고, 세 팔이면 600편이다.

## 4. 판정·지표 (보고 전용, 결과 전 고정)

- **성공**: LIBERO `_check_success()`가 참이 된 첫 걸음에서 끝낸다. openpi의 `done`과 같고, 유지 시간은 없다.
- **성공률과 Wilson 95 % 구간**을 묶음별과 전체로 낸다.
- **A − B 짝 차이**: 같은 편끼리 짝을 짓는다. 과제 단위 부트스트랩 10,000회로 95 % 구간을 낸다.
  - 차이 ≥ +10 %p이고 구간 하한 > 0이면 'A 우위'라고 적는다. 반대 방향으로 같은 조건이면 'B 우위'다. 나머지는 '구분 안 됨'이다.
  - 시범이므로 채택 판정은 아니다.
- **시간 예산이 다르다**. A는 학습 실행기 한도(30호출·120 s)를 쓰고, B·R은 openpi `max_steps`를 쓴다.
  - 보조 지표로, A가 openpi 걸음 예산(대기 10걸음 뒤 `max_steps` × 0.05 s) 안에 성공한 비율을 함께 적는다.
  - 두 팔 모두 모델이 생각하는 동안 시뮬은 멈춘다.
- **실패 유형**:
  - A: 실행기 기록(`end_reason` × `fail_stage`)을 센다. `stage_cap_calls`, `stall`, `stop`(틀린 멈춤), `schema`, `stage_cap_motion`, `off_table`이고, 단계는 집기 전/집은 뒤/놓은 뒤다.
  - B·R: `max_steps` 시간 초과와 예외로 나눈다.
  - 상위 3개를 보고한다.
- **지연**:
  - A: 호출당 vLLM 왕복 시간(중앙·p90), 편당 호출 수, 편당 벽시계.
  - B·R: 추론 1회(청크)당 웹소켓 왕복 시간, 편당 벽시계.
- **영상**: 모든 편을 10 fps mp4로 남긴다(agentview | 손목, 원본 방향). 대표 성공·실패 몇 편은 노트북 `D:\tools\pdf_out\lib0_videos\`로 가져온다.

## 5. 자체 검사 (실험 전·도중·끝)

- **G0 환경 검사**: R(공식 체크포인트)을 libero_spatial 과제 10개 × 1편으로 먼저 돌린다.
  - 8/10 미만이면 멈춘다. 공개 수치는 98.8 %이므로, 그 아래면 시뮬 설치가 공식과 다르다고 보고 원인을 찾는다.
  - 통과해야 B·A를 돌린다.
- **G1 기하 검사(A)**: 등록 전에 모델 없이 했다(`box.py`, 40과제 k=0).
  - TCP 원이 agentview 위 집게에 그려지는지 프레임으로 봤다. 통과(libero_goal 0번 그림).
  - 관심 물체 몸체 원점을 화소로 투영하고 변환기에 넣어 얻은 xy를 시뮬 참값과 비교했다. 참값은 이 검사에만 쓰고 모델 입력에는 넣지 않는다.
  - 결과: 묶음별 중앙 6.3 / 6.7 / 11.7 / 11.9 mm(Spatial/Object/Goal/Long). 통과 기준은 중앙 ≤ 20 mm다.
  - 큰 오차(최대 229 mm)는 몸체 원점이 보이는 물체 중심과 다른 큰 가구(전자레인지·캐비닛)와, 원점이 밑바닥이라 투영 화소가 가장자리에 걸리는 키 큰 병에서 나왔다. 변환기 오류가 아니다.
- **G2 형식**: A 첫 10편의 출력 형식 오류율을 본다. 50 %를 넘으면 멈추고 원인을 적는다. 형식 오류는 모델 실패로 센다.
- 도중: 레인 로그 진전이 30분 없으면 그 레인을 멈춘다. 끝: 편 수(팔마다 200)와 영상 수가 맞는지 본다.

## 6. 자원 배치 (메인 위임 "묻지 말고 알아서 최적으로")

- A 서버: vLLM, **7a2a GPU2**(평가 카드, 서빙만)에 메모리 0.6으로 둔다. E-CL15와 같은 자리다.
- B·R 서버: openpi JAX, **x3 GPU0**에 둔다(`XLA_PYTHON_CLIENT_MEM_FRACTION` 0.3, 서버 두 개). `vla/GPU_WANTED`에 FUT1·LIB0 표시 없는 `x3:0` 줄이 생기면 편 사이에 비킨다.
- 시뮬: MuJoCo **CPU(OSMesa)**로 **78dc CPU**에서 돌린다(메인 확인 10-01 21:5x). GPU는 쓰지 않는다. 78dc 0–3은 E-VB1 학습 카드다.
  - 레인은 최대 12개, `nice 10`이다. 7a2a CPU는 L9 양산 몫이라 쓰지 않는다. L9 렌더 카드(7a2a 0·1·3)·x2도 쓰지 않는다.
  - 파드에 OSMesa가 없어 conda-forge `mesalib<25`를 /data 아래에 둔다(25부터 OSMesa가 빠졌다). `opencv-python`은 headless 판(같은 4.6.0.66)으로 바꾼다.
- 멈춤: `touch /data/harvest/out/lib0/STOP`(편 사이에 멈춤).

## 7. 라이선스 (2026-10-01 확인)

| 대상 | 라이선스 | 비고 |
|---|---|---|
| LIBERO 코드·BDDL·자산·초기 상태(Lifelong-Robot-Learning/LIBERO, 스타 약 2.4천) | MIT | openpi 서브모듈 f78abd6 |
| LIBERO 데이터 | HF `physical-intelligence/libero` CC BY 4.0, `yifengzhu-hf/LIBERO-datasets` Apache-2.0 | 우리는 내려받지 않는다. R은 PI가 이것으로 학습했다. |
| robosuite 1.4.1 | MIT | |
| MuJoCo 3.2.3 | Apache-2.0 | |
| openpi 코드(Physical-Intelligence/openpi, 스타 약 1.4만) | Apache-2.0 | 예제 실행 경로를 따른다 |
| π0.5 가중치(pi05_base, pi05_libero) | Gemma Terms of Use | 내부 비교 기준선으로만 쓴다. 가중치·파생물은 배포하지 않고 점수만 싣는다(사용자 10-01 05:15 "a 묻지말고 고 앞으로 5시간간", user-log 227) |
| 본 35B(Qwen3.5-35B-A3B 기반) | Apache-2.0 기반 + 우리 LoRA | |

- NOW §4의 '3인칭 금지'는 학습 데이터 규칙이다. 이번에는 평가 입력으로만 agentview(3인칭)를 머리 자리에 넣는다(사용자 과제 지시). 학습에는 쓰지 않는다.

## 8. 한계 (미리 적음)

- A는 머리 시점 데이터만 학습했고, 3인칭 agentview·Franka·LIBERO 물체는 처음 본다. 프롬프트 고정 문구(로봇 이름·집게 치수)도 Franka와 맞지 않는다.
- A의 명령은 위에서 잡기 + 직선 이동뿐이다. 서랍 열기·밀기·켜기(Goal·Long 일부)는 edit 명령으로만 할 수 있다.
- 편 수가 과제당 5편, 묶음당 50편이라 구간이 넓다(±14 %p 안팎).
- 렌더 해상도가 팔마다 다르다. A는 512/256(자기 학습 해상도에 가깝게), B·R은 224(openpi 공식)다.

## 변경 기록
- (규칙 변경 없음.) 결과: `docs/stage3/results/lib0.md`(2026-10-01 22:47 KST).
- **변경 2 — E-LIB0b (A 결과를 본 뒤, 새 팔 실행 전; 2026-10-01 23시경 KST)**: 메인 결정(근거: '버리기 전 재검증' 규칙). 학습 없이 어댑터만 고친다. 같은 200편·같은 초기 상태·같은 서버(ep2.5, 7a2a GPU2)·같은 실행기 한도로 **A만 다시** 돌려 팔 이름 **Ab**로 둔다. B·R은 기존 결과를 그대로 쓴다. 판정·지표는 4절 그대로다. 보고는 A·Ab·B·R 나란히, A−B 짝 비교는 변경 없이 내고, Ab−B도 같은 규칙으로 함께 적는다.
  - 바꾼 목록(Franka 실측: `tools/lib0/franka_geom.py`, `franka_mesh.py`, 시작 자세):
    1. **패드 간격 척도**: 코드가 보고·판단에 쓰는 모든 간격(NOW·이력·잡음 판단·반복 끊기)을 Franka 간격 × 10.7/8로 바꾼다. 그래서 다 연 Franka(약 7.7–7.9 cm)는 약 10.4–10.6 cm로 보인다. 프롬프트 고정 문구 '완전히 연 패드 간격 10.7 cm'는 이 척도에서 맞는 값이라 그대로 둔다.
    2. **닫힘 폭**(코드가 채우는 칸): 0 → 아무것도 없이 닫았을 때의 실측 0.18 cm × 10.7/8 = 0.24 cm(문구 "ends near 0.2 cm").
    3. **z 바닥**: 탁자 + 2.5 cm → **탁자 + 1.2 cm**. Franka 손끝은 TCP 아래 1.0 cm이고, 학습 때 틈(AI Worker 2.5 − 2.25 = 0.25 cm)을 그대로 둔다. 위 끝 40 cm는 그대로다.
    4. **집게 문구**(학습 고정 문구 → Franka 실측): '닫힘 축 x' → **y**, '패드 4.5 cm(TCP 위 2.25 ~ 아래 2.25 cm)' → **1.7 cm(위 1.2 ~ 아래 0.5 cm)**, '+ 손끝은 TCP 아래 1.0 cm', '집게 몸통은 TCP 위 2.5 cm부터' → **3.0 cm부터**.
    5. **로봇 이름 문장**: "You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation." → "You control a robot arm (Franka Emika Panda) at a table, in simulation."
  - 그대로 둔 것: 높이 의도 수치(above 8 cm, grasp 위 끝 아래 2 cm, place 1 cm, lift 22 cm)는 모델의 명령 정의라서 바꾸지 않는다. 작업 상자 x·y(변경 1, 이미 Franka 실측)도 그대로다. 영상 표식 'RIGHT wrist'는 답 형식(`right_wrist`)과 묶여 있어 그대로 둔다. 속도 8 cm/s, 도착·정착 규칙도 그대로다.
  - 결과 루트는 같은 `/data/harvest/out/lib0/Ab/`, 영상은 `/data/harvest/videos/lib0/Ab/`, 코드 사본은 새 커밋으로 둔다.
