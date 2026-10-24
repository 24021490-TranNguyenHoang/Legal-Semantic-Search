"""Finite development batch adapter; no labels transferred and no metric invention."""
import argparse
from pathlib import Path
import json
import math
import shutil
import time
from src import composition_bm25, bm25_baseline, evaluation
from src.assessment_evidence import check_files,seal,now
from src.experimental_dataset import load,rows,write_json,write_rows
from src.source_contracts import digest

def batch(index_manifest,queries_manifest,old_index,old_evaluation,run_dir):
    qpath=Path(queries_manifest).resolve();qm=check_files(qpath)
    if qm['frozen_before_new_ranking'] is not True:raise ValueError('Missing pre-ranking query freeze')
    query_sets=[('old',qpath.parent/'old-dev.queries.jsonl'),('new',qpath.parent/'new-dev.queries.jsonl'),('limit',qpath.parent/'limits.queries.jsonl')]
    queries=[{**q,'batch_group':group} for group,p in query_sets for q in rows(p)]
    evaluation.validate_queries(queries)
    loaded=composition_bm25.load_index(index_manifest)
    old_loaded=bm25_baseline.load_index(old_index)
    root=evaluation.new_output(run_dir)
    for group,p in query_sets:shutil.copyfile(p,root/(group+'.queries.jsonl'))
    write_rows(root/'queries.jsonl',queries);run=[];notes=[];outcomes=[];details={};changes=[];old_replay=[]
    frozen_old={}
    for r in rows(Path(old_evaluation)/'run.jsonl'):frozen_old.setdefault(r['query_id'],[]).append(r)
    for q in queries:
        try:answer=composition_bm25.search_loaded(loaded,q['query'],10)
        except Exception as e:
            outcomes.append({'query_id':q['query_id'],'outcome':'error','error':str(e)});continue
        t=time.perf_counter()
        for h in answer['results']:
            rid=h['record_id'];detail_ref='details/'+rid+'.json'
            if rid not in details:
                detail=loaded['consumer'].detail(rid);details[rid]=detail
                dest=root/detail_ref;dest.parent.mkdir(exist_ok=True);write_json(dest,detail)
            run.append({'query_id':q['query_id'],**h,'detail_ref':detail_ref,
                'dataset_version':loaded['manifest']['dataset_version'],'dataset_manifest_sha256':loaded['manifest']['dataset_manifest_sha256'],
                'index_version':composition_bm25.VERSION,'index_manifest_sha256':digest(Path(index_manifest).read_bytes())})
            notes.append({'query_id':q['query_id'],'record_type':h['record_type'],'record_id':rid,'relevance':None,'relation_to_query':None,
                'relation_choices':['direct_target','dependency_only','unrelated'],'origin':'agent_review','status':'pending',
                'reviewer_ref':None,'reason':None,'evidence_refs':[],'recorded_at':None,'detail_ref':detail_ref})
        outcomes.append({'query_id':q['query_id'],'outcome':'success','search_ms':answer['timings_ms']['search'],
            'detail_ms':(time.perf_counter()-t)*1000,'query_tokens':answer['query_tokens'],'returned':len(answer['results'])})
        if q['batch_group']=='old':
            before=bm25_baseline.search_loaded(old_loaded,q['query'],10)['results'];stored=sorted(frozen_old[q['query_id']],key=lambda r:r['rank'])
            replay=(len(before)==len(stored) and all(a['chunk_id']==b['chunk_id'] and math.isclose(a['score'],b['score'],rel_tol=1e-6,abs_tol=1e-7) for a,b in zip(before,stored)))
            old_replay.append({'query_id':q['query_id'],'same_v1_ids_scores':replay})
            if not replay:raise ValueError('Original v1 regression failed: '+q['query_id'])
            changes.append({'query_id':q['query_id'],'old_ids':[x['chunk_id'] for x in before],'new_ids':[x['record_id'] for x in answer['results']],
                'old_scores':[x['score'] for x in before],'new_scores':[x['score'] for x in answer['results']],
                'same_top10_ids':[x['chunk_id'] for x in before]==[x['record_id'] for x in answer['results']],
                'interpretation':'Corpus statistics and membership changed; no quality conclusion without labels'})
    # Coverage observations are based on membership/selection, not ranking misses.
    selection=loaded['consumer'].selection
    limits=[{'query_id':q['query_id'],'coverage_status':'pending_review','origin':'agent_review',
        'basis':'selection_and_graph_inventory_not_top10_absence','finding':{
            'V3-L01':'Form XI target withheld; annex evidence/reference may exist, not a retrieval form target',
            'V3-L02':'Form XXVI target withheld; not a claim that all references or source text are absent',
            'V3-L03':'No QCVN retrieval targets in composition; pilot transcription excluded',
            'V3-L04':'Detailed medical standard is not a packaged legal component; general health references exist',
            'V3-L05':'TT38 A11K2b is not a target; its original text can be read via A4K2 required-read subtree; related other targets may exist'}[q['query_id']]} for q in queries if q['batch_group']=='limit']
    for name,value in [('run',run),('annotations',notes),('outcomes',outcomes),('ranking_comparison',changes),('v1_regression',old_replay),('coverage_limits',limits),('qrels',[])]:write_rows(root/(name+'.jsonl'),value)
    write_json(root/'report.json',{'state':'PENDING_LABELS','metrics':None,'queries':len(queries),'query_groups':{'old':sum(q['batch_group']=='old' for q in queries),'new':sum(q['batch_group']=='new' for q in queries),'limit':len(limits)},
        'eligible_queries':0,'reason':'No accepted v3 judgments; v1 qrels not transferred','results':len(run),'unique_detail_records':len(details),
        'query_errors':sum(o['outcome']=='error' for o in outcomes),'v1_regression_passed':all(x['same_v1_ids_scores'] for x in old_replay),
        'old_queries_changed_top10':sum(not c['same_top10_ids'] for c in changes),'load_ms':loaded['load_ms'],'old_index_load_ms':old_loaded['load_ms'],
        'detail_is_separate_from_search_timing':True,'experimental':True,'release_eligible':False})
    sheet=['# Review v3 — pending, no accepted labels','Pool biased by BM25. Read detail/dependencies; distinguish direct target from dependency-only. No qrels inherited.']
    for q in queries:
        sheet+=['## '+q['query_id']+' — '+q['query']]
        for hit in [r for r in run if r['query_id']==q['query_id']]:
            d=details[hit['record_id']];sheet += [f"### {hit['rank']}. {hit['citation_path']} ({hit['record_type']})",hit['record_id'],
                'Nguyên văn:',d['text_original'],'Dẫn xuất bảng (nếu có):',d['derived_text'] or '',
                'Context:',*[(c['text_original']) for c in d['contexts']],
                'Required-read IDs: '+', '.join(hit['required_dependency_ids']),f"[Full detail/source/cells/dependencies]({hit['detail_ref']})",
                'Relevance: null; relation: null; reviewer/time/reason: null.']
    (root/'annotation_sheet.md').write_text('\n\n'.join(sheet),encoding='utf8')
    binding={k:loaded['manifest'][k] for k in ['index_version','dataset_version','dataset_manifest_sha256','dataset_content_sha256','index_content_sha256']}
    binding['index_manifest_sha256']=digest(Path(index_manifest).read_bytes())
    seal(root,{'manifest_type':'composition-development-run.v1','created_at':now(),'binding':binding,'queries_manifest_sha256':digest(qpath.read_bytes()),
        'evaluation_code_sha256':digest(Path(__file__).read_bytes()),'old_query_bytes_unchanged':(root/'old.queries.jsonl').read_bytes()==(qpath.parent/'old-dev.queries.jsonl').read_bytes(),
        'origin':'agent_review','state':'PENDING_LABELS','human_reviewer_events':0,'release_eligible':False})
    return load(root/'report.json')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--index-manifest',type=Path,required=True);p.add_argument('--queries-manifest',type=Path,required=True)
    p.add_argument('--old-index',type=Path,required=True);p.add_argument('--old-evaluation',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args(argv)
    print(json.dumps(batch(a.index_manifest,a.queries_manifest,a.old_index,a.old_evaluation,a.run_dir),ensure_ascii=False))
if __name__=='__main__':main()
