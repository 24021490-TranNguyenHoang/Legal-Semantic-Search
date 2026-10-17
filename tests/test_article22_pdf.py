"""Synthetic in-memory mapping fixtures; real-PDF checks are opt-in CLI runs.

These texts are not legal evidence and are never imported into a corpus.
"""
import copy
from contextlib import closing
import importlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.article22_pdf import DEFAULT_CONFIG, map_units, require_config, main, validate
from src.assessment_evidence import inventory
from src.config import STAGING_DIR
from src.content_comparison import compare_fields, select_interval
from src.ingestion.legal_tree import unit_id, span_id
from src.source_contracts import canonical, digest, connect_sqlite
from src.source_registry import load_json, read_rows


def synthetic_pages():
    texts = {n: f"SYNTHETIC PAGE {n}" for n in range(1, 20)}
    texts[1] = "FIXTURE\nLUẬT\nTÊN GIẢ LẬP\nCăn cứ Hiến pháp giả lập;\nChương I\nTÊN CHƯƠNG GIẢ LẬP"
    # Inline chapter reference must not be mistaken for the actual heading.
    texts[10] = "Dẫn chiếu tại Chương II\ncủa luật giả lập.\nChương II\nTÊN CHƯƠNG GIẢ LẬP\n" + "\n".join(f"Điều {n}. Tiêu đề giả lập" for n in range(10, 22))
    texts[19] = ("FIXTURE\nĐiều 22. Tiêu đề giả lập\nKhi đến gần đường giao nhau, GIẢ LẬP\n"
                 "1. Tại nơi đường giao nhau GIẢ LẬP không được bỏ phủ định;\n"
                 "2. Tại nơi đường giao nhau GIẢ LẬP 50 km/h;\n"
                 "3. Tại nơi đường giao nhau GIẢ LẬP đường cho xe đi đến từ bên trái.")
    offset, pages, all_parts = 0, {}, []
    for n, t in texts.items():
        loc = {"format": "pdf", "page_start": n, "page_end": n, "width": 600.0, "height": 800.0}
        pages[n] = {"text": t, "node": {"char_start": offset, "char_end": offset + len(t),
                                       "locator": loc, "locator_id": f"fixture_locator_{n}"}}
        all_parts.append(t)
        offset += len(t) + 1
    return {"extraction": {"extraction_id": "e_" + "1" * 64, "text_ref": "fixture/normalized.txt"}}, "\n".join(all_parts), pages


class NarrowPdfMappingTests(unittest.TestCase):
    def setUp(self):
        self.config = load_json(DEFAULT_CONFIG)
        self.record, self.text, self.pages = synthetic_pages()

    def test_span_roundtrip_and_three_offset_namespaces(self):
        units, spans, mappings = map_units(self.config, self.record, self.pages)
        self.assertEqual(len(units), 6)
        self.assertEqual(len(spans), 8)
        self.assertEqual(len({u["unit_id"] for u in units}), 6)
        for u in units:
            self.assertEqual(u["unit_id"], unit_id(u))
            for field in ("title", "text_original"):
                own = sorted([s for s in spans if s["unit_id"] == u["unit_id"] and s["field_name"] == field], key=lambda s: s["span_order"])
                self.assertEqual(u[field], "\n".join(self.text[s["char_start"]:s["char_end"]] for s in own))
        for s, m in zip(spans, mappings):
            self.assertEqual(s["span_id"], span_id(s))
            self.assertEqual(self.text[s["char_start"]:s["char_end"]], m["quote"])
            self.assertEqual(m["extraction_char_start"], m["page_extraction_char_start"] + m["pdf_page_char_start"])
            u = next(u for u in units if u["unit_id"] == m["unit_id"])
            self.assertEqual(u[m["field_name"]][m["field_char_start"]:m["field_char_end"]], m["quote"])
            self.assertEqual(digest(m["quote"].encode("utf8")), m["quote_sha256"])
        self.assertTrue(all(u["parent_unit_id"] == units[2]["unit_id"] for u in units[3:]))
        self.assertNotIn(units[3]["text_original"], units[2]["text_original"])
        self.assertEqual([u["ordinal"] for u in units], [0, 1, 12, 0, 1, 2])

    def test_deterministic_tree_spans_ids(self):
        a = map_units(self.config, self.record, self.pages)
        b = map_units(copy.deepcopy(self.config), copy.deepcopy(self.record), copy.deepcopy(self.pages))
        self.assertEqual(canonical(a), canonical(b))

    def test_parent_identity_change_changes_descendant_ids(self):
        first = map_units(self.config, self.record, self.pages)[0]
        other = copy.deepcopy(self.pages)
        other[1]["text"] = other[1]["text"].replace("TÊN GIẢ LẬP", "tên giả lập")
        second = map_units(self.config, self.record, other)[0]
        self.assertTrue(all(a["unit_id"] != b["unit_id"] for a, b in zip(first, second)))
        self.assertEqual(first[2]["text_original"], second[2]["text_original"])

    def test_missing_and_ambiguous_anchors_fail(self):
        for text in ("missing", "start end start end"):
            with self.assertRaises(ValueError):
                select_interval(text, {"start": "start", "end": "end"})

    def test_uncertain_source_order_fails_instead_of_renumbering(self):
        self.pages[10]["text"] = self.pages[10]["text"].replace("Điều 11.", "Điều 99.")
        with self.assertRaisesRegex(ValueError, "ordinal"):
            map_units(self.config, self.record, self.pages)

    def test_scope_cannot_expand(self):
        self.config["nodes"].append(copy.deepcopy(self.config["nodes"][-1]))
        with self.assertRaisesRegex(ValueError, "Scope"):
            require_config(self.config)

    def test_whitespace_is_classification_not_a_rewrite(self):
        r = compare_fields("Không được đi; 50 km/h.", "Không được\nđi; 50 km/h.")
        self.assertEqual(r["classification"], "format_only")
        self.assertIn("\n", r["pdf_text"])
        self.assertEqual(r["differences"][0]["pdf_field_start"], 10)
        self.assertEqual(compare_fields("Không được đi", "Được đi")["classification"], "content_difference")

    def test_cli_missing_input_creates_no_run(self):
        with tempfile.TemporaryDirectory(prefix="test-pdf-admission-", dir=STAGING_DIR) as temp:
            output = Path(temp) / "should-not-exist"
            code = main(["prepare", "--evidence-manifest", str(Path(temp)/'input/missing.json'),
                         "--tree-manifest", "missing.json", "--comparison-manifest", "missing.json", "--run-dir", str(output)])
            self.assertNotEqual(code, 0)
            self.assertFalse(output.exists())

    def test_import_no_io_network_or_models(self):
        script = '''
import importlib, sys
def audit(event, args):
    if event.startswith(('socket.', 'sqlite3.connect')):
        raise AssertionError(event)
    if event == 'open' and ((isinstance(args[1], str) and any(c in args[1] for c in 'wax+')) or (args[2] & 3)):
        raise AssertionError('write on import')
sys.addaudithook(audit)
importlib.import_module('src.content_comparison')
importlib.import_module('src.article22_pdf')
assert not any(n in sys.modules for n in ['pdfplumber', 'torch', 'transformers'])
'''
        r = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipUnless(os.environ.get("VTLS_ARTICLE22_MANIFEST"), "Supply captured PDF run via VTLS_ARTICLE22_MANIFEST")
class RealPdfAdmissionChecks(unittest.TestCase):
    """Poison copies only. Upstream replay is covered by separate full CLI validate.

These checks isolate mapping/DB/pending gates without rereading 82 PDF pages
for every deliberate tamper case. Original evidence/run are never modified.
"""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-pdf-real-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "copy"
        shutil.copytree(Path(os.environ["VTLS_ARTICLE22_MANIFEST"]).resolve().parent, self.run)
        self.manifest = self.run / "manifest.json"

    def reseal(self):
        metadata = load_json(self.manifest)
        # Only this isolated test copy is rewritten. Production seal uses
        # exclusive creation and correctly refuses an existing manifest.
        metadata["files"] = inventory(self.run)
        self.manifest.write_text(canonical(metadata) + "\n", encoding="utf8")
        (self.run / "manifest.sha256").write_text(digest(self.manifest.read_bytes()) + "\n", encoding="ascii")

    def local_validate(self):
        with patch("src.article22_pdf.preflight"), patch("src.article22_pdf.validate_extraction",
                return_value={"technical_valid": True, "processing_success": True, "issue_count": 1}):
            return validate(self.manifest)

    def test_actual_scope_ids_fk_and_no_fake_corpus(self):
        self.assertTrue(self.local_validate()["technical_valid"])
        with closing(connect_sqlite(self.run / "admission.prepared.sqlite", readonly=True)) as db:
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(list(db.execute("PRAGMA foreign_key_check")), [])
            self.assertEqual(db.execute("SELECT count(*) FROM legal_unit").fetchone()[0], 6)
            for table in ("corpus", "unit_assessment", "chunk"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
        a = read_rows(self.run / "assessments.pending.jsonl")
        self.assertEqual(sum(r["assessment_required_for_planned_use"] for r in a), 4)
        self.assertTrue(all(not r["release_eligible"] and not r["ready_to_load_assessment"] for r in a))

    def test_wrong_code_binding_rejected_after_reseal(self):
        p = self.run / "binding.json"
        data = load_json(p)
        data["code_sha256"]["mapping"] = "0" * 64
        p.write_text(canonical(data), encoding="utf8")
        self.reseal()
        self.assertFalse(self.local_validate()["technical_valid"])

    def test_prepared_sqlite_rejects_missing_parent(self):
        with closing(connect_sqlite(self.run / "admission.prepared.sqlite")) as db:
            unit = db.execute("SELECT unit_id FROM legal_unit WHERE unit_type='clause' LIMIT 1").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE legal_unit SET parent_unit_id='missing-parent' WHERE unit_id=?", (unit,))
            db.rollback()

    def test_wrong_policy_version_rejected_after_reseal(self):
        p = self.run / "binding.json"
        data = load_json(p)
        data["policy_version"] = "wrong-policy.v999"
        p.write_text(canonical(data), encoding="utf8")
        self.reseal()
        self.assertFalse(self.local_validate()["technical_valid"])

    def test_wrong_extraction_offsets_rejected_after_reseal(self):
        p = self.run / "mapping.pending.jsonl"
        rows = read_rows(p)
        rows[-1]["extraction_char_start"] += 1
        p.write_text("\n".join(canonical(r) for r in rows) + "\n", encoding="utf8")
        self.reseal()
        self.assertFalse(self.local_validate()["technical_valid"])

    def test_cannot_assert_verified_from_four_compared_units(self):
        p = self.run / "extractions.pending.jsonl"
        rows = read_rows(p)
        rows[0]["review_status"] = "verified"
        p.write_text("\n".join(canonical(r) for r in rows) + "\n", encoding="utf8")
        self.reseal()
        self.assertFalse(self.local_validate()["technical_valid"])


if __name__ == "__main__":
    unittest.main()
