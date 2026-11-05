"""Synthetic typed-label projections; no legal or retrieval quality claims."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import unittest

from src import subset_labels as labels


class TypedLabelsTests(unittest.TestCase):
    def setUp(self):
        self.submission = {'binding': {'dataset_version': 'FIXTURE-only'},
                           'reviewer_ref': '## FIXTURE-OPAQUE-REF',
                           'reviewed_at': '2020-01-01T01:00:00Z', 'items': []}
        self.proposals, self.evidence = {}, {}
        for n, (kind, rel, relation, complete) in enumerate([
                ('chunk.v1', 2, 'direct_target', 'partial'),
                ('table-retrieval.v1', 1, 'dependency_only', 'partial'),
                ('source-retrieval.v1', 0, 'unrelated', 'none'),
                ('chunk.v1', None, 'uncertain', 'uncertain')]):
            item = {'calibration_id': 'FIXTURE-cal-' + str(n), 'query_id': 'FIXTURE-q-' + str(n),
                    'record_id': 'FIXTURE-r-' + str(n), 'relevance': rel, 'relation': relation,
                    'completeness': complete, 'reason': 'SYNTHETIC decision',
                    'evidence_refs_used': ['FIXTURE/detail.json'], 'reviewer_outcome': 'uncertain' if rel is None else 'agree'}
            self.submission['items'].append(item)
            self.proposals[item['query_id'], item['record_id']] = {
                'record_type': kind, 'binding': self.submission['binding'], 'source_spans': [], 'cell_ids': []}
            self.evidence[item['calibration_id']] = {'detail_sha256': 'FIXTURE-sha',
                                                   'evidence_locators': [{'quote': 'SYNTHETIC source'}]}
        self.source = {'ref': 'staging/FIXTURE/submission.json', 'sha256': 'FIXTURE-source-sha'}

    def project(self):
        return labels.project(self.submission, self.proposals, self.evidence, self.source)

    def test_typed_records_are_not_coerced_to_chunks(self):
        _, accepted, pending = self.project()
        self.assertEqual([a['record_type'] for a in accepted],
                         ['chunk.v1', 'table-retrieval.v1', 'source-retrieval.v1'])
        self.assertTrue(all('chunk_id' not in a for a in accepted))
        self.assertEqual(len(pending), 1)

    def test_supporting_and_partial_fields_preserved(self):
        _, accepted, _ = self.project()
        self.assertEqual(accepted[1]['relevance'], 1)
        self.assertEqual(accepted[1]['relation'], 'dependency_only')
        self.assertEqual(accepted[0]['completeness'], 'partial')
        self.assertEqual(accepted[1]['evidence_locators'], self.evidence['FIXTURE-cal-1']['evidence_locators'])

    def test_null_stays_pending_and_never_enters_qrels(self):
        _, accepted, pending = self.project()
        self.assertIsNone(pending[0]['relevance'])
        self.assertEqual(pending[0]['status'], 'pending')
        self.assertNotIn(pending[0]['record_id'], {q['record_id'] for q in labels.qrels(accepted)})
        self.assertIn(0, [q['relevance'] for q in labels.qrels(accepted)])

    def test_replay_is_deterministic_and_does_not_mutate_input(self):
        before = copy.deepcopy(self.submission)
        self.assertEqual(self.project(), self.project())
        self.assertEqual(self.submission, before)

    def test_opaque_ref_preserved_and_ai_assistance_kept(self):
        _, accepted, _ = self.project()
        self.assertEqual(accepted[0]['reviewer_ref'], '## FIXTURE-OPAQUE-REF')
        self.assertEqual(accepted[0]['origin'], 'user_reviewed_ai_assisted')
        self.assertTrue(accepted[0]['ai_assisted'])
        self.assertFalse(accepted[0]['blind'])
        self.assertFalse(accepted[0]['independent'])

    def test_date_conversion_equivalence(self):
        self.assertEqual(datetime.fromisoformat('2026-11-05T08:00:00+07:00'),
                         datetime.fromisoformat('2026-11-05T01:00:00+00:00'))

    def test_missing_metadata_rejected(self):
        for key in ['reviewer_ref', 'reviewed_at']:
            old = self.submission[key]; self.submission[key] = None
            with self.subTest(field=key), self.assertRaises(ValueError): self.project()
            self.submission[key] = old

    def test_duplicate_ids_and_pairs_rejected(self):
        self.submission['items'].append(copy.deepcopy(self.submission['items'][0]))
        with self.assertRaises(ValueError): self.project()

    def test_wrong_binding_and_unsupported_record_type_rejected(self):
        first = next(iter(self.proposals.values()))
        first['binding'] = {'dataset_version': 'WRONG'}
        with self.assertRaises(ValueError): self.project()
        first['binding'] = self.submission['binding']; first['record_type'] = 'FAKE-chunk'
        with self.assertRaises(ValueError): self.project()

    def test_bool_is_not_zero_or_one(self):
        self.submission['items'][0]['relevance'] = True
        with self.assertRaises(ValueError): self.project()

    def test_null_with_direct_relation_rejected(self):
        self.submission['items'][-1]['relation'] = 'direct_target'
        with self.assertRaises(ValueError): self.project()

    def test_reimport_overlap_and_conflict_rejected(self):
        _, accepted, pending = self.project()
        for prior in [accepted, [{**accepted[0], 'relevance': 0}], pending]:
            with self.subTest(prior=prior), self.assertRaises(ValueError):
                labels.reject_overlap(accepted + pending, prior)
        labels.reject_overlap(accepted, [{'query_id': 'FIXTURE-other', 'record_id': 'FIXTURE-other'}])


@unittest.skipUnless(os.environ.get('VTLS_SUBSET_ACCEPTED_MANIFEST'), 'Opt-in real artifact checks')
class AcceptedArtifactTests(unittest.TestCase):
    def test_replay_idempotency_and_resealed_corruption(self):
        manifest = Path(os.environ['VTLS_SUBSET_ACCEPTED_MANIFEST']).resolve()
        output = Path(os.environ['VTLS_SUBSET_LABEL_CHECKS_DIR']).resolve()
        if labels.STAGING_DIR.resolve() not in output.parents:
            raise ValueError('Test output must be a new staging directory')
        output.mkdir(parents=True, exist_ok=False)
        root = manifest.parent
        result = labels.validate(manifest)
        receipt = labels.review.load(root / 'receipt.json')
        submission = labels.bound_file(receipt['source_submission'])
        before = labels.review.inventory(root)
        repeated = labels.admit(submission, root)
        self.assertEqual(repeated['state'], 'ALREADY_IMPORTED')
        self.assertEqual(repeated['newly_imported'], 0)
        self.assertEqual(before, labels.review.inventory(root))
        replay = output / 'replay'
        labels.admit(submission, replay)
        for name in ['accepted.annotations.jsonl', 'pending.annotations.jsonl', 'qrels.accepted.jsonl']:
            self.assertEqual((root / name).read_bytes(), (replay / name).read_bytes())
        self.assertEqual(result['import_id'], labels.validate(replay / 'manifest.json')['import_id'])
        duplicate = output / 'duplicate-prior'
        with self.assertRaisesRegex(ValueError, 'Duplicate/conflicting'):
            labels.admit(submission, duplicate, manifest)
        self.assertFalse(duplicate.exists())
        cases = [
            ('missing_accepted', 'accepted.annotations.jsonl', lambda v: v.pop()),
            ('duplicate_accepted', 'accepted.annotations.jsonl', lambda v: v.append(copy.deepcopy(v[0]))),
            ('wrong_binding', 'accepted.annotations.jsonl', lambda v: v[0]['binding'].__setitem__('dataset_version', 'WRONG')),
            ('wrong_record', 'accepted.annotations.jsonl', lambda v: v[0].__setitem__('record_id', 'WRONG')),
            ('wrong_type', 'accepted.annotations.jsonl', lambda v: v[0].__setitem__('record_type', 'table-retrieval.v1')),
            ('lost_relation', 'accepted.annotations.jsonl', lambda v: next(a for a in v if a['relation'] == 'dependency_only').__setitem__('relation', 'direct_target')),
            ('lost_completeness', 'accepted.annotations.jsonl', lambda v: next(a for a in v if a['completeness'] == 'partial').__setitem__('completeness', 'full')),
            ('wrong_evidence', 'accepted.annotations.jsonl', lambda v: v[0].__setitem__('evidence_refs_used', ['WRONG/detail.json'])),
            ('null_to_zero', 'pending.annotations.jsonl', lambda v: v[0].__setitem__('relevance', 0)),
            ('missing_pending', 'pending.annotations.jsonl', lambda v: v.pop()),
            ('duplicate_qrel', 'qrels.accepted.jsonl', lambda v: v.append(copy.deepcopy(v[0]))),
            ('null_qrel', 'qrels.accepted.jsonl', lambda v: v[0].__setitem__('relevance', None)),
            ('bool_qrel', 'qrels.accepted.jsonl', lambda v: next(a for a in v if a['relevance'] == 1).__setitem__('relevance', True)),
            ('bool_accepted', 'accepted.annotations.jsonl', lambda v: next(a for a in v if a['relevance'] == 1).__setitem__('relevance', True)),
            ('float_accepted', 'accepted.annotations.jsonl', lambda v: next(a for a in v if a['relevance'] == 0).__setitem__('relevance', 0.0)),
            ('wrong_reviewer', 'receipt.json', lambda v: v.__setitem__('reviewer_ref', 'WRONG')),
            ('fake_independent', 'receipt.json', lambda v: v.__setitem__('independent', True)),
            ('scope_expanded', 'receipt.json', lambda v: v.__setitem__('scope', 'all_500_pairs')),
            ('metrics_injected', 'receipt.json', lambda v: v.__setitem__('metrics', {'MRR': 1})),
        ]
        rejected = []
        for name, filename, mutate in cases:
            private = output / 'private' / name
            shutil.copytree(root, private)
            rows = filename.endswith('.jsonl')
            value = labels.review.rows(private / filename) if rows else labels.review.load(private / filename)
            mutate(value)
            (labels.review.write_rows if rows else labels.review.write_json)(private / filename, value)
            metadata = labels.review.load(private / 'manifest.json'); metadata.pop('files')
            labels.review.seal(private, metadata)
            with self.subTest(case=name):
                try:
                    labels.validate(private / 'manifest.json')
                except ValueError as exc:
                    rejected.append({'case': name, 'rejected': True, 'reason': str(exc)})
                else:
                    self.fail('Resealed mutation passed: ' + name)
        # Even rewriting the captured feedback/checksums cannot change a decision
        # in a snapshot authorized only to add metadata to the parent response.
        private = output / 'private' / 'metadata_snapshot_changes_null'
        shutil.copytree(submission.parent, private)
        response = labels.review.load(private / 'submission.json')
        item = next(i for i in response['items'] if i['calibration_id'] == 'CAL-b69c61257d')
        item.update(relevance=0, relation='unrelated', completeness='none', reviewer_outcome='edit')
        feedback = labels.review.load(private / 'feedback.received.json')
        next(i for i in feedback['items'] if i['calibration_id'] == item['calibration_id'])['relevance'] = 0
        labels.review.write_json(private / 'submission.json', response)
        labels.review.write_json(private / 'feedback.received.json', feedback)
        provenance = labels.review.load(private / 'provenance.json')
        provenance['submission_sha256'] = labels.digest((private / 'submission.json').read_bytes())
        provenance['feedback_sha256'] = labels.digest((private / 'feedback.received.json').read_bytes())
        labels.review.write_json(private / 'provenance.json', provenance)
        metadata = labels.review.load(private / 'manifest.json'); metadata.pop('files')
        labels.review.seal(private, metadata)
        with self.assertRaisesRegex(ValueError, 'changed prior decisions'):
            labels.load_response(private / 'submission.json')
        rejected.append({'case': 'metadata_snapshot_changes_null', 'rejected': True,
                         'reason': 'Metadata snapshot changed prior decisions or bindings'})
        labels.review.write_rows(output / 'negative_checks.jsonl', rejected)
        labels.review.write_json(output / 'validation_report.json', {
            **result, 'same_run_idempotent_noop': repeated['newly_imported'] == 0,
            'same_run_files_unchanged': before == labels.review.inventory(root),
            'replay_payloads_identical': True, 'prior_duplicate_rejected_before_output': not duplicate.exists(),
            'private_mutations_rejected': len(rejected)})


if __name__ == '__main__':
    unittest.main()
