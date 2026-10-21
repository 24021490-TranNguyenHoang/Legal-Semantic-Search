"""Bounded nine-article preview from hash-bound coverage and handed-off dataset."""
import argparse
import json
from pathlib import Path
import sys
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from src import chunk_preview_articles as builder, encoder_input, coverage_survey
from src.article22_preview import require_preview_schema
from src.assessment_evidence import check_files, seal, now, inventory
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_json, write_rows
from src.legal_parser import validate_run
from src.retrieval_dataset import check_inventory, latest_scope
from src.source_contracts import digest, canonical, resolve_ref
from src.pipeline_cli import staging_path

VERSION = "nine-leaf-articles-preview.v1"
EXPORTS = {"chunks": "chunks.preview.jsonl", "contexts": "contexts.preview.jsonl",
           "encoder_inputs": "encoder_inputs.jsonl", "quarantined": "quarantined.preview.jsonl",
           "issues": "issues.jsonl", "unit_results": "unit_results.jsonl", "dependency_checks": "dependency_checks.jsonl"}


def code_binding():
    return {n: digest((BASE_DIR / n).read_bytes()) for n in
            ["src/chunk_preview_articles.py", "src/leaf_articles_preview.py"]}


def inspect_raw(data, root, u):
    """Inspect actual DOCX paragraphs behind both fields; no repair/number inference."""
    evidence = []
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for s in [s for s in data["spans"] if s["unit_id"] == u["unit_id"]]:
        loc = json.loads(s["locator_json"])
        e = next(e for e in data["extractions"] if e["extraction_id"] == s["extraction_id"])
        f = next(f for f in data["files"] if f["file_id"] == e["file_id"])
        with ZipFile(resolve_ref(root, f["raw_file_ref"])) as z:
            doc = ET.fromstring(z.read(loc["part"]))
        paragraphs = list(doc.find(ns + "body").findall(ns + "p"))
        paragraph = paragraphs[loc["paragraph_index"]]
        text = unicodedata.normalize("NFC", "".join(x.text or "" for x in paragraph.iter(ns + "t")))
        flags = [tag for tag in ("numPr", "fldChar", "instrText", "ins", "del", "moveFrom", "moveTo")
                 if list(paragraph.iter(ns + tag))]
        evidence.append({"span_id": s["span_id"], "locator": loc, "raw_paragraph_text": text,
                         "unresolved_xml_tags": flags, "field_present_in_raw_paragraph": u[s["field_name"]] in text})
        if flags or not evidence[-1]["field_present_in_raw_paragraph"]:
            data["issues"].append({"law_id": u["law_id"], "unit_id": u["unit_id"],
                                   "code": "RAW_UNDECODED_STRUCTURE", "locator": loc, "flags": flags})
    return evidence


def inputs(coverage_manifest, dataset_manifest):
    cm, dm = Path(coverage_manifest).resolve(), Path(dataset_manifest).resolve()
    c = check_files(cm)
    if (c["manifest_type"] != coverage_survey.VERSION or c["code_sha256"] != coverage_survey.code_binding()
            or c["release_eligible"] is not False or c["files"] != inventory(cm.parent)):
        raise ValueError("Coverage version/code/inventory/status mismatch")
    from src.bm25_baseline import dataset_files_check
    dataset_files_check(dm)
    binding = load(dm.parent / "input_binding.json")
    if digest(cm.read_bytes()) != binding["coverage_manifest_sha256"]:
        raise ValueError("Dataset belongs to another coverage bundle")
    config = load(cm.parent / "config.json")
    coverage_survey.check_config(cm.parent, config)
    tree = validate_run(cm.parent / "inputs/tree/manifest.json", raw_root=cm.parent / "inputs")
    if not tree["technical_valid"]:
        raise ValueError("Tree/extraction/source validation failed: " + canonical(tree))
    laws, _ = coverage_survey.load_data(cm.parent)
    selected = [r for r in rows(cm.parent / "unit_coverage.jsonl") if r["status"] == "unsupported_structure"]
    if len(selected) != 9 or any(r["unit_type"] != "article" for r in selected):
        raise ValueError("This task only accepts the nine unsupported articles")
    by = {u["unit_id"]: u for d in laws.values() for u in d["units"]}
    for r in selected:
        if r["unit_sha256"] != digest(canonical(by[r["unit_id"]]).encode()):
            raise ValueError("Selected unit binding mismatch")
    scopes = latest_scope(by, rows(dm.parent / "support/scope_proposals.jsonl"),
                          rows(dm.parent / "support/scope_revisions.jsonl"),
                          binding["coverage_manifest_sha256"], binding["scope_manifest_sha256"])
    return cm, dm, laws, selected, scopes


def calculate(coverage_manifest, dataset_manifest):
    cm, dm, laws, selected, scopes = inputs(coverage_manifest, dataset_manifest)
    config = {"chunk_policy_version": builder.VERSION, "snapshot_date": SNAPSHOT_DATE, "token_limit": 256}
    ec = load(cm.parent / "encoder_config.json")
    encode = lambda texts: encoder_input.encode_inputs(texts, ec, cm.parent / "tokenizer_assets")["rows"]
    output = {k: [] for k in EXPORTS}
    inspection = []
    for law, data in laws.items():
        ids = [r["unit_id"] for r in selected if r["law_id"] == law]
        if not ids:
            continue
        by = {u["unit_id"]: u for u in data["units"]}
        for uid in ids:
            u = by[uid]
            ancestors, node = [], u
            while node["parent_unit_id"]:
                node = by[node["parent_unit_id"]]
                ancestors.append(node)
            inspection.append({"unit": u, "ancestors": ancestors,
                               "children": [x["unit_id"] for x in data["units"] if x["parent_unit_id"] == uid],
                               "spans": [s for s in data["spans"] if s["unit_id"] == uid],
                               "raw_inspection": inspect_raw(data, cm.parent / "inputs", u),
                               "coverage_scope": next(r["scope"] for r in selected if r["unit_id"] == uid),
                               "latest_scope_proposal": scopes.get(uid),
                               "source_status": "pending", "applicability_status": "pending_review",
                               "origin": "agent_review", "release_eligible": False})
        result = builder.build_chunks(data, cm.parent / "inputs", {**config, "target_unit_ids": ids},
                                      coverage_survey.LEGAL_BLOCKERS, encode)
        for k in output:
            output[k].extend(result[k])
    require_preview_schema(output["chunks"] + [q["candidate"] for q in output["quarantined"]])
    return output, inspection


def render(output, inspection):
    lines = ["# Chín Điều lá — experimental preview", "Nguồn/extraction/hiệu lực pending; origin=agent_review. Không thay dataset/index đã bàn giao.",
             "Title dùng một lần làm heading context; target là nguyên text_original, kể cả khoảng trắng cuối.",
             "Proof paths tương đối với inputs/ của coverage manifest ghi trong manifest run này.",
             "| Citation | Kết quả | Token / unknown | Scope proposal | Nguồn / applicability |",
             "|---|---|---|---|---|"]
    enc = {x["unit_id"]: x for x in output["encoder_inputs"]}
    status = {x["unit_id"]: x for x in output["unit_results"]}
    candidates = {c["unit_id"]: c for c in output["chunks"] + [q["candidate"] for q in output["quarantined"]]}
    for row in inspection:
        u = row["unit"]; uid = u["unit_id"]; e = enc.get(uid, {})
        lines.append(f"| {u['citation_path']} | {status[uid].get('issue', status[uid]['status'])} | {e.get('tokens_with_special')} / {e.get('unknown_tokens')} | {(row['latest_scope_proposal'] or {}).get('scope_candidate', 'pending')} | pending / pending_review |")
    for row in inspection:
        u = row["unit"]; uid = u["unit_id"]
        lines += ["\n## " + u["citation_path"], "unit_id: `" + uid + "`", "Title: " + u["title"],
                  "Nguyên văn (JSON giữ cả whitespace cuối):", "```json\n" + json.dumps(u["text_original"], ensure_ascii=False) + "\n```",
                  "Cha thật: " + " → ".join(x["citation_path"] for x in reversed(row["ancestors"])),
                  "Children: " + str(row["children"]), "Spans:", "```json\n" + json.dumps(row["spans"], ensure_ascii=False, indent=2) + "\n```",
                  "Raw paragraph inspection:", "```json\n" + json.dumps(row["raw_inspection"], ensure_ascii=False, indent=2) + "\n```",
                  "Issue: " + canonical([q for q in output["issues"] if q["unit_id"] == uid]),
                  "Scope đã có (proposal, không phải quyết định): " + str((row["latest_scope_proposal"] or {}).get("reason"))]
        if uid in candidates:
            c = candidates[uid]
            lines += ["chunk_id: `" + c["chunk_id"] + "`", "text_for_search:", c["text_for_search"],
                      "encoder_text:", enc[uid]["encoder_text"]]
    lines += ["\nGiới hạn: không mở rộng dẫn chiếu ngoài Điều; không xác minh pháp lý/toàn văn; không lấy scope pending thành excluded."]
    return "\n\n".join(lines) + "\n"


def build(cm, dm, run):
    target = staging_path(run)
    if target.exists():
        raise ValueError("Output exists; choose a new staging run")
    output, inspection = calculate(cm, dm)
    target.mkdir(parents=True)
    for k, filename in EXPORTS.items():
        write_rows(target / filename, output[k])
    write_rows(target / "inspection.jsonl", inspection)
    (target / "articles_preview.md").write_text(render(output, inspection), encoding="utf8")
    report = {"technical_valid": True, "candidates": len(inspection), "preview": len(output["chunks"]),
              "blocked": len(inspection) - len(output["chunks"]), "quarantined": len(output["quarantined"]),
              "release_eligible": False, "roundtrip": "source_proof checked every target/title slice"}
    write_json(target / "validation_report.json", report)
    seal(target, {"manifest_type": VERSION, "snapshot_date": SNAPSHOT_DATE, "built_at": now(),
                  "origin": "agent_review", "human_reviewer_event_count": 0, "release_eligible": False,
                  "chunk_policy_version": builder.VERSION, "code_sha256": code_binding(),
                  "inputs": {n: {"manifest_ref": Path(p).resolve().relative_to(BASE_DIR).as_posix(), "sha256": digest(Path(p).read_bytes())}
                             for n, p in [("coverage", cm), ("dataset", dm)]}})
    return report


def validate(path):
    path = Path(path).resolve()
    m = check_files(path)
    if (m["manifest_type"] != VERSION or m["code_sha256"] != code_binding() or m["files"] != inventory(path.parent)
            or m["snapshot_date"] != SNAPSHOT_DATE or m["chunk_policy_version"] != builder.VERSION
            or m["origin"] != "agent_review" or m["human_reviewer_event_count"] != 0
            or m["release_eligible"] is not False or set(m["inputs"]) != {"coverage", "dataset"}):
        raise ValueError("Preview code/version/inventory mismatch")
    refs = {}
    for n, r in m["inputs"].items():
        refs[n] = resolve_ref(BASE_DIR, r["manifest_ref"])
        if digest(refs[n].read_bytes()) != r["sha256"]:
            raise ValueError("Input manifest changed")
    output, inspection = calculate(refs["coverage"], refs["dataset"])
    for k, filename in EXPORTS.items():
        if rows(path.parent / filename) != output[k]:
            raise ValueError("Replay mismatch: " + filename)
    if rows(path.parent / "inspection.jsonl") != inspection or (path.parent / "articles_preview.md").read_text(encoding="utf8") != render(output, inspection):
        raise ValueError("Inspection/render replay mismatch")
    expected_report = {"technical_valid": True, "candidates": len(inspection), "preview": len(output["chunks"]),
                       "blocked": len(inspection)-len(output["chunks"]), "quarantined": len(output["quarantined"]),
                       "release_eligible": False, "roundtrip": "source_proof checked every target/title slice"}
    if load(path.parent / "validation_report.json") != expected_report:
        raise ValueError("Validation report differs from replay")
    return {"technical_valid": True, "replay": True, "preview": len(output["chunks"]), "blocked": len(inspection)-len(output["chunks"]), "release_eligible": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build")
    b.add_argument("--coverage-manifest", type=Path, required=True)
    b.add_argument("--dataset-manifest", type=Path, required=True)
    b.add_argument("--run-dir", type=Path, required=True)
    v = sub.add_parser("validate"); v.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    try:
        result = build(a.coverage_manifest, a.dataset_manifest, a.run_dir) if a.action == "build" else validate(a.manifest)
        print(json.dumps(result, ensure_ascii=False))
        return 2 if result["blocked"] else 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
