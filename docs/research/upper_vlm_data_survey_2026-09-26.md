# 상위 VLM(Astra 대체) 학습 데이터 조사 — 공개 데이터 대 자체 시뮬 생성 (2026-09-26)

작성 2026-09-26 12:20 UTC(21:20 KST), 데이터 조사 에이전트. 사용자 원문: **"저거에 맞는 데이터를 찾는 작업을 꼼꼼하게 해보자 심이면 더 좋을 것 같구"**. 대상은 E-TEACH-L(정본 §96·§97)의 상위 VLM(8B 추세 시험 → 35B) 학습 데이터다. **학습·변환·유료 호출·GPU 0.** HF·GitHub·arXiv·OpenReview 공개 API와 카드만 읽고, 표본 몇 편만 파드에 받아 필드와 프레임을 직접 봤다(파드 `/data/harvest/data/upper_vlm_survey/`, 1.3 GB).

중복 방지: `robotis_open_data_survey_2026-09-26.md`(ROBOTIS 실데이터 — 여기서는 다시 조사하지 않고 결론만 가져옴), `lit_sweep_2026-09-26.md`·`auto_context_design_2026-09-26.md`(RoboRefer·Embodied-R1 논문 근거 — 여기서는 **데이터** 쪽만).

## 0. 결론 요약

- **판정: 주 데이터는 자체 시뮬 생성, 공개 데이터는 다양성·일반 인식 보조.** 스펙 1(조종 표본)·2(복구)·4(자기 인식)는 우리 기체(FFW-SG2)·우리 카메라(머리 ZED Mini 672×376, 손목 D405)·우리 행동 공간(절대 TCP 목표 + 그리퍼)이 정확히 맞아야 하는데, 그런 공개 데이터는 **없다**(AI Worker 시뮬 데이터는 HF에 0건; 실데이터는 ROBOTIS 조사 참고). 우리 Isaac 시뮬 + 참값 모델은 이것을 무한히, 무료로, 깊이·물체 자세·FK 투영까지 정답으로 낸다. 공개 데이터가 이기는 것은 스펙 5(장면 다양성)와 스펙 3의 일반 공간 지시·점 찍기 능력 유지다.
- **상위 5개(자세한 순위는 4절)**
  1. **MolmoBot-data** `allenai/molmobot-data` — 시뮬, **RBY1 양팔 바퀴형 인간형**(AI Worker와 가장 가까운 형태) + Franka. 머리 + 손목 2대, 손목 깊이, **프레임마다 카메라 내부값·외부값**, TCP 자세, 물체 시작 자세, **그리퍼·집을 물체·놓을 곳의 영상 점**(카메라별), 실패·재시도 표시, 지시문과 지칭 표현. ODC-BY. → 스펙 4(자기 인식 점)·3(물체 점) 사전 학습, 1의 형식 예열.
  2. **BEHAVIOR-1K 2025 challenge demos** `behavior-1k/2025-challenge-demos` — 시뮬(OmniGibson), **R1Pro 양팔 바퀴형 인간형**, 사람 원격조작 1만 편·50과제. 머리 720² + 손목 2대 480², **깊이·인스턴스 분할 영상**, 말단 자세, 카메라 상대 자세·고정 내부값, 과제 물체 자세, **스킬 구간 주석**(물체 id·프레임 구간). MIT. → 스펙 3(깊이 + 분할로 물체 3D·받침 면)·5(집 장면)·1(스킬 단위 목표).
  3. **RoboTwin 2.0** `TianxingChen/RoboTwin2.0` — 시뮬, 50과제 × 5기체(양팔 aloha-agilex 등), 과제·기체당 깨끗한 50편 + **도메인 무작위화 500편**(방해물·질감·조명). 머리·손목 2대·정면, **프레임마다 내부값·외부값**, 말단 자세·그리퍼, 지시문 수십 가지. MIT, **ICML 2026**, 2,914★. → 스펙 1·4·5.
  4. **RefSpatial** `JingkunAn/RefSpatial`(+ AI2 재포장 `allenai/Molmo2-ER-*`) — 공간 지시 점 찍기 250만 표본, 깊이 포함, **빈 공간(놓을 자리) 점** 질문, Blender 시뮬 부분 포함. Apache-2.0, **NeurIPS 2025**. → 스펙 3의 '놓을 면·자리' 점, 학습 중 일반 그라운딩 잊음 방지 혼합.
  5. **InternData-M1** `InternRobotics/InternData-M1` — 시뮬 24.4만 편, 프레임마다 **2D·3D 상자, TCP 2D·3D 궤적**, 집을·놓을 물체 id, 다양한 지시문. 필드는 스펙 3·4에 가장 딱 맞지만 **게이트(약관 동의 필요)·CC BY-NC-SA** → 이번에 표본을 못 받았다(카드 필드만 확인).
- **복구 데이터(스펙 2)는 공개된 것이 사실상 없다.** 수치 목표가 붙은 교정·개입 데이터는 0건. 있는 것은 (a) MolmoBot의 재시도 횟수·실패 표시(스크립트 계획기), (b) BEHAVIOR 원격조작의 자연스러운 다시 잡기(표시 없음), (c) RoboFAC의 언어 수준 실패 분석 QA(수치 목표 없음, 신뢰도 중하). → **자체 시뮬 DAgger(학생 상태 × 참값 모델 라벨)가 유일한 실용 경로**다.
- **AI Worker 시뮬 자산**: `ROBOTIS-GIT/cyclo_lab`(Isaac Lab 2.3, FFW-BG2 도달·집어 놓기, **FFW-SG2 Real 집어 놓기 + Isaac Lab Mimic 생성 파이프라인**, Apache-2.0, 145★ — 우리 `harvest/sim/scene.py`가 이미 이 FFW_SG2 USD를 씀), `ROBOTIS-GIT/robotis_mujoco_menagerie`(`robotis_ffw/ffw_bg2.xml`·`ffw_sg2.xml`·`ffw_sh5.xml`, Apache-2.0, 74★), `ROBOTIS-GIT/cyclo_mjlab`(MuJoCo MJLab, 2026-08, 5★). **AI Worker 공개 시뮬 데이터셋은 HF에 없다**(검색어 `ffw_sim`·`ffw_sg2_sim`·`cyclo`·`isaac_ffw` 등 0건).
- **자체 생성 다양성 보강 1순위**: `allenai/molmospaces`(Isaac USD·MuJoCo 물체·장면·파지, CC BY 4.0 / ODC-BY, 2026-02부터 Isaac 호환) — 공개 데이터를 그대로 쓰는 대신 **우리 생성기의 물체·배경 풀을 넓히는** 쪽이 스펙 1·2·4 정합을 잃지 않는다.
- **막힘**: (1) 게이트 데이터(InternData-A1·M1, RoboInter, AgiBot, Galaxea)는 사용자가 HF에서 약관 동의를 눌러야 받을 수 있다(에이전트가 대신 동의하지 않음). (2) CC BY-NC-SA·CC BY-NC는 **Astra 전송 보류**(비상업 조항의 외부 API 전송 해석 필요), 라이선스 없음(SynGrasp-1B 등)은 내부 전용·Astra 금지. (3) 규모가 TB 단위 — 부분 집합만.

## 1. 방법

- 검색: HF API `datasets?search=`(RoboTwin, SynGrasp, InternData, PhysicalAI-Robotics, behavior, RoboCasa, RefSpatial, Embodied-R1, ShareRobot, RoboBrain, Cosmos-Reason, MolmoAct, Robo2VLM, RoboFAC, AgiBot, Galaxea, SpatialIntelligence, InternSpatial, SPAR, RoboSpatial, Molmo2, PixMo, EmbSpatial, RoboPoint, RoboMIND, ManiSkill, LIBERO, mimicgen, ai_worker, ffw_, VSI-590K, EO-Data, RoboInter, RoboAfford, ERQA, MolmoBot, failure, recovery, intervention, correction, dagger, failbench, cyclo, ffw_sim 등) + `author=allenai`. GitHub API로 별·생성일·라이선스, `orgs/ROBOTIS-GIT/repos` 전체. arXiv API로 날짜·Comments, **OpenReview API v2로 학회**.
- 카드: 공개 카드는 `raw/main/README.md`, 게이트 카드는 웹 페이지 본문(약관 문구 포함)을 읽음.
- 표본(파드, 토큰은 파일에서만 읽음): RoboTwin 2.0 `lift_pot/aloha-agilex_clean_50.zip`(280 MB, 편 0 hdf5), BEHAVIOR 2025 편 1개(parquet·주석·편 메타·머리 영상), MolmoBot RBY1PickAndPlace val 샤드 1개(128 MB, 꾸러미 1개 해제), NVIDIA RoboCasa Kitchen-Demos `PickPlaceCounterToSink`(89 MB, 100편), RefSpatial 시각화 부분(Simulator·3D parquet), Robo2VLM parquet 1개(366 MB), RoboFAC `training_qa.json`. 프레임은 눈으로 확인(3절).
- 도구: 로컬 `D:\tools\scratch_qdd\upper_vlm_survey\`(hf_search·hf_cards·hf_tree·gh_info·arxiv_info·or_venue·page_text), 파드 `code/`(pod_get.sh·inspect_h5·inspect_pq·molmobot_peek·molmobot_json·grab_frames·peek_rows·qa_types). h5py·zstandard는 `/data/.../upper_vlm_survey/pylib`에 설치.

## 2. 데이터셋 표

### 2.1 스펙 대조 (● 있음 · ◐ 계산 가능/부분 · ○ 없음 · ? 미확인)

스펙: **1** 조종 표본(머리·손목 RGB + TCP·그리퍼 + 지시문 → 다음 말단 목표) · **2** 복구·교란 상태 · **3** 인식 QA(물체 3D 위치·크기, 받침·탁자 면, 놓을 면) · **4** 자기 인식(말단 영상 위치·접근 방향) · **5** 장면 다양성 · **6** AI Worker·유사 양팔 인간형.

| 데이터셋 | 시뮬/실물 | 1 | 2 | 3 | 4 | 5 | 6 | 깊이 | 카메라 보정 | 확인 방법 |
|---|---|---|---|---|---|---|---|---|---|---|
| MolmoBot-data (RBY1·Franka) | 시뮬(MuJoCo 기반 MolmoSpaces) | ● 머리·손목2, `tcp_pose`, `actions/ee_pose`(팔별), 그리퍼, 지시문 | ◐ `policy_num_retries`·`fail`·`policy_phase` | ◐ `obj_start` 자세, 물체 영상 점(10점) | **●** 그리퍼 영상 점(카메라별) + 보정 | ● procthor·holodeck 집 | **● RBY1** | 손목만(영상) | ● 프레임마다 intrinsic·extrinsic | 표본 |
| BEHAVIOR-1K 2025 demos (R1Pro) | 시뮬(OmniGibson) 원격조작 | ● 머리 720²·손목2 480², `eef_{left,right}_{pos,quat}`, 그리퍼 | ◐ 사람 원격조작의 자연 교정(표시 없음) | ● `task_info`(과제 물체 자세 46-D), 깊이 + 인스턴스 분할 | ◐ 말단 자세 + 카메라 자세 + 고정 내부값 → 투영 | ● 50과제·집 장면 | **● R1Pro** | ● 3대 | ◐ 내부값 고정(코드 상수), `cam_rel_poses` | 표본 + 코드 |
| BEHAVIOR-1K 2026 demos | 같음 | ● | ◐ | ● | ◐ | ● 100과제·2만 편 | ● | ● | ◐ | 카드만 |
| RoboTwin 2.0 | 시뮬(SAPIEN) | ● 머리·손목2·정면, `endpose` 7-D ×2, 그리퍼 | ○(성공 편만) | ◐ 물체 id(`scene_info`), 무작위판에 방해물 | ◐ 말단 자세 + 보정 → 투영 | ● 무작위판(방해물·질감·조명) | ◐ aloha-agilex 양팔 | ○ 저장 안 됨(생성기는 가능) | ● 프레임마다 | 표본 |
| InternData-M1 | 시뮬 | ● Franka(ego·base 2대), 말단 위치·자세, 그리퍼 | ? | **● 2D·3D 상자, 집을·놓을 물체 id** | **● TCP 2D 궤적(카메라별)·3D 궤적** | ● 8만 물체 | ○ 한 팔 | ? | ? | 카드만(게이트) |
| InternData-A1 | 시뮬(+실물 예정) | ● 머리 + 손목2, `ee`·`tcp` 자세(팔별), 그리퍼 | ? | ○ | ◐ 보정 + TCP 자세 → 투영 | ● 70과제·227장면 | ◐ Lift-2·Split-Aloha·A2D 양팔 | ○(`is_depth_map` false) | ● 머리·손목 intrinsics + extrinsics | 카드만(게이트) |
| RoboCasa365 (NVIDIA Kitchen-Demos, ember 미러) | 시뮬(MuJoCo) | ◐ 3인칭2 + 손목, `eef_pos_rel`·`eef_quat_rel` | ○ | ◐ `states.npz`·`model.xml.gz` 재생으로 물체 자세 복원 가능 | ◐ MJCF 카메라(fovy·자세)로 투영 | ● 365과제·주방 | ○ Panda 이동형 | ○(재렌더 가능) | ◐ MJCF | 표본 |
| GR00T X-Embodiment-Sim | 시뮬(RoboCasa) | ◐ GR1 ego 1대, 관절 상태 | ○ | ○ | ○ | ◐ | ◐ GR1 인간형 | ○ | ○ | info.json |
| SynGrasp-1B (GraspVLA) | 시뮬 | ◐ Franka 파지 | ? | ? | ? | ● 1만 물체 | ○ | ? | ? | 카드 없음(15 B) |
| RefSpatial | 실사진 + CA-1M + Blender 시뮬 | ○ | ○ | **● 점 답 + 깊이, 빈 공간·사이·거리 지정 자리** | ○ | ● 실내외 | ○ | ● | ○(3D 부분은 CA-1M) | 표본 |
| Robo2VLM-1 | 실물(OXE) VQA | ○ | ◐ 성공 여부·파지 안정 질문 | ◐ 가림·도달 가능 질문(객관식) | ◐ "그리퍼 열림?" 등 | ● OXE 여러 원천 | ○ | ○ | ○ | 표본 |
| RoboFAC | 시뮬(ManiSkill) + 실물 | ○(h5 운동학은 있음) | **◐ 오류 궤적 9,440 + 실패 분석·교정 언어 QA** | ○ | ○ | ◐ 16과제·53장면 | ○ | ? | ? | 표본(QA) |
| RoboInter-Data | 실물(DROID·RH20T) 주석 | ◐ | ○ | ● 물체 상자·놓을 자리 제안·접촉점 | ● 그리퍼 상자·궤적 | ● | ○ | ○ | ? | 카드만(게이트) |
| Embodied-R1.5 SFT | 혼합 재포장 | ○ | ◐ RoboFail·ManiskillFail·BridgeDataFail(언어) | ● 점·영역·3D 궤적(깊이 m) | ◐ 궤적 | ● | ○ | ◐ | ○ | 카드 |
| Cosmos-Reason1 SFT | 실물 영상 | ○ | ◐ 성공·실패 판단 텍스트 | ○ | ○ | ● | ○ | ○ | ○ | 카드 |
| MolmoAct Dataset·혼합 | 실물 Franka | ◐ 외부 2 + 손목 1 | ○ | ◐ 깊이 토큰·궤적 추적 | ● 궤적 점 | ◐ | ○ | ◐ 깊이 토큰 | ○ | 카드(선행 문서) |
| VSI-590K / InternSpatial / SPAR-7M | 실내 영상·3D 스캔 QA | ○ | ○ | ◐ 거리·크기·상대 위치(로봇 아님) | ○ | ● | ○ | ◐ | ◐ | 카드 |
| AgiBot Digital World | 시뮬 | ? | ? | ? | ? | ◐ 5장면 | ● A2D 양팔 | ? | ? | 카드(게이트) |
| Galaxea Open-World | 실물 | ● R1 Lite 양팔 | ? | ○ | ◐ | ● | ● | ? | ? | 카드(게이트) |

### 2.2 규모·날짜·라이선스·신뢰도·적합 점수

적합 점수 = 스펙 1–6 가중(1·3·4 각 2, 2·5·6 각 1)의 0–5 환산, 표본으로 본 것만 만점 가능. 신뢰도: 학회(OpenReview/arXiv Comments) + GitHub 별 + HF 좋아요·지난달 내려받기(모두 2026-09-26 API 값).

| 데이터셋 | 크기 | 날짜(공개) | 라이선스 | Astra 전송 | 학회 · 별 · HF 반응 | 신뢰도 | 적합 |
|---|---|---|---|---|---|---|---|
| MolmoBot-data | 8,874.5 GB(설정 9개) | 2026-03-05(arXiv 2603.16861) | ODC-BY 1.0 (Objaverse 물체별 라이선스 표 제공) | 가능(출처 표기) | 학회 본회의 미확인(ICRA 2026 워크숍 구두 3곳) · molmospaces 479★ · L8 D46,994 | 중상(AI2, 반응 중간) | **4.5** |
| BEHAVIOR-1K 2025 demos | 2,070.9 GB, 1만 편·1.19억 프레임·30 fps | 2025-08-22 | MIT | 가능 | NeurIPS 2025 챌린지 데이터 · BEHAVIOR-1K 1,723★ · L38 D32,062 | 상 | **4.3** |
| BEHAVIOR-1K 2026 demos | 3,411.7 GB, 2만 편·100과제 | 2026-06-30 | MIT | 가능 | 같음 · L10 D87,858 | 상 | 4.3(표본 안 봄) |
| RoboTwin 2.0 | 2,553.0 GB | 2025-05-07 / arXiv 2506.18088 | MIT | 가능 | **ICML 2026**(OpenReview) · 2,914★ · L68 D94,923 | 상 | **3.8** |
| InternData-M1 | 6,131.2 GB, 244,426편 | 2025-07-26 | CC BY-NC-SA 4.0, 게이트 | 보류(NC) | 기술 보고서(InternVLA-M1 2510.13778) · 432★ · L31 | 중상 | 4.0(미표본) |
| InternData-A1 | 8,011.1 GB, 63만 궤적(주석판 58.9만) | 2025-07-26 / arXiv 2511.16651 | CC BY-NC-SA 4.0, 게이트 | 보류(NC) | **CVPR 2026** · InternVLA-A 559★ · L108 D113,556 | 상 | 3.3(미표본) |
| RoboCasa365 (NVIDIA Kitchen-Demos) | 348.0 GB, 5.5만 편·316과제(사람) / ember MimicGen 53.6만 편 | 2026-02-10 / arXiv 2603.04356 | CC BY 4.0 (NVIDIA) / MIT (ember) | 가능 | **ICLR 2026** · robocasa 1,758★ · L42 D21,082 | 상 | 2.8 |
| GR00T X-Embodiment-Sim | 1,874.2 GB, 27만+ 궤적 | 2025-03-18(경계) | CC BY 4.0 | 가능 | GR00T N1 기술 보고서 · 8,132★ · L274 | 상 | 1.8 |
| SynGrasp-1B | 4,913.2 GB | 2026-08-18(논문 2505.03233) | **표기 없음**(HF·GitHub 둘 다) | **금지** | **CoRL 2025** · 419★ · L2 | 중 | 1.5 |
| RefSpatial | 357.2 GB, 250만 표본·2천만 QA | 2025-06-24 | Apache-2.0 | 가능 | **NeurIPS 2025** · 267★ · L24 D5,961 | 상 | **3.5**(스펙 3 전용) |
| Robo2VLM-1 | 106.5 GB(QA 수 미확인) | 2025-05-09 | Apache-2.0 | 가능 | **NeurIPS 2025 D&B spotlight** · 저장소 못 찾음 · L20 | 중상 | 2.0 |
| RoboFAC | 25.8 GB, 64,691 QA(학습 파일 실측) | 2025-05-24 | MIT | 가능 | 학회 미확인 · 46★ · L6 D10,151 | 중하 | 1.8(스펙 2 언어만) |
| RoboInter-Data / VQA | 408.0 / 150.0 GB, 23만 편 | 2026-02-03 | CC BY-NC-SA 4.0(게이트 문구) | 보류 | **ICLR 2026** · 182★ · L16 | 상 | 3.0(실물, 미표본) |
| Embodied-R1.5 SFT | 692.2 GB(일부 공개) | 2026-02-24 | Apache-2.0(카드; 원천별 상속) | 원천별 | 기술 보고서(R1은 ICLR 2026) · R1.5 58★ · L10 | 중 | 2.3 |
| Cosmos-Reason1 SFT | 85.7 GB | 2025-05-16(arXiv 2503.15558 경계) | CC BY 4.0 | 가능 | 학회 미확인 · 962★ · L31 | 중상 | 1.3 |
| MolmoAct Dataset·혼합 | 814 / 1,168 / 1,264 GB | 2025-08-10 | CC BY 4.0 | 가능 | ICRA 2026(선행 문서) · 389★ · L31 | 상 | 2.0 |
| VSI-590K | 235.9 GB | 2025-10-13 | Apache-2.0 | 가능 | **ICLR 2026**(Cambrian-S) · 569★ · L26 | 상 | 1.0 |
| InternSpatial | 671.7 GB | 2025-09-01 | CC BY-ND 4.0 | 보류(ND) | **ICLR 2026** · L3 | 중 | 1.0 |
| SPAR-7M | 155.6 GB | 2025-03-21 | MIT | 가능 | 학회 미확인 · L7 | 중하 | 1.0 |
| AgiBot Digital World | 7,635.5 GB | 2025-02-19(**1.5년 밖**) | CC BY-NC-SA 4.0, 게이트 | 보류 | — · L36 | 중 | 제외 |
| Galaxea Open-World | 13,016.3 GB | 2025-08-23 | CC BY-NC-SA 4.0, 게이트 | 보류 | 학회 미확인 · GalaxeaVLA 799★ · L53 | 중상 | 2.5(실물) |
| 자산: MolmoSpaces | 13,231.8 GB | 2025-09-19(Isaac USD 2026-02-16) | CC BY 4.0 / ODC-BY | 해당 없음 | arXiv 2602.11337 · 479★ · L51 | 중상 | 생성용 |
| 자산: cyclo_lab / robotis_mujoco_menagerie | 코드·USD·MJCF | 2025-07 / 2025-03 | Apache-2.0 | 해당 없음 | ROBOTIS 공식 · 145★ / 74★ | 제조사 | 생성용(사용 중) |

**제외(규칙)**: ShareRobot(CVPR 2025지만 arXiv 2502.21257 — 1.5년 밖, HF 라이선스 없음), RoboPoint·PixMo(2024), RoboSpatial(2411), LIBERO·MimicGen·ManiSkill 원 데이터(2023–24), `samwang1010/robotwin-failure-recovery`(개인, 카드·라이선스 없음, L1), `aaronngx/failbench-robocasa-v2`(개인, 학회 없음), LIBERO-Plus(교란 **평가** 벤치 — 학습 데이터는 성공 시연뿐, 스펙 2의 교정 라벨 아님).

## 3. 표본에서 직접 본 것

- **RoboTwin 2.0 `lift_pot/aloha-agilex_clean_50` 편 0**(114 스텝): `observation/{head,left,right,front}_camera/{rgb(JPEG), intrinsic_cv, extrinsic_cv, cam2world_gl}`, `endpose/{left,right}_endpose`(7-D)·`_gripper`, `joint_action/*`, `pointcloud`(비어 있음 — 깊이·점군은 기본 저장 끔). 머리 영상 320×240(fx 358.6), 두 그리퍼가 머리 영상에 보인다(프레임 57 확인). 지시문 파일에 같은 과제의 표현 수십 개(`seen`/`unseen`). `scene_info.json`에 물체 id·방해물·질감(깨끗한 판은 비어 있음).
- **BEHAVIOR 2025 편 10(과제 0 "turning on radio", 1,956 프레임)**: `observation.state` 256-D(BEHAVIOR 코드 `PROPRIOCEPTION_INDICES["R1Pro"]`: `eef_left_pos` 17:20, `eef_left_quat` 20:24, `gripper_left_qpos` 24:26, `eef_right_pos` 42:45 …), `observation.cam_rel_poses` 21-D(3대 × 7), `observation.task_info` 46-D, `action` 23-D. 주석 JSON = 스킬 4개("move to"·"pick up from"·"press"·"place on") × 물체 id × 프레임 구간 × 공간 접두어. 편 메타에 장면 파일·인스턴스 id 대응표. 내부값은 코드 상수(`CAMERA_INTRINSICS["R1Pro"]["head"]` fx = 306, 720×720). 머리 프레임 978: 탁자 위 라디오를 오른손이 쥐고 있고 **양쪽 그리퍼가 영상 아래에 보임** — 우리 머리 시점과 닮은 자기 중심 부감.
- **MolmoBot RBY1PickAndPlace val 꾸러미 `house_2565`**: `traj_0` 183 스텝(10 Hz). `obs/sensor_param/{head_camera,wrist_camera_l,wrist_camera_r}/{intrinsic_cv, extrinsic_cv, cam2world_gl}`, `obs/extra/tcp_pose`, `obj_start`·`obj_end`, `object_image_points/{left_gripper,right_gripper,pickup_obj,place_receptacle}/{head_camera,wrist_camera_l,wrist_camera_r}/points`(10점, 안 보이면 NaN), `grasp_state_*`(held·touching), `policy_phase` 0–5, `policy_num_retries`, `fail`·`success`, `obs_scene`(과제 문장 "Pick up the batterypack and place it in or on the matte dark gray bowl" + 지칭 표현 확률). 영상: 머리·손목 RGB, 손목 깊이 mp4. **주의**: 머리 내부값은 cx = cy = 240(480² 기준)인데 영상은 1024×576 — 해상도·화각 대응을 변환 전에 확인해야 한다 [확인 필요]. 머리 프레임은 화각이 넓고 기울어 우리 시점과는 다르다.
- **RoboCasa Kitchen-Demos PickPlaceCounterToSink**(100편): `observation.state` 16-D(베이스 위치·자세 + `eef_pos_rel`·`eef_quat_rel` + 그리퍼), `action` 12-D, `extras/episode_*/ep_meta.json`(배치·물체 범주·MJCF 경로·카메라 설정), `model.xml.gz`, `states.npz` → MuJoCo 재생으로 물체 자세·깊이 재생성 가능.
- **RefSpatial Simulator 부분**: 영상 + 깊이 PNG, 다중 턴 대화, 답 = 점 목록. 질문 예: "0.340 m 떨어진 빈 공간의 점", "가장 작은 회색 그릇과 가장 오른쪽 회색 그릇 사이 빈 공간", "두 번째로 큰 알람 시계".
- **Robo2VLM parquet 1개(앞 100행 유형)**: "그리퍼가 열려 있나"(17/100), "파지가 안정적인가", "물체까지 가는 길에 장애물이 있나", "과제를 완료했나", "어느 구성이 …" — 객관식, 실물 OXE 영상.
- **RoboFAC `training_qa.json`**: 64,691개. 유형은 과제 설명·하위 과제 분해·성공 여부·실패 하위 과제 위치·실패 원인·교정 제안(모두 자연어).

## 4. 순위 권고 — 무엇을 어디에, 변환 작업량

| 순위 | 데이터 | 쓸 곳 | 변환 | 작업량 |
|---|---|---|---|---|
| 1 | **MolmoBot RBY1 (PickAndPlace·Pick) + Franka PickAndPlace(NextTo·Color)** | 스펙 4 자기 인식 점 사전 학습("오른 그리퍼 끝을 가리켜라" → `right_gripper/head_camera/points`), 스펙 3 물체·놓을 곳 점, 스펙 1 형식 예열(머리 + 손목 영상 → 다음 `tcp_pose`) | tar.zst → h5, JSON 필드 해독, 머리 내부값·영상 해상도 대응 확인, 좌표계를 로봇 기준으로 | 중(1–2일) |
| 2 | **BEHAVIOR-1K 2025 demos** | 스펙 3(깊이 + 분할 + `task_info`로 물체 3D 위치·받침 면 QA 자동 생성), 스펙 1(스킬 구간 끝 말단 자세 = 하위 목표 라벨), 스펙 5 | 탐색 구간 잘라냄, 스킬 주석 → 하위 목표, `task_info` 배열 뜻(과제별) 해석, HEVC 영상 복호 | 중상(2–3일) |
| 3 | **RoboTwin 2.0 aloha-agilex 무작위판** | 스펙 1(양팔, 머리 + 손목), 스펙 4(보정 + `endpose` 투영), 스펙 5(방해물) | hdf5 그대로, 투영은 `extrinsic_cv`·`intrinsic_cv`로 바로 | 하(반나절–1일) |
| 4 | **RefSpatial**(또는 AI2 재포장 `Molmo2-ER-RefSpatial`·`-RoboPoint`) | 스펙 3 놓을 자리·빈 공간 점, 우리 데이터로 학습할 때 일반 그라운딩 잊음 방지 혼합(비율은 사전 등록에서) | 점 좌표 정규화만 | 하 |
| 5 | **InternData-M1**(사용자 동의 뒤) | 스펙 3·4 — 3D 상자·TCP 2D 궤적이 이미 라벨로 있음 | LeRobot v2.1, 압축 해제 스크립트 | 중(받기 전 표본 확인 필요) |
| 보조 | RoboCasa365(NVIDIA CC BY 4.0) | 스펙 5 주방 다양성, 물체 자세는 재생으로 | MuJoCo 재생 | 중상 |
| 보조 | Robo2VLM | 스펙 4의 "그리퍼 열림·파지 안정·완료" 객관식 판단 보조 | 형식 그대로 | 하 |
| 보조 | RoboFAC | 스펙 2의 실패 **설명** 능력(수치 목표 아님) | 형식 그대로 | 하 |
| 생성 자산 | **MolmoSpaces Isaac USD 물체·장면** | 우리 생성기의 물체·방해물·배경 풀 확장 | USD 불러오기·물리 속성 점검 | 중 |

- **E-TEACH-L8 쪽 권고(메인 전달용)**: 8B 추세 시험은 **자체 시뮬 참값 데이터만**으로 먼저 돈다(지금 계획 그대로). 공개 데이터는 (a) 일반 그라운딩 유지용 RefSpatial 소량 혼합, (b) 자기 인식 점 사전 학습용 MolmoBot RBY1을 **별도 팔**로 두고, 짝 비교(DEV 폐루프)에서 이득이 보일 때만 넣는다. 공개 데이터를 먼저 섞으면 우리 좌표계·카메라와 다른 분포가 들어와 결과를 흐린다.

## 5. 스펙별 판정 — 자체 시뮬 생성 대 공개 데이터

| 스펙 | 판정 | 이유 |
|---|---|---|
| 1 조종 표본 | **자체 생성** (공개는 형식 예열만) | 출력이 "우리 로봇 기준 절대 TCP 목표"라 기체·카메라·좌표계가 다르면 라벨 뜻이 바뀐다. 공개 셋은 모두 다른 기체(RBY1·R1Pro·aloha·Franka). 우리 시뮬은 같은 기체 USD(cyclo_lab FFW_SG2)·같은 카메라 설정이라 정합이 완전하다. |
| 2 복구·교란 | **자체 생성(유일)** | 수치 교정 라벨이 붙은 공개 데이터 0건. 학생 상태에서 참값 모델이 라벨을 다는 DAgger식이 필요(정본 §96). 공개는 RoboFAC(언어), MolmoBot 재시도 표시 정도. |
| 3 인식 QA | **혼합: 수치는 자체, 일반 능력은 공개** | 우리 탁자·물체의 3D 위치·크기·평면은 시뮬 참값이 정확하고 무료. 다만 실물 전이·과적합 방지를 위해 RefSpatial(놓을 자리 점), BEHAVIOR(깊이 + 분할 물체), MolmoBot(물체 점)로 다양한 장면의 그라운딩을 유지. |
| 4 자기 인식 | **자체 생성 주, 공개 사전 학습 보조** | 우리 그리퍼 모양·손목 카메라로 FK 투영 라벨이 무료(정본 §97). 다른 기체의 그리퍼 점(MolmoBot)·투영(RoboTwin)은 "그리퍼를 찾는 일반 능력" 예열에만. |
| 5 장면 다양성 | **공개가 유리 → 자산으로 흡수** | BEHAVIOR 집 50–100과제, MolmoBot procthor 집, RoboTwin 무작위화, RoboCasa 주방. 데이터 그대로보다 **MolmoSpaces 물체·장면을 우리 생성기에 넣는 쪽**이 1·2·4 정합을 유지. |
| 6 AI Worker | **자체(자산 있음), 공개 데이터 없음** | AI Worker 시뮬 데이터는 공개 0건. 시뮬 자산은 cyclo_lab(Isaac Lab, Mimic 생성 파이프라인 포함)·MuJoCo MJCF가 공식 공개. 실데이터는 ROBOTIS 조사(RB1·RB2·pickup_obj·카탈로그) 참고. |

## 6. 막힘·확인 필요

1. **게이트 동의**: InternData-A1·M1, RoboInter-Data·VQA, AgiBot, Galaxea는 HF 약관 동의 뒤에만 받을 수 있다. 우리 토큰은 현재 "not in the authorized list". 사용자가 동의해야 표본 확인이 가능하다.
2. **Astra 전송 라이선스**: CC BY-NC-SA(InternData·RoboInter·Galaxea·AgiBot)·CC BY-ND(InternSpatial)는 Astra로 보내지 않는다(해석 확인 전). 라이선스 없음(SynGrasp-1B)은 내부 전용. MIT·Apache·CC BY·ODC-BY는 가능.
3. **MolmoBot 머리 내부값 대 영상 해상도 불일치**(cx 240 대 1024×576) — 투영 라벨을 쓰기 전에 몇 프레임에서 `object_image_points`와 영상을 겹쳐 확인.
4. **BEHAVIOR `task_info` 46-D 배열 뜻**은 과제마다 다르다(과제 관련 물체 자세 목록) — 과제별 키 목록을 코드에서 뽑아야 한다 [미확인].
5. 규모: 상위 3개만 합쳐도 12 TB 이상. 과제·설정 부분 집합으로만 받는다(파드 `/data` 여유 32 TB, 공용).

## 7. 산출물 위치

- 파드 `/data/harvest/data/upper_vlm_survey/`: `raw/`(표본 원본 1.2 GB — RoboTwin zip, BEHAVIOR 편 1개, MolmoBot 샤드 1개, RoboCasa 100편, RefSpatial·Robo2VLM parquet, RoboFAC QA), `frames/`(robotwin_lift_pot·behavior·molmobot·refspatial), `code/`(위 1절 도구), `pylib/`(h5py·zstandard).
- 로컬 `D:\tools\scratch_qdd\upper_vlm_survey\`: 검색·카드 도구, `cards/`(데이터셋 카드 40여 개), `pages/`(게이트 카드 본문), `frames/`(확인한 프레임 사본).
