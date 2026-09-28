# E-VIEW8 — 공개 점 데이터의 3인칭 시점 행을 어떻게 쓸까 (8B, D 줄기, 무료, 사전 등록)

- 작성: PT-ND 에이전트, 2026-09-28. **학습 전에** 커밋한다. 결과는 `docs/stage3/results/view8.md`에 적는다.
- 근거:
  - user-log 169: 광각 gopro 행 제외.
  - user-log 170: 3인칭 행 사용법을 평가로 정한다.
  - 통제 지시(2026-09-28): 팔 A0–A3, 추가 방식, 걸음은 행 수에 비례, 시드 0·1, 바로 앞 팔 대비 판정.
- 유료 0원.
- GPU: 78dc `juhyoung-q-78dc`.
  - GPU 2·3: 곧바로 쓴다.
  - GPU 0·1: E-OPRATIO8-S1 체인이 끝난 뒤(`S1_DONE`) 쓴다.

## 0. 자체 검사
- **결정**: 35B D 학습에 3인칭 물체·놓을 곳 점(A1)과 3인칭 자기 손 점(A2)을 넣을지. RH20T·DROID 3인칭 물체 점(A3)은 두 번째 차수로 정한다.
- **가를 수 있나**: 두 시드를 합쳐 G는 3,154짝, L8-X는 세트당 약 200–1,100짝이다.
- **증분이 작다는 점**:
  - A1은 공개 행 1,750개를 더한다(전체의 1.5 %).
  - A2는 376개를 더한다(0.3 %). 그래서 A2 대 A1은 'SAME'이 나올 가능성이 크다. 그 경우 규칙대로 채택하지 않는다.
- **이미 본 것(P16)**: E-OPRATIO8 시드 0에서 공개 점을 넣으면 G가 크게 올랐다(0.30 → 0.66–0.68). 그 팔들의 풀에는 Franka 3인칭·광각 행이 섞여 있었다. 이 실험은 그 풀을 시점별로 나눈다.

## 1. 데이터 (빌드 `tools/teach_pt/view8_build.py`, 결과 `/data/harvest/out/view8/build.counts.json`)
- **기본**: E-OPRATIO8과 같은 L8-X b2 D d-min 78,745행(`/data/harvest/out/opratio/base_d-min.jsonl`). 모든 팔에서 같다.
- **Franka 행은 학습용 사본만 읽는다**(작전T `753c9a1`; mix_pack은 광각 제외 표시를 읽지 않음). 사본에는 광각 gopro 행이 없다.
  - `/data/harvest/out/xemb/dist8_packs/obj_pixel_train.jsonl`: 3,381행, sha256 `035929f6f5b9d86f9261412f3bee5c2199c0899c1106bbda505eca9c00f5878e`.
  - `/data/harvest/out/xemb_proto/points/molmobot_franka/records_verified_train.jsonl`: 880행, sha256 `7a638a1ca38dd2c85b4dce93aa2105b82cde3c14ea03cb1174a53c8a46d95ab8`.
- **머리 시점 파일**: BEHAVIOR·MolmoBot RBY1·RB2·RB3·ManiSkill의 `records_verified.jsonl`, `dh_pack/dh_D.jsonl`, `dist8_packs/t1t4_pixel.jsonl`.
  - dh_D와 t1t4에는 시점 태그가 없다. 둘 다 머리 카메라(BEHAVIOR 머리, ManiSkill 주 카메라, RB2·RB3·RBY1 머리)라 head로 둔다.
- **시점 구분은 태그로 한다.**
  - view=head → A0.
  - view=third이면서 qa_kind가 obj_point 또는 place_point(zed2·droid 어깨) → A1에 더함.
  - view=third이면서 ee_point → A2에 더함.
  - 같은 id는 한 번만 넣는다. G 행은 `gsplit.split`으로 먼저 빼고, 각 칸마다 `gsplit.guard`를 통과시킨다.
- **칸별 행 수**(G 제외 뒤): head 37,490(G에서 뺀 행: dh_D 366, t1t4 646, obj_pixel_train 927), third 물체·놓을 곳 1,750, third 손 376, 기타 0.

| 팔 | 공개 행 | 전체 행 | 걸음 = round(1,632 × 전체 / 78,745) |
|---|---|---|---|
| A0 | 37,490 | 116,235 | 2,409 |
| A1 | 39,240 | 117,985 | 2,445 |
| A2 | 39,616 | 118,361 | 2,453 |
| A3 | A1 + RH20T·DROID 3인칭 물체 점(작전T 변환분) | — | 같은 공식 |

- **A3 (두 번째 차수)**:
  - 작전T 변환이 준비되면 `view8_build.py a3`로 만든다. 새 파일의 view=third 물체·놓을 곳 점만, A1에 없는 id만 더한다.
  - 넣기 전에 파일 경로·sha256·행 수·G 제외 수를 이 문서의 변경 기록에 적는다(답 보기 전). 판정은 A3 대 A1이며, 규칙은 아래와 같다.
  - 참고: 사용자 규칙(정확도 위험 데이터 제외, 09-28)이 RH20T·DROID 3인칭을 막고 있다. A3는 이 규칙에 대한 **평가**로 한다. 채택은 아래 판정을 통과할 때만이다.
- **레시피**: E-OPRATIO8과 같다. Qwen3-VL-8B LoRA r16 α32, lr 1e-4 코사인, 미세 배치 8 × 누적 2, `--save-every 200`. 시드 0·1은 `--seed`만 다르다(학습 파일 같음).

## 2. 평가 (E-OPRATIO8과 같음)
- **G 1,577행**(`/data/harvest/out/opratio/g_eval.jsonl`, 변경 2 채점기).
  - BEHAVIOR·MolmoBot Franka(3인칭 보류)·RBY1·RB2 보류 각 300행.
  - Where2Place 100행.
  - RefSpatial-Bench 277행.
- **L8-X 7세트** d-min: 접근 3D 오차, '내려가지 않음' 비율.

## 3. 판정 (결과 전 고정, `tools/teach_pt/view8_compare.py`)
- **비교 쌍**: A1 대 A0, A2 대 A1, A3 대 A1. 짝 = (시드, 상태/행)이다. 두 시드의 짝을 합쳐 짝 부트스트랩 10,000회(시드 0)를 한 번 돌린다.
- **나빠짐 없음**(하나라도 어기면 REJECT):
  - (i) L8-X 7세트 모두 접근 3D 평균 차 95 % 상한 ≤ +2 mm.
  - (ii) G 하위 6세트 적중률 차 하한 > −0.03(Where2Place만 > −0.10).
  - (iii) 라벨 세트 픽셀 오차 평균 차 상한 ≤ +3 px.
- **좋아짐**: G 전체 적중률 차 하한 > 0, 또는 가장 바깥 벤치마크(RefSpatial + Where2Place를 합친 377행 × 2시드) 적중률 차 하한 > 0.
- **결과**:
  - ADOPT = 나빠짐 없음 + 좋아짐.
  - SAME = 나빠짐은 없으나 좋아짐도 없음. 채택하지 않는다.
  - REJECT = 나빠짐이 하나라도 있음.
- **보고만 하는 것**(판정에는 안 씀): 팔·시드별 L8-X 평균·중앙값·'내려가지 않음' 비율, G 하위 세트 적중률, 시드별 결과.
- 35B에는 채택된 칸만 넣는다. 한 크기(8B)에서의 결과라 35B에서 다시 확인한다고 적는다.

## 4. 실행·규칙
- 준비: `tools/teach_pt/view8.sh <code> prep`(학습 파일·gsplit 검사·작업 큐). 체인: `tools/teach_pt/view8_chain.sh`.
- 작업 큐 순서: A0 s0, A1 s0, A0 s1, A1 s1, A2 s0, A2 s1.
  - 일꾼 GPU 2·3은 바로 시작한다. GPU 0·1은 `S1_DONE`을 기다린다. 모두 끝나면 판정한다.
- 금지: heredoc·`python -`·`python -c`·유료 호출. 모든 파일은 `/data`에 둔다. 끝나면 78dc를 비우고 events.log에 적는다.

## 변경 기록
