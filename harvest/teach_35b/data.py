"""E-TEACH-35B training rows: one JSONL format for the solo and the coupled upper-model interfaces.

Every row (teach_l8.dataset rows are valid as they are):
  id, kind            'control' (a runtime request -> its label) or 'aux' (perception QA)
  prompt_path|prompt  request text (control reads the file, aux carries it)
  images              image paths, in the order sent
  answer              the label text (the model learns exactly this string after the non-thinking prefix)
  format              'astra-solo@v2' (default when absent) or 'astra-couple@v2'
  image_labels        text part sent right before each image. Absent -> the solo LocalVLM layout
                      'Image k: head camera' / 'right wrist camera'. Coupled rows carry the production labels
                      ('cam_head:', 'cam_wrist_right:', ... = couple.prompt_v2.build -> local_vlm.to_chat).
  cameras, mode       coupled rows: the cameras sent (evidence views / claims are checked against them) and the
                      coupling mode (F0 default, F1)
The coupled answer = assessment (execution / intent / claims = the upper's verification: grasped or not) + segment
plan {now, do, next} (the upper's stated intent) + command continue | edit | stop (canon §90 / §96 supp 2).
label_problems runs the runtime parser of the row's format on control labels, so a label the runtime would reject
never reaches training."""
from __future__ import annotations

SOLO, COUPLE = "astra-solo@v2", "astra-couple@v2"
FORMATS = (SOLO, COUPLE)


def row_format(row: dict) -> str:
    f = row.get("format", SOLO)
    if f not in FORMATS:
        raise ValueError(f"row {row.get('id')}: format {f!r} not in {FORMATS}")
    return f


def request_text(row: dict) -> str:
    return row["prompt"] if row["kind"] == "aux" else open(row["prompt_path"], encoding="utf-8").read()


def user_content(text: str, row: dict) -> list:
    labels = row.get("image_labels")
    if labels is None:
        from ..teach_l8.dataset import user_content as solo
        return solo(text, len(row["images"]))
    if len(labels) != len(row["images"]):
        raise ValueError(f"row {row.get('id')}: {len(labels)} image labels for {len(row['images'])} images")
    out = [{"type": "text", "text": text}]
    for lab in labels:
        out += [{"type": "text", "text": lab}, {"type": "image"}]
    return out


def messages(row: dict, with_answer: bool) -> list:
    m = [{"role": "user", "content": user_content(request_text(row), row)}]
    if with_answer:
        m.append({"role": "assistant", "content": [{"type": "text", "text": row["answer"]}]})
    return m


def label_problems(row: dict) -> list:
    """[] when the runtime parser of the row's format accepts a control label (aux rows are not checked)."""
    if row.get("kind") != "control":
        return []
    if row_format(row) == SOLO:
        from ..astra_solo.schema import validate
        parsed, err = validate(row["answer"])
        return [] if parsed is not None else [str(e) for e in err][:4]
    from ..couple import schema as CS
    try:
        CS.parse_answer(row["answer"], row.get("mode", "F0"), row.get("cameras", []), 1, 0.0, 1.0, version="v2")
    except CS.SchemaError as e:
        return list(e.problems)[:4]
    return []


def check_rows(rows: list) -> dict:
    by, bad = {}, []
    for r in rows:
        f = row_format(r)
        by[f"{f}/{r['kind']}"] = by.get(f"{f}/{r['kind']}", 0) + 1
        p = label_problems(r)
        if p:
            bad.append({"id": r.get("id"), "problems": p})
    return {"counts": by, "invalid": len(bad), "invalid_first": bad[:5]}
