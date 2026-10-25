"""Resumable page evidence for seven-source completion; old reader artifacts stay immutable."""
from pathlib import Path
import importlib.metadata
import json
import re
import unicodedata
from types import SimpleNamespace

from src.assessment_evidence import now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import canonical, digest, file_identity, require_contract
from src.ingestion import extractors, extraction_normalizer, pdf_layout, circular_layout

VERSION = 'page-evidence.v1'
NAMESPACE = '6a36999d-9a98-4a12-aed9-fdbea516e54e'


def hashed(value):
    return digest(canonical(value).encode('utf8'))


def page_binding(raw_sha, page):
    return {'policy': VERSION, 'raw_sha256': raw_sha, 'pdf_page': page,
            'pdfplumber': importlib.metadata.version('pdfplumber'),
            'pdfminer.six': importlib.metadata.version('pdfminer.six'),
            'code_sha256': digest(Path(__file__).read_bytes())}


def inspect_page(page, file, ordinal):
    """Keep reader text, normalized text, measured geometry and exact cell slices."""
    raw = page.extract_text() or ''
    text = extraction_normalizer.normalize_fragment(raw)
    raw_lines = page.extract_text_lines()
    aligned = '\n'.join(extraction_normalizer.normalize_fragment(l['text']) for l in raw_lines) == text
    locator = {'format': 'pdf', 'page_start': ordinal, 'page_end': ordinal,
               'width': page.width, 'height': page.height}
    lines = []
    if aligned:
        cursor = 0
        for i, line in enumerate(raw_lines):
            value = extraction_normalizer.normalize_fragment(line['text'])
            lines.append({'page': ordinal, 'line_index': i, 'text': value,
                          'char_start': cursor, 'char_end': cursor+len(value),
                          'offset_space': 'page_normalized_unicode_codepoints', 'locator': locator,
                          'bbox': [line[k] for k in ['x0', 'top', 'x1', 'bottom']],
                          'bold': all('Bold' in ch['fontname'] for ch in line['chars'] if ch['text'].strip()),
                          'chars': line['chars']})
            cursor += len(value)+1
    bad = {f'U+{ord(c):04X}': text.count(c) for c in ['\x00', '\ufffe', '\uffff'] if c in text}
    filtered = page.filter(circular_layout.visible_object)
    dense = len(page.curves)+len(page.edges) > 10000
    detected = [] if dense else [t for t in filtered.find_tables() if len(t.rows)>1 and len(t.columns)>1]
    tables, cells, issues = [], [], []
    for i, table in enumerate(detected):
        bbox = list(table.bbox)
        tid = 'layout-table_'+hashed({'sha256': file['sha256'], 'page': ordinal, 'bbox': bbox})
        t = {'table_id': tid, 'page': ordinal, 'bbox': bbox, 'observed_cell_text': table.extract(),
             'rows': len(table.rows), 'columns': len(table.columns), 'cell_slots': [],
             'status': 'physical_structure_not_semantic_header_review'}
        if aligned and not bad:
            spec = {'number': i+1, 'page': ordinal, 'bbox': bbox, 'detected_index': i,
                    'rows': len(table.rows), 'columns': len(table.columns)}
            proxy = [None]*ordinal
            proxy[-1] = SimpleNamespace(find_tables=lambda: detected)
            region = {'number': i+1, 'char_start': 0, 'char_end': len(text), 'context_unit_id': None,
                      'locator': locator, 'extraction_id': 'page-local-not-extraction'}
            try:
                tt, cc = pdf_layout.cell_evidence(SimpleNamespace(pages=proxy), lines, [region], [spec],
                                                   {'extraction': {'extraction_id': 'page-local-not-extraction'}}, file['sha256'], text)
                # These are explicitly page-local evidence; final extraction bindings are made after serialization.
                t.update(table_id=tt[0]['table_id'], cell_slots=tt[0]['cell_slots'])
                for cell in cc:
                    cell['offset_space'] = 'page_normalized_unicode_codepoints'
                cells.extend(cc)
            except ValueError as e:
                t['blocker'] = str(e)
        else:
            t['blocker'] = 'PAGE_TEXT_ALIGNMENT_OR_DECODING'
        tables.append(t)
    if dense: issues.append('VECTOR_DENSE_TABLE_DETECTION_PENDING')
    if bad: issues.append('READER_NONCHARACTERS_PRESERVED')
    if not text.strip(): issues.append('NO_TEXT_NOT_BLANK_DECISION')
    if not aligned: issues.append('LINE_ALIGNMENT_PENDING')
    images = [{'image_index': i, 'bbox': [v[k] for k in ['x0', 'top', 'x1', 'bottom']],
               'status': 'image_not_interpreted'} for i,v in enumerate(page.images)]
    figures = [{'bbox': [v[k] for k in ['x0', 'top', 'x1', 'bottom']],
                'object_type': v['object_type']} for v in page.curves]
    return {'binding': page_binding(file['sha256'], ordinal), 'file_id': file['file_id'],
            'law_id': file['law_id'], 'locator': locator, 'reader_text': raw,
            'normalized_text': text, 'text_sha256': digest(text.encode('utf8')), 'char_count': len(text),
            'line_alignment': aligned, 'lines': [{k:v for k,v in l.items() if k!='chars'} for l in lines],
            'tables': tables, 'cells': cells, 'images': images, 'vector_objects': figures,
            'noncharacters': bad, 'blockers': issues, 'rendered_is_reviewed': False,
            'content_review': 'not_human_reviewed; reader_and_layout_measurement_only',
            'origin': 'agent_review', 'review_status': 'pending', 'created_at': now()}


def validate_page(value, file, page):
    if (value['binding'] != page_binding(file['sha256'], page)
            or value['file_id'] != file['file_id'] or value['law_id'] != file['law_id']):
        raise ValueError('Resume page source/config/code binding mismatch')
    text = value['normalized_text']
    if (text != extraction_normalizer.normalize_fragment(value['reader_text'])
            or digest(text.encode()) != value['text_sha256'] or len(text)!=value['char_count']):
        raise ValueError('Page normalization/hash mismatch')
    for line in value['lines']:
        if text[line['char_start']:line['char_end']] != line['text']:
            raise ValueError('Page line slice mismatch')
    for cell in value['cells']:
        for s in cell['source_slices']:
            q=text[s['char_start']:s['char_end']]
            if q!=s['quote'] or digest(q.encode())!=s['quote_sha256']:
                raise ValueError('Cell/header source slice mismatch')
        if '\n'.join(s['quote'] for s in cell['source_slices'])!=cell['text']:
            raise ValueError('Cell text roundtrip mismatch')


def scan_pdf(file, run_root, *, resume=False, stop_after=None):
    """One page at a time; checkpoint contains checksum of every completed page."""
    import pdfplumber
    raw_path=Path(file['local_ref'])
    if digest(raw_path.read_bytes())!=file['sha256']:raise ValueError('PDF source checksum changed')
    folder=Path(run_root)/file['file_id'];folder.mkdir(parents=True,exist_ok=resume)
    cp=folder/'checkpoint.json'
    checkpoint=load(cp) if cp.exists() else {'file_id':file['file_id'],'raw_sha256':file['sha256'],'pages':{},'state':'IN_PROGRESS'}
    if checkpoint['file_id']!=file['file_id'] or checkpoint['raw_sha256']!=file['sha256']:
        raise ValueError('Checkpoint source mismatch')
    done=0
    with pdfplumber.open(raw_path) as pdf:
        checkpoint['total_pages']=len(pdf.pages)
        for n,page in enumerate(pdf.pages,1):
            dest=folder/f'page-{n:04d}.json'
            if dest.exists():
                if not resume:raise ValueError('Page exists; require explicit --resume')
                if checkpoint['pages'].get(str(n))!=digest(dest.read_bytes()):raise ValueError('Incomplete/tampered page checkpoint')
                validate_page(load(dest),file,n)
            else:
                value=inspect_page(page,file,n);validate_page(value,file,n);write_json(dest,value)
                checkpoint['pages'][str(n)]=digest(dest.read_bytes());checkpoint['updated_at']=now();write_json(cp,checkpoint)
            page.close()
            done+=1
            if stop_after and done>=stop_after:return checkpoint
            if n%10==0:print(f"{file['file_id']} {n}/{len(pdf.pages)}",flush=True)
    checkpoint.update(state='READER_COMPLETED_NOT_CONTENT_VERIFIED',updated_at=now());write_json(cp,checkpoint)
    return checkpoint


def extraction_from_pages(file, cache, destination):
    folder=Path(cache)/file['file_id'];cp=load(folder/'checkpoint.json')
    if cp['state']!='READER_COMPLETED_NOT_CONTENT_VERIFIED':raise ValueError('Cannot serialize incomplete page extraction')
    pages=[load(folder/f'page-{i:04d}.json') for i in range(1,cp['total_pages']+1)]
    for i,p in enumerate(pages,1):validate_page(p,file,i)
    text,trace=extraction_normalizer.serialize(extractors.node('document',{'format':'pdf'},children=[
        extractors.node('page',p['locator'],raw_text=p['reader_text']) for p in pages],separator='\n'))
    tool=canonical({'reader':VERSION,'pdfplumber':importlib.metadata.version('pdfplumber'),
                    'pdfminer.six':importlib.metadata.version('pdfminer.six'),
                    'code_sha256':digest(Path(__file__).read_bytes())})
    config={'normalization':'NFC_LF_ONLY','page_separator':'LF','ocr':False,'repair':False}
    payload={'identity_schema':'extraction.v1','file_id':file['file_id'],'source_raw_sha256':file['sha256'],
             'method':'pdf_text','tool_version':tool,'config_sha256':hashed(config),
             'text_sha256':digest(text.encode()),'trace_content_sha256':hashed(trace)}
    eid='e_'+hashed(payload)
    for n in trace['nodes']:
        n.update(extraction_id=eid,locator_id='l_'+hashed({'extraction_id':eid,'node_index':n['node_index'],'locator':n['locator']}))
        n['parent_locator_id']=None if n['parent_index'] is None else trace['nodes'][n['parent_index']]['locator_id']
    e={'extraction_id':eid,'file_id':file['file_id'],'method':'pdf_text','tool_version':tool,
       'text_ref':f'extractions/{eid}/normalized.txt','text_sha256':payload['text_sha256'],
       'char_count':len(text),'review_status':'pending','created_at':now()}
    require_contract('extraction',e)
    out=Path(destination)/'extractions'/eid;out.mkdir(parents=True)
    (out/'normalized.txt').write_bytes(text.encode());write_json(out/'trace.json',trace)
    write_json(out/'identity.json',payload)
    return {'extraction':e,'law_id':file['law_id'],'trace_ref':f'extractions/{eid}/trace.json',
            'trace_sha256':digest((out/'trace.json').read_bytes()),'source_raw_sha256':file['sha256'],
            'technical_status':'partial' if any(p['blockers'] for p in pages) else 'reader_complete',
            'source_status':'pending','config_sha256':payload['config_sha256']}


def gazette_files(cfg):
    root=Path(cfg['new_source_receipt_root']);profile=cfg['gazette_profile'];output=[]
    for i in range(1,profile['parts']+1):
        p=root/f"{profile['pdf_prefix']}{i:02d}.pdf";receipt=load(p.with_suffix('.receipt.json'))
        raw=p.read_bytes()
        if receipt['sha256']!=digest(raw) or receipt['bytes']!=len(raw):raise ValueError('New capture receipt mismatch')
        output.append({'file_id':file_identity(NAMESPACE,profile['law_id'],digest(raw)),
            'source_id':profile['source_id'],'law_id':profile['law_id'],'source_set':profile['source_set'],
            'file_role':'main' if i==1 else 'part','part_order':i,'local_ref':p.as_posix(),
            'mime_type':'application/pdf','sha256':digest(raw),'size_bytes':len(raw),
            'official_page_url':profile['official_page_url'],'download_url':receipt['url'],
            'retrieved_at':receipt['accessed_at'],'retrieved_at_basis':'actual_new_capture',
            'status':'pending','edition_status':'pending_agent_comparison','evidence_ref':p.with_suffix('.receipt.json').as_posix(),
            'relationship':'gazette_serial_parts; alternate_source_set_not_appended_to_403_page_pdf'})
    return output
