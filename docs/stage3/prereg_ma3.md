# E-MA3 expert 층별 KV 조건 — 사전 등록 (2026-09-25T20:34:02Z, 학습 전)

작성 E-CAM3·E-MA3 에이전트. 근거: MolmoAct 깊이 분해 `docs/research/molmoact_deepdive_2026-09-26.md` §3.1·§3.3(MolmoAct2 표 11: 은닉 상태 조건 94.0 / 헤드별 층별 KV 94.8 / **층별 KV 95.9**, LIBERO 평균, 같은 설정, 시드 수 미표기)·§5 순위 3, 설계 §14, 정본 §84. 이 문서는 **어느 kv 판도 학습하기 전에** 구조·설계·판정 규칙·자체 검사 관문을 고정한다. 결과는 `docs/stage3/results/ma3.md`. 같은 시각에 E-CAM3(`prereg_cam3.md`)가 GPU 2에서 따로 돈다.

## 0. 성격, 이미 본 것, 자체 검사(user-log 87, CLAUDE.md)
- 확인형 요인 실험. 시드 2개 × 검증 전체 1,799, 기준 = 움직임 줄 확인 실험 `motion_s1`·`motion_s2` 재사용(E-MA1b와 같은 짝 방식). RB1 체크포인트 내부용(§63 (6)).
- **이미 본 것(문턱을 정하려고 이 등록을 쓰며 읽음)**: 움직임 줄 확인 실험의 검증 1,799 예측 요약 `sample_mse_norm`(확정 결정 조건 청크 오차, 고정 잡음) — none_s1 0.02992·none_s2 0.03208(시드 간 +7.2 %), motion_s1 0.02960·motion_s2 0.03062(+3.5 %); 같은 시드 짝 차이 motion 대 none(expert를 건드리지 않은 입력 변화) s1 −1.1 %·s2 −4.5 %(합동 상대 감소 2.8 %); `results/ma1b.md`의 A3d 확정 보기 청크 오차 0.0298·0.0312(motion 대비 합동 −1.3 %). 결정 정확도 결과(motion 0.7067/0.7076 등)도 봤다. 20스텝 사전 실행(파이프라인 확인)의 출력을 봤다(0.3절). kv 본 판의 출력은 없다.
- **문턱 선택 근거(결과 전)**: expert를 목표로 하지 않은 두 개입의 합동 상대 변화가 +2.8 %·−1.3 %, 같은 설정 시드 간 차이가 3.5–7.2 %다. **합동 상대 감소 ≥ 5 %**면 이 "우연한" 변동(최대 2.8 %)의 약 1.8배이고 한 시드 차이 폭 안쪽이라 두 시드 평균으로 구별된다. 스냅샷 부트스트랩 하한 > 0을 함께 요구한다(표본 잡음). MolmoAct2 이득은 성공률이라 MSE 크기로 옮길 수 없어 문턱의 근거로 쓰지 않았다.
- **이 결과로 바뀌는 결정**: 채택이면 본 학습(단계 B) 레시피의 expert 조건을 층별 KV로 바꾸는 정본 보충을 올리고, 런타임 적용(`fused_action`·CUDA 그래프 재캡처, 연구 문서 §5 비용 '중')은 별도 작업으로 연다(이 실험은 런타임을 건드리지 않음). 불채택이면 한 층(마지막) 은닉 상태 조건(§58)을 유지하고 E-MA3를 닫는다.
- **이 표본으로 가를 수 있는가**: 상대 5 % 이상 감소는 두 시드 평균·하한 > 0으로 가를 수 있다; 0–5 %의 작은 이득은 이 설계로 가를 수 없다(규칙상 불채택, "작은 효과 가능성"으로 보고). 결정 정확도는 KI stop이라 흐름 손실이 백본에 가지 않으므로 원리상 거의 같아야 한다(차이는 기울기 자르기의 전체 노름 결합에서만 온다) → 비열등 여유 −0.01은 부트스트랩 반폭 약 0.010으로 가를 수 있다.
- **싼 사전 실행**(0.3절): kv 옵션 20스텝(학습 64·검증 원천별 5) + 저장·재적재 검사(`--reload-check`) + 청크 평가 + 지연 도구 소규모.
- **도중 관문(멈추고 재설계 → 8절에 UTC와 함께 기록·커밋 → 재개)**: (1) 기준 재사용 검사 실패(3절 (2)) → none 두 판을 이 코드로 새로 학습, (2) NaN·발산(학습 기록 `fm`·`total` NaN, 또는 step ≥ 500 검증 `fm`이 step 0보다 큼), (3) 판 하나의 학습이 예상(약 37분, motion_s1 2,222 s)의 2배(**75분**) 초과, (4) 실행 경로 검사 실패(5절).
- 비용: 유료 API 0건. GPU 3만(GPU 0·1 = R2_TRAIN Isaac 작업자, GPU 2 = E-CAM3).

### 0.3 사전 실행 결과(등록 전, 파이프라인 확인)
- 2026-09-25 20:22–20:25 UTC, 개발 사본 `/data/harvest/tmp/cam3ma3/repo`, GPU 3: kv 옵션 20스텝(학습 64, 검증 원천별 5) rc 0 — 손실 유한(step 1 total 5.59 → step 20 3.88), `--reload-check`: 새 백본에 다시 적재한 청크 최대 차 **0.0**, 고정 잡음 평가 동일(`eval_equal` true); `chunk_eval` rc 0(`expert_cond` kvcond@v1, 항목 30 + 청크 10 + 요약); 지연 도구 소규모(4표본 × 1회) rc 0. 값은 파이프라인 확인용이라 판정·문턱에 쓰지 않는다. 로그 `/data/harvest/logs/ma3/dry/`.
- 시험: 파드(작은 Qwen3-VL, CPU) `tests/train/test_se2e_kvcond_qwen.py` 9개(층 선택, 공유 접두 = 문맥별 K·V, KI stop, 다른 전방의 K·V 거부, 저장·재적재 동일 청크, 기본 적재기 거부, 기본 체크포인트 불변 적재, 기준 초기값 보존, 옵션 끔 CLI = `stageb_train`) + `test_ma3_chunk_eval.py` 2개(기본·kv 모델에서 `evaluate()` 요약·항목 기록 비트 동일) 통과; 로컬 `tests/test_ma3_verdict.py`.

## 1. 질문
expert 블록마다 백본의 서로 다른 층 K·V에 교차 주의하게 하면(MolmoAct2 층별 KV), 마지막 층 은닉 상태 하나에 교차 주의하는 기준보다 expert 청크 오차가 줄어드는가 — 결정 정확도와 지연은 거의 그대로인가.

## 2. 구조 `kvcond@v1` (`harvest/train/se2e_kvcond.py`)
- expert 깊이 8, 백본 36층 → 블록 i는 층 L_i = ⌊(i+1)·36/8⌋ − 1 = **3, 8, 12, 17, 21, 26, 30, 35**(마지막 블록 = 마지막 층).
- K = `k_norm(k_proj(x))`(**회전 위치 부호화 전** — 위치가 섞이지 않은 내용; expert는 자기 위치를 가짐), V = `v_proj(x)`, 각 [T, 8 × 128 = 1024], 기준과 **같은 문맥 프롬프트 토큰**(공유 접두 전방의 문맥 행). LoRA가 걸린 투영 출력 그대로. 전방 훅으로 잡고 전방이 끝나면 떼어 낸다.
- 블록마다 LayerNorm + Linear(1024 → 768)을 K와 V에 따로 두고(8 × 1.58M ≈ 12.6M 매개변수), 블록의 교차 주의에 key = 사상 K, value = 사상 V. 자기 주의·MLP·조건 토큰·시간 부호화는 기준과 같다. 기준의 `ctx_norm`·`ctx_proj`는 쓰이지 않는다.
- **KI stop만**: K·V를 떼어(detach) 흐름 손실이 백본에 가지 않는다(시험). aux·확인 헤드·결정은 기준처럼 마지막 층 은닉 상태.
- 초기화: 새 사상은 기준 헤드를 모두 만든 **뒤에** 만든다 → 기준 매개변수 초기값이 같다(시험); 학습 루프가 시드를 다시 맞추므로 데이터 순서·드롭아웃·흐름 잡음 난수 흐름도 같다.
- 체크포인트: 사상은 `heads.pt`의 `expert.kv.*`, `stageb.json`에 `expert_cond = {ver, layers, kv_dim}`. 기본 `load_heads`는 이 체크포인트를 거부(엄격 적재, 시험), `load_heads_kv`는 둘 다 읽는다(기본 체크포인트 = `load_heads` 그대로, 시험).

## 3. 설계
- 판: **kv 시드 1·2**(`kv_s1`, `kv_s2`) 새로 학습. 기준 = `/data/harvest/ckpt/se2e_confirm/motion_s{1,2}` 재사용.
- **기준 재사용 조건(하나라도 어기면 none 두 판을 이 코드로 새로 학습)**: (1) 기준 `config.args`가 kv 판 인자와 `run`·`out_root`·`expert_cond` 밖에서 전부 같음, (2) 이 등록 커밋의 코드 사본(LF)의 `tools/ma3/chunk_eval.py`로 기준 `last/`를 검증 1,799에 돌린 항목 기록·요약(`dec`·`dec_acc`·`fm`·`sample_mse_norm`·`sample_mae_arm_rad` 등 옛 요약의 모든 필드)이 `logs/se2e_confirm/predfull_motion_s<s>.jsonl`과 `utc` 밖 **비트 동일**(도구가 `evaluate()`와 같은 난수 순서를 쓰는지는 시험 `test_ma3_chunk_eval.py`로 확인), (3) `stageb_train.py` 등 기준 파일 **무수정**(옵션은 새 파일의 CLI 포장 `python -m harvest.train.se2e_kvcond`이 옵션 켬일 때만 `stageb_train`의 `aux_model`·`load_heads`를 감싼다).
- 스케줄(기준과 같음): Qwen3-VL-4B@`ebb281ec` + LoRA r32, KI stop, λ 1/1/0.1/0.1, **2,000스텝, 묶음 8, lr 1e-4/1e-4, 워밍업 3 % + 코사인, 시드 1·2**, `--data se2e --se2e-root/--se2e-t-root se2e_c1/conv --motion-line se2e-motion@v1 --motion-bins se2e_c1/motion_bins.json --expert-cond kvcond@v1`, 평가 500스텝마다 검증 300.
- 실행: 파드 **GPU 3**, 기준 청크 평가(= 재사용 검사) → `kv_s1` → `kv_s2`(각 학습 + 청크 평가) → 지연. `OMP_WAIT_POLICY=PASSIVE`, `OMP_NUM_THREADS=8`. 드라이버 `/data/harvest/logs/ma3/run_ma3.sh`.

## 4. 데이터
- 기준과 같은 `se2e_c1`(읽기만). 새 데이터 없음.

## 5. 실행 경로 동일성
- (a) 새 파일뿐 — `harvest/runtime`·`PROMPT_FILES`·`PROMPT_FILES_B`·`stageb_expert.py`·`prefix_share.py`·`stageb_train.py`·`stageb_model.py`·`stageb_data.py` 무수정(`git diff`). (b) 시험: 옵션 끔일 때 CLI 인자 = `stageb_train` 인자, 함수 교체 없음; 기본 체크포인트 적재 불변; 공유 접두 경로와 문맥별 경로의 K·V 같음(상대 1e-4). (c) 파드: 기준 재사용 비트 동일(3절 (2)). 프롬프트·질문·이미지 불변(`prompt_config` 같음).

## 6. 지표와 판정 규칙 (고정)
- **1차 지표 = expert 청크 오차**: 스냅샷마다 확정 결정 조건으로 10 Euler 스텝 표본(고정 잡음 시드 0, `evaluate()`와 같은 추출 순서)의 마스크 정규화 MSE(`sample_mse_norm`의 스냅샷 값, 이전 결과 문서가 쓴 값). 시드 s 상대 감소 r_s = 1 − mean(kv_s)/mean(none_s), **합동 r = ½(r₁ + r₂)**, 스냅샷 군집 부트스트랩 10,000회(시드 0, 네 판 같은 추출).
- 결정 정확도: 합동 효과(kv − none)와 그 부트스트랩 95 % 구간(E-MA1b와 같은 방식).
- 지연: `tools/ma3/ma3_latency.py` — `temporal_latency.py`의 FULL 정의에 청크를 더함(변화가 expert에 있으므로): FULL = 이미지 읽기·전처리·토큰화·공유 접두 순전파(kv는 훅 포함) + cond + expert 10스텝 표본, cuda 동기, 묶음 1, 움직임 줄 켬, 같은 검증 한 손 스냅샷 50개, 두 조건 교차(예열 30, 4회), 백본 하나(motion_s1 어댑터)를 두 헤드가 공유, GPU 3. 결정 부분(DECIDE)도 따로 보고.
- **채택** ⇔ (1) 합동 상대 감소 **r ≥ 0.05** 그리고 (2) r의 부트스트랩 95 % 하한 **> 0** 그리고 (3) 결정 정확도 합동 효과의 부트스트랩 95 % 하한 **≥ −0.01**(비열등) 그리고 (4) FULL p95(kv) / FULL p95(base) − 1 **≤ 0.10**. 상대 CMP_EPS 1e-12(청크 하한 > 0은 엄격). 검증 1,799에서만.
- 판정 밖(보고 의무): 예측 결정 조건 청크 오차, 팔 관절 MAE(rad), 고정 잡음 흐름 손실, 정확도 층별·원천별, 시드별 값·차이, DECIDE p50/p95, 학습 시간.
- 판정 스크립트 `tools/ma3/ma3_verdict.py`(공통부 `tools/se2e/paired_verdict.py`, 시험 `tests/test_ma3_verdict.py` 경계값, `tests/test_paired_verdicts.py` 상대 감소·부트스트랩·입력 검사). 입력 검사: 1,799개·중복 없음·청크 키 = 항목 키·청크 평균 = 요약. 결과 뒤 고치지 않는다.

## 7. 코드·출력
| 항목 | 값 |
|---|---|
| 이 등록과 함께 고정(LF 블롭 sha256 앞 16) | `harvest/train/se2e_kvcond.py` `6be33eb6e61391bd`, `tools/ma3/chunk_eval.py` `60a14ce5537cdf73`, `tools/ma3/ma3_latency.py` `581cede84fdf4d7b`, `tools/ma3/ma3_verdict.py` `a58afe00f091e0ef`, `tools/se2e/paired_verdict.py` `37422bb2912fbfbc`, `tests/train/test_se2e_kvcond_qwen.py` `a074d1d9107a11bb`, `tests/train/test_ma3_chunk_eval.py` `0a5e713e2c385ac8`, `tests/test_ma3_verdict.py` `4ca30139ef9806c4` |
| 코드 사본 | 파드 `/data/harvest/code_ma3` = `git -c core.autocrlf=false archive` 이 등록 커밋(LF), 판 폴더마다 `CODE_HASHES.txt` |
| 출력 | 체크포인트 `/data/harvest/ckpt/ma3/kv_s<seed>`, 로그·청크 평가·지연·판정 `/data/harvest/logs/ma3/`, 로컬 요약 `D:\tools\scratch_qdd\cam3_ma3` |

## 8. 하지 않는 것 / 변경 기록
- 하지 않음: 헤드별 층별 KV·KI 끔·expert 깊이 변경(표 11의 다른 칸), 런타임·CUDA 그래프, 시드 0·검증 300 판정, 기준·`se2e_c1` 덮어쓰기, GPU 0·1·2, 유료 API.
- 변경 기록: (없음 — 변경은 UTC 시각과 사유를 여기에 적는다.)
