# 휴머노이드(Galaxea R1 Pro·Unitree G1) 조작 데이터 생성/계획 최근 연구 조사 — 테스트 가능한 추천 (2026-10-03)

작성: 조사 에이전트(SubagentHandback 경유). **구현·학습·GPU/파드 실행은 하지 않았다.** GitHub API(별 수·라이선스·최근 커밋), arXiv API(날짜), WebFetch(논문/README 원문), 하위 조사 에이전트 2개(프레임워크 조사, 모션플래닝·파지 조사)만 썼다.

## 문제 정의 (재확인)

Galaxea R1 Pro(양팔 7-DoF, 평행 그리퍼, 토르소 고정)·Unitree G1(7-DoF 팔, Dex3-1 3지 핸드)가 AI Worker·Franka 대비 많은 테이블탑·선반 과제에서 실패. 실패는 주로 (a) 다중 물체/2단계 과제, (b) 몸에 가까운 리치(close-to-body reach). 기존 가설: 장면이 AI Worker 지오메트리 기준으로 설계됨, 리치 데드존, 손가락 간격 테이블, ready/carry 포즈 문제.

## 규칙 적용

1.5년 규칙(2025-03-26 이후 핵심 근거, 그 이전은 [경계]/[기초]), 신뢰도 규칙(스타/인용 적으면 "뒷받침만") 적용. 날짜·venue/star·라이선스 표기.

---

## 1. 결론 요약 (추천은 §4)

가장 직접적이고 신뢰도 높은 근거는 **우리가 이미 쓰는 스택인 Isaac Lab Mimic/SkillGen의 GR1T2·Unitree G1 공식 태스크**와 **DexMimicGen의 subtask-분할 데이터 증폭**, 그리고 **HumanoidGen/RoboTwin 2.0의 "로봇별 IK/그립 후보 재탐색"** 패턴이다. 특히 Isaac Lab의 `*_waist_enabled` 변형이 실재한다는 사실 자체가 — 토르소/허리 보조축을 리치 확장 변수로 다루는 것이 업계 표준 설계라는 신호이며, 우리 R1 Pro의 "에피소드당 토르소 고정" 설계와 정면으로 대비된다.

---

## 2. 휴머노이드 시뮬 데이터 생성 프레임워크

- **Isaac Lab Mimic / SkillGen** (isaac-sim/IsaacLab, **8,269★**, BSD-3-Clause, 최근 커밋 2026-10-02 — 우리와 동일 스택): `isaaclab_tasks/manager_based/manipulation/pick_place/config/`에 **GR1T2** 공식 태스크(`pickplace_gr1t2_env_cfg.py`, **`pickplace_gr1t2_waist_enabled_env_cfg.py`**, `exhaustpipe_gr1t2_*`, `nutpour_gr1t2_*`, 일부 `pink_ik` 솔버)와 **Unitree G1 + Inspire Hand**(`pickplace_unitree_g1_inspire_hand_env_cfg.py`) 태스크가 존재. `stack` 태스크는 아직 franka/galbot/ur10만 지원(휴머노이드 미지원, 확인됨). SkillGen 메커니즘: cuRobo GPU 모션플래너로 **접근/후퇴 구간은 충돌-free 플래닝, transit 구간은 충돌체크**, grasp/place 시 객체 attach/detach를 궤적과 동기화. 공식 수치(Franka 큐브스태킹 기준, 휴머노이드 수치는 미확인): 데이터생성 성공률 40–70%, BC 정책 성공률 40–85%(1000 데모), RTX 6000 Ada에서 1000 데모 생성 90–120분. **`waist_enabled` 변형의 존재 자체가 핵심 신호**: 허리/토르소를 리치 확장용 설계 변수로 명시적으로 켜고 끈다.
- **DexMimicGen** (NVlabs/dexmimicgen, arXiv 2410.24185 2024-10-31 [기초, 최신 유지보수 2025-12-06], **288★**, NVIDIA 소스코드 라이선스/데이터 CC-BY 4.0): 60개 인간 시연 → 21K 데모 자동 합성. 양팔 + 멀티핑거 핸드, real-to-sim-to-real 파이프라인으로 **휴머노이드 can-sorting 과제에 실제 배포**된 사례 있음. 핵심 메커니즘은 **subtask 분할(approach/grasp/transport/place) + 객체 기준 상대 변환(object-relative transform)만 바꿔 재생** — 적은 시연으로 물체 배치를 바꿔 대량 생성.
- **HumanoidGen** (TeleHuman/HumanoidGen, NeurIPS 2025, arXiv 2507.00833 2025-07-01, CC BY-NC 4.0, 별 수 확인 안 됨→신뢰도 중하): **Unitree H1_2** 사용, mplib 플래너. LLM이 "atomic dexterous operation + 공간 제약 체인"으로 장기·다중물체 과제를 분해, 어려운 경우 MCTS로 계획 보강. **직접 확인된 실측값**: `mplib/planner.py`의 IK 시드 수(`n_init_qpos`)를 기본 **20 → 50**으로 늘려야 동작했다고 설치 가이드에 명시 — redundant 7-DoF에서 시드 수 부족이 실패 원인이 될 수 있다는 구체적 증거.
- **RoboTwin 2.0** (RoboTwin-Platform/RoboTwin, ICML 2026, arXiv 2506.18088 2025-06-22, **2,936★**, MIT, 최근 커밋 2026-09-24): 731개 애셋 라이브러리 + 구조화된 domain randomization(혼잡도·조명·배경·**테이블 높이**·언어 5축). **테이블 높이를 최대 3cm 범위로 무작위화**(리치/운동학 일반화 목적, 원문: "table heights vary across workspaces, affecting robot perception, kinematics, and interaction"). **Embodiment-aware grasp candidate generation**: 선호 접근 방향 + 랜덤 포즈 교란 + **cuRobo 병렬 모션플래닝 시도**를 결합해 로봇별로 성공하는 그립 후보를 고른다(한 로봇에 튜닝된 waypoint를 그대로 재사용하지 않음). 성공률 개선은 저-DoF 로봇(Piper 2.4%→25.1%, +22.7%p)에서 크고 고-DoF(Franka 67.3%→67.2%)는 거의 불변 — "이미 충분한 DoF/튜닝이 있으면 효과가 작다"는 대조군 역할. **주의**: README/논문에서 5개 embodiment(Franka·Piper·UR5·ARX-X5·Aloha-AgileX)만 확인됨, **휴머노이드 지원은 미확인**(가정하지 않음).
- **GR00T N1** (NVIDIA, arXiv 2503.14734, 2025-03-18 [경계, 1.5년 규칙 바로 직전이나 메이저 기술보고서]) / **DreamGen = GR00T-Dreams** (arXiv 2505.12705 2025-05-19, GitHub NVIDIA/GR00T-Dreams **616★**, Apache-2.0): 비디오 world model로 "neural trajectory"(합성 비디오 → 역동역학/latent action 복원) 생성. 우리의 **기구학적 리치/충돌 실패**와는 결이 달라 **관련성 낮음**(시각 다양성 확장 쪽 — 향후 과제로만 메모). "GR00T-Mimic"이라는 별도 독립 프로젝트는 검색상 확인 안 됨(Isaac Lab Mimic/DexMimicGen을 GR00T 파이프라인에 쓰는 것을 가리키는 비공식 표현일 가능성).
- **Galaxea 공개 자료**: `GalaxeaManipSim`(OpenGalaxea, 46★, Apache-2.0, 2025-08-18) — 자사 로봇 전용 시뮬(범용 해법 아님, "AI Worker 지오메트리 장면 문제"의 반대 사례로만 참고), `GalaxeaVLA`(803★), `GalaxeaDP`(41★). "Open-World Dataset"이라는 별도 GitHub 저장소는 없음(HF 등 다른 곳 가능성, 확인 안 됨). 논문 "Galaxea Open-World Dataset and G0 Dual-System VLA"(arXiv 2509.00576, 2025-08-30)은 실물 teleop 데이터+VLA 모델이라 시뮬 리치/IK 문제와 **직접 관련성 낮음**.
- **BiGym** (arXiv 2407.07788 2024-07 [경계], GitHub NeuracoreAI/bigym 229★, Apache-2.0, 유지보수 중): 모바일 양팔, "이동으로 접근"이 전제라 "몸 가까운 리치"보다는 베이스 이동 의존 — **관련성 중간**.
- **HumanoidBench** (arXiv 2403.10506 2024-03 [기초], 798★): 전신제어/로코모션 RL 벤치마크, 데이터 생성 파이프라인 아님 — **관련성 낮음**.
- **Unitree 조작 레포**: `avp_teleoperate`→**`xr_teleoperate`**로 리네임(1,685★), `unitree_IL_lerobot`→**`unitree_lerobot`**(771★) — 둘 다 사람이 직접 원격조작/학습 코드일 뿐 자동 장면생성·reachability 로직 없음 — **관련성 낮음**.

---

## 3. 7-DoF 모션 플래닝 · 3지 핸드 파지 실행

**주의**: 이 절은 WebSearch 예산 소진(세션 전체 0/200) 후 WebFetch+curl(GitHub/arXiv API)로만 조사했다. 항목 중 일부(엘보 선호, carry pose, reachability-aware scene)는 1차 근거를 충분히 못 찾았다 — **근거 부족으로 명시**, 설계 확정에 쓰지 말고 재조사 대상으로 둔다.

- **cuRobo IK 설정 실측**(NVlabs/curobo, 1,885★, Apache-2.0, 최근 커밋 2026-09-10/리팩터링 진행 중): main 브랜치 `IKSolverCfg.num_seeds` 기본값 **32**, LM seed solver(`seed_solver_num_seeds`)도 **32**, `optimizer_collision_activation_distance` 기본 **0.01m**. 공식 `InverseKinematics` 예제(Franka 7-DoF, 평행 그리퍼)는 `num_seeds=12`를 씀. **HumanoidGen(H1_2, mplib 기준)이 20→50으로 늘려야 했던 사실**과 겹쳐보면, 7-DoF+humanoid 자기충돌 복잡도에서는 공식 기본 범위(12~32)보다 더 필요할 수 있다는 정황이 두 독립 소스에서 일관되게 나옴. G1/GR1 전용 공식 cuRobo IK 예제·null-space/엘보 비용 항은 레포 리팩터링(`curobo/_src/`)으로 위치가 바뀌었거나 grep으로 못 찾음 — **코드 직접 탐색 필요(미확인 상태로 둠)**.
- **approach/standoff 궤적**: PreAfford(arXiv 2404.03634, 2024-04/08 [기초, 1.5년 규칙 이전]) — point-level affordance + relay training으로 사전파지 계획, ShapeNet-v2 성공률 +69%p, **2지 평행 그리퍼 전용**(3지 핸드엔 직접 적용 안 됨). GES-UniGrasp(arXiv 2509.23567, 2025-09-28, venue 미확인→**신뢰도 낮음, 뒷받침만**) — geometry-based expert selection, ContactGrasp 773객체/82카테고리에서 멀티핑거 파지 train/test 99.4%/96.3%, 손 종류·standoff 수치는 본문 미확인. **고정 cm 값을 쓰는 수치 근거는 확보 못함** — 업계 관례(배경지식 수준, 미검증)로 "palm-to-fingertip 길이의 0.5~1배" 정도가 거론되나 1차 출처 미확인.
- **엘보 방향(elbow-up/down) 선호, carry/ready pose, reachability-aware scene 자동배치**: 최근(2025-03 이후) 전용 논문을 특정하지 못함(WebSearch 예산 소진 + arXiv OR 매칭 한계). **조사 미완 — 설계에 반영 전 재조사 필요**로 명시. 다만 RoboTwin 2.0의 tabletop height ±3cm 랜덤화와 embodiment-aware grasp candidate generation(§2)은 이 영역에서 유일하게 arXiv ID로 확인된 근거다.
- **3지 핸드 파지 실행(Dex3-1/Allegro/LEAP)**: Dex3-1 전용 pre-shaping·sequential closing의 최신 전용 논문은 특정 못함. GitHub에서 `g1-dex3-act-grasping`(개인 레포, 연구 신뢰도 낮음, 뒷받침 안 됨)만 발견 — **핵심 근거로 쓰지 않음**.

---

## 4. 검증 가능한 추천 (일반 메커니즘, 로봇별 하드코딩 금지)

1. **IK 시드 수를 측정된 실패율에 비례해 자동 스윕**: cuRobo 공식 기본값(`num_seeds=32`, Franka 예제는 12)을 "2지 그리퍼·단순 자기충돌" 기준선으로 두고, 자기충돌 링크가 많거나(3지 핸드) standoff가 짧은(몸통 근접) 경우 IK 실패율이 목표치(예: <1%) 밑으로 떨어질 때까지 시드 수를 2배씩 늘리는 자동 스윕을 건다. HumanoidGen이 H1_2+mplib에서 20→50으로 올려야 했던 실측과 cuRobo 기본값(12~32)이 겹쳐 보이는 정황 — 로봇 이름이 아니라 "실패율"이 트리거.
2. **standoff/접근 거리를 손 치수로 정규화**: 고정 cm 값 대신 (그리퍼 최대 개도 또는 핸드 palm 폭) × k(0.5~1.0, 성공률로 보정)로 approach waypoint 거리를 정의. R1 Pro(평행 그리퍼)·G1(Dex3-1)에 같은 수식, 다른 실측 입력값만 적용.
3. **충돌 활성화 거리를 손/팔 충돌구체 반경 기준으로 재스케일**: cuRobo 기본 `optimizer_collision_activation_distance=0.01m`은 Franka류 기준값. 3지 핸드처럼 충돌구체가 더 조밀/작으면 구체 최소 반경의 0.5~1배로 재설정 후 "과도 보수적 접근 실패" 여부를 재측정.
4. **Reachability 사전필터 + 재배치 루프**: 장면 샘플링 때 cuRobo로 목표 pose의 도달가능성(IK해+충돌없는 경로, N시드 병렬)을 미리 계산, 실패율 임계(예 20%) 초과 배치는 베이스/토르소 기준 반경·각도를 좁혀 재샘플링(RoboTwin 2.0 embodiment-aware grasp candidate generation + Isaac Lab SkillGen 충돌-free 접근/후퇴 개념을 장면생성 단계로 끌어올림).
5. **몸-가까운 데드존을 실측 반경으로 지표화하고 토르소/허리 보조축 유무로 쌍대 비교**: R1 Pro·G1 각각의 실패 object-to-shoulder 거리 분포를 측정해 "최소 안전 접근 반경(mm)"을 로봇별 실측값으로 저장, 이보다 가까운 배치는 자동 배제. 보조축이 있으면(Isaac Lab GR1T2 `waist_enabled` 선례) 켠/끈 상태를 쌍으로 비교해 R1 Pro의 "에피소드당 토르소 고정" 정책 자체를 재검토할 실측 자료로 쓴다(즉시 변경 아님, 버리기 전 재검토 규칙).
6. **소수 시연 → subtask-분할 재생으로 다중물체/2단계 과제 증폭**: DexMimicGen/Isaac Lab Mimic처럼 성공 시연을 approach/grasp/transport/place subtask로 분할, 각 subtask의 object-relative transform만 바꿔 재생. 생성 성공률과 다운스트림 성공률을 분리 측정.
7. **그리퍼/핸드 치수 기반 테이블·선반 간격 파라미터화**: "손가락 간격 테이블"의 AI Worker 기준 고정값을 각 로봇의 실측 평행 그리퍼 개도/3지 핸드 접촉폭으로 치환, 같은 장면에서 간격만 바꿔 A/B 재측정.
8. **실패를 단계별로 분해해 원인 귀속**: approach-IK 실패/파지 실패(접촉·힘 기준)/운반 중 낙하/배치 실패를 구분 로깅(기존 "단계별 분해 추론" 규칙과 일치). 위 추천들의 효과는 이 분해 지표로만 판정.

**근거 부족으로 재조사 필요(설계 확정에 쓰지 말 것)**: 엘보 방향(elbow-up/down) 선호 null-space 비용 설계, carry/ready pose 전용 최신 기법, Dex3-1류 3지 핸드의 접촉/힘 기반 순차 닫기 전용 최신 논문 — 이번 조사(WebSearch 예산 소진)로 1차 근거를 확보하지 못함.

## 5. 버리기 전 재검토해야 할 것

- "RoboTwin 2.0 휴머노이드 지원"은 README/논문 선에서 미확인이다. 채택 전 실제 RoboTwin 2.0 코드(`envs/`, `task_config/`)에서 G1/H1/GR1 클래스 존재 여부를 직접 확인하는 것을 권장(이 보고서는 GitHub API/README 조사만 수행, 코드 레벨 미확인).
- "GR00T N1/DreamGen 관련성 낮음" 판정은 "리치/충돌" 문제 기준이다. 추후 시각 다양성·도메인 갭 문제로 전환되면 재평가 필요.

## 참고 출처

- Isaac Lab: https://github.com/isaac-sim/IsaacLab (8,269★, BSD-3, 2026-10-02 커밋)
- DexMimicGen: arXiv 2410.24185 / https://github.com/NVlabs/dexmimicgen (288★)
- HumanoidGen: arXiv 2507.00833 / https://github.com/TeleHuman/HumanoidGen
- RoboTwin 2.0: arXiv 2506.18088 / https://github.com/RoboTwin-Platform/RoboTwin (2,936★, MIT)
- GR00T N1: arXiv 2503.14734 · DreamGen/GR00T-Dreams: arXiv 2505.12705 / https://github.com/NVIDIA/GR00T-Dreams (616★, Apache-2.0)
- Galaxea: https://github.com/OpenGalaxea (GalaxeaManipSim 46★, GalaxeaVLA 803★) / arXiv 2509.00576
- BiGym: arXiv 2407.07788 / https://github.com/NeuracoreAI/bigym (229★, Apache-2.0)
- HumanoidBench: arXiv 2403.10506 / https://github.com/carlosferrazza/humanoid-bench (798★)
- Unitree: https://github.com/unitreerobotics/xr_teleoperate (1,685★) · unitree_lerobot (771★)
- cuRobo: https://github.com/NVlabs/curobo (1,885★, Apache-2.0, num_seeds=32 기본·Franka 예제 12, collision_activation_distance=0.01m 기본)
- PreAfford: arXiv 2404.03634 [기초] · GES-UniGrasp: arXiv 2509.23567 [신뢰도 낮음, 뒷받침만]
