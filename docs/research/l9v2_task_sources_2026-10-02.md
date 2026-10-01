# L9 v2 과제 정의 출처 표 (2026-10-02, L9v2-TASK)

- 사용자 결정(10-02 02시 KST): "여러로봇으로해서 l9으로 가고 그 테스크의 다양성 자체를 지금보다도 훨씬 더 가져갈 수 있으면 좋을 것 같네". 메인 지시: 관문 통과 정의 ≥ 150, 계열 9개보다 많이, 출처는 공개 벤치·데이터셋 과제 목록(상상으로 만들지 않음), 한 팔·우리 명령 형식으로 되는 것만, 관절 물체는 다음 후보.
- 코드: `harvest/l9/task9v2.py`(정의·출처·장면 제약·놓기 자세·done·지시문 변주), `harvest/l9/alloc9.py`(로봇·정의 배분), `harvest/l9/task9.py`(grip_max 인자, v2 갈래), `tools/l9/plan.py v2`, `tools/l9/task_diversity.py`, `tools/l9/v2_hostable.py`, 시험 `tests/l9/test_task9v2.py`.
- 설계 원칙 §12.11-1(벤치 저격 금지)에 따라 **과제 '유형'만** 가져왔다. 장면·자산·배치·지시문은 우리 생성기가 따로 만든다. 지시문은 우리 문장 틀(정의당 ≥ 5개) + 물체 이름으로 채우며, 벤치 지시문 문자열(LIBERO bddl 이름·CALVIN 주석·SimplerEnv 프롬프트 52개)과 정규화 후 완전히 같아지면 다음 문장 틀로 바꾼다(`BENCH_INSTR`, `avoid_bench`, meta `instr_meta.bench_clash_avoided`). n-gram 겹침 검사는 관문 쪽 몫으로 남긴다.

## 1. 출처 목록 (GitHub API 2026-10-02 확인)

| 키 | 과제 목록 | 논문 · 날짜 | 저장소 · 별 · 라이선스 | 구분 |
|---|---|---|---|---|
| RT2 | RoboTwin 2.0 50과제(envs/*.py) | arXiv 2506.18088 · 2025-06 | RoboTwin-Platform/RoboTwin · 2,935★ · MIT | 1.5년 이내 |
| RC | RoboCasa atomic `PickPlace*` 19종 + composite 활동 60종 | RSS 2024 (arXiv 2406.02523) | robocasa/robocasa · 1,773★ · NOASSERTION | [기초] |
| B1K | BEHAVIOR activity manifest(100개) | CoRL 2022 | StanfordVL/BEHAVIOR-1K · 1,732★ · MIT | [기초] |
| LIB | LIBERO object/spatial/goal/10 bddl 이름 | NeurIPS 2023 | Lifelong-Robot-Learning/LIBERO · 2,373★ · MIT | [기초] |
| CAL | CALVIN 34과제(new_playtable_validation.yaml) | RA-L 2022 | mees/calvin · 996★ · MIT | [기초] |
| RLB | RLBench 100과제 | RA-L 2020 | stepjam/RLBench · 1,823★ · NOASSERTION | [기초] |
| VIMA | VIMA-Bench 17 메타 과제 | ICML 2023 | vimalabs/VIMABench · 328★ · MIT | [기초] |
| SIMPLER | SimplerEnv(Google robot·WidowX) | CoRL 2024 (arXiv 2405.05941) | simpler-env/SimplerEnv · 1,174★ · MIT | [기초] |
| BRIDGE | BridgeData V2 기술 목록 | CoRL 2023 | rail-berkeley/bridge_data_v2 · 292★ · MIT | [기초] |
| DROID | DROID 동사 분류 | RSS 2024 | droid-dataset/droid · 446★ | [기초] |

- 라이선스와 무관하게 과제 아이디어만 인용한다(코드·데이터·자산 복사 없음).
- v1 108개 정의는 설계 §3에서 우리가 직접 쓴 것이다. 표에서는 `v1` + 계열별로 가장 가까운 공개 과제(`V1_SOURCES`)를 붙였다.

## 2. 포함 기준과 제외(다음 후보)

- 포함: 한 팔, 한 편 안에서 (대상, 놓을 곳[, 오프셋]) 단계로 컴파일되는 것. 단계마다 잡기 점(잡을 부위) + 접근 방향 + 손목 회전 + 높이 의도 + 그리퍼 열기/닫기로 표현할 수 있어야 한다.
- 능력이 더 필요한 정의는 `extra.requires`로 표시하고, 계획(`plan.py v2 --caps`)은 그 능력이 켜졌을 때만 넣는다.

| 능력 | 뜻 | 정의 수 | 누가 |
|---|---|---|---|
| `node:shelf` | 위가 막힌 칸 노드(shelf·shelf_high·shelf_low·wall_shelf·cupboard, 또는 노드 `blocked_above`/`clear_above` < 0.25 m) | 20 | L9v2-ENV(scene9) |
| `exec:approach_front` | 앞 접근 잡기·놓기 | 20 | 주인(world9·grasp9) |
| `exec:movable_container` | 그릇·머그를 동적 물체로 옮기기(테두리·벽 잡기) | 11 | 주인 |
| `exec:place_pose` | 6-DoF 놓기 자세(눕힘·기대기·방향) | 10 | 주인 |
| `exec:start_pose` | 누운 채 시작 | 1 | 주인(world9 spawn) |
| `exec:recovery` | 놓기 교란(빗나감·기울어짐) 뒤 재잡기(recovery 계열) | 8 | 주인 |
| `exec:push` | 닫은 손가락으로 밀기(L8S xnew.plan_push) | 6 | 주인 |
| `asset:ring_peg` | 고리·말뚝 자산(L8S xring) | 1 | ENV/자산 |
| `node:drawer_open` | 열린 서랍 노드(L8S xart A) | 1 | ENV |

다음 후보(지금 제외, `NEXT_CANDIDATES`):

| 출처 | 과제 | 제외 이유 |
|---|---|---|
| RC | CounterToMicrowave/Oven/ToasterOven/Drawer/Fridge*, doors, drawers, 손잡이·노브 | 관절 물체 |
| CAL | open/close_drawer, move_slider_*, lightbulb·led 스위치, push_*_block, push_into_drawer | 관절·밀기 |
| LIB | open drawer, turn on stove, push plate, 전자레인지 넣고 닫기 | 관절·밀기 |
| RT2 | open_laptop, open_microwave, click_bell/alarmclock, press_stapler, turn_switch, stamp_seal, beat_block_hammer(도구), shake_bottle*, rotate_qrcode, scan_object, hanging_mug(걸기 자세) | 관절·도구·손 안 조작 |
| RT2 | handover_*, lift_pot, pick_dual_bottles, place_dual_shoes, grab_roller | 두 팔(2단계) |
| RLB | put_item_in_drawer, put_bottle_in_fridge, put_tray_in_oven, open/close_*, wipe_desk, sweep_to_dustpan | 관절·닦기·쓸기 |
| BRIDGE / DROID | fold, wipe, sweep, pour, open/close, turn | 변형체·접촉 동작·액체 |
| B1K | cleaning_*, mopping, vacuuming, washing_*, opening_packages, installing_* | 닦기·액체·조립 |
| — | 재질 조건 고르기(금속·유리) | 카탈로그에 재질 표지가 없음 |

## 3. 정의 수 (전 → 후)

| 계열 | v1 | 추가 | 합계 | 비고 |
|---|---|---|---|---|
| insert | 11 | 6 | 17 | 고리 끼우기 포함 |
| arrange | 12 | 8 | 20 | 가장자리·깊은 뒤·좁은 틈·앞뒤 3줄·대각·색 3줄 |
| stack | 17 | 6 | 23 | 받침 위 탑 2·3층, 책 위, 색 짝, 내려서 통에, 쌓고 둘 넣기 |
| sort | 14 | 5 | 19 | |
| put_in | 10 | 1 | 11 | 열린 서랍 |
| set | 9 | 6 | 15 | |
| clear | 14 | 5 | 19 | |
| relation | 11 | 5 | 16 | |
| height | 10 | 3 | 13 | |
| shelf (신규) | — | 12 | 12 | 전부 `node:shelf` 필요 |
| select (신규) | — | 13 | 13 | 색·크기·범주 조건 |
| tall (신규) | — | 8 | 8 | 키 큰 물체(옆 잡기 후보) |
| hollow (신규) | — | 10 | 10 | 그릇·머그 테두리 잡기 |
| pose (신규) | — | 10 | 10 | 눕힘·기대기·방향·세우기 |
| kitchen (신규) | — | 8 | 8 | 싱크·도마·건조대 |
| tidy (신규) | — | 13 | 13 | 2~3개 순서 |
| transfer (신규) | — | 12 | 12 | 용기·칸 사이 옮기기, 받침 → 접시 |
| recovery (신규) | — | 8 | 8 | 놓기 교란 뒤 바로잡기 |
| push (신규) | — | 6 | 6 | 닫은 손가락 밀기(L8S pu__) |
| **합계** | **108 (9계열)** | **145** | **253 (19계열)** | 지금 능력으로 돌 수 있는 것 200, 능력 필요 53 |

- 단계 수: 1단계 177, 2단계 62, 3단계 14(여러 단계 76개 = 30 %).
- 문장 틀: 1,268개(신규 727). 지시문 변주: 감싸기 8종(40 %는 그대로), 방향 지시 문장 4종 × 4방향.

## 4. 단계 정보(step_info)·done·지시 방향

- `task9.instantiate(..., grip_max=<로봇 최대 벌림>, v2=True)` → 편에 `step_info[]`, `done`, `instr_meta`, `movable_containers`, `start_poses`, `requires`를 더한다(collect9가 meta에 기록). 기본값이면 v1 편과 바이트 단위로 같다(`tests/l9/fixtures/task9_v1_golden.json`, 장면까지 저장해 다른 에이전트의 scene9 변경과 무관).
- 그리퍼 폭: AI Worker 0.107, Franka 0.08 m(robot9 값). R1 Pro 0.10, G1 0.06은 **[가설]**(robot9에 `grip_max(robot)`가 생기면 그 값을 먼저 쓴다). 옮기는 물체의 `grasp_width`가 최대 벌림 − 1.4 cm를 넘으면 그 로봇 편에서 뽑지 않는다(테두리 잡기 대상 제외). 카탈로그 대상의 33 %가 Franka 한계를 넘는다.
- 장면 제약(`constraint`, 우선순위 순): `blocked_above`(시작 노드가 선반류·`clear_above` < 0.25 m) > `wide_hollow`(그릇·머그 계열이고 잡는 폭 > 최대 벌림 − 2 cm) > `tall`(높이 ≥ 15 cm 또는 높이/폭 ≥ 1.6) > `handle`(머그·컵, handle_ratio ≥ 1.6) > `flat`(높이 ≤ 3.5 cm). 기준값은 모두 **[가설]**(시범 G1·G2 프레임으로 확인).
- 놓기: `place_pose`{kind: upright|lying|leaning|oriented, yaw(rad, 월드)·delta_yaw·tilt_deg·against, support}, `place_approach`(top|front|side; 위가 막힌 노드면 front), `place_point`(surface_point|front_edge|inner_wall|container_opening|container_top|object_top), `place_height`{z(바닥 기준), band(floor < 0.25 < low < 0.60 < mid < 1.10 < high < 1.35 ≤ above_eye **[가설]**), rel_main}, `height_intent`(놓기 = 받침 윗면 + 0.4–2 cm에서 놓음; high·above_eye·선반은 받침 윗면이 안 보일 수 있으므로 점은 **보이는 앞 가장자리**, 놓는 높이는 노드 top_z에서 가져옴).
- 눕힘 가능: 병·캔·상자·책·블록이고 높이/폭 ≥ 1.2. 기대기 가능: 책·상자 중 얇은 것(가장 짧은 반축 ≤ 0.45 × 가장 긴 반축, 높이 ≥ 6 cm). 방향 맞춤: 한 반축이 다음 반축의 1.3배 이상. 모두 **[가설]**.
- done(멈춤 술어): 단계마다 on_spot(점 4 cm 안·면 위)·on_surface(노드 위·half 안)·in_container·on_container·stacked_on + 자세 조건(눕힘 기울기 ≥ 70°, 기대기 10–40°·벽 접촉, 방향 yaw ± 20°, 꽂기 upright 한도) + "그리퍼를 놓았음". `done.stop_label`은 멈출 때 라벨 문장(모든 술어가 동시에 참일 때만).
- 복구: 모든 정의에 시드 해시로 약 15 % `recovery_candidate`(실행기가 할 수 있으면 적용) + recovery 계열 8개는 `step_info[i].recovery` = {kind: off_target(오프셋 5–9 cm, 방향은 시드 해시)|tilted(30–60°), teach: false, fix}. 실행기가 그 놓기를 일부러 어긋나게 하고, 다음 호출이 다시 잡아 바로잡는다. 라벨은 늘 올바른 목표(교란 동작은 가르치지 않음).
- 지시 방향 행: 시드·정의 해시로 약 20 %(4,000 시드에서 0.17–0.23 시험)에 `instr_meta.approach_candidate`를 정한다. 장면 제약이 허용하는 방향만(blocked_above → front·oblique·side, tall → side·front·oblique, wide_hollow → top·oblique·side, handle → side·oblique·top, flat → top·oblique). 실행 가능 여부는 주인의 잡기 선택기가 정하고, 되면 `task9v2.apply_approach(ep, approach)`로 문장(방향마다 4종, 앞/뒤 위치 해시)을 넣는다. 주인 v2plan.py에도 별도 20 % 동전(`INSTRUCTED_P`)이 있으므로 **둘 중 하나만** 써야 한다(이중 지시 방지).

## 5. 배분 (성공 15,000편, `alloc9.allocate`)

- 로봇: AI Worker 40 %(오른팔 55 % · 왼팔 45 %), Franka 20 %(오른팔만, §9.2), R1 Pro 20 %, G1 20 %(좌·우 반반).
- 정의마다 ≥ 60편(로봇 합), 남는 몫은 가중치로: v1 계열 1.0(주인 10-02 03시: relation·put_in도 같게 — L9 v2만으로 학습), 신규 계열 1.5, recovery 1.0, × (1 + 0.5 × (단계 수 − 1)) **[가설]**. 정의 하나의 몫은 로봇 비율대로 나누되 누적 로봇 합이 목표를 따르게 반올림한다(로봇 합 오차 0).
- 보류(학습 금지) 정의: 계열마다 최대 1개, 해시로 약 5 %(지금 10~11개) → 바닥 60편만, 계획 행 `split = holdout`.
- 계획 행 = ceil(성공 몫 / 시범 수율)(수율 없으면 0.6, 하한 0.3). 행에 robot·grip_max·arm·task_family·n_steps·recovery·requires·split을 적어 E-7,500 사전 검증의 부분 집합(다양성 축소·회복 유무·로봇 혼합)을 meta로 자를 수 있다.
- v2에서 옮길 물체는 자연 잡기(grasp9.natural_order) 계열 → (계열, 부위) 부류 → 물체 순으로 균등하게 뽑는다(`task9v2.balanced_pick`, 범주 단어 = l9cat). v1 경로는 그대로다.

### 5.1 배분표 — 지금 능력(능력 없음)

- 계획에 든 정의 181개 / 계열 14개, 정의당 60–116편(중앙 79), 60편 미만 0개, 정의별 편 분포 정규화 엔트로피 0.9989, 계열 엔트로피 0.9822.
- 로봇별 편: {'ffw_sg2': 6000, 'franka_mast': 3000, 'r1pro': 3000, 'g1': 3000}, 로봇마다 덮는 계열 수: {'ffw_sg2': 14, 'franka_mast': 14, 'g1': 14, 'r1pro': 14}.
- 보류(학습 금지): in_second_container, ins_from_block, kit_from_sink, rel_right, sel_bigger_in, sort_food_bowl_toy_side, st_tower3_stand, swap_levels, tall_between.
- 장면 없음(호환 배치 규칙 없음): ins_from_second, kit_sink_to_rack; 사전 점검 0회 성공으로 뺀 것: arr_colour_row3, arr_three_corners, clear_after_meal, clear_three_mixed, hol_bowl_next_to, hol_two_mugs_row, kit_serve_two, kit_sink_to_rack, pose_handle_right, pose_stand_up, rel_between_containers, rel_chain3, set_place_three, set_two_drinks, set_two_plates_drink, sort_book_toy, sort_colour3_bins, sort_drink_food, tidy_gift_basket, tidy_return_two, tidy_three_places, tr_out_two_containers.

| 계열 | 정의 | AI Worker | Franka | R1 Pro | G1 | 합계 |
|---|---|---|---|---|---|---|
| stack | 23 | 740 | 371 | 369 | 371 | 1851 |
| arrange | 18 | 590 | 297 | 295 | 296 | 1478 |
| clear | 16 | 531 | 265 | 266 | 265 | 1327 |
| sort | 15 | 512 | 257 | 256 | 256 | 1281 |
| select | 13 | 446 | 223 | 224 | 223 | 1116 |
| insert | 14 | 441 | 221 | 221 | 221 | 1104 |
| relation | 14 | 434 | 216 | 217 | 217 | 1084 |
| height | 13 | 409 | 203 | 204 | 203 | 1019 |
| transfer | 11 | 393 | 196 | 197 | 196 | 982 |
| set | 12 | 387 | 193 | 193 | 193 | 966 |
| tidy | 8 | 332 | 166 | 166 | 166 | 830 |
| put_in | 10 | 309 | 154 | 154 | 155 | 772 |
| tall | 8 | 276 | 138 | 138 | 138 | 690 |
| kitchen | 6 | 200 | 100 | 100 | 100 | 500 |

- 단계 수(편 가중): 1 68.2 %, 2 28.0 %, 3 3.8 %; 잡은 뒤 호출 수(놓기·다음 잡기, 2×단계−1 + 회복 2): 1 68.2 %, 3 28.0 %, 5 3.8 %; 정의 회복 편 비율 0.0 % (+ 모든 정의의 회복 후보 약 15 %).
- 놓기 자세(계획): upright 100.0 %; 놓기 접근: top 100.0 %; 놓는 곳 높이 종류: in_container 47.2 %, main 37.5 %, on_object 10.8 %, high 2.5 %, low 2.1 %.
- 자연 잡기 기대 분포(natural_v1, 카탈로그 후보를 계열 → 부류 → 물체 순 균등 추첨): 접근 oblique 37.2 %, side 33.1 %, top 29.8 %; 부위 body 89.3 %, handle 10.7 %. (top ≤ 50 % 관문 충족 예상)
- 문장 틀 906개, 문장 틀 × 감싸기 × 방향 문장 용량 123,216개(물체 이름 제외).

### 5.2 배분표 — 모든 능력이 켜졌을 때

- 계획에 든 정의 208개 / 계열 18개, 정의당 60–89편(중앙 70), 60편 미만 0개, 정의별 편 분포 정규화 엔트로피 0.9997, 계열 엔트로피 0.9756.
- 로봇별 편: {'ffw_sg2': 6000, 'franka_mast': 3000, 'r1pro': 3000, 'g1': 3000}, 로봇마다 덮는 계열 수: {'ffw_sg2': 18, 'franka_mast': 18, 'g1': 18, 'r1pro': 18}.
- 보류(학습 금지): hol_mug_in_bowl, in_second_container, ins_from_block, kit_from_sink, rel_right, sel_bigger_in, sort_food_bowl_toy_side, st_tower3_stand, swap_levels, tall_between.
- 장면 없음(호환 배치 규칙 없음): clear_leftovers_shelf, hol_bowl_in_shelf, in_open_drawer, ins_from_second, ins_from_shelf, ins_ring_peg, kit_sink_to_rack, pose_lay_in_shelf, pose_stand_in_shelf, shelf_by_colour, shelf_from_bin, shelf_high_put, shelf_high_take_down, shelf_low_put, shelf_low_take_up, shelf_put_in, shelf_take_out, shelf_tall_put, shelf_to_shelf, shelf_two_items, shelf_wall_put, sort_shelf_bin, tidy_clear_to_shelf, tidy_stock_shelf; 사전 점검 0회 성공으로 뺀 것: arr_colour_row3, arr_three_corners, clear_after_meal, clear_three_mixed, hol_bowl_next_to, hol_two_mugs_row, kit_serve_two, kit_sink_to_rack, pose_handle_right, pose_stand_up, rel_between_containers, rel_chain3, set_place_three, set_two_drinks, set_two_plates_drink, sort_book_toy, sort_colour3_bins, sort_drink_food, tidy_gift_basket, tidy_return_two, tidy_three_places, tr_out_two_containers.

| 계열 | 정의 | AI Worker | Franka | R1 Pro | G1 | 합계 |
|---|---|---|---|---|---|---|
| stack | 23 | 653 | 326 | 326 | 326 | 1631 |
| arrange | 18 | 516 | 259 | 258 | 258 | 1291 |
| clear | 16 | 461 | 231 | 231 | 231 | 1154 |
| sort | 15 | 436 | 219 | 219 | 219 | 1093 |
| insert | 14 | 394 | 196 | 196 | 196 | 982 |
| relation | 14 | 390 | 194 | 195 | 195 | 974 |
| select | 13 | 378 | 190 | 190 | 190 | 948 |
| height | 13 | 363 | 182 | 182 | 182 | 909 |
| set | 12 | 342 | 170 | 170 | 170 | 852 |
| transfer | 11 | 330 | 164 | 164 | 164 | 822 |
| put_in | 10 | 278 | 139 | 139 | 139 | 695 |
| tidy | 8 | 264 | 133 | 133 | 133 | 663 |
| tall | 8 | 235 | 117 | 117 | 117 | 586 |
| recovery | 8 | 226 | 113 | 113 | 112 | 564 |
| hollow | 7 | 204 | 102 | 102 | 102 | 510 |
| pose | 6 | 180 | 90 | 91 | 91 | 452 |
| push | 6 | 178 | 89 | 88 | 89 | 444 |
| kitchen | 6 | 172 | 86 | 86 | 86 | 430 |

- 단계 수(편 가중): 1 72.3 %, 2 24.6 %, 3 3.1 %; 잡은 뒤 호출 수(놓기·다음 잡기, 2×단계−1 + 회복 2): 1 69.0 %, 3 27.4 %, 5 3.6 %; 정의 회복 편 비율 3.8 % (+ 모든 정의의 회복 후보 약 15 %).
- 놓기 자세(계획): upright 97.3 %, lying 1.6 %, oriented 0.8 %, leaning 0.4 %; 놓기 접근: top 97.4 %, push 2.3 %, front 0.4 %; 놓는 곳 높이 종류: in_container 44.1 %, main 41.0 %, on_object 10.1 %, high 3.0 %, low 1.9 %.
- 자연 잡기 기대 분포(natural_v1, 카탈로그 후보를 계열 → 부류 → 물체 순 균등 추첨): 접근 oblique 34.9 %, side 34.1 %, top 30.9 %; 부위 body 87.2 %, handle 11.3 %, rim 1.5 %. (top ≤ 50 % 관문 충족 예상)
- 문장 틀 1042개, 문장 틀 × 감싸기 × 방향 문장 용량 141,712개(물체 이름 제외).

## 6. 사전 점검 (Isaac 없음, `tools/l9/v2_hostable.py`, 신규 정의, 시도 5 × 장면 재추첨 6)

- AI Worker 폭으로 성공률 65 %, 0회인 정의 22개: arr_colour_row3, arr_three_corners, clear_after_meal, clear_three_mixed, hol_bowl_next_to, hol_two_mugs_row, kit_serve_two, kit_sink_to_rack, pose_handle_right, pose_stand_up, rel_between_containers, rel_chain3, set_place_three, set_two_drinks, set_two_plates_drink, sort_book_toy, sort_colour3_bins, sort_drink_food, tidy_gift_basket, tidy_return_two, tidy_three_places, tr_out_two_containers.
- Franka(8 cm)만 0회: tidy_picnic.
- 0회 원인(diag): 팔 작업 띠에 용기 2개 + 물체 2–3개가 들어가지 않음('no room'), 풀에 맞는 용기가 없음. 둘째 면으로 옮긴 정의도 아직 0회가 많다 → ENV의 넓은 작업면·둘째 면이 생기면 다시 점검하고, 그 전에는 `plan.py v2 --hostable`로 계획에서 뺀다.
- 이 점검은 '장면에 놓을 수 있는가'만 본다. 실행 성공은 주인의 G1(정의별 시범 ≥ 10편)이 정한다.

## 7. L8S 과제 종류 → L9 v2 정의 (주인 10-02 03시: 다음 본 학습은 L9 v2만 씀)

L8S 목록: `harvest/sim/tasks.py`(TASKS·X_TASKS·OBJV_TASK_KINDS·X_STEPS·CONF_TASKS), `harvest/teach_l8d/xnew.py`(쌓기·밀기), `xring.py`(고리 끼우기), `xart.py`(열린 서랍·상자). 굵게 = 지금 능력으로 계획에 들어가는 정의.

| L8S 종류 | L8S 예 | L9 v2 정의 |
|---|---|---|
| tray | mug_tray, bottle_tray | **in_onto_tray**, **set_food_on_plate**, **sel_colour_plate**, **sel_food_plate**, **tall_on_tray**, **tr_plate_to_plate** |
| bin | mug_bin, bottle_bin | **in_wide**, **clear_one**, **clear_toy_bin**, **tall_into_bin**, **sel_can_bin**, **in_kind_toy** |
| basket | objv basket (o20) | **in_cubby**, **clear_to_cubby**, **kit_to_sink**, **sel_bottle_basket**, tidy_gift_basket |
| left | mug_left_of_bottle | **rel_left**, **rel_left_of_container**, **sel_colour_left_of**, **tall_left_of**, **spread_out** |
| right | mug_right_of_bottle | **rel_right**, **rel_right_of_container**, **line_next_to**, **spread_right**, **set_drink_right** |
| front | objv front (o27) | **rel_front**, **rel_front_of_container**, **set_drink_front**, **rel_front_left**, **rel_front_right** |
| behind | objv behind (o28) | **rel_behind**, **rel_behind_container**, **set_behind_plate**, **rel_behind_left**, **rel_behind_right** |
| between | objv between (o29) | **rel_between**, rel_between_containers, **tall_between**, **arr_gap_narrow** |
| upper | mug_to_upper | **up_to_higher**, **up_into_container**, **up_two**, **tall_up_higher**, **up_onto_plate** |
| marker | mug_marker, box_marker | **set_on_mat**, **sort_kind_mat**, **set_coaster**, **kit_to_board**, **tidy_two_mats**, **to_front_left**, **set_centre** |
| stand | mug_stand, bottle_stand | **block_stack**, **block_two**, **block_by_side**, **block_named**, **sel_book_stand**, **st_tower_stand** |
| stand_then_place | stand_mug_tray | **block_unstack**, **tr_stand_to_bowl**, **tr_stand_to_plate**, **ins_from_block**, **block_restack** |
| confuser_attribute | bluemug_tray, smallcup_tray, cf_* | **in_by_colour**, **stack_by_colour**, **ins_among**, **sel_colour_in**, **sel_smaller_in**, **clear_colour**, **stack_named** |
| multi_step | mug_tray_bottle_marker, clear_to_bin | **clear_two**, **set_pair**, **in_two_same**, **tidy_pack_lunch**, set_place_three, clear_three_mixed, rel_chain3, **line3_y** |
| open_container | mug_to_container | **in_cubby**, **kit_to_sink**, **clear_to_cubby**, **tr_out_of_cubby** |
| stack | st__top__base | **stack2**, **stack_on_bigger**, **stack_named**, **st_on_book**, **st_colour_pair**, **stack_then_in** |
| push | pu__obj | push_onto_mat, push_left, push_right, push_to_front, push_next_to |
| ring_peg | rp__ring__peg | ins_ring_peg, **ins_one**, **ins_slot** |
| open_drawer_box | xart A/C | in_open_drawer, **in_cubby**, shelf_low_put |

- 밀기(push)는 L8S에서 기존 eef·그리퍼 명령만으로 한 계획(xnew.plan_push: 위 → 뒤로 내림 → 밀기 → 들어 빼기)이므로 우리 명령 형식으로 된다. 실행기에 그 계획을 붙이는 것은 주인 몫(`exec:push`).
- 고리 끼우기는 고리·말뚝 자산(`asset:ring_peg`), 열린 서랍은 노드 종류 `drawer_open`(ENV)이 필요하다.
- AI Worker 오른팔이 L8S의 주력이었으므로 AI Worker 행의 55 %를 오른팔로 준다(`alloc9.RIGHT_SHARE`).

## 8. 신규 정의 표 (출처마다 과제 이름은 그 목록의 이름)

| 정의 | 계열 | 단계 | 놓기 자세 | 필요 능력 | 출처 |
|---|---|---|---|---|---|
| `shelf_put_in` | shelf | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCounterToCabinet; RLB put_groceries_in_cupboard |
| `shelf_take_out` | shelf | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCabinetToCounter; RLB take_cup_out_from_cabinet |
| `shelf_high_put` | shelf | 1 | upright | node:shelf, exec:approach_front | B1K re-shelving_library_books; RC PickPlaceCounterToCabinet (upper) |
| `shelf_high_take_down` | shelf | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCabinetToCounter (upper); B1K putting_dishes_away_after_cleaning |
| `shelf_low_put` | shelf | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCounterToCabinet (lower); B1K putting_away_toys |
| `shelf_low_take_up` | shelf | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCabinetToCounter (lower); B1K storing_the_groceries |
| `shelf_to_shelf` | shelf | 1 | upright | node:shelf, exec:approach_front | B1K re-shelving_library_books; RC arranging_cabinets |
| `shelf_two_items` | shelf | 2 | upright | node:shelf, exec:approach_front | B1K storing_food; RLB put_groceries_in_cupboard |
| `shelf_by_colour` | shelf | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCounterToCabinet; CAL place_in_slider |
| `shelf_wall_put` | shelf | 1 | upright | node:shelf, exec:approach_front | B1K putting_up_Christmas_decorations_inside; RLB put_books_on_bookshelf |
| `shelf_tall_put` | shelf | 1 | upright | node:shelf, exec:approach_front | LIB put_the_wine_bottle_on_top_of_the_cabinet; B1K storing_the_groceries |
| `shelf_from_bin` | shelf | 1 | upright | node:shelf, exec:approach_front | B1K storing_the_groceries; RC restocking_supplies |
| `sel_colour_in` | select | 1 | upright | - | CAL lift_red_block_table; VIMA visual_manipulation |
| `sel_colour_plate` | select | 1 | upright | - | VIMA visual_manipulation; LIB libero_object |
| `sel_colour_left_of` | select | 1 | upright | - | VIMA rearrange; CAL lift_blue_block_table |
| `sel_bigger_in` | select | 1 | upright | - | RT2 blocks_ranking_size; VIMA manipulate_old_neighbor |
| `sel_smaller_in` | select | 1 | upright | - | RT2 blocks_ranking_size; VIMA manipulate_old_neighbor |
| `sel_bigger_front` | select | 1 | upright | - | RT2 blocks_ranking_size; BRIDGE pick-and-place |
| `sel_food_plate` | select | 1 | upright | - | LIB pick_up_the_X_and_place_it_in_the_basket; B1K serving_a_meal |
| `sel_drink_tray` | select | 1 | upright | - | B1K serving_hors_d_oeuvres; RC serving_beverages |
| `sel_toy_bin` | select | 1 | upright | - | B1K putting_away_toys; LIB libero_object |
| `sel_can_bin` | select | 1 | upright | - | B1K collecting_aluminum_cans; RT2 put_bottles_dustbin |
| `sel_bottle_basket` | select | 1 | upright | - | RT2 pick_diverse_bottles; LIB pick_up_the_ketchup_and_place_it_in_the_basket |
| `sel_book_stand` | select | 1 | upright | - | B1K sorting_books; RLB put_books_on_bookshelf |
| `sel_box_corner` | select | 1 | upright | - | B1K moving_boxes_to_storage; B1K organizing_boxes_in_garage |
| `tall_left_of` | tall | 1 | upright | - | RT2 pick_diverse_bottles; SIMPLER pick_coke_can (vertical) |
| `tall_into_bin` | tall | 1 | upright | - | RT2 put_bottles_dustbin; B1K collecting_aluminum_cans |
| `tall_on_tray` | tall | 1 | upright | - | B1K serving_a_meal; RT2 place_object_scale |
| `tall_row_two` | tall | 2 | upright | - | B1K storing_the_groceries; RT2 pick_dual_bottles (one-arm variant) |
| `tall_up_higher` | tall | 1 | upright | - | LIB put_the_wine_bottle_on_top_of_the_cabinet; RC PickPlaceCounterToCabinet |
| `tall_down_lower` | tall | 1 | upright | - | RC PickPlaceCabinetToCounter; LIB put_the_wine_bottle_on_the_rack |
| `tall_between` | tall | 1 | upright | - | VIMA rearrange; LIB pick_up_the_black_bowl_between_the_plate_and_the_ramekin |
| `tall_to_back` | tall | 1 | upright | - | RC arranging_condiments; B1K storing_the_groceries |
| `hol_bowl_next_to` | hollow | 1 | upright | exec:movable_container | LIB pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate; RT2 place_container_plate |
| `hol_mug_on_plate` | hollow | 1 | upright | exec:movable_container | LIB put_the_white_mug_on_the_plate; RT2 place_container_plate |
| `hol_bowl_nest2` | hollow | 1 | upright | exec:movable_container | RT2 stack_bowls_two; RC organizing_dishes_and_containers |
| `hol_mug_in_bowl` | hollow | 1 | upright | exec:movable_container | RC organizing_dishes_and_containers; RT2 stack_bowls_two |
| `hol_mug_next_to` | hollow | 1 | upright | exec:movable_container | RT2 place_empty_cup; LIB put_the_white_mug_on_the_plate_and_put_the_chocolate_pudding_to_the_right |
| `hol_cup_on_mat` | hollow | 1 | upright | exec:movable_container | RT2 place_empty_cup; RC serving_beverages |
| `hol_bowl_to_zone` | hollow | 1 | upright | exec:movable_container | LIB put_the_bowl_on_the_stove; RC PickPlaceCounterToStove |
| `hol_two_mugs_row` | hollow | 2 | upright | exec:movable_container | LIB put_the_white_mug_on_the_left_plate_and_put_the_yellow_and_white_mug_on_the_right_plate |
| `hol_bowl_up` | hollow | 1 | upright | exec:movable_container | LIB put_the_bowl_on_top_of_the_cabinet |
| `hol_bowl_in_shelf` | hollow | 1 | upright | exec:movable_container, node:shelf, exec:approach_front | B1K putting_dishes_away_after_cleaning; RC organizing_dishes_and_containers |
| `pose_lay_down` | pose | 1 | lying | exec:place_pose | SIMPLER pick_coke_can (lying horizontally); BRIDGE reorient |
| `pose_lay_in_box` | pose | 1 | lying | exec:place_pose | RT2 place_cans_plasticbox; B1K boxing_books_up_for_storage |
| `pose_stand_up` | pose | 1 | upright | exec:place_pose, exec:start_pose | BRIDGE flip pot upright; SIMPLER pick_coke_can (lying -> standing) |
| `pose_lean_divider` | pose | 1 | leaning | exec:place_pose | RLB put_books_on_bookshelf; B1K re-shelving_library_books |
| `pose_rotate90` | pose | 1 | oriented | exec:place_pose | CAL rotate_red_block_right; VIMA rotate |
| `pose_long_side_lr` | pose | 1 | oriented | exec:place_pose | VIMA rearrange; CAL rotate_blue_block_left |
| `pose_handle_right` | pose | 1 | oriented | exec:place_pose, exec:movable_container | VIMA rotate; RLB place_cups |
| `pose_lay_in_shelf` | pose | 1 | lying | exec:place_pose, node:shelf, exec:approach_front | RLB stack_wine; LIB put_the_wine_bottle_on_the_rack |
| `pose_lay_two` | pose | 2 | lying | exec:place_pose | B1K boxing_books_up_for_storage; SIMPLER pick_coke_can (lying) |
| `pose_stand_in_shelf` | pose | 1 | oriented | exec:place_pose, node:shelf, exec:approach_front | RLB put_books_on_bookshelf; B1K sorting_books |
| `kit_to_sink` | kitchen | 1 | upright | - | RC PickPlaceCounterToSink; B1K washing_dishes |
| `kit_from_sink` | kitchen | 1 | upright | - | RC PickPlaceSinkToCounter |
| `kit_to_board` | kitchen | 1 | upright | - | RC chopping_food; B1K chopping_vegetables |
| `kit_board_to_bowl` | kitchen | 1 | upright | - | B1K preparing_salad; RC making_salads |
| `kit_sink_to_rack` | kitchen | 1 | upright | - | B1K washing_dishes; RLB put_plate_in_colored_dish_rack |
| `kit_rack_to_counter` | kitchen | 1 | upright | - | RLB take_plate_off_colored_dish_rack; RC organizing_utensils |
| `kit_can_next_pot` | kitchen | 1 | upright | - | RT2 move_can_pot; RC arranging_condiments |
| `kit_serve_two` | kitchen | 2 | upright | - | RC serving_food; RC plating_food |
| `tidy_return_two` | tidy | 2 | upright | - | B1K collect_misplaced_items; B1K cleaning_bedroom |
| `tidy_desk` | tidy | 2 | upright | - | B1K organizing_school_stuff; RC organizing_utensils |
| `tidy_pack_lunch` | tidy | 2 | upright | - | RC packing_lunches; B1K packing_lunches |
| `tidy_picnic` | tidy | 3 | upright | - | B1K packing_picnics |
| `tidy_gift_basket` | tidy | 2 | upright | - | B1K assembling_gift_baskets; B1K filling_an_Easter_basket |
| `tidy_trash_two` | tidy | 2 | upright | - | B1K picking_up_trash; B1K throwing_away_leftovers |
| `tidy_toys_away` | tidy | 2 | upright | - | B1K putting_away_toys; B1K cleaning_bedroom |
| `tidy_clear_and_stack` | tidy | 2 | upright | - | B1K cleaning_table_after_clearing; B1K boxing_books_up_for_storage |
| `tidy_clear_to_shelf` | tidy | 2 | upright | node:shelf, exec:approach_front | B1K cleaning_up_after_a_meal; RC clearing_table |
| `tidy_stock_shelf` | tidy | 2 | upright | node:shelf, exec:approach_front | RC restocking_supplies; B1K storing_the_groceries |
| `tidy_pack_bag` | tidy | 2 | upright | - | B1K packing_child_s_bag; B1K packing_bags_or_suitcase |
| `tidy_two_mats` | tidy | 2 | upright | - | RC arranging_buffet; B1K setting_up_candles |
| `tr_out_of_basket` | transfer | 1 | upright | - | B1K unpacking_suitcase; RT2 place_object_basket (reverse) |
| `tr_basket_to_bowl` | transfer | 1 | upright | - | RC organizing_dishes_and_containers; B1K storing_food |
| `tr_plate_to_plate` | transfer | 1 | upright | - | RT2 place_bread_skillet; RT2 place_burger_fries |
| `tr_tray_to_bin` | transfer | 1 | upright | - | B1K clearing_the_table_after_dinner; RC clearing_table |
| `tr_out_of_cubby` | transfer | 1 | upright | - | CAL lift_red_block_slider; RC PickPlaceDrawerToCounter (open) |
| `tr_cubby_to_cubby` | transfer | 1 | upright | - | B1K organizing_file_cabinet; LIB pick_up_the_book_and_place_it_in_the_back_compartment_of_the_caddy |
| `tr_slot_to_slot` | transfer | 1 | upright | - | B1K organizing_school_stuff |
| `tr_out_two_containers` | transfer | 2 | upright | - | B1K unpacking_suitcase; B1K opening_presents |
| `tr_bin_to_plate` | transfer | 1 | upright | - | RC PickPlaceSinkToCounter; RC serving_food |
| `tr_stand_to_bowl` | transfer | 1 | upright | - | CAL unstack_block; CAL place_in_slider |
| `rcv_rel_left_off` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_in_wide_off` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_line2_x_off` | recovery | 2 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_set_food_on_plate_off` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_block_stack_tilt` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_ins_one_tilt` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_to_front_left_off` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rcv_set_drink_right_tilt` | recovery | 1 | upright | exec:recovery | RT2 domain randomisation + retry (expert replanning); DROID recovery / retry segments |
| `rel_front_right` | relation | 1 | upright | - | LIB libero_spatial; VIMA rearrange |
| `rel_behind_left` | relation | 1 | upright | - | LIB libero_spatial; VIMA rearrange |
| `rel_behind_right` | relation | 1 | upright | - | LIB libero_spatial; VIMA rearrange |
| `rel_between_containers` | relation | 1 | upright | - | LIB pick_up_the_black_bowl_between_the_plate_and_the_ramekin; VIMA rearrange |
| `arr_front_edge` | arrange | 1 | upright | - | VIMA rearrange; B1K rearranging_furniture |
| `arr_deep_back` | arrange | 1 | upright | - | RC arranging_condiments; B1K rearranging_furniture |
| `arr_left_edge` | arrange | 1 | upright | - | VIMA rearrange; B1K rearranging_furniture |
| `arr_right_edge` | arrange | 1 | upright | - | VIMA rearrange; B1K rearranging_furniture |
| `arr_gap_narrow` | arrange | 1 | upright | - | LIB pick_up_the_black_bowl_between_the_plate_and_the_ramekin; VIMA rearrange |
| `arr_three_corners` | arrange | 3 | upright | - | VIMA rearrange; B1K collect_misplaced_items |
| `arr_diag` | arrange | 2 | upright | - | VIMA rearrange; B1K rearranging_furniture |
| `arr_colour_row3` | arrange | 3 | upright | - | RT2 blocks_ranking_rgb; VIMA rearrange |
| `st_tower_stand` | stack | 2 | upright | - | RT2 stack_blocks_two; CAL stack_block |
| `st_tower3_stand` | stack | 3 | upright | - | RT2 stack_blocks_three |
| `st_on_book` | stack | 1 | upright | - | B1K boxing_books_up_for_storage; RLB stack_blocks |
| `st_colour_pair` | stack | 1 | upright | - | CAL stack_block; VIMA visual_manipulation |
| `st_unstack_to_bin` | stack | 1 | upright | - | CAL unstack_block; CAL place_in_drawer (open) |
| `ins_two_one_holder` | insert | 2 | upright | - | B1K organizing_school_stuff; RC organizing_utensils |
| `ins_narrow_cont` | insert | 1 | upright | - | B1K organizing_school_stuff; RLB put_umbrella_in_umbrella_stand |
| `ins_candle` | insert | 1 | upright | - | B1K setting_up_candles |
| `ins_from_shelf` | insert | 1 | upright | node:shelf, exec:approach_front | RC PickPlaceCabinetToCounter; B1K organizing_school_stuff |
| `ins_from_bin` | insert | 1 | upright | - | B1K organizing_school_stuff; B1K unpacking_suitcase |
| `sort_colour3_bins` | sort | 3 | upright | - | VIMA rearrange; RT2 blocks_ranking_rgb |
| `sort_drink_food` | sort | 2 | upright | - | B1K sorting_groceries; RC sorting_ingredients |
| `sort_recycle` | sort | 2 | upright | - | B1K collecting_aluminum_cans; RC organizing_recycling |
| `sort_book_toy` | sort | 2 | upright | - | B1K sorting_books; B1K putting_away_toys |
| `sort_shelf_bin` | sort | 2 | upright | node:shelf, exec:approach_front | B1K storing_the_groceries; B1K putting_away_toys |
| `set_place_three` | set | 3 | upright | - | RLB set_the_table; B1K serving_a_meal |
| `set_behind_plate` | set | 1 | upright | - | RLB set_the_table; B1K serving_a_meal |
| `set_hors_tray` | set | 2 | upright | - | B1K serving_hors_d_oeuvres; RT2 place_burger_fries |
| `set_two_drinks` | set | 2 | upright | - | RLB set_the_table; LIB put_the_white_mug_on_the_left_plate_and_put_the_yellow_and_white_mug_on_the_right_plate |
| `set_coaster` | set | 1 | upright | - | RT2 place_empty_cup; RC serving_beverages |
| `clear_after_meal` | clear | 2 | upright | - | B1K clearing_the_table_after_dinner; RC clearing_table |
| `clear_cans` | clear | 2 | upright | - | B1K collecting_aluminum_cans; RT2 put_bottles_dustbin |
| `clear_leftovers_shelf` | clear | 1 | upright | node:shelf, exec:approach_front | B1K putting_leftovers_away; RC storing_leftovers |
| `clear_zone_two` | clear | 2 | upright | - | B1K cleaning_table_after_clearing |
| `down_two` | height | 2 | upright | - | RC PickPlaceCabinetToCounter; B1K putting_away_Christmas_decorations |
| `up_onto_plate` | height | 1 | upright | - | LIB put_the_bowl_on_top_of_the_cabinet; RC PickPlaceCounterToCabinet |
| `down_onto_plate` | height | 1 | upright | - | RC PickPlaceCabinetToCounter; LIB pick_up_the_black_bowl_on_the_wooden_cabinet_and_place_it_on_the_plate |
| `tidy_three_places` | tidy | 3 | upright | - | B1K collect_misplaced_items; B1K cleaning_bedroom |
| `tr_swap_containers` | transfer | 2 | upright | - | B1K storing_food; RC organizing_dishes_and_containers |
| `set_two_plates_drink` | set | 3 | upright | - | B1K serving_a_meal; RLB set_the_table |
| `clear_three_mixed` | clear | 3 | upright | - | B1K cleaning_up_after_a_meal; RC clearing_table |
| `rel_chain3` | relation | 3 | upright | - | VIMA rearrange; LIB libero_spatial |
| `stack_then_two_in` | stack | 3 | upright | - | B1K boxing_books_up_for_storage; CAL stack_block |
| `push_onto_mat` | push | 1 | upright | exec:push | CAL push_red_block_right; DROID push |
| `push_left` | push | 1 | upright | exec:push | CAL push_blue_block_left; BRIDGE push |
| `push_right` | push | 1 | upright | exec:push | CAL push_pink_block_right; BRIDGE push |
| `push_to_front` | push | 1 | upright | exec:push | LIB push_the_plate_to_the_front_of_the_stove; DROID push |
| `push_next_to` | push | 1 | upright | exec:push | CAL push_red_block_left; VIMA sweep_without_exceeding |
| `push_to_back` | push | 1 | upright | exec:push | CAL push_into_drawer (push part); BRIDGE push |
| `tr_stand_to_plate` | transfer | 1 | upright | - | RT2 place_object_stand (reverse); CAL unstack_block |
| `ins_ring_peg` | insert | 1 | upright | asset:ring_peg | RLB put_rubbish_in_bin -> ring variant: place_shape_in_shape_sorter; RT2 place_object_stand |
| `in_open_drawer` | put_in | 1 | upright | node:drawer_open | RC PickPlaceCounterToDrawer (drawer already open); LIB open_the_top_drawer_and_put_the_bowl_inside (put part only) |

## 9. v1 정의의 출처 (계열별)

| 계열 | 가장 가까운 공개 과제 |
|---|---|
| insert | RLB put_umbrella_in_umbrella_stand; B1K organizing_school_stuff |
| arrange | VIMA rearrange; B1K collect_misplaced_items |
| stack | RT2 stack_blocks_two; CAL stack_block |
| sort | RT2 blocks_ranking_rgb; B1K sorting_groceries |
| put_in | LIB pick_up_the_X_and_place_it_in_the_basket; RT2 place_object_basket |
| set | RLB set_the_table; B1K serving_a_meal |
| clear | B1K clearing_the_table_after_dinner; RC clearing_table |
| relation | LIB libero_spatial; VIMA rearrange |
| height | LIB put_the_bowl_on_top_of_the_cabinet; RC PickPlaceCabinetToCounter |

## 10. 열린 문제

- Isaac 검증 전(주인): 신규 정의 G1 시범, `exec:*` 능력 구현(앞 접근·움직이는 용기·놓기 자세·시작 자세·회복·밀기), 선반 노드(ENV) 이름 맞추기(`SHELF_KINDS`), R1 Pro·G1 그리퍼 폭 실측(robot9 `grip_max`).
- 지시 방향 행: 주인 v2plan/rt9의 20 % 동전과 이 문서의 `instructed_approach` 중 하나만 써야 이중 지시가 없다.
- 납작한 물체(≤ 3 cm: edge 잡기)·도구 손잡이·키 큰 물체(≥ 14 cm)는 카탈로그 대상에 거의 없다 → 자산(ENV/assets) 보강이 필요하다.
- 재질 조건 고르기는 재질 표지가 없어 제외했다.
