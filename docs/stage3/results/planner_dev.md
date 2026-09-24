# Task 12 — 오라클 플래너 · DEV 섭동 P0–P2 · 성공 판정

## v2 (challenge-env config) — 2026-09-24 11:05–12:45 UTC

장면 = `scene_bringup.md`의 v2 절(humanoid-challenge-env 로봇·카메라 복사본, 베이스 고정, 오른팔 초기 자세 변경). 플래너 FSM·섭동·성공 판정은 v1 그대로다. **시드: DEV 0–29만**(TEST 1000–1149·TEST-P5 1300–1329는 만들지도 열지도 않음), P3·P4 미구현 그대로. 성공률 측정은 카메라 끔. 결과 원본(파드): `/data/harvest/out/t11_12_v2/final_cpu/dev_P{0,1,2}.jsonl`, `final_gpu/…`, 로그 `/data/harvest/out/t11_12/v2_final_{cpu,gpu}_P*.log`.

### 결과 (v2 vs v1)

| 섭동 | v1 (GPU PhysX, cyclo 설정) | **v2 CPU PhysX (기본, 정본 §48)** | v2 GPU PhysX |
|---|---|---|---|
| P0 | 30/30 (100 %) | **30/30 (100 %)** — 판정 P0 ≥ 90 % 통과 | 20/30 (66.7 %) — lift 6, place 2, carry 2 |
| P1 | 29/30 (96.7 %) | **28/30 (93.3 %)** | 15/30 (50 %) — lift 10, carry 5 |
| P2 | 30/30 (100 %) | **30/30 (100 %)** | 20/30 (66.7 %) — lift 6, place 2, carry 2 |

| 지표 (v2 CPU, 성공 판) | P0 | P1 | P2 | v1 P0 |
|---|---|---|---|---|
| 시뮬 시간 중앙값 (최대) | 8.8 s (9.8) | 9.35 s (10.7) | 8.8 s (9.8) | 11.65 s |
| 놓인 머그–트레이 중심 수평 거리 중앙값 (최대) | 12.7 mm (28.2) | 25.2 mm (29.3) | 14.5 mm (28.2) | 3.5 mm (9.5) |
| 기울기 최대 | 0.0° | 0.0° | 0.0° | 0.0° |
| 쥔 뒤 머그–TCP (x, z) 중앙값 | −10.9, −41.6 mm | −12.9, −46.5 mm | −11.1, −41.6 mm | −9.2, −46 mm |
| 결정 시점 수 중앙값 | 26 | 28 | 26 | 35 |
| RTF (카메라 끔) | **5.18**(P0 단독 실행 중앙값, 4.87–5.36) | — | — | 0.56–0.58 |

- 섭동 발동 시각(실측): P1 2.2–3.2 s(descend 중, 첫 `near`), P2 5.0–6.05 s(carry 시작 + 0.5 s).
- 시뮬 시간이 v1보다 짧은 것은 초기 자세가 작업 영역 위라 접근이 0.6–1.3 s로 짧기 때문이다.
- 놓기 정확도가 v1보다 나쁜 것은 쥔 자세의 x 치우침(복사한 그리퍼: 보조 손가락 k 2)이 그대로 놓는 자리로 옮겨 가기 때문이다. 모두 트레이 안(`mug_outside_tray_mm` 0).

### GPU PhysX에서 떨어지는 까닭 (같은 코드, 물리 장치만 다름)
- 실패 50판 전부 **쥔 뒤 미끄러져 빠짐**(lift·carry·place, 접근·파지 단계 실패 0). 실패 판 중앙값: 패드 간격 65.7 mm(목표 50 mm, 머그 지름 64 mm보다 넓음 = 보조 손가락이 밀려 벌어짐), 머그–TCP 수평 16.0 mm.
- CPU PhysX에서는 같은 파지가 버틴다(쥔 뒤 머그–TCP x −10.9 mm, 실패 0–2판). 즉 복사한 그리퍼(보조 관절 k 2)의 쥐는 힘이 GPU 솔버에서는 모자란다. 기본 물리가 CPU(정본 §48)이므로 GPU 쪽은 더 맞추지 않았다 — 맞추려면 그리퍼 게인을 바꿔야 하고 그것은 복사본에서 벗어나는 일이다.
- GPU RTF(카메라 끔)는 세 프로세스 동시 실행이라 0.20(단독 값 아님).

### 실패 분해 (v2 CPU)
- P0·P2: 실패 없음.
- P1 시드 3 — **lift**: P1이 t 2.6 s(descend 중)에 머그를 (−19.6, −3.7) mm 옮긴 뒤 쥐었고, 들기 0.4 s 만에 `holding` 거짓. 폭 71.3 mm(목표 50 mm → 보조 손가락이 벌어짐), 머그–TCP z −43.3 mm, 머그 바닥 14.9 mm에서 빠짐.
- P1 시드 5 — **lift**: t 3.0 s에 (−14.0, +14.3) mm 이동, 들기 0.25 s 만에 빠짐. 폭 71.2 mm, 머그–TCP z −46.5 mm, 바닥 3.7 mm.
- 둘 다 **섭동으로 중심이 어긋난 파지 + 약한 보조 손가락(k 2)**이 겹친 경우다. 복사한 그리퍼 게인을 바꾸지 않는 한 이 판은 남는다.

### 플래너 쪽 수정 (로봇 설정은 복사본 그대로)

| # | 실측(수정 전) | 원인 | 수정 |
|---|---|---|---|
| 1 | P0 시드 0–3 모두 approach_ik: TCP가 명령보다 21–26 mm 낮게 멈춤, 벌린 손가락이 머그를 쳐 넘어뜨림(기울기 90°) | 로봇 링크 중력 켬 + 팔 PD k 600 → 정적 처짐. 정착 중 `q_target − q` = 관절4 −17.7 mrad, 중력 보상 토크 / k = −16.9 mrad로 일치 | `OraclePlanner._gravity_offset()`: 관절 목표에 `get_gravity_compensation_forces() / joint_stiffness`를 더함(정지 상태 정확, 되먹임 없음). 뒤: descend 중 TCP–명령 < 1 mm |
| 2 | 1 뒤 GPU P0 18/30(실패 lift 9, place 2, carry 1). 시드 1: 접근 중 `arm_r_link1`↔`arm_r_link6` 134–201 N, 팔꿈치 −2.93 rad, 머그 쓰러짐 | 복원된 link6 콜라이더와 자기 충돌 | 오른팔 초기 자세를 작업 영역 위로(장면 판정, `scene_bringup.md` v2 절). 관절 공간 준비 이동은 손끝이 탁상을 쓸어 기각 |
| 3 | 2 뒤 CPU P0 29/30, P1 27/30: 파지 실패 3(폭 80–86 mm), 들기 미끄러짐 1 | 조임 부족 → 보조 손가락이 밀려 벌어짐 | `GRIP_SQUEEZE_M` 0.012 → **0.014**(목표 폭 50 mm). DEV 0–29, CPU, P0/P1 성공: 0.004 → 11/12, 0.012 → 29/27, 0.014 → 30/28, 0.016 → 30/28, 0.024 → 25/22(조이면 carry/place에서 폭 ~70 mm로 빠짐). P0 30/30이 되는 가장 작은 값 |

v1에 있던 "그리퍼 보조 관절 게인을 주 관절 값으로" 변경은 **없앴다**(복사한 설정이 게인을 정의하므로). 네 그리퍼 관절에 같은 목표를 주는 것(행동 쪽)은 유지.

### 프레임 검증 (CPU, 머리캠 + 우손목캠, 단계가 바뀔 때마다 한 장)
- `planner_dev_v2_frames_P0_s0_head.png`, `planner_dev_v2_frames_P0_s0_wrist.png`: approach → retreat. 머리캠에서 오른손이 위에서 내려와 머그를 쥐고 트레이 위에 세워 놓는다. 우손목캠에서 descend 때 머그 윗면이 두 손가락 사이 가운데로 들어오고, close 뒤로는 머그가 화면을 채운 채 트레이 위로 옮겨 가 놓인다.
- `planner_dev_v2_frames_P2_s0_head.png`, `…_wrist.png`: P2 시드 0. place_descend 장에 보라색 o10이 운반 경로 옆 탁상에 나타나 있다(발동 t 5.5 s = carry 시작 5.0 s + 0.5 s). 그 뒤 장에서는 팔에 가려진다. 우손목캠에는 들어오지 않는다(시야가 머그와 트레이에 가깝다).

### 테스트
- 로컬 `python -m pytest -p no:cacheprovider -q`: 233 통과(새 `tests/sim/test_challenge_cameras.py` 7건 포함). 파드(`tools/pod_sync.sh`, `test_stereo_metrics.py` 제외 규칙 그대로) 225 통과. `tools/pod_sync.sh`는 `third_party/`도 보내도록 한 줄 고쳤다.

## v1 (cyclo_lab `FFW_SG2_CFG`, GPU PhysX) — 원래 기록

- 작업 시각: 2026-09-24 09:20–10:54 UTC (파드 `date -u`)
- 파드 `juhyoung-native-7a2a`, **GPU 0만**. 장면은 `scene_bringup.md`(T11) 그대로(카메라 끔으로 실행).
- 코드: `harvest/sim/planner.py`(FSM·오라클 정답·결정 시점·`OraclePlanner`·`run_episode`), `harvest/sim/perturb.py`(P0–P2), `harvest/sim/run_dev.py`(실행기, DEV 0–29 밖 시드는 거부)
- 결과 원본(파드): `/data/juhyoung_qdd/out/t11_12/final/dev_P{0,1,2}.jsonl`, 로그 `fin_P*.log`
- **시드: DEV 0–29만.** TEST(1000–1149)·TEST-P5(1300–1329)는 만들지도 열지도 않았다. P3·P4는 구현하지 않았다(`PerturbState("P3")`는 `ValueError`).

### 요약

| 섭동 | 성공 | 성공률 | 실패 단계 |
|---|---|---|---|
| **P0** | **30/30** | **100 %** (목표 ≥ 90 %, DC4 조건 일부 충족) | — |
| P1 | 29/30 | 96.7 % | approach_ik 1(시드 14, 아래) |
| P2 | 30/30 | 100 % | — |

- 성공 판의 시뮬 시간 중앙값 11.65 s(최대 12.4 s, 제한 60 s). 성공 판정 = `on(o3,o5) ∧ ¬holding(o3) ∧ upright(o3)` 1 s 연속(`success_from_history`), 탁상 밖 낙하(머그 z < −5 cm) 즉시 실패.
- 놓인 머그 중심 ↔ 트레이 중심 수평 거리: P0 중앙값 3.5 mm(최대 9.5 mm), P1 3.1 mm(최대 14.1 mm). 기울기 전부 0.0°.
- RTF(카메라 끔, 90판 중앙값): 0.555–0.579. 한 판 벽시계 약 20 s.
- 결정 시점: T_c = 0.33 s마다, 성공 판 중앙값 35개/판.

### 구현

#### FSM (`next_phase`, 순수 함수)
approach(머그 윗면 위 10 cm) → descend(패드 중심이 머그 윗면 1.8 cm 아래) → close(0.6 s 뒤 `holding(o3)`이면 lift, 아니면 실패) → lift(탁상 좌표 TCP z 0.20 m, 머그 바닥 ≥ h_lift 3 cm 확인) → carry(트레이 위) → place_descend(`in_contact(o3,o5)` 또는 머그 바닥이 트레이 위 3 mm) → open(0.5 s) → retreat(10 cm 위) → done.
- 단계마다 시간 제한(approach 8 s, descend 5 s, close 1.5 s, lift 4 s, carry 6 s, place 5 s, open 1.5 s, retreat 3 s). 넘으면 실패.
- lift·carry·place 중 `holding(o3)`이 3스텝(0.15 s) 연속 거짓이면 실패(떨어뜨림).
- 실패 단계 이름(`FAIL_STAGE`): approach·descend → **approach_ik**, close → **grasp**, lift → **lift**, carry → **carry**, place_descend → **place**, open·retreat·done 뒤 미성공 → **release**.

#### 제어
- IK: Isaac Lab `DifferentialIKController`(pose, 절대, DLS λ = 0.05). TCP = link7 + 167.1 mm(link7 −z) 오프셋, 자코비안을 TCP로 옮김(`J_v − [r]× J_ω`).
- 위에서 잡는 자세, yaw = π/2(손가락이 월드 x축으로 닫힘). IK 시험(목표 9곳 x 0.36–0.48, y −0.40–−0.06): yaw π/2 9/9 도달(≤ 1.9 mm, 1.1°), yaw 0은 y = −0.06 두 곳에서 관절 한계로 약 220 mm 오차(7/9), −π/2 2/9, π 4/9(10 mm 이내 6/9) → π/2 고정.
- 명령 TCP는 목표로 속도 제한 이동: 빠름 0.20 m/s, 내리기 0.06 m/s, **들기 0.08 m/s**. 방향은 1.5 rad/s slerp. **한 스텝(50 ms) 관절 변화 ≤ 0.04 rad**(튐 금지).
- 그리퍼: 쥘 때 목표 폭 = 머그 지름 − 12 mm(52 mm). 완전히 닫는 목표는 손가락이 머그로 14 mm 파고들어 PhysX가 팔을 튕겼다.
- 상태: 매 스텝 `oracle_objects(env)` → `PredicateState.update`(T2 술어기 그대로). **상태 쓰기는 리셋 때 한 번**, 섭동 발동 때 한 번뿐.

#### 오라클 정답·결정 시점 (`oracle_answer`, `decision_points`, 순수 함수)
- 결정 시점 k: t_k = k·T_c(0.33 s), `ds_id = "ds{k}"`. 정답 = 플래너 **명령 TCP**의 [t_k, t_k + T_c] 변위(탁상 좌표)와 그리퍼 명령 변화.
- `dir_xy`: 8방향(`plus_x` … `plus_x_minus_y`, 45° 구간) 또는 `none_xy`(수평 < 2.5 mm). `dir_z`: `up`/`down`/`none_z`(< 2.5 mm). `mag_coarse`: 로그 거리로 가장 가까운 구간(tiny 0.5 / small 1 / medium 2 / large 4 / xlarge 8 cm; `jevcall.MAG`와 같은 값, [가정]). `grip`: `open`/`close`/`keep`(명령 폭 변화 5 mm 기준). 보기 키는 `jevcall.DIR_XY`/`DIR_Z`/`MAG`의 option_key와 같다.
- 예(P0 시드 0): ds0 `plus_x_minus_y / up / xlarge / keep / approach`.

#### 섭동 (`perturb.py`, E §4.5 DEV 행을 주석으로 원문 그대로 옮김)

| 코드 | E §4.5 원문 | 구현 |
|---|---|---|
| P0 | 없음(초기 배치 무작위만) | 아무것도 안 함 |
| P1 | 대상 물체 수평 2 cm 이동(방향 무작위) / 그리퍼가 대상에 `near` 처음 참일 때 | 손가락 중점–머그 중심 < 5 cm(`near_in_m`)가 처음 참인 스텝에 머그 자세를 한 번 써서 (dx, dy) 이동, 크기 정확히 20 mm, 방향 = 시드. 실측 발동 시각 4.25–5.9 s(descend 중) |
| P2 | 방해물이 경로 옆에 등장 / 운반 단계 시작 뒤 0.5 s | carry 시작 0.5 s 뒤 주차해 둔 o10을 운반 직선(머그 → 트레이) 옆 7–13 cm, 구간 안, 다른 물체와 1 cm 이상 떨어진 탁상 위에 한 번 놓음(쪽·거리 = 시드). 실측 발동 7.05–9.25 s |

해석은 우리 것이다(원문에 `near` 주체·"경로 옆" 거리 정의가 없음). P2의 o10은 등장 뒤 `present`에 들어가 술어 계산에 포함된다.

### 실패 분해 (단계별, mm)

#### 최종 실행
- P0: 실패 없음.
- P1 시드 14 — 단계 **approach_ik**(descend 시간 초과). 원인: P1이 descend 중(t = 5.9 s, 손가락이 머그 옆에 내려온 상태) 머그를 (−15.8, −12.3) mm 옮기자 머그가 손가락에 걸려 **넘어짐(기울기 90°)**, 굴러간 머그와 TCP 수평 거리 543 mm, 목표 도달 실패. IK 한계가 아니라 **섭동이 대상 물체를 쓰러뜨린 경우**다. 룰/Jev 쪽에서는 "다시 세우기 또는 보류"가 필요한 상황이라 풀에서 의미 있는 판이다.
- P2: 실패 없음. 운반 높이(머그 바닥 약 12 cm)가 방해물보다 높아 o10이 궤적과 닿지 않는다(프레임 확인).

#### 개발 중 실패(수정 이력, 재발 방지용)
| 회차 | 시드 | 단계 | 실측 | 원인 → 수정 |
|---|---|---|---|---|
| 1 | P0 0–2 | approach_ik | TCP–목표 30–156 mm, 머그 기울기 23° | 탁상 0.76 m에서 yaw 0 자세가 관절 한계 → IK 시험 뒤 yaw π/2, 탁상 0.85 m |
| 2 | P0 0–3 | approach_ik(descend) | 목표 위 12.5 mm에서 멈춤, 머그–TCP z −24.7 mm | 패드 중심을 윗면 35 mm 아래로 내리면 그리퍼 몸체(패드 중심 위 약 23 mm)가 머그 윗면에 닿음 → 18 mm |
| 3 | P0 0–3 | lift | 쥔 뒤 손가락 관절 [0.88, 1.10, 0.16, 0.40], 머그–TCP x −24 mm, 들기 중 TCP가 목표에서 0.3–0.68 m 벗어남 | cyclo 그리퍼 보조 관절 강성 2 → 네 관절 같은 목표·같은 게인. DLS 튐 → 스텝당 0.04 rad 제한. 완전 닫힘 목표 → 폭 52 mm 목표 |
| 4 | P0 24, P1 12판 | lift·carry·place | 들기 0.35–0.6 s 뒤 `holding` 거짓, 머그가 TCP 대비 17–18 mm 미끄러져 내려감(z −46 → −64 mm), 폭 61.5 mm, 수평 어긋남 1–7 mm | 윗면 45 mm만 쥐는 파지에 0.20 m/s 들기가 급함 → 들기 0.08 m/s. (쥐는 힘을 폭 44 mm 목표로 올리면 오히려 5판 전부 실패: 폭 66–68 mm로 벌어지고 팔이 튐 → 되돌림) |
| 최종 | P0·P1·P2 각 0–29 | — | 30/30, 29/30, 30/30 | — |

수정 4(들기 속도) 전 결과: P0 29/30(시드 24 lift), P1 14/30, P2는 도중 중단. 판정은 수정 뒤 전 조건을 다시 돌린 **최종 실행 값**으로 한다. P0 기준(≥ 90 %)은 수정 전에도 96.7 %로 충족이었다.

#### 남은 약점 (숫자로)
- 쥔 자세에서 머그 중심이 TCP보다 x로 −9.2 mm(P0 중앙값), P1은 −11.2 mm 치우친다. 손가락이 닿는 순간 한쪽이 먼저 밀어서다. 그리퍼가 닫는 동안 팔이 약 17 mm 위로 밀린다(머그–TCP z −46 mm, 계획값 −29.5 mm). 즉 **윗부분 약 30 mm만 쥔다.** 무거운 물체·빠른 운반에는 약하다(carry는 0.20 m/s 그대로이고 최종 실행에서 carry 실패는 0).
- 실행 속도: RTF 0.56–0.58(카메라 끔)로 1보다 작다. 방향 질문 5("장면 RTF ≪ 1")에 걸리는 수준은 아니지만 벽시계(wall) 트랙은 이 장면에서 못 쓰고 simlat가 기본이어야 한다(T10 결론과 같음).

### 프레임 검증
- `planner_dev_frames_P0_s0.png`: P0 시드 0, 머리캠, 단계가 바뀌는 순간마다 한 장(approach → retreat). 머그가 트레이 위에 서서 놓인다. (이 장은 수정 4 전 코드로 찍었다. 같은 시드의 최종 실행도 성공, 놓인 위치 3.3 mm.)
- `planner_dev_frames_P2_s0.png`: 최종 코드, P2 시드 0. place_descend 장에 보라색 o10이 운반 경로 옆 탁상에 나타나 있다(발동 t = 7.1 s, carry 시작 6.6 s + 0.5 s). 그 뒤 장에서는 팔에 가려진다.

### 테스트 (로컬, Isaac 없이)
- `tests/sim/test_planner_logic.py`(16): 1 s 연속 성공, FSM 전 경로 전이, close 뒤 미파지 = grasp 실패, lift·carry 중 놓침 = 실패, place는 접촉 또는 도달로 open, 모든 단계 시간 초과 = 실패, 실패 단계 이름 6종, `oracle_answer` 방향·크기 구간·그립, `decision_points`(T_c 간격·ds_id·정답).
- `tests/sim/test_perturb_logic.py`(65): DEV 종류는 P0–P2뿐(P3·P4·P5는 `ValueError`), P1은 DEV 30시드 모두 정확히 2 cm·시드 결정적·방향 다양, P1은 첫 `near`에만 1회, P2는 carry 시작 0.5 s 뒤 1회, P0는 발동 없음, P2 위치는 30시드 모두 경로 옆 7–13 cm·구간 안·겹침 없음.
- 전체: `pytest -p no:cacheprovider tests` 191 통과(다른 에이전트가 작성 중인 `tests/test_jevl_client.py`는 모듈이 아직 없어 수집 오류 — 이 과제와 무관, 제외하고 셈).

### 계획과 다른 점
1. 카메라: ZED_M/63 mm 쌍 대신 cyclo 기본 머리캠(사용자 지시). 플래너 성공률 측정은 카메라 끔.
2. 머그는 YCB 메시가 아니라 원기둥(물리 판 404, 정본의 "머그/블록" 범위 안).
3. 섭동 코드는 계획 파일 목록대로 `perturb.py`에 뒀다(지시문의 "planner.py에 perturb"와 위치만 다름).
4. 그리퍼 보조 관절 게인을 cyclo 값에서 바꿨다(위 3번 수정). 탁상 높이 0.85 m.
5. 실행기 `harvest/sim/run_dev.py`를 추가했다(계획 목록에 없음, 파드 실행·DEV 시드 제한용).
