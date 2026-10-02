# 외부 검토 1차 (ext1, 10-03 04:30 KST) — 휴머노이드 팔 조작 방법·평가 감사

범위: 코드(dev 0776749 harvest/l9) 읽기 + 파드 원자료 집계. 팀 추론 문서는 읽지 않음. 사용자 토큰 절약 지시로 **시험(A/B)은 하지 않고** 근거·가설만 넘긴다.
집계 도구: e9f3b `/data/harvest/l9v2/ext1/` (census.py → census.tsv: l9v2·out/l9 아래 collect 142개, R1 1,469편·G1 280편; agg.py, drop.py).

## 1. 평가 감사 (가장 큰 발견)
- **"0 %(시도 ≥5) = 그 로봇 불가" 판정이 다단계 정의에서 통계적으로 무의미**. AIW 자신도 이 정의들에서 4–6 %:
  clear_to_basket_second 8/189, stack_then_in 4/100, tidy_pack_lunch 6/117, in_two_same 4/71, tidy_trash_two 14/138, tidy_picnic·tidy_toys_away AIW 도 0.
  R1 시도 수에서 AIW 성공률이면 0 성공이 나올 확률: stack_then_in 0.69, tidy_pack_lunch 0.62, clear_to_basket_second 0.57, tidy_trash_two 0.42, sort_size 0.15, in_two_same(37편) 0.12, kit_serve_two 0.11, up_two·down_two 0.10.
  → R1 제외 15개 중 **≥8개는 "R1 이 못 함"이 아니라 "파이프라인 공통으로 다단계가 약함 + 표본 작음"**. 판정은 정의별 n 을 AIW 비율에서 P(0)<0.05 가 되게(예: p=5 %면 ≈60편) 정하거나, 로봇 간 비교(같은 정의, 비율 차 검정)로 해야 함.
  G1 은 8개 중 tidy_clear_and_stack(0.68) 1개만 해당, 나머지 7개(AIW 32–70 %)는 실제 결함.
- **gate_now.json 은 모든 변형 합산**(events 699 "전 변형 합산"): lean 0.4/0.6, GAPJUDGE(해로움 판정됨), badlaunch 등 이미 버린 설정의 편이 정의별 분모에 섞임 → 현재 코드의 능력이 아님. 판정은 현행 코드 sha·설정 행만으로.
- **result.json `knocked` 가 다단계에서 오염**: harness 는 마지막 대상 하나만 추적해 앞 단계에서 일부러 옮긴 대상도 "knocked/collision" 으로 셈(예: r1own/vL8 in_two_same_s3960152: 첫 대상 199 mm 이동 = 정상 운반인데 knocked). R1 2단계 실패의 45 %(123/271)가 knocked=1 → 이 지표로 다단계 원인을 추론하면 틀림.
- **VLM 라벨 결함**: 왼팔 편의 prompt 첫 줄이 "You control the right arm"(R1 r1sweep 표본 5/5, vL8 예시 동일, meta arm=left). L9 원칙(VLM 혼란 금지) 위반 — 빌드 전 확인 필요.

## 2. 실측 분해 (R1, 전 변형)
- 단계 수별 성공: 1단계 478/1124 (42.5 %), 2단계 52/324 (16 %), 3단계 0/21.
- 2단계 실패 272: 두 번째 집기까지 가서 place 실패 118, 첫 집기 approach 실패 74, 첫 집기 place 68.
- 예시 in_two_same_s3960152: 2번째 물체 운반 중 첨부(attach) 계획 실패 → 첨부 없이 재계획(carry_fallback k=1) 6회, held_move_failed 22, lower_open "no collision-free path" 반복 → 같은 그릇(이미 1번 물체가 들어 있음) 위 같은 xy 로 내려가다 51 mm 앞에서 막힘.

## 3. 가설 (humanoid_failed.md 와 겹치지 않음, 미시험)
| # | 가설 | 근거 | 범용 수정(측정값만) |
|---|---|---|---|
| H1 | cuRobo `cspace.default_joint_position` 이 R1·G1 팔은 **전부 0**(팔 쭉 편 특이 자세). cuRobo 0.8 에서 이 값은 trajopt/MPC 초기 action mean 으로 쓰임(코드 확인), IK 정규화 목표(retract)로 쓰이는지는 미확인. AIW(-1.05,1.10,-1.23,-2.39…)·Franka(표준 ready)는 굽힌 자세 | assets9/curobo/{r1pro,g1}_*.yml vs ffw_sg2/franka; pylib curobo `robot_state_transition.init_action_mean`, `PositionCSpaceCost` target term | 모든 로봇 default = 그 로봇 실측 ready 관절(ready_ik 최대여유 가지 또는 시뮬 시작 자세)로 빌드 — build_curobo9 공통 |
| H2 | 다단계 두 번째 놓기: 같은 용기·같은 place xy 로 두 번째 물체를 내림(첫 물체 위) + 첨부 계획 실패 시 첨부 없이 운반 → 첫 물체·이웃 침범 | 위 예시, 2단계 place 실패 118 | place xy 를 용기 안 빈 칸(점유 상자 제외)으로 — AIW 다단계 4–6 % 도 같이 올라야 정답 |
| H3 | 판정 n 부족(1절) — 수정이 아니라 평가 규칙 | 1절 | 정의별 최소 n = AIW 비율 기준 P(0)<0.05 |
| H4 | `_valid` 의 후보 IK(16 시드, 시드 무작위)는 도달만 보고 그 가지를 버림; 실제 접근은 plan_pose 가 다른 가지를 고름 → 직선 접근·들기에서 관절 한계(R1 은 REVERSE_APPROACH 로 땜질) | rt9._valid / plan9.ik·pose | 후보 IK 해를 plan 의 goal 시드로 넘김(공통) |

추천 순서: H3(평가, 즉시·무비용) → H1(설정 1줄급, ≥20편 A/B, AIW/Franka 비열등 확인) → H2 → H4.
