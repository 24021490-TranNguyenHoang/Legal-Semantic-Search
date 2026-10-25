"""Stdlib candidate reader: explicit membership, whole-record views and form layout."""
import argparse
import importlib.util
import json
from pathlib import Path
import hashlib
import re
import sys
import unicodedata

VERSION='seven-source-candidate.v1.3'
CAPABILITIES={'circular-composition.v1','explicit-scope-membership.v1','whole-record-read.v1','encoder-views.v1','form-layout-read.v1'}
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(v):return hashlib.sha256(v).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def rows(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf8').splitlines() if s.strip()]
def resolve(root,ref):
    p=(Path(root)/ref).resolve()
    if not p.is_relative_to(Path(root).resolve()):raise ValueError('Unsafe package path')
    return p
def inventory(root):
    root=Path(root)
    return [{'path':p.relative_to(root).as_posix(),'size_bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
        for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()) if p.is_file()
        and p.relative_to(root).as_posix() not in {'dataset_manifest.json','dataset_manifest.sha256'}]
def component(root):
    sys.dont_write_bytecode=True
    path=Path(root)/'components/v3'
    spec=importlib.util.spec_from_file_location('frozen_v3_portable',path/'validate_read.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return path,module


def check_views(r):
    src=r['source_record'];identity=r['identity'];text=r['text_for_search'];cursor=0
    if (r['record_type']!='source-retrieval.v1' or r['record_id']!='rv_'+sha(canonical(identity).encode())
        or identity['source_record_sha256']!=sha(canonical(src).encode()) or r['text_original']!=src['text_original']
        or text!=src['text_for_search'] or sha(text.encode())!=r['content_sha256']
        or r['release_eligible'] is not False or not text or not r['encoder_views']
        or identity['policy_version']!='whole-record-encoder-views.v1' or r['origin']!='agent_review'
        or r['applicability']!='pending_review'
        or set(r['required_capabilities'])!={'whole-record-read.v1','encoder-views.v1'}):
        raise ValueError('Whole record identity/content mismatch')
    expected=[{k:v[k] for k in ['view_no','search_char_start','search_char_end']} for v in r['encoder_views']]
    if identity['views']!=expected:raise ValueError('View identity offsets changed')
    boundaries={0,len(text),*[m.end() for m in re.finditer(r'\n|;|[.!?](?=\s)',text)]}
    for i,v in enumerate(r['encoder_views'],1):
        a,b=v['search_char_start'],v['search_char_end'];e=v['encoding']
        if (v['view_no']!=i or a!=cursor or not a<b<=len(text) or a not in boundaries or b not in boundaries
            or v['input_text']!=text[a:b] or v['independent_target'] is not False or e['truncation'] is not False
            or e['input_sha256']!=sha(v['input_text'].encode()) or not 2<=e['tokens_with_special']<=256
            or e['tokens_with_special']!=len(e['after']['token_ids']) or e['model_max_tokens']!=256
            or e['after']['token_ids_sha256']!=sha(canonical(e['after']['token_ids']).encode())
            or e['encoder_text_sha256']!=sha(e['encoder_text'].encode()) or e['unknown_tokens']!=e['after']['token_ids'].count(3)
            or e.get('role')!='document' or e.get('preprocessing_version')!='phobert-pyvi-input.v1'):
            raise ValueError('Encoder view source/hash/budget mismatch')
        cursor=b
    if cursor!=len(text):raise ValueError('View gap/truncation')


def mounted(root,m,ref):
    if ref not in m['proof_mounts']:raise ValueError('Required source not mounted')
    return resolve(root,m['proof_mounts'][ref])


def extraction_binding(root,m,eid):
    d=m['extraction_bindings'][eid]
    text_bytes=mounted(root,m,d['text_ref']).read_bytes();text=text_bytes.decode('utf8')
    trace_bytes=mounted(root,m,d['trace_ref']).read_bytes();trace=json.loads(trace_bytes)
    ident=load(mounted(root,m,d['identity_ref']))
    content={**trace,'nodes':[{k:v for k,v in n.items() if k not in {'locator_id','parent_locator_id','extraction_id'}} for n in trace['nodes']]}
    if (eid!='e_'+sha(canonical(ident).encode()) or ident['identity_schema']!='extraction.v1'
        or ident['file_id']!=d['file_id'] or ident['source_raw_sha256']!=d['source_raw_sha256']
        or sha(text_bytes)!=d['text_sha256'] or ident['text_sha256']!=d['text_sha256']
        or sha(trace_bytes)!=d['trace_sha256'] or ident['trace_content_sha256']!=sha(canonical(content).encode())
        or text!=unicodedata.normalize('NFC',text) or '\r' in text):raise ValueError('Extraction identity/normalization/trace binding mismatch')
    return d,text,trace


def locate_proof(root,m,p):
    d,text,trace=extraction_binding(root,m,p['extraction_id']);a,b=p['char_start'],p['char_end']
    page=next((n for n in trace['nodes'] if n['kind']=='page' and n['locator']==p['locator'] and n['char_start']<=a<b<=n['char_end']),None)
    if d['file_id']!=p['file_id'] or page is None:raise ValueError('Wrong extraction/file/page locator or range')
    bbox=p.get('bbox_pdf_top_origin')
    if bbox is not None:
        if not (len(bbox)==4 and 0<=bbox[0]<bbox[2]<=page['locator']['width'] and 0<=bbox[1]<bbox[3]<=page['locator']['height']):raise ValueError('Invalid source bbox')
    return d,text


def direct_proof(root,m,p):
    raw=mounted(root,m,p['raw_ref']).read_bytes();tb=mounted(root,m,p['text_ref']).read_bytes();t=tb.decode('utf8')
    a,b=p['char_start'],p['char_end']
    d,source=locate_proof(root,m,p)
    if (d['text_ref']!=p['text_ref'] or source!=t or d['source_raw_sha256']!=p['raw_sha256']
        or sha(raw)!=p['raw_sha256'] or sha(tb)!=p['text_sha256'] or not 0<=a<b<=len(t) or t[a:b]!=p['quote'] or sha(p['quote'].encode())!=p['quote_sha256']):
        raise ValueError('Source quote/raw/extraction binding mismatch')
    return p['quote']


def check_form(root,m,r):
    if (r['record_type']!='form-retrieval.v1' or r['origin']!='agent_review' or r['release_eligible'] is not False
        or r['applicability']!='pending_review' or r['visual_review']['origin']!='agent_review'
        or set(r['required_capabilities'])!={'form-layout-read.v1'}):raise ValueError('False form status/origin/capability')
    ident={k:r[k] for k in ['law_id','citation_path','source_raw_sha256','extraction_id','char_start','char_end','text_original','form_fields']}
    ident={'identity_schema':'form-retrieval.v1',**ident}
    if r['identity']!=ident or r['record_id']!='fr_'+sha(canonical(ident).encode()):raise ValueError('Form identity mismatch')
    raw=mounted(root,m,r['raw_ref']).read_bytes();text=mounted(root,m,r['text_ref']).read_text(encoding='utf8')
    d,source,trace=extraction_binding(root,m,r['extraction_id'])
    if d['file_id']!=r['file_id'] or d['source_raw_sha256']!=r['source_raw_sha256'] or d['text_ref']!=r['text_ref'] or source!=text:raise ValueError('Wrong form extraction/file binding')
    if sha(raw)!=r['source_raw_sha256'] or text[r['char_start']:r['char_end']]!=r['text_original'] or sha(r['text_original'].encode())!=r['text_sha256']:
        raise ValueError('Form full source mismatch')
    seen=set();last=r['char_start']
    for f in r['form_fields']:
        p=f['source_proof'];a,b=p['char_start'],p['char_end']
        locate_proof(root,m,p)
        if (f['source_region_id'] in seen or p['extraction_id']!=r['extraction_id'] or p['file_id']!=r['file_id']
            or not r['char_start']<=a<b<=r['char_end'] or a<last or not p['bbox_pdf_top_origin']
            or text[a:b]!=f['text_original'] or p['quote']!=f['text_original'] or sha(p['quote'].encode())!=p['quote_sha256']):
            raise ValueError('Form field/layout source mismatch')
        seen.add(f['source_region_id']);last=b
    # Every non-whitespace source character must be in a preserved field, not just a title.
    cursor=r['char_start']
    for f in r['form_fields']:
        p=f['source_proof']
        if text[cursor:p['char_start']].strip():raise ValueError('Missing form label/instruction')
        cursor=p['char_end']
    if text[cursor:r['char_end']].strip():raise ValueError('Missing form tail')


def validate(root,capabilities=CAPABILITIES):
    root=Path(root).resolve();m=load(root/'dataset_manifest.json')
    if set(m['required_capabilities'])!=CAPABILITIES or not CAPABILITIES<=set(capabilities):raise ValueError('Missing/unknown consumer capability')
    if (m['policy_version']!=VERSION or m['status']!='draft' or m['snapshot_date']!='2025-01-01'
        or m['experimental'] is not True or m['release_eligible'] is not False or m['corpus_version'] is not None
        or m['origin']!='agent_review' or m['human_reviewer_events']!=0):raise ValueError('False review/status/snapshot')
    if sha((root/'dataset_manifest.json').read_bytes())!=(root/'dataset_manifest.sha256').read_text().strip():raise ValueError('Manifest checksum mismatch')
    if inventory(root)!=m['files'] or sha(canonical(m['files']).encode())!=m['dataset_content_sha256']:raise ValueError('Package inventory mismatch')
    cp,old=component(root);old.validate(cp)
    if sha((cp/'dataset_manifest.json').read_bytes())!=m['input_bindings']['v3']['sha256']:raise ValueError('Wrong base version binding')
    cm=load(cp/'dataset_manifest.json');graphs={k:old.graph(cp,v) for k,v in cm['graphs'].items()}
    base={r.get('chunk_id',r.get('retrieval_id')):r for fn in ['chunks.jsonl','table_records.jsonl'] for r in rows(cp/fn)}
    base_members={r['record_id']:r for r in rows(cp/'memberships.jsonl')}
    raw_added=rows(root/'additions/chunks.jsonl');added={r['chunk_id']:r for r in raw_added};ctx=rows(root/'additions/contexts.jsonl')
    if len(added)!=len(raw_added) or set(added)&set(base):raise ValueError('Duplicate/colliding added chunk identity')
    enc={r['chunk_id']:r for r in rows(root/'additions/encoder_inputs.jsonl')}
    for rid,c in added.items():
        u=graphs['tt35'][c['unit_id']];own=sorted([x for x in ctx if x['chunk_id']==rid],key=lambda x:x['context_order'])
        ident={'identity_schema':'chunk.v1',**{k:c[k] for k in ['unit_id','segment_no','unit_char_start','unit_char_end','text_original','chunk_policy_version','law_id','law_title','citation_path','source_url','effective_from','effective_to','applicability_status']},
            'contexts':[{k:x[k] for k in ['unit_id','field_name','char_start','char_end','context_role','context_order']} for x in own]}
        context='\n'.join(graphs['tt35'][x['unit_id']][x['field_name']][x['char_start']:x['char_end']] for x in own) if own else None
        if (rid!='c_'+sha(canonical(ident).encode()) or c['text_original']!=u['text_original'] or c['citation_path']!=u['citation_path']
            or c['parent_unit_id']!=u['parent_unit_id'] or c['context_text']!=context or c['unit_char_start']!=0 or c['unit_char_end']!=len(u['text_original'])
            or [x['context_order'] for x in own]!=list(range(len(own)))
            or c['text_for_search']!='\n\n'.join(c[k] for k in ['law_title','citation_path','context_text','text_original'] if c[k] is not None)):
            raise ValueError('Added chunk identity/context mismatch')
        old.check_encoder(enc[rid],sha(c['text_for_search'].encode()))
        old.field_proof(cp/'components/tt35',c['source_locator'],u,'text_original',cm['graphs']['tt35'],cp)
        for x in own:old.field_proof(cp/'components/tt35',x['source_locator'],graphs['tt35'][x['unit_id']],x['field_name'],cm['graphs']['tt35'],cp)
    raw_views=rows(root/'additions/records.jsonl');raw_forms=rows(root/'additions/forms.jsonl')
    views={r['record_id']:r for r in raw_views};forms={r['record_id']:r for r in raw_forms}
    if len(views)!=len(raw_views) or len(forms)!=len(raw_forms) or set(views)&set(forms):raise ValueError('Duplicate view/form identity')
    qg={n['region_unit_id']:n for n in rows(root/'additions/qcvn.graph.jsonl')}
    for r in forms.values():check_form(root,m,r)
    allrows={**base,**added,**views,**forms};members=rows(root/'memberships.jsonl');ids=[x['record_id'] for x in members]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate membership')
    positions=set();new_proposals={p['unit_id']:p for p in rows(root/'additions/scope.proposals.jsonl')}
    base_proposals={p['chunk_id']:p for p in rows(cp/'components/base/metadata.jsonl')}
    base_proposals.update({p['record_id']:p for p in rows(cp/'selection.jsonl')})
    for member in members:
        rid=member['record_id'];r=allrows[rid]
        expected_type=base_members[rid]['record_type'] if rid in base else 'chunk.v1' if rid in added else 'source-retrieval.v1' if rid in views else 'form-retrieval.v1'
        expected_location='component-v3' if rid in base else 'additions'
        if member['record_type']!=expected_type or member['location']!=expected_location:raise ValueError('Record type/location does not match membership payload')
        if (member['scope_proposal']!='included' or member['origin']!='agent_review' or member['release_eligible'] is not False
            or member['applicability']!='pending_review' or member['reviewer_ref'] is not None):raise ValueError('Membership false scope/reviewer status')
        proposal=base_proposals.get(rid) if rid in base else new_proposals.get(r.get('unit_id')) if rid in added else r
        if proposal is None or proposal.get('scope_proposal')!='included':raise ValueError('Pending/excluded cannot become target')
        if rid in views:
            check_views(r);s=r['source_record'];citation=s['citation_path'];law=s['law_id']
            if s['scope_proposal']!='included':raise ValueError('Source scope not included')
            if s.get('record_type')=='qcvn-source-subtree.v1':
                target=qg[s['region_unit_id']];subtree={target['region_unit_id']}
                while True:
                    expanded=subtree|{n['region_unit_id'] for n in qg.values() if n['parent_region_unit_id'] in subtree}
                    if expanded==subtree:break
                    subtree=expanded
                if set(s['subtree_member_ids'])!=subtree:raise ValueError('QCVN subtree dependency missing')
                expected=[p for n in qg.values() if n['region_unit_id'] in subtree for p in n['source_proofs']]
                actual=[{k:v for k,v in p.items() if k not in {'raw_ref','raw_sha256','text_ref','text_sha256'}} for p in s['source_proofs']]
                if sorted(canonical(p) for p in actual)!=sorted(canonical(p) for p in expected):raise ValueError('Wrong QCVN source-region binding')
                expected=qg[target['parent_region_unit_id']]['source_proofs']
                actual=[{k:v for k,v in p.items() if k not in {'raw_ref','raw_sha256','text_ref','text_sha256'}} for p in s['context_proofs']]
                if actual!=expected:raise ValueError('Wrong QCVN context parent')
                text='\n'.join(direct_proof(root,m,p) for p in s['source_proofs'])
                context='\n'.join(direct_proof(root,m,p) for p in s['context_proofs'])
                if text!=s['text_original'] or context!=s['context_text'] or s['text_for_search']!='\n\n'.join(['QCVN 41:2024/BGTVT',citation,context,text]):raise ValueError('QCVN subtree/context source mismatch')
            elif s.get('source_graph')=='tt38':
                u=graphs['tt38'][s['unit_id']];a=graphs['tt38'][s['explicit_dependency_unit_id']]
                old.field_proof(cp/'components/tt38',s['own_source_locator'],u,'text_original',cm['graphs']['tt38'],cp)
                for x in s['contexts']:
                    owner=graphs['tt38'][x['unit_id']]
                    if x['text_original']!=owner[x['field_name']]:raise ValueError('Rain context binding mismatch')
                    old.field_proof(cp/'components/tt38',x['source_locator'],owner,x['field_name'],cm['graphs']['tt38'],cp)
                rows_by={(x['table_id'],x['row']):x for t in rows(cp/'table_records.jsonl') for x in t['rows']}
                cells={x['cell_id']:x for t in rows(cp/'table_records.jsonl') for x in t['cells']}
                if not any(x['unit_id']==a['unit_id'] for x in s['contexts']):raise ValueError('Rain point-a dependency missing')
                if any(rows_by[(x['table_id'],x['row'])]!=x for x in s['table_rows']) or any(cells[x['cell_id']]!=x for x in s['source_cells']):raise ValueError('Rain header/row/cell mismatch')
                expected_rows=[x for x in rows_by.values() if x['owner_unit_id']==a['unit_id']]
                if s['table_rows']!=sorted(expected_rows,key=lambda x:x['row']):raise ValueError('Rain table3 dependency incomplete')
                derived='\n\n'.join(x['text_derived'] for x in s['table_rows'])
                law_title=next(c['law_title'] for c in base.values() if c.get('law_id')==law and 'law_title' in c)
                if s['text_original']!=u['text_original'] or s['text_derived']!=derived or s['text_for_search']!='\n\n'.join([law_title,citation,*[c['text_original'] for c in s['contexts']],u['text_original'],derived]):raise ValueError('Rain full meaning/search mismatch')
            else:raise ValueError('Unsupported source-retrieval binding')
        else:
            if member['record_type']=='table-retrieval.v1':
                u=graphs[base_members[rid]['graph_id']][r['owner_unit_id']];law=u['law_id'];citation=u['citation_path']
            else:law=r['law_id'];citation=r['citation_path']
        pos=(law,citation)
        # Different physical table rows remain distinct; other duplicate legal targets are rejected.
        if member['record_type']=='table-retrieval.v1':pos+=(r['rows'][0]['table_id'],r['rows'][0]['row'])
        if pos in positions:raise ValueError('Duplicate legal position/source branch')
        positions.add(pos)
    dep=rows(root/'additions/dependencies.jsonl');uid_to_added={c['unit_id']:c['chunk_id'] for c in added.values()}
    for d in dep:
        if d['unit_id'] not in uid_to_added:raise ValueError('Dependency lacks target')
        if uid_to_added[d['unit_id']] not in ids:continue
        graph_id=d.get('graph_id','tt35');pool=graphs[graph_id]
        if d['root_unit_id'] not in pool:raise ValueError('Missing dependency graph root')
        expected={d['root_unit_id']}
        while True:
            expanded=expected|{u['unit_id'] for u in pool.values() if u['parent_unit_id'] in expected}
            if expanded==expected:break
            expected=expanded
        if expected!=set(d['unit_ids']) or not d['required']:raise ValueError('Dependency subtree incomplete')
    for c in added.values():
        if c['chunk_id'] in ids and re.search(r'/article:34/clause:2/point:[ab]$',graphs['tt35'][c['unit_id']]['canonical_path']):
            required={'article:17/clause:1','article:17/clause:2','article:17/clause:3','article:29/clause:3','article:15/clause:1/point:b'}
            actual={graphs['tt35'][d['root_unit_id']]['canonical_path'].split('/article:')[-1] for d in dep if d['unit_id']==c['unit_id'] and d.get('dependency_role')!='snapshot_transition'}
            actual={'article:'+p for p in actual}
            if actual!=required:raise ValueError('Missing/wrong A34 required-read dependencies')
    for c in added.values():
        if c['chunk_id'] not in ids:continue
        transition=[d for d in dep if d['unit_id']==c['unit_id'] and d.get('dependency_role')=='snapshot_transition']
        observed={(d.get('graph_id','tt35'),graphs[d.get('graph_id','tt35')][d['root_unit_id']]['canonical_path'].split('/article:')[-1]) for d in transition}
        if observed!={('tt35','66/clause:1'),('tt35','67'),('base-docx','89/clause:3')}:raise ValueError('Snapshot/transition required-read evidence missing')
    form_deps=rows(root/'additions/form_dependencies.jsonl')
    for d in form_deps:
        if d['record_id'] not in ids or d['form_record_id'] not in forms or not d['required']:raise ValueError('Missing target/form dependency')
        form=forms[d['form_record_id']]
        if form['source_annex']['literal_marker']!='XXVI' or not d['via_unit_id'] in graphs['tt35']:raise ValueError('Wrong application form binding')
        if not graphs['tt35'][d['via_unit_id']]['canonical_path'].endswith('article:29/clause:3/point:b'):raise ValueError('Wrong form reference source')
    for c in added.values():
        if c['chunk_id'] in ids and re.search(r'/article:34/clause:2/point:[ab]$',graphs['tt35'][c['unit_id']]['canonical_path']):
            if len([d for d in form_deps if d['record_id']==c['chunk_id']])!=1:raise ValueError('Application form dependency absent')
    from collections import Counter
    counts=dict(Counter(x['record_type'] for x in members))
    if counts!=m['record_counts'] or len(ids)!=m['total_records']:raise ValueError('Candidate count mismatch')
    return {'technical_valid':True,'total_records':len(ids),'record_counts':counts,'status':'draft','legal_review':'pending','release_eligible':False}


def read(root,record_id,capabilities=CAPABILITIES):
    root=Path(root);validate(root,capabilities);m=load(root/'dataset_manifest.json')
    member=next(x for x in rows(root/'memberships.jsonl') if x['record_id']==record_id)
    cp,old=component(root)
    if member['location']=='component-v3':return {'component_root':'components/v3',**old.read(cp,record_id)}
    for fn in ['records','forms','chunks']:
        for r in rows(root/f'additions/{fn}.jsonl'):
            if r.get('record_id',r.get('chunk_id'))!=record_id:continue
            if fn=='chunks':
                cm=load(cp/'dataset_manifest.json');deps=[]
                for d in rows(root/'additions/dependencies.jsonl'):
                    if d['unit_id']!=r['unit_id']:continue
                    desc=cm['graphs'][d.get('graph_id','tt35')];units={u['unit_id']:u for u in rows(resolve(cp,desc['units_ref']))}
                    deps.append({**d,'units':[units[u] for u in d['unit_ids']],
                        'spans':[s for s in rows(resolve(cp,desc['spans_ref'])) if s['unit_id'] in d['unit_ids']],
                        'texts':desc['texts'],'text_refs_root':'components/v3'})
                forms={f['record_id']:f for f in rows(root/'additions/forms.jsonl')}
                required_forms=[{**d,'form':forms[d['form_record_id']]} for d in rows(root/'additions/form_dependencies.jsonl') if d['record_id']==record_id]
                return {'record':r,'contexts':[c for c in rows(root/'additions/contexts.jsonl') if c['chunk_id']==record_id],
                    'required_read_dependencies':deps,'required_forms':required_forms,'proof_mounts':m['proof_mounts'],
                    'membership':member,'proof_root':'components/v3/components/tt35'}
            return {'record':r,'membership':member,'proof_mounts':m['proof_mounts'],
                'required_read_notice':'Read whole record, all contexts, fields/cells/dependencies; encoder views are never standalone targets'}
    raise ValueError('Member payload missing')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['validate','read']);p.add_argument('--root',type=Path,required=True);p.add_argument('--record-id');p.add_argument('--capabilities',default=','.join(sorted(CAPABILITIES)));a=p.parse_args(argv)
    try:
        result=validate(a.root,a.capabilities.split(',')) if a.action=='validate' else read(a.root,a.record_id,a.capabilities.split(','))
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,OSError,StopIteration) as e:print('ERROR: '+str(e));return 1
if __name__=='__main__':raise SystemExit(main())
