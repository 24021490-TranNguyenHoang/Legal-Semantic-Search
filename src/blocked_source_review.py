"""Scoped repair/triage of the thirteen source/context-blocked candidates.

Old parser/builders remain byte-bound. Only a reviewed non-text layout boundary
is reclassified; source discrepancies and unsupported amendment tables defer.
"""
import argparse
import copy
import json
from io import BytesIO
from pathlib import Path
import sys
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from src import coverage_survey, chunk_preview_v2, encoder_input
from src.article22_preview import require_preview_schema
from src.assessment_evidence import check_files, inventory, seal, now
from src.bm25_baseline import dataset_files_check
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion.legal_tree import parse_extraction, validate_tree
from src.legal_parser import validate_run, check_contracts
from src.pipeline_cli import staging_path
from src.retrieval_dataset import latest_scope
from src.source_contracts import canonical, digest, resolve_ref

VERSION = "blocked-source-review.v1"
PARSER_POLICY = "legal-tree.v1.1.scoped-layout.v1"
DEFAULT_CONFIG = BASE_DIR / "config/blocked_source_review.v1.json"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
V = "{urn:schemas-microsoft-com:vml}"
EXPORTS = {"chunks": "chunks.preview.jsonl", "contexts": "contexts.preview.jsonl",
           "encoder_inputs": "encoder_inputs.jsonl", "quarantined": "quarantined.preview.jsonl",
           "issues": "builder_issues.jsonl", "unit_results": "unit_results.jsonl", "dependency_checks": "dependency_checks.jsonl"}


def non_text_horizontal_line(paragraph):
    """Fail closed: no text/fields/numbering/bitmaps, matching horizontal DML/VML."""
    forbidden = {W + t for t in ("t", "delText", "sym", "numPr", "fldChar", "fldSimple", "instrText", "object", "ins", "del", "moveFrom", "moveTo")}
    forbidden |= {A + "blip", V + "imagedata", V + "shape"}
    if any(e.tag in forbidden for e in paragraph.iter()):
        return False
    shapes = list(paragraph.iter(A + "prstGeom"))
    lines = list(paragraph.iter(V + "line"))
    if not shapes or not lines or any(e.get("prst") != "line" for e in shapes):
        return False
    extents = list(paragraph.iter(A + "ext"))
    if not extents or any(e.get("cy") != "0" for e in extents):
        return False
    for e in lines:
        start, end = e.get("from", "").split(","), e.get("to", "").split(",")
        if len(start) != 2 or len(end) != 2 or start[1] != end[1]:
            return False
    return True


def scoped_layout_parse(record, text, trace, source_issues, raw, spec):
    """Same immutable extraction, unchanged units/spans; explicit layout sidecar."""
    if digest(raw) != spec["raw_sha256"] or record["law_id"] != spec["law_id"]:
        raise ValueError("Layout raw binding mismatch")
    matches = [n for n in trace["nodes"] if n["locator"] == spec["locator"]]
    if (len(matches) != 1 or matches[0]["char_start"] != matches[0]["char_end"]
            or matches[0]["char_start"] != spec["char_start"] or spec["char_end"] != spec["char_start"]):
        raise ValueError("Layout is not the reviewed zero-width locator")
    loc = spec["locator"]
    with ZipFile(BytesIO(raw)) as z:
        xml = ET.fromstring(z.read(loc["part"]))
    ps = list(xml.find(W + "body").findall(W + "p"))
    idx = loc["paragraph_index"]
    if (not non_text_horizontal_line(ps[idx]) or idx + 1 >= len(ps)
            or not "".join(ps[idx + 1].itertext()).strip().startswith("Luật này được Quốc hội")):
        raise ValueError("Not a bounded non-text line before enactment/signature")
    matched = [q for q in source_issues if q["locator"] == loc]
    if len(matched) != 2 or any(q["code"] != "DOCX_VISUAL_OR_SYMBOL_REVIEW" for q in matched):
        raise ValueError("Unexpected source warnings; do not suppress them")
    original = parse_extraction(record, text, trace, source_issues)
    fixed = parse_extraction(record, text, trace, [q for q in source_issues if q not in matched])
    if fixed["units"] != original["units"] or fixed["spans"] != original["spans"]:
        raise ValueError("Layout disposition must not change any legal content/identity/span")
    for c in fixed["coverage"]:
        if c["locator"] == loc:
            c.update(category="layout", reason="SCOPED_NON_TEXT_HORIZONTAL_LINE")
    for q in original["warning_reviews"]:
        if q["locator"] == loc:
            fixed["warning_reviews"].append({**q, "handling": "scoped_layout_disposition_source_warning_still_pending"})
    errors = validate_tree(fixed["units"], fixed["spans"], {record["extraction"]["extraction_id"]: (record, text, trace)}, fixed["coverage"])
    if errors:
        raise ValueError("Scoped tree invariant failure: " + canonical(errors))
    check_contracts(fixed)
    return fixed, {"policy": PARSER_POLICY, "locator": loc, "source_warning_ids": [q["issue_id"] for q in matched],
                   "original_parser_issues": [q for q in original["issues"] if q["locator"] == loc],
                   "action": "non_text_layout_boundary_only", "source_review_status": "pending",
                   "unit_content_and_spans_unchanged": True, "origin": "agent_review"}


def group_for(u, by):
    parent = by[u["parent_unit_id"]] if u["unit_type"] == "point" else u
    return ("ND168_A" if u["law_id"].startswith("168/") else "L35_A") + by[parent["parent_unit_id"]]["designation"] + "K" + parent["designation"]


def prepared(config, full_tree=False):
    if config["version"] != VERSION or config["origin"] != "agent_review" or config["human_reviewer_event_count"] != 0:
        raise ValueError("Invalid scoped review configuration")
    cm = resolve_ref(BASE_DIR, config["coverage_manifest_ref"])
    dm = resolve_ref(BASE_DIR, config["dataset_manifest_ref"])
    cov = cm.parent; dataset = dm.parent
    c = check_files(cm); dataset_files_check(dm)
    if c["code_sha256"] != coverage_survey.code_binding() or c["files"] != inventory(cov):
        raise ValueError("Coverage code/inventory mismatch")
    bind = load(dataset / "input_binding.json")
    if digest(cm.read_bytes()) != bind["coverage_manifest_sha256"]:
        raise ValueError("Coverage/dataset binding mismatch")
    if full_tree:
        result = validate_run(cov / "inputs/tree/manifest.json", raw_root=cov / "inputs")
        if not result["technical_valid"]:
            raise ValueError("Invalid upstream source/extraction/tree")
    evidence = resolve_ref(BASE_DIR, config["review_evidence_ref"])
    if digest((evidence / "evidence_catalog.json").read_bytes()) != config["evidence_catalog_sha256"]:
        raise ValueError("Review evidence catalog changed")
    catalog = load(evidence / "evidence_catalog.json")
    for e in catalog:
        if (digest(resolve_ref(BASE_DIR, e["pdf_ref"]).read_bytes()) != e["pdf_sha256"]
                or digest(resolve_ref(evidence, e["image_ref"]).read_bytes()) != e["image_sha256"]
                or digest(resolve_ref(evidence, e["page_text_ref"]).read_bytes()) != e["page_text_sha256"]
                or e["visually_reviewed_by_agent"] is not True):
            raise ValueError("Evidence PDF/image hash mismatch")
    laws, _ = coverage_survey.load_data(cov)
    by = {u["unit_id"]: u for d in laws.values() for u in d["units"]}
    selected = [r for r in rows(dataset / "deferred.jsonl") if r["reason"] == "blocked_source_or_context"]
    coverage = {r["unit_id"]: r for r in rows(cov / "unit_coverage.jsonl")}
    if len(selected) != 13 or any(coverage[r["unit_id"]]["status"] != r["reason"]
                                  or coverage[r["unit_id"]]["unit_sha256"] != digest(canonical(by[r["unit_id"]]).encode()) for r in selected):
        raise ValueError("Expected exactly thirteen bound candidates")
    if config["layout"]["unit_id"] not in {r["unit_id"] for r in selected}:
        raise ValueError("Layout disposition outside the thirteen candidates")
    scopes = latest_scope(by, rows(dataset / "support/scope_proposals.jsonl"), rows(dataset / "support/scope_revisions.jsonl"), bind["coverage_manifest_sha256"], bind["scope_manifest_sha256"])
    return cov, dataset, evidence, catalog, laws, by, selected, scopes


def calculate(config, full_tree=False):
    cov, dataset, evidence, catalog, laws, by, selected, scopes = prepared(config, full_tree)
    spec = config["layout"]
    tree = cov / "inputs/tree"; extraction = tree / "extraction_snapshot"
    record = next(r for r in rows(extraction / "extractions.pending.jsonl") if r["law_id"] == spec["law_id"])
    text = resolve_ref(extraction, record["extraction"]["text_ref"]).read_text(encoding="utf8")
    trace = load(resolve_ref(extraction, record["trace_ref"]))
    source_issues = [q for q in rows(extraction / "quality_issues.jsonl") if q["extraction_id"] == record["extraction"]["extraction_id"]]
    file = next(f for f in laws[spec["law_id"]]["files"] if f["file_id"] == record["extraction"]["file_id"])
    layout_ev = next(e for e in catalog if e["law_id"] == spec["law_id"] and e["page"] == spec["evidence_page"])
    target = by[spec["unit_id"]]
    page_text = resolve_ref(evidence, layout_ev["page_text_ref"]).read_text(encoding="utf8")
    flat = lambda s: "".join(unicodedata.normalize("NFC", s).split())
    if (layout_ev["pdf_sha256"] != spec["pdf_sha256"] or flat(target["text_original"]) not in flat(page_text)
            or flat(by[target["parent_unit_id"]]["title"]) not in flat(page_text)):
        raise ValueError("Full target/title must match official page text; visual review also required")
    parsed, disposition = scoped_layout_parse(record, text, trace, source_issues, resolve_ref(cov / "inputs", file["raw_file_ref"]).read_bytes(), spec)
    transformed = copy.deepcopy(laws)
    data = transformed[spec["law_id"]]
    data["units"], data["spans"] = parsed["units"], parsed["spans"]
    removed = [q for q in data["issues"] if q["locator"] == spec["locator"]]
    if (len(removed) != 4 or {q["origin"] for q in removed} != {"stage4_parser", "stage4_coverage", "stage3_extraction"}):
        raise ValueError("Unexpected layout dependencies")
    data["issues"] = [q for q in data["issues"] if q not in removed]
    disposition["original_dependencies_retained_in_sidecar"] = removed
    ec = load(cov / "encoder_config.json")
    encode = lambda texts: encoder_input.encode_inputs(texts, ec, cov / "tokenizer_assets")["rows"]
    config_chunk = load(cov / "config.json")["chunk"]
    output = {k: [] for k in EXPORTS}
    for law, data in transformed.items():
        ids = [r["unit_id"] for r in selected if r["law_id"] == law]
        if ids:
            result = chunk_preview_v2.build_chunks(data, cov / "inputs", {**config_chunk, "target_unit_ids": ids}, coverage_survey.LEGAL_BLOCKERS, encode)
            for k in output:
                output[k].extend(result[k])
    require_preview_schema(output["chunks"])
    after = {r["unit_id"]: r for r in output["unit_results"]}
    oldchecks = {r["unit_id"]: r for r in rows(cov / "dependency_checks.jsonl")}
    candidates = []
    for r in selected:
        uid = r["unit_id"]; u = by[uid]; group = group_for(u, by)
        action = ("scoped_layout_parser_fix_preview" if uid == spec["unit_id"] else
                  "defer_docx_differs_from_scanned_official_source" if group.startswith("ND168") else
                  "defer_unsupported_amendment_table_scope_not_approved")
        parent = by[u["parent_unit_id"]]
        ctx = [x for x in [parent, by.get(parent["parent_unit_id"])] if x and x["unit_type"] in {"article", "clause"}]
        region_unit = parent if u["unit_type"] == "point" else u
        region_window = next(w for w in oldchecks[uid]["windows"] if w["unit_id"] == region_unit["unit_id"])
        e = next(e for e in laws[u["law_id"]]["extractions"] if e["extraction_id"] == region_window["extraction_id"])
        source_text = resolve_ref(cov / "inputs", e["text_ref"]).read_text(encoding="utf8")
        a, b = region_window["char_start"], region_window["char_end"]
        candidates.append({**r, "group_id": group, "before_status": r["reason"], "after": after[uid], "action": action,
                           "scope_proposal": (scopes.get(uid) or {}).get("scope_candidate", "pending"),
                           "scope_record": scopes.get(uid), "unit": u, "source_spans": [s for s in laws[u["law_id"]]["spans"] if s["unit_id"] == uid],
                           "context_dependencies": [{"unit_id": x["unit_id"], "title": x["title"], "text_original": x["text_original"],
                                                     "source_spans": [s for s in laws[u["law_id"]]["spans"] if s["unit_id"] == x["unit_id"]]} for x in ctx],
                           "before_impacts": oldchecks[uid]["impacts"], "applicability": "pending_review", "source_status": "pending",
                           "full_source_region": {**region_window, "text_ref": e["text_ref"], "text": source_text[a:b],
                                                  "quote_sha256": digest(source_text[a:b].encode()), "not_a_legal_unit_span": True},
                           "old_unit_id": uid, "new_unit_id": uid, "id_reason": "No legal field/identity edited; deferred records are not repaired identities",
                           "origin": "agent_review", "release_eligible": False})
    return output, candidates, parsed, disposition, catalog


def render(candidates, config):
    lines = ["# 13 candidate → vùng lỗi → bằng chứng → kết quả", "Origin=agent_review; không reviewer event; nguồn/scope/applicability không được nâng trạng thái.",
             "13 candidate, 6 nhóm vùng nguồn. Không cộng số candidate thành số issue hoặc số vùng cần sửa.",
             "| Citation | Nhóm | Scope proposal | Trước | Sau / hành động |", "|---|---|---|---|---|"]
    for r in candidates:
        lines.append(f"| {r['citation_path']} | {r['group_id']} | {r['scope_proposal']} | blocked_source_or_context | {r['after']['status']} / {r['action']} |")
    for r in candidates:
        lines += ["\n## " + r["citation_path"], "unit_id: `" + r["unit_id"] + "`", "Nguyên văn:", r["unit"]["text_original"],
                  "Context dependencies:", canonical(r["context_dependencies"]), "Source spans:", canonical(r["source_spans"]),
                  "Toàn vùng nguồn của Khoản (gồm phần cách ly/bảng và ranh giới cuối văn bản nếu có):", canonical(r["full_source_region"]),
                  "Trước — issue/ảnh hưởng:", canonical(r["before_impacts"]), "Sau:", canonical(r["after"]),
                  "Bằng chứng ND168: " + ("trang 40–41" if "A16" in r["group_id"] else "trang 84–85" if "A39" in r["group_id"] else "trang 85–86")
                  if r["group_id"].startswith("ND168") else "Bằng chứng Luật35: PDF trang 67/in 69 (bảng); 68–69/in 70–71 (liền kề/Điều86)."]
    lines += ["\n## Nguyên văn trích ảnh và khác biệt (không dùng làm extraction/spans)", canonical(config["visual_quotes"]),
              "ND168: cần bản text chính thức có provenance hoặc transcription/OCR được đối chiếu có contract extraction/mapping trước khi tái dựng. Không relabel DOCX, không fake spans trên normalized cũ.",
              "Hai bảng Luật35: cần quy tắc giữ ngữ nghĩa bảng sửa đổi và quyết định nhu cầu scope riêng; không ép ô thành Khoản/Điểm. Một scope pending, một excluded proposal.",
              "Luật35 Điều86K2: chỉ disposition graphic line zero-width thành layout ở run mới; warnings nguồn cũ giữ pending trong sidecar. Identity/text/spans giữ nguyên."]
    return "\n\n".join(lines) + "\n"


def build(config_path, run):
    target = staging_path(run); config = load(config_path)
    output, candidates, parsed, disposition, catalog = calculate(config, full_tree=True)
    target.mkdir(parents=True)
    write_json(target / "config.json", config)
    for k, name in EXPORTS.items():
        write_rows(target / name, output[k])
    write_rows(target / "candidates.before_after.jsonl", candidates)
    write_json(target / "layout_disposition.json", disposition)
    (target / "parser_projection").mkdir()
    for k in ("units", "spans", "coverage", "issues", "warning_reviews"):
        write_rows(target / "parser_projection" / (k + ".pending.jsonl"), parsed[k])
    write_json(target / "evidence_catalog.json", catalog)
    (target / "review.md").write_text(render(candidates, config), encoding="utf8")
    report = {"technical_valid": True, "candidates": len(candidates), "groups": len({r["group_id"] for r in candidates}),
              "preview": len(output["chunks"]), "deferred": len(candidates)-len(output["chunks"]), "release_eligible": False}
    write_json(target / "validation_report.json", report)
    seal(target, {"manifest_type": VERSION, "built_at": now(), "snapshot_date": SNAPSHOT_DATE, "origin": "agent_review",
                  "release_eligible": False, "human_reviewer_event_count": 0, "parser_policy": PARSER_POLICY,
                  "code_sha256": digest(Path(__file__).read_bytes()), "input_sha256": {n: digest(resolve_ref(BASE_DIR, config[n]).read_bytes()) for n in ("coverage_manifest_ref", "dataset_manifest_ref")}})
    return report


def validate(manifest):
    manifest = Path(manifest).resolve(); root = manifest.parent; m = check_files(manifest)
    if (m["manifest_type"] != VERSION or m["code_sha256"] != digest(Path(__file__).read_bytes()) or m["files"] != inventory(root)
            or m["release_eligible"] is not False or m["origin"] != "agent_review" or m["human_reviewer_event_count"] != 0
            or m["snapshot_date"] != SNAPSHOT_DATE or m["parser_policy"] != PARSER_POLICY
            or set(m["input_sha256"]) != {"coverage_manifest_ref", "dataset_manifest_ref"}):
        raise ValueError("Review manifest/code/status mismatch")
    config = load(root / "config.json")
    if any(digest(resolve_ref(BASE_DIR, config[n]).read_bytes()) != h for n, h in m["input_sha256"].items()):
        raise ValueError("Input bundle changed")
    output, candidates, parsed, disposition, catalog = calculate(config)
    for k, name in EXPORTS.items():
        if rows(root / name) != output[k]:
            raise ValueError("Preview replay mismatch: " + name)
    for k in ("units", "spans", "coverage", "issues", "warning_reviews"):
        if rows(root / "parser_projection" / (k + ".pending.jsonl")) != parsed[k]:
            raise ValueError("Parser projection mismatch: " + k)
    if (rows(root / "candidates.before_after.jsonl") != candidates or load(root / "layout_disposition.json") != disposition
            or load(root / "evidence_catalog.json") != catalog or (root / "review.md").read_text(encoding="utf8") != render(candidates, config)):
        raise ValueError("Review output differs from replay")
    report = {"technical_valid": True, "candidates": len(candidates), "groups": len({r["group_id"] for r in candidates}),
              "preview": len(output["chunks"]), "deferred": len(candidates)-len(output["chunks"]), "release_eligible": False}
    if load(root / "validation_report.json") != report:
        raise ValueError("Report mismatch")
    return {**report, "replay": True}


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build"); b.add_argument("--config", type=Path, default=DEFAULT_CONFIG); b.add_argument("--run-dir", type=Path, required=True)
    v = sub.add_parser("validate"); v.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(build(args.config, args.run_dir) if args.action == "build" else validate(args.manifest), ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
