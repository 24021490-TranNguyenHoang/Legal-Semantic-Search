"""Stage 3 traced extraction into a new pending-only staging run."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import sys
import unicodedata

from src.config import BASE_DIR, SNAPSHOT_DATE
from src.ingestion import extractors, extraction_normalizer
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import (canonical, connect_sqlite, digest, require_contract,
                                 resolve_ref, validate_extraction)
from src.source_registry import (ARTIFACTS as SOURCE_ARTIFACTS, inspect_bundle, load_json,
                                 read_rows, write_rows, schema_signature, expected_signature)

SCHEMA_DIR = BASE_DIR / "schemas" / "extraction_v1"
DEFAULT_CONFIG = BASE_DIR / "config" / "extraction.v1.json"
BLOCKERS = ["PENDING_SOURCE_EVIDENCE", "PENDING_EXTRACTION_REVIEW", "DOWNSTREAM_RELEASE_GATES_NOT_RUN"]


def require_profile(name, value):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = load_json(SCHEMA_DIR / f"{name}.schema.json")
    errors = [e.message for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value)]
    if errors:
        raise ValueError(f"{name}: " + "; ".join(errors))


def tool_config(mime):
    code = {"pipeline": Path(__file__), "reader": Path(extractors.__file__),
            "normalizer": Path(extraction_normalizer.__file__)}
    versions = {"python": platform.python_version(), "unicode": unicodedata.unidata_version,
                "reader": "stdlib-xml.v1" if mime == extractors.DOCX_MIME else "pdfplumber"}
    if mime == "application/pdf":
        versions.update({name: importlib.metadata.version(name) for name in ("pdfplumber", "pdfminer.six")})
    return canonical({"versions": versions, "code_sha256": {k: digest(p.read_bytes()) for k, p in code.items()}})


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def trace_content(trace):
    return {**trace, "nodes": [{k: v for k, v in n.items() if k not in
                               {"locator_id", "parent_locator_id", "extraction_id"}} for n in trace["nodes"]]}


def issue_record(file_id, extraction_id, issue, ordinal):
    payload = {"file_id": file_id, "extraction_id": extraction_id, **issue, "ordinal": ordinal}
    return {"issue_id": "xqi_" + digest(canonical(payload).encode("utf-8")), **payload, "status": "pending"}


def extract_file(source, raw_root, config, *, created_at=None):
    measured = source["measured"]
    data = resolve_ref(raw_root, measured["raw_file_ref"]).read_bytes()
    if len(data) != measured["size_bytes"] or digest(data) != measured["sha256"]:
        raise ValueError("Raw size/hash mismatch before extraction")
    tree, issues, method = extractors.read_source(data, measured["mime_type"], config)
    text, trace = extraction_normalizer.serialize(tree)
    tool_version = tool_config(measured["mime_type"])
    config_sha = digest(canonical(config).encode("utf-8"))
    text_sha = digest(text.encode("utf-8"))
    trace_sha = digest(canonical(trace).encode("utf-8"))
    identity = {"identity_schema": "extraction.v1", "file_id": source["file_id"],
                "source_raw_sha256": measured["sha256"], "method": method,
                "tool_version": tool_version, "config_sha256": config_sha,
                "text_sha256": text_sha, "trace_content_sha256": trace_sha}
    extraction_id = "e_" + digest(canonical(identity).encode("utf-8"))
    for item in trace["nodes"]:
        item["extraction_id"] = extraction_id
        item["locator_id"] = "l_" + digest(canonical({"extraction_id": extraction_id,
                                                       "node_index": item["node_index"],
                                                       "locator": item["locator"]}).encode("utf-8"))
        parent = item["parent_index"]
        item["parent_locator_id"] = None if parent is None else trace["nodes"][parent]["locator_id"]
    prefix = f"extractions/{extraction_id}"
    metadata = {"extraction_id": extraction_id, "file_id": source["file_id"], "method": method,
                "tool_version": tool_version, "text_ref": prefix + "/normalized.txt", "text_sha256": text_sha,
                "char_count": len(text), "review_status": "pending", "created_at": created_at or utc_now()}
    require_contract("extraction", metadata)
    technical = "partial" if any(q["severity"] == "error" for q in issues) else "complete"
    trace_bytes = (canonical(trace) + "\n").encode("utf-8")
    record = {"extraction": metadata, "law_id": source["law_id"], "source_status": "pending",
              "technical_status": technical, "config_sha256": config_sha, "source_raw_sha256": measured["sha256"],
              "trace_ref": prefix + "/trace.json", "trace_sha256": digest(trace_bytes), "trace_content_sha256": trace_sha}
    require_profile("pending_extraction", record)
    return record, text.encode("utf-8"), trace_bytes, trace, issues


def status_record(source, record, issues):
    return {"file_id": source["file_id"], "law_id": source["law_id"], "source_status": "pending",
            "source_raw_sha256": source["measured"]["sha256"],
            "extraction_id": record["extraction"]["extraction_id"] if record else None,
            "technical_status": record["technical_status"] if record else "quarantined",
            "needs_ocr_review": any(q["code"] == "PDF_PAGE_NO_TEXT" for q in issues), "issue_count": len(issues)}


def database_rows(sources, records, traces, issues):
    return {
        "pending_source": [{"file_id": s["file_id"], "law_id": s["law_id"], "record_json": canonical(s)} for s in sources],
        "pending_extraction": [{"extraction_id": r["extraction"]["extraction_id"],
                                "file_id": r["extraction"]["file_id"], "review_status": "pending",
                                "technical_status": r["technical_status"], "record_json": canonical(r)} for r in records],
        "pending_locator": [{"locator_id": n["locator_id"], "extraction_id": n["extraction_id"],
                             "parent_locator_id": n["parent_locator_id"], "char_start": n["char_start"],
                             "char_end": n["char_end"], "record_json": canonical(n)} for trace in traces for n in trace["nodes"]],
        "pending_extraction_issue": [{"issue_id": q["issue_id"], "file_id": q["file_id"],
                                      "extraction_id": q["extraction_id"], "record_json": canonical(q)} for q in issues],
    }


def inspect_content(run, raw_root):
    source_check = inspect_bundle(run / "source_snapshot/manifest.json", raw_root)
    if not source_check["technical_valid"]:
        raise ValueError("Source snapshot invalid: " + canonical(source_check))
    sources = read_rows(run / "source_snapshot/files.pending.jsonl")
    config = load_json(run / "config.json")
    require_profile("config", config)
    for name in ("config.schema.json", "pending_extraction.schema.json", "pending_schema.sql"):
        if (run / name).read_bytes() != (SCHEMA_DIR / name).read_bytes():
            raise ValueError(f"Extraction contract/schema mismatch: {name}")
    records = read_rows(run / "extractions.pending.jsonl")
    statuses = read_rows(run / "file_status.jsonl")
    issues = read_rows(run / "quality_issues.jsonl")
    errors, traces = [], []
    mapping = {r["extraction"]["file_id"]: r for r in records}
    status_map = {s["file_id"]: s for s in statuses}
    if len(mapping) != len(records) or len(status_map) != len(statuses):
        errors.append("DUPLICATE_ID: file/extraction status")
    if set(status_map) != {s["file_id"] for s in sources} or set(mapping) - set(status_map):
        errors.append("SOURCE_RELATIONSHIP: source/status/extraction set differs")
    if len({q["issue_id"] for q in issues}) != len(issues):
        errors.append("DUPLICATE_ID: quality issue")
    for source in sources:
        file_id = source["file_id"]
        record, status = mapping.get(file_id), status_map.get(file_id)
        own_issues = [q for q in issues if q["file_id"] == file_id]
        for q in own_issues:
            payload = {k: v for k, v in q.items() if k not in {"issue_id", "status"}}
            if q["issue_id"] != "xqi_" + digest(canonical(payload).encode("utf-8")) or q["status"] != "pending":
                errors.append(f"ISSUE_ID_OR_STATUS: {file_id}")
        if not record:
            if not own_issues or not any(q["severity"] == "error" for q in own_issues):
                errors.append(f"UNREPORTED_QUARANTINE: {file_id}")
            if status != status_record(source, None, own_issues) or any(q["extraction_id"] is not None for q in own_issues):
                errors.append(f"QUARANTINE_RELATIONSHIP: {file_id}")
            continue
        require_profile("pending_extraction", record)
        metadata = record["extraction"]
        errors.extend(validate_extraction(metadata, [{"file_id": s["file_id"]} for s in sources], run))
        actual_text = resolve_ref(run, metadata["text_ref"]).read_bytes()
        actual_trace_bytes = resolve_ref(run, record["trace_ref"]).read_bytes()
        trace = json.loads(actual_trace_bytes)
        traces.append(trace)
        if digest(actual_trace_bytes) != record["trace_sha256"]:
            errors.append(f"TRACE_CHECKSUM: {file_id}")
        # Replay the reader and serializer against immutable raw, proving locators,
        # order, normalization fragments, separators, offsets and quote checksums.
        expected, text_bytes, trace_bytes, _, reader_issues = extract_file(
            source, raw_root, config, created_at=metadata["created_at"])
        if record != expected or actual_text != text_bytes or actual_trace_bytes != trace_bytes:
            errors.append(f"EXTRACTION_REPLAY_MISMATCH: {file_id}")
        expected_issues = [issue_record(file_id, metadata["extraction_id"], q, i) for i, q in enumerate(reader_issues)]
        if own_issues != expected_issues or status != status_record(source, record, own_issues):
            errors.append(f"EXTRACTION_STATUS_OR_ISSUES: {file_id}")
        if digest(canonical(trace_content(trace)).encode("utf-8")) != record["trace_content_sha256"]:
            errors.append(f"TRACE_IDENTITY: {file_id}")
    with closing(connect_sqlite(run / "extraction.pending.sqlite", readonly=True)) as db:
        if schema_signature(db) != expected_signature((SCHEMA_DIR / "pending_schema.sql").read_text(encoding="utf-8")):
            errors.append("SQLITE_SCHEMA_MISMATCH")
        for row in db.execute("PRAGMA foreign_key_check"):
            errors.append(f"FOREIGN_KEY: {tuple(row)}")
        if [r[0] for r in db.execute("PRAGMA integrity_check")] != ["ok"]:
            errors.append("SQLITE_INTEGRITY")
        for table, rows in database_rows(sources, records, traces, issues).items():
            actual = [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
            if sorted(actual, key=canonical) != sorted(rows, key=canonical):
                errors.append(f"SQLITE_EXPORT_MISMATCH: {table}")
    processing = not any(s["technical_status"] in {"partial", "quarantined"} for s in statuses)
    return {"technical_valid": not errors, "errors": errors, "processing_success": processing,
            "dataset_kind": source_check["dataset_kind"], "source_pending_count": len(sources),
            "extraction_count": len(records), "locator_count": sum(len(t["nodes"]) for t in traces),
            "quarantined_file_count": sum(s["technical_status"] == "quarantined" for s in statuses),
            "partial_file_count": sum(s["technical_status"] == "partial" for s in statuses), "issue_count": len(issues),
            "release_eligible": False, "release_blockers": BLOCKERS, "legal_verification": "not_performed"}


def validate_run(manifest_path, raw_root=BASE_DIR):
    try:
        manifest_path = Path(manifest_path).resolve()
        run = manifest_path.parent
        if (run / "manifest.sha256").read_text(encoding="ascii").strip() != digest(manifest_path.read_bytes()):
            raise ValueError("MANIFEST_CHECKSUM mismatch")
        manifest = load_json(manifest_path)
        report = inspect_content(run, raw_root)
        expected = {"manifest_type": "pending_extraction", "contract_version": "trace-extraction.v1",
                    "snapshot_date": SNAPSHOT_DATE, "source_manifest_sha256": digest((run / "source_snapshot/manifest.json").read_bytes()),
                    "config_sha256": digest(canonical(load_json(run / "config.json")).encode("utf-8")),
                    "dataset_kind": report["dataset_kind"], "extraction_count": report["extraction_count"],
                    "release_eligible": False, "release_blockers": BLOCKERS}
        if set(manifest) != set(expected) | {"built_at", "files"}:
            report["errors"].append("MANIFEST_FIELDS mismatch")
        for key, value in expected.items():
            if manifest.get(key) != value or type(manifest.get(key)) is not type(value):
                report["errors"].append(f"MANIFEST_FIELD mismatch: {key}")
        stamp = manifest["built_at"]
        if not isinstance(stamp, str) or not stamp.endswith("Z"):
            raise ValueError("Invalid built_at")
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        listed = [e["path"] for e in manifest["files"]]
        expected_files = sorted(p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and
                                p.relative_to(run).as_posix() not in {"manifest.json", "manifest.sha256", "run_report.json"})
        if sorted(listed) != expected_files:
            report["errors"].append("MANIFEST_ARTIFACT_SET mismatch")
        for entry in manifest["files"]:
            data = resolve_ref(run, entry["path"]).read_bytes()
            if digest(data) != entry["sha256"] or type(entry["size_bytes"]) is not int or len(data) != entry["size_bytes"]:
                report["errors"].append(f"ARTIFACT_CHECKSUM mismatch: {entry['path']}")
        if load_json(run / "validation_report.json") != report:
            report["errors"].append("VALIDATION_REPORT mismatch")
        report["technical_valid"] = not report["errors"]
        return report
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        return {"technical_valid": False, "processing_success": False, "release_eligible": False,
                "release_blockers": BLOCKERS, "errors": [str(exc)], "legal_verification": "not_performed"}


class ExtractionBatchError(ValueError):
    def __init__(self, result):
        self.result = result
        super().__init__("Batch contains partial/quarantined files; inspect manifest and quality_issues.jsonl")


def build_run(source_manifest, run_dir, raw_root=BASE_DIR, config_path=DEFAULT_CONFIG):
    staging_path(run_dir)
    source_manifest = Path(source_manifest).resolve()
    source_check = inspect_bundle(source_manifest, raw_root)
    if not source_check["technical_valid"]:
        raise ValueError("Source registration invalid: " + canonical(source_check))
    config = load_json(config_path)
    require_profile("config", config)
    sources = read_rows(source_manifest.parent / "files.pending.jsonl")
    with staged_run(run_dir, "traced_extraction", source_manifest) as (run, run_report):
        snapshot = run / "source_snapshot"
        snapshot.mkdir()
        for name in (*SOURCE_ARTIFACTS, "manifest.json", "manifest.sha256"):
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(resolve_ref(source_manifest.parent, name).read_bytes())
        write_json(run / "config.json", config)
        for name in ("config.schema.json", "pending_extraction.schema.json", "pending_schema.sql"):
            with (run / name).open("xb") as output:
                output.write((SCHEMA_DIR / name).read_bytes())
        records, statuses, issues, traces = [], [], [], []
        for source in sources:
            try:
                record, text, trace_bytes, trace, reader_issues = extract_file(source, raw_root, config)
            except Exception as exc:
                code = "UNSUPPORTED_SOURCE" if isinstance(exc, extractors.UnsupportedSource) else "SOURCE_EXTRACTION_FAILED"
                own = [issue_record(source["file_id"], None,
                                    {"code": code, "severity": "error", "locator": {"raw_file_ref": source["measured"]["raw_file_ref"]},
                                     "detail": f"{type(exc).__name__}: {exc}"}, 0)]
                statuses.append(status_record(source, None, own))
                issues.extend(own)
                continue
            for ref, data in ((record["extraction"]["text_ref"], text), (record["trace_ref"], trace_bytes)):
                target = resolve_ref(run, ref)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(data)
            own = [issue_record(source["file_id"], record["extraction"]["extraction_id"], q, i) for i, q in enumerate(reader_issues)]
            records.append(record)
            traces.append(trace)
            statuses.append(status_record(source, record, own))
            issues.extend(own)
        for name, values in (("extractions.pending.jsonl", records), ("file_status.jsonl", statuses), ("quality_issues.jsonl", issues)):
            write_rows(run / name, values)
        with closing(connect_sqlite(run / "extraction.pending.sqlite")) as db:
            db.executescript((run / "pending_schema.sql").read_text(encoding="utf-8"))
            with db:
                for table, rows in database_rows(sources, records, traces, issues).items():
                    for row in rows:
                        db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
        result = inspect_content(run, raw_root)
        if not result["technical_valid"]:
            raise ValueError(canonical(result))
        write_json(run / "validation_report.json", result)
        manifest = {"manifest_type": "pending_extraction", "contract_version": "trace-extraction.v1",
                    "snapshot_date": SNAPSHOT_DATE, "dataset_kind": result["dataset_kind"], "built_at": utc_now(),
                    "source_manifest_sha256": digest((snapshot / "manifest.json").read_bytes()),
                    "config_sha256": digest(canonical(config).encode("utf-8")), "extraction_count": len(records),
                    "release_eligible": False, "release_blockers": BLOCKERS,
                    "files": [{"path": p.relative_to(run).as_posix(), "size_bytes": p.stat().st_size,
                               "sha256": digest(p.read_bytes())} for p in sorted(run.rglob("*")) if p.is_file()]}
        write_json(run / "manifest.json", manifest)
        with (run / "manifest.sha256").open("x", encoding="ascii", newline="\n") as output:
            output.write(digest((run / "manifest.json").read_bytes()) + "\n")
        result = validate_run(run / "manifest.json", raw_root)
        if not result["technical_valid"]:
            raise ValueError(canonical(result))
        run_report.update(result)
        if not result["processing_success"]:
            raise ExtractionBatchError(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage 3 pending extraction with locators; no cleaning/OCR/models")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("extract")
    build.add_argument("--source-manifest", type=Path, required=True)
    build.add_argument("--run-dir", type=Path, required=True)
    build.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    build.add_argument("--raw-root", type=Path, default=BASE_DIR)
    check = commands.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--raw-root", type=Path, default=BASE_DIR)
    check.add_argument("--require-release-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_run(args.source_manifest, args.run_dir, args.raw_root, args.config) if args.command == "extract" else validate_run(args.manifest, args.raw_root)
    except ExtractionBatchError as exc:
        result = exc.result
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ready = not (args.command == "validate" and args.require_release_ready and not result["release_eligible"])
    return 0 if result["technical_valid"] and result["processing_success"] and ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
