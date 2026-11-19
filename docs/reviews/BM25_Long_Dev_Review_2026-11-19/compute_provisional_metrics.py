"""Compute clearly marked provisional BM25 metrics from proposed known-positive qrels."""

from __future__ import annotations

import json
import math
import statistics
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent


def dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(grades, 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=HERE / "run.jsonl")
    parser.add_argument("--proposals", type=Path, default=HERE / "proposed_positive_judgments.jsonl")
    parser.add_argument("--output", type=Path, default=HERE / "metrics.provisional.json")
    args = parser.parse_args()

    qrels = {}
    for line in args.proposals.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        qrels[row["query_id"]] = {item["chunk_id"]: item["relevance"] for item in row["judgments"]}

    runs: dict[str, list[dict]] = {}
    for line in args.run.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        runs.setdefault(row["query_id"], []).append(row)
    for result_rows in runs.values():
        result_rows.sort(key=lambda row: row["rank"])

    per_query = {}
    for query_id in sorted(set(qrels) & set(runs)):
        judgments = qrels[query_id]
        ranked = [row["chunk_id"] for row in runs[query_id]]
        known_relevant = {chunk_id for chunk_id, grade in judgments.items() if grade > 0}
        first_rank = next((rank for rank, chunk_id in enumerate(ranked, 1) if chunk_id in known_relevant), None)
        top5 = ranked[:5]
        top10 = ranked[:10]
        ideal = sorted(judgments.values(), reverse=True)[:10]
        actual = [judgments.get(chunk_id, 0) for chunk_id in top10]
        per_query[query_id] = {
            "known_relevant_count": len(known_relevant),
            "known_hits_at_5": sum(chunk_id in known_relevant for chunk_id in top5),
            "known_hits_at_10": sum(chunk_id in known_relevant for chunk_id in top10),
            "reciprocal_rank_at_10": (1 / first_rank) if first_rank and first_rank <= 10 else 0.0,
            "ndcg_at_10_known_qrels": (dcg(actual) / dcg(ideal)) if dcg(ideal) else 0.0,
        }

    count = len(per_query)
    report = {
        "status": "PROVISIONAL_DO_NOT_TREAT_AS_ACCEPTED_METRICS",
        "evaluation_version": "bm25-development-evaluation.v1",
        "queries_scored": count,
        "qrels_source": "assistant proposals from visible Top-10 plus phrase-search leads across 3,077 chunks",
        "coverage_complete": False,
        "annotation_accepted": False,
        "limitations": [
            "Proposed relevance labels have not been accepted by Long or a second reviewer.",
            "Full-corpus text sweeps are leads, not proof that all relevant chunks were found.",
            "The corpus manifest says legal_verification=false, experimental=true, release_eligible=false, corpus_version=null.",
            "Recall denominators include only currently known proposed positives, so reported recall is not final recall.",
            "MRR and nDCG also depend on complete qrels and are provisional.",
        ],
        "metrics": {
            "Recall@5_known_positive": round(statistics.fmean(row["known_hits_at_5"] / row["known_relevant_count"] for row in per_query.values() if row["known_relevant_count"]), 6),
            "Recall@10_known_positive": round(statistics.fmean(row["known_hits_at_10"] / row["known_relevant_count"] for row in per_query.values() if row["known_relevant_count"]), 6),
            "MRR@10": round(statistics.fmean(row["reciprocal_rank_at_10"] for row in per_query.values()), 6),
            "nDCG@10": round(statistics.fmean(row["ndcg_at_10_known_qrels"] for row in per_query.values()), 6),
        },
        "per_query": per_query,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "queries_scored": count, "metrics": report["metrics"], "status": report["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
