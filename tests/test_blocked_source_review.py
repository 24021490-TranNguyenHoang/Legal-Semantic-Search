"""Synthetic layout fixtures, never legal evidence or reviewer decisions."""
import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from src.blocked_source_review import non_text_horizontal_line, scoped_layout_parse, W, A, V
from src.extraction_pipeline import extract_file, issue_record, DEFAULT_CONFIG
from src.experimental_dataset import load
from src.ingestion.legal_tree import parse_extraction
from src.source_contracts import digest
from tests.test_stage4 import fixture


def line():
    p = ET.Element(W + "p")
    ET.SubElement(ET.SubElement(p, W + "drawing"), A + "prstGeom", prst="line")
    ET.SubElement(p, A + "ext", cx="500", cy="0")
    ET.SubElement(ET.SubElement(p, W + "pict"), V + "line", {"from": "0pt,1pt", "to": "40pt,1pt"})
    return p


class LineGateTests(unittest.TestCase):
    def test_horizontal_only(self):
        self.assertTrue(non_text_horizontal_line(line()))

    def test_text_field_symbol_numbering_image_revision_never_suppressed(self):
        for tag in [W + "t", W + "sym", W + "numPr", W + "instrText", W + "fldChar", W + "ins", W + "del", A + "blip", V + "imagedata"]:
            p = line(); ET.SubElement(p, tag)
            self.assertFalse(non_text_horizontal_line(p), tag)

    def test_nonhorizontal_or_unknown_shape(self):
        p = line(); p.find(A + "ext").set("cy", "1")
        self.assertFalse(non_text_horizontal_line(p))
        p = line(); next(p.iter(V + "line")).set("to", "40pt,2pt")
        self.assertFalse(non_text_horizontal_line(p))
        p = line(); next(p.iter(A + "prstGeom")).set("prst", "rect")
        self.assertFalse(non_text_horizontal_line(p))


class ScopedParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name); path = root / "fixture.docx"
        fixture(path, ["LUẬT", "Synthetic layout fixture", "Điều 1. Quy tắc", "1. FIXTURE không mất 0,25 mg/l.", "", "Luật này được Quốc hội thông qua (FIXTURE)."], header=False)
        with ZipFile(path) as z:
            content = {n: z.read(n) for n in z.namelist()}
        doc = ET.fromstring(content["word/document.xml"]); body = doc.find(W + "body")
        body.remove(list(body)[4]); body.insert(4, line())
        content["word/document.xml"] = ET.tostring(doc, encoding="utf-8")
        with ZipFile(path, "w") as z:
            for n, b in content.items(): z.writestr(n, b)
        self.raw = path.read_bytes()
        source = {"file_id": "10175c53-bab0-5ea4-b2ed-50b680e0ed40", "law_id": "SYNTHETIC/LAYOUT",
                  "measured": {"raw_file_ref": "fixture.docx", "sha256": digest(self.raw), "size_bytes": len(self.raw),
                               "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}}
        self.record, text, _, self.trace, qs = extract_file(source, root, load(DEFAULT_CONFIG))
        self.text = text.decode("utf8")
        self.qs = [issue_record(source["file_id"], self.record["extraction"]["extraction_id"], q, i) for i, q in enumerate(qs)]
        node = next(n for n in self.trace["nodes"] if n["locator"].get("paragraph_index") == 4)
        self.spec = {"law_id": source["law_id"], "raw_sha256": digest(self.raw), "locator": node["locator"],
                     "char_start": node["char_start"], "char_end": node["char_end"]}

    def test_reparse_changes_only_layout_not_units_spans(self):
        original = parse_extraction(self.record, self.text, self.trace, self.qs)
        fixed, sidecar = scoped_layout_parse(self.record, self.text, self.trace, self.qs, self.raw, self.spec)
        self.assertEqual(fixed["units"], original["units"])
        self.assertEqual(fixed["spans"], original["spans"])
        self.assertEqual(len(fixed["issues"]), len(original["issues"])-1)
        self.assertEqual(sidecar["source_review_status"], "pending")
        self.assertEqual(len(sidecar["source_warning_ids"]), 2)

    def test_bad_binding_or_nonzero_range_rejected(self):
        for changes in [{"raw_sha256": "bad"}, {"char_end": self.spec["char_end"]+1}, {"law_id": "other"}]:
            with self.assertRaises(ValueError):
                scoped_layout_parse(self.record, self.text, self.trace, self.qs, self.raw, {**self.spec, **changes})

    def test_unexpected_warning_not_suppressed(self):
        qs = copy.deepcopy(self.qs); qs[0]["code"] = "DOCX_GENERATED_TEXT_REVIEW"
        with self.assertRaises(ValueError):
            scoped_layout_parse(self.record, self.text, self.trace, qs, self.raw, self.spec)


if __name__ == "__main__":
    unittest.main()
