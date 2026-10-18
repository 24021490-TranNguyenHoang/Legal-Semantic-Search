"""Readonly chunkability survey of parsed DOCX trees. No new chunking rules."""
import argparse
from collections import Counter
import copy
import csv
import io
import json
import math
from pathlib import Path
import shutil
import sys

from src import chunk_preview_v2 as builder, chunk_preview, encoder_input
from src.assessment_pipeline import validate_run as validate_assessment
from src.legal_parser import validate_run as validate_tree
from src.assessment_evidence import inventory, check_files, seal, now
from src.article22_preview import require_preview_schema
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.pipeline_cli import staged_run, staging_path, write_json
from src.preview_tokens import default_tokenizer_dir, ASSETS
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows

VERSION = "chunk-coverage-survey.v1"
DEFAULT_CONFIG = BASE_DIR/"config/coverage_survey.v1.json"
LEGAL_BLOCKERS = ["SOURCE_PROVENANCE_PENDING", "EXTRACTION_TREE_REVIEW_PENDING", "SCOPE_APPLICABILITY_REVIEW_PENDING", "CORPUS_NOT_CREATED", "PREVIEW_NOT_RELEASE_READY"]
PRIORITY = ["EXECUTION_ERROR", "INVALID_RELATION_OR_SOURCE", "DUPLICATE_UNIT_ID", "MISSING_TARGET", "MISSING_REQUIRED_CONTEXT",
            "PARSER_OR_EXTRACTION_ISSUE_IMPACT", "TOKEN_BUDGET_EXCEEDED", "UNSUPPORTED_STRUCTURE"]
STATUSES = ["context_only", "preview_available", "blocked_source_or_context", "over_token_budget", "unsupported_structure", "execution_error"]
EXPORTS = {"preview/chunks.preview.jsonl": "chunks", "preview/contexts.preview.jsonl": "contexts",
           "preview/encoder_inputs.preview.jsonl": "encoder_inputs", "preview/quarantined.preview.jsonl": "quarantined",
           "builder_issues.jsonl": "issues", "dependency_checks.jsonl": "dependency_checks", "execution_errors.jsonl": "execution_errors"}


def code_binding():
    return {n: digest(Path(m.__file__).read_bytes()) for n,m in [("survey",sys.modules[__name__]),("builder",builder),("proof_identity",chunk_preview),("encoder",encoder_input)]}


def classification(unit, parents):
    kind, children = unit["unit_type"], unit["unit_id"] in parents
    if kind in {"document", "chapter", "section"} or children and kind in {"article", "clause"}:
        return "context_only"
    if kind in {"clause", "point"} and not children:
        return "supported_target"
    if unit["text_original"] or kind == "point":
        return "unsupported_target"
    return "context_only"


def load_data(run):
    """Bind existing pending source records to each law; no structural validation clone.

    All relation/proof/dependency decisions below come from the actual builder.
    Upstream validators verify the complete tree/extraction/source snapshots.
    """
    root = run/"inputs"
    tree = root/"tree"
    source = tree/"extraction_snapshot/source_snapshot"
    units, spans = read_rows(tree/"legal_units.pending.jsonl"), read_rows(tree/"source_spans.pending.jsonl")
    records = read_rows(tree/"extraction_snapshot/extractions.pending.jsonl")
    docs = read_rows(source/"documents.pending.jsonl")
    files = read_rows(source/"files.pending.jsonl")
    issues = [dict(q,origin="stage4_parser") for q in read_rows(tree/"quality_issues.jsonl")]
    coverage = read_rows(tree/"coverage.jsonl")
    for q in coverage:
        if q["category"] in {"needs_review", "unparsed"}:
            issues.append({**q,"issue_id":"coverage:"+q["locator_id"],"code":q["reason"],"origin":"stage4_coverage"})
    traces = {r["extraction"]["extraction_id"]:load_json(resolve_ref(tree/"extraction_snapshot",r["trace_ref"])) for r in records}
    for q in read_rows(tree/"extraction_snapshot/quality_issues.jsonl"):
        r = next(r for r in records if r["extraction"]["extraction_id"] == q["extraction_id"])
        item = {**q,"law_id":r["law_id"],"origin":"stage3_extraction"}
        nodes = [n for n in traces[q["extraction_id"]]["nodes"] if n["locator"] == q["locator"]]
        if len(nodes) == 1:
            item.update(char_start=nodes[0]["char_start"],char_end=nodes[0]["char_end"])
        issues.append(item)
    laws = {}
    for d in docs:
        law = d["law_id"]
        us = [u for u in units if u["law_id"] == law]; ids = {u["unit_id"] for u in us}
        extractions = []
        for r in records:
            if r["law_id"] == law:
                e = copy.deepcopy(r["extraction"]);e["text_ref"]="tree/extraction_snapshot/"+e["text_ref"];extractions.append(e)
        laws[law] = {"document":{"law_id":law,"source_id":d["source_id"],"law_title":d["declared"]["law_title"],"source_url":d["declared"]["source_url_candidate"]},
                     "units":us,"spans":[s for s in spans if s["unit_id"] in ids],"extractions":extractions,
                     "files":[{**f["measured"],**{k:f[k] for k in ["file_id","law_id","source_set_id","part_order"]}} for f in files if f["law_id"] == law],
                     "issues":[q for q in issues if q["law_id"] == law]}
    # Keep issue/coverage records separately. They are NOT artificial legal units.
    return laws, source_gaps(issues,read_rows(tree/"tables.jsonl"))


def source_gaps(issues, tables):
    gaps=[]
    for q in issues:
        if q["origin"] in {"stage4_parser", "stage4_coverage"}:
            gaps.append({**q,"gap_id":q["origin"]+":"+q["issue_id"],"input_ref":"inputs/tree/", "unit_created":False,
                         "note":"May overlap another layer's record; not an additional legal unit or independent source gap."})
    for i,t in enumerate(tables):
        gaps.append({**t,"origin":"stage4_table","gap_id":"table:"+str(i),"input_ref":"inputs/tree/tables.jsonl","unit_created":False,
                     "note":"Table retained, not parsed as legal targets; supporting/non-body tables are not target failures. May overlap parser/coverage record."})
    return gaps


def scope_index(assessment_root, units, tree_manifest_hash):
    binding = load_json(assessment_root/"binding.json")
    if binding["input_manifest_sha256"] != tree_manifest_hash:
        raise ValueError("Scope assessment belongs to another tree; never transfer PDF/DOCX bindings")
    by = {u["unit_id"]:u for u in units}
    proposals = {}
    for p in read_rows(assessment_root/"machine_proposals.jsonl"):
        if p["unit_id"] not in by or p["binding"] != binding or p["unit_sha256"] != digest(canonical(by[p["unit_id"]]).encode()):
            raise ValueError("Scope proposal unit/content/binding mismatch")
        proposals[p["unit_id"]] = p
    decisions = {}
    for d in read_rows(assessment_root/"review_decision_history.jsonl"):
        if d["binding"] != binding or d["unit_id"] not in by or d["unit_sha256"] != digest(canonical(by[d["unit_id"]]).encode()):
            raise ValueError("Scope decision unit/content binding mismatch")
        if d["dimension"] == "scope":
            decisions[d["unit_id"]] = d  # Upstream validator replays evidence and per-dimension supersedes.
    result = {}
    for uid in by:
        p,d = proposals.get(uid),decisions.get(uid)
        result[uid] = {"stage":"decision_recorded" if d else "proposal_only" if p and p["scope_candidate"] is not None else "unassessed",
                       "scope_status":d["scope_status"] if d else None,"scope_proposal":p["scope_candidate"] if p else None,
                       "proposal_record_present":p is not None,"proposal_id":p["proposal_id"] if p else None,
                       "decision_id":d["decision_id"] if d else None,"reason":d["decision_note"] if d else p["scope_reason"] if p else None}
    return result


def execute_batches(data, root, config, encode, batch_size=64, progress=None):
    """Call the real builder. Isolate runtime failures; never forge token rows."""
    output = {k:[] for k in ["chunks","contexts","issues","quarantined","encoder_inputs","unit_results","dependency_checks","execution_errors"]}
    parents = {u["parent_unit_id"] for u in data["units"]}
    targets = [u["unit_id"] for u in data["units"] if classification(u,parents) != "context_only"]
    def one(ids):
        try:
            r = builder.build_chunks(data,root,{**config,"target_unit_ids":ids},LEGAL_BLOCKERS,encode,reference_prefix="inputs/")
        except Exception as exc:
            if len(ids)>1:
                mid=len(ids)//2;one(ids[:mid]);one(ids[mid:]);return
            output["execution_errors"].append({"unit_id":ids[0],"code":"EXECUTION_ERROR","exception_type":type(exc).__name__,"detail":str(exc)})
            return
        for key in r:output[key].extend(r[key])
    for start in range(0,len(targets),batch_size):
        one(targets[start:start+batch_size])
        if progress:progress(data["document"]["law_id"],min(start+batch_size,len(targets)),len(targets))
    output["chunks"].sort(key=lambda c:c["chunk_id"])
    output["contexts"].sort(key=lambda c:(c["chunk_id"],c["context_order"]))
    output["encoder_inputs"].sort(key=lambda c:c["chunk_id"])
    return output


def unit_rows(data, output, scopes):
    by={u["unit_id"]:u for u in data["units"]};parents={u["parent_unit_id"] for u in data["units"]}
    chunks={c["unit_id"]:c for c in output["chunks"]}
    contexts={c["chunk_id"]:[x for x in output["contexts"] if x["chunk_id"]==c["chunk_id"]] for c in output["chunks"]}
    for q in output["quarantined"]:
        chunks[q["candidate"]["unit_id"]]=q["candidate"];contexts[q["candidate"]["chunk_id"]]=q["contexts"]
    encoded={e["unit_id"]:e for e in output["encoder_inputs"]}
    errors={e["unit_id"]:e for e in output["execution_errors"]}
    rows=[]
    for u in data["units"]:
        uid=u["unit_id"];category=classification(u,parents);c=chunks.get(uid);e=encoded.get(uid)
        issues=[q for q in output["issues"] if q["unit_id"]==uid]
        codes=set(q["code"] for q in issues)
        if uid in errors:codes.add("EXECUTION_ERROR")
        primary=next((code for code in PRIORITY if code in codes),None)
        if category=="context_only":status="context_only";primary="STRUCTURE_OR_PARENT_CONTEXT"
        elif primary=="EXECUTION_ERROR":status="execution_error"
        elif primary=="TOKEN_BUDGET_EXCEEDED":status="over_token_budget"
        elif primary=="UNSUPPORTED_STRUCTURE":status="unsupported_structure"
        elif primary is not None:status="blocked_source_or_context"
        elif c is not None and e is not None:status="preview_available";primary="BUILDER_PREVIEW_CREATED"
        else:raise ValueError("Builder did not account for candidate: "+uid)
        if status=="preview_available" and not e["within_budget"]:raise ValueError("Over-budget candidate cannot count as preview")
        related=set(codes)
        for q in issues:
            for impact in q.get("impacts",[]):related.add(impact["issue"]["code"])
        ancestry=[];node=u;seen=set()
        while node.get("parent_unit_id") in by and node["parent_unit_id"] not in seen:
            uid_parent=node["parent_unit_id"];seen.add(uid_parent);ancestry.append(uid_parent);node=by[uid_parent]
        ctx=contexts.get(c["chunk_id"],[]) if c else []
        rows.append({"law_id":u["law_id"],"unit_id":uid,"unit_type":u["unit_type"],"citation_path":u["citation_path"],
                     "unit_sha256":digest(canonical(u).encode()),"category":category,"is_candidate":category!="context_only",
                     "supported_target":category=="supported_target","status":status,"primary_reason":primary,
                     "reasons":sorted(related),"builder_issues":issues,"execution_error":errors.get(uid),
                     "parent_unit_ids":ancestry,"context_unit_ids":list(dict.fromkeys(x["unit_id"] for x in ctx)),
                     "context_resolution":"returned_by_builder" if c else "not_returned_by_builder",
                     "tokens_with_special":e["tokens_with_special"] if e else None,"unknown_tokens":e.get("unknown_tokens") if e else None,
                     "encoder_text_sha256":e.get("encoder_text_sha256") if e else None,"content_sha256":c["content_sha256"] if c else None,
                     "chunk_id":c["chunk_id"] if c else None,"source_spans":[s for s in data["spans"] if s["unit_id"]==uid],
                     "context_source_proofs":[x["source_locator"] for x in ctx],"input_unit_ref":{"file":"inputs/tree/legal_units.pending.jsonl","unit_id":uid},
                     "scope":scopes[uid],"origin":"agent_review","preview_only":True,"release_eligible":False,
                     "legal_metadata":{"source":"pending","extraction_tree":"pending","applicability":"pending_review","corpus_version":None}})
    return rows


def distribution(values):
    values=sorted(values);n=len(values)
    return {"n":n,"quantile_method":"nearest_rank","p50":values[math.ceil(n*.50)-1] if n else None,
            "p95":values[math.ceil(n*.95)-1] if n else None,"max":values[-1] if n else None}


def summarize(rows):
    counts=Counter(r["status"] for r in rows)
    if sum(counts.values())!=len(rows) or len({r["unit_id"] for r in rows})!=len(rows):raise ValueError("Duplicate survey unit/state")
    supported=[r for r in rows if r["supported_target"]]
    measured=[r for r in rows if r["tokens_with_special"] is not None]
    candidates=[r for r in rows if r["is_candidate"]]
    n=len(supported);passed=sum(r["status"]=="preview_available" for r in supported)
    if len(candidates)!=len(rows)-counts["context_only"]:raise ValueError("Context-only denominator mismatch")
    scope=Counter(r["scope"]["stage"] for r in rows)
    buckets={"257_384":sum(257<=r["tokens_with_special"]<=384 for r in measured),
             "385_512":sum(385<=r["tokens_with_special"]<=512 for r in measured),"over_512":sum(r["tokens_with_special"]>512 for r in measured)}
    return {"legal_units":len(rows),"unit_types":dict(sorted(Counter(r["unit_type"] for r in rows).items())),
            "context_only":counts["context_only"],"supported_targets":n,"supported_target_types":dict(sorted(Counter(r["unit_type"] for r in supported).items())),
            "candidates_including_unsupported":len(candidates),"unsupported_target_types":dict(sorted(Counter(r["unit_type"] for r in candidates if not r["supported_target"]).items())),
            "final_status_counts":{s:counts[s] for s in STATUSES},"supported_preview_count":passed,
            "supported_success_rate":{"numerator":passed,"denominator":n,"ratio":passed/n if n else None},
            "measured_candidates":len(measured),"token_distribution":distribution([r["tokens_with_special"] for r in measured]),
            "over_256":sum(buckets.values()),"overflow_buckets":buckets,"unknown_tokens":sum(r["unknown_tokens"] for r in measured),
            "candidates_with_unknown":sum(r["unknown_tokens"]>0 for r in measured),
            "primary_failure_reasons":dict(Counter(r["primary_reason"] for r in candidates if r["status"]!="preview_available")),
            "scope_stages":{s:scope[s] for s in ["decision_recorded","proposal_only","unassessed"]},
            "scope_proposal_values":dict(Counter(str(r["scope"]["scope_proposal"]) for r in rows if r["scope"]["proposal_record_present"])),
            "scope_proposal_records":sum(r["scope"]["proposal_record_present"] for r in rows),
            "failure_scope_stages":{status:dict(Counter(r["scope"]["stage"] for r in rows if r["status"]==status)) for status in STATUSES if status not in {"preview_available","context_only"}}}


def csv_text(rows):
    fields=["law_id","unit_id","unit_type","citation_path","category","supported_target","status","primary_reason","tokens_with_special","unknown_tokens",
            "parent_unit_ids","context_unit_ids","reasons","source_spans","scope","chunk_id","origin","preview_only","release_eligible"]
    output=io.StringIO(newline="");writer=csv.DictWriter(output,fieldnames=fields,lineterminator="\n");writer.writeheader()
    for row in rows:writer.writerow({k:canonical(row[k]) if isinstance(row[k],(dict,list)) else row[k] for k in fields})
    return output.getvalue()


def samples_text(rows):
    lines=["# Mẫu khảo sát trên cây DOCX — pending, agent_review","","Không có mẫu không có nghĩa dữ liệu verified. Mỗi hàng tham chiếu input/outputs của cùng run.",""]
    groups=[("Preview thành công",lambda r:r["status"]=="preview_available"),
            ("Vượt token budget",lambda r:r["status"]=="over_token_budget"),
            ("Thiếu context/spans/quan hệ",lambda r:r["status"]=="blocked_source_or_context" and r["primary_reason"]!="PARSER_OR_EXTRACTION_ISSUE_IMPACT"),
            ("Parser/extraction issue ảnh hưởng",lambda r:r["primary_reason"]=="PARSER_OR_EXTRACTION_ISSUE_IMPACT"),
            ("Điều lá/cấu trúc chưa hỗ trợ",lambda r:r["status"]=="unsupported_structure"),
            ("Lỗi thực thi",lambda r:r["status"]=="execution_error")]
    for name,predicate in groups:
        found=[r for r in rows if predicate(r)];chosen=[];seen=set()
        for r in found:
            if r["law_id"] not in seen:chosen.append(r);seen.add(r["law_id"])
            if len(chosen)==2:break
        if not chosen:lines += ["## "+name,"","Không quan sát thấy mẫu trong dữ liệu thật; không tạo mẫu luật giả.",""];continue
        lines += ["## "+name,"","| Citation | Primary reason | Token / unknown | Artifact |","|---|---|---|---|"]
        for r in chosen:
            ref="preview/chunks.preview.jsonl" if r["status"]=="preview_available" else "preview/quarantined.preview.jsonl" if r["status"]=="over_token_budget" else "unit_coverage.jsonl"
            lines.append(f"| {r['citation_path']} | {r['primary_reason']} | {r['tokens_with_special']} / {r['unknown_tokens']} | {ref}, unit_id={r['unit_id']} |")
            lines.append("\nLocator/spans: `"+canonical(r["source_spans"])+"`\n")
        lines.append("")
    return "\n".join(lines)


def priorities(rows):
    result=[]
    for status,title,risk,need in [
        ("over_token_budget","Nghiên cứu tách segment có spans, giữ đủ context", "Cao: có thể tách mất phủ định/điều kiện hoặc context tự nó quá dài",True),
        ("blocked_source_or_context","Đối chiếu vùng parser/context/nguồn bị chặn", "Cao: không khôi phục đánh số hoặc nội dung bằng suy đoán",True),
        ("unsupported_structure","Thiết kế hỗ trợ Điều lá sau khi xác định scope", "Cần giữ trọn cấu trúc/điều kiện; chưa biết bao nhiêu đơn vị thuộc nghiệp vụ",True)]:
        selected=[r for r in rows if r["status"]==status]
        if selected:result.append({"proposal_only":True,"work":title,"candidates_to_investigate":len(selected),"improvement_upper_bound":len(selected),
                                   "improvement_not_demonstrated":True,"scope_stages":dict(Counter(r["scope"]["stage"] for r in selected)),
                                   "scope_proposal_values":dict(Counter(str(r["scope"]["scope_proposal"]) for r in selected if r["scope"]["proposal_record_present"])),
                                   "scope_decision_values":dict(Counter(r["scope"]["scope_status"] for r in selected if r["scope"]["stage"]=="decision_recorded")),
                                   "risk":risk,"required_before_embedding_selected_candidates":need})
    return result[:3]


def report_text(summary):
    lines=["# Khảo sát khả năng chunking trên bốn cây DOCX", "", "Snapshot 2025-01-01; origin=agent_review; preview_only. Không phải độ phủ nghiệp vụ/toàn nguồn hoặc release-ready.",
           "Không dùng mapping PDF Điều 22. Builder/policy/encoder/token budget giữ nguyên Stage6; không parser repair, truncate hoặc bỏ context.", "",
           "## Mẫu số và trạng thái", "", "Document/Chương/Mục và cha Điều/Khoản có con là context-only, không phải target thất bại. Khoản/Điểm lá là mẫu số target được hỗ trợ; Điều lá có chữ được thống kê chưa hỗ trợ riêng.",
           "", "| Văn bản | Units | Context-only | Khoản/Điểm lá | Preview | Chặn nguồn/context | Vượt 256 | Chưa hỗ trợ | Lỗi thực thi | Thành công trên nhóm hỗ trợ |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name,s in list(summary["documents"].items())+[("TỔNG",summary["total"])]:
        c=s["final_status_counts"];rate=s["supported_success_rate"]
        lines.append(f"| {name} | {s['legal_units']} | {s['context_only']} | {s['supported_targets']} | {c['preview_available']} | {c['blocked_source_or_context']} | {c['over_token_budget']} | {c['unsupported_structure']} | {c['execution_error']} | {rate['numerator']}/{rate['denominator']} ({100*rate['ratio']:.2f}%) |" if rate['ratio'] is not None else f"| {name} | không có target hỗ trợ |")
    lines += ["","| Văn bản | Document | Chương | Mục | Điều | Khoản | Điểm |","|---|---:|---:|---:|---:|---:|---:|"]
    for name,s in list(summary["documents"].items())+[("TỔNG",summary["total"])]:
        lines.append("| "+name+" | "+" | ".join(str(s["unit_types"].get(k,0)) for k in ["document","chapter","section","article","clause","point"])+" |")
    lines += ["", "Chi tiết từng loại unit/target và reason ở coverage_summary.json, từng unit ở unit_coverage.jsonl/CSV. Primary reason ưu tiên: "+" → ".join(PRIORITY)+".",
              "Toàn bộ reasons/impacts là những gì builder thực tế trả về, không phải kiểm định song song. Builder dừng sớm khi lỗi, nên nguyên nhân ở bước chưa chạy hoặc token chưa đo giữ unknown/null, không suy đoán.",
              "", "## Token trên encoder_text", "", "Đếm gồm special tokens, không truncate. Quantile nearest-rank; mẫu số là candidate đo được, không gồm context-only hoặc target bị chặn trước encoder.",
              "", "| Văn bản | Mẫu đo | p50 | p95 | Max | 257–384 | 385–512 | >512 | Tổng unknown | Candidate có unknown |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name,s in list(summary["documents"].items())+[("TỔNG",summary["total"])]:
        d=s["token_distribution"];b=s["overflow_buckets"]
        lines.append(f"| {name} | {d['n']} | {d['p50']} | {d['p95']} | {d['max']} | {b['257_384']} | {b['385_512']} | {b['over_512']} | {s['unknown_tokens']} | {s['candidates_with_unknown']} |")
    lines += ["","Primary reason phổ biến (mỗi candidate chỉ một lần):",""]
    for reason,count in sorted(summary["total"]["primary_failure_reasons"].items(),key=lambda pair:(-pair[1],pair[0])):
        lines.append(f"- {reason}: {count}")
    lines += ["", "## Scope đã ghi nhận — tách khỏi khả năng chunking", "", "BRD §3.1/§3.3: ưu tiên áp dụng trực tiếp cho người tham gia giao thông; quy hoạch/hạ tầng và quản lý cơ sở không tự thành target nghiệp vụ. Không gán scope bằng keyword hoặc coi cả bốn luật đều included.",
              "Bảng dùng assessment v1.1 đã có, đúng hash cây/unit. Proposal không phải quyết định. Proposal record có scope_candidate=null vẫn tính chưa đánh giá scope, được thống kê riêng số record.",
              "", "| Văn bản | Có quyết định scope | Chỉ proposal có kết luận | Chưa đánh giá/kết luận scope | Tổng proposal records |", "|---|---:|---:|---:|---:|"]
    for name,s in list(summary["documents"].items())+[("TỔNG",summary["total"])]:
        q=s["scope_stages"];lines.append(f"| {name} | {q['decision_recorded']} | {q['proposal_only']} | {q['unassessed']} | {s['scope_proposal_records']} |")
    lines += ["", "## Vùng nguồn chưa đầy đủ trong cây", "", f"{summary['source_gap_record_count']} record parser/coverage/table trong source_gaps.jsonl; các lớp có thể trùng vùng, không phải số unit hoặc số lỗi độc lập. Không đưa vùng này vào mẫu số, không tạo unit giả. Bảng/field/đánh số/suspended regions còn nguyên locator, offsets và lý do. Bảng supporting/non-body được liệt kê để truy vết, không mặc định là target bị lỗi.",
              "", "## Vấn đề kỹ thuật và blocker pháp lý", "", "Lỗi thực thi khảo sát: "+str(summary["total"]["final_status_counts"]["execution_error"])+" candidate. Xem execution_errors.jsonl; candidate lỗi không tính đạt.",
              "Blocker nguồn/pháp lý còn pending (không phải lỗi cấu trúc chunking): "+", ".join(LEGAL_BLOCKERS)+".",
              "Không có reviewer event mới, corpus/index hoặc kích hoạt ứng dụng. Tỷ lệ kỹ thuật chỉ trên cây đã parse; không chứng minh toàn văn, scope hay hiệu lực.",
              "", "## Tối đa ba ưu tiên — đề xuất, chưa triển khai", ""]
    for i,p in enumerate(summary["next_priorities"],1):
        lines.append(f"{i}. {p['work']}: {p['candidates_to_investigate']} candidate cần khảo sát; đây là cận trên tiềm năng, chưa chứng minh khắc phục được tất cả. Scope: {canonical(p['scope_stages'])}; proposal: {canonical(p['scope_proposal_values'])}; quyết định: {canonical(p['scope_decision_values'])}. Rủi ro: {p['risk']}. Cần xử lý trước embedding các candidate được chọn.")
    lines += ["", "Mẫu ngắn ở samples.md; không sao chép hàng loạt nguyên văn trong báo cáo. Các preview/quarantine đầy đủ và source proofs nằm riêng ở preview/; toàn bộ nguồn/units cũ trong inputs/ được giữ nguyên byte.", ""]
    return "\n".join(lines)


def check_config(run, config):
    expected=load_json(BASE_DIR/"config/stage6_points.v1.json")["chunk"]
    expected={k:v for k,v in expected.items() if k!="target_unit_ids"}
    if (config["version"]!=VERSION or config["snapshot_date"]!=SNAPSHOT_DATE or config["chunk"]!=expected
            or type(config["batch_size"]) is not int or not 1<=config["batch_size"]<=128
            or digest((run/"inputs/tree/manifest.json").read_bytes())!=config["tree_manifest_sha256"]
            or digest((run/"inputs/assessment/manifest.json").read_bytes())!=config["assessment_manifest_sha256"]
            or digest(canonical(load_json(run/"encoder_config.json")).encode())!=config["encoder_config_sha256"]):
        raise ValueError("Survey policy/budget/encoder/input binding mismatch")
    encoder_input.require_config(load_json(run/"encoder_config.json"),run/"tokenizer_assets")


def calculate(run, progress=None):
    config=load_json(run/"config.json");check_config(run,config)
    root=run/"inputs"
    valid=validate_tree(root/"tree/manifest.json",root)
    if not valid["technical_valid"] or not valid["processing_success"]:raise ValueError("Invalid Stage4 tree: "+canonical(valid))
    valid_scope=validate_assessment(root/"assessment/manifest.json",root)
    if not valid_scope["technical_valid"]:raise ValueError("Invalid assessment: "+canonical(valid_scope))
    laws,gaps=load_data(run)
    if sorted(laws)!=sorted(config["laws"]):raise ValueError("Unexpected four-tree source set")
    allunits=[u for data in laws.values() for u in data["units"]]
    scopes=scope_index(root/"assessment",allunits,config["tree_manifest_sha256"])
    outputs={k:[] for k in ["chunks","contexts","issues","quarantined","encoder_inputs","unit_results","dependency_checks","execution_errors"]}
    rows=[];runtime={}
    def encode(texts):
        r=encoder_input.encode_inputs(texts,load_json(run/"encoder_config.json"),run/"tokenizer_assets")
        runtime.update({k:v for k,v in r.items() if k!="rows"});return r["rows"]
    for law in sorted(laws):
        data=laws[law]
        output=execute_batches(data,root,config["chunk"],encode,config["batch_size"],progress)
        rows.extend(unit_rows(data,output,scopes))
        for key in outputs:outputs[key].extend(output[key])
    rows.sort(key=lambda r:(r["law_id"],r["unit_id"]))
    outputs["chunks"].sort(key=lambda c:c["chunk_id"]);outputs["contexts"].sort(key=lambda c:(c["chunk_id"],c["context_order"]))
    require_preview_schema(outputs["chunks"])
    summary={"version":VERSION,"snapshot_date":SNAPSHOT_DATE,"origin":"agent_review","preview_only":True,"release_eligible":False,
             "tree_manifest_sha256":config["tree_manifest_sha256"],"chunk_policy_version":builder.VERSION,"token_limit":256,
             "documents":{law:summarize([r for r in rows if r["law_id"]==law]) for law in sorted(laws)},"total":summarize(rows),
             "source_gap_record_count":len(gaps),"legal_release_blockers":LEGAL_BLOCKERS,"next_priorities":priorities(rows)}
    report={"technical_valid":True,"survey_completed":True,"execution_error_candidates":len(outputs["execution_errors"]),
            "all_candidates_successful":all(r["status"]=="preview_available" for r in rows if r["is_candidate"]),
            "legal_units":len(rows),"supported_targets":summary["total"]["supported_targets"],"preview_count":len(outputs["chunks"]),
            "quarantine_count":len(outputs["quarantined"]),"origin":"agent_review","human_reviewer_event_count":0,
            "preview_only":True,"release_eligible":False,"corpus_created":False,"legal_release_blockers":LEGAL_BLOCKERS,
            "inference_loaded":False,"truncation":False}
    return rows,outputs,gaps,summary,report,runtime


def validate(manifest_path, progress=None):
    p=Path(manifest_path).resolve()
    if p.name!="manifest.json":raise ValueError("Expected manifest.json")
    m=check_files(p);run=p.parent
    if (m["manifest_type"]!=VERSION or m["files"]!=inventory(run) or m["code_sha256"]!=code_binding()
            or m["config_sha256"]!=digest((run/"config.json").read_bytes()) or m["snapshot_date"]!=SNAPSHOT_DATE
            or m["origin"]!="agent_review" or m["release_eligible"] is not False or m["preview_only"] is not True
            or m["human_reviewer_event_count"]!=0 or m["corpus_version"] is not None):raise ValueError("Survey manifest binding/pending mismatch")
    rows,out,gaps,summary,report,runtime=calculate(run,progress)
    for file,key in EXPORTS.items():
        if read_rows(run/file)!=out[key]:raise ValueError("Survey replay mismatch: "+file)
    for file,value in [("unit_coverage.jsonl",rows),("source_gaps.jsonl",gaps)]:
        if read_rows(run/file)!=value:raise ValueError("Survey replay mismatch: "+file)
    for file,value in [("coverage_summary.json",summary),("validation_report.json",report),("runtime.json",runtime)]:
        if load_json(run/file)!=value:raise ValueError("Survey replay mismatch: "+file)
    for file,value in [("unit_coverage.csv",csv_text(rows)),("coverage_report.md",report_text(summary)),("samples.md",samples_text(rows))]:
        if (run/file).read_text(encoding="utf8")!=value:raise ValueError("Readable survey/export mismatch: "+file)
    return report


def build(tree_manifest,assessment_manifest,run_dir,tokenizer_dir=None,config_path=DEFAULT_CONFIG,raw_root=BASE_DIR,progress=None):
    target=staging_path(run_dir);tree=Path(tree_manifest).resolve().parent;assessment=Path(assessment_manifest).resolve().parent
    if tree in target.parents or assessment in target.parents:raise ValueError("Output cannot be inside an old input run")
    config=load_json(config_path)
    if digest(Path(tree_manifest).read_bytes())!=config["tree_manifest_sha256"] or digest(Path(assessment_manifest).read_bytes())!=config["assessment_manifest_sha256"]:
        raise ValueError("Unexpected source manifests")
    if not validate_tree(tree_manifest,raw_root)["technical_valid"] or not validate_assessment(assessment_manifest,raw_root)["technical_valid"]:
        raise ValueError("Invalid source tree or assessment")
    enc=load_json(BASE_DIR/"config/stage6_preview.v1.json")["encoder"];assets=Path(tokenizer_dir or default_tokenizer_dir())
    encoder_input.require_config(enc,assets)
    with staged_run(run_dir,VERSION,tree_manifest) as (run,run_report):
        (run/"inputs").mkdir();shutil.copytree(tree,run/"inputs/tree");shutil.copytree(assessment,run/"inputs/assessment")
        source=tree/"extraction_snapshot/source_snapshot"
        refs={f["measured"]["raw_file_ref"] for f in read_rows(source/"files.pending.jsonl")}
        refs|={d["declared"]["inventory_ref"] for d in read_rows(source/"documents.pending.jsonl")}
        for ref in sorted(refs):
            p=resolve_ref(run/"inputs",ref);p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(resolve_ref(raw_root,ref),p)
        (run/"tokenizer_assets").mkdir()
        for name in ASSETS:shutil.copyfile(assets/name,run/"tokenizer_assets"/name)
        write_json(run/"config.json",config);write_json(run/"encoder_config.json",enc)
        rows,out,gaps,summary,report,runtime=calculate(run,progress)
        (run/"preview").mkdir()
        for file,key in EXPORTS.items():write_rows(run/file,out[key])
        write_rows(run/"unit_coverage.jsonl",rows);write_rows(run/"source_gaps.jsonl",gaps)
        for file,value in [("coverage_summary.json",summary),("validation_report.json",report),("runtime.json",runtime)]:write_json(run/file,value)
        for file,value in [("unit_coverage.csv",csv_text(rows)),("coverage_report.md",report_text(summary)),("samples.md",samples_text(rows))]:
            (run/file).write_text(value,encoding="utf8",newline="\n")
        seal(run,{"manifest_type":VERSION,"built_at":now(),"snapshot_date":SNAPSHOT_DATE,"code_sha256":code_binding(),
                  "config_sha256":digest((run/"config.json").read_bytes()),"origin":"agent_review","preview_only":True,
                  "human_reviewer_event_count":0,"release_eligible":False,"corpus_version":None})
        run_report.update(report)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description="Survey actual DOCX trees with the unchanged Stage6 builder/encoder; pending only")
    sub=p.add_subparsers(dest="command",required=True)
    create=sub.add_parser("build")
    create.add_argument("--tree-manifest",type=Path,required=True);create.add_argument("--assessment-manifest",type=Path,required=True)
    create.add_argument("--run-dir",type=Path,required=True);create.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    create.add_argument("--tokenizer-dir",type=Path);create.add_argument("--raw-root",type=Path,default=BASE_DIR)
    check=sub.add_parser("validate");check.add_argument("--manifest",type=Path,required=True)
    args=p.parse_args(argv)
    def progress(law,done,total):print(f"{law}: {done}/{total} candidate",file=sys.stderr,flush=True)
    try:
        report=build(args.tree_manifest,args.assessment_manifest,args.run_dir,args.tokenizer_dir,args.config,args.raw_root,progress) if args.command=="build" else validate(args.manifest,progress)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 2 if report["execution_error_candidates"] else 0
    except Exception as exc:
        print(json.dumps({"technical_valid":False,"errors":[str(exc)],"release_eligible":False},ensure_ascii=False),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
