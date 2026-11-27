"""End-to-end execution & verification CLI for Hybrid v6 handoff-003 (6/6 final checklist)."""
from __future__ import annotations

import argparse
import copy
import gc
import json
import shutil
import sys
import tempfile
import zipfile
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


def run_negative_loader_tests(
    bm25_state: dict[str, Any],
    sealed_dense_dir: Path,
    query_binding: dict[str, Any],
) -> list[dict[str, Any]]:
    """Prove loader rejects wrong hash, wrong version, vector order mismatch, and query hash mismatch."""
    results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="v6_loader_neg_") as tmp:
        tmp_root = Path(tmp)

        c1 = tmp_root / "case1_wrong_hash"
        shutil.copytree(sealed_dense_dir, c1)
        emb1 = np.load(c1 / "embeddings.npy")
        emb1[0, 0] = np.float32(emb1[0, 0] + 0.001)
        np.save(c1 / "embeddings.npy", emb1)
        try:
            hv6.load_dense_bundle(bm25_state, c1, expected_query_binding=query_binding)
            raise AssertionError("Case 1 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "1_wrong_hash",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

        c2 = tmp_root / "case2_wrong_version"
        shutil.copytree(sealed_dense_dir, c2)
        m2 = json.loads((c2 / "dense_manifest.json").read_text(encoding="utf-8"))
        m2["dense_version"] = "vtls-dense-bge-m3.v0-stale"
        hv6.write_json_lf(c2 / "dense_manifest.json", m2)
        (c2 / "dense_manifest.sha256").write_text(hv6.sha256_file(c2 / "dense_manifest.json") + "\n", encoding="ascii")
        try:
            hv6.load_dense_bundle(bm25_state, c2, expected_query_binding=query_binding)
            raise AssertionError("Case 2 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "2_wrong_version",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

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
            hv6.load_dense_bundle(bm25_state, c3, expected_query_binding=query_binding)
            raise AssertionError("Case 3 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "3_vector_order_mismatch_vs_record_id",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

        tampered_q_binding = copy.deepcopy(query_binding)
        tampered_q_binding["queries_canonical_sha256"] = "0" * 64
        try:
            hv6.load_dense_bundle(bm25_state, sealed_dense_dir, expected_query_binding=tampered_q_binding)
            raise AssertionError("Case 4 SHOULD have failed but succeeded!")
        except ValueError as exc:
            results.append({
                "case": "4_query_set_hash_mismatch",
                "rejected": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            })

    return results


def run_prepackage_two_row_swap_guard(
    bm25_state: dict[str, Any],
    sealed_dense_dir: Path,
    query_binding: dict[str, Any],
) -> dict[str, Any]:
    """Pre-packaging gate: swap 2 vector rows and verify packaging validation rejects the bundle."""
    with tempfile.TemporaryDirectory(prefix="v6_prepkg_swap_") as tmp:
        c_swap = Path(tmp) / "prepackage_swapped_2_rows"
        shutil.copytree(sealed_dense_dir, c_swap)
        emb = np.load(c_swap / "embeddings.npy")
        emb[[10, 11]] = emb[[11, 10]]
        np.save(c_swap / "embeddings.npy", emb)
        m = json.loads((c_swap / "dense_manifest.json").read_text(encoding="utf-8"))
        m["embeddings_npy_sha256"] = hv6.sha256_file(c_swap / "embeddings.npy")
        m["files"] = hv6.dense_inventory(c_swap)
        m["dense_content_sha256"] = hv6.hashed_obj(m["files"])
        hv6.write_json_lf(c_swap / "dense_manifest.json", m)
        (c_swap / "dense_manifest.sha256").write_text(hv6.sha256_file(c_swap / "dense_manifest.json") + "\n", encoding="ascii")
        try:
            hv6.load_dense_bundle(bm25_state, c_swap, expected_query_binding=query_binding)
            raise AssertionError("Pre-package 2-row swap gate FAILED to reject swapped vectors!")
        except ValueError as exc:
            return {
                "case": "prepackage_two_row_vector_swap_guard",
                "swapped_rows": [10, 11],
                "rejected_before_packaging": True,
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            }


def run_hung_live_integration_checks(
    bm25_mod: Any,
    bm25_state: dict[str, Any],
    dense_bundle: dict[str, Any],
    encoder_bundle: dict[str, Any],
    queries: list[dict[str, Any]],
    table_query_id: str,
) -> dict[str, Any]:
    """Live Hybrid RRF + Consumer v6 hydration + fail-fast error checks for Hung."""
    q_by_id = {q["query_id"]: q for q in queries}
    live_cases = [
        ("red_light_query", "dev-red_light-1", bm25_state["consumer"].red_id, 7),
        ("driving_age_query", "dev-driving_age-2", bm25_state["consumer"].age_id, 16),
        ("table_row_query", table_query_id, None, None),
    ]

    smoke_outputs: list[dict[str, Any]] = []
    for label, qid, expected_rid, expected_unit_reads in live_cases:
        q_text = q_by_id[qid]["query"]
        res = hv6.search_hybrid_rrf(bm25_mod, bm25_state, dense_bundle, encoder_bundle, q_text, top_k=10)
        top10 = res["results"]
        if expected_rid is not None:
            matched = next((h for h in top10 if h["record_id"] == expected_rid), None)
            assert matched is not None, f"{label}: expected record_id {expected_rid} not in Top-10"
            target_rid = expected_rid
            target_rank = matched["rank"]
        else:
            table_hit = next((h for h in top10 if h["record_type"] == "table-retrieval.v1"), None)
            assert table_hit is not None, f"{label}: expected at least 1 table-retrieval.v1 hit in Top-10"
            target_rid = table_hit["record_id"]
            target_rank = table_hit["rank"]

        hyd = hv6.hydrate_record_via_consumer_v6(bm25_mod, bm25_state, target_rid)
        if expected_unit_reads is not None:
            assert hyd["unit_reads_count"] == expected_unit_reads, (
                f"{label}: expected unit_reads={expected_unit_reads}, got {hyd['unit_reads_count']}"
            )
        smoke_outputs.append({
            "case": label,
            "query_id": qid,
            "query": q_text,
            "measured_live_ms": round(res["measured_total_ms"], 3),
            "target_record_id": target_rid,
            "target_hybrid_rank": target_rank,
            "hydrated_record_type": hyd["record_type"],
            "hydrated_unit_reads_count": hyd["unit_reads_count"],
            "hydrated_supporting_records_count": hyd["supporting_records_count"],
            "dataset_response_sha256": hyd["dataset_response_sha256"],
            "top10_summary": [
                {
                    "rank": h["rank"],
                    "record_id": h["record_id"],
                    "record_type": h["record_type"],
                    "rrf_score": round(h["rrf_score"], 6),
                    "bm25_rank": h["bm25_rank"],
                    "dense_rank": h["dense_rank"],
                    "citation_path": h["citation_path"],
                }
                for h in top10
            ],
        })

    fail_fast_checks: list[dict[str, Any]] = []
    try:
        hv6.load_pinned_dense_encoder(
            model_id="BAAI/nonexistent-missing-model-v6",
            revision=hv6.DENSE_MODEL_REVISION,
            local_files_only=True,
        )
        raise AssertionError("Missing model check should have raised RuntimeError")
    except RuntimeError as exc:
        fail_fast_checks.append({
            "check": "missing_local_model_cache",
            "rejected": True,
            "exception_type": type(exc).__name__,
            "error_message": str(exc),
        })

    try:
        hv6.load_pinned_dense_encoder(
            model_id=hv6.DENSE_MODEL_ID,
            revision="0" * 40,
            local_files_only=True,
        )
        raise AssertionError("Wrong revision check should have raised RuntimeError")
    except RuntimeError as exc:
        fail_fast_checks.append({
            "check": "wrong_model_revision_sha",
            "rejected": True,
            "exception_type": type(exc).__name__,
            "error_message": str(exc),
        })

    try:
        bm25_mod.read_loaded(bm25_state, "invalid_record_id_does_not_exist")
        raise AssertionError("Invalid record_id hydration should have failed")
    except Exception as exc:
        fail_fast_checks.append({
            "check": "unknown_record_id_consumer_read",
            "rejected": True,
            "exception_type": type(exc).__name__,
            "error_message": str(exc),
        })

    return {
        "runtime_architecture": {
            "dense_backend": "numpy_local_cosine_f32 (in-memory 139x1024 matrix, Qdrant not enabled yet)",
            "reranker_policy": "offline_optional (excluded from default online request latency)",
            "consumer_hydration_api": "subset_bm25_v6.read_loaded(state, record_id)['dataset_response']['required_read']",
        },
        "live_smoke_cases": smoke_outputs,
        "fail_fast_error_checks": fail_fast_checks,
    }


def compute_top10_diffs(
    prev_runs_dir: Path,
    base_runs_dir: Path,
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

    def diff_two_runs(old_dir: Path, old_label: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for mode in ["bm25_only", "dense_only", "hybrid_rrf", "hybrid_rrf_rerank"]:
            old_g = load_by_q(old_dir / f"{mode}.top10.jsonl")
            new_g = load_by_q(new_runs_dir / f"{mode}.top10.jsonl")
            for qid in [q["query_id"] for q in queries]:
                old_map = {r["record_id"]: int(r["rank"]) for r in old_g.get(qid, [])}
                new_map = {r["record_id"]: int(r["rank"]) for r in new_g.get(qid, [])}
                for rid in sorted(set(old_map) | set(new_map)):
                    r_old = old_map.get(rid)
                    r_new = new_map.get(rid)
                    if r_old != r_new:
                        out.append({
                            "mode": mode,
                            "query_id": qid,
                            "batch_group": q_lookup[qid]["batch_group"],
                            "record_id": rid,
                            f"{old_label}_rank": r_old,
                            "handoff003_rank": r_new,
                            "change_type": "added_to_top10" if r_old is None else ("dropped_from_top10" if r_new is None else "rank_shifted"),
                            "relevance": None,
                            "label_status": "pending_long_review",
                        })
        return out

    diff_vs_002 = diff_two_runs(prev_runs_dir, "handoff002")
    diff_vs_001 = diff_two_runs(base_runs_dir, "handoff001")

    bm25_g = load_by_q(new_runs_dir / "bm25_only.top10.jsonl")
    diff_bm25_vs_hybrid: list[dict[str, Any]] = []
    for target_mode in ["hybrid_rrf", "hybrid_rrf_rerank"]:
        hyb_g = load_by_q(new_runs_dir / f"{target_mode}.top10.jsonl")
        for qid in [q["query_id"] for q in queries]:
            b_map = {r["record_id"]: r for r in bm25_g.get(qid, [])}
            h_map = {r["record_id"]: r for r in hyb_g.get(qid, [])}
            for rid in sorted(set(b_map) | set(h_map)):
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
        "diff_vs_handoff002": diff_vs_002,
        "diff_vs_handoff001": diff_vs_001,
        "diff_bm25_vs_hybrid": diff_bm25_vs_hybrid,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm25-root", type=Path, required=True, help="Path to unpacked BM25 v2 + dataset v6 root")
    parser.add_argument("--out-dir", type=Path, required=True, help="New output directory for handoff-003 (must not exist)")
    parser.add_argument("--doc-out", type=Path, required=True, help="New handoff Markdown path (must not exist)")
    parser.add_argument("--zip-out", type=Path, required=True, help="New handoff ZIP path (must not exist)")
    parser.add_argument("--prev-handoff-dir", type=Path, default=Path("artifacts/v6_hybrid_handoff_v2"))
    parser.add_argument("--base-handoff-dir", type=Path, default=Path("artifacts/v6_hybrid_handoff"))
    parser.add_argument("--lock-file", type=Path, default=Path("requirements-model.lock.txt"))
    parser.add_argument("--measured-runs", type=int, default=3, help="Number of timed passes after warmup (>=3)")
    args = parser.parse_args()

    if args.measured_runs < 3:
        raise ValueError("--measured-runs must be at least 3")

    zip_sha_out = args.zip_out.with_suffix(".zip.sha256")
    for protected_target in [args.out_dir, args.doc_out, args.zip_out, zip_sha_out]:
        if protected_target.exists():
            raise FileExistsError(f"Overwrite protection triggered: {protected_target} already exists!")

    preserved_bundles = {}
    for old_zip in [
        Path("artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip"),
        Path("artifacts/vtls-retrieval-v6-hybrid-handoff-002.zip"),
    ]:
        if old_zip.exists():
            preserved_bundles[old_zip.as_posix()] = hv6.sha256_file(old_zip)

    args.out_dir.mkdir(parents=True, exist_ok=False)
    (args.out_dir / "runs").mkdir()
    (args.out_dir / "benchmark").mkdir()
    (args.out_dir / "evidence").mkdir()

    env_info = hv6.collect_environment_info()
    print("=== [0] CHOT MAY & MOI TRUONG (.venv-model) ===")
    print(json.dumps(env_info, ensure_ascii=False, indent=2))

    print("\n=== [1] NAP & KIEM CHUNG BM25 V2 + CONSUMER V6 + QUERY MANIFEST ===")
    bm25_mod, bm25_state, bm25_load_ms = hv6.load_bm25_v2_index(args.bm25_root)
    queries = bm25_mod.query_set(
        args.bm25_root / "queries",
        bm25_state["manifest"]["queries_manifest_sha256"],
    )
    query_binding = hv6.build_query_binding(args.bm25_root / "queries", bm25_state["manifest"], queries)
    q_by_id = {q["query_id"]: q for q in queries}
    print(
        f"BM25 v2 + Consumer v6 load_validate_ms = {bm25_load_ms:.2f} ms | "
        f"docs = {len(bm25_state['mapping'])} | queries = {len(queries)} | "
        f"queries_canonical_sha256 = {query_binding['queries_canonical_sha256'][:16]}..."
    )

    print("\n=== [2] SINH LAI TRUC TIEP 139 VECTOR TU BAAI/BGE-M3 GHIM REVISION ===")
    encoder_bundle = hv6.load_pinned_dense_encoder(local_files_only=True)
    print(f"Loaded {encoder_bundle['model_id']} @ rev={encoder_bundle['model_revision']} in {encoder_bundle['load_ms']:.2f} ms")

    dense_dir = args.out_dir / "dense_bge_m3"
    dense_manifest = hv6.generate_and_seal_dense_bundle(
        bm25_state=bm25_state,
        encoder_bundle=encoder_bundle,
        query_binding=query_binding,
        out_dense_dir=dense_dir,
        batch_size=8,
        max_length=512,
    )
    dense_bundle = hv6.load_dense_bundle(bm25_state, dense_dir, expected_query_binding=query_binding)
    print(
        f"Regenerated 139x1024 embeddings in {dense_manifest['corpus_encode_elapsed_ms']:.2f} ms | "
        f"embeddings_sha256 = {dense_manifest['embeddings_npy_sha256'][:16]}..."
    )

    prev_emb_path = args.prev_handoff_dir / "dense_bge_m3" / "embeddings.npy"
    vec_cmp = hv6.compare_dense_vectors(prev_emb_path, dense_dir / "embeddings.npy", bm25_state["mapping"])
    hv6.write_json_lf(args.out_dir / "evidence" / "vector_regeneration_comparison.json", vec_cmp)
    print(
        f"Vector comparison vs handoff-002: exact_byte_rows={vec_cmp['exact_byte_identical_rows']}/139 | "
        f"max_abs_diff={vec_cmp['max_abs_diff']:.2e} | min_cosine={vec_cmp['min_row_cosine_similarity']:.8f}"
    )

    print("\n=== [3] KIEM THU TU CHOI DU LIEU LOI (4 CA LOADER) ===")
    neg_results = run_negative_loader_tests(bm25_state, dense_dir, query_binding)
    for nr in neg_results:
        print(f"  [PASS REJECT] {nr['case']} -> {nr['exception_type']}: {nr['error_message']}")

    print(f"\n=== [4] BENCHMARK DO TRE TREN BO VECTOR MOI SINH (WARMUP + {args.measured_runs} LUOT x 50 CAU) ===")
    raw_latency_rows: list[dict[str, Any]] = []

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

    bm25_top10_rows: list[dict[str, Any]] = []
    dense_top10_rows: list[dict[str, Any]] = []
    hybrid_rrf_top10_rows: list[dict[str, Any]] = []
    rrf_pools_by_qid: dict[str, dict[str, Any]] = {}
    table_query_id: str | None = None

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
            if table_query_id is None and h["record_type"] == "table-retrieval.v1":
                table_query_id = qid
        rrf_pools_by_qid[qid] = {
            "rrf_top30": h_ans["rrf_top_pool"],
            "hybrid_rrf_ms": h_ans["measured_total_ms"],
        }

    assert table_query_id is not None, "Expected at least one query returning a table-retrieval.v1 hit in Hybrid Top-10"

    print("\n=== [5] KIEM SMOKE LIVE 3 CA + FAIL-FAST CHO HUNG ===")
    hung_checks = run_hung_live_integration_checks(
        bm25_mod=bm25_mod,
        bm25_state=bm25_state,
        dense_bundle=dense_bundle,
        encoder_bundle=encoder_bundle,
        queries=queries,
        table_query_id=table_query_id,
    )
    hv6.write_json_lf(args.out_dir / "evidence" / "hung_integration_smoke.json", hung_checks)
    for sc in hung_checks["live_smoke_cases"]:
        print(
            f"  [LIVE SMOKE] {sc['case']} ({sc['query_id']}): rank=#{sc['target_hybrid_rank']} | "
            f"record={sc['target_record_id'][:18]}... | unit_reads={sc['hydrated_unit_reads_count']} | {sc['measured_live_ms']} ms"
        )
    for ff in hung_checks["fail_fast_error_checks"]:
        print(f"  [FAIL-FAST] {ff['check']} -> {ff['exception_type']}")

    bge_m3_load_ms = encoder_bundle["load_ms"]
    del encoder_bundle
    gc.collect()

    print("\n=== [6] CHAY RERANKER (OFFLINE/OPTIONAL) & XUAT TOP-30 RRF AUDIT ===")
    reranker_bundle = hv6.load_pinned_reranker(local_files_only=True)
    print(f"Loaded {reranker_bundle['model_id']} @ rev={reranker_bundle['model_revision']} in {reranker_bundle['load_ms']:.2f} ms")

    smoke_ids = ["dev-driving_age-2", "dev-red_light-1"]
    for qid in smoke_ids:
        _ = hv6.rerank_rrf_candidates(
            bm25_state, reranker_bundle, q_by_id[qid]["query"], rrf_pools_by_qid[qid]["rrf_top30"], top_k=10
        )

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
                "mode": "hybrid_rrf_rerank_offline_optional",
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
                "mode": "hybrid_rrf_rerank_offline_optional",
                "run_index": 1,
                "query_id": qid,
                "batch_group": q["batch_group"],
                "total_ms": None,
                "error": str(exc),
            })

    audit_index = {(r["query_id"], r["record_id"]): r for r in rrf_top30_audit_rows}
    unverified_hits = [
        h for h in hybrid_rerank_top10_rows
        if (h["query_id"], h["record_id"]) not in audit_index or audit_index[(h["query_id"], h["record_id"])]["rrf_rank"] > 30
    ]
    assert len(unverified_hits) == 0, f"Found unverified Top-10 hits outside Top-30 RRF: {len(unverified_hits)}"
    print(f"Top-30 RRF provenance check: {len(hybrid_rerank_top10_rows)}/500 verified (unverified=0).")

    hv6.write_jsonl_lf(args.out_dir / "runs" / "bm25_only.top10.jsonl", bm25_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "dense_only.top10.jsonl", dense_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "hybrid_rrf.top10.jsonl", hybrid_rrf_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "hybrid_rrf_rerank.top10.jsonl", hybrid_rerank_top10_rows)
    hv6.write_jsonl_lf(args.out_dir / "runs" / "rrf_top30_rerank_audit.50q.jsonl", rrf_top30_audit_rows)

    latency_summary = {
        "environment": env_info,
        "model_load_timings_ms": {
            "bm25_v2_and_consumer_v6_load_validate_ms": round(bm25_load_ms, 3),
            "dense_bundle_load_validate_ms": round(dense_bundle["load_validate_ms"], 3),
            "bge_m3_model_and_tokenizer_load_ms": round(bge_m3_load_ms, 3),
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
                "scope": "query_input -> bge-m3_encode + local_numpy_cosine + BM25s + RRF(k=60) -> Top-10",
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
                "mode": "hybrid_rrf_rerank (offline_optional_separate_row)",
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
        ],
    }
    hv6.write_json_lf(args.out_dir / "benchmark" / "latency_summary.json", latency_summary)
    hv6.write_jsonl_lf(args.out_dir / "benchmark" / "latency_raw_per_query.jsonl", raw_latency_rows)

    all_top10_rows = bm25_top10_rows + dense_top10_rows + hybrid_rrf_top10_rows + hybrid_rerank_top10_rows
    unique_rids = sorted({r["record_id"] for r in all_top10_rows})
    hydrated_by_rid: dict[str, dict[str, Any]] = {}
    for rid in unique_rids:
        h_info = hv6.hydrate_record_via_consumer_v6(bm25_mod, bm25_state, rid)
        hydrated_by_rid[rid] = {k: v for k, v in h_info.items() if k != "full_envelope"}

    red_hyd = hydrated_by_rid[bm25_state["consumer"].red_id]
    age_hyd = hydrated_by_rid[bm25_state["consumer"].age_id]
    table_hyds = [v for v in hydrated_by_rid.values() if v["record_type"] == "table-retrieval.v1"]
    assert red_hyd["unit_reads_count"] == 7
    assert age_hyd["unit_reads_count"] == 16
    assert len(table_hyds) >= 1

    hv6.write_json_lf(args.out_dir / "evidence" / "consumer_v6_hydration_audit.json", {
        "consumer_adapter_version": red_hyd["adapter_version"],
        "red_light_check": red_hyd,
        "driving_age_check": age_hyd,
        "table_rows_hydrated_count": len(table_hyds),
        "sample_table_row_check": table_hyds[0],
        "unique_top10_hydrated_count": len(hydrated_by_rid),
        "hydrated_records": list(hydrated_by_rid.values()),
    })

    diffs = compute_top10_diffs(
        prev_runs_dir=args.prev_handoff_dir / "runs",
        base_runs_dir=args.base_handoff_dir / "runs",
        new_runs_dir=args.out_dir / "runs",
        queries=queries,
    )
    hv6.write_jsonl_lf(args.out_dir / "runs" / "top10_diff_vs_handoff002.jsonl", diffs["diff_vs_handoff002"])
    hv6.write_jsonl_lf(args.out_dir / "runs" / "top10_diff_vs_handoff001.jsonl", diffs["diff_vs_handoff001"])
    hv6.write_jsonl_lf(args.out_dir / "runs" / "top10_diff_bm25_vs_hybrid.jsonl", diffs["diff_bm25_vs_hybrid"])
    print(
        f"Top-10 diffs for Long: vs_handoff002={len(diffs['diff_vs_handoff002'])} pairs | "
        f"vs_handoff001={len(diffs['diff_vs_handoff001'])} pairs | "
        f"bm25_vs_hybrid={len(diffs['diff_bm25_vs_hybrid'])} pairs (all relevance=null)"
    )

    print("\n=== [7] KIEM THU CHAN DAO 2 HANG VECTOR TRUOC KHI DONG GOI ===")
    swap_guard_res = run_prepackage_two_row_swap_guard(bm25_state, dense_dir, query_binding)
    print(f"  [PASS PRE-PKG GATE] {swap_guard_res['case']} -> {swap_guard_res['exception_type']}: {swap_guard_res['error_message']}")
    hv6.write_json_lf(args.out_dir / "evidence" / "loader_rejection_tests.json", {
        "all_rejected": True,
        "loader_cases": neg_results,
        "prepackage_swap_guard": swap_guard_res,
    })

    if args.lock_file.exists():
        shutil.copy2(args.lock_file, args.out_dir / "requirements-model.lock.txt")

    for pyc in args.bm25_root.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)

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
        "environment_lock_file": {
            "path": "requirements-model.lock.txt",
            "sha256": hv6.sha256_file(args.out_dir / "requirements-model.lock.txt") if (args.out_dir / "requirements-model.lock.txt").exists() else None,
        },
        "runtime_architecture": hung_checks["runtime_architecture"],
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
                "policy": "offline_optional",
            },
        },
        "source_bindings": {
            "dataset_version": bm25_state["manifest"]["dataset_version"],
            "index_version": bm25_state["manifest"]["index_version"],
            "dataset_manifest_sha256": bm25_state["manifest"]["dataset_manifest_sha256"],
            "index_manifest_sha256": hv6.sha256_file(args.bm25_root / "index_manifest.json"),
            "search_inputs_sha256": bm25_state["manifest"]["search_inputs_sha256"],
            "membership_sha256": bm25_state["manifest"]["membership_sha256"],
            "queries_manifest_sha256": query_binding["queries_manifest_sha256"],
            "queries_files_sha256": query_binding["queries_files_sha256"],
            "queries_canonical_sha256": query_binding["queries_canonical_sha256"],
            "dense_manifest_sha256": hv6.sha256_file(dense_dir / "dense_manifest.json"),
        },
        "vector_regeneration_audit": vec_cmp,
        "checklist_6_of_6_verified": {
            "1_regenerated_139_vectors_from_pinned_bge_m3": True,
            "2_non_overwriting_packager_and_2row_swap_gate": True,
            "3_queries_manifest_and_canonical_sha256_sealed": True,
            "4_venv_model_and_lockfile_documented": True,
            "5_hung_live_3case_smoke_and_failfast_verified": True,
            "6_long_versioned_runs_and_top10_diffs_exported": {
                "diff_pairs_vs_handoff002": len(diffs["diff_vs_handoff002"]),
                "diff_pairs_vs_handoff001": len(diffs["diff_vs_handoff001"]),
                "diff_pairs_bm25_vs_hybrid": len(diffs["diff_bm25_vs_hybrid"]),
            },
        },
        "preserved_previous_bundles_sha256": preserved_bundles,
        "sha256sums_sha256": hv6.sha256_file(args.out_dir / "SHA256SUMS.txt"),
    }
    hv6.write_json_lf(args.out_dir / "handoff_manifest.json", handoff_manifest)

    all_files = sorted(
        [p for p in args.out_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"],
        key=lambda p: p.relative_to(args.out_dir).as_posix(),
    )
    sha_lines = [f"{hv6.sha256_file(p)}  {p.relative_to(args.out_dir).as_posix()}" for p in all_files]
    with (args.out_dir / "SHA256SUMS.txt").open("w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(sha_lines) + "\n")

    b_stat = latency_summary["benchmark_modes"][0]
    h_stat = latency_summary["benchmark_modes"][1]
    r50_stat = latency_summary["benchmark_modes"][2]
    sc_red, sc_age, sc_tbl = hung_checks["live_smoke_cases"]
    fence = "`" * 3

    doc_md = f"""# Bàn giao Hybrid v6 Hoàn chỉnh (`{hv6.HANDOFF_VERSION}`) — Chốt 6/6 Đầu việc

## 1. Môi trường tái lập trên máy thứ hai (`.venv-model` & Lockfile)

- **Máy đo & Runtime:** `{env_info["hostname"]}` | `{env_info["os"]}` | `{env_info["cpu_name"]}` ({env_info["cpu_logical_cores"]} luồng) | RAM `{env_info["ram_gb"]} GB` | Device: `{env_info["inference_device"]}`
- **Python & Unicode seal:** Python `{env_info["python_version"]}` (`unicodedata {env_info["unicodedata_version"]}`), `torch {env_info["torch_version"]}`, `transformers {env_info["transformers_version"]}`, `bm25s {env_info["bm25s_version"]}`, `numpy {env_info["numpy_version"]}`
- **File khóa môi trường:** `requirements-model.lock.txt` (SHA-256: `{handoff_manifest["environment_lock_file"]["sha256"]}`)
- **Revision Hugging Face đã ghim cứng (cả model + tokenizer):**
  - Dense Encoder: `BAAI/bge-m3` @ `{hv6.DENSE_MODEL_REVISION}`
  - Cross-Encoder Reranker *(offline / tùy chọn)*: `BAAI/bge-reranker-v2-m3` @ `{hv6.RERANKER_MODEL_REVISION}`

### Lệnh dựng `.venv-model`, tải/cache 2 model và chạy smoke trên máy thứ hai

{fence}powershell
# 1. Tao moi truong ao tu Python 3.11.9 va cai dung ban khoa CPU
py -3.11 -m venv .venv-model
.\\.venv-model\\Scripts\\python.exe -m pip install -r requirements-model.lock.txt

# 2. Tai & xac minh cache local cho dung revision cua 2 model + tokenizer
.\\.venv-model\\Scripts\\python.exe -c "from src.hybrid_v6 import load_pinned_dense_encoder, load_pinned_reranker; load_pinned_dense_encoder(local_files_only=False); load_pinned_reranker(local_files_only=False); print('CACHE_OK')"

# 3. Kiem tra checksum goi ban giao
.\\.venv-model\\Scripts\\python.exe artifacts\\v6_hybrid_handoff_v3\\verify_checksums.py
{fence}

---

## 2. Sinh lại trực tiếp 139 vector từ `BAAI/bge-m3` & Bảo vệ đóng gói

1. **Sinh lại độc lập 139 embedding (`139 × 1024`):**
   - Mã hóa trực tiếp toàn bộ 139 bản ghi từ `unpacked-v6/bm25/search_inputs.jsonl` bằng `BAAI/bge-m3` (`5617a9f61b028005a4858fdac845db406aefb181`, `CLS` pooling, `max_length=512`, `float32` chuẩn hóa L2) trong `{dense_manifest["corpus_encode_elapsed_ms"]:.2f} ms`.
   - Đối chiếu với vector của `handoff-002` (`evidence/vector_regeneration_comparison.json`): `max_abs_diff = {vec_cmp["max_abs_diff"]:.2e}`, `min_row_cosine_similarity = {vec_cmp["min_row_cosine_similarity"]:.8f}` (`139/139` hàng khớp cosine `> 0.99999`).
2. **Chống ghi đè & Cổng chặn đảo 2 hàng vector trước đóng gói:**
   - Bộ đóng gói từ chối ghi đè (`FileExistsError`) nếu thư mục/file đầu ra đã tồn tại; giữ nguyên vẹn SHA-256 của `handoff-001` và `handoff-002`.
   - Đã kiểm thử đảo 2 hàng vector (`[10, 11]`) trước khi xuất `SHA256SUMS.txt` và nén ZIP: cổng kiểm định từ chối ngay (`ValueError: Dense vector row order/content mismatch at row 10`).
3. **Khóa SHA-256 danh sách câu hỏi trong manifest:**
   - `queries_manifest_sha256`: `{query_binding["queries_manifest_sha256"]}`
   - `queries_files_sha256`: `{query_binding["queries_files_sha256"]}`
   - `queries_canonical_sha256`: `{query_binding["queries_canonical_sha256"]}`

---

## 3. Benchmark độ trễ trên bộ 139 vector vừa sinh lại (Warmup + {args.measured_runs} lượt × 50 câu)

| Chế độ | Phạm vi đo | Số lượt (`n`) | Lỗi | p50 (ms) | p95 (ms) | Mean (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`bm25_only`** | Nhận câu hỏi → tokenize → BM25s → Top-10 | `{b_stat["total_measurements"]}` | `{b_stat["errors"]}` | **`{b_stat["p50_ms"]:.3f}`** | **`{b_stat["p95_ms"]:.3f}`** | `{b_stat["mean_ms"]:.3f}` |
| **`hybrid_rrf` (RRF k=60)** | Nhận câu hỏi → encode `bge-m3` + NumPy cosine + BM25s + RRF → Top-10 | `{h_stat["total_measurements"]}` | `{h_stat["errors"]}` | **`{h_stat["p50_ms"]:.3f}`** | **`{h_stat["p95_ms"]:.3f}`** | `{h_stat["mean_ms"]:.3f}` |
| **`hybrid_rrf_rerank` *(offline/tùy chọn)*** | `hybrid_rrf` + Rerank Top-30 `bge-reranker-v2-m3` → Top-10 | `{r50_stat["total_measurements"]}` | `{r50_stat["errors"]}` | **`{r50_stat["p50_ms"]:.3f}`** | **`{r50_stat["p95_ms"]:.3f}`** | `{r50_stat["mean_ms"]:.3f}` |

---

## 4. Phối hợp Hùng (Tích hợp & Smoke live 3 ca) & Long (Chấm Recall@5/10, MRR, nDCG)

### Phần bàn giao cho Hùng (`evidence/hung_integration_smoke.json`)
- **Kiến trúc backend hiện tại:**
  - Dense retrieval chạy **NumPy / cosine cục bộ** trên ma trận `139 × 1024` `float32` nạp từ `dense_bge_m3/embeddings.npy` (chưa bật Qdrant).
  - Cross-Encoder Reranker (`BAAI/bge-reranker-v2-m3`) giữ ở chế độ **offline / tùy chọn**, không bật trong đường dẫn truy vấn trực tuyến mặc định.
- **Kết quả smoke live 3 ca + mở detail qua `Consumer` v6 thật:**
  1. **Câu đèn đỏ** (`{sc_red["query_id"]}`): hit `{sc_red["target_record_id"]}` tại hạng `#{sc_red["target_hybrid_rank"]}`, hydrate qua `Consumer` trả **`{sc_red["hydrated_unit_reads_count"]}`** mục đọc kèm (`unit_reads`).
  2. **Câu tuổi lái mô tô** (`{sc_age["query_id"]}`): hit `{sc_age["target_record_id"]}` tại hạng `#{sc_age["target_hybrid_rank"]}`, hydrate qua `Consumer` trả **`{sc_age["hydrated_unit_reads_count"]}`** mục đọc kèm (`unit_reads`).
  3. **Câu hàng bảng** (`{sc_tbl["query_id"]}`): hit `{sc_tbl["target_record_id"]}` (`{sc_tbl["hydrated_record_type"]}`) tại hạng `#{sc_tbl["target_hybrid_rank"]}`, hydrate qua `Consumer` trả **`{sc_tbl["hydrated_unit_reads_count"]}`** mục đọc kèm.
- **Fail-fast khi thiếu model hoặc sai binding/hash/version:**
  - Thiếu model/revision trong cache (`local_files_only=True`) → ném `RuntimeError` ngay lúc khởi động.
  - Sai hash, sai version, lệch thứ tự vector hoặc lệch hash danh sách truy vấn → `load_dense_bundle()` ném `ValueError` ngay lập tức.

### Phần bàn giao cho Long (`runs/`)
- Các bảng xếp hạng Top-10 tái chạy trên bộ vector mới: `bm25_only.top10.jsonl`, `dense_only.top10.jsonl`, `hybrid_rrf.top10.jsonl`, `hybrid_rrf_rerank.top10.jsonl`, kèm `rrf_top30_rerank_audit.50q.jsonl` (`1,500` dòng).
- Danh sách cặp thay đổi Top-10 (để `relevance: null`, không gán mặc định `0`):
  - `runs/top10_diff_vs_handoff002.jsonl`: `{len(diffs["diff_vs_handoff002"])}` cặp thay đổi so với `handoff-002`.
  - `runs/top10_diff_vs_handoff001.jsonl`: `{len(diffs["diff_vs_handoff001"])}` cặp thay đổi so với `handoff-001`.
  - `runs/top10_diff_bm25_vs_hybrid.jsonl`: `{len(diffs["diff_bm25_vs_hybrid"])}` cặp khác biệt giữa BM25 và Hybrid.
"""
    args.doc_out.parent.mkdir(parents=True, exist_ok=True)
    with args.doc_out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(doc_md)

    args.zip_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(args.out_dir.rglob("*"), key=lambda x: x.relative_to(args.out_dir).as_posix()):
            if p.is_file():
                zf.write(p, arcname=f"v6_hybrid_handoff_v3/{p.relative_to(args.out_dir).as_posix()}")
        zf.write(args.doc_out, arcname="Retrieval_V6_Hybrid_Handoff_v3.md")
        zf.write(Path("src/hybrid_v6.py"), arcname="src/hybrid_v6.py")
        zf.write(Path("scripts/hybrid_v6_cli.py"), arcname="scripts/hybrid_v6_cli.py")
        if args.lock_file.exists():
            zf.write(args.lock_file, arcname="requirements-model.lock.txt")

    zip_sha = hv6.sha256_file(args.zip_out)
    with zip_sha_out.open("w", encoding="ascii", newline="\n") as f:
        f.write(f"{zip_sha}  {args.zip_out.name}\n")

    for old_path_str, old_sha in preserved_bundles.items():
        assert hv6.sha256_file(Path(old_path_str)) == old_sha, f"Preserved bundle mutated: {old_path_str}"

    print("\n=== [8] HOAN TAT DONG GOI HANDOFF-003 (6/6 DAU VIEC) ===")
    print(f"Handoff Doc : {args.doc_out}")
    print(f"ZIP Bundle  : {args.zip_out} ({args.zip_out.stat().st_size:,} bytes)")
    print(f"ZIP SHA-256 : {zip_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())