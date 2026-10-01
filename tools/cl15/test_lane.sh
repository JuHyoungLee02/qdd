#!/bin/bash
# CPU test of the real lane.sh (no Isaac, no GPU, no API): a throwaway code dir whose teach_strip8/isaac.sh is a stub
# that eats stdin and logs the episode file it was given; a throwaway root with a copy of a jobs file + its eps files.
# PASS = every job in the list was claimed and its eps file existed, DONE written. GPU_FREED is redirected.
# usage: test_lane.sh <code dir> <source root> <jobs file name> <ckpt>
C=$1; SRC=$2; JF=$3; CK=$4
T=$(mktemp -d /data/harvest/out/cl15_lanetest.XXXX); FC=$T/code; R=$T/cl15lt
mkdir -p $FC/tools/teach_strip8 $FC/tools/cl15 $R
cp $C/tools/cl15/lane.sh $FC/tools/cl15/
sed -i "s#/data/harvest/out/l9/GPU_FREED#$T/GPU_FREED#; s#/data/harvest/venv_train/bin/python \$C/tools/cl15/summary.py.*#true#" $FC/tools/cl15/lane.sh
cat > $FC/tools/teach_strip8/isaac.sh <<'EOF'
#!/bin/bash
head -c 200 > /dev/null   # eats stdin like a child that reads it
for ((i=1; i<=$#; i++)); do [ "${!i}" = "--episodes" ] && { j=$((i+1)); E=${!j}; }; done
mkdir -p /data/harvest/logs/strip8
if [ -f "$E" ]; then echo "STUB found $E" >> $TESTLOG; else echo "STUB MISSING $E" >> $TESTLOG; fi
echo "EXIT 0" >> /data/harvest/logs/strip8/$3.log
EOF
cp $SRC/$JF $SRC/eps_*.json $R/
touch $R/LANES_GO_7a2a_9
TESTLOG=$T/stub.log CL15_ROOT=$R CL15_CKPT=$CK CL15_JOBS=$R/$JF CL15_VID=$T/vid bash $FC/tools/cl15/lane.sh $FC 9 t_l1 http://x x < /dev/null
n=$(wc -l < $R/$JF); f=$(grep -c "STUB found" $T/stub.log 2>/dev/null); m=$(grep -c MISSING $T/stub.log 2>/dev/null)
cat $T/stub.log
echo "jobs=$n found=$f missing=$m claims=$(ls $R/claims | wc -l) done=$([ -f $R/DONE ] && echo yes)"
[ "$n" = "$f" ] && [ "$m" = 0 ] && [ -f $R/DONE ] && echo PASS || { echo FAIL; exit 1; }
