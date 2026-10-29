"""Opt-in real artifact, negative, isolated-read and preservation checks; no admission."""
import argparse
import copy
from pathlib import Path
import shutil
import subprocess
import sys

from src import source_session4 as s
from src.assessment_evidence import seal,now
from src.experimental_dataset import load,rows,write_json,write_rows
from src.ingestion.completion_records import form_identity
from src.ingestion.table_owner_adapter import TableOwnerConsumer
from src.pipeline_cli import staging_path


ISOLATED = r'''
import sys,json,runpy
from pathlib import Path
root=Path(sys.argv[1]).resolve();original=Path(sys.argv[2]).resolve();stdlib=Path(sys.base_prefix).resolve();denied=[]
def audit(event,args):
 if event!='open' or isinstance(args[0],int):return
 p=Path(args[0]).resolve()
 if p.is_relative_to(root) or p.is_relative_to(stdlib):return
 denied.append(str(p));raise PermissionError('Isolated probe denied outside root: '+str(p))
sys.addaudithook(audit)
try:(original/'AGENTS.md').read_bytes()
except PermissionError:pass
else:raise AssertionError('Original workspace was readable')
module=runpy.run_path(str(root/'reader.py'));manifest=module['load'](root/'probe_manifest.json')
for entry in manifest['files']:
 if module['sha'](module['resolve'](root,entry['ref']).read_bytes())!=entry['sha256']:raise ValueError('Copied file checksum mismatch')
checks=[]
for rid,ref in manifest['reads'].items():
 checks.append(module['check'](root,module['load'](root/ref),manifest['capabilities']))
print(json.dumps({'technical_valid':True,'reads':checks,'original_workspace_denied':True,'denied_count':len(denied),'same_machine':True},ensure_ascii=False))
'''


def review_pack(root,out,cfg,plan):
    """Readable projections of existing proofs; no new labels/units/source text."""
    prior=Path(cfg['proposal_run']);pool={p['unit_id']:p for p in rows(prior/'membership.proposals.jsonl')}
    inv={p['record_id']:p for p in rows(prior/'record_inventory.jsonl')};mapping=rows(prior/'nd168.legacy_branch_mapping.jsonl')
    new={f['record_id']:f for f in rows(root/'nd168.reads.jsonl')};cache={};expanded=[]
    s3=load(cfg['source_config']);oldcontexts=rows(Path(s3['v3'])/'contexts.jsonl')
    for d in rows(root/'nd168.disposition.jsonl'):
        desc=inv[d['old_record_id']];ref=Path(desc['artifact_ref'])
        if ref not in cache:cache[ref]=rows(ref)
        old=next(r for r in cache[ref]if r.get('chunk_id',r.get('record_id'))==d['old_record_id'])
        f=new.get(d['new_record_id']);u=pool[d['unit_id']]
        lineage=[m for m in mapping if m['old_unit_id']==desc['old_unit_id']and m['new_unit_id']==u['unit_id']]
        if not lineage:raise ValueError('Missing pinned branch lineage for old record')
        changes=[]
        if f:
            nc=f['record'];cs=[c for c in oldcontexts if c['chunk_id']==d['old_record_id']]
            if not cs and old.get('context_text'):raise ValueError('Old context identity evidence absent')
            oc=s.chunk_preview.chunk_identity(old,cs);ni=s.chunk_preview.chunk_identity(nc,f['contexts'])
            changes=[k for k in oc if oc[k]!=ni[k]]
        expanded.append({**d,'old_unit_id':desc['old_unit_id'],'old_record_artifact':desc['artifact_ref'],
                         'old_record_payload_sha256':s.hashed(old),'lineage':lineage,'citation_path':u['citation_path'],
                         'title':u['title'],'text_original':u['text_original'],
                         'new_source_proofs':f['native_proofs']if f else u['source_spans'],
                         'new_contexts':f['contexts']if f else [],'identity_fields_changed':changes,
                         'source_status':u['source_status'],'edition_status':u['edition_status'],'applicability':u['applicability']})
    write_rows(out/'nd168.disposition.expanded.jsonl',expanded)
    from src.membership_proposal import csv_export
    csv_export(out/'nd168.disposition.expanded.csv',expanded,['old_record_id','old_unit_id','unit_id','citation_path','scope','role','new_record_id','status','reason','tokens','unknown_tokens','identity_fields_changed'])
    md=['# NĐ168 — đủ 27 record cũ; agent_review / pending',
        '22 record mới là target proposal; năm A16K2 chưa có scope kết luận trên nguồn DOCX. Không chuyển nhãn HTML, assessment hoặc qrels.']
    for d in expanded:
        md += ['## '+d['citation_path'],f"**{d['status']}** — {d['reason']}",
               f"Old record: `{d['old_record_id']}`\n\nOld unit: `{d['old_unit_id']}`\n\nNew unit: `{d['unit_id']}`\n\nNew record: `{d['new_record_id']}`",
               'Scope/role (proposal): '+d['scope']+' / '+d['role'],d['text_original'],
               'Context theo thứ tự:\n'+ '\n\n'.join(c['text_original']for c in d['new_contexts']),
               'Identity đổi: '+str(d['identity_fields_changed']),
               'Required-read units: '+str(len(d.get('required_unit_ids',[])))+'; danh sách đầy đủ trong expanded JSONL và nd168.reads.jsonl.',
               'Source spans: '+str([(p.get('locator',p.get('locator_json')),p['char_start'],p['char_end'])for p in d['new_source_proofs']if p.get('use')=='target'])]
    (out/'ND168_Disposition.md').write_text('\n\n'.join(md),encoding='utf8')
    form=load(root/'form_xxiii.preview.json');a=load(root/'a28.closure.json')
    md=['# Mẫu XXIII / closure A28K2 — agent_review, chưa verified',
        'Nguồn: data/raw/35-bgtvt-kem.pdf, PDF trang127 (không có số trang in quan sát được). Trang126 AnnexXXII;128 AnnexXXIV.',
        'Đã xem ảnh toàn trang và so nguyên văn/nhãn/trường trống/chữ ký/hướng dẫn. Không có bảng vật lý; không dựng cell giả.',
        '**Mẫu: ready kỹ thuật; A28K2: blocked required-read.**',
        '| Dòng | Nguyên văn | Extraction offsets | Bbox PDF (top origin) |','|---|---|---|---|']
    for i,f in enumerate(form['form_fields'],1):
        p=f['source_proof'];md.append(f"|{i}|{f['text_original'].replace('|','/')}|{p['char_start']}:{p['char_end']}|{p.get('bbox_pdf_top_origin')}|")
    md += ['## Target và điều kiện hoàn thành',* [r['text_original']for r in rows(root/'a28.chunks.jsonl')],
           'Nguồn A28K2 in đúng “được cơ đào tạo”; giữ nguyên, không tự thêm “sở”.',
           'Sáu programme owners và whole-read có tại a28_table_reads/. A7 dẫn Phụ lục II. Chỉ chọn các chương trình theo hạng GPLX; không biến thành sáu target.',
           'Completion units (nguyên văn, không tự mở mọi dẫn chiếu):']
    for u in sorted(a['completion_units'],key=lambda u:u['canonical_path']):md += ['### '+u['canonical_path'],u['text_original']]
    md += ['## Blocker còn lại',a['reason'],
           '| Phụ lục | Trang PDF | Dòng native | Bảng native | Trạng thái |','|---|---|---|---|---|']
    for x in a['required_unchecked_annexes']:md.append(f"|{x['literal_marker']}|{x['page_start']}–{x['page_end']}|{len(x['line_region_ids'])}|{len(x['table_ids'])}|Chưa đủ kiểm layout/nội dung/whole-read|")
    md += ['49 trang trên đã có inventory/native extraction, không được gọi là đã đọc rà. Không thêm A28K2 vào plan; XXIII không là target. A21K4c/A46K2 ngoài target.']
    (out/'TT35_XXIII_A28_Review.md').write_text('\n\n'.join(md),encoding='utf8')
    md=['# Packaging plan — chỉ đề xuất, chưa tạo dataset',
        'Binding theo run009 và '+root.as_posix()+'. Scope chỉ proposal; source/edition/applicability pending; human review=null.',
        'Không lấy toàn inventory supporting_only. Chỉ union required-read của target đã chọn; một unit có thể đồng thời là target và required-read cho target khác.',
        '| ID | Type / role | Vị trí | Required units | Capability |','|---|---|---|---|---|']
    for p in plan:
        uid=p.get('unit_id');path=pool[uid]['citation_path']if uid in pool else p.get('source_artifact')
        md.append('|'+ '|'.join([p['record_id'],p['record_type']+' / '+p['role'],str(path),str(len(p.get('required_unit_ids',[]))),', '.join(p['required_capabilities'])])+'|')
    md += ['Bằng chứng target/dependency: base116.reads.jsonl, nd168.reads.jsonl; mỗi read có typed payload, native proof/source hash/trace và toàn own fields của required units.',
           'Supporting form XXVI được đọc riêng ở supporting_records.reads.jsonl. Form XXIII và sáu course tables giữ ở hồ sơ A28 blocked, chưa là dependency của tập target đóng gói này.',
           'ND168 self artifact nd168.reads.jsonl là đường dẫn tương đối theo this_run, không phải workspace root. Các source_artifact lịch sử cần mount/copy theo hash nếu đóng gói ở phiên sau.']
    (out/'Packaging_Plan.md').write_text('\n\n'.join(md),encoding='utf8')


def check(config,run,replay,output):
    root=Path(run);cfg=load(config);result=s.validate(config,root,replay)
    out=staging_path(output);out.mkdir(parents=True)
    nd=rows(root/'nd168.reads.jsonl')[0];form=load(root/'form_xxiii.read.json');plan=rows(root/'packaging_plan.jsonl')
    negatives=[]
    def rejected(name,fn):
        try:fn()
        except (ValueError,KeyError)as exc:negatives.append({'case':name,'rejected':True,'reason':str(exc)})
        else:raise AssertionError('Negative accepted: '+name)
    for name in ['source','offset','old_unit','missing_dependency','missing_unit_content','capability','truncation','budget']:
        f=copy.deepcopy(nd);cap=s.CAPS
        if name=='source':f['native_proofs'][0]['raw_sha256']='0'*64
        elif name=='offset':f['native_proofs'][0]['char_start']+=1
        elif name=='old_unit':f['record']['unit_id']='OLD_source_unit'
        elif name=='missing_dependency':f['dependencies'].pop()
        elif name=='missing_unit_content':f['dependency_units'].pop()
        elif name=='capability':cap=set()
        elif name=='truncation':f['encoding']['truncation']=True
        elif name=='budget':f['encoding']['tokens_with_special']=257
        rejected(name,lambda:s.reader.check(s.BASE_DIR,f,cap))
    f=copy.deepcopy(form);f['record']['form_fields'].pop();f['native_proofs'].pop()
    f['record']['identity']=form_identity(f['record']);f['record']['record_id']='fr_'+s.hashed(f['record']['identity']);f['record_id']=f['record']['record_id']
    rejected('missing_form_instruction_even_rehashed',lambda:s.reader.check(s.BASE_DIR,f,s.CAPS))
    target=next(p for p in plan if p['role']=='target'and p['record_type']=='chunk.v1')
    for name in ['duplicate_DOCX_HTML','view_as_target','QCVN_I418_I416','unsupported_type']:
        p=copy.deepcopy(target);own=[p]
        if name=='duplicate_DOCX_HTML':own.append({**p,'record_id':'OTHER_HTML_BRANCH','unit_id':'OTHER_HTML_UNIT'})
        elif name=='view_as_target':p['independent_encoder_view']=True
        elif name=='QCVN_I418_I416':p.update(source_conflict=True,region_key='R-caption-I416')
        else:p['record_type']='unknown-record-type'
        rejected(name,lambda:s.check_plan(own))
    base=next(f for f in rows(root/'base116.reads.jsonl')if f['record_type']=='source-retrieval.v1')
    f=copy.deepcopy(base);f['record']['encoder_views'].pop()
    rejected('incomplete_encoder_views',lambda:s.reader.check(s.BASE_DIR,f,s.CAPS))
    tc=TableOwnerConsumer(load(cfg['source_config'])['table_owner']);original=next(r for r in tc.records if '/article:7/'in r['owner_path'])
    for name in ['owner','header','cell','dependency','proof']:
        a=copy.deepcopy(original)
        if name=='owner':a['owner_unit_id']='WRONG_OWNER'
        elif name=='header':a['bindings'][0]['header_cell_ids']=[]
        elif name=='cell':a['cells'].pop()
        elif name=='dependency':a['required_dependencies']=[]
        else:a['cells'][0]['source_slices'][0]['quote_sha256']='0'*64
        rejected('table_'+name,lambda:tc.validate_record(a))
    clone=out/'isolated_copy';shutil.copytree(root/'portable_probe',clone)
    execution=subprocess.run([sys.executable,'-I','-B','-S','-c',ISOLATED,str(clone.resolve()),str(s.BASE_DIR.resolve())],
                             cwd=clone,capture_output=True,text=True,encoding='utf8',timeout=60)
    (out/'isolated.stdout.log').write_text(execution.stdout,encoding='utf8');(out/'isolated.stderr.log').write_text(execution.stderr,encoding='utf8')
    if execution.returncode:raise ValueError('Isolated read failed: '+execution.stderr[-2000:])
    import json
    isolated=json.loads(execution.stdout)
    baseline=load(cfg['baseline_ref']);changed=[p for p,h in baseline.items()if not Path(p).is_file()or s.digest(Path(p).read_bytes())!=h]
    unexpected=[p for p in changed if p not in ['docs/progress/STATUS.md','docs/ingestion.md']]
    if unexpected:raise ValueError({'protected_changes':unexpected})
    report={**result,'negative_cases_rejected':len(negatives),'isolated_read_count':len(isolated['reads']),
            'workspace_fallback_denied':isolated['original_workspace_denied'],'protected_files_checked':len(baseline),
            'unexpected_changes':unexpected,'authorized_doc_changes':changed,'origin':'agent_review','human_reviewer_events':0,
            'limits':'Same Windows machine; five typed probe reads, not a portable packaging of all planned records.'}
    review_pack(root,out,cfg,plan)
    write_rows(out/'negative_checks.jsonl',negatives);write_json(out/'isolated_report.json',isolated);write_json(out/'validation_report.json',report)
    seal(out,{'manifest_type':'source-session4-checks.v1','built_at':now(),'code_sha256':s.digest(Path(__file__).read_bytes())})
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['config','run','replay','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(check(a.config,a.run,a.replay,a.output))


if __name__=='__main__':main()
