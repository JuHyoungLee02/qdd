# D7 선점 재검사 (2026-09-24, 9/18 이후 새 항목 위주)

작성: 2026-09-23 23:55 UTC, 선점 재검사 에이전트(텍스트 반환) → 메인 세션 저장·요약. 전체 검색어 43개(arXiv API, 6초 간격, 429 없음), WebSearch 5회, arXiv cs.RO /list/new(9/23 게시 104편), GitHub commits.atom.
색인 한계: arXiv API 최신 제출이 2026-09-22 17:59 UTC(9/23~24 제출분 미색인).

## 결론
- **M4 (a)+(b) 확정 규칙**: 9/18 이후 신규 선점 없음. 그러나 이전 검색이 놓친 **A3 (2605.11567, 2026-05-12, "Dynamic Execution Commitment of Vision-Language-Action Models")**가 "그룹 샘플링 합의 점수 → 합의 낮은 행동은 합의 높은 행동을 조건으로 재디코딩해 검증 → 앞에서부터 이어지는 가장 긴 검증 구간만 확정"을 했다(메인 세션 초록 확인). 차이: 학습 VLA 하나에서 **같은 시각** 샘플(시간차 겹침 호출 아님), 블랙박스 typed 결정 모델 아님, **(b) 실행 뒤 예상 대 측정 비교 없음**, keep/replace/repair 대신 청크 길이만. → 반드시 인용, 새로움 문장 수정.
- **평가(환경 변화에서 LLM 대 VLA)**: **RoboDawn (2609.22966, 2026-09-19, "Transferring the Intelligence of VLMs to Robotic Control")** — 에이전트형 VLM이 이산 이동·회전·그리퍼 명령으로 폐루프 제어(정지형), RoboTwin 2.0 C2R(깨끗한 장면 학습 → 랜덤화 장면 평가)에서 무학습 53.2%, 1-shot 73.6% 대 π0.5 46.0%(HarnessVLA 58.4%), RoboDojo 35.67% → 47.17%(메인 세션 원문 확인). 차이: 같은 인식 모듈 위에서 결정 층만 바꾸지 않음(VLM은 원본 이미지), clean→shift 낙폭을 짝지어 재지 않음, 비정지 아님. → 반드시 인용, "처음 잰다" 문구 수정.
- M6 typed 결정 지점, M10 컴파일 규칙: 변화 없음.
- **E2a("마차") 반례(커뮤니티, LOW)**: RoboJEV(lykycy123, 9/23) 같은 구조화 상태에서 Jev 43/50 < 룰 48/50(과제 5 × 시드 10, 정지형), embodied-jev(FBddcz, 9/22) 스킬 모드 Astra 9/9 = 룰 9/9. → "코드 술어 위 Jev > 룰" 가설의 알려진 반례.
- Jev 쪽 선점 없음: jev-realtime-sdk README "at most one decision is in flight at a time"(겹침 호출을 설계상 금지 — M4와 대조 근거), Jev-as-Policy 9/21 이후 커밋 없음(Astra+Jev 결과 여전히 예고), reflex-autonomy-lab은 System 2만 비동기.

## 새 항목 표
| id·날짜 | 무엇 | 겹침 | 위험 |
|---|---|---|---|
| 2605.11567 A3 (05-12) | VLA 청크 그룹 합의 → 앞 구간 확정 | M4 (a) 뼈대 | MED, 필수 인용 |
| 2602.21445, 2606.11408, 2606.03847, 2606.00537, 2607.04739, 2608.09125 | 학습 정책 청크의 적응형 실행 구간 | M4 관련 | LOW |
| 2609.22966 RoboDawn (09-19) | 에이전트 VLM 무학습 제어, C2R에서 π0.5 대비 우위 | 평가 부분 겹침 | MED~HIGH, 필수 인용 |
| 2609.20116 (09-17) | GPT-6 Astra VLN-CE 무학습 SR 52% | Astra 로봇 사례 | LOW |
| 2609.24350 LIBERO-VPro (09-21) | VLA·WAM 시각 강건성 벤치(오래된·누락 관측에 약함) | 우리 주장 지지 | LOW, 인용 권장 |
| 2609.25636 RoboFollow (09-22) | VLA가 장면 교란에서 지시 따르기 실패 | 지지 | LOW |
| 2609.19803 HEROIC (09-17) | 같은 인식 위 VLM 기준선 비교(수색) | "같은 인식" 설계 선례 | LOW |
| RoboJEV / embodied-jev (GitHub) | Jev ≤ 룰 관측 | E2a 반례 | LOW, 인용·대비 |

(검색어 43개 전체 표와 GitHub 확인표는 에이전트 원 보고 기준. 요점만 여기 옮겼다.)
