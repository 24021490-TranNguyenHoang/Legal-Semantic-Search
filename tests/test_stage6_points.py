"""Synthetic point fixtures; no source/reviewer/legal verification is asserted."""
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

from src import chunk_preview_v2 as builder, encoder_input, points_preview
from src.chunk_preview import chunk_identity
from src.config import BASE_DIR, STAGING_DIR
from src.ingestion.legal_tree import unit_id, span_id
from src.source_contracts import canonical, digest
from src.source_registry import read_rows, load_json
from src.assessment_evidence import inventory


def fixture(root, article_lead="FIXTURE: Điều kiện chung không được bỏ."):
    law = "FIXTURE/STAGE6-POINTS"
    raw = b"SYNTHETIC POINT CONTEXT FIXTURE; not a legal source or DOCX reader test"
    (root/"raw.fixture").write_bytes(raw)
    eid = "e_"+digest(b"FIXTURE POINT EXTRACTION")
    units, spans, parts = [], [], []
    offset = 0
    def add(kind, designation, parent, text, title=""):
        nonlocal offset
        u = {"law_id": law, "parent_unit_id": parent["unit_id"] if parent else None, "unit_type": kind, "designation": designation,
             "canonical_path": (parent["canonical_path"]+"/" if parent else "")+kind+":"+designation,
             "citation_path": (parent["citation_path"]+" > " if parent else "")+kind+" "+designation,
             "ordinal": sum(x["parent_unit_id"] == (parent["unit_id"] if parent else None) for x in units),
             "title": title, "text_original": text, "text_sha256": digest(text.encode())}
        u["unit_id"] = unit_id(u); units.append(u)
        for field in ["title", "text_original"]:
            if not u[field]: continue
            s = {"unit_id": u["unit_id"], "extraction_id": eid, "field_name": field, "span_order": 0,
                 "char_start": offset, "char_end": offset+len(u[field]), "quote_sha256": digest(u[field].encode()),
                 "locator_json": canonical({"format": "docx", "part": "word/document.xml", "paragraph_index": len(parts), "fixture": True})}
            s["span_id"] = span_id(s); spans.append(s); parts.append(u[field]); offset += len(u[field])+1
        return u
    doc = add("document", law, None, "", "FIXTURE law")
    article = add("article", "6", doc, article_lead, "FIXTURE xử phạt")
    c1 = add("clause", "1", article, "1. FIXTURE: Phạt tiền từ 400.000 đồng đến 600.000 đồng đối với các hành vi sau:")
    same = "a) FIXTURE: Không thực hiện hành vi được yêu cầu;"
    a1 = add("point", "a", c1, same)
    b1 = add("point", "b", c1, "b) FIXTURE: Giữ dẫn chiếu điểm a khoản 2 Điều này; không tự ghép nội dung.")
    c2 = add("clause", "2", article, "2. FIXTURE: Phạt tiền từ 1.000.000 đồng đến 2.000.000 đồng đối với các hành vi sau:")
    a2 = add("point", "a", c2, same)
    d2 = add("point", "đ", c2, "đ) FIXTURE: Không bỏ dấu đ và đơn vị 0,25 mg/l.")
    c3 = add("clause", "3", article, "3. FIXTURE: Khoản không có Điểm vẫn là một target nguyên vẹn.")
    text = "\n".join(parts)
    (root/"normalized.txt").write_text(text, encoding="utf8", newline="\n")
    data = {"document": {"law_id": law, "source_id": "FIXTURE-POINTS", "law_title": "FIXTURE synthetic penalty law", "source_url": "https://example.invalid/fixture"},
            "files": [{"file_id": "fixture-file", "law_id": law, "raw_file_ref": "raw.fixture", "sha256": digest(raw), "size_bytes": len(raw)}],
            "extractions": [{"extraction_id": eid, "file_id": "fixture-file", "text_ref": "normalized.txt", "text_sha256": digest(text.encode()), "char_count": len(text), "review_status": "pending"}],
            "units": units, "spans": spans, "issues": []}
    cfg = {"chunk_policy_version": builder.VERSION, "snapshot_date": "2025-01-01", "token_limit": 256,
           "required_context_fields": ["title"], "required_clause_context_fields": ["text_original"], "target_unit_ids": [u["unit_id"] for u in [a1,b1,a2,d2]]}
    return data, cfg, {"article": article, "c1": c1, "c2": c2, "c3": c3, "a1": a1, "b1": b1, "a2": a2, "d2": d2}


def fixture_encoder(texts):
    return [{"input_sha256": digest(t.encode()), "encoder_text": "FIXTURE ENCODER COPY "+t, "truncation": False,
             "tokens_with_special": len(t.split())+2, "model_max_tokens": 256} for t in texts]


class PointBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage6-points-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data, self.cfg, self.u = fixture(self.root)

    def build(self, encoder=fixture_encoder):
        return builder.build_chunks(self.data, self.root, self.cfg, ["FIXTURE_PENDING"], encoder)

    def test_many_points_each_get_own_target_and_ordered_context(self):
        r = self.build(); self.assertEqual(len(r["chunks"]), 4); self.assertFalse(r["issues"])
        by = {u["unit_id"]: u for u in self.data["units"]}
        for c in r["chunks"]:
            u = by[c["unit_id"]]; parent = by[u["parent_unit_id"]]
            self.assertEqual(c["text_original"], u["text_original"])
            ctx = [x for x in r["contexts"] if x["chunk_id"] == c["chunk_id"]]
            self.assertEqual([(x["unit_id"], x["field_name"]) for x in ctx], [(self.u["article"]["unit_id"], "title"), (self.u["article"]["unit_id"], "text_original"), (parent["unit_id"], "text_original")])
            self.assertEqual(c["context_text"], "\n".join([self.u["article"]["title"], self.u["article"]["text_original"], parent["text_original"]]))
            self.assertEqual(c["content_sha256"], digest(c["text_for_search"].encode()))
            self.assertEqual(c["chunk_id"], "c_"+digest(canonical(chunk_identity(c,ctx)).encode()))

    def test_different_penalty_parents_cannot_cross_context_or_merge_same_point(self):
        r = self.build(); by = {c["unit_id"]: c for c in r["chunks"]}
        a, b = by[self.u["a1"]["unit_id"]], by[self.u["a2"]["unit_id"]]
        self.assertEqual(a["text_original"], b["text_original"])
        self.assertIn("400.000", a["context_text"]); self.assertNotIn("1.000.000", a["context_text"])
        self.assertIn("1.000.000", b["context_text"]); self.assertNotEqual(a["chunk_id"], b["chunk_id"])
        self.assertNotEqual(a["source_locator"], b["source_locator"])
        self.assertNotEqual(a["citation_path"], b["citation_path"])

    def test_no_article_lead_and_no_sibling_text_in_context(self):
        self.data, self.cfg, self.u = fixture(self.root, article_lead="")
        r = self.build(); self.assertFalse(r["issues"])
        for c in r["chunks"]:
            self.assertEqual(len([x for x in r["contexts"] if x["chunk_id"] == c["chunk_id"]]), 2)
            self.assertNotIn("Giữ dẫn chiếu", c["context_text"])

    def test_clause_with_points_is_not_an_extra_target_but_leaf_clause_survives(self):
        self.cfg["target_unit_ids"] += [self.u["c1"]["unit_id"], self.u["c3"]["unit_id"]]
        r = self.build()
        self.assertEqual(len(r["chunks"]), 5)
        self.assertEqual(r["issues"][0]["code"], "UNSUPPORTED_STRUCTURE")
        self.assertNotIn(self.u["c1"]["unit_id"], {c["unit_id"] for c in r["chunks"]})

    def test_missing_parent_or_context_span_is_blocked(self):
        self.data["units"].remove(self.u["c1"])
        r = self.build(); self.assertEqual(len(r["chunks"]), 2)
        self.data["units"].insert(2, self.u["c1"])
        self.data["spans"] = [s for s in self.data["spans"] if s["unit_id"] != self.u["c1"]["unit_id"]]
        self.assertEqual(len(self.build()["chunks"]), 2)
        self.data, self.cfg, self.u = fixture(self.root)
        # Optional article lead is present: missing its evidence must block,
        # unlike the valid empty-field case tested separately.
        self.data["spans"] = [s for s in self.data["spans"] if not (s["unit_id"] == self.u["article"]["unit_id"] and s["field_name"] == "text_original")]
        self.assertFalse(self.build()["chunks"])

    def test_direct_issue_on_clause_blocks_only_dependent_points(self):
        self.data["issues"].append({"issue_id": "fixture-conflict", "unit_id": self.u["c1"]["unit_id"], "code": "CONFLICTING_POINT_DESIGNATION"})
        r = self.build(); self.assertEqual(len(r["chunks"]), 2)
        self.assertTrue(all(q["code"] == "PARSER_OR_EXTRACTION_ISSUE_IMPACT" for q in r["issues"]))

    def test_unparsed_gap_in_parent_region_is_not_hidden_by_valid_target_spans(self):
        s = next(s for s in self.data["spans"] if s["unit_id"] == self.u["b1"]["unit_id"])
        self.data["issues"] = [{"issue_id": "fixture-unparsed", "code": "STRUCTURE_SUSPENDED", "law_id": self.data["document"]["law_id"],
                                "extraction_id": s["extraction_id"], "char_start": s["char_end"], "char_end": s["char_end"], "locator": {"part": "word/document.xml"}}]
        r = self.build(); self.assertEqual(len(r["chunks"]), 2)
        self.assertEqual({q["unit_id"] for q in r["issues"]}, {self.u["a1"]["unit_id"], self.u["b1"]["unit_id"]})

    def test_unbounded_issue_is_blocked_but_separate_nonbody_warning_is_not(self):
        eid = self.data["extractions"][0]["extraction_id"]
        self.data["issues"] = [{"issue_id": "fixture-unbounded", "code": "UNKNOWN_CONTENT", "extraction_id": eid}]
        self.assertFalse(self.build()["chunks"])
        self.data["issues"][0]["locator"] = {"part": "word/header1.xml"}
        self.assertEqual(len(self.build()["chunks"]), 4)

    def test_budget_keeps_whole_context_and_target_in_quarantine(self):
        self.cfg["token_limit"] = 4
        r = self.build(); self.assertFalse(r["chunks"]); self.assertFalse(r["contexts"])
        self.assertEqual(len(r["quarantined"]), 4)
        self.assertTrue(all(q["code"] == "TOKEN_BUDGET_EXCEEDED" for q in r["issues"]))
        self.assertIn("400.000", next(q["candidate"]["context_text"] for q in r["quarantined"] if q["candidate"]["unit_id"] == self.u["b1"]["unit_id"]))

    def test_cross_reference_and_non_whitespace_content_are_preserved(self):
        before = copy.deepcopy(self.data)
        r = self.build(); self.assertEqual(self.data, before)
        c = next(c for c in r["chunks"] if c["unit_id"] == self.u["b1"]["unit_id"])
        self.assertEqual(c["text_original"], self.u["b1"]["text_original"])
        self.assertIn("điểm a khoản 2 Điều này", c["text_for_search"])
        self.assertEqual(c["text_for_search"], "\n\n".join([c["law_title"],c["citation_path"],c["context_text"],c["text_original"]]))

    def test_policy_change_is_an_identity_change_not_content_change(self):
        self.cfg["target_unit_ids"] = [self.u["c3"]["unit_id"]]
        c = self.build()["chunks"][0]; prior = {**c, "chunk_policy_version": "old-fixture-policy"}
        self.assertNotEqual(chunk_identity(c,[]), chunk_identity(prior,[]))
        self.assertEqual(c["content_sha256"], prior["content_sha256"])

    def test_actual_encoder_does_not_mutate_legal_fields_or_spans(self):
        before = copy.deepcopy(self.data)
        self.cfg["target_unit_ids"] = [self.u["d2"]["unit_id"]]
        enc = load_json(BASE_DIR/"config/stage6_preview.v1.json")["encoder"]
        assets = BASE_DIR/"staging/article22-preview-001/tokenizer_assets"
        measured = {}
        def encode(texts):
            rows = encoder_input.encode_inputs([self.u["d2"]["text_original"]]+texts,enc,assets)["rows"]
            measured.update(target_tokens=rows[0]["tokens_with_special"], rows=rows[1:])
            return rows[1:]
        r = self.build(encode)
        self.assertEqual(self.data, before); self.assertEqual(len(r["chunks"]), 1)
        self.assertEqual(r["chunks"][0]["text_original"], self.u["d2"]["text_original"])
        self.assertFalse(r["encoder_inputs"][0]["truncation"])
        # A budget that fits the target alone must still reject full context+target.
        self.cfg["token_limit"] = measured["target_tokens"]
        q = self.build(lambda texts: measured["rows"])
        self.assertFalse(q["chunks"]); self.assertEqual(len(q["quarantined"]), 1)
        self.assertEqual(q["quarantined"][0]["candidate"]["context_text"], r["chunks"][0]["context_text"])

    def test_import_is_side_effect_free(self):
        code = '''
import sys,importlib
def audit(e,a):
 if e.startswith(('socket.','sqlite3.connect','subprocess.Popen')):raise AssertionError(e)
 if e=='open' and ((isinstance(a[1],str) and any(c in a[1] for c in 'wax+')) or (a[2]&3)):raise AssertionError('write')
sys.addaudithook(audit)
importlib.import_module('src.chunk_preview_v2');importlib.import_module('src.points_preview')
assert not any(m in sys.modules for m in ['torch','transformers','pyvi'])
'''
        p = subprocess.run([sys.executable,"-B","-c",code],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)


@unittest.skipUnless(os.environ.get("VTLS_POINTS_MANIFEST"), "Supply real point pilot")
class RealPointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-points-real-",dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)/"copy"
        shutil.copytree(Path(os.environ["VTLS_POINTS_MANIFEST"]).resolve().parent,self.run)
        self.manifest = self.run/"manifest.json"

    def check(self):
        with patch("src.points_preview.validate_tree",return_value={"technical_valid":True,"processing_success":True}), patch("src.points_preview.validate_article22",return_value={"processing_success":True}):
            return points_preview.validate(self.manifest)

    def reseal(self):
        m=load_json(self.manifest);m["files"]=inventory(self.run)
        self.manifest.write_text(canonical(m)+"\n",encoding="utf8")
        (self.run/"manifest.sha256").write_text(digest(self.manifest.read_bytes())+"\n",encoding="ascii")

    def test_real_roundtrip_pending_and_article22_regression(self):
        r=self.check()
        self.assertEqual(r["requested_target_count"],5)
        self.assertEqual(r["chunk_count"]+r["quarantine_count"],5)
        self.assertEqual(r["article22_regression_count"],3)
        self.assertFalse(r["release_eligible"]);self.assertEqual(r["human_reviewer_event_count"],0)

    def test_context_parent_or_encoder_tamper_after_reseal_rejected(self):
        p=self.run/"contexts.preview.jsonl";rows=read_rows(p);rows[0]["unit_id"]="u_"+"0"*64
        p.write_text("\n".join(canonical(r) for r in rows)+"\n",encoding="utf8");self.reseal()
        with self.assertRaises(ValueError):self.check()

    def test_issue_inventory_cannot_hide_an_affecting_source_region(self):
        p=self.run/"inputs/tree/quality_issues.jsonl"
        rows=read_rows(p);s=read_rows(self.run/"inputs/tree/source_spans.pending.jsonl")
        selected=load_json(self.run/"config.json")["chunk"]["target_unit_ids"][1]
        source=next(x for x in s if x["unit_id"]==selected)
        rows.append({"issue_id":"fixture-tamper-not-real-event","law_id":"168/2024/NĐ-CP","code":"UNDECODED_SOURCE_CONTENT",
                     "extraction_id":source["extraction_id"],"char_start":source["char_start"],"char_end":source["char_end"],"locator":json.loads(source["locator_json"])})
        p.write_text("\n".join(canonical(r) for r in rows)+"\n",encoding="utf8");self.reseal()
        with self.assertRaises(ValueError):self.check()


if __name__ == "__main__":
    unittest.main()
