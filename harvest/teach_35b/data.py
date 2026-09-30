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
    """The row's format. E-PT / E-DIST8 rows carry their arm name ('pt' = D track, 'nd-xyz' with h_mode = H track,
    ...): they use the solo layout (as harvest.teach_l8.train does) and the parser of their track (label_problems)."""
    return row.get("format", SOLO)


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
    f = row_format(row)
    if f == SOLO or "h_mode" in row or f == "pt":
        if "h_mode" in row:
            from ..astra_solo.hybrid import validate
            parsed, err = validate(row["answer"])
        elif f == "pt":
            from ..astra_solo.pt_schema import validate
            parsed, err = validate(row["answer"], allow_eef=True)
        else:
            from ..astra_solo.schema import validate
            parsed, err = validate(row["answer"])
        return [] if parsed is not None else [str(e) for e in err][:4]
    if f != COUPLE:
        return []  # other E-PT arm formats: checked by their builder
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


GROUPS = ("sim_control", "sim_aux", "open", "mixed")


def row_group(row: dict) -> str:
    """Loss-logging group: open point rows carry their public 'source'; the rest are simulator (L8S) rows."""
    if row.get("source"):
        return "open"
    return "sim_control" if row.get("kind") == "control" else "sim_aux"


def mb_group(groups: list) -> str:
    """A micro-batch's group: the common group of its rows, else 'mixed' (its loss is not split per row)."""
    return groups[0] if len(set(groups)) == 1 else "mixed"
