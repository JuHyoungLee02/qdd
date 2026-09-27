# 공개 로봇·공간 데이터 전체 목록 (2026-09-27)

목적(user-log 158): 35B 상위 모델 학습 데이터를 빨리 고를 수 있도록, 쓸 수 있는 공개 로봇·공간 데이터를 전부 한 표에 모은다.

우리 D·H 형식:
- **D** = 모델이 이미지 점(0–1000) + 높이 의도를 낸다. 코드가 점 + 미터 깊이(헤드) + 보정으로 3D 목표를 만든다. 깊이가 없어도, 알려진 3D 목표를 보정으로 투영해 점 라벨을 만들 수 있으면 D는 된다.
- **H** = D와 같되 깊이 영상도 입력으로 받고, xyz 직접 출력 대체 경로가 있다.
- 둘 다 필요한 것: RGB + (H는) 미터 깊이 + 카메라 내부값(K) + 로봇 기저 기준 카메라 자세(외부값) + 로봇 기저 기준 3D 목표(말단·물체).

표기: 상/중/하 = 변환 난이도(상 = 쉬움·거의 그대로), ● 있음 / ◐ 부분·불확실 / ✕ 없음, **굵게** = 이미 우리가 변환기를 돌려 수를 낸 원천.

출처는 3절 참고. 원문 상세는 `public_data_conversion_howto_2026-09-26.md`(4·9·13절), `rgb_depth_hybrid_survey_2026-09-27.md`(6절), `upper_vlm_data_survey_2026-09-26.md`.

## 1. 요약 표 — 상위 후보 순위

| 순위 | 이름 | 이유 |
|---|---|---|
| 1 | **BEHAVIOR-1K 2025 데모** | MIT·게이트 없음, m 깊이+분할+과제 물체 GT+보정 전부 있음, 1만 편, 변환기 이미 운용 중(D·H 5,277행). 자산 재렌더만 별도 약관 필요 |
| 2 | **ROBOTIS AI Worker RB2/RB3** | 우리 로봇 계열(FFW-BG2), T4 실루엣 보정(2.32 px) + 스테레오 깊이(관문 통과 81 %) 관문 통과, 변환기 생산판 완료(투영점 1.8만 + C′ 3,073 + 깊이 7,050장) |
| 3 | **MolmoBot Franka** | ODC-BY·게이트 없음, 계획기 10단계가 우리 6단계와 거의 1:1, 위에서 잡기 93.7 %, C′ 3,381행, 전체 약 9.2만 꾸러미(수백만 행 추정) |
| 4 | **RoboTwin 2.0** | MIT·게이트 없음, 시뮬 5기체, 위에서 잡기 100 %(집기 과제), C′ 353행, 깊이는 재생 필요(SAPIEN). **D 변환 보류**: 눈 확인에서 일부 과제의 물체 이름이 뒤바뀜('kitchenpot'이 캔 위) — 이름 매핑부터 고침 |
| 5 | **CALVIN** (신규 발견, 미착수) | MIT, 정적+손목 RGB-D 네이티브, 시뮬 카메라 보정 코드에 있음, Franka. **아직 아무 변환기도 없음 — 우선순위 대비 방치**, 다음 착수 후보 1순위 |
| 6 | **DROID**(lerobot C′ 완료 + 원본 스테레오는 후보) | CC BY 4.0·게이트 없음, 실물 Franka 9.2만+ 편, lerobot판 C′ 3,857행 완료, 깊이는 원본 스테레오 처리해야 함(설계만, 13.1 DROID 오른쪽 카메라 보류) |
| 7 | OXE ManiSkill (+ 깊이만 있는 OXE 6종) | ManiSkill만 깊이 단위(÷1024 m)와 K·외부 보정이 명세에 있음 → D·H 3,850행 완료. stanford_robocook은 외부만(K 없음), taco_play·fmb·uiuc_d3field·berkeley_autolab_ur5·nyu_franka_play는 보정 없음 → 관문 불통(features.json 확인) |
| 게이트 1 | InternData-M1 | 필드가 우리 형식에 가장 딱 맞음(`tcp_2d_trace`·`bbox3d`·`pick/place_obj_uid`), CC BY-NC-SA·게이트, 사용자 동의 필요 |
| 게이트 2 | AgiBot World Beta | 규모 최대(100만+ 궤적, 48 TB), 깊이 PNG 있으나 단위 확인 필요, CC BY-NC-SA·게이트 |

## 2. 전체 표

### 2.1 비게이트 — 우리가 이미 다룬 원천

| 이름(HF/출처 id) | 비게이트/게이트 | 라이선스 | 깊이 | 보정값 | 규모 | 로봇 종류 | 과제 다양성 | D·H 변환가능성 | 현재 상태 |
|---|---|---|---|---|---|---|---|---|---|
| **BEHAVIOR-1K 2025** (`behavior-1k/2025-challenge-demos`) | 비게이트(자산 재렌더는 별도 동의) | MIT | 있음, m 시뮬 GT, 14비트 로그 양자화→10비트(≈2.4 cm@1 m), 헤드 720²+손목 480²×2 | 내부값 상수(K) + `cam_rel_poses`(21, 기체 루트 기준) | 1만 편·1.19억 프레임·1.95 TB | R1Pro(이동 휴머노이드 양팔) | 50과제, 사람 원격조작 다양 | **상** — 깊이·보정·과제물체 GT 다 있어 그대로 D·H | 변환기 있음(운용중, D·H 5,277행) |
| **OXE ManiSkill**(시뮬, OXE 내) | 비게이트 | Apache 계열(OXE 공통, 개별 확인 필요) | 있음, uint16/1024 m 스케일(시뮬 GT) | K + 스텝별 외부값 | 30,000편(시트) | ManiSkill 다중 시뮬 로봇 | 시뮬 조작 과제 다양 | **상** | 변환기 있음(3,850행 생성) |
| **MolmoBot Franka** (`allenai/molmobot-data`) | 비게이트 | ODC-BY | 손목만, 0.05–0.55 m RGB부호화 mp4(머리 깊이 없음) | 편·프레임별 완전(K+외부값, 480² 기준→세로화각 보정 필요) | 약 9.2만 꾸러미×약5편≈46만 편[추정], 3.47 TB | Franka | pick-place, 계획기 10단계 | **상**(D) / **중**(H, 머리 깊이 없음) | 변환기 있음(생산판, C′ 3,381행, 위잡기 93.7%) |
| MolmoBot RBY1 (`allenai/molmobot-data`) | 비게이트 | ODC-BY | 손목만, 같은 형식 | 같음 | 약 9,905편, 148 GB | RBY1(휴머노이드) | 같은 계획기 | **중**(D, 위잡기 40%뿐) / **중**(H) | 변환기 있음(시운전 완료, C′ 부원천 254행) |
| **RoboTwin 2.0** (`TianxingChen/RoboTwin2.0`) | 비게이트 | MIT | 저장 안 됨, 재생하면 가능(SAPIEN) | `config.yml robot_pose` + 매 프레임 카메라 외부값 완전 | 집기 약 30과제×5기체×550편≈8만 편[추정], 2.55 TB | 5기체(aloha-agilex·franka 등) | 집기·놓기 다양, 옆잡기 과제 별도 표시 | **상**(D, C′) / **중**(H, 재생 비용) | 변환기 있음(운용중, C′ 353행, 위잡기 100%) |
| DROID lerobot (`lerobot/droid_1.0.1`) | 비게이트 | CC BY 4.0(카드 apache-2.0 표기) | 없음(lerobot판, 왼쪽 카메라만) | 원 보정(잡음 큼) + 2025 개선 보정(`KarlP/droid`, lerobot과 date필드 깨져 못 이음) | 95,658편·2,763만 프레임 | Franka | pick-place 가정 과제 넓음 | **중**(D만, C′ 완료) / **하**(H, 깊이 없음) | 변환기 있음(C′ 3,857행, `src_droid.py`) |
| DROID 원본(`gs://gresearch/robotics/droid_raw`) | 비게이트 | CC BY 4.0 | 스테레오 쌍만(ZED2 외부2+ZED미니 손목), 처리 필요 | 내부값 SVO 안, 외부값 메타+개선보정(약 3.6만 장면) | 약 9.2–9.5만 편, 원본 약 8.7 TB | Franka | 위와 동일 | **중**(처리 후 D·H 가능) | 없음(설계만, 오른쪽 카메라 확보는 사용자 보류) |
| **AI Worker RB2** (`ROBOTIS/Task_0002`) | 비게이트(추정, HF API 401로 확인 못함) | apache-2.0(카드) | 스테레오 쌍(657/857편에 오른눈), 깊이 스트림 없음 → Fast-FoundationStereo 처리 | 공개보정 없음, **우리 T4 자체보정**(2.32 px, ±4°·5cm 모호) | 857편·85,474프레임 | AI Worker FFW-BG2(우리 로봇 계열) | pick-place 문장 다양 | **상**(처리 후, 이미 생산판) | 변환기 있음(투영점 18,660+C′3,073+깊이 7,050장) |
| AI Worker RB3 | 비게이트(같음, 확인 필요) | apache-2.0(카드) | RB2와 동일 절차, 스테레오 처리 대상 | T4(2.32 px, 85% ≤5px), 머리가 편 안에서도 움직여 프레임별 재검증 필요 | 300편(과제파싱 246편) | AI Worker | pickup_obj | **상**(처리 후) | 변환기 있음(EE점 3,231+C′500) |
| AI Worker RB1 | 비게이트(같음, 확인 필요) | apache-2.0(카드) | 미처리 | T4(4.78 px, 52% ≤5px, 경계선) | 소규모 | AI Worker | CoffeeClassification(다중물체 분류, 이름파싱 불가) | **하**(관문 경계선+과제 특성상 이름 파싱 불가) | 변환기 있음이나 표본 생성 안 함 |
| MolmoAct 공개 혼합(bridge·rt1·bcz·aux_trace) | 비게이트 | CC BY 4.0 | 없음 | 없음(카메라 보정 자체가 없음) | tabletop 1,966편·31.7만 프레임 + 궤적 프레임 약 1,000만 | OXE 다중 로봇 | 다양(원 OXE 과제) | **하**(픽셀 전용, T0 트랙만) | 변환기 있음(T0, 궤적 3,200행) |
| Robo2VLM-1 | 비게이트 | Apache-2.0 | 없음(좌표 메타 없음) | 없음 | 68.5만 문항 | OXE 여러 원천(VQA) | 객관식 QA만 | **하**(형식 QA 전용) | 변환기 있음(형식 변환만) |
| RefSpatial (`JingkunAn/RefSpatial`) | 비게이트 | Apache-2.0 | 상대 8비트(영상별 min–max, m 뜻 없음) | 없음 | 250만 표본(HF 색인 250MB, 원본 약 357GB) | 로봇 아님(일반 실내영상+시뮬) | 공간 QA(빈공간·사이·거리) | **하**(D 불가, H는 depth:none만) | 변환기 있음(2D 점, T0) |

### 2.2 비게이트 — 깊이·보정 있는 OXE 부분집합(소규모, 즉시 후보)

| 이름 | 비게이트/게이트 | 라이선스 | 깊이 | 보정값 | 규모 | 로봇 종류 | 과제 다양성 | D·H 변환가능성 | 현재 상태 |
|---|---|---|---|---|---|---|---|---|---|
| taco_play | 비게이트(OXE 공통, 개별 확인 필요) | 확인 필요 | 있음, `depth_static` 150×200 + `depth_gripper` 84×84 float32(단위 확인 필요) | 있음(시트 표기) | 3,242편 | OXE 로봇(확인 필요) | 다양 | **중**(해상도 낮음, 단위 확인 전) | 없음 |
| stanford_robocook | 비게이트 | 확인 필요 | 있음, `depth_1–4` 256² float32 | 외부값만(내부값 확인 필요) | 2,460편 | 로봇팔(확인 필요) | 요리 조작 | **중** | 없음 |
| fmb | 비게이트 | 확인 필요 | 있음, 옆2+손목2 256² float32 | 있음(시트 표기) | 1,804편 | 로봇팔(확인 필요) | 조립·삽입 | **중** | 없음 |
| berkeley_autolab_ur5 | 비게이트 | 확인 필요 | 있음, `image_with_depth` 480×640 float32 | 없음(features spec에 보정 없음) | 896편 | UR5 | 다양 | **하**(보정 없어 D 불가, H depth 입력만) | 없음 |
| nyu_franka_play | 비게이트 | 확인 필요 | 있음, `depth`+`depth_additional_view` 128×128 int32 | 없음(features spec에 보정 없음) | 456편 | Franka | play data | **하** | 없음 |
| uiuc_d3field | 비게이트 | 확인 필요 | 있음, `depth_1–4` 360×640 uint16 | 없음 | 196편 | 로봇팔(확인 필요) | 소규모 | **하** | 없음 |
| kuka·toto·viola·berkeley_cable_routing·utaustin_mutex 등 나머지 OXE | 비게이트(대부분) | 개별 확인 필요 | **없음**(수집 장비엔 있었으나 RLDS 필드에 미포함, TFDS 카탈로그 확인 완료) | 데이터셋마다 다름 | 데이터셋마다 다름 | 다양 | 다양 | **하** | 없음 |
| bridge(BridgeData 원 RLDS) | 비게이트 | 확인 필요 | 없음 | 없음 | — | WidowX | 다양 | **하** | 없음 |

### 2.3 비게이트 — 새로 찾은 후보(이번 조사에서 추가)

| 이름(HF/출처) | 비게이트/게이트 | 라이선스 | 깊이 | 보정값 | 규모 | 로봇 종류 | 과제 다양성 | D·H 변환가능성 | 현재 상태 |
|---|---|---|---|---|---|---|---|---|---|
| **CALVIN**(`github.com/mees/calvin`) | 비게이트 | **MIT**(github LICENSE 확인) | **있음**, 정적+손목 RGB-D(시뮬 PyBullet GT) + 촉각 | 있음, 시뮬 카메라 파라미터가 코드에 있음(K+외부값 재현 가능) | 4환경(A–D)×약 6h play data(총 약24h), 34과제, 장기시퀀스 5개 연결 평가 | Franka Panda | 34과제, 언어 조건 장기 조작 | **상** — MIT+RGB-D 네이티브+보정 확보, 즉시 변환 가능 | 없음(우선 착수 후보) |
| LIBERO(HF `physical-intelligence/libero` 등 여러 미러) | 비게이트 | **CC BY 4.0**(HF API 확인) | 확인 필요(robosuite 기반, 기본 hdf5엔 없을 가능성, 재생하면 depth 획득 가능) | 있음(robosuite/MJCF 카메라, 재생시 이용) | 130과제×약50편(LIBERO-100 기준 약 6,500편) | Franka(robosuite) | 4계열(Spatial·Object·Goal·Long) 과제 다양 | **중**(재생 비용, RoboTwin과 유사한 경로) | 없음 |
| RoboCasa(원본, `robocasa/robocasa`) | 비게이트 | CC BY 4.0(추정, MimicGen 계열, 라이선스 페이지 확인 필요) | 없음(저장 안 됨), `dataset_states_to_obs.py --depth`로 재생 시 생성 가능 | 있음, robosuite 카메라(agentview·robot0_eye_in_hand) | 공개 3,000편(MimicGen 확장 가능) | Franka(이동형 아님, 원본 쪽) | 주방 다과제 | **중**(재생 필요) | 없음 (RoboCasa365 변형은 4.7에 별도, NVIDIA CC BY4.0, 게이트 없음, Panda 이동형) |
| RLBench(`github.com/stepjam/RLBench`) | 비게이트지만 **비상업 연구 전용**(Imperial College 커스텀 라이선스, 상업 불가) | 커스텀(비상업), 일부 BSD | 있음, CoppeliaSim 렌더로 깊이 획득 가능 | 있음, PyRep API로 카메라 내부·외부값 조회 가능 | 과제 생성기 기반(고정 편수 없음, 약 100과제) | Franka Panda(기본) | 100과제, 조작 다양 | **중**(라이선스 제약 주의) | 없음 |
| Colosseum(RLBench 확장) | RLBench와 동일 제약(확인 필요) | 커스텀(비상업 추정) | RLBench와 동일 | RLBench와 동일 | 20과제×교란 변형(평가 중심) | Franka | 일반화 평가용(학습 데이터 아님) | **하**(평가 벤치, 학습용 아님) | 없음, 확인 필요 |
| RoboSet(`robopen/roboset`, RoboHive) | 비게이트 | **MIT** | 확인 필요(카메라 4대, 깊이 여부 문서에 명시 안 됨) | 확인 필요 | 주방 다과제(정확한 편수 확인 필요) | Franka(추정) | 다과제 가정 | **하**(깊이·보정 불확실) | 없음 |
| BridgeData V2 원본 | 비게이트 | CC BY 4.0 | "있을 때만, 주 고정 카메라"(편수 미기재) | 언급 없음 | 확인 필요 | WidowX | 다양 | **하**(불확실, 보류) | 없음 |
| Mobile ALOHA(`lerobot/aloha_mobile_*`) | 비게이트 | MIT/Apache-2.0(서브셋마다 다름) | 대부분 없음(`is_depth_map:false`), lerobot이 RealSense 깊이 기능은 지원하나 배포본엔 적용 안 됨 | 확인 필요 | 서브셋마다 수백 편 | ALOHA 양팔(이동형) | 가정용 조작 다양 | **하**(깊이 없음) | 없음 |
| ARIO(All Robots In One, `imaei.github.io/project_pages/ario`, `agilexsupport` HF) | 비게이트(자체 수집분) | **혼합**: 자체 수집·생성분은 CC BY 4.0/MIT, 변환해 온 부분은 원 라이선스 따름(편별 확인 필요) | 확인 필요(시리즈마다 다를 것으로 추정) | 확인 필요 | 약 300만 편, 258 시리즈, 321,064과제 | 다중 로봇(258 시리즈) | 매우 다양 | **확인 필요**(규모는 크나 편별 라이선스·깊이 확인 전엔 못 씀) | 없음 |
| RoboPoint 데이터(`wentao-yuan/robopoint-data`) | 비게이트 | **Apache-2.0**(HF API 확인) | 없음(합성 포인팅 QA) | 없음 | 약 143.2만 image-QA | 로봇 아님(포인팅 사전학습용) | 공간 포인팅 QA | **중**(D 트랙 포인트 사전학습 보조로 유망, 로봇 조종 데이터 아님) | 없음 |
| PixMo-Points(`allenai/PixMo-Points`) | 비게이트 | **ODC-BY**(HF API 확인) | 없음 | 없음 | HF 카드상 다운로드 863(정확한 표본수 확인 필요) | 로봇 아님 | 일반 이미지 포인팅·개수 세기 | **중**(사전학습 보조) | 없음 |
| Where2Place(`wentao-yuan/where2place`) | 비게이트 | **Apache-2.0**(HF API 확인) | 없음 | 없음 | 100장(평가용, 소규모) | 로봇 아님 | 빈 공간 지정(평가 벤치) | **하**(학습보다 평가용, 소규모) | 없음 |
| ARKitScenes(`github.com/apple/ARKitScenes`) | 비게이트이나 **동의 절차 필요**(license 파일 서명, `ARKitScenes-license@group.apple.com`) | Apple 커스텀(연구용 허용, 조건부) | **있음**, LiDAR m 깊이 + RGB | 있음, 카메라 내부값+궤적(포즈)+메시 재구성 | 1,661개 장면, 5,048 RGB-D 시퀀스 | 로봇 아님(실내 장면) | 실내 3D 이해(로봇 과제 아님) | **하**(로봇 조작 데이터 아님, 공간 QA/사전학습 보조로만) | 없음 |
| ScanNet(`scan-net.org`) | 비게이트이나 **기관 이메일 신청 필요**(사실상 게이트에 준함) | 데이터=ScanNet 자체 약관, 코드=MIT | 있음, RGB-D `.sens`(m) | 있음, 내부·외부값+포즈 | 1,500+ 스캔, 250만 뷰 | 로봇 아님 | 실내 장면 이해 | **하**(로봇 아님, 공간 QA 보조로만) | 없음 |

## 3. 게이트 데이터 (설계만 — 절대 내려받지 않음, HF API로만 조회)

원칙: 게이트 데이터는 HF에서 동의가 필요하다. 에이전트는 동의하지 않는다(`public_data_conversion_howto` 4.7). 아래는 변환기를 만든다면 무엇이 필요한지 설계만 적는다. 실제 착수는 사용자 동의 뒤(비게이트 데이터를 먼저 쓰라는 규칙, `project_gated_data_reminder.md`).

| 이름 | 라이선스 | 깊이 | 보정값 | 규모 | 로봇 | 변환기 설계 메모 |
|---|---|---|---|---|---|---|
| **InternData-M1** | CC BY-NC-SA 4.0, 게이트 | 카드에 없음, 확인 필요 | 확인 필요 | 확인 필요(A1 규모 참고: 63만+ 궤적급) | InternRobotics M1 | 필드 `tcp_2d_trace`(2D 점) + `bbox3d`(물체 3D 상자) + `pick/place_obj_uid`가 D·H 필드에 가장 가깝다. 카메라 보정 유무만 확인되면 MolmoBot과 같은 경로로 바로 변환 가능 |
| InternData-A1 | CC BY-NC-SA 4.0, 게이트 | 없음(RGB 3대: 머리+손 좌우) | 있음(보강판, 내부·외부값) | 63만+ 궤적, 7,433h, 6.72TB | InternRobotics A1 | 보정은 있으나 깊이 없음 → D만(점 라벨), H는 불가. 시뮬 엔진·장면 비공개면 재렌더도 불가 |
| AgiBot World Alpha/Beta | CC BY-NC-SA 4.0, 게이트 | 깊이 PNG 폴더 있음(단위·카메라 확인 필요) | 편마다 내부·외부값 폴더 있음 | Beta 100만+ 궤적, 2,976h, 48.1TB | AgiBot 다중 | 단위 확인되면 최대 규모 D·H 후보. 게이트+비상업이라 Astra로 전송 여부도 별도 결정 필요 |
| RoboMIND | Apache-2.0, 게이트 | 카드에 "시뮬은 깊이 당분간 없음"만, 실물 깊이 확인 필요 | 카드에 없음 | 10.7만 궤적, 12.3TB | Franka·Tiangong 휴머노이드·AgileX·UR5e | 깊이 확인 전엔 R(텍스트/QA)용으로만. 다중 로봇이라 우리 로봇 계열과 매칭되는 서브셋부터 확인 |
| Galaxea Open-World | CC BY-NC-SA 4.0, 게이트 | 없음(단, 머리 좌우 RGB 720×1280 15fps라 스테레오 쌍 가능성) | 카드에 보정 없음 | 500+h, 2.87TB | Galaxea | 보정 공개되면 RB2와 같은 T4+스테레오 절차 적용 가능. 지금은 R용 |
| RH20T | C부분 CC BY-SA 4.0 / NC부분 CC BY-NC 4.0, 비게이트지만 자체 다운로드 신청 절차(확인 필요) | 있음, m 센서 RGB-D 1280×720 10Hz | 있음, 보정 폴더(내부·외부+캘리브 시 그리퍼 자세) | 11만+ 시퀀스, RGB 약5TB/RGBD 약10TB | 다중 로봇, 전역 카메라 8–10대+손 1–2대 | 전역 카메라라 머리 시점과 다름 → 카메라 선택 로직 필요. C부분(상업 허용)만 우선 |
| RoboInter-Data/VQA | 확인 필요, 게이트 | 확인 필요 | 확인 필요 | 확인 필요 | 확인 필요 | 카드만 확인됨, 필드 상세 미조사 |

## 4. 확인 경로

- HF API(비인증): `https://huggingface.co/api/datasets/<id>` — `gated`·`license` 필드. LeRobot 계열은 `https://huggingface.co/datasets/<id>/resolve/main/meta/info.json`으로 `features`(깊이·카메라 필드) 확인.
- BEHAVIOR-1K 2025: https://huggingface.co/datasets/behavior-1k/2025-challenge-demos
- MolmoBot: https://huggingface.co/datasets/allenai/molmobot-data
- RoboTwin 2.0: https://huggingface.co/datasets/TianxingChen/RoboTwin2.0
- DROID lerobot판: https://huggingface.co/datasets/lerobot/droid_1.0.1 · 원본: https://droid-dataset.github.io/droid/the-droid-dataset · 개선 보정: `KarlP/droid`
- ROBOTIS AI Worker: https://huggingface.co/ROBOTIS (Task_0002 등, 비로그인 API 401 — 게이트 여부 재확인 필요)
- InternData-A1/M1: https://huggingface.co/datasets/InternRobotics/InternData-A1 · https://huggingface.co/datasets/InternRobotics/InternData-M1
- AgiBot World: https://huggingface.co/datasets/agibot-world/AgiBotWorld-Beta · https://github.com/OpenDriveLab/AgiBot-World
- RoboMIND: https://huggingface.co/datasets/x-humanoid-robomind/RoboMIND
- Galaxea Open-World: https://huggingface.co/datasets/OpenGalaxea/Galaxea-Open-World-Dataset
- RH20T: https://rh20t.github.io/
- RefSpatial: https://huggingface.co/datasets/JingkunAn/RefSpatial
- OXE 시트: https://docs.google.com/spreadsheets/d/1rPBD77tk60AEIGZrGSODwyyzs5FgCU9Uz3h-3_t2A9g · TFDS 카탈로그: https://www.tensorflow.org/datasets/catalog/taco_play (외 berkeley_autolab_ur5·nyu_franka_play·maniskill·stanford_robocook·uiuc_d3field·fmb)
- CALVIN: https://github.com/mees/calvin (LICENSE = MIT)
- LIBERO: https://huggingface.co/datasets/physical-intelligence/libero (CC BY 4.0, 원 프로젝트 https://libero-project.github.io/)
- RoboCasa(원본): https://github.com/robocasa/robocasa · RoboCasa365(4.7): NVIDIA CC BY 4.0
- RLBench: https://github.com/stepjam/RLBench (LICENSE = Imperial College 커스텀, 비상업)
- RoboSet: https://robopen.github.io/roboset/ · https://sites.google.com/view/robohive/roboset
- BridgeData V2: https://rail-berkeley.github.io/bridgedata/
- Mobile ALOHA(lerobot판): https://huggingface.co/datasets/lerobot/aloha_mobile_cabinet 등
- ARIO: https://imaei.github.io/project_pages/ario/ · https://arxiv.org/abs/2408.10899 · https://huggingface.co/agilexsupport
- RoboPoint: https://huggingface.co/datasets/wentao-yuan/robopoint-data
- PixMo-Points: https://huggingface.co/datasets/allenai/PixMo-Points
- Where2Place: https://huggingface.co/datasets/wentao-yuan/where2place
- ARKitScenes: https://github.com/apple/ARKitScenes (동의 메일 `ARKitScenes-license@group.apple.com`)
- ScanNet: http://www.scan-net.org/ (기관 이메일로 약관 신청)

## 5. 확인 못 한 것(다음에 채울 것)

- ROBOTIS 데이터셋들의 정확한 게이트 여부(비로그인 HF API가 401 반환, 로그인 상태에서만 재확인 가능).
- OXE 개별 서브셋(taco_play·stanford_robocook·fmb·berkeley_autolab_ur5·nyu_franka_play·uiuc_d3field)의 정확한 라이선스·로봇 종류·깊이 단위 — RLDS 필드 존재만 확인됨.
- LIBERO·RoboCasa(원본)의 재생 기반 깊이 생성이 실제로 되는지(RoboTwin·BEHAVIOR와 같은 경로일 것으로 추정만 함).
- ARIO 편별(시리즈별) 라이선스와 깊이 유무 — 규모가 커서(약 300만 편) 확인되면 상위 후보로 올라갈 수 있음.
- AgiBot World 깊이 PNG의 단위·대상 카메라.
- RoboSet 카메라 4대 중 깊이 카메라 포함 여부.
