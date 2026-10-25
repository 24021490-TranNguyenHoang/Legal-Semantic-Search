"""Synthetic data only; no model inference or legal verification."""
import copy
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from tests.test_stage3 import pdf_fixture
from src.source_contracts import canonical, digest
from src.experimental_dataset import load, write_json,write_rows
from src.ingestion import full_source, encoder_views, source_regions, ocr_pages
from src.ingestion.completion_records import sibling_table_dispositions,form_identity
from src.ingestion.completion_ledger import partition,legal_position,discover_extractions
from src.ingestion.qcvn_graph import graph
from src import seven_dataset_portable as portable
from src.full_ingestion import preflight_ocr
from src.full_ingestion import source_scan,run_path
from unittest.mock import patch
from src.assessment_evidence import seal


def encode(texts):
    result=[]
    for t in texts:
        tokens=[0]+list(range(4,4+len(t.split())))+[2]
        result.append({'input_sha256':digest(t.encode()),'tokens_with_special':len(tokens),
            'model_max_tokens':256,'truncation':False,'unknown_tokens':0,'encoder_text':t,
            'role':'document','preprocessing_version':'phobert-pyvi-input.v1',
            'encoder_text_sha256':digest(t.encode()),'after':{'token_ids':tokens,
                'token_ids_sha256':digest(canonical(tokens).encode())}})
    return result


class FullIngestionTests(unittest.TestCase):
    def test_new_modules_import_without_writes_network_subprocess_or_pipeline(self):
        script='''
import sys,os
def guard(event,args):
    if event in {'socket.connect','subprocess.Popen','os.mkdir','os.remove','os.rename'}:
        raise AssertionError('Import side effect: '+event)
    if event=='open' and isinstance(args[2],int) and args[2] & (os.O_CREAT|os.O_TRUNC|os.O_WRONLY|os.O_RDWR):
        raise AssertionError('Import file write')
sys.addaudithook(guard)
import src.full_ingestion,src.seven_dataset_portable
from src.ingestion import full_source,full_graph,full_preview,encoder_views,source_regions,ocr_pages,qcvn_graph,completion_records,completion_repairs,completion_dataset,completion_ledger
'''
        p=subprocess.run([sys.executable,'-X','utf8','-B','-c',script],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(p.returncode,0,p.stderr)

    def test_pdf_resume_checks_hashes_and_empty_page(self):
        with tempfile.TemporaryDirectory(dir='staging') as temp:
            root=Path(temp);raw=root/'fixture.pdf';pdf_fixture(raw)
            f={'local_ref':raw.as_posix(),'file_id':'FIXTURE-PDF','law_id':'FIXTURE/1','sha256':digest(raw.read_bytes())}
            cp=full_source.scan_pdf(f,root/'pages',stop_after=1)
            self.assertEqual(cp['state'],'IN_PROGRESS')
            full_source.scan_pdf(f,root/'pages',resume=True)
            empty=load(root/'pages/FIXTURE-PDF/page-0002.json')
            self.assertIn('NO_TEXT_NOT_BLANK_DECISION',empty['blockers'])
            rec=full_source.extraction_from_pages(f,root/'pages',root)
            self.assertEqual(rec['source_status'],'pending')
            page=root/'pages/FIXTURE-PDF/page-0001.json';value=load(page)
            value['reader_text']='tampered';write_json(page,value)
            with self.assertRaisesRegex(ValueError,'tampered'):
                full_source.scan_pdf(f,root/'pages',resume=True)

    def test_views_cover_whole_content_and_do_not_become_targets(self):
        text=' '.join(['Không được vượt quá 50 km/h;']*100)
        r={'text_for_search':text,'text_original':'Không được vượt quá 50 km/h;','scope_proposal':'pending'}
        result,bad=encoder_views.prepare([r],encode)
        self.assertFalse(bad);self.assertEqual(len(result),1)
        record=result[0];self.assertGreater(len(record['encoder_views']),1)
        self.assertEqual(''.join(v['input_text'] for v in record['encoder_views']),text)
        self.assertEqual(record['source_record'],r)
        self.assertTrue(all(v['encoding']['tokens_with_special']<=256 and not v['independent_target'] for v in record['encoder_views']))
        for field in ['text_original','content_sha256']:
            changed=copy.deepcopy(record);changed[field]='tampered'
            with self.assertRaises(ValueError):encoder_views.validate(changed)
        changed=copy.deepcopy(record);changed['encoder_views'][0]['search_char_end']-=1
        with self.assertRaises(ValueError):encoder_views.validate(changed)

    def test_unsplittable_sentence_is_quarantined(self):
        r={'text_for_search':' '.join(['synthetic']*300),'text_original':'synthetic'}
        result,bad=encoder_views.prepare([r],encode)
        self.assertFalse(result);self.assertEqual(bad[0]['record'],r)
        self.assertEqual(bad[0]['reason'],'SINGLE_SOURCE_SENTENCE_OR_FIELD_EXCEEDS_BUDGET')

    def test_absolute_pdf_region_offsets(self):
        t='previous page\nđúng nguồn'
        n={'char_start':14,'char_end':len(t),'locator':{'format':'pdf','page_start':2,'page_end':2}}
        p=source_regions.proof({'extraction_id':'FIXTURE-E','file_id':'FIXTURE-F'},n,0,len(t)-14,t,[1,2,3,4])
        source_regions.validate_proof(p,t)
        self.assertEqual(p['quote'],'đúng nguồn')
        p['char_start']=0
        with self.assertRaises(ValueError):source_regions.validate_proof(p,t)

    def test_ocr_draft_does_not_replace_reader_or_claim_review(self):
        with tempfile.TemporaryDirectory(dir='staging') as temp:
            root=Path(temp);(root/'draft.txt').write_bytes('đúng nguồn\r\n'.encode())
            (root/'normalized.txt').write_bytes('đúng nguồn\n'.encode())
            r={'config':{'policy':'FIXTURE'},'source_sha256':'sha','file_id':'FIXTURE','pdf_page':1,
                'origin':'agent_review','review_status':'pending',
                'artifacts':{n:digest((root/n).read_bytes()) for n in ['draft.txt','normalized.txt']},
                'words':[{'char_start':0,'char_end':4,'text':'đúng'}]}
            ocr_pages.validate_result(r,root,{'sha256':'sha','file_id':'FIXTURE'},r['config'],1)
            r['review_status']='verified'
            with self.assertRaises(ValueError):ocr_pages.validate_result(r,root,{'sha256':'sha','file_id':'FIXTURE'},r['config'],1)

    def test_sibling_table_is_unrelated_only_when_source_ranges_prove_it(self):
        units=[{'unit_id':uid,'parent_unit_id':parent,'unit_type':kind} for uid,parent,kind in
               [('doc',None,'document'),('article','doc','article'),('clause','article','clause'),('a','clause','point'),('c','clause','point')]]
        spans=[{'unit_id':uid,'char_start':a,'char_end':b,'extraction_id':'FIXTURE'} for uid,a,b in
               [('article',0,10),('clause',10,20),('a',20,30),('c',40,45)]]
        issue={'code':'TABLE_STRUCTURE_NOT_PARSED','char_start':46,'char_end':50,'extraction_id':'FIXTURE'}
        data={'units':units,'spans':spans,'issues':[issue]}
        kept,notes=sibling_table_dispositions(data,units[-2]);self.assertFalse(kept);self.assertEqual(len(notes),1)
        kept,notes=sibling_table_dispositions(data,units[-1]);self.assertEqual(kept,[issue])
        data['issues']=[{**issue,'code':'DUPLICATE_POINT_MARKER'}]
        self.assertEqual(len(sibling_table_dispositions(data,units[-2])[0]),1)
        data['issues']=[issue];spans[1]['char_end']=49
        self.assertEqual(len(sibling_table_dispositions(data,units[-2])[0]),1)

    def test_qcvn_annex_reference_does_not_end_body_or_invent_clauses(self):
        values=['PHẦN 1: QUY ĐỊNH CHUNG','Điều 62. Quy cách','62.1. Thực hiện theo','Phụ lục I.',
                '62.2. Không được bỏ điều kiện.','Điều 63. Cọc H','63.1. Nội dung.','Phụ lục I','TÊN PHỤ LỤC']
        regions=[{'region_id':str(i),'content':v,'source_proof':{'file_id':'FIXTURE','char_start':i*100,
            'locator':{'page_start':5},'quote':v}} for i,v in enumerate(values)]
        nodes,disp,issues=graph(regions,[{'file_id':'FIXTURE','part_order':1}])
        self.assertEqual([n['designation'] for n in nodes if n['kind']=='article'],['62','63'])
        self.assertEqual(len([n for n in nodes if n['kind']=='annex']),1)
        self.assertIn('Phụ lục I.',next(n['text_original'] for n in nodes if n['designation']=='62.1'))
        self.assertFalse(any(n['kind']=='clause' for n in nodes));self.assertFalse(issues)

    def test_qcvn_unreadable_serial_annex_boundary_is_not_guessed(self):
        values=[('one','PHẦN 1: QUY ĐỊNH CHUNG'),('one','Điều 1. Fixture'),('one','Phụ lục K'),
                ('one','K.1 Nội dung nguồn thứ nhất'),('two','Một nhãn bảng dưới heading không đọc được'),
                ('two','Phụ lục P'),('two','P.1 Nội dung nguồn thứ hai')]
        rr=[{'region_id':str(i),'content':v,'source_proof':{'file_id':f,'char_start':i*100,'locator':{'page_start':5},'quote':v}} for i,(f,v) in enumerate(values)]
        nodes,disp,issues=graph(rr,[{'file_id':'one','part_order':1},{'file_id':'two','part_order':2}])
        k=next(n for n in nodes if n['kind']=='annex' and n['designation']=='K')
        self.assertNotIn('Một nhãn bảng',k['text_original'])
        self.assertIn({'region_id':'4','disposition':'UNRESOLVED_ANNEX_CONTINUATION_OR_IMAGE_HEADING'},disp)
        self.assertFalse(any(n['designation']=='M' for n in nodes))
        legacy,_,_=graph(rr,[{'file_id':'one','part_order':1},{'file_id':'two','part_order':2}],legacy_serial_annexes=True)
        self.assertIn('Một nhãn bảng',next(n['text_original'] for n in legacy if n['kind']=='annex' and n['designation']=='K'))

    def test_partition_keeps_overlapping_facets_and_unprocessed_text(self):
        text='đúng\nnguồn thiếu';r=partition(text,[{'char_start':0,'char_end':4,'category':'parsed'},
            {'char_start':1,'char_end':3,'category':'review'}])
        self.assertEqual(''.join(text[x['char_start']:x['char_end']] for x in r),text)
        self.assertTrue(any(len(x['coverage_refs'])==2 for x in r))
        self.assertTrue(any(x['disposition']=='unprocessed_no_existing_disposition' for x in r))
        self.assertEqual(legal_position('document:FIXTURE/part:II/chapter:I/article:2/clause:1'),'article:2/clause:1')

    def test_portable_view_validator_rejects_identity_or_budget_evasion(self):
        r=encoder_views.prepare([{'text_for_search':'Không được bỏ điều kiện; giữ đủ nguồn.','text_original':'nguyên văn'}],encode)[0][0]
        portable.check_views(r)
        for change in ['identity','budget','truncation']:
            bad=copy.deepcopy(r)
            if change=='identity':bad['identity']['views'][0]['search_char_end']-=1
            elif change=='budget':bad['encoder_views'][0]['encoding']['tokens_with_special']=257
            else:bad['encoder_views'][0]['encoding']['truncation']=True
            with self.assertRaises(ValueError):portable.check_views(bad)

    def test_form_identity_excludes_review_time_but_binds_layout(self):
        f={'law_id':'FIXTURE/FORM','citation_path':'FIXTURE form','source_raw_sha256':'raw','extraction_id':'FIXTURE-E',
            'char_start':0,'char_end':5,'text_original':'field','form_fields':[{'text_original':'field','bbox':[1,2,3,4]}],
            'visual_review':{'reviewed_at':'time1'}}
        a=form_identity(f);f['visual_review']['reviewed_at']='time2';self.assertEqual(a,form_identity(f))
        f['form_fields']=copy.deepcopy(f['form_fields']);f['form_fields'][0]['bbox']=[1,2,3,5]
        self.assertNotEqual(a,form_identity(f))

    def test_discovery_reports_bad_copy_without_admitting_or_poisoning_good_source(self):
        with tempfile.TemporaryDirectory(dir='staging') as temp:
            root=Path(temp);paths=[]
            for name,actual in [('good','source'),('negative-copy','tampered')]:
                folder=root/name;folder.mkdir();(folder/'normalized.txt').write_text(actual,encoding='utf8')
                (folder/'trace.json').write_text('{}',encoding='utf8')
                record={'source_raw_sha256':'FIXTURE-RAW','extraction':{'file_id':'FIXTURE-F','extraction_id':'FIXTURE-E',
                    'text_ref':'normalized.txt','text_sha256':digest(b'source')},'trace_ref':'trace.json','trace_sha256':digest(b'{}')}
                path=folder/'extractions.pending.jsonl';write_rows(path,[record]);paths.append(path)
            found,rejected=discover_extractions(paths,{'FIXTURE-RAW'})
            self.assertEqual(len(found),1);self.assertEqual(len(rejected),1)
            self.assertFalse(rejected[0]['admitted']);self.assertIn('negative-copy',rejected[0]['records_ref'])
            self.assertEqual(next(iter(found.values()))['reference']['text_ref'],(root/'good/normalized.txt').as_posix())

    def test_ocr_resume_preflight_checks_actual_raw_outside_manifest(self):
        with tempfile.TemporaryDirectory(dir='staging') as temp:
            root=Path(temp);raw=root/'fixture.pdf';pdf_fixture(raw);source=root/'source';source.mkdir()
            write_rows(source/'files.pending.jsonl',[{'local_ref':raw.as_posix(),'sha256':digest(raw.read_bytes())}])
            seal(source,{'manifest_type':'FIXTURE-ONLY'})
            preflight_ocr(source/'manifest.json')
            raw.write_bytes(b'changed fixture')
            with self.assertRaisesRegex(ValueError,'OCR source checksum'):
                preflight_ocr(source/'manifest.json')

    def test_portable_pdf_locator_and_complete_form_fields(self):
        with tempfile.TemporaryDirectory(dir='staging') as temp:
            root=Path(temp);raw=root/'fixture.pdf';pdf_fixture(raw)
            file={'local_ref':raw.as_posix(),'file_id':'FIXTURE-F','law_id':'FIXTURE/FORM','sha256':digest(raw.read_bytes())}
            full_source.scan_pdf(file,root/'pages');rec=full_source.extraction_from_pages(file,root/'pages',root)
            e=rec['extraction'];trace=load(root/rec['trace_ref']);page=next(n for n in trace['nodes'] if n['kind']=='page')
            text=(root/e['text_ref']).read_text(encoding='utf8');cache=load(root/'pages/FIXTURE-F/page-0001.json')
            line=cache['lines'][0];p=source_regions.proof(e,page,0,len(line['text']),text,line['bbox'])
            identity_ref=str(Path(rec['trace_ref']).with_name('identity.json')).replace('\\','/')
            refs=['fixture.pdf',e['text_ref'],rec['trace_ref'],identity_ref]
            m={'proof_mounts':{ref:ref for ref in refs},'extraction_bindings':{e['extraction_id']:{
                'file_id':e['file_id'],'source_raw_sha256':file['sha256'],'text_ref':e['text_ref'],'text_sha256':e['text_sha256'],
                'trace_ref':rec['trace_ref'],'trace_sha256':rec['trace_sha256'],'identity_ref':identity_ref}}}
            direct={**p,'raw_ref':'fixture.pdf','raw_sha256':file['sha256'],'text_ref':e['text_ref'],'text_sha256':e['text_sha256']}
            portable.direct_proof(root,m,direct)
            wrong=copy.deepcopy(direct);wrong['locator']['page_start']=2
            with self.assertRaisesRegex(ValueError,'locator'):portable.direct_proof(root,m,wrong)
            form={'record_type':'form-retrieval.v1','law_id':'FIXTURE/FORM','citation_path':'FIXTURE form',
                'source_raw_sha256':file['sha256'],'file_id':file['file_id'],'extraction_id':e['extraction_id'],
                'char_start':p['char_start'],'char_end':p['char_end'],'text_original':p['quote'],
                'text_sha256':p['quote_sha256'],'raw_ref':'fixture.pdf','text_ref':e['text_ref'],
                'form_fields':[{'source_region_id':'FIXTURE-LINE','text_original':p['quote'],'source_proof':p,'role':'source_label_or_instruction'}],
                'origin':'agent_review','visual_review':{'origin':'agent_review'},'release_eligible':False,
                'applicability':'pending_review','required_capabilities':['form-layout-read.v1']}
            form['identity']=form_identity(form);form['record_id']='fr_'+digest(canonical(form['identity']).encode())
            portable.check_form(root,m,form)
            missing=copy.deepcopy(form);missing['form_fields']=[];missing['identity']=form_identity(missing)
            missing['record_id']='fr_'+digest(canonical(missing['identity']).encode())
            with self.assertRaisesRegex(ValueError,'Missing form'):portable.check_form(root,m,missing)
            false_review=copy.deepcopy(form);false_review['visual_review']['origin']='human_review'
            with self.assertRaisesRegex(ValueError,'origin'):portable.check_form(root,m,false_review)

    def test_run_scope_missing_input_and_serialization_interruption_resume(self):
        with tempfile.TemporaryDirectory(dir='staging') as temp:
            root=Path(temp);raw=root/'fixture.pdf';pdf_fixture(raw)
            metadata=root/'source_metadata.jsonl';write_rows(metadata,[])
            cfg=root/'config.json';write_json(cfg,{'snapshot_date':'2025-01-01','metadata_manifest':str(root/'manifest.json')})
            target=root/'scan'
            with self.assertRaisesRegex(ValueError,'No registered PDF'):source_scan(cfg,target,law_id='FIXTURE')
            self.assertFalse(target.exists())
            with self.assertRaises(ValueError):run_path('data/raw/new-fixture-must-not-exist')
            write_rows(metadata,[{'file_id':'FIXTURE-F','law_id':'FIXTURE','file_role':'main','local_ref':raw.as_posix(),'sha256':digest(raw.read_bytes())}])
            original=full_source.extraction_from_pages
            def interrupted(*args):
                original(*args);raise InterruptedError('Synthetic stop after serialization')
            with patch.object(full_source,'extraction_from_pages',side_effect=interrupted):
                with self.assertRaises(InterruptedError):source_scan(cfg,target,law_id='FIXTURE')
            before={p:p.read_bytes() for p in (target/'extractions').rglob('*') if p.is_file()}
            result=source_scan(cfg,target,resume=True,law_id='FIXTURE')
            self.assertEqual(result['pages'],2)
            self.assertTrue(all(p.read_bytes()==content for p,content in before.items()))
            with self.assertRaisesRegex(ValueError,'Sealed'):source_scan(cfg,target,resume=True,law_id='FIXTURE')


if __name__=='__main__':unittest.main()
