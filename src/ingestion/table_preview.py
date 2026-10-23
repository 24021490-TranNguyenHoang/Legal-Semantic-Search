"""Source-cell backed TT38 table previews; no synthetic legal units or DDD rows."""
from pathlib import Path
import shutil
from src import encoder_input
from src.assessment_evidence import check_files, inventory, now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest
from src.chunk_preview import source_proof

VERSION = "tt38-cell-row-preview.v1"


def candidates(base):
    from src.tt38_preview import derive_rows
    cfg = load(base/'config.json')
    units, spans = rows(base/'legal_units.pending.jsonl'), rows(base/'source_spans.pending.jsonl')
    tables, cells = rows(base/'tables.jsonl'), rows(base/'cells.jsonl')
    by = {u['unit_id']:u for u in units}; cb = {c['cell_id']:c for c in cells}
    rec = rows(base/'extraction_snapshot/extractions.pending.jsonl')[0]
    e = {**rec['extraction'], 'text_ref':'extraction_snapshot/'+rec['extraction']['text_ref']}
    data = {'spans':spans,'extractions':[e],'files':[{'file_id':e['file_id'],'law_id':cfg['law_id'],
        'raw_file_ref':'sources/selected.pdf','sha256':cfg['raw_sha256'],'size_bytes':(base/'sources/selected.pdf').stat().st_size}]}
    derived = derive_rows(tables,cells,units)
    result=[]
    def context(u, extra=None):
        parents=[];p=by.get(u['parent_unit_id'])
        while p:
            if p['unit_type'] in {'article','clause'}:parents.insert(0,p)
            p=by.get(p['parent_unit_id'])
        if extra:parents.append(extra)
        return [{'unit_id':p['unit_id'],'field_name':f,'char_start':0,'char_end':len(p[f]),
                 'text_original':p[f],'source_locator':source_proof(data,base,p,f,'base/')}
                for p in parents for f in ['title','text_original'] if p[f]]
    def make(u,selected,dependency=None):
        contexts=context(u,dependency)
        linked=sorted({c for r in selected for c in r['source_cell_ids']})
        body='\n\n'.join(r['text_derived'] for r in selected)
        # Own source prose includes text before AND after table. It is never rewritten.
        search='\n\n'.join([cfg['law_title'],u['citation_path'],*[c['text_original'] for c in contexts],u['text_original'],body])
        payload={'policy_version':VERSION,'unit_id':u['unit_id'],'citation_path':u['citation_path'],
            'text_original':u['text_original'],'own_source_locator':source_proof(data,base,u,'text_original','base/'),
            'contexts':contexts,'table_rows':selected,'source_cells':[cb[c] for c in linked],
            'text_derived':body,'text_for_search':search,'content_sha256':digest(search.encode()),
            'explicit_dependency_unit_id':dependency['unit_id'] if dependency else None,
            'representation':'derived_table_preview_not_DDD_chunk','origin':'agent_review','scope_proposal':'included',
            'scope_reason':'BRD UC-02: tốc độ/khoảng cách trực tiếp cho người điều khiển; proposal only',
            'applicability':'pending_review','snapshot_date':'2025-01-01','release_eligible':False,'corpus_version':None}
        payload['preview_id']='tp_'+digest(canonical(payload).encode())
        result.append(payload)
    for r in derived:
        # Regenerate labels from measured cells; never reuse quarantine state as a decision.
        selected={k:v for k,v in r.items() if k not in {'status','not_a_chunk'}}
        make(by[r['owner_unit_id']],[selected])
    b=next(u for u in units if u['canonical_path'].endswith('article:11/clause:2/point:b'))
    a=next(u for u in units if u['canonical_path'].endswith('article:11/clause:2/point:a'))
    make(b,[{k:v for k,v in r.items() if k not in {'status','not_a_chunk'}} for r in derived if r['owner_unit_id']==a['unit_id']],a)
    return result


def render(records, encoded):
    lines=['# TT38 — tables, pending experimental',
        'Bản dẫn xuất có ID tp_, không phải legal_unit hoặc chunk DDD; chưa nhập dataset. Nguyên văn và cells giữ riêng.']
    for c,e in zip(records,encoded):
        lines.extend(['## '+c['citation_path'],c['preview_id'],f"Token {e['tokens_with_special']}; unknown {e['unknown_tokens']}; "+('preview' if e['tokens_with_special']<=256 else 'quarantine: TOKEN_BUDGET_EXCEEDED'),
            'Nguyên văn ngoài bảng:',c['text_original'],'Context:',*[x['text_original'] for x in c['contexts']],
            'Dẫn xuất từ cells:',c['text_derived'],'Text for search:',c['text_for_search'],'Encoder:',e['encoder_text']])
    return '\n\n'.join(lines)+'\n'


def validate(path):
    from src.tt38_preview import validate as validate_base
    root=Path(path).resolve().parent;m=check_files(root/'manifest.json')
    if m['manifest_type']!=VERSION or m['code_sha256']!=digest(Path(__file__).read_bytes()) or m['files']!=inventory(root) or m['release_eligible'] is not False:
        raise ValueError('Table preview binding/status mismatch')
    validate_base(root/'base/manifest.json')
    if digest((root/'base/manifest.json').read_bytes())!=m['base_manifest_sha256']:raise ValueError('Table base binding mismatch')
    expected=candidates(root/'base'); enc=rows(root/'encoder_inputs.jsonl')
    if expected!=rows(root/'candidates.jsonl') or len(enc)!=len(expected):raise ValueError('Table candidate replay mismatch')
    for c,e in zip(expected,enc):
        if (e['input_sha256']!=c['content_sha256'] or e['truncation'] is not False or e['tokens_with_special']!=len(e['after']['token_ids'])
            or e['after']['token_ids_sha256']!=digest(canonical(e['after']['token_ids']).encode())
            or e['encoder_text_sha256']!=digest(e['encoder_text'].encode()) or e['unknown_tokens']!=e['after']['token_ids'].count(3)
            or e['model_max_tokens']!=256 or e['role']!='document' or e['preprocessing_version']!=encoder_input.VERSION):raise ValueError('Encoder binding mismatch')
    good=[c for c,e in zip(expected,enc) if e['tokens_with_special']<=256]
    bad=[{**c,'reason':'TOKEN_BUDGET_EXCEEDED'} for c,e in zip(expected,enc) if e['tokens_with_special']>256]
    if rows(root/'tables.preview.jsonl')!=good or rows(root/'tables.quarantine.jsonl')!=bad:raise ValueError('Table budget mismatch')
    if (root/'review.md').read_text(encoding='utf8')!=render(expected,enc):raise ValueError('Table report mismatch')
    return {'technical_valid':True,'candidates':len(expected),'derived_previews':len(good),'quarantined':len(bad),
            'unchanged_legacy_chunks':len(rows(root/'base/chunks.preview.jsonl')),'unknown':sum(e['unknown_tokens'] for e in enc),
            'token_min':min(e['tokens_with_special'] for e in enc),'token_max':max(e['tokens_with_special'] for e in enc),'release_eligible':False}


def build(base_manifest,run_dir):
    from src.tt38_preview import validate as validate_base
    base=Path(base_manifest).resolve().parent;validate_base(base/'manifest.json')
    records=candidates(base);cfg=load(base/'encoder_config.json')
    enc=encoder_input.encode_inputs([c['text_for_search'] for c in records],cfg,base/'tokenizer_assets')['rows']
    root=staging_path(run_dir);root.mkdir(parents=True);shutil.copytree(base,root/'base')
    write_rows(root/'candidates.jsonl',records);write_rows(root/'encoder_inputs.jsonl',enc)
    write_rows(root/'tables.preview.jsonl',[c for c,e in zip(records,enc) if e['tokens_with_special']<=256])
    write_rows(root/'tables.quarantine.jsonl',[{**c,'reason':'TOKEN_BUDGET_EXCEEDED'} for c,e in zip(records,enc) if e['tokens_with_special']>256])
    (root/'review.md').write_text(render(records,enc),encoding='utf8')
    seal(root,{'manifest_type':VERSION,'built_at':now(),'origin':'agent_review','human_reviewer_events':0,
               'base_manifest_sha256':digest((base/'manifest.json').read_bytes()),'code_sha256':digest(Path(__file__).read_bytes()),'release_eligible':False})
    return validate(root/'manifest.json')
