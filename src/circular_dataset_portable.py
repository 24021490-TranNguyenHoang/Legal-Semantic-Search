"""Standalone stdlib validation/read for heterogeneous experimental composition."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

VERSION='circular-composition.v1'
CAPABILITIES={'chunk.v1','graph-part.v1.2','table-retrieval.v1','required-read-dependency.v1'}

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(x):return hashlib.sha256(x).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf8').splitlines() if s]
def resolve(root,ref):
    p=(root/ref).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('Unsafe/nonportable reference')
    return p
def inventory(root):
    return [{'path':p.relative_to(root).as_posix(),'size_bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file() and p.relative_to(root).as_posix() not in {'dataset_manifest.json','dataset_manifest.sha256','execution.json'}]
def unit_hash(u):return 'u_'+sha(canonical({'identity_schema':'unit.v1',**{k:u[k] for k in ['law_id','parent_unit_id','unit_type','designation','canonical_path','citation_path','ordinal','title','text_original']}}).encode())
def span_hash(s):return 's_'+sha(canonical({'identity_schema':'source-span.v1',**{k:v for k,v in s.items() if k!='span_id'}}).encode())
def check_encoder(e,content_hash):
    if (e['input_sha256']!=content_hash or e['truncation'] is not False or e['model_max_tokens']!=256 or
        e['tokens_with_special']!=len(e['after']['token_ids']) or e['tokens_with_special']>256 or
        e['after']['token_ids_sha256']!=sha(canonical(e['after']['token_ids']).encode()) or
        e['encoder_text_sha256']!=sha(e['encoder_text'].encode()) or e['unknown_tokens']!=e['after']['token_ids'].count(3)):
        raise ValueError('Encoder/budget binding invalid')

def proof(root,items):
    if isinstance(items,str):items=json.loads(items)
    if not items:raise ValueError('Missing required proof')
    for s in items:
        raw=resolve(root,s['raw_file_ref']).read_bytes();text=resolve(root,s['text_ref']).read_bytes()
        a,b=s['char_start'],s['char_end'];t=text.decode('utf8')
        if sha(raw)!=s['raw_sha256'] or sha(text)!=s['text_sha256'] or not 0<=a<b<=len(t) or sha(t[a:b].encode())!=s['quote_sha256']:raise ValueError('Source proof mismatch')
    return items

def field_proof(root,items,unit,field,descriptor,package):
    ss=proof(root,items);spans={s['span_id']:s for s in rows(resolve(package,descriptor['spans_ref']))}
    values=[]
    for item in ss:
        s=spans[item['span_id']]
        if s['unit_id']!=unit['unit_id'] or s['field_name']!=field or any(s[k]!=item[k] for k in ['extraction_id','char_start','char_end','quote_sha256']):raise ValueError('Proof belongs to wrong unit/field')
        t=resolve(root,item['text_ref']).read_text(encoding='utf8');values.append(t[s['char_start']:s['char_end']])
    if '\n'.join(values)!=unit[field]:raise ValueError('Proof does not reconstruct required field')

def graph(root,descriptor):
    units=rows(resolve(root,descriptor['units_ref']));spans=rows(resolve(root,descriptor['spans_ref']));by={u['unit_id']:u for u in units}
    if len(by)!=len(units):raise ValueError('Duplicate graph unit')
    texts={k:resolve(root,v).read_text(encoding='utf8') for k,v in descriptor['texts'].items()}
    for u in units:
        if u['unit_id']!=unit_hash(u) or sha(u['text_original'].encode())!=u['text_sha256']:raise ValueError('Unit hash mismatch')
        seen=set();node=u
        while node['parent_unit_id']:
            if node['unit_id'] in seen:raise ValueError('Graph cycle')
            seen.add(node['unit_id']);parent=by[node['parent_unit_id']]
            if parent['law_id']!=node['law_id'] or not node['canonical_path'].startswith(parent['canonical_path']+'/'):raise ValueError('Wrong graph parent')
            node=parent
        for field in ['title','text_original']:
            ss=sorted([s for s in spans if s['unit_id']==u['unit_id'] and s['field_name']==field],key=lambda s:s['span_order'])
            if [s['span_order'] for s in ss]!=list(range(len(ss))):raise ValueError('Span order mismatch')
            values=[]
            for s in ss:
                t=texts[s['extraction_id']];a,b=s['char_start'],s['char_end']
                if span_hash(s)!=s['span_id'] or not 0<=a<b<=len(t) or sha(t[a:b].encode())!=s['quote_sha256']:raise ValueError('Span identity/slice mismatch')
                values.append(t[a:b])
            if '\n'.join(values)!=u[field]:raise ValueError('Source field roundtrip mismatch')
    return by

def table_identity(r):
    return 'tr_'+sha(canonical({k:v for k,v in r.items() if k not in {'retrieval_id','legacy_preview_id','encoder','technical_status','downstream_blocker'}}).encode())

def validate(root,capabilities=CAPABILITIES):
    root=Path(root).resolve();m=load(root/'dataset_manifest.json')
    if set(m['required_capabilities'])!=CAPABILITIES:raise ValueError('Unknown/omitted composition capabilities')
    if not set(m['required_capabilities'])<=set(capabilities):raise ValueError('Consumer lacks required graph/record/dependency capabilities')
    if m['policy_version']!=VERSION or m['snapshot_date']!='2025-01-01' or m['status']!='draft' or m['experimental'] is not True or m['release_eligible'] is not False or m['corpus_version'] is not None or m['origin']!='agent_review' or m['human_reviewer_events']!=0:raise ValueError('Invalid composition status/snapshot')
    if sha((root/'dataset_manifest.json').read_bytes())!=(root/'dataset_manifest.sha256').read_text().strip():raise ValueError('Manifest checksum mismatch')
    if inventory(root)!=m['files'] or sha(canonical(m['files']).encode())!=m['dataset_content_sha256']:raise ValueError('Inventory/content binding mismatch')
    cfg=load(root/'selection_config.json');dispositions=rows(root/'selection.jsonl')
    if dispositions!=cfg['selection'] or cfg['snapshot_date']!=m['snapshot_date']:raise ValueError('Selection replay mismatch')
    graphs={k:graph(root,v) for k,v in m['graphs'].items()}
    sparse={u['unit_id']:u for u in rows(root/'evidence/tt35_sparse.units.jsonl')}
    cw=rows(root/'unit_crosswalk.jsonl');mapped={x['old_unit_id']:x['new_unit_id'] for x in cw if x['old_unit_id'] is not None}
    if set(mapped)!=set(sparse):raise ValueError('Incomplete old/new unit crosswalk')
    for old_id,new_id in mapped.items():
        old=sparse[old_id];new=graphs['tt35'][new_id]
        if unit_hash(old)!=old_id or any(old[k]!=new[k] for k in ['law_id','unit_type','designation','title','text_original']):raise ValueError('Crosswalk changed legal content/position')
    # Every file of the old draft is preserved, including its nested component manifests.
    base=root/'components/base';bm=load(base/'dataset_manifest.json')
    if bm['dataset_version']!='vtls-coverage-experimental.v2-draft.1' or bm['counts']['chunks']!=3082 or sha((base/'dataset_manifest.json').read_bytes())!=cfg['inputs']['base']['sha256']:raise ValueError('Wrong base draft')
    for f in bm['files']:
        p=resolve(base,f['path'])
        if sha(p.read_bytes())!=f['sha256'] or p.stat().st_size!=f['size_bytes']:raise ValueError('Base component changed')
    chunks=rows(root/'chunks.jsonl');tables=rows(root/'table_records.jsonl');contexts=rows(root/'contexts.jsonl');members=rows(root/'memberships.jsonl')
    ids=[c['chunk_id'] for c in chunks]+[r['retrieval_id'] for r in tables]
    if len(ids)!=len(set(ids)) or {r['record_id'] for r in members}!=set(ids) or len(members)!=len(ids):raise ValueError('Duplicate/missing membership')
    old={c['chunk_id']:c for c in rows(base/'chunks.jsonl')};bychunk={c['chunk_id']:c for c in chunks}
    if any(bychunk.get(cid)!=c for cid,c in old.items()):raise ValueError('Base payload not preserved')
    if [c for c in contexts if c['chunk_id'] in old]!=rows(base/'contexts.jsonl'):raise ValueError('Base contexts changed')
    membership={r['record_id']:r for r in members};selected=[s for s in dispositions if s['disposition']=='selected']
    for member in members:
        expected_type='chunk.v1' if member['record_id'] in bychunk else 'table-retrieval.v1'
        if member['record_type']!=expected_type:raise ValueError('Unsupported/mismatched record type')
    wanted={s['record_id'] for s in selected}
    if set(ids)-set(old)!=wanted:raise ValueError('Selection/target membership mismatch')
    dependencies=rows(root/'dependencies.jsonl')
    expected=[{'record_id':s['record_id'],**d} for s in selected for d in s['required_dependencies']]
    if dependencies!=expected:raise ValueError('Missing/wrong required dependency')
    for d in dependencies:
        by=graphs[d['graph_id']]
        if d['root_unit_id'] not in by:raise ValueError('Missing dependency root')
        subtree={d['root_unit_id']}
        while True:
            more={u['unit_id'] for u in by.values() if u['parent_unit_id'] in subtree}
            if more<=subtree:break
            subtree|=more
        if sorted(subtree)!=d['unit_ids']:raise ValueError('Incomplete mandatory dependency subtree')
    positions=set();matches=[]
    for cw in rows(root/'chunk_crosswalk.jsonl'):
        if mapped.get(cw['old_unit_id'])!=cw['new_unit_id']:raise ValueError('Chunk/unit crosswalk mismatch')
        if cw['new_chunk_id'] in bychunk and bychunk[cw['new_chunk_id']]['unit_id']!=cw['new_unit_id']:raise ValueError('Selected chunk crosswalk mismatch')
    for c in chunks:
        mem=membership[c['chunk_id']];u=graphs[mem['graph_id']][c['unit_id']]
        pos=(c['law_id'],u['canonical_path'])
        if pos in positions:raise ValueError('Duplicate legal position')
        positions.add(pos)
        if c['citation_path']!=u['citation_path'] or c['parent_unit_id']!=u['parent_unit_id'] or c['text_original']!=u['text_original'][c['unit_char_start']:c['unit_char_end']]:raise ValueError('Target/unit binding invalid')
        ctx=[x for x in contexts if x['chunk_id']==c['chunk_id']]
        keys=['unit_id','segment_no','unit_char_start','unit_char_end','text_original','chunk_policy_version','law_id','law_title','citation_path','source_url','effective_from','effective_to','applicability_status']
        identity={'identity_schema':'chunk.v1',**{k:c[k] for k in keys},'contexts':[{k:x[k] for k in ['unit_id','field_name','char_start','char_end','context_role','context_order']} for x in ctx]}
        if c['chunk_id']!='c_'+sha(canonical(identity).encode()) or c['content_sha256']!=sha(c['text_for_search'].encode()):raise ValueError('Chunk identity/hash mismatch')
        if c['chunk_id'] not in old:
            if [x['context_order'] for x in ctx]!=list(range(len(ctx))):raise ValueError('Context order mismatch')
            expected_context='\n'.join(graphs[mem['graph_id']][x['unit_id']][x['field_name']][x['char_start']:x['char_end']] for x in ctx) if ctx else None
            if c['context_text']!=expected_context:raise ValueError('Context content/source roundtrip mismatch')
            if c['text_for_search']!='\n\n'.join(c[k] for k in ['law_title','citation_path','context_text','text_original'] if c[k] is not None):raise ValueError('Search text mismatch')
            field_proof(resolve(root,mem['proof_base']),c['source_locator'],u,'text_original',m['graphs'][mem['graph_id']],root)
            for x in ctx:
                owner=graphs[mem['graph_id']][x['unit_id']]
                field_proof(resolve(root,mem['proof_base']),x['source_locator'],owner,x['field_name'],m['graphs'][mem['graph_id']],root)
                if not 0<=x['char_start']<x['char_end']<=len(owner[x['field_name']]):raise ValueError('Context field slice invalid')
    enc={e['chunk_id']:e for e in rows(root/'encoder_inputs.jsonl')}
    for cid in set(bychunk)-set(old):check_encoder(enc[cid],bychunk[cid]['content_sha256'])
    measured={r['table_id']:r for r in rows(root/'components/tt38/tables.jsonl')}
    table_positions=set()
    for r in tables:
        if r['record_type']!='table-retrieval.v1' or r['retrieval_id']!=table_identity(r) or r['technical_status']!='pass' or r['origin']!='agent_review' or r['release_eligible'] is not False:raise ValueError('Table record type/identity/status invalid')
        mem=membership[r['retrieval_id']];owner=graphs['tt38'][r['owner_unit_id']]
        if r['source_original']!=owner['text_original']:raise ValueError('Derived/source separation invalid')
        pr=resolve(root,mem['proof_base']);field_proof(pr,r['source_proof'],owner,'text_original',m['graphs']['tt38'],root)
        for x in r['contexts']:
            context_owner=graphs['tt38'][x['unit_id']]
            if x['text_original']!=context_owner[x['field_name']]:raise ValueError('Table condition/context changed')
            field_proof(pr,x['source_locator'],context_owner,x['field_name'],m['graphs']['tt38'],root)
        if m['mounts'].get(r['source_proof_base_ref'])!=mem['proof_base']:raise ValueError('Unmapped logical proof base')
        cells={c['cell_id']:c for c in r['cells']}
        for c in cells.values():
            if sha((root/'components/tt38/base/sources/selected.pdf').read_bytes())!=c['source_pdf_sha256']:raise ValueError('Cell raw PDF binding mismatch')
            if c['cell_id']!='pdf-cell_'+sha(canonical({k:v for k,v in c.items() if k!='cell_id'}).encode()):raise ValueError('Cell identity mismatch')
            text=resolve(root,m['graphs']['tt38']['texts'][c['extraction_id']]).read_text(encoding='utf8')
            if c['text']!='\n'.join(s['quote'] for s in c['source_slices']):raise ValueError('Cell roundtrip mismatch')
            for s in c['source_slices']:
                if text[s['char_start']:s['char_end']]!=s['quote'] or sha(s['quote'].encode())!=s['quote_sha256']:raise ValueError('Cell source slice mismatch')
        for row in r['rows']:
            position=(r['owner_unit_id'],row['table_id'],row['row'])
            if position in table_positions:raise ValueError('Duplicate table legal row')
            table_positions.add(position)
            t=measured[row['table_id']];slots=t['cell_slots'];ri=row['row'];parts=[];refs=[]
            if t['context_unit_id']!=r['owner_unit_id']:raise ValueError('Wrong table owner')
            for ci,cid in enumerate(slots[ri]):
                headers=[slots[0][ci]] if t['number']==3 else ([slots[0][0]] if ci==0 else [slots[0][1],slots[1][ci]])
                refs+=headers+[cid];parts.append(' / '.join(cells[h]['text'] for h in headers)+': '+cells[cid]['text'])
            if row['source_cell_ids']!=refs or row['text_derived']!='\n'.join(parts):raise ValueError('Wrong row/header/derived binding')
        if r['derived_text']!='\n\n'.join(x['text_derived'] for x in r['rows']) or sha(r['text_for_search'].encode())!=r['content_sha256']:raise ValueError('Table derived hash invalid')
        check_encoder(r['encoder'],r['content_sha256'])
    for s in dispositions:
        if s['origin']!='agent_review' or s['reviewer_ref'] is not None or s['release_eligible'] is not False or s['applicability']!='pending_review':raise ValueError('False reviewer/legal acceptance')
    stats={'text_chunks':len(chunks),'table_retrieval_records':len(tables),'total_retrieval_records':len(chunks)+len(tables),
        'contexts':len(contexts),'required_read_dependencies':len(dependencies),'added_text':len(chunks)-len(old),'base_unchanged':len(old),
        'withheld':sum(s['disposition']=='withheld' for s in dispositions)}
    if stats!=m['counts']:raise ValueError('Counts mismatch')
    return {'technical_valid':True,'status':'draft','release_eligible':False,'counts':stats}

def read(root,record_id,capabilities=CAPABILITIES):
    root=Path(root);validate(root,capabilities)
    allrows=rows(root/'chunks.jsonl')+rows(root/'table_records.jsonl')
    item=next(r for r in allrows if r.get('chunk_id',r.get('retrieval_id'))==record_id)
    m=load(root/'dataset_manifest.json');deps=[]
    for d in rows(root/'dependencies.jsonl'):
        if d['record_id']!=record_id:continue
        descriptor=m['graphs'][d['graph_id']];by={u['unit_id']:u for u in rows(resolve(root,descriptor['units_ref']))}
        spans=rows(resolve(root,descriptor['spans_ref']))
        deps.append({**d,'units':[by[uid] for uid in d['unit_ids']],
            'source_spans':[s for s in spans if s['unit_id'] in d['unit_ids']],'text_refs':descriptor['texts']})
    return {'record':item,'membership':next(r for r in rows(root/'memberships.jsonl') if r['record_id']==record_id),'required_read_dependencies':deps}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['validate','read']);p.add_argument('--root',type=Path,required=True);p.add_argument('--record-id');p.add_argument('--capabilities',default=','.join(sorted(CAPABILITIES)));a=p.parse_args(argv)
    try:
        result=validate(a.root,a.capabilities.split(',')) if a.action=='validate' else read(a.root,a.record_id,a.capabilities.split(','))
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,OSError,StopIteration) as e:print('ERROR: '+str(e));return 1
if __name__=='__main__':raise SystemExit(main())
