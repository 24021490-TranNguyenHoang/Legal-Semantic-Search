"""Package an experimental pilot, without legal approval or retrieval indexes.

The validation path uses only Python's standard library and existing contract
helpers copied into runtime/. Build alone imports the upstream pipeline.
"""
import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys

from src.config import SNAPSHOT_DATE, BASE_DIR
from src.source_contracts import canonical, digest, resolve_ref
from src.chunk_preview import chunk_identity, search_components
from src.chunk_preview_v2 import build_chunks

VERSION = "experimental-pilot-packaging.v1"
DEFAULT_CONFIG = BASE_DIR / "config/experimental_dataset.v1.json"
RUNTIME = ["src/config.py", "src/source_contracts.py", "src/chunk_preview.py",
           "src/chunk_preview_v2.py", "src/ingestion/legal_tree.py"]
CONTROL = {"dataset_manifest.json", "dataset_manifest.sha256", "execution.json"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf8").splitlines() if line.strip()]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")


def write_rows(path, value):
    Path(path).write_text("".join(canonical(r) + "\n" for r in value), encoding="utf8", newline="\n")


def unique(values, key):
    by = {v[key]: v for v in values}
    if len(by) != len(values):
        raise ValueError("Duplicate " + key)
    return by


def inventory(root):
    return [{"path": p.relative_to(root).as_posix(), "size_bytes": p.stat().st_size,
             "sha256": digest(p.read_bytes())} for p in sorted(root.rglob("*"),key=lambda p:p.relative_to(root).as_posix())
            if p.is_file() and p.relative_to(root).as_posix() not in CONTROL]


def csv_text(values, keys):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=keys, lineterminator="\n")
    writer.writeheader()
    for r in values:
        writer.writerow({k: canonical(r[k]) if isinstance(r[k], (list, dict)) else r[k] for k in keys})
    return out.getvalue()


def require_policy(cfg):
    expected = {"policy_version": VERSION, "snapshot_date": SNAPSHOT_DATE, "experimental": True,
                "required_scope_proposal": "included", "required_chunk_capability": "preview_available",
                "required_context_selection": "all_fields_proposed_for_use",
                "negative_applicability": "explicit_unit_date_rule_with_bound_text_slice",
                "unknown_token_policy": "retain_diagnostic_do_not_exclude", "corpus_version": None,
                "release_eligible": False}
    if (any(k not in cfg or type(cfg[k]) is not type(v) or cfg[k] != v for k,v in expected.items())
            or not isinstance(cfg.get("dataset_version"),str) or not cfg["dataset_version"].strip()
            or cfg["dataset_version"] != cfg["dataset_version"].strip()):
        raise ValueError("Invalid experimental packaging policy")


def evidence_checks(root):
    catalog = unique(rows(root / "evidence/catalog.jsonl"), "evidence_id")
    findings = unique(rows(root / "evidence/findings.pending.jsonl"), "finding_id")
    for e in catalog.values():
        p = resolve_ref(root, e["artifact_ref"])
        if digest(p.read_bytes()) != e["sha256"] or p.stat().st_size != e["size_bytes"]:
            raise ValueError("Evidence capture hash/size mismatch")
    for f in findings.values():
        if f["finding_id"] != "find_"+digest(canonical({k:v for k,v in f.items() if k!="finding_id"}).encode()):
            raise ValueError("Finding identity mismatch")
        e = catalog[f["evidence_id"]]
        if e["sha256"] != f["evidence_sha256"] or e["law_id"] != f["law_id"] or e["accessed_at"] != f["accessed_at"]:
            raise ValueError("Finding/capture binding mismatch")
        if f["kind"] == "text_slice":
            text = resolve_ref(root / "evidence/pages", f["text_ref"]).read_text(encoding="utf8")
            if (digest(text.encode()) != f["text_sha256"] or not 0 <= f["char_start"] < f["char_end"] <= len(text)
                    or text[f["char_start"]:f["char_end"]] != f["quote"]
                    or digest(f["quote"].encode()) != f["quote_sha256"]):
                raise ValueError("Finding quote/offset/hash mismatch")
        elif f["kind"] != "visual_observation":
            raise ValueError("Unsupported evidence finding")
    rules = rows(root / "evidence/date_rules.pending.jsonl")
    unique(rules, "rule_id")
    for r in rules:
        if r["rule_id"] != "rule_"+digest(canonical({k:v for k,v in r.items() if k!="rule_id"}).encode()):
            raise ValueError("Date rule identity mismatch")
        f = findings[r["finding_id"]]
        if r["rule_kind"] != "machine_candidate_not_legal_verification" or r["review_status"] != "pending" or f["evidence_id"] not in r["evidence_ids"]:
            raise ValueError("Date rule missing pending evidence binding")
        start = date.fromisoformat(r["effective_from"]) if r["effective_from"] else None
        end = date.fromisoformat(r["effective_to"]) if r["effective_to"] else None
        if (start and start.isoformat()!=r["effective_from"] or end and end.isoformat()!=r["effective_to"]
                or type(r["priority"]) is not int):
            raise ValueError("Date rules require canonical dates and integer priority")
        if start and end and start >= end:
            raise ValueError("Invalid evidence date interval")
    return rules, findings


def negative_applicability(ids, rules, findings, snapshot):
    """Use explicit unit rules only. A past general date never declares active."""
    results = []
    for uid in sorted(ids):
        own = [r for r in rules if uid in r["unit_ids"]]
        if not own:
            continue
        best = max(r["priority"] for r in own)
        chosen = [r for r in own if r["priority"] == best]
        if len({(r["effective_from"], r["effective_to"]) for r in chosen}) > 1:
            results.append({"unit_id": uid, "reason": "APPLICABILITY_EVIDENCE_CONFLICT",
                            "rule_ids": sorted(r["rule_id"] for r in chosen)})
            continue
        for r in chosen:
            f = findings[r["finding_id"]]
            # Visual observations without a source transcription remain pending.
            if f["kind"] != "text_slice":
                continue
            outside = (r["effective_from"] and snapshot < r["effective_from"]
                       or r["effective_to"] and snapshot >= r["effective_to"])
            if outside:
                results.append({"unit_id": uid, "reason": "OUTSIDE_SNAPSHOT_BY_EXPLICIT_EVIDENCE",
                                "rule_id": r["rule_id"], "finding_id": f["finding_id"],
                                "evidence_id": f["evidence_id"], "evidence_page": f["page"],
                                "quote": f["quote"], "finding_review_status": f["review_status"],
                                "origin": "agent_review", "reviewer_decision": None})
    return results


def select(candidates, rules, findings, dependency_checks):
    selected, deferred = [], []
    for p in sorted(candidates, key=lambda p: p["unit_id"]):
        reasons = []
        if p["scope_proposal"] != "included": reasons.append("SCOPE_PROPOSAL_PENDING")
        if p["chunk_capability"] != "preview_available": reasons.append("CHUNK_" + p["chunk_capability"].upper())
        if p["context_selection_proposal"] != "all_fields_proposed_for_use": reasons.append("CONTEXT_SELECTION_NEEDS_REVIEW")
        if dependency_checks[p["unit_id"]]["impacts"]: reasons.append("TECHNICAL_DEPENDENCY_BLOCK")
        used = {p["unit_id"]} | {d["unit_id"] for d in p["context_dependencies"]}
        negative = negative_applicability(used, rules, findings, SNAPSHOT_DATE)
        reasons += sorted({n["reason"] for n in negative})
        if reasons:
            deferred.append({"unit_id": p["unit_id"], "chunk_id": p["chunk_id"], "citation_path": p["citation_path"],
                             "scope_proposal": p["scope_proposal"], "reasons": reasons, "evidence": negative,
                             "tokens_with_special": p["tokens_with_special"], "release_eligible": False})
        else:
            selected.append(p)
    return selected, deferred


def replay(root):
    """Rebuild only existing 107 candidates using existing, verified token evidence."""
    laws = load(root / "support/laws.json")
    candidates = rows(root / "support/pilot.jsonl")
    unique(candidates, "unit_id")
    chunks = unique(rows(root / "support/chunks.upstream.jsonl"), "unit_id")
    contexts = rows(root / "support/contexts.upstream.jsonl")
    encoder = unique(rows(root / "support/encoder_inputs.jsonl"), "unit_id")
    ids = {p["unit_id"] for p in candidates}
    if set(chunks) != ids or set(encoder) != ids:
        raise ValueError("Candidate/chunk/encoder join mismatch")
    cfg = load(root / "chunk_config.json")
    enc_cfg = load(root / "encoder_config.json")
    if cfg["token_limit"] != 256 or cfg["chunk_policy_version"] != "leaf-clause-point-context.v1":
        raise ValueError("Existing preview policy/budget must remain unchanged")
    lookup = {e["input_sha256"]: e for e in encoder.values()}
    checks = {}
    for data in laws.values():
        own = sorted(ids & {u["unit_id"] for u in data["units"]})
        if not own:
            raise ValueError("Unused structural law snapshot")
        result = build_chunks(data, root / "inputs", {**cfg, "target_unit_ids": own},
                              load(root / "support/release_blockers.json"),
                              lambda texts: [lookup[digest(t.encode())] for t in texts], reference_prefix="inputs/")
        rebuilt = result["chunks"] + [q["candidate"] for q in result["quarantined"]]
        ctx = result["contexts"] + [c for q in result["quarantined"] for c in q["contexts"]]
        if {c["unit_id"] for c in rebuilt} != set(own):
            raise ValueError("Builder lost candidate or source/dependency invalid")
        for c in rebuilt:
            if c != chunks[c["unit_id"]]: raise ValueError("Original chunk ID/content/proof changed")
        expected = sorted([c for c in contexts if c["chunk_id"] in {chunks[u]["chunk_id"] for u in own}], key=lambda c:(c["chunk_id"], c["context_order"]))
        if sorted(ctx, key=lambda c:(c["chunk_id"], c["context_order"])) != expected:
            raise ValueError("Context FK/order/source/content mismatch")
        for q in result["dependency_checks"]: checks[q["unit_id"]] = q
    if set(checks) != ids or len(contexts) != len({(c["chunk_id"], c["context_order"]) for c in contexts}):
        raise ValueError("Duplicate context or missing dependency check")
    units = {u["unit_id"]:u for d in laws.values() for u in d["units"]}
    history=unique(rows(root/"support/scope_history.jsonl"),"unit_id")
    if set(history)!=ids:raise ValueError("Scope history lost or expanded pilot")
    field_reviews = unique(rows(root / "support/field_reviews.jsonl"), "field_review_id")
    for p in candidates:
        u, c, e = units[p["unit_id"]], chunks[p["unit_id"]], encoder[p["unit_id"]]
        h=history[p["unit_id"]]
        if (h["proposal_id"]!=p["proposal_id"] or h["unit_sha256"]!=p["unit_sha256"] or h["scope_candidate"]!=p["scope_proposal"]
                or h["reviewer_ref"] is not None or h["reviewed_at"] is not None or h["origin"]!="agent_review"):
            raise ValueError("Scope proposal/history binding mismatch")
        if (digest(canonical(u).encode()) != p["unit_sha256"] or p["chunk_id"] != c["chunk_id"]
                or p["content_sha256"] != c["content_sha256"] or p["text_original"] != c["text_original"]
                or p["tokens_with_special"] != e["tokens_with_special"] or p["unknown_tokens"] != e["unknown_tokens"]):
            raise ValueError("Pilot unit/hash/chunk/token binding mismatch")
        actual_capability = "preview_available" if e["tokens_with_special"] <= min(cfg["token_limit"],e["model_max_tokens"]) else "over_token_budget"
        if p["chunk_capability"] != actual_capability or e["model_max_tokens"] != enc_cfg["model_max_tokens"] or e["preprocessing_version"] != enc_cfg["preprocessing_version"]:
            raise ValueError("Pilot encoder/budget capability mismatch")
        used = sorted([x for x in contexts if x["chunk_id"] == c["chunk_id"]], key=lambda x:x["context_order"])
        if len(used) != len(p["context_dependencies"]): raise ValueError("Missing pilot dependency")
        proposals = []
        for context, dep in zip(used, p["context_dependencies"]):
            keys = ["unit_id", "field_name", "char_start", "char_end", "context_order", "context_role", "source_locator"]
            if any(context[k] != dep[k] for k in keys): raise ValueError("Pilot context evidence/field mismatch")
            if dep["scope_dependency_pending"]:
                matching = [f for f in field_reviews.values() if f["target_unit_id"] == p["unit_id"] and all(f[k] == dep[k] for k in keys)]
                if len(matching) != 1: raise ValueError("Missing target-specific field proposal")
                f = matching[0];parent = units[f["unit_id"]]
                if (f["parent_verified"] is not False or f["field_text"] != parent[f["field_name"]][f["char_start"]:f["char_end"]]
                        or f["field_sha256"] != digest(f["field_text"].encode())): raise ValueError("Field binding/verified mismatch")
                proposals.append(f["selection_proposal"])
        state = "needs_more_review" if any(x != "use" for x in proposals) else "all_fields_proposed_for_use"
        if p["context_selection_proposal"] != state: raise ValueError("Context selection mismatch")
        for record in [c] + used:
            if record["corpus_version"] is not None or record["release_eligible"] is not False or record["preview_only"] is not True:
                raise ValueError("Preview cannot claim corpus/release")
        if c["effective_from"] is not None or c["effective_to"] is not None or c["applicability_status"] != "pending_review":
            raise ValueError("Invented applicability metadata")
        if p["reviewer_ref"] is not None or p["reviewed_at"] is not None or p["origin"] != "agent_review":
            raise ValueError("Invented reviewer")
        search_components(c)
        if "c_" + digest(canonical(chunk_identity(c, used)).encode()) != c["chunk_id"] or digest(c["text_for_search"].encode()) != c["content_sha256"]:
            raise ValueError("DDD chunk identity/search hash mismatch")
        if (e["input_sha256"] != c["content_sha256"] or e["truncation"] is not False
                or e["tokens_with_special"] != len(e["after"]["token_ids"])
                or e["after"]["token_ids_sha256"] != digest(canonical(e["after"]["token_ids"]).encode())
                or e["encoder_text_sha256"] != digest(e["encoder_text"].encode())
                or e["unknown_tokens"] != sum(t == 3 for t in e["after"]["token_ids"])):
            raise ValueError("Encoder evidence count/hash mismatch")
    return candidates, chunks, contexts, encoder, laws, checks


def trace_checks(root, chunks, contexts):
    records = rows(root / "support/extraction_records.jsonl")
    traces = {}
    for r in records:
        base = root / "inputs/tree/extraction_snapshot"
        p = resolve_ref(base, r["trace_ref"])
        if digest(p.read_bytes()) != r["trace_sha256"] or r["extraction"]["review_status"] != "pending":
            raise ValueError("Extraction trace hash/status mismatch")
        traces[r["extraction"]["extraction_id"]] = load(p)["nodes"]
    for name in ["documents.pending.jsonl","files.pending.jsonl"]:
        for record in rows(root/"support"/name):
            if record["status"] != "pending" or any(record["evidence"].get(k) is not None for k in ["reviewer_ref","verified_at"]):
                raise ValueError("Source provenance cannot become verified")
    for c in list(chunks.values()) + contexts:
        for s in json.loads(c["source_locator"]):
            nodes = [n for n in traces[s["extraction_id"]] if n["locator"] == s["locator"]]
            if len(nodes) != 1 or not nodes[0]["char_start"] <= s["char_start"] < s["char_end"] <= nodes[0]["char_end"]:
                raise ValueError("Source span does not match trace locator/range")


def calculate(root):
    cfg = load(root / "packaging_config.json"); require_policy(cfg)
    pilot, chunks, contexts, encoder, laws, checks = replay(root)
    trace_checks(root, chunks, contexts)
    rules, findings = evidence_checks(root)
    selected, deferred = select(pilot, rules, findings, checks)
    selected_ids = {p["unit_id"] for p in selected}
    cs = sorted([chunks[u] for u in selected_ids], key=lambda c:c["chunk_id"])
    cids = {c["chunk_id"] for c in cs}
    ctx = sorted([c for c in contexts if c["chunk_id"] in cids], key=lambda c:(c["chunk_id"],c["context_order"]))
    enc_cfg = load(root / "encoder_config.json")
    diagnostic=load(root/"unknown_diagnostics.json")
    if diagnostic["encoder_config"]!=enc_cfg or diagnostic["preprocessing_changed"] is not False or diagnostic["inference_loaded"] is not False:
        raise ValueError("Unknown diagnostic configuration mismatch")
    uid=diagnostic["unit_id"]
    if uid not in encoder or any(encoder[uid][k]!=v for k,v in diagnostic["result"]["rows"][0].items()):
        raise ValueError("Unknown diagnostic/encoder evidence mismatch")
    for name, expected in enc_cfg["tokenizer_assets"].items():
        asset = resolve_ref(root / "tokenizer_assets", name)
        if digest(asset.read_bytes()) != expected["sha256"] or asset.stat().st_size != expected["size_bytes"]:
            raise ValueError("Pinned tokenizer asset mismatch")
    targets = [{"dataset_version":cfg["dataset_version"], "unit_id":p["unit_id"], "chunk_id":p["chunk_id"],
                "law_id":p["law_id"], "citation_path":p["citation_path"], "target_type":next(u["unit_type"] for u in laws[p["law_id"]]["units"] if u["unit_id"]==p["unit_id"]),
                "scope_proposal":p["scope_proposal"], "source_status":"pending", "technical_review":"pending",
                "applicability":"pending_review", "tokens_with_special":p["tokens_with_special"], "unknown_tokens":p["unknown_tokens"],
                "experimental":True,"release_eligible":False} for p in selected]
    docs = [{**data["document"], "target_count":sum(t["law_id"]==law for t in targets),
             "source_provenance":"pending", "applicability":"pending_review"} for law,data in sorted(laws.items()) if any(t["law_id"]==law for t in targets)]
    gaps = []
    spans=[s for law in laws.values() for s in law["spans"]]
    for p in selected:
        fields = [(p["unit_id"],"text_original","target")] + [(d["unit_id"],d["field_name"],"context") for d in p["context_dependencies"]]
        for uid, field, role in fields:
            for dimension, missing in [("source","DOCX legacy lacks historical download/provenance and scoped official-content verification"),
                                       ("technical","Agent source/span/builder checks are not an actual technical reviewer decision"),
                                       ("applicability","Historical applicability/amendment/exception review at snapshot remains incomplete")]:
                gaps.append({"target_unit_id":p["unit_id"],"dependency_unit_id":uid,"field":field,"role":role,"dimension":dimension,
                             "status":"pending","missing":missing,
                             "span_ids":[s["span_id"] for s in spans if s["unit_id"]==uid and s["field_name"]==field],
                             "explicit_unit_date_rule_ids":[r["rule_id"] for r in rules if uid in r["unit_ids"]],
                             "legacy_target_finding_ids":p["prior_finding_ids"],"reviewer_ref":None})
    counts = Counter(reason for d in deferred for reason in d["reasons"])
    token = [t["tokens_with_special"] for t in targets]
    stats = {"dataset_version":cfg["dataset_version"],"experimental":True,"snapshot_date":SNAPSHOT_DATE,
             "snapshot_guarantee":"reference_only_not_all_units_confirmed_applicable", "input_candidates":len(pilot),
             "target_count":len(selected_ids),"chunk_count":len(cs),"context_row_count":len(ctx),
             "distinct_context_units":len({c["unit_id"] for c in ctx}),
             "distinct_context_fields":len({(c["unit_id"],c["field_name"],c["char_start"],c["char_end"]) for c in ctx}),
             "by_law":dict(Counter(t["law_id"] for t in targets)),"by_target_type":dict(Counter(t["target_type"] for t in targets)),
             "token_count":{"basis":"upstream_verified_full_encoder_input_including_special","min":min(token) if token else None,
                            "max":max(token) if token else None,"total":sum(token)},
             "unknown_tokens":sum(t["unknown_tokens"] for t in targets),"targets_with_unknown":sum(t["unknown_tokens"]>0 for t in targets),
             "deferred_count":len(deferred),"deferred_by_reason":dict(sorted(counts.items())),
             "reason_counts_overlap":True,"metadata_gap_rows":len(gaps),"pending_gap_counts":dict(Counter(g["dimension"] for g in gaps)),
             "source_pending_targets":len(targets),"technical_review_pending_targets":len(targets),"applicability_pending_targets":len(targets),
             "human_reviewer_events":0,"corpus_version":None,"release_eligible":False}
    return {"chunks":cs,"contexts":ctx,"targets":targets,"deferred":deferred,"documents":docs,"gaps":gaps}, stats


def stats_md(stats):
    lines = ["# Thống kê dataset thử nghiệm", "", "Snapshot 2025-01-01 chỉ là ngày tham chiếu dự kiến; applicability vẫn pending.", "",
             "| Chỉ tiêu | Giá trị |", "|---|---:|"]
    for k in ["input_candidates","target_count","chunk_count","context_row_count","distinct_context_units","distinct_context_fields","deferred_count","unknown_tokens","targets_with_unknown","metadata_gap_rows"]:
        lines.append(f"| {k} | {stats[k]} |")
    lines += ["", "Các nhóm deferred có thể giao nhau; không cộng nhóm làm tổng candidate.", "", "```json", json.dumps(stats,ensure_ascii=False,indent=2), "```", ""]
    return "\n".join(lines)


def readme(stats):
    return f"""# {stats['dataset_version']}

experimental=true; {stats['target_count']} target, {stats['chunk_count']} chunk,
{stats['context_row_count']} context rows. Đây là pilot được chọn có chủ đích,
chưa đại diện toàn miền pháp luật giao thông. Không phải corpus verified,
frozen hoặc serving release. corpus_version=null, release_eligible=false.
Snapshot 2025-01-01 là ngày tham chiếu dự kiến; applicability pending nên
không bảo đảm toàn bộ nội dung áp dụng vào ngày đó. Không có reviewer event.

BM25 và Dense phải dùng cùng tập chunk_id và text_for_search nền trong
chunks.jsonl. text_original/context_text/spans và nguồn giữ nguyên upstream.
Các DOCX/normalized/trace trong inputs là bằng chứng kỹ thuật có provenance
pending; cấu trúc toàn văn trong support/laws.json chỉ để tái kiểm ranh giới
và issue của builder, không thêm các unit đó vào target/context tìm kiếm.

BKAI hiện dùng encoder_config.json, word segmentation PyVi CPU trước encoder,
cùng preprocessing cho query/document. Đây chưa là lựa chọn model cuối cùng.
Không dùng encoder_text đã PyVi mặc định cho mọi model. Các số token kế thừa
upstream đã replay; validator portable kiểm binding/IDs/count/hash, không
chạy tokenizer/PyVi hoặc encoder. Tokenizer assets có trong bundle; package
PyVi/CRF, Transformers và encoder weights không đóng gói. Muốn tokenize lại
cần môi trường requirements-stage6.txt đúng pins và module encoder_input của
repository, ghi kết quả vào run khác. Không có embedding/index trong bộ này.

Qrels sau này phải tham chiếu dataset_version={stats['dataset_version']} và
chunk_id đúng bộ, kèm dataset_content_sha256 trong dataset_manifest.json.
Không dùng số dòng hoặc citation thay ID. targets.csv, deferred_candidates.csv,
metadata_gaps.csv và evidence giúp phân biệt scope, kỹ thuật và hiệu lực.
Ngày trong date_rules là ứng viên bằng chứng, không phải metadata đã duyệt.
Unknown không tự bị loại; xem unknown_diagnostics.json/MD và encoder records.

Kiểm portable sau khi chuyển toàn thư mục (Python 3.11+, chỉ stdlib):

```powershell
python -B runtime/validate_dataset.py validate --manifest dataset_manifest.json
```

Hoặc tại repository:

```powershell
python -B -m src.experimental_dataset validate --manifest <bundle>/dataset_manifest.json
```

Các proof gốc dùng đường dẫn inputs/... tính từ gốc bundle. Evidence finding
text_ref tính từ evidence/pages/; catalog.artifact_ref tính từ gốc bundle.
URL/accessed_at capture giữ ngày sự kiện thật, không thay ngày tải DOCX lịch
sử hoặc ngày hiệu lực. Extraction trace_ref tính từ inputs/tree/extraction_snapshot/.

input_binding.json giữ SHA/version upstream và hashes các tệp nguồn đã chọn;
không sao chép đệ quy lịch sử staging. Full upstream replay/build từ đầu cần
run refinement gốc và repository đúng version; portable validation chỉ tái
kiểm phạm vi bundle. Manifest/checksum không phải chữ ký hoặc xác minh pháp lý.
Dataset manifest/data ổn định theo nội dung; execution.json chứa thời điểm/log
thực thi riêng, không nằm trong dataset_content_sha256. Không ghi vào bundle
đã seal khi kiểm tra (dùng -B để không tạo __pycache__).
"""


def views(out, stats):
    return {"README.md":readme(stats), "dataset_statistics.md":stats_md(stats),
            "targets.csv":csv_text(out["targets"], ["dataset_version","unit_id","chunk_id","law_id","citation_path","target_type","scope_proposal","source_status","technical_review","applicability","tokens_with_special","unknown_tokens","experimental","release_eligible"]),
            "deferred_candidates.csv":csv_text(out["deferred"],["unit_id","chunk_id","citation_path","scope_proposal","reasons","evidence","tokens_with_special","release_eligible"]),
            "documents.csv":csv_text(out["documents"],["law_id","source_id","law_title","source_url","target_count","source_provenance","applicability"]),
            "metadata_gaps.csv":csv_text(out["gaps"],["target_unit_id","dependency_unit_id","field","role","dimension","status","missing","span_ids","explicit_unit_date_rule_ids","legacy_target_finding_ids","reviewer_ref"])}


def model_binding(root):
    enc=load(root/"encoder_config.json");cfg=load(root/"chunk_config.json")
    return {k:enc[k] for k in ["model_id","model_revision","preprocessing_version"]} | {"chunk_policy_version":cfg["chunk_policy_version"],"preview_token_budget":cfg["token_limit"]}


def validate(manifest):
    path=Path(manifest).resolve();root=path.parent;m=load(path)
    if digest(path.read_bytes()) != (root/"dataset_manifest.sha256").read_text(encoding="ascii").strip():
        raise ValueError("Dataset manifest checksum mismatch")
    cfg=load(root/"packaging_config.json");require_policy(cfg)
    if (m["dataset_version"] != cfg["dataset_version"] or m["policy_version"] != VERSION
            or m["experimental"] is not True or m["corpus_version"] is not None
            or m["release_eligible"] is not False or m["snapshot_date"] != SNAPSHOT_DATE):
        raise ValueError("Dataset version/pending contract mismatch")
    if m["files"] != inventory(root) or digest(canonical(m["files"]).encode()) != m["dataset_content_sha256"]:
        raise ValueError("Dataset file inventory/hash mismatch")
    if digest(Path(__file__).read_bytes()) != m["validator_sha256"]:
        raise ValueError("Validator version mismatch")
    binding=load(root/"input_binding.json")
    if m["input_binding"] != binding or m["encoder_config_sha256"] != digest((root/"encoder_config.json").read_bytes()):
        raise ValueError("Input/model binding mismatch")
    if m["model_binding"] != model_binding(root):raise ValueError("Pinned model/policy binding mismatch")
    for q in binding["packaged_source_files"]:
        if digest(resolve_ref(root,q["bundle_ref"]).read_bytes()) != q["sha256"]:
            raise ValueError("Packaged upstream source hash mismatch")
    out,stats=calculate(root)
    if m["counts"] != stats or load(root/"dataset_statistics.json") != stats:
        raise ValueError("Dataset count/statistics mismatch")
    if rows(root/"chunks.jsonl") != out["chunks"] or rows(root/"contexts.jsonl") != out["contexts"]:
        raise ValueError("Selected/deferred chunks or context replay mismatch")
    for name,ids in [("target_unit_ids.txt",sorted(c["unit_id"] for c in out["chunks"])),("chunk_ids.txt",sorted(c["chunk_id"] for c in out["chunks"]))]:
        if (root/name).read_text(encoding="utf8") != "".join(s+"\n" for s in ids):raise ValueError("ID set export mismatch")
    for name,text in views(out,stats).items():
        if (root/name).read_text(encoding="utf8") != text: raise ValueError("CSV/Markdown/readable view mismatch: "+name)
    expected={"technical_valid":True,"experimental":True,"release_eligible":False,"human_reviewer_events":0,
              "counts":stats,"tokenizer_reexecuted":False,"validation_scope":"portable_bounded_builder_source_evidence_replay"}
    if load(root/"validation_report.json") != expected: raise ValueError("Validation report mismatch")
    return expected


def build(manifest, run_dir, config=DEFAULT_CONFIG):
    from src import pilot_refinement, coverage_survey
    from src.pipeline_cli import staging_path
    source=Path(manifest).resolve().parent;target=staging_path(run_dir);cfg=load(config);require_policy(cfg)
    if target.exists() or source==target or source in target.parents:
        raise ValueError("New run required outside sealed input")
    pilot_refinement.validate(manifest)  # Required full input validation before output.
    cov=source/"scope_snapshot/coverage_snapshot";assessment=cov/"inputs/assessment"
    candidates=rows(source/"pilot_candidates.jsonl");ids={p["unit_id"] for p in candidates}
    laws,_=coverage_survey.load_data(cov)
    laws={k:v for k,v in laws.items() if any(u["unit_id"] in ids for u in v["units"])}
    target.mkdir(parents=True)
    copied=[]
    def copy(origin, ref):
        dest=resolve_ref(target,ref);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(origin,dest)
        copied.append({"bundle_ref":ref,"sha256":digest(dest.read_bytes())})
    try:
        for d in ["support","evidence/pages","tokenizer_assets","runtime"]:(target/d).mkdir(parents=True,exist_ok=True)
        write_json(target/"packaging_config.json",cfg);write_json(target/"support/laws.json",laws)
        # Project old candidates, removing historical relative paths. Keep IDs/hashes
        # and exact dependency proofs; rebasing paths is not a legal ID change.
        for p in candidates:
            p["prior_finding_ids"]=p["source_evidence"]["prior_finding_ids"]
            for key in ["source_evidence","source_proof_base_ref"]:p.pop(key)
            for d in p["context_dependencies"]:d.pop("source_locator_base_ref",None)
        write_rows(target/"support/pilot.jsonl",candidates)
        revisions=rows(source/"scope_proposal_revisions.jsonl")
        write_rows(target/"support/scope_history.jsonl",[
            {**{k:r[k] for k in ["unit_id","unit_sha256","proposal_id","previous_proposal_id","previous_proposal_sha256","scope_candidate","reason","regulated_subject","behavior_right_duty","use_cases","reference_notes"]},
             "original_proposal_sha256":digest(canonical(r).encode()),"origin":"agent_review","reviewer_ref":None,"reviewed_at":None}
            for r in revisions])
        fields=rows(source/"context_field_reviews.jsonl")
        for f in fields:f.pop("source_locator_base_ref",None)
        write_rows(target/"support/field_reviews.jsonl",fields)
        chunks=rows(cov/"preview/chunks.preview.jsonl");contexts=rows(cov/"preview/contexts.preview.jsonl")
        for q in rows(cov/"preview/quarantined.preview.jsonl"):chunks.append(q["candidate"]);contexts.extend(q["contexts"])
        chunks=[c for c in chunks if c["unit_id"] in ids];cids={c["chunk_id"] for c in chunks}
        write_rows(target/"support/chunks.upstream.jsonl",sorted(chunks,key=lambda c:c["chunk_id"]))
        write_rows(target/"support/contexts.upstream.jsonl",sorted([c for c in contexts if c["chunk_id"] in cids],key=lambda c:(c["chunk_id"],c["context_order"])))
        write_rows(target/"support/encoder_inputs.jsonl",[e for e in rows(cov/"preview/encoder_inputs.preview.jsonl") if e["unit_id"] in ids])
        write_json(target/"chunk_config.json",load(cov/"config.json")["chunk"])
        write_json(target/"support/release_blockers.json",coverage_survey.LEGAL_BLOCKERS)
        for data in laws.values():
            for f in data["files"]:copy(cov/"inputs"/f["raw_file_ref"],"inputs/"+f["raw_file_ref"])
            for e in data["extractions"]:copy(cov/"inputs"/e["text_ref"],"inputs/"+e["text_ref"])
        er=[r for r in rows(cov/"inputs/tree/extraction_snapshot/extractions.pending.jsonl") if r["law_id"] in laws]
        write_rows(target/"support/extraction_records.jsonl",er)
        for r in er:copy(cov/"inputs/tree/extraction_snapshot"/r["trace_ref"],"inputs/tree/extraction_snapshot/"+r["trace_ref"])
        src=cov/"inputs/tree/extraction_snapshot/source_snapshot"
        for name in ["documents.pending.jsonl","files.pending.jsonl"]:
            data=[r for r in rows(src/name) if r["law_id"] in laws]
            write_rows(target/"support"/name,data)
        for doc in rows(target/"support/documents.pending.jsonl"):
            ref=doc["declared"]["inventory_ref"]
            if not (target/ref).exists():copy(BASE_DIR/ref,ref)
        fids={i for p in candidates for i in p["prior_finding_ids"]}
        rules=[r for r in rows(assessment/"date_rules.pending.jsonl") if ids.intersection(r["unit_ids"])]
        fids.update(r["finding_id"] for r in rules)
        findings=[f for f in rows(assessment/"evidence_findings.pending.jsonl") if f["finding_id"] in fids]
        write_rows(target/"evidence/findings.pending.jsonl",findings);write_rows(target/"evidence/date_rules.pending.jsonl",rules)
        catalog=[]
        for e in rows(assessment/"evidence.jsonl"):
            if e["evidence_id"] not in {f["evidence_id"] for f in findings}:continue
            ref="evidence/captures/"+e["artifact_ref"]
            copy(assessment/"evidence_snapshot"/e["artifact_ref"],ref)
            catalog.append({k:e[k] for k in ["evidence_id","law_id","url","accessed_at","kind","sha256","size_bytes"]} | {"artifact_ref":ref,"review_status":"pending"})
        write_rows(target/"evidence/catalog.jsonl",catalog)
        for f in findings:
            if f["kind"]=="text_slice":copy(assessment/"evidence_snapshot"/f["text_ref"],"evidence/pages/"+f["text_ref"])
        copy(cov/"encoder_config.json","encoder_config.json")
        for p in sorted((cov/"tokenizer_assets").iterdir()):copy(p,"tokenizer_assets/"+p.name)
        # Preserve diagnostic records but rebase the diagnostic's explicit base.
        diag=load(source/"unknown_diagnostics.json");diag["source_proof_base_ref"]="";write_json(target/"unknown_diagnostics.json",diag)
        copy(source/"unknown_diagnostics.md","unknown_diagnostics.md")
        for name in RUNTIME:copy(BASE_DIR/name,"runtime/"+name)
        copy(Path(__file__),"runtime/validate_dataset.py")
        bind={"refinement_manifest_sha256":digest(Path(manifest).read_bytes()),
              "upstream_manifests":{name:digest(p.read_bytes()) for name,p in [("scope",source/"scope_snapshot/manifest.json"),("coverage",cov/"manifest.json"),("tree",cov/"inputs/tree/manifest.json"),("extraction",cov/"inputs/tree/extraction_snapshot/manifest.json")]},
              "upstream_code_sha256":load(manifest)["code_sha256"],"tree_binding":revisions[0]["binding"]["tree_binding"],
              "packaged_source_files":sorted({c["bundle_ref"]:c for c in copied}.values(),key=lambda c:c["bundle_ref"])}
        write_json(target/"input_binding.json",bind)
        out,stats=calculate(target)
        write_rows(target/"chunks.jsonl",out["chunks"]);write_rows(target/"contexts.jsonl",out["contexts"])
        for name,ids in [("target_unit_ids.txt",sorted(c["unit_id"] for c in out["chunks"])),("chunk_ids.txt",sorted(c["chunk_id"] for c in out["chunks"]))]:
            (target/name).write_text("".join(s+"\n" for s in ids),encoding="utf8",newline="\n")
        write_json(target/"dataset_statistics.json",stats)
        write_json(target/"validation_report.json",{"technical_valid":True,"experimental":True,"release_eligible":False,"human_reviewer_events":0,"counts":stats,"tokenizer_reexecuted":False,"validation_scope":"portable_bounded_builder_source_evidence_replay"})
        for name,text in views(out,stats).items():(target/name).write_text(text,encoding="utf8",newline="\n")
        files=inventory(target)
        write_json(target/"dataset_manifest.json",{"dataset_version":cfg["dataset_version"],"policy_version":VERSION,"snapshot_date":SNAPSHOT_DATE,
                   "experimental":True,"corpus_version":None,"release_eligible":False,"input_binding":bind,"counts":stats,
                   "encoder_config_sha256":digest((target/"encoder_config.json").read_bytes()),"validator_sha256":digest(Path(__file__).read_bytes()),
                   "model_binding":model_binding(target),
                   "dataset_content_sha256":digest(canonical(files).encode()),"files":files})
        (target/"dataset_manifest.sha256").write_text(digest((target/"dataset_manifest.json").read_bytes())+"\n",encoding="ascii")
        validate(target/"dataset_manifest.json")
        write_json(target/"execution.json",{"completed_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"operation":"build_and_validate","technical_valid":True,"origin":"agent_review","human_reviewer_events":0})
        return stats
    except Exception:
        write_json(target/"execution.json",{"failed_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"technical_valid":False,"operation":"build"})
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    b=sub.add_parser("build");b.add_argument("--manifest",type=Path,required=True);b.add_argument("--run-dir",type=Path,required=True);b.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    v=sub.add_parser("validate");v.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        print(canonical(build(a.manifest,a.run_dir,a.config) if a.command=="build" else validate(a.manifest)));return 0
    except Exception as exc:
        print(canonical({"technical_valid":False,"error":str(exc),"release_eligible":False}),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
