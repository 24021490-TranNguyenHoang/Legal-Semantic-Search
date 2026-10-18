"""Scoped review and DDD draft admission; no file verification, chunking or serving."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys

from src import assessment_contracts as decisions
from src.article22_pdf import validate as validate_mapping
from src.assessment_evidence import check_files, inventory, now, seal
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.ingestion.legal_tree import unit_id, span_id
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, digest, resolve_ref, connect_sqlite, require_contract
from src.source_registry import load_json, read_rows, write_rows, TABLES, schema_signature, expected_signature

VERSION = "article22-draft.v1"
PACK = "article22-scoped-review.v1"
SCHEMA = BASE_DIR / "schemas/data_model_v1/schema.sql"
ROOT_FILES = {"legal_document": "documents.prepared.jsonl", "source_file": "source_files.prepared.jsonl",
              "extraction": "extractions.pending.jsonl", "legal_unit": "legal_units.pending.jsonl",
              "source_span": "source_spans.pending.jsonl"}


def hashed(prefix, value):
    return prefix + digest(canonical(value).encode("utf8"))


def code_binding():
    return {"adapter": digest(Path(__file__).read_bytes()), "assessment_v11": digest(Path(decisions.__file__).read_bytes()),
            "ddd_schema": digest(SCHEMA.read_bytes())}


def checked_manifest(path, kind):
    path = Path(path).resolve()
    if path.name != "manifest.json":
        raise ValueError("Expected manifest.json")
    m = check_files(path)
    if (m["manifest_type"] != kind or m["files"] != inventory(path.parent)
            or m["release_eligible"] is not False or m["code_sha256"] != code_binding()):
        raise ValueError("Manifest type/code/hash/artifact/release mismatch")
    return m


def real_context(root):
    return {"dataset_kind": "legal_sources", "mapping_manifest_sha256": digest((root / "manifest.json").read_bytes()),
            "mapping_binding": load_json(root / "binding.json"),
            "tables": {k: read_rows(root / v) for k, v in ROOT_FILES.items()},
            "proposals": read_rows(root / "assessments.pending.jsonl"),
            "basis": read_rows(root / "effectiveness_basis.jsonl"),
            "captures": read_rows(root / "inputs/evidence/evidence.jsonl")}


def check_context(context, root):
    """Check the narrow set and all actual slices also for isolated adapter fixtures."""
    kind, tables = context["dataset_kind"], context["tables"]
    if kind not in {"legal_sources", "synthetic_fixture"}:
        raise ValueError("Unknown dataset kind")
    laws = {u["law_id"] for u in tables["legal_unit"]}
    if len(laws) != 1 or (kind == "legal_sources" and laws != {"36/2024/QH15"}) or (kind == "synthetic_fixture" and not all(l.startswith("FIXTURE/") for l in laws)):
        raise ValueError("Fixture/real law boundary mismatch")
    units = tables["legal_unit"]
    if len(tables["legal_document"]) != 1 or tables["legal_document"][0]["law_id"] not in laws:
        raise ValueError("Document/unit law mismatch")
    require_contract("legal_document", tables["legal_document"][0])
    if [u["unit_type"] for u in units] != ["document", "chapter", "article", "clause", "clause", "clause"]:
        raise ValueError("Only four selected units and two ancestors are permitted")
    if [u["designation"] for u in units[1:]] != ["II", "22", "1", "2", "3"]:
        raise ValueError("Wrong selected legal positions")
    if [u["parent_unit_id"] for u in units] != [None, units[0]["unit_id"], units[1]["unit_id"], *([units[2]["unit_id"]] * 3)]:
        raise ValueError("Wrong parent/context dependency")
    if len({u["unit_id"] for u in units}) != 6 or len({u["canonical_path"] for u in units}) != 6:
        raise ValueError("Duplicate identity/path")
    for u in units:
        if unit_id(u) != u["unit_id"] or digest(u["text_original"].encode("utf8")) != u["text_sha256"]:
            raise ValueError("Unit identity/content hash mismatch")
    ex = {e["extraction_id"]: e for e in tables["extraction"]}
    source_ids = {f["file_id"] for f in tables["source_file"]}
    if (len(source_ids) != 2 or {e["file_id"] for e in ex.values()} != source_ids
            or any(f["law_id"] not in laws for f in tables["source_file"])
            or sorted(f["part_order"] for f in tables["source_file"]) != [1, 2]
            or len({f["source_set_id"] for f in tables["source_file"]}) != 1):
        raise ValueError("Source/extraction relationship or part order mismatch")
    for e in ex.values():
        require_contract("extraction", e)
        text = resolve_ref(root, e["text_ref"]).read_text(encoding="utf8")
        if e["review_status"] != "pending" or len(text) != e["char_count"] or digest(text.encode("utf8")) != e["text_sha256"]:
            raise ValueError("Extraction hash/status mismatch; scoped review cannot verify file")
    if len(tables["source_file"]) != 2 or len(ex) != 2:
        raise ValueError("Both source parts are required")
    for f in tables["source_file"]:
        require_contract("source_file", f)
        data = resolve_ref(root, f["raw_file_ref"]).read_bytes()
        if len(data) != f["size_bytes"] or digest(data) != f["sha256"]:
            raise ValueError("Raw source hash/size mismatch")
    spans = tables["source_span"]
    if len({s["span_id"] for s in spans}) != len(spans):
        raise ValueError("Duplicate source span")
    for s in spans:
        if s["unit_id"] not in {u["unit_id"] for u in units} or span_id(s) != s["span_id"]:
            raise ValueError("Span ID/unit mismatch")
        e = ex[s["extraction_id"]]
        text = resolve_ref(root, e["text_ref"]).read_text(encoding="utf8")
        if not 0 <= s["char_start"] < s["char_end"] <= len(text) or digest(text[s["char_start"]:s["char_end"]].encode("utf8")) != s["quote_sha256"]:
            raise ValueError("Span offset/quote mismatch")
        locator = json.loads(s["locator_json"])
        if locator["format"] != "pdf" or not 1 <= locator["page_start"] <= locator["page_end"]:
            raise ValueError("Invalid PDF locator")
    for u in units:
        for field in ("title", "text_original"):
            own = sorted([s for s in spans if s["unit_id"] == u["unit_id"] and s["field_name"] == field], key=lambda s: s["span_order"])
            if [s["span_order"] for s in own] != list(range(len(own))):
                raise ValueError("Span order gap")
            text = "\n".join(resolve_ref(root, ex[s["extraction_id"]]["text_ref"]).read_text(encoding="utf8")[s["char_start"]:s["char_end"]] for s in own)
            if text != u[field]:
                raise ValueError("Field roundtrip mismatch")


def make_catalog(context, root):
    tables, rows = context["tables"], []
    files = {f["file_id"]: f for f in tables["source_file"]}
    ex = {e["extraction_id"]: e for e in tables["extraction"]}
    captures = context["captures"]
    for f in files.values():
        capture = next(c for c in captures if c["sha256"] == f["sha256"])
        rows.append({"finding_id": "file_" + f["sha256"], "kind": "source_capture", "evidence_id": capture["evidence_id"],
                     "file_id": f["file_id"], "artifact_ref": "mapping_snapshot/" + f["raw_file_ref"],
                     "artifact_sha256": f["sha256"], "url": f["download_url"], "accessed_at": capture["accessed_at"]})
    for s in tables["source_span"]:
        f = files[ex[s["extraction_id"]]["file_id"]]
        rows.append({"finding_id": s["span_id"], "kind": "source_span", "evidence_id": "file_" + f["sha256"],
                     "unit_id": s["unit_id"], "span": s, "accessed_at": f["retrieved_at"]})
    for b in context["basis"]:
        text = resolve_ref(root, b["text_ref"]).read_text(encoding="utf8")
        if text[b["char_start"]:b["char_end"]] != b["quote"] or digest(b["quote"].encode("utf8")) != b["quote_sha256"]:
            raise ValueError("Legal basis slice mismatch")
        rows.append({**b, "finding_id": hashed("basis_", b), "kind": "text_slice", "accessed_at":
                     next(c["accessed_at"] for c in captures if c["evidence_id"] == b["evidence_id"]),
                     "artifact_ref": "mapping_snapshot/" + b["text_ref"]})
    html = next(c for c in captures if c["kind"] == "metadata_html" and c["law_id"] == tables["legal_document"][0]["law_id"])
    rows.append({"finding_id": "metadata_" + html["sha256"], "kind": "source_capture", "evidence_id": html["evidence_id"],
                 "artifact_ref": "mapping_snapshot/inputs/evidence/" + html["artifact_ref"], "artifact_sha256": html["sha256"],
                 "url": html["final_url"], "accessed_at": html["accessed_at"]})
    return rows


def plan_data(context, catalog, binding):
    units, spans = context["tables"]["legal_unit"], context["tables"]["source_span"]
    proposals, slots = {}, []
    for i, u in enumerate(units[2:]):
        proposal = {"unit_id": u["unit_id"], "scope_candidate": "supporting" if i == 0 else "included",
                    "applicability_candidate": "verified_at_snapshot", "effective_from_candidate": "2025-01-01", "effective_to_candidate": None,
                    "origin": "machine_proposal_not_decision"}
        proposal["proposal_id"] = hashed("pr_", {"binding": binding, **proposal})
        proposals[u["unit_id"]] = proposal
        own = [s["span_id"] for s in spans if s["unit_id"] == u["unit_id"]]
        req = [f["finding_id"] for f in catalog if f["kind"] == "project_requirement"]
        basis = [f["finding_id"] for f in catalog if f["kind"] == "text_slice"]
        slots.append({"unit_id": u["unit_id"], "unit_sha256": digest(canonical(u).encode("utf8")), "citation": u["citation_path"],
                      "proposal": proposal, "own_span_ids": own,
                      "suggested_evidence": {"technical": own, "scope": own + req, "applicability": own + basis},
                      "dimensions": {d: {"status": None, "note": None, "evidence_refs": [], "supersedes": None,
                                          **({"effective_from": None, "effective_to": None, "history_note": None,
                                              "content_note": None, "historical_basis": None} if d == "applicability" else {})}
                                     for d in decisions.DIMENSIONS}})
    source_refs = [f["finding_id"] for f in catalog if f["kind"] == "source_capture" or f.get("role") == "page21_warning"]
    source_refs += [s["span_id"] for s in spans if s["unit_id"] in {u["unit_id"] for u in units[:2]}]
    form = {"form_version": VERSION, "dataset_kind": context["dataset_kind"], "binding": binding, "snapshot_date": SNAPSHOT_DATE,
            "reviewer_ref": None, "reviewed_at": None, "record_status": "unfilled_no_decision",
            "source_review": {"status": None, "note": None, "evidence_refs": [], "supersedes": None,
                              "review_scope": "source edition/necessary parts and selected spans only; not whole-file content verification"},
            "suggested_source_evidence": source_refs, "unit_reviews": slots}
    return form, proposals


def pack_binding(context, catalog):
    return {"adapter_version": VERSION, "snapshot_date": SNAPSHOT_DATE, "dataset_kind": context["dataset_kind"],
            "mapping_manifest_sha256": context["mapping_manifest_sha256"], "mapping_binding": context["mapping_binding"],
            "units_sha256": digest(canonical(context["tables"]["legal_unit"]).encode("utf8")),
            "spans_sha256": digest(canonical(context["tables"]["source_span"]).encode("utf8")),
            "evidence_catalog_sha256": digest(canonical(catalog).encode("utf8")), "code_sha256": code_binding()}


def render_pack(context, catalog, form):
    lines = ["# Hồ sơ review có phạm vi — chưa có quyết định", "", "Snapshot 2025-01-01. Mẫu còn null không phải approval.",
             "", "## Nguồn và giới hạn", "",
             "Bản gốc Công báo 977–978 (phần đầu) và 979–980 (phần tiếp), ngày 24-8-2024. Metadata công bố liên kết hai phần; phần tiếp ghi Tiếp theo Công báo số 977 + 978.",
             "Chỉ dùng title/đoạn dẫn Điều 22 và Khoản 1–3 ở trang PDF 19 / in 94. Document và Chương II chỉ là cha cấu trúc, không dùng làm target/context.",
             "Đã kiểm kỹ thuật 8 spans/832 code point trên trang 1, 10, 19; nguồn, offset và hash có trong mapping_snapshot. Chưa đối chiếu toàn bộ text phần đầu 21 trang hoặc phần tiếp 61 trang.",
             "Trang 21 có PDF_PAGE_NO_TEXT. Ảnh page21.png cho thấy thông tin xuất bản dạng nét; chưa OCR/resolve. Nó nằm ngoài 8 spans; không ảnh hưởng trực tiếp slice Điều 22. Người rà cần xác nhận phạm vi/ảnh hưởng, không xác nhận toàn file.",
             "DDD extraction.review_status ở mức file: giữ pending. Review có phạm vi nằm trong catalog và quyết định riêng; chỉ cho corpus draft. DQ-03 tiếp tục chặn phát hành/serving; không nới schema.",
             "Căn cứ ứng viên: Điều 88 khoản 1–2, Điều 89 trên phần tiếp trang 58–61 (in 59–62). Ngoại lệ khoản 2 Điều 88 nêu Điều 10 khoản 3. Các quote đầy đủ ở bảng dưới/capture. Chưa chứng minh tra cứu lịch sử toàn diện; bản hợp nhất 2026 không thay bản tại 2025-01-01.",
             "", "## Nội dung cần xem", ""]
    for u in context["tables"]["legal_unit"]:
        lines += ["### " + u["citation_path"], "", "unit_id: `" + u["unit_id"] + "`", "",
                  "Vai trò: " + ("chỉ cấu trúc" if u["unit_type"] in {"document", "chapter"} else "vùng được chọn"),
                  "```text", u["title"], u["text_original"], "```", ""]
        for s in context["tables"]["source_span"]:
            if s["unit_id"] == u["unit_id"]:
                lines.append(f"- `{s['span_id']}` {s['field_name']} extraction [{s['char_start']},{s['char_end']}) locator `{s['locator_json']}` quote SHA-256 `{s['quote_sha256']}`")
    lines += ["", "## Căn cứ và catalog", "", "Mỗi finding_id dưới đây có thể ghi vào evidence_refs khi người rà đã xem. Suggested refs trong JSON chỉ là gợi ý, không chứng minh đã xem.", ""]
    for f in catalog:
        lines += ["### " + f["finding_id"], "", "Loại: " + f["kind"], "", canonical(f)]
        if f.get("quote"):
            lines += ["", "```text", f["quote"], "```"]
    lines += ["", "## Cách điền", "", "Sao decision_template.json sang file ngoài run này trước khi điền. Không sửa bundle đã seal.",
              "1. Điền reviewer_ref và reviewed_at thực tế (UTC kết thúc Z). Không dùng thời điểm máy chạy thay thời điểm rà.",
              "2. source_review: accepted hoặc needs_fix; note ghi đúng bản/hai phần và phạm vi đã xem; evidence_refs chọn từ suggested_source_evidence sau khi thực tế xem.",
              "3. Mỗi unit có ba ô độc lập: technical accepted/needs_fix; scope supporting/included/excluded; applicability chọn enum DDD và ngày/căn cứ thực tế. Để null nếu chưa kết luận.",
              "4. Điền note, evidence_refs của từng chiều. Applicability khác pending_review cần historical_basis=promulgation_and_changes_reviewed, history_note và content_note nêu việc thực tế kiểm tra, giới hạn và lý do kết luận.",
              "5. Có thể khác proposal; note phải ghi lý do và chọn bằng chứng phù hợp. Compiler ghi override, không sửa policy để ép proposal.",
              "6. record_status=submitted chỉ khi gửi quyết định thật. Trạng thái này một mình không tạo quyết định; các ô null vẫn thiếu. Có thể gửi một chiều, các chiều còn lại pending.",
              "7. Khi thay một quyết định, dùng --history của run trước và điền supersedes đúng event ID của cùng unit/chiều (source có chuỗi riêng). Không chép quyết định DOCX.",
              "", "Không yêu cầu chữ ký số hoặc hệ thống phân quyền. Reviewer không bị yêu cầu xác nhận toàn văn từ vùng hẹp."]
    if context["dataset_kind"] == "synthetic_fixture":
        lines.insert(2, "SYNTHETIC FIXTURE — không phải dữ liệu pháp luật thật; mô tả vị trí chỉ mô phỏng adapter.")
    return "\n".join(lines) + "\n"


def render_form(form):
    lines = ["# Phiếu rà soát — CHƯA CÓ QUYẾT ĐỊNH", "", "Reviewer_ref: __________", "Thời điểm rà thực tế UTC (Z): __________", "",
             "Bản để đọc/ghi nháp; CLI nhập decision_template.json tương ứng. Không điền thay reviewer. Không sửa tệp trong bundle đã seal; sao ra chỗ làm việc trước.",
             "", "Nguồn: đúng hai phần PDF Công báo 977–978 / 979–980 theo binding trong JSON.",
             "Phạm vi đã xem (ghi thực tế): __________", "Kết quả nguồn accepted/needs_fix: __________", "Bằng chứng đã xem + lý do: __________", "",
             "| Đơn vị | Technical accepted/needs_fix | Scope (đề xuất) → quyết định | Applicability tại 2025-01-01 | Căn cứ/lý do |",
             "|---|---|---|---|---|"]
    for r in form["unit_reviews"]:
        lines.append(f"| {r['citation']} | chưa quyết định | {r['proposal']['scope_candidate']} → chưa quyết định | chưa quyết định | __________ |")
    lines += ["", "Mỗi chiều có thể kết luận riêng. Ghi evidence_refs đã thực tế xem, không coi suggested refs là đã xem.",
              "Applicability: ghi status, effective_from/to, history_note, content_note và historical_basis thực tế trong JSON; ngày truy cập không phải ngày hiệu lực.",
              "Có thể bác proposal với lý do/bằng chứng. Không cần xác nhận toàn bộ file. Extraction cấp file vẫn pending; review chỉ giới hạn các spans đã chọn.",
              "Document/Chương II chỉ phục vụ cấu trúc. Trang 21 ngoài vùng Điều 22, cần ghi nhận ảnh hưởng từ ảnh, không tự gọi trang trắng/đã OCR.",
              "Chỉ đổi record_status thành submitted sau khi điền quyết định thật. Ô để trống vẫn pending, không phải đồng ý mặc định."]
    return "\n".join(lines) + "\n"


def write_pack(context, artifact_root, run_dir, *, page21_image=None):
    """Shared writer; fixture contexts are allowed only with FIXTURE/ law identities."""
    target = staging_path(run_dir)
    artifact_root = Path(artifact_root).resolve()
    if artifact_root in target.parents:
        raise ValueError("Output must not be nested inside input")
    check_context(context, artifact_root)
    with staged_run(run_dir, PACK, artifact_root) as (run, report):
        shutil.copytree(artifact_root, run / "mapping_snapshot")
        write_json(run / "context.json", context)
        catalog = make_catalog(context, artifact_root)
        # A missing bound image is a concrete gap in mapping-004's warning evidence.
        if context["dataset_kind"] == "legal_sources":
            import pdfplumber
            main = next(f for f in context["tables"]["source_file"] if f["part_order"] == 1)
            with pdfplumber.open(resolve_ref(artifact_root, main["raw_file_ref"])) as pdf:
                pdf.pages[20].to_image(resolution=90).save(str(run / "page21.png"))
            visual = (run / "page21.png").read_bytes()
        else:
            visual = page21_image or b"synthetic visual fixture, not real source evidence"
            (run / "page21.png").write_bytes(visual)
        main = next(f for f in context["tables"]["source_file"] if f["part_order"] == 1)
        catalog.append({"finding_id": "visual_" + digest(visual), "kind": "visual_observation", "role": "page21_warning",
                        "evidence_id": "file_" + main["sha256"], "artifact_ref": "page21.png", "artifact_sha256": digest(visual),
                        "file_id": main["file_id"], "page": 21, "accessed_at": main["retrieved_at"],
                        "note": "Agent observation only: publishing colophon outside selected spans; no OCR or issue resolution."})
        requirement = BASE_DIR / "docs/requirements/BRD Vietnamese Traffic Legal Semantic Search_v1.0.docx.md"
        (run / "requirements").mkdir()
        shutil.copyfile(requirement, run / "requirements/brd.md")
        req_sha = digest(requirement.read_bytes())
        catalog.append({"finding_id": "req_" + req_sha, "evidence_id": "req_" + req_sha, "kind": "project_requirement",
                        "artifact_ref": "requirements/brd.md", "artifact_sha256": req_sha, "section": "BRD §3.1 / §3.3"})
        binding = pack_binding(context, catalog)
        form, proposals = plan_data(context, catalog, binding)
        write_rows(run / "evidence_catalog.jsonl", catalog)
        write_json(run / "binding.json", binding)
        write_json(run / "decision_template.json", form)
        (run / "decision_template.md").write_text(render_form(form), encoding="utf8", newline="\n")
        write_json(run / "proposals.json", proposals)
        (run / "review.md").write_text(render_pack(context, catalog, form), encoding="utf8", newline="\n")
        write_json(run / "decision_history.empty.json", {"source_events": [], "unit_events": []})
        seal(run, {"manifest_type": PACK, "built_at": now(), "snapshot_date": SNAPSHOT_DATE,
                           "dataset_kind": context["dataset_kind"], "code_sha256": code_binding(), "binding": binding,
                           "release_eligible": False})
        report.update(technical_valid=True, review_decision_count=0, release_eligible=False)
    return {"technical_valid": True, "review_decision_count": 0, "release_eligible": False}


def build_pack(mapping_manifest, run_dir):
    staging_path(run_dir)
    result = validate_mapping(mapping_manifest)
    if not result["technical_valid"]:
        raise ValueError("Invalid mapping bundle: " + canonical(result))
    root = Path(mapping_manifest).resolve().parent
    return write_pack(real_context(root), root, run_dir)


def read_pack(manifest_path):
    m = checked_manifest(manifest_path, PACK)
    root = Path(manifest_path).resolve().parent
    context = load_json(root / "context.json")
    if context["dataset_kind"] != m["dataset_kind"] or m["snapshot_date"] != SNAPSHOT_DATE:
        raise ValueError("Dataset/snapshot mismatch")
    if context["dataset_kind"] == "legal_sources":
        result = validate_mapping(root / "mapping_snapshot/manifest.json")
        if not result["technical_valid"] or context != real_context(root / "mapping_snapshot"):
            raise ValueError("Mapping snapshot/context replay mismatch")
    check_context(context, root / "mapping_snapshot")
    catalog = read_rows(root / "evidence_catalog.jsonl")
    # Base findings are deterministic from the source slices; append two bound findings only.
    base = make_catalog(context, root / "mapping_snapshot")
    if catalog[:-2] != base or catalog[-2].get("role") != "page21_warning" or catalog[-1]["kind"] != "project_requirement":
        raise ValueError("Evidence catalog replay mismatch")
    for f in catalog:
        if "artifact_sha256" in f and digest(resolve_ref(root, f["artifact_ref"]).read_bytes()) != f["artifact_sha256"]:
            raise ValueError("Evidence artifact hash mismatch")
    binding = pack_binding(context, catalog)
    form, proposals = plan_data(context, catalog, binding)
    if (binding != m["binding"] or load_json(root / "binding.json") != binding
            or load_json(root / "decision_template.json") != form or load_json(root / "proposals.json") != proposals
            or (root / "decision_template.md").read_text(encoding="utf8") != render_form(form)
            or (root / "review.md").read_text(encoding="utf8") != render_pack(context, catalog, form)):
        raise ValueError("Review pack binding/template/proposal/report mismatch")
    return root, context, catalog, binding, form, proposals


def source_history_errors(events, binding, catalog, required, earliest):
    latest, seen = None, set()
    allowed = {f["finding_id"]: f for f in catalog}
    for e in events:
        payload = {k: v for k, v in e.items() if k != "decision_id"}
        if set(e) != {"decision_id", "binding", "status", "review_scope", "evidence_refs", "reviewer_ref", "reviewed_at", "note", "supersedes", "record_origin"}:
            raise ValueError("Invalid source decision fields")
        if (hashed("srcdec_", payload) != e["decision_id"] or e["decision_id"] in seen
                or e["binding"] != binding or e["status"] not in {"accepted", "needs_fix"}
                or e["record_origin"] != "external_review_submission"
                or e["review_scope"] != "source edition/necessary parts and selected spans only; not whole-file content verification"):
            raise ValueError("Invalid source decision binding/status/scope/hash")
        if e["supersedes"] != (latest["decision_id"] if latest else None):
            raise ValueError("Source decision history chain mismatch")
        if not isinstance(e["reviewer_ref"], str) or not e["reviewer_ref"].strip() or not isinstance(e["note"], str) or not e["note"].strip():
            raise ValueError("Source reviewer/note required")
        refs = e["evidence_refs"]
        if (not isinstance(refs, list) or not refs or len(refs) != len(set(refs)) or not set(refs) <= set(allowed)
                or e["status"] == "accepted" and not set(required) <= set(refs)):
            raise ValueError("Source review needs source parts, metadata, structural spans and warning evidence")
        stamp = decisions.utc_time(e["reviewed_at"])
        dates = [earliest] + [decisions.utc_time(allowed[r]["accessed_at"]) for r in refs if allowed[r].get("accessed_at")]
        if latest:
            dates.append(decisions.utc_time(latest["reviewed_at"]))
        if stamp < max(dates):
            raise ValueError("Source review predates its bound evidence")
        seen.add(e["decision_id"])
        latest = e
    return latest


def compile_review(form, history, context, catalog, binding, template, proposals):
    if (set(form) != set(template) or form["binding"] != binding or form["snapshot_date"] != SNAPSHOT_DATE
            or form["dataset_kind"] != context["dataset_kind"] or form["form_version"] != VERSION
            or form["suggested_source_evidence"] != template["suggested_source_evidence"]
            or form["record_status"] not in {"unfilled_no_decision", "submitted"}):
        raise ValueError("Review form fields/binding/snapshot/dataset mismatch")
    if set(history) != {"source_events", "unit_events"} or any(not isinstance(v, list) for v in history.values()):
        raise ValueError("Invalid history container")
    source_events, events = list(history["source_events"]), list(history["unit_events"])
    by_ref = {f["finding_id"]: f for f in catalog}
    earliest = max(decisions.utc_time(e["created_at"]) for e in context["tables"]["extraction"])
    source = form["source_review"]
    if set(source) != set(template["source_review"]) or source["review_scope"] != template["source_review"]["review_scope"]:
        raise ValueError("Source review scope/fields changed")
    if source["status"] is not None:
        if form["record_status"] != "submitted":
            raise ValueError("Completed fields require an actual submitted review")
        e = {**source, "binding": binding, "reviewer_ref": form["reviewer_ref"], "reviewed_at": form["reviewed_at"],
             "record_origin": "external_review_submission"}
        e["decision_id"] = hashed("srcdec_", e)
        source_events.append(e)
    latest_source = source_history_errors(source_events, binding, catalog, template["suggested_source_evidence"], earliest)
    subjects = {u["unit_id"]: {"unit_sha256": digest(canonical(u).encode("utf8"))} for u in context["tables"]["legal_unit"][2:]}
    if len(form["unit_reviews"]) != len(template["unit_reviews"]):
        raise ValueError("Wrong unit review count")
    for row, expected in zip(form["unit_reviews"], template["unit_reviews"]):
        if set(row) != set(expected) or {k: v for k, v in row.items() if k != "dimensions"} != {k: v for k, v in expected.items() if k != "dimensions"}:
            raise ValueError("Unit/hash/proposal/coverage binding changed")
        if set(row["dimensions"]) != set(decisions.DIMENSIONS):
            raise ValueError("Wrong review dimensions")
        for dimension, slot in row["dimensions"].items():
            if set(slot) != set(expected["dimensions"][dimension]):
                raise ValueError("Unexpected decision fields")
            if slot["status"] is None:
                continue
            if form["record_status"] != "submitted":
                raise ValueError("Completed fields require an actual submitted review")
            if (not isinstance(form["reviewer_ref"], str) or not form["reviewer_ref"].strip()
                    or not isinstance(slot["note"], str) or not slot["note"].strip()):
                raise ValueError("Actual reviewer and decision note required")
            decisions.utc_time(form["reviewed_at"])
            refs = slot["evidence_refs"]
            negative = dimension == "technical" and slot["status"] == "needs_fix"
            if (not isinstance(refs, list) or not set(refs) <= set(by_ref)
                    or (not negative and not set(row["own_span_ids"]) <= set(refs))
                    or (negative and not set(row["own_span_ids"]) & set(refs))):
                raise ValueError("Decision missing exact own-field source spans")
            if dimension == "applicability" and slot["status"] != "pending_review":
                legal = {f["finding_id"] for f in catalog if f["kind"] == "text_slice"}
                if not legal or not legal <= set(refs):
                    raise ValueError("Applicability needs the stored general/exception/transitional basis")
                if any(not isinstance(slot[k], str) or not slot[k].strip() for k in ("history_note", "content_note")):
                    raise ValueError("Applicability needs actual history/content review notes")
            e = {"unit_id": row["unit_id"], "unit_sha256": row["unit_sha256"], "dimension": dimension,
                 "binding": binding, "snapshot_date": SNAPSHOT_DATE, "supersedes": slot["supersedes"],
                 "reviewer_ref": form["reviewer_ref"], "reviewed_at": form["reviewed_at"], "decision_note": slot["note"],
                 "record_origin": "external_review_submission", "finding_ids": refs,
                 "evidence_ids": sorted({by_ref[r]["evidence_id"] for r in refs}),
                 "proposal_id": row["proposal"]["proposal_id"], "proposal_relation": "accept", "override_reason": ""}
            if dimension == "scope":
                e["scope_status"] = slot["status"]
            elif dimension == "technical":
                e.update(technical_review_status=slot["status"], review_scope_note=slot["note"])
                if slot["status"] not in {"accepted", "needs_fix"}:
                    raise ValueError("Technical status must be accepted or needs_fix")
            else:
                e.update(applicability_status=slot["status"], effective_from=slot["effective_from"], effective_to=slot["effective_to"],
                         historical_basis=slot["historical_basis"], historical_review_note=slot["history_note"], content_comparison_note=slot["content_note"])
            if decisions.proposal_differences(e, row["proposal"]):
                e.update(proposal_relation="override", override_reason=slot["note"])
            if slot["status"] in {"pending_review", "needs_fix"}:
                e["proposal_relation"] = "defer" if dimension != "applicability" else e["proposal_relation"]
            e["decision_id"] = decisions.identity("dec_", e)
            events.append(e)
    errors, latest = decisions.decision_errors(events, subjects, binding, {f["evidence_id"] for f in catalog}, findings=catalog, proposals=proposals)
    if errors:
        raise ValueError("; ".join(errors))
    # Apply the same coverage/date conditions to historical events, not just new slots.
    for e in events:
        own = next(r["own_span_ids"] for r in template["unit_reviews"] if r["unit_id"] == e["unit_id"])
        covered = set(own) & set(e["finding_ids"]) if e["dimension"] == "technical" and e["technical_review_status"] == "needs_fix" else set(own) <= set(e["finding_ids"])
        if not covered or decisions.utc_time(e["reviewed_at"]) < earliest:
            raise ValueError("History loses scoped coverage or predates extraction")
        if e["dimension"] == "technical" and e["technical_review_status"] not in {"accepted", "needs_fix"}:
            raise ValueError("Invalid historical technical result")
        if e["dimension"] == "applicability" and e["applicability_status"] != "pending_review":
            if not {f["finding_id"] for f in catalog if f["kind"] == "text_slice"} <= set(e["finding_ids"]):
                raise ValueError("Historical applicability lacks stored basis")
    blockers = []
    if latest_source is None or latest_source["status"] != "accepted":
        blockers.append({"code": "SOURCE_REVIEW_MISSING" if latest_source is None else "SOURCE_NEEDS_FIX", "slot": "source_review"})
    for row in template["unit_reviews"]:
        for dimension in decisions.DIMENSIONS:
            e = latest.get((row["unit_id"], dimension))
            if e is None:
                blockers.append({"code": "DECISION_MISSING", "unit_id": row["unit_id"], "citation": row["citation"], "dimension": dimension})
            elif dimension == "technical" and e["technical_review_status"] != "accepted":
                blockers.append({"code": "TECHNICAL_NEEDS_FIX", "unit_id": row["unit_id"], "dimension": dimension})
            elif dimension == "applicability" and e["applicability_status"] == "pending_review":
                blockers.append({"code": "APPLICABILITY_DEFERRED", "unit_id": row["unit_id"], "dimension": dimension})
    return {"source_events": source_events, "unit_events": events}, latest, latest_source, blockers


def draft_rows(context, latest, source_decision, corpus_version, built_at):
    tables = {name: [] for name in TABLES}
    for table, rows in context["tables"].items():
        tables[table] = [dict(r) for r in rows]
    for table, field in (("source_file", "raw_file_ref"), ("extraction", "text_ref")):
        for row in tables[table]:
            row[field] = "review_pack/mapping_snapshot/" + row[field]
    assessed = context["tables"]["legal_unit"][2:]
    has_targets = any(latest[(u["unit_id"], "scope")]["scope_status"] == "included" and latest[(u["unit_id"], "applicability")]["applicability_status"] == "verified_at_snapshot" for u in assessed)
    tables["corpus"] = [{"corpus_version": corpus_version, "snapshot_date": SNAPSHOT_DATE, "schema_version": "1.0.0", "status": "draft",
                         "built_at": built_at, "processing_config_ref": "processing_config.json", "manifest_ref": "manifest.json",
                         "supported_topics_json": canonical(["Nhường đường tại nơi đường giao nhau"] if has_targets else []),
                         "exclusions_json": canonical(["Ngoài Điều 22 và Khoản 1–3", "Cha document/Chương II chỉ cấu trúc, không target/context",
                                                       "Các vùng extraction chưa rà", "Không chunk/index/serving; extraction file-level pending"]),
                         "coverage_report_ref": "coverage.json"}]
    tables["corpus_document"] = [{"corpus_version": corpus_version, "law_id": assessed[0]["law_id"], "usage_role": "retrieval" if has_targets else "supporting"}]
    for u in assessed:
        uid = u["unit_id"]
        s, a, t = (latest[(uid, d)] for d in decisions.DIMENSIONS)
        tables["unit_assessment"].append({"corpus_version": corpus_version, "unit_id": uid, "scope_status": s["scope_status"],
                                          "applicability_status": a["applicability_status"], "effective_from": a["effective_from"], "effective_to": a["effective_to"],
                                          "verification_ref": "decision_history.json#" + a["decision_id"], "verified_at": a["reviewed_at"],
                                          "reviewer_ref": a["reviewer_ref"], "decision_note": canonical({"scope": s["decision_id"], "applicability": a["decision_id"],
                                                                                                    "technical": t["decision_id"], "source": source_decision["decision_id"],
                                                                                                    "notes": [s["decision_note"], a["decision_note"], t["decision_note"]]})})
    # File-level review stays pending, even with all scoped decisions accepted.
    for row in tables["extraction"]:
        row["review_status"] = "pending"
    return tables


def review_uses(context, latest):
    rows = []
    article_id = context["tables"]["legal_unit"][2]["unit_id"]
    def effective(uid):
        a = latest.get((uid, "applicability"))
        t = latest.get((uid, "technical"))
        return bool(a and a["applicability_status"] == "verified_at_snapshot" and t and t["technical_review_status"] == "accepted")
    for i, u in enumerate(context["tables"]["legal_unit"]):
        uid = u["unit_id"]
        scope = latest.get((uid, "scope"), {}).get("scope_status")
        context_ok = effective(article_id) and latest.get((article_id, "scope"), {}).get("scope_status") in {"included", "supporting"}
        rows.append({"unit_id": uid, "structural_only": i < 2,
                     "scoped_target_review_complete": i >= 3 and scope == "included" and effective(uid) and context_ok,
                     "scoped_context_review_complete": i == 2 and scope in {"included", "supporting"} and effective(uid),
                     "span_ids": [s["span_id"] for s in context["tables"]["source_span"] if s["unit_id"] == uid] if i >= 2 else [],
                     "context_dependency_ids": [article_id] if i >= 3 else [], "serving_eligible": False,
                     "release_blocker": "DDD_DQ03_FILE_EXTRACTION_PENDING"})
    return rows


def admission_report(context, history, latest, blockers):
    return {"technical_valid": True, "errors": [], "admission_ready": not blockers, "draft_created": not blockers,
            "status": "draft" if not blockers else "blocked_missing_or_deferred_review", "dataset_kind": context["dataset_kind"],
            "snapshot_date": SNAPSHOT_DATE, "blockers": blockers, "source_decision_count": len(history["source_events"]),
            "unit_decision_count": len(history["unit_events"]), "release_eligible": False,
            "file_extraction_review_status": "pending", "review_is_scoped": True,
            "dimension_completion": [{"unit_id": u["unit_id"], **{d: ((u["unit_id"], d) in latest and not
                                        (d == "applicability" and latest[(u["unit_id"], d)]["applicability_status"] == "pending_review"))
                                        for d in decisions.DIMENSIONS}}
                                     for u in context["tables"]["legal_unit"][2:]]}


def version_check(version, dataset_kind, allow_fixture):
    if type(allow_fixture) is not bool:
        raise ValueError("allow_fixture must be boolean")
    prefix = "fixture" if dataset_kind == "synthetic_fixture" else "traffic"
    if not re.fullmatch(prefix + r"-20250101-v\d+\.\d+\.\d+", version):
        raise ValueError("Corpus version must match dataset kind and snapshot")
    if dataset_kind == "synthetic_fixture" and not allow_fixture:
        raise ValueError("Synthetic fixture requires --allow-fixture and a fixture- corpus version")


def coverage_data(context):
    return {"selected_unit_ids": [u["unit_id"] for u in context["tables"]["legal_unit"][2:]],
            "structural_dependency_ids": [u["unit_id"] for u in context["tables"]["legal_unit"][:2]],
            "reviewed_uses_ref": "scoped_review_uses.jsonl", "unreviewed_regions_permitted": False,
            "whole_file_review_claimed": False, "chunk_count": 0}


def admit(review_manifest, submission_path, run_dir, corpus_version, history_path=None, *, allow_fixture=False):
    target = staging_path(run_dir)
    source_root = Path(review_manifest).resolve().parent
    if source_root in target.parents:
        raise ValueError("Output must not be nested inside review bundle")
    root, context, catalog, binding, template, proposals = read_pack(review_manifest)
    version_check(corpus_version, context["dataset_kind"], allow_fixture)
    form = load_json(submission_path)
    history_in = load_json(history_path) if history_path else {"source_events": [], "unit_events": []}
    history, latest, source_decision, blockers = compile_review(form, history_in, context, catalog, binding, template, proposals)
    with staged_run(run_dir, VERSION, review_manifest) as (run, run_report):
        shutil.copytree(root, run / "review_pack")
        (run / "submission.input.json").write_bytes(Path(submission_path).read_bytes())
        write_json(run / "history.input.json", history_in)
        write_json(run / "decision_history.json", history)
        write_rows(run / "scoped_review_uses.jsonl", review_uses(context, latest))
        built_at = now()
        config = {"adapter_version": VERSION, "code_sha256": code_binding(), "binding": binding,
                  "requested_corpus_version": corpus_version, "built_at": built_at, "allow_fixture": allow_fixture,
                  "file_review_policy": "scoped_sidecar_keep_extraction_pending", "chunking": "not_run", "indexing": "not_run"}
        write_json(run / "processing_config.json", config)
        write_json(run / "coverage.json", coverage_data(context))
        report = admission_report(context, history, latest, blockers)
        if not blockers:
            tables = draft_rows(context, latest, source_decision, corpus_version, built_at)
            (run / "schema.sql").write_bytes(SCHEMA.read_bytes())
            with closing(connect_sqlite(run / "content.sqlite")) as db:
                db.executescript(SCHEMA.read_text(encoding="utf8"))
                with db:
                    for table in TABLES:
                        for row in tables[table]:
                            db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
            for table, rows in tables.items():
                write_rows(run / f"{table}.jsonl", rows)
        write_json(run / "validation_report.json", report)
        (run / "pending_work.md").write_text("# Kết quả nhập draft\n\n" + ("Draft được tạo; chưa verified extraction cấp file, chưa phát hành.\n" if not blockers else
                    "Chưa tạo corpus hoặc content.sqlite. Các quyết định còn thiếu/needs_fix:\n\n" + "\n".join("- " + canonical(b) for b in blockers)) + "\n", encoding="utf8", newline="\n")
        seal(run, {"manifest_type": VERSION, "built_at": built_at, "snapshot_date": SNAPSHOT_DATE,
                           "dataset_kind": context["dataset_kind"], "code_sha256": code_binding(), "binding": binding,
                           "review_manifest_sha256": digest(Path(review_manifest).read_bytes()), "draft_created": not blockers,
                           "corpus_version": corpus_version if not blockers else None,
                           "document_count": 0, "registered_document_count": 1 if not blockers else 0,
                           "unit_count": 6 if not blockers else 0, "assessed_unit_count": 4 if not blockers else 0,
                           "chunk_count": 0, "release_eligible": False})
        run_report.update(report)
    return report


def validate_draft(manifest_path):
    m = checked_manifest(manifest_path, VERSION)
    run = Path(manifest_path).resolve().parent
    root, context, catalog, binding, template, proposals = read_pack(run / "review_pack/manifest.json")
    if m["binding"] != binding or m["review_manifest_sha256"] != digest((root / "manifest.json").read_bytes()):
        raise ValueError("Draft/review binding mismatch")
    config = load_json(run / "processing_config.json")
    version_check(config["requested_corpus_version"], context["dataset_kind"], config["allow_fixture"])
    if (config["binding"] != binding or config["code_sha256"] != code_binding() or config["adapter_version"] != VERSION
            or config["file_review_policy"] != "scoped_sidecar_keep_extraction_pending" or config["chunking"] != "not_run" or config["indexing"] != "not_run"):
        raise ValueError("Draft policy/config mismatch")
    decisions.utc_time(config["built_at"])
    history, latest, src, blockers = compile_review(load_json(run / "submission.input.json"), load_json(run / "history.input.json"), context, catalog, binding, template, proposals)
    report = admission_report(context, history, latest, blockers)
    expected_meta = {"snapshot_date": SNAPSHOT_DATE, "dataset_kind": context["dataset_kind"], "built_at": config["built_at"],
                     "document_count": 0, "registered_document_count": 1 if not blockers else 0,
                     "unit_count": 6 if not blockers else 0, "assessed_unit_count": 4 if not blockers else 0, "chunk_count": 0}
    if any(m.get(k) != v or type(m.get(k)) is not type(v) for k, v in expected_meta.items()) or load_json(run / "coverage.json") != coverage_data(context):
        raise ValueError("Draft coverage/metadata mismatch")
    if (history != load_json(run / "decision_history.json") or read_rows(run / "scoped_review_uses.jsonl") != review_uses(context, latest)
            or report != load_json(run / "validation_report.json") or m["draft_created"] != (not blockers)
            or m["corpus_version"] != (config["requested_corpus_version"] if not blockers else None)):
        raise ValueError("Decision/report/draft state replay mismatch")
    if blockers:
        if (run / "content.sqlite").exists() or any((run / f"{t}.jsonl").exists() for t in TABLES):
            raise ValueError("Blocked admission must not contain canonical draft rows")
    else:
        tables = draft_rows(context, latest, src, config["requested_corpus_version"], config["built_at"])
        if (run / "schema.sql").read_bytes() != SCHEMA.read_bytes():
            raise ValueError("Official DDD schema changed")
        with closing(connect_sqlite(run / "content.sqlite", readonly=True)) as db:
            if schema_signature(db) != expected_signature(SCHEMA.read_text(encoding="utf8")) or list(db.execute("PRAGMA foreign_key_check")) or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("SQLite schema/FK/integrity mismatch")
            for table in TABLES:
                actual = [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
                if sorted(actual, key=canonical) != sorted(tables[table], key=canonical) or read_rows(run / f"{table}.jsonl") != tables[table]:
                    raise ValueError("SQLite/JSONL replay mismatch: " + table)
            if list(db.execute("SELECT * FROM serving_chunks")):
                raise ValueError("Draft cannot serve chunks")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scoped Article 22 review and DDD draft admission only")
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("review-pack")
    pack.add_argument("--mapping-manifest", type=Path, required=True)
    pack.add_argument("--run-dir", type=Path, required=True)
    add = commands.add_parser("admit")
    add.add_argument("--review-manifest", type=Path, required=True)
    add.add_argument("--decisions", type=Path, required=True)
    add.add_argument("--history", type=Path)
    add.add_argument("--corpus-version", required=True)
    add.add_argument("--allow-fixture", action="store_true")
    add.add_argument("--run-dir", type=Path, required=True)
    check = commands.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "review-pack":
            result = build_pack(args.mapping_manifest, args.run_dir)
        elif args.command == "admit":
            result = admit(args.review_manifest, args.decisions, args.run_dir, args.corpus_version, args.history, allow_fixture=args.allow_fixture)
        else:
            result = validate_draft(args.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("blockers") else 0
    except Exception as exc:
        print(json.dumps({"technical_valid": False, "error_type": "invalid_input_or_artifact", "errors": [str(exc)], "release_eligible": False}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
