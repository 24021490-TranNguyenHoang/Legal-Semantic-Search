"""Bounded development evaluation using the existing BM25 loader/search API."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import math
from pathlib import Path
import sys

from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import digest

VERSION = "bm25-development-evaluation.v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    require(isinstance(value, str), "Missing annotation timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed <= datetime.now(timezone.utc),
            "Annotation timestamp must be timezone aware and not future")


def evidence(refs, chunk_ids):
    require(isinstance(refs, list) and bool(refs)
            and all(isinstance(r, str) and
                    (r == "dataset_inventory" or (r.startswith("chunk:") and r[6:] in chunk_ids))
                    for r in refs), "Evidence must reference bound chunks or dataset_inventory")


def validate_queries(queries):
    seen, groups = set(), {}
    require(bool(queries), "Empty query set")
    for q in queries:
        for key in ("query_id", "intent_group_id", "query", "query_type", "topic", "split"):
            require(isinstance(q.get(key), str) and q[key].strip(), f"Missing query field: {key}")
        require(q["query_id"] not in seen, "Duplicate query_id")
        seen.add(q["query_id"])
        require(q["query_type"] in {"direct", "paraphrase", "scenario"}, "Invalid query_type")
        require(q["split"] in {"dev", "test"}, "Invalid split")
        group = q["intent_group_id"]
        require(group not in groups or groups[group] == q["split"], "Intent group leaks across splits")
        groups[group] = q["split"]
    return seen


def validate_records(queries, qrels, annotations, run, outcomes, chunk_ids):
    qids = validate_queries(queries)
    labels, notes, seen, ranks = {}, {}, set(), {}
    for a in annotations:
        key = (a.get("query_id"), a.get("chunk_id"))
        require(key[0] in qids and key[1] in chunk_ids, "Annotation binding mismatch")
        require(key not in notes, "Duplicate annotation; submit a new complete snapshot")
        require(a.get("status") in {"pending", "proposed", "accepted"}, "Invalid annotation status")
        require(a.get("origin") in {"agent", "human"}, "Invalid annotation origin")
        if a["status"] != "pending":
            require(bool(a.get("annotator_ref")) and bool(a.get("reason")) and bool(a.get("evidence_refs")),
                    "Judgment lacks author/reason/evidence")
            timestamp(a.get("recorded_at"))
            evidence(a["evidence_refs"], chunk_ids)
            require(type(a.get("relevance")) is int and a["relevance"] in {0, 1, 2}, "Invalid proposed relevance")
        else:
            require(a.get("relevance") is None, "Pending annotation cannot assert relevance")
        if a["status"] == "accepted":
            require(a["origin"] == "human", "Agent proposal cannot become accepted review")
        notes[key] = a
    for r in qrels:
        key = (r.get("query_id"), r.get("chunk_id"))
        require(key[0] in qids and key[1] in chunk_ids and key not in labels, "Invalid/duplicate qrel binding")
        require(type(r.get("relevance")) is int and r["relevance"] in {0, 1, 2}, "Invalid relevance")
        a = notes.get(key, {})
        require(a.get("status") == "accepted" and a.get("relevance") == r["relevance"],
                "Qrel requires matching accepted annotation")
        labels[key] = r["relevance"]
    require({k for k, a in notes.items() if a["status"] == "accepted"} == set(labels),
            "Accepted annotations and qrels differ")
    for r in run:
        qid, cid = r.get("query_id"), r.get("chunk_id")
        require(qid in qids and cid in chunk_ids, "Run binding mismatch")
        require((qid, cid) not in seen, "Duplicate run result")
        seen.add((qid, cid))
        require(type(r.get("rank")) is int and 1 <= r["rank"] <= 10, "Invalid rank")
        require(type(r.get("score")) in {int, float} and math.isfinite(r["score"]), "Nonfinite score")
        ranks.setdefault(qid, []).append(r)
    require(len(outcomes) == len(qids) and {o["query_id"] for o in outcomes} == qids,
            "Missing/duplicate query outcome")
    for o in outcomes:
        require(o["outcome"] in {"success", "error"}, "Invalid query outcome")
        rs = sorted(ranks.get(o["query_id"], []), key=lambda r: r["rank"])
        require([r["rank"] for r in rs] == list(range(1, len(rs) + 1)), "Non-contiguous/duplicate ranks")
        require(all(a["score"] >= b["score"] for a, b in zip(rs, rs[1:])), "Scores not descending")
        require(o["outcome"] != "error" or (not rs and bool(o.get("error"))), "Invalid error outcome")
    return labels


def metrics(judgments, ranked_ids):
    """Pure metric function; callers ensure judgments are sufficiently reviewed."""
    require(len(ranked_ids) == len(set(ranked_ids)), "Duplicate results")
    positives = {cid for cid, rel in judgments.items() if rel >= 1}
    require(bool(positives), "No positive judgments")
    require(all(cid in judgments for cid in ranked_ids[:10]), "Unjudged result")
    gains = [(2 ** judgments[cid] - 1) / math.log2(i + 2) for i, cid in enumerate(ranked_ids[:10])]
    ideal = sorted(judgments.values(), reverse=True)[:10]
    idcg = sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(ideal))
    return {
        "Recall@5": len(positives.intersection(ranked_ids[:5])) / len(positives),
        "Recall@10": len(positives.intersection(ranked_ids[:10])) / len(positives),
        "MRR@10": next((1 / i for i, cid in enumerate(ranked_ids[:10], 1) if cid in positives), 0),
        "nDCG@10": sum(gains) / idcg,
    }


def evaluate(queries, qrels, annotations, run, outcomes, reviews, chunk_ids):
    labels = validate_records(queries, qrels, annotations, run, outcomes, chunk_ids)
    qids = {q["query_id"] for q in queries}
    require(len(reviews) == len(qids) and {r["query_id"] for r in reviews} == qids, "Missing query review")
    by_review = {r["query_id"]: r for r in reviews}
    for r in reviews:
        require(r.get("status") in {"pending", "accepted"}, "Invalid query review")
        require(r.get("coverage") in {"pending", "answer_present", "corpus_coverage_gap"}, "Invalid coverage")
        if r["status"] == "accepted":
            require(r.get("origin") == "human" and r.get("reviewer_ref") and r.get("reason")
                    and r.get("evidence_refs") and r.get("judgments_complete") is True
                    and r["coverage"] != "pending", "Incomplete query review")
            timestamp(r.get("recorded_at"))
            evidence(r["evidence_refs"], chunk_ids)
    result, excluded = [], []
    for q in queries:
        qid = q["query_id"]
        review = by_review[qid]
        judged = {cid: rel for (qi, cid), rel in labels.items() if qi == qid}
        ranking = [r["chunk_id"] for r in sorted(run, key=lambda r: r["rank"]) if r["query_id"] == qid]
        positive = any(v >= 1 for v in judged.values())
        reason = None
        if review["status"] != "accepted":
            reason = "JUDGMENT_COMPLETENESS_PENDING"
        elif not positive:
            reason = "NO_POSITIVE_CORPUS_COVERAGE_GAP" if review["coverage"] == "corpus_coverage_gap" else "NO_POSITIVE"
        else:
            require(review["coverage"] == "answer_present", "Coverage gap conflicts with positive")
            if any(cid not in judged for cid in ranking):
                reason = "MISSING_TOP10_JUDGMENT"
        if reason:
            excluded.append({"query_id": qid, "reason": reason})
        else:
            result.append({"query_id": qid, **metrics(judged, ranking)})
    aggregate = ({k: sum(r[k] for r in result) / len(result) for k in result[0] if k != "query_id"}
                 if result else None)
    return {"queries_total": len(queries), "queries_eligible": len(result),
            "queries_excluded": len(excluded), "excluded": excluded, "per_query": result,
            "metrics": aggregate, "status": "DEV_METRICS" if result else "PENDING_LABELS",
            "annotation_status": dict(Counter(a["status"] for a in annotations)),
            "errors": [o for o in outcomes if o["outcome"] == "error"],
            "coverage_gaps": [r for r in reviews if r["coverage"] == "corpus_coverage_gap"],
            "coverage_pending": [r["query_id"] for r in reviews if r["coverage"] == "pending"],
            "legal_quality_verified": False}


def binding(path, loaded):
    m = loaded["manifest"]
    return {k: m[k] for k in ("index_version", "index_content_sha256", "dataset_version",
                              "dataset_content_sha256", "dataset_manifest_sha256")} | {
        "index_manifest_sha256": digest(Path(path).read_bytes())}


def new_output(path):
    from src.config import BASE_DIR
    p = Path(path).resolve()
    require((BASE_DIR / "staging").resolve() in p.parents, "Output must be a new run under staging")
    require(not p.exists(), "Output already exists; use a new run")
    p.mkdir(parents=True)
    return p


def seal(root, bound, state, extra=None):
    write_json(root / "manifest.json", {
        "evaluation_version": VERSION, "binding": bound, "state": state,
        "created_at": datetime.now(timezone.utc).isoformat(), "corpus_version": None,
        "evaluation_code_sha256": digest(Path(__file__).read_bytes()),
        "experimental": True, "release_eligible": False,
        "files": {p.name: digest(p.read_bytes()) for p in sorted(root.iterdir()) if p.is_file()},
        **(extra or {})})


def batch(index_manifest, query_path, output):
    from src.bm25_baseline import load_index, search_loaded
    queries = rows(query_path)
    validate_queries(queries)
    require(all(q["split"] == "dev" for q in queries), "This batch is development only")
    query_hash = digest(Path(query_path).read_bytes())
    loaded = load_index(index_manifest)
    root = new_output(output)
    write_rows(root / "queries.jsonl", queries)
    run, outcomes, annotations = [], [], []
    sheet = ["# Phiếu annotation development — chưa có nhãn được chấp nhận",
             "Pool BM25 Top-10 có thiên lệch; cần tìm thêm positive ngoài pool.",
             "Không có đề xuất relevance tự động. Pending không phải nhãn 0.",
             "Căn cứ dưới đây là nội dung dataset pending, không phải kết luận pháp lý.",
             "Evidence source_locator tính tương đối từ dataset/ trong index."]
    for q in queries:
        sheet += [f"\n## {q['query_id']}", q["query"]]
        try:
            answer = search_loaded(loaded, q["query"], 10)
        except Exception as exc:
            outcomes.append({"query_id": q["query_id"], "outcome": "error", "error": str(exc)})
            sheet.append(f"Lỗi truy vấn: {exc}")
            continue
        outcomes.append({"query_id": q["query_id"], "outcome": "success",
                         "search_ms": answer["timings_ms"]["search"], "query_tokens": answer["query_tokens"]})
        for hit in answer["results"]:
            cid = hit["chunk_id"]
            run.append({"query_id": q["query_id"], "chunk_id": cid, "rank": hit["rank"], "score": hit["score"]})
            annotations.append({"query_id": q["query_id"], "chunk_id": cid, "relevance": None,
                                "status": "pending", "origin": "agent", "annotator_ref": None,
                                "recorded_at": None, "reason": None, "evidence_refs": [],
                                "candidate_reason": "BM25_TOP10_POOL_NOT_A_RELEVANCE_PROPOSAL"})
            sheet += [f"\n### Rank {hit['rank']} — {hit['citation_path']}", f"`{cid}`",
                      "Nguyên văn:", hit["text_original"], "\nContext:", hit["context_text"],
                      "\nNguồn target:", hit["source_locator"],
                      "\nNguồn context:", *[c["source_locator"] for c in hit["contexts"]],
                      "\nNhãn [0/1/2]: chưa điền. Lý do/căn cứ/người gán/thời điểm: chưa có.",
                      "Lý do đưa vào phiếu: xuất hiện trong Top-10, chưa phải đề xuất liên quan."]
    reviews = [{"query_id": q["query_id"], "status": "pending", "origin": None, "reviewer_ref": None,
                "recorded_at": None, "judgments_complete": False, "coverage": "pending",
                "reason": None, "evidence_refs": []} for q in queries]
    for name, data in (("run", run), ("outcomes", outcomes), ("annotations", annotations),
                       ("qrels", []), ("query_reviews", reviews)):
        write_rows(root / f"{name}.jsonl", data)
    (root / "annotation_sheet.md").write_text("\n\n".join(sheet) + "\n", encoding="utf8")
    write_json(root / "timings.json", {"load_ms": loaded["load_ms"], "index_load_count": 1,
                                     "warmup_queries": 0, "concurrency": 1,
                                     "runtime": loaded["runtime_compatibility"], "queries": outcomes})
    report = evaluate(queries, [], annotations, run, outcomes, reviews, loaded["chunks"])
    write_json(root / "report.json", report)
    seal(root, binding(index_manifest, loaded), report["status"], {"input_queries_sha256": query_hash})
    return report


def read_bundle(path, loaded, index_manifest):
    root = Path(path).resolve()
    m = load(root / "manifest.json")
    require(m["evaluation_version"] == VERSION and m["binding"] == binding(index_manifest, loaded),
            "Evaluation dataset/index binding mismatch")
    actual = {p.name for p in root.iterdir() if p.is_file()} - {"manifest.json"}
    require(actual == set(m["files"]), "Evaluation file inventory mismatch")
    for name, sha in m["files"].items():
        require(Path(name).name == name and digest((root / name).read_bytes()) == sha, "Evaluation file hash mismatch")
    return root, m


def score_bundle(index_manifest, bundle, submission=None, output=None):
    from src.bm25_baseline import load_index
    loaded = load_index(index_manifest)
    root, manifest = read_bundle(bundle, loaded, index_manifest)
    queries, run, outcomes = (rows(root / f"{n}.jsonl") for n in ("queries", "run", "outcomes"))
    if submission:
        s = load(submission)
        require(s.get("binding") == manifest["binding"]
                and s.get("queries_sha256") == manifest["files"]["queries.jsonl"]
                and s.get("parent_manifest_sha256") == digest((root / "manifest.json").read_bytes()),
                "Submission binding mismatch")
        qrels, annotations, reviews = (s[n] for n in ("qrels", "annotations", "query_reviews"))
    else:
        qrels, annotations, reviews = (rows(root / f"{n}.jsonl") for n in ("qrels", "annotations", "query_reviews"))
    report = evaluate(queries, qrels, annotations, run, outcomes, reviews, loaded["chunks"])
    if output:
        dest = new_output(output)
        for n, v in (("queries", queries), ("run", run), ("outcomes", outcomes),
                     ("qrels", qrels), ("annotations", annotations), ("query_reviews", reviews)):
            write_rows(dest / f"{n}.jsonl", v)
        write_json(dest / "report.json", report)
        if submission:
            write_json(dest / "submission.json", s)
        seal(dest, manifest["binding"], report["status"],
             {"parent_manifest_sha256": digest((root / "manifest.json").read_bytes())})
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("batch")
    b.add_argument("--queries", type=Path, required=True)
    b.add_argument("--run-dir", type=Path, required=True)
    v = sub.add_parser("validate")
    v.add_argument("--bundle", type=Path, required=True)
    s = sub.add_parser("score")
    s.add_argument("--bundle", type=Path, required=True)
    s.add_argument("--submission", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    for cmd in (b, v, s):
        cmd.add_argument("--index-manifest", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.action == "batch":
            result = batch(a.index_manifest, a.queries, a.run_dir)
        else:
            result = score_bundle(a.index_manifest, a.bundle, getattr(a, "submission", None),
                                  getattr(a, "run_dir", None))
        print({k: result[k] for k in ("status", "queries_total", "queries_eligible", "queries_excluded", "metrics")})
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
