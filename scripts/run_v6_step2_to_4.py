import gc
import hashlib
import json
import math
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import bm25s
import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.bm25_tokenizer import tokenize  # noqa: E402

V6_BM25_DIR = ROOT / "unpacked-v6" / "bm25"
OUT_DIR = ROOT / "artifacts" / "v6_hybrid_handoff"
DENSE_DIR = OUT_DIR / "dense_bge_m3"

DENSE_MODEL_ID = "BAAI/bge-m3"
RERANK_MODEL_ID = "BAAI/bge-reranker-v2-m3"
RERANK_MAX_LENGTH = 1024
RRF_K = 60
RERANK_DEPTH = 30
TOP_K = 10


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_v6_inputs():
    index_manifest = json.loads((V6_BM25_DIR / "index_manifest.json").read_text(encoding="utf-8"))
    bm25_cfg = json.loads((V6_BM25_DIR / "config.json").read_text(encoding="utf-8"))
    search_inputs = read_jsonl(V6_BM25_DIR / "search_inputs.jsonl")
    doc_mapping = read_jsonl(V6_BM25_DIR / "document_mapping.jsonl")

    assert len(search_inputs) == 139 and len(doc_mapping) == 139
    for idx, (inp, mp) in enumerate(zip(search_inputs, doc_mapping)):
        assert inp["record_id"] == mp["record_id"] and mp["internal_doc_id"] == idx

    queries = []
    for batch_group, fname in [
        ("old", "old-dev.queries.jsonl"),
        ("new", "new-dev.queries.jsonl"),
        ("limit", "limits.queries.jsonl"),
    ]:
        for row in read_jsonl(V6_BM25_DIR / "queries" / fname):
            queries.append({**row, "batch_group": batch_group})
    assert len(queries) == 50

    bm25_engine = bm25s.BM25.load(
        str(V6_BM25_DIR / "engine"),
        load_corpus=False,
        mmap=False,
        allow_pickle=False,
        show_progress=False,
    )

    frames_by_id = {}
    for row in read_jsonl(V6_BM25_DIR / "dataset" / "target_frames.jsonl"):
        rec = row.get("record", row)
        rid = rec.get("record_id") or row.get("record_id")
        if rid:
            frames_by_id[rid] = row
    assert len(frames_by_id) == 139

    emb_path = DENSE_DIR / "embeddings.npy"
    dense_manifest = json.loads((DENSE_DIR / "dense_manifest.json").read_text(encoding="utf-8"))
    assert sha256_file(emb_path) == dense_manifest["embeddings_npy_sha256"], "embeddings.npy SHA mismatch"
    doc_embeddings = np.load(emb_path)
    assert doc_embeddings.shape == (139, 1024)

    return index_manifest, bm25_cfg, search_inputs, queries, bm25_engine, frames_by_id, doc_embeddings, dense_manifest


def precompute_dense_queries(
    queries: list[dict],
    doc_embeddings: np.ndarray,
    search_inputs: list[dict],
    device: torch.device,
) -> tuple[dict[str, list[tuple[int, float]]], dict[str, float]]:
    print("Nap BAAI/bge-m3 de encode 50 queries...")
    tok = AutoTokenizer.from_pretrained(DENSE_MODEL_ID)
    mod = AutoModel.from_pretrained(DENSE_MODEL_ID, low_cpu_mem_usage=True)
    mod.eval()
    mod.to(device)

    dense_rankings: dict[str, list[tuple[int, float]]] = {}
    dense_timings: dict[str, float] = {}
    with torch.no_grad():
        for q in queries:
            t0 = time.perf_counter()
            enc = tok(
                [q["query"]],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(device)
            out = mod(**enc)
            q_vec = F.normalize(out.last_hidden_state[:, 0], p=2, dim=-1).cpu().numpy()[0]
            sims = (doc_embeddings @ q_vec).astype(float)
            ranked = [(i, float(sims[i])) for i in range(len(search_inputs))]
            ranked.sort(key=lambda x: (-x[1], search_inputs[x[0]]["record_id"]))
            dense_rankings[q["query_id"]] = ranked
            dense_timings[q["query_id"]] = (time.perf_counter() - t0) * 1000.0

    del mod, tok
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("Da giai phong BAAI/bge-m3 khoi RAM.")
    return dense_rankings, dense_timings


def bm25_rank_all(bm25_engine, bm25_cfg: dict, search_inputs: list[dict], query: str) -> list[tuple[int, float]]:
    q_tokens = tokenize(query, bm25_cfg)
    if not q_tokens:
        return []
    doc_ids, scores = bm25_engine.retrieve(
        [q_tokens],
        k=len(search_inputs),
        sorted=True,
        return_as="tuple",
        show_progress=False,
    )
    pairs = [(int(idx), float(sc)) for idx, sc in zip(doc_ids[0].tolist(), scores[0].tolist()) if float(sc) > 0.0]
    pairs.sort(key=lambda x: (-x[1], search_inputs[x[0]]["record_id"]))
    return pairs


def step2_hybrid_and_rerank(
    queries: list[dict],
    search_inputs: list[dict],
    index_manifest: dict,
    bm25_cfg: dict,
    bm25_engine,
    dense_rankings: dict[str, list[tuple[int, float]]],
    dense_timings: dict[str, float],
    device: torch.device,
):
    print("\n" + "=" * 72)
    print("BUOC 2: HYBRID RRF (k=60) + CROSS-ENCODER RERANKING (BAAI/bge-reranker-v2-m3)")
    print("=" * 72)

    rerank_tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL_ID)
    rerank_model = AutoModelForSequenceClassification.from_pretrained(
        RERANK_MODEL_ID, low_cpu_mem_usage=True
    )
    rerank_model.eval()
    rerank_model.to(device)
    rerank_commit = getattr(rerank_model.config, "_commit_hash", None)
    print(f"Reranker: {RERANK_MODEL_ID} | Revision: {rerank_commit} | Depth: {RERANK_DEPTH}")

    runs_by_mode: dict[str, list[dict]] = {
        "bm25_only": [],
        "dense_only": [],
        "hybrid_rrf": [],
        "hybrid_rrf_rerank": [],
    }
    query_diagnostics = []

    for idx_q, q in enumerate(queries, 1):
        qid = q["query_id"]
        qtext = q["query"]

        t_bm25 = time.perf_counter()
        bm25_ranked = bm25_rank_all(bm25_engine, bm25_cfg, search_inputs, qtext)
        ms_bm25 = (time.perf_counter() - t_bm25) * 1000.0

        dense_ranked = dense_rankings[qid]
        ms_dense = dense_timings[qid]

        bm25_rank_map = {idx: (r, sc) for r, (idx, sc) in enumerate(bm25_ranked, 1)}
        dense_rank_map = {idx: (r, sc) for r, (idx, sc) in enumerate(dense_ranked, 1)}

        rrf_scores: dict[int, float] = {}
        for r, (idx, _) in enumerate(bm25_ranked, 1):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (RRF_K + r)
        for r, (idx, _) in enumerate(dense_ranked, 1):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (RRF_K + r)

        rrf_ranked = sorted(
            rrf_scores.items(),
            key=lambda x: (-x[1], search_inputs[x[0]]["record_id"]),
        )

        t_rerank = time.perf_counter()
        candidates = [idx for idx, _ in rrf_ranked[:RERANK_DEPTH]]
        pairs = [[qtext, search_inputs[idx]["text_for_search"]] for idx in candidates]
        ce_logits = []
        with torch.no_grad():
            for start in range(0, len(pairs), 8):
                batch_pairs = pairs[start : start + 8]
                enc = rerank_tokenizer(
                    batch_pairs,
                    padding=True,
                    truncation=True,
                    max_length=RERANK_MAX_LENGTH,
                    return_tensors="pt",
                ).to(device)
                logits = rerank_model(**enc, return_dict=True).logits.view(-1).float()
                ce_logits.extend(logits.cpu().tolist())

        reranked_head = sorted(
            zip(candidates, ce_logits),
            key=lambda x: (-x[1], search_inputs[x[0]]["record_id"]),
        )
        ms_rerank = (time.perf_counter() - t_rerank) * 1000.0

        if idx_q % 10 == 0 or idx_q == 1:
            print(f"  [{idx_q:2d}/50] {qid} | rerank_top30={ms_rerank:.0f}ms")

        def make_rows(mode_name: str, ranked_list: list[tuple[int, float]], score_field: str):
            out_rows = []
            for rank, (idx, sc) in enumerate(ranked_list[:TOP_K], 1):
                rec = search_inputs[idx]
                b_info = bm25_rank_map.get(idx)
                d_info = dense_rank_map.get(idx)
                out_rows.append({
                    "query_id": qid,
                    "batch_group": q["batch_group"],
                    "topic": q["topic"],
                    "query_type": q["query_type"],
                    "record_id": rec["record_id"],
                    "record_type": rec["record_type"],
                    "source_id": rec["source_id"],
                    "law_id": rec["law_id"],
                    "unit_id": rec["unit_id"],
                    "citation_path": rec["citation_path"],
                    "rank": rank,
                    "score": round(float(sc), 6),
                    "score_type": score_field,
                    "mode": mode_name,
                    "corpus_version": index_manifest["dataset_version"],
                    "index_version": index_manifest["index_version"],
                    "bm25_rank": b_info[0] if b_info else None,
                    "bm25_score": round(b_info[1], 6) if b_info else 0.0,
                    "dense_rank": d_info[0] if d_info else None,
                    "dense_score": round(d_info[1], 6) if d_info else None,
                    "rrf_score": round(rrf_scores.get(idx, 0.0), 6),
                })
            return out_rows

        runs_by_mode["bm25_only"].extend(make_rows("bm25_only", bm25_ranked, "bm25s_lucene"))
        runs_by_mode["dense_only"].extend(make_rows("dense_only", dense_ranked, "bge_m3_cosine"))
        runs_by_mode["hybrid_rrf"].extend(make_rows("hybrid_rrf", rrf_ranked, "rrf_k60"))
        runs_by_mode["hybrid_rrf_rerank"].extend(
            make_rows("hybrid_rrf_rerank", reranked_head, "bge_reranker_v2_m3_logit")
        )

        top1_ce_logit = reranked_head[0][1] if reranked_head else float("-inf")
        top1_ce_prob = 1.0 / (1.0 + math.exp(-max(min(top1_ce_logit, 50.0), -50.0)))
        query_diagnostics.append({
            "query_id": qid,
            "batch_group": q["batch_group"],
            "topic": q["topic"],
            "query": qtext,
            "bm25_hits": len(bm25_ranked),
            "top1_bm25": search_inputs[bm25_ranked[0][0]]["citation_path"] if bm25_ranked else None,
            "top1_dense": search_inputs[dense_ranked[0][0]]["citation_path"],
            "top1_rrf": search_inputs[rrf_ranked[0][0]]["citation_path"],
            "top1_rerank": search_inputs[reranked_head[0][0]]["citation_path"],
            "top1_rerank_logit": round(top1_ce_logit, 4),
            "top1_rerank_sigmoid": round(top1_ce_prob, 4),
            "timings_ms": {
                "bm25": round(ms_bm25, 2),
                "dense_query": round(ms_dense, 2),
                "rerank_top30": round(ms_rerank, 2),
            },
        })

    rerank_meta = {
        "reranker_model_id": RERANK_MODEL_ID,
        "reranker_revision_sha": rerank_commit,
        "fusion_method": "rrf",
        "rrf_k": RRF_K,
        "rerank_depth": RERANK_DEPTH,
        "rerank_max_length": RERANK_MAX_LENGTH,
        "top_k": TOP_K,
        "heuristic_weight_multipliers": False,
    }
    return runs_by_mode, query_diagnostics, rerank_meta


def evaluate_if_accepted_labels_exist(runs_by_mode: dict[str, list[dict]]):
    accepted_path = ROOT / "staging" / "subset-v6-accepted-labels-001" / "accepted.annotations.jsonl"
    if not accepted_path.exists():
        print("\n[Info] Khong tim thay staging/subset-v6-accepted-labels-001/accepted.annotations.jsonl -> bo qua cham 5 cau accepted.")
        return None

    print("\n" + "=" * 72)
    print("DOI CHIEU TREN 5 CAU ACCEPTED LABELS V6 (SESSION 16/17)")
    print("=" * 72)
    ann_rows = read_jsonl(accepted_path)
    qrels: dict[str, dict[str, int]] = {}
    for row in ann_rows:
        if row.get("status") == "accepted":
            qrels.setdefault(row["query_id"], {})[row["record_id"]] = int(row["relevance"])

    eval_qids = sorted(qrels.keys())
    summary_table = {}
    for mode, run_rows in runs_by_mode.items():
        by_q: dict[str, list[dict]] = {}
        for r in run_rows:
            if r["query_id"] in qrels:
                by_q.setdefault(r["query_id"], []).append(r)

        p10_d, hit10_d, mrr10_d = [], [], []
        p10_u, hit10_u, mrr10_u = [], [], []
        ndcg10_list = []

        for qid in eval_qids:
            judgments = qrels[qid]
            hits = sorted(by_q.get(qid, []), key=lambda x: x["rank"])[:10]
            rels = [judgments.get(h["record_id"], 0) for h in hits]

            p10_d.append(sum(1 for rel in rels if rel == 2) / 10.0)
            hit10_d.append(1.0 if any(rel == 2 for rel in rels) else 0.0)
            rr_d = next((1.0 / (i + 1) for i, rel in enumerate(rels) if rel == 2), 0.0)
            mrr10_d.append(rr_d)

            p10_u.append(sum(1 for rel in rels if rel >= 1) / 10.0)
            hit10_u.append(1.0 if any(rel >= 1 for rel in rels) else 0.0)
            rr_u = next((1.0 / (i + 1) for i, rel in enumerate(rels) if rel >= 1), 0.0)
            mrr10_u.append(rr_u)

            gains = [(2**rel - 1) for rel in rels]
            dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
            ideal_rels = sorted(judgments.values(), reverse=True)[:10]
            ideal_gains = [(2**rel - 1) for rel in ideal_rels]
            idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))
            ndcg10_list.append(dcg / idcg if idcg > 0 else 0.0)

        n = len(eval_qids)
        summary_table[mode] = {
            "Direct_P@10": round(sum(p10_d) / n, 4),
            "Direct_Hit@10": round(sum(hit10_d) / n, 4),
            "Direct_MRR@10": round(sum(mrr10_d) / n, 4),
            "Useful_P@10": round(sum(p10_u) / n, 4),
            "Useful_Hit@10": round(sum(hit10_u) / n, 4),
            "Useful_MRR@10": round(sum(mrr10_u) / n, 4),
            "nDCG@10_pool": round(sum(ndcg10_list) / n, 6),
        }
        print(f"{mode:18s} -> {summary_table[mode]}")
    return summary_table


def step3_and_4_export_handoff(
    runs_by_mode: dict[str, list[dict]],
    query_diagnostics: list[dict],
    dense_manifest: dict,
    rerank_meta: dict,
    index_manifest: dict,
    frames_by_id: dict[str, dict],
    eval_summary: dict | None,
):
    print("\n" + "=" * 72)
    print("BUOC 3 & 4: XUAT RUN LOGS CHO LONG & HYDRATION CHECK")
    print("=" * 72)

    runs_dir = OUT_DIR / "runs"
    for mode, rows in runs_by_mode.items():
        write_jsonl(runs_dir / f"{mode}.top10.jsonl", rows)

    write_jsonl(OUT_DIR / "query_diagnostics.50q.jsonl", query_diagnostics)

    unique_rids = sorted({r["record_id"] for r in runs_by_mode["hybrid_rrf_rerank"]})
    hydrated_samples = []
    for rid in unique_rids:
        frame = frames_by_id[rid]
        rec = frame.get("record", frame)
        req = frame.get("required_read") or {}
        hydrated_samples.append({
            "record_id": rid,
            "record_type": rec.get("record_type"),
            "law_id": rec.get("law_id"),
            "citation_path": rec.get("citation_path"),
            "unit_reads_count": len(req.get("unit_reads", [])),
            "supporting_records_count": len(req.get("supporting_records", [])),
            "has_supporting_form": bool(req.get("supporting_forms")),
        })
    write_jsonl(OUT_DIR / "hydration_check.jsonl", hydrated_samples)
    print(f"Verified target_frames hydration for {len(hydrated_samples)} unique top-10 records.")

    target_a6k9b = "c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6"
    print("\n--- KIEM TRA CAU DEN DO (A6K9b: 168/2024/ND-CP Dieu 6 Khoan 9 Diem b) ---")
    for qd in query_diagnostics:
        if "đèn" in qd["query"].lower() or "tín hiệu" in qd["query"].lower():
            qid = qd["query_id"]
            print(f"Query [{qid}]: {qd['query']}")
            for mode in ["bm25_only", "dense_only", "hybrid_rrf", "hybrid_rrf_rerank"]:
                hits = [r for r in runs_by_mode[mode] if r["query_id"] == qid]
                found = next((h for h in hits if h["record_id"] == target_a6k9b), None)
                top1 = hits[0] if hits else None
                print(
                    f"  {mode:18s}: A6K9b_rank={found['rank'] if found else '>10'} | "
                    f"Top1=[{top1['rank']}] {top1['citation_path']} (score={top1['score']})"
                )

    print("\n--- KIEM TRA 5 CAU NGOAI PHAM VI (limits.queries.jsonl) ---")
    for qd in query_diagnostics:
        if qd["batch_group"] == "limit":
            print(
                f"  [{qd['query_id']}] {qd['query'][:55]:55s} | "
                f"CE_logit={qd['top1_rerank_logit']:7.3f} | CE_prob={qd['top1_rerank_sigmoid']:.4f}"
            )

    handoff_manifest = {
        "handoff_version": "vtls-retrieval-v6-handoff.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "bm25s_version": bm25s.__version__,
            "numpy_version": np.__version__,
        },
        "source_bindings": {
            "dataset_version": index_manifest["dataset_version"],
            "index_version": index_manifest["index_version"],
            "dataset_manifest_sha256": index_manifest["dataset_manifest_sha256"],
            "index_manifest_sha256": sha256_file(V6_BM25_DIR / "index_manifest.json"),
            "queries_manifest_sha256": index_manifest["queries_manifest_sha256"],
        },
        "dense_manifest": dense_manifest,
        "hybrid_rerank_config": rerank_meta,
        "five_query_accepted_eval": eval_summary,
        "outputs": {
            "bm25_only": "runs/bm25_only.top10.jsonl",
            "dense_only": "runs/dense_only.top10.jsonl",
            "hybrid_rrf": "runs/hybrid_rrf.top10.jsonl",
            "hybrid_rrf_rerank": "runs/hybrid_rrf_rerank.top10.jsonl",
            "query_diagnostics": "query_diagnostics.50q.jsonl",
            "hydration_check": "hydration_check.jsonl",
        },
    }
    write_json(OUT_DIR / "handoff_manifest.json", handoff_manifest)
    print(f"\nHOAN TAT TOAN BO! Tat ca artifact da xuat tai: {OUT_DIR}")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    (
        index_manifest,
        bm25_cfg,
        search_inputs,
        queries,
        bm25_engine,
        frames_by_id,
        doc_embeddings,
        dense_manifest,
    ) = load_v6_inputs()

    dense_rankings, dense_timings = precompute_dense_queries(
        queries, doc_embeddings, search_inputs, device
    )
    runs_by_mode, query_diagnostics, rerank_meta = step2_hybrid_and_rerank(
        queries,
        search_inputs,
        index_manifest,
        bm25_cfg,
        bm25_engine,
        dense_rankings,
        dense_timings,
        device,
    )
    eval_summary = evaluate_if_accepted_labels_exist(runs_by_mode)
    step3_and_4_export_handoff(
        runs_by_mode,
        query_diagnostics,
        dense_manifest,
        rerank_meta,
        index_manifest,
        frames_by_id,
        eval_summary,
    )


if __name__ == "__main__":
    main()