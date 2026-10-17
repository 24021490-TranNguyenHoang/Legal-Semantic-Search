"""Stage 4 structure/provenance tests; fixtures never enter the real corpus."""
from collections import Counter
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
from unittest.mock import patch
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from src.config import BASE_DIR, STAGING_DIR
from src.extraction_pipeline import extract_file, issue_record, build_run as extract_run, DEFAULT_CONFIG as EXTRACTION_CONFIG
from src.ingestion.extractors import W
from src.ingestion.legal_tree import parse_extraction, validate_tree, unit_id
from src.legal_parser import build_run, validate_run, main, EXPORTS, examples
from src.ingestion.legal_tree_render import readable_artifacts
from src.source_contracts import canonical, connect_sqlite, digest
from src.source_registry import registration_records, DEFAULT_REGISTRY, load_json, read_rows, register


def fixture(path, blocks, *, warning=None, header=True):
    """blocks are source paragraphs or physical table-cell paragraphs."""
    doc = ET.Element(W + "document")
    body = ET.SubElement(doc, W + "body")
    def paragraph(parent, text):
        p = ET.SubElement(parent, W + "p")
        if warning and text == warning[0]:
            if warning[1] == "numbering":
                ET.SubElement(ET.SubElement(p, W + "pPr"), W + "numPr")
            elif warning[1] == "field":
                ET.SubElement(ET.SubElement(p, W + "r"), W + "instrText").text = " SEQ clause "
            elif warning[1] == "revision":
                p = ET.SubElement(p, W + "ins")
        ET.SubElement(ET.SubElement(p, W + "r"), W + "t").text = text
    for block in blocks:
        if isinstance(block, list):
            row = ET.SubElement(ET.SubElement(body, W + "tbl"), W + "tr")
            for text in block:
                paragraph(ET.SubElement(row, W + "tc"), text)
        else:
            paragraph(body, block)
    with ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("word/document.xml", ET.tostring(doc, encoding="utf-8"))
        if header:
            hdr = ET.Element(W + "hdr")
            paragraph(hdr, "Điều 99. Đây là header")
            z.writestr("word/header1.xml", ET.tostring(hdr, encoding="utf-8"))


BLOCKS = ["LUẬT", "Ví dụ giả lập", "Chương I", "QUY TẮC CHUNG", "Mục 1. QUY TẮC",
          "Điều 1. Điều kiện", "Đoạn dẫn trước các Khoản:", "Một đoạn dẫn thứ hai.",
          "1. Không được vượt quá 50 km/h; 0,25 mg/l; 1.000.000 đồng:",
          "a) Phải giữ nguyên dấu.", "đ) Không được bỏ phủ định.",
          "2. Sửa đổi nội dung như sau:", "“Điều 17. Tên điều được trích", "1. Số trong trích dẫn.",
          "5a. Nội dung chưa kết thúc.”", "Điều 2 của văn bản khác được dẫn chiếu tại đây.",
          ["1. Ô bảng không phải Khoản.", "Điều 3. Ô bảng không phải Điều"],
          "Điều 2. Tiếp theo", "Nội dung Điều không có Khoản.",
          "Luật này được Quốc hội thông qua (fixture).", ["CHỦ TỊCH QUỐC HỘI", "Tên giả lập"]]


class Stage4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage4-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "raw").mkdir()
        self.path = self.root / "raw/fixture.docx"
        fixture(self.path, BLOCKS)
        self.source = {"file_id": "10175c53-bab0-5ea4-b2ed-50b680e0ed40", "law_id": "SYNTHETIC/4",
                       "measured": {"raw_file_ref": "raw/fixture.docx", "size_bytes": self.path.stat().st_size,
                                    "sha256": digest(self.path.read_bytes()),
                                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}}

    def parse(self, blocks=None, warning=None):
        if blocks is not None:
            fixture(self.path, blocks, warning=warning)
            self.source["measured"].update(size_bytes=self.path.stat().st_size, sha256=digest(self.path.read_bytes()))
        record, text_bytes, _, trace, raw_issues = extract_file(self.source, self.root, load_json(EXTRACTION_CONFIG))
        eid = record["extraction"]["extraction_id"]
        issues = [issue_record(self.source["file_id"], eid, q, i) for i, q in enumerate(raw_issues)]
        data = {eid: (record, text_bytes.decode("utf-8"), trace)}
        result = parse_extraction(record, data[eid][1], trace, issues)
        self.assertEqual(validate_tree(result["units"], result["spans"], data, result["coverage"]), [])
        return result, data

    def bundle(self):
        (self.root / "inventory.md").write_text("Synthetic fixture only", encoding="utf-8")
        registry = {"contract_version": "source-registration.v1", "dataset_kind": "synthetic_fixture",
                    "snapshot_date": "2025-01-01", "file_id_namespace": "4682a18d-a842-48aa-8549-ab2b74d1e610",
                    "documents": [{"source_id": "FIXTURE-4", "law_id": "SYNTHETIC/4",
                                   "declared": {"law_title": "Synthetic fixture", "document_type": "law", "scope_note": "Tests only",
                                                "source_url_candidate": "https://example.invalid/fixture",
                                                "issued_date_candidate": "2024-01-01", "inventory_ref": "inventory.md"}}],
                    "files": [{"law_id": "SYNTHETIC/4", "source_set_id": "FIXTURE-4-local", "part_order": 1,
                               "file_role": "main", "raw_file_ref": "raw/fixture.docx", "expected_sha256": digest(self.path.read_bytes())}]}
        config = self.root / "sources.json"
        config.write_text(json.dumps(registry), encoding="utf-8")
        register(config, self.root / "sources", self.root)
        extract_run(self.root / "sources/manifest.json", self.root / "extracted", self.root)
        return self.root / "extracted/manifest.json"

    def test_real_hierarchy_intro_negation_and_no_descendant_copy(self):
        result, _ = self.parse()
        units = result["units"]
        article = next(u for u in units if u["unit_type"] == "article" and u["designation"] == "1")
        self.assertEqual(article["text_original"], "Đoạn dẫn trước các Khoản:\nMột đoạn dẫn thứ hai.")
        self.assertNotIn("50 km/h", article["text_original"])
        clause = next(u for u in units if u["unit_type"] == "clause" and u["designation"] == "1")
        self.assertEqual(clause["text_original"], BLOCKS[8])
        self.assertNotIn("Không được bỏ", clause["text_original"])
        point = next(u for u in units if u["unit_type"] == "point" and u["designation"] == "đ")
        self.assertEqual(point["text_original"], BLOCKS[10])
        self.assertEqual(point["parent_unit_id"], clause["unit_id"])
        self.assertEqual(article["citation_path"], "SYNTHETIC/4 > Chương I > Mục 1 > Điều 1")

    def test_single_and_split_chapter_titles_and_actual_levels_only(self):
        result, _ = self.parse(["Chương I. TIÊU ĐỀ MỘT DÒNG", "Điều 1. Một điều", "Nội dung.",
                                "Chương II", "TIÊU ĐỀ DÒNG HAI", "PHẦN TIẾP THEO", "Điều 2. Hai", "Nội dung.",
                                "Chương III", "Tên chương giữ nguyên chữ hoa và thường", "Điều 3. Ba", "Nội dung."])
        chapters = [u for u in result["units"] if u["unit_type"] == "chapter"]
        self.assertEqual([u["title"] for u in chapters], ["TIÊU ĐỀ MỘT DÒNG", "TIÊU ĐỀ DÒNG HAI\nPHẦN TIẾP THEO", "Tên chương giữ nguyên chữ hoa và thường"])
        self.assertFalse(any(u["unit_type"] in {"section", "clause", "point"} for u in result["units"]))

    def test_tables_headers_signature_and_references_not_legal_units(self):
        result, _ = self.parse()
        self.assertEqual([u["designation"] for u in result["units"] if u["unit_type"] == "article"], ["1", "2"])
        self.assertEqual([u["designation"] for u in result["units"] if u["unit_type"] == "clause"], ["1", "2"])
        self.assertEqual(len(result["tables"]), 2)
        self.assertEqual(result["tables"][0]["category"], "unprocessed")
        self.assertEqual(result["tables"][1]["category"], "supporting_non_body")
        own_text = "\n".join(u["text_original"] for u in result["units"])
        self.assertNotIn("Đây là header", own_text)
        self.assertNotIn("Quốc hội thông qua", own_text)
        self.assertIn("5a. Nội dung chưa kết thúc.”", own_text)
        self.assertIn("Điều 2 của văn bản khác", own_text)

    def test_line_number_inside_paragraph_and_article_like_prose_not_heading(self):
        result, _ = self.parse(["Điều 1. Tiêu đề", "Nội dung\n1. Danh sách nội bộ.",
                                "Điều 2. quy định tại văn bản khác.", "Điều 2. Tiêu đề thật", "Nội dung."])
        self.assertFalse(any(u["unit_type"] == "clause" for u in result["units"]))
        self.assertEqual(sum(u["unit_type"] == "article" for u in result["units"]), 2)
        self.assertTrue(any(q["code"] == "ARTICLE_LIKE_PROSE_REFERENCE" for q in result["issues"]))

    def test_unresolved_numbering_field_revision_quarantines_and_resumes(self):
        for kind in ("numbering", "field", "revision"):
            with self.subTest(kind=kind):
                result, _ = self.parse(["Điều 1. Tiêu đề", "Chưa giải mã", "1. Không suy số", "Điều 2. Tin cậy", "Nội dung."], warning=("Chưa giải mã", kind))
                self.assertFalse(any(u["unit_type"] == "clause" for u in result["units"]))
                self.assertTrue(any(c["reason"] == "STRUCTURE_SUSPENDED" for c in result["coverage"]))
                self.assertEqual(sum(u["unit_type"] == "article" for u in result["units"]), 2)

    def test_duplicate_points_both_quarantined_without_guessing_designations(self):
        result, _ = self.parse(["Điều 1. Tiêu đề", "1. Các điểm:", "a) Một", "b) Hai", "a) Trùng",
                                "c) Chưa xác định", "2. Khoản tiếp theo", "a) Hợp lệ"])
        clause1 = next(u for u in result["units"] if u["unit_type"] == "clause" and u["designation"] == "1")
        self.assertEqual([u["designation"] for u in result["units"] if u["parent_unit_id"] == clause1["unit_id"]], ["b"])
        self.assertTrue(any(q["code"] == "CONFLICTING_POINT_DESIGNATION" for q in result["issues"]))
        self.assertEqual(sum(u["unit_type"] == "clause" for u in result["units"]), 2)

    def test_field_roundtrip_offsets_hash_and_determinism(self):
        one, data = self.parse()
        two, _ = self.parse()
        self.assertEqual(one, two)
        for u in one["units"]:
            obj = {k: u[k] for k in ("law_id", "parent_unit_id", "unit_type", "designation", "canonical_path", "citation_path", "ordinal", "title", "text_original")}
            self.assertEqual(u["unit_id"], "u_" + digest(canonical({"identity_schema": "unit.v1", **obj}).encode("utf-8")))
        bad = copy.deepcopy(one["spans"])
        bad[0]["char_start"] += 1
        self.assertTrue(validate_tree(one["units"], bad, data, one["coverage"]))

    def test_lead_before_direct_points_no_fake_clause_or_chapter(self):
        out, _ = self.parse(["Điều 1. Tiêu đề", "Đoạn dẫn trước Điểm:", "a) Không được đổi dấu.", "b) Phải giữ số 50 km/h."])
        article = next(u for u in out["units"] if u["unit_type"] == "article")
        self.assertEqual(article["text_original"], "Đoạn dẫn trước Điểm:")
        self.assertEqual([u["unit_type"] for u in out["units"]], ["document", "article", "point", "point"])
        self.assertTrue(all(u["parent_unit_id"] == article["unit_id"] for u in out["units"] if u["unit_type"] == "point"))

    def test_annex_recorded_not_attached_to_last_article_even_after_signature(self):
        for signature in ([], ["Luật này được Quốc hội thông qua (fixture)."]):
            out, _ = self.parse(["Điều 1. Tiêu đề", "Nội dung thân luật.", *signature,
                                 "PHỤ LỤC I", "Điều 2. Heading trong phụ lục", ["1. Ô bảng", "Không đoán Khoản"]])
            self.assertEqual(sum(u["unit_type"] == "article" for u in out["units"]), 1)
            self.assertTrue(any(q["code"] == "ANNEX_STRUCTURE_NOT_SUPPORTED" for q in out["issues"]))
            self.assertTrue(all(t["reason"] == "ANNEX_STRUCTURE_NOT_SUPPORTED" for t in out["tables"]))
            self.assertEqual(next(u for u in out["units"] if u["unit_type"] == "article")["text_original"], "Nội dung thân luật.")

    def test_body_table_signature_words_not_a_boundary_without_end_position(self):
        out, _ = self.parse(["Điều 1. Tiêu đề", "1. Nội dung trước bảng", ["CHỦ TỊCH QUỐC HỘI", "Tên cột chưa phân tích"], "2. Nội dung sau bảng"])
        self.assertEqual(out["tables"][0]["category"], "unprocessed")
        self.assertEqual([u["designation"] for u in out["units"] if u["unit_type"] == "clause"], ["1", "2"])

    def test_no_supported_structure_is_explicitly_reported(self):
        out, _ = self.parse(["Văn bản chưa nhận diện được cấu trúc", "Không tự tạo Điều hoặc Khoản."])
        self.assertEqual([u["unit_type"] for u in out["units"]], ["document"])
        self.assertTrue(any(q["code"] == "NO_RELIABLE_LEGAL_STRUCTURE" for q in out["issues"]))
        self.assertTrue(any(c["category"] == "needs_review" for c in out["coverage"]))

    def test_unclear_structure_and_explicit_lists_raise_issues_without_guessing(self):
        for unclear in ("Điều X. Không rõ số", "1a. Không rõ cấp", "Danh sách minh họa:"):
            out, _ = self.parse(["Điều 1. Tiêu đề", unclear, "1. Dòng chưa rõ", "2. Dòng tiếp", "Điều 2. Điều thật", "Nội dung."])
            self.assertFalse(any(u["unit_type"] == "clause" for u in out["units"]))
            self.assertEqual([u["designation"] for u in out["units"] if u["unit_type"] == "article"], ["1", "2"])
            self.assertTrue(any(q["code"] in {"UNCLEAR_HEADING", "UNCLEAR_NUMBERED_STRUCTURE", "AMBIGUOUS_NUMBERED_LIST"} for q in out["issues"]))

    def test_undelimited_amendment_does_not_create_replacement_article_at_root(self):
        out, _ = self.parse(["Điều 1. Sửa đổi văn bản", "1. Thay thế Điều 2 của văn bản khác như sau:",
                             "Điều 2. Tên Điều được thay thế", "1. Nội dung thay thế chưa rõ ranh giới", "Điều 3. Cũng chưa xác định"])
        self.assertEqual([u["designation"] for u in out["units"] if u["unit_type"] == "article"], ["1"])
        self.assertTrue(any(q["code"] == "UNDELIMITED_AMENDMENT" for q in out["issues"]))
        self.assertEqual(sum(c["reason"] == "UNDELIMITED_AMENDMENT_REGION" for c in out["coverage"]), 3)

    def test_quoted_amendment_nested_instructions_and_unclosed_quote(self):
        out, _ = self.parse(["Điều 1. Sửa đổi", "1. Sửa đổi một số điểm của khoản 2 Điều 4 như sau:",
                             "a) Thay thế điểm a khoản 2 Điều 4 như sau:", "“Điều 2. Tên Điều được trích", "1. Nội dung trích.”",
                             "Điều 2. Điều thật", "Nội dung."])
        self.assertEqual([u["designation"] for u in out["units"] if u["unit_type"] == "article"], ["1", "2"])
        self.assertFalse(any(q["code"] == "UNDELIMITED_AMENDMENT" for q in out["issues"]))
        out, _ = self.parse(["Điều 1. Sửa đổi", "“Điều 2. Chưa đóng quote", "1. Nội dung", "Điều 3. Không suy ranh giới"])
        self.assertEqual(sum(u["unit_type"] == "article" for u in out["units"]), 1)
        self.assertTrue(any(q["code"] == "UNCLOSED_QUOTATION" for q in out["issues"]))
        self.assertFalse(any("Điều 3. Không suy ranh giới" in u["text_original"] for u in out["units"]))
        self.assertTrue(any(c["reason"] == "UNCLOSED_QUOTATION_REGION" for c in out["coverage"]))

    def test_readable_views_show_only_own_text_and_roundtrip_replay(self):
        out, _ = self.parse()
        views = readable_artifacts(out, examples(out))
        index = json.loads(views["trees/index.json"])
        self.assertEqual(index[0]["law_id"], "SYNTHETIC/4")
        tree = views[index[0]["tree_ref"]]
        self.assertIn("UNPROCESSED / NEEDS REVIEW", tree)
        self.assertIn("text_original#0", tree)
        self.assertEqual(tree.count("Không được bỏ phủ định."), 1)
        self.assertEqual(views, readable_artifacts(out, examples(out)))

    def test_validator_rejects_duplicates_cycles_wrong_law_and_fake_levels(self):
        out, data = self.parse()
        for mutation in ("duplicate", "cycle", "wrong_law", "fake", "ordinal"):
            units = copy.deepcopy(out["units"])
            if mutation == "duplicate":
                units.append(units[-1])
            elif mutation == "cycle":
                units[0]["parent_unit_id"] = units[-1]["unit_id"]
            elif mutation == "wrong_law":
                units[1]["law_id"] = "OTHER/LAW"
            elif mutation == "fake":
                units[1]["unit_type"] = "point"
            else:
                units[-1]["ordinal"] = True
            with self.subTest(mutation=mutation):
                self.assertTrue(validate_tree(units, out["spans"], data, out["coverage"]))

    def test_bundle_sqlite_foreign_keys_pending_status_and_release_gate(self):
        extraction = self.bundle()
        run = self.root / "parsed"
        import builtins
        original_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "sentence_transformers", "qdrant_client", "rank_bm25"}:
                raise AssertionError("Forbidden runtime dependency: " + name)
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            result = build_run(extraction, run, self.root)
        self.assertTrue(result["technical_valid"], result)
        self.assertFalse(result["release_eligible"])
        self.assertEqual(validate_run(run / "manifest.json", self.root), result)
        self.assertEqual(len(load_json(run / "trees/index.json")), 1)
        with closing(connect_sqlite(run / "legal_tree.pending.sqlite")) as db:
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual({r[0] for r in db.execute("SELECT review_status FROM pending_legal_unit")}, {"pending"})
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE pending_source_span SET law_id='OTHER'")
            db.rollback()
        with closing(connect_sqlite(run / "extraction_snapshot/source_snapshot/content.sqlite", readonly=True)) as db:
            for name in ("legal_document", "source_file", "extraction", "legal_unit", "source_span", "corpus"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {name}").fetchone()[0], 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["validate", "--manifest", str(run / "manifest.json"), "--raw-root", str(self.root), "--require-release-ready"]), 1)

    def test_missing_invalid_input_output_reuse_and_tampering_fail(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["parse", "--extraction-manifest", str(self.root / "missing"), "--run-dir", str(self.root / "no-output")]), 1)
        self.assertFalse((self.root / "no-output").exists())
        extraction = self.bundle()
        with self.assertRaises(ValueError):
            build_run(extraction, BASE_DIR / "data/processed/forbidden", self.root)
        run = self.root / "parsed"
        build_run(extraction, run, self.root)
        with self.assertRaises(FileExistsError):
            build_run(extraction, run, self.root)
        rows = read_rows(run / EXPORTS["units"])
        rows[1]["title"] = "Fabricated title"
        (run / EXPORTS["units"]).write_text("".join(canonical(r) + "\n" for r in rows), encoding="utf-8")
        # Reseal checksums: replay and field reconstruction must still reject it.
        manifest = load_json(run / "manifest.json")
        for e in manifest["files"]:
            b = (run / e["path"]).read_bytes()
            e.update(size_bytes=len(b), sha256=digest(b))
        (run / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
        (run / "manifest.sha256").write_text(digest((run / "manifest.json").read_bytes()), encoding="ascii")
        self.assertFalse(validate_run(run / "manifest.json", self.root)["technical_valid"])
        rec = read_rows(self.root / "extracted/extractions.pending.jsonl")[0]
        text_path = self.root / "extracted" / rec["extraction"]["text_ref"]
        text_path.write_text("Tampered extraction", encoding="utf-8")
        with self.assertRaises(ValueError):
            build_run(extraction, self.root / "invalid-input-output", self.root)
        self.assertFalse((self.root / "invalid-input-output").exists())

    def test_readable_tree_tampering_detected_after_reseal(self):
        extraction = self.bundle()
        run = self.root / "parsed"
        build_run(extraction, run, self.root)
        tree = run / load_json(run / "trees/index.json")[0]["tree_ref"]
        tree.write_text("Invented tree", encoding="utf-8")
        manifest = load_json(run / "manifest.json")
        for entry in manifest["files"]:
            value = (run / entry["path"]).read_bytes()
            entry.update(size_bytes=len(value), sha256=digest(value))
        (run / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
        (run / "manifest.sha256").write_text(digest((run / "manifest.json").read_bytes()), encoding="ascii")
        result = validate_run(run / "manifest.json", self.root)
        self.assertFalse(result["technical_valid"])
        self.assertTrue(any("READABLE_TREE_REPLAY_MISMATCH" in error for error in result["errors"]), result)

    def test_import_and_cli_do_not_initialize_models_write_or_connect(self):
        script = '''
import sys, os, importlib.abc
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'torch','transformers','sentence_transformers','qdrant_client','rank_bm25','pdfplumber','docx'}: raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
def audit(event,args):
 if event=='open' and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND): raise AssertionError('write')
 if event in {'os.mkdir','os.remove','os.rmdir','os.rename','socket.connect','subprocess.Popen'}: raise AssertionError(event)
sys.addaudithook(audit)
import src.legal_parser, src.ingestion.legal_tree
'''
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=BASE_DIR, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for flags, code in ((["--help"], 0), (["parse"], 2), (["validate"], 2)):
            p = subprocess.run([sys.executable, "-B", "-m", "src.legal_parser", *flags], cwd=BASE_DIR, capture_output=True, text=True)
            self.assertEqual(p.returncode, code, p.stderr)

    def test_real_four_sources_chapters_17_leads_and_warning_partition(self):
        _, sources, _ = registration_records(load_json(DEFAULT_REGISTRY), BASE_DIR)
        expected = {"168/2024/NĐ-CP": (4, 55, []),
                    "165/2024/NĐ-CP": (9, 70, ["1", "20", "32", "36", "46", "47", "48", "53"]),
                    "36/2024/QH15": (9, 89, ["22", "26", "66"]),
                    "35/2024/QH15": (6, 86, ["2", "24", "46", "49", "55", "83"])}
        lead_paragraphs = {"168/2024/NĐ-CP": [],
                           "165/2024/NĐ-CP": [17, 225, 478, 537, 672, 690, 709, 763],
                           "36/2024/QH15": [240, 272, 777],
                           "35/2024/QH15": [14, 324, 570, 597, 662, 902]}
        warnings = 0
        for source in sources:
            record, tb, _, trace, qi = extract_file(source, BASE_DIR, load_json(EXTRACTION_CONFIG))
            text = tb.decode("utf-8")
            eid = record["extraction"]["extraction_id"]
            issues = [issue_record(source["file_id"], eid, q, i) for i, q in enumerate(qi)]
            one = parse_extraction(record, text, trace, issues)
            two = parse_extraction(record, text, trace, issues)
            self.assertEqual(one, two)
            data = {eid: (record, text, trace)}
            self.assertEqual(validate_tree(one["units"], one["spans"], data, one["coverage"]), [])
            units = one["units"]
            counts = Counter(u["unit_type"] for u in units)
            chapters, articles, leads = expected[source["law_id"]]
            self.assertEqual(counts["chapter"], chapters)
            self.assertEqual(counts["article"], articles)
            children = {u["parent_unit_id"] for u in units}
            observed = [u["designation"] for u in units if u["unit_type"] == "article" and u["unit_id"] in children and u["text_original"]]
            self.assertEqual(observed, leads)
            for article_no, paragraph_no in zip(leads, lead_paragraphs[source["law_id"]]):
                node = next(n for n in trace["nodes"] if n["locator"].get("part") == "word/document.xml" and n["locator"].get("xpath") == f"/w:document/w:body/w:p[{paragraph_no}]")
                article = next(u for u in units if u["unit_type"] == "article" and u["designation"] == article_no)
                self.assertEqual(article["text_original"], text[node["char_start"]:node["char_end"]])
            for n in trace["nodes"]:
                if n["kind"] != "paragraph" or n["locator"].get("part") != "word/document.xml" or trace["nodes"][n["parent_index"]]["kind"] != "part":
                    continue
                # Exact source paragraph lead before the first clause must be owned by the article.
                if n["locator"]["xpath"] in {"/w:document/w:body/w:p[240]", "/w:document/w:body/w:p[272]"} and source["law_id"] == "36/2024/QH15":
                    self.assertTrue(any(u["unit_type"] == "article" and text[n["char_start"]:n["char_end"]] == u["text_original"] for u in units))
            warnings += len(one["warning_reviews"])
            self.assertTrue(any(u["unit_type"] == "point" and u["designation"] == "đ" for u in units))
            body_text = "\n".join(u["text_original"] for u in units if u["unit_type"] != "document")
            self.assertNotIn("CHỦ TỊCH QUỐC HỘI", body_text)
            self.assertNotIn("Luật này được Quốc hội", body_text)
            if source["law_id"] == "35/2024/QH15":
                self.assertEqual(sum(t["category"] == "unprocessed" for t in one["tables"]), 2)
        self.assertEqual(warnings, 13)


if __name__ == "__main__":
    unittest.main()
