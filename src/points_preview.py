"""Narrow Stage4 point pilot + Article22 regression, all pending and offline."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

from src import chunk_preview_v2, chunk_preview, encoder_input
from src.article22_preview import mapping_data, require_preview_schema
from src.article22_stage6 import validate as validate_article22
from src.legal_parser import validate_run as validate_tree
from src.assessment_evidence import check_files, inventory, now, seal
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows

VERSION = "stage6-points-preview.v1"
DEFAULT_CONFIG = BASE_DIR / "config/stage6_points.v1.json"
BLOCKERS = ["LEGACY_DOCX_PROVENANCE_PENDING", "SOURCE_EXTRACTION_TREE_REVIEW_PENDING", "SCOPE_APPLICABILITY_DECISIONS_PENDING",
            "CROSS_REFERENCES_NOT_EXPANDED", "PREVIEW_NOT_A_CORPUS", "AGENT_REVIEW_NOT_REVIEWER_DECISION", "TOKEN_BUDGET_NOT_RELEASE_POLICY"]
EXPORTS = {"chunks.preview.jsonl": "chunks", "contexts.preview.jsonl": "contexts", "encoder_inputs.preview.jsonl": "encoder_inputs",
           "issues.jsonl": "issues", "quarantined.preview.jsonl": "quarantined", "unit_results.jsonl": "unit_results", "dependency_checks.jsonl": "dependency_checks"}


def code_binding():
    return {name: digest(Path(module.__file__).read_bytes()) for name, module in
            [("cli", sys.modules[__name__]), ("builder", chunk_preview_v2), ("v1_identity_proof", chunk_preview), ("encoder", encoder_input)]}


def tree_data(root):
    """Adapt real pending records, never create official document/source records."""
    tree = root / "tree"
    units = read_rows(tree/"legal_units.pending.jsonl")
    cfg = load_json(root.parent/"config.json")
    law = cfg["law_id"]
    source = tree/"extraction_snapshot/source_snapshot"
    document = next(d for d in read_rows(source/"documents.pending.jsonl") if d["law_id"] == law)
    files = [{**f["measured"], **{k: f[k] for k in ["file_id", "law_id", "source_set_id", "part_order"]}} for f in read_rows(source/"files.pending.jsonl") if f["law_id"] == law]
    records = [r for r in read_rows(tree/"extraction_snapshot/extractions.pending.jsonl") if r["law_id"] == law]
    extractions, traces = [], {}
    for r in records:
        e = copy.deepcopy(r["extraction"])
        e["text_ref"] = "tree/extraction_snapshot/"+e["text_ref"]
        extractions.append(e)
        traces[e["extraction_id"]] = load_json(resolve_ref(tree/"extraction_snapshot", r["trace_ref"]))
    selected = [u for u in units if u["law_id"] == law]
    ids = {u["unit_id"] for u in selected}
    issues = [dict(q, origin="stage4_parser") for q in read_rows(tree/"quality_issues.jsonl")]
    for q in read_rows(tree/"coverage.jsonl"):
        if q["category"] in {"needs_review", "unparsed"}:
            issues.append({**q, "issue_id": "coverage:"+q["locator_id"], "code": q["reason"], "origin": "stage4_coverage"})
    for q in read_rows(tree/"extraction_snapshot/quality_issues.jsonl"):
        r = next(r for r in read_rows(tree/"extraction_snapshot/extractions.pending.jsonl") if r["extraction"]["extraction_id"] == q["extraction_id"])
        item = {**q, "law_id": r["law_id"], "origin": "stage3_extraction"}
        if q["extraction_id"] in traces:
            nodes = [n for n in traces[q["extraction_id"]]["nodes"] if n["locator"] == q["locator"]]
            if len(nodes) == 1:
                item.update(char_start=nodes[0]["char_start"], char_end=nodes[0]["char_end"])
        issues.append(item)
    return {"document": {"law_id": law, "source_id": document["source_id"], "law_title": document["declared"]["law_title"],
                         "source_url": document["declared"]["source_url_candidate"], "metadata_origin": "pending_inventory_declaration_not_verified_source_url"},
            "files": files, "extractions": extractions, "units": selected,
            "spans": [s for s in read_rows(tree/"source_spans.pending.jsonl") if s["unit_id"] in ids], "issues": issues}


def check_config(config, tree_manifest, article22_manifest):
    if (config["artifact_version"] != VERSION or config["snapshot_date"] != SNAPSHOT_DATE
            or config["tree_manifest_sha256"] != digest(Path(tree_manifest).read_bytes())
            or config["article22_manifest_sha256"] != digest(Path(article22_manifest).read_bytes())
            or config["chunk"]["chunk_policy_version"] != chunk_preview_v2.VERSION):
        raise ValueError("Pilot policy/snapshot/input binding mismatch")


def calculate(run):
    config = load_json(run/"config.json")
    root = run/"inputs"
    baseline = run/"article22_snapshot"
    check_config(config, root/"tree/manifest.json", baseline/"manifest.json")
    validation = validate_tree(root/"tree/manifest.json", root)
    if not validation["technical_valid"] or not validation["processing_success"]:
        raise ValueError("Invalid Stage4 input: "+canonical(validation))
    if not validate_article22(baseline/"manifest.json")["processing_success"]:
        raise ValueError("Invalid Article22 baseline")
    encoder_config = load_json(baseline/"config.json")["encoder"]
    if digest(canonical(encoder_config).encode()) != config["encoder_config_sha256"]:
        raise ValueError("Encoder configuration must remain unchanged")
    assets = baseline/"baseline_snapshot/tokenizer_assets"
    encoder_input.require_config(encoder_config, assets)
    data = tree_data(root)
    by = {u["unit_id"]: u for u in data["units"]}
    parent = by[config["parent_unit_id"]]
    if parent["unit_type"] != "clause" or {u["unit_id"] for u in data["units"] if u["parent_unit_id"] == parent["unit_id"]} != set(config["chunk"]["target_unit_ids"]):
        raise ValueError("Narrow pilot requires exactly the declared parent's real children")
    runtime = {}
    def encode(texts):
        measured = encoder_input.encode_inputs(texts, encoder_config, assets)
        runtime.update({k: v for k, v in measured.items() if k != "rows"})
        return measured["rows"]
    result = chunk_preview_v2.build_chunks(data, root, config["chunk"], BLOCKERS, encode, reference_prefix="inputs/")
    require_preview_schema(result["chunks"])
    # Rebuild the old legal content under the explicit NEW policy, keeping the
    # old artifacts/code intact; differences in IDs must be explained field by field.
    old_root = baseline/"baseline_snapshot/mapping_snapshot"
    regression_data = mapping_data(old_root)
    regression_data["issues"] = []  # Scoped PDF mapping; full baseline validator above retains page21 warning/blockers.
    old_chunks = read_rows(baseline/"chunks.preview.jsonl")
    old_contexts = read_rows(baseline/"contexts.preview.jsonl")
    regression_config = {**config["chunk"], "target_unit_ids": [c["unit_id"] for c in old_chunks], "required_context_fields": ["title", "text_original"]}
    regression = chunk_preview_v2.build_chunks(regression_data, old_root, regression_config, old_chunks[0]["release_blockers"], encode,
                                                reference_prefix="article22_snapshot/baseline_snapshot/mapping_snapshot/")
    comparisons = []
    for c in regression["chunks"]:
        old = next(x for x in old_chunks if x["unit_id"] == c["unit_id"])
        before = chunk_preview.chunk_identity(old, [x for x in old_contexts if x["chunk_id"] == old["chunk_id"]])
        after = chunk_preview.chunk_identity(c, [x for x in regression["contexts"] if x["chunk_id"] == c["chunk_id"]])
        differences = [k for k in before if before[k] != after[k]]
        if differences != ["chunk_policy_version"] or any(c[k] != old[k] for k in ["text_original", "context_text", "text_for_search", "content_sha256"]):
            raise ValueError("Unexpected Article22 identity/content regression")
        comparisons.append({"unit_id": c["unit_id"], "before_chunk_id": old["chunk_id"], "after_chunk_id": c["chunk_id"],
                            "changed_identity_fields": differences, "content_and_context_equal": True})
    if len(comparisons) != 3 or regression["issues"]:
        raise ValueError("Article22 regression must retain all three whole clauses")
    candidates = result["chunks"]+[q["candidate"] for q in result["quarantined"]]
    inventory_report = {"origin": "agent_review", "law_id": config["law_id"], "parent_unit_id": parent["unit_id"],
                        "selected_target_ids": config["chunk"]["target_unit_ids"], "source_url_origin": data["document"]["metadata_origin"],
                        "upstream_issue_count": len(data["issues"]), "checked_fields": [{"unit_id": c["unit_id"], "source_locator": c["source_locator"]} for c in candidates],
                        "upstream_issues": data["issues"], "source_status": "pending", "reviewer_event_created": False}
    report = {"technical_valid": True, "processing_success": not any(q["code"] != "TOKEN_BUDGET_EXCEEDED" for q in result["issues"]),
              "all_candidates_within_budget": not result["issues"], "requested_target_count": len(config["chunk"]["target_unit_ids"]),
              "chunk_count": len(result["chunks"]), "context_count": len(result["contexts"]), "blocked_count": len(result["issues"]),
              "quarantine_count": len(result["quarantined"]), "token_limit": config["chunk"]["token_limit"], "model_max_tokens": encoder_config["model_max_tokens"],
              "snapshot_date": SNAPSHOT_DATE, "origin": "agent_review", "human_reviewer_event_count": 0,
              "source_status": "pending", "extraction_status": "pending", "applicability_status": "pending_review",
              "preview_only": True, "release_eligible": False, "corpus_created": False, "release_blockers": BLOCKERS,
              "inference_loaded": False, "truncation": False, "article22_regression_count": len(comparisons),
              "article22_changed_identity_fields": ["chunk_policy_version"]}
    return result, regression, runtime, comparisons, inventory_report, report


def render(run, result, report):
    data = tree_data(run/"inputs")
    by = {u["unit_id"]: u for u in data["units"]}
    lines = ["# PREVIEW Điểm — Điều 6 Khoản 1 NĐ168", "", "origin=agent_review; nguồn DOCX legacy và extraction/cây/hiệu lực pending. Không phải corpus phục vụ.",
             "URL metadata lấy từ inventory chưa xác minh; không phải bằng chứng URL tải DOCX hoặc provenance toàn file.", "",
             "Không mở rộng dẫn chiếu ngoài cây cha. Chưa đối chiếu các chế tài/ngoại lệ ở đơn vị khác; context đầy đủ theo policy không chứng minh đủ mọi điều kiện pháp lý.", "",
             "| Citation | Trạng thái | Token encoder (gồm special) | Unknown | Ngưỡng |", "|---|---|---:|---:|---:|"]
    rows = [(c, [x for x in result["contexts"] if x["chunk_id"] == c["chunk_id"]], "preview_only") for c in result["chunks"]]
    rows += [(q["candidate"], q["contexts"], "quarantine: TOKEN_BUDGET_EXCEEDED") for q in result["quarantined"]]
    rows.sort(key=lambda row: by[row[0]["unit_id"]]["ordinal"])
    for c, ctx, status in rows:
        e = next(e for e in result["encoder_inputs"] if e["chunk_id"] == c["chunk_id"])
        lines.append(f"| {c['citation_path']} | {status} | {e['tokens_with_special']} | {e['unknown_tokens']} | {report['token_limit']} |")
    for c, ctx, status in rows:
        e = next(e for e in result["encoder_inputs"] if e["chunk_id"] == c["chunk_id"])
        lines += ["", "## "+c["citation_path"], "", "Trạng thái: "+status, "", "Chunk ID: `"+c["chunk_id"]+"`", "", "Nguyên văn Điểm:", "```text", c["text_original"], "```", ""]
        for x in ctx:
            u = by[x["unit_id"]]
            lines += [f"Context {x['context_order']} — {u['citation_path']}, field={x['field_name']}, offsets [{x['char_start']},{x['char_end']}):",
                      "```text", u[x["field_name"]][x["char_start"]:x["char_end"]], "```", "Nguồn: "+x["source_locator"], ""]
        lines += ["text_for_search:", "```text", c["text_for_search"], "```", "", "encoder_text (bản sao đã tiền xử lý):", "```text", e["encoder_text"], "```", "", "Nguồn target: "+c["source_locator"], ""]
    lines += ["## Các issue/blocker", "", canonical(result["issues"]), "", "Không bỏ context hoặc truncate để vừa budget; candidate quarantine giữ đầy đủ nguyên văn/context/spans/encoder input.", "", "Inventory warning/coverage và kiểm ảnh hưởng từng target: source_inspection.json, dependency_checks.jsonl. Không suy verified từ việc không có issue giao vùng.", ""]
    return "\n".join(lines)


def validate(manifest_path):
    p = Path(manifest_path).resolve()
    if p.name != "manifest.json":
        raise ValueError("Expected manifest.json")
    run = p.parent
    m = check_files(p)
    if (m["manifest_type"] != VERSION or m["files"] != inventory(run) or m["code_sha256"] != code_binding()
            or m["config_sha256"] != digest((run/"config.json").read_bytes()) or m["snapshot_date"] != SNAPSHOT_DATE
            or m["origin"] != "agent_review" or m["human_reviewer_event_count"] != 0
            or m["release_eligible"] is not False or m["preview_only"] is not True or m["corpus_version"] is not None):
        raise ValueError("Point preview binding/pending/origin mismatch")
    result, regression, runtime, comparison, inspection, report = calculate(run)
    for prefix, value in [("", result), ("article22_regression/", regression)]:
        for file, key in EXPORTS.items():
            if read_rows(run/(prefix+file)) != value[key]:
                raise ValueError("Point preview replay mismatch: "+prefix+file)
    for file, value in [("runtime.json", runtime), ("article22_comparison.json", comparison), ("source_inspection.json", inspection), ("validation_report.json", report)]:
        if load_json(run/file) != value:
            raise ValueError("Point preview replay mismatch: "+file)
    if (run/"chunks_preview.md").read_text(encoding="utf8") != render(run, result, report):
        raise ValueError("Readable preview differs from replay")
    return report


def build(tree_manifest, article22_manifest, run_dir, config_path=DEFAULT_CONFIG, raw_root=BASE_DIR):
    target = staging_path(run_dir)
    tree, baseline = Path(tree_manifest).resolve().parent, Path(article22_manifest).resolve().parent
    if tree in target.parents or baseline in target.parents:
        raise ValueError("Output must not be nested in an old run")
    config = load_json(config_path)
    check_config(config, tree_manifest, article22_manifest)
    if not validate_tree(tree_manifest, raw_root)["technical_valid"] or not validate_article22(article22_manifest)["processing_success"]:
        raise ValueError("Invalid upstream bundle")
    files = read_rows(tree/"extraction_snapshot/source_snapshot/files.pending.jsonl")
    for f in files:
        if digest(resolve_ref(raw_root, f["measured"]["raw_file_ref"]).read_bytes()) != f["measured"]["sha256"]:
            raise ValueError("Raw source hash mismatch")
    with staged_run(run_dir, VERSION, tree_manifest) as (run, run_report):
        (run/"inputs").mkdir()
        shutil.copytree(tree, run/"inputs/tree")
        for f in files:
            p = resolve_ref(run/"inputs", f["measured"]["raw_file_ref"])
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolve_ref(raw_root, f["measured"]["raw_file_ref"]), p)
        # Stage2 validation also checks the inventory declaration at raw_root.
        # Preserve its actual bytes instead of weakening upstream validation.
        documents = read_rows(tree/"extraction_snapshot/source_snapshot/documents.pending.jsonl")
        for ref in sorted({d["declared"]["inventory_ref"] for d in documents}):
            p = resolve_ref(run/"inputs", ref)
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolve_ref(raw_root, ref), p)
        shutil.copytree(baseline, run/"article22_snapshot")
        write_json(run/"config.json", config)
        result, regression, runtime, comparison, inspection, report = calculate(run)
        (run/"article22_regression").mkdir()
        for prefix, value in [("", result), ("article22_regression/", regression)]:
            for file, key in EXPORTS.items():
                write_rows(run/(prefix+file), value[key])
        for file, value in [("runtime.json", runtime), ("article22_comparison.json", comparison), ("source_inspection.json", inspection), ("validation_report.json", report)]:
            write_json(run/file, value)
        (run/"chunks_preview.md").write_text(render(run, result, report), encoding="utf8", newline="\n")
        seal(run, {"manifest_type": VERSION, "built_at": now(), "snapshot_date": SNAPSHOT_DATE, "code_sha256": code_binding(),
                   "config_sha256": digest((run/"config.json").read_bytes()), "origin": "agent_review", "human_reviewer_event_count": 0,
                   "release_eligible": False, "preview_only": True, "corpus_version": None})
        run_report.update(report)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description="Pending Stage6 leaf-point preview; no legal decisions/index/inference")
    sub = p.add_subparsers(dest="command", required=True)
    create = sub.add_parser("build")
    create.add_argument("--tree-manifest", type=Path, required=True)
    create.add_argument("--article22-manifest", type=Path, required=True)
    create.add_argument("--run-dir", type=Path, required=True)
    create.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    create.add_argument("--raw-root", type=Path, default=BASE_DIR)
    check = sub.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        r = build(args.tree_manifest, args.article22_manifest, args.run_dir, args.config, args.raw_root) if args.command == "build" else validate(args.manifest)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["processing_success"] and r["all_candidates_within_budget"] else 2
    except Exception as exc:
        print(json.dumps({"technical_valid": False, "errors": [str(exc)], "release_eligible": False}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
