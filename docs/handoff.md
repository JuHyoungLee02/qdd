# 인수인계: 새 세션이 가장 먼저 읽을 문서

마지막 갱신: 2026-09-23 21:15 UTC (두 번째 세션, 로컬 Windows `D:\qdd`. 초안 조사 마무리 중, plan v4.1)

## 1. 먼저 할 일
1. `dev` 브랜치인지 확인한다. **모든 작업(글, 코드)은 `dev`에서 시작하고 `dev`에만 푸시한다. `main`은 절대 건드리지 않는다**(사용자가 직접 반영).
   - Windows 클론이면 `git -c safe.directory=D:/qdd ...`가 필요할 수 있다.
2. 다음 순서로 읽는다.
   1. `CLAUDE.md`: 모든 규칙과 제약.
   2. `docs/user-log.md`: 사용자 발언 전체(1~24번). 의도는 여기서.
   3. `docs/plan.md`: 현재 계획 **v4.1** ([사용자] / [제안] / [결정 필요]). §5에 [결정 필요] 10개와 첫 실험.
   4. `docs/draft-log.md`: v0~v4.1 기록과 교훈. **같은 실수를 반복하지 않는다.**
   5. `docs/research/v3/README.md`(에이전트 공통 규칙) + `v3/01~18`(원문 확인 보고서). v2는 참고만(일부 정정됨).
   6. `paper/`: Overleaf 초안(CVPR 공식 author kit 구조, 한국어 마인드맵, 빨간색 = 사용자 의도).
3. 네트워크: `curl -s -o /dev/null -w "%{http_code}" https://arxiv.org/abs/2506.07339` → 200이면 원문 가능. 두 번째 세션에서는 arXiv, docs.typesafe.ai, developers.openai.com, GitHub, OpenReview, Semantic Scholar 모두 됐다.

## 2. 현재 위치
- **단계 1 초안 조사**: 2026-09-23 19:25 UTC 시작, 목표 약 3시간(±1~2시간) → 22:25 UTC 전후 마감.
  - 첫 세션: 약 20분, 검색 요약만(v2).
  - 두 번째 세션: 19:49부터. 원문 확인 보고서 18개(v3/01~18), plan v3 → v4.1, Overleaf를 CVPR 템플릿으로.
- **단계 2 모듈 설계**: 최소 6시간, 최대 24시간(±1~2시간). 초안 마감 직후 시작.
  - [사용자] 파이프라인 설계가 아니다. 각 부분(M1~M10)에 대해 어디의 어떤 연구가 최고였고, 무엇을 가져올 수 있고, 우리 것에 어떻게 접목할지를 최대한 모은다. 로봇·VLA 분야일 필요 없다. LLM/VLM 방법 중 아직 로봇에 안 쓰인 것도 찾는다. 1년 반 이내(큰 주제의 기초 문헌은 예외, 표시).

## 3. 단계 2 진행 방법 (제안, 자율 진행)
- 모듈마다 `docs/design/Mx-*.md` 한 개: (1) 역할과 입출력 (2) 분야 전체의 최고 후보 표(어디서 최고, 조건 포함 수치, 신뢰도, 기간) (3) 가져올 것과 접목 방법 (4) 대안과 비교 실험 (5) 반대 증거 (6) 열린 질문·[결정 필요].
- 순서 제안: M4(가장 강한 컨트리뷰션) → M3·M5(M4와 얽힘) → M7·M8·M9(실패 흐름) → M1·M2(사용자 결정 대기 부분은 후보만) → M6 → M10 → 평가·첫 실험(E1 보정, E2 마차 시험, E3 형식 비교) 설계.
- 모듈마다: 조사 에이전트(요약) → **원문 확인 에이전트(독립)** → 메인 세션이 설계를 바꾸는 주장 직접 재확인 → plan·Overleaf 갱신 → draft-log 기록 → dev 푸시.
- 30분마다 루프 점검(세션 cron). 사용자 승인 없이 계속 진행한다.

## 4. 사용자 결정을 기다리는 것 (`plan.md` §5 요약)
1. 핵심 주장 문구 2. M1 변환 방법·인식 앞단 3. 실험 환경(RoboDojo-Sim + LIBERO-Plus 제안) 4. 기간 밖 문헌 허용 5. Astra effort 원칙 적용 6. M3 기본안(촘촘 대 목표 지정형) 7. M8 자체 판단 구현·다중 프레임 기본값 8. M6 5위·"기존 스킬" 정의 9. M10 메모리 주입·로컬 학습 진행 모델 10. 정밀 구간 정지 허용
- 결정 전에는 두 안을 모두 설계에 남기고 멈추지 않는다.
- 저장소 이름 변경(qdd → harvest)은 사용자가 직접 한다.

## 5. 작업 습관과 함정 (두 세션에서 정착)
- 커밋 메시지 끝에 Co-Authored-By 줄(시스템이 주는 것)을 붙이고 바로 `git push origin dev`.
- 조사 에이전트는 공통 규칙 파일(`docs/research/v3/README.md`)을 주고 결과를 `docs/research/<버전>/`에 쓰게 한다. 커밋은 메인 세션만.
- **API 한도**: arXiv 검색 API·Semantic Scholar·GitHub API는 같은 IP를 공유해 429가 난다. 한 번에 한 에이전트만 arXiv 검색 API(5초 간격)를 쓰게 하고, 나머지는 abs/html 페이지만.
- **원문 확인**: 요약 에이전트는 표 한 행을 일반화하거나 우리 제안을 원문처럼 적는 일이 반복됐다. 요약 뒤에는 반드시 독립 원문 확인 단계를 둔다. 원문 칸과 우리 접목안 칸을 나눈다.
- **부재 주장**은 전용 검색(검색어 기록) 뒤에만. "못 찾음"은 부재 증거가 아니다.
- **사용자 의도**: 조사가 의도와 달라도 [사용자] 줄은 그대로, 제안은 [결정 필요]로. 기본값도 사용자 예시 먼저.
- 시각은 `date -u`로 찍는다(추측 금지).
- Windows 체크아웃은 CRLF라 `sed` 줄 치환이 조용히 실패하거나 `\t`를 탭으로 바꾼다. 수정은 Edit 도구나 python으로 하고 grep으로 확인한다.
- `paper/` 컴파일: Tectonic 0.15.0 `D:/tools/tectonic/tectonic.exe`. 절차: `rm -rf D:/tools/texbuild; mkdir -p D:/tools/texbuild; cp -r paper/. D:/tools/texbuild/; cd D:/tools/texbuild; TECTONIC_CACHE_DIR=D:/tools/tectonic/cache D:/tools/tectonic/tectonic.exe main.tex`. PDF 확인은 `PYTHONPATH=D:/tools/pylib` pymupdf. 참고 문헌은 arXiv abs 페이지 메타데이터로 만든다(예: 로컬 `D:/tmp_main/mkbib.py`).
- 작업 드라이브는 D만 쓴다(C 사용 금지, 사용자 환경 규칙).
- 사용자에게는 한국어로 짧게 보고한다.
