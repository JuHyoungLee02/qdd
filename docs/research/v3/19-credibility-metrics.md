# 19. plan.md v4.2 근거 문헌 신뢰도 지표 (인용·스타·학회)

작성: 2026-09-23 21:30 UTC 전후. plan.md는 고치지 않았다. 이 보고서만 쓴다.

## 1. 조사 방법과 한계
- 대상: plan.md v4.2가 근거로 이름을 드는 논문·저장소 전부. plan 본문에서 arXiv id와 이름을 뽑고, id가 없는 이름은 `docs/research/v3/*`·`v2/*` 보고서의 id로 채웠다(이름 옆 id를 자동 추출한 뒤 S2 제목으로 전부 대조, 오매칭 0건). 총 **96항목**(arXiv 있는 것 89, arXiv 없는 저장소·리더보드·비arXiv 논문 7). plan에 이름만 있고 v3에서 id를 찾은 것 포함.
- 인용 수: Semantic Scholar batch API 1회 호출(89개 id, 429 없음). **측정 시각 2026-09-23 21:26 UTC.**
- 스타: GitHub API 비인증 41회(+1회 ReasoningBank). **측정 시각 2026-09-23 21:27 UTC.** 한도 초과 없음. 공식 저장소를 v3 보고서·arXiv 코멘트로 확인한 것만 적었다. 여러 논문이 공유하는 저장소(openpi, lerobot)는 논문 반응으로 보기 어렵다(표에 저장소 이름을 함께 적음).
- 첫 공개일·학회 표기: arXiv export API(`id_list`, 3회 호출, 약 3초 간격)의 `published`(v1 날짜)와 `arxiv:comment`. **측정 시각 2026-09-23 21:28 UTC.** S2 `publicationDate`는 쓰지 않았다(학회 날짜가 섞임).
- WebSearch 0회. 원문 본문은 읽지 않았다(지표 조사). 소속은 v3 보고서 기록을 그대로 썼고 이번에 재확인하지 않았다.
- 한계: (1) S2 인용 수는 Google Scholar보다 작게 나오는 경향이 있고, 1개월 안 된 논문은 인용 0이 정상이다. (2) S2 venue는 학회 채택을 늦게 반영한다(아래 목록 2 참고). (3) HF 추천(upvote)·X 반응은 재지 않았다. (4) arXiv 없는 self-triggered(2012)·WAPR는 인용을 못 쟀다.

## 2. 지표 → 등급 제안 규칙 (README 신뢰도 규칙을 숫자로 옮긴 것, [제안])
- **HIGH**: README 목록의 주요 학회(NeurIPS·ICML·ICLR·CVPR·ICCV·ECCV·CoRL·RSS·ICRA·ACL 계열, 여기에 IROS 포함) 채택이 arXiv 코멘트·S2·CVF/OpenReview 중 하나로 확인됨, **또는** 유명 연구실(PI, Google DeepMind, NVIDIA, Meta, Microsoft, HF, 칭화 AIR, NUS Show Lab 등) + 반응(인용 ≥ 20 또는 스타 ≥ 300).
- **MED**: 유명 연구실이지만 반응 약함(인용 < 20, 스타 < 300), 또는 반응은 큰데 미심사·소속 불명, 또는 주요 목록 밖 심사처(TMLR, IJCAS)로 반응 약함.
- **LOW**: 미심사 + 반응 약함(인용 < 5, 스타 < 100 또는 없음) + 유명 연구실 확인 안 됨. 개인 데모 저장소.
- 1개월 안 된 미심사 논문은 인용이 쌓일 시간이 없어 LOW로 떨어진다. "시기상조"로 따로 표시했지만 **규칙상으로는 LOW**다(README: "반응 미확인 → LOW").
- "핵심" = plan이 설계 선택·주장·수치 근거로 직접 쓴 것(본문 [제안] 줄, "근거:", "반대 증거" 중심 수치). "보조" = "보조:", 기준 방법, 관련 연구, 범주 예시, [결정 필요] 4의 허용 요청 목록.

## 3. 표 (96항목)
- plan의 신뢰도 등급 열: **plan v4.2는 거의 모든 항목에 등급을 적지 않았다**(명시는 2512.17250 LOW, FaRe·RIR "둘 다 MED-LOW" 뿐). README "각 항목에 신뢰도 근거를 숫자로 적는다"와 어긋난다. 그래서 대부분 "없음".
- 학회(plan 표기) 열의 "-"는 plan에 학회 표기가 없다는 뜻. "(기간 밖 표기)"는 plan이 기간 밖이라고 적은 것.

| # | 모듈 | 이름 | arXiv id | 첫 공개일 | 기간(안·밖) | 학회(plan 표기) | S2 venue | 인용 수(S2) | 공식 저장소 스타 | plan의 신뢰도 등급 | 지표로 본 등급 제안 | 핵심/보조 | 근거·비고 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 선점 | Jev-as-Policy | - | (저장소 2026-09-21) | 안 | - | - | 미측정(arXiv 없음) | 37 (YuanKJing/Jev-as-Policy) | 없음 | LOW | 핵심(선행·C1) | 개인 데모 저장소, 논문 없음. 선행 인정용이라 강등 영향 작음 |
| 2 | 선점·M4 | Slow Brain, Fast Planner | 2606.20458 | 2026-06-18 | 안 | - | arXiv.org | 0 | - | 없음 | LOW | 핵심(선행·C2) | 인용 0, 미심사. 반드시 인용할 선행으로만 씀(우리 주장 근거 아님) |
| 3 | 선점·M3·M6 | Show-Harness (NUS) | 2609.10522 | 2026-09-09 | 안 | - | (빈칸) | 4 | 451 (showlab/Show-Harness) | 없음 | MED-HIGH | 핵심(M3·M6) | NUS Show Lab + 451★, 2주 된 논문이라 인용 4 |
| 4 | 선점·M6 | Harness VLA / RPent | 2607.08448 | 2026-07-09 | 안 | - | arXiv.org | 23 | 966 (RLinf/RPent) | 없음 | HIGH | 핵심(M6·기준 방법) | 유명 연구실(RLinf) + 인용 23 + 966★ |
| 5 | 선점·M4 | 실시간 비동기 자기회귀 정책 | 2606.13355 | 2026-06-11 | 안 | - | arXiv.org | 0 | - | 없음 | LOW | 보조(관련 연구) | 인용 0 |
| 6 | 선점·M8 | AGP (Agent as Policy) | 2609.12541 | 2026-09-11 | 안 | - | (빈칸) | 2 | 14 (agent-as-policy-2026/agent-as-policy) | 없음 | MED | 보조(범주·effort 수치) | Notre Dame·UCSD(Meng Jiang), 인용 2, 14★ |
| 7 | 선점·M8 | GPT-as-Policy (Galbot) | - | (저장소 2026-09-13) | 안 | - | - | 미측정(arXiv 없음) | 526 (anonymous-report-421/GPT-as-Policy) | 없음 | MED | 보조(범주) | 논문 없음(보고서 사이트), 526★ |
| 8 | 선점·M8 | GPT-Policy (In-Context Robot Learning with VLM Agents) | 2609.19138 | 2026-09-16 | 안 | - | (빈칸) | 0 | 270 (cheng-haha/GPT-Policy) | 없음 | LOW-MED | 보조(범주) | plan 본문에는 이름 없이 v3 보고서에서만. 인용 0, 270★ |
| 9 | 선점·M8 | TGL (Teach and Grow) | 2608.17209 | 2026-08-17 | 안 | - | (빈칸) | 0 | - | 없음 | MED | 보조(범주) | SJTU Hesheng Wang, 인용 0 |
| 10 | 선점·평가 | RoboDojo 벤치마크 | 2607.04434 | 2026-07-05 | 안 | - | arXiv.org | 20 | 617 (RoboDojo-Benchmark/RoboDojo) | 없음 | HIGH | 핵심(§3 지지 증거·주 벤치마크) | 인용 20 + 617★ (소속은 이번에 재확인 안 함) |
| 11 | 평가 | RoboDojo Astra 평가 | 2609.24170 | 2026-09-21 | 안 | - | (빈칸) | 1 | - | 없음 | LOW(시기상조) | 핵심(§3 Astra 수치) | 인용 1, 첫 공개 3일 전. 반응을 잴 시간이 없었다 |
| 12 | 선점·M8 | REFLEX | 2609.26532 | 2026-09-22 | 안 | - | (빈칸) | 0 | - | 없음 | LOW | 보조(관련 연구) | 인용 0, 미심사 |
| 13 | M1 | Context Length Alone Hurts | 2510.05381 | 2025-10-06 | 안 | EMNLP 2025 Findings | Conference on Empirical Methods in Natural Language Processing | 163 | - | 없음 | HIGH | 핵심(M1 원칙) | 인용 163 |
| 14 | M1 | FloorplanQA (KAUST) | 2507.07644 | 2025-07-10 | 안 | ICML 2026 | (빈칸) | 15 | - | 없음 | HIGH | 핵심(M1 원칙) | arXiv 코멘트 ICML 2026, 인용 15 |
| 15 | M1 | OmniParser V2 | 2408.00203 | 2024-08-01 | 밖 | -(기간 밖 표기) | arXiv.org | 216 | 25,446 (microsoft/OmniParser) | 없음 | HIGH | 보조(유비) | 25,446★, 인용 216 |
| 16 | M1 | SAM 3 / SAM 3.1 | 2511.16719 | 2025-11-20 | 안 | - | arXiv.org | 990 | 11,771 (facebookresearch/sam3) | 없음 | HIGH | 핵심(인식 1순위) | Meta, 인용 990, 11,771★ (3.1은 릴리스, 별도 논문 없음) |
| 17 | M1 | FoundationPose | 2312.08344 | 2023-12-13 | 밖 | -(기간 밖 표기) | Computer Vision and Pattern Recognition | 768 | 3,589 (NVlabs/FoundationPose) | 없음 | HIGH | 보조(후보) | CVPR 2024(S2), 인용 768, 3,589★ |
| 18 | M1 | WAPR.v2.1 (MUSE) | - | (리더보드 2026-03) | 안 | BOP 2025 리더보드 | - | 미측정(arXiv 없음) | - | 없음 | 미측정 | 보조(후보) | 논문·저장소 없음, 리더보드 항목. 반응 잴 수 없음 |
| 19 | M1 | Fast-FoundationStereo | 2512.11130 | 2025-12-11 | 안 | CVPR 2026 | arXiv.org | 28 | 1,497 (NVlabs/Fast-FoundationStereo) | 없음 | HIGH | 핵심(깊이 후보) | NVIDIA, 인용 28, 1,497★. 학회는 저장소 표기뿐 |
| 20 | M2 | PhyAgentOS | 2607.16636 | 2026-07-18 | 안 | - | arXiv.org | 4 | 2,481 (PhyAgentOS/PhyAgentOS) | 없음 | MED | 핵심(세션 계약) | 2,481★이지만 인용 4, 미심사 |
| 21 | M2 | Set-of-Mark | 2310.11441 | 2023-10-17 | 밖 | - | arXiv.org | 274 | 1,564 (microsoft/SoM) | 없음 | HIGH | 보조(개념) | Microsoft, 인용 274, 1,564★. 기간 밖인데 plan에 표시 없음 |
| 22 | M2 | Code-as-Monitor | 2412.04455 | 2024-12-05 | 밖 | CVPR 2025 | Computer Vision and Pattern Recognition | 76 | - | 없음 | HIGH | 보조(개념) | 인용 76 |
| 23 | M2 | COPE | 2506.11578 | 2025-06-13 | 안 | TMLR 2026 | Trans. Mach. Learn. Res. | 3 | - | 없음 | MED | 핵심(M2 근거) | TMLR(주요 학회 목록 밖), 인용 3, KAIST |
| 24 | M2 | AgileThinker / Real-Time Reasoning Agents | 2511.04898 | 2025-11-07 | 안 | ICLR 2026 | arXiv.org | 9 | - | 없음 | HIGH | 핵심(M2 근거) | v3에서 학회 논문집 PDF 확인, 인용 9 |
| 25 | M3 | VLA-0 | 2510.13054 | 2025-10-15 | 안 | - | arXiv.org | 53 | 492 (NVlabs/vla0) | 없음 | HIGH | 보조(해상도 수치) | NVIDIA, 인용 53, 492★ |
| 26 | M3 | BEAST | 2506.06072 | 2025-06-06 | 안 | NeurIPS 2025 | Neural Information Processing Systems | 24 | - | 없음 | HIGH | 보조(제어점) | 인용 24 |
| 27 | M3 | SPF (See, Point, Fly) | 2509.22653 | 2025-09-26 | 안 | CoRL 2025 | arXiv.org | 31 | - | 없음 | HIGH | 핵심(M3 반대 증거) | arXiv 코멘트 CoRL 2025, 인용 31 |
| 28 | M3 | PIVOT | 2402.07872 | 2024-02-12 | 밖 | -(기간 밖 표기) | International Conference on Machine Learning | 257 | - | 없음 | HIGH | 보조 | ICML 2024(S2), 인용 257 |
| 29 | M3 | GUI-Cursor | 2509.21552 | 2025-09-25 | 안 | ICML 2026 | arXiv.org | 10 | - | 없음 | HIGH | 핵심(M3 반대 증거) | arXiv 코멘트 ICML 2026, Microsoft, 인용 10 |
| 30 | M3 | KnowNo | 2307.01928 | 2023-07-04 | 밖 | -(기간 밖 표기) | Conference on Robot Learning | 442 | - | 없음 | HIGH | 보조 | CoRL 2023, 인용 442 |
| 31 | M4 | LocalAgreement (Whisper-Streaming) | 2307.14743 | 2023-07-27 | 밖 | -(기간 밖 표기) | International Joint Conference on Natural Language Processing | 68 | 3,673 (ufal/whisper_streaming) | 없음 | HIGH | 핵심(M4 (a)) | IJCNLP-AACL 2023 데모, 인용 68, 3,673★ |
| 32 | M4 | Spec-VLA | 2507.22424 | 2025-07-30 | 안 | EMNLP 2025 | Conference on Empirical Methods in Natural Language Processing | 36 | - | 없음 | HIGH | 핵심(M4 (a) 완화 수용) | 인용 36 |
| 33 | M4 | Speculative Actions | 2510.04371 | 2025-10-05 | 안 | ICLR 2026 | arXiv.org | 17 | - | 없음 | HIGH | 핵심(M4 갱신 틀) | Columbia, 인용 17. S2·arXiv 코멘트에 학회 없음(iclr.cc 검색 결과가 근거) |
| 34 | M4 | RTC (Real-Time Chunking) | 2506.07339 | 2025-06-09 | 안 | - | Neural Information Processing Systems | 236 | 13,974 (Physical-Intelligence/openpi) | 없음 | HIGH | 핵심(M4 3구간) | NeurIPS 2025(S2), 인용 236 |
| 35 | M4 | SmolVLA | 2506.01844 | 2025-06-02 | 안 | - | arXiv.org | 541 | 27,735 (huggingface/lerobot) | 없음 | HIGH | 핵심(M4 스케줄러) | Hugging Face, 인용 541 (저장소는 LeRobot 공용 27,735★) |
| 36 | M4 | VLASH | 2512.01031 | 2025-11-30 | 안 | - | arXiv.org | 66 | - | 없음 | MED-HIGH | 보조(발상만) | 인용 66 |
| 37 | M4 | A2C2 | 2509.23224 | 2025-09-27 | 안 | ICLR 2026 거절 | arXiv.org | 46 | - | 없음 | MED | 보조(발상만) | 인용 46, 거절 확인 |
| 38 | M4 | Input Prediction and Mishit Correction | 2512.17250 | 2025-12-19 | 안 | - | arXiv.org | 1 | - | LOW | LOW | 보조(가까운 선행) | 수업 과제, 인용 1 |
| 39 | M4 | DiscreteRTC | 2604.25050 | 2026-04-27 | 안 | - | arXiv.org | 2 | - | 없음 | LOW | 보조(관련) | 인용 2 |
| 40 | M4 | jev-drone | - | (저장소 2026-09-16) | 안 | - | - | 미측정(arXiv 없음) | 153 (RomanSlack/jev-drone) | 없음 | LOW | 보조(위험 수치) | 개인 저장소 153★ |
| 41 | M4 | jev-realtime-sdk | - | (저장소 2026-09-21) | 안 | - | - | 미측정(arXiv 없음) | 0 (chy4pro/jev-realtime-sdk) | 없음 | LOW | 보조(위험 수치) | 0★, 생성 3일 |
| 42 | M5 | SEAM | 2607.04609 | 2026-07-06 | 안 | - | arXiv.org | 4 | - | 없음 | LOW | 핵심(M5 겹침 평균 반대 증거) | 인용 4, 미심사, 소속 미확인(plan은 South China Univ. of Technology) |
| 43 | M5 | WAM 실시간 실행 연구 | 2608.01880 | 2026-08-03 | 안 | - | (빈칸) | 1 | - | 없음 | LOW | 핵심(M5·M8 반대 증거) | 인용 1, 미심사 |
| 44 | M5 | LiPo | 2506.05165 | 2025-06-05 | 안 | IJCAS 2025 | International Journal of Control, Automation and Systems | 6 | - | 없음 | MED | 보조(비교 후보) | IJCAS(주요 학회 목록 밖), 인용 6 |
| 45 | M5 | Ruckig | 2105.04830 | 2021-05-11 | 밖 | - | Robotics: Science and Systems Conference | 125 | 1,379 (pantor/ruckig) | 없음 | HIGH | 보조(비교 후보) | RSS 2021, 인용 125, 1,379★. 기간 밖인데 plan에 표시 없음 |
| 46 | M6 | Zetta | 2608.16590 | 2026-08-17 | 안 | - | (빈칸) | 3 | 1,252 (air-embodied-brain/Zetta-Embodiment) | 없음 | MED-HIGH | 핵심(M6) | 칭화 AIR + 1,252★, 인용 3 |
| 47 | M6 | CaP-X | 2603.22435 | 2026-03-23 | 안 | ICML 2026 | arXiv.org | 52 | 819 (capgym/cap-x) | 없음 | HIGH | 핵심(M6·M8) | OpenReview ICML 2026(v3), 인용 52, 819★ |
| 48 | M6 | ROSClaw | 2603.26997 | 2026-03-27 | 안 | - | arXiv.org | 4 | 625 (PlaiPin/rosclaw) | 없음 | LOW-MED | 보조(5위 후보) | 인용 4, 저장소 연결 추정 |
| 49 | M7 | π*0.6 (RECAP) | 2511.14759 | 2025-11-18 | 안 | - | arXiv.org | 316 | - | 없음 | HIGH | 보조(개념) | Physical Intelligence, 인용 316 |
| 50 | M7 | π0.7 | 2604.15483 | 2026-04-16 | 안 | - | arXiv.org | 136 | - | 없음 | HIGH | 보조(개념) | Physical Intelligence, 인용 136 |
| 51 | M7·M9 | FaRe | 2609.18016 | 2026-09-16 | 안 | - | (빈칸) | 0 | - | MED-LOW | LOW | 핵심(M7 정체 규칙·M9 구조) | 인용 0, 1주 됨, 미심사 |
| 52 | M7 | SAFE | 2506.09937 | 2025-06-11 | 안 | NeurIPS 2025 | Neural Information Processing Systems | 82 | 109 (vla-safe/SAFE) | 없음 | HIGH | 보조 | 인용 82, 109★ |
| 53 | M7 | GVL | 2411.04549 | 2024-11-07 | 밖 | ICLR 2025(기간 밖 표기) | International Conference on Learning Representations | 118 | - | 없음 | HIGH | 보조 | 인용 118 |
| 54 | M7 | R²VLM | 2603.17312 | 2026-03-18 | 안 | CVPR 2026 | arXiv.org | 3 | - | 없음 | HIGH | 보조(형식) | arXiv 코멘트 CVPR 2026, 인용 3 |
| 55 | M8 | BRACE | 2608.01428 | 2026-08-02 | 안 | ICML 2026 | (빈칸) | 0 | - | 없음 | HIGH | 핵심(M8 문지기) | arXiv 코멘트 ICML 2026, 인용 0 |
| 56 | M8 | self-triggered control (Heemels 외 2012) | - | 2012 (CDC) | 밖 | -(기간 밖 표기) | - | 미측정(arXiv 없음) | - | 없음 | HIGH | 핵심(M8 (3a) 개념) | CDC 2012, arXiv 없음(S2 미측정) |
| 57 | M8 | Learning When to Plan | 2509.03581 | 2025-09-03 | 안 | ICLR 미채택 | arXiv.org | 19 | - | 없음 | MED | 핵심(M8 (3a) 근거) | UCL·Oxford, 인용 19, 미채택 |
| 58 | M8 | Sentinel | 2410.04640 | 2024-10-06 | 밖 | CoRL 2024(기간 밖 표기) | Conference on Robot Learning | 79 | - | 없음 | HIGH | 보조((3b) 선례) | 인용 79 |
| 59 | M8 | KITE | 2604.07034 | 2026-04-08 | 안 | ICRA 2026 | arXiv.org | 2 | - | 없음 | HIGH | 보조(비교 조건) | arXiv 코멘트 ICRA 2026, 인용 2 |
| 60 | M8 | LIBERO-RECOVER | 2609.05178 | 2026-09-04 | 안 | - | (빈칸) | 0 | - | 없음 | LOW | 핵심(M8 시작 프레임 포함 수치) | 인용 0, 미심사 |
| 61 | M8 | CheckVLA | 2607.26789 | 2026-07-29 | 안 | - | arXiv.org | 2 | - | 없음 | LOW-MED | 핵심(M8 실험 설계 수치) | 칭화·상해교대·북경대·NTU, 인용 2, 미심사 |
| 62 | M8 | Critic in the Loop | 2603.05185 | 2026-03-05 | 안 | - | arXiv.org | 4 | - | 없음 | LOW | 보조(선행 구분) | 인용 4, 미심사 |
| 63 | M9 | RIR | 2609.18304 | 2026-09-16 | 안 | - | (빈칸) | 0 | - | MED-LOW | LOW | 핵심(M9 구조) | 인용 0, 미심사 |
| 64 | M9 | FLARE | 2608.26645 | 2026-08-27 | 안 | CVPR 2026 | (빈칸) | 6 | - | 없음 | HIGH | 보조 | arXiv 코멘트 CVPR 2026, 인용 6 |
| 65 | M9 | WebRollback | 2504.11788 | 2025-04-16 | 안 | EACL 2026 | Conference of the European Chapter of the Association for Computational Linguistics | 13 | - | 없음 | MED-HIGH | 보조 | EACL(ACL 계열), 인용 13 |
| 66 | M9 | FailSafe | 2510.01642 | 2025-10-02 | 안 | - | arXiv.org | 32 | - | 없음 | HIGH | 보조(평가용) | IROS 2026(arXiv 코멘트), 인용 32 |
| 67 | M9 | VRL-Bench | 2609.12404 | 2026-09-11 | 안 | - | (빈칸) | 0 | - | 없음 | LOW | 보조(반대 증거) | 인용 0, 미심사 |
| 68 | M10 | Evo-Memory (ReMem·ExpRAG) | 2511.20857 | 2025-11-25 | 안 | - | arXiv.org | 130 | - | 없음 | HIGH | 핵심(M10 Astra 쪽) | Google DeepMind, 인용 130 |
| 69 | M10 | ReasoningBank | 2509.25140 | 2025-09-29 | 안 | ICLR 2026 | arXiv.org | 199 | 594 (google-research/reasoning-bank) | 없음 | HIGH | 보조(형식) | arXiv 코멘트 ICLR 2026, 인용 199, 594★ |
| 70 | M10 | ACE | 2510.04618 | 2025-10-06 | 안 | ICLR 2026 | arXiv.org | 321 | 1,332 (ace-agent/ace) | 없음 | HIGH | 보조 | arXiv 코멘트 ICLR 2026, 인용 321, 1,332★ |
| 71 | M10 | Dynamic Cheatsheet | 2504.07952 | 2025-04-10 | 안 | - | Conference of the European Chapter of the Association for Computational Linguistics | 125 | 276 (suzgunmirac/dynamic-cheatsheet) | 없음 | HIGH | 보조(비교 기준) | EACL 2026(S2), 인용 125, 276★ |
| 72 | M10 | MemCompiler | 2605.07594 | 2026-05-08 | 안 | - | arXiv.org | 5 | - | 없음 | MED-LOW | 핵심(M10 Jev 쪽 0~2개·−83.3%) | MSR+칭화 AIR(v3), 인용 5, 미심사 |
| 73 | M10 | Kintsugi | 2605.09487 | 2026-05-10 | 안 | - | arXiv.org | 2 | - | 없음 | MED-LOW | 보조(선행 인정) | TU Darmstadt Kersting, 인용 2 |
| 74 | M10 | 예산 맞춘 메모리 비교 | 2606.15017 | 2026-06-12 | 안 | EMNLP 2026 | arXiv.org | 1 | - | 없음 | HIGH | 핵심(M10 반대 증거·라벨 규칙) | arXiv 코멘트 EMNLP 2026, 인용 1 |
| 75 | M10 | AWM (Agent Workflow Memory) | 2409.07429 | 2024-09-11 | 밖 | - | International Conference on Machine Learning | 285 | 474 (zorazrw/agent-workflow-memory) | 없음 | HIGH | 보조(비교 대상) | ICML 2025(S2), 인용 285, 474★. 기간 밖인데 plan에 표시 없음 |
| 76 | M10 | Robo-Dopamine (8B) | 2512.23703 | 2025-12-29 | 안 | - | arXiv.org | 48 | - | 없음 | HIGH | 보조([결정 필요] 9) | CVPR 2026(v3, CVF 목록), 인용 48 |
| 77 | 평가 | LIBERO-Plus | 2510.13626 | 2025-10-15 | 안 | CVPR 2026 | arXiv.org | 253 | 459 (sylvestf/LIBERO-plus) | 없음 | HIGH | 핵심(§3 지지·보조 벤치마크) | CVF 페이지(v3), 인용 253, 459★. S2·arXiv 코멘트엔 학회 없음 |
| 78 | 평가 | LIBERO-PRO | 2510.03827 | 2025-10-04 | 안 | - | arXiv.org | 138 | 325 (Zxy-MLlab/LIBERO-PRO) | 없음 | MED-HIGH | 보조(벤치마크) | 인용 138, 325★, 미심사 |
| 79 | 평가 | π0.5 | 2504.16054 | 2025-04-22 | 안 | - | arXiv.org | 1891 | 13,974 (Physical-Intelligence/openpi) | 없음 | HIGH | 핵심(§3 반대 증거·기준) | PI, 인용 1,891 |
| 80 | 평가 | DreamZero (World Action Models are Zero-shot Policies) | 2602.15922 | 2026-02-17 | 안 | - | arXiv.org | 355 | - | 없음 | HIGH | 핵심(§3 반대 증거) | NVIDIA, 인용 355 |
| 81 | 평가 | Gemini Robotics 1.5 | 2510.03342 | 2025-10-02 | 안 | - | (빈칸) | 89 | - | 없음 | HIGH | 핵심(§3 반대 증거) | Google DeepMind, 인용 89 |
| 82 | 평가 | AGNOSTOS / X-ICM | 2505.15660 | 2025-05-21 | 안(1.5년) / 밖(LLM+스킬 1년) | -(LLM+스킬 1년 창 밖 표기) | Neural Information Processing Systems | 40 | 70 (jiaming-zhou/X-ICM) | 없음 | HIGH | 보조(벤치마크·기준) | NeurIPS(S2), 인용 40, 70★ |
| 83 | 평가 | MolmoSpaces | 2602.11337 | 2026-02-11 | 안 | - | arXiv.org | 13 | 477 (allenai/molmospaces) | 없음 | MED-HIGH | 보조(선택 벤치마크) | AI2, 인용 13, 477★ |
| 84 | 평가 | VoxPoser | 2307.05973 | 2023-07-12 | 밖 | -(기간 밖 표기) | Conference on Robot Learning | 1135 | 839 (huangwl18/VoxPoser) | 없음 | HIGH | 보조(기준) | CoRL 2023, 인용 1,135 |
| 85 | 평가 | π0 | 2410.24164 | 2024-10-31 | 밖 | - | arXiv.org | 2752 | 13,974 (Physical-Intelligence/openpi) | 없음 | HIGH | 보조(기준 VLA) | RSS 2025(arXiv 코멘트), 인용 2,752. 기간 밖인데 plan에 표시 없음 |
| 86 | 평가 | OpenVLA | 2406.09246 | 2024-06-13 | 밖 | - | Conference on Robot Learning | 3462 | 7,070 (openvla/openvla) | 없음 | HIGH | 보조(기준 VLA) | CoRL 2024(S2), 인용 3,462, 7,070★. 기간 밖인데 plan에 표시 없음 |
| 87 | 평가 | RDT-1B | 2410.07864 | 2024-10-10 | 밖 | - | International Conference on Learning Representations | 887 | 1,804 (thu-ml/RoboticsDiffusionTransformer) | 없음 | HIGH | 보조(기준 VLA) | ICLR 2025(S2), 인용 887, 1,804★. 기간 밖인데 plan에 표시 없음 |
| 88 | 평가 | system-one-adapter | - | (저장소 2026-08-08) | 안 | - | - | 미측정(arXiv 없음) | 282 (typesafe-ai/system-one-adapter-python) | 없음 | MED | 보조(기준) | TypeSafe 공식 저장소 282★, 논문 없음 |
| 89 | 결정4 | BALROG | 2411.13543 | 2024-11-20 | 밖 | -(기간 밖 표기) | International Conference on Learning Representations | 134 | 272 (balrog-ai/BALROG) | 없음 | HIGH | 보조(허용 요청 목록) | ICLR 2025, 인용 134 |
| 90 | 결정4 | PriDe | 2309.03882 | 2023-09-07 | 밖 | -(기간 밖 표기) | International Conference on Learning Representations | 551 | - | 없음 | HIGH | 보조(허용 요청 목록) | ICLR 2024, 인용 551 |
| 91 | 결정4 | AHA | 2410.00371 | 2024-10-01 | 밖 | -(기간 밖 표기) | International Conference on Learning Representations | 179 | 73 (NVlabs/AHA) | 없음 | HIGH | 보조(허용 요청 목록) | ICLR(S2), 인용 179 |
| 92 | 결정4 | BID (Bidirectional Decoding) | 2408.17355 | 2024-08-30 | 밖 | -(기간 밖 표기) | International Conference on Learning Representations | 52 | - | 없음 | HIGH | 보조(허용 요청 목록) | ICLR(S2), 인용 52 |
| 93 | 결정4 | RoboOS | 2505.03673 | 2025-05-06 | 안(1.5년) / 밖(LLM+스킬 1년) | -(기간 밖 표기) | arXiv.org | 36 | 626 (FlagOpen/RoboOS) | 없음 | MED-HIGH | 보조(허용 요청 목록) | BAAI, 인용 36, 626★ |
| 94 | 결정4 | LLM-as-a-Judge 판정 분포 | 2503.03064 | 2025-03-04 | 밖 | -(기간 밖 표기) | Conference on Empirical Methods in Natural Language Processing | 50 | - | 없음 | HIGH | 보조(허용 요청 목록) | EMNLP 2025 Findings, 인용 50 |
| 95 | 결정4 | TRACT | 2503.04381 | 2025-03-06 | 밖 | -(기간 밖 표기) | Annual Meeting of the Association for Computational Linguistics | 27 | - | 없음 | HIGH | 보조(허용 요청 목록) | ACL 2025, 인용 27 |
| 96 | 결정4 | YOLOE | 2503.07465 | 2025-03-10 | 밖 | -(기간 밖 표기) | IEEE International Conference on Computer Vision | 70 | 2,295 (THU-MIG/yoloe) | 없음 | HIGH | 보조(허용 요청 목록) | ICCV 2025, 인용 70, 2,295★ |

집계: 96항목 / 핵심 38·보조 58 / 지표 등급 제안 HIGH 58, MED-HIGH 7, MED 9, MED-LOW 2, LOW-MED 3, LOW 15, LOW(시기상조) 1, 미측정 1 / 기간 안 71, 기간 밖 23, 1.5년 안이지만 LLM+스킬 1년 밖 2.

## 4. 목록 1 — plan이 **핵심 근거**로 쓰는데 지표가 LOW(또는 LOW-MED·MED-LOW)인 것 (강등 검토 대상)
| 항목 | plan에서의 쓰임 | 지표 | 제안 [제안] |
|---|---|---|---|
| SEAM 2607.04609 | M5 "겹침 평균은 정밀도를 깎는다" 핵심 수치(94.8→82.7%) | 미심사, 인용 4, 소속 미확인 | LOW 표시 + 보조로 내림. 같은 주장을 받칠 심사 논문(RTC NeurIPS 2025의 경계 비교 등)을 대신 쓴다 |
| WAM 실시간 연구 2608.01880 | M5 블렌딩 점수, M8 "멈추지 않는다" 반대 증거(72.5 대 40) | 미심사, 인용 1 | LOW 표시. 반대 증거로 올리는 것은 유지해도 되나(사용자 규칙 7) [결정 필요] 10의 유일한 근거로 쓰지 않는다 |
| FaRe 2609.18016 | M7 정체 규칙, M9 "언제/어디로/무엇을 남길지" 구조 | 미심사, 인용 0, 1주 | plan의 MED-LOW → **LOW**. M9 구조에 HIGH 근거가 없다는 점을 본문에 적는다 |
| RIR 2609.18304 | M9 구조(FaRe와 짝) | 미심사, 인용 0, 1주 | plan의 MED-LOW → **LOW**. 위와 같음 |
| LIBERO-RECOVER 2609.05178 | M8 "하위 작업 시작 프레임 포함"(0.103→0.247) | 미심사, 인용 0 | 보조로 내림 |
| CheckVLA 2607.26789 | M8 실험 설계 수치(10.1 대 10.2회, +8.5%p·+3.9%p) | 미심사, 인용 2(유명 대학 연합) | LOW-MED 표시. 실험 설계 "참고"로만 |
| RoboDojo Astra 평가 2609.24170 | §3 Astra 28.97/22.48% 등 핵심 주장 수치 | 미심사, 인용 1, 공개 3일 | LOW(시기상조) 표시. 단독 근거로 쓰지 않고 우리 재실행으로 대체한다는 §3 방침과 연결 |
| MemCompiler 2605.07594 | M10 Jev 쪽 "0~2개만"(−83.3%) | 미심사, 인용 5 (MSR+칭화 AIR는 v3 기록) | MED-LOW 표시. 소속 재확인 전까지 단독 핵심 근거 금지 |
| Slow Brain 2606.20458 / Jev-as-Policy(37★) | M4 새로움 범위를 줄이는 선행, 비교 조건 C1·C2 | 인용 0 / 개인 저장소 | **강등 불필요**: 우리 주장을 받치는 근거가 아니라 인정해야 할 선행이다. 등급만 LOW로 표시 |

## 5. 목록 2 — plan의 학회 표기와 S2 venue가 다른 것
- **S2와 다른 학회를 적은 경우는 0건.** 모두 "plan은 학회, S2는 arXiv.org 또는 빈칸"인 형태다.
- arXiv 코멘트가 plan 표기를 확인(S2가 늦은 것, 문제 없음) 10건: FloorplanQA(ICML 2026), SPF(CoRL 2025), GUI-Cursor(ICML 2026), R²VLM(CVPR 2026), BRACE(ICML 2026), KITE(ICRA 2026), FLARE(CVPR 2026), ReasoningBank(ICLR 2026), ACE(ICLR 2026), 2606.15017(EMNLP 2026).
- **S2·arXiv 코멘트 둘 다 학회가 없어 다른 출처에만 기대는 것 5건(재확인 권장)**: Fast-FoundationStereo "CVPR 2026"(근거 = 저장소 표기뿐, 가장 약함) / Speculative Actions "ICLR 2026"(근거 = 검색 결과의 iclr.cc 페이지) / AgileThinker "ICLR 2026"(v3: 논문집 PDF) / CaP-X "ICML 2026"(v3: OpenReview) / LIBERO-Plus "CVPR 2026"(v3: CVF 논문 페이지).
- 세부 차이 1건: 2510.05381은 plan "EMNLP 2025 Findings", S2 "EMNLP"(Findings 구분 없음). arXiv 코멘트가 Findings라 plan이 맞다.
- plan에 학회를 안 적었지만 S2·arXiv에 있는 것(적으면 등급 근거가 강해짐): RTC NeurIPS 2025, AGNOSTOS/X-ICM NeurIPS, π0 RSS 2025, OpenVLA CoRL, RDT ICLR 2025, AWM ICML 2025, Dynamic Cheatsheet EACL 2026, FoundationPose CVPR 2024, PIVOT ICML 2024, FailSafe IROS 2026, Ruckig RSS 2021.

## 6. 목록 3 — 기간 밖인데 plan에 "기간 밖" 표시가 없는 것
| 항목 | 첫 공개 | plan 위치 | 쓰임 |
|---|---|---|---|
| Set-of-Mark 2310.11441 | 2023-10-17 | M2 "객체 ID(텍스트판 Set-of-Mark)" | 개념 차용 |
| Ruckig 2105.04830 | 2021-05-11 | M5 마지막 층 비교 후보 | 비교 후보 |
| AWM 2409.07429 | 2024-09-11 | M10 반대 증거 문장 | 비교 대상 이름 |
| π0 2410.24164 | 2024-10-31 | §3 기준 방법 | 기준 VLA |
| OpenVLA 2406.09246 | 2024-06-13 | §3 기준 방법 | 기준 VLA |
| RDT 2410.07864 | 2024-10-10 | §3 기준 방법 | 기준 VLA |
- 여섯 모두 기준 방법·비교 후보·개념 차용이라 쓰는 것 자체는 문제가 적다. 다만 plan은 VoxPoser·X-ICM에는 "기준 방법 예외 요청"을 붙였으므로 **같은 기준으로 π0·OpenVLA·RDT·Ruckig·Set-of-Mark·AWM도 [결정 필요] 4 목록에 넣어야 일관된다** [제안].
- 참고: RoboOS(2025-05-06)는 1.5년 창 **안**이다. plan이 [결정 필요] 4에서 기간 밖으로 분류한 것은 LLM+스킬 1년 규칙 때문으로 보이며 맞다(X-ICM 2025-05-21도 같음). 이유를 한 단어 붙이면 좋다.
- 경계: Learning When to Plan(2025-09-03)은 LLM 에이전트 계획 호출 논문이다. "LLM+스킬 결합"으로 보면 1년 창(2025-09-23) 밖이 된다. 스킬 결합 논문은 아니라고 보아 "안"으로 두었다. [결정 필요 여부는 메인 세션 판단]

## 7. 확인 못 한 것
- 소속(유명 연구실 여부)은 v3 보고서 기록만 따랐다. SEAM·Slow Brain·2606.13355·PhyAgentOS·RoboDojo 소속은 이번에 확인하지 않았다.
- HF Papers 추천 수, X 반응은 재지 않았다(README 규칙의 "HF 추천" 축 빠짐).
- 공식 저장소를 모르는 논문(Spec-VLA, BEAST, KnowNo, Evo-Memory, MemCompiler, Kintsugi, FaRe, RIR 등)은 스타를 "-"로 두었다. 저장소가 없다는 뜻이 아니다.
- self-triggered(Heemels 외 2012, CDC)·WAPR.v2.1은 arXiv가 없어 인용을 못 쟀다.
- 2609.19138(GPT-Policy)과 GPT-as-Policy(Galbot 저장소)는 다른 작업이다. plan "GPT-as-Policy"는 저장소 쪽으로 보고 표에 둘 다 넣었다.
