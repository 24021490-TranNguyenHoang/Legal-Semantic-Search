"""Negative integration fixtures based on an isolated copy; never admitted as data."""
import argparse
import copy
from pathlib import Path
import shutil
import sys
import importlib.util
from src import seven_dataset_portable as portable
from src.experimental_dataset import load,rows,write_json,write_rows
from src.source_contracts import canonical,digest


def run(dataset,run_dir):
    out=Path(run_dir);out.mkdir(parents=True);root=out/'negative-fixture'
    shutil.copytree(dataset,root)
    spec=importlib.util.spec_from_file_location('bound_negative_test_reader',root/'validate_read.py')
    portable=importlib.util.module_from_spec(spec);spec.loader.exec_module(portable)
    write_json(out/'fixture_metadata.json',{'dataset_kind':'negative_integration_fixture','not_a_candidate':True,
        'source':str(dataset),'human_events_created':0,'purpose':'Mutated copies must be rejected even after resealing outer checksums'})
    controlled=['memberships.jsonl','additions/dependencies.jsonl','additions/form_dependencies.jsonl','additions/records.jsonl','additions/forms.jsonl','dataset_manifest.json','dataset_manifest.sha256']
    original={name:(root/name).read_bytes() for name in controlled};results=[]
    def reset():
        for ref,raw in original.items():(root/ref).write_bytes(raw)
    def reseal():
        m=load(root/'dataset_manifest.json');m['files']=portable.inventory(root);m['dataset_content_sha256']=digest(canonical(m['files']).encode())
        write_json(root/'dataset_manifest.json',m);(root/'dataset_manifest.sha256').write_text(digest((root/'dataset_manifest.json').read_bytes())+'\n',encoding='utf8')
    def member_scope():
        rr=rows(root/'memberships.jsonl');rr[0]['scope_proposal']='pending';write_rows(root/'memberships.jsonl',rr)
    def member_type():
        rr=rows(root/'memberships.jsonl');rr[0]['record_type']='form-retrieval.v1';write_rows(root/'memberships.jsonl',rr)
    def form_origin():
        rr=rows(root/'additions/forms.jsonl');rr[0]['visual_review']['origin']='human_review';write_rows(root/'additions/forms.jsonl',rr)
    def wrong_dependency():
        rr=rows(root/'additions/dependencies.jsonl');rr.pop(0);write_rows(root/'additions/dependencies.jsonl',rr)
    def missing_form():write_rows(root/'additions/form_dependencies.jsonl',[])
    def missing_transition():
        rr=rows(root/'additions/dependencies.jsonl');index=next(i for i,d in enumerate(rr) if d.get('dependency_role')=='snapshot_transition')
        rr.pop(index);write_rows(root/'additions/dependencies.jsonl',rr)
    def missing_rain_context():
        rr=rows(root/'additions/records.jsonl');r=next(r for r in rr if r['source_record'].get('source_graph')=='tt38');oldid=r['record_id'];s=r['source_record']
        s['contexts']=[c for c in s['contexts'] if c['unit_id']!=s['explicit_dependency_unit_id']]
        r['identity']['source_record_sha256']=digest(canonical(s).encode());r['record_id']='rv_'+digest(canonical(r['identity']).encode())
        write_rows(root/'additions/records.jsonl',rr);mm=rows(root/'memberships.jsonl')
        for m in mm:
            if m['record_id']==oldid:m['record_id']=r['record_id']
        write_rows(root/'memberships.jsonl',mm)
    cases=[('pending_scope',member_scope,'Membership false'),('wrong_type',member_type,'type/location'),
        ('invented_human_review',form_origin,'form status/origin'),('missing_dossier_reference',wrong_dependency,'required-read dependencies'),
        ('missing_form_reference',missing_form,'Application form dependency'),('missing_point_a_context',missing_rain_context,'point-a dependency missing'),
        ('missing_snapshot_transition',missing_transition,'Snapshot/transition required-read')]
    for name,mutate,expected in cases:
        reset();mutate();reseal();error=None
        try:portable.validate(root)
        except (ValueError,KeyError,OSError) as e:error=str(e)
        passed=error is not None and expected in error
        results.append({'case':name,'passed':passed,'expected_reason':expected,'actual_rejection':error})
        write_json(out/'checkpoint.json',results);print(name,passed,error,flush=True)
    reset()
    try:portable.validate(root,portable.CAPABILITIES-{'encoder-views.v1'})
    except ValueError as e:results.append({'case':'missing_encoder_view_capability','passed':'capability' in str(e),'actual_rejection':str(e)})
    else:results.append({'case':'missing_encoder_view_capability','passed':False})
    # Fixture is left restored; source candidate and all old artifacts were read-only.
    report={'cases':results,'all_rejected_as_expected':all(r['passed'] for r in results),'fixture_not_for_membership':True}
    write_json(out/'validation_report.json',report)
    return 0 if report['all_rejected_as_expected'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset-root',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True)
    a=p.parse_args();raise SystemExit(run(a.dataset_root,a.run_dir))
