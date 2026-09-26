#!/bin/bash
# L8X-assets: fetch the CC BY 4.0 MolmoSpaces Isaac USD subsets (THOR objects, iTHOR scenes) to /data only.
# Objaverse subsets are NOT fetched (per-object licences, some CC BY-NC). Token from /data/.hf_token (never echoed).
# usage: fetch_molmospaces.sh   -> /data/harvest/assets_x/molmospaces/{objects_thor,scenes_ithor}
set -euo pipefail
D=/data/harvest/assets_x/molmospaces
H=https://huggingface.co/datasets/allenai/molmospaces/resolve/main/isaac
mkdir -p $D
df -h /data | tail -1
TOK=$(cat /data/.hf_token)
get() { # $1 remote path, $2 local file
  [ -s "$2" ] && { echo "have $2"; return; }
  curl -sfL -H "Authorization: Bearer $TOK" "$H/$1" -o "$2.part" && mv "$2.part" "$2" && ls -la "$2"
}
for s in objects/thor/20260128:objects_thor scenes/ithor/20260121:scenes_ithor; do
  r=${s%%:*}; n=${s##*:}; mkdir -p $D/$n
  for f in arrow_table.json mjthor_resource_file_to_size_mb.json mjthor_resources_combined_meta.json.gz shards/00000.tar; do
    get $r/$f $D/$n/$(basename $f)
  done
done
