"""Option naming variants A0-A4 (canon §27, E §2A.3 (i)); answers are always counted by option_key (R5)."""
import random
import string
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Option:
    key: str  # canonical meaning (option_key)
    name: str  # name shown to the model
    desc: str


NE = "NONE_ESCALATE"


def variant(opts, v, seed):
    body = [o for o in opts if o.key != NE]
    tail = [o for o in opts if o.key == NE]
    if v == "A0":
        out = body
    elif v == "A1":
        out = [replace(o, name=f"opt_{string.ascii_lowercase[i]}") for i, o in enumerate(body)]
    elif v == "A2":
        rng = random.Random(seed)
        names: list[str] = []
        while len(names) < len(body):
            n = "".join(rng.choice(string.ascii_lowercase) for _ in range(5))
            if n not in names:
                names.append(n)
        out = [replace(o, name=n) for o, n in zip(body, names)]
    elif v == "A3":
        out = [replace(o, name=body[(i + 1) % len(body)].name) for i, o in enumerate(body)]
    elif v == "A4":
        out = body[1:] + body[:1]
    else:
        raise ValueError(v)
    return list(out) + tail


def to_option_key(shown, answer_name):
    for o in shown:
        if o.name == answer_name:
            return o.key
    raise KeyError(answer_name)


def layer(k, qtype):
    if qtype == "noul" or k <= 2:
        return "L2"
    return "L3_6" if k <= 6 else "L7_17"
