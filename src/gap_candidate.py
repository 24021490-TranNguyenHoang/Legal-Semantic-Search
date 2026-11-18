"""Package the pinned session12 delta with immutable v5; no indexing or label transfer."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import zipfile

from src import gap_candidate_portable as runtime, development_gap_preview as preview
from src.experimental_dataset import write_json, write_rows
from src.pipeline_cli import staging_path

p = runtime.p
CONTRACT = Path('docs/design/Development_Gap_Candidate_v1.0.md')


def preflight(config):
    cfg = p.load(config)
    if cfg['policy_version'] != runtime.VERSION or cfg['dataset_version'] != runtime.DATASET:
        raise ValueError('Wrong candidate policy/version')
    for key, expected in [('base', runtime.BASE_SHA), ('preview', runtime.PREVIEW_SHA)]:
        entry = cfg['inputs'][key]
        if entry['sha256'] != expected or p.sha(Path(entry['ref']).read_bytes()) != expected:
            raise ValueError('Wrong pinned '+key)
    preview.validate(Path(cfg['inputs']['preview']['ref']))
    return cfg


def clone_state(old, root, manifest):
    c = object.__new__(runtime.Consumer)
    for key, value in old.__dict__.items():
        setattr(c, key, copy.deepcopy(value) if isinstance(value, (dict, list, set)) else value)
    c.baseline = old; c.root = root; c.manifest = manifest
    c.assets = {ref: {**e, 'package_ref': 'base/'+e['package_ref']} for ref, e in old.assets.items()}
    c.cache = {}; c.proof_cache = {}; c.checked = set(); c.validated = False
    c.red_id, c.age_id = runtime.merge(c, root/'preview')
    return c


def build(config, destination):
    cfg = preflight(config)
    root = staging_path(destination); root.mkdir(parents=True)
    base = Path(cfg['inputs']['base']['ref']).parent; prior = Path(cfg['inputs']['preview']['ref']).parent
    shutil.copytree(base, root/'base'); shutil.copytree(prior, root/'preview')
    (root/'runtime').mkdir(); (root/'evidence').mkdir()
    shutil.copyfile(base/'consumer.py', root/'runtime/base_consumer.py')
    shutil.copyfile(Path(runtime.__file__), root/'consumer.py')
    shutil.copyfile(CONTRACT, root/'CONTRACT.md'); shutil.copyfile(config,root/'config.snapshot.json')
    old = p.Consumer(root/'base'); old.validate()
    m = dict(policy_version=runtime.VERSION, dataset_version=runtime.DATASET, snapshot_date='2025-01-01',
        status='candidate', experimental=True, release_eligible=False, corpus_version=None, origin='agent_review',
        human_reviewer_events=0, source_status='pending', edition_status='pending', applicability='pending_review',
        scope_status='proposal_only', labels_transferred=False, base_manifest_sha256=runtime.BASE_SHA,
        preview_manifest_sha256=runtime.PREVIEW_SHA, required_capabilities=old.manifest['required_capabilities'],
        runtime=dict(python_minimum='3.11', dependencies=[], inference=False),
        locator_aliases=old.manifest['locator_aliases'], extraction_bindings=old.extractions,
        producer_sha256=p.sha(Path(__file__).read_bytes()), contract_sha256=p.sha(CONTRACT.read_bytes()))
    c = clone_state(old, root, m); m['asset_mounts']=c.assets; m['artifact_mounts']=list(c.artifacts.values()); m['counts']=c.counts()
    for ref, data in runtime.materialized(c).items(): write_rows(root/ref,data)
    write_rows(root/'source_usage.jsonl',c.source_usage())
    write_json(root/'lineage.json',dict(base_target_ids=sorted(old.targets), added_target_ids=[c.red_id],
        retained_target_closure_changed=[c.age_id], labels_transferred=False, offsets_transferred=False))
    pr = p.load(prior/'manifest.json'); reviewpath=Path(pr['inputs']['official_agent_review']['ref'])
    shutil.copyfile(reviewpath,root/'evidence/agent_review.json')
    review=p.load(reviewpath); mounts={}
    for entry in [dict(ref=review['pdf_ref'],sha256=review['evidence']['sha256']),*review['images']]:
        raw=Path(entry['ref']); h=p.sha(raw.read_bytes())
        if h!=entry['sha256']:raise ValueError('Evidence changed')
        existing=next((e['package_ref'] for e in c.assets.values() if e['sha256']==h),None)
        ref=existing or 'evidence/'+h
        if not existing and not (root/ref).exists():shutil.copyfile(raw,root/ref)
        mounts[entry['ref']]=dict(package_ref=ref,sha256=h)
    m['evidence_mounts']=mounts
    shutil.copyfile(reviewpath.parent/'comparison_notes.json',root/'evidence/comparison_notes.json')
    (root/'QUICKSTART.md').write_text(quickstart(c.red_id,c.age_id),encoding='utf8',newline='\n')
    # Same frozen checks as consumer; no pending label/metric read output is copied.
    c.validate_payload(); changes=runtime.delta(old,c)
    write_json(root/'delta.json',changes)
    write_rows(root/'disposition.jsonl',changes['frames'])
    write_json(root/'full_read.bindings.json',c.full_read())
    m['files']=p.inventory(root);m['dataset_content_sha256']=p.hashed(m['files'])
    write_json(root/'dataset_manifest.json',m)
    (root/'dataset_manifest.sha256').write_text(p.sha((root/'dataset_manifest.json').read_bytes())+'\n',encoding='ascii')
    result=runtime.Consumer(root).validate()
    return result


def quickstart(red,age):
    return f'''# Candidate v6 — experimental only

Snapshot 2025-01-01. Python >=3.11, stdlib only; no pip/model/cache/repository needed.
No shared download URL yet (chưa có URL chia sẻ). Obtain ZIP and .sha256 together.
Verify before extraction: `(Get-FileHash candidate.zip -Algorithm SHA256).Hash`
must match candidate.zip.sha256. Then `Expand-Archive candidate.zip clean`.
From clean/ (outputs outside candidate/):

```powershell
python -I -B candidate/consumer.py validate --dataset candidate
python -I -B candidate/consumer.py list --dataset candidate
python -I -B candidate/consumer.py read --dataset candidate --record-id {red}
python -I -B candidate/consumer.py read --dataset candidate --record-id {age}
python -I -B candidate/consumer.py full-read --dataset candidate --output all-records.jsonl
```

Base v5 is preserved inside base/; run the top-level consumer for v6. The original
138 target IDs/types/payloads/contexts are retained. One new red-light target is
added. Age target retains its ID but has a new read closure/binding. Do not reuse
accepted labels/qrels or old index with the new dataset binding. No new index is
included. Tables, whole-source records, form XXVI and encoder views keep their
types; views/supporting units are not independent targets. Read returns the full
required closure, not just the search projection. Structural ancestors are not
automatically context. delta.json includes before/after frame and response hashes.

Source/edition/applicability pending; scope proposal only; release=false. This is
not human-approved/legal-verified, nor evidence of improved retrieval. Original
paths are provenance labels; all proof access uses packaged assets. Code-point
offsets refer to the bound normalized extraction, context offsets to own fields.

Missing object/hash/type/proof/dependency => exit1: restore the exact ZIP, do not
edit the seal or substitute latest source. Existing output files are refused.
Do not write output/cache inside candidate/. No network or original workspace
fallback. Clean-directory verification is not a different-machine/OS test.
'''


def archive(root,destination):
    root=Path(root);runtime.Consumer(root).validate();out=staging_path(destination)
    if out.exists() or Path(str(out)+'.sha256').exists():raise ValueError('ZIP already exists')
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                info=zipfile.ZipInfo('candidate/'+path.relative_to(root).as_posix(),date_time=(1980,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,path.read_bytes())
    h=p.sha(out.read_bytes());Path(str(out)+'.sha256').write_text(h+'  '+out.name+'\n',encoding='ascii')
    return dict(zip_ref=out.as_posix(),sha256=h,size_bytes=out.stat().st_size)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['build','validate','zip'])
    parser.add_argument('--config');parser.add_argument('--run-dir',required=True);parser.add_argument('--zip-path');a=parser.parse_args()
    try:
        result=build(a.config,a.run_dir) if a.action=='build' else archive(a.run_dir,a.zip_path) if a.action=='zip' else runtime.Consumer(a.run_dir).validate()
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,TypeError,OSError,StopIteration) as exc:
        print('Candidate failed: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
