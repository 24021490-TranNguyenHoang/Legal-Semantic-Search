"""Controlled DOCX/PDF fixtures only; no OCR/models or corpus indexing."""
from contextlib import closing, redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import copy
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from src.config import BASE_DIR, STAGING_DIR
from src.extraction_pipeline import (build_run, validate_run, extract_file, DEFAULT_CONFIG,
                                     ExtractionBatchError, main)
from src.ingestion.extractors import read_source, UnsupportedSource, DOCX_MIME, W
from src.ingestion.extraction_normalizer import normalize_fragment, serialize
from src.source_contracts import canonical, connect_sqlite, digest
from src.source_registry import register, load_json, read_rows


def docx_fixture(path, *, broken=False, unsupported=False):
    document = ET.Element(W + "document")
    body = ET.SubElement(document, W + "body")
    def paragraph(parent, text):
        p = ET.SubElement(parent, W + "p")
        run = ET.SubElement(p, W + "r")
        ET.SubElement(run, W + "t").text = text
        return p
    paragraph(body, unicodedata.normalize("NFD", "Điều 1. Không được vượt quá 50 km/h; 0,25 mg/l."))
    table = ET.SubElement(body, W + "tbl")
    for row_number, values in enumerate((("Phạt tiền", "1.000.000 đồng"), ("Không được", "đổi đơn vị mg/l."))):
        row = ET.SubElement(table, W + "tr")
        for column, value in enumerate(values):
            cell = ET.SubElement(row, W + "tc")
            if column == 0:
                props = ET.SubElement(cell, W + "tcPr")
                ET.SubElement(props, W + "gridSpan", {W + "val": "2"})
                ET.SubElement(props, W + "vMerge", {W + "val": "restart" if row_number == 0 else "continue"})
            paragraph(cell, value)
    paragraph(body, "Điều 2. Phải nhường đường — không được đi tiếp.")
    if unsupported:
        ET.SubElement(body, W + "altChunk")
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr("word/document.xml", b"<broken" if broken else ET.tostring(document, encoding="utf-8"))


def pdf_fixture(path):
    """Handwritten valid PDF with known ASCII text on page 1 and empty page 2."""
    text = b"BT /F1 12 Tf 50 750 Td (KHONG duoc vuot 50 km/h; 0.25 mg/l; 1.000.000 VND.) Tj ET"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
               b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 7 0 R >>",
               b"<< /Length 0 >>\nstream\n\nendstream"]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    path.write_bytes(data)


class Stage3Tests(unittest.TestCase):
    def setUp(self):
        STAGING_DIR.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage3-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "raw").mkdir()
        (self.root / "inventory.md").write_text("Synthetic fixture, not law", encoding="utf-8")
        docx_fixture(self.root / "raw/example.docx")
        self.config = load_json(DEFAULT_CONFIG)

    def sources(self, names=("example.docx",), *, run_name="sources"):
        registry = {"contract_version": "source-registration.v1", "dataset_kind": "synthetic_fixture",
                    "snapshot_date": "2025-01-01", "file_id_namespace": "4682a18d-a842-48aa-8549-ab2b74d1e610",
                    "documents": [], "files": []}
        for i, name in enumerate(names, 1):
            law = f"FIXTURE/{i}"
            registry["documents"].append({"source_id": f"FIXTURE-{i}", "law_id": law,
                                          "declared": {"law_title": "Synthetic fixture", "document_type": "law",
                                                       "scope_note": "Tests only", "source_url_candidate": "https://example.invalid/fixture",
                                                       "issued_date_candidate": "2024-01-01", "inventory_ref": "inventory.md"}})
            path = self.root / "raw" / name
            registry["files"].append({"law_id": law, "source_set_id": f"FIXTURE-{i}-local",
                                      "part_order": 1, "file_role": "main", "raw_file_ref": "raw/" + name,
                                      "expected_sha256": digest(path.read_bytes())})
        config = self.root / f"{run_name}.json"
        config.write_text(json.dumps(registry), encoding="utf-8")
        run = self.root / run_name
        register(config, run, self.root)
        return run / "manifest.json"

    def build(self, *, source_manifest=None, name="extracted"):
        manifest = source_manifest or self.sources()
        out = self.root / name
        result = build_run(manifest, out, self.root)
        self.assertTrue(result["technical_valid"], result)
        return out

    def get_record(self, run):
        record = read_rows(run / "extractions.pending.jsonl")[0]
        text = (run / record["extraction"]["text_ref"]).read_text(encoding="utf-8")
        trace = load_json(run / record["trace_ref"])
        return record, text, trace

    def reseal(self, run):
        manifest = load_json(run / "manifest.json")
        for entry in manifest["files"]:
            data = (run / entry["path"]).read_bytes()
            entry.update(size_bytes=len(data), sha256=digest(data))
        path = run / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        (run / "manifest.sha256").write_text(digest(path.read_bytes()) + "\n", encoding="ascii")

    def test_docx_order_cells_and_negation_numbers_accents_preserved(self):
        run = self.build()
        record, text, trace = self.get_record(run)
        expected = "Điều 1. Không được vượt quá 50 km/h; 0,25 mg/l.\nPhạt tiền\t1.000.000 đồng\nKhông được\tđổi đơn vị mg/l.\nĐiều 2. Phải nhường đường — không được đi tiếp."
        self.assertEqual(text, expected)
        self.assertEqual([n["kind"] for n in trace["nodes"] if n["parent_index"] == 1], ["paragraph", "table", "paragraph"])
        cells = [n for n in trace["nodes"] if n["kind"] == "cell"]
        self.assertEqual(len(cells), 4)  # Physical cells, no duplicated merged-cell text.
        self.assertEqual(cells[0]["locator"]["grid_span"], "2")
        self.assertEqual(cells[2]["locator"]["v_merge"], "continue")
        self.assertEqual(record["extraction"]["review_status"], "pending")
        self.assertTrue(trace["fragments"][0]["nfc_changed"])

    def test_locators_resolve_to_xml_and_normalized_offsets(self):
        run = self.build()
        record, text, trace = self.get_record(run)
        with ZipFile(self.root / "raw/example.docx") as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        for fragment in trace["fragments"]:
            n = trace["nodes"][fragment["node_index"]]
            path = n["locator"]["xpath"].removeprefix("/w:document/")
            element = root.find(path, {"w": W[1:-1]})
            self.assertIsNotNone(element, path)
            original = "".join(e.text or "" for e in element.iter(W + "t"))
            self.assertEqual(fragment["raw_text"], original)
            quote = text[n["char_start"]:n["char_end"]]
            self.assertEqual(quote, normalize_fragment(original))
            self.assertEqual(digest(quote.encode()), n["quote_sha256"])
        self.assertEqual(record["extraction"]["char_count"], len(text))
        self.assertNotEqual(len(text), len(text.encode()))

    def test_separators_and_leaf_spans_cover_entire_artifact(self):
        run = self.build()
        _, text, trace = self.get_record(run)
        ranges = [(n["char_start"], n["char_end"]) for n in trace["nodes"] if n["kind"] == "paragraph"]
        ranges += [(s["char_start"], s["char_end"]) for s in trace["separators"]]
        cursor = 0
        for start, end in sorted(ranges):
            self.assertEqual(cursor, start)
            cursor = end
        self.assertEqual(cursor, len(text))

    def test_nfc_lf_only_no_cleanup_of_legal_text(self):
        raw = "  KHÔNG  1.000.000 đồng\r\n0,25 mg/l\rkhông được\t50 km/h  "
        text, trace = serialize({"kind": "paragraph", "locator": {"synthetic": True}, "raw_text": raw, "separator": "\n"})
        self.assertEqual(text, raw.replace("\r\n", "\n").replace("\r", "\n"))
        self.assertTrue(trace["fragments"][0]["line_endings_changed"])
        self.assertNotIn("\r", text)

    def test_ancillary_parts_preserved_and_explicitly_labeled(self):
        path = self.root / "raw/example.docx"
        with ZipFile(path, "a") as z:
            header = ET.Element(W + "hdr")
            ET.SubElement(ET.SubElement(ET.SubElement(header, W + "p"), W + "r"), W + "t").text = "Header fixture"
            z.writestr("word/header1.xml", ET.tostring(header, encoding="utf-8"))
        run = self.build()
        _, text, trace = self.get_record(run)
        self.assertTrue(text.endswith("\nHeader fixture"))
        self.assertTrue(any(n["locator"].get("part") == "word/header1.xml" for n in trace["nodes"]))
        self.assertIn("DOCX_ANCILLARY_PARTS_APPENDED", {q["code"] for q in read_rows(run / "quality_issues.jsonl")})

    def test_stable_content_hash_trace_and_id_exclude_run_clock(self):
        source = self.sources()
        first = self.build(source_manifest=source, name="first")
        second = self.build(source_manifest=source, name="second")
        a, text, trace = self.get_record(first)
        b, text2, trace2 = self.get_record(second)
        self.assertEqual(text, text2)
        self.assertEqual(trace, trace2)
        self.assertEqual(a["extraction"]["extraction_id"], b["extraction"]["extraction_id"])
        self.assertEqual(a["extraction"]["text_sha256"], b["extraction"]["text_sha256"])
        self.assertEqual(a["source_status"], "pending")
        self.assertNotEqual(a["extraction"]["created_at"], b["extraction"]["created_at"])

    def test_timestamp_is_real_technical_time_and_config_is_recorded(self):
        before = datetime.now(timezone.utc)
        run = self.build()
        after = datetime.now(timezone.utc)
        record, _, _ = self.get_record(run)
        stamp = datetime.fromisoformat(record["extraction"]["created_at"].replace("Z", "+00:00"))
        self.assertLessEqual(before, stamp)
        self.assertLessEqual(stamp, after)
        self.assertEqual(record["config_sha256"], digest(canonical(self.config).encode()))
        tools = json.loads(record["extraction"]["tool_version"])
        self.assertIn("python", tools["versions"])
        self.assertIn("normalizer", tools["code_sha256"])
        source = read_rows(run / "source_snapshot/files.pending.jsonl")[0]
        self.assertIsNone(source["evidence"]["retrieved_at"])

    def test_pdf_fixture_text_page_and_empty_page_no_ocr(self):
        pdf_fixture(self.root / "raw/fixture.pdf")
        source = self.sources(("fixture.pdf",))
        run = self.build(source_manifest=source)
        record, text, trace = self.get_record(run)
        self.assertEqual(record["extraction"]["method"], "pdf_text")
        self.assertIn("KHONG duoc vuot 50 km/h; 0.25 mg/l; 1.000.000 VND.", text)
        pages = [n for n in trace["nodes"] if n["kind"] == "page"]
        self.assertEqual([n["locator"]["page_start"] for n in pages], [1, 2])
        self.assertEqual(pages[1]["char_start"], pages[1]["char_end"])
        issue = next(q for q in read_rows(run / "quality_issues.jsonl") if q["code"] == "PDF_PAGE_NO_TEXT")
        self.assertEqual(issue["locator"]["page_start"], 2)
        self.assertTrue(read_rows(run / "file_status.jsonl")[0]["needs_ocr_review"])
        self.assertFalse(validate_run(run / "manifest.json", self.root)["release_eligible"])

    def test_broken_docx_and_pdf_are_quarantined_without_dropping_good_file(self):
        docx_fixture(self.root / "raw/broken.docx", broken=True)
        (self.root / "raw/broken.pdf").write_bytes(b"%PDF-1.4\ninvalid body")
        source = self.sources(("example.docx", "broken.docx", "broken.pdf"))
        out = self.root / "failed"
        with self.assertRaises(ExtractionBatchError):
            build_run(source, out, self.root)
        result = validate_run(out / "manifest.json", self.root)
        self.assertTrue(result["technical_valid"], result)
        self.assertFalse(result["processing_success"])
        self.assertEqual(result["quarantined_file_count"], 2)
        self.assertEqual(result["extraction_count"], 1)
        self.assertEqual(len(read_rows(out / "file_status.jsonl")), 3)
        self.assertEqual(load_json(out / "run_report.json")["status"], "failed")

    def test_unknown_format_reader_rejected_and_pipeline_failure_reported(self):
        with self.assertRaises(UnsupportedSource):
            read_source(b"fixture", "application/rtf", self.config)
        source = self.sources()
        out = self.root / "unsupported"
        with patch("src.ingestion.extractors.read_source", side_effect=UnsupportedSource("controlled unsupported fixture")):
            with self.assertRaises(ExtractionBatchError):
                build_run(source, out, self.root)
        issues = read_rows(out / "quality_issues.jsonl")
        self.assertEqual(issues[0]["code"], "UNSUPPORTED_SOURCE")
        self.assertFalse(validate_run(out / "manifest.json", self.root)["processing_success"])

    def test_unhandled_docx_structure_is_partial_with_error(self):
        docx_fixture(self.root / "raw/example.docx", unsupported=True)
        source = self.sources()
        out = self.root / "partial"
        with self.assertRaises(ExtractionBatchError):
            build_run(source, out, self.root)
        result = validate_run(out / "manifest.json", self.root)
        self.assertTrue(result["technical_valid"], result)
        self.assertEqual(result["partial_file_count"], 1)

    def test_offsets_and_review_status_tampering_fail_even_after_resealing(self):
        source = self.sources()
        for name in ("offset", "review"):
            run = self.build(source_manifest=source, name=name)
            record, _, trace = self.get_record(run)
            if name == "offset":
                trace["nodes"][2]["char_start"] += 1
                (run / record["trace_ref"]).write_text(canonical(trace) + "\n", encoding="utf-8")
            else:
                record["extraction"]["review_status"] = "verified"
                (run / "extractions.pending.jsonl").write_text(canonical(record) + "\n", encoding="utf-8")
            self.reseal(run)
            self.assertFalse(validate_run(run / "manifest.json", self.root)["technical_valid"])

    def test_sqlite_foreign_keys_reject_fake_official_or_wrong_source(self):
        run = self.build()
        with closing(connect_sqlite(run / "extraction.pending.sqlite")) as db:
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE pending_extraction SET file_id='missing'")
            db.rollback()
        with closing(connect_sqlite(run / "source_snapshot/content.sqlite", readonly=True)) as db:
            for name in ("legal_document", "source_file", "extraction", "corpus"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {name}").fetchone()[0], 0)

    def test_release_gate_missing_input_reuse_and_protected_output(self):
        source = self.sources()
        run = self.build(source_manifest=source)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["validate", "--manifest", str(run / "manifest.json"), "--raw-root", str(self.root), "--require-release-ready"]), 1)
            self.assertEqual(main(["extract", "--source-manifest", str(self.root / "missing"), "--run-dir", str(self.root / "new")]), 1)
        self.assertFalse((self.root / "new").exists())
        for target in (run, BASE_DIR / "data/processed/forbidden", BASE_DIR / "qdrant_db/forbidden"):
            with self.assertRaises((ValueError, FileExistsError)):
                build_run(source, target, self.root)

    def test_real_four_docx_source_order_tables_and_stable_replay(self):
        # Read only: actual raw and Stage 2 config; all test outputs remain synthetic-run storage.
        from src.source_registry import DEFAULT_REGISTRY, registration_records
        _, sources, _ = registration_records(load_json(DEFAULT_REGISTRY), BASE_DIR)
        for source in sources:
            a, text, trace_bytes, trace, _ = extract_file(source, BASE_DIR, self.config)
            b, text2, trace2, _, _ = extract_file(source, BASE_DIR, self.config)
            self.assertEqual(text, text2)
            self.assertEqual(trace_bytes, trace2)
            self.assertEqual(a["extraction"]["extraction_id"], b["extraction"]["extraction_id"])
            nodes = trace["nodes"]
            part = next(n for n in nodes if n["kind"] == "part" and n["locator"]["part"] == "word/document.xml")
            actual = [n["kind"] for n in nodes if n["parent_index"] == part["node_index"]]
            with ZipFile(BASE_DIR / source["measured"]["raw_file_ref"]) as z:
                root = ET.fromstring(z.read("word/document.xml"))
            expected = ["paragraph" if e.tag == W + "p" else "table" for e in root.find(W + "body") if e.tag in {W + "p", W + "tbl"}]
            self.assertEqual(actual, expected)
            if source["law_id"] == "35/2024/QH15":
                self.assertEqual(sum(n["kind"] == "table" for n in nodes if n["locator"].get("part") == "word/document.xml"), 4)
                self.assertTrue(any("Phí sử dụng đường bộ" in text.decode()[n["char_start"]:n["char_end"]]
                                    for n in nodes if n["kind"] == "cell"))

    def test_imports_and_extraction_never_load_inference_or_index_engines(self):
        import builtins
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "sentence_transformers", "rank_bm25", "qdrant_client"}:
                raise AssertionError(name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            self.build()
        script = '''
import sys,os
def audit(event,args):
 if event=='open' and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('write')
 if event in {'os.mkdir','os.remove','socket.connect','os.rename'}:raise AssertionError(event)
sys.addaudithook(audit)
import src.ingestion.extractors,src.ingestion.extraction_normalizer,src.extraction_pipeline
'''
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=BASE_DIR, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
