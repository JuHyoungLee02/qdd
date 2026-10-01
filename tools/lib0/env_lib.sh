# E-LIB0 sim environment (source it): LIBERO venv (python 3.10) + CPU OSMesa (conda-forge mesalib < 25 -- 25+ dropped OSMesa -- llvmpipe, 1 thread),
# caches under /data. Usage: source env_lib.sh <code dir>  -> $PY
R=/data/harvest/lib0
export MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa LD_LIBRARY_PATH=$R/mesa24/lib LP_NUM_THREADS=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE
export LIBERO_CONFIG_PATH=$R/libero_cfg HOME=/data/harvest/home XDG_CACHE_HOME=$R/cache TMPDIR=/data/harvest/tmp
export MPLCONFIGDIR=/data/harvest/cache/mpl PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc_lib0 PYTHONPATH=${1:-$PWD}:$R/openpi/third_party/libero
PY=$R/venv_libero/bin/python
# E-LIBP: LIBERO-plus instead of LIBERO (LIB0_BENCH=plus): its venv, config and package path
if [ "${LIB0_BENCH:-}" = plus ]; then
  export LIBERO_CONFIG_PATH=$R/liberoplus_cfg PYTHONPATH=${1:-$PWD}:$R/LIBERO-plus
  export MAGICK_HOME=$R/imagick LD_LIBRARY_PATH=$R/mesa24/lib:$R/imagick/lib  # Wand (ImageMagick, conda-forge)
  PY=$R/venv_liberoplus/bin/python
fi
