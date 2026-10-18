"""Scope proposals bound to existing units/coverage, never review decisions."""
import argparse
from collections import Counter
import csv
import io
from pathlib import Path
import shutil
import sys

from src import assessment_contracts as assessment, coverage_survey as coverage
from src.assessment_evidence import check_files, inventory, seal, now
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, digest
from src.source_registry import load_json, read_rows, write_rows

VERSION = "scope-proposal-survey.v1"
POLICY = "agent-scope-curation.v1"
DEFAULT_CONFIG = BASE_DIR/"config/scope_curation.v1.json"
BRD = "docs/requirements/BRD Vietnamese Traffic Legal Semantic Search_v1.0.docx.md"
SRS = "docs/requirements/SRS Vietnamese Traffic Legal Semantic Search v1.0.docx.md"
DDD = "docs/design/DDD_Data_Model_Vietnamese_Traffic_Legal_Search_v1.0.docx.md"
REQUIREMENTS = [BRD,SRS,DDD,"docs/design/data_model_v1/Stage5_Assessment_Contract.md"]
EXPORTS = {"scope_proposals.jsonl":"proposals", "structural_roles.jsonl":"structural",
           "context_dependencies.jsonl":"dependencies", "proposal_comparisons.jsonl":"comparisons"}


def code_binding():
    return {"survey":digest(Path(__file__).read_bytes()),"assessment_contract":digest(Path(assessment.__file__).read_bytes())}


def unique(rows, key, label):
    by={r[key]:r for r in rows}
    if len(by)!=len(rows):raise ValueError("Duplicate "+label)
    return by


def context_links(root):
    chunks=read_rows(root/"preview/chunks.preview.jsonl")
    contexts=read_rows(root/"preview/contexts.preview.jsonl")
    for q in read_rows(root/"preview/quarantined.preview.jsonl"):
        chunks.append(q["candidate"]);contexts.extend(q["contexts"])
    by=unique(chunks,"chunk_id","coverage chunk")
    return [{"target_unit_id":by[c["chunk_id"]]["unit_id"],**{k:c[k] for k in
             ["unit_id","field_name","char_start","char_end","context_order","context_role"]},
             "source_locator":c["source_locator"],"source_locator_base_ref":"coverage_snapshot/"} for c in contexts]


def requirement_basis(root):
    refs=[]
    for key,start,end in [("BRD3.1","## **3 1","## **3 2"),("BRD3.3","## **3 3","## **3 4"),
                          ("EVIDENCE_ONLY","## **5 2","## **5 3")]:
        p=root/"requirements_snapshot"/BRD
        text=p.read_bytes().decode("utf8");a=text.index(start);b=text.index(end,a)
        refs.append({"evidence_ref":key,"kind":"project_requirement","artifact_ref":"requirements_snapshot/"+BRD,
                     "sha256":digest(p.read_bytes()),"locator":start,"char_start":a,"char_end":b,
                     "offset_basis":"unicode_codepoint_original_UTF8","quote":text[a:b],"quote_sha256":digest(text[a:b].encode())})
    tree=root/"coverage_snapshot/inputs/tree"
    records=read_rows(tree/"extraction_snapshot/extractions.pending.jsonl")
    by={r["extraction"]["extraction_id"]:r["extraction"]["text_ref"] for r in records}
    for s in read_rows(tree/"source_spans.pending.jsonl"):
        refs.append({"evidence_ref":s["span_id"],"kind":"source_span",**s,
                     "artifact_ref":"coverage_snapshot/inputs/tree/extraction_snapshot/"+by[s["extraction_id"]]})
    return refs


def compose(units, coverage_rows, curated, previous, spans, links, binding):
    """Copy explicit bound agent observations; unexamined content stays pending.

    No keyword classifier, ancestor label propagation, new technical judgment,
    legal-date calculation or reviewer event is implemented here.
    """
    by=unique(units,"unit_id","unit");cv=unique(coverage_rows,"unit_id","coverage unit")
    reviews=unique(curated,"unit_id","curated unit");old=unique(previous,"unit_id","prior proposal")
    if set(by)!=set(cv) or not set(reviews)<=set(by) or not set(old)<=set(by):raise ValueError("Coverage/curation/history join lost or added unit")
    for uid,u in by.items():
        if cv[uid]["unit_sha256"]!=digest(canonical(u).encode()) or cv[uid]["law_id"]!=u["law_id"]:
            raise ValueError("Coverage content/law binding mismatch")
    actual={(c["target_unit_id"],c["unit_id"],c["field_name"],c["char_start"],c["char_end"],c["context_order"],c["context_role"]):c for c in links}
    if len(actual)!=len(links):raise ValueError("Duplicate actual context dependency")
    children={u["parent_unit_id"] for u in units};proposals=[];structural=[];dependencies=[];comparisons=[]
    for u in units:
        uid=u["unit_id"];r=reviews.get(uid);c=cv[uid];before=old.get(uid)
        if u["unit_type"] in {"document","chapter","section"}:
            if r:raise ValueError("Structural nodes cannot receive business target labels")
            structural.append({"unit_id":uid,"law_id":u["law_id"],"unit_type":u["unit_type"],"citation_path":u["citation_path"],
                               "role":"structure_only","scope_candidate":None,"descendant_scope_inherited":False})
            continue
        scope=r["scope_candidate"] if r else "pending"
        if scope not in assessment.SCOPES|{"pending"}:raise ValueError("Invalid proposal-only scope")
        if r:
            if r["unit_sha256"]!=digest(canonical(u).encode()) or r["reviewed_fields"]!=["title","text_original"]:
                raise ValueError("Curated unit hash/field binding mismatch")
            if not r["source_quote"] or r["source_quote"] not in (u["text_original"] or u["title"]):raise ValueError("Missing/incorrect curated source quote")
            if not r["reason"].strip() or not r["regulated_subject"].strip() or r["criterion_id"] not in {"BRD3.1","BRD3.3","EVIDENCE_ONLY"}:raise ValueError("Missing subject/reason/BRD basis")
            if r["mixed_parent"] and scope!="pending":raise ValueError("Mixed own/parent scope must remain pending, never label descendants")
        if before and (before["unit_sha256"]!=digest(canonical(u).encode()) or before["binding"]["input_manifest_sha256"]!=binding["input_manifest_sha256"]):
            raise ValueError("Prior proposal unit/tree binding mismatch")
        if scope=="included" and (uid in children or not u["text_original"]):raise ValueError("This curation only includes own-content leaves as targets")
        source_units={uid};n=u
        seen={uid}
        while n["parent_unit_id"]:
            if n["parent_unit_id"] in seen:raise ValueError("Cycle in source context parents")
            seen.add(n["parent_unit_id"])
            if n["parent_unit_id"] not in by:raise ValueError("Missing source context parent")
            n=by[n["parent_unit_id"]]
            if n["unit_type"] in {"article","clause"}:source_units.add(n["unit_id"])
        evidence=[s for s in spans if s["unit_id"] in source_units]
        for field in ["title","text_original"]:
            if u[field] and not any(s["unit_id"]==uid and s["field_name"]==field for s in evidence):raise ValueError("Missing source span for own field")
        deps=r.get("context_dependencies",[]) if r else []
        if scope=="supporting" and not deps:raise ValueError("Supporting requires exact target/field dependencies")
        for dep in deps:
            target=reviews.get(dep["target_unit_id"])
            key=(dep["target_unit_id"],uid,dep["field_name"],dep["char_start"],dep["char_end"],dep["context_order"],dep["context_role"])
            if not target or target["scope_candidate"]!="included" or key not in actual:
                raise ValueError("Supporting dependency is not an actual included-target context")
            if not any(s["unit_id"]==uid and s["field_name"]==dep["field_name"] for s in evidence):raise ValueError("Missing supporting span")
        previous_scope=before["scope_candidate"] if before else None
        comparison="first_proposal" if not before else "unchanged" if (previous_scope or "pending")==scope else "changed_proposal_not_decision"
        change_kind=("pending_to_conclusion" if previous_scope is None else "conclusion_deferred" if scope=="pending" else "role_or_conclusion_changed") if comparison=="changed_proposal_not_decision" else comparison
        row={"unit_id":uid,"unit_sha256":digest(canonical(u).encode()),"law_id":u["law_id"],"unit_type":u["unit_type"],
             "citation_path":u["citation_path"],"parent_unit_id":u["parent_unit_id"],"scope_candidate":scope,
             "assessment_v1_1_scope_candidate":None if scope=="pending" else scope,"scope_status":None,
             "reason":(r["reason"]+" Own source: «"+r["source_quote"]+"»") if r else "Chưa xem xét nội dung unit này trong đợt rà có giới hạn; không suy nhãn từ cha, tiêu đề hay từ khóa; pending không phải excluded.",
             "regulated_subject":r["regulated_subject"] if r else "not_assessed",
             "reviewed_for_scope":bool(r),"method":"agent_content_review_explicit_unit_list" if r else "unassessed_inventory",
             "policy_version":POLICY,"review_scope":r["review_scope"] if r else None,"mixed_parent":r["mixed_parent"] if r else None,
             "evidence_refs":[s["span_id"] for s in evidence]+[r["criterion_id"] if r else "BRD3.1"],
             "source_spans":evidence,"source_span_artifact_ref":"coverage_snapshot/inputs/tree/source_spans.pending.jsonl","context_dependencies":deps,
             "binding":binding,"snapshot_date":SNAPSHOT_DATE,"origin":"agent_review","review_status":"pending",
             "previous_proposal_ref":{"proposal_id":before["proposal_id"],"artifact_ref":"coverage_snapshot/inputs/assessment/machine_proposals.jsonl","sha256":digest(canonical(before).encode())} if before else None,
             "proposal_relation":comparison,"change_kind":change_kind,"previous_scope_candidate":previous_scope,
             "coverage_status":c["status"],"coverage_primary_reason":c["primary_reason"],"coverage_reasons":c["reasons"],
             "tokens_with_special":c["tokens_with_special"],"unknown_tokens":c["unknown_tokens"],
             "legal_metadata":{"source":"pending","extraction_tree":"pending","applicability":"pending_review","effective_from":None,"effective_to":None},
             "decision_ids":dict.fromkeys(assessment.DIMENSIONS),"reviewer_ref":None,"reviewed_at":None,
             "release_eligible":False,"corpus_version":None,"ready_to_load_ddd":False}
        row["proposal_id"]=assessment.identity("pr_",row);proposals.append(row)
        if before:comparisons.append({"unit_id":uid,"citation_path":u["citation_path"],"previous_proposal_id":before["proposal_id"],
                                     "proposal_id":row["proposal_id"],"before":previous_scope,"after":scope,"relation":comparison,"change_kind":change_kind,"explanation":row["reason"]})
    pp={p["unit_id"]:p for p in proposals}
    for link in links:
        target=pp[link["target_unit_id"]]
        if target["scope_candidate"]!="included":continue
        parent=pp[link["unit_id"]]
        if not any(d["target_unit_id"]==link["target_unit_id"] and d["field_name"]==link["field_name"] for d in parent["context_dependencies"]):
            raise ValueError("Included target is missing its actual context dependency declaration")
        dependencies.append({**link,"context_scope_candidate":parent["scope_candidate"],"target_scope_candidate":"included",
                             "scope_dependency_pending":parent["scope_candidate"] not in {"supporting","included"},
                             "technical_status":"no_direct_issue_reported_by_existing_builder",
                             "coverage_status":target["coverage_status"],"release_eligible":False})
    for rows in [proposals,structural,comparisons]:rows.sort(key=lambda r:(r.get("law_id",""),r["unit_id"]))
    dependencies.sort(key=lambda r:(r["target_unit_id"],r["context_order"]))
    return {"proposals":proposals,"structural":structural,"dependencies":dependencies,"comparisons":comparisons}


def summarize(proposals, structural, dependencies):
    included=[p for p in proposals if p["scope_candidate"]=="included"]
    measured=[p for p in included if p["tokens_with_special"] is not None]
    pending_targets={d["target_unit_id"] for d in dependencies if d["scope_dependency_pending"]}
    return {"legal_units":len(proposals)+len(structural),"business_unit_rows":len(proposals),"structural_only":len(structural),
            "explicit_agent_reviews":sum(p["reviewed_for_scope"] for p in proposals),"unassessed":sum(not p["reviewed_for_scope"] for p in proposals),
            "scope_proposal_counts":{k:sum(p["scope_candidate"]==k for p in proposals) for k in ["included","supporting","excluded","pending"]},
            "reviewed_pending":sum(p["reviewed_for_scope"] and p["scope_candidate"]=="pending" for p in proposals),
            "included_coverage":dict(sorted(Counter(p["coverage_status"] for p in included).items())),
            "included_measured":len(measured),"included_unknown_tokens":sum(p["unknown_tokens"] for p in measured),
            "included_candidates_with_unknown":sum(p["unknown_tokens"]>0 for p in measured),
            "included_with_pending_scope_context":len(pending_targets),"context_dependency_rows":len(dependencies),
            "supporting_units_with_coverage_issues":sum(p["scope_candidate"]=="supporting" and p["coverage_status"] not in {"context_only","preview_available"} for p in proposals),
            "prior_proposals_linked":sum(p["previous_proposal_ref"] is not None for p in proposals),
            "changed_prior_proposals":sum(p["proposal_relation"]=="changed_proposal_not_decision" for p in proposals),
            "prior_change_kinds":dict(Counter(p["change_kind"] for p in proposals if p["proposal_relation"]=="changed_proposal_not_decision"))}


def csv_text(rows):
    fields=["law_id","citation_path","unit_id","unit_type","scope_candidate","reviewed_for_scope","regulated_subject","coverage_status",
            "tokens_with_special","unknown_tokens","reason","context_dependencies","previous_scope_candidate","proposal_relation","evidence_refs","origin"]
    s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n");w.writeheader()
    for r in rows:w.writerow({k:canonical(r[k]) if isinstance(r[k],(dict,list)) else r[k] for k in fields})
    return s.getvalue()


def report_text(summary):
    lines=["# Đề xuất phạm vi nghiệp vụ — agent_review, chưa có quyết định", "",
           "Snapshot 2025-01-01; chỉ cây DOCX Stage4-005 + coverage-001, không trộn PDF Điều 22. Không phải Recall/retrieval quality hoặc corpus được duyệt.","",
           "## Phương pháp và mức bao phủ", "",
           "Agent đã đọc own title/text và các cha của tập unit giới hạn, ghi danh sách unit/hash/quote/subject/reason rõ ràng trong config. Runtime chỉ áp dụng danh sách đó và pending cho phần chưa xét; không phân loại bằng keyword hay truyền nhãn cha xuống con.",
           "BRD §3.1/§3.3 và SRS §1.2 ưu tiên quy tắc, GPLX/điểm GPLX, xử phạt trực tiếp. Điều kiện phương tiện chưa thành use case cam kết toàn diện: giữ pending các ca chưa rõ. BRD/SRS còn snapshot mở, áp dụng mốc 2025-01-01 đã chốt trong DDD/inventory/người dùng. Không dùng scope.md/prototype để mở rộng phạm vi.",
           "Stage5A v1.1 trước giới hạn pilot 40/60; yêu cầu mới cho phép mở rộng proposal. Không thay validator pilot, enum/schema DDD hoặc hệ thống quyết định. pending chỉ là enum proposal ở staging, ánh xạ scope_candidate=null của v1.1; scope_status luôn null.","",
           "| Văn bản | Units | Cấu trúc | Đã xét own fields | Chưa xét | Included | Supporting | Excluded | Pending |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for law,s in list(summary["documents"].items())+[("TỔNG",summary["total"])]:
        q=s["scope_proposal_counts"];lines.append(f"| {law} | {s['legal_units']} | {s['structural_only']} | {s['explicit_agent_reviews']} | {s['unassessed']} | {q['included']} | {q['supporting']} | {q['excluded']} | {q['pending']} |")
    lines += ["","Pending gồm cả đã đọc nhưng chưa kết luận và chưa đọc; xem reviewed_for_scope/method trong JSONL/CSV. Document/Chương/Mục không có proposal target. Cha hỗn hợp giữ pending, không làm mất khác biệt con. Supporting chỉ giới hạn own fields và target IDs trong context_dependencies, không gán toàn nhánh.","",
              "## Proposed included ghép coverage thật", "", "| Văn bản | Preview | Vượt budget | Parser/source/context chặn | Chưa hỗ trợ | Lỗi thực thi | Mẫu đo | Unknown / candidate | Target có context pending scope |", "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for law,s in list(summary["documents"].items())+[("TỔNG",summary["total"])]:
        c=s["included_coverage"];lines.append(f"| {law} | {c.get('preview_available',0)} | {c.get('over_token_budget',0)} | {c.get('blocked_source_or_context',0)} | {c.get('unsupported_structure',0)} | {c.get('execution_error',0)} | {s['included_measured']} | {s['included_unknown_tokens']} / {s['included_candidates_with_unknown']} | {s['included_with_pending_scope_context']} |")
    lines += ["","Token lấy nguyên từ coverage đã replay, trên toàn encoder_text; không bịa số cho unit chưa đo, không truncate. Preview là khả năng kỹ thuật, không phải serving. Context pending scope là việc nghiệp vụ còn mở, không gán thành lỗi kỹ thuật của builder. Xem context_dependencies.jsonl: từng field, offsets và source proof, không dùng mọi supporting làm context chung.","",
              "## Lịch sử và giới hạn", "", f"Giữ {summary['total']['prior_proposals_linked']} proposal cũ nguyên byte trong coverage_snapshot/inputs/assessment; {summary['total']['changed_prior_proposals']} proposal mới khác kết luận/role cũ. proposal_comparisons.jsonl giải thích từng thay đổi, không supersede decision hoặc xóa lịch sử. Toàn bộ decision/evidence cũ vẫn trong snapshot, không biến ngày hiệu lực ứng viên thành quyết định scope.",
              "Nguồn DOCX legacy/provenance, extraction/cây và applicability còn pending. Bằng chứng nội dung là spans/locator/hash của extraction đang có, không phải chứng minh DOCX tương đương bản chính thức. URL inventory là candidate. Các ảnh/PDF/HTML/findings cũ được giữ, không khẳng định đã rà lại toàn bộ hoặc lịch sử hiệu lực trong lượt này.",
              "Bảng/quarantine chưa thành unit vẫn ở coverage_snapshot/source_gaps.jsonl; không tạo unit/proposal giả. Mixed amendment/vehicle scope còn mở. Chưa tạo corpus, reviewer event, assessment verified, chunk mới, embedding/index hoặc kích hoạt ứng dụng.",
              "","## Tối đa ba ưu tiên — chỉ đề xuất",""]
    for i,p in enumerate(summary["priorities"],1):lines.append(f"{i}. {p['work']}: {p['candidate_count']} proposed included liên quan; {p['note']}")
    return "\n".join(lines+["","Các nhóm ưu tiên có thể giao nhau, không cộng thành số target mới. Các ca cụ thể và bất đồng ở priority_cases.md; không gọi số liệu này là độ phủ toàn pháp luật hoặc Recall.",""])


def priority_text(out):
    lines=["# Ca rà soát ưu tiên và bất đồng", "", "Chỉ proposal agent; không có quyết định người dùng. Nội dung/spans đầy đủ trong scope_proposals.jsonl và snapshot cây.",""]
    for label,predicate in [("Included vượt budget",lambda p:p["scope_candidate"]=="included" and p["coverage_status"]=="over_token_budget"),
                            ("Ca đã biết",lambda p: any(x in p["citation_path"] for x in ["Điều 22 >", "Điều 6 > Khoản 1", "Điều 39 > Khoản 9", "Điều 84 >"]) or p["citation_path"].endswith("Điều 22")),
                            ("Bất đồng với proposal cũ",lambda p:p["proposal_relation"]=="changed_proposal_not_decision")]:
        lines += ["## "+label,""]
        for p in out["proposals"]:
            if not predicate(p):continue
            lines += [f"- **{p['citation_path']}**: {p['scope_candidate']}; coverage={p['coverage_status']}; token={p['tokens_with_special']}; unknown={p['unknown_tokens']}.",
                      "  "+p["reason"],"  unit_id="+p["unit_id"]+"; evidence_refs="+", ".join(p["evidence_refs"]),""]
    lines += ["## Context nghiệp vụ còn pending","", "| Target | Context | Field | Offsets trong field |","|---|---|---|---|"]
    by={p["unit_id"]:p for p in out["proposals"]}
    for d in out["dependencies"]:
        if d["scope_dependency_pending"]:lines.append(f"| {by[d['target_unit_id']]['citation_path']} | {by[d['unit_id']]['citation_path']} | {d['field_name']} | [{d['char_start']},{d['char_end']}) |")
    return "\n".join(lines+["", "Offset context là tương đối trong field; extraction offsets nằm trong source_locator.spans. Không tự ghép dẫn chiếu ngoài cây cha hoặc đưa các con anh em vào context.",""])


def calculate(run):
    root=run/"coverage_snapshot";cfg=load_json(run/"config.json")
    if cfg["policy_version"]!=POLICY or cfg["method"]!="agent_content_review_explicit_unit_list" or cfg["snapshot_date"]!=SNAPSHOT_DATE or digest((root/"manifest.json").read_bytes())!=cfg["coverage_manifest_sha256"]:
        raise ValueError("Policy/snapshot/coverage binding mismatch")
    if set(cfg["requirements_sha256"])!=set(REQUIREMENTS) or any(digest((run/"requirements_snapshot"/ref).read_bytes())!=h for ref,h in cfg["requirements_sha256"].items()):
        raise ValueError("Scope requirements changed; explicit curation needs reconsideration")
    meta=check_files(root/"manifest.json")
    if meta["files"]!=inventory(root) or meta["code_sha256"]!=coverage.code_binding():raise ValueError("Coverage inventory/code mismatch")
    tree=root/"inputs/tree";oldroot=root/"inputs/assessment";binding=load_json(oldroot/"binding.json")
    if binding["input_manifest_sha256"]!=cfg["tree_manifest_sha256"] or digest((tree/"manifest.json").read_bytes())!=cfg["tree_manifest_sha256"]:raise ValueError("Wrong tree/old assessment binding")
    binding={**binding,"coverage_manifest_sha256":cfg["coverage_manifest_sha256"],"scope_curation_sha256":digest(canonical(cfg).encode()),
             "scope_policy_version":POLICY,"scope_requirements_sha256":digest(canonical(inventory(run/"requirements_snapshot")).encode())}
    units=read_rows(tree/"legal_units.pending.jsonl");spans=read_rows(tree/"source_spans.pending.jsonl")
    basis=requirement_basis(run)
    out=compose(units,read_rows(root/"unit_coverage.jsonl"),cfg["reviews"],read_rows(oldroot/"machine_proposals.jsonl"),spans,context_links(root),binding)
    if not all(set(p["evidence_refs"])<={r["evidence_ref"] for r in basis} for p in out["proposals"]):raise ValueError("Unknown evidence reference")
    summary={"version":VERSION,"snapshot_date":SNAPSHOT_DATE,"origin":"agent_review","release_eligible":False,
             "documents":{},"total":summarize(out["proposals"],out["structural"],out["dependencies"])}
    for law in sorted({u["law_id"] for u in units}):
        ps=[p for p in out["proposals"] if p["law_id"]==law];ids={p["unit_id"] for p in ps}
        summary["documents"][law]=summarize(ps,[r for r in out["structural"] if r["law_id"]==law],[d for d in out["dependencies"] if d["target_unit_id"] in ids])
    included=[p for p in out["proposals"] if p["scope_candidate"]=="included"]
    summary["priorities"]=[{"work":"Rà scope các field context của cha hỗn hợp", "candidate_count":summary["total"]["included_with_pending_scope_context"],"note":"Chỉ xét field/target dependency đã liệt kê, không gán lại toàn nhánh; cần trước khi chọn context phục vụ."},
                           {"work":"Nghiên cứu segment giữ nguyên nghĩa cho proposed included quá dài","candidate_count":sum(p["coverage_status"]=="over_token_budget" for p in included),"note":"Cận trên cần khảo sát; không tăng budget/bỏ context; cần cho các target dài thực sự được chọn trước embedding."},
                           {"work":"Hoàn thiện nguồn và applicability của proposed included có preview", "candidate_count":sum(p["coverage_status"]=="preview_available" for p in included),"note":"Không đồng nghĩa đều phát hành được; đối chiếu bản chính thức, ngoại lệ snapshot và quyết định thật, không sửa parser ngoài tập cần."}]
    report={"technical_valid":True,"business_rows":len(out["proposals"]),"structural_only":len(out["structural"]),
            "explicit_agent_reviews":summary["total"]["explicit_agent_reviews"],"new_reviewer_events":0,"release_eligible":False,
            "corpus_created":False,"legal_blockers":coverage.LEGAL_BLOCKERS,"source_gap_units_created":0}
    return out,basis,summary,report


def build(coverage_manifest,run_dir,config=DEFAULT_CONFIG):
    target=staging_path(run_dir);source=Path(coverage_manifest).resolve().parent;cfg=load_json(config)
    if source in target.parents:raise ValueError("Output cannot be nested in a sealed coverage input")
    if digest(Path(coverage_manifest).read_bytes())!=cfg["coverage_manifest_sha256"]:raise ValueError("Wrong coverage manifest")
    if any(digest((BASE_DIR/ref).read_bytes())!=h for ref,h in cfg["requirements_sha256"].items()):raise ValueError("Scope requirements changed")
    report=coverage.validate(coverage_manifest)
    if not report["technical_valid"] or not report["survey_completed"]:raise ValueError("Invalid coverage survey")
    with staged_run(run_dir,VERSION,coverage_manifest) as (run,status):
        shutil.copytree(Path(coverage_manifest).resolve().parent,run/"coverage_snapshot")
        for ref in REQUIREMENTS:
            p=run/"requirements_snapshot"/ref;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(BASE_DIR/ref,p)
        write_json(run/"config.json",cfg)
        out,basis,summary,report=calculate(run)
        for file,key in EXPORTS.items():write_rows(run/file,out[key])
        write_rows(run/"review_basis.jsonl",basis)
        write_json(run/"scope_coverage_summary.json",summary);write_json(run/"validation_report.json",report)
        for name,text in [("scope_proposals.csv",csv_text(out["proposals"])),("scope_report.md",report_text(summary)),("priority_cases.md",priority_text(out))]:
            (run/name).write_text(text,encoding="utf8",newline="\n")
        seal(run,{"manifest_type":VERSION,"built_at":now(),"code_sha256":code_binding(),"snapshot_date":SNAPSHOT_DATE,
                  "coverage_manifest_sha256":cfg["coverage_manifest_sha256"],"origin":"agent_review","release_eligible":False,"corpus_version":None,"new_reviewer_events":0})
        status.update(report)
    return report


def validate(manifest):
    m=check_files(manifest);run=Path(manifest).resolve().parent
    if (m["manifest_type"]!=VERSION or m["files"]!=inventory(run) or m["code_sha256"]!=code_binding()
            or m["snapshot_date"]!=SNAPSHOT_DATE or m["origin"]!="agent_review" or m["release_eligible"] is not False
            or m["corpus_version"] is not None or m["new_reviewer_events"]!=0):raise ValueError("Scope manifest/decision/pending mismatch")
    coverage.validate(run/"coverage_snapshot/manifest.json")
    out,basis,summary,report=calculate(run)
    for file,key in EXPORTS.items():
        if read_rows(run/file)!=out[key]:raise ValueError("Scope replay mismatch: "+file)
    if read_rows(run/"review_basis.jsonl")!=basis or load_json(run/"scope_coverage_summary.json")!=summary or load_json(run/"validation_report.json")!=report:raise ValueError("Summary/evidence/review replay mismatch")
    for name,text in [("scope_proposals.csv",csv_text(out["proposals"])),("scope_report.md",report_text(summary)),("priority_cases.md",priority_text(out))]:
        if (run/name).read_text(encoding="utf8")!=text:raise ValueError("Readable scope mismatch: "+name)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="command",required=True)
    b=s.add_parser("build");b.add_argument("--coverage-manifest",type=Path,required=True);b.add_argument("--run-dir",type=Path,required=True);b.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    v=s.add_parser("validate");v.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        print(canonical(build(a.coverage_manifest,a.run_dir,a.config) if a.command=="build" else validate(a.manifest)));return 0
    except Exception as exc:
        print(canonical({"technical_valid":False,"error":str(exc),"release_eligible":False}),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
