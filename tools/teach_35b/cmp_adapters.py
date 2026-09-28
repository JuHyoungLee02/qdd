"""Compare LoRA adapters tensor by tensor (resume check): max |a - b| and whether every tensor is bit-identical.
usage: python cmp_adapters.py <adapter dir A> <adapter dir B> [<adapter dir C> ...]   (each against A)"""
import json
import os
import sys

from safetensors.torch import load_file

A = load_file(os.path.join(sys.argv[1], "adapter_model.safetensors"))
for d in sys.argv[2:]:
    B = load_file(os.path.join(d, "adapter_model.safetensors"))
    assert set(A) == set(B), "different tensor names"
    mx = max(float((A[k].float() - B[k].float()).abs().max()) for k in A)
    same = all(bool((A[k] == B[k]).all()) for k in A)
    scale = max(float(A[k].float().abs().max()) for k in A)
    print("CMP " + json.dumps({"a": sys.argv[1], "b": d, "tensors": len(A), "max_abs_diff": mx, "bit_identical": same,
                               "max_abs_value": scale}))
