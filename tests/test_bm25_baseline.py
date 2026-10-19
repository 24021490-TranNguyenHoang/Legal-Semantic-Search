"""Synthetic lexical fixtures and opt-in real dataset/index regression."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src import bm25_baseline as bm
from src.bm25_tokenizer import tokenize
from src.experimental_dataset import load, rows, write_json
from src.source_contracts import canonical, digest
from src.retrieval_dataset import latest_scope


class RuntimeCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.created = {"dependencies": {"bm25s": "0.3.13", "numpy": "2.4.6", "scipy": "1.17.1"},
                        "python": "3.11.9", "unicode": "14.0.0", "engine_source_sha256": {"scoring.py": "FIXTURE/hash"}}

    def test_patch_difference_allowed_and_environment_recorded(self):
        running = {**self.created, "python": "3.11.10"}
        result = bm.runtime_compatibility(self.created, running)
        self.assertTrue(result["compatible"]); self.assertTrue(result["warnings"])
        self.assertEqual(result["created"]["python"], "3.11.9")
        self.assertEqual(result["running"]["python"], "3.11.10")
        self.assertEqual(bm.runtime_compatibility(self.created, self.created)["warnings"], [])

    def test_minor_unicode_dependency_source_or_invalid_python_rejected(self):
        for key, value in [("python", "3.12.1"), ("python", "3.11"), ("python", "invalid"),
                           ("unicode", "15.0.0"), ("dependencies", {"bm25s": "wrong"}),
                           ("engine_source_sha256", {"scoring.py": "wrong"})]:
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "runtime incompatibility"):
                bm.runtime_compatibility(self.created, {**self.created, key: value})
        with patch("platform.python_implementation", return_value="PyPy"), self.assertRaises(ValueError):
            bm.runtime_compatibility(self.created, self.created)

    def test_original_loader_only_and_exact_tokenizer_required(self):
        current = bm.code_binding()
        self.assertEqual(bm.compatible_code_binding(current), "exact")
        original = {**current, "src/bm25_baseline.py": bm.ORIGINAL_V1_LOADER_SHA256}
        self.assertEqual(bm.compatible_code_binding(original), "original_v1_loader_handoff_compatibility")
        for bad in [{**original, "src/bm25_baseline.py": "unknown"},
                    {**original, "src/bm25_tokenizer.py": "wrong"}, {}]:
            with self.assertRaisesRegex(ValueError, "source binding mismatch"):
                bm.compatible_code_binding(bad)


def fixture(cid, text):
    return {"chunk_id": "FIXTURE/" + cid, "unit_id": "FIXTURE/u" + cid,
            "text_for_search": text, "content_sha256": digest(text.encode())}


class LexicalTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load(bm.DEFAULT_CONFIG)
        self.chunks = [fixture("b", "đi không dừng 400.000 đồng"),
                       fixture("a", "đi không dừng 400.000 đồng"), fixture("c", "còi đêm")]

    def build(self):
        index, mapping = bm.create_index(self.chunks, self.cfg)
        return index, {r["internal_doc_id"]: r for r in mapping}

    def test_vietnamese_numbers_symbols_and_nfc(self):
        import unicodedata
        text = "Đ) KHÔNG 400.000 đồng 0,25 mg/l 168/2024/NĐ-CP 36/2024/QH15 10%"
        before = text
        expected = ["đ", "không", "400.000", "đồng", "0,25", "mg/l", "168/2024/nđ-cp", "36/2024/qh15", "10", "%"]
        self.assertEqual(tokenize(text, self.cfg), expected)
        self.assertEqual(text, before)
        self.assertEqual(tokenize(unicodedata.normalize("NFD", text), self.cfg), expected)
        self.assertEqual(tokenize("không\t được\nphép", self.cfg), ["không", "được", "phép"])

    def test_save_load_same_scores(self):
        import bm25s
        import numpy as np
        index, mapping = self.build()
        with tempfile.TemporaryDirectory() as d:
            index.save(d, allow_pickle=False, show_progress=False)
            restored = bm25s.BM25.load(d, load_corpus=False, allow_pickle=False, show_progress=False)
            np.testing.assert_allclose(index.get_scores(["không"]), restored.get_scores(["không"]), rtol=1e-6, atol=1e-7)
            self.assertEqual(bm.rank(index, mapping, "không", 5, self.cfg), bm.rank(restored, mapping, "không", 5, self.cfg))

    def test_input_reordered_mapping_stable(self):
        _, ma = bm.create_index(self.chunks, self.cfg)
        _, mb = bm.create_index(list(reversed(self.chunks)), self.cfg)
        self.assertEqual(ma, mb)
        bm.check_mapping(list(reversed(ma)), list(reversed(self.chunks)), self.cfg)

    def test_mapping_duplicate_missing_cross_binding(self):
        _, mapping = bm.create_index(self.chunks, self.cfg)
        for bad in [mapping[:-1], mapping + mapping[:1], [dict(r, internal_doc_id=0) for r in mapping],
                    [dict(r, chunk_id="FIXTURE/wrong") if i == 0 else r for i, r in enumerate(mapping)]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError): bm.check_mapping(bad, self.chunks, self.cfg)
        for chunks in [self.chunks + self.chunks[:1], [dict(self.chunks[0], chunk_id="")],
                       [dict(self.chunks[0], content_sha256="wrong")], []]:
            with self.assertRaises(ValueError): bm.create_index(chunks, self.cfg)

    def test_same_tokenizer_document_query(self):
        index, mapping = self.build()
        query_tokens, hits = bm.rank(index, mapping, "KHÔNG", 3, self.cfg)
        self.assertEqual(query_tokens, tokenize("KHÔNG", self.cfg))
        self.assertIn(query_tokens[0], index.vocab_dict); self.assertEqual(len(hits), 2)

    def test_query_empty_punctuation_oov(self):
        index, mapping = self.build()
        for q in ["", "  \n", "?!...", "%"]:
            with self.assertRaises(ValueError): bm.rank(index, mapping, q, 5, self.cfg)
        self.assertEqual(bm.rank(index, mapping, "zzzxxyybm25oov", 5, self.cfg)[1], [])

    def test_positive_topk_no_zero_fill_stable_ties(self):
        index, mapping = self.build()
        hits = bm.rank(index, mapping, "không", 9999, self.cfg)[1]
        self.assertEqual([mapping[i]["chunk_id"] for i, _ in hits], ["FIXTURE/a", "FIXTURE/b"])
        self.assertTrue(all(score > 0 for _, score in hits))
        for k in [0, -1, True, 2.5, "5"]:
            with self.assertRaises(ValueError): bm.rank(index, mapping, "không", k, self.cfg)
        self.assertEqual(len(bm.rank(index, mapping, "không", 1, self.cfg)[1]), 1)

    def test_query_not_encoder_limited(self):
        index, mapping = self.build()
        ts, hits = bm.rank(index, mapping, "không " * 300, 5, self.cfg)
        self.assertEqual(len(ts), 300); self.assertEqual(len(hits), 2)

    def test_config_rejects_drift(self):
        for field, value in [("b", .1), ("token_pattern", ".*"), ("stemming", True), ("lowercase", 1), ("engine_version", "wrong")]:
            with self.assertRaises(ValueError): bm.check_config({**self.cfg, field: value})

    def test_import_no_models_database_or_writes(self):
        script = "import sys; import src.bm25_baseline; print([n for n in sys.modules if n.split('.')[0] in {'torch','sentence_transformers','qdrant_client','transformers','pyvi'}])"
        p = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr); self.assertEqual(p.stdout.strip(), "[]")


class SelectionTests(unittest.TestCase):
    def test_scope_preserved_and_revision_bound(self):
        units = {"FIXTURE/u": {"unit_id": "FIXTURE/u", "text": "Synthetic institution sanction"}}
        p = {"unit_id": "FIXTURE/u", "unit_sha256": digest(canonical(units["FIXTURE/u"]).encode()),
             "binding": {"coverage_manifest_sha256": "cov"}, "reviewer_ref": None,
             "reviewed_at": None, "proposal_id": "FIXTURE/p", "scope_candidate": "excluded"}
        self.assertEqual(latest_scope(units, [p], [], "cov", "scope")["FIXTURE/u"]["scope_candidate"], "excluded")
        r = {**p, "proposal_id": "FIXTURE/r", "previous_proposal_id": "FIXTURE/p",
             "previous_proposal_sha256": digest(canonical(p).encode()), "scope_candidate": "pending",
             "binding": {"scope_manifest_sha256": "scope", "tree_binding": p["binding"]}}
        self.assertEqual(latest_scope(units, [p], [r], "cov", "scope")["FIXTURE/u"]["scope_candidate"], "pending")
        for bad in [dict(r, unit_sha256="wrong"), dict(r, previous_proposal_sha256="wrong")]:
            with self.assertRaises(ValueError): latest_scope(units, [p], [bad], "cov", "scope")


@unittest.skipUnless(os.getenv("VTLS_BM25_MANIFEST"), "Set VTLS_BM25_MANIFEST for actual saved-index tests")
class ActualIndexTests(unittest.TestCase):
    def test_patch_warning_is_reported_without_mutating_artifact(self):
        from contextlib import redirect_stderr
        import io
        path = Path(os.environ["VTLS_BM25_MANIFEST"])
        before = path.read_bytes(); running = bm.runtime(); running["python"] = "3.11.10"
        output = io.StringIO()
        # Policy simulation only: the real interpreter has not changed.
        with patch.object(bm, "runtime", return_value=running), redirect_stderr(output):
            loaded = bm.load_index(path)
        self.assertIn("PYTHON_PATCH_DIFFERS", output.getvalue())
        self.assertEqual(loaded["runtime_compatibility"]["running"]["python"], "3.11.10")
        self.assertEqual(path.read_bytes(), before)

    def test_actual_validate_search_without_rebuild(self):
        path = Path(os.environ["VTLS_BM25_MANIFEST"])
        self.assertTrue(bm.validate_index(path)["technical_valid"])
        with patch("bm25s.BM25.index", side_effect=AssertionError("Search must not rebuild")):
            loaded = bm.load_index(path); result = bm.search_loaded(loaded, "nhường đường vòng xuyến", 5)
        self.assertTrue(result["results"])
        self.assertTrue(all(r["release_eligible"] is False and r["source_status"] == "pending" for r in result["results"]))

    def test_hash_mapping_dataset_binding_rejected(self):
        path = Path(os.environ["VTLS_BM25_MANIFEST"]).resolve()
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "FIXTURE-index"; shutil.copytree(path.parent, dest)
            mapping = dest / "document_mapping.jsonl"; original = mapping.read_bytes(); mapping.write_bytes(original + b"\n")
            with self.assertRaises(ValueError): bm.load_index(dest / "index_manifest.json")
            mapping.write_bytes(original)
            manifest = load(dest / "index_manifest.json"); manifest["dataset_manifest_sha256"] = "wrong"
            write_json(dest / "index_manifest.json", manifest)
            (dest / "index_manifest.sha256").write_text(digest((dest / "index_manifest.json").read_bytes()))
            with self.assertRaises(ValueError): bm.load_index(dest / "index_manifest.json")

    def test_resealed_mapping_and_tokenizer_invalid(self):
        from src.retrieval_dataset import files
        source = Path(os.environ["VTLS_BM25_MANIFEST"]).resolve().parent
        for kind in ["mapping", "tokenizer"]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as d:
                dest = Path(d) / "FIXTURE-index"; shutil.copytree(source, dest)
                m = load(dest / "index_manifest.json")
                if kind == "mapping":
                    r = rows(dest / "document_mapping.jsonl")
                    r[0]["internal_doc_id"], r[1]["internal_doc_id"] = r[1]["internal_doc_id"], r[0]["internal_doc_id"]
                    from src.experimental_dataset import write_rows
                    write_rows(dest / "document_mapping.jsonl", r)
                else:
                    cfg = load(dest / "config.json"); cfg["token_pattern"] = ".*"
                    write_json(dest / "config.json", cfg); m["config_sha256"] = digest((dest / "config.json").read_bytes())
                m["files"] = files(dest, bm.CONTROL); m["index_content_sha256"] = digest(canonical(m["files"]).encode())
                write_json(dest / "index_manifest.json", m)
                (dest / "index_manifest.sha256").write_text(digest((dest / "index_manifest.json").read_bytes()))
                with self.assertRaisesRegex(ValueError, "mapping mismatch|tokenizer configuration"):
                    bm.load_index(dest / "index_manifest.json")


if __name__ == "__main__":
    unittest.main()
