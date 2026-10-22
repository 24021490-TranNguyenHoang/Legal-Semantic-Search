"""Narrow official-HTML extraction/mapping of NĐ168 A16K2, scan-confirmed preview.

No general HTML parser, OCR, source promotion, retrieval or model inference.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import unicodedata

from src import chunk_preview_v2, encoder_input
from src.assessment_evidence import check_files, inventory, seal, now
from src.article22_preview import require_preview_schema
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.content_comparison import compare_fields
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion.extractors import node
from src.ingestion import extraction_normalizer
from src.ingestion.legal_tree import UNIT_FIELDS, unit_id, span_id, ALLOWED
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest, file_identity, require_contract, resolve_ref

VERSION = "nd168-a16k2-html.v1"
DEFAULT_CONFIG = BASE_DIR / "config/nd168_a16k2.v1.json"
LAW = "168/2024/NĐ-CP"
LABELS = {"chapter": "Chương", "section": "Mục", "article": "Điều", "clause": "Khoản", "point": "Điểm"}
BLOCKERS = ["SOURCE_EDITION_REVIEW_PENDING", "SCOPED_HTML_SCAN_AGENT_REVIEW_ONLY", "APPLICABILITY_PENDING",
            "NO_HUMAN_REVIEW_DECISION", "EXPERIMENTAL_PREVIEW_NOT_RELEASE_READY"]
EXPORTS = {"chunks": "chunks.preview.jsonl", "contexts": "contexts.preview.jsonl", "encoder_inputs": "encoder_inputs.jsonl",
           "issues": "issues.jsonl", "quarantined": "quarantined.preview.jsonl", "dependency_checks": "dependency_checks.jsonl",
           "unit_results": "unit_results.jsonl"}


def dom_text(element, *, strict=True):
    """Entity-decoded DOM text; explicit div/br boundaries become LF, no folding."""
    out = []
    def visit(e):
        if not isinstance(e.tag, str):
            return
        if e.tag in {"script", "style", "img", "svg", "iframe", "table", "object"}:
            if strict:
                raise ValueError("Unsupported content in a selected HTML block")
            return
        if e.tag in {"div", "br"} and out and not out[-1].endswith("\n"):
            out.append("\n")
        if e.text:
            out.append(e.text)
        for c in e:
            visit(c)
            if c.tail:
                out.append(c.tail)
    visit(element)
    return "".join(out)


def select_blocks(raw):
    from lxml import html
    doc = html.fromstring(raw)
    bodies = doc.xpath('//div[@itemprop="articleBody"]')
    if len(bodies) != 1 or "168/2024/NĐ-CP" not in "".join(doc.xpath('//h1//text()')):
        raise ValueError("Wrong/ambiguous official article body or decree number")
    body = [e for e in bodies[0] if isinstance(e.tag, str)]
    texts = [dom_text(e, strict=False) for e in body]
    matches = [i for i, t in enumerate(texts) if t.startswith("Điều 16. ")]
    if len(matches) != 1:
        raise ValueError("Missing/ambiguous Article 16 heading")
    i = matches[0]
    chapter = max(k for k in range(i) if texts[k].startswith("Chương "))
    section = max(k for k in range(chapter, i) if texts[k].startswith("Mục "))
    if texts[chapter].split("\n")[0] != "Chương II" or texts[section].split("\n")[0] != "Mục 2":
        raise ValueError("Unexpected real chapter/section")
    if [t.split("\n")[0] for t in texts[:chapter+1] if t.startswith("Chương ")] != ["Chương I", "Chương II"]:
        raise ValueError("Chapter source order is unclear")
    if [t.split("\n")[0] for t in texts[chapter:section+1] if t.startswith("Mục ")] != ["Mục 1", "Mục 2"]:
        raise ValueError("Section source order is unclear")
    if [re.match(r"Điều (\d+)\.", t)[1] for t in texts[section:i+1] if re.match(r"Điều (\d+)\.", t)] != ["13", "14", "15", "16"]:
        raise ValueError("Article ordinal cannot be established")
    end = next(k for k in range(i+1, len(texts)) if re.match(r"Điều \d+\.", texts[k]))
    leads = [k for k in range(i+1, end) if re.match(r"2\. Phạt tiền", texts[k])]
    if len(leads) != 1:
        raise ValueError("Missing/ambiguous clause 2")
    start = leads[0]
    if [re.match(r"(\d+)\. ", t)[1] for t in texts[i+1:start+1] if re.match(r"(\d+)\. ", t)] != ["1", "2"]:
        raise ValueError("Clause source ordinal cannot be established")
    stop = next(k for k in range(start+1, end) if re.match(r"3\. ", texts[k]))
    points = [k for k in range(start+1, stop) if texts[k].strip()]
    if [re.match(r"([a-zđ])\) ", texts[k])[1] if re.match(r"([a-zđ])\) ", texts[k]) else None for k in points] != list("abcdđ"):
        raise ValueError("Whole clause requires exactly a/b/c/d/đ; never infer missing points")
    if any(texts[k].strip() and not re.match(r"1\. |[a-zđ]\) ", texts[k]) for k in range(i+1, start)):
        raise ValueError("Unmapped article lead needs separate treatment")
    root = next(k for k in range(chapter) if texts[k].startswith("NGHỊ ĐỊNH\n"))
    chosen = [("document", root), ("chapter", chapter), ("section", section), ("article", i), ("clause", start)]
    chosen += [("point_" + p, k) for p, k in zip("abcdđ", points)]
    return [(key, body[k].getroottree().getpath(body[k]), dom_text(body[k])) for key, k in chosen]


def extract_html(raw, file_id):
    blocks = select_blocks(raw)
    tree = node("document", {"format": "html", "scope": "selected_structural_ancestors_and_A16K2"}, children=[
        node("paragraph", {"format": "html", "xpath": xpath, "selection_key": key}, raw_text=text)
        for key, xpath, text in blocks])
    text, trace = extraction_normalizer.serialize(tree)
    tool = canonical({"reader": VERSION, "python": platform.python_version(), "unicode": unicodedata.unidata_version,
                      "lxml": importlib.metadata.version("lxml"), "code_sha256": digest(Path(__file__).read_bytes()),
                      "normalizer_sha256": digest(Path(extraction_normalizer.__file__).read_bytes())})
    settings = {"reader": VERSION, "normalization": "NFC_LF_ONLY", "dom_blocks": "DIV_BR_TO_LF_INLINE_CONCAT",
                "selection": [k for k, _, _ in blocks], "structural_own_text": "unselected_empty_in_sparse_projection"}
    identity = {"identity_schema": "extraction.v1", "file_id": file_id, "source_raw_sha256": digest(raw),
                "method": "html_text", "tool_version": tool, "config_sha256": digest(canonical(settings).encode()),
                "text_sha256": digest(text.encode()), "trace_content_sha256": digest(canonical(trace).encode())}
    eid = "e_" + digest(canonical(identity).encode())
    for n in trace["nodes"]:
        n["extraction_id"] = eid
        n["locator_id"] = "l_" + digest(canonical({"extraction_id": eid, "node_index": n["node_index"], "locator": n["locator"]}).encode())
        p = n["parent_index"]
        n["parent_locator_id"] = None if p is None else trace["nodes"][p]["locator_id"]
    return text, trace, {"extraction_id": eid, "file_id": file_id, "method": "html_text", "tool_version": tool,
                         "text_ref": "extraction/normalized.txt", "text_sha256": identity["text_sha256"],
                         "char_count": len(text), "review_status": "pending"}


def map_units(text, trace):
    nodes = {n["locator"]["selection_key"]: n for n in trace["nodes"] if "selection_key" in n["locator"]}
    specs = [("document", None, "document", LAW, 0), ("chapter", "document", "chapter", "II", 1),
             ("section", "chapter", "section", "2", 1), ("article", "section", "article", "16", 3),
             ("clause", "article", "clause", "2", 1)] + [("point_"+p, "clause", "point", p, i) for i, p in enumerate("abcdđ")]
    keyed, units, spans = {}, [], []
    for key, parent_key, kind, designation, ordinal in specs:
        n = nodes[key]; parent = keyed.get(parent_key); a, b = n["char_start"], n["char_end"]
        field = "text_original" if kind in {"clause", "point"} else "title"
        if kind in {"chapter", "section"}:
            a = text.index("\n", a, b)+1
        elif kind == "article":
            a += len("Điều 16. ")
        u = {"law_id": LAW, "parent_unit_id": parent["unit_id"] if parent else None, "unit_type": kind,
             "designation": designation, "ordinal": ordinal, "title": "", "text_original": ""}
        u["canonical_path"] = (parent["canonical_path"]+"/" if parent else "")+kind+":"+designation
        u["citation_path"] = parent["citation_path"]+" > "+LABELS[kind]+" "+designation if parent else LAW
        u[field] = text[a:b]
        u["text_sha256"] = digest(u["text_original"].encode()); u["unit_id"] = unit_id(u)
        s = {"unit_id": u["unit_id"], "extraction_id": n["extraction_id"], "field_name": field, "span_order": 0,
             "char_start": a, "char_end": b, "locator_json": canonical(n["locator"]), "quote_sha256": digest(text[a:b].encode())}
        s["span_id"] = span_id(s); spans.append(s); units.append(u); keyed[key] = u
    return units, spans


def check_projection(units, spans, extraction, text, trace):
    """Sparse ordinals are source ordinals; do not invent siblings to fill gaps."""
    from src.legal_parser import check_contracts
    check_contracts({"units": units, "spans": spans})
    by = {u["unit_id"]: u for u in units}
    if len(by) != 10 or len({s["span_id"] for s in spans}) != len(spans):
        raise ValueError("Duplicate IDs or wrong selected scope")
    if (sum(u["unit_type"] == "document" for u in units) != 1
            or [u["designation"] for u in units if u["unit_type"] == "point"] != list("abcdđ")):
        raise ValueError("Missing/duplicate root or incomplete point order")
    if any(s["unit_id"] not in by or s["field_name"] not in {"title", "text_original"} for s in spans):
        raise ValueError("Orphan/invalid span field")
    for u in units:
        p = by.get(u["parent_unit_id"])
        if (u["unit_id"] != unit_id(u) or u["text_sha256"] != digest(u["text_original"].encode())
                or (u["parent_unit_id"] is None) != (u["unit_type"] == "document")
                or u["parent_unit_id"] is not None and p is None
                or p and (p["law_id"] != u["law_id"] or u["unit_type"] not in ALLOWED[p["unit_type"]])):
            raise ValueError("Invalid identity/parent relation")
        path = (p["canonical_path"]+"/" if p else "")+u["unit_type"]+":"+u["designation"]
        citation = p["citation_path"]+" > "+LABELS[u["unit_type"]]+" "+u["designation"] if p else u["law_id"]
        if u["canonical_path"] != path or u["citation_path"] != citation:
            raise ValueError("Path/citation not linked to parent")
        for field in ["title", "text_original"]:
            group = sorted([s for s in spans if s["unit_id"] == u["unit_id"] and s["field_name"] == field], key=lambda s:s["span_order"])
            if [s["span_order"] for s in group] != list(range(len(group))) or "\n".join(text[s["char_start"]:s["char_end"]] for s in group) != u[field]:
                raise ValueError("Field roundtrip failed")
            for s in group:
                if (s["extraction_id"] != extraction["extraction_id"] or s["span_id"] != span_id(s)
                        or not 0 <= s["char_start"] < s["char_end"] <= len(text)
                        or digest(text[s["char_start"]:s["char_end"]].encode()) != s["quote_sha256"]
                        or not any(n["locator"] == json.loads(s["locator_json"]) and n["char_start"] <= s["char_start"] < s["char_end"] <= n["char_end"] for n in trace["nodes"])):
                    raise ValueError("Span/locator/hash mismatch")


def official_diff(old, new):
    d = compare_fields(old, new)
    # The existing helper names its right side PDF; here right offsets are HTML fields.
    for a, b in [("pdf_text", "official_text"), ("pdf_sha256", "official_sha256")]:
        d[b] = d.pop(a)
    for x in d["differences"]:
        x["official_field_start"] = x.pop("pdf_field_start")
        x["official_field_end"] = x.pop("pdf_field_end")
        x["official_fragment"] = x.pop("pdf_fragment")
    return d


def comparisons(units, spans, legacy, legacy_spans, old_text, old_trace):
    results, crosswalk = [], []
    by_path = {u["canonical_path"]: u for u in legacy}
    # These quarantined nodes have no old unit/span; never pretend otherwise.
    quarantined = {"d": 517, "đ": 518}
    for u in units:
        old = by_path.get(u["canonical_path"])
        raw_region = None
        if u["unit_type"] == "point" and u["designation"] in quarantined:
            old = None
            n = next(n for n in old_trace["nodes"] if n["locator"].get("part") == "word/document.xml"
                     and n["locator"].get("xpath") == f"/w:document/w:body/w:p[{quarantined[u['designation']]+1}]")
            raw_region = {"locator": n["locator"], "char_start": n["char_start"], "char_end": n["char_end"],
                          "quote": old_text[n["char_start"]:n["char_end"]], "no_legacy_unit_or_legal_span": True}
        changed = [k for k in UNIT_FIELDS if old[k] != u[k]] if old else None
        if old and ((not changed) != (old["unit_id"] == u["unit_id"])):
            raise ValueError("Unit identity preservation failure")
        crosswalk.append({"citation_path": u["citation_path"], "old_unit_id": old["unit_id"] if old else None,
                          "new_unit_id": u["unit_id"], "changed_identity_fields": changed,
                          "reason": "identity_payload_fields_changed" if changed else "identity_payload_unchanged" if old else "restored_from_quarantined_extraction_region",
                          "legacy_region": raw_region, "decisions_transferred": False})
        if u["unit_type"] not in {"article", "clause", "point"}:
            continue
        field = "title" if u["unit_type"] == "article" else "text_original"
        original = old[field] if old else raw_region["quote"]
        results.append({"citation_path": u["citation_path"], "field": field, **official_diff(original, u[field]),
                        "restored_text": u[field], "old_unit_id": old["unit_id"] if old else None,
                        "new_unit_id": u["unit_id"], "legacy_region": raw_region,
                        "input_spans": [s for s in legacy_spans if old and s["unit_id"] == old["unit_id"] and s["field_name"] == field],
                        "restored_spans": [s for s in spans if s["unit_id"] == u["unit_id"] and s["field_name"] == field],
                        "origin": "agent_comparison", "pdf_text_offsets": None})
    return results, crosswalk


def calculate(root, config, created_at):
    raw = (root / "sources/official.html").read_bytes(); capture = load(root / "sources/capture.json")
    pdf = root / "sources/official_scan.pdf"
    if (digest(raw) != config["html_sha256"] or capture["sha256"] != digest(raw)
            or digest((root / "sources/capture.json").read_bytes()) != config["html_capture_record_sha256"]
            or digest(pdf.read_bytes()) != config["pdf_sha256"] or config["policy_version"] != VERSION
            or config["law_id"] != LAW or config["snapshot_date"] != SNAPSHOT_DATE):
        raise ValueError("Source/config binding mismatch")
    review = config["visual_review"]
    if review["origin"] != "agent_review" or review["human_reviewer_event_count"] != 0:
        raise ValueError("Review must stay agent-only")
    for p in config["pdf_pages"]:
        if digest((root / f"evidence/page-{p['page']:03d}.png").read_bytes()) != p["image_sha256"]:
            raise ValueError("Scan image binding mismatch")
    fid = file_identity(config["file_id_namespace"], LAW, digest(raw))
    text, trace, extraction = extract_html(raw, fid); extraction["created_at"] = created_at
    require_contract("extraction", extraction)
    if (root / extraction["text_ref"]).read_bytes() != text.encode("utf8"):
        raise ValueError("Immutable normalized artifact differs from HTML extraction replay")
    units, spans = map_units(text, trace); check_projection(units, spans, extraction, text, trace)
    files = [{"file_id": fid, "law_id": LAW, "raw_file_ref": "sources/official.html", "sha256": digest(raw), "size_bytes": len(raw)}]
    source = {"document": {"law_id": LAW, "source_id": "SRC-004", "law_title": units[0]["title"], "source_url": capture["url"]},
              "units": units, "spans": spans, "extractions": [extraction], "files": files, "issues": []}
    if review["unresolved_characters"]:
        source["issues"] = [{"law_id": LAW, "affected_unit_ids": [u["unit_id"] for u in units],
                             "code": "SOURCE_CHARACTER_UNCERTAINTY", "detail": canonical(review["unresolved_characters"])}]
    ec = load(root / "encoder_config.json")
    encode = lambda texts: encoder_input.encode_inputs(texts, ec, resolve_ref(BASE_DIR, config["coverage_manifest_ref"]).parent / "tokenizer_assets")["rows"]
    cfg = {"chunk_policy_version": chunk_preview_v2.VERSION, "snapshot_date": SNAPSHOT_DATE, "token_limit": 256,
           "required_context_fields": ["title"], "required_clause_context_fields": ["text_original"],
           "target_unit_ids": [u["unit_id"] for u in units if u["unit_type"] == "point"]}
    output = chunk_preview_v2.build_chunks(source, root, cfg, BLOCKERS, encode)
    require_preview_schema(output["chunks"] + [q["candidate"] for q in output["quarantined"]])
    coverage = resolve_ref(BASE_DIR, config["coverage_manifest_ref"]).parent
    check_files(coverage / "manifest.json")
    tree = coverage / "inputs/tree"; es = tree / "extraction_snapshot"
    legacy = rows(root / "legacy/units.jsonl"); legacy_spans = rows(root / "legacy/spans.jsonl")
    expected_units = [u for u in rows(tree / "legal_units.pending.jsonl") if u["law_id"] == LAW]
    ids = {u["unit_id"] for u in expected_units}
    old = next(r for r in rows(es / "extractions.pending.jsonl") if r["law_id"] == LAW)
    if (legacy != expected_units or legacy_spans != [s for s in rows(tree / "source_spans.pending.jsonl") if s["unit_id"] in ids]
            or (root / "legacy/normalized.txt").read_bytes() != resolve_ref(es, old["extraction"]["text_ref"]).read_bytes()
            or (root / "legacy/trace.json").read_bytes() != resolve_ref(es, old["trace_ref"]).read_bytes()):
        raise ValueError("Legacy comparison snapshot differs from bound coverage")
    comp, crosswalk = comparisons(units, spans, legacy, legacy_spans, (root / "legacy/normalized.txt").read_text(encoding="utf8"), load(root / "legacy/trace.json"))
    scope = [{"unit_id": u["unit_id"], "unit_sha256": digest(canonical(u).encode()), "scope_candidate": "included" if u["unit_type"] == "point" else
              "supporting" if u["unit_type"] in {"article", "clause"} else None,
              "reason": "BRD3.1: chế tài trực tiếp người điều khiển xe máy chuyên dùng tham gia giao thông; không phải cơ sở đào tạo/đăng kiểm hoặc quản lý hạ tầng." if u["unit_type"] == "point" else
              "Title Điều xác định loại phương tiện, lead Khoản giữ mức phạt cho đúng năm Điểm." if u["unit_type"] in {"article", "clause"} else "Structural dependency only; no inferred scope label.",
              "origin": "agent_review", "status": "proposed", "reviewer_ref": None, "applicability_status": "pending_review",
              "binding": {"extraction_id": extraction["extraction_id"], "html_sha256": digest(raw), "pdf_sha256": config["pdf_sha256"], "snapshot_date": SNAPSHOT_DATE},
              "evidence_refs": [s["span_id"] for s in spans if s["unit_id"] == u["unit_id"]] + ["BRD3.1"],
              "effective_from": None, "effective_to": None, "release_eligible": False} for u in units]
    return text, trace, extraction, units, spans, output, comp, crosswalk, scope


def source_records(root, config):
    """Real capture facts and DDD-shaped source files; pending, no fake document/FK."""
    capture = load(root / "sources/capture.json")
    result = []
    for ref, url, retrieved, kind, group in [
        ("sources/official.html", capture["url"], capture["accessed_at"], "alternate", "SRC-004-html-a16k2"),
        ("sources/official_scan.pdf", config["pdf_url"], config["pdf_accessed_at"], "main", "SRC-004-signed-pdf")]:
        raw = (root / ref).read_bytes(); sha = digest(raw)
        row = {"file_id": file_identity(config["file_id_namespace"], LAW, sha), "law_id": LAW,
               "source_set_id": group, "file_role": kind, "part_order": 1, "filename": Path(ref).name,
               "raw_file_ref": ref, "download_url": url, "retrieved_at": retrieved.replace("+00:00", "Z"),
               "mime_type": "text/html" if ref.endswith("html") else "application/pdf", "size_bytes": len(raw), "sha256": sha}
        require_contract("source_file", row)
        result.append(row)
    return result


def source_facts(root, config):
    return {"origin": "agent_review", "source_status": "pending", "edition_review": "pending", "applicability": "pending_review",
            "capture_facts": config["html_capture_ref"], "html_capture": load(root / "sources/capture.json"),
            "scan_capture_url": config["pdf_url"], "scan_capture_accessed_at": config["pdf_accessed_at"],
            "visual_review": config["visual_review"], "not_a_formal_stage2_bundle": True,
            "no_corpus_or_review_decision_created": True}


def render(data, config):
    text, trace, extraction, units, spans, output, comp, crosswalk, scope = data
    lines = ["# NĐ168 Điều16 Khoản2 — HTML chính thức đối chiếu scan", "Origin=agent_review; chưa human-reviewed/verified, applicability pending; không thay dataset nhóm.",
             "HTML là nguồn text mới; PDF trang40–41 là bằng chứng hình ảnh. Không có PDF text offsets hoặc tọa độ tự đoán.",
             "\n## Cây chọn lọc (ordinal theo nguồn, không tạo sibling giả)"]
    by = {u["unit_id"]: u for u in units}
    tree = []
    for u in units:
        depth, p = 0, by.get(u["parent_unit_id"])
        while p:
            depth += 1; p = by.get(p["parent_unit_id"])
        tree.append("  "*depth + u["unit_type"]+" "+u["designation"]+" [ordinal="+str(u["ordinal"])+"] "+(u["title"] or u["text_original"]))
    lines += ["```text\n"+"\n".join(tree)+"\n```",
             "| Citation | DOCX → official HTML | Token / unknown | Kết quả |", "|---|---|---|---|"]
    enc = {e["unit_id"]:e for e in output["encoder_inputs"]}; status = {r["unit_id"]:r for r in output["unit_results"]}
    for r in comp:
        e = enc.get(r["new_unit_id"], {})
        lines.append(f"| {r['citation_path']} | {r['classification']} | {e.get('tokens_with_special')} / {e.get('unknown_tokens')} | {status.get(r['new_unit_id'], {}).get('status', 'context/dependency')} |")
    for r in comp:
        lines += ["\n## " + r["citation_path"], "DOCX cũ (kể cả vùng cách ly):", r["input_text"], "Nguồn chính thức / khôi phục:", r["official_text"],
                  "Trang scan: " + str(config["visual_review"]["per_field_pages"]["article_title" if r["field"] == "title" else
                     "clause_2" if r["citation_path"].endswith("Khoản 2") else "point_"+r["citation_path"].split("Điểm ")[-1]]),
                  "Diff (offset tương đối trong field, không phải PDF):", canonical(r["differences"]),
                  "Spans mới (absolute Unicode code point trong normalized.txt):", canonical(r["restored_spans"])]
    for c in output["chunks"] + [q["candidate"] for q in output["quarantined"]]:
        lines += ["\n## Preview " + c["citation_path"], "`" + c["chunk_id"] + "`", "Context:", c["context_text"],
                  "Target:", c["text_original"], "text_for_search:", c["text_for_search"], "encoder_text:", enc[c["unit_id"]]["encoder_text"]]
    lines += ["\n## ID mapping", canonical(crosswalk), "\n## Giới hạn", *config["limitations"],
              "Chỉ sparse tree: document/chapter/section giữ title thật, own text không được chọn. Không suy full preamble hoặc sibling đã kiểm/verified."]
    return "\n\n".join(lines) + "\n"


def export(root, data):
    text, trace, extraction, units, spans, output, comp, crosswalk, scope = data
    (root / "extraction").mkdir(exist_ok=True)
    (root / "extraction/normalized.txt").write_text(text, encoding="utf8", newline="\n")
    write_json(root / "extraction/trace.json", trace); write_json(root / "extraction/metadata.json", extraction)
    for name, value in [("legal_units.pending.jsonl", units), ("source_spans.pending.jsonl", spans), ("comparison.jsonl", comp),
                        ("id_crosswalk.jsonl", crosswalk), ("scope.proposals.jsonl", scope)]:
        write_rows(root / name, value)
    for k, name in EXPORTS.items():
        write_rows(root / name, output[k])


def build(config_path, run_dir):
    target = staging_path(run_dir); config = load(config_path)
    capture_root = resolve_ref(BASE_DIR, config["html_capture_ref"])
    raw = (capture_root / "official.html").read_bytes()
    if digest(raw) != config["html_sha256"]:
        raise ValueError("Capture hash mismatch")
    select_blocks(raw)  # preflight before writing output
    coverage = resolve_ref(BASE_DIR, config["coverage_manifest_ref"]).parent
    check_files(coverage / "manifest.json")
    if digest(resolve_ref(BASE_DIR, config["pdf_ref"]).read_bytes()) != config["pdf_sha256"]:
        raise ValueError("PDF binding mismatch")
    if sorted(p["page"] for p in config["pdf_pages"]) != [40, 41]:
        raise ValueError("Only reviewed scan pages 40–41 are allowed")
    for p in config["pdf_pages"]:
        if digest(resolve_ref(BASE_DIR, p["image_ref"]).read_bytes()) != p["image_sha256"]:
            raise ValueError("Scan image input hash mismatch")
    target.mkdir(parents=True); (target / "sources").mkdir(); (target / "evidence").mkdir(); (target / "legacy").mkdir()
    for name in ["official.html", "capture.json"]:
        shutil.copyfile(capture_root / name, target / "sources" / name)
    shutil.copyfile(resolve_ref(BASE_DIR, config["pdf_ref"]), target / "sources/official_scan.pdf")
    for p in config["pdf_pages"]:
        shutil.copyfile(resolve_ref(BASE_DIR, p["image_ref"]), target / f"evidence/page-{p['page']:03d}.png")
    tree = coverage / "inputs/tree"; es = tree / "extraction_snapshot"
    old = next(r for r in rows(es / "extractions.pending.jsonl") if r["law_id"] == LAW)
    shutil.copyfile(resolve_ref(es, old["extraction"]["text_ref"]), target / "legacy/normalized.txt")
    shutil.copyfile(resolve_ref(es, old["trace_ref"]), target / "legacy/trace.json")
    write_rows(target / "legacy/units.jsonl", [u for u in rows(tree / "legal_units.pending.jsonl") if u["law_id"] == LAW])
    ids = {u["unit_id"] for u in rows(target / "legacy/units.jsonl")}
    write_rows(target / "legacy/spans.jsonl", [s for s in rows(tree / "source_spans.pending.jsonl") if s["unit_id"] in ids])
    shutil.copyfile(coverage / "encoder_config.json", target / "encoder_config.json")
    write_json(target / "config.json", config)
    fid = file_identity(config["file_id_namespace"], LAW, digest(raw))
    normalized, _, _ = extract_html(raw, fid)
    (target / "extraction").mkdir()
    (target / "extraction/normalized.txt").write_text(normalized, encoding="utf8", newline="\n")
    created = now(); data = calculate(target, config, created); export(target, data)
    write_rows(target / "source_files.prepared.jsonl", source_records(target, config))
    write_json(target / "source_facts.pending.json", source_facts(target, config))
    (target / "review.md").write_text(render(data, config), encoding="utf8")
    report = {"technical_valid": True, "points_restored": 5, "preview": len(data[5]["chunks"]),
              "quarantined": len(data[5]["quarantined"]), "blocked": len(data[5]["issues"]), "release_eligible": False}
    write_json(target / "validation_report.json", report)
    seal(target, {"manifest_type": VERSION, "built_at": created, "snapshot_date": SNAPSHOT_DATE, "origin": "agent_review",
                  "human_reviewer_event_count": 0, "release_eligible": False, "corpus_version": None,
                  "code_sha256": digest(Path(__file__).read_bytes()), "coverage_manifest_sha256": digest((coverage / "manifest.json").read_bytes())})
    return report


def validate(path):
    path = Path(path).resolve(); root = path.parent; m = check_files(path)
    if (m["manifest_type"] != VERSION or m["files"] != inventory(root) or m["code_sha256"] != digest(Path(__file__).read_bytes())
            or m["release_eligible"] is not False or m["corpus_version"] is not None or m["origin"] != "agent_review"
            or m["snapshot_date"] != SNAPSHOT_DATE or m["human_reviewer_event_count"] != 0):
        raise ValueError("Manifest/version/status/code mismatch")
    config = load(root / "config.json")
    cm = resolve_ref(BASE_DIR, config["coverage_manifest_ref"])
    if digest(cm.read_bytes()) != m["coverage_manifest_sha256"]:
        raise ValueError("Legacy coverage binding changed")
    data = calculate(root, config, m["built_at"])
    text, trace, extraction, units, spans, output, comp, crosswalk, scope = data
    if ((root / "extraction/normalized.txt").read_bytes() != text.encode() or load(root / "extraction/trace.json") != trace
            or load(root / "extraction/metadata.json") != extraction):
        raise ValueError("HTML extraction replay mismatch")
    for name, value in [("legal_units.pending.jsonl", units), ("source_spans.pending.jsonl", spans), ("comparison.jsonl", comp),
                        ("id_crosswalk.jsonl", crosswalk), ("scope.proposals.jsonl", scope)] + [(name, output[k]) for k, name in EXPORTS.items()]:
        if rows(root / name) != value:
            raise ValueError("Mapping/preview replay mismatch: " + name)
    if (root / "review.md").read_text(encoding="utf8") != render(data, config):
        raise ValueError("Readable report mismatch")
    if rows(root / "source_files.prepared.jsonl") != source_records(root, config):
        raise ValueError("Source provenance record mismatch")
    if load(root / "source_facts.pending.json") != source_facts(root, config):
        raise ValueError("Source facts/review status mismatch")
    report = {"technical_valid": True, "points_restored": 5, "preview": len(output["chunks"]),
              "quarantined": len(output["quarantined"]), "blocked": len(output["issues"]), "release_eligible": False}
    if load(root / "validation_report.json") != report:
        raise ValueError("Validation report mismatch")
    return {**report, "replay": True}


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build"); b.add_argument("--config", type=Path, default=DEFAULT_CONFIG); b.add_argument("--run-dir", type=Path, required=True)
    v = sub.add_parser("validate"); v.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    try:
        r = build(a.config, a.run_dir) if a.action == "build" else validate(a.manifest)
        print(json.dumps(r, ensure_ascii=False)); return 2 if r["blocked"] else 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
