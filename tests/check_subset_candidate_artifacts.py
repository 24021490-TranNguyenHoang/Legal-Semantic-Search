"""Real subset/ZIP/replay checks. All mutations use a private bundle copy."""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from src import subset_candidate_portable as p
from src.subset_candidate import preflight, archive
from src.experimental_dataset import write_json, write_rows
from src.pipeline_cli import staging_path


AUDIT = r'''
import contextlib,importlib.metadata,io,json,os,runpy,sys,traceback
from pathlib import Path
root=Path(sys.argv[1]).resolve();repo=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve()
venv=Path(sys.executable).resolve().parent.parent;base=Path(sys.base_prefix).resolve();script=Path(__file__).resolve().parent
allowed=[root,out,venv,base,script];denied=[];probe=True
def audit(event,args):
 if event=='socket.connect':raise PermissionError('No network allowed during portable read')
 if event!='open'or isinstance(args[0],int):return
 target=Path(args[0]).resolve()
 if any(target.is_relative_to(a)for a in allowed):return
 denied.append({'path':str(target),'expected_probe':probe});raise PermissionError('Read outside portable roots denied')
sys.addaudithook(audit)
for target in [repo/'AGENTS.md',repo/'staging/source-session4-preview-007/manifest.json',repo/'.venv-stage1/Lib/site-packages',Path.home()/'.cache/huggingface/FORBIDDEN-cache-test']:
 try:target.read_bytes()
 except PermissionError:pass
 else:raise AssertionError('Original repo/cache access was not blocked')
probe=False
distributions=[d.metadata['Name']for d in importlib.metadata.distributions()]
if distributions:raise AssertionError('Runtime environment was not clean: '+str(distributions))
ids=json.loads((root/'example_record_ids.json').read_text(encoding='utf8'))
commands=[['validate'],['list']]+[['read','--record-id',rid]for rid in ids]+[['full-read','--output',str(out/'all-records.read.jsonl')]]
results=[]
for i,command in enumerate(commands,1):
 argv=[str(root/'consumer.py'),command[0],'--dataset',str(root),*command[1:]];sys.argv=argv
 stdout=io.StringIO();stderr=io.StringIO();code=0
 try:
  with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
   runpy.run_path(str(root/'consumer.py'),run_name='__main__')
 except SystemExit as ex:code=ex.code or 0
 except BaseException:
  code=1;traceback.print_exc(file=stderr)
 (out/(str(i).zfill(2)+'-'+command[0]+'.stdout.json')).write_text(stdout.getvalue(),encoding='utf8')
 (out/(str(i).zfill(2)+'-'+command[0]+'.stderr.log')).write_text(stderr.getvalue(),encoding='utf8')
 results.append({'argv':argv,'exit_code':code})
 if code:break
foreign=[]
for name,module in list(sys.modules.items()):
 ref=getattr(module,'__file__',None)
 if ref and not any(Path(ref).resolve().is_relative_to(a)for a in allowed):foreign.append({'module':name,'file':ref})
report={'commands':results,'all_succeeded':all(r['exit_code']==0 for r in results)and len(results)==len(commands),
        'expected_denials':denied,'unexpected_denials':[x for x in denied if not x['expected_probe']],
        'installed_distributions':distributions,'foreign_modules':foreign,'python':sys.version,'executable':sys.executable,
        'sys_prefix':sys.prefix,'sys_path':sys.path,'same_machine':True,'platform':sys.platform}
(out/'audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if not report['all_succeeded']or report['unexpected_denials']or foreign:raise SystemExit(1)
print(json.dumps(report,ensure_ascii=False))
'''


def negatives(bundle, output):
    private=output/'private_bundle';shutil.copytree(bundle,private)
    c=p.Consumer(private);c.validate();found=[]
    def reject(name, action, level='semantic'):
        try:action()
        except (ValueError,KeyError,OSError,TypeError)as exc:found.append({'case':name,'rejected':True,'level':level,'reason':str(exc)})
        else:raise AssertionError('Mutation accepted: '+name)
    first=next(f for f in c.frames.values()if f['record_type']=='chunk.v1')
    m=c.targets[first['record_id']]
    for case in ['wrong_source','wrong_offset','wrong_extraction']:
        proof=copy.deepcopy(first['native_proofs'][0])
        if case=='wrong_source':proof['raw_sha256']='0'*64
        elif case=='wrong_offset':proof['char_start']+=1
        else:proof['extraction_id']='OLD-extraction-id'
        reject(case,lambda:c.native(proof))
    asset=next(iter(c.assets.values()))['package_ref'];ap=p.safe(private,asset)
    if not ap.is_relative_to(private.resolve()):raise ValueError('Mutation copy path unsafe')
    backup=ap.read_bytes();ap.unlink()
    reject('missing_asset_no_repo_fallback',lambda:p.Consumer(private),'inventory')
    ap.write_bytes(b'FIXTURE CORRUPTION ONLY IN PRIVATE COPY')
    reject('asset_hash_corruption',lambda:p.Consumer(private),'inventory');ap.write_bytes(backup)
    reject('missing_capability',lambda:p.Consumer(private,p.CAPABILITIES-{'table-header-read.v1'}))
    reject('old_unit_id_binding',lambda:c._check_frame(first,{**m,'unit_id':'OLD-source-unit'}))
    depframe=next(f for f in c.frames.values()if f['dependencies'])
    f=copy.deepcopy(depframe);f['dependencies'].pop()
    reject('missing_required_dependency',lambda:c._check_frame(f,c.targets[f['record_id']]))
    f=copy.deepcopy(depframe);f['dependency_units'].pop()
    reject('missing_required_unit_content',lambda:c._check_frame(f,c.targets[f['record_id']]))
    f=copy.deepcopy(first);f['independent_encoder_view']=True
    reject('encoder_view_as_target',lambda:c._check_frame(f,m))
    f=copy.deepcopy(first);f['encoding']['truncation']=True
    reject('truncation',lambda:c._check_frame(f,m))
    f=copy.deepcopy(first);f['encoding']['tokens_with_special']=257
    reject('budget_exceeded',lambda:c._check_frame(f,m))
    table=next(f['record']for f in c.frames.values()if f['record_type']=='table-retrieval.v1')
    for case in ['header','cell','owner']:
        r=copy.deepcopy(table)
        if case=='header':
            row=r['rows'][0]['row'];removed={x['cell_id']for x in r['cells']if x['row']<row}
            r['cells']=[x for x in r['cells']if x['cell_id']not in removed]
            for rr in r['rows']:rr['source_cell_ids']=[i for i in rr['source_cell_ids']if i not in removed]
        elif case=='cell':r['cells'].pop()
        else:r['rows'][0]['owner_unit_id']='WRONG-OWNER'
        r['retrieval_id']=c.helpers.table_identity(r)
        reject('table_'+case+'_even_rehashed',lambda:c._check_table(r))
    r=copy.deepcopy(table);r['cells'][0]['source_slices'][0]['quote_sha256']='0'*64
    reject('table_cell_proof_binding',lambda:c._check_cells(r))
    form=copy.deepcopy(next(iter(c.form_frames.values())))
    form['record']['form_fields'].pop();form['native_proofs'].pop()
    ident={k:form['record'][k]for k in ['law_id','citation_path','source_raw_sha256','extraction_id','char_start','char_end','text_original','form_fields']}
    form['record']['record_id']='fr_'+p.hashed({'identity_schema':'form-retrieval.v1',**ident});form['record_id']=form['record']['record_id']
    form['native_proofs']=[c.native(x)for x in form['native_proofs']]
    reject('form_instruction_omitted_even_rehashed',lambda:c.reader.check(private,form,c.capabilities))
    whole=copy.deepcopy(next(f['record']for f in c.frames.values()if f['record_type']=='source-retrieval.v1'))
    whole['encoder_views'].pop();reject('encoder_view_gap',lambda:c.reader.views(whole))
    nd=next(m for m in c.targets.values()if m.get('artifact_base')=='this_run')
    old=copy.deepcopy(c.artifacts[nd['record_id']]);c.artifacts[nd['record_id']]['original_base']='workspace'
    reject('wrong_this_run_artifact_base',c.validate);c.artifacts[nd['record_id']]=old
    # A mutated JSONL must fail its pinned input binding even after the outer
    # inventory is re-sealed; no private mutation touches the real dataset.
    original=(private/'inputs/session4/packaging_plan.jsonl').read_bytes()
    altered=copy.deepcopy(c.plan);altered.pop();write_rows(private/'inputs/session4/packaging_plan.jsonl',altered)
    manifest=p.load(private/'dataset_manifest.json');manifest['files']=p.inventory(private);manifest['dataset_content_sha256']=p.hashed(manifest['files'])
    write_json(private/'dataset_manifest.json',manifest);(private/'dataset_manifest.sha256').write_text(p.sha((private/'dataset_manifest.json').read_bytes()),encoding='ascii')
    reject('changed_membership_even_resealed',lambda:p.Consumer(private),'pinned_input')
    # Retain private copy and receipts as quarantined mutation evidence.
    write_rows(output/'negative_checks.jsonl',found)
    return found


def check(config, dataset, replay, zip_path, output):
    cfg=preflight(config);dataset=Path(dataset);replay=Path(replay);out=staging_path(output);out.mkdir(parents=True)
    c=p.Consumer(dataset);validation=c.validate();full=c.full_read(out/'full_read.build.jsonl')
    r=p.Consumer(replay);r.validate();rfull=r.full_read()
    equality={ref['path']:p.sha((dataset/ref['path']).read_bytes())==p.sha((replay/ref['path']).read_bytes())for ref in c.manifest['files']}
    equality['dataset_manifest.json']=(dataset/'dataset_manifest.json').read_bytes()==(replay/'dataset_manifest.json').read_bytes()
    if not all(equality.values())or full['responses_content_sha256']!=rfull['responses_content_sha256']:raise ValueError('Replay changed deterministic package/read responses')
    write_json(out/'replay.json',equality)
    archive_result=archive(dataset,zip_path);replay_zip=out/'replay.zip';archive(replay,replay_zip)
    if p.sha(Path(zip_path).read_bytes())!=p.sha(replay_zip.read_bytes()):raise ValueError('Deterministic ZIP replay differs')
    negative=negatives(dataset,out)
    portable=out/'independent';portable.mkdir();extracted=portable/'unpacked';extracted.mkdir()
    with zipfile.ZipFile(zip_path)as z:
        for name in z.namelist():p.safe(extracted,name)
        z.extractall(extracted)
    unpacked=extracted/'candidate'
    if p.inventory(unpacked)!=c.manifest['files']or (unpacked/'dataset_manifest.json').read_bytes()!=(dataset/'dataset_manifest.json').read_bytes():raise ValueError('ZIP extraction changed package')
    venv=portable/'venv-runtime';env=subprocess.run([sys.executable,'-B','-m','venv','--without-pip',str(venv)],capture_output=True,text=True,encoding='utf8')
    (out/'venv_create.log').write_text(env.stdout+env.stderr,encoding='utf8')
    if env.returncode:raise ValueError('Clean runtime venv creation failed')
    run=portable/'runtime-output';run.mkdir();runtime=portable/'harness';runtime.mkdir();script=runtime/'portable_audit.py';script.write_text(AUDIT,encoding='utf8')
    python=venv/('Scripts/python.exe'if sys.platform=='win32'else 'bin/python')
    command=[str(python.resolve()),'-I','-B',str(script.resolve()),str(unpacked.resolve()),str(Path.cwd().resolve()),str(run.resolve())]
    execution=subprocess.run(command,cwd=unpacked,capture_output=True,text=True,encoding='utf8',timeout=240)
    (out/'portable.stdout.log').write_text(execution.stdout,encoding='utf8');(out/'portable.stderr.log').write_text(execution.stderr,encoding='utf8')
    write_json(out/'portable_command.json',{'argv':command,'cwd':unpacked.as_posix(),'exit_code':execution.returncode})
    if execution.returncode:raise ValueError('Full portable ZIP checks failed: '+execution.stderr[-2500:])
    audit=p.load(run/'audit_report.json');portable_full=p.load(run/'07-full-read.stdout.json')
    if portable_full['responses_content_sha256']!=full['responses_content_sha256']:raise ValueError('Extracted portable responses differ')
    baseline=p.load(cfg['baseline_ref']);changed=[ref for ref,h in baseline.items()if not Path(ref).is_file()or p.sha(Path(ref).read_bytes())!=h]
    unexpected=[ref for ref in changed if ref not in ['docs/progress/STATUS.md','docs/ingestion.md']]
    if unexpected:raise ValueError({'protected_changes':unexpected})
    summary={'state':'PACKAGED_AND_FULL_PORTABLE_READ_VERIFIED','validation':validation,'full_read':{k:v for k,v in full.items()if k!='response_hashes'},
        'zip':archive_result,'zip_replay_identical':True,'replay_payload_files':len(equality),'negative_cases_rejected':len(negative),
        'portable_cli_commands':len(audit['commands']),'portable_all_succeeded':audit['all_succeeded'],
        'portable_distributions':audit['installed_distributions'],'portable_unexpected_denials':audit['unexpected_denials'],
        'protected_files_checked':len(baseline),'unexpected_protected_changes':unexpected,'authorized_doc_changes':changed,
        'same_machine_windows_only':True,'runtime_stdlib_only_verified':True,'release_eligible':False,'human_reviewer_events':0}
    write_json(out/'validation_report.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['config','dataset','replay','zip','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();check(args.config,args.dataset,args.replay,args.zip,args.output)


if __name__=='__main__':main()
