# E-TP1 — 3인칭 행 끔 대 켬 (8B, L9 v2 전용, 사전 등록)

- **조기 시범이다.** 7,500편 점검을 앞당겨 지금 있는 편으로 돌린다. 본 판단은 편이 더 모인 뒤 같은 규칙으로 다시 한다.
- 작성: E-GP2 에이전트(메인 지시 10-02 21시대 KST). **빌드·학습 전에** dev에 커밋한다. 결과는 `docs/stage3/results/tp1.md`에 적는다.
- 근거: 사용자 10-02 지시(3인칭 행은 따로 묶음, ego 묶음에는 3인칭 0, `build_v2.py --third-person on --both`). 금지 그대로다: 교사·Astra, 유료 API, 파드 생성·삭제, main, L9 양산 프로세스, 실행 중 스크립트 수정.

## 0. 질문
- 같은 ego 행에 같은 편의 3인칭(외부 카메라) 변형 행을 더해 학습하면(on), ego 성능이 끔(off)보다 나빠지지 않는가(비열등)? 좋아지는가?

## 1. 데이터 (빌드 때 동결)
- 대상은 `/data/harvest/l9v2/pilot1/collect`(AI Worker)와 `/data/harvest/l9v2/pilotF/collect`(Franka)다.
  - **학습** = `collect/train`
  - **보류** = `collect/holdout`(L9 주인의 보류 정의, `alloc9.holdout_defs`)
- 조건: `success`, `max_dq_rad ≤ 0.04`, 로봇 ∈ {ffw_sg2, franka_mast}, `gate_move` 제외, **`spec_of(meta) = L9v2-spec-final`만**. 편 목록은 `/data/harvest/out/tp1/data/episodes.json`이다.
- 빌드: `tools/tp1/tp1_build.py`. `tools/l9/build_v2.py --third-person on --both --success-only`(spec 기본값)와 같은 `build9.build(slots=True, third_person=True, seed=0)`를 64조각으로 나눠 병렬로 돈다.
  - **off** = ego 행
  - **on** = 같은 ego 바이트 + 3인칭 행
- 단언(어기면 멈춤): ego 바이트 동일, ego 묶음 3인칭 0, 3인칭 묶음은 전부 3인칭, 슬롯 파싱 오류 0, 머리 없는 행 0, 보류 3인칭 0, spec 관문 통과(한 spec·mono 겹그림·한 템플릿 계열·legend none).
- 보류 행은 반복 없는 ego만 쓴다(`train=False`, 3인칭 끔).
- **변경 1 (빌드 첫 단계에서, 학습 전)**: `collect/holdout` 폴더의 정의 8개 중 5개가 `collect/train`에도 편이 있었다(시범 때 생긴 편). 또 holdout 성공 편은 94편뿐이었다.
  - **보류 정의** = holdout 폴더에 나온 정의 ∪ E-GP2 해시 정의(`sha256("gp2:<task_id>") % 5 == 0`)로 바꾼다.
  - 두 폴더 어디에 있든 보류 정의의 편은 전부 평가에만 쓰고, 학습에는 넣지 않는다. 겹치는 정의 0은 코드가 단언한다.

## 2. 팔·시드·레시피
| 실행 | 팔 | 시드 | 카드 |
|---|---|---|---|
| off_s0 | 끔 | 0 | 78dc GPU1 |
| on_s0 | 켬 | 0 | 78dc GPU2 |
| off_s1 | 끔 | 1 | 78dc GPU3 (A/A) |
- 레시피는 E-GP2와 같다(Qwen3-VL-8B LoRA r16 α32, lr 1e-4 코사인, 미세 배치 8 × 누적 2). `tools/gp2/gp2_worker.sh`(`GP2_O=/data/harvest/out/tp1`, `GP2_TAG=_tp1`)로 돌린다.
- 걸음은 E-GP2 2단계와 같은 식 round(1,632 × 그 팔 행 / 78,745)이다. on은 행이 많아 걸음도 많다. 같은 ego 행을 대략 같은 비율로 보게 하려는 것이다.
- 25 %·50 % 상태 스냅숏도 평가한다(학습 곡선, 보고만).

## 3. 평가 (`tools/gp2/gp2_eval.sh`, vLLM, 오프라인)
- **L9 v2 보류**(collect/holdout, ego): 모든 모델에서 잰다.
- **L8-X 7세트**(E-HCAM8과 같음): 최종 모델만 잰다.
- **eval_ood**(처음 보는 물체)는 아직 편이 0이라 이번에는 뺀다. 생기면 같은 모델로 보탠다(보고만).
- 서빙 카드는 E-GP2 평가가 끝나 빈 카드부터 쓴다: x2 GPU0, x3 GPU0, 7a2a GPU2.

## 4. 지표 (`tools/tp1/tp1_report.py`)
- **주 지표(ego)**: L9 보류 control 행의 점 픽셀 오차. 라벨 점까지이며, 중앙값과 **20 px 초과율**을 본다. E-GP2 변경 2와 같은 이유로 L9 v2 행에는 3D mm를 쓰지 않는다.
- 보조:
  - 잡기 행(라벨에 approach가 있는 행)의 접근 계열 정확도와 rot ±1
  - 답 형식 위반율
  - L8-X 7세트의 3D 중앙값과 20 mm 초과율

## 5. 판정 (결과 전 고정, 최종 모델)
- 짝 부트스트랩: 행 단위, 10,000회(L8-X는 2,000회), 시드 0.
- **A/A 여유**: off_s1 − off_s0의 같은 통계에서 m = max(바닥값, 95 % 반폭, |관측 차|)로 정한다. 바닥값은 다음과 같다.
  - 20 px 초과율 2 %p
  - 중앙값 3 px
  - 계열 정확도 3 %p
  - L8-X 20 mm 초과율 2 %p
- **ON_NONINF**: on_s0 − off_s0와 on_s0 − off_s1이 **둘 다** 다음을 만족하는 경우다.
  - 20 px 초과율 차 상한 ≤ m
  - 중앙값 차 상한 ≤ m
  - 계열 정확도 차 하한 ≥ −m
  - L8-X 각 세트 20 mm 초과율 차 상한 ≤ m
- **ON_BETTER**: ON_NONINF이면서 20 px 초과율 차가 두 비교 모두 ≤ −m이고 상한 < 0인 경우다.
- **ON_WORSE**: 위 비열등 가운데 하나라도 어긴 경우다.
- 채택: ON_NONINF와 ON_BETTER면 3인칭 행을 넣는다(사용자 기본 방침 유지). ON_WORSE면 빼고 원인을 본다. ON_WORSE면 버리기 전에 한 번 다시 검증한다(시드 1개를 더하거나 3인칭 비율을 절반으로 낮춰 확인).
- 보류 잡기 행이 200 미만이면 '표본 한계'를 붙인다.
