"""Seven-source offline completion runner; checkpoints never imply legal approval."""
import argparse
import json
from pathlib import Path
import sys
import shutil
import tempfile
from src.experimental_dataset import load, rows, write_json, write_rows
from src.assessment_evidence import check_files, now, seal
from src.source_contracts import digest
from src.ingestion import full_source
from src.config import STAGING_DIR


def run_path(path,resume=False):
    target=Path(path).resolve();staging=STAGING_DIR.resolve()
    if staging!=STAGING_DIR.absolute() or target==staging or staging not in target.parents:
        raise ValueError('--run-dir must stay strictly inside staging/')
    if target.exists() and not resume:raise FileExistsError('Run exists; choose a new staging run')
    if resume and not target.is_dir():raise ValueError('Resume requires an existing partial run')
    return target


def resume_serialization(file,root):
    """Recompute to a private temporary directory; compare instead of overwriting.

    The page reader and extraction identity are unchanged. This also recovers an
    interruption after normalized/trace/identity were written but before seal.
    """
    with tempfile.TemporaryDirectory(prefix='serialization-check-',dir=root) as temp:
        if not Path(temp).resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe temporary path')
        rec=full_source.extraction_from_pages(file,root/'pages',Path(temp))
        relative=Path(rec['extraction']['text_ref']).parent;source=Path(temp)/relative;dest=root/relative
        if dest.exists():
            expected={p.name for p in source.iterdir()}
            if not {p.name for p in dest.iterdir()}<=expected:raise ValueError('Unexpected existing serialization; retain for investigation')
            for p in source.iterdir():
                existing=dest/p.name
                if existing.exists() and p.read_bytes()!=existing.read_bytes():raise ValueError('Existing serialization differs from source replay')
            for p in source.iterdir():
                if not (dest/p.name).exists():shutil.copyfile(p,dest/p.name)
        else:
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,dest)
        return rec


def source_scan(config, run_dir, resume=False, law_id=None,comparison_inventory=None):
    cfg=load(config);root=run_path(run_dir,resume)
    if cfg['snapshot_date']!='2025-01-01':raise ValueError('Snapshot mismatch')
    if comparison_inventory is not None:
        check_files(Path(comparison_inventory).parent/'manifest.json')
        files=[f for f in rows(comparison_inventory) if f['file_role']=='official_comparison_pdf' and (law_id is None or f['law_id']==law_id)]
    else:
        files=full_source.gazette_files(cfg) if law_id is None else [
            {**f,'mime_type':'application/pdf'} for f in rows(Path(cfg['metadata_manifest']).parent/'source_metadata.jsonl')
            if f['law_id']==law_id and f['local_ref'].lower().endswith('.pdf')]
    if not files:raise ValueError('No registered PDF files for selected law')
    for f in files:
        if digest(Path(f['local_ref']).read_bytes())!=f['sha256']:raise ValueError('Source checksum mismatch before creating run')
    if (root/'manifest.json').exists():raise ValueError('Sealed scan cannot be overwritten')
    if (root/'config.json').exists() and load(root/'config.json')!=cfg:raise ValueError('Resume config mismatch')
    root.mkdir(parents=True,exist_ok=resume);write_json(root/'config.json',cfg)
    selection={'law_id':law_id,'comparison_inventory_ref':None if comparison_inventory is None else Path(comparison_inventory).as_posix(),
        'comparison_inventory_sha256':None if comparison_inventory is None else digest(Path(comparison_inventory).read_bytes())}
    if (root/'source_selection.json').exists() and load(root/'source_selection.json')!=selection:raise ValueError('Resume source selection changed')
    write_json(root/'source_selection.json',selection)
    write_rows(root/'files.pending.jsonl',files)
    records=[]
    for f in files:
        cp=full_source.scan_pdf(f,root/'pages',resume=resume)
        print(f['file_id'],cp['state'],flush=True)
    # Serialization occurs once after all resumable page checkpoints succeed.
    for f in files:records.append(resume_serialization(f,root) if resume else full_source.extraction_from_pages(f,root/'pages',root))
    write_rows(root/'extractions.pending.jsonl',records)
    seal(root,{'manifest_type':'seven-source-gazette-extraction.v1','built_at':now(),'snapshot_date':'2025-01-01',
               'origin':'agent_review','release_eligible':False,'human_reviewer_events':0,
               'code_sha256':digest(Path(full_source.__file__).read_bytes())})
    return {'files':len(files),'pages':sum(load(root/'pages'/f['file_id']/'checkpoint.json')['total_pages'] for f in files),
            'technical_reader_completed':True,'legal_review':'pending'}


def preflight_ocr(manifest):
    """Also on resume: a valid saved page cannot excuse changed source bytes."""
    check_files(manifest)
    for source in rows(Path(manifest).parent/'files.pending.jsonl'):
        if digest(Path(source['local_ref']).read_bytes())!=source['sha256']:
            raise ValueError('OCR source checksum changed before run/resume')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    q=s.add_parser('source-scan');q.add_argument('--config',type=Path,default=Path('config/seven_source_completion.v1.json'))
    q.add_argument('--run-dir',type=Path,required=True);q.add_argument('--resume',action='store_true')
    q.add_argument('--law-id',help='Optional registered PDF law; default is the new TT51 Gazette source set')
    q.add_argument('--comparison-inventory',type=Path,help='Explicit sealed inventory for existing captured official comparison PDFs')
    q=s.add_parser('ocr');q.add_argument('--extraction-manifest',type=Path,required=True);q.add_argument('--run-dir',type=Path,required=True)
    q.add_argument('--executable',type=Path,required=True);q.add_argument('--tessdata',type=Path,required=True)
    q.add_argument('--pilot',action='store_true');q.add_argument('--resume',action='store_true')
    q=s.add_parser('nd168-html');q.add_argument('--config',type=Path,default=Path('config/nd168_a16k2.v1.json'));q.add_argument('--run-dir',type=Path,required=True)
    q=s.add_parser('previews');q.add_argument('--config',type=Path,default=Path('config/seven_source_completion.v1.json'));q.add_argument('--run-dir',type=Path,required=True)
    q=s.add_parser('regions');q.add_argument('--source-run',type=Path,required=True);q.add_argument('--run-dir',type=Path,required=True)
    q=s.add_parser('complete-records');q.add_argument('--config',type=Path,default=Path('config/seven_source_completion.v1.json'));q.add_argument('--run-dir',type=Path,required=True)
    q=s.add_parser('qcvn-graph');q.add_argument('--source-run',type=Path,required=True);q.add_argument('--regions-run',type=Path,required=True);q.add_argument('--run-dir',type=Path,required=True)
    q.add_argument('--previous-graph-manifest',type=Path)
    q.add_argument('--parser-revision',choices=['qcvn-reader-boundaries.v1.1','qcvn-reader-boundaries.v1.2'],default='qcvn-reader-boundaries.v1.2')
    for action in ['ledger','dataset']:
        q=s.add_parser(action);q.add_argument('--config',type=Path,default=Path('config/seven_source_completion.v1.json'));q.add_argument('--run-dir',type=Path,required=True)
        if action=='ledger':q.add_argument('--candidate-manifest',type=Path);q.add_argument('--qcvn-graph-manifest',type=Path)
        if action=='dataset':q.add_argument('--qcvn-graph-manifest',type=Path)
    q=s.add_parser('source-repairs');q.add_argument('--run-dir',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        a.run_dir=run_path(a.run_dir,getattr(a,'resume',False))
        if a.action=='source-repairs':
            from src.ingestion.completion_repairs import build
            result=build(a.run_dir)
        elif a.action=='ledger':
            from src.ingestion.completion_ledger import build
            result=build(a.config,a.run_dir,a.candidate_manifest,a.qcvn_graph_manifest)
        elif a.action=='dataset':
            from src.ingestion.completion_dataset import build
            result=build(a.config,a.run_dir,a.qcvn_graph_manifest)
        elif a.action=='qcvn-graph':
            from src.ingestion.qcvn_graph import build
            result=build(a.source_run,a.regions_run,a.run_dir,a.previous_graph_manifest,a.parser_revision)
        elif a.action=='complete-records':
            from src.ingestion.completion_records import build
            result=build(a.config,a.run_dir)
        elif a.action=='regions':
            from src.ingestion.source_regions import build
            result=build(a.source_run,a.run_dir)
        elif a.action=='previews':
            from src.ingestion.full_preview import build
            result=build(a.config,a.run_dir)
        elif a.action=='nd168-html':
            from src.ingestion.full_graph import nd168_html
            result=nd168_html(a.config,a.run_dir)
        elif a.action=='ocr':
            from src.ingestion.ocr_pages import build
            preflight_ocr(a.extraction_manifest)
            result=build(a.extraction_manifest,a.run_dir,a.executable,a.tessdata,pilot=a.pilot,resume=a.resume)
        else:result=source_scan(a.config,a.run_dir,a.resume,a.law_id,a.comparison_inventory)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,OSError) as e:
        print(f'ERROR: {type(e).__name__}: {e}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
