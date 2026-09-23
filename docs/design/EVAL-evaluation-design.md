# EVAL. 평가 설계 (구체화판)

> 개정: 2026-09-23 D6(모의 심사) 반영 (`D6-mock-review.md`, 00-interfaces §17): 주장 문구를 "과제 데이터로 미세조정한 학습 정책(VLA 포함)" + "같은 인식 앞단 위에서"로(§4.1, 사용자 빨간 줄 불변), 새 절 **§4.4** — 2×2(결정 층 {LLM, 규칙, B3c} × 상태 {정답, 인식}, S3 파일럿 규모), **B3c-V**(동결 π0.5 표현 + 헤드), **π0.5 few-shot 적응 곡선**(random 시연 k=5, 20, 2512.02902 대응), **바닥 과제 뺀 7과제 사전 등록 분석**, 조건부 **E-link**(RoboDojo Gen 4과제 random 벽시계, C2' 대 C5 — 한 논문 틀일 때만 필수), 조건부 **E-real 최소판**([결정 필요] 19). 새 항목마다 사전 등록 판정과 비용·시간 [가정]. §3.1 B3c-V·B3b' 추가, §5 S3에 2×2 표시, §8 Q7·Q8.
> 개정: 2026-09-23 D5 반영 (`D5-consistency.md` 4-2, 00-interfaces §16): effort 표기를 "잠정 기본 high(다른 작업 발언 근거) — 이 프로젝트 적용은 [결정 필요] 5, 00 §16"로 통일(출처는 user-log가 아니라 다른 작업 발언).
> 개정: 2026-09-23 정본 §14–§15 반영 (`00-interfaces.md` §14·§15): 모듈 실험 중 본 평가 구성에 걸리는 두 조건을 §5 끝에 적음 — E-M8a **정적 규칙 조건**(절제 조건, 근거 논문 없음. 2602.09902는 "실패하면 항상 상향"의 비용 측면 반대 근거로만 기록, 사용자 원칙 불변), E-M10 **역량 보존 사례 삭제 조건**(Smyth·Keane IJCAI 1995).

> 개정: 2026-09-23 D4 반영 (`D4-devils-advocate.md` F1·F6·F8·F9·D-4·C-1·C-2·C-4·C-5·C-9·C-10·E-2, 00-interfaces §13): H4(인식 술어 정확도 standard 대 random)를 S1 직후로 당기고 random 스냅샷 오프라인 룰 대 Jev 추가(S1.5), 트랙 선택을 "T1 술어가 계산되는가"에 묶음, Astra effort 기본 high(RoboDojo 원문 medium은 재현 조건만), S0 통과 조건 = XPolicyLab 루프가 정책을 기다리는지 확인, 공식 동기 트랙과 벽시계 트랙 분리 보고, 주장 문구에 "같은 인식 앞단" 필수, S2를 "E2a 뒤 RoboDojo 이식 점검"으로 고침(초기 실험은 단일 팔 자작 장면).

작성: 2026-09-23 UTC(첫 판 표기 "2026-09-24"는 KST 날짜, D4 C-10), 단계 2 평가 설계 에이전트. 대상: `plan.md` §3 평가, §5, §6 / `docs/research/v3/10`, `13` / `user-log.md` 11-(10)(11).
표기: **[원문]** = 문서·README·논문이 말한 것(출처 URL과 위치). **[우리 계획]** = 우리 제안. **[사용자]** = 사용자 발언(바꾸지 않음). **[결정 필요]** = 사용자가 정할 것. **[우리 계산]** = 공개 원자료로 우리가 직접 계산한 값(원문에 없는 수치).

---

## 0. 사용자 의도 [사용자] (바꾸지 않는다)
- 비교 대상: **Astra만 / Jev만 / VLA / 룰베이스(스킬 다발) / LLM+스킬을 연결한 기존 논문 / Astra를 쓰는 기존 논문.** (user-log 11-(10))
- "VLA는 다른 환경으로 일반화가 안 되고 LLM은 된다. 이걸 엄청 부각하고 항상 기억한다." (user-log 11-(5))
- 안전은 크게 다루지 않는다. (user-log 11-(11)) → 이 문서는 안전 지표를 두지 않는다. 시뮬레이터가 내는 불안정 표본 처리만 적는다(§6).

## 1. 이번에 새로 확인한 것 (앞 보고서 정정 포함)

| # | 내용 | 구분 | 출처 |
|---|---|---|---|
| N1 | **Astra의 RoboDojo Gen standard/random 분리 수치를 공개 원자료로 계산할 수 있다.** RoboProbe 저장소가 2,100칸 전부를 칸(slot)별로 공개한다. Gen 과제는 "slot 1–25 = standard, 26–50 = 짝지은 `_random`"이고 **같은 layout_id 0–24를 양쪽에 쓴다(짝 300쌍)**. | [원문] | `https://raw.githubusercontent.com/RoboProbe/RoboProbe/main/results/l3_inspect_eef_official_2100/astra_task_layouts.json` (`protocol.generalization` 필드) |
| N2 | 위 자료로 계산: Astra Gen **Score 35.32 → 31.40 (상대 하락 −11.1%)**, **SR 32.67 → 28.33% (−13.3%)**. 두 조건 평균 33.36 / 30.50은 논문 표 1 Gen 셀과 일치(검산 통과). 95% CI(과제 재표집 부트스트랩 1만 회): Score 하락 2.2~22.2%, SR 하락 3.8~27.1%. 과제 안 짝 재표집(과제 고정): −3.6~23.8%. | **[우리 계산]** (논문에 없는 값. 논문 2609.24170은 Gen을 평균만 보고) | 같은 JSON, 스크립트는 §9 |
| N3 | 과제별(Score, std→rnd): stack_blocks 89.8→86.4, fold_clothes 76.8→76.0, arrange_largest_number 76.0→61.4, stack_bowls 68.8→64.2, push_T 68.0→52.0, sort_nesting_dolls 16.0→20.0, pack_objects 11.0→12.2, sweep_blocks 8.0→0.0, pour_liquid 8.0→0.0, hang_mugs 0.6→1.2, make_toast 0.0→1.0, store_laptop 0.8→2.4. **12개 중 5개는 standard에서도 거의 0점(바닥 효과)**이라 하락폭은 7개 과제가 정한다(standard Score ≥10 과제만: −8.4%). | [우리 계산] | 같은 JSON |
| N4 | 비교: RoboDojo 원 논문 표 3 π0.5 **20.92 → 5.82 (−72.2%)**. 즉 공개 자료만으로도 "Astra-as-policy는 random에서 −11%, 미세조정 VLA는 −65~−93%"라는 **예비 지지 증거**가 있다. 단 (1) Astra는 wiki 레시피를 받았고 VLA는 안 받았다, (2) Astra는 1 seed, (3) "같은 인식" 조건이 아니다(둘 다 RGB 직접). | [원문] + [우리 계산] | 2607.04434 표 3, 2609.24170 §3.3 |
| N5 | **RoboDojo 라이선스 표기가 엇갈린다.** 저장소 `LICENSE` 파일은 MIT(© 2025 Yue Chen)인데 README 본문·배지는 "RoboDojo **Non-Commercial** Research License … Commercial use requires prior written permission". v3/10·13의 "MIT"는 **정정 필요**. 연구 목적 사용은 양쪽 모두 허용이라 우리 평가에는 지장 없음. 보수적으로 "비상업 연구용"으로 적는다. | [원문] | `raw.githubusercontent.com/RoboDojo-Benchmark/RoboDojo/main/README.md` 끝 "License" 절, 같은 저장소 `LICENSE` |
| N6 | **LIBERO-PRO README에는 환경(Env) 섭동 수치가 표로 있다**(v3/10은 "그림에만"이라 적음 → 보완). π0.5 Env: Goal 0.46 / Spatial 0.46 / 10 0.46 / Object 0.73. π0: 0.39/0.60/0.27/0.29. OpenVLA: 0.98/0.89/0.85/0.00. 원본 LIBERO는 모두 ≥0.9. 단 README 스스로 "환경을 바꾸면 경우에 따라 탁자 위 물체가 무작위로 움직인다, `main_table`만 안정"이라고 적어 **환경 축 신뢰성이 낮다.** | [원문] | `raw.githubusercontent.com/Zxy-MLlab/LIBERO-PRO/master/README.md` "LIBERO-Pro Model Leaderboard", "Note!!!" 줄 |
| N7 | LIBERO-Plus README 리더보드 값이 논문 표 1과 다르다(π0 카메라: README 13.8 / 논문 15.8, 조명 85.0 / 79.6). 판본이 다른 것으로 보인다. **인용할 때 출처(README 대 논문 표)를 반드시 명시.** | [원문] | `raw.githubusercontent.com/sylvestf/LIBERO-plus/main/README.md` |
| N8 | **Isaac Sim 5.1 공식 요구사항은 "RT 코어 없는 GPU 미지원"**이다(RoboDojo Installation Issues 문서가 인용). 우리 H200은 RT 코어가 없다. 한편 RoboProbe `setup`은 "A100/A800 호스트에서는 `scripts/a100_env_setup.sh`"를 제공한다(A100도 RT 코어 없음) → 데이터센터 GPU에서 돌리는 우회 경로가 실제로 있다. **첫 단계에서 스모크로 확인해야 할 1순위 위험.** | [원문] | `robodojo-benchmark.com/doc/common-issue/installation/`, `raw.githubusercontent.com/RoboProbe/RoboProbe/main/README.md` |
| N9 | RoboProbe Lite 주 조건의 정보 경계: **RGB + 고유수용(관절) + 공식 지시문만.** "Depth, camera calibration, ground-truth object poses, layout metadata and reward internals are not available." | [원문] | `RoboProbe/docs/llm_benchmark_protocol.md` "Locked benchmark boundary" |
| N10 | GPT-as-Policy(Astra xhigh가 π0.5 행동을 검토·수정): RoboDojo 10과제 × 정렬 사례 5개, 하이브리드 Score 62.60 / SR 48%, Astra Direct 26% / 37.81. "공식 모델 비교는 재가중 공개 참고치이지 같은 seed 재실행이 아니다." 코드 공개(시뮬 자산·체크포인트 제외). | [원문] | `raw.githubusercontent.com/anonymous-report-421/GPT-as-Policy/main/README.md` 9행 |

---

## 2. 벤치마크별 실행 가능성

### 2.1 RoboDojo-Sim (주 벤치마크) [원문 → 우리 계획]
| 항목 | [원문] | 출처 |
|---|---|---|
| 시뮬레이터 | Isaac Sim 5.1 + Isaac Lab 2.3, Python 3.11, CuRobo | README 배지, doc/usage/install-and-download |
| 하드웨어 | Ubuntu 22.04 권장, RAM ≥32 GB, VRAM ≥16 GB, 드라이버 570/580, CUDA 12.8. Isaac Sim 5.1은 RT 코어 없는 GPU 미지원(N8) | install-and-download §1, common-issue/installation |
| 설치 | `bash scripts/install.sh -i` (단계별 재개 `--from isaacsim` 등), 자산 `scripts/init_assets.sh`(ModelScope, git-lfs), 경로 갱신 스크립트. Docker(시뮬 쪽만) 선택 | install §3~5, §8 |
| 데이터 | LeRobot v2.1 64 GB / v3.0 120 GB / HDF5 523 GB / 깊이 포함 ≈4.5 TB / 실물 273 GB. 25 Hz, 카메라 3개(머리·좌우 손목, 480×640) | install §6 |
| 체크포인트 | `scripts/RoboDojo/download_ckpt.sh huggingface Pi_0` 식으로 정책별 다운로드(어댑터가 있어야 함) | install §7 |
| 로봇 | 양팔 ARX X5(`dual_x5`, 팔 6축 × 2 + 그리퍼 1 × 2), 행동 `joint` 또는 `ee`(기본 `ee`) | configurations "Robot config", quick-evaluation 인자표 |
| 과제 | 42 기본 + Gen 12개의 `_random` 짝 = 실행 가능 54개. Gen 12 / Memory 6 / Precision 8 / Long 8 / Open 8 | quick-evaluation "Benchmark rules" |
| standard/random 설정 | **`_random`은 별도 과제 설정**(`stack_bowls_random` 등, 같은 목적, `--only`로 따로 실행). 무작위화 대상 5가지: 탁자 위 방해물, 탁자 재질, 바닥 재질, 조명(종류·세기·색온도), HDR 배경. 배치는 seed로 고정된 `Assets/Eval_Layout/RoboDojo/arx_x5/<seed>/` | quick-evaluation, sim-tasks/domain-randomization, configurations |
| 공식 에피소드 수 | `--eval-num native`: 비-Gen 과제 50회/seed, Gen 기본 25회/seed, Gen random 25회/seed. 출판용은 seed 0·1·2 세 번. 요약 스크립트가 Gen 기본과 `_random`을 합쳐 `_summary.md` | quick-evaluation "Complete evaluation" |
| 점수 | 과제별 단계 점수(예: stack_bowls 0/15/100), Score = 과정 보상 평균 × 100, SR = 완전 성공 비율 | sim-tasks/stack-bowls, 2609.24170 §3.3 |
| 정책 꽂기 | XPolicyLab 어댑터: `policy/<NAME>/eval.sh`, `deploy.yml`, `model.py`(`update_obs`, `get_action`, `reset`, 배치판). websocket 정책 서버 ↔ Isaac 클라이언트 분리 가능. **`EVAL_ENV_TYPE=debug`로 Isaac 없이 배선 점검** | doc/usage/xpolicylab |
| 관측 형식 | RGB(+선택 깊이·내부/외부 행렬), 관절·EE 자세. 깊이·행렬은 설정(`observation.vision`)으로 켜고 끔 | configurations "Top-level config", xpolicylab "Standard Data Formats" |
| 불안정 표본 | 배치 불안정·보조 팔 실패 표본은 "unstable"로 표시되고 **집계에서 빠진다**(정책 실패로 세지 않음) | common-issue/evaluation |
| 병렬 | `scene.num_envs`(기본 1), `--gpu-ids`로 과제를 GPU별 분배 | parallel-environments, quick-evaluation |
| 라이선스 | README: 비상업 연구 라이선스 / LICENSE 파일: MIT (N5) | README |

**[우리 계획] 우리 스택을 꽂는 방법**
- 정책 서버 = 우리 스택 전체(인식 앞단 M1 → Jev/Astra 결정 → 스킬 → M5). XPolicyLab `model.py`의 `get_action()`이 **행동 덩어리(action chunk)**를 돌려주는 구조라, 우리 비정지 루프는 서버 안에서 돌고 `get_action()`은 "현재 확정 궤적의 다음 N틱"을 넘긴다. 25 Hz 시뮬이 정책 응답을 기다리는지(동기 스텝)는 **확인 못 함** → 시뮬이 기다리면 "비정지"의 벽시계 이점은 시뮬에서 드러나지 않는다(§7 위험 R3). **S0 통과 조건으로 확인한다**(§5). 동기이면 두 트랙으로 따로 돌리고 따로 보고한다: **공식 동기 트랙**(XPolicyLab 원 루프 그대로, VLA 공개 수치 B3a와 같은 프로토콜, "비정지·겹침 이점은 이 트랙 점수에 나타나지 않는다"고 명시) / **벽시계 트랙**(시뮬 시간을 벽시계에 묶어 실제 Jev·Astra 지연이 작용, M4·M8 비교 전용, 공개 VLA 수치와 같은 열에 두지 않는다).
- 행동 공간은 `ee`(RoboProbe L3 Inspect EEF와 같은 경계). 스킬은 EE 목표 → 비학습 계획기(CuRobo/RoboProbe 변환부)로 관절 경로. **RoboProbe 변환부를 그대로 재사용**하면 Astra 기존 결과와 행동 경계가 같아진다.
- 정보 경계는 두 트랙으로 나눈다 [결정 필요] — **선택은 "트랙 O에서 M1 T1 술어가 계산되는가"에 묶는다**(D4 F6·C-4):
  - **트랙 O(공식 경계, RGB + 관절만)**: RGB + 관절 + 지시문(+ wiki 레시피, Astra 조건과 같게). 깊이·보정·정답 자세 없음(N9와 같음). 인식 앞단은 RGB에서만 상태를 만든다(M1 후보 중 단안 깊이/다중 시점 방식 필요). RoboDojo 카메라(머리·좌우 손목 3대)의 외부 행렬도 없어 삼각측량이 어렵다. 이 경우 M1 T1 술어(깊이·3D 기하, 결정적)가 성립하지 않을 수 있고, 그러면 M7 하드 층(T1 전용)·M9 체크포인트·M4 `expected_after`가 흔들린다.
  - **트랙 D(우리 인식 앞단, 깊이·카메라 행렬 켬)**: VLA는 원래 쓰지 않는 정보라 **표에 "입력 정보 다름"을 적는다.**
  - 판단 자료: S1.5(§5)에서 트랙 O 조건으로 T1 술어 정확도를 시뮬 정답과 비교한다. (i) T1 술어가 트랙 O에서도 사전 문턱(술어별 정확도 ≥ 95%, M1 등록부 기준)을 넘으면 주 = 트랙 O / (ii) 못 넘으면 두 선택지를 대칭으로 올린다: 주 = 트랙 D(입력 다름 표기) 또는 주 = 트랙 O + T1 등록부를 단안 추정 기반으로 재등급(대부분 T2로 강등, 하드 층 약화 수용).
  - 정답 상태(시뮬 내부 자세)는 **상한선 참고**로만(v3/10 §3-4 유지).

### 2.2 LIBERO-Plus (보조, 환경 축 세분)
- [원문] robosuite/MuJoCo, 원 LIBERO를 대체 설치(`pip install -e .` + 추가 apt 패키지), 자산은 HF `Sylvest/LIBERO-plus`. 평가는 LIBERO와 같고 `num_trials_per_task`를 50 → 1로. 과제 10,030개, 과제 ID ↔ 섭동 범주·난이도 표 `task_classification.json`. 섭동 7축: 배치, 카메라, 로봇 초기 상태, 언어, 조명, 배경, 센서 노이즈. 평가 대상은 VLA만. CVPR 2026.
- 설정 부담: 낮음(단일 Franka, MuJoCo, GPU는 렌더·VLA 추론 정도). 우리 스택: 단일 팔용 스킬 필요(양팔 스킬과 별도). 정답 상태를 주면 조명·배경·노이즈 축이 무의미해지므로 **인식 추정 상태로만** 돌린다.
- 공개 수치: VLA 10종(README 표, 논문 표 1과 판본 차이 N7), Astra판 TGL LIBERO-Plus 92.4%(v3/01, 축별 분리 여부 미확인).

### 2.3 LIBERO-PRO (보조, 범주 5·6 공개 수치가 가장 많은 곳)
- [원문] LIBERO와 같은 환경(conda py3.8, torch 1.11), bddl/init 파일은 HF `zhouxueyang/LIBERO-Pro`. `evaluation_config.yaml`의 `use_environment / use_swap(위치) / use_object / use_language / use_task`, 한 번에 하나(조합은 설정 가능, task는 조합 불가). 환경 섭동 불안정 경고(N6). 라이선스 MIT 배지.
- 공개 수치: VLA(README 표, Env 열 포함), CaP-X(위치·작업 축만, 표 2), RPent Astra low **92.63% (741/800, 8개 묶음 전체)** — 어느 섭동 축인지는 문서 확인 필요(`rpent.readthedocs.io` 리더보드), Zetta 90.8%.
- 우리 쓰임: **환경 주장 근거로는 약하다**(N6). 범주 5·6 기존 방법과 같은 판에 서는 용도.

### 2.4 AGNOSTOS (선택, 작업 축)
- [원문] RLBench/CoppeliaSim, Pixi로 설치(CUDA 12.4 필요), 데이터 seen 18과제 140 GB + unseen 23과제 20.2 GB. X-ICM(7B 23.5%, 72B 30.1%, 로그 공개), VLA는 seen 18과제로 미세조정 후 unseen 23과제 시험(`custom_agent.py`의 `_inference`만 구현하면 됨). NeurIPS 2025.
- 우리 쓰임: 작업 축(새 작업) 보조. X-ICM은 LLM(Qwen 72B, 로컬 GPU 필요)이라 범주 5 비교가 된다. 환경 축 근거는 아님.

### 2.5 MolmoSpaces (선택, "양쪽 모두 zero-shot" 새 집)
- [원문] `pip install molmo-spaces==0.2.9`(벤치 고정 판본), **벤치 실행은 MuJoCo만 지원**, 8작업 벤치(MS-Bench v1/v2), `eval_main.py … PiPolicyEvalConfig --benchmark_dir …`. Franka FR3(+Robotiq), RB-Y1 등. Apache 2.0(일부 Objaverse 자산은 비상업). 2026-09-13 "업그레이드 중, 안정판 0.2.9 사용" 공지. 리더보드 `molmospaces.allen.ai/leaderboard`, 정책 모음 `molmospaces_policy_zoo`.
- 우리 쓰임: π0.5-DROID도 해당 집 데이터 0이라 **가장 공정한 zero-shot 비교**. 단 Franka 스킬을 새로 붙여야 하고 결과 수치가 논문에선 그림뿐. 4단계 이후.

### 2.6 요약표 [우리 계획]
| 벤치 | 설정 부담 | GPU | 우리 스택 꽂기 | 범주 1 | 2 | 3 | 4 | 5 | 6 | 쓰임 |
|---|---|---|---|---|---|---|---|---|---|---|
| RoboDojo-Sim | **높음**(Isaac 5.1, RT 코어 위험, 자산 수십 GB) | 작업자당 ≥16 GB VRAM 1장 | XPolicyLab 어댑터, `ee` 경계 | **공개 칸별 자료(N1)** | 구현 | 공개 40종 + 체크포인트 재실행 | 구현 | 재구현 필요 | **RoboProbe, GPT-as-Policy 코드** | **주: 환경 축(Gen) + 작업 축(Open)** |
| LIBERO-Plus | 낮음 | 작음 | 단일 팔 스킬 필요 | TGL(축 불명) | 구현 | VLA 10종 | 구현 | 없음 | TGL | 보조: 환경 축 세분 |
| LIBERO-PRO | 낮음 | 작음 | 같음 | RPent Astra | 구현 | VLA 6종 | 구현 | CaP-X, Zetta | RPent | 보조: 기존 방법과 같은 판 |
| AGNOSTOS | 중간(CoppeliaSim) | 72B 로컬 LLM 시 큼 | 키프레임 자세 출력 | 없음 | 구현 | π0·OpenVLA·RDT | 구현 | X-ICM, D&R | 없음 | 선택: 작업 축 |
| MolmoSpaces | 중간 | 작음(MuJoCo) | Franka 스킬 새로 | 없음 | 구현 | π0/π0.5-DROID zero-shot | 구현 | 없음 | 없음 | 선택: 새 집 |

---

## 3. 기준 방법 재현 경로

### 3.1 범주별 [사용자 범주 → 우리 계획]
| 범주 | 구체 조건 | 코드 | 새로 구현할 것 | 공정 조건 |
|---|---|---|---|---|
| 1. Astra만 | **B1a** RoboProbe L3 Inspect EEF 그대로(이미지 직접, `move_eef`/`give_up`, 호출 100회, medium). **B1b** 우리 인식·스킬 위에서 Astra가 결정 지점마다 직접 답(Jev 없음, 로봇은 응답 동안 "직전 행동 유지") | B1a: RoboProbe 공개(설정 스크립트, `run_fixed_layout.sh`) + 칸별 결과 공개 | B1b는 우리 스택의 스위치 | B1a는 **공개 결과 재사용 + 일부 layout 재실행으로 모델 판본 변동 확인**. B1b는 Astra 호출 상한을 우리 시스템과 같게 |
| 2. Jev만 | 우리 스택에서 Astra 끔. 첫 계획(세션 계약)은 과제별 고정 문서, 실패 시 Astra 대신 M9 아래 층 복구만 | Jev API | 과제별 고정 세션 계약 12개(Gen) | [결정 필요] 고정 계약을 누가 쓰나: (a) 사람이 wiki 레시피로 작성(정보 동등) / (b) Astra가 standard 장면 1장으로 사전 작성(Astra 누출) |
| 3. VLA | **B3a** 공개 표 3 수치(π0.5, X-VLA, Spatial Forcing, π0, GR00T N1.7, Hy-Embodied). **B3b** XPolicyLab 체크포인트로 π0.5(필수)·X-VLA·Spatial Forcing을 **같은 layout 0–24에서 재실행**(칸별 짝 자료 확보, 표 3 재현 점검). **B3c** [우리 계획] "같은 인식 위 학습 결정 층": 우리 인식 앞단이 만든 상태 벡터/술어를 입력으로 받는 상태 기반 모방 정책(DP 또는 ACT)을 **standard 시연으로만** 학습 | B3a/b: XPolicyLab `policy/Pi_05` 등 + `download_ckpt.sh` | B3c: 시연 영상 → 인식 앞단 → 상태 변환, 학습 스크립트 | B3b는 공식 native 프로토콜. B3c는 우리 방법과 **입력이 완전히 같다** → 핵심 대조의 "VLA식 학습 결정 층" 대표 |
| 4. 룰베이스(스킬 다발) | **B4a** 같은 술어·같은 스킬 위 손으로 쓴 규칙(E2a 룰의 작성 규칙을 따르되, E2a 룰은 단일 팔 단일 과제용이라 RoboDojo Gen 과제마다 양팔 규칙을 새로 쓴다. 과제당 작성 예산은 **Jev 질문 템플릿과 같은 예산**으로 사전 고정, D4 C-9). **B4b** 과제별 고정 스킬 순서(분기 없음) | 없음 | 과제별 규칙표 | 규칙 작성 시간(사람-시간)과 개발에 쓴 seed를 기록. 규칙 작성자는 standard 장면만 본다(random은 시험 전용) |
| 5. LLM+스킬 기존 논문 | **B5a** CaP-X를 LIBERO-PRO에서 공개 코드로(공개 수치와 대조). **B5b** RoboDojo에서 "CaP-X식" 재구현: Astra가 우리 스킬 API 위에서 코드 생성 + 다회 실행 피드백. **B5c** X-ICM(AGNOSTOS, 선택). Show-Harness는 Isaac Lab·Piper 양팔 해석기가 있어 ARX X5 이식을 검토 | CaP-X 공개(ICML 2026), X-ICM 공개, Show-Harness 공개 | B5b 전부, Show-Harness ARX 해석기 | B5b는 "재구현"임을 표기. 같은 스킬 API·같은 인식·같은 Astra 판본·같은 호출 상한 |
| 6. Astra 쓰는 기존 논문 | **B6a** RoboDojo Astra = B1a와 같은 것(논문 2609.24170). **B6b** GPT-as-Policy(π0.5 + Astra xhigh 검토) 공개 코드로 Gen 12과제 재실행. **B6c** RPent Astra를 LIBERO-PRO에서(공개 수치 + 코드) | RoboProbe, GPT-as-Policy, RPent 공개 | GPT-as-Policy의 클러스터 설정 이식 | B6b는 π0.5 체크포인트가 같은 것인지 확인. effort는 원문대로 xhigh |
| 7. 예산 맞춘 메모리 없음 | 우리 스택에서 M10(경험) 끔, Astra·Jev 호출 수를 켠 쪽 실측에 맞춤 | 우리 스택 | 없음 | 호출 수 ±10% 안 |
| 8. logprob 선택기 | Jev 자리에 GPT-6 Sol/Luna(`none` effort, logprob) 또는 system-one-adapter를 같은 질문·보기로 | API | 질문 형식 어댑터 | 같은 결정 지점·같은 보기·같은 호출 주기 |
- **(D6, 00 §17) 범주 3 추가 조건**: **B3c-V** = B3c의 사전학습 VLA 기반 변형. 같은 카메라 이미지와 과제 문장을 **동결 π0.5 표현**(VLM 백본 출력 토큰 풀링)에 넣고, 그 위에 작은 헤드(MLP 또는 작은 행동 헤드)만 standard 시연으로 학습한다. 선택으로 우리 인식 상태 벡터를 헤드 입력에 이어 붙인 판(B3c-V+s)도 둔다. 학습 예산·늘리는 규칙은 B3c와 같다(§4.2 H2). **B3b'** = π0.5에 random 장면 시연 k개(k = 0, 5, 20)로 추가 미세조정한 적응 조건(§4.4 (3)). 둘 다 표의 "적응 예산" 열에 시연 수·학습 GPU 시간을 적는다.
- **(D6) 범주 8은 E-M4-gen에서도 쓴다**: 같은 확정기를 붙인 C2 대 C5(M4 §5.1 (2)). 질문 형식 어댑터는 한 벌로 공유.

### 3.2 공정 조건 체크리스트 (모든 비교에 적용) [우리 계획]
1. **같은 layout·seed**: RoboDojo `Eval_Layout/arx_x5/<seed>` layout_id 0–24(Gen std/rnd 짝). 모든 시스템이 같은 칸을 돈다.
2. **같은 인식**(범주 2·4·7·8, B1b, B3c, B5b): M1 판본 해시를 결과 파일에 기록. 인식 앞단은 standard 장면에서만 조정(개발). random은 시험 전용.
3. **정보 동등**: wiki 레시피 문장을 **모든 LLM 시스템(B1, B2, 우리, B5b, B6)과 규칙 작성자**에게 똑같이 준다. VLA(B3a/b)는 레시피를 쓸 수 없으므로 표에 "입력 정보 다름" 표기(원문 2609.24170 §3.3과 같은 단서).
4. **같은 호출 예산**: Astra 호출 상한 100/에피소드(RoboDojo 기본값). Jev는 초당 상한(설정 표 T_c 0.33 s)과 에피소드 총량을 기록. 비용(달러)·토큰도 같이 보고.
5. **같은 행동 경계**: `ee` 목표 + RoboProbe 비학습 변환부. 정밀 프리미티브(집기 등)를 쓰는 시스템(우리, B4, B5b)은 RoboProbe 원문이 "집기 프리미티브를 주지 않는다"고 한 것과 **조건이 다르다**는 것을 B1a 대비 표에 적는다.
6. **모델 판본 고정**: Astra·Jev(`jev-1.13.0`)·Sol 판본 문자열과 날짜 기록. B1a 공개 결과는 2026-09 이전 실행이므로 **재실행 표본(과제 4개 × 짝 10개)으로 판본 변동 점검**.
7. **effort**: 우리 시스템과 Astra를 쓰는 모든 기준(B1b, B5b 등)의 Astra effort **= high**(잠정 기본 high(다른 작업 발언 근거) — 이 프로젝트 적용은 [결정 필요] 5, 00 §16). B1a(RoboDojo 원문)의 medium은 **재현 조건으로만** 쓴다(공개 결과 + 같은 layout medium 재실행 일부로 판본 점검). B1a 대 우리 비교 표에는 "effort 다름(medium 대 high)"을 각주로 적는다.
8. **불안정 표본**: RoboDojo가 빼는 unstable 표본은 모든 시스템에서 같은 규칙(버퍼 layout ≥50으로 채움, RoboProbe 선택 규칙과 같게)으로 처리하고 개수를 보고.

---

## 4. 핵심 주장 시험 (사전 등록안)

### 4.1 주장과 가설 [우리 계획, 문구는 plan §3 [제안] 유지, 최종 [결정 필요]]
- 주장: "같은 인식 앞단 위에서, 과제 데이터로 미세조정한 학습 정책(VLA 포함)은 배경·조명·방해물이 바뀌면 성능 대부분을 잃는다. 학습 없는 API 모델 + 스킬 결정 층은 같은 변화에서 상대 하락폭이 작다." 절대 성공률 우위는 주장하지 않는다.
- **문구 규칙(D4 F1)**: 초록·결과·그림 설명 등 이 주장을 쓰는 모든 문장에 **"같은 인식 앞단 위에서(same perception front-end)"** 한정어를 넣는다. 한정어 없이 "LLM이 일반화한다"고 쓰지 않는다. 인식 앞단이 변화를 흡수했다면(H4) 그것은 LLM의 몫이 아니라 인식의 몫이다.
- **문구 규칙 2(D6, 00 §17)**: 평가 주장에서 "VLA" 대신 **"과제 데이터로 미세조정한 학습 정책(VLA 포함)"**을 쓰고 **"같은 인식 앞단 위에서"** 한정어를 항상 붙인다. §0의 [사용자] 빨간 줄("VLA는 다른 환경으로 일반화가 안 되고 LLM은 된다")은 바꾸지 않는다. 바뀌는 것은 논문에 쓰는 검정 줄(주장 문구)뿐이다. B3c가 DP/ACT라 "VLA가 아니다"라는 반론(D6 R1 약점 1)에는 B3c-V(§3.1)로 답한다.
- **H1 (시스템 수준)**: RD(우리) < RD(π0.5 재실행 B3b).
- **H2 (같은 인식, 학습 결정 층 대 LLM 결정 층)**: RD(우리) < RD(B3c). ← 사용자 요구 "같은 인식, VLA 대 LLM"을 가장 깨끗하게 재는 대조.
- **H3 (같은 인식, 규칙 대 LLM)**: random 조건 Score(우리) > Score(B4a). RD 차이도 보고. ← 인식이 환경 변화를 막아 주면 규칙도 안 무너질 수 있다. 그 경우 LLM의 몫은 RD가 아니라 random에서의 절대 점수·Open 축·복구에서 보여야 한다(정직하게 사전 등록).
- **H4 (인식 귀속, S1 직후로 당김 — S1.5)**: standard → random에서 인식 술어 정확도 하락(시뮬 정답과 비교, 분석용 기록만, 정책 입력 아님)이 RD의 몇 %를 설명하는지. **S4를 기다리지 않고** S1 스모크의 렌더 프레임으로 먼저 잰다(Jev·정책 없음). 사전 해석: 술어 정확도 하락이 작으면(과제 합산 T1·T2 술어 정확도 하락 < 3%p **[우리 계획: 문턱]**) "환경 강건성은 인식 몫, LLM 몫은 방해물·Open 축·복구에서 찾는다"로 주장 문구를 S4 전에 고쳐 [결정 필요](Q5)로 올린다.

### 4.2 프로토콜
- 과제: RoboDojo Gen 12과제 전부(주). 바닥 효과 과제(standard Score <10)도 빼지 않고 포함하되, 부차 분석으로 "standard Score ≥10 과제만"을 따로 보고(사전 등록).
- 에피소드: 과제당 standard 25 + random 25(layout 0–24 짝) × seed 0 = **시스템당 600회**. 주 시스템(우리, B4a, B3b, B3c)은 seed 1·2를 더해 1,800회(예산 되면). B1a는 공개 자료 1 seed.
- 지표: 주 = **상대 하락 RD = 1 − Score_rnd / Score_std**(과제 합산 Score, RoboDojo 표 3과 같은 식). 보조 = SR 기반 RD, 과제별 RD, random 절대 Score, 0% 과제 수, 결정 수·호출 수·지연 p50/p95·비용.
- 통계:
  - **짝 층화 부트스트랩**(과제 고정, 과제 안 layout 짝 재표집, 시스템 간에도 같은 layout 인덱스로 같이 재표집) 10,000회, 95% 백분위 CI. 이게 주 추론(12과제를 고정 대상으로 보는 해석).
  - **과제 군집 부트스트랩**(과제 재표집 후 과제 안 짝 재표집) = "다른 과제로 일반화" 해석용 부차 CI.
  - 시스템 간 차이 ΔRD = RD(A) − RD(B)의 CI. 과제별 짝 McNemar(SR)는 기술 통계로만.
  - 다중 비교: 주 가설 H1·H2 두 개만 확인적, 나머지는 탐색적으로 표기.
- **사전 등록 판정 기준**
  - H1 지지: ΔRD(우리 − π0.5) 95% CI 상한 < 0 **그리고** RD(우리) 점추정 ≤ 35%(π0.5 72%의 절반 이하).
  - H2 지지: ΔRD(우리 − B3c) 95% CI 상한 < 0. B3c가 standard에서 우리보다 Score가 낮으면(학습이 덜 된 경우) "공정 비교 불성립"으로 기록하고 B3c 학습을 늘린다(시연 수·에폭은 사전에 고정, 늘리는 규칙도 사전 고정: standard Score가 π0.5 재실행의 80% 이상이 될 때까지 최대 2회).
  - H3: random Score 차이(우리 − B4a) CI 하한 > 0이면 지지. CI가 0을 걸치고 RD도 비슷하면 "환경 강건성은 인식 앞단 몫"으로 결론을 **바꿔 적는다**(주장 문구 수정 [결정 필요]).
  - 실패 처리: H1이 기각되면 핵심 메시지를 주 결과로 쓰지 않고 사용자에게 보고.
- 표본 크기 근거 [우리 계산]: Astra 1 seed(600회)의 RD CI 폭이 약 ±10~13%p(N2). π0.5와의 차이(약 60%p)는 1 seed로 충분히 검출. H2·H3의 차이가 10%p 수준이면 1 seed로는 CI가 0을 걸칠 수 있어 **seed 0 결과로 차이 점추정이 <15%p면 seed 1·2를 추가**(사전 규칙).

### 4.3 이미 가진 예비 결과 [우리 계산]
| 시스템 | standard Score | random Score | RD | 조건 |
|---|---|---|---|---|
| GPT-6 Astra (RoboProbe L3, B1a) | 35.32 | 31.40 | **−11.1%** (층화 CI −3.6~23.8, 과제 CI 2.2~22.2) | wiki 레시피, medium, 100호출, 1 seed, RGB 직접 |
| π0.5 (표 3) | 20.92 | 5.82 | −72.2% | 과제 데이터 미세조정, 레시피 없음 |
| Spatial Forcing (표 3) | 21.25 | 6.98 | −67.2% | 같음 |
| X-VLA (표 3) | 17.92 | 3.04 | −83.0% | 같음 |
→ "Astra-as-policy는 덜 무너진다"는 방향이 **미심사 벤치마크 공개 자료**(RoboDojo 2607.04434, RoboDojo Astra 평가 2609.24170)에서 보인다(정보·seed·인식 조건 다름, π0.5 쪽 seed·에피소드 수는 확인 못 함 §10, D4 E-2). **우리 기여는 이것을 "같은 인식" 조건(H2·H3)과 우리 계층 구조(Astra+Jev+스킬)로 옮기는 것**이다. 이 표는 조건이 달라 같은 열 비교가 아니다(주석 필수).

### 4.4 D6 모의 심사 추가 분석 (00-interfaces §17, `D6-mock-review.md` R1·메타 사유 1·2·5) [우리 계획]
모두 **사전 등록**이다. (1)~(4)는 탐색적 분석(주 가설 H1·H2의 다중 비교 수에 넣지 않음)이고, (5)·(6)은 조건부 실험이다.

**(1) 2×2 표 — 결정 층 {LLM, 규칙, B3c} × 상태 {정답, 인식}** (메타 사유 2, R1 약점 2)
- 칸: 우리(LLM 결정 층: Jev + Astra) / B4a(규칙) / B3c(같은 상태 입력의 학습 결정 층) × **정답 상태**(시뮬 정답으로 계산한 술어·상태 벡터) / **인식 상태**(M1 인식 앞단). 결정 층 3 × 상태 2 = 6칸(이름은 D6의 "2×2"를 따른다). B3c는 상태마다 따로 학습(standard 시연만, 같은 예산).
- 규모 = **S3 파일럿**: Gen 4과제(stack_blocks, stack_bowls, push_T, arrange_largest_number) × std/random 짝 10개 × seed 0 → 칸당 80 에피소드, 6칸 480(인식 상태의 우리·B4a 칸은 S3 본 실행과 공유 → 추가 약 320).
- 지표: 칸별 RD. 인식 몫 = RD(인식) − RD(정답)(결정 층별), 결정 층 몫 = 같은 상태 안 RD 차. 정답 상태에서는 조명·배경·재질 변화가 입력에 안 들어가고 방해물만 남는다는 점을 표에 적는다.
- 사전 등록 판정: (i) 정답 상태에서 세 결정 층 RD가 모두 5%p 안이고 인식 상태에서만 벌어지면 "강건성 차이는 인식 몫"으로 적고 Q5(주장 문구)를 S4 전에 올린다. (ii) 정답 상태에서도 RD(우리) < RD(B3c)(점추정 차 ≥ 10%p)이면 결정 층 몫이 있다는 방향 신호로 S4에서 같은 표를 12과제로 확장한다. (iii) 파일럿이라 CI가 넓다(칸당 짝 40, 폭 약 ±15%p [우리 계산, 대략]) → 판정은 "방향"만, 확인은 S4.
- 비용·시간 [가정]: 추가 320 에피소드 × 약 5분(Astra high 포함) ≈ 27 시간 직렬 → 병렬 6개 약 5 시간. B3c 두 벌 학습 GPU 약 1일. 정답 상태 배선(시뮬 상태 → 술어) 약 1일. Astra 비용은 S3 단가로 실측 뒤 확정.

**(2) B3c-V — 사전학습 VLA 기반 변형** (R1 질문 1)
- 정의는 §3.1. H2를 B3c-V로도 같은 식(ΔRD(우리 − B3c-V) CI)으로 잰다. S3 파일럿에서 먼저, 방향이 서면 S4에 넣는다.
- 사전 등록 판정: H2 문장은 B3c와 B3c-V **둘 다**에서 ΔRD CI 상한 < 0일 때만 "같은 인식 위 학습 정책보다 덜 무너진다"로 쓴다. B3c에서만 성립하면 "소량 시연 모방 정책(DP/ACT)보다"로 좁힌다(D6 R1 약점 1). B3c-V standard Score가 π0.5 재실행의 80% 미만이면 B3c와 같은 증액 규칙(최대 2회).
- 비용·시간 [가정]: π0.5 표현 추출은 추론만(과제당 시연 수 × 프레임), 헤드 학습 GPU 수 시간 × 과제 4(파일럿) → 약 1~2일. 에피소드 S3와 같은 규모(160).

**(3) π0.5 few-shot 적응 곡선 — 2512.02902 대응** (R1 약점 3·질문 3)
- B3b'(§3.1): random 장면 시연 k ∈ {0, 5, 20}(과제당)으로 π0.5를 추가 미세조정. 시연 장면은 시험 layout 0–24와 겹치지 않는 random layout(25–49 [가정: 배치 폴더가 있는지 S0에서 확인])에서 만들고, 시연 생성 경로(원문 데이터 생성 스크립트 사용 가능 여부)는 **[가정]**, S0에서 확인.
- 과제: S3 4과제. 에피소드: k마다 std/random 짝 10 → 3점 × 4과제 × 20 = 240.
- 보고: 가로 k, 세로 random Score·RD의 곡선에 우리(적응 시연 0) 수평선. 표에 "적응 예산" 열(시연 수, GPU 시간).
- 사전 등록 판정: (i) k = 5에서 π0.5 RD가 우리 RD의 CI 안에 들어오면 주장을 **"적응 시연 없이(0-shot) 같은 인식 앞단 위에서"**로 한정하고, 교차 k를 본문에 적는다. (ii) k = 20에서도 π0.5 RD − 우리 RD ≥ 20%p(점추정)이면 "소량 적응으로 따라잡히지 않는다"를 탐색적 결과로 적는다. (iii) 그 사이면 곡선만 보고하고 문장은 (i)의 한정을 쓴다.
- 비용·시간 [가정]: 미세조정 2회(k = 5, 20) × 과제 4 × π0.5 LoRA/전체 미세조정 GPU 약 4~8 시간 → GPU 약 1.5~3일. 시연 수집 약 1일(스크립트 가능 시). 평가 240 에피소드 ≈ 병렬 수 시간.

**(4) 바닥 과제 뺀 7과제 부분집합 — 사전 등록 분석** (R1 약점 4, 메타 기타)
- 7과제 = B1a(Astra 공개) standard Score ≥ 10인 과제: stack_blocks, fold_clothes, arrange_largest_number, stack_bowls, push_T, sort_nesting_dolls, pack_objects. 빠지는 5과제 = sweep_blocks, pour_liquid, hang_mugs, make_toast, store_laptop(§1 N3). **목록은 우리 결과를 보기 전에 공개 자료로 고정**한다(§4.2의 "우리 결과 standard ≥10" 부차 분석과 별개로 둘 다 보고).
- 판정: H1·H2를 7과제에서도 같은 식으로 계산. 12과제 결론과 7과제 결론의 방향이 다르면 본문에 둘 다 적고 주장은 약한 쪽을 따른다.
- 비용: 추가 실행 없음(S4 자료 재분석).

**(5) E-link (조건부) — RoboDojo 위 M4 연결** (메타 사유 1)
- **필요 조건**: 사용자가 [결정 필요] 18에서 **2안(한 논문: 방법 + 평가)**을 고를 때만 필수. 1안(분리)이면 하지 않는다.
- 설정: Gen 4과제(S3와 같은) **random**, **벽시계 트랙**(§6 트랙 분리: 시뮬이 정책을 기다리지 않고 실시간으로 진행, S0에서 루프가 동기면 실시간 진행 래퍼를 새로 만든다 [가정: 약 2~3일]). 우리 스택에서 M4만 C2'(겹침 + 감쇠 융합) 대 C5로 바꾼다. 짝 25 × seed 0·1 → 조건당 200, 합계 400 에피소드.
- 사전 등록 판정: C5 − C2' random Score 짝 부트스트랩 CI 하한 > 0이면 "확정 규칙이 일반화 벤치마크의 벽시계 조건에서도 이득"으로 두 기여를 잇는다. CI가 0을 걸치면 한 논문 틀의 연결 근거가 없다고 보고하고 [결정 필요] 18을 다시 올린다(1안 전환 권고). 공식 동기 트랙 결과와 같은 표에 두지 않는다.
- 비용·시간 [가정]: 400 에피소드 × 약 5분 ≈ 33 시간 직렬 → 병렬 6개 약 6 시간. Jev 약 $5, Astra는 S3 단가로 실측 뒤.

**(6) E-real 최소판 (조건부) — 실물 단일 팔** (메타 사유 5, R3 약점 2)
- **필요 조건**: [결정 필요] 19(하드웨어 사용 여부)에서 사용자가 허락할 때만. 로봇 학회 제출이면 사실상 필수(ICRA 2027은 이미 마감, plan §8).
- 설정: 실물 단일 팔 pick-and-place, 섭동 2종(물체 이동, 짧은 가림 [가정: 사람 손 또는 판으로 재현 가능한 두 종]) × C2' 대 C5 × 약 20회 = 80회. 같은 섭동 시각·크기를 섭동 순서표로 고정, 조건 순서는 교대.
- 사전 등록 판정: 두 섭동 합산 40짝에서 C5 − C2' 성공률 짝 부트스트랩 CI 하한 > 0이면 "실물에서도 같은 방향"을 주장. CI가 0을 걸치면 "방향 일치/불일치"만 보고(검정력 부족 명시). epoch 교체 빈도·미확정 실행 비율·번복률 분포(M4 §5.1 (3))를 시뮬 값과 나란히 보고(conformal 교환성 붕괴 여부 확인).
- 비용·시간 [가정]: 하드웨어 준비·배선 약 1주, 실행 80회 × 약 3분 ≈ 4 시간 + 리셋, Jev 약 $1.

---

## 5. 단계별 실행 계획 (자원이 적을 때 순서) [우리 계획]
| 단계 | 내용 | 자원 | 산출·진행 조건 |
|---|---|---|---|
| S0 (GPU 없음, 반나절) | RoboProbe 칸별 자료 분석(§4.3, 완료), RoboProbe·XPolicyLab 클론, `pytest`, 우리 어댑터 뼈대를 `EVAL_ENV_TYPE=debug`로 배선 점검, **XPolicyLab 평가 루프(`deploy.py` 등)가 정책 응답을 기다리는지(동기 여부)와 에피소드 시간 제한 확인** | CPU | 어댑터가 행동 키·차원 점검 통과 **그리고** 루프 동기 여부 확정(D4 C-5). 동기이면 공식 동기 트랙·벽시계 트랙 두 벌 계획으로 S3·S4 예산을 다시 적는다 |
| S1 (1~2일) | Isaac Sim 5.1 설치를 클러스터 노드에서 시도(RT 코어 위험 N8, RoboProbe A100 스크립트 참고), `robodojo.sh doctor`, `smoke --only stack_bowls,push_T`, π0.5 체크포인트로 stack_blocks·stack_bowls std/rnd 각 25회 | GPU 1~2장 | π0.5 재실행 RD가 표 3과 ±15%p 안이면 통과. 실패하면 RTX 계열 노드 확보 [결정 필요] |
| **S1.5 (S1 직후, GPU 몇 시간 + Jev 약 $1~5)** | (1) **H4 선행 측정**: Gen 2~4과제 std/random 짝 layout 렌더 프레임에서 M1 술어 정확도(트랙 O·D 각각)를 시뮬 정답과 비교. Jev·정책 없음. (2) **random 스냅샷 오프라인 룰 대 Jev**: 같은 random 스냅샷(인식 상태)에서 룰(B4a)과 Jev가 같은 결정 질문에 답하고, 결과 기반 라벨(E §4.4b와 같은 짧은 롤아웃 라벨러)로 채점 | GPU 1장 + Jev API | 산출: 트랙별 T1·T2 술어 정확도 표(§2.1 트랙 선택 자료), std→random 술어 정확도 하락(H4), random에서 룰 대 Jev 결과 기반 정답률. 해석은 §4.1 H4 사전 문구대로. 멈춤 조건 아님 |
| S2 | E0·E1·E2a는 **단일 팔 자작 장면에서 끝낸다**(00 §13, E 문서). 여기서는 **E2a 뒤 RoboDojo 이식 점검**만: Gen 두 과제(stack_blocks, stack_bowls)에서 우리 스택이 정답 상태(상한) → 인식 상태 순으로 도는지, E0 지연·E1 보정이 RoboDojo 관측 형식에서도 크게 다르지 않은지 축소판으로 확인 | GPU 1장 + Jev API | 이식 점검 통과(행동·관측 배선, 지연·보정 축소판이 E0·E1과 크게 다르면 표시). 마차 판정은 E2a에서 이미 끝남 |
| S3 파일럿 | Gen 4과제(stack_blocks, stack_bowls, push_T, arrange_largest_number = Astra가 점수를 낸 과제) + 바닥 과제 1개(pour_liquid) × 짝 10개: 우리 / B4a / B2 / B3b. **(D6) 같은 4과제로 2×2 표(§4.4 (1)), B3c-V(§4.4 (2)), π0.5 적응 곡선 B3b' k=5·20(§4.4 (3))** | GPU 2~4장 | 효과 방향 확인, 비용·시간 실측으로 S4 예산 확정. 2×2·B3c-V·적응 곡선의 방향으로 S4 확장 여부 결정 |
| S4 주 실험 | Gen 12 × 짝 25 × seed 0: 우리, B4a, B2, B3b(π0.5), B3c, B7. B1a는 공개 자료 + 재실행 점검 | GPU 4~8장 병렬(`--gpu-ids`) | H1·H2·H3 판정. 필요하면 seed 1·2 |
| S5 | Open 8과제(작업 축): 우리, B1a(공개), B3b, B4a. LLM 이점이 가장 클 곳(Astra Open 31.00% 대 VLA ≈2%) | 같음 | 작업 축 결과 |
| S6 | 범주 6 B6b(GPT-as-Policy)를 Gen에서, 범주 5 B5b(CaP-X식 재구현) | 같음 + Astra xhigh 비용 | 범주 5·6 같은 판 비교 |
| S7 | LIBERO-Plus 환경 축(조명·배경·노이즈·배치·카메라) 부분집합 + LIBERO-PRO(CaP-X, RPent 공개 수치 옆) | GPU 1~2장 | 보조 표 |
| S8 (선택) | AGNOSTOS, MolmoSpaces | | |
- 시간 추정은 **미측정**이다. Astra 첫 토큰은 medium 5.9 s, **high(기본) 약 73 s**, xhigh 약 198 s(plan §1, Artificial Analysis 2026-09-23 값, 날마다 변동). high × 실패 호출 여러 번이면 에피소드가 수 분 이상일 수 있고, 동기 트랙에서는 이 대기가 시뮬 시간으로 드러나지 않는다. B1a형 재현(medium) × 최대 100호출도 10분 이상일 수 있다. S3에서 실측해 S4 규모를 정한다. 사용자 원칙 세 개의 수치 충돌은 M9 §7 [결정 필요].
- Jev 요청 한도 1,200/분: 3 Hz × 병렬 에피소드 6개 = 1,080/분 → **동시 에피소드 6개 이하**로 운영.
- **모듈 실험 조건 메모(00 §14·§15)** — 본 평가 전에 단일 팔 자작 장면에서 끝내는 모듈 실험이고, 결과가 본 평가의 "우리" 시스템 구성을 정한다.
  - E-M8a(M8 §5): **정적 규칙 조건 A8**(트리거별 부름/안 부름을 미리 고정, 동적 문지기 없음, 실패 트리거는 항상 호출)을 둔다. 이 조건은 문지기의 가치를 재는 절제 조건이고 근거 논문을 두지 않는다. 2602.09902(ICLR 2026)는 2모델·사용자 이탈 게임에서 **공급자 비용 기준** 최적 라우팅이 거의 항상 캐스케이드 없는 정적 정책이라는 결과라 이 비교의 근거가 아니며, "실패하면 항상 Astra"에 대한 비용 측면 반대 근거로만 기록한다. 사용자 원칙(실패할 때마다 Astra 개입)은 바꾸지 않는다. §6 비용 지표에서 Astra 호출 비용을 성공률과 함께 보고한다.
  - E-M10(M10 §5): **역량 보존 사례 삭제 조건 B10**(Smyth·Keane IJCAI 1995, 기간 밖 기초 문헌)을 이력 기반 삭제(2505.16067, ACL 2026)와 비교한다.

---

## 6. 지표와 보고 형식 [우리 계획]
- 주: RD(Score), random Score, standard Score, 0% 과제 수.
- 비용·시간: 에피소드 벽시계, 정지 시간, Astra 호출 수·토큰·비용·응답 시간, Jev 호출 수·지연 p50/p95.
- 과정: 적시 재현율(M7), 복구 성공률(M9), jerk(M5).
- **트랙 분리 보고**(D4 C-5): 공식 동기 트랙과 벽시계 트랙 결과는 **다른 표**에 둔다. VLA 공개 수치(B3a)와 같은 표에는 공식 동기 트랙 결과만 둔다. 비정지·겹침(M4)·Astra 비동기(M8/M9)의 이점은 벽시계 트랙에서만 주장한다.
- 표기 규칙: 공개 수치와 우리 실행 수치는 **다른 열**. 모든 칸에 (정보 경계 O/D, 레시피 유무, seed 수, 에피소드 수, 모델 판본)을 각주로. unstable 제외 개수 보고.
- 안전 지표는 두지 않는다 [사용자].

## 7. 위험과 반대 증거
- R1 **Isaac Sim이 H200에서 안 돌 수 있다**(N8). 대응: S1에서 가장 먼저 확인, 안 되면 RTX 노드 확보 또는 Docker 경로.
- R2 **바닥 효과**: Gen 12개 중 5개는 Astra도 standard ≈0. 우리 시스템도 같으면 RD가 7개 과제로 결정되고 CI가 넓다. 대응: 부차 분석 사전 등록, 절대 점수를 같이 보고.
- R3 **시뮬 동기 스텝**: XPolicyLab 루프가 정책 응답을 기다리면 비정지·겹침(M4)의 벽시계 이점이 시뮬 점수에 안 나타난다. 확인 못 함 → **S0 통과 조건**으로 확인하고, 동기이면 공식 동기 트랙과 벽시계 트랙을 따로 돌리고 따로 보고한다(§2.1, §6). 벽시계 트랙은 공개 VLA 수치와 프로토콜이 달라진다.
- R4 **정보 비대칭**: 레시피·스킬(집기 프리미티브)은 VLA에 없는 정보다. 상대 하락폭으로 주장하는 이유이고, 절대 비교는 하지 않는다.
- R5 **H3 반대 결과 가능성**: 같은 인식 위에서는 규칙도 안 무너질 수 있다(환경 변화는 주로 인식을 때린다, v3/10 §3-4). 사전 등록대로 결론을 바꾼다. 이 위험을 S4까지 미루지 않도록 H4와 random 스냅샷 룰 대 Jev를 S1.5로 당겼다(D4 W1).
- R6 **Astra 판본 변동**: B1a 공개 자료는 과거 판본. 재실행 점검 필수.
- R7 반대 증거(v3/10 §4 유지): π0.5 새 집, DreamZero 62.2% 대 27.4%(학습에 있던 작업·새 환경), 2512.02902 1-shot 적응 회복, GR 1.5 기성 계획기 실패 25.5% 대 9%. "적응 예산" 열을 표에 둔다.
- R8 벤치 신뢰도: RoboDojo 미심사, 라이선스 표기 엇갈림(N5), LIBERO-PRO 환경 섭동 불안정(N6), LIBERO-Plus 판본 차이(N7).

## 8. [결정 필요]
- Q1 정보 경계: 주 결과를 트랙 O(RGB + 관절만, 공식 경계)로 할지, 트랙 D(우리 인식 앞단, 깊이·보정 허용)로 할지. **S1.5에서 트랙 O로 T1 술어가 계산되는지를 보고 정한다**(§2.1). T1이 트랙 O에서 성립하면 주 = O. 성립하지 않으면 두 안을 대칭으로 올린다: (i) 주 = D, VLA와 입력 다름 표기 / (ii) 주 = O, T1 등록부를 단안 추정 기반으로 재등급(대부분 T2로 강등)하고 M7 하드 층 약화를 받아들임. 첫 판의 "권장: 주 = O"는 T1 성립 여부를 보기 전의 권장이라 거둔다.
- Q2 effort: **잠정 정리(00 §13·§16)** — 우리 시스템은 잠정 기본 high(다른 작업 발언 근거) — 이 프로젝트 적용은 [결정 필요] 5, 00 §16. B1a의 medium은 재현 조건으로만. 첫 판의 "주 비교는 medium" 권장은 이 잠정 기본 반대편에 기운 권장이라 거둔다(D4 D-4). 남는 비용·시간 문제(high 첫 토큰 약 73 s)는 M9 §7 [결정 필요]에 묶는다.
- Q3 Jev만(B2)의 첫 계획을 누가 쓰나(사람 작성 대 Astra 사전 작성).
- Q4 B3c(같은 인식 위 학습 결정 층)를 "VLA 범주"의 대표로 인정할지. 사용자 범주 "VLA"는 픽셀 VLA(B3b)가 원뜻일 수 있어 둘 다 둔다.
- Q5 주장 문구(plan §3). H3가 기각되면 문구를 "인식 앞단 + 학습 없는 결정 층"으로 바꿀지.
- Q6 H200에서 Isaac이 안 되면 다른 GPU 노드 사용 허가.
- Q7 (D6, plan §8 [결정 필요] 18) 논문 틀. 2안(한 논문)이면 E-link(§4.4 (5))가 필수가 된다. 1안(분리)이면 E-link는 하지 않는다.
- Q8 (D6, plan §8 [결정 필요] 19) 실물 로봇 사용. 허락되면 E-real 최소판(§4.4 (6))을 돌린다.

## 9. 재현용 계산 (N2~N3)
```python
import json; d=json.load(open('astra_task_layouts.json'))
G=[r for r in d['rows'] if r['dimension']=='Generalization']
S=[s['score'] for r in G for s in r['slots'] if s['variant']=='standard']
R=[s['score'] for r in G for s in r['slots'] if s['variant']=='random']
print(100*sum(S)/len(S), 100*sum(R)/len(R), 1-sum(R)/sum(S))  # 35.32 31.40 0.111
```
부트스트랩: 과제 재표집 10,000회(seed 0), 층화는 과제 안 짝 재표집 10,000회(seed 1).

## 10. 확인 못 한 것
- XPolicyLab 평가 루프가 정책 응답을 기다리는지(동기 여부), 에피소드 시간 제한(스텝 수).
- RoboDojo 원 논문 표 3의 VLA 수치가 seed 몇 개·에피소드 몇 회인지(native면 seed 3 × 25).
- RPent 92.63%와 TGL 92.4%가 어느 섭동 축인지(환경 축 포함 여부).
- GPT-as-Policy 10과제가 Gen standard/random 중 어느 것인지.
- Isaac Sim 5.1이 H200에서 실제로 도는지(메모리상 이 사용자의 다른 작업은 같은 클러스터에서 Isaac 렌더를 돌린 기록이 있으나 판본 5.1인지 모름).
- MolmoSpaces 리더보드 수치(JS 페이지, 읽지 않음). RoboDojo 리더보드 사이트도 JS라 읽지 않음.
- 사용한 조회: RoboDojo README·LICENSE·문서 9쪽(install, xpolicylab, configurations, quick-evaluation, sim-tasks, domain-randomization, stack-bowls, common-issue 2쪽), XPolicyLab 문서, RoboProbe README·protocol·leaderboard·setup·칸별 JSON, 2609.24170 HTML, LIBERO-Plus·LIBERO-PRO·X-ICM·MolmoSpaces·GPT-as-Policy·CaP-X·RPent·Show-Harness README. WebSearch 0회.
