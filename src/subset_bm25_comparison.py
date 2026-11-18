"""Finite session14 v5/v6 retrieval comparison; no judgments or metrics."""
import argparse
from pathlib import Path
from src import subset_bm25 as v5,subset_bm25_v6 as v6
from src.experimental_dataset import load,rows,write_json,write_rows


def validate_batch(root,manifest_sha):
    m=load(root/'manifest.json')
    if v6.digest((root/'manifest.json').read_bytes())!=manifest_sha:raise ValueError('Wrong frozen batch manifest')
    if v6.hashed(m['files'])!=m['content_sha256']:raise ValueError('Batch inventory hash differs')
    for e in m['files']:
        b=v6.resolve_ref(root,e['path']).read_bytes()
        if len(b)!=e['size_bytes'] or v6.digest(b)!=e['sha256']:raise ValueError('Batch payload differs: '+e['path'])
    return m


def top_delta(old,new):
    a={x['record_id']:x for x in old};b={x['record_id']:x for x in new}
    return dict(top1_before=old[0]['record_id'] if old else None,top1_after=new[0]['record_id'] if new else None,
        top10_before=[x['record_id'] for x in old],top10_after=[x['record_id'] for x in new],
        entered_top10=[x['record_id'] for x in new if x['record_id'] not in a],
        exited_top10=[x['record_id'] for x in old if x['record_id'] not in b],
        shared_rank_changes=[dict(record_id=x,old_rank=a[x]['rank'],new_rank=b[x]['rank'],
             old_score=a[x]['score'],new_score=b[x]['score']) for x in sorted(set(a)&set(b))])


def compare(config,index,batch,output):
    cfg=load(config);pin=cfg['v5_comparison'];old_root=v6.resolve_ref(v6.BASE_DIR,pin['index_ref'])
    if v6.digest((old_root/'index_manifest.json').read_bytes())!=pin['index_manifest_sha256']:raise ValueError('Wrong v5 index')
    old_batch=v6.resolve_ref(v6.BASE_DIR,pin['batch_ref']);validate_batch(old_batch,pin['batch_manifest_sha256'])
    new_manifest_sha=v6.digest((Path(batch)/'manifest.json').read_bytes());validate_batch(Path(batch),new_manifest_sha)
    old=v5.load_index(old_root);new=v6.load_index(index)
    oq=rows(old_batch/'queries.jsonl');nq=rows(Path(batch)/'queries.jsonl')
    if oq!=nq:raise ValueError('Query IDs/text/order changed')
    if new['manifest']['dataset_manifest_sha256']!=cfg['dataset_manifest_sha256']:raise ValueError('Wrong v6 dataset')
    out=v6.new_output(output);old_runs=rows(old_batch/'raw_results.jsonl');new_runs=rows(Path(batch)/'raw_results.jsonl')
    if len(old_runs)!=len(oq) or len(new_runs)!=len(oq):raise ValueError('Incomplete query run')
    deltas=[];replay=[]
    for q,a,b in zip(oq,old_runs,new_runs):
        if a['query_id']!=q['query_id'] or b['query_id']!=q['query_id'] or a['query']!=q['query'] or b['query']!=q['query'] or a['top_k_requested']!=10 or b['top_k_requested']!=10:raise ValueError('Query or topk mismatch')
        answer=v5.search_loaded(old,q['query'],10)
        if answer['results']!=a['results']:raise ValueError('Frozen v5 retrieval not reproducible')
        replay.append(dict(query_id=q['query_id'],query_sha256=v6.digest(q['query'].encode()),results=answer['results']))
        if any(h['record_id'] not in new['consumer'].targets for h in b['results']):raise ValueError('Foreign target returned')
        deltas.append(dict(query_id=q['query_id'],query=q['query'],query_sha256=v6.digest(q['query'].encode()),**top_delta(a['results'],b['results'])))
    write_rows(out/'v5.replay.jsonl',replay);write_rows(out/'query_deltas.jsonl',deltas)
    added=sorted(set(new['consumer'].targets)-set(old['consumer'].targets));removed=sorted(set(old['consumer'].targets)-set(new['consumer'].targets))
    if added!=[new['consumer'].red_id] or removed:raise ValueError('Unexpected membership delta')
    diagnostic=[];deep={}
    for qid in ['dev-red_light-2','dev-driving_age-2','V3-D05','V3-D07']:
        q=next(q for q in oq if q['query_id']==qid);a=v5.search_loaded(old,q['query'],138);b=v6.search_loaded(new,q['query'],139)
        diagnostic.append(dict(query_id=qid,query=q['query'],v5=a,v6=b))
        rid=new['consumer'].red_id if qid=='dev-red_light-2' else new['consumer'].age_id if qid=='dev-driving_age-2' else None
        if rid:
            detail=v6.read_loaded(new,rid);d=detail['dataset_response'];before=v5.read_loaded(old,rid) if rid in old['consumer'].targets else None
            deep[qid]=dict(record_id=rid,rank_v5=next((h['rank'] for h in a['results'] if h['record_id']==rid),None),rank_v6=next((h['rank'] for h in b['results'] if h['record_id']==rid),None),
                target=d['record']['text_original'],contexts=d['contexts'],required_unit_ids=[u['unit_id'] for u in d['required_read']['unit_reads']],
                required_read=d['required_read'],source_proofs=d['source_proofs'],
                previous_required_count=len(before['dataset_response']['required_read']['unit_reads']) if before else None,
                payload_unchanged=before['dataset_response']['record']==d['record'] if before else None,
                context_unchanged=before['dataset_response']['contexts']==d['contexts'] if before else None,
                response_sha256=detail['dataset_response_sha256'])
        else:
            selected=[v6.read_loaded(new,h['record_id']) for h in b['results'][:10] if h['record_type'] in ['table-retrieval.v1','source-retrieval.v1']]
            deep[qid]=dict(reads=selected,warning='Partial hit or a single row is not a complete multi-part answer; keep header, conditions and correct 60/80/81 interval.')
    if len(deep['dev-red_light-2']['required_unit_ids'])!=7 or len(deep['dev-driving_age-2']['required_unit_ids'])!=16 or deep['dev-driving_age-2']['previous_required_count']!=2:raise ValueError('Incorrect selected dependency closure')
    if not deep['dev-driving_age-2']['payload_unchanged'] or not deep['dev-driving_age-2']['context_unchanged']:raise ValueError('Age payload changed')
    write_rows(out/'diagnostic-all-documents.jsonl',diagnostic);write_json(out/'deep_checks.json',deep)
    md=['# Retrieval v5 → v6, cùng 50 query ghim','So sánh hành vi, không relevance metrics. V5 replay exact ID/rank/score; corpus stats v6 có thể đổi score.','| Query | Top1 đổi | Vào Top10 | Ra Top10 |','|---|---|---|---|']
    md.extend('| '+x['query_id']+' | '+str(x['top1_before']!=x['top1_after'])+' | '+str(len(x['entered_top10']))+' | '+str(len(x['exited_top10']))+' |' for x in deltas)
    md+=['','## Đèn đỏ và tuổi']
    for qid in ['dev-red_light-2','dev-driving_age-2']:
        d=deep[qid];md += ['',qid+': rank '+str(d['rank_v5'])+' → '+str(d['rank_v6'])+'; required-read '+str(d['previous_required_count'])+' → '+str(len(d['required_unit_ids'])),d['record_id'],'',d['target'],'']
        md.extend(c['text_original'] for c in d['contexts'])
    md+=['','V3-D05/V3-D07: xem deep_checks.json để đọc nguyên rows/cells/header và điều kiện; V=60 / 60<V≤80 / 80<V≤100 tương ứng35/55/70m. Một hàng55m cho80 không trả lời phần81; applicability vẫn pending.','Chi tiết Top10/record vào-ra/rank và score từng ID: query_deltas.jsonl. Diagnostic139 riêng, không ghi đè batchTop10.']
    (out/'comparison.md').write_text('\n'.join(md)+'\n',encoding='utf8')
    report=dict(queries=len(oq),v5_replay_exact=True,top1_changed=sum(d['top1_before']!=d['top1_after'] for d in deltas),top10_changed=sum(d['top10_before']!=d['top10_after'] for d in deltas),added_target_ids=added,removed_target_ids=removed,
        old_index_manifest_sha256=pin['index_manifest_sha256'],new_index_manifest_sha256=v6.digest((Path(index)/'index_manifest.json').read_bytes()),old_batch_manifest_sha256=pin['batch_manifest_sha256'],new_batch_manifest_sha256=new_manifest_sha,
        queries_manifest_sha256=cfg['queries_manifest_sha256'],metrics=None,labels_transferred=False,release_eligible=False)
    write_json(out/'report.json',report);inv=v6.inventory(out);write_json(out/'manifest.json',dict(files=inv,content_sha256=v6.hashed(inv),binding=report));return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['config','index','batch','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(compare(a.config,a.index,a.batch,a.output))

if __name__=='__main__':main()
