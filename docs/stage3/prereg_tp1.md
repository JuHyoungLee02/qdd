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
- **변경 2 (빌드 중, 학습 전)**: 보류가 1,938편(정의 53)이라 모델 하나 평가에 2시간 넘게 걸린다. 그래서 **보류 정의마다 시드 순으로 최대 10편**만 평가한다(≤ 530편). 보류 행 빌드는 16조각으로 돈다.
- **변경 3 (10-02 22시대 KST, 사용자 지시 "3인칭을 넣고 좌우 혼동을 그걸로 풀어라" → 메인; 학습 전, 앞선 빌드는 중단·폐기)**
  - **방향 문장**: 모든 행 요청에 다음 고정 문장을 넣는다. "Directions in the task (left, right, front, behind) are in the robot's frame, not the camera image." 대상은 ego·3인칭 행 모두이고, L9 코드 7d5523c의 `views9.FRAME_NOTE`를 쓴다.
    - 메인 지시는 '3·4팔에만'이었다. 그런데 off 팔도 아직 학습 전이어서(앞 빌드 중단) **모든 팔이 같은 문장을 갖는다**. 그래서 off 대 on은 3인칭 행만, on 대 on+aux는 보조 행만 다르다.
    - 게이트 `frame_note_missing = 0`이다.
  - **보류 동결**: 보류 정의 = `alloc9.HOLDOUT_FROZEN` ∪ holdout 폴더 정의 ∪ GP2 해시 정의다. 학습에는 `split = train`이면서 is_holdout가 아닌 편만 쓴다. 분할 게이트(보류 정의·다른 split·ood_o 물체·ood 방 행 0)를 `specgate9.gates(train=True)`로 확인한다.
  - **4번째 팔 on+aux (onaux_s0, 78dc GPU0, E-GP2 b_s2 뒤)**: on 행 + 보조 행이다. 보조 행 수 = on 행의 15 %, 즉 전체의 ≤ 15 %다. 근거는 `docs/research/perspective_frames_2026-10-02.md`(dev 778be17) §4 (2)의 세 종류다. 모두 시뮬 참값(labels gt 로봇 좌표, cams.json·external_cams 카메라)에서 만들고, 다시 렌더하지 않는다(`tools/tp1/tp1_aux.py`).
    - P: 로봇 기준 방향 점찍기. "물체의 로봇 왼/오른/앞/뒤 12 cm 바닥점"이며, 점과 관점이 결합된 문항이다.
    - Q: 관점 QA. "로봇 시점에서 물체가 집게의 좌/우/앞/뒤인가"다.
    - Y: 카메라-로봇 상대 요. same·left·right·toward 네 구간이다.
    - 이미지는 ego 행이면 머리 영상, 3인칭 행이면 3인칭 영상이다.
    - 위험을 규칙으로 둔다. (a) 거울반전 증강은 없다. (b) 제어 행은 on과 바이트까지 같다. 보조 행 요청에는 카메라 자세 글이 없다(카메라 줄이 지름길이 되지 않게).
    - 투영 검사: 머리 투영과 라벨 픽셀 차 중앙값 ≤ 15(0–1000 척도), 3인칭 목표 투영의 화면 안 비율 ≥ 0.7. 어기면 멈춘다.
  - **평가 추가**(모든 팔, 최종 모델; 관점 문항은 25·50 %에도):
    - 관점 보류 문항 = 보류 편의 머리 정면(head_std)·머리 기울임(head_tilt = 무작위 머리 기하)·3인칭 층 × P·Q·Y이며, 층마다 같은 수로 최대 2,400문항이다.
    - 방향 단어가 있는 지시의 3인칭 보류 행(`l9_eval_tpdir`)도 평가한다.
  - **4번째 팔 판정**:
    - 주 지표는 관점 정확도다. 3인칭+기울임 층의 P(예측 점이 정답 점에 반대 방향 점보다 가까움)와 Q(정답 일치)를 합친 정확도다.
    - **AUX_BETTER** = onaux_s0 − on_s0가 ≥ max(3 %p, off A/A 같은 통계)이고 95 % 하한 > 0이며, ego 비열등(§5 기준, on_s0 대비)을 만족할 때다.
    - **AUX_SAME**은 그 밖의 비열등이고, **AUX_WORSE**는 ego 비열등을 어긴 경우다.
  - on 대 off 판정(§5)은 그대로다. 걸음은 팔마다 같은 식으로 정한다(onaux는 행이 많아 걸음도 많다).
- **변경 4 (10-03 00시대 KST, 학습 전)**: 병합 게이트에서 학습 74,765 ego 행 중 '같은 상황 다른 답' 모순이 1건 나왔다(`specgate9.contradictions`). 그 상황의 행을 **모두** 뺀다(ego 행, 3인칭 쌍둥이, 보조 행). 같은 행이 off·on 두 묶음에서 함께 빠지므로 ego 바이트 동일은 유지된다. 뺀 수는 `check.json`의 `contradiction_drop`에 남긴다. 병합 실패(23:05 KST)와 세션 중단 때문에 78dc 4장이 약 1시간 놀았다.
- **변경 5 (10-03 01시대 KST, 결과 전 — 학습 재시작)**: on·onaux 학습이 첫 배치에서 죽었다. 원인은 4장 행(머리+손목 둘+3인칭)에서 `teach_l8.dataset.user_content`가 위치 고정 라벨 3개만 알았기 때문이다(IndexError).
  - 같은 원인으로 슬롯 스키마 행의 이미지 라벨이 슬롯과 어긋나 있었다. 예를 들어 왼손목·3인칭 영상이 "right wrist camera"나 "head depth"로 붙었다. off 팔도 마찬가지였다.
  - 고침:
    - `image_views`가 있는 행은 슬롯 이름 라벨을 쓴다(head / left wrist / right wrist / third-person camera). 학습 `train.py`와 평가 `evaluate.py`, `tp1_persp_eval.py`가 같은 함수(`dataset.image_labels`)를 쓴다.
    - 보조 행에 `image_views`를 붙인다.
    - vLLM 이미지 상한을 3에서 4로 올린다.
    - `image_views`가 없는 행(L8·E-GP2)은 예전과 같다.
  - 네 팔 모두 처음부터 다시 학습한다. 앞선 off 진행분(약 500걸음)은 `out/tp1/aborted_labels_*`에 남긴다. 데이터 행(동결 목록·병합)은 같다.
- **변경 6 (10-03 02시대 KST, 사용자 지시, 결과 전)**: 주 평가 세트는 **l9_test** = L9 v2 보류 중 `HOLDOUT_FROZEN` 정의 + eval_ood다. 이후 모든 L9 학습 점검도 같다.
  - 이 빌드에서는 보류 496편 중 HOLDOUT_FROZEN 정의 67편(control 521행)이 해당한다. eval_ood는 아직 0편이라, 생기면 보탠다.
  - §5의 ego 판정(20 px 초과율·중앙값·계열 정확도)은 l9_test 행으로 한다. 보류 전체(정의 53)는 보조로 보고한다(`tp1_report.py --subset all`).
  - L8-X는 보조로만 쓰고 **'old-convention'**(L8 라벨 규약) 표시를 붙여 보고하며, 판정에서는 뺀다. L8-X-v2 재라벨은 사용자 지시로 취소했다.
  - 관점 문항(4번째 팔 주 지표)은 그대로 보류 전체 편에서 만든 층화 문항을 쓴다.
