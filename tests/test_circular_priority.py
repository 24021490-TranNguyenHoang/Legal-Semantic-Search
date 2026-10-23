"""Synthetic fixtures only; no legal or human verification claims."""
import copy
import tempfile
import unittest
from pathlib import Path
from src.ingestion.circular_priority import graph, validate_graph
from src.ingestion.legal_tree import unit_id, span_id
from src.experimental_dataset import write_rows,write_json
from src.source_contracts import digest,canonical


class GraphTests(unittest.TestCase):
    def fixture(self,base):
        text='Phần I\nTên một\nChương I\nTên chương\nA\na\nPhần II\nTên hai\nChương I\nTên chương\nB\nb'
        def unit(kind,d,parent,title,body,path):
            u={'law_id':'FIXTURE/CIRCULAR','unit_type':kind,'designation':d,'parent_unit_id':parent,'title':title,'text_original':body,
               'text_sha256':digest(body.encode()),'ordinal':0,'canonical_path':path,'citation_path':path};u['unit_id']=unit_id(u);return u
        root=unit('document','FIXTURE/CIRCULAR',None,'','','document:FIXTURE/CIRCULAR')
        a=unit('article','1',root['unit_id'],'A','a','document:FIXTURE/CIRCULAR/article:1')
        b=unit('article','2',root['unit_id'],'B','b','document:FIXTURE/CIRCULAR/article:2')
        ss=[]
        for u in [a,b]:
            for f in ['title','text_original']:
                start=text.index('\n'+u[f]+'\n')+1 if u[f]!='b' else len(text)-1
                s={'unit_id':u['unit_id'],'extraction_id':'FIXTURE/e','field_name':f,'span_order':0,'char_start':start,'char_end':start+1,
                    'locator_json':'{}','quote_sha256':digest(u[f].encode())};s['span_id']=span_id(s);ss.append(s)
        lines=[];offset=0
        for value in text.splitlines():
            if value.startswith(('Phần','Chương','Tên')):lines.append({'text':value,'char_start':offset,'char_end':offset+len(value),'locator':{}})
            offset+=len(value)+1
        deps=[]
        for u,p,c in [(a,0,2),(b,4,6)]:deps.append({'unit_id':u['unit_id'],'source_ancestors':[{'source_lines':[lines[p]]},{'source_lines':[lines[c]]}]})
        write_rows(base/'legal_units.pending.jsonl',[root,a,b]);write_rows(base/'source_spans.pending.jsonl',ss)
        write_rows(base/'structure.pending.jsonl',lines);write_rows(base/'unit_structure_dependencies.jsonl',deps)
        (base/'extraction_snapshot').mkdir();(base/'extraction_snapshot/text.txt').write_text(text,encoding='utf8')
        write_rows(base/'extraction_snapshot/extractions.pending.jsonl',[{'extraction':{'extraction_id':'FIXTURE/e','text_ref':'text.txt'}}])
        # Root has no spans; assign extraction lookup using an empty root title span
        # lookup in graph selects root extraction, so provide a real source title.
        root['title']='Phần I';root['unit_id']=unit_id(root)
        for u in [a,b]:u['parent_unit_id']=root['unit_id']
        s={'unit_id':root['unit_id'],'extraction_id':'FIXTURE/e','field_name':'title','span_order':0,'char_start':0,'char_end':6,'locator_json':'{}','quote_sha256':digest('Phần I'.encode())};s['span_id']=span_id(s)
        write_rows(base/'legal_units.pending.jsonl',[root,a,b]);write_rows(base/'source_spans.pending.jsonl',[s,*ss])
        return {'FIXTURE/e':text}

    def test_repeated_chapters_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);texts=self.fixture(base);us,ss,cross,mapping=graph(base)
            chapters=[u for u in us if u['unit_type']=='chapter']
            self.assertEqual(len(chapters),2);self.assertNotEqual(chapters[0]['unit_id'],chapters[1]['unit_id'])
            self.assertIn('/part:I/chapter:I',chapters[0]['canonical_path'])
            self.assertIn('/part:II/chapter:I',chapters[1]['canonical_path'])
            validate_graph(us,ss,texts)
            self.assertEqual(graph(base),(us,ss,cross,mapping))

    def test_wrong_parent_and_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);texts=self.fixture(base);us,ss,_,_=graph(base)
            bad=copy.deepcopy(us);bad[-1]['parent_unit_id']=bad[-1]['unit_id']
            with self.assertRaises(ValueError):validate_graph(bad,ss,texts)
            bad=copy.deepcopy(ss);bad[-1]['quote_sha256']='0'*64
            with self.assertRaises(ValueError):validate_graph(us,bad,texts)

    def test_missing_span_and_duplicate_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);texts=self.fixture(base);us,ss,_,_=graph(base)
            with self.assertRaises(ValueError):validate_graph(us,ss[:-1],texts)
            with self.assertRaises(ValueError):validate_graph(us+[us[-1]],ss,texts)


if __name__=='__main__':unittest.main()
