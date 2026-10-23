"""Export the seven-source pending registry and measured processing status.

This is an export of existing pipeline artifacts, not a new workflow database.
"""
import argparse
from collections import Counter
from pathlib import Path
import json
import sys
import csv
import io
from html import unescape
from urllib.parse import urlsplit

from src.assessment_evidence import now, seal, check_files, inventory
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_rows, write_json, csv_text, unique
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import inspect_bundle

SOURCES = {"36/2024/QH15":"SRC-001", "168/2024/NĐ-CP":"SRC-002", "35/2024/QH15":"SRC-003", "165/2024/NĐ-CP":"SRC-004",
           "38/2024/TT-BGTVT":"SRC-005", "51/2024/TT-BGTVT":"SRC-006", "35/2024/TT-BGTVT":"SRC-007"}
EVIDENCE = BASE_DIR / "data/source_evidence/circulars-2024"


def require_url(value):
    """Capture/export boundary: a URL is a scalar, never a serialized object."""
    if value is None:
        return None
    if type(value) is not str or len(value) > 8192 or any(c.isspace() or ord(c) < 32 for c in value) or any(c in value for c in '{}<>"\\'):
        raise ValueError("URL must be a plain absolute HTTP(S) URL")
    p = urlsplit(value)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("Invalid URL scheme/host/credentials")
    _ = p.port
    return value


def attachment_url(observed, evidence=EVIDENCE):
    value = observed["official_attachment_url"]
    if isinstance(value, dict):
        keys = {"value", "PSPath", "PSParentPath", "PSChildName", "PSDrive", "PSProvider", "ReadCount"}
        receipt = load(evidence/"gazette_pdf_capture.json")
        html = unescape((evidence/"tt38-congbao.html").read_text(encoding="utf8"))
        if (set(value) != keys or value["PSChildName"] != "gazette_cdn_url.txt"
            or observed["law_id"] != "38/2024/TT-BGTVT" or receipt["url"] != value
            or receipt["sha256"] != observed["sha256"] or receipt["size_bytes"] != observed["size_bytes"]
            or receipt["accessed_at"] != observed["new_capture_retrieved_at"] or receipt["valid_pdf"] is not True
            or receipt["http_status"] != 200 or type(value.get("value")) is not str or value["value"] not in html):
            raise ValueError("Legacy URL wrapper lacks matching capture/HTML/hash evidence")
        value = value["value"]
    return require_url(value)


def validate_csv_semantics(text, records):
    """Use the default csv field limit; reject giant serialized objects."""
    parsed = list(csv.DictReader(io.StringIO(text)))
    expected = list(csv.DictReader(io.StringIO(csv_text(records, list(records[0])))))
    if parsed != expected or len(parsed) != len(records):
        raise ValueError("CSV/JSONL semantic mismatch")
    for row, source in zip(parsed, records):
        for key in ("download_url", "official_page_url"):
            if require_url(row[key] or None) != source[key]:
                raise ValueError("CSV URL/null mismatch")


def calculate(registry, dataset, draft, preview, *additional):
    check_files(EVIDENCE/"manifest.json")
    docs = unique(rows(registry/"documents.pending.jsonl"),"law_id")
    if {k:d["source_id"] for k,d in docs.items()}!=SOURCES:raise ValueError("Seven-source inventory mapping mismatch")
    observed=unique(rows(EVIDENCE/"source_files.observed.jsonl"),"file_id")
    laws=load(dataset/"support/laws.json"); chunks=rows(dataset/"chunks.jsonl")
    preview_manifest=check_files(preview/"manifest.json")
    if preview_manifest["manifest_type"]!="tt38-pdf-preview.v1" or preview_manifest["release_eligible"] is not False:raise ValueError("Wrong preview")
    circulars={};table_preview=None
    for extra in additional:
        em=check_files(extra/"manifest.json")
        if em["release_eligible"] is not False:raise ValueError("Unexpected released preview")
        if em["manifest_type"]=="tt38-cell-row-preview.v1":
            if table_preview is not None:raise ValueError("Duplicate table preview")
            table_preview=extra
        elif em["manifest_type"]=="circular-text-preview.v1":
            law=rows(extra/"extraction_snapshot/source_snapshot/documents.pending.jsonl")[0]["law_id"]
            if law not in {"35/2024/TT-BGTVT","51/2024/TT-BGTVT"} or law in circulars:raise ValueError("Circular progress law mismatch")
            circulars[law]=em
        else:raise ValueError("Unsupported progress manifest")
    result=[]
    for f in rows(registry/"files.pending.jsonl"):
        m=f["measured"];p=resolve_ref(BASE_DIR,m["raw_file_ref"])
        if digest(p.read_bytes())!=m["sha256"]:raise ValueError("Export raw changed")
        o=observed.get(f["file_id"]);law=f["law_id"]
        refs=[{"ref":str((registry/"files.pending.jsonl").relative_to(BASE_DIR)).replace("\\","/"),"locator":{"file_id":f["file_id"]}}]
        if o:
            refs.append({"ref":"data/source_evidence/circulars-2024/source_files.observed.jsonl","locator":{"file_id":f["file_id"]}})
            refs.append({"ref":"data/source_evidence/circulars-2024/tt"+law.split("/")[0]+".html","locator":"metadata/attachment anchors"})
            if isinstance(o["official_attachment_url"], dict):
                refs.extend({"ref":"data/source_evidence/circulars-2024/"+name,"locator":locator} for name,locator in [
                    ("gazette_pdf_capture.json","url.value + sha256 + accessed_at"),
                    ("tt38-congbao.html","exact HTML-unescaped attachment href")])
        for ref in refs:ref["sha256"]=digest(resolve_ref(BASE_DIR,ref["ref"]).read_bytes())
        result.append({"source_id":SOURCES[law],"law_id":law,"file_id":f["file_id"],"source_set":f["source_set_id"],
            "file_role":f["file_role"],"part_order":f["part_order"],"local_ref":m["raw_file_ref"],
            "official_page_url":require_url(docs[law]["declared"]["source_url_candidate"]),"download_url":attachment_url(o) if o else None,
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
        if law in circulars:
            counts=circulars[law]["counts"]
            progress[-1].update(extraction="all_pages_observed_annex_decoding_partial" if law.startswith("51/") else "all_main_and_annex_pages_extracted",
                parsed_units=sum(counts["units"].values()),chunk_preview="available_pending_main_only",
                preview_chunks=counts["chunks"],preview_contexts=counts["contexts"],scope="agent_proposals_partial",
                unprocessed_annex_pages=counts["unprocessed_annex_pages"])
        if tt and table_preview:
            progress[-1].update(derived_table_previews=len(rows(table_preview/"tables.preview.jsonl")),
                table_quarantine=len(rows(table_preview/"tables.quarantine.jsonl")))
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
    out=["# Tiến độ bảy nguồn (pending, không phải corpus verified)","| Source | Law | Hồ sơ file | Extraction | Units | Preview riêng | Dataset/index chunks | Scope / applicability |",
         "|---|---|---:|---|---:|---|---:|---|"]
    for r in exports["source_progress"]:
        separate=str(r.get('preview_chunks',r.get('tt38_preview_chunks')) or 0)
        if r.get('derived_table_previews') is not None:separate+=' + '+str(r['derived_table_previews'])+' derived table'
        out.append(f"| {r['source_id']} | {r['law_id']} | {r['registered_files']} | {r['extraction']} | {r['parsed_units']} | {separate} | {r['dataset_chunks']} | {r['scope']} / pending |")
    out += ["", "Bốn văn bản trong dataset3077/index v1; ba Thông tư chưa được nhập. TT38 chỉ preview riêng.",
        "Source metadata: JSON null giữ đúng nghĩa; ô CSV rỗng là null, không phải đã verified. DOCX không có số trang render tin cậy.",
        "Crosswalk SRC-004 trong nhánh HTML NĐ168 là alias cũ theo đúng law/artifact; không đổi ID/chunk hoặc alias toàn cục.",
        "Circular progress chỉ cập nhật khi manifest tương ứng được bind. Annex TT35 và QCVN TT51 vẫn có phần chưa xử lý; không suy technical preview là scope/applicability pass."]
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
    if (m["manifest_type"]!="seven-source-export.v1.1" or m["code_sha256"]!=digest(Path(__file__).read_bytes()) or m["release_eligible"] is not False
        or m["snapshot_date"]!=SNAPSHOT_DATE or m["origin"]!="agent_review" or m["human_reviewer_events"]!=0 or m["files"]!=inventory(root)):
        raise ValueError("Export code/status/snapshot mismatch")
    exports=calculate_bound(root,load(root/"binding.json"))
    for name,value in exports.items():
        if rows(root/(name+".jsonl"))!=value:raise ValueError("Metadata export replay mismatch")
    fields=list(exports["source_metadata"][0])
    validate_csv_semantics((root/"source_metadata.csv").read_text(encoding="utf8"), exports["source_metadata"])
    if (root/"source_metadata.csv").read_text(encoding="utf8")!=csv_text(exports["source_metadata"],fields):raise ValueError("CSV mismatch")
    if (root/"source_progress.md").read_text(encoding="utf8")!=render(exports):raise ValueError("Progress mismatch")
    return {"technical_valid":True,"documents":len(exports["source_progress"]),"files":len(exports["source_metadata"]),"release_eligible":False}


def build(registry_manifest,dataset_manifest,draft_manifest,preview_manifest,run_dir,circular_manifests=(),table_manifest=None):
    target=staging_path(run_dir)
    if not inspect_bundle(registry_manifest)["technical_valid"]:raise ValueError("Invalid source registration")
    paths=[Path(p).resolve() for p in [registry_manifest,dataset_manifest,draft_manifest,preview_manifest,*circular_manifests,*([table_manifest] if table_manifest else [])]]
    binding={"inputs":[{"ref":p.relative_to(BASE_DIR).as_posix(),"sha256":digest(p.read_bytes())} for p in paths]}
    exports=calculate(*(p.parent for p in paths));target.mkdir(parents=True)
    validate_csv_semantics(csv_text(exports["source_metadata"],list(exports["source_metadata"][0])),exports["source_metadata"])
    write_json(target/"binding.json",binding)
    for name,value in exports.items():write_rows(target/(name+".jsonl"),value)
    (target/"source_metadata.csv").write_text(csv_text(exports["source_metadata"],list(exports["source_metadata"][0])),encoding="utf8",newline="\n")
    (target/"source_progress.md").write_text(render(exports),encoding="utf8",newline="\n")
    seal(target,{"manifest_type":"seven-source-export.v1.1","built_at":now(),"snapshot_date":SNAPSHOT_DATE,"origin":"agent_review",
        "code_sha256":digest(Path(__file__).read_bytes()),"human_reviewer_events":0,"release_eligible":False})
    return validate(target/"manifest.json")


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="action",required=True)
    b=sub.add_parser("export")
    for key in ["registry-manifest","dataset-manifest","draft-manifest","preview-manifest","run-dir"]:b.add_argument("--"+key,type=Path,required=True)
    b.add_argument("--circular-manifest",type=Path,action="append",default=[])
    b.add_argument("--table-manifest",type=Path)
    v=sub.add_parser("validate");v.add_argument("--manifest",type=Path,required=True);a=p.parse_args(argv)
    try:
        result=validate(a.manifest) if a.action=="validate" else build(a.registry_manifest,a.dataset_manifest,a.draft_manifest,a.preview_manifest,a.run_dir,a.circular_manifest,a.table_manifest)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print(f"ERROR: {e}",file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
