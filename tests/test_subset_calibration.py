"""Synthetic response validation; no human identity or corpus quality claims."""
import copy
from unittest import TestCase, main

from src import subset_calibration as c


class CalibrationResponseTests(TestCase):
    def setUp(self):
        self.proposal = {'relevance': 2, 'relation': 'direct_target', 'completeness': 'partial'}
        self.pair = ('FIXTURE-query', 'FIXTURE-record')
        self.proposals = {self.pair: self.proposal}
        self.template = {'binding': {'dataset_version': 'FIXTURE-only'},
                         'reviewer_ref': None, 'reviewed_at': None,
                         'coverage_decision': None, 'all_labels_approved': None,
                         'items': [{'calibration_id': 'FIXTURE-cal', 'query_id': self.pair[0],
                                    'record_id': self.pair[1], 'query_sha256': 'FIXTURE-query-hash',
                                    'record_sha256': 'FIXTURE-record-hash',
                                    'proposal_sha256': c.review.bm.hashed(self.proposal),
                                    'reviewer_outcome': None, 'relevance': None, 'relation': None,
                                    'completeness': None, 'reason': None, 'evidence_refs_used': []}]}
        self.response = copy.deepcopy(self.template)
        self.response['items'][0].update(reviewer_outcome='agree', relevance=2,
                                        relation='direct_target', completeness='partial',
                                        reason='SYNTHETIC source matches only part of the question.',
                                        evidence_refs_used=['FIXTURE/detail.json'])
        self.feedback = [{'calibration_id': 'FIXTURE-cal', 'relevance': 2,
                          'reason': self.response['items'][0]['reason']}]

    def validate(self, value=None):
        return c.validate_items(value or self.response, self.template, self.proposals, self.feedback)

    def test_response_can_be_valid_while_metadata_missing(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(c.metadata_blockers(self.response), ['reviewer_ref', 'reviewed_at'])

    def test_null_override_preserved_instead_of_proposal(self):
        self.feedback[0]['relevance'] = None
        self.response['items'][0].update(relevance=None, relation='uncertain',
                                         completeness='uncertain', reviewer_outcome='uncertain')
        changes = self.validate()
        self.assertEqual(changes[0]['proposal'][0], 2)
        self.assertIsNone(changes[0]['response'][0])

    def test_evidenced_label_disagreement_is_allowed(self):
        self.feedback[0]['relevance'] = 0
        self.response['items'][0].update(relevance=0, relation='unrelated',
                                         completeness='none', reviewer_outcome='edit')
        self.assertEqual(self.validate()[0]['response'], [0, 'unrelated', 'none'])

    def test_missing_duplicate_or_foreign_item_rejected(self):
        for items in [[], self.response['items'] * 2,
                      [{**self.response['items'][0], 'calibration_id': 'FOREIGN'}]]:
            with self.subTest(items=items), self.assertRaises(ValueError):
                self.validate({**self.response, 'items': items})

    def test_each_identity_and_binding_must_stay_exact(self):
        for field in c.IDENTITY:
            bad = copy.deepcopy(self.response)
            bad['items'][0][field] = 'WRONG'
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate(bad)
        with self.assertRaises(ValueError): self.validate({**self.response, 'binding': {}})

    def test_explicit_reason_and_label_cannot_be_rewritten(self):
        for fields in [{'relevance': 0}, {'reason': 'A different reason'}, {'relevance': True}]:
            bad = copy.deepcopy(self.response); bad['items'][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError): self.validate(bad)

    def test_enum_and_evidence_rejected(self):
        for fields in [{'relation': 'accepted'}, {'completeness': 'complete'},
                       {'reviewer_outcome': 'accepted'}, {'evidence_refs_used': []},
                       {'evidence_refs_used': ['FIXTURE/a', 'FIXTURE/a']}]:
            bad = copy.deepcopy(self.response); bad['items'][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError): self.validate(bad)

    def test_pending_cannot_be_promoted_to_zero(self):
        self.feedback[0]['relevance'] = None
        bad = copy.deepcopy(self.response)
        bad['items'][0].update(relevance=0, relation='unrelated', completeness='none')
        with self.assertRaises(ValueError): self.validate(bad)

    def test_no_sample_to_all_labels_or_coverage_approval(self):
        for field in ['all_labels_approved', 'coverage_decision']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate({**self.response, field: True})

    def test_metadata_invalid_dates_and_empty_identity(self):
        for fields in [{'reviewer_ref': ''}, {'reviewer_ref': 123},
                       {'reviewed_at': '2026-01-01'}, {'reviewed_at': 0},
                       {'reviewed_at': '2999-01-01T00:00:00Z'}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                c.metadata_blockers({**self.response, **fields})

    def test_synthetic_metadata_does_not_import_anything(self):
        synthetic = {**self.response, 'reviewer_ref': 'SYNTHETIC-NOT-A-PERSON',
                     'reviewed_at': '2020-01-01T00:00:00Z'}
        self.assertEqual(c.metadata_blockers(synthetic), [])
        self.assertIsNone(self.response['reviewer_ref'])


if __name__ == '__main__':
    main()
