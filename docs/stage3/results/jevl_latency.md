# Jev-L 사전 시험 (1) 지연 + 결정성 (정본 §44, D24 §3·§5)

## 사전 등록 기준 (실행 전 고정, 2026-09-24T09:55:58Z `date -u`)

원문 그대로(작업 지시문에서 옮김, 데이터를 본 뒤 바꾸지 않는다):

- L1 (latency, per model × input mode): operating point = S1-size DecCall (dir_xy, dir_z, mag_coarse, mon.progress as parallel sequences sharing the prefix), concurrency N ∈ {1,2,4,8}, warm server. p95 of end-to-end request time (client → all option logprobs back) censored at 2 s with failures = inf. Pass for 3 Hz loop: p95 ≤ 0.15 s at N=4 (target) ; acceptable: p95 ≤ 0.33 s (= T_c) ; fail: > 0.33 s.
- L2 (determinism): 20 fixed payloads × 10 repeats, with VLLM_BATCH_INVARIANT=1 and with it off, while background load N=4 runs. Metric = share of payloads whose argmax option changes across repeats, and max |Δp| of the chosen option. Pass: flip = 0 with batch invariance on.
- L3 (image cost): p95(text+head image) − p95(text only) at N=4 reported; no threshold.
- Decision rule: the smallest model passing L1-target in text+image mode is preferred; if none, the smallest passing L1-acceptable; if none pass acceptable, report "Jev-L on H200 insufficient" (do not tune thresholds after seeing data).


---

## 결과 요약 (2026-09-24 10:40Z 작성)

**판정(사전 규칙 그대로 적용): Qwen3-VL-4B-Instruct, 텍스트+머리캠 모드 = L1 "acceptable"(목표 미달).**
- 텍스트+이미지 모드에서 N=4 p95 ≤ 0.15 s(목표)를 넘은 모델은 없다. 둘 다 acceptable(≤ 0.33 s) → 규칙상 "가장 작은 acceptable 모델" = **4B**(p95 0.261 s; 추가 반복 0.265·0.292 s). 8B는 0.307 s로 acceptable이지만 여유가 0.02 s뿐이다.
- 텍스트만 모드에서는 4B가 목표 통과(0.104 s), 8B는 acceptable(0.177 s).
- L2: 배치 불변 켬에서 두 모델 모두 flip 0/20, max |Δp| = 0(비트 단위 같음) → **통과**. 끔에서도 flip은 0이지만 |Δp|가 최대 0.06까지 흔들린다.
- L3(N=4, BI=1): 이미지 비용 4B +0.156 s, 8B +0.130 s.
- "Jev-L on H200 insufficient"에는 해당하지 않는다.

## 설정 (재현용)

| 항목 | 값 |
|---|---|
| 파드·GPU | `juhyoung-native-7a2a`, `CUDA_VISIBLE_DEVICES=3`(H200 한 장), 클라이언트도 같은 파드(127.0.0.1) |
| vLLM | **0.30.0** (PyPI 최신 안정판, 2026-09-24), torch 2.13.0, transformers 5.17.0, triton 3.7.1, flashinfer 0.6.18.post1, venv `/data/juhyoung_qdd/venv_vllm` |
| 모델 | `Qwen/Qwen3-VL-4B-Instruct@ebb281ec70b05090aa6165b016eac8ec08e71b17`, `Qwen/Qwen3-VL-8B-Instruct@0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, BF16, `/data/juhyoung_qdd/models/` |
| 서버 옵션 | `--enable-prefix-caching --logprobs-mode raw_logprobs --max-model-len 8192 --gpu-memory-utilization 0.85 --limit-mm-per-prompt {"image":1,"video":0} --seed 0`, attention = FLASH_ATTN(FA3) |
| 배치 불변 | `VLLM_BATCH_INVARIANT=1`(켬) / 변수 없음(끔). 켬일 때 `model_executor/determinism/batch_invariant.py`의 matmul 경로가 쓰인 것을 로그로 확인 |
| 환경 우회 2건 | (1) 파드에 C 컴파일러가 없어 triton JIT가 실패 → `pip install ziglang` 후 `CC=/data/juhyoung_qdd/jevl/bin/cc`(zig cc 래퍼, `-l:libcuda.so.1`→`-lcuda` 변환). (2) FlashInfer 샘플러 JIT가 nvcc·g++를 찾다 실패 → `VLLM_USE_FLASHINFER_SAMPLER=0`(max_tokens 1·로그 확률만 읽으므로 샘플러 종류는 결과에 영향 없음) |
| 이미지 | ROBOTIS Task_0001 머리캠 `episode_000000.mp4` 첫 프레임, 672×376 PNG(280 KB), `/data/juhyoung_qdd/jevl/head_task0001_episode_000000.png`. 시각 토큰 ≈ 254(프롬프트 395 → 649) |
| 페이로드 | `harvest/load/payloads.py` `make("S1", i)`(결정 3 + 감시 1: `ds412.dir_xy`·`dir_z`·`mag_coarse`·`mon.progress`), L2는 `fixed(j)` j=0..19 |
| 호출 방식 | 새 클라이언트 `harvest/clients/jevl.py`. 질문마다 보기 이름을 토큰화해 트라이를 만들고, **갈림 노드마다 한 시퀀스**(max_tokens 1, `logprob_token_ids` = 자식 토큰, `return_tokens_as_token_ids`)를 보낸다. 앞부분 `[system][image][state][question]`은 모든 시퀀스가 공유. S1 한 호출 = **8 시퀀스 병렬**(dir_xy는 `plus`/`minus` 첫 토큰 공유로 갈림 노드 5개, 나머지 질문은 첫 토큰이 모두 달라 1개씩) |
| 확률 | p(보기) = 보기 경로 위 갈림 노드마다 자식 집합 안 softmax의 곱 = 보기 집합 안 재정규화(첫 토큰이 모두 다르면 1-패스 재정규화와 같음). 이어 쓰기 접두사가 트라이 접두 토큰과 같게 재토큰화되는 것을 `/tokenize`로 확인(4개 접두 모두 OK) |
| 측정 | 호출 시간 = 첫 시퀀스 전송 직전 → 8 시퀀스 응답 모두 도착(클라이언트 `time.monotonic`). 폐루프 N 워커, 조건당 200호출, 2 s 초과·실패 = inf(`censored_quantile` 재사용). 클라이언트 타임아웃 2 s |

## L1 표 (BI=1 = 운영 구성, perN 워밍 기준)

| 모델 | 모드 | N=1 p50/p95 | N=2 p50/p95 | N=4 p50/p95 | N=8 p50/p95 | 실패 | N=4 판정 |
|---|---|---|---|---|---|---|---|
| 4B | text | 0.037 / 0.040 | 0.057 / 0.090 | 0.099 / **0.104** | 0.150 / 0.223 | 0 | target |
| 4B | text+image | 0.068 / 0.082 | 0.121 / 0.134 | 0.223 / **0.261** | 0.294 / 0.414 | 0 | acceptable |
| 8B | text | 0.049 / 0.064 | 0.084 / 0.103 | 0.142 / **0.177** | 0.193 / 0.295 | 0 | acceptable |
| 8B | text+image | 0.081 / 0.098 | 0.146 / 0.154 | 0.270 / **0.307** | 0.476 / 0.528 | 0 | acceptable |

(단위 s, 조건당 200호출, 실패·2 s 초과 0건.)

4B BI=1 추가 반복(새 서버 기동, 같은 절차): N=4 image p95 **0.265 / 0.292 s**, text p95 0.114 / 0.116 s; N=8 image p95 0.461 / 0.456 s. 세 번 모두 acceptable, 목표는 세 번 모두 미달.

### 참고: 배치 불변 끔(BI=0)

| 모델 | 모드 | N=1 | N=2 | N=4 | N=8 |
|---|---|---|---|---|---|
| 4B | text | 0.028 / 0.038 | 0.052 / 0.067 | 0.085 / 0.097 | 0.142 / 0.175 |
| 4B | text+image | 0.065 / 0.086 | 0.112 / 0.131 | 0.220 / **0.629** | 0.275 / 0.421 |
| 8B | text | 0.033 / 0.042 | 0.052 / 0.056 | 0.096 / 0.206 | 0.170 / 0.190 |
| 8B | text+image | 0.066 / 0.076 | 0.116 / 0.143 | 0.225 / 0.256 | 0.280 / 0.369 |

배치 불변 비용(N=4 p50): 4B text +0.014 s, image +0.003 s; 8B text +0.046 s, image +0.045 s.

## L2 (결정성, text+image, 배경 부하 N=4 image, 20 고정 페이로드 × 10 반복, 반복마다 순서 섞음)

| 모델 | BI | 성공 호출 | flip (페이로드, 질문 하나라도) | flip (페이로드×질문) | max \|Δp_chosen\| | 판정 |
|---|---|---|---|---|---|---|
| 4B | 1 | 200/200 | 0/20 | 0/80 | **0** | 통과 |
| 4B | 0 | 200/200 | 0/20 | 0/80 | 6.2e-2 | (참고) |
| 8B | 1 | 200/200 | 0/20 | 0/80 | **0** | 통과 |
| 8B | 0 | 200/200 | 0/20 | 0/80 | 5.0e-2 | (참고) |

해석 주의: 고정 페이로드 20개는 `t_state` 번호만 다른 합성 상태라 argmax 여유가 크다(4B dir_xy p_chosen 0.56–0.72, 8B 0.72–0.83). 그래서 끔에서도 flip이 0이다. 끔의 |Δp| 최대 0.06은 여유가 작은 실제 결정 지점에서는 flip이 될 수 있는 크기다. 켬에서는 확률까지 비트 단위로 같았다.

## L3 (이미지 비용, N=4, p95 차)

- 4B BI=1: 0.261 − 0.104 = **+0.156 s** (BI=0: 0.629 − 0.097 = +0.532 s, 아래 과도 구간 때문)
- 8B BI=1: 0.307 − 0.177 = **+0.130 s** (BI=0: +0.050 s)
- 이미지 비용은 N에 따라 커진다(N=1 +0.04 s → N=8 +0.2–0.25 s). 원인 추정 [미확인]: 한 호출의 8 시퀀스가 **같은 이미지를 각자 들고 동시에** 들어가므로, 같은 스텝에 스케줄된 시퀀스끼리는 접두 캐시를 아직 못 쓰고 시각 인코딩·prefill을 중복할 수 있다. 또 PNG base64(약 375 KB)를 시퀀스마다 보내 API 서버 CPU가 디코딩한다.

## 절차 이탈과 과도 구간 (숨기지 않고 적음)

1. **첫 4B BI=1 L1은 워밍이 N=1 순차 10호출뿐**이었다(표의 `N1only` 행). 이 판에서 image N=4 p95가 **0.819 s**(fail 구간)로 나왔는데, 느린 호출은 전부 **N을 바꾼 직후 워커당 처음 약 10호출**에 몰려 있었다(1.0–1.7 s 포함). 새 배치 모양이 처음 나올 때의 JIT·캡처 비용으로 보고, 사전 등록의 "warm server"를 지키지 못한 절차 오류로 판단했다. 그래서 **각 N 측정 전 워커당 10호출 버림**(perN)을 넣고 4B BI=1 L1을 다시 돌렸다(0.261 s). 문턱·규칙은 바꾸지 않았다. 판정은 perN 판으로 했고, `N1only` 판도 표·원자료에 그대로 남겼다.
2. 그런데 **perN 워밍을 넣은 4B BI=0에서도 image N=4 시작 직후 워커당 약 7호출이 0.4–0.67 s**였다(p95 0.629 s). 즉 이 과도 구간은 워밍 10호출로 늘 없어지지는 않는다. 4B BI=1은 perN 판 3회(0.261·0.265·0.292 s) 모두 과도 구간이 없었다. 8B에서는 네 조건 모두 나타나지 않았다. 원인은 확인하지 못했다 [미확인].
   → 운영 권고(판정 변경 아님): 시뮬 시작 전 실제 동시성 패턴으로 수십 호출 워밍을 돌리고, E0.5에서 `d_p95`를 다시 잴 때 시작 구간을 따로 보고한다.
3. 판정에 쓴 4B image p95(0.261–0.292 s)는 **목표(0.15 s)보다 0.11–0.14 s 크고, acceptable(0.33 s)까지 여유는 0.04–0.07 s**뿐이다. N=8에서는 두 모델 모두 image 모드가 0.33 s를 넘는다(4B 0.41–0.46, 8B 0.53). 정본 `N_max = ceil(d_p95/T_c)+1` = 2이므로 운영 동시성은 N ≤ 4 안이지만, 여러 에피소드를 한 GPU에서 병렬로 돌리면 N이 커진다는 점을 E0.5 설계에 넘긴다.

## 판정 (사전 규칙, 데이터 본 뒤 문턱 변경 없음)

- L1 target(text+image, N=4 p95 ≤ 0.15 s) 통과 모델: **없음**.
- L1 acceptable(≤ 0.33 s) 통과 모델: 4B(0.261), 8B(0.307) → **가장 작은 = Qwen3-VL-4B-Instruct**.
- L2: 두 모델 BI=1 flip 0 → 통과.
- 결론: **Jev-L 1순위 모델 후보 = Qwen3-VL-4B-Instruct(텍스트+머리캠), 배치 불변 켬, `d_p95` ≈ 0.26–0.29 s(N=4)**. 정확도·보정 비교는 사전 시험 (2)(D24 §5 D1-b)에서 따로 정한다. 이번 시험은 정답을 보지 않았다(합성 페이로드에서 4B는 dir_xy `plus_y`, 8B는 `minus_y`를 골라 서로 다르다는 것만 관찰).

## 원자료·파일

- 파드: `/data/juhyoung_qdd/jevl/` — `results.jsonl`(L1·L2 전 행), `results_4B_rep{2,3}.jsonl`(추가 반복), `serve.sh`·`run.sh`·`drive*.sh`, 서버 로그 `srv_*.log`, `bin/cc`(zig 래퍼), 코드 사본 `code/`.
- 로컬(D:\qdd, dev, 커밋 안 함): `harvest/clients/jevl.py`(새), `tests/test_jevl_client.py`(새, httpx.MockTransport 5개), `tools/jevl_bench.py`(새), `tools/jevl_report.py`(새, `censored_quantile` 재사용), 이 문서. 기존 코드는 건드리지 않았다. 전체 테스트 196 통과.
- `/data` 밖 쓰기: `/tmp`·`/root`·`~/.cache`에 새 파일 없음(`find -newermt 09:55Z`로 확인). `/dev/shm` 디렉터리 시각만 바뀜(vLLM 프로세스 간 공유 메모리, 남은 파일 없음).

## 사후 변경 기록 (메인, 10:41 UTC, E §1.7 규칙)
- 사전 등록의 "warm server"는 워밍 방식을 정의하지 않았다. 첫 4B 배치 불변 켬 판(N=1에서만 10호출 워밍)의 이미지 N=4 p95 = **0.819 s(fail 구간)**. 느린 호출이 N 변경 직후 워커당 첫 약 10호출에 몰려 "warm 아님"으로 보고 N마다 워밍(워커당 10호출 버림)을 넣어 재실행 → 0.261 s. 이는 데이터를 본 뒤의 절차 변경이므로 **두 판을 함께 보고**한다. 반복 두 판(새 서버) 0.265·0.292 s로 재현.
- 메인 재계산(파드 원자료 `results*.jsonl`, 같은 검열 규칙): 4B 이미지 N=4 = 0.261 / 0.265 / 0.292 s, 4B 텍스트 0.104 / 0.114 / 0.116 s, 8B 이미지 0.307 s, 8B 텍스트 0.177 s — 에이전트 보고와 일치.
- 운영 함의: 동시성이 바뀐 직후 첫 호출들은 느리다(0.6–0.8 s). 실제 루프는 동시성이 일정하므로 시작 전 같은 패턴으로 워밍을 돌리고, 워밍 판도 E-M4 기록에 남긴다.
