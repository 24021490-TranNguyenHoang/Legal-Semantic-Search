"""Offline integration checks for real pending artifacts; never a legal approval."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from src.experimental_dataset import load,rows,write_json
from src.source_contracts import digest,canonical
from src.assessment_evidence import check_files
from src.ingestion import full_source,full_graph,ocr_pages


def preservation(baseline):
    expected=load(baseline);bad=[];docs=[]
    allowed_documents={'AGENTS.md','README.md','docs/progress/STATUS.md','docs/ingestion.md'}
    for ref,h in expected.items():
        p=Path(ref)
        actual=digest(p.read_bytes()) if p.is_file() else None
        if actual!=h:
            if ref.replace('\\','/') in allowed_documents and actual is not None:
                docs.append({'ref':ref,'before_sha256':h,'after_sha256':actual,'reason':'Explicitly authorized current instructions/status/handoff documentation update'})
            else:bad.append(ref)
    if bad:raise ValueError('Protected artifacts changed: '+str(bad))
    return {'checked_files':len(expected),'changed_protected_artifacts':[],'authorized_document_changes':docs}


def page_evidence(root):
    root=Path(root);check_files(root/'manifest.json');count=0
    for f in rows(root/'files.pending.jsonl'):
        if digest(Path(f['local_ref']).read_bytes())!=f['sha256']:raise ValueError('Raw source changed')
        cp=load(root/'pages'/f['file_id']/'checkpoint.json')
        for n in range(1,cp['total_pages']+1):
            p=root/'pages'/f['file_id']/f'page-{n:04d}.json'
            if digest(p.read_bytes())!=cp['pages'][str(n)]:raise ValueError('Page checkpoint checksum mismatch')
            full_source.validate_page(load(p),f,n);count+=1
    return {'pages':count,'review':'reader/layout checks only'}


def ocr_drafts(root,source):
    root=Path(root);check_files(Path(source)/'manifest.json');cfg=load(root/'config.json');cp=load(root/'checkpoint.json')
    files={f['file_id']:f for f in rows(Path(source)/'files.pending.jsonl')}
    low=0;unmapped=0
    for p in cp['pages']:
        path=root/p['result_ref'];r=load(path);ocr_pages.validate_result(r,path.parent,files[p['file_id']],cfg,p['pdf_page'])
        low+=r['low_confidence_words'];unmapped+=r['unmapped_words']
    return {'pages':len(cp['pages']),'checkpoint_state':cp['state'],'low_confidence_words':low,'unmapped_words':unmapped,
        'target_quality_gate':'failed; drafts only; not added to candidate'}


def amendment_cells(output):
    old=rows('staging/seven-source-repairs-001/amendment_tables.jsonl')
    new=sorted(rows('staging/law35-pdf-regions-001/tables.jsonl'),key=lambda t:(t['page'],t['bbox'][1]))
    cells=rows('staging/law35-pdf-regions-001/cells.jsonl');comparisons=[]
    if len(old)!=2 or len(new)!=2:raise ValueError('Amendment table source count changed; inspect before matching')
    for before,after in zip(sorted(old,key=lambda t:t['table_index']),new):
        cc=[c for c in cells if c['table_id']==after['table_id']]
        if {(c['row'],c['column']) for c in cc}!={(c['row'],c['column']) for c in before['cells']}:raise ValueError('Amendment table row/column shape differs')
        for c in before['cells']:
            match=next(x for x in cc if (x['row'],x['column'])==(c['row'],c['column']))
            same=' '.join(c['text_original'].split())==' '.join(match['text'].split())
            comparisons.append({'table_index':before['table_index'],'row':c['row'],'column':c['column'],
                'docx_text_original':c['text_original'],'pdf_text_original':match['text'],
                'comparison':'identical' if c['text_original']==match['text'] else 'whitespace_only' if same else 'content_difference',
                'docx_source_proof':c['source_proof'],'pdf_cell_id':match['cell_id'],'pdf_source_slices':match['source_slices'],
                'pdf_bbox':match['bbox'],'pdf_page':match['page'],'pdf_source_sha256':match['source_raw_sha256'],
                'origin':'agent_review','review_status':'pending'})
    write_json(output,comparisons)
    return {'tables':2,'cells':len(comparisons),'comparisons':dict(Counter(c['comparison'] for c in comparisons)),
        'evidence_ref':Path(output).as_posix(),'whole_file_provenance':'pending','all_cells_match_ignoring_whitespace':all(c['comparison']!='content_difference' for c in comparisons)}


CHILD=r'''
from pathlib import Path
import sys,json,importlib.util,hashlib
sys.dont_write_bytecode=True
repo=Path(sys.argv[1]).resolve();bundle=Path('.').resolve();ids=json.loads(sys.argv[2])
def guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes)):
        p=Path(args[0]).resolve()
        if p.is_relative_to(repo) and not p.is_relative_to(bundle):
            raise RuntimeError('PORTABILITY: access outside independent bundle: '+str(p))
sys.addaudithook(guard)
spec=importlib.util.spec_from_file_location('candidate_reader',bundle/'validate_read.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
print(json.dumps({'validation':reader.validate(bundle)},ensure_ascii=False),flush=True)
for rid in ids:
    detail=reader.read(bundle,rid)
    print(json.dumps({'record_id':rid,'detail':detail},ensure_ascii=False),flush=True)
'''


def independent(dataset,root,sample_ids=None):
    root=Path(root);root.mkdir();dataset=Path(dataset)
    shutil.copytree(dataset,root/'bundle')
    script=root/'isolated_read.py';script.write_text(CHILD,encoding='utf8')
    chunks=rows(dataset/'additions/chunks.jsonl');views=rows(dataset/'additions/records.jsonl');forms=rows(dataset/'additions/forms.jsonl')
    ids=[next(c['chunk_id'] for c in chunks if 'Điều 34 > Khoản 2 > Điểm a' in c['citation_path']),
         next(r['record_id'] for r in views if r['source_record'].get('source_graph')=='tt38'),
         next(r['record_id'] for r in views if r['source_record'].get('record_type')=='qcvn-source-subtree.v1'),
         next(f['record_id'] for f in forms if f['source_annex']['literal_marker']=='XXVI'),
         next(m['record_id'] for m in rows(dataset/'memberships.jsonl') if m['record_type']=='table-retrieval.v1')]
    if sample_ids is not None:ids=list(sample_ids)
    cmd=[sys.executable,'-I','-X','utf8','-B',str(script.resolve()),str(Path('.').resolve()),json.dumps(ids)]
    completed=subprocess.run(cmd,cwd=root/'bundle',capture_output=True,text=True,encoding='utf8')
    (root/'stdout.jsonl').write_text(completed.stdout,encoding='utf8');(root/'stderr.txt').write_text(completed.stderr,encoding='utf8')
    if completed.returncode:raise ValueError('Independent read failed: '+completed.stderr[-1000:])
    result=[json.loads(s) for s in completed.stdout.splitlines() if s.strip()]
    if len(result)!=len(ids)+1:raise ValueError('Independent output count mismatch')
    return {'exit_code':completed.returncode,'reads':len(ids),'record_ids':ids,'isolated_python':True,
        'workspace_access_gate':'denied all workspace paths outside copied bundle',
        'stdout_sha256':digest((root/'stdout.jsonl').read_bytes()),'same_machine_os':True,'other_machine_os':'not_tested'}


def run(a):
    out=Path(a.run_dir);out.mkdir(parents=True);results={};errors={}
    checks={'preservation':lambda:preservation(a.baseline),
        'tt35_pages':lambda:page_evidence('staging/tt35-full-layout-001'),
        'tt38_pages':lambda:page_evidence('staging/tt38-full-layout-001'),
        'qcvn_pages':lambda:page_evidence('staging/qcvn-gazette-extraction-001'),
        'nd168_comparison_pages':lambda:page_evidence('staging/nd168-comparison-extraction-001'),
        'law35_comparison_pages':lambda:page_evidence('staging/law35-comparison-extraction-001'),
        'law35_amendment_cells':lambda:amendment_cells(out/'amendment_cell_comparison.json'),
        'ocr_drafts':lambda:ocr_drafts('staging/qcvn-ocr-drafts-001','staging/qcvn-gazette-extraction-001'),
        'independent_read':lambda:independent(Path(a.dataset_manifest).parent,out/'independent')}
    for name,fn in checks.items():
        print('CHECK '+name,flush=True)
        try:results[name]=fn()
        except Exception as e:errors[name]=f'{type(e).__name__}: {e}'
        write_json(out/'checkpoint.json',{'results':results,'errors':errors})
    # Graph source field identities, not just counts.
    try:
        graph=Path('staging/nd168-html-full-002');check_files(graph/'manifest.json');e=load(graph/'extraction.json')
        units=rows(graph/'legal_units.pending.jsonl');spans=rows(graph/'source_spans.pending.jsonl');text=(graph/e['text_ref']).read_text(encoding='utf8')
        full_graph.validate_fields(units,spans,{e['extraction_id']:text})
        articles=[u['designation'] for u in units if u['unit_type']=='article']
        if set(articles)!={str(i) for i in range(1,56)} or len(articles)!=55:raise ValueError('ND168 missing/duplicate/root amendment article')
        results['nd168_graph']={'units':len(units),'articles':len(articles),'source_roundtrip':True}
    except Exception as e:errors['nd168_graph']=str(e)
    report={'completed_at':datetime.now(timezone.utc).isoformat(),'results':results,'errors':errors,
        'technical_valid':not errors,'legal_review':'pending','release_eligible':False}
    write_json(out/'validation_report.json',report);print(json.dumps(report,ensure_ascii=False))
    return 1 if errors else 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset-manifest',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=Path('staging/seven-source-completion-001/preservation.baseline.json'))
    p.add_argument('--run-dir',type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
