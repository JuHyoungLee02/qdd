# E-OPR2 — 공개 점 비율 재판정(ni_judge) + ±10 %p 비율 판 (8B, 무료, 사전 등록)

- 작성: OPR2 에이전트, 2026-09-29 KST (UTC 시각은 커밋 시각). 근거: user-log 193(재판정 먼저, 시드 0, ±10 %p), 186(A/A 보정 여유 + 중앙값·20 mm 실패율).
- **1단계 계산 전, 2단계 학습 전에** 커밋한다. 결과는 `docs/stage3/results/opratio.md`의 새 절 'ni_judge 재판정'(1단계)과 'E-OPR2 ±10 %p'(2단계). 원래 판정 글은 고치지 않는다.
- 유료 0원. 78dc 파드(`juhyoung-q-78dc`, p-test2), 모든 파일 `/data`, 코드 고정 사본 `/data/harvest/code_opr2_<이 커밋>`.

## 비율 축 (통제자 정정 09-29)
- **비율 r = 공개 행 / 기본 행**(open_over_base). E-OPRATIO8의 p(25·50·75 %)와 user-log 177의 '75 %'가 이 축이다.
- 현재 recipe = dryrun2 `/data/harvest/out/final35/dryrun2/train_open.jsonl`: 기본 78,745 + 공개 46,803(풀 31,202 × 반복 상한 1.5) → r = 0.594, 파일 안 공개 몫(open_share) = 0.373.

## 1단계 — 기존 산출물 재판정 (학습 없음)
- **자료**: `/data/harvest/out/opratio/eval/op_{p0,p25,p50,p75,p0_s1,p75_s1}`(E-OPRATIO8·S1), `/data/harvest/out/poolv/eval/pv_old_s{0,1}`(= 현재 recipe r 0.594 그 자체, E-POOLV8 OLD; L8-X는 dev·OOD-O만 평가됨). G 행 = `/data/harvest/out/opratio/g_eval.jsonl`(1,577행, gsplit_g166 보류 분할).
- **팔 비교(모두 X 대 p0)**:
  - 주: p75 대 p0, 시드 0·1 합침(35B '75 % 채택'의 근거 비교).
  - 보조: p25·p50·p75 각 대 p0(시드 0 단독); p25·p50 대 p75(시드 0, '다른 팔이 더 나은가').
  - recipe 직접: pv_old(r 0.594) 대 p0, 시드 0·1 합침 — L8-X는 dev·OOD-O만, G 전부. 기본 행 파일은 opratio `base_d-min.jsonl`과 행 집합이 같은지 먼저 확인해 결과에 적는다(다르면 이 비교는 참고로만).
- **규칙(user-log 186)**:
  - L8-X 7세트: `tools/teach_pt/ni_judge.py judge`, 여유 = `ni_margins_ul186.json`(A/A 5쌍 — E-VIEW8 A0·A1·A2, E-OPRATIO8 p0·p75). 세트마다 중앙값 차 상한 ≤ 중앙값 여유 **그리고** 20 mm 초과 실패율 차 상한 ≤ 실패율 여유면 비열등.
  - G 6하위(BEHAVIOR·MolmoBot Franka·RBY1·RB2·RefSpatial·Where2Place) + 전체: E-POOLV8(`poolv_compare.py`)과 같은 방식 — 적중률 차(나쁜 쪽 부호)와 라벨 4하위의 px 오차 차, 짝 부트스트랩 10,000(시드 0), 여유 = E-OPRATIO8 A/A 두 쌍(p0 s0/s1, p75 s0/s1)의 |부트스트랩 차| 95번째 백분위. 상한 ≤ 여유면 비열등.
  - 주의(적어 둠): A/A 여유 쌍에 p0·p75 자신이 들어 있다(순환이 조금 있음). 여유는 한 시드 대 한 시드 폭이라 시드 합친 비교에는 약간 너그럽다.
- **판정**: 팔이 L8-X 7세트(recipe 직접은 2세트)와 G 7항목 모두 비열등이면 '자격'. G 전체 적중 차 하한 > 0이면 'BETTER'. **현재 recipe가 선다** = 주 비교(p75 두 시드)와 recipe 직접 비교가 모두 자격이고, 시드 0에서 p25·p50 중 p75 대비 '자격 + G 전체 적중 유의하게 높음'인 팔이 없을 때. 평균·'내려가지 않음'은 보고만 한다.

## 2단계 — r = 0.49 / 0.59 / 0.69 (8B, 시드 0)
- **팔**(반복 상한 1.5 유지, 공개 풀 = dryrun2 파일의 공개 행 그대로 — `open_pool.py`로 다시 만들지 않는다: 지금은 agibot_p0 불량 209행을 끌어옴):
  - **r 0.59** = E-POOLV8 `pv_old_s0`(dryrun2 파일, 125,548행, 2,602걸음, 시드 0, E-OPRATIO8 8B와 같은 레시피) → **다시 학습하지 않는다**. 없는 L8-X 5세트(OOD-H·D·S·T·H-lift)만 같은 병합 모델로 평가한다.
  - **r 0.69** = 공개 46,803행 전부 + 기본을 round(46,803 / 0.69) = 67,830행으로 부분 추출(무작위, 시드 8) → 114,633행, open_share 0.408.
  - **r 0.49** = 기본 78,745행 전부 + 공개를 round(0.49 × 78,745) = 38,585행으로 부분 추출(46,803 공개 행에서 비복원, 시드 8; 풀 대비 실효 반복 약 1.24) → 117,330행, open_share 0.329.
  - 공개/기본 구분 = 행의 `aux_kind`가 `open_`으로 시작하면 공개. 개수(78,745 / 46,803)가 맞지 않으면 멈춘다. G 가드(`xemb.gsplit check`) 통과 필수.
- **레시피**(E-OPRATIO8과 같음): Qwen3-VL-8B-Instruct LoRA r16 α32, lr 1e-4 코사인 warmup 20, bf16, 비전 동결, 미세 배치 8 × 누적 2, `--save-every 200`, 시드 0. 걸음 = round(1,632 × 행 수 / 78,745) → r 0.69 = 2,376, r 0.49 = 2,432(r 0.59 = 2,602).
- **평가**: G(`opratio/g_eval.jsonl` 1,577행) + L8-X 7세트(`dist8/data_x/x_*_d-min_clean.jsonl`, d-min, 접근 3D), 한 GPU에서 vLLM.
- **여유**: 시드가 하나라 A/A는 **기존 E-OPRATIO8 시드 쌍(p0 s0/s1, p75 s0/s1)**에서 잰다 — L8-X는 `ni_judge.py aa`를 이 두 쌍으로, G는 1단계와 같은 두 쌍.
- **판정(r 0.49·0.69 각각 대 r 0.59)**: 자격 = L8-X 7세트 + G 7항목 모두 비열등. **바꾼다** = 자격이고 (G 전체 적중 차 하한 > 0 또는 L8-X 어느 세트의 실패율 차 상한 < 0). 두 팔 다 '바꾼다'면 G 전체 적중이 높은 쪽. 아니면 **r 0.59 유지**. 한 시드라 결과는 '방향 신호'로 적고, 35B 비율 변경은 통제·사용자가 정한다.
- **자원**: 78dc GPU3(지금 빈 카드). 00:30 KST 뒤 GPU0·1은 adc9be77f7286dd40와 협의한 경우에만. 9/30 09:30 KST 전에 끝낸다(E-C35가 4장 전부 씀). 백그라운드 사슬, 학습 3회 재시도(재개), 완료 표지 `/data/harvest/logs/opr2/opr2.log`의 `STAGE2_DONE`.

## 변경 기록
