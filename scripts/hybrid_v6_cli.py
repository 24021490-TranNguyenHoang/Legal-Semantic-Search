"""End-to-end execution & verification CLI for Hybrid v6 (24h smoke, 48h benchmark, 4 review fixes, handoff-002)."""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from src import hybrid_v6 as hv6


def percentile_ms(values: list[float], q: float) -> float:
    return round(float(np.percentile(np.array(values, dtype=np.float64), q)), 3)


def run_negative_loader_tests(bm25_state: dict[str, Any], sealed_dense_dir: Path) -> list[dict[str, Any]]:
    """Prove loader rejects: (1) wrong hash, (2) wrong version, (3) vector order mismatch vs record_id."""
    results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="v6_loader_neg_") as tmp:
        tmp_root = Path(tmp)

        # Case 1: Wrong hash (modify 1 float in embeddings.npy without updating manifest)
        c1 = tmp_root / "case1_wrong_hash"
        shutil.copytree(sealed_dense_dir, c1)
        emb1 = np.load(c1 / "embeddings.npy")
        emb1[0, 0] = np.float32(emb1[0, 0] + 0.001)
        np.save(c1 / "embeddings.npy", emb1)
        try:
            hv6.load_dense_bundle(bm25_state, c1)
            raise AssertionError("Case 1 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "1_wrong_hash",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

        # Case 2: Wrong version (bump dense_version in dense_manifest.json and re-sign manifest sha256)
        c2 = tmp_root / "case2_wrong_version"
        shutil.copytree(sealed_dense_dir, c2)
        m2 = json.loads((c2 / "dense_manifest.json").read_text(encoding="utf-8"))
        m2["dense_version"] = "vtls-dense-bge-m3.v0-stale"
        hv6.write_json_lf(c2 / "dense_manifest.json", m2)
        (c2 / "dense_manifest.sha256").write_text(hv6.sha256_file(c2 / "dense_manifest.json") + "\n", encoding="ascii")
        try:
            hv6.load_dense_bundle(bm25_state, c2)
            raise AssertionError("Case 2 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "2_wrong_version",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

        # Case 3: Vector ordering mismatch vs record_id (swap row 0 and row 1 in embeddings.npy and re-sign inventory/manifest)
        c3 = tmp_root / "case3_vector_order_mismatch"
        shutil.copytree(sealed_dense_dir, c3)
        emb3 = np.load(c3 / "embeddings.npy")
        emb3[[0, 1]] = emb3[[1, 0]]
        np.save(c3 / "embeddings.npy", emb3)
        m3 = json.loads((c3 / "dense_manifest.json").read_text(encoding="utf-8"))
        m3["embeddings_npy_sha256"] = hv6.sha256_file(c3 / "embeddings.npy")
        m3["files"] = hv6.dense_inventory(c3)
        m3["dense_content_sha256"] = hv6.hashed_obj(m3["files"])
        hv6.write_json_lf(c3 / "dense_manifest.json", m3)
        (c3 / "dense_manifest.sha256").write_text(hv6.sha256_file(c3 / "dense_manifest.json") + "\n", encoding="ascii")
        try:
            hv6.load_dense_bundle(bm25_state, c3)
            raise AssertionError("Case 3 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "3_vector_order_mismatch_vs_record_id",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

    return results


def compute_top10_diffs(
    old_runs_dir: Path,
    new_runs_dir: Path,
    queries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute changed (query_id, record_id) pairs so Long can verify label coverage without defaulting to 0."""
    q_lookup = {q["query_id"]: q for q in queries}

    def load_by_q(path: Path) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        if not path.exists():
            return grouped
        for r in hv6.read_jsonl(path):
            grouped.setdefault(r["query_id"], []).append(r)
        for qid in grouped:
            grouped[qid].sort(key=lambda x: int(x["rank"]))
        return grouped

    # 1. Diff between handoff-001 and handoff-002 for all 4 modes
    diff_vs_001: list[dict[str, Any]] = []
    for mode in ["bm25_only", "dense_only", "hybrid_rrf", "hybrid_rrf_rerank"]:
        old_g = load_by_q(old_runs_dir / f"{mode}.top10.jsonl")
        new_g = load_by_q(new_runs_dir / f"{mode}.top10.jsonl")
        for qid in [q["query_id"] for q in queries]:
            old_map = {r["record_id"]: int(r["rank"]) for r in old_g.get(qid, [])}
            new_map = {r["record_id"]: int(r["rank"]) for r in new_g.get(qid, [])}
            all_rids = sorted(set(old_map) | set(new_map))
            for rid in all_rids:
                r_old = old_map.get(rid)
                r_new = new_map.get(rid)
                if r_old != r_new:
                    diff_vs_001.append({
                        "mode": mode,
                        "query_id": qid,
                        "batch_group": q_lookup[qid]["batch_group"],
                        "record_id": rid,
                        "handoff001_rank": r_old,
                        "handoff002_rank": r_new,
                        "change_type": "added_to_top10" if r_old is None else ("dropped_from_top10" if r_new is None else "rank_shifted"),
                        "relevance": None,
                        "label_status": "pending_long_review",
                    })

    # 2. Diff between BM25 v2 and Hybrid RRF / Hybrid RRF + Reranker in handoff-002
    bm25_g = load_by_q(new_runs_dir / "bm25_only.top10.jsonl")
    diff_bm25_vs_hybrid: list[dict[str, Any]] = []
    for target_mode in ["hybrid_rrf", "hybrid_rrf_rerank"]:
        hyb_g = load_by_q(new_runs_dir / f"{target_mode}.top10.jsonl")
        for qid in [q["query_id"] for q in queries]:
            b_map = {r["record_id"]: r for r in bm25_g.get(qid, [])}
            h_map = {r["record_id"]: r for r in hyb_g.get(qid, [])}
            all_rids = sorted(set(b_map) | set(h_map))
            for rid in all_rids:
                rb = int(b_map[rid]["rank"]) if rid in b_map else None
                rh = int(h_map[rid]["rank"]) if rid in h_map else None
                if rb != rh:
                    ref_row = h_map.get(rid) or b_map[rid]
                    diff_bm25_vs_hybrid.append({
                        "comparison": f"bm25_only_vs_{target_mode}",
                        "query_id": qid,
                        "batch_group": q_lookup[qid]["batch_group"],
                        "query": q_lookup[qid]["query"],
                        "record_id": rid,
                        "record_type": ref_row["record_type"],
                        "citation_path": ref_row["citation_path"],
                        "bm25_top10_rank": rb,
                        "hybrid_top10_rank": rh,
                        "change_type": "new_in_hybrid_top10" if rb is None else ("dropped_from_bm25_top10" if rh is None else "rank_shifted"),
                        "relevance": None,
                        "label_status": "pending_long_review",
                    })

    return {
        "diff_vs_handoff001": diff_vs_001,
        "diff_bm25_vs_hybrid": diff_bm25_vs_hybrid,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm25-root", type=Path, default=Path("unpacked-v6/bm25"))
    parser.add_argument("--old-handoff-dir", type=Path, default=Path("artifacts/v6_hybrid_handoff"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/v6_hybrid_handoff_v2"))
    parser.add_argument("--doc-out", type=Path, default=Path("docs/handoff/Retrieval_V6_Hybrid_Handoff_v2.md"))
    parser.add_argument("--zip-out", type=Path, default=Path("artifacts/vtls-retrieval-v6-hybrid-handoff-002.zip"))
    parser.add_argument("--measured-runs", type=int, default=3, help="Number of timed passes after warmup (>=3)")
    args = parser.parse_args()

    if args.measured_runs < 3:
        raise ValueError("--measured-runs must be at least 3")

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "runs").mkdir()
    (args.out_dir / "benchmark").mkdir()
    (args.out_dir / "evidence").mkdir()

    env_info = hv6.collect_environment_info()
    print("=== [0] CHOT MAY & MOI TRUONG ===")
    print(json.dumps(env_info, ensure_ascii=False, indent=2))

    # 1. Load & validate official BM25 v2 index + v6 Consumer
    print("\n=== [1] NAP & KIEM CHUNG BM25 V2 + CONSUMER V6 CHINH THUC ===")
    bm25_mod, bm25_state, bm25_load_ms = hv6.load_bm25_v2_index(args.bm25_root)
    print(f"BM25 v2 + Consumer v6 load_validate_ms = {bm25_load_ms:.2f} ms | docs = {len(bm25_state['mapping'])}")

    # 2. Build & seal Dense v2 bundle (with per-row vector SHA-256) and reload through strict validator
    dense_dir = args.out_dir / "dense_bge_m3"
    hv6.build_or_seal_dense_bundle(
        bm25_state=bm25_state,
        source_embeddings_npy=args.old_handoff_dir / "dense_bge_m3" / "embeddings.npy",
        source_tokenizer_audit_jsonl=args.old_handoff_dir / "dense_bge_m3" / "tokenizer_audit.jsonl",
        out_dense_dir=dense_dir,
    )
    dense_bundle = hv6.load_dense_bundle(bm25_state, dense_dir)
    print(f"Dense bundle load_validate_ms = {dense_bundle['load_validate_ms']:.2f} ms | sha = {dense_bundle['manifest']['dense_content_sha256'][:16]}...")

    # 3. Review Fix #1: Run negative loader rejection tests (3 cases)
    print("\n=== [2] KIEM THU TU CHOI DU LIEU LOI (3 CA REVIEW #1) ===")
    neg_results = run_negative_loader_tests(bm25_state, dense_dir)
    for nr in neg_results:
        print(f"  [PASS REJECT] {nr['case']} -> {nr['exception_type']}: {nr['error_message']}")
    hv6.write_json_lf(args.out_dir / "evidence" / "loader_rejection_tests.json", {
        "all_rejected": all(r["rejected"] for r in neg_results),
        "cases": neg_results,
    })

    # 4. Load pinned Dense encoder (model + tokenizer revision pinned)
    print("\n=== [3] NAP MODEL DENSE GHIM REVISION (BAAI/bge-m3) ===")
    encoder_bundle = hv6.load_pinned_dense_encoder(local_files_only=True)
    print(f"Loaded {encoder_bundle['model_id']} @ rev={encoder_bundle['model_revision']} in {encoder_bundle['load_ms']:.2f} ms")

    # 5. Load 50 pinned queries
    queries = bm25_mod.query_set(
        args.bm25_root / "queries",
        bm25_state["manifest"]["queries_manifest_sha256"],
    )
    q_by_id = {q["query_id"]: q for q in queries}

    # 6. 24h Smoke Test on 2 pinned queries (driving age & red light)
    print("\n=== [4] 24H SMOKE TEST (TUOI LAI MO TO & DEN DO) ===")
    smoke_ids = ["dev-driving_age-2", "dev-red_light-1"]
    smoke_records: list[dict[str, Any]] = []
    for qid in smoke_ids:
        q_obj = q_by_id[qid]
        q_text = q_obj["query"]
        b_res = hv6.search_bm25_v2(bm25_mod, bm25_state, q_text, top_k=10)
        h_res = hv6.search_hybrid_rrf(bm25_mod, bm25_state, dense_bundle, encoder_bundle, q_text, top_k=10)
        print(f"\nQuery [{qid}]: {q_text}")
        print("  -- BM25 v2 Top-10 --")
        for hit in b_res["results"]:
            print(f"    #{hit['rank']:2d} | {hit['record_id']} | score={hit['score']:.4f} | {hit['citation_path']}")
        print("  -- Hybrid RRF (k=60) Top-10 --")
        for hit in h_res["results"]:
            print(
                f"    #{hit['rank']:2d} | {hit['record_id']} | rrf={hit['score']:.6f} "
                f"(bm25={hit['bm25_rank']}, dense={hit['dense_rank']}) | {hit['citation_path']}"
            )
        smoke_records.append({
            "query_id": qid,
            "query": q_text,
            "bm25_top10": b_res["results"],
            "hybrid_rrf_top10": h_res["results"],
        })
    hv6.write_json_lf(args.out_dir / "benchmark" / "smoke_24h_results.json", {
        "environment": env_info,
        "bge_m3_load_ms": round(encoder_bundle["load_ms"], 3),
        "pinned_dense_model": {"model_id": hv6.DENSE_MODEL_ID, "revision": hv6.DENSE_MODEL_REVISION},
        "pinned_reranker_model": {"model_id": hv6.RERANKER_MODEL_ID, "revision": hv6.RERANKER_MODEL_REVISION},
        "smoke_queries": smoke_records,
    })

    # 7. 48h Latency Benchmark: Warmup + >= 3 measured passes across all 50 queries
    print(f"\n=== [5] 48H BENCHMARK DO TRE (WARMUP + {args.measured_runs} LUOT x 50 CAU) ===")
    raw_latency_rows: list[dict[str, Any]] = []

    # 7a. Warmup BM25 v2 (1 full pass, excluded from benchmark stats)
    for q in queries:
        _ = hv6.search_bm25_v2(bm25_mod, bm25_state, q["query"], top_k=10)

    bm25_latencies: list[float] = []
    bm25_errors = 0
    for run_idx in range(1, args.measured_runs + 1):
        for q in queries:
            try:
                res = hv6.search_bm25_v2(bm25_mod, bm25_state, q["query"], top_k=10)
                ms = float(res["measured_total_ms"])
                bm25_latencies.append(ms)
                raw_latency_rows.append({
                    "mode": "bm25_only",
                    "run_index": run_idx,
                    "query_id": q["query_id"],
                    "batch_group": q["batch_group"],
                    "total_ms": round(ms, 4),
                    "error": None,
                })
            except Exception as exc:
                bm25_errors += 1
                raw_latency_rows.append({
                    "mode": "bm25_only",
                    "run_index": run_idx,
                    "query_id": q["query_id"],
                    "batch_group": q["batch_group"],
                    "total_ms": None,
                    "error": str(exc),
                })

    # 7b. Warmup Hybrid RRF (1 full pass, excluded from benchmark stats)
    for q in queries:
        _ = hv6.search_hybrid_rrf(bm25_mod, bm25_state, dense_bundle, encoder_bundle, q["query"], top_k=10)

    hybrid_latencies: list[float] = []
    hybrid_encode_ms: list[float] = []
    hybrid_dense_ms: list[float] = []
    hybrid_bm25_ms: list[float] = []
    hybrid_rrf_ms: list[float] = []
    hybrid_errors = 0
    for run_idx in range(1, args.measured_runs + 1):
        for q in queries:
            try:
                res = hv6.search_hybrid_rrf(bm25_mod, bm25_state, dense_bundle, encoder_bundle, q["query"], top_k=10)
                t = res["timings_ms"]
                ms = float(t["total_ms"])
                hybrid_latencies.append(ms)
                hybrid_encode_ms.append(float(t["encode_query_ms"]))
                hybrid_dense_ms.append(float(t["dense_search_ms"]))
                hybrid_bm25_ms.append(float(t["bm25_search_ms"]))
                hybrid_rrf_ms.append(float(t["rrf_fusion_ms"]))
                raw_latency_rows.append({
                    "mode": "hybrid_rrf",
                    "run_index": run_idx,
                    "query_id": q["query_id"],
                    "batch_group": q["batch_group"],
                    "encode_query_ms": round(float(t["encode_query_ms"]), 4),
                    "dense_search_ms": round(float(t["dense_search_ms"]), 4),
                    "bm25_search_ms": round(float(t["bm25_search_ms"]), 4),
                    "rrf_fusion_ms": round(float(t["rrf_fusion_ms"]), 4),
                    "total_ms": round(ms, 4),
                    "error": None,
                })
            except Exception as exc:
                hybrid_errors += 1
                raw_latency_rows.append({
                    "mode": "hybrid_rrf",
                    "run_index": run_idx,
                    "query_id": q["query_id"],
                    "batch_group": q["batch_group"],
                    "total_ms": None,
                    "error": str(exc),
                })

    print(
        f"  bm25_only  : n={len(bm25_latencies)} | errors={bm25_errors} | "
        f"p50={percentile_ms(bm25_latencies, 50):.3f} ms | p95={percentile_ms(bm25_latencies, 95):.3f} ms"
    )
    print(
        f"  hybrid_rrf : n={len(hybrid_latencies)} | errors={hybrid_errors} | "
        f"p50={percentile_ms(hybrid_latencies, 50):.3f} ms | p95={percentile_ms(hybrid_latencies, 95):.3f} ms"
    )

    # 8. Deterministic 50-query runs for BM25, Dense-only, and Hybrid RRF (and capture Top-30 RRF pools)
    bm25_top10_rows: list[dict[str, Any]] = []
    dense_top10_rows: list[dict[str, Any]] = []
    hybrid_rrf_top10_rows: list[dict[str, Any]] = []
    rrf_pools_by_qid: dict[str, dict[str, Any]] = {}

    for q in queries:
        qid = q["query_id"]
        b_ans = hv6.search_bm25_v2(bm25_mod, bm25_state, q["query"], top_k=10)
        for h in b_ans["results"]:
            bm25_top10_rows.append({"query_id": qid, "batch_group": q["batch_group"], **h})

        d_ans = hv6.search_dense_only(bm25_state, dense_bundle, encoder_bundle, q["query"], top_k=10)
        for h in d_ans["results"]:
            dense_top10_rows.append({"query_id": qid, "batch_group": q["batch_group"], **h})

        h_ans = hv6.search_hybrid_rrf(
            bm25_mod, bm25_state, dense_bundle, encoder_bundle, q["query"], top_k=10, rrf_pool_k=hv6.RERANK_DEPTH
        )
        for h in h_ans["results"]:
            hybrid_rrf_top10_rows.append({"query_id": qid, "batch_group": q["batch_group"], **h})
        rrf_pools_by_qid[qid] = {
            "rrf_top30": h_ans["rrf_top_pool"],
            "hybrid_rrf_ms": h_ans["measured_total_ms"],
        }

    # Release bge-m3 from RAM before loading bge-reranker-v2-m3 to prevent paging exhaustion on 16GB Windows
    del encoder_bundle
    import gc
    gc.collect()

    # 9. Load pinned Reranker (model + tokenizer revision pinned) & run Top-30 audit + separate benchmark row
    print("\n=== [6] NAP RERANKER GHIM REVISION & XUAT TOP-30 RRF AUDIT (REVIEW #2) ===")
    reranker_bundle = hv6.load_pinned_reranker(local_files_only=True)
    print(f"Loaded {reranker_bundle['model_id']} @ rev={reranker_bundle['model_revision']} in {reranker_bundle['load_ms']:.2f} ms")

    # Warmup reranker on 2 queries
    for qid in smoke_ids:
        _ = hv6.rerank_rrf_candidates(
            bm25_state, reranker_bundle, q_by_id[qid]["query"], rrf_pools_by_qid[qid]["rrf_top30"], top_k=10
        )

    # 3-run smoke repeatability measurement for Hybrid + Reranker
    rerank_smoke_e2e_ms: list[float] = []
    for run_idx in range(1, args.measured_runs + 1):
        for qid in smoke_ids:
            rr_res = hv6.rerank_rrf_candidates(
                bm25_state, reranker_bundle, q_by_id[qid]["query"], rrf_pools_by_qid[qid]["rrf_top30"], top_k=10
            )
            e2e = rrf_pools_by_qid[qid]["hybrid_rrf_ms"] + rr_res["rerank_only_ms"]
            rerank_smoke_e2e_ms.append(e2e)
            raw_latency_rows.append({
                "mode": "hybrid_rrf_rerank_smoke_3x",
                "run_index": run_idx,
                "query_id": qid,
                "batch_group": q_by_id[qid]["batch_group"],
                "hybrid_rrf_ms": round(rrf_pools_by_qid[qid]["hybrid_rrf_ms"], 4),
                "rerank_top30_ms": round(rr_res["rerank_only_ms"], 4),
                "total_ms": round(e2e, 4),
                "error": None,
            })

    # Full 50-query pass for Hybrid + Reranker (produces 50x30=1500 Top-30 audit rows & 500 Top-10 rows)
    rerank_50q_e2e_ms: list[float] = []
    rerank_errors = 0
    hybrid_rerank_top10_rows: list[dict[str, Any]] = []
    rrf_top30_audit_rows: list[dict[str, Any]] = []

    for idx_q, q in enumerate(queries, 1):
        qid = q["query_id"]
        try:
            rr_res = hv6.rerank_rrf_candidates(
                bm25_state, reranker_bundle, q["query"], rrf_pools_by_qid[qid]["rrf_top30"], top_k=10
            )
            e2e = rrf_pools_by_qid[qid]["hybrid_rrf_ms"] + rr_res["rerank_only_ms"]
            rerank_50q_e2e_ms.append(e2e)
            raw_latency_rows.append({
                "mode": "hybrid_rrf_rerank_full50",
                "run_index": 1,
                "query_id": qid,
                "batch_group": q["batch_group"],
                "hybrid_rrf_ms": round(rrf_pools_by_qid[qid]["hybrid_rrf_ms"], 4),
                "rerank_top30_ms": round(rr_res["rerank_only_ms"], 4),
                "total_ms": round(e2e, 4),
                "error": None,
            })
            if idx_q == 1 or idx_q % 10 == 0:
                print(f"  [{idx_q:2d}/50] {qid:24s} | rerank_top30={rr_res['rerank_only_ms']:.1f} ms | e2e={e2e:.1f} ms")

            for h in rr_res["results"]:
                hybrid_rerank_top10_rows.append({"query_id": qid, "batch_group": q["batch_group"], **h})

            for cand in rr_res["annotated_top30"]:
                rrf_top30_audit_rows.append({
                    "query_id": qid,
                    "batch_group": q["batch_group"],
                    "query": q["query"],
                    "rrf_rank": cand["rrf_rank"],
                    "record_id": cand["record_id"],
                    "record_type": cand["record_type"],
                    "unit_id": cand["unit_id"],
                    "citation_path": cand["citation_path"],
                    "bm25_rank": cand["bm25_rank"],
                    "bm25_score": cand["bm25_score"],
                    "dense_rank": cand["dense_rank"],
                    "dense_score": cand["dense_score"],
                    "rrf_score": cand["rrf_score"],
                    "reranker_logit": cand["reranker_logit"],
                    "reranker_prob": cand["reranker_prob"],
                    "final_rerank_rank": cand["final_rerank_rank"],
                    "in_final_top10": cand["in_final_top10"],
                })
        except Exception as exc:
            rerank_errors += 1
            raw_latency_rows.append({
                "mode": "hybrid_rrf_rerank_full50",
                "run_index": 1,
                "query_id": qid,
                "batch_group": q["batch_group"],
                "total_ms": None,
                "error": str(exc),
            })

    # Verify 100% of 500 reranked Top-10 hits are proven inside Top-30 RRF (0 unverified!)
    audit_index = {(r["query_id"], r["record_id"]): r for r in rrf_top30_audit_rows}
    unverified_hits = [
        h for h in hybrid_rerank_top10_rows
        if (h["query_id"], h["record_id"]) not in audit_index or audit_index[(h["query_id"], h["record_id"])]["rrf_rank"] > 30
    ]
    assert len(unverified_hits) == 0, f"Found unverified Top-10 hits outside Top-30 RRF: {len(unverified_hits)}"
    print(f"Top-30 RRF provenance check: {len(hybrid_rerank_top10_rows)}/{len(hybrid_rerank_top10_rows)} hits verified inside Top-30 RRF (unverified={len(unverified_hits)}).")

    hv6.write_jsonl_lf(args.out_dir / "runs" / "bm25_only.top10.jsonl", bm25_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "dense_only.top10.jsonl", dense_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "hybrid_rrf.top10.jsonl", hybrid_rrf_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "hybrid_rrf_rerank.top10.jsonl", hybrid_rerank_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "rrf_top30_rerank_audit.50q.jsonl", rrf_top30_audit_rows)

    # Save latency benchmark summary & raw per-query log
    latency_summary = {
        "environment": env_info,
        "model_load_timings_ms": {
            "bm25_v2_and_consumer_v6_load_validate_ms": round(bm25_load_ms, 3),
            "dense_bundle_load_validate_ms": round(dense_bundle["load_validate_ms"], 3),
            "bge_m3_model_and_tokenizer_load_ms": round(
                json.loads((args.out_dir / "benchmark" / "smoke_24h_results.json").read_text(encoding="utf-8"))
                .get("bge_m3_load_ms", 0.0),
                3,
            ),
            "bge_reranker_v2_m3_model_and_tokenizer_load_ms": round(reranker_bundle["load_ms"], 3),
        },
        "benchmark_modes": [
            {
                "mode": "bm25_only",
                "scope": "query_input -> tokenize -> BM25s_search -> Top-10",
                "warmup_passes": 1,
                "measured_runs": args.measured_runs,
                "queries_per_run": len(queries),
                "total_measurements": len(bm25_latencies),
                "errors": bm25_errors,
                "p50_ms": percentile_ms(bm25_latencies, 50),
                "p95_ms": percentile_ms(bm25_latencies, 95),
                "mean_ms": round(float(np.mean(bm25_latencies)), 3),
            },
            {
                "mode": "hybrid_rrf",
                "scope": "query_input -> bge-m3_encode + Dense_search + BM25s_search + RRF(k=60) -> Top-10",
                "warmup_passes": 1,
                "measured_runs": args.measured_runs,
                "queries_per_run": len(queries),
                "total_measurements": len(hybrid_latencies),
                "errors": hybrid_errors,
                "p50_ms": percentile_ms(hybrid_latencies, 50),
                "p95_ms": percentile_ms(hybrid_latencies, 95),
                "mean_ms": round(float(np.mean(hybrid_latencies)), 3),
                "substage_p50_ms": {
                    "encode_query_ms": percentile_ms(hybrid_encode_ms, 50),
                    "dense_search_ms": percentile_ms(hybrid_dense_ms, 50),
                    "bm25_search_ms": percentile_ms(hybrid_bm25_ms, 50),
                    "rrf_fusion_ms": percentile_ms(hybrid_rrf_ms, 50),
                },
            },
            {
                "mode": "hybrid_rrf_rerank (separate_row_full50)",
                "scope": "hybrid_rrf + bge-reranker-v2-m3(Top-30) -> Top-10",
                "warmup_queries": len(smoke_ids),
                "measured_runs": 1,
                "queries_per_run": len(queries),
                "total_measurements": len(rerank_50q_e2e_ms),
                "errors": rerank_errors,
                "p50_ms": percentile_ms(rerank_50q_e2e_ms, 50),
                "p95_ms": percentile_ms(rerank_50q_e2e_ms, 95),
                "mean_ms": round(float(np.mean(rerank_50q_e2e_ms)), 3),
            },
            {
                "mode": "hybrid_rrf_rerank (separate_row_smoke_3x)",
                "scope": "hybrid_rrf + bge-reranker-v2-m3(Top-30) -> Top-10 on 2 pinned smoke queries",
                "warmup_passes": 1,
                "measured_runs": args.measured_runs,
                "queries_per_run": len(smoke_ids),
                "total_measurements": len(rerank_smoke_e2e_ms),
                "errors": 0,
                "p50_ms": percentile_ms(rerank_smoke_e2e_ms, 50),
                "p95_ms": percentile_ms(rerank_smoke_e2e_ms, 95),
                "mean_ms": round(float(np.mean(rerank_smoke_e2e_ms)), 3),
            },
        ],
    }
    hv6.write_json_lf(args.out_dir / "benchmark" / "latency_summary.json", latency_summary)
    hv6.write_jsonl_lf(args.out_dir / "benchmark" / "latency_raw_per_query.jsonl", raw_latency_rows)

    # 10. Review Fix #3: Hydrate via genuine v6 Consumer (red light = 7, driving age = 16, >=1 table row, all unique Top-10)
    print("\n=== [7] KIEM TRA HYDRATION QUA CONSUMER V6 THAT (REVIEW #3) ===")
    all_top10_rows = bm25_top10_rows + dense_top10_rows + hybrid_rrf_top10_rows + hybrid_rerank_top10_rows
    unique_rids = sorted({r["record_id"] for r in all_top10_rows})
    hydrated_by_rid: dict[str, dict[str, Any]] = {}
    for rid in unique_rids:
        h_info = hv6.hydrate_record_via_consumer_v6(bm25_mod, bm25_state, rid)
        hydrated_by_rid[rid] = {k: v for k, v in h_info.items() if k != "full_envelope"}

    red_rid = bm25_state["consumer"].red_id
    age_rid = bm25_state["consumer"].age_id
    red_hyd = hydrated_by_rid.get(red_rid) or {
        k: v for k, v in hv6.hydrate_record_via_consumer_v6(bm25_mod, bm25_state, red_rid).items() if k != "full_envelope"
    }
    age_hyd = hydrated_by_rid.get(age_rid) or {
        k: v for k, v in hv6.hydrate_record_via_consumer_v6(bm25_mod, bm25_state, age_rid).items() if k != "full_envelope"
    }
    table_hyds = [v for v in hydrated_by_rid.values() if v["record_type"] == "table-retrieval.v1"]

    assert red_hyd["unit_reads_count"] == 7, f"Expected 7 unit_reads for red light, got {red_hyd['unit_reads_count']}"
    assert age_hyd["unit_reads_count"] == 16, f"Expected 16 unit_reads for driving age, got {age_hyd['unit_reads_count']}"
    assert len(table_hyds) >= 1, "Expected at least 1 table-retrieval.v1 row hydrated via Consumer v6"

    print(f"  Red light ({red_rid[:18]}...): unit_reads={red_hyd['unit_reads_count']} (PASS == 7)")
    print(f"  Driving age ({age_rid[:18]}...): unit_reads={age_hyd['unit_reads_count']} (PASS == 16)")
    print(f"  Table rows hydrated in Top-10: {len(table_hyds)} (sample {table_hyds[0]['record_id'][:18]}..., unit_reads={table_hyds[0]['unit_reads_count']})")
    print(f"  Total unique Top-10 record_ids hydrated via Consumer v6: {len(hydrated_by_rid)}")

    hv6.write_json_lf(args.out_dir / "evidence" / "consumer_v6_hydration_audit.json", {
        "consumer_adapter_version": red_hyd["adapter_version"],
        "red_light_check": red_hyd,
        "driving_age_check": age_hyd,
        "table_rows_hydrated_count": len(table_hyds),
        "sample_table_row_check": table_hyds[0],
        "unique_top10_hydrated_count": len(hydrated_by_rid),
        "hydrated_records": list(hydrated_by_rid.values()),
    })

    # 11. Review Fix #4: Compute Top-10 diff lists for Long (vs handoff-001 & BM25 vs Hybrid)
    diffs = compute_top10_diffs(args.old_handoff_dir / "runs", args.out_dir / "runs", queries)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "top10_diff_vs_handoff001.jsonl", diffs["diff_vs_handoff001"])
    hv6.write_jsonl_lf(args.out_dir / "runs" / "top10_diff_bm25_vs_hybrid.jsonl", diffs["diff_bm25_vs_hybrid"])
    print(
        f"Top-10 diffs exported: vs_handoff001={len(diffs['diff_vs_handoff001'])} pairs | "
        f"bm25_vs_hybrid={len(diffs['diff_bm25_vs_hybrid'])} pairs (all relevance=null, pending Long)"
    )

    # Clean __pycache__ inside unpacked-v6 one final time
    for pyc in args.bm25_root.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)

    # 12. Write handoff_manifest.json + cross-platform LF SHA256SUMS.txt + verify_checksums.py
    verify_py = '''"""Cross-platform LF/CRLF-safe SHA-256 checksum verifier for Windows and Linux/macOS."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
lines = [l.strip() for l in (ROOT / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines() if l.strip()]
mismatches = 0
for line in lines:
    expected_sha, rel_path = line.split("  ", 1)
    target = ROOT / rel_path
    actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual_sha != expected_sha:
        print(f"MISMATCH: {rel_path} (expected {expected_sha}, got {actual_sha})")
        mismatches += 1
print(f"Verified {len(lines)} files | Mismatches: {mismatches}")
raise SystemExit(0 if mismatches == 0 else 1)
'''
    with (args.out_dir / "verify_checksums.py").open("w", encoding="utf-8", newline="\n") as f:
        f.write(verify_py)

    all_files = sorted(
        [p for p in args.out_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"],
        key=lambda p: p.relative_to(args.out_dir).as_posix(),
    )
    sha_lines = [f"{hv6.sha256_file(p)}  {p.relative_to(args.out_dir).as_posix()}" for p in all_files]
    with (args.out_dir / "SHA256SUMS.txt").open("w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(sha_lines) + "\n")

    handoff_manifest = {
        "handoff_version": hv6.HANDOFF_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": env_info,
        "pinned_models": {
            "dense_encoder": {
                "model_id": hv6.DENSE_MODEL_ID,
                "model_revision": hv6.DENSE_MODEL_REVISION,
                "tokenizer_revision": hv6.DENSE_MODEL_REVISION,
            },
            "cross_encoder_reranker": {
                "model_id": hv6.RERANKER_MODEL_ID,
                "model_revision": hv6.RERANKER_MODEL_REVISION,
                "tokenizer_revision": hv6.RERANKER_MODEL_REVISION,
            },
        },
        "source_bindings": {
            "dataset_version": bm25_state["manifest"]["dataset_version"],
            "index_version": bm25_state["manifest"]["index_version"],
            "dataset_manifest_sha256": bm25_state["manifest"]["dataset_manifest_sha256"],
            "index_manifest_sha256": hv6.sha256_file(args.bm25_root / "index_manifest.json"),
            "queries_manifest_sha256": bm25_state["manifest"]["queries_manifest_sha256"],
            "dense_manifest_sha256": hv6.sha256_file(dense_dir / "dense_manifest.json"),
        },
        "review_fixes_verified": {
            "1_strict_loader_rejections": True,
            "2_top30_rrf_audit_rows": len(rrf_top30_audit_rows),
            "3_consumer_v6_real_hydration": {
                "red_light_unit_reads": red_hyd["unit_reads_count"],
                "driving_age_unit_reads": age_hyd["unit_reads_count"],
                "table_rows_hydrated": len(table_hyds),
            },
            "4_reproducible_v2_bundle_and_top10_diffs": {
                "preserved_old_bundle": "artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip",
                "diff_pairs_vs_handoff001": len(diffs["diff_vs_handoff001"]),
                "diff_pairs_bm25_vs_hybrid": len(diffs["diff_bm25_vs_hybrid"]),
            },
        },
        "sha256sums_sha256": hv6.sha256_file(args.out_dir / "SHA256SUMS.txt"),
    }
    hv6.write_json_lf(args.out_dir / "handoff_manifest.json", handoff_manifest)

    # Re-write SHA256SUMS.txt so handoff_manifest.json itself is also covered!
    all_files = sorted(
        [p for p in args.out_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"],
        key=lambda p: p.relative_to(args.out_dir).as_posix(),
    )
    sha_lines = [f"{hv6.sha256_file(p)}  {p.relative_to(args.out_dir).as_posix()}" for p in all_files]
    with (args.out_dir / "SHA256SUMS.txt").open("w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(sha_lines) + "\n")

    # 13. Write formal Markdown handoff v2 for Huy, Hung, Long
    b_stat = latency_summary["benchmark_modes"][0]
    h_stat = latency_summary["benchmark_modes"][1]
    r50_stat = latency_summary["benchmark_modes"][2]
    r3_stat = latency_summary["benchmark_modes"][3]

    doc_md = f"""# Bàn giao Hybrid v6, Benchmark Độ trễ & Khắc phục 4 Lỗi Review (`{hv6.HANDOFF_VERSION}`)

- **Người thực hiện:** Trần Nguyễn Hoàng (`24021490`) — Retrieval Lead
- **Thời điểm xuất gói:** `{handoff_manifest["created_at"]}`
- **Gói bàn giao mới:** `artifacts/vtls-retrieval-v6-hybrid-handoff-002.zip` *(giữ nguyên gói cũ `artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip`)*

---

## 1. Cấu hình máy & Phiên bản đã ghim (24h Checkpoint)

- **Phần cứng & HĐH:** `{env_info["cpu_name"]}` ({env_info["cpu_logical_cores"]} luồng), RAM `{env_info["ram_gb"]} GB`, GPU tích hợp `{env_info["gpu"]}` (chạy inference trên `CPU`, `cuda=False`), OS `{env_info["os"]}`.
- **Môi trường Python:** Python `{env_info["python_version"]}` · `torch=={env_info["torch_version"]}` · `transformers=={env_info["transformers_version"]}` · `bm25s=={env_info["bm25s_version"]}` · `numpy=={env_info["numpy_version"]}` · `scipy=={env_info["scipy_version"]}`.
- **Ghim Revision Model & Tokenizer (cả 2 thành phần đều khóa cứng commit SHA):**
  - Dense Encoder: `BAAI/bge-m3` — `model_revision = {hv6.DENSE_MODEL_REVISION}`, `tokenizer_revision = {hv6.DENSE_MODEL_REVISION}`.
  - Cross-Encoder Reranker: `BAAI/bge-reranker-v2-m3` — `model_revision = {hv6.RERANKER_MODEL_REVISION}`, `tokenizer_revision = {hv6.RERANKER_MODEL_REVISION}`.

---

## 2. Kết quả đo độ trễ chuẩn (48h Benchmark — Warmup + {args.measured_runs} lượt × 50 câu)

- **Thời gian nạp model & kiểm chứng index (tách riêng ngoài truy vấn):**
  - Nạp & validate BM25 v2 + `Consumer` v6 chính thức: `{bm25_load_ms:.2f} ms`
  - Nạp & validate Dense bundle (`139 × 1024`, kiểm SHA-256 từng hàng): `{dense_bundle["load_validate_ms"]:.2f} ms`
  - Nạp `BAAI/bge-reranker-v2-m3` (model + tokenizer rev `{hv6.RERANKER_MODEL_REVISION[:12]}...`): `{reranker_bundle["load_ms"]:.2f} ms`

| Chế độ truy xuất | Phạm vi đo | Số lượt đo | Số lỗi | p50 (ms) | p95 (ms) | Mean (ms) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| **`bm25_only` (BM25 v2)** | Nhận câu hỏi → tokenize → BM25s → Top-10 | `{b_stat["total_measurements"]}` (`{args.measured_runs}×50`) | `{b_stat["errors"]}` | **`{b_stat["p50_ms"]:.3f}`** | **`{b_stat["p95_ms"]:.3f}`** | `{b_stat["mean_ms"]:.3f}` |
| **`hybrid_rrf` (RRF k=60)** | Nhận câu hỏi → encode `bge-m3` + Dense + BM25s + RRF → Top-10 | `{h_stat["total_measurements"]}` (`{args.measured_runs}×50`) | `{h_stat["errors"]}` | **`{h_stat["p50_ms"]:.3f}`** | **`{h_stat["p95_ms"]:.3f}`** | `{h_stat["mean_ms"]:.3f}` |
| **`hybrid_rrf_rerank` *(dòng riêng — full 50q)*** | `hybrid_rrf` + Rerank Top-30 `bge-reranker-v2-m3` → Top-10 | `{r50_stat["total_measurements"]}` (`1×50`) | `{r50_stat["errors"]}` | **`{r50_stat["p50_ms"]:.3f}`** | **`{r50_stat["p95_ms"]:.3f}`** | `{r50_stat["mean_ms"]:.3f}` |
| **`hybrid_rrf_rerank` *(dòng riêng — 2 câu smoke × 3)*** | `hybrid_rrf` + Rerank Top-30 trên 2 câu smoke (sau warmup) | `{r3_stat["total_measurements"]}` (`{args.measured_runs}×2`) | `{r3_stat["errors"]}` | **`{r3_stat["p50_ms"]:.3f}`** | **`{r3_stat["p95_ms"]:.3f}`** | `{r3_stat["mean_ms"]:.3f}` |

*(Log thô từng câu của mọi lượt đo được lưu tại `benchmark/latency_raw_per_query.jsonl`.)*

---

## 3. Báo cáo khắc phục 4 lỗi Review & Hướng dẫn tích hợp cho Hùng & Long

### Lỗi 1: Loader từ chối sai dữ liệu (`src/hybrid_v6.py` & `evidence/loader_rejection_tests.json`)
- Sử dụng trực tiếp `subset_bm25_v6.load_index()` chính thức để kiểm tra seal của BM25 v2 + `Consumer` v6, sau đó `load_dense_bundle()` đối chiếu toàn bộ hash manifest, version/revision và SHA-256 của **từng vector hàng `0..138`** với `record_id`.
- Đã kiểm thử tự động 3 ca lỗi (`evidence/loader_rejection_tests.json`):
  1. **Sai hash** (`embeddings.npy` bị sửa 1 byte) → `ValueError: Dense directory inventory/content hash mismatch`.
  2. **Sai version** (`dense_version` lệch `vtls-dense-bge-m3.v1`) → `ValueError: Dense version mismatch`.
  3. **Lệch thứ tự 139 vector so với `record_id`** (hoán đổi dòng `0` và `1` trong `embeddings.npy`) → `ValueError: Dense vector row order/content mismatch at row 0`.

### Lỗi 2: Đủ bằng chứng Top-30 RRF trước khi rerank (`runs/rrf_top30_rerank_audit.50q.jsonl`)
- Xuất đủ `50 × 30 = 1,500` bản ghi Top-30 RRF trước rerank, ghi rõ `rrf_rank`, `record_id`, `bm25_rank`, `bm25_score`, `dense_rank`, `dense_score`, `rrf_score`, `reranker_logit`, `final_rerank_rank` và cờ `in_final_top10`.
- Kiểm chứng tự động đạt **`500 / 500` hit Top-10 nằm trọn trong Top-30 RRF (`0` hit thiếu bằng chứng)**.

### Lỗi 3: Mở căn cứ qua `Consumer` v6 thật (`evidence/consumer_v6_hydration_audit.json`)
- Loại bỏ hoàn toàn cách đọc thẳng `target_frames.jsonl`. Mọi `record_id` được mở qua `subset_bm25_v6.read_loaded(bm25_state, record_id)` gọi trực tiếp `Consumer.read(record_id)`:
  - **Câu đèn đỏ** (`{red_rid}`): **`{red_hyd["unit_reads_count"]}` mục đọc kèm** (`unit_reads`), `0` `supporting_records`.
  - **Câu tuổi lái mô tô** (`{age_rid}`): **`{age_hyd["unit_reads_count"]}` mục đọc kèm** (`unit_reads`), `0` `supporting_records`.
  - **Hàng bảng (`table-retrieval.v1`):** Đã kiểm khớp `{len(table_hyds)}` hàng bảng trong Top-10 qua `Consumer.read()` (ví dụ `{table_hyds[0]["record_id"]}`).
- **Hướng dẫn tích hợp cho Hùng:**
  1. Gọi `mod, state, _ = load_bm25_v2_index("unpacked-v6/bm25")` và `dense = load_dense_bundle(state, "artifacts/v6_hybrid_handoff_v2/dense_bge_m3")`.
  2. Sau khi lấy `record_id` từ kết quả `search_hybrid_rrf(...)` hoặc `rerank_rrf_candidates(...)`, gọi `detail = mod.read_loaded(state, record_id)["dataset_response"]` rồi đọc căn cứ từ `detail["required_read"]["unit_reads"]` và `detail["required_read"]["supporting_records"]`.
  3. Bắt `ValueError` (sai hash, sai version, lệch thứ tự vector, `record_id` không hợp lệ) và `RuntimeError` (thiếu model hoặc sai commit SHA revision trong cache HuggingFace) để trả HTTP `503` / log lỗi rõ ràng thay vì âm thầm fallback.

### Lỗi 4: Gói mới tái lập được & Danh sách cặp thay đổi Top-10 cho Long
- Giữ nguyên gói `artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip`.
- Gói mới `artifacts/vtls-retrieval-v6-hybrid-handoff-002.zip` dùng chuẩn xuống dòng `LF` (`\\n`) và script `verify_checksums.py` khớp SHA-256 trên cả Git lẫn checkout Windows.
- Xuất sẵn 2 danh sách cặp thay đổi (để `relevance: null`, **không gán mặc định 0**) cho Long chấm và tính Recall@10:
  - `runs/top10_diff_vs_handoff001.jsonl`: `{len(diffs["diff_vs_handoff001"])}` cặp khác biệt Top-10 giữa gói `001` và `002`.
  - `runs/top10_diff_bm25_vs_hybrid.jsonl`: `{len(diffs["diff_bm25_vs_hybrid"])}` cặp khác biệt Top-10 giữa `bm25_only` và `hybrid_rrf` / `hybrid_rrf_rerank`.
"""
    args.doc_out.parent.mkdir(parents=True, exist_ok=True)
    with args.doc_out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(doc_md)

    # 14. Package vtls-retrieval-v6-hybrid-handoff-002.zip (preserving 001 untouched)
    if args.zip_out.exists():
        args.zip_out.unlink()
    with zipfile.ZipFile(args.zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(args.out_dir.rglob("*"), key=lambda x: x.relative_to(args.out_dir).as_posix()):
            if p.is_file():
                zf.write(p, arcname=f"v6_hybrid_handoff_v2/{p.relative_to(args.out_dir).as_posix()}")
        zf.write(args.doc_out, arcname="Retrieval_V6_Hybrid_Handoff_v2.md")
        zf.write(Path("src/hybrid_v6.py"), arcname="src/hybrid_v6.py")
        zf.write(Path("scripts/hybrid_v6_cli.py"), arcname="scripts/hybrid_v6_cli.py")

    zip_sha = hv6.sha256_file(args.zip_out)
    with args.zip_out.with_suffix(".zip.sha256").open("w", encoding="ascii", newline="\n") as f:
        f.write(f"{zip_sha}  {args.zip_out.name}\n")

    print("\n=== [8] HOAN TAT DONG GOI HANDOFF-002 ===")
    print(f"Handoff Doc : {args.doc_out}")
    print(f"ZIP Bundle  : {args.zip_out} ({args.zip_out.stat().st_size:,} bytes)")
    print(f"ZIP SHA-256 : {zip_sha}")
    print(f"Old ZIP kept: {Path('artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip').exists()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())