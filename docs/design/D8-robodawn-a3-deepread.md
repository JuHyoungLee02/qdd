# D8 RoboDawn(2609.22966)·A3(2605.11567) 원문 정독 요약

> 정정 2026-09-24 04:54 UTC (D16 W1): 아래 원 보고의 "Astra RoboDojo 자체 평가 28.97/22.58"과 "자체 평가 22.58%"는 원문 값이 아니다. 원문(2609.24170)은 "22.48% average success rate and 28.97 Score"(표 1도 28.97/22.48)이고, 22.58은 RoboDawn Table 4(2609.22966)가 옮겨 적은 2차 인용 값이다. 원 보고 문장은 기록으로 두고 고치지 않는다.

작성: 2026-09-24 00:20 UTC. (00:25 보강: 요약 때 빠뜨린 C2R 7개 항목·시드 제공 범위·턴 45·Table 4 값 형식을 원 보고에서 되살림.) 정독 에이전트(두 논문 HTML 전문 + 부록, RoboDawn 프로젝트 페이지·GitHub Hugo-AGI/RoboDawn 코드, A3 프로젝트 페이지·GitHub INCEPTIONwang/A3 코드) 보고를 메인 세션이 요약·저장. 메인 세션 원문 재확인: RoboDawn 절제 "Removing reasoning … 47.0% to 34.8% … removing grid-based localization … 32.4%", §3.2 "executed until the robot reaches a stationary state"; A3 §6 "all verification signals are derived from the underlying policy, A3 cannot identify confidently incorrect predictions … Incorporating explicit world models or independently learned state-transition predictors could complement self-consistency with external evidence".

## RoboDawn (Tsinghua·Tencent Hunyuan, 2026-09-19, 코드 09-22 공개)
- **인터페이스[원문]**: `<arm> move <x|y|z> <cm>`, `rotate <roll|pitch|yaw> <deg>`, `point <preset>`, `gripper <open|close|0..1>`, `home`, `wait`, `done`. **보기 목록이 아니라 모델이 부호 있는 실수를 직접 적는다**(|cm| ≤ 20, |deg| ≤ 90). 한 명령 = 한 축, 대각은 한 턴에 여러 명령(기본 최대 4, 평균 3.4). RoboDojo 판만 회전 15° 반올림 + 자세 프리셋 7개. 턴마다 VLM 1회, JSON `{scene, progress, memory, plan, commands}`, temperature 0, reasoning 켬(Astra high).
- **관측[원문]**: 하네스가 추가한 전경·수직 하향 카메라 2대(10 cm 격자·손끝 마커 주석) + 양 손목, cm 단위 손끝 상태, 시뮬 내부 탁자 높이, 직전 명령 결과(RoboDojo: 목표 대비 1.5 cm/8° 안이면 reached, 아니면 실제 이동량), 스크래치패드. 요청당 이미지 최대 58장.
- **정지형[원문]**: 명령마다 정지 상태까지 실행 후 다음 관측. 결정당 추론 9.74 s, 동작 2.09 s(Seed-2.1-Pro). 겹쳐 스트리밍은 "가능하다"고만 쓰고 하지 않음.
- **C2R[원문]**: RoboTwin 공식 `demo_randomized.yml`의 7개 항목 — `random_background`, `cluttered_table`(방해물), `clean_background_rate 0.02`, `random_table_height 0.03`(최대 3 cm 낮아짐), `random_light`, `crazy_random_light_rate 0.02`, `eval_instruction: unseen`(clean 설정에서는 전부 꺼짐). 평가 시드는 `harness/valid_seeds/<task>__demo_randomized__seed0.json`(seed_base 100000, 전문가가 풀 수 있는 시드) — **`demo_randomized` 시드만 제공**(clean 짝 시드는 없음). 턴 한도 45회. VLA는 50과제 × clean 시연 50개로 함께 학습. 50과제 × 10회 = 500. 결과(Table 1): π0.5 46.0, LingBot 50.4, HarnessVLA 58.0/58.4, RoboDawn Gemini-3.8-Flash 0/1-shot 47.0/62.2, Astra 0/1-shot 53.2/73.6(Astra 1-shot 368/500 ±3.1). **0-shot 행은 저장소가 재현 구성을 제공하지 않는 보고치, 기준선은 타 논문 보고치, RoboDawn clean 점수 없음 → 낙폭 계산 불가.**
- 절제(Table 3): 샷 0/1/2/4/8 = 47.0/62.2/63.6/65.4/62.7, 모델별 1-shot Luna 14.4·Sol 43.2·Seed 45.0·Gemini 62.2·Astra 73.6, 하네스 추론 제거 34.8·**격자 제거 32.4**·primer 제거 44.0.
- RoboDojo(Table 4, 값 형식은 **Score / SR%**): seed 0 · 과제당 layout 0–4 = 5회 · **`_random` 짝 평가 안 함** · 차원 평균. Astra RoboDojo 자체 평가 28.97/22.58 대 RoboDawn Astra 0-shot 39.92/35.67, 1-shot 54.63/47.17. 명령 예산 60→240에서 1-shot 31.2→47.2%.
- 실물(Gemini, zero-shot): Franka 바구니 9/10, 쌓기 5/10, Piper 천 접기 0/10.
- 저자 한계: 느린 추론, 회전이 더 어려움, "이산 의미 명령이 미세 보정에 너무 거칠다", 안전. 실패: 마지막 1 cm, IK 충돌, 조기 성공 판단.

## A3 (Adelaide·SJTU 외, 2026-05-12, 학회 표기 없음)
- 알고리즘[원문]: **같은 관측 s_t에서** K=8 청크를 한 배치로 샘플 → 누적 자세 궤적 공간에서 합의 점수(군집 우세 모드) → 합의순 조건부 불변성 + 접두부 닫힘 순차 일관성 이중 검증(RTC식 flow inpainting 재디코딩, 추가 순전파 1회) → 모두 통과한 **가장 긴 접두부 확정**. δ = 차원별 std(0.5/1/1.5×에서 97.9/98.1/97.8).
- 결과: π0.5 LIBERO 97.9/6.3 → 98.0/9.8(본문은 98.1/9.7로 표와 불일치), 실물 Piper 84.6%(고정 최적 79.2), 가림·블러에서 최대 +10.2, 호출당 지연 253.2 → 289.5 ms.
- **시간차 호출 사이 비교 없음. 실행 뒤 예상 대 측정 확인 없음.** 저자가 §6에서 외부 증거(세계 모델·상태 전이 예측기)를 향후 과제로 명시.
- 공개 코드와 논문 차이: 군집·medoid·시간 정렬 코드를 해당 파일에서 못 찾음, 첫 행동은 항상 실행.

## 설계에 주는 것 (메인 세션 채택 → 정본 §19)
- 평가: RoboDawn은 **같은 인식 비교가 아니다**(하네스 주석 시점·계획기 실행·판정 요령 프로파일). EVAL N11의 "VLM은 원본 이미지" 서술은 틀렸다. "같은 인식 앞단" 한정어가 더 정당해진다. Astra가 같은 RoboDojo에서 자체 평가 22.58% 대 RoboDawn 하네스 35.67% → "인터페이스·근거 설계가 점수를 크게 바꾼다" = 같은 앞단 요구의 근거.
- M4: A3 저자가 우리 (b)를 향후 과제로 명시 → 차별화 문장에 인용. (b) 단독(실행 뒤 되먹임)은 RoboDawn에도 있다 → 차별점은 "(b)가 합의 원장의 전제 무효화·확정 판단에 쓰인다".
- M4 빌릴 것: 누적 예상 상태 기준 합의(증분 보기 순서가 달라도 같은 결과면 일치), 시간 정렬 ±1 스텝, 데이터 척도 기반 허용 폭, "격자 탐색 최적 고정 확정 길이" 기준선, 평균 확정 길이·호출 수 지표, 관측 열화 스윕.
- M3: RoboDawn의 "한 축 한 명령 + 한 호출에 여러 명령", 회전 15° 이산화·프리셋 7개를 D-줌 대안 조건으로. 성능을 가장 움직인 것은 공간 근거(격자 −14.6%p)와 결정 횟수 → "촘촘함 = 결정 빈도·공간 근거" 해석 지지. 접촉 근처가 거칠다는 저자 한계 → H안(접촉 근처 미세 조정) 지지.
