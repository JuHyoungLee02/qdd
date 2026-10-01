# L9R 인계 — 로봇 프로필 층 · 머리 카메라 무작위화 · Franka 받침대 · L9 → d-min 빌드 (2026-10-02)

- 작성: L9R(다른 로봇 + E-HCAM8) 에이전트. 받는 쪽: **L9 v2 책임자**(L9 양산 에이전트, 사용자 10-02 01시대 "그냥 처음 하는 것처럼 다양한 로봇하고 다양한 환경 이런거 전부 다 가능하게 해줘야해").
- 이후 L9 생성기 코드는 L9 v2 책임자가 맡는다. **E-HCAM8의 H0·H1·H2 학습과 판정은 L9R이 계속 맡는다**(`docs/stage3/prereg_hcam8.md`).
- 근거 문서: 설계 `docs/superpowers/specs/2026-09-30-l9-diverse-datagen-design.md` §9(개정)·§9.1–9.3·§10.1, 사전등록 `docs/stage3/prereg_hcam8.md`(변경 1·2), 후보 표 `harvest/l9/assets9/robots_s9.json`, user-log 236·237.

## 1. 무엇이 있나 (파일)

| 파일 | 역할 | 기본 경로 영향 |
|---|---|---|
| `harvest/l9/robot9.py` | 로봇 프로필(`ffw_sg2` = 기존, `franka_mast`). Franka 정의 전부가 여기 있다. URDF 준비(메시 절대경로, `panda_link8` 관성, `panda_ee` 프레임, `<mimic>` 제거) → Isaac Lab `UrdfFileCfg`(내용 해시 이름의 URDF·USD, `/data/harvest/assets_l9r/franka/`). 그 밖에 이득(팔 400/80, 손가락 2000/100·70 N, 중력 켬), 손가락 폭↔관절(폭 = 2q, 최대 8 cm), 카메라 정의(머리 받침대 `panda_link0`, 손목 D405 `panda_hand`), 요청 문구 교체(`apply_prompts`). | 프로필을 줄 때만 쓰임 |
| `harvest/l9/hcam9.py` | 순수 기하. 표준·무작위·보류 기하 뽑기(작업면 위 0.35–0.80 m, 피치 30–62°, 가로 화각 65–95°; 보류는 한 축만 범위 밖), Franka 받침대 뽑기, 마운트 계산, `camera:` 줄(`line`, 높이 = 바닥 위). | 없음 |
| `harvest/l9/world9.py` | `make_world9(..., robot=, hcam=)`. 편마다 카메라 마운트(USD 로컬 자세)·내부값 쓰기를 하고, 표준 편 다음 표준 편이면 아무것도 쓰지 않는다. `_cam`은 그 편의 마운트를 쓴다. Franka 기저는 받침대 위(작업면 − U[0, 0.12] m), 기저 확인(1 cm). meta `head_cam`·`base`. | `robot="ffw_sg2", hcam=None` = 기존 |
| `harvest/l9/collect9.py`, `run9.py` | 행 필드 `robot`·`hcam`(작업당 하나), 실행 스위치 `HCAM_ON`(run 디렉터리 옆 → `hcam="coin"`, 편 50 %), 조합 원장 태그(AI Worker 표준은 해시 불변), Franka 편 폴더 접미사 `_franka_mast`, Franka 대상 폭 ≤ 6.6 cm 필터, `IR_L9R_LENT=1`(빌린 카드에서 yield 무시), SIGUSR1 → 전체 스택 출력. | 필드가 없으면 기존 |
| `harvest/sim/scene.py` | `make_env(..., robot=None)`. `None`이면 기존과 같은 경로이고, `"franka_mast"`면 프로필의 관절·링크·카메라·받침대·손가락 폭·TCP를 쓴다. | 시험으로 고정 |
| `harvest/sim/oracle_state.py`, `teach_l8d/collect.py`, `teach_pt/dataset.py` | 손가락 링크 수, 관절 접두사(`joint_prefixes`), 분할 `l9*`(L9 시드 1e6–1e8, 행 id = 편 폴더). | 옵션일 때만 |
| `harvest/teach_strip8/strip.py` | L9 물체 줄 처리. 실행 중에 정한 설명을 알려진 접두사('object')에서 자르면 크기가 남는다. 그 경우에만 `- 이름 (역할)`로 줄인다. | L8S 결과 불변(기준 텍스트 시험) |
| `harvest/l9/build9.py` | **L9 → d-min 빌드**(모든 로봇·두 팔·카메라 기하). control 행(검증 점 라벨, L8 반복)과 aux 가리키기 행(물체 이름은 그 호출 요청에서 읽음)을 만든다. 행마다 `robot`·`head_cam_mode`·`camera`·`source`를 넣고, 요청에 `camera:` 줄을 넣는 옵션이 있다. `check_rows`는 로봇·요청 문구·카메라 줄·손·이미지를 다기체 섞임에서 검사한다. | 새 파일 |
| `tools/l9r/` | `probe_franka.py`·`probe_finger.py`(파드 진단), `pilot_plan.py`(스모크·시범·`--eval` 보류 세트), `lane_r.sh`(빌린 카드용 레인, 메모리 가드 85 GiB), `pilot.sh`(시범 체인 + 15분 무출력 감시), `pilot_summary.py`·`pilot_compare.py`(무작위 대 양산 표준: 끝 이유·라벨 탈락)·`sheets.py`(로봇·기하별 프레임 시트), `hcam8_build.py`·`hcam8_rows_par.sh`·`hcam8_start.sh`·`hcam8_worker.sh`(E-HCAM8), `hollow_grasp.py`(속 빈 물체 라벨 실측). | — |
| `tests/l9/` | `test_hcam9.py`, `test_robot9.py`, `test_build9.py`(+ `fixtures/` L8S 기준 텍스트 3쌍, L9 요청 2개), `test_hcam8_build.py`. | — |

## 2. 커밋 (dev)
`99bf83f`(등록·설계 §9) · `2b84d96`(프로필 층·hcam) · `48b4cb0`(mimic 제거·해시 이름·변경 1) · `3f0c6a9`(probe) · `ea35833`(import) · `b8cb53b`(받침대 위치·L9 분할·빌드 도구) · `62fe89d`(strip L9 줄) · `016fc27`(build9·strip 접두사 함정·시험) · `738288b`(SIGUSR1) · `e552d35`·`4e2794c`(병렬 빌드) · `5fdb363`(손목 9 cm·감시·hollow 도구) · `bee7cba`(시작 스크립트·§10.1) · `981b3fd`(eval 계획) · `ffc27f4`(변경 2) · `9feaa0e`(§9.2 개정).
- 파드 코드 사본 이름은 **리베이스 전 해시**다(내용 동일). `code_l9r_4fe75ee` = `5fdb363`(시범 코드), `code_l9r_7ec6a17` = `bee7cba`(H0 빌드·학습 코드), `code_l9r_1fa439e` = `4e2794c`, `code_l9r_c0a7619` = `016fc27`.

## 3. 시험
- `tests/l9` 68개 통과. 여기에 L8S d-min 기준 텍스트 불변(e9fd82c로 만든 3쌍), L9 물체 줄, 로봇 프로필(집게·카메라·요청 문구), 카메라 줄 위치, 다기체 행 검사가 들어 있다.
- `tests/teach_strip8` 통과. `tests/sim`·`tests/teach_l8d`·`tests/astra_motion`에서 실패하는 3개는 이 작업 전부터 실패한다(Windows CRLF 카메라 파일 해시 2개, `test_e2e_fake` F0 1개; origin/dev에서 같은 실패 확인).
- 파드: Franka probe(TCP 오프셋 102.3 mm = 공식 TCP 103.4 mm에 가까움, IK 2.3 mm, 손가락 폭 0–80 mm 추종), H0 빌드 행 검사 3,000행 오류 0.

## 4. 시범 결과 (`/data/harvest/out/l9r/pilot1`, 7a2a GPU1 레인 1–3, 코드 `code_l9r_4fe75ee`)
- 실행: 2026-10-01 15:28–16:41 UTC. 처음에는 레인 3개였고, 사용자 GPU 묶음 지시(10-02 01시) 뒤 15:43 UTC부터 레인 1개로 줄이고 카드를 L9에 돌려주었다. 작업 36개 중 16 + 4개는 건너뛰었다. 편 122(건너뜀 38 = '정의가 장면에 안 맞음', L9 양산과 같은 원인). 요약 `pilot1/summary.json`, 비교 `tools/l9r/pilot_compare.py`.

| 묶음 | 편 | 성공(관절 ≤ 0.04) | Wilson 95 % | 튐(> 0.04 rad) 편 | 관절 걸음 최대 중앙/95 % | G1 통과(n ≥ 10, ≥ 0.5) |
|---|---|---|---|---|---|---|
| AI Worker 무작위 머리 기하 | 44(좌 29·우 15) | 0.705 | 0.56–0.82 | 2.3 % | 0.026 / 0.037 rad | spread_right(10편 있는 유일한 정의) |
| 같은 (정의, 팔) 양산 표준 기하(l9m-2) | 316 | 0.788(편 가중 0.755) | — | — | — | — |
| Franka + 머리 받침대 | 76(우) | 0.605 | 0.49–0.71 | **0 %** | 0.008 / 0.010 rad | set_centre 0.7, set_drink_left 0.9, stack_by_colour 0.5 |

- **AI Worker 무작위 기하 관문(무작위 − 표준 ≥ −5 %p)**: −5.1 %p로 **경계에서 미달**이지만 n = 44라 판단할 힘이 없다. 원인을 보면 카메라 탓이 아니다.
  - 데이터 실행기는 참값 xyz(`eef`) 명령으로 움직이고 카메라를 쓰지 않는다.
  - 실패 대부분은 4편(spread_right·down_front_of)에서 열린 손가락이 다른 물체 위에 걸려 '막힘'이 반복된 경우다. 그래서 '막힘' 라벨 탈락이 19 %(양산 1.5 %)로 늘었다.
  - 카메라 탓인 '가려짐' 탈락은 오히려 17.8 %로, 양산 24.1 %보다 낮다.
  - 기하 구간별 성공도 높이·피치·화각 높음/낮음 모두 0.68–0.79로 비슷하다.
  - **권장**: L9 v2 양산에서 편 50 % 동전(`HCAM_ON`)으로 켜고, 표준 쪽과 수율을 같은 시간대에 실시간 비교한다(n ≥ 300에서 차이 < −5 %p면 끈다). 학습 채택은 E-HCAM8이 정한다.
- **실현 기하(AI Worker 무작위)**: 작업면 위 0.375–0.718 m, 피치 31.7–61.3°, 가로 화각 66.8–94.9°, 팬 −28.5…+29.5°. 다시 뽑기 0회 28편 · 1–3회 16편이고, 5회 뒤 표준으로 돌아간 편이 2편이다.
- **Franka**: 관절 튐 0. 기저 내림 0.001–0.118 m. 받침대 기하는 작업면 위 0.454–0.699 m, 피치 38.1–54.9°, 팬 −19.6…−0.1°.
  - n ≥ 10에서 통과한 정의는 3개다.
  - 0.5 이상이지만 n < 10인 정의: rel_front 0.78(9), set_drink_front 1.0(4), down_front_of 0.6(5), rel_between 0.56(9).
  - 미달: sort_size_sides 0.22, to_back_right 0.40.
  - 실패 끝 이유: stop 17, 단계 호출 한도 7, 호출 한도 5, 탁자 밖 1.
- **프레임 직접 검수**(시트 `/data/harvest/out/l9r/pilot1/sheet_*_half.jpg`, 노트북 `D:\tools\pdf_out\l9r_pilot1\`):
  - AI Worker 무작위 기하는 높이·피치·화각이 눈에 띄게 다르다. TCP 고리는 렌더된 집게 위에 정확히 겹친다(마운트·내부값 일치 확인, 스모크 3 프레임).
  - Franka 머리 받침대 영상은 작업면과 오른쪽의 팔이 보이는 사람 머리 같은 시점이다. 팔이 받침대 쪽으로 오면 왼쪽 아래를 크게 가리는 프레임이 있다(가려짐 라벨 탈락으로 걸러짐).
  - Franka 손목 영상은 손가락과 물체가 보인다. 아래 약 30 %는 손 몸체다(§6-3).

## 5. 쓰는 법 (L9 v2에 넣을 때)
- AI Worker 머리 카메라 무작위화: 양산 run 디렉터리 옆에 `HCAM_ON` 파일을 둔다(run9가 `hcam="coin"`으로 읽음, 편 50 %). 또는 행에 `"hcam": "rand"|"hold"`를 넣는다. 결과는 meta `head_cam`(mode·draw·실현 높이·피치·팬·fx…·마운트)과 호출마다 cams.json에 남는다. 학습에 쓸지는 E-HCAM8 판정 뒤에 정한다(`head_cam.mode`로 거를 수 있음).
- Franka: 행에 `"robot": "franka_mast"`(오른팔 행만; 작업당 로봇 하나)를 넣는다. 같은 시드의 AI Worker 편과 폴더가 겹치지 않는다(`_franka_mast`). 시범 G1을 통과한 정의만 쓴다(§4).
- 빌드: `build9.build(ep_dirs, out_dir, "l9train", name, train=True, camera_line=False)` 다음에 `check_rows(rows, camera_line)`를 돌린다. 오류 0이어야 학습에 넣는다. 처리량은 CPU 1개당 약 0.7 상태/초라 병렬로 나눠야 한다(`hcam8_rows_par.sh`, 16조각에 1,800편 약 35분).

## 6. 남은 일
1. Franka 왼팔 행(기저를 y로 거울, `+0.23`)은 아직 없다(`world9`가 오른팔만 허용).
2. Galaxea R1 Pro(GalaxeaManipSim Apache-2.0, ZED 머리 + 양손 RealSense)와 Unitree G1(BSD-3, GR1 대체) 프로필이 없다. 순서는 §9.2 표.
3. Franka 손목 영상은 아래 약 30 %가 손 몸체다. 실물 장착(예: D405 손 옆 마운트)과 비교해 각도를 다시 볼 것.
4. 넓은 속 빈 물체(그릇·머그) 테두리 잡기는 설계 §10.1뿐이고, 시험·구현은 아직이다.
5. E-HCAM8 H1·H2: L9 v2 양산이 무작위 기하 편(같은 134층, `select --match episodes_H0.json`)을 내야 시작할 수 있다. 보류 평가 세트 900편(`pilot_plan.py --eval`: AI Worker 범위 밖 기하 300, Franka 300, 표준 300, 시드 9e6+)도 L9 묶음에서 렌더가 필요하다.
6. 런타임 `camera:` 줄 생성(camera_info + 관절)은 다음 본 학습(P2) 때 붙인다.
7. L9 양산의 '첫 호출에서 이미 성공' 편이 0.5 %(3,844 성공 중 18) 있다. 대상이 이미 목적지 근처에 놓인 경우로, 이 작업 전부터 있던 문제다. 시범 요약에서는 따로 센다.

## 7. 함정 (다시 밟지 말 것)
- Isaac URDF 가져오기는 `convert_mimic_joints_to_normal_joints=True`여도 `<mimic>`를 PhysX mimic으로 남긴다. 그러면 손가락 2가 구동기와 싸워 80 mm 명령에 9 mm가 된다 → URDF에서 `<mimic>`을 지운다.
- 변환 USD는 캐시된다 → URDF를 내용 해시 이름으로 두어 바뀌면 새로 변환되게 한다.
- `convert_camera_frame_orientation_convention`은 `isaaclab.utils.math`에 있다(sensors.camera.utils 아님).
- 카메라 자세는 부모 링크 기준 **로컬** USD 변환으로 쓴다. Isaac Lab의 카메라 `pos_w`는 물리가 갱신하지 않으므로, 우리 `_cam` = 살아 있는 부모 링크 자세 × 마운트로 계산한다. 표준 편은 아무것도 쓰지 않는다.
- Franka 받침대를 기저 뒤 높이에 두면 팔꿈치가 화면을 가린다 → 사람 머리처럼 두 어깨 사이(팔 왼쪽 0.23 m)에 둔다. 손목 카메라를 손 옆 5.5 cm에 두면 손 몸체가 화면을 채운다 → 9 cm.
- d-min strip: L9 물체 설명은 실행 중에 정해진다. 빌드 프로세스가 카탈로그를 등록하지 않으면 'object' 접두사에서 잘려 **크기 문구가 남는다**. `build9.prepare()`가 등록하고, strip은 그런 줄을 `- 이름 (역할)`로 줄인다.
- L9 행 id: 모든 L9 편의 task가 `l9_task`라 L8 id 규칙이면 겹친다 → 분할 `l9*`에서는 편 폴더 이름을 쓴다.
- aux 가리키기 행에는 그 편의 실행 중 이름이 필요하다 → 그 호출 요청의 OBJECTS 줄에서 읽는다(키 순서 = 상태의 present 순서). 개수가 다르면 aux를 건너뛰고 센다.
- Isaac이 첫 편 전에 30분 넘게 무출력으로 멈춘 적이 있다(스모크 3, CPU 260 %, SIGTERM·SIGINT 무시, 같은 시드 재실행은 정상). 대책은 감시(15분 무출력 → TERM, 30초 뒤 KILL)와 SIGUSR1 스택 덤프다.
- lend9로 빌린 카드에서는 yield 파일이 남아 있다 → 빌린 쪽 run9는 `IR_L9R_LENT=1`, 레인은 yield 검사가 없는 `lane_r.sh`를 쓴다.
- `pkill -f 패턴`·`pgrep -f`를 실행 명령줄에 두면 자기 셸을 죽인다(실제로 겪음) → 스크립트 파일 안에서 `/proc/*/cmdline`·`environ`으로 찾는다.
- 파드 스크립트에 `python -c`·heredoc 파이썬은 쓰지 않는다(값은 파일로 넘김: `--steps-out`).
