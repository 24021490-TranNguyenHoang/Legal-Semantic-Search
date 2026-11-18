"""Finite v6 adapter regressions; fixtures explicitly synthetic, no metrics."""
import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src import subset_bm25 as old, subset_bm25_v6 as bm
from tests import test_subset_bm25 as fixtures


class V6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SubsetBM25Tests.setUpClass.__func__(cls)

    def test_algorithms_and_query_contract_unchanged(self):
        def functions(module):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(module.__file__).read_text('utf8')).body if isinstance(n,ast.FunctionDef)}
        a,b=functions(old),functions(bm)
        for name in ['projection','mapping_for','query_set','search_loaded','read_loaded']:
            self.assertEqual(a[name],b[name],name)
        self.assertEqual(old.SEARCH_POLICY,bm.SEARCH_POLICY)
        self.assertEqual(old.RECIPES,bm.RECIPES)

    def test_fixture_id_order_filters_oov_and_preprocessing(self):
        for query in ['đường','đường','zzzxxyyfixture']:
            for filters in [{},{'source_id':'B'},{'record_type':'table-retrieval.v1'}]:
                a=old.search_loaded(self.state,query,1,**filters);b=bm.search_loaded(self.state,query,1,**filters)
                for key in ['query_tokens','filters']:
                    self.assertEqual(a[key],b[key])
                self.assertEqual([{k:v for k,v in x.items() if k not in ['dataset_version','index_version']} for x in a['results']],
                                 [{k:v for k,v in x.items() if k not in ['dataset_version','index_version']} for x in b['results']])

    def test_inventory_uses_posix_case_sensitive_order(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            for ref in ['z.json','A.json','a-1.json','T/inside.json']:
                p=root/ref;p.parent.mkdir(exist_ok=True);p.write_text('SYNTHETIC')
            refs=[x['path'] for x in bm.inventory(root)]
            self.assertEqual(refs,sorted(refs));self.assertTrue(all('\\' not in x for x in refs))

    def test_comparison_uses_ids_and_keeps_membership_separate(self):
        from src.subset_bm25_comparison import top_delta
        a=[dict(record_id='FIXTURE-A',rank=1,score=2),dict(record_id='FIXTURE-B',rank=2,score=1)]
        b=[dict(record_id='FIXTURE-C',rank=1,score=3),dict(record_id='FIXTURE-A',rank=2,score=1)]
        d=top_delta(a,b)
        self.assertEqual(d['entered_top10'],['FIXTURE-C']);self.assertEqual(d['exited_top10'],['FIXTURE-B'])
        self.assertEqual(d['shared_rank_changes'][0]['new_rank'],2)
        self.assertNotIn('removed_targets',d)

    def test_new_versions_do_not_change_v1_constants(self):
        self.assertEqual(old.DATASET,'vtls-subset-experimental.v5-candidate.1')
        self.assertEqual(old.COUNTS['chunk.v1'],125)
        self.assertEqual(bm.DATASET,'vtls-subset-experimental.v6-candidate.1')
        self.assertEqual(sum(bm.COUNTS.values()),139)

if __name__=='__main__':unittest.main()
