# R3 (1부) 학습 처리량 + 단계 A 다중 이미지 — 구현·동일성 시험·측정

작성 2026-09-24 UTC(R7 2회차 K1 정정 — 처음엔 KST 날짜를 적었다), R3 구현 에이전트. git 커밋 안 함. 계획 `docs/superpowers/plans/2026-09-25-e2e-ready.md` 관문 R3(1부: 처리량 + 다중 이미지), 근거 정본 `00-interfaces.md` §52–§59, `D27-multi-image-input.md`, `stageA_pipeline.md`·`stageA_sft.md`·`r4_stageB.md`.
**아래 처리량·스모크 수치는 파이프라인 확인용(§56)이다. 모델 성능 결론이 아니다.** 데이터는 POOL(fit/eval)·합성만 썼다. CAL/TEST/TEST-P5와 풀 `oracle` 필드는 읽지 않았다.

## 1. 결론 요약

- **공유 접두 묶음 처리(prefix sharing) 구현.** 한 스냅샷의 모든 질문(과 단계 B 문맥 프롬프트)을 **한 번의 순전파**로 계산한다. 이미지·system·상태는 스냅샷당 1회만 인코딩된다. 여러 스냅샷을 오른쪽 패딩으로 한 묶음으로 처리한다(`--micro`/`--batch`).
- **손실이 옛 경로와 같다(시험으로 확인).** 작은 무작위 Qwen3-VL 구조(CPU, fp32)에서 보기 로그확률, 합한 NLL의 LoRA 기울기, 단계 B 문맥 은닉 상태, 손실 전체(fm·aux·dec·total)와 기울기가 옛 질문별 경로와 **rel 1e-4 안**에서 같다. **Jev-L 추론 에뮬레이션**(`_body_mm` HW 배치, 노드마다 요청 하나)과도 확률이 같다. 변이 시험(마스크·위치를 일부러 틀림)에서는 5개 시험이 모두 실패한다. 테스트가 차이를 잡는다는 뜻이다.
- **처리량 (H200 GPU 2, 실제 Qwen3-VL-4B BF16 + LoRA r32):**
  - 단계 A §59 HW: 학습 **3.61 → 23.6 항목/s**(micro 4, **6.5배**, 63 GB), micro 8은 25.2 항목/s(7.0배, 116 GB). 평가는 8.8 → 49–52 항목/s.
  - 단계 B: 합성(질문 3개) 묶음 4 기준 **5.00 → 0.42 s/스텝(11.9배)**. 풀 이미지 표본(질문 5개)은 0.80 → 6.2–6.9 표본/s(약 8배)다. 옛 경로는 이 표본에서 묶음 4가 메모리 부족이었다.
- **단계 A 다중 이미지(§59):** 기본값은 `--cameras HW`다. 순서는 머리 672×376 원본("head camera:") → 활성 팔 손목 424×240 원본("right wrist camera (active arm):") → 상태·질문이다. 이는 `jevl._body_mm` 배치 HW와 같고 단계 B와도 같은 배치다. 카메라 구성은 `config.json`의 `prompt_config`(카메라·상태·격자·system 해시·프롬프트 파일 해시 → `sha`)에 들어간다. `--cameras H`는 §55 스모크 프롬프트(= `jevl._body`)이며 절제용으로 남겼다.
- **스모크(GPU 2, POOL, HW, 30스텝):** 검증 NLL 4.08 → 0.471, 정확도 0.47 → 0.82. 저장한 어댑터를 다시 올리면 NLL이 **소수점 끝자리까지 같다**(0.47086653900146486).
- **전체 학습 시간 [추정]:** 현재 풀(3,000항목, 2 에폭)은 약 43분에서 **약 7분**으로 준다. 9.5만 항목(2 에폭)은 약 15 h에서 **약 2.3 h**로 준다. S-E2E 단계 B(ROBOTIS 약 4.3만–6.2만 행)는 에폭당 약 15–22 h에서 **약 1.1–1.6 h**로 준다(§6).

## 2. 구현

### 2.1 공유 접두 순전파 (`harvest/train/prefix_share.py`, 새 파일)
- **옛 경로**: 항목(스냅샷 × 질문)마다 `[system][이미지][상태][질문][보기 토큰]`을 따로 순전파한다(가지 노드를 덮는 보기 서열 1–4개, `stagea_loss.item_logprobs`). 따라서 스냅샷 하나에 이미지·상태 인코딩이 5번(단계 B는 문맥 포함 6번) 들어간다.
- **새 경로(트리 주의, tree attention)**
  1. `encode_group`: 스냅샷 하나의 프롬프트들을 채팅 템플릿으로 렌더링한다. 이미지는 `image_processor`로 한 번만 처리하고, `<|image_pad|>`는 격자 크기만큼 토큰 공간에서 펼친다. 결과는 처리기가 프롬프트마다 낸 `input_ids`·`pixel_values`·`image_grid_thw`와 **같다**(시험).
  2. `pack_rows`: 그룹의 모든 행(질문별 보기 서열, 단계 B 문맥 프롬프트)을 **토큰 트라이**로 합친다. 공통 접두(system + 이미지 + 상태, 이미지 토큰은 반드시 이 안)는 한 번만 둔다. 그 뒤로 공유되는 이어짐도 한 번만 둔다. 예를 들어 같은 질문의 보기 서열 2개(`dir_xy`)는 질문 꼬리 약 180토큰을 공유하고, 보기 첫 토큰도 공유된다.
  3. 4차원 불리언 주의 마스크로 각 토큰이 **트라이 조상만** 보게 한다. 트라이 조상은 원래 행에서 그 토큰 앞에 있던 토큰들과 정확히 같다. 위치 id는 원래 행과 같게 둔다. 접두의 mrope는 모델 자신의 `get_rope_index`에서 가져오고, 접두 뒤 텍스트 위치는 접두 끝 + 깊이다. 패딩 토큰은 자기 자신만 본다(완전 가림 행을 두지 않아 NaN 없음).
  4. 필요한 위치(가지 노드 로짓)에서만 `lm_head`를 계산하고, fp32로 올려 옛 `option_logprobs`에 넣는다.
- 처음 구현은 **2단계 KV 캐시 재사용**이었다(접두 1회 순전파 → 행마다 캐시를 복제해 꼬리 순전파). 동일성 시험은 통과했다. 그러나 행마다 접두 KV를 복제하고 꼬리 패딩이 55 %(행 길이 78–183)라서 메모리가 컸다: HW micro 4에서 16.6 항목/s·98 GB, micro 8은 메모리 부족. 트리 주의로 바꾼 뒤 같은 조건에서 23.6 항목/s·63 GB가 됐고 캐시가 없어져 **기울기 체크포인트도 쓸 수 있다**(시험). 2단계판 측정 원자료는 `/data/harvest/r3/bench_a_twopass.{json,out}`에 남겼다.
- **스냅샷당 토큰 (HW, POOL 64 스냅샷)**: 프롬프트 중앙 843토큰, 공유 접두 중앙 734토큰, 서열 6개/스냅샷(질문 5개). 옛 경로는 스냅샷당 약 5,100토큰을 순전파하고, 새 경로는 약 1,300토큰을 한 번 순전파한다.

### 2.2 단계 A (`stagea_data.py`, `stagea_train.py`)
- `load_pool(..., cameras="H"|"HW", arm="right")`: HW면 항목에 `images = stageb_data.images_of(line, arm)`를 붙인다. 레이블 문자열과 순서는 단계 B·런타임(`runtime/models.py WRIST_LABEL`)과 같다. 풀 과제는 오른팔 단일 과제라서 활성 팔 기본값을 오른팔로 뒀다. 손목 이미지가 없으면 KeyError가 난다(조용히 머리만 쓰지 않는다). `camera_of(item)`은 카메라 구성 문자열(`D27v1:head camera:|right wrist camera (active arm):` / `H:cam_head`)을 준다.
- `stagea_train`:
  - `Scorer`는 `stageb_model.HFEncoder`와 같게 했다(다중 이미지·레이블 지원, 옛 단일 이미지 문자열 경로도 받음).
  - `--cameras HW`가 기본이다.
  - `--micro`(묶음당 스냅샷 수, 기본 4)와 `--no-share`(옛 경로)를 추가했다.
  - 학습 순서는 **스냅샷 셔플 후 한 스냅샷의 질문을 연속 배치**다(`snapshot_order`). 한 최적화 스텝의 항목들이 접두를 공유하게 하려는 것이다.
  - 평가는 (스냅샷, 질문) 정렬로 묶는다(`canonical`). 같은 항목 집합이면 학습 중 평가와 `load` 평가가 같은 묶음을 만들어 값이 비트 단위로 같다.
  - `config.json`에 `prompt_config`를 추가했고, `PROMPT_FILES`에 `prefix_share.py`를 추가했다.
- 기울기 누적 방식은 옛 경로와 같다: 스텝 손실 = Σ NLL / 스텝 항목 수. 마이크로 묶음마다 backward한다.

### 2.3 단계 B (`stageb_model.py`, `stageb_train.py`)
- `StageB.forward_shared(samples)`: 표본마다 그룹 하나를 만든다. 그룹 = [문맥 프롬프트] + [그 표본의 결정 항목들의 보기 서열]이고, 묶음 전체를 한 번에 순전파한다. 문맥 은닉 상태(층 `self.layer`, 모든 위치)와 항목별 보기 로그확률을 함께 돌려준다.
- `losses`는 `self.shared=True`(기본)면 이 경로를 쓴다. HF 처리기가 없는 모의 인코더는 옛 경로로 간다(기존 모의 테스트 유지).
- `evaluate`는 `losses`의 공유 순전파 결과(`last_fw`)를 정확도·행동 샘플링에 재사용한다. 옛 코드는 같은 표본을 3번 순전파했다.
- CLI에 `--no-share`를 추가했다.
- **KI 불변**: expert는 여전히 `insulate(ctx)`로 읽는다. 문맥 은닉 상태가 결정 손실과 같은 순전파에서 나와도 fm → 백본 기울기는 detach로 0이다. `ki_check`는 옛 경로 그대로다(기존 시험 통과).

### 2.4 옛 경로와 달라지는 점(학습 분포, 수치가 아님)
- LoRA dropout(0.05)의 마스크가 이제 스냅샷의 질문들 사이에서 **공유된다**. 옛 경로는 질문마다 접두를 따로 계산해 마스크가 달랐다. 평가(dropout 꺼짐)와 동일성 시험(dropout 0)에는 영향이 없다.
- 최적화 스텝의 항목 구성이 달라진다: 무작위 항목 대신 무작위 스냅샷(각 5질문)이다. 한 스텝의 질문 간 상관이 늘어난다. 유효 배치 64 = 약 13 스냅샷.
- 옛 경로는 `--no-share`로 그대로 쓸 수 있다.

## 3. 동일성 시험

| 시험 | 내용 | 결과 |
|---|---|---|
| `tests/train/test_r3_pure.py` (9개, 로컬·파드) | `lcp_len`, `shared_len`(이미지 토큰이 접두 밖이면 오류, 캡), `pack_rows`(트라이가 모든 행을 정확히 복원·부모 = 앞 위치), `expand_image_tokens`, `group_items`, `snapshot_order`(순열·스냅샷 연속·결정성), `load_pool` HW 배치(§59 레이블·순서·경로), H = 옛 단일 이미지, 손목 없으면 거부 | 통과 |
| `test_r3_shared_qwen.py::test_group_ids_equal_processor` | 한 번 처리한 이미지 + 토큰 공간 펼침 = 처리기의 프롬프트별 `input_ids`·`pixel_values`·`image_grid_thw`·`mm_token_type_ids` | 정확히 같음 |
| `::test_shared_logprobs_equal_per_item_path[HW/H]` | 스냅샷 3개 × 질문 3–5개(상태 길이 다름, 이미지 다름), LoRA B ≠ 0. 공유 경로 로그확률 = 옛 `item_logprobs`. 질문 하나짜리 그룹(보기 서열이 프롬프트보다 더 공유되는 경우)도 확인 | rel 1e-4 안 |
| `::test_shared_grads_equal_per_item_path` | Σ NLL의 LoRA 기울기 벡터, 옛 경로 대 공유 경로 | 상대 노름 차 < 1e-4 |
| `::test_shared_grads_with_gradient_checkpointing` | 기울기 체크포인트 켬 대 끔 | < 1e-4 |
| `::test_shared_probs_equal_jevl_mm_inference_emulation` | `jevl._body_mm` HW 요청 에뮬레이션(가지 노드마다 접두를 assistant로 넣고 `continue_final_message`, 전체 어휘 로그확률 → `jevl.option_probs`) = 공유 경로 확률 | rel 1e-4 안 |
| `::test_stageb_shared_context_and_losses_equal_old` | 단계 B 합성 3표본: 문맥 은닉 상태, fm·aux·dec·total 손실(고정 t·잡음), 전체 기울기 | rel 1e-4 안 |

- **변이 확인**(파드 사본에서 일부러 틀림): (a) 트라이 마스크 대신 일반 인과 마스크 → 5/6 실패. (b) 접두 뒤 위치 +1 → 5/6 실패. 통과한 1개는 처리기 동일성 시험으로, 순전파와 무관하다. 앞선 2단계판에서도 위치 +1 → 5개 실패였다.
- 테스트 수:
  - 로컬 `cd D:/qdd && python -m pytest -q`: **449 passed, 10 skipped**(torch 없는 기본 파이썬). 첫 실행에서 `tests/runtime/test_core_fakeworld.py::test_fused_mock_interface_holds_and_logs`가 한 번 실패했다. 곧바로 따로 돌리면 3/3, 전체 재실행 2회 모두 통과했다. 이 파일은 R5 쪽 시험이고 이번 변경과 무관하다(시간 의존 불안정으로 보임, 기록만).
  - 파드 `venv_train`(CPU): `tests/train` **88 passed**(기존 + R3 16).
- 기존 시험 수정 1건: `test_stagea_qwen.py::test_train_cli_end_to_end_tiny_model`의 인자에 `--cameras H`를 추가했다. 이 시험의 가짜 풀에는 머리 이미지만 있고 기본값이 HW로 바뀌었기 때문이다.

## 4. 처리량 측정 (H200 GPU 2, 2026-09-24 UTC, 원자료 `/data/harvest/r3/bench_*.json`·`.out`)

조건: `tools/r3_bench.py`, Qwen3-VL-4B-Instruct@ebb281ec BF16, SDPA, LoRA r32(dropout 0.05), `TORCH_DISABLE_NATIVE_JIT=1`. 시작 전 `nvidia-smi`로 GPU 2가 비어 있음(1 MiB)을 확인했고, 다른 프로세스는 건드리지 않았다. 시간에는 이미지 디코딩·토큰화(CPU, 학습 루프 안)가 포함된다. 단계 A 학습 = 순전파 + 역전파 + AdamW 스텝(64항목마다)이다.

### 4.1 단계 A (POOL fit 64 스냅샷 = 320항목, labels_v2, S1 1 mm)

| 프롬프트 | 경로 | micro(스냅샷/묶음) | 학습 항목/s | 평가 항목/s | 최대 메모리(학습) |
|---|---|---|---|---|---|
| H (머리만, 727토큰) | 옛 | – | 3.62 | 8.9 | 25.9 GB |
| H | 공유 | 8 | 26.3 | 56.3 | 107.9 GB |
| **HW (§59, 843토큰)** | **옛** | – | **3.61** | 8.8 | 27.8 GB |
| HW | 공유 | 1 | 16.0 | 35.9 | 22.9 GB |
| HW | 공유 | 2 | 20.6 | 45.2 | 35.9 GB |
| HW | 공유 | **4 (기본)** | **23.6** | 49.0 | **62.7 GB** |
| HW | 공유 | 8 | 25.2 | 52.1 | 116.3 GB |
| HW | 공유 | 16 | 메모리 부족 | – | – |

- 옛 경로 H 3.62는 §55 스모크 기록(약 4.1 항목/s)과 같은 수준이다. HW는 이미지 토큰이 116개 늘지만 옛 경로 속도가 거의 같다(3.61).
- 메모리는 묶음 스냅샷당 약 13–14 GB다(LoRA 학습 활성값, 스냅샷당 약 1,300토큰). micro 4 → 8로 가도 속도는 7 %만 느는데 메모리는 거의 2배가 된다 → **기본값 4**. 체크포인트를 켜면 더 큰 micro를 쓸 수 있지만 재계산 비용이 있다(측정 안 함).
- **스모크 학습 루프 실측**(`/data/harvest/r3/ckpt/smoke_hw/log.jsonl`, micro 4, accum 32): 평가 제외 구간 약 19 항목/s, 최대 61–63 GB.
  - 평가 250항목은 약 17 s(약 15 항목/s)였다. `--max-val`이 항목을 무작위로 뽑아 스냅샷당 평균 약 1.3질문만 들어가 공유가 거의 안 되기 때문이다. 검증 부분집합을 **스냅샷 단위로 뽑으면** 벤치 수준(49 항목/s)이 된다 → 열린 문제 2.

### 4.2 단계 B (Qwen3-VL-4B + LoRA r32 + expert 79.4M(폭 768·깊이 8) + 보조 헤드, λ = 1/1/0.1, KI stop)

| 데이터 | 경로 | 묶음 | s/스텝 | 스텝/s | 표본/s | 최대 메모리 |
|---|---|---|---|---|---|---|
| 합성(R4 스모크와 같은 형식: 질문 3개, 문맥 454토큰, 머리 + 손목 원본) | 옛 | 4 | **5.00** | 0.20 | 0.80 | 76.5 GB |
| 합성 | 공유 | 4 | **0.421** | 2.37 | 9.49 | 29.7 GB |
| 합성 | 공유 | 8 | 0.746 | 1.34 | 10.7 | 49.1 GB |
| 합성 | 공유 | 16 | 1.32 | 0.76 | 12.1 | 88.2 GB |
| 합성 | 공유 | 32 | 메모리 부족 | – | – | – |
| POOL 스냅샷(IMG 상태, 머리 + 오른손목, labels_v2 질문 5개) + 합성 행동 필드 | 옛 | 1 | 2.55 | 0.39 | 0.39 | 46.2 GB |
| 〃 | 옛 | 2 | 2.49 | 0.40 | 0.80 | 82.1 GB |
| 〃 | 옛 | 4 | 메모리 부족 | – | – | – |
| 〃 | 공유 | 1 | 0.288 | 3.47 | 3.47 | 19.6 GB |
| 〃 | 공유 | 2 | 0.367 | 2.72 | 5.45 | 29.2 GB |
| 〃 | 공유 | 4 | 0.641 | 1.56 | 6.24 | 48.8 GB |
| 〃 | 공유 | 8 | 1.153 | 0.87 | 6.94 | 87.4 GB |
| 〃 | 공유 | 16 | 메모리 부족 | – | – | – |

- R4 GPU 스모크의 3.9 s/스텝(묶음 4)은 이번 옛 경로 5.0 s/스텝과 같은 조건(합성)이다. 차이는 이번 측정의 최적화 스텝·클리핑 포함과 GPU 상태로 보인다[미확인].
- 옛 경로는 표본 묶음의 모든 질문 그래프를 역전파까지 들고 있어 메모리가 크다(질문 5개 × 묶음 4 → 메모리 부족). 공유 경로는 같은 메모리에서 묶음을 4–8까지 올린다.
- 단계 B 공유 경로의 속도 향상은 합성 묶음 4 기준 11.9배다. POOL 형식에서는 옛 최선(묶음 2, 0.80 표본/s) 대비 공유 묶음 8이 6.94 표본/s로 **8.7배**다.

## 5. 지연 (R3 관문 항목)
- 이번 변경은 **학습 경로**만 바꿨다. 추론은 `jevl.acall_mm`(vLLM, lead 방식)이 그대로 맡는다. D27·§59 설계값은 머리 + 손목 N=4 p95 0.28 s(최악 판, 문턱 0.33 s)이고, 그 요청 형식과 학습 프롬프트가 같다는 것이 §3 에뮬레이션 시험의 내용이다.
- HW 모델을 병합해 vLLM으로 서빙한 확률·지연 재측정은 하지 않았다. GPU 3(vLLM)은 다른 작업이 쓰고 있어서다 → 열린 문제 1.

## 6. 전체 학습 시간 추정 [추정]

가정: HW 프롬프트, H200 1장, 단계 A 학습 23.6 항목/s(micro 4). 평가는 검증 1,000항목(스냅샷 단위 선택 시 49 항목/s ≈ 20 s, 무작위 항목 선택 시 약 15 항목/s ≈ 67 s)을 에폭당 4회 이상으로 잡았다. 옛 경로는 학습 3.6·평가 8.9 항목/s.

| 대상 | 학습 항목(2 에폭) | 옛 경로 | 새 경로(micro 4) | 새 경로(micro 8) |
|---|---|---|---|---|
| (i) 현재 풀: fit 600 스냅샷 × 5질문 = 3,000항목 | 6,000 | 28 분 + 평가 8회 15 분 ≈ **43 분** | 4.2 분 + 평가 3–9 분 ≈ **7–13 분** | 4.0 분 + 평가 |
| (ii) D26 규모 9.5×10⁴ 항목 | 1.9×10⁵ | 14.7 h + 평가 ≈ **15 h** | 2.2 h + 평가 약 10 분(20회) ≈ **2.3 h** | 2.1 h + 평가 |

S-E2E 단계 B (ROBOTIS AI Worker, `se2e_data.md`는 아직 없어 파드 자료로 추정):
- 원자료:
  - Task_0002는 전체 2.8 GB, 857편, 85,474프레임(10 fps)이고, stride 5 변환 행 17,440개(`/data/harvest/data/se2e/trial_noimg/RB2.stats.json`)다.
  - Task_0001은 718편, 125,746프레임이다. 바이트/프레임이 같다고 보면 약 4.1 GB, 약 25,100행이다.
  - 두 과제 합계는 약 6.9 GB, 약 4.26만 행이다. 10 GB까지 채우면 비례로 약 6.2만 행이다. 행마다 결정 질문 3개(휴리스틱 라벨), 짧은 문맥(과제 문장 + 그리퍼), 머리 + 활성 손목(양팔 1.2 %는 손목 2장)이다.
- 가장 가까운 측정은 합성 형식(질문 3개): 공유 묶음 8은 10.7 표본/s, 묶음 16은 12.1 표본/s다. 옛 경로 묶음 4는 0.80 표본/s다.

| 행 수 | 옛 경로(0.80 표본/s) 에폭당 | 새 경로 묶음 8(10.7) 에폭당 | 묶음 16(12.1) |
|---|---|---|---|
| 4.26만 (두 과제 전부, 약 6.9 GB) | 14.8 h | **66 분** | 59 분 |
| 6.2만 (10 GB 비례) | 21.5 h | **97 분** | 85 분 |

- 단계 B 평가(`evaluate`)는 아직 표본 1개씩이다: 공유 순전파 1회 + expert 10스텝 샘플링, 약 0.3 s/표본. 검증 5 %(2,100–3,100표본)를 통째로 돌리면 평가 1회에 약 11–16 분이다 → `--max-val` 200–500 권장(1–3 분).
- 위 값에는 데이터 적재 병렬화가 없다(이미지 디코딩이 학습 루프 안). 실제 ROBOTIS 이미지는 영상에서 뽑은 JPEG라서 비슷한 부하로 봤다[가정].

## 7. 파일

| 파일 | 변경 |
|---|---|
| `harvest/train/prefix_share.py` | 새 파일. `lcp_len`·`shared_len`·`expand_image_tokens`·`group_items`·`snapshot_order`(순수), `encode_group`·`mm_types`·`pack_rows`·`shared_forward`(트리 주의 한 번 순전파)·`group_rows`·`items_logprobs`(단계 A)·`samples_forward`(단계 B) |
| `harvest/train/stagea_data.py` | `load_pool(cameras, arm)`, `camera_of` |
| `harvest/train/stagea_train.py` | `Scorer` = HFEncoder, `item_batches`·`batch_logprobs`(canonical)·`prompt_config`, 공유 학습·평가 루프, `--cameras HW`(기본)·`--micro 4`·`--no-share`, `PROMPT_FILES` + prefix_share |
| `harvest/train/stageb_model.py` | `HFEncoder.inputs`가 문자열 경로도 받음, `HFEncoder.logprobs`(옛 경로), `StageB.shared`·`forward_shared`·`last_fw`, `losses` 공유 경로 |
| `harvest/train/stageb_train.py` | `evaluate`가 공유 순전파 재사용, `--no-share` |
| `tools/r3_bench.py` | 새 파일. 처리량 벤치(`stagea`/`stageb`) |
| `tests/train/test_r3_pure.py`, `tests/train/test_r3_shared_qwen.py` | 새 시험(§3) |
| `tests/train/test_stagea_qwen.py` | CLI 시험에 `--cameras H` 추가 |

파드(모두 `/data/harvest` 아래):
- 코드 사본: `/data/harvest/code_r3`
- 벤치 스크립트: `/data/harvest/r3/bench_a.sh`·`bench_b.sh`·`bench_b2.sh`
- 원자료: `bench_a.json`(트리 주의)·`bench_a_twopass.json`(2단계 KV판)·`bench_b.json`·`bench_b2.json`(+ `.out`)
- 스모크: `smoke_a.sh`·`smoke_a.out`·`ckpt/smoke_hw/`(config.json의 `prompt_config.sha`로 카메라 구성 기록)

## 8. 열린 문제
1. **HW 모델의 vLLM 서빙 확률·지연 재측정**: HF 학습 확률과 vLLM 추론 확률 일치(§55의 argmax 100 % 확인)를 HW 배치로 다시 해야 한다. 병합 → `serve_merged.sh`와 같은 옵션 → `JevLClient.acall_mm(layout="HW", mode="lead")`. GPU 3이 빌 때 한다.
2. **검증 부분집합을 스냅샷 단위로**: 지금 `select_val`은 항목을 무작위로 뽑아 공유가 안 된다(평가 3배 느림). 스냅샷 단위 선택으로 바꾸면 빨라지지만 기존 실행과 검증 집합이 달라진다 → 본 학습 사전 등록 때 정한다.
3. **질문 id 해시 추론 쪽 연결**: 학습 쪽 `prompt_config.sha`(카메라 구성 포함)는 기록된다. 런타임(`JevLSelector`)이 같은 해시를 내 비교하는 연결은 R5/R6 몫이다. → **해결(R5·R6·pre-R7)**: 런타임이 `question_id@vN` 5개를 기록하고(`runtime/run_r5.py` `question_ids`, `r5_closed_loop.md` 45줄 `policy_config`), 보정 파일은 question_id 해시가 다르면 거부하며(`runtime/calibration.py`, `r6_eval.md` 48줄), 융합 런타임은 체크포인트 `prompt_config`가 다르면 거부한다(`pre_r7_fixes.md` §1.1).
4. **단계 B `evaluate` 묶음화**: 지금은 표본 1개씩이다(§6). 고정 잡음 순서를 유지한 채 묶을 수 있다.
5. **활성 팔**: 단계 A 풀은 오른팔 단일 과제라 `arm="right"` 고정이다. 다과제(R2)에서 왼팔·양팔이 생기면 풀 줄에 활성 팔 필드가 필요하다(단계 B는 R2 행 `arm` 사용).
6. **LoRA dropout 공유·스냅샷 단위 스텝 구성**(§2.4)이 학습 결과에 주는 영향은 재지 않았다. 필요하면 `--no-share`와 짝 비교한다.
7. 메모리 여유: micro 8은 116 GB로 H200 한계에 가깝다. RTX PRO 6000(96 GB) 실물 서버에서 학습한다면 micro 4(63 GB)가 상한이다[추정].
