# 오픈 가중치 VLM으로 Astra 단독 조종을 대신할 수 있나 — 후보 조사와 OpenAI 대리 모델 대응 (2026-09-26)

- 작성: open-VLM 조사 에이전트, 2026-09-26T10:44Z(UTC, KST 19:44). 사용자 질문(원문): "근데 이걸 아스트라가 아닌 지금 우리가 돌릴 수 있는데 대형 오픈소스llm들은 이걸 못하나? 가능한 오픈 lln찾아보고 일단 동급의 지피티 api로 불러서 평가해보기 4판만해보는걸루". 이어 사용자 정정(원문): "저거 다운해서 하라는게 아니라 일단 저중에 고르고 비슷한 성능의 openai ㅇapi 불러 테스트 하잖뜻".
- 이 문서는 **조사와 대응표**만 담는다. 오픈 모델을 직접 올리지 않는다(정정). 대리(proxy) 모델 4판 실행은 등록 `docs/stage3/prereg_open_vlm_solo.md`에서 다룬다(아래 5절: 이 문서 작성 시점에 유료 실행은 권한 대기).
- 적용 규칙: 1.5년 규칙(2025-03-26 이후 공개), 신뢰도 규칙("신뢰도 낮은 논문과 깃 저장소는 최대한 쓰지 않는다. 쓰느니만 못하다." / "신뢰도가 무조건 있어야 하고, 스타도 어느 정도 있어야 하고, 논문도 좋아요(반응)를 많이 받은 것이어야 한다.").
- 배경: 무료 사전 실행에서 Qwen3-VL-8B는 0/5(머그를 y = +0.40 작업 상자 밖으로 읽음, 같은 두 점 반복, 방해물 병 쓰러뜨림; [R/astra_solo_pilot](../stage3/results/astra_solo_pilot.md) 2절). 작은 모델로는 안 되므로 **가장 강한 오픈 VLM**을 골라야 한다.

## 1. 우리 과제에 필요한 능력
Astra-solo(`astra-solo@v2`)는 머리 영상의 격자(5 cm, `x=0.40`·`y=-0.20` 라벨)·낙하선·오른손목 영상을 보고 **절대 TCP 목표(m)**를 JSON으로 낸다. 필요한 것: (a) 격자 위 물체 바닥 위치 읽기(공간 참조·포인팅), (b) 손목 영상으로 빗나감 알아채기(구현체 추론), (c) 측정 이력으로 다음 단계 고르기(추론). 가장 가까운 공개 지표 = RefSpatialBench(공간 참조 점), EmbSpatialBench, ERQA(구현체 추론), CountBench·RefCOCO(그라운딩); 일반 지표 MMMU·RealWorldQA는 참고.

## 2. 후보 (검색어: "Qwen3.5 open weight multimodal", "best open-weight vision language model 2026 spatial grounding embodied reasoning ERQA RefSpatial", "Qwen3.6 open weights vision", "open-weight multimodal 2026 GLM-5V InternVL4 Gemma 4 Kimi K3", "RoboBrain 2.5 Cosmos-Reason2"; 읽은 날 2026-09-26)

수치는 모두 **모델 카드(Qwen 팀 측정)** 값이고 조건(추론 여부·프롬프트)은 카드에 없다. '—' = 카드에 없음.

| 모델 | 기관 · 공개 | 크기(전체/활성) | 라이선스 | HF 반응(지난달 내려받기 / 좋아요) | ERQA | EmbSpatial | RefSpatial | CountBench | RefCOCO | MMMU | 1.5년·신뢰도 판정 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-397B-A17B** | Alibaba Qwen · 2026-02 | 397B / 17B | Apache-2.0 | 257,428 / 1.56k | **67.5** | **84.5** | **73.6** | 97.2 | **92.3** | **85.0** | 통과 — 최강 후보 |
| Qwen3.5-122B-A10B | Alibaba Qwen · 2026-02 | 122B / 10B | Apache-2.0 | 375,945 / 624 (FP8판 856,896 / 117) | 62.0 | 83.9 | 69.3 | 97.0 | 91.3 | — | 통과 |
| Qwen3.8-27B | Alibaba Qwen · 2026-08 | 27B 밀집 | Apache-2.0 | 6,652,309 / — | 65.5 | — | — | — | — | — | 통과, 다만 '대형' 아님·공간 지표 미공개 |
| Qwen3-VL-235B-A22B | Alibaba Qwen · 2025-09 | 236B / 22B | Apache-2.0 | 327,368 / 419 | 52.5 | 84.3 | 69.9 | 93.7 | 91.1 | 80.6 | 통과(한 세대 전) |
| Qwen3.5-27B / 35B-A3B | Alibaba Qwen · 2026-02 | 27B / 35B-A3B | Apache-2.0 | — | 60.5 / 64.8 | 84.5 / 83.1 | 67.7 / 63.5 | 97.8 / 97.8 | 90.9 / 89.2 | — | 통과(작음) |
| Kimi K2.5 | Moonshot · 2026 | 1T / 32B | (미확인) | — | — | 77.4 | — | 94.1 | 87.8 | 84.3 | 공간 지표가 Qwen3.5보다 낮음 |
| Kimi K3 | Moonshot · 2026 여름 | 2.8T / 104B | 자체 상용 라이선스 | — | — | — | — | — | — | — | 공간 지표 미확인, 너무 큼 |
| GLM-5.3-Flash | Z.ai · 2026-08 | 320B / 약 18B | MIT | — | — | — | — | — | — | — | 공간 지표 미확인 |
| GLM-4.6V | Z.ai | 108B | MIT | 3,606 / 396 | — | — | — | — | — | — | 반응 낮음, 공간 지표 없음 → 제외 |
| InternVL3.5-241B-A28B | OpenGVLab · 2025-08 | 241B / 28B | 체크포인트별 | — | — | — | — | — | — | — | 이 조사에서 공간 수치 미확인 |
| Gemma 4 (31B·26B-A4B) | Google · 2026-04 | ≤ 31B | Apache-2.0 | — | — | — | — | — | — | — | 작음(엣지용) |
| Muse Glimmer 30B | Meta · 2026-08 | 30B | Apache-2.0 | — | — | — | — | — | — | — | 공간 지표 미확인 |
| Cosmos-Reason2 | NVIDIA · 2025-12 | 2B / 8B / 32B | NVIDIA 오픈 모델 | — | — | — | — | — | — | — | 구현체 특화지만 작음 |
| RoboBrain 2.5 | BAAI · 2026-03 | 4B 공개 확인 | — | — | — | — | — | — | — | — | 작음; Where2Place 등 특화 |
| Gemma 3 27B | Google · 2025-03-12 | 27B | Gemma | — | — | — | — | — | — | — | **1.5년 규칙 밖**(2025-03-26 전) → 제외 |

출처: HF 모델 카드 [Qwen3.5-397B-A17B](https://huggingface.co/Qwen/Qwen3.5-397B-A17B), [Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B), [Qwen3.5-122B-A10B-FP8](https://huggingface.co/Qwen/Qwen3.5-122B-A10B-FP8), [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B), [Qwen3-VL-235B-A22B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-235B-A22B-Instruct), [GLM-4.6V](https://huggingface.co/zai-org/GLM-4.6V); 목록 기사 [Turing Post](https://www.turingpost.com/p/10-open-mllms), [Fastino](https://fastino.ai/blog/best-open-weight-models-2026)(기사 자체는 신뢰도 규칙상 목록 확인용으로만 씀, 수치는 쓰지 않음); [RoboBrain 2.5 논문 페이지](https://huggingface.co/papers/2601.14352), [Cosmos-Reason2](https://huggingface.co/nvidia/Cosmos-Reason2-32B). Kimi K2.5 수치는 Qwen3.5-397B 카드의 비교 열.

한계: '—'가 많은 모델(Kimi K3·GLM-5.3·Muse Glimmer·InternVL3.5)은 **같은 지표로 비교할 수치를 못 찾았다** — 없다는 증거가 아니다(P51). Qwen 카드 수치는 Qwen 팀이 잰 값이라 자기 모델에 유리한 조건일 수 있다.

## 3. 목표 오픈 VLM 선택
- **목표 = Qwen3.5-397B-A17B.** 1.5년 안(2026-02), 신뢰도(Alibaba Qwen, 좋아요 1.56k, 지난달 25만 내려받기, Apache-2.0), 우리 과제에 가까운 공간·구현체 지표(ERQA 67.5, RefSpatial 73.6, EmbSpatial 84.5, RefCOCO 92.3)가 조사한 오픈 모델 중 가장 높다. 조정자가 예상한 Qwen3-VL-235B-A22B보다 같은 기관의 다음 세대이고 모든 공유 지표에서 같거나 높다(ERQA +15.0, RefSpatial +3.7, MMMU +4.4).
- 우리가 돌릴 수 있나: FP8 약 400 GB → **H200 4장(TP4)** 한 노드면 된다(7a2a 노드는 8장). 오늘 메인 파드의 빈 GPU는 0·1 두 장뿐이라 지금 당장은 122B-A10B(FP8 125 GB, 2장)까지만 올라간다. 공간 지표 차이는 397B 대 122B가 ERQA +5.5, RefSpatial +4.3.
- 버금: Qwen3-VL-235B-A22B(한 세대 전 기준선, 조정자 예상), Qwen3.5-122B-A10B(지금 GPU로 올릴 수 있는 최대).

## 4. OpenAI 대리 모델 대응 (같은 표에서 비교된 모델만 씀)
- 우리 키로 부를 수 있는 모델: `GET /v1/models` 136개(2026-09-26T10:40Z, `tools/open_vlm/list_models.py`, 토큰 비출력). 영상 입력 후보: gpt-5 / 5-mini / 5-nano, gpt-5.1, gpt-5.2, gpt-5.4 / -mini / -nano, gpt-5.5, gpt-5.6-luna / -sol / -terra, gpt-6-luna / -sol / -astra, gpt-4.1 계열, o3·o4-mini.
- **Qwen3.5-397B-A17B ↔ gpt-5.2**: Qwen3.5-397B 카드가 같은 표에서 GPT5.2를 직접 비교한다.

| 지표 | GPT5.2 | Qwen3.5-397B-A17B | 차(Qwen − GPT) |
|---|---|---|---|
| MMMU | 86.7 | 85.0 | −1.7 |
| MMMU-Pro | 79.5 | 79.0 | −0.5 |
| RealWorldQA | 83.3 | 83.9 | +0.6 |
| ERQA | 59.8 | 67.5 | **+7.7** |
| CountBench | 91.9 | 97.2 | +5.3 |
| EmbSpatialBench | 81.3 | 84.5 | +3.2 |
| RefSpatialBench | — | 73.6 | 비교 불가 |

  일반 영상 추론(MMMU·RealWorldQA)은 ±2 안으로 같고, **구현체·공간 지표는 Qwen이 3–8점 높다.** 따라서 gpt-5.2 대리 결과는 목표 오픈 모델의 이 과제 능력을 **약간 낮게 볼 가능성이 있는 대리값**이다.
- Qwen3-VL-235B-A22B(버금)의 대리를 고른다면 **gpt-5-mini**: Qwen3.5-122B 카드의 같은 표에서 GPT-5-mini ERQA 54.0 대 235B 52.5, EmbSpatial 80.7 대 84.3, CountBench 91.0 대 93.7(RefSpatial 9.0 대 69.9는 점 출력 형식 차로 보임 — 해석 주의).
- mini/nano 최신 계열(gpt-5.4-mini/-nano, gpt-5.6-luna, gpt-6-luna)은 **Qwen과 같은 표에서 비교한 공개 수치를 찾지 못해** 대응 근거가 없다 → 대리로 쓰지 않는다.
- **불확실성**: (1) 수치는 Qwen 팀 측정 — GPT의 추론 effort·프롬프트 조건 미상. (2) 지표는 정지 영상 질문이고 우리 과제는 격자 읽기 + 폐루프 JSON 명령이라 지표 차이가 성공률 차이로 옮겨진다는 보장이 없다. (3) 대리 결과는 **오픈 모델 자체의 결과가 아니다**; '오픈 모델이 된다/안 된다'의 결론으로 인용하지 않는다(대리는 방향만).
- 가격(공식 가격표, 읽은 날 2026-09-26, 1M 토큰당 표준): gpt-5.2 입력 $1.75 · 캐시 $0.175 · 출력 $14.00; gpt-5-mini $0.25 · $0.025 · $2.00; gpt-6-astra $10 · $1 · $50. Astra 파일럿 호출당 입력 2,339 / 출력 274 토큰을 쓰면 gpt-5.2 호출당 약 11.5원(출력 1,000 토큰이면 약 26원), 4판 × 최대 20호출 = 80호출 상한에서 약 0.9천–2.1천 원.

## 5. 진행 상태와 한 일 (2026-09-26 KST)
- 19:36–19:39 KST: 첫 지시(직접 올리기)에 따라 Qwen3.5-122B-A10B-FP8와 Qwen3.8-27B를 `/data/harvest/models/`에 내려받기 시작 → 사용자 정정 뒤 19:39 KST 우리 프로세스만(argv 정확 비교) 종료하고 **부분 파일 삭제**(qwen35_122b_fp8 72 GB, qwen38_27b 24 GB, HF 캐시 빈 항목 2개). vLLM 서버는 띄우지 않았다.
- 대리 실행(gpt-5.2, 4판)용 클라이언트 변경(모델 id만 바꾸는 `SoloAstra(model_id=…)`·가격표 한 줄·시험)은 작성했으나, 자동 권한 검사가 유료 API 실행 준비를 '실제 거래'로 막아 **공유 파일 변경을 되돌리고** 패치만 `D:\tools\scratch_qdd\open_vlm\proxy_client.patch`·`test_proxy_model.py`로 보관했다. 사용자 허용 뒤 이 패치로 등록 → 3호출 자체 검사 → 4판을 잇는다.
- [갱신 2026-09-26T11:05Z] 사용자 승인("허용") 뒤 등록 `5c021c6` 커밋, gpt-5.2 4판 실행 중(결과는 `docs/stage3/results/open_vlm_solo.md`).

## 6. 학습 가능한 크기의 목표 (사용자 목적 정정, 2026-09-26T11:05Z)
- 사용자(원문): "나는 학습할 수 있는 llm크기에서 아스트라를 대체하는게 목적이야", "아니 빨리해줘 4판". → 3절의 397B는 **호스팅 가능한 상한 참고**로만 두고, 대체 목표는 우리 H200에서 미세조정할 수 있는 크기로 바꾼다.
- '학습 가능' 가정: LoRA(bf16 기반 가중치 고정) 기준 H200 1–4장(장당 141 GB) — 밀집 ≤ 약 35B(27B bf16 가중치 약 54 GB) 또는 전체 약 35B/활성 3B급 MoE. 지금 빈 GPU = 메인 파드 0·1(x2 파드는 E-MAR-real 사용 중, 확인 안 함).
- **목표 = Qwen3.5-27B**(밀집, 2026-02, Apache-2.0, 같은 Qwen3.5 카드 표: ERQA 60.5·EmbSpatial 84.5·RefSpatial 67.7·CountBench 97.8·RefCOCO 90.9). 이 크기에서 우리 과제에 가장 가까운 RefSpatial(점 참조)이 가장 높고, 밀집이라 LoRA가 단순하다. 버금: Qwen3.5-35B-A3B(ERQA 64.8, RefSpatial 63.5), 같은 구조의 새 판 Qwen3.8-27B(2026-08, ERQA 65.5, 공간 지표 미공개 — 목표 확정 뒤 교체 후보).
- **대리 = gpt-5-mini**(`gpt-5-mini-2025-08-07`, effort low): Qwen3.5-122B 카드의 같은 표에서 GPT-5-mini ERQA 54.0·EmbSpatial 80.7·CountBench 91.0·RefSpatial 9.0 — Qwen3.5-27B보다 구현체·공간 지표가 3–7점 낮아 **보수적(낮은 쪽) 대리**다(RefSpatial 9.0은 점 출력 형식 차로 보여 해석 제외). 참고로 gpt-5.2(397B 카드 표)는 ERQA 59.8·EmbSpatial 81.3으로 Qwen3.5-27B와 ERQA가 가깝다 — 두 대리가 목표를 아래(mini)와 비슷한 쪽(5.2)에서 감싼다(다른 카드 표끼리라 불확실).
- 바닥 참고: Qwen3-VL-8B 무료 5판 0/5(작은 크기의 하한).
- **대리의 영샷 결과는 Astra 교사 데이터로 미세조정하기 전의 출발점**이지, 학습 뒤 성능이 아니다.
