"""Bounded agent proposals on existing pilot fields/content; no review authority."""
import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import unicodedata

from src import scope_survey as scope, coverage_survey as coverage, chunk_preview as proof, chunk_preview_v2 as builder, encoder_input
from src.assessment_contracts import identity
from src.assessment_evidence import check_files, inventory, seal, now
from src.config import BASE_DIR,SNAPSHOT_DATE
from src.pipeline_cli import staged_run,staging_path,write_json
from src.source_contracts import canonical,digest,resolve_ref
from src.source_registry import read_rows,write_rows,load_json

VERSION="pilot-field-refinement.v1"
DEFAULT_CONFIG=BASE_DIR/"config/pilot_refinement.v1.json"
EXPORTS={"context_field_reviews.jsonl":"fields","scope_proposal_revisions.jsonl":"revisions","pilot_candidates.jsonl":"candidates"}


def code_binding():
    return {n:digest(Path(m.__file__).read_bytes()) for n,m in [("refinement",sys.modules[__name__]),("scope",scope),("builder",builder),("proof",proof),("encoder",encoder_input)]}


def field_key(d):return (d["target_unit_id"],d["unit_id"],d["field_name"],d["char_start"],d["char_end"],d["context_order"])


def ordered_character_map(search,encoder,start,end):
    """Prove retained characters globally; do not invert ambiguous segmentation.

    Original underscores/NFC changes are deliberately unsupported. Inserted
    underscores map to no source character. This does not alter encoder input.
    """
    if "_" in search or unicodedata.normalize("NFC",search)!=search:
        return {"status":"unavailable","reason":"Original underscore or NFC change prevents this restricted proof"}
    a=[(i,c) for i,c in enumerate(search) if not c.isspace()]
    b=[(i,c) for i,c in enumerate(encoder) if not c.isspace() and c!="_"]
    if [c for _,c in a]!=[c for _,c in b]:return {"status":"unavailable","reason":"Non-whitespace character streams differ"}
    mapped={j:i for (i,_),(j,_) in zip(a,b)}
    return {"status":"proved","method":"global_ordered_nonwhitespace_character_bijection_no_original_underscores",
            "search_positions":[mapped[i] for i in range(start,end) if i in mapped],
            "inserted_underscore_positions":[i for i in range(start,end) if encoder[i]=="_"],
            "source_nonwhitespace_count":len(a),"encoder_retained_character_count":len(b)}


def diagnose(chunk,record,unit,spans,cov):
    fresh=encoder_input.encode_inputs([chunk["text_for_search"]],load_json(cov/"encoder_config.json"),cov/"tokenizer_assets")
    row=fresh["rows"][0]
    if any(record[k]!=v for k,v in row.items()):raise ValueError("Unknown diagnosis does not reproduce original encoder evidence")
    vocab={l.rsplit(" ",1)[0] for l in (cov/"tokenizer_assets/vocab.txt").read_text(encoding="utf8").splitlines()}
    mappings=[]
    for q in row["after"]["unknowns"]:
        if not q["source"]:
            mappings.append({"unknown":q,"mapping":{"status":"unavailable","reason":"Tokenizer BPE source proof unavailable"}});continue
        a,b=q["source"]["char_start"],q["source"]["char_end"]
        m=ordered_character_map(chunk["text_for_search"],row["encoder_text"],a,b)
        value={"unknown":q,"mapping":m,"piece_in_vocabulary":q["token_piece"] in vocab,"component":None,"unit_field_positions":[],"extraction_positions":[]}
        if m["status"]=="proved" and m["search_positions"]:
            positions=m["search_positions"]
            comp=next((c for c in proof.search_components(chunk) if all(c["char_start"]<=p<c["char_end"] for p in positions)),None)
            value["component"]=comp["component"] if comp else None
            if comp and comp["component"]=="text_original":
                field_positions=[p-comp["char_start"] for p in positions];value["unit_field_positions"]=field_positions
                offset=0;joined=[]
                for s in sorted([s for s in spans if s["unit_id"]==unit["unit_id"] and s["field_name"]=="text_original"],key=lambda s:s["span_order"]):
                    own_length=s["char_end"]-s["char_start"]
                    for p in field_positions:
                        if offset<=p<offset+own_length:value["extraction_positions"].append({"extraction_id":s["extraction_id"],"span_id":s["span_id"],"char_offset":s["char_start"]+p-offset,"locator":json.loads(s["locator_json"])})
                    offset+=own_length+1;joined.append(s["span_id"])
                if len(value["extraction_positions"])!=len(field_positions):raise ValueError("Cannot map retained target characters to extraction spans")
        mappings.append(value)
    return {"unit_id":unit["unit_id"],"chunk_id":chunk["chunk_id"],"text_for_search":chunk["text_for_search"],"text_original":unit["text_original"],
            "search_components":proof.search_components(chunk),"source_proof":chunk["source_locator"],"source_proof_base_ref":"scope_snapshot/coverage_snapshot/",
            "encoder_config":load_json(cov/"encoder_config.json"),
            "result":fresh,"mappings":mappings,"offset_basis":"Unicode code point, zero based; each named artifact has its own namespace",
            "vocab_do_present":"do" in vocab,"origin":"agent_review","preprocessing_changed":False,"inference_loaded":False,
            "conclusion":"Exact BPE emits _do from segmented có_lý_do; _do is absent from pinned vocabulary. This is a segmentation/BPE/vocabulary interaction, not evidence of broken source encoding.",
            "impact_limit":"One unknown ID replaces that piece only; retrieval/model impact has not been measured. Legal text/spans remain unchanged.",
            "proposed_action":"Keep current policy and diagnostic evidence. A future segmentation-policy experiment must version/query-document configuration and evaluate impact; do not silently delete/replace characters or extend vocabulary."}


def replay_pilot(cov,selected):
    laws,_=coverage.load_data(cov);cfg=load_json(cov/"config.json")["chunk"]
    chunks=read_rows(cov/"preview/chunks.preview.jsonl");contexts=read_rows(cov/"preview/contexts.preview.jsonl")
    for q in read_rows(cov/"preview/quarantined.preview.jsonl"):chunks.append(q["candidate"]);contexts.extend(q["contexts"])
    cc={c["unit_id"]:c for c in chunks};enc={e["unit_id"]:e for e in read_rows(cov/"preview/encoder_inputs.preview.jsonl")}
    lookup={e["input_sha256"]:e for e in enc.values()}
    def cached_measurements(texts):
        return [lookup[digest(t.encode())] for t in texts] # Original tokenizer evidence, not a newly measured count.
    for law,data in laws.items():
        ids=sorted(selected&{u["unit_id"] for u in data["units"]})
        if not ids:continue
        out=builder.build_chunks(data,cov/"inputs",{**cfg,"target_unit_ids":ids},coverage.LEGAL_BLOCKERS,cached_measurements,reference_prefix="inputs/")
        rebuilt=out["chunks"]+[q["candidate"] for q in out["quarantined"]]
        own=out["contexts"]+[c for q in out["quarantined"] for c in q["contexts"]]
        if {c["unit_id"] for c in rebuilt}!=set(ids):raise ValueError("Pilot builder replay lost target")
        for c in rebuilt:
            if c!=cc[c["unit_id"]]:raise ValueError("Pilot content/ID/source replay mismatch")
            expected=sorted([d for d in contexts if d["chunk_id"]==c["chunk_id"]],key=lambda d:d["context_order"])
            if sorted([d for d in own if d["chunk_id"]==c["chunk_id"]],key=lambda d:d["context_order"])!=expected:raise ValueError("Pilot context replay mismatch")
    return laws,cc,enc


def review_fields(dependencies,notes,units):
    notes=scope.unique(notes,"unit_id","field unit annotation") # This bounded input has one selected field per parent.
    result=[]
    for d in dependencies:
        if not d["scope_dependency_pending"]:continue
        u=units[d["unit_id"]];n=notes[u["unit_id"]]
        if (n["unit_sha256"]!=digest(canonical(u).encode()) or n["field_name"]!=d["field_name"] or n["char_start"]!=d["char_start"]
                or n["char_end"]!=d["char_end"] or n["field_sha256"]!=digest(u[d["field_name"]].encode())
                or n["selection_proposal"] not in {"use","needs_more_review","do_not_use"} or not n["reason"].strip() or not n["information_roles"]):raise ValueError("Field annotation unit/hash/offset/meaning mismatch")
        row={**d,"target_unit_sha256":digest(canonical(units[d["target_unit_id"]]).encode()),"context_unit_sha256":n["unit_sha256"],
             "target_text":units[d["target_unit_id"]]["text_original"],"target_citation":units[d["target_unit_id"]]["citation_path"],"context_citation":u["citation_path"],
             "field_text":u[d["field_name"]][d["char_start"]:d["char_end"]],"field_sha256":n["field_sha256"],
             "selection_proposal":n["selection_proposal"],"information_roles":n["information_roles"],"reason":n["reason"],
             "parent_scope_candidate_unchanged":"pending","parent_verified":False,"origin":"agent_review","reviewer_ref":None,"reviewed_at":None,
             "source_locator_base_ref":"scope_snapshot/coverage_snapshot/","release_eligible":False}
        row["field_review_id"]=identity("ctxr_",row);result.append(row)
    if {(d["unit_id"],d["field_name"]) for d in result}!={(n["unit_id"],n["field_name"]) for n in notes.values()}:raise ValueError("Field curation contains unused/missing fields")
    return sorted(result,key=field_key)


def context_state(deps,fields):
    reviews={field_key(r):r for r in fields};proposals=[]
    for d in deps:
        if d["scope_dependency_pending"]:
            if field_key(d) not in reviews:raise ValueError("Missing target-specific field assessment")
            proposals.append(reviews[field_key(d)]["selection_proposal"])
        else:proposals.append("use_from_prior_scoped_context_proposal")
    return "needs_more_review" if any(p in {"needs_more_review","do_not_use"} for p in proposals) else "all_fields_proposed_for_use"


def assemble(previous,notes,units,dependencies,fields,chunks,enc,original_proposals,binding):
    selected={p["unit_id"] for p in previous};notes=scope.unique(notes,"unit_id","pilot annotation")
    if set(notes)!=selected:raise ValueError("Refinement must cover exactly prior included pilot, no expansion")
    revisions=[];candidates=[]
    for p in previous:
        uid=p["unit_id"];u=units[uid];n=notes[uid];c=chunks[uid];e=enc[uid]
        if (n["unit_sha256"]!=digest(canonical(u).encode()) or n["unit_sha256"]!=p["unit_sha256"] or n["previous_proposal_id"]!=p["proposal_id"]
                or n["previous_proposal_sha256"]!=digest(canonical(p).encode()) or n["scope_candidate"] not in {"included","supporting","pending","excluded"}
                or not set(n["use_cases"])<={"UC-01","UC-02","UC-03"} or not n["use_cases"] or type(n["review_completed"]) is not bool
                or not n["review_completed"] and n["scope_candidate"]!="pending"):raise ValueError("Proposal binding/review mismatch")
        if any(not n[k].strip() for k in ["regulated_subject","behavior_right_duty","reason","reference_notes","prior_reason_limitation"]) or n["behavior_right_duty"] not in n["reason"]:raise ValueError("Incomplete unit-specific rationale")
        deps=[d for d in dependencies if d["target_unit_id"]==uid]
        if n["scope_candidate"]=="supporting":raise ValueError("No new supporting role without explicit target/field dependency in this bounded task")
        row={**n,"law_id":u["law_id"],"citation_path":u["citation_path"],"binding":binding,"policy_version":VERSION,
             "scope_label_relation":"unchanged" if n["scope_candidate"]==p["scope_candidate"] else "changed_agent_proposal",
             "previous_proposal_ref":"scope_snapshot/scope_proposals.jsonl","evidence_refs":p["evidence_refs"],
             "brd_basis_ref":"scope_snapshot/requirements_snapshot/"+scope.BRD,"brd_locator":"§3.1/§3.2/§3.3",
             "scope_status":None,"decision_ids":dict.fromkeys(["scope","applicability","technical"]),"reviewer_ref":None,"reviewed_at":None,
             "origin":"agent_review","release_eligible":False,"corpus_version":None,"snapshot_date":SNAPSHOT_DATE}
        row["proposal_id"]=identity("pr_",row);revisions.append(row)
        prior=original_proposals.get(uid)
        todo=["Đối chiếu đúng bản nguồn chính thức và nội dung/phạm vi đang dùng; DOCX legacy vẫn thiếu provenance.",
              "Ghi kết quả technical review có phạm vi theo contract hiện hành; quan sát agent chưa là quyết định reviewer.",
              "Đối chiếu hiệu lực/sửa đổi/ngoại lệ tại 2025-01-01 cho target và các context, giữ chứng cứ và quyết định thật."]
        if n["scope_candidate"]=="pending":todo.append("Làm rõ ca sử dụng/đối tượng/dẫn chiếu trong lý do scope mới trước khi kết luận target.")
        if p["coverage_status"]=="over_token_budget":todo.append("Candidate/context còn nguyên trong quarantine; cần thiết kế xử lý dài riêng, chưa tách/truncate.")
        state=context_state(deps,fields)
        if state=="needs_more_review":todo.append("Giải quyết field context còn cần xem thêm; không bỏ nó để vừa budget.")
        if e["unknown_tokens"]:todo.append("Giữ chẩn đoán unknown; chưa đo tác động retrieval, chưa thay preprocessing/vocabulary.")
        candidates.append({"unit_id":uid,"unit_sha256":n["unit_sha256"],"law_id":u["law_id"],"citation_path":u["citation_path"],
                           "scope_proposal":n["scope_candidate"],"proposal_id":row["proposal_id"],"scope_reason":n["reason"],
                           "text_original":c["text_original"],"chunk_id":c["chunk_id"],"content_sha256":c["content_sha256"],
                           "chunk_capability":p["coverage_status"],"tokens_with_special":e["tokens_with_special"],"unknown_tokens":e["unknown_tokens"],
                           "context_selection_proposal":state,"context_field_review_ids":[f["field_review_id"] for f in fields if f["target_unit_id"]==uid],
                           "context_dependencies":deps,"source_proof":c["source_locator"],"source_proof_base_ref":"scope_snapshot/coverage_snapshot/",
                           "source_evidence":{"status":"pending","available":["Raw/extraction hashes","Unit/span/locator roundtrip","BRD scope basis"],
                                              "prior_assessment_proposal_id":prior["proposal_id"] if prior else None,
                                              "prior_finding_ids":prior["finding_ids"] if prior else [],"prior_date_rule_id":prior["date_rule_id"] if prior else None,
                                              "prior_evidence_base_ref":"scope_snapshot/coverage_snapshot/inputs/assessment/"},
                           "technical_review":{"agent_checks":"Existing builder replay exact; source/context slices/hash/relationships match","reviewer_decision":None},
                           "applicability":{"status":"pending_review","effective_from":None,"effective_to":None,"reviewer_decision":None},
                           "next_work":todo,"origin":"agent_review","snapshot_date":SNAPSHOT_DATE,"scope_status":None,"reviewer_ref":None,"reviewed_at":None,
                           "release_eligible":False,"corpus_version":None})
    return sorted(revisions,key=lambda r:r["unit_id"]),sorted(candidates,key=lambda r:r["unit_id"])


def calculate(run):
    cfg=load_json(run/"config.json");snap=run/"scope_snapshot";cov=snap/"coverage_snapshot"
    if cfg["version"]!=VERSION or cfg["snapshot_date"]!=SNAPSHOT_DATE or digest((snap/"manifest.json").read_bytes())!=cfg["input_manifest_sha256"]:raise ValueError("Refinement version/snapshot/input binding mismatch")
    sm=check_files(snap/"manifest.json")
    if sm["files"]!=inventory(snap) or sm["code_sha256"]!=scope.code_binding():raise ValueError("Original scope input/code changed")
    previous=[p for p in read_rows(snap/"scope_proposals.jsonl") if p["scope_candidate"]=="included"]
    selected={p["unit_id"] for p in previous};laws,chunks,enc=replay_pilot(cov,selected)
    units={u["unit_id"]:u for data in laws.values() for u in data["units"]};spans=[s for data in laws.values() for s in data["spans"]]
    deps=read_rows(snap/"context_dependencies.jsonl")
    for d in deps:
        data=laws[units[d["unit_id"]]["law_id"]]
        if proof.source_proof(data,cov/"inputs",units[d["unit_id"]],d["field_name"],"inputs/")!=d["source_locator"]:raise ValueError("Context source evidence differs from original builder")
    fields=review_fields(deps,cfg["field_reviews"],units)
    binding={"scope_manifest_sha256":cfg["input_manifest_sha256"],"config_sha256":digest(canonical(cfg).encode()),"tree_binding":previous[0]["binding"],"refinement_policy":VERSION}
    old=scope.unique(read_rows(cov/"inputs/assessment/machine_proposals.jsonl"),"unit_id","original pilot proposal")
    revisions,candidates=assemble(previous,cfg["scope_reviews"],units,deps,fields,chunks,enc,old,binding)
    unknown=[uid for uid in selected if enc[uid]["unknown_tokens"]]
    if len(unknown)!=1:raise ValueError("Unexpected unknown pilot set; explicit diagnostic scope needs review")
    uid=unknown[0];diag=diagnose(chunks[uid],enc[uid],units[uid],spans,cov)
    included=[p for p in candidates if p["scope_proposal"]=="included"]
    summary={"technical_valid":True,"pilot_records":len(candidates),"agent_scope_reviews":len(revisions),"scope_labels":dict(Counter(p["scope_proposal"] for p in candidates)),
             "scope_label_relations":dict(Counter(p["scope_label_relation"] for p in revisions)),
             "scope_needs_more_review":sum(p["scope_proposal"]=="pending" for p in candidates),"unread_targets":sum(not p["review_completed"] for p in revisions),
             "field_review_rows":len(fields),"field_review_targets":len({f["target_unit_id"] for f in fields}),"distinct_parent_fields":len(cfg["field_reviews"]),
             "field_selection_counts":dict(Counter(f["selection_proposal"] for f in fields)),
             "field_targets_needing_more_review":len({f["target_unit_id"] for f in fields if f["selection_proposal"]!="use"}),
             "pilot_chunk_capability":dict(Counter(p["chunk_capability"] for p in candidates)),
             "included_chunk_capability":dict(Counter(p["chunk_capability"] for p in included)),
             "included_context_selection":dict(Counter(p["context_selection_proposal"] for p in included)),
             "included_from_pending_parent_with_fields_proposed_for_use":sum(bool(p["context_field_review_ids"]) and p["context_selection_proposal"]=="all_fields_proposed_for_use" for p in included),
             "unknown_tokens":sum(p["unknown_tokens"] for p in candidates),"human_reviewer_events":0,"release_eligible":False,"legal_blockers":coverage.LEGAL_BLOCKERS}
    return {"fields":fields,"revisions":revisions,"candidates":candidates},diag,summary,chunks,units


def unknown_md(diag):
    e=diag["result"]["rows"][0];lines=["# Unknown token — Luật36 Điều62 Khoản5 Điểm c","", "Đúng model/revision/preprocessing đã pin; tokenizer-only, không inference hoặc sửa nội dung.","",
        "| Input | Token gồm special | Unknown |","|---|---:|---:|"]
    for k in ["before","whitespace_only","after"]:lines.append(f"| {k} | {e[k]['tokens_with_special']} | {e[k]['unknown_tokens']} |")
    lines += ["", "before/whitespace_only là probe chẩn đoán, không thay encoder input hiện hành. before có unknown LF của phép ghép; sau whitespace LF mất. after có một unknown mới ở mảnh BPE sau PyVi, khác nguyên nhân LF.", ""]
    for x in diag["mappings"]:
        q=x["unknown"];lines += [f"- Token position {q['token_position']} (từ 0, gồm special), ID={q['token_id']}, piece={q['token_piece']!r}, source={canonical(q['source'])}.",
                                   "- Component="+str(x.get("component"))+"; mapping="+canonical(x["mapping"])+".",
                                   "- Offsets trong text_original="+canonical(x.get("unit_field_positions",[]))+"; extraction="+canonical(x.get("extraction_positions",[]))+"."]
    lines += ["",diag["conclusion"],"",diag["impact_limit"],"",diag["proposed_action"],"",
              "Tokenizer không có native offset_mapping. Source fragment được chứng minh bằng regex/BPE replay khớp IDs; mapping sang search dùng toàn chuỗi ký tự không-whitespace theo đúng thứ tự, chỉ khi NFC không đổi và nguồn không có underscore. Underscore thêm bởi segmentation không có source offset; không đoán inverse mapping. Từ field sang extraction dùng spans + LF join đã kiểm roundtrip.",
              "", "Literal nguồn không có replacement character/encoding error được quan sát trong phép kiểm này. _do vắng trong vocab đã pin, do có trong vocab; không sửa vocab hoặc thay có_lý_do để ép unknown=0. Tác động retrieval chưa được đo.",""]
    return "\n".join(lines)


def fulltext_md(out,chunks,units):
    chosen={p["unit_id"] for p in out["candidates"] if p["chunk_capability"]=="over_token_budget" or p["unknown_tokens"] or p["scope_proposal"]!="included"}
    lines=["# Nguyên văn các ca ưu tiên — agent_review, chưa là quyết định","", "Các namespace offsets tách riêng; giữ cả candidate quá dài/context cần xem thêm, không cắt.",""]
    for p in out["candidates"]:
        if p["unit_id"] not in chosen:continue
        c=chunks[p["unit_id"]];lines += ["## "+p["citation_path"],"", "unit_id="+p["unit_id"]+f"; scope={p['scope_proposal']}; coverage={p['chunk_capability']}; token={p['tokens_with_special']}; unknown={p['unknown_tokens']}","",p["scope_reason"],"", "### Target đầy đủ","","```text",c["text_original"],"```","", "Nguồn target: `"+c["source_locator"]+"`",""]
        for d in sorted(p["context_dependencies"],key=lambda d:d["context_order"]):
            lines += [f"### Context {d['context_order']}: {units[d['unit_id']]['citation_path']} — {d['field_name']}","", f"Field offsets [{d['char_start']},{d['char_end']}); unit_id={d['unit_id']}","","```text",units[d["unit_id"]][d["field_name"]][d["char_start"]:d["char_end"]],"```","", "Nguồn context: `"+d["source_locator"]+"`",""]
        lines += ["Gốc đường dẫn trong proof: scope_snapshot/coverage_snapshot/; xem scope_proposal_revisions.jsonl để đọc giới hạn dẫn chiếu/ngoại lệ.",""]
    return "\n".join(lines)


def report_md(summary):
    return "\n".join(["# Pilot refinement — đề xuất agent có phạm vi", "", "Snapshot 2025-01-01. Không mở rộng ngoài 107 included cũ; không có quyết định reviewer hoặc dữ liệu phục vụ.","",
        "Lý do cũ chủ yếu là nhóm nghiệp vụ + đoạn trích đầu. Lượt này đọc toàn target/context, bổ sung đối tượng, hành vi/quyền/nghĩa vụ, use case BRD và giới hạn riêng từng unit. Config là các annotation unit/hash rõ ràng, không keyword classifier.","",
        "```json",__import__('json').dumps(summary,ensure_ascii=False,indent=2),"```","",
        "Context field được đề xuất dùng không xác nhận scope hay verified toàn cha. Scope cha pending không tự chặn field đã có đánh giá phù hợp. Field needs_more_review hoặc do_not_use vẫn giữ trong candidate, không bỏ để vừa budget. Scope target và lựa chọn field là hai đánh giá khác nhau.","",
        "Tập pilot_candidates giữ đủ 107 hồ sơ, gồm scope pending và nguồn/hiệu lực pending. chunk_capability/token/unknown là bằng chứng kỹ thuật riêng; không có trạng thái ready. Có raw/extraction/span/BRD và hồ sơ evidence cũ gắn đúng binding; thiếu đối chiếu bản chính thức/phạm vi, technical decision thực tế và applicability cho target/context. Không dùng test đạt để xác minh scope.","",
        "Mỗi proposal sửa có ID/hash tham chiếu proposal cũ, giữ nguyên unit_id/nguồn và không viết decision. Các ngày hiệu lực/reviewer vẫn null. Nguyên văn, context, search, ID/hash chunk và quarantine cũ không đổi. Xem priority_cases_fulltext.md và unknown_diagnostics.md.","",
        "## Tối đa ba bước tiếp theo — chưa triển khai","",
        "1. Làm rõ các proposal scope pending và field Điều47 Khoản5: đối tượng/dẫn chiếu/ca sử dụng cụ thể, không thêm toàn nhánh hoặc ghép context bằng đoán.",
        "2. Thiết kế xử lý dài cho proposed included còn quá budget, giữ spans và điều kiện/context; chưa tách hoặc thay policy trong lượt này.",
        "3. Hoàn thiện nguồn, technical/applicability có bằng chứng cho tập chọn. Giữ unknown và đề xuất thử nghiệm policy/evaluation riêng nếu cần, không đổi model/vocab/preprocessing để ép số 0.","",
        "Các bước có thể giao nhau. Chưa xác minh pháp lý/corpus, embedding/index hoặc kích hoạt ứng dụng.",""])


def csv_text(rows):
    keys=["law_id","citation_path","unit_id","scope_proposal","scope_reason","chunk_capability","tokens_with_special","unknown_tokens","context_selection_proposal","source_evidence","technical_review","applicability","next_work","origin","release_eligible"]
    out=io.StringIO(newline="");w=csv.DictWriter(out,fieldnames=keys,lineterminator="\n");w.writeheader()
    for r in rows:w.writerow({k:canonical(r[k]) if isinstance(r[k],(dict,list)) else r[k] for k in keys})
    return out.getvalue()


def views(run,out,diag,summary,chunks,units):
    return {"pilot_refinement_report.md":report_md(summary),"unknown_diagnostics.md":unknown_md(diag),"priority_cases_fulltext.md":fulltext_md(out,chunks,units),"pilot_candidates.csv":csv_text(out["candidates"])}


def build(manifest,run_dir,config=DEFAULT_CONFIG):
    target=staging_path(run_dir);source=Path(manifest).resolve().parent;cfg=load_json(config)
    if source in target.parents:raise ValueError("Output cannot be inside sealed input")
    if digest(Path(manifest).read_bytes())!=cfg["input_manifest_sha256"]:raise ValueError("Wrong scope input")
    scope.validate(manifest)
    with staged_run(run_dir,VERSION,manifest) as (run,status):
        shutil.copytree(source,run/"scope_snapshot");write_json(run/"config.json",cfg)
        out,diag,summary,chunks,units=calculate(run)
        for path,key in EXPORTS.items():write_rows(run/path,out[key])
        write_json(run/"unknown_diagnostics.json",diag);write_json(run/"validation_report.json",summary)
        for path,text in views(run,out,diag,summary,chunks,units).items():(run/path).write_text(text,encoding="utf8",newline="\n")
        seal(run,{"manifest_type":VERSION,"snapshot_date":SNAPSHOT_DATE,"built_at":now(),"input_manifest_sha256":cfg["input_manifest_sha256"],"code_sha256":code_binding(),
                  "origin":"agent_review","release_eligible":False,"corpus_version":None,"human_reviewer_events":0})
        status.update(summary,technical_valid=True)
    return summary


def validate(manifest):
    m=check_files(manifest);run=Path(manifest).resolve().parent
    if (m["manifest_type"]!=VERSION or m["files"]!=inventory(run) or m["code_sha256"]!=code_binding() or m["snapshot_date"]!=SNAPSHOT_DATE
            or m["origin"]!="agent_review" or m["release_eligible"] is not False or m["corpus_version"] is not None or m["human_reviewer_events"]!=0):raise ValueError("Refinement manifest/code/pending mismatch")
    scope.validate(run/"scope_snapshot/manifest.json")
    out,diag,summary,chunks,units=calculate(run)
    for path,key in EXPORTS.items():
        if read_rows(run/path)!=out[key]:raise ValueError("Refinement output replay mismatch: "+path)
    if load_json(run/"unknown_diagnostics.json")!=diag or load_json(run/"validation_report.json")!=summary:raise ValueError("Diagnostic/summary replay mismatch")
    for path,text in views(run,out,diag,summary,chunks,units).items():
        if (run/path).read_text(encoding="utf8")!=text:raise ValueError("Readable/CSV replay mismatch: "+path)
    return summary


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    b=sub.add_parser("build");b.add_argument("--scope-manifest",type=Path,required=True);b.add_argument("--run-dir",type=Path,required=True);b.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    v=sub.add_parser("validate");v.add_argument("--manifest",type=Path,required=True);a=p.parse_args(argv)
    try:print(canonical(build(a.scope_manifest,a.run_dir,a.config) if a.command=="build" else validate(a.manifest)));return 0
    except Exception as exc:print(canonical({"technical_valid":False,"error":str(exc),"release_eligible":False}),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
