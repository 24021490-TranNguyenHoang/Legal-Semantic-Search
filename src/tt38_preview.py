"""Full TT38 Gazette technical preview using Stage3, layout adapter and builders."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import shutil
import sys

from src import chunk_preview_v2, chunk_preview_articles, encoder_input, content_comparison
from src.assessment_evidence import now, seal, check_files, inventory
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_json, write_rows, unique
from src.extraction_pipeline import validate_run as validate_extraction
from src.ingestion import pdf_layout
from src.legal_parser import check_contracts
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest, resolve_ref

VERSION = "tt38-pdf-preview.v1"
DEFAULT_CONFIG = BASE_DIR / "config/tt38_pdf.v1.json"
BLOCKERS = ["SOURCE_AND_EXTRACTION_PENDING", "AGENT_REVIEW_ONLY", "APPLICABILITY_PENDING_AT_2025_01_01", "EXPERIMENTAL_NOT_CORPUS"]
CODE = ["src/tt38_preview.py", "src/ingestion/pdf_layout.py", "src/ingestion/legal_tree.py", "src/chunk_preview.py",
        "src/chunk_preview_v2.py", "src/chunk_preview_articles.py", "src/encoder_input.py", "src/content_comparison.py"]
LEGACY_ENTRY_SHA = "693edc50f9fa8a7e792ee1b1c4b6daba0c7dd57f471236d3af8750d14ee2599f"


def scope_proposals(units, spans):
    result = []
    by = {u["unit_id"]:u for u in units}
    for u in units:
        p=u
        while p["unit_type"] not in {"article", "document"}:p=by[p["parent_unit_id"]]
        article=p["designation"] if p["unit_type"]=="article" else None
        if article in {"5","10"}:
            scope,reason="excluded","BRD3.3: thiết kế/quản lý hạ tầng, thẩm quyền đặt biển; không trực tiếp quy tắc người tham gia giao thông."
        elif article in {"1","2","3","12"}:
            scope,reason="supporting","BRD3.1/BR-04: phạm vi/định nghĩa/căn cứ thi hành hỗ trợ đọc các quy tắc TT38; chưa là quyết định hiệu lực."
        elif article=="9" and u["unit_type"]=="clause" and u["designation"] in {"1","4"}:
            scope,reason="excluded","BRD3.3: yêu cầu đặt biển/phương án tổ chức giao thông; đối tượng quản lý hạ tầng."
        elif article in {"4","6","7","8","9","11"} and u["unit_type"] in {"clause","point","article"}:
            scope,reason="included" if not any(x["parent_unit_id"]==u["unit_id"] for x in units) else "pending", "BRD3.1/UC-02: quy tắc tốc độ, khoảng cách hoặc điều kiện áp dụng trực tiếp; cha hỗn hợp không truyền nhãn."
        else:scope,reason="pending","Vai trò cấu trúc; chưa kết luận scope toàn cha."
        result.append({"unit_id":u["unit_id"],"unit_sha256":digest(canonical(u).encode()),"scope_proposal":scope,"reason":reason,
            "own_text_read_sha256":digest((u["title"]+"\n"+u["text_original"]).encode()),
            "source_span_ids":[s["span_id"] for s in spans if s["unit_id"]==u["unit_id"]],
            "origin":"agent_review","status":"proposed","reviewer_ref":None,"snapshot_date":SNAPSHOT_DATE,
            "applicability":"pending_review","effective_from":None,"effective_to":None,"release_eligible":False})
    return result


def derive_rows(tables, cells, units):
    by={c["cell_id"]:c for c in cells};ub={u["unit_id"]:u for u in units};result=[]
    for t in tables:
        slots=t["cell_slots"]; start=1 if t["number"]==3 else 2
        for ri in range(start,len(slots)):
            parts=[];refs=[]
            for ci,cid in enumerate(slots[ri]):
                if cid is None:raise ValueError("Unexpected missing data cell")
                headers=[slots[0][ci]] if t["number"]==3 else ([slots[0][0]] if ci==0 else [slots[0][1],slots[1][ci]])
                refs.extend(headers+[cid]);parts.append(" / ".join(by[h]["text"] for h in headers)+": "+by[cid]["text"])
            owner=ub[t["context_unit_id"]]; ancestors=[]; parent=ub.get(owner["parent_unit_id"])
            while parent and parent["unit_type"]!="document":
                if parent["unit_type"] in {"article","clause"}:
                    ancestors.insert(0,{"unit_id":parent["unit_id"],"title_original":parent["title"],"text_original":parent["text_original"]})
                parent=ub.get(parent["parent_unit_id"])
            result.append({"table_id":t["table_id"],"row":ri,"owner_unit_id":t["context_unit_id"],
                "owner_lead_original":ub[t["context_unit_id"]]["text_original"],"text_derived":"\n".join(parts),
                "ancestor_context_original":ancestors,
                "source_cell_ids":refs,"status":"quarantined_unsupported_table_chunk_policy","not_a_chunk":True,
                "normalization":"NONE; generated header/value labels separated with colon and LF", "release_eligible":False})
    return result


def comparison(root):
    import pdfplumber
    captures=[]
    for ref in ["sources/selected.pdf","sources/comparison.pdf"]:
        with pdfplumber.open(root/ref) as p:
            chunks=[]
            for page in p.pages:
                lines=(page.extract_text() or "").splitlines()
                if lines and ("CÔNG BÁO/Số" in lines[0] or lines[0].isdigit()):lines=lines[1:]
                chunks.extend(lines)
            body="\n".join(chunks)
            for marker in ["KT. BỘ TRƯỞNG","Nơi nhận:"]:
                if marker in body:body=body[:body.index(marker)]
            captures.append(body)
    output=[]
    for n in range(1,13):
        sections=[]
        for value in captures:
            a=re.search(rf"(?m)^Điều {n}\. ",value)
            if not a:raise ValueError("Missing comparison article")
            stop=re.search(r"(?m)^(?:Điều \d+\. |Chương )",value[a.end():])
            sections.append(value[a.start():a.end()+stop.start() if stop else len(value)].rstrip())
        # compare_fields is exact and reports all formatting/content differences.
        output.append({"article":n,"comparison_kind":"diagnostic_not_legal_equivalence", "source_order":"local7_vs_gazette8",
                       **content_comparison.compare_fields(sections[1],sections[0])})
    return output


def calculate(root, cfg, *, tokenize=False):
    import pdfplumber
    records=rows(root/"extraction_snapshot/extractions.pending.jsonl")
    if len(records)!=1 or records[0]["law_id"]!=cfg["law_id"]:raise ValueError("TT38 requires exactly one selected edition")
    rec=records[0];eid=rec["extraction"]["extraction_id"]
    text=(root/"extraction_snapshot"/rec["extraction"]["text_ref"]).read_text(encoding="utf8")
    trace=load(root/"extraction_snapshot"/rec["trace_ref"])
    if digest((root/"sources/selected.pdf").read_bytes())!=cfg["raw_sha256"] or digest((root/"sources/comparison.pdf").read_bytes())!=cfg["comparison_sha256"]:raise ValueError("Source editions changed")
    with pdfplumber.open(root/"sources/selected.pdf") as pdf:
        if len(pdf.pages)!=8:raise ValueError("Expected eight Gazette pages")
        lines=pdf_layout.page_lines(pdf,rec,text,trace)
        parsed=pdf_layout.parse_layout(rec,text,trace,lines,cfg["tables"])
        tables,cells=pdf_layout.cell_evidence(pdf,lines,parsed["tables"],cfg["tables"],rec,cfg["raw_sha256"],text)
    if [u["designation"] for u in parsed["units"] if u["unit_type"]=="article"] != [str(i) for i in range(1,13)]:raise ValueError("Incomplete actual article order")
    check_contracts(parsed)
    e={**rec["extraction"],"text_ref":"extraction_snapshot/"+rec["extraction"]["text_ref"]}
    data={"document":{k:cfg[k] for k in ["law_id","source_id","law_title","source_url"]},"units":parsed["units"],"spans":parsed["spans"],
          "issues":parsed["issues"],"extractions":[e],"files":[{"file_id":e["file_id"],"law_id":cfg["law_id"],"raw_file_ref":"sources/selected.pdf","sha256":cfg["raw_sha256"],"size_bytes":(root/"sources/selected.pdf").stat().st_size}]}
    ec=load(root/"encoder_config.json")
    if tokenize:
        encode=lambda texts:encoder_input.encode_inputs(texts,ec,root/"tokenizer_assets")["rows"]
    else:
        encoded=rows(root/"encoder_inputs.jsonl");lookup=unique(encoded,"input_sha256")
        for x in encoded:
            if (x["truncation"] is not False or x["model_max_tokens"]!=256 or x["tokens_with_special"]!=len(x["after"]["token_ids"])
                or x["after"]["token_ids_sha256"]!=digest(canonical(x["after"]["token_ids"]).encode())
                or x["encoder_text_sha256"]!=digest(x["encoder_text"].encode()) or x["unknown_tokens"]!=x["after"]["token_ids"].count(3)
                or x["role"]!="document" or x["preprocessing_version"]!=encoder_input.VERSION
                or x["after"]["token_ids"][0]!=0 or x["after"]["token_ids"][-1]!=2):raise ValueError("Invalid cached encoder evidence")
        encode=lambda texts:[lookup[digest(t.encode())] for t in texts]
    combined={k:[] for k in ["chunks","contexts","quarantined","issues","encoder_inputs","unit_results","dependency_checks"]}
    leaves=[u for u in data["units"] if u["unit_type"] in {"article","clause","point"} and not any(v["parent_unit_id"]==u["unit_id"] for v in data["units"])]
    for is_article in [False,True]:
        builder=chunk_preview_articles if is_article else chunk_preview_v2
        c={"chunk_policy_version":builder.VERSION,"snapshot_date":SNAPSHOT_DATE,"token_limit":256,"required_context_fields":["title"],
           "required_clause_context_fields":["text_original"],"target_unit_ids":[u["unit_id"] for u in leaves if (u["unit_type"]=="article")==is_article]}
        out=builder.build_chunks(data,root,c,BLOCKERS,encode)
        for k in combined:combined[k].extend(out[k])
    for k in combined:combined[k].sort(key=canonical)
    proposals=scope_proposals(data["units"],data["spans"])
    encoded={r["unit_id"]:r for r in combined["encoder_inputs"]};states={r["unit_id"]:r for r in combined["unit_results"]}
    coverage=[];blocked=[]
    for u in data["units"]:
        state=states.get(u["unit_id"],{"status":"context_or_structure_only"})
        coverage.append({"unit_id":u["unit_id"],"citation_path":u["citation_path"],"unit_type":u["unit_type"],"status":state["status"],
            "issue":state.get("issue"),"tokens":encoded.get(u["unit_id"],{}).get("tokens_with_special"),"unknown":encoded.get(u["unit_id"],{}).get("unknown_tokens"),
            "scope_proposal":next(p["scope_proposal"] for p in proposals if p["unit_id"]==u["unit_id"]),"applicability":"pending_review"})
        if state.get("issue") and state["issue"]!="TOKEN_BUDGET_EXCEEDED":
            own=[s for s in data["spans"] if s["unit_id"]==u["unit_id"]]
            blocked.append({"unit":u,"spans":own,"reason":state["issue"],"tables":tables,"source_cells":cells,
                "note":"Complete own fields/source spans and all three table objects retained for review; not an admitted chunk"})
    counts={"units":dict(Counter(u["unit_type"] for u in data["units"])),"spans":len(data["spans"]),"leaf_candidates":len(leaves),
        "chunks":len(combined["chunks"]),"contexts":len(combined["contexts"]),"over_budget":len(combined["quarantined"]),"blocked_source_or_structure":len(blocked),
        "tables":len(tables),"physical_cells":len(cells),"derived_rows":sum(len(t["cell_slots"])-(1 if t["number"]==3 else 2) for t in tables),
        "source_codepoints":len(text),"coverage_codepoints":dict(Counter({k:sum(c["char_end"]-c["char_start"] for c in parsed["coverage"] if c["category"]==k) for k in {c["category"] for c in parsed["coverage"]}})),
        "unknown_tokens":sum(x["unknown_tokens"] for x in combined["encoder_inputs"]),"token_min":min((x["tokens_with_special"] for x in combined["encoder_inputs"]),default=None),"token_max":max((x["tokens_with_special"] for x in combined["encoder_inputs"]),default=None)}
    applicability=[]
    for u in data["units"]:
        if u["canonical_path"].endswith("article:12/clause:1"):
            applicability.append({"unit_id":u["unit_id"],"observed_general_effective_date":"2025-01-01","source_span_ids":[s["span_id"] for s in data["spans"] if s["unit_id"]==u["unit_id"]],
                "text_observed":u["text_original"],"origin":"agent_review","status":"candidate_not_unit_applicability_decision","amendment_history_review":"pending","reviewer_ref":None})
    exports={"legal_units.pending":data["units"],"source_spans.pending":data["spans"],"parser_issues":data["issues"],"coverage":parsed["coverage"],
        "layout_blocks":parsed["blocks"],"tables":tables,"cells":cells,"tables.derived":derive_rows(tables,cells,data["units"]),
        "scope.proposals":proposals,"applicability.observed":applicability,"unit_coverage":coverage,"blocked.quarantine":blocked,"comparison":comparison(root),
        **{name:combined[key] for name,key in [("chunks.preview","chunks"),("contexts.preview","contexts"),("encoder_inputs","encoder_inputs"),("chunks.quarantine","quarantined"),("chunk_issues","issues"),("dependency_checks","dependency_checks")]}}
    return exports,counts


def render(exports,counts):
    lines=["# TT38 — toàn văn Công báo, preview pending",canonical(counts),"Origin=agent_review; chưa verified/applicability, không thuộc dataset/index.",
        "| Citation | Trạng thái | Token / unknown | Scope proposal |", "|---|---|---:|---|"]
    lines += [f"| {r['citation_path']} | {r['status']} {r['issue'] or ''} | {r['tokens']} / {r['unknown']} | {r['scope_proposal']} |" for r in exports["unit_coverage"]]
    for u in exports["legal_units.pending"]:lines += ["\n## "+u["citation_path"],u["title"],u["text_original"]]
    for t in exports["tables.derived"]:lines += ["\n## Table derived row (quarantine, không phải chunk)",
        *[c["title_original"]+"\n"+c["text_original"] for c in t["ancestor_context_original"]],
        t["owner_lead_original"],t["text_derived"],"Source cells: "+canonical(t["source_cell_ids"])]
    for c in exports["chunks.preview"]:lines += ["\n## Preview "+c["citation_path"],"`"+c["chunk_id"]+"`",c["context_text"] or "",c["text_original"],"text_for_search:",c["text_for_search"]]
    return "\n\n".join(lines)+"\n"


def require_config(cfg):
    default=load(DEFAULT_CONFIG)
    if set(cfg)!=set(default) or any(cfg[k]!=v for k,v in default.items() if k not in {"extraction_manifest_ref","extraction_manifest_sha256"}):
        raise ValueError("Unknown TT38 source/layout/encoder/budget profile")
    if not re.fullmatch(r"[0-9a-f]{64}",cfg["extraction_manifest_sha256"]):raise ValueError("Invalid extraction binding")


def validate(path):
    path=Path(path).resolve();root=path.parent;m=check_files(path);cfg=load(root/"config.json")
    require_config(cfg)
    expected_code={p:digest((BASE_DIR/p).read_bytes()) for p in CODE}
    if m["code_sha256"].get("src/tt38_preview.py")==LEGACY_ENTRY_SHA:
        expected_code["src/tt38_preview.py"]=LEGACY_ENTRY_SHA  # v1 calculation unchanged; additive CLI routes only.
    if (m["manifest_type"]!=VERSION or m["code_sha256"]!=expected_code or m["files"]!=inventory(root)
        or m["release_eligible"] is not False or m["origin"]!="agent_review" or m["human_reviewer_events"]!=0
        or m["snapshot_date"]!=SNAPSHOT_DATE or m["corpus_version"] is not None):raise ValueError("TT38 code/config/status binding mismatch")
    r=validate_extraction(root/"extraction_snapshot/manifest.json")
    if not r["technical_valid"] or not r["processing_success"]:raise ValueError("Stage3 snapshot invalid")
    if digest((root/"extraction_snapshot/manifest.json").read_bytes())!=cfg["extraction_manifest_sha256"]:raise ValueError("Wrong extraction binding")
    encoder_input.require_config(load(root/"encoder_config.json"),root/"tokenizer_assets")
    if load(root/"encoder_config.json")!=load(BASE_DIR/cfg["encoder_config_ref"]):raise ValueError("Encoder profile changed")
    exports,counts=calculate(root,cfg)
    for name,value in exports.items():
        if rows(root/(name+".jsonl"))!=value:raise ValueError("TT38 replay mismatch: "+name)
    if m["counts"]!=counts or load(root/"validation_report.json")!={"technical_valid":True,"counts":counts,"release_eligible":False,"legal_verification":False}:raise ValueError("TT38 report mismatch")
    if (root/"review.md").read_text(encoding="utf8")!=render(exports,counts):raise ValueError("Readable report mismatch")
    return {"technical_valid":True,"counts":counts,"release_eligible":False}


def build(run_dir,config=DEFAULT_CONFIG,extraction_manifest=None):
    cfg=load(config);root=staging_path(run_dir)
    require_config(cfg)
    if extraction_manifest is not None:
        chosen=Path(extraction_manifest).resolve();cfg={**cfg,"extraction_manifest_ref":chosen.relative_to(BASE_DIR).as_posix(),"extraction_manifest_sha256":digest(chosen.read_bytes())}
    source=resolve_ref(BASE_DIR,cfg["extraction_manifest_ref"])
    if digest(source.read_bytes())!=cfg["extraction_manifest_sha256"] or not validate_extraction(source)["processing_success"]:raise ValueError("Invalid extraction input")
    for ref,sha in [(cfg["raw_ref"],cfg["raw_sha256"]),(cfg["comparison_ref"],cfg["comparison_sha256"])]:
        if digest(resolve_ref(BASE_DIR,ref).read_bytes())!=sha:raise ValueError("Source changed")
    root.mkdir(parents=True);(root/"sources").mkdir()
    shutil.copytree(source.parent,root/"extraction_snapshot")
    shutil.copyfile(BASE_DIR/cfg["raw_ref"],root/"sources/selected.pdf");shutil.copyfile(BASE_DIR/cfg["comparison_ref"],root/"sources/comparison.pdf")
    shutil.copyfile(BASE_DIR/cfg["encoder_config_ref"],root/"encoder_config.json");shutil.copytree(BASE_DIR/cfg["tokenizer_assets_ref"],root/"tokenizer_assets")
    write_json(root/"config.json",cfg);exports,counts=calculate(root,cfg,tokenize=True)
    for name,value in exports.items():write_rows(root/(name+".jsonl"),value)
    (root/"review.md").write_text(render(exports,counts),encoding="utf8",newline="\n")
    write_json(root/"validation_report.json",{"technical_valid":True,"counts":counts,"release_eligible":False,"legal_verification":False})
    seal(root,{"manifest_type":VERSION,"built_at":now(),"snapshot_date":SNAPSHOT_DATE,"origin":"agent_review","human_reviewer_events":0,"release_eligible":False,
        "corpus_version":None,"counts":counts,"code_sha256":{p:digest((BASE_DIR/p).read_bytes()) for p in CODE}})
    return validate(root/"manifest.json")


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="action",required=True)
    ds=s.add_parser("dataset-draft");ds.add_argument("--config",type=Path,default=BASE_DIR/'config/circular_dataset.v1.json');ds.add_argument("--run-dir",type=Path,required=True)
    pr=s.add_parser("priority");pr.add_argument("--config",type=Path,default=BASE_DIR/'config/circular_priority.v1.2.json');pr.add_argument("--run-dir",type=Path,required=True)
    pv=s.add_parser("validate-priority");pv.add_argument("--manifest",type=Path,required=True)
    qp=s.add_parser("qcvn-pilot");qp.add_argument("--manifest",type=Path,required=True);qp.add_argument("--run-dir",type=Path,required=True)
    qv=s.add_parser("validate-qcvn-pilot");qv.add_argument("--manifest",type=Path,required=True)
    b=s.add_parser("build");b.add_argument("--run-dir",type=Path,required=True);b.add_argument("--config",type=Path,default=DEFAULT_CONFIG);b.add_argument("--extraction-manifest",type=Path)
    t=s.add_parser("tables");t.add_argument("--base-manifest",type=Path,required=True);t.add_argument("--run-dir",type=Path,required=True)
    tv=s.add_parser("validate-tables");tv.add_argument("--manifest",type=Path,required=True)
    c=s.add_parser("circular");c.add_argument("--extraction-manifest",type=Path,required=True);c.add_argument("--run-dir",type=Path,required=True);c.add_argument("--survey-manifest",type=Path)
    cv=s.add_parser("validate-circular");cv.add_argument("--manifest",type=Path,required=True)
    r=s.add_parser("extract-circular");r.add_argument("--source-manifest",type=Path,required=True);r.add_argument("--run-dir",type=Path,required=True)
    rv=s.add_parser("validate-reader");rv.add_argument("--manifest",type=Path,required=True)
    v=s.add_parser("validate");v.add_argument("--manifest",type=Path,required=True);a=p.parse_args(argv)
    try:
        if a.action=='dataset-draft':
            from src.circular_dataset import build as build_dataset
            print(json.dumps(build_dataset(a.config,a.run_dir),ensure_ascii=False));return 0
        if a.action in {"qcvn-pilot","validate-qcvn-pilot"}:
            from src.ingestion import qcvn_pilot
            result=qcvn_pilot.build(a.manifest,a.run_dir) if a.action=="qcvn-pilot" else qcvn_pilot.validate(a.manifest)
            print(json.dumps(result,ensure_ascii=False));return 0
        if a.action in {"priority","validate-priority"}:
            from src.ingestion import circular_priority
            result=circular_priority.build(a.config,a.run_dir) if a.action=="priority" else circular_priority.validate(a.manifest)
            print(json.dumps(result,ensure_ascii=False));return 0
        if a.action in {"extract-circular","validate-reader"}:
            from src.ingestion import circular_reader
            result=circular_reader.build(a.source_manifest,a.run_dir) if a.action=="extract-circular" else circular_reader.validate(a.manifest)
            print(json.dumps(result,ensure_ascii=False));return 0 if result["processing_success"] else 1
        if a.action in {"circular","validate-circular"}:
            from src.ingestion import circular_preview
            result=circular_preview.build(a.extraction_manifest,a.run_dir,a.survey_manifest) if a.action=="circular" else circular_preview.validate(a.manifest)
            print(json.dumps(result,ensure_ascii=False));return 0
        if a.action in {"tables","validate-tables"}:
            from src.ingestion import table_preview
            result=table_preview.build(a.base_manifest,a.run_dir) if a.action=="tables" else table_preview.validate(a.manifest)
            print(json.dumps(result,ensure_ascii=False));return 0
        result=build(a.run_dir,a.config,a.extraction_manifest) if a.action=="build" else validate(a.manifest);print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,TypeError,OSError,StopIteration) as e:print(f"ERROR: {type(e).__name__}: {e}",file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
