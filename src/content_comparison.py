"""Lossless comparison helpers; whitespace folding classifies, never rewrites source."""
from difflib import SequenceMatcher
import json
import re

from src.source_contracts import digest


def compare_fields(original, official):
    """Offsets in differences are relative to each *field*, not to a source file."""
    differences = []
    for op, a, b, c, d in SequenceMatcher(None, original, official, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        left, right = original[a:b], official[c:d]
        differences.append({"operation": op, "input_field_start": a, "input_field_end": b,
                            "pdf_field_start": c, "pdf_field_end": d,
                            "input_fragment": left, "pdf_fragment": right,
                            "classification": "format_whitespace" if not left.strip() and not right.strip()
                            else "content_or_alignment_needs_review"})
    fold = lambda s: re.sub(r"\s+", " ", s).strip()
    return {"input_text": original, "pdf_text": official,
            "input_sha256": digest(original.encode("utf8")), "pdf_sha256": digest(official.encode("utf8")),
            "classification": "exact" if original == official else
            "format_only" if fold(original) == fold(official) else "content_difference",
            "differences": differences, "offset_namespace": "field_relative_unicode_code_point"}


def select_interval(text, selector):
    """Unique literal anchors on a newly extracted page; no imported numeric offsets."""
    anchor = selector["start"]
    if not anchor or text.count(anchor) != 1:
        raise ValueError("Missing/ambiguous start anchor")
    a = text.index(anchor) + (len(anchor) if selector.get("after_start", False) else 0)
    end = selector.get("end")
    if end is None:
        b = len(text)
    else:
        # A newline may occur repeatedly: it explicitly means the next line boundary.
        if end != "\n" and text[a:].count(end) != 1:
            raise ValueError("Missing/ambiguous end anchor")
        b = text.index(end, a) + (len(end) if selector.get("include_end", False) else 0)
    if not 0 <= a < b <= len(text):
        raise ValueError("Empty/reversed selection")
    return a, b


def render_comparison(rows):
    lines = ["# Đối chiếu DOCX legacy / extraction PDF mới", "",
             "Kết luận agent, chưa có quyết định reviewer. Offsets trong bảng diff tương đối trong field; mapping.pending.jsonl giữ offsets extraction tuyệt đối và trang PDF riêng."]
    for r in rows:
        lines += ["", "## " + r["citation"] + " — " + r["field"], "",
                  "Kết quả: " + r["classification"] + "; khớp comparison trước: " + str(r["previous_comparison_reproduced"]),
                  "", "DOCX legacy:", "```text", r["input_text"], "```", "PDF (giữ nguyên LF):", "```text", r["pdf_text"], "```", "",
                  "| Thao tác | DOCX field [start,end) | PDF field [start,end) | DOCX fragment JSON | PDF fragment JSON | Loại |",
                  "|---|---|---|---|---|---|"]
        for d in r["differences"]:
            lines.append(f"| {d['operation']} | [{d['input_field_start']},{d['input_field_end']}) | [{d['pdf_field_start']},{d['pdf_field_end']}) | {json.dumps(d['input_fragment'],ensure_ascii=False)} | {json.dumps(d['pdf_fragment'],ensure_ascii=False)} | {d['classification']} |")
        if not r["differences"]:
            lines.append("| Không khác | — | — | — | — | exact |")
    return "\n".join(lines) + "\n"
