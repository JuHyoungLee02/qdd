# E-VB1 지식 보존 — 같은 데이터 π0.5 맞대결 (중단)

- 작성 2026-10-01 22시대 KST, VB1 에이전트. 등록 `docs/stage3/prereg_vb1.md`(변경 1).
- **상태: 중단·보존.**
  - 사용자 원문(user-log 235): "근데 같은 데이터 맞대결 자체를 안하면되지 않을까/ 평가자체를우리 데이터로 안하는게 맞을 것 같아"
  - 결과(성공률)는 하나도 나오지 않았다. 판정 없음.
  - 프로세스는 SIGTERM으로 모두 멈췄다(7a2a·x2·78dc). 78dc GPU는 비어 있다.
  - 데이터·체크포인트·코드는 지우지 않았다.

## 1. 결정과 이유
- **라이선스.** π0.5 가중치(`lerobot/pi05_base`, openpi `pi05_base`)는 Gemma Terms of Use이고, NOW §4 허용 목록 밖이다.
  - 사용자 "a"(user-log 227)로 내부 기준선 전용 예외를 받았다. 가중치·파생물은 배포하지 않는다.
  - 다시 쓰려면 같은 조건이 그대로 적용된다.
- **재생 대신 재수집.**
  - L8S 원본에는 연속 영상이 없다. 결정 시점 사진만 있고, 연속 프레임 `frames/`는 1,389/9,133편에만 약 4 Hz 미리보기로 있다.
  - 관절 기록에는 집게 명령폭이 없고, 수집 코드 판본이 편마다 다르다.
  - 그래서 같은 수집기(`collect_episode`)를 같은 작업 줄·시드·과제·스타일·p로 다시 돌렸다.
  - 기록은 10 Hz로 남겼다: 머리(절반 해상도)·오른손목 JPEG, 상태 11(팔 7 + 집게 폭 + 리프트 + 머리 2), 행동 8(중력 보정 전 팔 명령 `_qcmd` 7 + 집게 명령폭).
- **학습 편.**
  - main35 학습 행의 L8S 편 7,446개(고리 루트 제외)에서 고르기 분할 sha256("vb1|seed") % 100 < 3(215편)을 뺐다.
  - 그중 재수집 성공 편만 쓴다.

## 2. 실측
- 재수집 470/7,446편(성공 403, 원본과 성공 일치 455, 건너뜀 1, 오류 0).
  - 지시문 일치 470/470, 어지럼 id 일치 325/470.
  - 어지럼 묶음은 불일치가 많다. E-M35CL도 같은 재구성에서 265/282가 불일치다.
- 편당 벽시계 시간: 전체 중앙 27.8 s, 90분위 57.2 s. 어지럼 묶음 스모크는 중앙 61 s였다. 편당 프레임 중앙 160.
  - 레인 처리량: x2:1 레인 2개로 시간당 약 130편이었다.
- 스모크 변환: 8편, 1,331프레임, 44 s.
  - 정확 통계(float64, 델타 청크 50)가 통과했다.
- 스모크 학습: 78dc 4장, 20걸음, loss 0.347, 체크포인트 `train/smoke_vb1/checkpoints/000020`.
- 평가 스모크: 서버는 떴다(78dc GPU0). 그러나 렌더 카드가 모두 L9 요청 중이라 60분 안에 0편이었다.

## 3. 함정
1. **venv 링크.** GARO lerobot venv의 `bin/python`은 `/home/irteam/.local/share/uv/python/...`를 가리키는 링크다. 이 경로는 파드마다 따로라, 78dc에서는 끊겨 있었다.
   - 증상: 변환 ALERT (`nice: ... No such file or directory`).
   - 해결: 먼저 `ln -sfn /data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu` 링크를 걸고 `import lerobot`을 검사한다(e3b19e5).
2. **작업 묶음 g0009가 멈춤.** 묶음 g0009(cyclo_basket)의 한 편이 세계를 짓고 나서 2 h 47 min 동안 진전이 없었다.
   - 양보 검사는 편 사이에서만 돌기 때문에 x2:1을 L9에 늦게 돌려줬다. 이 묶음은 그 뒤에도 crash가 났다.
   - 해결: 레인 감시를 넣었다(c84e729). 로그가 늘지 않으면 카드 요청 시 5분, 평소 30분 뒤 Isaac을 죽인다.
   - 재개하기 전에 g0009의 남은 편(`rec/drf_fx_cyclo_basket/ov_basket__gso_*`)이 왜 멈추는지 먼저 확인한다.
3. **렌더 카드 부족.**
   - 렌더 가능 카드는 7a2a 0·1·3과 x2 1뿐이다. 7a2a GPU2·78dc·x2 GPU0·x3은 렌더 금지 카드다.
   - 이 카드들은 L9 GPU_WANTED에 거의 늘 올라 있어서, 레인은 대부분 시간을 대기로 보냈다.
4. 원래 함정 3종은 그대로 대비해 두었다: 델타 행동은 팔만, float64 통계, 평가 정규화는 체크포인트 안의 전처리기 통계.
   - 왼손목 키는 데이터에 없다. π0.5가 −1로 채우고 마스크 0으로 처리한다. `validate_visual_features_consistency`는 부분집합이면 통과한다.

## 4. 재개 방법
1. `/data/harvest/out/vb1/STOP`과 `STOP_EVAL`을 지운다.
2. 렌더 레인을 띄운다(7a2a·x2): `bash lane.sh <code> <7a2a|x2> <gpu> <tag>`. 평가 레인은 `eval_lane.sh`다.
   - 이미 끝난 편은 `rec.json`이 있으면 건너뛴다.
3. 78dc에서 `chain_train.sh`(스모크는 이미 통과)와 `chain_eval.sh`를 띄운다.
   - 대기 조건(E-FUT1 표식 등)은 상황에 맞게 새 사본에서 고친다.
- 코드 사본은 `/data/harvest/code_vb1_c84e729`가 마지막이다(dev c84e729, `tools/vb1/`).

## 5. 경로
- 데이터 `/data/harvest/out/vb1/`:
  - `rec/<vdir>/<task>_s<seed>/{vla/,rec.json,scene.json,meta.json,...}` 3.6 GB
  - `groups.json`·`eps/`(묶음 221, digest 01f0cabfd22866be)
  - `lerobot/vb1_smoke`
  - `train/smoke_vb1`(23 GB, 내부 전용)
  - `eval/groups.json`(sel60·OOD-O58·L8S 보류 160, E-M35CL digest 0a7aac1227bb55b6)
  - `events.log`
- 로그 `/data/harvest/logs/vb1/`.
- 코드 `tools/vb1/`: eps·rec·card·lane·isaac·convert·train·chain_train·server·closed·evalq·eval_lane·chain_eval. 시험은 `tests/test_vb1.py`.
