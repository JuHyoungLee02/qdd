# E-CJ1 사전등록 — 시뮬 참값 명령 × {스크립트 실행기, VLA 조이스틱} + 같은 VLA 단독 (결합 프로그램 1번, P0-3 + P0-8)

> **명칭 갱신 (2026-10-01):** 사용자 확정으로 하위 모델을 'VLA'가 아니라 **JCR(Joystick-Conditioned Reflex, 조이스틱 반사 정책)**로 부른다. 이 문서는 사전등록 원문이라 아래 'VLA' 표기를 그대로 둔다(등록 뒤 결과 규칙). 새 문서·논문은 JCR을 쓴다. NOW.md §1-0 참고.

- 작성 2026-09-30 22시경 KST, COUPLE 에이전트. 프로그램 `docs/stage3/coupling_program.md`, 계획 `D:\tools\scratch_qdd\board\PLAN_coupling.md`. **이 문서 커밋 뒤에 본 실행을 시작한다.** 결과를 본 뒤 문턱·팔·시드를 바꾸지 않는다(바꾸면 '변경 n'으로 기록). 유료 호출 0.
- 상위 LLM은 이 실험에 쓰지 않는다: 명령은 **시뮬 참값**(`harvest/astra_solo/pt_truth.PtTruth` — 시뮬 물체 자세로 계산한 점 + 높이 의도 명령, 방식 D와 같은 점 → 깊이 → xyz 경로). 상위를 붙이는 재실행(PX·PV)은 E-CJ2(본 35B 최적 체크포인트, 없으면 f35_d)에서 한다. Astra·교사 정책은 쓰지 않는다.

## 1. 질문
1. (Q1 상한) 이 세계·이 인터페이스에서 시뮬 참값 명령 + 스크립트 실행기(OX)의 성공률 = 과제 상한은?
2. (Q2 실행기 손실) 같은 명령을 C1 VLA가 조이스틱으로 실행하면(OV) 얼마나 잃는가? — 2×2의 'VLA 상한' 칸이자, VLA를 결합에 쓸 수 있는지의 관문.
3. (Q3 핵심 가설 준비) 같은 VLA가 스스로 계획할 때(V0)보다 조이스틱 역할(OV)이 나은가? (짐을 덜어 준 VLA > 단독 VLA)

## 2. 팔
| 팔 | 명령 | 실행 | 코드 |
|---|---|---|---|
| OX | 시뮬 참값(PtTruth, iface pt) | 스크립트 최소 저크 직선(MinJerkExec) | `harvest.couple_joy.run --arms ox` |
| OV | 시뮬 참값(같음) | **VLA 조이스틱**(`couple_joy.vla_exec.VLAJoyExec`, C1 청크, 0.33 s마다 labels_v2 조이스틱, 그리퍼는 허용 방향만·도착 뒤 1.5 s 안에 VLA가 못 끝내면 코드가 끝냄 = `grip_fallback`) | `--arms ov` |
| V0 | 없음(VLA가 스스로 결정: 방향·크기·대상·단계) | VLA 단독 런타임(`harvest.eval.closed` C5 fused, 결합 끔) | 옛 사본 `code_vla_solo_d752509`(`tools/vla_alone/vla_closed.py`, 1.0배, 영상 10 Hz) |

- VLA = `/data/harvest/ckpt/sr1c/c1/last`(E-SR1c ADOPT_C1) 하나. 서버 = x2 GPU0 :8151, 코드 `code_cj_vla_9322853h`(C1을 돌리던 `code_couple_dry_9322853` 사본, 바인드 주소만 0.0.0.0). OV·V0가 같은 서버를 쓴다.
- OV의 C1 문맥 문장 = 이미지 전용 상태(옛 런타임과 바이트 동일, 파드 확인). 현재 런타임은 C1을 거부하므로(프롬프트 판 불일치) V0는 옛 런타임이다 — **V0 해석 한계**: 이 런타임에는 E-VLA-solo 진단의 교착(T1 모순 → M4 hold, 12편 중 8편)이 남아 있다. V0는 '이 VLA의 스스로 계획 모드가 지금 낼 수 있는 값'이지 VLA 단독의 상한이 아니다.

## 3. 세트·제한
- 세계: E-Couple 세계(`astra_solo.world.SoloWorld`, 머그 → 쟁반, 머리 깊이 켬), DEV 배치 시드 **0–19 × standard·dr = 팔당 40편**, 팔 사이 같은 시드 짝.
- 제한: OX·OV 명령 30회·동작 120 s(E-M35CL과 같음), V0 `--max-seconds 120`.
- 스모크(배관, 판정 제외, 등록 전 실행): `out/couple/cj1_smoke`, 시드 0 standard OX·OV·V0 1편씩 — 실행·영상·로그만 확인했다. 스모크가 잡은 배관 버그 2개(시작 그리퍼 폭 → 단계 carry 고정, 틱 로그 줄바꿈)는 고친 뒤 등록했다. 성공 여부로 규칙을 정하지 않았다.

## 4. 지표
- 편 성공(에피소드 자체 판정 `success`), 들어 올림(`grasp_lift`), 실패 단계·끝 이유, 명령 수, 시뮬 시간, 벽시계.
- OV 전용: `grip_fallback` 수(편당), `vla_error`, reach/settled/timeout 수, VLA 청크 지연 p50/p95, **폐루프 조이스틱 준수** = 명령 `dir_xy` ≠ none이고 다음 스텝까지 손끝이 xy로 2 mm 이상 움직인 스텝 중, 그 이동이 명령 방향(E-SR0 방향 벡터)과 45° 안인 비율(`vla_steps.jsonl`).
- 기록(나중 끝-끝 학습용, 사용자 09-30): 명령(calls/), 조이스틱·관절·VLA 청크(`vla_steps.jsonl`), 10 Hz 시각·손끝·관절·물체 자세(`ticks.jsonl`), 10 fps 머리 | 손목 프레임(jpg 보존) + mp4.

## 5. 판정 규칙 (짝 부트스트랩 10,000회, 시드×변형 단위)
- **G0 관문**: OX 성공 ≥ 30/40. 미달이면 세계·인터페이스 문제 → Q2·Q3 판정 보류, 원인 분해 후 '변경'으로 재등록.
- **Q2**: d = OX − OV(짝).
  - `EXEC_OK`: d ≤ 5 %p 이고 OV ≥ 30/40 — VLA 조이스틱이 스크립트 실행기와 맞먹는다.
  - `VLA_FLOOR`: OV ≤ 4/40 — 이 VLA는 조이스틱으로도 과제를 못 한다 → 2×2(E-CJ2) 전에 VLA 1단계 학습(P0-6·7)이 먼저.
  - 그 밖 `EXEC_LOSS`(d와 95 % 구간 보고, 실패 단계 분해).
- **Q3**: e = OV − V0(짝). `JOY_BETTER`: e ≥ +10 %p 이고 95 % 하한 > 0. `JOY_WORSE`: e ≤ −10 %p 이고 상한 < 0. 그 밖 `NO_DIFF`. 2절의 V0 해석 한계를 결과에 같이 적는다(교착 편 수를 따로 셈).
- 판정·표 = `tools/couple_joy/summary.py`(등록 때 고정, 결과 뒤 수정하면 '변경'으로 기록).
- 모든 판은 영상 확인(편마다 mp4) — 숫자만으로 결론 내지 않는다.

## 6. 카드·양보
- VLA: x2 GPU0(VLA 카드). x3 GPU0은 가져오지 않는다(상위 없음, E-M35CL 서빙 유지).
- 렌더: 7a2a GPU 0·1·3 레인(`tools/couple_joy/lane.sh`). `/data/harvest/out/l9/GPU_WANTED`(또는 레인 WANTED, 이 GPU의 L9 프로세스)가 생기면 진행 중 편을 끝내고(600 s 넘으면 중단) 레인이 나가며, 그 GPU의 마지막 레인이 `/data/harvest/out/l9/GPU_FREED`에 한 줄을 남긴다. 7a2a GPU2·78dc·x2 GPU0 렌더 금지.

## 7. 코드
- 실행 코드 = 이 등록 커밋의 `git -c core.autocrlf=false archive` 사본 `/data/harvest/code_cj_<커밋>`(실행 중 수정 금지). 단위 시험 `tests/couple_joy` 27개 통과.
- V0 영상: 옛 런타임이 10 Hz 머리·손목 프레임(jpg)을 `<편>/standard|dr/C5/ours/*/…_frames`에 남긴다; mp4는 실행 뒤 같은 프레임으로 만든다.
