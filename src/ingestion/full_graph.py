"""Source-backed graph extensions; reuses legal grammar without changing frozen policies."""
from pathlib import Path
import copy
import re
from src.experimental_dataset import load, rows, write_json, write_rows
from src.assessment_evidence import now, seal
from src.source_contracts import canonical, digest, file_identity
from src.ingestion import legal_tree, pdf_layout, extraction_normalizer, extractors
from src.nd168_a16k2 import dom_text
from src.ingestion.full_source import NAMESPACE, hashed


def remap_graph(law, text, trace, blocks):
    eid=trace['nodes'][0]['extraction_id'];view,vt,pieces=pdf_layout.project(blocks,eid)
    old=legal_tree.parse_extraction({'law_id':law,'extraction':{'extraction_id':eid,'method':'doc_text'}},view,vt,[])
    draft=[]
    for s in old['spans']:
        for a,b,loc in pdf_layout.remap_interval(s['char_start'],s['char_end'],pieces):
            draft.append({'old':s['unit_id'],'field_name':s['field_name'],'char_start':a,'char_end':b,
                          'locator_json':canonical(loc),'extraction_id':eid,'quote_sha256':digest(text[a:b].encode())})
    units=[];spans=[];mapping={}
    for before in old['units']:
        u=copy.deepcopy(before);u['parent_unit_id']=mapping.get(before['parent_unit_id'])
        own=[]
        for field in ['title','text_original']:
            group=sorted([s for s in draft if s['old']==before['unit_id'] and s['field_name']==field],key=lambda s:s['char_start'])
            u[field]='\n'.join(text[s['char_start']:s['char_end']] for s in group)
            own.extend({**{k:v for k,v in s.items() if k!='old'},'span_order':i} for i,s in enumerate(group))
        u['text_sha256']=digest(u['text_original'].encode());u['unit_id']=legal_tree.unit_id(u)
        mapping[before['unit_id']]=u['unit_id'];units.append(u)
        for s in own:
            s['unit_id']=u['unit_id'];s['span_id']=legal_tree.span_id(s);spans.append(s)
    cov=[]
    for c in old['coverage']:
        for a,b,loc in pdf_layout.remap_interval(c['char_start'],c['char_end'],pieces):
            cov.append({**c,'char_start':a,'char_end':b,'locator':loc,'unit_id':mapping.get(c.get('unit_id'))})
    for s in trace['separators']:
        cov.append({'extraction_id':eid,'law_id':law,'char_start':s['char_start'],'char_end':s['char_end'],
                    'category':'serialization_separator','reason':'BLOCK_LF','unit_id':None})
    issues=[]
    for q in old['issues']:
        locations=pdf_layout.remap_interval(q['char_start'],q['char_end'],pieces)
        if locations:
            value={**{k:v for k,v in q.items() if k!='issue_id'},'char_start':locations[0][0],
                   'char_end':locations[-1][1],'locator':locations[0][2]}
            value['issue_id']='pqi_'+hashed(value);issues.append(value)
    return {'units':units,'spans':spans,'issues':issues,'coverage':sorted(cov,key=lambda c:c['char_start'])}


def validate_fields(units,spans,texts):
    by={u['unit_id']:u for u in units}
    if len(by)!=len(units):raise ValueError('Duplicate unit identity')
    for u in units:
        if legal_tree.unit_id(u)!=u['unit_id'] or digest(u['text_original'].encode())!=u['text_sha256']:
            raise ValueError('Unit identity/content mismatch')
        seen=set();p=u
        while p['parent_unit_id']:
            if p['unit_id'] in seen:raise ValueError('Cycle')
            seen.add(p['unit_id']);p=by[p['parent_unit_id']]
            if p['law_id']!=u['law_id']:raise ValueError('Cross-law parent')
        for field in ['title','text_original']:
            ss=sorted([s for s in spans if s['unit_id']==u['unit_id'] and s['field_name']==field],key=lambda s:s['span_order'])
            if [s['span_order'] for s in ss]!=list(range(len(ss))):raise ValueError('Span gap')
            values=[]
            for s in ss:
                t=texts[s['extraction_id']];a,b=s['char_start'],s['char_end']
                if (not 0<=a<b<=len(t) or legal_tree.span_id(s)!=s['span_id']
                        or digest(t[a:b].encode())!=s['quote_sha256']):raise ValueError('Source span/hash mismatch')
                values.append(t[a:b])
            if '\n'.join(values)!=u[field]:raise ValueError('Field roundtrip failed')


def nd168_html(config,run_dir):
    from lxml import html
    cfg=load(config);src=Path(cfg['html_capture_ref']);raw=(src/'official.html').read_bytes()
    if digest(raw)!=cfg['html_sha256']:raise ValueError('Official HTML capture changed')
    doc=html.fromstring(raw);bodies=doc.xpath('//div[@itemprop="articleBody"]')
    if len(bodies)!=1 or '168/2024/NĐ-CP' not in ''.join(doc.xpath('//h1//text()')):
        raise ValueError('Wrong source edition/number')
    body=bodies[0]
    if body.xpath('.//table'):raise ValueError('HTML table requires separate cell reader; refusing silent loss')
    file_id=file_identity(NAMESPACE,'168/2024/NĐ-CP',digest(raw))
    children=[extractors.node('paragraph',{'format':'html','xpath':e.getroottree().getpath(e)},raw_text=dom_text(e,strict=False)) for e in body if isinstance(e.tag,str)]
    text,trace=extraction_normalizer.serialize(extractors.node('document',{'format':'html'},children=children))
    tool=canonical({'reader':'official-html-blocks.v2','code_sha256':digest(Path(__file__).read_bytes()),'normalization':'NFC_LF_ONLY'})
    ident={'identity_schema':'extraction.v1','file_id':file_id,'source_raw_sha256':digest(raw),
           'method':'html_text','tool_version':tool,'config_sha256':hashed({'body_xpath':'//div[@itemprop="articleBody"]','dom_rule':'DIV_BR_LF_INLINE_CONCAT'}),
           'text_sha256':digest(text.encode()),'trace_content_sha256':hashed(trace)}
    eid='e_'+hashed(ident)
    for n in trace['nodes']:
        n.update(extraction_id=eid,locator_id='l_'+hashed({'extraction_id':eid,'node_index':n['node_index'],'locator':n['locator']}))
        n['parent_locator_id']=None if n['parent_index'] is None else trace['nodes'][n['parent_index']]['locator_id']
    blocks=[]
    for n in trace['nodes']:
        if n['kind']!='paragraph':continue
        a,b=n['char_start'],n['char_end'];value=text[a:b]
        # The official DOM combines Chapter IV, its title, and Article52 in one
        # element. Split the grammar view only at the real LF before Điều.
        cuts=[0]
        if re.match(r'^(?:Chương|Mục)\s+',value):
            cuts += [m.start() for m in re.finditer(r'(?m)^Điều\s+[1-9]\d*\.\s+',value)]
        cuts=sorted(set(cuts+[len(value)]))
        for lo,hi in zip(cuts,cuts[1:]):
            end=a+hi
            if hi<len(value) and text[end-1:end]=='\n':end-=1
            blocks.append({'kind':'paragraph','lines':[{'text':text[a+lo:end],
                'char_start':a+lo,'char_end':end,'locator':n['locator']}]})
    parsed=remap_graph('168/2024/NĐ-CP',text,trace,blocks);validate_fields(parsed['units'],parsed['spans'],{eid:text})
    root=Path(run_dir);root.mkdir(parents=True)
    (root/'sources').mkdir();(root/'sources/official.html').write_bytes(raw)
    (root/'extraction').mkdir();(root/'extraction/normalized.txt').write_bytes(text.encode());write_json(root/'extraction/trace.json',trace)
    rec={'extraction_id':eid,'file_id':file_id,'method':'html_text','tool_version':tool,'text_ref':'extraction/normalized.txt',
         'text_sha256':ident['text_sha256'],'char_count':len(text),'review_status':'pending','created_at':now()}
    write_json(root/'extraction.json',rec);write_json(root/'extraction/identity.json',ident)
    for key,name in [('units','legal_units.pending'),('spans','source_spans.pending'),('issues','quality_issues'),('coverage','coverage')]:write_rows(root/(name+'.jsonl'),parsed[key])
    visual=[{'xpath':e.getroottree().getpath(e),'images':len(e.xpath('.//img')),'status':'nontext_region_pending_or_supporting_no_inferred_content'} for e in body if isinstance(e.tag,str) and e.xpath('.//img')]
    write_rows(root/'visual_regions.jsonl',visual)
    # Crosswalk uses exact legal location; whitespace diagnostics are never edits.
    old=rows('staging/stage4-docx-005/legal_units.pending.jsonl');by={u['canonical_path']:u for u in old if u['law_id']=='168/2024/NĐ-CP'}
    cw=[]
    for u in parsed['units']:
        before=by.get(u['canonical_path']);cw.append({'old_unit_id':before['unit_id'] if before else None,'new_unit_id':u['unit_id'],
            'law_id':u['law_id'],'canonical_path':u['canonical_path'],'relation':'new_from_source_region' if not before else
            'same_own_text' if (before['title'],before['text_original'])==(u['title'],u['text_original']) else
            'formatting_only' if ' '.join((before['title']+before['text_original']).split())==' '.join((u['title']+u['text_original']).split()) else 'source_content_difference',
            'old_text':None if not before else before['text_original'],'new_text':u['text_original'],
            'reason':'official_HTML_branch_identity_recomputed_no_DOCX_offset_reuse'})
    write_rows(root/'id_crosswalk.jsonl',cw)
    seal(root,{'manifest_type':'nd168-whole-html-graph.v1','built_at':now(),'source_capture_sha256':digest(raw),
               'origin':'agent_review','snapshot_date':'2025-01-01','release_eligible':False,'code_sha256':digest(Path(__file__).read_bytes())})
    return {'units':len(parsed['units']),'articles':sum(u['unit_type']=='article' for u in parsed['units']),
            'issues':len(parsed['issues']),'nontext_regions':len(visual),'legal_review':'pending'}
