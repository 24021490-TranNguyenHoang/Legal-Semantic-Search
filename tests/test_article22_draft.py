"""Synthetic adapter fixtures only: approvals here do not concern real law/users."""
import copy
from contextlib import closing, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from src.article22_draft import (write_pack, read_pack, compile_review, admit, validate_draft,
                                 main, code_binding, check_context)
from src.assessment_evidence import inventory
from src.config import BASE_DIR, STAGING_DIR
from src.ingestion.legal_tree import unit_id, span_id
from src.source_contracts import canonical, digest, connect_sqlite
from src.source_registry import load_json, read_rows


def fixture_context(root):
    """Simulated provenance/text for adapter contracts, NOT a PDF reader test."""
    law = "FIXTURE/0001"
    (root / "raw").mkdir(parents=True)
    (root / "extractions").mkdir()
    files, captures = [], []
    for i, role in [(1, "main"), (2, "continuation")]:
        # Explicitly simulated source bytes; never claim these are legal PDFs.
        data = f"SYNTHETIC ADAPTER FIXTURE source part {i}; not legal evidence".encode()
        ref = f"raw/part-{i}.fixture"
        (root / ref).write_bytes(data)
        files.append({"file_id": f"fixture-file-{i}", "law_id": law, "source_set_id": "FIXTURE-SET", "file_role": role,
                      "part_order": i, "filename": f"part-{i}.fixture", "raw_file_ref": ref,
                      "download_url": f"https://example.invalid/fixture/{i}", "mime_type": "application/octet-stream",
                      "size_bytes": len(data), "sha256": digest(data), "retrieved_at": "2010-01-01T00:00:00Z"})
        captures.append({"evidence_id": f"fixture-capture-{i}", "kind": "promulgation_pdf", "law_id": law,
                         "sha256": digest(data), "accessed_at": "2010-01-01T00:00:00Z"})
    html = b"SYNTHETIC metadata; not a real download"
    (root / "inputs/evidence").mkdir(parents=True)
    (root / "inputs/evidence/metadata.html").write_bytes(html)
    captures.append({"evidence_id": "fixture-metadata", "law_id": law, "kind": "metadata_html", "sha256": digest(html),
                     "artifact_ref": "metadata.html", "final_url": "https://example.invalid/fixture/metadata",
                     "accessed_at": "2010-01-01T00:00:00Z"})
    specs = [("document", law, None, 0, "FIXTURE LAW", "FIXTURE PREAMBLE"),
             ("chapter", "II", 0, 1, "FIXTURE CHAPTER", ""),
             ("article", "22", 1, 12, "FIXTURE ARTICLE", "FIXTURE LEAD: do not remove this condition"),
             ("clause", "1", 2, 0, "", "1. FIXTURE first clause;"),
             ("clause", "2", 2, 1, "", "2. FIXTURE second clause;"),
             ("clause", "3", 2, 2, "", "3. FIXTURE third clause.")]
    units, spans, parts, offset = [], [], [], 0
    eid = "e_" + digest(b"FIXTURE extraction main")
    for kind, designation, parent_index, ordinal, title, text in specs:
        parent = units[parent_index] if parent_index is not None else None
        u = {"law_id": law, "parent_unit_id": parent["unit_id"] if parent else None,
             "unit_type": kind, "designation": designation, "ordinal": ordinal,
             "canonical_path": (parent["canonical_path"] + "/" if parent else "") + kind + ":" + designation,
             "citation_path": (parent["citation_path"] + " > " if parent else "") + kind + " " + designation,
             "title": title, "text_original": text, "text_sha256": digest(text.encode())}
        u["unit_id"] = unit_id(u)
        units.append(u)
        for field in ["title", "text_original"]:
            if not u[field]:
                continue
            q = u[field]
            s = {"unit_id": u["unit_id"], "extraction_id": eid, "field_name": field, "span_order": 0,
                 "char_start": offset, "char_end": offset + len(q), "locator_json": canonical({"format": "pdf", "page_start": 1, "page_end": 1}),
                 "quote_sha256": digest(q.encode())}
            s["span_id"] = span_id(s)
            spans.append(s)
            parts.append(q)
            offset += len(q) + 1
    text = "\n".join(parts)
    (root / "extractions/main.txt").write_text(text, encoding="utf8")
    basis = "FIXTURE general rule effective 2025-01-01; FIXTURE exception not applicable."
    (root / "basis.txt").write_text(basis, encoding="utf8")
    ex = []
    for i, txt, ref, ident in [(1, text, "extractions/main.txt", eid),
                              (2, basis, "basis.txt", "e_" + digest(b"FIXTURE extraction continued"))]:
        ex.append({"extraction_id": ident, "file_id": files[i-1]["file_id"], "method": "pdf_text",
                   "tool_version": "synthetic-adapter-fixture; reader not exercised", "text_ref": ref,
                   "text_sha256": digest(txt.encode()), "char_count": len(txt), "review_status": "pending", "created_at": "2011-01-01T00:00:00Z"})
    document = {"law_id": law, "source_id": "FIXTURE-001", "law_title": "Synthetic fixture law; not legal evidence",
                "document_type": "law", "issued_date": "2009-01-01", "document_effective_from": None,
                "source_url": "https://example.invalid/fixture/metadata", "scope_note": "Synthetic adapter tests only"}
    return {"dataset_kind": "synthetic_fixture", "mapping_manifest_sha256": digest(b"fixture mapping"), "mapping_binding": {"fixture": True},
            "tables": {"legal_document": [document], "source_file": files, "extraction": ex, "legal_unit": units, "source_span": spans},
            "proposals": [], "captures": captures,
            "basis": [{"text_ref": "basis.txt", "char_start": 0, "char_end": len(basis), "quote": basis,
                       "quote_sha256": digest(basis.encode()), "evidence_id": "fixture-capture-2", "page": 1}]}


def filled_fixture_form(template):
    f = copy.deepcopy(template)
    f.update(record_status="submitted", reviewer_ref="fixture-reviewer-not-a-person", reviewed_at="2020-01-01T00:00:00Z")
    f["source_review"].update(status="accepted", note="SYNTHETIC source/parts and selected scope checked, not whole file.",
                              evidence_refs=f["suggested_source_evidence"])
    for row in f["unit_reviews"]:
        for d, slot in row["dimensions"].items():
            slot.update(status="accepted" if d == "technical" else row["proposal"]["scope_candidate"] if d == "scope" else "verified_at_snapshot",
                        note="SYNTHETIC review decision for fixture only.", evidence_refs=row["suggested_evidence"][d])
            if d == "applicability":
                slot.update(effective_from="2025-01-01", historical_basis="promulgation_and_changes_reviewed",
                            history_note="SYNTHETIC historical basis checked, not real legal research.", content_note="SYNTHETIC own content matched.")
    return f


class ScopedDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-draft-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "fixture-input"
        self.context = fixture_context(source)
        self.pack = self.root / "review-pack"
        write_pack(self.context, source, self.pack)
        self.manifest = self.pack / "manifest.json"
        self.template = load_json(self.pack / "decision_template.json")
        self.form = filled_fixture_form(self.template)

    def save(self, form=None, name="submission.json"):
        p = self.root / name
        p.write_text(canonical(self.form if form is None else form), encoding="utf8")
        return p

    def compile(self, form=None, history=None):
        _, c, cat, bind, tmpl, props = read_pack(self.manifest)
        return compile_review(self.form if form is None else form, history or {"source_events": [], "unit_events": []}, c, cat, bind, tmpl, props)

    def reseal(self, run):
        p = run / "manifest.json"
        m = load_json(p)
        m["files"] = inventory(run)
        p.write_text(canonical(m) + "\n", encoding="utf8")
        (run / "manifest.sha256").write_text(digest(p.read_bytes()) + "\n", encoding="ascii")

    def test_unfilled_template_is_thirteen_missing_decisions(self):
        h, latest, src, blockers = self.compile(self.template)
        self.assertEqual(h, {"source_events": [], "unit_events": []})
        self.assertEqual(len(blockers), 13)
        self.assertIsNone(self.template["reviewer_ref"])
        run = self.root / "blocked"
        report = admit(self.manifest, self.save(self.template), run, "fixture-20250101-v0.1.0", allow_fixture=True)
        self.assertTrue(report["technical_valid"])
        self.assertFalse(report["admission_ready"])
        self.assertFalse((run / "content.sqlite").exists())
        self.assertEqual(validate_draft(run / "manifest.json"), report)

    def test_successful_fixture_uses_real_ddd_schema_and_stays_draft(self):
        run = self.root / "draft"
        report = admit(self.manifest, self.save(), run, "fixture-20250101-v0.1.0", allow_fixture=True)
        self.assertTrue(report["draft_created"])
        self.assertFalse(report["release_eligible"])
        self.assertEqual(validate_draft(run / "manifest.json"), report)
        with closing(connect_sqlite(run / "content.sqlite", readonly=True)) as db:
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(list(db.execute("PRAGMA foreign_key_check")), [])
            self.assertEqual(db.execute("SELECT status FROM corpus").fetchone()[0], "draft")
            self.assertEqual(db.execute("SELECT count(*) FROM unit_assessment").fetchone()[0], 4)
            self.assertEqual(db.execute("SELECT count(*) FROM legal_unit").fetchone()[0], 6)
            self.assertEqual(db.execute("SELECT count(*) FROM source_span").fetchone()[0], 8)
            self.assertEqual(db.execute("SELECT count(*) FROM extraction WHERE review_status='verified'").fetchone()[0], 0)
            self.assertEqual(list(db.execute("SELECT * FROM serving_chunks")), [])
        uses = read_rows(run / "scoped_review_uses.jsonl")
        self.assertTrue(all(u["structural_only"] and not u["scoped_target_review_complete"] and not u["scoped_context_review_complete"] for u in uses[:2]))
        self.assertEqual(sum(u["scoped_target_review_complete"] for u in uses), 3)
        self.assertTrue(all(not u["serving_eligible"] for u in uses))
        self.assertEqual((run / "schema.sql").read_bytes(), (BASE_DIR / "schemas/data_model_v1/schema.sql").read_bytes())

    def test_one_dimension_can_complete_while_others_pending(self):
        f = copy.deepcopy(self.template)
        f.update(record_status="submitted", reviewer_ref=self.form["reviewer_ref"], reviewed_at=self.form["reviewed_at"])
        f["unit_reviews"][1]["dimensions"]["scope"] = self.form["unit_reviews"][1]["dimensions"]["scope"]
        h, latest, src, blockers = self.compile(f)
        self.assertEqual(len(h["unit_events"]), 1)
        self.assertEqual(len(blockers), 12)
        self.assertIsNone(src)

    def test_scope_and_date_overrides_are_valid_decisions(self):
        self.form["unit_reviews"][1]["dimensions"]["scope"].update(status="excluded", note="SYNTHETIC exclusion with evidence; overrides proposal.")
        self.form["unit_reviews"][2]["dimensions"]["applicability"].update(effective_from="2024-12-31", note="SYNTHETIC date override justified by fixture evidence.")
        h, _, _, blockers = self.compile()
        self.assertEqual(blockers, [])
        self.assertEqual(sum(e["proposal_relation"] == "override" for e in h["unit_events"]), 2)

    def test_binding_unit_hash_and_evidence_fail(self):
        for mutate in [lambda f:f['binding'].update(mapping_manifest_sha256='0'*64),
                       lambda f:f['unit_reviews'][0].update(unit_sha256='0'*64),
                       lambda f:f['unit_reviews'][0]['dimensions']['technical'].update(evidence_refs=[]),
                       lambda f:f.update(snapshot_date='2026-01-01'),
                       lambda f:f.update(reviewer_ref=None),
                       lambda f:f.update(reviewed_at='2000-01-01T00:00:00Z')]:
            f = copy.deepcopy(self.form);mutate(f)
            with self.assertRaises((ValueError, TypeError)):
                self.compile(f)

    def test_invalid_input_is_rejected_before_writing_output(self):
        self.form["binding"]["mapping_manifest_sha256"] = "0"*64
        output = self.root / "must-not-exist"
        with self.assertRaises(ValueError):
            admit(self.manifest, self.save(), output, "fixture-20250101-v0.1.0", allow_fixture=True)
        self.assertFalse(output.exists())

    def test_needs_fix_is_a_decision_and_blocks_admission(self):
        slot = self.form["unit_reviews"][0]["dimensions"]["technical"]
        slot.update(status="needs_fix", evidence_refs=slot["evidence_refs"][:1])
        h, _, _, blockers = self.compile()
        self.assertEqual(len(h["unit_events"]), 12)
        self.assertEqual([b['code'] for b in blockers], ['TECHNICAL_NEEDS_FIX'])

    def test_context_exclusion_does_not_change_child_decision_but_closes_uses(self):
        self.form["unit_reviews"][0]["dimensions"]["scope"].update(status="excluded", note="SYNTHETIC exclude this context by evidence.")
        run = self.root / "context-excluded"
        admit(self.manifest, self.save(), run, "fixture-20250101-v0.1.0", allow_fixture=True)
        self.assertTrue(all(not u["scoped_target_review_complete"] for u in read_rows(run/'scoped_review_uses.jsonl')))
        self.assertEqual(sum(a["scope_status"]=='included' for a in read_rows(run/'unit_assessment.jsonl')),3)

    def test_history_supersedes_only_same_unit_dimension(self):
        h, latest, _, _ = self.compile()
        f = copy.deepcopy(self.template)
        f.update(record_status='submitted', reviewer_ref=self.form['reviewer_ref'], reviewed_at='2020-01-02T00:00:00Z')
        r=f['unit_reviews'][1]
        slot=r['dimensions']['scope']
        slot.update(status='excluded', note='SYNTHETIC new scope only.', evidence_refs=r['suggested_evidence']['scope'],
                    supersedes=latest[(r['unit_id'],'scope')]['decision_id'])
        new, latest2, _, blockers = self.compile(f,h)
        self.assertEqual(len(new['unit_events']),13)
        self.assertEqual(blockers,[])
        self.assertEqual(latest2[(r['unit_id'],'applicability')],latest[(r['unit_id'],'applicability')])
        slot['supersedes']=latest[(r['unit_id'],'applicability')]['decision_id']
        with self.assertRaises(ValueError):self.compile(f,h)

    def test_fixture_cannot_enter_real_namespace_or_without_flag(self):
        for version, allow in [('traffic-20250101-v0.1.0',True),('fixture-20250101-v0.1.0',False)]:
            with self.assertRaises(ValueError):admit(self.manifest,self.save(name=version+'.json'),self.root/version,version,allow_fixture=allow)

    def test_tampering_after_reseal_is_rejected(self):
        run=self.root/'draft'
        admit(self.manifest,self.save(),run,'fixture-20250101-v0.1.0',allow_fixture=True)
        p=run/'scoped_review_uses.jsonl';rows=read_rows(p)
        rows[0]['scoped_target_review_complete']=True
        p.write_text('\n'.join(canonical(r) for r in rows)+'\n',encoding='utf8')
        self.reseal(run)
        with self.assertRaises(ValueError):validate_draft(run/'manifest.json')

    def test_frozen_db_or_verified_file_rejected_after_reseal(self):
        for column, value in [('status','frozen'),('review_status','verified')]:
            run=self.root/value
            admit(self.manifest,self.save(name=value+'.json'),run,'fixture-20250101-v0.1.0',allow_fixture=True)
            with closing(connect_sqlite(run/'content.sqlite')) as db:
                with db:
                    db.execute(f"UPDATE {'corpus' if column=='status' else 'extraction'} SET {column}=?",(value,))
            self.reseal(run)
            with self.assertRaises(ValueError):validate_draft(run/'manifest.json')

    def test_cli_distinguishes_missing_decisions_from_invalid_input(self):
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            blocked=main(['admit','--review-manifest',str(self.manifest),'--decisions',str(self.save(self.template)),
                          '--run-dir',str(self.root/'blocked'),'--corpus-version','fixture-20250101-v0.1.0','--allow-fixture'])
            invalid=main(['admit','--review-manifest','missing.json','--decisions','missing.json',
                          '--run-dir',str(self.root/'invalid'),'--corpus-version','traffic-20250101-v0.1.0'])
        self.assertEqual(blocked,2)
        self.assertEqual(invalid,1)

    def test_import_has_no_io_network_models_or_databases(self):
        script='''
import sys, importlib
def audit(event,args):
 if event.startswith(('socket.','sqlite3.connect')): raise AssertionError(event)
 if event=='open' and ((isinstance(args[1],str) and any(c in args[1] for c in 'wax+')) or (args[2]&3)): raise AssertionError('write on import')
sys.addaudithook(audit)
importlib.import_module('src.article22_draft')
assert not any(k in sys.modules for k in ['torch','pdfplumber','transformers'])
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__ == '__main__':
    unittest.main()
