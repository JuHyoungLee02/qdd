# E-POL0 PolaRiS(DROID) — 보류 기록 (2026-10-02 06:5x KST)

- 목적: PolaRiS(arXiv 2512.16881, arhanjain/polaris 129abc4, MIT, 별 236)의 DROID 6과제 × 100 초기 조건. 공식 체크포인트(π0.5·π0·π0-FAST·PaliGemma polaris)와 우리 상위를 같은 조건에서 비교하려 했다.
- **설치까지 됨**:
  - `/data/harvest/polaris`: uv venv, Isaac Lab 2.3, Isaac Sim 5.1, torch 2.14 cu130. PolaRiS-Hub 자산 1.7 GB.
  - CUDA 13 툴킷과 g++ 13은 conda로 `/data/harvest/polaris/cudatk`에 깔았다.
  - 2DGS 스플랫 확장(diff-surfel-rasterization, simple-knn)은 C++17 고정이라 torch 2.14와 맞지 않았다. `-std=c++20`으로 고쳐 JIT 컴파일 캐시를 만들었다(원본은 `*.orig_cxx17`로 보존).
  - libGL(conda)과 ninja를 추가했다.
- **막힌 곳**(render_float x2 GPU1을 두 번, 1시간 한도 안에서 빌림):
  - Isaac Sim 5.1의 `carb.graphics-vulkan`이 vkCreateInstance에 실패한다(로더 로그: `Could not get 'vkCreateInstance' via 'vk_icdGetInstanceProcAddr' for ICD libGLX_nvidia.so.0`). 그래서 GPU Foundation이 없고, PhysX도 "no suitable CUDA GPU"로 CPU로 넘어간다. 그 뒤 환경을 만드는 단계(충돌 메시 cooking 추정)에서 30분 넘게 멈춘다.
  - 파드에는 시스템 Vulkan 로더가 없다. conda 로더 1.4.357을 LD 경로와 LD_PRELOAD로 넣어도 같다. 같은 파드에서 같은 로더의 `vulkaninfo`는 H200을 정상으로 본다.
- 원인 후보(미검증): Isaac Sim 5.1이 파드 이미지(NVIDIA 드라이버 그래픽 구성요소, glvnd 판)와 맞지 않는다. 같은 파드의 L9 Isaac(다른 판본)은 렌더된다.
- 다음에 다시 할 때: L9의 Isaac 판본과 맞는 Isaac Lab 2.x로 PolaRiS를 맞추거나, PolaRiS가 Isaac Sim 5.1을 요구하면 그 판을 지원하는 파드 이미지를 사용자에게 요청한다.
- 카드는 반납했다(float9: 1,611 s 대여, L9 5 s 만에 복귀).

## 다시 할 때의 길(06:5x 확인, 미시험)
- L9 양산은 같은 파드에서 `/data/harvest/ir/ir_run.sh`(unshare + chroot)로 Isaac을 돌린다.
- 루트 파일 시스템은 `/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0`이고, **Isaac Sim 5.1.0 + Isaac Lab 2.3.0**(PolaRiS가 요구하는 판)이다. NVIDIA 그래픽 라이브러리는 `/data/juhyoung_infra/nvidia_libs`에서 바인드된다.
- 그래서 PolaRiS(파이썬 패키지 + 스플랫 확장)를 이 루트 파일 시스템의 파이썬에 얹어 `IR_ROOT=cyclo ir_run.sh`로 돌리면 Vulkan 문제를 피할 가능성이 높다. L9 v2 책임자와 맞춘 뒤 한다.
