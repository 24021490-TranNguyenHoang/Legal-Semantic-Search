"""Synthetic evidence facets and opt-in real preview regressions, never legal acceptance."""
import copy
import os
from pathlib import Path
import shutil
import unittest

from src import distance_evidence as d, development_gap_preview as p


class SyntheticConsumer:
    """Explicit synthetic binding double; real proof checks run in artifact tests."""
    root = Path('.')
    class reader:
        @staticmethod
        def proof(root, value):
            if value.get('fixture_binding') != 'SYNTHETIC' or value.get('quote_sha256') != d.digest(value['quote'].encode()):
                raise ValueError('Wrong synthetic proof')
            return value['quote']

    def __init__(self):
        self.nodes = {uid: {'unit': {'text_original': text}} for uid, text in
                      [('FIXTURE-normal', 'SYNTHETIC normal condition'), ('FIXTURE-adverse', 'SYNTHETIC adverse condition')]}
        self.spans = [dict(unit_id=uid, field_name='text_original', span_order=0, quote=n['unit']['text_original'])
                      for uid, n in self.nodes.items()]
        self.cells = []
        for row, values in enumerate([list(d.HEADERS.values()), ['V = 60', '35'], ['60 < V ≤ 80', '55'], ['80 < V ≤ 100', '70']]):
            for col, text in enumerate(values):
                self.cells.append(dict(cell_id=f'FIXTURE-cell-{row}-{col}', extraction_id='FIXTURE-e', table_id='FIXTURE-table',
                                       row=row, column=col, text=text, source_slices=[dict(quote=text)]))
        self.rows = [dict(row=i, owner_unit_id='FIXTURE-normal', table_id='FIXTURE-table',
                         source_cell_ids=[f'FIXTURE-cell-{r}-{c}' for r in [0, i] for c in [0, 1]]) for i in [1, 2, 3]]

    def native(self, value):
        text = value['quote']
        return dict(quote=text, quote_sha256=d.digest(text.encode()), fixture_binding='SYNTHETIC')

    def read(self, rid):
        if rid == 'FIXTURE-embedded':
            record = {'source_record': dict(explicit_dependency_unit_id='FIXTURE-normal', unit_id='FIXTURE-adverse',
                        table_rows=self.rows, source_cells=self.cells)}
            return dict(record_type='source-retrieval.v1', record=record)
        row = self.rows[1 if rid == 'FIXTURE-80' else 2]
        record = dict(owner_unit_id='FIXTURE-normal', rows=[row],
                      cells=[c for c in self.cells if c['cell_id'] in row['source_cell_ids']])
        return dict(record_type='table-retrieval.v1', record=record)


class EvidenceRequirementTests(unittest.TestCase):
    def setUp(self):
        self.consumer = SyntheticConsumer()
        self.packets = d.packets(self.consumer, ['FIXTURE-80', 'FIXTURE-81', 'FIXTURE-embedded'])

    def test_both_rows_and_conditions_pass_without_legal_approval(self):
        result = d.check(self.consumer, self.packets)
        self.assertTrue(result['sufficient_for_declared_requirements'])
        self.assertEqual(result['values'][80]['distance_m'], 55)
        self.assertEqual(result['values'][81]['distance_m'], 70)
        self.assertEqual(result['comparison_normal_only']['difference_m'], 15)
        self.assertIsNone(result['adverse_fixed_distance'])
        self.assertFalse(result['legal_verified'])
        self.assertIsNone(result['human_review'])

    def test_embedded_bound_table_and_dependency_alone_pass(self):
        result = d.check(self.consumer, [self.packets[2]])
        self.assertTrue(result['sufficient_for_declared_requirements'])
        self.assertEqual(result['access_paths'], ['dependency:source_record/table_rows'])

    def test_only_80_or_81_is_not_complete(self):
        for index, absent in [(0, 'MISSING_SPEED_81'), (1, 'MISSING_SPEED_80')]:
            result = d.check(self.consumer, [self.packets[index]])
            self.assertFalse(result['sufficient_for_declared_requirements'])
            self.assertIn(absent, result['errors'])

    def test_missing_header_units_conditions_or_proof(self):
        for facet in ['header', 'units', 'normal_conditions', 'adverse_conditions', 'proof']:
            with self.subTest(facet=facet):
                packet = copy.deepcopy(self.packets[2])
                if facet == 'header': packet['cells'] = [c for c in packet['cells'] if c['cell']['row'] != 0]
                elif facet == 'units': packet['cells'][0]['cell']['text'] = 'speed without unit'
                elif facet in ['normal_conditions', 'adverse_conditions']: packet[facet] = None
                else: packet['cells'][0]['proofs'] = []
                self.assertFalse(d.check(self.consumer, [packet])['sufficient_for_declared_requirements'])

    def test_wrong_boundary_owner_source_and_value_fail(self):
        for facet in ['boundary', 'owner', 'source', 'value']:
            packet = copy.deepcopy(self.packets[2])
            if facet == 'boundary': packet['rows'][1]['row'] = 3
            elif facet == 'owner': packet['rows'][1]['owner_unit_id'] = 'WRONG'
            elif facet == 'source': packet['cells'][0]['proofs'][0]['fixture_binding'] = 'WRONG'
            else: packet['cells'][5]['cell']['text'] = '70'
            with self.subTest(facet=facet):
                self.assertFalse(d.check(self.consumer, [packet])['sufficient_for_declared_requirements'])

    def test_exact_boundary_wrong_valid_row_is_not_80_or_81(self):
        packet = copy.deepcopy(self.packets[2]); packet['rows'] = [packet['rows'][0]]  # V=60
        result = d.check(self.consumer, [packet])
        self.assertIn('MISSING_SPEED_80', result['errors'])
        self.assertIn('MISSING_SPEED_81', result['errors'])

    def test_omitted_normal_and_adverse_are_not_refilled(self):
        packet = copy.deepcopy(self.packets[2]); packet['normal_conditions'] = None; packet['adverse_conditions'] = None
        result = d.check(self.consumer, [packet])
        self.assertIn('MISSING_NORMAL_CONDITIONS', result['errors'])
        self.assertIn('MISSING_ADVERSE_CONDITIONS', result['errors'])

    def test_payload_hash_duplicate_and_type_fail(self):
        for name in ['payload_sha256', 'record_type']:
            packet = copy.deepcopy(self.packets[2]); packet[name] = 'WRONG'
            self.assertFalse(d.check(self.consumer, [packet])['sufficient_for_declared_requirements'])
        self.assertFalse(d.check(self.consumer, [self.packets[2], self.packets[2]])['sufficient_for_declared_requirements'])


@unittest.skipUnless(os.environ.get('VTLS_GAP_PREVIEW_MANIFEST'), 'opt-in pinned real preview')
class RealGapPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = Path(os.environ['VTLS_GAP_PREVIEW_MANIFEST']).resolve()
        cls.output = p.staging_path(os.environ['VTLS_GAP_PREVIEW_CHECKS']); cls.output.mkdir(parents=True)
        cls.loaded = p.inputs(cls.manifest.parent / 'config.snapshot.json')

    def test_real_native_roundtrip_and_scope(self):
        report = p.validate(self.manifest, self.loaded)
        self.assertEqual(report['red_target_preview'], 1)
        self.assertEqual(report['age_target_retained'], 1)
        red = p.rows(self.manifest.parent / 'red.reads.jsonl')[0]
        self.assertTrue(red['record']['citation_path'].endswith('Điều 6 > Khoản 9 > Điểm b'))
        self.assertIn('18.000.000', red['record']['context_text'])
        self.assertNotIn('Khoản 1 >', red['record']['citation_path'])
        expected = {p.find(self.loaded[-1]['nd'], suffix)['unit_id'] for suffix in self.loaded[0]['red_required']}
        self.assertTrue(expected <= {u['unit_id'] for u in red['dependency_units']})
        age = p.rows(self.manifest.parent / 'age.reads.jsonl')[0]
        old = self.loaded[3].frames[age['record_id']]
        self.assertEqual(age['record'], old['record'])
        self.assertEqual(age['contexts'], old['contexts'])
        self.assertTrue(any('/article:57/clause:1/point:c' in u['canonical_path'] for u in age['dependency_units']))
        self.assertTrue(any('/article:34/clause:1/point:g' in u['canonical_path'] for u in age['dependency_units']))
        self.assertEqual(report['sufficient_cases'], ['both_rows_with_conditions', 'embedded_table_complete'])
        p.write_json(self.output / 'validation_report.json', report)

    def test_resealed_source_content_and_closure_mutations_rejected(self):
        cases = [
            ('wrong_source', 'red.reads.jsonl', lambda x: x[0]['native_proofs'][0].update(raw_sha256='0'*64)),
            ('wrong_offsets', 'red.reads.jsonl', lambda x: x[0]['native_proofs'][0].update(char_start=0)),
            ('missing_lead', 'red.reads.jsonl', lambda x: x[0]['contexts'].pop()),
            ('missing_modifier', 'red.reads.jsonl', lambda x: x[0]['dependency_units'].pop()),
            ('missing_dependency', 'red.reads.jsonl', lambda x: x[0]['dependencies'].clear()),
            ('lost_target_content', 'red.reads.jsonl', lambda x: x[0]['record'].update(text_original='b)')),
            ('wrong_parent', 'red.reads.jsonl', lambda x: x[0]['record'].update(parent_unit_id='WRONG')),
            ('wrong_legacy_id', 'red.reads.jsonl', lambda x: x[0]['record'].update(chunk_id='c_OLD')),
            ('missing_classification', 'age.reads.jsonl', lambda x: x[0]['dependency_units'].clear()),
            ('fake_verified', 'report.json', lambda x: x.update(legal_verified=True)),
            ('fake_checker_pass', 'distance.evidence_cases.jsonl', lambda x: x[2]['result'].update(sufficient_for_declared_requirements=True))]
        rejected = []
        for name, ref, mutate in cases:
            private = self.output / 'private' / name; shutil.copytree(self.manifest.parent, private)
            value = (p.rows if ref.endswith('.jsonl') else p.load)(private / ref); mutate(value)
            (p.write_rows if ref.endswith('.jsonl') else p.write_json)(private / ref, value)
            m = p.load(private / 'manifest.json'); m.pop('files'); p.labels.r.seal(private, m)
            with self.assertRaises(ValueError): p.validate(private / 'manifest.json', self.loaded)
            rejected.append(dict(case=name, rejected_after_reseal=True))
        p.write_rows(self.output / 'negative_checks.jsonl', rejected)

    def test_wrong_pinned_source_rejected_before_output(self):
        cfg = p.load(self.manifest.parent / 'config.snapshot.json'); cfg['inputs']['nd_graph']['sha256'] = '0'*64
        path = self.output / 'wrong_source.config.json'; p.write_json(path, cfg); dest = self.output / 'must-not-exist'
        with self.assertRaises(ValueError): p.build(path, dest)
        self.assertFalse(dest.exists())


if __name__ == '__main__':
    unittest.main()
