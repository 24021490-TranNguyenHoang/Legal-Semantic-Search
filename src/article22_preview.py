"""Pending-only chunk/context preview and agent review; never a serving corpus."""
import argparse
from html.parser import HTMLParser
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import sys

from src import preview_tokens
from src.article22_pdf import validate as validate_mapping
from src.assessment_evidence import check_files, inventory, now, seal
from src.assessment_contracts import utc_time
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows

VERSION = "article22-context-preview.v1"
DEFAULT_CONFIG = BASE_DIR / "config/article22_preview.v1.json"
EXTRA_BLOCKERS = ["PREVIEW_NOT_A_CORPUS", "AGENT_REVIEW_NOT_REVIEWER_DECISION", "TOKEN_BUDGET_NOT_RELEASE_POLICY"]
PAGES = ((2, 1), (2, 10), (2, 19), (2, 20), (2, 21), (3, 1), (3, 58), (3, 59), (3, 60), (3, 61))


def hash_json(value):
    return digest(canonical(value).encode("utf8"))


def code_binding():
    return {"preview": digest(Path(__file__).read_bytes()), "tokenizer_worker": digest(Path(preview_tokens.__file__).read_bytes()),
            "preview_schema": digest((BASE_DIR / "schemas/chunk_preview_v1/preview.schema.json").read_bytes())}


def require_config(cfg):
    if (cfg["policy_version"] != VERSION or cfg["snapshot_date"] != SNAPSHOT_DATE
            or cfg["effective_from"] is not None or cfg["effective_to"] is not None
            or cfg["applicability_status"] != "pending_review" or cfg["tokenizer_model_id"] != preview_tokens.MODEL_ID
            or cfg["tokenizer_revision"] != preview_tokens.REVISION
            or type(cfg["token_limit"]) is not int or not 1 <= cfg["token_limit"] <= 256
            or cfg["budget_status"] != "preview_only_not_release_policy"):
        raise ValueError("Invalid preview/snapshot/pending/token policy")


def mapping_data(root):
    return {"document": read_rows(root / "documents.prepared.jsonl")[0],
            "files": read_rows(root / "source_files.prepared.jsonl"),
            "extractions": read_rows(root / "extractions.pending.jsonl"),
            "units": read_rows(root / "legal_units.pending.jsonl"), "spans": read_rows(root / "source_spans.pending.jsonl")}


def source_proof(data, root, unit, field):
    spans = sorted([s for s in data["spans"] if s["unit_id"] == unit["unit_id"] and s["field_name"] == field], key=lambda s: s["span_order"])
    parts, proof = [], []
    if len(spans) != 1 or spans[0]["span_order"] != 0:
        raise ValueError("Narrow preview expects one exact source span per selected field")
    for s in spans:
        e = next(e for e in data["extractions"] if e["extraction_id"] == s["extraction_id"])
        f = next(f for f in data["files"] if f["file_id"] == e["file_id"])
        text = resolve_ref(root, e["text_ref"]).read_text(encoding="utf8")
        q = text[s["char_start"]:s["char_end"]]
        if not 0 <= s["char_start"] < s["char_end"] <= len(text) or digest(q.encode("utf8")) != s["quote_sha256"]:
            raise ValueError("Target/context source slice/hash mismatch")
        parts.append(q)
        proof.append({"file_id": f["file_id"], "raw_file_ref": "mapping_snapshot/" + f["raw_file_ref"], "raw_sha256": f["sha256"],
                      "span_id": s["span_id"], "extraction_id": e["extraction_id"], "text_ref": "mapping_snapshot/" + e["text_ref"],
                      "text_sha256": e["text_sha256"], "char_start": s["char_start"], "char_end": s["char_end"],
                      "locator": json.loads(s["locator_json"]), "quote_sha256": s["quote_sha256"]})
    if "\n".join(parts) != unit[field]:
        raise ValueError("Own field does not roundtrip to source spans")
    return canonical(proof)


def chunk_identity(chunk, contexts):
    # Exact chunk.v1 payload/key names from the supplied design validate_design.py.
    keys = ["unit_id", "segment_no", "unit_char_start", "unit_char_end", "text_original", "chunk_policy_version",
            "law_id", "law_title", "citation_path", "source_url", "effective_from", "effective_to", "applicability_status"]
    return {"identity_schema": "chunk.v1", **{k: chunk[k] for k in keys},
            "contexts": [{k: c[k] for k in ["unit_id", "field_name", "char_start", "char_end", "context_role", "context_order"]} for c in contexts]}


def make_chunks(data, root, config, blockers):
    require_config(config)
    units = data["units"]
    article = next(u for u in units if u["unit_type"] == "article" and u["designation"] == "22")
    clauses = sorted([u for u in units if u["parent_unit_id"] == article["unit_id"]], key=lambda u: u["ordinal"])
    if [u["designation"] for u in clauses] != ["1", "2", "3"] or any(u["unit_type"] != "clause" for u in clauses) or len(units) != 6:
        raise ValueError("Preview only permits the three whole clauses and real dependencies")
    if any(e["review_status"] != "pending" for e in data["extractions"]):
        raise ValueError("Preview must preserve pending extraction state")
    doc = data["document"]
    chunks, contexts = [], []
    for u in clauses:
        own_contexts = []
        for order, field in enumerate(["title", "text_original"]):
            if not article[field]:
                raise ValueError("Missing article title/lead required by selected context plan")
            own_contexts.append({"corpus_version": None, "unit_id": article["unit_id"], "context_order": order,
                                 "field_name": field, "char_start": 0, "char_end": len(article[field]),
                                 "context_role": "heading" if field == "title" else "lead_in",
                                 "source_locator": source_proof(data, root, article, field), "preview_only": True, "release_eligible": False})
        context_text = "\n".join(article[c["field_name"]][c["char_start"]:c["char_end"]] for c in own_contexts)
        search = "\n\n".join([doc["law_title"], u["citation_path"], context_text, u["text_original"]])
        row = {"corpus_version": None, "unit_id": u["unit_id"], "parent_unit_id": u["parent_unit_id"],
               **{k: doc[k] for k in ["source_id", "law_id", "law_title", "source_url"]}, "citation_path": u["citation_path"],
               "source_locator": source_proof(data, root, u, "text_original"), "segment_no": 1,
               "unit_char_start": 0, "unit_char_end": len(u["text_original"]), "text_original": u["text_original"],
               "context_text": context_text, "text_for_search": search, "content_sha256": digest(search.encode("utf8")),
               "chunk_policy_version": VERSION, "snapshot_date": SNAPSHOT_DATE, "effective_from": None, "effective_to": None,
               "applicability_status": "pending_review", "preview_only": True, "release_eligible": False, "release_blockers": blockers}
        row["chunk_id"] = "c_" + hash_json(chunk_identity(row, own_contexts))
        for c in own_contexts:
            c["chunk_id"] = row["chunk_id"]
        chunks.append(row)
        contexts.extend(own_contexts)
    return sorted(chunks, key=lambda c: c["chunk_id"]), sorted(contexts, key=lambda c: (c["chunk_id"], c["context_order"]))


class MetadataHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cells, self.values, self.links = [], [], {}, []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.rows.append([])
        elif tag == "td":
            self.cells.append([])
        elif tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("https://"):
                self.links.append(href)

    def handle_data(self, value):
        if self.cells:
            self.cells[-1].append(value)

    def handle_endtag(self, tag):
        if tag == "td" and self.cells:
            value = " ".join(" ".join(self.cells.pop()).split())
            if self.rows:
                self.rows[-1].append(value)
        elif tag == "tr" and self.rows:
            row = self.rows.pop()
            if len(row) == 2 and row[0] in {"Số ký hiệu", "Ngày ban hành", "Trích yếu", "Ngày có hiệu lực"}:
                if row[0] in self.values and self.values[row[0]] != row[1]:
                    raise ValueError("Conflicting captured HTML metadata")
                self.values[row[0]] = row[1]


def agent_findings(root, data, visual):
    evroot = root / "inputs/evidence"
    html_ref = evroot / "01/snapshot.html"
    parser = MetadataHTML()
    parser.feed(html_ref.read_text(encoding="utf8"))
    expected = {"Số ký hiệu": "36/2024/QH15", "Ngày ban hành": "27-06-2024",
                "Trích yếu": "Luật Trật tự, an toàn giao thông đường bộ"}
    if any(parser.values.get(k) != v for k, v in expected.items()):
        raise ValueError("Captured HTML identity/issuance mismatch")
    refs = [{"artifact_ref": "mapping_snapshot/inputs/evidence/01/snapshot.html", "sha256": digest(html_ref.read_bytes()), "locator": "metadata table: Số ký hiệu / Ngày ban hành / Trích yếu / Tài liệu đính kèm"}]
    captures = read_rows(evroot / "evidence.jsonl")
    for f in data["files"]:
        if f["download_url"] not in parser.links:
            raise ValueError("Captured metadata does not link both PDF parts")
        captured = next(e for e in captures if e["sha256"] == f["sha256"])
        refs.append({"artifact_ref": "mapping_snapshot/" + f["raw_file_ref"], "sha256": f["sha256"], "download_url": f["download_url"],
                     "source_accessed_at": captured["accessed_at"], "evidence_id": captured["evidence_id"]})
    def page(part, number):
        p = evroot / f"{part:02d}/page-{number:03d}.txt"
        return p.read_text(encoding="utf8")
    required = {(2, 1): ["36/2024/QH15", "TRẬT TỰ, AN TOÀN GIAO THÔNG ĐƯỜNG BỘ", "977 + 978/Ngày 24-8-2024"],
                (2, 10): ["\nChương II\nQUY TẮC GIAO THÔNG ĐƯỜNG BỘ"],
                (2, 19): ["Điều 22. Nhường đường tại nơi đường giao nhau", "Khi đến gần đường giao nhau", "1. Tại nơi", "2. Tại nơi", "3. Tại nơi"],
                (2, 20): ["Điều 23.", "Xem tiếp Công báo số 979 + 980"],
                (3, 1): ["36/2024/QH15 ngày 27 tháng 6 năm 2024", "Tiếp theo Công báo số 977 + 978", "Điều 24."],
                (3, 58): ["Điều 88. Hiệu lực thi hành", "ngày 01 tháng 01 năm 2025", "Khoản 3 Điều 10", "ngày 01 tháng 01 năm 2026", "Điều 89."],
                (3, 61): ["ngày 27 tháng 6 năm 2024", "Trần Thanh Mẫn"]}
    checks = []
    for (part, number), anchors in required.items():
        text = page(part, number)
        evidence = []
        for anchor in anchors:
            if anchor not in text:
                raise ValueError("Missing captured page anchor: " + anchor)
            start = text.index(anchor)
            evidence.append({"quote": anchor, "char_start": start, "char_end": start + len(anchor), "quote_sha256": digest(anchor.encode("utf8"))})
        p = evroot / f"{part:02d}/page-{number:03d}.txt"
        checks.append({"part": part, "page": number, "text_ref": "mapping_snapshot/" + p.relative_to(root).as_posix(),
                       "text_sha256": digest(p.read_bytes()), "offset_namespace": "captured_page_text", "checks": evidence, "result": "matched"})
    no_text = not page(2, 21).strip()
    if not no_text:
        raise ValueError("Expected recorded no-text page 21 differs")
    # Original mapping/issues remain unchanged, even when the agent sees a colophon.
    return {"origin": "agent_review", "human_review_claimed": False, "reviewer_event_created": False,
            "identity_result": "number_title_issuance_links_and_part_relation_match_within_inspected_evidence",
            "metadata": parser.values, "source_evidence": refs, "page_checks": checks,
            "selected_unit_ids": [u["unit_id"] for u in data["units"] if u["unit_type"] in {"article", "clause"}],
            "structural_only_unit_ids": [u["unit_id"] for u in data["units"] if u["unit_type"] in {"document", "chapter"}],
            "visual_review": visual, "page21": {"no_extracted_text": True, "agent_observation": "publishing colophon, not blank",
                                                "intersects_selected_spans": False, "issue_resolved": False, "ocr_performed": False},
            "applicability_analysis": {"candidate_effective_from": "2025-01-01", "basis": "Điều 88 khoản 1–2 và Điều 89, PDF phần tiếp 58–61",
                                       "result": "candidate_only_no_specific_Article22_exception_observed_in_reviewed_basis",
                                       "certainty": "limited_by_non_exhaustive_change_history_search", "decision": None},
            "limits": ["Agent review is not a reviewer decision under the current contract.",
                       "Only selected pages/fields inspected; whole files/extraction/tree not verified.",
                       "No exhaustive amendment/history search, signature validation or OCR.",
                       "Website metadata/capture date does not establish historical applicability."]}


def inspect_visual(path, mapping_root):
    visual = load_json(path)
    if (visual["origin"] != "agent_review" or visual["actor"] != "codex_agent" or visual["human_review_claimed"] is not False
            or visual["reviewer_event_created"] is not False or visual["mapping_manifest_sha256"] != digest((mapping_root / "manifest.json").read_bytes())):
        raise ValueError("Agent observation origin/binding mismatch")
    utc_time(visual["reviewed_at"])
    if [(r["part"], r["page"]) for r in visual["images"]] != list(PAGES):
        raise ValueError("Agent observation page coverage mismatch")
    for row in visual["images"]:
        image = resolve_ref(Path(path).parent, row["image_ref"])
        pdf = mapping_root / f"inputs/evidence/{row['part']:02d}/snapshot.pdf"
        if digest(image.read_bytes()) != row["image_sha256"] or digest(pdf.read_bytes()) != row["pdf_sha256"] or not row["observation"].strip():
            raise ValueError("Agent visual evidence/hash mismatch")
    return visual


def token_report(chunks, tokenizer_dir, cfg):
    texts = [c[k] for c in chunks for k in ["text_original", "context_text", "text_for_search"]]
    runtime = preview_tokens.count_tokens(texts, tokenizer_dir)
    counts = runtime.pop("counts")
    return {"model_id": cfg["tokenizer_model_id"], "revision": cfg["tokenizer_revision"],
            "asset_hashes": cfg["tokenizer_assets"], "runtime": runtime, "limit": cfg["token_limit"],
            "rows": [{"chunk_id": c["chunk_id"], "citation_path": c["citation_path"],
                      **{k: {**counts[3*i+j], "text_sha256": digest(c[k].encode("utf8"))} for j, k in enumerate(["text_original", "context_text", "text_for_search"])},
                      "within_limit": counts[3*i+2]["tokens_with_special"] <= cfg["token_limit"]} for i, c in enumerate(chunks)]}


def render_agent(review):
    lines = ["# Đối chiếu của agent — không phải quyết định reviewer", "", "origin=agent_review. Không ghi người dùng đã xem hoặc tạo human event.",
             "", "| Phần đối chiếu | Kết quả agent | Bằng chứng |", "|---|---|---|",
             "| Nhận diện nguồn | Số/tên luật, ngày 27-06-2024, hai PDF đính kèm khớp HTML capture | inputs/evidence/01, PDF phần đầu p1, phần tiếp p1/p61 |",
             "| Quan hệ hai phần | Cuối Điều 23 ghi xem tiếp 979+980; phần tiếp ghi tiếp theo 977+978 và mở Điều 24 | PDF phần đầu p20; phần tiếp p1 |",
             "| Nút cha | Root title/preamble và Chương II có nguồn; chỉ cấu trúc | PDF phần đầu p1/p10 |",
             "| Điều 22 | Title/đoạn dẫn/Khoản 1–3 khớp mapping; source slices/hash được kiểm | PDF phần đầu p19 + normalized.txt/trace/spans |",
             "| Warning p21 | Có thông tin xuất bản dạng nét; ngoài các spans đã chọn, chưa thấy ảnh hưởng trực tiếp đến Điều 22 | Ảnh p21; vẫn giữ warning, không OCR/resolve |",
             "| Căn cứ hiệu lực | Đề xuất 2025-01-01 từ Điều 88; ngoại lệ nêu A10K3; không thấy ngoại lệ riêng A22 trong Điều 89 đã xem | PDF phần tiếp p58–61; chưa tra cứu lịch sử toàn diện |", "",
             "Đã quan sát ảnh 10 trang được liệt kê dưới đây; không xác minh toàn văn/file hoặc nguồn legacy. Giữ nguyên pending và mọi blocker, không chuyển agent_review thành decision của reviewer.", ""]
    for r in review["visual_review"]["images"]:
        lines.append(f"- Phần {r['part']-1}, trang PDF {r['page']}: {r['observation']}")
    return "\n".join(lines) + "\n"


def render_chunks(chunks, contexts, tokens):
    lines = ["# Ba chunk/context PREVIEW — chưa xác minh, không phục vụ tìm kiếm", "",
             "Ba Khoản nguyên vẹn; context chung là title và đoạn dẫn Điều 22. Không tạo corpus/assessment, không inference/index.", ""]
    for c in sorted(chunks, key=lambda c: c["citation_path"]):
        t = next(t for t in tokens["rows"] if t["chunk_id"] == c["chunk_id"])
        lines += ["## " + c["citation_path"], "", "Chunk ID: `" + c["chunk_id"] + "`", "",
                  "Nguyên văn mục tiêu:", "```text", c["text_original"], "```", "",
                  "Context (title + LF + đoạn dẫn, lấy nguyên field cha):", "```text", c["context_text"], "```", "",
                  "text_for_search (các khối nối hai LF):", "```text", c["text_for_search"], "```", "",
                  f"Token có special tokens: target {t['text_original']['tokens_with_special']}; context {t['context_text']['tokens_with_special']}; toàn text_for_search {t['text_for_search']['tokens_with_special']}/{tokens['limit']}. Không truncation. Đạt ngưỡng preview: {t['within_limit']}.", "",
                  "Nguồn mục tiêu: " + c["source_locator"], ""]
        for x in [x for x in contexts if x["chunk_id"] == c["chunk_id"]]:
            lines.append(f"Context {x['context_order']}: field={x['field_name']}, unit offsets [{x['char_start']},{x['char_end']}), spans: {x['source_locator']}")
        lines += ["", "Trạng thái: pending_review; effective_from/to=null; corpus_version=null; release_eligible=false.", ""]
    return "\n".join(lines)


def require_preview_schema(chunks):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = load_json(BASE_DIR / "schemas/chunk_preview_v1/preview.schema.json")
    for c in chunks:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(c)


def replay(run):
    config = load_json(run / "config.json")
    require_config(config)
    mapping_root = run / "mapping_snapshot"
    result = validate_mapping(mapping_root / "manifest.json")
    if not result["technical_valid"]:
        raise ValueError("Invalid mapping input: " + canonical(result))
    blockers = load_json(mapping_root / "manifest.json")["blockers"] + EXTRA_BLOCKERS
    data = mapping_data(mapping_root)
    visual = inspect_visual(run / "agent_inspection/observations.json", mapping_root)
    chunks, contexts = make_chunks(data, mapping_root, config, blockers)
    require_preview_schema(chunks)
    review = agent_findings(mapping_root, data, visual)
    if preview_tokens.inspect_assets(run / "tokenizer_assets") != config["tokenizer_assets"]:
        raise ValueError("Tokenizer asset binding mismatch")
    tokens = token_report(chunks, run / "tokenizer_assets", config)
    return chunks, contexts, review, tokens


def validate(manifest_path):
    path = Path(manifest_path).resolve()
    if path.name != "manifest.json":
        raise ValueError("Expected manifest.json")
    m = check_files(path)
    run = path.parent
    if (m["manifest_type"] != VERSION or m["code_sha256"] != code_binding() or m["files"] != inventory(run)
            or m["snapshot_date"] != SNAPSHOT_DATE or m["preview_only"] is not True or m["release_eligible"] is not False
            or m["corpus_version"] is not None or m["human_reviewer_event_count"] != 0
            or m["mapping_manifest_sha256"] != digest((run / "mapping_snapshot/manifest.json").read_bytes())
            or m["config_sha256"] != hash_json(load_json(run / "config.json"))):
        raise ValueError("Preview manifest binding/pending/origin mismatch")
    chunks, contexts, review, tokens = replay(run)
    for f, expected in [("chunks.preview.jsonl", chunks), ("contexts.preview.jsonl", contexts)]:
        if read_rows(run / f) != expected:
            raise ValueError("Preview replay mismatch: " + f)
    if (load_json(run / "agent_review.json") != review or load_json(run / "token_report.json") != tokens
            or (run / "agent_review.md").read_text(encoding="utf8") != render_agent(review)
            or (run / "chunks_preview.md").read_text(encoding="utf8") != render_chunks(chunks, contexts, tokens)):
        raise ValueError("Agent review/token/report replay mismatch")
    report = validation_report(chunks, contexts, tokens)
    if load_json(run / "validation_report.json") != report:
        raise ValueError("Stored validation report mismatch")
    return report


def validation_report(chunks, contexts, tokens):
    passed = all(r["within_limit"] for r in tokens["rows"])
    return {"technical_valid": True, "processing_success": passed, "errors": [], "chunk_count": len(chunks), "context_count": len(contexts),
            "snapshot_date": SNAPSHOT_DATE, "token_limit_passed": passed, "token_limit": tokens["limit"],
            "origin": "agent_review", "human_reviewer_event_count": 0, "corpus_created": False,
            "source_status": "pending", "extraction_status": "pending", "applicability_status": "pending_review",
            "release_eligible": False, "release_blockers": chunks[0]["release_blockers"], "preview_only": True}


def build(mapping_manifest, visual_path, run_dir, tokenizer_dir=None, config_path=DEFAULT_CONFIG):
    target = staging_path(run_dir)
    source = Path(mapping_manifest).resolve().parent
    if source in target.parents or Path(visual_path).resolve().parent in target.parents:
        raise ValueError("Output must not be nested inside existing evidence")
    config = load_json(config_path)
    require_config(config)
    tokenizer_dir = Path(tokenizer_dir or preview_tokens.default_tokenizer_dir())
    if preview_tokens.inspect_assets(tokenizer_dir) != config["tokenizer_assets"]:
        raise ValueError("Tokenizer files do not match pinned model revision")
    validated = validate_mapping(mapping_manifest)
    if not validated["technical_valid"]:
        raise ValueError("Mapping bundle invalid: " + canonical(validated))
    visual = inspect_visual(visual_path, source)
    with staged_run(run_dir, VERSION, mapping_manifest) as (run, run_report):
        shutil.copytree(source, run / "mapping_snapshot")
        (run / "agent_inspection").mkdir()
        shutil.copyfile(visual_path, run / "agent_inspection/observations.json")
        for row in visual["images"]:
            dest = resolve_ref(run / "agent_inspection", row["image_ref"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolve_ref(Path(visual_path).parent, row["image_ref"]), dest)
        (run / "tokenizer_assets").mkdir()
        for name in preview_tokens.ASSETS:
            shutil.copyfile(tokenizer_dir / name, run / "tokenizer_assets" / name)
        write_json(run / "config.json", config)
        chunks, contexts, review, tokens = replay(run)
        write_rows(run / "chunks.preview.jsonl", chunks)
        write_rows(run / "contexts.preview.jsonl", contexts)
        write_json(run / "agent_review.json", review)
        write_json(run / "token_report.json", tokens)
        (run / "agent_review.md").write_text(render_agent(review), encoding="utf8", newline="\n")
        (run / "chunks_preview.md").write_text(render_chunks(chunks, contexts, tokens), encoding="utf8", newline="\n")
        report = validation_report(chunks, contexts, tokens)
        write_json(run / "validation_report.json", report)
        seal(run, {"manifest_type": VERSION, "built_at": now(), "snapshot_date": SNAPSHOT_DATE,
                   "mapping_manifest_sha256": digest(Path(mapping_manifest).read_bytes()), "config_sha256": hash_json(config),
                   "code_sha256": code_binding(), "preview_only": True, "corpus_version": None,
                   "human_reviewer_event_count": 0, "release_eligible": False})
        run_report.update(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pending Article22 chunk/context PREVIEW and agent-only review")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("build")
    create.add_argument("--mapping-manifest", type=Path, required=True)
    create.add_argument("--agent-review", type=Path, required=True)
    create.add_argument("--run-dir", type=Path, required=True)
    create.add_argument("--tokenizer-dir", type=Path)
    create.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    check = commands.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build(args.mapping_manifest, args.agent_review, args.run_dir, args.tokenizer_dir, args.config) if args.command == "build" else validate(args.manifest)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["processing_success"] else 2
    except Exception as exc:
        print(json.dumps({"technical_valid": False, "errors": [str(exc)], "release_eligible": False}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
