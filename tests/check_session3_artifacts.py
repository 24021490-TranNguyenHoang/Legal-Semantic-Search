"""Opt-in session3 artifact/negative/replay checks; does not admit a dataset."""
import argparse
import copy
from pathlib import Path
from collections import Counter

from src.membership_proposal import validate, check_memberships
from src.ingestion.table_owner_adapter import TableOwnerConsumer
from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import digest
from src.pipeline_cli import staging_path
from src.assessment_evidence import now, seal


def check(config, proposal, replay, output):
    result = validate(config, proposal)
    cfg=load(config); source={r['source_id']:r for r in rows(proposal/'source_selection.jsonl')}
    proposals=rows(proposal/'membership.proposals.jsonl'); dependencies={d['dependency_id']:d for d in rows(proposal/'dependencies.jsonl')}
    paired = [p for p in proposals if p['law_id']=='35/2024/TT-BGTVT' and any(p['canonical_path'].endswith(s) for s in ['article:32/clause:6/point:a','article:32/clause:6/point:b'])]
    if len(paired)!=2:raise ValueError('Missing baseline/exception pair')
    for p in paired:
        peer=next(x['unit_id']for x in paired if x['unit_id']!=p['unit_id'])
        if not any(dependencies[did]['kind']=='paired_exception_read' and peer in dependencies[did]['unit_ids'] for did in p['required_dependency_ids']):
            raise ValueError('Baseline/exception required read missing')
    selected=next(p for p in proposals if p['membership']=='proposed_include' and p['required_dependency_ids'])
    rejected=[]
    for case in ['source','proof','missing_dependency','old_id','duplicate_branch','capability','view','qcvn_conflict']:
        altered=copy.deepcopy(selected); own=[altered]; deps=copy.deepcopy(dependencies); capabilities={'chunk.v1','table-retrieval.v1','source-retrieval.v1'}
        if case=='source':altered['source_version_sha256']='WRONG'
        if case=='proof':altered['proof_source_hashes']=['WRONG']
        if case=='missing_dependency':deps.pop(altered['required_dependency_ids'][0])
        if case=='old_id':deps[altered['required_dependency_ids'][0]]['unit_ids']=['UNRESOLVED_OLD_ID']
        if case=='duplicate_branch':own.append({**altered,'unit_id':'OTHER_HTML_BRANCH','record_id':'OTHER_HTML_RECORD'})
        if case=='capability':capabilities=set()
        if case=='view':altered['independent_encoder_view']=True
        if case=='qcvn_conflict':
            altered.update(source_id='SRC-006',source_version_sha256=source['SRC-006']['graph_manifest_sha256'],source_conflict=True)
        try:check_memberships(own,source,deps,capabilities,{p['unit_id'] for p in proposals})
        except ValueError as exc:rejected.append({'case':case,'rejected':True,'reason':str(exc)})
        else:raise ValueError('Negative accepted: '+case)
    consumer=TableOwnerConsumer(cfg['table_owner']); original=consumer.records[0]
    for case in ['header','cells','dependency','proof']:
        altered=copy.deepcopy(original)
        if case=='header':altered['bindings'][0]['header_cell_ids']=[]
        if case=='cells':altered['cells']=[]
        if case=='dependency':altered['required_dependencies']=[]
        if case=='proof':altered['cells'][0]['source_slices'][0]['quote_sha256']='0'*64
        try:consumer.validate_record(altered)
        except ValueError as exc:rejected.append({'case':'table_'+case,'rejected':True,'reason':str(exc)})
        else:raise ValueError('Table negative accepted: '+case)
    changed=[x for x in consumer.crosswalk if x['old_record_id']!=x['new_record_id']]
    if len(changed)!=1:raise ValueError('Unexpected TT35 identity change')
    a7=next(r for r in consumer.records if '/article:7/' in r['owner_path'])
    read=consumer.read(a7['record_id']); annexes=[d['annex']['literal_marker'] for d in read['loaded_required_dependencies'] if 'annex' in d]
    if annexes!=['II']:raise ValueError('A7 required read does not contain correct AnnexII')
    equality={}
    if replay:
        for path in sorted(proposal.rglob('*')):
            if path.is_file() and (path.suffix in ['.jsonl','.csv'] or path.parent.name=='table_owner_reads'):
                ref=path.relative_to(proposal);equality[ref.as_posix()]=digest(path.read_bytes())==digest((replay/ref).read_bytes())
        if not all(equality.values()):raise ValueError('Replay differs')
    baseline=load(cfg['baseline_ref']);changed_files=[p for p,h in baseline.items() if not Path(p).is_file() or digest(Path(p).read_bytes())!=h]
    unexpected=[p for p in changed_files if p not in ['docs/progress/STATUS.md','docs/ingestion.md']]
    if unexpected:raise ValueError({'protected_changes':unexpected})
    out=staging_path(output);out.mkdir(parents=True);write_rows(out/'negative_checks.jsonl',rejected)
    write_json(out/'replay.json',equality)
    summary={**result,'negative_cases_rejected':len(rejected),'replay_payloads':len(equality),
             'protected_files_checked':len(baseline),'unexpected_changes':unexpected,'authorized_doc_changes':changed_files,
             'table_records_changed':len(changed),'a7_effective_annexes':annexes,
             'manual_scope_reviews':len(cfg['manual_reviews']), 'scope_methods':dict(Counter(p['review_method']for p in proposals)),
             'v3_delta':dict(Counter(r['change']for r in rows(proposal/'v3.comparison.jsonl'))),
             'v4_delta':dict(Counter(r['change']for r in rows(proposal/'v4.comparison.jsonl'))),
             'origin':'agent_review','human_reviewer_events':0,'release_eligible':False}
    write_json(out/'validation_report.json',summary);seal(out,{'manifest_type':'source-session3-checks.v1','built_at':now(),'code_sha256':digest(Path(__file__).read_bytes())})
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['config','proposal','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--replay',type=Path);a=p.parse_args();print(check(a.config,a.proposal,a.replay,a.output))


if __name__=='__main__':main()
