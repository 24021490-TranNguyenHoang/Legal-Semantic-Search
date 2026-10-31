"""Build a bounded candidate/ZIP from pinned session4 reads; never builds an index."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import zipfile

from src import source_session4 as s4
from src import subset_candidate_portable as portable
from src.assessment_evidence import check_files
from src.experimental_dataset import load, rows, write_json, write_rows
from src.pipeline_cli import staging_path
from src.source_contracts import digest, canonical


def preflight(config):
    cfg=load(config)
    if cfg['policy_version']!=portable.VERSION or cfg['snapshot_date']!='2025-01-01':raise ValueError('Wrong policy/snapshot')
    for ref,h in cfg['input_hashes'].items():
        if digest(Path(ref).read_bytes())!=h:raise ValueError('Pinned input changed: '+ref)
    for ref in [cfg['session4_run'],cfg['session4_checks'],cfg['source_proposal_run']]:check_files(Path(ref)/'manifest.json')
    return cfg


class Assets:
    def __init__(self, root):
        self.root=root;self.mounts={};(root/'objects').mkdir()

    def add(self, ref, expected=None):
        ref=Path(ref).as_posix()
        if ref in self.mounts:
            if expected and self.mounts[ref]['sha256']!=expected:raise ValueError('Asset expected hash differs')
            return self.mounts[ref]
        p=Path(ref)
        if not p.is_file():raise ValueError('Required asset missing: '+ref)
        h=digest(p.read_bytes())
        if expected and h!=expected:raise ValueError('Evidence/asset hash mismatch: '+ref)
        target='objects/'+h
        if not (self.root/target).exists():shutil.copyfile(p,self.root/target)
        row={'package_ref':target,'sha256':h,'size_bytes':p.stat().st_size}
        self.mounts[ref]=row
        return row


def node_id(u):return u.get('unit_id',u.get('region_unit_id'))


def gather_graph(selections, selected):
    by={};owner={};spans=[];manifests={}
    for s in selections:
        root=Path(s['graph_run']);check_files(root/'manifest.json')
        if digest((root/'manifest.json').read_bytes())!=s['graph_manifest_sha256']:raise ValueError('Source graph differs')
        manifests[s['source_id']]=root/'manifest.json'
        for u in rows(root/s['graph_units_file']):
            if u.get('law_id',s['law_id'])!=s['law_id']:continue
            uid=node_id(u)
            if uid in by:raise ValueError('Duplicate selected source graph node')
            by[uid]=u;owner[uid]=s
        if s['source_id']!='SRC-006':
            spans += [p for p in rows(root/'source_spans.pending.jsonl') if p['unit_id'] in by and owner[p['unit_id']]['source_id']==s['source_id']]
    wanted=set(selected)
    for uid in list(selected):
        visited=set()
        while uid:
            if uid not in by or uid in visited:raise ValueError('Missing graph node or cycle')
            wanted.add(uid);visited.add(uid);u=by[uid];uid=u.get('parent_unit_id',u.get('parent_region_unit_id'))
    nodes=[{'unit_id':uid,'source_id':owner[uid]['source_id'],'law_id':owner[uid]['law_id'],
            'graph_model':'unit.v1'if 'unit_id'in by[uid]else 'qcvn-source-rule-graph.v1.1',
            'role':'selected_read'if uid in selected else 'structural_only','unit':by[uid]}for uid in sorted(wanted)]
    return nodes,[p for p in spans if p['unit_id']in wanted],manifests


def collect_aliases(value, aliases):
    if isinstance(value,str) and value.startswith(('[','{')):
        try:collect_aliases(json.loads(value),aliases)
        except (ValueError,TypeError):pass
    elif isinstance(value,list):
        for v in value:collect_aliases(v,aliases)
    elif isinstance(value,dict):
        if 'extraction_id'in value:
            a=aliases[value['extraction_id']]
            for key,role in [('raw_ref','raw'),('raw_file_ref','raw'),('text_ref','text'),('trace_ref','trace'),('identity_ref','identity')]:
                if value.get(key) is not None:a[role].add(value[key])
        for v in value.values():collect_aliases(v,aliases)


def evidence(root, assets, unit_ids, pool):
    """Keep selected existing observations, never turn them into assessments."""
    refs={pool[u].get('applicability_evidence_ref')for u in unit_ids}-{None};rules=[];findings=[];catalog=[];links=[]
    for ref in sorted(refs):
        base=Path(ref).parent
        selected=[r for r in rows(ref)if set(r['unit_ids']) & set(unit_ids)]
        rules.extend({'original_ref':ref,'original_file_sha256':digest(Path(ref).read_bytes()),'rule':r}for r in selected)
        fids={r['finding_id']for r in selected};eids={e for r in selected for e in r['evidence_ids']}
        chosen=[f for f in rows(base/'findings.pending.jsonl')if f['finding_id']in fids]
        for f in chosen:
            rawtext=base/'pages'/f['text_ref']
            assets.add(rawtext,f['text_sha256'])
            findings.append(f);links.append({'kind':'finding_text','id':f['finding_id'],'asset_ref':rawtext.as_posix()})
        for ev in rows(base/'catalog.jsonl'):
            if ev['evidence_id']not in eids:continue
            raw=base.parent/ev['artifact_ref'];assets.add(raw,ev['sha256']);catalog.append(ev)
            links.append({'kind':'evidence_raw','id':ev['evidence_id'],'asset_ref':raw.as_posix()})
    # Corrected DOCX is immutable. Existing correction evidence explains its
    # derivation; no correction or parsing is run in this builder.
    corrections=rows(Path('staging/nd168-docx-session2-001/corrections.jsonl'))
    for c in corrections:assets.add(c['evidence_image_ref'],c['evidence_image_sha256'])
    write_rows(root/'evidence/nd168.corrections.jsonl',corrections)
    write_rows(root/'evidence/date_rules.pending.jsonl',rules)
    write_rows(root/'evidence/findings.pending.jsonl',findings);write_rows(root/'evidence/catalog.jsonl',catalog)
    write_rows(root/'evidence/links.jsonl',links)


def build(config, run_dir):
    cfg=preflight(config);prior=Path(cfg['session4_run']);proposal=Path(cfg['source_proposal_run'])
    root=staging_path(run_dir);root.mkdir(parents=True)
    for folder in ['inputs/session4','runtime','metadata','evidence']: (root/folder).mkdir(parents=True,exist_ok=True)
    assets=Assets(root);plan=rows(prior/'packaging_plan.jsonl');targets={p['record_id']:p for p in plan if p['role']=='target'}
    if len(targets)!=sum(p['role']=='target'for p in plan):raise ValueError('Duplicate target membership')
    frames=rows(prior/'base116.reads.jsonl')+rows(prior/'nd168.reads.jsonl');by=portable.unique(frames,'record_id','target read')
    if set(by)!=set(targets):raise ValueError('Plan/frame membership mismatch; admission halted')
    support={p['unit_id']:p for p in plan if p['record_type']=='source-unit-read.v1'}
    support_records={p['record_id']:p for p in plan if p['role']=='supporting'and p['record_type']!='source-unit-read.v1'}
    forms=rows(prior/'supporting_records.reads.jsonl');formby=portable.unique(forms,'record_id','supporting form')
    selected={p['unit_id']for p in targets.values()}|set(support)
    selections=rows(proposal/'source_selection.jsonl');pool={p['unit_id']:p for p in rows(proposal/'membership.proposals.jsonl')}
    nodes,spans,graph_manifests=gather_graph(selections,selected)
    write_rows(root/'graph_nodes.jsonl',nodes);write_rows(root/'source_spans.jsonl',spans)
    write_rows(root/'unit_proposals.jsonl',[pool[n['unit_id']]for n in nodes])
    shutil.copyfile(proposal/'source_selection.jsonl',root/'source_selection.jsonl')
    catalog=s4.Catalog(selections);native=[p for f in [*frames,*forms]for p in f['native_proofs']]
    native += [catalog.proof(s,'graph:'+s['unit_id']+':'+s['field_name'])for s in spans]
    native += [catalog.proof(p,'region:'+n['unit_id'])for n in nodes if n['graph_model']!='unit.v1'for p in n['unit']['source_proofs']]
    used_eids={p['extraction_id']for p in native}
    bindings={eid:catalog.entries[eid]for eid in sorted(used_eids)}
    for b in bindings.values():
        for key in ['raw_ref','text_ref','trace_ref','identity_ref']:
            if b[key]:assets.add(b[key],b.get('raw_sha256')if key=='raw_ref'else b.get('text_sha256')if key=='text_ref'else None)
    aliases=defaultdict(lambda:{k:set()for k in ['raw','text','trace','identity']})
    for eid,b in bindings.items():
        for key,role in [('raw_ref','raw'),('text_ref','text'),('trace_ref','trace'),('identity_ref','identity')]:
            if b[key]:aliases[eid][role].add(b[key])
    collect_aliases([*frames,*forms,nodes],aliases)
    input_files={}
    for name in ['packaging_plan.jsonl','packaging_plan.csv','base116.reads.jsonl','nd168.reads.jsonl','supporting_records.reads.jsonl']:
        ref='inputs/session4/'+name;shutil.copyfile(prior/name,root/ref);input_files[ref]=name
    shutil.copyfile(prior/'manifest.json',root/'inputs/session4.manifest.json')
    shutil.copyfile(Path(cfg['session4_checks'])/'manifest.json',root/'inputs/session4_checks.manifest.json')
    shutil.copyfile(proposal/'manifest.json',root/'inputs/session3.manifest.json')
    mounts=[];original_cache={}
    for p in [*targets.values(),*support_records.values()]:
        ref=Path(p['source_artifact']);absolute=prior/ref if p.get('artifact_base')=='this_run'else ref
        if absolute not in original_cache:original_cache[absolute]=rows(absolute)
        record=next(r.get('record',r)for r in original_cache[absolute]if r.get('chunk_id',r.get('retrieval_id',r.get('record_id')))==p['record_id'])
        actual=(by if p['role']=='target'else formby)[p['record_id']]['record']
        if record!=actual or portable.hashed(record)!=p['payload_sha256']:raise ValueError('Source artifact/plan payload mismatch: '+p['record_id'])
        mounts.append({'record_id':p['record_id'],'original_ref':p['source_artifact'],'original_base':p.get('artifact_base','workspace'),
                       'original_file_sha256':digest(absolute.read_bytes()),'package_frames_ref':'inputs/session4/nd168.reads.jsonl'if p.get('artifact_base')=='this_run'else
                       'inputs/session4/supporting_records.reads.jsonl'if p['role']=='supporting'else 'inputs/session4/base116.reads.jsonl',
                       'payload_sha256':portable.hashed(record)})
    # Preserve exact source metadata only for files/extractions actually needed.
    file_ids={b['file_id']for b in bindings.values()};files=[];documents=[];extractions=[]
    used_sources={n['source_id']for n in nodes}
    for s in selections:
        if s['source_id']not in used_sources:continue
        eroot=Path(s['extraction_run']);source=eroot/'source_snapshot'if (eroot/'source_snapshot').is_dir()else eroot
        files += [f for f in rows(source/'files.pending.jsonl')if f['file_id']in file_ids]
        if (source/'documents.pending.jsonl').exists():documents += [d for d in rows(source/'documents.pending.jsonl')if d['law_id']==s['law_id']]
        raw=Path(s['graph_extraction_run']);extractions += [e for e in rows(raw/'extractions.pending.jsonl')if e['extraction']['extraction_id']in used_eids]
        # Native TT35/TT38 layout identities may be distinct from grammar view.
    for raw in [Path('staging/tt35-full-layout-001'),Path('staging/tt38-full-layout-001')]:
        extractions += [e for e in rows(raw/'extractions.pending.jsonl')if e['extraction']['extraction_id']in used_eids]
    def dedupe(values,key):
        out={}
        for v in values:
            k=key(v)
            if k in out and out[k]!=v:raise ValueError('Conflicting source metadata '+k)
            out[k]=v
        return [out[k]for k in sorted(out)]
    write_rows(root/'metadata/files.pending.jsonl',dedupe(files,lambda f:f['file_id']))
    write_rows(root/'metadata/documents.pending.jsonl',dedupe(documents,lambda d:d['law_id']))
    write_rows(root/'metadata/extractions.pending.jsonl',dedupe(extractions,lambda e:e['extraction']['extraction_id']))
    evidence(root,assets,selected,pool)
    source3_map=rows(proposal/'nd168.legacy_branch_mapping.jsonl');expanded=rows(Path(cfg['session4_checks'])/'nd168.disposition.expanded.jsonl')
    lineage=[]
    for d in expanded:
        if d['new_record_id']in targets:
            lineage.append({k:d[k]for k in ['old_record_id','old_unit_id','unit_id','new_record_id','identity_fields_changed','lineage','assessment_qrels_or_offsets_transferred']})
    write_rows(root/'nd168.lineage.jsonl',lineage)
    blocked=rows(prior/'nd168.disposition.jsonl');a28=load(prior/'a28.closure.json')
    write_json(root/'exclusions.json',{'unit_ids':[d['unit_id']for d in blocked if d['status']=='blocked']+[a28['unit_id']],
        'record_ids':[d['old_record_id']for d in blocked], 'reasons':['Unresolved DOCX A16K2 scope','A28K2 required-read incomplete',
        'XXIII/course tables not in selected closure','QCVN conflicting captions/recovery/OCR regions not selected'],
        'raw_assets_may_contain_unselected_content':True})
    usage=[]
    for s in selections:
        target_ids={p['unit_id']for p in targets.values()if pool[p['unit_id']]['source_id']==s['source_id']}
        support_ids={u for u in support if pool[u]['source_id']==s['source_id']}
        usage.append({'source_id':s['source_id'],'law_id':s['law_id'],'target_records':sum(pool[p['unit_id']]['source_id']==s['source_id']for p in targets.values()),
                      'target_unit_ids':len(target_ids),'supporting_unit_reads':len(support_ids),'graph_nodes':sum(n['source_id']==s['source_id']for n in nodes),
                      'raw_file_ids_packaged':sorted({b['file_id']for b in bindings.values()if b['raw_sha256']in {f['sha256']for f in s['files']}}),
                      'source_status':s['source_status'],'edition_status':s['edition_status'],'applicability':s['applicability']})
    write_rows(root/'source_usage.jsonl',usage)
    shutil.copyfile(Path(portable.__file__),root/'consumer.py')
    shutil.copyfile(Path(s4.reader.__file__),root/'runtime/frame_reader.py')
    shutil.copyfile(Path('src/circular_dataset_portable.py'),root/'runtime/graph_helpers.py')
    (root/'requirements-runtime.txt').write_text('# CPython >=3.11. Runtime uses only the Python standard library.\n',encoding='utf8')
    examples=[next(r for r,m in targets.items() if m['law_id']=='168/2024/NĐ-CP'),
              next(r for r,m in targets.items() if m['record_type']=='table-retrieval.v1'),
              next(r for r,m in targets.items() if m['record_type']=='source-retrieval.v1'),
              next(r for r in targets if any(d.get('record_id')for d in by[r]['dependencies']))]
    write_json(root/'example_record_ids.json',examples)
    (root/'QUICKSTART.md').write_text(quickstart(cfg,examples),encoding='utf8')
    draft=SimpleNamespace(targets=targets,support=support,support_records=support_records,nodes={n['unit_id']:n for n in nodes},frames=by,sources={s['source_id']:s for s in selections},spans=spans,extractions=bindings)
    files_inventory=portable.inventory(root)
    manifest={'policy_version':portable.VERSION,'dataset_version':cfg['dataset_version'],'snapshot_date':'2025-01-01','status':'candidate','experimental':True,
              'release_eligible':False,'corpus_version':None,'origin':'agent_review','human_reviewer_events':0,
              'source_status':'pending','edition_status':'pending','scope_status':'proposal_only','applicability':'pending_review',
              'required_capabilities':sorted(portable.CAPABILITIES),'runtime':{'python_minimum':'3.11','dependencies':[],'inference':False},
              'plan_ref':'inputs/session4/packaging_plan.jsonl','target_frames_refs':['inputs/session4/base116.reads.jsonl','inputs/session4/nd168.reads.jsonl'],
              'supporting_frames_ref':'inputs/session4/supporting_records.reads.jsonl','input_files':input_files,
              'input_binding':{'session4_manifest_ref':'inputs/session4.manifest.json','session4_manifest_sha256':digest((prior/'manifest.json').read_bytes()),
                'session4_checks_manifest_sha256':digest((Path(cfg['session4_checks'])/'manifest.json').read_bytes()),
                'session3_manifest_sha256':digest((proposal/'manifest.json').read_bytes()),'config_sha256':digest(Path(config).read_bytes())},
              'asset_mounts':assets.mounts,'extraction_bindings':bindings,'artifact_mounts':mounts,
              'locator_aliases':{eid:{k:sorted(v)for k,v in roles.items()}for eid,roles in aliases.items()if eid in used_eids},
              'counts':portable.Consumer.counts(draft),'files':files_inventory,'dataset_content_sha256':portable.hashed(files_inventory)}
    write_json(root/'dataset_manifest.json',manifest)
    (root/'dataset_manifest.sha256').write_text(digest((root/'dataset_manifest.json').read_bytes())+'\n',encoding='ascii')
    consumer=portable.Consumer(root);result=consumer.validate();consumer.full_read()
    return result


def quickstart(cfg,examples):
    text='''# Experimental subset candidate — not a verified serving corpus

Snapshot2025-01-01. Scope proposal only; source/edition/applicability pending.
No human decision, accepted label, corpus activation, index, embedding or model.
Seven sources in inventory; see source_usage.jsonl for actual subset coverage.
Full raw files may contain content beyond the admitted records.

From a new directory after extracting the ZIP (CPython3.11+):

```powershell
python -m venv .venv-runtime
.\\.venv-runtime\\Scripts\\python.exe -I -B candidate/consumer.py validate --dataset candidate
.\\.venv-runtime\\Scripts\\python.exe -I -B candidate/consumer.py list --dataset candidate
.\\.venv-runtime\\Scripts\\python.exe -I -B candidate/consumer.py read --dataset candidate --record-id RECORD_ID_FROM_LIST
.\\.venv-runtime\\Scripts\\python.exe -I -B candidate/consumer.py full-read --dataset candidate --output all-records.read.jsonl
```

The ZIP root folder is candidate/. No pip packages or model/cache access needed.
Run only against the extracted immutable directory. Output files must be outside
candidate/ and new; missing asset, wrong hash/type/ID/offset/dependency or capability
fails with exit1. No fallback fixture or original-workspace lookup.

Consumer responses contain unchanged typed record, context, source proofs with
original_locator and package_locator, full required unit reads and supporting
form record. Whole-source content and all encoder views stay in one target.
Table original/cells/header and derived search text remain separate. XXVI is
supporting layout only, not a retrieval target. Structural ancestors are stored
for relationships and identity, not automatically served as context/targets.

Extraction offsets: NFC/LF Unicode code points [start,end). Context offsets:
relative to own field. Encoder-view offsets: relative to text_for_search. Do not
swap them or reinterpret PDF page numbers as printed pages.

asset_mounts resolve original labels to content-addressed objects. Artifact
mounts resolve historical/this_run record references by record ID without
opening the old JSONL paths. Original payload paths are provenance labels.
Date evidence/correction observations are pending, not assessments. DOCX layout
render remains unverified on the build machine. Technical validation is not
legal verification or retrieval evaluation. See membership/closure counts in
dataset_manifest.json; this is not complete coverage of all seven sources.
'''
    text+='\n## Actual packaged examples\n\nNo synthetic law content: these IDs come from the pinned plan. The last example\nrequires the supporting XXVI form. Redirect responses outside candidate/.\n\n```powershell\n'
    for i,rid in enumerate(examples,1):
        text+=f'.\\.venv-runtime\\Scripts\\python.exe -I -B candidate/consumer.py read --dataset candidate --record-id {rid} > example-{i}.json\n'
    return text+'```\n\nPayload XXVI retains historic scope_proposal=included; its role in this bundle\nis supporting only. Historical adapter blocker strings remain untouched inside\npayloads; technical_admission describes the new validated package adapter.\n'


def archive(dataset, destination):
    dataset=Path(dataset);destination=staging_path(destination)
    if destination.exists() or Path(str(destination)+'.sha256').exists():raise ValueError('Archive/SHA already exists')
    portable.Consumer(dataset).validate()
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for p in sorted(dataset.rglob('*'),key=lambda p:p.relative_to(dataset).as_posix()):
            if not p.is_file():continue
            info=zipfile.ZipInfo('candidate/'+p.relative_to(dataset).as_posix(),date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
    h=digest(destination.read_bytes());Path(str(destination)+'.sha256').write_text(h+'  '+destination.name+'\n',encoding='ascii')
    return {'zip_ref':destination.as_posix(),'sha256':h,'size_bytes':destination.stat().st_size}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','zip','validate'])
    p.add_argument('--config',type=Path);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--zip-path',type=Path)
    a=p.parse_args()
    try:
        result=build(a.config,a.run_dir)if a.action=='build'else archive(a.run_dir,a.zip_path)if a.action=='zip'else portable.Consumer(a.run_dir).validate()
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,OSError,TypeError,StopIteration)as exc:
        print('Candidate build/validation failed: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
