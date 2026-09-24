# 단계 A SFT 파이프라인 (Jev-L typed 선택기) — 구축·스모크 결과

작성: 2026-09-24 (UTC 15:30 기준), 구현 에이전트. git 커밋 안 함. 근거: 정본 `00-interfaces.md` §51–§54, `D26-vlm-training-recipe.md` §1.4.
**본 학습은 시작하지 않았다**(정답 파일이 아직 최종이 아님). 아래 수치는 전부 스모크(파이프라인 동작 확인)이며 모델 성능 결론이 아니다.

## 1. 결론 요약

- 학습 입력은 추론 프롬프트와 **같다**: `jevl.JevLClient._body`의 system(`jevl.SYSTEM`) + user[머리캠 이미지, `jevl.question_text(...)`] + 생성 프롬프트. DecCall 문구는 `deccall_snap.build_snapshot_request`가 그대로 만든다. 상태 텍스트 기본 = E3-lite **S1, 1 mm 격자**(§53·§54).
- 손실 = **보기 집합 안 재정규화 확률의 NLL**, 확률은 추론과 **같은 보기 트라이 분해**(가지 노드마다 자식 토큰만의 softmax 곱, `jevl.option_trie`·`jevl.option_probs`). 정답이 여러 개면 −log Σ_{o∈best} p̃(o).
- 정답 원천은 **플러그인**이다: `labels_v2`(§54 관측 정의, 1차 정답, 기본값) / `outcome`(결과 기반 라벨, 사전 등록 점수식, 보조) / `py:<module>:<factory>`. 원천 함수에는 `oracle` 필드를 뺀 줄만 넘기고, 프롬프트 생성에도 가짜 oracle을 넣으므로 **풀의 `oracle` 필드는 정답에도 프롬프트에도 들어갈 수 없다**(테스트로 확인).
- 검증: (i) 학습 로그확률 = `jevl.py` 추론 로그확률(모의 로짓·모의 인과 LM, rel 1e-9), (ii) **실제 Qwen3-VL 구조의 작은 무작위 모델**로 "노드마다 따로 렌더링해 추론"과 학습 경로가 같음(rel 1e-4, fp32), (iii) 채팅 템플릿 이어쓰기 = 생성 프롬프트 + 접두 토큰(실제 DecCall 보기 전부), (iv) 기본 모델 HF 확률 대 **기록된 vLLM 확률** 120문항: argmax 일치 100 %(S0 텍스트·S0 이미지), 99.2 %(S1 이미지, 1건 동점 근처), (v) 병합 BF16 모델을 **우리 vLLM venv로 서빙**해 HF 기본+어댑터와 60문항 argmax 100 % 일치.
- 스모크(H200 GPU 1, 50 스텝): labels_v2 정답에서 검증 NLL **3.76 → 0.656**, 정확도 0.36 → 0.78, 학습 손실 구간 평균 2.40 → 0.39. 저장한 어댑터를 다시 올리면 검증 NLL이 로그 값과 **소수점까지 같다**(0.65589).
- 전체 학습 시간 [추정]: 현재 풀 규모(120편 × 결정 스냅샷 약 10 × 5질문 ≈ 6,000항목, 학습 절반)면 2 에폭 **약 40분**. D26 규모(9.5만 항목)면 지금 구현(1항목씩)으로 약 13 h → 묶음 처리 최적화가 필요하다(§7).

## 2. 파일

| 파일 | 역할 |
|---|---|
| `harvest/train/stagea_data.py` | 풀 줄 + 정답 원천 → 항목(추론과 같은 DecCall 문구·보기 순서·이미지 경로·정답 보기 이름). `OutcomeLabels`·`LabelsV2`·`FnSource`, `split_of`, `load_pool`, `labels_v2_factory`·`outcome_factory`, `state_fn`(S0/S1/S2, `step_cm`) |
| `harvest/train/stagea_loss.py` | `cover`(가지 노드를 모두 지나는 최소 보기 서열 선택), `option_logprobs`(노드 로짓 → 보기 로그확률), `batch_inputs`, `item_logprobs`, `set_nll` |
| `harvest/train/stagea_train.py` | CLI `train` / `load` / `parity`. LoRA 적용, AdamW + cosine + 워밍업, 검증 NLL 조기 종료·최고 어댑터 저장, 실행 기록(config.json·log.jsonl) |
| `tools/stagea_merge.py` | LoRA → 기본 가중치 병합(fp32에서 병합 후 BF16 저장), 처리기·토크나이저·채팅 템플릿 파일 그대로 복사, `merge_info.json`, `--check`(로짓 비교 + BF16 반올림 잡음 바닥) |
| `tests/train/test_stagea_data.py` | 순수 함수 18개(점수식·NE 규칙·분할·프롬프트 동일성·oracle 차단·labels_v2·파일 위치·step_cm) |
| `tests/train/test_stagea_loss.py` | `cover` 순수 테스트 3개(무작위 트라이 200개 포함) |
| `tests/train/test_stagea_loss_torch.py` | torch(CPU): 학습 로그확률 = jevl 추론 로그확률(모의 인과 LM, 무작위 트라이 105개), 노드 로짓 경로, 묶음 입력, set NLL, SGD로 손실 감소 |
| `tests/train/test_stagea_train_cli.py` | 정답 원천 지정 해석(oracle 원천 없음), 검증 부분집합 결정성, 시드 범위 파싱 |
| `tests/train/test_stagea_qwen.py` | 파드 전용(transformers·peft·Qwen3-VL 처리기 파일 필요, 없으면 건너뜀): 템플릿 이어쓰기 동일성, 작은 Qwen3-VL 무작위 모델로 학습 경로 = 추론 에뮬레이션, LoRA 대상 층, 병합 도구, `train`→`load` CLI 끝까지 |

파드 쪽(모두 `/data/harvest` 아래): 코드 사본 `/data/harvest/code_stageA`(다른 에이전트 코드 폴더와 분리), venv `/data/harvest/venv_train`(설치 스크립트 `/data/harvest/setup_train.sh`, 고정 목록 `/data/harvest/venv_train_freeze.txt`), 실행 스크립트 `/data/harvest/ckpt/stageA/run_stagea.sh`·`smoke*.sh`·`serve_merged.sh`, 스모크 산출 `/data/harvest/ckpt/stageA/{smoke_labels_v2,smoke_short1,smoke_0924_plan_aborted}/`, 로그 `/data/harvest/ckpt/stageA/_smoke_logs/`.

## 3. 설계

### 3.1 항목 만들기 (`stagea_data`)
- 한 항목 = (결정 스냅샷 `decision=true`, DecCall 질문). 질문 = DecCall 6개와 정답이 있는 것의 교집합 = `dir_xy, dir_z, mag_coarse, target, phase` 5개. `progress`는 제외 — labels_v2의 `progress`는 옛 oracle 값 그대로라서(§54 "progress 그대로") **절대 쓰지 않는다**. `fine_dir`는 DecCall 질문이 아니다.
- 프롬프트 텍스트 = `question_text(req["state"], qid, spec)` — `jevl._body`와 바이트 단위로 같음(테스트). 보기 순서도 추론과 같음(`--` 순환 `shift`는 인자로만, 기본 고정 순서 — §53 판정 (4) "회전 필수 아님").
- 정답 원천 인터페이스: `source(line_without_oracle, question, option_keys) -> ({option_key...}, is_NE) | None`. 반환 키가 보기 집합 밖이면 오류(판본 어긋남 방지). 보기 이름(`shown name`)으로 바꿔 저장(§27 R5: 키 ↔ 이름).
  - `labels_v2`(기본): 파일 = 에피소드 폴더의 **형제 파일** `<폴더>.labels_v2.jsonl`(예: `jsel_dev/P0/` ↔ `jsel_dev/P0.labels_v2.jsonl` — `ep*.jsonl` 글롭에 안 걸림), `--labels-v2`로 경로 직접 지정 가능. 키 = (seed, kind, k). `phase` ← `phase_choice`.
  - `outcome`: `cli_label` 행의 `best_by_rule[rule]`. **NONE_ESCALATE 정답은 모든 보기 점수 = 0일 때만**(§52 결정 1; 점수는 그 규칙의 점수식을 저장된 롤아웃 결과로 다시 계산 — D-plan/D-time은 `score_outcome`, D-short(h)는 `short_score`). `finalize`로 다른 규칙이 박힌 행은 거부.
- 분할: 풀 에피소드 플래그 `fit → train`, `eval → val`. `dev`는 `--dev-val-seeds`를 준 스모크에서만(시드로 나눔), `cal`·`test`와 그 밖은 **항상 거부**. CAL/TEST 시드 파일은 읽지 않는다.

### 3.2 손실 (`stagea_loss`)
- 추론(jevl.py): 가지 노드(자식 ≥ 2)마다 [프롬프트][접두]로 한 번씩 호출해 자식 토큰의 원시 로그확률을 읽고, p̃(o) = Π_노드 softmax_자식(로짓)[다음 토큰].
- 학습: 인과 LM에서 [프롬프트][접두] 뒤 로짓은 뒤 토큰과 무관하므로, [프롬프트][보기 토큰]을 교사 강제로 넣은 서열에서 같은 로짓을 얻는다. `cover`가 모든 가지 노드를 지나는 보기 몇 개만 고른다(깊은 노드부터, 보기 순서로 결정적). 예: `mag_coarse`는 첫 토큰이 모두 달라 서열 1개, `dir_xy`는 `plus`/`minus` 가지 때문에 몇 개.
- 서열들은 같은 프롬프트를 복제해 오른쪽 패딩으로 한 묶음, `logits_to_keep = 최대 보기 길이 + 1`로 필요한 위치의 로짓만 계산, fp32로 올려 log-sum-exp. 전체 어휘 정규화 상수는 가지 안 재정규화에서 약분되므로 vLLM의 "원시 로그확률 → 재정규화"와 수학적으로 같은 값이다.
- 손실 = −logsumexp_{o∈target} log p̃(o). 정답 하나면 보통의 재정규화 NLL. (과제 문장의 "uniform target"은 이 집합 우도로 구현했다 — 균일 분포 교차 엔트로피 −(1/|B|)Σ log p̃(o)와는 다르다. 정답이 하나면 같다. D26 §1.4 식을 따랐다.)

### 3.3 모델·학습 (`stagea_train`)
- Qwen/Qwen3-VL-4B-Instruct(`/data/harvest/models/Qwen3-VL-4B-Instruct`, revision `ebb281ec…` 기록), BF16, SDPA 주의.
- LoRA r32 α64 dropout 0.05, 대상 정규식 `.*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)` = LLM 36층 × 7 선형층 = 252개, 학습 파라미터 66,060,288개. 비전 타워(`model.visual`, qkv/proj/linear_fc*)·병합기·`lm_head`(임베딩과 묶임)는 동결 — 학습 시작 때 LoRA 밖·비전 파라미터가 학습 가능하면 멈추도록 검사.
- AdamW lr 1e-4, weight decay 0, cosine, 워밍업 = ceil(3 % × 총 스텝), 기울기 자르기 1.0, 유효 배치 `--accum` 항목(기본 64), 1–2 에폭(기본 2).
- 조기 종료: `--eval-every` 스텝마다 val(풀 `eval` 판, standard) NLL, 좋아지면 `best/` 저장, `--patience`번 연속 나빠지면 멈춤. 스텝 0(영점) 평가도 기록. 끝에 `last/`.
- 기록: `config.json`(인자, 모델 revision, LoRA 대상, 항목 수·NE 수·다중 정답 수, 정답 원천, 프롬프트 관련 파일 7개 + e3lite sha256 앞 12자리, 판본, 장치), `log.jsonl`(스텝별 손실·기울기 노름·lr·처리량·최대 메모리, 평가별 NLL·정확도·p̃(정답 집합)·질문별 NLL).
- `question_id@vN`: DecCall 경로는 아직 `qid.py` 레지스트리에 연결돼 있지 않아서(질문 id = `ds21.dir_xy` 형식), 학습·평가 일치는 **프롬프트 관련 파일 해시**로 묶었다(열린 문제 5).

### 3.4 병합·서빙 (`tools/stagea_merge.py`)
- 기본 모델을 fp32로 올려 어댑터 병합(W + BA를 한 번만 BF16으로 반올림) → `save_pretrained`(safetensors) + 처리기·토크나이저·채팅 템플릿 파일 복사. 스모크 병합: 무작위 토큰 16개 로짓 최대 차 0.73(병합 BF16 대 fp32 기본+어댑터), 같은 입력에서 기본 BF16 대 기본 fp32 차(반올림 잡음 바닥) 1.13 → 병합 오차는 BF16 반올림 수준.
- 서빙 확인: `serve_merged.sh`(= `jsel/serve.sh`와 같은 옵션, `VLLM_BATCH_INVARIANT=1`, GPU 1, 메모리 0.30)로 병합 모델을 venv_vllm에서 띄우고 `JevLClient`로 DEV 10 스냅샷(S1 1 mm, 이미지) 60문항 → HF 기본+어댑터와 argmax **60/60 일치**, 보기 확률 최대 절대차 중앙 0.002, 95 % 0.024, 최대 0.073. 확인 뒤 서버는 내렸다. 지연·결정성 재측정(§50 절차)은 본 학습 모델로 따로 한다.

## 4. 테스트

- 로컬(`cd D:/qdd && python -m pytest -q`): **316 passed, 2 skipped**(torch 없는 기본 파이썬에서 torch 모듈 2개 건너뜀). CPU torch(`D:\tools\pylib_train`, 2.13 CPU)를 경로에 넣으면 `tests/train` **32 passed, 1 skipped**(transformers 없는 Qwen 모듈).
- 파드(venv_train, CPU, `CUDA_VISIBLE_DEVICES=`): `tests/train` **37 passed** (Qwen 구조 테스트 포함).
- 핵심 동일성 테스트
  - `test_training_logprobs_equal_jevl_inference_logprobs`: 모의 인과 LM(fp64) + 무작위 트라이 105개 — 학습 경로의 exp(log p̃) = `jevl.option_probs`(노드마다 [프롬프트][접두]로 따로 돌린 전체 어휘 로그확률), rel 1e-9.
  - `test_tiny_qwen3vl_training_logprobs_equal_inference_emulation`: 실제 Qwen3VLForConditionalGeneration 구조(2층, 무작위 초기화) + 실제 처리기·채팅 템플릿 + 672×376 JPEG — 추론 에뮬레이션은 노드마다 접두를 assistant 텍스트로 넣고 `continue_final_message`로 렌더링(= jevl의 vLLM 요청), 학습 경로와 rel 1e-4(fp32) 일치. mrope 위치·이미지 토큰·오른쪽 패딩·`logits_to_keep`까지 포함.
  - `test_template_continuation_is_generation_prompt_plus_prefix_ids`: 실제 DecCall 6질문의 모든 가지 접두에서 "이어쓰기 렌더링 토큰 = 생성 프롬프트 토큰 + 접두 토큰".
  - `test_build_items_ne_target_and_never_reads_oracle`·`test_target_source_is_pluggable_and_never_sees_oracle`·`test_build_snapshot_request_cannot_leak_oracle_into_prompt`: oracle을 바꿔도 정답·프롬프트 불변, 원천 함수에 oracle 키가 없음.

## 5. 스모크 결과 (H200 GPU 1, 다른 에이전트 Isaac 작업이 없을 때만 시작 — 대기 스크립트로 확인)

### 5.1 기본 모델 HF 대 기록된 vLLM(E3-lite 실행 파일) — 프롬프트·분해 동일성의 끝단 확인
| 조건 | 문항 | argmax 일치 | 최대 절대차 중앙 | 95 % | 최대 |
|---|---|---|---|---|---|
| S0 텍스트 | 120 | 1.000 | 8e-6 | 0.060 | 0.121 |
| S0 이미지 | 120 | 1.000 | 0.003 | 0.059 | 0.184 |
| S1 이미지(1 cm 격자, 기록 조건) | 120 | 0.992 | 5e-4 | 0.057 | 0.169 |

- 대부분 소수 셋째 자리까지 같고, 차이는 몇 문항에 몰린다. 차이가 나는 문항은 확률이 0.500/0.852/0.148처럼 BF16 로짓 간격(|로짓| 16–32에서 0.125)으로 양자화된 값 사이를 오간다 → 커널 차이(SDPA 대 vLLM 배치 불변 커널)에 따른 BF16 로짓 한 칸 차이. fp32 HF로 돌려도 vLLM에 더 가까워지지 않았다(같은 모양의 차이). 프롬프트가 달랐다면 텍스트 질문 대부분이 1e-5 수준으로 맞을 수 없다.

### 5.2 스모크 학습 3회 (모두 lr 1e-4, LoRA r32, 2 에폭, 50 스텝)
| 실행 | 데이터·정답 | 상태 | 항목(학습/검증) | 검증 NLL 스텝 0 → 최고 | 정확도 0 → 최고 시점 | 비고 |
|---|---|---|---|---|---|---|
| `smoke_labels_v2` (**§54 기준**) | DEV P0–P2 결정 스냅샷, labels_v2, 검증 = DEV 시드 25–29 | S1 1 mm | 200 / 50, 배치 8 | **3.759 → 0.656**(스텝 45) | 0.36 → 0.78 | 학습 손실 구간 평균: 스텝 1–5 2.40, 6–10 0.48, 11–20 1.18, 21–25 0.52, 26–35 0.71, 36–50 0.39. 질문별 최고 시점 NLL target 0.003, dir_z 0.149, phase 0.118, dir_xy 0.890, mag 1.596 |
| `smoke_short1` | 풀(대체된 run2 사본) 결과 기반 라벨, 규칙 D-short(1)(판별력 확인용, **규칙 선택 아님**) | S1 1 cm | 150 / 50, 배치 6 | 3.808 → 0.987(스텝 15) | 0.34 → 0.60 | 스텝 20부터 검증 과적합(dir_xy NLL 2.2 → 5.2) → 최고 어댑터(스텝 15) 보존이 작동 |
| `smoke_0924_plan_aborted` | 풀 결과 기반 라벨, 규칙 D-plan | S1 1 cm | 200 / 50 | 0.0026 → 1e-8 | 1.0 | D-plan best 집합이 거의 모든 보기(200/200 다중 정답) → 정답이 사실상 "NE만 아님"이라 학습 신호 없음(§48 판별력 문제 그대로). 스텝 30 평가 뒤 풀 폴더가 다른 에이전트에 의해 교체돼(이미지 없음) 중단 |

- **적재 확인**: `load`로 `smoke_labels_v2/best`를 새로 올려 같은 검증 50항목 → NLL 0.65589, 정확도 0.78 = 학습 로그의 최고 평가와 같다. `smoke_short1/best`도 0.98739로 같다.
- 병합 + vLLM 서빙: §3.4.
- 처리량(labels_v2 실행): 학습 400항목 98 s = **약 4.1 항목/s**(기울기 포함), 평가 550항목 41 s = 약 13 항목/s, 최대 GPU 메모리 26.8 GB(1항목 = 가지 덮는 서열 1–4개 묶음). `smoke_short1`(1 cm): 학습 약 3.3 항목/s.
- 풀 교체 주의: 스모크 중(15:06 UTC) 풀 담당 에이전트가 `/data/harvest/data/pool`을 다시 만들며 첫 풀과 라벨을 `pool_superseded_liftcut/`로 옮겼다. `smoke_short1`은 run2 풀 에피소드 2001·2002·2119(fit)·2061(eval)과 그 라벨(`pool_superseded_liftcut/v2_run2_partial/labels`)을 `/data/harvest/tmp/stageA/smoke_pool`에 복사해 썼다(2000·2060은 이미지가 없어 뺌). 원본 파일은 건드리지 않았다.

### 5.3 스모크에서 본 데이터 성질 (결정 아님, 참고)
- 대체된 run2 풀 5편(300 질문 행)의 결과 기반 규칙별 판별력(1 − |best|/|보기| 평균)과 정답 1개 비율: plan 0.011(0/300), time0.66 0.124(26), time0.33 0.308(78), short3 0.463(178), short2 0.564(226), short1 0.659(263). 모든 보기 실패(NE 정답) 0건. 규칙 선택은 `prereg_labeler.md`대로 DEV 자체 점검에서 한다 — 이 표는 그 선택에 쓰지 않는다.

## 6. 판본 (파드 `venv_train`, `/opt/conda/bin/python3` 3.11.9)

torch 2.13.0+cu130, torchvision 0.28.0, transformers 5.17.0, tokenizers 0.23.2, safetensors 0.8.0, huggingface_hub 1.33.0, pillow 12.3.0, numpy 2.3.5, httpx 0.28.1(`jevl` 임포트), **peft 0.21.0**, accelerate 1.15.0, pytest 9.1.1, triton 3.7.1.
- venv_vllm과 겹치는 패키지(torch·torchvision·transformers·tokenizers·pillow·numpy)는 **같은 판본**으로 고정했다 — 이미지 처리기(`Qwen2VLImageProcessor`)·채팅 템플릿 렌더링이 추론 쪽과 같아야 하기 때문.
- 새 라이브러리 = PEFT(huggingface/peft, HF 공식)·accelerate(HF 공식)뿐. TRL은 쓰지 않았다 — 맞춤 손실(트라이 재정규화)이라 `compute_loss`를 덮어써야 하는데, 평범한 PyTorch 루프가 더 짧고 검사하기 쉽다(D26 §1.4 "TRL/transformers+PEFT 맞춤 스크립트" 범위 안).
- `TORCH_DISABLE_NATIVE_JIT=1` 필수: torch 2.13이 일부 eager 연산(Qwen3-VL mrope의 bmm)을 Triton 커널로 보내는데, 그 런처 빌드에 C 컴파일러가 필요하고 파드에는 없다. 끄면 보통 ATen 커널을 쓴다(`run_stagea.sh`가 설정).

## 7. 전체 학습 시간 추정 [추정, 스모크 처리량 기준]

| 규모 | 학습 항목 | 2 에폭 학습 | 평가(검증 1,000항목 × 약 8회) | 합계 |
|---|---|---|---|---|
| 현재 풀 120편(결정 스냅샷 약 10/편, 5질문), fit 60편 | 약 3,000 | 6,000 / 4 ≈ 25 분 | 8 × 80 s ≈ 11 분 | **약 40 분** |
| D26 표 규모(POOL 600편, 9.5만 항목) | 95,000 | 190,000 / 4 ≈ 13 h | ≈ 0.5 h | 약 13–14 h(최적화 없이) |

- 병목은 1항목씩 도는 구조(메모리 27 GB만 씀). 여러 항목을 한 묶음으로, 같은 스냅샷의 5질문이 이미지·상태를 공유하는 점을 쓰면 몇 배 빨라질 여지가 있다 [미측정]. D26 §1.4의 "2만 항목 에폭당 30분 안"은 이 최적화 뒤에나 맞는다.
- 평가 비용을 줄이려면 `--max-val`로 검증 부분집합을 고정(결정적 선택, `select_val`)한다.

## 8. 열린 문제

1. **정답 최종화 대기**: labels_v2는 지금 DEV(`jsel_dev/P*.labels_v2.jsonl`)에만 있다. 풀(`/data/harvest/data/pool`, 재생성 중)에 labels_v2가 생기면 파일을 `<풀 폴더>.labels_v2.jsonl`(= `/data/harvest/data/pool.labels_v2.jsonl`)에 두거나 `--labels-v2`로 경로를 준다. 결과 기반 라벨의 규칙은 DEV 자체 점검 뒤 `finalize` — 그 전에는 `--rule`을 직접 줘야 한다.
2. **progress 질문은 학습하지 않는다**: 정답 원천이 없다(labels_v2의 progress = 옛 oracle). 그런데 LoRA가 LLM 전 층을 바꾸므로 progress 보기 확률도 영점에서 움직인다 → M7 progress 게이트·보정은 학습 뒤 모델로 다시 재야 한다.
3. **NONE_ESCALATE 소멸**: labels_v2에는 NE 정답이 없고, 결과 기반 라벨의 "모든 보기 점수 0"도 스모크 데이터에 0건. SFT 뒤 p(NE) → 0이 예상된다(D26 위험 2) → §52 결정 1대로 J5 집합 크기를 상위 호출 신호로 쓰는지 확인 필요.
4. **보기 순서**: 학습은 고정 순서(추론과 같음). §53에서 고정 순서 첫 자리 쏠림이 보였으므로, 순서 순환 증강(`shift`)을 켤지는 SFT 뒤 E3-lite 재측정에서 판정할 일.
5. **question_id@vN 미연결**: DecCall 질문 id에 `qid.py` 레지스트리 판본이 붙어 있지 않다. 지금은 프롬프트 관련 파일 해시를 `config.json`에 남긴다. 추론 쪽도 같은 해시를 기록해야 학습–평가 일치를 기계적으로 확인할 수 있다.
6. **BF16 수치 차**: HF 학습 경로 대 vLLM 추론은 BF16 로짓 한 칸(0.125) 차이로 일부 문항 확률이 0.05–0.18 흔들린다(argmax는 거의 항상 같음). 보정(온도·J5)은 반드시 **vLLM으로 서빙한 병합 모델의 확률**로 맞춘다.
7. **머리캠만**: §51 입력은 머리캠 + 우손목캠이지만 지금 Jev-L 추론 프롬프트가 머리캠 1장이라 학습도 그대로 따랐다. 손목캠을 넣으려면 `jevl._body`와 학습 `Scorer`를 함께 바꿔야 한다(이미지 순서 포함).
8. **과적합 신호**: 작은 스모크(150–200항목)에서 dir_xy·mag 검증 NLL이 에폭 2에 다시 오른다. 본 학습에서는 조기 종료가 작동하도록 `--eval-every`를 에폭당 4회 이상으로 둔다.
9. **가중치**: 풀의 `w_natural`(과다 표집 보정 가중치)은 손실에 쓰지 않았다(모든 결정 스냅샷 동일 가중). 필요하면 항목 가중 NLL로 바꾼다.
10. 스모크 산출 `smoke_short1/merged`·`smoke_labels_v2/merged`(각 8.5 GB)는 지연·결정성 재측정 연습용으로 남겨 두었다. 필요 없으면 지워도 된다.
