"""Quick environment check on a new pod: torch + CUDA devices, transformers / peft import, a small matmul per GPU.
usage: python env_check.py"""
import json

import torch

out = {"torch": torch.__version__, "cuda": torch.cuda.is_available(), "n_gpu": torch.cuda.device_count()}
for i in range(torch.cuda.device_count()):
    x = torch.randn(1024, 1024, device=f"cuda:{i}")
    out[f"gpu{i}"] = [torch.cuda.get_device_name(i), round(float((x @ x).sum().abs().item()) > 0, 0)]
import peft  # noqa: E402
import transformers  # noqa: E402
out.update(transformers=transformers.__version__, peft=peft.__version__)
print(json.dumps(out))
