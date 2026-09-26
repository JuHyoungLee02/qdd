# E-OpenVLM-proxy — 오픈 VLM 대리(gpt-5.2)로 Astra 단독 조종 4판 (사전 등록)

- 작성: open-VLM 에이전트, 2026-09-26T10:50Z(UTC, KST 19:50). **유료 호출 전에** 커밋한다(P15). 결과는 `docs/stage3/results/open_vlm_solo.md`.
- 근거: 사용자 질문(원문) "근데 이걸 아스트라가 아닌 지금 우리가 돌릴 수 있는데 대형 오픈소스llm들은 이걸 못하나? 가능한 오픈 lln찾아보고 일단 동급의 지피티 api로 불러서 평가해보기 4판만해보는걸루", 정정(원문) "저거 다운해서 하라는게 아니라 일단 저중에 고르고 비슷한 성능의 openai ㅇapi 불러 테스트 하잖뜻", 승인(원문, "gpt-5.2로 4판, 상한 3,000원 허용"에 대한 답) "허용".
- 조사·대응: [open_vlm_astra_replacement_2026-09-26](../research/open_vlm_astra_replacement_2026-09-26.md) — 목표 오픈 VLM = **Qwen3.5-397B-A17B**, 대리 = **gpt-5.2**(`gpt-5.2-2025-12-11`, 같은 Qwen 카드 표에서 MMMU −1.7·RealWorldQA +0.6·ERQA +7.7·EmbSpatial +3.2, Qwen − GPT). **이 실험의 결과는 대리 모델의 값이지 오픈 모델 자체의 값이 아니다.**

## 0. 자체 검사
- **결정**: "오픈 VLM 최상위급(대리)이 Astra 단독 인터페이스(`astra-solo@v2`)로 mug_tray를 잡고 놓는가" → 되면 실제 오픈 모델(Qwen3.5-122B/397B 자체 호스팅)을 같은 인터페이스로 재는 무료 실험을 등록할 가치가 있다; 0이고 원인이 인식(첫 접근 목표 xy 오차 > 20 mm)이면 오픈 모델 대체 전에 인식 보조가 먼저다.
- **표본**: 4판(n = 4)은 방향만 보여 준다. 성공률 추정·Astra와의 유의 비교는 하지 않는다.
- **더 싼 사전 실행**: Qwen3-VL-8B 무료 5판(0/5, 인식 한계)과 참값 6/6이 이미 있다(astra_solo_pilot 2절). 배선은 Astra와 같은 클라이언트이며 모델 id만 바꿨다(시험 `tests/astra_solo/test_proxy_model.py`: 요청 본문이 `model` 외에는 Astra와 같음).

## 1. 설정 (Astra 파일럿과 같게, 모델만 바꿈)
- 프롬프트 `astra-solo@v2`(`PROMPT_ID` 변경 없음), 동기 루프, 명령 `eef`/`edit`/`gripper`/`stop`, 격자·낙하선 덧그림, 측정 이력, PNG `detail: high`, Responses API 스트리밍, `reasoning.effort = low`(Astra low와 같은 값; gpt-5.2가 받는 값), `max_output_tokens` 6,000, `prompt_cache_key astra_solo`.
- 코드: 고정 사본 `/data/harvest/code_open_vlm_proxy_<커밋>`(git archive, LF) = `11cbc39`의 astra_solo + 이 등록 커밋의 변경(모델 id·가격표·러너 `--model proxy-low --api-model`). 따라서 이력 문구 P107 고침과 API 가드(변경 2)가 켜진 판이다 — 파일럿 4편(`50336ce`)과 이력 문구 한 가지가 다르다(Astra 비교표에 적는다).
- 편: DEV 레이아웃, 순서 (standard 0) → (dr 0) → (standard 1) → (dr 1)(파일럿 순서), 한 Isaac 프로세스 = 한 편, Isaac은 메인 파드 **GPU 1**.
- 한도: 프롬프트에 적힌 호출 40·움직임 180 s는 그대로, 러너 조기 종료 **20호출 또는 움직임 60 s**(`--stop-calls 20 --stop-motion 60`). 파일럿 Astra 성공 4편은 모두 이 안(최대 17호출·22.7 s)이었다.
- 영상(필수): 편마다 연속 mp4(머리 | 오른손목, 저장 프레임 4 fps)와 모델 시점 mp4(호출별 입력 두 영상 + 답·결과 글), `/data/harvest/videos/open_vlm_proxy/gpt-5.2/`, `index.json`·`index.md`(`tools/astra_solo/make_videos.py`). 원본 프레임·호출 기록은 `/data/harvest/out/open_vlm_proxy/proxy-low/`에 남긴다.

## 2. 비용·가드 (가격: gpt-5.2 입력 $1.75 / 캐시 $0.175 / 출력 $14 per 1M, 공식 가격표 2026-09-26, 1,450원/USD)
- 호출당 추정: Astra 파일럿 토큰(입력 2,339·출력 274)이면 **약 11.5원**, 출력 1,000이면 약 26원. 편당 ≤ 20호출 → 편당 약 230–520원, 4판 **약 0.9–2.1천 원**.
- 하드 정지 **3,000원**(새 장부 `/data/harvest/logs/open_vlm_proxy/ledger.jsonl`, 호출 직전 최대 비용 예약: (4,000 × $1.75 + 6,000 × $14)/1M ≈ 132원). 편 관문 `누적 + 1.25 × (끝난 편 평균, 없으면 500원) ≤ 3,000원`. 재설계 정지: 무효율 > 10 % 또는 호출당 > 40원(`--est-krw-per-call 20`의 2배).
- API 가드: `insufficient_quota`·크레딧 오류는 즉시 정지, 빈 답·오류 연속 3번이면 정지.
- **자체 검사(첫 3호출 뒤)**: 무효 ≤ 1/3, API 오류 0, 호출당 ≤ 40원, 답의 `model` 필드가 gpt-5.2 계열, 명령이 작업 상자 안 — 하나라도 어기면 멈추고 원인을 적은 뒤 재설계 여부를 정한다.

## 3. 지표 (Astra 파일럿과 같은 정의)
- 편별 성공·파지 + 들기·실패 단계(approach / grasp / lift / place + 접근 세분)·끝 이유·호출 수·무효 수·성공까지 움직임 s·벽시계 s·원·접근 목표 xy 오차 중앙(mm)·첫 닫기 xy 오차(mm)·잘림/막힘.
- 호출 단위: 지연 p50/p95, 입력·출력·추론 토큰, 호출당 원, 무효율.
- 프레임 눈 확인(단계별 분해 규칙): 실패 편은 어느 단계에서 몇 mm 빗나갔는지 영상으로 확인한다.

## 4. 판정 (결과 전 고정, 방향만)
- **WORKS**: 성공 ≥ 1편 또는 파지 + 들기 ≥ 2편 → 오픈 모델 자체 호스팅 무료 실험을 다음 후보로 올린다.
- **PERCEPTION**: 파지 + 들기 0편 그리고 접근 목표 xy 오차 중앙 > 20 mm → 오픈급 모델에는 인식 보조(확대 자르기·점 지정 + 광선–평면 교차)가 먼저.
- **DOWNSTREAM**: 그 밖 → 실패 단계 분해가 가리키는 곳을 적는다.
- Astra 파일럿(4/4, 편당 9–17호출, 편당 438–1,019원)과의 표는 기술만 한다(n = 4).

## 변경 기록
