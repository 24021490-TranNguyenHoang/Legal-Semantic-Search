"""Stage 1 safety tests. No embeddings, model downloads or Qdrant builds."""
import ast
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.config import BASE_DIR, STAGING_DIR, CHUNKS_FILE, CLEANED_DIR
from src.pipeline_cli import read_records, staging_path


MODULES = (
    "src.config", "src.pipeline_cli", "src.ingestion.cleaner", "src.ingestion.chunker",
    "src.ingestion.embedder", "src.database.bm25_store", "src.database.qdrant_setup",
    "src.search.legal_retriever", "src.search.search_db", "src.search.test_search",
    "src.frontend.app",
)
WRITERS = MODULES[2:7]


def protected_hashes():
    return {p.relative_to(BASE_DIR).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for name in ("data", "qdrant_db") for p in (BASE_DIR / name).rglob("*")
            if p.is_file()}


class Stage1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected = protected_hashes()

    @classmethod
    def tearDownClass(cls):
        if protected_hashes() != cls.protected:
            raise AssertionError("Raw/corpus/embedding/Qdrant files changed during tests")

    def setUp(self):
        STAGING_DIR.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-stage1-", dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def call(self, module, args):
        with redirect_stderr(io.StringIO()) as error, redirect_stdout(io.StringIO()):
            code = importlib.import_module(module).main([str(a) for a in args])
        return code, error.getvalue()

    def record(self, **changes):
        return dict({"chunk_id": "example-1", "original_text": "Example source text",
                     "enriched_text": "Example context and source text"}, **changes)

    def jsonl(self, items):
        path = self.root / "input.jsonl"
        path.write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")
        return path

    def test_imports_have_no_io_or_third_party_initialization(self):
        script = '''
import importlib, importlib.abc, os, sys
class BlockDependencies(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','transformers','sentence_transformers',
             'qdrant_client','rank_bm25','streamlit','docx','pdfplumber','numpy'}:
            raise AssertionError('Dependency initialized during import: ' + fullname)
sys.meta_path.insert(0, BlockDependencies())
def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        if isinstance(mode, str) and any(c in mode for c in 'wax+'):
            raise AssertionError('Write during import: ' + str(path))
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError('Write during import: ' + str(path))
    if event in {'os.mkdir','os.remove','os.rmdir','os.rename','socket.connect','subprocess.Popen'}:
        raise AssertionError('Side effect during import: ' + event)
sys.addaudithook(audit)
for name in sys.argv[1:]: importlib.import_module(name)
'''
        result = subprocess.run([sys.executable, "-B", "-c", script, *MODULES],
                                cwd=BASE_DIR, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_help_and_missing_cli_arguments(self):
        for module in (*WRITERS, "src.search.search_db", "src.search.test_search"):
            with self.subTest(module=module):
                for flags, expected in ((["--help"], 0), ([], 2)):
                    result = subprocess.run([sys.executable, "-B", "-m", module, *flags],
                                            cwd=BASE_DIR, capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stderr)

    def test_missing_input_returns_nonzero_without_output(self):
        for module in WRITERS:
            flag = "--input-dir" if module.endswith(("cleaner", "chunker")) else "--input"
            out = self.root / module.rsplit(".", 1)[1]
            code, error = self.call(module, [flag, self.root / "missing", "--run-dir", out])
            self.assertEqual(code, 1)
            self.assertIn("does not exist", error)
            self.assertFalse(out.exists())

    def test_empty_directories_and_unparseable_text_fail(self):
        inputs = self.root / "inputs"
        inputs.mkdir()
        for module in WRITERS[:2]:
            code, _ = self.call(module, ["--input-dir", inputs, "--run-dir", self.root / "out"])
            self.assertEqual(code, 1)
        (inputs / "no-structure.txt").write_text("no legal structure", encoding="utf-8")
        code, error = self.call("src.ingestion.chunker", ["--input-dir", inputs,
                                "--run-dir", self.root / "out"])
        self.assertEqual(code, 1)
        self.assertIn("no chunks", error)
        self.assertFalse((self.root / "out").exists())

    def test_malformed_json_duplicate_ids_and_vectors_fail_before_writes(self):
        path = self.root / "bad.jsonl"
        path.write_text('{broken\n', encoding="utf-8")
        for module in WRITERS[2:]:
            code, _ = self.call(module, ["--input", path, "--run-dir", self.root / "out"])
            self.assertEqual(code, 1)
            self.assertFalse((self.root / "out").exists())
        for items in ([self.record(), self.record()],
                      [self.record(vector=[0.1])],
                      [self.record(vector=[float("nan")] * 768)],
                      [self.record(vector=[True] * 768)],
                      [self.record(vector=[0.0] * 768)]):
            path = self.jsonl(items)
            code, _ = self.call("src.database.qdrant_setup", ["--input", path,
                                "--run-dir", self.root / "out"])
            self.assertEqual(code, 1)
            self.assertFalse((self.root / "out").exists())

    def test_protected_or_reused_output_rejected(self):
        for path in (BASE_DIR / "data/raw/new", BASE_DIR / "data/processed/new",
                     BASE_DIR / "qdrant_db/new", STAGING_DIR, self.root,
                     STAGING_DIR / ".." / "escaped"):
            with self.subTest(path=path), self.assertRaises((ValueError, FileExistsError)):
                staging_path(path)
        # A symlink into protected data must not bypass path resolution.
        link = self.root / "link"
        try:
            link.symlink_to(BASE_DIR / "data", target_is_directory=True)
        except OSError:
            return  # Windows may require elevated symlink privileges.
        self.addCleanup(link.unlink)
        with self.assertRaises(ValueError):
            staging_path(link / "new")

    def test_check_only_never_initializes_models_or_qdrant(self):
        import builtins
        original_import = builtins.__import__
        def block_engines(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "qdrant_client", "rank_bm25"}:
                raise AssertionError(f"Engine imported during check-only: {name}")
            return original_import(name, *args, **kwargs)
        path = self.jsonl([self.record(vector=[0.1] * 768)])
        for module in WRITERS[2:]:
            out = self.root / module.rsplit(".", 1)[1]
            with patch("builtins.__import__", side_effect=block_engines):
                code, error = self.call(module, ["--input", path, "--run-dir", out, "--check-only"])
            self.assertEqual(code, 0, error)
            self.assertFalse(out.exists())

    def test_chunker_matches_existing_corpus_without_overwriting(self):
        out = self.root / "chunked"
        code, error = self.call("src.ingestion.chunker", ["--input-dir", CLEANED_DIR,
                                "--run-dir", out])
        self.assertEqual(code, 0, error)
        original = {i["chunk_id"]: i for i in read_records(CHUNKS_FILE)}
        actual = {i["chunk_id"]: i for i in read_records(out / "corpus_chunks.jsonl")}
        self.assertEqual(actual, original)
        self.assertEqual(json.loads((out / "run_report.json").read_text())["status"], "success")
        code, _ = self.call("src.ingestion.chunker", ["--run-dir", out])
        self.assertEqual(code, 1)

    def test_parser_cleaner_algorithms_unchanged(self):
        for name, functions in (("src/ingestion/chunker.py", {"enrich_context", "determine_doc_info", "parse_and_chunk"}),
                                ("src/ingestion/cleaner.py", {"clean_text", "read_docx", "read_pdf", "extract_and_clean"})):
            old = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=BASE_DIR).decode("utf-8")
            new = (BASE_DIR / name).read_text(encoding="utf-8")
            def defs(text):
                result = {}
                for node in ast.parse(text).body:
                    if isinstance(node, ast.FunctionDef) and node.name in functions:
                        # Lazy dependency imports are the only changes in reader functions.
                        node.body = [n for n in node.body if not isinstance(n, (ast.Import, ast.ImportFrom))]
                        result[node.name] = ast.dump(node)
                return result
            self.assertEqual(defs(old), defs(new))

    def test_cleaner_writes_only_new_staging_files(self):
        from docx import Document
        source = self.root / "raw"
        source.mkdir()
        doc = Document()
        doc.add_paragraph("Example legal input")
        doc.save(source / "example.docx")
        out = self.root / "cleaned"
        code, error = self.call("src.ingestion.cleaner", ["--input-dir", source, "--run-dir", out])
        self.assertEqual(code, 0, error)
        self.assertEqual((out / "cleaned/example_cleaned.txt").read_text(), "Example legal input")
        # A broken DOCX aborts the entire batch before outputs are created.
        (source / "broken.docx").write_bytes(b"broken zip")
        code, _ = self.call("src.ingestion.cleaner", ["--input-dir", source,
                            "--run-dir", self.root / "failed"])
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "failed").exists())

    def test_failure_after_run_creation_is_reported(self):
        path = self.jsonl([self.record()])
        out = self.root / "bm25-failed"
        with patch("rank_bm25.BM25Okapi", side_effect=RuntimeError("controlled build failure")):
            code, error = self.call("src.database.bm25_store", ["--input", path, "--run-dir", out])
        self.assertEqual(code, 1)
        self.assertIn("controlled build failure", error)
        self.assertFalse((out / "bm25_index.pkl").exists())
        report = json.loads((out / "run_report.json").read_text())
        self.assertEqual(report["status"], "failed")

    def test_bm25_fixture_success_is_isolated(self):
        path = self.jsonl([self.record(), self.record(chunk_id="example-2",
                                                     enriched_text="Different example text")])
        out = self.root / "bm25-ok"
        code, error = self.call("src.database.bm25_store", ["--input", path, "--run-dir", out])
        self.assertEqual(code, 0, error)
        self.assertGreater((out / "bm25_index.pkl").stat().st_size, 0)
        self.assertFalse((out / "bm25_index.pkl.partial").exists())
        self.assertEqual(json.loads((out / "run_report.json").read_text())["status"], "success")

    def test_search_checks_inputs_before_loading_model(self):
        for module in ("src.search.search_db", "src.search.test_search"):
            code, error = self.call(module, ["--query", "example", "--input", self.root / "missing"])
            self.assertEqual(code, 1)
            self.assertIn("does not exist", error)


if __name__ == "__main__":
    unittest.main()
