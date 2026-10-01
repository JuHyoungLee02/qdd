"""E-LIB0b: mesh-vertex z extents (base frame, mm relative to the TCP) of the gripper meshes (geom_rbound overestimates)."""
import numpy as np

from harvest.lib0.world import LiberoWorld

w = LiberoWorld("libero_spatial", 0)
w.reset(0)
sim = w.sim
M = sim.model._model
Rb, tb = w._base()
tcp = w.status()["tcp"]
for i in range(M.ngeom):
    n = sim.model.geom_id2name(i) or ""
    if n.startswith("gripper0_") and M.geom_type[i] == 7:
        mid = M.geom_dataid[i]
        V = M.mesh_vert[M.mesh_vertadr[mid]:M.mesh_vertadr[mid] + M.mesh_vertnum[mid]]
        R = np.array(sim.data.geom_xmat[i]).reshape(3, 3)
        P = (Rb.T @ ((V @ R.T) + np.array(sim.data.geom_xpos[i]) - tb).T).T
        print(n, "dz mm", round((P[:, 2].min() - tcp[2]) * 1e3, 1), round((P[:, 2].max() - tcp[2]) * 1e3, 1),
              "y mm", round((P[:, 1].min() - tcp[1]) * 1e3, 1), round((P[:, 1].max() - tcp[1]) * 1e3, 1))
