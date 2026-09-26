# 공개(다른 로봇) 데이터를 우리 학습 형식으로 바꾸는 방법 — 방법별 코드 근거·데이터셋별 필드 조리법·품질 관문·시제품 (2026-09-26)

작성 2026-09-26 16:4x UTC(2026-09-27 01:4x KST), 변환 방법 조사 에이전트. 보강 2026-09-26 17:5x UTC(09-27 02:5x KST): 9–12절(Franka·RBY1·RoboTwin·BEHAVIOR 보강, 좌표계 없는 오픈소스 네 트랙과 공용 추적, L 단계, E-OPEN8). 사용자 원문(user-log 119): **"1번을 할 방법을 더 자세하기 찾아봐야해"**. 여기서 '1번'은 공개 데이터를 상위 VLM(Astra 대체, 지금 8B 경향 시험 → Qwen3.5-35B-A3B, 정본 §96·§97, 가설 H-L)의 학습 형식 두 가지로 바꾸는 일이다.
- **(P) 인식 QA**: 물체 2D 점·3D 중심·크기, 탁자 평면, 말단(TCP) 영상 점과 접근 방향, 놓을 면. 답은 픽셀이나 카메라 좌표이고 `source:`·`frame:` 표시를 단다.
- **(C′) 좌표계 명시 조종**: 우리 요청 형식(머리 영상 + 손목 영상 + 그 로봇의 자동 생성 자기 정보 + 상태 + 이력)과 우리 답 JSON(평가 + 명령 하나)을 그대로 쓴다. 목표는 **그 로봇의 기저 좌표** 절대 EEF이고 `frame: base_<로봇>`을 단다. 편은 그리퍼 사건에서 우리 단계(above_target → descend_close → carry_up → carry_over → lower_open → retreat + 복구)로 자른다.
- 우선순위(통제자 전달, 사용자 대화 "몰모엑트가 한방식데로 데이터를 하면 안되나? / 우리는 몰모엑트방식으로는 데이터가 부족한가?"): **MolmoAct 방식 흐름을 맨 앞에** 둔다(1절).

중복 방지: 전체 다양성 계획·자체 시뮬 무작위화·OOD 세트는 `diversity_plan_2026-09-26.md`, 스트림 S1–S10과 규칙 1–4·E-XEMB8은 `cross_embodiment_data_use_2026-09-26.md`, 데이터 카드는 `upper_vlm_data_survey_2026-09-26.md`, 무좌표 출력 방향은 `no_metric_xyz_control_survey_2026-09-26.md`(user-log 118)에 있다. 이 문서는 **'어떻게 바꾸나'의 세부**만 다룬다.

유료 0원, GPU 0. 논문 본문(arXiv HTML)·공개 코드(얕은 클론)·HF API·카드·표본 행만 읽었다. 시제품은 파드 CPU로 돌렸다. 게이트 데이터는 약관 동의를 하지 않았다(목록만 4.7절). 규칙: 1.5년(2025-03-26 이후; 그 전은 **[기초]**), 신뢰도(원문 "신뢰도 낮은 논문과 깃 저장소는 최대한 쓰지 않는다. 쓰느니만 못하다." / "신뢰도가 무조건 있어야 하고, 스타도 어느 정도 있어야 하고, 논문도 좋아요(반응)를 많이 받은 것이어야 한다.").

## 0. 결론 요약

1. **MolmoAct 방식**(그리퍼 점·궤적, 픽셀)
   - 공개분(CC BY 4.0, 약 1,000만 프레임, 집어 놓기 약 76 %)만으로 **P-점·궤적 흐름의 양은 넘친다**.
   - 그러나 **충분하지 않다**. 기저 좌표 조종 목표(C′)가 0이고, 3D·m·평면 정보도 없다(상대 깊이 토큰뿐). 포인팅 궤적에는 품질 필터가 없다.
   - 보정이 있는 원천에서는 Molmo 포인팅 대신 **FK + 보정 투영**(HAMSTER[기초] 방식)이 정확하고 공짜다. 시제품에서 그리퍼 위에 떨어진 비율은 BEHAVIOR 100 %, MolmoBot 눈 확인 ≥ 97 %였다.
2. **남들의 변환**(2절)
   - Robo2VLM: 그리퍼 열림 상태 기계(0.4/0.9) + 깊이 차 ≥ 5 cm 점 + 각도 간격 오답.
   - HAMSTER[기초]: FK 투영 + RDP ε 0.05 + 그리퍼 토큰 + extrinsic 정렬 필터.
   - X-VLA: 데이터셋별 핸들러, 좌표는 그 로봇 기저 그대로 + 출처 표시.
   - InternVLA-M1·RoboBrain: 시뮬 특권 정보로 라벨.
   - RefSpatial: 로봇 편을 쓰지 않고, 생성 코드는 비공개.
   - 공통 함정: 쿼터니언 순서, 외부값 방향, TCP 대 끝 링크, K 해상도.
3. **데이터셋별 조리법**(4절). C′ 주원천은 위에서 잡는 비율로 고른다.
   - **MolmoBot Franka**(위에서 잡기 93 %, 계획기 단계 10종이 우리 6단계에 대응, ODC-BY)
   - **RoboTwin 2.0**(73 %, MIT)
   - BEHAVIOR(29 %, 대신 깊이 + 분할 + 과제 물체 GT로 P-3D·평면이 가장 좋음)
   - MolmoBot RBY1(측정 엇갈림 20 % 또는 80 % — 다시 잰다)
   - DROID[기초]는 실물 C′ 2순위다(개선 보정 약 3.6만 편, 물체 GT 없음).
4. **시제품**(6절, 무료 CPU)
   - 변환기 3개와 시험 31개. P 1,145개(MolmoBot 877 · BEHAVIOR 222 · RoboTwin 46), C′ 54개(MolmoBot 42 · RoboTwin 12).
   - 관문:
     - G1 EE가 그리퍼 위: BEHAVIOR 37/37, MolmoBot 자동 90.2 %·눈 ≥ 97 %, RoboTwin 눈 9/9.
     - G6 MolmoBot 보정 자기 검사: 2.2 px.
     - G7 단계 ↔ 계획기 일치: 94.2 %.
     - G5 탁자 평면: 61/61.
     - **G2 3D 중심(분할 ∩ 깊이 − GT) 9.1 cm → 불통**. 겉면 편향 −8.6 cm 때문이다. → 3D 답은 GT에서만 만든다.
5. **C′를 막는 것**: 잡는 자세(위에서 잡기 필터), 바퀴 기저 이동, 명령 대 실제 자세, 공개 깊이의 뜻 차이, 좌표 누수. 누수 시험(5.1)이 0이어야 섞는다.
6. **보강 실행(9절, 2026-09-27)**
   - 받은 것 약 17 GB.
   - **MolmoBot Franka**: 277편, 위에서 잡기 **93.7 %**, 단계 일치 95.4 %, **C′ 3,381**.
   - **RBY1** 50편: 위에서 잡기 **40 %**(엇갈림 해소).
   - **RoboTwin**: `robot_pose` 기저로 고쳤다. 집어 놓기 8과제에서 C′ 353.
   - **BEHAVIOR 50과제 × 2편**: 인식 QA 53,605, 위에서 잡기 31 %, C′ 기저 정지 39 %.
7. **좌표계 없는 오픈소스(10절, user-log 123)**: 네 트랙과 공용 추적 앞단을 구현했다. 대상은 **RB2(AI Worker 실데이터)**와 **MolmoAct OXE 행**이다.
   - **T0**: 궤적 3,200개.
   - **공용 추적 + 포인팅 일치**: RB2 점 6,746·궤적 2,638.
   - **④ C′(`camera: unknown`)**: RB2 3,073.
   - **T1 자체 보정**
     - 보정을 숨긴 Franka에서 정확한 2D를 주면 참 TCP 재투영 **0.81 px**(관문 ≤ 5 px 통과)였다. 포인팅·추적 2D로는 **24–26 px**로 불통이었다. 씨앗 편향 탓이다.
     - RB2: 초점 373(사양 367), 보류 재투영 21–28 px로 **불통**이다. 그래서 RB2는 카메라 정보가 든 표본 0개다.
     - 추적은 편 사이 카메라 흔들림을 25° → 13.5°로 줄였다.
   - **T3(MoGe-2)**: 물체 중심 17.5 cm·평면 7.7 cm로 **불통**이라 순서형 QA만 만든다. 초점 추정은 RB2 385로 T1 초기값감이다.
   - **L 단계**: Molmo2 포인팅이 옳은 그리퍼를 찍은 비율 65.5 %(MolmoBot)·48.2 %(BEHAVIOR). 추적 오차 중앙 19 px.
8. **E-OPEN8(12절)**: 오픈소스만으로 6,500행을 만들었다(L8 한 에폭 크기). 사전 등록 초안은 `prereg_open8.md`, E-XEMB8 초안은 `prereg_xemb8.md`다.

## 1. MolmoAct 방식 — 맨 앞 (공개 데이터·변환 코드·우리에게 늘리는 법·양 판정)

**신뢰도**: arXiv 2508.07917(2025-08-11), OpenReview에 ICRA 2026과 CoRL 2025 Robot Data Workshop, allenai/molmoact 389★, HF MolmoAct-7B-D-0812 좋아요 53. 1.5년 안이다.

### 1.1 공개 데이터 (HF API·카드·실제 행으로 확인)

| 저장소 | 라이선스 | 크기 | 행 | 좋아요 | 원천 |
|---|---|---|---|---|---|
| `allenai/MolmoAct-Pretraining-Mixture` | CC BY 4.0 | 1,167.9 GB | bc_z 10,289,224 · fractal(RT-1) 7,065,568 · bridge 3,746,468 · auxiliary_depth 1.5M · auxiliary_trace 1.5M · lvis 124,108 | 14 | OXE 실물(RT-1·Bridge·BC-Z) |
| `allenai/MolmoAct-Midtraining-Mixture` | CC BY 4.0 | 1,264.3 GB | home_primary·home_secondary 각 1,977,450, tabletop_primary·tabletop_secondary 각 987,748 | 6 | 자체 Franka(외부 1 + 손목 1, 640×480) |
| `allenai/MolmoAct-Dataset` | CC BY 4.0 | 814.4 GB | 10,689 궤적·93과제(가정 7,730/73, 탁상 2,959/20) | 31 | 자체 Franka 원본(LeRobot) |

- **필드**: `image`(jpg), `conversations{from,value}`, `annotation`(문자열). 행은 두 종류다.
  - 추론형: 답에 깊이 토큰 + 궤적 + 행동 토큰이 들어가고, annotation은 null이다.
  - 궤적 조건형: annotation에 궤적이 있고, 학습할 때 그 궤적을 영상 위에 그린다.
  - 두 종류의 합이 논문의 1,050만 + 1,050만과 맞는다. 그래서 **원 프레임 수는 행 수의 약 절반**이다.
- **궤적 형식**: `[[x, y], ...]` 1–5점, 정수 0–255, 영상 크기로 정규화한 값이다. 예를 들어 213×171 영상에서 y = 181이 나온다.
- **깊이 형식**: `<DEPTH_START>` + `<DEPTH_k>` 100개(k < 128) + `<DEPTH_END>`.
- **영상 크기**: Bridge 320×240, RT-1 320×256, BC-Z 213×171.
- **출처 칸**: 행 안에 출처 칸이 없다. 설정 이름이 곧 출처다.
- **로봇 행 몫**(사전 학습 혼합): BC-Z 48.8 %, RT-1 33.5 %, Bridge 17.8 %, 자체 Franka 0 %. 논문의 표집 비율은 RT-1 20 %, Bridge 12.5 %, BC-Z 7.5 %다.
- **집어 놓기 몫**: datasets-server 무작위 표본으로 쟀고, 정규식은 place·put·move다.
  - BC-Z는 33행 중 76 %, RT-1은 29행 중 76 %다. 나머지는 서랍 여닫기, 넘어뜨리기, 세우기다.
  - Bridge와 Midtraining은 서버가 응답하지 않아 재지 못했다.
  - 이 값은 표본이 작으니 대략으로만 본다.

### 1.2 변환 코드 (공개, `allenai/molmoact`)

- **진입점**: `preprocess/action_reasoning_data.py` `DatasetProcessor.process_dataset`. LeRobot repo_id를 받고, 기본값은 `--line-length 5 --action-bins 256 --action-chunk-size 8`이다.
- **포인팅**: `preprocess/line_utils.py:point_at_gripper`.
  - 모델 `allenai/Molmo-7B-D-0924`, 탐욕 복호, 새 토큰 최대 448.
  - 프롬프트 원문은 **`"point to the robot gripper"`**다. 양팔일 때 논문은 "…on the left/right"를 쓴다.
  - 출력 `<point x= y=>`(0–100 %)를 원 영상 픽셀로 바꾼다.
- **프레임 선택**: 편의 **모든 프레임**을 쓴다. 손목이 아닌 첫 영상 키를 쓴다(`collect_gripper_points`).
- **궤적 구성**: `processors.py:Trace.subsample_to_line`.
  - 지금 프레임부터 편 끝까지의 유효 점에서 `np.linspace`로 5점을 고른다(지금·끝 포함). 5개 이하면 전부 쓴다.
  - 유효 점이 없으면 `[지금 점]`을 쓴다. 이 점도 None일 수 있다.
- **필터**: 파싱에 실패한 점(None)만 버린다. **이상치·범위·신뢰도 필터는 없다.** 공개 Bridge 행에 `[[142,30],[158,150],[105,59],…]`처럼 크게 튀는 궤적이 실제로 있다.
- **함정 — 좌표 정규화**: 공개 전처리는 궤적을 **원 픽셀**로 저장한다. 그런데 학습 로더 `olmo/data/image_preprocessor.py:load_image`는 그 값을 0–255로 보고 `(w − 1)/255`를 곱한다.
  - 256 px LIBERO에서만 맞는다. HF 공개 데이터는 이미 0–255다.
  - **우리가 이 코드를 다시 돌리면 0–255 정규화를 반드시 넣어야 한다.**
- **깊이**: `processors.py:Depth`·`DepthTokens`.
  - Depth-Anything-V2 **ViT-B**(입력 518)로 깊이를 구하고, 영상마다 min–max로 uint8에 맞춘다. **상대 깊이이지 m 단위가 아니다.**
  - 320×320으로 바꿔 VQ-VAE(코드 128개, 코드 차원 512, 축소 32)에 넣으면 10×10 = **100토큰**이 나온다.
  - VQ-VAE는 RT-1·Bridge·BC-Z 깊이 1,000만 장으로 20에폭 학습했다. 체크포인트 `vae-final.pt`가 공개돼 있다.
- **행동**: 앞 6차원은 q01·q99로 [−1, 1]에 맞추고, 그리퍼는 `1 − g`로 뒤집는다. 256칸으로 나눠 8스텝 묶음으로 만든다.
- **학습 형식** (`olmo/data/custom_lerobot_dataset.py`):
  - 추론형 : 궤적 조건형 = 50 : 50.
  - 이상한 점: 답에 'left end effector'와 'right end effector' 궤적으로 **같은 궤적을 두 번** 넣는다.
- **후속작**: MolmoAct2(arXiv 2605.02881, 773★) 본문에는 영상 궤적이 **없다**. 깊이 토큰만 남았다. 궤적 표현의 효용은 저자들도 계속 유지하지 않았다는 뜻이다(해석).

### 1.3 우리에게 늘리는 법

- **Bridge·RT-1·BC-Z**: 이미 변환된 CC BY 행이 있어 **다시 돌리지 않는다.** 궤적은 0–255 → 영상 픽셀로 풀어 우리 P 형식으로 옮긴다.
  - 예: `{"point": [u, v]}`, `{"trace": [[u, v], …]}`.
  - 머리 줄은 `source: molmoact/<bridge|rt1|bcz>`, `frame: pixel`이다.
  - **품질 필터를 새로 단다**: 연속 점 사이 튐이 영상 폭의 40 % 초과면 버린다. 첫 점이 영상 밖이면 버린다.
- **보정이 있는 원천은 포인팅 모델 대신 FK 투영을 쓴다** (HAMSTER[기초]의 방식, 3절).
  - 원천: BEHAVIOR·RoboTwin·MolmoBot/MolmoSpaces(시뮬 GT 보정)과 DROID(실물 보정, 품질 필터 필요).
  - 이유: Molmo 포인팅은 우리 실측에서 원시 21–30 %였다(`auto_context` 8절). 투영은 공짜이고, 이번 시제품에서 그리퍼 위에 떨어진 비율이 BEHAVIOR 37/37, MolmoBot 눈 확인 ≥ 95 %(6절)였다.
  - 궤적은 투영점을 RDP(ε = 0.05, 정규화 좌표)로 줄이고 그리퍼 사건 토큰을 끼운다.
- **깊이 토큰**은 쓰지 않는다. 우리 §97은 **m 단위 깊이**(시뮬 GT·실물 스테레오)를 가정한다. MolmoAct 깊이는 영상별 min–max 상대 깊이라 뜻이 다르다.
- **우리 P 흐름과의 대응**:

  | MolmoAct 형식 | 우리 형식 | 머리 줄 |
  |---|---|---|
  | 그리퍼 점 | `ee_point` | `frame: pixel` |
  | 궤적 | `ee_trace` | `frame: pixel` |

  - **MolmoAct 방식은 기저 좌표 조종 목표를 주지 않는다.** 행동 토큰은 그 로봇의 정규화된 관절·EEF 차이이고, 좌표계·카메라가 행에 없다. 그래서 C′로 바꿀 수 없다. C′는 보정 + EE 자세 + 그리퍼 상태가 있는 원천(3·4절)에서만 만든다.

### 1.4 양 판정 — MolmoAct 방식만으로 충분한가

- **P(인식) 양으로는 넘친다.**
  - 사전 학습 혼합의 궤적 행: 추론형 약 1,050만 + auxiliary_trace 150만.
  - 원 프레임은 약 1,050만이고, 그중 집어 놓기류는 표본 기준 약 76 %다.
  - 우리 35B 1차 공개 인식 몫 목표는 약 10만(`cross_embodiment` 3.1 S3–S6 합)이다. **궤적 행 100개 중 1개만 써도 채운다.**
- **그러나 아니다(부족하다)**: 세 가지 이유가 있다.
  - (a) **C′ = 0.** 기저 좌표·카메라·그리퍼 폭이 행에 없다. 우리 실패 지점인 '영상 → 3D → 기저 좌표' 사상을 가르치지 못한다.
  - (b) **3D·m 정보가 없다.** 상대 깊이 토큰뿐이라 물체 3D 중심, 탁자 평면, 크기 QA를 만들 수 없다.
  - (c) **라벨 품질.** Molmo 포인팅 궤적에 필터가 없다. 실물 OXE 3원천(3개 로봇·실험실 장면)으로 다양성이 좁다. 행 수의 절반은 같은 프레임을 궤적 조건형으로 되풀이한 것이다.
- **결론**: MolmoAct 방식은 **'그리퍼 점·궤적(pixel) P 흐름'의 원천으로 충분하고 가장 싸다.** 다만 '3D·평면 P'와 'C′'는 보정·깊이가 있는 시뮬 원천(BEHAVIOR·MolmoBot·RoboTwin)에서 투영으로 만들어야 한다.
- 수치 비교(35B 1차 목표, `cross_embodiment` 3.1 기준):

  | 흐름 | 목표 | MolmoAct 공개분 |
  |---|---|---|
  | P-점·궤적 | 약 2만–4만 | 약 1,000만 프레임 |
  | P-3D·평면 | 약 5만 | 0 |
  | C′ | 실험 팔, 약 1만 [추정] | 0 |

## 2. 남들의 변환 — 방법별 코드 근거 (공개 코드에서 확인한 것만; 비공개는 '비공개')

### 2.1 Robo2VLM — 그리퍼 단계 분할 + 템플릿 QA (NeurIPS 2025 D&B spotlight)
- **신뢰도**: arXiv 2505.15517. KeplerC/robo2VLM 30★(라이선스 표기 없음 — 코드는 참고만 하고 복사하지 않는다). HF `keplerccc/Robo2VLM-1` Apache-2.0, 106.5 GB, 좋아요 20. 별이 적어 학회 채택을 근거로 쓴다.
- **코드**:
  - `generation/utils.py`: `determine_grasp_phases(grasp_threshold=0.4, contact_threshold=0.9)`, `project_point_to_image`, `get_target_object`.
  - 템플릿은 `generation/vqa.py`에 있다.
  - 쓰는 템플릿 목록은 `generation/droid_trajectory.py:generate_vqa_data`에 있다.
- **단계 분할**: 신호는 그리퍼 위치 하나다.
  - 편 안에서 min–max로 0(열림)–1(닫힘)에 맞춘다.
  - 상태 기계: pre_grasp → immobilization(> 0.4이고 닫히는 중) → contact(≥ 0.9) → detach(< 0.9이고 열리는 중) → post_grasp(≤ 0.4), 그리고 transition.
  - 논문의 힘 문턱 τ_f는 **공개 코드에 없다**.
  - 핵심 프레임 = 단계 구간마다 무작위 1장 + 첫·끝 프레임.
- **보정 사용 (DROID)**:
  - extrinsic: `cam2base_extrinsic_superset.json` → `cam2base_extrinsics.json` → `cam2cam_extrinsics.json` 순으로 찾는다. 값은 [x, y, z, rx, ry, rz]이고, `Rotation.from_euler('xyz')`로 cam → base를 만든 뒤 역행렬을 쓴다.
  - intrinsic: ZED SVO 보정을 쓰고, 실패하면 fx 733.37·cx 625.26·cy 361.92(1280×720) 상수로 대신한다.
  - 깊이: ZED `DEPTH_MODE.QUALITY`, 최소 0.2 m.
- **품질 필터**:
  - 상대 깊이 문항: 깊이 0.1–5 m, 유효 픽셀 ≥ 100, 테두리 20 px 제외, 점 5개 사이 깊이 차 ≥ 5 cm(안 되면 2 cm).
  - 방향 문항: 오답 화살표가 정답과 30° 이상 떨어진다.
  - 모든 문항의 20 %는 정답을 'None of the above'로 바꾼다.
  - 다중 시점: 투영점이 영상 밖이면 버린다.
  - 논문: 궤적 17.6만 → 문항 약 300만 → 선별 684,710.
- **보고·발견된 함정**:
  - 논문: 보정이 틀리면 VQA 품질이 떨어진다.
  - 코드 결함:
    - `vqa_object_reachable`이 늘 '장애물 없음'을 정답으로 낸다.
    - `relative_direction`의 부호가 뒤집혀 있고 abs가 빠졌다(DROID에서는 주석 처리됨).
    - `multi_view`가 미래 스텝을 계산해 놓고 현재 스텝을 쓴다.
    - 그리퍼 열림 문턱이 0.8로, 분할의 0.4·0.9와 다르다.
- **가져올 것**:
  - 단계 상태 기계의 발상(우리 `steps.py`는 열림 비율 + 이력 문턱 + '쥠 여부'로 같은 일을 한다).
  - 깊이 차가 보장된 점 문항.
  - 각도 간격을 둔 오답.
  - 위 결함은 가져오지 않는다.

### 2.2 RoboRefer / RefSpatial — 깊이 + 검출 → 3D QA (NeurIPS 2025)
- **신뢰도**: arXiv 2506.04308, Zhoues/RoboRefer 267★, HF `JingkunAn/RefSpatial` Apache-2.0, 357 GB, 좋아요 24.
- **로봇 편을 입력으로 쓰지 않는다.** 원천은 OpenImages 2D, CA-1M 3D 영상, Infinigen·Objaverse 시뮬이다. **생성 코드는 비공개**다(README TODO에 "Release the Dataset Generation Pipeline"이 남아 있다).
- **단계** (논문 부록 B):
  1. SigLIP2(giant-opt-patch16-384)로 긍정·부정 라벨을 걸러 170만 → 93.4만 장, Qwen2.5-VL로 다시 걸러 46.6만 장을 남긴다.
  2. RAM 태그를 GroundingDINO 상자 프롬프트로 쓴다. Florence-2는 중복 상자가 많아 뺐다.
  3. SAM2.1 마스크 + UniDepthV2 m 깊이 + WildeCamera 내부값으로 물체 점군과 축 정렬 3D 상자를 만든다.
  4. Qwen2.5-VL과 규칙으로 계층형 지칭('왼쪽에서 세 번째 컵')을 만들고, 템플릿·LLM으로 QA를 만든다.
  5. CA-1M: 200만 → 10만 프레임. 검출 문턱을 낮춰 후보를 많이 만든 뒤, GT 3D 상자와 IoU 양방향 1 : 1로 맞춰 의미 없는 상자를 버린다.
- **점 형식**: `[(x, y)]`, [0, 1], 소수 셋째 자리.
- **가져올 것**:
  - '침식한 마스크 안의 점'. MolmoSpaces `ObjectImagePointsSensor`도 GT 마스크를 2회 침식한 뒤 10점을 뽑는다.
  - GT와 1 : 1 매칭하는 필터.
  - S9(일반 공간)은 형식만 바꿔 쓴다.

### 2.3 HAMSTER [기초] — FK + 보정 투영으로 2D 경로 (ICLR 2025, 1.5년 밖)
- **신뢰도**: arXiv 2502.05485, ICLR 2025 poster. 공식 liyi14/HAMSTER_beta 66★에는 서버·gradio 예제만 있고, **데이터 생성 코드는 비공개**다. 기초 연구라 방법만 가져온다.
- **단계** (논문 부록):
  - 규모: Bridge 1만 + DROID 약 4.5만 궤적 → 2D 궤적 11만. RLBench 81/103과제 × 1,000편 × 지시문 약 4개 → 32만.
  - Bridge는 보정이 없다. 편마다 몇 프레임에서 **그리퍼 손가락 중심을 손으로 찍고**, EE 자세와 PnP로 투영 행렬을 추정한다. 투영이 어긋나면 그 편을 빼고 다시 추정한다.
  - DROID는 **투영 깊이와 RGB가 안 맞는 extrinsic**의 궤적을 뺀다. 남는 것이 약 4.5만 시점-궤적(고유 약 2.2만)이다.
  - 경로 단순화: RDP ε = 0.05(정규화 좌표), 궤적당 약 2–5점.
  - 출력: `<ans>[(x,y), <action>Close Gripper</action>, …]</ans>`, 0–1 실수. 그리퍼는 숫자가 아니라 토큰이다.
- **보고된 함정**: 3B 모델에서 RDP 경로가 20점 고정 경로보다 성능이 훨씬 좋았다.
- **가져올 것**: 'FK 투영 → RDP → 그리퍼 토큰'과 extrinsic 정렬 필터. 우리 관문 3·5절의 '투영점이 그리퍼 위' 검사가 같은 역할이다.

### 2.4 X-VLA — 여러 기체를 절대 EEF xyz + Rotate6D + 그리퍼로 (ICLR 2026 poster)
- **신뢰도**: arXiv 2510.10274, 2toinf/X-VLA 734★, HF X-VLA-Pt 좋아요 14.
- **코드**:
  - 데이터셋별 핸들러: `datasets/domain_handler/{droid, simulations(RT1·Bridge·Calvin·libero·VLABench·RobotWin2·robocasa), robomind, agiworld, real_world, x2robot, lerobotv21, lerobot_agibot}.py`.
  - 공통: `base.py:BaseHDF5Handler.iter_episode`.
  - 변환: `utils.py:quat_to_rotate6d / euler_to_rotate6d / rotate6d_to_quat`.
  - 가중·도메인 ID: `domain_config.py`(Droid-Left·Right 각 0.15, AGIBOT 0.4 등).
- **형식**:
  - 팔당 10차원(xyz + rot6d + 그리퍼 1 = 닫힘), 양팔 20차원.
  - **좌표계는 각 데이터셋 proprio 그대로**다. DROID는 base이고, 카메라 좌표로 바꾸지 않는다.
  - 시간축은 `interp1d`로 보간하고, 데이터셋별 (주파수, 미래 길이)는 DROID 15 Hz/4 s, RT-1 3/10, Bridge 5/5, RoboTwin 30/1이다.
  - 정지 구간(차 < 1e−5)은 건너뛴다.
- **함정**:
  - rot6d가 `as_matrix()[..., :, :2].reshape(6)`로 첫 두 **열**을 행 순서로 섞어 편다. Zhou 원 논문과 순서가 다르다.
  - `quat_to_rotate6d` 기본이 xyzw인데 RoboTwin endpose는 **wxyz**다. 핸들러가 xyzw로 읽는 것으로 보인다(추정, 확인 필요). 학습·평가는 일관되지만 회전의 뜻이 다른 데이터셋과 어긋날 수 있다.
  - 그리퍼 규약이 데이터셋마다 다르다: Bridge `1 − action`, RoboTwin `1 − g`, Calvin `< 0`, robomind 양팔 `> 2.5`.
- **가져올 것**:
  - 데이터셋별 핸들러 구조(우리 `src_*.py`).
  - '좌표는 그 로봇 기저 그대로 + 출처 표시'(우리 C′의 `frame: base_<로봇>`).
  - **쿼터니언 순서·그리퍼 규약을 원천마다 시험으로 고정**한다(우리 `test_xemb_geom.py`).

### 2.5 InternVLA-M1 / RoboBrain 2.0 — 그라운딩 데이터 구성
- **InternVLA-M1**: arXiv 2510.13778, 기술 보고서, 432★(코드 MIT, 모델 CC BY-NC-SA 4.0).
  - 상자·점·궤적 라벨은 GenManip·Isaac 시뮬 렌더러의 **특권 정보**(상자·2D EE 궤적 직접 출력)에서 나왔다. 카메라는 ArUco로 실물과 맞췄다.
  - **실물 편에서 라벨을 만드는 코드는 없다**(`qwen_data_config.py`에는 JSON 경로만 있다).
  - 필터: Pixmo-Points는 1024 px 초과 영상을 빼고, 영상당 점 10개까지만 쓴다. 좌표는 절대 픽셀이다.
  - 궤적 QA 약 68.4만은 A0 ManiSkill·InternData-M1·MolmoAct에서 왔다.
  - InternData-M1(CC BY-NC-SA, 게이트) 필드:
    - `annotation.{base_view, base_view_2, ego_view}.tcp_2d_trace`
    - `bbox2d_tight/loose`
    - `annotation.tcp_3d_trace`
    - `bbox3d`
    - `pick_obj_uid / place_obj_uid`
    - `diverse_instructions`
  - → 우리 라벨 칸의 참고본으로만 쓴다.
- **RoboBrain 2.0**: arXiv 2507.02029, 학회 미확인, FlagOpen/RoboBrain2.5 1,146★, HF 7B 좋아요 127.
  - 공개 스크립트는 추론용뿐이다.
  - 점·상자 데이터는 LVIS, Pixmo(점 10개 제한, 템플릿 28개), RoboPoint(절대 좌표로 변환)이고, RefSpatial 파이프라인을 다시 썼다.
  - **로봇 궤적 데이터를 어떻게 만들었는지는 논문에 없다**(ShareRobot 인용뿐).
- **요약**: 두 곳 모두 '시뮬 특권 정보로 라벨'이다. 우리 시제품(BEHAVIOR·MolmoBot·RoboTwin의 GT·보정 사용)과 같은 쪽이다.

### 2.6 로더·좌표 규약 (원천별 — 틀리기 쉬운 곳)

| 원천 | 코드 위치 | EE 자세 | 쿼터니언 | 외부값 방향 | 내부값 | 확인 |
|---|---|---|---|---|---|---|
| LeRobot DROID (lerobot 27.8k★, `lerobot/droid_1.0.1` Apache-2.0 태그) | `examples/port_datasets/port_droid.py:generate_lerobot_frames` | `observation.state.cartesian_position` [x,y,z,roll,pitch,yaw] base, m·rad | 오일러 | `camera_extrinsics.{wrist_left, exterior_1_left, exterior_2_left}` 6-D cam → base(`from_euler('xyz')`, Robo2VLM 해석) | **RLDS에 없음** — ZED 1280×720 K를 320×180이면 0.25배 | 코드 |
| BEHAVIOR-1K 2025 (1,723★) | v3.7.2 `learning/utils/obs_utils.py:depth_to_pcd`·`eval_utils.py` | state 256의 `eef_right_pos` 225:228, `eef_right_quat` 228:232, base 기준 | **xyzw** | `cam_rel_poses` cam → base, GL 축(x축 180° 추가) | head fx 306 (720²), 손목 388.66 (480²) 코드 상수 | 코드 + **실측**(4.2) |
| RoboTwin 2.0 (ICML 2026, 2,914★) | `envs/camera/camera.py:get_config`, `envs/robot/robot.py:_trans_endpose` | `endpose` [x,y,z,**qw,qx,qy,qz**] world, **끝 링크(TCP 아님, gripper_bias − 0.12)** | wxyz | `extrinsic_cv` world → cam(CV), `cam2world_gl` cam → world(GL) | `intrinsic_cv` (저장 JPEG 크기) | 코드 + 실측 |
| MolmoSpaces / MolmoBot (479★ / 108★) | `molmo_spaces/env/sensors.py:ObjectImagePointsSensor`, `camera_manager.py:get_pose` | `actions/ee_pose` 부위별 base 기준 [x,y,z,qw,qx,qy,qz] | wxyz(`scalar_first=True`) | `extrinsic_cv` world → cam(CV); `cam2world_gl`은 **이름과 달리 CV 축 cam → world**(단순 역행렬) | f = (H/2)/tan(fovy/2) — 표본은 **480² 기준 K인데 영상은 1024×576**(4.1) | 코드 + 실측 |

- 버전 함정 셋:
  - (1) BEHAVIOR **현재 main**의 `PROPRIOCEPTION_INDICES`는 eef_left_pos 17:20·eef_right 42:45다. 2025 데이터(256-D)에서는 이 값이 틀린다. v3.7.2의 186:189·225:228이 맞다. 실측: 17:20은 거의 0, 225:228은 (0.12, −0.25, 0.44) m, 쿼터니언 노름 1.0.
  - (2) BEHAVIOR 현재 코드는 `observation.robot2cam_pose.{cam}`을 쓰지만 2025 데이터에는 `cam_rel_poses`만 있다.
  - (3) BEHAVIOR 현재 `CAMERA_EXTRINSICS`에 내부값을 잘못 복사한 버그가 있다.
- RoboTwin의 새 xpolicylab hdf5(`pkl2hdf5.py:create_xpolicylab_hdf5`)는 `vision/<cam>/extrinsics_matrix`에 cam2world_gl을 우선 넣고, 없으면 extrinsic_cv를 넣는다. **방향이 반대인 두 행렬이 같은 이름으로 저장될 수 있다.** → 편마다 '투영점이 그리퍼 위' 관문으로 방향을 판별한다.

## 3. 공통 변환 절차 (모든 원천에 같은 순서 — `tools/xemb/`)

1. **좌표 규약을 시험으로 고정한다** (`geom.py`, `test_xemb_geom.py`).
   - 쿼터니언 순서: MolmoBot·RoboTwin은 wxyz, BEHAVIOR는 xyzw.
   - 외부값 방향: world → cam(CV)인지, cam → world(GL)인지.
   - 내부값의 해상도.
   - 원천마다 표본 몇 프레임을 겹쳐 그려 **G1(EE가 그리퍼 위)이 맞는 조합**을 고른다. 이번에는 MolmoBot K 해상도와 RoboTwin TCP 오프셋을 이렇게 골랐다.
2. **자세를 '그 로봇 기저' 기준으로 모은다.**
   - BEHAVIOR·MolmoBot EE: 이미 기저 기준이다.
   - RoboTwin: 세계 좌표를 우리 축(x 앞·y 왼·z 위)으로 돌린다.
   - 물체 GT: 세계 → 기저. 바퀴형은 프레임마다 기저 자세를 쓴다.
   - 카메라: T_base_cam(CV).
3. **P 표본** (프레임 표집 간격: MolmoBot 1 s, BEHAVIOR 2 s, RoboTwin 0.2 s 상당).
   - `ee_point`: EE/TCP 투영 픽셀.
   - `ee_approach_cam`: 접근축의 카메라 좌표 단위 벡터.
   - `obj_point`: 물체 마스크 또는 데이터셋 물체 점의 중심 픽셀.
   - `place_point`: 놓을 곳 점.
   - `obj_center_cam`: GT 중심의 카메라 좌표(m).
   - `table_plane_cam`: 탁자 마스크 ∩ 깊이 RANSAC 평면(n, d).
   - 요청 첫 두 줄은 `source: <원천>/<로봇>`, `frame: pixel | cam_<이름>`이다. 그 아래 카메라 한 줄(해상도·fx fy cx cy·기저 기준 자세)을 쓰고, 질문과 'Return JSON only'를 붙인다.
   - 답은 `{"point": [u, v]}`, `{"xyz_cam": [x, y, z]}`, `{"dir_cam": …}`, `{"normal_cam": …, "d_m": …}` 중 하나다.
   - **우리 런타임 답 칸(`command.position_m`)은 쓰지 않는다**(규칙 1).
4. **C′ 표본** (`steps.py`).
   - 열림 비율(원천별로 측정값 또는 명령)을 이력 문턱으로 닫힘/열림으로 바꾼다.
   - 쥠 신호(원천별: 닫힌 구간 최소 열림 > 3 %, 또는 데이터셋 쥠 표시)로 빈 닫힘과 쥔 닫힘을 가른다.
   - 사건 사이를 우리 단계로 자른다. 각 단계 구간의 라벨은 **구간 끝 EE 위치**(그 로봇 기저, m)와 그리퍼다.
   - 빈 닫힘: 그 앞의 접근을 버리고, 닫힌 프레임에 `reopen`(gripper open)을 붙인다.
   - 쥔 채 떨어뜨림: carry_up 뒤를 자른다.
   - 구간마다 2프레임을 뽑는다(`sample_frames`).
   - 요청 = 자동 자기 정보(아래 5) + TASK + NOW(TCP·열림) + 이력(앞 구간 목표) + **우리 런타임 답 명세 그대로**(`fmt.ANSWER == harvest/astra_solo/prompts.ANSWER`, 시험으로 고정).
   - 답 = 우리 스키마(`validate` 통과). **`frame`은 요청에만** 둔다.
   - 필터: G8 위에서 잡기(≤ 30°), G9 기저 정지.
5. **자기 정보 블록 자동 생성** (`fmt.self_info`, §97 '로봇 자기 정보는 로봇에서').
   - 원천의 로봇 모델·보정에서만 만든다(손으로 쓴 숫자 금지):
     - 로봇 이름·팔.
     - 기저 좌표 규약.
     - 그리퍼 최대 폭: MolmoBot qpos 0.05 × 2, BEHAVIOR 손가락 qpos 합 0.10 m, RoboTwin 0.08 m는 MJCF/URDF 한계로 바꿀 것 [확인 필요].
     - 데이터에서 본 TCP 범위(1–99 백분위).
     - 카메라별 해상도·내부값·T_base_cam(머리). 손목은 '손과 함께 움직임'.
   - 로봇 모델 파일(4절 표)의 관절 한계·그리퍼 링크 길이로 채울 칸(손가락 길이·TCP 정의)은 다음 단계다. 지금은 데이터에서 잰 값만 넣었다.
6. **관문과 필터**(5절) → `gates.json`.
7. **눈 확인**: 겹쳐 그림 판(무작위 36 + 불통 24)을 사람이 본다. 불통의 대부분이 한 원인(TCP 정의·명령 앞섬)이면 규칙을 고치고 다시 돌린다.

## 4. 데이터셋별 필드 조리법

실측은 이 에이전트의 시제품(6절)과 데이터 조사 보조 에이전트의 표본 측정(`D:\tools\scratch_qdd\xemb_data\`)에서 나왔다. 보조 측정 표본은 BEHAVIOR 10편, MolmoBot RBY1 5꾸러미와 Franka 3꾸러미(15편), RoboTwin 20과제 × 3편(원격 zip 범위 읽기)이다. 수율은 모두 **[추정]**이다. 실제 수는 변환 뒤 '로더가 붙인 행 수'(P115)로 보고한다.

### 4.0 요약표

| 원천 | 라이선스·게이트 | 신뢰도 | P | C′ | 위에서 잡기(≤ 30°) | 예상 수율 [추정] |
|---|---|---|---|---|---|---|
| S3 BEHAVIOR-1K 2025 (R1Pro) | MIT, 없음, 2.07 TB | NeurIPS 2025 챌린지, 1,723★, 좋아요 38 | ●(깊이 + 분할 + 과제 물체 GT) | ◐(바퀴 이동 구간 제외, G9 83 %) | 29 %(55회, 중앙 50°; 캔 2–16°, 접시 43–69°) | P: 1만 편 × 약 30프레임 = 약 30만; C′: 약 8만 사이클 × 29 % ≈ 2.3만 사이클 × 구간 6 × 2 ≈ 28만 |
| S4 MolmoBot **Franka** PnP | ODC-BY, 없음(3.47 TB) | 학회 미확인, molmospaces 479★ | ●(점 GT, 물체 시작 자세) | **●(계획기 단계 10종이 우리 6단계에 거의 1 : 1)** | **93 %**(15회, 중앙 5°) | 꾸러미 92,543 × 약 5편 ≈ 46만 편 → C′ 수십만(상한), P 수백만 |
| S4 MolmoBot **RBY1** PnP | 같음(148 GB) | 같음 | ●(시제품 G1 90 %, G6 2.2 px) | ◐ | **엇갈림**: 이 에이전트 15편 20 %, 보조 에이전트 5회 80 %(아래 4.1) | 9,905편 × P 약 58 = 약 57만; C′ 약 11/편(필터 전) |
| S5 RoboTwin 2.0 (5기체) | MIT, 없음, 2.55 TB | ICML 2026, 2,914★, 좋아요 68 | ◐(EE 투영만; 깊이·물체 자세 없음 — 재생하면 가능) | ●(월드 → 기체 기저: `config.yml robot_pose`) | **72.7 %**(20과제 99회, 중앙 1.5°; 병·솥 손잡이 과제는 79–90°) | 집어 놓기 약 30과제 × 5기체 × 550편 ≈ 8만 편 × 73 % |
| MolmoAct 공개 혼합 | CC BY 4.0 | ICRA 2026, 389★ | ◐(그리퍼 점·궤적 픽셀만) | ✕(보정 없음) | — | 궤적 프레임 약 1,000만(1절) |
| S7 Robo2VLM-1 | Apache-2.0 | NeurIPS 2025 D&B spotlight | 객관식만(좌표·보정 메타 없음) | ✕ | — | 68.5만 문항 |
| S9 RefSpatial | Apache-2.0 | NeurIPS 2025, 267★ | 2D 점만(깊이 PNG는 8비트 영상별 min–max 상대값, 내부값 없음) | ✕ | — | 250만 표본 |
| DROID **[기초]**(2024-03, RSS 2024) | CC BY 4.0(`lerobot/droid_1.0.1` 카드는 apache-2.0 표기, 원 라이선스 따름) | RSS 2024 | ◐(보정 품질 필터 뒤; 물체 GT 없음) | ◐(실물 Franka, 기저 절대 목표 있음) | 미측정(측정법 4.6) | 95,658편·2,763만 프레임; 개선 보정 약 3.6만 편 |

### 4.1 S4 MolmoBot-data (`allenai/molmobot-data`)

- **꾸러미**: tar.zst, `<config>/{train,val}_pkgs-*.parquet`(path·shard_id·offset·size), `…_shards/NNNNN.tar`. 제공 도구 `stream_access_example.py`로 범위 요청해 받는다. 꾸러미 안에 h5 1개(`traj_k`)와 편마다 mp4(머리·손목 l·r·손목 깊이)가 있다.
- **필드**(h5 `traj_k/`, JSON은 uint8 2,000바이트):
  - `actions/ee_pose`(JSON): 부위별 **기저 기준 명령 절대 목표** [x, y, z, qw, qx, qy, qz]. 키는 RBY1 `left_gripper`/`right_gripper`, Franka `arm`/`gripper`. 끝 스텝은 빈 JSON일 수 있어 앞 값을 이어 쓴다.
  - `obs/extra/tcp_pose`: 첫 이동 그룹(RBY1은 **왼팔**) — 오른팔 과제에 쓰면 틀린다.
  - `obs/extra/robot_base_pose`: 월드 wxyz.
  - `obs/extra/obj_start`: 집을 물체의 월드 자세(wxyz); `obj_end`는 0.
  - `obs/sensor_param/<cam>/{intrinsic_cv, extrinsic_cv, cam2world_gl}`.
    - extrinsic_cv = 월드 → 카메라(CV).
    - cam2world_gl = 그 단순 역행렬(이름과 달리 CV 축).
    - **intrinsic_cv는 480² 기준, 영상은 1024×576** → `rescale_K_vertical_fov`(세로 화각 유지) 필수.
  - `obs/extra/object_image_points/{left_gripper, right_gripper, pickup_obj, place_receptacle}/<cam>/points` (T, 10, 2): **0–1 정규화**. GT 분할 마스크를 2회 침식한 뒤(그리퍼·손잡이는 침식 생략) 무작위로 10점을 뽑는다. 안 보이면 NaN.
  - `obs/agent/qpos`(JSON): RBY1 손가락 ±0.05(열림) … 0(닫힘).
  - `actions/joint_pos`의 그리퍼는 관절값이 아니다. RBY1에서는 0·0.05·100이 섞이고, Franka 명령은 0 = 열림, 255 = 닫힘이다.
  - `obs/extra/grasp_state_*`: `held` = 물체가 그리퍼 외에는 닿지 않음. 성공 편에서도 0 → 쓰지 않는다.
  - `obs/extra/policy_phase` + `obs_scene.policy_phases`:
    - RBY1: pregrasp 0, grasp 1, lift 2, place 3, postplace 4, done 5.
    - Franka: unknown 0, gripper-open 1, pregrasp 2, grasp 3, gripper-close 4, lift 5, preplace 6, place 7, retreat 8, go_home 9.
  - `obs/extra/policy_num_retries`, `fail`, `success`.
  - `obs_scene`: 과제 문장, 지칭 표현 확률, `frozen_config`(pickle base64 — 풀지 말고 `pickletools.dis`로 읽는다: 카메라 fov 138.5°·해상도·물체 자산).
  - 손목 깊이 mp4: `libx264rgb`·gbrp, `d = 0.05 + ((R·256 + G) − 1)/65534 × 0.50` m, 0 = 무효, **0.05–0.55 m만 유효**. 머리 깊이는 없다.
- **좌표**: 투영식은 `K' · extrinsic_cv · (T_world_base(robot_base_pose) · T_base_ee)`, 모두 wxyz다. 시제품 G6 중앙 2.2 px, G1(c) 90 %였다.
- **물체 위치**: 3D는 `obj_start`(잡기 전 프레임만), 2D는 `pickup_obj`·`place_receptacle` 점의 평균이다. 크기는 데이터에 없어 `frozen_config`의 자산 → molmospaces MJCF 상자로 구해야 한다(다음 단계).
- **사건 분할**:
  - RBY1: 측정 열림 비율(|qpos|/0.05)에 이력 문턱 0.8/0.95를 쓴다. 쥠은 닫힌 구간 최소 열림 > 3 %, 빈 닫힘(재시도)은 0.01까지 닫힌다. 우리 단계 ↔ 계획기 단계 일치 94.2 %.
  - Franka: `policy_phase` 10종을 그대로 대응시킨다.
    - pregrasp → above_target
    - grasp·gripper-close → descend_close
    - lift → carry_up
    - preplace → carry_over
    - place → lower_open
    - retreat → retreat
    - 재시도(`policy_num_retries`)의 빈 닫힘 → reopen
- **접근축**: TCP 로컬 **+z**. 근거는 curobo 비용 `dists_up = R[2,2]`와 시제품 하강 방향 코사인 0.76, 7회.
- **위에서 잡기**:
  - Franka 15회: 93 %가 ≤ 30°. 생성기의 수직 비용 가중이 Franka 2.0, RBY1 0.5다.
  - RBY1: 이 에이전트 15편 중 3편(20 %; 각도 1–96°, 중앙 약 65°) 대 보조 에이전트 5회 80 %로 **엇갈린다**. 원인 후보는 (a) 명령 자세 대 실제 자세(시제품은 명령 `actions/ee_pose`), (b) 표본 꾸러미 차이, (c) 팔(왼·오른) 대응이다. → 35B 전에 RBY1 꾸러미 50개로 다시 잰다. **C′ 주원천은 Franka로 정한다.**
- **자기 정보 원천**:
  - molmospaces `get_robot_path("rby1m")` MJCF, `curobo_config/rby1m_*_arm_holobase.yml`.
  - `molmo_spaces/configs/camera_configs.py` `RBY1GoProD455CameraSystem`: head 세로 화각 139° ± 3, 손목 58°.
  - Franka는 panda MJCF.
- **수율**: 위 요약표. 상업 필터: `commercial_episodes.parquet`로 NC 물체가 든 편을 뺀다.

### 4.2 S3 BEHAVIOR-1K 2025 (`behavior-1k/2025-challenge-demos`)

- **형식**: LeRobot v2.1, 1만 편, 1.19억 프레임, 30 fps, 50과제.
- **parquet 필드**:
  - `observation.state`(256): v3.7.2 `learning/utils/eval_utils.py` 배치.
    - robot_pos 140:143(월드), robot_ori_cos 143:146, robot_ori_sin 146:149, robot_2d_ori 149.
    - eef_left_pos 186:189, eef_left_quat 189:193, gripper_left_qpos 193:195.
    - eef_right_pos 225:228, eef_right_quat 228:232, gripper_right_qpos 232:234.
    - base_qpos 244:247.
  - `observation.cam_rel_poses`(21): 왼손목·오른손목·머리 × [pos, quat xyzw], 기체 루트 기준 카메라 자세, GL 축.
  - `observation.task_info`(가변): 편 메타 `task_obs_keys` 순서로 물체마다 real 1 · pos 3(**월드**) · ori_cos 3 · ori_sin 3 · (움직이는 물체) in_gripper_left·right. `in_gripper_*`는 늘 −1이라 쓰지 않는다.
  - `action`(23): base 0:3, torso 3:7, left_arm 7:14, left_gripper 14, right_arm 15:22, right_gripper 22(+1 열림 / −1 닫힘).
- **영상**(HEVC): `observation.images.{rgb, depth, seg_instance_id}.{head 720², left_wrist 480², right_wrist 480²}`.
  - 깊이 해독: 6.2 함정 7.
  - 분할: 편 메타 `<cam>::unique_ins_ids` 순서로 팔레트를 만들고(`generate_yuv_palette`) 최근접 색으로 id를 얻는다. `ins_id_mapping` id → prim 경로이고, 경로 4번째 조각이 물체 이름이다(0 배경, 1 미표지). 로봇 링크는 `controllable__r1pro__robot_r1/<link>`다.
  - bddl 이름 → 장면 이름은 `config.scene.scene_file.metadata.task.inst_to_name`에 있다.
- **주석**: `annotations/…json` `skill_annotation[]`에 skill_description, object_id, manipulating_object_id, frame_duration [s, e], skill_type, spatial_prefix가 있다. `primitive_annotation[]`도 있다. 놓을 면은 `place on/in` 스킬의 `object_id[1]`이다.
- **좌표**:
  - 쿼터니언은 xyzw다.
  - eef는 기체 루트 기준, 내부값은 코드 상수(head fx = fy = 306, c = 360; 손목 388.66, c = 240)다.
  - 카메라(CV) → 기저는 `pose(cam_rel) · diag(1, −1, −1)`이다.
  - 물체: 월드 → 기저는 (robot_pos, yaw = robot_2d_ori) 역변환이다.
  - 시제품 G1(a) 37/37, G3 93.5 %.
- **물체 위치**:
  - 과제 물체는 `task_info` GT를 쓴다(3D 답은 이것만).
  - 그 밖의 물체는 분할 ∩ 깊이로 구하되, 겉면 편향이 약 8.6 cm(6.1)라 자산 상자 보정 전에는 **2D 점만** 낸다.
  - 크기: 분할 ∩ 깊이 범위는 보이는 부분뿐이다 → 자산 메타 상자가 필요하다.
  - 탁자 평면: 받침 물체 마스크 ∩ 깊이 RANSAC, 시제품 61/61.
- **사건 분할**: `action[22]` 부호가 바뀌는 순간이 닫힘·열림이다. 쥠은 손가락 qpos 합 > 0.004(열림 0.1)로 보고, 표본 닫힘 55회 중 53회가 쥠이었다.
- **접근축**: eef 로컬 **+z**(시제품: +z가 아래와 11–12°, 다른 축은 78–102°).
- **위에서 잡기**: 29 %(55회). 사람 원격조작이라 옆 잡기가 많다.
- **자기 정보 원천**: `behavior-1k/omnigibson-robot-assets`(MIT) `models/r1pro/urdf/r1pro.urdf` + `r1pro.yaml`. 손가락은 직동 0–0.05 m × 2, 카메라는 `zed_link`(head)·`{arm}_realsense_link`, `eef_link_names = {arm}_eef_link`.
- **C′ 제약**: 바퀴 이동 중인 구간은 기저가 움직여 '기저 절대 목표'의 뜻이 흐려진다 → G9(시제품 10/12 통과).

### 4.3 S5 RoboTwin 2.0 (`TianxingChen/RoboTwin2.0`)

- **꾸러미**: `dataset/<과제>/<기체>_{clean_50, randomized_500}.zip`(원격 zip 범위 읽기로 편 단위 추출 가능). 안에 `data/episodeN.hdf5`, `instructions/episodeN.json`(seen·unseen 표현 수십 개), `_traj_data/episodeN.pkl`(관절 경로), `seed.txt`, `scene_info.json`(방해물·질감·`{A}` 물체 id)가 있다.
- **h5 필드**:
  - `endpose/{left,right}_endpose`: [x, y, z, qw, qx, qy, qz], **월드**, 끝 링크.
  - `endpose/*_gripper`: 0–1, 1 = 열림.
  - `joint_action/*`.
  - `observation/{head, front, left, right}_camera/{rgb(JPEG), intrinsic_cv, extrinsic_cv(월드 → 카메라 CV), cam2world_gl(GL)}`.
  - `pointcloud`는 비어 있다.
- **좌표**:
  - TCP = pos + 0.12 · R[:, 0](로컬 +x = 접근축, 전 기체 공통; 코드 gripper_bias − 0.12, 시제품 눈 9/9).
  - 기체 기저 = `embodiments/<e>/config.yml` `robot_pose`. aloha-agilex는 [0, −0.65, 0, 0.707, 0, 0, 0.707]로, 월드 원점 (0, −0.65)에서 +y를 본다.
  - 시제품은 원점을 월드에 두고 축만 돌렸다. **다음 판은 `robot_pose` 역변환으로 바꾼다.**
  - aloha는 양팔이 한 엔티티라 팔별 마운트 오프셋을 URDF(`arx5_description_isaac.urdf`)에서 더한다.
- **물체 위치**: 저장돼 있지 않다.
  - `seed.txt` + `_traj_data`로 재생하며 깊이·분할·actor 자세를 기록한다. 수집기가 `data_type` 깊이·분할을 지원한다. SAPIEN이 필요하고 CPU 렌더도 가능하지만 느리다 [확인 필요].
  - 대안: 닫힘 순간 TCP를 물체 위치 근사로 쓴다(P에는 쓰지 않는다).
- **사건 분할**: 그리퍼 값이 0.5를 아래로 지나면 닫힘이다. 시제품은 이력 문턱 0.3/0.45를 썼다(0.5 = 계획기의 반쯤 연 예비 자세).
- **위에서 잡기**: 72.7 %(20과제 99회, 중앙 1.5°), 두 봉우리 분포다. 옆 잡기 과제(`lift_pot`·`pick_dual_bottles`·`put_bottles_dustbin`)는 과제 단위로 뺀다.
- **자기 정보 원천**: `embodiments.zip`(220 MB, 범위 읽기) `<e>/config.yml`의 gripper_bias·gripper_scale·robot_pose·static_camera_list와 URDF(aloha `arx5_description_isaac.urdf`, franka `panda.urdf`). extrinsic은 매 프레임 있다.

### 4.4 MolmoAct 데이터 — 1절

- 원본 `MolmoAct-Dataset` tabletop: 1,966편, 316,670프레임, 10 fps, 14과제, 480×640.
- `state` = EE xyz + rpy + 그리퍼, `actions` = 델타 EE.
- **카메라 보정이 없어 3D·C′에 쓸 수 없다.**

### 4.5 S7 Robo2VLM-1 · S9 RefSpatial (형식 변환만)

- **Robo2VLM**:
  - 필드: `id`, `question`, `choices`(문자열 목록), `correct_answer`(int), `image`.
  - 답 형식: `{"choice": k}`.
  - 머리 줄: `source: robo2vlm/<원 데이터>`, `frame: none`.
  - 우리 런타임 지시문과 다른 지시문을 쓴다(형식 오염 방지, `cross_embodiment` 4절).
- **RefSpatial**:
  - `2D/`·`3D/`·`Simulator/` JSON(choice_qa·reasoning_template_qa·vacant_qa·multi_view_qa·visual_choice_qa, metadata.json)과 image·depth tar.gz.
  - 점은 `[(x, y)]` 0–1을 우리 `{"point": [u, v]}` 픽셀로 바꾼다.
  - 깊이 PNG는 8비트 상대값이라 **3D QA를 만들지 않는다.**

### 4.6 DROID [기초] — C′ 실물 원천 후보

- **신뢰도**: 2024-03, RSS 2024, CC BY 4.0. 1.5년 밖이라 기초로 표시한다.
- **개선 보정**: 2025-04 `KarlP/droid`.
  - `cam2base_extrinsics.json`(약 3.6만 편), `cam2base_extrinsic_superset.json`(약 2.4만 고유 / 4.8만 자세), `cam2cam_extrinsics.json`(약 9만).
  - 형식 6-D [t, `R.from_euler("xyz")`], 카메라 → 목표.
  - `intrinsics.json`(시리얼별 [fx, cx, fy, cy], 원해상도 — 320×180이면 1/4), `keep_ranges_1_0_1.json`, `episode_id_to_path.json`.
- **필드** (`lerobot/droid_1.0.1`):
  - `observation.state.cartesian_position`(xyz + euler xyz, 기저).
  - `gripper_position` 0 열림 … 1 닫힘.
  - `action.cartesian_position`(절대 목표).
  - `camera_extrinsics.{wrist_left, exterior_1_left, exterior_2_left}`(원 보정, 잡음 큼).
  - 영상 180×320 av1.
- **조리법**:
  1. 개선 보정이 있는 약 3.6만 편만 쓴다.
  2. G1(투영 EE가 그리퍼 위)을 **분할 모델 없이** 판정할 방법이 없으므로, HAMSTER처럼 '투영 깊이 ↔ 스테레오 깊이 정렬' 필터를 둔다.
  3. 접근축 +z로 닫힘 순간 `arccos(−R[2,2])`를 잰다 — **위에서 잡기 비율은 미측정**.
  4. 물체 GT가 없어 P-3D는 없다(분할 모델 + 스테레오 깊이 필요, 라벨 잡음).
- **판정**: 실물 C′의 유일한 대규모 후보지만 보정 잡음·물체 GT 없음 때문에 **시뮬 C′ 뒤 2순위**다.

### 4.7 목록만 (게이트·NC — 사용자 동의 전 받지 않음)

- **게이트 + CC BY-NC-SA**:
  - InternData-A1·M1: M1에 `tcp_2d_trace`·`bbox3d`·`pick/place_obj_uid`가 있어 필드가 가장 딱 맞다.
  - AgiBot World / Digital World: Digital World는 1.5년 밖.
  - RoboInter-Data·VQA, Galaxea Open-World.
- **동의가 필요한 것**: HF에서 사용자가 약관에 동의해야 한다(에이전트는 동의하지 않는다). NC는 Astra 전송을 보류한다.
- **RoboCasa365**(NVIDIA CC BY 4.0 / ember MIT, ICLR 2026, 게이트 없음):
  - `eef_pos_rel`·`eef_quat_rel`(기체 기준, robosuite xyzw)과 `states.npz` + `model.xml.gz` 재생으로 물체 자세·깊이·MJCF 카메라를 복원할 수 있다.
  - Panda 이동형이다. 재생 비용 때문에 2순위.
- **Open-X의 다른 부분 집합**(Bridge·Fractal 등): 카메라 외부값이 없다. MolmoAct 공개 궤적으로만 쓴다.

## 5. 품질 관문과 검증

모든 관문은 `tools/xemb/gates.py`에 있고, 원천별 변환기가 `gates.json`에 수치를 쓴다. **관문을 못 넘은 표본은 버린다**(필터). 원천 전체가 관문을 못 넘으면 그 원천을 쓰지 않는다.

| 관문 | 정의 | 문턱 | 원천 |
|---|---|---|---|
| G1 EE 투영점이 그리퍼 위 | EE(또는 TCP) 3D → 보정 투영 → 픽셀 u, v가 (a) 그리퍼 분할 마스크의 4 px 안(`on_mask`), 또는 (b) 데이터셋 GT 그리퍼 점 10개의 상자 + 10 px 안(`on_points`), 또는 (c) 가장 가까운 GT 점에서 0.5 × 상자 대각선 안(`near_points`, 손끝 너머 TCP 허용) | 원천별 ≥ 95 %(보이는 프레임 기준). (c)를 통과 못 한 프레임의 표본은 버림 | BEHAVIOR (a), MolmoBot (b)(c) + 눈, RoboTwin 눈 |
| G2 3D 중심 오차 | 분할 ∩ 깊이 역투영 중심 − GT 물체 중심(카메라 좌표) | 중앙 ≤ 2 cm. **넘으면 3D 답은 GT에서만** 만들고, 분할 ∩ 깊이 추정은 쓰지 않음 | BEHAVIOR(`task_info` GT) |
| G3 GT 중심이 마스크 안 | GT 중심 투영이 그 물체 마스크 3 px 안 | ≥ 90 % | BEHAVIOR |
| G4 분할 건전성 | 마스크 ≥ 150 px, 유효 깊이 ≥ 80 %, 5–95 % 점 퍼짐 ≤ 0.5 m(탁자 1.5 m) | 불통 표본 버림 | BEHAVIOR |
| G5 평면 | 탁자 마스크 ∩ 깊이 RANSAC(1 cm) 인라이어 ≥ 50 %, 법선이 기저 z와 이루는 각 ≤ 3° | 불통 표본 버림 | BEHAVIOR |
| G6 보정 자기 검사 | 물체 시작 자세 투영 ↔ 데이터셋 물체 점 중심의 픽셀 거리(물체가 움직이기 전 프레임) | 중앙 ≤ 5 px | MolmoBot |
| G7 단계 분할 일치 | 우리 `steps.segment` 단계 ↔ 데이터셋 계획기 단계 표시(있을 때) 프레임 일치율 | ≥ 90 % | MolmoBot `policy_phase` |
| G8 위에서 잡기 | 잡는 순간 접근축이 수직 아래와 이루는 각 | ≤ 30° 편만 C′ | 전 원천 |
| G9 기저 정지 | C′ 구간 시작 ↔ 목표 프레임 사이 기저 이동 < 2 cm·회전 < 2° | 불통 구간 C′ 버림 | 바퀴형(BEHAVIOR·MolmoBot) |
| G10 형식 | C′ 답이 우리 런타임 검사기(`harvest/astra_solo/schema.validate`)를 통과, 답에 `frame`·픽셀 키 없음 | 100 % | 전 원천(`test_xemb_fmt.py`) |

### 5.1 좌표 누수(frame-leak) 시험 설계 — 학습한 모델에 대해 (E-XEMB8에 붙임, 실행 안 함)

- **질문**: 공개 C′·P를 섞어 학습하면, 우리 요청(출처·좌표계 줄이 없는 런타임 그대로)에 대한 답에 남의 좌표계나 형식이 새는가?
- **입력**: DEV 스냅숏 약 350(L8 4.4절과 같음). 우리 요청은 `source`·`frame` 줄 없이 **런타임 그대로** 넣는다.
- **자동 판정**: `fmt.leak_flags(answer, our_box)`.
  - `foreign_key:*`: 답에 `frame`·`point`·`xyz_cam`·`source` 같은 공개 형식 키가 있다.
  - `outside_box`: eef 목표가 우리 작업 상자(여유 5 cm) 밖이다.
  - `not_json`: 답이 JSON이 아니다.
- **추가 두 가지**:
  - (i) **꼬리표 바꿔치기**: 공개 C′ 검증 표본의 `frame: base_rby1`을 `base_ffw_sg2`로 바꿔 넣는다. 답의 목표가 RB-Y1 작업 상자 → 우리 상자 쪽으로 옮겨 가면 모델이 꼬리표를 읽는다는 뜻이다(좋은 쪽). 안 움직이면 꼬리표를 무시한다는 뜻이다.
  - (ii) **로봇 바꿔치기 역검사**: 우리 요청의 영상을 그대로 두고 자기 정보 블록만 RB-Y1 것으로 바꾼다. 답이 RB-Y1 상자로 옮겨 가는 비율을 잰다.
- **판정 초안**:
  - 누수율(`foreign_key` 또는 `outside_box`)은 **0 / 350이어야 한다.** 1건이라도 있으면 그 팔은 '누수'로 보고, 형식 분리(지시문·답 틀을 더 다르게)를 먼저 고친다.
  - (i)·(ii)는 보고만 한다(판정 없음).
- **L8 기준선**: A팔(자체만)에도 같은 검사를 돌려 0임을 확인한다(검사기 자체의 오탐 확인).

## 6. 시제품 결과 (무료, CPU만, 파드 표본)

- **실행**: 2026-09-27 00:0x–01:3x KST, 파드 `juhyoung-native-7a2a`. 환경은 `venv_e3st`(cv2·av·pyarrow)와 조사 때 설치한 `pylib`(h5py·zstandard)이다. GPU 0, 유료 0.
- **새로 받은 것**: BEHAVIOR 편 10·20의 머리 깊이·분할 영상, 편 20의 parquet·메타·주석뿐이다(합 약 26 MB, 기존 `pod_get.sh` 사용, 토큰은 파일에서만 읽음).
- **코드**: `tools/xemb/`에 geom·steps·fmt·gates·sheet·src_molmobot·src_behavior·src_robotwin·run_proto가 있다.
  - 순수 부분은 시험을 먼저 썼다. `tests/test_xemb_{geom,steps,fmt,behavior}.py` 31개가 통과했다(로컬).
  - 파드 사본은 `/data/harvest/out/xemb_proto/code/xemb/`에 있다.
- **실행 방법**: `PYTHONPATH=<code>:<pylib> venv_e3st/bin/python -m xemb.run_proto {molmobot|behavior|robotwin} <원천> <출력>`.
- **산출**: 파드 `/data/harvest/out/xemb_proto/{molmobot,behavior,robotwin}/` 아래에 `records_P.jsonl`·`records_C.jsonl`·`gates.json`·`frames/`·`sheets/`가 있다.

### 6.1 관문 수치

| 원천(편) | G1 EE가 그리퍼 위 | 3D·보정 | 단계·C′ | 표본 |
|---|---|---|---|---|
| **MolmoBot RBY1 val 샤드**(15편, 12꾸러미) | (b) 상자 + 10 px 176/205 = **85.9 %**; (c) 0.5 대각선 185/205 = **90.2 %**; **눈 확인**: 무작위 타일 10/10 그리퍼 위, (b) 불통 타일 12개 중 11개는 손끝 바로 너머(데이터셋 TCP 정의), 1개만 어긋남(명령이 실제보다 앞섬) → 추정 ≥ 97 % | G6 물체 시작 자세 투영 ↔ 물체 점 중심 중앙 **2.2 px**(p90 6.8, n 95) | G7 단계 ↔ `policy_phase` **94.2 %**(1,907/2,024프레임). 15/15편 전 단계 순서 복원(2편은 빈 닫힘 → `reopen` 복구 포함). **G8 위에서 잡기 ≤ 30°: 3/15 = 20 %**(≤ 20°: 1/15) | P 877, C′ 42(필터 전 205) |
| **BEHAVIOR 2025 task-0000**(2편, 라디오 켜기) | (a) 오른 그리퍼 분할 마스크 4 px 안 **37/37 = 100 %** | G3 GT 중심이 마스크 안 **58/62 = 93.5 %**; **G2 3D 중심(분할 ∩ 깊이 − GT) 중앙 9.1 cm — 불통**. 광선에 수직 성분은 2.5 cm, 광선 방향은 **−8.6 cm**(보이는 겉면이 GT 원점보다 카메라 쪽); G5 탁자 평면 61/61 통과(법선 기울기 중앙 0.44°, 탁자 윗면 기저 z 0.407 ± 0.005 m); G4 퍼짐 불통 21 | G8: 두 편 모두 R1Pro 말단 +z가 아래와 **11–12°**(위에서 잡음); G9 기저 정지 10/12 구간 | P 222 |
| **RoboTwin 2.0 lift_pot**(1편 × 2팔) | 눈: 첫 장 9/9가 손가락 사이(끝 링크 + 12 cm 접근축) | 깊이 없음 → 3D 없음 | 접근축 = 끝 링크 +x(wxyz), 코사인 0.99–1.00; **G8: 59–61°(손잡이 옆 잡기) — C′ 필터면 0** | P 46, C′ 12(필터 전; 들기 과제라 놓기 단계 없음) |

- **겹쳐 그림 판**(파드):
  - MolmoBot: `/data/harvest/out/xemb_proto/molmobot/sheets/sheet_0{0,1,2}.jpg`, 불통 모음 `fail_0{0,1}.jpg`.
  - BEHAVIOR: `/data/harvest/out/xemb_proto/behavior/sheets/sheet_0{0,1,2}.jpg`.
  - RoboTwin: `/data/harvest/out/xemb_proto/robotwin/sheets/sheet_0{0,1,2}.jpg`.
  - 표시: 빨강 고리 = 투영 EE/TCP, 주황 선 = 접근축 8 cm, 파랑 점 = GT 그리퍼 점, 초록 = 물체 점, 청록 + = GT 중심 투영, 노랑 = 놓을 곳, 자홍 X = C′ 목표.
  - MolmoBot은 그리퍼가 작아 EE 주변 240 px를 잘라 보였다.
- **BEHAVIOR G2 해석**: 분할·보정은 맞다. GT 중심은 마스크 안에 93.5 % 떨어지고, 광선에 수직 오차는 2.5 cm다. 오차의 대부분은 **'보이는 겉면의 중심'과 '물체 원점'의 차이**다(라디오 두께의 약 절반).
  - 그래서 3D 중심 답은 **GT(task_info)에서만** 만든다(시제품 `obj_center_cam` 62개가 GT값).
  - 분할 ∩ 깊이 추정은 GT가 없는 물체에 쓰려면 물체 상자(자산 메타)의 광선 방향 반두께 보정이 필요하다. 그 전에는 쓰지 않는다.
  - 깊이 해독은 탁자 평면(기울기 0.44°, 높이 흔들림 ± 5 mm)으로 간접 확인했다.

### 6.2 시제품에서 찾은 함정 (각 원천)

1. **MolmoBot `actions/ee_pose`는 명령이다.** 첫 프레임과 막힌 구간에서 실제 그리퍼보다 앞선다(눈 확인). 투영에는 1스텝 늦춘 값을 썼다.
   - 늦춤 0/1/2/3에서 G1(b)는 81.8/85.9/83.9/79.5 %였다.
   - G1(c)를 통과하지 못한 프레임의 P는 버린다.
2. **MolmoBot `obs/extra/tcp_pose`는 이 샤드에서 왼 그리퍼다.** 오른팔이 일할 때 z가 1.36 m로 고정돼 있었다. `actions/ee_pose`의 `<arm>_gripper`를 쓴다.
3. **MolmoBot `intrinsic_cv`는 480² 기준인데 영상은 1024×576이다.** 세로 화각이 같다고 보고 fy' = fy × 576/480, fx' = fy', 주점 (512, 288)으로 고치면 그리퍼 점과 5.4 px로 맞는다. 저장된 K를 그대로 쓰면 32.8 px 어긋난다.
   - 조사 에이전트가 읽은 MolmoSpaces 코드는 "설정 img_resolution에서 계산"이라 했지만, 이 샤드 값은 그렇지 않았다. **샤드마다 K 해상도를 확인**한다.
4. **MolmoBot `actions/joint_pos`의 그리퍼 값은 관절값이 아니다**(0·0.05·100이 섞임). 열림은 **측정 qpos**(−0.05 열림 … 0 닫힘)로 판정한다.
5. **MolmoBot `grasp_state_*.held`는 이 샤드에서 늘 거짓이다.** '쥠'은 닫힌 구간의 최소 열림 > 3 %로 판정한다.
   - 12 %로 두면 얇은 물체 3/15편이 빈 닫힘으로 잘못 잡혔다.
   - 빈 재시도는 0.01까지 닫혔다.
6. **팔 고르기**: '그리퍼가 가장 많이 닫힌 팔'로 고르면, 놀고 있는 팔이 처음부터 닫힌 편(house_7645)에서 틀린다. **명령 EE 이동 거리가 긴 팔**로 고른다.
7. **BEHAVIOR 깊이 영상은 yuv420p10le**다(info.json은 yuv420p16le라고 적음). gray16le로 풀면 14비트 로그 양자화 값 q이고, 10비트 저장이라 q는 64단위로 끊긴다(1 m에서 약 2.4 cm 단위).
   - v3.7.2 `dequantize_depth`(MIN 0, MAX 10, SHIFT 3.5, qmax 16383)를 쓴다. 현재 main 코드는 12비트, MIN 0.01이라 **판이 다르다.**
8. **BEHAVIOR `in_gripper_*`는 이 편들에서 늘 −1이다.** 쥠은 행동 22번(오른 그리퍼 +1 열림 / −1 닫힘)과 손가락 qpos 합(0.10 열림, 0.037 쥠)으로 정한다.
9. **BEHAVIOR 분할 영상**은 압축 탓에 색이 1.2만 가지로 번진다. 팔레트 최근접 색으로 풀고, 마스크를 5 px 침식해 가장자리 번짐을 뺀다. 퍼짐 불통이 21건 나왔다.
10. **RoboTwin `endpose`는 끝 링크(손목)다.** 손끝 중심은 접근축(+x, wxyz) 12 cm 앞이다. RoboTwin 코드의 gripper_bias − 0.12와 맞는다.

## 7. C′를 막는 것, 권고 순서

### 7.1 C′를 막는 것

1. **잡는 자세.** 우리 그리퍼는 아래를 향하고 손목 회전 명령이 없다. 그래서 C′에는 위에서 잡는 편(≤ 30°)만 쓴다. 원천별로 남는 몫은 다음과 같다.

   | 원천 | ≤ 30° 몫 | 비고 |
   |---|---|---|
   | MolmoBot Franka | 93 % | |
   | RoboTwin | 73 % | 옆으로 잡는 과제는 과제 단위로 뺀다 |
   | BEHAVIOR | 29 % | |
   | MolmoBot RBY1 | 20 % 또는 80 % | 측정이 엇갈려 다시 잰다 |

   → **C′ 주원천은 MolmoBot Franka, 그다음 RoboTwin**이다.

2. **기저의 뜻.**
   - 바퀴형(BEHAVIOR·RBY1)은 구간 중에 기저가 움직인다. 기저가 움직인 구간은 G9로 뺀다. 시제품에서는 12구간 중 2구간이 빠졌다.
   - RoboTwin은 월드 → `robot_pose` 역변환과 팔 마운트 오프셋이 필요하다. 시제품은 원점을 월드에 둔 판이라 **아직 기저 좌표가 아니다**.
3. **'명령' 대 '실제'.** MolmoBot `actions/ee_pose`는 명령이라 실제 자세보다 앞설 수 있다(6.2의 1).
   - 라벨(다음 목표)로는 오히려 맞는 값이다.
   - 상태(NOW의 TCP)는 1스텝 늦춘 값이 근사다.
   - FK 측정값(qpos + MJCF)으로 바꾸는 것이 정답이다. 다음 단계다.
4. **보정 품질(실물).** DROID는 개선 보정본이 필요하고 물체 GT가 없다. 실물 C′는 2순위다.
5. **깊이.** 공개 깊이는 제각각이다.

   | 원천 | 깊이 |
   |---|---|
   | BEHAVIOR | m, 14비트 로그 |
   | MolmoBot | 손목만 0.05–0.55 m |
   | RoboTwin | 없음 |
   | MolmoAct·RefSpatial | 상대값 |

   우리 §97의 깊이 입력과 같은 뜻인 원천은 BEHAVIOR뿐이다. 깊이를 입력으로 넣는 설계(§97)에서 공개 C′ 대부분은 **깊이 없는 요청**이 된다. 이 차이는 요청 글에 적는다(`depth: none`).
6. **좌표 누수 위험.** C′ 답의 수치는 남의 기저 좌표이고, 한 원천 안에서도 높이대가 다르다. 예를 들어 RB-Y1 z는 0.83–1.36 m이고 우리 탁자는 0.85다. 5.1의 누수 시험이 0이어야 섞는다.

### 7.2 권고 순서 (무료, 모두 CPU 또는 기존 x2 렌더 GPU)

1. **MolmoBot Franka PnP 꾸러미 50개**를 범위 요청으로 받는다(약 2 GB). `src_molmobot`에 Franka 분기를 넣는다(`policy_phase` 10종 대응, `arm`/`gripper` 키, 명령 0/255). 같은 김에 RBY1 위에서 잡기 비율을 꾸러미 50개로 다시 잰다.
2. **RoboTwin 기저 변환 고치기**(`robot_pose` 역변환 + 팔 마운트)와 **집어 놓기 과제 5개 × clean_50 편 몇 개**(원격 zip 범위 읽기).
3. **BEHAVIOR**: 과제 물체만 GT 3D를 쓰고, 나머지는 2D 점만 쓴다. 50과제 × 편 2로 다양성 표본을 만든다(편당 깊이·분할·RGB 약 20 MB).
4. **MolmoAct 공개 궤적**: 그리퍼 점·궤적 P를 형식 변환하고 튐 필터를 단다(재생성 없음).
5. 각 원천은 G1–G10 관문과 눈 확인(판 1장)을 거친다.
6. 그 뒤 E-XEMB8(`diversity_plan` 4절 개정)에 원천별 표본 수를 등록한다.

**유료 0원.** 새 게이트 동의가 필요한 것은 4.7 목록뿐이다(사용자 결정).



## 8. 사전 등록 초안 (실행 안 함)

- `docs/stage3/prereg_xemb8.md`: 공개 인식 QA(B)·공개 C′(D)·둘 다(E)를 L8 행 일부와 바꿔 넣는다. E-PT와 같은 DEV·OOD-H·채점기·판정 규칙을 쓰고, 좌표 누수 0을 관문으로 둔다. E-PT에서 ND가 이기면 ND 인터페이스로 만든다.
- `docs/stage3/prereg_open8.md`: 오픈소스만 쓴 O-A(전이), L8 + 공개인 O-B(일반화). 세트는 12절이다.

## 9. 추가 실행 (2026-09-27, 무료 CPU + 빈 GPU 1장) — 다운로드 합 약 17 GB (상한 300 GB, `/data` 여유 32 TB)

| 받은 것 | 크기 |
|---|---|
| MolmoBot Franka PnP 꾸러미 50개(무작위, 시드 0) | 1.75 GB |
| MolmoBot RBY1 PnP 꾸러미 50개 | 0.79 GB |
| BEHAVIOR 2025 50과제 × 첫 2편(parquet·메타·주석·머리 RGB·깊이·분할) | 12.15 GB |
| RoboTwin aloha-agilex randomized_500 집어 놓기 8과제 × 편 3(원격 zip 범위 읽기) | 0.39 GB |
| MolmoAct 사전 학습 혼합 조각 4개(bridge·rt1·bcz·aux_trace 각 1) | 약 2.5 GB |

### 9.1 MolmoBot Franka (C′ 주원천) — `mbfranka/`, 277편(50꾸러미 × 배치·궤적)

- **구조 발견(4.1 보충)**:
  - 꾸러미 하나에 h5 배치가 여러 개 들어 있다(`trajectories_batch_<b>_of_20.h5`). 영상도 같은 배치 꼬리표를 단다. 첫 h5만 읽으면 영상과 짝이 틀린다 → 두 변환기 모두 배치별로 읽게 고쳤다.
  - `object_image_points`는 **JSON 한 칸**으로 된 판과 **그룹**으로 된 판이 섞여 있다.
  - 그리퍼 점이 없다(물체·놓을 곳만) → EE 관문은 눈 확인으로 한다.
  - 카메라는 외부 3–4대(무작위) + 손목이고, 624×352다. K는 480² 기준이라 세로 화각으로 고친다.
- **관문**:
  - G6 물체 시작 자세 투영 ↔ 물체 점: 중앙 5.4 px(p90 21, n 283).
  - G7 단계 ↔ 계획기: **95.4 %**(66,423프레임).
  - 접근축 = TCP +z: 코사인 0.93, n 255.
  - **위에서 잡기 ≤ 30°: 93.7 %**(252회, 중앙 5.0°). ≤ 20°: 91.7 %.
  - G10 C′ 답 깨끗: 3,381/3,381.
  - 눈: 먼 시점은 고리가 손끝에 있다. 가까운 시점(그리퍼가 화면 절반)에서는 손끝보다 한 손가락 길이 앞에 찍힌 판이 15장 중 4장 있었다(측정 TCP `tcp_pose`로 바꿔도 같음 → 데이터셋의 TCP 정의).
  - → EE 점 QA는 카메라에서 TCP까지 ≥ 0.6 m인 프레임만 쓴다.
- **표본**: P 약 6,300, **C′ 3,381**(필터 전 3,671). 단계별로 고르게 나온다(above_target 465 · descend_close 478 · carry_up 477 · carry_over 470 · lower_open 477 · retreat 478 · done 472 · reopen 64).

### 9.2 MolmoBot RBY1 다시 재기 — `molmobot50/`, 50편

- **위에서 잡기 ≤ 30°: 18/45 = 40 %**(≤ 20° 31 %). 앞서 15편 20 %, 보조 측정 5회 80 %로 엇갈렸던 값이 **약 40 %**로 모였다.
- 왼팔 편에서 명령 자세(`actions/ee_pose`)와 측정 자세(`tcp_pose`)의 기울기는 ± 0.3° 안에서 같았다. 엇갈림은 표본 수 탓이다.
- G1 (b) 82.5 %, (c) 89.1 %. G6 3.7 px. 단계 일치 96.4 %.
- P 3,190, C′ 254(필터 전 639).
- 결론: RBY1은 C′ 부원천이다.

### 9.3 RoboTwin 2.0 기저 변환 수정 — `robotwin2/`, 집어 놓기 8과제 × 3편

- 기저 = `embodiments/aloha-agilex.yml robot_pose` [0, −0.65, 0, 0.707, 0, 0, 0.707]. 월드 → 기저는 R^T(p − t)이고, 시험으로 고정했다(`test_xemb_robotwin.py`).
- 양팔이 한 몸(우리 FFW와 같음)이라 **팔별 마운트 오프셋은 넣지 않았다**. 두 팔 목표가 같은 몸 기저에 있는 것이 우리 런타임과 같다.
- 시작 손끝의 기저 x ≥ 0.456 m(로봇 앞)로 부호를 확인했다.
- 잡은 팔 29개 모두 위에서 잡음(중앙 0.6°).
- P 1,178, **C′ 353**. 과제 이름은 `scene_info`의 `{A}`·`{B}`에서 뽑았다.
- 눈: 목표 X가 캔·물체 위에 있다(`robotwin2/sheets`).

### 9.4 BEHAVIOR 50과제 × 2편 — `behavior100/`

- **버그 수정**: `task_info`에서 탁자도 `in_gripper_*` 칸을 가져 '움직이는 물체'로 잘못 분류됐다 → 받침 이름(table·countertop·shelf …)을 먼저 가른다. 앞선 2편 결과(6절)는 라디오만 대상이어서 영향이 없었다.
- 수치는 11절 표에 적는다.

## 10. 좌표계·보정이 없는 오픈소스 데이터 — 구현과 검증 (user-log 123)

사용자 원문(123, 통제자 경유):
- "아니 아까부터 계속 이얘기 했잖아 좌표계 없는거는 어떻게 할건지 오픈소스를 어떻게 할건지 해야한다니까?"
- "좌표계가 없는걸 좌표계를 만들건지 / 그냥 이미지를 엄청 ㅁ낳이 핛브햇거 좌표계를 뭔가 너머에서 알 수 있게 하던지 / 뎁스를 근사화하는 비슷한 방식으로 해서 하던지"
- "근데 저 4개의 방법론은 오픈소스데이터로 일단 해야해 이해했으?"
- "점추적은 T,1,3에 다 들어갈 수 있을 것 같은데 아닌가?"

원칙: **네 방법 모두 오픈소스 데이터에 먼저 적용했다.** 대상은 보정이 없는 ROBOTIS AI Worker RB2 실데이터와 MolmoAct가 공개한 OXE 행(BC-Z·RT-1·Bridge)이다. 보정이 있는 공개 세트(MolmoBot·BEHAVIOR·RoboTwin)는 **보정을 숨긴 채 정답 대조용으로만** 썼다. 우리 시뮬은 쓰지 않았다(평가용으로만 남김).

### 10.1 한 장 요약 — 데이터 조건 → 경로 → 표본

`tools/xemb/routes.py`(`allowed(Cond)`)가 이 표를 코드로 강제한다(`test_xemb_routes.py`).

| 데이터 조건 | 예(오픈소스) | 쓰는 경로·트랙 | 만들 수 있는 표본 | 만들면 안 되는 것 |
|---|---|---|---|---|
| **좌표계 없음**(영상 + 문장만, 또는 궤적 라벨만) | MolmoAct 공개 행(OXE BC-Z·RT-1·Bridge), RefSpatial | ① 픽셀 전용 · ② 그리퍼 검출(포인팅·추적) · **T2** | 그리퍼 점·2D 궤적(`frame: pixel`), 형식 QA, 일반 공간 점 | m 단위 답 전부, 조종(C′) |
| **관절만**(관절 + URDF, 카메라 보정 없음) | **ROBOTIS RB2**(AI Worker, 우리 로봇 계열), RB1·RB3, OXE 중 관절 공개분 | + ④ **C′(FK 목표, `camera: unknown`)** · ③ **T1 자체 보정 시도** · 공용 추적 | 위 + C′(그 로봇 기저 m, 카메라 모름), 잡기·놓기 픽셀 라벨 | T1 관문(≤ 5 px) 전에는 투영 점·카메라 정보가 든 C′ |
| **보정 있음** | MolmoBot(RBY1·Franka), RoboTwin, DROID[기초] | + 투영 QA · C′(카메라 정보) | 위 + EE 투영 점·접근 방향(카메라 좌표) | 깊이·GT 없는 3D 중심 |
| **+ 깊이 또는 물체 GT** | BEHAVIOR(깊이·분할·과제 물체 GT), MolmoBot(물체 시작 자세) | + ⑤ 3D·평면 QA | 물체 3D 중심(GT에서만), 탁자 평면 | 분할 ∩ 깊이 겉면 중심을 '중심'으로(9.1 cm 편향) |
| **깊이 추정만**(T3) | 어디든(RB2 등) | T3: 단안 m 깊이 모델 | **관문(≤ 3 cm) 통과 전에는 순서형 QA만**('더 가깝다') | m 단위 3D 답 |

### 10.2 네 트랙(+ 공용 추적 앞단)과 측정값

| 트랙 | 데이터 조건 | 방법(코드) | 관문 | 측정(오픈소스) | 여는 표본 |
|---|---|---|---|---|---|
| **T0 픽셀 전용** | 좌표계 없음 | MolmoAct 궤적 0–255 → 픽셀 + 튐·되돌림 필터(`src_molmoact.py`), RefSpatial 점(`src_refspatial.py`) | 2–5점, 한 걸음 ≤ 대각선 40 %, 급반전(> 135°) 없음 | 궤적 남김 **54 %(Bridge)·75 %(RT-1)·79 %(BC-Z)·76 %(보조 궤적)**. 눈: 시작점이 그리퍼 위, 같은 편의 이웃 행이 겹쳐 10행 간격 표집 | 궤적 3,200(각 800), RefSpatial 1,169 |
| **공용 추적 앞단**(T0·T1·T3가 함께 씀) | 영상 + (관절 사건) | CoTracker3 offline, 한 편에 한 번, 캐시 npz(`track.py`: 씨앗 고르기·합치기·사건·저장) | 두 검출기 일치(추적 ↔ 포인팅 ≤ 20 px)일 때만 라벨 | **L 단계(MolmoBot, 보정 숨김)**: 한 점 씨앗에서 그리퍼 추적 오차 **편별 중앙 19.2 px**(1024 px 영상), ≤ 20 px 52 %. 잡기 라벨 중앙 40 px(≤ 40 px 50 %), 놓기 61 px. RB2: 539편 캐시, 추적·포인팅 일치 **46.6 %**(6,795/14,587) | RB2 그리퍼 점 **6,746**·궤적 **2,638** |
| **② 그리퍼 검출(포인팅)** | 영상 | Molmo2-ER "point to the {left\|right} robot gripper"(무료 로컬 GPU) | — | **L 단계**: MolmoBot RBY1 옳은 그리퍼 **65.5 %**(다른 팔 3.2 %, 2,157회, 최근접 GT 점까지 중앙 10.2 px). BEHAVIOR R1Pro 48.2 %(다른 팔 7.9 %, 114회). RB2(앞선 눈 검사) 틀림 21–30 % | 검출 점(추적과 일치할 때만) |
| **T1 좌표계 만들기**(자체 보정) | 관절 + URDF | FK 3D 그리퍼 + 2D 검출 → RANSAC EPnP → 편 합동 LM + **조준점 오프셋(팔별 3)** + 초점(1), 좌우 재배정(`selfcal.py`) | 보류 편 재투영 **≤ 5 px**(무프레임 조사 관문) | **보정 숨기고 되찾기(MolmoBot Franka 30편)**: ① 정확한 2D(GT 투영 + 3 px 잡음, 'FK 클릭' 대용) → 참 TCP 재투영 **0.81 px**(30/30편 ≤ 5 px), 회전 1.35°, 중심 6.3 cm(깊이 방향 모호). ② Molmo2 포인팅 → **23.9 px**(0/25). ③ 추적(포인팅 씨앗) → 25.8 px. 초점 15 % 틀린 채 시작 → 재투영 0.88 px, 초점 오차 10 %(초점–거리 모호). **RB2 실데이터**: 합동 적합 fx **373**(추적) / 386(포인팅), ZED 사양 367. 명목 URDF 카메라와 1.1° / 6.0 cm. 보류 재투영 21–28 px → **관문 불통** | 통과한 리그만: 투영 점·궤적, 카메라 정보가 든 C′. **RB2는 불통**이라 0 |
| **T2 암묵(대량 이미지)** | 모든 원천 | ①·②·④ 표본을 대량으로, `camera: unknown`·`frame: pixel`·`frame: base_<로봇>` 표시로 섞어 모델이 스스로 관계를 배우게 함. 학습 시험은 E-OPEN8 O-A·E-XEMB8(ND-1과 맞춤) | 누수 0(학습 뒤) | 생성 수만 보고: RB2 C′(카메라 모름) **3,073**, RB2 픽셀 9,384, MolmoAct 3,200, RefSpatial 1,169 | 픽셀·C′(카메라 모름) |
| **T3 깊이 근사** | 영상(+ 초점 추정) | MoGe-2(단안 m 기하 + 내부값, `t3_moge.py`), 여러 프레임 추적과 결합(3D 궤적) | 3D 중심·평면 ≤ 3 cm | 11.2절 | 통과 전: 순서형 QA만 |
| **T4 렌더 정렬** | 관절 + URDF 메시 | CtRNet-X식(무프레임 조사) — **이번에 구현 안 함** | ≤ 5 px | — | T1 불통 리그(RB2)의 다음 수단 |

### 10.3 공용 추적 앞단을 나눠 써서 얻은 것 (사용자 제안 "점추적은 T,1,3에 다 들어갈 수 있을 것 같은데")

- **계산**: 편당 추적 1회(RB2 539편, H200 1장 약 25분, 쿼리 6)로 T0 라벨, T1 대응점, T3 3D 궤적(다음 단계)에 같은 캐시를 쓴다. 트랙마다 따로 검출하면 포인팅만 편당 약 2 × 프레임 수 번 호출해야 한다.
- **T1 정확도(RB2, 포인팅 대신 추적을 2D로 쓴 경우)**:
  - 합동 적합 정상점 43.7 → **49.0 %**.
  - 편별 카메라 흔들림(편 적합 ↔ 합동): 회전 25.3 → **13.5°**, 중심 29.5 → **15.2 cm**.
  - 명목 카메라와의 차: 1.58°/7.6 cm → **1.13°/6.0 cm**.
  - 초점: 386 → **373**(사양 367에 더 가까움).
  - 보류 재투영(21–25 px)은 비슷하다.
- **T1 정확도(보정 숨긴 Franka)**: 추적은 포인팅의 씨앗 오차(조준 편향)를 물려받아 재투영 25.8 px로 포인팅(23.9 px)과 비슷했다.
- **정리**: 추적은 흔들림은 줄이지만 **씨앗 편향**은 못 없앤다. 정확한 씨앗(보정 세트의 FK 클릭, 또는 사람 클릭 몇 개)이 있으면 T1이 5 px 관문을 넘는다(0.81 px). 포인팅 씨앗만으로는 넘지 못한다.
- **T4 필요**: T4 렌더 정렬이 씨앗 편향을 없애는 다음 수단이다.

### 10.4 권고 — 어떻게 섞나

1. **주 경로는 픽셀**(T0 + 공용 추적 → 잡기·놓기 픽셀, 2D 궤적, E-PT의 점 형식 조종 C-pt).
2. **관절이 있으면 C′를 FK로 먼저**: 카메라가 필요 없다(`camera: unknown`). RB2에서 3,073개가 나왔다.
3. **T1은 관문(≤ 5 px)을 넘는 리그에서만** 투영·카메라 정보에 쓴다. 넘기는 방법은 둘이다.
   - 사람 클릭 소량(편당 수 개) + FK로 씨앗 편향 제거. 보정 숨긴 실험의 'FK 클릭' 조건이 0.81 px였다.
   - T4 렌더 정렬.
4. **T3 → T1**: T3의 초점 추정(11.2절)을 T1 초점 초기값으로 쓴다. T1 카메라 + T3 깊이는 3D QA 후보이지만 3 cm 관문 전에는 순서형 QA만 만든다.
5. **3D m 답은 깊이·GT가 있는 원천에서만**(BEHAVIOR GT, MolmoBot 시작 자세).

## 11. 정답 세트 L 단계 수치 (학습 없이 라벨 정확도, 보정 숨김)

### 11.1 T1·②·추적 — 10.2절 표

### 11.2 T3 깊이 근사 — MoGe-2 (`Ruicheng/moge-2-vitl-normal`)

- **후보 확인**(1.5년·신뢰도, 2026-09-27 API):

  | 모델 | 공개 | 학회 | 별 | HF 좋아요 | 판정 |
  |---|---|---|---|---|---|
  | **MoGe-2** | arXiv 2507.02546, 2025-07-03 | 학회 미확인(전작 MoGe는 CVPR 2025 Oral) | microsoft/MoGe 2,981★ | vitl-normal 22 | 사용 |
  | **Depth Anything 3** | arXiv 2511.10647, 2025-11-13 | 학회 미확인 | 6,396★ | DA3METRIC-LARGE 28 | 다음 후보, 이번에는 돌리지 않음 |
  | VGGT | 2503.11651, 2025-03-14 | CVPR 2025 Best Paper, 14,434★ | — | — | **[기초]** — 12일 차로 1.5년 밖 |
  | UniDepthV2 | 2502.20110 | — | 1,266★ | — | **[기초]** |
  | Metric3D v2 | 2404.15506 | TPAMI | — | — | **[기초]** |
  | Depth Pro | 2410.02073 | ICLR 2025 | 5,730★ | — | **[기초]** |

- **BEHAVIOR 34프레임**(보정 숨김; GT 깊이, 과제 물체 GT 124개, 받침 면 37개; 파드 `t3/moge/`):

  | 항목 | 값 |
  |---|---|
  | 초점 추정 | 333 px(GT 306, **+8.8 %**) |
  | 깊이 AbsRel 중앙 | 0.081 |
  | δ1 | 0.955 |
  | 절대 오차 중앙 | 7.5 cm |
  | 척도 중앙 | 0.98 |
  | **물체 3D 중심 오차(유사 깊이)** | 중앙 **17.5 cm**, 광선 수직 5.3 cm. 같은 물체의 GT 깊이 겉면 기준 6.1 cm(6.1절 9.1 cm 편향과 같은 종류)에 유사 깊이가 11.6 cm를 더한다 |
  | **받침 면 거리 오차** | 중앙 **7.7 cm**(p90 19.0), 법선 1.9° |

  → **T3 관문(≤ 3 cm) 불통.** T3 표본은 순서형 QA('A가 B보다 가깝다')로만 쓴다. m 단위 3D 답에는 쓰지 않는다.
- **RB2(오픈, 보정 없음) 120프레임 초점 추정**: 중앙 **385 px**(p10–p90 370–403). ZED 사양 367, T1 추적 373 / 포인팅 386과 같은 범위다 → **T3 초점을 T1 초기값으로** 쓰는 권고의 근거.
- **하지 못한 것**: 추적 + 여러 프레임 일관성으로 깊이 척도를 고치는 판(요청 항목)과 DA3 비교. 다음 단계로 남긴다(시간). 여러 프레임 보정 전후의 cm 차는 **재지 않았다**.

### 11.3 BEHAVIOR 50과제 × 2편 (`behavior100/`)

- 100편 · 50과제, 오류 0, 인식 QA **53,605**:
  - obj_point 22,998
  - obj_center_cam(GT) 17,607
  - ee_point 7,577
  - table_plane 5,423
- **G1 EE가 오른 그리퍼 마스크 4 px 안: 74.2 %**(7,577/10,217).
  - 불통 판 눈 확인(12장): 10장은 고리가 **열린 두 손가락 사이 틈**(마스크가 아닌 빈 공간) 또는 손끝 바로 앞에 있었다. 2장만 어긋났다.
  - → 이 관문은 반지름 4 px가 너무 좁아 실제보다 낮게 나온다. 표본은 통과분만 썼다.
  - 다음 판에서는 마스크를 손가락 사이 볼록 껍질로 넓힌다.
- **물체 3D**:
  - GT 중심이 자기 마스크 안: 77.9 % → 이것만 3D 답을 만든다(G3를 필터로).
  - 분할 ∩ 깊이 겉면 중심 ↔ GT: 중앙 4.1 cm, 광선 수직 2.0 cm, 광선 방향 −3.0 cm. 50과제의 작은 물체가 많아 2편(라디오) 9.1 cm보다 작다. 그래도 2 cm 관문은 불통이라 **3D 답은 GT에서만** 만든다는 결정을 유지한다.
- **받침 면**: 적합 13,623 중 관문(인라이어 ≥ 50 %·기울기 ≤ 3°) 통과 5,422. 선반 옆면·찬장 문처럼 수평이 아닌 받침이 많다.
- **분할 거절**: 퍼짐 58,443 · 작은 마스크 41,272 · 깊이 구멍 2,444.
- **위에서 잡기 ≤ 30°: 31.2 %**(660회, 중앙 48°. 보조 측정 55회 29 %와 같다). ≤ 20° 19.5 %.
- **C′ 기저 정지**: 39.1 %(3,703구간). 50과제에는 이동하며 조작하는 편이 많다 → C′ 원천으로는 약하다.

## 12. E-OPEN8 — 오픈소스만으로 만든 소규모 학습 세트 (user-log 123: "일단 오픈소스를 가지고 학습을 할건데 어떤걸 써서 어떻게 할거임? 대규모는 아니고 소규모로 해두돼")

- 파드 `/data/harvest/out/xemb/open8/`(`train.jsonl` 6,500행, `counts.json`, `plan.json`). 빌더는 `tools/xemb/build_open8.py`다.
- 크기는 L8 한 에폭(6,521)과 같게 맞췄다. 사전 등록 초안은 `docs/stage3/prereg_open8.md`(실행 안 함)다.

| 스트림 | 원천(라이선스) | 트랙 | 행 | 비고 |
|---|---|---|---|---|
| RB2 C′(카메라 모름) | ROBOTIS AI Worker RB2 실데이터 | ④ FK 목표, `frame: base_ffw_bg2`, `camera: unknown` | 1,000 | 우리 로봇 계열. T1 관문 불통이라 카메라 정보가 든 C′는 0 |
| RB2 그리퍼 점(추적 ∩ 포인팅) | 같음 | T0 + 공용 추적 | 950 | 두 검출기가 20 px 안에서 일치할 때만 |
| RB2 그리퍼 궤적 | 같음 | T0 + 추적 | 400 | 다음 놓기까지 5점 |
| MolmoAct OXE 궤적 | MolmoAct-Pretraining-Mixture(CC BY 4.0) | T0 | 1,000 | BC-Z·RT-1·Bridge·보조 궤적 |
| MolmoBot RBY1 점 | molmobot-data(ODC-BY) | 보정 있음 | 1,000 | EE 투영(G1 필터)·물체·놓을 곳·GT 3D 중심 |
| MolmoBot Franka C′ | 같음 | C′(카메라 정보) | 1,000 | 위에서 잡기 ≤ 30° |
| MolmoBot Franka 점 | 같음 | 보정 있음 | 500 | EE(≥ 0.6 m)·물체·놓을 곳 |
| RefSpatial | Apache-2.0 | 일반 공간 | 650(10 %) | 다른 지시문 |
| T3 유사 깊이 3D | RB2 + MoGe-2 | T3 | **0** | 관문(≤ 3 cm) 불통 |

- `frame` 분포: pixel 3,716 · base_ffw_bg2 1,000 · base_franka 1,000 · cam_head 335 · none 449.
- 빌더 거부 0건(영상 없음·머리 줄 없음·C′ 답 누수 없음).
- 학습한 모델의 누수 시험은 등록 5절에서 한다.

## 13. 확인 경로

- **논문**(arXiv HTML 본문): MolmoAct·Robo2VLM·RoboRefer·HAMSTER·X-VLA·InternVLA-M1·RoboBrain 2.0.
- **코드 얕은 클론**(`D:\tools\scratch_qdd\xemb_howto\`, `xemb_data\`): allenai/molmoact, KeplerC/robo2VLM, Zhoues/RoboRefer, liyi14/HAMSTER_beta, 2toinf/X-VLA, InternRobotics/InternVLA-M1, huggingface/lerobot, StanfordVL/BEHAVIOR-1K(main·v3.7.2), allenai/molmospaces, RoboTwin-Platform/RoboTwin.
- **HF API·카드·datasets-server 행**, OpenReview·arXiv Comments.
  - 별 수: 앞선 조사 문서 값을 쓴 것이 있다. GitHub API 요청 한도 때문이다.
- **표본 측정**: 시제품(6절)과 보조 측정(`xemb_data/` 스크립트 `rt_topdown.py`·`b1k_grasp2.py`·`mb_grasp.py` 등).
