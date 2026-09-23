# 인수인계: 새 세션이 가장 먼저 읽을 문서

마지막 갱신: 2026-09-23 19:55 UTC (두 번째 세션 진행 중, v3 조사 에이전트 6개 실행 중. 결과는 `docs/research/v3/`)

## 1. 먼저 할 일
1. `dev` 브랜치에 있는지 확인한다. `main`에는 이 문서들이 없다. `main`에 직접 커밋, 푸시, 병합하지 않는다.
2. 다음 순서로 읽는다.
   1. `CLAUDE.md`: 모든 규칙과 제약. 반드시 지킨다.
   2. `docs/user-log.md`: 사용자 발언 전체 기록. 의도를 여기서 파악한다.
   3. `docs/plan.md`: 현재 계획 v2 ([사용자] / [제안] / [결정 필요] 구분).
   4. `docs/draft-log.md`: 버전별 기록과 교훈. 같은 실수를 반복하지 않는다.
   5. `docs/research/v2/00~07-*.md`: 모듈별 검증 보고서(근거 URL, 신뢰도).
   6. `paper/main.tex`: Overleaf 정리본(빨간색 = 사용자 의도, 검정색 = Claude 내용).
3. 네트워크를 확인한다.
   - `curl -s -o /dev/null -w "%{http_code}" https://arxiv.org/abs/2506.07339`가 200이면 원문을 읽을 수 있다.
   - 안 되면 사용자에게 네트워크 허용을 요청한다.

## 2. 현재 위치
- 진행 단계: **단계 1, 초안 조사 (목표 약 3시간 ±1~2시간)**
  - 19:25 UTC에 시작했다.
  - 첫 세션에서 약 20분 동안 1차 검증(에이전트 8개)을 했다.
  - 첫 세션의 네트워크가 막혀 있었고(원문 불가) 검색 한도 200회가 소진되어 중단했다.
  - **남은 초안 조사 시간은 약 2.5시간(±1~2시간)이다.**
- 그다음은 단계 2, 상세 설계(6~24시간)다. 각 부분에 장착할 모듈에 집중한다.

## 3. 남은 초안 조사 작업 (우선순위 순)
1. **원문 재검증**: `docs/research/v2/`에서 SINGLE-SOURCE나 UNCONFIRMED인 수치와 주장을 arxiv 원문으로 확인한다. 특히 다음 항목이다.
   - Jev jaggedness 문서 (docs.typesafe.ai/model-jaggedness/jev-1.13)
   - Jev 요청당 최대 질문 수
   - Astra 요청당 이미지 수 한도
   - FLARE 수치
   - A2C2 4.7ms / ICLR 2026 여부
   - LiPo
   - SiT-Bench, BALROG
   - AGNOSTOS 설정(에피소드 수, 시드)
   - 2606.15017, ExpWeaver, IOM, H2-EMV
2. **LLM/VLM 분야 전반 조사** (1차에서 거의 못 함)
   - M3: 선택지 확률 → 연속값 변환, 순서형 분류 기법
   - M1/M2: 장면 그래프(ConceptGraphs, HOV-SG), Set-of-Mark, 코드 기반 하위 목표 명세(Code as Policies 계열)
   - M8: 이미지 격자 대 개별 프레임 대 영상(일반 VLM 문헌)
   - M10: 2026년 메모리 벤치마크와 새 방법 (MemCompiler 2605.07594 등)
3. **호출 방식 비교 선행 연구**: arXiv 2608.28075(event-triggered FM planning)를 확인한다. 주기 / 이벤트 / 시간 초과 비교가 이미 있으면 컨트리뷰션을 조정한다.
4. **스킬 논문 GitHub 스타 수 확인**: 1년 이내, 상위 5개 순위를 확정한다.
5. **선점 추적**: Jev-as-Policy 저장소(Astra + Jev RoboTwin 평가 예고), jev-libero, Awesome-Astra-Embodied-AI 목록의 논문 내용(2609.12541, 2609.19138, 2608.17209)
6. 끝나면 할 일
   - `docs/plan.md` v3, `paper/main.tex`를 갱신한다.
   - `docs/draft-log.md`에 v3 항목을 추가한다.
   - `dev`에 푸시하고 사용자에게 보고한다.
   - 사용자에게 [결정 필요] 항목을 묻는다.

## 4. 사용자 결정을 기다리는 것
1. 핵심 주장 범위: "VLA는 일반화 안 됨"을 "대규모 로봇 데이터와 학습 없이도 덜 무너짐"처럼 좁힐지
2. 인식 앞단 (SAM 3 + 깊이 / FoundationPose 등). CLAUDE.md 규칙상 사용자가 정한다.
3. 실험 환경 (AGNOSTOS/RLBench 제안)
4. 기간 밖 참고 문헌(AHA, BID, RoboOS 개념) 허용 여부
5. 저장소 이름 변경(qdd → harvest)은 사용자가 직접 한다.

## 5. 작업 습관 (첫 세션에서 정착된 것)
- 커밋 메시지 끝에 Co-Authored-By 줄을 붙이고, 커밋하면 바로 `git push origin dev` 한다.
- 조사 에이전트를 병렬로 돌릴 때는 공통 규칙을 파일로 주고, 결과는 `docs/research/<버전>/`에 쓰게 한다.
- 검색 한도가 세션 전체에서 공유된다(첫 세션은 200회). 원문 읽기(curl/WebFetch)를 우선하고 검색은 아껴 쓴다.
- 사용자에게는 한국어로, 짧고 명확하게 보고한다.
