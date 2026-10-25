"""Local Tesseract page drafts with measured boxes/confidence and resume checks."""
from pathlib import Path
import csv
import io
import os
import subprocess
import unicodedata
from src.assessment_evidence import now
from src.experimental_dataset import load, rows, write_json
from src.source_contracts import canonical, digest

VERSION='tesseract-page-draft.v1'


def configuration(executable, tessdata, scale=3, psm=3):
    exe=Path(executable).resolve();td=Path(tessdata).resolve()
    version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,check=True).stdout
    return {'policy':VERSION,'executable_sha256':digest(exe.read_bytes()),'tool_version':version,
            'vie_sha256':digest((td/'vie.traineddata').read_bytes()),'languages':'vie',
            'render_scale':scale,'psm':psm,'oem':1,'source_modified':False,
            'license':'Tesseract Apache-2.0; dependencies carry separate licenses in portable environment',
            'code_sha256':digest(Path(__file__).read_bytes())}


def validate_result(result, root, file, cfg, page):
    if (result['config']!=cfg or result['source_sha256']!=file['sha256']
            or result['file_id']!=file['file_id'] or result['pdf_page']!=page
            or result['origin']!='agent_review' or result['review_status']!='pending'):
        raise ValueError('OCR resume/provenance binding mismatch')
    for name,h in result['artifacts'].items():
        if digest((root/name).read_bytes())!=h:raise ValueError('OCR draft artifact checksum mismatch')
    text=(root/'normalized.txt').read_text(encoding='utf8')
    if text!=unicodedata.normalize('NFC',(root/'draft.txt').read_bytes().decode('utf8').replace('\r\n','\n').replace('\r','\n')):
        raise ValueError('OCR normalization changed source output')
    for word in result['words']:
        if word['char_start'] is not None and text[word['char_start']:word['char_end']]!=word['text']:
            raise ValueError('OCR word offset mismatch')


def run_page(file, page_no, root, executable, tessdata, cfg, *, resume=False):
    import pypdfium2 as pdfium
    root=Path(root)/file['file_id']/f'page-{page_no:04d}'
    if (root/'result.json').exists():
        if not resume:raise ValueError('OCR page exists; require --resume')
        result=load(root/'result.json');validate_result(result,root,file,cfg,page_no);return result
    root.mkdir(parents=True,exist_ok=True)
    raw=Path(file['local_ref'])
    if digest(raw.read_bytes())!=file['sha256']:raise ValueError('OCR input source changed')
    with pdfium.PdfDocument(str(raw)) as pdf:
        page=pdf[page_no-1];width,height=page.get_width(),page.get_height()
        page.render(scale=cfg['render_scale']).to_pil().save(root/'source.png');page.close()
    cmd=[str(Path(executable).resolve()),str((root/'source.png').resolve()),str((root/'draft').resolve()),
         '--tessdata-dir',str(Path(tessdata).resolve()),'-l',cfg['languages'],'--oem','1',
         '--psm',str(cfg['psm']),'txt','tsv']
    env={**os.environ,'OMP_THREAD_LIMIT':'1'}
    started=now();proc=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',env=env,timeout=120)
    (root/'stderr.txt').write_text(proc.stderr,encoding='utf8')
    if proc.returncode:raise ValueError('Tesseract failed: '+proc.stderr)
    original=(root/'draft.txt').read_bytes().decode('utf8');text=unicodedata.normalize('NFC',original.replace('\r\n','\n').replace('\r','\n'))
    (root/'normalized.txt').write_bytes(text.encode('utf8'));words=[];cursor=0
    for row in csv.DictReader(io.StringIO((root/'draft.tsv').read_text(encoding='utf8')),delimiter='\t',quoting=csv.QUOTE_NONE):
        if not row.get('text','').strip():continue
        word=unicodedata.normalize('NFC',row['text']);start=text.find(word,cursor)
        if start>=0:cursor=start+len(word)
        x,y,w,h=[int(row[k]) for k in ['left','top','width','height']];scale=cfg['render_scale']
        words.append({'text':word,'confidence':float(row['conf']),'bbox_pixels':[x,y,x+w,y+h],
                      'bbox_pdf_top_origin':[x/scale,y/scale,(x+w)/scale,(y+h)/scale],
                      'char_start':start if start>=0 else None,'char_end':start+len(word) if start>=0 else None})
    result={'file_id':file['file_id'],'law_id':file['law_id'],'source_sha256':file['sha256'],
            'source_ref':file['local_ref'],'pdf_page':page_no,'bbox_pdf_points_full_page':[0,0,width,height],
            'offset_space':'new_ocr_normalized_unicode_codepoints_not_reader_offsets','config':cfg,
            'started_at':started,'completed_at':now(),'words':words,
            'low_confidence_words':sum(w['confidence']<80 for w in words),
            'unmapped_words':sum(w['char_start'] is None for w in words),
            'origin':'agent_review','review_status':'pending','human_reviewer_events':0,
            'quality_state':'OCR_DRAFT_NOT_LEGAL_OR_SOURCE_VERIFIED','release_eligible':False,
            'artifacts':{n:digest((root/n).read_bytes()) for n in ['source.png','draft.txt','draft.tsv','normalized.txt','stderr.txt']}}
    validate_result(result,root,file,cfg,page_no);write_json(root/'result.json',result);return result


def build(extraction_manifest,run_root,executable,tessdata,*,pilot=False,resume=False):
    source=Path(extraction_manifest).parent;files=rows(source/'files.pending.jsonl');cfg=configuration(executable,tessdata)
    root=Path(run_root);root.mkdir(parents=True,exist_ok=resume)
    if (root/'config.json').exists() and load(root/'config.json')!=cfg:raise ValueError('OCR config changed on resume')
    write_json(root/'config.json',cfg);result=[]
    selected={1:[5,9],3:[30],4:[50],5:[40]}
    for f in files:
        cp=load(source/'pages'/f['file_id']/'checkpoint.json')
        for i in range(1,cp['total_pages']+1):
            p=load(source/'pages'/f['file_id']/f'page-{i:04d}.json')
            # Only image-dependent pages: do not OCR good reader pages or the entire source blindly.
            required=len(p['normalized_text'])<500 and bool(p['images'])
            use=i in selected.get(f['part_order'],[]) if pilot else required
            if not use:continue
            output=run_page(f,i,root/'pages',executable,tessdata,cfg,resume=resume)
            result.append({'file_id':f['file_id'],'pdf_page':i,'result_ref':f"pages/{f['file_id']}/page-{i:04d}/result.json",'low_confidence_words':output['low_confidence_words']})
            write_json(root/'checkpoint.json',{'state':'IN_PROGRESS','pages':result,'updated_at':now()});print(f"OCR {f['part_order']}:{i}",flush=True)
    write_json(root/'checkpoint.json',{'state':'OCR_DRAFTS_COMPLETE_REVIEW_PENDING','pages':result,'updated_at':now()})
    return {'ocr_pages':len(result),'legal_review':'pending','ocr_replaces_reader':False}
