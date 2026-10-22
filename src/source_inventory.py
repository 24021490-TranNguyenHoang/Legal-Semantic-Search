"""Export the seven-source pending registry and measured processing status.

This is an export of existing pipeline artifacts, not a new workflow database.
"""
import argparse
from collections import Counter
from pathlib import Path
import json
import sys

from src.assessment_evidence import now, seal, check_files, inventory
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_rows, write_json, csv_text, unique
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import inspect_bundle

SOURCES = {"36/2024/QH15":"SRC-001", "168/2024/NĐ-CP":"SRC-002", "35/2024/QH15":"SRC-003", "165/2024/NĐ-CP":"SRC-004",
           "38/2024/TT-BGTVT":"SRC-005", "51/2024/TT-BGTVT":"SRC-006", "35/2024/TT-BGTVT":"SRC-007"}
EVIDENCE = BASE_DIR / "data/source_evidence/circulars-2024"


def calculate(registry, dataset, draft, preview):
    check_files(EVIDENCE/"manifest.json")
    docs = unique(rows(registry/"documents.pending.jsonl"),"law_id")
    if {k:d["source_id"] for k,d in docs.items()}!=SOURCES:raise ValueError("Seven-source inventory mapping mismatch")
    observed=unique(rows(EVIDENCE/"source_files.observed.jsonl"),"file_id")
    laws=load(dataset/"support/laws.json"); chunks=rows(dataset/"chunks.jsonl")
    preview_manifest=check_files(preview/"manifest.json")
    if preview_manifest["manifest_type"]!="tt38-pdf-preview.v1" or preview_manifest["release_eligible"] is not False:raise ValueError("Wrong preview")
    result=[]
    for f in rows(registry/"files.pending.jsonl"):
        m=f["measured"];p=resolve_ref(BASE_DIR,m["raw_file_ref"])
        if digest(p.read_bytes())!=m["sha256"]:raise ValueError("Export raw changed")
        o=observed.get(f["file_id"]);law=f["law_id"]
        refs=[{"ref":str((registry/"files.pending.jsonl").relative_to(BASE_DIR)).replace("\\","/"),"locator":{"file_id":f["file_id"]}}]
        if o:
            refs.append({"ref":"data/source_evidence/circulars-2024/source_files.observed.jsonl","locator":{"file_id":f["file_id"]}})
            refs.append({"ref":"data/source_evidence/circulars-2024/tt"+law.split("/")[0]+".html","locator":"metadata/attachment anchors"})
        for ref in refs:ref["sha256"]=digest(resolve_ref(BASE_DIR,ref["ref"]).read_bytes())
        result.append({"source_id":SOURCES[law],"law_id":law,"file_id":f["file_id"],"source_set":f["source_set_id"],
            "file_role":f["file_role"],"part_order":f["part_order"],"local_ref":m["raw_file_ref"],
            "official_page_url":docs[law]["declared"]["source_url_candidate"],"download_url":o["official_attachment_url"] if o else None,
            "sha256":m["sha256"],"size_bytes":m["size_bytes"],"pages":o["page_count"] if o else None,
            "retrieved_at":o["new_capture_retrieved_at"] if o else None,
            "retrieved_at_basis":"actual_gazette_capture" if o and o["new_capture_retrieved_at"] else "historical_download_unknown",
            "status":"pending","origin":"agent_review","source_match":o["source_match"] if o else "legacy_provenance_pending",
            "evidence_ref":refs,"release_eligible":False})
    progress=[]
    for law,sid in SOURCES.items():
        d=laws.get(law);tt=law=="38/2024/TT-BGTVT"
        progress.append({"source_id":sid,"law_id":law,"registered_files":sum(r["law_id"]==law for r in result),"registration":"pending_registered",
            "extraction":"full_docx_in_existing_dataset" if d else "gazette8_pages_pending" if tt else "not_run",
            "parsed_units":len(d["units"]) if d else sum(preview_manifest["counts"]["units"].values()) if tt else 0,
            "chunk_preview":"available_pending" if d or tt else "not_run","tt38_preview_chunks":preview_manifest["counts"]["chunks"] if tt else None,
            "dataset_chunks":sum(c["law_id"]==law for c in chunks),"index_membership":"experimental_v1" if d else "not_added",
            "scope":"agent_proposals_only" if d or tt else "not_assessed","applicability":"pending_review","release_eligible":False})
    crosswalk=[]
    manifests=[(dataset/"chunks.jsonl",chunks)]
    dm=load(draft/"dataset_manifest.json")
    for component in dm["components"]:
        base=resolve_ref(draft,component["root_ref"])
        name="chunks.jsonl" if component["role"]=="unchanged_base" else "chunks.preview.jsonl"
        manifests.append((base/name,rows(base/name)))
    for path,records in manifests:
        groups=Counter((c["law_id"],c["source_id"]) for c in records)
        for (law,internal),count in sorted(groups.items()):
            crosswalk.append({"artifact_ref":path.relative_to(BASE_DIR).as_posix(),"artifact_sha256":digest(path.read_bytes()),
                "law_id":law,"internal_source_id":internal,"inventory_source_id":SOURCES[law],"chunk_count":count,
                "conflict":internal!=SOURCES[law],"mapping_rule":"law_id plus artifact hash; never a global alias of SRC-004","original_ids_and_payloads_modified":False})
    return {"source_metadata":result,"source_progress":progress,"source_id_crosswalk":crosswalk}


def render(exports):
    out=["# Tiến độ bảy nguồn (pending, không phải corpus verified)","| Source | Law | Hồ sơ file | Extraction | Units | Dataset/index chunks | Scope / applicability |",
         "|---|---|---:|---|---:|---:|---|"]
    for r in exports["source_progress"]:out.append(f"| {r['source_id']} | {r['law_id']} | {r['registered_files']} | {r['extraction']} | {r['parsed_units']} | {r['dataset_chunks']} | {r['scope']} / pending |")
    out += ["", "Bốn văn bản trong dataset3077/index v1; ba Thông tư chưa được nhập. TT38 chỉ preview riêng.",
        "Source metadata: JSON null giữ đúng nghĩa; ô CSV rỗng là null, không phải đã verified. DOCX không có số trang render tin cậy.",
        "Crosswalk SRC-004 trong nhánh HTML NĐ168 là alias cũ theo đúng law/artifact; không đổi ID/chunk hoặc alias toàn cục.",
        "TT35 có main/annex, chưa extraction/parse/chunk. TT51 có main/QCVN, chưa extraction pipeline; giữ100 trang text rỗng PDFium, NUL pdfplumber và nhu cầu đọc hình riêng trong durable evidence."]
    return "\n\n".join(out)+"\n"


def calculate_bound(root, binding):
    paths=[]
    for item in binding["inputs"]:
        path=resolve_ref(BASE_DIR,item["ref"])
        if digest(path.read_bytes())!=item["sha256"]:raise ValueError("Inventory input binding changed")
        paths.append(path.parent)
    return calculate(*paths)


def validate(manifest):
    path=Path(manifest);root=path.parent;m=check_files(path)
    if (m["manifest_type"]!="seven-source-export.v1" or m["code_sha256"]!=digest(Path(__file__).read_bytes()) or m["release_eligible"] is not False
        or m["snapshot_date"]!=SNAPSHOT_DATE or m["origin"]!="agent_review" or m["human_reviewer_events"]!=0 or m["files"]!=inventory(root)):
        raise ValueError("Export code/status/snapshot mismatch")
    exports=calculate_bound(root,load(root/"binding.json"))
    for name,value in exports.items():
        if rows(root/(name+".jsonl"))!=value:raise ValueError("Metadata export replay mismatch")
    fields=list(exports["source_metadata"][0])
    if (root/"source_metadata.csv").read_text(encoding="utf8")!=csv_text(exports["source_metadata"],fields):raise ValueError("CSV mismatch")
    if (root/"source_progress.md").read_text(encoding="utf8")!=render(exports):raise ValueError("Progress mismatch")
    return {"technical_valid":True,"documents":len(exports["source_progress"]),"files":len(exports["source_metadata"]),"release_eligible":False}


def build(registry_manifest,dataset_manifest,draft_manifest,preview_manifest,run_dir):
    target=staging_path(run_dir)
    if not inspect_bundle(registry_manifest)["technical_valid"]:raise ValueError("Invalid source registration")
    paths=[Path(p).resolve() for p in [registry_manifest,dataset_manifest,draft_manifest,preview_manifest]]
    binding={"inputs":[{"ref":p.relative_to(BASE_DIR).as_posix(),"sha256":digest(p.read_bytes())} for p in paths]}
    exports=calculate(*(p.parent for p in paths));target.mkdir(parents=True)
    write_json(target/"binding.json",binding)
    for name,value in exports.items():write_rows(target/(name+".jsonl"),value)
    (target/"source_metadata.csv").write_text(csv_text(exports["source_metadata"],list(exports["source_metadata"][0])),encoding="utf8",newline="\n")
    (target/"source_progress.md").write_text(render(exports),encoding="utf8",newline="\n")
    seal(target,{"manifest_type":"seven-source-export.v1","built_at":now(),"snapshot_date":SNAPSHOT_DATE,"origin":"agent_review",
        "code_sha256":digest(Path(__file__).read_bytes()),"human_reviewer_events":0,"release_eligible":False})
    return validate(target/"manifest.json")


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="action",required=True)
    b=sub.add_parser("export")
    for key in ["registry-manifest","dataset-manifest","draft-manifest","preview-manifest","run-dir"]:b.add_argument("--"+key,type=Path,required=True)
    v=sub.add_parser("validate");v.add_argument("--manifest",type=Path,required=True);a=p.parse_args(argv)
    try:
        result=validate(a.manifest) if a.action=="validate" else build(a.registry_manifest,a.dataset_manifest,a.draft_manifest,a.preview_manifest,a.run_dir)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print(f"ERROR: {e}",file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
