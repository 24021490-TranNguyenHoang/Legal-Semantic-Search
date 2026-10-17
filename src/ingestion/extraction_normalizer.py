"""Normalize reader fragments only; serialize with explicit structural separators."""
import unicodedata

from src.source_contracts import digest


def normalize_fragment(text):
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def serialize(tree):
    nodes, fragments, separators, output = [], [], [], []
    position = 0

    def visit(item, parent_index=None, child_order=0):
        nonlocal position
        index = len(nodes)
        record = {"node_index": index, "parent_index": parent_index, "child_order": child_order,
                  "kind": item["kind"], "locator": item["locator"], "char_start": position}
        nodes.append(record)
        if "raw_text" in item:
            raw = item["raw_text"]
            normalized = normalize_fragment(raw)
            output.append(normalized)
            position += len(normalized)
            fragments.append({"node_index": index, "raw_text": raw,
                              "raw_char_count": len(raw), "normalized_char_count": len(normalized),
                              "raw_sha256": digest(raw.encode("utf-8")),
                              "normalized_sha256": digest(normalized.encode("utf-8")),
                              "line_endings_changed": "\r" in raw,
                              "nfc_changed": unicodedata.normalize("NFC", raw) != raw,
                              "rules": ["CRLF_TO_LF", "CR_TO_LF", "UNICODE_NFC"]})
        else:
            for order, child in enumerate(item["children"]):
                if order:
                    sep = item["separator"]
                    separators.append({"parent_index": index, "before_child_order": order,
                                       "char_start": position, "char_end": position + len(sep),
                                       "text": sep, "rule": "CELL_TAB" if item["kind"] == "row" else "BLOCK_LF"})
                    output.append(sep)
                    position += len(sep)
                visit(child, index, order)
        record["char_end"] = position

    visit(tree)
    text = "".join(output)
    if text.startswith("\ufeff"):
        raise ValueError("Leading source U+FEFF needs an explicit policy; refusing silent BOM removal")
    for record in nodes:
        record["quote_sha256"] = digest(text[record["char_start"]:record["char_end"]].encode("utf-8"))
    return text, {"nodes": nodes, "fragments": fragments, "separators": separators}
