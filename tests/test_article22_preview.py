"""Chunk/context PREVIEW checks. Fixture data never becomes real legal corpus."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from src.article22_preview import (DEFAULT_CONFIG, EXTRA_BLOCKERS, MetadataHTML, make_chunks, chunk_identity,
                                  require_preview_schema, require_config, validate, replay, validation_report)
from src.config import BASE_DIR, STAGING_DIR
from src.preview_tokens import count_tokens, default_tokenizer_dir, ASSETS, inspect_assets
from src.source_contracts import canonical, digest
from src.source_registry import load_json, read_rows
from src.assessment_evidence import inventory
from test_article22_draft import fixture_context


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-preview-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        c = fixture_context(self.root / "fixture")
        t = c["tables"]
        self.data = {"document": t["legal_document"][0], "files": t["source_file"], "extractions": t["extraction"],
                     "units": t["legal_unit"], "spans": t["source_span"]}
        self.cfg = load_json(DEFAULT_CONFIG)

    def chunks(self):
        return make_chunks(self.data, self.root / "fixture", self.cfg, ["PENDING"] + EXTRA_BLOCKERS)

    def test_three_whole_targets_and_six_source_linked_contexts(self):
        chunks, contexts = self.chunks()
        self.assertEqual((len(chunks), len(contexts)), (3, 6))
        require_preview_schema(chunks)
        article = self.data["units"][2]
        for c in chunks:
            u = next(u for u in self.data["units"] if u["unit_id"] == c["unit_id"])
            self.assertEqual(c["text_original"], u["text_original"])
            self.assertEqual((c["unit_char_start"], c["unit_char_end"], c["segment_no"]), (0, len(u["text_original"]), 1))
            self.assertEqual(c["context_text"], article["title"] + "\n" + article["text_original"])
            self.assertEqual(c["text_for_search"], "\n\n".join([self.data["document"]["law_title"], u["citation_path"], c["context_text"], u["text_original"]]))
            self.assertEqual(c["content_sha256"], digest(c["text_for_search"].encode()))
            for p in json.loads(c["source_locator"]):
                q=(self.root/'fixture'/p['text_ref'].removeprefix('mapping_snapshot/')).read_text(encoding='utf8')[p['char_start']:p['char_end']]
                self.assertEqual(q,c['text_original'])
        for c in contexts:
            self.assertEqual(c["unit_id"], article["unit_id"])
            self.assertNotIn(c["unit_id"], {u["unit_id"] for u in self.data["units"][:2]})
            self.assertTrue(json.loads(c["source_locator"])[0]["span_id"].startswith("s_"))

    def test_exact_design_chunk_v1_formula_including_pending_metadata(self):
        with ZipFile(BASE_DIR/'docs/design/data_model_v1/Data_Model_Schema_Examples_v1.0.zip') as z:
            tree=ast.parse(z.read('validate_design.py').decode('utf8'))
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'canonical','digest','chunk_id'}]
        scope={'json':json,'hashlib':hashlib}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'<design-pure-functions>','exec'),scope)
        chunks,contexts=self.chunks()
        for c in chunks:
            own=[x for x in contexts if x['chunk_id']==c['chunk_id']]
            fingerprint=[{k:x[k] for k in ['unit_id','field_name','char_start','char_end','context_role','context_order']} for x in own]
            u=next(u for u in self.data['units'] if u['unit_id']==c['unit_id'])
            expected=scope['chunk_id'](c,u,self.data['document'],{'effective_from':None,'effective_to':None,'applicability_status':'pending_review'},fingerprint)
            self.assertEqual(c['chunk_id'],expected)

    def test_preview_does_not_pass_serving_schema_or_claim_approval(self):
        from jsonschema import Draft202012Validator
        with ZipFile(BASE_DIR/'docs/design/data_model_v1/Data_Model_Schema_Examples_v1.0.zip') as z:schema=json.loads(z.read('chunk.schema.json'))
        chunks,_=self.chunks()
        for c in chunks:
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(c)))
            self.assertIsNone(c['corpus_version']);self.assertIsNone(c['effective_from'])
            self.assertFalse(c['release_eligible']);self.assertEqual(c['applicability_status'],'pending_review')

    def test_replay_determinism_and_id_changes_for_context_or_legal_metadata(self):
        a,b=self.chunks(),self.chunks()
        self.assertEqual(a,b)
        c=a[0][0];own=[x for x in a[1] if x['chunk_id']==c['chunk_id']]
        payload=chunk_identity(c,own)
        modified=copy.deepcopy(c);modified['applicability_status']='verified_at_snapshot';modified['effective_from']='2025-01-01'
        self.assertNotEqual(payload,chunk_identity(modified,own))
        changed=copy.deepcopy(own);changed[0]['char_end']-=1
        self.assertNotEqual(payload,chunk_identity(c,changed))

    def test_offset_drift_or_missing_lead_rejected(self):
        own=self.data['spans'][-1];own['char_start']+=1
        with self.assertRaises(ValueError):self.chunks()
        self.data['spans'][-1]['char_start']-=1
        self.data['units'][2]['text_original']=''
        with self.assertRaises(ValueError):self.chunks()

    def test_scope_cannot_expand_or_assert_verified(self):
        self.data['units'].append(copy.deepcopy(self.data['units'][-1]))
        with self.assertRaises(ValueError):self.chunks()
        self.data['units'].pop()
        self.cfg['effective_from']='2025-01-01'
        with self.assertRaises(ValueError):self.chunks()

    def test_captured_html_parser_uses_metadata_cells_and_links(self):
        p=MetadataHTML()
        p.feed('<table><tr><td>Số ký hiệu</td><td>36/2024/QH15</td></tr></table><a href="https://example.invalid/a.pdf">PDF</a>')
        self.assertEqual(p.values['Số ký hiệu'],'36/2024/QH15')
        self.assertEqual(p.links,['https://example.invalid/a.pdf'])
        with self.assertRaises(ValueError):p.feed('<tr><td>Số ký hiệu</td><td>OTHER</td></tr>')

    def test_token_budget_failure_is_explicit_no_truncation(self):
        chunks,contexts=self.chunks()
        token={'limit':1,'rows':[{'within_limit':False}]*3}
        report=validation_report(chunks,contexts,token)
        self.assertTrue(report['technical_valid']);self.assertFalse(report['processing_success'])
        self.assertFalse(report['release_eligible']);self.assertEqual(chunks[0]['text_original'],next(u['text_original'] for u in self.data['units'] if u['unit_id']==chunks[0]['unit_id']))

    def test_import_is_side_effect_free(self):
        script='''
import importlib,sys
def audit(e,a):
 if e.startswith(('socket.','sqlite3.connect','subprocess.Popen')):raise AssertionError(e)
 if e=='open' and ((isinstance(a[1],str) and any(c in a[1] for c in 'wax+')) or (a[2]&3)):raise AssertionError('write')
sys.addaudithook(audit)
importlib.import_module('src.preview_tokens');importlib.import_module('src.article22_preview')
assert not any(x in sys.modules for x in ['torch','transformers','pdfplumber'])
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless((default_tokenizer_dir()/'bpe.codes').is_file(),'Pinned local tokenizer not present')
    def test_offline_tokenizer_exact_counts_no_inference_and_no_truncation(self):
        texts=['Không được bỏ từ phủ định.','Không được bỏ từ phủ định. '*300]
        result=count_tokens(texts,default_tokenizer_dir())
        self.assertEqual(result['counts'][0]['tokens_with_special'],9)
        self.assertGreater(result['counts'][1]['tokens_with_special'],256)
        self.assertFalse(result['truncation']);self.assertFalse(result['inference_loaded']);self.assertFalse(result['network_used'])
        self.assertEqual(set(inspect_assets(default_tokenizer_dir())),set(ASSETS))


@unittest.skipUnless(os.environ.get('VTLS_ARTICLE22_PREVIEW_MANIFEST'),'Supply real preview for post-reseal checks')
class RealPreviewChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='test-preview-real-',dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name)/'copy'
        shutil.copytree(Path(os.environ['VTLS_ARTICLE22_PREVIEW_MANIFEST']).resolve().parent,self.run)
        self.manifest=self.run/'manifest.json'

    def reseal(self):
        m=load_json(self.manifest);m['files']=inventory(self.run)
        self.manifest.write_text(canonical(m)+'\n',encoding='utf8')
        (self.run/'manifest.sha256').write_text(digest(self.manifest.read_bytes())+'\n',encoding='ascii')

    def local_validate(self):
        # Isolate downstream replay; full upstream/real tokenizer replay runs via CLI.
        with patch('src.article22_preview.validate_mapping',return_value={'technical_valid':True}):
            return validate(self.manifest)

    def test_real_chunks_and_agent_review_remain_pending_without_human_events(self):
        r=self.local_validate();self.assertTrue(r['token_limit_passed']);self.assertEqual(r['chunk_count'],3)
        self.assertEqual(r['human_reviewer_event_count'],0);self.assertFalse(r['corpus_created'])
        review=load_json(self.run/'agent_review.json');self.assertEqual(review['origin'],'agent_review')
        self.assertFalse(review['human_review_claimed']);self.assertIsNone(review['applicability_analysis']['decision'])

    def test_tampered_context_after_reseal_fails(self):
        p=self.run/'contexts.preview.jsonl';rows=read_rows(p);rows[0]['char_start']=1
        p.write_text('\n'.join(canonical(r) for r in rows)+'\n',encoding='utf8');self.reseal()
        with self.assertRaises(ValueError):self.local_validate()

    def test_verified_status_after_reseal_fails(self):
        p=self.run/'chunks.preview.jsonl';rows=read_rows(p);rows[0]['applicability_status']='verified_at_snapshot'
        p.write_text('\n'.join(canonical(r) for r in rows)+'\n',encoding='utf8');self.reseal()
        with self.assertRaises(ValueError):self.local_validate()

    def test_false_token_counts_after_reseal_fail(self):
        p=self.run/'token_report.json';report=load_json(p)
        report['rows'][0]['text_for_search']['tokens_with_special']=1
        p.write_text(canonical(report),encoding='utf8');self.reseal()
        with self.assertRaises(ValueError):self.local_validate()

    def test_agent_review_cannot_be_submitted_as_human_form(self):
        from src.article22_draft import compile_review
        review=load_json(self.run/'agent_review.json')
        with self.assertRaises((ValueError,KeyError,TypeError)):
            compile_review(review,{'source_events':[],'unit_events':[]},{},[],{}, {'form_only':True},{})


if __name__=='__main__':unittest.main()
