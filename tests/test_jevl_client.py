import asyncio
import json
import math

import httpx

from harvest.clients.jevl import JevLClient, option_probs, option_trie


def _q(names):
    return {"type": "choice", "instructions": "q", "criteria": {n: n + " desc" for n in names}}


END = 99


def _server(vocab, table, status=200):
    """vocab: name -> token ids; table: assistant prefix text -> {token_id: raw logprob}."""
    inv = {}
    for name, ids in vocab.items():
        # contiguous-substring detokenization for the fake tokenizer
        pos = 0
        for t in ids:
            inv.setdefault(t, name[pos:pos + 1] if len(ids) > 1 else name)
            pos += 1
    seen = []

    def handler(request):
        body = json.loads(request.content)
        path = request.url.path
        if path.endswith("/tokenize"):
            if body["prompt"] == "<|im_end|>":
                return httpx.Response(200, json={"tokens": [END]})
            return httpx.Response(200, json={"tokens": vocab[body["prompt"]]})
        if path.endswith("/detokenize"):
            return httpx.Response(200, json={"prompt": "".join(inv[t] for t in body["tokens"])})
        assert path.endswith("/chat/completions")
        seen.append(body)
        if status != 200:
            return httpx.Response(status, json={"error": "x"})
        assert body["max_tokens"] == 1 and body["logprobs"] is True
        last = body["messages"][-1]
        prefix = last["content"] if last["role"] == "assistant" else ""
        assert body["continue_final_message"] == (prefix != "")
        lp = table[prefix]
        tops = [{"token": f"token_id:{t}", "logprob": lp[t]} for t in body["logprob_token_ids"]]
        return httpx.Response(200, json={
            "model": "m", "usage": {"prompt_tokens": 500, "completion_tokens": 1},
            "choices": [{"logprobs": {"content": [{"token": tops[0]["token"], "logprob": tops[0]["logprob"],
                                                   "top_logprobs": tops}]}}]})
    return httpx.MockTransport(handler), seen


def _run(client, req, image=None):
    return asyncio.run(client.acall(req, {"experiment": "T"}, image=image))


def test_trie_branching_nodes_only():
    trie = option_trie({"a": [1, 2], "b": [1, 3], "c": [4], "d": [1, 2, 5]}, END)
    # root {1,4}; [1] {2,3}; [1,2] {END,5}; unique continuations are not scored
    assert trie == {(): {1, 4}, (1,): {2, 3}, (1, 2): {END, 5}}


def test_distinct_first_tokens_renormalize_over_option_set():
    vocab = {"up": [1], "down": [2], "none_z": [3, 7], "NONE_ESCALATE": [4, 8, 9]}
    table = {"": {1: math.log(0.6), 2: math.log(0.2), 3: math.log(0.1), 4: math.log(0.05)}}
    tr, seen = _server(vocab, table)
    c = JevLClient("http://x", "m", transport=tr)
    req = {"model": "m", "state": "s", "questions": {"ds1.dir_z": _q(vocab)}}
    r = _run(c, req)
    a = r.answers["ds1.dir_z"]
    assert a["choice"] == "up"
    assert abs(a["probabilities"]["up"] - 0.6 / 0.95) < 1e-9
    assert abs(sum(a["probabilities"].values()) - 1.0) < 1e-9
    assert abs(a["confidence"] - 0.6 / 0.95) < 1e-9 and abs(a["p_second"] - 0.2 / 0.95) < 1e-9
    assert len(seen) == 1  # one pass, no prefix sequences
    assert r.http_status == 200 and r.error is None and r.t_send <= r.t_first_byte <= r.t_done
    assert r.input_tokens == 500 and r.experiment == "T"


def test_shared_first_token_scores_full_string():
    vocab = {"px": [1, 2], "py": [1, 3], "pxpy": [1, 2, 5], "n": [4]}
    table = {"": {1: math.log(0.8), 4: math.log(0.2)},
             "p": {2: math.log(0.3), 3: math.log(0.1)},
             "px": {END: math.log(0.5), 5: math.log(0.5)}}
    tr, seen = _server(vocab, table)
    r = _run(JevLClient("http://x", "m", transport=tr), {"model": "m", "state": "s", "questions": {"q": _q(vocab)}})
    p = r.answers["q"]["probabilities"]
    # constrained-to-set: product of softmax over children at each branching node
    assert abs(p["n"] - 0.2) < 1e-9
    assert abs(p["py"] - 0.8 * 0.25) < 1e-9
    assert abs(p["px"] - 0.8 * 0.75 * 0.5) < 1e-9 and abs(p["pxpy"] - 0.8 * 0.75 * 0.5) < 1e-9
    assert len(seen) == 3


def test_option_probs_pure():
    trie = option_trie({"a": [1], "b": [2]}, END)
    p = option_probs({"a": [1], "b": [2]}, trie, {(): {1: 0.0, 2: math.log(0.25)}}, END)
    assert abs(p["a"] - 0.8) < 1e-9 and abs(p["b"] - 0.2) < 1e-9


def test_image_sent_and_http_error_recorded():
    vocab = {"up": [1], "down": [2]}
    tr, seen = _server(vocab, {"": {1: -1.0, 2: -2.0}})
    _run(JevLClient("http://x", "m", transport=tr), {"model": "m", "state": "s", "questions": {"q": _q(vocab)}},
         image=b"\x89PNG")
    content = seen[0]["messages"][-1]["content"]
    assert content[0]["type"] == "image_url" and content[0]["image_url"]["url"].startswith("data:image/png;base64,")
    tr2, _ = _server(vocab, {"": {1: -1.0, 2: -2.0}}, status=500)
    r = _run(JevLClient("http://x", "m", transport=tr2), {"model": "m", "state": "s", "questions": {"q": _q(vocab)}})
    assert r.http_status == 500 and r.error == "http_500" and r.answers == {}


def test_acall_mm_layout_H_matches_legacy_body_and_HW_labels_images():
    vocab = {"px": [1, 2], "py": [1, 3], "n": [4]}
    table = {"": {1: math.log(0.8), 4: math.log(0.2)}, "p": {2: math.log(0.3), 3: math.log(0.1)}}
    req = {"model": "m", "state": "s", "questions": {"q": _q(vocab)}}
    tr, seen = _server(vocab, table)
    c = JevLClient("http://x", "m", transport=tr, image_mime="image/jpeg")
    r = asyncio.run(c.acall_mm(req, {}, [("head camera:", b"H")], mode="base", layout="H"))
    legacy = c._body(req, "q", req["questions"]["q"], "", {1, 4}, b"H")
    assert seen[0]["messages"] == legacy["messages"]  # layout H == the stage-A training prompt
    assert r.answers["q"]["choice"] == "py" or r.answers["q"]["choice"] == "px"
    tr2, seen2 = _server(vocab, table)
    c2 = JevLClient("http://x", "m", transport=tr2, image_mime="image/jpeg")
    r2 = asyncio.run(c2.acall_mm(req, {}, [("head camera:", b"H"), ("right wrist camera (active arm):", b"W")],
                                 mode="lead", layout="HW"))
    content = seen2[0]["messages"][1]["content"]
    assert [p["type"] for p in content] == ["text", "image_url", "text", "image_url", "text"]
    assert content[0]["text"] == "head camera:" and content[2]["text"] == "right wrist camera (active arm):"
    assert r2.meta["mode"] == "lead" and r2.meta["layout"] == "HW" and len(seen2) == 2
    assert abs(r2.answers["q"]["probabilities"]["n"] - 0.2) < 1e-9
