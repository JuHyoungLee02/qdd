# v3 초안 조사: 공통 규칙 (에이전트용)

작성: 2026-09-23 19:55 UTC, 두 번째 세션. 초안 조사 단계(19:25 UTC 시작, 목표 약 3시간). v3 조사는 약 70분 안에 끝낸다.

## 무엇을 하나
`docs/handoff.md` §3의 남은 초안 조사. 보고서 하나당 주제 하나. 결과는 이 폴더에 `NN-주제.md`로 쓴다(한국어).

## 반드시 먼저 읽을 것
- `D:\qdd\CLAUDE.md`: 모든 규칙과 제약
- `D:\qdd\docs\plan.md`: 현재 계획 v2 (모듈 M1~M10)
- 자기 주제와 관련된 `D:\qdd\docs\research\v2\*.md`: 이미 확인한 것과 "확인 못 한 것"

## 네트워크 (이번 세션은 열려 있다)
- arXiv 원문: `curl -sL https://arxiv.org/abs/<id>` (초록, 제출일), `https://arxiv.org/html/<id>` (본문 HTML), `https://arxiv.org/pdf/<id>`.
  - 검색: `http://export.arxiv.org/api/query?search_query=...&max_results=..&sortBy=submittedDate`
- GitHub 스타: `curl -s https://api.github.com/repos/<owner>/<repo>` 의 `stargazers_count`, `created_at`. 비인증은 시간당 60회 한도. 아껴 쓴다.
- 인용 수: `https://api.semanticscholar.org/graph/v1/paper/arXiv:<id>?fields=title,year,venue,citationCount,publicationVenue`
- OpenReview, 학회 사이트, 저자 블로그, docs.typesafe.ai, developers.openai.com 모두 접근 가능.
- **WebSearch는 세션 전체가 한도를 공유한다(첫 세션에서 200회가 바닥났다).** 에이전트당 최대 15회. 원문 읽기(curl, WebFetch)와 arXiv API 검색을 먼저 쓴다.
- 긴 HTML은 파일로 저장한 뒤 grep/python으로 필요한 부분만 뽑는다. 저장은 `D:\qdd` 밖의 임시 폴더(예: `$TEMP`)에.

## 신뢰도 규칙 [사용자]
- HIGH: 동료 심사 주요 학회(NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, CoRL, RSS, ICRA, ACL 계열 등) 채택 확인, 또는 유명 연구실 + 반응(인용, 스타, HF 추천) 확인.
- MED: 유명 연구실이지만 심사 전, 또는 심사는 됐지만 반응 정보 없음.
- LOW: arXiv만, 덜 알려진 그룹, 반응 미확인. **추천하지 않는다. 쓰느니만 못하다.**
- 각 항목에 신뢰도 근거(학회, 소속, 인용 수, 스타)를 숫자로 적는다.

## 기간 규칙 [사용자]
- 1년 반 이내: arXiv 첫 공개일이 **2025-03-23 이후**.
- LLM+스킬 결합 논문은 1년 이내: **2025-09-23 이후**.
- 예외: 아주 큰 주제를 포괄하는 기초 문헌은 기간 밖이어도 된다. 쓸 때는 "기간 밖, 기초 문헌"이라고 표시한다.

## 분야 규칙 [사용자]
- 정답이 로봇 분야에만 있다고 생각하지 않는다. LLM, VLM, 로봇, VLA 전 분야를 본다.
- **아직 로봇에 적용되지 않은 LLM/VLM 방법**을 적극 찾는다. 모듈 단위로 최고이면 된다.

## 지난 버전에서 틀린 것 (반복 금지) — `docs/draft-log.md`
1. 요약만 보고 방법 세부를 단정했다 → **원문(초록 + 본문 해당 절)을 직접 읽고** 인용한다. 수치는 표나 본문 문장에서 확인한다.
2. "최대(up to)" 수치를 평균처럼 썼다 → 수치의 조건(벤치마크, 기준 방법, Pass@k, 평균/최대)을 함께 적는다.
3. "선행 연구 없음"을 쉽게 주장했다 → 부재 주장은 여러 검색어로 찾아본 뒤에만, 사용한 검색어를 적는다.
4. 신뢰도 낮은 문헌을 핵심 근거로 썼다 → 신뢰도 등급을 먼저 매긴다.
5. 기간 조건을 어겼다 → 제출일을 arXiv 원문으로 확인한다.
6. 모델 제약(Jev는 텍스트만, 수치에 약함)을 무시했다 → Jev에 옮길 수 있는지 항상 따진다.
7. 사용자 주장도 반대 증거를 찾아 보고한다.
8. 확인 못 한 것은 확인 못 했다고 적는다. 과한 의심으로 없는 사실을 만들지 않는다.

## 보고서 형식
1. 조사 방법과 한계 (사용한 WebSearch 횟수, 원문 읽은 논문 수)
2. 검증 표: 항목 | 확인 수준(ORIGINAL-CONFIRMED = 원문 확인 / CONFIRMED-MULTI / SINGLE-SOURCE / UNCONFIRMED / WRONG) | 정정/비고(신뢰도 근거 포함) | 출처 URL
3. 새로 찾은 것과 모듈별 최고 후보 (어디서 최고였는지, 무엇을 가져오나, 우리 구조(Astra 상위, Jev 텍스트 전용 하위, 스킬)에 어떻게 접목하나)
4. 반대 증거와 위험
5. plan.md에 반영할 제안 (사용자 의도 [사용자]와 제안 [제안]을 섞지 않는다)
6. 확인 못 한 것

## 금지
- `D:\qdd`의 다른 파일(plan.md, main.tex, CLAUDE.md 등)을 고치지 않는다. 자기 보고서 파일만 쓴다.
- git 커밋, 푸시하지 않는다(메인 세션이 한다).
- Jev 입력 변환 방법(카메라 → 텍스트)은 사용자가 정한다. 후보와 근거만 적고 확정하지 않는다.
