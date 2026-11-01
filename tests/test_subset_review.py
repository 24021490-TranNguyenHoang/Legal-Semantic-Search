"""Synthetic evidence/binding and path-order checks, not legal/retrieval metrics."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src import subset_review as r


class SubsetReviewTests(unittest.TestCase):
    def setUp(self):
        self.detail = {'dataset_response': {'record': {'text_original': 'SYNTHETIC đ 60 < V ≤ 80'},
            'required_read': {'unit_reads': [{'unit_id': 'FIXTURE-unit', 'unit': {'text_original': 'Synthetic condition'}}]}}}

    def test_unicode_field_quote_roundtrip(self):
        q = r.quote(self.detail, '/dataset_response/record/text_original')
        r.validate_quote(self.detail, q)
        self.assertEqual(q['char_end'], len('SYNTHETIC đ 60 < V ≤ 80'))

    def test_quote_source_offset_hash_binding_rejected(self):
        q = r.quote(self.detail, '/dataset_response/record/text_original')
        for changes in [{'char_start': 1}, {'char_end': 1000}, {'quote': 'WRONG'},
                        {'quote_sha256': '0'*64}, {'offset_space': 'pdf_page_offset'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                r.validate_quote(self.detail, {**q, **changes})

    def test_missing_or_non_text_pointer_rejected(self):
        for path in ['/dataset_response/record/MISSING', '/dataset_response/required_read']:
            with self.subTest(path=path), self.assertRaises((ValueError, KeyError)):
                r.quote(self.detail, path)

    def test_dependency_only_cannot_cite_own_text(self):
        a = {'relation': 'dependency_only', 'evidence_locators': [{'field_pointer': '/dataset_response/record/text_original'}]}
        with self.assertRaises(ValueError): r.validate_focus_roles(a, self.detail)
        a['evidence_locators'][0]['field_pointer'] = '/dataset_response/required_read/unit_reads/0/unit/text_original'
        r.validate_focus_roles(a, self.detail)

    def test_embedded_table_dependency_requires_real_owner(self):
        self.detail['dataset_response']['record']['source_record'] = {'explicit_dependency_unit_id': 'WRONG'}
        a = {'relation': 'dependency_only', 'evidence_locators': [{'field_pointer': '/dataset_response/record/source_record/text_derived'}]}
        with self.assertRaises(ValueError): r.validate_focus_roles(a, self.detail)
        self.detail['dataset_response']['record']['source_record']['explicit_dependency_unit_id'] = 'FIXTURE-unit'
        r.validate_focus_roles(a, self.detail)

    def test_windows_posix_order_differs_with_same_file_set(self):
        values = [{'path': 'config/a.json'}, {'path': 'QUICKSTART.md'}]
        result = r.portability(values)
        self.assertTrue(result['same_file_set'])
        self.assertFalse(result['same_order'])
        self.assertNotEqual(result['windows_inventory_sha256'], result['posix_inventory_sha256'])

    def test_new_review_inventory_has_canonical_posix_order(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); (root/'config').mkdir(); (root/'config/a').write_bytes(b'FIXTURE'); (root/'QUICKSTART.md').write_bytes(b'FIXTURE')
            self.assertEqual([x['path'] for x in r.inventory(root)], ['QUICKSTART.md', 'config/a'])

    def test_template_blank_and_no_inferred_human_acceptance(self):
        binding = {'dataset_version': 'FIXTURE-only'}
        pairs = {('fixture-q', 'fixture-r'): {'status': 'proposed', 'relevance': 2}}
        cross = [{'calibration_id': 'FIXTURE-cal', 'query_id': 'fixture-q', 'record_id': 'fixture-r',
                  'query_sha256': 'fixture-q-hash', 'record_sha256': 'fixture-r-hash'}]
        template = r.blank_template(binding, cross, pairs)
        r.validate_template(template, cross, pairs, binding)
        for changes in [{'reviewer_ref': 'invented'}, {'reviewed_at': '2026-10-31T00:00:00Z'}, {'all_labels_approved': True}, {'items': []}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                r.validate_template({**template, **changes}, cross, pairs, binding)
        bad = copy.deepcopy(template); bad['items'][0]['relevance'] = 2
        with self.assertRaises(ValueError): r.validate_template(bad, cross, pairs, binding)


if __name__ == '__main__': unittest.main()
