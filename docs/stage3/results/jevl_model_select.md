# Jev-L 모델 선정: Gemma 4 E4B 대 Qwen3-VL-4B (정본 §44)

## 사전 등록 기준 (모델 실행 전 고정, 2026-09-24T13:08:54Z `date -u`)

작업 지시문 원문 그대로(데이터를 본 뒤 바꾸지 않는다):

- Data: DEV seeds 0–29 × P0/P1/P2 on the v2 scene (CPU PhysX), all decision snapshots from decision_points (M1 text state via serialize_state + default head camera RGB 672×376 at that instant). Labels = oracle_answer for dir_xy, dir_z, mag_coarse, target, phase, mon.progress (use whichever of these the planner defines). Same prompts (DecCall format, R1 shown names, NONE_ESCALATE last) for both models; image = head cam only.
- Primary metric A: accuracy vs oracle (argmax of renormalized option probabilities) pooled over questions, paired by snapshot; 95% CI by episode-cluster bootstrap (10,000). Secondary: per-question accuracy, ECE (15 bins) and AUROC of p_chosen for correctness, NONE_ESCALATE rate.
- Latency L: same L1 protocol as jevl_latency.md (S1-size DecCall, text+image, N=4, warm-up per N of 10 calls per worker discarded, batch invariance ON, 200 calls): p95 must be ≤ 0.33 s (acceptable) to be eligible.
- Determinism: 20 fixed payloads × 10 repeats, batch invariance ON, flip must be 0.
- Decision rule: among eligible models (L acceptable and flip 0), choose the higher accuracy if the paired difference's 95% CI lower bound > 0; if the CI includes 0, choose the one with lower N=4 p95 latency; if still tied within 0.02 s, choose Qwen3-VL-4B (incumbent). Do not change the rule after seeing data; any deviation goes to a "사후 변경" section with both results.

### 운영 세부 (같은 시각, 모델 실행 전 고정 — 위 원문을 코드에 옮기는 방법)

- 후보: `google/gemma-4-E4B-it@ee0ef6023621cff504d758262d4e04895a5af4a2`, `Qwen/Qwen3-VL-4B-Instruct@ebb281ec70b05090aa6165b016eac8ec08e71b17`. 둘 다 BF16, 같은 vLLM(0.30.0, `/data/harvest/venv_vllm`), GPU 3 한 장, 같은 서버 옵션(jevl_latency.md 표), `VLLM_BATCH_INVARIANT=1`, 기본 채팅 템플릿(생각 모드 켜지 않음), 같은 시스템 문장(`harvest/clients/jevl.py` `SYSTEM`).
- "decision snapshots from decision_points" = 연속 스냅샷(0.33 s 격자) 중 `decision_points`의 정답이 있는 **모든** 시점(`attach_oracle`의 `oracle` ≠ null). 풀의 10개 표집(`decision` 표시)이 아니라 전부. 실패 판 포함. 90판(30시드 × P0/P1/P2).
- 정답 원천(플래너·스냅샷 코드가 정의하는 것 전부): `dir_xy`·`dir_z`·`mag_coarse` = `oracle_answer`, `target` = `oracle_target`(집기 단계 o3, 그 뒤 o5), `phase` = `oracle_phase_choice`(continue/next; hold는 오라클이 내지 않음), `mon.progress` = `oracle_progress`. `grip`·`fine_dir`는 지시 목록에 없어 제외.
- 질문 6개(한 스냅샷 = 한 DecCall, 질문 id `ds<k>.dir_xy` 등, 단계 S = `stage_of(phase)`):
  - `dir_xy`, `dir_z`: "Which direction should the gripper move during step ds<k> to make progress toward the exit of stage S?" 보기 `jevcall.DIR_XY` / `DIR_Z`.
  - `mag_coarse`: "How far should the gripper move during step ds<k>?" 보기 `jevcall.MAG`.
  - `target`: "Which object is the robot's current motion about during step ds<k>?" 보기 = 그 시점 `present` 물체 id(번호순, 보이는 이름 = id, 설명 = `SPEC_NAMES` 색·종류) + NONE_ESCALATE.
  - `phase`: "During step ds<k>, should the robot keep its current motion phase, switch to the next phase of stage S, or pause?" 보기 `continue` "Keep executing the current motion phase." / `next` "Switch to the next motion phase now." / `hold` "Pause and keep the gripper still." + NONE_ESCALATE.
  - `mon.progress`: "Considering the change since the last step, how is stage S going?" 보기 `jevcall.PROGRESS`(보이는 이름 R1: advancing/side_change/regressed/recovering).
  - 모든 질문 NONE_ESCALATE 마지막. 텍스트 상태 = 풀 코드 `snapshot.text_state`(→ `serialize_state`). 이미지 = 그 시각 머리캠 RGB 672×376, 풀 저장 형식 JPEG q90 그대로 전송.
- 채점: 보기 집합 안 재정규화 확률(`jevl.option_probs`)의 argmax option_key == 오라클 key면 정답. argmax가 NONE_ESCALATE면 오답(오라클은 NONE_ESCALATE를 내지 않음). `p_chosen` = argmax 확률. 동률은 보기 순서 앞쪽.
- A = 모든 (스냅샷, 질문) 항목 정답률(질문 합침). 짝 차이 = 항목별 (Gemma 정답 − Qwen 정답)의 평균, 판(시드×섭동, 90개) 단위 부트스트랩 10,000회(`harvest.analysis.stats.cluster_bootstrap_ci`, seed 0), 95 % 백분위 구간.
- ECE: p_chosen 15개 등간격 구간, 항목 수 가중 |정답률 − 평균 p_chosen|. AUROC: p_chosen으로 정답/오답 구분(동률 0.5). 둘 다 질문 합침 + 질문별.
- 정확도 호출 순서·동시성: 같은 스냅샷 목록·순서, 동시 4 호출(BI 켬이라 결과는 동시성과 무관). 호출 실패는 재시도 3회, 그래도 실패면 그 항목 오답으로 세고 따로 보고.
- 지연·결정성: `tools/jevl_bench.py` `l1`·`l2`를 두 모델 모두 **이번에 새로** 잰다(같은 날·같은 GPU, 이전 Qwen 수치는 참고만). 이미지 = jevl_latency.md와 같은 ROBOTIS 머리캠 PNG. 적격 판정은 text+image N=4 p95(검열 2 s, 실패 = inf). 결정성 = BI 켬 L2의 페이로드 flip(질문 하나라도 argmax가 바뀐 페이로드 수) = 0/20.
- 전처리 확인(판정 아님): 두 모델 모두 `jevl_bench.py sanity`로 이어 쓰기 접두 재토큰화 일치를 확인한 뒤 정확도를 잰다. 불일치면 채점 전에 클라이언트를 고치고 그 사실을 적는다.
- 시드: DEV 0–29만. TEST 1000–1149·TEST-P5 1300–1329·POOL 2000–2119는 만들지도 읽지도 않는다.

---

## 결과 (2026-09-24 13:55Z 작성)

**판정(사전 규칙 그대로): Qwen3-VL-4B-Instruct 유지.** 두 경로 모두 같은 답이다.
1. 적격: Gemma 4 E4B는 text+image N=4 p95 **0.380 s > 0.33 s** → 부적격. Qwen3-VL-4B는 0.267 s(acceptable), 결정성 flip 0 → 유일한 적격 모델.
2. (참고, 규칙상 필요 없음) Gemma가 적격이었더라도 정확도 짝 차이 Qwen − Gemma = **+0.057, 95 % CI [+0.050, +0.065]**(하한 > 0) → Qwen.

### 설정 (재현용)

| 항목 | 값 |
|---|---|
| 파드·GPU | `juhyoung-native-7a2a`, vLLM = GPU 3, Isaac 렌더(DEV 스냅샷) = GPU 1, CPU PhysX. GPU 0·2 사용 안 함 |
| vLLM | 0.30.0, `/data/harvest/venv_vllm`(업그레이드 불필요: `Gemma4ForConditionalGeneration` 등록됨), torch 2.13.0, transformers 5.17.0 |
| Gemma | `google/gemma-4-E4B-it@ee0ef6023621cff504d758262d4e04895a5af4a2`, BF16, `/data/harvest/models/gemma-4-E4B-it`(15 GB), 기본 템플릿(생각 모드 끔 — E4B는 빈 thought 블록도 내지 않음, 모델 카드), 이미지 토큰 기본 예산 280, 끝 토큰 `<turn\|>` |
| Qwen | `Qwen/Qwen3-VL-4B-Instruct@ebb281ec70b05090aa6165b016eac8ec08e71b17`, 끝 토큰 `<\|im_end\|>` |
| 서버 옵션 | jevl_latency.md와 같음 + `VLLM_BATCH_INVARIANT=1`. **Gemma만 `--attention-backend TRITON_ATTN`**(아래 사후 변경 1) |
| 이어 쓰기 확인 | 두 모델 모두 `jevl_bench.py sanity` 접두 재토큰화 전부 OK. Gemma는 `plus_x`가 3토큰이라 S1 호출 = 10 시퀀스(Qwen 8), 프롬프트 712 대 649 토큰 |
| DEV 스냅샷 | `python.sh -m harvest.cli_pool dev --seeds 0-29 --kinds P0\|P1\|P2`(v2 장면, CPU PhysX, 머리캠만) → `/data/harvest/data/jsel_dev/P{0,1,2}/`. 90판, 성공 P0 30/30 · P1 28/30(시드 3·5 lift 실패) · P2 30/30. 오라클 있는 스냅샷 **2,387개 × 질문 6 = 14,322 항목**(두 모델 모두 최종 호출 오류 0; Gemma는 재시도가 필요했던 스냅샷 4개, 모두 성공) |
| 프레임 확인 | P0 시드 0 k11(lift) 머리캠: 그리퍼가 빨간 머그를 쥐고 들어 올리는 장면, 파란 트레이 보임 — 텍스트 상태 `held_by_gripper`와 일치 |

### 1. 정확도 (주 지표 A, 질문 합침, text+머리캠, BI 켬)

| 모델 | A | 95 % CI (판 90개 부트스트랩 10,000) | ECE (15구간) | AUROC(p_chosen→정답) | NONE_ESCALATE 비율 |
|---|---|---|---|---|---|
| Gemma 4 E4B | 0.4254 | [0.4191, 0.4314] | 0.316 | 0.779 | 3.5 % |
| Qwen3-VL-4B | **0.4828** | [0.4768, 0.4888] | 0.402 | 0.599 | 0.09 % |
| 짝 차이 Gemma − Qwen | **−0.0574** | [−0.0651, −0.0502] | | | |

참고 기준선(규칙 밖): 질문마다 최빈 오라클 보기를 늘 고르면 A = 9,583/14,322 = **0.669**. 두 모델 모두 이 기준선보다 낮다.

질문별(정답률 / ECE / AUROC / NE 비율, 차이 = Gemma − Qwen, 판 부트스트랩 95 % CI):

| 질문 | n | Gemma | Qwen | 차이 |
|---|---|---|---|---|
| dir_xy | 2,387 | 0.180 / 0.240 / 0.509 / 0 | 0.088 / 0.848 / 0.740 / 0 | +0.091 [+0.073, +0.110] |
| dir_z | 2,387 | 0.405 / 0.357 / 0.750 / 0 | 0.568 / 0.296 / 0.610 / 0 | −0.163 [−0.189, −0.138] |
| mag_coarse | 2,387 | 0.080 / 0.565 / 0.421 / **0.212** | 0.282 / 0.471 / 0.324 / 0 | −0.202 [−0.216, −0.188] |
| target | 2,387 | 0.566 / 0.301 / 0.601 / 0 | 0.439 / 0.550 / 0.564 / 0 | +0.127 [+0.102, +0.150] |
| phase | 2,387 | 0.397 / 0.385 / 0.501 / 0 | 0.609 / 0.216 / 0.466 / 0 | −0.212 [−0.234, −0.190] |
| mon.progress | 2,387 | 0.925 / 0.070 / 0.409 / 0 | 0.910 / 0.073 / 0.604 / 0.005 | +0.015 [+0.010, +0.020] |

섭동별 A: P0 0.443 / 0.498, P1 0.411 / 0.474, P2 0.423 / 0.476 (Gemma / Qwen).

오라클 분포와 모델 선택(치우침 진단):
- dir_xy 오라클 none_xy 1,711 · minus_y 222 · plus_y 212 · …; Qwen은 **plus_x 2,173/2,387(91 %)**, Gemma는 minus_x_minus_y 988 · minus_y 447 · none_xy 389.
- dir_z 오라클 down 1,251 · up 660 · none_z 476; Qwen down 1,419 · up 885, Gemma none_z 892 · up 849 · down 646.
- mag_coarse 오라클 medium 1,320 · xlarge 448; Gemma small 1,735 · **NONE_ESCALATE 506**, Qwen small 1,079 · medium 769 · tiny 539.
- target 오라클 o5 1,349 · o3 1,038; Qwen o3 2,373(99 %), Gemma o3 1,941 · o5 373.
- phase 오라클 continue 1,745 · next 642; Gemma next 1,840(77 %), Qwen continue 1,421.
- progress 오라클 valid_progress 2,207 · allowed_change 180; 두 모델 거의 모두 advancing(valid_progress).

해석: 두 모델 모두 **보기 이름·위치 치우침이 크고, 영점 설정으로는 최빈 기준선(0.669)에도 못 미친다.** Gemma는 보정(ECE·AUROC)이 더 낫고 dir_xy·target에서 이기지만, dir_z·mag_coarse·phase에서 크게 진다. 규칙은 합친 A만 본다.

### 2. 지연 (L1, BI 켬, 200호출/조건, N마다 워커당 10호출 버림, 이미지 = jevl_latency.md와 같은 ROBOTIS PNG)

사전 등록 판(판정에 씀):

| 모델 | 모드 | N=1 p50/p95 | N=2 | N=4 | N=8 | 실패 | N=4 판정 |
|---|---|---|---|---|---|---|---|
| Gemma 4 E4B | text | 0.060 / 0.071 | 0.094 / 0.106 | 0.158 / **0.165** | 0.214 / 0.300 | 0 | acceptable |
| Gemma 4 E4B | text+image | 0.105 / 0.120 | 0.178 / 0.330 | 0.321 / **0.380** | 0.344 / 0.538 | 0 | **fail** |
| Qwen3-VL-4B | text | 0.039 / 0.049 | 0.048 / 0.073 | 0.102 / **0.119** | 0.130 / 0.192 | 0 | target |
| Qwen3-VL-4B | text+image | 0.073 / 0.085 | 0.129 / 0.165 | 0.237 / **0.267** | 0.362 / 0.496 | 0 | acceptable |

(단위 s. Qwen 수치는 이전 시험 0.261–0.292 s와 맞는다. 이미지 비용 N=4: Gemma +0.215 s, Qwen +0.148 s.)

반복 판(규칙 밖, 배경 부하 있음 — 사후 변경 2): Gemma image N=4 p95 **0.375**(p50 0.330), text 0.171; Qwen(FA3) image **0.369**(p50 0.292), text 0.120; Qwen을 Gemma와 같은 TRITON_ATTN으로(참고) image 0.285, text 0.185. Gemma의 image N=4 **p50은 두 판 모두 0.32–0.33 s**로 Qwen(0.24–0.29 s)보다 늘 높다.

### 3. 결정성 (L2, BI 켬, 배경 부하 N=4 image, 20 고정 페이로드 × 10 반복)

| 모델 | 판 | 성공 호출 | flip(페이로드) | flip(페이로드×질문) | max \|Δp\| |
|---|---|---|---|---|---|
| Gemma 4 E4B | 사전 등록 | 200/200 | 0/20 | 0/80 | 0 |
| Gemma 4 E4B | 반복 | 200/200 | 0/20 | 0/80 | 0 |
| Qwen3-VL-4B | 사전 등록 | **180/200**(20건 2 s 시간 초과, 반복 5–8) | 0/20 | 0/80 | 0 |
| Qwen3-VL-4B | 반복 | 200/200 | 0/20 | 0/80 | 0 |

두 모델 모두 비트 단위로 같다(flip 0). Qwen 사전 등록 판의 시간 초과 20건은 13:32Z에 시작된 다른 에이전트의 POOL 생성·라벨 프로세스(파드 load 37 → 72)와 겹친 구간이다(사후 변경 2).

### 4. 판정 (사전 규칙, 데이터 본 뒤 규칙·문턱 변경 없음)
- 적격 = L acceptable(text+image N=4 p95 ≤ 0.33 s) 그리고 flip 0: **Qwen3-VL-4B만**(0.267 s, flip 0). Gemma 4 E4B는 0.380 s로 부적격.
- 적격 모델이 하나이므로 → **Qwen3-VL-4B-Instruct 선정(현행 유지).**
- 강건성: 적격을 무시해도 정확도 짝 차이 CI가 Qwen 쪽으로 0을 벗어나(Qwen − Gemma 하한 +0.050) 같은 답. 부하 있는 반복 판에서도 Gemma가 Qwen보다 빠른 판은 없다.

## 사후 변경 (숨기지 않고 적음)
1. **Gemma 어텐션 백엔드**: 사전 등록의 "같은 서버 옵션"으로 띄우면 Gemma 4는 기동에 실패한다. 전역 어텐션 층 head dim이 512인데, 배치 불변 켬에서는 vLLM이 FA4를 금지하고 FA2로 내려가며 FA2는 head dim ≤ 256만 지원한다(`RuntimeError: FlashAttention forward only supports head dimension at most 256`, `srv_gemma_fa_fail.log`). 그래서 Gemma만 `--attention-backend TRITON_ATTN`(vLLM 배치 불변 경로가 있는 백엔드)으로 돌렸다. 공정성 참고로 Qwen도 TRITON_ATTN으로 L1을 한 번 쟀다(image N=4 p95 0.285 s, 부하 있음). Qwen은 어느 백엔드로도 Gemma보다 빠르다.
2. **배경 CPU 부하**: 사전 등록 측정 동안 (a) Gemma L1(13:21:51–13:23:52Z)은 내 DEV 생성 Isaac 2개(P1·P2, CPU PhysX, 13:23:06Z에 끝남)와 겹쳤고, (b) 13:32Z부터 다른 에이전트의 `cli_pool pool`(POOL 2000–2119) 4개·`cli_label selfcheck` 3개·`diag_xproc`가 파드 CPU를 포화시켰다(load 30–72). vLLM API 서버는 CPU(이미지 디코딩·토큰화)를 쓰므로 지연이 부하에 민감하다. Qwen 반복 판은 부하 아래에서 0.267 → 0.369 s로 나빠졌다. 그래서 두 모델을 같은 부하 조건에서 번갈아 한 번씩 더 쟀다(위 반복 판). 판정은 사전 등록 판으로 했고, 반복 판은 결론(Gemma가 더 느림)을 바꾸지 않는다. 깨끗한 CPU에서 Gemma가 0.33 s 안에 들어올 가능성은 남아 있다(부하가 적었던 첫 판 p50이 0.321 s라 여유는 작다). 다만 정확도에서도 지므로 판정에는 영향이 없다.
3. 결정성 판정은 Qwen 사전 등록 판의 성공 180호출 기준 flip 0이고, 반복 판(200/200)도 flip 0이다.

## 신뢰도 기록 (사용자 규칙: 신뢰도·스타·반응)
| 모델 | HF 좋아요 | 다운로드(최근 30일 / 누적) | 공개 | 기술 보고서 | 라이선스 |
|---|---|---|---|---|---|
| google/gemma-4-E4B-it | 1,594 | 4,430,582 / 32,506,043 | 2026-03-02 (최종 수정 2026-07-20) | Gemma 4 Technical Report, arXiv 2607.02770(모델 카드 링크) | Apache-2.0 |
| Qwen/Qwen3-VL-4B-Instruct | 475 | 3,403,280 / 27,446,760 | 2025-10-11 | Qwen3-VL Technical Report, arXiv 2511.21631 | Apache-2.0 |

(HF API `expand[]=likes,downloads,downloadsAllTime`, 2026-09-24 13:0x UTC 조회. 둘 다 1차 제공자라 신뢰도는 충분하다.)

## 원자료·파일
- 파드 `/data/harvest/jsel/`: `acc_<model>.jsonl`(항목별 정답·보기 확률·p_chosen), `lat_<model>.jsonl`(사전 등록 L1·L2), `rep_*.jsonl`(반복 판), `serve.sh`·`run_model.sh`·`rep.sh`·`gen_dev.sh`, 서버·실행 로그. DEV 스냅샷 `/data/harvest/data/jsel_dev/`(95 MB). 코드 사본 `/data/harvest/code_jsel/`(공용 `/data/harvest/code`는 건드리지 않음).
- 로컬(D:\qdd, 커밋 안 함): 새 `harvest/deccall_snap.py`(스냅샷 → 6질문 DecCall, option_key 채점), `harvest/analysis/stats.py`에 `ece`·`auroc` 추가, `harvest/cli_pool.py`에 `dev` 모드 추가(DEV 0–29 × P0–P2, 종류별 폴더, 머리캠만), `tools/jevl_bench.py`에 `--end-token` 추가, 새 `tools/jevl_acc.py`·`tools/jevl_select_report.py`, 새 테스트 `tests/test_deccall_snap.py`(4) + `tests/test_stats.py`에 2개. 전체 테스트 243 통과.
- `/data` 밖: 새 파일 없음(`/tmp` 항목 수 1,036 → 1,036. 새 시각의 `/tmp/og.txt`는 다른 프로젝트 것). `/dev/shm` 디렉터리 시각만 바뀜(vLLM 공유 메모리, 남은 파일 없음). vLLM 서버는 모두 내려 GPU 3을 비웠다.
