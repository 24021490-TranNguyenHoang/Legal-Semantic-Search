"""Composition binding/content tests; no legal-query Top1 assertions."""
from pathlib import Path
import copy
import json
import shutil
import unittest
import numpy as np
from src import bm25_baseline as baseline,composition_bm25 as index
from src.composition_consumer import Consumer
from src.experimental_dataset import load,rows,write_json,write_rows
from src.source_contracts import canonical,digest

DATA=Path('staging/dataset-v3-draft-005')
INDEX=Path('staging/bm25-composition-001')

class MappingTests(unittest.TestCase):
    def test_tie_uses_record_id(self):
        class Retriever:
            vocab_dict={'xe':0}
            def get_scores(self,tokens):return np.array([1.,1.],dtype=np.float32)
        tokens,hits=baseline.rank(Retriever(),{0:{'chunk_id':'tr_z'},1:{'chunk_id':'c_a'}},'xe',10,load(baseline.DEFAULT_CONFIG))
        self.assertEqual([i for i,_ in hits],[1,0])

class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATA.exists():raise unittest.SkipTest('Explicit composition bundle missing')
        cls.consumer=Consumer(DATA)

    def test_projection_matches_membership_both_types(self):
        c=self.consumer;p=c.projection()
        self.assertEqual({x['record_id'] for x in p},set(c.members))
        self.assertEqual({x['record_id'] for x in p if x['record_type']=='table-retrieval.v1'},
            {x['retrieval_id'] for x in rows(DATA/'table_records.jsonl')})
        self.assertTrue(all(c.records[x['record_id']]['text_for_search']==x['text_for_search'] for x in p))

    def test_frozen_reader_equivalence_and_table_cells(self):
        c=self.consumer;rid=next(rid for rid,m in c.members.items() if m['record_type']=='table-retrieval.v1')
        self.assertEqual(c.bound_read(rid),c.portable.read(DATA,rid))
        d=c.detail(rid);self.assertTrue(d['cells']);self.assertTrue(d['rows']);self.assertIsNotNone(d['derived_text_notice'])
        self.assertEqual(d['text_original'],d['payload']['source_original'])
        rid=next(d['record_id'] for d in c.dependencies if d['graph_id']=='base-docx')
        self.assertEqual(c.bound_read(rid),c.portable.read(DATA,rid))

    def test_real_parts_and_repeated_chapters(self):
        chapters=[u for u in self.consumer.graphs['tt35'].values() if u['unit_type']=='chapter' and u['designation']=='I']
        self.assertGreater(len(chapters),1);self.assertEqual(len(chapters),len({u['unit_id'] for u in chapters}))
        self.assertTrue(all('/part:' in u['canonical_path'] for u in chapters))

    def test_quarantine_is_readable_source_not_target(self):
        c=self.consumer;b=next(u for u in c.graphs['tt38'].values() if u['canonical_path'].endswith('/article:11/clause:2/point:b'))
        self.assertFalse(any(r.get('unit_id',r.get('owner_unit_id'))==b['unit_id'] for r in c.records.values()))
        link=next(d for d in c.dependencies if b['unit_id'] in d['unit_ids'])
        detail=c.detail(link['record_id']);allunits=[u for d in detail['required_read_dependencies'] for u in d['units']]
        self.assertIn(b,allunits)

    def test_capabilities_and_path_guard(self):
        with self.assertRaises(ValueError):Consumer(DATA,{'chunk.v1'})
        with self.assertRaises(ValueError):self.consumer.portable.resolve(DATA,'../../AGENTS.md')

class NegativeIndexTests(unittest.TestCase):
    def test_bound_failures_after_reseal(self):
        if not INDEX.exists():self.skipTest('Explicit composition index missing')
        n=1
        while Path(f'staging/composition-index-negative-{n:03d}').exists():n+=1
        dst=Path(f'staging/composition-index-negative-{n:03d}');shutil.copytree(INDEX,dst)
        original=load(dst/'index_manifest.json');results=[]
        def seal(m):
            write_json(dst/'index_manifest.json',m);(dst/'index_manifest.sha256').write_text(digest((dst/'index_manifest.json').read_bytes()),encoding='ascii')
        for name,key,value in [('dataset_hash','dataset_manifest_sha256','0'*64),('snapshot','snapshot_date','2026-01-01'),('path_escape','dataset_manifest_ref','../../AGENTS.md')]:
            m=copy.deepcopy(original);m[key]=value;seal(m)
            with self.assertRaises(ValueError) as ctx:index.load_index(dst/'index_manifest.json')
            results.append({'case':name,'rejected':True,'error':str(ctx.exception)})
        seal(original)
        file=dst/'document_mapping.jsonl';data=file.read_bytes();r=rows(file);r[0]['record_id']=r[1]['record_id'];write_rows(file,r)
        m=copy.deepcopy(original);m['files']=index.inventory(dst);m['index_content_sha256']=digest(canonical(m['files']).encode());seal(m)
        with self.assertRaisesRegex(ValueError,'mapping mismatch'):index.load_index(dst/'index_manifest.json')
        results.append({'case':'row_id','rejected':True});file.write_bytes(data);seal(original)
        # Dataset semantics are checked even when inventory/checksums are resealed.
        portable=Consumer(DATA).portable;dr=dst/'dataset'
        for filename,mutate in [('dependencies.jsonl',lambda r:[]),('memberships.jsonl',lambda r:[{**r[0],'record_type':'unknown'},*r[1:]])]:
            f=dr/filename;old=f.read_bytes();dm=load(dr/'dataset_manifest.json');dmbytes=(dr/'dataset_manifest.json').read_bytes();checksum=(dr/'dataset_manifest.sha256').read_bytes()
            write_rows(f,mutate(rows(f)));dm['files']=portable.inventory(dr);dm['dataset_content_sha256']=digest(canonical(dm['files']).encode());write_json(dr/'dataset_manifest.json',dm);(dr/'dataset_manifest.sha256').write_text(digest((dr/'dataset_manifest.json').read_bytes()),encoding='ascii')
            with self.assertRaises(ValueError) as ctx:Consumer(dr)
            results.append({'case':filename,'rejected':True,'error':str(ctx.exception)})
            f.write_bytes(old);(dr/'dataset_manifest.json').write_bytes(dmbytes);(dr/'dataset_manifest.sha256').write_bytes(checksum)
        dst.with_suffix('.results.json').write_text(json.dumps(results,indent=2),encoding='utf8')

if __name__=='__main__':unittest.main()
