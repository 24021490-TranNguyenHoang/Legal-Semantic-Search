"""All-scope experimental export from validated coverage; no legal approval."""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from src.config import BASE_DIR, SNAPSHOT_DATE
from src.source_contracts import canonical, digest, resolve_ref
from src.experimental_dataset import (load, rows, write_json, write_rows, unique,
                                      csv_text, evidence_checks, negative_applicability, trace_checks)

VERSION = "coverage-retrieval-dataset.v1"
DEFAULT_CONFIG = BASE_DIR / "config/retrieval_dataset.v1.json"
CODE = ["src/retrieval_dataset.py", "src/experimental_dataset.py", "src/coverage_survey.py",
        "src/chunk_preview.py", "src/chunk_preview_v2.py", "src/ingestion/legal_tree.py"]


def files(root, excluded):
    return [{"path": p.relative_to(root).as_posix(), "size_bytes": p.stat().st_size,
             "sha256": digest(p.read_bytes())} for p in sorted(root.rglob("*"))
            if p.is_file() and p.relative_to(root).as_posix() not in excluded]


def check_inventory(root, expected, excluded):
    for r in expected:
        resolve_ref(root, r["path"])  # Reject escaping paths, even in a malformed manifest.
    if files(root, excluded) != expected:
        raise ValueError("File inventory/hash/size mismatch: " + str(root))


def check_upstream(path):
    from src.assessment_evidence import check_files
    path = Path(path).resolve()
    m = check_files(path)
    if m["snapshot_date"] != SNAPSHOT_DATE or m["release_eligible"] is not False:
        raise ValueError("Unexpected upstream snapshot/status")
    return m


def require_config(cfg):
    if canonical(cfg) != canonical(load(DEFAULT_CONFIG)):
        raise ValueError("Unknown dataset selection policy/config; version a policy change")


def latest_scope(units, proposals, revisions, coverage_hash, scope_hash):
    by = unique(proposals, "unit_id")
    for p in proposals:
        if (p["unit_id"] not in units or p["unit_sha256"] != digest(canonical(units[p["unit_id"]]).encode())
                or p["binding"]["coverage_manifest_sha256"] != coverage_hash
                or p["reviewer_ref"] is not None or p["reviewed_at"] is not None):
            raise ValueError("Scope proposal unit/hash/coverage binding mismatch")
    unique(revisions, "unit_id")
    for r in revisions:
        p = by[r["unit_id"]]
        if (r["unit_sha256"] != p["unit_sha256"] or r["previous_proposal_id"] != p["proposal_id"]
                or r["previous_proposal_sha256"] != digest(canonical(p).encode())
                or r["binding"]["scope_manifest_sha256"] != scope_hash
                or r["binding"]["tree_binding"] != p["binding"]
                or r["reviewer_ref"] is not None or r["reviewed_at"] is not None):
            raise ValueError("Scope revision/history binding mismatch")
        by[r["unit_id"]] = r
    return by


def exclusions(root, cfg, units, rules, findings):
    excluded = {r["unit_id"]: r for r in negative_applicability(units, rules, findings, SNAPSHOT_DATE)}
    finding = findings[cfg["visual_exception_finding_id"]]
    image = resolve_ref(root, "evidence/" + cfg["visual_exception_image"])
    if (finding["kind"] != "visual_observation" or finding["page"] != 110
            or finding["law_id"] != "168/2024/NĐ-CP"
            or digest(image.read_bytes()) != cfg["visual_exception_image_sha256"]):
        raise ValueError("Visual exception evidence binding mismatch")
    unique(cfg["visual_exceptions"], "unit_id")
    for r in cfg["visual_exceptions"]:
        if (digest(canonical(units[r["unit_id"]]).encode()) != r["unit_sha256"]
                or date.fromisoformat(r["effective_from_candidate"]).isoformat() != r["effective_from_candidate"]):
            raise ValueError("Visual exception unit/hash/date mismatch")
        if SNAPSHOT_DATE < r["effective_from_candidate"]:
            excluded[r["unit_id"]] = {**r, "reason": "OUTSIDE_SNAPSHOT_BY_CAPTURED_VISUAL_EVIDENCE",
                "explanation": r["reason"], "finding_id": finding["finding_id"],
                "evidence_id": finding["evidence_id"], "page": 110,
                "image_ref": "evidence/" + cfg["visual_exception_image"], "origin": "agent_review",
                "reviewer_decision": None, "assessment_created": False}
    return excluded


def calculate(root):
    # Importing/searching BM25 never imports encoder modules. Export validation
    # reuses the existing builder with measured, hash-bound token evidence only.
    from src.coverage_survey import execute_batches
    cfg = load(root / "packaging_config.json"); require_config(cfg)
    laws = load(root / "support/laws.json")
    units = unique([u for d in laws.values() for u in d["units"]], "unit_id")
    binding = load(root / "input_binding.json")
    scope = latest_scope(units, rows(root / "support/scope_proposals.jsonl"),
                         rows(root / "support/scope_revisions.jsonl"),
                         binding["coverage_manifest_sha256"], binding["scope_manifest_sha256"])
    enc = rows(root / "support/encoder_evidence.jsonl")
    unique(enc, "unit_id"); lookup = unique(enc, "input_sha256")
    for e in enc:
        if (e["truncation"] is not False or e["tokens_with_special"] != len(e["token_ids"])
                or e["token_ids_sha256"] != digest(canonical(e["token_ids"]).encode())
                or e["unknown_tokens"] != e["token_ids"].count(3)):
            raise ValueError("Encoder token evidence count/hash mismatch")
    combined = {k: [] for k in ["chunks", "contexts", "quarantined", "issues", "execution_errors"]}
    chunk_cfg = load(root / "chunk_config.json")
    if chunk_cfg["token_limit"] != 256 or chunk_cfg["chunk_policy_version"] != "leaf-clause-point-context.v1":
        raise ValueError("Existing builder/budget must remain unchanged")
    for data in laws.values():
        result = execute_batches(data, root / "inputs", chunk_cfg,
                                 lambda texts: [lookup[digest(t.encode())] for t in texts])
        for k in combined: combined[k].extend(result[k])
    if combined["execution_errors"]:
        raise ValueError("Builder replay execution error: " + canonical(combined["execution_errors"]))
    all_chunks = sorted(combined["chunks"], key=lambda c: c["chunk_id"])
    all_contexts = sorted(combined["contexts"], key=lambda c: (c["chunk_id"], c["context_order"]))
    if (digest(canonical(all_chunks).encode()) != binding["preview_chunks_sha256"]
            or digest(canonical(all_contexts).encode()) != binding["preview_contexts_sha256"]
            or sorted(combined["quarantined"], key=lambda q: q["candidate"]["chunk_id"]) != rows(root / "support/quarantined.jsonl")):
        raise ValueError("Upstream chunk/context/quarantine replay mismatch")
    trace_checks(root, unique(all_chunks, "chunk_id"), all_contexts)
    rules, findings = evidence_checks(root)
    negative = exclusions(root, cfg, units, rules, findings)
    coverage = unique(rows(root / "support/unit_coverage.jsonl"), "unit_id")
    if set(coverage) != set(units): raise ValueError("Incomplete coverage units")
    selected, deferred, metadata = [], [], []
    for c in all_chunks:
        contexts = [x for x in all_contexts if x["chunk_id"] == c["chunk_id"]]
        used = {c["unit_id"]} | {x["unit_id"] for x in contexts}
        reasons = [negative[u] for u in sorted(used & negative.keys())]
        if reasons:
            deferred.append({"unit_id": c["unit_id"], "law_id": c["law_id"], "citation_path": c["citation_path"],
                             "reason": "APPLICABILITY_EVIDENCE", "evidence": reasons})
        else:
            selected.append(c)
            p = scope.get(c["unit_id"])
            metadata.append({"chunk_id": c["chunk_id"], "unit_id": c["unit_id"],
                             "unit_sha256": digest(canonical(units[c["unit_id"]]).encode()),
                             "scope_proposal": p["scope_candidate"] if p else "pending",
                             "scope_proposal_id": p["proposal_id"] if p else None,
                             "scope_reason": p["reason"] if p else "Not assessed",
                             "source_status": "pending", "technical_review": "pending", "applicability": "pending_review",
                             "origin": "agent_review", "reviewer_decision": None, "experimental": True, "release_eligible": False})
    for r in coverage.values():
        if r["unit_sha256"] != digest(canonical(units[r["unit_id"]]).encode()):
            raise ValueError("Coverage unit hash mismatch")
        if r["status"] not in {"preview_available", "context_only"}:
            deferred.append({"unit_id": r["unit_id"], "law_id": r["law_id"], "citation_path": r["citation_path"],
                             "reason": r["status"], "evidence": r["reasons"]})
    cids = {c["chunk_id"] for c in selected}
    contexts = [x for x in all_contexts if x["chunk_id"] in cids]
    if len(cids) != len(selected): raise ValueError("Duplicate dataset chunk")
    stats = {"input_units": len(units), "input_preview_chunks": len(all_chunks), "chunks": len(selected),
             "contexts": len(contexts), "context_only": sum(r["status"] == "context_only" for r in coverage.values()),
             "chunks_by_law": dict(sorted(Counter(c["law_id"] for c in selected).items())),
             "scope_proposals": dict(sorted(Counter(m["scope_proposal"] for m in metadata).items())),
             "deferred": len(deferred), "deferred_reasons": dict(Counter(d["reason"] for d in deferred)),
             "source_gap_records": len(rows(root / "source_gaps.jsonl")), "experimental": True,
             "release_eligible": False, "source_review": "pending", "technical_review": "pending",
             "applicability_review": "pending_review", "corpus_version": None}
    return selected, contexts, sorted(metadata, key=lambda m: m["chunk_id"]), sorted(deferred, key=lambda d: d["unit_id"]), stats


def validate(manifest):
    manifest = Path(manifest).resolve(); root = manifest.parent; m = load(manifest)
    if (m["policy_version"] != VERSION or m["snapshot_date"] != SNAPSHOT_DATE
            or m["experimental"] is not True or m["release_eligible"] is not False or m["corpus_version"] is not None
            or digest(manifest.read_bytes()) != (root / "dataset_manifest.sha256").read_text().strip()):
        raise ValueError("Dataset manifest identity/status/hash mismatch")
    check_inventory(root, m["files"], {"dataset_manifest.json", "dataset_manifest.sha256", "execution.json"})
    if m["dataset_content_sha256"] != digest(canonical(m["files"]).encode()): raise ValueError("Dataset content hash mismatch")
    if m["code_sha256"] != {p: digest((BASE_DIR / p).read_bytes()) for p in CODE}:
        raise ValueError("Dataset validator/builder version changed")
    chunks, contexts, metadata, deferred, stats = calculate(root)
    for name, expected in [("chunks.jsonl", chunks), ("contexts.jsonl", contexts), ("metadata.jsonl", metadata), ("deferred.jsonl", deferred)]:
        if rows(root / name) != expected: raise ValueError("Dataset replay mismatch: " + name)
    if (load(root / "dataset_statistics.json") != stats or m["counts"] != stats
            or (root / "deferred.csv").read_text(encoding="utf8") != csv_text(deferred, ["law_id", "unit_id", "citation_path", "reason", "evidence"])):
        raise ValueError("Statistics/deferred export mismatch")
    return {"technical_valid": True, "counts": stats, "legal_verification": False, "release_eligible": False}


def build(coverage_manifest, scope_manifest, refinement_manifest, run_dir, config=DEFAULT_CONFIG):
    from src.coverage_survey import validate as validate_coverage, load_data
    from src.pipeline_cli import staging_path
    target = staging_path(run_dir); cfg = load(config); require_config(cfg)
    paths = [Path(p).resolve() for p in [coverage_manifest, scope_manifest, refinement_manifest]]
    if any(p.parent == target or p.parent in target.parents for p in paths): raise ValueError("Output inside sealed input")
    validate_coverage(paths[0])
    for p in paths[1:]: check_upstream(p)
    cov, scope, refinement = [p.parent for p in paths]
    if (digest((scope / "coverage_snapshot/manifest.json").read_bytes()) != digest(paths[0].read_bytes())
            or digest((refinement / "scope_snapshot/manifest.json").read_bytes()) != digest(paths[1].read_bytes())):
        raise ValueError("Different scope/refinement/coverage inputs")
    laws, _ = load_data(cov)
    target.mkdir(parents=True)
    def copy(origin, ref):
        dest = resolve_ref(target, ref); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(origin, dest)
    for folder in ["support", "evidence/pages"]: (target / folder).mkdir(parents=True, exist_ok=True)
    write_json(target / "packaging_config.json", cfg); write_json(target / "support/laws.json", laws)
    write_json(target / "chunk_config.json", load(cov / "config.json")["chunk"])
    for origin, ref in [(scope / "scope_proposals.jsonl", "support/scope_proposals.jsonl"),
                        (refinement / "scope_proposal_revisions.jsonl", "support/scope_revisions.jsonl"),
                        (cov / "source_gaps.jsonl", "source_gaps.jsonl"), (cov / "encoder_config.json", "encoder_config.json")]: copy(origin, ref)
    write_rows(target / "support/unit_coverage.jsonl", [{k: r[k] for k in ["unit_id", "unit_sha256", "law_id", "citation_path", "status", "reasons"]} for r in rows(cov / "unit_coverage.jsonl")])
    encoder = rows(cov / "preview/encoder_inputs.preview.jsonl")
    write_rows(target / "support/encoder_evidence.jsonl", [{**{k: e[k] for k in ["unit_id", "input_sha256", "model_max_tokens", "tokens_with_special", "unknown_tokens", "truncation", "preprocessing_version", "encoder_text_sha256"]},
                "token_ids": e["after"]["token_ids"], "token_ids_sha256": e["after"]["token_ids_sha256"]} for e in encoder])
    write_rows(target / "support/quarantined.jsonl", sorted(rows(cov / "preview/quarantined.preview.jsonl"), key=lambda q: q["candidate"]["chunk_id"]))
    for d in laws.values():
        for f in d["files"]: copy(cov / "inputs" / f["raw_file_ref"], "inputs/" + f["raw_file_ref"])
        for e in d["extractions"]: copy(cov / "inputs" / e["text_ref"], "inputs/" + e["text_ref"])
    base = cov / "inputs/tree/extraction_snapshot"
    records = rows(base / "extractions.pending.jsonl"); write_rows(target / "support/extraction_records.jsonl", records)
    for r in records: copy(base / r["trace_ref"], "inputs/tree/extraction_snapshot/" + r["trace_ref"])
    for name in ["documents.pending.jsonl", "files.pending.jsonl"]: copy(base / "source_snapshot" / name, "support/" + name)
    assessment = cov / "inputs/assessment"
    findings = rows(assessment / "evidence_findings.pending.jsonl")
    rules = rows(assessment / "date_rules.pending.jsonl")
    # Existing evidence only; no network fetch, invented retrieval date or human decision.
    write_rows(target / "evidence/findings.pending.jsonl", findings); write_rows(target / "evidence/date_rules.pending.jsonl", rules)
    catalog = []
    for e in rows(assessment / "evidence.jsonl"):
        if e["evidence_id"] not in {f["evidence_id"] for f in findings}: continue
        ref = "evidence/captures/" + e["artifact_ref"]; copy(assessment / "evidence_snapshot" / e["artifact_ref"], ref)
        catalog.append({k: e[k] for k in ["evidence_id", "law_id", "url", "accessed_at", "kind", "sha256", "size_bytes"]} | {"artifact_ref": ref, "review_status": "pending"})
    write_rows(target / "evidence/catalog.jsonl", catalog)
    for f in findings:
        if f["kind"] == "text_slice": copy(assessment / "evidence_snapshot" / f["text_ref"], "evidence/pages/" + f["text_ref"])
    copy(assessment / "evidence_pages" / cfg["visual_exception_image"], "evidence/" + cfg["visual_exception_image"])
    binding = {name + "_manifest_sha256": digest(p.read_bytes()) for name, p in zip(["coverage", "scope", "refinement"], paths)}
    for name in ["chunks", "contexts"]:
        binding["preview_" + name + "_sha256"] = digest(canonical(rows(cov / ("preview/" + name + ".preview.jsonl"))).encode())
    write_json(target / "input_binding.json", binding)
    chunks, contexts, metadata, deferred, stats = calculate(target)
    for name, value in [("chunks", chunks), ("contexts", contexts), ("metadata", metadata), ("deferred", deferred)]: write_rows(target / (name + ".jsonl"), value)
    (target / "deferred.csv").write_text(csv_text(deferred, ["law_id", "unit_id", "citation_path", "reason", "evidence"]), encoding="utf8", newline="\n")
    write_json(target / "dataset_statistics.json", stats)
    write_json(target / "validation_report.json", {"technical_valid": True, "legal_verification": False, "experimental": True, "release_eligible": False, "replay": "unchanged_builder_with_bound_encoder_evidence", "counts": stats})
    inv = files(target, {"dataset_manifest.json", "dataset_manifest.sha256", "execution.json"})
    write_json(target / "dataset_manifest.json", {"policy_version": VERSION, "dataset_version": cfg["dataset_version"], "snapshot_date": SNAPSHOT_DATE,
               "experimental": True, "release_eligible": False, "corpus_version": None, "input_binding": binding,
               "counts": stats, "code_sha256": {p: digest((BASE_DIR / p).read_bytes()) for p in CODE},
               "dataset_content_sha256": digest(canonical(inv).encode()), "files": inv})
    (target / "dataset_manifest.sha256").write_text(digest((target / "dataset_manifest.json").read_bytes()) + "\n", encoding="ascii")
    validate(target / "dataset_manifest.json")
    write_json(target / "execution.json", {"completed_at": datetime.now(timezone.utc).isoformat(), "origin": "agent_review", "human_reviewer_events": 0})
    return stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build")
    for name in ["coverage-manifest", "scope-manifest", "refinement-manifest", "run-dir"]: b.add_argument("--" + name, required=True, type=Path)
    b.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    v = sub.add_parser("validate"); v.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = validate(a.manifest) if a.action == "validate" else build(a.coverage_manifest, a.scope_manifest, a.refinement_manifest, a.run_dir, a.config)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
