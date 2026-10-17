"""Synthetic source-contract tests, separate from the real-law registration config."""
from contextlib import closing, redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from src.config import BASE_DIR, STAGING_DIR
from src.source_contracts import (SCHEMA_DIR, connect_sqlite, digest, validate_contract,
                                 validate_extraction)
from src.source_registry import (DEFAULT_REGISTRY, inspect_bundle, load_json, main,
                                 read_rows, register, registration_records, write_rows)


class Stage2Tests(unittest.TestCase):
    def setUp(self):
        STAGING_DIR.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage2-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "raw").mkdir()
        raw = self.root / "raw/example.docx"
        with ZipFile(raw, "w") as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            z.writestr("word/document.xml", '<document>synthetic package, not a legal source</document>')
        (self.root / "inventory.md").write_text("Synthetic fixture only", encoding="utf-8")
        self.registry = {"contract_version": "source-registration.v1", "dataset_kind": "synthetic_fixture",
                         "snapshot_date": "2025-01-01",
                         "file_id_namespace": "f4322665-fc6d-47f4-a062-48b8a01d9b11",
                         "documents": [{"source_id": "FIXTURE-001", "law_id": "SYNTHETIC/1",
                                        "declared": {"law_title": "Synthetic fixture", "document_type": "law",
                                                     "scope_note": "Tests only", "source_url_candidate": "https://example.invalid/source",
                                                     "issued_date_candidate": "2024-01-01", "inventory_ref": "inventory.md"}}],
                         "files": [{"law_id": "SYNTHETIC/1", "source_set_id": "FIXTURE-local-01",
                                    "part_order": 1, "file_role": "main", "raw_file_ref": "raw/example.docx",
                                    "expected_sha256": digest(raw.read_bytes())}]}

    def build(self, name="run", registry=None):
        path = self.root / f"{name}-input.json"
        path.write_text(json.dumps(registry or self.registry), encoding="utf-8")
        out = self.root / name
        report = register(path, out, self.root)
        self.assertTrue(report["technical_valid"], report)
        return out

    def reseal(self, run):
        """Model an attacker updating checksums: semantic checks must still fail."""
        path = run / "manifest.json"
        manifest = load_json(path)
        for entry in manifest["files"]:
            data = (run / entry["path"]).read_bytes()
            entry.update(sha256=digest(data), size_bytes=len(data))
        path.write_text(json.dumps(manifest), encoding="utf-8")
        (run / "manifest.sha256").write_text(digest(path.read_bytes()) + "\n", encoding="ascii")

    def replace_rows(self, path, rows):
        # Only modify a synthetic test artifact created by this test.
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def assert_bad(self, run, expected=None):
        result = inspect_bundle(run / "manifest.json", self.root)
        self.assertFalse(result["technical_valid"], result)
        self.assertFalse(result["release_eligible"])
        if expected:
            self.assertIn(expected, " ".join(result["errors"]))

    def test_official_schema_exactly_matches_design_zip(self):
        path = BASE_DIR / "docs/design/data_model_v1/Data_Model_Schema_Examples_v1.0.zip"
        with ZipFile(path) as z:
            self.assertEqual((SCHEMA_DIR / "schema.sql").read_bytes(), z.read("schema.sql"))
        provenance = load_json(SCHEMA_DIR / "provenance.json")
        self.assertEqual(provenance["package_sha256"], digest(path.read_bytes()))

    def test_pending_has_no_fabricated_evidence_and_canonical_is_empty(self):
        run = self.build()
        result = inspect_bundle(run / "manifest.json", self.root)
        self.assertTrue(result["technical_valid"])
        self.assertFalse(result["release_eligible"])
        self.assertEqual(result["pending_quality_issue_count"], 11)
        self.assertTrue(all(count == 0 for count in result["official_counts"].values()))
        for name in ("documents.pending.jsonl", "files.pending.jsonl"):
            for record in read_rows(run / name):
                self.assertEqual(record["status"], "pending")
                self.assertTrue(all(v is None for v in record["evidence"].values()))
        self.assertEqual(load_json(run / "manifest.json")["extraction_count"], 0)

    def test_stable_identity_and_no_filename_identity(self):
        first, second = self.build("first"), self.build("second")
        self.assertEqual((first / "files.pending.jsonl").read_bytes(), (second / "files.pending.jsonl").read_bytes())
        modified = copy.deepcopy(self.registry)
        (self.root / "raw/renamed.docx").write_bytes((self.root / "raw/example.docx").read_bytes())
        modified["files"][0]["raw_file_ref"] = "raw/renamed.docx"
        third = self.build("renamed", modified)
        a, b = read_rows(first / "files.pending.jsonl"), read_rows(third / "files.pending.jsonl")
        self.assertEqual(a[0]["file_id"], b[0]["file_id"])
        self.assertEqual(a[0]["source_set_id"], b[0]["source_set_id"])

    def test_input_missing_and_hash_wrong_never_create_run(self):
        for field, value in (("raw_file_ref", "raw/missing.docx"), ("expected_sha256", "0" * 64)):
            registry = copy.deepcopy(self.registry)
            registry["files"][0][field] = value
            with self.assertRaises(ValueError):
                self.build("bad", registry)
            self.assertFalse((self.root / "bad").exists())

    def test_duplicate_documents_files_parts_and_wrong_law_rejected(self):
        for mutate in (lambda r: r["documents"].append(copy.deepcopy(r["documents"][0])),
                       lambda r: r["files"].append(copy.deepcopy(r["files"][0])),
                       lambda r: r["files"][0].update(law_id="MISSING"),
                       lambda r: r["files"][0].update(part_order=True),
                       lambda r: r["files"][0].update(part_order=1.0)):
            registry = copy.deepcopy(self.registry)
            mutate(registry)
            with self.assertRaises(ValueError):
                registration_records(registry, self.root)

    def test_invalid_mime_and_path_escape_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["files"][0]["raw_file_ref"] = "../outside.docx"
        with self.assertRaises(ValueError):
            registration_records(registry, self.root)
        raw = self.root / "raw/example.docx"
        raw.write_bytes(b"not a docx despite its extension")
        registry = copy.deepcopy(self.registry)
        registry["files"][0]["expected_sha256"] = digest(raw.read_bytes())
        with self.assertRaises(ValueError):
            registration_records(registry, self.root)

    def test_readonly_validator_does_not_create_missing_database(self):
        missing = self.root / "missing.sqlite"
        with self.assertRaises(sqlite3.Error):
            connect_sqlite(missing, readonly=True)
        self.assertFalse(missing.exists())

    def test_foreign_keys_and_not_null_are_enforced(self):
        run = self.build()
        with closing(connect_sqlite(run / "content.sqlite")) as db:
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO legal_document VALUES ('FIX','FIX','Fixture','law',NULL,NULL,NULL,'fixture')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO extraction VALUES ('fixture','missing-file','doc_text','fixture','fixture.txt',?,1,'pending','2024-01-01T00:00:00Z')", ("0" * 64,))
            db.rollback()
        with closing(connect_sqlite(run / "pending.sqlite")) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE pending_file SET law_id='missing-law'")
            db.rollback()

    def test_validator_detects_raw_loss_and_raw_hash_change(self):
        run = self.build()
        raw = self.root / "raw/example.docx"
        raw.write_bytes(raw.read_bytes() + b"tampered")
        self.assert_bad(run, "SHA-256 mismatch")
        raw.unlink()
        self.assert_bad(run, "Raw file missing")

    def test_manifest_and_artifact_checksums_detect_tampering(self):
        run = self.build()
        (run / "manifest.json").write_bytes((run / "manifest.json").read_bytes() + b" ")
        self.assert_bad(run, "MANIFEST_CHECKSUM")
        self.reseal(run)
        (run / "validation_report.json").write_text("{}", encoding="utf-8")
        self.assert_bad(run, "ARTIFACT_HASH_SIZE")

    def test_duplicate_ids_and_wrong_relationship_fail_even_after_resealing(self):
        for name, change, expected in (
            ("duplicate", lambda rows: rows.append(copy.deepcopy(rows[0])), "DUPLICATE_ID"),
            ("relationship", lambda rows: rows[0].update(law_id="missing-law"), "RELATIONSHIP"),
            ("claimed-verified", lambda rows: rows[0].update(status="verified"), "pending"),
            ("fabricated-time", lambda rows: rows[0]["evidence"].update(retrieved_at="2026-10-16T00:00:00Z"), "null")):
            run = self.build(name)
            path = run / "files.pending.jsonl"
            rows = read_rows(path)
            change(rows)
            self.replace_rows(path, rows)
            self.reseal(run)
            self.assert_bad(run, expected)

    def test_database_foreign_key_corruption_and_schema_relaxation_detected(self):
        run = self.build("foreign")
        with closing(sqlite3.connect(run / "pending.sqlite")) as db:
            db.execute("PRAGMA foreign_keys=OFF")
            db.execute("UPDATE pending_file SET law_id='missing-law'")
            db.commit()
        self.reseal(run)
        self.assert_bad(run, "FOREIGN_KEY")
        run = self.build("schema")
        with closing(sqlite3.connect(run / "content.sqlite")) as db:
            db.execute("CREATE TABLE unexpected_table (id TEXT)")
            db.commit()
        self.reseal(run)
        self.assert_bad(run, "SCHEMA_MISMATCH")

    def test_official_contract_rejects_missing_evidence(self):
        document = {"law_id": "FIX", "source_id": "FIX", "law_title": "Fixture", "document_type": "law",
                    "issued_date": None, "document_effective_from": None, "source_url": None, "scope_note": "Fixture"}
        errors = validate_contract("legal_document", document)
        self.assertTrue(any("issued_date" in e for e in errors))
        self.assertTrue(any("source_url" in e for e in errors))
        file = {"file_id": "FIX", "law_id": "FIX", "source_set_id": "FIX", "part_order": 1, "file_role": "main",
                "filename": "fixture.docx", "raw_file_ref": "raw/fixture.docx", "mime_type": "fixture",
                "size_bytes": 1, "sha256": "0" * 64, "download_url": None, "retrieved_at": None}
        errors = validate_contract("source_file", file)
        self.assertTrue(any("download_url" in e for e in errors))
        self.assertTrue(any("retrieved_at" in e for e in errors))
        document.update(issued_date="2024-02-30", source_url="file:///local")
        self.assertTrue(validate_contract("legal_document", document))

    def test_existing_extraction_contract_without_running_extractor(self):
        text = "Ví dụ\n"  # Synthetic Unicode test, not a legal source.
        (self.root / "synthetic.txt").write_text(text, encoding="utf-8", newline="\n")
        record = {"extraction_id": "SYNTHETIC", "file_id": "SYNTHETIC-FILE", "method": "doc_text",
                  "tool_version": "synthetic-fixture.v1", "text_ref": "synthetic.txt", "text_sha256": digest(text.encode()),
                  "char_count": len(text), "review_status": "pending", "created_at": "2024-01-01T00:00:00Z"}
        files = [{"file_id": "SYNTHETIC-FILE"}]
        self.assertEqual(validate_extraction(record, files, self.root), [])
        self.assertEqual(record["review_status"], "pending")
        self.assertTrue(validate_extraction(record, [], self.root))
        for field, value in (("char_count", len(text.encode())), ("char_count", float(len(text))),
                             ("created_at", "2024-01-01"), ("text_sha256", "0" * 64), ("text_ref", "../escape.txt")):
            changed = dict(record, **{field: value})
            self.assertTrue(validate_extraction(changed, files, self.root), changed)
        (self.root / "synthetic.txt").write_bytes(b"\xef\xbb\xbf" + text.encode())
        self.assertTrue(validate_extraction(record, files, self.root))

    def test_pending_release_gate_and_cli_exit_codes(self):
        run = self.build()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["validate", "--manifest", str(run / "manifest.json"), "--raw-root", str(self.root)]), 0)
            self.assertEqual(main(["validate", "--manifest", str(run / "manifest.json"), "--raw-root", str(self.root), "--require-release-ready"]), 1)
            self.assertEqual(main(["register", "--config", str(self.root / "missing.json"), "--run-dir", str(self.root / "new")]), 1)
        manifest = load_json(run / "manifest.json")
        manifest["release_eligible"] = True
        (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.reseal(run)
        self.assert_bad(run, "release_eligible")

    def test_unchanged_real_raw_registration_has_four_pending_files(self):
        registry = load_json(DEFAULT_REGISTRY)
        documents, files, issues = registration_records(registry, BASE_DIR)
        self.assertEqual((len(documents), len(files), len(issues)), (4, 4, 44))
        self.assertEqual({d["source_id"] for d in documents}, {"SRC-001", "SRC-002", "SRC-003", "SRC-004"})

    def test_register_does_not_import_models_or_index_engines(self):
        import builtins
        from unittest.mock import patch
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "sentence_transformers", "rank_bm25", "qdrant_client"}:
                raise AssertionError(f"Forbidden engine during Stage 2 registration: {name}")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            self.build()

    def test_import_is_quiet_and_cli_help_does_not_load_model(self):
        script = '''
import importlib.abc,sys
class BlockModel(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','transformers','sentence_transformers','qdrant_client','rank_bm25'}:
   raise AssertionError(fullname)
sys.meta_path.insert(0,BlockModel())
def audit(event,args):
 if event=='open' and isinstance(args[1],str) and any(c in args[1] for c in 'wax+'):
  raise AssertionError('write on import')
 if event in {'socket.connect','os.mkdir','os.remove','os.rename'}:raise AssertionError(event)
sys.addaudithook(audit)
import src.source_contracts,src.source_registry
'''
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=BASE_DIR, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        for args, code in ((["--help"], 0), (["register"], 2), (["validate"], 2)):
            result = subprocess.run([sys.executable, "-B", "-m", "src.source_registry", *args], cwd=BASE_DIR, capture_output=True)
            self.assertEqual(result.returncode, code)


if __name__ == "__main__":
    unittest.main()
