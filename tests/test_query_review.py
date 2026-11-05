"""Synthetic pool/sheet invariants plus opt-in checks on the real finite bundle."""
import copy
import os
from pathlib import Path
import shutil
import unittest

from src import query_review as q


class QueryReviewTests(unittest.TestCase):
    def setUp(self):
        self.top = [{'query_id': 'FIXTURE-q', 'record_id': 'FIXTURE-r-' + str(i), 'rank': i}
                    for i in range(1, 11)]
        self.accepted = [{'query_id': 'FIXTURE-q', 'record_id': 'FIXTURE-r-1'}]
        self.outside = [{'query_id': 'FIXTURE-q', 'record_id': 'FIXTURE-outside', 'relevance': 1,
                         'origin': 'agent_review', 'status': 'proposed'}]

    def test_pool_deduplicates_pair_but_retains_all_sources(self):
        self.accepted.append(copy.deepcopy(self.outside[0]))
        result = dict(q.pool_union(['FIXTURE-q'], self.top, self.accepted, self.outside))
        self.assertEqual(len(result), 11)
        self.assertEqual([s['origin'] for s in result['FIXTURE-q', 'FIXTURE-outside']],
                         ['accepted_existing', 'outside_positive_session7'])

    def test_identical_record_in_different_query_stays_separate(self):
        top = self.top + [{**r, 'query_id': 'FIXTURE-other'} for r in self.top]
        self.assertEqual(len(q.pool_union(['FIXTURE-q', 'FIXTURE-other'], top, [], [])), 20)

    def test_missing_and_duplicate_top10_are_errors(self):
        for run in [self.top[:-1], self.top + [self.top[0]]]:
            with self.subTest(run=run), self.assertRaises(ValueError):
                q.pool_union(['FIXTURE-q'], run, [], [])

    def test_deep_unjudged_or_wrong_query_not_added(self):
        other = [{**self.outside[0], 'query_id': 'FIXTURE-other'}]
        self.assertEqual(len(q.pool_union(['FIXTURE-q'], self.top, [], other)), 10)
        for fields in [{'relevance': None}, {'relevance': 0}, {'relevance': True}, {'status': 'pending'}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                q.pool_union(['FIXTURE-q'], self.top, [], [{**self.outside[0], **fields}])

    def test_duplicate_accepted_and_outside_are_not_silently_swallowed(self):
        for accepted, outside in [(self.accepted * 2, []), ([], self.outside * 2)]:
            with self.assertRaises(ValueError): q.pool_union(['FIXTURE-q'], self.top, accepted, outside)

    def test_page_limit_never_discards_pairs_or_rescores_accepted(self):
        pool = [{'query_id': 'FIXTURE-q', 'record_id': str(i), 'accepted_existing': i < 2}
                for i in range(45)]
        pages = q.paginate(pool, ['FIXTURE-q'], 20)
        self.assertEqual([len(p['members']) for p in pages], [20, 20, 3])
        self.assertEqual(len({p['record_id'] for s in pages for p in s['members']}), 43)

    def test_sheet_budget_invalid_values(self):
        for maximum in [0, 21, True]:
            with self.subTest(maximum=maximum), self.assertRaises(ValueError):
                q.paginate([], [], maximum)

    def test_new_template_blank_no_prior_reviewer_or_approval(self):
        member = {'review_pair_id': 'FIXTURE-pair', 'query_id': 'FIXTURE-q', 'record_id': 'FIXTURE-r',
                  'record_type': 'table-retrieval.v1', 'query_sha256': 'q', 'record_sha256': 'r', 'detail_sha256': 'd'}
        template = q.blank_response({'sheet_id': 'FIXTURE-sheet', 'members': [member]},
                                    {'dataset_version': 'FIXTURE'}, 'pool-sha',
                                    {('FIXTURE-q', 'FIXTURE-r'): {'relevance': 1}})
        for key in ['reviewer_ref', 'reviewed_at', 'proposal_consulted', 'ai_assisted',
                    'independent', 'blind', 'coverage_decision', 'all_labels_approved']:
            self.assertIsNone(template[key])
        for key in ['relevance', 'relation', 'completeness', 'reviewer_outcome', 'reason']:
            self.assertIsNone(template['items'][0][key])
        self.assertEqual(template['items'][0]['evidence_refs_used'], [])

    def test_neutral_content_has_cells_and_whole_dependency(self):
        detail = {'citation_path': 'FIXTURE-table', 'record_id': 'FIXTURE-r',
                  'record_type': 'table-retrieval.v1', 'text_original': 'SYNTHETIC source',
                  'cells': [{'row': 0, 'column': 1, 'cell_id': 'FIXTURE-cell', 'text': 'SYNTHETIC header 60'}],
                  'dataset_response': {'record': {'derived_text': 'SYNTHETIC derived',
                      'source_record': {'text_derived': 'SYNTHETIC dependency table', 'context_text': 'SYNTHETIC own context'}}}}
        text = '\n'.join(q.record_text(detail))
        for phrase in ['SYNTHETIC source', 'SYNTHETIC header 60', 'SYNTHETIC derived',
                       'SYNTHETIC dependency table', 'SYNTHETIC own context']:
            self.assertIn(phrase, text)
        self.assertNotIn('relevance', text)
        self.assertNotIn('rank', text)


@unittest.skipUnless(os.environ.get('VTLS_QUERY_REVIEW_MANIFEST'), 'Opt-in finite real artifact checks')
class QueryReviewArtifactTests(unittest.TestCase):
    def test_replay_and_resealed_failures(self):
        manifest = Path(os.environ['VTLS_QUERY_REVIEW_MANIFEST']).resolve()
        output = Path(os.environ['VTLS_QUERY_REVIEW_CHECKS_DIR']).resolve()
        if q.labels.STAGING_DIR.resolve() not in output.parents:
            raise ValueError('Private test output must be in staging')
        output.mkdir(parents=True, exist_ok=False)
        root = manifest.parent
        # All corruptions below affect outputs only. Keep one freshly validated
        # input projection instead of re-reading immutable upstream files 14 times.
        loaded = q.assemble(root / 'config.snapshot.json')
        result = q.validate(manifest, loaded)
        q.build(root / 'config.snapshot.json', output / 'replay')
        original = q.review.load(manifest)
        for f in original['files']:
            self.assertEqual((root / f['path']).read_bytes(), (output / 'replay' / f['path']).read_bytes())
        self.assertEqual(manifest.read_bytes(), (output / 'replay' / 'manifest.json').read_bytes())
        index = q.review.load(root / 'sheets.json')[0]
        cases = [
            ('missing_pool_pair', 'pool.jsonl', lambda v: v.pop()),
            ('duplicate_pool_pair', 'pool.jsonl', lambda v: v.append(v[0])),
            ('wrong_pool_origin', 'pool.jsonl', lambda v: v[0].__setitem__('pool_sources', [])),
            ('wrong_query', 'queries.jsonl', lambda v: v[0].__setitem__('query', 'CHANGED')),
            ('changed_accepted', 'accepted.inherited.jsonl', lambda v: v[0].__setitem__('relevance', 0)),
            ('lost_prior_metadata', 'accepted.inherited.jsonl', lambda v: v[0].__setitem__('reviewer_ref', None)),
            ('wrong_evidence', 'proposals/annotations.proposed.jsonl', lambda v: v[0]['evidence_locators'][0].__setitem__('char_end', 1)),
            ('proposal_accepted', 'proposals/annotations.proposed.jsonl', lambda v: v[0].__setitem__('status', 'accepted')),
            ('fake_template_reviewer', index['template_ref'], lambda v: v.__setitem__('reviewer_ref', 'INVENTED')),
            ('template_filled', index['template_ref'], lambda v: v['items'][0].__setitem__('relevance', 0)),
            ('missing_template_pair', index['template_ref'], lambda v: v['items'].pop()),
            ('template_duplicate', index['template_ref'], lambda v: v['items'].append(v['items'][0])),
        ]
        rejected = []
        for name, filename, mutate in cases:
            private = output / 'private' / name
            shutil.copytree(root, private)
            value = q.review.rows(private / filename) if filename.endswith('.jsonl') else q.review.load(private / filename)
            mutate(value)
            (q.review.write_rows if filename.endswith('.jsonl') else q.review.write_json)(private / filename, value)
            meta = q.review.load(private / 'manifest.json'); meta.pop('files')
            q.review.seal(private, meta)
            with self.subTest(case=name), self.assertRaises(ValueError): q.validate(private / 'manifest.json', loaded)
            rejected.append({'case': name, 'rejected': True})
        for name, suffix in [('rank_leak', '\nRank: 1, score: 9.0\n'),
                             ('label_leak', '\nĐề xuất: relevance=2\n')]:
            private = output / 'private' / name
            shutil.copytree(root, private)
            sheet = private / index['review_ref']
            sheet.write_text(sheet.read_text(encoding='utf-8') + suffix, encoding='utf-8')
            meta = q.review.load(private / 'manifest.json'); meta.pop('files'); q.review.seal(private, meta)
            with self.subTest(case=name), self.assertRaises(ValueError): q.validate(private / 'manifest.json', loaded)
            rejected.append({'case': name, 'rejected': True})
        q.review.write_rows(output / 'negative_checks.jsonl', rejected)
        q.review.write_json(output / 'validation_report.json', {**result, 'payload_and_manifest_replay_identical': True,
                            'private_mutations_rejected': len(rejected)})


if __name__ == '__main__':
    unittest.main()
