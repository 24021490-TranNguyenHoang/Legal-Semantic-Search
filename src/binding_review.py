"""Finite v5→v6 binding review for five fixed queries; never admits or scores."""
import argparse
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import sys
import zipfile
from src import query_review as qr, subset_review as review, subset_evaluation as evaluation
from src import subset_bm25_v6 as bm, subset_labels as labels
from src.experimental_dataset import load,rows,write_json,write_rows
from src.source_contracts import resolve_ref,digest,canonical
from src.config import BASE_DIR

VERSION='subset-v6-binding-review.v1'
QUERIES=qr.QUERIES


def check_bundle(path,sha):
    if digest(path.read_bytes())!=sha:raise ValueError('Wrong pinned input: '+str(path))
    m=load(path)
    for f in m['files']:
        p=resolve_ref(path.parent,f['path']);b=p.read_bytes()
        if len(b)!=f['size_bytes'] or digest(b)!=f['sha256']:raise ValueError('Changed input inventory: '+f['path'])
    return m


def native_semantics(value):
    # Only package_locator denotes version-dependent storage. Original locators,
    # raw/extraction IDs/hashes, Unicode offsets and quotes are never discarded.
    if isinstance(value,list):return [native_semantics(v) for v in value]
    if isinstance(value,dict):return {k:native_semantics(v) for k,v in value.items() if k!='package_locator'}
    return value


def facets(detail):
    d=detail['dataset_response'];m=d['membership']
    return dict(payload=bm.hashed(d['record']),context=bm.hashed(d['contexts']),
        search_text=digest(d['record']['text_for_search'].encode()),record_type=d['record_type'],
        membership=bm.hashed(m),closure=bm.hashed(native_semantics(d['required_read'])),
        source_proofs=bm.hashed(native_semantics(d['source_proofs'])),ancestors=d['structural_ancestor_ids'])


def classify(old,new,evidence_ok=True):
    if new is None or not evidence_ok:return 'D'
    if old is None:return 'C'
    a,b=facets(old),facets(new)
    if any(a[k]!=b[k] for k in ['payload','context','search_text','record_type']):return 'C'
    if a!=b:return 'B'
    return 'A'


def detail_for(c,rid):
    d=c.read(rid);r=d['record']
    return dict(record_id=rid,record_type=d['record_type'],citation_path=c.proposals[d['membership']['unit_id']]['citation_path'],
        text_original=r.get('text_original',r.get('source_original','')),source_spans=[s for s in c.spans if s['unit_id']==d['membership']['unit_id']],
        cells=r.get('cells',r.get('source_record',{}).get('source_cells',[])),required_read_dependencies=d['required_read']['bindings'],
        dataset_response=d,dataset_response_sha256=bm.hashed(d))


def rebound_evidence(old_detail,new_detail,evidence):
    output=[]
    for e in evidence:
        review.validate_quote(old_detail,e);p=e['field_pointer']
        parts=p.split('/')
        if p.startswith('/dataset_response/required_read/unit_reads/'):
            uid=old_detail['dataset_response']['required_read']['unit_reads'][int(parts[4])]['unit_id']
            values=new_detail['dataset_response']['required_read']['unit_reads']
            parts[4]=str(next(i for i,x in enumerate(values) if x['unit_id']==uid));p='/'.join(parts)
        q={**e,'field_pointer':p};review.validate_quote(new_detail,q);output.append(q)
    return output


def inputs(config):
    cfg=load(config)
    if cfg['contract']!=VERSION or cfg['snapshot']!='2025-01-01' or cfg['query_ids']!=QUERIES:raise ValueError('Wrong review scope')
    paths={k:labels.bound_file(v) for k,v in cfg['inputs'].items()}
    # Existing full accepted/aggregate validator replays receipts/provenance; no metric function is called.
    ctx=evaluation.inputs(paths['evaluation_config'])
    if labels.spec(ctx['paths']['aggregate'])!=cfg['inputs']['aggregate']:raise ValueError('Wrong accepted aggregate')
    im=check_bundle(paths['index'],cfg['inputs']['index']['sha256'])
    if im['dataset_version']!=bm.DATASET or im['index_version']!=bm.VERSION or im['dataset_manifest_sha256']!=cfg['inputs']['dataset']['sha256']:raise ValueError('Wrong v6 binding')
    batch=check_bundle(paths['batch'],cfg['inputs']['batch']['sha256'])
    if batch['binding']['index_manifest_sha256']!=cfg['inputs']['index']['sha256']:raise ValueError('Wrong v6 batch binding')
    v14=load(paths['v14_config']);consumer=bm.bound_consumer(paths['dataset'].parent,v14)
    q=rows(paths['batch'].parent/'queries.jsonl');oldq=rows(ctx['paths']['batch'].parent/'queries.jsonl')
    if q!=oldq:raise ValueError('Frozen queries changed')
    comparison=check_bundle(paths['comparison'],cfg['inputs']['comparison']['sha256'])
    from src.subset_bm25_comparison import top_delta
    oldruns=rows(ctx['paths']['batch'].parent/'raw_results.jsonl');newruns=rows(paths['batch'].parent/'raw_results.jsonl')
    actual=rows(paths['comparison'].parent/'query_deltas.jsonl')
    expected=[dict(query_id=x['query_id'],query=x['query'],query_sha256=digest(x['query'].encode()),**top_delta(a['results'],b['results'])) for x,a,b in zip(q,oldruns,newruns)]
    if actual!=expected:raise ValueError('Session14 comparison does not match sealed payloads')
    agg=load(paths['aggregate']);all_annotations=[];pending=[]
    for spec in agg['batches']:
        root=labels.bound_file(spec).parent;all_annotations+=rows(root/'accepted.annotations.jsonl');pending+=rows(root/'pending.annotations.jsonl')
    if len(all_annotations)!=59 or len({qr.pair(x) for x in all_annotations})!=59:raise ValueError('Accepted inventory differs')
    if len(pending)!=2 or any(p['query_id']!='V3-D02' or p['relevance'] is not None for p in pending):raise ValueError('Pending inventory differs')
    selected={qr.pair(a):a for a in all_annotations if a['query_id'] in QUERIES}
    if len(selected)!=len(ctx['pool']) or set(selected)!={qr.pair(p) for p in ctx['pool']}:raise ValueError('Old accepted pool omitted or duplicated')
    binding={k:im[k] for k in ['dataset_version','dataset_manifest_sha256','dataset_content_sha256','consumer_sha256','queries_manifest_sha256','index_version','index_content_sha256']}
    binding.update(index_manifest_sha256=cfg['inputs']['index']['sha256'],batch_manifest_sha256=cfg['inputs']['batch']['sha256'])
    return dict(cfg=cfg,paths=paths,old=ctx,new=consumer,binding=binding,queries={x['query_id']:x for x in q if x['query_id'] in QUERIES},accepted=selected,all_accepted=all_annotations,pending=pending,runs=rows(paths['batch'].parent/'run.jsonl'),comparison=actual)


def member_role(consumer,record_id,unit_id):
    if record_id in consumer.targets:return 'target'
    if unit_id in consumer.support:return 'dependency_only'
    if unit_id in consumer.nodes:return 'structural_or_unselected_unit'
    return 'absent'


def assemble_context(data):
    # Reuse the finite query/record pool union, filtering out old pairs without membership explicitly.
    accepted=list(data['accepted'].values());c=data['new'];selected=[a for a in accepted if a['record_id'] in c.targets]
    union=qr.pool_union(QUERIES,data['runs'],selected,[])
    for key,origins in union:
        a=data['accepted'].get(key)
        if a and a['relevance'] in [1,2] and not any(qr.pair(h)==key for h in data['runs']):
            origins.append(dict(origin='known_accepted_positive_outside_v6_top10',source_row_sha256=bm.hashed(a)))
    details={rid:detail_for(c,rid) for (_,rid),_ in union}
    pool=[];disposition=[]
    for (qid,rid),origins in union:
        new=details[rid];old=data['old']['details'].get(rid);a=data['accepted'].get((qid,rid));evidence=[];error=None
        if a:
            try:evidence=rebound_evidence(old,new,a['evidence_locators'])
            except (ValueError,KeyError,StopIteration,IndexError) as exc:error=str(exc)
        group=classify(old if a else None,new,error is None)
        pool.append(dict(review_pair_id='V6PAIR-'+bm.hashed([qid,rid])[:14],query_id=qid,record_id=rid,record_type=new['record_type'],
            query_sha256=bm.hashed(data['queries'][qid]),record_sha256=bm.hashed(new['dataset_response']['record']),
            full_read_sha256=new['dataset_response_sha256'],classification=group,pool_sources=origins,
            old_unit_role=member_role(c.baseline,rid,new['dataset_response']['membership']['unit_id']),
            old_decision=copy.deepcopy(a),old_decision_sha256=bm.hashed(a) if a else None,
            old_facets=facets(old) if a else None,new_facets=facets(new),
            rebound_old_evidence=evidence,evidence_error=error,reviewer_decision=None,human_review=None,
            old_top10=any(x['query_id']==qid and x['record_id']==rid for x in data['old']['run']),
            v6_top10=any(x['query_id']==qid and x['record_id']==rid for x in data['runs']),target_membership_v6=True))
    for a in accepted:
        p=next((p for p in pool if qr.pair(p)==qr.pair(a)),None)
        disposition.append(dict(query_id=a['query_id'],record_id=a['record_id'],annotation_id=a['annotation_id'],old_annotation_sha256=bm.hashed(a),
            classification=p['classification'] if p else 'D',in_review_pool=p is not None,
            membership=member_role(c,a['record_id'],data['old']['details'][a['record_id']]['dataset_response']['membership']['unit_id']),
            accepted_v6=False,new_decision=None))
    return dict(pool=pool,details=details,disposition=disposition)


def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
def jsonl(value):return ''.join(canonical(v)+'\n' for v in value).encode()


def pack_manifest(files,prefix,metadata):
    refs=[dict(path=k[len(prefix):],sha256=digest(v),size_bytes=len(v)) for k,v in sorted(files.items()) if k.startswith(prefix)]
    value=encode(dict(metadata,files=refs));files[prefix+'manifest.json']=value;files[prefix+'manifest.sha256']=(digest(value)+'\n').encode()


def proposal_for(p,detail,cfg,query):
    old=p['old_decision'];group=p['classification']
    if group in ['A','B']:
        rel,relation,complete,reason=[old[k] for k in ['relevance','relation','completeness','reason']]
        evidence=p['rebound_old_evidence'][:]
        action='confirm_exact_list' if group=='A' else 're_review_changed_closure'
        if group=='B':reason='Đề xuất tạm giữ nhãn cũ '+str(rel)+'/'+complete+'; closure đã đổi nên cần rà lại evidence/completeness, chưa nâng lên full. Lý do lịch sử nguyên vẹn nằm trong old_decision. '+reason
    elif group=='C':
        matches=[x for x in cfg['new_pair_judgments'] if qr.pair(x)==qr.pair(p)]
        if len(matches)!=1:raise ValueError('New pair requires explicit inspected judgment, not rank/default label')
        x=matches[0];rel,relation,complete=review.CODES[x['code']];reason=x['reason'];action='review_new_pair';evidence=[]
    else:rel,relation,complete=None,'uncertain','uncertain';reason='Chưa đủ bằng chứng tương đương; cần rà blocker.';evidence=[];action='pending_evidence'
    if group in ['B','C','D']:
        field='source_original' if p['record_type']=='table-retrieval.v1' else 'text_original'
        paths=['/dataset_response/record/'+field]
        paths += ['/dataset_response/contexts/'+str(i)+'/text_original' for i,c in enumerate(detail['dataset_response']['contexts']) if c['text_original']]
        paths += ['/dataset_response/required_read/unit_reads/'+str(i)+'/unit/'+('text_original' if u['unit']['text_original'] else 'title') for i,u in enumerate(detail['dataset_response']['required_read']['unit_reads']) if u['unit']['text_original'] or u['unit'].get('title')]
        evidence += [review.quote(detail,path) for path in paths]
    unique={bm.hashed(e):e for e in evidence};evidence=list(unique.values())
    if not evidence:raise ValueError('Missing bound evidence')
    return dict(review_pair_id=p['review_pair_id'],query_id=p['query_id'],record_id=p['record_id'],record_type=p['record_type'],
        binding=None,query_sha256=p['query_sha256'],record_sha256=p['record_sha256'],
        origin='agent_review',status='pending' if rel is None else 'proposed',reviewer_ref=None,human_review=None,recorded_at=cfg['agent_recorded_at'],
        relevance=rel,relation=relation,completeness=complete,reason=reason,
        answered_part=reason if rel in [1,2] else None,missing_part=None if complete=='full' else 'Cần kiểm nội dung/điều kiện theo query; không coi partial hoặc dependency-only là đủ mọi phần.',
        uncertainty='Proposal nội dung experimental, source/edition/applicability pending; chưa có quyết định v6.',
        evidence_refs=['details/'+p['record_id']+'.json'],detail_sha256=None,citation_path=detail['citation_path'],
        source_spans=detail['source_spans'],cell_ids=[c['cell_id'] for c in detail['cells']],combine_with=[],
        evidence_locators=evidence,full_read_scope_sha256=detail['dataset_response_sha256'],suggested_action=action)


def packet_files(data):
    assembled=assemble_context(data);pool=assembled['pool'];details=assembled['details'];cfg=data['cfg'];files={}
    for rid,d in sorted(details.items()):
        files['review/details/'+rid+'.json']=encode(d)
        files['review/evidence/'+rid+'.md']=qr.source_page(d).encode()
    evidence=[];proposals=[]
    for p in pool:
        a=proposal_for(p,details[p['record_id']],cfg,data['queries'][p['query_id']]);a['binding']=data['binding'];a['detail_sha256']=digest(files['review/details/'+p['record_id']+'.json'])
        ids=[]
        for loc in a['evidence_locators']:
            eid='EV6-'+bm.hashed([p['review_pair_id'],loc])[:18];ids.append(eid)
            evidence.append(dict(evidence_id=eid,review_pair_id=p['review_pair_id'],record_id=p['record_id'],detail_sha256=a['detail_sha256'],locator=loc,
                native_proofs_ref='details/'+p['record_id']+'.json#/dataset_response/source_proofs'))
        a['evidence_ids']=ids;proposals.append(a)
    byproposal={a['review_pair_id']:a for a in proposals}
    # Only native proof assets referenced by selected detail/required-read are mounted.
    mounts={}
    from src.binding_review_packet import walk
    for d in details.values():
        for proof in walk(d):
            if 'package_locator' not in proof:continue
            for key,ref in proof['package_locator'].items():
                if not key.endswith('_ref') or not isinstance(ref,str) or ref in mounts:continue
                content=resolve_ref(data['new'].root,ref).read_bytes();sha=digest(content)
                suffix={ 'text_ref':'.txt','trace_ref':'.json','identity_ref':'.json'}.get(key,'')
                if key=='raw_ref':suffix=Path(proof['original_locator']['raw_ref']).suffix.lower()
                if suffix not in ['.pdf','.docx','.doc','.png','.jpg','.txt','.jsonl','.json']:suffix='.bin'
                local='proof_assets/'+sha+suffix;files['review/'+local]=content
                mounts[ref]=dict(package_ref=ref,local_ref=local,sha256=sha,size_bytes=len(content),source_status='pending',review_scope='selected slices only, not whole-file review')
    extraction_bindings={}
    for d in details.values():
        for cell in d['cells']:
            eid=cell['extraction_id'];e=data['new'].extractions[eid]
            selected={}
            for kind in ['raw','text']:
                sha=e[kind+'_sha256'];mount=next((v for v in mounts.values() if v['sha256']==sha),None)
                if mount is None:
                    asset=next(a for a in data['new'].assets.values() if a['sha256']==sha)
                    ref=asset['package_ref'];content=resolve_ref(data['new'].root,ref).read_bytes()
                    if digest(content)!=sha:raise ValueError('Cell extraction asset hash differs')
                    local='proof_assets/'+sha+('.txt' if kind=='text' else Path(e['raw_ref']).suffix.lower())
                    files['review/'+local]=content;mounts[ref]=dict(package_ref=ref,local_ref=local,sha256=sha,size_bytes=len(content),source_status='pending',review_scope='selected cell slices only')
                    mount=mounts[ref]
                selected[kind+'_sha256']=sha;selected[kind+'_local_ref']=mount['local_ref']
            extraction_bindings[eid]=selected
    files['review/extraction_bindings.selected.json']=encode(extraction_bindings)
    files['review/source_assets.json']=encode(list(mounts.values()))
    files['review/pool.jsonl']=jsonl(pool);files['review/disposition.jsonl']=jsonl(assembled['disposition'])
    files['review/queries.jsonl']=jsonl([data['queries'][q] for q in QUERIES])
    files['review/retrieval_deltas.five.jsonl']=jsonl([x for x in data['comparison'] if x['query_id'] in QUERIES])
    files['review/top10.v6.frozen.jsonl']=jsonl([h for h in data['runs'] if h['query_id'] in QUERIES])
    files['review/evidence.jsonl']=jsonl(evidence);files['review/proposals.jsonl']=jsonl(proposals)
    files['review/history/accepted.v5.selected.jsonl']=jsonl([a for a in data['all_accepted'] if a['query_id'] in QUERIES])
    outside=[dict(query_id=a['query_id'],record_id=a['record_id'],record_type=a['record_type'],annotation_id=a['annotation_id'],row_sha256=bm.hashed(a),disposition='outside five-query review; inventory only') for a in data['all_accepted'] if a['query_id'] not in QUERIES]
    files['review/history/outside_inventory.jsonl']=jsonl(outside)
    files['review/history/pending_outside.jsonl']=jsonl([dict(calibration_id=a['calibration_id'],query_id=a['query_id'],record_id=a['record_id'],relevance=None,row_sha256=bm.hashed(a),status='pending_on_v5_outside_scope') for a in data['pending']])
    aggregate=load(data['paths']['aggregate']);receipts=[]
    for spec in aggregate['batches']:
        path=labels.bound_file(spec).parent/'receipt.json';receipts.append(dict(original_manifest=spec,receipt=load(path),receipt_sha256=digest(path.read_bytes())))
    files['review/history/receipts.v5.json']=encode(receipts)
    progress=[];sheets=[]
    for number,qid in enumerate(QUERIES,1):
        selected=[p for p in pool if p['query_id']==qid];groups={k:sum(p['classification']==k for p in selected) for k in 'ABCD'}
        progress.append(dict(query_id=qid,total_pool=len(selected),groups=groups,old_v5_decisions=sum(p['old_decision'] is not None for p in selected),
            accepted_v6=0,awaiting_user=len(selected),new_pairs=sum(p['old_decision'] is None for p in selected),coverage_complete=False))
        text=['# Phiếu v6 — '+qid,'**Query nguyên văn:** '+data['queries'][qid]['query'],
            'Đây là proposal-visible / AI-assisted; không gọi independent hoặc blind. Quyết định v5 chỉ là lịch sử, chưa là quyết định v6. Nguồn/edition/applicability pending.',
            'Không suy relevance/completeness từ rank. Điền bản sao template ngoài bundle; chưa kết luận giữ null/pending.']
        for p in selected:
            a=byproposal[p['review_pair_id']];d=details[p['record_id']];old=p['old_decision']
            text+=['## '+p['review_pair_id']+' — nhóm '+p['classification'],*qr.record_text(d)]
            text+=['**Quyết định v5 (nguyên lý do, không nhập lại):**',canonical({k:old[k] for k in ['relevance','relation','completeness','reason','reviewer_ref','reviewed_at']} ) if old else 'Chưa có quyết định v5 cho cặp này.',
                '**Membership v5 → v6:** '+p['old_unit_role']+' → target; rời Top10 không là mất membership.',
                '**Khác biệt:** '+('Chỉ version/package locator/binding đổi; payload/context/closure/source proof resolved tương đương.' if p['classification']=='A' else 'Closure/evidence thay đổi, cần rà riêng.' if p['classification']=='B' else 'Target/cặp mới; chưa có quyết định.' if p['classification']=='C' else 'Thiếu bằng chứng tương đương.'),
                '**Proposal agent, chưa duyệt:** '+canonical({k:a[k] for k in ['relevance','relation','completeness','reason']}),
                '**Evidence cụ thể:**']
            for e in [e for e in evidence if e['review_pair_id']==p['review_pair_id']]:text+=['`'+e['evidence_id']+'` — '+e['locator']['field_pointer'],'```text',e['locator']['quote'],'```']
            text+=['[Đọc đầy đủ required-read, nguồn và locator](../evidence/'+p['record_id']+'.md)',
                '**Người dùng:** ☐ đồng ý quyết định cũ ☐ sửa ☐ giữ pending — chưa điền.']
        ref='review/sheets/'+str(number).zfill(2)+'-'+qid+'.md';files[ref]=('\n\n'.join(text)+'\n').encode();sheets.append(dict(query_id=qid,ref=ref,pairs=len(selected)))
    files['review/progress.jsonl']=jsonl(progress);files['review/sheets.json']=encode(sheets)
    equivalence=[dict(review_pair_id=p['review_pair_id'],query_id=p['query_id'],record_id=p['record_id'],old_decision_sha256=p['old_decision_sha256'],
        decision={k:p['old_decision'][k] for k in ['relevance','relation','completeness','reason']},evidence_ids=byproposal[p['review_pair_id']]['evidence_ids']) for p in pool if p['classification']=='A']
    files['review/equivalence_list.jsonl']=jsonl(equivalence)
    table=['# Năm query v6 — chưa có quyết định mới','| Query | Pool | A tương đương | B closure đổi | C mới | D chưa rõ | Accepted v6 |','|---|---:|---:|---:|---:|---:|---:|']
    for p in progress:table.append('| '+p['query_id']+' | '+' | '.join(str(v) for v in [p['total_pool'],*[p['groups'][k] for k in 'ABCD'],0])+' |')
    table+=['53 quyết định v5 được đối chiếu;6 accepted ngoài phạm vi chỉ inventory;2 pending V3-D02 không đổi. Pool hữu hạn, không suy đã tìm mọi positive.',
        'Nhóm A: có thể xác nhận theo danh sách exact trong equivalence_list.jsonl, nhưng template vẫn chưa có xác nhận. Nhóm B/C/D phải rà riêng.',
        'Tuổi giữ relevance2/partial chỉ là proposal thận trọng; closure2→16 chưa tự biến full. Đèn đỏ proposal2/partial dựa own text+lead/7reads, không rank4. Khoảng cách giữ boundary/điều kiện và dependency-only.',
        'Các file raw đầy đủ trong proof_assets chỉ là bằng chứng cho slices; không có xác minh toàn file hoặc legal verified.']
    for s in sheets:table.append('['+s['query_id']+'](sheets/'+Path(s['ref']).name+')')
    files['review/OVERVIEW.md']=('\n\n'.join([table[0], '\n'.join(table[1:3+len(progress)]), *table[3+len(progress):]])+'\n').encode()
    files['review/config.snapshot.json']=encode(cfg)
    core_metadata=dict(contract=VERSION,binding=data['binding'],snapshot='2025-01-01',accepted_v6=0,human_events_created=0,metrics=None,scope='five_queries_only',
        prepared_at=cfg['agent_recorded_at'],adapter_sha256=digest(Path(__file__).read_bytes()),inputs=cfg['inputs'])
    pack_manifest(files,'review/',core_metadata);review_sha=digest(files['review/manifest.json'])
    template=dict(contract=VERSION,binding=data['binding'],review_manifest_sha256=review_sha,pool_sha256=digest(files['review/pool.jsonl']),
        reviewer_ref=None,reviewed_at=None,ai_assisted=None,independent=None,blind=None,
        review_method='proposal_visible_ai_assisted; new explicit confirmation required',
        equivalent_confirmation=dict(pair_ids=[p['review_pair_id'] for p in pool if p['classification']=='A'],outcome=None,evidence_refs_used_by_pair={}),
        items=[dict(**{k:p[k] for k in ['review_pair_id','query_id','record_id','record_type','query_sha256','record_sha256','full_read_sha256']},
            proposal_sha256=bm.hashed(byproposal[p['review_pair_id']]),outcome=None,relevance=None,relation=None,completeness=None,reason=None,evidence_refs_used=[]) for p in pool])
    files['templates/submission.template.json']=encode(template)
    files['packet_validator.py']=(BASE_DIR/'src/binding_review_packet.py').read_bytes()
    files['README.md']=("""# Gói review v6 — phiên15

Mở review/OVERVIEW.md rồi năm phiếu review/sheets/. Đây là proposal-visible có AI hỗ trợ; không independent/blind. Hiện accepted v6=0, metrics=null. Phân loại A/B/C/D chỉ là kết quả kỹ thuật, không phê duyệt tự động; kiểm số thực trong progress.

Xem decision v5 và evidence mới theo từng cặp. Source proof assets có local_ref trong review/source_assets.json; mở đúng file đó, không mở staging ref lịch sử. Đọc required-read đầy đủ ở review/evidence và review/details. Offsets quote tương đối field JSON; offsets native thuộc normalized extraction gốc. Package locator đổi được map sang proof_assets; không sửa original locators/hash/offset.

Sao chép templates/submission.template.json ra thư mục ngoài gói seal. Không sửa bundle. Điền reviewer_ref/reviewed_at thực tế; nếu dùng proposal, ai_assisted=true, independent=false, blind=false. Giữ nguyên IDs/hashes/binding. Mỗi item chọn confirm_previous (đúng cả relevance/relation/completeness/reason cũ), change (có lý do/evidence), hoặc pending (null/uncertain). Bằng chứng đã thực sự dùng lấy đúng EV6 ID trên phiếu, không tự chọn tất cả.

Có thể xác nhận exact danh sách A bằng equivalent_confirmation.outcome=confirm_list, giữ pair_ids nguyên vẹn và điền evidence_refs_used_by_pair cho từng cặp đã đọc. Không đưa B/C/D vào nhóm này; không điền item trùng quyết định nhóm. Các item chưa kết luận giữ nguyên null; hai pending V3-D02 không nằm trong template.

Chạy bằng Python >=3.11, chỉ stdlib, không cần index/model/repo:
```
python -I -B packet_validator.py --packet .
python -I -B packet_validator.py --packet . --response ../submission.NEW.json
```
Validator portable kiểm integrity/evidence/template, không là bằng chứng tương đương độc lập thay consumer. Repo validate còn replay từ input/code đã ghim. Manifest review/manifest.json seal nội dung review; template pin hash manifest đó để tránh vòng tự hash. Manifest cấp gốc seal cả review+template+validator; SHA ZIP bảo vệ cả gói.

Chưa có URL chia sẻ. Kiểm ZIP SHA do người bàn giao cung cấp, không sửa seal để pass. Chỉ sau khi có phản hồi thực tế và kiểm binding mới mới chuẩn bị adapter nhập v6 riêng; không chạy admit v5 cho v6. Phiên này không nhập accepted/qrels hoặc metrics.
""").encode()
    pack_manifest(files,'',dict(contract=VERSION,review_manifest_sha256=review_sha,accepted_v6=0,human_events_created=0,metrics=None))
    return files,dict(pool=len(pool),groups=dict(Counter(p['classification'] for p in pool)),progress=progress,accepted_v6=0,metrics=None)


def build(config,run_dir):
    data=inputs(config);files,report=packet_files(data)
    output=Path(run_dir).resolve()
    if any(output.is_relative_to(p.parent) for p in data['paths'].values()):raise ValueError('Output must not be nested in immutable input directories')
    root=bm.new_output(output)
    for ref,content in files.items():
        p=resolve_ref(root,ref);p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(content)
    validate(root,expected=files,data=data)
    return report


def validate(root,expected=None,data=None):
    root=Path(root);from src.binding_review_packet import validate as integrity
    result=integrity(root)
    if expected is None:
        data=inputs(root/'review/config.snapshot.json');expected,_=packet_files(data)
    if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}!=set(expected):raise ValueError('Review packet files missing/extra')
    for ref,content in expected.items():
        if resolve_ref(root,ref).read_bytes()!=content:raise ValueError('Review semantic replay differs: '+ref)
    if data is not None:
        class View:
            def __init__(self):
                self.members=data['new'].targets;self.records={rid:f['record'] for rid,f in data['new'].frames.items()}
            def detail(self,rid):return detail_for(data['new'],rid)
        view=View()
        for a in rows(root/'review/proposals.jsonl'):
            review.validate_annotation(a,data['queries'],view,root/'review',data['binding']);review.validate_focus_roles(a,view.detail(a['record_id']))
            for e in a['evidence_locators']:review.validate_quote(view.detail(a['record_id']),e)
    return dict(result,semantic_replay=True)


def archive(root,path):
    root,path=Path(root),Path(path)
    if path.exists() or path.resolve().is_relative_to(root.resolve()):raise ValueError('ZIP must be new outside packet')
    from src.binding_review_packet import validate as integrity
    integrity(root)
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
            if p.is_file():
                info=zipfile.ZipInfo('review-v6/'+p.relative_to(root).as_posix(),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    sha=digest(path.read_bytes());path.with_suffix(path.suffix+'.sha256').write_text(sha+'  '+path.name+'\n',encoding='ascii');return dict(zip=path.as_posix(),sha256=sha,size_bytes=path.stat().st_size)


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    q=s.add_parser('build');q.add_argument('--config',type=Path,required=True);q.add_argument('--run-dir',type=Path,required=True)
    for name in ['validate','zip','validate-response']:
        q=s.add_parser(name);q.add_argument('--packet',type=Path,required=True)
        if name=='zip':q.add_argument('--output',type=Path,required=True)
        if name=='validate-response':q.add_argument('--response',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.action=='build':result=build(a.config,a.run_dir)
        elif a.action=='validate':result=validate(a.packet)
        elif a.action=='zip':result=archive(a.packet,a.output)
        else:
            from src.binding_review_packet import response
            result=response(a.packet,a.response)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,OSError,TypeError,IndexError,StopIteration) as e:print(str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
