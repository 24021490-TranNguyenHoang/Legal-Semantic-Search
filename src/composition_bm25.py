"""Experimental BM25 composition adapter; preserves baseline engine and query path."""
import argparse
from pathlib import Path
import json
import shutil
import sys
import time
from src import bm25_baseline as baseline
from src.bm25_tokenizer import tokenize
from src.composition_consumer import Consumer,VERSION as CONSUMER_VERSION
from src.experimental_dataset import load,rows,write_json,write_rows
from src.source_contracts import canonical,digest,resolve_ref
from src.config import BASE_DIR

VERSION='vtls-bm25s-composition.v1'
PROJECTION='composition-text-for-search.v1'
CODE=['src/composition_bm25.py','src/composition_consumer.py','src/bm25_baseline.py','src/bm25_tokenizer.py']
RUNTIME=CODE+['src/config.py','src/source_contracts.py','src/experimental_dataset.py','src/chunk_preview.py','src/chunk_preview_v2.py','src/ingestion/legal_tree.py']
CONTROL={'index_manifest.json','index_manifest.sha256'}

def inventory(root):
    return [{'path':p.relative_to(root).as_posix(),'size_bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file() and p.relative_to(root).as_posix() not in CONTROL and '__pycache__' not in p.parts]

def create(projected,cfg):
    if len({p['record_id'] for p in projected})!=len(projected):raise ValueError('Duplicate projected record')
    projected=sorted(projected,key=lambda p:p['record_id'])
    tokens=[tokenize(p['text_for_search'],cfg) for p in projected]
    if not projected or any(not ts for ts in tokens):raise ValueError('Empty projection/document')
    vocab={t:i for i,t in enumerate(sorted({t for ts in tokens for t in ts}))}
    retriever=baseline.engine(cfg);retriever.index(([[vocab[t] for t in ts] for ts in tokens],vocab),create_empty_token=False,show_progress=False)
    mapping=[{'internal_doc_id':i,'record_type':p['record_type'],'record_id':p['record_id'],'content_sha256':p['content_sha256'],
        'token_count':len(ts),'tokens_sha256':digest(canonical(ts).encode())} for i,(p,ts) in enumerate(zip(projected,tokens))]
    return retriever,mapping

def build(dataset_manifest,run_dir):
    from src.pipeline_cli import staging_path
    source=Path(dataset_manifest).resolve();consumer=Consumer(source.parent)
    if consumer.manifest['dataset_version']!='vtls-coverage-experimental.v3-draft.1':raise ValueError('Wrong experimental dataset version')
    cfg=load(baseline.DEFAULT_CONFIG);retriever,mapping=create(consumer.projection(),cfg)
    root=staging_path(run_dir);root.mkdir(parents=True);shutil.copytree(source.parent,root/'dataset')
    write_json(root/'config.json',cfg);write_rows(root/'document_mapping.jsonl',mapping)
    retriever.save(str(root/'engine'),allow_pickle=False,show_progress=False)
    for name in RUNTIME+['config/bm25_baseline.v1.json']:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(BASE_DIR/name,target)
    (root/'src/__init__.py').write_text('',encoding='utf8');(root/'src/ingestion/__init__.py').write_text('',encoding='utf8')
    shutil.copyfile(BASE_DIR/'requirements-bm25.txt',root/'requirements-bm25.txt')
    write_json(root/'runtime.json',baseline.runtime())
    inv=inventory(root);m={'index_version':VERSION,'projection_version':PROJECTION,'consumer_version':CONSUMER_VERSION,
        'dataset_version':consumer.manifest['dataset_version'],'dataset_manifest_ref':'dataset/dataset_manifest.json',
        'dataset_manifest_sha256':digest(source.read_bytes()),'dataset_content_sha256':consumer.manifest['dataset_content_sha256'],
        'snapshot_date':'2025-01-01','documents':len(mapping),'record_counts':dict(__import__('collections').Counter(x['record_type'] for x in mapping)),
        'runtime':baseline.runtime(),'config_sha256':digest((root/'config.json').read_bytes()),
        'code_sha256':{n:digest((BASE_DIR/n).read_bytes()) for n in CODE},'tie_break':'score_desc_record_id_asc',
        'experimental':True,'release_eligible':False,'corpus_version':None,'files':inv,'index_content_sha256':digest(canonical(inv).encode())}
    write_json(root/'index_manifest.json',m);(root/'index_manifest.sha256').write_text(digest((root/'index_manifest.json').read_bytes())+'\n',encoding='ascii')
    return validate(root/'index_manifest.json')

def load_index(manifest):
    start=time.perf_counter();path=Path(manifest).resolve();root=path.parent;m=load(path)
    if (m['index_version']!=VERSION or m['projection_version']!=PROJECTION or m['consumer_version']!=CONSUMER_VERSION or m['snapshot_date']!='2025-01-01'
        or m['release_eligible'] is not False or m['experimental'] is not True or m['corpus_version'] is not None
        or digest(path.read_bytes())!=(root/'index_manifest.sha256').read_text().strip()
        or m['files']!=inventory(root) or m['index_content_sha256']!=digest(canonical(m['files']).encode())):raise ValueError('Index version/inventory/status mismatch')
    if m['code_sha256']!={n:digest((BASE_DIR/n).read_bytes()) for n in CODE}:raise ValueError('Consumer/projection/tokenizer source binding mismatch')
    cfg=load(root/'config.json');baseline.check_config(cfg)
    compatibility=baseline.runtime_compatibility(m['runtime'],baseline.runtime())
    if load(root/'runtime.json')!=m['runtime'] or digest((root/'config.json').read_bytes())!=m['config_sha256']:raise ValueError('Index runtime/config binding mismatch')
    dp=resolve_ref(root,m['dataset_manifest_ref'])
    if digest(dp.read_bytes())!=m['dataset_manifest_sha256']:raise ValueError('Index/dataset manifest hash mismatch')
    consumer=Consumer(dp.parent)
    if consumer.manifest['dataset_version']!=m['dataset_version'] or consumer.manifest['dataset_content_sha256']!=m['dataset_content_sha256']:raise ValueError('Dataset content/version mismatch')
    projected=consumer.projection();mapping=rows(root/'document_mapping.jsonl')
    if len(mapping)!=len(projected) or m['documents']!=len(mapping):raise ValueError('Index membership count mismatch')
    for i,(r,p) in enumerate(zip(mapping,projected)):
        ts=tokenize(p['text_for_search'],cfg)
        expected={'internal_doc_id':i,**{k:p[k] for k in ['record_type','record_id','content_sha256']},'token_count':len(ts),'tokens_sha256':digest(canonical(ts).encode())}
        if r!=expected:raise ValueError('Index row/type/ID/token mapping mismatch')
    import bm25s,numpy as np
    retriever=bm25s.BM25.load(str(root/'engine'),load_corpus=False,mmap=False,allow_pickle=False,show_progress=False)
    vocab={t:i for i,t in enumerate(sorted({t for p in projected for t in tokenize(p['text_for_search'],cfg)}))};s=retriever.scores
    if (s['num_docs']!=len(mapping) or retriever.vocab_dict!=vocab or retriever.method!=cfg['method'] or retriever.idf_method!=cfg['idf_method'] or retriever.k1!=cfg['k1'] or retriever.b!=cfg['b']
        or len(s['indptr'])!=len(vocab)+1 or s['indptr'][0]!=0 or s['indptr'][-1]!=len(s['data']) or len(s['data'])!=len(s['indices'])
        or not np.isfinite(s['data']).all() or (s['data']<0).any() or (np.diff(s['indptr'])<0).any() or (s['indices']<0).any() or (s['indices']>=len(mapping)).any()):raise ValueError('Saved engine/config/CSC mismatch')
    return {'consumer':consumer,'manifest':m,'retriever':retriever,'mapping':mapping,'config':cfg,'load_ms':(time.perf_counter()-start)*1000,'runtime_compatibility':compatibility}

def search_loaded(loaded,query,top_k=10):
    start=time.perf_counter()
    # Baseline rank only uses this ephemeral key for tie sorting, not chunk semantics.
    rankmap={i:{'chunk_id':r['record_id']} for i,r in enumerate(loaded['mapping'])}
    tokens,hits=baseline.rank(loaded['retriever'],rankmap,query,top_k,loaded['config']);results=[];c=loaded['consumer']
    for rank,(idx,score) in enumerate(hits,1):
        row=loaded['mapping'][idx];rid=row['record_id'];r=c.records[rid];mem=c.members[rid];u=c.graphs[mem['graph_id']][r.get('unit_id',r.get('owner_unit_id'))]
        results.append({'rank':rank,'score':score,'record_type':row['record_type'],'record_id':rid,'citation_path':u['citation_path'],
            'text_original':r.get('text_original',r.get('source_original')),'derived_text':r.get('derived_text'),
            'required_dependency_ids':[d['root_unit_id'] for d in c.dependencies if d['record_id']==rid],
            'notice':'Ranked evidence snippet; read full detail/dependencies before interpretation','experimental':True,'release_eligible':False})
    return {'query':query,'query_tokens':tokens,'results':results,'timings_ms':{'load':loaded['load_ms'],'search':(time.perf_counter()-start)*1000},
        'index_version':VERSION,'dataset_version':loaded['manifest']['dataset_version'],'experimental':True,'release_eligible':False}

def validate(manifest):
    import numpy as np
    loaded=load_index(manifest);expected,mapping=create(loaded['consumer'].projection(),loaded['config'])
    if loaded['mapping']!=mapping:raise ValueError('Mapping replay mismatch')
    for k in ['data','indices','indptr']:
        a,b=loaded['retriever'].scores[k],expected.scores[k]
        if a.shape!=b.shape or not (np.allclose(a,b,rtol=1e-6,atol=1e-7) if k=='data' else np.array_equal(a,b)):raise ValueError('Index replay mismatch '+k)
    return {'technical_valid':True,'documents':len(mapping),'record_counts':loaded['manifest']['record_counts'],'save_load_replay':True,'release_eligible':False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    b=s.add_parser('build');b.add_argument('--dataset-manifest',required=True,type=Path);b.add_argument('--run-dir',required=True,type=Path)
    for name in ['validate','search','read']:
        q=s.add_parser(name);q.add_argument('--index-manifest',required=True,type=Path)
        if name=='search':q.add_argument('--query',required=True);q.add_argument('--top-k',type=int,default=10)
        if name=='read':q.add_argument('--record-id',required=True)
    a=p.parse_args(argv)
    try:
        if a.action=='build':result=build(a.dataset_manifest,a.run_dir)
        elif a.action=='validate':result=validate(a.index_manifest)
        else:
            loaded=load_index(a.index_manifest);result=search_loaded(loaded,a.query,a.top_k) if a.action=='search' else loaded['consumer'].detail(a.record_id)
        print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as e:print(f'ERROR: {type(e).__name__}: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
