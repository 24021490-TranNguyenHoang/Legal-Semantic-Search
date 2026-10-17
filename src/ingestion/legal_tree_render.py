"""Deterministic human-readable views of pending units; no source rewriting."""
from collections import defaultdict
import json

from src.ingestion.legal_tree import LABELS


def readable_artifacts(output, examples):
    units = output["units"]
    by_id = {u["unit_id"]: u for u in units}
    spans = defaultdict(list)
    for span in output["spans"]:
        spans[span["unit_id"]].append(span)

    def block(unit, depth=0):
        pad = "  " * depth
        name = (LABELS[unit["unit_type"]] + " " + unit["designation"]).strip()
        lines = [pad + "- " + name + " [" + unit["unit_id"] + "]",
                 pad + "  parent_unit_id: " + str(unit["parent_unit_id"])]
        for field in ("title", "text_original"):
            lines.append(pad + "  " + field + ":")
            lines.extend(pad + "    " + line for line in unit[field].split("\n"))
        for s in spans[unit["unit_id"]]:
            lines.append(pad + f"  span {s['field_name']}#{s['span_order']} [{s['char_start']},{s['char_end']}) {s['extraction_id']} {s['locator_json']}")
        return lines

    artifacts, index = {}, []
    laws = list(dict.fromkeys(u["law_id"] for u in units))
    for number, law in enumerate(laws, 1):
        ref = f"trees/{number:02d}.txt"
        index.append({"law_id": law, "tree_ref": ref, "review_status": "pending"})
        lines = [law, "PENDING — technical tree only; no legal verification or release eligibility.",
                 "Each unit displays its own fields; descendants are separate units.", ""]
        for unit in (u for u in units if u["law_id"] == law):
            depth, parent = 0, by_id.get(unit["parent_unit_id"])
            while parent:
                depth += 1
                parent = by_id.get(parent["parent_unit_id"])
            lines.extend(block(unit, depth))
        lines.extend(["", "UNPROCESSED / NEEDS REVIEW (see normalized.txt and coverage.jsonl):"])
        for c in output["coverage"]:
            if c["law_id"] == law and c["category"] in {"unprocessed", "needs_review"}:
                lines.append(f"[{c['char_start']},{c['char_end']}) {c['category']} {c['reason']} " + json.dumps(c["locator"], ensure_ascii=False, sort_keys=True))
        lines.append("SOURCE WARNINGS STILL PENDING:")
        for q in output["warning_reviews"]:
            if q["law_id"] == law:
                lines.append(q["source_issue_id"] + " " + q["code"] + " " + json.dumps(q["locator"], ensure_ascii=False, sort_keys=True))
        artifacts[ref] = "\n".join(lines) + "\n"
    artifacts["trees/index.json"] = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    lines = ["Stage 4 examples — PENDING", ""]
    for key, example in examples.items():
        lines.append(key + ": " + example["description"])
        if not example["units"]:
            lines.append("Not present in this input bundle; no fixture law is synthesized.")
        for entry in example["units"]:
            lines.extend(block(entry["unit"]))
        lines.append("")
    artifacts["examples.txt"] = "\n".join(lines) + "\n"
    return artifacts
