"""Saved BM25S Lucene-formula experimental baseline. No encoder or serving imports."""
import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import unicodedata

from src.config import BASE_DIR, SNAPSHOT_DATE
from src.source_contracts import canonical, digest, resolve_ref
from src.bm25_tokenizer import tokenize, validate_config as validate_tokenizer
from src.experimental_dataset import load, rows, write_json, write_rows, unique

DEFAULT_CONFIG = BASE_DIR / "config/bm25_baseline.v1.json"
VERSION = "vtls-bm25s-lucene.v1"
CONTROL = {"index_manifest.json", "index_manifest.sha256"}
# The existing v1 index predates this loader-only compatibility change.
# Do not reseal its manifest or accept arbitrary historical implementations.
ORIGINAL_V1_LOADER_SHA256 = "93f20a8a66e2d5f61b20b85b6f0199fc598b51bb3422d50598ca0a9700ee893c"


def check_config(config):
    validate_tokenizer(config)
    if canonical(config) != canonical(load(DEFAULT_CONFIG)):
        raise ValueError("Unknown BM25 configuration; version policy changes explicitly")


def runtime():
    versions = {p: metadata.version(p) for p in ["bm25s", "numpy", "scipy"]}
    required = {"bm25s": "0.3.13", "numpy": "2.4.6", "scipy": "1.17.1"}
    if versions != required: raise ValueError("Install requirements-bm25.txt: " + canonical(versions))
    package = Path(metadata.distribution("bm25s").locate_file("bm25s"))
    return {"dependencies": versions, "python": platform.python_version(), "unicode": unicodedata.unidata_version,
            "engine_source_sha256": {n: digest((package / n).read_bytes()) for n in ["__init__.py", "scoring.py"]}}


def engine(config):
    check_config(config); runtime()
    import bm25s
    return bm25s.BM25(k1=config["k1"], b=config["b"], method=config["method"],
                      idf_method=config["idf_method"], dtype=config["dtype"], int_dtype="int32",
                      backend=config["backend"], csc_backend=config["csc_backend"])


def ordered_documents(chunks):
    unique(chunks, "chunk_id"); unique(chunks, "unit_id")
    if not chunks: raise ValueError("Dataset has no documents")
    for c in chunks:
        if (not isinstance(c["chunk_id"], str) or not c["chunk_id"] or not c.get("unit_id")
                or not isinstance(c["text_for_search"], str) or not c["text_for_search"].strip()
                or digest(c["text_for_search"].encode()) != c["content_sha256"]):
            raise ValueError("Invalid chunk ID/unit/search content/hash")
    return sorted(chunks, key=lambda c: c["chunk_id"])


def create_index(chunks, config):
    ordered = ordered_documents(chunks)
    tokens = [tokenize(c["text_for_search"], config) for c in ordered]
    if any(not t for t in tokens): raise ValueError("Document has no lexical tokens")
    vocab = {t: i for i, t in enumerate(sorted({t for ts in tokens for t in ts}))}
    retriever = engine(config)
    retriever.index(([[vocab[t] for t in ts] for ts in tokens], vocab),
                    create_empty_token=False, show_progress=False)
    mapping = [{"internal_doc_id": i, **{k: c[k] for k in ["chunk_id", "unit_id", "content_sha256"]},
                "token_count": len(ts), "tokens_sha256": digest(canonical(ts).encode())}
               for i, (c, ts) in enumerate(zip(ordered, tokens))]
    return retriever, mapping


def check_mapping(mapping, chunks, config):
    unique(mapping, "internal_doc_id"); unique(mapping, "chunk_id"); unique(mapping, "unit_id")
    ordered = ordered_documents(chunks)
    if (len(mapping) != len(ordered) or any(type(r["internal_doc_id"]) is not int for r in mapping)
            or {r["internal_doc_id"] for r in mapping} != set(range(len(ordered)))):
        raise ValueError("Missing/duplicate/non-contiguous mapping IDs")
    by = {r["internal_doc_id"]: r for r in mapping}
    for i, c in enumerate(ordered):
        r = by[i]; ts = tokenize(c["text_for_search"], config)
        if (any(r[k] != c[k] for k in ["chunk_id", "unit_id", "content_sha256"])
                or r["token_count"] != len(ts) or r["tokens_sha256"] != digest(canonical(ts).encode())):
            raise ValueError("Internal ID/chunk/token mapping mismatch")
    return by


def rank(retriever, mapping, query, top_k, config):
    if type(top_k) is not int or top_k <= 0: raise ValueError("top_k must be a positive integer")
    tokens = tokenize(query, config)
    if not tokens or not any(any(ch.isalnum() for ch in t) for t in tokens):
        raise ValueError("Query must contain at least one letter/number token")
    known = [t for t in tokens if t in retriever.vocab_dict]
    if not known: return tokens, []
    import numpy as np
    scores = retriever.get_scores(known)
    if len(scores) != len(mapping) or not np.isfinite(scores).all(): raise ValueError("Invalid BM25 score vector")
    positive = [(int(i), float(s)) for i, s in enumerate(scores) if s > 0]
    positive.sort(key=lambda pair: (-pair[1], mapping[pair[0]]["chunk_id"]))
    return tokens, positive[:min(top_k, len(mapping))]


def code_binding():
    return {n: digest((BASE_DIR / n).read_bytes()) for n in ["src/bm25_baseline.py", "src/bm25_tokenizer.py"]}


def compatible_code_binding(stored):
    current = code_binding()
    if stored == current:
        return "exact"
    original = {**current, "src/bm25_baseline.py": ORIGINAL_V1_LOADER_SHA256}
    if stored == original:
        return "original_v1_loader_handoff_compatibility"
    raise ValueError("Index source binding mismatch: unknown loader or changed tokenizer")


def runtime_compatibility(created, running):
    """Conservative same-minor CPython compatibility; patch version is provenance."""
    for key in ["dependencies", "unicode", "engine_source_sha256"]:
        if created.get(key) != running.get(key):
            raise ValueError("Index runtime incompatibility: " + key)
    versions = [re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(r.get("python", ""))) for r in [created, running]]
    if (not all(versions) or versions[0].groups()[:2] != versions[1].groups()[:2]
            or versions[1].group(1) != "3" or platform.python_implementation() != "CPython"):
        raise ValueError("Index runtime incompatibility: require same CPython major/minor; patch may differ")
    notes = []
    if created["python"] != running["python"]:
        notes.append("PYTHON_PATCH_DIFFERS: built=" + created["python"] + "; running=" + running["python"])
    return {"policy": "bm25-runtime-compatibility.v1", "created": created, "running": running,
            "running_platform": platform.platform(), "running_implementation": platform.python_implementation(),
            "warnings": notes, "compatible": True}


def dataset_files_check(path):
    from src.retrieval_dataset import check_inventory
    path = Path(path); m = load(path)
    if (m["policy_version"] != "coverage-retrieval-dataset.v1" or m["snapshot_date"] != SNAPSHOT_DATE
            or m["experimental"] is not True or m["release_eligible"] is not False or m["corpus_version"] is not None
            or digest(path.read_bytes()) != (path.parent / "dataset_manifest.sha256").read_text().strip()
            or m["dataset_content_sha256"] != digest(canonical(m["files"]).encode())):
        raise ValueError("Dataset manifest/status/content binding mismatch")
    check_inventory(path.parent, m["files"], {"dataset_manifest.json", "dataset_manifest.sha256", "execution.json"})
    return m


def build(dataset_manifest, config_path, run_dir):
    from src.pipeline_cli import staging_path
    from src.retrieval_dataset import validate, files
    target = staging_path(run_dir); source = Path(dataset_manifest).resolve()
    if source.parent in target.parents: raise ValueError("Index output inside input dataset")
    cfg = load(config_path); check_config(cfg); runtime(); validate(source)
    chunks = rows(source.parent / "chunks.jsonl")
    retriever, mapping = create_index(chunks, cfg)
    target.mkdir(parents=True)
    # Snapshot only this compact export, never its recursive upstream history.
    shutil.copytree(source.parent, target / "dataset")
    write_json(target / "config.json", cfg); write_json(target / "runtime.json", runtime())
    write_rows(target / "document_mapping.jsonl", mapping)
    retriever.save(str(target / "engine"), allow_pickle=False, show_progress=False)
    dataset = load(source)
    report = {"technical_valid": True, "documents": len(chunks), "engine": "bm25s", "engine_version": "0.3.13",
              "method": "lucene", "idf_method": "lucene", "legal_verification": False, "release_eligible": False,
              "embedding_created": False, "inference_loaded": False}
    write_json(target / "validation_report.json", report)
    inv = files(target, CONTROL)
    write_json(target / "index_manifest.json", {"index_version": VERSION, "dataset_version": dataset["dataset_version"],
                "dataset_manifest_ref": "dataset/dataset_manifest.json", "dataset_manifest_sha256": digest(source.read_bytes()),
                "dataset_content_sha256": dataset["dataset_content_sha256"], "documents": len(chunks),
                "snapshot_date": SNAPSHOT_DATE, "experimental": True, "release_eligible": False,
                "config_sha256": digest((target / "config.json").read_bytes()), "runtime": runtime(),
                "code_sha256": code_binding(), "files": inv, "index_content_sha256": digest(canonical(inv).encode())})
    (target / "index_manifest.sha256").write_text(digest((target / "index_manifest.json").read_bytes()) + "\n", encoding="ascii")
    validate_index(target / "index_manifest.json")
    return {**report, "index_manifest": str(target / "index_manifest.json"), "dataset_content_sha256": dataset["dataset_content_sha256"]}


def load_index(index_manifest):
    from src.retrieval_dataset import check_inventory
    started = time.perf_counter()
    path = Path(index_manifest).resolve(); root = path.parent; m = load(path)
    if (m["index_version"] != VERSION or m["snapshot_date"] != SNAPSHOT_DATE or m["experimental"] is not True
            or m["release_eligible"] is not False
            or m["index_content_sha256"] != digest(canonical(m["files"]).encode())
            or digest(path.read_bytes()) != (root / "index_manifest.sha256").read_text().strip()):
        raise ValueError("Index manifest/version/status/hash mismatch")
    source_compatibility = compatible_code_binding(m["code_sha256"])
    check_inventory(root, m["files"], CONTROL)
    cfg = load(root / "config.json"); check_config(cfg)
    if (m["config_sha256"] != digest((root / "config.json").read_bytes())
            or load(root / "runtime.json") != m["runtime"]):
        raise ValueError("Index configuration/build runtime record binding mismatch")
    compatibility = runtime_compatibility(m["runtime"], runtime())
    compatibility["source_binding"] = source_compatibility
    for note in compatibility["warnings"]:
        print("WARNING: " + note, file=sys.stderr)
    dataset_path = resolve_ref(root, m["dataset_manifest_ref"])
    dataset = dataset_files_check(dataset_path)
    if (m["dataset_manifest_sha256"] != digest(dataset_path.read_bytes()) or m["dataset_version"] != dataset["dataset_version"]
            or m["dataset_content_sha256"] != dataset["dataset_content_sha256"]):
        raise ValueError("Index/dataset version/hash mismatch")
    data = dataset_path.parent
    chunks = rows(data / "chunks.jsonl"); by = unique(chunks, "chunk_id")
    mapping = check_mapping(rows(root / "document_mapping.jsonl"), chunks, cfg)
    meta = unique(rows(data / "metadata.jsonl"), "chunk_id")
    if set(meta) != set(by) or m["documents"] != len(mapping): raise ValueError("Incomplete result metadata")
    import bm25s
    retriever = bm25s.BM25.load(str(root / "engine"), load_corpus=False, mmap=False, allow_pickle=False, show_progress=False)
    if (retriever.scores["num_docs"] != len(mapping) or retriever.method != cfg["method"]
            or retriever.idf_method != cfg["idf_method"] or retriever.k1 != cfg["k1"] or retriever.b != cfg["b"]):
        raise ValueError("Saved engine/mapping/parameters mismatch")
    vocab = {t: i for i, t in enumerate(sorted({t for c in chunks for t in tokenize(c["text_for_search"], cfg)}))}
    import numpy as np
    s = retriever.scores
    if (retriever.vocab_dict != vocab or len(s["indptr"]) != len(vocab) + 1 or s["indptr"][0] != 0
            or s["indptr"][-1] != len(s["data"]) or len(s["data"]) != len(s["indices"])
            or not np.isfinite(s["data"]).all() or (s["data"] < 0).any()
            or (np.diff(s["indptr"]) < 0).any() or (s["indices"] < 0).any() or (s["indices"] >= len(mapping)).any()):
        raise ValueError("Saved vocabulary/CSC index inconsistent")
    return {"retriever": retriever, "mapping": mapping, "chunks": by, "metadata": meta,
            "contexts": rows(data / "contexts.jsonl"), "manifest": m, "config": cfg,
            "load_ms": (time.perf_counter() - started) * 1000, "runtime_compatibility": compatibility}


def search_loaded(loaded, query, top_k):
    started = time.perf_counter(); m = loaded["manifest"]
    tokens, hits = rank(loaded["retriever"], loaded["mapping"], query, top_k, loaded["config"])
    results = []
    for position, (internal, score) in enumerate(hits, 1):
        cid = loaded["mapping"][internal]["chunk_id"]; c = loaded["chunks"][cid]
        results.append({"rank": position, **c, **loaded["metadata"][cid], "score": score, "score_type": "bm25",
                        "score_semantics": "ranking_score_not_probability_or_legal_confidence",
                        "dataset_version": m["dataset_version"], "index_version": m["index_version"],
                        "source_proof_base_ref": "dataset/", "source_url_status": "legacy_candidate_provenance_pending",
                        "contexts": [x for x in loaded["contexts"] if x["chunk_id"] == cid]})
    return {"query": query, "query_tokens": tokens, "top_k_requested": top_k, "top_k_limit": min(top_k, len(loaded["mapping"])),
            "results": results, "timings_ms": {"load": loaded["load_ms"], "search": (time.perf_counter() - started) * 1000},
            "experimental": True, "release_eligible": False, "index_version": VERSION, "dataset_version": m["dataset_version"],
            "runtime_compatibility": loaded["runtime_compatibility"]}


def validate_index(manifest):
    from src.retrieval_dataset import validate
    import numpy as np
    loaded = load_index(manifest); m = loaded["manifest"]
    validate(Path(manifest).resolve().parent / m["dataset_manifest_ref"])
    expected, mapping = create_index(list(loaded["chunks"].values()), loaded["config"])
    if mapping != [loaded["mapping"][i] for i in range(len(mapping))]: raise ValueError("Rebuilt mapping differs")
    for key in ["data", "indices", "indptr"]:
        actual = loaded["retriever"].scores[key]; wanted = expected.scores[key]
        if actual.shape != wanted.shape or not (np.allclose(actual, wanted, rtol=1e-6, atol=1e-7) if key == "data" else np.array_equal(actual, wanted)):
            raise ValueError("Persisted index differs from rebuild: " + key)
    return {"technical_valid": True, "documents": m["documents"], "save_load_replay": True,
            "score_tolerance": {"rtol": 1e-6, "atol": 1e-7}, "release_eligible": False,
            "runtime_compatibility": loaded["runtime_compatibility"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build"); b.add_argument("--dataset-manifest", required=True, type=Path)
    b.add_argument("--config", default=DEFAULT_CONFIG, type=Path); b.add_argument("--run-dir", required=True, type=Path)
    for name in ["validate", "search"]:
        q = sub.add_parser(name); q.add_argument("--index-manifest", required=True, type=Path)
        if name == "search": q.add_argument("--query", required=True); q.add_argument("--top-k", type=int, default=5)
    a = p.parse_args(argv)
    try:
        if a.action == "build": result = build(a.dataset_manifest, a.config, a.run_dir)
        elif a.action == "validate": result = validate_index(a.index_manifest)
        else: result = search_loaded(load_index(a.index_manifest), a.query, a.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
