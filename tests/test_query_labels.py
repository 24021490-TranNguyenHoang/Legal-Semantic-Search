"""Feedback/typed acceptance checks; synthetic tests do not establish legal quality."""
import copy
import json
import os
from pathlib import Path
import shutil
import unittest

from src import query_labels as a


class FeedbackTests(unittest.TestCase):
    def source(self):
        return 'Query FIXTURE-only:\n- 35 nhãn 0:\n  unrelated / none.\n' + '\n'.join(
            f'PAIR-{n:012x} | 0 | SYNTHETIC reason {n}' for n in range(39))

    def test_explicit_feedback_and_reason_preserved(self):
        rows = a.capture_items(self.source())
        self.assertEqual(len(rows), 39)
        self.assertEqual(rows[3]['reason'], 'SYNTHETIC reason 3')
        self.assertTrue(all(x['relation'] == 'unrelated' for x in rows))

    def test_missing_pair_rejected_not_defaulted(self):
        with self.assertRaises(ValueError):
            a.capture_items(self.source().rsplit('\n', 1)[0])

    def test_duplicate_pair_rejected(self):
        with self.assertRaises(ValueError):
            a.capture_items(self.source().replace('PAIR-000000000001', 'PAIR-000000000000'))

    def test_null_is_not_zero(self):
        with self.assertRaises(ValueError):
            a.capture_items(self.source().replace(' | 0 | ', ' | null | ', 1))

    def test_positive_needs_explicit_relation(self):
        with self.assertRaises(KeyError):
            a.capture_items(self.source().replace(' | 0 | ', ' | 1 | ', 1))

    def test_canonical_comparison_rejects_bool_and_float(self):
        for value in (False, 0.0, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                a.same({'relevance': value}, {'relevance': 0}, 'wrong numeric type')

    def test_prior_conflict_not_implicit_supersedes(self):
        old = [{'query_id': 'FIXTURE-q', 'record_id': 'FIXTURE-r', 'relevance': None}]
        with self.assertRaises(ValueError):
            a.labels.reject_overlap([{**old[0], 'relevance': 0}], old)


@unittest.skipUnless(os.environ.get('VTLS_QUERY_LABELS_REAL') == '1', 'opt-in pinned real artifacts')
class RealAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = Path('staging/subset-v5-query-review-002/manifest.json').resolve()
        cls.prior = Path('staging/subset-v5-accepted-labels-002/manifest.json').resolve()
        cls.submission = Path(os.environ['VTLS_QUERY_SUBMISSION']).resolve()
        cls.accepted = Path(os.environ['VTLS_QUERY_ACCEPTED']).resolve()
        cls.output = a.staging_path(os.environ['VTLS_QUERY_CHECKS'])
        cls.output.mkdir(parents=True)
        cls.ctx = a.context(cls.review, cls.prior)
        cls.report, cls.files, _ = a.validate_submission(cls.submission, cls.ctx)

    def test_01_typed_new_batch_and_prior_preserved(self):
        result = a.validate(self.accepted, self.ctx)
        self.assertEqual(result['accepted'], 39)
        self.assertEqual(result['labels'], {'0': 35, '1': 4})
        self.assertEqual(result['relations'], {'unrelated': 35, 'supporting_target': 2, 'dependency_only': 2})
        rows = a.r.rows(self.accepted.parent / 'accepted.annotations.jsonl')
        self.assertTrue(all(x['reviewed_at'] == '2026-11-05T09:07:00+07:00' for x in rows))
        self.assertTrue(all(x['user_opened_detail_files'] is None and x['bundle_b_consulted'] is None for x in rows))
        self.assertEqual({x['record_type'] for x in rows}, a.labels.TYPES)
        self.assertEqual(len(a.r.rows(self.prior.parent / 'accepted.annotations.jsonl')), 20)
        self.assertTrue(all(x['relevance'] is None for x in a.r.rows(self.prior.parent / 'pending.annotations.jsonl')))

    def test_02_resealed_submission_mutations_rejected(self):
        cases = {
            'wrong_binding': lambda s: s['binding'].update(dataset_version='WRONG'),
            'wrong_type': lambda s: s['items'][0].update(record_type='source-retrieval.v1'),
            'wrong_record_hash': lambda s: s['items'][0].update(record_sha256='0'*64),
            'missing_pair': lambda s: s['items'].pop(),
            'duplicate_pair': lambda s: s['items'].append(copy.deepcopy(s['items'][0])),
            'altered_relevance': lambda s: s['items'][0].update(relevance=1),
            'altered_reason': lambda s: s['items'][0].update(reason='changed'),
            'fake_provenance': lambda s: s['provenance'].update(independent=True),
            'fake_opened_files': lambda s: s['provenance'].update(user_opened_detail_files=True),
            'missing_evidence': lambda s: s['items'][0].update(evidence_refs_used=[]),
            'boolean_zero': lambda s: s['items'][0].update(relevance=False),
            'null_decision': lambda s: s['items'][0].update(relevance=None),
            'wrong_time': lambda s: s.update(reviewed_at='2026-11-05T09:08:00+07:00'),
            'coverage_claim': lambda s: s.update(coverage_decision='approved'),
        }
        rejected = []
        for name, mutate in cases.items():
            with self.subTest(case=name):
                private = self.output / 'private' / name
                shutil.copytree(self.submission.parent, private)
                response = a.r.load(private / 'submission.json'); mutate(response)
                a.r.write_json(private / 'submission.json', response)
                m = a.r.load(private / 'manifest.json'); m.pop('files'); a.r.seal(private, m)
                with self.assertRaises(ValueError):
                    a.validate_submission(private / 'manifest.json', self.ctx)
                rejected.append({'case': name, 'rejected_after_reseal': True})
        # Native field offsets/quotes must also match, even with a valid outer seal.
        for name, ref, mutate in [
            ('wrong_quote', 'evidence.used.jsonl', lambda x: x[0]['evidence_locators'][0].update(quote='WRONG')),
            ('wrong_cells', 'evidence.used.jsonl', lambda x: x[0].update(cell_ids=['WRONG'])),
            ('fake_capture_label', 'feedback.received.json', lambda x: x['items'][0].update(relevance=1)),
            ('fake_bundle_history', 'feedback.received.json', lambda x: x.update(bundle_b_consulted=True))]:
            private = self.output / 'private' / name; shutil.copytree(self.submission.parent, private)
            data = (a.r.rows if ref.endswith('jsonl') else a.r.load)(private / ref); mutate(data)
            (a.r.write_rows if ref.endswith('jsonl') else a.r.write_json)(private / ref, data)
            m = a.r.load(private / 'manifest.json'); m.pop('files'); a.r.seal(private, m)
            with self.assertRaises(ValueError): a.validate_submission(private / 'manifest.json', self.ctx)
            rejected.append({'case': name, 'rejected_after_reseal': True})
        a.r.write_rows(self.output / 'negative_checks.jsonl', rejected)

    def test_03_idempotence_and_replay(self):
        before = a.r.inventory(self.accepted.parent)
        result = a.admit(self.submission, self.prior, self.accepted.parent, self.ctx)
        self.assertEqual(result['newly_imported'], 0)
        self.assertEqual(before, a.r.inventory(self.accepted.parent))
        replay = self.output / 'accepted-replay'
        repeated = a.admit(self.submission, self.prior, replay, self.ctx)
        self.assertEqual(repeated['import_id'], result['import_id'])
        for ref in ('accepted.annotations.jsonl', 'pending.annotations.jsonl', 'qrels.accepted.jsonl'):
            self.assertEqual((replay / ref).read_bytes(), (self.accepted.parent / ref).read_bytes())

    def test_05_resealed_accepted_payload_rejected(self):
        cases = {
            'accepted_type': lambda rows: rows[0].update(record_type='source-retrieval.v1'),
            'accepted_binding': lambda rows: rows[0]['binding'].update(index_version='WRONG'),
            'accepted_missing': lambda rows: rows.pop(),
            'accepted_duplicate': lambda rows: rows.append(copy.deepcopy(rows[0])),
            'accepted_relation': lambda rows: next(x for x in rows if x['relation'] == 'dependency_only').update(relation='direct_target'),
            'accepted_evidence': lambda rows: rows[0].update(evidence_locators=[]),
            'accepted_null': lambda rows: rows[0].update(relevance=None),
        }
        rejected = []
        for name, mutate in cases.items():
            private = self.output / 'private' / name; shutil.copytree(self.accepted.parent, private)
            rows = a.r.rows(private / 'accepted.annotations.jsonl'); mutate(rows)
            a.r.write_rows(private / 'accepted.annotations.jsonl', rows)
            m = a.r.load(private / 'manifest.json'); m.pop('files'); a.r.seal(private, m)
            with self.assertRaises(ValueError): a.validate(private / 'manifest.json', self.ctx)
            rejected.append({'case': name, 'rejected_after_reseal': True})
        a.r.write_rows(self.output / 'accepted_negative_checks.jsonl', rejected)

    def test_06_wrong_prior_rejected_before_output(self):
        output = self.output / 'must-not-exist'
        with self.assertRaises(ValueError):
            a.admit(self.submission, self.review, output, self.ctx)
        self.assertFalse(output.exists())

    def test_04_aggregate_counts_and_replay_rejected(self):
        result = a.aggregate_payload(self.review, [self.prior, self.accepted], self.ctx)
        summary = result['summary.json']
        self.assertEqual((summary['accepted'], summary['pending'], summary['pool_accepted']), (59, 2, 53))
        self.assertEqual(summary['labels'], {'2': 7, '1': 10, '0': 42})
        self.assertTrue(all(p['awaiting_review'] == 0 for p in result['progress.jsonl']))
        with self.assertRaisesRegex(ValueError, 'Duplicate/replayed'):
            a.aggregate_payload(self.review, [self.prior, self.accepted, self.accepted], self.ctx)
        a.r.write_json(self.output / 'validation_report.json', summary)


if __name__ == '__main__':
    unittest.main()
