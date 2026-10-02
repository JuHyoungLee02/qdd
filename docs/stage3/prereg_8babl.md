# E-8BABL — 8B 오프라인 비교 4종 (사전 등록)

- 작성: 통제자 요청(10-03) Sonnet 에이전트, E-TP1(`docs/stage3/prereg_tp1.md`, dev cfd6e676) 파이프라인을 **그대로 복제**해 돈다(episodes.json·build9·gp2_worker.sh·py.sh·vllm.sh·harvest.teach_pt.evaluate 전부 원본, 사본 코드에서만 호출).
- 금지 그대로: 교사·Astra, 유료 API, 파드 생성·삭제, main 커밋, 재생기·씬·로봇·계획기 수정, 실행 중 스크립트 수정(전부 `/data/harvest/code_8babl_r1`, `code_tp1_5b4c66e`의 사본).
- 데이터는 E-TP1이 이미 동결한 `/data/harvest/out/tp1/data/episodes.json`(train 5,733편: ffw_sg2 3,197·franka_mast 2,536 / eval 496편: ffw_sg2 187·franka_mast 309)을 그대로 쓴다. 레시피는 E-TP1·E-GP2와 같다(Qwen3-VL-8B LoRA r16 α32, lr 1e-4 코사인, micro 8 × accum 2, 3 epoch, 걸음 수 식 round(1,632 × rows / 78,745)). 시드 1개(0).
- 행 빌드는 ego만(off 레시피: `slots=False, third_person=False, camera_line=False`) — 네 실험 다 3인칭 변수를 건드리지 않으므로 off와 바로 비교 가능.

## 실험 1 — rationale 필드 켬/끔
- **질문**: 답 앞에 build-time "왜"(`rationale9.build`)를 넣으면(on) off_s0_final(끔, 이미 완료: px_median 16.6, fam_acc 0.8077, rot_pm1 0.1923, n_point_label 237/407) 대비 점 오차가 나빠지지 않는가.
- **데이터**: episodes.json train 전체, robot=all, `build9.build(..., rationale=True)`. 평가는 off_s0_final과 **같은** `l9_eval_off.jsonl`(공유 보류 행).
- **실행**: `ration_on_s0`, 78dc GPU0.
- **판정**: 비열등 여유 m = max(바닥값, off A/A 95% 반폭) — E-TP1 §5와 같은 바닥값(20px 초과율 2%p, 중앙값 3px, 계열정확도 3%p). ON_NONINF면 유지, 아니면 버리기 전 재검증 1회.

## 실험 2 — 오버레이 단색 vs 팔별 색(+손끝 표시) — **건너뜀**
- 이유: 머리 오버레이(그리드·TCP 링·낙하선)는 **시뮬 수집 시점**에 `harvest/astra_solo/episode.py`(`head_overlay`)에서 RGB에 바로 그려져 저장된다. TP1/build9는 이미 저장된 이미지를 그대로 읽으므로, 색을 바꾸려면 **새 시뮬 수집**이 필요하다 — "재생기·씬·로봇·계획기 수정 금지" 규칙과 "실행 중 스크립트 수정 금지"를 지키는 오프라인 재구성 범위를 벗어난다. 사용자 승인 시 별도 수집 작업으로 분리 제안.

## 실험 3 — perspective aux 행 켬/끔 — **E-TP1 재사용(신규 학습 없음)**
- E-TP1의 `on_s0_final`(aux 끔, train_on.jsonl) vs `onaux_s0_final`(aux 켬, train_onaux.jsonl)이 **이미 이 비교 그 자체**다(둘 다 머지·vLLM eval 완료, `report_final.json`의 `on_s0_final`/`onaux_s0_final`·`compare.onaux_s0-on_s0@*` 참조). 중복 학습 대신 그 보고서의 수렴값을 그대로 가져와 쓴다. E-TP1 §5 변경3의 AUX_BETTER/SAME/WORSE 판정을 그대로 채택.

## 실험 4 — leave-one-robot-out (LORO)
- **질문**: 한 로봇(ffw_sg2 또는 franka_mast)을 학습에서 완전히 빼면, 그 로봇에 대한 오프라인 성능이 (a) 그 로봇을 포함해 학습한 off_s0_final 대비 얼마나 떨어지는가, (b) 그래도 쓸만한 수준인가(px_fail20·fam_acc).
- **데이터**: `loro_exA` = train robot=franka_mast만(ffw_sg2 제외) → 평가는 `l9_eval_off.jsonl`에서 robot=ffw_sg2만 추려낸 행(ffw_sg2 쪽 보류, 약 187편 분량). `loro_exB` = train robot=ffw_sg2만(franka_mast 제외) → 평가는 robot=franka_mast만(약 309편).
- **실행**: `loro_exA_s0` 78dc GPU1, `loro_exB_s0` 78dc GPU2.
- **판정**: 기준선 = off_s0_final의 같은 로봇 부분집합(같은 `l9_eval_off.jsonl`을 robot으로 나눠 집계) 대비 LORO 쪽 20px 초과율·중앙값 차. E-TP1 §5 바닥값과 같은 식으로 "로봇 빼도 비열등"/"로봇 빼면 나빠짐"을 가른다. 이 실험은 설계상 비열등을 기대하지 않는다(핵심 질문은 저하의 크기).

## 배치
| 실행 | 팔 | 카드 | 비고 |
|---|---|---|---|
| ration_on_s0 | 켬 | 78dc GPU0 | off_s0_final과 비교 |
| loro_exA_s0 | franka만 학습 | 78dc GPU1 | ffw_sg2 보류에서 평가 |
| loro_exB_s0 | ffw_sg2만 학습 | 78dc GPU2 | franka_mast 보류에서 평가 |
| (실험3) | — | — | E-TP1 on_s0_final/onaux_s0_final 재사용, 새 GPU 안 씀 |
| 78dc GPU3, x2 GPU0, x3 | 유휴/보조 | — | 빈 카드, 추가 시드나 재검증용으로 둠 |

## 코드·산출물
- 코드 사본: `/data/harvest/code_8babl_r1`(= `code_tp1_5b4c66e` 복제 + `tools/tp1/x8_build.py`, `tools/tp1/x8_filter_eval.py` 추가, 원본 수정 없음).
- 체인: `/data/harvest/out/x8_run.sh`(행 빌드 16조각 병렬 → merge → `tools/l9r/hcam8_build.py combine`(원본, empty base)로 steps 계산 → `tools/gp2/gp2_worker.sh`(원본) 학습·머지 → vLLM + `harvest.teach_pt.evaluate`(원본) 평가).
- 출력: `/data/harvest/out/8babl/`(`train_*.jsonl`, `steps.txt`, `merged/*_s0_final`, `eval/*/summary.json`, `final_summary.txt`, `chain.log`).
- 결과는 `docs/stage3/results/8babl.md`에 적는다(완료 후).
