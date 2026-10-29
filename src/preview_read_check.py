"""Stdlib read-probe checks. Inspection only: no dataset, search or admission."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def canonical(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def resolve(root, ref):
    p = (Path(root) / ref).resolve()
    if not p.is_relative_to(Path(root).resolve()): raise ValueError('Unsafe read-probe path')
    return p


def proof(root, p, cache=None):
    cache={} if cache is None else cache
    def asset(ref,kind):
        path=resolve(root,ref);key=(str(path),kind)
        if key not in cache:
            b=path.read_bytes()
            if kind=='text':
                value=b.decode('utf-8')
                if value!=unicodedata.normalize('NFC',value)or '\r'in value:raise ValueError('Wrong normalized offset space')
            elif kind=='trace':value=json.loads(b)
            else:value=b
            cache[key]=(sha(b),value)
        return cache[key]
    raw_hash,_=asset(p['raw_ref'],'raw');text_hash,text=asset(p['text_ref'],'text')
    if raw_hash!=p['raw_sha256']or text_hash!=p['text_sha256']:raise ValueError('Wrong raw/text binding')
    _,trace=asset(p['trace_ref'],'trace')
    ident = load(resolve(root, p['identity_ref'])) if p.get('identity_ref') else p['identity_payload']
    content_key=(p['trace_ref'],'content_hash')
    if content_key not in cache:
        content = {**trace, 'nodes': [{k:v for k,v in n.items() if k not in {'locator_id','parent_locator_id','extraction_id'}} for n in trace['nodes']]}
        cache[content_key]=sha(canonical(content).encode())
    if (p['extraction_id'] != 'e_' + sha(canonical(ident).encode()) or ident['source_raw_sha256'] != p['raw_sha256']
            or ident['text_sha256'] != p['text_sha256'] or ident['trace_content_sha256'] != cache[content_key]
            or ident['file_id'] != p['file_id']): raise ValueError('Extraction identity/proof binding mismatch')
    a,b = p['char_start'],p['char_end']
    if type(a)is not int or type(b)is not int or not 0 <= a < b <= len(text) or text[a:b] != p['quote'] or sha(p['quote'].encode()) != p['quote_sha256']:
        raise ValueError('Wrong offsets/quote proof')
    nodes = [n for n in trace['nodes'] if n['locator'] == p['locator'] and n['char_start'] <= a < b <= n['char_end']]
    if not nodes: raise ValueError('Wrong native locator/range')
    box=p.get('bbox_pdf_top_origin')
    if box is not None:
        loc=nodes[0]['locator']
        if not(0<=box[0]<box[2]<=loc['width']and 0<=box[1]<box[3]<=loc['height']):raise ValueError('Invalid measured PDF bbox')
    return p['quote']


def encoding(e, text):
    if not isinstance(e,dict):raise ValueError('Missing encoder evidence')
    if (e['input_sha256'] != sha(text.encode()) or e['truncation'] is not False or e['tokens_with_special'] > 256
            or e['tokens_with_special'] != len(e['after']['token_ids'])
            or e['after']['token_ids_sha256'] != sha(canonical(e['after']['token_ids']).encode())
            or e['encoder_text_sha256'] != sha(e['encoder_text'].encode())):
        raise ValueError('Encoder binding/budget/truncation mismatch')


def views(record):
    if record['record_id'] != 'rv_' + sha(canonical(record['identity']).encode()): raise ValueError('Wrong view ID')
    if record['identity']['source_record_sha256'] != sha(canonical(record['source_record']).encode()): raise ValueError('Wrong view source')
    if (record['text_for_search']!=record['source_record']['text_for_search']or record['text_original']!=record['source_record']['text_original']
            or record['content_sha256']!=sha(record['text_for_search'].encode())
            or record['identity']['views']!=[{k:v[k]for k in ['view_no','search_char_start','search_char_end']}for v in record['encoder_views']]):
        raise ValueError('View source content/ranges mismatch')
    cursor=0;cuts={0,len(record['text_for_search']),*[m.end()for m in re.finditer(r'\n|;|[.!?](?=\s)',record['text_for_search'])]}
    for i,v in enumerate(record['encoder_views'],1):
        a,b=v['search_char_start'],v['search_char_end']
        if a != cursor or not a < b <= len(record['text_for_search']) or a not in cuts or b not in cuts or v['view_no'] != i or v['independent_target'] is not False:
            raise ValueError('View gap/independent target')
        if v['input_text'] != record['text_for_search'][a:b]: raise ValueError('Wrong view slice')
        encoding(v['encoding'],v['input_text']); cursor=b
    if cursor != len(record['text_for_search']): raise ValueError('Incomplete encoder views')


def check(root, frame, capabilities):
    if not set(frame['required_capabilities']) <= set(capabilities): raise ValueError('Missing consumer capability')
    if frame['human_review'] is not None or frame['release_eligible'] is not False: raise ValueError('False review status')
    if frame.get('source_conflict') or frame.get('independent_encoder_view'): raise ValueError('Conflict/view cannot be target')
    r=frame['record']; kind=frame['record_type']
    if frame['record_id']!=r.get('chunk_id',r.get('retrieval_id',r.get('record_id'))):raise ValueError('Frame/record ID mismatch')
    if set(frame['expected_dependency_ids']) != {d['dependency_id'] for d in frame['dependencies']}:
        raise ValueError('Missing required-read dependency')
    if any(uid.startswith('OLD_') for d in frame['dependencies'] for uid in d.get('unit_ids', [])):
        raise ValueError('Stale dependency ID')
    grouped={};cache={}
    for p in frame['native_proofs']:
        if p['raw_sha256'] not in frame['allowed_source_hashes']: raise ValueError('Wrong selected source')
        grouped.setdefault(p['use'], []).append(proof(root,p,cache))
    own_uid=r.get('unit_id',r.get('owner_unit_id',r.get('source_record',{}).get('unit_id',r.get('source_record',{}).get('region_unit_id'))))
    required_units={uid for d in frame['dependencies']for uid in d.get('unit_ids',[])}-{own_uid}
    loaded={u['unit_id']:u for u in frame.get('dependency_units',[])}
    if required_units!=set(loaded):raise ValueError('Consumer omitted required unit content')
    for uid,u in loaded.items():
        for field in ['title','text_original']:
            if '\n'.join(grouped.get('dependency:'+uid+':'+field,[]))!=u[field]:raise ValueError('Required unit field/proof mismatch')
    if kind=='chunk.v1':
        keys=['unit_id','segment_no','unit_char_start','unit_char_end','text_original','chunk_policy_version','law_id','law_title','citation_path','source_url','effective_from','effective_to','applicability_status']
        contexts=frame['contexts']; ctxkeys=['unit_id','field_name','char_start','char_end','context_role','context_order']
        ident={'identity_schema':'chunk.v1',**{k:r[k]for k in keys},'contexts':[{k:c[k]for k in ctxkeys}for c in contexts]}
        if r['chunk_id'] != 'c_'+sha(canonical(ident).encode()): raise ValueError('Wrong chunk identity')
        if r['content_sha256']!=sha(r['text_for_search'].encode()):raise ValueError('Wrong content hash')
        if '\n'.join(grouped.get('target', [])) != r['text_original']: raise ValueError('Missing target text/proof')
        ctx=[]
        for c in contexts:
            text='\n'.join(grouped.get('context:'+str(c['context_order']), []));ctx.append(text)
            if text != c['text_original']: raise ValueError('Context field proof mismatch')
        context='\n'.join(ctx) if ctx else None
        if r['context_text']!=context or r['text_for_search']!='\n\n'.join(t for t in [r['law_title'],r['citation_path'],context,r['text_original']] if t is not None):
            raise ValueError('Wrong search/context recipe')
        encoding(frame['encoding'],r['text_for_search'])
    elif kind=='source-retrieval.v1':
        views(r)
        if '\n'.join(grouped.get('target',[]))!=r['text_original']:raise ValueError('Whole-source target proof incomplete')
    elif kind=='form-retrieval.v1':
        ident={'identity_schema':'form-retrieval.v1',**{k:r[k]for k in ['law_id','citation_path','source_raw_sha256','extraction_id','char_start','char_end','text_original','form_fields']}}
        if r['record_id']!='fr_'+sha(canonical(ident).encode()):raise ValueError('Wrong form identity')
        full=next(p for p in frame['native_proofs'] if p['use']=='form_page')
        if full['quote']!=r['text_original'] or full['raw_sha256']!=r['source_raw_sha256']:raise ValueError('Wrong form page')
        text=resolve(root,full['text_ref']).read_text(encoding='utf-8');cursor=r['char_start']
        for i,f in enumerate(r['form_fields']):
            p=f['source_proof'];a,b=p['char_start'],p['char_end']
            if not cursor<=a<b<=r['char_end'] or text[cursor:a].strip() or text[a:b]!=f['text_original']:
                raise ValueError('Missing/modified form field/instruction')
            if '\n'.join(grouped.get('form_field:'+str(i), []))!=f['text_original']:raise ValueError('Missing form field proof')
            cursor=b
        if text[cursor:r['char_end']].strip():raise ValueError('Form tail/instructions omitted')
    elif kind=='table-owner-retrieval.v1':
        if r['record_id']!='tr_'+sha(canonical({k:v for k,v in r.items()if k!='record_id'}).encode()):raise ValueError('Wrong table-owner identity')
        if not r['tables'] or not r['cells'] or not r['bindings']:raise ValueError('Incomplete table/header/cells')
        for d in r['required_dependencies']:
            if d['kind']!='annex_source_regions':continue
            matches=[x for x in frame.get('loaded_required_dependencies',[])if x.get('annex')==d['annex']]
            if len(matches)!=1:raise ValueError('Required annex not read')
            x=matches[0];a=d['annex']
            if set(a['line_region_ids'])!={v['region_id']for v in x['lines']}or set(a['table_ids'])!={t['table_id']for t in x['tables']}:
                raise ValueError('Required annex lines/tables omitted')
            expected={c for t in x['tables']for row in t['cell_slots']for c in row if c}
            if expected!={c['cell_id']for c in x['cells']}:raise ValueError('Required annex cells omitted')
    elif kind=='table-retrieval.v1':
        ident={k:v for k,v in r.items()if k not in {'retrieval_id','legacy_preview_id','encoder','technical_status','downstream_blocker'}}
        if r['retrieval_id']!='tr_'+sha(canonical(ident).encode()):raise ValueError('Wrong table row identity')
        encoding(frame['encoding'],r['text_for_search'])
    else: raise ValueError('Unsupported record type')
    return {'record_id':frame['record_id'],'record_type':kind,'proofs_checked':len(frame['native_proofs']),
            'dependencies_read':len(frame['dependencies']),'technical_valid':True,'release_eligible':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--record-id',required=True)
    a=p.parse_args();m=load(a.root/'probe_manifest.json')
    for f in m['files']:
        if sha(resolve(a.root,f['ref']).read_bytes())!=f['sha256']:raise ValueError('Probe checksum mismatch')
    frame=load(resolve(a.root,m['reads'][a.record_id]))
    print(json.dumps(check(a.root,frame,m['capabilities']),ensure_ascii=False))


if __name__=='__main__':main()
