"""Stage 2: pending source registration and strict, read-only bundle validation.

No extraction, legal verification, corpus promotion, model or index build occurs here.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from zipfile import ZipFile, BadZipFile
import xml.etree.ElementTree as ET

from src.config import BASE_DIR, SNAPSHOT_DATE
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import (SCHEMA_DIR, SCHEMA_NAMES, canonical, connect_sqlite,
                                 digest, file_identity, require_contract, resolve_ref)

DEFAULT_REGISTRY = BASE_DIR / "config" / "source_registration.v1.json"
DOCUMENT_EVIDENCE = ("issued_date", "source_url", "edition", "verification_ref",
                     "reviewer_ref", "verified_at")
FILE_EVIDENCE = ("download_url", "retrieved_at", "edition", "verification_ref",
                 "source_set_complete")
ARTIFACTS = ("content.sqlite", "pending.sqlite", "schema.sql", "pending_schema.sql",
             "registration_input.json", "documents.pending.jsonl", "files.pending.jsonl",
             "quality_issues.jsonl", "validation_report.json") + tuple(
                 f"contracts/{name}.schema.json" for name in SCHEMA_NAMES)
TABLES = ("legal_document", "source_file", "extraction", "legal_unit", "source_span",
          "legal_reference", "corpus", "corpus_document", "unit_assessment", "chunk",
          "chunk_context", "quality_issue")
BLOCKERS = ["PENDING_SOURCE_EVIDENCE", "DOWNSTREAM_RELEASE_GATES_NOT_RUN"]


def load_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def detect_docx(data):
    """Inspect package type, not paragraph content; do not perform extraction."""
    from io import BytesIO
    try:
        with ZipFile(BytesIO(data)) as archive:
            types = ET.fromstring(archive.read("[Content_Types].xml"))
            if "word/document.xml" not in archive.namelist():
                raise ValueError("Missing word/document.xml")
            match = any(e.get("PartName") == "/word/document.xml" and e.get("ContentType") ==
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
                        for e in types)
            if not match:
                raise ValueError("Not a DOCX document package")
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError(f"Invalid DOCX package: {exc}") from exc
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def detect_source_mime(data):
    # Stage 3 needs controlled PDF fixtures. Registration only recognizes the
    # PDF header; parsing failures are handled/quarantined by the extraction CLI.
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return detect_docx(data)


def registration_records(registry, raw_root):
    require_contract("registration", registry)
    documents, files, issues = [], [], []
    laws, source_ids, ids, byte_keys, part_keys, paths = set(), set(), set(), set(), set(), set()
    for item in registry["documents"]:
        law_id, source_id = item["law_id"], item["source_id"]
        if law_id in laws or source_id in source_ids:
            raise ValueError("Duplicate law_id/source_id in registration")
        laws.add(law_id)
        source_ids.add(source_id)
        inventory = resolve_ref(raw_root, item["declared"]["inventory_ref"])
        if not inventory.is_file():
            raise ValueError(f"Inventory declaration does not exist: {inventory}")
        document = {**item, "evidence": dict.fromkeys(DOCUMENT_EVIDENCE), "status": "pending"}
        require_contract("pending_document", document)
        documents.append(document)
    for item in registry["files"]:
        if item["law_id"] not in laws:
            raise ValueError(f"File refers to unknown law_id: {item['law_id']}")
        path = resolve_ref(raw_root, item["raw_file_ref"])
        if not path.is_file():
            raise ValueError(f"Raw file missing: {item['raw_file_ref']}")
        if path in paths:
            raise ValueError(f"Duplicate raw file registration: {item['raw_file_ref']}")
        paths.add(path)
        data = path.read_bytes()
        sha = digest(data)
        if sha != item["expected_sha256"]:
            raise ValueError(f"Raw SHA-256 mismatch: {item['raw_file_ref']}")
        file_id = file_identity(registry["file_id_namespace"], item["law_id"], sha)
        byte_key = item["law_id"], sha
        part_key = item["law_id"], item["source_set_id"], item["part_order"]
        if file_id in ids or byte_key in byte_keys or part_key in part_keys:
            raise ValueError("Duplicate file ID, law/hash or source-set part order")
        ids.add(file_id)
        byte_keys.add(byte_key)
        part_keys.add(part_key)
        record = {"file_id": file_id, "law_id": item["law_id"],
                  "source_set_id": item["source_set_id"], "part_order": item["part_order"],
                  "file_role": item["file_role"],
                  "measured": {"filename": path.name, "raw_file_ref": item["raw_file_ref"],
                               "size_bytes": len(data), "sha256": sha, "mime_type": detect_source_mime(data)},
                  "evidence": dict.fromkeys(FILE_EVIDENCE), "status": "pending"}
        require_contract("pending_file", record)
        files.append(record)
    if laws != {f["law_id"] for f in files}:
        raise ValueError("Every declared document must have a registered raw file")
    for record, fields in [(d, DOCUMENT_EVIDENCE) for d in documents] + [(f, FILE_EVIDENCE) for f in files]:
        for field in fields:
            identity = {"law_id": record["law_id"], "file_id": record.get("file_id"), "field": field}
            issues.append({"issue_id": "qi_" + digest(canonical(identity).encode("utf-8")),
                           **identity, "rule_id": "DQ-01", "code": "PENDING_SOURCE_EVIDENCE",
                           "severity": "error", "status": "pending",
                           "detail": f"Evidence unavailable for {field}; registration is not verification."})
    return (sorted(documents, key=lambda r: r["source_id"]),
            sorted(files, key=lambda r: r["file_id"]), sorted(issues, key=lambda r: r["issue_id"]))


def pending_rows(documents, files, issues):
    return {
        "pending_document": [{"law_id": d["law_id"], "source_id": d["source_id"],
                              "record_json": canonical(d)} for d in documents],
        "pending_file": [{"file_id": f["file_id"], "law_id": f["law_id"],
                          "source_set_id": f["source_set_id"], "part_order": f["part_order"],
                          "sha256": f["measured"]["sha256"], "record_json": canonical(f)} for f in files],
        "pending_quality_issue": [{"issue_id": q["issue_id"], "law_id": q["law_id"],
                                   "file_id": q["file_id"], "record_json": canonical(q)} for q in issues],
    }


def schema_signature(db):
    return [tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master "
                                        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]


def expected_signature(sql):
    import sqlite3
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(sql)
        return schema_signature(db)


def write_rows(path, rows):
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(canonical(row) + "\n")


def read_rows(path):
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{path}:{number}: blank JSONL row")
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{number}: expected object")
        rows.append(item)
    return rows


def _inspect(run, raw_root, *, manifest=None):
    errors = []
    documents = read_rows(run / "documents.pending.jsonl")
    files = read_rows(run / "files.pending.jsonl")
    issues = read_rows(run / "quality_issues.jsonl")
    registry = load_json(run / "registration_input.json")
    for name, records in (("pending_document", documents), ("pending_file", files)):
        for record in records:
            require_contract(name, record)
    # Recompute from input declaration and real raw bytes; do not trust exported flags/IDs.
    expected = registration_records(registry, raw_root)
    for label, actual, desired in zip(("documents", "files", "issues"), (documents, files, issues), expected):
        if actual != desired:
            errors.append(f"REGISTRATION_MISMATCH: {label} differ from deterministic registration")
    for records, key in ((documents, "law_id"), (documents, "source_id"),
                         (files, "file_id"), (issues, "issue_id")):
        if len({r[key] for r in records}) != len(records):
            errors.append(f"DUPLICATE_ID: {key}")
    doc_laws = {d["law_id"] for d in documents}
    for record in files:
        if record["law_id"] not in doc_laws:
            errors.append("RELATIONSHIP: file law_id does not exist")
    for name in ("schema.sql", "pending_schema.sql"):
        if (run / name).read_bytes() != (SCHEMA_DIR / name).read_bytes():
            errors.append(f"SCHEMA_MISMATCH: {name} changed")
    official = (SCHEMA_DIR / "schema.sql").read_bytes()
    provenance = load_json(SCHEMA_DIR / "provenance.json")
    if digest(official) != provenance["member_sha256"]:
        errors.append("SCHEMA_MISMATCH: official SQL no longer matches design provenance")
    for name in SCHEMA_NAMES:
        ref = f"contracts/{name}.schema.json"
        if resolve_ref(run, ref).read_bytes() != (SCHEMA_DIR / f"{name}.schema.json").read_bytes():
            errors.append(f"CONTRACT_MISMATCH: {name}")
    official_counts = {}
    for name, schema_name in (("content.sqlite", "schema.sql"), ("pending.sqlite", "pending_schema.sql")):
        with closing(connect_sqlite(run / name, readonly=True)) as db:
            if schema_signature(db) != expected_signature((SCHEMA_DIR / schema_name).read_text(encoding="utf-8")):
                errors.append(f"SCHEMA_MISMATCH: database {name}")
            for row in db.execute("PRAGMA foreign_key_check"):
                errors.append(f"FOREIGN_KEY: {name}: {tuple(row)}")
            if [r[0] for r in db.execute("PRAGMA integrity_check")] != ["ok"]:
                errors.append(f"DATABASE_INTEGRITY: {name}")
            if name == "content.sqlite":
                for table in TABLES:  # Fixed design table names, never user-provided SQL.
                    official_counts[table] = db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                if any(official_counts.values()):
                    errors.append("UNSUPPORTED_PROMOTION: Stage 2 canonical database must remain empty")
            else:
                for table, rows in pending_rows(documents, files, issues).items():
                    actual = [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
                    if sorted(actual, key=canonical) != sorted(rows, key=canonical):
                        errors.append(f"SQLITE_EXPORT_MISMATCH: {table}")
    report = {"technical_valid": not errors, "errors": errors,
              "dataset_kind": registry["dataset_kind"], "pending_document_count": len(documents),
              "pending_file_count": len(files), "pending_quality_issue_count": len(issues),
              "official_counts": official_counts, "release_eligible": False,
              "release_blockers": BLOCKERS, "legal_verification": "not_performed"}
    if manifest is not None:
        checks = {"manifest_type": "source_registration", "contract_version": "source-registration.v1",
                  "snapshot_date": SNAPSHOT_DATE, "dataset_kind": registry["dataset_kind"],
                  "file_id_namespace": registry["file_id_namespace"], "document_count": len(documents),
                  "file_count": len(files), "extraction_count": 0, "quality_issue_count": len(issues),
                  "release_eligible": False, "release_blockers": BLOCKERS}
        if set(manifest) != set(checks) | {"built_at", "files"}:
            errors.append("MANIFEST_MISMATCH: missing or unsupported manifest fields")
        for key, value in checks.items():
            if manifest.get(key) != value or type(manifest.get(key)) is not type(value):
                errors.append(f"MANIFEST_MISMATCH: {key}")
        built = manifest.get("built_at", "")
        try:
            if not isinstance(built, str) or not built.endswith("Z"):
                raise ValueError()
            datetime.fromisoformat(built.replace("Z", "+00:00"))
        except ValueError:
            errors.append("MANIFEST_MISMATCH: invalid built_at (technical run timestamp)")
        entries = manifest.get("files", [])
        if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
            raise ValueError("Invalid manifest artifact list")
        refs = [entry.get("path") for entry in entries]
        if sorted(refs) != sorted(ARTIFACTS):
            errors.append("MANIFEST_MISMATCH: missing, extra or duplicate artifact paths")
        for entry in entries:
            path = resolve_ref(run, entry["path"])
            data = path.read_bytes()
            if entry.get("sha256") != digest(data) or type(entry.get("size_bytes")) is not int or entry["size_bytes"] != len(data):
                errors.append(f"ARTIFACT_HASH_SIZE: {entry['path']}")
        stored = load_json(run / "validation_report.json")
        if stored != report:
            errors.append("REPORT_MISMATCH: stored report differs from current validation")
    report["technical_valid"] = not errors
    return report


def inspect_bundle(manifest_path, raw_root=BASE_DIR, *, require_release_ready=False):
    """Read-only validation. A pending registration can pass technically, never for release."""
    try:
        manifest_path = Path(manifest_path).resolve()
        data = manifest_path.read_bytes()
        if (manifest_path.parent / "manifest.sha256").read_text(encoding="ascii").strip() != digest(data):
            raise ValueError("MANIFEST_CHECKSUM: sidecar SHA-256 mismatch")
        report = _inspect(manifest_path.parent, raw_root, manifest=load_json(manifest_path))
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        report = {"technical_valid": False, "errors": [str(exc)], "release_eligible": False,
                  "release_blockers": BLOCKERS, "legal_verification": "not_performed"}
    # Structural database corruption must also become a failing CLI result.
    if require_release_ready and not report["release_eligible"]:
        report = {**report, "release_check_passed": False}
    return report


def register(config_path, run_dir, raw_root=BASE_DIR):
    staging_path(run_dir)
    registry = load_json(config_path)
    documents, files, issues = registration_records(registry, raw_root)
    with staged_run(run_dir, "source_registration", config_path) as (run, run_report):
        for name in ("schema.sql", "pending_schema.sql"):
            with (run / name).open("xb") as output:
                output.write((SCHEMA_DIR / name).read_bytes())
        (run / "contracts").mkdir()
        for name in SCHEMA_NAMES:
            (run / "contracts" / f"{name}.schema.json").write_bytes((SCHEMA_DIR / f"{name}.schema.json").read_bytes())
        write_json(run / "registration_input.json", registry)
        for name, records in (("documents.pending.jsonl", documents), ("files.pending.jsonl", files),
                              ("quality_issues.jsonl", issues)):
            write_rows(run / name, records)
        for name, sql in (("content.sqlite", "schema.sql"), ("pending.sqlite", "pending_schema.sql")):
            with closing(connect_sqlite(run / name)) as db:
                db.executescript((run / sql).read_text(encoding="utf-8"))
                if name == "pending.sqlite":
                    with db:
                        for table, rows in pending_rows(documents, files, issues).items():
                            for row in rows:
                                columns = ",".join(row)
                                placeholders = ",".join("?" for _ in row)
                                db.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", list(row.values()))
        validation = _inspect(run, raw_root)
        if not validation["technical_valid"]:
            raise ValueError(canonical(validation))
        write_json(run / "validation_report.json", validation)
        manifest = {"manifest_type": "source_registration", "contract_version": "source-registration.v1",
                    "dataset_kind": registry["dataset_kind"], "snapshot_date": SNAPSHOT_DATE,
                    "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "file_id_namespace": registry["file_id_namespace"], "document_count": len(documents),
                    "file_count": len(files), "extraction_count": 0, "quality_issue_count": len(issues),
                    "release_eligible": False, "release_blockers": BLOCKERS,
                    "files": [{"path": name, "size_bytes": (run / name).stat().st_size,
                               "sha256": digest((run / name).read_bytes())} for name in sorted(ARTIFACTS)]}
        write_json(run / "manifest.json", manifest)
        with (run / "manifest.sha256").open("x", encoding="ascii", newline="\n") as output:
            output.write(digest((run / "manifest.json").read_bytes()) + "\n")
        result = inspect_bundle(run / "manifest.json", raw_root)
        if not result["technical_valid"]:
            raise ValueError(canonical(result))
        run_report.update(pending_file_count=len(files), release_eligible=False,
                          quality_issue_count=len(issues), technical_valid=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage 2 source registration; no extraction/model/index")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("register", help="Create new staging databases/manifest")
    build.add_argument("--config", type=Path, default=DEFAULT_REGISTRY)
    build.add_argument("--raw-root", type=Path, default=BASE_DIR,
                       help="Root for relative raw/inventory refs; defaults to repository root")
    build.add_argument("--run-dir", type=Path, required=True)
    check = commands.add_parser("validate", help="Validate manifest, DBs and raw bytes read-only")
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--raw-root", type=Path, default=BASE_DIR)
    check.add_argument("--require-release-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "register":
            result = register(args.config, args.run_dir, args.raw_root)
        else:
            result = inspect_bundle(args.manifest, args.raw_root,
                                    require_release_ready=args.require_release_ready)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["technical_valid"] and result.get("release_check_passed", True) else 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
