"""Stdlib integrity/evidence/blank-response validator for the sealed v6 review packet.
Repository replay additionally reconstructs content from pinned source consumers.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

VERSION='subset-v6-binding-review.v1'

def sha(b):return hashlib.sha256(b).hexdigest()
def hashed(x):return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def load(p):return json.loads(p.read_text('utf8'))
def rows(p):return [json.loads(x) for x in p.read_text('utf8').splitlines() if x]
def safe(root,ref):
    if not isinstance(ref,str) or '\\' in ref:raise ValueError('Noncanonical path')
    p=(root/ref).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('Path escapes packet')
    return p

def inventory(root):
    return [dict(path=p.relative_to(root).as_posix(),size_bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()) if p.is_file() and p.relative_to(root).as_posix() not in ['manifest.json','manifest.sha256']]

def pointer(x,path):
    for key in path[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~');x=x[int(key)] if isinstance(x,list) else x[key]
    return x

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from walk(v)
    elif isinstance(x,list):
        for v in x:yield from walk(v)

def seal(root):
    m=load(root/'manifest.json')
    if sha((root/'manifest.json').read_bytes())!=(root/'manifest.sha256').read_text().strip() or m['files']!=inventory(root):raise ValueError('Packet seal/inventory mismatch')
    return m

def validate(root):
    root=Path(root).resolve();m=seal(root);core=root/'review';cm=seal(core)
    if m['contract']!=VERSION or m['review_manifest_sha256']!=sha((core/'manifest.json').read_bytes()) or cm['accepted_v6']!=0 or cm['human_events_created']!=0 or cm['metrics'] is not None:raise ValueError('Wrong packet contract/state')
    binding=cm['binding']
    if binding['dataset_version']!='vtls-subset-experimental.v6-candidate.1' or binding['index_version']!='vtls-bm25s-subset.v2':raise ValueError('Wrong dataset/index')
    pool=rows(core/'pool.jsonl');byid={p['review_pair_id']:p for p in pool}
    if len(byid)!=len(pool) or len({(p['query_id'],p['record_id']) for p in pool})!=len(pool):raise ValueError('Duplicate pool pair')
    queries={q['query_id']:q for q in rows(core/'queries.jsonl')}
    top10=rows(core/'top10.v6.frozen.jsonl')
    pairs={(p['query_id'],p['record_id']) for p in pool}
    for qid in queries:
        hits=[h for h in top10 if h['query_id']==qid]
        if sorted(h['rank'] for h in hits)!=list(range(1,11)) or any((qid,h['record_id']) not in pairs for h in hits):raise ValueError('Missing or duplicate Top10 member')
    history=rows(core/'history/accepted.v5.selected.jsonl')
    old_by_pair={(p['query_id'],p['record_id']):p for p in history}
    dispositions=rows(core/'disposition.jsonl')
    if len(old_by_pair)!=len(history) or len(dispositions)!=len(history) or {(p['query_id'],p['record_id']) for p in dispositions}!=set(old_by_pair):raise ValueError('Missing old accepted disposition')
    for p in pool:
        old=old_by_pair.get((p['query_id'],p['record_id']))
        if p['old_decision']!=old or p['old_decision_sha256']!=(hashed(old) if old else None):raise ValueError('Historical decision changed')
        if p['query_sha256']!=hashed(queries[p['query_id']]):raise ValueError('Wrong query hash')
        if p['reviewer_decision'] is not None or p['human_review'] is not None or not p['target_membership_v6']:raise ValueError('Fake human event or supporting target')
    evidence=rows(core/'evidence.jsonl');bye={e['evidence_id']:e for e in evidence}
    if len(bye)!=len(evidence):raise ValueError('Duplicate evidence')
    details={p['record_id']:load(core/'details'/ (p['record_id']+'.json')) for p in pool}
    for p in pool:
        d=details[p['record_id']]['dataset_response']
        if hashed(d)!=p['full_read_sha256'] or hashed(d['record'])!=p['record_sha256'] or d['record_id']!=p['record_id'] or d['record_type']!=p['record_type'] or d['dataset_version']!=binding['dataset_version']:raise ValueError('Wrong target/read binding or missing proof')
    for detail in details.values():
        d=detail['dataset_response'];required=d['required_read'];member=d['membership']
        if [x['unit_id'] for x in required['unit_reads']]!=member['required_unit_ids'] or {x['record_id'] for x in required['supporting_records']}!={x['record_id'] for x in required['bindings'] if x.get('record_id')}:raise ValueError('Missing required dependency or supporting form')
    assets={x['package_ref']:x for x in load(core/'source_assets.json')}
    for a in assets.values():
        data=safe(core,a['local_ref']).read_bytes()
        if len(data)!=a['size_bytes'] or sha(data)!=a['sha256']:raise ValueError('Proof asset mismatch')
    extraction_bindings=load(core/'extraction_bindings.selected.json')
    for detail in details.values():
        if not any('package_locator' in x for x in walk(detail)) and detail['record_type']!='table-retrieval.v1':raise ValueError('Missing native proof')
        if detail['record_type']=='table-retrieval.v1' and not detail['cells']:raise ValueError('Missing table cells/headers')
        for cell in detail['cells']:
            e=extraction_bindings[cell['extraction_id']];text_bytes=safe(core,e['text_local_ref']).read_bytes();raw=safe(core,e['raw_local_ref']).read_bytes()
            if sha(text_bytes)!=e['text_sha256'] or sha(raw)!=e['raw_sha256'] or cell['source_pdf_sha256']!=e['raw_sha256'] or not cell['source_slices']:raise ValueError('Cell/raw/extraction binding mismatch')
            text=text_bytes.decode('utf8')
            for part in cell['source_slices']:
                if text[part['char_start']:part['char_end']]!=part['quote'] or sha(part['quote'].encode())!=part['quote_sha256']:raise ValueError('Cell native slice/hash mismatch')
        for proof in walk(detail):
            if 'package_locator' not in proof:continue
            loc=proof['package_locator'];original=proof['original_locator']
            for key in ['raw_ref','text_ref','trace_ref','identity_ref']:
                if loc.get(key) and loc[key] not in assets:raise ValueError('Missing proof dependency')
            text=safe(core,assets[loc['text_ref']]['local_ref']).read_text('utf8')
            if text[loc['char_start']:loc['char_end']]!=original['quote'] or sha(original['quote'].encode())!=original['quote_sha256']:raise ValueError('Native source offset/quote mismatch')
            for key,field in [('raw_ref','raw_sha256'),('text_ref','text_sha256')]:
                if field in original and assets[loc[key]]['sha256']!=original[field]:raise ValueError('Wrong raw/extraction hash binding')
    for e in evidence:
        p=byid[e['review_pair_id']];detail=details[p['record_id']];q=e['locator'];text=pointer(detail,q['field_pointer'])
        if text[q['char_start']:q['char_end']]!=q['quote'] or sha(q['quote'].encode())!=q['quote_sha256']:raise ValueError('Evidence quote binding differs')
    proposals=rows(core/'proposals.jsonl')
    if {p['review_pair_id'] for p in proposals}!=set(byid) or len(proposals)!=len(byid):raise ValueError('Proposal pool differs')
    for p in proposals:
        if p['origin']!='agent_review' or p['status'] not in ['proposed','pending'] or p['reviewer_ref'] is not None or p['human_review'] is not None:raise ValueError('Agent cannot create accepted/human review')
        if not p['evidence_ids'] or any(x not in bye or bye[x]['review_pair_id']!=p['review_pair_id'] for x in p['evidence_ids']):raise ValueError('Missing evidence')
    template=load(root/'templates/submission.template.json')
    if template['binding']!=binding or template['review_manifest_sha256']!=m['review_manifest_sha256'] or template['pool_sha256']!=sha((core/'pool.jsonl').read_bytes()):raise ValueError('Wrong response binding')
    if any(template[k] is not None for k in ['reviewer_ref','reviewed_at','ai_assisted','independent','blind']):raise ValueError('Template inherits reviewer event')
    if template['equivalent_confirmation']['outcome'] is not None or template['equivalent_confirmation']['evidence_refs_used_by_pair']:raise ValueError('Fake group confirmation')
    if len(template['items'])!=len(pool) or {p['review_pair_id'] for p in template['items']}!=set(byid):raise ValueError('Template pairs missing/duplicate')
    for item in template['items']:
        p=byid[item['review_pair_id']]
        proposal=next(a for a in proposals if a['review_pair_id']==p['review_pair_id'])
        if item['proposal_sha256']!=hashed(proposal):raise ValueError('Wrong proposal binding')
        for key in ['query_id','record_id','record_type','query_sha256','record_sha256','full_read_sha256']:
            if item[key]!=p[key]:raise ValueError('Template identity differs')
        if any(item[k] is not None for k in ['outcome','relevance','relation','completeness','reason']) or item['evidence_refs_used']:raise ValueError('Template contains decisions')
    return dict(technical_valid=True,pool=len(pool),groups={x:sum(p['classification']==x for p in pool) for x in 'ABCD'},accepted_v6=0,metrics=None)

def response(root,path):
    root=Path(root);validate(root);template=load(root/'templates/submission.template.json');value=load(Path(path))
    if set(value)!=set(template):raise ValueError('Unknown/missing response fields, no accepted/human event fields allowed')
    for key in ['contract','binding','review_manifest_sha256','pool_sha256']:
        if value[key]!=template[key]:raise ValueError('Response binding differs')
    originals={p['review_pair_id']:p for p in template['items']};ev={x['evidence_id']:x for x in rows(root/'review/evidence.jsonl')};proposals={p['review_pair_id']:p for p in rows(root/'review/proposals.jsonl')}
    if len(value['items'])!=len(originals) or {x['review_pair_id'] for x in value['items']}!=set(originals):raise ValueError('Missing/duplicate response pairs')
    decisions=[]
    def evidence(pid,refs):
        if not refs or any(x not in ev or ev[x]['review_pair_id']!=pid for x in refs) or len(set(refs))!=len(refs):raise ValueError('Missing/wrong used evidence')
    group=value['equivalent_confirmation'];expected=template['equivalent_confirmation']['pair_ids']
    if set(group)!=set(template['equivalent_confirmation']):raise ValueError('Unknown group confirmation fields')
    if group['pair_ids']!=expected:raise ValueError('Equivalent list changed')
    if group['outcome'] is not None:
        if group['outcome']!='confirm_list' or set(group['evidence_refs_used_by_pair'])!=set(expected):raise ValueError('Group confirmation incomplete')
        for pid in expected:evidence(pid,group['evidence_refs_used_by_pair'][pid]);decisions.append(pid)
    for p in value['items']:
        original=originals[p['review_pair_id']];pid=p['review_pair_id']
        if set(p)!=set(original):raise ValueError('Unknown/missing response item fields')
        for k in ['query_id','record_id','record_type','query_sha256','record_sha256','full_read_sha256','proposal_sha256']:
            if p[k]!=original[k]:raise ValueError('Response identity differs')
        if p['outcome'] is None:
            if any(p[k] is not None for k in ['relevance','relation','completeness','reason']) or p['evidence_refs_used']:raise ValueError('Unconfirmed response has decision data')
            continue
        if pid in decisions or p['outcome'] not in ['confirm_previous','change','pending']:raise ValueError('Duplicate/invalid outcome')
        evidence(pid,p['evidence_refs_used'])
        old=next(x for x in rows(root/'review/pool.jsonl') if x['review_pair_id']==pid)['old_decision']
        if p['outcome']=='confirm_previous' and (old is None or any(p[k]!=old[k] for k in ['relevance','relation','completeness','reason'])):raise ValueError('Confirm previous requires exact old decision')
        rel=p['relevance'];relation=p['relation'];complete=p['completeness']
        if p['outcome']=='pending' and rel is not None:raise ValueError('Pending must remain null, not zero')
        legal=(rel is None and relation==complete=='uncertain' and p['outcome']=='pending') or (type(rel) is int and ((rel==0 and (relation,complete)==('unrelated','none')) or (rel==1 and relation in ['supporting_target','dependency_only'] and complete=='partial') or (rel==2 and relation=='direct_target' and complete in ['partial','full'])))
        if not legal or not p['reason']:raise ValueError('Invalid rubric/reason')
        decisions.append(pid)
    if decisions:
        if Path(path).resolve().is_relative_to(root.resolve()):raise ValueError('Filled response must be outside sealed packet')
        if not value['reviewer_ref'] or not value['reviewed_at'] or value['ai_assisted'] is not True or value['independent'] is not False or value['blind'] is not False:raise ValueError('Missing actual reviewer/AI-assisted metadata')
        t=datetime.fromisoformat(value['reviewed_at'].replace('Z','+00:00'))
        if t.tzinfo is None or t>datetime.now(timezone.utc):raise ValueError('Invalid actual review time')
    return dict(valid_response=True,decisions_present=len(decisions),unconfirmed=len(originals)-len(decisions),accepted_created=0,import_supported=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packet',type=Path,required=True);p.add_argument('--response',type=Path);a=p.parse_args()
    try:print(json.dumps(response(a.packet,a.response) if a.response else validate(a.packet),ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,OSError,TypeError,IndexError) as e:print(str(e));return 1

if __name__=='__main__':raise SystemExit(main())
