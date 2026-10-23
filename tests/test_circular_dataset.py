"""Finite adapter/resolver checks; synthetic fixtures and explicit bundle integration."""
from pathlib import Path
import copy
import json
import shutil
import unittest
from src import circular_dataset_portable as p

class PortableUnitTests(unittest.TestCase):
    def test_escaping_reference_rejected(self):
        with self.assertRaises(ValueError):p.resolve(Path('staging'), '../data/raw/file.pdf')

    def test_encoder_budget_and_truncation(self):
        e={'input_sha256':'input','truncation':False,'model_max_tokens':256,'tokens_with_special':257,
           'after':{'token_ids':[1]*257,'token_ids_sha256':p.sha(p.canonical([1]*257).encode())},
           'encoder_text':'FIXTURE synthetic','encoder_text_sha256':p.sha(b'FIXTURE synthetic'),'unknown_tokens':0}
        with self.assertRaises(ValueError):p.check_encoder(e,'input')
        e['tokens_with_special']=2;e['after']['token_ids']=[0,2];e['after']['token_ids_sha256']=p.sha(b'[0,2]');p.check_encoder(e,'input')
        e['truncation']=True
        with self.assertRaises(ValueError):p.check_encoder(e,'input')

class RealBundleIntegration(unittest.TestCase):
    def test_resealed_mutations_rejected(self):
        source=Path('staging/dataset-v3-draft-005')
        if not (source/'dataset_manifest.json').exists():self.skipTest('Build the explicit experimental draft fixture first')
        n=1
        while Path(f'staging/circular-dataset-negative-{n:03d}').exists():n+=1
        dest=Path(f'staging/circular-dataset-negative-{n:03d}')
        shutil.copytree(source,dest);results=[]
        cases=[('dependency_missing','dependencies.jsonl',lambda r:[]),
               ('wrong_record_type','memberships.jsonl',lambda r:[{**r[0],'record_type':'unknown'},*r[1:]]),
               ('table_header_removed','table_records.jsonl',lambda r:[{**r[0],'cells':[]},*r[1:]]),
               ('wrong_parent','graphs/tt35.units.jsonl',lambda r:[*r[:-1],{**r[-1],'parent_unit_id':r[0]['unit_id']}]),
               ('crosswalk_wrong','unit_crosswalk.jsonl',lambda r:[{**r[0],'new_unit_id':'u_'+'0'*64},*r[1:]])]
        for name,file,change in cases:
            original=(dest/file).read_bytes();data=change(p.rows(dest/file))
            (dest/file).write_text(''.join(p.canonical(x)+'\n' for x in data),encoding='utf8')
            m=p.load(dest/'dataset_manifest.json');m['files']=p.inventory(dest);m['dataset_content_sha256']=p.sha(p.canonical(m['files']).encode())
            (dest/'dataset_manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf8');(dest/'dataset_manifest.sha256').write_text(p.sha((dest/'dataset_manifest.json').read_bytes()),encoding='ascii')
            with self.assertRaises((ValueError,KeyError)) as ctx:p.validate(dest)
            results.append({'case':name,'rejected':True,'error':str(ctx.exception)});(dest/file).write_bytes(original)
        # Capability and snapshot guards run on the unchanged, valid bundle.
        with self.assertRaises(ValueError):p.validate(source,{'chunk.v1'})
        m=p.load(dest/'dataset_manifest.json');m['snapshot_date']='2026-01-01'
        (dest/'dataset_manifest.json').write_text(json.dumps(m),encoding='utf8');(dest/'dataset_manifest.sha256').write_text(p.sha((dest/'dataset_manifest.json').read_bytes()),encoding='ascii')
        with self.assertRaisesRegex(ValueError,'Invalid composition status/snapshot'):p.validate(dest)
        results.append({'case':'wrong_snapshot','rejected':True})
        dest.with_suffix('.results.json').write_text(json.dumps(results,indent=2),encoding='utf8')

if __name__=='__main__':unittest.main()
