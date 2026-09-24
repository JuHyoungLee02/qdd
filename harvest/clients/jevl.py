"""Jev-L client: local VLM (vLLM OpenAI server) as a typed selector (canon §44, D24 §3.1).

One JevCall/DecCall request -> per question, the option names are tokenized and put in a trie.
Every branching trie node becomes one chat sequence (max_tokens 1) that shares the prefix
[system][image][state][question] and reads raw logprobs of exactly the child tokens
(`logprob_token_ids`). p(option) = product over its branching nodes of the softmax over the
children = the probability renormalized inside the option set. Distinct first tokens -> one pass.
All sequences of one call are sent in parallel (prefix cache serves the shared part).
Returns a CallRecord (same shape as the Jev client).
"""
from __future__ import annotations

import asyncio
import base64
import math
import time
import uuid

import httpx

from ..config import CFG
from .jev import CallRecord

SYSTEM = ("You are the fast typed decision selector of a robot manipulator. "
          "Read the state (and the head-camera image if given) and answer the question "
          "with exactly one option name from the list and nothing else.")


def option_trie(tok, end):
    """tok: name -> token ids. Returns {prefix tuple: set of child ids} for branching nodes only."""
    kids: dict[tuple, set] = {}
    for ids in tok.values():
        for i in range(len(ids) + 1):
            kids.setdefault(tuple(ids[:i]), set()).add(ids[i] if i < len(ids) else end)
    if len({tuple(v) for v in tok.values()}) != len(tok):
        raise ValueError("two options share one token sequence")
    return {k: v for k, v in kids.items() if len(v) >= 2}


def option_probs(tok, trie, node_lp, end):
    """node_lp: prefix -> {child id: raw logprob}. Product of per-node softmax over children."""
    out = {}
    for name, ids in tok.items():
        lp = 0.0
        for i in range(len(ids) + 1):
            pre = tuple(ids[:i])
            if pre not in trie:
                continue
            nxt = ids[i] if i < len(ids) else end
            m = node_lp[pre]
            mx = max(m.values())
            lp += m[nxt] - mx - math.log(sum(math.exp(v - mx) for v in m.values()))
        out[name] = math.exp(lp)
    return out


def question_text(state, qid, q):
    opts = "\n".join(f"- {n}: {d}" for n, d in q["criteria"].items())
    return (f"{state}\n\nQuestion ({qid}): {q['instructions']}\nOptions:\n{opts}\n"
            "Answer with exactly one option name from the list.")


class JevLClient:
    def __init__(self, base_url, model, transport=None, timeout_s=CFG.timeout_s, end_token="<|im_end|>",
                 image_mime="image/png"):
        self.base, self.model, self.end_token, self.mime = base_url.rstrip("/"), model, end_token, image_mime
        self._c = httpx.AsyncClient(timeout=timeout_s, transport=transport)
        self._tok: dict[str, list[int]] = {}
        self._detok: dict[tuple, str] = {}
        self._end: int | None = None

    async def aclose(self):
        await self._c.aclose()

    async def _tokenize(self, s):
        if s not in self._tok:
            r = await self._c.post(f"{self.base}/tokenize",
                                   json={"model": self.model, "prompt": s, "add_special_tokens": False})
            r.raise_for_status()
            self._tok[s] = list(r.json()["tokens"])
        return self._tok[s]

    async def _detokenize(self, ids):
        if not ids:
            return ""
        if ids not in self._detok:
            r = await self._c.post(f"{self.base}/detokenize", json={"model": self.model, "tokens": list(ids)})
            r.raise_for_status()
            self._detok[ids] = r.json()["prompt"]
        return self._detok[ids]

    async def plan(self, req):
        """Per question: (token map, trie, {prefix: prefix text}). Cached tokenizer calls."""
        if self._end is None:
            e = await self._tokenize(self.end_token)
            if len(e) != 1:
                raise ValueError(f"end token {self.end_token!r} is not one token: {e}")
            self._end = e[0]
        out = {}
        for qid, q in req["questions"].items():
            tok = {n: await self._tokenize(n) for n in q["criteria"]}
            trie = option_trie(tok, self._end)
            out[qid] = (tok, trie, {pre: await self._detokenize(pre) for pre in trie})
        return out

    def _body(self, req, qid, q, prefix_text, kids, image):
        user = [{"type": "text", "text": question_text(req["state"], qid, q)}]
        if image is not None:
            url = f"data:{self.mime};base64," + base64.b64encode(image).decode()
            user.insert(0, {"type": "image_url", "image_url": {"url": url}})
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        cont = prefix_text != ""
        if cont:
            msgs.append({"role": "assistant", "content": prefix_text})
        return {"model": self.model, "messages": msgs, "max_tokens": 1, "temperature": 0.0,
                "logprobs": True, "logprob_token_ids": sorted(kids), "return_tokens_as_token_ids": True,
                "continue_final_message": cont, "add_generation_prompt": not cont}

    async def acall(self, req, meta, image=None) -> CallRecord:
        r = CallRecord(call_id=uuid.uuid4().hex, raw_request=req, meta=dict(meta),
                       experiment=meta.get("experiment", ""), condition=meta.get("condition", ""),
                       seed=meta.get("seed"))
        plans = await self.plan(req)
        jobs = [(qid, pre, self._body(req, qid, req["questions"][qid], ptxt[pre], trie[pre], image))
                for qid, (tok, trie, ptxt) in plans.items() for pre in trie]
        first = []

        async def one(body):
            resp = await self._c.post(f"{self.base}/v1/chat/completions", json=body)
            if not first:
                first.append(time.monotonic())
            return resp

        r.t_send = time.monotonic()
        try:
            resps = await asyncio.gather(*(one(b) for _, _, b in jobs))
        except httpx.TimeoutException:
            r.t_done = time.monotonic()
            r.t_first_byte = first[0] if first else r.t_done
            r.error = "timeout"
            return r
        except httpx.HTTPError as e:
            r.t_done = time.monotonic()
            r.t_first_byte = first[0] if first else r.t_done
            r.error = type(e).__name__
            return r
        r.t_done = time.monotonic()
        r.t_first_byte = first[0]
        bad = [x.status_code for x in resps if x.status_code != 200]
        r.http_status = bad[0] if bad else 200
        if bad:
            r.error = f"http_{bad[0]}"
            r.raw_response = {"error_body": resps[[x.status_code for x in resps].index(bad[0])].text[:2000]}
            return r
        node_lp: dict[str, dict] = {qid: {} for qid in plans}
        ptoks = []
        for (qid, pre, _), x in zip(jobs, resps):
            d = x.json()
            ptoks.append(d.get("usage", {}).get("prompt_tokens"))
            r.model = d.get("model")
            tops = d["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
            node_lp[qid][pre] = {int(t["token"].split(":", 1)[1]): t["logprob"] for t in tops}
        r.model_ok = r.model == self.model
        r.input_tokens = max(p for p in ptoks if p is not None) if any(p is not None for p in ptoks) else None
        r.output_tokens = len(jobs)
        for qid, (tok, trie, _) in plans.items():
            p = option_probs(tok, trie, node_lp[qid], self._end)
            ranked = sorted(p.items(), key=lambda kv: -kv[1])
            r.answers[qid] = {"choice": ranked[0][0], "probabilities": p, "confidence": ranked[0][1],
                              "p_second": ranked[1][1] if len(ranked) > 1 else 0.0, "n_seq": len(trie)}
        r.raw_response = {"n_seq": len(jobs), "prompt_tokens": ptoks}
        return r
