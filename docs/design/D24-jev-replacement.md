# D24 — Jev 대체 조사 (user-log 46)

작성: 2026-09-24, 조사 에이전트(D24). git 커밋 안 함.
요청 원문(user-log 46): "jev는 지금 사용이 불가능한상황임을 확인했어 애초에 텍스트 기반의 api 활성화 기반자체가 우리랑 엮기에는 약간은 부족할 수 있겠단 생각을 해서 jev를 대체할 무언가 방법을 찾아서 해볼 필요가 있을 것 같아"

읽은 것: 정본 `00-interfaces.md` §1–§9·§27·§28·§31·§35·§41–§43, `M3` §4, `M4` §0–§4, `M6` §1·§4.1, `E-first` §0–§2A, `CLAUDE.md`, `docs/stage3/results/{sol_luna_probe,scene_bringup}.md`, 코드 `harvest/sim/{planner,labeler}.py`·`harvest/clients/jev.py`.
표기: **[원문]** = 출처에서 확인한 것, **[우리 접목]** = 우리 설계 제안, **[우리 계산]**/**[추정]** = 측정 안 한 값, **[결정 필요]** = 사용자·메인 결정.
한계: 이 세션의 웹 검색 한도(200회)가 조사 중간에 소진돼, Gemini 3 계열 logprob 지원과 Orin 위 VLM 지연의 1차 수치는 확인하지 못했다(§2·§6에 [미확인]으로 적음).

---

## 0. 결론 한 줄

**Jev 자리에 "로컬 오픈 VLM을 typed 선택기로 쓰는 것"(가칭 Jev-L)을 1순위로 넣는다.** H200에서 vLLM으로 Qwen3-VL-8B-Instruct를 돌리고, 보기마다 로그 확률을 읽어 보기 확률로 쓴다(이미지 입력 가능, 호출당 수십 ms [추정], 배치 불변 모드로 결정적). **2순위는 하이브리드**: Jev-L이 3 Hz 결정을 맡고, GPT-6 Luna(effort none, top_logprobs, 이미지 입력)는 저빈도 윗단(감시 질문·보류가 반복될 때 올려 묻기·기준선)만 맡는다. Luna를 3 Hz 루프에 직접 넣지 않는 이유는 메인 실측 지연이 한국에서 1–3 s여서다. M4 확정 규칙·평가 설계는 그대로 두고 "호출 대상"만 바뀐다. 따라서 새로움 주장(M4 + 평가)과 겹치는 선행은 새로 생기지 않는다.

---

## 1. Jev가 맡던 역할 (정본 요약)

| 항목 | 정본 내용 | 출처 |
|---|---|---|
| 위치 | Astra(GPT-6 Astra, 느림, 이미지, 세션 계약) → **Jev ~3 Hz 계단식 겹침** → M4 원장·확정기(코드) → 스크립트 스킬 S(100 Hz) + 구간 제한 잔차 R → M5 스무딩 | M4 §1, 정본 §35 |
| 하는 일 | "앞으로, 뒤로 좌우 몇 센티"(user-log 36): 방향·크기 구간의 **권위**. D-줌: `dir_xy` 10개(8방향 + `none_xy` + `NONE_ESCALATE`), `dir_z` 4개, `mag_coarse` 5구간 + `mag_fine` 5–9등분, `grip` {open, close, keep}. G/H안: 목표·접근·단계·미세 방향 | M3 §4.2–4.4 |
| 한 호출 | `JevCall` = 결정 질문 H개(H ∈ {1, 3}) + 감시 질문(M7 진행 범주, 필요 시 M8 T3b). 질문들은 state를 공유 | 정본 §2, E §1.2 |
| 박자 | T_c = 0.33 s마다 호출, 여러 호출이 겹쳐 떠 있음(`N_max = ceil(d_p95/T_c)+1`), **로봇은 멈추지 않음**. 고정 구간 = 실측 `d_p95` | 정본 §5·§7, M4 §4.3 |
| 필요한 출력 | 질문별 `chosen`·`p_chosen`·`p_second`(보기 확률). E1 전에는 확률 게이트 끔(최빈만). E1 뒤 θ 게이트 또는 J5 conformal 집합 | 정본 §6·§31, M4 §4.1 |
| 일관성 규약 | `question_id@vN`, 상태 직렬화 바이트 고정(J2), **합의 표는 시간차 상태에서만**(J3), 확률 비교는 같은 질문끼리만(J4), 매일 카나리 | 정본 §28 |
| 보기 이름 | R1–R6: 2지선다는 중립 ID, 3지선다 이상은 뜻 있는 이름 + 설명, `NONE_ESCALATE` 마지막, `option_key`로 셈 | 정본 §27 |
| Jev 고유 제약 | **텍스트 입력만**(카메라는 M1 후보 A 텍스트로 변환), 수치 약함, 가격 $0.042/1M 입력, 1,200 req/min, 모델 ID `jev-1.13.0` 고정 | CLAUDE.md, E §1.1 |
| 새로움과의 관계 | 새로움은 **M4(시간차 겹침 typed 호출 사이 합의 + 실행 뒤 예상 대 측정으로 전제 무효화)와 평가**에만. Astra+Jev 계층은 이미 공개 담론(JEV-Star 2609.27331) | CLAUDE.md, M4 §0 |

→ 대체물이 지켜야 할 요건(우리 정리):
- R-a **보기 확률**을 돌려준다(M4 `p_chosen`/`p_second`, E1 보정, J5 conformal).
- R-b 한 호출(결정 H개 + 감시) 지연 p95가 T_c(0.33 s)와 비슷하거나 작다. 겹침은 어느 경우에도 끄지 않으므로(정본 §9 C1) 지연이 T_c보다 훨씬 작아도 된다. 그때 겹침의 목적은 "같은 스텝 여러 표(자기 확인)"다.
- R-c 같은 입력 → 같은 출력(정본 §28). 적어도 test-retest 바닥을 잴 수 있다.
- R-d 이미지를 받을 수 있다(사용자: 텍스트만으로는 부족할 수 있다).
- R-e 실험 규모(E0류 약 20만 결정)에서 비용·호출 한도가 문제되지 않는다.
- R-f 실물(AI Worker FFW-SG2, Jetson AGX Orin 32GB)로 옮길 길이 있다.

---

## 2. 후보 표

### 2.1 계열별 요약

| 계열 | 대표 | 보기 확률(R-a) | 호출 지연(R-b) | 이미지(R-d) | 결정성(R-c) | 20만 결정 비용(R-e) | Orin(R-f) | 공수 | 새로움 영향 |
|---|---|---|---|---|---|---|---|---|---|
| **A. 호스팅 API** | GPT-6 Luna, effort none | **됨** [원문·실측]: Responses API `top_logprobs`(effort none일 때만) | **한국 실측 중앙 1.17 s, 1.04–2.91 s, 새 연결 약 2.4 s**(메인, 표본 4회) → T_c의 3배 이상 | 됨(text, image 입력) | 보장 없음(API, 정본 §28 전제) | 입력 $0.1/1M, 캐시 $0.01/1M → 2–3k 토큰 × 20만 ≈ $40–60 [우리 계산] | 네트워크만 있으면 됨(지연 동일) | 낮음 | 없음 |
|  | GPT-6 Sol, effort none | 됨, 그러나 실측 한 번에 `B 0.0`(확률 1.0 몰림) | 1.05–1.64 s(실측 4회) | 됨 | 보장 없음 | Luna보다 비쌈 | 같음 | 낮음 | 없음 |
|  | Gemini Flash 계열 | 2.x Flash는 `responseLogprobs` 보고 있음, **3 계열 [미확인]**. 포럼에 "Logprobs is not enabled for models/gemini-2.5-flash" 오류 보고도 있음 | [미확인] (미국 리전, 한국발은 A와 같은 문제로 추정) | 됨 | 보장 없음 | [미확인] | 같음 | 낮음 | 없음 |
|  | Claude(Haiku 급) | **안 됨** [원문]: OpenAI 호환 표에서 `logprobs`·`top_logprobs` "Ignored", 응답 `logprobs` "Always empty" | — | 됨 | — | — | — | — | — |
| **B. 로컬 오픈 VLM** (H200: vLLM/SGLang, Orin: TensorRT Edge-LLM) | Qwen3-VL-8B/4B/2B-Instruct | **전체 분포** — 한 번의 prefill로 보기 토큰 로그 확률을 직접 읽음(제약 디코딩 불필요) | H200: 1.5–2k 토큰 prefill **수십 ms [우리 계산, 사전 시험에서 잰다]**. 네트워크 왕복 없음 | 됨(시각 토큰 수 조절 가능) | **됨**: vLLM `VLLM_BATCH_INVARIANT=1` [원문] | GPU 수 시간 [우리 계산] | 2B/4B INT4·INT8로 가능성 있음, 지연 **[미확인]**(§2.3) | 중간(서버·템플릿·보정) | 없음(호출 대상만 바뀜) |
|  | Qwen3.5-4B/9B(네이티브 멀티모달) | 같음 | 같음 | 됨 | 같음 | 같음 | TensorRT Edge-LLM이 Qwen3.5/3.6 지원 [원문] | 중간(기본 thinking 끄기 필요) | 없음 |
|  | Gemma 4 E4B/E2B | 같음 | 같음 | 됨, **이미지당 시각 토큰 70/140/280/560/1120 선택** [원문] | 같음 | 같음 | Jetson AI Lab 모델 목록에 있음 [원문, Orin 64GB 기준] | 중간 | 없음 |
| **C. 학습한 결정 머리** | (C1) 작은 VLM LoRA 분류(오라클 라벨) / (C2) M1 술어 위 MLP | 됨(분류 확률) | B와 같거나 더 빠름 | C1 됨 / C2 없음 | 됨 | 학습 GPU 수 시간 + 라벨 생성 | C2는 쉬움, C1은 B와 같음 | 높음(데이터·학습·검증) | **위험**: 사실상 학습 정책(π0.5 상위 단·Hi Robot·HiVLA와 같은 모양). 사용자 핵심 주장("VLA는 일반화가 안 되고 LLM은 된다")과 부딪침 → 주 조건 부적합, 비교·상한 조건으로만 |
| **D. 하이브리드** | B(3 Hz) + A(저빈도 윗단) | 둘 다 됨 | 3 Hz 경로는 B의 지연 | 됨 | 3 Hz 경로는 결정적 | A 사용량만큼 | 3 Hz 경로는 B | B + α | 없음. "싼 판정기 → 비싼 모델 계단"은 Trust or Escalate와 같은 모양(정본 §31, 이미 인용) |

### 2.2 핵심 사실의 원문

- **GPT-6 Luna** [원문, developers.openai.com 모델 페이지]: 입력 "text, image", 가격 "Input: $0.1 / Cached input: $0.01 / Output: $0.5"(1M 토큰), effort "none, low, medium (default), high, xhigh, max", 기능 목록에 structured_outputs·image_input·prompt_caching. Tier 1 500 RPM. **logprob 조건** [원문, Model guidance 페이지]: "When reasoning effort is not `none`, remove `temperature`, `top_p`, and `top_logprobs`. For Chat Completions, also remove `logprobs`." / "GPT-6 Sol and Luna support `none`." / "GPT-6 Astra does not support the `none` reasoning effort." → Luna·Sol은 effort none에서만 보기 확률을 받는다(Astra 불가는 기존 정본과 같음).
- **메인 실측** (`docs/stage3/results/sol_luna_probe.md`, 2026-09-24T09:46Z, 한국 로컬 PC, Responses API, effort none, 짧은 텍스트 3지선다, `top_logprobs 5`): Luna "B, top_logprobs [B −0.275, C −1.438]", 연결 재사용 4회 1.04/1.17/1.12/2.91 s(중앙 1.17 s); Sol "B, [B 0.0]", 1.31/1.64/1.05/1.57 s; 첫 호출 약 2.4 s. 표본 4회라 설계값은 아니다. E0 판정 3의 (d) 구간.
- Artificial Analysis Luna 페이지는 "(max)" 변형만 수치를 싣는다(TTFT 106.86 s). **effort none의 TTFT는 제3자 수치가 없다** → 메인 실측이 유일한 근거.
- **Claude** [원문, platform.claude.com OpenAI SDK 호환 문서]: 요청 `logprobs`·`top_logprobs` "Ignored", 응답 `logprobs` "Always empty". → 보기 확률 요건 R-a 불충족, 후보에서 제외.
- **vLLM** [원문]: 구조화 출력 `choice`는 "the output will be exactly one of the choices"(백엔드 xgrammar/guidance). `logprobs_mode` ∈ {raw_logprobs, processed_logprobs, raw_logits, processed_logits}, "Raw means the values before applying any logit processors". **배치 불변**: "Batch invariance ensures that the output of a model is deterministic and independent of the batch size or the order of requests in a batch.", 켜는 법 `export VLLM_BATCH_INVARIANT=1`, "NVIDIA GPUs with compute capability 8.0 or higher", "may impact performance". 근거 글(Thinking Machines, Horace He, 2025-09-10): "the primary reason nearly all LLM inference endpoints are nondeterministic is that the load (and thus batch-size) nondeterministically varies!", 배치 불변 커널을 켜면 "all of our 1000 completions are identical"(끄면 80종).
- **Qwen3-VL** [원문, arXiv 2511.21631 abs, GitHub]: "dense variants (2B/4B/8B/32B) and mixture-of-experts (30B-A3B/235B-A22B)", Apache-2.0, 4B·8B 2025-10-15, 2B 2025-10-21 공개, README가 vLLM·SGLang 추론을 명시.
- **Qwen3.5 소형** [원문, Qwen 공식 X·Artificial Analysis]: 0.8B/2B/4B/9B, 2026-03, Apache 2.0, "native multimodal". Artificial Analysis: 벤치마크 동안 출력 토큰 소모가 매우 큼(추론 모드) → 우리는 **추론(thinking) 끄고 1토큰 로그 확률만 읽는다**.
- **Gemma 4** [원문, ai.google.dev 모델 카드]: E2B·E4B·12B·26B A4B·31B, Apache 2.0, "Supported budgets are 70, 140, 280, 560, and 1120 tokens per image", E2B/E4B 128K 문맥. 공개일은 카드에서 2026-07-30으로 읽혔다(요약 도구 경유, 재확인 필요).
- **TensorRT Edge-LLM** (NVIDIA 공식 저장소·문서) [원문]: Jetson용 C++ LLM/VLM 런타임. "Qwen3.5 and Qwen3.6 checkpoints are unified text+VLM models … selects the VLM path when visual inputs are provided". Orin은 "FP16, INT8, and INT4 runtime precision"만(FP8·NVFP4 불가).

### 2.3 Orin 지연 — 확인된 것과 못 한 것

- 확인된 것은 약한 근거 하나뿐이다: 2607.08029(ICML 2026 워크숍, MED-LOW)는 Jetson AGX(64GB) 위 Qwen3-VL-2B에서 출력 토큰당 약 136 ms(FP16)·212 ms(INT4), 시각 인코딩 약 160–684 ms(설정별)를 적었다(요약 도구 경유, 서빙 방식 미기재). 워크숍 논문이고 표를 직접 대조하지 못해 **설계 근거로 쓰지 않는다**.
- Jetson AI Lab 벤치 페이지·NVIDIA 포럼에는 Orin 위 VLM TTFT 수치가 없었다.
- [우리 계산, 대략] 4B 모델 prefill 1.5k 토큰 ≈ 2 × 4e9 × 1.5e3 ≈ 12 TFLOP. Orin 32GB 실효 FP16 처리량을 수십 TFLOPS의 일부로 보면 수백 ms. 여기에 시각 인코더가 더해진다. 2B + INT8/INT4 + 시각 토큰 70–140이면 0.2–0.5 s 범위일 수 있다. **Orin은 GPU 한 장이라 겹친 호출이 사실상 직렬**이다(초당 3호출이면 호출당 GPU 시간 ≤ 0.33 s가 필요). 게다가 같은 Orin에서 ZED 깊이(NEURAL)·SAM 등 M1 앞단이 돈다(정본 §37). → 실물은 **LAN의 별도 GPU 서버**(같은 vLLM 구성)를 기본, Orin 단독은 비교 조건으로 둔다 [결정 필요, §4.5].

### 2.4 문헌 표 (신뢰도 규칙: user-log 14)

| 출처 | 형태 | 날짜 | 반응·장소 | 신뢰도 | 쓰는 곳 |
|---|---|---|---|---|---|
| OpenAI 모델·가이드 문서(GPT-6 Luna/Sol) | 공식 문서 | 2026 | 업체 공식 | HIGH(사실 기재) | 후보 A 사양 |
| 메인 실측 `sol_luna_probe.md` | 우리 측정 | 2026-09-24 | 표본 4회 | 우리 자료(작은 표본) | 후보 A 지연 |
| Claude OpenAI 호환 문서 | 공식 문서 | 2026 | 업체 공식 | HIGH | Claude 제외 근거 |
| vLLM 문서(구조화 출력, logprobs_mode, 배치 불변) | 공식 문서 + 저장소 | 2026 | GitHub 92.6k★ | HIGH | 후보 B 서빙 |
| Thinking Machines "Defeating Nondeterminism in LLM Inference" | 연구 블로그 | 2025-09-10 | 업계에서 널리 인용, vLLM이 기능으로 채택 | HIGH(원리), 논문 아님 | 결정성 근거 |
| SGLang | 저장소 | — | 36.4k★ | HIGH | 대체 서버(RadixAttention 접두 캐시) |
| Qwen3-VL Technical Report | arXiv 2511.21631 | 2025-11-26 | 저장소 20k★ | HIGH | 1순위 모델 |
| Qwen3.5 소형(공식 발표·AA 기사) | 발표 | 2026-03 | 업체 공식, 기술 보고서는 확인 못 함 | MED | 비교 모델 |
| Gemma 4 모델 카드 | 공식 문서 | 2026 | 업체 공식 | HIGH(사양) | 비교 모델(시각 토큰 예산) |
| TensorRT Edge-LLM | NVIDIA 저장소·문서 | 2026 | 업체 공식 | HIGH(지원 범위) | Orin 경로 |
| π0.5 (2504.16054) | arXiv, Physical Intelligence | 2025-04-22 | openpi 널리 사용 | HIGH | 후보 C의 위치(상위 단 하위 과제 예측) |
| Hi Robot (2502.19417) | ICML 2025 | 2025-02-26 | — | HIGH, **기간 밖, 기초 문헌** | 후보 C 위치 |
| HiVLA (2604.14125) | arXiv, HKU·상하이 AI Lab 등 | 2026-04 | 학회 표기 없음 | MED | 후보 C 위치(VLM 계획기 → 행동 전문가) |
| KnowNo (2307.01928) | CoRL 2023 Oral | 2023 | — | HIGH, **기간 밖, 기초 문헌** | 보기 확률 → conformal 집합(정본 §31 그대로) |
| 2607.08029 소형 VLM 양자화·Jetson | ICML 2026 워크숍 | 2026-07-09 | 워크숍 | MED-LOW | 근거로 안 씀(참고만) |
| 2604.25235 "VLM Judges Can Rank but Cannot Score" | arXiv | 2026-04 | 학회 표기 없음 | LOW-MED | 근거로 안 씀 |
| 2604.23443, 2604.09529 등 VLM 보정 논문 | arXiv | 2026 | 학회 확인 못 함 | LOW | 근거로 안 씀 |

보정(calibration)에 관해서는 신뢰도 높은 2025–26 VLM 전용 근거를 찾지 못했다. 그래서 "지시 조정 모델의 토큰 확률은 과신할 수 있다"는 **우리 실측(Sol 1.0 몰림)과 E1 설계(온도 적합, E §3.6)로만** 다룬다.

---

## 3. 추천 상위 2개와 구체 설계

### 3.1 1순위 — Jev-L: 로컬 VLM typed 선택기 (후보 B)

**[원문] 무엇을 가져오나**: vLLM(서빙·접두 캐시·배치 불변), Qwen3-VL-8B-Instruct(모델), KnowNo식 "보기 토큰 확률 → 예측 집합"(정본 §31 J5 그대로).
**[우리 접목] 어떻게 붙이나**:

1. **모델과 서빙**
   - 시뮬(H200 파드): `Qwen/Qwen3-VL-8B-Instruct` BF16, vLLM, `VLLM_BATCH_INVARIANT=1`, 접두 캐시 켬, Isaac 렌더와 **다른 GPU 한 장**. 모델 ID는 HF 저장소 + **리비전 커밋 해시** + vLLM 판본 + 정밀도로 고정한다(`jev-1.13.0` 고정 규칙의 대응).
   - 속도 판: Qwen3-VL-4B(같은 계열, 같은 템플릿). 실물: LAN GPU 서버에서 같은 구성(기본) / Orin에서 Qwen3-VL-2B·4B 또는 Qwen3.5 INT4·INT8(TensorRT Edge-LLM, 비교 조건).
   - 파일은 파드 `/data/juhyoung_qdd/` 아래에만(가중치 캐시 포함, user-log 45).
2. **질문 형식 = 지금 `JevCall`을 그대로 옮긴다**
   - 공유 앞부분(캐시됨): 시스템 문장 + 스킬 문맥 + 보기 설명(criteria) — 바이트 고정(J2).
   - 동적 부분: M1 후보 A 상태 텍스트(오라클 또는 인식) + **이미지 1장**(머리캠 `cam_head` 672×376을 고정 해상도로, 시각 토큰 예산 고정. 접촉 근처에서 손목 영상은 실물에만 있음 — §4.5).
   - 질문마다 한 시퀀스: `[공유 앞부분][상태 + 이미지][질문 i의 instructions + 보기 목록] → "Answer:"`. 한 `JevCall`의 질문 4–6개는 **같은 접두사를 쓰는 병렬 시퀀스로 한 번에 보낸다**(접두 캐시로 이미지·상태 prefill은 한 번).
   - 출력은 생성하지 않는다(max_tokens 1). 다음 토큰 분포에서 보기 첫 토큰의 로그 확률을 읽는다.
3. **보기 확률 만드는 법**
   - 보기 표시 이름은 정본 §27 R1–R3 그대로(3지 이상은 뜻 있는 이름). 질문 빌드 때 토크나이저로 **보기마다 첫 토큰이 서로 다른지 검사**한다. 다르면 1-패스 점수, 겹치면(예: `plus_x`/`plus_y`) 보기 문자열 전체의 로그 확률 합을 접두 캐시 위에서 K개 짧은 연속으로 잰다(`prompt_logprobs`).
   - p(보기) = softmax(보기 점수) — 보기 집합 안에서 다시 정규화. `logprobs_mode = raw_logprobs`로 온도·필터 영향을 뺀다.
   - 제약 디코딩(`choice`)은 쓰지 않는다. 형식 오류가 구조적으로 0이고, 제약 디코딩의 마스크가 확률 해석을 흐리지 않게 하려는 것이다.
4. **M4로 들어가는 것 (바뀌지 않음)**: `Vote{choice = argmax, p_chosen, p_second, ...}`. E1 전에는 최빈만(정본 §6). E1에서 `question_id@vN × 모델 리비전`별로 온도 하나를 적합(E §3.6)하고, 그 보정 확률로 θ 게이트 또는 J5 conformal 집합을 만든다. Jev보다 나아지는 점: 전체 분포를 가지므로 J5 비순응 점수를 모든 보기에 대해 계산할 수 있다.
5. **결정성과 J3**: 배치 불변을 켜면 같은 입력의 test-retest flip 바닥이 0이 될 것으로 본다(E0.5 (ii)가 확인). 그러면 J3의 잡음 바닥 "2p(1−p)"가 0이 되어, **호출 사이 불일치는 전부 상태 변화에서 온다** → M4 (a) 합의와 `C_flip`의 해석이 Jev 때보다 깨끗해진다. 반대로 같은 입력 반복은 정보가 전혀 없으므로 J3 규칙(합의 표는 시간차 상태에서만)은 더 확실해진다.
6. **지연 예산** [우리 계산, 사전 시험에서 확정]: H200, 8B, 동적 부분 약 1k 텍스트 + 약 300–600 시각 토큰, 질문 5개 병렬 → 호출 약 30–100 ms 예상. 목표는 p95 ≤ 0.15 s(T_c의 절반 이하). 그러면 `N_max = ceil(d_p95/T_c)+1 = 2`, 고정 구간 `d_p95` ≈ 0.1 s. 겹침은 끄지 않고, 목적은 정본 §9 C1대로 "같은 스텝 여러 표"다. H=3이면 스텝마다 약 3표.
7. **simlat**: 정본 §42 시계 그대로. 시뮬 시각 t에 보낸 요청의 응답을 t + 실측 지연에 전달한다. 로컬 추론이 RTF 0.54 시뮬과 같은 파드에서 돌아도 지연은 실측값으로 주입되므로 공정성은 유지된다.

### 3.2 2순위 — 하이브리드: Jev-L(3 Hz) + GPT-6 Luna(저빈도 윗단) (후보 D)

- 3 Hz 결정 경로는 1순위와 같다.
- Luna(effort none, Responses API, `top_logprobs`, 이미지 입력)를 다음 세 곳에만 쓴다 [우리 접목]:
  1. **J5 올려 묻기 계단**: Jev-L의 예측 집합이 같은 결정 지점에서 2회 연속 원소 둘 이상이면(정본 §31 `T_j5`), Astra로 가기 전에 Luna에 같은 질문을 한 번 묻는다(1–3 s 동안 로봇은 직전 확정 행동 유지 + 감속, 정지 아님). Luna 집합도 모호하면 Astra. "싼 판정기 → 비싼 모델" 계단을 한 층 늘린 것이다(Trust or Escalate 모양, 이미 인용).
  2. **감시 질문**(`mon.progress`, `mon.t3b`)을 1초에 한 번 이하로.
  3. **기준선 행**: 비교 대상 범주 "Jev만"을 "빠른 선택기만"으로 바꾸고, Luna-only를 그 범주의 호스팅 판으로 둔다(지연 충실 트랙에서 1–3 s 지연이 그대로 불리하게 작용함을 보인다).
- 비용: 올려 묻기·감시만이면 20만 결정 실험에서 수천–수만 호출, 수 달러 수준 [우리 계산].
- 채택 조건은 §5 사전 시험의 판정 D2다.

### 3.3 왜 A 단독·C를 1–2순위로 두지 않나

- **A 단독(Luna를 3 Hz 루프에)**: 한국발 실측 중앙 1.17 s, 최대 2.91 s. `N_max`가 5–10이 되고 고정 구간이 1–3 s로 늘어 D-줌의 "촘촘함"이 사라진다. 결정성도 없다. 호출 한도(Tier 1 500 RPM)도 3 Hz × 병렬 실험에 빠듯하다.
- **C(학습 머리)**: 오라클 라벨로 학습하면 그것은 학습 정책(π0.5의 상위 단 하위 과제 예측, Hi Robot, HiVLA와 같은 모양)이다. 사용자 핵심 주장 "VLA는 다른 환경으로 일반화가 안 된다, LLM은 된다"와 정면으로 부딪치고, standard→random 낙폭 비교(주장 근거)를 스스로 약하게 만든다. → **C1(Jev-L과 같은 모델의 LoRA 판)은 "학습 선택기" 상한·절제 조건으로만**, C2(M1 술어 위 MLP)는 룰베이스 범주의 강한 판으로만 둔다.

---

## 4. 정본·M3·M4·E-first에서 바뀌는 것 (편집 제안, 메인이 반영)

### 4.1 CLAUDE.md "모델 사실에서 나온 설계 제약"
- "Jev(TypeSafe AI)는 텍스트 입력만 받는다" → **[사용자 user-log 46] Jev 사용 불가. 빠른 typed 선택기는 로컬 VLM(Jev-L)으로 대체, 이미지 입력 허용.**
- "Jev는 수치 정밀도·산술에 약하다", "Jev 확률 보정은 업체 주장뿐", "#2(c)", "#8"은 Jev 문서 근거이므로 **Jev-L에서는 다시 잰다**. 설계 규칙(기하는 코드, 범주화 술어로 묻기, 같은 질문끼리만 확률 비교)은 일반 원칙으로 유지한다.

### 4.2 정본
- §2 `JevCall` → 이름을 `DecCall`(빠른 typed 결정 호출)로 바꾸거나 "Jev"를 "빠른 선택기 F"로 일반화. 필드 추가: `image_refs`(카메라, 해상도, 시각 토큰 예산), `model_rev`.
- §5 `d_p95`: 출처가 "Jev 실측"에서 "F 실측(서빙 위치별: H200 / LAN 서버 / Orin)"으로.
- §7 설정 표 추가: 모델 리비전, 정밀도, `VLLM_BATCH_INVARIANT=1`, 이미지 해상도·시각 토큰 예산, 질문별 온도 T(E1 뒤), 서빙 위치.
- §9 C1: 로컬이면 지연이 T_c보다 짧을 가능성이 커서 겹침 목적은 "자기 확인"이 기본이 된다(규칙은 그대로).
- §27: R2·R3의 근거(이름 맞바꿈 flip, 중립 문자 정답률 하락)는 Jev·Type-Safe 측정이다. **E0.5 (i)를 Jev-L로 다시 돌려** 층별 규칙을 확정한다(로컬이라 비용 0, 시간만).
- §28: J1 `question_id@vN` 해시에 이미지 렌더러 판본·시각 토큰 예산·채팅 템플릿·모델 리비전을 넣는다. 매일 카나리는 로컬이면 "가중치 해시 + vLLM 판본 확인 + 고정 세트 재생(바이트 일치)"로 가벼워지고, Luna 윗단에만 확률 분포 비교형 카나리를 유지한다.
- §31 J5: 변경 없음(오히려 전체 분포로 쉬워짐).
- §35 R: 변경 없음. Jev-L이 방향·크기 구간 권위를 그대로 가진다.
- §41·§42 Inspect Robots: `OursPolicy`의 Jev 스레드 풀 → 로컬 vLLM 클라이언트. 정보 동등(§42): Jev-L이 이미지를 받으면 기준선(agent·capx)도 같은 카메라 이미지를 받는다(이미 받음).

### 4.3 M3
- D-줌 보기 구조는 그대로. 추가: 보기 표시 이름의 **첫 토큰 고유성 검사**(질문 빌드 시), 겹치면 전체 문자열 점수.
- 새 비교 조건(E-M3-1): 입력 {텍스트만(M1 A), 텍스트 + 머리캠, 텍스트 + 머리캠 + 방향 화살표 덧그림}. 덧그림은 TCP 투영점과 보기 이름을 붙인 축 화살표. 머리캠이 기울어져 있어 "+y(로봇 왼쪽)"을 영상과 잇기 어렵기 때문이다 [우리 접목, 효과 미확인].

### 4.4 M4
- 확정기 코드·결정 표·변수 전부 그대로. `STALE_MAX` 1.5 s 유지. `N_max`는 새 `d_p95`로 자동 계산.
- 차별화 문장의 "black-box typed decision calls"는 그대로 써도 된다(확정기는 선택기 내부를 쓰지 않고 typed 답과 확률만 쓴다). 영어 판에 "frozen, general-purpose (V)LM selector"를 덧붙이는 것을 제안한다.
- 새로움 충돌 점검: 로컬 VLM을 상위 결정기로 쓰는 선행(Hi Robot, π0.5, HiVLA)은 **학습된 계층 정책**이고 시간차 겹침 호출 합의 + 실행 뒤 예상 대 측정 무효화가 없다 → M4 주장과 겹치지 않는다. 이번 조사에서 새 선점 후보는 찾지 못했다(검색 한도 때문에 정식 선점 재검사는 아님).

### 4.5 E-first
- §1.1 모델·버전: `jev-1.13.0` → `Qwen/Qwen3-VL-8B-Instruct@<커밋>` + vLLM 판본 + BF16. 엔드포인트·가격·호출 한도 줄 삭제. 재시도 규칙은 로컬 서버 타임아웃으로.
- §2 E0: "한국 → Jev" 지연 → **서빙 위치별 지연**(H200 파드 같은 노드, 실물용 LAN 서버, Orin). 판정 구간 (a)–(d)는 그대로 쓴다. Luna는 윗단 후보로 한국 PC·파드 양쪽에서 같은 날 잰다. 비용 줄 $14–18 → GPU 시간.
- §2A E0.5 (ii): 배치 불변 켬/끔 두 조건으로 test-retest 바닥을 잰다(켬에서 0이 아니면 원인 조사).
- §3 E1: 모델 리비전별 보정. 조건 추가: 텍스트만 대 텍스트 + 이미지.
- §1.4: 오라클 상태 원칙 그대로. 이미지 조건에서도 결정 층 비교는 오라클 텍스트 + 렌더 영상으로 한다.
- **[결정 필요]** (1) SG2 시뮬에는 손목캠 prim이 없다(`scene_bringup.md`). 실물엔 D405 × 2가 있다. 접촉 근처 영상을 쓰려면 BG2 정의를 SG2 장착 프레임에 붙여야 하는데, 이것은 정본 §43 "기본 카메라만"과 부딪친다. 머리캠만으로 시작하고 사용자에게 묻는다. (2) 실물 추론 위치: LAN GPU 서버(권장) 대 Orin 단독 대 클러스터 H200(원격 지연·네트워크 경로 미확인).

---

## 5. 하루 안에 끝나는 사전 시험 (H200 파드, 상위 2개 결정)

**목적**: (D1) 1순위에서 어떤 로컬 모델·입력으로 갈지, (D2) Luna 윗단(2순위)을 넣을 만한 정확도 이득이 있는지를 정한다.

**자료** (기존 코드 재사용, 새 세계 없음):
- `harvest/sim/planner.py`의 `OraclePlanner` + `run_episode`로 P0–P2 섭동 에피소드 30편(시드 2000–2029, POOL 범위)을 돌리고, `decision_points(T_c = 0.33)`로 결정 시점마다 {오라클 상태 텍스트(`serialize.py`, M1 후보 A), `cam_head` 프레임 672×376, 오라클 답 `dir_xy·dir_z·mag_coarse·grip`, phase}를 저장한다. 에피소드당 약 40–60개 → **약 1,500 스냅샷**. RTF 0.54라 약 2–3시간 [추정].
- 정답: 플래너 명령 운동(`oracle_answer`). 순서형은 M4 τ = 1(이웃 방향 한 칸)을 허용한 정답률도 같이 낸다. 결과 기반 라벨(`labeler.best_set`)은 200개 부분 표본에만(짧은 롤아웃 비용).

**조건**:
- 로컬 모델 3개: Qwen3-VL-8B-Instruct, Qwen3-VL-4B-Instruct, Gemma-4-E4B-it(또는 Qwen3.5-4B, thinking 끔) — 전부 vLLM, BF16, `VLLM_BATCH_INVARIANT=1`.
- 입력 2개: 텍스트만 / 텍스트 + 머리캠(고정 해상도).
- 질문 템플릿은 E §1.2 예시를 그대로(D-줌 H = 1, `dir_xy` 10, `dir_z` 4, `mag_coarse` 6, `grip` 4).
- Luna(effort none, `top_logprobs`, 텍스트 + 이미지): 300 스냅샷 부분 표본, **메인 세션이 기존 OpenAI 키로 실행**(user-log 43 허용, 비용 약 $0.1 [우리 계산]). 이 에이전트는 유료 API를 부르지 않았다.

**지표**:
1. 질문별 top-1 정답률(엄격·τ = 1), 에피소드 군집 부트스트랩 95% 구간.
2. 보정: 에피소드 단위 반반 나눠 온도 하나 적합 → ECE, Brier, `p_chosen`의 정답 AUROC.
3. 지연: 한 `DecCall`(질문 5개 병렬) p50/p95, 동시성 1과 3, 렌더 GPU와 분리/공유 두 경우.
4. 결정성: 같은 입력 20회 반복 flip(배치 불변 켬/끔), 보기 순서 한 칸 순환 flip(정본 §27 A4).
5. 형식: 첫 토큰 충돌 비율(전체 문자열 점수로 떨어지는 비율).

**판정 (실행 전 해시로 고정, E §1.7 규칙)**:
- D1-a 지연 문턱: H200 p95 ≤ 0.15 s를 못 넘는 모델은 탈락.
- D1-b 남은 모델 중 `dir_xy` τ = 1 정답률 최고를 1순위 모델로. 차가 2%p 안이면 작은 모델(실물 이식에 유리).
- D1-c 이미지: 텍스트 + 이미지가 텍스트만보다 `dir_xy` 또는 `grip` 정답률 짝 차 95% 하한 > 0이면 이미지 기본 켬, 아니면 기본은 텍스트만이고 이미지는 E-M3-1 조건으로 남김(사용자 우려는 E-M3-1·E2a에서 다시 잼).
- D1-d 결정성: 배치 불변 켬에서 test-retest flip이 0이 아니면 원인 조사 전 E0.5 금지.
- D2 Luna 윗단: 같은 300개에서 Luna − 선택된 로컬의 `dir_xy` 정답률 차 95% 하한 > 0이고 점 추정 ≥ +5%p면 2순위(하이브리드) 채택, 아니면 Luna는 기준선 행으로만.
- 참고: 모든 로컬 모델의 `dir_xy` τ = 1 정답률이 텍스트 규칙 R0(같은 상태에서 코드 규칙)보다 5%p 이상 낮으면 E2a "마차 시험"의 방향 재검토 신호로 메인에 올린다(멈춤 아님).

**시간** [추정]: 가중치 받기 약 0.5 h(세 모델 약 40 GB, `/data` 캐시) → 스냅샷 2–3 h → 추론 1–2 h(1,500 × 3 모델 × 2 입력 × 5 질문 ≈ 4.5만 시퀀스) → 분석 1 h. 합계 약 5–7 h.

---

## 6. 위험

1. **작은 VLM의 공간 판단**: 방향 결정은 거의 기하다. 이미지로 좋아진다는 보장이 없다. 그래서 M1 텍스트(코드가 계산한 술어)를 주 입력으로 두고 이미지는 조건으로 잰다(§5 D1-c).
2. **과신한 확률**: 지시 조정 모델은 확률이 한쪽으로 몰릴 수 있다(Sol 실측 1.0). E1 온도 적합과 J5 conformal이 이를 다룬다. 보정 뒤에도 AUROC가 낮으면 게이트는 계속 끄고 최빈만 쓴다(정본 §6).
3. **Jev 기반 규칙의 이월**: §27 보기 이름 규칙과 "수치 약함" 같은 사실은 Jev 측정이다. 모델이 바뀌면 E0.5 (i)·E1을 다시 돌려야 한다(로컬이라 싸다).
4. **GPU 경합**: 같은 파드에서 Isaac 렌더(RTF 0.54)와 추론이 한 GPU를 나누면 지연이 흔들린다 → 다른 GPU에 고정하고 지연을 simlat로 주입한다.
5. **실물 이식**: Orin 지연 수치 [미확인]. Orin은 M1 앞단(ZED NEURAL 깊이 등)도 돌린다. LAN 서버가 없으면 2B·INT4·시각 토큰 70–140까지 내려야 할 수 있고, 그때 정확도가 떨어질 수 있다. 실물 트랙은 모델을 시뮬과 같게 두고 서빙 위치만 바꾸는 것을 원칙으로 한다.
6. **일반화 서사**: 로컬 8B는 Jev(호스팅 대형 모델로 추정)보다 일반화가 약할 수 있다. "LLM은 일반화된다" 주장은 Astra와 선택기 모두에 걸려 있으므로, standard→random 낙폭을 Jev-L 조건에서도 따로 보고한다. 학습 머리(C)를 주 조건으로 쓰지 않는 이유와 같다.
7. **새로움**: 호출 대상이 바뀌어도 M4 확정 규칙·평가 주장은 그대로다. 다만 "Jev"라는 이름이 논문·그림·정본 전반에 있으므로 일괄 교체 때 빨간 줄(사용자 의도) 원문은 바꾸지 않는다(CLAUDE.md 규칙). user-log 원문 속 "Jev"는 그대로 두고 설명 줄에서만 "빠른 선택기(현재 Jev-L)"로 푼다.
8. **라이선스·판본**: Qwen3-VL·Qwen3.5·Gemma 4 모두 Apache 2.0 [원문]. vLLM의 배치 불변은 판본에 따라 성능 비용이 다르다 → 판본 고정.
9. **확인 못 한 것**: Gemini 3 Flash logprob 지원, Luna effort none의 제3자 TTFT, Orin 위 Qwen3-VL/Qwen3.5 TTFT, Gemma 4 공개일 재확인, Qwen3.5 기술 보고서.

---

## 출처

- OpenAI GPT-6 Luna 모델 페이지: https://developers.openai.com/api/docs/models/gpt-6-luna
- OpenAI Model guidance(logprob·effort none): https://developers.openai.com/api/docs/guides/latest-model
- Artificial Analysis GPT-6 Luna: https://artificialanalysis.ai/models/gpt-6-luna
- Claude OpenAI SDK 호환 문서: https://platform.claude.com/docs/en/api/openai-sdk
- Gemini logprob 포럼 보고: https://discuss.ai.google.dev/t/logprobs-is-not-enabled-for-gemini-models/107989 , Vertex 블로그: https://developers.googleblog.com/unlock-gemini-reasoning-with-logprobs-on-vertex-ai/
- vLLM 구조화 출력: https://docs.vllm.ai/en/latest/features/structured_outputs/ , 배치 불변: https://docs.vllm.ai/en/latest/features/batch_invariance/ , 저장소: https://github.com/vllm-project/vllm
- Thinking Machines, Defeating Nondeterminism in LLM Inference: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- SGLang: https://github.com/sgl-project/sglang
- Qwen3-VL: https://arxiv.org/abs/2511.21631 , https://github.com/QwenLM/Qwen3-VL
- Qwen3.5 소형: https://artificialanalysis.ai/articles/qwen3-5-small-models , https://x.com/Alibaba_Qwen/status/2028460046510965160
- Gemma 4 모델 카드: https://ai.google.dev/gemma/docs/core/model_card_4
- TensorRT Edge-LLM: https://github.com/NVIDIA/TensorRT-Edge-LLM , https://nvidia.github.io/TensorRT-Edge-LLM/latest/user_guide/getting_started/supported-models.html
- Jetson AI Lab 모델 목록: https://www.jetson-ai-lab.com/models/
- π0.5: https://arxiv.org/abs/2504.16054 / Hi Robot: https://arxiv.org/abs/2502.19417 / HiVLA: https://arxiv.org/abs/2604.14125 / KnowNo: https://arxiv.org/abs/2307.01928
- (근거로 안 씀) 2607.08029: https://arxiv.org/abs/2607.08029 / 2604.25235: https://arxiv.org/abs/2604.25235
- 우리 자료: `docs/stage3/results/sol_luna_probe.md`, `docs/stage3/results/scene_bringup.md`
