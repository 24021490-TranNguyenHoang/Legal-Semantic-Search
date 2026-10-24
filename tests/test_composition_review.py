"""Synthetic review records: binding/pending/evidence checks, not retrieval quality."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from src.composition_review import validate_annotation, validate_pair_set, sha
from src.source_contracts import digest
from src.assessment_evidence import now


class CompositionReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'details').mkdir()
        self.queries = {'fixture-q': {'query_id': 'fixture-q', 'query': 'Synthetic question'}}
        self.binding = {'dataset_version': 'fixture-only', 'snapshot': '2025-01-01'}
        self.detail = {'citation_path': 'FIXTURE > Article1', 'source_spans': [{'span_id': 'fixture-s'}],
                       'cells': [], 'required_read_dependencies': [{'unit_ids': ['fixture-source']}],
                       'text_original': 'Synthetic content', 'record_id': 'fixture-c'}
        self.consumer = SimpleNamespace(records={'fixture-c': {'text_original': 'Synthetic content'}},
                                        members={'fixture-c': {'record_type': 'chunk.v1'}},
                                        detail=lambda rid: copy.deepcopy(self.detail))
        dest = self.root/'details/fixture-c.json'
        dest.write_text(json.dumps(self.detail), encoding='utf8')
        self.a = {'query_id': 'fixture-q', 'record_id': 'fixture-c', 'record_type': 'chunk.v1',
                  'binding': self.binding, 'query_sha256': sha(self.queries['fixture-q']),
                  'record_sha256': sha(self.consumer.records['fixture-c']),
                  'origin': 'agent_review', 'status': 'proposed', 'reviewer_ref': None,
                  'relevance': 2, 'relation': 'direct_target', 'completeness': 'partial',
                  'reason': 'Synthetic half of a multipart question', 'answered_part': 'First half',
                  'missing_part': 'Second half', 'uncertainty': None, 'recorded_at': now(),
                  'evidence_refs': ['details/fixture-c.json'], 'detail_sha256': digest(dest.read_bytes()),
                  'citation_path': self.detail['citation_path'], 'source_spans': self.detail['source_spans'],
                  'cell_ids': [], 'combine_with': []}

    def check(self, a=None):
        validate_annotation(self.a if a is None else a, self.queries, self.consumer, self.root, self.binding)

    def test_direct_partial_is_valid_without_full_answer(self):
        self.check()

    def test_missing_duplicate_extra_pairs_are_rejected(self):
        expected = {('fixture-q', 'fixture-c')}
        validate_pair_set([self.a], expected)
        for annotations in [[], [self.a, self.a], [self.a, {**self.a, 'record_id': 'other'}]]:
            with self.subTest(annotations=annotations), self.assertRaises(ValueError):
                validate_pair_set(annotations, expected)

    def test_dependency_does_not_create_ranked_source(self):
        self.a.update(relevance=1, relation='dependency_only')
        self.check()
        self.a['record_id'] = 'fixture-source'
        with self.assertRaisesRegex(ValueError, 'retrieval member'): self.check()

    def test_unknown_judgment_remains_null(self):
        self.a.update(relevance=None, status='pending', relation='uncertain', completeness='uncertain', uncertainty='Unknown condition')
        self.check()
        self.a['relevance'] = 0
        with self.assertRaises(ValueError): self.check()

    def test_agent_cannot_create_human_or_accepted_event(self):
        for changes in [{'status': 'accepted'}, {'origin': 'human'}, {'reviewer_ref': 'invented-person'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.check({**self.a, **changes})

    def test_query_record_and_version_hashes(self):
        for field in ['query_sha256', 'record_sha256', 'binding', 'record_type']:
            with self.subTest(field=field), self.assertRaises(ValueError): self.check({**self.a, field: 'wrong'})

    def test_source_and_table_cells_cannot_be_substituted(self):
        for field in ['source_spans', 'cell_ids', 'citation_path', 'detail_sha256']:
            with self.subTest(field=field), self.assertRaises(ValueError): self.check({**self.a, field: 'wrong'})

    def test_detail_context_tampering_is_rejected(self):
        dest = self.root/'details/fixture-c.json'
        dest.write_text(json.dumps({**self.detail, 'text_original': 'Changed'}), encoding='utf8')
        self.a['detail_sha256'] = digest(dest.read_bytes())
        with self.assertRaisesRegex(ValueError, 'detail/source/context'): self.check()

    def test_missing_evidence_explanation_or_bad_date(self):
        for changes in [{'evidence_refs': []}, {'reason': ''}, {'missing_part': None},
                        {'recorded_at': '2099-01-01T00:00:00Z'}, {'recorded_at': '2025-01-01T00:00:00'},
                        {'combine_with': ['fixture-source']}, {'relevance': True}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.check({**self.a, **changes})


if __name__ == '__main__':
    unittest.main()
