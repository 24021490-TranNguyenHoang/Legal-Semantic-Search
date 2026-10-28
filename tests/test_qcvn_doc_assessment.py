"""Diagnostic reader contracts with synthetic data, no legal quality claim."""
import copy
import unittest

from src.ingestion.extraction_normalizer import normalize_fragment
from src.qcvn_doc_assessment import check_receipt, diagnostics, line_trace
from src.source_revision import sha


class DocAssessmentTests(unittest.TestCase):
    def test_offsets_preserve_errors_and_picture_placeholder(self):
        text = normalize_fragment('Điều 4.\r\n\0\ufffe[pic]\n')
        trace = line_trace(text, 'a' * 64)
        self.assertEqual(''.join(text[t['char_start']:t['char_end']] for t in trace), text)
        for t in trace:
            self.assertEqual(sha(text[t['char_start']:t['char_end']].encode()), t['quote_sha256'])
        d = diagnostics(text)
        self.assertEqual((d['nul'], d['ufffe'], d['picture_placeholders']), (1, 1, 1))
        self.assertTrue(all(t['native_doc_page_or_cell'] is None for t in trace))

    def test_official_anchor_part_hash_and_time_binding(self):
        data = bytes.fromhex('d0cf11e0a1b11ae1') + b'FIXTURE'
        url = 'https://g7.cdnchinhphu.vn/api/download/stream?FIXTURE'
        links = {'2024_1359 + 1360_51-2024-TT-BGTVT.doc': url}
        r = dict(url=url, final_url=url, sha256=sha(data), bytes=len(data), part_order=1,
                 started_at='2026-10-28T00:00:00Z', accessed_at='2026-10-28T00:00:01Z')
        check_receipt(data, r, 1, links)
        for field, value in [('sha256', '0' * 64), ('bytes', 1), ('part_order', 2),
                             ('url', 'https://example.com/fixture'), ('final_url', 'https://example.com/fixture'),
                             ('accessed_at', '2026-10-27T00:00:00Z')]:
            wrong = copy.deepcopy(r); wrong[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_receipt(data, wrong, 1, links)


if __name__ == '__main__':
    unittest.main()
