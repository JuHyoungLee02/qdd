# 인수인계: 새 세션이 가장 먼저 읽을 문서

마지막 갱신: 2026-09-24 23:32 UTC (R1–R6 완료·태그 stage3-r1r6, R7 1회차 FAIL → 수정 중, 정본 §1~§67)

> 현재 판본: plan **v6.8**, SUMMARY **v3.10**, 정본 §1~§42. 아래 §1의 판본 표기(v5.6)는 옛 기록이고 최신 상태는 §2.6.

## 1. 먼저 할 일
1. `dev` 브랜치인지 확인한다. **모든 작업(글, 코드)은 `dev`에서 시작하고 `dev`에만 푸시한다. `main`은 절대 건드리지 않는다**(사용자가 직접 반영).
   - Windows 클론이면 `git -c safe.directory=D:/qdd ...`가 필요할 수 있다.
2. 다음 순서로 읽는다.
   1. `CLAUDE.md`: 모든 규칙과 제약.
   2. `docs/user-log.md`: 사용자 발언 전체(1~41번). 의도는 여기서.
   3. `docs/plan.md`: 현재 계획 **v5.6** ([사용자] / [제안] / [결정 필요]). §5에 [결정 필요] 10개와 첫 실험.
   4. `docs/draft-log.md`: v0~v4.1 기록과 교훈. **같은 실수를 반복하지 않는다.**
   5. `docs/research/v3/README.md`(에이전트 공통 규칙) + `v3/01~19`(원문 확인 보고서). v2는 참고만(일부 정정됨).
   6. `paper/`: Overleaf 초안(CVPR 공식 author kit 구조, 한국어 마인드맵, 빨간색 = 사용자 의도).
3. 네트워크: `curl -s -o /dev/null -w "%{http_code}" https://arxiv.org/abs/2506.07339` → 200이면 원문 가능. 두 번째 세션에서는 arXiv, docs.typesafe.ai, developers.openai.com, GitHub, OpenReview, Semantic Scholar 모두 됐다.

## 2. 현재 위치
- **단계 1 초안 조사**: 2026-09-23 19:25 UTC 시작 → **21:32 UTC 마감**(약 2시간 07분, 범위 안). 마감 이유는 draft-log.
  - 첫 세션: 약 20분, 검색 요약만(v2).
  - 두 번째 세션: 19:49부터. 원문 확인 보고서 18개(v3/01~18), plan v3 → v4.1, Overleaf를 CVPR 템플릿으로.
- **단계 2 모듈 설계**: 21:32 UTC 시작. 최소 6시간(→ 03:32 UTC 이후), 최대 24시간(±1~2시간). 결과는 `docs/design/`.
  - [사용자] 파이프라인 설계가 아니다. 각 부분(M1~M10)에 대해 어디의 어떤 연구가 최고였고, 무엇을 가져올 수 있고, 우리 것에 어떻게 접목할지를 최대한 모은다. 로봇·VLA 분야일 필요 없다. LLM/VLM 방법 중 아직 로봇에 안 쓰인 것도 찾는다. 1년 반 이내(큰 주제의 기초 문헌은 예외, 표시).

## 2.5 단계 2 진행 상황 (2026-09-24 01:30 UTC)
- **먼저 읽을 것**: `docs/design/SUMMARY.md`(현재 설계 정리본 v2, 23:30 기준) → `docs/design/00-interfaces.md`(정본 §1~§23, 뒤 절이 앞 절보다 우선; SUMMARY v2 뒤의 변경은 §19~§23과 D8~D10 문서) → 필요한 모듈 문서.
- 완료: 설계 1판 M1~M10, 검증 D1·D2(원문), D3(근거 상향), D4(반대 검토 + 로봇 밖 분야 2차 + 그 원문 확인), D5(일관성 49건 정리), D6(모의 심사: 3/4/2점, 두 논문 문제), D7(선점 재검사: A3, RoboDawn), D8(RoboDawn·A3 정독), D9(Slow Brain·Show-Harness·GPT-as-Policy 정독), D10a(Harness VLA·CaP-X 정독 + 코드), D10b(Critic in the Loop·CheckVLA 정독), 첫 실험 프로토콜(`E-first-experiments.md`), 평가 설계(`EVAL-evaluation-design.md`), 설계 정리본 v2.
- 가장 중요한 사실
  - 사용자 핵심 주장 지지 근거 둘: RoboDojo Astra standard→random −11.1% 대 π0.5 −72.2%(우리가 RoboProbe 원자료로 계산), RoboDawn C2R Astra 무학습 53.2% 대 π0.5 46.0%.
  - M4 새로움: (a) 시간차 겹침 typed 호출 합의 + (b) 실행 뒤 예상 대 측정을 **함께** 쓰는 확정 규칙(A3·Slow Brain은 각각 일부만).
  - 학회: CVPR 2027 제출 2026-11-16 AoE, ICRA 2027 마감됨.
- 완료(01:30): §21·§22 반영, SUMMARY v3, plan v5.8, D11 최종 일관성 점검(60건) 반영, Overleaf v4(빨간 줄 33개 user-log 글자 일치, `tools/intent_check.py`로 확인).
- 완료(01:55): D12 선점 재검사 → 정본 §24, SUMMARY v3.1, plan v5.9.
- 완료(02:22): D13 M1·M2·M5 원문 정독 → 정본 §25, SUMMARY v3.2, plan v6.0, Overleaf.
- **단계 2 마감 03:37 UTC**: 보고서 `docs/design/STAGE2-CLOSE.md`. 사용자 결정(user-log 25·26) 반영 완료 — 논문 한 편, effort 기본 low + low·high 비교, D32 → 정본 §27, M1 기본 후보 A, Overleaf 논문형 본문(`paper/main.tex`) + 마인드맵(`paper/mindmap.tex`).
- **03:37 뒤 연장·추가 작업(05:03 UTC 기준)**: user-log 26–31.
  - Overleaf: `paper/main.tex`는 논문형 글(16쪽), 그림 5장(`paper/figures/`, 스크립트 `figures/src/make_figs.py`, 실행 `MPLCONFIGDIR=D:/tools/mplcache PYTHONPATH=D:/tools/pylib`), 마인드맵은 `paper/mindmap.tex`(빨간 줄 36, `tools/intent_check.py`).
  - 점검: D15(오류)·D16(자료·신뢰도, bib 39편 서지 확인) 반영. 22.58 → 원문 22.48 등.
  - API 일관성: 정본 §28(Astra A1–A6, Jev J1–J4, E0 반복·매일 카나리). §29 다수결(A5) 보류. §30 D18 결과 — 3개는 §31에서 결정됨(user-log 32, Claude 결정·근거 포함): A5′ 검사→수리(다수결 삭제), A4′ 적응형 patch|replace, J5 Jev conformal 게이트(E1 뒤). 설계 문서·논문 반영 완료(05:24 UTC).
  - 규칙 위반 1건 발견·수정: C 드라이브 사용 → 임시 파일은 `D:\tools\scratch_qdd`만.
- **07:02 UTC 추가**: user-log 33–34 — 학습 실행기 B(소규모 E2E, 모든 스킬 실행을 하나의 학습 실행기가 맡고 스크립트 스킬은 GT 생성기·백업, 결정 층은 학습 안 함). 정본 §32·§33, 근거 `docs/design/D19-action-expert.md`, 논문 '학습 실행기' 절·E-AE-0~5·개요도 반영. D9 해소(허용). 새 사용자 결정 대기: D35 도메인 무작위화 허용 여부, D36 주 표 실행기 S(잠정) 대 B. 글꼴은 나눔고딕(paper/fonts). PDF 출력은 D:/tools/pdf_out.
- 다음(제안, 사용자 지시 대기): 단계 3 첫 실험 E0·E0.5(같은 날) → E1 → E2a, 병행 EVAL S0·S1. 남은 사용자 결정은 SUMMARY §5.1 "나중" 묶음과 실물 실험(D30). E0 전 할 일: R1 금지어 보기 이름 교체(정본 §27 끝).
- D10에서 바뀐 것: M7 "적시 재현율(CheckVLA 방식)"은 원문 정의가 아니었음 → 고정 창판(판정 기준) + 원문판(병기). E-M8a에 원문 충실 기준 A2-CV·A1-cal·A1-wait·A6-CiL-sync. RPent Astra 92.63%는 논문 아닌 리더보드 값(8칸 T/S, 메모리 두 묶음, 에피소드당 412 s 정지형). 반대 증거 둘: CheckVLA d_lat = 10에서 경계 대기가 청크 안 수리보다 나음, CaP-X 검증 강화 프롬프트 68.29 → 65.43.
- 남은 계획(마감 전 기록, 완료됨): 단계 2 마감 보고. 이전 계획: 마지막 일관성·사용자 의도 점검 → 단계 2 마감 보고(최소 03:32 UTC 이후).
- 사용자 [결정 필요]: `SUMMARY.md` §5.1(D1~D28) + plan §8의 18(논문 틀)·19(실물 실험). 결정 전에는 두 안을 대칭으로 둔다.

## 2.6 07:02 UTC 뒤 결정 (정본 §34~§42, user-log 35~41)
- **§34·§35**: 도메인 무작위화 넣음(D35), 주 표 실행기 = 스크립트 스킬 S(D36), action expert = 구간 제한 잔차 R(`D20-expert-role.md`).
- **§36~§39** [사용자 결정]: 로봇 = ROBOTIS AI Worker, 카메라 = ZED 스테레오(머리 ZED Mini + 손목 D405), 실물 = FFW-SG2 베이스 고정, R 힘 입력 = 관절 `effort` + 그리퍼 전류(손목 F/T 추가 안 함). GT·모듈 실험 장면 = cyclo_lab AI Worker 한 팔 + `ZED_M` 쌍둥이(`D21-aiworker-zed.md`). 남은 하드웨어 결정 없음.
- **§40**: Inspect Robots(`robocurve/inspect-robots`, MIT, 논문 없음) 판정 — 선행 겹침 없음, Robocurve Astra 실물 수치는 LOW라 근거로 안 씀(`D22-inspect-robots.md`).
- **§41** [사용자 결정, user-log 41]: **1차 평가 = Inspect Robots + AI Worker SG2 한 팔 시뮬, 2차 = RoboDojo.** B1a-real 해소(agent + Astra = 범주 1 기준선).
- **§42** (`D23-inspect-robots-integration.md`): 시계 sync/simlat/wall 주입, 주 표 = 지연 충실 트랙(우리 simlat, 동기 기준선 `LatencyChargingController`) + sync-fair 병기, RTF 기록, 오라클 상태 정보 동등, `aiworker` 몸체·`OursPolicy` 어댑터, 기준선 B1a-IR·B5-IR·B3b-IR, 단계 P0~P4. 반영 문서: EVAL, E-first, SUMMARY v3.10, plan v6.8, 논문 평가 절.
- **다음(단계 3, 사용자 go 대기)**: E0·E0.5(같은 날, E0.5 먼저) / ROBOTIS HF 데이터로 오프라인 스테레오 안정성 시험(E3-ST, E §5.10) / Inspect Robots **P0** 설치·스모크(v0.59.0·커밋 `7e506e3` 고정). 사용자 지시 전에는 시작하지 않는다.

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

## 2.7 단계 3 이후 상태 (2026-09-24 21:03 UTC, user-log 42~66, 정본 §43~§64)
- **먼저 읽을 것**: `docs/superpowers/plans/2026-09-25-e2e-ready.md`(현재 계획: 관문 R1–R7 → S-E2E), `docs/design/00-interfaces.md` §43–§64, `docs/stage3/direction-log.md`(방향 검사 기록), 진행 기록(ledger) `.superpowers/sdd/2026-09-24-stage3-experiments/progress.md`, 결과 문서 `docs/stage3/results/`.
- **핵심 결정**: Jev 사용 불가 → 로컬 VLM Qwen3-VL-4B typed 선택기(§44, §50, Gemma 4 E4B는 지연 탈락) / Astra = 위층 계획기 + 하트비트 5 s·단계 경계·사건(§45) / 인식 이름 `detect_phrase`는 Astra가(§46) / 카메라 = AI Worker 기본, 시뮬 설정은 humanoid-challenge-env 복사, ZED Mini VGA 85°·fx 367(§43·§47) / 시뮬 CPU PhysX(§48) / 실물 추론 = RTX PRO 6000 서버, 지금은 H200에서 가정해 검증(§49·user-log 62) / 영점 선택기는 최빈 미만 → 정답 재정의 labels_v2(§53·§54) / 학습 경로 C→A→B(§51·§52), **융합 원칙: 런타임은 단일 VLA(결정 토큰 + action expert + 확인 헤드)**, 모듈형 스택은 기준선으로 병기(§58·§60) / 입력 = 머리 + 활성 손목 다중 이미지, lead 호출(§57·§59) / S-E2E = ROBOTIS AI Worker 공개 데이터 1,575편·10 Hz(§62·§63) / **M4 (b)·critic 측정 = 세계 쪽 확인 헤드 V1h + 로봇 쪽 고유 감각 T1, critic 경보 = V1h 단독(§61·§64)**.
- **완료 관문**: R1 인식 기준선(3D 오차 35 mm — 융합의 근거), R3 처리량(6.5–12배), R4 단계 B 코드(KI 기울기 0 확인, GPU 스모크), R5 폐루프(Inspect Robots에서 한 판 성공), E-M4b-meas. **진행 중**: R2 데이터 생성기(30 Hz·다과제·DR·LeRobot 내보내기), R6 평가 스크립트(CAL/TEST 차단 가드), 결과 라벨(T14, GPU 0 장시간). **다음**: R7 객관 검증 순회 2회 연속 무결 → S-E2E 소규모 E2E 학습(사전 등록 뒤).
- **성격 주의(§56)**: 지금까지의 학습·평가 수치는 모두 파이프라인 확인용 소규모 시험 — 논문 결과로 쓰지 않는다.
- **운영 규칙(추가)**: 파드 작업 폴더 `/data/harvest`(옛 경로는 링크), 모든 파드 파일은 /data 아래(`source /data/harvest/env.sh`), GPU 0·1 = Isaac 렌더, GPU 2 = 학습·vLLM(렌더 금지, user-log 64 허용), GPU 3 = vLLM; 로컬 임시 파일은 D:\tools\scratch_qdd만(하위 에이전트는 C scratchpad를 기본으로 쓰려 하므로 지시문에 명시), pytest basetemp는 pytest.ini가 D로 고정; 키: HF `/data/.hf_token`, OpenAI `/data/.openai_token`(값 출력 금지); Jev 키는 없음.
- **사용자 대기 항목**: 없음(주 표 병기 유지 합의, RB1 라이선스는 논문 전 확인).

## 2.8 R7 진행 (2026-09-24 23:32 UTC)
- R1–R6 관문 + R7 전 사전 수정 완료(태그 `stage3-r1r6`, 커밋 519de26). 추가 결정 §65(결과 라벨 = 거부권 용도), §66(R2 생성기·R2_TRAIN 시드 10000–59999), §67(날짜 정정·두 호출 구조·SCOPED 목록).
- **R7 1회차 FAIL**(DEFECT 2: §63 코드 미구현·S-E2E 학습 진입점, §42 로그의 요청 해시·카나리 id / DOC 8) → 코드 수정 에이전트 진행 중, 문서는 메인이 정정. 수정 뒤 **2회차부터 다시 센다**(2회 연속 무결이면 S-E2E).
- 보고서: `docs/stage3/results/r7_cycle1.md`, 수정 기록 `docs/stage3/results/r7_fixes.md`.
