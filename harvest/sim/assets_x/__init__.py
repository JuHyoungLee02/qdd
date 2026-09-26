"""L8X-assets: furniture / scene assets for the L8-X environment suite (board: L8X-assets, helper of L8D).

surfaces.py   support surfaces from a triangle mesh (pure numpy): top heights, free boxes, cover, container rims
furniture.py  parametric furniture kinds (tables, counters, shelves, low tables, bins, stands, multi-level) and
              licensed mesh furniture from assets_table.json -> sample_scene(kind, seed)
reach.py      reachable / visible placement regions from the L8-D reach probe and the head camera
isaac.py      pod only: spawn a sample_scene dict as static colliders into an Isaac Lab scene
"""
