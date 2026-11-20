"""Compare the five reviewed BM25 queries using only the sealed v5 and v6 runs."""

import argparse
from collections import Counter
from pathlib import Path
import sys

from src import subset_evaluation as v5, v6_acceptance
from src.config import BASE_DIR
from src.pipeline_cli import staging_path
from src.source_contracts import digest, resolve_ref


VERSION = "subset-v6-five-query-diagnostic.v1"
PAIR = v5.acceptance.q.pair
same = v5.acceptance.same
require = v5.evaluation.require
load, rows, hashed = v5.r.load, v5.r.rows, v5.r.bm.hashed
PINS = {
    "v5_evaluation": ("staging/subset-v5-five-query-evaluation-001/manifest.json",
                      "71b249f6626120cf2137ab86675874f6e6131438758df8ca64e9faa0dbbff4d1"),
    "v5_aggregate": ("staging/subset-v5-label-aggregate-001/manifest.json",
                     "7c4dbee482e5bc7d38e96b12e4a75684b3756a47b48d4385c713e2fd846cd56e"),
    "v6_batch": ("staging/bm25-subset-v6-batch-001/manifest.json",
                 "43cda4d3c35b416c56d8c7da1bdefbec2e2ab1a8910b04c574d54a75d649bef2"),
    "comparison": ("staging/bm25-v5-v6-comparison-001/manifest.json",
                   "67f9fc847bf6e19c023d1d3bd3e53d81f7b4761d8f26ce0d3cfbdfda4c4cdfda"),
    "v6_packet": ("staging/subset-v6-binding-review-008/manifest.json", v6_acceptance.PACKET_SHA),
    "v6_core": ("staging/subset-v6-binding-review-008/review/manifest.json", v6_acceptance.REVIEW_SHA),
    "v6_capture": ("staging/subset-v6-response-capture-001/manifest.json",
                   "4ae8dcd15809f3fe266f009460c4eb942ac6749a33e1a7ca0a510eb38dbb4ea3"),
    "v6_accepted": ("staging/subset-v6-accepted-labels-001/manifest.json",
                    "d5ab715923b05f05d037acbcfa7b06457a7082a90b586920c8c644143fcb473c"),
    "v6_dataset": ("staging/dataset-v6-gap-002/dataset_manifest.json", v6_acceptance.DATASET_SHA),
    "v6_index": ("staging/bm25-subset-v6-001/index_manifest.json", v6_acceptance.INDEX_SHA),
    "queries": ("staging/composition-queries-001/manifest.json",
                "f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0"),
}
METRICS = ["Precision@1", "Precision@3", "Precision@5", "Precision@10", "Hit@10", "MRR@10"]


def load_pin(ref, sha):
    return v5.labels.bound_file({"ref": ref, "sha256": sha})


def verify_inventory(manifest_path):
    manifest = load(manifest_path)
    entries = manifest["files"]
    same(hashed(entries), manifest["content_sha256"], "Comparison inventory binding")
    actual = {path.relative_to(manifest_path.parent).as_posix()
              for path in manifest_path.parent.rglob("*") if path.is_file() and path != manifest_path}
    same(sorted(actual), sorted(row["path"] for row in entries), "Comparison inventory")
    for row in entries:
        content = resolve_ref(manifest_path.parent, row["path"]).read_bytes()
        same([len(content), digest(content)], [row["size_bytes"], row["sha256"]], row["path"])
    return manifest


def bind_v6(queries, pool, annotations, run, binding):
    query_map = {row["query_id"]: row for row in queries}
    same(list(query_map), list(v5.QUERIES), "Five-query identities and order")
    require(len(queries) == len(query_map), "Duplicate query")
    pool_map = {PAIR(row): row for row in pool}
    require(len(pool_map) == len(pool), "Duplicate v6 pool pair")
    accepted = {}
    for row in annotations:
        key = PAIR(row)
        require(key not in accepted, f"Duplicate accepted judgment: {key}")
        require(key in pool_map and key[0] in query_map, f"Accepted judgment outside v6 pool: {key}")
        require(row["status"] == "accepted" and type(row["relevance"]) is int and row["relevance"] in (0, 1, 2),
                f"Invalid accepted judgment: {key}")
        require(row["record_type"] in v5.labels.TYPES, f"Unsupported record type: {key}")
        same(row["binding"], binding, f"Wrong accepted binding: {key}")
        same(row["query_sha256"], hashed(query_map[key[0]]), f"Wrong query hash: {key}")
        for field in ("review_pair_id", "query_sha256", "record_sha256", "full_read_sha256", "record_type"):
            same(row[field], pool_map[key][field], f"Wrong {field}: {key}")
        accepted[key] = row

    selected = v5.validate_top10(run, v5.QUERIES, accepted, binding)
    missing = sorted(set(pool_map) - set(accepted))
    require(not missing, f"Missing accepted pool judgments: {missing}")
    for hit in selected:
        same(hit["dataset_response_sha256"], accepted[PAIR(hit)]["full_read_sha256"],
             f"Frozen hit full-read binding: {PAIR(hit)}")
    return accepted, selected


def read_inputs():
    inputs = {key: load_pin(*pin) for key, pin in PINS.items()}
    old_root = inputs["v5_evaluation"].parent
    old_report = v5.validate(inputs["v5_evaluation"])
    same(load(inputs["v5_evaluation"])["inputs"]["aggregate"], v5.labels.spec(inputs["v5_aggregate"]),
         "Session 11 aggregate binding")
    old_binding = old_report["binding"]
    old_labels = rows(old_root / "accepted.selected.jsonl")
    same(len(old_labels), 53, "Session 11 pool")

    packet = inputs["v6_packet"].parent
    core = inputs["v6_core"].parent
    receipt = v6_acceptance.validate(packet, inputs["v6_capture"].parent, inputs["v6_accepted"].parent)
    same([receipt["accepted"], receipt["pending"]], [54, 0], "Session 16 acceptance counts")
    same(receipt["relevance_counts"], {"2": 7, "1": 8, "0": 39}, "Session 16 label distribution")
    binding = receipt["binding"]
    same(load(inputs["v6_core"])["binding"], binding, "Review packet binding")
    index = load(inputs["v6_index"])
    dataset = load(inputs["v6_dataset"])
    same(index["snapshot_date"], "2025-01-01", "Index snapshot")
    same(dataset["snapshot_date"], "2025-01-01", "Dataset snapshot")
    for key in ("dataset_version", "dataset_content_sha256"):
        same(dataset[key], binding[key], f"Dataset {key}")
    batch = load(inputs["v6_batch"])
    for key, value in binding.items():
        if key in index:
            same(index[key], value, f"Index {key}")
        if key in batch["binding"]:
            same(batch["binding"][key], value, f"Batch {key}")
    for key in ("v6_dataset", "v6_index", "v6_batch", "queries"):
        field = {"v6_dataset": "dataset_manifest_sha256", "v6_index": "index_manifest_sha256",
                 "v6_batch": "batch_manifest_sha256", "queries": "queries_manifest_sha256"}[key]
        same(PINS[key][1], binding[field], f"Pinned {field}")
    same(old_binding["queries_manifest_sha256"], binding["queries_manifest_sha256"], "Shared query manifest")
    batch_root = inputs["v6_batch"].parent
    frozen_queries = v5.r.bm.query_set(inputs["queries"].parent, binding["queries_manifest_sha256"])
    same(rows(batch_root / "queries.jsonl"), frozen_queries, "Canonical frozen query payload")
    selected = {q["query_id"]: q for q in frozen_queries if q["query_id"] in v5.QUERIES}
    queries = [selected[qid] for qid in v5.QUERIES]
    same(queries, rows(old_root / "queries.jsonl"), "Session 11 query payload")
    same(queries, rows(core / "queries.jsonl"), "Reviewed v6 query payload")
    annotations = rows(inputs["v6_accepted"].parent / "accepted.annotations.jsonl")
    all_hits = v5.frozen_batch(inputs["v6_batch"])
    accepted, new_run = bind_v6(queries, rows(core / "pool.jsonl"), annotations, all_hits, binding)
    same(new_run, rows(core / "top10.v6.frozen.jsonl"), "Reviewed Top-10 payload")
    for hit in new_run:
        row = accepted[PAIR(hit)]
        packet_detail = resolve_ref(core, row["detail_ref"])
        batch_detail = resolve_ref(batch_root, hit["detail_ref"])
        same(digest(packet_detail.read_bytes()), row["detail_sha256"], "Review detail hash")
        same(digest(batch_detail.read_bytes()), hit["detail_sha256"], "Frozen batch detail hash")
        packet_response = load(packet_detail)["dataset_response"]
        envelope = load(batch_detail)
        for key in ("dataset_manifest_sha256", "index_manifest_sha256", "index_version"):
            same(envelope[key], binding[key], f"Detail envelope {key}")
        same(envelope["dataset_response_sha256"], row["full_read_sha256"], "Envelope full-read hash")
        same(envelope["dataset_response"], packet_response, "Full read in batch and review packet")
        same(hashed(packet_response["record"]), row["record_sha256"], "Record payload hash")

    comparison = verify_inventory(inputs["comparison"])["binding"]
    for name, version_binding in (("old", old_binding), ("new", binding)):
        for key in ("index_manifest_sha256", "batch_manifest_sha256"):
            same(comparison[f"{name}_{key}"], version_binding[key], f"Comparison {name} {key}")
    same(comparison["queries_manifest_sha256"], binding["queries_manifest_sha256"], "Comparison queries")
    old_run = rows(old_root / "frozen.run.jsonl")
    old_top = rows(old_root / "top10.accepted.jsonl")
    return {
        "queries": queries, "old_run": old_run, "new_run": new_run,
        "old_labels": old_labels, "new_labels": annotations, "old_top": old_top,
        "new_top": joined_top(new_run, accepted), "old_binding": old_binding, "binding": binding,
        "old_metrics": rows(old_root / "metrics.per_query.jsonl"), "old_report": old_report,
        "comparison": comparison, "inputs": inputs,
    }


def joined_top(run, accepted):
    return [{**hit, "accepted_label": accepted[PAIR(hit)],
             "accepted_annotation_sha256": hashed(accepted[PAIR(hit)])} for hit in run]


def measure(queries, labels, run):
    accepted = {PAIR(row): row["relevance"] for row in labels}
    require(len(accepted) == len(labels), "Duplicate label in metric pool")
    result = []
    for query in queries:
        qid = query["query_id"]
        judgments = {rid: label for (qid_label, rid), label in accepted.items() if qid_label == qid}
        ranked = [row["record_id"] for row in run if row["query_id"] == qid]
        require(len(ranked) == 10, f"Expected 10 stored hits: {qid}")
        result.append({"query_id": qid, "query_sha256": hashed(query), "pool_judgments": len(judgments),
                       "returned": len(ranked), **v5.metric_values(judgments, ranked)})
    return result


def delta(v5_value, v6_value):
    return v6_value - v5_value if v5_value is not None and v6_value is not None else None


def case_checks(data):
    paths = data["inputs"]
    comparison_root = paths["comparison"].parent
    diagnostics = {row["query_id"]: row for row in rows(comparison_root / "diagnostic-all-documents.jsonl")}
    comparison_rows = {row["query_id"]: row for row in rows(comparison_root / "query_deltas.jsonl")}
    deep = load(comparison_root / "deep_checks.json")
    old = {PAIR(row): row for row in data["old_top"]}
    new = {PAIR(row): row for row in data["new_top"]}
    cases = {}
    for query in data["queries"]:
        qid = query["query_id"]
        previous = [row for (q, _), row in old.items() if q == qid]
        current = [row for (q, _), row in new.items() if q == qid]
        summary = comparison_rows[qid]
        for side, ranked in (("before", previous), ("after", current)):
            same(summary[f"top10_{side}"], [hit["record_id"] for hit in ranked], f"Comparison ranks: {qid} {side}")
        cases[qid] = {
            "same_ranked_ids": summary["top10_before"] == summary["top10_after"],
            "same_ranked_labels": [row["relevance"] for row in previous]
            == [row["accepted_label"]["relevance"] for row in current],
            "positive_ranks_v5": [row["rank"] for row in previous if row["relevance"]],
            "positive_ranks_v6": [row["rank"] for row in current if row["accepted_label"]["relevance"]],
        }

    red, age = "dev-red_light-2", "dev-driving_age-2"
    for qid in (red, age):
        rid = deep[qid]["record_id"]
        row = next(row for row in data["new_labels"] if PAIR(row) == (qid, rid))
        observed = {}
        for version in ("v5", "v6"):
            ranked = diagnostics[qid][version]
            version_binding = data["old_binding"] if version == "v5" else data["binding"]
            for field in ("dataset_version", "index_version"):
                same(ranked[field], version_binding[field], f"Diagnostic {qid} {field}")
            observed[version] = next((hit["rank"] for hit in ranked["results"] if hit["record_id"] == rid), None)
            same(observed[version], deep[qid][f"rank_{version}"], f"Diagnostic observed rank: {qid}")
        detail = load(resolve_ref(paths["v6_core"].parent, row["detail_ref"]))["dataset_response"]
        same(hashed(detail), row["full_read_sha256"], f"Diagnostic read binding: {qid}")
        count = len(detail["required_read"]["unit_reads"])
        same(count, len(deep[qid]["required_unit_ids"]), f"Diagnostic closure: {qid}")
        previous_count = None
        if qid == age:
            review = load(paths["v5_evaluation"])["inputs"]["review"]
            old_detail = load(v5.labels.bound_file(review).parent / "details" / f"{rid}.json")
            previous_count = len(old_detail["dataset_response"]["required_read"]["unit_reads"])
            same([observed["v5"], observed["v6"], previous_count, count], [15, 15, 2, 16], "Age ranks and closure")
        else:
            same([observed["v5"], observed["v6"], count], [None, 4, 7], "Red-light rank and closure")
            same(new[qid, rid]["rank"], 4, "Red-light batch rank")
            require(rid in data["comparison"]["added_target_ids"], "Red-light target is not a new target")
        cases[qid].update(record_id=rid, observed_rank=observed, required_reads_v5=previous_count,
                          required_reads_v6=count, decision=row)

    for qid, expected in (("V3-D05", {2: ("V = 60", "35")}),
                          ("V3-D07", {2: ("60 < V ≤ 80", "55"), 3: ("80 < V ≤ 100", "70")})):
        found = []
        for (q, rid), hit in new.items():
            label = hit["accepted_label"]
            if q != qid or not label["relevance"]:
                continue
            previous = old[qid, rid]
            same([previous[k] for k in ("rank", "relevance", "relation", "completeness")],
                 [hit["rank"], label["relevance"], label["relation"], label["completeness"]],
                 f"Distance judgment {qid} {rid}")
            if hit["rank"] in expected:
                interval, meters = expected[hit["rank"]]
                quotes = [entry["locator"]["quote"] for entry in label["evidence_locators"]]
                require(any(f": {interval}\nKhoảng cách an toàn (m): {meters}" in quote for quote in quotes),
                        f"Expected verified distance row: {qid} {interval}")
                require(any("khô ráo" in quote and "tầm nhìn" in quote for quote in quotes),
                        f"Expected applicability condition in cited text: {qid}")
                same([label["record_type"], label["relevance"], label["completeness"]],
                     ["table-retrieval.v1", 2, "partial"], "Accepted distance row")
            if hit["rank"] == 1:
                same([label["relevance"], label["relation"]], [1, "dependency_only"], "Distance dependency")
            found.append({"rank": hit["rank"], "decision": label})
        require({1, *expected}.issubset({row["rank"] for row in found}), f"Missing checked distance evidence: {qid}")
        cases[qid]["positive_evidence"] = found
    return cases


def paired_value(old, new):
    if old is None or new is None:
        return f"{old} → {new}"
    return f"{old:.6f} → {new:.6f} ({delta(old, new):+.6f})"


def render(per_query, macro, cases):
    lines = [
        "# Phiên 17 · Chẩn đoán BM25 v5 và v6 trên năm query",
        "",
        "Tính từ hai run đã lưu và nhãn accepted của từng phiên bản. Pool v5 có 53 cặp "
        "trên 138 target và pool v6 có 54 cặp trên 139 target. Nhãn có ChatGPT hỗ trợ "
        "và người dùng xác nhận hoặc tiếp nhận. Kết luận giới hạn ở năm query đã rà.",
        "",
        "Direct dùng relevance 2. Useful dùng relevance 1 hoặc 2, gồm supporting và dependency-only. "
        "Precision@k chia cho k. Macro trung bình năm query, gồm cả query có điểm 0. "
        "nDCG dùng gain 2^relevance − 1, discount log₂(rank + 1) và IDCG từ pool riêng mỗi phiên bản. "
        "Nếu IDCG bằng 0, nDCG là null. Recall, AP, MAP toàn corpus và metrics chính thức 50 query giữ null.",
        "",
        "## Macro",
        "",
        "| Cách đọc | Chỉ số | v5 | v6 | Δ v6 − v5 |",
        "|---|---|---:|---:|---:|",
    ]
    for name in ("Direct", "Useful"):
        for metric in METRICS:
            old = macro["v5"]["readings"][name][metric]
            new = macro["v6"]["readings"][name][metric]
            lines.append(f"| {name} | {metric} | {old:.6f} | {new:.6f} | {delta(old, new):+.6f} |")
    old, new = (macro[version]["nDCG_at_10_pool"] for version in ("v5", "v6"))
    lines += [f"| Graded | nDCG@10_pool | {old:.6f} | {new:.6f} | {delta(old, new):+.6f} |",
              "", "## Theo query", "", "Mỗi ô ghi v5 → v6 (delta). RR@10 là đóng góp vào MRR@10.",
              "", "| Query | Cách đọc | P@1 | P@3 | P@5 | P@10 | Hit@10 | RR@10 |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in per_query:
        for name in ("Direct", "Useful"):
            metrics = METRICS[:-1] + ["RR@10"]
            values = [paired_value(*(row[version]["readings"][name]["values"][key]
                                    for version in ("v5", "v6"))) for key in metrics]
            lines.append(f"| {row['query_id']} | {name} | " + " | ".join(values) + " |")
    lines += ["", "| Query | DCG@10 | IDCG@10_pool | nDCG@10_pool |",
              "|---|---:|---:|---:|"]
    for row in per_query:
        values = [paired_value(*(row[version][key] for version in ("v5", "v6")))
                  for key in ("DCG@10", "IDCG@10_pool", "nDCG@10_pool")]
        lines.append(f"| {row['query_id']} | " + " | ".join(values) + " |")
    lines += ["", "## Đối chiếu căn cứ", "",
              "- **Đèn đỏ.** A6K9b trở thành target riêng trong v6, ở hạng 4 và mang nhãn "
              "2/direct_target/partial. V5 có căn cứ này qua dependency. Cặp mới đóng góp gain ở hạng 4 "
              "và nâng IDCG của pool. Thay đổi quan sát được gắn với việc thêm target trong cùng thiết lập BM25.",
              "- **Tuổi lái mô tô.** Target trực tiếp ở hạng 15 trong cả hai run sâu đã lưu. "
              "Required-read tăng từ 2 lên 16, bổ sung căn cứ về hạng GPLX và loại xe. Target vẫn ngoài Top‑10, "
              "nên Direct Top‑10 vẫn bằng 0.",
              "- **Khoảng cách.** V3-D05 ở hạng 2 có hàng V = 60 ứng với 35 m. V3-D07 ở hạng 2 và 3 "
              "có hai hàng 60 < V ≤ 80 ứng với 55 m và 80 < V ≤ 100 ứng với 70 m. "
              "Evidence giữ điều kiện mặt đường khô ráo và tầm nhìn bảo đảm. Cả ba hàng là 2/partial. "
              "Record hạng 1 đi qua dependency ở hai query, được tính Useful.",
              "- **Còi ban đêm.** Hai căn cứ trực tiếp ở hạng 1 và 2 của cả hai run. "
              f"Thứ tự ID Top‑10 giống nhau: {cases['dev-night_horn-3']['same_ranked_ids']}. "
              f"Chuỗi nhãn Top‑10 giống nhau: {cases['dev-night_horn-3']['same_ranked_labels']}.",
              "", "Xem bằng chứng và lý do đã chấp nhận trong [case_checks.json](case_checks.json), "
              "[Top‑10 v5](top10.v5.accepted.jsonl) và [Top‑10 v6](top10.v6.accepted.jsonl).",
              "Kết quả này là chẩn đoán relevance và giữ trạng thái xác minh pháp lý của các nguồn ở mức pending.",
              "", "## Lệnh tái chạy", "", "```powershell",
              r".\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_v6_evaluation build --run-dir staging/subset-v6-five-query-evaluation-NEW",
              r".\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_v6_evaluation validate --manifest staging/subset-v6-five-query-evaluation-001/manifest.json",
              "```", ""]
    return "\n".join(lines).encode("utf8")


def assemble():
    data = read_inputs()
    old = measure(data["queries"], data["old_labels"], data["old_run"])
    new = measure(data["queries"], data["new_labels"], data["new_run"])
    same(old, data["old_metrics"], "Recomputed Session 11 per-query metrics")
    old_macro, old_contributions = v5.summarize(old)
    new_macro, new_contributions = v5.summarize(new)
    same(old_macro, {key: data["old_report"][key] for key in old_macro}, "Recomputed Session 11 macro")
    per_query = []
    for before, after in zip(old, new):
        per_query.append({
            "query_id": before["query_id"], "v5": before, "v6": after,
            "delta": {
                **{key: delta(before[key], after[key]) for key in ("DCG@10", "IDCG@10_pool", "nDCG@10_pool")},
                "readings": {mode: {key: delta(value, after["readings"][mode]["values"][key])
                                    for key, value in info["values"].items()}
                             for mode, info in before["readings"].items()},
            },
        })
    macro = {"v5": old_macro, "v6": new_macro, "delta": {
        "nDCG_at_10_pool": delta(old_macro["nDCG_at_10_pool"], new_macro["nDCG_at_10_pool"]),
        "readings": {mode: {key: delta(value, new_macro["readings"][mode][key]) for key, value in info.items()}
                     for mode, info in old_macro["readings"].items()},
    }}
    cases = case_checks(data)
    report = {
        "evaluation_scope": v5.SCOPE, "snapshot": "2025-01-01", "metric_policy": v5.METRIC_POLICY,
        "pool_pairs": {"v5": len(data["old_labels"]), "v6": len(data["new_labels"])},
        "target_counts": {"v5": 138, "v6": 139}, "judged_top10": {"v5": 50, "v6": 50},
        "excluded_labels": {"v5_accepted_outside_pool": 6, "v5_pending_V3-D02": 2},
        "bindings": {"v5": data["old_binding"], "v6": data["binding"]},
        "label_provenance": {"v5": "user_reviewed_ai_assisted", "v6": "user_adopted_ai_assisted",
                             "ai_assisted": True, "independent": False, "blind": False},
        "macro": macro, "corpus_recall": None, "corpus_ap": None, "corpus_map": None,
        "official_50_query_metrics": None, "legal_verified": False, "release_eligible": False,
    }
    values = {"queries.jsonl": data["queries"], "metrics.per_query.jsonl": per_query,
              "macro.delta.json": macro, "top10.v5.accepted.jsonl": data["old_top"],
              "top10.v6.accepted.jsonl": data["new_top"], "case_checks.json": cases,
              "macro.contributions.json": {"v5": old_contributions, "v6": new_contributions},
              "report.json": report}
    files = {ref: v5.encode(value, ref.endswith(".jsonl")) for ref, value in values.items()}
    files["results.md"] = render(per_query, macro, cases)
    return files, report


def manifest_metadata():
    return {
        "manifest_type": VERSION, "producer": v5.labels.spec(Path(__file__)),
        "session11_metric_adapter": v5.labels.spec(Path(v5.__file__)),
        "metric_helper": v5.labels.spec(Path(v5.evaluation.__file__)),
        "inputs": {key: {"ref": ref, "sha256": sha} for key, (ref, sha) in PINS.items()},
    }


def build(run_dir):
    output = staging_path(run_dir)
    files, report = assemble()
    output.mkdir(parents=True, exist_ok=False)
    for ref, content in files.items():
        (output / ref).write_bytes(content)
    v5.r.seal(output, manifest_metadata())
    return report


def validate(manifest):
    manifest = Path(manifest).resolve()
    sealed = v5.labels.check_seal(manifest)
    same({key: value for key, value in sealed.items() if key != "files"}, manifest_metadata(), "Evaluation manifest")
    files, report = assemble()
    same(sorted(ref["path"] for ref in sealed["files"]), sorted(files), "Evaluation inventory")
    for ref, content in files.items():
        require((manifest.parent / ref).read_bytes() == content, f"Replay differs: {ref}")
    return {"technical_valid": True, **report}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("build").add_argument("--run-dir", required=True)
    commands.add_parser("validate").add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    try:
        report = build(args.run_dir) if args.action == "build" else validate(args.manifest)
        print(v5.encode(report).decode("utf8"), end="")
        return 0
    except (ValueError, KeyError, OSError, TypeError, StopIteration) as error:
        print(f"Evaluation invalid: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
