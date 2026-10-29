"""Synthetic FIXTURE source/records only, not legal text or human decisions."""
import copy
from pathlib import Path
import tempfile
import unittest

from src import preview_read_check as r
from src.chunk_preview import chunk_identity
from src.ingestion.completion_records import form_identity
from src.ingestion.encoder_views import prepare
from src.source_session4 import check_plan


def encoded(text):
    ids=[0,7,2]
    return {'input_sha256':r.sha(text.encode()),'encoder_text':text,'encoder_text_sha256':r.sha(text.encode()),
            'truncation':False,'tokens_with_special':3,'after':{'token_ids':ids,'token_ids_sha256':r.sha(r.canonical(ids).encode())}}


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.text='FIXTURE title\nFIXTURE lead:\na) FIXTURE target.\nFIXTURE instruction.'
        self.loc={'format':'pdf','page_start':1,'page_end':1,'width':100,'height':100}
        trace={'nodes':[{'locator':self.loc,'char_start':0,'char_end':len(self.text)}]}
        raw=b'FIXTURE raw only';self.ident={'identity_schema':'extraction.v1','file_id':'FIXTURE-file',
            'source_raw_sha256':r.sha(raw),'text_sha256':r.sha(self.text.encode()),'trace_content_sha256':r.sha(r.canonical(trace).encode())}
        (self.root/'raw').write_bytes(raw);(self.root/'text').write_text(self.text,encoding='utf8',newline='\n')
        (self.root/'trace').write_text(r.canonical(trace),encoding='utf8')
        self.proofs=[];self.contexts=[]
        for i,t in enumerate(['FIXTURE title','FIXTURE lead:']):
            self.proofs.append(self.proof(t,'context:'+str(i)))
            self.contexts.append({'unit_id':'FIXTURE-parent','field_name':'title'if i==0 else 'text_original','char_start':0,'char_end':len(t),
                                  'context_role':'FIXTURE','context_order':i,'text_original':t})
        target='a) FIXTURE target.';self.proofs.append(self.proof(target,'target'))
        chunk={'unit_id':'FIXTURE-unit','segment_no':0,'unit_char_start':0,'unit_char_end':len(target),'text_original':target,
               'chunk_policy_version':'FIXTURE-policy','law_id':'FIXTURE/law','law_title':'FIXTURE law','citation_path':'FIXTURE article1 pointa',
               'source_url':None,'effective_from':None,'effective_to':None,'applicability_status':None,'context_text':'FIXTURE title\nFIXTURE lead:'}
        chunk['text_for_search']='\n\n'.join([chunk['law_title'],chunk['citation_path'],chunk['context_text'],target])
        chunk['content_sha256']=r.sha(chunk['text_for_search'].encode());chunk['chunk_id']='c_'+r.sha(r.canonical(chunk_identity(chunk,self.contexts)).encode())
        self.frame={'record_id':chunk['chunk_id'],'record_type':'chunk.v1','record':chunk,'contexts':self.contexts,
                    'encoding':encoded(chunk['text_for_search']),'native_proofs':self.proofs,'dependencies':[],'expected_dependency_ids':[],
                    'allowed_source_hashes':[self.ident['source_raw_sha256']],'required_capabilities':['chunk.v1','required-read.v1'],
                    'human_review':None,'release_eligible':False}
        self.caps={'chunk.v1','required-read.v1','form-retrieval.v1','source-retrieval.v1'}

    def proof(self,text,use):
        a=self.text.index(text)
        return {'raw_ref':'raw','raw_sha256':self.ident['source_raw_sha256'],'text_ref':'text','text_sha256':self.ident['text_sha256'],
                'trace_ref':'trace','identity_payload':self.ident,'extraction_id':'e_'+r.sha(r.canonical(self.ident).encode()),
                'file_id':'FIXTURE-file','char_start':a,'char_end':a+len(text),'quote':text,'quote_sha256':r.sha(text.encode()),'locator':self.loc,'use':use}

    def test_valid_roundtrip(self):
        self.assertTrue(r.check(self.root,self.frame,self.caps)['technical_valid'])

    def test_wrong_source_offset_locator_and_identity(self):
        for field,value in [('raw_sha256','wrong'),('char_start',1),('locator',{**self.loc,'page_start':2}),('file_id','OLD_file')]:
            with self.subTest(field=field),self.assertRaises(ValueError):r.proof(self.root,{**self.proofs[0],field:value})

    def test_missing_source_context_or_wrong_unit(self):
        for case in ['context','source','unit','content_hash']:
            f=copy.deepcopy(self.frame)
            if case=='context':f['native_proofs']=f['native_proofs'][1:]
            elif case=='source':f['allowed_source_hashes']=[]
            elif case=='unit':f['record']['unit_id']='OLD_unit'
            else:f['record']['content_sha256']='wrong'
            with self.subTest(case=case),self.assertRaises(ValueError):r.check(self.root,f,self.caps)

    def test_required_dependency_and_content_not_silently_omitted(self):
        f=copy.deepcopy(self.frame);f['expected_dependency_ids']=['FIXTURE-dep']
        with self.assertRaises(ValueError):r.check(self.root,f,self.caps)
        f['dependencies']=[{'dependency_id':'FIXTURE-dep','unit_ids':['FIXTURE-support']}]
        with self.assertRaisesRegex(ValueError,'omitted'):r.check(self.root,f,self.caps)
        f['dependency_units']=[{'unit_id':'FIXTURE-support','title':'FIXTURE title','text_original':'FIXTURE instruction.'}]
        f['native_proofs'] += [self.proof('FIXTURE title','dependency:FIXTURE-support:title'),self.proof('FIXTURE instruction.','dependency:FIXTURE-support:text_original')]
        r.check(self.root,f,self.caps)

    def test_consumer_type_and_frame_id(self):
        with self.assertRaisesRegex(ValueError,'capability'):r.check(self.root,self.frame,set())
        f=copy.deepcopy(self.frame);f['record_id']='OLD_record'
        with self.assertRaisesRegex(ValueError,'ID'):r.check(self.root,f,self.caps)

    def test_budget_and_no_truncation(self):
        for k,v in [('tokens_with_special',257),('truncation',True),('encoder_text','modified')]:
            f=copy.deepcopy(self.frame);f['encoding'][k]=v
            with self.subTest(field=k),self.assertRaises(ValueError):r.check(self.root,f,self.caps)

    def form(self):
        fs=[{'text_original':t,'source_proof':self.proof(t,'unused')}for t in self.text.split('\n')]
        form={'law_id':'FIXTURE/law','citation_path':'FIXTURE annex','source_raw_sha256':self.ident['source_raw_sha256'],
              'extraction_id':fs[0]['source_proof']['extraction_id'],'char_start':0,'char_end':len(self.text),'text_original':self.text,'form_fields':fs}
        form['record_id']='fr_'+r.sha(r.canonical(form_identity(form)).encode())
        f=copy.deepcopy(self.frame);f.update(record_id=form['record_id'],record_type='form-retrieval.v1',record=form,contexts=[],encoding=None,
           native_proofs=[self.proof(self.text,'form_page')]+[self.proof(x['text_original'],'form_field:'+str(i))for i,x in enumerate(fs)],
           required_capabilities=['form-retrieval.v1'])
        return f

    def test_form_full_page_and_instruction_coverage(self):
        f=self.form();r.check(self.root,f,self.caps)
        f['record']['form_fields'].pop();f['native_proofs'].pop()
        # Even a self-consistent rehashed form must not omit a printed instruction.
        f['record']['record_id']='fr_'+r.sha(r.canonical(form_identity(f['record'])).encode());f['record_id']=f['record']['record_id']
        with self.assertRaisesRegex(ValueError,'omitted'):r.check(self.root,f,self.caps)

    def test_views_keep_all_content_and_are_not_targets(self):
        original=self.frame['record'];wrapped,bad=prepare([original],lambda xs:[encoded(x)for x in xs])
        self.assertFalse(bad);r.views(wrapped[0])
        for case in ['gap','truncate','independent']:
            w=copy.deepcopy(wrapped[0]);v=w['encoder_views'][0]
            if case=='gap':v['search_char_end']-=1
            elif case=='truncate':v['encoding']['truncation']=True
            else:v['independent_target']=True
            with self.subTest(case=case),self.assertRaises(ValueError):r.views(w)

    def test_derived_table_row_also_requires_exact_encoder_budget(self):
        record={'record_type':'table-retrieval.v1','text_for_search':'FIXTURE derived row','original_source':'FIXTURE cells'}
        record['retrieval_id']='tr_'+r.sha(r.canonical(record).encode())
        f=copy.deepcopy(self.frame);f.update(record=record,record_id=record['retrieval_id'],record_type='table-retrieval.v1',
            native_proofs=[],contexts=[],required_capabilities=['table-retrieval.v1'],encoding=encoded(record['text_for_search']))
        caps=self.caps|{'table-retrieval.v1'};r.check(self.root,f,caps)
        f['encoding']['tokens_with_special']=257
        with self.assertRaisesRegex(ValueError,'budget'):r.check(self.root,f,caps)


class PlanTests(unittest.TestCase):
    def test_duplicate_branch_view_and_qcvn_caption(self):
        p={'record_id':'FIXTURE-DOCX','role':'target','record_type':'chunk.v1','law_id':'FIXTURE/law','canonical_path':'FIXTURE/article:1'}
        check_plan([p])
        for case in ['duplicate','view','caption','type']:
            a=copy.deepcopy(p);records=[a]
            if case=='duplicate':records.append({**p,'record_id':'FIXTURE-HTML'})
            elif case=='view':a['independent_encoder_view']=True
            elif case=='caption':a['source_conflict']=True;a['region_key']='R-caption-I416'
            else:a['record_type']='unsupported-type'
            with self.subTest(case=case),self.assertRaises(ValueError):check_plan(records)


if __name__=='__main__':unittest.main()
