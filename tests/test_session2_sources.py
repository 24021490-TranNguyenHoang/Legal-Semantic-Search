"""Synthetic fixtures only; checks technical contracts, not real legal quality."""
import copy
from pathlib import Path
import tempfile
import unittest

from src.experimental_dataset import write_json, write_rows, rows
from src.ingestion.tt35_owner_tables import merged_grid, check_record, read_record, validate_encoder_partition
from src.nd168_field_review import display_fold, project_html
from src.qcvn_region_recovery import select_lines
from src.ingestion import legal_tree
from src.source_contracts import canonical, digest


class TableOwnerTests(unittest.TestCase):
    def test_missing_encoder_disposition_or_full_input_refused(self):
        r = {'record_id': 'FIXTURE-record', 'text_for_search': 'fixture'}
        e = {'input_sha256': digest(b'fixture'), 'truncation': False}
        with self.assertRaisesRegex(ValueError, 'disposition'):
            validate_encoder_partition([r], [], [], [e])
        with self.assertRaisesRegex(ValueError, 'full encoder'):
            validate_encoder_partition([r], [], [], [])

    def fixture(self):
        table = {'table_id': 'FIXTURE-T', 'columns': 2, 'rows': 2, 'cell_slots': [['h', None], ['a', 'b']]}
        cells = [{'table_id': 'FIXTURE-T', 'cell_id': i, 'bbox': box} for i, box in [('h', [0, 0, 2, 1]), ('a', [0, 1, 1, 2]), ('b', [1, 1, 2, 2])]]
        return table, cells

    def test_merged_header_keeps_one_physical_cell(self):
        table, cells = self.fixture()
        self.assertEqual(merged_grid(table, cells), [['h', 'h'], ['a', 'b']])
        self.assertEqual(table['cell_slots'][0][1], None)
        self.assertEqual(len(cells), 3)

    def test_missing_cell_or_ambiguous_geometry_refused(self):
        t, c = self.fixture()
        with self.assertRaises(ValueError): merged_grid(t, c[:-1])
        c[2]['bbox'] = [0, 1, 2, 2]
        with self.assertRaises(ValueError): merged_grid(t, c)

    def checked_fixture(self):
        proof = {'extraction_id': 'e_fixture', 'file_id': 'f_fixture', 'char_start': 0, 'char_end': 2,
                 'quote': '10', 'quote_sha256': digest(b'10'), 'offset_space': 'normalized_extraction_unicode_codepoints',
                 'locator': {'page_start': 1}}
        r = {'owner_unit_id': 'FIXTURE-owner', 'owner_path': 'FIXTURE/article:1/clause:1',
             'required_dependencies': [{'kind': 'unit_subtree', 'required': True, 'units': ['FIXTURE-dep']}],
             'bindings': [{'cell_id': 'fixture-cell', 'header_cell_ids': ['fixture-header']}],
             'cells': [{'file_id': 'f_fixture', 'source_raw_sha256': 'fixture_hash', 'page': 1, 'text': '10', 'source_slices': [proof]}]}
        return r, {'e_fixture': '10'}, {'e_fixture': {1: {'char_start': 0, 'char_end': 2}}}, {'f_fixture': {'sha256': 'fixture_hash'}}

    def test_owner_header_cell_dependency_and_proof_fail_closed(self):
        expected, texts, pages, files = self.checked_fixture()
        check_record(expected, expected, texts, pages, files)
        for kind in ['owner', 'header', 'cell', 'dependency', 'proof', 'page', 'source']:
            r = copy.deepcopy(expected)
            if kind == 'owner': r['owner_unit_id'] = 'OTHER-owner'
            if kind == 'header': r['bindings'][0]['header_cell_ids'] = []
            if kind == 'cell': r['cells'] = []
            if kind == 'dependency': r['required_dependencies'] = []
            if kind == 'proof': r['cells'][0]['source_slices'][0]['quote_sha256'] = '0' * 64
            if kind == 'page': r['cells'][0]['source_slices'][0]['locator']['page_start'] = 2
            if kind == 'source': r['cells'][0]['source_raw_sha256'] = 'other'
            with self.subTest(kind=kind), self.assertRaises(ValueError): check_record(r, expected, texts, pages, files)

    def test_consumer_returns_required_units_not_only_projection(self):
        r, _, _, _ = self.checked_fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ['regions', 'tables', 'cells']: write_rows(root / (name + '.jsonl'), [])
            read = read_record(r, root)
        self.assertEqual(read['loaded_required_dependencies'][0]['units'], ['FIXTURE-dep'])
        self.assertEqual(read['cells'], r['cells'])


class FieldReviewTests(unittest.TestCase):
    def test_display_fold_does_not_hide_word_number_negation_or_punctuation_changes(self):
        self.assertEqual(display_fold('“hóa”'), display_fold('"hoá"'))
        for a, b in [('đã thu phí', 'để thu phí'), ('không', 'có'), ('13', '15'), ('hè,', 'hè.')]:
            self.assertNotEqual(display_fold(a), display_fold(b))

    def test_related_widget_projection_keeps_source_and_legal_text(self):
        with tempfile.TemporaryDirectory() as td:
            old, out = Path(td) / 'old', Path(td) / 'out'; old.mkdir(); out.mkdir()
            body = 'FIXTURE: Nghị định này./.'; widget = 'Tham khảo thêm FIXTURE not law'
            text = body + '\n' + widget
            u = {'law_id': 'FIXTURE/ND', 'parent_unit_id': None, 'unit_type': 'article', 'designation': '55', 'canonical_path': 'document:FIXTURE/ND/article:55',
                 'citation_path': 'FIXTURE/ND > Điều55', 'ordinal': 0, 'title': '', 'text_original': text, 'text_sha256': digest(text.encode())}
            u['unit_id'] = legal_tree.unit_id(u)
            spans = []
            for i, (a, b) in enumerate([(0, len(body)), (len(body) + 1, len(text))]):
                s = {'unit_id': u['unit_id'], 'field_name': 'text_original', 'span_order': i, 'char_start': a, 'char_end': b,
                     'extraction_id': 'e_fixture', 'locator_json': canonical({'format': 'html', 'xpath': f'/fixture/p[{i+1}]'}), 'quote_sha256': digest(text[a:b].encode())}
                s['span_id'] = legal_tree.span_id(s); spans.append(s)
            write_rows(old / 'legal_units.pending.jsonl', [u]); write_rows(old / 'source_spans.pending.jsonl', spans)
            write_json(old / 'extraction.json', {'extraction_id': 'e_fixture', 'text_ref': 'normalized.txt'})
            (old / 'normalized.txt').write_bytes(text.encode())
            project_html(old, out)
            self.assertEqual(rows(out / 'legal_units.pending.jsonl')[0]['text_original'], body)
            self.assertEqual((old / 'normalized.txt').read_bytes(), text.encode())
            self.assertEqual(len(rows(out / 'non_body.related_links.jsonl')), 1)


class QcvnRegionTests(unittest.TestCase):
    def test_bounded_region_does_not_take_next_sign(self):
        rr = [{'region_id': f'fixture{i}', 'content': s, 'source_proof': {'file_id': 'f', 'locator': {'page_start': 1}, 'char_start': i}}
              for i, s in enumerate(['cover', 'B.18 fixture', 'same source text', 'B.19 next sign'])]
        selected = select_lines(rr, 'f', 1, 'B.18', 'B.19')
        self.assertEqual([r['content'] for r in selected], ['B.18 fixture', 'same source text'])
        with self.assertRaises(ValueError): select_lines(rr, 'f', 1, 'missing', 'B.19')


if __name__ == '__main__': unittest.main()
