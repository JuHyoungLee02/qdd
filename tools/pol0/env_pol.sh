# E-POL0 PolaRiS environment (source it on the render-card pod): polaris venv (Isaac Lab 2.3 / Isaac Sim 5.0, torch cu130),
# libGL from conda (cv2 / iray), CUDA 13 toolkit + conda g++ 13 for the splat-rasterizer JIT (cached under /data).
# usage: source env_pol.sh <gpu> <code dir>
P=/data/harvest/polaris; TK=$P/cudatk
export CUDA_VISIBLE_DEVICES=$1 LD_LIBRARY_PATH=$P/gllibs HOME=/data/harvest/home TMPDIR=/data/harvest/tmp XDG_CACHE_HOME=$P/cache
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y CUDA_HOME=$TK PATH=$TK/bin:$P/.venv/bin:$PATH TORCH_EXTENSIONS_DIR=$P/cache/torch_ext
export CC=$TK/bin/x86_64-conda-linux-gnu-gcc CXX=$TK/bin/x86_64-conda-linux-gnu-g++ TORCH_CUDA_ARCH_LIST=9.0 MAX_JOBS=8
export PYTHONPATH=${2:-}:$P/src PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc_pol0
PY=$P/.venv/bin/python
