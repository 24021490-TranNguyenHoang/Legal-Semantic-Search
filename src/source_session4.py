"""Bounded record rebuilding and packaging-plan verification; never builds a dataset."""
import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import re
import shutil

from src import chunk_preview_v2, chunk_preview
from src.assessment_evidence import check_files, now, seal
from src.config import BASE_DIR
from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import canonical, digest
from src.pipeline_cli import staging_path
from src.ingestion import encoder_views
from src.ingestion.full_preview import EncoderCache, circular_data
from src.ingestion.completion_records import form_identity
from src.ingestion.table_owner_adapter import TableOwnerConsumer
from src import preview_read_check as reader

VERSION='source-session4-record-preparation.v1'
BLOCKERS=['PREVIEW_ONLY','SOURCE_EDITION_APPLICABILITY_PENDING','AGENT_REVIEW_ONLY','NO_CORPUS_OR_QRELS_PROMOTION']
CAPS={'chunk.v1','source-retrieval.v1','form-retrieval.v1','table-owner-retrieval.v1','table-retrieval.v1','required-read.v1','form-layout-read.v1','whole-record-read.v1','encoder-views.v1'}


def hashed(o):return digest(canonical(o).encode())


def check_plan(plan):
    targets=[p for p in plan if p['role']=='target'];ids=set();positions=set()
    for p in targets:
        if p['record_id']in ids:raise ValueError('Duplicate target ID')
        ids.add(p['record_id'])
        if p.get('independent_encoder_view')or p['record_type']not in CAPS:raise ValueError('View/unsupported target type')
        if p.get('source_conflict'):raise ValueError('QCVN conflicting region cannot be target')
        if p['record_type']!='table-retrieval.v1':
            key=p['law_id'],p['canonical_path']
            if key in positions:raise ValueError('Duplicate DOCX/HTML legal position')
            positions.add(key)


def bounded_closure(uid,extra,source_deps):
    by=defaultdict(list)
    for d in source_deps:by[d['from_unit_id']].append(d)
    used=set(extra);queue=[uid,*extra];seen=set();deps=[]
    while queue:
        cur=queue.pop()
        if cur in seen:continue
        seen.add(cur)
        for d in by[cur]:
            deps.append(d)
            for other in d['unit_ids']:
                if other not in used:used.add(other);queue.append(other)
    return sorted(used-{uid}),list({d['dependency_id']:d for d in deps}.values())


def nd_extra(uid,cfg,pool):
    path=pool[uid]['canonical_path'];article=re.search(r'/article:(\d+)',path).group(1);extra=[]
    def find(law,suffix):return next(p for p in pool.values()if p['law_id']==law and p['canonical_path'].endswith('/'+suffix))
    def sub(p):return [x['unit_id']for x in pool.values()if x['law_id']==p['law_id']and(x['canonical_path']==p['canonical_path']or x['canonical_path'].startswith(p['canonical_path']+'/'))]
    if article in ['6','7']:
        for k in ([15,16]if article=='6'else [12,13]):extra+=sub(find('168/2024/NĐ-CP',f'article:{article}/clause:{k}'))
    if path.endswith('/clause:1/point:a')and article in cfg['nd_exception_clauses']:
        for clause,points in cfg['nd_exception_clauses'][article].items():
            if points is None:extra+=sub(find('168/2024/NĐ-CP',f'article:{article}/clause:{clause}'))
            else:extra += [find('168/2024/NĐ-CP',f'article:{article}/clause:{clause}/point:{pt}')['unit_id']for pt in points]
    for key,values in {'6/clause:1/point:c':['article:6/clause:7/point:c'],'7/clause:1/point:đ':['article:7/clause:6/point:c','article:7/clause:6/point:d'],'10/clause:1/point:b':['article:10/clause:2/point:a']}.items():
        if path.endswith('/article:'+key):extra += [find('168/2024/NĐ-CP',s)['unit_id']for s in values]
    if path.endswith('/article:6/clause:1/point:đ')or path.endswith('/article:7/clause:1/point:i'):extra+=sub(find('36/2024/QH15','article:27'))
    return extra


def add_nd_parents(ids,nd):
    by={u['unit_id']:u for u in nd['units']};out=set(ids)
    for uid in ids:
        node=by.get(uid)
        while node and node['parent_unit_id']:
            node=by[node['parent_unit_id']]
            if node['unit_type']in ['article','clause']:out.add(node['unit_id'])
    return sorted(out)


def preflight(config):
    cfg=load(config)
    if cfg['snapshot']!='2025-01-01':raise ValueError('Wrong snapshot')
    for ref,h in cfg['input_hashes'].items():
        if digest(Path(ref).read_bytes())!=h:raise ValueError('Pinned input changed: '+ref)
    root=Path(cfg['proposal_run']);check_files(root/'manifest.json')
    return cfg,root,load(cfg['source_config'])


def docx_data(graph,law):
    graph=Path(graph);snapshot=graph/'extraction_snapshot';source=snapshot/'source_snapshot'
    units=[u for u in rows(graph/'legal_units.pending.jsonl')if u['law_id']==law];ids={u['unit_id']for u in units}
    doc=next(d for d in rows(source/'documents.pending.jsonl')if d['law_id']==law)
    fs=[]
    for f in rows(source/'files.pending.jsonl'):
        if f['law_id']==law:fs.append({**f['measured'],**{k:f[k]for k in ['law_id','file_id','part_order','source_set_id']}})
    extractions=[];issues=[]
    for rec in rows(snapshot/'extractions.pending.jsonl'):
        if rec['law_id']==law:extractions.append({**rec['extraction'],'text_ref':(snapshot/rec['extraction']['text_ref']).as_posix()})
    issues.extend(rows(graph/'quality_issues.jsonl'))
    issues.extend({**q,'code':q['reason']}for q in rows(graph/'coverage.jsonl')if q['category']in ['needs_review','unparsed'])
    traces={r['extraction']['extraction_id']:load(snapshot/r['trace_ref']) for r in rows(snapshot/'extractions.pending.jsonl')if r['law_id']==law}
    for q in rows(snapshot/'quality_issues.jsonl'):
        if q['extraction_id'] not in traces:continue
        selected=[n for n in traces[q['extraction_id']]['nodes']if n['locator']==q['locator']]
        issues.append({**q,'law_id':law,**({'char_start':selected[0]['char_start'],'char_end':selected[0]['char_end']}if len(selected)==1 else {})})
    return {'document':{'law_id':law,'source_id':doc['source_id'],'law_title':doc['declared']['law_title'],'source_url':doc['declared']['source_url_candidate']},
            'units':units,'spans':[s for s in rows(graph/'source_spans.pending.jsonl')if s['unit_id']in ids],
            'files':fs,'extractions':extractions,'issues':issues}


class Catalog:
    def __init__(self,selections):
        self.entries={};self.selections=selections
        roots={s['graph_extraction_run']for s in selections}|{'staging/tt35-full-layout-001','staging/tt38-full-layout-001'}
        allowed={f['sha256']for s in selections for f in s['files']}
        for ref in sorted(roots):
            root=Path(ref);check_files(root/'manifest.json')
            for r in rows(root/'extractions.pending.jsonl'):
                if r['source_raw_sha256']not in allowed:continue
                e=r['extraction'];raw=next(f['local_ref']for s in selections for f in s['files']if f['sha256']==r['source_raw_sha256'])
                identity=(root/r['trace_ref']).with_name('identity.json')
                payload=load(identity)if identity.exists()else {'identity_schema':'extraction.v1','file_id':e['file_id'],'source_raw_sha256':r['source_raw_sha256'],
                         'method':e['method'],'tool_version':e['tool_version'],'config_sha256':r['config_sha256'],
                         'text_sha256':e['text_sha256'],'trace_content_sha256':r['trace_content_sha256']}
                self.entries[e['extraction_id']]={'raw_ref':raw,'raw_sha256':r['source_raw_sha256'],'text_ref':(root/e['text_ref']).as_posix(),
                    'text_sha256':e['text_sha256'],'trace_ref':(root/r['trace_ref']).as_posix(),
                    'identity_ref':identity.as_posix()if identity.exists()else None,'identity_payload':payload,'file_id':e['file_id']}
    def proof(self,p,use):
        e=self.entries[p['extraction_id']];text=Path(e['text_ref']).read_text(encoding='utf-8');a,b=p['char_start'],p['char_end']
        if p.get('file_id',e['file_id'])!=e['file_id']:raise ValueError('Wrong native proof file')
        if p.get('raw_sha256',e['raw_sha256'])!=e['raw_sha256'] or p.get('text_sha256',e['text_sha256'])!=e['text_sha256']:raise ValueError('Stale proof binding')
        quote=text[a:b]
        if digest(quote.encode())!=p['quote_sha256']:raise ValueError('Stale proof offsets')
        loc=p.get('locator',json.loads(p['locator_json'])if 'locator_json'in p else None)
        return {**e,'extraction_id':p['extraction_id'],'char_start':a,'char_end':b,'locator':loc,
                'quote':quote,'quote_sha256':p['quote_sha256'],'use':use,'offset_space':'normalized_extraction_unicode_codepoints',
                **({'bbox_pdf_top_origin':p['bbox_pdf_top_origin']}if p.get('bbox_pdf_top_origin')else {})}


def make_form(cfg,catalog):
    spec=cfg['form'];physical=Path('staging/tt35-source-regions-001');source=Path('staging/tt35-full-layout-001')
    for ev in spec['image_proofs']:
        if digest(Path(ev['ref']).read_bytes())!=ev['sha256']:raise ValueError('Form visual evidence binding')
    if digest(Path(spec['source_raw_ref']).read_bytes())!=spec['source_raw_sha256']:raise ValueError('Form source mismatch')
    a=next(a for a in rows(physical/'annexes.jsonl')if a['literal_marker']=='XXIII')
    if a['file_id']!=spec['file_id'] or a['page_start']!=127 or a['page_end']!=127:raise ValueError('Wrong AnnexXXIII locator')
    by={r['region_id']:r for r in rows(physical/'regions.jsonl')};lines=[by[i]for i in a['line_region_ids']]
    lines.sort(key=lambda r:r['source_proof']['char_start'])
    if not lines[0]['content'].startswith('Phụ lục XXIII') or not any('MẪU GIẤY XÁC NHẬN HOÀN THÀNH' in r['content']for r in lines):raise ValueError('Wrong form title')
    if a['table_ids']:raise ValueError('Unmapped physical table in form; do not flatten')
    rec=next(r for r in rows(source/'extractions.pending.jsonl')if r['extraction']['file_id']==a['file_id']);e=rec['extraction']
    page=next(n for n in load(source/rec['trace_ref'])['nodes']if n['kind']=='page'and n['locator']['page_start']==127)
    text=(source/e['text_ref']).read_text(encoding='utf-8')[page['char_start']:page['char_end']]
    fields=[{'source_region_id':r['region_id'],'text_original':r['content'],'source_proof':r['source_proof'],
             'role':'fillable_line'if re.search(r'\.{3,}|…',r['content'])else 'source_label_or_instruction'}for r in lines]
    form={'record_type':'form-retrieval.v1','law_id':'35/2024/TT-BGTVT','citation_path':'35/2024/TT-BGTVT > Phụ lục XXIII',
          'source_annex':a,'text_original':text,'form_fields':fields,'source_raw_sha256':spec['source_raw_sha256'],
          'file_id':a['file_id'],'extraction_id':e['extraction_id'],'char_start':page['char_start'],'char_end':page['char_end'],
          'text_sha256':digest(text.encode()),'raw_ref':spec['source_raw_ref'],'text_ref':(source/e['text_ref']).as_posix(),
          'scope_proposal':'supporting','required_capabilities':['form-layout-read.v1'],'applicability':'pending_review',
          'release_eligible':False,'origin':'agent_review','visual_evidence':spec['image_proofs'],
          'limits':'Whole one-page template and adjacent boundaries compared; no filled values or legal verification.'}
    form['identity']=form_identity(form);form['record_id']='fr_'+hashed(form['identity'])
    proofs=[catalog.proof({'extraction_id':e['extraction_id'],'char_start':page['char_start'],'char_end':page['char_end'],
                           'locator':page['locator'],'quote_sha256':digest(text.encode())},'form_page')]
    proofs += [catalog.proof(f['source_proof'],'form_field:'+str(i))for i,f in enumerate(fields)]
    return form,proofs


def physical_proofs(value,catalog):
    out=[]
    def walk(v):
        if isinstance(v,dict):
            if all(k in v for k in ['extraction_id','char_start','char_end','quote_sha256'])and('locator'in v or 'locator_json'in v):
                out.append(catalog.proof(v,'supporting_source'))
            else:
                for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(value)
    return out


def read_form(record,catalog):
    f=frame_for(record,'form-retrieval.v1',[],None,catalog,[])
    e=catalog.entries[record['extraction_id']];trace=load(e['trace_ref'])
    page=next(n for n in trace['nodes']if n['char_start']<=record['char_start']<record['char_end']<=n['char_end'])
    f['native_proofs']=[catalog.proof({'extraction_id':record['extraction_id'],'char_start':record['char_start'],'char_end':record['char_end'],
        'quote_sha256':digest(record['text_original'].encode()),'locator':page['locator']},'form_page')]
    f['native_proofs'] += [catalog.proof(x['source_proof'],'form_field:'+str(i))for i,x in enumerate(record['form_fields'])]
    return f


def frame_for(record,kind,contexts,encoding,catalog,deps):
    result={'record_id':record.get('chunk_id',record.get('retrieval_id',record.get('record_id'))),'record_type':kind,
            'record':record,'contexts':contexts,'encoding':encoding,'native_proofs':[], 'dependencies':deps,
            'expected_dependency_ids':sorted(d['dependency_id']for d in deps),
            'required_capabilities':[kind,'required-read.v1']+(['whole-record-read.v1','encoder-views.v1']if kind=='source-retrieval.v1'else []),
            'allowed_source_hashes':sorted({f['sha256']for s in catalog.selections for f in s['files']}),
            'human_review':None,'release_eligible':False,'origin':'agent_review','independent_encoder_view':False}
    def add(value,use):
        if isinstance(value,str):value=json.loads(value)
        for p in value:result['native_proofs'].append(catalog.proof(p,use))
    if kind=='chunk.v1':
        add(record['source_locator'],'target')
        for c in contexts:add(c['source_locator'],'context:'+str(c['context_order']))
    elif kind=='source-retrieval.v1':
        src=record['source_record']
        if 'source_locator'in src:add(src['source_locator'],'target')
        elif 'own_source_locator'in src:add(src['own_source_locator'],'target')
        else:add(src['source_proofs'],'target')
        if src.get('context_proofs'):add(src['context_proofs'],'context')
        for c in contexts:
            if 'source_locator'in c:add(c['source_locator'],'context:'+str(c['context_order']))
    # All other physical proof facets (cells/header/fields) remain bound as well.
    result['native_proofs']+=physical_proofs(record,catalog)
    return result


def build(config,output):
    cfg,prior,s3=preflight(config);root=staging_path(output);root.mkdir(parents=True)
    selections=rows(prior/'source_selection.jsonl');ps=rows(prior/'membership.proposals.jsonl');pool={p['unit_id']:p for p in ps}
    bypath={(p['law_id'],p['canonical_path']):p for p in ps};catalog=Catalog(selections)
    def find(law,suffix):
        found=[p for p in ps if p['law_id']==law and p['canonical_path'].endswith('/'+suffix)]
        if len(found)!=1:raise ValueError('Missing/ambiguous selected dependency '+suffix)
        return found[0]
    def subtree(p):return [x['unit_id']for x in ps if x['law_id']==p['law_id']and(x['canonical_path']==p['canonical_path']or x['canonical_path'].startswith(p['canonical_path']+'/'))]
    # Follow only the finite reviewed dependency graph, never parse every citation.
    source_deps=rows(prior/'dependencies.jsonl')
    def closure(uid,extra=()):
        return bounded_closure(uid,extra,source_deps)
    def unit_proofs(ids):
        return [catalog.proof(s,'dependency:'+uid+':'+s.get('field_name','text_original'))for uid in sorted(set(ids))for s in pool[uid]['source_spans']]
    encode=EncoderCache(cfg['encoder_base'],root/'encoder_cache.jsonl')
    nd=docx_data(cfg['nd_graph'],'168/2024/NĐ-CP');old=rows(prior/'v4.comparison.jsonl')
    seeds=[r for r in old if r['change']=='source_and_ID_change_pending_rebuild']
    if len({r['selected_unit_id']for r in seeds})!=len(seeds):raise ValueError('Ambiguous old-record/unit mapping')
    eligible=[r['selected_unit_id']for r in seeds if pool[r['selected_unit_id']]['scope']=='in_scope'and pool[r['selected_unit_id']]['role']=='target']
    bc={**load('config/stage6_points.v1.json')['chunk'],'target_unit_ids':eligible}
    built=chunk_preview_v2.build_chunks(nd,BASE_DIR,bc,BLOCKERS,encode)
    chunks={c['unit_id']:c for c in built['chunks']};enc={e['unit_id']:e for e in built['encoder_inputs']}
    ctx=defaultdict(list)
    for c in built['contexts']:ctx[c['chunk_id']].append(c)
    wrapped=[]
    for q in built['quarantined']:
        c=q['candidate'];views,bad=encoder_views.prepare([c],encode,256)
        if views:
            chunks[c['unit_id']]=views[0];wrapped.extend(views);ctx[views[0]['record_id']]=q['contexts']
    nd_frames=[];disposition=[]
    for seed in seeds:
        uid=seed['selected_unit_id'];p=pool[uid];record=chunks.get(uid);extra=[]
        path=p['canonical_path']
        if record:
            extra=nd_extra(uid,cfg,pool)
            ids,deps=closure(uid,extra)
            # Cited point needs its own article/clause lead, not unrelated siblings.
            ids=sorted(set(add_nd_parents(ids,nd))-{uid})
            direct={'dependency_id':'finite_'+hashed([uid,ids]),'unit_ids':ids,'required':True,'reason':'Bound source exceptions/modifiers/parent fields; no fine inference'}
            deps=[*deps,direct];kind='source-retrieval.v1'if record.get('record_type')=='source-retrieval.v1'else 'chunk.v1';rid=record.get('chunk_id',record.get('record_id'))
            contexts=copy.deepcopy(ctx[rid])
            for c in contexts:
                owner=next(u for u in nd['units']if u['unit_id']==c['unit_id']);c['text_original']=owner[c['field_name']][c['char_start']:c['char_end']]
            frame=frame_for(record,kind,contexts,enc[uid],catalog,deps);frame['native_proofs']+=unit_proofs(ids)
            frame['dependency_units']=[{k:pool[i][k]for k in ['unit_id','law_id','canonical_path','title','text_original']}for i in ids]
            check=reader.check(BASE_DIR,frame,CAPS);nd_frames.append(frame)
            disposition.append({'old_record_id':seed['old_record_id'],'unit_id':uid,'canonical_path':path,'scope':p['scope'],'role':p['role'],
                                'new_record_id':rid,'record_type':kind,'status':'ready','reason':'Fresh native proof/context and finite required-read validated',
                                'tokens':enc[uid]['tokens_with_special'],'unknown_tokens':enc[uid]['unknown_tokens'],'required_unit_ids':ids,
                                'assessment_qrels_or_offsets_transferred':False})
        else:
            disposition.append({'old_record_id':seed['old_record_id'],'unit_id':uid,'canonical_path':path,'scope':p['scope'],'role':p['role'],
                                'new_record_id':None,'record_type':None,'status':'blocked','reason':'SCOPE_UNRESOLVED_IN_RUN009'if uid not in eligible else 'BUILDER_OR_TOKEN_QUARANTINE',
                                'builder_issues':[q for q in built['issues']if q['unit_id']==uid],'assessment_qrels_or_offsets_transferred':False})
    write_rows(root/'nd168.disposition.jsonl',disposition);write_rows(root/'nd168.chunks.preview.jsonl',built['chunks']);write_rows(root/'nd168.contexts.preview.jsonl',built['contexts'])
    write_rows(root/'nd168.views.preview.jsonl',wrapped);write_rows(root/'nd168.quarantine.jsonl',built['quarantined']);write_rows(root/'nd168.encoder_inputs.jsonl',built['encoder_inputs'])
    write_rows(root/'nd168.dependency_checks.jsonl',built['dependency_checks']);write_rows(root/'nd168.reads.jsonl',nd_frames)
    form,proofs=make_form(cfg,catalog)
    form_frame=frame_for(form,'form-retrieval.v1',[],None,catalog,[]);form_frame['native_proofs']=proofs
    reader.check(BASE_DIR,form_frame,CAPS);write_json(root/'form_xxiii.preview.json',form);write_json(root/'form_xxiii.read.json',form_frame)
    # Build A28K2 technically, but do not hide mandatory practical-exam layout gaps.
    ttbase=Path('staging/tt35-preview-005');tunits=rows(Path('staging/circular-priority-006/legal_units.pending.jsonl'));tspans=rows(Path('staging/circular-priority-006/source_spans.pending.jsonl'))
    tt=circular_data(ttbase,tunits,tspans)
    for f in tt['files']:f['raw_file_ref']=(ttbase/f['raw_file_ref']).as_posix()
    for e in tt['extractions']:e['text_ref']=(ttbase/e['text_ref']).as_posix()
    a28=find('35/2024/TT-BGTVT','article:28/clause:2');a28build=chunk_preview_v2.build_chunks(tt,BASE_DIR,{**bc,'target_unit_ids':[a28['unit_id']]},BLOCKERS,encode)
    for name,values in a28build.items():write_rows(root/('a28.'+name+'.jsonl'),values)
    table_consumer=TableOwnerConsumer(s3['table_owner']);course=[r for r in table_consumer.records if any('/article:'+str(a)+'/'in r['owner_path']for a in [6,7,8])]
    reads=root/'a28_table_reads';reads.mkdir()
    for c in course:write_json(reads/(c['record_id']+'.json'),table_consumer.read(c['record_id']))
    completion=[]
    for a,k in [(6,4),(7,4),(7,5),(8,4),(8,5)]:completion+=subtree(find('35/2024/TT-BGTVT',f'article:{a}/clause:{k}'))
    annexes=rows(Path('staging/tt35-source-regions-001/annexes.jsonl'));missing=[a for a in annexes if a['literal_marker']in ['XV','XVI','XVII']]
    a28closure={'unit_id':a28['unit_id'],'status':'blocked','scope':'in_scope','form_record_id':form['record_id'],'form_technical_status':'ready',
                'table_record_ids':[c['record_id']for c in course],'completion_unit_ids':sorted(set(completion)),
                'completion_proofs':unit_proofs(completion),'completion_units':[{k:pool[i][k]for k in ['unit_id','canonical_path','title','text_original']}for i in sorted(set(completion))],
                'required_unchecked_annexes':missing,'annex_source_ref':cfg['form']['source_raw_ref'],'annex_source_sha256':cfg['form']['source_raw_sha256'],
                'reason':'A7K4d/A8K4d completion tests depend on Annex XV/XVI/XVII scoring/layout; native source exists but full required-read content/figures not checked in this bounded session.',
                'a7_annex':'II','outside_target':['A21K4c','A46K2'],'human_review':None,'release_eligible':False}
    write_json(root/'a28.closure.json',a28closure)
    # Cross-source probe stays dormant: A12K12 was not one of the 27 selected seeds.
    a12=find('168/2024/NĐ-CP','article:12/clause:12');ids,deps=closure(a12['unit_id'])
    cross={'from_unit_id':a12['unit_id'],'unit_ids':ids,'dependencies':deps,'source_proofs':unit_proofs(ids),
           'selected_target':False,'reason':'Verified source/ID closure only; A12K12 not silently added to the selected 27.'}
    for p in cross['source_proofs']:reader.proof(BASE_DIR,p)
    write_json(root/'nd168.cross_source_probe.json',cross)
    # Validate every inherited target and derive only reachable supporting closure.
    from src.composition_consumer import Consumer
    from src import seven_dataset_portable
    v3=Path(s3['v3']);v4=Path(s3['v4']);consumer=Consumer(v3);seven_dataset_portable.validate(v4)
    inv={d['record_id']:d for d in rows(prior/'record_inventory.jsonl')};payloads={};file_cache={}
    encbase={e['chunk_id']:e for e in rows(v3/'encoder_inputs.jsonl')}
    encbase.update({e['chunk_id']:e for e in rows(Path('staging/seven-source-complete-records-002/encoder_inputs.jsonl'))})
    contexts=rows(v3/'contexts.jsonl')+rows(Path('staging/seven-source-complete-records-002/contexts.preview.jsonl'))
    chosen=[p for p in ps if p['membership']=='proposed_include']+rows(prior/'table_row.membership.proposals.jsonl')
    # Archival v1 evidence is compact; re-run only preprocessing/tokenization,
    # compare its hash/IDs below, never invent encoder_text from compact evidence.
    compact={e['input_sha256']:e for e in rows(v3/'components/base/components/base/support/encoder_evidence.jsonl')}
    originals=[]
    for prop in chosen:
        desc=inv[prop['record_id']];ref=Path(desc['artifact_ref'])
        if not ref.is_file():ref=prior/ref
        if ref not in file_cache:file_cache[ref]=rows(ref)
        originals.append(next(r for r in file_cache[ref]if r.get('chunk_id',r.get('retrieval_id',r.get('record_id')))==prop['record_id']))
    fresh=encode([r['text_for_search']for r in originals]);write_rows(root/'base116.encoder_inputs.jsonl',fresh)
    checks=[];plan=[];selected_support=set();support_records=set();base_frames=[]
    for prop,measured in zip(chosen,fresh):
        rid=prop['record_id'];desc=inv[rid];ref=Path(desc['artifact_ref'])
        if not ref.is_file():ref=prior/ref
        if ref not in file_cache:file_cache[ref]=rows(ref)
        record=next(r for r in file_cache[ref]if r.get('chunk_id',r.get('retrieval_id',r.get('record_id')))==rid)
        ids,deps=closure(prop['unit_id']);status='ready';reason=None
        try:
            if hashed(record)!=desc['payload_sha256']:raise ValueError('Target payload changed')
            old_evidence=compact.get(measured['input_sha256'])
            if old_evidence and (old_evidence['token_ids_sha256']!=measured['after']['token_ids_sha256']or old_evidence['tokens_with_special']!=measured['tokens_with_special']):
                raise ValueError('Pinned encoder preprocessing evidence changed')
            ctxs=[]
            for c in [c for c in contexts if c['chunk_id']==rid]:
                owner=pool[c['unit_id']];ctxs.append({**c,'text_original':owner[c['field_name']][c['char_start']:c['char_end']]})
            frame=frame_for(record,prop['record_type'],ctxs,measured,catalog,deps)
            frame['native_proofs']+=unit_proofs(ids)
            frame['dependency_units']=[{k:pool[i][k]for k in ['unit_id','law_id','canonical_path','title','text_original']}for i in ids]
            if prop['record_type']=='source-retrieval.v1':
                src=record['source_record']
                if src.get('explicit_dependency_unit_id') and not src.get('source_cells'):raise ValueError('Rain point lacks mandatory table3')
            result=reader.check(BASE_DIR,frame,CAPS);base_frames.append(frame)
            selected_support.update(ids);support_records.update(d['record_id']for d in deps if d.get('record_id'))
        except (ValueError,KeyError,StopIteration,OSError)as exc:status='blocked';reason=str(exc);result=None
        checks.append({'record_id':rid,'record_type':prop['record_type'],'unit_id':prop['unit_id'],'status':status,'reason':reason,
                       'source_artifact':ref.as_posix(),'payload_sha256':hashed(record),'read_validation':result})
        if status=='ready':plan.append({'record_id':rid,'record_type':prop['record_type'],'unit_id':prop['unit_id'],'role':'target','status':'ready',
                                       'law_id':prop['law_id'],'canonical_path':prop['canonical_path'],
                                       'source_artifact':ref.as_posix(),'payload_sha256':hashed(record),'required_dependency_ids':sorted(d['dependency_id']for d in deps),
                                       'required_unit_ids':ids,'required_capabilities':frame['required_capabilities'],'scope':'in_scope',
                                       'source_status':'pending','edition_status':'pending','applicability':'pending_review','release_eligible':False})
    for f in nd_frames:
        rid=f['record_id'];selected_support.update(u['unit_id']for u in f['dependency_units'])
        plan.append({'record_id':rid,'record_type':f['record_type'],'unit_id':f['record'].get('unit_id',f['record'].get('source_record',{}).get('unit_id')),
                     'law_id':'168/2024/NĐ-CP','canonical_path':next(p['canonical_path']for p in disposition if p['new_record_id']==rid),
                     'role':'target','status':'ready','source_artifact':'nd168.reads.jsonl','artifact_base':'this_run',
                     'payload_sha256':hashed(f['record']),'required_unit_ids':[u['unit_id']for u in f['dependency_units']],
                     'required_dependency_ids':f['expected_dependency_ids'],'required_capabilities':f['required_capabilities'],
                     'scope':'in_scope','source_status':'pending','edition_status':'pending','applicability':'pending_review','release_eligible':False})
    for uid in sorted(selected_support):
        plan.append({'record_id':uid,'record_type':'source-unit-read.v1','unit_id':uid,'role':'supporting','status':'ready',
                     'source_artifact':(prior/'membership.proposals.jsonl').as_posix(),'payload_sha256':hashed(pool[uid]),
                     'proof_refs':pool[uid]['source_spans'],'required_capabilities':['required-read.v1'],'release_eligible':False})
    nonunits={n['record_id']:n for n in rows(prior/'nonunit.membership.proposals.jsonl')}
    supporting_reads=[]
    for rid in sorted(support_records):
        n=nonunits[rid];original=next(r for r in rows(n['artifact_ref'])if r.get('record_id')==rid)
        f=read_form(original,catalog);reader.check(BASE_DIR,f,CAPS);supporting_reads.append(f)
        plan.append({'record_id':rid,'record_type':n['record_type'],'role':'supporting','status':n['technical'],
                                    'source_artifact':n['artifact_ref'],'required_by_unit_ids':n.get('required_by_unit_ids',[]),
                                    'payload_sha256':hashed(original),'source_proofs':f['native_proofs'],
                                    'required_capabilities':['form-layout-read.v1']if n['record_type']=='form-retrieval.v1'else ['required-read.v1'],
                                    'release_eligible':False})
    write_rows(root/'supporting_records.reads.jsonl',supporting_reads)
    targets=[p for p in plan if p['role']=='target'];identities=[(p['record_id'],p['record_type'])for p in targets]
    check_plan(plan)
    write_rows(root/'base116.verification.jsonl',checks);write_rows(root/'base116.reads.jsonl',base_frames);write_rows(root/'packaging_plan.jsonl',plan)
    write_rows(root/'packaging_plan.blocked.jsonl',[*([d for d in disposition if d['status']=='blocked']),a28closure,*[c for c in checks if c['status']=='blocked']])
    csv_disposition(root,disposition,plan)
    a7=next(r for r in table_consumer.records if '/article:7/'in r['owner_path'])
    dps=[{'dependency_id':'table_'+hashed(d),'unit_ids':[u['unit_id']for u in d['units']]if d['kind']=='unit_subtree'else [],'required':True}for d in a7['required_dependencies']]
    tf=frame_for(a7,'table-owner-retrieval.v1',[],None,catalog,dps)
    ids=sorted({uid for d in dps for uid in d['unit_ids']});tf['dependency_units']=[{k:pool[i][k]for k in ['unit_id','law_id','canonical_path','title','text_original']}for i in ids]
    tf['native_proofs']+=unit_proofs(ids);tf['loaded_required_dependencies']=table_consumer.read(a7['record_id'])['loaded_required_dependencies']
    tf['native_proofs']+=physical_proofs(tf['loaded_required_dependencies'],catalog)
    samples=[next(f for f in base_frames if f['record_type']==kind)for kind in ['table-retrieval.v1','source-retrieval.v1']if any(f['record_type']==kind for f in base_frames)]
    create_probes(root,[*nd_frames[:1],form_frame,tf,*samples],catalog)
    summary={'state':'PREVIEW_AND_PLAN_ONLY','old_nd_records':len(seeds),'unique_nd_units':len({r['selected_unit_id']for r in seeds}),
             'nd_ready':len(nd_frames),'nd_blocked':len(seeds)-len(nd_frames),'nd_types':dict(Counter(f['record_type']for f in nd_frames)),
             'form_xxiii_fields':len(form['form_fields']),'form_xxiii_status':'ready','a28_status':'blocked','base_checked':len(checks),
             'base_ready':sum(c['status']=='ready'for c in checks),'base_blocked':sum(c['status']=='blocked'for c in checks),
             'planned_targets':len(targets),'planned_supporting_units':len(selected_support),'planned_supporting_records':len(support_records),
             'human_reviewer_events':0,'release_eligible':False,'snapshot':'2025-01-01'}
    write_json(root/'validation_report.json',summary)
    seal(root,{'manifest_type':VERSION,'built_at':now(),'config_ref':Path(config).as_posix(),'config_sha256':digest(Path(config).read_bytes()),
               'module_sha256':digest(Path(__file__).read_bytes()),'reader_sha256':digest(Path(reader.__file__).read_bytes()),'release_eligible':False})
    return summary


def csv_disposition(root,dispositions,plan):
    from src.membership_proposal import csv_export
    csv_export(root/'nd168.disposition.csv',dispositions,['old_record_id','unit_id','canonical_path','scope','role','new_record_id','record_type','status','reason'])
    csv_export(root/'packaging_plan.csv',plan,['record_id','record_type','unit_id','role','status','source_artifact','required_capabilities'])
    lines=['# NĐ168 — preview pending, không phải corpus']
    for f in rows(root/'nd168.reads.jsonl'):
        r=f['record'].get('source_record',f['record']);lines += ['## '+r['citation_path'],r['text_original'],'Context: '+str(r.get('context_text')),
            'ID: '+f['record_id'],'Required unit count: '+str(len(f.get('dependency_units',[])))]
    (root/'nd168_preview.md').write_text('\n\n'.join(lines),encoding='utf-8')


def create_probes(root,frames,catalog):
    probe=root/'portable_probe';probe.mkdir();(probe/'objects').mkdir();reads={};copied={}
    for f in frames:
        c=copy.deepcopy(f)
        for p in c['native_proofs']:
            for key in ['raw_ref','text_ref','trace_ref','identity_ref']:
                ref=p[key]
                if ref is None:continue
                if ref not in copied:
                    path=Path(ref);h=digest(path.read_bytes());target='objects/'+h+path.suffix.lower()
                    if not(probe/target).exists():shutil.copyfile(path,probe/target)
                    copied[ref]=target
                p[key]=copied[ref]
        ref=c['record_id']+'.json';write_json(probe/ref,c);reads[c['record_id']]=ref
    shutil.copyfile(Path(reader.__file__),probe/'reader.py')
    files=[{'ref':p.relative_to(probe).as_posix(),'sha256':digest(p.read_bytes())}for p in sorted(probe.rglob('*'))if p.is_file()]
    write_json(probe/'probe_manifest.json',{'inspection_only':True,'not_a_dataset':True,'reads':reads,'files':files,'capabilities':sorted(CAPS)})


def validate(config,run,replay_run=None):
    """Rebind reads to pinned sources/proposals, not only self-reported checksums."""
    from src.membership_proposal import csv_validate
    cfg,prior,s3=preflight(config);root=Path(run);m=check_files(root/'manifest.json')
    if (m['manifest_type']!=VERSION or m['config_sha256']!=digest(Path(config).read_bytes())
            or m['module_sha256']!=digest(Path(__file__).read_bytes())or m['reader_sha256']!=digest(Path(reader.__file__).read_bytes())):
        raise ValueError('Wrong config/code binding')
    selections=rows(prior/'source_selection.jsonl');catalog=Catalog(selections)
    pool={p['unit_id']:p for p in rows(prior/'membership.proposals.jsonl')};source_deps=rows(prior/'dependencies.jsonl')
    def ups(ids):return [catalog.proof(s,'dependency:'+uid+':'+s.get('field_name','text_original'))for uid in sorted(set(ids))for s in pool[uid]['source_spans']]
    def units(ids):return [{k:pool[i][k]for k in ['unit_id','law_id','canonical_path','title','text_original']}for i in ids]
    nd=docx_data(cfg['nd_graph'],'168/2024/NĐ-CP');seeds=[r for r in rows(prior/'v4.comparison.jsonl')if r['change']=='source_and_ID_change_pending_rebuild']
    ds=rows(root/'nd168.disposition.jsonl');frames=rows(root/'nd168.reads.jsonl');by={f['record']['unit_id']:f for f in frames}
    if len(by)!=len(frames)or[(d['old_record_id'],d['unit_id'])for d in ds]!=[(s['old_record_id'],s['selected_unit_id'])for s in seeds]:
        raise ValueError('Wrong old-record/new-unit lineage')
    eligible=[s['selected_unit_id']for s in seeds if pool[s['selected_unit_id']]['scope']=='in_scope'and pool[s['selected_unit_id']]['role']=='target']
    memo={e['input_sha256']:e for e in rows(root/'encoder_cache.jsonl')}
    def cached(texts):return [memo[digest(t.encode())]for t in texts]
    bc={**load('config/stage6_points.v1.json')['chunk'],'target_unit_ids':eligible}
    rebuilt=chunk_preview_v2.build_chunks(nd,BASE_DIR,bc,BLOCKERS,cached)
    for name,key in [('chunks','chunks'),('contexts','contexts'),('quarantine','quarantined'),('encoder_inputs','encoder_inputs'),('dependency_checks','dependency_checks')]:
        if rows(root/('nd168.'+name+('.preview.jsonl'if name in ['chunks','contexts']else '.jsonl')))!=rebuilt[key]:raise ValueError('Fresh builder replay differs: '+name)
    records={c['unit_id']:c for c in rebuilt['chunks']};wrapped=[];ctx=defaultdict(list)
    observed={e['unit_id']:e for e in rebuilt['encoder_inputs']}
    for c in rebuilt['contexts']:ctx[c['chunk_id']].append(c)
    for q in rebuilt['quarantined']:
        views,_=encoder_views.prepare([q['candidate']],cached,256)
        if views:
            r=views[0];records[q['candidate']['unit_id']]=r;wrapped.append(r);ctx[r['record_id']]=q['contexts']
    if rows(root/'nd168.views.preview.jsonl')!=wrapped:raise ValueError('Changed whole-record view')
    for d in ds:
        uid=d['unit_id'];p=pool[uid]
        if (d['scope'],d['role'],d['canonical_path'])!=(p['scope'],p['role'],p['canonical_path']):raise ValueError('Scope/position copied from old branch')
        if uid not in records:
            if d['status']!='blocked'or d['new_record_id']is not None or uid in by:raise ValueError('Blocked record admitted')
            continue
        r=records[uid];rid=r.get('chunk_id',r.get('record_id'));ids,deps=bounded_closure(uid,nd_extra(uid,cfg,pool),source_deps)
        ids=sorted(set(add_nd_parents(ids,nd))-{uid});deps+=[{'dependency_id':'finite_'+hashed([uid,ids]),'unit_ids':ids,'required':True,'reason':'Bound source exceptions/modifiers/parent fields; no fine inference'}]
        cs=copy.deepcopy(ctx[rid]);ndby={u['unit_id']:u for u in nd['units']}
        for c in cs:c['text_original']=ndby[c['unit_id']][c['field_name']][c['char_start']:c['char_end']]
        f=frame_for(r,r.get('record_type','chunk.v1'),cs,observed[uid],catalog,deps)
        f['native_proofs']+=ups(ids);f['dependency_units']=units(ids)
        if by.get(uid)!=f or d['status']!='ready'or d['new_record_id']!=rid or d['required_unit_ids']!=ids:raise ValueError('ND source/context/dependency or old ID mismatch')
        reader.check(BASE_DIR,f,CAPS)
    if set(by)!=set(records):raise ValueError('Unexpected ND target')
    form,proofs=make_form(cfg,catalog);ff=frame_for(form,'form-retrieval.v1',[],None,catalog,[]);ff['native_proofs']=proofs
    if load(root/'form_xxiii.preview.json')!=form or load(root/'form_xxiii.read.json')!=ff:raise ValueError('Form source/field mismatch')
    reader.check(BASE_DIR,ff,CAPS)
    inv={p['record_id']:p for p in rows(prior/'record_inventory.jsonl')}
    props=[p for p in pool.values()if p['membership']=='proposed_include']+rows(prior/'table_row.membership.proposals.jsonl')
    bases=rows(root/'base116.reads.jsonl');baseby={f['record_id']:f for f in bases};checks=rows(root/'base116.verification.jsonl')
    if len({c['record_id']for c in checks})!=len(props)or{c['record_id']for c in checks}!={p['record_id']for p in props}:raise ValueError('Incomplete base inventory check')
    for p in props:
        check=next(c for c in checks if c['record_id']==p['record_id'])
        if check['status']!='ready':continue
        f=baseby[p['record_id']];ids,deps=bounded_closure(p['unit_id'],[],source_deps)
        if f['record_type']!=p['record_type']or hashed(f['record'])!=inv[p['record_id']]['payload_sha256']:raise ValueError('Changed base payload/type')
        expected=frame_for(f['record'],p['record_type'],f['contexts'],f['encoding'],catalog,deps)
        expected['native_proofs']+=ups(ids);expected['dependency_units']=units(ids)
        if f!=expected:raise ValueError('Incomplete base required read/proof')
        reader.check(BASE_DIR,f,CAPS)
    plan=rows(root/'packaging_plan.jsonl');check_plan(plan);targets=[p for p in plan if p['role']=='target']
    allframes={f['record_id']:f for f in [*bases,*frames]}
    if {p['record_id']for p in targets}!=set(allframes):raise ValueError('Target selection mismatch')
    wanted_units=set();wanted_records=set()
    for p in targets:
        f=allframes[p['record_id']];u=pool[p['unit_id']];wanted_units.update(x['unit_id']for x in f['dependency_units'])
        wanted_records.update(d['record_id']for d in f['dependencies']if d.get('record_id'))
        if (p['required_unit_ids']!=[x['unit_id']for x in f['dependency_units']]or p['payload_sha256']!=hashed(f['record'])
                or p['required_dependency_ids']!=f['expected_dependency_ids']or p['record_type']!=f['record_type']
                or p['required_capabilities']!=f['required_capabilities']or (p['law_id'],p['canonical_path'])!=(u['law_id'],u['canonical_path'])
                or p['release_eligible']is not False):raise ValueError('Packaging plan/source/dependency mismatch')
    support=[p for p in plan if p['role']=='supporting'];sunit=[p for p in support if p['record_type']=='source-unit-read.v1']
    if {p['unit_id']for p in sunit}!=wanted_units or len(sunit)!=len(wanted_units):raise ValueError('Unrelated/omitted supporting unit')
    for p in sunit:
        if p['payload_sha256']!=hashed(pool[p['unit_id']])or p['proof_refs']!=pool[p['unit_id']]['source_spans']:raise ValueError('Supporting proof mismatch')
    sr=[p for p in support if p['record_type']!='source-unit-read.v1']
    if {p['record_id']for p in sr}!=wanted_records:raise ValueError('Unrelated/omitted supporting record')
    support_frames=rows(root/'supporting_records.reads.jsonl')
    if {f['record_id']for f in support_frames}!=wanted_records:raise ValueError('Supporting form not read')
    for p in sr:
        expected=next(r for r in rows(p['source_artifact'])if r.get('record_id')==p['record_id'])
        f=read_form(expected,catalog)
        if next(x for x in support_frames if x['record_id']==p['record_id'])!=f or p['payload_sha256']!=hashed(expected)or p['source_proofs']!=f['native_proofs']:raise ValueError('Supporting form source/proof differs')
        reader.check(BASE_DIR,f,CAPS)
    table=TableOwnerConsumer(s3['table_owner'])
    for c in table.records:
        if any('/article:'+str(a)+'/'in c['owner_path']for a in [6,7,8]):
            if load(root/'a28_table_reads'/(c['record_id']+'.json'))!=table.read(c['record_id']):raise ValueError('Course consumer lost whole tables/dependency')
    a=load(root/'a28.closure.json');annexes=rows(Path('staging/tt35-source-regions-001/annexes.jsonl'))
    if a['status']!='blocked'or a['required_unchecked_annexes']!=[x for x in annexes if x['literal_marker']in ['XV','XVI','XVII']]or a['a7_annex']!='II':raise ValueError('A28 closure falsely completed')
    if a['completion_proofs']!=ups(a['completion_unit_ids']):raise ValueError('A28 condition proof changed')
    for p in a['completion_proofs']:reader.proof(BASE_DIR,p)
    csv_validate(root/'nd168.disposition.csv',ds);csv_validate(root/'packaging_plan.csv',plan)
    probe=root/'portable_probe';pm=load(probe/'probe_manifest.json')
    for rid,ref in pm['reads'].items():
        f=load(probe/ref)
        if f['record_id']!=rid:raise ValueError('Probe record binding')
        reader.check(probe,f,pm['capabilities'])
    replay=[]
    if replay_run:
        other=Path(replay_run);check_files(other/'manifest.json')
        for name in [p['path']for p in m['files']]:
            if (root/name).read_bytes()!=(other/name).read_bytes():raise ValueError('Replay payload differs: '+name)
            replay.append(name)
    return {'technical_valid':True,'nd_checked':len(ds),'native_reads_checked':len(allframes),'portable_types_checked':len(pm['reads']),
            'replay_files_equal':len(replay),'a28_status':'blocked','release_eligible':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','validate']);p.add_argument('--config',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--replay-run',type=Path)
    a=p.parse_args();print(build(a.config,a.run_dir)if a.action=='build'else validate(a.config,a.run_dir,a.replay_run))


if __name__=='__main__':main()
