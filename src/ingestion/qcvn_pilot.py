"""Four-page reproducible reader/render pilot plus explicit agent transcription."""
from pathlib import Path
import importlib.metadata
import shutil
import unicodedata
import io
import pypdfium2 as pdfium
from src.assessment_evidence import check_files, inventory, now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import digest
from src.config import BASE_DIR
from src.pipeline_cli import staging_path

CONFIG=BASE_DIR/'config/qcvn_pilot.agent_transcription.v1.json'


def build(manifest,run_dir):
    p=Path(manifest).resolve();check_files(p);root=staging_path(run_dir)
    src=next(s for s in rows(p.parent/'source_snapshot/files.pending.jsonl') if s['file_role']=='annex')
    raw=BASE_DIR/src['measured']['raw_file_ref'];cfg=load(CONFIG)
    if digest(raw.read_bytes())!=cfg['raw_sha256'] or cfg['raw_sha256']!=src['measured']['sha256']:raise ValueError('QCVN source mismatch')
    root.mkdir(parents=True);results=[];write_json(root/'transcription_config.json',cfg)
    with pdfium.PdfDocument(str(raw)) as pdf:
        for item in cfg['pages']:
            i=item['pdf_page'];page=pdf[i-1];tp=page.get_textpage()
            text=tp.get_text_range();tp.close()
            image=page.render(scale=1.5).to_pil();image.save(root/f'page-{i}.png')
            bbox=[0,0,page.get_width(),page.get_height()];page.close()
            (root/f'page-{i}.reader.txt').write_text(text,encoding='utf8',newline='')
            original=item['text'];normalized=unicodedata.normalize('NFC',original.replace('\r\n','\n').replace('\r','\n'))
            (root/f'page-{i}.transcription.txt').write_text(normalized,encoding='utf8',newline='')
            results.append({**item,'text':normalized,'raw_sha256':cfg['raw_sha256'],'source_ref':str(raw.relative_to(BASE_DIR)).replace('\\','/'),
                'source_locator':{'format':'pdf','pdf_page':i,'bbox_pdf_points_full_page':bbox},
                'region_precision':'page_only_not_glyph_bbox','offset_space':'new_transcription_unicode_codepoints',
                'char_start':0,'char_end':len(normalized),'text_sha256':digest(normalized.encode()),
                'reader_codepoints':len(text),'reader_nul':text.count('\x00'),'reader_ufffe':text.count('\ufffe'),
                'reader_sha256':digest(text.encode()),'image_sha256':digest((root/f'page-{i}.png').read_bytes()),
                'origin':'agent_review','review_status':'pending','release_eligible':False,
                'tool_version':importlib.metadata.version('pypdfium2'),'render_scale':1.5})
    write_rows(root/'pages.jsonl',results)
    write_json(root/'tools.json',{'tesseract':shutil.which('tesseract'),'pdftotext':shutil.which('pdftotext'),
        'ocr_executed':False,'reason':'No installed OCR executable; scoped visual transcription is separate from reader text',
        'font_evidence_ref':'staging/circulars-completion-audit-001/qcvn-font-diagnostic.json',
        'font_evidence_sha256':digest((BASE_DIR/'staging/circulars-completion-audit-001/qcvn-font-diagnostic.json').read_bytes())})
    lines=['# QCVN four-page pilot — agent_review, pending','PDF page equals printed page for these four samples. No units/chunks created.']
    for r in results:lines.extend([f"## PDF/printed {r['pdf_page']}",r['text'],r['status'],r['missing'],f"Reader U+FFFE: {r['reader_ufffe']}; chars: {r['reader_codepoints']}"])
    (root/'review.md').write_text('\n\n'.join(lines),encoding='utf8')
    seal(root,{'manifest_type':'qcvn-four-page-pilot.v1','built_at':now(),'origin':'agent_review','human_reviewer_events':0,
        'release_eligible':False,'source_manifest_ref':str(p.relative_to(BASE_DIR)).replace('\\','/'),'source_manifest_sha256':digest(p.read_bytes()),
        'raw_ref':str(raw.relative_to(BASE_DIR)).replace('\\','/'),'raw_sha256':cfg['raw_sha256'],
        'code_sha256':digest(Path(__file__).read_bytes()),'config_sha256':digest(CONFIG.read_bytes())})
    return validate(root/'manifest.json')


def validate(manifest):
    p=Path(manifest).resolve();root=p.parent;m=check_files(p)
    if m['manifest_type']!='qcvn-four-page-pilot.v1' or m['origin']!='agent_review' or m['files']!=inventory(root) or m['code_sha256']!=digest(Path(__file__).read_bytes()) or m['config_sha256']!=digest(CONFIG.read_bytes()) or m['release_eligible'] is not False or m['human_reviewer_events']!=0:raise ValueError('Pilot binding mismatch')
    if load(root/'transcription_config.json')!=load(CONFIG):raise ValueError('Pilot config mismatch')
    if digest((BASE_DIR/m['source_manifest_ref']).read_bytes())!=m['source_manifest_sha256'] or digest((BASE_DIR/m['raw_ref']).read_bytes())!=m['raw_sha256']:raise ValueError('Pilot source changed')
    cfg=load(CONFIG);result=rows(root/'pages.jsonl')
    if [r['pdf_page'] for r in result]!=[7,214,300,368]:raise ValueError('Pilot page scope changed')
    with pdfium.PdfDocument(str(BASE_DIR/m['raw_ref'])) as pdf:
        for r,c in zip(result,cfg['pages']):
            page=pdf[r['pdf_page']-1];tp=page.get_textpage();t=tp.get_text_range();tp.close()
            if any(r[k]!=v for k,v in c.items()) or r['raw_sha256']!=m['raw_sha256'] or r['char_start']!=0 or r['source_locator']!={'format':'pdf','pdf_page':r['pdf_page'],'bbox_pdf_points_full_page':[0,0,page.get_width(),page.get_height()]}:raise ValueError('Pilot scope/locator mismatch')
            buffer=io.BytesIO();page.render(scale=1.5).to_pil().save(buffer,format='PNG')
            rendered=digest(buffer.getvalue());page.close()
            if digest(t.encode())!=r['reader_sha256'] or rendered!=r['image_sha256'] or t!=(root/f"page-{r['pdf_page']}.reader.txt").read_bytes().decode('utf8'):raise ValueError('Pilot reader/render replay mismatch')
            value=(root/f"page-{r['pdf_page']}.transcription.txt").read_text(encoding='utf8')
            if value!=c['text'] or value!=r['text'] or len(value)!=r['char_end'] or digest(value.encode())!=r['text_sha256'] or r['origin']!='agent_review' or r['review_status']!='pending':raise ValueError('Pilot transcription mismatch')
    return {'technical_valid':True,'pages':4,'qcvn_chunks':0,'ocr_executed':False,'release_eligible':False}
