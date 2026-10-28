"""Synthetic DOCX/evidence only, not legal verification."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from src.source_revision import correct_package, replace_text, sha, structural_check


class SourceRevisionTests(unittest.TestCase):
    def fixture(self):
        out = BytesIO()
        xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Điều 16. FIXTURE</w:t></w:r></w:p><w:p><w:r><w:t>2. FIXTURE</w:t></w:r></w:p><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>đ) FIX</w:t></w:r><w:r><w:t>TURE ngán hàng;</w:t></w:r></w:p><w:p><w:r><w:t>đ) KEEP</w:t></w:r></w:p><w:p/></w:body></w:document>'
        with ZipFile(out, 'w') as z:
            z.writestr('word/document.xml', xml)
            z.writestr('word/styles.xml', b'unchanged')
        return out.getvalue()

    def spec(self, raw):
        return dict(raw_sha256=sha(raw), evidence_image_ref='proof.png', evidence_image_sha256=sha(b'FIXTURE'),
                    article=16, clause=2, current_text_original='đ) FIXTURE ngán hàng;',
                    proposed_change_from='ngán hàng', proposed_change_to='ngân hàng',
                    official_text_original='đ) FIXTURE ngân hàng;')

    def test_finite_correction_keeps_runs_neighbors_members_and_replays(self):
        raw = self.fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'proof.png').write_bytes(b'FIXTURE')
            out, log = correct_package(raw, [self.spec(raw)], root)
            replay, _ = correct_package(raw, [self.spec(raw)], root)
        self.assertEqual(out, replay)
        self.assertEqual(structural_check(raw, out, log)['changed_paragraphs'], 1)
        with ZipFile(BytesIO(out)) as z:
            self.assertIn('đ) KEEP', z.read('word/document.xml').decode())

    def test_wrong_citation_or_hash_is_blocked(self):
        raw = self.fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'proof.png').write_bytes(b'FIXTURE')
            for field, value in [('article', 40), ('raw_sha256', '0' * 64), ('evidence_image_sha256', '0' * 64), ('current_text_original', 'not present')]:
                spec = self.spec(raw); spec[field] = value
                out, log = correct_package(raw, [spec], root)
                self.assertEqual(log[0]['status'], 'blocked')
                with ZipFile(BytesIO(raw)) as a, ZipFile(BytesIO(out)) as b:
                    self.assertEqual(a.read('word/document.xml'), b.read('word/document.xml'))

    def test_mismatch_does_not_stop_independent_correction(self):
        raw = self.fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'proof.png').write_bytes(b'FIXTURE')
            bad = self.spec(raw); bad['clause'] = 9
            out, log = correct_package(raw, [bad, self.spec(raw)], root)
        self.assertEqual([x['status'] for x in log], ['blocked', 'corrected_derivative_pending'])
        structural_check(raw, out, log)

    def test_split_text_replacement_preserves_markup(self):
        xml = b'<w:p><w:r><w:t>xx ab</w:t></w:r><w:r><w:t>cd yy</w:t></w:r></w:p>'
        out = replace_text(xml, 'abcd', 'XYZ')
        self.assertEqual(out, b'<w:p><w:r><w:t>xx XYZ</w:t></w:r><w:r><w:t> yy</w:t></w:r></w:p>')

    def test_unlogged_content_change_rejected(self):
        with self.assertRaises(ValueError):
            structural_check(self.fixture(), self.fixture(), [{'status': 'corrected_derivative_pending', 'actual_xml_locator': '/w:p[3]', 'before': 'x', 'after': 'y'}])


if __name__ == '__main__':
    unittest.main()
