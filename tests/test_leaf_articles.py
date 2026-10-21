"""Synthetic builder fixtures; no legal approval or real token estimates."""
import copy
from pathlib import Path
import tempfile
import unittest

from src import chunk_preview_articles as builder, chunk_preview_v2 as legacy
from src.chunk_preview import chunk_identity, source_proof
from src.source_contracts import canonical, digest
from src.ingestion.legal_tree import unit_id, span_id
from tests.test_stage6_points import fixture, fixture_encoder


class LeafArticleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data, self.old_config, self.u = fixture(self.root, article_lead="FIXTURE: Không bỏ 0,25 mg/l. ")
        self.original = copy.deepcopy(self.data)
        self.uid = self.u["article"]["unit_id"]
        self.data["units"] = [u for u in self.data["units"] if u["unit_type"] in {"document", "article"}]
        self.data["spans"] = [s for s in self.data["spans"] if s["unit_id"] in {u["unit_id"] for u in self.data["units"]}]
        self.cfg = {"chunk_policy_version": builder.VERSION, "snapshot_date": "2025-01-01", "token_limit": 256,
                    "target_unit_ids": [self.uid]}

    def build(self, encode=fixture_encoder):
        return builder.build_chunks(self.data, self.root, self.cfg, ["FIXTURE_PENDING"], encode)

    def reidentify(self):
        old = self.uid
        self.uid = unit_id(self.u["article"])
        self.u["article"]["unit_id"] = self.uid
        self.cfg["target_unit_ids"] = [self.uid]
        for s in self.data["spans"]:
            if s["unit_id"] == old:
                s["unit_id"] = self.uid
                s["span_id"] = span_id(s)

    def test_roundtrip_title_once_original_unchanged_identity(self):
        before = copy.deepcopy(self.data)
        r = self.build(); c = r["chunks"][0]; contexts = r["contexts"]
        self.assertEqual(c["text_original"], self.u["article"]["text_original"])
        self.assertEqual(c["context_text"], self.u["article"]["title"])
        self.assertEqual(len(contexts), 1)
        self.assertEqual(c["text_for_search"].count(self.u["article"]["title"]), 1)
        self.assertEqual(c["source_locator"], source_proof(self.data, self.root, self.u["article"], "text_original", ""))
        self.assertEqual(c["content_sha256"], digest(c["text_for_search"].encode()))
        self.assertEqual(c["chunk_id"], "c_" + digest(canonical(chunk_identity(c, contexts)).encode()))
        self.assertEqual(self.data, before)
        self.assertEqual(self.build(), r)

    def test_article_with_child_rejected(self):
        self.data["units"].append(self.u["c1"])
        r = self.build()
        self.assertFalse(r["chunks"])
        self.assertEqual(r["issues"][0]["code"], "UNSUPPORTED_STRUCTURE")

    def test_missing_title_or_text_spans(self):
        original = copy.deepcopy(self.data["spans"])
        for field in ["title", "text_original"]:
            self.data["spans"] = [s for s in original if not (s["unit_id"] == self.uid and s["field_name"] == field)]
            self.assertFalse(self.build()["chunks"])

    def test_no_title_is_valid(self):
        self.u["article"]["title"] = ""
        self.reidentify()
        self.data["spans"] = [s for s in self.data["spans"] if s["field_name"] != "title"]
        r = self.build()
        self.assertEqual(len(r["chunks"]), 1)
        self.assertIsNone(r["chunks"][0]["context_text"])

    def test_parser_issue_blocks(self):
        self.data["issues"] = [{"law_id": self.u["article"]["law_id"], "unit_id": self.uid, "code": "FIXTURE_UNPARSED"}]
        self.assertEqual(self.build()["issues"][0]["code"], "PARSER_OR_EXTRACTION_ISSUE_IMPACT")

    def test_over_budget_retains_every_byte(self):
        def encode(texts):
            return [{**e, "tokens_with_special": 257} for e in fixture_encoder(texts)]
        r = self.build(encode)
        self.assertFalse(r["chunks"]); self.assertFalse(r["contexts"])
        q = r["quarantined"][0]
        self.assertEqual(q["candidate"]["text_original"], self.u["article"]["text_original"])
        self.assertEqual(len(q["contexts"]), 1)

    def test_possible_missed_numbering_is_not_chunked(self):
        self.u["article"]["text_original"] = "1. FIXTURE possible missing clause"
        self.u["article"]["text_sha256"] = digest(self.u["article"]["text_original"].encode())
        self.reidentify()
        self.assertEqual(self.build()["issues"][0]["code"], "POSSIBLE_UNPARSED_CHILD_STRUCTURE")

    def test_missing_parent_and_bad_hash(self):
        self.data["units"] = [self.u["article"]]
        self.assertFalse(self.build()["chunks"])
        self.data = copy.deepcopy(self.original)
        self.data["units"] = [u for u in self.data["units"] if u["unit_type"] in {"article", "document"}]
        self.data["units"][1]["text_sha256"] = "bad"
        self.assertFalse(self.build()["chunks"])

    def test_legacy_dispatch_equal_for_clause_and_points(self):
        cfg = {**self.old_config, "target_unit_ids": self.old_config["target_unit_ids"] + [self.u["c3"]["unit_id"]]}
        old = legacy.build_chunks(self.original, self.root, cfg, ["FIXTURE_PENDING"], fixture_encoder)
        new = builder.build_chunks(self.original, self.root, cfg, ["FIXTURE_PENDING"], fixture_encoder)
        self.assertEqual(new, old)


if __name__ == "__main__":
    unittest.main()
