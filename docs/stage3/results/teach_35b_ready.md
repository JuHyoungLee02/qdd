# E-TEACH-35B 준비 기록 — Qwen3.5-35B-A3B를 바로 학습·서빙할 수 있게 (준비 실측, **결과 아님**)

- 작성: E-TEACH-35B 준비 에이전트, 2026-09-26T17:4xZ(UTC) = 09-27 02:4x KST. 시각은 UTC, 괄호에 KST.
- 사용자 원문(user-log 135): "35B-A3B는 일단 바로 할 수 있게 준비만 다 해둬보자"
- 통제자 추가 지시(정본 §96 보충 2, user-log 125): 최종 상위는 35B, 8B는 임시 대리. 35B는 결합 의도 형식 `astra-couple@v2`(구간 now/do/next + 평가·검증 + 명령)로 학습한다 → 학습 도구·로더가 solo와 결합 형식을 모두 받게 하고, 지연을 결합 요청으로도 잰다.
- 전략 변경(user-log 134, 정본 §98 — "일단 제거하라 그리고 필요하면 넣어라"): VLA 층을 당분간 빼고 **상위 단독이 주 트랙**. → 학습·평가 기본 경로는 solo 형식이다(`train.sh` 기본, 등록 초안 2절); 결합 형식 지원은 코드에 남긴다. 한계 찾기 지표(편당 벽시계·호출 수·교란·접촉 정밀도)는 등록 초안 3.1절.
- **이것은 준비 기록이다.** 본 학습은 하지 않았다. 아래 숫자는 배선·처리량·지연 확인용이다. 영샷 정확도와 50걸음 모델의 답은 판정에 쓰지 않는다(등록 초안 [P/prereg_teach_35b](../prereg_teach_35b.md) 0.3).
- 비용: **유료 호출 0원.** GPU만(6절).

## 0. 한 줄 요약
- 모델: `Qwen/Qwen3.5-35B-A3B`(sha `59d61f3c`, Apache-2.0, 2026-02-24, `qwen3_5_moe`, 영상-글 → 글). 공식 FP8판 `Qwen/Qwen3.5-35B-A3B-FP8`(sha `9d1823d2`). 둘 다 `/data/harvest/models/`에 받음(71.9 GB·37.5 GB).
- 기존 가상환경으로 된다(새 venv 안 만듦): transformers 5.17.0·peft 0.21.0·torch 2.13.0+cu130(venv_train), vLLM 0.30.0(venv_vllm)이 이 구조를 안다.
- **서빙 지연(영샷, FP8, thinking 끔, 한 요청씩, 빈 H200 한 장)**:
  - astra-solo@v2: **p50 1.11 s · p95 1.26 s**, 출력 중앙 222토큰, 유효 JSON 59/60(0.983).
  - astra-couple@v2(PROMPT_ID `83fa03a5de19`): **p50 1.50 s · p95 1.83 s**, 출력 중앙 328토큰, 유효 27/35(0.771 — 무효 8개 모두 edit 크기 한도 초과).
  - thinking 켬: 8개 모두 6,000토큰 한도까지 생각만 하다 잘림(39–60 s, 유효 0) → **thinking은 쓸 수 없다.**
  - 추정 "1–2 s"는 thinking 끔에서 맞다. §96 보충 1 (a)의 2 s·Astra/3(solo 2.27 s, 결합 1.79 s) 안이다(영샷 기준 — 학습 뒤 답 길이에 따라 달라짐).
- **학습 스모크(L8 데이터, 50걸음, H200 한 장)**: 미세 4 × 누적 4(전역 16; 미세 8은 메모리 초과), 최대 **108.8 GB**.
  - HF 기본(GDN 참조 경로): 18.1 s/걸음, 약 1.75k 토큰/s, 0.88 샘플/s.
  - **fla 커널 겹침(채택)**: **6.07 s/걸음, 약 4.8k 토큰/s, 2.64 샘플/s**, 손실 같은 경로 → 에폭(408걸음) **약 0.69 h**, L8 2 에폭 = **약 1.4 GPU-h**(8B L8 1.39 GPU-h와 같음).
- **왕복 확인**: 50걸음 어댑터 → 샤드 단위 병합(37 s) → vLLM(BF16) → DEV 20요청 모두 유효 JSON, p50 1.00 s. P123(샤드 색인) 문제 없음(병합이 기본 샤드 배치를 그대로 둠).
- 바로 쓰는 한 줄: `bash tools/teach_35b/train.sh <코드 사본> 0 <data.jsonl> /data/harvest/out/teach_35b/<run>` (7절).

## 1. 모델·판본 확인
| 항목 | 값 |
|---|---|
| HF id | `Qwen/Qwen3.5-35B-A3B` (sha `59d61f3ce65a6d9863b86d2e96597125219dc754`), 기본 판 `-Base`, FP8 `Qwen/Qwen3.5-35B-A3B-FP8`(sha `9d1823d2dee688a6b25e77009dc727688c44936e`), GPTQ-Int4판도 있음. `-Instruct` 이름의 저장소는 없다(기본 이름이 지시 조정판) |
| 라이선스 | Apache-2.0 (카드 메타데이터, 세 판 모두) |
| 인기·신뢰 | 내려받기 170만(FP8 156만), 좋아요 1,518 — Alibaba Qwen 공식 |
| 구조 | `Qwen3_5MoeForConditionalGeneration`, 언어 40층(Gated DeltaNet 선형 주의 30 + 완전 주의 10, 4층마다 1), hidden 2048, 전문가 256개 중 토큰당 8 + 공유 전문가 1(중간 512), 어휘 248,320, MTP 머리 1층; 영상 27층(패치 16, 병합 2); 채팅 틀 기본 thinking 켬 |
| 필요 판 | 카드 `transformers_version` 4.57.0.dev0. 우리 venv_train transformers **5.17.0**(`qwen3_5_moe` 등록, 전문가 `grouped_mm`), peft **0.21.0**, accelerate 1.15.0, torch **2.13.0+cu130**; venv_vllm **vLLM 0.30.0**(`Qwen3_5MoeForConditionalGeneration` 다중모달 등록) |
| 없는 것 | `flash-linear-attention`·`causal_conv1d`(HF가 GDN을 느린 참조 경로로 돌림), deepspeed, flash_attn, CUDA 도구(nvcc) |
| 결정 | **새 venv 안 만듦.** 공유 venv는 건드리지 않고, fla는 겹침 폴더 `/data/harvest/pylib_fla052`(flash-linear-attention 0.5.2 + fla-core 0.5.2 + einops 0.8.2, `pip --target --no-deps`)로 두고 `PYLIB`로만 켠다(4.4절) |

## 2. 내려받기
- 전: `/data` 140 T 중 109 T 사용, **여유 32 T**(78 %).
- `/data/harvest/models/Qwen3.5-35B-A3B`: 71.93 GB(14 샤드), 101 s. `/data/harvest/models/Qwen3.5-35B-A3B-FP8`: 37.49 GB, 83 s. 16:09Z(01:09 KST). 토큰은 `/data/.hf_token`에서 읽고 출력하지 않음(`D:\tools\scratch_qdd\teach_35b\download.py`).

## 3. 서빙 준비 (`tools/teach_35b/vllm.sh`)
### 3.1 실행 환경 (L8 `vllm.sh`의 환경 블록 + 이 모델에 필요한 셋)
- `VLLM_USE_DEEP_GEMM=0`: FP8 블록 GEMM의 DeepGEMM JIT가 CUDA 경로 없음으로 단언 실패(파드에 nvcc 없음).
- `VLLM_BATCH_INVARIANT=0`: "batch_invariant mode is not supported for GDN_ATTN"으로 엔진이 멈춤. 한 요청씩은 탐욕 복호라 같은 요청 두 번의 답이 같았다(메인 GPU 1과 x3에서 solo 60개·결합 35개 답 동일). 묶음 평가는 bf16 흔들림이 있을 수 있다(P110).
- `--max-num-seqs 32`: 혼합 모델은 실행 중 요청마다 Mamba(GDN) 상태 블록이 필요하고, 기본 1,024는 메모리 40 %에서 안 들어감(719 블록).
- `--reasoning-parser qwen3` + `--default-chat-template-kwargs '{"enable_thinking": false}'`: 런타임 클라이언트(`LocalVLM`·`LocalVLMAstra`)는 kwargs를 안 보내므로 서버 기본을 thinking 끔으로 둔다. 요청이 `chat_template_kwargs`로 켤 수 있다.
- 적재: FP8 가중치 34.2 GiB, 적재 약 55 s + torch.compile 약 75 s(첫 회, 캐시 뒤 약 20 s) + FlashInfer GDN JIT → 준비까지 약 100–300 s.

### 3.2 지연·유효 JSON (영샷, 탐욕, 한 요청씩 — `harvest/teach_35b/probe.py`, `tools/eacc/run_eacc.py --model qwen`)
| 조건 | GPU | n | 지연 p50 / p95 / 최대 (s) | 출력 토큰 중앙 / 최대 | 유효 JSON | 비고 |
|---|---|---|---|---|---|---|
| **solo@v2, thinking 끔** | x3 GPU 0 (빈 H200, CPU 2) | 60 | **1.11 / 1.26** / 7.98 | 222 / 2,000 | 0.983 (59/60) | 1개가 2,000토큰 반복으로 잘림(dr s10 c006) |
| 같음 | 메인 GPU 1 (Isaac 한 줄과 공유, 메모리 40 %) | 60 | 1.63 / 3.63 / 9.49 | 222 / 2,000 | 0.983 | 파드 CPU 한도 포화(10 s 중 100/101 주기 제한) — 참고용 |
| **couple@v2 (E-ACC bench screen 35장)** | x3 GPU 0 | 35 | **1.50 / 1.83** / 1.87 | 328 / 419 | 0.771 (27/35) | 무효 8 = edit Δp 0.10–0.12 m > 0.05; 구간 now 25/35, 명령 9/35(E-ACC 채점기) |
| 같음 | 메인 GPU 1 | 35 | 3.02 / 5.17 / 5.87 | 328 / 419 | 0.771 | 같은 답 |
| solo@v2, **thinking 켬**(max 6,000) | 메인 GPU 1 | 8 | 46.6 / 56.5 / 60.2 | 6,000 / 6,000 | 0.000 | 8/8 생각 중 잘림, 해독 약 65–150 토큰/s |
| **50걸음 병합 모델(BF16)**, solo, 끔 | x3 GPU 0 | 20 (첫 호출) | **1.00 / 1.15** / 1.94 | 186 / 186 | 1.000 | 왕복 확인(4.3) |

- 참고(판정 아님): 영샷 35B FP8 solo 접근 xy 중앙 132.4 mm(43개) — L8 영샷 8B 125.5 mm와 같은 급. 행동 정확도 0.72. 결합 영샷 8B(E-ACC screen2, 다른 날·다른 GPU)는 유효 34/35, p50 3.94 s, 출력 188토큰.
- 기준: Astra solo low p50 6.8 s(`astra_solo_pilot`), Astra 결합 v2 low p50 5.38 s(`eacc` 2절), 미세조정 8B solo p50 3.5 s(`teach_l8` 3절, 출력 171토큰, batch-invariant 켬).
- **사용자 질문(35B 지연 1–2 s 추정)에 대한 답**: thinking을 끄면 맞다 — 빈 GPU에서 solo 1.1 s, 결합 1.5 s(p95 1.3·1.8 s). 지연은 대부분 해독(약 200토큰/s)이라 학습 뒤 답 길이가 곧 지연이다(L8 템플릿 답 186토큰 → 1.0 s). 공유 GPU·CPU 한도가 걸린 파드에서는 1.5–2배 느렸다.

## 4. 학습 준비 (`harvest/teach_35b/train.py`, `tools/teach_35b/train.sh` + `train.conf`)
### 4.1 LoRA 대상 (결정과 이유)
- **대상**: 모든 토큰 혼합 사영 — 완전 주의 `q/k/v/o_proj`(10층) + Gated DeltaNet `in_proj_qkv`·`in_proj_z`·`out_proj`(30층) — 와 항상 켜진 **공유 전문가** `gate/up/down_proj`(40층). 250 모듈, r 16에서 학습 변수 **19.2 M**.
- **안 하는 것**: 라우팅 전문가 256개(3D 묶음 텐서 `experts.gate_up_proj`·`down_proj`), 라우터 `mlp.gate`, `shared_expert_gate`, `in_proj_a/b`(폭 32), 비전 탑, MTP.
- 이유: (1) 토큰당 8/256만 지나가 전문가별 어댑터는 데이터의 1/32만 본다. (2) PEFT 매개변수 LoRA는 매 전방에 전문가 전체 델타를 다시 만들어 느리고 메모리가 크다. (3) 병합이 약 60 GB 전문가 텐서를 다시 써야 한다. (4) 라우팅을 고정하면 사전학습된 전문가 사용이 그대로다. 모든 토큰이 지나가는 주의·공유 전문가가 L8(q/k/v/o + MLP)과 같은 자리다. 전문가 LoRA는 결과가 부족할 때 새 팔로(등록 변경).
- 시험 고정: `tests/teach_35b/test_teach_35b.py`가 실제 체크포인트 이름으로 맞음·안 맞음을 확인.

### 4.2 데이터 형식 — solo와 결합 모두 (`harvest/teach_35b/data.py`)
- teach_l8 행은 그대로 받는다(`format` 없음 = `astra-solo@v2`).
- 결합 행 `format: "astra-couple@v2"`: `image_labels`(`cam_head:` 등, 운영 `local_vlm.to_chat`과 같은 배치 — 시험), `cameras`, 답 = 평가·검증 + 구간 now/do/next + 명령.
- 학습 시작 전 모든 조종 라벨을 런타임 파서로 검사(solo `astra_solo.schema.validate`, 결합 `couple.schema.parse_answer(version="v2")`); 하나라도 거부되면 멈춤. 스모크: L8 4,025/4,025 통과.
- 결합 형식 **학습 데이터는 아직 없다**(참값 라벨러 `couple-truth` — `coupled_training_plan` 4.1). 스모크는 L8 solo 데이터로 했다.

### 4.3 스모크 (L8 TRAIN 6,521행, 50걸음, `--max-steps 50`, 메인 GPU 1 — Isaac 한 줄(2.7 GB)과 공유, `--mem-frac 0.88`)
| 설정 | 결과 |
|---|---|
| 미세 8 × 누적 2 (L8과 같음) | **메모리 초과**(21 GiB 할당 실패, 어휘 248k 로짓) |
| **미세 4 × 누적 4** (전역 16, 채택) | 50걸음 904.8 s = **18.1 s/걸음**, 토큰/s 1.65–1.92k(중앙 약 1.75k), 샘플/s 0.72–1.23(평균 0.88), 답 토큰 약 120/s, **최대 108.8 GB**, 적재 151 s |
| 손실 | 0.81(5걸음) → 0.58 → 0.48 → 0.33 → 0.20–0.33(40–50걸음); L8 8B 첫 50걸음 1.39 → 0.26 |
| 에폭 추정 | 408걸음 × 18.1 s ≈ **7,400 s ≈ 2.05 h/에폭**, L8 2 에폭(816걸음) ≈ **4.1 GPU-h**(H200 한 장). 8B L8은 1.39 GPU-h(약 4.4k 토큰/s) |

- 왕복: `harvest.teach_35b.merge`(CPU, 샤드 단위) — 250 대상 병합, 대상이 있는 샤드 2개만 새로 쓰고 12개는 하드링크, 작은 파일·색인 13개, 37 s. 색인이 가리키는 샤드가 모두 있음을 검사(P123 방지). vLLM(BF16, x3, 메모리 85 %) 적재 100 s → DEV 첫 호출 20개 모두 유효(3.2 표 마지막 줄).
  - 첫 시도(메인 GPU 1, 메모리 40 %)는 BF16 67 GB가 안 들어가 실패 — BF16 병합 모델은 H200 한 장의 약 60 % 이상이 필요(또는 `--quantization fp8` 온라인).
- DDP(`torchrun`, N장): 코드·스크립트 경로는 있으나 **여러 장으로는 못 돌려 봄**(빈 GPU 2장이 없었다). 대기 목록 8절.

### 4.4 fla 커널 겹침 (Gated DeltaNet)
- 4.3 스모크 로그에 transformers가 "`chunk_gated_delta_rule` is falling back to its reference PyTorch implementation … much slower"를 남겼다. `flash-linear-attention` 0.5.2(Triton, `CC=/data/harvest/jevl/bin/cc` 필요 — P123)를 겹침 폴더에 두고 같은 설정·같은 시드로 다시 쟀다(메인 GPU 1, 17:24–17:29Z).
- 결과: 50걸음 **303.4 s = 6.07 s/걸음**, 토큰/s 4.1–5.0k(중앙 약 4.8k), 샘플/s 2.2–3.4(평균 2.64), 최대 108.8 GB(같음) → **fla 없이보다 3.0배 빠름**, 8B L8(약 4.4k 토큰/s)과 같은 급.
- 손실이 같은 경로: 5–50걸음 0.807·0.586·0.479·0.332·0.263·0.280·0.255·0.199·0.337·0.237(fla 없이 0.808·0.584·0.476·0.332·0.262·0.281·0.255·0.199·0.332·0.228) — 차 ≤ 0.009.
- 첫 실행은 Triton 컴파일로 첫 10걸음이 약 5분 더 걸렸다(15걸음 예비 실행, 캐시 `/data/harvest/cache/triton`에 남음).
- `causal_conv1d`는 여전히 참조 경로(CUDA 컴파일 필요, 짧은 합성곱이라 영향 작다고 봄 — 재지 않음).
- **채택**: `train.conf`의 `PYLIB` 기본 = `/data/harvest/pylib_fla052`(공유 venv 불변, `PYLIB=`로 끔).
- **에폭 추정(fla)**: 408걸음 × 6.07 s ≈ **2,480 s ≈ 0.69 h/에폭**, L8 2 에폭(816걸음) ≈ **1.4 GPU-h**(H200 한 장; 8B L8 1.39 GPU-h와 같음). 40만 행 혼합이면 에폭당 약 40만 ÷ 2.64 ≈ 42 h/장(4장 DDP 이상적 약 10.5 h) [추정 — 행 길이가 L8과 같다고 가정].

## 5. 등록 초안
- [P/prereg_teach_35b](../prereg_teach_35b.md): 35-L8 대 8-L8(DEV + OOD-H, E-PT 파일·규칙), 뒤에 E-OPEN8·E-XEMB8 혼합, 목표 35-C(= 결합 계획의 E-TEACH-35C). H-L 기준: 지연 p50 ≤ 2 s 그리고 ≤ Astra/3, DEV 짝 성공 Astra − 3/40 이내, 접근 xy ≤ 14 mm. GPU-h 추정은 4.3·4.4.

## 6. 자원·비용
- 유료 **0원**.
- GPU(모두 UTC):

| 항목 | GPU | 시간 | GPU-h |
|---|---|---|---|
| vLLM 시작 실패 3회(DeepGEMM·batch-invariant·메모리 — 그 사이 E-PT가 이 GPU를 잡음) | x2 0 | 16:15–16:21 | ≈ 0.05 |
| 영샷 FP8 서빙 + solo 60·thinking 9·결합 35 | 메인 1(40 %, Isaac 공유) | 16:22–16:48 | ≈ 0.45 |
| 학습 스모크(미세 8 실패 + 미세 4 50걸음) | 메인 1(Isaac 공유) | 16:48–17:10 | ≈ 0.37 |
| 병합 모델 서빙 실패(메모리 40 %) | 메인 1 | 17:11–17:14 | ≈ 0.05 |
| 병합 모델 서빙 + FP8 재측정(solo 60·결합 35) | x3 0 | 17:15–17:22 | ≈ 0.12 |
| fla 스모크 15 + 50걸음 | 메인 1(Isaac 공유) | 17:15–17:29 | ≈ 0.23 |
| **합** | | | **≈ 1.3 GPU-h** |

- 다른 사람 프로세스는 건드리지 않았다. 우리 프로세스는 모두 `TEACH_35B_JOB` 표지로 `tools/teach_35b/stop.sh`가 종료했다(x3 17:22Z 반납 — 통제자에게 알림).
- 파드 CPU: 메인 파드는 한도 32코어가 포화(10 s 중 100/101 주기 제한)였다. 서빙 지연·학습 처리량 모두 이 영향을 받았을 수 있다(3.2 두 GPU 비교).

## 7. 바로 시작하는 방법
```
# 코드 고정 사본: /data/harvest/code_teach_35b_1e4ed20 (git archive LF, 준비 커밋) — 코드가 바뀌면 새 커밋으로 새 사본
bash tools/teach_35b/train.sh /data/harvest/code_teach_35b_<커밋> 0 /data/harvest/out/teach_l8/data/train.jsonl /data/harvest/out/teach_35b/run_l8
#   N장 DDP: 두 번째 인자 0,1 (전역 배치 = 4 x ACCUM x N — 같은 전역 16이면 --accum 2(2장)·1(4장))
#   다른 데이터: 세 번째 인자만 바꿈(E-OPEN8·E-XEMB8·결합 행 모두 같은 JSONL 형식)
python -m harvest.teach_35b.merge --adapter <run>/epoch2 --out <merged>          # CPU, venv_train
bash tools/teach_35b/vllm.sh <gpu> <merged> q35_<name> <port> 0.85                # BF16; FP8이면 --quantization fp8
```
- 기본값은 `tools/teach_35b/train.conf`(에폭 2, lr 1e-4, r 16, α 32, 미세 4, 누적 4, warmup 20, 작업자 6, `grouped_mm`, fla 겹침). 공유 GPU면 `--mem-frac 0.88`.

## 8. 기다리는 것
- **DDP 여러 장 실측**: 빈 GPU 2장 이상이 생길 때 `train.sh ... 0,1 ... --max-steps 20`으로 확인.
- **교란 주입**(한계 찾기, 등록 초안 3.1): solo 폐루프 러너에 편 도중 물체 옮기기·미끄러짐 주입이 없다 — 구현·시험 필요.
- (뒤로 미룸) 결합 형식 데이터: `couple-truth` 라벨러와 결합 DAgger 수집(결합 계획 4.1–4.2) — 행 형식·검사는 준비됨.
- **OOD-H 파일**: E-PT G-H 결과 뒤.

## 9. 이탈
- 규칙 이탈(P03):
  - (1) 로컬에서 빈 heredoc + `python -`를 한 번 실행해 멈춤 → 작업 중지(효과 없음).
  - (2) 파드 크기 확인 명령 끝에 `python -c "print(1)"`이 한 번 섞였다(효과 없음).
  - (3) 준비 커밋 `1e4ed20`의 메시지를 로컬 heredoc(`git commit -F-`)으로 넘겼다(내용 영향 없음).
  - (4) TDD: 시험을 코드보다 먼저 썼지만 실패를 먼저 확인하지 않고 코드를 쓴 뒤 한 번에 돌렸다(31개 통과).
- 영샷 thinking 켬은 20개 계획을 8개로 줄였다(모두 한도까지 잘림 — 더 재도 결론이 같음).
