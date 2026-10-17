"""Bounded Stage 5A pilot. No inference, parser edits, official DB writes or release."""
import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
import re
import sys

from src import assessment_contracts as contract
from src.assessment_evidence import check_files, validate_evidence, seal, now
from src.config import BASE_DIR
from src.legal_parser import validate_run as validate_tree_bundle
from src.pipeline_cli import staged_run, write_json
from src.source_contracts import canonical, connect_sqlite, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows, schema_signature, expected_signature

SCHEMA = BASE_DIR / "schemas" / "assessment_v1"
DEFAULT_CONFIG = BASE_DIR / "config" / "assessment_pilot.v1.json"
DEFAULT_FINDINGS = BASE_DIR / "config" / "assessment_findings.v1.json"
EXPORTS = {
    "subjects": "subjects.pending.jsonl", "evidence": "evidence.jsonl", "findings": "evidence_findings.pending.jsonl",
    "rules": "date_rules.pending.jsonl", "regions": "regions.pending.jsonl", "impacts": "technical_impacts.pending.jsonl",
    "proposals": "machine_proposals.jsonl", "decisions": "review_decision_history.jsonl",
    "review_basis": "review_basis.jsonl", "proposal_conflicts": "proposal_conflicts.jsonl",
    "assessments": "assessments.pending.jsonl", "mapping": "ddd_mapping.pending.jsonl",
    "target_candidates": "target_candidates.jsonl", "context_candidates": "context_candidates.jsonl"}


def tool_identity():
    from importlib.metadata import version
    return {"policy": contract.VERSION, "pdfplumber_version": version("pdfplumber"), "code_sha256": {name: digest((BASE_DIR / "src" / name).read_bytes())
            for name in ("assessment_pipeline.py", "assessment_contracts.py", "assessment_evidence.py")}}


def binding_for(tree, review_manifest):
    metadata = load_json(tree / "manifest.json")
    return {"input_manifest_sha256": digest((tree / "manifest.json").read_bytes()),
            "parser_version": metadata["contract_version"], "parser_tool": metadata["tool"],
            "units_sha256": digest((tree / "legal_units.pending.jsonl").read_bytes()),
            "spans_sha256": digest((tree / "source_spans.pending.jsonl").read_bytes()),
            "extraction_manifest_sha256": metadata["extraction_manifest_sha256"],
            "review_pack_manifest_sha256": digest(Path(review_manifest).read_bytes())}


def select_subjects(config, units):
    if config["policy"] != contract.VERSION or config["snapshot_date"] != contract.SNAPSHOT:
        raise ValueError("Assessment policy/snapshot mismatch")
    if config["dataset_kind"] not in {"legal_sources", "synthetic_fixture"}:
        raise ValueError("Unknown dataset kind")
    selected, seen, groups = [], set(), set()
    for group in config["groups"]:
        if group["group_id"] in groups or not group["scope_reason"].strip():
            raise ValueError("Duplicate group or missing scope reason")
        groups.add(group["group_id"])
        if group["scope_candidate"] not in contract.SCOPES | {None}:
            raise ValueError("Invalid scope candidate")
        for uid in group["unit_ids"]:
            if uid in seen or uid not in units:
                raise ValueError("Unknown/duplicate pilot unit_id")
            seen.add(uid)
            selected.append({"unit_id": uid, "group_id": group["group_id"], "unit": units[uid]})
    if not selected or not 0 < len(selected) <= config["max_units"] <= 60:
        raise ValueError("Stage 5A requires a bounded nonempty pilot, at most 60 units")
    return selected


def compute_findings(requests, evidence, root, subjects):
    findings, rules, keys = [], [], set()
    by_id = {e["evidence_id"]: e for e in evidence}
    for req in requests:
        if req["key"] in keys:
            raise ValueError("Duplicate evidence finding key")
        keys.add(req["key"])
        matches = [e for e in evidence if e["law_id"] == req["law_id"] and e["url"].endswith(req["pdf_suffix"])]
        if len(matches) != 1:
            raise ValueError("Finding must bind exactly one captured PDF")
        item = matches[0]
        page = next((p for p in item["pages"] if p["page"] == req["page"]), None)
        if page is None:
            raise ValueError("Unknown evidence page")
        record = {"key": req["key"], "law_id": req["law_id"], "evidence_id": item["evidence_id"],
                  "evidence_sha256": item["sha256"], "url": item["url"], "accessed_at": item["accessed_at"],
                  "page": req["page"], "legal_locator": req["legal_locator"], "review_status": "pending",
                  "observation_origin": "machine", "historical_status": "pending_review", "note": req["note"]}
        if "quote" in req:
            text = resolve_ref(root, page["text_ref"]).read_text(encoding="utf8")
            if text.count(req["quote"]) != 1:
                raise ValueError("Evidence quote missing or nonunique: " + req["key"])
            start = text.index(req["quote"])
            record.update(kind="text_slice", text_ref=page["text_ref"], text_sha256=page["text_sha256"],
                          char_start=start, char_end=start + len(req["quote"]), quote=req["quote"],
                          quote_sha256=digest(req["quote"].encode("utf8")))
        else:
            if page["text_status"] != "needs_ocr" or not req["visual_observation"].strip():
                raise ValueError("Visual observation requires an identified image-only page")
            record.update(kind="visual_observation", visual_observation=req["visual_observation"],
                          character_offsets=None, transcription_status="not_a_source_text_transcription")
        record["finding_id"] = contract.identity("find_", record)
        findings.append(record)
        if "date_rule" in req:
            rule = req["date_rule"]
            if not rule["unit_ids"] or not set(rule["unit_ids"]) <= {s["unit_id"] for s in subjects}:
                raise ValueError("Date rule target is outside pilot")
            contract.legal_date(rule["effective_from"])
            if "quote" in req:
                compact = re.sub(r"\s+", " ", req["quote"])
                day, month, year = rule["effective_from"].split("-")[2], rule["effective_from"].split("-")[1], rule["effective_from"].split("-")[0]
                if f"ngày {day} tháng {month} năm {year}" not in compact:
                    raise ValueError("Candidate effective date not present in evidence text")
            bound = {**rule, "finding_id": record["finding_id"], "evidence_ids": [item["evidence_id"]],
                     "review_status": "pending", "rule_kind": "machine_candidate_not_legal_verification"}
            bound["rule_id"] = contract.identity("rule_", bound)
            rules.append(bound)
    # Candidate rules can disagree. Record that in proposals; a reviewer may resolve it.
    return findings, rules


def compute_impacts(tree, pack, subjects, spans, context_links=()):
    issues = read_rows(pack / "issues.jsonl")
    selected = {s["unit_id"] for s in subjects}
    units = {s["unit_id"]: s["unit"] for s in subjects}
    records = read_rows(tree / "extraction_snapshot" / "extractions.pending.jsonl")
    texts = {r["extraction"]["extraction_id"]: resolve_ref(tree / "extraction_snapshot", r["extraction"]["text_ref"]).read_text(encoding="utf8") for r in records}
    regions, impacts, region_keys = [], [], {}

    def region(issue, parent, note=None):
        key = (issue["extraction_id"], issue["char_start"], issue["char_end"], canonical(issue["locator"]))
        if key not in region_keys:
            a, b = issue["char_start"], issue["char_end"]
            quote = texts[key[0]][a:b]
            if "source_quote" in issue and quote != issue["source_quote"]:
                raise ValueError("Review pack quote mismatches immutable extraction")
            value = {"law_id": issue["law_id"], "extraction_id": key[0], "locator": issue["locator"],
                     "char_start": a, "char_end": b, "source_quote": quote, "quote_sha256": digest(quote.encode("utf8")),
                     "context_unit_id": parent, "context_is_legal_parent": parent is not None,
                     "issue_ids": [], "reason": note or issue.get("reason_or_quarantine", issue.get("reason", "needs_review")),
                     "review_status": "pending"}
            value["region_id"] = contract.identity("reg_", {"extraction_id": key[0], "locator": issue["locator"], "start": a, "end": b})
            regions.append(value)
            region_keys[key] = value
        if issue.get("issue_id"):
            region_keys[key]["issue_ids"].append(issue["issue_id"])
        return region_keys[key]

    def impact(uid, reg, kind, reason, roles):
        row = {"unit_id": uid, "region_id": reg["region_id"], "impact_kind": kind,
               "reason": reason, "blocks_roles": roles, "resolution_status": "pending",
               "propagation": "explicit_pilot_link_not_automatic_parent_child_inheritance"}
        row["impact_id"] = contract.identity("impact_", row)
        if row not in impacts:
            impacts.append(row)

    for issue in issues:
        parent = issue.get("parent_unit_id")
        reg = region(issue, parent)
        if parent not in selected:
            kind = "non_body_warning_no_legal_parent" if parent is None else "outside_pilot_context_not_assessed"
            impact(None, reg, kind, issue["reason_or_quarantine"], [])
            continue
        retained = [s["unit_id"] for s in spans if s["unit_id"] in selected
                    and s["extraction_id"] == issue["extraction_id"]
                    and s["char_start"] < issue["char_end"] and s["char_end"] > issue["char_start"]]
        if retained:
            for uid in sorted(set(retained)):
                impact(uid, reg, "unit_present_with_structure_warning", "Ký hiệu nhảy vẫn có unit/span; chưa sửa hoặc coi đã xác minh.", ["target", "context"])
            impact(parent, reg, "child_designation_review", "Cha có con đang cảnh báo ký hiệu; không tự kết luận thiếu con.", ["target", "context"])
        else:
            kind = "unparsed_table_content_dependency" if issue["code"] == "TABLE_STRUCTURE_NOT_PARSED" else "parent_missing_some_children"
            impact(parent, reg, kind, issue["impact"], ["target", "context"])
            impact(None, reg, "extraction_region_without_unit", issue["reason_or_quarantine"], ["target", "context"])
    # Review pack explicitly notes this quarantined continuation has no parser issue ID.
    for row in read_rows(tree / "coverage.jsonl"):
        if row["locator"].get("xpath") == "/w:document/w:body/w:p[1059]" and row["extraction_id"] == next((r["extraction"]["extraction_id"] for r in records if r["law_id"] == "168/2024/NĐ-CP"), None):
            parents = [s["unit_id"] for s in subjects if s["unit"]["law_id"] == "168/2024/NĐ-CP" and s["unit"]["unit_type"] == "clause" and s["unit"]["canonical_path"].endswith("/article:40/clause:3")]
            if not parents:
                continue
            parent = parents[0]
            reg = region({**row, "law_id": "168/2024/NĐ-CP"}, parent, "Continuation quarantined after duplicate symbols; no separate Stage 4 issue ID.")
            impact(parent, reg, "parent_missing_some_children", "p[1059] chưa thành unit, không chỉ rà hai ký hiệu đ).", ["target", "context"])
            impact(None, reg, "extraction_region_without_unit", reg["reason"], ["target", "context"])
    # Only explicitly enumerated, justified pilot links; never propagate to children.
    for link in context_links:
        uid, parent = link["unit_id"], link["context_unit_id"]
        if uid not in selected or parent not in selected or units[uid]["parent_unit_id"] != parent:
            raise ValueError("Context review link has wrong pilot unit/parent")
        if link["own_content_impact"] != "not_observed" or not link["reason"].strip():
            raise ValueError("Context review link needs a separate own-content assessment and reason")
        matched = [r for r in regions if r["context_unit_id"] == parent and r["locator"].get("xpath") in link["region_xpaths"]]
        if {r["locator"].get("xpath") for r in matched} != set(link["region_xpaths"]) or not matched:
            raise ValueError("Context review link references an unknown/incorrect extraction region")
        for reg in matched:
            impact(uid, reg, "context_dependency_needs_review", link["reason"], ["context"])
    return regions, impacts


def review_basis(config, subjects, spans, findings):
    """References to existing checked artifacts, not new legal evidence or units."""
    result = list(findings)
    selected = {s["unit_id"] for s in subjects}
    selected |= {s["unit"]["parent_unit_id"] for s in subjects}
    for ref in config.get("scope_basis", []):
        key = contract.identity("req_", ref)
        result.append({"finding_id": key, "evidence_id": key, "kind": "project_requirement",
                       "artifact_ref": "requirements_snapshot/" + ref["path"], "sha256": ref["sha256"], "locator": ref["locator"]})
    for span in spans:
        if span["unit_id"] in selected:
            result.append({"finding_id": span["span_id"], "evidence_id": "extraction:" + span["extraction_id"],
                           "kind": "source_span", **span,
                           "artifact_ref": "input_snapshot/extraction_snapshot/extractions/" + span["extraction_id"] + "/normalized.txt"})
    return result


def compute(tree, pack, evidence_root, config, requests, submissions):
    if config["dataset_kind"] != load_json(tree / "manifest.json")["dataset_kind"]:
        raise ValueError("Synthetic fixtures must remain separate from legal sources")
    units = {u["unit_id"]: u for u in read_rows(tree / "legal_units.pending.jsonl")}
    subjects = select_subjects(config, units)
    spans = read_rows(tree / "source_spans.pending.jsonl")
    binding = binding_for(tree, pack / "manifest.json")
    binding.update(evidence_manifest_sha256=digest((evidence_root / "manifest.json").read_bytes()),
                   assessment_config_sha256=digest(canonical(config).encode("utf8")),
                   finding_requests_sha256=digest(canonical(requests).encode("utf8")),
                   assessment_policy=contract.VERSION)
    pack_meta = check_files(pack / "manifest.json")
    if pack_meta["input_manifest_sha256"] != binding["input_manifest_sha256"]:
        raise ValueError("Review pack belongs to a different Stage 4 bundle")
    evidence = validate_evidence(evidence_root / "manifest.json")
    findings, rules = compute_findings(requests, evidence, evidence_root, subjects)
    regions, impacts = compute_impacts(tree, pack, subjects, spans, config.get("context_review_links", []))
    decisions = submissions["events"]
    basis = review_basis(config, subjects, spans, findings)
    groups = {g["group_id"]: g for g in config["groups"]}
    proposals, assessments, mappings = [], [], []
    for subject in subjects:
        uid, group = subject["unit_id"], groups[subject["group_id"]]
        candidates = [r for r in rules if uid in r["unit_ids"]]
        top = [r for r in candidates if r["priority"] == max(x["priority"] for x in candidates)] if candidates else []
        conflicting = len({(r["effective_from"], r.get("effective_to")) for r in top}) > 1
        rule = top[0] if top and not conflicting else None
        proposal = {"binding": binding, "unit_id": uid, "unit_sha256": digest(canonical(units[uid]).encode("utf8")),
                    "snapshot_date": contract.SNAPSHOT, "origin": "machine", "review_status": "pending",
                    "scope_candidate": group["scope_candidate"], "scope_reason": group["scope_reason"],
                    "scope_basis": config.get("scope_basis", []),
                    "applicability_candidate": "not_yet_effective" if rule and rule["effective_from"] > contract.SNAPSHOT else "pending_review",
                    "effective_from_candidate": rule["effective_from"] if rule else None,
                    "effective_to_candidate": rule.get("effective_to") if rule else None,
                    "date_rule_id": rule["rule_id"] if rule else None,
                    "date_rule_conflicts": [r["rule_id"] for r in top] if conflicting else [],
                    "finding_ids": [f["finding_id"] for f in findings if f["law_id"] == units[uid]["law_id"]],
                    "pending_work": ["Review exact original edition and amendments at snapshot", "Compare DOCX content and official evidence", "Actual scope/applicability decision", "Resolve selected technical/context impacts"]}
        proposal["proposal_id"] = contract.identity("pr_", proposal)
        proposals.append(proposal)
    subject_hashes = {s["unit_id"]: {"unit_sha256": digest(canonical(s["unit"]).encode("utf8"))} for s in subjects}
    by_proposal = {p["unit_id"]: p for p in proposals}
    errors, latest = contract.decision_errors(decisions, subject_hashes, binding,
        {f["evidence_id"] for f in basis}, findings=basis, proposals=by_proposal)
    if errors:
        raise ValueError(canonical(errors))
    conflicts = [{"decision_id": e["decision_id"], "unit_id": e["unit_id"], "dimension": e["dimension"],
                  "proposal_id": e["proposal_id"], "differences": contract.proposal_differences(e, by_proposal[e["unit_id"]]),
                  "disposition": "reviewer_override", "reason": e["override_reason"]}
                 for e in decisions if e["proposal_relation"] == "override"]
    for subject in subjects:
        uid, group = subject["unit_id"], groups[subject["group_id"]]
        accepted = {d: latest[(uid, d)] for d in contract.DIMENSIONS if (uid, d) in latest}
        row = contract.assessment(units[uid], group, binding, impacts, by_proposal[uid], accepted)
        assessments.append(row)
        mappings.append(contract.ddd_mapping(row, accepted))
    return {"subjects": subjects, "evidence": evidence, "findings": findings, "rules": rules,
            "regions": regions, "impacts": impacts, "proposals": proposals, "decisions": decisions,
            "assessments": assessments, "mapping": mappings, "review_basis": basis, "proposal_conflicts": conflicts,
            "target_candidates": [], "context_candidates": []}, binding


def database_rows(output, binding):
    bid = contract.identity("bind_", binding)
    def rows(key, id_key, **links):
        return [{id_key: r[id_key], **{k: (bid if v == "$binding" else r[v]) for k, v in links.items()},
                 "payload_json": canonical(r)} for r in output[key]]
    return {"assessment_binding": [{"binding_id": bid, "payload_json": canonical(binding)}],
            "pending_subject": rows("subjects", "unit_id", binding_id="$binding"),
            "pending_evidence": rows("evidence", "evidence_id"),
            "pending_review_basis": rows("review_basis", "finding_id"),
            "pending_region": rows("regions", "region_id"),
            "pending_impact": rows("impacts", "impact_id", unit_id="unit_id", region_id="region_id"),
            "pending_proposal": rows("proposals", "proposal_id", unit_id="unit_id"),
            "pending_decision_event": rows("decisions", "decision_id", unit_id="unit_id", dimension="dimension", supersedes="supersedes"),
            "pending_assessment": [{"assessment_id": a["assessment_id"], "unit_id": a["unit_id"], "proposal_id": a["proposal_id"],
                **{d + "_decision_id": a["decision_ids"][d] for d in contract.DIMENSIONS}, "payload_json": canonical(a)} for a in output["assessments"]]}


def summary_for(output):
    return {"technical_valid": True, "legal_verification": "not_performed", "unit_count": len(output["subjects"]),
            "decision_count": len(output["decisions"]), "evidence_count": len(output["evidence"]),
            "region_count": len(output["regions"]), "impact_count": len(output["impacts"]),
            "scope_decided_count": sum(a["scope_status"] is not None for a in output["assessments"]),
            "applicability_decided_count": sum(a["dimension_complete"]["applicability"] for a in output["assessments"]),
            "technical_decided_count": sum(a["dimension_complete"]["technical"] for a in output["assessments"]),
            "proposal_override_count": len(output["proposal_conflicts"]),
            "target_candidate_count": 0, "context_candidate_count": 0, "release_eligible": False}


def write_readable(run, output):
    units = {s["unit_id"]: s["unit"] for s in output["subjects"]}
    proposals = {r["unit_id"]: r for r in output["proposals"]}
    lines = ["# Pilot Stage 5A — tất cả vẫn pending", "", "Snapshot 2025-01-01; đề xuất máy không phải quyết định. Không kích hoạt dữ liệu.", "",
             "| Nhóm | Đơn vị | Kỹ thuật | Scope máy | Hiệu lực máy / ngày ứng viên | Quyết định |", "|---|---|---|---|---|---|"]
    with (run / "pilot.csv").open("x", encoding="utf8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "unit_id", "citation", "own_title", "own_text", "technical", "machine_scope", "machine_applicability", "candidate_effective_from", "actual_decision", "target_eligible", "context_eligible"])
        for row in output["assessments"]:
            unit, prop = units[row["unit_id"]], proposals[row["unit_id"]]
            lines.append(f"| {row['pilot_group']} | {unit['citation_path']} | {row['technical']['status']} | {prop['scope_candidate'] or 'pending'} | {prop['applicability_candidate']} / {prop['effective_from_candidate'] or 'pending'} | {canonical(row['decision_ids'])} |")
            writer.writerow([row["pilot_group"], row["unit_id"], unit["citation_path"], unit["title"], unit["text_original"], row["technical"]["status"], prop["scope_candidate"], prop["applicability_candidate"], prop["effective_from_candidate"], canonical(row["decision_ids"]), False, False])
    lines += ["", "## Nội dung riêng và spans", "", "Spans lấy từ input_snapshot/source_spans.pending.jsonl; normalized.txt bất biến nằm dưới input_snapshot/extraction_snapshot/."]
    spans = read_rows(run / "input_snapshot" / "source_spans.pending.jsonl")
    for uid, unit in units.items():
        lines += ["", "### " + unit["citation_path"], "", "`" + uid + "`", "", unit["title"], "", unit["text_original"], "",
                  "| Field | Span | Locator | [start,end) |", "|---|---|---|---|"]
        for span in (s for s in spans if s["unit_id"] == uid):
            locator = json.loads(span["locator_json"])
            lines.append(f"| {span['field_name']} | {span['span_id']} | {locator.get('part')} {locator.get('xpath')} | [{span['char_start']},{span['char_end']}) |")
    (run / "pilot.md").write_text("\n".join(lines) + "\n", encoding="utf8", newline="\n")
    findings = ["# Bằng chứng và quan sát của máy — chờ rà soát", "", "Ngày truy cập là sự kiện mới, không thay retrieved_at lịch sử. Chưa kiểm chữ ký số hoặc chứng minh đầy đủ lịch sử sửa đổi."]
    for f in output["findings"]:
        findings += ["", "## " + f["key"], "", f"{f['law_id']} — {f['legal_locator']} — PDF trang {f['page']}", "", f"URL: {f['url']}", "", f"SHA-256 PDF: `{f['evidence_sha256']}`; truy cập `{f['accessed_at']}`.", "", f.get("quote", f.get("visual_observation", "")), "", f["note"], "", "Trạng thái: pending; observation_origin=machine."]
    (run / "evidence_review.md").write_text("\n".join(findings) + "\n", encoding="utf8", newline="\n")
    # Render only cited image-only evidence pages. This is not OCR or extraction repair.
    images = run / "evidence_pages"
    visual = [f for f in output["findings"] if f["kind"] == "visual_observation"]
    if visual:
        import pdfplumber
        images.mkdir()
        by_id = {e["evidence_id"]: e for e in output["evidence"]}
        for f in visual:
            source = resolve_ref(run / "evidence_snapshot", by_id[f["evidence_id"]]["artifact_ref"])
            with pdfplumber.open(source) as pdf:
                pdf.pages[f["page"] - 1].to_image(resolution=110).save(images / (f["key"] + ".png"))
    review = ["# Ảnh hưởng kỹ thuật — liên kết riêng từng vùng", "", "Không suy trạng thái toàn bộ cha/con. Các link dưới đây đều là đề xuất máy, pending."]
    for reg in output["regions"]:
        review += ["", "## " + reg["region_id"], "", f"{reg['law_id']} — {reg['locator']} — [{reg['char_start']},{reg['char_end']})", "",
                   "Context unit: `" + str(reg["context_unit_id"]) + "`; không tạo unit cho vùng chưa phân tích.", "",
                   reg["source_quote"] or "(text rỗng; chưa giải mã visual)", "", reg["reason"], "",
                   "| Đơn vị | Loại ảnh hưởng | Lý do | Chặn vai trò |", "|---|---|---|---|"]
        for impact in (i for i in output["impacts"] if i["region_id"] == reg["region_id"]):
            review.append(f"| {impact['unit_id'] or '(vùng chưa có unit)'} | {impact['impact_kind']} | {impact['reason']} | {','.join(impact['blocks_roles']) or 'không gán ảnh hưởng thân luật'} |")
    (run / "technical_review.md").write_text("\n".join(review) + "\n", encoding="utf8", newline="\n")
    pending = ["# Việc còn pending", "", "Quyết định rà soát thực tế: " + str(len(output["decisions"])) + ". Không ghi tên người/nhóm phê duyệt giả.", "",
               "- Rà đúng bản ban hành và sửa đổi có tác động trước/tại 2025-01-01; tải hiện tại không chứng minh lịch sử.",
               "- Đối chiếu DOCX với PDF Công báo/bản ký số, giải quyết issue trong run mới nếu được duyệt.",
               "- Đọc đủ Điều 89 Luật 36 và các dẫn chiếu/ngoại lệ liên quan; lát bằng chứng hiện có chưa chứng minh rà toàn bộ.",
               "- Rà ngữ nghĩa hai bảng Luật 35; nội dung thay thế còn phụ thuộc văn bản đích và ngày áp dụng.",
               "- Chốt ma trận scope: quy hoạch/hạ tầng theo BRD §3.3; điều kiện phương tiện theo §3.1 còn cần quyết định phạm vi.",
               "- Nguồn, extraction, cây vẫn pending; corpus_version chưa được cấp. Chưa có đường promote/release trong Stage 5A.",
               "- Người rà soát ghi riêng scope, applicability hoặc technical: reviewer_ref, UTC, bằng chứng/locator và lý do; không cần hoàn thành các chiều cùng lúc.",
               "- unit_assessment chỉ được nạp về sau khi đủ hồ sơ, FK thật và các cổng kiểm định; không thay null bằng excluded giả."]
    (run / "pending_work.md").write_text("\n".join(pending) + "\n", encoding="utf8", newline="\n")


def copy_bundle(manifest_path, destination):
    manifest_path = Path(manifest_path).resolve()
    meta = check_files(manifest_path)
    for ref in [f["path"] for f in meta["files"]] + ["manifest.json", "manifest.sha256"]:
        target = resolve_ref(destination, ref)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as out:
            out.write(resolve_ref(manifest_path.parent, ref).read_bytes())


def build_run(tree_manifest, review_manifest, evidence_manifest, run_dir, config_path=DEFAULT_CONFIG, findings_path=DEFAULT_FINDINGS, submissions_path=None, raw_root=BASE_DIR):
    # All input validation and replay precede output/SQLite writes.
    result = validate_tree_bundle(tree_manifest, raw_root)
    if not result["technical_valid"] or not result["processing_success"]:
        raise ValueError("Invalid Stage 4 input: " + canonical(result))
    tree, pack, evidence = (Path(p).resolve().parent for p in (tree_manifest, review_manifest, evidence_manifest))
    config, requests = load_json(config_path), load_json(findings_path)
    for ref in config.get("scope_basis", []):
        if digest(resolve_ref(BASE_DIR, ref["path"]).read_bytes()) != ref["sha256"]:
            raise ValueError("Scope requirement source hash mismatch")
    submissions = load_json(submissions_path) if submissions_path else {"events": []}
    output, binding = compute(tree, pack, evidence, config, requests, submissions)
    with staged_run(run_dir, contract.VERSION, tree_manifest) as (run, report):
        for source, name in ((tree_manifest, "input_snapshot"), (review_manifest, "review_pack_snapshot"), (evidence_manifest, "evidence_snapshot")):
            copy_bundle(source, run / name)
        for ref in config.get("scope_basis", []):
            target = resolve_ref(run / "requirements_snapshot", ref["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(resolve_ref(BASE_DIR, ref["path"]).read_bytes())
        for name, value in (("config.json", config), ("finding_requests.json", requests), ("review_submissions.json", submissions), ("binding.json", binding)):
            write_json(run / name, value)
        if submissions_path:
            (run / "external_review_submission.input.json").write_bytes(Path(submissions_path).read_bytes())
        for name in ("pending_schema.sql", "pending_assessment.schema.json"):
            (run / name).write_bytes((SCHEMA / name).read_bytes())
        for key, name in EXPORTS.items():
            write_rows(run / name, output[key])
        write_readable(run, output)
        with closing(connect_sqlite(run / "assessment.pending.sqlite")) as db:
            db.executescript((run / "pending_schema.sql").read_text(encoding="utf8"))
            with db:
                for table, rows in database_rows(output, binding).items():
                    for row in rows:
                        db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
        write_json(run / "validation_report.json", summary_for(output))
        seal(run, {"manifest_type": contract.VERSION, "snapshot_date": contract.SNAPSHOT, "dataset_kind": config["dataset_kind"],
                   "binding": binding, "tool": tool_identity(), "built_at": now(), "release_eligible": False})
        checked = validate_run(run / "manifest.json", raw_root)
        report.update(checked)
        if not checked["technical_valid"]:
            raise ValueError(canonical(checked))
    return checked


def validate_run(manifest_path, raw_root=BASE_DIR):
    errors = []
    try:
        metadata = check_files(manifest_path)
        root = Path(manifest_path).resolve().parent
        if metadata["manifest_type"] != contract.VERSION or metadata["snapshot_date"] != contract.SNAPSHOT or metadata["release_eligible"] is not False:
            raise ValueError("Assessment manifest policy/snapshot/release mismatch")
        if metadata["tool"] != tool_identity():
            raise ValueError("Assessment tool/code version mismatch")
        check = validate_tree_bundle(root / "input_snapshot" / "manifest.json", raw_root)
        if not check["technical_valid"] or not check["processing_success"]:
            raise ValueError("Stage 4 snapshot invalid: " + canonical(check))
        for name in ("pending_schema.sql", "pending_assessment.schema.json"):
            if (root / name).read_bytes() != (SCHEMA / name).read_bytes():
                raise ValueError("Pending schema changed")
        expected, binding = compute(root / "input_snapshot", root / "review_pack_snapshot", root / "evidence_snapshot",
                                    load_json(root / "config.json"), load_json(root / "finding_requests.json"), load_json(root / "review_submissions.json"))
        for ref in load_json(root / "config.json").get("scope_basis", []):
            if digest(resolve_ref(root / "requirements_snapshot", ref["path"]).read_bytes()) != ref["sha256"]:
                raise ValueError("Scope requirement snapshot hash mismatch")
        submission_copy = root / "external_review_submission.input.json"
        if submission_copy.is_file():
            if load_json(submission_copy) != load_json(root / "review_submissions.json"):
                raise ValueError("External review submission original/normalized mismatch")
        elif expected["decisions"]:
            raise ValueError("Missing original external review submission")
        if metadata["binding"] != binding or load_json(root / "binding.json") != binding:
            raise ValueError("Input bundle/parser version/hash binding mismatch")
        from jsonschema import Draft202012Validator
        schema = Draft202012Validator(load_json(root / "pending_assessment.schema.json"))
        for row in expected["assessments"]:
            schema.validate(row)
        for key, name in EXPORTS.items():
            if read_rows(root / name) != expected[key]:
                raise ValueError("Export/replay mismatch: " + name)
        with closing(connect_sqlite(root / "assessment.pending.sqlite", readonly=True)) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Assessment SQLite integrity/FK failure")
            tables = database_rows(expected, binding)
            if schema_signature(db) != expected_signature((root / "pending_schema.sql").read_text(encoding="utf8")):
                raise ValueError("SQLite schema differs from pending design")
            existing = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if existing != set(tables):
                raise ValueError("Unexpected SQLite tables, including official stand-ins")
            for table, rows in tables.items():
                actual = [dict(row) for row in db.execute(f"SELECT * FROM {table}")]
                if sorted(map(canonical, actual)) != sorted(map(canonical, rows)):
                    raise ValueError("SQLite/export mismatch: " + table)
        summary = load_json(root / "validation_report.json")
        if summary != summary_for(expected):
            raise ValueError("Technical report/counts differ from replay; cannot claim legal verification/release")
    except Exception as exc:
        errors.append(str(exc))
    return {"technical_valid": not errors, "errors": errors, "legal_verification": "not_performed",
            "release_eligible": False, "target_candidate_count": 0, "context_candidate_count": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage 5A bounded pending assessment, no release/index/model")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("pilot")
    for name in ("tree-manifest", "review-manifest", "evidence-manifest", "run-dir"):
        build.add_argument("--" + name, type=Path, required=True)
    build.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    build.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS)
    build.add_argument("--decisions", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    candidates = sub.add_parser("candidates")
    candidates.add_argument("--manifest", type=Path, required=True)
    candidates.add_argument("--role", choices=["target", "context"], required=True)
    for cmd in (build, check, candidates):
        cmd.add_argument("--raw-root", type=Path, default=BASE_DIR)
    args = parser.parse_args(argv)
    try:
        if args.command == "pilot":
            result = build_run(args.tree_manifest, args.review_manifest, args.evidence_manifest, args.run_dir, args.config, args.findings, args.decisions, args.raw_root)
        else:
            result = validate_run(args.manifest, args.raw_root)
            if args.command == "candidates" and result["technical_valid"]:
                result.update(role=args.role, candidates=[], reason="All Stage 5A upstream acceptance gates remain pending; no activation.")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["technical_valid"] else 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
