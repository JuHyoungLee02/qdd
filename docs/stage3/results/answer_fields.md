# E-8BABL2 결과 — 답에 approach·rot·hand/arm까지 답하게 하는 것이 도움/방해인가

작성: 통제자, 10-04. (1)(3)은 측정 완료(새 학습 없음). (2)는 학습 진행 중(기존 off_v4=A, 신규 fieldsB=B).

## (1) off_v4 보류 평가에서 approach·rot·arm 정확도 (`x8b2_fields_acc.py`, replies.jsonl 직접 집계)

접기(grasp) 행 575개(approach/rot 라벨이 있는 행), rot 라벨 있는 행 238개.

| 구분 | n | approach_acc(4종, 우연 0.25) | arm_acc(2종, 우연 0.5) | rot 정확일치 | rot ±1(12칸, 우연 0.25) | **rot ±1(180°대칭 6칸, 우연 0.5)** |
|---|---|---|---|---|---|---|
| 전체 | 575 | 0.235 | 0.437 | 0.105 | 0.269 | **0.546** |
| g1(3지) | 109 | 0.220 | 0.257 | 0.143 | 0.321 | 0.679 |
| r1pro | 160 | 0.181 | 0.469 | 0.069 | 0.167 | 0.542 |
| franka_mast(2지) | 195 | 0.236 | 0.441 | 0.158 | 0.329 | 0.500 |
| ffw_sg2(2지) | 111 | 0.324 | 0.559 | 0.065 | 0.290 | 0.548 |

**옛 E-TP1 rot±1=0.19가 진짜인가 지표 문제(대칭 미반영)인가**: 둘 다 아니고 **둘 다다** — 대칭 반영 전(0.269)과 우연(0.25)이 거의 같고, 대칭 반영 후(0.546)도 그 우연(0.5)과 거의 같다. 즉 **대칭을 넣으면 숫자는 크게 오르지만(0.27→0.55), 그만큼 우연 기준선도 같이 올라서(0.25→0.5) 실제로는 둘 다 거의 우연 수준** — 옛 리포트의 낮은 숫자는 지표 결함이 아니라 모델이 집게 방향을 거의 못 맞춘다는 실제 신호였다. approach_acc(0.235)·arm_acc(0.437)도 각자의 우연 기준(0.25 / 0.5) 근처이거나 그보다 낮다(특히 g1 arm_acc=0.257은 우연보다 뚜렷이 나쁨).
혼동표(전체): top/oblique 둘로만 쏠리고(위쪽 합 393/575) side는 거의 전부 틀림(31개 중 None 또는 다른 값), None(형식 누락) 비율도 높다(138+157+31+11=337/575, 59%) — approach 자체를 아예 안 적는 행이 과반.
off_s1_v4(시드1)는 아직 평가 전이라 포함 못 함, 끝나면 추가.

## (2) 비교 학습 A(F1=전체형식, off_v4 재사용) vs B(F2=점·높이·그리퍼만, fieldsB)

- 같은 편(episodes_g2.json, gen2 1,381train/300eval)·같은 걸음 수(302, off_v4와 동일)·시드 0.
- B 빌드: build9(grasp_format=False)로 approach/rot 제거 + 프롬프트 GRASP 블록 제거(기존 기능) → 추가로 `hand`/`arm`도 답과 프롬프트(스키마 줄 "hand": …, "every command names its arm" 문장)에서 제거하는 후처리(`x8b2_build_fieldsB.py`).
- 상태: CPU 빌드 중(juhyoung-0), x2 큐(현재 r1_adapt_v4 뒤)에 걸어둠 — **아직 결과 없음, 끝나면 표 추가**(point px 중앙·p90, action_acc, approach_xy mm).

## (3) 프롬프트 형식 줄과 정답 필드 어긋남 — 실제 행 3개로 확인

맞다, 어긋나 보이지만 **의도된 구조다**: 메인 "Return JSON only" 스키마 줄에는 `mode/point_2d/height/hand/delta_m/gripper`만 있고 approach·rot·arm이 없다. 그런데 approach·rot은 **별도 GRASP 블록**("GRASP (only when the gripper closes...): ... "approach": top|oblique|front|side ... "rot": 0-11 ...")에서, arm은 **또 다른 별도 문장**("every command names its arm ("arm": "left"|"right")...")에서 각각 설명된다 — 전부 프롬프트 안에 있다, 한 줄에 몰려있지 않을 뿐. hand와 arm은 실제로 같은 걸 말하는 중복 필드다(hand 설명 자체가 "the arm that moves"). 3개 샘플 행(`l9_arr_deep_back_s9020076_right_c000/c001`, `l9_kit_can_next_pot_s9023175_left_c000`) 전부 이 구조를 확인함.
