#!/bin/bash
# main2: drop the relative-path queue lines for good (new inode; lanes that start later read the clean file), then
# unclaim jobs whose last run failed on that path (no episode was made) so a lane runs them with the absolute plan.
R=/data/harvest/l9v2/gab/main2
grep -v ' main/plan_gab.json ' $R/q.txt | awk '!seen[$0]++' > $R/q.txt.new && mv $R/q.txt.new $R/q.txt
n=0
for c in $(ls $R/claim); do
  [ -e $R/done/$c ] && continue
  f=$(ls -t /data/harvest/logs/l9/*_${c}.log 2>/dev/null | head -1)
  if [ -n "$f" ] && tail -3 "$f" | grep -q '^EXIT 1' && grep -q "No such file or directory: 'main/plan_gab.json'" "$f"; then
    rmdir $R/claim/$c && n=$((n + 1))
  fi
done
echo "unclaimed $n, queue $(wc -l < $R/q.txt)"
