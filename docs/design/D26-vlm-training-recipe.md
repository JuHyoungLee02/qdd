# D26 — VLM 결정층 학습 레시피 조사 (단계 A: SFT→RL, 단계 B: action expert) (정본 §51)

작성: 2026-09-24, 조사 에이전트(D26). git 커밋 안 함.
읽은 것: 정본 `00-interfaces.md` §32–§35·§44·§48·§50·§51, `D19-action-expert.md`·`D20-expert-role.md`·`D24-jev-replacement.md`(요약·표), `docs/stage3/results/{jevl_model_select,labeler,pool,e3lite}.md`, `docs/superpowers/plans/2026-09-24-stage3-experiments.md` Task 14, `D:\qdd\CLAUDE.md`.
표기: **[원문]** = 1차 출처(arXiv abs/html, 공식 저장소·문서)에서 직접 확인한 것(짧은 인용은 영어 그대로), **[우리 접목]** = 우리 설계 제안, **[추정]** = 측정 안 한 계산값, **[미확인]** = 이번에 1차 확인 못 함, **[결정 필요]** = 사용자·메인 결정.
신뢰도 표기: **HIGH** = 상위 학회 게재 + 인용 ≥ 100, 또는 주요 연구소 대표 모델(인용 ≥ 1,000·공식 저장소 ≥ 5k★) / **MED** = 학회 게재지만 인용이 적거나, arXiv 전용이지만 인용 ≥ 40 또는 저장소 ≥ 1k★ / **LOW** = 그 밖. **LOW는 권고의 근거로 쓰지 않는다.** 인용 수는 Semantic Scholar API(2026-09-24 조회), ★는 GitHub API(같은 날).
기간 규칙: 2025-03-23 이후 처음 게시된 것만 기간 안. 그 전 것은 "**기간 밖, 기초 문헌**".
한계: E3-lite(§50) 결과가 아직 없다(`e3lite.md`는 사전 등록만). 풀·라벨(T13·T14)은 새 장면에서 아직 안 만들어졌다 — 아래 데이터 수·시간은 옛 장면 실측(`labeler.md`·`pool.md`)으로 계산한 [추정]이다.

---

## 0. 결론 요약

1. **단계 A = "LoRA SFT(오라클 라벨, 보기 안 재정규화 손실) → 짧은 on-policy RL(스냅샷 분기 보상, SFT 기준 KL 닻) → 질문별 온도 보정 → J5 conformal"**. 문헌이 일관되게 말하는 것: (i) 영점 모델이 과제 지식이 없으면 RL만으로는 못 올라간다 — SFT가 먼저 필요하다(Chu 외 ICML 2025, Yue 외 NeurIPS 2025). (ii) SFT를 오래·많이 하면 분포 밖에서 떨어진다(같은 Chu 외: V-IRL-L OOD 80.8 % → 1.3 %). RL은 분포 밖에서 오르거나 덜 잊는다(RL4VLA NeurIPS 2025, RL's Razor, Retaining by Doing). (iii) 로봇 데이터로 VLM을 통째로 미세조정하면 일반 VLM 능력이 무너진다(OpenVLA는 VQA 대부분 0점, VLM2VLA 표 1). LoRA·자연어 행동 표현·일반 데이터 섞기로 줄일 수 있다.
2. **우리 구조에 맞는 핵심 설계 [우리 접목]**: 결정이 "보기 토큰 하나"이고 시뮬 스냅샷을 복원할 수 있으므로, RL에서 GRPO식 표집이 필요 없다. 스냅샷마다 **모든 보기를 분기 실행해 얻은 보상(라벨러와 같은 롤아웃)**으로 기대 보상을 정확히 계산하고, KL(π‖π_SFT)로 닻을 건다. KL 정규화의 최적해는 π ∝ π_SFT·exp(R/β)라서 **확률이 한 보기로 무너지지 않는다** → M4·E1·J5가 쓰는 보기 확률이 살아남는다. RL이 SFT와 다른 점은 "학습된 선택기가 스스로 간 상태"(on-policy 스냅샷)에서 배운다는 것이다.
3. **보정**: 미세조정·RL은 과신을 만든다(RLCR: 보통 RLVR HotpotQA ECE 0.37 대 보정 보상 0.03). 우리 기본값은 **CAL 시드에서 질문별 온도 T_q 6개를 NLL로 맞춤 → 따로 떼어 둔 CAL 절반에서 J5 문턱** → TEST에서 ECE·Brier·AUROC·적중률을 standard·random 따로 보고. 라벨 스무딩은 기본 끔(절제만). 모델이 바뀔 때마다(A-SFT, RL 매 라운드, B) 다시 맞춘다.
4. **단계 B**: 같은 Qwen3-VL-4B 백본에 flow-matching action expert(잔차 R 청크, §35)를 붙이되 **expert → 백본 기울기 차단(KI, NeurIPS 2025)**, 백본은 결정 토큰 + 일반 VQA 데이터로 계속 학습. 공개 저장소 중 Qwen3-VL-4B + π식 flow expert를 지원하는 것은 **starVLA(3.7k★, MED)**. openpi(14k★)는 PaliGemma 백본이라 Qwen3-VL로 바로 못 쓴다.
5. **M4 새로움은 영향 없다** — M4는 "누가 확률을 내느냐"와 무관한 확정 규칙이다. 다만 학습된 결정 머리는 π0.5 상위 단·Hi Robot과 같은 모양이 되므로, **"LLM이 일반화한다" 주장은 영점 C 조건에만 걸고**, A·B는 "얼마나 학습하면 standard→random 낙폭(RD)이 얼마나 커지나"를 재는 짝 비교로 논문에 넣는다.

---

## 1. 질문 1 — 단계 A 레시피: VLM이 이산 행동·보기를 내도록 SFT

### 1.1 출처 표

| 출처 | 게재·반응 | 날짜 | 신뢰도 | 무엇을 가져오나 |
|---|---|---|---|---|
| SFT Memorizes, RL Generalizes (Chu 외, 2501.17161) | ICML 2025, 인용 726, 코드 LeslieTrue/SFTvsRL 335★ | 2025-01-28 | HIGH, **기간 밖, 기초 문헌** | SFT 과다 → OOD 붕괴, SFT는 RL 전 형식 안정용 |
| RL4VLM (Zhai 외, 2405.10292) | NeurIPS 2024, 인용 213, 417★ | 2024-05-16 | HIGH, **기간 밖, 기초 문헌** | VLM이 텍스트 행동을 내고 환경 보상으로 PPO — "VLM as policy with discrete actions"의 원형 |
| RT-2 (2307.15818) | CoRL 2023, 인용 4,306 | 2023 | HIGH, **기간 밖, 기초 문헌** | 행동을 토큰으로, 웹 데이터와 공동 미세조정 |
| OpenVLA-OFT (2502.19645) | 인용 906 | 2025-02-27 | HIGH, **기간 밖, 기초 문헌** | LoRA로 VLA 미세조정 관행 |
| Hi Robot (2502.19417) | ICML 2025, 인용 254 | 2025-02-26 | HIGH, **기간 밖, 기초 문헌** | 상위 VLM이 하위 과제 문장 예측(학습) |
| π0.5 (2504.16054) | Physical Intelligence, 인용 1,907, openpi 13,985★ | 2025-04-22 | HIGH | 상위 하위과제 예측을 같은 백본에서 공동 학습, GPT-4 영점 상위 단과 비교 |
| Embodied-R1 (2508.13998) | ICLR 2026, 인용 46, 156★ | 2025-08-19 | MED | Qwen2.5-VL-3B SFT 대 GRPO 같은 데이터 비교, 하이퍼파라미터 |
| Reason-RFT (2503.20752) | NeurIPS 2025, 인용 40 | 2025-03-26 | MED | SFT→GRPO 2단, 3 % 데이터로 70 % |
| RoboRefer (2506.04308) | NeurIPS 2025, 인용 153 | 2025-06-04 | HIGH | 공간 지시 VLM SFT→RFT(과정 보상) |
| VLM2VLA (2509.22195) | arXiv, 인용 52 | 2025-09-26 | MED(보조 근거만) | 행동을 자연어로 표현하면 LoRA만으로 망각 회피 |
| LoRA Without Regret (Schulman·Thinking Machines 블로그) | 동료 심사 없음, 널리 인용 | 2025-09-29 | MED | LoRA는 모든 층(특히 MLP)에, 학습률은 전체 FT의 약 10배, RL은 낮은 rank로 충분 |
| LoRA Learns Less and Forgets Less (2405.09673) | TMLR, 인용 406 | 2024-05 | HIGH, **기간 밖, 기초 문헌** | LoRA는 덜 배우고 덜 잊는다 |
| Qwen3-VL 기술 보고서 (2511.21631) + HF 설정 | 인용 2,297, QwenLM/Qwen3-VL 19,995★ | 2025-11-26 | HIGH | 이미지 토큰 계산 |
| RoboBrain 2.0 (2507.02029), VLA-RL (2505.18719) | arXiv, 인용 100·178, vlarl 458★ | 2025 | MED | 이번에 본문 수치를 확인하지 않음 → **권고 근거로 안 씀**(목록만) |

### 1.2 확인한 수치 [원문]

- **Embodied-R1** (Qwen2.5-VL-3B-Instruct 출발): "trained on eight NVIDIA A100 40G GPUs. The first phase was trained for 2 epochs, and the second phase for 1 epoch, with each phase taking approximately 48 hours." GRPO는 "learning rate of 1e-6", "number of samples to 8", "KL penalty (coefficient 1e-2), with a global batch size of 128". 같은 데이터 SFT 비교군은 "trained for 3 epochs". 데이터 = Embodied-Spatial-84K + ViRL 18K → Embodied-Points-200K. 코드 = EasyR1. 결론 문장: "Compared to the Embodied-SFT, Embodied-R1 demonstrates substantial improvements … validating the benefits of RFT in developing strong generalization".
- **Reason-RFT**: 2B 모델이 "70% of the final performance of Reason-RFT-Zero using only 3% of the training data (1,600 samples)". Qwen2-VL-2B/7B, 8×A800.
- **RL4VLM**: VLM이 CoT 뒤 텍스트 행동을 내고, 행동 토큰 로그 확률로 PPO. "removing the CoT reasoning results in a significant decrease". CoT 토큰 로그 확률이 행동 토큰보다 훨씬 커서 배율 λ로 줄였고 "choosing an extreme value (close to 1 or 0) will degrade overall performance".
- **π0.5**: 상위 단 = "first infer a high-level semantic subtask … then predict the action". 사전학습 280k 스텝(이산 토큰) + 사후학습 80k 스텝(flow expert 추가, 다음 토큰 예측 유지). 상위 추론 비교에서 "zero-shot prompting a large API-based model (GPT-4) performs worse"(학습한 상위 단보다).
- **VLM2VLA** 표 1: OpenVLA(7B)는 MMStar·MME·OCRBench·TextVQA·DocVQA 등에서 **0**, 출발점 Prismatic VLM은 MMStar 38.8·TextVQA 42.5. VLM2VLA(Gemma-3-12B, LoRA만)는 대부분 원래 수준 유지. 저자 주장: "representing low-level actions with natural language … makes it possible to train VLAs solely with Low-Rank Adaptation (LoRA)".
- **LoRA Without Regret**: "Even in small data settings, LoRA performs better when applied to all weight matrices, especially MLP and MoE layers." "Optimal LR is 10 times higher for LoRA." "LoRA performs equivalently to FullFT for reinforcement learning even with small ranks."
- **Qwen3-VL-4B 설정**(HF `config.json`·`preprocessor_config.json` 직접): 비전 `patch_size` 16, `spatial_merge_size` 2 → 이미지 토큰 1개 = 32×32 px. 텍스트 36층·hidden 2560, 비전 24층(deepstack 5·11·17). 머리캠 672×376 → 21×12 = **약 252 토큰**, 손목캠 1장 더하면 약 500 토큰 [우리 계산].

### 1.3 도구 (★ = 2026-09-24 GitHub API)

| 도구 | ★ | Qwen3-VL | 우리 용도 | 신뢰도 |
|---|---|---|---|---|
| LLaMA-Factory (hiyouga/LlamaFactory) | 75,003 | README 표에 "Qwen3-VL 2B/4B/8B… `qwen3_vl`" | 표준 SFT(정답 토큰 CE) 빠른 기준선 | HIGH |
| TRL (huggingface/trl) | 19,379 | (transformers 경유) | 맞춤 손실 SFT(`compute_loss` 덮어쓰기) | HIGH |
| ms-swift | 15,724 | 지원 | GRPO 계열 다수·다회차 GRPO | MED–HIGH |
| verl (verl-project/verl) | 23,600 | "multi-modal RL … Qwen2.5-vl", 다회차 agent loop | 대규모 RL(우리에겐 과함) | HIGH |
| EasyR1 (verl 포크) | 5,171 | "Qwen2-VL/Qwen2.5-VL/Qwen3-VL", 예제 `qwen3_vl_4b_geo3k_grpo_lora.sh` | 표집형 GRPO 대안(절제용) | MED |
| openpi | 13,985 | 아님(PaliGemma) | 단계 B 참조 구현(KI) | HIGH |
| starVLA | 3,723 (기술 보고서 2604.05014, 인용 105) | Qwen3-VL 4B·Qwen3.5 백본, "StarVLA-PI: Flow-Matching action expert (à la π₀)", 다목적 공동학습 | 단계 B 후보 코드 | MED |

### 1.4 우리 접목 — 단계 A SFT 설정 (Qwen3-VL-4B, H200 1장)

- **출력 형식은 지금 그대로**: 보기 이름(자연어, 정본 §27 R1–R6)의 토큰. 새 토큰을 어휘에 넣지 않는다(RT-2식 드문 토큰 덮어쓰기 금지). 근거: VLM2VLA의 "자연어 행동 → LoRA만으로 망각 회피"(MED, 보조), π0.5 상위 단도 자연어 하위과제. 보기 이름 첫 토큰이 겹치면 전체 문자열 로그 확률(정본 §44 그대로).
- **손실 = 보기 집합 안에서 재정규화한 확률의 NLL**: p̃(a) = softmax(보기 로그 확률). 오라클 라벨이면 −log p̃(오라클), 결과 기반 best **집합** 라벨이면 −log Σ_{a∈best} p̃(a). 추론 때 읽는 값과 학습 때 줄이는 값이 같아진다. 교차 엔트로피는 적절 점수 규칙이라 분포 안에서는 확률이 보정되는 쪽으로 간다(Guo 외 2017 HIGH, 기간 밖 — 과적합하면 과신). LLaMA-Factory는 이 손실을 못 하므로 **TRL/transformers + PEFT 맞춤 스크립트(수백 줄)**로 한다. LLaMA-Factory 표준 CE는 절제 기준선으로만.
- **`NONE_ESCALATE` 문제 [우리 접목, 중요]**: 오라클은 이 보기를 절대 고르지 않으므로 그대로 SFT하면 p(NONE_ESCALATE) → 0이 되어 상위 호출 신호가 사라진다. 풀의 `ambiguous`(near 띠) 스냅샷과 라벨러 best 집합이 모든 보기를 덮는 스냅샷을 `NONE_ESCALATE` 정답으로 표시하거나(규칙은 사전 등록), 상위 호출을 J5 예측 집합 크기로만 판단하도록 정한다. [결정 필요 — 메인]
- **어디를 학습하나**: LoRA r = 32(절제 16·64), α = 2r, **LLM의 모든 선형층(q,k,v,o,gate,up,down)**, 비전 타워·병합기 동결(표준 장면 텍스처 암기를 줄이려는 것 [우리 추정]; 절제: 병합기만 풀기). 전체 FT는 절제 1개로만.
- **하이퍼파라미터**: 학습률 1e-4(LoRA; 전체 FT라면 1e-5, "10배" 규칙), cosine, 워밍업 3 %, 유효 배치 64, bf16, **1–2 에폭**(Embodied-SFT 3 에폭보다 짧게 — Chu 외의 "SFT를 늘리면 OOD 하락" 때문), 검증 = 따로 둔 POOL `eval` 판(standard)에서 NLL 최소 체크포인트. random은 고르는 데 쓰지 않는다(EVAL §2 규칙 10).
- **이미지**: 머리캠 672×376 원해상도(252 토큰) + 우손목캠 1장(§51 입력). `max_pixels`를 원해상도에 맞춰 줄이지 않는다.
- **추론 배포**: LoRA를 병합한 가중치로 vLLM에 올린다 → `VLLM_BATCH_INVARIANT=1` 결정성·p95 지연 측정(§50 절차)을 병합 모델로 다시 한다(허용선 0.33 s).
- **시간 [추정]**: 항목당 약 1.3k 토큰(이미지 2장 약 500 + 텍스트 약 650 + 기하 요약 약 150). 9.5만 항목 × 1.3k = 1.24억 토큰/에폭. 4.4B × 약 4(LoRA는 가중치 기울기 생략) × 1.24e8 ≈ 2.2e18 FLOP → H200 실효 250–350 TFLOPS면 **에폭당 약 2–2.5시간, 2 에폭 4–6시간**. 2만 항목이면 에폭당 30분 안. 처음 200스텝 실측으로 고친다.

---

## 2. 질문 2 — RL 단계: 시뮬 보상 GRPO/PPO

### 2.1 출처와 수치 [원문]

| 출처 | 신뢰도 | 확인한 것 |
|---|---|---|
| Chu 외 (ICML 2025, 기간 밖 기초) | HIGH | RL OOD: GP-L 11.5→15.0 %, V-IRL-L 80.8→91.8 %, GP-VL 11.2→14.2 %, V-IRL-VL 35.7→45.0 %. SFT OOD: "-8.1% on GP-L (11.5% 3.4%), -79.5% on V-IRL-L (80.8% 1.3%), -5.6% … GP-VL, and -33.2% (35.7% 2.5%) on V-IRL-VL". 동시에 "SFT is still necessary to stabilize the model's output format", "without SFT, all end-to-end RL runs fail to improve"(Llama-3.2-Vision-11B). "scaling up SFT degrades visual recognition capabilities". |
| RL4VLA (2505.19789, NeurIPS 2025, 인용 110, gen-robot/RL4VLA 288★) | HIGH | "RL fine-tuning, particularly with PPO, significantly enhances generalization in semantic understanding and execution robustness over SFT, while maintaining comparable visual robustness." "PPO as a more effective RL algorithm for VLAs than … DPO and GRPO." SFT는 "performance plateaus at roughly 16k trajectories". PPO 수렴 "about 42 hours on a single NVIDIA A100". 표 1 IND 성공 SFT 0.781 → RL 0.938. 실물 예비: 잡기 0.10 → 0.43, 집어 놓기 0.00 → 0.27. |
| SimpleVLA-RL (2509.09674, 인용 155, 1,864★) | MED | 결과(이진) 보상만으로 RL. LIBERO 시연 **과제당 1개** SFT 평균 48.9 → RL 뒤 96.9, 시연 전체(과제군당 500) SFT 91.0 → 99.1. |
| Yue 외 "Does RL Really Incentivize…" (2504.13837, NeurIPS 2025, 인용 1,042) | HIGH | "the base models achieve a higher pass@k score when k is large", "reasoning abilities originate from and are bounded by the base model", "distillation can introduce new reasoning patterns". → **영점 모델이 모르는 것은 RL이 못 만든다; 증류(SFT)가 먼저.** |
| Entropy Mechanism (2505.22617, 인용 426) | MED | 엔트로피 개입 없는 RL은 "policy entropy dropped sharply at the early training stage", 성능 포화와 함께 옴 → Clip-Cov·KL-Cov. |
| DAPO (2503.14476, NeurIPS 2025, 인용 2,612) | HIGH, **기간 밖(2025-03-18), 기초 문헌** | 동적 표집·clip-higher(그룹 전원 같은 보상이면 기울기 0 문제). |

### 2.2 "RL이 SFT보다 일반화"의 적용 범위 — 정직한 한정

- 증거는 **같은 데이터·같은 계산에서 SFT를 계속 늘린 것 대 RL**(Chu 외), 또는 **SFT 뒤 RL을 더한 것 대 SFT 멈춘 것**(RL4VLA, SimpleVLA-RL, Embodied-R1)이다. "SFT 없이 RL"은 영점이 형식·지식을 못 갖출 때 실패한다(Chu 외, Yue 외).
- 우리 영점 Qwen3-VL-4B는 **최빈 기준선 0.669보다 낮은 0.483**(§50)이다. 원인은 입력에 기하가 없던 것 → E3-lite가 먼저 입력을 고친다. 그래도 방향·크기를 이미지에서 읽는 능력은 영점에 약하다고 봐야 하므로 **SFT 단계를 건너뛰지 않는다**.

### 2.3 우리 접목 — RL 설정

**(1) 보상 = 스냅샷 분기(라벨러와 같은 롤아웃)**. 결정이 보기 토큰 하나이고 스냅샷 복원(T13)이 되므로, 한 상태 s에서 **보기 k개를 전부 실행**해 R(s,a)를 얻는다(라벨러가 이미 하는 일, 같은 방식 보기는 롤아웃 공유). 그러면 GRPO의 "같은 입력 G번 표집 → 그룹 평균 기준" 대신 **그룹 = 보기 전체, 기대값을 정확히** 계산할 수 있다:

  L(θ) = − Σ_s [ Σ_a p̃_θ(a|s) · (R(s,a) − R̄_θ(s)) ] + β · KL(p̃_θ(·|s) ‖ p̃_SFT(·|s)),  R̄_θ(s) = Σ_a p̃_θ(a|s) R(s,a)

  표집 분산이 없고(작은 데이터에 유리), GRPO의 "그룹 전원 동점 → 기울기 0"은 R이 모든 보기에서 같을 때만 생긴다(그 스냅샷은 정보 없음 → 버림). KL 정규화 최적해 p̃* ∝ p̃_SFT·exp(R/β)라서 확률이 한 점으로 무너지지 않는다(엔트로피 붕괴 방지; Entropy Mechanism MED·RLCR MED의 문제 제기와 같은 방향). β는 0.05–0.2에서 CAL 보정 지표로 고른다.

**(2) 상태 분포 = on-policy**. RL의 몫은 "학습된 선택기가 M4를 켠 채 스스로 몰고 간 상태"에서 배우는 것이다(SFT는 오라클 플래너가 간 상태만 봄 — D19의 VIRAL 근거 "fails to correct its own mistakes"와 같은 문제). 라운드마다: A-SFT(또는 직전 라운드) 모델 + M4 + 스크립트 스킬로 **standard POOL 시드 150판** 폐루프 → 그 판들의 0.33 s 격자 스냅샷(약 4k) 중 **분기 라벨을 붙일 2k**를 고름(모델과 오라클 불일치 전부 + p̃ 여유 < 0.2 전부 + 나머지 무작위 20 %, 규칙은 사전 등록) → (1)의 손실로 1 에폭 → 다음 라운드. **3라운드**.
  근거: on-policy 데이터가 망각을 줄인다("the mode-seeking nature of RL, which stems from its use of on-policy data, enables keeping prior knowledge intact", Retaining by Doing 2510.18874, MED; "RL is implicitly biased towards KL-minimal solutions", RL's Razor 2509.04259, MED).

**(3) 보상 정의**: 라벨러 점수(§48에서 사전 등록 규칙으로 고를 D-plan/D-short/D-time 중 하나)를 R(s,a)로 그대로 쓴다. 판 전체 성공(0/1)은 **보조 보상**으로만 — 한 판에 결정이 약 26개(DEV 2,387 스냅샷/90판)라 판 단위 보상의 공로 배분이 약하다. 판 단위 GRPO(같은 시드 8판을 표집해 비교, EasyR1)는 절제 1개로만.

**(4) 예산 [추정, 옛 장면 실측 기반]**: CPU PhysX 롤아웃 2–3 s, 스냅샷당 롤아웃 약 20개(질문 6개, 캐시 공유 뒤) → 스냅샷당 약 50 프로세스·초. 2k 스냅샷 × 50 s ≈ 28 프로세스·시간 → 12 프로세스(2.5코어씩, 쿼터 32코어)로 **라운드당 약 2.5 h** + 폐루프 150판(실시간 1.3–3.9배, 판 수십 초) 1 h 미만 + 학습 1 h 미만. **3라운드 ≈ 12 h**. 라운드마다 CAL 보정·RD를 기록해 RL이 RD를 키우면 멈춘다.

**(5) 알고리즘 선택 근거**: RL4VLA가 PPO > GRPO라 한 것은 **여러 스텝 연속 행동 VLA**(가치 함수가 공로 배분을 도움)의 결과다. 우리 (1)은 한 스텝 결정에 보기별 보상이 다 있으므로 가치 함수가 필요 없다(정확한 기대값이 PPO critic 역할을 대신). [우리 접목 — 문헌에 같은 형식의 직접 비교는 찾지 못함]

---

## 3. 질문 3 — 미세조정 뒤 보정

### 3.1 증거 [원문]

| 출처 | 신뢰도 | 확인한 것 |
|---|---|---|
| RLCR "Beyond Binary Rewards" (2507.16806, 인용 105) | MED | 이진 보상 RL은 "degrading calibration". HotpotQA 표 2: RLVR ECE **0.37**(OOD 평균 0.46) 대 RLCR **0.03**(OOD 0.21), 정확도 비슷(63.0 % 대 62.1 %). 답 토큰 확률 기준선은 "performs poorly, as the model typically commits to an answer during CoT reasoning, inflating output confidence"(표 1 ECE 0.26/0.43). 보상 = 정답 + Brier 점수("any reward function that uses a bounded, proper scoring rule"). |
| Restoring Calibration for Aligned LLMs (2505.01997) | ICML 2025, 인용 31 → MED | 선호 정렬 뒤 과신·보정 악화, 보정 인식 미세조정·ECE 정규화로 회복. |
| Guo 외 "On Calibration of Modern NNs" (1706.04599) | ICML 2017, 인용 9,908 → HIGH, **기간 밖, 기초 문헌** | 온도 스케일링 = 검증셋 NLL로 스칼라 T 하나. 순위(AUROC)는 안 바뀜. |
| Müller 외 "When Does Label Smoothing Help?" (1906.02629) | NeurIPS 2019, 인용 2,507 → HIGH, **기간 밖, 기초 문헌** | 라벨 스무딩은 보정을 돕지만 표현 정보를 지운다(증류 악화). |
| KnowNo (2307.01928) | CoRL 2023, 인용 442 → HIGH, **기간 밖, 기초 문헌** | 보기 확률 → conformal 예측 집합(정본 J5의 근거). |
| Confidence Calibration in VLA (Zollo 외, 2507.17383) | arXiv, 인용 11 → **LOW** | 프롬프트 앙상블·행동별 Platt 스케일링. **권고 근거로 쓰지 않는다**(우리 C3'' 순서 순환 평균과 같은 발상이라는 참고만). |

### 3.2 우리 기준값 (현재 영점, §50)

Qwen3-VL-4B 영점: ECE 0.402, AUROC(p_chosen→정답) 0.599 — 이미 쓸 수 없는 수준. 학습 뒤 확률을 게이트에 쓰려면 보정이 반드시 따로 필요하다.

### 3.3 우리 접목 — 보정 절차(사전 등록 후보)

1. **분할**: CAL 시드(풀 코드가 이미 TEST·TEST-P5·CAL을 따로 거부·관리)를 판 단위 반으로 나눔 → CAL-T(온도) / CAL-C(conformal). TEST는 보고만.
2. **질문별 온도 T_q**(6개)를 CAL-T에서 재정규화 보기 로짓의 NLL 최소로 맞춘다. 보기 순서 순환(C3'')을 쓰면 순환 평균 확률 위에서 맞춘다.
3. **J5 conformal 문턱**을 CAL-C에서 `question_id@vN`별로(정본 §31 그대로). 비적합 점수 = 1 − Σ_{a∈best} p̃(a)(best 집합 라벨) 또는 1 − p̃(오라클)(둘 중 하나를 사전 등록).
4. **보고**(TEST, standard·random 따로, 질문별): 정확도(오라클·best 집합), NLL, Brier, ECE-15, AUROC, 신뢰도 그림, J5 적중률(목표 1−α)과 평균 집합 크기, 단일 원소 비율. **random에서 적중률이 떨어지는 것 자체가 결과**다(교환 가능성 가정이 깨짐 — RD와 함께 보고).
5. **다시 맞추는 때**: 모델이 바뀔 때마다(A-SFT, RL 각 라운드, B). 온도·문턱은 모델 판본 해시와 함께 기록.
6. **라벨 스무딩**: 기본 끔. 절제 1개(ε = 0.1)만 — 온도 스케일링과 겹치고 AUROC 순위 정보를 줄일 수 있다(Müller 외).
7. **보정 인식 RL 항(조건부)**: RL 뒤 온도 보정 후에도 ECE > 0.05이거나 AUROC가 A-SFT보다 0.03 넘게 떨어지면, (1) 손실에 Brier 항 λ·Σ_a (p̃(a) − 1[a∈best])²를 더한다(RLCR의 적절 점수 규칙 보상을 **토큰 확률**에 옮긴 것 — RLCR은 말로 낸 확신도라 그대로 옮겨진다는 보장은 없음, [우리 접목]).
8. **판정 기준 후보 [결정 필요 — 메인, 사전 등록]**: 온도 뒤 standard ECE ≤ 0.05, AUROC ≥ 0.75, J5 적중률 ≥ 1−α−0.02.

---

## 4. 질문 4 — 단계 B: 이산 결정 토큰 + 연속 action expert 공동 학습

### 4.1 증거 [원문]

- **KI "Knowledge Insulating VLA"** (2505.23705, NeurIPS 2025, 인용 151, Physical Intelligence) — HIGH. 핵심: "naively including such experts significantly harms both training speed and knowledge transfer". 처방: 백본은 **이산 행동(FAST) + 일반 VLM 데이터로 다음 토큰 예측**, expert는 flow matching, "Gradients do not flow from the action expert to the backbone, insulating the knowledge of the backbone." 절제에 "joint-training … without the stop-gradient"와 "w/o VLM data"가 있고, 결론: "such models suffer from a significant loss of pre-trained knowledge, and propose a method that can greatly mitigate this degradation". openpi README: `pi05_droid`는 "fine-tuned on the DROID dataset with knowledge insulation: fast inference and good language-following". (단, openpi는 "only support the flow matching head for both π0.5 training and inference" — FAST 공동 손실 학습 코드는 공개판에 없음.)
- **π0.5** — 사후학습은 "jointly trains with next-token prediction, to preserve text prediction capabilities, and flow matching for the action expert (which is initialized with random weights …)", 80k 스텝. 사전학습 예시의 "97.6% during the first training phase" 가 목표 로봇 가정 과제가 아닌 데이터. 웹 데이터 빼기(no WD): 전체 과제 성공 차이는 "not statistically significant", 그러나 "removing web data (no WD) causes significantly worse performance on out-of-distribution (OOD) objects", 상위 추론에도 큰 영향.
- **InternVLA-M1** (2510.13778, 인용 77, 432★) — MED. 차단 대신 감쇠: "gradient decay factor … attenuates the gradients propagated from the Action Expert back to the VLM (e.g., by a factor of 0.5)". 매 스텝 두 종류 배치를 함께 처리해 한 번에 갱신.
- **VLM2VLA** (MED, 보조): "co-training is not a guaranteed solution to catastrophic forgetting".
- **섞는 비율**: 읽은 1차 출처(π0.5·KI·InternVLA-M1)에 **공개된 배치 비율 수치가 없다** [미확인]. 따라서 비율은 우리 측정(보존 탐침)으로 정한다.

### 4.2 우리 접목 — 단계 B 개요

- **구조**: 단계 A 체크포인트(Qwen3-VL-4B + 병합 LoRA) + flow-matching expert(약 0.3B [추정], 백본 KV에 주의) → 출력 = **구간 제한 잔차 R 청크**(§35, 0.5 s·10 Hz 생성, D19 §33). 결정 토큰 출력은 단계 A와 **같은 위치·같은 보기 토큰**이어서 M4·E1·J5는 그대로.
- **기울기**: KI식 **완전 차단**을 기본(HIGH 근거), InternVLA-M1식 0.5 감쇠를 절제 1개.
- **백본 손실**: 결정 토큰 NLL(단계 A 손실 그대로) + (선택) 잔차 R의 FAST 토큰 다음 토큰 예측(KI "having both action representations at training time is crucial") + 일반 VQA 공동 학습.
- **섞는 비율 출발점 [우리 추정]**: 결정 : 잔차 행동 : 일반 VQA = 1 : 1 : 0.25(배치 수). 일반 VQA 보존 탐침(§5.2)이 A 대비 2점 넘게 떨어지면 VQA 몫을 0.5로 올린다.
- **코드**: starVLA의 Qwen3-VL-4B + "PI"(flow expert) 프레임워크(MED, 3.7k★, 동결 옵션 `--trainer.freeze_modules`)를 출발점으로 하되 KI 차단은 우리가 넣어야 할 수 있다 [미확인 — 코드에서 확인 필요]. openpi는 백본이 달라 참조용.
- **깨지는 것**: (i) 백본 일반성(KI·VLM2VLA), (ii) 결정 토큰 보정 이동 → 다시 맞춤, (iii) 지연 — expert 추가로 3 Hz 결정 경로의 p95가 늘면 결정은 expert 없이 한 번, 행동은 따로 부르는 두 경로로 둔다.
- **평가 공정성**: 주 표 실행기는 S(§34). B는 "결정 + 실행을 한 모델로 합쳤을 때"의 별도 행.

---

## 5. 질문 5 — 일반화 긴장: 로봇 데이터 미세조정은 일반화를 줄이나

### 5.1 증거 정리

- 줄인다(강한 증거): OpenVLA VQA 대부분 0(VLM2VLA 표 1), KI "significant loss of pre-trained knowledge", Chu 외 SFT OOD −79.5 %p(V-IRL-L)·"scaling up SFT degrades visual recognition", π0.5 no WD → OOD 물체 악화.
- 줄이는 방법(근거 있음): LoRA(LoRA Learns Less and Forgets Less, 기간 밖 HIGH; VLM2VLA MED), 자연어 행동 표현(VLM2VLA), 일반 데이터 공동 학습(π0.5·KI), SFT를 짧게 + on-policy RL(Chu 외, RL's Razor, Retaining by Doing), expert 기울기 차단(KI).
- 반대편 증거: π0.5에서 **영점 GPT-4 상위 단이 학습한 상위 단보다 못했다**. 즉 "학습하면 분포 안에서는 이긴다"는 강하다. 사용자 주장("LLM이 일반화")은 **분포 이동 뒤 낙폭**의 주장이지 절대 성능의 주장이 아니다 — 측정도 그렇게 해야 한다.

### 5.2 우리 접목 — 재는 방법

1. **RD(standard → random 낙폭)**: 결정 정확도(오프라인 스냅샷)와 폐루프 성공률 둘 다. 조건 C / A-SFT / A-SFT+RL / B를 **같은 스냅샷·같은 인식 앞단**에서 짝 비교, 판 단위 부트스트랩 95 % CI. 주장 문장은 "같은 인식 앞단 위에서"(EVAL §4 D4 F1 규칙).
   - 우리 Isaac 장면의 random = EVAL이 RoboDojo `_random`에 쓴 5축(방해물·탁자 재질·바닥 재질·조명·HDR 배경)을 같은 방식으로 적용한 시험 전용 판 [결정 필요 — 메인: 우리 장면에 5축 무작위화를 구현할지]. 학습 데이터는 standard에서만(EVAL §2 규칙 10).
2. **일반 VLM 보존 탐침**: 공개 벤치 작은 부분집합(예: MMStar·RealWorldQA·CV-Bench 각 300문항, 고정 시드)을 영점·A·A+RL·B에서 잰다. 결정 정확도와 무관한 "얼마나 잊었나" 지표.
3. **KL 진단**(RL's Razor): random 스냅샷 프롬프트에서 KL(p̃_학습 ‖ p̃_영점)의 평균. RL's Razor가 망각의 예측 변수로 제시한 값이라, RD와 함께 그리면 "얼마나 움직였나 ↔ 얼마나 떨어졌나"가 보인다(싸다, 분석용).
4. **데이터 양 곡선**: SFT 5k / 20k / 80k 항목에서 standard 정확도와 RD를 함께 그린다 — 과적합 지점이 곧 권장 데이터 양이다.

---

## 6. 질문 6 — 우리 권고

### 6.1 만들어야 할 데이터 (새 장면 기준, [추정])

| 묶음 | 양 | 라벨 | 비용 |
|---|---|---|---|
| SFT 학습 | standard POOL **600판**(P0/P1/P2 각 200) × 약 26 스냅샷 ≈ **1.6만 스냅샷 × 6질문 ≈ 9.5만 항목** | 오라클(플래너 답) — 풀 만들 때 공짜 | 판 생성만(CPU PhysX 12 프로세스로 수 시간) |
| SFT 검증 | POOL `eval` 60판 ≈ 1.5k 스냅샷 | 오라클 + 결과 기반 best 집합 | best 집합 1.5k × 50 s ≈ 21 프로세스·h → 약 2 h |
| 보정 | CAL 시드 60판 ≈ 1.5k 스냅샷(CAL-T/CAL-C 반씩) | 오라클 + best 집합 | 약 2 h |
| RL | 라운드당 150판 폐루프 → 2k 스냅샷 분기 라벨 × 3라운드 | 분기 보상 R(s,a) | 라운드당 약 2.5 h |
| 시험 | TEST 시드 standard + random(짝) | 오라클 + best 집합 | 시험 때만 |

- 양의 근거: RL4VLA(연속 행동 VLA)는 16k **궤적**에서 SFT 포화, Reason-RFT는 1.6k 샘플로 70 %. 우리 문제는 보기 ≤ 10개 분류라 훨씬 작다 → 9.5만 항목은 넉넉한 상한이고 §5.2-4 곡선으로 줄인다. 먼저 **기존 설계대로 POOL 120판(약 3k 스냅샷, 1.9만 항목)**으로 1회 돌려 곡선의 첫 점을 얻는다.
- 입력은 E3-lite가 고른 상태 표현(S0/S1/S2)을 따른다. **S1(기하 줄)을 넣으면 방향·크기는 사실상 텍스트 해석 문제**가 되어(코드 규칙 상한 UB가 이를 잰다) 학습 효과의 대부분이 "텍스트 읽기"로 간다 → 그때 standard→random 낙폭은 인식 앞단(H4)으로 옮겨간다. 이 점을 결과 해석에 미리 적는다.

### 6.2 권장 레시피 (단계 A)

| 단계 | 설정 |
|---|---|
| A0 영점 C | 지금 Jev-L(E3-lite 입력) — 기준선 |
| A1 SFT | Qwen3-VL-4B-Instruct, LoRA r32 α64 LLM 전 선형층, 비전 동결, 재정규화 보기 NLL(오라클; best 집합은 절제), lr 1e-4 cosine, 워밍업 3 %, 배치 64, 1–2 에폭, standard 검증 NLL로 조기 종료, TRL/transformers+PEFT 맞춤 스크립트, H200 1장 4–6 h(9.5만 항목) |
| A2 RL | on-policy 3라운드, 분기 보상 정확 기대값 손실 + β·KL(p̃‖p̃_SFT), β ∈ {0.05, 0.1, 0.2}, lr 5e-5, 라운드당 1 에폭, 합계 약 12 h |
| 보정 | CAL-T 질문별 온도 → CAL-C J5 문턱, 모델 바뀔 때마다 |
| 배포 | LoRA 병합 → vLLM 배치 불변, 결정성 flip 0·p95 ≤ 0.33 s 재측정 |

### 6.3 절제 (사전 등록 후보)

주 비교: **C / A-SFT / A-SFT+RL / B** × {standard, random}, 지표 = 결정 정확도·ECE·AUROC·J5 적중률·폐루프 성공·RD·보존 탐침·KL.
부 절제: LoRA 대 전체 FT, 오라클 라벨 대 best 집합 라벨, SFT 데이터 5k/20k/80k, 에폭 1 대 3, 일반 VQA 공동 학습 0 대 20 %, RL β, 판 단위 GRPO(EasyR1) 대 분기 정확 기대값, 라벨 스무딩, B의 기울기 차단 대 0.5 감쇠.

### 6.4 논문 주장에 남는 것

- **M4 새로움: 영향 없음.** M4는 시간차 겹침 typed 호출의 합의 + 실행 뒤 예상 대 측정 무효화이고, 확률을 내는 쪽이 영점이든 학습이든 규칙은 같다. 오히려 "A-SFT/RL로 바뀐 확률에서도 M4 이득이 유지되나"가 강건성 결과가 된다.
- **바뀌는 것**: 학습한 결정 머리는 Hi Robot·π0.5 상위 단·HiVLA와 같은 "학습된 계층 정책"이다(D24 §새로움 점검). 그래서 (i) "LLM이 일반화한다"는 문장은 **영점 C 조건과 그 RD**에만 쓴다. (ii) A·B는 "학습량을 늘릴수록 RD가 어떻게 변하나"(C < A-RL < A-SFT < B 순이면 사용자 주장을 지지, 아니면 반박)로 보고한다 — 어느 쪽이 나와도 논문 결과가 된다. (iii) 공개 선행과의 차이는 M4·평가에만 둔다.

---

## 7. 위험

1. **라벨 판별력**: 10 s 지평 결과 라벨은 방향·크기에서 거의 동점(§48). SFT는 사실상 **오라클 플래너 모방**이 된다 → 학습한 선택기 = 플래너 증류 정책. 일반화 주장에 불리할 수 있다.
2. **NONE_ESCALATE 소멸**: SFT가 상위 호출 보기를 죽인다(§1.4) — 라벨 규칙이나 J5 집합 크기 대체가 필요.
3. **standard 암기**: 비전 동결·LoRA·짧은 SFT로 줄이지만 random 낙폭이 커질 수 있다(Chu 외). RL 라운드마다 RD·보존 탐침을 보고 나빠지면 멈춘다.
4. **보정 붕괴**: RL 엔트로피 붕괴 → KL 닻·온도·(조건부) Brier 항. 순위(AUROC)가 무너지면 온도로 못 고친다.
5. **결정성·지연**: 병합 가중치로 재측정 필수. 손목캠을 더하면 입력 토큰이 약 250 늘어 p95가 허용선을 넘을 수 있다.
6. **sim→real**: 시뮬 렌더 이미지로만 학습 — 실물(FFW-SG2, §38) 전이는 별도 시험 필요.
7. **단계 B 코드**: starVLA는 MED(기술 보고서 인용 105) — KI 차단 구현 여부를 코드로 확인해야 한다. 섞는 비율의 공개 근거가 없다.
8. **RL 설계의 직접 선례 부족**: "스냅샷 분기로 보기별 보상을 다 구해 정확 기대값 + KL" 형식의 VLM 결정 RL 직접 비교 논문은 이번에 찾지 못했다 — 표집형 GRPO를 절제로 반드시 같이 둔다.

---

## 8. 출처 링크

- SFT vs RL: https://arxiv.org/abs/2501.17161 / RL4VLM: https://arxiv.org/abs/2405.10292 / RL4VLA: https://arxiv.org/abs/2505.19789 / SimpleVLA-RL: https://arxiv.org/abs/2509.09674 / Yue 외: https://arxiv.org/abs/2504.13837 / Entropy: https://arxiv.org/abs/2505.22617 / DAPO: https://arxiv.org/abs/2503.14476
- π0.5: https://arxiv.org/abs/2504.16054 / KI: https://arxiv.org/abs/2505.23705 / InternVLA-M1: https://arxiv.org/abs/2510.13778 / VLM2VLA: https://arxiv.org/abs/2509.22195 / Hi Robot: https://arxiv.org/abs/2502.19417 / RT-2: https://arxiv.org/abs/2307.15818 / OpenVLA-OFT: https://arxiv.org/abs/2502.19645
- Embodied-R1: https://arxiv.org/abs/2508.13998 / Reason-RFT: https://arxiv.org/abs/2503.20752 / RoboRefer: https://arxiv.org/abs/2506.04308 / Qwen3-VL: https://arxiv.org/abs/2511.21631, https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
- RL's Razor: https://arxiv.org/abs/2509.04259 / Retaining by Doing: https://arxiv.org/abs/2510.18874 / LoRA Learns Less: https://arxiv.org/abs/2405.09673 / LoRA Without Regret: https://thinkingmachines.ai/blog/lora/
- RLCR: https://arxiv.org/abs/2507.16806 / Restoring Calibration: https://arxiv.org/abs/2505.01997 / Guo 외: https://arxiv.org/abs/1706.04599 / Müller 외: https://arxiv.org/abs/1906.02629 / KnowNo: https://arxiv.org/abs/2307.01928 / VLA 보정(LOW): https://arxiv.org/abs/2507.17383
- 도구: https://github.com/hiyouga/LlamaFactory · https://github.com/huggingface/trl · https://github.com/modelscope/ms-swift · https://github.com/verl-project/verl · https://github.com/hiyouga/EasyR1 · https://github.com/Physical-Intelligence/openpi · https://github.com/starVLA/starVLA
