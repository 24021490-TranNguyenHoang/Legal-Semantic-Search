"""Lossless encoder views of a whole retrieval record; views are never legal targets."""
import re
from src.source_contracts import canonical,digest

VERSION='whole-record-encoder-views.v1'


def boundaries(text):
    # Preserve delimiters; no arbitrary character/word truncation.
    return sorted({0,len(text),*[m.end() for m in re.finditer(r'\n|;|[.!?](?=\s)',text)]})


def prepare(records,encode,budget=256):
    """Two batch tokenizations; final counts on exact view inputs, no model inference."""
    if budget!=256:raise ValueError('This policy retains the existing 256-token budget')
    atoms=[];plans=[]
    for record in records:
        text=record['text_for_search'];cuts=boundaries(text)
        plan=[]
        for a,b in zip(cuts,cuts[1:]):
            if a<b:
                plan.append((a,b,len(atoms)));atoms.append(text[a:b])
        plans.append(plan)
    # Empty-whitespace atoms stay attached to neighboring source text, not sent alone.
    observed=encode([t for t in atoms if t.strip()])
    iterator=iter(observed);counts=[next(iterator)['tokens_with_special'] if t.strip() else 0 for t in atoms]
    candidates=[];quarantine=[]
    for r,plan in zip(records,plans):
        views=[];start=0;cost=2;failed=False
        for a,b,i in plan:
            size=max(0,counts[i]-2)
            if counts[i]>budget:
                quarantine.append({'record':r,'reason':'SINGLE_SOURCE_SENTENCE_OR_FIELD_EXCEEDS_BUDGET','char_start':a,'char_end':b,'tokens':counts[i]});failed=True;break
            if size and cost+size>budget-8 and a>start:
                views.append((start,a));start=a;cost=2
            cost+=size
        if failed:continue
        if start<len(r['text_for_search']):views.append((start,len(r['text_for_search'])))
        candidates.append((r,views))
    inputs=[r['text_for_search'][a:b] for r,v in candidates for a,b in v]
    encoded=iter(encode(inputs));output=[]
    for r,spans in candidates:
        views=[]
        for i,(a,b) in enumerate(spans):
            e=next(encoded)
            views.append({'view_no':i+1,'search_char_start':a,'search_char_end':b,
                          'input_text':r['text_for_search'][a:b],'encoding':e,'independent_target':False})
        if any(v['encoding']['tokens_with_special']>budget for v in views):
            quarantine.append({'record':r,'reason':'EXACT_VIEW_TOKEN_BUDGET_EXCEEDED','views':views});continue
        identity={'policy_version':VERSION,'source_record_sha256':digest(canonical(r).encode()),
                  'views':[{k:v[k] for k in ['view_no','search_char_start','search_char_end']} for v in views]}
        out={'record_id':'rv_'+digest(canonical(identity).encode()),'record_type':'source-retrieval.v1','identity':identity,
             'source_record':r,'text_original':r['text_original'],'text_for_search':r['text_for_search'],
             'content_sha256':digest(r['text_for_search'].encode()),'encoder_views':views,
             'required_capabilities':['whole-record-read.v1','encoder-views.v1'],
             'origin':'agent_review','scope_proposal':r.get('scope_proposal','pending'),
             'applicability':'pending_review','release_eligible':False}
        validate(out,budget);output.append(out)
    return output,quarantine


def validate(r,budget=256):
    if r['record_type']!='source-retrieval.v1' or r['release_eligible'] is not False:
        raise ValueError('Incorrect view record status/type')
    if (r['record_id']!='rv_'+digest(canonical(r['identity']).encode())
            or r['identity']['policy_version']!=VERSION
            or r['identity']['source_record_sha256']!=digest(canonical(r['source_record']).encode())
            or r['text_original']!=r['source_record']['text_original']
            or r['text_for_search']!=r['source_record']['text_for_search']
            or r['content_sha256']!=digest(r['text_for_search'].encode())):
        raise ValueError('Whole record identity/content mismatch')
    cursor=0
    for i,v in enumerate(r['encoder_views'],1):
        a,b=v['search_char_start'],v['search_char_end'];e=v['encoding']
        if (v['view_no']!=i or a!=cursor or not a<b<=len(r['text_for_search'])
                or a not in boundaries(r['text_for_search']) or b not in boundaries(r['text_for_search'])
                or v['input_text']!=r['text_for_search'][a:b] or v['independent_target'] is not False
                or e['input_sha256']!=digest(v['input_text'].encode()) or e['truncation'] is not False
                or e['tokens_with_special']>budget or e['tokens_with_special']!=len(e['after']['token_ids'])
                or e['after']['token_ids_sha256']!=digest(canonical(e['after']['token_ids']).encode())
                or e['encoder_text_sha256']!=digest(e['encoder_text'].encode())):
            raise ValueError('Encoder view gap/slice/hash/budget/truncation mismatch')
        cursor=b
    if cursor!=len(r['text_for_search']):raise ValueError('Views do not cover full input')
