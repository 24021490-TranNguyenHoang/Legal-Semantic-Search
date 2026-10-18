"""Article22 CLI example calling the reusable builder and shared encoder input.

The v1 CLI is intentionally immutable: its byte hash seals preview-001.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

from src import chunk_preview, encoder_input
from src.article22_preview import validate as validate_baseline, mapping_data, require_preview_schema
from src.assessment_evidence import check_files, inventory, now, seal
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.pipeline_cli import staged_run, staging_path, write_json
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows

VERSION = "article22-stage6-preview.v1"
DEFAULT_CONFIG = BASE_DIR / "config/stage6_preview.v1.json"


def code_binding():
    return {name: digest(p.read_bytes()) for name, p in {
        "cli": Path(__file__), "builder": Path(chunk_preview.__file__), "encoder_input": Path(encoder_input.__file__),
        "preview_schema": BASE_DIR / "schemas/chunk_preview_v1/preview.schema.json"}.items()}


def check_inputs(baseline, config, evidence):
    manifest = baseline / "manifest.json"
    if (config["artifact_version"] != VERSION or config["baseline_manifest_sha256"] != digest(manifest.read_bytes())
            or config["chunk"]["snapshot_date"] != SNAPSHOT_DATE):
        raise ValueError("Stage6 baseline/config/snapshot binding mismatch")
    chunks = read_rows(baseline / "chunks.preview.jsonl")
    if set(config["chunk"]["target_unit_ids"]) != {c["unit_id"] for c in chunks} or len(chunks) != 3:
        raise ValueError("Narrow CLI may not expand the existing three targets")
    if config["chunk"]["required_context_fields"] != ["title", "text_original"]:
        raise ValueError("Article22 example still requires its actual title and lead")
    encoder_input.require_config(config["encoder"], baseline / "tokenizer_assets")
    captures = load_json(evidence / "captures.json")
    expected = {"model_card.md", "sentence_bert_config.json", "phobert_docs.html", "pyvi_readme.rst"}
    if {r["file"] for r in captures} != expected:
        raise ValueError("Incomplete model/tokenizer documentation evidence")
    for r in captures:
        if "error" in r or not r["accessed_at"].endswith("Z") or digest(resolve_ref(evidence, r["file"]).read_bytes()) != r["sha256"]:
            raise ValueError("Model evidence hash/capture mismatch")
    limits = load_json(evidence / "sentence_bert_config.json")
    card = next(r for r in captures if r["file"] == "model_card.md")
    if (config["encoder"]["model_revision"] not in card["url"] or limits != {"max_seq_length": 256, "do_lower_case": False}
            or config["encoder"]["sentence_bert_config_sha256"] != digest((evidence / "sentence_bert_config.json").read_bytes())):
        raise ValueError("Pinned model card/sequence configuration mismatch")
    agent = load_json(baseline / "agent_review.json")
    if agent["origin"] != "agent_review" or agent["human_review_claimed"] is not False or agent["reviewer_event_created"] is not False:
        raise ValueError("Agent observation must not become reviewer event")


def locate_unknowns(chunk, contexts, units, row):
    components = chunk_preview.search_components(chunk)
    for unknown in row["before"]["unknowns"]:
        proof = unknown["source"]
        unknown["component"] = None
        unknown["offset_namespace"] = "text_for_search"
        if proof is None:
            continue
        a, b = proof["char_start"], proof["char_end"]
        if chunk["text_for_search"][a:b] != proof["source_fragment"]:
            raise ValueError("Unknown diagnostic character proof mismatch")
        part = next((x for x in components if x["char_start"] <= a and b <= x["char_end"]), None)
        if part:
            unknown["component"] = part["component"]
            unknown["component_range"] = part
            unknown["relative_char_start"] = a-part["char_start"]
            unknown["relative_char_end"] = b-part["char_start"]
            if part["component"] == "context_text":
                offset = part["char_start"]
                for c in contexts:
                    if c["chunk_id"] != chunk["chunk_id"]:
                        continue
                    if offset <= a and b <= offset+c["char_end"]-c["char_start"]:
                        unknown["context_field"] = c["field_name"]
                        unknown["context_unit_id"] = c["unit_id"]
                        unknown["unit_field_char_start"] = a-offset+c["char_start"]
                        unknown["unit_field_char_end"] = b-offset+c["char_start"]
                        break
                    offset += c["char_end"]-c["char_start"]+1
        unknown["snippet"] = chunk["text_for_search"][max(0,a-20):min(len(chunk["text_for_search"]),b+20)]
    # No invented inverse offsets from segmented encoder input to legal fields.
    for unknown in row["after"]["unknowns"]:
        unknown.update(component=None, offset_namespace="encoder_input", legal_source_mapping=None)
    row["search_components"] = components


def calculate(run):
    baseline = run / "baseline_snapshot"
    config = load_json(run / "config.json")
    check_inputs(baseline, config, run / "model_evidence")
    valid = validate_baseline(baseline / "manifest.json")
    if not valid["technical_valid"]:
        raise ValueError("Invalid baseline preview")
    root = baseline / "mapping_snapshot"
    data = mapping_data(root)
    runtime = {}

    def encode(texts):
        measured = encoder_input.encode_inputs(texts, config["encoder"], baseline / "tokenizer_assets")
        runtime.update({k: v for k, v in measured.items() if k != "rows"})
        return measured["rows"]

    old = read_rows(baseline / "chunks.preview.jsonl")
    blockers = old[0]["release_blockers"]
    result = chunk_preview.build_chunks(data, root, config["chunk"], blockers, encode,
                                        reference_prefix="baseline_snapshot/mapping_snapshot/")
    require_preview_schema(result["chunks"])
    old_contexts = read_rows(baseline / "contexts.preview.jsonl")
    old_tokens = load_json(baseline / "token_report.json")["rows"]
    comparisons = []
    candidates = result["chunks"] + [q["candidate"] for q in result["quarantined"]]
    all_contexts = result["contexts"] + [c for q in result["quarantined"] for c in q["contexts"]]
    for c in candidates:
        prior = next(x for x in old if x["unit_id"] == c["unit_id"])
        before = chunk_preview.chunk_identity(prior, [x for x in old_contexts if x["chunk_id"] == prior["chunk_id"]])
        after = chunk_preview.chunk_identity(c, [x for x in all_contexts if x["chunk_id"] == c["chunk_id"]])
        row = next(r for r in result["encoder_inputs"] if r["chunk_id"] == c["chunk_id"])
        token = next(t for t in old_tokens if t["chunk_id"] == prior["chunk_id"])["text_for_search"]
        if any(row["before"][k] != token[k] for k in ["tokens_with_special", "unknown_tokens", "token_ids_sha256"]):
            raise ValueError("Baseline tokenizer replay differs; do not infer unknown causes from a different tokenizer")
        locate_unknowns(c, all_contexts, data["units"], row)
        comparisons.append({"unit_id": c["unit_id"], "chunk_id_before": prior["chunk_id"], "chunk_id_after": c["chunk_id"],
                            "identity_payload_equal": before == after, "changed_identity_fields": [k for k in before if before[k] != after[k]],
                            "content_hash_equal": prior["content_sha256"] == c["content_sha256"],
                            "original_equal": prior["text_original"] == c["text_original"], "context_equal": prior["context_text"] == c["context_text"]})
    report = {"technical_valid": True, "processing_success": not result["issues"] and len(result["chunks"]) == 3,
              "chunk_count": len(result["chunks"]), "context_count": len(result["contexts"]), "issue_count": len(result["issues"]),
              "snapshot_date": SNAPSHOT_DATE, "origin": "agent_review", "human_reviewer_event_count": 0,
              "source_status": "pending", "extraction_status": "pending", "applicability_status": "pending_review",
              "release_eligible": False, "corpus_created": False, "preview_only": True, "release_blockers": blockers,
              "identity_payloads_equal": all(r["identity_payload_equal"] for r in comparisons),
              "preprocessing_version": encoder_input.VERSION, "truncation": False, "inference_loaded": False}
    return result, runtime, comparisons, report


def render(result, report):
    lines = ["# Ba chunk/context PREVIEW Stage 6", "", "origin=agent_review; pending; không phải quyết định reviewer hoặc corpus phục vụ.",
             "", "| Khoản | Token trước | Unknown trước | Token sau | Unknown sau | Ngưỡng |", "|---|---:|---:|---:|---:|---:|"]
    for c in sorted(result["chunks"], key=lambda c: c["citation_path"]):
        r = next(r for r in result["encoder_inputs"] if r["chunk_id"] == c["chunk_id"])
        lines.append(f"| {c['citation_path']} | {r['before']['tokens_with_special']} | {r['before']['unknown_tokens']} | {r['tokens_with_special']} | {r['unknown_tokens']} | 256 |")
    for c in sorted(result["chunks"], key=lambda c: c["citation_path"]):
        r = next(r for r in result["encoder_inputs"] if r["chunk_id"] == c["chunk_id"])
        lines += ["", "## " + c["citation_path"], "", "ID: `"+c["chunk_id"]+"`", ""]
        for label, text in [("Nguyên văn", c["text_original"]), ("Context có nguồn", c["context_text"]),
                            ("text_for_search — content hash DDD", c["text_for_search"]), ("Đầu vào encoder — bản sao đã tiền xử lý", r["encoder_text"])]:
            lines += [label, "```text", text or "", "```", ""]
        lines += ["Nguồn target: " + c["source_locator"], "", "Context: xem contexts.preview.jsonl (field offsets) và source_locator (extraction offsets).", ""]
    lines += ["## Phần bị chặn", "", canonical(result["issues"]), "", "Giữ toàn bộ blocker từ preview-001. Không truncate, không tạo assessment/corpus/index hoặc ghi reviewer event.", ""]
    return "\n".join(lines)


def render_unknowns(result, runtime, config):
    lines = ["# Chẩn đoán unknown token — agent_review", "", "Model: `"+config["encoder"]["model_id"]+"`, revision `"+config["encoder"]["model_revision"]+"`.",
             "", "Native offset mapping: không hỗ trợ. Vị trí token tính từ 0, gồm BOS/EOS. Chỉ ghi ký tự khi regex/BPE dựng lại khớp hoàn toàn chuỗi tokens/IDs và literal nguồn. JSONL giữ đầy đủ token IDs/pieces.",
             "", "Nguồn offsets bảng dưới là text_for_search; không phải extraction offsets. Separator là ký tự ghép do thiết kế, không gán giả vào field nguồn.",
             "", "| Chunk | Token pos | BPE piece | Component | Source [start,end) | Đoạn lân cận (escaped) |", "|---|---:|---|---|---|---|"]
    for r in result["encoder_inputs"]:
        for u in r["before"]["unknowns"]:
            s = u["source"]
            where = f"[{s['char_start']},{s['char_end']})" if s else "không xác định"
            fragment = json.dumps(u.get("snippet"), ensure_ascii=False).replace("|", "\\|")
            component = u["component"] or "chưa xác định"
            if "context_field" in u:
                component += "."+u["context_field"]
            lines.append(f"| {r['chunk_id']} | {u['token_position']} | {json.dumps(u['token_piece'])} | {component} | {where} | {fragment} |")
    lines += ["", "## Đối chứng", "", "| Chunk | Trước: token/unknown | Chỉ gom whitespace: token/unknown | Sau PyVi: token/unknown | Special |", "|---|---|---|---|---|"]
    for r in result["encoder_inputs"]:
        pair = lambda d: f"{d['tokens_with_special']}/{d['unknown_tokens']}"
        lines.append(f"| {r['chunk_id']} | {pair(r['before'])} | {pair(r['whitespace_only'])} | {pair(r['after'])} | {r['after']['special_token_count']} |")
    lines += ["", "Unknown trước trên ba chunk là LF được regex PhoBERT giữ lại nhưng không có trong vocabulary; phép chỉ gom whitespace đưa unknown về 0. Không có bằng chứng lỗi encoding. PyVi là bước bổ sung theo yêu cầu model card, không phải bằng chứng rằng thiếu segmentation gây các unknown LF này.",
              "", "Sau segmentation, offsets trên encoder_text không tự ánh xạ ngược về extraction. Nguyên văn/context/spans/search giữ nguyên. Phân tích này không chứng minh chất lượng retrieval hoặc xác minh pháp lý.",
              "", "Runtime và cấu hình đầy đủ: runtime.json/config.json; model card đúng revision, sentence_bert_config và tài liệu PhoBERT/PyVi trong model_evidence/ cùng URL/hash/thời điểm capture thực.", "", canonical(runtime), ""]
    return "\n".join(lines)


EXPORTS = {"chunks.preview.jsonl": "chunks", "contexts.preview.jsonl": "contexts", "encoder_inputs.preview.jsonl": "encoder_inputs",
           "issues.jsonl": "issues", "quarantined.preview.jsonl": "quarantined", "unit_results.jsonl": "unit_results"}


def validate(manifest_path):
    p = Path(manifest_path).resolve()
    if p.name != "manifest.json":
        raise ValueError("Expected manifest.json")
    m = check_files(p)
    run = p.parent
    if (m["manifest_type"] != VERSION or m["code_sha256"] != code_binding() or m["files"] != inventory(run)
            or m["baseline_manifest_sha256"] != digest((run/"baseline_snapshot/manifest.json").read_bytes())
            or m["config_sha256"] != digest((run/"config.json").read_bytes()) or m["snapshot_date"] != SNAPSHOT_DATE
            or m["origin"] != "agent_review" or m["human_reviewer_event_count"] != 0
            or m["release_eligible"] is not False or m["preview_only"] is not True or m["corpus_version"] is not None):
        raise ValueError("Stage6 manifest/version/pending/hash mismatch")
    result, runtime, comparisons, report = calculate(run)
    for filename, key in EXPORTS.items():
        if read_rows(run/filename) != result[key]:
            raise ValueError("Stage6 replay mismatch: " + filename)
    for filename, expected in [("runtime.json", runtime), ("comparison.json", comparisons), ("validation_report.json", report)]:
        if load_json(run/filename) != expected:
            raise ValueError("Stage6 replay mismatch: " + filename)
    if ((run/"chunks_preview.md").read_text(encoding="utf8") != render(result, report)
            or (run/"unknown_diagnostics.md").read_text(encoding="utf8") != render_unknowns(result, runtime, load_json(run/"config.json"))):
        raise ValueError("Readable report differs from replay")
    return report


def build(baseline_manifest, evidence_dir, run_dir, config_path=DEFAULT_CONFIG):
    target = staging_path(run_dir)
    baseline = Path(baseline_manifest).resolve().parent
    evidence = Path(evidence_dir).resolve()
    if baseline in target.parents or evidence in target.parents:
        raise ValueError("Output must not be nested inside existing bundle")
    config = load_json(config_path)
    check_inputs(baseline, config, evidence)
    if not validate_baseline(baseline_manifest)["technical_valid"]:
        raise ValueError("Invalid baseline")
    with staged_run(run_dir, VERSION, baseline_manifest) as (run, run_report):
        shutil.copytree(baseline, run/"baseline_snapshot")
        shutil.copytree(evidence, run/"model_evidence")
        write_json(run/"config.json", config)
        result, runtime, comparisons, report = calculate(run)
        for filename, key in EXPORTS.items():
            write_rows(run/filename, result[key])
        write_json(run/"runtime.json", runtime)
        write_json(run/"comparison.json", comparisons)
        write_json(run/"validation_report.json", report)
        (run/"chunks_preview.md").write_text(render(result, report), encoding="utf8", newline="\n")
        (run/"unknown_diagnostics.md").write_text(render_unknowns(result, runtime, config), encoding="utf8", newline="\n")
        seal(run, {"manifest_type": VERSION, "built_at": now(), "snapshot_date": SNAPSHOT_DATE,
                   "baseline_manifest_sha256": digest(Path(baseline_manifest).read_bytes()), "config_sha256": digest((run/"config.json").read_bytes()),
                   "code_sha256": code_binding(), "origin": "agent_review", "human_reviewer_event_count": 0,
                   "preview_only": True, "corpus_version": None, "release_eligible": False})
        run_report.update(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Article22 Stage6 example: reusable pending chunk/context + encoder input")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("build")
    create.add_argument("--baseline-manifest", type=Path, required=True)
    create.add_argument("--model-evidence", type=Path, required=True)
    create.add_argument("--run-dir", type=Path, required=True)
    create.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    check = sub.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build(args.baseline_manifest, args.model_evidence, args.run_dir, args.config) if args.command == "build" else validate(args.manifest)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["processing_success"] else 2
    except Exception as exc:
        print(json.dumps({"technical_valid": False, "errors": [str(exc)], "release_eligible": False}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
