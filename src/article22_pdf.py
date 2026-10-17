"""Narrow, reproducible PDF admission preparation. No general PDF parser or promotion.

Uses Stage 2/3 unchanged. All review decisions remain external to this command.
"""
import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys

from src import content_comparison
from src.assessment_evidence import check_files, inventory, now, seal, validate_evidence
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.content_comparison import compare_fields, select_interval, render_comparison
from src.extraction_pipeline import build_run as extract, validate_run as validate_extraction
from src.ingestion.legal_tree import UNIT_FIELDS, unit_id, span_id
from src.legal_parser import validate_run as validate_legacy
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, connect_sqlite, digest, require_contract, resolve_ref
from src.source_registry import (register, read_rows, write_rows, load_json, TABLES,
                                 schema_signature, expected_signature)

VERSION = "article22-pdf.v1"
DEFAULT_CONFIG = BASE_DIR / "config/article22_pdf.v1.json"
EXPECTED_NODES = [("document", None, "document", "36/2024/QH15", 0),
                  ("chapter_ii", "document", "chapter", "II", 1),
                  ("article_22", "chapter_ii", "article", "22", 12),
                  ("clause_1", "article_22", "clause", "1", 0),
                  ("clause_2", "article_22", "clause", "2", 1),
                  ("clause_3", "article_22", "clause", "3", 2)]
BLOCKERS = ["SOURCE_EDITION_AND_COMPLETENESS_REVIEW_PENDING", "EXTRACTION_REVIEW_PENDING",
            "MAPPED_FIELDS_AND_PARENT_CONTEXT_REVIEW_PENDING", "SCOPE_DECISIONS_PENDING",
            "APPLICABILITY_AND_HISTORY_DECISIONS_PENDING", "REAL_CORPUS_MEMBERSHIP_NOT_CREATED"]
LABELS = {"chapter": "Chương", "article": "Điều", "clause": "Khoản"}


def code_binding():
    return {"mapping": digest(Path(__file__).read_bytes()),
            "comparison": digest(Path(content_comparison.__file__).read_bytes()),
            "ddd_schema": digest((BASE_DIR / "schemas/data_model_v1/schema.sql").read_bytes())}


def require_config(config):
    if (config["policy_version"] != VERSION or config["snapshot_date"] != SNAPSHOT_DATE
            or config["law_id"] != "36/2024/QH15"):
        raise ValueError("Wrong mapping policy/law/snapshot")
    actual = [(n["key"], n["parent"], n["unit_type"], n["designation"], n["ordinal"]) for n in config["nodes"]]
    if actual != EXPECTED_NODES:
        raise ValueError("Scope is exactly four selected units plus two real ancestors")
    if len(config["pdf_parts"]) != 2 or [(r["order"], r["role"]) for r in config["pdf_parts"]] != [(1, "main"), (2, "continuation")]:
        raise ValueError("Expected two Gazette parts in explicit source-set order")
    for n in config["nodes"]:
        if type(n["ordinal"]) is not int or n["ordinal"] < 0:
            raise ValueError("Ordinal must be a source-order integer")
        if set(n["fields"]) != {"title", "text_original"}:
            raise ValueError("Expected title and own text selectors")
        for selectors in n["fields"].values():
            for s in selectors:
                if type(s["page"]) is not int or s["page"] < 1:
                    raise ValueError("Invalid selector page")


def preflight(evidence_manifest, tree_manifest, comparison_manifest, config):
    require_config(config)
    evidence = validate_evidence(evidence_manifest)
    checked = validate_legacy(tree_manifest)
    if not checked["technical_valid"]:
        raise ValueError("Legacy tree invalid: " + canonical(checked))
    old = check_files(comparison_manifest)
    if (old["input_stage4_manifest_sha256"] != digest(Path(tree_manifest).read_bytes())
            or old["evidence_manifest_sha256"] != digest(Path(evidence_manifest).read_bytes())
            or old["snapshot_date"] != SNAPSHOT_DATE or old["release_eligible"] is not False):
        raise ValueError("Comparison/tree/evidence binding mismatch")
    by_ref = {r["artifact_ref"]: r for r in evidence}
    for part in config["pdf_parts"]:
        row = by_ref[part["artifact_ref"]]
        if row["law_id"] != config["law_id"] or row["kind"] != "promulgation_pdf" or row["sha256"] != part["sha256"]:
            raise ValueError("PDF selection hash/law/kind mismatch")
    if by_ref[config["metadata_ref"]]["law_id"] != config["law_id"]:
        raise ValueError("Metadata law mismatch")
    return evidence


def pdf_pages(run):
    """Return page slices from Stage 3 normalized.txt/trace, never evidence page offsets."""
    records = read_rows(run / "extraction/extractions.pending.jsonl")
    sources = read_rows(run / "extraction/source_snapshot/files.pending.jsonl")
    main = next(r for r in sources if r["part_order"] == 1)
    record = next(r for r in records if r["extraction"]["file_id"] == main["file_id"])
    metadata = record["extraction"]
    text = resolve_ref(run / "extraction", metadata["text_ref"]).read_text(encoding="utf8")
    trace = load_json(resolve_ref(run / "extraction", record["trace_ref"]))
    pages = {n["locator"]["page_start"]: {"node": n, "text": text[n["char_start"]:n["char_end"]]}
             for n in trace["nodes"] if n["kind"] == "page"}
    return record, text, pages


def check_source_order(pages):
    """Only establish source ordinals for the selected chapter/article, not a PDF tree."""
    if pages[1]["text"].count("\nChương I\n") != 1 or pages[10]["text"].count("\nChương II\n") != 1:
        raise ValueError("Real chapter order cannot be established")
    region = "\n".join(pages[n]["text"] for n in range(10, 20))
    region = region[region.index("\nChương II\n") + 1:region.index("Điều 22. ")]
    headings = re.findall(r"^Điều (\d+)\. ", region, flags=re.M)
    if headings != [str(n) for n in range(10, 22)]:
        raise ValueError("Source article ordinal is uncertain")


def map_units(config, record, pages):
    """Build only configured units; LF joins slices exactly as DDD requires."""
    check_source_order(pages)
    units, spans, mappings, keyed = [], [], [], {}
    for spec in config["nodes"]:
        parent = keyed.get(spec["parent"])
        unit = {"law_id": config["law_id"], "parent_unit_id": parent["unit_id"] if parent else None,
                "unit_type": spec["unit_type"], "designation": spec["designation"], "ordinal": spec["ordinal"]}
        unit["canonical_path"] = (parent["canonical_path"] + "/" if parent else "") + spec["unit_type"] + ":" + spec["designation"]
        unit["citation_path"] = (parent["citation_path"] + " > " + LABELS[spec["unit_type"]] + " " + spec["designation"]) if parent else config["law_id"]
        own = []
        for field, selectors in spec["fields"].items():
            parts, relative = [], 0
            for order, selector in enumerate(selectors):
                page = pages[selector["page"]]
                a, b = select_interval(page["text"], selector)
                quote = page["text"][a:b]
                # No normalization/folding here. Stage 3 artifact is already NFC/LF.
                start = page["node"]["char_start"]
                span = {"extraction_id": record["extraction"]["extraction_id"], "field_name": field,
                        "span_order": order, "char_start": start + a, "char_end": start + b,
                        "locator_json": canonical(page["node"]["locator"]), "quote_sha256": digest(quote.encode("utf8"))}
                if order:
                    relative += 1  # DDD LF join; not a character copied from some other page.
                own.append((span, {"key": spec["key"], "field_name": field, "span_order": order,
                                   "field_char_start": relative, "field_char_end": relative + len(quote),
                                   "page": selector["page"], "pdf_page_char_start": a, "pdf_page_char_end": b,
                                   "extraction_char_start": start + a, "extraction_char_end": start + b,
                                   "page_extraction_char_start": start, "locator_id": page["node"]["locator_id"],
                                   "quote": quote, "quote_sha256": span["quote_sha256"]}))
                parts.append(quote)
                relative += len(quote)
            unit[field] = "\n".join(parts)
        unit["text_sha256"] = digest(unit["text_original"].encode("utf8"))
        unit["unit_id"] = unit_id(unit)
        for span, mapping in own:
            span["unit_id"] = unit["unit_id"]
            span["span_id"] = span_id(span)
            spans.append(span)
            mappings.append({**mapping, "unit_id": unit["unit_id"], "span_id": span["span_id"],
                             "extraction_id": span["extraction_id"], "extraction_text_ref": "extraction/" + record["extraction"]["text_ref"],
                             "status": "pending", "not_a_reviewer_decision": True})
        units.append(unit)
        keyed[spec["key"]] = unit
    return units, spans, mappings


def compare_legacy(run, units, mappings, pages, config):
    legacy = read_rows(run / "inputs/legacy_tree/legal_units.pending.jsonl")
    legacy_spans = read_rows(run / "inputs/legacy_tree/source_spans.pending.jsonl")
    previous = read_rows(run / "inputs/comparison/comparison.jsonl")
    evidence = read_rows(run / "inputs/evidence/evidence.jsonl")
    main = next(r for r in evidence if r["artifact_ref"] == config["pdf_parts"][0]["artifact_ref"])
    rows, identities = [], []
    for unit in units:
        matches = [u for u in legacy if u["law_id"] == unit["law_id"] and u["canonical_path"] == unit["canonical_path"]]
        if len(matches) != 1:
            raise ValueError("Ambiguous/missing legacy position")
        old = matches[0]
        old_payload = {k: old[k] for k in UNIT_FIELDS}
        new_payload = {k: unit[k] for k in UNIT_FIELDS}
        same = old_payload == new_payload
        if same != (old["unit_id"] == unit["unit_id"]):
            raise ValueError("ID preservation violates DDD identity payload")
        identities.append({"old_unit_id": old["unit_id"], "new_unit_id": unit["unit_id"],
                           "canonical_path": unit["canonical_path"], "identity_payload_unchanged": same,
                           "changed_identity_fields": [k for k in UNIT_FIELDS if old[k] != unit[k]],
                           "old_identity_payload": old_payload, "new_identity_payload": new_payload,
                           "old_decisions_carried_forward": False})
        for field in ("title", "text_original"):
            if not unit[field] and not old[field]:
                continue
            row = {"old_unit_id": old["unit_id"], "new_unit_id": unit["unit_id"], "field": field,
                   "citation": unit["citation_path"], **compare_fields(old[field], unit[field]),
                   "input_spans": [s for s in legacy_spans if s["unit_id"] == old["unit_id"] and s["field_name"] == field],
                   "mapping_span_ids": [m["span_id"] for m in mappings if m["unit_id"] == unit["unit_id"] and m["field_name"] == field],
                   "previous_comparison_reproduced": None, "origin": "agent_comparison_not_reviewer"}
            prior = [p for p in previous if p["unit_id"] == old["unit_id"] and p["field"] == field]
            if unit["unit_type"] in {"article", "clause"}:
                if len(prior) != 1:
                    raise ValueError("Missing prior comparison for selected field")
                p = prior[0]
                if (p["input_text"] != old[field] or p["official_pdf_sha256"] != main["sha256"]
                        or p["official_text"] != unit[field] or p["classification"] != row["classification"]
                        or digest(unit[field].encode("utf8")) != p["official_quote_sha256"]):
                    raise ValueError("New PDF mapping differs from comparison table")
                # Confirm the old evidence slice separately. Its offsets are never used to create spans.
                captured = resolve_ref(run / "inputs/evidence", f"02/page-{p['official_page']:03d}.txt").read_text(encoding="utf8")
                if captured[p["official_char_start"]:p["official_char_end"]] != unit[field]:
                    raise ValueError("Old evidence page slice mismatch")
                row["previous_comparison_reproduced"] = True
            rows.append(row)
    if sum(r["previous_comparison_reproduced"] is True for r in rows) != 5:
        raise ValueError("Expected exactly five previously compared fields")
    return rows, identities


def source_and_basis(run, config):
    evidence = read_rows(run / "inputs/evidence/evidence.jsonl")
    by_ref = {r["artifact_ref"]: r for r in evidence}
    registry = load_json(run / "source_registration/registration_input.json")
    sources = read_rows(run / "source_registration/files.pending.jsonl")
    declaration = registry["documents"][0]
    # Metadata is a real descriptive row, not a verification decision.
    document = {"law_id": config["law_id"], "source_id": declaration["source_id"],
                "law_title": declaration["declared"]["law_title"], "document_type": "law",
                "issued_date": "2024-06-27", "document_effective_from": None,
                "source_url": by_ref[config["metadata_ref"]]["final_url"],
                "scope_note": "Chuẩn bị riêng Điều 22 và Khoản 1–3; hai nút cha là dependency; chưa phát hành."}
    # Check the quoted issuance facts in actual captured PDF bytes/text, not today's date.
    continued = resolve_ref(run / "inputs/evidence", "03/page-001.txt").read_text(encoding="utf8")
    if "Luật số 36/2024/QH15 ngày 27 tháng 6 năm 2024" not in continued:
        raise ValueError("Missing issuance/law evidence")
    metadata_text = resolve_ref(run / "inputs/evidence", config["metadata_ref"]).read_text(encoding="utf8")
    files, facts = [], []
    for part in config["pdf_parts"]:
        evidence_row = by_ref[part["artifact_ref"]]
        source = next(r for r in sources if r["part_order"] == part["order"])
        if evidence_row["final_url"].rsplit('/', 1)[-1] not in metadata_text:
            raise ValueError("Gazette part not linked from captured document metadata")
        data = resolve_ref(run / "inputs/evidence", part["artifact_ref"]).read_bytes()
        if digest(data) != source["measured"]["sha256"]:
            raise ValueError("Source/capture hash mismatch")
        file = {"file_id": source["file_id"], "law_id": config["law_id"], "source_set_id": config["source_set_id"],
                "file_role": part["role"], "part_order": part["order"], "filename": Path(part["artifact_ref"]).name,
                "raw_file_ref": "inputs/evidence/" + part["artifact_ref"], "download_url": evidence_row["final_url"],
                "mime_type": "application/pdf", "size_bytes": len(data), "sha256": digest(data),
                "retrieved_at": evidence_row["accessed_at"]}
        require_contract("source_file", file)
        files.append(file)
        facts.append({"file_id": file["file_id"], "evidence_id": evidence_row["evidence_id"],
                      "capture_record": evidence_row, "known_facts": file,
                      "edition_review_status": "pending", "source_set_completeness_review": "pending",
                      "source_status": "pending", "whole_legacy_docx_verified": False})
    require_contract("legal_document", document)
    basis = read_rows(run / "inputs/comparison/effectiveness_basis.jsonl")
    for row in basis:
        page_ref = "03/" + Path(row["text_ref"]).name
        text = resolve_ref(run / "inputs/evidence", page_ref).read_text(encoding="utf8")
        quote = text[row["char_start"]:row["char_end"]]
        if quote != row["quote"] or digest(quote.encode("utf8")) != row["quote_sha256"]:
            raise ValueError("Effectiveness evidence slice mismatch")
        row["text_ref"] = "inputs/evidence/" + page_ref
        row["pdf_ref"] = "inputs/evidence/03/snapshot.pdf"
        row["pdf_sha256"] = by_ref["03/snapshot.pdf"]["sha256"]
        row["evidence_id"] = by_ref["03/snapshot.pdf"]["evidence_id"]
        row["offset_namespace"] = "captured_pdf_page_text_unicode_code_point"
    return document, files, facts, basis


def compute(run):
    config = load_json(run / "mapping_config.json")
    require_config(config)
    record, text, pages = pdf_pages(run)
    units, spans, mappings = map_units(config, record, pages)
    from jsonschema import Draft202012Validator
    for kind, rows in (("legal_unit", units), ("source_span", spans)):
        schema = load_json(BASE_DIR / "schemas/legal_tree_v1" / f"{kind}.schema.json")
        for row in rows:
            Draft202012Validator(schema).validate(row)
    for m in mappings:
        quote = text[m["extraction_char_start"]:m["extraction_char_end"]]
        if quote != m["quote"] or digest(quote.encode("utf8")) != m["quote_sha256"]:
            raise ValueError("Mapping roundtrip/hash mismatch")
    comparisons, identities = compare_legacy(run, units, mappings, pages, config)
    document, files, facts, basis = source_and_basis(run, config)
    extractions = [r["extraction"] for r in read_rows(run / "extraction/extractions.pending.jsonl")]
    for e in extractions:
        e["text_ref"] = "extraction/" + e["text_ref"]
        require_contract("extraction", e)
    assessments = []
    for spec, u in zip(config["nodes"], units):
        is_target = u["unit_type"] == "clause"
        is_context = u["unit_type"] == "article"
        assessments.append({"unit_id": u["unit_id"], "unit_sha256": digest(canonical(u).encode("utf8")),
                            "snapshot_date": SNAPSHOT_DATE, "binding_ref": "binding.json",
                            "role_proposal": "target" if is_target else "lead_in_and_heading" if is_context else "structural_dependency_only",
                            "scope_candidate": "included" if is_target else "supporting" if is_context else None,
                            "scope_reason": "Quy tắc nhường đường áp dụng trực tiếp cho người điều khiển phương tiện." if is_target
                            else "Điều 22 chứa điều kiện dẫn nhập cần đọc cùng ba Khoản." if is_context
                            else "Chỉ giữ cha thật cho FK; chưa chọn title/preamble làm context truy hồi.",
                            "technical_result": "slice_hash_and_roundtrip_passed_not_verified",
                            "assessment_required_for_planned_use": is_target or is_context,
                            "context_dependency_ids": [units[2]["unit_id"]] if is_target else [],
                            "effective_from_candidate": "2025-01-01" if is_target or is_context else None,
                            "effective_to_candidate": None,
                            "applicability_candidate": "applicable_at_snapshot_candidate" if is_target or is_context else None,
                            "applicability_reason": "Điều 88 khoản 1; ngoại lệ khoản 2 chỉ Điều 10 khoản 3; Điều 89 cần rà chuyển tiếp; tra cứu lịch sử chưa toàn diện.",
                            "evidence_refs": ["effectiveness_basis.jsonl", "inputs/comparison/agent_findings.json"],
                            "dimensions": {d: {"status": "pending", "decision_id": None} for d in ("scope", "applicability", "technical")},
                            "ddd_unit_assessment": {"corpus_version": None, "unit_id": u["unit_id"], "scope_status": None,
                                                    "applicability_status": "pending_review", "effective_from": None, "effective_to": None,
                                                    "verification_ref": None, "verified_at": None, "reviewer_ref": None,
                                                    "decision_note": "Chưa có quyết định thực tế cho binding PDF mới."},
                            "blockers": BLOCKERS if is_target or is_context else
                            [b for b in BLOCKERS if b not in {"SCOPE_DECISIONS_PENDING", "APPLICABILITY_AND_HISTORY_DECISIONS_PENDING"}],
                            "ready_to_load_assessment": False, "release_eligible": False})
    return {"documents.prepared.jsonl": [document], "source_files.prepared.jsonl": files,
            "source_facts.pending.jsonl": facts, "extractions.pending.jsonl": extractions,
            "legal_units.pending.jsonl": units, "source_spans.pending.jsonl": spans,
            "mapping.pending.jsonl": mappings, "comparison.jsonl": comparisons,
            "identity_crosswalk.jsonl": identities, "effectiveness_basis.jsonl": basis,
            "assessments.pending.jsonl": assessments}


def database_payload(payload):
    return {"legal_document": payload["documents.prepared.jsonl"], "source_file": payload["source_files.prepared.jsonl"],
            "extraction": payload["extractions.pending.jsonl"], "legal_unit": payload["legal_units.pending.jsonl"],
            "source_span": payload["source_spans.pending.jsonl"]}


def inspect(run):
    manifest = check_files(run / "manifest.json") if (run / "manifest.json").exists() else None
    binding = load_json(run / "binding.json")
    if (binding["code_sha256"] != code_binding() or binding["snapshot_date"] != SNAPSHOT_DATE
            or binding.get("policy_version") != VERSION
            or set(binding) != {"policy_version", "snapshot_date", "code_sha256", "input_sha256"}):
        raise ValueError("Mapping code/schema/snapshot binding mismatch")
    preflight(run / "inputs/evidence/manifest.json", run / "inputs/legacy_tree/manifest.json",
              run / "inputs/comparison/manifest.json", load_json(run / "mapping_config.json"))
    checks = {"evidence": run / "inputs/evidence/manifest.json", "legacy_tree": run / "inputs/legacy_tree/manifest.json",
              "comparison": run / "inputs/comparison/manifest.json", "extraction": run / "extraction/manifest.json",
              "config": run / "mapping_config.json"}
    if binding["input_sha256"] != {k: digest(p.read_bytes()) for k, p in checks.items()}:
        raise ValueError("Input binding mismatch")
    result = validate_extraction(run / "extraction/manifest.json")
    if not result["technical_valid"] or not result["processing_success"]:
        raise ValueError("Stage 3 bundle invalid: " + canonical(result))
    payload = compute(run)
    for name, expected in payload.items():
        if read_rows(run / name) != expected:
            raise ValueError("Export replay mismatch: " + name)
    sql = (BASE_DIR / "schemas/data_model_v1/schema.sql").read_bytes()
    if (run / "schema.sql").read_bytes() != sql:
        raise ValueError("Official schema changed")
    with closing(connect_sqlite(run / "admission.prepared.sqlite", readonly=True)) as db:
        if schema_signature(db) != expected_signature(sql.decode("utf8")):
            raise ValueError("Prepared SQLite schema mismatch")
        if list(db.execute("PRAGMA foreign_key_check")) or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Prepared SQLite FK/integrity failure")
        desired = database_payload(payload)
        counts = {}
        for table in TABLES:
            actual = [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
            if sorted(actual, key=canonical) != sorted(desired.get(table, []), key=canonical):
                raise ValueError("SQLite/export mismatch: " + table)
            counts[table] = len(actual)
    if read_rows(run / "review_decision_history.jsonl"):
        raise ValueError("This preparation command cannot create reviewer decisions")
    report = {"technical_valid": True, "errors": [], "snapshot_date": SNAPSHOT_DATE,
              "unit_count": len(payload["legal_units.pending.jsonl"]), "span_count": len(payload["source_spans.pending.jsonl"]),
              "compared_selected_fields": 5, "previous_comparison_reproduced": True,
              "source_set_review_status": "pending", "extraction_review_status": "pending",
              "review_decision_count": 0, "official_schema_preparation_counts": counts,
              "extraction_issue_count": result["issue_count"], "release_eligible": False,
              "blockers": BLOCKERS, "legal_verification": "not_performed"}
    if manifest is not None:
        if (manifest["manifest_type"] != VERSION or manifest["binding"] != binding or manifest["release_eligible"] is not False
                or manifest["snapshot_date"] != SNAPSHOT_DATE or manifest["blockers"] != BLOCKERS
                or manifest["files"] != inventory(run)):
            raise ValueError("Mapping manifest metadata/artifact set mismatch")
        if load_json(run / "validation_report.json") != report:
            raise ValueError("Validation report mismatch")
        if (run / "review.md").read_text(encoding="utf8") != render_review(payload):
            raise ValueError("Review report replay mismatch")
        if (run / "comparison.md").read_text(encoding="utf8") != render_comparison(payload["comparison.jsonl"]):
            raise ValueError("Comparison report replay mismatch")
    return report


def render_review(payload):
    units, assessments = payload["legal_units.pending.jsonl"], payload["assessments.pending.jsonl"]
    lines = ["# Điều 22 Luật 36 — PDF, bản chuẩn bị chưa phát hành", "",
             "Snapshot 2025-01-01. Kết luận agent; chưa có quyết định reviewer. 6 nút = 4 đơn vị được chọn + 2 cha thật.",
             "Ordinal giữ vị trí trong nguồn đầy đủ (Chương II=1; Điều 22=12), không đánh lại từ 0 trong cây con.", "",
             "| Citation | Vai trò đề xuất | Scope đề xuất | Kỹ thuật | Hiệu lực đề xuất |", "|---|---|---|---|---|"]
    for u, a in zip(units, assessments):
        lines.append(f"| {u['citation_path']} | {a['role_proposal']} | {a['scope_candidate']} | roundtrip/hash đạt, review pending | {a['effective_from_candidate']} / pending |")
    for u, a in zip(units, assessments):
        lines += ["", "## " + u["citation_path"], "", "unit_id: `" + u["unit_id"] + "`",
                  "", "parent_unit_id: `" + str(u["parent_unit_id"]) + "`", "", "Title:", "```text", u["title"], "```",
                  "Nội dung riêng (không chép con):", "```text", u["text_original"], "```", "", a["scope_reason"], "",
                  "| Field | Span ID | Trang PDF | Field [start,end) | Extraction [start,end) | Page [start,end) | Quote SHA-256 |",
                  "|---|---|---:|---|---|---|---|"]
        for m in payload["mapping.pending.jsonl"]:
            if m["unit_id"] == u["unit_id"]:
                lines.append(f"| {m['field_name']} | {m['span_id']} | {m['page']} | [{m['field_char_start']},{m['field_char_end']}) | [{m['extraction_char_start']},{m['extraction_char_end']}) | [{m['pdf_page_char_start']},{m['pdf_page_char_end']}) | {m['quote_sha256']} |")
        lines += ["", "Kỹ thuật: " + a["technical_result"], "Context cần rà: " + canonical(a["context_dependency_ids"]),
                  "Hiệu lực: " + a["applicability_reason"], "Blocker: " + ", ".join(a["blockers"])]
    lines += ["", "## Nguồn và căn cứ", ""]
    for f in payload["source_files.prepared.jsonl"]:
        lines += [f"- part {f['part_order']}: `{f['raw_file_ref']}`; file_id `{f['file_id']}`; SHA-256 `{f['sha256']}`; tải thật {f['retrieved_at']}; URL {f['download_url']}"]
    lines += ["", "Điều 88 khoản 1–2: phần tiếp, trang PDF 58 / trang in 59. Điều 89: PDF 58–61. Các quote/hash trong effectiveness_basis.jsonl.",
              "Lịch sử tra cứu cũ còn giới hạn; ấn bản hợp nhất 2026 chỉ là đầu mối, không thay bản tại snapshot.",
              "Nguồn, extraction, cây và cả 6 đơn vị chưa được gán verified; 3 chiều review đều pending.",
              "Extraction phần đầu có PDF_PAGE_NO_TEXT tại trang 21: ảnh render quan sát có thông tin xuất bản dạng nét, không phải chứng cứ trang trắng; chưa OCR/resolve.",
              "Không suy toàn file đã verified từ bốn đơn vị. Hai cha là dependency, không đồng nghĩa toàn Chương II đã nhập.",
              "", "## Việc người rà soát cần ghi nhận", "",
              "1. Tiếp nhận đúng bản Công báo 977–978 và phần tiếp 979–980; xác nhận đủ phần trong source set, URL/time đã có thật.",
              "2. Review extraction chất lượng theo file cho phần được dùng: DDD review_status thuộc extraction, chưa hỗ trợ cờ verified từng vùng. Không nâng cả file từ 5 field. Trang 21 cần ghi nhận non-body qua ảnh, không gọi trang rỗng.",
              "3. Technical: đọc trang 1, 10, 19; đối chiếu title/preamble thật của hai cha; title/đoạn dẫn Điều 22 + từng Khoản, source spans và context Điều 22. Cha không mang toàn bộ con.",
              "4. Scope: đề xuất included ba Khoản; supporting title/đoạn dẫn Điều 22. Hai cha chỉ dependency; chỉ review scope/applicability nếu sau này chọn làm context.",
              "5. Applicability: kết luận riêng cho bốn đơn vị, kiểm Điều 88/89 và lịch sử trước snapshot; nếu chấp nhận 2025-01-01, ghi bằng chứng, lý do, reviewer_ref và thời gian thật trên binding PDF mới.",
              "6. Tạo corpus draft với phiên bản/thành viên/metadata thật khi đủ điều kiện; chuyển assessment ba chiều sang DDD bằng hồ sơ quyết định thực tế. Chưa có corpus/version giả, chunk hay index.",
              "", "Không yêu cầu chữ ký số hoặc hệ thống phân quyền mới. Giới hạn tra cứu chưa phải kết luận nguồn không hợp lệ."]
    return "\n".join(lines) + "\n"


def build(evidence_manifest, tree_manifest, comparison_manifest, run_dir, config_path=DEFAULT_CONFIG):
    target = staging_path(run_dir)
    for path in (evidence_manifest, tree_manifest, comparison_manifest):
        if Path(path).resolve().parent in target.parents:
            raise ValueError("New run must not be nested inside an existing input bundle")
    config = load_json(config_path)
    preflight(evidence_manifest, tree_manifest, comparison_manifest, config)
    # Preflight before creating output. Snapshots preserve exact source/capture/legacy bytes.
    with staged_run(run_dir, VERSION, evidence_manifest) as (run, run_report):
        for name, path in (("evidence", evidence_manifest), ("legacy_tree", tree_manifest), ("comparison", comparison_manifest)):
            shutil.copytree(Path(path).resolve().parent, run / "inputs" / name)
        write_json(run / "mapping_config.json", config)
        registry = load_json(BASE_DIR / "config/source_registration.v1.json")
        registry["documents"] = [r for r in registry["documents"] if r["law_id"] == config["law_id"]]
        registry["files"] = [{"law_id": config["law_id"], "source_set_id": config["source_set_id"],
                              "part_order": p["order"], "file_role": p["role"], "expected_sha256": p["sha256"],
                              "raw_file_ref": (run / "inputs/evidence" / p["artifact_ref"]).relative_to(BASE_DIR).as_posix()}
                             for p in config["pdf_parts"]]
        write_json(run / "registration_input.json", registry)
        register(run / "registration_input.json", run / "source_registration")
        extract(run / "source_registration/manifest.json", run / "extraction")
        binding = {"policy_version": VERSION, "snapshot_date": SNAPSHOT_DATE, "code_sha256": code_binding(),
                   "input_sha256": {k: digest(p.read_bytes()) for k, p in {
                       "evidence": run / "inputs/evidence/manifest.json", "legacy_tree": run / "inputs/legacy_tree/manifest.json",
                       "comparison": run / "inputs/comparison/manifest.json", "extraction": run / "extraction/manifest.json",
                       "config": run / "mapping_config.json"}.items()}}
        write_json(run / "binding.json", binding)
        payload = compute(run)
        for name, rows in payload.items():
            write_rows(run / name, rows)
        write_rows(run / "review_decision_history.jsonl", [])
        sql = (BASE_DIR / "schemas/data_model_v1/schema.sql").read_bytes()
        (run / "schema.sql").write_bytes(sql)
        with closing(connect_sqlite(run / "admission.prepared.sqlite")) as db:
            db.executescript(sql.decode("utf8"))
            with db:
                for table, rows in database_payload(payload).items():
                    for row in rows:
                        db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", list(row.values()))
        (run / "review.md").write_text(render_review(payload), encoding="utf8", newline="\n")
        (run / "comparison.md").write_text(render_comparison(payload["comparison.jsonl"]), encoding="utf8", newline="\n")
        with (run / "review.csv").open("x", encoding="utf8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["citation", "unit_id", "parent_unit_id", "title", "text_original", "scope_candidate", "technical", "effective_from_candidate", "blockers"])
            for u, a in zip(payload["legal_units.pending.jsonl"], payload["assessments.pending.jsonl"]):
                writer.writerow([u["citation_path"], u["unit_id"], u["parent_unit_id"], u["title"], u["text_original"],
                                 a["scope_candidate"], a["technical_result"], a["effective_from_candidate"], canonical(a["blockers"])])
        result = inspect(run)
        write_json(run / "validation_report.json", result)
        seal(run, {"manifest_type": VERSION, "snapshot_date": SNAPSHOT_DATE, "built_at": now(),
                   "binding": binding, "release_eligible": False, "blockers": BLOCKERS})
        result = inspect(run)
        run_report.update(result)
    return result


def validate(manifest_path):
    try:
        path = Path(manifest_path).resolve()
        if path.name != "manifest.json" or not path.is_file():
            raise ValueError("Expected an existing manifest.json")
        return inspect(path.parent)
    except (OSError, ValueError, KeyError, TypeError, StopIteration, sqlite3.Error) as exc:
        return {"technical_valid": False, "errors": [f"{type(exc).__name__}: {exc}"], "release_eligible": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare only Gazette Article 22 L36; no corpus activation")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare")
    create.add_argument("--evidence-manifest", type=Path, required=True)
    create.add_argument("--tree-manifest", type=Path, required=True)
    create.add_argument("--comparison-manifest", type=Path, required=True)
    create.add_argument("--run-dir", type=Path, required=True)
    create.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    check = commands.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--require-corpus-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build(args.evidence_manifest, args.tree_manifest, args.comparison_manifest, args.run_dir, args.config) if args.command == "prepare" else validate(args.manifest)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["technical_valid"] and not (getattr(args, "require_corpus_ready", False) and not result["release_eligible"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
