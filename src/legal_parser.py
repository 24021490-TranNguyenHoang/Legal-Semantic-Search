"""Stage 4 CLI/bundle validator. Pending trees never authorize publication."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sys

from src.config import BASE_DIR, SNAPSHOT_DATE
from src.extraction_pipeline import validate_run as validate_extraction_run, utc_now
from src.ingestion import legal_tree
from src.ingestion import legal_tree_render
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, connect_sqlite, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows, schema_signature, expected_signature


SCHEMA_DIR = BASE_DIR / "schemas/legal_tree_v1"
DEFAULT_CONFIG = BASE_DIR / "config/legal_parser.v1.1.json"
POLICY_VERSION = "legal-tree.v1.1"
BLOCKERS = ["source_evidence_pending", "extraction_review_pending", "legal_tree_review_pending",
            "scope_and_applicability_not_assessed", "not_a_corpus_or_release"]
EXPORTS = {"units": "legal_units.pending.jsonl", "spans": "source_spans.pending.jsonl",
           "coverage": "coverage.jsonl", "issues": "quality_issues.jsonl",
           "tables": "tables.jsonl", "warning_reviews": "source_warning_review.jsonl"}


def tool_config():
    return {"parser": POLICY_VERSION, "python": sys.version.split()[0],
            "code_sha256": {"parser": digest(Path(legal_tree.__file__).read_bytes()),
                            "renderer": digest(Path(legal_tree_render.__file__).read_bytes()),
                            "pipeline": digest(Path(__file__).read_bytes())}}


def input_bundle(manifest_path, raw_root):
    result = validate_extraction_run(manifest_path, raw_root)
    if not result["technical_valid"] or not result["processing_success"]:
        raise ValueError("Stage 3 input invalid/incomplete: " + canonical(result))
    root = Path(manifest_path).resolve().parent
    records = read_rows(root / "extractions.pending.jsonl")
    sources = read_rows(root / "source_snapshot/files.pending.jsonl")
    if not records:
        raise ValueError("No extraction input")
    if len({r["law_id"] for r in records}) != len(records):
        raise ValueError("Multiple extractions per law require an explicit continuation/edition policy; parser does not guess a merge")
    if any(r["extraction"]["method"] != "doc_text" for r in records):
        raise ValueError("Parser supports DOCX block traces only; PDF structural parsing needs a separate policy")
    data = {}
    for r in records:
        text = resolve_ref(root, r["extraction"]["text_ref"]).read_text(encoding="utf-8")
        trace = load_json(resolve_ref(root, r["trace_ref"]))
        data[r["extraction"]["extraction_id"]] = (r, text, trace)
    return sources, records, data, read_rows(root / "quality_issues.jsonl"), result["dataset_kind"]


def compute(data, source_issues):
    result = {key: [] for key in EXPORTS}
    for record, text, trace in data.values():
        parsed = legal_tree.parse_extraction(record, text, trace, [q for q in source_issues if q["extraction_id"] == record["extraction"]["extraction_id"]])
        for key in result:
            result[key].extend(parsed[key])
    return result


def check_contracts(output):
    from jsonschema import Draft202012Validator
    import unicodedata
    for key, schema_name in (("units", "legal_unit.schema.json"), ("spans", "source_span.schema.json")):
        validator = Draft202012Validator(load_json(SCHEMA_DIR / schema_name))
        for row in output[key]:
            validator.validate(row)
            if any(isinstance(value, str) and ("\r" in value or unicodedata.normalize("NFC", value) != value) for value in row.values()):
                raise ValueError("Non-NFC/LF legal unit/span")


def database_rows(sources, records, output):
    laws = {u["unit_id"]: u["law_id"] for u in output["units"]}
    return {
        "pending_source": [{"file_id": s["file_id"], "law_id": s["law_id"], "source_status": "pending", "record_json": canonical(s)} for s in sources],
        "pending_extraction": [{"extraction_id": r["extraction"]["extraction_id"], "file_id": r["extraction"]["file_id"],
                                "law_id": r["law_id"], "review_status": "pending", "record_json": canonical(r)} for r in records],
        "pending_legal_unit": [{**u, "review_status": "pending"} for u in output["units"]],
        "pending_source_span": [{**s, "law_id": laws[s["unit_id"]]} for s in output["spans"]],
        "pending_parser_issue": [{"issue_id": q["issue_id"], "extraction_id": q["extraction_id"], "record_json": canonical(q)} for q in output["issues"]],
    }


def coverage_report(output, data):
    documents = []
    for eid, (record, text, _) in data.items():
        rows = [c for c in output["coverage"] if c["extraction_id"] == eid]
        counts = Counter()
        for c in rows:
            counts[c["category"]] += c["char_end"] - c["char_start"]
        units = [u for u in output["units"] if u["law_id"] == record["law_id"]]
        children = {u["parent_unit_id"] for u in units}
        leads = [u["unit_id"] for u in units if u["unit_type"] == "article" and u["unit_id"] in children and u["text_original"]]
        documents.append({"law_id": record["law_id"], "extraction_id": eid,
                          "char_count": len(text), "covered_code_points": sum(counts.values()),
                          "code_points_by_category": dict(sorted(counts.items())),
                          "unit_counts": dict(sorted(Counter(u["unit_type"] for u in units).items())),
                          "articles_with_lead_in": leads,
                          "table_count": sum(t["extraction_id"] == eid for t in output["tables"]),
                          "parser_issue_count": sum(q["extraction_id"] == eid for q in output["issues"])})
    return {"snapshot_date": SNAPSHOT_DATE, "coverage_kind": "technical_partition_not_legal_scope",
            "release_eligible": False, "documents": documents,
            "note": "All code points are accounted for, including supporting, unparsed/review and serialization separators. This is not proof of legal completeness."}


def examples(output):
    units, spans = output["units"], output["spans"]
    article22 = next((u for u in units if u["law_id"] == "36/2024/QH15" and u["unit_type"] == "article" and u["designation"] == "22"), None)
    article6 = next((u for u in units if u["law_id"] == "168/2024/NĐ-CP" and u["unit_type"] == "article" and u["designation"] == "6"), None)
    clause = next((u for u in units if article6 and u["parent_unit_id"] == article6["unit_id"] and u["unit_type"] == "clause" and u["designation"] == "1"), None)
    result = {}
    for key, target, description in (("A", article22, "Điều 22 Luật 36: đoạn dẫn và các Khoản"),
                                      ("B", clause, "Điều 6 Khoản 1 NĐ168: nội dung riêng và các Điểm")):
        selected = [] if target is None else [target] + [u for u in units if u["parent_unit_id"] == target["unit_id"]]
        result[key] = {"description": description, "root_unit_id": target["unit_id"] if target else None,
                       "units": [{"unit": u, "spans": [s for s in spans if s["unit_id"] == u["unit_id"]]} for u in selected]}
    return result


def inspect_content(run, raw_root):
    sources, records, data, source_issues, dataset_kind = input_bundle(run / "extraction_snapshot/manifest.json", raw_root)
    config = load_json(run / "config.json")
    # This policy is fixed for v1. A new behavior needs a new documented policy.
    if config != load_json(DEFAULT_CONFIG):
        raise ValueError("Unknown parser configuration/policy")
    for name in ("pending_schema.sql", "legal_unit.schema.json", "source_span.schema.json"):
        if (run / name).read_bytes() != (SCHEMA_DIR / name).read_bytes():
            raise ValueError("Parser contract mismatch: " + name)
    output = {key: read_rows(run / ref) for key, ref in EXPORTS.items()}
    check_contracts(output)
    errors = legal_tree.validate_tree(output["units"], output["spans"], data, output["coverage"])
    replay = compute(data, source_issues)
    for key in EXPORTS:
        if output[key] != replay[key]:
            errors.append("PARSER_REPLAY_MISMATCH: " + key)
    if load_json(run / "coverage_report.json") != coverage_report(output, data):
        errors.append("COVERAGE_REPORT_MISMATCH")
    if load_json(run / "examples.json") != examples(output):
        errors.append("EXAMPLES_MISMATCH")
    rendered = legal_tree_render.readable_artifacts(output, examples(output))
    actual_views = {p.relative_to(run).as_posix() for p in (run / "trees").rglob("*") if p.is_file()} | {"examples.txt"}
    if actual_views != set(rendered):
        errors.append("READABLE_ARTIFACT_SET")
    for ref, expected_text in rendered.items():
        if resolve_ref(run, ref).read_bytes() != expected_text.encode("utf-8"):
            errors.append("READABLE_TREE_REPLAY_MISMATCH: " + ref)
    with closing(connect_sqlite(run / "legal_tree.pending.sqlite", readonly=True)) as db:
        if schema_signature(db) != expected_signature((run / "pending_schema.sql").read_text(encoding="utf-8")):
            errors.append("SQLITE_SCHEMA_MISMATCH")
        if list(db.execute("PRAGMA foreign_key_check")):
            errors.append("SQLITE_FOREIGN_KEY")
        if [r[0] for r in db.execute("PRAGMA integrity_check")] != ["ok"]:
            errors.append("SQLITE_INTEGRITY")
        for table, rows in database_rows(sources, records, output).items():
            actual = [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
            if sorted(actual, key=canonical) != sorted(rows, key=canonical):
                errors.append("SQLITE_EXPORT_MISMATCH: " + table)
    return {"technical_valid": not errors, "processing_success": not errors, "errors": errors,
            "dataset_kind": dataset_kind, "document_count": len(records),
            "unit_count": len(output["units"]), "span_count": len(output["spans"]),
            "source_warning_count": len(source_issues), "parser_issue_count": len(output["issues"]),
            "table_count": len(output["tables"]), "release_eligible": False,
            "release_blockers": BLOCKERS, "legal_verification": "not_performed"}


def manifest_metadata(run, result):
    return {"manifest_type": "pending_legal_tree", "contract_version": POLICY_VERSION,
            "snapshot_date": SNAPSHOT_DATE, "dataset_kind": result["dataset_kind"],
            "extraction_manifest_sha256": digest((run / "extraction_snapshot/manifest.json").read_bytes()),
            "config_sha256": digest(canonical(load_json(run / "config.json")).encode("utf-8")),
            "tool": tool_config(), "unit_count": result["unit_count"], "span_count": result["span_count"],
            "release_eligible": False, "release_blockers": BLOCKERS}


def validate_run(manifest_path, raw_root=BASE_DIR):
    try:
        path = Path(manifest_path).resolve()
        run = path.parent
        if (run / "manifest.sha256").read_text(encoding="ascii").strip() != digest(path.read_bytes()):
            raise ValueError("MANIFEST_CHECKSUM mismatch")
        manifest = load_json(path)
        result = inspect_content(run, raw_root)
        expected = manifest_metadata(run, result)
        if set(manifest) != set(expected) | {"built_at", "files"}:
            result["errors"].append("MANIFEST_FIELDS")
        for key, value in expected.items():
            if manifest.get(key) != value or type(manifest.get(key)) is not type(value):
                result["errors"].append("MANIFEST_FIELD: " + key)
        if not manifest["built_at"].endswith("Z"):
            raise ValueError("built_at must be real UTC run time")
        datetime.fromisoformat(manifest["built_at"].replace("Z", "+00:00"))
        expected_paths = sorted(p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p.relative_to(run).as_posix() not in {"manifest.json", "manifest.sha256", "run_report.json"})
        if sorted(e["path"] for e in manifest["files"]) != expected_paths:
            result["errors"].append("MANIFEST_ARTIFACT_SET")
        for entry in manifest["files"]:
            value = resolve_ref(run, entry["path"]).read_bytes()
            if type(entry["size_bytes"]) is not int or len(value) != entry["size_bytes"] or digest(value) != entry["sha256"]:
                result["errors"].append("ARTIFACT_CHECKSUM: " + entry["path"])
        if load_json(run / "validation_report.json") != result:
            result["errors"].append("VALIDATION_REPORT_MISMATCH")
        result["technical_valid"] = result["processing_success"] = not result["errors"]
        return result
    except Exception as exc:
        return {"technical_valid": False, "processing_success": False, "errors": [f"{type(exc).__name__}: {exc}"],
                "release_eligible": False, "release_blockers": BLOCKERS, "legal_verification": "not_performed"}


def build_run(extraction_manifest, run_dir, raw_root=BASE_DIR, config_path=DEFAULT_CONFIG):
    staging_path(run_dir)
    extraction_manifest = Path(extraction_manifest).resolve()
    sources, records, data, source_issues, _ = input_bundle(extraction_manifest, raw_root)
    config = load_json(config_path)
    if config != load_json(DEFAULT_CONFIG):
        raise ValueError("Unknown parser configuration/policy")
    # Parse and validate before the first output/database write.
    output = compute(data, source_issues)
    check_contracts(output)
    errors = legal_tree.validate_tree(output["units"], output["spans"], data, output["coverage"])
    if errors:
        raise ValueError("Invalid legal tree: " + canonical(errors))
    with staged_run(run_dir, "pending_legal_tree", extraction_manifest) as (run, report):
        snapshot = run / "extraction_snapshot"
        source_manifest = load_json(extraction_manifest)
        for ref in [e["path"] for e in source_manifest["files"]] + ["manifest.json", "manifest.sha256"]:
            target = resolve_ref(snapshot, ref)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(resolve_ref(extraction_manifest.parent, ref).read_bytes())
        write_json(run / "config.json", config)
        for name in ("pending_schema.sql", "legal_unit.schema.json", "source_span.schema.json"):
            with (run / name).open("xb") as out:
                out.write((SCHEMA_DIR / name).read_bytes())
        for key, ref in EXPORTS.items():
            write_rows(run / ref, output[key])
        write_json(run / "coverage_report.json", coverage_report(output, data))
        write_json(run / "examples.json", examples(output))
        for ref, value in legal_tree_render.readable_artifacts(output, examples(output)).items():
            target = resolve_ref(run, ref)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8", newline="\n") as out:
                out.write(value)
        with closing(connect_sqlite(run / "legal_tree.pending.sqlite")) as db:
            db.executescript((run / "pending_schema.sql").read_text(encoding="utf-8"))
            with db:
                for table, rows in database_rows(sources, records, output).items():
                    for row in rows:
                        db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
        result = inspect_content(run, raw_root)
        if not result["technical_valid"]:
            raise ValueError(canonical(result))
        write_json(run / "validation_report.json", result)
        manifest = {**manifest_metadata(run, result), "built_at": utc_now(),
                    "files": [{"path": p.relative_to(run).as_posix(), "size_bytes": p.stat().st_size,
                               "sha256": digest(p.read_bytes())} for p in sorted(run.rglob("*")) if p.is_file()]}
        write_json(run / "manifest.json", manifest)
        with (run / "manifest.sha256").open("x", encoding="ascii", newline="\n") as out:
            out.write(digest((run / "manifest.json").read_bytes()) + "\n")
        result = validate_run(run / "manifest.json", raw_root)
        report.update(result)
        if not result["technical_valid"]:
            raise ValueError(canonical(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage 4 pending legal tree, no scope/applicability assessment or indexing")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("parse")
    build.add_argument("--extraction-manifest", required=True, type=Path)
    build.add_argument("--run-dir", required=True, type=Path)
    build.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    build.add_argument("--raw-root", type=Path, default=BASE_DIR)
    check = commands.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--raw-root", type=Path, default=BASE_DIR)
    check.add_argument("--require-release-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_run(args.extraction_manifest, args.run_dir, args.raw_root, args.config) if args.command == "parse" else validate_run(args.manifest, args.raw_root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ready = not (args.command == "validate" and args.require_release_ready and not result["release_eligible"])
    return 0 if result["technical_valid"] and result["processing_success"] and ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
