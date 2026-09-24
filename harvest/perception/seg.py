"""SAM 3.1 text-prompted image segmentation (venv_sam3, pod only).

The image model is the SAM 3.1 checkpoint's detector (build_sam3_image_model loads the `detector.*` weights of
sam3.1_multiplex.pt): one image encoder pass per frame, then one grounding pass per detect_phrase (canon §46).
Per-frame detection, no video memory (the tracker is not used here; the Tracker in fuse.py only holds the last
estimate). bf16 autocast.
"""
from __future__ import annotations

import time

import numpy as np

SAM31_CKPT = "/data/harvest/models/sam3.1/sam3.1_multiplex.pt"

# Stand-in for Astra's detect_phrase (M2 contract objects, canon §46): a fixed table, chosen once on probe frames
# (r1_perception.md §2) and then frozen.
PHRASE_CANDIDATES = {"o3": ("red mug", "red cup", "red cylinder"),
                     "o5": ("blue tray", "blue plate", "blue board"),
                     "o8": ("green bottle", "green cylinder"),
                     "o9": ("yellow box", "yellow block"),
                     "o10": ("purple box", "purple block")}


class Sam31Image:
    def __init__(self, ckpt: str = SAM31_CKPT, thr: float = 0.3, device: str = "cuda"):
        import torch
        from sam3.model.sam3_image_processor import Sam3Processor
        from sam3.model_builder import build_sam3_image_model
        self.torch = torch
        self.model = build_sam3_image_model(checkpoint_path=ckpt, load_from_HF=False, device=device)
        self.proc = Sam3Processor(self.model, device=device, confidence_threshold=thr)
        self._text_cache = {}

    def segment(self, img: np.ndarray, phrases, cache_text: bool = False) -> tuple[dict, dict]:
        """{phrase: [(score, mask HxW bool), ...] best first}, timings {encode_ms, ground_ms}.
        cache_text: reuse each phrase's text-encoder output (phrases change only when Astra renames an object) --
        a latency diagnostic added after the pre-registered run (r1_perception.md §3)."""
        torch = self.torch
        out = {}
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            st = self.proc.set_image(torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1))
            torch.cuda.synchronize()
            t1 = time.perf_counter()
            for ph in phrases:
                self.proc.reset_all_prompts(st)
                if cache_text:
                    if ph not in self._text_cache:
                        self._text_cache[ph] = self.model.backbone.forward_text([ph], device=self.proc.device)
                    st["backbone_out"].update(self._text_cache[ph])
                    st["geometric_prompt"] = self.model._get_dummy_prompt()
                    st = self.proc._forward_grounding(st)
                else:
                    st = self.proc.set_text_prompt(ph, st)
                sc = st["scores"].float().cpu().numpy()
                ms = st["masks"][:, 0].cpu().numpy()
                order = np.argsort(-sc)
                out[ph] = [(float(sc[i]), ms[i]) for i in order]
            torch.cuda.synchronize()
            t2 = time.perf_counter()
        return out, {"encode_ms": (t1 - t0) * 1e3, "ground_ms": (t2 - t1) * 1e3}
