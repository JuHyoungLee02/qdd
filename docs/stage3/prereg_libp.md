# E-LIBP — LIBERO-Plus 섭동 강건성 시범: 본 35B(무학습) 대 π0.5-LIBERO·π0·π0-FAST 공식 (사전 등록, 보고 전용)

- 작성: LIB0 에이전트, 2026-10-02 03시대 KST. **결과를 보기 전에** 커밋한다.
- 근거:
  - 사용자 원문(10-02 03시대) "pi0.5 … 다른거랑 비교하면서 내놨던걸 … 진짜 여러개를 다 비교"
  - 메인 순서(② LIBERO-Plus, 시점·조명 강건성)
  - 공개 비교: LIBERO-Plus 논문(arXiv 2510.13626)의 π0·π0-FAST 공식 가중치 섭동별 수치
- 벤치: LIBERO-plus(github sylvestf/LIBERO-plus 4976dc3, HF 카드 MIT, 별 469).
  - 섭동 7종: 카메라 시점, 로봇 초기 상태, 언어, 조명, 배경, 센서 노이즈, 물체 배치. 과제는 10,030개다.
  - 공식 평가는 과제당 1편이다(`num_trials_per_task = 1`).

## 범위 (결과 전 고정)
- `task_classification.json`의 묶음 4개(spatial 2,402·object 2,518·goal 2,591·10 2,519과제) × 범주 7개마다 **5과제**를 sha256("libp|<묶음>|<과제 이름>") 오름차순으로 고른다. 과제당 1편, 초기 상태 0번이다. 팔마다 **140편**이다(`tools/lib0/libp_jobs.py` → `/data/harvest/out/libp/jobs.txt`, `meta.json`).
- 환경 구성과 대기 10걸음, max_steps는 E-LIB0와 같다(openpi `examples/libero/main.py`, `env.seed(7)`).

## 팔
- **Ab** = 본 35B ep2.5, E-LIB0b 어댑터(Franka 실제 설정값, 잡기 규칙 없음, prereg_lib0 변경 4). LIBERO 공식 설정이다.
- **R** = `pi05_libero`, **P0** = `pi0_libero`, **PF** = `pi0_fast_libero`. 모두 LIBERO 미세조정 공식 체크포인트이고, 섭동 데이터로는 학습하지 않았다.
- B(π0.5 base 무학습)는 정보가 적어 뺀다(메인 원칙).
- **센서 노이즈 범주**: LIBERO-plus는 env `step`에서 agentview RGB에만 흐림·안개 등을 입힌다(256 px 관측). 우리 팔은 머리 영상을 직접 렌더하므로, 같은 함수와 같은 강도를 우리 512 px 머리 RGB에 입힌다(`LiberoWorld._plus_noise`). 깊이는 LIBERO-plus가 손대지 않으므로 우리 깊이도 깨끗하다. 이 점은 우리 팔에 유리할 수 있는 한계로 적는다. LIBERO-plus에서는 노이즈 처리 때문에 env 카메라 관측을 켠다.
- 우리 팔은 시뮬에서 카메라 내·외부 파라미터를 매번 읽으므로, 시점 섭동에서도 점 → 3D 변환은 맞는 기하를 쓴다. 이것은 '모델이 아닌 로봇 실제 설정값' 쪽이다. 결과 해석에 적는다.

## 지표
- 범주별 성공률(Wilson 95 %), 팔 사이 짝 차이(같은 과제, 과제 부트스트랩)를 낸다. 그리고 섭동 없는 기준(E-LIB0 같은 묶음 성공률) 대비 하락폭을 낸다.
- 공개 수치(LIBERO-Plus 표 π0: 카메라 15.8 / 로봇 6.6 / 언어 61.0 / 조명 79.6 / 배경 78.5 / 노이즈 79.4 / 배치 70.4)는 참고 줄이다. 전체 10,030과제 기준이라 우리 표본과 다르다.

## 자원
- 서버: x3 GPU0(R·P0·PF), 7a2a GPU2(35B). 시뮬: 78dc CPU(OSMesa).

## 변경 기록
- 변경 1 (결과 뒤, 절차 버그만): Ab 센서 노이즈 2편(t1679, t1722, libero_spatial·goal의 zoom/glass 계열)이 노이즈 함수가 256 px를 가정해 512 px 영상에서 오류로 끝났다(error.json). 그 함수만 256 px로 줄여 노이즈를 입힌 뒤 다시 키우게 고치고, 이 2편만 다시 돈다. 나머지 편과 판정은 그대로다.
