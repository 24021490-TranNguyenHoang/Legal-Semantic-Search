"""Source-branch repair dispositions; immutable DOCX offsets are never corrected."""
from pathlib import Path
from src.experimental_dataset import load,rows,write_rows,write_json
from src.assessment_evidence import now,seal,check_files
from src.source_contracts import digest,canonical
from src.ingestion.completion_ledger import legal_position


def build(run_dir):
    root=Path(run_dir);root.mkdir(parents=True)
    branch=Path('staging/nd168-html-full-002');check_files(branch/'manifest.json')
    units=rows(branch/'legal_units.pending.jsonl');spans=rows(branch/'source_spans.pending.jsonl')
    old=Path('staging/stage4-docx-005');check_files(old/'manifest.json');uu=rows(old/'legal_units.pending.jsonl')
    rec=next(r for r in rows(old/'extraction_snapshot/extractions.pending.jsonl') if r['law_id']=='35/2024/QH15')
    e=rec['extraction'];base=old/'extraction_snapshot';text=(base/e['text_ref']).read_text(encoding='utf8');trace=load(base/rec['trace_ref'])
    tables=[]
    for index,clause,scope,reason in [(1,1,'excluded','BRD §3.1/3.3: bảng xác định danh mục phí và cơ quan quyết định, không quy định mức phí hay nghĩa vụ cụ thể để trả lời hành vi người tham gia.'),
        (2,2,'excluded','BRD §3.3: danh mục quy hoạch kết cấu hạ tầng và văn bản quản lý, ngoài nghiệp vụ người tham gia/GPLX/chế tài cá nhân.')]:
        table=next(n for n in trace['nodes'] if n['kind']=='table' and n['locator']['table_index']==index)
        owner=next(u for u in uu if u['law_id']=='35/2024/QH15' and u['canonical_path'].endswith(f'article:84/clause:{clause}'))
        cells=[]
        for n in trace['nodes']:
            if n['kind']!='cell' or n['locator'].get('table_index')!=index:continue
            a,b=n['char_start'],n['char_end'];cells.append({'row':n['locator']['row_index'],'column':n['locator']['cell_index'],
                'text_original':text[a:b],'source_proof':{'extraction_id':e['extraction_id'],'file_id':e['file_id'],
                    'locator':n['locator'],'char_start':a,'char_end':b,'quote_sha256':digest(text[a:b].encode()),
                    'locator_id':n['locator_id'],'offset_space':'normalized_extraction_unicode_codepoints'}})
        if len(cells)!=6 or {(c['row'],c['column']) for c in cells}!={(r,c) for r in [0,1] for c in [0,1,2]}:raise ValueError('Unexpected amendment-table geometry')
        grid=[[next(c['text_original'] for c in cells if c['row']==r and c['column']==col) for col in range(3)] for r in range(2)]
        reconstructed='\n'.join('\t'.join(row) for row in grid)
        if reconstructed!=text[table['char_start']:table['char_end']]:raise ValueError('Amendment table roundtrip mismatch')
        t={'record_type':'amendment-table-region.v1','owner_unit_id':owner['unit_id'],'law_id':owner['law_id'],
            'citation_path':owner['citation_path'],'table_index':index,'cells':cells,'grid':grid,
            'source_table_ref':{'extraction_id':e['extraction_id'],'char_start':table['char_start'],'char_end':table['char_end'],'locator':table['locator']},
            'text_original':reconstructed,'header_row':0 if index==2 else None,
            'column_role_proposals':['mục phí','loại phí','cơ quan có thẩm quyền'] if index==1 else None,
            'column_role_notice':'Agent interpretation, not invented source header' if index==1 else 'Source header retained literally',
            'scope_proposal':scope,'scope_reason':reason,'applicability':'pending_review','release_eligible':False,'origin':'agent_review',
            'visual_evidence_ref':'staging/blocked-source-review-002/evidence_pages/L35-page-067.png',
            'visual_review_limit':'Compared all cells and surrounding A84K1/K2 on page67; no whole-file provenance verification'}
        t['region_id']='atr_'+digest(canonical(t).encode());tables.append(t)
    proposals=[]
    for u in units:
        if any(p in u['canonical_path'] for p in ['article:39/clause:9','article:40/clause:2','article:40/clause:3']):
            proposals.append({'unit_id':u['unit_id'],'law_id':u['law_id'],'citation_path':u['citation_path'],
                'scope_proposal':'excluded','scope_reason':'BRD §3.1/§3.3: chế tài cơ sở đào tạo/trung tâm/cơ sở đăng kiểm hoặc thử nghiệm, không phải người học/người lái; đã đọc own text và Khoản cha, không suy scope từ sửa marker.',
                'source_span_ids':[s['span_id'] for s in spans if s['unit_id']==u['unit_id']],
                'origin':'agent_review','reviewed_at':now(),'reviewer_ref':None,'applicability':'pending_review','release_eligible':False,
                'visual_evidence_refs':[f'staging/blocked-source-review-002/evidence_pages/ND168-page-0{p}.png' for p in [84,85,86]]})
    before=rows('staging/blocked-source-repair-003/candidates.before_after.jsonl');after=[]
    for c in before:
        u=c['unit'];position=legal_position(u['canonical_path']);matches=[n for n in units if legal_position(n['canonical_path'])==position] if c['law_id']=='168/2024/NĐ-CP' else []
        if matches:
            target=matches[0];result='new_official_HTML_graph_source_roundtrip_available'
            details={'new_unit_id':target['unit_id'],'new_source_spans':[s for s in spans if s['unit_id']==target['unit_id']],
                'identity_reason':'Own source text/ancestor identity recalculated for official HTML; no offsets copied',
                'scope_proposal':'excluded' if 'article:39/' in position or 'article:40/' in position else 'included_proposal_from_existing_A16_recovery'}
        elif 'article:84/' in position:
            result='physical_cells_represented_and_visual_compared_not_legal_clause_parser_completion'
            details={'table_region_id':next(t['region_id'] for t in tables if t['owner_unit_id']==u['unit_id']),
                     'scope_proposal':'excluded','technical_limit':'Amending text kept in table-region layer; no fabricated child units'}
        else:
            result='reuse_existing_scoped_layout_disposition_and_preview';details={'artifact_ref':'staging/blocked-source-repair-003/layout_disposition.json',
                'technical_limit':'Do not remove global extraction warning or assert full-file review'}
        after.append({'old_unit_id':u['unit_id'],'law_id':u['law_id'],'citation_path':u['citation_path'],'before_action':c['action'],
            'after':result,**details,'source_status':'pending','applicability':'pending_review','release_eligible':False,'origin':'agent_review'})
    write_rows(root/'amendment_tables.jsonl',tables);write_rows(root/'scope.proposals.jsonl',proposals);write_rows(root/'candidates.before_after.jsonl',after)
    write_json(root/'validation_report.json',{'original_candidates':len(before),'dispositions':len(after),'amendment_tables':len(tables),'cells':sum(len(t['cells']) for t in tables),
        'new_HTML_scoped_excluded_proposals':len(proposals),'not_all_original_parser_warnings_resolved':True,'legal_review':'pending'})
    seal(root,{'manifest_type':'seven-source-repair-dispositions.v1','built_at':now(),'origin':'agent_review','release_eligible':False,
        'code_sha256':digest(Path(__file__).read_bytes())})
    return load(root/'validation_report.json')
