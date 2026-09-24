# 결정 질문 정답 v2: 관측 상태로 정한 라벨 (정본 §53 결정 2)

## 사전 등록 (정확도 계산 전 고정, 2026-09-24T15:06:16Z `date -u`)

작업 지시 요지(원문 뜻을 바꾸지 않음): 옛 오라클(계획기 **명령** TCP의 다음 0.33 s 이동, 명령 지연·타이머 의존 → 코드 규칙 상한 dir_xy 0.920 · dir_z 0.803 · mag 0.730, `e3lite.md`)을 버리고, 스냅샷의 **실제** 그리퍼·물체 자세만으로 정해지는 정답으로 바꾼다. S1 텍스트만 읽는 코드 규칙이 새 라벨을 질문별 ≥ 0.95로 재현해야 한다(게이트).

### 기호와 좌표계
- 틀 = 스냅샷 `state.obs.raw`의 테이블 틀(x·y = 로봇 기저 x·y, +x 앞, +y 로봇 왼쪽, z = 테이블 윗면 위 높이). 로봇 기저 틀과 z 원점만 다르므로 **변위 Δ는 기저 틀 값과 같다**.
- g = 실제 그리퍼 손가락 중점 `obs.raw.grip.pos`. 머그 o3 중심 m, 트레이 o5 중심 r = `obs.raw.objs[k].pos`. 반높이 h_m = o3 `he[2]`(0.0475), h_r = o5 `he[2]`(0.0075) — 상태에 있는 값(코드 규칙은 텍스트에 없으므로 같은 상수를 씀).
- 계약 단계 stage = 스냅샷 `phase`의 `stage_of`(S1 = approach·descend·close·lift, S2 = 나머지) — S0 텍스트의 `stage:` 줄과 같다.
- 그리퍼 상태 = S0 텍스트와 같은 규칙: `pred.gripper_open`이면 open, 아니면 `holding(o3)`이면 closed_holding, 아니면 closed_empty.

### 운동 소단계 M과 목표점 G (계획기 `_goal`과 같은 기하, 명령값이 아닌 실제 자세로)
계획기 FSM 단계(`phase`)는 S1 텍스트에 없으므로 소단계도 관측값으로 정한다(ALIGN = 1.5 cm = 계획기 `REACH_TOL_FAST_M`, 수평 거리 = xy 성분만):

| 조건 | M | G |
|---|---|---|
| S1, open, ‖(m − g)_xy‖ > ALIGN | approach | (m_x, m_y, m_z + h_m + 0.10) — 머그 윗면 위 10 cm |
| S1, open, ‖(m − g)_xy‖ ≤ ALIGN | grasp | (m_x, m_y, m_z + h_m − 0.018) — 패드 중심 = 윗면 아래 1.8 cm |
| S1, closed_holding | lift | (g_x, g_y, 0.20) — 운반 높이 `CARRY_TCP_Z` |
| S2, closed_holding, ‖(r − g)_xy‖ > ALIGN | carry | (r_x, r_y, 0.20) |
| S2, closed_holding, ‖(r − g)_xy‖ ≤ ALIGN | place | (r_x, r_y, g_z − ((m_z − h_m) − (r_z + h_r)) + 0.003) — 머그 바닥이 트레이 윗면 위 3 mm |
| S2, open | retreat | (g_x, g_y, m_z + h_m − 0.018 + 0.10) — 쥔 높이 + 10 cm(계획기 `retreat_z` = 놓을 때 TCP + 0.10과 같은 뜻을 물체 자세로) |
| closed_empty (S1·S2) | wait | g (움직임 없음: 손가락이 닫히는/여는 중이거나 빈 손) |

Δ = G − g.

### 라벨 (보기 키는 `jevcall` 그대로)
- **dir_xy**: 성분별 부호 s_x = sign(Δx) if |Δx| ≥ 1 cm else 0, s_y 같음. (0,0) → `none_xy`, 그 밖 (s_x, s_y) → `plus_x`·`plus_x_plus_y`·`plus_y`·`minus_x_plus_y`·`minus_x`·`minus_x_minus_y`·`minus_y`·`plus_x_minus_y` 중 하나(부호 패턴 그대로, 각도 양자화 아님).
- **dir_z**: |Δz| < 1 cm → `none_z`, 그 밖 Δz > 0 → `up`, < 0 → `down`.
- **mag_coarse**: n = ‖Δ‖(3D). 구간 중심 0.5 / 1 / 2 / 4 / 8 cm(tiny/small/medium/large/xlarge, `planner.MAG_BINS`), 경계 = 이웃 중심의 기하 중점 **√0.5 = 0.7071 cm, √2 = 1.4142 cm, √8 = 2.8284 cm, √32 = 5.6569 cm**. n < 0.7071 → tiny(0 포함), < 1.4142 → small, < 2.8284 → medium, < 5.6569 → large, 그 이상 → xlarge. (옛 오라클의 "0.25 cm 미만 tiny" 규칙은 쓰지 않는다.)
- **target**: stage S1 → `o3`(머그를 집어 드는 단계), S2 → `o5`(트레이에 놓는 단계). holding 술어는 target이 아니라 M(소단계) 선택에만 쓴다. 옛 오라클과 달리 lift(쥔 채 S1)는 o3.
- **phase** (키 continue/next/hold, 위에서부터 첫 해당):
  1. `hold`(멈춤): 그리퍼 closed_empty, 또는 S2에서 holding(o3)=no 이고 on(o3,o5)=no(불변식 깨짐, 종료 술어 불충족 — 머그를 놓쳤음).
  2. `next`: 현재 단계의 종료 술어가 모두 참(S1: holding(o3) ∧ lifted(o3); S2: on(o3,o5)), 또는 소단계 목표에 도달(dir_xy = none_xy 이고 dir_z = none_z).
  3. 그 밖 `continue`.
  술어 값은 스냅샷 `pred`(= S0 facts 줄) 그대로.
- **progress**: 옛 오라클 값 그대로(변경 없음).

### 게이트
- 코드 규칙 `code_rule_v2`: **S1 텍스트만** 파싱(`stage:`, `gripper=`, `facts:` 줄 + geometry 블록의 반올림된 cm 값). g = 텍스트 gripper x/y/z, 물체 중심 = g + 텍스트 오프셋. 같은 M·G·라벨 함수에 넣는다(상수 h_m 0.0475, h_r 0.0075).
- 대상: DEV 0–29 × P0/P1/P2 스냅샷 중 `oracle` ≠ null 전부(E3-lite와 같은 2,387개; `jevl_acc.snapshots`). 라벨 파일은 모든 줄에 쓴다.
- 판정: 질문별(dir_xy, dir_z, mag_coarse, target, phase) 정확도 ≥ 0.95. *(정정 2026-09-24T15:07:45Z, 어떤 정확도도 계산하기 전: 처음 적은 목록에 progress가 들어 있었으나 progress는 지시대로 "바꾸지 않음" = 옛 오라클 값(DEV 섭동 사건 창·실패 시각)이라 S1 텍스트로 정해지지 않고 직렬화 정밀도로 고칠 수 없다. 게이트에서 빼고, 코드 규칙(늘 `valid_progress`)의 일치율만 참고로 적는다 — E3-lite에서 이미 0.925로 알려진 값.)* 반올림 전 값 규칙(UB-raw)은 정의상 1.0이어야 한다(아니면 구현 결함).
- 미달 질문이 있으면 **라벨이 아니라 S1 직렬화 정밀도**를 고친다: 0.5 cm 단위 → 그래도 미달이면 mm. 한 번만 다시 돌리고 두 판 모두 보고한다. *(재실행 전 변경 2026-09-24T15:10:44Z, 1 cm 판 결과(dir_xy 0.944 · dir_z 0.856 · mag 0.932 미달, 원인 전부 반올림)를 본 뒤·재실행 전: 0.5 cm와 1 mm는 둘 다 소수 한 자리(`dx=+9.5` 대 `dx=+9.4`)로 찍혀 글자·토큰 수가 같으므로 0.5 cm를 거칠 이유가 없다. 지시문의 "한 번만 다시"를 지키려고 **재실행은 1 mm(`step_cm=0.1`) 한 번**으로 한다. 라벨 정의는 바꾸지 않는다.)* 잔차는 원인별로 센다: 1 cm 데드밴드 근처(참값 성분이 1 cm ± 반올림 반폭 안), 크기 구간 경계 근처, ALIGN 1.5 cm 근처(소단계 뒤바뀜), 그 밖.

### 함께 보고
1. 질문별 새 라벨 분포와 최빈 기준선.
2. 옛 오라클 라벨과의 일치율·혼동표(질문별), 소단계 M 대 계획기 `phase` 교차표.
3. 결과 기반 라벨과의 일관성: DEV 자체 점검 원자료(`/data/harvest/data/pool_selfcheck/dev*_P*.jsonl`, T14; 지시문의 `out/t13`에는 로그만 있음)에서 (seed, kind, k)로 맞춘 스냅샷의 질문별 "새 라벨 ∈ best 집합" 비율을 규칙별(plan·short1–3·time0.33·time0.66)로, 옛 오라클의 같은 비율과 나란히. 자체 점검은 편을 다시 돌린 것이므로 (seed, kind, k)의 `phase`·`t`가 같은 줄만 쓴다(다르면 수를 보고).

### 파일 규칙
- 라벨 파일: `/data/harvest/data/jsel_dev/{P0,P1,P2}.labels_v2.jsonl`(종류별 한 파일, 스냅샷 디렉터리 옆). 원본 `P*/ep*.jsonl`은 수정하지 않는다. `P*/` 안에 `ep*.labels_v2.jsonl`로 두면 `jevl_acc.snapshots`·`train/stagea_data.py`의 `ep*.jsonl` 글롭이 걸려 파일 이름 정수 변환에서 깨지므로 이 위치를 택했다(데이터 보기 전 결정).
- CPU 한 프로세스, `nice -n 10`. DEV 시드만.

---

## 결과 (2026-09-24T15:13Z 작성)

### 요약
- **게이트 통과 (1 mm 직렬화)**: S1 텍스트만 읽는 코드 규칙 = dir_xy **0.9954** · dir_z **0.9908** · mag_coarse **0.9883** · target **1.0000** · phase **0.9992** (2,387 스냅샷). 1 cm 판(E3-lite S1 그대로)은 dir_xy 0.9439 · dir_z 0.8559 · mag 0.9317 미달(target 1.0 · phase 0.9527 통과) → 사전 규칙대로 **라벨은 두고 직렬화만 1 mm**로 바꿔 한 번 재실행.
- 남은 오차는 전부 반올림: 0.1 mm 격자(진단, 판정 밖)에서 dir_xy·mag·target·phase·소단계 1.0000, dir_z 0.9996(1건, 참 Δz 9.98 mm가 데드밴드 1 cm 바로 아래) → 정의·구현 결함 없음.
- 옛 오라클과 일치: dir_xy 0.816 · dir_z 0.894 · **mag 0.269** · target 0.818 · phase 0.678 · progress 1.0.
- 결과 기반 라벨(자체 점검 91 스냅샷): 계획서 규칙 `plan`에서 새 라벨 ∈ best 0.945–1.0(옛 오라클 0.978–1.0). 판별력 있는 규칙(time0.33·time0.66)에서는 새 라벨이 5질문 평균으로 옛 오라클보다 약간 높고(0.840 대 0.826, 0.906 대 0.884), mag에서 크게 높다(0.879 대 0.692, 0.923 대 0.747). phase는 옛 쪽이 높다.

### 1. 게이트 (코드 규칙 = S1 텍스트만, 대상 2,387 스냅샷)

| 직렬화 | dir_xy | dir_z | mag_coarse | target | phase | (소단계 M) | (progress, 게이트 밖) |
|---|---|---|---|---|---|---|---|
| 1 cm (E3-lite S1) | 0.9439 ✗ | 0.8559 ✗ | 0.9317 ✗ | 1.0000 | 0.9527 | 0.9954 | 0.9246 |
| **1 mm (`step_cm=0.1`, 재실행 1회)** | **0.9954** | **0.9908** | **0.9883** | **1.0000** | **0.9992** | 0.9992 | 0.9246 |
| 0.1 mm (진단, 판정 밖 — UB-raw 대용) | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9246 |

잔차 원인(규칙 ≠ 라벨 건수; "근처" = 참값이 문턱에서 인쇄 격자 1.5칸(크기는 2칸) 안):

| 직렬화 | dir_xy | dir_z | mag_coarse | phase |
|---|---|---|---|---|
| 1 cm | 데드밴드 131, ALIGN 3 | 데드밴드 336, ALIGN 8 | 구간 경계 152, ALIGN 11 | 도달 판정(데드밴드) 113 |
| 1 mm | 데드밴드 11 (place 4·approach 3·carry 3·grasp 1) | 데드밴드 20 (carry 18·place 2), ALIGN 2 | 구간 경계 26 (grasp 13·lift 7·place 3·carry 2·retreat 1), ALIGN 2 | 도달 판정 2 |

"그 밖" 원인은 두 판 모두 0건. 1 cm 판 최다 오차는 carry의 dir_z(182건)와 grasp의 dir_z·phase(각 92건).

- **주의(라벨 성질)**: carry에서 실제 그리퍼는 명령 높이 20 cm보다 약 0.4–1.1 cm 낮게 간다(Δz 5–95백분위 0.39–1.14 cm, 중앙 0.74 cm). carry 297건 중 41 %가 Δz 0.8–1.2 cm로 데드밴드 경계에 붙어 있어, carry dir_z(none_z 234 / up 63)는 mm 단위 흔들림에 민감하다. 정의는 사전 등록대로 두고 기록만 한다.
- **직렬화 변경**: `harvest/e3lite.py`의 `geometry_block`·`state_text`에 `step_cm` 인자 추가(기본 1 = E3-lite S1 바이트 동일, 기존 테스트 통과). 1 mm 판은 `dx=+9.4` 식 소수 한 자리. 결정층 SFT 입력 S1은 **`step_cm=0.1`**을 쓸 것.

### 2. 새 라벨 분포 (2,387 스냅샷; 최빈 기준선)

| 질문 | 분포 | 최빈 |
|---|---|---|
| dir_xy | none_xy 1,771 · plus_x_plus_y 211 · plus_x_minus_y 169 · minus_y 96 · plus_y 85 · minus_x 26 · minus_x_plus_y 15 · minus_x_minus_y 12 · plus_x 2 | 0.742 |
| dir_z | down 1,185 · up 748 · none_z 454 | 0.496 |
| mag_coarse | xlarge 1,441 · large 460 · medium 246 · small 129 · tiny 111 | 0.604 |
| target | o3 1,472 · o5 915 | 0.617 |
| phase | continue 1,775 · next 593 · hold 19 | 0.744 |
| progress (그대로) | valid_progress 2,207 · allowed_change 180 | 0.925 |
| 소단계 M (참고) | grasp 664 · lift 510 · place 429 · carry 297 · approach 293 · retreat 176 · wait 18 | 0.278 |

최빈 기준선 평균: 게이트 5질문 0.641, 6질문 0.688(옛 라벨 6질문 0.669).

### 3. 옛 오라클과의 일치·혼동 (옛 → 새, 건수)

| 질문 | 일치 | 주요 불일치 |
|---|---|---|
| dir_xy | 0.816 | plus_y→plus_x_plus_y 127, minus_y→plus_x_minus_y 73, minus_y→none_xy 55, plus_y→none_xy 42, none_xy→plus_y 40, none_xy→minus_x 20 (각도 양자화 → 부호 패턴, 명령 지연) |
| dir_z | 0.894 | down→none_z 83, none_z→up 79(carry: 실제 높이 < 20 cm), none_z→down 45, down→up 28, up→none_z 19 |
| mag_coarse | **0.269** | medium→xlarge 848, medium→large 376, large→xlarge 99, tiny→small 86, small→xlarge 65 (옛 = 0.33 s 한 스텝 이동량, 새 = 목표까지 남은 거리 → 뜻이 다른 양) |
| target | 0.818 | o5→o3 434 (lift: 옛 오라클은 lift를 o5로, 새 정의는 S1 = o3) — 그 밖 불일치 0 |
| phase | 0.678 | next→continue 398, continue→next 352(S1 종료 술어 holding∧lifted가 lift 중간에 참이 됨 등), continue→hold 16, next→hold 3 |
| progress | 1.000 | — |

소단계 M 대 계획기 phase: descend→grasp 569, lift→lift 426, place_descend→place 369, carry→carry 297, approach→approach 276, open→retreat 102, close→lift 84(닫힌 뒤 holding 참), close→grasp 80(아직 open 판정), retreat→retreat 74, carry→place 32(트레이 위 1.5 cm 안), open→place 28(아직 holding), descend→approach 17(섭동으로 머그가 1.5 cm 넘게 밀림), approach→grasp 15, wait 18(open 10·lift 4·place_descend 3·close 1).

### 4. 결과 기반 라벨과의 일관성 (DEV 자체 점검)
- 원자료: 지시문의 `/data/harvest/out/t13`에는 로그뿐. 사전 등록에 적은 `/data/harvest/data/pool_selfcheck/`는 이 작업 중(00:09 KST) 다른 작업의 자체 점검 재시작(`self4_*`, 풀 재생성)으로 비워지고 이전 판이 `/data/harvest/data/pool_superseded_liftcut/v2_run2_partial/selfcheck/`로 옮겨졌다(그 작업의 SUPERSEDED 설명: "재실행 위치 오차 필드 없음"). **그 옮겨진 판**(DEV 0·8·15·23 등, 548행)을 읽기만 했다.
- 맞춤: (seed, kind, k) 일치 + 계획기 phase·t 같음 → **91 스냅샷 × 5질문 = 455행**(phase/t 다른 35행 제외). 자체 점검은 편을 다시 돌린 것이라 상태가 jsel_dev와 비트 단위로 같다는 보장은 없다.

| 규칙 | dir_xy 새/옛 | dir_z 새/옛 | mag 새/옛 | target 새/옛 | phase 새/옛 | 5질문 평균 새/옛 | best 크기/보기 수 (dir_xy) |
|---|---|---|---|---|---|---|---|
| plan (계획서) | 0.978 / 0.978 | 0.978 / 0.978 | 0.978 / 0.989 | 1.000 / 1.000 | 0.945 / 1.000 | 0.976 / 0.989 | 0.98 |
| short3 | 0.637 / 0.626 | 0.714 / 0.813 | 0.725 / 0.549 | 0.824 / 0.890 | 0.571 / 0.648 | 0.695 / 0.706 | 0.35 |
| short2 | 0.703 / 0.736 | 0.681 / 0.769 | 0.769 / 0.571 | 0.846 / 0.901 | 0.560 / 0.637 | 0.712 / 0.723 | 0.30 |
| short1 | 0.571 / 0.615 | 0.670 / 0.736 | 0.670 / 0.451 | 0.714 / 0.747 | 0.396 / 0.429 | 0.604 / 0.596 | 0.15 |
| time0.33 | 0.813 / 0.846 | 0.912 / 0.934 | 0.879 / 0.692 | 0.967 / 1.000 | 0.626 / 0.659 | 0.840 / 0.826 | 0.71 |
| time0.66 | 0.956 / 0.956 | 0.945 / 0.967 | 0.923 / 0.747 | 1.000 / 1.000 | 0.703 / 0.747 | 0.906 / 0.884 | 0.90 |

- 읽기: `plan`은 best가 거의 전 보기(dir_xy 98 %)라 둘 다 자명하게 높다. 판별력 있는 규칙에서 새 라벨은 **mag에서 확실히 결과와 더 맞고**(남은 거리가 크면 크게 움직이는 보기가 빨리 끝남), dir_z·target·phase는 옛 오라클보다 조금 낮다(phase: lift 중 S1 종료 술어로 `next`가 되는 경우 등; target: lift를 o3로 둔 정의). 결과 기반 규칙 선택(§48)은 아직 진행 중(`self4`)이라 이 표는 참고값이다.

### 파일·재현
- 코드(로컬 D:\qdd, 커밋 안 함): 새 `harvest/labels_v2.py`(순수 함수 `goal_point(phase, state)`·`delta`·`motion_phase`·`dir_xy_label`·`dir_z_label`·`mag_label`·`target_label`·`phase_label`·`labels`·`code_rule_v2`), `tests/test_labels_v2.py`(12, 먼저 실패 확인 뒤 구현), `tools/labels_v2_eval.py`; 수정 `harvest/e3lite.py`(`step_cm`, 소수 파싱; 기본 동작 불변).
- 파드: 코드 사본 `/data/harvest/code_labels_v2/`(공용 `code`는 건드리지 않음). 결과 `/data/harvest/labels_v2/eval_step1.json`(1 cm) · `eval_step01.json`(1 mm, 판정) · `eval_step01_outcome.json`(1 mm + 자체 점검 대조) · `diag_step001.json`(0.1 mm 진단), 각 `*_mismatch.jsonl`. 라벨 `/data/harvest/data/jsel_dev/{P0,P1,P2}.labels_v2.jsonl`(825/841/826줄 = 원본 2,492줄 전부, `oracle` null 줄 포함; 원본 `P*/ep*.jsonl`은 그대로).
- 실행: `nice -n 10` CPU 1프로세스, GPU 안 씀. `/data` 밖 파드 파일 없음.
