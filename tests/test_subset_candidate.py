"""Synthetic FIXTURE tests only; real bundle verification is a separate opt-in CLI."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from src import subset_candidate_portable as p
from src import circular_dataset_portable as frozen
from src.subset_candidate import Assets


class ResolverTests(unittest.TestCase):
    def test_package_paths_cannot_fall_back_to_original_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(p.safe(root,'objects/FIXTURE'),root/'objects/FIXTURE')
            for ref in ['../raw.pdf','C:/private/raw.pdf','C:\\private\\raw.pdf','/outside/raw.pdf','objects/../../outside']:
                with self.subTest(ref=ref),self.assertRaises(ValueError):p.safe(root,ref)

    def test_every_declared_capability_is_required(self):
        p.require_capabilities(p.CAPABILITIES)
        for cap in p.CAPABILITIES:
            with self.subTest(cap=cap),self.assertRaises(ValueError):p.require_capabilities(p.CAPABILITIES-{cap})

    def test_asset_dedupe_preserves_two_original_aliases_and_one_object(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=root/'package';bundle.mkdir()
            a=root/'FIXTURE-a';b=root/'FIXTURE-b';a.write_bytes(b'FIXTURE same source bytes');b.write_bytes(a.read_bytes())
            assets=Assets(bundle);x=assets.add(a);y=assets.add(b)
            self.assertEqual(x,y);self.assertEqual(len(assets.mounts),2);self.assertEqual(len(list((bundle/'objects').iterdir())),1)
            with self.assertRaises(ValueError):assets.add(a,'WRONG')


class TableTests(unittest.TestCase):
    def fixture(self):
        c=object.__new__(p.Consumer);c.helpers=frozen
        row={'owner_unit_id':'FIXTURE-owner','row':1,'source_cell_ids':['FIXTURE-header','FIXTURE-value'],'text_derived':'FIXTURE speed: 10'}
        r={'owner_unit_id':'FIXTURE-owner','rows':[row],'cells':[{'cell_id':'FIXTURE-header','row':0},{'cell_id':'FIXTURE-value','row':1}],
           'text_for_search':'FIXTURE search','derived_text':row['text_derived']}
        r['content_sha256']=p.sha(r['text_for_search'].encode());r['retrieval_id']=frozen.table_identity(r)
        return c,r

    def test_complete_row_retains_header_and_owner(self):
        c,r=self.fixture();c._check_table(r)

    def test_header_cell_and_owner_errors_survive_rehash(self):
        for case in ['header','cell','owner','derived']:
            c,r=self.fixture()
            if case=='header':r['cells']=r['cells'][1:];r['rows'][0]['source_cell_ids']=['FIXTURE-value']
            elif case=='cell':r['cells'].pop()
            elif case=='owner':r['rows'][0]['owner_unit_id']='WRONG_OWNER'
            else:r['rows'][0]['text_derived']='Changed FIXTURE value'
            r['retrieval_id']=frozen.table_identity(r)
            with self.subTest(case=case),self.assertRaises(ValueError):c._check_table(r)


class IdentityBudgetTests(unittest.TestCase):
    def test_partial_frame_checks_do_not_bypass_failed_whole_bundle_validation(self):
        c=object.__new__(p.Consumer);c.targets={'FIXTURE-record':{}};c.frames={'FIXTURE-record':{}}
        c.checked={'FIXTURE-record'};c.validated=False;c.validate=Mock(side_effect=ValueError('FIXTURE whole bundle failed'))
        with self.assertRaisesRegex(ValueError,'whole bundle failed'):c.read('FIXTURE-record')
        c.validate.assert_called_once()

    def encoding(self):
        return {'input_sha256':p.sha(b'FIXTURE'),'truncation':False,'model_max_tokens':256,'tokens_with_special':3,
                'after':{'token_ids':[0,11,2],'token_ids_sha256':p.hashed([0,11,2])},'encoder_text':'FIXTURE',
                'encoder_text_sha256':p.sha(b'FIXTURE'),'unknown_tokens':0}

    def test_frozen_budget_check_never_silently_truncates(self):
        original=self.encoding();frozen.check_encoder(original,p.sha(b'FIXTURE'))
        for key,value in [('truncation',True),('tokens_with_special',257),('model_max_tokens',512),('encoder_text','Changed')]:
            e=copy.deepcopy(original);e[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):frozen.check_encoder(e,p.sha(b'FIXTURE'))

    def test_inventory_is_content_based_and_excludes_only_manifest_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'record.json').write_text('{"fixture":true}',encoding='utf8')
            first=p.inventory(root);(root/'dataset_manifest.json').write_text('{}',encoding='utf8')
            self.assertEqual(first,p.inventory(root))
            (root/'unexpected-cache').write_text('FIXTURE',encoding='utf8')
            self.assertNotEqual(first,p.inventory(root))


if __name__=='__main__':unittest.main()
