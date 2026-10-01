# E-RC0 sim environment (source it): robocasa venv (= the robocasa-benchmark/openpi venv), CPU OSMesa, numba JIT off
# (numba 0.61 / LLVM segfaults compiling the placement sampler on the pods), neutral cwd (the /data/harvest/rc checkout
# would shadow the robocasa package). usage: source env_rc.sh <code dir>  -> $PY
R=/data/harvest/lib0
export MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa LD_LIBRARY_PATH=$R/mesa24/lib LP_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_DISABLE_JIT=1
export HOME=/data/harvest/home TMPDIR=/data/harvest/tmp PYTHONPATH=${1:-} PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc_rc0
PY=/data/harvest/rc/openpi/.venv/bin/python
cd /data/harvest/tmp
