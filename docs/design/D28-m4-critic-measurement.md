# D28. 융합 런타임에서 M4 (b)·M7 critic의 "측정"을 무엇으로 할 것인가 — 조사·설계·사전 등록 시험

작성: D28 조사 에이전트. 로컬 `date -u` = 2026-09-24 18:59 UTC(정본 §60 제목의 '2026-09-25'는 KST 날짜를 잘못 붙인 것이다 — 시계 문제가 아니었다, 정본 §67 C1·R7 2회차 K1 정정). git 커밋 안 함. 유료 API 호출 없음.
요청(user-log 원문): "저 M4의 크리틱 저거는 무조건 해결을해 1년반 내 논문 싹다 깃도 뒤져서 신뢰성있는걸로 찾아서 해봐봐". 신뢰도 규칙(원문): "신뢰도 낮은 논문과 깃 저장소는 최대한 쓰지 않는다. 쓰느니만 못하다." / "신뢰도가 무조건 있어야 하고, 스타도 어느 정도 있어야 하고, 논문도 좋아요(반응)를 많이 받은 것이어야 한다."
근거로 읽은 우리 문서: 정본 `00-interfaces.md` §1–§9·§21·§31·§35·§39·§45·§50–§60, `M4-overlap-commit.md` §0·§2.2·§4.2, `M7-progress.md` §2·§4·§5, `D10b-critic-checkvla.md` §2, `docs/stage3/results/r1_perception.md` §1·§3, `r4_stageB.md` §1·§2, `pool.md`, `labeler.md`, 코드 `harvest/sim/snapshot.py`(`ROBOT_ARRAYS`, `obs.raw.grip.effort`)·`harvest/sim/scene.py`(`gripper_effort` = `applied_torque`)·`harvest/predicates.py`(`holding`은 폭 < 8 cm·effort ≥ 1 요구).

---

## 0. 결론 (먼저)

1. **측정은 "한 곳"이 아니라 출처가 다른 두 곳으로 나눈다.** `expected_after` 술어를 **로봇 쪽**(그리퍼 열림, 쥠/빈 집기, 쥔 채 들림, 접촉에서 멈춤)과 **세계 쪽**(물체–물체 `on`/`in_contact`, `near`, 물체 위치)으로 나누고,
   - 로봇 쪽 = **고유 감각 코드 규칙**(그리퍼 폭 + 그리퍼 전류 + 팔 관절 `effort`의 `ref(t)` 대비 잔차). 결정적이라 **T1**(하드 채널 가능).
   - 세계 쪽 = **같은 백본의 "확인 헤드"**가 **실행 뒤 다음 관측**(머리 + 활성 손목 이미지 + 고유 감각)을 보고 `expected_after` 술어의 참거짓 확률을 낸다. 시뮬 특권 상태로 학습(R4에 이미 있는 보조 기하 헤드의 술어 7개 BCE를 그대로 확장), 온도 + split conformal로 보정. 학습된 값이라 **T2**(소프트 채널만).
   - M4 (b)(1) `ref(t)` 대비 연속 잔차는 지금도 고유 감각(관절·TCP)이 측정이다 → **바뀌지 않는다.** 문제는 (b)(2) 술어였다.
2. **1순위 설계 = (i) 확인 헤드 + (iii) 고유 감각의 두 채널.** 2순위(절제·보조) = (ii) 예측 잠재 대 관측 잠재 일치(FLARE식 미래 잠재 헤드를 같은 백본에). (iv) Astra 성공 판정은 M4 (b)에 쓰지 않고 **단계 경계(T_sub)·하트비트의 느린 감사**로만 둔다. 토큰 엔트로피·확률은 **측정이 아니다**(근거 §2.3). [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
3. 선택은 §4의 사전 등록 오프라인 시험 **E-M4b-meas**로 한다. 풀·DEV 스냅샷·R1 데이터 + DEV 시드 실패 주입 롤아웃(새로 생성, TEST·CAL 시드 불사용)으로 술어별 균형 정확도·보정·conformal 커버리지(M4 (b))와 에피소드 FWER·고정 창 재현율(M7)을 잰다.
4. 사용자 원칙과의 관계: 둘 다 **런타임 추가 호출 0**(확인 헤드는 다음 호출의 문맥 순전파에 얹힘, 고유 감각은 코드) → 3 Hz 루프·비정지 원칙 불변. 융합 원칙(§58): 세계 쪽 측정이 **같은 모델 안**으로 들어간다. 명시적 인식(R1)은 기준선 행으로만.

---

## 1. 조사 방법과 한계

- 기간: 2025-03-23 이후. 이전은 "기간 밖, 기초 문헌"으로 표시.
- 방법: 이 세션의 WebSearch 예산은 이미 소진돼 있었다(첫 호출에서 "200 of 200" 응답). 그래서 (a) Semantic Scholar 일괄 조회(인용 수·학회·날짜, 2회 배치 39편), (b) Semantic Scholar 키워드 검색(8회, 속도 제한으로 일부 빈 결과), (c) arXiv abs/html 원문 직접 읽기(약 25쪽), (d) GitHub API(스타·마지막 푸시)로 했다. arXiv 검색 API는 2회 시도했으나 빈 응답(다른 에이전트와 겹칠 위험 때문에 더 쓰지 않음).
- **한계(숨기지 않음)**: WebFetch는 요약 모델을 거친다 — 아래 "원문"의 인용은 요약 도구가 돌려준 문장이며, 표 수치 중 "요약 도구 경유"로 표시한 것은 PDF 표를 우리가 직접 대조하지 않았다. CheckVLA 수치는 D10b(PDF 27쪽 정독)에서 가져왔다. 고유 감각 쪽은 키워드 검색이 산업용 모터 고장 논문만 돌려줘 **기간 안 로봇 논문은 TA-VLA 하나만** 원문 확인했다(§6 확인 못 한 것).
- 인용 수 = Semantic Scholar 2026-09-24/25 조회값. 스타 = GitHub API 조회값.

---

## 2. 측정원 분류와 근거 표

### 2.1 분류 (무엇을 "측정"으로 쓰나)

| 계열 | 신호 | 대표 | 우리 3 Hz·비정지 루프 적합 |
|---|---|---|---|
| A. 명시적 인식 → 코드 술어 | 검출·깊이 → 3D 중심 → 기하 술어 | 우리 R1(M1) | **부적합(실측)**: 3D p50 35 mm, 손목 머그 누락 87.6 %, 지연 p95 379 ms, 라벨 0.612 < 최빈 0.634 |
| B. 학습된 성공·결과 판정(VLM/VLA) | 관측(+지시)으로 성공/진행/술어 확률 | SAFE, Self-Improving EFM, GR-ER 1.5, VLAC, Robo-Dopamine, SuccessVQA | 같은 백본 헤드면 추가 지연 거의 0. 별도 대형 모델은 지연·비용 문제 |
| C. 예측 대 관측 일치(세계 모델·잠재) | 행동 조건 예측 잠재 vs 다음 관측 잠재 | CheckVLA, Foresight(V-JEPA 2-AC), FLARE(학습 목적), V-JEPA 2 | 외부 세계 모델은 무겁고 별도 모듈. 같은 백본 미래 잠재 헤드는 감시 용도 선례 없음 |
| D. 고유 감각·전류 | 그리퍼 폭·전류, 관절 토크(전류) | TA-VLA, 운동량 관측기(기초), Show-Harness 폭 규칙 | 코드, 지연 ~0, 결정적. 세계 쪽 술어는 못 잼 |
| E. 불확실성 | 토큰 엔트로피, 행동 샘플 분산, 앙상블, 보정 | FIPER(ACE), SAFE 기준선, CheckVLA 기준선, Zollo & Zemel | **측정이 아님**: "결과가 참인가"가 아니라 "모델이 헷갈리나". 이미 `C_flip`·J5가 이 몫 |
| F. 느린 상위 VLM 판정 | API VLM에 프레임 보내 성공/실패 | GR 1.5 오케스트레이터, Critic in the Loop | Astra 첫 토큰 ~3 s(low) → 결정 스텝(0.33 s) 확인엔 늦음 |

### 2.2 근거 표 (신뢰도: HIGH / MED / LOW; 추천은 HIGH·MED만)

| 이름 (arXiv) | 계열 | 원문 핵심 (조건 포함) | 학회·날짜 | 인용 | GitHub★ | 신뢰도 |
|---|---|---|---|---|---|---|
| **SAFE** (2506.09937) | B/E | VLA 마지막 층 특징 → MLP/LSTM 실패 점수, functional CP 시간 가변 문턱. 원문: "VLAs have sufficient high-level knowledge about task success and failure, which is generic across different tasks". 성공+실패 롤아웃 필요(작업 7–10개, 약 200–450편). 추가 지연 "<1ms". **토큰 불확실성 기준선(최대 확률 53.83, 평균 엔트로피 50.03 ROC-AUC, 미학습 과제 LIBERO) ≈ 우연 수준** 대 SAFE 평균 78 (요약 도구 경유) | NeurIPS 2025, 2025-06 | 83 | vla-safe/SAFE 109 | HIGH |
| **FIPER** (2510.09459) | C/E | 관측 임베딩 OOD(RND) + 행동 청크 엔트로피(ACE), **성공 롤아웃만**(시뮬 M=50, 실물 M=10)으로 conformal, 두 점수 AND. TWA 0.65, 정확도 0.78 (요약 도구 경유). 부록 C.4.2 "CP 임계는 예측보다 탐지 쪽"(M4 문서에서 확인) | NeurIPS 2025, 2025-10 | 39 | learnsyslab/fiper 55 | HIGH |
| **Self-Improving Embodied Foundation Models** (2509.15155) | B | **정책과 같은 모델(PaLI-3B)**이 steps-to-go를 토큰으로 예측 → `success(o,g):=1[d(o,g)≤s]`, 보상 `d(o_t,g) − d(o_{t+1},g)`. 원문: 이 성공 판정은 "very robust even in low data regimes, and significantly more reliable than explicitly including a success detection binary classification objective in Stage 1". 판정기 정확도 수치는 없음. Google DeepMind | NeurIPS 2025, 2025-09 | 33 | 없음 | HIGH |
| **Gemini Robotics 1.5** (2510.03342) | B/F | ER 1.5가 다중 시점·단일 시점 성공 판정(실시간 5 Hz 조건과 오프라인), 오케스트레이터가 "performs success detection to decide when to switch to the next step". 원문 경고: "stale success predictions quickly become irrelevant during dynamic robot interactions". 수치는 그림 13에만(본문 수치 없음) | 기술 보고서(GDM), 2025-10 | 89 | — | HIGH(출처), 수치 미확인 |
| **π\*0.6 RECAP** (2511.14759) | B | 가치 함수 = 별도 작은 VLM(670M, Gemma 3), 201 구간 분포로 "성공까지 남은 스텝", 실패는 큰 음수. **학습 때만** 사용. 원문: "the VF correctly identifies mistakes in the episode, as well as the speed of progress"(그림 4). 정량 수치 없음 | PI 기술 보고서, 2025-11 | 320 | — | HIGH(출처), 판정 수치 없음 |
| **TA-VLA** (2509.07962) | D | 원문: "The joint torques are derived from the robot's motors based on the electrical currents supplied to them … without the need for external force sensors"(Cobot Magic ALOHA). 토크를 보조 출력으로 예측하면 성능 향상. 원문: "no contact, failed insertion, and successful plug-in—can be clearly distinguished by the joint torque profiles". 접촉 과제 π0 5/20 → 18/20(버튼) 등(요약 도구 경유) | CoRL 2025, 2025-09 | 39 | ZZongzheng0918/TA-VLA 121 | MED-HIGH |
| **V-JEPA 2 / 2-AC** (2506.09985) | C | Droid 무라벨 62 h로 행동 조건 예측기, 에너지 = 예측 잠재와 목표 잠재의 L1. 계획 "16 seconds per action"(Cosmos 4분). 영점 pick-and-place 72.5 % | Meta, 2025-06 | 730 | facebookresearch/vjepa2 4,679 | HIGH |
| **FLARE** (2505.15659) | C | 확산 정책 특징을 **미래 관측 임베딩**(SigLIP-2 + Q-former 32 토큰)에 cosine 정렬 — 학습 목적이지 감시기가 아님. 절제 43.9 → 55.0 % (NVIDIA) | arXiv, 2025-05 | 95 | 공식 저장소 확인 못 함 | MED |
| **VLAC** (2509.15937) | B | InternVL 2B/8B, 두 관측 + 지시 → 진행 증분 + done. 데이터 4,000 h 이상. 관측 처리 0.1 s 안. VOC-F1: RT1 0.95, Bridge 0.98, Droid 0.79, **RoboFAC-fail 0.19** (실패 궤적에서 약함) | arXiv, 2025-09 (Shanghai AI Lab) | 82 | InternRobotics/VLAC 331 | MED |
| **Robo-Dopamine** (2512.23703) | B | 과정 보상 모델 GRM, 3,400 h 이상, 다시점 융합. 150 롤아웃(약 1 h)으로 95 % | arXiv, 2025-12 | 49 | FlagOpen/Robo-Dopamine 668 | MED |
| **RoboMonkey** (2506.17811) | B(실행 전) | 행동 후보 샘플 + 7B VLM 검증기로 선택, "16 candidate actions in 650 ms". **실행 전 선택**이지 실행 뒤 측정이 아님 | CoRL 2025, 2025-06 | 52 | robomonkey-vla/RoboMonkey 45 | MED(범위 밖 용도) |
| **CheckVLA** (2607.26789) | C | 동결 V-JEPA 2-AC 인코더 + 확정 행동 조건 특징 예측 → 관측과 cosine 불일치 → 시간 위험 헤드 → functional CP. 감시기 p95 16.4 ms. 적시 재현율(FWER 5 %): **MC 행동 엔트로피 58.7, 동결 정책 특징 프로브 68.6, 관측만 세계 예측 48.6, 전체 77.9**. Table 5: "확신하며 틀림"(정책 불확실성 낮음·세계 모델 위험 높음) 상태가 25 %, 실패율 48 %. 실패 분석: "가림·접촉 중 세계 모델 모호" 18.6 % (D10b 정독) | arXiv, 2026-07 | 2 | 코드 확인 못 함 | MED-LOW (정독했으나 반응 적음) |
| Foresight (2606.23085) | C | V-JEPA 2-AC 예측 잠재 vs 관측 잠재 → 인과 Transformer 실패 점수 → FCP. BEHAVIOR-1K 균형 정확도 0.78 대 SAFE-LSTM 0.64. 저자 한계: "computational cost and latency of pretrained world models" | arXiv, 2026-06 (Michigan·Princeton·UVA) | 8 | 확인 못 함 | MED-LOW |
| Confidence Calibration in VLAs (2507.17383) | E | VLA 신뢰도 보정 첫 체계 연구, 프롬프트 앙상블·행동별 Platt | arXiv, 2025-07 (Zollo·Zemel) | 11 | — | LOW-MED |
| Rewind-IL / TIDE (2604.16683) | E | 겹친 청크 불일치 + split CP (M4 `C_flip` 근거) | arXiv 2026-04; S2는 RA-L 표기, arXiv 페이지엔 없음 → 미확인 | 7 | — | LOW-MED |
| RoVer (2510.10975) | B | 0.2B 과정 보상 모델로 후보 선택, 5.7–6.2 ms/행동 | arXiv | 18 | 코드 미공개 | LOW |
| VLA-Scope (2609.21246) / FPC-VLA (2509.04018) / ReconVLA (2604.16677) / Large Reward Models (2603.16065) | B/E | 각각 OOD+진행 특징 로지스틱 AUC 0.85, VLM 감독기, 불확실성 유도, 보상 VLM | arXiv | 0 / 25 / 4 / 11 | — | LOW (추천 안 씀) |
| GVL (2411.04549) | B | 섞은 프레임 진행 추정 | ICLR 2025 — **기간 밖, 기초 문헌** | 118 | — | 기초 |
| SuccessVQA (2303.07280) | B | 성공 판정을 VQA로 | CoLLAs 2023 — **기간 밖, 기초 문헌** | 167 | — | 기초 |
| AHA (2410.00371) | B | 실패 탐지·설명 VLM | ICLR 2025 — **기간 밖, 기초 문헌** | 180 | — | 기초 |
| Sentinel/STAC (2410.04640), FAIL-Detect (2503.08558), FOREWARN (2502.01828), DINO-WM (2411.04983) | C/E | 행동 일관성 감시, 실패 데이터 없는 탐지, 세계 모델 잠재 + VLM 조향, DINO 잠재 세계 모델 | CoRL 2024 / RSS 2025 / RSS 2025 / ICML 2025 — **기간 밖, 기초 문헌**(2025-03-23 이전) | 80 / 73 / 70 / 369 | — / CXU-TRI/FAIL-Detect 57 / — / gaoyuezhou/dino_wm 584 | 기초 |
| 운동량 관측기 기반 무센서 충돌·접촉 검출 (De Luca 2003 계열, Haddadin 외 2017 T-RO 서베이) | D | 관절 토크 잔차로 접촉 검출 | **기간 밖, 기초 문헌**(이번 라운드 원문 재확인 안 함) | — | — | 기초 |

### 2.3 표에서 읽은 것 (원문 → 우리 해석 분리)

1. **[원문] 학습된 판정은 VLA 내부에 이미 있다.** SAFE(HIGH): VLA 특징이 과제를 넘어 성공/실패를 가른다. Self-Improving EFM(HIGH): 정책과 **같은 모델**이 steps-to-go를 예측하면 그것이 성공 판정기가 되고, 이진 성공 분류 목적보다 "significantly more reliable". → **[우리]** 세계 쪽 측정을 같은 백본 헤드로 두는 것은 선례가 있는 방향이다. 다만 두 선례 모두 **과제 성공**(에피소드·하위 목표 수준)이고, "결정 스텝마다 `expected_after` 술어 참거짓"을 측정으로 쓴 직접 선례는 **찾지 못했다** → 우리 접목([가정]), 시험으로 확인.
2. **[원문] 토큰 불확실성은 성공/실패를 거의 못 가른다.** SAFE의 최대 확률·평균 엔트로피 기준선이 ROC-AUC 50–55(요약 경유), CheckVLA에서 MC 행동 엔트로피 적시 재현율 58.7 대 전체 77.9, "확신하며 틀림" 상태가 25 %·실패율 48 %. → **[우리]** 결정 토큰 확률·엔트로피는 M4 (a) 합의·J5 게이트·`C_flip`에만 쓰고 (b)의 "측정"으로 쓰지 않는다.
3. **[원문] 예측 잠재 대 관측 잠재는 강하지만 무겁고 외부 모듈이다.** CheckVLA 적시 재현율 77.9(정책 특징 프로브 68.6보다 +9.3), 감시기 p95 16.4 ms(단 별도 V-JEPA 2-AC 인코더 + 88.4M, A100). Foresight도 V-JEPA 2-AC이고 저자가 지연을 한계로 적음. V-JEPA 2-AC 계획은 행동당 16 s. **가림·접촉 중 모호**가 잔여 실패의 18.6 %(CheckVLA). → **[우리]** 외부 세계 모델을 붙이면 §58 융합 원칙과 부딪히고, 우리 핵심 구간(접촉·가림: 손목 근거리)에서 약하다. FLARE식 **같은 백본 미래 잠재 헤드**는 학습 목적으로만 선례가 있고 감시기로 쓴 선례가 없다 → 2순위(절제).
4. **[원문] 진행 추정 모델은 실패 궤적에서 약할 수 있다.** VLAC VOC-F1 RoboFAC-fail 0.19(성공 0.73). GR 1.5: 느린 판정은 "stale". → **[우리]** 범용 진행 모델·Astra를 결정 스텝 측정에 쓰지 않는다. Astra는 단계 경계 확인(§45 T_sub)에만. [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
5. **[원문] 전류 기반 관절 토크로 접촉 결과가 갈린다.** TA-VLA(CoRL 2025): 모터 전류에서 토크, 삽입 실패/성공/무접촉이 토크 프로파일로 구분. → **[우리]** AI Worker의 `effort`(Present Current)·그리퍼 전류(§39)로 로봇 쪽 술어를 코드로 잴 수 있다. 우리 R1에서도 고유 감각 `gripper_open` 일치 1.000, `holding`은 `unknown`을 뺀 경우 0.999(단 이 `holding`은 기하 조건도 씀 — 고유 감각만 판은 시험 필요).

---

## 3. 1·2순위 설계

### 3.0 공통: 술어를 측정 출처로 나눈다

| `expected_after` 술어 | 측정원 | 등급 | 비고 |
|---|---|---|---|
| `gripper_open` | 그리퍼 폭 | T1 | 코드 |
| `holding(x)` / 빈 집기 | 폭 ∈ (w_empty+δ, w_open) **그리고** 그리퍼 전류 ≥ θ_I (히스테리시스) / 폭 ≤ w_empty+δ | T1(로봇 쪽 판) | Show-Harness의 빈 집기 폭 규칙(≤ 5 mm)과 같은 모양(M4 문서 §2.2) |
| 쥔 채 `lifted(x)` | `holding` 참 + TCP z 상승(FK) | T1 | 물체 높이가 아니라 "쥔 상태 + 손 높이" |
| 접촉에서 멈춤(`contact_stall`) | 팔 관절 `effort` − 명목 `effort(ref(t))` 잔차 + 추종 잔차 | T1 후보(보정 뒤) | TA-VLA 근거, 문턱은 성공 롤아웃 conformal |
| `on(a,b)`·`in_contact(a,b)`·`near`·`above`·물체 `lifted`(쥐지 않은) | **확인 헤드** | T2 | 학습 + 보정, 소프트만 |
| `unknown` | 확인 헤드의 conformal 집합이 {참, 거짓} 둘 다 | — | 정본 §11.2대로 위반으로 세지 않음, 1.0 s 지속 시 `C_pred` |

### 3.1 1순위 설계 A: 같은 백본 확인 헤드(세계 쪽) + 고유 감각 코드(로봇 쪽)

**구조**
- R4의 보조 기하 헤드(술어 7개 BCE: gripper_open, holding, lifted, upright, near, contact, on)를 **"확인 헤드"**로 승격한다. 입력은 이미 매 호출 도는 **문맥 순전파**(system + 머리 672×376 + 활성 손목 424×240 + IMG 상태, §59)의 은닉 상태. 결정 스텝 k의 `expected_after`는 **t_state ≥ 스텝 k 끝**인 첫 호출의 헤드 출력으로 판정한다(3 Hz 겹침 호출이므로 대개 0.33 s 안에 온다).
- 헤드 목표 추가: 대상 물체 쌍 술어(`on(o3,o5)`, `in_contact(o3,o5)` 등)를 **물체 역할 슬롯(target/place_ref)** 기준으로 — 물체 id를 고정 순서로 두면 과제가 바뀔 때 깨진다. 선택: Self-Improving EFM을 따라 **"phase 끝까지 남은 스텝" 구간 예측**을 함께 둔다(이진보다 신뢰할 만하다는 원문, M7 `C_stag`의 진행 대리값도 겸함).
- 고유 감각 입력: 그리퍼 폭·전류, 관절 `effort` 요약을 IMG 상태 텍스트 한 줄로(또는 expert 조건과 같은 23차원을 헤드에 연결). 확인 헤드가 로봇 쪽 사실을 이미지에서 다시 추정하지 않게.
- 라벨: 풀 `npz`의 `obj_pose`(특권) → `harvest/predicates.py` → 술어 참거짓(`aux_labels.py`가 이미 만든다). 비용 0.
- 보정: CAL(또는 DEV-cal) 분할에서 **술어별 온도** → **split conformal**(α = 0.1 시작): 집합 {거짓}만이면 "위반", {참}만이면 "일치", 둘 다면 `unknown`. 정본 §52 보정 절차와 같은 틀(질문별 온도 → J5 conformal)을 술어 단위로.

**M4 규칙에 꽂는 곳**(정본 §3·§4 형식 유지)
- (b)(1) `ref(t)` 잔차: 그대로(고유 감각).
- (b)(2) `holds(expected_after, measured)`: 술어마다 위 표의 측정원으로. 결과 → 범주
  - T1 로봇 쪽 술어가 거짓 확정 → **CONTRADICT → M7 하드(H4)**.
  - T2 세계 쪽 술어가 conformal {거짓} → **DEVIATE**(M7 `C_m4`). 같은 술어가 연속 2회 {거짓}이면 CONTRADICT-soft(여전히 `C_m4`, 하드 아님 — 정본 §11.2 "T2는 하드 금지" 유지).
  - `unknown` → 판정 보류, `premise_epoch` 변경 없음, 1.0 s 지속 시 `C_pred`.
- 합의 원장: DEVIATE/CONTRADICT의 epoch 교체·미확정 표 폐기 규칙은 그대로(M4 §4.2).

**M7 critic에 꽂는 곳**
- 하드: H1(T1 불변 — 예: 운반 중 `holding` 로봇 쪽 판이 연속 2틱 거짓 = 놓침), H2, H3(T1 entry), H4(T1 CONTRADICT), H5, H6 — **전부 고유 감각·코드·시계**. 학습 헤드는 하드에 들어가지 않는다.
- 소프트: 새 채널 **`C_vq`**(확인 헤드: 현재 단계 `invariants_k`·`exit_k`의 T2 술어가 conformal {거짓}으로 0.5 s 지속) — 기존 `C_pred`의 T2 경로를 이 채널이 대체. `C_stag`의 진행 대리값 = 확인 헤드의 "남은 스텝" 구간. `C_m4`·`C_flip`·`C_dead`·`C_assume` 유지. **출처 독립 규칙**: `C_vq`·`C_m4`(T2 경로)·`C_stag`(헤드 진행)는 모두 같은 백본 출처 → E-M7 D4f와 같은 "같은 출처는 1표" 기본값. 그래서 소프트 AND의 두 표가 **서로 다른 출처**(백본 대 고유 감각/시계/Astra 계약)에서 오게 된다 — CheckVLA Table 5의 "확신하며 틀림"(같은 모델 신호끼리는 함께 놓침)에 대한 방어.
- 문턱: 정본 §31 그대로 성공 에피소드 conformal(δ_c = 0.05 시작).

**지연**: 헤드는 문맥 순전파 은닉 상태에 붙은 작은 MLP(3.4M, R4) → 추가 시퀀스 0, 추가 지연 ~ms. 고유 감각은 코드. **3 Hz 예산(p95 0.28 s 설계값, §59) 불변.** 명시 인식(R1 p95 379 ms) 제거로 오히려 여유가 생긴다.

**학습 데이터**: 풀(120편 × 0.33 s 연속 스냅샷, 머리+우손목 이미지, 특권 상태) + labeler 분기 롤아웃(실패 결과 포함, 단 현재 프레임 미기록 → 카메라 켜고 재생성 필요) + DEV 실패 주입(§4). 본 실험(§56)의 DR·다과제 데이터로 확장.

**실패 모드와 대책**
| 위험 | 대책 |
|---|---|
| 같은 백본이라 결정 오류와 확인 오류가 상관(자기 확인 맹점) | 입력이 다르다(실행 **뒤** 관측), 목표가 특권 참값, 고유 감각 채널이 독립 두 번째 표. §4 지표 "결정 오류 스텝에서 확인 헤드가 '일치'라 한 비율"로 직접 잰다 |
| 가림(그리퍼가 머그를 가림: R1에서 머리 approach 오차 48 mm, 손목 근거리 누락) | 머리+활성 손목 두 장, conformal `unknown`으로 흡수, 로봇 쪽 술어는 고유 감각 |
| 시뮬→실물 전이(이미지 도메인 차) | 실물 CAL 에피소드로 온도·conformal 재보정(FIPER: 실물 성공 롤아웃 10개로 보정). 교환 가능성 깨짐은 ACI 선택지(M4 §6) |
| 헤드가 `expected_after`를 "예상"대로 믿는 쏠림 | 헤드 입력에 결정 문자열·`expected_after`를 넣지 않는다(R4가 이미 결정 문자열을 문맥에서 뺐다 — 같은 원칙) |
| 경계 술어(near 5 cm 띠) | 데드밴드·히스테리시스 공유, 경계 스냅샷은 `ambiguous`로 따로 보고 |

### 3.2 2순위 설계 B: 예측 잠재 대 관측 잠재 일치 (절제·보조 소프트 채널)

- **[원문]** CheckVLA·Foresight: 동결 V-JEPA 2-AC로 "확정 행동 조건 예측 특징 vs 관측 특징"의 cosine 불일치 → 시간 위험 헤드 → FCP. FLARE: 정책 특징을 미래 관측 임베딩에 cosine 정렬(학습 목적).
- **[우리 접목안]** 외부 세계 모델 대신 **같은 백본에 FLARE식 미래 잠재 토큰**을 둔다: 문맥 은닉 상태 + 확정 행동 청크 → 다음 결정 시각 관측의 **풀링된 비전 타워 임베딩**(동결 비전 타워라 목표가 고정) 예측, 불일치 d = 1 − cos, phase별 성공 통계로 표준화(CheckVLA 식 5 모양), 짧은 창 집계 + functional CP. 학습은 성공 롤아웃만(FIPER처럼 실패 데이터 불필요).
- M4: (b)에 넣지 않는다(술어 의미가 없어 epoch 교체 사유를 설명 못 함). M7: 소프트 채널 `C_lat` 후보, **E-M7 조건 D-LAT**로 켬/끔 절제만.
- 왜 2순위인가: (1) 감시기로 쓴 선례가 모두 외부 세계 모델(무겁고 §58과 충돌), (2) 같은 백본 판은 선례 없음, (3) 접촉·가림 모호(CheckVLA 잔여 18.6 %)가 우리 핵심 구간, (4) 무해 편차(카메라 흔들림·가림)에 민감 — CheckVLA도 무해 음성 없이 학습하면 무해 첫 개입 14.8 %.
- 대안 비교 조건(오프라인만): 외부 V-JEPA 2-AC 판(CheckVLA 충실판) — 상한 참고용. 실물 서버 VRAM·지연 측정 전에는 런타임 후보 아님.

### 3.3 쓰지 않거나 역할을 좁히는 것
- **Astra 성공 판정**: 정본 §45 T_sub(단계 경계)에서 "이 단계가 끝났나 + 다음 계약이 맞나"를 비동기로 묻는 데만. M4 (b)·하드 채널에 쓰지 않는다(첫 토큰 ~3 s, GR 1.5 "stale" 경고). 결과가 확인 헤드와 어긋나면 `C_assume`(계약 쪽) 경로로. [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
- **범용 보상·진행 모델(VLAC, Robo-Dopamine)**: 별도 2–8B 모델 = 융합 원칙 위배 + 실패 궤적 약함(VLAC fail 0.19). 교사 라벨 교차 확인용으로만 가능.
- **토큰 엔트로피·결정 확률**: (b)의 측정 아님(§2.3-2). 기존 `C_flip`·J5 역할 유지.
- **명시적 인식(R1)**: 모듈형 기준선 행과 §4 시험의 V0 대조로만.

---

## 4. 사전 등록 오프라인 시험 E-M4b-meas (실행 전 고정할 초안)

### 4.1 데이터
- **POOL**(있음): 시드 2000–2119, 0.33 s 연속 스냅샷, 머리+우손목 JPEG, 특권 `obj_pose`·`obj_vel`, `joint_pos/vel/targets`, JSON `obs.raw.grip{w, effort}`. 분할 = pool.md의 fit/eval 60/60(섭동별 20/20). **학습은 fit 60만.**
- **R1-DEV**(있음): DEV 0–9 × P0–P2, 804 스냅샷, R1 파이프라인 추정 술어(`eval.jsonl`) → V0 기준선 칸 그대로.
- **FI-DEV**(새로 생성, DEV 시드 0–29만 — TEST 1000–1149·TEST-P5·CAL은 만들지도 열지도 않음, `check_seed` 그대로): 풀과 같은 결정적 재실행 경로(선행 실행 warmup, 비트 동일)에 주입. [정정 R7 15회차 D-1, 정본 §78·`pool_replay_debug.md:15`: 선행 실행 warmup으로는 비트 동일이 보장되지 않는다 — 고정 선행 실행은 이력 의존을 없애지 못하고, 풀 라벨 886행(29편)이 재실행과 비트 동일이 아니다. 비트 동일 재실행은 하드 리셋 빌드(e8e1864, 에피소드마다 PhysX 장면 재생성)에서만 성립한다]
  - 실패 주입 5종(시작 시각 기록): 빗나간 집기(닫기 직전 TCP 3 cm 어긋남), 미끄러짐(운반 중 그리퍼 5 mm 벌림 또는 마찰 감소), 쳐서 떨굼(운반 중 물체 충격), 놓기 빗나감(놓기 직전 트레이 6 cm 이동), 방해물(접근 경로에 물체 삽입).
  - 무해 편차 3종: 카메라 흔들림, 짧은 부분 가림, 작은 자가 교정 이동(CheckVLA Table S9·S15 근거).
  - 명목 30편. 합계 약 30 × (5 + 3 + 1) = 270편. 저장 필드 추가: **팔 관절 `applied_torque`**(지금 `ROBOT_ARRAYS`에 `joint_effort_target`만 있고 실제 토크는 그리퍼만 JSON에 있음), 그리퍼 `applied_torque`. 시뮬 전류 잡음 모델 [가정]은 R-noforce와 같은 것.
  - 분할: DEV 0–14 = 보정(온도·conformal·채널 문턱), DEV 15–29 = 평가.
- labeler 분기 롤아웃은 프레임이 없어 이번 시험에 쓰지 않는다(재생성 비용 대비 FI-DEV가 같은 역할).

### 4.2 조건
| 이름 | 측정원 | 학습 |
|---|---|---|
| V0 | R1 명시적 인식 → 코드 술어 | 없음(기준선) |
| V1z | Qwen3-VL-4B 영점, typed 확인 질문("Is the mug on the tray now? yes/no") 트라이 확률 | 없음 |
| **V1h**(1순위 주) | 확인 헤드(R4 보조 헤드 확장, 다음 관측) | POOL fit 60, 특권 라벨 |
| V1q | 같은 학습 데이터로 typed 확인 질문 SFT(단계 A 레시피) | POOL fit 60 |
| P | 고유 감각 코드 규칙(§3.0 표) | 없음, 문턱만 DEV-cal |
| **V1h+P**(1순위 전체) | 술어별 출처 분할 | 위 둘 |
| L | FLARE식 같은 백본 미래 잠재 불일치 | POOL fit 명목만 |
| (선택) A | Astra 단계 경계 성공 판정, 평가 분할 100사건 | 없음 — **유료 호출이므로 사용자 승인 뒤에만** |
| 최빈 | 술어별 최빈 답 | — |

### 4.3 지표
- **M4 (b)**: 스텝 끝 스냅샷(평가 분할)에서 술어별 균형 정확도·AUROC, 온도 뒤 ECE, conformal(α = 0.1) 경험 커버리지·원소 하나 비율, "{거짓} 판정 정밀도"(CONTRADICT/DEVIATE의 오경보), 단계(near/contact 대 먼 구간)·카메라 조건별. 로봇 쪽 술어는 P의 정확도를 따로.
- **자기 확인 맹점**: labels_v2 정답과 다른 결정을 한 스텝(단계 A 모델 재생)에서 V1h가 "일치"라 한 비율 대 P.
- **M7 critic**(FI-DEV 평가 분할, 오프라인 재생): 에피소드 FWER(명목 + 무해 편차) 5 %에서 고정 창 재현율(τ = 2 s, 정본 §23 판정 지표), 탐지 지연 중앙값, 주입 종류·단계별, 무해 편차 첫 개입률. 채널 구성은 M7 D5(AND, 같은 출처 1표).
- **지연**: 문맥 순전파 + 헤드 p95 증가분(H200, 실물 서버 RTX PRO 6000 측정은 뒤에).

### 4.4 판정 (실행 전 고정)
1. **PC1(세계 쪽 측정)**: V1h의 세계 쪽 술어 {`on/in_contact(target, place_ref)`, 쥐지 않은 `lifted`, `near`, `above`} 평균 균형 정확도 ≥ 0.90 **그리고** V0 + 0.15 이상 **그리고** 최빈 + 0.15 이상(부트스트랩 95 % 하한 기준), 온도 뒤 ECE ≤ 0.05, conformal 경험 커버리지 ∈ [0.88, 0.95]. 통과하면 V1h를 (b)(2) 세계 쪽 측정으로 채택. V1q가 V1h보다 +0.03 이상이고 지연 증가 ≤ 50 ms면 V1q로.
2. **PC2(로봇 쪽 T1)**: P의 `gripper_open`·`holding`/빈 집기·쥔 채 `lifted` 균형 정확도 ≥ 0.97 이고 명목 에피소드 FWER ≤ 1 %면 T1(하드 가능)로 등록. 미달 술어는 T2.
3. **PC3(critic)**: V1h+P가 FWER 5 %에서 고정 창 재현율 ≥ 0.80이고 V1h 단독·P 단독보다 각각 +0.05 이상이면 두 채널 구성 채택. 아니면 더 나은 단독 + 나머지는 기록만.
4. **PC4(지연)**: V1h 추가 p95 ≤ 20 ms. 넘으면 헤드를 결정 시퀀스 대신 lead 시퀀스에만.
5. **PC5(L)**: V1h+P에 L을 더했을 때 같은 FWER에서 재현율 +3 %p 이상이면 `C_lat`을 [결정 필요]로 올린다. 아니면 절제 결과로만 보고(M7 판정 2와 같은 규칙).
6. **PC6(실패 시 대체)**: PC1 미달이면 (b)(2) 세계 쪽 술어는 `unknown`으로 두고(로봇 쪽 P만 판정), 세계 쪽 확인은 Astra T_sub로 옮긴 판을 E-M4 비교 조건으로 올리고 논문 한계로 적는다. 결과를 보고 판정을 바꾸지 않는다. [→ 정본 §82(2026-09-25, user-log 74·76): 5 s 하트비트·단계 경계 확인·Astra 성공 판정은 작은 모델·코드로 강등, 주기 호출은 J5 저빈도 진행 감사로 대체 — 이 줄은 §82 이전 설계]
7. 통계: 평가 시드 15–29 × P0–P2(POOL 평가 60편은 V1 계열 술어 정확도 보조), 에피소드 단위 짝 부트스트랩 95 %. 사후 변경은 시각과 함께 결과 문서에 적는다(R1 §3.0 방식).

---

## 5. 정본·M4·M7·논문에 바뀔 것 (제안, 메인 세션 반영)

**정본(새 절 §61 제안)**
- §3 "예상 상태는 한 곳에서"에 줄 추가: "(b)(2)의 측정 = 술어 출처 표(로봇 쪽 = 고유 감각 T1, 세계 쪽 = 같은 백본 확인 헤드 T2, 집합이 둘이면 `unknown`)". `ref(t)` 잔차는 변경 없음.
- §11.2 등급: **T1 = 고유 감각·시계·오류 코드만**(융합 런타임에서 코드 기하 T1은 사라짐 — 시뮬 특권 상태는 런타임에 없다). 학습 헤드는 항상 T2.
- §58: "보조 기하 헤드" → "확인 헤드(보조 손실 + 런타임 측정)"로 역할 확장. M1 명시 인식은 기준선 행.
- §7 설정 표: 확인 헤드 conformal α(0.1 시작), 그리퍼 전류 문턱 θ_I·빈 집기 폭 w_empty+δ, 관절 effort 잔차 문턱(성공 롤아웃 conformal), `C_vq` 지속 0.5 s.
- 실험 순서(§8): E-M4b-meas는 오프라인이라 E-M7과 병행, **E-M4 폐루프 전에** 끝낸다(PC 결과가 (b) 구현을 정함).

**M4**: §0·§4.2 `on_step_executed`의 `pred = holds(expected_after, measured)`를 `pred = measure(expected_after, source_table)`로(술어별 출처·등급·`unknown`). §2.2 표에 SAFE·Self-Improving EFM·CheckVLA·TA-VLA 줄 추가. "(b)의 최고 조합 = 모두 학습 없음" 문장은 "로봇 쪽은 학습 없음, 세계 쪽은 학습 + 보정"으로 정정.

**M7**: 소프트 채널 `C_vq` 신설(T2 `C_pred` 경로 흡수), `C_stag` 진행 대리값 = 확인 헤드 남은 스텝, 하드 층 H1·H3·H4는 고유 감각 T1만, 출처 독립 1표 규칙을 `C_vq`·`C_m4`(T2)·`C_stag`(헤드)에 확장. E-M7 조건 추가: **D-VQ**(확인 헤드), **D-P**(고유 감각만), **D-LAT**(잠재 일치), **D-V0**(명시 인식 기준선). 데이터는 FI-DEV와 공유.

**M6/R**: 팔 `applied_torque` 기록을 풀·FI-DEV 생성기에 추가(현재 그리퍼만). R-noforce 절제와 같은 전류 잡음 모델.

**논문**
- 방법: "M4 (b)는 결정 스텝 뒤 `expected_after`를 (1) 고유 감각 결정 규칙과 (2) 같은 VLA의 보정된 확인 헤드로 잰다. 둘은 출처가 달라 M7 AND 결합의 독립 표가 된다." 새로움 문장(§58 "융합 모델의 결정 토큰 확률을 시간차 호출로 확정")에 "**같은 모델의 실행 뒤 자기 확인이 합의 원장의 전제 무효화를 구동한다**"를 덧붙일 수 있다 — 단 직접 선례 부재는 [가정]이며 PC1 통과 뒤에만 주장.
- 관련 연구 단락: 성공 판정(SAFE, Self-Improving EFM, GR 1.5, SuccessVQA 기초), 세계 모델 감시(CheckVLA, Foresight, V-JEPA 2), 토크(TA-VLA), 불확실성의 한계(SAFE 기준선, CheckVLA Table 4·5).
- 한계: 시뮬 특권 라벨 학습 → 실물 재보정 필요, conformal 보장은 명목 성공의 첫 개입만(CheckVLA·FIPER 원문과 같은 한계), 같은 모델 자기 확인 상관은 시험 지표로만 통제.

---

## 6. 확인 못 한 것
- 기간 안(2025-03-23 이후) **그리퍼 전류·관절 전류만으로 파지/접촉 성공을 판정한 로봇 논문**은 TA-VLA 외에 원문으로 확인하지 못했다(검색 예산 소진, S2 키워드 검색은 산업 모터 고장 논문만 반환). 운동량 관측기 계열은 기초 문헌으로 이름만 적었다.
- Gemini Robotics-ER 1.5 성공 판정 정확도 수치(그림 13만, 본문 수치 없음).
- SAFE·FIPER·TA-VLA·VLAC 표 수치는 WebFetch 요약 경유 — PDF 표 직접 대조 안 함.
- FLARE 공식 코드 저장소, GR00T N1.5의 FLARE 사용 여부(Isaac-GR00T README에 언급 없음 → 주장하지 않음), Rewind-IL의 RA-L 게재(S2 표기만).
- "결정 스텝마다 `expected_after` 술어 참거짓을 같은 VLA 헤드로 재서 실행 원장을 갱신"한 직접 선례 — 찾지 못함(부재 주장 아님).
- 확인 헤드의 실제 정확도·지연(§4 시험 전).

## 출처 (원문 확인 페이지)
- https://arxiv.org/abs/2506.09937 · https://vla-safe.github.io/ · https://github.com/vla-safe/SAFE
- https://arxiv.org/abs/2510.09459 · https://github.com/learnsyslab/fiper
- https://arxiv.org/abs/2509.15155
- https://arxiv.org/abs/2510.03342
- https://arxiv.org/abs/2511.14759
- https://arxiv.org/abs/2509.07962 · https://github.com/ZZongzheng0918/TA-VLA
- https://arxiv.org/abs/2506.09985 · https://github.com/facebookresearch/vjepa2
- https://arxiv.org/abs/2505.15659 · https://research.nvidia.com/labs/gear/flare
- https://arxiv.org/abs/2509.15937 · https://github.com/InternRobotics/VLAC
- https://arxiv.org/abs/2512.23703 · https://github.com/FlagOpen/Robo-Dopamine · https://arxiv.org/abs/2608.15680
- https://arxiv.org/abs/2506.17811 · https://robomonkey-vla.github.io/ · https://github.com/robomonkey-vla/RoboMonkey
- https://arxiv.org/abs/2607.26789 (D10b 정독) · https://arxiv.org/abs/2606.23085 · https://arxiv.org/abs/2604.16683
- https://arxiv.org/abs/2507.17383 · https://arxiv.org/abs/2510.10975 · https://arxiv.org/abs/2609.21246 · https://arxiv.org/abs/2603.16065
- Semantic Scholar Graph API(인용 수), GitHub REST API(스타)
