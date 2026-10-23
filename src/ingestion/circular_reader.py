"""Bounded-memory TT51 annex reader, sharing Stage3 normalization/contracts/SQLite.

PDFium is an observation reader, not an encoding repair or OCR. Noncharacters
are preserved and make that file partial. The main circular uses Stage3 as-is.
"""
from contextlib import closing
import importlib.metadata
from pathlib import Path
import platform
import shutil
import unicodedata

from src import extraction_pipeline as stage3
from src.assessment_evidence import check_files, inventory, now, seal
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion import extractors, extraction_normalizer
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, connect_sqlite, digest, require_contract, resolve_ref, validate_extraction
from src.source_registry import ARTIFACTS, inspect_bundle

VERSION = 'circular-pdfium-extraction.v1'
CONFIG = {'reader_policy':VERSION,'normalization':'NFC_LF_ONLY','block_separator':'\n',
          'text_api':'PdfTextPage.get_text_range','decode_repair':False,'ocr':False}


def text_issues(text,locator):
    issues=[]
    if not text.strip():issues.append({'code':'PDF_PAGE_NO_TEXT','severity':'warning','locator':locator,
        'detail':'No reader text; not a blank-page decision. Visual/OCR review pending.'})
    if any(c in text for c in ['\x00','\ufffe','\uffff']):issues.append({'code':'PDF_READER_NONCHARACTER','severity':'error','locator':locator,
        'detail':'NUL/U+FFFE/U+FFFF preserved, never removed or replaced. File text unusable pending scoped decoding review.'})
    return issues


def extract_annex(source, raw_root=BASE_DIR, created_at=None):
    import pypdfium2 as pdfium
    raw=resolve_ref(raw_root,source['measured']['raw_file_ref']).read_bytes()
    if digest(raw)!=source['measured']['sha256'] or len(raw)!=source['measured']['size_bytes']:raise ValueError('Raw binding changed')
    pages=[];issues=[]
    with pdfium.PdfDocument(raw) as pdf:
        for i in range(len(pdf)):
            page=pdf[i]
            try:
                tp=page.get_textpage()
                try:text=tp.get_text_range()
                finally:tp.close()
                locator={'format':'pdf','page_start':i+1,'page_end':i+1,'width':page.get_width(),'height':page.get_height()}
                issues.extend(text_issues(text,locator))
                pages.append(extractors.node('page',locator,raw_text=text))
            finally:page.close()
    text,trace=extraction_normalizer.serialize(extractors.node('document',{'format':'pdf'},children=pages,separator='\n'))
    tool=canonical({'reader':'pypdfium2','versions':{'pypdfium2':importlib.metadata.version('pypdfium2'),'python':platform.python_version(),'unicode':unicodedata.unidata_version},
                    'code_sha256':{p:digest((BASE_DIR/p).read_bytes()) for p in ['src/ingestion/circular_reader.py','src/ingestion/extraction_normalizer.py']}})
    identity={'identity_schema':'extraction.v1','file_id':source['file_id'],'source_raw_sha256':digest(raw),'method':'pdf_text','tool_version':tool,
              'config_sha256':digest(canonical(CONFIG).encode()),'text_sha256':digest(text.encode()),'trace_content_sha256':digest(canonical(trace).encode())}
    eid='e_'+digest(canonical(identity).encode())
    for n in trace['nodes']:
        n.update(extraction_id=eid,locator_id='l_'+digest(canonical({'extraction_id':eid,'node_index':n['node_index'],'locator':n['locator']}).encode()))
        n['parent_locator_id']=None if n['parent_index'] is None else trace['nodes'][n['parent_index']]['locator_id']
    trace_bytes=(canonical(trace)+'\n').encode()
    e={'extraction_id':eid,'file_id':source['file_id'],'method':'pdf_text','tool_version':tool,'text_ref':f'extractions/{eid}/normalized.txt',
       'text_sha256':identity['text_sha256'],'char_count':len(text),'review_status':'pending','created_at':created_at or now()}
    require_contract('extraction',e)
    record={'extraction':e,'law_id':source['law_id'],'source_status':'pending','technical_status':'partial' if any(q['severity']=='error' for q in issues) else 'complete',
            'config_sha256':identity['config_sha256'],'source_raw_sha256':digest(raw),'trace_ref':f'extractions/{eid}/trace.json',
            'trace_sha256':digest(trace_bytes),'trace_content_sha256':identity['trace_content_sha256']}
    stage3.require_profile('pending_extraction',record)
    return record,text.encode(),trace_bytes,trace,issues


def validate(path):
    path=Path(path).resolve();root=path.parent;m=check_files(path)
    if (m['manifest_type']!=VERSION or m['files']!=inventory(root) or m['release_eligible'] is not False
        or m['origin']!='agent_review' or m['snapshot_date']!=SNAPSHOT_DATE or m['code_sha256']!=digest(Path(__file__).read_bytes())
        or load(root/'config.json')!=CONFIG or (root/'pending_schema.sql').read_bytes()!=(stage3.SCHEMA_DIR/'pending_schema.sql').read_bytes()):raise ValueError('Reader manifest mismatch')
    if not inspect_bundle(root/'source_snapshot/manifest.json')['technical_valid']:raise ValueError('Source snapshot invalid')
    sources=rows(root/'source_snapshot/files.pending.jsonl');records=rows(root/'extractions.pending.jsonl');traces=[];issues=[];statuses=[]
    for source in sources:
        actual=next(r for r in records if r['extraction']['file_id']==source['file_id'])
        args={'created_at':actual['extraction']['created_at']}
        expected,text,tbytes,trace,qs=extract_annex(source,**args) if source['file_role']=='annex' else stage3.extract_file(source,BASE_DIR,load(BASE_DIR/'config/extraction.v1.json'),**args)
        if actual!=expected or resolve_ref(root,actual['extraction']['text_ref']).read_bytes()!=text or resolve_ref(root,actual['trace_ref']).read_bytes()!=tbytes:raise ValueError('Reader text/trace/metadata replay mismatch')
        if validate_extraction(actual['extraction'],sources,root):raise ValueError('Extraction contract mismatch')
        own=[stage3.issue_record(source['file_id'],actual['extraction']['extraction_id'],q,i) for i,q in enumerate(qs)]
        issues.extend(own);statuses.append(stage3.status_record(source,actual,own));traces.append(trace)
    if issues!=rows(root/'quality_issues.jsonl') or statuses!=rows(root/'file_status.jsonl'):raise ValueError('Reader issues mismatch')
    expected_db=stage3.database_rows(sources,records,traces,issues)
    with closing(connect_sqlite(root/'extraction.pending.sqlite',readonly=True)) as db:
        if db.execute('PRAGMA foreign_key_check').fetchall() or db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Reader SQLite integrity/FK error')
        for table,value in expected_db.items():
            actual=[dict(r) for r in db.execute('SELECT * FROM '+table)]
            if sorted(actual,key=canonical)!=sorted(value,key=canonical):raise ValueError('Reader SQLite export mismatch')
    result={'technical_valid':True,'reader_completed':True,'processing_success':all(r['technical_status']=='complete' for r in records),
            'extractions':len(records),'pages':sum(len([n for n in t['nodes'] if n['kind']=='page']) for t in traces),
            'issues':len(issues),'partial_files':sum(r['technical_status']=='partial' for r in records),'release_eligible':False}
    if load(root/'validation_report.json')!=result:raise ValueError('Reader report mismatch')
    return result


def build(source_manifest,run_dir):
    path=Path(source_manifest).resolve()
    if not inspect_bundle(path)['technical_valid']:raise ValueError('Source registration invalid')
    sources=rows(path.parent/'files.pending.jsonl')
    if len(sources)!=2 or any(s['law_id']!='51/2024/TT-BGTVT' for s in sources) or {s['file_role'] for s in sources}!={'main','annex'}:raise ValueError('This reader profile is limited to registered TT51 main/QCVN')
    root=staging_path(run_dir);root.mkdir(parents=True);(root/'source_snapshot').mkdir()
    for name in [*ARTIFACTS,'manifest.json','manifest.sha256']:
        target=root/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path.parent/name,target)
    write_json(root/'config.json',CONFIG)
    records=[];traces=[];issues=[];statuses=[]
    for source in sources:
        rec,text,tbytes,trace,qs=extract_annex(source) if source['file_role']=='annex' else stage3.extract_file(source,BASE_DIR,load(BASE_DIR/'config/extraction.v1.json'))
        for ref,data in [(rec['extraction']['text_ref'],text),(rec['trace_ref'],tbytes)]:
            p=resolve_ref(root,ref);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        own=[stage3.issue_record(source['file_id'],rec['extraction']['extraction_id'],q,i) for i,q in enumerate(qs)]
        records.append(rec);traces.append(trace);issues.extend(own);statuses.append(stage3.status_record(source,rec,own))
    for name,value in [('extractions.pending',records),('quality_issues',issues),('file_status',statuses)]:write_rows(root/(name+'.jsonl'),value)
    shutil.copyfile(stage3.SCHEMA_DIR/'pending_schema.sql',root/'pending_schema.sql')
    with closing(connect_sqlite(root/'extraction.pending.sqlite')) as db:
        db.executescript((root/'pending_schema.sql').read_text(encoding='utf8'))
        with db:
            for table,value in stage3.database_rows(sources,records,traces,issues).items():
                for r in value:db.execute(f"INSERT INTO {table} ({','.join(r)}) VALUES ({','.join('?' for _ in r)})",list(r.values()))
    write_json(root/'validation_report.json',{'technical_valid':True,'reader_completed':True,'processing_success':all(r['technical_status']=='complete' for r in records),
        'extractions':len(records),'pages':sum(len([n for n in t['nodes'] if n['kind']=='page']) for t in traces),'issues':len(issues),
        'partial_files':sum(r['technical_status']=='partial' for r in records),'release_eligible':False})
    seal(root,{'manifest_type':VERSION,'built_at':now(),'origin':'agent_review','snapshot_date':SNAPSHOT_DATE,'release_eligible':False,'code_sha256':digest(Path(__file__).read_bytes())})
    return validate(root/'manifest.json')
