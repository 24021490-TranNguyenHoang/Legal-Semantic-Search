"""Package a scope-filtered candidate around immutable v3 and validated additions."""
from collections import Counter
from pathlib import Path
import shutil
from src.experimental_dataset import load,rows,write_json,write_rows
from src.assessment_evidence import now,check_files
from src.source_contracts import digest,canonical
from src import seven_dataset_portable as portable


def build(config,run_dir,qcvn_graph_manifest=None):
    cfg=load(config);base=Path(cfg['base_dataset_manifest']).parent
    from src.circular_dataset_portable import validate
    validate(base)
    ext=Path('staging/seven-source-complete-records-002');views=Path('staging/seven-source-previews-001')
    qcvn=Path(qcvn_graph_manifest).parent if qcvn_graph_manifest is not None else Path('staging/qcvn-rule-graph-002')
    for r in [ext,views,qcvn]:check_files(r/'manifest.json')
    root=Path(run_dir);root.mkdir(parents=True);(root/'components').mkdir();shutil.copytree(base,root/'components/v3')
    (root/'additions').mkdir();(root/'objects').mkdir()
    selected_proposals={p['unit_id']:p for p in rows(ext/'scope.proposals.jsonl') if p['scope_proposal']=='included'}
    newchunks=[c for c in rows(ext/'chunks.preview.jsonl') if c['unit_id'] in selected_proposals]
    newids={c['chunk_id'] for c in newchunks}
    for name,rr in [('chunks',newchunks),('contexts',[c for c in rows(ext/'contexts.preview.jsonl') if c['chunk_id'] in newids]),
        ('encoder_inputs',[e for e in rows(ext/'encoder_inputs.jsonl') if e['chunk_id'] in newids]),
        ('scope.proposals',list(selected_proposals.values()))]:write_rows(root/f'additions/{name}.jsonl',rr)
    rr=[r for r in rows(views/'records.preview.jsonl') if r['scope_proposal']=='included']+rows(qcvn/'records.preview.jsonl')
    forms=rows(ext/'forms.jsonl');write_rows(root/'additions/records.jsonl',rr);write_rows(root/'additions/forms.jsonl',forms)
    # Finite closure for the dossier referenced by A34K2a/b: A29K3a -> A15K1b,
    # A29K3b -> original Annex XXVI. Preserve other citations, no recursive expansion.
    graph=rows(base/'graphs/tt35.units.jsonl');deps=rows(ext/'dependencies.jsonl');formdeps=[]
    extra=next(u for u in graph if u['canonical_path'].endswith('article:15/clause:1/point:b'))
    via=next(u for u in graph if u['canonical_path'].endswith('article:29/clause:3/point:b'))
    form=next(f for f in forms if f['source_annex']['literal_marker']=='XXVI')
    for c in newchunks:
        if any(d['unit_id']==c['unit_id'] for d in deps):
            deps.append({'unit_id':c['unit_id'],'required':True,'root_unit_id':extra['unit_id'],'unit_ids':[extra['unit_id']],
                'reason':'A29K3a explicitly references A15K1b identity documentation','representation':'source_unit_subtree_for_required_read','scope_use':'supporting_for_this_target_only'})
            formdeps.append({'record_id':c['chunk_id'],'form_record_id':form['record_id'],'via_unit_id':via['unit_id'],
                'required':True,'reason':'A34 -> A29K3b -> Annex XXVI application form; bounded explicit dependency'})
    law36=rows(base/'graphs/base.units.jsonl')
    transition=next(u for u in law36 if u['law_id']=='36/2024/QH15' and u['canonical_path'].endswith('article:89/clause:3'))
    # Observed effective date is not an active verdict. The actual transitional
    # paragraph and its explicit Law36 referral stay available for mandatory read.
    for c in newchunks:
        for graph_id,pool,unit in [('tt35',graph,next(u for u in graph if u['canonical_path'].endswith('article:66/clause:1'))),
            ('tt35',graph,next(u for u in graph if u['canonical_path'].endswith('article:67'))),('base-docx',law36,transition)]:
            ids={unit['unit_id']}
            while True:
                expanded=ids|{u['unit_id'] for u in pool if u['parent_unit_id'] in ids}
                if expanded==ids:break
                ids=expanded
            deps.append({'unit_id':c['unit_id'],'graph_id':graph_id,'required':True,'root_unit_id':unit['unit_id'],
                'unit_ids':sorted(ids),'dependency_role':'snapshot_transition','representation':'source_unit_subtree_for_required_read',
                'reason':'TT35 A66K1/A67 and explicit referral to Law36 A89K3; applicability remains pending, no unconditional active claim'})
    write_rows(root/'additions/dependencies.jsonl',deps);write_rows(root/'additions/form_dependencies.jsonl',formdeps)
    write_rows(root/'additions/qcvn.graph.jsonl',rows(qcvn/'region_units.pending.jsonl'))
    mounts={}
    def mount(ref):
        ref=Path(ref).as_posix()
        if ref in mounts:return
        p=Path(ref);h=digest(p.read_bytes());target='objects/'+h+p.suffix.lower()
        if not (root/target).exists():shutil.copyfile(p,root/target)
        mounts[ref]=target
    for r in rr:
        s=r['source_record']
        for p in s.get('source_proofs',[])+s.get('context_proofs',[]):mount(p['raw_ref']);mount(p['text_ref'])
    for r in forms:mount(r['raw_ref']);mount(r['text_ref'])
    used_eids={f['extraction_id'] for f in forms}|{p['extraction_id'] for r in rr for p in r['source_record'].get('source_proofs',[])+r['source_record'].get('context_proofs',[])}
    extraction_bindings={}
    for source_run in [Path('staging/qcvn-gazette-extraction-001'),Path('staging/tt35-full-layout-001')]:
        for rec in rows(source_run/'extractions.pending.jsonl'):
            e=rec['extraction'];eid=e['extraction_id']
            if eid not in used_eids:continue
            tr=(source_run/rec['trace_ref']).as_posix();ident=(source_run/rec['trace_ref']).with_name('identity.json').as_posix()
            mount(tr);mount(ident)
            extraction_bindings[eid]={'file_id':e['file_id'],'source_raw_sha256':rec['source_raw_sha256'],
                'text_ref':(source_run/e['text_ref']).as_posix(),'text_sha256':e['text_sha256'],
                'trace_ref':tr,'trace_sha256':rec['trace_sha256'],'identity_ref':ident}
    if set(extraction_bindings)!=used_eids:raise ValueError('Missing extraction identity/trace dependency')
    # v3 remains a full archival dependency, but only these member IDs become retrieval targets.
    meta={p['chunk_id']:p for p in rows(base/'components/base/metadata.jsonl')};base_meta_ids=set(meta)
    meta.update({p['record_id']:p for p in rows(base/'selection.jsonl') if p['disposition']=='selected'})
    members=[];delta=[];oldids=set();newall={}
    for fn,kind,idfield in [('chunks.jsonl','chunk.v1','chunk_id'),('table_records.jsonl','table-retrieval.v1','retrieval_id')]:
        for r in rows(base/fn):
            rid=r[idfield];oldids.add(rid);p=meta.get(rid,{})
            if p.get('scope_proposal')=='included':
                members.append({'record_id':rid,'record_type':kind,'location':'component-v3','scope_proposal':'included',
                    'scope_basis_ref':'components/v3/components/base/metadata.jsonl' if rid in base_meta_ids else 'components/v3/selection.jsonl',
                    'origin':'agent_review','applicability':'pending_review','reviewer_ref':None,'release_eligible':False})
                delta.append({'record_id':rid,'delta':'unchanged','reason':'Identical payload; explicit included proposal retained'})
            else:delta.append({'record_id':rid,'delta':'removed','reason':'Removed from candidate membership only: '+p.get('scope_proposal','pending')+' scope; archived payload retained unchanged'})
    for r,kind in [(r,'chunk.v1') for r in newchunks]+[(r,'source-retrieval.v1') for r in rr]+[(r,'form-retrieval.v1') for r in forms]:
        rid=r.get('chunk_id',r.get('record_id'))
        if any(m['record_id']==rid for m in members):continue
        members.append({'record_id':rid,'record_type':kind,'location':'additions','scope_proposal':'included',
            'scope_basis_ref':'additions/scope.proposals.jsonl' if kind=='chunk.v1' else 'additions/records.jsonl' if kind=='source-retrieval.v1' else 'additions/forms.jsonl',
            'origin':'agent_review','applicability':'pending_review','reviewer_ref':None,'release_eligible':False})
        delta.append({'record_id':rid,'delta':'added','citation_path':r.get('citation_path',r.get('source_record',{}).get('citation_path')),
            'reason':'New explicit included source-backed preview, distinct source position/type; not activated'})
    write_rows(root/'memberships.jsonl',members);write_rows(root/'delta.jsonl',delta)
    write_rows(root/'crosswalk.jsonl',[{'old_record_id':None,'new_record_id':r['record_id'],'reason':'Add previously withheld source-retrieval representation; no qrels transferred'} for r in rr]
        +[{'old_record_id':None,'new_record_id':c['chunk_id'],'unit_id':c['unit_id'],'reason':'Existing real Part/Chapter graph; new membership, original unit/chunk identity formula'} for c in newchunks])
    (root/'README.md').write_text('''# Seven-source experimental candidate\n\nOnly memberships.jsonl is the target list. components/v3 is an immutable archival source/proof dependency, **not** implicit membership. Pending/excluded records are not targets. No active corpus or index.\n\nRun `python -B validate_read.py validate --root .` and `python -B validate_read.py read --root . --record-id ID`. Standard library, Python3.11+. Query/ranking/encoder inference are not provided.\n\nWhole-record views require reading the entire record plus all required dependencies. Form records require layout/fields; they do not assert regulations from blank fields. Text/source/provenance/applicability remain pending; scope is agent proposal only. QCVN OCR drafts are excluded.\n''',encoding='utf8')
    shutil.copyfile(Path(portable.__file__),root/'validate_read.py')
    inv=portable.inventory(root);manifest={'policy_version':portable.VERSION,'dataset_version':'vtls-seven-source-experimental.v4-candidate.5',
        'status':'draft','snapshot_date':'2025-01-01','experimental':True,'release_eligible':False,'corpus_version':None,
        'origin':'agent_review','human_reviewer_events':0,'built_at':now(),'required_capabilities':sorted(portable.CAPABILITIES),
        'proof_mounts':mounts,'extraction_bindings':extraction_bindings,'record_counts':dict(Counter(m['record_type'] for m in members)),'total_records':len(members),
        'input_bindings':{'v3':{'manifest_ref':cfg['base_dataset_manifest'],'sha256':digest((base/'dataset_manifest.json').read_bytes())},
            **{r.name:{'manifest_ref':(r/'manifest.json').as_posix(),'sha256':digest((r/'manifest.json').read_bytes())} for r in [ext,views,qcvn]}},
        'source_review':'pending','edition_review':'pending','applicability':'pending_review','scope_status':'proposed_not_accepted',
        'record_encoder_contracts':{'chunk.v1':'existing immutable encoder input, <=256 tokens',
            'table-retrieval.v1':'existing immutable derived encoder input, <=256 tokens',
            'source-retrieval.v1':'whole-record mandatory read; each encoder view <=256; views are not targets',
            'form-retrieval.v1':'layout read only; no encoder/search projection implemented; consumer must not flatten into a chunk'},
        'files':inv,'dataset_content_sha256':digest(canonical(inv).encode())}
    write_json(root/'dataset_manifest.json',manifest);(root/'dataset_manifest.sha256').write_text(digest((root/'dataset_manifest.json').read_bytes())+'\n',encoding='utf8')
    return portable.validate(root)
