"""Synthetic fixtures only: no legal or real-corpus quality assertions."""
import math
import unittest
from copy import deepcopy
from pathlib import Path
import tempfile

from src.evaluation import evaluate, metrics, validate_queries, validate_records, read_bundle, binding, VERSION
from src.experimental_dataset import write_json
from src.source_contracts import digest


class MetricsTests(unittest.TestCase):
    def test_multiple_graded_short(self):
        r = metrics({"a": 2, "b": 1, "c": 0}, ["c", "b", "a"])
        self.assertEqual(r["Recall@5"], 1)
        self.assertEqual(r["MRR@10"], .5)
        self.assertAlmostEqual(r["nDCG@10"], (1 / math.log2(3) + 3 / 2) / (3 + 1 / math.log2(3)))

    def test_hit_outside_cutoff(self):
        ids = [str(i) for i in range(11)]
        r = metrics({i: int(i == "10") for i in ids}, ids)
        self.assertEqual(r["Recall@10"], 0)
        self.assertEqual(r["MRR@10"], 0)
        self.assertEqual(r["nDCG@10"], 0)

    def test_distinct_cutoffs(self):
        ids = [str(i) for i in range(10)]
        r = metrics({i: int(i in {"0", "7"}) for i in ids}, ids)
        self.assertEqual(r["Recall@5"], .5)
        self.assertEqual(r["Recall@10"], 1)

    def test_no_hit_empty(self):
        self.assertEqual(metrics({"a": 2}, [])["nDCG@10"], 0)

    def test_invalid_metrics(self):
        for judgments, result in [({"a": 1}, ["a", "a"]), ({"a": 0}, ["a"]), ({"a": 1}, ["b"])]:
            with self.assertRaises(ValueError):
                metrics(judgments, result)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.q = [{"query_id": "q", "query": "fixture", "query_type": "direct", "topic": "fixture",
                   "intent_group_id": "g", "split": "dev"}]
        self.a = [{"query_id": "q", "chunk_id": "a", "relevance": 2, "status": "accepted", "origin": "human",
                   "annotator_ref": "FIXTURE/reviewer", "reason": "Synthetic", "evidence_refs": ["chunk:a"],
                   "recorded_at": "2020-01-01T00:00:00+00:00"}]
        self.qrels = [{"query_id": "q", "chunk_id": "a", "relevance": 2}]
        self.run = [{"query_id": "q", "chunk_id": "a", "rank": 1, "score": 1.}]
        self.outcomes = [{"query_id": "q", "outcome": "success"}]
        self.reviews = [{"query_id": "q", "status": "accepted", "origin": "human",
                         "reviewer_ref": "FIXTURE/reviewer", "reason": "Synthetic complete pool",
                         "evidence_refs": ["chunk:a"], "recorded_at": "2020-01-01T00:00:00+00:00",
                         "judgments_complete": True, "coverage": "answer_present"}]

    def score(self):
        return evaluate(self.q, self.qrels, self.a, self.run, self.outcomes, self.reviews, {"a", "b"})

    def test_accepted_fixture_only(self):
        self.assertEqual(self.score()["metrics"]["Recall@10"], 1)

    def test_pending_not_metrics(self):
        self.reviews[0]["status"] = "pending"
        self.assertIsNone(self.score()["metrics"])

    def test_unjudged_excluded(self):
        self.run.append({"query_id": "q", "chunk_id": "b", "rank": 2, "score": .5})
        self.assertEqual(self.score()["excluded"][0]["reason"], "MISSING_TOP10_JUDGMENT")

    def test_error_contributes_zero(self):
        self.run = []
        self.outcomes = [{"query_id": "q", "outcome": "error", "error": "fixture failure"}]
        self.assertEqual(self.score()["metrics"]["Recall@10"], 0)

    def test_gap_separate(self):
        self.a = []
        self.qrels = []
        self.reviews[0]["coverage"] = "corpus_coverage_gap"
        self.assertEqual(self.score()["excluded"][0]["reason"], "NO_POSITIVE_CORPUS_COVERAGE_GAP")

    def test_agent_cannot_accept(self):
        self.a[0]["origin"] = "agent"
        with self.assertRaises(ValueError):
            self.score()

    def test_invalid_records(self):
        original = deepcopy(self.run)
        for bad in [original * 2, [{"query_id": "q", "chunk_id": "unknown", "rank": 1, "score": 1}],
                    [{"query_id": "q", "chunk_id": "a", "rank": 2, "score": float("nan")}]]:
            self.run = bad
            with self.assertRaises(ValueError):
                self.score()

    def test_evidence_binding(self):
        self.a[0]["evidence_refs"] = []
        with self.assertRaises(ValueError):
            self.score()
        self.a[0]["evidence_refs"] = ["chunk:unknown"]
        with self.assertRaises(ValueError):
            self.score()

    def test_qrel_requires_accepted(self):
        self.a[0]["status"] = "proposed"
        with self.assertRaises(ValueError):
            self.score()

    def test_no_positive_distinct_from_missing_labels(self):
        self.a[0]["relevance"] = self.qrels[0]["relevance"] = 0
        self.assertEqual(self.score()["excluded"][0]["reason"], "NO_POSITIVE")

    def test_split_leak(self):
        other = {**self.q[0], "query_id": "q2", "split": "test"}
        with self.assertRaises(ValueError):
            validate_queries(self.q + [other])

    def test_no_outcome(self):
        with self.assertRaises(ValueError):
            validate_records(self.q, [], [], [], [], {"a"})


class BindingTests(unittest.TestCase):
    def test_hash_and_dataset_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index = root / "index"
            index.write_text("fixture", encoding="utf8")
            loaded = {"manifest": {k: "fixture" for k in (
                "index_version", "index_content_sha256", "dataset_version",
                "dataset_content_sha256", "dataset_manifest_sha256")}}
            bundle = root / "bundle"
            bundle.mkdir()
            f = bundle / "queries.jsonl"
            f.write_text("fixture", encoding="utf8")
            m = {"evaluation_version": VERSION, "binding": binding(index, loaded),
                 "files": {"queries.jsonl": digest(f.read_bytes())}}
            write_json(bundle / "manifest.json", m)
            read_bundle(bundle, loaded, index)
            f.write_text("changed", encoding="utf8")
            with self.assertRaises(ValueError):
                read_bundle(bundle, loaded, index)
            f.write_text("fixture", encoding="utf8")
            m["binding"]["dataset_version"] = "other"
            write_json(bundle / "manifest.json", m)
            with self.assertRaises(ValueError):
                read_bundle(bundle, loaded, index)


if __name__ == "__main__":
    unittest.main()
