"""Synthetic FIXTURE data only; not a legal review or a retrieval evaluation."""
import copy
import unittest
from unittest.mock import patch

from src.membership_proposal import check_memberships, nd_lineage
from src.ingestion.table_owner_adapter import TableOwnerConsumer, require_capabilities, CAPABILITIES


class MembershipTests(unittest.TestCase):
    def fixture(self):
        source = {'graph_manifest_sha256': 'FIXTURE-graph', 'files': [{'sha256': 'FIXTURE-raw'}]}
        row = {'unit_id': 'FIXTURE-unit', 'source_id': 'SRC-001', 'source_version_sha256': 'FIXTURE-graph',
               'canonical_path': 'FIXTURE/article:1', 'role': 'target', 'scope': 'in_scope', 'technical': 'ready',
               'record_id': 'FIXTURE-record', 'record_type': 'chunk.v1', 'membership': 'proposed_include',
               'human_review': None, 'release_eligible': False, 'proof_source_hashes': ['FIXTURE-raw'], 'required_dependency_ids': []}
        return row, {'SRC-001': source}

    def test_source_version_and_proof_binding(self):
        row, sources = self.fixture(); check_memberships([row], sources, {}, {'chunk.v1'})
        for field, value in [('source_version_sha256','WRONG'), ('proof_source_hashes',['WRONG']), ('proof_source_hashes',[])]:
            altered = {**row, field:value}
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                check_memberships([altered], sources, {}, {'chunk.v1'})

    def test_missing_dependency_and_stale_id(self):
        row, sources = self.fixture(); row['required_dependency_ids'] = ['FIXTURE-dep']
        for deps in [{}, {'FIXTURE-dep': {'from_unit_id':row['unit_id'], 'unit_ids':['OLD-unresolved-ID']}}]:
            with self.assertRaises(ValueError): check_memberships([row], sources, deps, {'chunk.v1'})

    def test_duplicate_docx_html_target_is_not_two_legal_positions(self):
        row, sources = self.fixture(); other = {**row, 'unit_id':'FIXTURE-html-unit','record_id':'FIXTURE-html-record'}
        with self.assertRaisesRegex(ValueError, 'Duplicate DOCX/HTML'):
            check_memberships([row, other], sources, {}, {'chunk.v1'})

    def test_missing_capability_and_independent_view(self):
        row, sources = self.fixture()
        with self.assertRaises(ValueError): check_memberships([row], sources, {}, set())
        row['independent_encoder_view'] = True
        with self.assertRaisesRegex(ValueError, 'Encoder view'): check_memberships([row], sources, {}, {'chunk.v1'})

    def test_qcvn_conflict_not_admitted(self):
        row, sources = self.fixture(); sources['SRC-006'] = sources['SRC-001']; row['source_id'] = 'SRC-006'
        row['region_key'] = 'R-caption-I416'
        with self.assertRaisesRegex(ValueError, 'QCVN'): check_memberships([row], sources, {}, {'chunk.v1'})

    def test_pending_scope_and_partial_review_do_not_open_gate(self):
        row, sources = self.fixture(); row['scope'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'Ineligible'): check_memberships([row], sources, {}, {'chunk.v1'})
        row['membership'] = 'pending'; check_memberships([row], sources, {}, {'chunk.v1'})

    def test_table_rows_require_distinct_real_anchors(self):
        row, sources = self.fixture(); row['record_anchor'] = 'FIXTURE-row1'
        other = {**row, 'record_id':'FIXTURE-row2', 'record_anchor':'FIXTURE-row2'}
        check_memberships([row, other], sources, {}, {'chunk.v1'})


class TableConsumerTests(unittest.TestCase):
    def test_capabilities_and_whole_record_tamper(self):
        require_capabilities(CAPABILITIES)
        with self.assertRaises(ValueError): require_capabilities(CAPABILITIES - {'bounded-dependency-read.v1'})
        consumer = object.__new__(TableOwnerConsumer)
        expected = {'record_id':'FIXTURE-table','header':['FIXTURE-h'],'cells':['FIXTURE-cell'], 'required_dependencies':['FIXTURE-annexII']}
        consumer.records = [expected]; consumer.validate_record(expected)
        for field in ['header','cells','required_dependencies']:
            altered = copy.deepcopy(expected); altered[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError): consumer.validate_record(altered)


class LineageTests(unittest.TestCase):
    def test_two_step_lineage_not_just_citation(self):
        old = {'unit_id':'FIXTURE-phase1','parent_unit_id':'P1','designation':'a','canonical_path':'FIXTURE/a',
               'citation_path':'FIXTURE a','ordinal':1,'title':'','text_original':'FIXTURE text'}
        new = {**old,'unit_id':'FIXTURE-phase2','parent_unit_id':'P2'}
        cw = [{'old_unit_id':old['unit_id'],'new_unit_id':new['unit_id'],'changed_identity_fields':['parent_unit_id']}]
        def reader(path):
            name = path.as_posix()
            if name.endswith('graph/legal_units.pending.jsonl'): return [old]
            if 'session2' in name and name.endswith('/unit_crosswalk.jsonl'): return cw
            if name.endswith('/unit_crosswalk.jsonl'): return [{'old_unit_id':'FIXTURE-raw','new_unit_id':old['unit_id']}]
            if name.endswith('source_spans.pending.jsonl'): return [{'span_id':'FIXTURE-span'}]
            if name.endswith('span_crosswalk.jsonl'): return [{'old_span_id':'FIXTURE-span','new_span_id':'FIXTURE-span'}]
            raise AssertionError(name)
        with patch('src.membership_proposal.rows', side_effect=reader):
            _, chain, _ = nd_lineage({new['unit_id']:new})
            self.assertEqual(chain['FIXTURE-raw'], new['unit_id'])
            with self.assertRaises(ValueError): nd_lineage({'WRONG':new})


if __name__ == '__main__': unittest.main()
