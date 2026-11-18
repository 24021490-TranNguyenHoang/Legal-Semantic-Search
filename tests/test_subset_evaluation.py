"""Independent hand calculations and opt-in checks of the pinned diagnostic."""
import copy
import math
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from src import subset_evaluation as e


class DiagnosticMathTests(unittest.TestCase):
    def test_two_thresholds_many_positives_and_short_precision(self):
        m = e.metric_values({'a': 2, 'b': 1, 'c': 2, 'd': 0}, ['d', 'b', 'a'])
        direct, useful = [m['readings'][name]['values'] for name in ('Direct', 'Useful')]
        self.assertEqual(direct['Precision@1'], 0)
        self.assertAlmostEqual(direct['Precision@3'], 1/3)
        self.assertEqual(direct['Precision@5'], .2)
        self.assertEqual(direct['Precision@10'], .1)
        self.assertAlmostEqual(useful['Precision@3'], 2/3)
        self.assertEqual(useful['Precision@10'], .2)
        self.assertAlmostEqual(direct['RR@10'], 1/3)
        self.assertEqual(useful['RR@10'], .5)
        expected_idcg = 3 + 3/math.log2(3) + 1/2
        self.assertAlmostEqual(m['IDCG@10_pool'], expected_idcg)
        self.assertAlmostEqual(m['nDCG@10_pool'], (1/math.log2(3) + 3/2)/expected_idcg)
        self.assertEqual(m['readings']['Direct']['counts']['10'],
                         {'positive_hits': 1, 'precision_denominator': 10, 'returned': 3})

    def test_rank10_counts_rank11_does_not(self):
        ids = [str(n) for n in range(1, 12)]
        m = e.metric_values({rid: (2 if rid in {'10', '11'} else 0) for rid in ids}, ids)
        self.assertEqual(m['readings']['Direct']['positive_ranks_top10'], [10])
        self.assertEqual(m['readings']['Direct']['values']['RR@10'], .1)
        self.assertEqual(m['readings']['Useful']['values']['Hit@5'], 0)
        self.assertEqual(m['readings']['Useful']['values']['Hit@10'], 1)

    def test_only_positive_rank11_zero_rr_and_ndcg(self):
        ids = [str(n) for n in range(11)]
        m = e.metric_values({rid: int(rid == '10') for rid in ids}, ids)
        self.assertEqual(m['readings']['Useful']['values']['RR@10'], 0)
        self.assertEqual(m['nDCG@10_pool'], 0)

    def test_no_positive_pool_is_retained_idcg_null(self):
        m = e.metric_values({'x': 0}, ['x'])
        self.assertIsNone(m['nDCG@10_pool'])
        self.assertEqual(m['IDCG@10_pool'], 0)
        self.assertTrue(all(v == 0 for v in m['readings']['Direct']['values'].values()))

    def test_dependency_positive_not_direct(self):
        m = e.metric_values({'support': 1}, ['support'])
        self.assertEqual(m['readings']['Direct']['values']['Hit@1'], 0)
        self.assertEqual(m['readings']['Useful']['values']['Hit@1'], 1)

    def test_empty_results_no_padding(self):
        m = e.metric_values({'a': 2}, [])
        self.assertEqual(m['readings']['Direct']['values']['Precision@10'], 0)
        self.assertEqual(m['readings']['Direct']['counts']['10']['returned'], 0)
        self.assertEqual(m['nDCG@10_pool'], 0)

    def test_unjudged_duplicate_and_bad_numeric_rejected(self):
        for judgments, ranking in [({'a': 2}, ['b']), ({'a': 2}, ['a', 'a']),
                                    ({'a': False}, ['a']), ({'a': 0.0}, ['a']), ({'a': None}, ['a'])]:
            with self.subTest(judgments=judgments, ranking=ranking), self.assertRaises(ValueError):
                e.metric_values(judgments, ranking)

    def test_macro_exactly_five_including_zero_and_idcg_null(self):
        rows = [dict(query_id='FIXTURE-'+str(i), **e.metric_values({'a': 2 if i == 0 else 0}, ['a']))
                for i in range(5)]
        summary, contributions = e.summarize(rows)
        self.assertEqual(summary['queries_total'], 5)
        self.assertEqual(summary['readings']['Direct']['MRR@10'], .2)
        self.assertEqual(summary['readings']['Useful']['Hit@1'], .2)
        self.assertEqual(summary['ndcg_pool_valid_queries'], 1)
        self.assertEqual(summary['ndcg_pool_null_queries'], 4)
        self.assertEqual(summary['nDCG_at_10_pool'], 1)
        self.assertEqual(len(contributions), 10)
        self.assertIsNone(summary['corpus_recall'])
        self.assertIsNone(summary['corpus_AP_MAP'])


class TypedInputTests(unittest.TestCase):
    def setUp(self):
        self.query = {'query_id': 'FIXTURE-q', 'intent_group_id': 'FIXTURE-g', 'query': 'SYNTHETIC ONLY',
                      'query_type': 'direct', 'topic': 'fixture', 'split': 'dev'}
        self.binding = {'dataset_version': 'FIXTURE-only', 'index_version': 'FIXTURE-only'}
        self.pool = []; self.annotations = []
        for i, kind in enumerate(['chunk.v1', 'table-retrieval.v1', 'source-retrieval.v1']):
            p = dict(query_id='FIXTURE-q', record_id='FIXTURE-'+str(i), record_type=kind,
                     query_sha256=e.r.bm.hashed(self.query), record_sha256='FIXTURE-record-'+str(i),
                     detail_sha256='FIXTURE-detail-'+str(i))
            self.pool.append(p)
            self.annotations.append({**p, 'status': 'accepted', 'relevance': i, 'binding': copy.deepcopy(self.binding)})

    def bind(self):
        return e.bind_judgments([self.query], self.pool, self.annotations, self.binding)

    def test_all_three_types_preserved_no_fake_chunk_ids(self):
        result = self.bind()
        self.assertEqual({x['record_type'] for x in result.values()}, e.labels.TYPES)
        self.assertTrue(all('chunk_id' not in x for x in result.values()))

    def test_missing_duplicate_and_proposal_rejected(self):
        original = copy.deepcopy(self.annotations)
        for operation in ('missing', 'duplicate', 'proposal', 'null'):
            self.annotations = copy.deepcopy(original)
            if operation == 'missing': self.annotations.pop()
            elif operation == 'duplicate': self.annotations.append(copy.deepcopy(self.annotations[0]))
            elif operation == 'proposal': self.annotations[0]['status'] = 'proposed'
            else: self.annotations[0]['relevance'] = None
            with self.subTest(operation=operation), self.assertRaises(ValueError): self.bind()

    def test_wrong_dataset_query_record_type_or_hash_rejected(self):
        original = copy.deepcopy(self.annotations)
        for field, value in [('query_id', 'WRONG'), ('query_sha256', 'WRONG'), ('record_sha256', 'WRONG'),
                             ('detail_sha256', 'WRONG'), ('record_type', 'source-retrieval.v1'),
                             ('binding', {'dataset_version': 'WRONG'})]:
            self.annotations = copy.deepcopy(original); self.annotations[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.bind()

    def test_duplicate_pool_not_silently_deduped(self):
        self.pool.append(copy.deepcopy(self.pool[0]))
        with self.assertRaises(ValueError): self.bind()

    def test_top10_keeps_physical_order_and_scores(self):
        # Synthetic ten ranked records, independent of real labels.
        accepted = {('FIXTURE-q', str(i)): {'record_type': 'chunk.v1'} for i in range(10)}
        run = [dict(query_id='FIXTURE-q', record_id=str(i), record_type='chunk.v1', rank=i+1, score=10-i,
                    **self.binding) for i in range(10)]
        self.assertEqual(e.validate_top10(run, ['FIXTURE-q'], accepted, self.binding), run)
        for mutated in [run[::-1], run[:-1], [{**run[0], 'score': float('nan')}, *run[1:]],
                        [{**run[0], 'record_id': 'WRONG'}, *run[1:]]]:
            with self.assertRaises(ValueError): e.validate_top10(mutated, ['FIXTURE-q'], accepted, self.binding)


@unittest.skipUnless(os.environ.get('VTLS_FIVE_QUERY_EVAL_MANIFEST'), 'opt-in pinned artifacts')
class RealDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = Path(os.environ['VTLS_FIVE_QUERY_EVAL_MANIFEST']).resolve()
        cls.output = e.staging_path(os.environ['VTLS_FIVE_QUERY_EVAL_CHECKS'])
        cls.output.mkdir(parents=True)
        cls.data = e.inputs(cls.manifest.parent / 'config.snapshot.json')
        cls.assembled = e.assemble(cls.manifest.parent / 'config.snapshot.json', cls.data)

    def test_actual_all_positions_pool_and_zero_query(self):
        with patch('src.subset_bm25.search_loaded', side_effect=AssertionError('ranking forbidden')):
            report = e.validate(self.manifest, self.assembled)
        self.assertEqual((report['accepted_aggregate'], report['pool_pairs'], report['top10_positions']), (59, 53, 50))
        self.assertEqual(report['queries_eligible'], 5)
        per_query = e.r.rows(self.manifest.parent / 'metrics.per_query.jsonl')
        red = next(p for p in per_query if p['query_id'] == 'dev-red_light-2')
        self.assertEqual(red['readings']['Direct']['pool_positives'], 0)
        self.assertEqual(red['readings']['Direct']['values']['RR@10'], 0)
        self.assertGreater(red['readings']['Useful']['values']['RR@10'], 0)
        self.assertEqual(len(e.r.rows(self.manifest.parent / 'outside_positives.jsonl')), 3)
        e.r.write_json(self.output / 'validation_report.json', report)

    def test_resealed_output_mutations_rejected(self):
        cases = [
            ('missing_top10', 'top10.accepted.jsonl', lambda x: x.pop()),
            ('duplicate_top10', 'top10.accepted.jsonl', lambda x: x.append(copy.deepcopy(x[0]))),
            ('wrong_rank', 'frozen.run.jsonl', lambda x: x[0].update(rank=10)),
            ('wrong_score', 'frozen.run.jsonl', lambda x: x[0].update(score=999)),
            ('wrong_query', 'queries.jsonl', lambda x: x[0].update(query='changed query')),
            ('wrong_type', 'accepted.selected.jsonl', lambda x: x[0].update(record_type='source-retrieval.v1')),
            ('proposal', 'accepted.selected.jsonl', lambda x: x[0].update(status='proposed')),
            ('wrong_binding', 'accepted.selected.jsonl', lambda x: x[0]['binding'].update(dataset_version='WRONG')),
            ('fake_metric', 'report.json', lambda x: x['readings']['Direct'].update(**{'MRR@10': 1})),
            ('fake_official_metric', 'report.json', lambda x: x.update(official_50_query_metrics={'MRR@10': 1})),
            ('fake_outside_rank', 'outside_positives.jsonl', lambda x: x[0].update(frozen_observed_rank=1)),
            ('missing_evidence', 'top10.accepted.jsonl', lambda x: x[0].update(evidence_locators=[]))]
        rejected = []
        for name, ref, mutate in cases:
            private = self.output / 'private' / name; shutil.copytree(self.manifest.parent, private)
            value = (e.r.rows if ref.endswith('.jsonl') else e.r.load)(private / ref); mutate(value)
            (e.r.write_rows if ref.endswith('.jsonl') else e.r.write_json)(private / ref, value)
            m = e.r.load(private / 'manifest.json'); m.pop('files'); e.r.seal(private, m)
            with self.assertRaises(ValueError): e.validate(private / 'manifest.json', self.assembled)
            rejected.append({'case': name, 'rejected_after_reseal': True})
        e.r.write_rows(self.output / 'negative_checks.jsonl', rejected)

    def test_bad_config_fails_before_output(self):
        cfg = e.r.load(self.manifest.parent / 'config.snapshot.json')
        cfg['inputs']['aggregate']['sha256'] = '0'*64
        source = self.output / 'bad-config.json'; e.r.write_json(source, cfg)
        target = self.output / 'must-not-exist'
        with self.assertRaises(ValueError): e.build(source, target)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
