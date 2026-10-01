#!/bin/bash
# (laptop) Copy the committed tree (git archive, LF) of HEAD -- harvest tools tests third_party -- to the pod code dir
# /data/harvest/l9v2robot/code, then overlay uncommitted files given as arguments (CR stripped).
# usage: tools/l9/v2robot/deploy.sh [extra files...]   (run from the worktree root)
set -e
export MSYS_NO_PATHCONV=1
POD=juhyoung-native-7a2a; C=/data/harvest/l9v2robot/code
git -c safe.directory=* -c core.autocrlf=false archive --format=tar HEAD -- harvest tools tests third_party \
  | kubectl exec -i -n p-test2 $POD -- bash -c "rm -rf $C.new && mkdir -p $C.new && tar -x -C $C.new && rm -rf $C && mv $C.new $C"
for f in "$@"; do
  tr -d '\r' < "$f" | kubectl exec -i -n p-test2 $POD -- bash -c "mkdir -p $C/$(dirname $f) && cat > $C/$f"
done
kubectl exec -n p-test2 $POD -- bash -c "chmod +x $C/tools/l9/v2robot/*.sh 2>/dev/null; ls $C | head"
