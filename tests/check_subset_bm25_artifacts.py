"""Finite actual v5 index/ZIP/replay harness. Mutations only in a private copy."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from src import subset_bm25 as bm
from src.experimental_dataset import load, rows, write_json, write_rows


AUDIT = r'''
import contextlib,importlib.metadata,io,json,os,runpy,sys,traceback
from pathlib import Path
root=Path(sys.argv[1]).resolve();repo=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve()
venv=Path(sys.executable).resolve().parent.parent;base=Path(sys.base_prefix).resolve();script=Path(__file__).resolve().parent
allowed=[root,out,venv,base,script];denied=[];probe=True;device_accesses=[];subprocess_denials=[]
def audit(event,args):
 if event=='socket.connect':raise PermissionError('Network forbidden in portable runtime')
 if event=='subprocess.Popen':
  subprocess_denials.append(str(args[0]));raise PermissionError('Child processes forbidden in portable runtime')
 if event!='open' or isinstance(args[0],int):return
 target=Path(args[0]).resolve()
 if target==Path(os.devnull).resolve():
  device_accesses.append(str(target));return
 if any(target.is_relative_to(a)for a in allowed):return
 denied.append({'path':str(target),'expected_probe':probe});raise PermissionError('Outside portable roots denied')
sys.addaudithook(audit)
for target in [repo/'AGENTS.md',repo/'staging/dataset-v5-subset-006/dataset_manifest.json',repo/'.venv-stage1/pyvenv.cfg',Path.home()/'.cache/huggingface/FORBIDDEN-cache-test']:
 try:target.read_bytes()
 except PermissionError:pass
 else:raise AssertionError('Audit probe not denied')
probe=False
commands=[['validate','--index',str(root)],['batch','--index',str(root),'--output',str(out/'batch')]]
results=[]
for i,args in enumerate(commands,1):
 sys.argv=[str(root/'search.py'),*args];stdout=io.StringIO();stderr=io.StringIO();code=0
 try:
  with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):runpy.run_path(str(root/'search.py'),run_name='__main__')
 except SystemExit as exc:code=exc.code or 0
 except BaseException:code=1;traceback.print_exc(file=stderr)
 (out/(str(i)+'-'+args[0]+'.stdout.json')).write_text(stdout.getvalue(),encoding='utf8')
 (out/(str(i)+'-'+args[0]+'.stderr.log')).write_text(stderr.getvalue(),encoding='utf8')
 results.append({'argv':sys.argv,'exit_code':code})
 if code:break
if all(r['exit_code']==0 for r in results)and len(results)==2:
 sys.path.insert(0,str(root))
 from src import subset_bm25 as bm
 state=bm.load_index(root)
 full=state['consumer'].full_read(out/'all-records.read.jsonl')
 (out/'full_read.json').write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding='utf8')
 # Exercise actual read CLI for one record of each type, in addition to all
 # unique hits read in batch and all138 dataset reads above.
 ids=[next(r['record_id']for r in state['mapping']if r['record_type']==t)for t in bm.COUNTS]
 for i,rid in enumerate(ids,3):
  sys.argv=[str(root/'search.py'),'read','--index',str(root),'--record-id',rid]
  stdout=io.StringIO();stderr=io.StringIO();code=0
  try:
   with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):runpy.run_path(str(root/'search.py'),run_name='__main__')
  except SystemExit as exc:code=exc.code or 0
  except BaseException:code=1;traceback.print_exc(file=stderr)
  (out/(str(i)+'-read.stdout.json')).write_text(stdout.getvalue(),encoding='utf8')
  (out/(str(i)+'-read.stderr.log')).write_text(stderr.getvalue(),encoding='utf8')
  results.append({'argv':sys.argv,'exit_code':code})
distributions={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
if {k.lower():v for k,v in distributions.items()if k.lower()not in ['pip','setuptools']}!={'bm25s':'0.3.13','numpy':'2.4.6','scipy':'1.17.1'}:raise AssertionError('Unexpected distributions')
foreign=[]
for name,module in list(sys.modules.items()):
 ref=getattr(module,'__file__',None)
 if ref and not any(Path(ref).resolve().is_relative_to(a)for a in allowed):foreign.append({'module':name,'file':ref})
report={'commands':results,'all_succeeded':len(results)==5 and all(r['exit_code']==0 for r in results),
 'denials':denied,'unexpected_denials':[x for x in denied if not x['expected_probe']],
 'null_device_accesses':device_accesses,'blocked_metadata_subprocesses':subprocess_denials,
 'installed_distributions':distributions,'foreign_modules':foreign,'python':sys.version,'executable':sys.executable,
 'sys_prefix':sys.prefix,'sys_path':sys.path,'same_machine':True,'platform':sys.platform}
(out/'audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
if not report['all_succeeded']or report['unexpected_denials']or foreign:raise SystemExit(1)
'''


def negative_checks(index, out):
    private = out / 'private_index'
    shutil.copytree(index, private)
    manifest_bytes = (private / 'index_manifest.json').read_bytes()
    sidecar = (private / 'index_manifest.sha256').read_bytes()
    cases = []

    def reject(name, mutate):
        backups = {}

        def save(ref, content):
            path = bm.resolve_ref(private, ref)
            backups[ref] = path.read_bytes()
            if content is None: path.unlink()
            else: path.write_bytes(content)
        mutate(save)
        m = load(private / 'index_manifest.json')
        m['files'] = bm.inventory(private)
        m['index_content_sha256'] = bm.hashed(m['files'])
        write_json(private / 'index_manifest.json', m)
        (private / 'index_manifest.sha256').write_text(bm.digest((private / 'index_manifest.json').read_bytes()), encoding='ascii')
        try: bm.load_index(private)
        except (ValueError, KeyError, OSError, TypeError) as exc:
            cases.append({'case': name, 'rejected': True, 'reason': str(exc), 'outer_inventory_resealed': True})
        else: raise AssertionError('Mutation accepted: ' + name)
        finally:
            for ref, original in backups.items(): bm.resolve_ref(private, ref).write_bytes(original)
            (private / 'index_manifest.json').write_bytes(manifest_bytes)
            (private / 'index_manifest.sha256').write_bytes(sidecar)

    def altered_rows(ref, change):
        value = rows(private / ref)
        change(value)
        return (''.join(bm.canonical(r) + '\n' for r in value)).encode('utf8')

    for key in ['record_id', 'record_type', 'source_id', 'projection_recipe', 'tokens_sha256']:
        reject('mapping_' + key, lambda save, key=key: save('document_mapping.jsonl',
            altered_rows('document_mapping.jsonl', lambda v: v[0].update({key: 'WRONG'}))))
    reject('search_text_changed', lambda save: save('search_inputs.jsonl',
        altered_rows('search_inputs.jsonl', lambda v: v[0].update(text_for_search='SYNTHETIC PRIVATE MUTATION'))))
    for key in ['dataset_version', 'dataset_manifest_sha256', 'consumer_sha256']:
        reject('wrong_' + key, lambda save, key=key: save('index_manifest.json',
            (bm.canonical({**load(private / 'index_manifest.json'), key: 'WRONG'})).encode('utf8')))
    reject('missing_source_asset_no_fallback', lambda save: save('dataset/' + next(x['path'] for x in
        load(private / 'dataset/dataset_manifest.json')['files'] if x['path'].startswith('objects/')), None))
    reject('missing_engine', lambda save: save('engine/data.csc.index.npy', None))
    reject('query_text_changed', lambda save: save('queries/old-dev.queries.jsonl',
        altered_rows('queries/old-dev.queries.jsonl', lambda v: v[0].update(query='SYNTHETIC PRIVATE MUTATION'))))
    write_rows(out / 'negative_checks.jsonl', cases)
    return cases


def check(index, replay, batch, output, zip_path):
    out = bm.new_output(output)
    index, replay, batch = Path(index), Path(replay), Path(batch)
    state = bm.load_index(index)
    validation = bm.validate(index)
    rs = bm.load_index(replay)
    same = {x['path']: bm.digest((index / x['path']).read_bytes()) == bm.digest((replay / x['path']).read_bytes())
            for x in state['manifest']['files']}
    same['index_manifest.json'] = (index / 'index_manifest.json').read_bytes() == (replay / 'index_manifest.json').read_bytes()
    if not all(same.values()): raise AssertionError('Replay index differs')
    write_json(out / 'replay_payload.json', same)
    replay_batch = out / 'replay_batch'
    bm.batch_loaded(rs, replay_batch)
    signature = (batch / 'ranking_and_response_signature.jsonl').read_bytes()
    if signature != (replay_batch / 'ranking_and_response_signature.jsonl').read_bytes():
        raise AssertionError('Ranking/response replay differs')
    full = state['consumer'].full_read(out / 'full_read.main.jsonl')
    write_json(out / 'full_read.main.report.json', full)
    probes = []
    for name, action in [
        ('query_empty', lambda: bm.search_loaded(state, '')),
        ('query_whitespace', lambda: bm.search_loaded(state, ' \t ')),
        ('query_no_tokens', lambda: bm.search_loaded(state, '!!!')),
        ('top_k_zero', lambda: bm.search_loaded(state, 'xe', 0)),
        ('invalid_source_filter', lambda: bm.search_loaded(state, 'xe', source_id='NO-SOURCE')),
        ('invalid_type_filter', lambda: bm.search_loaded(state, 'xe', record_type='encoder-view')),
        ('supporting_not_target', lambda: bm.read_loaded(state, next(uid for uid in state['consumer'].support if uid not in state['consumer'].targets))),
        ('record_unknown', lambda: bm.read_loaded(state, 'UNKNOWN')),
        ('missing_index_no_build', lambda: bm.load_index(out / 'MISSING-index'))]:
        try: action()
        except (ValueError, KeyError, OSError, TypeError) as exc: probes.append({'case': name, 'rejected': True, 'reason': str(exc)})
        else: raise AssertionError('Probe accepted: ' + name)
    assert bm.search_loaded(state, 'zzxxyyqovnothing')['results'] == []
    assert bm.search_loaded(state, 'xe', source_id='SRC-004')['results'] == []
    for kind in bm.COUNTS:
        matches = bm.search_loaded(state, 'đường', 138, record_type=kind)['results']
        assert matches and all(h['record_type'] == kind for h in matches)
        bm.read_loaded(state, matches[0]['record_id'])
    for source, law in [(s['source_id'], s['law_id']) for s in state['consumer'].sources.values()]:
        matches = bm.search_loaded(state, 'đường', 138, source_id=source, law_id=law)['results']
        assert all(h['source_id'] == source and h['law_id'] == law for h in matches)
    assert bm.search_loaded(state, 'đường')['results'] == bm.search_loaded(state, 'đường')['results']
    write_rows(out / 'error_probes.jsonl', probes)
    negatives = negative_checks(index, out)
    zip_path = Path(zip_path)
    archive = bm.archive(index, zip_path)
    replay_zip = out / 'replay.zip'
    bm.archive(replay, replay_zip)
    if bm.digest(replay_zip.read_bytes()) != archive['sha256']: raise AssertionError('ZIP replay differs')
    portable_check(zip_path, out)
    audit = load(out / 'independent/runtime-output/audit_report.json')
    finish_report(index, batch, out, out, archive, validation, same, full, negatives, probes, audit)


def portable_check(zip_path, out):
    """Only the clean portable stage; callable for checkpoint/resume after a gate fix."""
    zip_path, out = Path(zip_path), Path(out)
    independent = out / 'independent'
    independent.mkdir()
    extracted = independent / 'unpacked'
    extracted.mkdir()
    with zipfile.ZipFile(zip_path) as z:
        for ref in z.namelist(): bm.resolve_ref(extracted, ref)
        z.extractall(extracted)
    bundle = extracted / 'bm25'
    wheels = independent / 'wheels'
    wheels.mkdir()
    cached = Path('staging/composition-bm25-independent-001/wheels')
    wheel_receipts = []
    for p in sorted(cached.glob('*.whl')):
        shutil.copyfile(p, wheels / p.name)
        wheel_receipts.append({'name': p.name, 'sha256': bm.digest(p.read_bytes())})
    if len(wheel_receipts) != 3: raise ValueError('Need the three pinned offline wheels')
    write_json(out / 'offline_wheels.json', wheel_receipts)
    venv = independent / 'venv-runtime'
    create = subprocess.run([sys.executable, '-B', '-m', 'venv', str(venv)], capture_output=True, text=True, encoding='utf8')
    (out / 'venv.log').write_text(create.stdout + create.stderr, encoding='utf8')
    if create.returncode: raise ValueError('Cannot create clean venv')
    python = venv / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    command = [str(python.resolve()), '-I', '-B', '-m', 'pip', 'install', '--no-cache-dir', '--no-index',
               '--find-links', str(wheels.resolve()), '-r', str((bundle / 'requirements-bm25.txt').resolve())]
    install = subprocess.run(command, capture_output=True, text=True, encoding='utf8')
    (out / 'pip-offline.log').write_text(install.stdout + install.stderr, encoding='utf8')
    write_json(out / 'pip-command.json', {'argv': command, 'exit_code': install.returncode})
    if install.returncode: raise ValueError('Offline pinned dependencies failed')
    harness = independent / 'harness'
    harness.mkdir()
    script = harness / 'audit.py'
    script.write_text(AUDIT, encoding='utf8')
    runtime = independent / 'runtime-output'
    runtime.mkdir()
    command = [str(python.resolve()), '-I', '-B', str(script.resolve()), str(bundle.resolve()), str(Path.cwd()), str(runtime.resolve())]
    execution = subprocess.run(command, cwd=bundle, capture_output=True, text=True, encoding='utf8', timeout=420)
    (out / 'portable.stdout.log').write_text(execution.stdout, encoding='utf8')
    (out / 'portable.stderr.log').write_text(execution.stderr, encoding='utf8')
    write_json(out / 'portable-command.json', {'argv': command, 'exit_code': execution.returncode})
    if execution.returncode: raise ValueError('Portable audit failed: ' + execution.stderr[-2400:])


def finish_report(index, batch, proof_root, out, archive, validation, same, full, negatives, probes, audit):
    runtime = out / 'independent/runtime-output'
    if (batch / 'ranking_and_response_signature.jsonl').read_bytes() != (runtime / 'batch/ranking_and_response_signature.jsonl').read_bytes():
        raise AssertionError('Portable ranking/response hashes differ')
    portable_full = load(runtime / 'full_read.json')
    if portable_full['responses_content_sha256'] != full['responses_content_sha256']:
        raise AssertionError('Portable full-read responses differ')
    report = {'state': 'BM25_BUILT_BATCH_READ_AND_PORTABLE_VERIFIED', 'validation': validation,
              'batch': load(batch / 'report.json'), 'zip': archive, 'replay_payload_files': len(same),
              'replay_rankings_and_responses_identical': True, 'zip_replay_identical': True,
              'full_read': {k: v for k, v in full.items() if k != 'response_hashes'},
              'private_mutations_rejected': len(negatives), 'input_error_probes_rejected': len(probes),
              'portable_commands': len(audit['commands']), 'portable_all_succeeded': audit['all_succeeded'],
              'portable_unexpected_denials': audit['unexpected_denials'], 'portable_foreign_modules': audit['foreign_modules'],
              'portable_distributions': audit['installed_distributions'], 'portable_expected_denials': len(audit['denials']),
              'portable_null_device_accesses': audit['null_device_accesses'],
              'portable_blocked_metadata_subprocesses': audit['blocked_metadata_subprocesses'],
              'index_ref': str(index), 'batch_ref': str(batch), 'earlier_checkpoints_ref': str(proof_root),
              'same_machine_windows_only': True, 'metrics': None, 'human_reviewer_events': 0, 'release_eligible': False}
    write_json(out / 'validation_report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def resume_portable(index, batch, previous, zip_path, output):
    """Retain old failed gate receipts; revalidate input and rerun only affected stage."""
    index, batch, previous, zip_path = map(Path, [index, batch, previous, zip_path])
    validation = bm.validate(index)
    same = load(previous / 'replay_payload.json')
    if not all(same.values()): raise ValueError('No successful deterministic replay checkpoint')
    if (batch / 'ranking_and_response_signature.jsonl').read_bytes() != (previous / 'replay_batch/ranking_and_response_signature.jsonl').read_bytes():
        raise ValueError('Replay/batch checkpoint mismatch')
    negatives = rows(previous / 'negative_checks.jsonl')
    probes = rows(previous / 'error_probes.jsonl')
    if len(negatives) != 12 or len(probes) != 9 or not all(x['rejected'] for x in negatives + probes):
        raise ValueError('Missing earlier successful negative/input checkpoints')
    sha = bm.digest(zip_path.read_bytes())
    if sha != bm.digest((previous / 'replay.zip').read_bytes()) or sha != zip_path.with_suffix('.zip.sha256').read_text().split()[0]:
        raise ValueError('ZIP/replay/SHA checkpoint mismatch')
    # Compare the ZIP itself with every byte of the actual bound index before
    # reusing it, rather than relying only on the previous stage's report.
    with zipfile.ZipFile(zip_path) as z:
        expected = {'bm25/' + p.relative_to(index).as_posix(): p for p in index.rglob('*') if p.is_file()}
        if set(z.namelist()) != set(expected) or any(z.read(ref) != p.read_bytes() for ref, p in expected.items()):
            raise ValueError('ZIP no longer equals pinned index bytes')
    out = bm.new_output(output)
    portable_check(zip_path, out)
    full = load(previous / 'full_read.main.report.json')
    archive = {'path': zip_path.as_posix(), 'sha256': sha, 'size_bytes': zip_path.stat().st_size}
    audit = load(out / 'independent/runtime-output/audit_report.json')
    finish_report(index, batch, previous, out, archive, validation, same, full, negatives, probes, audit)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['index', 'batch', 'output', 'zip']: p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--replay', type=Path)
    p.add_argument('--resume-portable', type=Path)
    a = p.parse_args()
    if a.resume_portable: resume_portable(a.index, a.batch, a.resume_portable, a.zip, a.output)
    elif a.replay: check(a.index, a.replay, a.batch, a.output, a.zip)
    else: p.error('Provide --replay or --resume-portable')


if __name__ == '__main__': main()
