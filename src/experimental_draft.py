"""Compose the unchanged experimental v1 and the scoped A16K2 source branch.

No unified legal tree, reviewer decisions, indexes, tokenization or inference.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import unicodedata

from src import retrieval_dataset as base_dataset
from src import nd168_a16k2 as recovery
from src.assessment_evidence import check_files, inventory as recovery_inventory
from src.chunk_preview import chunk_identity, search_components
from src.config import BASE_DIR, SNAPSHOT_DATE
from src.experimental_dataset import load, rows, write_json, write_rows, unique
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest, resolve_ref

VERSION = "coverage-source-branches-draft.v1"
DEFAULT_CONFIG = BASE_DIR / "config/experimental_dataset_draft.v1.json"
CONTROL = {"dataset_manifest.json", "dataset_manifest.sha256", "execution.json"}
BASE_REF = "components/base"
RECOVERY_REF = "components/nd168-a16k2"
CODE = list(dict.fromkeys(base_dataset.CODE + [
    "src/experimental_draft.py", "src/nd168_a16k2.py", "src/ingestion/extraction_normalizer.py",
    "src/source_contracts.py", "src/assessment_evidence.py", "src/content_comparison.py",
    "src/encoder_input.py", "src/article22_preview.py", "src/legal_parser.py"]))


def normalized(value):
    """Comparison diagnostic only; never changes content, identity or offsets."""
    return " ".join(unicodedata.normalize("NFC", value).split())


def basis(chunk, units):
    u = units[chunk["unit_id"]]
    if (chunk["law_id"], chunk["citation_path"]) != (u["law_id"], u["citation_path"]):
        raise ValueError("Chunk legal position differs from its source unit")
    return u["law_id"], u["canonical_path"]


def compare_candidates(old, old_units, new, new_units, crosswalk):
    """Audit every new candidate against all old chunks, not only its old ID."""
    unique(old, "chunk_id"); unique(new, "chunk_id")
    by_new = unique(crosswalk, "new_unit_id")
    result = []
    for c in sorted(new, key=lambda x: new_units[x["unit_id"]]["ordinal"]):
        key = basis(c, new_units)
        same_basis = [x for x in old if basis(x, old_units) == key]
        same_citation = [x for x in old if (x["law_id"], normalized(x["citation_path"])) ==
                         (c["law_id"], normalized(c["citation_path"]))]
        same_id = [x for x in old if x["chunk_id"] == c["chunk_id"] or x["unit_id"] == c["unit_id"]]
        if any(basis(x, old_units) != key for x in same_citation + same_id):
            kind = "conflicted"
        elif same_basis:
            kind = "duplicate" if all(x["text_original"] == c["text_original"] and
                x["context_text"] == c["context_text"] for x in same_basis) else "conflicted"
        else:
            kind = "added"
        def refs(values):
            return [{k: x[k] for k in ["law_id", "citation_path", "unit_id", "chunk_id", "content_sha256"]} for x in values]
        cw = by_new[c["unit_id"]]
        legacy = old_units.get(cw["old_unit_id"])
        if legacy is not None and (legacy["law_id"], legacy["canonical_path"]) != key:
            raise ValueError("Crosswalk points to a different legal basis")
        result.append({"law_id": c["law_id"], "citation_path": c["citation_path"], "canonical_path": key[1],
            "new_unit_id": c["unit_id"], "new_chunk_id": c["chunk_id"], "classification": kind,
            "old_unit_id": cw["old_unit_id"], "old_chunk_ids": [x["chunk_id"] for x in same_basis],
            "same_basis": refs(same_basis), "same_citation": refs(same_citation), "same_ids": refs(same_id),
            "same_text_exact_all_dataset": refs([x for x in old if x["text_original"] == c["text_original"]]),
            "same_text_nfc_whitespace_all_dataset": refs([x for x in old if normalized(x["text_original"]) == normalized(c["text_original"])]),
            "legacy_unit_exists": legacy is not None,
            "legacy_text_exact": legacy["text_original"] == c["text_original"] if legacy else None,
            "changed_identity_fields": cw["changed_identity_fields"], "crosswalk_reason": cw["reason"],
            "reason": "No existing target at this legal position; different source IDs alone were not used to decide" if kind == "added" else
                      "Same legal position requires explicit resolution; do not append by different ID"})
    return result


def check_active_targets(chunks, memberships, graphs):
    """Graph-local FKs, globally unique target legal positions and chunk IDs."""
    by = unique(chunks, "chunk_id"); members = unique(memberships, "chunk_id")
    if set(by) != set(members):
        raise ValueError("Incomplete or extra graph membership")
    positions = set()
    for cid, c in by.items():
        graph = graphs[members[cid]["graph_id"]]
        key = basis(c, graph)
        if key in positions:
            raise ValueError("Duplicate target legal basis across source branches")
        positions.add(key)
        if c["parent_unit_id"] != graph[c["unit_id"]]["parent_unit_id"]:
            raise ValueError("Target parent differs from graph-local relationship")


def replay_recovery(root, base):
    """Replay the packaged scoped mapping and builder with measured token evidence.

    Unlike recovery.validate, this does not require external coverage/tokenizer
    assets; the old comparison snapshot is bound to the packaged base instead.
    """
    m = check_files(root / "manifest.json")
    if (m["manifest_type"] != recovery.VERSION or m["files"] != recovery_inventory(root)
            or m["code_sha256"] != digest(Path(recovery.__file__).read_bytes())
            or m["snapshot_date"] != SNAPSHOT_DATE or m["origin"] != "agent_review"
            or m["human_reviewer_event_count"] != 0 or m["release_eligible"] is not False
            or m["corpus_version"] is not None):
        raise ValueError("Recovery manifest/version/pending/code mismatch")
    cfg = load(root / "config.json"); capture = load(root / "sources/capture.json")
    records = recovery.source_records(root, cfg)
    if (records != rows(root / "source_files.prepared.jsonl")
            or recovery.source_facts(root, cfg) != load(root / "source_facts.pending.json")
            or cfg["policy_version"] != recovery.VERSION or cfg["snapshot_date"] != SNAPSHOT_DATE
            or cfg["law_id"] != recovery.LAW or cfg["visual_review"]["unresolved_characters"]
            or cfg["visual_review"]["origin"] != "agent_review"
            or cfg["visual_review"]["human_reviewer_event_count"] != 0
            or digest((root / "sources/official.html").read_bytes()) != cfg["html_sha256"]
            or capture["sha256"] != cfg["html_sha256"]
            or digest((root / "sources/capture.json").read_bytes()) != cfg["html_capture_record_sha256"]
            or digest((root / "sources/official_scan.pdf").read_bytes()) != cfg["pdf_sha256"]):
        raise ValueError("Recovery source evidence/status mismatch")
    if [p["page"] for p in cfg["pdf_pages"]] != [40, 41]:
        raise ValueError("Unexpected scan review scope")
    for p in cfg["pdf_pages"]:
        if digest((root / f"evidence/page-{p['page']:03d}.png").read_bytes()) != p["image_sha256"]:
            raise ValueError("Recovery scan page hash mismatch")
    text, trace, extraction = recovery.extract_html((root / "sources/official.html").read_bytes(), records[0]["file_id"])
    extraction["created_at"] = m["built_at"]
    if ((root / "extraction/normalized.txt").read_bytes() != text.encode()
            or load(root / "extraction/metadata.json") != extraction or load(root / "extraction/trace.json") != trace):
        raise ValueError("Recovery extraction replay mismatch")
    units, spans = recovery.map_units(text, trace)
    recovery.check_projection(units, spans, extraction, text, trace)
    if units != rows(root / "legal_units.pending.jsonl") or spans != rows(root / "source_spans.pending.jsonl"):
        raise ValueError("Recovery mapping replay mismatch")
    laws = load(base / "support/laws.json"); legacy = laws[recovery.LAW]
    old_e = legacy["extractions"][0]
    if (rows(root / "legacy/units.jsonl") != legacy["units"] or rows(root / "legacy/spans.jsonl") != legacy["spans"]
            or (root / "legacy/normalized.txt").read_bytes() != resolve_ref(base / "inputs", old_e["text_ref"]).read_bytes()):
        raise ValueError("Recovery legacy tree/text differs from packaged base")
    er = next(e for e in rows(base / "support/extraction_records.jsonl") if e["law_id"] == recovery.LAW)
    if (root / "legacy/trace.json").read_bytes() != resolve_ref(base / "inputs/tree/extraction_snapshot", er["trace_ref"]).read_bytes():
        raise ValueError("Recovery legacy trace differs from base")
    comp, crosswalk = recovery.comparisons(units, spans, legacy["units"], legacy["spans"],
                                        (root / "legacy/normalized.txt").read_text(encoding="utf8"), load(root / "legacy/trace.json"))
    if comp != rows(root / "comparison.jsonl") or crosswalk != rows(root / "id_crosswalk.jsonl"):
        raise ValueError("Recovery comparison/crosswalk mismatch")
    if m["coverage_manifest_sha256"] != load(base / "input_binding.json")["coverage_manifest_sha256"]:
        raise ValueError("Different recovery/base coverage bindings")
    if load(root / "encoder_config.json") != load(base / "encoder_config.json"):
        raise ValueError("Encoder/preprocessing changed")
    enc = rows(root / "encoder_inputs.jsonl"); lookup = unique(enc, "input_sha256")
    for e in enc:
        after = e["after"]
        if (e["truncation"] is not False or e["role"] != "document" or e["model_max_tokens"] != 256
                or e["tokens_with_special"] != len(after["token_ids"]) or e["tokens_with_special"] > 256
                or after["token_ids_sha256"] != digest(canonical(after["token_ids"]).encode())
                or e["encoder_text_sha256"] != digest(e["encoder_text"].encode())
                or e["unknown_tokens"] != after["token_ids"].count(3)):
            raise ValueError("Invalid measured encoder evidence")
    data = {"document": {"law_id": recovery.LAW, "source_id": "SRC-004", "law_title": units[0]["title"], "source_url": capture["url"]},
            "units": units, "spans": spans, "extractions": [extraction], "files": [records[0]], "issues": []}
    chunk_cfg = {"chunk_policy_version": recovery.chunk_preview_v2.VERSION, "snapshot_date": SNAPSHOT_DATE, "token_limit": 256,
                 "required_context_fields": ["title"], "required_clause_context_fields": ["text_original"],
                 "target_unit_ids": [u["unit_id"] for u in units if u["unit_type"] == "point"]}
    output = recovery.chunk_preview_v2.build_chunks(data, root, chunk_cfg, recovery.BLOCKERS,
        lambda texts: [lookup[digest(t.encode())] for t in texts])
    for key, filename in recovery.EXPORTS.items():
        if output[key] != rows(root / filename):
            raise ValueError("Recovery cached builder replay mismatch: " + key)
    if len(output["chunks"]) != 5 or output["quarantined"] or output["issues"]:
        raise ValueError("Recovery must contain the five complete supported points")
    proposals = unique(rows(root / "scope.proposals.jsonl"), "unit_id")
    if set(proposals) != {u["unit_id"] for u in units}:
        raise ValueError("Incomplete recovery proposals")
    for u in units:
        p = proposals[u["unit_id"]]
        expected_scope = "included" if u["unit_type"] == "point" else "supporting" if u["unit_type"] in {"article", "clause"} else None
        if (p["unit_sha256"] != digest(canonical(u).encode()) or p["scope_candidate"] != expected_scope
                or p["origin"] != "agent_review" or p["status"] != "proposed" or p["reviewer_ref"] is not None
                or p["binding"] != {"extraction_id": extraction["extraction_id"], "html_sha256": cfg["html_sha256"],
                                     "pdf_sha256": cfg["pdf_sha256"], "snapshot_date": SNAPSHOT_DATE}
                or p["applicability_status"] != "pending_review" or p["effective_from"] is not None
                or p["effective_to"] is not None or p["release_eligible"] is not False):
            raise ValueError("Recovery proposal/pending binding mismatch")
    return data, output, crosswalk, proposals


def calculate(base, restored):
    data, output, crosswalk, proposals = replay_recovery(restored, base)
    old = rows(base / "chunks.jsonl"); new = output["chunks"]
    laws = load(base / "support/laws.json")
    old_units = unique([u for d in laws.values() for u in d["units"]], "unit_id")
    new_units = unique(data["units"], "unit_id")
    comparisons = compare_candidates(old, old_units, new, new_units, crosswalk)
    if any(c["classification"] != "added" for c in comparisons):
        raise ValueError("Non-additive candidate conflict/duplicate: " + canonical(comparisons))
    chunks = sorted(old + new, key=lambda x: x["chunk_id"])
    contexts = sorted(rows(base / "contexts.jsonl") + output["contexts"], key=lambda x: (x["chunk_id"], x["context_order"]))
    memberships = sorted([{"chunk_id": c["chunk_id"], "graph_id": graph} for graph, group in
                         [("base-docx", old), ("nd168-html-a16k2", new)] for c in group], key=lambda x: x["chunk_id"])
    check_active_targets(chunks, memberships, {"base-docx": old_units, "nd168-html-a16k2": new_units})
    by_chunk = unique(chunks, "chunk_id")
    if any(c["chunk_id"] not in by_chunk for c in contexts):
        raise ValueError("Orphan context")
    for c in new:
        ctx = [x for x in output["contexts"] if x["chunk_id"] == c["chunk_id"]]
        search_components(c)
        if c["chunk_id"] != "c_" + digest(canonical(chunk_identity(c, ctx)).encode()) or c["content_sha256"] != digest(c["text_for_search"].encode()):
            raise ValueError("New chunk identity/content mismatch")
    metadata = rows(base / "metadata.jsonl") + [{"chunk_id": c["chunk_id"], "unit_id": c["unit_id"],
        "unit_sha256": digest(canonical(new_units[c["unit_id"]]).encode()), "scope_proposal": proposals[c["unit_id"]]["scope_candidate"],
        "scope_proposal_id": None, "scope_proposal_sha256": digest(canonical(proposals[c["unit_id"]]).encode()),
        "scope_reason": proposals[c["unit_id"]]["reason"], "source_status": "pending", "technical_review": "pending",
        "applicability": "pending_review", "origin": "agent_review", "reviewer_decision": None,
        "experimental": True, "release_eligible": False} for c in new]
    metadata.sort(key=lambda x: x["chunk_id"])
    delta = sorted([{"status": status, "law_id": c["law_id"], "citation_path": c["citation_path"], "unit_id": c["unit_id"],
        "old_chunk_id": c["chunk_id"] if status == "unchanged" else None, "new_chunk_id": c["chunk_id"],
        "content_sha256": c["content_sha256"], "reason": "Object/context/proof unchanged; graph root is explicit" if status == "unchanged" else
        "Restored official-source target not previously packaged; not an ID-only duplicate", "qrels_action":
        "carry_over_only_after_new_dataset_binding_and_judgment_review" if status == "unchanged" else "unjudged_no_automatic_label"}
        for status, group in [("unchanged", old), ("added", new)] for c in group], key=lambda x: x["new_chunk_id"])
    unit_cw = [{**r, "old_chunk_ids": [c["chunk_id"] for c in old if c["unit_id"] == r["old_unit_id"]],
                "new_chunk_ids": [c["chunk_id"] for c in new if c["unit_id"] == r["new_unit_id"]],
                "old_graph_id": "base-docx" if r["old_unit_id"] else None, "new_graph_id": "nd168-html-a16k2"} for r in crosswalk]
    parents = []
    for r in crosswalk:
        u = new_units[r["new_unit_id"]]
        if u["unit_type"] == "point":
            continue
        o = old_units[r["old_unit_id"]]
        parents.append({"law_id": u["law_id"], "citation_path": u["citation_path"], "unit_type": u["unit_type"],
            "old_unit_id": o["unit_id"], "new_unit_id": u["unit_id"], "old_parent_unit_id": o["parent_unit_id"],
            "new_parent_unit_id": u["parent_unit_id"], "canonical_path_equal": o["canonical_path"] == u["canonical_path"],
            "new_title_selected": True if u["title"] else False,
            "new_own_text_selection": "unselected" if u["unit_type"] in {"document", "chapter", "section"} else "selected_or_confirmed_absent",
            "old_own_text_length": len(o["text_original"]), "old_own_text_sha256": o["text_sha256"],
            "new_own_text_length": len(u["text_original"]), "new_own_text_sha256": u["text_sha256"],
            "old_record_overwritten": False, "resolution": "Independent graph-local ancestor representation; no reparenting or field merge"})
    by_basis = {basis(c, new_units): c for c in new}
    history, deferred = [], []
    for d in rows(base / "deferred.jsonl"):
        u = old_units[d["unit_id"]]; alternate = by_basis.get((u["law_id"], u["canonical_path"]))
        history.append({"base_deferred": d, "draft_disposition": "alternate_source_target_available" if alternate else "carried_forward",
                        "replacement_chunk_id": alternate["chunk_id"] if alternate else None, "old_source_issue_resolved": False})
        if not alternate:
            deferred.append(d)
    stats = {"chunks": len(chunks), "contexts": len(contexts), "source_components": 2,
        "source_unit_representations": len(old_units) + len(new_units), "legal_documents": len(laws),
        "delta": {k: sum(d["status"] == k for d in delta) for k in ["added", "replaced", "removed", "unchanged", "conflicted"]},
        "duplicate_candidates": sum(c["classification"] == "duplicate" for c in comparisons),
        "chunks_by_law": dict(sorted(Counter(c["law_id"] for c in chunks).items())),
        "scope_proposals": dict(sorted(Counter(m["scope_proposal"] for m in metadata).items())),
        "base_deferred": len(history), "deferred": len(deferred), "alternate_source_for_old_deferred": len(history)-len(deferred),
        "source_review": "pending", "technical_review": "pending", "applicability": "pending_review",
        "experimental": True, "release_eligible": False, "corpus_version": None, "human_reviewer_events": 0}
    exports = {"chunks": chunks, "contexts": contexts, "metadata": metadata, "memberships": memberships, "delta": delta,
               "candidate_comparison": comparisons, "unit_crosswalk": unit_cw, "parent_dependencies": parents,
               "deferred": deferred, "deferred_history": history}
    return exports, stats


def render(exports, stats):
    lines = ["# Dataset experimental v2 draft — chưa chuyển bản cho nhóm", "",
        "Base 3.077 chunk vẫn là bản nhóm dùng. Origin=agent_review; source/edition/technical/applicability pending.",
        "Không corpus verified, không index mới; dữ liệu chỉ chứng minh composition kỹ thuật.", "",
        "Hai cây nguồn độc lập: không gộp cha, không chép own text chưa chọn đè DOCX. Proof resolve từ component root theo memberships.jsonl.", "",
        "| Citation | Kết quả | Unit cũ có trong cây | Chunk cũ cùng vị trí | Nội dung cũ khớp |", "|---|---|---|---:|---|"]
    for r in exports["candidate_comparison"]:
        lines.append(f"| {r['citation_path']} | {r['classification']} | {r['legacy_unit_exists']} | {len(r['old_chunk_ids'])} | {r['legacy_text_exact']} |")
    lines += ["", "## Delta", canonical(stats), "", "## Phụ thuộc cha và sparse projection"]
    for r in exports["parent_dependencies"]:
        lines.append(f"- {r['citation_path']}: own text mới={r['new_own_text_selection']}; DOCX cũ {r['old_own_text_length']} code points giữ nguyên. Hai parent ID chỉ resolve trong graph tương ứng.")
    lines += ["", "## Năm Điểm mới — nguyên văn và context"]
    added = {d["new_chunk_id"] for d in exports["delta"] if d["status"] == "added"}
    for c in exports["chunks"]:
        if c["chunk_id"] in added:
            lines += ["", "### " + c["citation_path"], "`" + c["chunk_id"] + "`", "Context Điều → Khoản:", c["context_text"], "Target:", c["text_original"]]
    lines += ["", "## Pending và tác động evaluation", "HTML tải sau snapshot, scan đối chiếu chỉ vùng hẹp. Chưa kết luận applicability/amendments tại2025-01-01 hoặc xác minh toàn nguồn.",
        "Mapping unit cũ→mới không phải mapping chunk thay thế: a/b/c trước chỉ có unit deferred, d/đ chưa có unit/chunk. Không chuyển decisions hoặc tạo qrels positive.",
        "Delta unchanged cho phép đề xuất carry-over ID có kiểm lại binding; query/qrels/index cũ giữ nguyên. Documents mới có thể đổi BM25 IDF/ranking; chưa build/chạy index draft.",
        "Deferred lịch sử được giữ trong base và deferred_history. Chỉ nhánh mới đủ nguồn/context kỹ thuật; issue DOCX cũ chưa resolved. Không thêm chín Điều lá hoặc L35 A86K2.",
        "Loader BM25 v1 không nhận policy draft. Muốn thử bản mới phải có adapter membership/proof và kế hoạch đánh giá/index riêng được cho phép sau."]
    return "\n\n".join(lines) + "\n"


def require_config(cfg):
    if canonical(cfg) != canonical(load(DEFAULT_CONFIG)):
        raise ValueError("Unknown draft scope/bindings; version the explicit config")


def bindings(base, restored, cfg):
    bm = load(base / "dataset_manifest.json")
    if (digest((base / "dataset_manifest.json").read_bytes()) != cfg["base_manifest_sha256"]
            or bm["dataset_version"] != cfg["base_dataset_version"] or bm["dataset_content_sha256"] != cfg["base_content_sha256"]
            or digest((restored / "manifest.json").read_bytes()) != cfg["recovery_manifest_sha256"]):
        raise ValueError("Input version/manifest/content binding mismatch")
    return [{"graph_id": "base-docx", "root_ref": BASE_REF, "manifest_ref": BASE_REF + "/dataset_manifest.json",
             "manifest_sha256": cfg["base_manifest_sha256"], "role": "unchanged_base"},
            {"graph_id": "nd168-html-a16k2", "root_ref": RECOVERY_REF, "manifest_ref": RECOVERY_REF + "/manifest.json",
             "manifest_sha256": cfg["recovery_manifest_sha256"], "role": "sparse_alternate_source"}]


def validate(manifest):
    manifest = Path(manifest).resolve(); root = manifest.parent; m = load(manifest)
    cfg = load(root / "config.json"); require_config(cfg)
    if (m["policy_version"] != VERSION or m["dataset_version"] != cfg["dataset_version"]
            or m["status"] != "draft" or m["snapshot_date"] != SNAPSHOT_DATE or m["experimental"] is not True
            or m["release_eligible"] is not False or m["corpus_version"] is not None or m["origin"] != "agent_review"
            or m["human_reviewer_events"] != 0
            or digest(manifest.read_bytes()) != (root / "dataset_manifest.sha256").read_text().strip()
            or m["code_sha256"] != {p: digest((BASE_DIR / p).read_bytes()) for p in CODE}):
        raise ValueError("Draft manifest/version/status/code mismatch")
    base_dataset.check_inventory(root, m["files"], CONTROL)
    if m["dataset_content_sha256"] != digest(canonical(m["files"]).encode()):
        raise ValueError("Draft content hash mismatch")
    base, restored = root / BASE_REF, root / RECOVERY_REF
    if m["components"] != bindings(base, restored, cfg):
        raise ValueError("Graph/manifest binding mismatch")
    base_dataset.validate(base / "dataset_manifest.json")
    exports, stats = calculate(base, restored)
    for name, expected in exports.items():
        if rows(root / (name + ".jsonl")) != expected:
            raise ValueError("Draft composition/replay mismatch: " + name)
    if m["counts"] != stats or load(root / "dataset_statistics.json") != stats:
        raise ValueError("Draft statistics mismatch")
    if (root / "review.md").read_text(encoding="utf8") != render(exports, stats):
        raise ValueError("Draft readable delta mismatch")
    report = {"technical_valid": True, "status": "draft", "legal_verification": False, "release_eligible": False,
              "replay": "base_validator_and_scoped_html_mapping_builder_with_bound_cached_tokens", "counts": stats}
    if load(root / "validation_report.json") != report:
        raise ValueError("Validation report mismatch")
    return report


def copy_component(origin, target, manifest_name, checksum_name):
    m = load(origin / manifest_name)
    for ref in [f["path"] for f in m["files"]] + [manifest_name, checksum_name]:
        dest = resolve_ref(target, ref); dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(resolve_ref(origin, ref), dest)


def build(config, run_dir):
    cfg = load(config); require_config(cfg); target = staging_path(run_dir)
    base = resolve_ref(BASE_DIR, cfg["base_manifest_ref"]).parent
    restored = resolve_ref(BASE_DIR, cfg["recovery_manifest_ref"]).parent
    components = bindings(base, restored, cfg)
    base_dataset.validate(base / "dataset_manifest.json")
    recovery.validate(restored / "manifest.json")
    exports, stats = calculate(base, restored)  # All conflicts detected before creating output.
    target.mkdir(parents=True)
    copy_component(base, target / BASE_REF, "dataset_manifest.json", "dataset_manifest.sha256")
    copy_component(restored, target / RECOVERY_REF, "manifest.json", "manifest.sha256")
    write_json(target / "config.json", cfg)
    for name, value in exports.items():
        write_rows(target / (name + ".jsonl"), value)
    write_json(target / "dataset_statistics.json", stats)
    (target / "review.md").write_text(render(exports, stats), encoding="utf8", newline="\n")
    write_json(target / "validation_report.json", {"technical_valid": True, "status": "draft", "legal_verification": False,
        "release_eligible": False, "replay": "base_validator_and_scoped_html_mapping_builder_with_bound_cached_tokens", "counts": stats})
    inv = base_dataset.files(target, CONTROL)
    write_json(target / "dataset_manifest.json", {"policy_version": VERSION, "dataset_version": cfg["dataset_version"],
        "snapshot_date": SNAPSHOT_DATE, "status": "draft", "experimental": True, "release_eligible": False,
        "corpus_version": None, "origin": "agent_review", "human_reviewer_events": 0, "components": components,
        "counts": stats, "code_sha256": {p: digest((BASE_DIR / p).read_bytes()) for p in CODE},
        "dataset_content_sha256": digest(canonical(inv).encode()), "files": inv})
    (target / "dataset_manifest.sha256").write_text(digest((target / "dataset_manifest.json").read_bytes()) + "\n", encoding="ascii")
    # Input validation already replayed both graphs; verify the copied inventory now.
    base_dataset.check_inventory(target, inv, CONTROL)
    write_json(target / "execution.json", {"completed_at": datetime.now(timezone.utc).isoformat(),
        "origin": "agent_review", "human_reviewer_events": 0, "tokenization": "recovery_validator_only_no_encoder_inference"})
    return {"technical_valid": True, "counts": stats, "status": "draft", "release_eligible": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build"); b.add_argument("--config", type=Path, default=DEFAULT_CONFIG); b.add_argument("--run-dir", type=Path, required=True)
    v = sub.add_parser("validate"); v.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = build(a.config, a.run_dir) if a.action == "build" else validate(a.manifest)
        print(json.dumps(result, ensure_ascii=False)); return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
