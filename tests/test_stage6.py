"""Stage6 preview tests; all generated legal text here is synthetic fixture."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src import chunk_preview, encoder_input, article22_stage6
from src.assessment_evidence import inventory
from src.config import BASE_DIR, STAGING_DIR
from src.ingestion.legal_tree import unit_id, span_id
from src.source_contracts import canonical, digest
from src.source_registry import load_json, read_rows
from test_article22_draft import fixture_context


def fake_encoder(texts):
    """Fixture callback tests builder gating; not a measured model tokenizer."""
    return [{"input_sha256": digest(t.encode()), "encoder_text": t, "truncation": False,
             "tokens_with_special": len(t.split())+2, "model_max_tokens": 256} for t in texts]


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage6-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        t = fixture_context(self.root)["tables"]
        self.data = {"document": t["legal_document"][0], "units": t["legal_unit"], "spans": t["source_span"],
                     "files": t["source_file"], "extractions": t["extraction"]}
        self.cfg = {"snapshot_date": "2025-01-01", "chunk_policy_version": "fixture-whole-clause.v1",
                    "token_limit": 256, "required_context_fields": ["title"], "target_unit_ids": [self.data["units"][3]["unit_id"]]}
        # The older adapter helper writes platform newlines; this builder requires
        # the actual UTF-8/LF bytes promised by the extraction contract.
        self.rebuild_fixture()

    def build(self, encoder=fake_encoder):
        return chunk_preview.build_chunks(self.data, self.root, self.cfg, ["FIXTURE_PENDING"], encoder)

    def rebuild_fixture(self):
        """Rekey synthetic tree and regenerate true slices after fixture edits."""
        replacements, spans, parts, offset = {}, [], [], 0
        e = self.data["extractions"][0]
        for u in self.data["units"]:
            old = u["unit_id"]
            if u["parent_unit_id"] in replacements:
                u["parent_unit_id"] = replacements[u["parent_unit_id"]]
            u["text_sha256"] = digest(u["text_original"].encode())
            u["unit_id"] = unit_id(u)
            replacements[old] = u["unit_id"]
            for field in ["title", "text_original"]:
                text = u[field]
                if not text:
                    continue
                s = {"unit_id": u["unit_id"], "extraction_id": e["extraction_id"], "field_name": field,
                     "span_order": 0, "char_start": offset, "char_end": offset+len(text),
                     "quote_sha256": digest(text.encode()), "locator_json": canonical({"format": "fixture", "paragraph": len(parts)})}
                s["span_id"] = span_id(s)
                spans.append(s); parts.append(text); offset += len(text)+1
        text = "\n".join(parts)
        (self.root/e["text_ref"]).write_text(text, encoding="utf8", newline="\n")
        e.update(text_sha256=digest(text.encode()), char_count=len(text))
        self.data["spans"] = spans
        self.cfg["target_unit_ids"] = [replacements[x] for x in self.cfg["target_unit_ids"]]

    def test_whole_clause_context_spans_and_search_hash(self):
        before = copy.deepcopy(self.data)
        r = self.build()
        self.assertFalse(r["issues"]); self.assertEqual(len(r["chunks"]), 1)
        c = r["chunks"][0]; a = self.data["units"][2]; u = self.data["units"][3]
        self.assertEqual(c["text_original"], u["text_original"])
        self.assertEqual(c["context_text"], a["title"]+"\n"+a["text_original"])
        self.assertEqual(c["text_for_search"], "\n\n".join([self.data["document"]["law_title"], u["citation_path"], c["context_text"], u["text_original"]]))
        self.assertEqual(c["content_sha256"], digest(c["text_for_search"].encode()))
        self.assertEqual(self.data, before)
        self.assertEqual([x["context_order"] for x in r["contexts"]], [0, 1])
        self.assertTrue(json.loads(c["source_locator"])[0]["span_id"])

    def test_no_article_lead_is_valid_when_not_required(self):
        self.data["units"][2]["text_original"] = ""
        self.rebuild_fixture()
        r = self.build()
        self.assertFalse(r["issues"]); self.assertEqual(len(r["contexts"]), 1)
        self.assertEqual(r["chunks"][0]["context_text"], self.data["units"][2]["title"])

    def test_missing_required_lead_reports_issue(self):
        self.data["units"][2]["text_original"] = ""
        self.rebuild_fixture(); self.cfg["required_context_fields"].append("text_original")
        r = self.build()
        self.assertFalse(r["chunks"]); self.assertEqual(r["issues"][0]["code"], "MISSING_REQUIRED_CONTEXT")

    def test_missing_parent_is_not_invented(self):
        self.data["units"] = [u for u in self.data["units"] if u["unit_type"] != "article"]
        r = self.build()
        self.assertFalse(r["chunks"]); self.assertIn("Missing parent", r["issues"][0]["detail"])

    def test_missing_required_source_and_wrong_artifact_hash_rejected(self):
        self.data["spans"] = [s for s in self.data["spans"] if s["unit_id"] != self.cfg["target_unit_ids"][0]]
        self.assertFalse(self.build()["chunks"])
        self.data["extractions"][0]["text_sha256"] = "0"*64
        self.assertFalse(self.build()["chunks"])

    def test_missing_context_evidence_is_not_silently_skipped(self):
        a = self.data["units"][2]
        self.data["spans"] = [s for s in self.data["spans"] if not (s["unit_id"] == a["unit_id"] and s["field_name"] == "text_original")]
        r = self.build()
        self.assertFalse(r["chunks"]); self.assertEqual(r["issues"][0]["code"], "INVALID_RELATION_OR_SOURCE")

    def test_over_budget_keeps_full_quarantined_content_and_no_ready_chunk(self):
        self.cfg["token_limit"] = 3
        r = self.build()
        self.assertFalse(r["chunks"]); self.assertFalse(r["contexts"])
        self.assertEqual(r["issues"][0]["code"], "TOKEN_BUDGET_EXCEEDED")
        self.assertEqual(r["quarantined"][0]["candidate"]["text_original"], self.data["units"][3]["text_original"])
        self.assertFalse(r["encoder_inputs"][0]["within_budget"])

    def test_penalty_lead_and_behavior_points_are_explicitly_unsupported(self):
        clause = self.data["units"][3]
        clause["text_original"] = "1. FIXTURE: Phạt tiền từ 400.000 đồng đến 600.000 đồng đối với hành vi sau:"
        point = {**copy.deepcopy(clause), "unit_id": "temporary-fixture-point", "unit_type": "point", "designation": "đ",
                 "parent_unit_id": clause["unit_id"], "canonical_path": clause["canonical_path"]+"/point:đ",
                 "citation_path": clause["citation_path"]+" > point đ", "ordinal": 0,
                 "title": "", "text_original": "đ) FIXTURE: Không chấp hành hiệu lệnh;"}
        self.data["units"].append(point); self.rebuild_fixture()
        r = self.build()
        self.assertFalse(r["chunks"]); self.assertEqual(r["issues"][0]["code"], "UNSUPPORTED_STRUCTURE")
        self.assertTrue(r["issues"][0]["source_spans"])
        self.assertIn("400.000", clause["text_original"])
        self.assertEqual(point["unit_type"], "point")

    def test_builder_has_no_article22_or_law_number_requirement(self):
        self.data["units"][2]["designation"] = "7"
        self.rebuild_fixture()
        self.assertFalse(self.build()["issues"])

    def test_duplicate_or_cross_law_input_blocked(self):
        self.data["units"].append(copy.deepcopy(self.data["units"][-1]))
        self.assertEqual(self.build()["issues"][0]["code"], "DUPLICATE_UNIT_ID")
        self.data["units"].pop(); self.data["units"][2]["law_id"] = "FIXTURE/OTHER"
        self.assertFalse(self.build()["chunks"])

    def test_encoder_binding_or_truncation_cannot_be_smuggled(self):
        def bad(texts):
            rows = fake_encoder(texts); rows[0]["truncation"] = True; return rows
        with self.assertRaises(ValueError): self.build(bad)

    def test_identity_stable_and_original_spans_unchanged_across_preprocessing(self):
        before = copy.deepcopy(self.data)
        a = self.build()
        def changed(texts):
            rows = fake_encoder(texts)
            for r in rows: r["encoder_text"] = "ENCODER COPY"
            return rows
        b = self.build(changed)
        self.assertEqual(a["chunks"], b["chunks"]); self.assertEqual(a["contexts"], b["contexts"])
        self.assertEqual(self.data, before)


class EncoderTests(unittest.TestCase):
    def test_preparation_preserves_all_content_and_uses_copy(self):
        text = "Không\nđược bỏ dấu; 0,25 mg/l."
        self.assertEqual(encoder_input.preprocess_text(text, lambda t: t.replace("bỏ dấu", "bỏ_dấu")), "Không được bỏ_dấu; 0,25 mg/l.")
        self.assertIn("\n", text)
        with self.assertRaises(ValueError): encoder_input.preprocess_text(text, lambda t: t.replace("Không", ""))

    def test_shared_real_query_document_configuration_and_newline_diagnosis(self):
        cfg = load_json(article22_stage6.DEFAULT_CONFIG)["encoder"]
        directory = BASE_DIR/"staging/article22-preview-001/tokenizer_assets"
        texts = ["Không được bỏ từ phủ định.\nĐơn vị đo: 0,25 mg/l.", "Không được bỏ từ phủ định. "*100+"Kết thúc."]
        document = encoder_input.encode_inputs(texts, cfg, directory, role="document")
        query = encoder_input.encode_inputs(texts, cfg, directory, role="query")
        d, q = document["rows"][0], query["rows"][0]
        self.assertEqual(d["encoder_text"], q["encoder_text"])
        self.assertEqual(d["after"]["token_ids"], q["after"]["token_ids"])
        self.assertEqual(document["segmenter_binding"], query["segmenter_binding"])
        self.assertEqual(d["before"]["unknowns"][0]["source"]["source_fragment"], "\n")
        self.assertEqual(d["before"]["special_token_count"], 2)
        self.assertEqual(d["after"]["unknown_tokens"], 0)
        self.assertFalse(document["runtime"]["inference_loaded"])
        self.assertFalse(document["runtime"]["native_offset_mapping"])
        self.assertGreater(document["rows"][1]["tokens_with_special"], 256)
        self.assertFalse(document["rows"][1]["truncation"])
        self.assertIn("Kết", document["rows"][1]["encoder_text"])

    def test_import_has_no_io_or_inference(self):
        code = '''
import sys,importlib
def audit(e,a):
 if e.startswith(('socket.','sqlite3.connect','subprocess.Popen')):raise AssertionError(e)
 if e=='open' and ((isinstance(a[1],str) and any(c in a[1] for c in 'wax+')) or (a[2]&3)):raise AssertionError('write')
sys.addaudithook(audit)
for m in ['src.chunk_preview','src.encoder_input','src.article22_stage6']:importlib.import_module(m)
assert not any(m in sys.modules for m in ['torch','transformers','pyvi'])
'''
        p = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


@unittest.skipUnless(os.environ.get("VTLS_STAGE6_MANIFEST"), "Supply Stage6 manifest for real artifact checks")
class RealStage6Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage6-real-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)/"copy"
        shutil.copytree(Path(os.environ["VTLS_STAGE6_MANIFEST"]).resolve().parent, self.run)
        self.path = self.run/"manifest.json"

    def reseal(self):
        m = load_json(self.path); m["files"] = inventory(self.run)
        self.path.write_text(canonical(m)+"\n", encoding="utf8")
        (self.run/"manifest.sha256").write_text(digest(self.path.read_bytes())+"\n", encoding="ascii")

    def check(self):
        # CLI separately replays upstream; these tests isolate downstream tamper.
        with patch("src.article22_stage6.validate_baseline", return_value={"technical_valid": True}):
            return article22_stage6.validate(self.path)

    def test_actual_ids_hashes_unknowns_and_pending(self):
        r = self.check()
        self.assertTrue(r["processing_success"]); self.assertTrue(r["identity_payloads_equal"])
        self.assertFalse(r["release_eligible"]); self.assertEqual(r["human_reviewer_event_count"], 0)
        self.assertEqual(sorted(e["tokens_with_special"] for e in read_rows(self.run/"encoder_inputs.preview.jsonl")), [82,83,106])

    def test_encoder_text_or_legal_text_tampering_after_reseal_rejected(self):
        path = self.run/"encoder_inputs.preview.jsonl"
        rows = read_rows(path); rows[0]["encoder_text"] += " khác"
        path.write_text("\n".join(canonical(r) for r in rows)+"\n", encoding="utf8"); self.reseal()
        with self.assertRaises(ValueError): self.check()

    def test_forged_diagnostic_offsets_rejected(self):
        path = self.run/"encoder_inputs.preview.jsonl"
        rows = read_rows(path); rows[0]["before"]["unknowns"][0]["source"]["char_start"] += 1
        path.write_text("\n".join(canonical(r) for r in rows)+"\n", encoding="utf8"); self.reseal()
        with self.assertRaises(ValueError): self.check()

    def test_missing_model_evidence_rejected(self):
        (self.run/"model_evidence/model_card.md").write_text("not evidence", encoding="utf8"); self.reseal()
        with self.assertRaises(ValueError): self.check()


if __name__ == "__main__":
    unittest.main()
