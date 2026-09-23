# v3 초안 조사 11: 인식 앞단 — 카메라 → 텍스트(Jev) / 이미지(Astra), "2026-09 기준 정말 최고인가"

- 작성: 2026-09-24, v3 조사 에이전트(주제 11)
- 대상: `docs/plan.md` M1(상태 표현), M2(Astra → Jev 전달)의 인식 앞단 / v2 `01-state-representation.md` §2.3 / v3 `04-representation-action.md` M1 부분
- **변환 방법(카메라 → 텍스트)은 사용자가 정한다.** 이 보고서는 하위 모듈별 후보 순위와 근거만 적고 확정하지 않는다.
- 결론 한 줄: v2 앞단 후보(SAM 3/3.1, FoundationPose)는 **2026-09에도 최상위권이 맞다.** 다만 (1) 6D 자세의 BOP 정확도 1위는 FoundationPose가 아니다(BOP 2025에서 FoundationPose는 "최고 공개 소스" 상), (2) 깊이는 **Fast-FoundationStereo(CVPR 2026)**가 새로 들어와야 하고, (3) 관계 술어는 VLM이나 학습형 장면 그래프보다 **코드가 3D 기하로 계산**하는 쪽이 근거가 가장 많다. 이미지를 직접 받는 "Visual Jev"는 **공식으로 존재하지 않는다**(TypeSafe 문서: 텍스트만).

---

## 1) 조사 방법과 한계

- WebSearch 10회(한도 12회). arXiv 검색 API, Semantic Scholar API, GitHub API는 쓰지 않았다(지시). 대신 arXiv abs/html 페이지, 프로젝트·저장소 README(raw.githubusercontent), github.com 페이지의 스타 카운터, **BOP 공식 리더보드와 BOP 2025 수상 PDF**, TypeSafe 공식 문서(docs.typesafe.ai)를 직접 읽었다.
- 원문 읽은 논문·문서
  - 본문 해당 절·표까지 읽고 수치 확인: 9건(SAM 3 2511.16719, SAM 3.1 릴리스 노트, YOLOE 2503.07465, Rex-Omni 2510.12798, SAM 3D 2511.16624, Depth Anything 3 2511.10647, Fast-FoundationStereo 2512.11130, OmniSpatial 2506.03135, RelateAnything 2609.12552)
  - 공식 표·문서: BOP 리더보드 2개 표(Classic-Core 6D 로컬라이제이션, H3 6D 검출), BOP 2025 수상 PDF 2개, TypeSafe `models.md`·`concepts/state.md`, Ultralytics YOLOE 문서, OmniParser README·HF 모델 카드
  - 초록·제출일만: 약 10건(EOVSAM, VL-SAM-v3, MoGe-2, OvSGTR, 2509.01209, EASI 2508.13142, GCA 2511.22659, Any6D, DAM, FoundationStereo, VGGT, MapAnything, DINOv3, UniDepthV2)
- 스타 수는 2026-09-24 github.com 페이지 기준.
- 한계
  - **우리 GPU에서 잰 지연은 하나도 없다.** 모든 지연은 논문·업체 수치이고 GPU가 제각각(H200, H100, A100, 3090, T4)이다.
  - BOP 2025 공식 보고서(arXiv)는 찾지 못했다. 수상 PDF와 리더보드 표만 봤다.
  - Jev에서 직접 실험한 결과는 없다. "Jev에 어떻게 넣나"는 모두 추론이다.

---

## 2) 검증 표

신뢰도: HIGH / MED / LOW (README 규칙). "기간 밖" = arXiv 첫 공개 2025-03-23 이전.

### 2.1 개방어휘 검출·분할·추적

| 항목 | 확인 수준 | 정정/비고 (신뢰도 근거) | 출처 URL |
|---|---|---|---|
| **SAM 3** (Meta, 2511.16719, 2025-11-20) | ORIGINAL-CONFIRMED | ICLR 2026(v2에서 OpenReview 확인), Meta, 스타 11,771 → HIGH. 약 850M 파라미터(비전 450M + 텍스트 300M + 검출·추적 100M). **H200에서 이미지 1장(물체 100개 이상) 30 ms.** 비디오는 물체 수에 비례, **약 5개까지 준실시간**. 30 FPS 비디오를 위해 **H200 2장으로 10개, 4장 28개, 8장 64개**까지 병렬화(본문). Table 1: SA-Co/Gold cgF1 **54.1**(사람 72.8, OWLv2★ 24.6, Gemini 2.5 Flash 13.0), LVIS 마스크 AP 48.5(이전 최고 APE 53.0은 LVIS 일부 학습★ 표시), 본문 "LVIS 제로샷 마스크 AP 48.8 대 38.5". | https://arxiv.org/html/2511.16719v2 , https://github.com/facebookresearch/sam3 |
| **SAM 3.1** (2026-03-27) | ORIGINAL-CONFIRMED | 릴리스 노트: Object Multiplex(물체를 고정 용량 묶음으로 공동 처리). **H100 1장, 물체 128개에서 약 7배**(SAM 3 2025-11판 대비). Meta 블로그 문장은 다른 조건: "물체 수 중간일 때 **16 → 32 FPS**(H100 1장), 한 번의 순전파로 **16개까지** 추적". 정확도는 SA-Co/VEval에서 **엇갈림**(YT-Temporal-1B +2.1 cgF1), VOS 7개 중 6개 향상. 별도 논문 없음(SAM 3 논문 부록 H). → v2의 "7배"는 맞지만 **128개라는 극단 조건**이다. 우리처럼 물체 5~15개면 블로그의 "약 2배"가 더 가까운 기대치. | https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md , https://ai.meta.com/blog/segment-anything-model-3/ |
| SAM 4 / SAM 3.2 | UNCONFIRMED(부재) | 검색어 `Meta "SAM 4" OR "SAM 3.5" OR "SAM 3.2" segment anything 2026 release`로 찾지 못했다. 2026-09 현재 Meta 최신은 SAM 3.1로 본다. | (검색) |
| **YOLOE** (THU-MIG, 2503.07465) | ORIGINAL-CONFIRMED | **2025-03-10 → 기간 밖(13일 이름).** ICCV 2025, 스타 2,295 → HIGH. Table 1: YOLOE-v8-L 텍스트 프롬프트 **T4 TensorRT 102.5 FPS**, LVIS minival AP 35.9. YOLOE-v8-S 305.8 FPS, 27.9 AP. v2에서 "수치 미확인"이던 것을 채웠다. | https://arxiv.org/html/2503.07465 |
| **YOLOE-26** (Ultralytics YOLO26 기반, 2026) | SINGLE-SOURCE(Ultralytics 문서) | 문서 표(LVIS minival 640, 텍스트/시각): YOLOE-26x **40.6 / 38.5 AP**, 26l 37.8 / 36.3, 26n 24.7. "YOLO26 paper" 인용(논문 심사 여부 미확인). FPS는 문서에서 찾지 못함 → MED. | https://docs.ultralytics.com/models/yoloe/ |
| **Rex-Omni** (IDEA, 2510.12798, 2025-10-14) | ORIGINAL-CONFIRMED | 3B MLLM이 좌표를 0~999 특수 토큰으로 출력. COCO·LVIS 제로샷에서 DINO·Grounding DINO와 비슷하거나 앞선다(초록). **A100 vLLM: 상자 0~29개 2초 미만, 400개대 16초 이상**(본문 §6.2). 스타 1,592, IDEA → MED~HIGH(학회 미확인). 저자 스스로 "기존 검출기보다 느리다". → 실시간 루프에는 부적합, Astra 쪽 보조나 오프라인 라벨용. | https://arxiv.org/html/2510.12798 |
| DINO-X Pro / Grounding DINO 1.6 Pro | SINGLE-SOURCE(검색 요약) | LVIS-minival 59.8 box AP(업체 보고). **API 전용** → 로컬 루프 부적합(v2 결론 유지). | https://arxiv.org/pdf/2411.14347 |
| EOVSAM (2608.02284), ActiveSAM (2606.16996) | ORIGINAL-CONFIRMED(초록) | SAM 3를 의미 분할(semantic)용으로 한 번에 돌리는 개량. EOVSAM은 "**최대(up to)** 338배" 가속(범주 수가 많을 때). 인스턴스 ID·추적이 아니라 **의미 분할**이고, 공개 1~3개월, 반응 미확인 → **LOW, 추천하지 않음.** | https://arxiv.org/abs/2608.02284 , https://arxiv.org/html/2606.16996v1 |
| VL-SAM-v3 (2605.03456) | ORIGINAL-CONFIRMED(초록) | 검색 기반 시각 기억으로 개방세계 검출 보강, SAM3에도 적용. 수치·반응 미확인 → LOW. | https://arxiv.org/abs/2605.03456 |

### 2.2 6D 자세 / 3D

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **BOP 2025 수상** (ICCV 2025 R6D) | ORIGINAL-CONFIRMED(수상 PDF) | Track 1(모델 기반, 처음 보는 물체 6D 로컬라이제이션, Classic-Core): **최고 정확도 = FRTPose-WAPR.v2**(Wang·Hu·Zhou·Luo), **최고 공개 소스 = FoundationPose**(NVIDIA). Track 2 최고 속도 = Co-op(NAVER LABS). Track 4(H3 6D 검출) 최고 = IPT-Pose-H3(Intrinsic), 공개 소스·속도 = GigaPose. **Track 6(모델 없는 6D 검출, H3) 최고 = gfreedet2-6d**(칭화 Xiangyang Ji 그룹). → v2의 "FoundationPose 2024-03 BOP 1위"는 과거 사실. 2025 기준으로는 **정확도 1위가 아니라 공개 소스 1위**. | https://bop.felk.cvut.cz/challenges/bop-challenge-2025/ (수상 PDF: drive 링크 1lvOBAm…) |
| BOP Classic-Core 리더보드 (처음 보는 물체 6D 로컬라이제이션) | ORIGINAL-CONFIRMED(리더보드 표) | AR_Core / 이미지당 시간(검출 포함): **WAPR.v2(Multi 2D, 2026-03) 0.845 / 50.8 s**, FRTPose-WAPR.v2(Multi 2D) 0.844 / 212.7 s, FreeZeV2.2 0.833 / 21.7 s, **Co-op(F3DT2D, 1 Hypo, RGBD) 0.759 / 0.77 s**, FRTPose-WAPR.v2(MUSE) 0.801 / 0.83 s, **FoundationPose(NVIDIA, 2024-08) 0.734 / 29.3 s**, SAM6D-FastSAM 0.662 / 1.43 s. 시간은 **이미지 한 장의 모든 물체 합**이고 제출자 하드웨어가 제각각이다. | https://bop.felk.cvut.cz/leaderboards/pose-estimation-unseen-bop23/bop-classic-core/ |
| BOP-H3 6D 검출 리더보드 | ORIGINAL-CONFIRMED(표) | AP_H3: 3PT-Pose(2025-11, RGB) 0.587 / 16.0 s, Co-op(MUSE, 1 Hypo) 0.464 / 3.4 s, GigaPose+GenFlow 0.312. 2026 제출 "SAM-FP"(RGB-D, HOPEv2 0.668만), "SAM3-FS-FP"(Classic, 일부만)가 보인다 — 이름으로 보아 SAM 3 + FoundationStereo + FoundationPose 조합으로 **추정**(문서 미확인). | https://bop.felk.cvut.cz/leaderboards/pose-detection-unseen-bop24/bop-h3/ |
| **FoundationPose** (2312.08344) | CONFIRMED-MULTI | 기간 밖, 기초 문헌. CVPR 2024 Highlight, 스타 3,589 → HIGH. 추적 약 32 Hz(3090), 5 Hz에서 크게 나빠짐(v2 확인). BOP 2025 공개 소스 최고상. | https://github.com/NVlabs/FoundationPose |
| **Any6D** (2503.18673) | SINGLE-SOURCE(날짜·학회) | **2025-03-24 → 기간 안(하루 차이).** CVPR 2025 → HIGH. RGB-D 앵커 1장으로 자세+크기. 속도는 이번에도 미확인. | https://arxiv.org/abs/2503.18673 |
| **SAM 3D Objects** (Meta, 2511.16624, 2025-11-20) | ORIGINAL-CONFIRMED | 스타 7,445, Meta → HIGH. 이미지 1장 → 모양·질감·**배치(layout: 회전·이동·크기)** 생성. Table 3(SA-3DAO / Aria Digital Twin): **SAM 3D 단독 ADD-S@0.1 0.723 / 0.767** 대 파이프라인 "SAM 3D 메시 + FoundationPose" 0.508 / 0.650, ICP 회전 오차 20.8° / 15.3°. 증류로 NFE 25 → 4, "**1초 미만** 모양·배치"(저자 주장, GPU 미기재). → **거친 초기 배치용**이지 끼우기 수준 정밀도는 아니다(회전 오차 15~20°). CAD 없는 물체의 **메시 생성 → FoundationPose 추적**에 쓸 수 있다. | https://arxiv.org/html/2511.16624 |

### 2.3 깊이

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **FoundationStereo** (2501.09898) | SINGLE-SOURCE(날짜·학회) | **2025-01-17 → 기간 밖, 기초 문헌.** CVPR 2025, 스타 2,923 → HIGH. 속도: 3090 496 ms, 4090 295 ms, A100 308 ms(아래 Fast-FS 논문 Table 5). | https://arxiv.org/abs/2501.09898 |
| **Fast-FoundationStereo** (NVIDIA, 2512.11130) | ORIGINAL-CONFIRMED | **CVPR 2026**(저장소 표기), 스타 1,497, Bowen Wen·Birchfield → HIGH. Table 5: **3090 49 ms, 4090 30 ms, A100 41 ms**, 파라미터 14.6M(FS 374.5M). "FoundationStereo보다 10배 이상 빠르고 제로샷 정확도는 **약간 낮다**"(Middlebury-Q 기준 그림 2). Jetson Orin/Thor 탑재 가능. **스테레오 카메라가 있으면 1순위.** | https://arxiv.org/html/2512.11130v2 , https://github.com/NVlabs/Fast-FoundationStereo |
| **Depth Anything 3** (ByteDance Seed, 2511.10647) | ORIGINAL-CONFIRMED | 스타 6,390 → HIGH(유명 연구실+반응, 학회 미확인). 임의 개수 시점 → 깊이+광선. 초록: VGGT 대비 카메라 자세 +44.3%, 기하 +25.1%(자체 벤치마크 평균). Table 8(A100, 504×336, 32장 장면의 장당 평균): **DA3-Large 78.4 FPS, Giant 37.6 FPS**, VGGT 34.1. **단안 미터 모델(DA3Metric-Large, 0.35B)은 별도**이고 속도는 확인 못 했다. 미터 변환은 `focal × 출력 / 300`(README). | https://arxiv.org/html/2511.10647 , https://github.com/ByteDance-Seed/Depth-Anything-3 |
| MoGe-2 (MSR, 2507.02546) | ORIGINAL-CONFIRMED(초록) | 단안 미터 점 지도, 스타 2,971(MoGe 저장소 공유) → MED~HIGH(학회 미확인). 속도 미확인. | https://arxiv.org/abs/2507.02546 |
| VGGT (2503.11651) | SINGLE-SOURCE | 2025-03-14 → 기간 밖. CVPR 2025. DA3가 넘었다고 보고. | https://arxiv.org/abs/2503.11651 |
| MapAnything (Meta, 2509.13414) | SINGLE-SOURCE(초록·코멘트) | 3DV 2026, 스타 3,763 → HIGH. 다시점 미터 재구성. 조작 루프용 속도 미확인. | https://arxiv.org/abs/2509.13414 |

### 2.4 이미지 → 구조화 텍스트 / 장면 그래프 / 관계 술어

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **OmniSpatial** (2506.03135) | ORIGINAL-CONFIRMED | ICLR 2026 → HIGH. 본문: o3·Gemini-2.5-Pro가 **기존 기본 공간 관계 벤치마크(왼/오, 가깝/멀, 개수)에서 90% 넘어 포화**에 가깝다. 복합 공간 추론 8.4K 문항에서는 **o3 56.33%**(1위) 대 **사람 92.63%**. 명시적 장면 그래프 단서(PointGraph)와 새 시점 CoT가 도움이 된다고 보고(향상 폭은 이번에 표에서 확인 못 함). | https://arxiv.org/html/2506.03135 |
| EASI (SenseTime 외, 2508.13142) | ORIGINAL-CONFIRMED(초록) | 8개 공간 벤치마크: GPT-5가 1위지만 사람보다 크게 낮다. 가장 어려운 과제에서는 폐쇄형 모델의 결정적 우위가 없다. 인용·학회 미확인 → MED. | https://arxiv.org/abs/2508.13142 |
| GCA: Geometrically-Constrained Agent (2511.22659) | ORIGINAL-CONFIRMED(초록) | VLM은 "의미는 잘하지만 기하는 손실이 큰 의미 공간에서 추론한다". VLM이 기준 좌표계·목표를 **형식 제약으로** 바꾸고 계산은 도구가 하게 하면 여러 공간 벤치마크 SOTA(학습 없음). 학회·반응 미확인 → LOW~MED. **개념 근거로만.** | https://arxiv.org/abs/2511.22659 |
| **RelateAnything** (2609.12552, 2026-09-11) | ORIGINAL-CONFIRMED | 53M 모델, **어떤 출처의 영역(SAM 3 마스크 등)이든 받아** 추론 시 문자열로 준 술어 어휘에 점수를 매긴다. **A40에서 20 ms/프레임.** 정답 영역 기준 표: RelateAnything 31.7 대 Qwen3-VL-32B 15.0, Qwen3-VL-8B 10.2, ROBIN-3B(3B VLM 장면 그래프) 35.1(같은 매처)·25.8(정확 일치). 공개 13일, 반응 없음 → **LOW, 추천하지 않음.** 다만 "범용 VLM에게 관계를 뽑게 하면 재현율이 낮다"는 방향 신호로 기록. | https://arxiv.org/html/2609.12552v1 |
| OvSGTR (2505.20106) | ORIGINAL-CONFIRMED(초록) | 완전 개방어휘 장면 그래프, VG150 SOTA 주장. 학회 미확인 → MED. VG150식 술어(50개)는 조작 술어와 맞지 않는다. | https://arxiv.org/abs/2505.20106 |
| **OmniParser V2** (Microsoft) | CONFIRMED-MULTI(README + HF 카드) | **기간 밖(2025-02, 논문 2408.00203), 기초 문헌·유비.** 스타 25,446 → HIGH. YOLO 상호작용 영역 검출기 + Florence-2 캡셔너 → **번호 붙은 요소 목록(상자·설명)**을 텍스트 LLM에 넘긴다. **A100 0.6 s/프레임, 4090 0.8 s.** GPT-4o와 함께 ScreenSpot-Pro 39.6(HF 카드). 2026-07 YOLOv9-E 검출기 추가. → "검출기가 ID·상자, 캡셔너가 설명, LLM은 목록만 읽는다"는 구조가 plan M1 후보 1과 같다. | https://github.com/microsoft/OmniParser , https://huggingface.co/microsoft/OmniParser-v2.0 |
| Describe Anything (DAM, NVIDIA, 2504.16072) | SINGLE-SOURCE(README) | 2025-04-22, ICCV 2025(저장소 표기), 스타 1,517 → HIGH. 마스크 영역 단위 상세 캡션. 속도 미확인. 물체 속성(재질·상태) 텍스트를 만드는 캡셔너 후보. | https://github.com/NVlabs/describe-anything |

### 2.5 "Visual Jev" / 이미지 입력 결정 모델

| 항목 | 확인 수준 | 정정/비고 | 출처 URL |
|---|---|---|---|
| **Jev 공식 입력** | ORIGINAL-CONFIRMED | `models.md`: "Input: **Text only.** … No image, audio, or video input." `concepts/state.md`: "Images, audio, and video are **not supported (yet)**." → 이미지 입력 Jev는 공식적으로 없다. "(yet)"은 계획 암시일 뿐 일정 없음. | https://docs.typesafe.ai/models.md , https://docs.typesafe.ai/concepts/state.md |
| Visual-JEV → SemIf (jiangxiluning) | ORIGINAL-CONFIRMED(README) | **TypeSafe와 무관한 개인 프로젝트**("not affiliated"). Qwen3.5-4B VLM에서 보기 확률을 읽는 방식. 2026-09-22 이미지 경로 추가. **스타 7 → LOW, 쓰지 않는다.** | https://github.com/jiangxiluning/Visual-Jev |
| OmniJev (shapsider) | SINGLE-SOURCE(awesome-jev 설명) | 자체 VLM에 두 카메라 이미지+텍스트, 다음 스킬을 한 번의 선택으로. MuJoCo 팔. **스타 11 → LOW.** | https://github.com/shapsider/OmniJev |
| jev-multimodal | SINGLE-SOURCE | 스타 0 → LOW. | https://github.com/Alpha-Harper-Franklin/jev-multimodal |
| Laya / "Laya Vision" | SINGLE-SOURCE | Laya 본체는 스타 20.1k이지만 **텍스트 결정 모델**이다. 검색 요약에 나온 "Laya Vision(SmolVLM-256M 교체 연구 포크)"은 README에서 확인하지 못했다 → UNCONFIRMED. | https://github.com/NandhaKishorM/laya |

---

## 3) 하위 모듈별 최고 후보 (확정 아님, 순위와 근거만)

전제 [사용자]: Jev는 텍스트만 받는다. Astra는 이미지를 받는다(비디오는 안 됨). 변환 방법은 사용자가 정한다.
전제(CLAUDE.md 제약): Jev는 수치 비교·산술에 약하다 → 기하는 코드가 계산하고 Jev에는 범주·술어로.

### 3.1 개방어휘 검출·분할·추적 (물체 ID의 원천)
| 순위 | 후보 | 어디서 최고였나 | 지연(조건) | 신뢰도 | Jev / Astra 접목 |
|---|---|---|---|---|---|
| 1 | **SAM 3.1** (SAM 3 체크포인트 + Multiplex) | SA-Co/Gold cgF1 54.1(다음 OWLv2★ 24.6, 약 2배), LVIS 제로샷 마스크 AP 48.8 | 이미지 30 ms(H200, 100개+). 비디오 SAM 3는 약 5개까지 준실시간, 3.1은 중간 개수에서 16 → 32 FPS(H100) | HIGH | **추적 ID가 곧 텍스트 키.** Jev에는 `obj_3: mug` 같은 ID 목록. Astra에는 같은 번호를 마스크 위에 그린 Set-of-Mark 이미지. |
| 2 | **YOLOE / YOLOE-26** | 실시간 개방어휘 중 정확도·속도 균형(YOLOE-v8-L 35.9 AP @ T4 102.5 FPS, YOLOE-26x 40.6 AP) | T4에서도 100 FPS대 | HIGH(YOLOE, 기간 밖) / MED(26) | SAM 3가 우리 GPU에서 느릴 때 검출용. ID 유지는 별도 추적기 필요(**ID 지속성은 SAM 3 쪽이 내장**). |
| 3 | Rex-Omni | MLLM 검출 중 최고, 지시 표현·점 찍기까지 | 2~16 s(A100, 상자 수 비례) | MED~HIGH | 루프 밖. Astra 계획 시점에 "이 문구가 가리키는 물체" 해소용 보조. |
| 추천 안 함 | EOVSAM, ActiveSAM, VL-SAM-v3 | 의미 분할 개량, 공개 직후 | — | LOW | — |

### 3.2 6D 자세 / 3D 형상
| 순위 | 후보 | 어디서 최고였나 | 지연 | 신뢰도 | 접목 |
|---|---|---|---|---|---|
| 1 | **FoundationPose** (초기화 1회 + 추적 루프) | BOP 2025 Track 1 **최고 공개 소스**, AR 0.734 | 추적 약 32 Hz(3090), 리더보드 29 s/이미지(전체 물체 초기 추정) | HIGH(기간 밖, 기초) | 자세가 필요한 물체만. 코드가 자세 → 범주(`upright/tilted/lying`, `aligned_with(slot)=True`)로 바꿔 Jev에. |
| 2 | Co-op (NAVER LABS) | BOP 2025 Track 2 최고 속도, AR 0.759 @ 0.77 s | 1초 미만 | MED(공개 여부·논문 이번에 미확인) | 초기화 속도가 문제일 때 비교 후보. |
| 3 | **SAM 3D Objects** | 단일 이미지 3D 배치: ADD-S@0.1 0.723 대 파이프라인 0.508(SA-3DAO) | "1초 미만"(저자, GPU 미기재) | HIGH | CAD 없는 물체의 **메시를 만들어 FoundationPose에 넘기는** 앞단. 단독 회전 오차 15~20°라 정밀 조작에는 부족. |
| 4 | Any6D | RGB-D 앵커 1장으로 자세+크기 | 미확인 | HIGH | SAM 3D 대안(모델 없는 경우). |
| 참고 | FRTPose-WAPR.v2 / WAPR.v2, 3PT/IPT-Pose(Intrinsic), gfreedet2-6d | BOP 2025 정확도 1위들 | 17~213 s/이미지 | 공개·논문 여부 미확인 | 루프용 아님. "정확도 1위 ≠ 쓸 수 있는 1위"의 근거. |

### 3.3 깊이 (3D 중심점·거리 → 관계 술어의 재료)
| 순위 | 후보 | 어디서 최고였나 | 지연 | 신뢰도 | 접목 |
|---|---|---|---|---|---|
| 1 | **Fast-FoundationStereo** (스테레오 카메라일 때) | 실시간 스테레오 중 제로샷 최고(저자) | 30 ms(4090), 49 ms(3090) | HIGH(CVPR 2026) | 마스크 × 깊이 → 3D 중심·크기 → 코드가 술어 계산. |
| 2 | FoundationStereo | 제로샷 스테레오 정확도 기준점 | 약 300~500 ms | HIGH(기간 밖) | 정확도가 필요한 순간(계획 시점)만. |
| 3 | **Depth Anything 3 (Metric)** (단안일 때) | 다시점 기하 벤치마크 SOTA(VGGT 대비) | Large 약 78 FPS(A100, 다시점 평균). 미터 모델 속도 미확인 | HIGH | 손목 카메라 등 단안. 미터 스케일 오차는 우리 데이터로 측정 필요. |
| 4 | MoGe-2 | 단안 미터 점 지도 | 미확인 | MED~HIGH | DA3 대안. |
| (RGB-D 센서가 있으면) | 센서 깊이 | — | — | — | 학습 모델보다 먼저 센서값을 쓰고, 투명·반사 물체만 스테레오 모델로 보완(추론, 미검증). |

### 3.4 관계 술어 / 구조화 텍스트 (Jev 입력의 본체)
| 순위 | 후보 | 근거 | 지연 | 신뢰도 | 접목 |
|---|---|---|---|---|---|
| 1 | **코드가 3D 기하로 술어 계산** (`on(a,b)`, `inside`, `left_of`(로봇 기준), `near`, `gripper_holding`) | OmniSpatial: 최고 VLM도 복합 공간 추론 56% 대 사람 93%. GCA: 기하는 도구에 맡겨야 한다. v2/04: 텍스트 LLM은 전역 일관성·기준 좌표계에 약함 | ms 단위 | 근거 HIGH(OmniSpatial) + MED(GCA) | ID 목록 + 참/거짓 술어 + 범주 거리. Jev가 가장 약한 수치 비교를 입력 단계에서 없앤다. |
| 2 | **OmniParser식 "검출기 + 영역 캡셔너 → 번호 목록"** (로봇판: SAM 3 ID + DAM 영역 캡션 + 1의 술어) | GUI 에이전트에서 텍스트 LLM을 에이전트로 만든 검증된 구조(스타 25k). 로봇 조작에 그대로 쓴 신뢰할 만한 선례는 이번에 찾지 못함(검색어: `OmniParser V2 latency screen parsing structured elements successor 2026 GUI agent screen parser benchmark` — 로봇 적용 결과 없음. 부재 주장은 하지 않음) | OmniParser 0.6 s(A100). 로봇판은 미측정 | HIGH(기간 밖, 유비) | 기하가 아닌 속성(`lid: open`, `material: glass`, `contents: empty`)을 텍스트로. 매 프레임이 아니라 **새 ID 등장 시 1회 + Astra 요청 시**만 캡션. |
| 3 | 학습형 관계 모델(RelateAnything 등) | 20 ms, 범용 VLM보다 관계 재현율 2배(자기 보고) | 20 ms(A40) | LOW | 기하로 못 정하는 상호작용 술어(`pouring_into`)가 필요할 때만 비교 조건. 지금은 추천 안 함. |
| 4 | 범용 VLM에게 JSON 장면 그래프를 직접 생성 | 기본 관계는 최신 추론 VLM에서 90% 이상(OmniSpatial 서술), 그러나 관계 재현율이 낮고(RelateAnything 표: Qwen3-VL-32B 15.0) 초 단위 지연. TSG-Bench(ACL 2025, v3/04): LLM은 그래프 **생성**을 못 한다 | 초 단위 | 근거 HIGH/LOW 혼재 | **Astra 계획 시점**의 보조(작업 관련 부분 그래프 선택)로만. 루프 안 Jev 입력원으로는 추천하지 않음. |

### 3.5 Astra 쪽 입력 (M2와 같은 문제)
- Astra는 이미지를 받으므로 텍스트 변환이 필수는 아니다. **같은 ID 체계를 두 쪽에 공유**하는 것이 핵심이다: SAM 3 추적 ID를 마스크 위 번호로 그린 이미지(Set-of-Mark) → Astra가 번호로 계획·완료 조건을 쓰면 Jev는 같은 번호를 텍스트 키로 읽는다(plan M2 제안과 일치).
- Astra에 텍스트 상태를 같이 줄지는 v3/05의 "변화 요약 텍스트" 비교 조건과 같이 실험한다.

---

## 4) 반대 증거와 위험

1. **"SAM 3.1이면 7배 빠르다"는 조건부다.** 7배는 128개 물체, H100 기준. 물체가 적으면 블로그 수치(16 → 32 FPS, 약 2배)가 더 맞다. 정확도는 비디오 벤치마크에서 엇갈린다.
2. **SAM 3의 30 ms는 이미지 1장, H200.** 비디오 추적은 물체 수에 비례하고, 30 FPS로 10개를 따라가려면 H200 2장이 필요했다(논문). 우리 GPU에서 재야 한다.
3. **FoundationPose는 BOP 정확도 1위가 아니다.** 2025 기준 AR 0.734로 1위(0.845)보다 11점 낮다. 1위들은 이미지당 수십~수백 초라 루프에는 못 쓴다. 공개·속도까지 따지면 여전히 가장 실용적이다.
4. **SAM 3D 배치 정밀도는 회전 15~20° 수준.** "SAM 3D로 자세까지 해결"은 틀린 기대다.
5. **기본 관계에서는 VLM이 이미 잘한다는 반대 증거**(OmniSpatial 서술: 기존 기본 관계 벤치마크 90% 이상). "VLM은 왼/오도 못 한다"는 주장은 최신 추론 모델에는 맞지 않는다. 코드 술어를 1순위로 두는 이유는 정확도만이 아니라 **지연(ms 대 초)과 결정성**이다.
6. **인식 오류가 그대로 Jev에 간다.** 텍스트 상태는 놓친 물체·잘못된 ID 교체를 숨긴다. ID 교체(추적 실패)를 코드가 감지해 `id_uncertain` 같은 플래그로 알리는 장치가 필요하다(추론).
7. **깊이 모델의 미터 스케일**은 벤치마크 밖에서 틀릴 수 있다. 술어 임계값(예: `near` 5 cm)이 스케일 오차에 민감하다.
8. "Visual Jev"라는 이름의 저장소들은 **모두 비공식, 스타 0~11**이다. 이름만 보고 "이미지 입력 Jev가 있다"고 쓰면 틀린다.

---

## 5) plan.md에 반영할 제안

- [사용자] Jev 입력은 AI 전 분야에서 이미지를 텍스트로 가장 효율적으로 바꾸는 방법을 찾아 쓴다. 변환 방법은 사용자가 정한다. (변경 없음)
- [제안] M1 "인식 앞단 후보는 v2 유지" 문장을 다음으로 갱신:
  - 검출·분할·추적: **SAM 3.1**(1순위, 추적 ID = 텍스트 키) / YOLOE(-26)(실시간 대안, **YOLOE 원 논문은 기간 밖**으로 표시).
  - 6D: **FoundationPose = BOP 2025 최고 공개 소스(정확도 1위 아님)**. CAD 없는 물체는 **SAM 3D Objects 메시 → FoundationPose** 또는 Any6D.
  - 깊이: **Fast-FoundationStereo(CVPR 2026, 4090 30 ms)** 추가. 단안이면 DA3 Metric.
  - 관계: **코드 기하 술어가 1순위**, 속성은 영역 캡셔너(DAM)로 새 ID 등장 시에만.
- [제안] M1 후보 순위 1의 선례로 **OmniParser(GUI 분야, 기간 밖 유비)**를 적는다: "검출기 ID + 캡션 + 번호 목록 → 텍스트 LLM" 구조가 GUI에서 검증됐다.
- [제안] v2 표의 SAM 3.1 "약 7배"에 조건(물체 128개, H100)과 블로그 수치(중간 개수 16 → 32 FPS)를 함께 적는다.
- [제안] "Visual Jev"는 공식적으로 없다(TypeSafe 문서, 2026-09-24 확인)를 제약 절에 추가.
- [결정 필요] 카메라 구성(스테레오 / RGB-D / 단안)에 따라 깊이 1순위가 바뀐다. 첫 실험 전에 정해야 한다.
- [결정 필요] 첫 실험 후보에 "우리 GPU에서 SAM 3.1 + Fast-FS(또는 센서 깊이) + 술어 계산의 끝-끝 지연 p50/p95"를 추가할지.

---

## 6) 확인 못 한 것

- 우리 GPU(H200 클러스터 등)에서 SAM 3.1, Fast-FoundationStereo, FoundationPose의 실제 지연.
- BOP 2025 공식 보고서(arXiv), FRTPose-WAPR·Co-op·gfreedet2-6d의 논문·공개 여부, 모델 없는 6D(Track 6) 리더보드 수치.
- 리더보드의 "SAM-FP", "SAM3-FS-FP" 제출물의 정체(이름으로만 추정).
- Any6D, MoGe-2, DAM, DA3 Metric 모델의 속도.
- OmniSpatial의 PointGraph(명시적 장면 그래프 단서) 향상 폭 수치.
- YOLOE-26의 FPS와 YOLO26 논문의 학회 여부.
- DINO-X/Grounding DINO 최신판의 로컬 가중치 공개 여부(v2에서도 미확인).
- OmniParser 구조를 로봇 조작에 그대로 쓴 신뢰할 만한 논문(찾지 못함, 부재 주장은 하지 않음).
- "Laya Vision" 포크의 실제 존재와 신뢰도.
- 인용 수(Semantic Scholar API 금지로 이번에 조회하지 않음). 신뢰도는 학회·소속·스타로만 매겼다.
