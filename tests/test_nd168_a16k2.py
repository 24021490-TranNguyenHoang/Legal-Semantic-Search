"""SYNTHETIC HTML/preview fixtures. No fixture becomes a legal source or corpus."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lxml import html
from src import nd168_a16k2 as task, chunk_preview_v2
from src.source_contracts import digest, canonical
from src.chunk_preview import chunk_identity
from tests.test_stage6_points import fixture_encoder


FIXTURE = '''<html><head><meta charset="utf-8"></head><body><h1>FIXTURE ONLY — 168/2024/NĐ-CP</h1>
<div itemprop="articleBody"><h2>NGHỊ ĐỊNH<div>FIXTURE synthetic law</div></h2>
<h3>Chương I<div>FIXTURE</div></h3><h3>Chương II<div>FIXTURE chapter</div></h3>
<h4>Mục 1<div>FIXTURE</div></h4><h4>Mục 2<div>FIXTURE section</div></h4>
<h4>Điều 13. FIXTURE</h4><h4>Điều 14. FIXTURE</h4><h4>Điều 15. FIXTURE</h4>
<h4>Điều 16. FIXTURE người điều khiển xe</h4>
<p>1. FIXTURE unselected clause</p><p>a) FIXTURE not selected</p>
<p>2. Phạt tiền từ 1.000.000 đồng đến 2.000.000 đồng (FIXTURE):</p>
<p>a) FIXTURE Không mất 0,25 mg/l;</p><span></span>
<p>b) FIXTURE Giữ phủ định và dấu;</p><p>c) FIXTURE Giữ toàn bộ nội dung;</p>
<p>d) FIXTURE Giữ ký hiệu d; </p><p>đ) FIXTURE Giữ ký hiệu đ.</p>
<p>3. FIXTURE unselected next clause</p><h4>Điều 17. FIXTURE</h4>
<iframe src="https://example.invalid/fixture-ad"></iframe></div></body></html>'''


class ScopedHtmlTests(unittest.TestCase):
    def extract(self, fixture=FIXTURE, file_id="FIXTURE-file"):
        with patch.object(task, "LAW", "FIXTURE/168-A16K2"):
            text, trace, e = task.extract_html(fixture.encode(), file_id)
            units, spans = task.map_units(text, trace)
            task.check_projection(units, spans, e, text, trace)
        return text, trace, e, units, spans

    def test_complete_points_sparse_source_ordinals_and_roundtrip(self):
        text, trace, e, units, spans = self.extract()
        self.assertEqual([u["designation"] for u in units if u["unit_type"] == "point"], list("abcdđ"))
        self.assertNotIn("unselected clause", text)
        self.assertEqual([u["ordinal"] for u in units[:5]], [0, 1, 1, 3, 1])
        self.assertEqual(len(spans), 10)
        self.assertEqual(e["method"], "html_text")
        self.assertTrue(all('"format":"html"' in s["locator_json"] for s in spans))

    def test_missing_duplicate_or_wrong_points_fail_instead_of_guess(self):
        for raw in [FIXTURE.replace('<p>d) FIXTURE Giữ ký hiệu d; </p>', ''),
                    FIXTURE.replace('d) FIXTURE Giữ ký hiệu d;', 'đ) FIXTURE Giữ ký hiệu d;'),
                    FIXTURE.replace('đ) FIXTURE Giữ ký hiệu đ.', 'e) FIXTURE Giữ ký hiệu đ.')]:
            with self.assertRaises(ValueError):
                self.extract(raw)

    def test_selected_unsupported_image_fails_unselected_ad_does_not(self):
        self.extract()
        with self.assertRaises(ValueError):
            self.extract(FIXTURE.replace('a) FIXTURE Không', 'a) <img src="fixture.png">FIXTURE Không'))

    def test_dom_entities_breaks_no_legal_rewriting(self):
        e = html.fromstring('<div>Không&nbsp;được<div>0,25 mg/l<br>1.000.000 đồng</div></div>')
        self.assertEqual(task.dom_text(e), 'Không\xa0được\n0,25 mg/l\n1.000.000 đồng')

    def test_new_source_id_changes_extraction_but_not_unit_identity(self):
        a = self.extract(file_id="FIXTURE-source-A"); b = self.extract(file_id="FIXTURE-source-B")
        self.assertNotEqual(a[2]["extraction_id"], b[2]["extraction_id"])
        self.assertEqual(a[3], b[3])
        self.assertNotEqual(a[4], b[4])

    def test_bad_span_parent_or_missing_point_rejected(self):
        text, trace, e, units, spans = self.extract()
        altered = copy.deepcopy(spans); altered[-1]["char_end"] += 1
        with self.assertRaises(ValueError):
            task.check_projection(units, altered, e, text, trace)
        altered = copy.deepcopy(units); altered[-1]["parent_unit_id"] = "u_" + "0"*64
        with self.assertRaises(ValueError):
            task.check_projection(altered, spans, e, text, trace)

    def test_preview_uses_article_and_clause_context_without_siblings(self):
        text, trace, e, units, spans = self.extract()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root/'normalized.txt').write_text(text, encoding='utf8', newline='\n')
            (root/'source.html').write_bytes(FIXTURE.encode())
            data = {"units": units, "spans": spans, "extractions": [{**e, "text_ref": "normalized.txt"}],
                    "files": [{"file_id": e['file_id'], "law_id": units[0]['law_id'], "raw_file_ref": "source.html",
                               "sha256": digest(FIXTURE.encode()), "size_bytes": len(FIXTURE.encode())}],
                    "issues": [], "document": {"law_id": units[0]['law_id'], "law_title": "FIXTURE law", "source_id": "FIXTURE", "source_url": "https://example.invalid/fixture"}}
            cfg = {"chunk_policy_version": chunk_preview_v2.VERSION, "snapshot_date": "2025-01-01", "token_limit": 256,
                   "required_context_fields": ["title"], "required_clause_context_fields": ["text_original"],
                   "target_unit_ids": [u['unit_id'] for u in units if u['unit_type']=='point']}
            before = copy.deepcopy(data)
            r = chunk_preview_v2.build_chunks(data, root, cfg, ['FIXTURE_PENDING'], fixture_encoder)
            self.assertEqual(len(r['chunks']), 5)
            for c in r['chunks']:
                self.assertEqual(c['context_text'], units[3]['title']+'\n'+units[4]['text_original'])
                ctx = [x for x in r['contexts'] if x['chunk_id']==c['chunk_id']]
                self.assertEqual(c['chunk_id'], 'c_'+digest(canonical(chunk_identity(c,ctx)).encode()))
            self.assertEqual(data, before)
            def long_encoder(texts):
                return [{**x, 'tokens_with_special': 257} for x in fixture_encoder(texts)]
            q = chunk_preview_v2.build_chunks(data, root, cfg, ['FIXTURE_PENDING'], long_encoder)
            self.assertEqual(len(q['quarantined']), 5)
            self.assertFalse(q['chunks'])
            data['issues'] = [{'law_id':units[0]['law_id'], 'affected_unit_ids':cfg['target_unit_ids'], 'code':'FIXTURE_UNCERTAIN'}]
            self.assertFalse(chunk_preview_v2.build_chunks(data,root,cfg,['FIXTURE_PENDING'],fixture_encoder)['chunks'])


if __name__ == "__main__":
    unittest.main()
