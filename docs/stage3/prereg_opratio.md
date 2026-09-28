# E-OPRATIO8 — 공개 점 데이터를 얼마나 더할까 (8B, D 줄기, 무료, 사전 등록)

- 작성: PT-ND 에이전트, 2026-09-28 (UTC 시각은 커밋 시각). **학습 전에** 커밋한다(P15). 결과 `docs/stage3/results/opratio.md`.
- 사용자 근거: user-log 164(D에 맞는 가용 데이터 전부, 공통 처리), 165(정확도를 떨어뜨릴 수 있는 데이터는 쓰지 않는다 — 어떤 세트라도 나빠지면 채택하지 않음), 166(공개 데이터 비율은 L8 밖 범용 평가 G로 판정). 목적: 본 규모 35B 전에 공개 점을 몇 % 더할지 정할 근거.
- 유료 0원. GPU = 78dc 파드 `juhyoung-q-78dc` GPU 0–3(통제자 배정), 한 장에 한 팔.

## 0. 자체 검사
- **결정**: 공개 점 추가 비율 p ∈ {0, 25, 50, 75 %} 중 무엇을 35B D 학습에 쓸지. **이 표본으로 가를 수 있나**: G 묶음 약 1,900행·L8-X 7세트 약 4,000상태, 스냅숏 짝 부트스트랩 → 수 % 적중률·수 mm 차를 가른다. 폐루프는 하지 않는다(오프라인만, 비율 선택용).
- **이미 본 것(P16)**: E-DIST8(B-D·B+obj-D: 물체 지시 팩이 OOD-O를 살림, 퇴행 없음), 35B D 대 D-nopub(공개 점이 OOD-O 4.0 대 85.3 mm, dev_x·OOD-H 꼬리 조금 나쁨). G 묶음에 대한 답은 아직 없다.

## 1. 팔 (모두 같은 레시피·시드 0, 차이는 공개 점 몫과 걸음 수뿐)
- **기본** = L8-X b2 번들 D 행(`/data/harvest/out/teach_l8d/data/b2/train_pt.jsonl`, 3,662편, 78,745행: 제어 47,724 + 보조 31,021)을 E-DIST8 최소 요청 D 형식으로 변환(`min_format.convert`, d-min). L8D의 b2는 b1을 포함한다.
- **공개 점 풀**(가드 `tools/xemb/gsplit.guard` 통과 — G 행 0): 작전T 변환 점 `xemb_proto/points/<원천>/records_verified.jsonl`(BEHAVIOR·MolmoBot RBY1·Franka·RB2·RB3·ManiSkill; SAM 검증·이름 검사 통과분), `dh_pack/dh_D.jsonl`, `dist8_packs/obj_pixel.jsonl`, `dist8_packs/t1t4_pixel.jsonl`. 같은 id는 한 번. 작전T가 변환 중인 AgiBot 등은 **이 등록 시점 풀에 없으면 넣지 않는다**(나중에 추가하려면 변경 기록, 답 보기 전).
- **추가 방식**: 공개 행 수 = p × 기본 행 수(풀보다 많이 필요하면 반복, 시드 8; 반복 배수를 결과에 적음). 기본 행은 모든 팔에서 같다.
- **걸음 수 = 행 수에 비례**: S(p) = 1,632 × (1 + p) → 1,632 / 2,040 / 2,448 / 2,856걸음(미세 배치 8 × 누적 2). 1,632 = L8 816걸음의 2배(35B가 L8 기준 2에폭이면 충분 — 여기서 기본은 약 0.33에폭; 4장 동시에 약 4–7 h 안에 끝나는 계산량으로 고정).
- 레시피: Qwen3-VL-8B-Instruct LoRA r16 α32, lr 1e-4 코사인 warmup 20, bf16, 비전 동결, `--save-every 200`(재개 가능).

## 2. 평가
- **G 묶음(주 판정)** — `docs/stage3/gsplit_g166.json`(동결 digest f5679bde1e5aa480)의 보류 분할에서:
  - 공개 보류(점 라벨): BEHAVIOR·MolmoBot Franka·MolmoBot RBY1·RB2(실물 T4 보류) 각 최대 300행(시드 0 표본) — 지표 **점 픽셀 오차**(영상 px, 중앙) + **적중 = 오차 ≤ 영상 대각선의 3 %**.
  - Where2Place 점 질문 100개(Apache-2.0, 평가 전용), RefSpatial-Bench Location·Placement·Unseen(평가 전용) — 지표 **마스크 안 적중률**.
  - 요청 끝에 '0–1000 좌표 JSON {"point": [x, y]}' 답 형식 한 줄을 붙인다(모든 팔 같음).
- **L8-X 7세트(비열등만)**: dev_x, OOD-H, OOD-D, OOD-O, OOD-S, OOD-T, OOD-H-lift — d-min 요청, 접근 3D 오차(E-DIST8 채점기).

## 3. 판정 (결과 전 고정)
- 각 p > 0 팔을 p = 0과 짝 비교(스냅숏 짝 부트스트랩 10,000회, 시드 0).
- **자격(user-log 165)**: (i) L8-X 7세트 **모두** 비열등 — 접근 3D 평균 차 95 % 구간 상한 ≤ +2 mm; (ii) G 하위 세트(원천·벤치마크 6개) **어느 것도 나빠지지 않음** — 적중률 차 구간 상한 ≥ 0이 아니라 하한 > −0.03(적중)·픽셀 오차 평균 차 상한 ≤ +3 px.
- **선택**: 자격 있는 팔 중 G 전체 적중률(행 가중)이 가장 높은 p; p = 0보다 G 전체 적중률 구간 하한 > 0이면 'BETTER', 아니면 'SAME'. 자격 있는 p > 0이 없으면 **p = 0**(공개 점 안 넣음).
- 한 시드·8B라 35B에서 같은 비율을 쓰되, 35B 결과로 다시 확인한다고 적는다.

## 4. 자원·규칙
- 78dc GPU 0–3(렌더 불가 카드 — 학습·vLLM만), 모든 파일 `/data`, 코드 고정 사본 `/data/harvest/code_opratio_<커밋>`. events.log에 GPU 줄.
- 금지: heredoc·`python -`·`python -c`·유료 호출.

## 변경 기록
- (없음)
