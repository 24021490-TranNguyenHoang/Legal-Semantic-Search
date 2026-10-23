"""Circular page survey and sparse text preview, using existing Stage3/grammar/builders.

No second CLI: exposed by the existing PDF preview entry point. Annexes are
preserved by page/region; forms and QCVN decimal structures are not guessed.
"""
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import json
import re
import shutil
import unicodedata
from src import chunk_preview_articles, chunk_preview_v2, encoder_input
from src.assessment_evidence import now, seal, check_files, inventory
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion import circular_layout, pdf_layout, legal_tree
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest
from src.legal_parser import check_contracts

VERSION='circular-text-preview.v1'
CODE=['src/ingestion/circular_preview.py','src/ingestion/circular_layout.py','src/ingestion/pdf_layout.py',
      'src/ingestion/legal_tree.py','src/chunk_preview.py','src/chunk_preview_v2.py','src/chunk_preview_articles.py','src/encoder_input.py','src/ingestion/circular_reader.py']
BLOCKERS=['PENDING_SOURCE','PENDING_APPLICABILITY','AGENT_REVIEW_ONLY','EXPERIMENTAL_NOT_CORPUS']


def structure_dependencies(parsed):
    """Real source ancestors omitted by the sparse DDD projection, never fake units."""
    by={u['unit_id']:u for u in parsed['units']};groups=[]
    for line in parsed['structure']:
        marker=re.match(r'^(Phần|PHẦN|Chương|CHƯƠNG|Mục)\s+([^\s.:]+)',line['text'])
        if marker:
            groups.append({'kind':marker[1].casefold(),'designation':marker[2],'source_lines':[line]})
        elif groups:groups[-1]['source_lines'].append(line)
    result=[]
    for u in parsed['units']:
        article=u
        while article['unit_type'] not in {'article','document'}:article=by[article['parent_unit_id']]
        if article['unit_type']=='document':continue
        position=min(s['char_start'] for s in parsed['spans'] if s['unit_id']==article['unit_id'])
        available=[g for g in groups if g['source_lines'][0]['char_start']<position]
        part=next((g for g in reversed(available) if g['kind']=='phần'),None)
        floor=part['source_lines'][0]['char_start'] if part else -1
        chapter=next((g for g in reversed(available) if g['kind']=='chương' and g['source_lines'][0]['char_start']>floor),None)
        result.append({'unit_id':u['unit_id'],'projected_parent_unit_id':u['parent_unit_id'],
            'source_ancestors':[g for g in [part,chapter] if g],
            'status':'source_ancestry_preserved_in_sidecar_not_official_DDD_parent_tree'})
    return result


def survey(root):
    import pdfplumber
    import pypdfium2 as pdfium
    sources={s['file_id']:s for s in rows(root/'extraction_snapshot/source_snapshot/files.pending.jsonl')}
    pages=[];tables=[];cells=[];lines=[];figures=[]
    for rec in rows(root/'extraction_snapshot/extractions.pending.jsonl'):
        e=rec['extraction'];src=sources[e['file_id']];raw=root/'sources'/Path(src['measured']['raw_file_ref']).name
        text=(root/'extraction_snapshot'/e['text_ref']).read_text(encoding='utf8')
        trace=load(root/'extraction_snapshot'/rec['trace_ref']);nodes=[n for n in trace['nodes'] if n['kind']=='page']
        if json.loads(e['tool_version']).get('reader')=='pypdfium2':
            measured=survey_pdfium_annex(raw,rec,text,nodes)
            pages.extend(measured['pages']);figures.extend(measured['figures']);continue
        other=pdfium.PdfDocument(str(raw))
        with pdfplumber.open(raw) as pdf:
            if len(nodes)!=len(pdf.pages):raise ValueError('Page count mismatch')
            for i,(page,n) in enumerate(zip(pdf.pages,nodes),1):
                source=text[n['char_start']:n['char_end']]
                if unicodedata.normalize('NFC',(page.extract_text() or '').replace('\r\n','\n').replace('\r','\n'))!=source:raise ValueError('Reader text differs from Stage3')
                op=other[i-1];ot=op.get_textpage();alt=ot.get_text_range();ot.close();op.close()
                filtered=page.filter(circular_layout.visible_object)
                detected=[t for t in filtered.find_tables() if len(t.rows)>1 and len(t.columns)>1]
                plines=[];alignment=True;cursor=n['char_start']
                raw_lines=page.extract_text_lines()
                if '\n'.join(unicodedata.normalize('NFC',l['text']) for l in raw_lines)!=source:alignment=False
                if alignment:
                    for j,l in enumerate(raw_lines):
                        value=unicodedata.normalize('NFC',l['text'])
                        plines.append({'page':i,'line_index':j,'text':value,'char_start':cursor,'char_end':cursor+len(value),
                            'locator':n['locator'],'bbox':[l[k] for k in ['x0','top','x1','bottom']],
                            'bold':all('Bold' in ch['fontname'] for ch in l['chars'] if ch['text'].strip()),'chars':l['chars']})
                        cursor+=len(value)+1
                own_tables=[];cell_errors=[]
                for j,t in enumerate(detected):
                    tid=legal_tree.hashed('survey-table_',{'raw_sha256':src['measured']['sha256'],'page':i,'bbox':list(t.bbox)})
                    record={'table_id':tid,'file_id':e['file_id'],'extraction_id':e['extraction_id'],'page':i,
                        'bbox':list(t.bbox),'rows':len(t.rows),'columns':len(t.columns),'cell_text_observed':t.extract(),
                        'status':'pending_structure_review','role':src['file_role']}
                    if alignment and '\x00' not in source:
                        spec={'number':j+1,'page':i,'bbox':list(t.bbox),'detected_index':j,'rows':len(t.rows),'columns':len(t.columns)}
                        region={'number':j+1,'page':i,'context_unit_id':None,'char_start':n['char_start'],'char_end':n['char_end'],'locator':n['locator'],'extraction_id':e['extraction_id']}
                        proxy=[None]*len(nodes);proxy[i-1]=SimpleNamespace(find_tables=lambda:detected)
                        try:
                            tt,cc=pdf_layout.cell_evidence(SimpleNamespace(pages=proxy),plines,[region],[spec],rec,src['measured']['sha256'],text)
                            record.update(table_id=tt[0]['table_id'],cell_slots=tt[0]['cell_slots']);cells.extend(cc)
                        except ValueError as exc:record['cell_alignment_blocker']=str(exc);cell_errors.append(str(exc))
                    own_tables.append(record);tables.append(record)
                own_fig=[]
                for j,img in enumerate(page.images):
                    item={'file_id':e['file_id'],'extraction_id':e['extraction_id'],'page':i,'image_index':j,
                          'bbox':[img[k] for k in ['x0','top','x1','bottom']],'status':'image_content_not_interpreted','source_locator':n['locator']}
                    figures.append(item);own_fig.append(item)
                reasons=[]
                if not source.strip():reasons.append('NO_TEXT_NOT_ASSUMED_BLANK')
                if '\x00' in source:reasons.append('NUL_TEXT_DECODING_UNRESOLVED')
                if '\ufffe' in alt:reasons.append('ALTERNATE_READER_UFFFE')
                if not alignment:reasons.append('LINE_ALIGNMENT_UNRESOLVED')
                if own_tables:reasons.append('TABLE_STRUCTURE_REVIEW')
                if own_fig or page.curves:reasons.append('POSSIBLE_IMAGE_OR_VECTOR_DEPENDENCY')
                if src['file_role']=='annex':reasons.append('ANNEX_FORM_OR_DECIMAL_STRUCTURE_NOT_PARSED')
                pages.append({'file_id':e['file_id'],'extraction_id':e['extraction_id'],'file_role':src['file_role'],'page':i,
                    'locator':n['locator'],'char_start':n['char_start'],'char_end':n['char_end'],'quote_sha256':n['quote_sha256'],
                    'codepoints':len(source),'nul_count':source.count('\x00'),'pdfium_codepoints':len(alt),'pdfium_ufffe':alt.count('\ufffe'),
                    'pdfium_text_empty':not alt.strip(),'line_alignment':alignment,'tables':len(own_tables),'images':len(own_fig),'vector_curves':len(page.curves),
                    'table_cell_errors':cell_errors,'blockers':reasons,'content_review':'not_human_reviewed; automated full-page extraction only',
                    'heading_observations':[l for l in source.splitlines() if re.match(r'^(?:Điều|Phụ lục|PHỤ LỤC|Phần|CHƯƠNG|Chương)\b',l)],
                    'sign_codes_observed':sorted(set(re.findall(r'\b(?:[A-Z]{1,3}\.\d{1,3}[a-z]?|QCVN[^\n]{0,40})',source)))})
                if src['file_role']=='main':
                    if not alignment or '\x00' in source:raise ValueError('Main circular needs source correction; cannot parse')
                    lines.extend({k:v for k,v in l.items() if k!='chars'} for l in plines)
                page.close()
        other.close()
    return {'page_coverage':pages,'tables':tables,'cells':cells,'figures':figures,'main_lines':lines}


def survey_pdfium_annex(raw,rec,text,nodes):
    """Complete text/page survey; bounded object inventory, no table/figure meaning."""
    import pypdfium2 as pdfium
    from src.ingestion.extraction_normalizer import normalize_fragment
    result=[];figures=[]
    with pdfium.PdfDocument(str(raw)) as pdf:
        if len(pdf)!=len(nodes):raise ValueError('PDFium page count changed')
        for i,n in enumerate(nodes):
            page=pdf[i]
            try:
                tp=page.get_textpage()
                try:alt=tp.get_text_range()
                finally:tp.close()
                value=text[n['char_start']:n['char_end']]
                if normalize_fragment(alt)!=value:raise ValueError('PDFium source text replay mismatch')
                root_count=pdfium.raw.FPDFPage_CountObjects(page)
                measured=root_count<=10000
                counts=Counter();height=page.get_height()
                if measured:
                    for j,obj in enumerate(page.get_objects(max_depth=1)):
                        counts[obj.type]+=1
                        if obj.type==3:
                            x0,y0,x1,y1=obj.get_bounds()
                            figures.append({'file_id':rec['extraction']['file_id'],'extraction_id':rec['extraction']['extraction_id'],
                                'page':i+1,'image_index':j,'bbox':[x0,height-y1,x1,height-y0],
                                'status':'image_content_not_interpreted','source_locator':n['locator'],'geometry_method':'PDFium root objects only'})
                reasons=['ANNEX_FORM_OR_DECIMAL_STRUCTURE_NOT_PARSED','TABLE_LAYOUT_NOT_MEASURED_PDFIUM_TEXT_ONLY']
                if not value.strip():reasons.append('NO_TEXT_NOT_ASSUMED_BLANK')
                if '\ufffe' in value or '\uffff' in value or '\x00' in value:reasons.append('TEXT_DECODING_UNRESOLVED')
                if not measured:reasons.append('ROOT_OBJECT_INVENTORY_OVER_10000')
                if counts[2] or counts[3] or counts[5] or not measured:reasons.append('POSSIBLE_IMAGE_OR_VECTOR_DEPENDENCY')
                result.append({'file_id':rec['extraction']['file_id'],'extraction_id':rec['extraction']['extraction_id'],'file_role':'annex','page':i+1,
                    'locator':n['locator'],'char_start':n['char_start'],'char_end':n['char_end'],'quote_sha256':n['quote_sha256'],
                    'codepoints':len(value),'nul_count':value.count('\x00'),'pdfium_codepoints':len(alt),'pdfium_ufffe':alt.count('\ufffe'),
                    'pdfium_text_empty':not alt.strip(),'line_alignment':None,'tables':None,'images':counts[3] if measured else None,
                    'vector_curves':None,'pdfium_path_objects':counts[2] if measured else None,'pdfium_form_objects':counts[5] if measured else None,
                    'root_object_count':root_count,'object_inventory_complete':measured,'geometry_method':'PDFium root objects, max_depth=1; nested Form objects not expanded',
                    'table_cell_errors':[],'blockers':reasons,'content_review':'automated extraction only, no image recognition',
                    'heading_observations':[s for s in value.splitlines() if re.match(r'^(?:Điều|Phụ lục|PHỤ LỤC|Phần|CHƯƠNG|Chương)\b',s)],
                    'sign_codes_observed':sorted(set(re.findall(r'\b(?:[A-Z]{1,3}\.\d{1,3}[a-z]?|QCVN[^\n]{0,40})',value)))})
            finally:page.close()
    return {'pages':result,'figures':figures}


def calculate(root,tokenize=False):
    recs=rows(root/'extraction_snapshot/extractions.pending.jsonl')
    sources=rows(root/'extraction_snapshot/source_snapshot/files.pending.jsonl')
    main=next(s for s in sources if s['file_role']=='main')
    rec=next(r for r in recs if r['extraction']['file_id']==main['file_id'])
    e=rec['extraction'];text=(root/'extraction_snapshot'/e['text_ref']).read_text(encoding='utf8');trace=load(root/'extraction_snapshot'/rec['trace_ref'])
    parsed=circular_layout.parse(rec,text,trace,rows(root/'main_lines.jsonl'),[t for t in rows(root/'tables.jsonl') if t['file_id']==main['file_id']])
    check_contracts(parsed)
    doc=rows(root/'extraction_snapshot/source_snapshot/documents.pending.jsonl')[0]
    data={'document':{'law_id':doc['law_id'],'source_id':doc['source_id'],'law_title':doc['declared']['law_title'],'source_url':doc['declared']['source_url_candidate']},
        'units':parsed['units'],'spans':parsed['spans'],'issues':parsed['issues'],
        'extractions':[{**e,'text_ref':'extraction_snapshot/'+e['text_ref']}],
        'files':[{'file_id':main['file_id'],'law_id':main['law_id'],'raw_file_ref':'sources/'+Path(main['measured']['raw_file_ref']).name,
                  'sha256':main['measured']['sha256'],'size_bytes':main['measured']['size_bytes']}]}
    # Figure dependencies use actual page ranges. No text-only preview from a possible figure region.
    for p in rows(root/'page_coverage.jsonl'):
        if p['file_id']==main['file_id'] and (p['images'] or p['vector_curves'] or p['table_cell_errors']):
            data['issues'].append({'code':'UNRESOLVED_PAGE_VISUAL_OR_CELL_DEPENDENCY','law_id':main['law_id'],
                'extraction_id':e['extraction_id'],'char_start':p['char_start'],'char_end':p['char_end'],'locator':p['locator'],'status':'pending'})
    ec=load(root/'encoder_config.json')
    if tokenize:encode=lambda texts:encoder_input.encode_inputs(texts,ec,root/'tokenizer_assets')['rows']
    else:
        encoded={r['input_sha256']:r for r in rows(root/'encoder_inputs.jsonl')}
        encode=lambda texts:[encoded[digest(t.encode())] for t in texts]
    combined={k:[] for k in ['chunks','contexts','quarantined','issues','encoder_inputs','unit_results','dependency_checks']}
    blockers=BLOCKERS+(['SPARSE_PART_CHAPTER_PROJECTION_PENDING'] if parsed['structure'] else [])
    leaves=[u for u in data['units'] if u['unit_type'] in {'article','clause','point'} and not any(x['parent_unit_id']==u['unit_id'] for x in data['units'])]
    for is_article in [False,True]:
        builder=chunk_preview_articles if is_article else chunk_preview_v2
        cfg={'chunk_policy_version':builder.VERSION,'snapshot_date':SNAPSHOT_DATE,'token_limit':256,'required_context_fields':['title'],
             'required_clause_context_fields':['text_original'],'target_unit_ids':[u['unit_id'] for u in leaves if (u['unit_type']=='article')==is_article]}
        result=builder.build_chunks(data,root,cfg,blockers,encode)
        for k in combined:combined[k].extend(result[k])
    for k in combined:combined[k].sort(key=canonical)
    scope=[];applicability=[]
    scope_config=load(root/'scope_config.json')
    if scope_config['snapshot_date']!=SNAPSHOT_DATE or scope_config['policy_version']!='circular-scope-proposals.v1':raise ValueError('Scope config mismatch')
    selected={s['unit_id']:s for s in scope_config['selections']}
    for s in selected.values():
        if s['origin']!='agent_review' or s['status']!='proposed' or s['reviewer_ref'] is not None or s['scope_proposal'] not in {'pending','included','supporting','excluded'}:raise ValueError('Not an agent scope proposal')
    for u in data['units']:
        # Nothing is auto-promoted by article membership; unreviewed units remain pending.
        scope.append({'unit_id':u['unit_id'],'unit_sha256':digest(canonical(u).encode()),'scope_proposal':'pending',
            'reason':'Full source preserved; unit-specific business-object review not yet recorded','origin':'agent_review','status':'proposed','reviewer_ref':None})
        if u['unit_id'] in selected:
            decision=selected[u['unit_id']]
            if decision['unit_sha256']!=digest(canonical(u).encode()):raise ValueError('Scope proposal binding changed')
            scope[-1]=decision
        elif u['law_id']=='51/2024/TT-BGTVT' and u['unit_type']!='document':
            scope[-1].update(scope_proposal='supporting',reason='BRD UC-02: văn bản ban hành nối QCVN và căn cứ thi hành; chưa phải quy tắc người lái, chưa xác nhận applicability.')
        if 'hiệu lực thi hành' in u['text_original'] and '2025' in u['text_original']:
            applicability.append({'unit_id':u['unit_id'],'text_observed':u['text_original'],'source_span_ids':[s['span_id'] for s in data['spans'] if s['unit_id']==u['unit_id']],
                'origin':'agent_review','status':'observed_not_applicability_decision','snapshot_date':SNAPSHOT_DATE,'amendment_history':'pending'})
    unprocessed=[{k:p[k] for k in ['file_id','extraction_id','page','locator','char_start','char_end','quote_sha256','blockers']}
                 for p in rows(root/'page_coverage.jsonl') if p['file_role']=='annex']
    regions=[]
    for p in unprocessed:
        selection=next((s for s in scope_config.get('region_selections',[]) if (s['file_id'],s['page'])==(p['file_id'],p['page'])),None)
        if selection:
            if any(selection[k]!=p[k] for k in ['extraction_id','char_start','char_end','quote_sha256','locator']):raise ValueError('Region scope binding mismatch')
            regions.append(selection)
        else:regions.append({**p,'scope_proposal':'pending','status':'proposed','origin':'agent_review','reviewer_ref':None,
                             'reason':'Annex is not excluded by file role; content/layout review pending.'})
    exports={'legal_units.pending':data['units'],'source_spans.pending':data['spans'],'parser_issues':data['issues'],
        'main_coverage':parsed['coverage'],'structure.pending':parsed['structure'],'scope.proposals':scope,'applicability.observed':applicability,
        'unit_structure_dependencies':structure_dependencies(parsed),
        'unprocessed_regions':unprocessed,
        'region_scope.proposals':regions,
        **{name:combined[k] for name,k in [('chunks.preview','chunks'),('contexts.preview','contexts'),('chunks.quarantine','quarantined'),('encoder_inputs','encoder_inputs'),
          ('chunk_issues','issues'),('unit_results','unit_results'),('dependency_checks','dependency_checks')]}}
    return exports


def summary(root,exports):
    pages=rows(root/'page_coverage.jsonl');enc=exports['encoder_inputs']
    return {'files':len({p['file_id'] for p in pages}),'pages':len(pages),'pages_by_role':dict(Counter(p['file_role'] for p in pages)),
        'pages_with_nul':sum(p['nul_count']>0 for p in pages),'nul_total':sum(p['nul_count'] for p in pages),
        'empty_text_pages':sum(p['codepoints']==0 for p in pages),'pdfium_empty_pages':sum(p['pdfium_text_empty'] for p in pages),
        'pages_with_images':sum((p['images'] or 0)>0 for p in pages),'pages_with_vector_curves':sum((p['vector_curves'] or 0)>0 or (p.get('pdfium_path_objects') or 0)>0 for p in pages),
        'pages_table_layout_unknown':sum(p['tables'] is None for p in pages),
        'pages_object_inventory_incomplete':sum(p.get('object_inventory_complete') is False or bool(p.get('pdfium_form_objects')) for p in pages),
        'tables_pending':len(rows(root/'tables.jsonl')),'cells':len(rows(root/'cells.jsonl')),'image_objects':len(rows(root/'figures.jsonl')),
        'units':dict(Counter(u['unit_type'] for u in exports['legal_units.pending'])),'spans':len(exports['source_spans.pending']),
        'scope_proposals':dict(Counter(p['scope_proposal'] for p in exports['scope.proposals'])),
        'preview_scope':dict(Counter(next(p['scope_proposal'] for p in exports['scope.proposals'] if p['unit_id']==c['unit_id']) for c in exports['chunks.preview'])),
        'unprocessed_annex_pages':len(exports['unprocessed_regions']),
        'region_scope_proposals':dict(Counter(p['scope_proposal'] for p in exports['region_scope.proposals'])),
        'main_coverage_codepoints':dict(Counter({cat:sum(c['char_end']-c['char_start'] for c in exports['main_coverage'] if c['category']==cat) for cat in {c['category'] for c in exports['main_coverage']}})),
        'candidates':len(exports['unit_results']),'chunks':len(exports['chunks.preview']),'contexts':len(exports['contexts.preview']),
        'quarantine_over_budget':len(exports['chunks.quarantine']),'blocked':dict(Counter(q['code'] for q in exports['chunk_issues'])),
        'tokens_min':min((x['tokens_with_special'] for x in enc),default=None),'tokens_max':max((x['tokens_with_special'] for x in enc),default=None),
        'unknown':sum(x['unknown_tokens'] for x in enc),'release_eligible':False}


def render(root,exports,counts):
    lines=['# Circular ingestion — pending technical preview',canonical(counts),
        'Automated extraction covers every page. No claim of full content/visual/human review. Sparse article tree: real Parts/Chapters retained in structure.pending; no fabricated DDD level.',
        '| File | Page | Text codepoints | NUL | Tables | Images/curves | Blockers |','|---|---:|---:|---:|---:|---|---|']
    for p in rows(root/'page_coverage.jsonl'):lines.append(f"| {p['file_id']} | {p['page']} | {p['codepoints']} | {p['nul_count']} | {p['tables']} | {p['images']}/{p['vector_curves']} | {', '.join(p['blockers'])} |")
    lines.extend(['## Scope proposals (agent, không phải reviewer decisions)',
                  '| Citation | Proposal | Lý do |','|---|---|---|'])
    by={u['unit_id']:u for u in exports['legal_units.pending']}
    for s in exports['scope.proposals']:
        if s['scope_proposal']!='pending':lines.append(f"| {by[s['unit_id']]['citation_path']} | {s['scope_proposal']} | {s['reason']} |")
    for u in exports['legal_units.pending']:lines.extend(['## '+u['citation_path'],u['title'],u['text_original']])
    for c in exports['chunks.preview']:lines.extend(['## Preview '+c['citation_path'],c['chunk_id'],c['context_text'] or '',c['text_original'],'Search:',c['text_for_search']])
    return '\n\n'.join(lines)+'\n'


def validate(path):
    root=Path(path).resolve().parent;m=check_files(root/'manifest.json')
    if (m['manifest_type']!=VERSION or m['code_sha256']!={p:digest((BASE_DIR/p).read_bytes()) for p in CODE}
        or m['files']!=inventory(root) or m['release_eligible'] is not False or m['snapshot_date']!=SNAPSHOT_DATE
        or m['origin']!='agent_review' or m['human_reviewer_events']!=0 or m['corpus_version'] is not None):raise ValueError('Circular binding mismatch')
    check_files(root/'extraction_snapshot/manifest.json')
    for source in rows(root/'extraction_snapshot/source_snapshot/files.pending.jsonl'):
        raw=root/'sources'/Path(source['measured']['raw_file_ref']).name
        if digest(raw.read_bytes())!=source['measured']['sha256']:raise ValueError('Raw binding mismatch')
    records=rows(root/'extraction_snapshot/extractions.pending.jsonl'); texts={};page_nodes={}
    for rec in records:
        e=rec['extraction'];text=(root/'extraction_snapshot'/e['text_ref']).read_text(encoding='utf8')
        trace=load(root/'extraction_snapshot'/rec['trace_ref'])
        texts[e['extraction_id']]=text
        if len(text)!=e['char_count'] or digest(text.encode())!=e['text_sha256']:raise ValueError('Text binding mismatch')
        ns=[n for n in trace['nodes'] if n['kind']=='page'];ps=[p for p in rows(root/'page_coverage.jsonl') if p['extraction_id']==e['extraction_id']]
        if len(ps)!=len(ns):raise ValueError('Missing page coverage')
        for p,n in zip(ps,ns):
            if any(p[k]!=n[k] for k in ['char_start','char_end','quote_sha256','locator']):raise ValueError('Page locator mismatch')
            page_nodes[(e['extraction_id'],p['page'])]=n
            value=text[n['char_start']:n['char_end']]
            if p['codepoints']!=len(value) or p['nul_count']!=value.count('\x00'):raise ValueError('Page diagnostics mismatch')
    for c in rows(root/'cells.jsonl'):
        if c['cell_id']!=legal_tree.hashed('pdf-cell_',{k:v for k,v in c.items() if k!='cell_id'}):raise ValueError('Cell identity mismatch')
        text=texts[c['extraction_id']];node=page_nodes[(c['extraction_id'],c['page'])]
        for s in c['source_slices']:
            a,b=s['char_start'],s['char_end']
            if not node['char_start']<=a<b<=node['char_end'] or text[a:b]!=s['quote'] or digest(s['quote'].encode())!=s['quote_sha256'] or s['locator']!=node['locator']:raise ValueError('Cell source slice mismatch')
        if c['text']!='\n'.join(s['quote'] for s in c['source_slices']):raise ValueError('Cell text roundtrip mismatch')
    main_rec=next(r for r in records if r['extraction']['file_id']==next(s['file_id'] for s in rows(root/'extraction_snapshot/source_snapshot/files.pending.jsonl') if s['file_role']=='main'))
    for line in rows(root/'main_lines.jsonl'):
        eid=main_rec['extraction']['extraction_id'];node=page_nodes[(eid,line['page'])]
        if texts[eid][line['char_start']:line['char_end']]!=line['text'] or line['locator']!=node['locator']:raise ValueError('Layout source slice mismatch')
    encoder_input.require_config(load(root/'encoder_config.json'),root/'tokenizer_assets')
    for x in rows(root/'encoder_inputs.jsonl'):
        if (x['truncation'] is not False or x['tokens_with_special']!=len(x['after']['token_ids']) or x['after']['token_ids_sha256']!=digest(canonical(x['after']['token_ids']).encode())
            or x['model_max_tokens']!=256 or x['unknown_tokens']!=x['after']['token_ids'].count(3)):raise ValueError('Encoder measurement invalid')
    expected=calculate(root)
    for key,value in expected.items():
        if rows(root/(key+'.jsonl'))!=value:raise ValueError('Circular replay mismatch: '+key)
    counts=summary(root,expected)
    if counts!=m['counts'] or (root/'review.md').read_text(encoding='utf8')!=render(root,expected,counts):raise ValueError('Circular report mismatch')
    return {'technical_valid':True,**counts}


def build(extraction_manifest,run_dir,survey_manifest=None):
    source=Path(extraction_manifest).resolve();m=check_files(source)
    report=load(source.parent/'validation_report.json')
    if m['manifest_type']=='circular-pdfium-extraction.v1':
        from src.ingestion.circular_reader import validate as validate_reader
        validate_reader(source)  # Partial annex retained; only clean main is passed to grammar.
        sources=rows(source.parent/'source_snapshot/files.pending.jsonl');records=rows(source.parent/'extractions.pending.jsonl')
        main_id=next(s['file_id'] for s in sources if s['file_role']=='main')
        if next(r['technical_status'] for r in records if r['extraction']['file_id']==main_id)!='complete':raise ValueError('Main circular reader not complete')
    elif m['manifest_type']!='pending_extraction' or not report['technical_valid'] or not report['processing_success']:raise ValueError('Stage3 must pass first')
    root=staging_path(run_dir);root.mkdir(parents=True);shutil.copytree(source.parent,root/'extraction_snapshot');(root/'sources').mkdir()
    for s in rows(root/'extraction_snapshot/source_snapshot/files.pending.jsonl'):
        raw=BASE_DIR/s['measured']['raw_file_ref']
        if digest(raw.read_bytes())!=s['measured']['sha256']:raise ValueError('Raw changed')
        shutil.copyfile(raw,root/'sources'/raw.name)
    baseline=BASE_DIR/'staging/tt38-preview-003'
    shutil.copyfile(baseline/'encoder_config.json',root/'encoder_config.json');shutil.copytree(baseline/'tokenizer_assets',root/'tokenizer_assets')
    shutil.copyfile(BASE_DIR/'config/circular_scope.proposed.v1.json',root/'scope_config.json')
    if survey_manifest:
        previous=Path(survey_manifest).resolve();check_files(previous)
        if (previous.parent/'extraction_snapshot/manifest.json').read_bytes()!=(root/'extraction_snapshot/manifest.json').read_bytes():raise ValueError('Survey reuse requires identical extraction manifest')
        measured={name:rows(previous.parent/(name+'.jsonl')) for name in ['page_coverage','tables','cells','figures','main_lines']}
    else:measured=survey(root)
    for name,value in measured.items():write_rows(root/(name+'.jsonl'),value)
    exports=calculate(root,tokenize=True)
    for name,value in exports.items():write_rows(root/(name+'.jsonl'),value)
    counts=summary(root,exports);(root/'review.md').write_text(render(root,exports,counts),encoding='utf8')
    write_json(root/'validation_report.json',{'technical_valid':True,'counts':counts,'legal_verification':False})
    seal(root,{'manifest_type':VERSION,'built_at':now(),'snapshot_date':SNAPSHOT_DATE,'origin':'agent_review','human_reviewer_events':0,
               'release_eligible':False,'corpus_version':None,'counts':counts,'code_sha256':{p:digest((BASE_DIR/p).read_bytes()) for p in CODE}})
    return validate(root/'manifest.json')
