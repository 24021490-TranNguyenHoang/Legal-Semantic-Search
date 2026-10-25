"""Explicit narrow additions from read source fields; no scope inheritance."""
from pathlib import Path
import copy
import re
from src import chunk_preview_v2
from src.chunk_preview import source_proof
from src.experimental_dataset import load, rows, write_json, write_rows
from src.assessment_evidence import now, seal, check_files
from src.source_contracts import canonical, digest
from src.ingestion.full_preview import circular_data, EncoderCache
from src.ingestion.source_regions import identity
from src.ingestion import encoder_views


def form_identity(form):
    return {'identity_schema':'form-retrieval.v1','law_id':form['law_id'],'citation_path':form['citation_path'],
        'source_raw_sha256':form['source_raw_sha256'],'extraction_id':form['extraction_id'],
        'char_start':form['char_start'],'char_end':form['char_end'],'text_original':form['text_original'],
        'form_fields':form['form_fields']}


def sibling_table_dispositions(data,target):
    """Only a physically bounded TABLE issue wholly in another real point is unrelated.

    Never suppress numbering/conflict issues, ancestor own fields, or table-owner gaps.
    The original issue remains in the evidence/disposition file.
    """
    by={u['unit_id']:u for u in data['units']};spans=data['spans'];kept=[];notes=[]
    selected={target['unit_id']};node=target
    while node['parent_unit_id']:
        node=by[node['parent_unit_id']];selected.add(node['unit_id'])
    used=[s for s in spans if s['unit_id'] in selected]
    positions={u['unit_id']:min((s['char_start'] for s in spans if s['unit_id']==u['unit_id']),default=-1) for u in data['units']}
    for q in data['issues']:
        a,b=q.get('char_start'),q.get('char_end');owner=None
        if q['code']=='TABLE_STRUCTURE_NOT_PARSED' and type(a) is int and type(b) is int and a<b:
            before=[u for u in data['units'] if positions[u['unit_id']]>=0 and positions[u['unit_id']]<=a]
            owner=max(before,key=lambda u:positions[u['unit_id']],default=None)
        safe=(owner is not None and owner['unit_type']=='point' and target['unit_type']=='point'
              and owner['parent_unit_id']==target['parent_unit_id'] and owner['unit_id']!=target['unit_id']
              and not any(s['extraction_id']==q['extraction_id'] and s['char_start']<b and a<s['char_end'] for s in used)
              and not any(a<pos<b for pos in positions.values()))
        if safe:
            notes.append({'target_unit_id':target['unit_id'],'issue':q,'owner_unit_id':owner['unit_id'],
                'disposition':'unrelated_sibling_physical_table_not_used_by_target_or_ancestor_own_fields',
                'owner_start':positions[owner['unit_id']], 'policy_version':'bounded-sibling-table-impact.v1'})
        else:kept.append(q)
    return kept,notes


def build(config,run_dir):
    cfg=load(config);base=Path(cfg['tt35_manifest']).parent;priority=Path(cfg['priority_manifest']).parent
    check_files(base/'manifest.json');check_files(priority/'manifest.json')
    root=Path(run_dir);root.mkdir(parents=True);encode=EncoderCache(base,root/'encoder_cache.jsonl')
    units=rows(priority/'legal_units.pending.jsonl');spans=rows(priority/'source_spans.pending.jsonl');by={u['unit_id']:u for u in units}
    data=circular_data(base,units,spans);chunk_cfg=load('config/stage6_points.v1.json')['chunk']
    candidates=[u for u in units if re.search(r'/article:21/clause:4/point:(a|b|d|đ|e)$',u['canonical_path'])]
    candidates += [u for u in units if '/article:34/' in u['canonical_path'] and not any(c['parent_unit_id']==u['unit_id'] for c in units)]
    chunks=[];contexts=[];dispositions=[];issues=[];proposals=[];inputs=[];dependencies=[]
    for u in candidates:
        local=copy.copy(data);local['issues'],notes=sibling_table_dispositions(data,u)
        result=chunk_preview_v2.build_chunks(local,base,{**chunk_cfg,'target_unit_ids':[u['unit_id']]},
            ['PENDING_SOURCE','PENDING_APPLICABILITY','AGENT_REVIEW_ONLY'],encode,reference_prefix='tt35/')
        chunks.extend(result['chunks']);contexts.extend(result['contexts']);inputs.extend(result['encoder_inputs']);issues.extend(result['issues']);dispositions.extend(notes)
        scope='included' if '/article:34/' in u['canonical_path'] else 'excluded'
        reason=('BRD §3.1/UC-03: quyền, nghĩa vụ và điều kiện cấp GPLX trực tiếp đối với người trúng tuyển, quá hạn, mất GPLX; đã đọc own text và Điều34/Khoản cha, không suy từ query.'
                if scope=='included' else 'BRD §3.1: tập huấn và điều kiện sát hạch viên/cơ quan, không phải người học hoặc người dự sát hạch; sửa kỹ thuật không đổi kết luận hiệu lực.')
        proposals.append({'unit_id':u['unit_id'],'unit_sha256':digest(canonical(u).encode()),'citation_path':u['citation_path'],
            'scope_proposal':scope,'reason':reason,'origin':'agent_review','reviewer_ref':None,
            'assessed_at':now(),'scope_status':'proposed','applicability':'pending_review','release_eligible':False,
            'source_span_ids':[s['span_id'] for s in spans if s['unit_id']==u['unit_id']]})
        if re.search(r'/article:34/clause:2/point:[ab]$',u['canonical_path']):
            for path in ['article:17/clause:1','article:17/clause:2','article:17/clause:3','article:29/clause:3']:
                target=next(x for x in units if x['canonical_path'].endswith('/'+path))
                descendants={target['unit_id']}
                while True:
                    expanded=descendants|{x['unit_id'] for x in units if x['parent_unit_id'] in descendants}
                    if expanded==descendants:break
                    descendants=expanded
                dependencies.append({'unit_id':u['unit_id'],'required':True,'root_unit_id':target['unit_id'],
                    'unit_ids':sorted(descendants),'reason':'Explicit A34K2a/b reference to exam contents or application dossier',
                    'representation':'source_unit_subtree_for_required_read','scope_use':'supporting_for_this_target_only'})
    # Two visually compared one-page applicant forms, with every source line and measured geometry.
    regions_root=Path('staging/tt35-source-regions-001');check_files(regions_root/'manifest.json')
    regions={r['region_id']:r for r in rows(regions_root/'regions.jsonl')};forms=[]
    source=Path('staging/tt35-full-layout-001');fs=rows(source/'files.pending.jsonl');ers=rows(source/'extractions.pending.jsonl')
    for annex in rows(regions_root/'annexes.jsonl'):
        if annex['literal_marker'] not in {'XI','XXVI'}:continue
        rr=[regions[rid] for rid in annex['line_region_ids']];f=next(f for f in fs if f['file_id']==annex['file_id'])
        rec=next(r for r in ers if r['extraction']['file_id']==f['file_id']);e=rec['extraction']
        node=next(n for n in load(source/rec['trace_ref'])['nodes'] if n['kind']=='page' and n['locator']['page_start']==annex['page_start'])
        text=(source/e['text_ref']).read_text(encoding='utf8')[node['char_start']:node['char_end']]
        form={'record_type':'form-retrieval.v1','law_id':f['law_id'],'citation_path':f"35/2024/TT-BGTVT > Phụ lục {annex['literal_marker']}",
            'source_annex':annex,'text_original':text,'form_fields':[
                {'source_region_id':r['region_id'],'text_original':r['content'],'source_proof':r['source_proof'],
                 'role':'fillable_line' if re.search(r'\.{3,}|…',r['content']) else 'source_label_or_instruction'} for r in rr],
            'source_raw_sha256':f['sha256'],'file_id':f['file_id'],'extraction_id':e['extraction_id'],
            'char_start':node['char_start'],'char_end':node['char_end'],'text_sha256':digest(text.encode()),
            'raw_ref':f['local_ref'],'text_ref':(source/e['text_ref']).as_posix(),
            'scope_proposal':'included','scope_reason':'BRD UC-03: mẫu đơn dành cho người học/dự sát hạch hoặc người xin đổi/cấp lại GPLX; đã đọc text và ảnh đầy đủ trang mẫu.',
            'visual_review':{'origin':'agent_review','pdf_page':annex['page_start'],'reviewed_at':now(),
                'limits':'Two one-page forms only; confirms labels/fields/order/photo requirement, not whole annex provenance or applicability'},
            'required_capabilities':['form-layout-read.v1'],'applicability':'pending_review','release_eligible':False,'origin':'agent_review'}
        form['identity']=form_identity(form)
        form['record_id']='fr_'+digest(canonical(form['identity']).encode());forms.append(form)
    for name,value in [('chunks.preview',chunks),('contexts.preview',contexts),('encoder_inputs',inputs),('issues',issues),
                       ('issue_dispositions',dispositions),('scope.proposals',proposals),('dependencies',dependencies),('forms',forms)]:write_rows(root/(name+'.jsonl'),value)
    result={'tt35_targets_attempted':len(candidates),'chunks':len(chunks),'contexts':len(contexts),
        'remaining_issues':len(issues),'unrelated_sibling_table_dispositions':len(dispositions),'forms':len(forms),
        'proposed_included':sum(p['scope_proposal']=='included' for p in proposals),'applicability':'pending_review'}
    write_json(root/'validation_report.json',result)
    seal(root,{'manifest_type':'seven-source-narrow-completion.v1','built_at':now(),'origin':'agent_review','release_eligible':False,
               'code_sha256':digest(Path(__file__).read_bytes())})
    return result
