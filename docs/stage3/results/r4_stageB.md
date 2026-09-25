# R4 단계 B 학습 코드 (융합 모델: Qwen3-VL-4B + flow-matching action expert + 보조 기하 헤드) — 구축·스모크

작성 2026-09-24 UTC(R7 2회차 K1 정정 — 처음엔 KST 날짜를 적었다), R4 구현 에이전트. git 커밋 안 함. **본 학습은 돌리지 않았다.** 아래 수치는 전부 합성 데이터 스모크(파이프라인 동작 확인, 정본 §56)라서 결과로 쓰지 않는다.
근거: 정본 `00-interfaces.md` §32–§35, §51–§59(작업 중 코디네이터가 §58 융합 원칙·§59 D27 이미지 배치를 추가 지시), `D19`·`D20`·`D26`, `stageA_pipeline.md`·`stageA_sft.md`.

## 1. 결론 요약

- 모델 하나 = **Qwen3-VL-4B 백본(단계 A와 같은 판본·LoRA r32 대상)** + **flow-matching action expert(79.5M, 기본 크기)** + **보조 기하 헤드**. 손실 = λ_dec·결정 토큰 NLL(단계 A 손실 그대로) + λ_act·조건부 flow matching + λ_aux·보조 기하(+ λ_vqa·VQA 보존, 기본 끔).
- **KI(지식 격리)**: expert는 백본 은닉 상태를 `detach()`해서 읽는다. expert 손실이 백본(LoRA)에 주는 기울기가 **정확히 0**임을 모의 백본·실제 Qwen3-VL 구조(작은 무작위 모델) 둘 다에서 테스트로 확인했고, 끔(`none`)일 때는 새는 것이 보이고 `scale:0.5`일 때는 정확히 절반인 것도 확인했다(테스트가 누수를 볼 수 있다는 증거). 보조 기하 헤드·결정 손실의 기울기는 백본으로 **흐른다**(§58: 기하를 이미지에서 배우게).
- **런타임 입력 기본 = IMG 상태**(과제 문장 + 계약 요약 + 그리퍼 열림/닫힘 + 이미지), M1 좌표·술어 줄 없음. S0·S1 텍스트는 절제 옵션(`--state S0|S1`). 이미지 배치는 **§59(D27)** 그대로: system → "head camera:" + 머리 672×376 원본 → "right wrist camera (active arm):" + 손목 424×240 원본(양팔 스킬이면 두 손목) → 상태 → 질문. 실제 Qwen3-VL 처리기에서 이미지 토큰 **252 + 104**로 D27 값과 같음을 테스트로 확인.
- **행동 목표**: 기본 = 절대(스크립트 스킬 S의 명령을 교사 라벨로, §58), 절제 = 잔차(실행 − 스크립트, 차원별 ξ로 제한, expert가 스크립트 청크도 입력으로 받음, §35). 청크 = 15스텝 × 8차원(오른팔 7관절 위치 목표 rad + 그리퍼 폭 m) @ 30 Hz = 0.5 s.
- **스모크(파드 CPU, 작은 무작위 Qwen3-VL 구조 + 합성 데이터 50스텝)**: 검증 손실 fm 2.62 → 1.92, aux 1.65 → 1.13, 결정 NLL 0.787 → 0.630(정확도 0.29 → 0.71), 학습 총손실 처음 5스텝 평균 3.50 → 마지막 5스텝 2.31. KI 검사 시작·끝 모두 fm→백본 기울기 노름 0.0. 저장 → 새 백본에 어댑터 + 헤드 재적재 → 같은 잡음으로 예측 행동 최대 차 **0.0**, 검증 지표 소수점까지 같음.
- **GPU 스모크(갱신, GPU 2 — 사용자 허용 user-log 64, 렌더 없는 학습·추론 한정)**: 실제 Qwen3-VL-4B BF16 + LoRA r32(66.1M) + 기본 크기 expert(79.4M) + 보조 헤드(3.4M), 합성 40표본 50스텝. 검증 결정 NLL 1.158 → 0.482(정확도 0.67 → 0.75), 보조 1.638 → 1.049, fm 2.382 → 2.116(요동 큼), 학습 총손실 처음 5스텝 7.67 → 마지막 5스텝 2.45. KI 검사 시작·끝 fm→백본 기울기 노름 **0.0**. 저장·재적재 예측 최대 차 **0.0**. **지연(H200)**: expert 10스텝 eager p50 36.5 ms / p95 38–45 ms로 목표 30 ms를 **넘는다**; 같은 샘플링을 CUDA 그래프로 잡으면 p50 **23.1 ms** / p95 23.2 ms(eager와 출력 차 0.0)로 목표 안. 백본 문맥 순전파 포함 전체 1회(eager) p50 **120 ms** / p95 131 ms.
- **starVLA는 재사용하지 않았다**(§3). 최소 PyTorch 구현 `harvest/train/stageb_*.py`.

## 2. 구조

```
이미지(머리 + 활성 손목, D27 배치) + IMG 상태 텍스트
        │
   Qwen3-VL-4B (+LoRA r32, 비전 타워 동결)
        │ 은닉 상태 [T, 2560] (기본 마지막 층)
        ├──► 결정 토큰: 질문별 프롬프트 [상태 + 질문] → 보기 트라이 재정규화 확률 → set NLL   (백본으로 기울기)
        ├──► 보조 기하 헤드: 학습 질의 4개 attention pooling → MLP → 회귀 11 + 술어 7            (백본으로 기울기)
        └──► detach (KI) ──► action expert (교차 주의)
                              조건 토큰: 고유감각(23) · skill · phase · 확정 결정 토큰 5개
                              행동 토큰 15개: MLP([W·x_t ; 시간 임베딩]) (+ 잔차 모드: 스크립트 청크) + 위치
                              블록 8개: 자기 주의(전체) → 교차 주의(백본 문맥) → MLP, 폭 768, 헤드 12
                              → 속도 v(x_t, t)  [15 × 8]
```

- **백본 조건 방식 선택**: π0.5는 expert 층마다 백본 같은 층의 KV를 함께 주의한다. 우리는 **한 층(기본 마지막 층) 은닉 상태 서열에 교차 주의**로 했다 — KI에 필요한 것(expert가 백본 특징을 읽되 그 경계에서 기울기 차단)은 그대로이고, HF 백본의 주의 코드를 고치지 않아도 되는 가장 단순한 형태다(GR00T N1 계열 DiT도 교차 주의). 층별 KV 방식은 절제 후보(열린 문제 6). `layer` 인자로 층 선택 가능.
- **결정 토큰 조건**: expert는 확정 결정(M4 확정값, 학습 때는 라벨)을 "질문=보기 이름" 학습 임베딩 5개로 받는다. 백본 문맥 프롬프트에는 결정 문자열을 넣지 않았다 — 보조 기하 헤드가 결정 답을 보고 기하를 맞히는 지름길을 막기 위해서다.
- **문맥 프롬프트**: 결정 질문 없이 system + 이미지 + 상태만(`jevcall.canonicalize` 적용 — 결정 항목의 상태 문자열과 바이트 단위로 같음, 테스트). 결정 손실은 단계 A와 같은 질문별 프롬프트로 따로 계산.
- **flow matching (openpi 규약)**: x_t = t·ε + (1−t)·a, 목표 속도 u = ε − a, t ~ 0.001 + 0.999·Beta(1.5, 1); 추론은 t = 1 → 0 오일러 10스텝. 적분 방향·부호는 "정확한 속도장이면 오일러가 데이터에 정확히 도착"하는 테스트로 고정. 패딩 스텝(`valid = 0`)은 손실에서 제외.
- **정규화**: 절대 모드 = 학습 데이터 평균·표준편차(바닥 1e-3 rad, 1e-4 m), 잔차 모드 = ξ(기본 관절 0.05 rad, 그리퍼 5 mm [가정])로 나누고 [−1, 1]로 자름, 포화 비율을 `res_sat`로 기록. 고유감각도 평균·표준편차. 통계·어휘는 체크포인트 `stageb.json`에 저장.
- **보조 기하 헤드**: 회귀(그리퍼→대상 Δxyz·거리, 그리퍼→소단계 목표 Δxyz·거리(labels_v2의 G), 대상→놓을 곳 Δxyz; 5 cm = 1 단위, smooth-L1) + 술어(BCE: gripper_open, holding, lifted, upright, near, contact, on). 값이 없으면(null) 가림.
- **KI 모드**: `stop`(기본) / `none`(절제, 전체 기울기) / `scale:g`(InternVLA-M1식 감쇠 절제, D26 §4.2). `stop`이고 보조 헤드를 끄면 문맥 순전파를 `no_grad`로 해서 메모리를 아낀다.
- **VQA 보존**: `vqa_loss`(답 토큰 NLL) 구현, λ_vqa 기본 0. 데이터 원천은 아직 없다(열린 문제 5).
- **안전 투영**: §35의 과제 공간 투영(Jev 방향·크기 권위, |r⊥| ≤ ε)은 FK·야코비안과 S의 누적 이동이 필요해서 **모델 밖 R5 훅**에 둔다. 모델은 잔차 모드에서 차원별 상자 제한(|r| ≤ ξ)까지만 보장(테스트).
- **checkpoint**: `adapter/`(PEFT LoRA) + `heads.pt`(expert + 보조 헤드, `torch.load(weights_only=True)`로 읽음) + `stageb.json`(구성·정규화·어휘·KI·λ·**prompt_config**). `prompt_config` = 카메라 구성 문자열(`D27v1:head camera:|right wrist camera (active arm):`), 상태 모드, system 해시, 프롬프트 관련 파일 해시와 그 전체 해시 `sha` — §59 "question_id@vN 해시에 카메라 구성 포함"의 학습 쪽 기록.

## 3. starVLA 판단 (재사용 안 함)

- 확인(2026-09-24 UTC, GitHub API·원문): starVLA/starVLA 3,724★, 기본 가지 `starVLA_dev`, LICENSE = **MIT**(단 README·LICENSE에 "rebase 시 upstream 커밋 두 개를 별도 커밋으로 유지" 같은 귀속 조항 추가). API의 spdx는 NOASSERTION.
- `starVLA/model/framework/VLM4A/QwenPI.py`: 액션 헤드가 VLM의 마지막 N층 은닉 상태 목록을 받는 층별 flow-matching 헤드(`LayerwiseFM_ActionHeader`). 이 파일에는 **stop-gradient(detach)가 없고**, **텍스트/결정 토큰 NLL 공동 손실도 없다**(행동만 예측). DeepSpeed·accelerate 전제의 큰 프레임워크.
- 판단: 우리에게 필요한 핵심 두 가지(KI 차단, 트라이 재정규화 결정 손실과의 공동 학습)를 어차피 우리가 넣어야 하고, 단계 A 손실·프롬프트와의 바이트 일치를 유지하려면 우리 코드 경로를 써야 한다 → **최소 PyTorch 구현**(expert 약 200줄). 설계 참고(층별 조건)만 기록. 새 의존성 없음(`venv_train`의 torch·transformers·peft 그대로).

## 4. 파일

| 파일 | 역할 |
|---|---|
| `harvest/train/stageb_data.py` | R2 계약(`check_row`), IMG 상태(`image_only_state`), D27 이미지 배치(`images_of`·`camera_config`), 정규화(`ActionNorm`), 보조 라벨 벡터(`aux_vecs`), 어휘(`Vocab`·`dec_ids`), 풀 결합 로더(`load_stageb`: R2 행 × 풀 줄 × 단계 A 결정 항목), 합성 원천(`synthetic_rows`) |
| `harvest/train/stageb_expert.py` | `ActionExpert`, `fm_loss`, `sample_actions`(오일러 10스텝, 조건 인코딩 1회 재사용), `sample_time`, `insulate`(KI), `AuxGeomHead`·`aux_loss` |
| `harvest/train/stageb_model.py` | `StageB`(문맥 순전파, 조건·목표, 결정·flow·보조·VQA 손실, `predict`, 헤드 저장), `HFEncoder`(Qwen3-VL 처리기 + D27 표지 다중 이미지), `load_heads`·`new_model` |
| `harvest/train/stageb_train.py` | CLI `smoke`(합성, KI·저장/재적재·지연 검사) / `train`(실데이터, R2 행 필요), `train_loop`·`evaluate`(고정 잡음 검증)·`ki_check`·`latency`·`prompt_config`·`tiny_qwen` |
| `tests/train/test_stageb_data.py` | 순수 9개: IMG 상태 누수 없음, 상태 모드·이미지 배치·카메라 구성, 계약 위반 거부, 정규화·잔차 포화, 보조 라벨 가림, 어휘, 합성 결정성, 풀 결합(oracle 무관, 결정 기본값, S0 절제), `committed` 우선 |
| `tests/train/test_stageb_torch.py` | 모의 백본 11개: **KI stop에서 fm→백본 기울기 정확히 0**(none은 누수, scale:0.5는 정확히 절반), 공동 손실의 백본 기울기 = 결정 + 보조만, insulate 순전파 불변, 오일러 정확성, 시간 분포, flow 학습·샘플 수렴, 패딩 제외, 저장/재적재(절대·잔차), 잔차 상자 제한, VQA NLL, 공동 루프 손실 감소 |
| `tests/train/test_stageb_qwen.py` | 파드 전용 3개(실제 Qwen3-VL 구조·처리기): D27 배치(표지 순서, 이미지 토큰 252·104), 실제 구조에서 KI, LoRA 어댑터 + 헤드 저장/재적재 예측 일치(어댑터 없으면 달라짐) |

파드: 코드 사본 `/data/harvest/code_stageB`, 스모크 스크립트 `/data/harvest/ckpt/stageB/smoke_cpu.sh`·`smoke_gpu2.sh`, 산출 `/data/harvest/ckpt/stageB/smoke_tiny_cpu/`·`smoke_qwen4b_gpu2/`(log.jsonl, ckpt/, img/), 표준 출력 `smoke_tiny_cpu.out`·`smoke_qwen4b_gpu2.out`.

## 5. R2용 데이터 계약 (`<에피소드 폴더>.stageb.jsonl`, labels_v2처럼 풀 폴더의 형제 파일)

스냅샷마다 한 줄. 키 (seed, kind, k)로 풀 줄(이미지·text_state·split·decision)과 결합한다. 검사 = `stageb_data.check_row`.

| 필드 | 형식·단위 | 뜻 |
|---|---|---|
| `seed`, `kind`, `k` | int, str, int | 풀 줄과 같은 키 |
| `hz` | 30 | 청크 주기(다르면 거부) |
| `H` | int (기본 15 = 0.5 s) | 청크 길이 |
| `arm` | `"right"` \| `"left"` \| `"both"` | 활성 팔 → 손목캠 선택(§57·§59). 풀 줄 `images`에 `cam_wrist_right`(·`cam_wrist_left`) 필요 |
| `skill_id`, `phase_id` | str | t0에 실행 중인 스크립트 스킬·FSM phase |
| `proprio` | `{"q":[7] rad, "qd":[7] rad/s, "tau":[7] N·m(측정 토크), "grip":[폭 m, 폭 속도 m/s]}` | 고유감각(expert 입력) |
| `action_exec` | [H][8] | 실제로 보낸 명령(교사 S, 또는 §35 투영 뒤 S+R). 7 = 오른팔 관절 위치 목표 rad, 8번째 = 그리퍼 폭 목표 m(`snapshot._full_action`의 q8과 같은 뜻) |
| `action_script` | [H][8] | 스크립트 스킬 명령(잔차를 안 썼으면 `action_exec`와 같음) |
| `valid` | [H] ∈ {0,1} | 1 = 실제 스텝, 0 = 에피소드 끝 뒤 채움(뒤에만, 첫 스텝은 1) |
| `committed` (선택) | `{질문: 보기 이름}` | M4 확정 결정(DecCall에 보이는 보기 **이름** = 결정 토큰 문자열). 없으면 그 질문의 labels_v2 단일 정답 |
| `aux` | `{"reg": {이름: float\|null}, "cls": {이름: 0\|1\|null}}` | 특권 시뮬 기하(학습 신호 전용, 런타임 입력 아님). 회귀 이름 `g2tgt_dx/dy/dz/dist`, `g2goal_dx/dy/dz/dist`(labels_v2 소단계 목표 G), `tgt2place_dx/dy/dz`(m, 로봇 기준 좌표). 술어 이름 `gripper_open`, `holding_tgt`, `lifted_tgt`, `upright_tgt`, `near_tgt_place`, `contact_tgt_place`, `on_tgt_place`. 모르는 이름은 거부 |

- 청크 시작 = 스냅샷 시각 t(풀 줄 `t`). 결정 스냅샷이 아닌 줄도 넣어도 된다 — 그 샘플은 결정 손실 없이 행동·보조 손실만 낸다.
- 결정 항목은 단계 A 원천(labels_v2 형제 파일)을 그대로 쓰고 풀 `oracle`은 읽지 않는다(테스트). split은 풀 규칙 그대로(fit → train, eval → val, DEV는 `--dev-val-seeds`일 때만, CAL·TEST 거부).
- 이미지는 원본 해상도(머리 672×376, 손목 424×240)로 저장해야 D27 토큰 수(252 + 104)가 나온다.
- 합성 원천 `synthetic_rows`가 같은 형식의 표본을 만든다(R2가 오기 전 테스트·스모크용).

## 6. 테스트

- 로컬 `cd D:/qdd && python -m pytest -q`: 전부 통과(torch 없는 기본 파이썬 — stage B torch 테스트는 건너뜀, 순수 9개는 실행). CPU torch 경로(`D:\tools\pylib_train`)를 붙이면 `tests/train` 전부 통과(stage B 순수 9 + torch 11; Qwen 3개는 처리기 파일이 없어 건너뜀).
- 파드(`venv_train`, CPU, `CUDA_VISIBLE_DEVICES=`): `tests/train` **60 passed**(stage A 기존 37 + stage B 23, Qwen 구조 테스트 포함).

## 7. 스모크

### 7.1 CPU 스모크 (파드 CPU, `smoke_tiny_cpu`, 2026-09-24 18:12–18:13 UTC, 파드 시계는 정확 — R7 2회차 K1 정정)

조건: 실제 Qwen3-VL 구조를 줄인 무작위 초기화 백본(LLM 2층, 폭 64, 비전 2층) + 실제 처리기·채팅 템플릿 + LoRA r32, expert 폭 128·깊이 2(스모크 축소), 합성 40표본(학습 32/검증 8, 원본 크기 이미지 2장, D27 배치), 배치 4, 50스텝, lr LoRA 1e-3 / 헤드 1e-3, λ_aux 0.1, KI stop, 절대 모드, `nice 10`, 8 스레드.

| 지표 (검증 8표본, 고정 잡음) | 스텝 0 | 스텝 50 |
|---|---|---|
| flow matching 손실 | 2.623 | 1.921 |
| 보조 기하 손실 | 1.651 | 1.129 |
| 결정 NLL | 0.787 | 0.630 |
| 결정 정확도 | 0.29 | 0.71 |
| 샘플 청크 MSE(정규화 단위, 10스텝) | 2.644 | 2.229 |
| 샘플 청크 팔 관절 MAE | 0.373 rad | 0.344 rad |

- 학습 총손실: 처음 5스텝 평균 3.50 → 마지막 5스텝 2.31. 벽시계 46 s.
- **KI 검사**(학습 전·후, 실제 구조): fm → 백본 LoRA 기울기 노름 **0.0 / 0.0**, 보조 → 백본 0.61, 결정 → 백본 0.81, fm → expert 7.9.
- **저장·재적재**: 어댑터 + `heads.pt` + `stageb.json` → 새 무작위 백본(같은 시드)에 어댑터 적재 + 헤드 적재 → 같은 잡음 예측 최대 절대차 **0.0**, 검증 지표 전부 같음.
- **지연(CPU, 참고)**: 작은 expert 10스텝 샘플링 p50 14 ms / p95 39 ms, 문맥 순전파 포함 전체 p50 41 ms(문맥 454토큰). 기본 크기 expert(79.5M, 폭 768·깊이 8)를 4B 크기 문맥(2560차원 × 480토큰)으로 10스텝: CPU 8스레드 p50 **0.30 s** / p95 0.37 s — GPU 값이 아니므로 D19 목표(청크당 ≤ 30 ms, GPU) 판정에 쓰지 않는다.

### 7.2 GPU 스모크 (GPU 2, `smoke_qwen4b_gpu2`, 파드 시계 18:21–18:25 UTC)

조건: `/data/harvest/ckpt/stageB/smoke_gpu2.sh` — 실제 Qwen3-VL-4B-Instruct@ebb281ec BF16 + LoRA r32(학습 파라미터 66,060,288), expert 기본 크기(폭 768·깊이 8·헤드 12, 79,427,080), 보조 헤드 3,427,346, 합성 40표본(학습 32/검증 8, 원본 크기 이미지 2장, D27 배치, IMG 상태, 문맥 454토큰), 배치 4, 50스텝, lr LoRA 2e-4 / 헤드 5e-4, λ_aux 0.1, KI stop, 절대 모드. GPU 2(H200)만 사용, 다른 프로세스 없음 확인 뒤 시작. prompt_config sha `6c5c21c79289`.

| 스텝 | fm | 보조 | 결정 NLL | 결정 정확도 | 샘플 MSE(정규화) |
|---|---|---|---|---|---|
| 0 | 2.382 | 1.638 | 1.158 | 0.667 | 2.128 |
| 10 | 2.148 | 1.469 | 0.586 | 0.708 | 2.329 |
| 20 | 2.632 | 1.145 | 0.482 | 0.583 | 2.739 |
| 30 | 2.314 | 1.341 | 0.502 | 0.750 | 2.454 |
| 40 | 2.079 | 1.051 | 0.460 | 0.750 | 2.227 |
| 50 | 2.116 | 1.049 | 0.482 | 0.750 | 2.262 |

- 학습 총손실 처음 5스텝 평균 7.67 → 마지막 5스텝 2.45(결정 손실이 주로 줄었다). 50스텝 192.7 s(스텝당 약 3.9 s, 표본당 문맥 1 + 질문 3 순전파).
- fm·샘플 MSE는 50스텝·32표본으로는 거의 안 줄었다(검증 fm 2.38 → 2.12, 샘플 MSE 제자리). 무작위 초기화 79M expert를 이 정도 스텝으로는 못 배운다는 뜻이지 KI 때문은 아니다(작은 구조 스모크 §7과 모의 테스트에서 fm 학습은 확인). 본 학습에서 fm 곡선을 따로 본다.
- **KI 검사**: 시작 fm→백본 **0.0**(보조 0.21, 결정 34.4, fm→expert 52.0), 끝 fm→백본 **0.0**(보조 0.21, 결정 0.97, fm→expert 16.1).
- **저장·재적재**: 어댑터 + 헤드 → 새로 올린 4B 백본에 적재 → 같은 잡음 예측 최대 차 **0.0**, 검증 지표 전부 같음.
- **지연 (H200, 배치 1, 문맥 454토큰, 10 오일러 스텝)**:

| 측정 | p50 | p95 |
|---|---|---|
| expert 샘플링만, eager fp32 (스모크 로그, 30회) | 36.5 ms | 38.1 ms |
| expert 샘플링만, eager fp32 (따로 잰 벤치, 50회) | 36.5 ms | 45.0 ms |
| expert 샘플링만, eager bf16 autocast | 44.1 ms | 48.7 ms |
| expert 샘플링만, **CUDA 그래프**(eager와 출력 차 0.0) | **23.1 ms** | **23.2 ms** |
| 한 속도 스텝(eager fp32) | 3.5 ms | 4.4 ms |
| 전체 1회 = 4B 문맥 순전파(이미지 2장 인코딩 포함) + expert 10스텝, eager | **120 ms** | 131 ms |

  - eager는 커널 실행 지연이 병목이라(bf16이 오히려 느림) D19 목표(청크당 ≤ 30 ms)를 넘는다. CUDA 그래프로 잡으면 목표 안으로 들어온다 → 런타임(R5)에서 expert 샘플링은 CUDA 그래프로 돌린다(지금 코드에는 벤치로만 확인, 열린 문제 1).
  - 전체 120 ms는 HF 순전파 기준이다(vLLM 아님). 결정 호출(D27 lead 방식 설계값 0.28 s)과 합치면 §58 "한 번 호출"(**정정(정본 §67 C4)**: 런타임은 스텝마다 두 호출(decide → chunk), 백본 순전파는 스텝당 1회, 둘 다 HF 백본(`harvest/runtime/fused_model.py`))의 지연 예산을 R5에서 다시 짜야 한다.
  - H200 수치다. 실물 서버(RTX PRO 6000, §49) 값은 따로 재야 한다.

- 이 수치는 합성 데이터·작은 무작위 백본이라 **결과로 쓰지 않는다**(§56). 확인한 것은 손실 세 개가 함께 줄고, KI가 지켜지고, 저장/재적재가 비트 단위로 같다는 것뿐이다.

## 8. 열린 문제

1. **expert CUDA 그래프**: GPU에서 eager 36.5 ms(목표 30 ms 초과), CUDA 그래프 23.1 ms(목표 안). 런타임 코드(R5)에 그래프 캡처(고정 입력 버퍼 + `torch.cuda.graph`)를 넣어야 한다 — 지금 `stageb_train.latency`는 eager만 잰다. 실물 서버(RTX PRO 6000)에서 다시 잰다. (처음 판에서 GPU 2 사용이 막혔던 문제는 사용자 허용(user-log 64) 뒤 §7.2로 해소.)
2. **처리량**: 한 표본 = 문맥 1회 + 질문 5회 순전파(각각 같은 이미지 2장 재인코딩). 본 학습 규모에서는 질문 5개를 한 서열로 묶거나 이미지 인코딩을 공유해야 한다(단계 A §7과 같은 문제, R3 묶음 처리와 함께).
3. **런타임 한 번 호출(§58, R5)** — **정정(정본 §67 C4)**: 런타임은 스텝마다 두 호출(decide → chunk), 백본 순전파는 스텝당 1회, 둘 다 HF 백본(`harvest/runtime/fused_model.py`): 지금은 결정(질문별 트라이 호출)과 행동(문맥 순전파 + expert)이 다른 순전파다. vLLM 서빙과 expert를 한 서버에서 묶으려면 vLLM이 은닉 상태를 내주거나(현재 미지원 [미확인]) HF 순전파를 따로 둬야 한다 — 지연 예산(§49·§59 0.33 s)과 함께 R5에서 정할 일.
4. **절대 모드 목표 표현**: 관절 위치 목표 절대값. 현재 관절 기준 차분(Δq) 표현이 나을 수 있다(π0 계열은 절대, 여러 VLA는 차분) — 실데이터가 오면 절제.
5. **VQA 보존 데이터 원천 없음**: `vqa_loss`만 있고 λ_vqa = 0. D26의 1 : 1 : 0.25 비율과 보존 탐침은 VQA 원천(공식 공개 데이터셋)을 정한 뒤.
6. **백본 조건 방식**: 한 층 교차 주의(기본 마지막 층). π0.5식 층별 공유 KV, starVLA식 마지막 N층 조건은 절제 후보. 마지막 층은 다음 토큰 예측에 특화돼 있어 중간 층이 나을 수 있다(`layer` 인자).
7. **잔차 모드 ξ 값**(관절 0.05 rad, 그리퍼 5 mm)은 [가정]. §35의 과제 공간 투영은 R5 훅에서 구현해야 하고, R2가 기록하는 `action_exec`가 투영 뒤 값이어야 한다.
8. **IMG 상태의 `t_state` 줄**: 단계 문장("pick up mug o3")에 물체 id가 남는다 — 계약 요약이라 유지했지만 id가 M1 인식 결과를 암시하는지는 설계 확인 필요. 로봇 줄의 `closed_holding(o3)`은 `closed`로 줄였다.
9. **보조 헤드 라벨 좌표계**: 로봇 기준 좌표(m)로 가정. R2가 labels_v2의 G·Δ와 같은 좌표계를 쓰는지 확인 필요.
10. **로컬 pytest 임시 폴더**: 기존 테스트 모음이 `tmp_path`를 쓰므로 인자 없이 돌리면 C: 임시 폴더를 쓴다. 이번 작업의 실행은 모두 `--basetemp=D:/tools/scratch_qdd/pt`로 했다.
