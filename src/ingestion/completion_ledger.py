"""Finite inventory/coverage/backlog across source branches; pending is explicit."""
from collections import Counter
from pathlib import Path
import re
from src.experimental_dataset import load, rows, write_rows, write_json
from src.source_contracts import canonical, digest, file_identity
from src.assessment_evidence import check_files, seal, now
from src.ingestion.full_source import NAMESPACE
from src.source_inventory import require_url

LAW_SOURCES={'36/2024/QH15':'SRC-001','168/2024/NĐ-CP':'SRC-002','35/2024/QH15':'SRC-003',
    '165/2024/NĐ-CP':'SRC-004','38/2024/TT-BGTVT':'SRC-005','51/2024/TT-BGTVT':'SRC-006','35/2024/TT-BGTVT':'SRC-007'}


def partition(text,entries):
    """No character disappears: overlapping facets retain all coverage references."""
    changes={0:[],len(text):[]}
    for i,r in enumerate(entries):
        a,b=r['char_start'],r['char_end']
        if not 0<=a<=b<=len(text):raise ValueError('Coverage outside extraction')
        if a==b:continue
        changes.setdefault(a,[]).append((i,True));changes.setdefault(b,[]).append((i,False))
    cuts=sorted(changes);active=set();out=[]
    for j,a in enumerate(cuts[:-1]):
        for i,add in changes[a]:
            if add:active.add(i)
            else:active.discard(i)
        b=cuts[j+1];part=text[a:b]
        disposition='source_fields_or_parser_disposition' if active else 'technical_separator' if not part.strip() else 'unprocessed_no_existing_disposition'
        out.append({'char_start':a,'char_end':b,'quote_sha256':digest(part.encode()),
            'disposition':disposition,'coverage_refs':sorted(active),
            'existing_categories':sorted({entries[i].get('category','source_region') for i in active})})
    if ''.join(text[r['char_start']:r['char_end']] for r in out)!=text:raise ValueError('Coverage partition failed')
    return out


def legal_position(path):
    # Used for backlog grouping ONLY; identity retains all real Part/Chapter ancestors.
    return '/'.join(re.findall(r'(?:article|clause|point):[^/]+',path)) or path


def discover_extractions(candidates,known_hashes):
    """Discovery is not admission. Rejected/unsealed test copies remain reported.

    Required input manifests are checked separately and still fail closed. A
    negative-test copy elsewhere in staging must not poison an unrelated run.
    """
    catalog={};rejected=[]
    for candidate in candidates:
        candidate=Path(candidate)
        for rec in rows(candidate):
            h=rec.get('source_raw_sha256');e=rec.get('extraction',{})
            if h not in known_hashes or not e or not rec.get('trace_ref'):continue
            text_path=candidate.parent/e['text_ref'];trace_path=candidate.parent/rec['trace_ref']
            if not text_path.is_file() or not trace_path.is_file():
                rejected.append({'records_ref':candidate.as_posix(),'extraction_id':e.get('extraction_id'),
                    'reason':'MISSING_DISCOVERED_TEXT_OR_TRACE','admitted':False});continue
            th=digest(text_path.read_bytes());trh=digest(trace_path.read_bytes())
            if th!=e['text_sha256'] or trh!=rec.get('trace_sha256'):
                rejected.append({'records_ref':candidate.as_posix(),'extraction_id':e.get('extraction_id'),
                    'reason':'DISCOVERED_TEXT_OR_TRACE_CHECKSUM_MISMATCH','admitted':False,
                    'actual_text_sha256':th,'declared_text_sha256':e['text_sha256'],
                    'actual_trace_sha256':trh,'declared_trace_sha256':rec.get('trace_sha256')});continue
            eid=e['extraction_id'];key=(h,eid)
            reference={'records_ref':candidate.as_posix(),'text_ref':text_path.as_posix(),'trace_ref':trace_path.as_posix()}
            if key in catalog:catalog[key]['aliases'].append(reference)
            else:catalog[key]={'source_raw_sha256':h,'extraction_id':eid,'file_id':e['file_id'],
                'text_sha256':e['text_sha256'],'trace_sha256':rec['trace_sha256'],'reference':reference,'aliases':[],
                'technical_status':rec.get('technical_status'),'review_status':'pending'}
    return catalog,rejected


def candidate_usage(manifest):
    from src import seven_dataset_portable as portable
    root=Path(manifest).parent;portable.validate(root);component=root/'components/v3'
    cm=load(component/'dataset_manifest.json')
    graphs={name:{u['unit_id']:u for u in rows(component/d['units_ref'])} for name,d in cm['graphs'].items()}
    base={r.get('chunk_id',r.get('retrieval_id')):r for fn in ['chunks.jsonl','table_records.jsonl'] for r in rows(component/fn)}
    added={r['chunk_id']:r for r in rows(root/'additions/chunks.jsonl')}
    other={r['record_id']:r for fn in ['records','forms'] for r in rows(root/f'additions/{fn}.jsonl')}
    oldmembers={r['record_id']:r for r in rows(component/'memberships.jsonl')}
    targets={};contexts=set();counts={}
    for member in rows(root/'memberships.jsonl'):
        rid=member['record_id'];r=(base|added|other)[rid];source=r.get('source_record',r)
        uid=source.get('unit_id',source.get('region_unit_id',source.get('source_annex',{}).get('annex_id')))
        if member['record_type']=='table-retrieval.v1':
            u=graphs[oldmembers[rid]['graph_id']][r['owner_unit_id']];law=u['law_id'];uid=u['unit_id']
        else:law=source['law_id']
        counts.setdefault(law,Counter())[member['record_type']]+=1
        if uid:targets.setdefault(uid,[]).append(rid)
    selected=set(m['record_id'] for m in rows(root/'memberships.jsonl'))
    for x in rows(component/'contexts.jsonl')+rows(root/'additions/contexts.jsonl'):
        if x['chunk_id'] in selected:contexts.add(x['unit_id'])
    return targets,contexts,{law:dict(count) for law,count in counts.items()}


def build(config,run_dir,candidate_manifest=None,qcvn_graph_manifest=None):
    cfg=load(config);root=Path(run_dir);root.mkdir(parents=True)
    qcvn_graph=Path(qcvn_graph_manifest).parent if qcvn_graph_manifest is not None else Path('staging/qcvn-rule-graph-002')
    if candidate_manifest is not None:
        expected=digest((qcvn_graph/'manifest.json').read_bytes())
        if not any(b['sha256']==expected for b in load(candidate_manifest)['input_bindings'].values()):
            raise ValueError('QCVN graph is not bound to selected candidate; pass --qcvn-graph-manifest explicitly')
    allfiles=rows(Path(cfg['metadata_manifest']).parent/'source_metadata.jsonl')
    allfiles+=rows('staging/qcvn-gazette-extraction-001/files.pending.jsonl')
    catalog_root=Path('staging/bm25-baseline-v1-001/dataset')
    for r in rows(catalog_root/'evidence/catalog.jsonl'):
        p=catalog_root/r['artifact_ref'];allfiles.append({'law_id':r['law_id'],'source_id':LAW_SOURCES[r['law_id']],
            'file_id':file_identity(NAMESPACE,r['law_id'],r['sha256']),'local_ref':p.as_posix(),
            'file_role':'official_comparison_pdf','source_set':LAW_SOURCES[r['law_id']]+'-historical-captured-promulgation',
            'sha256':r['sha256'],'size_bytes':r['size_bytes'],'download_url':r['url'],'retrieved_at':r['accessed_at'],
            'evidence_ref':r['evidence_id'],'status':'pending'})
    from src.ingestion.full_source import gazette_files
    ndcfg=load('config/nd168_a16k2.v1.json');p=Path(ndcfg['html_capture_ref'])/'official.html'
    receipt=load(p.parent/'capture.json')
    if receipt['sha256']!=digest(p.read_bytes()) or receipt['size_bytes']!=p.stat().st_size:raise ValueError('ND168 HTML receipt mismatch')
    allfiles.append({'law_id':'168/2024/NĐ-CP','source_id':'SRC-002','file_id':file_identity(NAMESPACE,'168/2024/NĐ-CP',digest(p.read_bytes())),
        'local_ref':p.as_posix(),'file_role':'official_alternate_html','source_set':'SRC-002-official-html-whole',
        'official_page_url':receipt['url'],'download_url':receipt['final_url'],'retrieved_at':receipt['accessed_at'],
        'retrieved_at_basis':'actual_existing_capture_not_historical_DOCX_download',
        'sha256':digest(p.read_bytes()),'size_bytes':p.stat().st_size,'evidence_ref':(p.parent/'capture.json').as_posix(),'status':'pending'})
    unique={}
    for f in allfiles:
        p=Path(f['local_ref']);h=digest(p.read_bytes())
        if h!=f['sha256'] or p.stat().st_size!=f['size_bytes']:raise ValueError('Inventory file changed')
        key=(f['law_id'],h)
        if key in unique:
            unique[key]['aliases'].append(f['local_ref']);continue
        f={**f,'aliases':[],'edition_status':'pending','source_status':'pending','applicability':'pending_review',
           'mime_type':'application/pdf' if p.suffix.lower()=='.pdf' else 'text/html' if p.suffix=='.html' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
           'source_id':LAW_SOURCES[f['law_id']]}
        if p.suffix.lower()=='.pdf':
            import pypdfium2 as pdfium
            with pdfium.PdfDocument(str(p)) as pdf:f['pages']=len(pdf)
        unique[key]=f
    files=list(unique.values());known_hashes={f['sha256'] for f in files}
    # Discover existing extraction identities, including Article22 PDF captures.
    # Dedup by identity; never guess "latest" or treat a copied payload as a new extraction.
    extraction_catalog,rejected=discover_extractions(sorted(Path('staging').rglob('extractions.pending.jsonl')),known_hashes)
    html=Path('staging/nd168-html-full-002');check_files(html/'manifest.json');he=load(html/'extraction.json');hi=load(html/'extraction/identity.json')
    if digest((html/he['text_ref']).read_bytes())!=he['text_sha256'] or digest(canonical(hi).encode())!=he['extraction_id'][2:]:raise ValueError('ND168 HTML extraction binding mismatch')
    extraction_catalog[(hi['source_raw_sha256'],he['extraction_id'])]={'source_raw_sha256':hi['source_raw_sha256'],
        'extraction_id':he['extraction_id'],'file_id':he['file_id'],'text_sha256':he['text_sha256'],
        'trace_sha256':digest((html/'extraction/trace.json').read_bytes()),'reference':{'records_ref':(html/'extraction.json').as_posix(),
        'text_ref':(html/he['text_ref']).as_posix(),'trace_ref':(html/'extraction/trace.json').as_posix()},'aliases':[],
        'technical_status':'source_backed_graph_not_legal_review','review_status':'pending'}
    file_crosswalk=[]
    for f in files:
        existing_ids={x['file_id'] for x in extraction_catalog.values() if x['source_raw_sha256']==f['sha256']}
        allocated=f['file_id']
        if f['file_role']=='official_comparison_pdf' and len(existing_ids)==1 and allocated not in existing_ids:
            f['file_id']=next(iter(existing_ids));file_crosswalk.append({'previous_inventory_file_id':allocated,'file_id':f['file_id'],
                'source_raw_sha256':f['sha256'],'law_id':f['law_id'],'reason':'Reuse unique existing validated extraction file_id; do not allocate a duplicate source identity'})
        f['extraction_branches']=[x['extraction_id'] for x in extraction_catalog.values() if x['source_raw_sha256']==f['sha256']]
        f['file_id_aliases']=sorted({x['file_id'] for x in extraction_catalog.values() if x['source_raw_sha256']==f['sha256'] and x['file_id']!=f['file_id']})
        if allocated!=f['file_id']:f['file_id_aliases'].append(allocated)
        for key in ['official_page_url','download_url']:f[key]=require_url(f.get(key))
        for key in ['retrieved_at','retrieved_at_basis','part_order','pages']:f.setdefault(key,None)
    write_rows(root/'inventory.jsonl',files);write_rows(root/'extraction_catalog.jsonl',list(extraction_catalog.values()))
    write_rows(root/'discovery_rejected.jsonl',rejected)
    write_rows(root/'file_id_crosswalk.jsonl',file_crosswalk)
    evidence_paths=list(Path('data/source_evidence').rglob('*'))+list(Path(cfg['new_source_receipt_root']).glob('*'))
    write_rows(root/'evidence_inventory.jsonl',[{'ref':p.as_posix(),'sha256':digest(p.read_bytes()),'size_bytes':p.stat().st_size,
        'role':'captured_evidence_not_automatically_a_legal_source','review_status':'pending'} for p in sorted(evidence_paths) if p.is_file()])
    regions=[];page_ledger=[];unit_ledger=[];backlog={};bindings=[]
    def backlog_add(law,pos,kind,record,branch):
        if kind in {'parser_region','source_gap'}:kind='source_region'
        key=(law,pos,kind)
        if key not in backlog:backlog[key]={'law_id':law,'position':pos,'kind':kind,'state':'remaining',
            'history':[],'source_status':'pending','applicability':'pending_review'}
        backlog[key]['history'].append({'branch':branch,'record':record})
    def bind(p):
        p=Path(p);check_files(p);bindings.append({'manifest_ref':p.as_posix(),'sha256':digest(p.read_bytes())})
    # Cover each original DOCX extraction byte/codepoint including parser non-body/gaps.
    tree=Path(cfg['docx_tree_manifest']).parent;bind(tree/'manifest.json');cov=rows(tree/'coverage.jsonl')
    original=rows(tree/'legal_units.pending.jsonl');coverage={r['unit_id']:r for r in rows(Path(cfg['docx_coverage_manifest']).parent/'unit_coverage.jsonl')}
    scopes={p['unit_id']:p for p in rows('staging/stage5-scope-survey-001/scope_proposals.jsonl')}
    scopes.update({p['unit_id']:p for p in rows('staging/stage5-pilot-refinement-001/scope_proposal_revisions.jsonl')})
    extracted=rows(tree/'extraction_snapshot/extractions.pending.jsonl')
    for rec in extracted:
        e=rec['extraction'];text=(tree/'extraction_snapshot'/e['text_ref']).read_text(encoding='utf8')
        own=[r for r in cov if r['extraction_id']==e['extraction_id']]
        for part in partition(text,own):
            regions.append({**part,'branch':'docx-original','law_id':rec['law_id'],'extraction_id':e['extraction_id'],
                'text_ref':(tree/'extraction_snapshot'/e['text_ref']).as_posix(),'scope_proposal':'pending','applicability':'pending_review'})
            if part['disposition']=='unprocessed_no_existing_disposition':backlog_add(rec['law_id'],e['extraction_id']+':'+str(part['char_start']),'uncovered_text',part,'docx-original')
        for r in own:
            if r['category'] in {'unprocessed','needs_review'}:
                backlog_add(rec['law_id'],canonical(r.get('locator',{})),'parser_region',r,'docx-original')
    for u in original:
        c=coverage.get(u['unit_id'],{});p=scopes.get(u['unit_id'],{})
        scope=p.get('scope_candidate','pending');entry={'branch':'docx-original','law_id':u['law_id'],'unit_id':u['unit_id'],
            'canonical_path':u['canonical_path'],'citation_path':u['citation_path'],'scope_proposal':scope,
            'scope_reason':p.get('reason','No completed unit-specific scope examination'),
            'technical_status':c.get('primary_reason','not_in_existing_chunk_coverage'),'scope_proposal_ref':p.get('proposal_id'),
            'source_status':'pending','edition_status':'pending','applicability':'pending_review','release_eligible':False}
        unit_ledger.append(entry)
        if scope=='pending':backlog_add(u['law_id'],legal_position(u['canonical_path']),'scope_review',{'unit_id':u['unit_id']},'docx-original')
        if c.get('primary_reason') in {'PARSER_OR_EXTRACTION_ISSUE_IMPACT','TOKEN_BUDGET_EXCEEDED','UNSUPPORTED_STRUCTURE'}:
            backlog_add(u['law_id'],legal_position(u['canonical_path']),'chunk_technical',c,'docx-original')
    for gap in rows(Path(cfg['docx_coverage_manifest']).parent/'source_gaps.jsonl'):
        backlog_add(gap.get('law_id','unknown'),canonical(gap.get('locator',gap.get('source_locator',{}))),'source_gap',gap,'coverage-source-gap')
    # All original circular pages, plus independently measured alternate/new editions.
    scans=['staging/tt35-full-layout-001','staging/tt38-full-layout-001','staging/qcvn-gazette-extraction-001',
        'staging/nd168-comparison-extraction-001','staging/law35-comparison-extraction-001']
    represented=set()
    for scan in scans:
        path=Path(scan);bind(path/'manifest.json')
        fs=rows(path/'files.pending.jsonl')
        for f in fs:
            rec=next(r for r in rows(path/'extractions.pending.jsonl') if r['extraction']['file_id']==f['file_id']);e=rec['extraction']
            text=(path/e['text_ref']).read_text(encoding='utf8');trace=load(path/rec['trace_ref'])
            for separator in trace['separators']:
                a,b=separator['char_start'],separator['char_end']
                regions.append({'char_start':a,'char_end':b,'quote_sha256':digest(text[a:b].encode()),
                    'disposition':'technical_separator','branch':scan,'law_id':f['law_id'],
                    'extraction_id':e['extraction_id'],'scope_proposal':'not_a_target','applicability':'not_assessed'})
            for n in trace['nodes']:
                if n['kind']!='page':continue
                page=n['locator']['page_start'];cache=load(path/'pages'/f['file_id']/f'page-{page:04d}.json')
                page_ledger.append({'branch':scan,'law_id':f['law_id'],'file_id':f['file_id'],'source_sha256':f['sha256'],
                    'pdf_page':page,'extraction_id':e['extraction_id'],'locator':n['locator'],
                    'chars':len(cache['normalized_text']),'tables':len(cache['tables']),'cells':len(cache['cells']),
                    'images':len(cache['images']),'blockers':cache['blockers'],'content_review':'not_implied_by_reader',
                    'disposition':'reader_layout_measured_semantics_pending' if cache['normalized_text'].strip() else 'no_text_not_blank_decision',
                    'scope_proposal':'pending','applicability':'pending_review'})
                # Partition the page locally, then restore absolute offsets.
                local=partition(cache['normalized_text'],cache['lines'])
                regions.extend({**r,'char_start':r['char_start']+n['char_start'],'char_end':r['char_end']+n['char_start'],
                    'branch':scan,'law_id':f['law_id'],'extraction_id':e['extraction_id'],'locator':n['locator'],
                    'scope_proposal':'pending','applicability':'pending_review'} for r in local)
                if cache['images'] or cache['blockers']:
                    backlog_add(f['law_id'],f['sha256']+':page:'+str(page),'page_visual_or_reader',
                        {'pdf_page':page,'blockers':cache['blockers'],'images':len(cache['images'])},scan)
                represented.add((f['sha256'],page))
    # The old 403-page failed text is retained with its actual reader errors, not marked resolved by a different edition.
    path=Path('staging/tt51-preview-003');bind(path/'manifest.json')
    oldfiles={f['file_id']:f for f in files}
    for p in rows(path/'page_coverage.jsonl'):
        f=oldfiles[p['file_id']];page_ledger.append({'branch':path.as_posix(),'law_id':f['law_id'],
            'file_id':f['file_id'],'source_sha256':f['sha256'],'pdf_page':p['page'],
            'disposition':'original_reader_partial_preserved_alternate_available_not_offset_equivalent',
            'blockers':p['blockers'],'chars':p['codepoints'],'scope_proposal':'pending','applicability':'pending_review'})
        represented.add((f['sha256'],p['page']))
    # Reuse real historical PDF extractions before calling a comparison page unextracted.
    for f in files:
        branches=[x for x in extraction_catalog.values() if x['source_raw_sha256']==f['sha256']]
        for x in branches:
            trace=load(x['reference']['trace_ref'])
            qpath=Path(x['reference']['records_ref']).parent/'quality_issues.jsonl'
            quality=rows(qpath) if qpath.exists() else []
            for n in trace['nodes']:
                if n['kind']!='page':continue
                page=n['locator']['page_start']
                if (f['sha256'],page) in represented:continue
                warnings=[q for q in quality if q.get('extraction_id')==x['extraction_id'] and q.get('locator',{}).get('page_start')==page]
                page_ledger.append({'branch':'existing_source_extraction_branch','law_id':f['law_id'],'file_id':f['file_id'],
                    'source_sha256':f['sha256'],'pdf_page':page,'extraction_id':x['extraction_id'],'locator':n['locator'],
                    'char_start':n['char_start'],'char_end':n['char_end'],'quote_sha256':n['quote_sha256'],
                    'reference':x['reference'],'disposition':'historical_extraction_available_content_review_still_scoped',
                    'blockers':[q['code'] for q in warnings],'quality_issues':warnings,
                    'scope_proposal':'pending','applicability':'pending_review'})
                if warnings:backlog_add(f['law_id'],f['sha256']+':page:'+str(page),'page_visual_or_reader',
                    {'warnings':warnings,'evidence_ref':qpath.as_posix()},'historical-pdf-extraction')
                represented.add((f['sha256'],page))
    # Remaining captured comparison PDFs have one explicit unextracted full-page region each.
    for f in files:
        for page in range(1,(f.get('pages') or 0)+1):
            if (f['sha256'],page) not in represented:
                page_ledger.append({'branch':'captured_comparison_not_extracted','law_id':f['law_id'],'file_id':f['file_id'],
                    'source_sha256':f['sha256'],'pdf_page':page,'disposition':'unextracted_full_page_region',
                    'blockers':['NO_EXTRACTION_FOR_THIS_COMPARISON_EDITION'],'scope_proposal':'pending','applicability':'pending_review'})
    # New source/ancestor graphs coexist; no union of incompatible parents or offsets.
    for branch,path in [('nd168-html','staging/nd168-html-full-002'),('tt35-part-graph','staging/circular-priority-006'),('tt38','staging/tt38-preview-003')]:
        path=Path(path);bind(path/'manifest.json')
        uu=rows(path/'legal_units.pending.jsonl')
        if branch=='nd168-html':
            e=load(path/'extraction.json');text=(path/e['text_ref']).read_text(encoding='utf8')
            cc=rows(path/'coverage.jsonl')
            for r in partition(text,cc):
                regions.append({**r,'branch':branch,'law_id':'168/2024/NĐ-CP','extraction_id':e['extraction_id'],
                    'scope_proposal':'pending','applicability':'pending_review'})
        proposals={p['unit_id']:p for p in rows(path/'scope.proposals.jsonl')} if (path/'scope.proposals.jsonl').exists() else {}
        if branch=='nd168-html':
            proposals.update({p['unit_id']:p for p in rows('staging/seven-source-repairs-001/scope.proposals.jsonl')})
        if branch=='tt35-part-graph':
            mapping={r['new_unit_id']:r['old_unit_id'] for r in rows(path/'unit_crosswalk.jsonl') if r['old_unit_id']}
            oldp={p['unit_id']:p for p in rows('staging/tt35-preview-005/scope.proposals.jsonl')}
            proposals={new:oldp.get(old,{}) for new,old in mapping.items()}
            proposals.update({p['unit_id']:p for p in rows('staging/seven-source-complete-records-002/scope.proposals.jsonl')})
        for u in uu:
            p=proposals.get(u['unit_id'],{});scope=p.get('scope_proposal',p.get('scope_candidate','pending'))
            unit_ledger.append({'branch':branch,'law_id':u['law_id'],'unit_id':u['unit_id'],'canonical_path':u['canonical_path'],
                'citation_path':u['citation_path'],'scope_proposal':scope,'scope_reason':p.get('reason',p.get('scope_reason','Not examined on this binding')),
                'technical_status':'graph_roundtrip_pending_semantics','source_status':'pending','edition_status':'pending','applicability':'pending_review'})
            if scope=='pending':backlog_add(u['law_id'],legal_position(u['canonical_path']),'scope_review',{'unit_id':u['unit_id']},branch)
    # Keep all thirteen circular blockers and their new source-local dispositions.
    ttold={u['unit_id']:u for u in rows('staging/tt35-preview-005/legal_units.pending.jsonl')}
    rebound={r['old_unit_id']:r['new_unit_id'] for r in rows('staging/circular-priority-006/unit_crosswalk.jsonl') if r['old_unit_id']}
    fixed={c['unit_id'] for c in rows('staging/seven-source-complete-records-002/chunks.preview.jsonl')}
    for c in rows('staging/tt35-preview-005/unit_results.jsonl'):
        if c['status']!='blocked_preview':continue
        u=ttold[c['unit_id']];position=legal_position(u['canonical_path'])
        backlog_add(u['law_id'],position,'chunk_technical',c,'tt35-original-preview')
        if rebound.get(c['unit_id']) in fixed:
            backlog[(u['law_id'],position,'chunk_technical')].update(state='resolved_unrelated_sibling_table_impact_only',
                remaining='Other eight table owners remain blocked; source/scope/applicability are independent')
    for run,law in [(qcvn_graph.as_posix(),'51/2024/TT-BGTVT'),('staging/tt35-source-regions-001','35/2024/TT-BGTVT')]:
        path=Path(run);bind(path/'manifest.json')
        for filename in ['region_units.pending.jsonl','annexes.jsonl']:
            if (path/filename).exists():
                for n in rows(path/filename):
                    uid=n.get('region_unit_id',n.get('annex_id'))
                    unit_ledger.append({'branch':run,'law_id':law,'region_unit_id':uid,'kind':n.get('kind','annex'),
                        'scope_proposal':n['scope_proposal'],'technical_status':'physical_or_rule_representation_pending_semantics','applicability':'pending_review'})
                    if n['scope_proposal']=='pending':backlog_add(law,uid,'scope_review',
                        {'region_unit_id':uid,'source_artifact_ref':(path/filename).as_posix(),
                         'note':'Unit/region-wide scope not inherited from a selected subtree/form proposal'},run)
    physical={r['region_id']:r for r in rows('staging/qcvn-source-regions-001/regions.jsonl')}
    for d in rows(qcvn_graph/'dispositions.jsonl'):
        if d['disposition']!='UNRESOLVED_ANNEX_CONTINUATION_OR_IMAGE_HEADING':continue
        r=physical[d['region_id']];p=r['source_proof'];pos=p['file_id']+':page:'+str(p['locator']['page_start'])
        backlog_add('51/2024/TT-BGTVT',pos,'annex_boundary_unprocessed',
            {'region_id':r['region_id'],'source_proof':p,'reason':d['disposition']},qcvn_graph.as_posix())
    # Deduplicated technical history; status changes only for the exact validated condition.
    all_units=original+rows('staging/circular-priority-006/legal_units.pending.jsonl')
    for r in rows('staging/seven-source-previews-001/records.preview.jsonl'):
        src=r['source_record'];position=legal_position(next((u['canonical_path'] for u in all_units if u['unit_id']==src.get('unit_id')),'')) or src['citation_path']
        key=(src.get('law_id','unknown'),position,'chunk_technical')
        backlog_add(key[0],key[1],key[2],{'new_record_id':r['record_id'],'old_chunk_id':src.get('chunk_id'),'condition':'complete bounded encoder views; whole record mandatory'},'new_encoder_views')
        backlog[key]['state']='resolved_encoder_representation_only';backlog[key]['remaining']='Scope/source/applicability not resolved; needs new consumer capability'
    for r in rows('staging/leaf-articles-preview-002/chunks.preview.jsonl'):
        uid=r['unit_id'];u=next((u for u in original if u['unit_id']==uid),None)
        if u:
            key=(u['law_id'],legal_position(u['canonical_path']),'chunk_technical')
            if key in backlog:backlog[key].update(state='resolved_existing_leaf_preview',remaining='Scope/source/applicability remain separate',
                evidence_ref='staging/leaf-articles-preview-002/manifest.json')
    for r in rows('staging/seven-source-repairs-001/candidates.before_after.jsonl'):
        oldunit=next(u for u in original if u['unit_id']==r['old_unit_id'])
        key=(r['law_id'],legal_position(oldunit['canonical_path']),'chunk_technical')
        if key in backlog:backlog[key].update(state='partial_resolved_source_branch_or_physical_representation',
            remaining='Original DOCX parser remains unchanged; new source/region is not human verified',
            evidence_ref='staging/seven-source-repairs-001/manifest.json')
    for r in rows('staging/composition-relevance-review-001/source_only_backlog.jsonl'):
        u=r.get('unit',{});backlog_add(u.get('law_id','35/2024/TT-BGTVT'),legal_position(u.get('canonical_path',canonical(r))),'source_only',r,'relevance-review')
    for f in files:backlog_add(f['law_id'],f['sha256'],'source_edition_review',{'file_id':f['file_id'],'evidence_ref':f.get('evidence_ref')},'source_inventory')
    candidate_counts={}
    if candidate_manifest is not None:
        targets,context_ids,candidate_counts=candidate_usage(candidate_manifest)
        for entry in unit_ledger:
            uid=entry.get('unit_id',entry.get('region_unit_id'))
            entry['candidate_record_ids']=targets.get(uid,[])
            entry['candidate_context_use']=uid in context_ids
        for key,entry in backlog.items():
            if entry['kind']!='source_only':continue
            unit=entry['history'][0]['record'].get('unit',{});uid=unit.get('unit_id')
            if uid in targets:entry.update(state='resolved_candidate_target_not_qrel_or_approval',candidate_record_ids=targets[uid])
            elif uid in context_ids:entry.update(state='resolved_context_use_not_target',reason='Parent lead is source-backed context of selected points; not another legal target')
        bindings.append({'manifest_ref':Path(candidate_manifest).as_posix(),'sha256':digest(Path(candidate_manifest).read_bytes())})
    bind(Path('staging/seven-source-repairs-001/manifest.json'))
    write_rows(root/'page_ledger.jsonl',page_ledger);write_rows(root/'region_ledger.jsonl',regions);write_rows(root/'unit_ledger.jsonl',unit_ledger)
    write_rows(root/'backlog.jsonl',list(backlog.values()));write_rows(root/'input_bindings.jsonl',bindings)
    matrix=[]
    for law,sid in LAW_SOURCES.items():
        fs=[f for f in files if f['law_id']==law];pp=[p for p in page_ledger if p['law_id']==law];uu=[u for u in unit_ledger if u['law_id']==law]
        matrix.append({'source_id':sid,'law_id':law,'files':len(fs),'registered_pdf_pages':sum(f.get('pages') or 0 for f in fs),
            'page_rows':len(pp),'pdf_pages_without_extraction':sum(p['disposition']=='unextracted_full_page_region' for p in pp),
            'unit_or_region_rows_across_branches':len(uu),'scope_proposals':dict(Counter(u['scope_proposal'] for u in uu)),
            'candidate_memberships':candidate_counts.get(law,{}),
            'source_edition':'pending','applicability':'pending_review','not_complete_if_semantics_unreviewed':True})
    write_json(root/'matrix.json',matrix)
    report={'inventory_files':len(files),'pages':len(page_ledger),'region_intervals':len(regions),'unit_or_region_rows':len(unit_ledger),
        'backlog_groups':len(backlog),'scope_pending_rows':sum(u['scope_proposal']=='pending' for u in unit_ledger),
        'legal_review':'pending','all_seven_sources_semantically_complete':False}
    write_json(root/'validation_report.json',report)
    seal(root,{'manifest_type':'seven-source-coverage-ledger.v1','built_at':now(),'origin':'agent_review','release_eligible':False,
        'code_sha256':digest(Path(__file__).read_bytes())})
    return report
