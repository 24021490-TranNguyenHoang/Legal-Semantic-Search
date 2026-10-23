"""Synthetic fixtures; never evidence of legal review."""
import copy
import tempfile
import unittest
from pathlib import Path
from src.source_inventory import require_url, attachment_url, validate_csv_semantics
from src.experimental_dataset import write_json, csv_text
from src.ingestion.circular_layout import select_blocks, visible_object
from src.ingestion import circular_layout, legal_tree
from tests.test_tt38_layout import fixture
from src.tt38_preview import derive_rows
from src.ingestion.circular_reader import extract_annex, text_issues
from src.ingestion.extraction_normalizer import normalize_fragment
from src.source_contracts import digest
from src.config import STAGING_DIR
from tests.test_stage3 import pdf_fixture
from src.ingestion.circular_preview import structure_dependencies


class MetadataTests(unittest.TestCase):
    def test_scalar_url_only(self):
        for v in [{"value":"https://example.test/a"}, '{"value":"https://example.test/a"}', 'https://host/a b', 'file:///a', 'https://u:p@host/a', 'https://host/{json}', 'https://host/'+'a'*8200]:
            with self.subTest(value=str(v)[:30]),self.assertRaises(ValueError):require_url(v)
        self.assertIsNone(require_url(None))
        self.assertEqual(require_url('https://example.test/a?x=1&y=%2B'),'https://example.test/a?x=1&y=%2B')

    def test_legacy_requires_independent_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);url='https://example.test/a?x=1&y=2'
            wrapper={k:None for k in ['PSPath','PSParentPath','PSDrive','PSProvider','ReadCount']}
            wrapper.update(value=url,PSChildName='gazette_cdn_url.txt')
            rec={'official_attachment_url':wrapper,'law_id':'38/2024/TT-BGTVT','sha256':'fixture-hash','size_bytes':12,'new_capture_retrieved_at':'2026-10-22T00:00:00Z'}
            receipt={'url':wrapper,'sha256':'fixture-hash','size_bytes':12,'accessed_at':rec['new_capture_retrieved_at'],'valid_pdf':True,'http_status':200}
            write_json(p/'gazette_pdf_capture.json',receipt);(p/'tt38-congbao.html').write_text('<a href="https://example.test/a?x=1&amp;y=2">fixture</a>',encoding='utf8')
            self.assertEqual(attachment_url(rec,p),url)
            for key,value in [('sha256','wrong'),('law_id','35/2024/TT-BGTVT'),('new_capture_retrieved_at',None)]:
                bad={**rec,key:value}
                with self.assertRaises(ValueError):attachment_url(bad,p)
            (p/'tt38-congbao.html').write_text('unrelated',encoding='utf8')
            with self.assertRaises(ValueError):attachment_url(rec,p)

    def test_csv_default_reader_and_null(self):
        data=[{'download_url':None,'official_page_url':'https://example.test/a','retrieved_at':None},
              {'download_url':'https://example.test/b?x=1&y=2','official_page_url':'https://example.test/a','retrieved_at':'2026-10-22T00:00:00Z'}]
        value=csv_text(data,list(data[0]));validate_csv_semantics(value,data)
        with self.assertRaises(ValueError):validate_csv_semantics(value.replace('example.test/b','example.test/c'),data)


class ReaderTests(unittest.TestCase):
    def test_actual_pdfium_fixture_text_empty_page_and_repeatable_identity(self):
        with tempfile.TemporaryDirectory(dir=STAGING_DIR) as d:
            root=Path(d);pdf_fixture(root/'fixture.pdf');raw=(root/'fixture.pdf').read_bytes()
            source={'law_id':'FIXTURE/PDFIUM','file_id':'a1c416ee-4289-49d2-a771-69ca1896ae5b',
                    'measured':{'raw_file_ref':'fixture.pdf','sha256':digest(raw),'size_bytes':len(raw)}}
            a=extract_annex(source,root);b=extract_annex(source,root)
            self.assertEqual(a[0]['extraction']['extraction_id'],b[0]['extraction']['extraction_id'])
            self.assertEqual(a[1:4],b[1:4]);self.assertIn(b'50 km/h',a[1])
            self.assertEqual(a[0]['technical_status'],'complete');self.assertEqual(a[0]['extraction']['review_status'],'pending')
            self.assertEqual([q['code'] for q in a[4]],['PDF_PAGE_NO_TEXT'])
            self.assertEqual(a[4][0]['locator']['page_start'],2)
            bad=copy.deepcopy(source);bad['measured']['sha256']='0'*64
            with self.assertRaises(ValueError):extract_annex(bad,root)

    def test_noncharacters_preserved_and_are_errors(self):
        value='FIXTURE\x00 Không\ufffe được vượt 50 km/h.'
        self.assertEqual(normalize_fragment(value),value)
        q=text_issues(value,{'format':'pdf','page_start':7,'page_end':7})
        self.assertEqual([x['code'] for x in q],['PDF_READER_NONCHARACTER'])
        self.assertEqual(q[0]['severity'],'error')
        self.assertFalse(text_issues('FIXTURE ordinary text',{}))


class LayoutTests(unittest.TestCase):
    def line(self,text,n,bold=False):
        return {'text':text,'page':1,'line_index':n,'bold':bold,'bbox':[50,60+20*n,500,75+20*n],
                'char_start':100*n,'char_end':100*n+len(text),'locator':{'format':'pdf','page_start':1,'page_end':1}}

    def test_parts_preserved_separately_not_fake_chapters(self):
        lines=[self.line('Phần II',0,True),self.line('ĐÀO TẠO',1,True),self.line('Chương I',2,True),
               self.line('QUY ĐỊNH',3,True),self.line('Điều 5. Hình thức đào tạo',4,True),self.line('1. Fixture.',5)]
        original=copy.deepcopy(lines);blocks,support,structure=select_blocks(lines,[])
        self.assertEqual(len(structure),4);self.assertEqual(len(blocks),2)
        self.assertEqual(lines,original)

    def test_table_numbers_do_not_become_clauses(self):
        lines=[self.line('Điều 1. Fixture',0,True),self.line('1. Dẫn.',1),self.line('2. ô bảng',2),self.line('b) ô bảng',3)]
        table={'page':1,'table_id':'fixture','bbox':[40,95,510,140]}
        blocks,_,_=select_blocks(lines,[table])
        self.assertEqual([b['kind'] for b in blocks],['paragraph','paragraph','table'])
        self.assertEqual(len(blocks[-1]['lines']),2)

    def test_signature_and_reference(self):
        lines=[self.line('Điều 1. Fixture',0,True),self.line('Dẫn chiếu Điều 2 trong câu.',1),self.line('KT. BỘ TRƯỞNG',2),self.line('Tên fixture',3)]
        blocks,support,_=select_blocks(lines,[])
        self.assertEqual(len(blocks),2);self.assertEqual(len(support),2)
        self.assertEqual(blocks[-1]['lines'][0]['text'],'Dẫn chiếu Điều 2 trong câu.')

    def test_white_background_is_not_table_border(self):
        self.assertFalse(visible_object({'object_type':'rect','stroke':False,'fill':True,'non_stroking_color':1.0}))
        self.assertTrue(visible_object({'object_type':'rect','stroke':False,'fill':True,'non_stroking_color':0.0}))
        self.assertTrue(visible_object({'object_type':'char'}))

    def test_sparse_grammar_roundtrip_and_real_offsets(self):
        rec,text,trace,lines,_=fixture()
        result=circular_layout.parse(rec,text,trace,lines,[])
        self.assertEqual([u['unit_type'] for u in result['units']],['document','article','clause','point'])
        self.assertTrue(result['structure'])
        ancestry=structure_dependencies(result)
        self.assertEqual(len(ancestry),3)
        self.assertTrue(all(x['source_ancestors'][0]['kind']=='chương' for x in ancestry))
        self.assertTrue(all(x['source_ancestors'][0]['source_lines'][0]['text']=='Chương I' for x in ancestry))
        for u in result['units']:
            for f in ['title','text_original']:
                selected=sorted([s for s in result['spans'] if s['unit_id']==u['unit_id'] and s['field_name']==f],key=lambda s:s['span_order'])
                self.assertEqual(u[f],'\n'.join(text[s['char_start']:s['char_end']] for s in selected))
        self.assertFalse(legal_tree.validate_tree(result['units'],result['spans'],{rec['extraction']['extraction_id']:(rec,text,trace)},result['coverage']))

    def test_table_inequalities_and_units_are_literal(self):
        units=[{'unit_id':'fixture-root','unit_type':'document','parent_unit_id':None},
               {'unit_id':'fixture-a','unit_type':'article','parent_unit_id':'fixture-root','title':'FIXTURE','text_original':'khô ráo'},
               {'unit_id':'fixture-c','unit_type':'clause','parent_unit_id':'fixture-a','title':'','text_original':'FIXTURE dưới 60 giữ riêng'}]
        vals=['Tốc độ (V km/h)','Khoảng cách (m)','60 < V ≤ 80','55']
        cells=[{'cell_id':str(i),'text':v} for i,v in enumerate(vals)]
        table={'table_id':'fixture-table','number':3,'context_unit_id':'fixture-c','cell_slots':[['0','1'],['2','3']]}
        result=derive_rows([table],cells,units)[0]
        self.assertIn('60 < V ≤ 80',result['text_derived']);self.assertIn('(m): 55',result['text_derived'])
        self.assertEqual(result['source_cell_ids'],['0','2','1','3'])
        self.assertIn('dưới 60',result['owner_lead_original'])


if __name__=='__main__':unittest.main()
