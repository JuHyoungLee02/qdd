"""Which data files hold the episodes of each exterior_1_left / wrist_left video file (DROID lerobot v3 meta)."""
import collections
import pyarrow.parquet as pq

m = pq.read_table("/data/harvest/data/droid/meta/episodes/chunk-000/file-000.parquet",
                  columns=["episode_index", "data/file_index", "videos/observation.images.exterior_1_left/file_index",
                           "videos/observation.images.wrist_left/file_index"]).to_pylist()
c = collections.Counter((r["videos/observation.images.exterior_1_left/file_index"],
                         r["videos/observation.images.wrist_left/file_index"], r["data/file_index"]) for r in m)
for k in sorted(c)[:20]:
    print("ext1 video, wrist video, data file", k, "episodes", c[k])
