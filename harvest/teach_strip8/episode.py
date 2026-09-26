"""E-STRIP8 closed-loop episode (prereg_strip8.md §5.3): the E-PT nd-xyz episode (ring-only head image, v2 eef /
edit / gripper / stop, same executor, limits and saving) whose request is the minimal one (strip.minimal: no table
height, grid, drop line, object sizes or recipes). Nothing else changes; the answer schema is the v2 / nd-xyz one."""
from __future__ import annotations

from ..astra_solo.pt_episode import PtEpisode
from . import strip as S


class StripEpisode(PtEpisode):
    def __init__(self, world, model, seed, task, out_dir=None, **kw):
        kw.pop("iface", None)
        super().__init__(world, model, seed, task, out_dir, iface="nd-xyz", **kw)
        self.prompt_id = S.PROMPT_ID

    def _request(self, obs, i, statics):
        text, ims = super()._request(obs, i, statics)
        return S.minimal(text), ims

    def _save(self, res):
        v, f = self.version, self.iface  # nd-xyz@v1 is still the schema used by _validate
        self.version, self.iface = S.VERSION, "s-min"
        try:
            super()._save(res)
        finally:
            self.version, self.iface = v, f
