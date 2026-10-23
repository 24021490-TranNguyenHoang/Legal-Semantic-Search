"""Scoped circular priority projections; invoked by existing PDF preview CLI."""
from pathlib import Path
from collections import Counter
import copy
import re
import shutil
from src.assessment_evidence import check_files, inventory, now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import canonical, digest
from src.config import BASE_DIR
from src.pipeline_cli import staging_path
from src.ingestion import legal_tree, circular_preview, table_preview
from src import chunk_preview_v2, chunk_preview_articles, encoder_input
from src.chunk_preview import source_proof, chunk_identity

VERSION='circular-priority.v1.2'
SCHEMA=BASE_DIR/'schemas/circular_priority_v1_2.json'


def graph(base):
    old=rows(base/'legal_units.pending.jsonl');spans=rows(base/'source_spans.pending.jsonl')
    deps={r['unit_id']:r for r in rows(base/'unit_structure_dependencies.jsonl')}
    recs=rows(base/'extraction_snapshot/extractions.pending.jsonl')
    texts={r['extraction']['extraction_id']:(base/'extraction_snapshot'/r['extraction']['text_ref']).read_text(encoding='utf8') for r in recs}
    eid=next(s['extraction_id'] for s in spans if s['unit_id']==old[0]['unit_id'])
    root=old[0];work={u['unit_id']:copy.deepcopy(u) for u in old};proof=copy.deepcopy(spans);keys={};part=root['unit_id']
    groups=[]
    for line in rows(base/'structure.pending.jsonl'):
        m=re.match(r'^(Phần|Chương)\s+(\S+)',line['text'])
        if m:groups.append({'kind':'part' if m[1]=='Phần' else 'chapter','designation':m[2],'lines':[line]})
        elif groups:groups[-1]['lines'].append(line)
    for g in groups:
        lines=g['lines'];key='structure:'+str(lines[0]['char_start'])
        parent=root['unit_id'] if g['kind']=='part' else part
        if g['kind']=='part':part=key
        work[key]={'law_id':root['law_id'],'unit_type':g['kind'],'designation':g['designation'],
            'parent_unit_id':parent,'title':'\n'.join(l['text'] for l in lines),'text_original':'','text_sha256':digest(b'')}
        keys[lines[0]['char_start']]=key
        for i,l in enumerate(lines):proof.append({'unit_id':key,'extraction_id':eid,'field_name':'title','span_order':i,
            'char_start':l['char_start'],'char_end':l['char_end'],'locator_json':canonical(l['locator']),'quote_sha256':digest(l['text'].encode())})
    for u in old:
        if u['unit_type']=='article':
            ancestors=deps[u['unit_id']]['source_ancestors']
            work[u['unit_id']]['parent_unit_id']=keys[ancestors[-1]['source_lines'][0]['char_start']] if ancestors else root['unit_id']
    pos=lambda key:min((s['char_start'] for s in proof if s['unit_id']==key),default=-1)
    children={k:sorted([c for c,v in work.items() if v['parent_unit_id']==k],key=pos) for k in work}
    result=[];mapped={};cross=[];newspans=[]
    def visit(key,parent=None,ordinal=0):
        u=work[key];u['parent_unit_id']=parent['unit_id'] if parent else None;u['ordinal']=ordinal
        u['canonical_path']=(parent['canonical_path']+'/' if parent else '')+u['unit_type']+':'+u['designation']
        label={'part':'Phần','chapter':'Chương','article':'Điều','clause':'Khoản','point':'Điểm','document':''}[u['unit_type']]
        u['citation_path']=(parent['citation_path']+' > ' if parent else '')+((label+' ') if label else '')+u['designation']
        u['unit_id']=legal_tree.unit_id(u);mapped[key]=u['unit_id'];result.append(u)
        cross.append({'old_unit_id':key if not key.startswith('structure:') else None,'new_unit_id':u['unit_id'],
            'reason':'real_part_chapter_parent_path_citation_ordinal' if key in {v['unit_id'] for v in old} else 'restored_source_ancestor',
            'own_content_unchanged':key in {v['unit_id'] for v in old}})
        for s in sorted([s for s in proof if s['unit_id']==key],key=lambda s:(s['field_name'],s['span_order'])):
            s={**s,'unit_id':u['unit_id']};s.pop('span_id',None);s['span_id']=legal_tree.span_id(s);newspans.append(s)
        for i,c in enumerate(children[key]):visit(c,u,i)
    visit(root['unit_id'])
    validate_graph(result,newspans,texts)
    return result,newspans,cross,mapped


def validate_graph(units,spans,texts):
    import jsonschema
    schema=load(SCHEMA)
    for unit in units:jsonschema.validate(unit,schema)
    by={u['unit_id']:u for u in units}
    if len(by)!=len(units) or len({u['canonical_path'] for u in units})!=len(units):raise ValueError('Duplicate graph identity/path')
    allowed={'document':{'part','article'},'part':{'chapter','article'},'chapter':{'article'},'article':{'clause','point'},'clause':{'point'},'point':set()}
    roots=[]
    for u in units:
        if digest(u['text_original'].encode())!=u['text_sha256']:raise ValueError('Unit text hash mismatch')
        if legal_tree.unit_id(u)!=u['unit_id']:raise ValueError('Unit identity mismatch')
        if u['parent_unit_id'] is None:roots.append(u);continue
        p=by[u['parent_unit_id']]
        if p['law_id']!=u['law_id'] or u['unit_type'] not in allowed[p['unit_type']] or not u['canonical_path'].startswith(p['canonical_path']+'/'):raise ValueError('Invalid structural parent')
        seen=set();v=u
        while v['parent_unit_id']:
            if v['unit_id'] in seen:raise ValueError('Graph cycle')
            seen.add(v['unit_id']);v=by[v['parent_unit_id']]
    if len(roots)!=1:raise ValueError('Wrong graph roots')
    for u in units:
        for field in ['title','text_original']:
            ss=sorted([s for s in spans if s['unit_id']==u['unit_id'] and s['field_name']==field],key=lambda s:s['span_order'])
            if [s['span_order'] for s in ss]!=list(range(len(ss))):raise ValueError('Span order gap')
            values=[]
            for s in ss:
                t=texts[s['extraction_id']];a,b=s['char_start'],s['char_end']
                if not 0<=a<b<=len(t) or legal_tree.span_id(s)!=s['span_id'] or digest(t[a:b].encode())!=s['quote_sha256']:raise ValueError('Span mismatch')
                values.append(t[a:b])
            if '\n'.join(values)!=u[field]:raise ValueError('Graph field roundtrip mismatch')


def selected_chunks(base,units,spans,mapping):
    src=rows(base/'extraction_snapshot/source_snapshot/files.pending.jsonl');main=next(s for s in src if s['file_role']=='main')
    rec=next(r for r in rows(base/'extraction_snapshot/extractions.pending.jsonl') if r['extraction']['file_id']==main['file_id'])
    doc=rows(base/'extraction_snapshot/source_snapshot/documents.pending.jsonl')[0]
    selected=[p for p in rows(base/'scope.proposals.jsonl') if p['scope_proposal']=='included']
    data={'document':{'law_id':doc['law_id'],'source_id':doc['source_id'],'law_title':doc['declared']['law_title'],'source_url':doc['declared']['source_url_candidate']},
        'units':units,'spans':spans,'issues':rows(base/'parser_issues.jsonl'),
        'extractions':[{**rec['extraction'],'text_ref':'extraction_snapshot/'+rec['extraction']['text_ref']}],
        'files':[{'file_id':main['file_id'],'law_id':main['law_id'],'raw_file_ref':'sources/'+Path(main['measured']['raw_file_ref']).name,
            'sha256':main['measured']['sha256'],'size_bytes':main['measured']['size_bytes']}]}
    cfg={'chunk_policy_version':chunk_preview_v2.VERSION,'snapshot_date':'2025-01-01','token_limit':256,
        'required_context_fields':['title'],'required_clause_context_fields':['text_original'],'target_unit_ids':[mapping[p['unit_id']] for p in selected]}
    encode=lambda ts:encoder_input.encode_inputs(ts,load(base/'encoder_config.json'),base/'tokenizer_assets')['rows']
    combined={k:[] for k in ['chunks','contexts','quarantined','issues','encoder_inputs','unit_results','dependency_checks']}
    for builder,article in [(chunk_preview_v2,False)]:
        own={**cfg,'chunk_policy_version':builder.VERSION}
        own['target_unit_ids']=[mapping[p['unit_id']] for p in selected if
            (next(u for u in units if u['unit_id']==mapping[p['unit_id']])['unit_type']=='article')==article]
        result=builder.build_chunks(data,base,own,['PENDING_SOURCE','PENDING_APPLICABILITY','AGENT_REVIEW_ONLY','EXPERIMENTAL_NOT_CORPUS'],encode,reference_prefix='tt35/')
        for k in combined:combined[k].extend(result[k])
    # Leaf-article v1 rank enum has no Part. Rebind only already validated leaf
    # previews after graph validation, retaining its search/context formula.
    for old in rows(base/'chunks.preview.jsonl'):
        if old['unit_id'] not in cfg['target_unit_ids'] and old['unit_id'] not in {p['unit_id'] for p in selected}:continue
        u=next(u for u in units if u['unit_id']==mapping[old['unit_id']])
        if u['unit_type']!='article':continue
        if any(c['parent_unit_id']==u['unit_id'] for c in units):raise ValueError('Not a leaf article')
        c=copy.deepcopy(old);c.update(unit_id=u['unit_id'],parent_unit_id=u['parent_unit_id'],citation_path=u['citation_path'],chunk_policy_version='leaf-article-part-ancestry.v1',
            source_locator=source_proof(data,base,u,'text_original','tt35/'),release_blockers=['PENDING_SOURCE','PENDING_APPLICABILITY','AGENT_REVIEW_ONLY','EXPERIMENTAL_NOT_CORPUS'])
        contexts=[]
        for ctx in rows(base/'contexts.preview.jsonl'):
            if ctx['chunk_id']==old['chunk_id']:
                ctx=copy.deepcopy(ctx);ctx['unit_id']=mapping[ctx['unit_id']]
                owner=next(n for n in units if n['unit_id']==ctx['unit_id'])
                ctx['source_locator']=source_proof(data,base,owner,ctx['field_name'],'tt35/');contexts.append(ctx)
        c['text_for_search']='\n\n'.join(t for t in [c['law_title'],c['citation_path'],c['context_text'],c['text_original']] if t is not None)
        c['content_sha256']=digest(c['text_for_search'].encode());c['chunk_id']='c_'+digest(canonical(chunk_identity(c,contexts)).encode())
        for ctx in contexts:ctx['chunk_id']=c['chunk_id']
        enc=encode([c['text_for_search']])[0];passed=enc['tokens_with_special']<=256
        combined['encoder_inputs'].append({**enc,'unit_id':u['unit_id'],'chunk_id':c['chunk_id'],'within_budget':passed})
        if passed:combined['chunks'].append(c);combined['contexts'].extend(contexts)
        else:combined['quarantined'].append({'candidate':c,'contexts':contexts,'reason':'TOKEN_BUDGET_EXCEEDED'})
    return combined


def calculate(root):
    base=root/'tt35';table=Path(load(root/'binding.json')['tables']['ref']).parent
    if not table.is_absolute():table=BASE_DIR/table
    units,spans,cross,mapping=graph(base);built=selected_chunks(base,units,spans,mapping)
    records=[]
    for c,e in zip(rows(table/'candidates.jsonl'),rows(table/'encoder_inputs.jsonl')):
        payload={'record_type':'table-retrieval.v1','policy':'source-cell-owner.v1','owner_unit_id':c['unit_id'],
            'source_proof_base_ref':str(table.relative_to(BASE_DIR)).replace('\\','/'),
            'source_original':c['text_original'],'source_proof':c['own_source_locator'],'contexts':c['contexts'],
            'rows':c['table_rows'],'cells':c['source_cells'],'derived_text':c['text_derived'],'text_for_search':c['text_for_search'],
            'content_sha256':c['content_sha256'],'dependency_unit_id':c['explicit_dependency_unit_id'],
            'origin':'agent_review','scope_proposal':c['scope_proposal'],'applicability':'pending_review','release_eligible':False}
        records.append({**payload,'retrieval_id':'tr_'+digest(canonical(payload).encode()),'legacy_preview_id':c['preview_id'],
            'encoder':e,'technical_status':'pass' if e['tokens_with_special']<=256 else 'quarantine',
            'downstream_blocker':'DATASET_ADAPTER_TABLE_RECORD_NOT_IMPLEMENTED'})
    priority=[]
    def add(base,c,scope,source_id,kind,technical,blockers,after=None):
        uid=c.get('unit_id',c.get('owner_unit_id'));unit=next(u for u in rows(base/'legal_units.pending.jsonl') if u['unit_id']==uid)
        ownspans=[s for s in rows(base/'source_spans.pending.jsonl') if s['unit_id']==uid]
        refs=re.findall(r'(?:Điều\s+\d+|khoản\s+\d+|điểm\s+[a-zđ]|[Pp]hụ lục\s+[IVXLCDM]+)',unit['text_original'])
        priority.append({'source_id':source_id,'law_id':unit['law_id'],'unit_id':uid,'new_unit_id':after,'candidate_id':c.get('chunk_id',c.get('preview_id')),
            'citation_path':unit['citation_path'],'artifact_ref':str(base.relative_to(BASE_DIR)).replace('\\','/'),
            'source_spans':ownspans,'scope_proposal':scope['scope_proposal'],'scope_reason':scope.get('reason',scope.get('scope_reason')),
            'text_original':unit['text_original'],'title':unit['title'],'context':c.get('context_text',c.get('contexts')),
            'dependency_refs_observed':refs,'dependency_review':'targeted_review_in_report_not_automatically_resolved',
            'provenance':'pending','edition':'pending','applicability':'pending_review','origin':'agent_review',
            'human_reviewer_events':0,'kind':kind,'technical_status':technical,'blockers':blockers,'release_eligible':False})
    tb=table/'base';scope={p['unit_id']:p for p in rows(tb/'scope.proposals.jsonl')}
    for c in rows(tb/'chunks.preview.jsonl'):
        if scope[c['unit_id']]['scope_proposal']=='included':add(tb,c,scope[c['unit_id']],'SRC-005','text','pass',[])
    for c,r in zip(rows(table/'candidates.jsonl'),records):add(tb,c,c,'SRC-005','table' if not c['explicit_dependency_unit_id'] else 'reference',r['technical_status'],[r['downstream_blocker']]+(['TOKEN_BUDGET_EXCEEDED'] if r['technical_status']=='quarantine' else []))
    scope={p['unit_id']:p for p in rows(base/'scope.proposals.jsonl')};newchunks={c['unit_id']:c for c in built['chunks']}
    for c in rows(base/'chunks.preview.jsonl'):
        if scope[c['unit_id']]['scope_proposal']=='included':
            n=newchunks.get(mapping[c['unit_id']]);add(base,c,scope[c['unit_id']],'SRC-007','text','pass' if n else 'blocked',[] if n else ['REBUILD_BLOCKED'],mapping[c['unit_id']])
    p51=Path(load(root/'binding.json')['tt51']['ref']).parent
    if not p51.is_absolute():p51=BASE_DIR/p51
    for c in rows(p51/'chunks.preview.jsonl'):add(p51,c,{'scope_proposal':'supporting','reason':'Main circular only; concrete QCVN target dependency not yet available'},'SRC-006','supporting','conditional',['NO_SELECTED_QCVN_TARGET_DEPENDENCY'])
    oldchunks={c['unit_id']:c for c in rows(base/'chunks.preview.jsonl')}
    cc=[{'old_chunk_id':oldchunks[k]['chunk_id'],'new_chunk_id':newchunks[v]['chunk_id'],'old_unit_id':k,'new_unit_id':v,
        'reason':'unit_id_and_citation_and_context_unit_ids_changed_by_real_ancestry'} for k,v in mapping.items() if k in oldchunks and v in newchunks]
    dependencies=[]
    for old in rows(base/'legal_units.pending.jsonl'):
        if any(re.search(r'/article:'+a+r'(?:/|$)',old['canonical_path']) for a in ['14','15','28','29','32','36','44','45','66','67']):
            dependencies.append({'kind':'targeted_article_or_dependency','unit':old,'spans':[s for s in rows(base/'source_spans.pending.jsonl') if s['unit_id']==old['unit_id']],
                'origin':'agent_review','review_status':'pending','note':'Source retained/read for priority only; not accepted scope/applicability'})
    for rec in rows(base/'extraction_snapshot/extractions.pending.jsonl'):
        e=rec['extraction'];t=(base/'extraction_snapshot'/e['text_ref']).read_text(encoding='utf8');trace=load(base/'extraction_snapshot'/rec['trace_ref'])
        for n in trace['nodes']:
            if n['kind']!='page':continue
            v=t[n['char_start']:n['char_end']]
            if re.match(r'^Phụ lục (XI|XII|XXIII|XXVI)\s*\n',v):
                dependencies.append({'kind':'referenced_annex_page','extraction_id':e['extraction_id'],'text':v,
                    'char_start':n['char_start'],'char_end':n['char_end'],'locator':n['locator'],'quote_sha256':digest(v.encode()),
                    'origin':'agent_review','scope_proposal':'supporting','review_status':'pending','note':'Form dependency only; no form target generated'})
    tt38_chunks=[c for c in rows(tb/'chunks.preview.jsonl') if next(p for p in rows(tb/'scope.proposals.jsonl') if p['unit_id']==c['unit_id'])['scope_proposal']=='included']
    tt38_contexts=[c for c in rows(tb/'contexts.preview.jsonl') if c['chunk_id'] in {x['chunk_id'] for x in tt38_chunks}]
    return {'legal_units.pending':units,'source_spans.pending':spans,'unit_crosswalk':cross,'chunk_crosswalk':cc,
        'tt38_text.chunks.preview':tt38_chunks,'tt38_text.contexts.preview':tt38_contexts,
        'chunks.preview':built['chunks'],'contexts.preview':built['contexts'],'encoder_inputs':built['encoder_inputs'],
        'quarantine':built['quarantined'],'issues':built['issues'],'table_records.preview':records,'priority':priority,
        'tt35_backlog':rows(base/'chunk_issues.jsonl'),'tt35_original_quarantine':rows(base/'chunks.quarantine.jsonl'),'targeted_dependencies':dependencies}


def validate(path):
    root=Path(path).resolve().parent;m=check_files(root/'manifest.json')
    if m['manifest_type']!=VERSION or m['snapshot_date']!='2025-01-01' or m.get('corpus_version') is not None or m['files']!=inventory(root) or m['release_eligible'] is not False or m['origin']!='agent_review' or m['human_reviewer_events']!=0:raise ValueError('Priority manifest status mismatch')
    if m['code_sha256']!=digest(Path(__file__).read_bytes()) or m['schema_sha256']!=digest(SCHEMA.read_bytes()):raise ValueError('Priority implementation binding mismatch')
    if load(root/'schema.json')!=load(SCHEMA):raise ValueError('Projection schema mismatch')
    binding=load(root/'binding.json')
    for value in binding.values():
        p=BASE_DIR/value['ref']
        if digest(p.read_bytes())!=value['sha256']:raise ValueError('Input binding changed')
        check_files(p)
    circular_preview.validate(root/'tt35/manifest.json')
    table_preview.validate(BASE_DIR/binding['tables']['ref'])
    circular_preview.validate(BASE_DIR/binding['tt51']['ref'])
    expected=calculate(root)
    for key,value in expected.items():
        if rows(root/(key+'.jsonl'))!=value:raise ValueError('Priority replay mismatch: '+key)
    return {'technical_valid':True,'units':len(expected['legal_units.pending']),'tt35_chunks':len(expected['chunks.preview']),
        'table_pass':sum(r['technical_status']=='pass' for r in expected['table_records.preview']),
        'table_quarantine':sum(r['technical_status']=='quarantine' for r in expected['table_records.preview']),
        'priority_rows':len(expected['priority']),'release_eligible':False}


def build(config,run_dir):
    cfg=load(config);binding={}
    for key,ref in cfg.items():
        p=BASE_DIR/ref;check_files(p);binding[key]={'ref':ref,'sha256':digest(p.read_bytes())}
    circular_preview.validate(BASE_DIR/cfg['tt35']);table_preview.validate(BASE_DIR/cfg['tables']);circular_preview.validate(BASE_DIR/cfg['tt51'])
    root=staging_path(run_dir);root.mkdir(parents=True);shutil.copytree((BASE_DIR/cfg['tt35']).parent,root/'tt35')
    write_json(root/'binding.json',binding);write_json(root/'schema.json',load(SCHEMA))
    result=calculate(root)
    for key,value in result.items():write_rows(root/(key+'.jsonl'),value)
    lines=['# Priority candidate review — pending, origin=agent_review','| Citation | Kind | Technical | Scope proposal | Blockers |','|---|---|---|---|---|']
    for p in result['priority']:lines.append(f"| {p['citation_path']} | {p['kind']} | {p['technical_status']} | {p['scope_proposal']} | {', '.join(p['blockers'])} |")
    for p in result['priority']:lines.extend(['## '+p['citation_path'],p['text_original'],'Context: '+canonical(p['context']),'Source spans: '+canonical(p['source_spans'])])
    (root/'review.md').write_text('\n\n'.join(lines),encoding='utf8')
    seal(root,{'manifest_type':VERSION,'built_at':now(),'origin':'agent_review','human_reviewer_events':0,'release_eligible':False,
        'snapshot_date':'2025-01-01','code_sha256':digest(Path(__file__).read_bytes()),'schema_sha256':digest(SCHEMA.read_bytes())})
    report=validate(root/'manifest.json');write_json(root/'run_report.json',report);return report
