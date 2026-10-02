# L9 v2 필터 감사 (후보/장면을 거르는 모든 수정, 10-03 03시 사용자 지시)

실행: 2026-10-03 03:20 KST, juhyoung-native-7a2a, `/data/harvest/venv_sam3/bin/python` (CPU).
데이터: `/data/harvest/l9v2/{pilot1,pilotF,pilotR,pilotG,r1sweep,g1fix,g1F,g1J,r1own/*}/collect/train/*/*/{skipped.json,meta.json}`
(최종 성공편은 `meta.json`만, 건너뛴 행은 `skipped.json`만 — 한 편당 둘 중 하나) + `/data/harvest/l9v2/prefilter/*.dropped.json` vs 그 옆 kept plan json.
도구: 스캔 스크립트는 파드 `/data/harvest/out/l9/faudit/{faudit_main.py,prefilter_scan.py,ab_vfin.py,r1sweep_focus.py}`.

**한계**: `skipped.json`의 `row`는 사전 계획 필드(seed·robot·arm·family·rule·def·task_family)만 가진다 — 장면이 완성되기 전에 걸러지므로 실제 table_z·목표 x/y·접근군·회전 bin은 없다. 이 값들은 kept(`meta.json`)에만 있다. 그래서 REMOVED 쪽은 환경군(family)·규칙(rule)·과제군(task_family)·로봇·팔로만 분해하고, "높이/접근/회전 다양성이 좁아졌는가"는 KEPT 쪽 분포(§6 다양성 관문과 동일 방식)로 답한다. 목표 base-frame x/y는 `robot_pose.distance/yaw`(극좌표 대용)로 근사했다.

## 0. 전체 규모
전수(17개 런 풀링): kept 22,283편, removed 15,483행. removed 필터별: DEFFIT(장면에 과제 안 맞음, 조합 소진) 52.4 %, **GRASPCHK**(첫 목표 유효 잡기 없음) 42.0 %, **REACH**(표면/몸통 자세가 로봇 도달대 밖) 3.6 %, HEADVIEW(목표가 머리캠 밖) 1.0 %, LIFT(리프트 축 미적용) 0.07 %.

## 1. GRASPCHK — "no valid grasp" (`rt9.py:500`, `SkipScene: v2: no valid grasp of the first target`)
removed 6,505건. 로봇별 제거율(=removed/(removed+kept), 같은 차원의 kept 모집단 대비):

| 로봇 | removed | kept | 제거율 |
|---|---|---|---|
| g1 | 270 | 72 | **78.95 %** |
| ffw_sg2 | 5,400 | 13,391 | 28.74 % |
| r1pro | 165 | 809 | 16.94 % |
| franka_mast | 670 | 8,011 | **7.72 %** |

G1 제거율이 Franka의 **10배**. 팔: left 30.96 % vs right 18.21 % (1.7배, 왼팔이 더 많이 걸러짐). 과제군: `transfer`(건네기류) **52.55 %** 제거로 최고치(다음 `insert` 26.78 %, 나머지 16–24 %) — transfer가 다른 과제군보다 2–3배 더 많이 잘려 나감. 환경군: cafe_counter 34.6 %·pantry_shelf 32.4 %·kitchen 27.4 % 상위, 가장 쉬운 축(평평한 긴 테이블류)은 15–18 %대.
**깃발**: G1·왼팔·transfer·조밀한 선반형 환경(어려운 쪽)이 불균형하게 제거됨 — §6 "어려운 동작만 걸러서 25 % 얻으면 안 됨" 위반 소지. G1은 이미 25 % 관문 미달(아래 §5)이라 이 필터가 원인의 상당 부분.

## 2. REACH — 표면/도달대 밖 (`world9.py:858-890`, `r1_band.py`, `reach9.py`, G1 `L9V2_G1_REACH/SURF`, R1 `r1_scene_reach`/band)
removed 554건, **r1pro·g1 전용**(ffw_sg2·franka_mast는 이 체크 대상 아님 → 두 로봇은 REACH로 전혀 안 걸림). r1pro 38.67 %, g1 37.93 % 제거율. 팔: 전체 풀(여러 런 혼합)에서 left 4.77 % vs right 1.35 %(3.5배) — 단 r1sweep 단일 런만 보면 방향이 반대로 뒤집힘(right 45.9 % vs left 34.4 %, N=225/107 vs 225/118), 즉 **런(기울기 lean 값 등)에 따라 어느 팔이 더 걸리는지가 달라짐** — 단일 원인이 아니라 환경 조합 의존.
과제군: `relation`(5.94 %)·`select`(4.23 %)·`arrange`(3.96 %)가 상위, `transfer`(1.08 %)·`sort`(1.12 %)는 하위.
**KEPT 쪽 결정적 증거**: r1pro·g1의 kept `table_z` 밴드에 **shelf(≥0.95 m)가 0 %** (ffw_sg2 4.44 %, franka_mast 4.66 %). r1sweep 단일 런도 동일(0건). REACH가 정확히 "높은 선반 놓기"를 통째로 걸러내고 있음 — §6 다양성 비열등 관문 직접 위반(AIW·Franka 대비 좁음). 사용자 메모 (2)번 질문("R1 높은 놓기 0 %")에 대한 답 = **확인됨, 0 %**.

## 3. PLACECHK + LIFTSKIP (커밋 51c6f1f, `IR_L9_R1_PLACECHK`/`IR_L9_R1_LIFTSKIP`, 기본 꺼짐) — A/B: r1own `vAll`(둘 다 OFF) vs `vFin`(둘 다 ON), 같은 LEAN=0.8·같은 잡 규모
| | vAll | vFin |
|---|---|---|
| 총 행 | 178 | 173 |
| kept | 36 | 34 |
| GRASPCHK 제거 | 7 | 8 |
| REACH 제거 | 35 | 36 |
| kept 성공률 | 63.89 % | 70.59 % |
| kept 팔 비율 | left 50.0/right 50.0 | left 44.1/**right 55.9** |
| 접근군(oblique/top/front/side) | 18/12/4/**2** | 17/12/4/**1** |

GRASPCHK·REACH 제거 건수는 거의 변화 없음(이 기능은 "없는 잡기를 생기게" 하는 게 아니라 "있는 잡기 중 place-IK 되는 것만 남기고, 실패한 lift_clear를 대체 경로로 우회"하는 것 — §2 코드 docstring 확인: PLACECHK는 "첫 집기에서 place-IK 없으면 → no valid grasp(= 같은 GRASPCHK 스킵)"로 떨어지므로 못 거른 몫이 GRASPCHK 쪽으로 넘어가는 구조). 성공률은 올랐으나(N=34–36, 표본 작아 노이즈 큼) **왼팔 비중이 50→44.1 %, side 접근 2→1건으로 둘 다 줄어듦** — 방향은 "어려운 쪽(왼팔·side)을 줄여 성공률을 얻는" 쪽. N이 너무 작아 확정 불가, **더 큰 N으로 재검증 필요**(깃발, 버리기 전 재검토 규칙에 따라 폐기 아님·보류).
`timeline.lift_clear_skipped` 카운터는 런타임 메모리에만 있고 `meta.json`에 저장되지 않아 발동 횟수 자체는 집계 불가(코드 확인: `rt9.py` self.timeline, build/export 경로에 없음) — 데이터 공백으로 기록.

## 4. 프리필터 재추첨 (`tools/l9/prefilter9.py` dropped, `ystrat9.py` 재시딩)
145개 kept-plan 파일 기준: kept 53,569행, dropped 15,264행(전체의 **22.2 %**). 로봇·팔 비율은 kept/dropped 간 큰 차이 없음(팔: kept right 70.5 %/dropped right 74.0 %, 1.05배 — 왼팔이 상대적으로 덜 drop됨, 경미).
과제군 drop 쏠림(해당 과제군의 drop-점유율 / kept-점유율 비):
- `sort` 2.30x(dropped 17.82 % vs kept 7.75 %), `set` 2.36x, `insert` 1.63x, `tidy` 1.45x — **과대 제거**.
- `height`(기준 과제) 0.12x(dropped 0.88 % vs kept 7.57 %) — 거의 안 걸림, `transfer`도 0.50x로 보존됨.
규칙(furniture rule) drop 쏠림: `hutch` 2.8x, `stepped_display` 2.1x, `stepped2` 2.1x — **선반형·단차형(높은/복잡한) 가구가 2배 이상 더 많이 드롭**, `plain`/`tray`/`table` 같은 평평한 쪽은 비율 1배 안팎. §6 "어려운 동작·높은 위치가 좁아지면 안 됨"과 같은 방향의 위험 신호 — REACH 필터(§2)와 겹쳐 같은 방향(높은/단차 놓기 축소)으로 작용.

## 5. LIFT·CARRY류는 "행 제거"가 아님 (코드 확인)
- `IR_L9_R1_CARRY`(기본 "1"=켜짐): r1pro 캐리 간격을 편마다 (0.05, 0.10 m) 범위에서 무작위로 **뽑는** 파라미터(`robot9.V2_CARRY_CLEAR`) — 후보나 행을 버리지 않음, 집행 중 궤적만 바꿈. 분포 narrowing 측정 대상 아님.
- `L9_CARRY_INVIEW`(기본 꺼짐): 감사 대상 17개 런 전부 미사용 — 적용 사례 0, 측정할 분포 변화 없음.
- `LIFTSKIP`은 §3에서 다룸(행이 아니라 실행 스텝 대체).
- `LIFTOK`/`LCSKIP`(r1b 레인, 커밋 2cd7a55/801f739)은 `r1own`보다 앞선 별도 실험 레인으로 51c6f1f에 흡수·대체됨, `/data/harvest/l9v2`에 populated된 collect/train 데이터 없음(별도 `r1b` 트리, 이번 감사 범위 밖) — 흔적만 기록.

## 6. 사용자 메모 추가 3문항(10-03 03시) 답
1. **좌/우 대칭(서는 자리 기준)**: kept 행의 팔 선택(= 물체가 놓인 쪽) 비율 — r1pro left 61.3 %/right 38.7 %, g1 right 59.7 %/left 40.3 % (r1sweep 단독: left 64.1 %/right 35.9 %). **대칭 아님**, 로봇마다 방향도 다름 — 장면 생성이 좌/우로 균등하지 않을 가능성, §6 "반반" 요구와 불일치.
2. **로봇 도달대 안 선반/높은 놓기 생성 여부**: r1pro·g1 kept shelf(≥0.95 m) = **0 %**(ffw_sg2·franka 4.4–4.7 %) — 생성이 안 되는 것으로 확인(§2).
3. **어려운 경우가 prefilter·도달 스킵으로 선제 제거되는지**: 그렇다 — REACH가 r1pro/g1에서만 표면 통째로 skip(37–39 %) + prefilter가 hutch/stepped류를 2배 이상 drop(§4), 둘 다 "높은/단차" 쪽을 양쪽에서 깎는 중복 효과.

## 7. 종합 깃발 (버리기 전 재검토 대상)
- **가장 큰 위험**: REACH + prefilter가 겹쳐 r1pro·g1의 "높은 놓기" 다양성을 AIW·Franka 대비 구조적으로 0으로 만듦 — §6 다양성 비열등 관문 위반 가능성 높음. 재검토: 도달대(reach_v2 band)·prefilter 규칙 중 하나를 완화해 높이 범위를 넓히고 A/B로 성공률 저하 확인 후 폐기/유지 재결정.
- GRASPCHK의 G1 10배·transfer 2–3배 쏠림은 "그 로봇/과제가 아직 서투르다"는 근본 신호와 겹쳐 있어 필터 자체보다 G1 손/카메라 문제가 선행 원인일 가능성 — §1 손 공통 층 수정과 함께 재평가 필요.
- PLACECHK+LIFTSKIP의 왼팔·side 감소는 N이 작아 미확정(tentative) — 더 큰 표본으로 재검증.
