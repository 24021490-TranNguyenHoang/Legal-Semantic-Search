"""Compose an immutable existing draft with selected circular components."""
from pathlib import Path
import shutil
from src import experimental_draft, circular_dataset_portable as portable
from src.ingestion import circular_priority
from src.experimental_dataset import load,rows,write_json,write_rows
from src.source_contracts import digest,canonical
from src.config import BASE_DIR
from src.pipeline_cli import staging_path
from src.assessment_evidence import now

DEFAULT_CONFIG=BASE_DIR/'config/circular_dataset.v1.json'

def build(config,run_dir):
    cfg=load(config)
    if cfg['policy_version']!=portable.VERSION or cfg['snapshot_date']!='2025-01-01':raise ValueError('Unknown composition/snapshot')
    inputs={}
    for key,b in cfg['inputs'].items():
        p=BASE_DIR/b['ref']
        if digest(p.read_bytes())!=b['sha256']:raise ValueError('Wrong input manifest hash')
        inputs[key]=p
    experimental_draft.validate(inputs['base']);circular_priority.validate(inputs['priority'])
    base=inputs['base'].parent;priority=inputs['priority'].parent
    binding=load(priority/'binding.json');tables=(BASE_DIR/binding['tables']['ref']).parent;tt38=tables/'base'
    root=staging_path(run_dir);root.mkdir(parents=True)
    experimental_draft.copy_component(base,root/'components/base','dataset_manifest.json','dataset_manifest.sha256')
    def cp(src,ref):
        target=portable.resolve(root,ref);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
    def exported(ref,value):
        (root/ref).parent.mkdir(parents=True,exist_ok=True);write_rows(root/ref,value)
    graphs={}
    laws=load(base/'components/base/support/laws.json')
    exported('graphs/base.units.jsonl',[u for law in laws.values() for u in law['units']])
    exported('graphs/base.spans.jsonl',[s for law in laws.values() for s in law['spans']])
    graphs['base-docx']={'units_ref':'graphs/base.units.jsonl','spans_ref':'graphs/base.spans.jsonl',
        'texts':{e['extraction_id']:'components/base/components/base/inputs/'+e['text_ref'] for law in laws.values() for e in law['extractions']},'schema':'DDD.v1.pending'}
    rec=load(base/'components/nd168-a16k2/extraction/metadata.json')
    graphs['nd168-html-a16k2']={'units_ref':'components/base/components/nd168-a16k2/legal_units.pending.jsonl',
        'spans_ref':'components/base/components/nd168-a16k2/source_spans.pending.jsonl','texts':{rec['extraction_id']:'components/base/components/nd168-a16k2/extraction/normalized.txt'},'schema':'sparse-source-branch.v1'}
    for key,source,unitref,spanref,proofbase,textprefix in [
        ('tt35',priority,'legal_units.pending.jsonl','source_spans.pending.jsonl','components/tt35','tt35/extraction_snapshot/'),
        ('tt38',tt38,'legal_units.pending.jsonl','source_spans.pending.jsonl','components/tt38/base','extraction_snapshot/')]:
        cp(source/unitref,f'graphs/{key}.units.jsonl');cp(source/spanref,f'graphs/{key}.spans.jsonl')
        needed={s['extraction_id'] for s in rows(source/spanref)}
        snapshot=source/('tt35/extraction_snapshot' if key=='tt35' else 'extraction_snapshot')
        er=[r for r in rows(snapshot/'extractions.pending.jsonl') if r['extraction']['extraction_id'] in needed]
        texts={}
        for r in er:
            e=r['extraction'];ref=proofbase+'/'+textprefix+e['text_ref'];cp(snapshot/e['text_ref'],ref);texts[e['extraction_id']]=ref
            cp(snapshot/r['trace_ref'],proofbase+'/'+textprefix+r['trace_ref'])
        exported(f'components/{key}/extractions.pending.jsonl',er)
        cp(snapshot/'source_snapshot/documents.pending.jsonl',f'components/{key}/documents.pending.jsonl')
        cp(snapshot/'source_snapshot/files.pending.jsonl',f'components/{key}/files.pending.jsonl')
        graphs[key]={'units_ref':f'graphs/{key}.units.jsonl','spans_ref':f'graphs/{key}.spans.jsonl','texts':texts,'schema':'graph-part.v1.2' if key=='tt35' else 'DDD.v1.pending'}
    # Copy bytes needed by every selected proof without changing any payload refs.
    text_by_id={c['chunk_id']:c for name in ['chunks.preview','tt38_text.chunks.preview'] for c in rows(priority/(name+'.jsonl'))}
    table_by_legacy={r['legacy_preview_id']:r for r in rows(priority/'table_records.preview.jsonl')}
    selected=[];tables_out=[];additions=[];contexts=[];enc=[];dispositions=[];deps=[]
    by35={u['unit_id']:u for u in rows(priority/'legal_units.pending.jsonl')}
    oldnew={r['old_chunk_id']:r['new_chunk_id'] for r in rows(priority/'chunk_crosswalk.jsonl')}
    for s in cfg['selection']:
        s=dict(s);cid=oldnew.get(s['legacy_candidate_id'],s['legacy_candidate_id'])
        table=table_by_legacy.get(s['legacy_candidate_id']);rid=table['retrieval_id'] if table else cid
        s['record_id']=rid;dispositions.append(s)
        if s['disposition']!='selected':continue
        if table:
            if table['technical_status']!='pass' or table['encoder']['tokens_with_special']>256:raise ValueError('Selected table quarantined')
            tables_out.append(table)
        else:
            c=text_by_id[cid]
            if c['unit_id']!=s['unit_id']:raise ValueError('Selected unit binding wrong')
            additions.append(c)
            contextfile='contexts.preview.jsonl' if s['graph_id']=='tt35' else 'tt38_text.contexts.preview.jsonl'
            contexts.extend(x for x in rows(priority/contextfile) if x['chunk_id']==cid)
            source_enc=rows(priority/'encoder_inputs.jsonl') if s['graph_id']=='tt35' else rows(tt38/'encoder_inputs.jsonl')
            enc.append(next(e for e in source_enc if e['chunk_id']==cid))
        selected.append(s)
        deps.extend({'record_id':rid,**d} for d in s['required_dependencies'])
    cfg={**cfg,'selection':dispositions};write_json(root/'selection_config.json',cfg)
    old=rows(base/'chunks.jsonl');chunks=old+additions
    # Existing payloads remain unchanged, graph membership supplies resolver roots.
    memberships=[{'record_type':'chunk.v1','record_id':x['chunk_id'],'graph_id':x['graph_id'],
        'proof_base':'components/base/components/'+('base' if x['graph_id']=='base-docx' else 'nd168-a16k2')} for x in rows(base/'memberships.jsonl')]
    for s in selected:memberships.append({'record_type':'table-retrieval.v1' if s['kind']=='table' else 'chunk.v1','record_id':s['record_id'],
        'graph_id':s['graph_id'],'proof_base':'components/tt35' if s['graph_id']=='tt35' else 'components/tt38'+('' if s['kind']=='table' else '/base')})
    # Source proof bundles have distinct logical roots; mount TT38 table root explicitly.
    for c in additions:
        source=priority if c['law_id']=='35/2024/TT-BGTVT' else tt38;dest='components/tt35' if source==priority else 'components/tt38/base'
        own=[c,*[x for x in contexts if x['chunk_id']==c['chunk_id']]]
        for x in own:
            for s in __import__('json').loads(x['source_locator']):
                for k in ['raw_file_ref','text_ref']:cp(source/s[k],dest+'/'+s[k])
    # A table may need the same PDF/text even when no selected text covers that page.
    for r in tables_out:
        for source in [r['source_proof'],*[x['source_locator'] for x in r['contexts']]]:
            if isinstance(source,str):source=__import__('json').loads(source)
            for s in source:
                for k in ['raw_file_ref','text_ref']:cp(tables/s[k],'components/tt38/'+s[k])
    cp(tt38/'tables.jsonl','components/tt38/tables.jsonl');cp(tt38/'cells.jsonl','components/tt38/cells.jsonl')
    for name in ['unit_crosswalk','chunk_crosswalk']:cp(priority/(name+'.jsonl'),name+'.jsonl')
    cp(priority/'tt35/legal_units.pending.jsonl','evidence/tt35_sparse.units.jsonl')
    cp(priority/'targeted_dependencies.jsonl','evidence/targeted_dependencies.jsonl')
    for name in ['tt35.html','tt38.html','tt38-congbao.html']:
        cp(BASE_DIR/'data/source_evidence/circulars-2024'/name,'evidence/'+name)
    # Source metadata preserved as a bound observation, never promoted to verified.
    meta=(BASE_DIR/binding['metadata']['ref']).parent
    cp(meta/'source_metadata.jsonl','evidence/source_metadata.jsonl')
    write_json(root/'evidence/dependency_roles.json',{
        'runtime':'Only packaged graph/proof/text/raw/cell references and manifest mounts are read by validate_read.py',
        'historical_metadata_refs':'Original refs inside source_metadata.jsonl are provenance observations, not runtime resolver paths; legacy receipt/observed PowerShell wrappers are not copied or opened',
        'rebuild_only':'Input priority/base manifests, original source registration/capture receipts, tokenizer assets and repository validators listed in source_binding.json; needed only for full rebuild',
        'limits':'No new assertion of whole-file provenance/edition/applicability; copied official HTML and raw source bytes remain evidence only'})
    cp(Path(portable.__file__),'validate_read.py')
    exported('chunks.jsonl',chunks);exported('contexts.jsonl',rows(base/'contexts.jsonl')+contexts)
    exported('table_records.jsonl',tables_out);exported('memberships.jsonl',memberships)
    exported('selection.jsonl',dispositions);exported('dependencies.jsonl',deps);exported('encoder_inputs.jsonl',enc)
    exported('delta.jsonl',[{'record_id':c['chunk_id'],'record_type':'chunk.v1','status':'unchanged'} for c in old]+
        [{'record_id':c['chunk_id'],'record_type':'chunk.v1','status':'added'} for c in additions]+
        [{'record_id':r['retrieval_id'],'record_type':'table-retrieval.v1','status':'added'} for r in tables_out])
    comparisons=[]
    for c in additions:
        same_id=[o['chunk_id'] for o in old if o['chunk_id']==c['chunk_id']]
        same_position=[o['chunk_id'] for o in old if (o['law_id'],o['citation_path'])==(c['law_id'],c['citation_path'])]
        same_text=[o['chunk_id'] for o in old if experimental_draft.normalized(o['text_original'])==experimental_draft.normalized(c['text_original'])]
        if same_id or same_position:raise ValueError('Non-additive ID/legal-position conflict')
        comparisons.append({'record_id':c['chunk_id'],'classification':'added','same_ids':same_id,'same_legal_positions':same_position,'same_normalized_content':same_text})
    exported('candidate_comparison.jsonl',comparisons)
    stats={'text_chunks':len(chunks),'table_retrieval_records':len(tables_out),'total_retrieval_records':len(chunks)+len(tables_out),
        'contexts':len(rows(base/'contexts.jsonl'))+len(contexts),'required_read_dependencies':len(deps),'added_text':len(additions),'base_unchanged':len(old),
        'withheld':len(dispositions)-len(selected)}
    lines=['# Draft experimental composition — pending','No accepted scope, no legal verification, no serving.','| Citation | Disposition | Reason |','|---|---|---|']
    lines.extend(f"| {s['citation_path']} | {s['disposition']} | {s['reason']} |" for s in dispositions)
    (root/'review.md').write_text('\n\n'.join(lines),encoding='utf8')
    write_json(root/'source_binding.json',cfg['inputs'])
    inv=portable.inventory(root)
    manifest={'policy_version':portable.VERSION,'dataset_version':cfg['dataset_version'],'snapshot_date':'2025-01-01','status':'draft','experimental':True,
        'release_eligible':False,'corpus_version':None,'origin':'agent_review','human_reviewer_events':0,'built_at':now(),
        'required_capabilities':sorted(portable.CAPABILITIES),'graphs':graphs,'mounts':{r['source_proof_base_ref']:'components/tt38' for r in tables_out},
        'counts':stats,'input_bindings':cfg['inputs'],'source_review':'pending','edition_review':'pending','scope_status':'proposed_not_accepted','applicability':'pending_review',
        'resolved_legacy_blockers':{'DATASET_ADAPTER_TABLE_RECORD_NOT_IMPLEMENTED':'circular-composition.v1 with table-retrieval.v1 capability'},
        'code_sha256':digest(Path(__file__).read_bytes()),'files':inv,'dataset_content_sha256':digest(canonical(inv).encode())}
    write_json(root/'dataset_manifest.json',manifest);(root/'dataset_manifest.sha256').write_text(digest((root/'dataset_manifest.json').read_bytes())+'\n',encoding='ascii')
    result=portable.validate(root);write_json(root/'execution.json',{'completed_at':now(),'validation':result,'no_index_or_inference':True});return result
