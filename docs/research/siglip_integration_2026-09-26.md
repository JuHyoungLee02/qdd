# SigLIP·SigLIP 2를 Harvest에 엮는 방법 — 주축: 융합 VLA 안에서 (2026-09-26)

- 작성: SigLIP 조사 에이전트, 2026-09-26 01:56 UTC 경(한국시간 10:56). 사용자 지시 user-log 90 원문: "Siglip을 쓸 방법도 찾아봐 어떻게 엮을 수 있을지". 메인 세션 추가 지시(user-log 90 보충, 커밋 `6e86a68`): **"우리 VLA에 쓰는 것"이 주축** — 선택지 (a)–(e)를 평가하고, 특히 **(c) expert를 직접 조건 짓는 SigLIP2 흐름**과 **(e) 손목 영상 고해상도 SigLIP2**의 실현 가능성·통합 지점·비용·지연·E-MA2/E-SR0와의 관계·사전 등록 초안을 내고, **E-SR0 결과에 따른 조건부 권고**를 준다. 나머지 역할(상태 판정·호출 트리거·라벨링·경험 검색·위치 찾기)은 부차.
- 이 문서는 **조사와 실험 초안**이다. 학습·GPU 실행은 하지 않았다(파드는 설정 파일 읽기만). 코드·정본·책은 고치지 않았다.
- 조사 규칙: 1.5년(2025-03-26 이후)·신뢰도(학회 표기는 arXiv Comments·Semantic Scholar venue, 스타·라이선스는 GitHub API로 2026-09-26 확인). **웹 검색 할당량이 소진**되어 새 문헌은 arXiv API 검색·arXiv/HF 원문 직접 열람으로만 찾았다 — 검색 폭이 평소보다 좁다(한계 10절).
- 수치 표시: **[실측]** 우리 저장소 결과 문서 값, **[원문]** 논문·모델 카드에서 직접 읽은 값, **[추정]** 계산으로 낸 값(측정 아님 — 사전 등록의 지연 관문에서 실측으로 바꾼다).

---

## 0. 한 쪽 요약

1. **우리 VLA는 이미 SigLIP 2를 쓰고 있다.** Qwen3-VL 기술 보고서(arXiv 2511.21631) 원문: "We utilize the SigLIP-2 architecture as our vision encoder and continue training it with dynamic input resolutions, initialized from official pretrained checkpoints … use SigLIP2-Large (300M) for small-scale LLMs (2B and 4B)". 파드의 우리 가중치 설정(`/data/harvest/models/Qwen3-VL-4B-Instruct/config.json`, 읽기만)의 `vision_config` = 깊이 24·폭 1024·MLP 4096·헤드 16·패치 16·`gelu_pytorch_tanh`·정규화 평균/표준편차 0.5 — HF `google/siglip2-large-patch16-256`의 영상 설정(24층·1024·4096·16헤드)과 같은 모양이다. 차이는 (i) Qwen이 동적 해상도로 이어 학습한 가중치, (ii) 2×2 패치 병합(`spatial_merge_size` 2 → 영상 토큰 하나 = 32×32 px), (iii) ViT 5·11·17층 특징을 LLM 첫 세 층에 더하는 DeepStack(`deepstack_visual_indexes` [5, 11, 17])이다. 그리고 **우리 학습에서 이 영상 탑은 동결**이다(LoRA 대상은 `language_model.layers`만, `stageb_train.backbone_trainable`이 visual 파라미터 학습을 거부).
2. 그래서 "SigLIP을 VLA에 넣기"는 새 인코더를 들이는 일이 아니라 **(1) 이미 도는 SigLIP2 계열 탑의 특징을 expert에 더 직접 주거나, (2) 원본(더 크거나 병합 안 한) SigLIP2를 두 번째 흐름으로 더하는** 일이다. (a) 탑 교체·(b) 백본 교체·(d) SigLIP 특징 빠른 결정 헤드는 비용 대비 근거가 없어 **권하지 않는다**(3절).
3. **E-SR0 판정은 WEAK**(결과 문서 `docs/stage3/results/sr0.md`, 커밋 `704d520`; 사용자는 이어서 E-SR1b 준수율 목표를 **0.8**로 올림 — user-log 91): 반사실 방향 준수율 S-E2E **0.340**(우연 0.335)·R2 **0.431**(우연 0.333). expert는 결정 토큰보다 영상·고유감각으로 궤적을 정한다. **expert에 영상을 더 직접 주는 (c)·(e)는 이 경향을 키울 위험이 있다**(OpenVLA-OFT RSS 2025: 여러 시점 영상의 가짜 상관 때문에 FiLM 없이는 언어 따르기 33 % = 우연; KI NeurIPS 2025 그림 4(b): 행동 전문가를 둔 π0 언어 따르기 약 20 %).
4. **권고(E-SR0 결과 조건부, 4.6절)**:
   - E-SR0가 **OK**(FOLLOWS/PARTIAL)였다면: (e)를 먼저 — 그중 **비용 0인 자기 탑 판 (e0)**(Qwen ViT의 병합 전 손목 패치 416개를 expert 문맥에 더함, 새 가중치·새 순전파 없음)을 먼저, 이어 원본 SigLIP2 So400m 판 (e1). (c)는 (e)가 통과한 뒤.
   - **실제 결과인 WEAK에서는**: (c)·(e)를 지금 단독으로 돌리지 않는다. **E-SR1b(결정 드롭아웃 + CFG — `sr0.md` 5절 권고)를 R2에서 먼저** 하고, 통과한 레시피 위에서 (e0)를 **준수율 비열등 조건을 하드 규칙으로** 건 R2 실험으로 돌린다. (c)는 그 뒤에도 (e)가 이득을 보일 때만.
5. 부차 역할 중 가장 값진 것은 **새 환경 감지(임베딩 이동) 트리거**(SAFE NeurIPS 2025: VLA 내부 특징에 코사인 k-NN만으로 실패 탐지 ROC-AUC 81.3/73.9, 학습형 SAFE 82.3/78.0). 다만 선행 근거는 정책 **자신의** 특징이라, 원본 SigLIP2와 우리 백본 특징(공짜)을 오프라인에서 맞대는 E-NOV0(5절)를 제안한다. 상태 판정기(손목 잡음 판정)는 V1h(균형 정확도 0.949 [실측])가 이미 있어 이득이 작고, 위치 찾기는 SAM 3.1이 이미 CLIP 계열(PE) 백본을 쓴다.

---

## 1. 사실 확인: 우리 백본의 영상 탑과 같은 계열 모델들

### 1.1 우리 영상 탑 (확인 방법 포함)
| 항목 | 값 | 근거 |
|---|---|---|
| Qwen3-VL-4B 영상 인코더 | **SigLIP2-Large(300M) 구조, 공식 가중치에서 시작해 동적 해상도로 이어 학습** | [원문] Qwen3-VL 기술 보고서 arXiv 2511.21631 v2(2025-11-26, Comments "42 pages", 학회 표기 없음, Semantic Scholar 인용 2,313) HTML 본문 |
| 파드 설정 `vision_config` | depth 24, hidden 1024, intermediate 4096, heads 16, patch 16, act `gelu_pytorch_tanh`, `spatial_merge_size` 2, `temporal_patch_size` 2, `deepstack_visual_indexes` [5, 11, 17], `out_hidden_size` 2560 | [실측] `kubectl exec … cat /data/harvest/models/Qwen3-VL-4B-Instruct/config.json`(읽기만, 2026-09-26 01:5x UTC); 같은 값이 HF `Qwen/Qwen3-VL-4B-Instruct/config.json`에도 있음 |
| SigLIP2-L/16 영상 설정 | hidden 1024, intermediate 4096, layers 24, heads 16 | [원문] HF `google/siglip2-large-patch16-256/config.json` |
| 전처리 | 평균·표준편차 0.5(SigLIP 관례) | [실측] 파드 `preprocessor_config.json` |
| 우리 학습에서 | **동결**(LoRA = `language_model.layers.*` q/k/v/o·gate/up/down만) | [실측] `harvest/train/stagea_train.py` L41 `LORA_TARGET`, `stageb_train.backbone_trainable` L189–193 |
| 영상 토큰 수 | 머리 672×376 → 252, 손목 424×240 → 104(병합 뒤 토큰 = 32 px 칸) | 정본 §59 [실측]; 병합 전 패치는 머리 약 42×24 = 1,008, 손목 약 26×16 = 416 [추정: 32 px 배수로 맞춘 크기 ÷ 16] |

- 따라서 사용자의 "SigLIP을 우리 VLA에" 요청의 가장 싼 해석은 이미 충족돼 있다. 남는 질문은 "**원본 SigLIP2가 주는 무엇이 우리 탑에 없나**"이다: (i) 더 큰 So400m(400M), (ii) 이어 학습으로 흐려졌을 수 있는 원래 영상-문장 정렬(영점 분류·검색에 필요 — VLA 안에서는 거의 쓰이지 않음), (iii) 병합하지 않은 16 px 패치 해상도(이것은 **우리 탑도 병합 전 단계에서 이미 계산한다** — 4.3절 (e0)).

### 1.2 SigLIP 2와 같은 계열의 최근 인코더 (1.5년·신뢰도)
| 모델 | 날짜 | 학회·반응 | 코드·가중치 라이선스 | 우리에게 의미 |
|---|---|---|---|---|
| **SigLIP 2**(Tschannen 외, Google DeepMind), arXiv 2502.14786 | 2025-02-20 — **1.5년 경계 밖 약 1개월**(모델 자체는 사용 허가, 날짜 표기) | 학회 표기 없음(arXiv Comments 없음), Semantic Scholar 인용 1,286; `google-research/big_vision` 3,541★ | 코드 Apache-2.0, HF `google/siglip2-so400m-patch14-384` 모델 카드 **apache-2.0**(월 내려받기 약 107만) | [원문] ImageNet 영점: B/16@256 79.1, L/16@256 82.5, So400m/14@384 84.1(SigLIP 1: 76.2·80.5·83.2); RefCOCO val(L/16) 67.33 → **86.04**; 열린 어휘 검출 COCO AP(So/14) 44.3 → 45.2. 크기 B 86M · L 303M · So400m 400M · g 1B. **NaFlex** = 원래 가로세로비로 가변 길이 입력(FlexiViT + NaViT) |
| **Perception Encoder**(PE, Meta), arXiv 2504.13181 | 2025-04-17 | **NeurIPS 2025**(Semantic Scholar venue), 인용 343; `facebookresearch/perception_models` 2,375★ | Apache-2.0(저장소) | [원문] PE-Core 영점 ImageNet 강건성 평균 86.6, PE-Spatial COCO 66.0 box mAP. **SAM 3의 백본이 PE**(SAM 3 원문 "aligned Perception Encoder (PE) backbone") — 우리 J4 위치 찾기(SAM 3.1)는 이미 이 계열을 쓴다 |
| MetaCLIP 2, arXiv 2507.22062 | 2025-07-29 | arXiv Comments "10 pages"만(학회 미확인), 저장소 1,853★ | 저장소 라이선스 NOASSERTION(미확인) | 근거·후보에서 뺌(라이선스·학회 미확인) |
| DINOv3, arXiv 2508.10104 | 2025-08-13 | 학회 미확인, 11,445★ | 저장소 NOASSERTION(자체 라이선스로 알려짐 — 이번에 원문 확인 안 함) | 영상-문장 정렬이 아니어서 "같은 계열"은 아님. 임베딩 비교군 후보로만 언급 |

### 1.3 SigLIP 계열을 쓰는 최근 로봇 정책 (통합 방식 비교)
| 정책 | 영상 인코더 | expert·행동 머리가 영상을 보는 방식 | 근거 |
|---|---|---|---|
| π0(PI), arXiv 2410.24164 | PaliGemma(SigLIP So400m 계열 + Gemma) | 행동 토큰이 블록 인과 주의로 VLM 토큰 전체를 봄 — **별도 영상 흐름 없음** | "We use PaliGemma …", "blockwise causal attention mask with 3 blocks" [원문]; RSS 2025(arXiv Comments), 인용 2,783 — 2024-10이라 **기간 밖, 기초 문헌** |
| π0.5, arXiv 2504.16054 | 같은 계열 | 같음(+ KI) | 인용 1,925; 학회 표기 없음 |
| π\*0.6(RECAP), arXiv 2511.14759 | Gemma 3 4B(= SigLIP 400M, Gemma 3 보고서 2503.19786 원문 "We use a 400M variant of the SigLIP encoder", 896×896 → 256 벡터) | 같음; **조건 표시(Advantage)를 학습 때 무작위로 빼고 실행 때 CFG(β > 1)** | [원문] §V-B; 기술 보고서(학회 미확인), 대형 연구실 |
| GR00T N1(NVIDIA), arXiv 2503.14734 | Eagle-2 VLM의 **SigLIP-2**, 224×224 → 프레임당 64토큰 | DiT가 LLM **12층** 표현을 교차 주의 — 별도 영상 흐름 없음("faster inference speed and higher downstream policy success rate") | [원문] HTML; 인용 1,354, `NVIDIA/Isaac-GR00T` 8,129★ Apache-2.0 |
| SmolVLA(HF), arXiv 2506.01844 | SmolVLM-2의 SigLIP, 프레임당 64토큰, VLM 층 절반만 | expert가 VLM 특징을 봄 — 별도 흐름 없음 | [원문]; 인용 550, `huggingface/lerobot` 27,781★ Apache-2.0 |
| MolmoAct / Molmo2-ER | SigLIP2(So400m급) + Qwen2.5-7B / Qwen3-4B | 저장소 연구 문서 `molmoact_deepdive_2026-09-26.md` §1·§3(Molmo2-ER은 파드 `/data/harvest/models/Molmo2-ER`에 있음) | MolmoAct ICRA 2026(연구 문서 확인) |
| OpenVLA-OFT, arXiv 2502.19645 | SigLIP + DINOv2(OpenVLA 융합 탑) | 언어가 **FiLM으로 두 영상 탑의 각 블록 특징을 변조** — ALOHA에서 "policies can struggle with language following due to spurious correlations in visual inputs", FiLM 없으면 언어 따르기 **33 %(무작위 선택과 같음)** | [원문]; **RSS 2025**(arXiv Comments); 2025-02(경계 약 1개월 밖, 표기) |
| X-VLA, arXiv 2510.10274 | 주 시점 = Florence VLM, **손목 등 보조 시점 = 공유 영상 탑만 거쳐 정책 트랜스포머로 직접** | 우리 (c)·(e)와 가장 가까운 구조. "Encoding pipeline" 추가 시 검증 오차 −0.018·Simpler-WidowX 적응 +16.7 pt — 단 **이 선택만 따로 뗀 절제 아님** | [원문]; 기술 보고서(학회 없음), `2toinf/X-VLA` 733★ Apache-2.0 — **신뢰도 중간, 보조 근거로만** |

- 읽을 점: 주류(π0·π0.5·GR00T N1·SmolVLA)는 **expert에 별도 영상 흐름을 주지 않고** VLM이 처리한 표현(한 층 또는 층별 KV)만 준다 — 우리 §58 구조와 같다. 별도 흐름의 근거는 X-VLA(보조 시점, 절제 불충분) 정도다. 반대로 **조건(언어·결정)이 영상에 밀리는 문제**는 OFT·KI·π\*0.6이 반복해서 보고하고, 처방은 FiLM(OFT)·기울기 차단(KI)·조건 드롭아웃 + CFG(π\*0.6)다.

---

## 2. 우리 쪽 전제 (저장소 실측)
- decide FULL p95 **85–96 ms**(E-MA2 96.0/95.8/91.0 ms, E-CAM3 84.6 → 94.6 ms), 설계 예산 약 0.3 s(§59 문턱 0.33 s) [실측].
- 청크 경로: `StageBFused.chunk_raw` = 캐시 문맥(≤ 0.7 s) 또는 새 문맥 순전파 + expert 10 Euler 단계 CUDA 그래프(`fused_action.GraphedSampler`, 문맥을 `T_max` 1024로 채워 고정 모양); expert 즉시 실행 p95 38–45 ms(R4) [실측].
- expert 조건(`stageb_expert.ActionExpert.encode`): 문맥 = 백본 **마지막 층 은닉 상태 전체**(영상 356 + 글 약 130토큰 → 약 486토큰, E-MA2) → `ctx_norm` + `ctx_proj`(2560 → 768), 조건 토큰 = 고유감각 1 + 스킬 1 + 단계 1 + 결정 5, KI stop(문맥 detach). E-MA3(층별 KV) −2.19 % [1.48, 2.88](문턱 5 % 미달) [실측].
- **E-SR0 WEAK** [실측, `sr0.md`]: 방향 퍼짐 중앙값 S-E2E 1.1 mm(청크 15.6 mm), R2 9.3 mm(10.8 mm); R2 참 결정 기준선 0.921이나 반사실은 0.431; `phase_id` close/open은 0.949 따름; S-E2E expert는 참 결정에서도 기록 행동 방향을 0.41–0.47만 맞힘(2,000스텝 ≈ 0.43 에폭). E-MA2 C1: 결정층 0.97 준수, 청크 0.28(90°)·0.09(180°).
- E-CAM3: 결정 입력 손목 둘(시각 토큰 +104)은 +0.0014 [−0.0041, +0.0069], FULL p95 +11.7 % → 불채택 [실측]. 즉 **결정층에 손목 영상을 더 주는 것은 이미 이득이 없었다.** (c)·(e)는 결정층이 아니라 **expert에만** 주는 안이라 이 결과와 겹치지 않는다(decide 경로 지연 불변).
- 손목 원본 해상도: 시뮬 R2 424×240, S-E2E RB1·RB2 424×240(RB1은 세로 저장 → 회전) [실측, `se2e_data.md`]. **어느 학습 데이터에도 424×240보다 큰 손목 영상이 없다**(실물 D405는 더 크게 찍을 수 있으나 학습 데이터가 없음). 그래서 (e)의 "고해상도"는 새 화소가 아니라 **토큰 밀도**(병합 없는 16 px 패치, 또는 NaFlex 확대)다.

---

## 3. "VLA 안의 SigLIP" 선택지 평가 (a)–(e)

| 선택지 | 무엇 | 근거 | 비용 | 지연 | 위험 | 판정 |
|---|---|---|---|---|---|---|
| **(a)** Qwen3-VL 영상 탑을 원본 SigLIP2(So400m)로 교체 | 탑 교체 + 병합기·DeepStack 병합기 재정렬 + 미세조정 | 없음. Qwen은 SigLIP2-L을 **이어 학습**해 LLM과 맞춰 둠(1.1) — 원본으로 바꾸면 그 정렬을 버린다. 병합기 재정렬은 VLM 사전 학습 규모(영상-문장 수백만 쌍) | 매우 큼(VLM 재정렬 + 단계 A·B 전부 다시) | So400m은 L보다 약 1.3배 무거움 → decide +수 ms [추정] | 퇴행 가능성 높음, 정본 §58·§59·보정·카나리 전부 새 판 | **비권고** |
| **(b)** 백본을 SigLIP 계열 VLM으로(PaliGemma 2 = π0 계열, Molmo2-ER = MolmoAct2 계열) | 전면 재기준선 | PaliGemma 2(2412.03555, 2024-12 기간 밖; SigLIP **1** So400m + Gemma 2, Gemma 이용 약관 — 세부 미확인). Molmo2-ER(Apache-2.0, SigLIP2 + **Qwen3-4B**, 폭 2560이라 expert `ctx_dim` 그대로): 체화 추론 13종 평균 63.8 대 Qwen3-VL-4B 59.0이나 RoboSpatial-Point 32.0 대 **62.3**·Where2Place 54.0 대 **63.0**로 Qwen이 앞서는 칸도 있음(연구 문서 `molmoact_deepdive` §3 — 거기서도 비권고) | 매우 큼(직렬화기·프롬프트·서빙·단계 A·B·보정·카나리 새 판) | Molmo식 다중 크롭은 영상 토큰이 많아질 수 있음 — 미측정 | Qwen3-VL-4B 자체가 이미 SigLIP2 탑이라 "SigLIP을 쓰기 위한" 교체는 이유가 안 됨 | **비권고**(H1 일반화 실험에서 백본 요인을 볼 때만 별도 등록) |
| **(c)** 별도 SigLIP2 흐름이 **expert를 직접** 조건 | 원본 SigLIP2(동결) 특징을 expert 문맥에 추가 토큰으로 | 주류는 쓰지 않음(1.3); X-VLA 보조 시점(절제 불충분). **조건 약화 위험 근거**: OFT·KI·E-SR0 | 작음–중간: 학습 칸당 약 0.7 GPU-h(4.5절) | decide 0(경로 불변); 청크 경로 +4–9 ms(H200)·+8–20 ms(RTX PRO 6000) [추정, 4.4절] | **E-SR0 WEAK에서 결정 무시를 키울 수 있음**; 우리 탑과 같은 계열(L vs So400m)이라 새 정보가 적을 수 있음 | **조건부**(4.6) |
| **(d)** SigLIP2 특징 위 작은 결정 헤드(빠른 결정 경로) | 백본 없이 조이스틱 결정 | 없음. 지연 필요 없음(FULL p95 85–96 ms ≪ 0.3 s). 결정 라벨은 상태 글(S1 좌표·움직임 줄)에 크게 기대는데(E3-lite·labels_v2) 이 헤드는 글을 못 봄 | 작음 | −70 ms 이상 [추정] | §58(런타임 한 모델) 위반, 정확도 하락 거의 확실 | **비권고**(필요하면 "LLM 없는 결정" 절제 기준선 행으로만) |
| **(e)** 손목 영상만 **촘촘한 토큰**으로 expert에 | 손목 16 px 패치(병합 없음)를 expert 문맥에 추가. 두 판: **(e0) 우리 탑의 병합 전 패치**(새 가중치·새 순전파 0), **(e1) 원본 SigLIP2 So400m/16 NaFlex** | 파지·접촉의 cm 이하 정렬은 손목에서 보인다(§57·설계 §12 근거); X-VLA 보조 시점 구조; 주류 VLA는 토큰을 64–256으로 **줄이는** 쪽(GR00T N1·SmolVLA 64) — 촘촘함의 이득은 증명 안 됨 | (e0) 학습 칸당 약 0.7 GPU-h, 추론 추가 계산 거의 0; (e1) 칸당 약 0.75 GPU-h | decide 0; 청크 (e0) +1–3 ms, (e1) +3–7 ms(H200) [추정] | (c)와 같은 조건 약화 위험(영상 토큰 +416은 결정 토큰 5개 대비 큰 몫); 424×240 원본이라 새 화소 없음 | **조건부, (c)보다 먼저**(4.6) |

- 공통 이유 — (c)·(e)는 **결정층을 건드리지 않으므로** E-CAM3(decide 지연 +11.7 %)의 문제를 피한다. 추가 토큰은 expert의 교차 주의 키로만 들어간다. 대신 E-SR0가 보인 "expert는 영상으로 궤적을 정한다"는 경향과 정면으로 부딪친다(4.2).

---

## 4. (c)·(e) 상세 — 통합 지점, 크기·지연, 학습 비용, E-MA2/E-SR0와의 관계, 사전 등록 초안

### 4.1 통합 지점 (읽기만 함, 수정 없음)
기준 파일(`stageb_model.py`·`stageb_expert.py`·`prefix_share`·`stageb_data.py` — `PROMPT_FILES_B` 해시 대상, 함정 P24)은 건드리지 않고 **E-MA3의 `harvest/train/se2e_kvcond.py`와 같은 옵션 파일 방식**으로 넣는다(새 파일 `harvest/train/se2e_sigstream.py` 가칭, `--expert-vis sig@v1|vitpatch@v1`).

학습 쪽(`harvest/train/stageb_model.py`, `stageb_expert.py`):
- `StageB.context()`(L96–100)·`contexts()`(L102–110)·`forward_shared()`(L112–124): 지금은 `out.hidden_states[self.layer][0]`(마지막 층)만 문맥으로 쓴다. 하위 클래스 `StageBSig`가 같은 호출에서 추가 흐름을 만든다.
  - (e0): 백본 순전파 중 `…visual.blocks[23]`(또는 DeepStack 탭 층 17) 출력에 **순전파 훅**을 걸어 병합 전 패치 특징 [N_patch, 1024]을 잡고, 처리기 출력 `image_grid_thw`로 **활성 손목 이미지의 패치 구간만** 잘라낸다(§59 순서: 머리 → 손목). E-MA3가 `self_attn.k_norm`·`v_proj`에 훅을 건 방식과 같다. 영상 탑은 동결이라 detach만 하면 KI stop과 같은 경계.
  - (e1)·(c): 별도 동결 모듈 `SiglipVisionModel`(HF, `google/siglip2-so400m-patch16-naflex` 또는 `-patch14-384`, bf16, `/data/harvest/models/`에 내려받음) — 입력은 `s["context"]["images"]`의 같은 JPEG(손목만 또는 머리 + 손목). RB1 손목은 로더가 이미 회전해 둔 파일을 쓴다(`se2e_data`).
- `StageB.cond()`(L136–146): `c["ctx"]`·`c["ctx_mask"]` 옆에 새 키 `c["vis"]`·`c["vis_mask"]`를 넣는다(기존 키의 뜻을 바꾸지 않음 — 기존 체크포인트 적재와 `GraphedSampler` 모양 검사가 안전).
- `ActionExpert.encode()`(`stageb_expert.py` L120–127): 하위 클래스 `ActionExpertVis`가 `vis`를 `LayerNorm + Linear(d_vis → 768)`(d_vis = 1024(e0)·1152(So400m)) + **흐름 종류 임베딩**으로 투영해 `ctx` 뒤에 이어 붙이고 `pad`도 잇는다. 블록(`Block.forward`)은 그대로 — 교차 주의 키가 늘 뿐. 새 파라미터 약 0.8–0.9 M(투영) + 종류 임베딩.
- 체크포인트: `heads.pt`에 `expert.vis_*`, `stageb.json`에 `"expert_vis": {"ver", "src", "layer", "cams", "pool"}`; 기본 `load_heads`는 이런 체크포인트를 엄격 적재로 거부 → `load_heads_vis`(E-MA3 `load_heads_kv`와 같은 모양).
- 결정 쪽 경로(`forward_shared`의 질문 로그확률)는 무변경 → decide 정확도 변화는 학습 잡음뿐이어야 한다(관문으로 확인).

실행 쪽(`harvest/runtime/fused_model.py`, `fused_action.py`):
- `StageBFused.__init__`(L110–138): (e1)·(c)면 SigLIP 모듈 적재(+0.8 GB bf16); `GraphedSampler(self.m.expert, T_max, steps)`(L138)의 고정 모양에 `vis` 길이 상한 `V_max`를 더한다 — `fused_action.pad_cond`(L30–40)가 지금 `ctx`·`ctx_mask`만 채우므로 `vis`·`vis_mask`도 채우게 새 옵션 판에서 확장(그래프 재포착 필요).
- `StageBFused._context()`(L244–255): 문맥 캐시 `(t_state, h, mask)`에 **같은 프레임의 추가 흐름**을 함께 넣는다 — (e0)는 이 순전파의 훅에서 공짜로, (e1)·(c)는 여기서 SigLIP 한 번(같은 `jpegs`). 캐시 나이 규칙(≤ 0.7 s)을 그대로 공유하므로 청크마다 SigLIP을 다시 돌리지 않는다.
- `StageBFused.chunk_raw()`(L257–287): `cond = self.m.cond([s], h, mask, …)`에 `vis`를 넘김; 메타에 `t_vis_s` 추가. `decide_raw()`(L210–242)는 무변경 — **decide p95는 원리상 그대로**(단 (e1)·(c)의 SigLIP을 decide와 같은 GPU 흐름에 두면 겹칠 때 줄 서기 지연이 생길 수 있음 → 관문에서 FULL p95로 확인).

### 4.2 E-MA2/E-SR0와의 관계 — 영상을 expert에 더 주면 결정 준수가 더 약해지나
- **위험 쪽 근거(강함)**: (1) E-SR0: S-E2E 방향 퍼짐 1.1 mm — 결정 토큰이 청크를 거의 못 움직인다; R2는 청크를 바꾸되 강제 방향이 아니라 학습 분포 쪽으로 보낸다. (2) OFT(RSS 2025): 다시점 영상의 가짜 상관 때문에 FiLM 없이는 언어 따르기 33 %. (3) KI(NeurIPS 2025, Semantic Scholar venue, 인용 152) 그림 4(b)(그림에서 읽은 근사값): π0 언어 따르기 약 20 % 대 π0-FAST 약 80 %·KI 약 90%, 원인 서술 "gradients from randomly initialized robotics specific adapters unfavorably interact with the pre-trained VLM weights". → expert가 이미 영상·고유감각만으로 궤적을 맞히는데, **손목 패치 416–1,008토큰**을 더 주면(결정 토큰 5개 대비) 그 지름길이 더 쉬워진다. 우리 학습 데이터에서 결정과 영상이 늘 같은 쪽을 가리키는 한(E-MA2 P75), 추가 영상은 결정 조건을 대체하는 쪽으로 쓰일 것이 합리적 예상이다.
- **완화 쪽 가능성(약함, 가설)**: 손목 영상이 촘촘하면 "지금 손끝이 물체와 얼마나 떨어졌나"가 더 분명해져 **크기(mag)** 조건과 영상이 역할을 나눌 수 있다(E-SR0 R2 크기 ρ 0.27 — 크기 토큰을 거의 안 씀). 근거 없음.
- **처방(신뢰할 만한 최근 근거)** — 영상을 더하든 안 하든 결정 조건을 세게 유지하는 방법:
  1. **결정 드롭아웃 + CFG**: π\*0.6(PI, 2511.14759) "During training, we randomly omit the indicator … enables … classifier-free guidance (CFG), which enables inference with β>1" [원문]. 우리 적용: 학습 때 확정 결정 5토큰을 확률 p로 "없음"으로, 실행 때 v = v_없음 + w·(v_결정 − v_없음). 비용 = expert 순전파 2배(청크 경로만). `sr0.md` 5절 권고 1과 같다(E-SR1b).
  2. **FiLM 조건**: OFT는 언어로 영상 탑 블록 특징을 변조. 우리 판: **결정 토큰으로 추가 영상 흐름을 FiLM 변조**(γ, β = MLP(결정 임베딩)) — 영상 흐름 자체를 결정 의존으로 만들어, 영상을 더해도 결정을 우회하기 어렵게 한다. (c)·(e)와 자연스럽게 합쳐지는 유일한 처방이지만, "결정으로 영상을 변조"한 로봇 선례는 확인하지 못했다([가정]).
  3. **데이터로 결정과 궤적을 떼기**: MolmoAct 조종 데이터(같은 목표로 다른 경로) — `sr0.md` 권고 2. 이것이 근본 처방이고 1·2는 모델 쪽 보강이다.
- 결론: **(c)·(e)는 준수율 비열등을 하드 규칙으로 걸어야** 하고, E-SR0 WEAK인 지금은 E-SR1b(처방 1)가 먼저다.

### 4.3 두 선택지의 구체 형태
| 판 | 흐름 원천 | 카메라 | 추가 토큰(expert 문맥) | 새 가중치 | 가설 |
|---|---|---|---|---|---|
| **(e0) vitpatch@v1** | 우리 Qwen ViT(SigLIP2-L 계열, 동결) 병합 전 패치, 층 23(마지막) — 판정 밖 비교로 층 17(DeepStack 탭) | 활성 손목 | 약 416 × 1024-d | 투영 약 0.8 M | 병합(32 px)과 LLM 통과로 잃은 손목 세부를 expert가 직접 본다 |
| **(e1) sig-wrist@v1** | 원본 SigLIP2 So400m/16 NaFlex(동결), 최대 패치 1,024(손목 424×240을 가로세로비 유지해 약 1.6배 확대 → 약 42×24) | 활성 손목 | 약 1,008 × 1152-d(판정 밖으로 2×2 평균 풀링 252 판) | SigLIP 약 400M(동결) + 투영 약 0.9 M | 더 크고 원래 정렬을 가진 인코더가 (e0)보다 낫다 |
| **(c) sig-dual@v1** | 원본 SigLIP2 So400m/16 NaFlex(동결) | 머리 + 활성 손목 | 우리 탑과 같은 격자로 맞추려 2×2 풀링: 머리 약 240 + 손목 약 104 = 약 344 | 같음 | "두 번째 인코더" 자체의 효과(토큰 수는 기존 영상 토큰과 비슷하게) |
- (e0)가 (e1)보다 먼저인 이유: 같은 계열 탑의 같은 화소라 **새 모델·새 지연 없이** "촘촘한 손목을 expert에 준다"는 가설만 순수하게 본다. (e0)가 실패하면 (e1)의 추가 이득(크기·원래 정렬)은 작을 가능성이 크다.

### 4.4 크기·메모리·지연 (배치 1, bf16)
| 판 | 추가 파라미터(동결 + 학습) | 추가 메모리 | 추가 계산(순전파) | H200 청크 경로 추가 | RTX PRO 6000 추가 | decide FULL p95 영향 |
|---|---|---|---|---|---|---|
| (e0) | 0 + 약 0.8 M | 무시할 만함(훅 버퍼 수 MB) | ≈ 0(ViT는 이미 돔); 투영 416×1024×768 ≈ 0.7 GFLOP | **+1–3 ms**(투영·교차 주의 키 +416, 그래프 재포착 뒤) [추정] | +2–5 ms [추정] | 0(같은 순전파; 캐시 공유) |
| (e1) | 400M + 0.9 M | 약 0.8 GB 가중치 | 2 × 0.4e9 × 1,008 ≈ 0.81 TFLOP + 주의 약 0.13 TFLOP ≈ **0.94 TFLOP** | **+4–8 ms**(MFU 25–40 % → 2.4–3.8 ms 계산 + 27층 즉시 실행 부담 2–3 ms; 그래프면 3–4 ms) [추정] | **+8–20 ms**(bf16 처리량을 H200의 약 0.4–0.5배로 가정 — 사양표 미확인) [추정] | 0(청크 경로) — 같은 GPU에서 decide와 겹치면 줄 서기 가능 |
| (c) | 400M + 0.9 M | 약 0.8 GB | 머리 966 + 손목 1,008 패치 ≈ **1.9 TFLOP** | **+6–12 ms** [추정] | +12–30 ms [추정] | 0(청크 경로) |
- 기준과 비교: decide p95 85–96 ms·예산 약 300 ms — 어느 판도 decide 예산을 위협하지 않는다(청크 경로에 두는 한). 청크 경로는 새 문맥 순전파 약 80–90 ms + expert(즉시 38–45 ms, 그래프는 더 짧음)라 (e1)·(c)는 청크 경로 +5–15 %[추정]. 실측은 사전 등록 관문 G-LAT(학습 전, 무작위 초기 투영으로 50스냅샷)에서 한다.
- expert 교차 주의 키 길이: 지금 약 486 → (e0) 약 900, (e1) 약 1,500, (c) 약 830. 계산량은 작지만 `T_max` 1024 고정 그래프는 (e1)에서 넘친다 → `vis`를 별도 키·별도 상한으로 둔다(4.1).

### 4.5 학습 비용
- 기준 틀: E-MA3·E-TC 칸 = 2,000스텝, H200 1장 약 36–41분(E-TC 칸당 2,119–2,450 s, E-MA2 학습 루프 2,306–2,360 s) [실측].
- (e0): 추가 계산 거의 0 → **칸당 약 0.7 GPU-h**. (e1)·(c): 동결 SigLIP 순전파가 스텝당 백본 순전파·역전파(4B × 약 840토큰 × 배치) 대비 약 3–6 % [추정] → 칸당 약 0.7–0.75 GPU-h. 특징을 미리 계산해 두는 안은 S-E2E 39,283행 × 1,008 × 1152 × 2 B ≈ 91 GB라 하지 않는다(온라인 계산).
- **S-E2E `se2e_c1`**(기준 = `motion_s1`·`motion_s2` 재사용, 예측 비트 동일 확인 방식 E-MA3와 같음): 새 칸 2개(시드 1·2) ≈ 1.4–1.5 GPU-h + 준수율 평가(`tools/sr0/sr0_eval.py`, 판당 약 6분) 0.2 + 지연 0.1 → **약 1.7–1.8 GPU-h**.
- **R2**(기준 = E-MA2 `c0`, 시드 하나): 새 칸 1개 ≈ 0.7 GPU-h + `ma2eval` 평가 약 10분 + `sr0_eval` 약 4분 → 약 0.9 GPU-h. 시드 2개로 판정하려면 기준 시드 2(`c0_s2`)도 필요 → **약 2.5 GPU-h**.
- (e0)·(e1)을 같은 등록에서 함께 보면 S-E2E 약 3.3 GPU-h, R2(2시드) 약 4 GPU-h. 유료 API 0.

### 4.6 E-SR0 결과별 권고 — 무엇을 먼저
| E-SR0 판정 | 권고 순서 | 이유 |
|---|---|---|
| **OK**(FOLLOWS 또는 PARTIAL) | ① **E-SG-E**(4.7) S-E2E에서 (e0) → 통과하거나 경계면 (e1) 추가 칸 ② (e)가 통과하면 **E-SG-C**(4.8) ③ 둘 다 실패면 SigLIP-VLA 축 닫음 | 결정 조건이 이미 작동하므로 영상 추가의 조건 약화 위험이 관리 가능; (e0)는 비용 0에 가까워 먼저 |
| **WEAK**(실제 결과, `sr0.md`) | ① **E-SR1b를 R2에서 먼저**(결정 드롭아웃 + CFG; `sr0.md` 5절) — 이 문서 범위 밖 ② E-SR1b가 채택되면 그 레시피 위에서 **E-SG-E를 R2로**((e0) 한 칸, 2시드), **준수율 하드 비열등** ③ S-E2E는 expert 자체가 참 방향을 절반도 못 맞혀(0.41–0.47) 조건 효과를 가리기 어렵다 — R2 뒤에 확인용으로만 ④ (c)는 ②가 통과한 뒤에만 | 조건이 약할 때 영상을 더하면 "청크 오차는 줄고 조종은 더 안 되는" 결과가 나올 가능성이 크다 — 그것은 결합 설계(§11 편향이 결정을 거쳐 행동을 바꾼다는 전제)에 해롭다. 준수율을 먼저 올리고, 영상 추가가 그것을 깎지 않는지 본다 |
- 추가 선택지(WEAK에서 E-SR1b와 합칠 수 있음): **FiLM 판 (e0-film)** — 결정 토큰으로 손목 패치를 변조(4.2 처방 2). E-SR1b 등록에 한 칸으로 넣을지는 E-SR1b 설계자가 정한다(여기서는 후보로만).

### 4.7 사전 등록 초안 A — **E-SG-E: 촘촘한 손목 영상 흐름을 expert에** (실행하지 않음)
0. **자체 검사(user-log 87, CLAUDE.md)**
   - **이 결과로 바뀌는 결정**: 단계 B 레시피의 expert 문맥에 손목 흐름을 넣는가(넣으면 런타임 `StageBFused`에 `vis` 경로·그래프 재포착·(e1)이면 SigLIP 모듈 탑재; 안 넣으면 SigLIP-in-VLA 축을 닫고 연구 문서에 "우리 탑이 이미 SigLIP2"로 정리).
   - **표본으로 가를 수 있나**: 주 지표(청크 MSE 상대 감소)의 두 시드 합동 구간 반폭은 E-MA3에서 약 ±0.7 %p(2.19 % [1.48, 2.88]) [실측] → 문턱 5 %는 참값이 5 ± 1 % 안이 아니면 가른다. 준수율 A_xy는 스냅샷 군집 표준오차 ≤ 0.012(S-E2E)·≤ 0.014(R2)(`prereg_sr0.md` 0절), 짝 차이는 더 작다 → 비열등 여유 0.03은 가를 수 있다. 접촉 층(그리퍼 사건 ±0.5 s) 표본은 전체의 약 15 %로 가정하면(미측정) 약 270개 → 구간 반폭 약 ±2–3 %p [추정] → 이 층은 **판정 밖 보고**로만.
   - **싼 사전 실행 먼저**: (1) 훅 단위 시험 — `image_grid_thw`로 자른 손목 패치 수 = 기대(416) 그리고 머리 패치와 겹치지 않음(CPU 작은 모델 `tiny_qwen`); (2) **G-LAT**: 무작위 초기 투영으로 50스냅샷 decide/청크 p95(H200, 약 5분); (3) 12스냅샷·50스텝 학습 끝까지(NaN·적재·재적재 차 0); (4) 기준 재사용 비트 동일(E-MA3 방식).
1. **질문**: expert가 백본 마지막 층 문맥에 더해 **활성 손목의 16 px 패치 특징**을 직접 보면 청크 오차가 줄어드는가, 그리고 결정 준수율을 깎지 않는가?
2. **조건**: `none`(기준 재사용: S-E2E `motion_s1`·`motion_s2` / R2 `c0`) 대 `vitpatch@v1`(e0). 선택 칸 `sig-wrist@v1`(e1)은 (e0)가 문턱 절반(2.5 %) 이상일 때만 같은 등록 안에서 추가(규칙 고정). 모든 칸 움직임 줄(§83) 켬, KI stop, 같은 스케줄·시드·데이터 순서. WEAK 경로에서는 기준·새 칸 모두 **E-SR1b 채택 레시피**(드롭아웃 p·CFG w 고정) 위에서.
3. **데이터·평가**: S-E2E `se2e_c1` 검증 1,799(키 sha `f03062db4b1d`), R2 E-MA2 평가 1,200(sha `61b2bce64ee1`).
4. **지표**: 주 = 청크 정규화 MSE(`sample_mse_norm`, 확정 결정 조건) 두 시드 합동 상대 감소(스냅샷 부트스트랩 10,000, 시드 0); 보조 = 결정 정확도(질문 평균), **청크 수준 준수율 A_xy·A_z·크기 ρ**(`tools/sr0/sr0_eval.py`·`sr0_verdict.py` 그대로 — E-MA2의 "청크 cos > 0.5" 정의를 E-SR0가 반사실 결정 전체로 넓힌 것), FULL decide p95, 청크 경로 p95(새 문맥·캐시 문맥 따로), 판정 밖 = 접촉 층 MSE, 원천별(RB1·RB2), MSE_flip 상대 차.
5. **채택 규칙(고정, E-TC·E-MA3 틀)** — 모두 만족해야 채택:
   1. 청크 MSE 합동 상대 감소 **≥ 5 %** 그리고 95 % 하한 **> 0**;
   2. 결정 정확도 차 **≥ −0.01**(비열등);
   3. **준수율 비열등**: 데이터마다 A_xy 차(새 − 기준) **≥ −0.03**, A_z 차 ≥ −0.03(WEAK 경로에서는 추가로 새 칸 A_xy ≥ E-SR1b 채택 문턱(user-log 91: 0.8) — E-SR1b 등록 값을 그대로 가져옴);
   4. FULL decide p95 증가 **≤ 10 %**, 청크 경로 p95 증가 **≤ 20 %**.
   - 1만 실패하고 2–4 통과 → 불채택, "가능성"으로만 기록(E-MA3와 같음). 3 실패 → **다른 값과 관계없이 불채택**(청크 오차를 줄여도 조종성을 깎으면 결합 설계에 해로움).
6. **관문(도중 결함이면 멈추고 재설계·등록 변경 커밋 뒤 재개)**: G0 데이터 수·키 sha; G1 기준 재사용 비트 동일; G-LAT(청크 경로 p95 +20 % 넘으면 학습 전에 멈추고 2×2 풀링 판으로 재등록); G2 NaN·발산; G3 시간 2배(칸당 90분).
7. **GPU 예산**: S-E2E (e0) 약 1.8 GPU-h(+ (e1) 선택 칸 약 1.6); R2 2시드 약 2.5 GPU-h. GPU는 메인 세션이 배정(user-log 91로 x2 파드 GPU 0·1이 E-SR1b 계산용 — 그 뒤 순서; 남의 프로세스 불가침은 그대로). 유료 0.
8. **하지 않는 것**: 결정층 입력 변경(E-CAM3로 닫힘), 영상 탑 학습(동결 유지), 데이터 재렌더링(손목 424×240 그대로).

### 4.8 사전 등록 초안 B — **E-SG-C: 두 번째 인코더(원본 SigLIP2) 흐름을 expert에** (실행하지 않음)
0. **자체 검사**: 바뀌는 결정 = 런타임에 400M 동결 인코더를 추가하는가(메모리 +0.8 GB, 청크 경로 +6–12 ms[추정]). 표본 판별력은 A와 같다. 싼 사전 실행: (1) SigLIP2 전처리 확인 — 20장에 영점 문장 쌍("a robot gripper holding an object" / "an empty robot gripper")의 점수 방향이 사람 판단과 대체로 맞는지(맞지 않으면 회전·색 순서 버그 의심; 판정 아님), (2) G-LAT, (3) 12스냅샷 스모크.
1. **질문**: 토큰 수를 기존 영상 토큰과 비슷하게(2×2 풀링, 약 344) 맞춘 **원본 SigLIP2 So400m 흐름**이, 우리 탑 표현만 볼 때보다 청크 오차를 줄이는가 — "더 큰·원래 정렬의 두 번째 인코더" 효과.
2. **조건**: `none` 대 `sig-dual@v1`. 판정 밖 한 칸(여력 있을 때): `sig-dual-film@v1`(결정 토큰 FiLM 변조, 4.2 처방 2).
3. **지표·채택 규칙**: A의 4·5와 같다(주 5 %·하한 > 0, 결정 −0.01, **준수율 A_xy·A_z 차 ≥ −0.03 하드**, decide p95 ≤ 10 %, 청크 p95 ≤ 20 %). 추가 조건: **E-SG-E (e0)를 먼저 채택했다면** 비교 기준은 `none`이 아니라 (e0) 칸(= 두 번째 인코더의 **추가** 이득).
4. **선행 조건**: E-SG-E가 채택(또는 경계, 주 지표 ≥ 2.5 %)일 때만 등록. 그렇지 않으면 등록하지 않는다(자체 검사: 같은 계열 탑의 더 큰 판이 촘촘한 같은 화소보다 클 근거가 없음).
5. **GPU 예산**: S-E2E 2칸 약 1.8 GPU-h, R2 2시드 약 2.5 GPU-h.

---

## 5. 부차 역할 (VLA 밖) — 순위와 가장 값진 하나의 초안

### 5.1 순위 (기대 이득 × 비용 × 위험, 각 1–5점, 곱이 클수록 앞; 비용·위험은 낮을수록 높은 점수)
| 순위 | 역할 | 이득 | 비용 | 위험 | 곱 | 근거 요지 |
|---|---|---|---|---|---|---|
| 1 | **새 환경·이상 감지 → Astra 호출 트리거(T_nov 보강, H1 대응)** | 4 | 5 | 4 | 80 | SAFE(NeurIPS 2025, 인용 84) 표 1 [원문]: VLA 내부 마지막 층 특징에 **코사인 k-NN** ROC-AUC 평균 본 과제 81.28·새 과제 73.93, Mahalanobis 80.28·67.45 대 SAFE-LSTM 82.26·77.04, SAFE-MLP 81.43·78.00, 토큰 확률 55.79·61.64. FIPER(NeurIPS 2025) [원문]: 정책 자신의 관측 임베딩 RND 단독 균형 정확도 0.67 대 행동 불확실성과 AND 결합 0.78. FAIL-Detect(RSS 2025): 성공 데이터만으로 순차 OOD + conformal. **세 근거 모두 정책 자신의 특징** — 원본 SigLIP2의 우위는 증명 안 됨 → E-NOV0로 맞댐 |
| 2 | **(e0) 촘촘한 손목 흐름**(4장) | 3 | 5 | 2 | 30 | 4장. E-SR0 WEAK라 E-SR1b 뒤 |
| 3 | 세계 쪽 상태 판정(잡음·놓임·넘어짐·손목에 물체 보임) | 2 | 4 | 3 | 24 | V1h 세계 술어 0.949·헤드 지연 0.44 ms, T1 ≥ 0.99 [실측] — 분포 안에서는 이미 충분. Astra 손목 판정은 실제 쥠 13/25 놓침 [실측]. SigLIP의 몫은 (i) V1h와 **독립된** 채널(같은 백본·같은 특권 라벨에 묶이지 않음), (ii) 시뮬 특권 라벨 없는 실물 데이터. 근거: AutoEval(arXiv 2503.24278, 학회 표기 없음) — PaliGemma(SigLIP 계열 VLM)를 약 1,000장으로 QLoRA 미세조정한 성공 판정기, 배치 전 정확도 > 95 % 요구 [원문]. **SigLIP 임베딩 선형 탐침으로 잡음 여부를 가른 1.5년 내 신뢰 근거는 못 찾음** |
| 4 | 편 단위 성공·실패 라벨·데이터 거르기(R2 병 넘어짐 등) | 2 | 4 | 3 | 24 | 시뮬 R2는 특권 상태로 이미 실패 유형을 앎(병 놓기 실패 794 중 전도 384 [실측]) → 시뮬에는 불필요. 실물(S-E2E·향후 수집)에만 의미 — 그때 AutoEval식 소량 라벨 판정기 |
| 5 | (c) 두 번째 인코더 흐름 | 2 | 4 | 2 | 16 | 4장 |
| 6 | J6 경험 검색(비슷한 과거 상황) | 2 | 4 | 2 | 16 | falsify 먼저 평가는 **서명 완전 일치**만 재사용(정본 §84 보충 1) → 임베딩 유사도는 재사용 판단에 못 씀; J6 오프라인에서 Astra 프롬프트에 비슷한 교훈 상위 k개를 붙이는 보조로만. 검색 VLA 선례 RA-VLA(arXiv 2608.25585, Comments "ICML 2026", 임베딩 종류·스타 미확인)는 확인이 부족해 근거로 쓰지 않음 |
| 7 | 문장 기반 위치 찾기(J4) | 1 | 3 | 3 | 9 | SAM 3(인용 1,012, `facebookresearch/sam3` 11,794★)가 이미 PE(CLIP 계열) 백본; SigLIP2 열린 어휘 검출 AP 45.2 [원문] — SAM 3.1을 대신할 이유 없음. 검출 프롬프트 문구가 성패를 가른다(정본 §47 근거 E3-ST: "box" 0/20 대 "basket" 19/20)는 문제는 SigLIP으로 **문구 후보 순위 매기기**(영상-문장 점수) 정도로만 도울 수 있음 |
| — | (a)·(b)·(d) | — | — | — | — | 3절: 비권고 |

### 5.2 사전 등록 초안 C — **E-NOV0: 임베딩 이동으로 새 환경·실패를 미리 아는가** (학습 없음, 실행하지 않음)
0. **자체 검사**
   - **바뀌는 결정**: (1) Astra 트리거 T_nov(`docs/research/astra_role_2026-09-25.md` 표의 AND 조건 목록)에 "임베딩 이동" 채널을 더하는가, (2) 더한다면 원본 SigLIP2(새 모델 0.8 GB·+3–5 ms)인가 **우리 백본 특징(추가 계산 0)**인가, (3) 흐름 호출(직렬 1개, 로봇 1분당 350–500원 [실측])을 "장면이 직전 답 이후 바뀌지 않았으면 쉬기"로 줄일 수 있는가(비용 한도 10만 원 대비).
   - **표본**: R2_TRAIN eval 분할 249편(실패 편 포함) + DEV random5·dr 장면(§34 — random은 시험 전용). 편 단위 AUROC는 실패 편 수에 좌우된다 — 등록 전 eval 분할의 실패 편 수를 세어 20편 미만이면 편 단위 대신 스냅샷 단위(편 군집 부트스트랩)로 바꾼다(규칙 고정).
   - **싼 사전 실행**: 100스냅샷으로 세 임베딩 추출 끝까지(형태·결정성), 자기 자신 k-NN 거리 0 확인.
1. **질문**: 결정 스냅샷 임베딩의 학습 분포 거리(코사인 k-NN, k = 10; Mahalanobis는 판정 밖)가 (i) 환경 이동(standard 대 random5·dr)과 (ii) 편 실패를 미리 가르는가? 어느 임베딩이 나은가?
2. **임베딩**: E1 원본 SigLIP2 So400m 영상 임베딩(머리 + 손목 평균, 풀링 출력), E2 우리 Qwen ViT 병합 전 패치 평균(공짜), E3 백본 마지막 층 은닉 상태 평균(SAFE 방식, 공짜), 판정 밖 E4 V1h `unknown` 비율.
3. **적합**: R2_TRAIN fit 분할 표준·dr 결정 스냅샷에서 무작위 20,000개(시드 0)를 기억 집합으로; 문턱 τ = fit 보류 분할 점수의 95 분위(split conformal, 정본 §79와 같은 방식).
4. **지표**: 이동 AUROC(standard eval 대 random5), 실패 AUROC(편 점수 = 편 안 최댓값의 앞 50 % 구간 — 실패 전에 알 수 있어야 하므로), τ에서 standard 거짓 경보율, 경보 시점(실패 전 몇 s).
5. **채택 규칙(고정)**: 채널 추가 = 어느 임베딩이든 이동 AUROC ≥ 0.80 **그리고** 실패 AUROC ≥ 0.70(하한 > 0.5) **그리고** τ 거짓 경보율 ≤ 0.07. 임베딩 선택 = E1이 E2·E3 중 최고보다 AUROC 합(이동 + 실패) **+0.05 이상**이면 E1(SigLIP2), 아니면 공짜인 E2/E3 중 최고. 미달이면 채널 추가 안 함(T_nov 현행 유지).
6. **비용**: 임베딩 추출 약 5만 장 × E1(장당 수 ms) ≈ GPU 0.2 h 이하 [추정], E2·E3는 백본 순전파라 약 0.3 GPU-h [추정]. 유료 0. GPU 배정은 메인 세션.
7. **하지 않는 것**: 폐루프 트리거 실험(E-Couple에서), 학습형 탐지기(SAFE식 — 이 결과가 경계면 다음 판).

---

## 6. 기존 부품과의 관계 (보완·대체)
- **V1h·T1**: 대체하지 않는다. SigLIP 상태 판정기는 V1h와 독립된 두 번째 세계 쪽 채널 후보일 뿐이고, 분포 안 정확도로는 V1h(0.949)를 넘을 이유가 없다. 실물·새 환경에서 V1h가 떨어지는지(H1)를 먼저 E-NOV0·E-H2 계열로 본다.
- **Astra**: SigLIP은 Astra 판단을 대신하지 않는다(J1–J6는 추론 과제). 대신 **언제 부를지**(E-NOV0)와 **흐름 호출을 쉴지**를 싸게 정하는 데 쓴다 — 비용 한도에 직접 도움.
- **SAM 3.1(J4)**: 유지. 같은 계열(PE) 백본이 이미 들어 있다.
- **융합 VLA(§58)**: "런타임 한 모델" 원칙과 (e0)는 충돌하지 않는다(같은 모델의 탑 특징). (e1)·(c)는 모델 안에 동결 인코더를 하나 더 두는 것이라 원칙상 허용 범위(한 프로세스·한 호출)지만 "두 인코더"라는 점을 논문에 명시해야 한다.
- **결합 구현(계획 2026-09-26)**: E-SR0 WEAK에 따라 §11 편향은 결정 토큰이 아니라 청크·손끝 기준에 직접 적용 중(`sr0.md` 3절). (c)·(e)는 이 적용 방식을 바꾸지 않는다. 다만 (c)·(e)가 채택되면 `fused_model.chunk_raw`의 입력이 늘어 결합 구현의 청크 호출 지연 상수(있다면)를 다시 재야 한다.

## 7. E-SR0·결합 구현과 맞물리는 곳 (명시)
1. E-SR0 WEAK → (c)·(e)는 E-SR1b 뒤, 준수율 하드 비열등(4.6·4.7 규칙 3).
2. (c)·(e)의 준수율 평가는 **E-SR0 도구를 그대로**(`tools/sr0/sr0_eval.py` A_xy·A_z·ρ) — 새 지표를 만들지 않는다(비교 가능성).
3. E-SR1b 설계자에게: FiLM 판(결정 → 손목 흐름 변조)을 E-SR1b의 한 칸으로 넣을지 검토 요청(4.2 처방 2, 선례 미확인 표시).
4. 결합 구현의 청크 경로(`StageBFused`): (c)·(e) 채택 전까지 무변경. 채택 시 `vis` 키·`pad_cond` 확장·그래프 재포착·캐시 공유(4.1).

## 8. 위험 목록
- **조건 약화**(가장 큼): 4.2. 규칙 3으로 막는다.
- **지름길 과적합과 H1**: 촘촘한 손목 특징은 장면 외관(질감·색)에 더 민감할 수 있다 → 채택하더라도 random5·dr 이동에서 청크 MSE 낙폭을 판정 밖으로 보고(E-H2 계열과 연결).
- **데이터 해상도 한계**: 손목 424×240이 상한 — (e1)의 확대는 새 정보를 만들지 않는다. 실물에서 D405를 더 크게 찍으려면 학습 데이터부터 다시(범위 밖).
- **RB1 라이선스**: S-E2E RB1은 내부 학습 시험만(§63 (6)) — 결과 수치는 논문 근거로 쓰지 않음(§56).
- **지연 추정치**: 4.4의 모든 ms 값은 추정 — G-LAT 실측 전에는 설계값으로 쓰지 않는다.
- **SigLIP2 날짜**: 2025-02-20로 1.5년 경계 밖 약 1개월 — 모델 사용은 허가 범위, 논문 인용 시 "기간 경계, 우리 백본의 영상 탑 출처"로 표기.

## 9. 출처 (직접 열람, 2026-09-26)
- Qwen3-VL 기술 보고서 arXiv 2511.21631 v2 HTML(영상 인코더·DeepStack 원문), HF `Qwen/Qwen3-VL-4B-Instruct/config.json`, 파드 `/data/harvest/models/Qwen3-VL-4B-Instruct/{config,preprocessor_config}.json`(읽기만).
- SigLIP 2 arXiv 2502.14786(초록·HTML 표 1·RefCOCO·검출), HF `google/siglip2-so400m-patch14-384` 모델 카드(apache-2.0), HF `google/siglip2-large-patch16-256/config.json`; `google-research/big_vision` 3,541★ Apache-2.0.
- Perception Encoder arXiv 2504.13181(Semantic Scholar: NeurIPS 2025, 인용 343), `facebookresearch/perception_models` 2,375★ Apache-2.0; SAM 3 arXiv 2511.16719 v2 HTML("aligned Perception Encoder (PE) backbone"), `facebookresearch/sam3` 11,794★.
- π0 arXiv 2410.24164(RSS 2025, 기간 밖 기초), π0.5 arXiv 2504.16054, π\*0.6 arXiv 2511.14759 HTML(CFG·드롭아웃 원문), Gemma 3 arXiv 2503.19786 HTML(SigLIP 400M 원문), `Physical-Intelligence/openpi` 13,996★ Apache-2.0.
- GR00T N1 arXiv 2503.14734 v2 HTML(SigLIP-2, 64토큰, 12층), `NVIDIA/Isaac-GR00T` 8,129★; SmolVLA arXiv 2506.01844 HTML; `huggingface/lerobot` 27,781★.
- OpenVLA-OFT arXiv 2502.19645(RSS 2025, FiLM·33 % 원문); KI arXiv 2505.23705 HTML(Semantic Scholar: NeurIPS 2025, 인용 152; 그림 4(b) 근사값); X-VLA arXiv 2510.10274 HTML, `2toinf/X-VLA` 733★.
- SAFE arXiv 2506.09937 v2(NeurIPS 2025 camera ready) 표 1 원 칸; FIPER arXiv 2510.09459(NeurIPS 2025, RND-OE는 정책 자신의 ResNet-18 인코더); FAIL-Detect arXiv 2503.08558(RSS 2025); AutoEval arXiv 2503.24278 v2 HTML(PaliGemma QLoRA, 약 1,000장, > 95 %).
- 저장소: `docs/stage3/results/{ma2,ma3,cam3,astra_motion,se2e_temporal,se2e_motion_confirm,sr0}.md`, `docs/stage3/prereg_sr0.md`, 정본 §57–§59·§61·§64·§82–§86, 결합 설계 `docs/superpowers/specs/2026-09-26-astra-vla-coupling-design.md`, 연구 `molmoact_deepdive_2026-09-26.md`·`astra_role_2026-09-25.md`·`hypothesis_short_window_2026-09-25.md`, 코드 `harvest/train/{stageb_model,stageb_expert,stageb_train,stagea_train,se2e_kvcond}.py`, `harvest/runtime/{fused_model,fused_action}.py`(읽기만).

## 10. 한계와 확인 못 한 것
- 웹 검색 할당량 소진 — arXiv API 검색("SigLIP AND robot" 등)과 원문 직접 열람만 했다. 검색으로 나온 SigLIP 로봇 논문 다수(SemanticVLA AAAI 2026 등)는 우리 역할과 직접 관련이 약하거나 학회·반응이 확인되지 않아 뺐다. "SigLIP 임베딩으로 파지 상태를 판정"한 신뢰할 만한 최근 논문은 찾지 못했다(없다는 뜻은 아님).
- Semantic Scholar 인용 수는 요청 제한(429)으로 일부만 얻었다(OpenVLA-OFT·X-VLA·FAIL-Detect·π\*0.6은 미확인).
- RTX PRO 6000의 bf16 처리량은 사양표를 이번에 확인하지 못해 H200 대비 0.4–0.5배로 가정했다. 지연 미세 측정(파드 CPU, 허용 범위)은 GPU 수치의 대용이 못 되어 하지 않았다 — 모든 지연은 [추정]이며 G-LAT에서 실측한다.
- KI 그림 4(b) 값은 그림에서 읽은 근사값이다(요약 도구 경유 — 인용 전 원 그림 재확인 필요).
- E-SR0 결과 문서는 조사 도중 작업 트리에서 먼저 읽었고, 이후 `704d520`으로 커밋된 것을 확인했다(인용 수치 같음). user-log 91(E-SR1b 준수율 목표 0.8, x2 GPU 사용)은 작성 끝에 반영했다.
