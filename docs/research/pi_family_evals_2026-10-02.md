# π0 계열이 숫자로 비교된 평가 전수 조사와 실행 순서 (2026-10-02 03시대 KST, LIB0 에이전트)

- 사용자 원문(10-02 03시대 KST):
  - "pi0.5에서 자기들 논문이 다른거랑 비교하면서 내놨던걸 한 것도 우리가 직접 해보면 좋을듯 … 진짜 여러개를 다 비교 테스트 해보는 걸로 하자"
  - "3인칭 금지를 내가 풀게 … 허용은 해볼게"
- 조사 방법: 무료 웹 조사만 했다. 확인하지 못한 것은 '미확인'으로 적는다.
- 원칙(prereg_sim0 변경 2): 우리 팔은 지금 모델 그대로이고, 어댑터에는 로봇 실제 설정값만 넣는다. 양팔 과제는 우리 상위가 한 팔이므로 '한 팔로 가능한 과제만' 한다.

## A. PI 공식
| 출처 | 시뮬 평가 | 비교 대상(조건) | 재현 |
|---|---|---|---|
| π0 (2410.24164) | 없음(실기: 셔츠·테이블 치우기·장보기·토스트) | OpenVLA, Octo, ACT, DP, π0-small | 재현 불가 |
| FAST (2501.09747) | **LIBERO**(PI가 30k 미세조정): π0 96.8/98.8/95.8/85.2, π0-FAST 96.4/96.8/88.6/60.2 | — | 가능: openpi `pi0_libero`, `pi0_fast_libero`(#849 0 % 보고, 미확인) |
| π0.5 (2504.16054) | 없음(실기·가정) | π0, π0-FAST+Flow | 재현 불가 |
| KI (2505.23705) | **LIBERO**: π0.5+KI 98.0/97.8/95.6/85.8, LIBERO-90 96.0 | π0, π0-FAST, OpenVLA-OFT 97.6/98.4/97.9/94.5 | KI 체크포인트 비공개(미확인). π0·OFT는 가능 |
| openpi README | LIBERO pi05_libero 96.85(재현함: 우리 96 %), ALOHA sim `pi0_aloha_sim`(공식 수치 없음) | — | 가능 |

## B. 후속 시뮬 벤치(π0·π0.5를 기준선으로 쓴 것)
| 벤치 | π0 계열 수치(조건) | 다른 비교 대상 | 카메라 / 팔 | 라이선스 | 우리 연결 |
|---|---|---|---|---|---|
| **LIBERO-Plus** (2510.13626) | π0 원본 94.2 / 카메라 15.8 / 로봇 6.6 / 언어 61.0 / 조명 79.6 / 배경 78.5 / 노이즈 79.4 / 배치 70.4. π0-FAST도 있다(공식 가중치) | OpenVLA, OFT, NORA, WorldVLA, UniVLA | 3인칭 + 손목, 한 팔 | 미확인 | 쉬움(LIBERO 스택 재사용) |
| LIBERO-PRO (2510.03827) | π0·π0.5 공식, 위치 섭동에서 붕괴(그림) | OpenVLA | 같음 | 미확인 | 쉬움 |
| **SimplerEnv WidowX/Bridge** | π0 27.1(StarVLA 인용)~, π0-FAST 48.3, π0.5 약 55–57(제3자) | OFT, GR00T N1.6(공식 체크포인트), Octo, RT-1-X | 3인칭(base_link 고정), 손목 없음, 한 팔 | MIT | **이미 연결됨** |
| SimplerEnv Google Robot | π0 VM 58.8, π0-FAST 61.9(제3자 표) | OFT, GR00T, RT-1 | 머리, 한 팔 | MIT | 끝남(E-SIM0) |
| RoboTwin 2.0 (2506.18088) | π0 46.4/16.4(저자), π0.5 약 83/77(미확인) | RDT, DP3, ACT, DP | 머리 + 양손목, **양팔** | MIT | SAPIEN3 lavapipe 확인 필요, 한 팔 과제만 |
| RoboCasa365 | π0.5 16.9, π0 14.8(RoboCasa 팀 학습) | GR00T N1.5 23.9, DP | 베이스 고정 + 손목, 한 팔 | 코드 MIT, 자산 CC BY | 중간(미세조정 체크포인트 공개 미확인) |
| CALVIN ABC→D | π0 3.87, π0.5 4.02(제3자, 미확인) | OpenVLA 3.27, OFT 4.10 | 고정 3인칭 + 그리퍼, 한 팔 | MIT(미확인) | 큼(데이터·미세조정) |
| Meta-World | π0 47.9~50.5(SmolVLA 표) | TinyVLA, DP | 3인칭, 한 팔 | MIT | 중간(체크포인트 없음) |
| ManiSkill3 | π0 41.6→85.7, π0.5 40.0→84.8(πRL; RLinf 체크포인트) | — | 고정, 한 팔 | Apache-2.0 | SAPIEN3 확인 필요 |
| VLABench | π0 37.8, π0-FAST 34.1(X-VLA 표) | GR00T | — | 미확인 | 중간 |
| DROID sim-evals / PolaRiS (2512.16881) | 공식 pi0-FAST-DROID, pi05_droid 무학습 | — | 외부 + 손목, Franka 한 팔 | 미확인 | Isaac(render_float 필요) |
| BEHAVIOR-1K 2025 | 1·2등이 π0.5 기반, SR 12.4 % | — | 머리 + 양손목, 이동형 양팔 | MIT + EULA | 가장 큼 |
| ALOHA sim (gym-aloha) | `pi0_aloha_sim`(공식 수치 없음) | — | top 캠, **양팔(전달·삽입)** | Apache-2.0 | 한 팔 과제 없음 → 우리 팔은 '해당 없음', π0만 기준치 |

## C. 실기 전용(재현 불가)
- π0·π0.5·π*0.6 논문 실기 평가, RoboArena, KI의 DROID·모바일, FAST의 DROID 무학습 평가.

## D. 실행 순서(빠른 것부터, 각 벤치 사전 등록 → 시범 → 결과)
1. **E-SIM1 SimplerEnv WidowX/Bridge**: 우리 vs π0.5 base(무학습). 참고는 공개 수치, 공개 체크포인트(open-pi-zero π0 Bridge·GR00T N1.6 bridge)는 다음 변경으로 붙인다.
2. **E-LIB1 LIBERO에 π0·π0-FAST 공식 체크포인트 추가**: 같은 200편, FAST 논문 표 재현.
3. **E-LIBP LIBERO-Plus**(섭동 7종): 우리(Ab 설정) vs π0.5-LIBERO·π0·π0-FAST 공식.
4. ALOHA sim: π0 기준치만 잰다(우리 팔은 양팔 과제라 해당 없음).
5. DROID sim-evals(Isaac, render_float), RoboTwin 2.0 한 팔 과제(SAPIEN3 렌더 확인 뒤), Meta-World, RoboCasa 순.
6. LIBERO 미세조정 분기는 맨 마지막이다.
