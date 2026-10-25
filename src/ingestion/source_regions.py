"""Measured PDF regions and annexes, separate from DDD legal-unit hierarchies."""
from pathlib import Path
import copy
import re
from src.experimental_dataset import load, rows, write_json, write_rows
from src.assessment_evidence import check_files, now, seal
from src.source_contracts import canonical, digest

VERSION = 'source-regions.v1'


def identity(value):
    return 'rg_' + digest(canonical(value).encode())


def proof(extraction, page_node, a, b, text, bbox=None):
    if not 0 <= a < b <= page_node['char_end']-page_node['char_start']:
        raise ValueError('Region outside source page')
    start = page_node['char_start']+a
    end = page_node['char_start']+b
    return {'extraction_id': extraction['extraction_id'], 'file_id': extraction['file_id'],
            'locator': page_node['locator'], 'bbox_pdf_top_origin': bbox,
            'char_start': start, 'char_end': end, 'quote': text[start:end],
            'quote_sha256': digest(text[start:end].encode()),
            'offset_space': 'normalized_extraction_unicode_codepoints'}


def validate_proof(p, text):
    a,b=p['char_start'],p['char_end']
    if (not 0<=a<b<=len(text) or text[a:b]!=p['quote']
            or digest(p['quote'].encode())!=p['quote_sha256']
            or p['offset_space']!='normalized_extraction_unicode_codepoints'):
        raise ValueError('Region source roundtrip/hash mismatch')


def physical_regions(source):
    """Rebind page-cache offsets to real Stage3 extractions; retain physical cells."""
    source=Path(source);check_files(source/'manifest.json')
    files=rows(source/'files.pending.jsonl');records=rows(source/'extractions.pending.jsonl')
    regions=[];pages=[];tables=[];cells=[];annexes=[]
    for f in files:
        rec=next(r for r in records if r['extraction']['file_id']==f['file_id']);e=rec['extraction']
        text=(source/e['text_ref']).read_text(encoding='utf8');trace=load(source/rec['trace_ref'])
        page_nodes=[n for n in trace['nodes'] if n['kind']=='page'];starts=[]
        for n in page_nodes:
            page=n['locator']['page_start'];cache=load(source/'pages'/f['file_id']/f'page-{page:04d}.json')
            if text[n['char_start']:n['char_end']]!=cache['normalized_text']:
                raise ValueError('Page/extraction binding mismatch')
            ps=[]
            for line in cache['lines']:
                p=proof(e,n,line['char_start'],line['char_end'],text,line['bbox']);validate_proof(p,text)
                rid=identity({'policy':VERSION,'kind':'line','proof':p})
                regions.append({'region_id':rid,'kind':'line','law_id':f['law_id'],
                    'source_proof':p,'content':line['text'],'bold':line['bold'],
                    'scope_proposal':'pending','applicability':'pending_review','review_status':'pending'})
                ps.append(rid)
                marker=re.fullmatch(r'Phụ lục\s+([IVXLCDM]+)',line['text'].strip())
                if f['file_role']=='annex' and marker:starts.append((page,marker.group(1),rid))
            mapping={}
            for c in cache['cells']:
                item=copy.deepcopy(c);ss=[]
                for s in c['source_slices']:
                    pp=proof(e,n,s['char_start'],s['char_end'],text)
                    validate_proof(pp,text);ss.append(pp)
                item.update(extraction_id=e['extraction_id'],source_slices=ss,
                            offset_space='normalized_extraction_unicode_codepoints',
                            source_raw_sha256=f['sha256'],file_id=f['file_id'])
                # Physical identity is versioned here; never masquerades as a legal unit.
                item['cell_id']=identity({'policy':VERSION,'kind':'cell','source':ss,
                                         'bbox':item['bbox'],'raw_sha256':f['sha256']})
                mapping[c['cell_id']]=item['cell_id'];cells.append(item)
            for t in cache['tables']:
                item=copy.deepcopy(t)
                item.update(file_id=f['file_id'],extraction_id=e['extraction_id'],source_raw_sha256=f['sha256'])
                item['cell_slots']=[[mapping[s] if s is not None else None for s in row] for row in t['cell_slots']]
                item['required_capability']='physical-cell-source-read.v1';tables.append(item)
            pages.append({'file_id':f['file_id'],'law_id':f['law_id'],'pdf_page':page,
                'extraction_id':e['extraction_id'],'char_start':n['char_start'],'char_end':n['char_end'],
                'source_raw_sha256':f['sha256'],'reader_char_count':len(cache['normalized_text']),
                'line_regions':ps,'tables':len(cache['tables']),'cells':len(cache['cells']),
                'images':cache['images'],'vector_object_count':len(cache['vector_objects']),
                'blockers':cache['blockers'],
                'disposition':'reader_layout_measured_semantics_pending' if cache['normalized_text'].strip() else 'no_text_not_blank_decision',
                'image_review':'pending' if cache['images'] else 'no_embedded_images_detected_not_a_visual_review',
                'scope_proposal':'pending','applicability':'pending_review','human_review':None})
        for i,(page,marker,rid) in enumerate(starts):
            end=starts[i+1][0]-1 if i+1<len(starts) else len(page_nodes)
            group=[p for p in pages if p['file_id']==f['file_id'] and page<=p['pdf_page']<=end]
            annexes.append({'annex_id':identity({'policy':VERSION,'file_id':f['file_id'],'marker':marker,'page':page}),
                'file_id':f['file_id'],'law_id':f['law_id'],'literal_marker':marker,'page_start':page,'page_end':end,
                'heading_region_id':rid,'line_region_ids':[x for p in group for x in p['line_regions']],
                'table_ids':[t['table_id'] for t in tables if t['file_id']==f['file_id'] and page<=t['page']<=end],
                'scope_proposal':'pending','reason':'Annex retained; requires object/use-case review; not implicitly excluded',
                'applicability':'pending_review'})
    return files,records,pages,regions,tables,cells,annexes


def build(source,run_dir):
    root=Path(run_dir);root.mkdir(parents=True)
    files,records,pages,regions,tables,cells,annexes=physical_regions(source)
    for name,value in [('pages',pages),('regions',regions),('tables',tables),('cells',cells),('annexes',annexes)]:
        write_rows(root/(name+'.jsonl'),value)
    write_json(root/'input_binding.json',{'manifest_ref':Path(source,'manifest.json').as_posix(),
        'sha256':digest(Path(source,'manifest.json').read_bytes())})
    report={'files':len(files),'pages':len(pages),'line_regions':len(regions),'tables':len(tables),'cells':len(cells),
        'annex_groups':len(annexes),'images':sum(len(p['images']) for p in pages),
        'pages_with_blockers':sum(bool(p['blockers']) for p in pages),
        'target_eligibility':'not_implied_by_physical_representation','legal_review':'pending'}
    write_json(root/'validation_report.json',report)
    seal(root,{'manifest_type':VERSION,'built_at':now(),'origin':'agent_review','release_eligible':False,
        'source_manifest_sha256':digest(Path(source,'manifest.json').read_bytes()),
        'code_sha256':digest(Path(__file__).read_bytes())})
    return report
