"""Measured circular layout -> existing paragraph grammar; sparse article projection.

Parts and repeated chapters stay in a source-backed structural sidecar because
the frozen DDD has no Part level. They are never fabricated as other unit types.
"""
import copy
import re
from src.ingestion import legal_tree as grammar, pdf_layout
from src.source_contracts import canonical, digest


def visible_object(obj):
    # White text background rectangles are not table borders. Text is unchanged.
    return not (obj['object_type']=='rect' and not obj.get('stroke') and obj.get('fill')
                and obj.get('non_stroking_color') in (1, 1.0, (1,1,1)))


def select_blocks(lines, tables):
    blocks=[];support=[];structure=[];active=None;ended=False;structural=False
    for line in lines:
        v=line['text']
        if v.strip().isdigit() and (line['bbox'][1]<50 or line['bbox'][1]>790):
            support.append({**line,'reason':'RUNNING_PAGE_NUMBER'});continue
        if v.startswith('KT. BỘ TRƯỞNG'):ended=True
        if ended:
            support.append({**line,'reason':'SIGNATURE_DISTRIBUTION'});continue
        if re.match(r'^(Phần|PHẦN|Chương|CHƯƠNG|Mục)\s+',v):
            structural=True;active=None
            structure.append({**line,'reason':'REAL_ANCESTOR_OUTSIDE_SPARSE_ARTICLE_PROJECTION'})
            support.append({**line,'reason':'STRUCTURAL_HEADING_SIDECAR'});continue
        if structural and line['bold'] and not grammar.ARTICLE.match(v):
            structure.append({**line,'reason':'STRUCTURAL_TITLE'});support.append({**line,'reason':'STRUCTURAL_HEADING_SIDECAR'});continue
        structural=False
        tab=next((t for t in tables if t['page']==line['page'] and t['bbox'][1]-.5<=(line['bbox'][1]+line['bbox'][3])/2<=t['bbox'][3]+.5),None)
        if tab:
            if active is None or active.get('table_id')!=tab['table_id']:
                active={'kind':'table','table_id':tab['table_id'],'lines':[]};blocks.append(active)
            active['lines'].append(line);continue
        heading=line['bold'] and bool(grammar.ARTICLE.match(v))
        marker=heading or bool(grammar.CLAUSE.match(v) or grammar.POINT.match(v))
        if marker or active is None or active['kind']=='table' or active.get('heading') and not line['bold']:
            active={'kind':'paragraph','heading':heading,'lines':[]};blocks.append(active)
        active['lines'].append(line)
    return blocks,support,structure


def parse(record,text,trace,lines,tables):
    eid=record['extraction']['extraction_id']
    blocks,support,structure=select_blocks(lines,tables)
    view,vt,pieces=pdf_layout.project(blocks,eid)
    old=grammar.parse_extraction({'law_id':record['law_id'],'extraction':{'extraction_id':eid,'method':'doc_text'}},view,vt,[])
    drafts=[]
    for s in old['spans']:
        for a,b,loc in pdf_layout.remap_interval(s['char_start'],s['char_end'],pieces):
            drafts.append({'old_id':s['unit_id'],'field_name':s['field_name'],'char_start':a,'char_end':b,'locator_json':canonical(loc)})
    start=text.index('THÔNG TƯ\n');end=text.index('\nCăn cứ',start);root=old['units'][0]['unit_id']
    drafts=[s for s in drafts if not(s['old_id']==root and start<=s['char_start']<s['char_end']<=end)]
    for l in lines:
        if start<=l['char_start']<l['char_end']<=end:
            drafts.append({'old_id':root,'field_name':'title','char_start':l['char_start'],'char_end':l['char_end'],'locator_json':canonical(l['locator'])})
    units=[];spans=[];mapping={}
    for old_u in old['units']:
        u=copy.deepcopy(old_u);u['parent_unit_id']=mapping.get(old_u['parent_unit_id']);own=[]
        for field in ['title','text_original']:
            group=sorted([s for s in drafts if s['old_id']==old_u['unit_id'] and s['field_name']==field],key=lambda s:s['char_start'])
            u[field]='\n'.join(text[s['char_start']:s['char_end']] for s in group)
            own.extend({**{k:v for k,v in s.items() if k!='old_id'},'extraction_id':eid,'span_order':i,
                        'quote_sha256':digest(text[s['char_start']:s['char_end']].encode())} for i,s in enumerate(group))
        u['text_sha256']=digest(u['text_original'].encode());u['unit_id']=grammar.unit_id(u);mapping[old_u['unit_id']]=u['unit_id'];units.append(u)
        for s in own:
            s['unit_id']=u['unit_id'];s['span_id']=grammar.span_id(s);spans.append(s)
    issues=[];regions=[]
    for q in old['issues']:
        ranges=pdf_layout.remap_interval(q['char_start'],q['char_end'],pieces)
        if not ranges:raise ValueError('Unmapped grammar issue')
        payload={**{k:v for k,v in q.items() if k not in {'issue_id','locator','char_start','char_end'}},
                 'char_start':ranges[0][0],'char_end':ranges[-1][1],'locator':ranges[0][2]}
        issues.append({'issue_id':grammar.hashed('pqi_',payload),**payload})
    for b in blocks:
        if b['kind']=='table':
            regions.append({'char_start':b['lines'][0]['char_start'],'char_end':b['lines'][-1]['char_end'],'table_id':b['table_id']})
    coverage=pdf_layout.partition(record,text,trace,spans,support,regions,units)
    # Retain original grammar reasons for marker syntax/review regions.
    for c in coverage:
        if c['reason']!='UNCLAIMED_SOURCE':continue
        heading=next((s for s in spans if s['field_name']=='title' and s['char_start']==c['char_end']
                      and any(u['unit_id']==s['unit_id'] and u['unit_type']=='article' for u in units)),None)
        if heading and re.fullmatch(r'\s*Điều\s+[1-9]\d*[a-zđ]?\.\s*',text[c['char_start']:c['char_end']]):
            c.update(category='parsed',reason='SOURCE_ARTICLE_MARKER',unit_id=heading['unit_id']);continue
        for q in old['coverage']:
            matches=pdf_layout.remap_interval(q['char_start'],q['char_end'],pieces)
            if any(a<=c['char_start']<c['char_end']<=b for a,b,_ in matches):
                c['category']=q['category'];c['reason']=q['reason'];break
    errors=grammar.validate_tree(units,spans,{eid:(record,text,trace)},coverage)
    if errors:raise ValueError(canonical(errors))
    return {'units':units,'spans':spans,'issues':issues,'coverage':coverage,'structure':structure}
