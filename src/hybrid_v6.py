"""Pinned v6 Hybrid Retrieval + Cross-Encoder Reranker adapter (bm25s + BAAI/bge-m3 + RRF + bge-reranker-v2-m3)."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Prevent Python from writing __pycache__ inside immutable v6 dataset directories.
sys.dont_write_bytecode = True

import numpy as np
import torch
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

DENSE_VERSION = "vtls-dense-bge-m3.v1"
HANDOFF_VERSION = "vtls-retrieval-v6-hybrid-handoff.v3"
DATASET_VERSION = "vtls-subset-experimental.v6-candidate.1"
INDEX_VERSION = "vtls-bm25s-subset.v2"

DENSE_MODEL_ID = "BAAI/bge-m3"
DENSE_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
RERANKER_MODEL_ID = "BAAI/bge-reranker-v2-m3"
RERANKER_MODEL_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"

EXPECTED_NUM_DOCS = 139
EXPECTED_EMBEDDING_DIM = 1024
RRF_K = 60
RERANK_DEPTH = 30
DENSE_CONTROL_FILES = {"dense_manifest.json", "dense_manifest.sha256"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hashed_obj(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def write_json_lf(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_jsonl_lf(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                rows.append(json.loads(s))
    return rows


def dense_inventory(root: Path) -> list[dict[str, Any]]:
    items = []
    for p in sorted(root.rglob("*"), key=lambda x: x.relative_to(root).as_posix()):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and rel not in DENSE_CONTROL_FILES:
            items.append({
                "path": rel,
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            })
    return items


def collect_environment_info() -> dict[str, Any]:
    cpu_name = platform.processor()
    ram_gb = None
    gpu_name = "None"
    try:
        cpu_name = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
            text=True,
        ).strip()
        ram_gb = float(
            subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)"],
                text=True,
            ).strip()
        )
        gpu_name = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name -join '; '"],
            text=True,
        ).strip()
    except Exception:
        pass

    import bm25s
    import huggingface_hub
    import scipy
    import transformers

    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu_name": cpu_name,
        "cpu_logical_cores": os.cpu_count(),
        "ram_gb": ram_gb,
        "gpu": gpu_name,
        "inference_device": "cpu" if not torch.cuda.is_available() else "cuda",
        "cuda_available": bool(torch.cuda.is_available()),
        "python_version": sys.version.split()[0],
        "unicodedata_version": unicodedata.unidata_version,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "bm25s_version": bm25s.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "huggingface_hub_version": huggingface_hub.__version__,
    }


def load_bm25_v2_module(bm25_root: Path):
    bm25_root = Path(bm25_root).resolve()
    adapter_path = bm25_root / "src" / "subset_bm25_v6.py"
    if not adapter_path.exists():
        raise FileNotFoundError(f"Official BM25 v2 adapter not found: {adapter_path}")
    bm25_root_str = str(bm25_root)
    saved_sys_path = list(sys.path)
    saved_src_mods = {k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")}
    try:
        for k in list(saved_src_mods):
            del sys.modules[k]
        sys.path.insert(0, bm25_root_str)
        spec = importlib.util.spec_from_file_location("official_subset_bm25_v6", adapter_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = saved_sys_path
        for k in [k for k in sys.modules if k == "src" or k.startswith("src.")]:
            del sys.modules[k]
        sys.modules.update(saved_src_mods)


def load_bm25_v2_index(bm25_root: Path) -> tuple[Any, dict[str, Any], float]:
    """Load and validate frozen BM25 v2 index + v6 Consumer via official adapter."""
    t0 = time.perf_counter()
    bm25_root = Path(bm25_root).resolve()
    for pyc in bm25_root.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)
    mod = load_bm25_v2_module(bm25_root)
    state = mod.load_index(bm25_root)
    for pyc in bm25_root.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return mod, state, elapsed_ms


def build_query_binding(
    queries_dir: Path,
    bm25_manifest: dict[str, Any],
    queries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Seal query manifest and query list SHA-256 so manifests cannot point to a drifted query file."""
    queries_dir = Path(queries_dir).resolve()
    q_manifest_path = queries_dir / "manifest.json"
    actual_q_manifest_sha = sha256_file(q_manifest_path)
    if actual_q_manifest_sha != bm25_manifest["queries_manifest_sha256"]:
        raise ValueError(
            f"Queries manifest SHA-256 mismatch: expected {bm25_manifest['queries_manifest_sha256']}, got {actual_q_manifest_sha}"
        )
    files_inv = []
    for p in sorted(queries_dir.rglob("*"), key=lambda x: x.relative_to(queries_dir).as_posix()):
        if p.is_file():
            files_inv.append({
                "path": p.relative_to(queries_dir).as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            })
    canonical_queries = [
        {"query_id": q["query_id"], "batch_group": q["batch_group"], "query": q["query"]}
        for q in queries
    ]
    return {
        "queries_manifest_sha256": actual_q_manifest_sha,
        "queries_count": len(queries),
        "queries_files": files_inv,
        "queries_files_sha256": hashed_obj(files_inv),
        "queries_canonical_sha256": hashed_obj(canonical_queries),
    }


def load_pinned_dense_encoder(
    model_id: str = DENSE_MODEL_ID,
    revision: str = DENSE_MODEL_REVISION,
    local_files_only: bool = True,
) -> dict[str, Any]:
    """Load BAAI/bge-m3 tokenizer and model with strictly pinned revision SHA."""
    if not revision or len(revision) != 40:
        raise ValueError(f"Dense encoder revision must be a 40-char commit SHA, got: {revision!r}")
    t0 = time.perf_counter()
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
        model = AutoModel.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load pinned dense encoder {model_id}@{revision} (local_files_only={local_files_only}): {exc}"
        ) from exc
    model.eval()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "model_id": model_id,
        "model_revision": revision,
        "tokenizer_revision": revision,
        "tokenizer": tokenizer,
        "model": model,
        "load_ms": elapsed_ms,
    }


def load_pinned_reranker(
    model_id: str = RERANKER_MODEL_ID,
    revision: str = RERANKER_MODEL_REVISION,
    local_files_only: bool = True,
) -> dict[str, Any]:
    """Load BAAI/bge-reranker-v2-m3 tokenizer and cross-encoder with strictly pinned revision SHA."""
    if not revision or len(revision) != 40:
        raise ValueError(f"Reranker revision must be a 40-char commit SHA, got: {revision!r}")
    t0 = time.perf_counter()
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load pinned reranker {model_id}@{revision} (local_files_only={local_files_only}): {exc}"
        ) from exc
    model.eval()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "model_id": model_id,
        "model_revision": revision,
        "tokenizer_revision": revision,
        "tokenizer": tokenizer,
        "model": model,
        "load_ms": elapsed_ms,
    }


def generate_and_seal_dense_bundle(
    bm25_state: dict[str, Any],
    encoder_bundle: dict[str, Any],
    query_binding: dict[str, Any],
    out_dense_dir: Path,
    batch_size: int = 8,
    max_length: int = 512,
) -> dict[str, Any]:
    """Directly encode all 139 pinned v6 records from BAAI/bge-m3 and seal manifest + per-row SHA-256."""
    if out_dense_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing dense bundle directory: {out_dense_dir}")
    out_dense_dir.mkdir(parents=True, exist_ok=False)

    mapping = bm25_state["mapping"]
    projected = bm25_state["projected"]
    if len(mapping) != EXPECTED_NUM_DOCS or len(projected) != EXPECTED_NUM_DOCS:
        raise ValueError(f"Expected {EXPECTED_NUM_DOCS} records, got mapping={len(mapping)}, projected={len(projected)}")

    texts: list[str] = []
    for i, (m_row, p_row) in enumerate(zip(mapping, projected)):
        if p_row.get("record_id") != m_row["record_id"]:
            raise ValueError(f"Projected search_inputs misaligned at row {i}: {p_row.get('record_id')} != {m_row['record_id']}")
        texts.append(p_row["text_for_search"])

    tokenizer = encoder_bundle["tokenizer"]
    model = encoder_bundle["model"]

    t0 = time.perf_counter()
    audit_rows: list[dict[str, Any]] = []
    for m_row, text in zip(mapping, texts):
        untruncated_ids = tokenizer.encode(text, add_special_tokens=True, truncation=False)
        tok_count = len(untruncated_ids)
        audit_rows.append({
            "record_id": m_row["record_id"],
            "record_type": m_row["record_type"],
            "law_id": m_row["law_id"],
            "citation_path": m_row["citation_path"],
            "char_count": len(text),
            "bge_m3_token_count": tok_count,
            "exceeds_512": tok_count > 512,
            "exceeds_1024": tok_count > 1024,
            "exceeds_2048": tok_count > 2048,
        })

    emb_chunks: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch_texts = texts[start : start + batch_size]
            encoded = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            outputs = model(**encoded)
            cls_emb = outputs.last_hidden_state[:, 0]
            cls_emb = torch.nn.functional.normalize(cls_emb, p=2, dim=1)
            emb_chunks.append(cls_emb.cpu().numpy().astype(np.float32))

    emb = np.vstack(emb_chunks).astype(np.float32)
    encode_corpus_ms = (time.perf_counter() - t0) * 1000.0

    if emb.shape != (EXPECTED_NUM_DOCS, EXPECTED_EMBEDDING_DIM):
        raise ValueError(f"Unexpected encoded embedding shape {emb.shape}")
    norms = np.linalg.norm(emb, axis=1)
    if not np.all(np.isfinite(emb)) or not np.allclose(norms, 1.0, atol=1e-4):
        raise ValueError("Newly generated dense embeddings are not finite L2-normalized unit vectors")

    emb_out = out_dense_dir / "embeddings.npy"
    np.save(emb_out, emb)
    write_jsonl_lf(out_dense_dir / "tokenizer_audit.jsonl", audit_rows)

    record_rows: list[dict[str, Any]] = []
    for i, m in enumerate(mapping):
        row_sha = sha256_bytes(emb[i].tobytes())
        record_rows.append({
            "internal_doc_id": i,
            "record_id": m["record_id"],
            "record_type": m["record_type"],
            "source_id": m["source_id"],
            "law_id": m["law_id"],
            "unit_id": m["unit_id"],
            "citation_path": m["citation_path"],
            "content_sha256": m["content_sha256"],
            "payload_sha256": m["payload_sha256"],
            "row_vector_sha256": row_sha,
            "l2_norm": round(float(norms[i]), 6),
        })
    write_jsonl_lf(out_dense_dir / "records.jsonl", record_rows)

    bm25_manifest = bm25_state["manifest"]
    bm25_root = bm25_state["root"]
    inv = dense_inventory(out_dense_dir)
    token_counts = [r["bge_m3_token_count"] for r in audit_rows]

    manifest = {
        "dense_version": DENSE_VERSION,
        "generated_from_pinned_model_directly": True,
        "corpus_encode_elapsed_ms": round(encode_corpus_ms, 3),
        "dataset_version": bm25_manifest["dataset_version"],
        "index_version": bm25_manifest["index_version"],
        "dataset_manifest_sha256": bm25_manifest["dataset_manifest_sha256"],
        "index_manifest_sha256": sha256_file(bm25_root / "index_manifest.json"),
        "search_inputs_sha256": bm25_manifest["search_inputs_sha256"],
        "membership_sha256": bm25_manifest["membership_sha256"],
        "queries_manifest_sha256": query_binding["queries_manifest_sha256"],
        "queries_files_sha256": query_binding["queries_files_sha256"],
        "queries_canonical_sha256": query_binding["queries_canonical_sha256"],
        "model_id": encoder_bundle["model_id"],
        "model_revision": encoder_bundle["model_revision"],
        "tokenizer_id": encoder_bundle["model_id"],
        "tokenizer_revision": encoder_bundle["tokenizer_revision"],
        "pooling": "cls",
        "max_length": max_length,
        "normalized": True,
        "dtype": "float32",
        "num_docs": len(mapping),
        "embedding_dim": EXPECTED_EMBEDDING_DIM,
        "embeddings_npy_sha256": sha256_file(emb_out),
        "records_jsonl_sha256": sha256_file(out_dense_dir / "records.jsonl"),
        "row_order_sha256": hashed_obj(
            [{"internal_doc_id": r["internal_doc_id"], "record_id": r["record_id"], "row_vector_sha256": r["row_vector_sha256"]} for r in record_rows]
        ),
        "tokenizer_audit_summary": {
            "total_records": len(mapping),
            "min_tokens": int(min(token_counts)),
            "median_tokens": int(np.median(token_counts)),
            "p95_tokens": int(np.percentile(token_counts, 95)),
            "max_tokens": int(max(token_counts)),
            "exceeding_512": sum(1 for t in token_counts if t > 512),
            "exceeding_1024": sum(1 for t in token_counts if t > 1024),
            "exceeding_2048": sum(1 for t in token_counts if t > 2048),
        },
        "files": inv,
        "dense_content_sha256": hashed_obj(inv),
    }
    manifest_path = out_dense_dir / "dense_manifest.json"
    write_json_lf(manifest_path, manifest)
    (out_dense_dir / "dense_manifest.sha256").write_text(sha256_file(manifest_path) + "\n", encoding="ascii")
    return manifest


def compare_dense_vectors(
    old_embeddings_npy: Path,
    new_embeddings_npy: Path,
    mapping: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audit numerical & SHA-256 comparison between newly encoded vectors and previous handoff vectors."""
    if not old_embeddings_npy.exists():
        return {
            "status": "previous_embeddings_not_present_on_disk",
            "new_embeddings_npy_sha256": sha256_file(new_embeddings_npy),
            "num_rows": len(mapping),
            "exact_byte_identical_rows": 0,
            "max_abs_diff": 0.0,
            "min_row_cosine_similarity": 1.0,
        }
    old_emb = np.load(old_embeddings_npy).astype(np.float32)
    new_emb = np.load(new_embeddings_npy).astype(np.float32)
    if old_emb.shape != new_emb.shape:
        raise ValueError(f"Shape mismatch comparing old vs new embeddings: {old_emb.shape} vs {new_emb.shape}")
    abs_diff = np.abs(new_emb - old_emb)
    row_cos = np.sum(new_emb * old_emb, axis=1)
    exact_byte_rows = sum(
        1 for i in range(len(mapping)) if sha256_bytes(new_emb[i].tobytes()) == sha256_bytes(old_emb[i].tobytes())
    )
    return {
        "old_embeddings_npy_sha256": sha256_file(old_embeddings_npy),
        "new_embeddings_npy_sha256": sha256_file(new_embeddings_npy),
        "identical_file_bytes": sha256_file(old_embeddings_npy) == sha256_file(new_embeddings_npy),
        "num_rows": len(mapping),
        "exact_byte_identical_rows": exact_byte_rows,
        "max_abs_diff": float(np.max(abs_diff)),
        "mean_abs_diff": float(np.mean(abs_diff)),
        "min_row_cosine_similarity": float(np.min(row_cos)),
        "mean_row_cosine_similarity": float(np.mean(row_cos)),
        "rows_with_cosine_gt_0_99999": int(np.sum(row_cos > 0.99999)),
    }


def load_dense_bundle(
    bm25_state: dict[str, Any],
    dense_dir: Path,
    expected_query_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Strictly validate and load dense embeddings; reject hash, version, query-list, or vector-order mismatch."""
    t0 = time.perf_counter()
    dense_dir = Path(dense_dir).resolve()
    manifest_path = dense_dir / "dense_manifest.json"
    sha_path = dense_dir / "dense_manifest.sha256"
    if not manifest_path.exists() or not sha_path.exists():
        raise ValueError(f"Missing dense_manifest.json or dense_manifest.sha256 in {dense_dir}")

    actual_manifest_sha = sha256_file(manifest_path)
    expected_manifest_sha = sha_path.read_text(encoding="ascii").strip()
    if actual_manifest_sha != expected_manifest_sha:
        raise ValueError(
            f"Dense manifest hash mismatch: expected {expected_manifest_sha}, got {actual_manifest_sha}"
        )

    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_inv = dense_inventory(dense_dir)
    if actual_inv != m.get("files") or hashed_obj(actual_inv) != m.get("dense_content_sha256"):
        raise ValueError("Dense directory inventory/content hash mismatch")

    bm25_manifest = bm25_state["manifest"]
    bm25_root = bm25_state["root"]
    if m.get("dense_version") != DENSE_VERSION:
        raise ValueError(f"Dense version mismatch: expected {DENSE_VERSION}, got {m.get('dense_version')}")
    if (
        m.get("dataset_version") != DATASET_VERSION
        or m.get("dataset_version") != bm25_manifest["dataset_version"]
        or m.get("index_version") != INDEX_VERSION
        or m.get("index_version") != bm25_manifest["index_version"]
    ):
        raise ValueError("Dense dataset/index version mismatch against pinned v6")
    if (
        m.get("dataset_manifest_sha256") != bm25_manifest["dataset_manifest_sha256"]
        or m.get("index_manifest_sha256") != sha256_file(bm25_root / "index_manifest.json")
        or m.get("search_inputs_sha256") != bm25_manifest["search_inputs_sha256"]
        or m.get("membership_sha256") != bm25_manifest["membership_sha256"]
        or m.get("queries_manifest_sha256") != bm25_manifest["queries_manifest_sha256"]
    ):
        raise ValueError("Dense upstream dataset/index/queries manifest SHA-256 binding mismatch")

    if expected_query_binding is not None:
        if (
            m.get("queries_manifest_sha256") != expected_query_binding["queries_manifest_sha256"]
            or m.get("queries_files_sha256") != expected_query_binding["queries_files_sha256"]
            or m.get("queries_canonical_sha256") != expected_query_binding["queries_canonical_sha256"]
        ):
            raise ValueError("Dense query-set hash mismatch against pinned evaluation query list")

    if (
        m.get("model_id") != DENSE_MODEL_ID
        or m.get("model_revision") != DENSE_MODEL_REVISION
        or m.get("tokenizer_id") != DENSE_MODEL_ID
        or m.get("tokenizer_revision") != DENSE_MODEL_REVISION
    ):
        raise ValueError(
            f"Dense model/tokenizer revision mismatch: expected {DENSE_MODEL_ID}@{DENSE_MODEL_REVISION}, "
            f"got {m.get('model_id')}@{m.get('model_revision')} / tok={m.get('tokenizer_revision')}"
        )

    emb_path = dense_dir / "embeddings.npy"
    records_path = dense_dir / "records.jsonl"
    if sha256_file(emb_path) != m.get("embeddings_npy_sha256"):
        raise ValueError("embeddings.npy SHA-256 mismatch")
    if sha256_file(records_path) != m.get("records_jsonl_sha256"):
        raise ValueError("records.jsonl SHA-256 mismatch")

    emb = np.load(emb_path)
    records = read_jsonl(records_path)
    mapping = bm25_state["mapping"]

    if len(mapping) != EXPECTED_NUM_DOCS or emb.shape != (len(mapping), EXPECTED_EMBEDDING_DIM):
        raise ValueError(f"Dense vector matrix shape mismatch: got {emb.shape}, expected ({len(mapping)}, {EXPECTED_EMBEDDING_DIM})")
    if emb.dtype != np.float32 or not np.all(np.isfinite(emb)):
        raise ValueError("Dense vector matrix dtype/finiteness check failed")
    norms = np.linalg.norm(emb, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise ValueError("Dense vectors are not L2-normalized")
    if len(records) != len(mapping):
        raise ValueError(f"Dense records count mismatch: got {len(records)}, expected {len(mapping)}")

    for i, (m_row, d_row) in enumerate(zip(mapping, records)):
        if d_row.get("internal_doc_id") != i:
            raise ValueError(f"Dense internal_doc_id out of sequence at row {i}: got {d_row.get('internal_doc_id')}")
        if d_row.get("record_id") != m_row["record_id"]:
            raise ValueError(
                f"Dense record_id order mismatch at row {i}: expected {m_row['record_id']}, got {d_row.get('record_id')}"
            )
        if (
            d_row.get("record_type") != m_row["record_type"]
            or d_row.get("unit_id") != m_row["unit_id"]
            or d_row.get("content_sha256") != m_row["content_sha256"]
        ):
            raise ValueError(f"Dense metadata/content hash mismatch at row {i} ({m_row['record_id']})")
        actual_row_sha = sha256_bytes(emb[i].tobytes())
        if actual_row_sha != d_row.get("row_vector_sha256"):
            raise ValueError(
                f"Dense vector row order/content mismatch at row {i} ({m_row['record_id']}): "
                f"expected {d_row.get('row_vector_sha256')}, got {actual_row_sha}"
            )

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "dense_dir": dense_dir,
        "manifest": m,
        "embeddings": emb,
        "records": records,
        "record_id_to_idx": {r["record_id"]: i for i, r in enumerate(records)},
        "load_validate_ms": elapsed_ms,
    }


def encode_query_dense(encoder_bundle: dict[str, Any], query: str, max_length: int = 512) -> np.ndarray:
    tokenizer = encoder_bundle["tokenizer"]
    model = encoder_bundle["model"]
    with torch.inference_mode():
        encoded = tokenizer(
            [query],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        outputs = model(**encoded)
        cls_emb = outputs.last_hidden_state[:, 0]
        cls_emb = torch.nn.functional.normalize(cls_emb, p=2, dim=1)
        vec = cls_emb[0].cpu().numpy().astype(np.float32)
    return vec


def search_bm25_v2(
    bm25_mod: Any,
    bm25_state: dict[str, Any],
    query: str,
    top_k: int = 10,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    ans = bm25_mod.search_loaded(bm25_state, query, top_k=top_k)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "query": query,
        "results": ans["results"],
        "measured_total_ms": elapsed_ms,
    }


def search_dense_only(
    bm25_state: dict[str, Any],
    dense_bundle: dict[str, Any],
    encoder_bundle: dict[str, Any],
    query: str,
    top_k: int = 10,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    q_vec = encode_query_dense(encoder_bundle, query)
    scores = dense_bundle["embeddings"] @ q_vec
    mapping = bm25_state["mapping"]
    order = sorted(range(len(mapping)), key=lambda idx: (-float(scores[idx]), mapping[idx]["record_id"]))
    hits = []
    for rank, idx in enumerate(order[:top_k], 1):
        row = mapping[idx]
        hits.append({
            **{k: row[k] for k in ["record_id", "record_type", "source_id", "law_id", "unit_id", "citation_path"]},
            "rank": rank,
            "score": float(scores[idx]),
            "score_type": "bge_m3_cosine",
            "model_id": encoder_bundle["model_id"],
            "model_revision": encoder_bundle["model_revision"],
            "dataset_version": DATASET_VERSION,
            "index_version": INDEX_VERSION,
            "experimental": True,
            "release_eligible": False,
        })
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "query": query,
        "results": hits,
        "measured_total_ms": elapsed_ms,
    }


def search_hybrid_rrf(
    bm25_mod: Any,
    bm25_state: dict[str, Any],
    dense_bundle: dict[str, Any],
    encoder_bundle: dict[str, Any],
    query: str,
    top_k: int = 10,
    rrf_pool_k: int = RERANK_DEPTH,
    rrf_k: int = RRF_K,
) -> dict[str, Any]:
    """End-to-end Hybrid RRF (local NumPy cosine + BM25s + RRF k=60)."""
    t_total_0 = time.perf_counter()
    mapping = bm25_state["mapping"]
    num_docs = len(mapping)

    t_enc_0 = time.perf_counter()
    q_vec = encode_query_dense(encoder_bundle, query)
    encode_ms = (time.perf_counter() - t_enc_0) * 1000.0

    t_dense_0 = time.perf_counter()
    dense_scores = dense_bundle["embeddings"] @ q_vec
    dense_order = sorted(range(num_docs), key=lambda idx: (-float(dense_scores[idx]), mapping[idx]["record_id"]))
    dense_rank_map: dict[str, int] = {}
    dense_score_map: dict[str, float] = {}
    for rank, idx in enumerate(dense_order, 1):
        rid = mapping[idx]["record_id"]
        dense_rank_map[rid] = rank
        dense_score_map[rid] = float(dense_scores[idx])
    dense_ms = (time.perf_counter() - t_dense_0) * 1000.0

    t_bm25_0 = time.perf_counter()
    bm25_ans = bm25_mod.search_loaded(bm25_state, query, top_k=num_docs)
    bm25_rank_map: dict[str, int] = {}
    bm25_score_map: dict[str, float] = {}
    for h in bm25_ans["results"]:
        rid = h["record_id"]
        bm25_rank_map[rid] = int(h["rank"])
        bm25_score_map[rid] = float(h["score"])
    bm25_ms = (time.perf_counter() - t_bm25_0) * 1000.0

    t_rrf_0 = time.perf_counter()
    fused: list[dict[str, Any]] = []
    for idx, row in enumerate(mapping):
        rid = row["record_id"]
        b_rank = bm25_rank_map.get(rid)
        d_rank = dense_rank_map.get(rid)
        b_score = bm25_score_map.get(rid, 0.0)
        d_score = dense_score_map[rid]
        rrf_score = (1.0 / (rrf_k + b_rank) if b_rank is not None else 0.0) + (
            1.0 / (rrf_k + d_rank) if d_rank is not None else 0.0
        )
        fused.append({
            "internal_doc_id": idx,
            "record_id": rid,
            "record_type": row["record_type"],
            "source_id": row["source_id"],
            "law_id": row["law_id"],
            "unit_id": row["unit_id"],
            "citation_path": row["citation_path"],
            "bm25_rank": b_rank,
            "bm25_score": b_score,
            "dense_rank": d_rank,
            "dense_score": d_score,
            "rrf_score": rrf_score,
        })

    fused.sort(
        key=lambda x: (
            -x["rrf_score"],
            x["dense_rank"] if x["dense_rank"] is not None else 999999,
            x["bm25_rank"] if x["bm25_rank"] is not None else 999999,
            x["record_id"],
        )
    )

    pool = []
    for r_rank, item in enumerate(fused[:rrf_pool_k], 1):
        pool.append({
            **item,
            "rrf_rank": r_rank,
            "rank": r_rank,
            "score": item["rrf_score"],
            "score_type": f"rrf_k{rrf_k}",
            "dense_backend": "numpy_local_cosine_f32",
            "dense_model_id": encoder_bundle["model_id"],
            "dense_model_revision": encoder_bundle["model_revision"],
            "dataset_version": DATASET_VERSION,
            "index_version": INDEX_VERSION,
            "experimental": True,
            "release_eligible": False,
        })
    rrf_ms = (time.perf_counter() - t_rrf_0) * 1000.0
    total_ms = (time.perf_counter() - t_total_0) * 1000.0

    return {
        "query": query,
        "results": copy.deepcopy(pool[:top_k]),
        "rrf_top_pool": pool,
        "timings_ms": {
            "encode_query_ms": encode_ms,
            "dense_search_ms": dense_ms,
            "bm25_search_ms": bm25_ms,
            "rrf_fusion_ms": rrf_ms,
            "total_ms": total_ms,
        },
        "measured_total_ms": total_ms,
    }


def rerank_rrf_candidates(
    bm25_state: dict[str, Any],
    reranker_bundle: dict[str, Any],
    query: str,
    rrf_candidates: list[dict[str, Any]],
    top_k: int = 10,
    max_length: int = 1024,
    batch_size: int = 2,
) -> dict[str, Any]:
    """Offline/optional Cross-Encoder reranking on Top-30 RRF candidates using pinned BAAI/bge-reranker-v2-m3."""
    t0 = time.perf_counter()
    projected = bm25_state["projected"]
    tokenizer = reranker_bundle["tokenizer"]
    model = reranker_bundle["model"]

    indexed_cands = list(enumerate(rrf_candidates))
    indexed_cands.sort(key=lambda pair: len(projected[pair[1]["internal_doc_id"]]["text_for_search"]))

    logits_by_pos: dict[int, float] = {}
    with torch.inference_mode():
        for start in range(0, len(indexed_cands), batch_size):
            batch = indexed_cands[start : start + batch_size]
            pairs = [(query, projected[cand["internal_doc_id"]]["text_for_search"]) for _, cand in batch]
            inputs = tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            scores = model(**inputs, return_dict=True).logits.view(-1).float().cpu().tolist()
            for (orig_pos, _), logit in zip(batch, scores):
                logits_by_pos[orig_pos] = float(logit)

    annotated: list[dict[str, Any]] = []
    for pos, cand in enumerate(rrf_candidates):
        logit = logits_by_pos[pos]
        prob = 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, logit))))
        annotated.append({
            **cand,
            "reranker_logit": logit,
            "reranker_prob": prob,
        })

    annotated.sort(key=lambda x: (-x["reranker_logit"], x["rrf_rank"], x["record_id"]))
    for final_rank, item in enumerate(annotated, 1):
        item["final_rerank_rank"] = final_rank
        item["in_final_top10"] = final_rank <= top_k

    top10_hits = []
    for item in annotated[:top_k]:
        top10_hits.append({
            **{k: item[k] for k in [
                "record_id", "record_type", "source_id", "law_id", "unit_id", "citation_path",
                "bm25_rank", "bm25_score", "dense_rank", "dense_score", "rrf_rank", "rrf_score",
                "reranker_logit", "reranker_prob",
            ]},
            "rank": item["final_rerank_rank"],
            "score": item["reranker_logit"],
            "score_type": "bge_reranker_v2_m3_logit",
            "reranker_mode": "offline_optional",
            "reranker_model_id": reranker_bundle["model_id"],
            "reranker_model_revision": reranker_bundle["model_revision"],
            "dataset_version": DATASET_VERSION,
            "index_version": INDEX_VERSION,
            "experimental": True,
            "release_eligible": False,
        })

    rerank_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "query": query,
        "results": top10_hits,
        "annotated_top30": annotated,
        "rerank_only_ms": rerank_ms,
    }


def hydrate_record_via_consumer_v6(
    bm25_mod: Any,
    bm25_state: dict[str, Any],
    record_id: str,
) -> dict[str, Any]:
    """Hydrate record_id through genuine v6 Consumer via official read_loaded()."""
    wrapped = bm25_mod.read_loaded(bm25_state, record_id)
    detail = wrapped["dataset_response"]
    req = detail["required_read"]
    return {
        "record_id": detail["record_id"],
        "record_type": detail["record_type"],
        "dataset_version": detail["dataset_version"],
        "index_version": wrapped["index_version"],
        "dataset_response_sha256": wrapped["dataset_response_sha256"],
        "unit_reads_count": len(req["unit_reads"]),
        "unit_read_ids": [u["unit_id"] for u in req["unit_reads"]],
        "supporting_records_count": len(req["supporting_records"]),
        "supporting_record_ids": [s["record_id"] for s in req["supporting_records"]],
        "bindings_count": len(req["bindings"]),
        "structural_ancestor_ids": detail["structural_ancestor_ids"],
        "adapter_version": detail["technical_admission"]["adapter_version"],
        "legal_verified": detail["legal_verified"],
        "release_eligible": detail["release_eligible"],
        "full_envelope": wrapped,
    }