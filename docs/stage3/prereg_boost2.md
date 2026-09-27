# boost2 — D(점 + 깊이) 강화: B-D 폐루프 실패 상태를 모아 참값으로 다시 라벨하고 1회 DAgger (8B, 무료, 사전 등록)

- 작성: E-STRIP8 에이전트, 2026-09-27T05:1xZ(UTC, KST 14:1x). **실행 전에** 커밋한다. 결과는 `docs/stage3/results/boost2.md`.
- 근거: 사용자 지시(통제자 경유) "D 성능을 더 올려야 한다". B-D는 L8-X 폐루프에서 인식·의도 고리로 실패한다(`results/dist8.md` 5b). boost1(코드 수정)과 따로, 모델이 스스로 만든 상태에서 참값을 배우게 한다. E-TEACH-L8 등록 5.3의 DAgger를 D 줄기에 적용한다.
- 비용: **유료 0원**, GPU만(x2 GPU 1 한 장에서 체인: Isaac + vLLM + 학습).

## 0. 자체 검사
- **무엇을 결정하나**: 학습자(B-D)가 간 상태에 참값 라벨을 붙여 한 번 더 학습(DAgger 1회)하면 폐루프 실패가 줄어드는가. 오프라인 새 높이·새 물체 오차도 나빠지지 않는가.
- **이 표본으로 가를 수 있나**:
  - 오프라인: L8-X dev_x 1,613·OOD-H 860·OOD-O 394 스냅숏을 짝 부트스트랩한다.
  - 폐루프: boost1과 같은 8편(OOD-H 0.98 4편 + OOD-O 0.86·0.94 각 2편), 수정 끔·켬 두 설정 → **방향만**.
- **이미 본 것**: boost1 수정 전(before) 폐루프 일부(OOD-H 0.98 4편 중 성공 2, OOD-O 0.86 2편 접근 실패)와 dist8 5b 분해.

## 1. 수집 (`harvest/teach_strip8/dagger.py`, `run_dagger.py`)
- 장면: L8D b1 동결 묶음(`b1_phase1_x`, digest `da087e26d85e5c6f`)의 TRAIN 장면. 한 단계·가구 없는 과제만, 세계 폴더(변형 × 탁자 높이)마다 시드 순 앞 **8편**(`tools/teach_strip8/dagger_pick.py`). 같은 장면·같은 시드지만 학습자가 모니 상태는 새롭다. 평가 세트(보호 70000–, dev_x)는 쓰지 않는다.
- 편 한 번의 흐름: L8D 수집 경로(XCollector + PtEpisode, 요청·영상·깊이·참값 라벨 저장)를 그대로 쓰되, 실행 명령을 **학습자 답**으로 바꾼다.
  - B-D vLLM에 같은 상태의 d-min 요청(`min_format.d_text` + 고리만 영상)을 묻는다.
  - 답이 무효면 참값 명령을 실행한다(수를 적음). 참값 라벨은 늘 같이 저장한다(교란 없음, p = 0).
  - 한도: 조기 종료 20호출·60 s(폐루프 평가와 같음).
- 학습자가 참값과 다른 명령을 낸 다음 호출은 `prev_kind = dagger`(회복 상태 가중 2배, L8 `repeat_of`)로 표시한다.

## 2. 학습
- 행: DAgger 수집 → `min_format.build(..., "d-min")`(L8 반복 가중 + 보조 QA, 점 라벨 검증 안 된 행 제외) + **B-D 학습 행 전부**(`dist8/data_b1/train_d-min.jsonl`) = 합본(추가 방식).
- **걸음 수** = 816 × 합본 행 / B-D 행(B-D와 같은 데이터 통과 비율). 기본 8B에서 새로 학습한다. L8 레시피, seed 0, 미세 배치 8 × 누적 2.

## 3. 평가·판정 (결과 전 고정)
- 오프라인: `dist8/data_x/x_{dev,ood_h,ood_o}_d-min_clean.jsonl` 조종 행, `teach_pt.evaluate --arm pt`. 비교 대상 B-D는 PT-ND 평가(`dist8/eval/b_d-min/x_*_d-min_clean`)를 재사용한다. 짝 차(DAgger − B-D)는 접근 3D 평균, 95 % 구간.
- 폐루프:
  - boost1의 8편(`boost1_pick.txt`)에서 DAgger 모델을 수정 끔·켬 두 설정으로 돌린다. 비교 대상은 boost1의 B-D before·after(같은 편·같은 설정).
  - 영상 `/data/harvest/videos/boost2/{dagger_off,dagger_on}/` + 색인.
- **ADOPT**(DAgger 모델을 D 기본으로):
  - 폐루프 성공(수정 켬 설정, 8편)이 B-D after보다 2편 이상 많다.
  - dev_x 접근 3D 중앙이 B-D + 1 mm 이하다.
  - OOD-H 짝 구간 상한이 +2 mm보다 작다.
- **PARTIAL**: ADOPT는 아니지만, 폐루프 성공이 1편 이상 늘거나 OOD-H 또는 OOD-O 짝 구간 상한이 0보다 작다(BETTER).
- **NOT_ADOPT**: 그 밖.
- 기술: 수집 편 수·성공률·학습자 답 비율·대체(fallback) 수, 실패 단계 분해(인식·의도·실행), 수정 끔 설정 비교.

## 4. 말하는 것과 못 하는 것
- 말하는 것: 학습자 방문 상태의 참값 라벨 1회가 D 폐루프 실패를 줄이는지(방향).
- 못 하는 것: DAgger 여러 회의 수렴, 계산량 동일 비교(합본 걸음 수가 더 많다 — 결과에 걸음 수를 적는다), 35B, 실물.

## 변경 기록
- (없음)
