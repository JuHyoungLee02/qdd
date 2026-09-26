# ROBOTIS AI Worker 공개 데이터 조사 (user-log 105)

작성 2026-09-26 07:18 UTC, 조사 에이전트. **학습·변환·유료 호출은 하지 않았다.** HF Hub 공개 API(목록·`meta/info.json`·`meta/tasks.jsonl`·`meta/episodes.jsonl`·카드)와 표본 편 몇 개의 프레임만 봤다. GPU 0, 유료 0원. 파드 사용 371 MB(`/data/harvest/data/robotis_survey/`).

## 0. 결론 요약
- "AI Worker 공개 데이터"는 세 층이다. (1) **ROBOTIS 공식 조직** 데이터셋 7개 — 09-24 조사(`stage3/results/se2e_data.md` 2절)와 같고 새로 늘지 않았다(조직 컬렉션 `PickCoffee_Env1–5`는 비어 있음). (2) **ROBOTIS 직원 개인 계정**(`RobotisSW` = SeongWoo Kim 675개, `Dongkkka` = Dongyun Kim 510개, 둘 다 ROBOTIS 조직 구성원) — 조직 페이지보다 훨씬 많다. 사용자가 말한 "많은 데이터"는 이것이다. (3) 외부 사용자 AI Worker 업로드(수백 개, 대부분 소규모·시험).
- 목록 1,500개 중 AI Worker(FFW) 관련 **1,150개의 메타데이터를 모두** 읽었다(오류 34, 대부분 `info.json` 없는 lance·원본 MCAP 저장소).
- **가장 쓸 만한 것 3개**
  1. **`Dongkkka/ffw_bg2_rev4_pickup_obj_1127_total2`**(806편, 우리 기종 BG2 rev4, 10 fps, 머리 672×376 + 손목 2대, 카드 apache-2.0) — **같은 장면·같은 물체를 왼팔/오른팔로 집는 쌍**과 **같은 공구 벽에서 지시문이 대상을 고르는** 구조가 둘 다 있다. 첫 프레임 MAD ≤ 8 편 쌍 2,023개 중 대상이 다른 쌍 601, 같은 대상·다른 팔 457. RB2와 같은 공구 벽이지만 **편이 겹치지 않는 RB2 이전 수집분**(11-24–27)이다. → (a) 조종 오프라인 평가·(b) 확장 1순위.
  2. **`RobotisSW` 과제 카탈로그**(`ffw_bg2_rev4_task_N_*` 121과제·2,271편·9.7 h, `ffw_sg2_rev1_task_N_*` 201과제·5,093편·31.9 h, 전부 카드 apache-2.0, 머리 672×376 + 손목 2대, 2025-12-16 – 2026-02-06, 조작자 2명) — **322개 과제**(상자 옮기기, 선반 과자, 냉장고 음료, 양손 옮기기 등). 지시문이 `task_101`처럼 번호뿐이다. → (c) E-AT 다양성 1순위, (b) 확장 2순위.
  3. **`RobotisSW/Merged_PickPlace_PlasticBottle_CoffeeCan_KJM_WJW_lerobot`**(626편, 2026-09-14 최신, SG2, 15 fps) — 식탁 위에 병·캔·과자 여러 개가 놓이고 지시문이 **병 또는 캔**을 고른다(두 대상 구조). 단 **라이선스 표기 없음**, 머리 1280×720·손목 480×640으로 카메라 배치가 다르다. → (a) 보조, 라이선스 확인 전 내부용.
- **"같은 장면·같은 목표·다른 경로" 원격조작 시연(MolmoAct D.7식)은 어디에도 없다.** 가장 가까운 것이 1번의 "같은 물체를 다른 팔로"다(경로 차가 크고 팔이 바뀜 — 좁은 뜻의 대체 경로와는 다름). E-MAR-S 학습용 대체 경로 시연은 여전히 새 수집이 필요하다(`stage3/molmoact_real_readiness.md` 4.6절 설계 유지).
- **실패·복구 데이터**: ROBOTIS 쪽에는 없다(모두 성공 시연). 외부 사용자 것만 있다 — `learner1119/ffw_sg2_rev1_VIN2_poc_Fail1`·`VINE2_poc_Fail2`(49·50편, 한 팔, 주황 상자 → 흰 상자, 프레임상 **실패·밀림·재시도 섞임**, apache-2.0), `chomeed/ai_worker_board_*_failure`·`dagger`(9·14·91편, 다른 손 그리퍼 38-D·1280×720, apache-2.0). E-AT 실패 표본으로 소량 쓸 수 있다.

## 1. 방법
- 목록: HF API `datasets?author=`(ROBOTIS, RobotisSW, Dongkkka)와 `search=`(ffw, ffw_, ffw_bg2, ffw_sg2, ffw_sh5, ffw_bh5, ai_worker, aiworker, ai-worker, robotis, worker, omx·omy는 제외용)로 1,500개 → 이름에 `ffw`·`ai_worker`가 있거나 ROBOTIS 계정의 `Task_*`·`Merged*`·`Pick*`인 1,150개. 주의: `search=ffw`는 1,000개에서 잘린다 — 세부 검색어와 계정별 목록으로 보완했다.
- 저장소마다: `meta/info.json`(판본·기종·fps·편·프레임·카메라와 해상도·상태 이름), `tasks.jsonl`(v3.0은 `tasks.parquet`), 카드 머리말 라이선스, API `usedStorage`·`lastModified`·`sha`. 결과 `meta_all.jsonl`(파드).
- 상위 후보 14개에서 편 2–8개씩 받아 머리 카메라 시작·중간·**놓기 순간**(그리퍼 관절이 0.5 s 넘게 닫혔다 열리는 프레임)·손목 1장 시트를 만들어 눈으로 봤다. 머리 관절 범위·리프트도 쟀다. 1번은 806편 전부의 첫 프레임(84×47 흑백)으로 같은 장면 쌍을 셌다(`se2e_data.md`·`molmoact_real_readiness.md`와 같은 MAD 지표).

## 2. 데이터셋 표 (상위 + 비교용)

| 데이터셋 | 기종 | 판본·fps | 편 / 프레임 | 크기 | 카메라(해상도) | 과제·지시문 | 라이선스 | 갱신 |
|---|---|---|---|---|---|---|---|---|
| ROBOTIS/Task_0001 (**RB1**, 사용 중) | bg2_rev4_custom | v2.1·10 | 718 / 125,746 | 5.39 GB | 머리 2(672×376)·손목 2(세로 240×424) | 병 색 분류 1문장 | **없음(카드 없음)** | 2025-09-26 |
| ROBOTIS/Task_0002 (**RB2**, 사용 중) | bg2_rev4 | v2.1·10 | 857 / 85,474 | 3.55 GB | 머리 2·손목 2(424×240) | 공구 11문장 | apache-2.0 | 2026-04-07 |
| ROBOTIS/Task_0003–0006 | ffw_arm_only | v2.1·15 | 268·198·1,316·21 | 0.6–7.1 GB | **머리 1대 1280×720, 손목 없음** | 재활용·에어백·포장·과자 스캔 | 없음 | 2026-03–04 |
| **Dongkkka/ffw_bg2_rev4_pickup_obj_1127_total2** | bg2_rev4 | v2.1·10 | 806 / 104,470 | 3.31 GB | 머리 1(672×376)·손목 2(424×240) | 공구 6종 × 왼/오른 그리퍼 12문장 + 노란 통 1 | 카드 apache-2.0 | 2025-11-27 |
| Dongkkka/…pickup_obj_1124_total_3 | bg2_rev4 | v2.1·10 | 568 | 2.65 GB | 같음 | 7종 × 두 팔 15문장 | 없음 | 2025-11-24 |
| **RobotisSW/ffw_bg2_rev4_task_N_*** (121과제) | bg2_rev4 | v2.1·10(5·15·30 일부) | 2,271 / 365,881 (중복 `_edit` 제외) | 11.4 GB | 머리 1·손목 2(424×240로 적혀 있으나 내용은 세로 — 아래) | `task_N` 번호만 | apache-2.0(전부) | 2025-12-16 – 2026-01-19 |
| **RobotisSW/ffw_sg2_rev1_task_N_*** (201과제) | sg2_rev1 | v2.1·15(10·30 일부) | 5,093 / 1,583,332 | 78.6 GB | 같음 | `task_N` 번호만 | apache-2.0(전부) | 2026-01-05 – 02-06 |
| Dongkkka/ffw_bg2_rev4_task_72to120_* (8개) | bg2_rev4 | v2.1·10 | 312–405 각 | 2.9 GB 각 | 같음 | 위 카탈로그 72–120의 병합본(홀·짝·조작자별) | 없음 | 2026-01-09 |
| **RobotisSW/Merged_PickPlace_PlasticBottle_CoffeeCan_KJM_WJW** | sg2_rev1 | v2.1·15 | 626 / 123,209 | 7.23 GB | 머리 2(**1280×720**)·손목 2(**480×640**) | 병 / 캔 2문장 | **없음** | 2026-09-14 |
| RobotisSW/Pick_chestnuts, Task_9000xx(땅콩·컵 재활용) 등 | sg2_rev1 | v2.1/v3.0·15 | 66–344 | 0.3–3.5 GB | 머리 2·손목 2 | 1문장씩 | 없음 | 2026-06–08 |
| Dongkkka/ffw_sg2_Object_Storage_*, task_4xx | ffw_arm_only | v2.1·15 | 106–834 | 1–7 GB | 머리 1대, 손목 없음 | 포장·스캔 | 없음 | 2026-03–04 |
| learner1119/ffw_sg2_rev1_VINE2_poc(+Fail1·Fail2) | sg2_rev1(한 팔 8-D) | v2.1·10 | 106 + 49 + 50 | 0.07–0.24 GB | 머리 1·손목 2 | 주황 상자 → 흰 상자 | apache-2.0 | 2026-07 |
| chomeed/ai_worker_board_*(success·failure·dagger) | 다른 손(38-D) | v3.0·30 | 9–222 | 0.1–6.6 GB | 머리 1280×720·손목 424×240 | 기판 건네기·끼우기 | apache-2.0 | 2026-05–06 |
| noisyduck/ffw_bg2_rev4_tm_*(sort·kitchenware 등 18개) | bg2_rev4 | v2.1·30 | 20–47 각 | 0.5–1.2 GB | 머리 1·손목 2 | 긴 다단계 문장(컵 분류·식기) | apache-2.0 | 2025-08–09 |
| rllab-postech/pretrain_aiworker_bg2_lance | 19-D 혼합 | lance(LeRobot 아님) | 11,605 / 1,984,298 | 366.8 GB | 3+2 | — | other | 2026-06-12 |

- `rllab-postech/pretrain_aiworker_bg2_lance`는 외부(POSTECH RL 연구실)가 **RobotisSW 196 + Dongkkka 110 + RB2 등 308개 저장소를 모은 재포장본**이다. 카드의 출처 표가 이 생태계의 좋은 색인이지만, 병합본과 그 조각(`_edit`, `task_72to120_*` 여러 판)을 함께 넣어 **같은 편이 여러 번 들어 있다**(예: RB2와 `Dongkkka/…pick_total_1209_merge`가 편·프레임 수까지 동일). 원본을 직접 쓰는 편이 낫다.
- **RB2의 정체**: `ROBOTIS/Task_0002`는 `Dongkkka/ffw_bg2_rev4_pick_total_1209_merge`(857편·85,474프레임, 11문장 동일)의 공식 재게시다. `pickup_obj_*`(11-24–27)는 그 전 단계로, 지시문 형식("Pick up the X with the left gripper and place it into the box below.")과 편 번호가 달라 **RB2와 겹치지 않는 별도 편**으로 보인다(같은 공구 벽·같은 조작 방식). [확인 필요: 영상 해시 대조는 안 함]

## 3. 프레임으로 본 것 (시트: 파드 `frames/<저장소>/sheet.jpg`)
- **pickup_obj_1127**: 검은 공구 벽(튜브·붓·칫솔·드라이버·흰 상자·통)에서 한 팔로 집어 아래 노란 상자에 넣는다. 편의 **약 1/3(앞쪽 편 0–179 대부분)은 머리가 위로 들려 노란 상자가 영상 밖**이고 놓는 순간 그리퍼도 영상 아래 밖이다(ep0 f99·ep30 f113 — RB1과 같은 C3 위반). **편 180 이후는 머리가 내려와 상자와 그리퍼가 놓기 순간 보인다**(ep240 f144·ep270 f129·ep180 f129). 첫 프레임에 노란 상자가 보이는 편 67.7 %(아래 40 % 노랑 비율 > 2 %). 머리 관절은 이 판에 기록되지 않았다(16-D) — `1124_total_3`·`1125` 판은 19-D.
- **RobotisSW bg2 과제**(task 2·40·101·122 등): 매 과제 장면이 다르다 — 선반 공구 벽에서 도구 꺼내기, 식탁 병·캔을 상자로, 냉장고에서 음료 꺼내 바구니에, 양손으로 파란 쟁반 사이 물건 옮기기(task 101, 편당 40–49 s·놓기 7–8회). **놓기 순간 그리퍼가 머리 영상에 보인다**(task 101·122·40에서 확인). 머리 관절 `head_joint2`가 편 안에서 0.5–0.6 rad 움직인다(**머리 고정 아님** — 텔레옵 중 머리를 돌림).
- **RobotisSW sg2 과제**(task 166·230·298·322): 선반 과자를 바구니에, 과자 봉지 옮기기, 바구니에 음료 넣기. 놓는 순간 그리퍼가 대체로 보인다(322·230). task 298은 짧은 한 동작(집어 들기)이라 놓기가 없다.
- **손목 영상 방향**: RobotisSW 카탈로그·pickup_obj는 `info.json`에 240×424(가로)로 적혀 있지만 **내용은 90° 돌아간 세로 배치**다(RB1과 같은 현상, 손가락이 위·아래에서 들어옴). 변환 때 RB1처럼 회전이 필요하다 — 저장소마다 프레임으로 확인해야 한다.
- **Merged_PickPlace**: 나무 식탁에 병·캔·과자 2–4개, 지시문이 병 또는 캔. 오른팔이 집어 들어 올리며 끝난다(놓기 없음 → 우리 궤적 끝 규칙 '다음 놓기'가 성립 안 함; 끝 = 들어 올린 뒤 정지로 바꿔야 함). 머리 두 대가 스테레오(1280×720).
- **VINE2_poc_Fail2**: 초록 바닥 상자 안, 주황 상자를 흰 상자 위에 올리다 **떨어뜨림·비껴 놓음**이 프레임에 보인다(ep10·20·30 끝 프레임). 정상판(VINE2_poc)과 같은 장면이라 성공/실패 대비가 된다.
- **noisyduck tm_sort**: 빨강·노랑 컵 4개를 좌우 통에 분류하는 다단계, 30 fps, 양팔.

## 4. 필요별 순위

### (a) MolmoAct 조종 데이터 (오프라인 조종 평가 ≥ 300 스냅샷, 학습 다양성)
1. **pickup_obj_1127_total2** — (i) 두 대상: 같은 공구 벽(첫 프레임 MAD ≤ 8)에서 지시문이 다른 대상을 고르는 편 쌍 601(대상 조합 3종), (ii) 같은 대상·다른 팔 쌍 457. 놓기 순간 그리퍼가 보이는 편(180번 이후 약 2/3) × 편당 접근 구간 스냅샷 2–3장이면 **300장을 넘긴다** — RB2 검증 분할을 늘리지 않고도(현재 계획은 RB2 15 % 해시로 약 390) 조종 평가 세트를 따로 만들 수 있다. 대체 대상 점은 기존 계획대로 Molmo2-ER에 다른 공구를 가리키게 해 얻는다.
2. **Merged_PickPlace**(라이선스 확인 뒤) — 한 편 안에 병·캔이 함께 있는 장면이 많아 "지시문이 고르는 두 대상" 스냅샷을 편마다 만들 수 있다. 다만 카메라 해상도·배치가 달라 별도 원천으로 보고해야 한다.
3. RB2(현행) — 이미 두 대상 구조(426쌍, `molmoact_real_readiness.md`).
- **없는 것**: 같은 팔·같은 목표로 일부러 돌아가는 경로 시연. 1번의 '다른 팔' 쌍은 경로 차가 크고 팔 선택까지 바뀌어 MolmoAct의 '궤적 편집' 평가와는 뜻이 다르다(보조 지표로만).

### (b) 실데이터 확장 (기본 학습·E-SR1d식 분기)
조건: 머리 + 손목, 놓기 때 머리 영상에 그리퍼, 관절·행동과 fps, 라이선스.
1. **pickup_obj_1127_total2**(편 180 이후 위주, 약 540편) — 기종·카메라·10 fps·16-D가 RB1/RB2와 같아 **`tools/se2e_convert.py`에 DATASETS 한 줄 + ROTATE_CW(손목) 추가로 변환 가능**(작업량 작음). 머리가 들린 앞쪽 편은 C3 위반이라 궤적 라벨에서 빼거나 따로 보고.
2. **RobotisSW bg2_rev4 카탈로그**(2,271편, 10 fps가 117/130 저장소) — 같은 기종·19-D. 저장소가 130개로 쪼개져 있어 **다중 저장소 적재**(DATASETS를 목록으로, `_edit` 판 우선·원판과 중복 제거, fps 5·15·30 저장소 제외 또는 리샘플)가 필요 — 작업량 중간. 지시문이 번호뿐이라 과제 문장이 필요하면 VLM으로 붙여야 한다.
3. **RobotisSW sg2_rev1 카탈로그**(5,093편, 대부분 15 fps, 22-D = 19 + 이동 속도 3) — 팔·그리퍼·머리 이름은 같다(이동 받침만 다름). 15 fps라 §62 '원래 fps 그대로'면 H = round(0.5·15) = 8스텝(`se2e_data.episode_rows`는 fps에서 H를 계산하므로 코드는 그대로 돈다), 10 Hz와 섞으려면 리샘플 결정 필요 [결정 필요: 메인]. 크기 78.6 GB는 이번 5 GB 제한 밖 — 과제 일부만 먼저.
- 빼는 것: ROBOTIS Task_0003–0006·Dongkkka `ffw_arm_only` 계열(손목 없음·머리 1280×720 한 대), `chomeed`(다른 손), `rllab` lance(재포장·중복·license other).

### (c) E-AT (Astra 교사 실데이터 오프라인 라벨)
1. **RobotisSW bg2+sg2 카탈로그 322과제** — 과제 다양성이 가장 크다(과제당 10–50편). 라이선스 apache-2.0이 카드에 있어 **외부 API(Astra)로 보내도 되는 유일한 대규모 후보**다. 과제 번호뿐이라 Astra가 과제 설명까지 라벨하게 할 수 있다.
2. **pickup_obj_1127_total2** — apache-2.0, 지시문 있음.
3. **VINE2_poc + Fail1·Fail2**(apache-2.0) — 실패·재시도 표본(99편). 한 팔·단순 과제라 규모는 작다. `chomeed` dagger/failure(apache-2.0)는 기종이 달라(다른 손) 보조로만.
- Astra에 보내면 안 되는 것: RB1, Merged_PickPlace, Pick_chestnuts·Task_9000xx, Dongkkka 병합본 대부분(라이선스 표기 없음).

## 5. 권고
1. **바로 추가(내부 학습·평가)**: `Dongkkka/ffw_bg2_rev4_pickup_obj_1127_total2`를 **RB3**로. 변환 = `se2e_convert.py` DATASETS에 한 줄 + 손목 회전(프레임 확인 후) + 16-D(머리·리프트 없음 — RB1과 같음). 받기 3.3 GB. 조종 오프라인 평가 세트(편 180 이후, 두 대상 쌍·같은 대상 다른 팔 쌍)로 E-MAR-S 준비의 '데이터 없음'을 부분적으로 푼다. 원래 목적(같은 팔 대체 경로)은 여전히 새 수집 필요.
2. **다음(과제 다양성)**: RobotisSW bg2_rev4 카탈로그부터(11.4 GB, 10 fps 저장소만), 다중 저장소 적재기를 `se2e_convert.py`에 추가. sg2_rev1은 fps 결정 뒤.
3. **E-AT 표본**: 카탈로그(apache-2.0)에서 과제마다 편 1–2개 + VINE2 Fail 편으로 Astra 라벨 시험 표본을 뽑는다(비용은 E-AT 사전 등록에서 계산).
4. **Merged_PickPlace**: 두 대상 구조가 좋고 최신이지만 라이선스 없음 → ROBOTIS에 문의(RB1과 같이) 전까지 내부 평가만, 외부 API 금지.
- **라이선스 위험**: (1) `RobotisSW`·`Dongkkka`는 **직원 개인 계정**이고 카드의 `apache-2.0`은 Physical AI Tools/LeRobot 업로드 도구가 자동으로 넣는 기본값일 수 있다 — 조직 공식 공개(Task_0002)보다 약하다. 논문·공개 산출물 전 ROBOTIS 확인 권장. (2) 사람(조작자·지나가는 사람)이 머리 영상에 자주 찍힌다 — 공개 산출물에 프레임을 실을 때 주의. (3) 같은 편이 여러 저장소에 중복(병합본·`_edit`·fps10판) — 학습/검증 분할 누수 주의(저장소가 아니라 편 내용 기준으로 분할).
- **신뢰도**: 발행자 = 제조사 직원(ROBOTIS 조직 구성원)이지만 좋아요 0, 내려받기 20–600 수준. 과제 번호의 뜻·성공 여부 표기는 없다(전부 성공 시연으로 가정 — 프레임 표본에서 실패는 못 봄).

## 6. 산출물 위치
- 파드 `/data/harvest/data/robotis_survey/`: `meta_all.jsonl`(1,150개 메타), `meta/`(저장소별 JSON), `eps_stats.json`(과제별 편 범위), `frames/<저장소>/sheet.jpg`·`ep*.json`(놓기 프레임·머리/리프트 범위)·`ff/`·`ff_stats.json`·`pairs.json`·`mosaic_first.jpg`, `code/`(조사 스크립트 사본: `meta_survey.py`·`sample_frames.py`·`first_frames.py`·`pairs.py`·`eps_stats.py`). 표본 원본(편 parquet·mp4)은 `frames/*/raw/`에 남김(합 약 0.37 GB).
- 로컬 작업 폴더 `D:\tools\scratch_qdd\robotis_survey`(목록·분석 스크립트·시트 사본).
