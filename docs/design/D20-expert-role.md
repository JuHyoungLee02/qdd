# D20 action expert의 역할: 스크립트 스킬 위 구간 제한 잔차 (user-log 35·36)

저장 2026-09-24 07:16 UTC. 조사 에이전트 보고 전문(신뢰도 기준 user-log 14 적용). 메인 원문 재확인(D:/tools/audit_d20): ResFiT "from 14% to 64%" / Object-Centric Residual RL "42% to 76%"·"visual domain gap" / Policy Decorator "Bounded residual action is essential" / PLD "bounded within a range" / Steerable Policies "rather than moving left unconditionally" / CR-DAgger "64%" — 모두 일치.


작업 조건
- D:\qdd는 읽기만 했다. 받은 자료는 모두 `D:\tools\audit_d20\`에 있다(abs_*, hf_*, html_*/txt_*, gh_*, proj_*, iclr_pld.html, pmlr_robomonkey.html).
- 요청 사이는 2초 이상 띄웠다. 날짜는 abs의 [v1]으로 확인했다.
- ★ 수와 HF 업보트는 2026-09-24에 잰 값이다.
- 코디네이터 추가 제약을 반영했다(Jev = 방향 + 크기 구간 결정자, 사용자 원문 "Jev는 앞으로, 뒤로 좌우 몇 센티를 판단하는 역할임 알지?").
  - (라)는 제외했다.
  - (가)는 Jev가 정한 방향·구간 안에서만 움직이게 했다.
  - "Jev 명령 추종 실행기"를 (마)로 추가해 비교했다.

### 0. 결론
1. **주 역할 = (가′) 구간 제한 잔차 R** [제안].
   - S가 만든 명령 위에 작은 병진 잔차를 더한다. 잔차는 접근·접촉 근처에서만 켠다.
   - 잔차는 **코드 투영**으로 Jev가 고른 방향·크기 구간 안에 가둔다.
   - 입력은 M1 상태, 고유수용, 힘이다. 이미지는 넣지 않는다.
   - S는 그대로 기본 실행기로 남는다. R은 끄고 켤 수 있는 추가 부품이라 주 표 S와 공정성 규칙을 깨지 않는다. S와 S+R을 짝지어 비교하면 R의 기여만 따로 잴 수 있다.
2. **보조 역할 = (다) 그림자 예측기** [제안]. 익스퍼트를 실행하지 않고 옆에서만 돌려, 진행도·phase 끝 확률·OOD 점수를 M7 소프트 채널 후보로 넣는다. FIPER식 conformal 보정을 쓰고 E-M7 절제로만 평가한다.
   - M4 (b)에는 넣지 않는다. S는 자기 `ref(t)`를 정확히 알고 있고, §33에 따라 `expected_after`는 코드로 남는다.
3. **(나) 학습 복구 실행기는 단독 역할로 채택하지 않는다.**
   - "학습 복구가 잘 설계된 스크립트 재시도를 이긴다"는 강한 근거가 없다(§2).
   - L1·L2의 "무엇으로 복구할지"는 Jev·Astra·M9 코드 목록이 정하는 결정이다. 학습 모델이 이를 정하면 역할이 겹친다.
   - 대신 복구 동작(`resume_ckpt_k` 재접근 등)을 실행할 때도 R이 같은 제한 아래 켜지게 한다. 이렇게 하면 (나)의 실행 부분은 (가′)에 흡수된다.
4. **(라) 후보 생성기는 제외한다.** Jev가 궤적 고르기 역할로 바뀐다(사용자 제약). RoboMonkey(CoRL 2025, 44★)는 기록만 한다.
5. **(마) 학습 추종 실행기**(Jev의 "앞 2 cm"를 학습 정책이 매끄럽게, 접촉을 인지하며 실행)는 사실상 §33의 B 실행기와 같다.
   - 주 표 S를 대체하므로 주 표에는 넣지 않는다. 비교는 기존 E-AE-2 B 표에서 한다.
   - 선행에 따르면 학습 추종기는 명령을 **맥락에 맞게 재해석**한다. Steerable Policies는 "when prompted to 'move left,' it servos left towards an object, rather than moving left unconditionally"라고 적었다.
   - 이 재해석은 접촉 인지라는 장점이면서 Jev의 크기 권위를 넘을 위험이다. 그래서 제한 없는 (마)보다 제한 잔차 (가′)가 사용자 제약에 맞다.

### 1. 근거와 신뢰도

| 출처 | v1 | 학회·소속 | ★ / HF | 등급 |
|---|---|---|---|---|
| ResFiT 2509.19301 | 2025-09-23 | abs에 학회 표기 없음. Amazon FAR·Stanford·CMU·UC Berkeley(Abbeel) | 155 / 20 | MED-HIGH |
| PLD 2511.00091 | 2025-10-30 | ICLR 2026(iclr.cc 포스터 페이지, abs에는 표기 없음). NVIDIA·CMU·UC Berkeley | 저장소 미확인 / HF 미등재 | HIGH |
| CR-DAgger 2506.16685 | 2025-06-20 | NeurIPS 2025(v5 본문 참고문헌 [56]에 "conference version"이 NeurIPS로 적힘). Stanford(Shuran Song) | 90 / 미등재 | HIGH |
| Object-Centric Residual RL 2606.18953 | 2026-06-17 | 학회 표기 없음. KAIST·MSRA Tokyo | – / 8 | MED |
| SAFE 2506.09937 | 2025-06-11 | NeurIPS 2025(comments). Toronto·TRI(저자 기준) | 109 / 10 | HIGH |
| FIPER 2510.09459 | 2025-10-10 | NeurIPS 2025(comments). TUM | 55 / 0 | HIGH |
| FailSafe 2510.01642 | 2025-10-02 | IROS 2026(comments). NTU·AI2·UW(Fox, Krishna) | – / 2 | MED |
| Steerable Policies 2602.13193 | 2026-02-13 | 학회 표기 없음. UC Berkeley·Stanford·Physical Intelligence(Levine) | 55 / 0 | MED |
| RoboMonkey 2506.17811 | 2025-06-21 | CoRL 2025(PMLR v305) | 44 / 1 | MED-HIGH, 역할 제외로 쓰지 않음 |
| FAR 2607.01111 | 2026-07-01 | CMU. 학회 표기 없음 | – / 미등재 | MED-LOW, 참고만 |
| RaC 2509.07953 | 2025-09-09 | CMU. CoRL 2025 Robot Data **워크숍** | – / 0 | MED-LOW, 참고만 |

기간 밖 기초 문헌:
- Policy Decorator 2412.13630: 2024-12-18, ICLR 2025(proceedings), 119★
- RecoveryChaining 2410.13979: 2024-10-17, Brown·MERL·CMU(Kroemer), abs에 학회 표기 없음
- RT-H 2403.01823: 2024-03-04, Google DeepMind, HF 8
- Residual Policy Learning 1812.06298: 2018-12-15
- Residual RL for Robot Control 1812.03201: 2018-12-07

### 2. 후보별 비교

#### (가) S 위의 잔차 보정
원문 근거:
- **베이스가 무엇이든 붙는다.**
  - RPL(기초): "For initial controllers, we consider both hand-designed policies and model-predictive controllers ... RPL consistently and substantially improves on the initial controllers"(MuJoCo 6과제).
  - Residual RL(기초): 기존 피드백 제어기 위에 RL 잔차를 더해 실물 블록 조립을 했다.
  - ResFiT: "leverages BC policies as black-box bases and learns lightweight per-step residual corrections".
  - 2025–26 수치는 모두 **BC·VLA 베이스** 위 결과다. 스크립트 베이스 위 결과는 기초 문헌뿐이다.
- **수치(조건 포함)**
  - ResFiT 실물(29-DoF 양팔 휴머노이드, ACT 베이스)
    - WoollyBallPnP: "boosted the performance of the base model from 14% to 64%". 134회, 약 15분.
    - PackageHandover: 23% → 64%. 343 에피소드, 약 76분, 시연 약 900개.
    - 모두 희소 이진 보상이다.
  - Object-Centric Residual RL: "improves the success rate from 42% to 76% zero-shot". 실물 FR3 5과제, 시뮬에서만 학습, 자세 잡음·dropout.
    - 관측 절제(과제 5개 × 20회 합계): 물체 자세 기반 76/100, 이미지 기반 47/100, 특권 교사 증류 46/100.
    - 원문: "the visual domain gap is the dominant sim-to-real barrier, which our object-centric observation sidesteps by design".
    - → [접목] R 입력을 M1 상태로 두는 근거다. sim→real 결과를 standard→random으로 옮기는 것은 [가정]이다.
  - CR-DAgger(v5 초록): 잔차가 "improving base policy success rates by 64% on four challenging tasks ... while outperforming both retraining-from-scratch and finetuning". 실물 접촉 과제, 사람 delta 교정.
    - 본문: "both the delta correction data and the force data are crucial" → R 입력에 힘을 넣는 근거다.
  - PLD: LIBERO "near-saturated 99%". 잔차 RL 전문가 데이터를 VLA로 증류한 결과다.
- **제한(bounded)의 근거**
  - Policy Decorator: "we do not want the resulting trajectory to deviate too much from the original trajectory because it usually leads to failure", "Bounded residual action is essential for effective residual policy learning".
    - α 범위: PushChair 0.1–0.5, StackCube 0.03–0.1이 "eventually converge to similar success rates".
  - PLD: "delta actions are usually scaled down and bounded within a range of [−ξ, ξ]". LIBERO ξ=0.5, SimplerEnv ξ=0.1. ξ가 너무 크면 초기 성능이 떨어진다.
  - **주의**: 원문의 제한은 학습 안정성을 위한 것이다. Jev 권위를 지키려고 쓰는 것은 우리 [접목]이다.
- **반대 증거(MED-LOW, 참고)**: ZPRL 2605.19919(Tsinghua 등, 51★, HF 0) — "residual corrections directly in action space ... often leads to noisy and poorly structured exploration".

우리 설계와의 관계:
- **더하는 것**: 접촉 근처의 세밀 정렬, 곧 M1 오차와 접촉 동역학 보정. Jev의 이산 구간보다 작은 오차를 메운다.
- **공정성**
  - R은 실행기 부품이므로 모든 결정 층 조건에 같게 붙인다.
  - 주 표는 S 그대로, S+R은 병기 표·절제로 둔다.
  - B3c가 연속 행동을 낸다면 같은 방향·구간 격자로 양자화해야 R을 똑같이 붙일 수 있다 → **[결정 필요]**. → **해소(정본 §35, Claude 결정)**: 같은 방향·크기 격자로 양자화해 R을 붙인다.
- **C2 영향**: 입력이 M1 상태뿐이면 외관 변화는 M1을 거쳐서만 R에 들어간다. 이 경로는 S와 같다. 그래서 RD(S+R) − RD(S)가 "학습 부품이 낙폭을 늘리는가"를 직접 잰다.
- **데이터**: skill GT 원칙을 유지한다.
  - 라벨 = 특권 시뮬 상태로 돌린 S 행동 − M1 추정 상태로 돌린 S 행동, 투영 후 [접목]
  - standard + D35 무작위화 + 섭동 + DAgger
  - 선택 2단계: T1 phase-exit 술어를 희소 보상으로 쓰는 off-policy 잔차 RL(ResFiT·PLD식) [제안]
- **지연**: 작은 MLP를 제어 주기마다 돌린다. 1 ms 미만 [가정, 측정 필요].

#### (나) 아래 층 복구 실행기
- RecoveryChaining(기초): 모델 기반 nominal 제어기 위에 학습한 복구 정책을 얹었다. 희소 보상, 시뮬 결과는 다음과 같다.

  | 과제 | Nom | Nom + RC |
  |---|---|---|
  | Pick-place | 70 | 90 |
  | Shelf | 51 | 83 |
  | Cluttered-shelf | 38 | 57 |

  - 실물 복구율은 박스 5/5, 겨자병 5/5, 캔 4/5다.
  - 비교 대상은 "복구 없음"이지 "스크립트 재시도"가 아니다.
- FAR(참고)
  - ManiSkill·RoboSuite 평균: 베이스 47.0, 단순 재시도 59.1, FAR 63.4.
  - 이득 대부분(+12.1%p)은 단순 재시도가 이미 얻었고, 학습 재시도의 추가분은 +4.3%p다.
- FailSafe: 모션 플래너가 만든 delta 복구 행동으로 VLM을 학습해 "up to 22.6%"를 얻었다(ManiSkill, OpenVLA 기준, OFT +8.0%, π0-FAST +4.0%).
  - 스크립트로 복구 라벨을 만드는 선례로는 유효하다.
- **판정**: 증거가 약하고 결정 역할(M9 목록·Jev `dp.critic_accept`)과 겹친다 → 단독 채택하지 않고 (가′)에 흡수한다.

#### (다) 예측기
- SAFE: "VLAs have sufficient high-level knowledge about task success and failure, which is generic across different tasks". **실행 중인** 정책의 내부 특징을 쓴다.
- FIPER: 성공 롤아웃만으로 conformal 보정한다. OOD(RND) 점수와 행동 청크 엔트로피가 둘 다 문턱을 넘을 때 경보한다.
- **빈칸**: 실행하지 않는 그림자 모델의 특징이 S 롤아웃의 실패를 예측한다는 원문은 없다 → [가정]. OOD(관측 기반) 쪽은 누가 실행하든 성립할 가능성이 크다 [가정].
- **공정성**: M7이 모든 결정 층 조건에서 공유되는 경우에만 교차 표에 넣고, 아니면 우리 시스템 내부 절제로만 쓴다 **[결정 필요]**. → **해소(정본 §35, Claude 결정)**: 교차 비교 표에는 넣지 않고 E-M7 조건 D-AE로 우리 시스템 내부 절제로만 평가.
- 지연은 B 머리 비용과 같다(청크당 30 ms 이하 목표, §33 [가정]).

#### (라)·(마)
- (라): 사용자 제약으로 제외.
- (마): 위 0-5 참조. 근거는 RT-H(기초, "language motions" 맥락 의존, "outperforming RT-2 by 15%")와 Steerable Policies("motions are the most effective" 단일 명령 방식 중). 둘 다 학습 추종기가 명령을 맥락에 맞게 재해석한다는 점을 보인다.

### 3. 주 역할 인터페이스 [제안]
- **입력**
  - `skill_id`·`phase_id`
  - Jev 확정값: 방향 d̂, 크기 구간 [m_lo, m_hi], 중심 m_c
  - S 명령 `a_S(t)`
  - M1 대상 자세와 불확실도
  - 관절·그리퍼 폭·힘/토크
  - 짧은 이력
  - 이미지 없음(R-state). R-crop은 절제 조건이다.
- **출력**: 병진 잔차 r = (r_∥, r_⊥). 회전은 기본으로 없다.
- **코드 투영(모델 밖, 강제)**
  - 누적 이동의 d̂ 성분 ∈ [m_lo, m_hi]. 방향 반전은 불가다.
  - |r_⊥| ≤ ε_⊥. ε_⊥는 standard+무작위화에서 잰 M1 위치 오차의 conformal 분위로 정한다 [가정].
  - near(목표 5 cm 이내) 또는 contact 술어가 참일 때만 켜고, 그 밖에서는 r = 0.
  - 마지막 클램프는 M5 L3 Ruckig이다.
- **기록**
  - `jev_choice`(권위값)
  - ∫r
  - 포화 비율
  - R on/off
- **M4 (b)**: `ref(t)` = 투영 뒤 실제 명령. `expected_after`는 바꾸지 않는다.
- **M7**: 새 채널 없음. 포화 지속은 기록만 한다.

### 4. 기여를 분리하는 실험 [제안, 문턱은 모두 가정]
- **E-R0 (오프라인)**: 라벨(특권 − 추정)이 제한을 넘는 비율. 넘는 비율이 크면 구간이 너무 거칠거나 M1 오차가 크다는 신호다.
- **E-R1 (주 실험)**
  - 조건: 결정 층을 우리 것(Jev+Astra)으로 고정. 실행기 {S, S+R-state, S+R-crop, S+R-무제한} × {standard, random}. 같은 layout·seed로 짝을 짓는다.
  - 지표: 성공률, 최종 정렬 오차(mm), 접촉 phase 성공률, Jev 권위 위반율(무제한 조건에서만 0이 아닐 수 있음), 포화율, jerk, FAIL·Astra 호출 수.
- **E-R2**: 오라클 결정 + {S, S+R}로 standard → random 낙폭을 잰다(E-AE-3 확장).
- **E-R3**: 결정 층 {LLM, 규칙, B3c(양자화)} × {S, S+R}의 상호작용 CI. 부호가 같을 때만 "실행기와 무관"이라고 쓴다.
- **E-R4**: 같은 seed에서 R 끔/켬 짝 비교, 그리고 phase별(접근만, 접촉만) 절제.
- **사전 판정**
  - S+R을 병기 표로 올리는 조건: standard 성공률 짝 차이의 95% CI 하한 > 0 **그리고** RD(S+R) − RD(S)의 95% CI 상한 ≤ +δ [가정].
  - 조건을 못 채우면 절제 결과로만 보고한다.
- **보조 역할 (다)**: E-M7에 조건 D-AE를 추가한다. 그림자 머리 채널 켬/끔에서 탐지 선행 시간, 오경보율(성공 에피소드 기준 δ_c), AUROC를 본다.

### 5. 제외·미사용
- 제외(신뢰도 낮음)
  - Atomic Motion Coordinate 2609.15012: 기업(DEEP Robotics), 학회 없음, HF 미등재, 공개 10일. "bounded spherical residual" 개념은 참고할 만하지만 쓰지 않는다.
  - RePO-VLA 2605.09410: 학회 없음, HF 미등재.
  - ZPRL 2605.19919: 반대 증거 참고만.
- 역할 제외: RoboMonkey.
- 받았지만 읽지 않음: RFS 2602.01789, 2602.10539, 2509.12562, Ctrl-World 2510.10125, π*0.6 2511.14759.

### 6. 확인하지 못한 것
- PLD 저장소 ★와 HF 등재 여부.
- SAFE 소속: 본문에서 확인하지 않고 저자 기준으로 적었다.
- RT-H(RSS 2024)와 RecoveryChaining의 학회 표기: abs에 없다.
- 스크립트 베이스 위 2025–26 잔차 결과: 찾지 못했다(기초 문헌뿐).
- 그림자 모드 예측기의 직접 선례: 찾지 못했다.
- R 지연 실측값: 없다.
