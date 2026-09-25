# VLM으로 로봇을 물체 쪽으로 조종할 때 무엇이 가장 잘 되나 — 조종 표현·학습법 문헌 조사 (2026-09-25)

작성: 문헌 조사 에이전트, 2026-09-25. 질문(user-log 75 원문): "근데 이게 확실하지는 않잖아? / VLM을 어떤식으로 물체를 향해 로봇을 조종할때 최고의 성능이 나오게 학습할 수 있는지에 대한 신뢰 자료 찾아서 그것도 정리를 좀 해보자".

**우리 설계(조사 대상, "오락실 조이스틱")**: 융합 VLA(Qwen3-VL-4B + LoRA, 정본 §58)가 0.33 s 결정 스텝마다 typed 보기를 고른다 — `dir_xy` 9가지(대각·none 포함), `dir_z` up/down/none, `mag_coarse` 5구간(0.5/1/2/4/8 cm 중심), `phase` continue/hold/next, `target`, 접촉 근처 `fine_dir`(M3 §4.4). 시간차 호출 여러 표를 M4 규칙이 확정하고, flow-matching action expert가 **확정된 보기**(+ 캐시된 백본 문맥, KI stop-grad)를 조건으로 연속 청크를 만든다(§67 C4: decide → chunk 두 호출). 학습 때 expert 조건은 **정답 보기**(`committed` = 라벨)다(`harvest/train/stageb_model.py` `cond()`).
**출발 사실**: S-E2E(공개 AI Worker 실물, 10 Hz)에서 결정 라벨 = 다음 3스텝(0.3 s) 말단 실제 변위의 부호(데드밴드 1 cm)·MAG 구간(`se2e_data.md` 76행) — 즉 결정은 **expert 자신이 낼 가까운 미래 행동을 거칠게 양자화한 것**이다. 결정 정확도 약 0.72, 오답은 거의 "움직이냐 마냐·크기 한 칸"(부호 반대 8/155), 0.1 s 이웃 라벨 불일치로 잡은 상한 약 0.93, 같은 스텝 기준 9k 표본 이상에서 포화(`se2e_diag.md`). 결정 지연 예산 p95 ≈ 0.3 s(설계값 0.28 s, §59).

**규칙**: (1) 1.5년 규칙 — 대략 2025-03 이후. 그 전 것은 "기간 밖, 기초 문헌"으로만. (2) 신뢰도 규칙(원문) "신뢰도 낮은 논문과 깃 저장소는 최대한 쓰지 않는다. 쓰느니만 못하다." — 학회 채택(arXiv Comments·OpenReview API·학회 논문 목록으로 확인) 또는 대형 연구실 + 별 많은 저장소만 근거로 썼다. 별 수는 2026-09-25 GitHub API 값. 제외한 것은 7절에 사유와 함께. (3) 수치는 논문 본문·표(arXiv HTML 원문을 내려받아 텍스트로 확인)에서 옮겼다. 그림에만 있는 수치는 옮기지 않고 "그림에만 있음"으로 적었다. **웹 검색 할당량이 소진되어** arXiv API·OpenReview API·GitHub API·학회 논문 목록 페이지(WebFetch)로 확인했다. Semantic Scholar는 속도 제한(429)으로 인용 수를 대부분 못 얻었다.

---

## 1. 요약

**판정 한 줄**: 조이스틱(동작 수준 typed 결정 → 연속 expert)은 **틀린 설계가 아니라 "반쪽"이다.** 동작 수준 명령을 VLM과 저수준 정책 사이의 인터페이스로 쓰는 것은 최신 대형 연구실 결과가 지지한다(Gemini Robotics 1.5의 Thinking VLA가 "move gripper to the left so that it is closer to the clothes" 같은 생각을 거쳐 행동하고, Steerable Policies(RSS 2026)에서 단일 명령 형식 중 동작 명령이 가장 효과적). 그러나 통제된 비교는 **시각에 근거한 공간 표현(점·궤적·상자)이 언어·동작 표현보다 낫고, 저수준이 더 잘 따르며, 한 가지 형식이 모든 상황을 이기지 않는다**고 말한다(VLA-OS, NeurIPS 2025; MolmoAct; Steerable Policies). 그리고 **저수준이 조건을 무시하거나, 틀린 결정이 그대로 전파되는 위험**이 반복해서 보고됐다. 우리 설계에 없는 것은 (i) "어디로"를 말하는 공간 목표, (ii) 틀린·무시된 결정에 대한 대비, (iii) 결정층 RL이다.

**핵심 수치(조건은 2절 표)**:
- VLA-OS(NeurIPS 2025, 같은 구조·데이터로 표현만 바꿈, LIBERO-Long, 기준 66.0%): 계획을 **보조 손실로만** 쓰면 언어 68.0 / 시각(상자·말단 궤적·어포던스) 71.0 / 미래 이미지 72.5; 계층형에서 언어 63.5 대 시각 69.0 대 셋 다 74.2. 정답 계획을 줬을 때 저수준 추종 점수(IFS) 언어 0.84 대 시각 0.93. 계획을 **명시적으로 먼저 생성**해 행동 머리에 넣고 행동 머리가 원 입력을 못 보면 42.7–67.5로 **오히려 떨어짐**(계획 오류 누적).
- MolmoAct(ICRA 2026): 궤적(trace) 그려 조종 성공 75%, 자유 언어로 조종보다 +33 pt; π0-FAST를 언어로 조종하는 것보다 +29 pt(각 15회).
- OpenVLA-OFT(RSS 2025): 같은 조건에서 256구간 이산 행동 90.2% 대 연속 L1 95.3%·확산 95.4%(LIBERO 평균, 스위트당 500회) — 양자화 정밀도 손실 약 5 pt.
- ECoT-Lite(CoRL 2025 Oral): 추론을 **학습 때만** 쓰고(추론 드롭아웃) 실행 때 생성하지 않아도 전체 ECoT와 같다(LIBERO-90 세 분할 평균 76.4% 대 76.6%, 표준 VLA 67.4%). 생성하는 ECoT는 1–1.2 Hz로 느림, "thinking token"은 −3.8 pt.
- 결정층 RL: SFT 뒤 RL이 반복해서 크게 올린다(πRL: π0.5 네 벤치마크 평균 55.6 → 86.6%; Embodied-R1: 같은 데이터 SFT 대 RFT로 Where2Place 41.25 → 69.50; DSRL(CoRL 2025 Oral): 얼린 π0의 잡음 입력만 RL로 조종해 실물 토스터 5/20 → 18/20).
- 조건 무시: LIBERO-Plus — 지시문을 빈 값으로 바꿔도 OpenVLA-OFT 성능이 Object 스위트에서 거의 그대로, 목표 물체를 바꾸면 성공 거의 0. KI 저자도 "correlations in the training data still cause the model to sometimes ignore language instructions".

**권고(순위, 4절에 상세)**:

| 순위 | 무엇 | 유지/수정/교체 | 기대 이득 | 비용 | 결정 지연 영향 | 해시·정본 |
|---|---|---|---|---|---|---|
| 0 | **E-SR0 진단(학습 없음)**: 지금 체크포인트에서 expert가 확정 보기를 따르는지·틀린 보기가 얼마나 해치는지 잰다 | — | 다음 결정의 근거 | 매우 낮음(GPU 약 1 h) | 없음 | 없음 |
| 1 | **공간 궤적 보조 손실**(미래 말단 경유점 회귀, 기존 aux 머리 재사용) — 실행 때 생성 없음 | 수정(추가) | 중(VLA-OS 보조 손실형 시각 +5.0/+6.5 pt 대 언어 +2.0) | 낮음 | **0** | `stageb_data.py`(AUX 목록) → `files_sha` 바뀜, 재학습 |
| 2 | **결정 조건 강건 학습**: expert를 정답 보기만이 아니라 모델 예측 보기로도 학습(노출 맞춤) + 준수도 지표(E-AE-1 오프라인판) | 수정 | 중(28 % 틀린 결정의 전파 차단; VLA-OS 명시 계획 오류 누적 −5.5~−23.3 pt 근거) | 낮음 | **0** | `stageb_model.py` → `files_sha` 바뀜 |
| 3 | **명시적 공간 목표 조건**(점·경유점 머리 → expert 조건, 조이스틱 방향·크기와 병행) | 수정(확장) | 중–고(새 물체·복잡 장면; MolmoAct·HAMSTER·Steerable) | 중–고, 시뮬(정확한 카메라 보정)에서 먼저 | 머리 방식이면 수 ms 추정, 토큰 생성 방식이면 +수백 ms(불가) | 모델 + M4가 연속·2D 목표를 어떻게 확정하는지 **정본 결정 필요** |
| 4 | **결정 토큰 RL**(D26 계획: 스냅샷 분기 기대 보상 + KL 닻) | 유지(계획대로) | 중–고(SFT→RL 반복 확인) | 중(시뮬 필요) | 0 | 가중치만이면 불변, 손실 코드를 `stageb_model.py`에 넣으면 바뀜 |
| 5 | **추론(CoT)은 실행 때 생성하지 않고 학습 비계로만**, 상위 추론은 Astra·경계 시점에만 | 유지(지금 구조와 같음) | 저–중 | 낮음 | 생성하면 3–7배 느려짐 → 금지 | 추론 문장을 결정 프롬프트에 넣으면 PROMPT_FILES 바뀜 |
| 6 | 크기 구간을 더 잘게 | 보류 | 낮음(오답은 경계 근처·움직임 유무) | 낮음 | 0 | `jevcall`/`options` → `question_id@vN` 새 판, 보정 재생성 |
| — | 조이스틱을 버리고 점만 / 연속만 | **교체 비권고** | — | — | — | — |

**권하는 실험**: E-SR0(진단, 학습 없음) → E-SR1(S-E2E 2×2: 기준 / +궤적 보조 / +결정 강건 학습 / 둘 다, 시드 2개, 같은 계산량, 주 지표 = **모델이 예측한 보기로 조건을 줬을 때의** expert 청크 오차) → E-SR2(시뮬 폐루프: 명시적 공간 목표 조건 대 조이스틱). 5절에 사전 등록 틀.

---

## 2. 근거 표

신뢰도 칸: 학회(확인 경로) · 연구실 · 저장소 별. "교란"은 비교가 공정하지 않은 점.

### 2.1 (a) 동작 수준 이산 명령(언어 동작·방향 토큰) — 우리 조이스틱과 가장 가까운 것

| 출처 | 신뢰도 | 표현 | 학습 | 벤치마크·조건 | 수치 | 일반화 발견 | 교란·주의 |
|---|---|---|---|---|---|---|---|
| **Steerable VLA Policies** (Chen, …, Driess, Pertsch, Levine; arXiv 2602.13193) | **RSS 2026**(학회 논문 목록 74번, 저자 목록 확인) · UC Berkeley + PI · 코드 미확인 | 저수준 VLA가 과제·하위과제·**동작("move left")**·궤적 픽셀·점·조합을 모두 받음(전부 텍스트) | Bridge 3.8만 과제 라벨 → 합성 명령 약 200만(Gemini·Molmo·SAM2·DETR 파이프라인), 프레임마다 명령 형식을 무작위로 바꿔 BC. 상위는 (1) 추론 + 명령을 SFT한 VLM, (2) 맥락 학습하는 Gemini 3.0 | 실물 WidowX, ECoT-Lite와 같은 Bridge 과제 모음 | **수치는 그림에만 있음**. 본문 문장: 사람 오라클이 모든 형식을 쓰면 "nearly 100% success rate"; 형식 하나로 제한해도 모두 과제 수준 언어보다 나음; "**when using a single steering modality, motions are the most effective**"; 궤적·점은 의미 일반화(처음 보는 물체)에서 최고, 동작은 공간 관계 과제에서 최고; "no one-size-fits-all steering modality exists" | 학습한 상위 + Steerable이 ECoT·ECoT-Lite·OpenVLA·π0.5를 모두 이김(동작·의미 일반화에서 차이 가장 큼). 맥락 학습 VLM이 형식을 골라 쓰면 하위과제만 쓰는 SayCan형보다 큼 | 동작 명령을 받은 정책은 "**servos left towards an object, rather than moving left unconditionally**" — 명령을 맥락으로 재해석한다(정본 §35가 이미 인용: Jev 크기 권위와 충돌 가능) |
| **Gemini Robotics 1.5** (GDM, arXiv 2510.03342) | 기술 보고서(학회 없음) · Google DeepMind · gemini-robotics-sdk 612★ | Thinking VLA가 행동 사이에 언어 생각을 끼움 — 예 "move gripper to the left so that it is closer to the clothes" → 그다음 행동 | 대규모 다중 로봇 사전학습 + 생각 문장 | 다단계 과제(옷 색깔별 분류 등) | 생각 켬이 진행 점수를 "sizable" 올림(**그림에만 있음**). 장기 과제: Thinking VLA 단독 진행 점수 최대 44% 대 상위 ER 모델 + VLA 에이전트 "near 80%"; 기성 Gemini 2.5 Flash를 상위로 쓰면 복잡 과제에서 약 절반 | 저자 설명: 어려운 "지시 → 행동" 번역을 "지시 → 짧은 동작 문장"(VLM이 잘함) + "동작 문장 → 행동"(쉬운 사상) 둘로 쪼개서 이득 | 비공개 모델, 수치 재현 불가 → **방향 지지 근거로만** |
| RT-H: Action Hierarchies Using Language (arXiv 2403.01823) | **기간 밖, 기초 문헌**(2024-03, 게재 표기는 이번에 확인 못 함) | "move arm forward" 같은 **언어 동작**을 먼저 예측하고, 그것과 과제로 행동 예측 | 같은 모델 안 두 단계 | 다양한 다과제 데이터 | (이번에 수치 옮기지 않음) 초록: 언어 동작 개입으로 교정되고, 그 개입에서 배우는 것이 원격조작 개입보다 낫다 | 서로 다른 과제 사이에서 저수준 동작 구조를 공유 | 우리 조이스틱의 직계 조상 |
| SPF: See, Point, Fly (arXiv 2509.22653, 정본 M3 §2 #1에서 이미 원문 확인) | CoRL 2025 | 학습 없는 VLM이 **이미지 위 점** / 연속 수치를 글로 / 후보 점 선택 | 없음(영점) | 시뮬 드론 항법, 과제당 5회 | 점 지정 100% 대 **수치를 글로 7%** 대 후보 선택(PIVOT) 40%(Gemini 2.0 Flash, Table 2) | 영점 VLM은 좌표·수치 출력보다 점 지정이 압도적 | 영점·드론 조건. 학습한 우리 모델과 직접 비교 불가 |

### 2.2 (d)(e) 공간 중간 표현(점·궤적·상자·미래 이미지)과 계층형

| 출처 | 신뢰도 | 표현 | 학습 | 벤치마크·조건 | 수치 | 일반화 발견 | 교란·주의 |
|---|---|---|---|---|---|---|---|
| **VLA-OS** (Gao 외, arXiv 2506.17561) | **NeurIPS 2025 poster**(OpenReview) · HeegerGao/VLA-OS 147★ | 같은 구조·데이터에서 계획 표현만 바꿈: 언어(Task·Plan·Subtask·**Move**·Gripper Position·Bounding Box 등 8키 텍스트), 시각(물체 상자·말단 궤적·어포던스를 32×32 위치 토큰으로), 미래 이미지. 패러다임: 행동만(A) / 통합-암묵(I-I: 계획은 보조 손실만) / 통합-명시(I-E: 계획 생성 후 행동) / 계층(H: 행동 머리가 원 이미지도 봄) | Qwen2.5 0.5B, 처음부터 | LIBERO-Long(10과제×50시연), 상위 3 체크포인트 × 20회 평균 | A 66.0. **I-I**: 언어 68.0 / 시각 71.0 / 미래이미지 72.5 / 셋 71.7. **I-E**: 60.5 / 52.5 / 67.5 / L+V **42.7** / 셋 50.7. **H**: 63.5 / 69.0 / 71.7 / 셋 **74.2**. 정답 계획 준 추종 점수 IFS(H) 언어 0.84 / 시각 0.93 / 미래이미지 0.90. 추가 벤치(3D Colosseum·실물 변형체·FurnitureBench·DexArt·PerAct2)에서 I·H가 A보다 +0.9 ~ +8.0 pt | "Visually grounded planning representations are easier for low-level policy to follow"(Finding 9); Colosseum 전체 섭동 일반화 A 6.1 / I 6.2 / H 7.4(절대값이 매우 낮음) | **언어 계획 약 2000토큰 자기회귀 생성**이 느리고 오류가 누적(Finding 2·10) — 우리 typed 결정(보기 확률 한 번 읽기, 생성 없음)과 비용 구조가 다르다. 0.5B 처음부터 학습 |
| **MolmoAct** (Lee, Duan 외, AI2; arXiv 2508.07917) | **ICRA 2026**(OpenReview 기록) · allenai/molmoact 389★ | 깊이 인식 토큰 → **2D 궤적(trace)** → 행동, 세 단계 모두 자기회귀 | Molmo 7B, 사전학습(이산 제어·점·궤적·VQA) + 중간학습 + 사후학습 | SimplerEnv, LIBERO, 실물 Franka | SimplerEnv 시각 일치 영점 70.5%, 변형 집계 72.1%(RT-2-X보다 +7.8), LIBERO 평균 86.6%. 실물 OOD(언어 바꿈·위치·방해물·새 물체) π0-FAST보다 과제 진행 +23.3%. 중간학습 +5.5%. **조종: 궤적 스케치로 조종 성공 75%, 자유 언어 조종보다 +33 pt, π0-FAST 언어 조종보다 +29 pt(각 15회)** | 공간 계획을 거치면 분포 이동에 강하다(변형 집계와 시각 일치 차 <1%) | "궤적 없음" 동일 조건 절제는 없다. 저자 한계: 2D 궤적이라 **카메라 깊이 방향 움직임이 부정확**, 추론 토큰이 많아 제어 주기가 데이터 주기보다 느림 |
| **HAMSTER** (Li 외, NVIDIA·UW; arXiv 2502.05485) | **ICLR 2025 poster**(OpenReview) · 기간 경계(2025-02, 학회 2025-04) · liyi14/HAMSTER_beta 66★(적음 — 학회가 근거) | 상위 VLM이 이미지 위 **2D 경로** → 3D 저수준 정책(RVT-2·3D-DA)이 경로 그린 이미지로 행동 | VLM은 싼 데이터(시뮬 RLBench·비디오)로 미세조정, 저수준은 소량 과제 데이터 | 실물 74과제 222회, Colosseum 시뮬 5시드 | 실물 7개 일반화 축 평균 OpenVLA보다 +20 pt(상대 +50%). Colosseum 3D-DA 0.18±0.10 → HAMSTER+3D-DA 0.43±0.05(데이터 50%만 써도 0.36±0.04) | 경로가 시각 변화에 대한 강건성을 줌 | **저수준이 경로를 강제로 따르지 않는다**: RVT 실패의 72%가 경로 불추종, 3DDA는 10% — 저수준 구조가 추종도를 가른다 |
| **Embodied-R1** (Yuan 외, arXiv 2508.13998) | **ICLR 2026 poster**(OpenReview) · pickxiguapi/Embodied-R1 156★ | 3B VLM이 4종 **점**(물체 지칭·영역·기능 부위·시각 궤적) 출력 → 모션 플래너(CuRobo) | 2단계 **RFT(GRPO)**, "질문–검증" 쌍(여러 정답 허용). 같은 데이터·배치 SFT 대조군 | 점 벤치 4종, SimplerEnv WidowX 영점, 실물 XArm 8과제 | SFT → RFT: Where2Place 41.25 → **69.50**, VABench-P 50.46 → 66.00, Part-Afford 40.20 → 56.63, RoboRefIt 83.85 → 85.58; VABench-V MAE 65.2 → 45.0. SimplerEnv 영점 56.2%(π0-FAST 48.3, OpenVLA-OFT 41.8), 실물 87.5% | "여러 정답이 있는 점 문제에서 SFT는 한 점에 과적합, RL은 맞는 답을 모두 강화" | SimplerEnv 비교는 플래너 실행 대 종단 VLA라 **교란**(방식이 다름) |
| **UniVLA** (Bu 외, OpenDriveLab; arXiv 2505.06111) | **RSS 2025**(학회 목록, 제목 "Learning to Act Anywhere with Task-centric Latent Actions") · OpenDriveLab/UniVLA 1,134★ | VLM(Prismatic-7B)이 **이산 잠재 행동 코드**(과제 중심, 언어 조건으로 분리) 예측 → 10.8M 디코더가 연속 청크 | 비디오에서 비지도 잠재 행동 학습 → VLM 사전학습 → 디코더 적응 | LIBERO, 실물 4과제, 항법 | LIBERO 평균 95.2%(본문: OpenVLA보다 +18.7, LAPA보다 +29.5). 실물 LAPA보다 +36.7%. 일반화(조명·방해물·새 물체) 평균 68.9% 대 LAPA 28.9%·OpenVLA 20.0%. 4090에서 10 Hz(청크 12) | **코드의 질이 결정적**: Ego4D 사전학습에서 과제 중심 코드가 모든 시각 변화를 담는 코드보다 LIBERO 평균 +6.4 pt; 과제와 무관한 코드로 학습하면 LIBERO-Long 성공 **거의 0**, 토큰 예측 정확도도 낮음 | 코드는 학습된 것(사람이 정한 방향 구간이 아님) |
| **GO-1 / AgiBot World** (arXiv 2503.06669) | 학회 미확인 · 대형 연구실(Shanghai AI Lab·AgiBot) · OpenDriveLab/AgiBot-World 3,193★ | VLM(InternVL2.5-2B) → **잠재 계획기가 이산 잠재 행동 토큰** → 행동 전문가(잡음 제거)가 그 토큰 조건으로 연속 행동 | 대규모 실물 데이터 사전학습 | 실물 5과제, 과제당 30회(보이는 설정 10 + 변형 20) | 잠재 계획기 추가로 평균 과제 완수 점수 **+0.12** | 물체 위치 강건성·지시 따르기 과제에서 이득이 큼 | **구조가 우리와 가장 비슷**(이산 토큰 → 연속 전문가 조건). 학회 확인 못 함 → 보조 근거 |
| **villa-X** (Chen 외, Microsoft; arXiv 2507.23682) | **ICLR 2026 poster**(OpenReview) · microsoft/villa-x 211★ | 잠재 행동 전문가(ACT-latent)가 먼저 잠재 행동 생성 → 로봇 행동 전문가가 그것을 조건으로(결합 확산) | 비디오 + 로봇 데이터 | SIMPLER(Google·WidowX) | Google 평균 77.7% 대 **잠재 경로 제거 36.5%**, WidowX 62.5% 대 49.0% | 잠재 행동 조건이 "essential" | 잠재 경로 제거가 비디오 사전학습 효과까지 함께 빼므로 **교란** |

### 2.3 (b)(c) 이산 행동 토큰 대 연속 머리, 둘의 결합

| 출처 | 신뢰도 | 비교 | 조건 | 수치 | 우리와의 관련 |
|---|---|---|---|---|---|
| **OpenVLA-OFT** (Kim, Finn, Liang; arXiv 2502.19645) | **RSS 2025**(학회 목록) · moojink/openvla-oft 1,399★ · 기간 경계(2025-02 말) | 같은 백본에서 256구간 이산 토큰 대 연속 L1 대 확산 | LIBERO 4스위트, 스위트당 500회, 병렬 디코딩+청크 공통 | 이산 90.2% / 연속 L1 **95.3%** / 확산 95.4%. 저자: "likely due to higher precision" | 거친 양자화는 정밀도를 깎는다 — 단 우리 조이스틱 구간은 행동 자체가 아니라 연속 expert의 **조건**이다 |
| **FAST** (Pertsch 외, PI; arXiv 2501.09747) | **RSS 2025**(학회 목록) · openpi 13,994★ · **기간 밖(2025-01), 기초 문헌** | 단순 구간화 토큰 대 DCT 압축 토큰 대 확산(π0) | 고주파 실물 데이터 | 단순 구간화는 주파수가 높아지면 오차가 급증해 "the model simply copies the first action"; π0-FAST는 확산 π0와 성능이 같고 학습 계산 최대 5배 적음; 대신 청크당 약 750 ms 대 확산 약 100 ms(4090) | 조밀한 시간에 이산 토큰을 자기회귀로 생성하면 지연이 크다 → 우리처럼 **보기 확률 한 번 읽기**가 지연 면에서 유리 |
| **Knowledge Insulating VLA (KI)** (Driess 외, PI; arXiv 2505.23705) | **NeurIPS 2025 spotlight**(OpenReview) · openpi 13,994★ | 백본 = 이산 FAST 토큰 + VLM 데이터 다음 토큰 예측, expert = flow, **expert → 백본 기울기 차단** | DROID·LIBERO·실물 | DROID 평가 0.55±0.09 대 π0 0.49 대 π0-FAST 0.45. LIBERO(일반 모델에서 미세조정) Spatial 98.0 / Object 97.8 / Goal 95.6 / 10 85.8 / 90 96.0. 차단 없이 함께 학습하면 언어 따르기·학습 속도 저하(그림). 단순 구간화 토큰으로 바꿔도 연속만보다는 낫고 FAST보다는 못함 | 우리가 이미 채택(§52·S-E2E "KI stop"). 저자 한계: "**correlations in the training data still cause the model to sometimes ignore language instructions**" — 조건 무시 위험 |
| **HybridVLA** (Liu 외, PKU; arXiv 2503.10631) | **ICLR 2026 poster**(OpenReview; NeurIPS 2025는 거절) · PKU-HMI-Lab/Hybrid-VLA 356★ | 한 LLM에서 자기회귀 이산 행동 + 확산 연속 행동 공동 학습, 이산 토큰 확신도로 두 결과를 섞음 | RLBench 10과제 | 따로 학습: 이산만 0.57 / 확산만 0.60 → 공동 학습: 이산 0.62 / 확산 0.66 → 확신도 앙상블 **0.74** | 이산·연속 공동 학습이 서로를 돕는다(우리 결정 NLL + fm 공동 손실과 같은 방향). 확신도 문턱 0.94 아래에서는 이산 예측이 믿을 수 없다 |
| Discrete Diffusion VLA (arXiv 2508.20072) | **ICML 2026**(OpenReview; ICLR 2026은 거절) | 이산 토큰을 확산식 병렬 디코딩 | LIBERO | 96.4%, 저자 "0.7% behind the overall continuous SOTA considering the inherent loss from bin-based tokenization" | 촘촘한 구간(256)이면 이산의 손실은 작다 — 우리 5구간과는 다른 이야기 |

### 2.4 (f) 행동 전 추론(chain-of-thought)

| 출처 | 신뢰도 | 무엇 | 조건 | 수치 | 우리와의 관련 |
|---|---|---|---|---|---|
| **ECoT-Lite: Training Strategies for Efficient Embodied Reasoning** (Chen, Belkhale, …, Pertsch, Levine 외; arXiv 2505.08243) | **CoRL 2025 Oral**(OpenReview) · ECoT 저장소 MichalZawalski/embodied-CoT 418★ | 추론(하위과제·**동작**·상자·그리퍼 위치)을 (i) 실행 때도 생성(ECoT) (ii) 학습 때만 섞고 실행 때 끔(추론 드롭아웃) (iii) 추론으로 사전학습 (iv) thinking token | LIBERO-90 세 분할(표준·섭동·섭동+방해물), MiniVLA | 평균: 표준 VLA 67.4 / 전체 ECoT 76.6 / **드롭아웃 76.4** / 사전학습 72.8 / 공동학습 69.3 / 비계 70.3 / thinking token 63.4–63.9(−3.8). Bridge에서 기존 VLA보다 +10–19%, ECoT 1–1.2 Hz 대 3.5+ Hz | 추론의 이득은 대부분 **표현 학습**에서 온다 → 실행 때 생성 없이 얻을 수 있다. 우리 결정 토큰 NLL도 expert 문맥에 대한 보조 손실 역할을 한다(가설) |
| **OneTwoVLA** (Lin 외; arXiv 2505.11917) | **ICLR 2026 poster**(OpenReview) · Fanqi-Lin/OneTwoVLA 239★ | 한 모델이 중요한 순간(하위과제 끝·오류·사람 입력)에만 추론, 나머지는 행동 | 실물 장기 과제 3개 | 평균 87%, 평면 VLA보다 +30, 이중 시스템(Gemini 2.5 Pro 상위)보다 +24 | 이중 시스템은 상위 지연 때문에 늦게 반응 — 우리 Astra(경계·사건 호출, §45)와 같은 문제·같은 처방 방향 |
| **ThinkAct** (Huang 외; arXiv 2507.16815) | **NeurIPS 2025 poster**(OpenReview) | 추론 VLM을 궤적 정렬 보상으로 RL → 시각 계획 잠재를 행동 모델에 | SimplerEnv·LIBERO | SFT 출발 56.4 → RL 60.1(SimplerEnv); 추론 1회당 행동 수 N = 25/50/75/100 → LIBERO 84.0/84.6/84.4/83.7 | 추론을 매 스텝 할 필요 없음(N에 거의 둔감) |
| **CoT-VLA** (Zhao 외, NVIDIA·Stanford; arXiv 2503.22020) | **CVPR 2025** · 인용 581(S2) | 미래 목표 이미지를 먼저 생성 후 행동 | 실물·시뮬 | 기존 최고 VLA보다 실물 +17%, 시뮬 +6%; 이미지 토큰 256개 생성으로 **평균 7배 느림** | 우리 지연 예산(0.3 s)에서는 생성형 추론 불가 |

### 2.5 (h) 결정층·정책 RL (D26에 이미 있는 것은 요약만)

| 출처 | 신뢰도 | 무엇을 RL로 | 수치 | 우리와의 관련 |
|---|---|---|---|---|
| **DSRL: Steering Your Diffusion Policy with Latent Space RL** (Wagenmaker 외, Berkeley·UW; arXiv 2506.15799) | **CoRL 2025 Oral**(OpenReview) · ajwagen/dsrl 228★ | 확산 정책은 얼리고, **입력 잡음(잠재) 공간**에서만 RL — 블랙박스 | π0(얼림) 조종: 실물 "Turn on toaster" 5/20 → 18/20, "Put spoon on plate" 15/20 → 19/20; 실물 WidowX 단일과제 20% → 거의 100% | **저차원 조종 인터페이스에 RL을 거는 것이 표본 효율적**이라는 직접 근거 — 우리 결정 토큰 RL(expert 얼림)과 같은 모양 |
| RL Token (Xu, Springenberg 외, PI; arXiv 2604.23073) | PI 프리프린트, 학회 미확인 · S2 인용 43 | VLA가 내는 압축 "RL 토큰" 위 작은 actor-critic, VLA에 닻 | 실물 4과제(나사·케이블타이·충전기·이더넷)에서 가장 어려운 구간 속도 최대 3배 | 보조 근거 |
| π*0.6 / Recap (PI; arXiv 2511.14759) | **RSS 2026**(학회 목록 87번) | 이점(advantage) 조건 정책 + 가치 함수, 시연·자율 롤아웃·개입 섞음 | 가장 어려운 과제에서 처리량 2배 이상, 실패율 약 절반(초록) | 조건 입력으로 정책을 조종한다는 점에서 같은 계열 |
| πRL (Chen 외; arXiv 2510.25889) | 학회 미확인(본문 키워드에 ICML 표기만) · RLinf/RLinf 5,368★ | flow VLA(π0·π0.5) 자체를 온라인 RL | π0 SFT 네 벤치 평균 51.1 → 80.3, π0.5 55.6 → 86.6; LIBERO 소수 시연 SFT + RL 98.3% 대 전체 시연 SFT 96.9%. OOD: 환경 변화(ManiSkill·CALVIN)에는 이득이 옮겨가나 새 과제(MetaWorld)에는 안 옮겨감 — "localized to action-level refinement" | RL은 행동 다듬기에 강하고 과제 간 일반화는 못 만든다 |
| SimpleVLA-RL (arXiv 2509.09674) / RL4VLA (arXiv 2505.19789) / Chu 외 (2501.17161) | **ICLR 2026**(OpenReview) 1,864★ / **NeurIPS 2025** 288★ / ICML 2025(기간 밖) | D26 §2.1 참조 | LIBERO 과제당 시연 1개 SFT 48.9 → RL 96.9; SFT 0.781 → RL 0.938(IND); SFT 확대 시 OOD 붕괴 | D26 결론 유지: SFT로 형식 → RL |
| RoboMonkey (Kwok 외, Stanford; arXiv 2506.17811) | **CoRL 2025 poster**(OpenReview) · 45★(적음) | RL 아님 — 후보 행동 표집 + VLM 검증기 선택 | 실물 OOD +25 pt, SIMPLER +9 pt; 후보 16개 약 650 ms | 우리 M4(여러 표 확정)와 발상이 닿음. 지연 때문에 그대로는 불가 |

### 2.6 (g)(i) 공동학습·일반화·조건 무시

| 출처 | 신뢰도 | 발견 | 수치 |
|---|---|---|---|
| **LIBERO-Plus** (arXiv 2510.13626) | 학회 미확인 · sylvestf/LIBERO-plus 460★ | VLA는 언어를 거의 안 쓴다: 지시를 빈 값으로 바꿔도 OpenVLA-OFT Object 스위트 성능 거의 불변(Long만 하락), 목표 물체를 바꾸면 성공 "dropped nearly to zero", 원래 과제를 그대로 수행 | 언어 섭동 평균 −25.3(두 번째로 작은 하락), 카메라·초기 자세 섭동은 95% → 30% 미만 |
| KI (위) | NeurIPS 2025 | expert 기울기 차단 + VLM 데이터로 언어 따르기 개선, 그래도 완벽하지 않음 | (그림) |
| π0.5 (arXiv 2504.16054, CoRL 2025, D26에서 인용) | CoRL 2025 | 웹 데이터 빼면 전체 성공 차이는 유의하지 않으나 **새 물체(OOD)에서 유의하게 나빠짐** | D26 §4.1 |
| MolmoAct, HAMSTER, UniVLA, Embodied-R1 (위) | | 공간·잠재 중간 표현이 분포 이동·새 물체에 강하다는 보고가 반복 | 위 표 |

---

## 3. 증거가 우리 조이스틱 설계에 대해 말하는 것

### 3.1 지지되는 점
1. **동작 수준 인터페이스 자체**: Gemini Robotics 1.5 Thinking VLA의 동작 문장 경유, Steerable Policies "single modality 중 motions most effective", RT-H(기초), ECoT의 "Move" 추론이 모두 "VLM이 짧은 동작 명령을 고르고 저수준이 그것을 연속 행동으로"를 지지한다. 사람이 이해·개입하기 쉽다는 이점(RT-H 언어 개입, Steerable 사람 오라클 거의 100%)도 우리 M4·Astra 구조와 맞다.
2. **이산 토큰 → 연속 전문가 조건 구조**: GO-1(잠재 계획기 +0.12), villa-X(잠재 경로 제거 시 77.7 → 36.5, 교란 있음), UniVLA(이산 코드 + 작은 디코더로 10 Hz), HybridVLA(이산·연속 공동 학습이 둘 다 올림)가 같은 구조의 이득을 보고했다.
3. **생성 없는 결정**: 생성형 계획·추론은 느리고(ECoT 1–1.2 Hz, CoT-VLA 7배, π0-FAST 750 ms, MolmoAct 제어 주기 불일치) 계획 오류가 누적된다(VLA-OS I-E). 보기 확률을 한 번 읽는 우리 방식은 이 비용을 피한다. 추론의 이득은 학습 때 비계로 대부분 얻을 수 있다(ECoT-Lite 드롭아웃 76.4 대 ECoT 76.6).
4. **KI stop-grad + 결정 토큰 NLL**: KI(NeurIPS 2025)와 같은 처방이며, 결정 NLL은 VLA-OS I-I·ECoT-Lite가 보인 "보조 손실로서의 계획"의 이득(+2 ~ +9 pt)을 받을 수 있는 자리다(우리에게서 따로 잰 적은 없음).
5. **결정층 RL 계획(D26)**: DSRL·RL Token·Embodied-R1·ThinkAct·πRL이 "작은 조종 공간 위 RL"과 "SFT → RL"을 반복 확인.

### 3.2 반박되거나 약한 점
1. **공간 근거가 없다**: 통제 비교(VLA-OS)에서 시각 표현이 언어 표현보다 보조 손실형 +5.0/+6.5 대 +2.0, 계층형 +3.0/+5.7 대 −2.5, 저수준 추종 0.93 대 0.84였다. MolmoAct 궤적 조종은 언어 조종보다 +33 pt. Steerable는 처음 보는 물체에서 궤적·점이 최고라고 했다. 우리 `target` 보기는 물체 ID뿐이고, "어디로"는 방향·크기 구간으로만 말한다 → **새 물체·복잡한 장면·같은 물체 여러 개**에서 약할 가능성이 크다.
   - 단, VLA-OS의 언어 계획은 약 2000토큰 자기회귀 생성이라 느리고 누적 오류가 컸다(Finding 2·10). 우리 typed 결정은 이 약점이 없으므로 **언어 쪽 불리함의 일부는 우리에게 해당하지 않는다**(교란).
2. **"한 형식이 다 이기지 않는다"**(Steerable): 동작은 공간 관계, 점·궤적은 물체 지정, 과제·하위과제는 분포 안에서 강하다. 조이스틱만으로는 한 가지 형식에 묶인다.
3. **라벨이 사람이 정한 경계에 묶여 있다**: UniVLA는 이산 코드의 질이 성능을 가른다고 보였다(과제 무관 코드 → LIBERO-Long 거의 0). 우리 S-E2E 라벨은 0.3 s 변위의 1 cm 데드밴드·로그 구간 경계에서 끊기며, 오답이 바로 그 경계("움직이냐 마냐·한 칸")에 몰려 있다(`se2e_diag.md` 5.1–5.3).

### 3.3 위험
1. **양자화·거친 구간이 정밀도를 막는 위험** — 부분적으로만 해당. OFT(이산 256구간 90.2 대 연속 95.3)·RoboDawn 저자 한계("이산 의미 명령은 미세 보정에 너무 거칠다", 정본 M3 #18)는 **구간이 행동 자체일 때**의 이야기다. 우리는 expert가 연속 행동을 내므로 구간은 조건일 뿐이다. 그래서 진짜 위험은 반대편이다: expert가 조건을 따르면 거친 조건이 정밀도를 묶고, 안 따르면 조이스틱이 장식이 된다. 어느 쪽인지는 아직 안 쟀다(E-SR0).
2. **틀린 결정의 전파(노출 차이)**: 학습 때 expert는 **정답** 보기를 조건으로 받지만 실행 때는 **모델이 고른**(약 28 % 틀린) 보기를 받는다. VLA-OS I-E(계획을 먼저 만들고 행동 머리가 원 입력으로 교정하지 못하면 −5.5 ~ −23.3 pt)가 같은 모양의 위험이다. 우리 expert의 `ctx`는 문맥 전체(시스템 + 이미지 + 상태 토큰)의 백본 한 층 은닉이라(`stageb_model.forward_shared`·`context`, `hidden_states[self.layer]`) 이미지 정보를 받는다 — 계획 임베딩만 받는 VLA-OS I-E보다는 원 입력도 보는 H에 가깝다. 그래도 학습 때 조건이 늘 정답이었으므로 틀린 조건을 무시·교정하는 법을 배운 적이 없다.
3. **expert가 조건을 무시하는 위험**: LIBERO-Plus(언어 무시), KI 저자 한계, HAMSTER(RVT 실패의 72 %가 경로 불추종)가 반복 보고. 반대로 Steerable 정책은 명령을 맥락으로 재해석해 "물체 쪽으로" 간다 — 성능에는 좋을 수 있으나 Jev 크기 권위(정본 §35)와 충돌한다. **준수도(E-AE-1)를 재지 않으면 둘을 구별할 수 없다.**
4. **이산 선택의 누적**: 0.33 s마다 결정이 쌓이므로 한 스텝의 작은 오차가 경로 전체로 누적될 수 있다. M4 시간차 합의가 흔들림은 줄이지만(정본의 새로움), 방향 편향은 줄이지 못한다. 폐루프에서만 보인다(E-SR2).
5. **지연**: 추론 토큰·점 좌표를 **생성**하게 바꾸면 예산을 넘는다. 생성 토큰당 비용은 우리 서버에서 안 쟀다 — 수십 토큰이면 수백 ms 규모로 추정 [추정, 실측 필요]. 따라서 공간 목표는 **생성이 아니라 같은 순전파 위의 머리**로 넣어야 한다.

---

## 4. Harvest 권고 (순위)

각 항목: 무엇 / 근거 / 기대 이득 / 비용 / 결정 지연 / 바뀌는 것(정본 §71 보충·§77: `stagea_train.PROMPT_FILES`·`stageb_train.PROMPT_FILES_B` = `stageb_data.py`·`stageb_model.py`의 바이트가 `files_sha`에 들어가 어긋나면 `runtime/fused_model.check_prompt`가 체크포인트를 거부. 질문 문구·보기가 바뀌면 `question_id@vN`·`SERIALIZER_VERSION`·보정 파일도 새로).

**0. E-SR0 진단 — 먼저, 학습 없이** (5.1절)
- 지금 S-E2E 체크포인트(고정 사본 `code_se2e_run`, 오프라인 전용 — §77 보충(2))에서 expert 조건을 {정답 / 모델 예측 / 반대 방향 / 무작위 다른 보기}로 바꿔 청크 오차와 FK 준수도를 잰다. 이것이 3.3의 위험 1–3 중 무엇이 실제인지 가른다. 비용 GPU 약 1 h, 해시 무관(기존 코드로 추론만).

**1. 공간 궤적 보조 손실 (유지 + 추가)**
- 무엇: 미래 말단 경유점(로봇 기준 `arm_base_link`, +0.3/+0.6/+0.9/+1.5 s의 Δ, 12개 회귀값)을 기존 `aux` 머리(`AuxGeomHead`, 지금은 시뮬 기하 전용 `AUX_REG`)로 예측하게 한다. 실행 때는 쓰지 않는다(VLA-OS I-I형). 시뮬(R2)에서는 머리캠 이미지 평면 경유점(정확한 카메라 보정)도 더할 수 있다.
- 근거: VLA-OS I-I 시각 +5.0·미래이미지 +6.5 대 언어 +2.0(LIBERO-Long, 0.5B 처음부터 — 교란: 우리와 규모·데이터 다름), ECoT-Lite 사전학습 +5.4·드롭아웃 +9.0(LIBERO-90 평균, 추론 내용에 상자·그리퍼 위치 포함).
- 기대 이득: 중(가설). 오답 유형("움직이냐 마냐")이 짧은 미래 궤적과 직결되므로 결정 정확도에도 도움 가능.
- 비용: 낮음 — S-E2E 행 생성기가 이미 FK로 미래 말단 위치를 계산한다(`se2e_data.py`).
- 지연: 0(실행 때 머리 안 씀).
- 바뀌는 것: `stageb_data.py`(`AUX_REG` 이름 추가) → `files_sha` 바뀜 → 재학습. 프롬프트·`question_id@vN` 불변.

**2. 결정 조건 강건 학습 + 준수도 지표 (수정)**
- 무엇: expert의 flow 손실 조건 `committed`를 확률 p(예: 0.5)로 **같은 순전파의 모델 예측 보기**(argmax, 기울기 차단)로 바꿔 학습(노출 맞춤). 준수도 = 조건을 바꿨을 때 expert 청크의 FK 말단 변위가 명령 방향을 따르는 비율(E-AE-1 오프라인판, 정본 §33).
- 근거: VLA-OS I-E의 계획 오류 누적(−5.5 ~ −23.3 pt)과 H(원 입력으로 교정)의 회복, ECoT-Lite 드롭아웃(학습 때 조건을 흔들어도 이득 유지). **"예측 조건으로 학습"을 직접 잰 신뢰할 만한 VLA 논문은 찾지 못했다 → [우리 접목]**.
- 기대 이득: 중 — E-SR0에서 "오류 전파"가 확인되면 1순위로 올린다.
- 비용: 낮음(`stageb_model.losses`에서 `lps`가 이미 계산됨).
- 지연: 0. 추론 때 분류기 없는 안내(CFG, 조건 있음/없음 두 번 적분)로 준수도를 올리는 선택지는 expert 순전파가 2배 — expert가 작아(768/8/12) 청크 호출 쪽 비용이며 결정 예산과는 별개 [추정].
- 바뀌는 것: `stageb_model.py` → `files_sha` 바뀜. CFG를 쓰려면 학습 때 조건 드롭아웃("없음" 토큰)이 필요 → `stageb_data.py`의 결정 어휘도 바뀜.

**3. 명시적 공간 목표 조건 (확장, 시뮬에서 먼저)**
- 무엇: 결정 순전파의 이미지 토큰 은닉 위에 **점(또는 짧은 경유점) 머리**를 두고(머리캠 21×12 = 252칸 + 활성 손목 104칸 위 softmax — 생성 없음), 그 결과를 조이스틱 방향·크기와 **함께** expert 조건으로 넣는다. 조이스틱은 버리지 않는다(Steerable: 형식마다 강한 상황이 다름).
- 근거: MolmoAct 궤적 조종 75 %(언어 조종 +33 pt), HAMSTER 실물 +20 pt·Colosseum 0.18 → 0.43, VLA-OS 계층형 셋 결합 74.2(최고), Steerable 새 물체에서 점·궤적 최고, SPF 영점 점 지정 100 % 대 수치 글쓰기 7 %.
- 위험: 2D 점은 카메라 깊이 방향이 부정확(MolmoAct 한계) → 깊이 방향은 조이스틱 `dir`·`mag`가 맡는 것이 합리적(보완 관계). 저수준이 점을 안 따를 수 있음(HAMSTER RVT 72 %) → 2번의 준수도 지표를 점에도.
- 비용: 중–고 — 점 라벨(시뮬 특권 상태 + 정확한 카메라 보정으로 투영; S-E2E 실물 데이터는 RB1에 머리 관절 기록이 없고 RB2는 머리가 약 0.55 rad로 고정이라 URDF + 공칭 내부 파라미터 투영만 가능 — `se2e_data.md` 20·50행), 모델 머리, **M4가 연속·2D 목표를 어떻게 확정하는지**(칸 확률 합의? 중앙값?)는 정본 결정 사항(논문 새로움 M4와 직결).
- 지연: 머리 방식이면 선형층 하나 수준(수 ms 이하 추정, 실측 필요). 좌표를 텍스트로 생성하면 수십 토큰 → 예산 초과(불가).
- 바뀌는 것: `stageb_model.py`·`stageb_data.py` → `files_sha`; 점을 typed 질문(격자 칸 보기)으로 만들면 `jevcall`·`options`·직렬화 → `question_id@vN` 새 판, 보정 재생성, 보기 수 상한(약 17, 정본 §27 R3) 때문에 거친 → 세밀 두 질문(D-줌) 필요.

**4. 결정 토큰 RL (유지, D26 계획 그대로)**
- 근거 추가: DSRL(얼린 π0를 저차원 조종 공간 RL로 5/20 → 18/20), RL Token, Embodied-R1(SFT 대 RFT +28 pt Where2Place), ThinkAct(+3.7), πRL(+29 ~ +31 pt, 단 새 과제로는 안 옮겨감).
- 조건: 폐루프 시뮬 필요 → S-E2E(공개 실물 데이터)에서는 불가. 1–3의 결과가 나온 뒤 시뮬에서.
- 지연 0. 해시: 가중치만 바뀌면 불변이나 손실 코드를 `stageb_model.py`에 넣으면 바뀜.

**5. 추론은 비계로만 (유지)**
- 실행 때 CoT를 생성하지 않는다(ECoT 3배 느림, CoT-VLA 7배). 원하면 Astra 계약 요약·하위과제 설명을 학습 때만 섞는 추론 드롭아웃/사전학습(ECoT-Lite)을 절제로 둔다. 상위 추론은 지금처럼 Astra를 경계·사건에만(OneTwoVLA +24 pt 대 이중 시스템, ThinkAct 추론 빈도 둔감).
- 바뀌는 것: 결정 프롬프트에 추론 문장을 넣으면 `PROMPT_FILES`·`question_id@vN`. 학습 데이터에만 넣으면 `stageb_data.py`.

**6. 구간을 더 잘게 — 보류**
- 오답의 34 %만 경계 밴드 안이고 대부분 "움직이냐 마냐"(`se2e_diag.md` 5.3), 인접 0.1 s 라벨도 9–20 % 바뀐다 → 구간을 늘리면 경계가 늘어 모호함이 커진다. 거친 → 세밀 두 질문(D-줌)은 정본에 이미 비교 조건으로 있다. 연속 정보가 필요하면 6이 아니라 1(연속 회귀 보조)로.

**교체 비권고**: (i) 점만으로 조종 — 깊이 방향 약점, M4 typed 합의·Jev 크기 권위(§35)를 잃음, Steerable에서 단일 형식은 전 형식보다 못함. (ii) 결정층 없이 연속 행동만 — 사용자 핵심 구조(M4 시간차 확정)와 해석 가능성을 잃고, 얻는 근거도 없다(우리 expert는 이미 연속).

---

## 5. 사전 등록 틀 (제안 — 판정 문턱은 메인 세션이 실행 전 고정)

공통: §56 — S-E2E 결과는 파이프라인 규모 시험이라 **논문 근거로 쓰지 않는다**(RB1 라이선스 미표기, §63 (6)). 검증 300개(`val_keys_sha` `e22f6d8ef7fc`, RB1 150 + RB2 150). 부트스트랩 10,000회(정본 §72 `analysis.stats.N_BOOT`), 에피소드 군집, seed 0, 95 % 백분위.

### 5.1 E-SR0 — 조건 민감도 진단 (학습 없음)
- 대상: `se2e_A_s0`·`se2e_B_s1` `last/`(고정 사본 `code_se2e_run`, 오프라인만).
- 조건 4개(같은 표본·같은 flow 잡음 시드로 짝): **GT**(라벨 보기) / **PRED**(모델 결정 확률 argmax — 폐루프의 M4 대신 단일 호출 근사) / **FLIP**(`dir_xy`·`dir_z`를 반대 부호로, none은 그대로) / **RAND**(질문마다 무작위 다른 보기).
- 지표: (1) 정규화 청크 MSE(`sample_mse_norm`, 정답 `action_exec` 대비), (2) **방향 준수도** = 청크 앞 3스텝 관절 → FK 말단 변위(`se2e_data` FK 그대로)의 부호가 조건 보기의 non-none 축 부호와 같은 비율, (3) 크기 준수도 = 조건 `mag` 구간 순서와 |Δ|의 Spearman.
- 판정(예시 문턱, 메인 고정):
  - "**선택 무시**": FLIP 준수도 < 0.5 **그리고** (MSE_FLIP − MSE_GT)/MSE_GT < 0.10 → 조이스틱이 실행을 조종하지 않는다 → 권고 2(+CFG 드롭아웃)를 최우선, 3의 가치도 재평가.
  - "**오류 전파**": (MSE_PRED − MSE_GT)/MSE_GT ≥ 0.20이고 짝 차 95 % 하한 > 0 → 권고 2 필수.
  - 둘 다 아니면 "조건 정상" → 권고 1·3 순서대로.
- 비용: 추론만(300 × 4 × 2 체크포인트), GPU 약 1 h.

### 5.2 E-SR1 — S-E2E 2×2 학습 (조이스틱 기준 대 상위 대안 2개)
- 팔 4개 × 시드 2개(0, 1): **B0** 기준(현재 코드·직렬화로 S-E2E 재학습 — 옛 체크포인트는 ser-A-min-1이라 런타임이 거부) / **T1** + 궤적 보조 손실(권고 1: 로봇 기준 미래 말단 Δ @ +3·+6·+9·+15 스텝, `aux` 머리, λ_aux 사전 고정) / **C1** + 결정 조건 강건 학습(권고 2: p = 0.5로 예측 보기 조건) / **T1+C1**.
- 계산 고정: S-E2E와 같음(묶음 8, lr 1e-4, 워밍업 3 % + 코사인, 1 에폭 = 4,686 스텝, 끝 체크포인트). 8판 × 약 1.8 h(GPU 2장 → 약 7–8 h, `se2e_train.md` 3절 실측 기준).
- **주 지표 P1**: 검증 300개에서 **PRED 조건** 청크 MSE(종단 오프라인 행동 오차 — 결정이 틀려도 행동이 좋으면 이긴다).
- 보조: GT 조건 MSE, PRED−GT 간격, 결정 정확도(질문별·전환 층 — `temporal_context` 문서 5절과 같은 정의), FLIP 준수도, 궤적 보조 오차(cm, T1), decide p95(변화 없어야 함 — 보조 머리는 실행 때 안 씀).
- 채택 규칙(예시): 팔 X를 B0 대신 채택 ⇔ 두 시드 합쳐 P1 상대 감소 ≥ 5 % **그리고** 짝 차 95 % 상한 < 0 **그리고** 결정 정확도 하락 ≤ 0.01 **그리고** FLIP 준수도 하락 ≤ 0.05. T1+C1이 두 단독보다 P1 추가 3 % 이상이면 둘 다 채택. 결과는 방향과 무관하게 모두 보고.
- 해시: T1·C1 모두 `files_sha` 바뀜(체크포인트는 새 해시로만 적재). 프롬프트·`question_id@vN` 불변.
- 병행 주의: 시간 맥락 실험(E-TC, `TEMPORAL_FILES`)과 같은 GPU·같은 검증을 쓰면 서로의 기준(B0)을 공유할 수 있게 코드 판을 맞춘다.

### 5.3 E-SR2 — 시뮬 폐루프 (본 단계, 나중에 따로 사전 등록)
- R2 시뮬 데이터(30 Hz, mug_tray·mug_marker·bottle_tray, 정본 §66), 정확한 카메라 보정으로 이미지 평면 점·궤적 라벨.
- 팔: {E-SR1 승자(조이스틱) / 승자 + 명시적 공간 목표 조건(권고 3)} × {standard, random5}, M4 켬.
- 지표: 과제 성공률, standard → random 낙폭(RD), 최종 정렬 오차 mm, E-AE-1 준수도(방향·점), Jev 권위 위반율(§35), decide p95(≤ 0.33 s), FAIL·Astra 호출 수.
- 판정: 성공률 짝 차 95 % 하한 > 0 그리고 RD 악화 없음 그리고 p95 ≤ 문턱일 때만 공간 목표 조건을 주 시스템에 넣는다. M4가 점을 확정하는 규칙은 이 실험 전에 정본에 먼저 적는다.
- 그 뒤: 권고 4(결정 토큰 RL, D26 절차).

---

## 6. 출처 목록

| # | 출처 | 게재(확인 경로) | arXiv | 코드·별(2026-09-25) |
|---|---|---|---|---|
| 1 | Steerable Vision-Language-Action Policies for Embodied Reasoning and Hierarchical Control | RSS 2026(학회 논문 목록 74번) | 2602.13193 | 미확인 |
| 2 | Gemini Robotics 1.5 | GDM 기술 보고서 | 2510.03342 | gemini-robotics-sdk 612 |
| 3 | RT-H: Action Hierarchies Using Language | 기간 밖, 기초 문헌 | 2403.01823 | — |
| 4 | SPF: See, Point, Fly (정본 M3 인용 재사용) | CoRL 2025 | 2509.22653 | (정본 기록) |
| 5 | VLA-OS | NeurIPS 2025 poster(OpenReview) | 2506.17561 | HeegerGao/VLA-OS 147 |
| 6 | MolmoAct | ICRA 2026(OpenReview 기록) | 2508.07917 | allenai/molmoact 389 |
| 7 | HAMSTER | ICLR 2025 poster(OpenReview), 기간 경계 | 2502.05485 | liyi14/HAMSTER_beta 66 |
| 8 | Embodied-R1 | ICLR 2026 poster(OpenReview, arXiv Comments) | 2508.13998 | pickxiguapi/Embodied-R1 156 |
| 9 | UniVLA | RSS 2025(학회 목록, arXiv Comments) | 2505.06111 | OpenDriveLab/UniVLA 1,134 |
| 10 | AgiBot World Colosseo (GO-1) | 학회 미확인 | 2503.06669 | OpenDriveLab/AgiBot-World 3,193 |
| 11 | villa-X | ICLR 2026 poster(OpenReview) | 2507.23682 | microsoft/villa-x 211 |
| 12 | OpenVLA-OFT | RSS 2025(학회 목록) | 2502.19645 | moojink/openvla-oft 1,399 |
| 13 | FAST | RSS 2025(학회 목록), 기간 밖 | 2501.09747 | openpi 13,994 |
| 14 | Knowledge Insulating VLA | NeurIPS 2025 spotlight(OpenReview) | 2505.23705 | openpi 13,994 |
| 15 | HybridVLA | ICLR 2026 poster(OpenReview) | 2503.10631 | PKU-HMI-Lab/Hybrid-VLA 356 |
| 16 | Discrete Diffusion VLA | ICML 2026(OpenReview, arXiv Comments) | 2508.20072 | 미확인 |
| 17 | ECoT-Lite: Training Strategies for Efficient Embodied Reasoning | CoRL 2025 Oral(OpenReview) | 2505.08243 | embodied-CoT 418 |
| 18 | OneTwoVLA | ICLR 2026 poster(OpenReview) | 2505.11917 | Fanqi-Lin/OneTwoVLA 239 |
| 19 | ThinkAct | NeurIPS 2025 poster(OpenReview) | 2507.16815 | 미확인 |
| 20 | CoT-VLA | CVPR 2025(arXiv journal-ref) | 2503.22020 | 미확인 |
| 21 | DSRL: Steering Your Diffusion Policy with Latent Space RL | CoRL 2025 Oral(OpenReview) | 2506.15799 | ajwagen/dsrl 228 |
| 22 | RL Token | PI 프리프린트 | 2604.23073 | — |
| 23 | π*0.6: a VLA That Learns From Experience | RSS 2026(학회 목록 87번) | 2511.14759 | — |
| 24 | πRL | 학회 미확인 | 2510.25889 | RLinf/RLinf 5,368 |
| 25 | SimpleVLA-RL | ICLR 2026 poster(OpenReview) | 2509.09674 | PRIME-RL/SimpleVLA-RL 1,864 |
| 26 | RL4VLA: What Can RL Bring to VLA Generalization? | NeurIPS 2025(arXiv Comments) | 2505.19789 | gen-robot/RL4VLA 288 |
| 27 | RoboMonkey | CoRL 2025 poster(OpenReview) | 2506.17811 | robomonkey-vla/RoboMonkey 45 |
| 28 | LIBERO-Plus | 학회 미확인 | 2510.13626 | sylvestf/LIBERO-plus 460 |
| 29 | π0.5 / Chu 외 SFT vs RL | CoRL 2025 / ICML 2025(기간 밖) — D26 인용 재사용 | 2504.16054 / 2501.17161 | openpi 13,994 / SFTvsRL 335 |

## 7. 제외한 것과 이유

| 항목 | 이유 |
|---|---|
| FOREWARN: From Foresight to Forethought (2502.01828) — VLM이 정책 후보 중 고르는 조종 | OpenReview에 워크숍(ICLR 2025 World Models, RSS 2025 OOD)만 확인, 본 학회 없음 |
| A0: Affordance-Aware Hierarchical Model (2504.12636) | 학회 표기 없음(arXiv Comments·OpenReview 검색 모두) |
| PointVLA (2503.07511) | 학회 표기 없음 |
| RoboBrain 2.0 (2507.02029), Robix (2509.01106), RationalVLA (2506.10826), G0 (2509.00576), OpenHelix (2505.03912) | 기술 보고서·학회 미확인, 또는 질문과 관련 약함 |
| GR-3 (2507.15493), InstructVLA (2507.17520, ICLR 2026), X-VLA (2510.10274, ICLR 2026), VLA-Adapter (2509.09372, AAAI 2026) | 신뢰도는 충족하나 이번 질문(조종 표현 비교)에 직접 수치를 주지 않아 본문을 읽지 않음 — 근거로 쓰지 않음 |
| VLA-0 (2510.13054, NVIDIA, 492★) | 학회 미확인, 정본 M3 #11에 이미 있음 — 새로 인용하지 않음 |
| Steerable Policies·Gemini Robotics 1.5·KI의 그림 속 수치 | 본문·표에 수치가 없어 옮기지 않음(그림 읽기는 오차가 커서) |
| Magma (CVPR 2025, 2502.13130), TraceVLA (ICLR 2025, 2412.10345), RoboPoint (2406.10721) | 기간 밖 또는 경계 밖, 같은 방향 근거가 기간 안(MolmoAct·HAMSTER·Embodied-R1)에 있어 생략 |
| Semantic Scholar 인용 수 | API 속도 제한(429)으로 대부분 못 얻음 — 인용 수를 신뢰도 근거로 쓰지 않았다 |

## 8. 이 조사의 한계
- 웹 검색 할당량 소진으로 arXiv 제목 검색·OpenReview 검색·GitHub API에 의존했다. 2025-03 이후 상위 학회 논문 중 놓친 것이 있을 수 있다(특히 "방향 토큰 대 점"을 같은 모델에서 직접 비교한 연구).
- **우리와 같은 형태(typed 방향·크기 구간 → flow expert 조건)를 다른 표현과 같은 조건에서 비교한 신뢰할 만한 논문은 찾지 못했다.** 가장 가까운 통제 비교는 VLA-OS(언어 계획에 "Move" 포함 대 시각 계획)와 Steerable Policies(동작 대 점·궤적, 수치는 그림)다. 따라서 3절의 판정은 "방향이 일관된 여러 간접 근거"이지 우리 조건의 측정값이 아니다 — 5절 실험이 그 몫이다.
- 여러 비교가 교란돼 있다: 모델 크기·데이터·영점 대 미세조정·플래너 사용 여부(Embodied-R1), 비디오 사전학습 동반(villa-X), 생성 길이(VLA-OS 언어).
- "예측 보기로 expert 학습(노출 맞춤)", "이미지 토큰 위 점 머리", "M4로 점 확정"은 문헌에 직접 선례를 확인하지 못한 **우리 접목**이다.
