"""Synthetic Stage 5A tests; no model, live network or real reviewer submissions."""
from contextlib import closing, redirect_stdout, redirect_stderr
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from zipfile import ZipFile

from src import assessment_contracts as c
from src import assessment_evidence as evidence
from src import assessment_pipeline as pipeline
from src.config import BASE_DIR, STAGING_DIR
from src.extraction_pipeline import build_run as extract_run
from src.legal_parser import build_run as parse_run
from src.source_contracts import canonical, digest, connect_sqlite
from src.source_registry import load_json, read_rows, write_rows, register


def json_file(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf8")
    return path


def reseal(root):
    """Only synthetic files owned by these tests; model an attacker rehashing."""
    meta = load_json(root / "manifest.json")
    meta["files"] = evidence.inventory(root)
    json_file(root / "manifest.json", meta)
    (root / "manifest.sha256").write_text(digest((root / "manifest.json").read_bytes()) + "\n", encoding="ascii")


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.uid = "u_" + "b" * 64
        self.binding = {"input_manifest_sha256": "a" * 64, "parser_version": "synthetic.v1"}
        self.subjects = {self.uid: {"unit_sha256": "c" * 64}}
        self.proposal = {"proposal_id": "fixture-proposal", "scope_candidate": "included", "applicability_candidate": "not_yet_effective", "effective_from_candidate": "2026-01-01", "effective_to_candidate": None}
        self.basis = [{"finding_id": "fixture-requirement", "evidence_id": "fixture-project", "kind": "project_requirement"},
                      {"finding_id": "fixture-span", "evidence_id": "fixture-extraction", "kind": "source_span", "unit_id": self.uid},
                      {"finding_id": "fixture-law", "evidence_id": "fixture-pdf", "kind": "text_slice", "accessed_at": "2025-01-01T00:00:00Z"}]
        self.payload = {"unit_id": self.uid, "unit_sha256": "c" * 64, "binding": self.binding, "snapshot_date": c.SNAPSHOT,
            "dimension": "scope", "supersedes": None, "reviewer_ref": "SYNTHETIC-REVIEWER-NOT-A-REAL-PERSON", "reviewed_at": "2025-02-01T00:00:00Z", "decision_note": "Synthetic only",
            "record_origin": "external_review_submission", "evidence_ids": ["fixture-project", "fixture-extraction"], "finding_ids": ["fixture-requirement", "fixture-span"],
            "proposal_id": "fixture-proposal", "proposal_relation": "accept", "override_reason": "", "scope_status": "included"}

    def event(self, payload=None):
        value = copy.deepcopy(self.payload if payload is None else payload)
        return {**value, "decision_id": c.identity("dec_", value)}

    def check(self, events):
        return c.decision_errors(events, self.subjects, self.binding, {f["evidence_id"] for f in self.basis}, findings=self.basis, proposals={self.uid: self.proposal})

    def applicability(self, **changes):
        payload = {k: v for k, v in self.payload.items() if k != "scope_status"}
        payload.update(dimension="applicability", applicability_status="verified_at_snapshot", effective_from="2025-01-01", effective_to=None,
                       evidence_ids=["fixture-pdf", "fixture-extraction"], finding_ids=["fixture-law", "fixture-span"],
                       historical_basis="promulgation_and_changes_reviewed", historical_review_note="Synthetic historical basis", content_comparison_note="Synthetic comparison",
                       proposal_relation="override", override_reason="Synthetic evidence corrects the machine date and exception applicability")
        payload.update(changes)
        return payload

    def technical(self):
        payload = {k: v for k, v in self.payload.items() if k != "scope_status"}
        payload.update(dimension="technical", technical_review_status="accepted", review_scope_note="Synthetic own text, title, spans and required context reviewed",
                       evidence_ids=["fixture-extraction"], finding_ids=["fixture-span"])
        return payload

    def test_scope_complete_while_applicability_and_technical_pending(self):
        event = self.event()
        errors, latest = self.check([event])
        self.assertEqual(errors, [])
        unit = {"unit_id": self.uid, "law_id": "SYNTHETIC/5"}
        row = c.assessment(unit, {"group_id": "fixture"}, self.binding, [], self.proposal, {"scope": latest[self.uid, "scope"]})
        self.assertEqual(row["scope_status"], "included")
        self.assertEqual(row["applicability_status"], "pending_review")
        self.assertEqual(row["technical_review_status"], "pending")
        self.assertEqual(row["dimension_complete"], {"scope": True, "applicability": False, "technical": False})
        self.assertFalse(row["target_eligible"] or row["context_eligible"] or c.ddd_mapping(row)["ready_to_load"])

    def test_evidence_backed_scope_and_date_overrides_accepted(self):
        scope = self.event({**self.payload, "scope_status": "excluded", "proposal_relation": "override", "override_reason": "Synthetic scope basis"})
        app = self.event(self.applicability())
        self.assertEqual(self.check([scope, app])[0], [])
        self.assertEqual(c.date_errors("verified_at_snapshot", "2025-01-01", None, rule={"effective_from": "2026-01-01"}), [])

    def test_missing_evidence_binding_unit_hash_or_reason_rejected(self):
        for changes in ({"evidence_ids": []}, {"finding_ids": []}, {"unit_id": "unknown"}, {"unit_sha256": "d" * 64},
                        {"binding": {}}, {"snapshot_date": "2026-01-01"}, {"reviewer_ref": ""}, {"record_origin": "machine"},
                        {"reviewed_at": "2999-01-01T00:00:00Z"}, {"reviewed_at": "2025-02-01"}):
            with self.subTest(changes=changes): self.assertTrue(self.check([self.event({**self.payload, **changes})])[0])
        for changes in ({"override_reason": ""}, {"proposal_relation": "accept"}):
            self.assertTrue(self.check([self.event(self.applicability(**changes))])[0])

    def test_dimension_specific_evidence_and_fields(self):
        scope = {**self.payload, "finding_ids": ["fixture-span"], "evidence_ids": ["fixture-extraction"]}
        self.assertTrue(self.check([self.event(scope)])[0])
        self.assertTrue(self.check([self.event({**self.payload, "applicability_status": "verified_at_snapshot"})])[0])
        self.assertEqual(self.check([self.event(self.technical())])[0], [])

    def test_history_chains_by_unit_and_dimension(self):
        scope = self.event(); app = self.event(self.applicability()); tech = self.event(self.technical())
        self.assertEqual(self.check([scope, app, tech])[0], [])
        replacement = self.event({**self.payload, "supersedes": scope["decision_id"], "reviewed_at": "2025-02-02T00:00:00Z"})
        self.assertEqual(self.check([scope, app, replacement])[0], [])
        wrong = self.event({**self.payload, "supersedes": app["decision_id"]})
        self.assertTrue(self.check([scope, app, wrong])[0])
        fork = self.event({**self.payload, "decision_note": "Unchained fixture fork"})
        self.assertTrue(self.check([scope, fork])[0])

    def test_all_dimensions_complete_still_no_serving_or_fake_corpus(self):
        events = [self.event(), self.event(self.applicability()), self.event(self.technical())]
        errors, latest = self.check(events); self.assertEqual(errors, [])
        decisions = {d: latest[self.uid, d] for d in c.DIMENSIONS}
        row = c.assessment({"unit_id": self.uid, "law_id": "SYNTHETIC/5"}, {"group_id": "fixture"}, self.binding, [], self.proposal, decisions)
        self.assertTrue(all(row["dimension_complete"].values()))
        self.assertEqual(row["aggregate_status"], "pending")
        self.assertFalse(row["target_eligible"] or row["context_eligible"] or row["release_eligible"])
        mapping = c.ddd_mapping(row, decisions)
        self.assertIsNone(mapping["unit_assessment"]["corpus_version"])
        self.assertEqual(len(mapping["dimension_decision_refs"]), 3)

    def test_historical_proof_and_date_constraints_remain_required(self):
        for changes in ({"historical_basis": "current_website_only"}, {"content_comparison_note": ""}, {"effective_from": "2026-01-01"}, {"effective_to": "2025-01-01"}):
            self.assertTrue(self.check([self.event(self.applicability(**changes))])[0])
        self.assertEqual(c.date_errors("expired_at_snapshot", "2024-01-01", "2025-01-01"), [])
        self.assertTrue(c.date_errors("not_yet_effective", "2025-01-01", None))
        self.assertTrue(c.date_errors("pending_review", "2025-02-30", None))
        self.assertTrue(c.date_errors("verified_at_snapshot", None, None))

    def test_applicability_or_technical_can_complete_first(self):
        for dimension, payload in [("applicability", self.applicability()), ("technical", self.technical())]:
            event = self.event(payload)
            errors, latest = self.check([event])
            self.assertEqual(errors, [])
            row = c.assessment({"unit_id": self.uid, "law_id": "SYNTHETIC/5"}, {"group_id": "fixture"},
                               self.binding, [], self.proposal, {dimension: latest[self.uid, dimension]})
            self.assertIsNone(row["scope_status"])
            self.assertTrue(row["dimension_complete"][dimension])
            self.assertFalse(row["release_eligible"])


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        STAGING_DIR.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="test-stage5a-", dir=STAGING_DIR)
        cls.root = Path(cls.temp.name)
        raw = cls.root / "raw.docx"
        with ZipFile(raw, "w") as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + ''.join('<w:p><w:r><w:t>' + t + '</w:t></w:r></w:p>' for t in ["LUẬT GIẢ LẬP", "Điều 1. Ví dụ", "Dẫn giả lập", "1. Nội dung chỉ để thử.", "a) Điểm giả lập."]) + '</w:body></w:document>')
        (cls.root / "inventory.md").write_text("Synthetic fixture only", encoding="utf8")
        registry = {"contract_version": "source-registration.v1", "dataset_kind": "synthetic_fixture", "snapshot_date": c.SNAPSHOT,
            "file_id_namespace": "4682a18d-a842-48aa-8549-ab2b74d1e610", "documents": [{"source_id": "FIXTURE-5", "law_id": "SYNTHETIC/5", "declared": {"law_title": "Synthetic test only", "document_type": "law", "scope_note": "Not real law", "source_url_candidate": "https://example.invalid/fixture", "issued_date_candidate": "2024-01-01", "inventory_ref": "inventory.md"}}],
            "files": [{"law_id": "SYNTHETIC/5", "source_set_id": "FIXTURE-5", "part_order": 1, "file_role": "main", "raw_file_ref": "raw.docx", "expected_sha256": digest(raw.read_bytes())}]}
        register(json_file(cls.root / "registry.json", registry), cls.root / "s2", cls.root)
        extract_run(cls.root / "s2/manifest.json", cls.root / "s3", cls.root)
        parse_run(cls.root / "s3/manifest.json", cls.root / "s4", cls.root)
        pack = cls.root / "pack"
        pack.mkdir()
        write_rows(pack / "issues.jsonl", [])
        evidence.seal(pack, {"manifest_type": "stage4_review_pack", "input_manifest_sha256": digest((cls.root / "s4/manifest.json").read_bytes())})
        # Simulate HTTP response only for SYNTHETIC/5. Never call a live endpoint.
        response = MagicMock()
        response.__enter__.return_value = response
        response.url = "https://vanban.chinhphu.vn/?fixture=stage5-test"
        response.status = 200
        response.headers = {"Content-Type": "text/html"}
        response.read.return_value = b"<html>Synthetic fixture, not official law evidence</html>"
        req = [{"law_id": "SYNTHETIC/5", "kind": "metadata_html", "url": response.url}]
        with patch.object(evidence, "build_opener") as opener:
            opener.return_value.open.return_value = response
            evidence.capture(json_file(cls.root / "requests.json", req), cls.root / "evidence")
        units = read_rows(cls.root / "s4/legal_units.pending.jsonl")
        cls.uid = next(x["unit_id"] for x in units if x["unit_type"] == "clause")
        cfg = {"policy": c.VERSION, "snapshot_date": c.SNAPSHOT, "dataset_kind": "synthetic_fixture", "max_units": 2,
               "groups": [{"group_id": "fixture", "unit_ids": [cls.uid], "scope_candidate": "included", "scope_reason": "Synthetic only"}]}
        cls.config = json_file(cls.root / "config.json", cfg)
        cls.findings = json_file(cls.root / "findings.json", [])
        cls.pilot_root = cls.root / "pilot"
        result = cls.build(cls.pilot_root)
        if not result["technical_valid"]:
            raise AssertionError(result)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def build(cls, destination, **changes):
        return pipeline.build_run(cls.root / "s4/manifest.json", cls.root / "pack/manifest.json", cls.root / "evidence/manifest.json", destination,
                                  changes.get("config", cls.config), cls.findings, changes.get("submissions"), raw_root=cls.root)

    def cloned(self):
        import shutil
        parent = tempfile.TemporaryDirectory(prefix="mutation-", dir=self.root)
        self.addCleanup(parent.cleanup)
        path = Path(parent.name) / "pilot"
        shutil.copytree(self.pilot_root, path)
        return path

    def assert_bad(self, path):
        result = pipeline.validate_run(path / "manifest.json", self.root)
        self.assertFalse(result["technical_valid"], result)
        self.assertFalse(result["release_eligible"])

    def test_end_to_end_pending_and_no_fake_official_tables(self):
        result = pipeline.validate_run(self.pilot_root / "manifest.json", self.root)
        self.assertTrue(result["technical_valid"], result)
        row = read_rows(self.pilot_root / "assessments.pending.jsonl")[0]
        self.assertIsNone(row["decision_ids"]["scope"])
        self.assertEqual(read_rows(self.pilot_root / "target_candidates.jsonl"), [])
        self.assertEqual(read_rows(self.pilot_root / "context_candidates.jsonl"), [])
        with closing(connect_sqlite(self.pilot_root / "assessment.pending.sqlite", readonly=True)) as db:
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertFalse(db.execute("SELECT name FROM sqlite_master WHERE name IN ('corpus','legal_unit','unit_assessment')").fetchall())
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_pending_cannot_be_smuggled_into_candidates_even_with_rehash(self):
        for name in ("target_candidates.jsonl", "context_candidates.jsonl"):
            run = self.cloned()
            (run / name).write_text(canonical({"unit_id": self.uid}) + "\n", encoding="utf8")
            reseal(run)
            self.assert_bad(run)

    def test_verified_or_unknown_unit_and_wrong_hash_cannot_be_smuggled(self):
        for changes in ({"applicability_status": "verified_at_snapshot"}, {"unit_id": "u_" + "f" * 64}, {"unit_sha256": "0" * 64}):
            run = self.cloned()
            rows = read_rows(run / "assessments.pending.jsonl")
            rows[0].update(changes)
            (run / "assessments.pending.jsonl").write_text("".join(canonical(r) + "\n" for r in rows), encoding="utf8")
            reseal(run)
            self.assert_bad(run)

    def test_missing_or_changed_evidence_detected(self):
        run = self.cloned()
        (run / "evidence_snapshot/01/snapshot.html").write_text("Changed synthetic bytes", encoding="utf8")
        self.assert_bad(run)
        run = self.cloned()
        (run / "evidence_snapshot/01/snapshot.html").unlink()  # Test-owned fixture only.
        self.assert_bad(run)

    def test_wrong_parser_binding_rejected_after_rehash(self):
        run = self.cloned()
        row = load_json(run / "binding.json")
        row["parser_version"] = "synthetic-wrong-version"
        json_file(run / "binding.json", row)
        reseal(run)
        self.assert_bad(run)

    def test_sqlite_fk_or_schema_tampering_detected_after_rehash(self):
        run = self.cloned()
        with closing(sqlite3.connect(run / "assessment.pending.sqlite")) as db:
            with db:
                db.execute("UPDATE pending_assessment SET proposal_id='unknown-fixture'")
        reseal(run)
        self.assert_bad(run)

    def test_technical_report_cannot_claim_legal_verification(self):
        run = self.cloned()
        report = load_json(run / "validation_report.json")
        report["legal_verification"] = "verified"
        json_file(run / "validation_report.json", report)
        reseal(run)
        self.assert_bad(run)

    def test_same_input_has_same_ids_and_exports(self):
        run = self.root / "repeat"
        self.assertTrue(self.build(run)["technical_valid"])
        for name in pipeline.EXPORTS.values():
            self.assertEqual((run / name).read_bytes(), (self.pilot_root / name).read_bytes(), name)

    def test_scope_only_submission_replays_into_sqlite_without_other_dimensions(self):
        config = load_json(self.config)
        config["scope_basis"] = [{"path": (self.root / "inventory.md").relative_to(BASE_DIR).as_posix(),
                                  "sha256": digest((self.root / "inventory.md").read_bytes()), "locator": "Synthetic scope fixture only"}]
        config_path = json_file(self.root / "scope-config.json", config)
        reference = self.root / "scope-reference"
        self.assertTrue(self.build(reference, config=config_path)["technical_valid"])
        basis = read_rows(reference / "review_basis.jsonl")
        requirement = next(f for f in basis if f["kind"] == "project_requirement")
        span = next(f for f in basis if f["kind"] == "source_span" and f["unit_id"] == self.uid)
        proposal = read_rows(reference / "machine_proposals.jsonl")[0]
        payload = {"unit_id": self.uid, "unit_sha256": proposal["unit_sha256"], "dimension": "scope",
                   "binding": load_json(reference / "binding.json"), "snapshot_date": c.SNAPSHOT, "supersedes": None,
                   "reviewer_ref": "SYNTHETIC-REVIEWER", "reviewed_at": evidence.now(), "decision_note": "Synthetic exclusion only",
                   "record_origin": "external_review_submission", "evidence_ids": [requirement["evidence_id"], span["evidence_id"]],
                   "finding_ids": [requirement["finding_id"], span["finding_id"]], "proposal_id": proposal["proposal_id"],
                   "proposal_relation": "override", "override_reason": "Synthetic requirement excludes this fixture", "scope_status": "excluded"}
        event = {**payload, "decision_id": c.identity("dec_", payload)}
        submission = json_file(self.root / "scope-submission.json", {"events": [event]})
        target = self.root / "scope-reviewed"
        self.assertTrue(self.build(target, config=config_path, submissions=submission)["technical_valid"])
        row = read_rows(target / "assessments.pending.jsonl")[0]
        self.assertEqual(row["scope_status"], "excluded")
        self.assertEqual(row["applicability_status"], "pending_review")
        self.assertEqual(row["technical_review_status"], "pending")
        self.assertEqual(row["decision_ids"]["scope"], event["decision_id"])
        self.assertEqual(load_json(target / "validation_report.json")["proposal_override_count"], 1)
        self.assertEqual(read_rows(target / "review_decision_history.jsonl"), [event])
        self.assertEqual(read_rows(reference / "review_decision_history.jsonl"), [])
        self.assertEqual((target / "external_review_submission.input.json").read_bytes(), submission.read_bytes())
        with closing(connect_sqlite(target / "assessment.pending.sqlite", readonly=True)) as db:
            self.assertEqual(db.execute("SELECT dimension FROM pending_decision_event").fetchone()[0], "scope")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_unknown_duplicate_or_unbounded_selection_rejected_before_output(self):
        config = load_json(self.config)
        for ids in ([self.uid, self.uid], ["u_unknown"], [self.uid]):
            candidate = copy.deepcopy(config)
            candidate["groups"][0]["unit_ids"] = ids
            if ids == [self.uid]:
                candidate["max_units"] = 4000
            with self.assertRaises(ValueError):
                pipeline.select_subjects(candidate, {self.uid: {"unit_id": self.uid}})

    def test_missing_input_cli_fails_without_creating_output(self):
        target = self.root / "must-not-exist"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = pipeline.main(["pilot", "--tree-manifest", str(self.root / "missing.json"),
                "--review-manifest", str(self.root / "pack/manifest.json"), "--evidence-manifest", str(self.root / "evidence/manifest.json"), "--run-dir", str(target)])
        self.assertNotEqual(code, 0)
        self.assertFalse(target.exists())

    def test_official_host_allowlist_and_capture_cannot_mark_verified(self):
        for url in ("http://vanban.chinhphu.vn", "https://vanban.chinhphu.vn.evil.invalid/", "https://127.0.0.1", "https://user@vanban.chinhphu.vn"):
            with self.assertRaises(ValueError):
                evidence.official_url(url)
        self.assertTrue(evidence.validate_evidence(self.root / "evidence/manifest.json"))

    def test_capture_status_and_evidence_identity_rejected_even_after_rehash(self):
        run = self.cloned()
        rows = read_rows(run / "evidence_snapshot/evidence.jsonl")
        rows[0]["historical_status"] = "verified"
        (run / "evidence_snapshot/evidence.jsonl").write_text(canonical(rows[0]) + "\n", encoding="utf8")
        reseal(run / "evidence_snapshot")
        reseal(run)
        self.assert_bad(run)

    def test_effective_date_requires_exact_captured_quote_and_known_target(self):
        root = self.root / "finding-fixture"
        root.mkdir(exist_ok=True)
        (root / "page.txt").write_text("Fixture có hiệu lực từ ngày 01 tháng 01 năm 2025.", encoding="utf8")
        ev = [{"evidence_id": "fixture-evidence", "law_id": "SYNTHETIC/5", "url": "https://vanban.chinhphu.vn/fixture.pdf",
               "sha256": "a" * 64, "accessed_at": "2025-01-01T00:00:00Z",
               "pages": [{"page": 1, "text_ref": "page.txt", "text_sha256": digest((root / "page.txt").read_bytes()), "text_status": "text_available"}]}]
        req = {"key": "fixture", "law_id": "SYNTHETIC/5", "pdf_suffix": "fixture.pdf", "page": 1, "legal_locator": "Fixture",
               "quote": (root / "page.txt").read_text(encoding="utf8"), "note": "Not real law",
               "date_rule": {"effective_from": "2025-01-01", "effective_to": None, "priority": 1, "unit_ids": [self.uid]}}
        result = pipeline.compute_findings([req], ev, root, [{"unit_id": self.uid}])
        self.assertEqual(result[1][0]["effective_from"], "2025-01-01")
        for changes in ({"quote": "Missing text"}, {"page": 2}, {"date_rule": {**req["date_rule"], "effective_from": "2026-01-01"}},
                        {"date_rule": {**req["date_rule"], "unit_ids": ["unknown-unit"]}}):
            with self.assertRaises(ValueError):
                pipeline.compute_findings([{**req, **changes}], ev, root, [{"unit_id": self.uid}])

    def test_impact_kinds_and_no_blanket_parent_child_inheritance(self):
        root = self.root / "impact-fixture"
        root.mkdir(exist_ok=True)
        (root / "extraction_snapshot").mkdir(exist_ok=True)
        text = "a)x\nd)y\nxdup\nTABLE"
        (root / "extraction_snapshot/text.txt").write_text(text, encoding="utf8")
        write_rows(root / "extraction_snapshot/extractions.pending.jsonl", [{"law_id": "SYNTHETIC/5", "extraction": {"extraction_id": "fixture-eid", "text_ref": "text.txt"}}])
        write_rows(root / "coverage.jsonl", [])
        pack = root / "pack"
        pack.mkdir()
        def issue(index, a, b, parent, code):
            return {"issue_id": f"fixture-{index}", "extraction_id": "fixture-eid", "law_id": "SYNTHETIC/5", "char_start": a, "char_end": b,
                    "locator": {"xpath": f"fixture/p[{index}]"}, "source_quote": text[a:b], "parent_unit_id": parent,
                    "code": code, "reason_or_quarantine": "Synthetic review region", "impact": "Synthetic impact only"}
        write_rows(pack / "issues.jsonl", [issue(1, 4, 7, "P", "POINT_SEQUENCE_GAP"), issue(2, 8, 12, "P", "AMBIGUOUS_POINT"),
                                         issue(3, 13, 18, "T", "TABLE_STRUCTURE_NOT_PARSED"), issue(4, 0, 0, None, "UNDECODED_SOURCE_CONTENT")])
        subjects = [{"unit_id": uid, "unit": {"unit_id": uid, "parent_unit_id": parent, "law_id": "SYNTHETIC/5", "unit_type": kind}}
                    for uid, parent, kind in [("P", None, "clause"), ("C", "P", "point"), ("W", "P", "point"), ("T", None, "clause"), ("UNRELATED", None, "clause")]]
        spans = [{"unit_id": "C", "extraction_id": "fixture-eid", "char_start": 0, "char_end": 3},
                 {"unit_id": "W", "extraction_id": "fixture-eid", "char_start": 4, "char_end": 7}]
        links = [{"unit_id": "C", "context_unit_id": "P", "region_xpaths": ["fixture/p[2]"],
                  "own_content_impact": "not_observed", "reason": "Synthetic explicit context review; own text is retained"}]
        regions, impacts = pipeline.compute_impacts(root, pack, subjects, spans, links)
        self.assertEqual(len(regions), 4)
        self.assertIn("unit_present_with_structure_warning", [r["impact_kind"] for r in impacts if r["unit_id"] == "W"])
        self.assertIn("parent_missing_some_children", [r["impact_kind"] for r in impacts if r["unit_id"] == "P"])
        self.assertIn("context_dependency_needs_review", [r["impact_kind"] for r in impacts if r["unit_id"] == "C"])
        self.assertIn("unparsed_table_content_dependency", [r["impact_kind"] for r in impacts if r["unit_id"] == "T"])
        self.assertFalse(any(r["unit_id"] == "UNRELATED" for r in impacts))
        self.assertFalse(any(r["unit_id"] == "W" and r["impact_kind"] == "context_dependency_needs_review" for r in impacts))
        _, no_links = pipeline.compute_impacts(root, pack, subjects, spans)
        self.assertFalse(any(r["unit_id"] == "C" for r in no_links))

    def test_imports_do_not_write_connect_or_initialize_dependencies(self):
        script = '''
import sys,importlib
def audit(event,args):
    if event in {'socket.connect','sqlite3.connect','os.remove','os.mkdir'}: raise RuntimeError(event)
    if event=='open' and isinstance(args[1],str) and any(x in args[1] for x in 'wax+'): raise RuntimeError(event)
sys.addaudithook(audit)
for name in ['src.assessment_evidence','src.assessment_contracts','src.assessment_pipeline']: importlib.import_module(name)
assert not any(x in sys.modules for x in ['torch','transformers','sentence_transformers','pdfplumber','qdrant_client'])
'''
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=BASE_DIR, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
