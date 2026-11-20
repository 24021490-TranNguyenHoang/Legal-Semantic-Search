"""Join checks and an independent check of the graded denominator change."""

from copy import deepcopy
from math import log2
import unittest

from src import subset_v6_evaluation as evaluation


class FrozenJudgmentJoinTests(unittest.TestCase):
    def setUp(self):
        self.queries = [{"query_id": qid, "query": qid} for qid in evaluation.v5.QUERIES]
        self.binding = {"dataset_version": "v6", "index_version": "v2"}
        self.pool, self.labels, self.run = [], [], []
        for query in self.queries:
            qid = query["query_id"]
            for rank in range(1, 11):
                # Reuse IDs across queries to exercise the composite join.
                pair = {
                    "query_id": qid, "record_id": f"record-{rank}", "record_type": "chunk.v1",
                    "review_pair_id": f"{qid}-{rank}", "query_sha256": evaluation.hashed(query),
                    "record_sha256": f"record-hash-{rank}", "full_read_sha256": f"full-read-hash-{rank}",
                }
                self.pool.append(pair)
                self.labels.append({**pair, "binding": dict(self.binding), "status": "accepted",
                                    "relevance": 1 if rank == 1 else 0,
                                    "relation": "dependency_only" if rank == 1 else "unrelated"})
                self.run.append({
                    **{field: pair[field] for field in ("query_id", "record_id", "record_type")},
                    **self.binding, "rank": rank, "score": 11 - rank,
                    "dataset_response_sha256": pair["full_read_sha256"],
                })

    def join(self):
        return evaluation.bind_v6(self.queries, self.pool, self.labels, self.run, self.binding)

    def test_composite_join_and_dependency_only(self):
        accepted, ranked = self.join()
        self.assertEqual(len(accepted), 50)
        self.assertEqual(ranked, self.run)
        for row in evaluation.measure(self.queries, self.labels, ranked):
            self.assertEqual(row["readings"]["Direct"]["values"]["Hit@10"], 0)
            self.assertEqual(row["readings"]["Useful"]["values"]["Hit@10"], 1)

    def test_missing_hit_label_and_duplicate_label_fail(self):
        first = self.labels.pop(0)
        with self.assertRaisesRegex(ValueError, "Missing accepted Top10 judgment"):
            self.join()
        self.labels.extend([first, deepcopy(first)])
        with self.assertRaisesRegex(ValueError, "Duplicate accepted judgment"):
            self.join()

    def test_pool_duplicate_proposal_and_version_are_rejected(self):
        self.pool.append(dict(self.pool[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate v6 pool pair"):
            self.join()
        self.pool.pop()
        self.labels[0]["status"] = "proposed"
        with self.assertRaisesRegex(ValueError, "Invalid accepted judgment"):
            self.join()
        self.labels[0]["status"] = "accepted"
        self.run[0]["index_version"] = "v1"
        with self.assertRaisesRegex(ValueError, "Wrong frozen version"):
            self.join()

    def test_wrong_binding_query_payload_type_and_full_read(self):
        base = deepcopy(self.labels[0])
        for field, value in (
            ("binding", {"dataset_version": "v5", "index_version": "v2"}),
            ("query_sha256", "foreign-query"),
            ("record_sha256", "foreign-record"),
            ("record_type", "table-retrieval.v1"),
            ("full_read_sha256", "foreign-read"),
        ):
            with self.subTest(field=field):
                self.labels[0] = {**base, field: value}
                with self.assertRaises(ValueError):
                    self.join()
        self.labels[0] = base
        self.run[0]["dataset_response_sha256"] = "foreign-frozen-read"
        with self.assertRaisesRegex(ValueError, "Frozen hit full-read binding"):
            self.join()


class GradedComparisonTests(unittest.TestCase):
    def test_new_rank_four_direct_changes_dcg_and_idcg(self):
        ranked = [f"r{rank}" for rank in range(1, 11)]
        old = {**dict.fromkeys(ranked, 0), "r2": 1, "outside": 1}
        new = {**old, "r4": 2}
        before = evaluation.v5.metric_values(old, ranked)
        after = evaluation.v5.metric_values(new, ranked)
        self.assertAlmostEqual(before["DCG@10"], 1 / log2(3))
        self.assertAlmostEqual(before["IDCG@10_pool"], 1 + 1 / log2(3))
        self.assertAlmostEqual(after["DCG@10"], 1 / log2(3) + 3 / log2(5))
        self.assertAlmostEqual(after["IDCG@10_pool"], 3 + 1 / log2(3) + 1 / log2(4))
        self.assertEqual(after["readings"]["Direct"]["values"]["RR@10"], 1 / 4)
        self.assertEqual(after["readings"]["Useful"]["values"]["RR@10"], 1 / 2)

    def test_zero_idcg_comparison_keeps_delta_null(self):
        before = evaluation.v5.metric_values({"a": 0}, ["a"])
        after = evaluation.v5.metric_values({"a": 1}, ["a"])
        self.assertEqual(before["IDCG@10_pool"], 0)
        self.assertIsNone(before["nDCG@10_pool"])
        self.assertIsNone(evaluation.delta(before["nDCG@10_pool"], after["nDCG@10_pool"]))
